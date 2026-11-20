# -*- coding: utf-8 -*-
"""Atajos de teclado por MCP y CLI (P-165): lo mismo que Preferencias › Atajos de teclado."""
import json

from . import atajos as at
from .errores import error
from .herramientas_preferencias import _ajustes
from .registro import herramienta

CLAVE = "atajos/teclas"


def _guardar(ajustes, teclas):
    ajustes.setValue(CLAVE, json.dumps(teclas, sort_keys=True))
    ajustes.sync()
    if ajustes.status() != ajustes.Status.NoError:
        raise error("FILE_ERROR", "No se pudieron guardar las preferencias.")


def _fila(clave, efectivo, choque):
    return {"command": clave, "title": at.titulo(clave), "default": at.CATALOGO[clave][1],
            "current": efectivo[clave], "conflicts_with": choque.get(clave, [])}


def _comando(clave):
    if clave not in at.CATALOGO:
        raise error("INVALID_ARGUMENTS", f"No existe el comando «{clave}».", "list_shortcuts lista los comandos y sus atajos.")
    return clave


@herramienta("list_shortcuts", "documento", "Lista los comandos con su atajo de teclado de fábrica y el vigente (Preferencias "
             "› Atajos de teclado). conflicts_with nombra los comandos que usan la misma combinación.")
def list_shortcuts(sesion, query: str | None = None, only_changed: bool = False):
    """
    query: texto a buscar en el nombre del comando, su título o su atajo (sin distinguir mayúsculas); omitido lista todo.
    only_changed: true muestra solo los comandos cuyo atajo difiere del de fábrica.
    """
    teclas = at.leer(_ajustes().value(CLAVE, "{}", type=str))
    efectivo = at.efectivos(teclas)
    choque = at.choques(efectivo)
    q = (query or "").strip().lower()
    filas = [_fila(c, efectivo, choque) for c in sorted(at.CATALOGO, key=at.titulo)
             if (not q or q in c.lower() or q in at.titulo(c).lower() or q in efectivo[c].lower())
             and (not only_changed or c in teclas)]
    return {"shortcuts": filas, "changed": len(teclas), "conflicts": len(choque)}


@herramienta("set_shortcut", "documento", "Cambia, agrega o quita el atajo de un comando (Preferencias › Atajos de teclado, "
             "como «Change Keyboard Shortcut» de Fusion). No lo guarda si otro comando ya usa esa combinación. No modifica "
             "el documento ni entra en deshacer; la ventana lo toma al aplicar preferencias.", modifica=True,
             transaccion=False)
def set_shortcut(sesion, command: str, keys: str):
    """
    command: clave del comando (list_shortcuts).
    keys: la combinación, p. ej. 'Ctrl+Alt+V' o 'Shift+E'; vacío = el comando queda sin atajo.
    """
    _comando(command)
    nueva = at.normalizar(keys)
    if nueva is None:
        raise error("INVALID_SHORTCUT", f"«{keys}» no es una combinación válida.")
    ajustes = _ajustes()
    teclas = at.leer(ajustes.value(CLAVE, "{}", type=str))
    efectivo = at.efectivos(teclas)
    otros = [c for c, t in efectivo.items() if nueva and t == nueva and c != command and at.contexto(c) == at.contexto(command)]
    if otros:
        raise error("SHORTCUT_CONFLICT", f"{nueva} ya la usa «{at.titulo(otros[0])}» ({otros[0]}).",
                    "Quitale ese atajo antes con set_shortcut(command=…, keys='').")
    efectivo[command] = nueva
    _guardar(ajustes, at.diferencias(efectivo))
    return {"command": command, "title": at.titulo(command), "current": nueva, "default": at.CATALOGO[command][1]}


@herramienta("reset_shortcuts", "documento", "Devuelve un comando (o todos) al atajo de fábrica. No modifica el documento ni "
             "entra en deshacer.", modifica=True, transaccion=False)
def reset_shortcuts(sesion, command: str | None = None):
    """
    command: clave del comando; omitido restablece todos los atajos.
    """
    ajustes = _ajustes()
    teclas = at.leer(ajustes.value(CLAVE, "{}", type=str))
    if command is not None:
        _comando(command)
        teclas.pop(command, None)
    else:
        teclas = {}
    _guardar(ajustes, teclas)
    return {"changed": len(teclas)}

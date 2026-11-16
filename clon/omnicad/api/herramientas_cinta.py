# -*- coding: utf-8 -*-
"""Cinta personalizable por MCP y CLI (P-164): lo mismo que Preferencias › Cinta."""
from . import cinta_personal as cp
from .errores import error
from .herramientas_preferencias import _ajustes
from .registro import herramienta

CLAVE = "cinta/personal"


def _guardar(ajustes, personal):
    ajustes.setValue(CLAVE, cp.a_texto(personal))
    ajustes.sync()
    if ajustes.status() != ajustes.Status.NoError:
        raise error("FILE_ERROR", "No se pudieron guardar las preferencias.")


def _seccion(nombre):
    if nombre not in cp.SECCIONES:
        raise error("INVALID_ARGUMENTS", f"No existe la sección «{nombre}».", "get_ribbon lista las secciones de la cinta.")
    return nombre


@herramienta("get_ribbon", "documento", "Lista las secciones de la cinta (pestaña/grupo) con los botones grandes que llevan, "
             "en orden, y los de fábrica (Preferencias › Cinta). «SÓLIDO/FAVORITAS» es la sección que cada persona llena.")
def get_ribbon(sesion, tab: str | None = None):
    """
    tab: nombre de la pestaña (p. ej. 'SÓLIDO'); omitido lista todas.
    """
    efectivas = cp.efectivas(cp.leer(_ajustes().value(CLAVE, "{}", type=str)))
    filas = [{"section": s, "tools": [{"command": c, "title": cp.titulo(c)} for c in efectivas[s]],
              "default": cp.SECCIONES[s], "changed": efectivas[s] != cp.SECCIONES[s]}
             for s in cp.SECCIONES if tab is None or s.split("/")[0] == tab]
    return {"sections": filas, "max_tools": cp.MAXIMO}


@herramienta("set_ribbon_section", "documento", "Elige los botones grandes de una sección de la cinta y su orden (Preferencias "
             "› Cinta). Con 'SÓLIDO/FAVORITAS' agrega tus herramientas preferidas a la sección principal. No modifica el "
             "documento ni entra en deshacer; la ventana lo toma al aplicar preferencias.", modifica=True, transaccion=False)
def set_ribbon_section(sesion, section: str, tools: list[str]):
    """
    section: «PESTAÑA/GRUPO» devuelto por get_ribbon, p. ej. 'SÓLIDO/CREAR'.
    tools: claves de comando (list_shortcuts las lista), en el orden en que se ven; como mucho 8 y sin repetir; [] deja la sección sin botones.
    """
    _seccion(section)
    motivo = cp.validar(section, tools)
    if motivo:
        raise error("INVALID_ARGUMENTS", motivo, "list_shortcuts lista las claves de comando.")
    ajustes = _ajustes()
    efectivas = cp.efectivas(cp.leer(ajustes.value(CLAVE, "{}", type=str)))
    efectivas[section] = list(tools)
    _guardar(ajustes, cp.diferencias(efectivas))
    return {"section": section, "tools": list(tools)}


@herramienta("reset_ribbon", "documento", "Devuelve una sección de la cinta (o toda) a sus botones de fábrica. No modifica el "
             "documento ni entra en deshacer.", modifica=True, transaccion=False)
def reset_ribbon(sesion, section: str | None = None):
    """
    section: «PESTAÑA/GRUPO»; omitido restablece toda la cinta.
    """
    ajustes = _ajustes()
    personal = cp.leer(ajustes.value(CLAVE, "{}", type=str))
    if section is not None:
        personal.pop(_seccion(section), None)
    else:
        personal = {}
    _guardar(ajustes, personal)
    return {"changed": len(personal)}

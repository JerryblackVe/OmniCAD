# -*- coding: utf-8 -*-
"""Preajustes de comandos (la biblioteca vive en `nucleo/preajustes.py`; la fila del diálogo, en `ui/preajustes_ui.py`)."""
import difflib
from typing import Literal

from ..nucleo import geometria as geo
from ..nucleo import preajustes as pre
from .claves_comandos import CLAVES
from .errores import error
from .registro import herramienta


def _estado(comando):
    info = pre.listar(comando)
    return {"command": comando, "presets": info["presets"],
            "default": {pre.FABRICA: "factory", pre.ULTIMO: "last_used"}.get(info["default"], info["default"])}


@herramienta("manage_command_presets", "documento", "Preajustes de los diálogos de comandos (Nervio, Red, Agujero…; Fusion: "
             "Create and use presets): valores guardados con un nombre para volver a usarlos. Se guardan solo en esta PC, "
             "no en el diseño. Cada preajuste es un dict {campo del diálogo: valor} con texto, números o casillas; lo que "
             "se elige en la vista no se guarda. action=list muestra los nombres y el predeterminado; get devuelve los "
             "valores de uno (para pasarlos a la herramienta del comando); save crea o actualiza; rename y delete; "
             "set_default elige qué trae el diálogo al abrirse (factory, last_used o el nombre de un preajuste).")
def manage_command_presets(sesion, command: str, action: Literal["list", "get", "save", "rename", "delete", "set_default"],
                           name: str = "", values: dict | None = None, new_name: str = "", default: str = ""):
    """
    command: clave del comando de la ventana (la de la cinta: "nervio", "red", "agujero", "saliente"…).
    action: list, get, save, rename, delete o set_default.
    name: nombre del preajuste (get, save, rename, delete).
    values: con save, los valores del diálogo {campo: valor}; los que no son texto, número o casilla se descartan.
    new_name: con rename, el nombre nuevo.
    default: con set_default: factory, last_used o el nombre de un preajuste existente.
    """
    command = command.strip()
    if not command:
        raise error("INVALID_ARGUMENTS", "Indicá el comando (command).")
    if command not in CLAVES:
        parecidas = difflib.get_close_matches(command, sorted(CLAVES), n=3)
        raise error("INVALID_ARGUMENTS", f"No hay un comando «{command}».",
                    *([f"Parecidos: {', '.join(parecidas)}."] if parecidas else ["Las claves son las de la cinta."]))
    try:
        if action == "get":
            return {"command": command, "name": name, "values": pre.obtener(command, name)}
        if action == "save":
            if not isinstance(values, dict) or not pre.simples(values):
                raise error("INVALID_ARGUMENTS", "save necesita values: {campo: valor} con texto, números o casillas.")
            guardados = pre.guardar(command, name, values)
            return {"name": name.strip(), "values": guardados, **_estado(command)}
        if action == "rename":
            pre.renombrar(command, name, new_name)
        elif action == "delete":
            pre.borrar(command, name)
        elif action == "set_default":
            pre.definir_defecto(command, {"factory": pre.FABRICA, "last_used": pre.ULTIMO}.get(default, default))
    except geo.ErrorGeometria as e:
        raise error("ENTITY_NOT_FOUND" if "no tiene" in str(e) else "INVALID_ARGUMENTS", str(e)) from e
    return _estado(command)

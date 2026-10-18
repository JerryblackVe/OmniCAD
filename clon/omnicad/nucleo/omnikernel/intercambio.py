# -*- coding: utf-8 -*-
"""STEP e IGES con los lectores y escritores de OmniKernel (el árbol XCAF queda sin soporte)."""
from pathlib import Path

import omnikernel as k

from ..geometria import ErrorGeometria


def _escribir(forma, ruta, formato):
    Path(ruta).write_bytes(forma.exportar(formato))
    return True


def _leer(ruta, formato):
    try:
        datos = Path(ruta).read_bytes()
    except OSError as e:
        raise ErrorGeometria(f"No se pudo leer el archivo {formato.upper()}: {ruta}") from e
    forma = k.importar(datos, formato)
    if forma.IsNull():
        raise ErrorGeometria(f"El archivo {formato.upper()} no contiene geometría.")
    return forma


def escribir_step(forma, ruta):
    _escribir(forma, ruta, "step")


def leer_step(ruta):
    return _leer(ruta, "step")


def leer_step_texto(texto):
    return k.importar(texto.encode("utf-8"), "step")


def escribir_iges(forma, ruta):
    return _escribir(forma, ruta, "iges")


def leer_iges(ruta):
    return _leer(ruta, "iges")


def leer_iges_texto(texto):
    return k.importar(texto.encode("utf-8"), "iges")

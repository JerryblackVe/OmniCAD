# -*- coding: utf-8 -*-
"""Herramientas del grupo "inspeccion": barrido de parámetros (SC18, `inspect.parameter_sweep` de SolidCraft).

`parameter_sweep` recalcula el diseño con cada valor de un parámetro en un rango y devuelve una fila por
valor con las medidas pedidas. Trabaja sobre una COPIA del documento: el del usuario no cambia y no deja
pasos de deshacer. La ventana (INSPECCIONAR › Barrido de parámetros) llama al mismo bucle con callbacks de
progreso y cancelación; la herramienta pública no."""
import json
from typing import Literal

import numpy as np

from ..timeline.documento import Documento
from .errores import error
from .herramientas_parametros import _parametro
from .registro import herramienta, llamar
from .sesion import Sesion

TOPE_PASOS = 50
MEDIDAS = ("volume", "mass", "area", "bounding_box", "interference")
_DEFECTO = ["volume", "mass", "area", "bounding_box"]
_CLAVE_FILA = {"volume": "volume", "mass": "mass_g", "area": "area", "bounding_box": "bounding_box"}   # medida -> clave de la fila


def _barrido(sesion, parameter, start, stop, steps, measure, bodies, density, progreso=None, cancelado=None):
    """El bucle del barrido: reusa `set_parameter` y `get_physical_properties` (y `check_interference`) por
    API, sobre una copia del documento. `progreso(i, n)` y `cancelado()` los usa la ventana."""
    info = _parametro(sesion.doc, parameter)
    if info["kind"] == "text":
        raise error("INVALID_ARGUMENTS", f"«{parameter}» es un parámetro de texto: no se puede barrer.",
                    "Los parámetros de número, ángulo o sin unidad sí se pueden barrer.")
    if not 2 <= steps <= TOPE_PASOS:
        raise error("INVALID_ARGUMENTS", f"steps tiene que ser de 2 a {TOPE_PASOS} (recibió {steps}).")
    if not set(measure) <= set(MEDIDAS):
        raise error("INVALID_ARGUMENTS", f"measure solo acepta: {', '.join(MEDIDAS)}.", f"Recibió: {', '.join(map(str, measure))}.")
    ids = [sesion.cuerpo(b).id for b in bodies] if bodies else []
    copia = Documento.desde_dict(json.loads(json.dumps(sesion.doc.a_dict())))
    sub = Sesion(copia)
    filas, avisos = [], []
    for v in np.linspace(float(start), float(stop), steps):
        if cancelado is not None and cancelado():
            raise error("CANCELLED", "El barrido se canceló.")
        fila = {"value": round(float(v), 6)}
        r = llamar(sub, "set_parameter", {"name": parameter, "expression": float(v)})
        if not r["ok"]:
            fila["error"] = r["mensaje"]
            filas.append(fila)
            if progreso is not None:
                progreso(len(filas), steps)
            continue
        avisos += r["avisos"]
        r = llamar(sub, "get_physical_properties", {"bodies": ids, "density": density})
        if r["ok"]:
            avisos += r["avisos"]
            total = r["result"]["total"]
            fila.update({clave: total[clave] for medida, clave in _CLAVE_FILA.items() if medida in measure})
        else:
            fila["error"] = r["mensaje"]
        if "interference" in measure and "error" not in fila:
            r = llamar(sub, "check_interference", {"bodies": ids})
            fila["interference"] = r["result"]["interference"] if r["ok"] else None
            if not r["ok"]:
                fila["error"] = r["mensaje"]
        filas.append(fila)
        if progreso is not None:
            progreso(len(filas), steps)
    for a in avisos:
        sesion.avisar(a)
    return {"parameter": parameter, "unit": info["unit"], "rows": filas, "document_changed": False}


@herramienta("parameter_sweep", "inspeccion", "Barrido de parámetros: recalcula el diseño con cada valor del "
             "parámetro entre start y stop (en la unidad del parámetro) y devuelve una fila por valor con las "
             "medidas pedidas. Trabaja sobre una copia: el documento no cambia y no deja pasos de deshacer. "
             "Un valor que hace fallar el recálculo deja su fila con error y no corta el barrido.")
def parameter_sweep(sesion, parameter: str, start: float, stop: float, steps: int = 5,
                    measure: list[Literal["volume", "mass", "area", "bounding_box", "interference"]] = _DEFECTO,
                    bodies: list[str] | None = None, density: float | None = None):
    """
    parameter: nombre exacto del parámetro a barrer (get_parameters lista los que hay).
    start: primer valor, en la unidad del parámetro.
    stop: último valor, en la unidad del parámetro.
    steps: cantidad de valores entre start y stop, ambos incluidos (2 a 50).
    measure: qué medir en cada valor: volume (mm3), mass (g), area (mm2), bounding_box (mm) e interference (bool, más lento).
    bodies: ids o nombres de los cuerpos a medir o revisar; vacío = todos.
    density: densidad en g/cm3 para la masa; vacío = la del material físico de cada cuerpo.
    """
    return _barrido(sesion, parameter, start, stop, steps, measure, bodies, density)

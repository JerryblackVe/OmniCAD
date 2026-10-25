# -*- coding: utf-8 -*-
"""SÓLIDO › CREAR › Reconocer funciones (Find Features), sin Qt: `nucleo/reconocer_funciones.py` lee la geometría."""
from typing import Literal

from ..nucleo import geometria as geo
from ..nucleo import reconocer_funciones as rf
from . import selectores as sl
from .errores import error
from .registro import herramienta


@herramienta("find_features", "inspeccion", "Reconoce las funciones que forman un cuerpo sin historial, por ejemplo uno "
             "importado (SÓLIDO › CREAR › Reconocer funciones): agujeros (diámetro, profundidad, pasante, avellanado), "
             "empalmes (radio, convexo o cóncavo) y chaflanes (ancho y ángulo), cada uno con los ids de sus caras "
             "(find_faces) para poder elegirlos. Solo lee: todavía no crea los pasos del timeline que los rehacen ni "
             "reconoce extrusiones, revoluciones, simetrías ni patrones. No cambia el documento.")
def find_features(sesion, body: str | None = None,
                  types: list[Literal["hole", "fillet", "chamfer"]] | None = None):
    """
    body: id o nombre del cuerpo sólido; vacío = el único cuerpo.
    types: qué reconocer: hole, fillet, chamfer; vacío = los tres.
    """
    cuerpo = sl.cuerpo_objetivo(sesion, body)
    if getattr(cuerpo, "tipo", "solido") != "solido":
        raise error("INVALID_ARGUMENTS", f"«{cuerpo.nombre}» no es un sólido.")
    try:
        r = rf.reconocer_funciones(cuerpo.forma, tuple(types) if types else ("hole", "fillet", "chamfer"))
    except geo.ErrorGeometria as e:
        raise error("INVALID_ARGUMENTS", str(e)) from e
    elementos = {i: next(e for e in sl.listar(cuerpo.forma, "cara") if e.sub.IsSame(f))
                 for i, f in enumerate(r["face_shapes"], 1)}
    ids = {i: sl.emitir_id(sesion, cuerpo, el) for i, el in elementos.items()}
    funciones = [dict(f, faces=[ids[i] for i in f["faces"]]) for f in r["features"]]
    return {"body": cuerpo.id, "faces": r["faces"], "features": funciones,
            "summary": {t: sum(f["type"] == t for f in funciones) for t in ("hole", "fillet", "chamfer")}}

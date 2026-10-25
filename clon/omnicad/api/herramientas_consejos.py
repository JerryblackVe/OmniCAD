# -*- coding: utf-8 -*-
"""PLÁSTICO › Inspeccionar › Consejos de diseño (Design Advice), sin Qt: `nucleo/consejos_diseno.py` hace la revisión."""
from typing import Literal

from ..nucleo import consejos_diseno as cd
from ..nucleo import geometria as geo
from ..nucleo import plastico
from . import selectores as sl
from .errores import error
from .registro import herramienta

_EJES = {"X": (1.0, 0.0, 0.0), "Y": (0.0, 1.0, 0.0), "Z": (0.0, 0.0, 1.0)}


@herramienta("design_advice", "inspeccion", "Consejos de diseño para moldeo por inyección (Plástico › Inspeccionar › Design "
             "Advice): revisa un cuerpo contra una regla de plástico y la dirección de extracción del molde. Devuelve "
             "alertas por cara de espesor (too_thin, too_thick, variation), contrasalidas (undercut), desmoldeo "
             "insuficiente (draft) y filos (knife_edge), cada una con su consejo, y un resumen por tipo. Usa la regla "
             "asignada al componente del cuerpo, o la de rule, o «ABS 2 mm». Mide con rayos sobre 3×3 puntos por cara: "
             "es una revisión por regiones, no una simulación. No cambia el documento.")
def design_advice(sesion, body: str | None = None, pull_direction: Literal["X", "Y", "Z"] = "Z", flip: bool = False,
                  rule: str | None = None, ignore: list[Literal["thickness", "undercut", "draft", "knife_edge"]] | None = None):
    """
    body: id o nombre del cuerpo sólido; vacío = el único cuerpo.
    pull_direction: eje del origen que define la dirección de extracción: X, Y o Z.
    flip: true invierte la dirección de extracción.
    rule: nombre de la regla de plástico (list_plastic_rules) si el componente del cuerpo no tiene una asignada; vacío = "ABS 2 mm".
    ignore: tipos de alerta que se omiten del resultado (thickness agrupa too_thin, too_thick y variation).
    """
    cuerpo = sl.cuerpo_objetivo(sesion, body)
    if getattr(cuerpo, "tipo", "solido") != "solido":
        raise error("INVALID_ARGUMENTS", f"«{cuerpo.nombre}» no es un sólido: Consejos de diseño revisa sólidos.")
    asignada = (sesion.doc.estado_final.componentes.get(cuerpo.componente or "") or {}).get("regla_plastico")
    try:
        regla = dict(asignada) if asignada else plastico.regla(rule or plastico.REGLA_DEFECTO)
        direccion = [-c for c in _EJES[pull_direction]] if flip else _EJES[pull_direction]
        r = cd.consejos_de_diseno(cuerpo.forma, direccion, regla)
    except geo.ErrorGeometria as e:
        raise error("OPERATION_FAILED", str(e)) from e
    omitir = {t for g in ignore or [] for t in ({"thickness": ("too_thin", "too_thick", "variation")}.get(g, (g,)))}
    listadas = sl.listar(cuerpo.forma, "cara")                      # una sola vez: una lista por cara era cuadrático
    alertas = [dict(a, face=sl.emitir_id(sesion, cuerpo, next(e for e in listadas if e.sub.IsSame(r["face_shapes"][a["face"] - 1]))))
               for a in r["alerts"] if a["type"] not in omitir]
    return {"body": cuerpo.id, "rule": regla["nombre"], "pull_direction": list(direccion), "faces": r["faces"],
            "summary": {t: sum(a["type"] == t for a in alertas) for t in cd.CONSEJOS}, "alerts": alertas,
            "thickness": r["thickness"]}

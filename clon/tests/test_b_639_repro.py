# -*- coding: utf-8 -*-
"""B-639: la previa de «Plano a lo largo de la ruta» dibuja solo el punto sobre la curva, no el plano perpendicular.

La ruta en sí está bien: los 20 puntos de la spline del boceto (en mundo) y la curva que usan Plano en ruta y Barrido
coinciden (desvío máximo 0,012 mm, el paso del muestreo). Lo que falta es el cuadrado perpendicular que muestra Fusion.
"""
import numpy as np
from test_manipuladores import _panel, app_qt  # noqa: F401  (fixture)

from omnicad.restricciones.boceto import Boceto
from omnicad.timeline.documento import Documento
from omnicad.timeline.operaciones import OpBoceto
from omnicad.timeline.ops_construir import calcular_plano
from omnicad.ui import manipuladores as mp
from omnicad.ui.comando import hit_desde_ref
from omnicad.ui.comandos import CATALOGO

ONDA = [(-20, 0), (-12, 8), (-4, -6), (4, 7), (12, -5), (20, 0)]       # onda en el plano XZ (no XY)


def _doc_onda():
    b = Boceto()
    sp = b.agregar_spline(ONDA)
    doc = Documento()
    doc.agregar(OpBoceto(doc.nuevo_id(), "Boceto1", plano="XZ", boceto=b))
    return doc, sp


def test_la_previa_del_plano_en_ruta_dibuja_el_plano_perpendicular(app_qt):  # noqa: F811
    doc, sp = _doc_onda()
    estado = doc.estado_final
    hit = hit_desde_ref({"tipo": "curva_boceto", "boceto": "op1", "curva": sp}, estado)
    panel, _visor, _ = _panel(CATALOGO["plano_ruta"](), doc, {"r0": [hit]})
    gm = panel.manipuladores
    gm.actualizar()
    asa = next(m for m in gm.manips if isinstance(m, mp.AsaRuta))
    punto = asa.asa(gm)
    px = gm.escala(punto)                          # mm por píxel: los umbrales van en píxeles
    plano = calcular_plano(dict(panel.valores, tipo="ruta"), [mp.entidad(hit, estado)], panel.ctx, estado)
    assert np.allclose(plano.origen, punto, atol=1e-6)          # el asa está donde el plano se crea

    # Todo lo que la previa dibuja, en mundo. El disco del asa mira a la cámara y no cuenta: el plano de Fusion es un
    # cuadrado perpendicular a la ruta. Se buscan sus puntos en el plano del comando, lejos del punto del asa.
    prims = [p for m in gm.manips for p in m.dibujar(gm, None)]
    pts = np.concatenate([np.asarray(p[1], float).reshape(-1, 3) for p in prims if p[0] in ("lineas", "tris")])
    en_plano = pts[np.abs((pts - punto) @ plano.normal) < 0.25 * px]
    lejos = en_plano[np.linalg.norm(en_plano - punto, axis=1) > 2 * px]
    assert len(lejos) >= 3, "la previa no dibuja el plano perpendicular: solo el punto sobre la ruta"
    # Un cuadrado se extiende en dos direcciones del plano; una línea (el cruce del disco con el plano) en una sola.
    ancho = np.linalg.svd(lejos - punto, compute_uv=False)
    assert ancho[1] > 4 * px, "lo dibujado en el plano es una línea, no el plano perpendicular"
    panel.cancelar()

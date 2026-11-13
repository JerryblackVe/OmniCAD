# -*- coding: utf-8 -*-
"""B-311: las «franjas claras sin rayar» entre un tapón y su soporte en el Análisis de sección son la holgura real del modelo.

Gerardo vio dos franjas entre un tapón de Ø45 y el tubo de su soporte (agujero Ø46). La tapa del corte (`an.seccion_visual`) cubre
cada cuerpo con su área exacta; entre los dos cuerpos queda sin cubrir justo la holgura de 0,5 mm por lado. Es lo que dibuja
Fusion; si la tapa perdiera área, las franjas serían más anchas que la holgura o aparecerían donde no hay hueco."""
import numpy as np
import pytest

from omnicad import api
from omnicad.nucleo import analisis as an
from omnicad.nucleo import geometria as geo


def _llamar(sesion, nombre, **argumentos):
    r = api.llamar(sesion, nombre, argumentos)
    assert r["ok"], r
    return r["result"]


def _intervalos(tris, z):
    """Los tramos de x que cubren los triángulos (sobre el plano y = 0) a la altura z, ya unidos."""
    tramos = []
    for t in np.asarray(tris, float).reshape(-1, 3, 3):
        xs = []
        for a, b in ((0, 1), (1, 2), (2, 0)):
            za, zb = t[a, 2], t[b, 2]
            if (za - z) * (zb - z) < 0:
                xs.append(t[a, 0] + (t[b, 0] - t[a, 0]) * (z - za) / (zb - za))
        if len(xs) == 2:
            tramos.append(tuple(sorted(xs)))
    tramos.sort()
    unidos = []
    for a, b in tramos:
        if unidos and a <= unidos[-1][1] + 1e-6:
            unidos[-1] = (unidos[-1][0], max(unidos[-1][1], b))
        else:
            unidos.append((a, b))
    return unidos


def test_las_franjas_entre_el_tapon_y_el_tubo_son_la_holgura_del_modelo():
    s = api.Sesion()
    tubo = _llamar(s, "create_cylinder", height=60, radius=25, name="Tubo")["bodies_created"][0]["id"]
    _llamar(s, "create_cylinder", height=60, radius=23, operation="cut", target=[tubo])           # agujero Ø46
    tapon = _llamar(s, "create_cylinder", height=50, radius=22.5, z=5, name="Tapon")["bodies_created"][0]["id"]   # Ø45: 0,5 mm por lado
    plano = geo.Plano.desde_marco(np.zeros(3), np.array([0.0, -1.0, 0.0]), np.array([1.0, 0.0, 0.0]))           # el plano XZ por el eje
    cubiertos = []
    for cid in (tubo, tapon):
        forma = s.cuerpo(cid).forma
        datos = an.seccion_visual(forma, plano)
        tris = np.asarray(datos["triangulos"], float).reshape(-1, 3, 3)
        area = 0.5 * np.linalg.norm(np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0]), axis=1).sum()
        assert area == pytest.approx(an.seccion(forma, plano)["area"], rel=0.01)           # la tapa cubre todo el corte
        cubiertos += _intervalos(tris, 29.3)           # una altura sin vértices de la malla
    cubiertos.sort()
    huecos = [(a[1], b[0]) for a, b in zip(cubiertos, cubiertos[1:], strict=False) if b[0] - a[1] > 1e-6]
    assert len(huecos) == 2                                                                # dos franjas, una por lado
    assert [b - a for a, b in huecos] == pytest.approx([0.5, 0.5], abs=0.1)                # de la holgura (la malla del cilindro erra ~0,05)
    assert [a for a, _b in huecos] == pytest.approx([-23.0, 22.5], abs=0.1)

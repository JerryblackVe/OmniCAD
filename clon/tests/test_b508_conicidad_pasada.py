"""B-508: Extruir con conicidad negativa que pasa el vértice recorta ahí, como Fusion (antes: doble cono)."""
import math

import pytest

from omnicad import api


def _extruir(herramienta, angulo, **extra):
    s = api.Sesion()
    api.llamar(s, "create_sketch", {"plane": "XY", "name": "e"})
    api.llamar(s, "draw_circle", {"radius": 3, "center_x": 0, "center_y": 0, "sketch": "e"})
    r = api.llamar(s, herramienta, {"distance": 30, "taper_angle": angulo, **extra})
    assert r["ok"], r
    return api.llamar(s, "get_scene_info", {})["result"]["bodies"][0]


@pytest.mark.parametrize("angulo, esperado", [
    (-10, math.pi * 9 * 3 / math.tan(math.radians(10)) / 3),        # Fusion: cono hasta la punta, 160 mm³
    (-80, math.pi * 9 * 3 / math.tan(math.radians(80)) / 3),        # Fusion: 5 mm³ (antes 862.142)
    (-math.degrees(math.atan(3 / 30)), math.pi * 9 * 30 / 3),       # el punto exacto: Fusion 282,8 (antes, error)
    (-3, None),                                                     # sin llegar al vértice: el tronco de siempre
])
def test_b508_el_solido_se_recorta_en_el_vertice(angulo, esperado):
    cuerpo = _extruir("extrude", angulo, sketch="e", profile=0)
    if esperado is None:
        r2 = 3 - 30 * math.tan(math.radians(3))
        esperado = math.pi * 30 / 3 * (9 + 3 * r2 + r2 ** 2)
    assert cuerpo["volume"] == pytest.approx(esperado, rel=1e-3)


@pytest.mark.parametrize("angulo", [-10, -80])
def test_b508_la_superficie_tambien_se_recorta(angulo):
    h = 3 / math.tan(math.radians(-angulo))
    cuerpo = _extruir("create_surface_extrude", angulo, profiles=[{"sketch": "e", "profile": 0}])
    assert cuerpo["area"] == pytest.approx(math.pi * 3 * math.hypot(3, h), rel=1e-3)     # el lateral del cono


def _boceto(dibujar, **extrusion):
    s = api.Sesion()
    api.llamar(s, "create_sketch", {"plane": "XY", "name": "e"})
    dibujar(s)
    return s, api.llamar(s, "extrude", {"sketch": "e", "distance": 15, "taper_angle": -10, **extrusion})


def test_b508_un_cuello_angosto_no_acorta_la_pieza():
    """Se cierra la barra de 1 mm, no los cuadrados: no se recorta en silencio (sigue el error de siempre)."""
    pesa = [(0, 0), (10, 0), (10, 4.5), (14, 4.5), (14, 0), (24, 0), (24, 10), (14, 10), (14, 5.5), (10, 5.5), (10, 10),
            (0, 10)]

    def dibujar(s):
        for a, b in zip(pesa, pesa[1:] + pesa[:1], strict=True):
            api.llamar(s, "draw_line", {"sketch": "e", "start_x": a[0], "start_y": a[1], "end_x": b[0], "end_y": b[1]})
    s, r = _boceto(dibujar, profile=0)
    assert not r["ok"] and not api.llamar(s, "get_scene_info", {})["result"]["bodies"]


def test_b508_perfiles_vecinos_llegan_a_la_distancia():
    """La arista compartida no se inclina: cada rectángulo de 10×4 se cierra a 22,7 mm, no a 11,3."""
    def dibujar(s):
        api.llamar(s, "draw_rectangle", {"sketch": "e", "x1": 0, "y1": 0, "x2": 10, "y2": 4})
        api.llamar(s, "draw_rectangle", {"sketch": "e", "x1": 0, "y1": 4, "x2": 10, "y2": 8})
    s, r = _boceto(dibujar, profile=[0, 1])
    assert r["ok"], r
    assert [c["bounding_box"]["size"][2] for c in api.llamar(s, "get_scene_info", {})["result"]["bodies"]] == [15.0, 15.0]

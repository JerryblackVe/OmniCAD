"""SOL-10: Nervio y Red con ángulo de desmoldeo, dirección de extracción, inicio, empalme y «Extender curvas»."""
import math

import pytest

from omnicad import api
from omnicad.nucleo import geometria as geo


def _ok(s, nombre, **args):
    r = api.llamar(s, nombre, args)
    assert r["ok"], r
    return r["result"]


def _canal():
    """Canal en U de 40 x 20 x 20: paredes de 2 en x = 0..2 y 38..40, piso de 2 (z = 0..2), abierto arriba y de frente."""
    s = api.Sesion()
    cid = _ok(s, "create_box", length=40, width=20, height=20, anchor="corner")["bodies_created"][0]["id"]
    _ok(s, "create_box", length=36, width=20, height=18, x=2, z=2, anchor="corner", operation="cut", target=cid)
    return s, cid


def _linea(s, plano, offset, x1, y1, x2, y2):
    _ok(s, "create_construction_plane", plane=plano, offset=offset, name="Plano")
    b = _ok(s, "create_sketch", plane="Plano")["sketch"]["id"]
    _ok(s, "draw_line", sketch=b, start_x=x1, start_y=y1, end_x=x2, end_y=y2)
    return b


def _aumento(s, cid, antes):
    forma = s.cuerpo(cid).forma
    assert geo.es_valida(forma)
    return geo.volumen(forma) - antes


def test_nervio_con_desmoldeo_es_mas_fino_en_el_borde_libre():
    s, cid = _canal()
    antes = geo.volumen(s.cuerpo(cid).forma)
    b = _linea(s, "XZ", -10, 10, 8, 30, 8)               # línea a z = 8: el nervio baja hasta el piso (6 mm)
    _ok(s, "create_rib", sketch=b, thickness=2, target=cid, draft_angle=5)
    esperado = 36 * (6 * 2 + 2 * math.tan(math.radians(5)) * 18)
    assert _aumento(s, cid, antes) == pytest.approx(esperado, rel=1e-3)


def test_nervio_con_direccion_de_extraccion_explicita():
    s, cid = _canal()
    antes = geo.volumen(s.cuerpo(cid).forma)
    b = _linea(s, "XZ", -10, 10, 8, 30, 8)
    _ok(s, "create_rib", sketch=b, thickness=2, target=cid, draft_angle=5, pull_direction="Z")
    esperado = 36 * (6 * 2 + 2 * math.tan(math.radians(5)) * 18)
    assert _aumento(s, cid, antes) == pytest.approx(esperado, rel=1e-3)


@pytest.mark.parametrize("direction,y_centro", [("side1", 9.0), ("side2", 11.0), ("symmetric", 10.0)])
def test_nervio_inicio_abajo_o_arriba(direction, y_centro):
    s, cid = _canal()
    antes = s.cuerpo(cid).forma
    b = _linea(s, "XZ", -10, 10, 8, 30, 8)
    _ok(s, "create_rib", sketch=b, thickness=2, target=cid, direction=direction)
    nervio = geo.booleano(s.cuerpo(cid).forma, antes, "cortar")
    assert geo.volumen(nervio) == pytest.approx(36 * 6 * 2, rel=1e-5)
    assert geo.centro_masa(nervio)[1] == pytest.approx(y_centro, abs=1e-6)


def test_red_con_desmoldeo():
    s, cid = _canal()
    antes = geo.volumen(s.cuerpo(cid).forma)
    b = _linea(s, "XY", 12, 10, 10, 30, 10)
    _ok(s, "create_web", sketch=b, thickness=2, target=cid, draft_angle=5)
    esperado = 36 * (10 * 2 + 2 * math.tan(math.radians(5)) * 50)
    assert _aumento(s, cid, antes) == pytest.approx(esperado, rel=1e-3)


def test_red_sin_extender_las_curvas():
    s, cid = _canal()
    antes = geo.volumen(s.cuerpo(cid).forma)
    b = _linea(s, "XY", 12, 10, 10, 30, 10)
    _ok(s, "create_web", sketch=b, thickness=2, target=cid, extend_curves=False)
    assert _aumento(s, cid, antes) == pytest.approx(20 * 10 * 2, rel=1e-5)


def test_red_con_empalme_redondea_las_juntas_con_la_placa():
    """Una red suelta de 20 mm sobre la placa de una L: la junta mide 2 · 20 de los lados más 2 · 2 de los extremos."""
    s = api.Sesion()
    cid = _ok(s, "create_box", length=60, width=40, height=4, anchor="corner")["bodies_created"][0]["id"]
    _ok(s, "create_box", length=60, width=2, height=20, y=38, anchor="corner", operation="join", target=cid)   # el fondo alto
    antes = geo.volumen(s.cuerpo(cid).forma)
    b = _linea(s, "XY", 14, 10, 20, 30, 20)
    _ok(s, "create_web", sketch=b, thickness=2, target=cid, extend_curves=False)
    sin = _aumento(s, cid, antes)
    assert sin == pytest.approx(20 * 10 * 2, rel=1e-5)         # entre z = 4 y z = 14
    _ok(s, "undo")
    _ok(s, "create_web", sketch=b, thickness=2, target=cid, extend_curves=False, fillet_radius=1)
    extra = _aumento(s, cid, antes) - sin
    assert extra == pytest.approx(44 * (1 - math.pi / 4), abs=1.5)


def test_red_con_empalme_en_el_canal_es_valida_y_suma_material():
    s, cid = _canal()
    antes = geo.volumen(s.cuerpo(cid).forma)
    b = _linea(s, "XY", 12, 10, 10, 30, 10)
    _ok(s, "create_web", sketch=b, thickness=2, target=cid)
    sin = _aumento(s, cid, antes)
    _ok(s, "undo")
    _ok(s, "create_web", sketch=b, thickness=2, target=cid, fillet_radius=1)
    assert _aumento(s, cid, antes) > sin + 20


def test_argumentos_invalidos():
    s, cid = _canal()
    b = _linea(s, "XZ", -10, 10, 8, 30, 8)
    for args in ({"draft_angle": 60}, {"draft_angle": -50}, {"pull_direction": "no existe"}):
        r = api.llamar(s, "create_rib", dict(sketch=b, thickness=2, target=cid, **args))
        assert not r["ok"] and r["error_kind"] == "INVALID_ARGUMENTS", args
    r = api.llamar(s, "create_web", dict(sketch=b, thickness=2, target=cid, fillet_radius=-1))
    assert not r["ok"]

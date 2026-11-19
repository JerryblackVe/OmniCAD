# -*- coding: utf-8 -*-
"""Tests para opciones del comando Insertar SVG en boceto sin test automático previo
(OpcA: Escala, Desplazamiento Y, Ángulo, Volteo horizontal, Volteo vertical)."""
import pytest

from omnicad import api

SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="10mm" height="10mm" viewBox="0 0 10 10">
  <line x1="0" y1="0" x2="10" y2="4"/>
</svg>"""


def ok(r):
    assert r["ok"], r
    return r["result"]


@pytest.fixture
def svg(tmp_path):
    ruta = tmp_path / "dibujo.svg"
    ruta.write_text(SVG, encoding="utf-8")
    return ruta


@pytest.fixture
def s():
    sesion = api.Sesion()
    ok(api.llamar(sesion, "create_sketch", {"plane": "XY"}))
    return sesion


def _linea(sk):
    e = [e for e in sk["entities"] if e["type"] == "line"][0]
    return e["start"], e["end"]


def test_insert_svg_escala(s, svg):
    ok(api.llamar(s, "insert_svg", {"path": str(svg), "plane": "XY", "scale": 1.0, "name": "E1"}))
    ok(api.llamar(s, "insert_svg", {"path": str(svg), "plane": "XY", "scale": 2.0, "name": "E2"}))
    (x1a, y1a), (x2a, y2a) = _linea(ok(api.llamar(s, "get_sketch", {"sketch": "E1"})))
    (x1b, y1b), (x2b, y2b) = _linea(ok(api.llamar(s, "get_sketch", {"sketch": "E2"})))
    import math
    da = math.hypot(x2a - x1a, y2a - y1a)
    db = math.hypot(x2b - x1b, y2b - y1b)
    assert db == pytest.approx(2 * da, rel=0.05)


def test_insert_svg_desplazamiento_y(s, svg):
    ok(api.llamar(s, "insert_svg", {"path": str(svg), "plane": "XY", "y": 0.0, "name": "Y0"}))
    ok(api.llamar(s, "insert_svg", {"path": str(svg), "plane": "XY", "y": 50.0, "name": "Y50"}))
    (x1a, y1a), (x2a, y2a) = _linea(ok(api.llamar(s, "get_sketch", {"sketch": "Y0"})))
    (x1b, y1b), (x2b, y2b) = _linea(ok(api.llamar(s, "get_sketch", {"sketch": "Y50"})))
    assert y1b == pytest.approx(y1a + 50.0, abs=0.5)
    assert y2b == pytest.approx(y2a + 50.0, abs=0.5)


def test_insert_svg_angulo(s, svg):
    ok(api.llamar(s, "insert_svg", {"path": str(svg), "plane": "XY", "angle": 0.0, "name": "A0"}))
    ok(api.llamar(s, "insert_svg", {"path": str(svg), "plane": "XY", "angle": 90.0, "name": "A90"}))
    (x1a, y1a), (x2a, y2a) = _linea(ok(api.llamar(s, "get_sketch", {"sketch": "A0"})))
    (x1b, y1b), (x2b, y2b) = _linea(ok(api.llamar(s, "get_sketch", {"sketch": "A90"})))
    # tras girar 90°, la diferencia en X pasa a ser la diferencia original en Y (en valor absoluto)
    assert abs(x2b - x1b) == pytest.approx(abs(y2a - y1a), abs=0.5)
    assert abs(y2b - y1b) == pytest.approx(abs(x2a - x1a), abs=0.5)


def test_insert_svg_volteo_horizontal(s, svg):
    ok(api.llamar(s, "insert_svg", {"path": str(svg), "plane": "XY", "flip_h": False, "name": "H0"}))
    ok(api.llamar(s, "insert_svg", {"path": str(svg), "plane": "XY", "flip_h": True, "name": "H1"}))
    (x1a, y1a), (x2a, y2a) = _linea(ok(api.llamar(s, "get_sketch", {"sketch": "H0"})))
    (x1b, y1b), (x2b, y2b) = _linea(ok(api.llamar(s, "get_sketch", {"sketch": "H1"})))
    # espejo horizontal: el extremo que estaba a la izquierda queda a la derecha
    assert x1b == pytest.approx(x2a, abs=0.5)
    assert x2b == pytest.approx(x1a, abs=0.5)
    assert y1b == pytest.approx(y1a, abs=0.5)
    assert y2b == pytest.approx(y2a, abs=0.5)


def test_insert_svg_volteo_vertical(s, svg):
    ok(api.llamar(s, "insert_svg", {"path": str(svg), "plane": "XY", "flip_v": False, "name": "V0"}))
    ok(api.llamar(s, "insert_svg", {"path": str(svg), "plane": "XY", "flip_v": True, "name": "V1"}))
    (x1a, y1a), (x2a, y2a) = _linea(ok(api.llamar(s, "get_sketch", {"sketch": "V0"})))
    (x1b, y1b), (x2b, y2b) = _linea(ok(api.llamar(s, "get_sketch", {"sketch": "V1"})))
    assert y1b == pytest.approx(y2a, abs=0.5)
    assert y2b == pytest.approx(y1a, abs=0.5)
    assert x1b == pytest.approx(x1a, abs=0.5)
    assert x2b == pytest.approx(x2a, abs=0.5)

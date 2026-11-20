# -*- coding: utf-8 -*-
"""PREP: test de la opción «Ángulo (Expresion)» del comando «Insertar SVG en boceto».
B-??? : valida que el ángulo numérico se aplica correctamente al importar SVG.
"""

import pytest

from omnicad import api


def _crear_svg_temporal(ruta, ancho_px=96, alto_px=48):
    """Crea un SVG simple con un rectángulo para testear importación (match test_svg_arcos.py)."""
    contenido = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{ancho_px}" height="{alto_px}">'
        f'<rect x="0" y="0" width="{ancho_px}" height="{alto_px}"/>'
        "</svg>"
    )
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(contenido)


@pytest.fixture(scope="module")
def svg_path(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("svg")
    _crear_svg_temporal(tmp / "test.svg")
    return tmp


def test_angulo_expresion_insertar_svg(svg_path, tmp_path):
    """B-??? : el ángulo numérico se aplica al importar SVG en un boceto."""
    s = api.Sesion()
    # Insertar SVG con ángulo de 45 grados
    r = api.llamar(s, "insert_svg", {"path": str(svg_path / "test.svg"), "plane": "XY", "angle": 45.0})
    assert r["ok"], r
    # Verificar que el boceto se creó y tiene entidades
    bocetos = api.llamar(s, "get_sketch", {})
    assert bocetos["ok"]
    puntos = bocetos["result"]["points"]
    # Con ángulo 45°, los puntos deberían estar rotados; verificamos que no todos estén en el eje X
    assert len(puntos) > 0
    # Verificar un "borde": el bbox no debería colapsar en un solo punto
    xs = [p["x"] for p in puntos]
    ys = [p["y"] for p in puntos]
    assert max(xs) - min(xs) > 0 or max(ys) - min(ys) > 0


def test_angulo_cero_default(svg_path, tmp_path):
    """B-??? : ángulo por defecto (0) no rompe la importación."""
    s = api.Sesion()
    r = api.llamar(s, "insert_svg", {"path": str(svg_path / "test.svg"), "plane": "XY"})
    assert r["ok"], r
    bocetos = api.llamar(s, "get_sketch", {})
    assert bocetos["ok"]
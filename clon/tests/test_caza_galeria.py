# -*- coding: utf-8 -*-
"""AG-20: `scripts/caza/galeria.py` rehace un diseño mínimo con el formato del Fusion 360 Gallery (cm) y lo compara con su JSON.
Los datos reales son de investigación y no están en el repo: el diseño de acá es una caja de 4 x 3 x 2 cm hecha a mano."""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "scripts" / "caza"))

import galeria as g  # noqa: E402

PUNTOS = {"a": (0, 0), "b": (4, 0), "c": (4, 3), "d": (0, 3)}


def diseno(z_axis=(0, 0, 1), origen=(0, 0, 0), largo=2.0, volumen=24.0):
    pts = {k: {"x": x, "y": y, "z": 0.0} for k, (x, y) in PUNTOS.items()}
    curvas = {f"l{i}": {"type": "SketchLine", "start_point": a, "end_point": b} for i, (a, b) in
              enumerate(("ab", "bc", "cd", "da"))}
    vec = lambda v: {"x": v[0], "y": v[1], "z": v[2]}  # noqa: E731
    return {"timeline": [{"index": 0, "entity": "S"}, {"index": 1, "entity": "E"}],
            "entities": {
                "S": {"type": "Sketch", "points": pts, "curves": curvas, "reference_plane": {"type": "ConstructionPlane"},
                      "transform": {"origin": vec(origen), "x_axis": vec((1, 0, 0)), "y_axis": vec((0, 1, 0)), "z_axis": vec(z_axis)},
                      "profiles": {"P": {"properties": {"area": 12.0, "centroid": vec((2, 1.5, 0))}}}},
                "E": {"type": "ExtrudeFeature", "operation": "NewBodyFeatureOperation", "extent_type": "OneSideFeatureExtentType",
                      "start_extent": {"type": "ProfilePlaneStartDefinition"}, "profiles": [{"sketch": "S", "profile": "P"}],
                      "extent_one": {"distance": {"value": largo}, "taper_angle": {"value": 0.0}}}},
            "properties": {"volume": volumen, "area": 52.0, "bounding_box": {"min_point": vec((0, 0, 0)), "max_point": vec((4, 3, 2))}}}


def test_caja_igual_a_fusion():
    d = diseno()
    assert g.alcance(d) is None and g.rasgos(d) == ["nuevo"]
    assert g.comparar(d, g.rehacer(d)) == {}


def test_una_diferencia_de_volumen_se_nota():
    assert "volumen" in g.comparar(diseno(volumen=30.0), g.rehacer(diseno()))


def test_plano_inclinado_y_curvas_raras_quedan_fuera_de_alcance():
    assert g.alcance(diseno(z_axis=(0.6, 0, 0.8))) == "boceto en un plano inclinado"
    d = diseno()
    d["entities"]["S"]["curves"]["x"] = {"type": "SketchFittedSpline"}
    assert g.alcance(d) == "curva SketchFittedSpline"

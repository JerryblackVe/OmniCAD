"""B-663: «Cambiar a» Concéntrica o Igual (menú y `replace_constraint`) deja quieta la primera figura y mueve la
segunda, como B-657 al agregarlas."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from omnicad import api  # noqa: E402
from omnicad.restricciones import Boceto  # noqa: E402
from omnicad.timeline.parametros import TablaParametros  # noqa: E402


def _dos_circulos():
    b = Boceto()
    c1, c2 = b.agregar_circulo((0, 0), 10), b.agregar_circulo((30, 5), 8)
    rid = b.agregar_restriccion("igual", [c1, c2])      # hay que tener algo que cambiar
    return b, c1, c2, rid


def test_menu_cambiar_a_concentrica_mueve_la_segunda():
    from omnicad.ui import editor_boceto
    QApplication.instance() or QApplication([])
    b, c1, c2, rid = _dos_circulos()
    lz = editor_boceto.Lienzo(b, TablaParametros().evaluar)
    lz.resolver()
    centro1, centro2 = b.coords(b.curvas[c1].centro), b.coords(b.curvas[c2].centro)
    assert lz.reemplazar_restriccion(rid, "concentrica")
    assert b.coords(b.curvas[c1].centro) == pytest.approx(centro1)
    assert b.coords(b.curvas[c2].centro) == pytest.approx(centro1) and centro2 != pytest.approx(centro1)


def test_replace_constraint_a_concentrica_mueve_la_segunda():
    s = api.Sesion()
    r = api.llamar(s, "sketch_from_spec", {"name": "B", "entities": [
        {"type": "circle", "center": [0, 0], "radius": 10}, {"type": "circle", "center": [30, 5], "radius": 8}]})
    assert r["ok"], r
    h = r["result"]["handles"]
    r = api.llamar(s, "add_constraint", {"sketch": "B", "type": "equal", "entities": [h["e0"], h["e1"]]})
    assert r["ok"], r
    b = s.paso("B").boceto
    rid = next(iter(b.restricciones))
    r = api.llamar(s, "replace_constraint", {"sketch": "B", "constraint": rid, "type": "concentric"})
    assert r["ok"], r
    b = s.paso("B").boceto
    c1, c2 = sorted(b.curvas)[:2]
    assert b.coords(b.curvas[c1].centro) == pytest.approx((0, 0)) and b.coords(b.curvas[c2].centro) == pytest.approx((0, 0))

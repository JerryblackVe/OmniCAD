"""B-670: «Cambiar a» Igual sobre una restricción que ya existe deja quieta la primera figura y mueve la segunda,
tanto en el menú del Lienzo como en `replace_constraint` (lo que B-657/B-663 hacen al agregar). Concéntrica ya
queda cubierta por `test_b663_cambiar_a_mueve_la_segunda`."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from omnicad import api  # noqa: E402
from omnicad.restricciones import Boceto  # noqa: E402
from omnicad.timeline.parametros import TablaParametros  # noqa: E402


def test_menu_cambiar_a_igual_deja_quieto_el_primero():
    from omnicad.ui import editor_boceto
    QApplication.instance() or QApplication([])
    b = Boceto()
    c1, c2 = b.agregar_circulo((0, 0), 10), b.agregar_circulo((30, 5), 8)
    rid = b.agregar_restriccion("concentrica", [c1, c2])      # hay algo que cambiar
    lz = editor_boceto.Lienzo(b, TablaParametros().evaluar)
    lz.resolver()
    centro1, radio1 = b.coords(b.curvas[c1].centro), b.curvas[c1].radio
    centro2, radio2 = b.coords(b.curvas[c2].centro), b.curvas[c2].radio
    assert lz.reemplazar_restriccion(rid, "igual")
    assert b.coords(b.curvas[c1].centro) == pytest.approx(centro1)
    assert b.curvas[c1].radio == pytest.approx(radio1)
    assert b.coords(b.curvas[c2].centro) == pytest.approx(centro2)
    assert b.curvas[c2].radio == pytest.approx(radio1) and radio2 != pytest.approx(radio1)


def test_replace_constraint_a_equal_deja_quieto_el_primero():
    s = api.Sesion()
    r = api.llamar(s, "sketch_from_spec", {"name": "B", "entities": [
        {"type": "circle", "center": [0, 0], "radius": 10}, {"type": "circle", "center": [30, 5], "radius": 8}]})
    assert r["ok"], r
    h = r["result"]["handles"]
    r = api.llamar(s, "add_constraint", {"sketch": "B", "type": "concentric", "entities": [h["e0"], h["e1"]]})
    assert r["ok"], r
    b = s.paso("B").boceto
    rid = next(iter(b.restricciones))
    r = api.llamar(s, "replace_constraint", {"sketch": "B", "constraint": rid, "type": "equal"})
    assert r["ok"], r
    b = s.paso("B").boceto
    c1, c2 = sorted(b.curvas)[:2]
    assert b.coords(b.curvas[c1].centro) == pytest.approx((0, 0)) and b.curvas[c1].radio == pytest.approx(10)
    assert b.coords(b.curvas[c2].centro) == pytest.approx((0, 0))
    assert b.curvas[c2].radio == pytest.approx(10)      # era 8: se acomodó la segunda

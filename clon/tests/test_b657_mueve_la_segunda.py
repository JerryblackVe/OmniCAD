"""B-657: con el comando, Concéntrico, Punto medio e Igual dejan quieta la primera figura elegida y mueven (o cambian)
la segunda, como Fusion. Antes el solver repartía el cambio y las dos se movían a mitad de camino."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from omnicad.restricciones import Boceto  # noqa: E402
from omnicad.timeline.parametros import TablaParametros  # noqa: E402


def _lienzo(b):
    from omnicad.ui import editor_boceto
    QApplication.instance() or QApplication([])
    lz = editor_boceto.Lienzo(b, TablaParametros().evaluar)
    lz.resolver()
    return lz


def _aplicar(b, tipo, ents):
    lz = _lienzo(b)
    lz.set_herramienta("r_" + tipo)
    assert lz.aplicar_restriccion(tipo, ents)
    assert lz.resultado.ok


@pytest.mark.parametrize("orden", [0, 1])
def test_concentrica_mueve_la_segunda(orden):
    b = Boceto()
    c1, c2 = b.agregar_circulo((0, 0), 10), b.agregar_circulo((30, 5), 8)
    primera, segunda = (c1, c2) if orden == 0 else (c2, c1)
    centro, radios = b.coords(b.curvas[primera].centro), (b.curvas[c1].radio, b.curvas[c2].radio)
    _aplicar(b, "concentrica", [primera, segunda])
    assert b.coords(b.curvas[primera].centro) == pytest.approx(centro)
    assert b.coords(b.curvas[segunda].centro) == pytest.approx(centro)
    assert (b.curvas[c1].radio, b.curvas[c2].radio) == pytest.approx(radios)


def test_igual_cambia_la_segunda():
    b = Boceto()
    c1, c2 = b.agregar_circulo((0, 0), 10), b.agregar_circulo((30, 5), 8)
    _aplicar(b, "igual", [c2, c1])
    assert b.curvas[c1].radio == pytest.approx(8) and b.curvas[c2].radio == pytest.approx(8)
    assert b.coords(b.curvas[c2].centro) == pytest.approx((30, 5))


def test_igual_lineas_cambia_la_segunda():
    b = Boceto()
    l1, l2 = b.agregar_linea((0, 0), (40, 0)), b.agregar_linea((0, 20), (20, 20))
    _aplicar(b, "igual", [l1, l2])
    assert [c for p in b.curvas[l1].puntos() for c in b.coords(p)] == pytest.approx([0, 0, 40, 0])
    (x1, y1), (x2, y2) = (b.coords(p) for p in b.curvas[l2].puntos())
    assert ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5 == pytest.approx(40)


def test_punto_medio_punto_primero_mueve_la_linea():
    b = Boceto()
    p = b.agregar_punto(10, 30)
    l = b.agregar_linea((0, 0), (40, 0))
    _aplicar(b, "punto_medio", [p, l])
    assert b.coords(p) == pytest.approx((10, 30))
    (x1, y1), (x2, y2) = (b.coords(q) for q in b.curvas[l].puntos())
    assert ((x1 + x2) / 2, (y1 + y2) / 2) == pytest.approx((10, 30))


def test_punto_medio_linea_primero_mueve_el_punto():
    b = Boceto()
    p = b.agregar_punto(10, 30)
    l = b.agregar_linea((0, 0), (40, 0))
    _aplicar(b, "punto_medio", [l, p])
    assert [c for q in b.curvas[l].puntos() for c in b.coords(q)] == pytest.approx([0, 0, 40, 0])
    assert b.coords(p) == pytest.approx((20, 0))


def test_por_la_api_concentrica_mueve_la_segunda():
    from omnicad import api
    s = api.Sesion()

    def L(nombre, **a):
        r = api.llamar(s, nombre, a)
        assert r["ok"], (nombre, a, r)
        return r["result"]

    L("create_sketch", name="B", plane="XY")
    L("draw_circle", sketch="B", center_x=-5, center_y=-5, radius=10)
    L("draw_circle", sketch="B", center_x=30, center_y=5, radius=8)
    c1, c2 = [e["id"] for e in L("get_sketch", sketch="B")["entities"]]
    L("add_constraint", sketch="B", type="concentric", entities=[c2, c1])
    centros = {e["id"]: e["center"] for e in L("get_sketch", sketch="B")["entities"]}
    assert [c for k in (c1, c2) for c in centros[k]] == pytest.approx([30, 5, 30, 5])

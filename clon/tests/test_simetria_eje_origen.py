"""BOC-40: la simetría del boceto acepta como línea de simetría un eje del origen (X = -1, Y = -2), como Fusion
(«line or axis»), por el motor, la API (MCP y CLI) y el panel SIMETRÍA."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from omnicad import api  # noqa: E402
from omnicad.restricciones import Boceto, resolver  # noqa: E402
from omnicad.timeline.parametros import TablaParametros  # noqa: E402
from omnicad.ui.editor_boceto import Lienzo  # noqa: E402


def _plano(b, k):
    """Los cuatro números de los extremos de una línea."""
    return [v for q in b._extremos_linea(k) for v in q]


@pytest.mark.parametrize("eje,esperado", [(Boceto.EJE_Y, [-10, 5, -30, 12]), (Boceto.EJE_X, [10, -5, 30, -12])])
def test_reflejo_exacto_sobre_un_eje_del_origen(eje, esperado):
    b = Boceto()
    linea = b.agregar_linea((10, 5), (30, 12))
    (copia,) = b.simetria([linea], eje)
    assert _plano(b, copia) == pytest.approx(esperado, abs=1e-9)
    assert b.curvas[eje].proyectada and b.curvas[eje].construccion         # el eje queda como referencia fija
    assert any(r.tipo == "simetrica" and r.entidades[2] == eje for r in b.restricciones.values())
    b.agregar_restriccion("fijo", [linea])
    assert resolver(b, {}).ok


def test_la_copia_sigue_al_original_al_moverlo_con_el_eje_del_origen():
    b = Boceto()
    linea = b.agregar_linea((10, 5), (30, 12))
    (copia,) = b.simetria([linea], Boceto.EJE_Y)
    b.puntos[b.curvas[linea].p2].x = 40
    b.agregar_restriccion("fijo", [linea])
    assert resolver(b, {}).ok
    assert _plano(b, copia)[2:] == pytest.approx([-40, 12], abs=1e-6)


def test_lo_que_esta_sobre_el_eje_del_origen_no_se_copia_y_se_dice():
    b = Boceto()
    sobre = b.agregar_linea((0, 2), (0, 9))
    with pytest.raises(Exception, match="ya está sobre"):
        b.simetria([sobre], Boceto.EJE_Y)


def _llamar(s, nombre, **args):
    r = api.llamar(s, nombre, args)
    assert r["ok"], r
    return r["result"]


def test_api_mirror_sketch_con_el_eje_del_origen_y_error_con_un_id_inexistente():
    s = api.Sesion()
    _llamar(s, "create_sketch", name="S")
    linea = _llamar(s, "draw_line", start_x=10, start_y=5, end_x=30, end_y=12)["entities"][0]["id"]
    _llamar(s, "mirror_sketch", entities=[linea], axis=-2)
    lineas = [e for e in _llamar(s, "get_sketch", sketch="S")["entities"] if e["type"] == "line" and e["id"] != linea]
    assert any(sorted((e["start"][0], e["end"][0])) == [-30, -10] for e in lineas)
    r = api.llamar(s, "mirror_sketch", {"entities": [linea], "axis": -7})
    assert not r["ok"]


@pytest.fixture
def lienzo():
    app = QApplication.instance() or QApplication([])
    lz = Lienzo(Boceto(), TablaParametros().evaluar)
    lz.resize(800, 600)
    lz.ajustar_grilla = False
    lz.show()
    yield lz
    lz.close()
    lz.deleteLater()
    app.processEvents()


def _clic(lz, x, y):
    QTest.mouseClick(lz, Qt.LeftButton, Qt.NoModifier, lz.a_px(x, y).toPoint())


def test_panel_simetria_elige_el_eje_del_origen_con_un_clic_y_enter_lo_acepta(lienzo):
    lz = lienzo
    linea = lz.b.agregar_linea((10, 5), (30, 12))
    lz.resolver()
    lz.set_herramienta("simetria")
    lz.seleccion = [linea]
    lz.elegir_campo_simetria("eje")
    _clic(lz, 0.05, 40)                                               # sobre el eje Y del origen (a unos píxeles)
    assert lz._eje_simetria == Boceto.EJE_Y
    e = lz.estado_simetria()
    assert e["eje"] and e["valido"] and not e["error"]
    n = len(lz.b.curvas)
    QTest.keyClick(lz, Qt.Key_Return)
    assert lz.herramienta == "seleccionar" and lz.resultado.ok
    nuevas = [c for c in lz.b.curvas.values() if c.id not in (linea, Boceto.EJE_Y) and c.tipo == "linea"]
    assert len(lz.b.curvas) == n + 2 and len(nuevas) == 1                      # el eje y la copia
    assert _plano(lz.b, nuevas[0].id) == pytest.approx([-10, 5, -30, 12], abs=1e-6)
    lz.deshacer()
    assert len(lz.b.curvas) == n and Boceto.EJE_Y not in lz.b.curvas         # un solo paso de deshacer


def test_panel_simetria_eje_x_y_clic_lejos_de_los_ejes_sigue_diciendo_que_no(lienzo):
    lz = lienzo
    linea = lz.b.agregar_linea((10, 20), (30, 32))
    lz.resolver()
    lz.set_herramienta("simetria")
    lz.seleccion = [linea]
    lz.elegir_campo_simetria("eje")
    _clic(lz, 50, 50)                                                  # lejos de las dos rectas
    assert lz._eje_simetria is None and "no hay ninguna línea" in lz.estado_simetria()["error"]
    _clic(lz, 50, 0.04)                                                # sobre el eje X
    assert lz._eje_simetria == Boceto.EJE_X and lz.estado_simetria()["valido"]
    assert lz.aceptar_simetria()
    assert any(c.tipo == "linea" and _plano(lz.b, c.id) == pytest.approx([10, -20, 30, -32], abs=1e-6)
               for c in lz.b.curvas.values())

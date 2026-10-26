"""Gizmo de Insertar SVG / DXF: mover, girar, escalar y voltear el dibujo con el ratón (eventos al visor)."""
import math

import numpy as np
import pytest
from PySide6.QtCore import QEvent, Qt
from test_manipuladores import _arrastrar, _doc_rectangulo, _panel, _raton, app_qt  # noqa: F401  (fixture)

from omnicad.ui import manipuladores as mp
from omnicad.ui.comando import hit_desde_ref
from omnicad.ui.comandos.insertar import InsertarDXF, InsertarSVG


@pytest.fixture
def panel(app_qt):  # noqa: F811
    doc = _doc_rectangulo()
    plano = hit_desde_ref({"tipo": "plano", "id": "XY"}, doc.estado_final)
    p, visor, _ = _panel(InsertarSVG(), doc, {"plano": [plano]})
    visor.vista("arriba")
    p.manipuladores.actualizar()
    yield p
    p.cancelar()


def asa(p, clase, clave=None):
    return next(m for m in p.manipuladores.manips
                if isinstance(m, clase) and (clave is None or getattr(m, "clave", None) == clave))


def arrastrar(p, desde, hasta):
    g = p.manipuladores
    xy, ok = g.pantalla([desde, hasta])
    assert ok.all()
    _arrastrar(p.visor, *xy)


def test_svg_trae_las_siete_asas_y_dxf_tambien(panel):
    assert [type(m) for m in panel.manipuladores.manips] == [
        mp.PosicionCalcomania, mp.FlechaCalcomania, mp.FlechaCalcomania, mp.GiroCalcomania, mp.EscalaCalcomania,
        mp.Volteo, mp.Volteo]
    doc = _doc_rectangulo()
    plano = hit_desde_ref({"tipo": "plano", "id": "XY"}, doc.estado_final)
    p, _v, _ = _panel(InsertarDXF(), doc, {"plano": [plano]})
    assert len(p.manipuladores.manips) == 7
    p.cancelar()


def test_cuadrado_mueve_en_x_y_con_negativos(panel):
    m = asa(panel, mp.PosicionCalcomania)
    arrastrar(panel, m.punto, m.punto + m.u * 6 - m.v * 4)
    g = panel.manipuladores
    assert (g.valor("dx"), g.valor("dy")) == pytest.approx((6, -4), abs=0.3)


def test_giro_90_por_el_asa_y_la_caja_escribe_grados(panel):
    g = panel.manipuladores
    m = asa(panel, mp.GiroCalcomania)
    arrastrar(panel, m.asa(g), m._origen_arco(g) + m.v * m._r(g))
    assert g.valor("angulo") == pytest.approx(90, abs=0.5)
    assert "angulo" in g.cajas


def test_codo_cambia_la_escala_y_pasa_el_tope_de_cero(panel):
    g = panel.manipuladores
    m = asa(panel, mp.EscalaCalcomania)
    punta = m.puntos(g)[1]
    arrastrar(panel, punta, m.origen + (punta - m.origen) * 2)
    assert g.valor("escala") == pytest.approx(2, abs=0.05)
    arrastrar(panel, m.puntos(g)[1], m.origen + (m.puntos(g)[1] - m.origen) * 0.001)
    assert g.valor("escala") > 0                                 # nunca cero ni negativa


@pytest.mark.parametrize("clave", ["voltear_h", "voltear_v"])
def test_clic_en_el_mono_voltea_y_otro_clic_deshace(panel, clave):
    g = panel.manipuladores
    for esperado in (True, False):
        xy = g.pantalla([asa(panel, mp.Volteo, clave)._geom(g)[0]])[0][0]
        _raton(panel.visor, QEvent.MouseButtonPress, xy, Qt.LeftButton, Qt.LeftButton)
        _raton(panel.visor, QEvent.MouseButtonRelease, xy, Qt.LeftButton, Qt.NoButton)
        assert panel.valores[clave] is esperado


def test_lo_tecleado_mueve_el_gizmo(panel):
    antes = asa(panel, mp.PosicionCalcomania).punto.copy()
    panel.set_valor("dx", "12 mm")
    despues = asa(panel, mp.PosicionCalcomania).punto
    assert despues - antes == pytest.approx(np.array([12.0, 0, 0]), abs=1e-6)
    panel.set_valor("angulo", "45 deg")
    g = panel.manipuladores
    m = asa(panel, mp.GiroCalcomania)
    assert math.degrees(m._theta(g)) == pytest.approx(45)

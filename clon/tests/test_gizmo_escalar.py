"""Gizmo de Escalar: la flecha del factor (y las tres de «No uniforme») se arrastran con el ratón."""
import numpy as np
import pytest
from test_manipuladores import _arrastrar, _doc_caja, _hit_cuerpo, _panel, app_qt  # noqa: F401  (fixture)

from omnicad.ui import manipuladores as mp
from omnicad.ui.comandos.modificar import Escala


@pytest.fixture
def panel(app_qt):  # noqa: F811
    doc = _doc_caja()
    p, visor, _ = _panel(Escala(), doc, {"cuerpos": [_hit_cuerpo(doc)]})
    visor.vista("iso")
    p.manipuladores.actualizar()
    yield p, doc
    p.cancelar()


def flecha(p, clave):
    return next(m for m in p.manipuladores.manips if isinstance(m, mp.Flecha) and m.clave == clave)


def arrastrar(p, m, factores):
    """Tira de la flecha `factores` veces su largo de referencia (m.factor mm) a lo largo de su dirección."""
    g = p.manipuladores
    a, b = m.puntos(g)
    xy, ok = g.pantalla([(a + b) / 2, (a + b) / 2 + m.direccion * m.factor * factores])
    assert ok.all()
    _arrastrar(p.visor, *xy)


def test_sin_cuerpos_no_hay_asa_de_error_y_con_cuerpos_hay_una_flecha(panel):
    p, _doc = panel
    assert [m.clave for m in p.manipuladores.manips] == ["factor"]


def test_arrastrar_la_flecha_cambia_el_factor_y_nunca_baja_de_cero(panel):
    p, _ = panel
    g = p.manipuladores
    m = flecha(p, "factor")
    assert g.valor("factor") == 1 and "factor" in g.cajas
    arrastrar(p, m, 1)                                                  # un tamaño más lejos del punto base
    assert g.valor("factor") == pytest.approx(2, abs=0.1)
    arrastrar(p, m, -5)                                                 # del otro lado, pasando por cero
    assert g.valor("factor") == pytest.approx(0.001)
    p._calcular_previa()
    assert p._previa_ok


def test_teclear_el_factor_mueve_la_flecha(panel):
    p, _ = panel
    g = p.manipuladores
    antes = flecha(p, "factor").puntos(g)[0].copy()
    p.set_valor("factor", "3")
    despues = flecha(p, "factor").puntos(g)[0]
    assert np.linalg.norm(despues - flecha(p, "factor").origen) == pytest.approx(
        3 * np.linalg.norm(antes - flecha(p, "factor").origen))


def test_no_uniforme_tiene_una_flecha_por_eje_que_escribe_su_factor(panel):
    p, _ = panel
    p.set_valor("tipo", "no_uniforme")
    assert [m.clave for m in p.manipuladores.manips] == ["fx", "fy", "fz"]
    m = flecha(p, "fy")
    arrastrar(p, m, 0.5)
    assert p.manipuladores.valor("fy") == pytest.approx(1.5, abs=0.1)
    assert (p.manipuladores.valor("fx"), p.manipuladores.valor("fz")) == (1, 1)

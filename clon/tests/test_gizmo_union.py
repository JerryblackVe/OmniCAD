"""Gizmo de Unión: flechas de desfase sobre los ejes del marco del origen y arco del ángulo, arrastrables con el ratón."""
import numpy as np
import pytest
from test_manipuladores import _arrastrar, _doc_caja, _panel, app_qt  # noqa: F401  (fixture)

from omnicad.nucleo import geometria as g, referencias as refs
from omnicad.ui import manipuladores as mp
from omnicad.ui.comando import hit_desde_ref
from omnicad.ui.comandos.ensamblar import Union


def _cara(doc, centro):
    forma = doc.estado_final.cuerpos["op1.c1"].forma
    cara = next(c for c in refs.subformas(forma, "cara") if np.allclose(g.centro_masa(c, True), centro))
    return hit_desde_ref(refs.referencia("op1.c1", cara, caja=g.caja_envolvente(forma)), doc.estado_final)


@pytest.fixture
def panel(app_qt):  # noqa: F811
    doc = _doc_caja()
    p, visor, _ = _panel(Union(), doc, {"origen2": [_cara(doc, (10, 10, 20))]})
    visor.vista("iso")
    p.manipuladores.actualizar()
    yield p
    p.cancelar()


def asa(p, clave):
    return next(m for m in p.manipuladores.manips if getattr(m, "clave", None) == clave)


def arrastrar(p, m, mm):
    gm = p.manipuladores
    a, b = m.puntos(gm) if isinstance(m, mp.Flecha) else (m.asa(gm), m.asa(gm))
    medio = (a + b) / 2
    xy, ok = gm.pantalla([medio, medio + m.direccion * mm])
    assert ok.all()
    _arrastrar(p.visor, *xy)


def test_hay_tres_flechas_y_el_arco_del_angulo(panel):
    assert [m.clave for m in panel.manipuladores.manips] == ["dx", "dy", "dz", "angulo"]


def test_el_gizmo_sigue_los_ejes_de_la_cara_y_no_los_del_mundo(app_qt):  # noqa: F811
    doc = _doc_caja()
    p, _v, _ = _panel(Union(), doc, {"origen2": [_cara(doc, (20, 10, 10))]})        # cara lateral: su normal es +X
    dz = asa(p, "dz")
    assert np.allclose(dz.direccion, (1, 0, 0), atol=1e-6)
    assert np.allclose(dz.origen, (20, 10, 10), atol=1e-6)
    p.cancelar()


def test_arrastrar_la_flecha_z_escribe_el_desfase_y_se_puede_pasar_por_cero(panel):
    gm = panel.manipuladores
    arrastrar(panel, asa(panel, "dz"), 7)
    assert gm.valor("dz") == pytest.approx(7, abs=0.4)
    arrastrar(panel, asa(panel, "dz"), -12)
    assert gm.valor("dz") == pytest.approx(-5, abs=0.5)
    assert (gm.valor("dx"), gm.valor("dy")) == (0, 0)


def test_otras_flechas_siguen_al_desfase_acumulado(panel):
    panel.set_valor("dz", "6 mm")
    dx = asa(panel, "dx")
    assert dx.origen == pytest.approx((10, 10, 26), abs=1e-6)


def test_arco_del_angulo_gira_la_unión(panel):
    gm = panel.manipuladores
    m = asa(panel, "angulo")
    objetivo = m.centro + (m.u * np.cos(np.radians(60)) + m.v * np.sin(np.radians(60))) * m._r(gm)
    xy, ok = gm.pantalla([m.asa(gm), objetivo])
    assert ok.all()
    _arrastrar(panel.visor, *xy)
    assert gm.valor("angulo") == pytest.approx(60, abs=1.5)

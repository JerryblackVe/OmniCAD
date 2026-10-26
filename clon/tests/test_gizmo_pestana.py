"""Gizmo de la Pestaña de contorno de chapa: la flecha de distancia va hacia donde se extruye la chapa."""
import numpy as np
import pytest
from test_manipuladores import _arrastrar, _panel, app_qt  # noqa: F401  (fixture)

from omnicad.restricciones.boceto import Boceto
from omnicad.timeline.documento import Documento
from omnicad.timeline.operaciones import OpBoceto
from omnicad.ui import manipuladores as mp
from omnicad.ui.comando import hit_desde_ref
from omnicad.ui.comandos.chapa import Pestana


def _doc_perfil():
    doc = Documento()
    b = Boceto()
    b.agregar_linea((0, 0), (30, 0))
    b.agregar_linea((30, 0), (30, 15))
    doc.agregar(OpBoceto(doc.nuevo_id(), "Boceto1", plano="XY", boceto=b))
    return doc


def _panel_contorno(**valores):
    doc = _doc_perfil()
    curvas = [hit_desde_ref({"tipo": "curva_boceto", "boceto": "op1", "curva": c}, doc.estado_final)
              for c in doc.estado_final.bocetos["op1"].boceto.curvas]
    p, visor, estados = _panel(Pestana(), doc, {"tipo": "contorno", "curvas": curvas, "distancia": "10 mm", **valores})
    visor.vista("iso")
    p.manipuladores.actualizar()
    return p, estados


def _flechas(p):
    return {m.clave: m for m in p.manipuladores.manips if isinstance(m, mp.Flecha)}


def test_flecha_de_distancia_arrastra_y_la_chapa_crece_hacia_donde_apunta(app_qt):  # noqa: F811
    p, estados = _panel_contorno()
    gm = p.manipuladores
    f = _flechas(p)["distancia"]
    a, b = f.puntos(gm)
    xy, ok = gm.pantalla([(a + b) / 2, (a + b) / 2 + f.direccion * 5])
    assert ok.all()
    _arrastrar(p.visor, *xy)
    assert gm.valor("distancia") == pytest.approx(15, abs=0.7)
    p._calcular_previa()
    assert p._previa_ok
    from omnicad.nucleo import geometria as g
    cuerpo = next(iter(estados[-1].cuerpos.values()))
    caja = g.caja_envolvente(cuerpo.forma)
    z_medio = (caja[0][2] + caja[1][2]) / 2
    assert np.sign(z_medio) == np.sign(f.direccion[2]) and abs(caja[1][2] - caja[0][2]) > 14
    p.cancelar()


def test_dos_lados_trae_la_segunda_flecha_en_sentido_contrario_y_simetrica_usa_la_mitad(app_qt):  # noqa: F811
    p, _ = _panel_contorno(direccion="dos_lados", distancia2="6 mm")
    f = _flechas(p)
    assert set(f) == {"distancia", "distancia2"}
    assert np.allclose(f["distancia"].direccion, -f["distancia2"].direccion)
    p.cancelar()
    p, _ = _panel_contorno(direccion="simetrica")
    assert _flechas(p)["distancia"].factor == 0.5
    p.cancelar()


def test_pasar_por_cero_se_frena_en_un_valor_valido(app_qt):  # noqa: F811
    p, _ = _panel_contorno()
    gm = p.manipuladores
    f = _flechas(p)["distancia"]
    a, b = f.puntos(gm)
    xy, ok = gm.pantalla([(a + b) / 2, (a + b) / 2 - f.direccion * 40])
    _arrastrar(p.visor, *xy)
    assert gm.valor("distancia") == pytest.approx(0.01)
    p.cancelar()


# ---------------------------------------------------------------- pestaña de arista
def _panel_arista(**valores):
    from test_chapa import _doc_placa, _sub
    doc = _doc_placa()                                         # placa de 100 × 50 × 2; su arista de arriba en y = 50
    arista = _sub(doc, "arista", (50, 50, 2))
    p, visor, estados = _panel(Pestana(), doc, {"tipo": "arista", "aristas": [arista], "altura": "20 mm", **valores})
    visor.vista("iso")
    p.manipuladores.actualizar()
    return p, estados


def test_pestana_de_arista_tiene_flecha_de_altura_y_arco_del_angulo(app_qt):  # noqa: F811
    p, _ = _panel_arista()
    gm = p.manipuladores
    f = _flechas(p)["altura"]
    assert np.allclose(f.origen, (50, 50, 2)) and np.allclose(f.direccion, (0, 0, 1))      # 90°: recto hacia arriba
    arco = next(m for m in gm.manips if isinstance(m, mp.Angulo))
    assert arco.clave == "angulo" and np.allclose(arco.eje, (1, 0, 0)) and np.allclose(arco.u, (0, 1, 0))
    a, b = f.puntos(gm)
    xy, ok = gm.pantalla([(a + b) / 2, (a + b) / 2 + f.direccion * 7])
    _arrastrar(p.visor, *xy)
    assert gm.valor("altura") == pytest.approx(27, abs=0.7)
    arco = next(m for m in gm.manips if isinstance(m, mp.Angulo))
    objetivo = arco.centro + (arco.u * np.cos(np.radians(50)) + arco.v * np.sin(np.radians(50))) * arco._r(gm)
    xy, ok = gm.pantalla([arco.asa(gm), objetivo])
    _arrastrar(p.visor, *xy)
    assert gm.valor("angulo") == pytest.approx(50, abs=2)
    nueva = _flechas(p)["altura"]
    assert nueva.direccion == pytest.approx([0, np.cos(np.radians(gm.valor("angulo"))), np.sin(np.radians(gm.valor("angulo")))],
                                            abs=1e-6)                                   # la flecha sigue a la pestaña
    p.cancelar()


def test_pestana_de_arista_invertida_apunta_hacia_abajo(app_qt):  # noqa: F811
    p, _ = _panel_arista(invertir=True)
    assert np.allclose(_flechas(p)["altura"].direccion, (0, 0, -1))
    p.cancelar()


def test_la_flecha_de_la_pestana_va_hacia_donde_crece_la_chapa(app_qt):  # noqa: F811
    from omnicad.nucleo import geometria as geo
    p, estados = _panel_arista()
    p._calcular_previa()
    z0 = geo.caja_envolvente(estados[-1].cuerpos[next(iter(estados[-1].cuerpos))].forma)[1][2]
    p.set_valor("altura", "35 mm")
    p._calcular_previa()
    z1 = geo.caja_envolvente(estados[-1].cuerpos[next(iter(estados[-1].cuerpos))].forma)[1][2]
    assert z1 - z0 == pytest.approx(15, abs=1e-6)
    p.cancelar()

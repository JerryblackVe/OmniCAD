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

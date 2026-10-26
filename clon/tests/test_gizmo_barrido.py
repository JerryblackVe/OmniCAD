"""Gizmos del Barrido (sólido y de superficie): asa del largo sobre la ruta y arco de la torsión."""
import numpy as np
import pytest
from test_manipuladores import _arrastrar, _doc_rectangulo, _panel, app_qt  # noqa: F401  (fixture)

from omnicad.ui import manipuladores as mp
from omnicad.ui.comando import hit_desde_ref
from omnicad.ui.comandos import CATALOGO


def _abrir(clave):
    doc = _doc_rectangulo()
    curva = next(iter(doc.estado_final.bocetos["op1"].boceto.curvas))
    ruta = hit_desde_ref({"tipo": "curva_boceto", "boceto": "op1", "curva": curva}, doc.estado_final)
    p, visor, _ = _panel(CATALOGO[clave](), doc, {"ruta": [ruta]})
    visor.vista("iso")
    p.manipuladores.actualizar()
    return p


def test_barrido_asa_del_largo_por_la_ruta_y_arco_de_torsion(app_qt):  # noqa: F811
    p = _abrir("barrido")
    gm = p.manipuladores
    asa = next(m for m in gm.manips if isinstance(m, mp.AsaRuta))
    assert asa.clave == "distancia" and gm.valor("distancia") == 1
    xy, ok = gm.pantalla([asa.asa(gm), asa.puntos_ruta[40]])                         # a la mitad de la ruta
    assert ok.all()
    _arrastrar(p.visor, *xy)
    assert gm.valor("distancia") == pytest.approx(0.5, abs=0.03)
    p.set_valor("distancia", "0.25")
    nueva = next(m for m in gm.manips if isinstance(m, mp.AsaRuta))
    assert np.allclose(nueva.asa(gm), nueva.puntos_ruta[20], atol=0.3)              # teclear mueve el asa
    arco = next(m for m in gm.manips if isinstance(m, mp.Angulo))
    objetivo = arco.centro + (arco.u * np.cos(np.radians(50)) + arco.v * np.sin(np.radians(50))) * arco._r(gm)
    xy, ok = gm.pantalla([arco.asa(gm), objetivo])
    _arrastrar(p.visor, *xy)
    assert gm.valor("torsion") == pytest.approx(50, abs=2)
    p.cancelar()


def test_barrido_de_superficie_solo_tiene_el_arco_de_torsion(app_qt):  # noqa: F811
    p = _abrir("sup_barrido")
    assert [type(m).__name__ for m in p.manipuladores.manips] == ["Angulo"]
    p.cancelar()

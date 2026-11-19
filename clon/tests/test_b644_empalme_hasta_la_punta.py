# -*- coding: utf-8 -*-
"""B-644: el empalme de aristas que llegan a una punta (caras que convergen en un vértice, como la estrella del
exprimidor) tardaba minutos en OpenCascade (133 s una arista). Ahora se saca una bolita chica alrededor de la punta, se
empalma lo demás y se vuelve a pegar la punta; si eso falla, el empalme de siempre."""
import pytest
from OCP.BRep import BRep_Tool
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakePolygon, BRepBuilderAPI_MakeVertex
from OCP.BRepOffsetAPI import BRepOffsetAPI_ThruSections
from OCP.gp import gp_Pnt

from omnicad.nucleo import aislado
from omnicad.nucleo import geometria as geo
from omnicad.nucleo import solidos_modificar as sm


@pytest.fixture
def punta_agujereada(monkeypatch):
    """Una solevación de cuadrado a cuadrado a punta, ya modificada por un paso anterior (un agujero en la base)."""
    monkeypatch.setattr(aislado, "EN_HIJO", True)      # la revisión de cruces como en el trabajador, sin abrirlo
    s = BRepOffsetAPI_ThruSections(True, False)
    for a, z in ((20, 0), (10, 20)):
        s.AddWire(BRepBuilderAPI_MakePolygon(gp_Pnt(-a, -a, z), gp_Pnt(a, -a, z), gp_Pnt(a, a, z), gp_Pnt(-a, a, z), True).Wire())
    s.AddVertex(BRepBuilderAPI_MakeVertex(gp_Pnt(0, 0, 40)).Vertex())
    s.Build()
    forma = geo.booleano(geo.solidos(s.Shape())[0], geo.caja(10, 10, 5, (-5, -5, -1)), "cortar")
    crestas = [e for e in sm._aristas(forma) if not BRep_Tool.Degenerated_s(e) and sm._puntas(forma, [e])]
    assert len(crestas) == 4
    return forma, crestas[:1]


def _sin_via_rapida(monkeypatch, forma, aristas, r):
    with monkeypatch.context() as m:
        m.setattr(sm, "_puntas", lambda *a: [])
        return sm.empalme(forma, [{"aristas": aristas, "radio": r}])


def test_b644_via_rapida_da_el_mismo_empalme(punta_agujereada, monkeypatch):
    forma, aristas = punta_agujereada
    usada = []
    original = sm._empalme_sin_puntas
    monkeypatch.setattr(sm, "_empalme_sin_puntas", lambda *a: usada.append(1) or original(*a))
    rapido = sm.empalme(forma, [{"aristas": aristas, "radio": 0.3}])
    assert usada and geo.es_valida(rapido) and len(geo.solidos(rapido)) == 1
    normal = _sin_via_rapida(monkeypatch, forma, aristas, 0.3)
    assert geo.volumen(rapido) == pytest.approx(geo.volumen(normal), abs=1e-3)
    assert geo.volumen(rapido) < geo.volumen(forma)


@pytest.mark.parametrize("romper", [False, True])
def test_b644_si_la_via_rapida_falla_queda_el_empalme_de_siempre(punta_agujereada, monkeypatch, romper):
    """Radio 2 no entra junto a la bolita (la vía rápida falla sola); con `romper`, falla por cualquier otra cosa."""
    forma, aristas = punta_agujereada
    if romper:
        monkeypatch.setattr(sm, "_empalme_sin_puntas", lambda *a: 1 / 0)
    resultado = sm.empalme(forma, [{"aristas": aristas, "radio": 2.0}])
    normal = _sin_via_rapida(monkeypatch, forma, aristas, 2.0)
    assert geo.es_valida(resultado) and geo.volumen(resultado) == pytest.approx(geo.volumen(normal), abs=1e-6)

"""B-854: estos offsets no repiten la mutación in place de tolerancias de B-850.

Medición 24/11: vértices y aristas del cuerpo y de los perfiles cacheados quedaron en 1e-7 mm
antes y después de `_desfase_kernel`, del plan B del Vaciado y de `desfasar_superficie`.
"""
import pytest
from OCP.BRep import BRep_Tool
from OCP.TopAbs import TopAbs_EDGE, TopAbs_VERTEX
from OCP.TopExp import TopExp_Explorer
from OCP.TopoDS import TopoDS

from omnicad import api
from omnicad.nucleo import geometria as geo
from omnicad.nucleo import perfiles as pf
from omnicad.nucleo import solidos_modificar as sm
from omnicad.nucleo import superficies as sf

from test_b_633_repro import _ok


def _elementos(forma, tipo):
    exp = TopExp_Explorer(forma, tipo)
    elementos = []
    while exp.More():
        elementos.append(exp.Current())
        exp.Next()
    return elementos


def _maximo(forma, tipo, convertir):
    return max((BRep_Tool.Tolerance_s(convertir(e)) for e in _elementos(forma, tipo)), default=0.0)


def _tolerancias(forma):
    return (_maximo(forma, TopAbs_VERTEX, TopoDS.Vertex), _maximo(forma, TopAbs_EDGE, TopoDS.Edge))


def _entrada(monkeypatch):
    monkeypatch.setattr(pf, "_CACHE_PERFILES", {})
    s = api.Sesion()
    _ok(s, "create_sketch", plane="XY", name="Boceto1")
    _ok(s, "draw_circle", center_x=0, center_y=0, radius=10)
    r = _ok(s, "extrude", sketch="Boceto1", profile=0, distance=20)
    cid = r["bodies_created"][0]["id"]
    forma = s.cuerpo(cid).forma
    cache = [p.cara for grupo in pf._CACHE_PERFILES.values() for p in grupo]
    vertices = _elementos(forma, TopAbs_VERTEX)
    assert cache and any(v.IsPartner(w) for c in cache for w in _elementos(c, TopAbs_VERTEX) for v in vertices)
    formas = [forma, *cache]
    return forma, cache, formas, [_tolerancias(f) for f in formas]


@pytest.mark.parametrize("camino", ["cara", "vaciado", "superficie"])
def test_offsets_no_agrandan_tolerancias_compartidas(monkeypatch, camino):
    forma, cache, formas, antes = _entrada(monkeypatch)
    if camino == "cara":
        lado = next(c for c in geo.caras(forma) if sm._plano_de_cara(c) is None)
        resultado, dada_vuelta = sm._desfase_kernel(forma, [lado], 0.5)
        assert resultado is not None and not dada_vuelta
    elif camino == "vaciado":
        tapa = max(geo.caras(forma), key=lambda c: geo.centro_masa(c, True)[2])
        resultado = sm._cascara_por_desfase(forma, [tapa], 1.0)
    else:
        resultado = sf.desfasar_superficie(cache[0], 0.5)
    assert resultado is not None and geo.es_valida(resultado)
    assert [_tolerancias(f) for f in formas] == antes

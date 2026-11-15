# -*- coding: utf-8 -*-
"""FL-12: find_faces / find_edges calculan la huella del documento una vez por llamada (antes, una por id), y los ids
se siguen venciendo con un cambio."""
import pytest

from omnicad import api
from omnicad.api import selectores as sl


def _llamar(s, nombre, **argumentos):
    r = api.llamar(s, nombre, argumentos)
    assert r["ok"], r
    return r["result"]


def test_fl12_huella_una_vez_y_ids_vencen_sobre_cuerpo_ya_modificado(monkeypatch):
    s = api.Sesion()
    _llamar(s, "create_box", length=10, width=10, height=10)
    _llamar(s, "create_box", length=4, width=4, height=20, operation="join")      # el cuerpo ya modificado
    calculos, md5 = [], sl.hashlib.md5
    monkeypatch.setattr(sl.hashlib, "md5", lambda *a: calculos.append(1) or md5(*a))
    caras = _llamar(s, "find_faces")["faces"]
    aristas = _llamar(s, "find_edges")["edges"]
    assert len(caras) > 6 and len(aristas) > 12 and len(calculos) == 2               # una huella por llamada
    assert s._huella_fija is None                                                     # no queda fija afuera
    tapa = _llamar(s, "find_faces", selector=">Z")["faces"][0]["id"]
    assert _llamar(s, "measure_angle", a=tapa, b="<Z")["angle"] == pytest.approx(180)
    _llamar(s, "create_parameter", name="p", expression="1 mm")                      # cualquier cambio
    r = api.llamar(s, "measure_angle", {"a": tapa, "b": "<Z"})
    assert not r["ok"] and r["error_kind"] == "STALE_ID"
    nueva = _llamar(s, "find_faces", selector=">Z")["faces"][0]["id"]
    assert _llamar(s, "measure_angle", a=nueva, b="<Z")["angle"] == pytest.approx(180)

# -*- coding: utf-8 -*-
"""El trabajador de las previas arma la receta con los pasos lentos que la ventana ya calculó (B-834), no desde cero."""
import json
import os

import pytest

from omnicad import api
from omnicad.nucleo import aislado, geometria as geo
from omnicad.timeline import documento as doc_mod
from omnicad.timeline.documento import Documento


@pytest.fixture
def pesado(monkeypatch):
    """Un documento con un cuerpo YA modificado por un paso anterior (el corte), con todos sus pasos en la caché."""
    monkeypatch.setattr(doc_mod, "_SEGUNDOS_CACHE", 0.0)
    s = api.Sesion()
    assert api.llamar(s, "create_box", {"length": 40, "width": 30, "height": 20})["ok"]
    assert api.llamar(s, "create_cylinder", {"radius": 5, "height": 30, "x": 20, "y": 15})["ok"]
    assert api.llamar(s, "boolean_operation", {"target": "op1.c1", "tools": ["op2.c1"], "operation": "cut"})["ok"]
    assert api.llamar(s, "create_box", {"length": 10, "width": 10, "height": 10, "x": 100})["ok"]
    monkeypatch.setattr(s.doc, "_prevuelo_corresponde", lambda *a, **k: True)
    return s.doc


def _volumenes(doc):
    return {cid: round(geo.volumen(c.forma), 3) for cid, c in doc.estado_final.cuerpos.items()}


def test_el_trabajador_toma_los_pasos_de_la_ventana_y_borra_la_carpeta(pesado, monkeypatch):
    receta = pesado.a_dict()
    cache = aislado._cache_para_trabajador(pesado)
    assert cache and len(cache["pasos"]) >= 3 and os.path.isdir(cache["carpeta"])
    json.dumps(cache)                                   # viaja por la tubería del trabajador: tiene que ser JSON
    ejecutados = []
    original = Documento._de_cache
    monkeypatch.setattr(Documento, "_de_cache",
                        lambda self, i, op, estado: ejecutados.append((i, original(self, i, op, estado) is not None)) or original(self, i, op, estado))
    monkeypatch.setattr(aislado, "documento_vivo", None)
    aislado._calentar(receta, cache)
    assert all(tomado for _, tomado in ejecutados) and len(ejecutados) >= 3     # ninguno se rehízo
    assert not os.path.exists(cache["carpeta"])         # el trabajador la borra
    assert _volumenes(Documento.desde_dict(receta)) == _volumenes(pesado)


def test_una_cache_dañada_se_ignora_y_se_arma_todo(pesado, monkeypatch):
    receta = pesado.a_dict()
    cache = aislado._cache_para_trabajador(pesado)
    os.remove(os.path.join(cache["carpeta"], "cuerpos.brep"))      # el archivo no está: sin error visible, se recalcula
    monkeypatch.setattr(aislado, "documento_vivo", None)
    aislado._calentar(receta, cache)
    assert not os.path.exists(cache["carpeta"])


def test_si_no_hay_nada_que_valga_no_se_arma_cache(pesado, monkeypatch):
    assert aislado._cache_para_trabajador(None) is None
    monkeypatch.setattr(pesado, "_prevuelo_corresponde", lambda *a, **k: False)    # un documento liviano no la paga
    assert aislado._cache_para_trabajador(pesado) is None
    monkeypatch.setattr(pesado, "_prevuelo_corresponde", lambda *a, **k: True)
    monkeypatch.setattr(pesado, "pasos_para_cache", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    assert aislado._cache_para_trabajador(pesado) is None          # si falla, cae al camino normal sin avisar

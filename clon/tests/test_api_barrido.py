# -*- coding: utf-8 -*-
"""SC18: barrido de parámetros (`parameter_sweep`) sobre una copia del documento."""
import json

import pytest

from omnicad import api
from omnicad.timeline.documento import Documento
from omnicad.timeline.operaciones import OpPrimitiva


def _sesion(con_segundo_cuerpo=False):
    doc = Documento()
    s = api.Sesion(doc)
    api.llamar(s, "create_parameter", {"name": "ancho", "expression": 10})
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="ancho", largo="20", alto="5"))
    if con_segundo_cuerpo:
        doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="10", largo="20", alto="5", x="5"))
    return s


def ok(r):
    assert r["ok"], r
    return r["result"]


def test_barrido_de_volumen_y_el_documento_queda_intacto():
    s = _sesion()
    antes = json.dumps(s.doc.a_dict(), sort_keys=True)
    volumen_antes = ok(api.llamar(s, "get_physical_properties", {}))["total"]["volume"]
    r = ok(api.llamar(s, "parameter_sweep", {"parameter": "ancho", "start": 10, "stop": 30, "steps": 5}))
    assert [f["value"] for f in r["rows"]] == [10, 15, 20, 25, 30]
    assert [f["volume"] for f in r["rows"]] == [1000, 1500, 2000, 2500, 3000]
    assert "mass_g" in r["rows"][0] and "area" in r["rows"][0] and "bounding_box" in r["rows"][0]
    assert r["rows"][0]["mass_g"] is None                       # sin material: no hay masa que inventar
    assert r["parameter"] == "ancho" and r["unit"] == "mm" and r["document_changed"] is False
    assert json.dumps(s.doc.a_dict(), sort_keys=True) == antes
    assert ok(api.llamar(s, "get_physical_properties", {}))["total"]["volume"] == volumen_antes


def test_fila_con_error_no_corta_el_barrido():
    s = _sesion()
    r = ok(api.llamar(s, "parameter_sweep", {"parameter": "ancho", "start": -5, "stop": 15, "steps": 3}))
    assert [f["value"] for f in r["rows"]] == [-5, 5, 15]
    assert "Las medidas de la caja" in r["rows"][0]["error"]
    assert r["rows"][1]["volume"] == 500 and r["rows"][2]["volume"] == 1500


def test_solo_se_miden_las_medidas_pedidas():
    s = _sesion()
    r = ok(api.llamar(s, "parameter_sweep", {"parameter": "ancho", "start": 5, "stop": 10, "steps": 2,
                                             "measure": ["volume"]}))
    assert [set(f) for f in r["rows"]] == [{"value", "volume"}] * 2
    assert r["rows"][0]["volume"] == 500


def test_interferencia_en_cada_valor():
    s = _sesion(True)
    r = ok(api.llamar(s, "parameter_sweep", {"parameter": "ancho", "start": 5, "stop": 30, "steps": 3,
                                             "measure": ["interference"]}))
    # caja1: 0..ancho; caja2: 5..15. Con ancho 5 solo se tocan (sin interferencia); después se superponen.
    assert r["rows"][0]["interference"] is False
    assert all(f["interference"] for f in r["rows"][1:])


def test_parametro_de_texto_no_se_barre():
    s = _sesion()
    ok(api.llamar(s, "create_parameter", {"name": "rotulo", "expression": "hola", "kind": "text"}))
    r = api.llamar(s, "parameter_sweep", {"parameter": "rotulo", "start": 1, "stop": 2})
    assert r["ok"] is False and r["error_kind"] == "INVALID_ARGUMENTS" and "texto" in r["mensaje"]


def test_cancelado_corta_el_barrido():
    s = _sesion()
    from omnicad.api.herramientas_barrido import _barrido
    with pytest.raises(Exception, match="canceló"):
        _barrido(s, "ancho", 10, 30, 3, ["volume"], None, None, cancelado=lambda: True)
    assert json.dumps(s.doc.a_dict(), sort_keys=True) == json.dumps(
        _sesion().doc.a_dict(), sort_keys=True)          # el documento queda como estaba


@pytest.mark.parametrize("args, kind", [
    ({"parameter": "anchoo", "start": 10, "stop": 20}, "PARAMETER_NOT_FOUND"),
    ({"parameter": "ancho", "start": 10, "stop": 20, "steps": 0}, "INVALID_ARGUMENTS"),
    ({"parameter": "ancho", "start": 10, "stop": 20, "steps": 51}, "INVALID_ARGUMENTS"),
    ({"parameter": "ancho", "start": 10, "stop": 20, "measure": ["peso"]}, "INVALID_ARGUMENTS"),
    ({"parameter": "ancho", "start": 10, "stop": 20, "bodies": ["nope"]}, "BODY_NOT_FOUND"),
])
def test_errores_claros(args, kind):
    s = _sesion()
    r = api.llamar(s, "parameter_sweep", args)
    assert r["ok"] is False and r["error_kind"] == kind and r["pistas"]

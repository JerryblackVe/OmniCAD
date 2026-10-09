# -*- coding: utf-8 -*-
import math

import pytest

from omnicad import api
from omnicad.ejemplo import crear_documento_ejemplo


@pytest.fixture
def s():
    return api.Sesion(crear_documento_ejemplo())


def ok(r):
    assert r["ok"], r
    return r["result"]


def _volumen_placa(sesion):
    cuerpos = ok(api.llamar(sesion, "get_scene_info"))["bodies"]
    return next(c["volume"] for c in cuerpos if c["id"] == "op2.c1")


def test_cambiar_parametro_cambia_el_volumen(s):
    r = ok(api.llamar(s, "set_parameter", {"name": "ancho", "expression": "80 mm"}))
    assert r["value"] == 80 and r["previous_expression"] == "60 mm" and "Boceto placa" in r["used_by"]
    esperado = (80 * 40 - math.pi * 36) * 8 + math.pi * 16 * 12 - 2 / 3 * math.pi * 125
    assert _volumen_placa(s) == pytest.approx(esperado, rel=1e-6)
    ok(api.llamar(s, "undo"))
    assert _volumen_placa(s) == pytest.approx(esperado - 20 * 40 * 8, rel=1e-6)


def test_crear_usar_y_borrar(s):
    r = ok(api.llamar(s, "create_parameter", {"name": "espesor", "expression": 10, "comment": "nuevo"}))
    assert r == {"name": "espesor", "expression": "10.0", "value": 10.0, "unit": "mm", "kind": "length",
                 "comment": "nuevo", "used_by": []}
    ok(api.llamar(s, "set_parameter", {"name": "alto_placa", "expression": "espesor / 2"}))
    assert _volumen_placa(s) > 0
    assert api.llamar(s, "delete_parameter", {"name": "espesor"})["error_kind"] == "PARAMETER_IN_USE"
    assert api.llamar(s, "delete_parameter", {"name": "ancho"})["error_kind"] == "PARAMETER_IN_USE"
    ok(api.llamar(s, "set_parameter", {"name": "alto_placa", "expression": "8 mm"}))
    assert ok(api.llamar(s, "delete_parameter", {"name": "espesor"})) == {"name": "espesor", "deleted": True}
    nombres = [p["name"] for p in ok(api.llamar(s, "get_parameters"))["parameters"]]
    assert nombres == ["ancho", "alto_placa", "radio_agujero"]


def test_parametro_de_angulo():
    s = api.Sesion()
    r = ok(api.llamar(s, "create_parameter", {"name": "giro", "expression": "30 deg"}))
    assert (r["kind"], r["unit"], r["value"]) == ("angle", "deg", 30.0)
    assert ok(api.llamar(s, "create_parameter", {"name": "doble", "expression": "2 * giro"}))["value"] == 60


@pytest.mark.parametrize("herramienta, args, kind", [
    ("create_parameter", {"name": "ancho", "expression": "1"}, "PARAMETER_EXISTS"),
    ("create_parameter", {"name": "1x", "expression": "1"}, "INVALID_PARAMETER_NAME"),
    ("create_parameter", {"name": "mm", "expression": "1"}, "INVALID_PARAMETER_NAME"),
    ("create_parameter", {"name": "b", "expression": "ancho +"}, "INVALID_EXPRESSION"),
    ("create_parameter", {"name": "b", "expression": "no_existe * 2"}, "INVALID_EXPRESSION"),
    ("set_parameter", {"name": "anchoo", "expression": "1"}, "PARAMETER_NOT_FOUND"),
    ("set_parameter", {"name": "ancho", "expression": "30 deg"}, "UNIT_MISMATCH"),
    ("set_parameter", {"name": "ancho", "expression": "1 / 0"}, "INVALID_EXPRESSION"),
    ("set_parameter", {"name": "radio_agujero", "expression": "alto_placa"}, None),
    ("delete_parameter", {"name": "zz"}, "PARAMETER_NOT_FOUND"),
])
def test_errores_de_parametros(s, herramienta, args, kind):
    antes = s.doc.parametros.a_lista()
    r = api.llamar(s, herramienta, args)
    if kind is None:
        assert r["ok"]
        return
    assert r["ok"] is False and r["error_kind"] == kind and r["pistas"]
    assert s.doc.parametros.a_lista() == antes


def test_referencia_circular(s):
    ok(api.llamar(s, "create_parameter", {"name": "a", "expression": "ancho"}))
    r = api.llamar(s, "set_parameter", {"name": "ancho", "expression": "a + 1 mm"})
    assert r["error_kind"] == "CIRCULAR_REFERENCE"


def test_sugerencia_de_nombre(s):
    r = api.llamar(s, "set_parameter", {"name": "anchoo", "expression": "1"})
    assert "ancho" in r["pistas"][0]

# -*- coding: utf-8 -*-
"""Nombres, ids y expresiones (hallazgos de las pruebas de uso del 2026-10-09: L184, L186, L202, L226)."""
import importlib.util
import json
import logging
from pathlib import Path

import pytest

from omnicad import api
from omnicad.ejemplo import crear_documento_ejemplo
from omnicad.nucleo import geometria as geo


@pytest.fixture
def s():
    return api.Sesion(crear_documento_ejemplo())


def ok(r):
    assert r["ok"], r
    return r["result"]


def foto(sesion):
    doc = sesion.doc
    return (json.dumps(doc.a_dict(), sort_keys=True), [(r.estado, r.mensaje) for r in doc.resultados],
            len(doc._deshacer), len(doc._rehacer), doc.modificado, doc._contador)


# ---------------------------------------------------------------- L184: una sola fuente de verdad para el nombre
def test_renombrar_cuerpo_cambia_cuerpo_nombre(s, tmp_path):
    doc = s.doc
    ok(api.llamar(s, "rename", {"target": "op2.c1", "new_name": "Placa", "kind": "body"}))
    assert doc.estado_final.cuerpos["op2.c1"].nombre == "Placa"
    assert [c.id for c in doc.estado_final.cuerpos.values() if c.nombre == "Placa"] == ["op2.c1"]
    for i in range(len(doc.operaciones) + 1):              # todos los estados que tienen el cuerpo
        c = doc.estado_en(i).cuerpos.get("op2.c1")
        assert c is None or c.nombre == "Placa"
    ok(api.llamar(s, "undo"))
    assert doc.estado_final.cuerpos["op2.c1"].nombre != "Placa"
    ok(api.llamar(s, "redo"))
    assert doc.estado_final.cuerpos["op2.c1"].nombre == "Placa"
    ok(api.llamar(s, "save_document", {"path": str(tmp_path / "p.omnicad")}))
    ok(api.llamar(s, "open_document", {"path": str(tmp_path / "p.omnicad")}))
    assert s.doc.estado_final.cuerpos["op2.c1"].nombre == "Placa"


def test_quitar_renombre_vuelve_al_nombre_de_la_operacion(s):
    doc = s.doc
    original = doc.estado_final.cuerpos["op2.c1"].nombre
    doc.set_propiedad(["op2.c1"], "nombre", "Placa")
    doc.set_propiedad(["op2.c1"], "nombre", None)
    assert doc.estado_final.cuerpos["op2.c1"].nombre == original != "Placa"


def test_copia_de_cuerpo_renombrado(s):
    ok(api.llamar(s, "rename", {"target": "op2.c1", "new_name": "Placa", "kind": "body"}))
    r = ok(api.llamar(s, "move_body", {"body": "Placa", "translate": [0, 0, 50], "copy": True}))
    nuevo = s.doc.estado_final.cuerpos[r["bodies_created"][0]["id"]]
    assert nuevo.nombre.startswith("Placa") and nuevo.nombre != "Placa"
    assert geo.es_valida(nuevo.forma)


# ---------------------------------------------------------------- L226: ids, nombres de parámetro y contador
@pytest.mark.parametrize("nombre", ["op2", "OP12", "op3.c1"])
def test_rename_rechaza_nombres_con_forma_de_id(s, nombre):
    antes = foto(s)
    r = api.llamar(s, "rename", {"target": "op3", "new_name": nombre})
    assert r["error_kind"] == "INVALID_ARGUMENTS" and "forma de un id" in r["mensaje"]
    r = api.llamar(s, "rename", {"target": "op2.c1", "new_name": nombre, "kind": "body"})
    assert r["error_kind"] == "INVALID_ARGUMENTS"
    assert foto(s) == antes


def test_rename_a_su_propio_id_se_acepta(s):
    assert ok(api.llamar(s, "rename", {"target": "op3", "new_name": "op3"}))["new_name"] == "op3"
    assert s.paso("op3").id == "op3"


def test_parametro_con_enie_y_acentos(s, tmp_path):
    ok(api.llamar(s, "create_parameter", {"name": "ñandú", "expression": "3 mm"}))
    ok(api.llamar(s, "set_parameter", {"name": "ancho", "expression": "ñandú * 20"}))
    assert s.doc.parametros.valores()["ancho"] == pytest.approx(60)
    ok(api.llamar(s, "save_document", {"path": str(tmp_path / "n.omnicad")}))
    ok(api.llamar(s, "open_document", {"path": str(tmp_path / "n.omnicad")}))
    assert s.doc.parametros.valores()["ñandú"] == pytest.approx(3)


@pytest.mark.parametrize("nombre", ["lambda", "None", "ñandu", "2x", "a b"])
def test_parametro_nombres_invalidos(s, nombre):
    r = api.llamar(s, "create_parameter", {"name": nombre, "expression": "3 mm"})
    assert r["error_kind"] == "INVALID_PARAMETER_NAME", r


def test_llamada_que_falla_no_gasta_id(s):
    antes = foto(s)
    r = api.llamar(s, "loft", {"sketches": ["op1", "op5"], "operation": "join", "target": "zzz"})
    assert r["error_kind"] == "BODY_NOT_FOUND"
    assert foto(s) == antes
    r = ok(api.llamar(s, "create_box", {"length": 5, "width": 5, "height": 5}))
    assert r["feature"]["id"] == "op9" if "feature" in r else s.doc.operaciones[-1].id == "op9"


# ---------------------------------------------------------------- L186: expresiones y valores en edit_feature
def test_edit_feature_devuelve_expresion_y_valor(s):
    ok(api.llamar(s, "create_parameter", {"name": "placa", "expression": "3.2 mm"}))
    r = ok(api.llamar(s, "edit_feature", {"feature": "op3", "params": {"alto": "5 * placa"}}))
    assert r["params"]["alto"] == "5 * placa"
    assert r["values"]["alto"] == pytest.approx(16.0)
    paso = next(p for p in ok(api.llamar(s, "get_timeline"))["steps"] if p["id"] == "op2")
    assert paso["params"]["distancia"] == "alto_placa" and paso["values"]["distancia"] == pytest.approx(8)
    r = ok(api.llamar(s, "move_body", {"body": "op2.c1", "rotate": [0, 0, "30 deg"]}))
    mover = s.doc.operaciones[-1]
    paso = next(p for p in ok(api.llamar(s, "get_timeline"))["steps"] if p["id"] == mover.id)
    assert paso["values"]["rz"] == pytest.approx(30)


# ---------------------------------------------------------------- L202: tipos de referencia y logging
def test_edit_feature_pivote_origen_y_tipos(s, caplog):
    ok(api.llamar(s, "create_box", {"length": 10, "width": 10, "height": 10, "x": 20}))
    caja = s.doc.estado_final.cuerpos[s.doc.operaciones[-1].id + ".c1"].id
    ok(api.llamar(s, "move_body", {"body": caja, "rotate": [0, 0, 90]}))
    mover = s.doc.operaciones[-1].id
    ok(api.llamar(s, "edit_feature", {"feature": mover, "params": {"pivote": "origen"}}))
    assert s.doc.operacion(mover).p["pivote"] == {"tipo": "punto", "id": "O"}
    p0, p1 = geo.caja_envolvente(s.doc.estado_final.cuerpos[caja].forma)
    assert [(a + b) / 2 for a, b in zip(p0, p1, strict=True)][:2] == pytest.approx([0, 20], abs=1e-6)
    antes = foto(s)
    for params in ({"pivote": "abc"}, {"pivote": 5}, {"cuerpos": "op2.c1"}):
        r = api.llamar(s, "edit_feature", {"feature": mover, "params": params})
        assert r["error_kind"] == "INVALID_ARGUMENTS", r
        assert "inesperado" not in r["mensaje"]
    assert foto(s) == antes
    with caplog.at_level(logging.ERROR):
        nueva = s.doc.operacion(mover).copia()
        nueva.p["pivote"] = {"tipo": "eje", "id": "Z"}       # tipo equivocado: error limpio, sin traceback
        s.doc.reemplazar(mover, nueva)
    r = s.doc.resultado(mover)
    assert r.estado == "error" and "inesperado" not in r.mensaje.lower()
    assert not [x for x in caplog.records if x.levelno >= logging.ERROR]


def _modulo_app():
    ruta = Path(__file__).resolve().parents[1] / "OmniCAD.py"
    spec = importlib.util.spec_from_file_location("omnicad_app_prueba", ruta)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_log_sin_consola_va_a_archivo(monkeypatch, tmp_path):
    app = _modulo_app()
    assert isinstance(app._manejador_log(), logging.StreamHandler)
    monkeypatch.setattr("sys.stderr", None)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    h = app._manejador_log()
    try:
        assert isinstance(h, logging.FileHandler)
        h.emit(logging.LogRecord("x", logging.ERROR, __file__, 1, "prueba ñ", None, None))
    finally:
        h.close()
    assert "prueba ñ" in (tmp_path / "OmniCAD" / "omnicad.log").read_text(encoding="utf-8")

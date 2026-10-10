# -*- coding: utf-8 -*-
"""Convenciones cruzadas entre herramientas y receta: posición de create_box, nombres en edit_feature y
move_body (desplazamiento relativo, pivote editable)."""
import pytest

from omnicad import api
from omnicad.nucleo import geometria as geo
from omnicad.timeline.operaciones import OpPrimitiva


@pytest.fixture
def s():
    return api.Sesion()


def ok(r):
    assert r["ok"], r
    return r["result"]


def llamar(sesion, nombre, **args):
    return ok(api.llamar(sesion, nombre, args))


def caja(sesion, cid):
    c = sesion.cuerpo(cid)
    assert geo.es_valida(c.forma)
    (a, b) = geo.caja_envolvente(c.forma)
    return [round(v, 4) for v in a + b]


def test_create_box_y_edit_feature_usan_el_mismo_centro(s):
    r = llamar(s, "create_box", length=50, width=10, height=5, x=20)
    cid, paso = r["bodies_created"][0]["id"], r["feature"]["id"]
    assert caja(s, cid) == [-5, -5, 0, 45, 5, 5]
    llamar(s, "edit_feature", feature=paso, params={"x": "20 mm"})
    assert caja(s, cid) == [-5, -5, 0, 45, 5, 5]
    llamar(s, "edit_feature", feature=paso, params={"x": "30 mm"})
    assert caja(s, cid) == [5, -5, 0, 55, 5, 5]


def test_receta_vieja_sin_caja_centrada_sigue_en_la_esquina(s):
    # Paso como lo guardaba una receta vieja: sin la clave caja_centrada.
    s.doc.agregar(OpPrimitiva(s.doc.nuevo_id(), forma="caja", ancho="50", largo="10", alto="5", x="20"))
    cid = next(iter(s.doc.estado_final.cuerpos))
    assert caja(s, cid) == [20, 0, 0, 70, 10, 5]


def test_edit_feature_acepta_los_nombres_de_create_box(s):
    r = llamar(s, "create_box", length=50, width=10, height=5)
    cid, paso = r["bodies_created"][0]["id"], r["feature"]["id"]
    llamar(s, "edit_feature", feature=paso, params={"length": "60 mm", "width": "20 mm", "height": 8})
    assert caja(s, cid) == [-30, -10, 0, 30, 10, 8]
    mal = api.llamar(s, "edit_feature", {"feature": paso, "params": {"length": 1, "ancho": 2}})
    assert not mal["ok"] and mal["error_kind"] == "INVALID_ARGUMENTS"
    mal = api.llamar(s, "edit_feature", {"feature": paso, "params": {"foo": 1}})
    assert not mal["ok"] and "length (= ancho)" in " ".join(mal["pistas"])


def test_move_body_informa_el_centro_antes_y_despues(s):
    r = llamar(s, "create_box", length=10, width=10, height=10, z=10)
    cid = r["bodies_created"][0]["id"]
    m = llamar(s, "move_body", body=cid, translate=[0, 0, 15.5])
    assert m["center"] == {"before": [0, 0, 15], "after": [0, 0, 30.5]}


def _rueda(s):
    llamar(s, "create_parameter", name="perno", expression="40 mm")
    d = llamar(s, "create_cylinder", radius=50, height=20)["bodies_created"][0]["id"]
    llamar(s, "create_cylinder", radius=5, height="perno", z=20, operation="join", target=d)
    return d


def test_pivote_origin_editable_y_estable(s):
    d = _rueda(s)
    paso = llamar(s, "move_body", body=d, rotate=[90, 0, 0])["feature"]["id"]
    llamar(s, "edit_feature", feature=paso, params={"pivot": "origin"})
    assert s.paso(paso).p["pivote"] == {"tipo": "punto", "id": "O"}
    antes = caja(s, d)
    assert antes[2] == pytest.approx(-50) and antes[5] == pytest.approx(50)
    llamar(s, "set_parameter", name="perno", expression="25 mm")
    despues = caja(s, d)
    assert despues[2] == pytest.approx(-50) and despues[5] == pytest.approx(50)
    llamar(s, "edit_feature", feature=paso, params={"pivote": "center"})
    assert s.paso(paso).p["pivote"] is None


def test_pivote_invalido_no_toca_el_documento(s):
    d = _rueda(s)
    paso = llamar(s, "move_body", body=d, rotate=[90, 0, 0])["feature"]["id"]
    receta = s.doc.a_dict()
    mal = api.llamar(s, "edit_feature", {"feature": paso, "params": {"pivote": "foo"}})
    assert not mal["ok"] and mal["error_kind"] == "INVALID_ARGUMENTS"
    assert s.doc.a_dict() == receta


def test_dialogo_primitiva_conserva_caja_centrada(s, qapp=None):
    from PySide6.QtWidgets import QApplication, QLabel
    app = QApplication.instance() or QApplication([])
    from omnicad.ui.dialogos import DialogoPrimitiva
    paso = llamar(s, "create_box", length=50, width=10, height=5, x=20)["feature"]["id"]
    dlg = DialogoPrimitiva(s.doc, op=s.paso(paso))
    assert any(w.text() == "La posición es el centro de la base." for w in dlg.findChildren(QLabel))
    assert dlg.crear_operacion().p["caja_centrada"] is True
    dlg.deleteLater()
    app.processEvents()

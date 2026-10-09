# -*- coding: utf-8 -*-
import json
import math

import pytest

from omnicad import api
from omnicad.ejemplo import crear_documento_ejemplo
from omnicad.timeline.documento import Documento

from omnicad.api import registro as cat

VOL_PLACA = (60 * 40 - math.pi * 36) * 8 + math.pi * 16 * 12 - 2 / 3 * math.pi * 125


@pytest.fixture
def s():
    return api.Sesion(crear_documento_ejemplo())


def ok(r):
    assert r["ok"], r
    return r["result"]


def foto(sesion):
    """Todo lo que una falla atómica no debe cambiar."""
    doc = sesion.doc
    return (json.dumps(doc.a_dict(), sort_keys=True), [(r.estado, r.mensaje) for r in doc.resultados],
            len(doc._deshacer), len(doc._rehacer), doc.modificado)


def test_escena_del_ejemplo(s):
    info = ok(api.llamar(s, "get_scene_info"))
    assert info["name"] == "Ejemplo" and info["path"] is None and info["modified"] is False
    assert info["units"] == {"length": "mm", "angle": "deg"} and info["timeline_steps"] == 8
    placa = next(c for c in info["bodies"] if c["id"] == "op2.c1")
    assert placa["type"] == "solid" and placa["volume"] == pytest.approx(VOL_PLACA, rel=1e-6)
    assert placa["bounding_box"]["size"] == pytest.approx([60, 40, 20], abs=1e-3)
    assert {b["plane"] for b in info["sketches"]} == {"XY", "XZ"}
    assert all(b["profiles"] >= 1 for b in info["sketches"])
    assert [p["name"] for p in info["parameters"]] == ["ancho", "alto_placa", "radio_agujero"]


def test_timeline(s):
    t = ok(api.llamar(s, "get_timeline"))
    assert t["marker"] == 8 and [p["index"] for p in t["steps"]] == list(range(8))
    assert all(p["status"] == "ok" for p in t["steps"])
    assert t["steps"][1]["params"]["distancia"] == "alto_placa"
    corto = ok(api.llamar(s, "get_timeline", {"include_params": False}))
    assert "params" not in corto["steps"][0]


def test_atomicidad_operacion_que_falla(s):
    antes = foto(s)
    r = api.llamar(s, "edit_feature", {"feature": "op8", "params": {"objetivo": "no_existe"}})
    assert not r["ok"] and r["error_kind"] == "BODY_NOT_FOUND" and "Unir aro y toroide" in r["mensaje"]
    assert foto(s) == antes
    r = api.llamar(s, "set_parameter", {"name": "alto_placa", "expression": "0 mm"})
    assert not r["ok"] and r["error_kind"] == "OPERATION_FAILED" and "op2" in r["mensaje"]
    assert foto(s) == antes
    r = api.llamar(s, "delete_feature", {"feature": "Boceto placa"})       # excepción del núcleo
    assert r["error_kind"] == "FEATURE_IN_USE"
    assert foto(s) == antes


def test_atomicidad_conserva_rehacer(s):
    ok(api.llamar(s, "rename", {"target": "op3", "new_name": "Columna"}))
    ok(api.llamar(s, "undo"))
    antes = foto(s)
    assert api.llamar(s, "set_parameter", {"name": "alto_placa", "expression": "0"})["ok"] is False
    assert foto(s) == antes
    ok(api.llamar(s, "redo"))
    assert s.doc.operacion("op3").nombre == "Columna"


def test_aviso_no_deshace(s):
    r = api.llamar(s, "suppress_feature", {"feature": "extrusión PLACA"})
    assert r["ok"] and r["result"]["suppressed"] is True
    assert any("Pilar" in a for a in r["avisos"])
    assert ok(api.llamar(s, "get_timeline"))["steps"][1]["status"] == "suppressed"
    ok(api.llamar(s, "suppress_feature", {"feature": "op2", "suppressed": False}))
    assert ok(api.llamar(s, "get_timeline"))["steps"][1]["status"] == "ok"


def test_deshacer_y_rehacer(s):
    s.doc._deshacer.clear()
    assert api.llamar(s, "undo")["error_kind"] == "NOTHING_TO_UNDO"
    ok(api.llamar(s, "edit_feature", {"feature": "Pilar", "params": {"alto": "30 mm"}}))
    ok(api.llamar(s, "rename", {"target": "op3", "new_name": "Columna"}))
    assert ok(api.llamar(s, "undo"))["can_redo"] is True
    assert s.doc.operacion("op3").nombre == "Pilar" and s.doc.operacion("op3").p["alto"] == "30 mm"
    ok(api.llamar(s, "undo"))
    assert s.doc.operacion("op3").p["alto"] == "20 mm"
    assert api.llamar(s, "undo")["error_kind"] == "NOTHING_TO_UNDO"
    ok(api.llamar(s, "redo"))
    ok(api.llamar(s, "redo"))
    assert s.doc.operacion("op3").nombre == "Columna" and s.doc.operacion("op3").p["alto"] == "30 mm"
    assert api.llamar(s, "redo")["error_kind"] == "NOTHING_TO_REDO"


def test_una_herramienta_es_un_paso_de_deshacer(s):
    @api.herramienta("_prueba_dos_cambios", "prueba", "Dos cambios internos.", modifica=True)
    def dos(sesion):
        sesion.doc.renombrar("op3", "A")
        sesion.doc.renombrar("op4", "B")
    try:
        s.doc._deshacer.clear()
        ok(api.llamar(s, "_prueba_dos_cambios"))
        assert len(s.doc._deshacer) == 1
        ok(api.llamar(s, "undo"))
        assert (s.doc.operacion("op3").nombre, s.doc.operacion("op4").nombre) == ("Pilar", "Hueco esférico")
    finally:
        cat._CATALOGO.pop("_prueba_dos_cambios")


def test_edit_feature_valida_parametros(s):
    r = api.llamar(s, "edit_feature", {"feature": "op3", "params": {"altura": "3"}})
    assert r["error_kind"] == "INVALID_ARGUMENTS" and any("alto" in p for p in r["pistas"])
    r = api.llamar(s, "edit_feature", {"feature": "op99", "params": {"alto": "3"}})
    assert r["error_kind"] == "FEATURE_NOT_FOUND"
    r = api.llamar(s, "edit_feature", {"feature": "pilarr", "params": {"alto": "3"}})
    assert r["error_kind"] == "FEATURE_NOT_FOUND" and "Pilar" in r["pistas"][0]
    vol = ok(api.llamar(s, "get_scene_info"))["bodies"][0]["volume"]
    ok(api.llamar(s, "edit_feature", {"feature": "PILAR", "params": {"alto": 30}}))   # número = mm
    assert ok(api.llamar(s, "get_scene_info"))["bodies"][0]["volume"] == pytest.approx(vol + math.pi * 16 * 10)


def test_edit_feature_no_acepta_selectores_en_referencias():
    """Prueba K real: un agente hizo edit_feature(params={"caras": [">Z", "<Z"]}) sobre un vaciado y el paso caía con
    «string indices must be integers». Ahora: INVALID_ARGUMENTS con la salida (borrar y recrear, o undo)."""
    s = api.Sesion()
    ok(api.llamar(s, "create_box", {"length": 20, "width": 20, "height": 20}))
    paso = ok(api.llamar(s, "shell", {"body": "Cuerpo1", "faces": ">Z", "thickness": 2}))
    vol = ok(api.llamar(s, "get_scene_info"))["bodies"][0]["volume"]
    pid = ok(api.llamar(s, "get_timeline"))["steps"][-1]["id"]
    r = api.llamar(s, "edit_feature", {"feature": pid, "params": {"caras": [">Z", "<Z"]}})
    assert r["error_kind"] == "INVALID_ARGUMENTS" and "delete_feature" in r["pistas"][0], (r, paso)
    assert ok(api.llamar(s, "get_scene_info"))["bodies"][0]["volume"] == pytest.approx(vol)   # quedó igual


def test_expresion_entre_comillas_se_acepta():
    """Prueba K real: 12 create_parameter fallaron porque el agente mandó expression="\\"60 mm\\"" (con comillas)."""
    s = api.Sesion()
    ok(api.llamar(s, "create_parameter", {"name": "L", "expression": '"60 mm"'}))
    ok(api.llamar(s, "create_parameter", {"name": "M", "expression": "'L / 2'"}))
    params = {p["name"]: p for p in ok(api.llamar(s, "get_parameters"))["parameters"]}
    assert params["L"]["value"] == pytest.approx(60) and params["M"]["value"] == pytest.approx(30)
    assert params["L"]["expression"] == "60 mm"          # se guarda limpia, sin comillas


def test_nombre_ambiguo(s):
    s.doc.renombrar("op4", "Pilar")
    r = api.llamar(s, "delete_feature", {"feature": "pilar"})
    assert r["error_kind"] == "AMBIGUOUS_REFERENCE" and "op3" in r["mensaje"] and "op4" in r["mensaje"]


def test_renombrar_cuerpo_y_paso(s):
    r = ok(api.llamar(s, "rename", {"target": "cuerpo1", "new_name": "Placa"}))
    assert r == {"kind": "body", "id": "op2.c1", "old_name": "Cuerpo1", "new_name": "Placa"}
    assert ok(api.llamar(s, "get_scene_info"))["bodies"][0]["name"] == "Placa"
    assert ok(api.llamar(s, "rename", {"target": "op1", "new_name": "Base"}))["kind"] == "feature"
    assert api.llamar(s, "rename", {"target": "nada", "new_name": "x"})["error_kind"] == "NOT_FOUND"
    assert api.llamar(s, "rename", {"target": "op1", "new_name": "  "})["error_kind"] == "INVALID_ARGUMENTS"
    assert api.llamar(s, "rename", {"target": "Placa", "new_name": "x", "kind": "feature"})["error_kind"] \
        == "FEATURE_NOT_FOUND"


def test_borrar_paso(s):
    assert api.llamar(s, "delete_feature", {"feature": "Toroide"})["error_kind"] == "FEATURE_IN_USE"
    r = ok(api.llamar(s, "delete_feature", {"feature": "Unir aro y toroide"}))
    assert r == {"id": "op8", "name": "Unir aro y toroide", "type": "combinar", "deleted": True}
    ok(api.llamar(s, "delete_feature", {"feature": "Toroide"}))
    assert ok(api.llamar(s, "get_scene_info"))["timeline_steps"] == 6


def test_guardar_y_abrir_ida_y_vuelta(s, tmp_path):
    assert api.llamar(s, "save_document")["error_kind"] == "MISSING_PATH"
    r = ok(api.llamar(s, "save_document", {"path": str(tmp_path / "pieza")}))
    assert r["path"].endswith("pieza.omnicad") and r["name"] == "pieza"
    info = ok(api.llamar(s, "get_scene_info"))
    assert info["modified"] is False and info["path"].endswith("pieza.omnicad")
    ok(api.llamar(s, "save_document"))                                   # mismo archivo: no pide overwrite

    otra = api.Sesion()
    abierta = ok(api.llamar(otra, "open_document", {"path": r["path"]}))
    assert abierta["bodies"] == info["bodies"] and abierta["parameters"] == info["parameters"]
    assert ok(api.llamar(otra, "get_timeline")) == ok(api.llamar(s, "get_timeline"))

    r2 = api.llamar(otra, "save_document", {"path": str(tmp_path / "copia.omnicad")})
    assert r2["ok"]
    assert api.llamar(s, "save_document", {"path": r2["result"]["path"]})["error_kind"] == "FILE_EXISTS"
    assert api.llamar(s, "save_document", {"path": r2["result"]["path"], "overwrite": True})["ok"]


def test_guardar_le_pone_al_documento_el_nombre_del_archivo(tmp_path):
    """Como en Fusion: guardar en pieza.omnicad llama «pieza» al documento, y el archivo guarda ese mismo nombre
    (antes el manifiesto se quedaba con el nombre viejo y al reabrir con la API volvía «Soporte»)."""
    s = api.Sesion()
    ok(api.llamar(s, "new_document", {"name": "Soporte"}))
    r = ok(api.llamar(s, "save_document", {"path": str(tmp_path / "pieza.omnicad")}))
    assert r["name"] == "pieza"
    otra = api.Sesion()
    assert ok(api.llamar(otra, "open_document", {"path": r["path"]}))["name"] == "pieza"
    # si no se puede escribir, el nombre no cambia
    assert api.llamar(s, "save_document", {"path": str(tmp_path / "no_existe" / "x.omnicad")})["ok"] is False
    assert ok(api.llamar(s, "get_scene_info"))["name"] == "pieza"


def test_errores_de_archivo(s, tmp_path):
    assert api.llamar(s, "open_document", {"path": str(tmp_path / "no.omnicad")})["error_kind"] == "FILE_NOT_FOUND"
    basura = tmp_path / "roto.omnicad"
    basura.write_bytes(b"no es un zip")
    antes = s.doc
    assert api.llamar(s, "open_document", {"path": str(basura)})["error_kind"] == "INVALID_PROJECT"
    assert s.doc is antes
    r = api.llamar(s, "save_document", {"path": str(tmp_path / "no_existe" / "a.omnicad")})
    assert r["error_kind"] == "FILE_NOT_FOUND"


def test_exportar(s, tmp_path):
    r = ok(api.llamar(s, "export", {"path": str(tmp_path / "todo.stl")}))
    assert r["format"] == "stl" and r["bodies"] == ["op2.c1", "op6.c1"] and r["triangles"] > 0 and r["size_bytes"] > 84
    assert api.llamar(s, "export", {"path": str(tmp_path / "todo.stl")})["error_kind"] == "FILE_EXISTS"
    assert ok(api.llamar(s, "export", {"path": str(tmp_path / "todo.stl"), "overwrite": True}))
    r = ok(api.llamar(s, "export", {"path": str(tmp_path / "placa.step"), "bodies": ["cuerpo1"]}))
    assert r["bodies"] == ["op2.c1"] and (tmp_path / "placa.step").read_text()[:13] == "ISO-10303-21;"
    assert api.llamar(s, "export", {"path": str(tmp_path / "a.xyz")})["error_kind"] == "INVALID_FORMAT"
    assert api.llamar(s, "export", {"path": str(tmp_path / "a.stl"), "bodies": ["zz"]})["error_kind"] == "BODY_NOT_FOUND"
    vacia = api.Sesion()
    assert api.llamar(vacia, "export", {"path": str(tmp_path / "v.stl")})["error_kind"] == "NOTHING_TO_EXPORT"


def test_documento_nuevo_y_externo():
    doc = Documento()
    avisado = []
    doc.suscribir(lambda: avisado.append(1))
    s = api.Sesion(doc)
    assert s.doc is doc and s.ruta is None
    ok(api.llamar(s, "create_parameter", {"name": "a", "expression": "5 mm"}))
    assert avisado and "a" in doc.parametros                         # modifica el documento de afuera
    r = ok(api.llamar(s, "new_document", {"name": "Otra"}))
    assert r["name"] == "Otra" and s.doc is not doc
    info = ok(api.llamar(s, "get_scene_info"))
    assert info["bodies"] == [] and info["timeline_steps"] == 0 and info["parameters"] == []

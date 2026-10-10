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
    assert api.llamar(s, "save_document", {"path": str(tmp_path / "no_existe" / "x.omnicad"),
                                           "create_folders": False})["ok"] is False
    assert ok(api.llamar(s, "get_scene_info"))["name"] == "pieza"


def test_errores_de_archivo(s, tmp_path):
    assert api.llamar(s, "open_document", {"path": str(tmp_path / "no.omnicad")})["error_kind"] == "FILE_NOT_FOUND"
    basura = tmp_path / "roto.omnicad"
    basura.write_bytes(b"no es un zip")
    antes = s.doc
    assert api.llamar(s, "open_document", {"path": str(basura)})["error_kind"] == "INVALID_PROJECT"
    assert s.doc is antes
    r = api.llamar(s, "save_document", {"path": str(tmp_path / "no_existe" / "a.omnicad"), "create_folders": False})
    assert r["error_kind"] == "FILE_NOT_FOUND" and not (tmp_path / "no_existe").exists()


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
    r = ok(api.llamar(s, "new_document", {"name": "Otra", "discard": True}))
    assert r["name"] == "Otra" and s.doc is not doc
    info = ok(api.llamar(s, "get_scene_info"))
    assert info["bodies"] == [] and info["timeline_steps"] == 0 and info["parameters"] == []


# ---------------------------------------------------------------- hallazgos de las pruebas de uso
def _cache_brep(ruta, carpeta):
    """La forma de cache/cuerpos.brep del proyecto (None si no tiene caché)."""
    import zipfile
    from omnicad.nucleo import intercambio
    with zipfile.ZipFile(ruta) as z:
        if "cache/cuerpos.brep" not in z.namelist():
            return None
        z.extract("cache/cuerpos.brep", carpeta)
    return intercambio.leer_brep(carpeta / "cache" / "cuerpos.brep")


def test_guardar_y_reabrir_con_cuerpo_de_malla(tmp_path):
    """Antes save_document (y Guardar de la ventana) daban INTERNAL_ERROR «Add(): incompatible function arguments»:
    la caché B-rep metía la Malla en un compuesto OCC. Las mallas viajan solo en la receta."""
    from omnicad.nucleo import geometria as geo
    s = api.Sesion()
    ok(api.llamar(s, "create_box", {"length": 10, "width": 10, "height": 10}))
    ok(api.llamar(s, "run_operation", {"type": "teselar", "params": {"cuerpos": ["op1.c1"], "mantener": True}}))
    r = ok(api.llamar(s, "save_document", {"path": str(tmp_path / "con_malla.omnicad")}))
    cache = _cache_brep(r["path"], tmp_path)
    assert len(geo.solidos(cache)) == 1 and geo.es_valida(cache)
    assert geo.volumen(cache) == pytest.approx(1000, rel=1e-9)        # solo el sólido, sin la malla
    abierta = ok(api.llamar(api.Sesion(), "open_document", {"path": r["path"]}))
    assert [(b["type"], b["volume"]) for b in abierta["bodies"]] == [("solid", pytest.approx(1000)),
                                                                     ("mesh", pytest.approx(1000))]
    # solo malla: se guarda sin caché
    ok(api.llamar(s, "edit_feature", {"feature": "op2", "params": {"mantener": False}}))
    r = ok(api.llamar(s, "save_document", {"path": str(tmp_path / "solo_malla.omnicad")}))
    assert _cache_brep(r["path"], tmp_path / "b") is None
    abierta = ok(api.llamar(api.Sesion(), "open_document", {"path": r["path"]}))
    assert [(b["type"], b["volume"]) for b in abierta["bodies"]] == [("mesh", pytest.approx(1000))]


def test_abrir_brep_como_operacion_base(tmp_path):
    """El .brep que escribe export se abre como los demás formatos: documento nuevo con UN paso (operación base)."""
    from omnicad.nucleo import geometria as geo
    from omnicad.nucleo import intercambio
    s = api.Sesion()
    ok(api.llamar(s, "create_box", {"length": 10, "width": 20, "height": 30}))
    ok(api.llamar(s, "create_cylinder", {"radius": 3, "height": 5, "x": 50}))
    ok(api.llamar(s, "export", {"path": str(tmp_path / "dos.brep")}))
    otra = api.Sesion()
    info = ok(api.llamar(otra, "open_document", {"path": str(tmp_path / "dos.brep")}))
    assert info["name"] == "dos" and info["path"] is None and info["modified"] is False
    assert [(b["type"], b["volume"]) for b in info["bodies"]] == [("solid", pytest.approx(6000)),
                                                                  ("solid", pytest.approx(math.pi * 9 * 5))]
    assert all(geo.es_valida(c.forma) for c in otra.doc.estado_final.cuerpos.values())
    pasos = ok(api.llamar(otra, "get_timeline"))["steps"]
    assert [(p["type"], p["status"]) for p in pasos] == [("operacion_base", "ok")]
    # se guarda y se reabre igual (el B-rep queda en la receta)
    r = ok(api.llamar(otra, "save_document", {"path": str(tmp_path / "dos.omnicad")}))
    assert ok(api.llamar(api.Sesion(), "open_document", {"path": r["path"]}))["bodies"] == info["bodies"]
    # .brp con un sólido y una superficie sueltos
    mixto = geo.compuesto([geo.caja(1, 2, 3), geo.cara_de_plano(geo.Plano("XY"), tam=10)])
    intercambio.escribir_brep(mixto, tmp_path / "mixto.brp")
    info = ok(api.llamar(api.Sesion(), "open_document", {"path": str(tmp_path / "mixto.brp")}))
    assert [b["type"] for b in info["bodies"]] == ["solid", "surface"]
    assert info["bodies"][0]["volume"] == pytest.approx(6) and info["bodies"][1]["area"] == pytest.approx(400)  # 20×20
    roto = tmp_path / "roto.brep"
    roto.write_text("no es un BREP", encoding="utf-8")
    r = api.llamar(api.Sesion(), "open_document", {"path": str(roto)})
    assert r["error_kind"] == "IMPORT_FAILED" and "roto.brep" in r["mensaje"]


def test_guardar_con_ruta_vacia_o_sin_nombre(tmp_path):
    """Antes path="" daba INTERNAL_ERROR «WindowsPath('.') has an empty name». Vacío = el archivo actual."""
    s = api.Sesion()
    ok(api.llamar(s, "create_box", {"length": 10, "width": 10, "height": 10}))
    r = api.llamar(s, "save_document", {"path": ""})
    assert r["error_kind"] == "MISSING_PATH"
    assert api.llamar(s, "save_document", {"path": "  "})["error_kind"] == "MISSING_PATH"
    for sin_nombre in (".", "..", str(tmp_path) + "/.."):
        r = api.llamar(s, "save_document", {"path": sin_nombre})
        assert r["error_kind"] == "INVALID_ARGUMENTS" and "nombre de archivo" in r["mensaje"]
    guardado = ok(api.llamar(s, "save_document", {"path": str(tmp_path / "pieza.omnicad")}))
    ok(api.llamar(s, "create_sphere", {"radius": 2, "x": 30}))
    r = ok(api.llamar(s, "save_document", {"path": ""}))
    assert r["path"] == guardado["path"] and not s.doc.modificado


def test_new_y_open_document_con_cambios_sin_guardar_sin_ventana(tmp_path):
    """Misma regla que en vivo: con cambios sin guardar fallan con UNSAVED_CHANGES; discard=true los descarta."""
    s = api.Sesion()
    ok(api.llamar(s, "create_box", {"length": 10, "width": 10, "height": 10}))
    ruta = tmp_path / "otra.omnicad"
    api.Sesion().guardar(ruta)
    antes = foto(s)
    for tool, args in (("new_document", {"name": "Otro"}), ("open_document", {"path": str(ruta)})):
        r = api.llamar(s, tool, args)
        assert r["error_kind"] == "UNSAVED_CHANGES" and any("discard" in p for p in r["pistas"])
        assert foto(s) == antes                                          # no se descartó nada
    assert ok(api.llamar(s, "open_document", {"path": str(ruta), "discard": True}))["bodies"] == []
    ok(api.llamar(s, "create_box", {"length": 1, "width": 1, "height": 1}))
    assert ok(api.llamar(s, "new_document", {"name": "Nuevo", "discard": True}))["name"] == "Nuevo"
    assert ok(api.llamar(s, "new_document", {"name": "Sin cambios"}))["name"] == "Sin cambios"
    for nombre in ("new_document", "open_document"):
        h = next(h for h in api.catalogo() if h["nombre"] == nombre)
        assert "UNSAVED_CHANGES" in h["descripcion"] and "sin guardarlo" not in h["descripcion"]


def test_apply_recipe_acepta_el_resultado_de_get_recipe_tal_cual(s):
    """Antes pasar {"recipe": {...}} (lo que devuelve get_recipe) daba INVALID_RECIPE."""
    resultado = ok(api.llamar(s, "get_recipe"))
    otra = api.Sesion()
    r = ok(api.llamar(otra, "apply_recipe", {"recipe": resultado}))
    assert r["added_steps"] == 8 and ok(api.llamar(otra, "get_recipe")) == resultado
    otra = api.Sesion()
    assert ok(api.llamar(otra, "apply_recipe", {"recipe": resultado["recipe"]}))["added_steps"] == 8
    assert api.llamar(otra, "apply_recipe", {"recipe": {"recipe": {}}})["error_kind"] == "INVALID_RECIPE"


# ---------------------------------------------------------------- hallazgos de las pruebas de uso (ola 2)
def test_guardar_crea_las_carpetas_que_faltan(tmp_path, monkeypatch):
    """Antes save_document a una carpeta inexistente daba FILE_NOT_FOUND. Ahora la crea (y avisa); con
    create_folders=false sigue fallando, y si la escritura falla no deja carpetas vacías."""
    from omnicad.io_archivos import proyecto
    s = api.Sesion()
    ok(api.llamar(s, "create_box", {"length": 10, "width": 20, "height": 30}))
    r = api.llamar(s, "save_document", {"path": str(tmp_path / "a" / "b" / "pieza.omnicad")})
    assert r["ok"] and (tmp_path / "a" / "b" / "pieza.omnicad").is_file()
    assert any("Se creó la carpeta" in a and "b" in a for a in r["avisos"])
    info = ok(api.llamar(api.Sesion(), "open_document", {"path": r["result"]["path"]}))
    assert info["bodies"][0]["volume"] == pytest.approx(6000)
    # sin crear carpetas: FILE_NOT_FOUND y no se crea nada
    r = api.llamar(s, "save_document", {"path": str(tmp_path / "c" / "x.omnicad"), "create_folders": False})
    assert r["error_kind"] == "FILE_NOT_FOUND" and any("create_folders" in p for p in r["pistas"])
    assert not (tmp_path / "c").exists()
    # un archivo en el camino: FILE_ERROR, sin carpetas a medias
    (tmp_path / "archivo.txt").write_text("x", encoding="utf-8")
    r = api.llamar(s, "save_document", {"path": str(tmp_path / "archivo.txt" / "d" / "x.omnicad")})
    assert r["error_kind"] == "FILE_ERROR" and "archivo.txt" in r["mensaje"]
    # si la escritura falla después de crear las carpetas, se borran

    def falla(*args, **kwargs):
        raise OSError("disco lleno")
    monkeypatch.setattr(proyecto, "guardar", falla)
    r = api.llamar(s, "save_document", {"path": str(tmp_path / "e" / "f" / "x.omnicad")})
    assert r["error_kind"] == "FILE_ERROR" and not (tmp_path / "e").exists()


def test_exportar_crea_las_carpetas_que_faltan(s, tmp_path):
    r = api.llamar(s, "export", {"path": str(tmp_path / "salida" / "stl" / "todo.stl")})
    assert r["ok"] and r["result"]["triangles"] > 0 and (tmp_path / "salida" / "stl" / "todo.stl").stat().st_size > 84
    assert any("Se creó la carpeta" in a for a in r["avisos"])
    r = api.llamar(s, "export", {"path": str(tmp_path / "z" / "a.xyz")})
    assert r["error_kind"] == "INVALID_FORMAT" and not (tmp_path / "z").exists()        # formato malo: ni la carpeta
    r = api.llamar(api.Sesion(), "export", {"path": str(tmp_path / "w" / "v.stl")})
    assert r["error_kind"] == "NOTHING_TO_EXPORT" and not (tmp_path / "w").exists()     # falló: se borró la carpeta
    r = api.llamar(s, "export", {"path": str(tmp_path / "y" / "a.stl"), "create_folders": False})
    assert r["error_kind"] == "FILE_NOT_FOUND" and not (tmp_path / "y").exists()


def test_escena_lista_componentes_y_uniones():
    """Antes get_scene_info no decía nada de componentes ni uniones (solo cuerpos)."""
    s = api.Sesion()
    ok(api.llamar(s, "create_box", {"length": 40, "width": 40, "height": 10}))
    ok(api.llamar(s, "create_box", {"length": 10, "width": 10, "height": 10, "x": 50}))
    ok(api.llamar(s, "rename", {"target": "Cuerpo1", "new_name": "Base"}))
    ok(api.llamar(s, "rename", {"target": "Cuerpo2", "new_name": "Bloque"}))
    vacia = ok(api.llamar(s, "get_scene_info"))
    assert vacia["components"] == [] and vacia["joints"] == [] and vacia["rigid_groups"] == []
    c1 = ok(api.llamar(s, "run_operation", {"type": "componente", "params": {"cuerpos": ["Bloque"]}, "name": "Pieza"}))
    c2 = ok(api.llamar(s, "run_operation", {"type": "componente", "params": {"cuerpos": ["Base"], "fijo": True},
                                            "name": "Soporte"}))
    abajo = ok(api.llamar(s, "find_faces", {"selector": "<Z", "body": "Bloque"}))["faces"][0]["id"]
    arriba = ok(api.llamar(s, "find_faces", {"selector": ">Z", "body": "Base"}))["faces"][0]["id"]
    u = ok(api.llamar(s, "run_operation", {"type": "union", "params": {"origen1": abajo, "origen2": arriba},
                                           "name": "Apoyo"}))
    info = ok(api.llamar(s, "get_scene_info"))
    assert [(c["id"], c["name"], c["grounded"], c["bodies"]) for c in info["components"]] == [
        (c1["id"], "Pieza", False, ["op2.c1"]), (c2["id"], "Soporte", True, ["op1.c1"])]
    pieza = info["components"][0]
    assert [fila[3] for fila in pieza["transform"][:3]] == pytest.approx([-50, 0, 10])   # se movió 50 en X y subió 10
    assert info["joints"] == [{"id": u["id"], "name": "Apoyo", "type": "rigid", "component1": c1["id"],
                               "component2": c2["id"], "moves": [c1["id"]],
                               "values": {"rotation": 0.0, "rotation2": 0.0, "rotation3": 0.0, "slide": 0.0,
                                          "slide2": 0.0}}]
    bloque = next(b for b in info["bodies"] if b["name"] == "Bloque")
    assert bloque["bounding_box"]["min"] == pytest.approx([-5, -5, 10]) and bloque["bounding_box"]["max"][2] == 20


def test_get_timeline_dice_que_campo_es_que():
    """NOMBRES CRUZADOS: la caja guarda ancho = X (length) y largo = Y (width); get_timeline lo dice en aliases."""
    s = api.Sesion()
    ok(api.llamar(s, "create_box", {"length": 50, "width": 10, "height": 5}))
    ok(api.llamar(s, "create_cylinder", {"radius": 3, "height": 7, "x": 100}))
    ok(api.llamar(s, "move_body", {"body": "Cuerpo1", "translate": [0, 0, 1]}))
    pasos = ok(api.llamar(s, "get_timeline"))["steps"]
    assert pasos[0]["aliases"] == {"length": "ancho", "width": "largo", "height": "alto"}
    assert pasos[0]["values"]["ancho"] == 50 and pasos[0]["values"]["largo"] == 10
    assert pasos[1]["aliases"] == {"height": "alto", "radius": "radio"}
    assert pasos[2]["aliases"] == {"pivot": "pivote"}
    assert "aliases" not in ok(api.llamar(s, "get_timeline", {"include_params": False}))["steps"][0]


def test_edit_feature_acepta_formas_cortas_de_referencias():
    s = api.Sesion()
    ok(api.llamar(s, "create_box", {"length": 10, "width": 10, "height": 10, "x": 20}))
    ok(api.llamar(s, "create_sphere", {"radius": 1, "x": 100}))
    paso = ok(api.llamar(s, "move_body", {"body": "Cuerpo1", "rotate": [0, 0, 90]}))["feature"]["id"]
    r = ok(api.llamar(s, "edit_feature", {"feature": paso, "params": {"pivote": "O"}}))
    assert r["params"]["pivote"] == {"tipo": "punto", "id": "O"}
    bb = ok(api.llamar(s, "get_scene_info"))["bodies"][0]["bounding_box"]
    assert bb["min"][:2] == pytest.approx([-5, 15]) and bb["max"][:2] == pytest.approx([5, 25])   # giró sobre el origen
    antes = foto(s)
    r = api.llamar(s, "edit_feature", {"feature": paso, "params": {"pivote": "Cuerpo1/F1"}})
    assert r["error_kind"] == "INVALID_ARGUMENTS" and "delete_feature" in r["pistas"][0]
    r = api.llamar(s, "edit_feature", {"feature": paso, "params": {"pivote": "qwerty"}})
    assert r["error_kind"] == "INVALID_ARGUMENTS" and "pivote" in r["mensaje"]
    assert foto(s) == antes
    ok(api.llamar(s, "edit_feature", {"feature": paso, "params": {"cuerpos": ["Cuerpo2"]}}))   # nombre → id
    assert s.paso(paso).p["cuerpos"] == ["op2.c1"]
    esfera = next(b for b in ok(api.llamar(s, "get_scene_info"))["bodies"] if b["id"] == "op2.c1")
    assert esfera["bounding_box"]["min"][:2] == pytest.approx([-1, 99])                    # (100, 0) girado 90°

# -*- coding: utf-8 -*-
"""insert_file (Insertar de Fusion en el documento actual) y los formatos de operacion_base / relleno_contorno
por run_operation."""
import pytest

from omnicad import api
from omnicad.nucleo import geometria as geo


def ok(r):
    assert r["ok"], r
    return r["result"]


def falla(r, kind):
    assert not r["ok"] and r["error_kind"] == kind, r
    return r


@pytest.fixture(scope="module")
def archivos(tmp_path_factory):
    """Una caja de 10³ exportada a STEP, IGES y STL, y guardada como .omnicad."""
    carpeta = tmp_path_factory.mktemp("insertar")
    s = api.Sesion()
    ok(api.llamar(s, "create_box", {"length": 10, "width": 10, "height": 10}))
    rutas = {}
    for ext in ("step", "igs", "stl"):
        rutas[ext] = carpeta / f"caja.{ext}"
        ok(api.llamar(s, "export", {"path": str(rutas[ext])}))
    rutas["omnicad"] = carpeta / "caja.omnicad"
    ok(api.llamar(s, "save_document", {"path": str(rutas["omnicad"])}))
    return rutas


@pytest.fixture
def s():
    sesion = api.Sesion()
    ok(api.llamar(sesion, "create_box", {"length": 4, "width": 4, "height": 4, "x": 50}))
    return sesion


def _caja(sesion, cid):
    p0, p1 = geo.caja_envolvente(sesion.doc.estado_final.cuerpos[cid].forma) \
        if sesion.doc.estado_final.cuerpos[cid].tipo != "malla" else sesion.doc.estado_final.cuerpos[cid].forma.caja()
    return [round(b - a, 3) for a, b in zip(p0, p1, strict=True)]


@pytest.mark.parametrize("ext", ["step", "igs"])
def test_insert_file_exacto_en_el_documento_actual(s, archivos, ext):
    r = ok(api.llamar(s, "insert_file", {"path": str(archivos[ext])}))
    assert r["status"] == "ok" and len(s.doc.operaciones) == 2 and "op1.c1" in r["bodies"]
    assert len(r["new_bodies"]) == 1
    forma = s.doc.estado_final.cuerpos[r["new_bodies"][0]].forma
    assert geo.es_valida(forma) and geo.volumen(forma) == pytest.approx(1000, rel=1e-6)
    assert _caja(s, r["new_bodies"][0]) == [10, 10, 10]
    ok(api.llamar(s, "undo"))
    assert len(s.doc.operaciones) == 1 and list(s.doc.estado_final.cuerpos) == ["op1.c1"]


def test_insert_file_malla_con_unidades_y_nombre(s, archivos):
    r = ok(api.llamar(s, "insert_file", {"path": str(archivos["stl"]), "mesh_units": "cm", "name": "Malla"}))
    assert r["type"] == "insertar_malla" and r["name"] == "Malla" and r["status"] == "ok"
    assert _caja(s, r["new_bodies"][0]) == [100, 100, 100]


def test_insert_file_diseno_omnicad(s, archivos):
    r = ok(api.llamar(s, "insert_file", {"path": str(archivos["omnicad"])}))
    assert r["type"] == "insertar_diseno" and r["status"] == "ok" and len(r["new_bodies"]) == 1
    assert r["id"] in s.doc.estado_final.componentes
    assert geo.volumen(s.doc.estado_final.cuerpos[r["new_bodies"][0]].forma) == pytest.approx(1000, rel=1e-6)


def test_insert_file_errores(s, archivos, tmp_path):
    falla(api.llamar(s, "insert_file", {"path": str(tmp_path / "no.step")}), "FILE_NOT_FOUND")
    r = falla(api.llamar(s, "insert_file", {"path": str(tmp_path / "x.dxf")}), "UNSUPPORTED_FILE_TYPE")
    assert any("open_document" in p for p in r["pistas"])
    malo = tmp_path / "malo.step"
    malo.write_text("hola", encoding="utf-8")
    assert not api.llamar(s, "insert_file", {"path": str(malo)})["ok"]
    assert len(s.doc.operaciones) == 1


@pytest.mark.parametrize("tipo,params", [("importar_step", {"archivo": "x.step"}), ("importar_iges", {"archivo": "x.igs"}),
                                         ("insertar_malla", {"archivo": "x"}), ("insertar_diseno", {"archivo": "x"})])
def test_run_operation_sin_contenido_sugiere_insert_file(s, tipo, params):
    r = falla(api.llamar(s, "run_operation", {"type": tipo, "params": params}), "INVALID_ARGUMENTS")
    assert any("insert_file" in p for p in r["pistas"])


def test_operacion_base_con_ids_congela(s):
    r = ok(api.llamar(s, "run_operation", {"type": "operacion_base", "params": {"cuerpos": ["op1.c1"]}}))
    assert r["status"] == "ok"
    ok(api.llamar(s, "edit_feature", {"feature": "op1", "params": {"length": 8}}))
    assert geo.volumen(s.doc.estado_final.cuerpos["op1.c1"].forma) == pytest.approx(64, rel=1e-6)
    r = api.llamar(s, "run_operation", {"type": "operacion_base", "params": {"cuerpos": [{"id": "op1.c1"}]}})
    assert not r["ok"] and "string indices" not in r["mensaje"]
    falla(api.llamar(s, "run_operation", {"type": "operacion_base", "params": {"cuerpos": ["zzz"]}}), "BODY_NOT_FOUND")


def test_relleno_contorno_formato(s):
    r = api.llamar(s, "run_operation", {"type": "relleno_contorno", "params": {"herramientas": ["op1.c1"]}})
    assert not r["ok"] and "string indices" not in r["mensaje"]
    r = ok(api.llamar(s, "run_operation", {"type": "relleno_contorno",
                                           "params": {"herramientas": [{"tipo": "cuerpo", "cuerpo": "op1.c1"}]}}))
    assert r["status"] == "ok"
    assert geo.volumen(s.doc.estado_final.cuerpos[r["new_bodies"][0]].forma) == pytest.approx(64, rel=1e-6)


def test_describe_operation_documenta_formatos(s):
    doc = ok(api.llamar(s, "describe_operation", {"type": "operacion_base"}))["doc"]
    assert "brep" in doc and "run_operation" in doc
    doc = ok(api.llamar(s, "describe_operation", {"type": "relleno_contorno"}))["doc"]
    assert '"tipo": "cuerpo"' in doc and "celdas" in doc

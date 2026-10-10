# -*- coding: utf-8 -*-
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Literal

import numpy as np
import pytest

from omnicad import api

from omnicad.api import registro as cat

ESPERADAS = {"documento": {"get_scene_info", "new_document", "open_document", "save_document", "export", "undo",
                           "redo", "get_timeline", "edit_feature", "suppress_feature", "delete_feature", "rename",
                           "insert_file"},
             "parametros": {"get_parameters", "create_parameter", "set_parameter", "delete_parameter"}}


@pytest.fixture
def temporales():
    """Registra herramientas de prueba y las saca del catálogo al terminar."""
    nombres = []

    def registrar(nombre, **kw):
        nombres.append(nombre)
        return api.herramienta(nombre, "prueba", "Herramienta de prueba.", **kw)
    yield registrar
    for n in nombres:
        cat._CATALOGO.pop(n, None)


def test_herramientas_registradas_por_grupo():
    for grupo, nombres in ESPERADAS.items():
        assert {h["nombre"] for h in api.catalogo(grupo)} == nombres
    assert len(api.catalogo(["documento", "parametros"])) == 17


def test_esquemas_validos_y_documentados():
    jsonschema = pytest.importorskip("jsonschema")
    for h in api.catalogo():
        assert re.fullmatch(r"[a-z][a-z0-9_]*", h["nombre"])
        assert h["descripcion"] and isinstance(h["modifica"], bool)
        esquema = h["esquema"]
        jsonschema.Draft202012Validator.check_schema(esquema)
        json.dumps(esquema)
        assert esquema["type"] == "object" and esquema["additionalProperties"] is False
        assert set(esquema["required"]) <= set(esquema["properties"])
        for nombre, prop in esquema["properties"].items():
            assert re.fullmatch(r"[a-z][a-z0-9_]*", nombre), nombre
            assert prop.get("description"), f"{h['nombre']}.{nombre} sin descripción en el docstring"
            if "default" in prop:
                jsonschema.validate(prop["default"], {k: v for k, v in prop.items() if k != "default"})


def test_generador_de_esquema(temporales):
    @temporales("_prueba_tipos")
    def f(sesion, a: str, b: int, c: float = 1.5, d: bool = False, e: list[int] | None = None,
          g: dict | None = None, h: Literal["x", "y"] = "x", i: api.Expr = "10 mm", j: dict[str, float] | None = None):
        """
        Texto libre que no es un parámetro.

        a: primera línea
            y su continuación.
        b: entero.
        """
    props = cat._CATALOGO["_prueba_tipos"].esquema["properties"]
    assert props["a"] == {"type": "string", "description": "primera línea y su continuación."}
    assert props["b"]["type"] == "integer" and props["c"] == {"type": "number", "default": 1.5}
    assert props["d"]["type"] == "boolean"
    assert props["e"]["anyOf"] == [{"type": "array", "items": {"type": "integer"}}, {"type": "null"}]
    assert props["g"]["type"] == ["object", "null"]
    assert props["h"] == {"type": "string", "enum": ["x", "y"], "default": "x"}
    assert props["i"]["type"] == ["number", "string"]
    assert props["j"]["anyOf"][0] == {"type": "object", "additionalProperties": {"type": "number"}}
    assert cat._CATALOGO["_prueba_tipos"].esquema["required"] == ["a", "b"]


def test_herramienta_repetida_falla(temporales):
    temporales("_prueba_rep")(lambda sesion: None)
    with pytest.raises(ValueError):
        api.herramienta("_prueba_rep", "prueba", "otra")(lambda sesion: None)


@pytest.mark.parametrize("nombre, args, kind", [
    ("no_existe", {}, "UNKNOWN_TOOL"),
    ("get_sceneinfo", {}, "UNKNOWN_TOOL"),
    (None, {}, "UNKNOWN_TOOL"),
    ("undo", {"x": 1}, "INVALID_ARGUMENTS"),
    ("undo", [1, 2], "INVALID_ARGUMENTS"),
    ("create_parameter", {"name": "a"}, "INVALID_ARGUMENTS"),
    ("create_parameter", {"name": 3, "expression": "1"}, "INVALID_ARGUMENTS"),
    ("create_parameter", {"name": "a", "expression": True}, "INVALID_ARGUMENTS"),
    ("create_parameter", {"name": "a", "expression": [1]}, "INVALID_ARGUMENTS"),
    ("suppress_feature", {"feature": "op1", "suppressed": "si"}, "INVALID_ARGUMENTS"),
    ("rename", {"target": "x", "new_name": "y", "kind": "otro"}, "INVALID_ARGUMENTS"),
    ("export", {"path": "a.stl", "bodies": "op1.c1"}, "INVALID_ARGUMENTS"),
    ("edit_feature", {"feature": "op1", "params": []}, "INVALID_ARGUMENTS"),
])
def test_llamar_con_argumentos_malos(nombre, args, kind):
    r = api.llamar(api.Sesion(), nombre, args)
    assert r["ok"] is False and r["error_kind"] == kind
    assert r["mensaje"] and 1 <= len(r["pistas"]) <= 3


def test_pista_lista_argumentos_validos():
    r = api.llamar(api.Sesion(), "create_parameter", {"name": "a", "expresion": "1"})
    assert r["error_kind"] == "INVALID_ARGUMENTS"
    assert any("name, expression, comment" in p for p in r["pistas"])
    r = api.llamar(api.Sesion(), "get_sceneinfo", {})
    assert any("get_scene_info" in p for p in r["pistas"])


def test_llamar_nunca_lanza_con_basura(monkeypatch):
    # Las herramientas "dev" lanzan subprocesos: run_checks correría la suite entera (que vuelve a llegar acá: cadena
    # infinita de pytest que colgó la PC el 2026-10-09) y app_screenshot abriría la ventana real. Se simulan.
    from omnicad.api import herramientas_dev
    monkeypatch.setattr(herramientas_dev, "_correr", lambda argv, timeout: (1, "subproceso simulado en el test"))
    s = api.Sesion()
    basura = [{}, {"x": object()}, None, "texto", {"feature": object(), "name": None, "path": 3, "target": ""}]
    for h in api.catalogo():
        for args in basura:
            r = api.llamar(s, h["nombre"], args)
            assert isinstance(r, dict) and isinstance(r["ok"], bool)
            json.dumps(r)
            if not r["ok"]:
                assert set(r) == {"ok", "error_kind", "mensaje", "pistas"} and r["error_kind"].isupper()


def test_excepcion_interna_y_resultado_normalizado(temporales):
    temporales("_prueba_falla")(lambda sesion: 1 / 0)

    @temporales("_prueba_numpy")
    def numpy(sesion):
        sesion.avisar("cuidado")
        return {"v": np.float64(1.5), "a": np.arange(3), "t": (1, 2), "p": Path("x"), "img": api.Imagen(b"png", 2, 1)}

    s = api.Sesion()
    r = api.llamar(s, "_prueba_falla", {})
    assert r["ok"] is False and r["error_kind"] == "INTERNAL_ERROR" and "ZeroDivisionError" in r["mensaje"]
    r = api.llamar(s, "_prueba_numpy", {})
    assert r["ok"] and r["avisos"] == ["cuidado"]
    assert r["result"]["v"] == 1.5 and r["result"]["a"] == [0, 1, 2] and r["result"]["t"] == [1, 2]
    assert r["result"]["p"] == "x" and r["result"]["img"] == api.Imagen(b"png", 2, 1)
    assert api.llamar(s, "get_parameters", {})["avisos"] == []     # los avisos no pasan a la llamada siguiente


def test_entero_acepta_float_entero(temporales):
    temporales("_prueba_int")(lambda sesion, n: n * 2)
    cat._CATALOGO["_prueba_int"].tipos["n"] = int
    assert api.llamar(api.Sesion(), "_prueba_int", {"n": 2.0})["result"] == 4
    assert api.llamar(api.Sesion(), "_prueba_int", {"n": 2.5})["error_kind"] == "INVALID_ARGUMENTS"


def test_importar_api_no_carga_qt():
    raiz = Path(__file__).resolve().parent.parent
    codigo = "import sys; import omnicad.api; assert 'PySide6' not in sys.modules, 'carga PySide6'; assert 'mcp' not in sys.modules; print('ok')"
    r = subprocess.run([sys.executable, "-c", codigo], cwd=raiz, capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "ok"

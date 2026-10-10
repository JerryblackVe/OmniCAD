# -*- coding: utf-8 -*-
import json
import re

import pytest

from omnicad import api
from omnicad.api import herramientas_avanzado as av
from omnicad.ejemplo import crear_documento_ejemplo
from omnicad.timeline.operaciones import TIPOS_OPERACION


@pytest.fixture
def s():
    return api.Sesion(crear_documento_ejemplo())


def ok(r):
    assert r["ok"], r
    return r["result"]


def foto(sesion):
    doc = sesion.doc
    return (json.dumps(doc.a_dict(), sort_keys=True), [(r.estado, r.mensaje) for r in doc.resultados],
            len(doc._deshacer), len(doc._rehacer), doc.modificado)


# ---------------------------------------------------------------- tipos de operación
def test_list_operation_types_trae_los_85(s):
    r = ok(api.llamar(s, "list_operation_types"))
    assert r["count"] == len(r["types"]) == len(TIPOS_OPERACION) >= 85
    assert {t["type"] for t in r["types"]} == set(TIPOS_OPERACION)
    assert all(t["label"] and t["summary"] for t in r["types"])


@pytest.mark.parametrize("tipo", sorted(TIPOS_OPERACION))
def test_describe_operation_de_cada_tipo(s, tipo):
    d = ok(api.llamar(s, "describe_operation", {"type": tipo}))
    clase = TIPOS_OPERACION[tipo]
    assert d["type"] == tipo and d["label"] == clase.ETIQUETA and d["summary"]
    assert [p["name"] for p in d["params"]] == list(clase.PARAMS)
    assert all(p["default"] == clase.PARAMS[p["name"]] and p["type"] for p in d["params"])
    assert set(clase.EXPRESIONES) <= set(d["expressions"])
    assert all(p["accepts_expression"] == (p["name"] in d["expressions"]) for p in d["params"])
    assert d["example"]["tool"] == "run_operation" and d["example"]["args"]["type"] == tipo
    assert set(d["example"]["args"]["params"]) <= set(clase.PARAMS)
    json.dumps(d)


def test_describe_operation_detalle(s):
    d = ok(api.llamar(s, "describe_operation", {"type": "extrusion"}))
    por = {p["name"]: p for p in d["params"]}
    assert por["distancia"]["type"] == "expression" and por["distancia"]["accepts_expression"] is True
    assert por["invertir"]["type"] == "boolean" and por["perfiles"]["type"] == "array"
    assert por["tipo"]["type"] == "string" and por["tipo"]["accepts_expression"] is False
    assert "SLD-EXTRUDE-SOLID" in d["doc"]
    prim = {p["name"]: p for p in ok(api.llamar(s, "describe_operation", {"type": "primitiva"}))["params"]}
    assert prim["ancho"]["accepts_expression"] and prim["z"]["accepts_expression"]      # vienen de expresiones()


def test_tipo_desconocido(s):
    for nombre, args in (("describe_operation", {"type": "extrusionn"}), ("run_operation", {"type": "extrusionn"})):
        r = api.llamar(s, nombre, args)
        assert not r["ok"] and r["error_kind"] == "UNKNOWN_OPERATION_TYPE" and any("extrusion" in p for p in r["pistas"])


# ---------------------------------------------------------------- run_operation
def test_run_operation_crea_una_primitiva_y_deshacer_la_quita(s):
    antes = ok(api.llamar(s, "get_scene_info"))
    r = ok(api.llamar(s, "run_operation", {"type": "primitiva", "params": {"forma": "esfera", "radio": "5 mm",
                                                                            "x": "100 mm"}, "name": "Bola"}))
    assert r["type"] == "primitiva" and r["name"] == "Bola" and r["status"] == "ok" and len(r["new_bodies"]) == 1
    info = ok(api.llamar(s, "get_scene_info"))
    assert info["timeline_steps"] == antes["timeline_steps"] + 1 and len(info["bodies"]) == len(antes["bodies"]) + 1
    bola = next(b for b in info["bodies"] if b["id"] == r["new_bodies"][0])
    assert bola["volume"] == pytest.approx(4 / 3 * 3.141592653589793 * 125, rel=1e-3)
    ok(api.llamar(s, "undo"))                      # un solo paso de deshacer (undo marca el documento como modificado)
    assert dict(ok(api.llamar(s, "get_scene_info")), modified=False) == antes


def test_run_operation_con_el_ejemplo_de_describe(s):
    ejemplo = ok(api.llamar(s, "describe_operation", {"type": "primitiva"}))["example"]
    r = ok(api.llamar(s, ejemplo["tool"], ejemplo["args"]))
    assert r["status"] == "ok" and r["new_bodies"]


def test_run_operation_acepta_expresiones_con_parametros(s):
    r = ok(api.llamar(s, "run_operation", {"type": "primitiva", "params": {"alto": "ancho / 2"}}))
    assert r["status"] == "ok"
    caja = next(b for b in ok(api.llamar(s, "get_scene_info"))["bodies"] if b["id"] == r["new_bodies"][0])
    assert caja["bounding_box"]["size"][2] == pytest.approx(30.0, abs=1e-3)


def test_run_operation_claves_invalidas(s):
    antes = foto(s)
    r = api.llamar(s, "run_operation", {"type": "primitiva", "params": {"ancho": "5 mm", "color": "rojo", "z0": 1}})
    assert not r["ok"] and r["error_kind"] == "INVALID_ARGUMENTS"
    assert "color" in r["mensaje"] and "z0" in r["mensaje"] and any("ancho" in p and "operacion" in p for p in r["pistas"])
    assert foto(s) == antes


def test_run_operation_que_falla_deja_el_documento_igual(s):
    antes = foto(s)
    r = api.llamar(s, "run_operation", {"type": "primitiva", "params": {"ancho": "sin_parametro"}})
    assert not r["ok"] and r["error_kind"] == "INVALID_EXPRESSION" and "quedó con error" in r["mensaje"]
    assert foto(s) == antes
    r = api.llamar(s, "run_operation", {"type": "extrusion", "params": {"boceto": "no_existe"}})
    assert not r["ok"] and foto(s) == antes


# ---------------------------------------------------------------- receta
def test_receta_ida_y_vuelta(s):
    receta = ok(api.llamar(s, "get_recipe"))["recipe"]
    assert receta["version_receta"] >= 1 and len(receta["operaciones"]) == 8
    otra = api.Sesion()
    r = ok(api.llamar(otra, "apply_recipe", {"recipe": receta}))
    assert r["mode"] == "replace" and r["timeline_steps"] == 8 and len(r["bodies"]) == 2
    assert ok(api.llamar(otra, "get_recipe"))["recipe"] == receta
    a, b = ok(api.llamar(s, "get_scene_info")), ok(api.llamar(otra, "get_scene_info"))
    assert [(x["id"], x["volume"]) for x in a["bodies"]] == [(x["id"], x["volume"]) for x in b["bodies"]]
    ok(api.llamar(otra, "undo"))                   # apply_recipe es un paso de deshacer
    assert ok(api.llamar(otra, "get_scene_info"))["timeline_steps"] == 0


def test_apply_recipe_reemplaza_y_se_deshace(s):
    receta = ok(api.llamar(s, "get_recipe"))["recipe"]
    ok(api.llamar(s, "run_operation", {"type": "primitiva", "params": {}}))
    assert ok(api.llamar(s, "get_scene_info"))["timeline_steps"] == 9
    ok(api.llamar(s, "apply_recipe", {"recipe": receta}))
    assert ok(api.llamar(s, "get_scene_info"))["timeline_steps"] == 8
    ok(api.llamar(s, "undo"))
    assert ok(api.llamar(s, "get_scene_info"))["timeline_steps"] == 9


def test_apply_recipe_append_renumera_ids_y_conserva_referencias(s):
    receta = ok(api.llamar(s, "get_recipe"))["recipe"]
    r = ok(api.llamar(s, "apply_recipe", {"recipe": receta, "mode": "append"}))
    assert r["mode"] == "append" and r["timeline_steps"] == 16
    assert len(r["bodies"]) >= 3                   # el Pilar copiado se une al cuerpo original que toca (objetivo automático)
    pasos = ok(api.llamar(s, "get_timeline"))["steps"]
    ids = [p["id"] for p in pasos]
    assert len(set(ids)) == 16 and all(p["status"] == "ok" for p in pasos)
    copia = pasos[9]                               # la extrusión copiada apunta a SU boceto copiado
    assert copia["type"] == "extrusion" and copia["params"]["boceto"] == ids[8]
    ok(api.llamar(s, "undo"))
    assert ok(api.llamar(s, "get_scene_info"))["timeline_steps"] == 8


def test_apply_recipe_append_con_parametro_en_conflicto(s):
    receta = ok(api.llamar(s, "get_recipe"))["recipe"]
    receta["parametros"][0]["expresion"] = "999 mm"
    antes = foto(s)
    r = api.llamar(s, "apply_recipe", {"recipe": receta, "mode": "append"})
    assert not r["ok"] and r["error_kind"] == "PARAMETER_EXISTS" and foto(s) == antes


@pytest.mark.parametrize("receta", [{}, {"operaciones": "x"}, {"operaciones": [{"id": "op1"}]},
                                    {"operaciones": [{"tipo": "no_existe", "id": "op1"}]},
                                    {"operaciones": [], "version_receta": 999}])
def test_apply_recipe_invalida_no_toca_nada(s, receta):
    antes = foto(s)
    r = api.llamar(s, "apply_recipe", {"recipe": receta})
    assert not r["ok"] and r["error_kind"] in ("INVALID_RECIPE", "UNKNOWN_OPERATION_TYPE") and foto(s) == antes


def test_apply_recipe_con_paso_roto_se_revierte(s):
    receta = ok(api.llamar(s, "get_recipe"))["recipe"]
    receta["operaciones"][1]["params"]["distancia"] = "sin_parametro"
    antes = foto(s)
    r = api.llamar(s, "apply_recipe", {"recipe": receta})
    assert not r["ok"] and foto(s) == antes
    r = api.llamar(s, "apply_recipe", {"recipe": {"operaciones": [{"tipo": "extrusion", "id": "x", "params": 5}]}})
    assert not r["ok"] and r["error_kind"] == "INVALID_RECIPE" and foto(s) == antes


# ---------------------------------------------------------------- execute_code
def test_execute_code_usa_llamar_stdout_y_result(s):
    pasos_antes = len(s.doc._deshacer)
    codigo = ("info = llamar('get_scene_info')\n"
              "print('cuerpos:', len(info['result']['bodies']))\n"
              "llamar('run_operation', {'type': 'primitiva', 'params': {}})\n"
              "result = {'n': len(doc.estado_final.cuerpos), 'api': api.__name__, 'sesion': sesion is not None}\n")
    r = ok(api.llamar(s, "execute_code", {"code": codigo}))
    assert r["stdout"] == "cuerpos: 2\n" and r["stdout_truncated"] is False
    assert r["result"] == {"n": 3, "api": "omnicad.api", "sesion": True}
    ok(api.llamar(s, "undo"))                      # todo el código es un solo paso de deshacer
    assert len(s.doc.estado_final.cuerpos) == 2 and len(s.doc._deshacer) == pasos_antes


def test_execute_code_sin_result_y_con_valor_no_json(s):
    r = ok(api.llamar(s, "execute_code", {"code": "print('hola')"}))
    assert r == {"stdout": "hola\n", "stdout_truncated": False}
    r = api.llamar(s, "execute_code", {"code": "result = doc.estado_final"})
    assert r["ok"] and isinstance(r["result"]["result"], str) and r["avisos"]
    r = ok(api.llamar(s, "execute_code", {"code": "result = (1, 2)\nprint('x' * 30000)"}))
    assert r["result"] == [1, 2] and len(r["stdout"]) == 20000 and r["stdout_truncated"] is True


def test_execute_code_que_lanza_deja_el_documento_igual(s):
    antes = foto(s)
    codigo = ("llamar('run_operation', {'type': 'primitiva', 'params': {}})\n"
              "print('antes del error')\n"
              "x = 1 / 0\n")
    r = api.llamar(s, "execute_code", {"code": codigo})
    assert not r["ok"] and r["error_kind"] == "CODE_ERROR"
    assert "línea 3" in r["mensaje"] and "x = 1 / 0" in r["mensaje"] and "ZeroDivisionError" in r["mensaje"]
    assert "antes del error" in r["mensaje"] and "Traceback" not in r["mensaje"]
    assert foto(s) == antes
    assert api.llamar(s, "get_scene_info")["ok"]


def test_execute_code_cambios_directos_al_documento_tambien_se_revierten(s):
    antes = foto(s)
    r = api.llamar(s, "execute_code", {"code": "doc.eliminar(doc.operaciones[-1].id)\nraise RuntimeError('boom')"})
    assert not r["ok"] and r["error_kind"] == "CODE_ERROR" and "boom" in r["mensaje"] and foto(s) == antes


def test_execute_code_errores_de_sintaxis_y_exit(s):
    r = api.llamar(s, "execute_code", {"code": "def f(:\n    pass"})
    assert not r["ok"] and r["error_kind"] == "CODE_ERROR" and "SyntaxError" in r["mensaje"] and "línea 1" in r["mensaje"]
    r = api.llamar(s, "execute_code", {"code": "import sys\nsys.exit(3)"})
    assert not r["ok"] and r["error_kind"] == "CODE_ERROR"
    r = api.llamar(s, "execute_code", {"code": "result = llamar('no_existe')['error_kind']"})
    assert ok(r)["result"] == "UNKNOWN_TOOL"       # llamar no lanza: devuelve el dict de error


def test_execute_code_falla_dentro_de_la_api_y_traza_larga(s):
    r = api.llamar(s, "execute_code", {"code": "doc.operacion('no_existe')"})
    assert not r["ok"] and "documento.py" in r["mensaje"] and "No existe la operación" in r["mensaje"]
    assert len(api.llamar(s, "execute_code", {"code": "raise ValueError('x' * 5000)"})["mensaje"]) <= 1500


# ---------------------------------------------------------------- execute_code con plazo (L139)
def test_execute_code_bucle_infinito_se_corta_por_timeout(s):
    import time
    antes = foto(s)
    t0 = time.monotonic()
    r = api.llamar(s, "execute_code", {"code": "print('arranca')\nwhile True:\n    pass", "timeout": 0.3})
    assert time.monotonic() - t0 < 5
    assert not r["ok"] and r["error_kind"] == "CODE_TIMEOUT" and r["pistas"]
    assert "0.3 s" in r["mensaje"] and "línea" in r["mensaje"] and "arranca" in r["mensaje"]
    assert foto(s) == antes


@pytest.mark.parametrize("codigo", ["while True: pass", "x = 0\nwhile 1: x += 1",
                                    "def f():\n    while True: pass\nf()"])
def test_execute_code_bucle_de_una_linea_se_corta_por_timeout(s, codigo):
    # El salto hacia atrás dentro de una misma línea no dispara LINE: el vigía escucha también JUMP.
    import time
    antes = foto(s)
    t0 = time.monotonic()
    r = api.llamar(s, "execute_code", {"code": codigo, "timeout": 0.3})
    assert time.monotonic() - t0 < 5
    assert not r["ok"] and r["error_kind"] == "CODE_TIMEOUT"
    assert foto(s) == antes


def test_execute_code_timeout_revierte_recalculos_aunque_atrape_todo(s):
    antes = foto(s)
    codigo = ("i = 0\n"
              "while True:\n"
              "    try:\n"
              "        i += 1\n"
              "        llamar('create_box', {'length': 5 + i % 3, 'width': 5, 'height': 5})\n"
              "    except:\n"
              "        pass\n")
    r = api.llamar(s, "execute_code", {"code": codigo, "timeout": 1})
    assert r["error_kind"] == "CODE_TIMEOUT"
    assert foto(s) == antes and len(s.doc.resultados) == len(s.doc.operaciones)
    assert ok(api.llamar(s, "execute_code", {"code": "result = 2 + 2"}))["result"] == 4   # sigue andando


def test_execute_code_timeout_invalido_none_y_anidado(s):
    for malo in (0, -1, float("nan")):
        assert api.llamar(s, "execute_code", {"code": "result = 1", "timeout": malo})["error_kind"] == "INVALID_ARGUMENTS"
    assert ok(api.llamar(s, "execute_code", {"code": "result = 1", "timeout": None}))["result"] == 1
    interno = "llamar('execute_code', {'code': 'while True:\\n    pass', 'timeout': 0.2})['error_kind']"
    assert ok(api.llamar(s, "execute_code", {"code": "result = " + interno}))["result"] == "CODE_TIMEOUT"
    props = next(h for h in api.catalogo() if h["nombre"] == "execute_code")["esquema"]["properties"]
    assert props["timeout"]["default"] == av.PLAZO_CODIGO == 60


# ---------------------------------------------------------------- guía
def test_guia_indice_y_flujo(s):
    ind = ok(api.llamar(s, "get_guide"))
    assert ind["topic"] == "indice" and "flujo" in ind["topics"] and "indice" in ind["topics"] and "flujo" in ind["text"]
    flujo = ok(api.llamar(s, "get_guide", {"topic": "flujo"}))
    assert flujo["topic"] == "flujo" and flujo["text"].startswith("# Ciclo de trabajo")
    assert ok(api.llamar(s, "get_guide", {"topic": "Flujo.md"}))["text"] == flujo["text"]


def test_guia_tema_inexistente_y_archivos_cortos(s):
    for malo in ("nada", "../errores", ""):
        r = api.llamar(s, "get_guide", {"topic": malo})
        if malo == "":                             # vacío cae al índice, no es error
            assert r["ok"] and r["result"]["topic"] == "indice"
            continue
        assert not r["ok"] and r["error_kind"] == "TOPIC_NOT_FOUND" and any("flujo" in p for p in r["pistas"])
    for tema in ok(api.llamar(s, "get_guide"))["topics"]:
        assert len(ok(api.llamar(s, "get_guide", {"topic": tema}))["text"].splitlines()) <= 60, tema


def test_guia_solo_nombra_herramientas_que_existen(s):
    conocidas = {h["nombre"] for h in api.catalogo()}
    for tema in ok(api.llamar(s, "get_guide"))["topics"]:
        texto = ok(api.llamar(s, "get_guide", {"topic": tema}))["text"]
        for nombre in re.findall(r"`([a-z]+(?:_[a-z]+)+)(?:\(|`)", texto):
            if nombre == "error_kind":             # clave de la respuesta de error, no una herramienta
                continue
            assert nombre in conocidas, f"{tema}: la guía nombra '{nombre}', que no es una herramienta"
    assert av._GUIA.is_dir()

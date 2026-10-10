# -*- coding: utf-8 -*-
"""Herramientas del grupo «grafo» (GH5 y GH8 de docs/brechas_grasshopper.md): list_graph_nodes, run_graph (sin tocar el
documento, con export a STEP/STL) y bake_graph (paso «Grafo» paramétrico del timeline), más el ejemplo para agentes."""
import copy
import json
import math
from pathlib import Path

import pytest

from omnicad import api
from omnicad.api import doc_markdown
from omnicad.api.herramientas_grafo import EJEMPLO
from omnicad.cli import main
from omnicad.grafo import catalogo
from omnicad.nucleo import geometria as geo

EJEMPLOS = Path(__file__).resolve().parents[2] / "ejemplos" / "agentes"
ARCHIVO_EJEMPLO = EJEMPLOS / "grilla_cajas.grafo.json"


@pytest.fixture
def s():
    return api.Sesion()


def ok(r):
    assert r["ok"], r
    return r["result"]


def llamar(sesion, nombre, **args):
    return ok(api.llamar(sesion, nombre, args))


def falla(sesion, nombre, kind, **args):
    r = api.llamar(sesion, nombre, args)
    assert not r["ok"] and r["error_kind"] == kind, r
    return r


def foto(sesion):
    doc = sesion.doc
    return json.dumps(doc.a_dict(), sort_keys=True), len(doc._deshacer), doc.modificado


def volumenes(sesion):
    return sorted(round(c["volume"], 3) for c in llamar(sesion, "get_scene_info")["bodies"])


def cilindros_en_circulo(radio_agujero=4.0):
    return {"nodos": [
        {"id": "centros", "tipo": "puntos_circulo", "entradas": {"radio": 30, "cantidad": 6}},
        {"id": "agujeros", "tipo": "cilindro", "entradas": {"base": {"de": "centros"}, "radio": radio_agujero,
                                                            "alto": 10}},
        {"id": "salida", "tipo": "salida", "nombre": "agujeros", "entradas": {"valor": {"de": "agujeros"}}}]}


# ---------------------------------------------------------------- catálogo y grupo
def test_grupo_grafo_registrado_en_el_mcp_la_cli_y_la_doc():
    from omnicad.servidor_mcp.servidor import GRUPOS_CONOCIDOS, GRUPOS_POR_DEFECTO
    herramientas = {h["nombre"]: h for h in api.catalogo("grafo")}
    assert set(herramientas) == {"list_graph_nodes", "run_graph", "bake_graph"}
    assert herramientas["bake_graph"]["modifica"] and not herramientas["run_graph"]["modifica"]
    assert "grafo" in GRUPOS_CONOCIDOS and "grafo" in GRUPOS_POR_DEFECTO and "grafo" in doc_markdown.GRUPOS
    assert "### `run_graph`" in doc_markdown.catalogo_a_markdown(api.catalogo())


def test_list_graph_nodes(s):
    todo = llamar(s, "list_graph_nodes")
    assert todo["count"] == len(todo["nodes"]) == len(catalogo()) >= 60
    assert set(todo["categories"]) == {n["category"] for n in todo["nodes"]}
    caja = next(n for n in todo["nodes"] if n["type"] == "caja")
    assert [p["name"] for p in caja["inputs"]] == ["centro", "ancho", "largo", "alto"]
    assert caja["inputs"][1] == {"name": "ancho", "type": "numero", "access": "item", "unit": "mm", "required": False,
                                 "default": 10.0}
    assert caja["outputs"] == [{"name": "cuerpo", "type": "cuerpo", "access": "item"}]
    assert todo["graph_format"]["example"] == EJEMPLO
    solidos = llamar(s, "list_graph_nodes", category="solidos", include_format=False)
    assert "graph_format" not in solidos and {n["category"] for n in solidos["nodes"]} == {"solidos"}
    assert {n["type"] for n in llamar(s, "list_graph_nodes", query="CAJA")["nodes"]} == {"caja", "caja_envolvente"}
    falla(s, "list_graph_nodes", "INVALID_ARGUMENTS", category="geometria")
    json.dumps(todo)


# ---------------------------------------------------------------- run_graph
def test_run_graph_no_toca_el_documento(s):
    llamar(s, "create_box", length=10, width=10, height=10)
    antes = foto(s)
    r = llamar(s, "run_graph", graph=EJEMPLO)
    assert foto(s) == antes
    assert r["status"] == "ok" and set(r["outputs"]) == {"pieza", "volumen"}
    assert r["outputs"]["volumen"] == {"count": 1, "branches": {"{0}": [4500.0]}, "truncated": False, "value": 4500.0}
    pieza = r["outputs"]["pieza"]["value"]
    assert pieza["kind"] == "body" and pieza["solids"] == 1 and pieza["volume"] == pytest.approx(4500.0)
    assert pieza["bounding_box"] == {"min": [-5.0, -5.0, 0.0], "max": [25.0, 25.0, 5.0], "size": [30.0, 30.0, 5.0]}
    assert [i["name"] for i in r["inputs"]] == ["lado", "alto", "filas"] and r["inputs"][0]["value"] == 10
    nodos = {n["id"]: n for n in r["nodes"]}
    assert list(nodos) == [n["id"] for n in EJEMPLO["nodos"]]
    assert nodos["cajas"]["items"] == {"cuerpo": 9} and all(n["status"] == "ok" and n["ms"] >= 0 for n in nodos.values())
    assert "nodes" not in llamar(s, "run_graph", graph=EJEMPLO, include_nodes=False)


def test_run_graph_variantes_recalculan_solo_lo_que_cambia(s):
    llamar(s, "run_graph", graph=EJEMPLO)
    r = llamar(s, "run_graph", graph=copy.deepcopy(EJEMPLO), inputs={"alto": 10})
    assert r["outputs"]["volumen"]["value"] == pytest.approx(9000.0)
    assert (r["computed_nodes"], r["cached_nodes"]) == (6, 3)
    assert {n["id"] for n in r["nodes"] if not n["computed"]} == {"lado", "filas", "grilla"}
    for lado in (6, 7, 8):                                              # «hacé variantes de este grafo»
        r = llamar(s, "run_graph", graph=EJEMPLO, inputs={"lado": lado, "filas": 2}, outputs=["volumen"],
                   include_nodes=False)
        assert list(r["outputs"]) == ["volumen"] and r["outputs"]["volumen"]["value"] == pytest.approx(4 * lado ** 2 * 5)


def test_run_graph_usa_los_parametros_del_documento(s):
    llamar(s, "create_parameter", name="ancho", expression="8 mm")
    r = llamar(s, "run_graph", graph=EJEMPLO, inputs={"lado": "ancho", "alto": "ancho / 4", "grilla.paso_x": "ancho * 2"})
    assert r["outputs"]["volumen"]["value"] == pytest.approx(9 * 64 * 2)                    # cajas separadas en x
    assert r["outputs"]["pieza"]["value"]["solids"] == 3                                    # 3 tiras a lo largo de y


def test_run_graph_errores_claros(s):
    r = falla(s, "run_graph", "INVALID_ARGUMENTS", graph=EJEMPLO, inputs={"ladoo": 3})
    assert "no tiene la entrada «ladoo»" in r["mensaje"] and any("lado, alto, filas" in p for p in r["pistas"])
    r = falla(s, "run_graph", "INVALID_ARGUMENTS", graph={"nodos": [{"id": "a", "tipo": "cajita"}]})
    assert any("caja" in p for p in r["pistas"])
    ciclo = {"nodos": [{"id": "a", "tipo": "sumar", "entradas": {"a": {"de": "b"}}},
                       {"id": "b", "tipo": "sumar", "entradas": {"a": {"de": "a"}}}]}
    assert "ciclo: a → b → a" in falla(s, "run_graph", "INVALID_ARGUMENTS", graph=ciclo)["mensaje"]
    assert "pieza" in " ".join(falla(s, "run_graph", "INVALID_ARGUMENTS", graph=EJEMPLO, outputs=["piezas"])["pistas"])
    falla(s, "run_graph", "INVALID_ARGUMENTS", graph=EJEMPLO, inputs={"lado": {"de": "alto"}})
    falla(s, "run_graph", "INVALID_ARGUMENTS", graph=[1, 2])
    falla(s, "run_graph", "INVALID_ARGUMENTS", graph="{no es json")
    falla(s, "run_graph", "FILE_NOT_FOUND", graph="no/existe.json")


def test_run_graph_con_un_nodo_en_error_avisa_y_sigue(s):
    grafo = {"nodos": [{"id": "d", "tipo": "dividir", "entradas": {"a": 10, "b": [2, 0]}},
                       {"id": "res", "tipo": "salida", "entradas": {"valor": {"de": "d"}}}]}
    r = api.llamar(s, "run_graph", {"graph": grafo})
    assert r["ok"] and r["result"]["status"] == "error"
    assert r["result"]["outputs"]["res"]["branches"] == {"{0}": [5.0, None]}
    assert r["avisos"] == ["Nodo «d» (error): División por cero."]


def test_run_graph_acepta_archivo_y_texto_json(s):
    r = llamar(s, "run_graph", graph=str(ARCHIVO_EJEMPLO))                   # {"graph", "inputs"}: usa sus entradas
    assert r["outputs"]["volumen"]["value"] == pytest.approx(16 * 144 * 5)
    r = llamar(s, "run_graph", graph=str(ARCHIVO_EJEMPLO), inputs={"filas": 1})  # las de la llamada ganan
    assert r["outputs"]["volumen"]["value"] == pytest.approx(144 * 5)
    assert llamar(s, "run_graph", graph=json.dumps(EJEMPLO))["outputs"]["volumen"]["value"] == pytest.approx(4500.0)


def test_run_graph_exporta_step_y_stl(s, tmp_path):
    step, stl = tmp_path / "grilla.step", tmp_path / "grilla.stl"
    r = llamar(s, "run_graph", graph=EJEMPLO, export=str(step))
    assert r["export"]["format"] == "step" and r["export"]["bodies"] == 1 and step.stat().st_size > 0
    otra = api.Sesion()
    llamar(otra, "open_document", path=str(step))
    assert volumenes(otra) == [pytest.approx(4500.0)]
    r = llamar(s, "run_graph", graph=EJEMPLO, export=str(stl), outputs=["pieza"])
    assert r["export"]["triangles"] > 0 and stl.read_bytes()[:5] != b"solid"            # STL binario
    falla(s, "run_graph", "FILE_EXISTS", graph=EJEMPLO, export=str(stl))
    assert llamar(s, "run_graph", graph=EJEMPLO, export=str(stl), overwrite=True)["export"]["size_bytes"] > 0
    falla(s, "run_graph", "INVALID_FORMAT", graph=EJEMPLO, export=str(tmp_path / "grilla.dxf"))
    falla(s, "run_graph", "FILE_NOT_FOUND", graph=EJEMPLO, export=str(tmp_path / "no" / "grilla.step"))
    falla(s, "run_graph", "NOTHING_TO_EXPORT", graph=EJEMPLO, outputs=["volumen"], export=str(tmp_path / "v.step"))


# ---------------------------------------------------------------- bake_graph
def test_bake_graph_es_un_paso_parametrico(s):
    llamar(s, "create_parameter", name="lado_p", expression="12 mm")
    r = llamar(s, "bake_graph", graph=EJEMPLO, inputs={"lado": "lado_p"}, outputs=["pieza"], name="Grilla")
    assert r["feature"] == {"id": "op1", "name": "Grilla", "type": "grafo"} and r["parametric"]
    assert [(c["name"], c["volume"]) for c in r["bodies_created"]] == [("pieza", pytest.approx(9 * 144 * 5))]
    paso = s.paso("Grilla")
    assert paso.p["entradas"] == {"lado": "lado_p"} and paso.p["grafo"]["formato"] == "omnicad.grafo"
    llamar(s, "set_parameter", name="lado_p", expression="20 mm")              # el paso sigue al parámetro
    assert volumenes(s) == [pytest.approx(9 * 400 * 5)]
    r = falla(s, "delete_parameter", "PARAMETER_IN_USE", name="lado_p")
    assert "Grilla" in r["mensaje"]
    llamar(s, "edit_feature", feature="Grilla", params={"entradas": {"lado": 6, "filas": 2}})
    assert volumenes(s) == [pytest.approx(4 * 36 * 5)]
    llamar(s, "undo")
    llamar(s, "undo")
    assert volumenes(s) == [pytest.approx(9 * 144 * 5)]
    llamar(s, "undo")
    assert volumenes(s) == []


def test_bake_graph_corta_un_cuerpo_existente(s):
    placa = llamar(s, "create_box", length=100, width=100, height=10)["bodies_created"][0]["id"]
    r = llamar(s, "bake_graph", graph=cilindros_en_circulo(), operation="cut", target=placa)
    assert r["bodies_created"] == [] and [m["id"] for m in r["bodies_modified"]] == [placa]
    assert volumenes(s) == [pytest.approx(100 * 100 * 10 - 6 * math.pi * 16 * 10)]
    assert s.paso(r["feature"]["id"]).dependencias() >= {"op1"}                 # no se puede mover antes de la placa
    llamar(s, "edit_feature", feature=r["feature"]["id"], params={"entradas": {"agujeros.radio": 2}})
    assert volumenes(s) == [pytest.approx(100 * 100 * 10 - 6 * math.pi * 4 * 10)]


def test_bake_graph_fijo_crea_una_operacion_base(s):
    llamar(s, "create_parameter", name="lado_p", expression="10 mm")
    r = llamar(s, "bake_graph", graph=EJEMPLO, inputs={"lado": "lado_p"}, fixed=True)
    assert r["feature"]["type"] == "operacion_base" and not r["parametric"]
    assert [c["name"] for c in r["bodies_created"]] == ["pieza"] and volumenes(s) == [pytest.approx(4500.0)]
    llamar(s, "set_parameter", name="lado_p", expression="20 mm")              # cuerpos fijos: no cambian
    assert volumenes(s) == [pytest.approx(4500.0)]
    falla(s, "bake_graph", "INVALID_ARGUMENTS", graph=EJEMPLO, fixed=True, operation="cut")


def test_bake_graph_que_falla_deja_el_documento_igual(s):
    llamar(s, "create_box", length=10, width=10, height=10)
    antes = foto(s)
    con_error = {"nodos": [{"id": "d", "tipo": "dividir", "entradas": {"a": 10, "b": 0}},
                           {"id": "c", "tipo": "caja", "entradas": {"ancho": {"de": "d"}}},
                           {"id": "pieza", "tipo": "salida", "entradas": {"valor": {"de": "c"}}}]}
    r = falla(s, "bake_graph", "OPERATION_FAILED", graph=con_error)
    assert "División por cero" in r["mensaje"]
    sin_salida = {"nodos": [{"id": "c", "tipo": "caja"}]}
    assert "no dio cuerpos" in falla(s, "bake_graph", "OPERATION_FAILED", graph=sin_salida)["mensaje"]
    falla(s, "bake_graph", "INVALID_ARGUMENTS", graph=EJEMPLO, outputs=["nada"])
    falla(s, "bake_graph", "INVALID_ARGUMENTS", graph=EJEMPLO, inputs={"nada": 1})
    falla(s, "bake_graph", "OPERATION_FAILED", graph=con_error, fixed=True)
    assert foto(s) == antes


def test_la_receta_guardada_y_abierta_reevalua_igual(s, tmp_path):
    llamar(s, "create_parameter", name="lado_p", expression="12 mm")
    llamar(s, "bake_graph", graph=EJEMPLO, inputs={"lado": "lado_p", "filas": 2})
    esperado = volumenes(s)
    assert esperado == [pytest.approx(4 * 144 * 5)]
    ruta = tmp_path / "grilla.omnicad"
    llamar(s, "save_document", path=str(ruta))
    otra = api.Sesion()
    llamar(otra, "open_document", path=str(ruta))
    assert volumenes(otra) == esperado
    assert otra.paso("op1").p["grafo"] == s.paso("op1").p["grafo"]
    llamar(otra, "set_parameter", name="lado_p", expression="5 mm")            # se reevalúa tras abrir
    assert volumenes(otra) == [pytest.approx(4 * 25 * 5)]
    tercera = api.Sesion()                                                     # receta → apply_recipe: lo mismo
    llamar(tercera, "apply_recipe", recipe=llamar(s, "get_recipe")["recipe"])
    assert volumenes(tercera) == esperado
    cuerpo = tercera.doc.estado_final.cuerpos["op1.c1"]
    assert geo.es_valida(cuerpo.forma) and cuerpo.nombre == "pieza"


def test_el_paso_grafo_por_run_operation_y_describe_operation(s):
    d = llamar(s, "describe_operation", type="grafo")
    assert [p["name"] for p in d["params"]] == ["grafo", "entradas", "salidas", "operacion", "objetivo"]
    assert next(p for p in d["params"] if p["name"] == "operacion")["choices"] == ["nuevo", "unir", "cortar", "intersecar"]
    r = llamar(s, "run_operation", type="grafo", params={"grafo": EJEMPLO, "entradas": {"filas": 2}})
    assert r["status"] == "ok" and volumenes(s) == [pytest.approx(4 * 100 * 5)]
    falla(s, "run_operation", "OPERATION_FAILED", type="grafo")                # grafo vacío
    r = falla(s, "run_operation", "OPERATION_FAILED", type="grafo", params={"grafo": {"nodos": [{"id": "a", "tipo": "x"}]}})
    assert "Grafo inválido" in r["mensaje"]


def test_varias_piezas_se_nombran_en_orden(s):
    r = llamar(s, "bake_graph", graph=cilindros_en_circulo())
    assert [c["name"] for c in r["bodies_created"]] == [f"agujeros {i}" for i in range(1, 7)]
    assert all(c["volume"] == pytest.approx(math.pi * 16 * 10) for c in r["bodies_created"])


# ---------------------------------------------------------------- ejemplo para agentes (CLI)
def correr(capsys, *argv):
    capsys.readouterr()
    codigo = main([str(a) for a in argv])
    salida = capsys.readouterr()
    return codigo, salida.out, salida.err


def test_el_ejemplo_coincide_con_el_de_list_graph_nodes():
    datos = json.loads(ARCHIVO_EJEMPLO.read_text(encoding="utf-8"))
    assert datos["graph"] == EJEMPLO and datos["inputs"] == {"lado": 12, "filas": 4}
    texto = (EJEMPLOS / "README.md").read_text(encoding="utf-8")
    assert ARCHIVO_EJEMPLO.name in texto and "run_graph" in texto and "bake_graph" in texto


def test_el_ejemplo_corre_y_se_hornea_por_la_cli(tmp_path, capsys):
    codigo, out, err = correr(capsys, "call", "run_graph", "--args-file", ARCHIVO_EJEMPLO, "--json",
                              f"export={tmp_path / 'grilla.step'}")
    assert codigo == 0, err
    r = json.loads(out)["result"]
    assert r["outputs"]["volumen"]["value"] == pytest.approx(11520.0) and (tmp_path / "grilla.step").is_file()
    pieza = tmp_path / "pieza.omnicad"
    assert correr(capsys, "new", pieza)[0] == 0
    codigo, _out, err = correr(capsys, "call", "bake_graph", "--doc", pieza, f"graph={ARCHIVO_EJEMPLO}")
    assert codigo == 0, err
    codigo, out, _err = correr(capsys, "info", pieza, "--json")
    cuerpos = json.loads(out)["result"]["bodies"]
    assert [(c["name"], round(c["volume"], 3)) for c in cuerpos] == [("pieza", 11520.0)]

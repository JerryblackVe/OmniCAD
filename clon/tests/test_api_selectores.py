# -*- coding: utf-8 -*-
"""Selectores de caras y aristas (api/selectores.py) y las herramientas de búsqueda y medida que los usan."""
import math

import pytest

from omnicad import api
from omnicad.api import selectores as sl


@pytest.fixture
def s():
    return api.Sesion()


def ok(r):
    assert r["ok"], r
    return r["result"]


def llamar(sesion, nombre, **args):
    return ok(api.llamar(sesion, nombre, args))


def falla(sesion, nombre, **args):
    r = api.llamar(sesion, nombre, args)
    assert not r["ok"], r
    return r


@pytest.fixture
def caja(s):
    llamar(s, "create_box", length=20, width=20, height=20)
    return s


def cuantas(sesion, tool, selector, **extra):
    r = llamar(sesion, tool, selector=selector, **extra)
    return r["count"]


def test_herramientas_de_inspeccion_nuevas():
    nombres = {h["nombre"]: h for h in api.catalogo("inspeccion")}
    for n in ("find_faces", "find_edges", "measure_angle"):
        assert n in nombres and not nombres[n]["modifica"]


def test_caja_aristas_verticales_son_cuatro(caja):
    r = llamar(caja, "find_edges", selector="|Z")
    assert r["count"] == 4 and r["total"] == 12
    for e in r["edges"]:
        assert e["type"] == "line" and e["length"] == pytest.approx(20) and abs(e["direction"][2]) == pytest.approx(1)
        assert e["id"].startswith("Cuerpo1/E")


@pytest.mark.parametrize("selector,aristas,caras", [
    ("|Z", 4, 2), ("#Z", 8, 4), (">Z", 4, 1), ("<Z", 4, 1), (">X", 4, 1), ("<Y", 4, 1),
    ("+Z", 4, 1), ("-X", 4, 1), ("%LINE", 12, None), ("%PLANE", None, 6), ("all", 12, 6),
    (">Z and >X", 1, 0), ("|Z and >X", 2, 0), (">Z or <Z", 8, 2), ("not >Z", 8, 5),
    ("(>Z or <Z) and not >X", 6, 2), ("#Z and not <X", 6, 3), (">Z[1]", None, 4), ("<Z[-1]", None, 1),
    ("nearest:[10, 10, 25]", 1, 1), ("  >Z  ", 4, 1), (">z", 4, 1),
])
def test_sintaxis_sobre_caja(caja, selector, aristas, caras):
    for tool, esperado in (("find_edges", aristas), ("find_faces", caras)):
        r = api.llamar(caja, tool, {"selector": selector})
        if esperado is None:
            continue
        if esperado == 0:
            assert not r["ok"] and r["error_kind"] == "NO_MATCH", (tool, selector, r)
        else:
            assert r["ok"] and r["result"]["count"] == esperado, (tool, selector, r)


def test_lo_que_cada_selector_elige_realmente(caja):
    tapa = llamar(caja, "find_faces", selector=">Z")["faces"][0]
    assert tapa["center"] == [0.0, 0.0, 20.0] and tapa["normal"] == [0.0, 0.0, 1.0] and tapa["area"] == pytest.approx(400)
    assert tapa["type"] == "plane" and tapa["center_uv"] == [0.0, 0.0] and tapa["id"].startswith("Cuerpo1/F")
    # como CadQuery: |Z en caras = normal paralela a Z (tapa y base); #Z = laterales
    assert {f["normal"][2] for f in llamar(caja, "find_faces", selector="|Z")["faces"]} == {1.0, -1.0}
    assert all(f["normal"][2] == 0 for f in llamar(caja, "find_faces", selector="#Z")["faces"])
    cerca = llamar(caja, "find_faces", selector="nearest:[50, 0, 10]")["faces"][0]
    assert cerca["normal"] == [1.0, 0.0, 0.0]
    arriba = llamar(caja, "find_edges", selector=">Z")["edges"]
    assert all(e["center"][2] == pytest.approx(20) for e in arriba)


def test_cilindro_tipos_y_aristas_circulares(s):
    llamar(s, "create_cylinder", radius=5, height=10)
    caras = llamar(s, "find_faces")
    assert {f["type"] for f in caras["faces"]} == {"plane", "cylinder"} and caras["count"] == 3
    lat = llamar(s, "find_faces", selector="%CYLINDER")["faces"][0]
    assert lat["radius"] == pytest.approx(5) and lat["axis"] == pytest.approx([0, 0, 1])
    circ = llamar(s, "find_edges", selector="%CIRCLE")
    assert circ["count"] == 2 and all(e["radius"] == pytest.approx(5) for e in circ["edges"])
    assert cuantas(s, "find_edges", "%CIRCLE and >Z") == 1
    assert cuantas(s, "find_edges", "%LINE") == 1                      # la costura del cilindro
    # %CIRCLE no es un tipo de cara
    r = falla(s, "find_faces", selector="%CIRCLE")
    assert r["error_kind"] == "INVALID_SELECTOR" and "PLANE" in r["mensaje"]


@pytest.mark.parametrize("malo", [">", ">W", "Z>", "%", "nearest:[1,2]", "nearest:1,2,3", "(>Z", ">Z)", ">Z <Z", "and",
                                  ">Z and", "not", "", "   ", ">Z[9]", "|Z |X", ">Z xor <Z"])
def test_selector_invalido(caja, malo):
    r = falla(caja, "find_faces", selector=malo)
    assert r["error_kind"] == "INVALID_SELECTOR" and r["pistas"]
    assert any("selectores" in p or ">Z" in p for p in r["pistas"])


def test_selector_sin_coincidencias_da_no_match_con_pista(caja):
    r = falla(caja, "find_faces", selector="%SPHERE")
    assert r["error_kind"] == "NO_MATCH"
    assert "6 caras" in r["mensaje"] and "6 PLANE" in r["mensaje"] and r["pistas"]
    r = falla(caja, "find_edges", selector="%CIRCLE")
    assert r["error_kind"] == "NO_MATCH" and "12 aristas" in r["mensaje"] and "12 LINE" in r["mensaje"]


def test_compilar_y_precedencia():
    assert sl.compilar(">Z or <Z and |X")[0] == "or"            # and ata más que or
    assert sl.compilar("not >Z and <X")[0] == "and"             # not ata más que and
    assert sl.parece_selector("|Z") and not sl.parece_selector("Cuerpo1") and not sl.parece_selector("")


def test_acepta_menor_y_mayor_escapados_como_html(caja):
    """Un agente real mandó face="&lt;Z" (prueba K con Claude Code): vale lo mismo que "<Z"."""
    assert sl.compilar("&lt;Z") == sl.compilar("<Z")
    assert sl.compilar("&lt;Z and &gt;X") == sl.compilar("<Z and >X")
    assert llamar(caja, "find_faces", selector="&lt;Z")["faces"] == llamar(caja, "find_faces", selector="<Z")["faces"]


def test_ids_efimeros_se_vencen_con_un_cambio(caja):
    id_tapa = llamar(caja, "find_faces", selector=">Z")["faces"][0]["id"]
    assert llamar(caja, "measure_angle", a=id_tapa, b="<Z")["angle"] == pytest.approx(180)
    llamar(caja, "create_parameter", name="p", expression="1 mm")   # cualquier cambio del documento
    r = falla(caja, "measure_angle", a=id_tapa, b="<Z")
    assert r["error_kind"] == "STALE_ID" and r["pistas"]
    nuevo = llamar(caja, "find_faces", body="Cuerpo1", selector=">Z")["faces"][0]["id"]   # volver a listar lo rehabilita
    assert llamar(caja, "measure_angle", a=nuevo, b="<Z")["angle"] == pytest.approx(180)


def test_id_que_no_existe_y_formato(caja):
    assert falla(caja, "measure_angle", a="Cuerpo1/F99", b=">Z")["error_kind"] == "ELEMENT_NOT_FOUND"
    assert falla(caja, "measure_angle", a="Nada/F1", b=">Z")["error_kind"] == "BODY_NOT_FOUND"


def test_varios_cuerpos_exigen_body_para_selectores(caja):
    llamar(caja, "create_box", length=5, width=5, height=5, x=50)
    r = falla(caja, "measure_angle", a=">Z", b=">X")
    assert r["error_kind"] == "AMBIGUOUS_REFERENCE" and "body" in r["mensaje"]
    todas = llamar(caja, "find_faces", selector=">Z")                  # find_* recorre todos los cuerpos
    assert todas["count"] == 2 and todas["total"] == 12
    assert llamar(caja, "find_faces", body="Cuerpo2", selector=">Z")["count"] == 1
    # un id basta aunque haya varios cuerpos
    ids = [f["id"] for f in todas["faces"]]
    assert ids[0].startswith("Cuerpo1/") and ids[1].startswith("Cuerpo2/")
    assert llamar(caja, "measure_angle", a=ids[0], b=ids[1])["angle"] == pytest.approx(0)


def test_measure_angle(caja):
    r = llamar(caja, "measure_angle", a=">Z", b=">X")
    assert r["angle"] == pytest.approx(90) and r["kind"] == "face-face" and r["acute_angle"] == pytest.approx(90)
    assert llamar(caja, "measure_angle", a=">Z", b="<Z")["angle"] == pytest.approx(180)
    assert llamar(caja, "measure_angle", a=">Z", b="<Z")["acute_angle"] == pytest.approx(0)
    # arista con arista
    assert llamar(caja, "measure_angle", a="edges:|Z and >X and >Y", b="edges:|X and >Y and >Z")["angle"] == pytest.approx(90)
    # arista con cara: una arista vertical contra la tapa es perpendicular (90°); contra una lateral paralela, 0°
    assert llamar(caja, "measure_angle", a="edges:|Z and >X and >Y", b=">Z")["angle"] == pytest.approx(90)
    assert llamar(caja, "measure_angle", a="edges:|Z and >X and >Y", b=">X")["angle"] == pytest.approx(0)
    # el selector ambiguo se rechaza con pista
    r = falla(caja, "measure_angle", a="#Z", b=">X")
    assert r["error_kind"] == "AMBIGUOUS_REFERENCE" and "4 caras" in r["mensaje"]


def test_measure_angle_cilindro_no_se_puede(s):
    llamar(s, "create_cylinder", radius=5, height=10)
    r = falla(s, "measure_angle", a="%CYLINDER", b=">Z")
    assert r["error_kind"] == "UNSUPPORTED_ELEMENT"


def test_measure_distance_acepta_caras_y_aristas(caja):
    assert llamar(caja, "measure_distance", a=">Z", b="<Z")["distance"] == pytest.approx(20)
    r = llamar(caja, "measure_distance", a=">Z", b=[0, 0, 50])
    assert r["distance"] == pytest.approx(30) and r["a"]["kind"] == "face"
    r = llamar(caja, "measure_distance", a="edges:|Z and >X and >Y", b="edges:|Z and <X and <Y")
    assert r["distance"] == pytest.approx(math.hypot(20, 20), abs=1e-3) and r["a"]["kind"] == "edge"
    # los cuerpos siguen funcionando por id y nombre; un nombre inexistente que no es selector sigue dando BODY_NOT_FOUND
    assert llamar(caja, "measure_distance", a="Cuerpo1", b=[0, 0, 30])["distance"] == pytest.approx(10)
    assert falla(caja, "measure_distance", a="Fantasma", b=[0, 0, 0])["error_kind"] == "BODY_NOT_FOUND"


def test_busqueda_sin_cuerpos(s):
    assert falla(s, "find_faces")["error_kind"] == "BODY_NOT_FOUND"
    llamar(s, "create_box", length=10, width=10, height=10)
    assert llamar(s, "find_faces")["total"] == 6


def test_find_no_modifica_el_documento(caja):
    import json
    antes = json.dumps(caja.doc.a_dict(), sort_keys=True)
    llamar(caja, "find_faces")
    llamar(caja, "find_edges", selector="|Z")
    llamar(caja, "measure_angle", a=">Z", b=">X")
    assert json.dumps(caja.doc.a_dict(), sort_keys=True) == antes

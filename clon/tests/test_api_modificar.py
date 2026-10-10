# -*- coding: utf-8 -*-
"""Empalme, chaflán, vaciado, agujero, desmoldeo y boceto sobre cara usando selectores (Paquete D)."""
import json
import math

import pytest

from omnicad import api


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


def foto(sesion):
    doc = sesion.doc
    return (json.dumps(doc.a_dict(), sort_keys=True), [(r.estado, r.mensaje) for r in doc.resultados],
            len(doc._deshacer), len(doc._rehacer), doc.modificado)


def volumen(sesion, cuerpo="Cuerpo1"):
    return next(c["volume"] for c in llamar(sesion, "get_scene_info")["bodies"] if c["name"] == cuerpo)


def caja_z(sesion, cuerpo="Cuerpo1"):
    bb = next(c["bounding_box"] for c in llamar(sesion, "get_scene_info")["bodies"] if c["name"] == cuerpo)
    return bb["min"][2], bb["max"][2]


@pytest.fixture
def caja(s):
    llamar(s, "create_box", length=20, width=20, height=20)
    return s


@pytest.fixture
def caja_param(s):
    llamar(s, "create_parameter", name="lado", expression="20 mm")
    llamar(s, "create_box", length="lado", width="lado", height="lado")
    return s


def test_herramientas_del_grupo_solido_nuevas():
    nombres = {h["nombre"]: h for h in api.catalogo("solido")}
    for n in ("fillet", "chamfer", "shell", "create_hole", "draft"):
        assert nombres[n]["modifica"]


# ---------------------------------------------------------------- empalme
def test_fillet_aristas_verticales(caja):
    r = llamar(caja, "fillet", edges="|Z", radius=2)
    assert r["edges_used"] == 4 and r["feature"]["type"] == "empalme"
    esperado = 20 ** 3 - 4 * (4 - math.pi) * 20          # 4 aristas · (r² − πr²/4) · largo, con r = 2
    assert volumen(caja) == pytest.approx(esperado, abs=1e-3) and volumen(caja) == pytest.approx(7931.3274, abs=1e-3)
    assert r["bodies_modified"][0]["previous_volume"] == pytest.approx(8000)
    assert len(llamar(caja, "find_faces", selector="%CYLINDER")["faces"]) == 4


def test_fillet_es_un_solo_paso_de_deshacer(caja):
    llamar(caja, "fillet", edges="|Z", radius=2)
    llamar(caja, "undo")
    assert volumen(caja) == pytest.approx(8000)


def test_fillet_con_ids_y_con_lista_mixta(caja):
    ids = [e["id"] for e in llamar(caja, "find_edges", selector="|Z")["edges"]]
    assert llamar(caja, "fillet", edges=ids, radius=2)["edges_used"] == 4
    assert volumen(caja) == pytest.approx(7931.3274, abs=1e-3)


def test_fillet_ids_efimeros_y_mezcla(caja):
    una = llamar(caja, "find_edges", selector="|Z and >X and >Y")["edges"][0]["id"]
    r = llamar(caja, "fillet", edges=[una, "|Z and <X"], radius=1)          # 1 por id + 2 del selector (una se repite o no)
    assert r["edges_used"] == 3
    assert volumen(caja) == pytest.approx(8000 - 3 * (1 - math.pi / 4) * 20, abs=1e-3)


def test_fillet_con_id_vencido(caja):
    ids = [e["id"] for e in llamar(caja, "find_edges", selector="|Z")["edges"]]
    llamar(caja, "create_parameter", name="otro", expression="3 mm")
    antes = foto(caja)
    r = falla(caja, "fillet", edges=ids, radius=2)
    assert r["error_kind"] == "STALE_ID" and foto(caja) == antes


def test_fillet_sobrevive_al_cambio_de_un_parametro(caja_param):
    s = caja_param
    llamar(s, "fillet", edges="|Z", radius=2)
    assert volumen(s) == pytest.approx(8000 - 4 * (4 - math.pi) * 20, abs=1e-3)
    r = api.llamar(s, "set_parameter", {"name": "lado", "expression": "30 mm"})
    assert r["ok"], r
    assert volumen(s) == pytest.approx(27000 - 4 * (4 - math.pi) * 30, abs=1e-3)          # mismas 4 aristas, más largas
    assert len(llamar(s, "find_faces", selector="%CYLINDER")["faces"]) == 4
    llamar(s, "set_parameter", name="lado", expression="12 mm")
    assert volumen(s) == pytest.approx(1728 - 4 * (4 - math.pi) * 12, abs=1e-3)


def test_fillet_radio_parametrico(caja_param):
    s = caja_param
    llamar(s, "create_parameter", name="r", expression="2 mm")
    llamar(s, "fillet", edges="|Z", radius="r")
    llamar(s, "set_parameter", name="r", expression="3 mm")
    assert volumen(s) == pytest.approx(8000 - 4 * (9 - 9 * math.pi / 4) * 20, abs=1e-3)


def test_referencia_perdida_da_reference_lost_y_no_cambia_nada(caja_param):
    s = caja_param
    llamar(s, "fillet", edges="|Z", radius=2)
    antes = foto(s)
    r = falla(s, "edit_feature", feature="op1", params={"forma": "esfera"})           # la caja pasa a ser una esfera
    assert r["error_kind"] == "REFERENCE_LOST" and r["pistas"] and "referencia" in r["mensaje"]
    assert foto(s) == antes


def test_fillet_errores(caja):
    antes = foto(caja)
    casos = [({"edges": "%CIRCLE", "radius": 2}, "NO_MATCH"),
             ({"edges": "|Z |X", "radius": 2}, "INVALID_SELECTOR"),
             ({"edges": [], "radius": 2}, "INVALID_ARGUMENTS"),
             ({"edges": "|Z", "radius": 0}, "INVALID_ARGUMENTS"),
             ({"edges": "|Z", "radius": 15}, "OPERATION_FAILED"),                    # no cabe: el paso falla y se descarta
             ({"edges": ">Z", "radius": 2, "body": "Fantasma"}, "BODY_NOT_FOUND"),
             ({"edges": "Cuerpo1/F1", "radius": 2}, "INVALID_ARGUMENTS"),            # una cara donde van aristas
             ({"edges": "faces:>Z", "radius": 2}, "INVALID_ARGUMENTS")]
    for args, kind in casos:
        r = falla(caja, "fillet", **args)
        assert r["error_kind"] == kind, (args, r)
        assert foto(caja) == antes, args


def test_fillet_con_varios_cuerpos_pide_body(caja):
    llamar(caja, "create_box", length=10, width=10, height=10, x=50)
    assert falla(caja, "fillet", edges="|Z", radius=1)["error_kind"] == "AMBIGUOUS_REFERENCE"
    r = llamar(caja, "fillet", edges="|Z", radius=1, body="Cuerpo2")
    assert r["edges_used"] == 4 and r["bodies_affected"] == ["op2.c1"]
    assert volumen(caja, "Cuerpo1") == pytest.approx(8000) and volumen(caja, "Cuerpo2") < 1000


# ---------------------------------------------------------------- chaflán
def test_chamfer_aristas_verticales(caja):
    r = llamar(caja, "chamfer", edges="|Z", distance=2)
    assert r["edges_used"] == 4 and r["feature"]["type"] == "chaflan"
    assert volumen(caja) == pytest.approx(20 ** 3 - 4 * (2 * 2 / 2) * 20, abs=1e-3)          # triángulo 2×2 por arista


def test_chamfer_tapa_y_parametro(caja_param):
    s = caja_param
    llamar(s, "chamfer", edges=">Z", distance=3)
    v1 = volumen(s)
    assert v1 == pytest.approx(8000 - 324, abs=1e-3)           # la capa de 3 mm de arriba es un tronco: 7676
    llamar(s, "set_parameter", name="lado", expression="30 mm")
    assert volumen(s) == pytest.approx(27000 - 504, abs=1e-3)                         # la misma tapa, ya más grande


# ---------------------------------------------------------------- vaciado
def test_shell_abre_la_tapa(caja):
    r = llamar(caja, "shell", body="Cuerpo1", faces=">Z", thickness=2)
    assert r["faces_removed"] == 1 and r["feature"]["type"] == "vaciado"
    assert volumen(caja) == pytest.approx(8000 - 16 * 16 * 18, abs=1e-3)                    # = 3392
    assert caja_z(caja) == (0.0, 20.0)                                                     # hacia adentro: no crece


def test_shell_hacia_afuera_y_cerrado(caja):
    llamar(caja, "shell", body="Cuerpo1", faces="<Z", thickness=1, direction="outside")
    assert caja_z(caja) == (0.0, 21.0)                                                      # crece por fuera; la cara quitada queda en z=0
    llamar(caja, "undo")
    llamar(caja, "shell", body="Cuerpo1", faces=[], thickness=2)
    assert volumen(caja) == pytest.approx(8000 - 16 ** 3, abs=1e-3)


def test_shell_cara_por_id_y_errores(caja):
    cara = llamar(caja, "find_faces", selector=">Z")["faces"][0]["id"]
    llamar(caja, "shell", body="Cuerpo1", faces=cara, thickness=2)
    assert volumen(caja) == pytest.approx(3392, abs=1e-3)
    antes = foto(caja)
    for args, kind in [({"body": "Cuerpo1", "faces": "%SPHERE", "thickness": 2}, "NO_MATCH"),
                       ({"body": "Cuerpo1", "faces": ">Z", "thickness": 0}, "INVALID_ARGUMENTS"),
                       ({"body": "Cuerpo1", "faces": ">Z", "thickness": 9}, "OPERATION_FAILED"),
                       ({"body": "Nada", "faces": ">Z", "thickness": 2}, "BODY_NOT_FOUND")]:
        assert falla(caja, "shell", **args)["error_kind"] == kind, args
        assert foto(caja) == antes


def test_shell_sobrevive_al_cambio_de_parametro(caja_param):
    s = caja_param
    llamar(s, "shell", body="Cuerpo1", faces=">Z", thickness=2)
    llamar(s, "set_parameter", name="lado", expression="30 mm")
    assert volumen(s) == pytest.approx(27000 - 26 * 26 * 28, abs=1e-3)


def test_fillet_de_las_verticales_y_despues_shell(caja_param):
    s = caja_param
    llamar(s, "fillet", edges="|Z", radius=3)
    llamar(s, "shell", body="Cuerpo1", faces=">Z", thickness=2)
    v20 = volumen(s)
    llamar(s, "set_parameter", name="lado", expression="40 mm")
    assert volumen(s) > 4 * v20 * 0.9


# ---------------------------------------------------------------- agujero
def test_agujero_pasante(caja):
    r = llamar(caja, "create_hole", face=">Z", diameter=6, through_all=True)
    assert r["holes"] == 1 and r["feature"]["type"] == "agujero" and r["face"].startswith("Cuerpo1/F")
    assert volumen(caja) == pytest.approx(8000 - math.pi * 9 * 20, abs=1e-2)
    assert llamar(caja, "find_faces", selector="%CYLINDER")["faces"][0]["radius"] == pytest.approx(3)


def test_agujero_ciego_con_dos_puntos_uv(caja):
    r = llamar(caja, "create_hole", face=">Z", diameter=6, depth=10, points=[[5, 5], [-5, -5]])
    assert r["holes"] == 2
    assert volumen(caja) == pytest.approx(8000 - 2 * math.pi * 9 * 10, abs=1e-2)
    centros = sorted(tuple(round(c, 3) for c in f["center"][:2]) for f in llamar(caja, "find_faces", selector="%CYLINDER")["faces"])
    assert centros == [(-5.0, -5.0), (5.0, 5.0)]


def test_agujero_con_punto_del_mundo_y_cara_lateral(caja):
    llamar(caja, "create_hole", face=">Z", diameter=4, depth=5, points=[[3, -4, 20]])           # [x, y, z] del mundo
    c = llamar(caja, "find_faces", selector="%CYLINDER")["faces"][0]["center"]
    assert c[0] == pytest.approx(3) and c[1] == pytest.approx(-4) and c[2] == pytest.approx(17.5)
    llamar(caja, "create_hole", face=">X", diameter=4, through_all=True, points=[[0, 10]])      # lateral: v hacia +Z
    assert any(abs(f["axis"][0]) == pytest.approx(1) for f in llamar(caja, "find_faces", selector="%CYLINDER")["faces"])


def test_agujero_abocardado_y_avellanado(caja):
    llamar(caja, "create_hole", face=">Z", diameter=6, depth=10, hole_type="counterbore",
           counterbore_diameter=10, counterbore_depth=3)
    esperado = 8000 - math.pi * 9 * 7 - math.pi * 25 * 3
    assert volumen(caja) == pytest.approx(esperado, abs=1e-2)
    llamar(caja, "undo")
    llamar(caja, "create_hole", face=">Z", diameter=6, depth=10, hole_type="countersink", countersink_diameter=12)
    assert 8000 - math.pi * 9 * 10 - 400 < volumen(caja) < 8000 - math.pi * 9 * 10


def test_agujero_errores(caja):
    antes = foto(caja)
    for args, kind in [({"face": ">Z", "diameter": 6}, "INVALID_ARGUMENTS"),                    # sin depth ni through_all
                       ({"face": "#Z", "diameter": 6, "through_all": True}, "AMBIGUOUS_REFERENCE"),
                       ({"face": "%CYLINDER", "diameter": 6, "through_all": True}, "NO_MATCH"),
                       ({"face": ">Z", "diameter": 0, "through_all": True}, "INVALID_ARGUMENTS"),
                       ({"face": ">Z", "diameter": 6, "depth": 5, "hole_type": "counterbore"}, "INVALID_ARGUMENTS"),
                       ({"face": ">Z", "diameter": 6, "depth": 5, "points": [[1, 2, 3, 4]]}, "INVALID_ARGUMENTS"),
                       ({"face": "edges:|Z", "diameter": 6, "through_all": True}, "INVALID_ARGUMENTS")]:
        assert falla(caja, "create_hole", **args)["error_kind"] == kind, args
        assert foto(caja) == antes, args


def test_agujero_en_cara_no_plana(s):
    llamar(s, "create_cylinder", radius=10, height=20)
    r = falla(s, "create_hole", face="%CYLINDER", diameter=3, through_all=True)
    assert r["error_kind"] == "UNSUPPORTED_ELEMENT"


def _cilindros(sesion):
    return sorted(tuple(round(c, 3) for c in f["center"]) for f in llamar(sesion, "find_faces", selector="%CYLINDER")["faces"])


def test_agujero_en_puntos_de_boceto_sigue_al_boceto(s):
    """Antes create_hole solo aceptaba coordenadas fijas: al cambiar una medida el agujero no seguía al boceto."""
    llamar(s, "create_parameter", name="px", expression="10 mm")
    llamar(s, "create_box", length=40, width=40, height=10)                          # x, y en ±20; z 0..10
    llamar(s, "create_sketch", plane="XY", name="Centros")
    linea = llamar(s, "draw_line", start_x=0, start_y=0, end_x=10, end_y=5, sketch="Centros")
    inicio, fin = linea["points"]
    llamar(s, "add_constraint", sketch="Centros", type="fix", entities=[inicio])
    llamar(s, "add_dimension", sketch="Centros", type="horizontal", entities=[linea["entities"][0]["id"]], value="px")
    llamar(s, "add_dimension", sketch="Centros", type="vertical", entities=[linea["entities"][0]["id"]], value=5)
    r = llamar(s, "create_hole", diameter=4, depth=5, sketch="Centros", sketch_points=[fin])
    assert r["holes"] == 1 and r["sketch_points"] == [fin] and r["direction"] == [0, 0, 1]   # boceto abajo: sube
    paso = r["feature"]["id"]
    assert s.paso(paso).p["posiciones"] == [{"tipo": "punto_boceto", "boceto": s.paso("Centros").id, "punto": fin}]
    assert volumen(s) == pytest.approx(16000 - math.pi * 4 * 5, abs=1e-3)
    assert _cilindros(s) == [(10.0, 5.0, 2.5)]
    llamar(s, "set_parameter", name="px", expression="15 mm")                       # el agujero sigue a la cota
    assert _cilindros(s) == [(15.0, 5.0, 2.5)]
    assert volumen(s) == pytest.approx(16000 - math.pi * 4 * 5, abs=1e-3)


def test_agujero_en_boceto_sobre_la_tapa_y_flip(caja):
    llamar(caja, "create_sketch", plane=">Z", name="Tapa")
    llamar(caja, "draw_circle", radius=1, center_x=3, center_y=4, sketch="Tapa")
    centro = llamar(caja, "get_sketch", sketch="Tapa")["entities"][0]["points"][0]
    r = llamar(caja, "create_hole", diameter=2, depth=4, sketch_points=[centro], face=">Z")   # último boceto
    assert r["direction"] == [0, 0, -1] and volumen(caja) == pytest.approx(8000 - math.pi * 4, abs=1e-3)
    llamar(caja, "undo")
    r = api.llamar(caja, "create_hole", {"diameter": 2, "depth": 4, "sketch": "Tapa", "sketch_points": [centro],
                                         "flip": True})
    assert r["ok"] and r["result"]["direction"] == [0, 0, 1]                        # hacia afuera: no corta nada
    assert volumen(caja) == pytest.approx(8000) and any("no cambió el volumen" in a for a in r["avisos"])


def test_agujero_en_boceto_errores(caja):
    llamar(caja, "create_sketch", plane=">Z", name="Tapa")
    llamar(caja, "draw_circle", radius=1, sketch="Tapa")
    centro = llamar(caja, "get_sketch", sketch="Tapa")["entities"][0]["points"][0]
    antes = foto(caja)
    for args, kind in [({"diameter": 2, "through_all": True}, "INVALID_ARGUMENTS"),                 # ni cara ni puntos
                       ({"diameter": 2, "through_all": True, "sketch": "Tapa"}, "INVALID_ARGUMENTS"),
                       ({"diameter": 2, "through_all": True, "sketch_points": [999]}, "ENTITY_NOT_FOUND"),
                       ({"diameter": 2, "through_all": True, "sketch": "nada", "sketch_points": [centro]},
                        "SKETCH_NOT_FOUND"),
                       ({"diameter": 2, "through_all": True, "face": ">Z", "points": [[1, 1]],
                         "sketch_points": [centro]}, "INVALID_ARGUMENTS"),
                       ({"diameter": 2, "sketch_points": [centro]}, "INVALID_ARGUMENTS")]:          # sin depth
        assert falla(caja, "create_hole", **args)["error_kind"] == kind, args
        assert foto(caja) == antes, args


def test_agujero_con_holgura_roscado_y_conico(caja):
    r = llamar(caja, "create_hole", face=">Z", hole_tap="clearance", thread="M8", through_all=True, points=[[-5, -5]])
    assert r["thread"] == "M8" and volumen(caja) == pytest.approx(8000 - math.pi * 4.5 ** 2 * 20, abs=1e-2)  # ISO 273
    llamar(caja, "undo")
    llamar(caja, "create_hole", face=">Z", hole_tap="clearance", thread="M8", fit="close", through_all=True)
    assert volumen(caja) == pytest.approx(8000 - math.pi * 4.2 ** 2 * 20, abs=1e-2)
    llamar(caja, "undo")
    r = llamar(caja, "create_hole", face=">Z", hole_tap="modeled", thread="M6", thread_class="6H", depth=6)
    assert r["thread"] == "M6x1" and 8000 - math.pi * 9 * 7 < volumen(caja) < 8000 - math.pi * 2.46 ** 2 * 6
    paso = llamar(caja, "get_timeline")["steps"][-1]["params"]
    assert (paso["rosca"], paso["designacion"], paso["clase_rosca"]) == ("modelada", "M6x1", "6H")
    llamar(caja, "undo")
    r = api.llamar(caja, "create_hole", {"face": ">Z", "hole_tap": "taper", "thread": "1/4 NPT", "depth": 10})
    assert r["ok"] and any("cónico" in a for a in r["avisos"])
    llamar(caja, "undo")
    llamar(caja, "create_hole", face=">Z", hole_tap="cosmetic", thread="M6", depth=6)          # Ø = broca de roscar
    assert volumen(caja) == pytest.approx(8000 - math.pi * 6.25 * 6, abs=1e-2)


def test_agujero_hasta_y_por_referencias(caja):
    llamar(caja, "create_hole", face=">Z", diameter=4, to="XY", to_offset=-2, points=[[5, 5]])   # z = 20 → z = 2
    assert volumen(caja) == pytest.approx(8000 - math.pi * 4 * 18, abs=1e-2)
    llamar(caja, "undo")
    llamar(caja, "create_hole", face=">Z", diameter=4, to="<Z", points=[[5, 5]])                  # hasta la cara de abajo
    assert volumen(caja) == pytest.approx(8000 - math.pi * 4 * 20, abs=1e-2)
    llamar(caja, "undo")
    r = llamar(caja, "create_hole", face=">Z", diameter=2, depth=3, reference_edges=["edges:>X and >Z", "edges:<Y and >Z"],
               reference_distances=[4, "3 mm"])
    assert r["holes"] == 1 and volumen(caja) == pytest.approx(8000 - math.pi * 3, abs=1e-2)
    c = llamar(caja, "find_faces", selector="%CYLINDER")["faces"][0]["center"]
    assert c[0] == pytest.approx(10 - 4) and c[1] == pytest.approx(-10 + 3)


def test_agujero_roscado_errores(caja):
    antes = foto(caja)
    for args in ({"face": ">Z", "hole_tap": "modeled", "depth": 5},                              # sin thread
                 {"face": ">Z", "hole_tap": "modeled", "thread": "M7", "depth": 5},              # rosca desconocida
                 {"face": ">Z", "hole_tap": "modeled", "thread": "M6", "thread_class": "6g", "depth": 5},  # de eje
                 {"face": ">Z", "hole_tap": "taper", "thread": "M6", "depth": 5},               # no es cónica
                 {"face": ">Z", "hole_tap": "clearance", "thread": "1/4-20", "depth": 5},       # ISO 273: solo M
                 {"face": ">Z", "depth": 5},                                                      # simple sin diámetro
                 {"face": ">Z", "diameter": 3, "depth": 5, "reference_edges": ["edges:>X and >Z"],
                  "reference_distances": [2]}):
        assert falla(caja, "create_hole", **args)["error_kind"] == "INVALID_ARGUMENTS", args
        assert foto(caja) == antes, args


def test_create_thread_exterior_con_clase_y_tamano_automatico(s):
    llamar(s, "create_cylinder", radius=5, height=12)
    r = llamar(s, "create_thread", faces="%CYLINDER", thread_class="6g", length=6)
    assert r["threads"] == [{"body": "Cuerpo1", "designation": "M10x1.5", "class": "6g", "internal": False,
                             "modeled": True}]
    assert r["faces_used"] == 1 and r["bodies_modified"][0]["volume"] < math.pi * 25 * 12
    llamar(s, "undo")
    r = llamar(s, "create_thread", faces="%CYLINDER", thread="M10x1.25", thread_class="", modeled=False)
    assert r["threads"][0]["class"] is None and volumen(s) == pytest.approx(math.pi * 25 * 12, abs=1e-2)
    for args, kind in (({"faces": ">Z"}, "UNSUPPORTED_ELEMENT"),
                       ({"faces": "%CYLINDER", "thread": "M10", "thread_class": "2A"}, "INVALID_ARGUMENTS"),
                       ({"faces": "%CYLINDER", "thread": "Tr99"}, "INVALID_ARGUMENTS")):
        assert falla(s, "create_thread", **args)["error_kind"] == kind, args


def test_create_thread_interior_trapezoidal(s):
    llamar(s, "create_box", length=40, width=40, height=12)
    llamar(s, "create_hole", face=">Z", diameter=16, through_all=True)
    v0 = volumen(s)
    r = llamar(s, "create_thread", faces="%CYLINDER", family="trapezoidal")
    assert r["threads"][0]["designation"] == "Tr20x4" and r["threads"][0]["internal"]
    assert v0 - volumen(s) == pytest.approx(0.5 * math.pi * (10 ** 2 - 8 ** 2) * 12, rel=0.03)


def test_thread_info_y_fit_tolerance(s):
    familias = {f["family"]: f for f in llamar(s, "thread_info")["families"]}
    assert set(familias) == {"iso_metric", "unified", "trapezoidal", "acme", "bsp_parallel", "bsp_taper", "npt"}
    assert familias["trapezoidal"]["profile_angle"] == 30 and familias["bsp_taper"]["taper"]
    tr = llamar(s, "thread_info", family="trapezoidal")["sizes"]
    assert tr[0] == {"size": "Tr8", "designations": ["Tr8x1.5"]}
    m10 = llamar(s, "thread_info", thread="M10", thread_class="6g")
    assert (m10["designation"], m10["pitch"], m10["tap_drill"]) == ("M10x1.5", 1.5, 8.5)
    assert m10["clearance_holes"] == {"close": 10.5, "normal": 11.0, "loose": 12.0}
    assert m10["limits"][0]["major_diameter"] == pytest.approx([9.732, 9.968])
    assert m10["limits"][0]["pitch_diameter"] == pytest.approx([8.862, 8.994], abs=6e-4)
    assert [x["class"] for x in llamar(s, "thread_info", thread="M10", thread_class="auto")["limits"]] == ["6H", "6g"]
    unc = llamar(s, "thread_info", thread="1/4-20", thread_class="2B")["limits"][0]
    assert [round(x / 25.4, 4) for x in unc["pitch_diameter"]] == [0.2175, 0.2224]
    f = llamar(s, "fit_tolerance", nominal=25, hole="H7", shaft="g6")
    assert f["fit_type"] == "clearance" and (f["max_clearance"], f["min_clearance"]) == pytest.approx((0.041, 0.007))
    assert f["hole"]["upper_deviation"] == pytest.approx(0.021) and f["shaft"]["lower_deviation"] == pytest.approx(-0.02)
    assert llamar(s, "fit_tolerance", nominal=25, hole="H7", shaft="p6")["fit_type"] == "interference"
    assert llamar(s, "fit_tolerance", nominal=25, hole="H7", shaft="k6")["fit_type"] == "transition"
    for args in ({"nominal": 600, "hole": "H7", "shaft": "g6"}, {"nominal": 25, "hole": "g6", "shaft": "H7"}):
        assert falla(s, "fit_tolerance", **args)["error_kind"] == "INVALID_ARGUMENTS"
    assert falla(s, "thread_info", thread="M7")["error_kind"] == "INVALID_ARGUMENTS"


# ---------------------------------------------------------------- desmoldeo
def test_draft_inclina_las_laterales(caja):
    r = llamar(caja, "draft", faces="#Z", angle=3, neutral="<Z")
    assert r["faces_used"] == 4 and r["feature"]["type"] == "desmoldeo"
    assert volumen(caja) < 8000 - 100
    bb = next(c["bounding_box"] for c in llamar(caja, "get_scene_info")["bodies"])
    assert bb["size"][2] == pytest.approx(20, abs=1e-3)


def test_draft_errores(caja):
    assert falla(caja, "draft", faces="#Z", angle=95)["error_kind"] == "INVALID_ARGUMENTS"
    assert falla(caja, "draft", faces="%CYLINDER", angle=3)["error_kind"] == "NO_MATCH"


# ---------------------------------------------------------------- boceto sobre una cara
def test_boceto_sobre_la_tapa_y_extruir_con_join(caja):
    r = llamar(caja, "create_sketch", plane=">Z")
    assert r["plane"] == "cara" and r["face"].startswith("Cuerpo1/F")
    f = r["plane_frame"]
    assert f["normal"] == [0.0, 0.0, 1.0] and f["u_axis"] == [1.0, 0.0, 0.0] and f["origin"] == [0.0, 0.0, 20.0]
    llamar(caja, "draw_circle", radius=5, center_x=0, center_y=0)
    r = llamar(caja, "extrude", sketch="Boceto1", distance=10, operation="join")
    assert caja_z(caja) == (0.0, 30.0)                                                      # sube la altura
    assert volumen(caja) == pytest.approx(8000 + math.pi * 25 * 10, abs=1e-2)
    assert r["bodies_modified"][0]["id"] == "op1.c1"


def test_boceto_sobre_la_tapa_cut_entra_al_material_como_fusion(caja):
    llamar(caja, "create_sketch", plane=">Z")
    llamar(caja, "draw_rectangle", center_x=0, center_y=0, width=10, height=10)
    llamar(caja, "extrude", sketch="Boceto1", distance=5, operation="cut")             # automático: hacia adentro
    assert volumen(caja) == pytest.approx(8000 - 10 * 10 * 5, abs=1e-3)
    llamar(caja, "undo")
    llamar(caja, "extrude", sketch="Boceto1", distance=5, operation="cut", reverse=False)  # forzado: sale del material
    assert volumen(caja) == pytest.approx(8000, abs=1e-6)


def test_boceto_sobre_cara_lateral_ejes(caja):
    f = llamar(caja, "create_sketch", plane="<Y")["plane_frame"]                            # cara frontal, normal −Y
    assert f["normal"] == [0.0, -1.0, 0.0] and f["v_axis"] == [0.0, 0.0, 1.0] and f["u_axis"] == [1.0, 0.0, 0.0]
    cu = llamar(caja, "find_faces", selector="<Y")["faces"][0]["center_uv"]
    assert cu == [0.0, 10.0]                                                                # centro de la cara en x,y del boceto
    llamar(caja, "draw_rectangle", x1=-2, y1=8, x2=2, y2=12)
    llamar(caja, "extrude", sketch="Boceto1", distance=5, operation="join")
    assert llamar(caja, "get_scene_info")["bodies"][0]["bounding_box"]["min"][1] == pytest.approx(-15)


def test_boceto_sobre_cara_por_id_y_plano_de_origen_sigue_andando(caja):
    cara = llamar(caja, "find_faces", selector=">Z")["faces"][0]["id"]
    assert llamar(caja, "create_sketch", plane=cara)["plane"] == "cara"
    assert llamar(caja, "create_sketch", plane="XY")["plane"] == "XY"
    assert llamar(caja, "create_sketch", plane="xz")["plane"] == "XZ"


def test_boceto_sobre_cara_errores(s):
    assert falla(s, "create_sketch", plane=">Z")["error_kind"] == "BODY_NOT_FOUND"          # sin cuerpos
    llamar(s, "create_cylinder", radius=10, height=20)
    antes = foto(s)
    assert falla(s, "create_sketch", plane="%CYLINDER")["error_kind"] == "UNSUPPORTED_ELEMENT"
    assert falla(s, "create_sketch", plane="%SPHERE")["error_kind"] == "NO_MATCH"
    assert falla(s, "create_sketch", plane="PlanoInventado")["error_kind"] == "PLANE_NOT_FOUND"
    assert foto(s) == antes


# ---------------------------------------------------------------- secuencia completa
def test_secuencia_caja_parametrica_fillet_shell_y_cambio(caja_param):
    s = caja_param
    llamar(s, "fillet", edges="|Z", radius=3)
    llamar(s, "shell", body="Cuerpo1", faces=">Z", thickness=2)
    v20 = volumen(s)
    # exterior: 8000 − 4·(9 − 9π/4)·20; cavidad: 16×16×18 con esquinas de radio 1 → 4608 − 4·(1 − π/4)·18
    esperado = (8000 - 4 * (9 - 9 * math.pi / 4) * 20) - (16 * 16 * 18 - 4 * (1 - math.pi / 4) * 18)
    assert v20 == pytest.approx(esperado, abs=1e-2)
    llamar(s, "set_parameter", name="lado", expression="30 mm")
    esperado30 = (27000 - 4 * (9 - 9 * math.pi / 4) * 30) - (26 * 26 * 28 - 4 * (1 - math.pi / 4) * 28)
    assert volumen(s) == pytest.approx(esperado30, abs=1e-2)
    assert len(llamar(s, "find_faces", selector="%CYLINDER")["faces"]) == 8                   # 4 exteriores + 4 interiores


def test_agujero_en_boceto_con_holgura_iso_273(caja):
    """Las dos ampliaciones de create_hole juntas: posición asociativa (sketch_points) + tipo de rosca (clearance)."""
    llamar(caja, "create_sketch", plane=">Z", name="Tapa")
    llamar(caja, "draw_circle", radius=1, center_x=3, center_y=4, sketch="Tapa")
    centro = llamar(caja, "get_sketch", sketch="Tapa")["entities"][0]["points"][0]
    r = llamar(caja, "create_hole", sketch="Tapa", sketch_points=[centro], hole_tap="clearance", thread="M8",
               through_all=True)
    assert r["thread"] == "M8" and r["direction"] == [0, 0, -1]
    assert volumen(caja) == pytest.approx(8000 - math.pi * 4.5 ** 2 * 20, abs=1e-2)          # M8 normal: Ø 9

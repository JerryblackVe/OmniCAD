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

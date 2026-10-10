# -*- coding: utf-8 -*-
"""Grupo "malla" de la API (MCP y CLI): una herramienta por operación del espacio MALLA, cada una con su resultado
numérico (triángulos, volumen, cerrada) y un solo paso de deshacer."""
import numpy as np
import pytest

from omnicad import api
from omnicad.nucleo import geometria as geo
from omnicad.nucleo import malla as ml

V_CUBO = np.array([[0, 0, 0], [10, 0, 0], [10, 10, 0], [0, 10, 0],
                   [0, 0, 10], [10, 0, 10], [10, 10, 10], [0, 10, 10]], float)
F_CUBO = np.array([[0, 2, 1], [0, 3, 2], [4, 5, 6], [4, 6, 7], [0, 1, 5], [0, 5, 4],
                   [1, 2, 6], [1, 6, 5], [2, 3, 7], [2, 7, 6], [3, 0, 4], [3, 4, 7]])
HERRAMIENTAS = {"get_mesh_info", "tessellate", "repair_mesh", "clean_mesh", "generate_face_groups", "reduce_mesh",
                "remesh", "smooth_mesh", "shell_mesh", "plane_cut_mesh", "combine_meshes", "separate_mesh",
                "reverse_mesh_normals", "scale_mesh", "convert_mesh"}


def ok(r):
    assert r["ok"], r
    return r["result"]


def llamar(s, nombre, **args):
    return ok(api.llamar(s, nombre, args))


def fallo(s, nombre, kind, **args):
    r = api.llamar(s, nombre, args)
    assert not r["ok"] and r["error_kind"] == kind, r
    return r


def malla_de_caja(s, lado=10, z=0, x=0):
    """Caja sólida teselada (sin conservar el sólido): id del cuerpo de malla."""
    cid = llamar(s, "create_box", length=lado, width=lado, height=lado, z=z, x=x)["bodies_created"][0]["id"]
    r = llamar(s, "tessellate", bodies=cid, keep_original=False)
    assert r["bodies_removed"] == [cid]
    return r["bodies_created"][0]["id"]


def insertar(s, tmp_path, m, nombre="pieza.stl"):
    ruta = tmp_path / nombre
    ml.escribir(m, ruta)
    return llamar(s, "insert_file", path=str(ruta))["new_bodies"][0]


@pytest.fixture
def s():
    return api.Sesion()


def test_el_grupo_tiene_una_herramienta_por_operacion():
    assert {h["nombre"] for h in api.catalogo("malla")} == HERRAMIENTAS
    modifican = {h["nombre"] for h in api.catalogo("malla") if h["modifica"]}
    assert modifican == HERRAMIENTAS - {"get_mesh_info"}


def test_teselar_e_info(s):
    m = malla_de_caja(s)
    info = llamar(s, "get_mesh_info", body=m)
    assert info["count"] == 1
    b = info["bodies"][0]
    assert (b["type"], b["triangles"], b["vertices"], b["face_groups"], b["shells"]) == ("mesh", 12, 8, 6, 1)
    assert b["closed"] and b["oriented"] and b["positive_volume"]
    assert (b["boundary_edges"], b["non_manifold_edges"], b["degenerate_triangles"]) == (0, 0, 0)
    assert b["volume"] == pytest.approx(1000) and b["area"] == pytest.approx(600)
    assert b["bounding_box"]["size"] == pytest.approx([10, 10, 10])
    assert llamar(s, "get_mesh_info")["count"] == 1                     # sin body: todas las mallas
    escena = llamar(s, "get_scene_info")
    assert [c["type"] for c in escena["bodies"]] == ["mesh"]


def test_teselar_conserva_el_solido_y_no_acepta_mallas(s):
    cid = llamar(s, "create_sphere", radius=10)["bodies_created"][0]["id"]
    r = llamar(s, "tessellate", bodies=[cid], refinement="high")
    assert r["bodies_removed"] == [] and r["feature"]["type"] == "teselar"
    malla = r["bodies_created"][0]
    assert malla["closed"] and malla["triangles"] > 500
    assert malla["volume"] == pytest.approx(4 / 3 * np.pi * 1000, rel=0.01)
    fallo(s, "tessellate", "UNSUPPORTED_BODY_TYPE", bodies=malla["id"])
    r = fallo(s, "remesh", "UNSUPPORTED_BODY_TYPE", bodies=cid)        # un sólido no es malla
    assert any("tessellate" in p for p in r["pistas"]) and any("insert_file" in p for p in r["pistas"])


def test_reparar_cierra_el_agujero_de_un_stl(s, tmp_path):
    m = insertar(s, tmp_path, ml.Malla(V_CUBO, F_CUBO[2:]))          # sin la tapa de abajo
    antes = llamar(s, "get_mesh_info", body=m)["bodies"][0]
    assert not antes["closed"] and antes["boundary_edges"] == 4 and antes["triangles"] == 10
    r = llamar(s, "repair_mesh", bodies=m)
    (b,) = r["bodies_modified"]
    assert b["before"]["triangles"] == 10 and not b["before"]["closed"]
    assert b["closed"] and b["triangles"] == 12 and b["volume"] == pytest.approx(1000)
    assert r["feature"]["type"] == "reparar_malla"


def test_limpiar_deja_una_malla_cerrada_y_es_editable(s, tmp_path):
    # Cubo sin tapa, con la mitad de las caras al revés, un vértice duplicado a 0,0001 mm y un triángulo suelto.
    v = np.vstack([V_CUBO, V_CUBO[5] + [1e-4, 0, 0], [[50, 0, 0], [51, 0, 0], [50, 1, 0]]])
    f = F_CUBO[2:].copy()
    f[f == 5] = np.where(np.arange(f.size).reshape(f.shape)[f == 5] % 2, 8, 5)
    f[::2] = f[::2][:, [0, 2, 1]]
    sucia = ml.Malla(v, np.vstack([f, [[9, 10, 11]]]))
    m = insertar(s, tmp_path, sucia, "sucia.ply")
    antes = llamar(s, "get_mesh_info", body=m)["bodies"][0]
    assert antes["shells"] == 2 and not antes["oriented"]
    r = llamar(s, "clean_mesh", bodies=m, fill_holes=True)
    (b,) = r["bodies_modified"]
    assert (b["triangles"], b["vertices"], b["shells"]) == (12, 8, 1)
    assert b["closed"] and b["oriented"] and b["volume"] == pytest.approx(1000)
    assert r["feature"]["type"] == "limpiar_malla"
    paso = r["feature"]["id"]
    # Sin rellenar huecos queda abierta: edit_feature cambia el paso guardado.
    llamar(s, "edit_feature", feature=paso, params={"rellenar": False})
    b = llamar(s, "get_mesh_info", body=m)["bodies"][0]
    assert b["triangles"] == 10 and b["boundary_edges"] == 4 and b["oriented"] and b["positive_volume"]
    # Distancia 0: el vértice duplicado no se une y la malla queda con un tajo.
    llamar(s, "edit_feature", feature=paso, params={"distancia": "0 mm", "rellenar": True})
    assert llamar(s, "get_mesh_info", body=m)["bodies"][0]["vertices"] == 9


def test_limpiar_valida_los_argumentos(s):
    m = malla_de_caja(s)
    fallo(s, "clean_mesh", "INVALID_ARGUMENTS", bodies=m, merge_by_distance=False, dissolve_degenerate=False,
          delete_loose=False, recalculate_normals=False)
    fallo(s, "clean_mesh", "INVALID_ARGUMENTS", bodies=m, distance=-1)
    fallo(s, "clean_mesh", "INVALID_ARGUMENTS", bodies=m, min_shell_fraction=1.5)
    fallo(s, "clean_mesh", "INVALID_ARGUMENTS", bodies=m, max_hole_sides=-2)
    fallo(s, "clean_mesh", "INVALID_ARGUMENTS", bodies=[])
    fallo(s, "clean_mesh", "BODY_NOT_FOUND", bodies="no_existe")
    assert len(s.doc.operaciones) == 2                                   # nada de lo anterior dejó pasos


def test_grupos_reducir_y_separar_por_grupos(s, tmp_path):
    m = insertar(s, tmp_path, ml.Malla(V_CUBO, F_CUBO))                 # el STL no trae grupos: uno solo
    assert llamar(s, "get_mesh_info", body=m)["bodies"][0]["face_groups"] == 1
    assert llamar(s, "generate_face_groups", bodies=m, angle=30)["bodies_modified"][0]["face_groups"] == 6
    r = llamar(s, "separate_mesh", bodies=m, by="face_groups")
    assert len(r["bodies_created"]) == 5 and r["bodies_modified"][0]["triangles"] == 2
    assert sum(c["area"] for c in r["bodies_created"] + r["bodies_modified"]) == pytest.approx(600)
    fallo(s, "generate_face_groups", "INVALID_ARGUMENTS", bodies=m, angle=200)


def test_reducir_y_remallar(s):
    cid = llamar(s, "create_sphere", radius=10)["bodies_created"][0]["id"]
    m = llamar(s, "tessellate", bodies=cid, keep_original=False, refinement="low")["bodies_created"][0]
    assert m["triangles"] > 1000                                         # remallarla tarda ~1,5 s
    r = llamar(s, "remesh", bodies=m["id"], density=1.5)["bodies_modified"][0]
    assert r["triangles"] > r["before"]["triangles"] and r["closed"]
    assert r["volume"] == pytest.approx(m["volume"], rel=0.01)
    r = llamar(s, "reduce_mesh", bodies=m["id"], proportion=0.5)["bodies_modified"][0]
    assert r["triangles"] == pytest.approx(r["before"]["triangles"] / 2, rel=0.02) and r["closed"]
    assert r["volume"] == pytest.approx(m["volume"], rel=0.01)
    r = llamar(s, "reduce_mesh", bodies=m["id"], mode="face_count", face_count=200)["bodies_modified"][0]
    assert r["triangles"] <= 210 and r["closed"]
    fallo(s, "remesh", "INVALID_ARGUMENTS", bodies=m["id"], density=0)
    fallo(s, "reduce_mesh", "INVALID_ARGUMENTS", bodies=m["id"], proportion=1.5)
    fallo(s, "reduce_mesh", "INVALID_ARGUMENTS", bodies=m["id"], mode="face_count", face_count=2)


def test_suavizar_vaciar_e_invertir(s):
    cid = llamar(s, "create_sphere", radius=10)["bodies_created"][0]["id"]
    esfera = llamar(s, "tessellate", bodies=cid, keep_original=False)["bodies_created"][0]
    r = llamar(s, "smooth_mesh", bodies=esfera["id"], strength=0.5, iterations=5)["bodies_modified"][0]
    assert r["triangles"] == esfera["triangles"] and r["volume"] == pytest.approx(esfera["volume"], rel=0.01)
    caja = malla_de_caja(s, lado=20, x=50)
    r = llamar(s, "shell_mesh", bodies=caja, thickness=2)["bodies_modified"][0]
    assert r["shells"] == 2 and r["triangles"] == 24 and r["closed"]
    assert r["volume"] == pytest.approx(20 ** 3 - 16 ** 3)
    r = llamar(s, "reverse_mesh_normals", bodies=caja)["bodies_modified"][0]
    assert r["volume"] == pytest.approx(-(20 ** 3 - 16 ** 3)) and not r["positive_volume"]
    fallo(s, "shell_mesh", "INVALID_ARGUMENTS", bodies=caja, thickness=0)
    fallo(s, "smooth_mesh", "INVALID_ARGUMENTS", bodies=caja, strength=2)


def test_cortar_con_plano(s):
    m = malla_de_caja(s, z=-5)                                           # de z=-5 a z=5: XY la parte al medio
    r = llamar(s, "plane_cut_mesh", bodies=m, plane="XY")
    b = r["bodies_modified"][0]
    assert b["closed"] and b["volume"] == pytest.approx(500)
    assert b["bounding_box"]["min"][2] == pytest.approx(0) and b["bounding_box"]["max"][2] == pytest.approx(5)
    assert r["kept_side_normal"] == [0, 0, 1] and r["plane"]["normal"] == [0, 0, 1]
    llamar(s, "undo")
    r = llamar(s, "plane_cut_mesh", bodies=m, plane="XY", kind="split_body", flip=True)
    assert len(r["bodies_created"]) == 1 and r["kept_side_normal"] == [0, 0, -1]
    assert r["bodies_modified"][0]["bounding_box"]["max"][2] == pytest.approx(0)
    vols = sorted(c["volume"] for c in r["bodies_created"] + r["bodies_modified"])
    assert vols == pytest.approx([500, 500])
    fallo(s, "plane_cut_mesh", "PLANE_NOT_FOUND", bodies=m, plane="ZZ")


def test_combinar_separar_escalar_y_convertir(s):
    a = malla_de_caja(s)
    b = malla_de_caja(s, x=5)                                            # se superpone a la mitad
    r = llamar(s, "combine_meshes", target=a, tools=b, operation="join")
    assert r["bodies_removed"] == [b] and r["bodies_modified"][0]["volume"] == pytest.approx(1500, rel=1e-6)
    fallo(s, "combine_meshes", "INVALID_ARGUMENTS", target=a, tools=[a])
    lejos = malla_de_caja(s, x=100)
    r = llamar(s, "combine_meshes", target=a, tools=[lejos], operation="merge")
    assert r["bodies_modified"][0]["shells"] == 2
    r = llamar(s, "separate_mesh", bodies=a)
    assert len(r["bodies_created"]) == 1
    nuevo = r["bodies_created"][0]["id"]
    assert sorted([r["bodies_created"][0]["volume"], r["bodies_modified"][0]["volume"]]) == pytest.approx([1000, 1500])
    r = llamar(s, "scale_mesh", bodies=nuevo, factor_x=2)["bodies_modified"][0]
    assert r["volume"] == pytest.approx(8000) and r["bounding_box"]["size"] == pytest.approx([20, 20, 20])
    r = llamar(s, "scale_mesh", bodies=nuevo, factor_x=-1, factor_y=1, factor_z=1)["bodies_modified"][0]
    assert r["volume"] == pytest.approx(8000)                           # espejar no da vuelta las normales
    fallo(s, "scale_mesh", "INVALID_ARGUMENTS", bodies=nuevo, factor_x=0)
    r = llamar(s, "convert_mesh", bodies=nuevo)
    (solido,) = r["bodies_created"]
    assert r["bodies_removed"] == [nuevo] and solido["type"] == "solid" and solido["valid"]
    assert solido["volume"] == pytest.approx(8000)
    assert geo.es_valida(s.cuerpo(solido["id"]).forma)


def test_cada_herramienta_es_un_paso_de_deshacer(s):
    m = malla_de_caja(s)
    pasos = len(s.doc.operaciones)
    llamar(s, "clean_mesh", bodies=m)
    llamar(s, "scale_mesh", bodies=m, factor_x="2")
    assert len(s.doc.operaciones) == pasos + 2
    llamar(s, "undo")
    assert llamar(s, "get_mesh_info", body=m)["bodies"][0]["volume"] == pytest.approx(1000)
    llamar(s, "undo")
    assert len(s.doc.operaciones) == pasos


def test_nombre_del_paso(s):
    m = malla_de_caja(s)
    r = llamar(s, "repair_mesh", bodies=m, name="Arreglo")
    assert r["feature"]["name"] == "Arreglo"
    fallo(s, "repair_mesh", "INVALID_ARGUMENTS", bodies=m, name="Arreglo")     # no se repite

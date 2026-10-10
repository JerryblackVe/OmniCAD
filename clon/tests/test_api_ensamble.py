# -*- coding: utf-8 -*-
"""Herramientas del grupo "ensamble" (api/herramientas_ensamble.py): componentes, fijar, uniones (con caras por
selector o id), unión como está, origen de unión, accionar, límites, grupos rígidos, vínculos y estudio de
movimiento. Posiciones verificadas con la caja envolvente y la traslación de cada componente."""
import json
import math

import pytest

from omnicad import api
from omnicad.nucleo import geometria as g


def ok(r):
    assert r["ok"], r
    return r["result"]


def llamar(s, nombre, **args):
    return ok(api.llamar(s, nombre, args))


def falla(s, nombre, kind, **args):
    receta = json.dumps(s.doc.a_dict(), sort_keys=True)
    r = api.llamar(s, nombre, args)
    assert not r["ok"] and r["error_kind"] == kind, r
    assert json.dumps(s.doc.a_dict(), sort_keys=True) == receta          # atómica: el documento no cambió
    return r


def caja(s, cid):
    return [round(v, 4) + 0.0 for p in g.caja_envolvente(s.cuerpo(cid).forma) for v in p]


def dos_cajas(fija=True):
    """Base 40×40×10 centrada en el origen (componente «Base») y un bloque 10×10×10 en (100, 50) («Bloque»)."""
    s = api.Sesion()
    base = llamar(s, "create_box", length=40, width=40, height=10)["bodies_created"][0]["id"]
    bloque = llamar(s, "create_box", length=10, width=10, height=10, x=100, y=50)["bodies_created"][0]["id"]
    llamar(s, "create_component", bodies=[base], name="Base", grounded=fija)
    llamar(s, "create_component", bodies=[bloque], name="Bloque")
    return s, base, bloque


# ---------------------------------------------------------------- componentes y unión rígida
def test_componentes_union_rigida_y_get_assembly():
    s, base, bloque = dos_cajas()
    r = llamar(s, "create_joint", origin1="<Z", body1=bloque, origin2=">Z", body2="Base")
    assert r["joint"] == dict(r["joint"], type="rigid", status="ok", component1={"id": "op4", "name": "Bloque"},
                              component2={"id": "op3", "name": "Base"}, values={}, limits=None)
    (movido,) = r["moved_components"]
    assert movido["id"] == "op4" and movido["translation"] == [-100, -50, 10]
    assert caja(s, bloque) == [-5, -5, 10, 5, 5, 20]                # apoyado en el centro de la cara de arriba
    a = llamar(s, "get_assembly")
    assert [(c["id"], c["name"], c["grounded"]) for c in a["components"]] == [("op3", "Base", True),
                                                                             ("op4", "Bloque", False)]
    assert a["components"][1]["bodies"] == [{"id": bloque, "name": "Cuerpo2"}]
    assert [j["id"] for j in a["joints"]] == ["op5"] and a["root_bodies"] == []
    # Una caja nueva queda en la raíz y se informa así.
    suelta = llamar(s, "create_box", length=5, width=5, height=5, x=-100)["bodies_created"][0]["id"]
    assert llamar(s, "get_assembly")["root_bodies"] == [{"id": suelta, "name": "Cuerpo3"}]


def test_errores_de_componentes_y_uniones():
    s, base, bloque = dos_cajas()
    r = falla(s, "create_joint", "INVALID_ARGUMENTS", origin1=">Z", body1=base, origin2="<Z", body2=bloque)
    assert "fijo" in r["mensaje"]
    falla(s, "create_joint", "INVALID_ARGUMENTS", origin1="<Z", body1=bloque, origin2=">Z", body2=bloque)
    r = falla(s, "create_joint", "INVALID_ARGUMENTS", origin1="<Z", body1=bloque, origin2=">Z", body2=base,
              joint_type="rigid", rotation=30)
    assert "rigid" in r["mensaje"]
    suelta = llamar(s, "create_box", length=5, width=5, height=5, x=-100)["bodies_created"][0]["id"]
    r = falla(s, "create_joint", "INVALID_ARGUMENTS", origin1="<Z", body1=suelta, origin2=">Z", body2=base)
    assert "raíz" in r["mensaje"] and "create_component" in " ".join(r["pistas"])
    r = falla(s, "create_rigid_group", "COMPONENT_NOT_FOUND", components=["Bloque", "Nada"])
    assert "Base (op3)" in r["mensaje"] and "Bloque (op4)" in r["mensaje"]
    r = falla(s, "create_rigid_group", "INVALID_ARGUMENTS", components=["Bloque", bloque])     # el mismo dos veces
    assert "Componentes: Base (op3), Bloque (op4)" in r["mensaje"]
    r = falla(s, "drive_joint", "JOINT_NOT_FOUND", joint="op4", rotation=10)
    assert "es de tipo componente" in r["mensaje"]
    falla(s, "create_component", "INVALID_ARGUMENTS", bodies=[base], name="Base")             # nombre repetido
    r = api.llamar(s, "create_component", {"bodies": [bloque], "name": "Otro"})
    assert r["ok"] and "pasa del componente «Bloque»" in r["avisos"][0]


def test_fijar_componente_y_union_como_esta_sigue_al_componente_2():
    s, base, bloque = dos_cajas(fija=False)
    llamar(s, "ground_component", component="Bloque")
    assert llamar(s, "get_assembly")["components"][1]["grounded"] is True
    falla(s, "create_joint", "INVALID_ARGUMENTS", origin1="<Z", body1=bloque, origin2=">Z", body2=base)
    llamar(s, "ground_component", component=bloque, grounded=False)
    # La base sube 5 mm (unión rígida contra un suelo de la raíz) y después el bloque se liga «como está»: la sigue.
    suelo = llamar(s, "create_box", length=200, width=200, height=5, z=-5)["bodies_created"][0]["id"]
    llamar(s, "create_joint", origin1="<Z", body1=base, origin2=">Z", body2=suelo, offset=[0, 0, 5])
    assert caja(s, base) == pytest.approx([-20, -20, 5, 20, 20, 15])      # dz = +5 sobre la normal del suelo
    r = llamar(s, "create_as_built_joint", origin=">Z", body=bloque, component2="Base", joint_type="revolute",
               rotation=90)
    assert r["joint"]["as_built"] and r["joint"]["component2"]["name"] == "Base"
    assert caja(s, bloque) == pytest.approx([95, 45, 5, 105, 55, 15])   # siguió a la base y giró en su lugar
    falla(s, "create_as_built_joint", "INVALID_ARGUMENTS", origin=">Z", body=bloque, component2="Bloque")


# ---------------------------------------------------------------- revolución: accionar, límites, perno
def test_union_de_revolucion_accionar_limites_y_deshacer():
    s, base, bloque = dos_cajas()
    r = llamar(s, "create_joint", origin1="<Z", body1=bloque, origin2=">Z", body2=base, joint_type="revolute",
               rotation=30)
    medio = 5 * (math.cos(math.radians(30)) + math.sin(math.radians(30)))      # 6,830: caja de un cuadrado girado
    assert caja(s, bloque) == pytest.approx([-medio, -medio, 10, medio, medio, 20], abs=1e-4)
    assert r["joint"]["values"] == {"rotation": 30} and r["joint"]["limits"]["motion"] == "rotation"
    r = llamar(s, "drive_joint", joint="Unión1", rotation=90)
    assert r["joint"]["values"] == {"rotation": 90}
    assert r["moved_components"][0]["rotation_matrix"] == [[0, -1, 0], [1, 0, 0], [0, 0, 1]]
    assert caja(s, bloque) == pytest.approx([-5, -5, 10, 5, 5, 20], abs=1e-6)
    falla(s, "drive_joint", "INVALID_ARGUMENTS", joint="Unión1", slide=5)
    falla(s, "drive_joint", "INVALID_ARGUMENTS", joint="Unión1")
    r = api.llamar(s, "set_joint_limits", {"joint": "op5", "maximum": 45})
    assert r["ok"] and "límite máximo (45°)" in r["avisos"][0] and r["result"]["joint"]["values"] == {"rotation": 45}
    assert r["result"]["joint"]["limits"] == {"motion": "rotation", "minimum": None, "maximum": "45.0"}
    falla(s, "set_joint_limits", "INVALID_ARGUMENTS", joint="op5", minimum=50, maximum=10)
    r = llamar(s, "set_joint_limits", joint="op5")                   # sin límites: vuelve a 90°
    assert r["joint"]["values"] == {"rotation": 90} and r["joint"]["limits"]["maximum"] is None
    llamar(s, "undo")
    assert llamar(s, "get_assembly")["joints"][0]["values"] == {"rotation": 45}


def _perno_y_placa():
    """Placa 40×40×10 fija con un agujero Ø10 en el centro y un perno Ø10×20 en x = 100."""
    s = api.Sesion()
    placa = llamar(s, "create_box", length=40, width=40, height=10)["bodies_created"][0]["id"]
    llamar(s, "create_cylinder", radius=5, height=10, operation="cut", target=placa)
    perno = llamar(s, "create_cylinder", radius=5, height=20, x=100)["bodies_created"][0]["id"]
    llamar(s, "create_component", bodies=[placa], name="Placa", grounded=True)
    llamar(s, "create_component", bodies=[perno], name="Perno")
    return s, placa, perno


def test_perno_en_agujero_con_ids_de_find_faces_y_con_origen_de_union():
    s, placa, perno = _perno_y_placa()
    agujero = llamar(s, "find_faces", body=placa, selector="%CYLINDER")["faces"][0]["id"]       # «Cuerpo1/F7»
    r = llamar(s, "create_joint", origin1="%CYLINDER", body1=perno, origin2=agujero, joint_type="revolute")
    (m,) = r["moved_components"]
    assert m["translation"] == [-100, 0, -5] and m["rotation_matrix"] == [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
    assert caja(s, perno) == pytest.approx([-5, -5, -5, 5, 5, 15], abs=1e-6)   # el medio del perno en el del agujero
    # Lo mismo contra un origen de unión puesto sobre el agujero (un marco de eje).
    s, placa, perno = _perno_y_placa()
    o = llamar(s, "create_joint_origin", geometry="%CYLINDER", body=placa, name="Eje agujero")
    assert o["joint_origin"]["origin"] == [0, 0, 5] and o["joint_origin"]["z_axis"] == [0, 0, 1]
    r = llamar(s, "create_joint", origin1="%CYLINDER", body1=perno, origin2="Eje agujero", joint_type="revolute")
    assert r["moved_components"][0]["translation"] == [-100, 0, -5]
    assert llamar(s, "get_assembly")["joint_origins"][0]["name"] == "Eje agujero"
    falla(s, "create_joint", "INVALID_ARGUMENTS", origin1="%CYLINDER", body1=perno, origin2="no es nada")


# ---------------------------------------------------------------- mecanismo: vínculo y grupo rígido
def _mecanismo():
    """Base 100×100×10 fija, manivela de revolución a 60° y pistón deslizante a 50 mm sobre X."""
    s = api.Sesion()
    base = llamar(s, "create_box", length=100, width=100, height=10)["bodies_created"][0]["id"]
    manivela = llamar(s, "create_box", length=10, width=10, height=10, x=200)["bodies_created"][0]["id"]
    piston = llamar(s, "create_box", length=10, width=10, height=10, x=300)["bodies_created"][0]["id"]
    llamar(s, "create_component", bodies=[base], name="Base", grounded=True)
    llamar(s, "create_component", bodies=[manivela], name="Manivela")
    llamar(s, "create_component", bodies=[piston], name="Piston")
    llamar(s, "create_joint", origin1="<Z", body1=manivela, origin2=">Z", body2=base, joint_type="revolute",
           rotation=60, name="J1")
    llamar(s, "create_joint", origin1="<Z", body1=piston, origin2=">Z", body2=base, joint_type="slider",
           slide_axis="X", slide=50, name="J2")
    return s, base, manivela, piston


def test_vinculo_de_movimiento_y_grupo_rigido():
    s, base, manivela, piston = _mecanismo()
    assert caja(s, piston)[0] == pytest.approx(45)                    # −5 + 50
    r = llamar(s, "create_motion_link", joint1="J1", joint2="J2", ratio=0.2)
    assert r["joint2"]["values"] == {"slide": 12} and r["joint2"]["driven_by_links"] == [r["feature"]["id"]]
    assert caja(s, piston)[0] == pytest.approx(7)                     # −5 + 0,2·60
    r = api.llamar(s, "drive_joint", {"joint": "J1", "rotation": 90})
    assert r["ok"] and caja(s, piston)[0] == pytest.approx(13)        # el pistón sigue a la manivela
    r = api.llamar(s, "drive_joint", {"joint": "J2", "slide": 30})
    assert r["ok"] and "vínculo" in r["avisos"][0]
    falla(s, "create_motion_link", "INVALID_ARGUMENTS", joint1="J1", joint2="j1")
    a = llamar(s, "get_assembly")
    assert a["motion_links"][0] == dict(a["motion_links"][0], joint1="op7", joint2="op8", ratio="0.2", reverse=False)
    r = llamar(s, "create_rigid_group", components=["manivela", piston])    # por nombre y por un cuerpo
    assert [c["name"] for c in r["rigid_group"]["components"]] == ["Manivela", "Piston"]
    assert llamar(s, "get_assembly")["rigid_groups"][0]["components"] == ["op5", "op6"]


# ---------------------------------------------------------------- estudio de movimiento
def test_estudio_de_movimiento_encuentra_el_choque_y_no_cambia_el_documento():
    s, base, bloque = dos_cajas()
    llamar(s, "create_joint", origin1="<Z", body1=bloque, origin2=">Z", body2=base, joint_type="revolute",
           offset=[15, 0, 0])
    assert caja(s, bloque) == pytest.approx([10, -5, 10, 20, 5, 20], abs=1e-6)
    llamar(s, "create_box", length=6, width=6, height=6, x=0, y=15, z=10)        # obstáculo en la raíz
    receta = json.dumps(s.doc.a_dict(), sort_keys=True)
    r = llamar(s, "motion_study", joint="Unión1", values=[0, 90, 180], check_interference=True)
    assert json.dumps(s.doc.a_dict(), sort_keys=True) == receta and r["document_changed"] is False
    assert [p["value"] for p in r["steps"]] == [0, 90, 180] and r["unit"] == "deg"
    centros = [(b["min"][i] + b["max"][i]) / 2 for b in (p["components"][0]["bounding_box"] for p in r["steps"])
               for i in range(2)]
    assert centros == pytest.approx([15, 0, 0, 15, -15, 0], abs=1e-6)
    assert r["collision_values"] == [90]
    assert r["steps"][1]["interference"][0]["volume"] == pytest.approx(216)          # el obstáculo entero
    r = llamar(s, "motion_study", joint="Unión1", steps=5)
    assert [p["value"] for p in r["steps"]] == [0, 90, 180, 270, 360]
    falla(s, "motion_study", "INVALID_ARGUMENTS", joint="Unión1", motion="slide")
    falla(s, "motion_study", "INVALID_ARGUMENTS", joint="Unión1", steps=1)

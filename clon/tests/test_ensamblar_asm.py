# -*- coding: utf-8 -*-
"""ENSAMBLAR igual a Fusion (ASM-6 a ASM-8 y ASM-10 a ASM-15): nan e inf, componente vacío, vínculo con unión suprimida,
modos de posición, ejes propios, límites por movimiento, vínculo por grado de libertad, estudio de movimiento y
Anclar / posición inicial / Capturar y Revertir. Todo con números: posiciones, ángulos y valores."""
import json
import math

import numpy as np
import pytest

from omnicad import api
from omnicad.nucleo import geometria as g
from omnicad.timeline.operaciones import ErrorOperacion
from omnicad.timeline.ops_ensamblar import (OpUnion, exigir_numero, movimiento, poses_de_estudio, valores_de_estudio)


def llamar(s, nombre, **args):
    r = api.llamar(s, nombre, args)
    assert r["ok"], r
    return r["result"]


def falla(s, nombre, kind, **args):
    receta = json.dumps(s.doc.a_dict(), sort_keys=True)
    r = api.llamar(s, nombre, args)
    assert not r["ok"] and r["error_kind"] == kind, r
    assert json.dumps(s.doc.a_dict(), sort_keys=True) == receta          # atómica: el documento no cambió
    return r


def caja(s, cid):
    return [round(v, 4) + 0.0 for p in g.caja_envolvente(s.cuerpo(cid).forma) for v in p]


def centro(s, cid):
    c = caja(s, cid)
    return [(c[i] + c[i + 3]) / 2 for i in range(3)]


def _mecanismo():
    """Base 100×100×10 fija, manivela de revolución a 60° (J1) y pistón deslizante a 50 mm sobre X (J2)."""
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


# ---------------------------------------------------------------- ASM-6, ASM-7 y ASM-8
@pytest.mark.parametrize("texto", ["nan", "NaN", "inf", "-inf", "+Infinity"])
def test_asm6_nan_e_inf_dicen_que_no_son_un_numero(texto):
    s, *_ = _mecanismo()
    r = falla(s, "drive_joint", "INVALID_ARGUMENTS", joint="J1", rotation=texto)
    assert "No es un número" in r["mensaje"] and "Nombre desconocido" not in r["mensaje"]
    r = falla(s, "create_joint", "INVALID_ARGUMENTS", origin1="<Z", body1="op3.c1", origin2=">Z", body2="op2.c1",
              joint_type="slider", slide=texto)
    assert "No es un número" in r["mensaje"]


def test_asm6_un_valor_float_nan_y_el_paso_de_una_receta_vieja_tambien():
    s, *_ = _mecanismo()
    r = falla(s, "drive_joint", "INVALID_ARGUMENTS", joint="J1", rotation=float("nan"))
    assert "'rotation' no es un número válido" in r["mensaje"]        # T-23: lo dice el registro, antes de la herramienta
    with pytest.raises(ErrorOperacion, match="No es un número"):
        exigir_numero(" -Inf ")
    exigir_numero("inferior")           # un parámetro que empieza con «inf» sigue siendo un nombre
    exigir_numero("30 deg")
    exigir_numero(None)
    from omnicad.ui.comando import ErrorComando
    from omnicad.ui.comandos.ensamblar import _numero
    with pytest.raises(ErrorComando, match="No es un número"):
        _numero("nan")


def test_asm7_mover_el_unico_cuerpo_de_un_componente_avisa_que_queda_vacio():
    s = api.Sesion()
    cuerpo = llamar(s, "create_box", length=10, width=10, height=10)["bodies_created"][0]["id"]
    otro = llamar(s, "create_box", length=10, width=10, height=10, x=50)["bodies_created"][0]["id"]
    llamar(s, "create_component", bodies=[cuerpo], name="Base", grounded=True)
    llamar(s, "create_component", bodies=[otro], name="Otro")
    r = api.llamar(s, "create_component", {"bodies": [cuerpo], "name": "Nuevo"})
    assert r["ok"] and any("«Base» quedó sin cuerpos (estaba fijo)" in a for a in r["avisos"]), r["avisos"]
    # si le quedan cuerpos, no avisa
    s2 = api.Sesion()
    a = llamar(s2, "create_box", length=10, width=10, height=10)["bodies_created"][0]["id"]
    b = llamar(s2, "create_box", length=10, width=10, height=10, x=50)["bodies_created"][0]["id"]
    llamar(s2, "create_component", bodies=[a, b], name="Par")
    r = api.llamar(s2, "create_component", {"bodies": [a], "name": "Solo"})
    assert r["ok"] and not any("sin cuerpos" in x for x in r["avisos"])


def test_asm8_suprimir_una_union_usada_por_un_vinculo_dice_cual_falta():
    s, *_ = _mecanismo()
    llamar(s, "create_motion_link", joint1="J1", joint2="J2", ratio=0.2, name="V")
    r = api.llamar(s, "suppress_feature", {"feature": "J1"})          # J1 es op7 y J2 es op8
    assert not r["ok"] and r["error_kind"] == "OPERATION_FAILED"
    assert "unión «op7»" in r["mensaje"] and "suprimida" in r["mensaje"]
    assert "«op8»" not in r["mensaje"]                                # la otra unión sí existe: no se la culpa


# ---------------------------------------------------------------- ASM-10: modos de posición
def _caja_20x20x30(s):
    return llamar(s, "create_box", length=20, width=20, height=30)["bodies_created"][0]["id"]


def test_asm10_entre_dos_caras_centra_el_origen_a_medio_camino():
    s = api.Sesion()
    c = _caja_20x20x30(s)                                # x ±10, y ±10, z de 0 a 30
    r = llamar(s, "create_joint_origin", geometry=">Z", geometry_b="<Z", mode="between_faces", body=c)
    o = r["joint_origin"]
    assert o["origin"] == pytest.approx([0, 0, 15], abs=1e-6) and o["z_axis"] == pytest.approx([0, 0, 1], abs=1e-6)
    # dos caras no paralelas, o sin la segunda: error claro y el documento no cambia
    falla(s, "create_joint_origin", "INVALID_ARGUMENTS", geometry=">Z", mode="between_faces", body=c)
    r = falla(s, "create_joint_origin", "OPERATION_FAILED", geometry=">Z", geometry_b=">X", mode="between_faces",
              body=c)
    assert "paralelas" in r["mensaje"]
    falla(s, "create_joint_origin", "INVALID_ARGUMENTS", geometry=">Z", geometry_b="<Z", body=c)    # modo simple


def test_asm10_interseccion_de_dos_aristas_extendidas():
    s = api.Sesion()
    c = _caja_20x20x30(s)
    e = {(tuple(x["center"]), tuple(x["direction"])): x["id"]
         for x in llamar(s, "find_edges", body=c, selector=">Z")["edges"]}
    sobre_x = e[((0.0, 10.0, 30.0), (1.0, 0.0, 0.0))]                  # el borde de arriba a y = 10, paralelo a X
    sobre_y = e[((10.0, 0.0, 30.0), (0.0, 1.0, 0.0))]                  # el de x = 10, paralelo a Y
    r = llamar(s, "create_joint_origin", geometry=sobre_x, geometry_b=sobre_y, mode="edge_intersection")
    o = r["joint_origin"]
    assert o["origin"] == pytest.approx([10, 10, 30], abs=1e-6)
    assert o["x_axis"] == pytest.approx([1, 0, 0], abs=1e-6) and o["z_axis"] == pytest.approx([0, 0, 1], abs=1e-6)
    e = {(tuple(x["center"]), tuple(x["direction"])): x["id"]           # los ids valen hasta el próximo cambio
         for x in llamar(s, "find_edges", body=c, selector=">Z")["edges"]}
    r = falla(s, "create_joint_origin", "OPERATION_FAILED", geometry=e[((0.0, 10.0, 30.0), (1.0, 0.0, 0.0))],
              geometry_b=e[((0.0, -10.0, 30.0), (1.0, 0.0, 0.0))], mode="edge_intersection")
    assert "paralelas" in r["mensaje"]


def test_asm10_la_union_usa_los_modos_y_la_receta_los_guarda():
    s = api.Sesion()
    base = _caja_20x20x30(s)                             # componente fijo
    bloque = llamar(s, "create_box", length=4, width=4, height=4, x=100)["bodies_created"][0]["id"]
    llamar(s, "create_component", bodies=[base], name="Base", grounded=True)
    llamar(s, "create_component", bodies=[bloque], name="Bloque")
    # la cara de abajo del bloque va al medio de la altura de la base (entre su tapa y su fondo): z = 15
    r = llamar(s, "create_joint", origin1="<Z", body1=bloque, origin2=">Z", origin2b="<Z", mode2="between_faces",
               body2=base, name="U")
    assert caja(s, bloque) == pytest.approx([-2, -2, 15, 2, 2, 19], abs=1e-4)
    assert r["joint"]["mode2"] == "between_faces" and r["joint"]["mode1"] == "simple"
    op = s.doc.operacion(r["joint"]["id"])
    assert op.p["modo2"] == "entre_caras" and op.p["origen2b"]
    # sin la segunda selección el modo no se puede pedir; y una receta vieja (sin modo) sigue siendo «simple»
    falla(s, "create_joint", "INVALID_ARGUMENTS", origin1="<Z", body1=bloque, origin2=">Z", body2=base, mode2="between_faces")
    vieja = OpUnion("opx", "U", tipo="rigida")
    assert vieja.p["modo1"] == "simple" and vieja.p["origen1b"] is None


# ---------------------------------------------------------------- ASM-11: ejes propios
def test_asm11_movimiento_con_eje_propio_gira_alrededor_de_el():
    eje = ([1.0, 0.0, 0.0], [0.0, 0.0, 1.0])            # paralelo a Z por (1, 0, 0), en el marco de la unión
    m = movimiento("revolucion", {"giro": 90.0}, eje, "X")
    assert (m @ [2.0, 0, 0, 1])[:3] == pytest.approx([1, 1, 0], abs=1e-9)
    assert (m @ [1.0, 0, 5, 1])[:3] == pytest.approx([1, 0, 5], abs=1e-9)         # lo que está sobre el eje no se mueve
    d = movimiento("deslizante", {"desliz": 7.0}, "Z", ([0, 0, 0], [0, 3, 4]))      # desliza a lo largo de (0, .6, .8)
    assert d[:3, 3] == pytest.approx([0, 4.2, 5.6])
    p = movimiento("planar", {"giro": 0.0, "desliz": 2.0, "desliz2": 3.0}, ([0, 0, 0], [0, 0, 1]), "X")
    assert np.hypot(*p[:2, 3]) == pytest.approx(np.hypot(2, 3)) and p[2, 3] == pytest.approx(0)


def test_asm11_la_union_gira_alrededor_de_una_arista_elegida():
    s = api.Sesion()
    base = llamar(s, "create_box", length=100, width=100, height=10)["bodies_created"][0]["id"]     # fija, z 0..10
    brazo = llamar(s, "create_box", length=20, width=10, height=10, x=300)["bodies_created"][0]["id"]
    poste = llamar(s, "create_cylinder", radius=3, height=40, x=30, y=0)["bodies_created"][0]["id"]
    llamar(s, "create_component", bodies=[base, poste], name="Base", grounded=True)
    llamar(s, "create_component", bodies=[brazo], name="Brazo")
    llamar(s, "create_joint", origin1="<Z", body1=brazo, origin2=">Z", body2=base, joint_type="revolute",
           rotation_axis_from=">Z", axis_body=poste, name="J")          # el eje del poste (x = 30) en vez del Z del marco
    c0 = centro(s, brazo)
    assert c0 == pytest.approx([0, 0, 15], abs=1e-4)                    # apoyado en el centro de la cara de arriba
    llamar(s, "drive_joint", joint="J", rotation=90)
    # el centro (0, 0) gira 90° alrededor de (30, 0): queda en (30, −30)
    assert centro(s, brazo) == pytest.approx([30, -30, 15], abs=1e-3)
    assert llamar(s, "get_assembly")["joints"][0]["custom_rotation_axis"] is True
    falla(s, "create_joint", "INVALID_ARGUMENTS", origin1="<Z", body1=brazo, origin2=">Z", body2=base,
          joint_type="slider", rotation_axis_from=">Z", axis_body=poste)


# ---------------------------------------------------------------- ASM-12: límites por movimiento, reposo e invertir
def test_asm12_cada_movimiento_tiene_sus_limites():
    s, base, manivela, piston = _mecanismo()
    # planar: giro (principal) y dos deslizamientos; límite solo en slide2
    s = api.Sesion()
    base = llamar(s, "create_box", length=100, width=100, height=10)["bodies_created"][0]["id"]
    bloque = llamar(s, "create_box", length=10, width=10, height=10, x=300)["bodies_created"][0]["id"]
    llamar(s, "create_component", bodies=[base], name="Base", grounded=True)
    llamar(s, "create_component", bodies=[bloque], name="Bloque")
    llamar(s, "create_joint", origin1="<Z", body1=bloque, origin2=">Z", body2=base, joint_type="planar", name="P",
           motion_limits={"slide2": {"minimum": -5, "maximum": 8}})
    r = api.llamar(s, "drive_joint", {"joint": "P", "slide": 40, "slide2": 20})
    assert r["ok"] and any("La distancia 2 pedida (20 mm) supera el límite máximo (8 mm)" in a for a in r["avisos"])
    j = r["result"]["joint"]
    assert j["values"]["slide"] == 40 and j["values"]["slide2"] == 8                 # el slide sin límite pasa entero
    assert j["limits_by_motion"]["slide2"] == {"minimum": "-5.0", "maximum": "8.0", "rest": None, "flip": False}
    assert centro(s, bloque)[:2] == pytest.approx([40, 8], abs=1e-6)                 # donde quedó, con el recorte
    # un movimiento que el tipo no tiene
    falla(s, "set_joint_limits", "INVALID_ARGUMENTS", joint="P", motion="rotation3", maximum=3)


def test_asm12_invertir_y_reposo():
    s, base, manivela, piston = _mecanismo()
    llamar(s, "set_joint_limits", joint="J1", minimum=0, maximum=30)
    r = api.llamar(s, "set_joint_limits", {"joint": "J1", "minimum": 0, "maximum": 30, "flip": True, "rest": 10})
    assert r["ok"], r
    j = r["result"]["joint"]
    assert j["limits_by_motion"]["rotation"] == {"minimum": "0.0", "maximum": "30.0", "rest": "10.0", "flip": True}
    # invertidos: de −30 a 0; los 60° que tenía la unión quedan recortados a 0
    assert j["values"]["rotation"] == 0
    r = api.llamar(s, "drive_joint", {"joint": "J1", "rotation": -50})
    assert r["ok"] and r["result"]["joint"]["values"]["rotation"] == -30 and any("mínimo" in a for a in r["avisos"])
    # el reposo 10 queda fuera del rango invertido: se lleva al reposo y se recorta al límite (0)
    r = llamar(s, "drive_joint", joint="J1", to_rest=True)
    assert r["joint"]["values"]["rotation"] == 0
    falla(s, "drive_joint", "INVALID_ARGUMENTS", joint="J2", to_rest=True)          # J2 no tiene reposo
    r = llamar(s, "set_joint_limits", joint="J1", flip=False, rest="")              # solo ajusta: los límites siguen
    lim = r["joint"]["limits_by_motion"]["rotation"]
    assert lim == {"minimum": "0.0", "maximum": "30.0", "rest": None, "flip": False}
    r = llamar(s, "set_joint_limits", joint="J1")                                   # sin nada: los quita
    assert r["joint"]["limits_by_motion"]["rotation"]["maximum"] is None


def test_asm12_el_reposo_es_el_valor_inicial_de_una_union_nueva():
    s = api.Sesion()
    base = llamar(s, "create_box", length=100, width=100, height=10)["bodies_created"][0]["id"]
    brazo = llamar(s, "create_box", length=10, width=10, height=10, x=300)["bodies_created"][0]["id"]
    llamar(s, "create_component", bodies=[base], name="Base", grounded=True)
    llamar(s, "create_component", bodies=[brazo], name="Brazo")
    r = llamar(s, "create_joint", origin1="<Z", body1=brazo, origin2=">Z", body2=base, joint_type="revolute", rest=25)
    assert r["joint"]["values"] == {"rotation": 25}
    falla(s, "create_joint", "INVALID_ARGUMENTS", origin1="<Z", body1=brazo, origin2=">Z", body2=base,
          joint_type="rigid", rest=3)


# ---------------------------------------------------------------- ASM-13: vínculo por grado de libertad
def test_asm13_el_vinculo_elige_el_movimiento_de_cada_union():
    s = api.Sesion()
    base = llamar(s, "create_box", length=100, width=100, height=10)["bodies_created"][0]["id"]
    a = llamar(s, "create_box", length=10, width=10, height=10, x=200)["bodies_created"][0]["id"]
    b = llamar(s, "create_box", length=10, width=10, height=10, x=300)["bodies_created"][0]["id"]
    llamar(s, "create_component", bodies=[base], name="Base", grounded=True)
    llamar(s, "create_component", bodies=[a], name="A")
    llamar(s, "create_component", bodies=[b], name="B")
    llamar(s, "create_joint", origin1="<Z", body1=a, origin2=">Z", body2=base, joint_type="cylindrical", name="Cil",
           slide_axis="X")
    llamar(s, "create_joint", origin1="<Z", body1=b, origin2=">Z", body2=base, joint_type="slider", slide_axis="Y",
           name="Des")
    # el DESLIZAMIENTO de la cilíndrica (no su giro, que es lo de antes) manda el de la deslizante
    r = llamar(s, "create_motion_link", joint1="Cil", motion1="slide", joint2="Des", ratio=2)
    assert r["motion_link"]["motion1"] == "slide" and r["motion_link"]["motion2"] is None
    llamar(s, "drive_joint", joint="Cil", slide=7)
    assert llamar(s, "get_assembly")["joints"][1]["values"] == {"slide": 14}
    llamar(s, "drive_joint", joint="Cil", rotation=40)                 # el giro de la cilíndrica no mueve nada más
    assert llamar(s, "get_assembly")["joints"][1]["values"] == {"slide": 14}
    # un movimiento que la unión no tiene: error que dice cuáles tiene
    falla(s, "create_motion_link", "INVALID_ARGUMENTS", joint1="Cil", motion1="rotation3", joint2="Des")


def test_asm13_una_receta_con_un_movimiento_inexistente_falla_diciendo_cuales_tiene():
    s, *_ = _mecanismo()
    llamar(s, "create_motion_link", joint1="J1", joint2="J2", ratio=1, name="V")
    vinculo = next(o for o in s.doc.operaciones if o.nombre == "V")
    from omnicad.timeline.ops_ensamblar import OpVinculoMovimiento
    s.doc.reemplazar(vinculo.id, OpVinculoMovimiento(vinculo.id, "V", False, **dict(vinculo.p, mov2="giro3")))
    paso = next(p for p in llamar(s, "get_timeline")["steps"] if p["name"] == "V")
    assert paso["status"] == "error" and "no tiene el movimiento «giro3»" in paso["message"]


# ---------------------------------------------------------------- ASM-14: estudio de movimiento
def test_asm14_poses_de_estudio_con_varias_uniones_y_vinculo():
    s, base, manivela, piston = _mecanismo()
    estado = s.doc.estado_final
    c0 = centro(s, piston)
    poses = poses_de_estudio(estado, {"op8": {"desliz": 80.0}})              # el pistón pasa de 50 a 80 mm
    nuevo = poses[piston] @ np.r_[c0, 1.0]
    assert nuevo[:3] == pytest.approx([c0[0] + 30, c0[1], c0[2]], abs=1e-6)
    assert manivela not in poses or np.allclose(poses[manivela], np.identity(4))      # la otra unión no se movió
    # sin pedir nada nada se mueve
    assert all(np.allclose(m, np.identity(4)) for m in poses_de_estudio(estado, {}).values())
    # la manivela de 60° a 150° gira 90° alrededor del eje de la unión
    giro = poses_de_estudio(estado, {"op7": {"giro": 150.0}})[manivela]
    assert np.linalg.det(giro[:3, :3]) == pytest.approx(1) and giro[2, 3] == pytest.approx(0, abs=1e-9)
    assert math.degrees(math.atan2(giro[1, 0], giro[0, 0])) == pytest.approx(90, abs=1e-6)


def test_asm14_el_estudio_respeta_el_vinculo_y_la_herramienta_no_cambia_el_documento():
    s, base, manivela, piston = _mecanismo()
    llamar(s, "create_motion_link", joint1="J1", joint2="J2", ratio=0.2)
    estado = s.doc.estado_final
    efectivos = valores_de_estudio(estado, {"op7": {"giro": 100.0}})
    assert efectivos["op8"]["desliz"] == pytest.approx(20.0)                  # 0,2 × 100
    receta = json.dumps(s.doc.a_dict(), sort_keys=True)
    r = llamar(s, "motion_study_pose", values={"J1": 100})
    assert r["document_changed"] is False and json.dumps(s.doc.a_dict(), sort_keys=True) == receta
    pistón = next(c for c in r["components"] if c["name"] == "Piston")
    # 0,2 × 100 = 20 mm contra los 12 mm de antes (0,2 × 60): el pistón va 8 mm más
    assert pistón["translation"][0] - pistón["previous_translation"][0] == pytest.approx(8, abs=1e-6)
    falla(s, "motion_study_pose", "INVALID_ARGUMENTS", values={"J1": float("inf")})
    falla(s, "motion_study_pose", "INVALID_ARGUMENTS", values={"J1:slide": 3})
    falla(s, "motion_study_pose", "INVALID_ARGUMENTS", values={})


def test_asm14_fases_de_reproduccion():
    from omnicad.ui.estudio_movimiento import fase_de_tiempo
    assert fase_de_tiempo(0.25, "una_vez") == (0.25, False) and fase_de_tiempo(3.0, "una_vez") == (1.0, True)
    assert fase_de_tiempo(0.5, "ida_vuelta") == (0.5, False) and fase_de_tiempo(1.5, "ida_vuelta") == (0.5, False)
    assert fase_de_tiempo(1.0, "ida_vuelta")[0] == 1.0 and fase_de_tiempo(2.0, "ida_vuelta") == (0.0, True)
    assert fase_de_tiempo(2.25, "bucle") == (0.25, False) and fase_de_tiempo(40.5, "bucle")[1] is False


# ---------------------------------------------------------------- ASM-15: anclar, posición inicial, capturar y revertir
def test_asm15_anclar_impide_mover_con_una_union_y_desanclar_lo_libera():
    s = api.Sesion()
    base = llamar(s, "create_box", length=100, width=100, height=10)["bodies_created"][0]["id"]
    bloque = llamar(s, "create_box", length=10, width=10, height=10, x=300)["bodies_created"][0]["id"]
    llamar(s, "create_component", bodies=[base], name="Base")
    llamar(s, "create_component", bodies=[bloque], name="Bloque")
    r = llamar(s, "pin_component", component="Bloque")
    assert r["component"]["pinned"] is True and r["component"]["grounded"] is False
    f = falla(s, "create_joint", "INVALID_ARGUMENTS", origin1="<Z", body1=bloque, origin2=">Z", body2=base)
    assert "fijo" in f["mensaje"]
    llamar(s, "pin_component", component="Bloque", pinned=False)
    llamar(s, "create_joint", origin1="<Z", body1=bloque, origin2=">Z", body2=base)
    assert centro(s, bloque) == pytest.approx([0, 0, 15], abs=1e-4)
    assert [p["type"] for p in llamar(s, "get_timeline")["steps"]].count("anclar") == 2     # son pasos del timeline


def test_asm15_posicion_inicial_mueve_y_gira_el_componente():
    s = api.Sesion()
    cuerpo = llamar(s, "create_box", length=20, width=10, height=10)["bodies_created"][0]["id"]    # x ±10, y ±5, z 0..10
    llamar(s, "create_component", bodies=[cuerpo], name="C")
    r = llamar(s, "set_component_initial_position", component="C", offset=[100, 0, 5], rotation=[0, 0, 90])
    # gira 90° alrededor de su centro (0, 0, 5): la caja queda de 10 de ancho en X y 20 en Y, y se corre (100, 0, 5)
    assert caja(s, cuerpo) == pytest.approx([95, -10, 5, 105, 10, 15], abs=1e-4)
    assert r["component"]["bounding_box"]["min"] == pytest.approx([95, -10, 5], abs=1e-4)
    falla(s, "set_component_initial_position", "INVALID_ARGUMENTS", component="C", offset=[1, 2])
    falla(s, "set_component_initial_position", "INVALID_ARGUMENTS", component="C", offset=["nan", 0, 0])
    falla(s, "set_component_initial_position", "COMPONENT_NOT_FOUND", component="Nada", offset=[1, 0, 0])


def test_asm15_capturar_y_revertir_posicion():
    s, base, manivela, piston = _mecanismo()
    c0 = centro(s, piston)                                            # el pistón en 50 mm
    llamar(s, "capture_position")
    # lo que mueve algo DESPUÉS de la captura (un paso nuevo) es lo que se revierte
    llamar(s, "set_component_initial_position", component="Piston", offset=[40, 0, 0])
    assert centro(s, piston)[0] == pytest.approx(c0[0] + 40, abs=1e-6)
    llamar(s, "revert_position", components=["Piston"])
    assert centro(s, piston) == pytest.approx(c0, abs=1e-6)           # vuelve a lo capturado (50 mm)
    # sin captura previa vuelve a donde se modeló: el pistón, a x = 300
    s2, _b, _m, piston2 = _mecanismo()
    llamar(s2, "revert_position", components=["Piston"])
    assert caja(s2, piston2) == pytest.approx([295, -5, 0, 305, 5, 10], abs=1e-6)
    falla(s2, "revert_position", "COMPONENT_NOT_FOUND", components=["Nada"])


def test_asm15_las_recetas_viejas_siguen_abriendo():
    """Una unión guardada sin las claves nuevas se calcula igual que antes."""
    s, base, manivela, piston = _mecanismo()
    d = s.doc.a_dict()
    for paso in d["operaciones"] if "operaciones" in d else d.get("pasos", []):
        for k in ("modo1", "modo2", "origen1b", "origen2b", "ref_eje_giro", "ref_eje_desliz", "limites_dof", "mov1", "mov2"):
            paso.get("params", {}).pop(k, None)
    from omnicad.timeline.documento import Documento
    doc = Documento.desde_dict(d)
    assert all(r.estado == "ok" for r in doc.resultados)
    assert doc.estado_final.uniones["op7"]["valores"]["giro"] == 60.0


# ---------------------------------------------------------------- los comandos de la ventana (sin abrir la ventana)
@pytest.fixture(scope="module", autouse=True)
def app_qt():
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _hit_cara(doc, cid, centro_cara):
    from omnicad.nucleo import referencias as refs
    from omnicad.ui.comando import hit_desde_ref
    f = doc.estado_final.cuerpos[cid].forma
    sub = next(x for x in refs.subformas(f, "cara") if np.allclose(refs.firma_cara(x)["centro"], centro_cara))
    return hit_desde_ref(refs.referencia(cid, sub, f), doc.estado_final)


def test_comando_union_en_modo_entre_dos_caras_y_sus_campos():
    from omnicad.ui.comando import ContextoComando, ErrorComando
    from omnicad.ui.comandos.ensamblar import Union
    s = api.Sesion()
    base = _caja_20x20x30(s)
    bloque = llamar(s, "create_box", length=4, width=4, height=4, x=100)["bodies_created"][0]["id"]
    llamar(s, "create_component", bodies=[base], name="Base", grounded=True)
    llamar(s, "create_component", bodies=[bloque], name="Bloque")
    doc = s.doc
    ctx, cmd = ContextoComando(doc), Union()
    campos = {c.clave: c for c in cmd.campos(ctx)}
    assert not campos["origen2b"].visible_si({"modo2": "simple"}) and campos["origen2b"].visible_si({"modo2": "entre_caras"})
    assert campos["clave2"].visible_si({"modo2": "simple"}) and not campos["clave2"].visible_si({"modo2": "interseccion"})
    v = dict(Union.CLASE_OP.PARAMS, origen1=[_hit_cara(doc, bloque, (100, 0, 0))],
             origen2=[_hit_cara(doc, base, (0, 0, 30))], modo2="entre_caras", origen2b=[])
    with pytest.raises(ErrorComando, match="segundo ajuste del componente 2"):
        cmd.construir(v, ctx)
    v["origen2b"] = [_hit_cara(doc, base, (0, 0, 0))]
    op = cmd.construir(v, ctx)
    assert op.p["modo2"] == "entre_caras" and op.p["origen2b"]["tipo"] == "cara"
    assert doc.agregar(op).estado == "ok"
    assert caja(s, bloque) == pytest.approx([-2, -2, 15, 2, 2, 19], abs=1e-4)
    assert cmd.desde_op(doc.operacion(op.id), ctx)["origen2b"]               # reabrir devuelve la segunda cara


def test_comando_union_limites_por_movimiento_ida_y_vuelta():
    from omnicad.ui.comandos.ensamblar import _campos_de_limites, _limites_dof
    v = {"tipo": "planar", "min_desliz2": "-5", "max_desliz2": "8", "reposo_giro": "10", "inv_giro": True,
         "min_desliz": "1", "max_desliz": "2"}        # desliz y giro: el principal de una planar es el giro
    dof = _limites_dof(v)
    assert dof == {"desliz2": {"minimo": "-5", "maximo": "8"}, "desliz": {"minimo": "1", "maximo": "2"},
                   "giro": {"reposo": "10", "invertir": True}}
    campos = _campos_de_limites({"tipo": "planar", "limites_dof": dof})
    assert campos["min_desliz2"] == "-5" and campos["reposo_giro"] == "10" and campos["inv_giro"] is True
    assert "min_giro" not in campos                # los del principal siguen en «Límite mínimo / máximo»
    assert _limites_dof({"tipo": "rigida", "min_giro": "3"}) == {}


def test_comando_accionar_rechaza_nan_y_vinculo_ofrece_los_movimientos_de_la_union():
    from omnicad.ui.comando import ContextoComando, ErrorComando
    from omnicad.ui.comandos.ensamblar import AccionarUniones, VinculoMovimiento
    s, *_ = _mecanismo()
    ctx = ContextoComando(s.doc)
    with pytest.raises(ErrorComando, match="No es un número"):
        AccionarUniones()._nueva({"union": "op7", "giro": "nan", "desliz": "0 mm"}, ctx)
    campos = {c.clave: c for c in VinculoMovimiento().campos(ctx)}
    assert list(campos["mov1"].listar({"union1": "op7"})) == ["", "giro"]       # J1 solo gira
    assert list(campos["mov2"].listar({"union2": "op8"})) == ["", "desliz"]     # J2 solo desliza
    assert list(campos["mov1"].listar({})) == [""]
    v = {"union1": "op7", "union2": "op8", "factor": "inf", "invertir": False, "mov1": "", "mov2": ""}
    with pytest.raises(ErrorComando, match="No es un número"):
        VinculoMovimiento().construir(v, ctx)
    op = VinculoMovimiento().construir(dict(v, factor="0.5", mov2="desliz"), ctx)
    assert op.p["mov2"] == "desliz" and op.p["mov1"] == ""


def test_comandos_nuevos_anclar_posicion_inicial_capturar_y_revertir():
    from omnicad.ui.comando import ContextoComando, ErrorComando, hit_desde_ref
    from omnicad.ui.comandos import CATALOGO, POR_TIPO
    from omnicad.ui.comandos.ensamblar import (AnclarComponente, CapturarPosicion, PosicionInicial, RevertirPosicion)
    s, base, manivela, piston = _mecanismo()
    doc = s.doc
    ctx = ContextoComando(doc)
    cuerpo = hit_desde_ref({"tipo": "cuerpo", "cuerpo": piston}, doc.estado_final)
    raiz = hit_desde_ref({"tipo": "cuerpo", "cuerpo": llamar(s, "create_box", length=5, width=5, height=5, x=-300)
                          ["bodies_created"][0]["id"]}, doc.estado_final)
    for clase in (AnclarComponente, PosicionInicial, CapturarPosicion, RevertirPosicion):
        assert CATALOGO[clase.CLAVE] is clase and POR_TIPO[clase.CLASE_OP.TIPO] is clase
    with pytest.raises(ErrorComando, match="no está en un componente"):
        AnclarComponente().construir({"cuerpos": [raiz], "anclado": True}, ctx)
    antes = centro(s, piston)
    op = AnclarComponente().construir({"cuerpos": [cuerpo], "anclado": True}, ctx)
    assert op.p["componente"] == "op6" and op.p["anclado"] is True and doc.agregar(op).estado == "ok"
    assert AnclarComponente().desde_op(op, ctx)["cuerpos"]                         # doble clic en el timeline
    op = PosicionInicial().construir(dict(x="40", y="0 mm", z="0", rx="0 deg", ry="0", rz="0", cuerpos=[cuerpo]), ctx)
    assert doc.agregar(op).estado == "ok" and centro(s, piston)[0] == pytest.approx(antes[0] + 40, abs=1e-6)
    with pytest.raises(ErrorComando, match="No es un número"):
        PosicionInicial().construir(dict(x="nan", y="0", z="0", rx="0", ry="0", rz="0", cuerpos=[cuerpo]), ctx)
    op = CapturarPosicion().construir({"cuerpos": []}, ctx)                          # sin elegir: todos
    assert op.p["componentes"] == [] and doc.agregar(op).estado == "ok"
    op = RevertirPosicion().construir({"cuerpos": [cuerpo]}, ctx)
    assert op.p["componentes"] == ["op6"] and RevertirPosicion().desde_op(op, ctx)["cuerpos"]


def test_review_entre_dos_caras_usa_el_centro_del_contorno_exterior_con_agujeros():
    """Una cara con un agujero descentrado: el origen va al centro del contorno exterior, no al centroide del área."""
    s = api.Sesion()
    c = _caja_20x20x30(s)
    llamar(s, "create_cylinder", radius=3, height=30, x=5, y=0, operation="cut", target=c)      # agujero pasante corrido
    r = llamar(s, "create_joint_origin", geometry=">Z", geometry_b="<Z", mode="between_faces", body=c)
    assert r["joint_origin"]["origin"] == pytest.approx([0, 0, 15], abs=1e-6)


def test_review_el_rango_del_estudio_no_falla_con_un_limite_ilegible():
    from omnicad.ui.estudio_movimiento import rango
    s, *_ = _mecanismo()
    op = s.doc.operacion("op7")
    s.doc.reemplazar("op7", OpUnion(op.id, op.nombre, False, **dict(op.p, minimo="nada + 1")))
    assert rango(s.doc, "op7", "giro", 100.0) == (0.0, 360.0)             # vuelve al recorrido de siempre

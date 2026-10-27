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


def test_union_contra_cara_anular_partida_engancha_el_circulo():
    """Regresión B-50: cara plana anular PARTIDA (semianillo: 2 arcos concéntricos + 2 líneas radiales):
    el origen de la unión es el centro del círculo, no el centroide lateralmente corrido."""
    s = api.Sesion()
    placa = llamar(s, "create_cylinder", radius=30, height=10)["bodies_created"][0]["id"]
    llamar(s, "create_cylinder", radius=10, height=10, operation="cut", target=placa)
    llamar(s, "create_box", length=40, width=100, height=10, x=-20, operation="cut", target=placa)  # queda x ≥ 0
    perno = llamar(s, "create_cylinder", radius=10, height=20, x=100)["bodies_created"][0]["id"]
    llamar(s, "create_component", bodies=[placa], name="Placa", grounded=True)
    llamar(s, "create_component", bodies=[perno], name="Perno")
    llamar(s, "create_joint", origin1="%CYLINDER", body1=perno, origin2=">Z", body2=placa,
           joint_type="revolute")
    c = caja(s, perno)
    assert (c[0] + c[3]) / 2 == pytest.approx(0, abs=1e-9)     # el eje del perno quedó en el del agujero
    assert (c[1] + c[4]) / 2 == pytest.approx(0, abs=1e-9)


def test_origen_de_union_sobrevive_al_drive_del_componente():
    """Regresión B-65: un origen de unión guardado sobre una cara de un componente NO pierde la
    referencia cuando un drive mueve (rota/traslada) ese componente y se recalcula."""
    s, base, bloque = dos_cajas()
    r = llamar(s, "create_as_built_joint", origin=">Z", body=bloque, component2="Base", joint_type="revolute")
    jid = r["joint"]["id"]
    llamar(s, "create_joint_origin", geometry="nearest:[100, 55, 15]", body=bloque, name="Lateral")
    llamar(s, "drive_joint", joint=jid, rotation=30)
    llamar(s, "drive_joint", joint=jid, rotation=60)
    pasos = llamar(s, "get_timeline", include_params=False)["steps"]
    assert all(p["status"] != "error" for p in pasos), pasos
    origen = next(p for p in pasos if p["name"] == "Lateral")
    assert origen["status"] == "ok"


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


def test_grupo_rigido_respeta_lo_fijo_y_se_propaga_entre_grupos():
    """ASM-1: el grupo es UN objeto: no mueve a un fijo y alcanza a los grupos encadenados."""
    s, base, bloque = dos_cajas()
    llamar(s, "create_rigid_group", components=["Base", "Bloque"])
    antes = caja(s, base)
    r = falla(s, "create_joint", "INVALID_ARGUMENTS", origin1="<Z", body1=bloque, origin2=">Z", body2=base)
    assert "fijo" in r["mensaje"] and "grupo" in r["mensaje"]
    assert caja(s, base) == antes

    s = api.Sesion()
    a = llamar(s, "create_box", length=10, width=10, height=10, x=100)["bodies_created"][0]["id"]
    b = llamar(s, "create_box", length=10, width=10, height=10, x=200)["bodies_created"][0]["id"]
    c = llamar(s, "create_box", length=10, width=10, height=10, x=300)["bodies_created"][0]["id"]
    base = llamar(s, "create_box", length=40, width=40, height=10)["bodies_created"][0]["id"]
    llamar(s, "create_component", bodies=[base], name="Base", grounded=True)
    llamar(s, "create_component", bodies=[a], name="A")
    llamar(s, "create_component", bodies=[b], name="B")
    llamar(s, "create_component", bodies=[c], name="C")
    llamar(s, "create_rigid_group", components=["A", "B"])
    llamar(s, "create_rigid_group", components=["B", "C"])
    llamar(s, "create_joint", origin1="<Z", body1=a, origin2=">Z", body2=base, joint_type="rigid")
    assert caja(s, a) == pytest.approx([-5, -5, 10, 5, 5, 20])
    assert caja(s, b) == pytest.approx([95, -5, 10, 105, 5, 20])
    assert caja(s, c) == pytest.approx([195, -5, 10, 205, 5, 20])


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


def test_vinculo_de_movimiento_rechaza_relaciones_imposibles():
    """ASM-2: una unión no puede seguir a dos vínculos, ni armar un círculo, ni tener relación 0."""
    s, base, manivela, piston = _mecanismo()
    falla(s, "create_motion_link", "INVALID_ARGUMENTS", joint1="J1", joint2="J2", ratio=0)
    llamar(s, "create_motion_link", joint1="J1", joint2="J2", ratio=2)
    falla(s, "create_motion_link", "INVALID_ARGUMENTS", joint1="J1", joint2="J2", ratio=2)
    falla(s, "create_motion_link", "INVALID_ARGUMENTS", joint1="J2", joint2="J1", ratio=2)


def test_borrar_un_componente_con_uniones_nombra_las_que_lo_usan():
    """ASM-3: un componente que usan uniones no se puede borrar; el error dice cuáles."""
    s, base, bloque = dos_cajas()
    brazo = llamar(s, "create_box", length=10, width=10, height=10, x=200)["bodies_created"][0]["id"]
    llamar(s, "create_component", bodies=[brazo], name="Brazo")
    llamar(s, "create_joint", origin1="<Z", body1=bloque, origin2=">Z", body2="Base", name="Unión A")
    llamar(s, "create_joint", origin1="<Z", body1=brazo, origin2=">Z", body2=bloque, name="Unión B")
    for componente, nombres in (("Base", ["Unión A"]), ("Bloque", ["Unión A", "Unión B"]), ("Brazo", ["Unión B"])):
        r = falla(s, "delete_feature", "FEATURE_IN_USE", feature=componente)
        assert all(n in r["mensaje"] for n in nombres), r["mensaje"]
    # un componente sin uniones se sigue borrando
    suelto = llamar(s, "create_box", length=5, width=5, height=5, x=-200)["bodies_created"][0]["id"]
    llamar(s, "create_component", bodies=[suelto], name="Suelto")
    llamar(s, "delete_feature", feature="Suelto")


@pytest.mark.parametrize("como_esta", [False, True])
def test_borrar_componente_con_union_sobre_un_cuerpo_dividido(como_esta):
    """ASM-3: las partes nuevas heredan el componente y la unión sigue necesitándolo."""
    from omnicad.timeline.documento import Documento
    s, base, bloque = dos_cajas()
    comp = s.cuerpo(base).componente
    parte = llamar(s, "split_body", body=base, tool="YZ")["bodies_created"][0]["id"]
    assert g.es_valida(s.cuerpo(parte).forma)
    assert g.volumen(s.cuerpo(parte).forma) == pytest.approx(8000)
    if como_esta:
        r = llamar(s, "create_as_built_joint", origin="<Z", body=bloque, component2="Base", name="Unión partida")
        # Elegir la parte nueva también al ligar sin mover: el selector automático toma el primer cuerpo.
        op = s.paso(r["feature"]["id"])
        nueva = op.copia()
        nueva.p["origen2"] = {"tipo": "cuerpo", "cuerpo": parte}
        s.doc.reemplazar(op.id, nueva)
    else:
        r = llamar(s, "create_joint", origin1="<Z", body1=bloque, origin2=">Z", body2=parte, name="Unión partida")
    # Al abrir se reconstruyen las dependencias del paso, no solo las de la sesión que lo creó.
    s = api.Sesion(Documento.desde_dict(s.doc.a_dict()))
    assert r["feature"]["id"] in {o.id for o in s.doc.dependientes(comp)}
    r = falla(s, "delete_feature", "FEATURE_IN_USE", feature=comp)
    assert "Unión partida" in r["mensaje"]
    falla(s, "move_feature", "OPERATION_FAILED", feature=comp, index=len(s.doc.operaciones) - 1)
    assert llamar(s, "get_assembly")["joints"][0]["component2"]["id"] == comp


@pytest.mark.parametrize("referencia_valida", [True, False])
def test_borrar_componente_con_referencia_de_cuerpo_en_la_receta(referencia_valida):
    """ASM-3: aceptar referencias dict y poder quitar un paso mal formado sin un error interno."""
    from omnicad.timeline.documento import Documento
    s = api.Sesion()
    cuerpo = llamar(s, "create_box", length=10, width=10, height=10)["bodies_created"][0]["id"]
    comp = llamar(s, "create_component", bodies=[cuerpo], name="Componente de receta")["feature"]["id"]
    receta = s.doc.a_dict()
    receta["operaciones"][-1]["params"]["cuerpos"] = [{"tipo": "cuerpo", "cuerpo": cuerpo} if referencia_valida else {}]
    s = api.Sesion(Documento.desde_dict(receta))
    assert s.doc.resultado(comp).estado == ("ok" if referencia_valida else "error")
    llamar(s, "delete_feature", feature=comp)
    assert comp not in s.doc.estado_final.componentes
    assert not s.cuerpo(cuerpo).componente


@pytest.mark.parametrize("antes_de_la_union", [True, False])
def test_borrado_respeta_el_componente_resuelto_al_crear_la_union(antes_de_la_union):
    """ASM-3: cuenta el dueño al ejecutar la unión, no la primera asignación ni el dueño final."""
    s, base, bloque = dos_cajas()
    anterior = s.cuerpo(base).componente
    if antes_de_la_union:
        llamar(s, "create_component", bodies=[base], name="Nuevo", grounded=True)
    r = llamar(s, "create_joint", origin1="<Z", body1=bloque, origin2=">Z", body2=base, name="Unión vigente")
    if not antes_de_la_union:
        llamar(s, "create_component", bodies=[base], name="Nuevo", grounded=True)
    nuevo = s.cuerpo(base).componente
    if antes_de_la_union:
        llamar(s, "delete_feature", feature=anterior)
        assert s.doc.resultado(r["feature"]["id"]).estado == "ok"
    else:
        falla(s, "delete_feature", "FEATURE_IN_USE", feature=anterior)
    esperado = nuevo if antes_de_la_union else anterior
    assert llamar(s, "get_assembly")["joints"][0]["component2"]["id"] == esperado


def test_vinculo_de_una_receta_con_relacion_cero_falla_en_el_paso():
    """ASM-2: el paso también rechaza una relación que da 0 (expresión o receta vieja)."""
    from omnicad.timeline.ops_ensamblar import OpVinculoMovimiento
    s, base, manivela, piston = _mecanismo()
    op = OpVinculoMovimiento(s.doc.nuevo_id(), "Vínculo malo", union1="op7", union2="op8", factor="1 - 1")
    resultado = s.doc.agregar(op)
    assert resultado.estado == "error" and "cero" in resultado.mensaje


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




# ---------------------------------------------------------------- límites con expresiones y delta (B-64, B-46)
def test_limites_min_mayor_que_max_tambien_con_expresiones():
    s, base, bloque = dos_cajas()
    llamar(s, "create_joint", origin1="<Z", body1=bloque, origin2=">Z", body2=base, joint_type="revolute",
           rotation=30)
    # B-64: con números ya se validaba; con expresiones ("100 deg") el chequeo se salteaba
    falla(s, "set_joint_limits", "INVALID_ARGUMENTS", joint="Unión1", minimum="100 deg", maximum="20 deg")
    llamar(s, "set_joint_limits", joint="Unión1", minimum="10 deg", maximum="80 deg")   # orden bien: entra
    # B-46: el informe del accionado trae cuánto se MOVIÓ el origen del componente, no solo la pose
    # (la pose `translation` orbita el eje: era lo que confundía la auditoría del reporte)
    previa = {c["id"]: c["translation"] for c in llamar(s, "get_assembly")["components"]}
    r = llamar(s, "drive_joint", joint="Unión1", rotation=40)
    (m,) = r["moved_components"]
    assert m["delta_translation"] == pytest.approx([d - o for d, o in zip(m["translation"], previa[m["id"]],
                                                                           strict=True)], abs=1e-3)


def test_delta_translation_del_deslizamiento():
    s = api.Sesion()
    base = llamar(s, "create_box", length=100, width=100, height=10)["bodies_created"][0]["id"]
    piston = llamar(s, "create_box", length=10, width=10, height=10, x=300)["bodies_created"][0]["id"]
    llamar(s, "create_component", bodies=[base], name="Base", grounded=True)
    llamar(s, "create_component", bodies=[piston], name="Piston")
    llamar(s, "create_joint", origin1="<Z", body1=piston, origin2=">Z", body2=base, joint_type="slider",
           slide_axis="X", slide=50, name="J2")
    r = llamar(s, "drive_joint", joint="J2", slide=100)
    (m,) = r["moved_components"]
    assert m["delta_translation"] == pytest.approx([50, 0, 0])    # se deslizó 50 mm más desde los 50 anteriores


# ---------------------------------------------------------------- hallazgos de la prueba de tortura (T-09, T-11)
def test_t09_una_union_nueva_avisa_si_el_componente_ya_tenia_otra():
    s, base, bloque = dos_cajas()
    llamar(s, "create_joint", origin1="<Z", body1=bloque, origin2=">Z", body2="Base", joint_type="revolute",
           rotation=20, name="Giro")
    r = api.llamar(s, "create_joint", {"origin1": "<Z", "body1": bloque, "origin2": ">Z", "body2": "Base"})
    assert r["ok"] and any("ya tiene Giro" in a and "deja de cumplirse" in a for a in r["avisos"]), r
    llamar(s, "suppress_feature", feature="Giro")
    r = api.llamar(s, "create_joint", {"origin1": "<Z", "body1": bloque, "origin2": ">Z", "body2": "Base"})
    assert r["ok"] and not any("ya tiene" in a and "Giro" in a for a in r["avisos"])        # la suprimida no cuenta


def test_t11_accionar_una_union_que_sigue_un_vinculo_no_guarda_el_valor_ignorado():
    s, base, manivela, piston = _mecanismo()
    llamar(s, "create_motion_link", joint1="J1", joint2="J2", ratio=0.2)
    receta = json.dumps(s.doc.a_dict(), sort_keys=True)
    r = api.llamar(s, "drive_joint", {"joint": "J2", "slide": 30})
    assert r["ok"] and "vínculo" in r["avisos"][0] and r["result"]["moved_components"] == []
    assert json.dumps(s.doc.a_dict(), sort_keys=True) == receta         # si se suprimiera el vínculo, no reaparece el 30


def test_t11_el_estudio_de_movimiento_lista_tambien_al_componente_que_sigue_el_vinculo():
    s, base, manivela, piston = _mecanismo()
    llamar(s, "create_motion_link", joint1="J1", joint2="J2", ratio=0.2)
    r = llamar(s, "motion_study", joint="J1", values=[0, 90])
    assert {c["name"] for c in r["steps"][1]["components"]} == {"Manivela", "Piston"}


def test_union_con_deslizamiento_avisa_que_movio_el_componente():
    """Regresión B-50: una unión con deslizamiento avisa que movió el componente (el origen de cada cara es su
    centro); una rígida y una como está no avisan."""
    s, base, bloque = dos_cajas()
    r = api.llamar(s, "create_joint", {"origin1": "<Z", "body1": bloque, "origin2": ">Z", "body2": "Base",
                                       "joint_type": "slider"})
    assert r["ok"] and any("se movió" in a and "create_as_built_joint" in a for a in r["avisos"]), r
    s, base, bloque = dos_cajas()
    r = api.llamar(s, "create_joint", {"origin1": "<Z", "body1": bloque, "origin2": ">Z", "body2": "Base",
                                       "joint_type": "rigid"})
    assert r["ok"] and not any("se movió" in a for a in r["avisos"]), r
    s, base, bloque = dos_cajas()
    r = api.llamar(s, "create_as_built_joint", {"origin": ">Z", "body": bloque, "component2": "Base",
                                                "joint_type": "slider"})
    assert r["ok"] and not any("se movió" in a for a in r["avisos"]), r

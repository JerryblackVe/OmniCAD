# -*- coding: utf-8 -*-
"""ENSAMBLAR igual a Fusion: ASM-11 (la bola con su eje de cabeceo «Pitch» y de guiñada «Yaw» elegidos; el balanceo «Roll»
sale de los dos) y ASM-13 (vínculo de movimiento entre dos movimientos de la MISMA unión, como un tornillo).
Todo con números: posiciones y ángulos."""
import numpy as np
import pytest

from omnicad import api
from omnicad.nucleo import geometria as g
from omnicad.timeline.operaciones import ErrorOperacion
from omnicad.timeline.ops_ensamblar import ejes_bola, movimiento, poses_de_estudio, valores_de_estudio


def llamar(s, nombre, **args):
    r = api.llamar(s, nombre, args)
    assert r["ok"], r
    return r["result"]


def falla(s, nombre, kind, **args):
    r = api.llamar(s, nombre, args)
    assert not r["ok"] and r["error_kind"] == kind, r
    return r


def centro(s, cid):
    c = [v for p in g.caja_envolvente(s.cuerpo(cid).forma) for v in p]
    return [round((c[i] + c[i + 3]) / 2, 4) + 0.0 for i in range(3)]


def _con_bola(**eje):
    """Base fija de 100×100×10 y un cubo de 10 apoyado en el centro de su cara de arriba con una bola en ese punto."""
    s = api.Sesion()
    base = llamar(s, "create_box", length=100, width=100, height=10)["bodies_created"][0]["id"]
    cubo = llamar(s, "create_box", length=10, width=10, height=10, x=200)["bodies_created"][0]["id"]
    poste = llamar(s, "create_cylinder", radius=3, height=40, x=30, y=0)["bodies_created"][0]["id"]
    llamar(s, "create_component", bodies=[base, poste], name="Base", grounded=True)
    llamar(s, "create_component", bodies=[cubo], name="Cubo")
    llamar(s, "create_joint", origin1="<Z", body1=cubo, origin2=">Z", body2=base, joint_type="ball", name="Bola",
           axis_body=poste, **eje)
    return s, cubo


# ---------------------------------------------------------------- ASM-11: Pitch y Yaw de la bola
def test_con_los_ejes_de_siempre_el_movimiento_es_el_de_las_recetas_viejas():
    valores = {"giro": 20.0, "giro2": 30.0, "giro3": 40.0}
    viejo = movimiento("bola", valores)
    nuevo = movimiento("bola", valores, "Z", {"cabeceo": "Y", "guinada": "X"})
    assert nuevo == pytest.approx(viejo, abs=1e-12)
    centro_, balanceo, cabeceo, guinada = ejes_bola({})
    assert balanceo == pytest.approx([0, 0, 1]) and cabeceo == pytest.approx([0, 1, 0]) and guinada == pytest.approx([1, 0, 0])


def test_el_balanceo_sale_de_la_guinada_y_el_cabeceo_elegidos():
    # cabeceo X y guiñada Z: el balanceo es guiñada × cabeceo = Z × X = Y
    _, balanceo, cabeceo, guinada = ejes_bola({"cabeceo": "X", "guinada": "Z"})
    assert balanceo == pytest.approx([0, 1, 0]) and cabeceo == pytest.approx([1, 0, 0]) and guinada == pytest.approx([0, 0, 1])
    eje = {"cabeceo": "X", "guinada": "Z"}
    punto = np.array([1.0, 2.0, 3.0, 1.0])
    assert (movimiento("bola", {"giro2": 90.0}, "Z", eje) @ punto)[:3] == pytest.approx([1, -3, 2], abs=1e-9)   # X por 90°
    assert (movimiento("bola", {"giro3": 90.0}, "Z", eje) @ punto)[:3] == pytest.approx([-2, 1, 3], abs=1e-9)   # Z por 90°
    assert (movimiento("bola", {"giro": 90.0}, "Z", eje) @ punto)[:3] == pytest.approx([3, 2, -1], abs=1e-9)    # Y por 90°
    # la guiñada que no es perpendicular al cabeceo se corrige: queda su parte perpendicular
    _, _, _, g2 = ejes_bola({"cabeceo": "Z", "guinada": ([0, 0, 0], [1, 0, 1])})
    assert g2 == pytest.approx([1, 0, 0], abs=1e-9)


def test_cabeceo_y_guinada_paralelos_se_rechazan_con_un_mensaje_claro():
    with pytest.raises(ErrorOperacion, match="paralelos"):
        ejes_bola({"cabeceo": "X", "guinada": ([0, 0, 0], [3, 0, 0])})


def test_api_la_bola_gira_el_cabeceo_sobre_el_eje_elegido():
    # el cubo queda 5 mm sobre el origen de la unión (centro de la cara de arriba de la base, z = 10)
    s, cubo = _con_bola(rotation2=90)
    assert centro(s, cubo) == pytest.approx([5, 0, 10], abs=1e-3)               # Pitch por defecto = Y: el cubo cae sobre +X
    s, cubo = _con_bola(rotation2=90, pitch_axis="X", yaw_axis="Z")
    assert centro(s, cubo) == pytest.approx([0, -5, 10], abs=1e-3)              # Pitch = X
    s, cubo = _con_bola(rotation2=90, pitch_axis="Y", yaw_axis="X")
    assert centro(s, cubo) == pytest.approx([5, 0, 10], abs=1e-3)               # lo de siempre, dicho a mano
    info = llamar(s, "get_assembly")["joints"][0]
    assert info["pitch_axis"] == "Y" and info["yaw_axis"] == "X"


def test_api_la_guinada_y_el_balanceo_usan_sus_ejes():
    s, cubo = _con_bola(rotation3=90, pitch_axis="Y", yaw_axis="X")
    assert centro(s, cubo) == pytest.approx([0, -5, 10], abs=1e-3)              # Yaw = X por 90°
    s, cubo = _con_bola(rotation3=90, pitch_axis="Y", yaw_axis="Z")
    assert centro(s, cubo) == pytest.approx([0, 0, 15], abs=1e-3)               # el cubo está sobre el eje Z: no se mueve
    s, cubo = _con_bola(rotation=90, pitch_axis="X", yaw_axis="Z")
    assert centro(s, cubo) == pytest.approx([5, 0, 10], abs=1e-3)               # balanceo = Y (guiñada × cabeceo)


def test_api_eje_de_cabeceo_propio_gira_alrededor_de_una_arista_o_cilindro():
    s, cubo = _con_bola(rotation2=90, pitch_axis_from=">Z")                     # el eje del poste, en x = 30
    assert centro(s, cubo) == pytest.approx([30, -30, 15], abs=1e-3)
    assert llamar(s, "get_assembly")["joints"][0]["pitch_axis"] == "custom"


def test_api_ejes_de_la_bola_pedidos_donde_no_hay_bola_o_mal_combinados_fallan():
    s = api.Sesion()
    base = llamar(s, "create_box", length=100, width=100, height=10)["bodies_created"][0]["id"]
    cubo = llamar(s, "create_box", length=10, width=10, height=10, x=200)["bodies_created"][0]["id"]
    llamar(s, "create_component", bodies=[base], name="Base", grounded=True)
    llamar(s, "create_component", bodies=[cubo], name="Cubo")
    falla(s, "create_joint", "INVALID_ARGUMENTS", origin1="<Z", body1=cubo, origin2=">Z", body2=base,
          joint_type="revolute", pitch_axis="X")
    falla(s, "create_joint", "INVALID_ARGUMENTS", origin1="<Z", body1=cubo, origin2=">Z", body2=base,
          joint_type="ball", pitch_axis="X", pitch_axis_from=">Z")
    antes = len(s.doc.operaciones)
    falla(s, "create_joint", "OPERATION_FAILED", origin1="<Z", body1=cubo, origin2=">Z", body2=base, joint_type="ball",
          pitch_axis="X", yaw_axis="X")
    assert len(s.doc.operaciones) == antes                                      # el documento no cambió


def test_la_receta_vieja_de_una_bola_abre_igual():
    s, cubo = _con_bola(rotation=20, rotation2=30, rotation3=40)
    vieja = centro(s, cubo)
    op = next(o for o in s.doc.operaciones if o.TIPO == "union")
    for clave in ("eje_cabeceo", "eje_guinada", "ref_eje_cabeceo", "ref_eje_guinada"):
        op.p.pop(clave)                                                          # recetas guardadas antes de ASM-11
    s.doc.reemplazar(op.id, type(op)(op.id, op.nombre, op.suprimida, **op.p))
    assert centro(s, cubo) == pytest.approx(vieja, abs=1e-9)
    s2, cubo2 = _con_bola(rotation=20, rotation2=30, rotation3=40, pitch_axis="Y", yaw_axis="X")
    assert centro(s2, cubo2) == pytest.approx(vieja, abs=1e-9)                  # y con los ejes dichos a mano, lo mismo


# ---------------------------------------------------------------- ASM-13: dos movimientos de la misma unión
def _tornillo():
    """Una cilíndrica (gira y desliza sobre Z) y el vínculo «desliza 0,5 mm por grado»."""
    s = api.Sesion()
    base = llamar(s, "create_box", length=100, width=100, height=10)["bodies_created"][0]["id"]
    perno = llamar(s, "create_box", length=10, width=10, height=10, x=200)["bodies_created"][0]["id"]
    llamar(s, "create_component", bodies=[base], name="Base", grounded=True)
    llamar(s, "create_component", bodies=[perno], name="Perno")
    llamar(s, "create_joint", origin1="<Z", body1=perno, origin2=">Z", body2=base, joint_type="cylindrical",
           name="Tornillo")
    return s, perno


def test_el_giro_de_una_cilindrica_manda_su_propio_deslizamiento():
    s, perno = _tornillo()
    z0 = centro(s, perno)[2]
    r = llamar(s, "create_motion_link", joint1="Tornillo", motion1="rotation", joint2="Tornillo", motion2="slide", ratio=0.5)
    assert r["motion_link"]["motion1"] == "rotation" and r["motion_link"]["motion2"] == "slide"
    llamar(s, "drive_joint", joint="Tornillo", rotation=90)
    valores = llamar(s, "get_assembly")["joints"][0]["values"]
    assert valores["rotation"] == pytest.approx(90) and valores["slide"] == pytest.approx(45)
    assert centro(s, perno)[2] - z0 == pytest.approx(45, abs=1e-3)               # sube 45 mm mientras gira 90°
    llamar(s, "drive_joint", joint="Tornillo", rotation=-40)
    assert llamar(s, "get_assembly")["joints"][0]["values"]["slide"] == pytest.approx(-20)
    assert centro(s, perno)[2] - z0 == pytest.approx(-20, abs=1e-3)


def test_el_vinculo_con_la_misma_union_exige_dos_movimientos_distintos():
    s, _ = _tornillo()
    for args in ({}, {"motion1": "rotation"}, {"motion1": "rotation", "motion2": "rotation"}):
        falla(s, "create_motion_link", "INVALID_ARGUMENTS", joint1="Tornillo", joint2="Tornillo", **args)
    assert not [o for o in s.doc.operaciones if o.TIPO == "vinculo_movimiento"]
    # una unión de un solo movimiento no tiene con qué relacionarse
    s2 = api.Sesion()
    base = llamar(s2, "create_box", length=100, width=100, height=10)["bodies_created"][0]["id"]
    a = llamar(s2, "create_box", length=10, width=10, height=10, x=200)["bodies_created"][0]["id"]
    llamar(s2, "create_component", bodies=[base], name="Base", grounded=True)
    llamar(s2, "create_component", bodies=[a], name="A")
    llamar(s2, "create_joint", origin1="<Z", body1=a, origin2=">Z", body2=base, joint_type="revolute", name="R")
    falla(s2, "create_motion_link", "INVALID_ARGUMENTS", joint1="R", motion1="rotation", joint2="R", motion2="slide")


def test_el_vinculo_a_la_misma_union_sigue_funcionando_en_el_estudio_de_movimiento():
    s, perno = _tornillo()
    llamar(s, "create_motion_link", joint1="Tornillo", motion1="rotation", joint2="Tornillo", motion2="slide", ratio=0.5)
    estado = s.doc.estado_final
    union = next(iter(estado.uniones))
    efectivos = valores_de_estudio(estado, {union: {"giro": 120.0}})
    assert efectivos[union]["giro"] == pytest.approx(120) and efectivos[union]["desliz"] == pytest.approx(60)
    poses = poses_de_estudio(estado, {union: {"giro": 120.0}})
    antes = np.array(g.caja_envolvente(s.cuerpo(perno).forma)[0])
    assert poses[perno][2, 3] == pytest.approx(60, abs=1e-6)                     # sube 60 mm sin recalcular
    assert antes[2] == pytest.approx(10, abs=1e-6)


def test_dos_uniones_distintas_siguen_igual_y_una_union_no_se_sigue_a_si_misma_dos_veces():
    s, _ = _tornillo()
    llamar(s, "create_motion_link", joint1="Tornillo", motion1="rotation", joint2="Tornillo", motion2="slide", ratio=0.5)
    falla(s, "create_motion_link", "INVALID_ARGUMENTS", joint1="Tornillo", motion1="slide", joint2="Tornillo",
          motion2="rotation", ratio=2)                                           # ya hay un vínculo que la mueve
    # accionar una unión con vínculo propio SÍ se puede: el giro es libre y el deslizamiento lo sigue
    r = llamar(s, "drive_joint", joint="Tornillo", rotation=10)
    assert not r.get("warnings")

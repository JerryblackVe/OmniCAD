# -*- coding: utf-8 -*-
"""ENSAMBLAR › Posición: el cuerpo reasignado que trae el movimiento de otro componente (B-108) y arrastrar componentes
sin capturar (ASM-15). Todo con números: posiciones, ángulos y valores."""
import json
import math

import numpy as np
import pytest
from test_ensamblar_asm import _mecanismo, caja, centro, falla, llamar

from omnicad import api
from omnicad.nucleo import geometria as g
from omnicad.timeline.documento import Documento
from omnicad.timeline.operaciones import ErrorOperacion
from omnicad.timeline.posicion import Arrastre, deshacer_arrastre, pendiente_de, que_arrastra


def _id(r):
    return r["bodies_created"][0]["id"]


def _centro_doc(doc, cid):
    a, b = g.caja_envolvente(doc.estado_final.cuerpos[cid].forma)
    return (np.array(a) + np.array(b)) / 2


def _pluma(reasignar, con_pin=True):
    """Lo de B-108: «Padre» gira sobre su base; «Hijo», colgado de él con una unión como está, recibe el brazo partido en
    dos y un perno. Con `reasignar`, el brazo estuvo antes en «Padre» y ya giró con él."""
    s = api.Sesion()
    llamar(s, "create_cylinder", name="Base", radius=25, height=4, x=116.25, z=55)
    brazo = _id(llamar(s, "create_box", name="Brazo", length=30, width=30, height=200, x=175, y=-15, z=-100, anchor="corner"))
    llamar(s, "create_construction_plane", plane="XY", offset=0, name="Corte")
    mitad = _id(llamar(s, "split_body", body=brazo, tool="Corte"))
    llamar(s, "create_component", name="Padre", bodies=["Base", brazo, mitad] if reasignar else ["Base"])
    llamar(s, "create_as_built_joint", name="Giro", origin="%CYLINDER", body="Base", joint_type="revolute")
    pin = _id(llamar(s, "create_cylinder", name="Pin", radius=2, height=4, plane="XZ", x=190, y=110, z=-2))
    llamar(s, "create_component", name="Hijo", bodies=[brazo, mitad, *([pin] if con_pin else [])])
    llamar(s, "create_as_built_joint", name="Elevacion", origin="%CYLINDER" if con_pin else ">Z",
           body=pin if con_pin else mitad, component2="Padre", joint_type="revolute")
    return s, brazo, mitad, pin


def test_b108_un_cuerpo_reasignado_no_se_separa_de_los_otros_del_componente_al_girar_el_padre():
    casos = []
    for reasignar in (False, True):
        s, brazo, mitad, pin = _pluma(reasignar)
        antes = llamar(s, "measure_distance", a=mitad, b=pin)["distance"]
        llamar(s, "drive_joint", joint="Giro", rotation=10)
        assert llamar(s, "measure_distance", a=mitad, b=pin)["distance"] == pytest.approx(antes, abs=1e-6)
        assert not llamar(s, "check_interference", bodies=[mitad, pin])["pairs"]
        casos.append({c: np.array(centro(s, c)) for c in (brazo, mitad, pin)})
    for c, posicion in casos[0].items():                 # reasignado o no, la pluma queda en el mismo lugar
        assert casos[1][c] == pytest.approx(posicion, abs=1e-3)
    assert not np.allclose(casos[1][pin], [190, 0, 110], atol=1)


def test_b108_sigue_igual_al_guardar_y_reabrir(tmp_path):
    s, _brazo, mitad, pin = _pluma(True)
    llamar(s, "drive_joint", joint="Giro", rotation=10)
    distancia = llamar(s, "measure_distance", a=mitad, b=pin)["distance"]
    ruta = tmp_path / "pluma.omnicad"
    llamar(s, "save_document", path=str(ruta))
    llamar(s, "open_document", path=str(ruta))
    assert llamar(s, "measure_distance", a=mitad, b=pin)["distance"] == pytest.approx(distancia, abs=1e-6)
    llamar(s, "drive_joint", joint="Giro", rotation=25)
    assert llamar(s, "measure_distance", a=mitad, b=pin)["distance"] == pytest.approx(distancia, abs=1e-6)


def test_b108_todos_del_mismo_componente_el_nuevo_hereda_su_movimiento_y_no_gira_dos_veces():
    control, reasignado = _pluma(False, con_pin=False), _pluma(True, con_pin=False)
    for s, *_ in (control, reasignado):
        r = api.llamar(s, "drive_joint", {"joint": "Giro", "rotation": 10})
        assert r["ok"] and not any("ya mueve" in a for a in r["avisos"]), r
    for c in control[1:3]:
        assert centro(reasignado[0], c) == pytest.approx(centro(control[0], c), abs=1e-3)


def test_b108_mezclados_avisa_y_quedan_en_su_posicion_relativa_con_el_padre_ya_girado():
    s = api.Sesion()
    llamar(s, "create_cylinder", name="Base", radius=25, height=4)
    a = _id(llamar(s, "create_box", name="A", length=10, width=10, height=10, x=100))
    llamar(s, "create_component", name="Padre", bodies=["Base", a])
    llamar(s, "create_as_built_joint", name="Giro", origin="%CYLINDER", body="Base", joint_type="revolute", rotation=90)
    assert centro(s, a) == pytest.approx([0, 100, 5], abs=1e-3)
    b = _id(llamar(s, "create_box", name="B", length=10, width=10, height=10, x=120))
    r = api.llamar(s, "create_component", {"name": "Hijo", "bodies": [a, b]})
    assert r["ok"] and any("venían movidos" in x for x in r["avisos"]), r
    assert np.subtract(centro(s, b), centro(s, a)) == pytest.approx([20, 0, 0], abs=1e-3)


def test_b108_una_receta_vieja_da_lo_mismo_que_antes():
    s, brazo, _mitad, pin = _pluma(True)
    llamar(s, "drive_joint", joint="Giro", rotation=10)
    receta = json.loads(json.dumps(s.doc.a_dict()))
    pasos = [o for o in receta["operaciones"] if o["tipo"] == "componente"]
    assert len(pasos) == 2 and all(o["params"].pop("version_pose") == 2 for o in pasos)    # así se guardaban
    viejo = Documento.desde_dict(receta)
    assert all(o.p["version_pose"] == 1 for o in viejo.operaciones if o.TIPO == "componente")
    assert not any(r.estado == "error" for r in viejo.resultados)
    # el cálculo de antes: el brazo giró 20° (10° con el padre y otros 10° al seguirlo) y el perno 10°
    def girado(p, grados):
        c, gr = np.array([116.25, 0.0]), math.radians(grados)
        x, y = np.subtract(p[:2], c)
        return [*(c + [x * math.cos(gr) - y * math.sin(gr), x * math.sin(gr) + y * math.cos(gr)]), p[2]]
    assert _centro_doc(viejo, brazo) == pytest.approx(girado([190, 0, -50], 20), abs=1e-3)
    assert _centro_doc(viejo, pin) == pytest.approx(girado([190, 0, 110], 10), abs=1e-3)


def test_b108_version_mal_formada_nombra_el_campo():
    s = api.Sesion()
    c = _id(llamar(s, "create_box", length=10, width=10, height=10))
    llamar(s, "create_component", bodies=[c], name="C")
    receta = s.doc.a_dict()
    next(o for o in receta["operaciones"] if o["tipo"] == "componente")["params"]["version_pose"] = "x"
    doc = Documento.desde_dict(receta)
    assert any(r.estado == "error" and "version_pose" in r.mensaje for r in doc.resultados)


# ------------------------------------------------------------------ ASM-15: arrastrar sin capturar
def _libre():
    s = api.Sesion()
    a = _id(llamar(s, "create_box", name="A", length=10, width=10, height=10))
    b = _id(llamar(s, "create_box", name="B", length=10, width=10, height=10, x=100))
    llamar(s, "create_component", bodies=[a], name="CA")
    llamar(s, "create_component", bodies=[b], name="CB")
    return s, a, b


def test_asm15_sin_union_mueve_libre_y_el_documento_no_cambia_hasta_capturar():
    s, a, b = _libre()
    receta, modificado = json.dumps(s.doc.a_dict(), sort_keys=True), s.doc.modificado
    r = llamar(s, "drag_component", component="CB", offset=[10, 20, 5])
    assert r["uncaptured"] is True and r["document_changed"] is False
    movido = next(c for c in r["components"] if c["name"] == "CB")
    assert movido["bounding_box"]["min"] == pytest.approx([105, 15, 5], abs=1e-6)
    assert json.dumps(s.doc.a_dict(), sort_keys=True) == receta and s.doc.modificado == modificado
    assert llamar(s, "get_assembly")["uncaptured_position"] is True
    llamar(s, "drag_component", component="CB", offset=[-10, 0, 0])              # los arrastres se acumulan
    assert pendiente_de(s.doc).libres[s.doc.estado_final.cuerpos[b].componente] == pytest.approx([0, 20, 5])
    n = len(s.doc.operaciones)
    llamar(s, "capture_position")
    assert [o.TIPO for o in s.doc.operaciones[n:]] == ["posicion_inicial", "capturar_posicion"]
    assert caja(s, b) == pytest.approx([95, 15, 5, 105, 25, 15], abs=1e-6)
    assert llamar(s, "get_assembly")["uncaptured_position"] is False
    llamar(s, "undo")                                                            # capturar es UN paso de deshacer
    assert len(s.doc.operaciones) == n and caja(s, b) == pytest.approx([95, -5, 0, 105, 5, 10], abs=1e-6)


def test_asm15_revertir_descarta_lo_arrastrado_y_no_agrega_pasos():
    s, _a, b = _libre()
    llamar(s, "drag_component", component=b, offset=[10, 0, 0])
    n = len(s.doc.operaciones)
    r = llamar(s, "revert_position")
    assert r["reverted_uncaptured"] is True and len(s.doc.operaciones) == n
    assert pendiente_de(s.doc) is None and llamar(s, "get_assembly")["uncaptured_position"] is False
    llamar(s, "revert_position")                                                 # sin nada pendiente, el paso de siempre
    assert len(s.doc.operaciones) == n + 1


def test_asm15_cualquier_otro_cambio_del_documento_descarta_lo_arrastrado():
    s, _a, b = _libre()
    llamar(s, "drag_component", component=b, offset=[10, 0, 0])
    llamar(s, "create_box", length=5, width=5, height=5, x=500)
    assert pendiente_de(s.doc) is None
    assert caja(s, b) == pytest.approx([95, -5, 0, 105, 5, 10], abs=1e-6)


def test_asm15_el_arrastre_no_se_guarda_en_el_archivo(tmp_path):
    s, _a, b = _libre()
    llamar(s, "drag_component", component=b, offset=[10, 0, 0])
    ruta = tmp_path / "a.omnicad"
    llamar(s, "save_document", path=str(ruta))
    llamar(s, "open_document", path=str(ruta))
    assert caja(s, b) == pytest.approx([95, -5, 0, 105, 5, 10], abs=1e-6)
    assert llamar(s, "get_assembly")["uncaptured_position"] is False


def test_asm15_con_union_sigue_su_grado_de_libertad_y_capturar_da_lo_mismo():
    s, _base, manivela, piston = _mecanismo()
    c0 = centro(s, piston)
    punto = [c0[0], c0[1], c0[2]]
    r = llamar(s, "drag_component", component="Piston", offset=[25, 40, 10], point=punto)  # el deslizamiento es sobre X
    movido = next(c for c in r["components"] if c["name"] == "Piston")["bounding_box"]
    assert np.mean([movido["min"], movido["max"]], axis=0) == pytest.approx([c0[0] + 25, c0[1], c0[2]], abs=1e-3)
    assert list(pendiente_de(s.doc).valores.values())[0]["desliz"] == pytest.approx(75, abs=1e-3)
    llamar(s, "capture_position")
    assert centro(s, piston) == pytest.approx([c0[0] + 25, c0[1], c0[2]], abs=1e-3)
    assert llamar(s, "get_assembly")["joints"][1]["values"]["slide"] == pytest.approx(75, abs=1e-3)


def test_asm15_el_giro_lleva_el_punto_agarrado_al_objetivo():
    s, _base, manivela, _piston = _mecanismo()
    u = s.doc.estado_final.uniones
    uid = next(k for k, x in u.items() if x["nombre"] == "J1")
    k = s.doc.estado_final.cuerpos[manivela].componente
    F = np.array(u[uid]["marco"])
    p0 = np.array(centro(s, manivela)) + [4, 3, 0]                                # sobre el cuerpo, fuera del eje
    radio = p0 - F[:3, 3] - ((p0 - F[:3, 3]) @ F[:3, 2]) * F[:3, 2]
    assert np.linalg.norm(radio) > 1
    c, sn = math.cos(math.radians(50)), math.sin(math.radians(50))
    n = F[:3, 2]
    destino = p0 - radio + radio * c + np.cross(n, radio) * sn                    # 50° más adelante sobre su círculo
    r = api.llamar(s, "drag_component", {"component": k, "point": p0.tolist(), "offset": (destino - p0).tolist()})
    assert r["ok"], r
    assert pendiente_de(s.doc).valores[uid]["giro"] % 360 == pytest.approx((60 + 50) % 360, abs=1e-3)
    pose = pendiente_de(s.doc).poses()[manivela]
    assert (pose @ np.r_[p0, 1.0])[:3] == pytest.approx(destino, abs=1e-3)
    esperado = g.transformar(s.doc.estado_final.cuerpos[manivela].forma, pose)
    llamar(s, "capture_position")
    a, b = g.caja_envolvente(esperado), g.caja_envolvente(s.doc.estado_final.cuerpos[manivela].forma)
    assert np.r_[a[0], a[1]] == pytest.approx(np.r_[b[0], b[1]], abs=1e-3)       # lo que se vio es lo que queda


def test_asm15_los_limites_frenan_el_arrastre():
    s, _base, _manivela, piston = _mecanismo()
    llamar(s, "set_joint_limits", joint="J2", minimum=0, maximum=60)
    c0 = centro(s, piston)
    llamar(s, "drag_component", component="Piston", offset=[100, 0, 0], point=c0)
    assert list(pendiente_de(s.doc).valores.values())[0]["desliz"] == pytest.approx(60, abs=1e-6)


def test_asm15_lo_que_no_se_puede_arrastrar_lo_dice():
    s = api.Sesion()
    a = _id(llamar(s, "create_box", length=10, width=10, height=10))
    b = _id(llamar(s, "create_box", length=10, width=10, height=10, x=50))
    c = _id(llamar(s, "create_box", length=10, width=10, height=10, x=90))
    llamar(s, "create_component", bodies=[a], name="Fijo", grounded=True)
    llamar(s, "create_component", bodies=[b], name="Anclado")
    llamar(s, "pin_component", component="Anclado")
    llamar(s, "create_component", bodies=[c], name="Vacio")
    assert "fijo" in falla(s, "drag_component", "INVALID_ARGUMENTS", component="Fijo", offset=[1, 0, 0])["mensaje"]
    assert "anclado" in falla(s, "drag_component", "INVALID_ARGUMENTS", component="Anclado", offset=[1, 0, 0])["mensaje"]
    falla(s, "drag_component", "COMPONENT_NOT_FOUND", component="Nada", offset=[1, 0, 0])
    falla(s, "drag_component", "INVALID_ARGUMENTS", component="Vacio", offset=[1, 0])
    falla(s, "drag_component", "INVALID_ARGUMENTS", component="Vacio", offset=[float("nan"), 0, 0])


def test_asm15_una_union_rigida_pasa_el_arrastre_a_lo_que_la_sostiene():
    s, a, b = _libre()
    llamar(s, "create_joint", origin1="<Z", body1=b, origin2=">Z", body2=a, joint_type="rigid", name="R")
    estado = s.doc.estado_final
    comp_a, comp_b = (estado.cuerpos[c].componente for c in (a, b))
    assert que_arrastra(estado, comp_b) == ([], [comp_a])
    llamar(s, "drag_component", component=comp_b, offset=[0, 30, 0])
    assert pendiente_de(s.doc).libres == {comp_a: pytest.approx([0, 30, 0])}
    poses = pendiente_de(s.doc).poses()
    for c in (a, b):                                                              # lo que cuelga va con él
        assert (poses[c] @ np.r_[0, 0, 0, 1.0])[:3] == pytest.approx([0, 30, 0], abs=1e-6)


def test_asm15_rigida_contra_la_raiz_no_tiene_a_donde_moverse():
    s, a, b = _libre()
    llamar(s, "create_as_built_joint", origin=">Z", body=b, joint_type="rigid", name="R")
    assert "rígida" in falla(s, "drag_component", "INVALID_ARGUMENTS", component=b, offset=[1, 0, 0])["mensaje"]


def test_asm15_el_componente_libre_lleva_lo_que_cuelga_tambien_despues_de_capturar():
    s = api.Sesion()
    a = _id(llamar(s, "create_box", name="A", length=10, width=10, height=10))
    b = _id(llamar(s, "create_box", name="B", length=30, width=10, height=10, x=100))
    llamar(s, "create_component", bodies=[a], name="CA")
    llamar(s, "create_component", bodies=[b], name="CB")
    llamar(s, "create_as_built_joint", origin="<Z", body=b, component2="CA", joint_type="revolute", name="Bisagra")
    llamar(s, "drag_component", component="CA", offset=[0, 50, 0])
    assert (pendiente_de(s.doc).poses()[b] @ np.r_[100, 0, 5, 1.0])[:3] == pytest.approx([100, 50, 5], abs=1e-6)
    llamar(s, "capture_position")
    assert centro(s, a) == pytest.approx([0, 50, 5], abs=1e-6)
    assert centro(s, b) == pytest.approx([100, 50, 5], abs=1e-6)
    tipos = [o.TIPO for o in s.doc.operaciones]
    assert tipos.index("posicion_inicial") < tipos.index("union")                # antes de la unión que cuelga de él
    llamar(s, "drive_joint", joint="Bisagra", rotation=90)                        # el eje de la unión se fue con él
    assert caja(s, b) == pytest.approx([95, 35, 0, 105, 65, 10], abs=1e-6)


def test_asm15_la_union_que_sigue_a_un_vinculo_se_mueve_desde_la_otra():
    s, *_ = _mecanismo()
    llamar(s, "create_motion_link", joint1="J1", joint2="J2", ratio=0.5, name="V")
    estado = s.doc.estado_final
    uid1 = next(k for k, u in estado.uniones.items() if u["nombre"] == "J1")
    uid2 = next(k for k, u in estado.uniones.items() if u["nombre"] == "J2")
    comp = estado.uniones[uid2]["comp1"]
    assert que_arrastra(estado, comp)[0] == [(uid1, "giro")]
    r = api.llamar(s, "drag_component", {"component": comp, "offset": [10, 0, 0]})
    assert r["ok"], r
    p = pendiente_de(s.doc)
    assert uid1 in p.valores and uid2 not in p.valores
    # J2 sigue a J1 × 0,5: de 60° a 80° el pistón avanza los 10 mm que se pidieron
    assert p.valores[uid1]["giro"] == pytest.approx(80, abs=1e-3)


def test_asm15_deshacer_vuelve_de_a_un_arrastre_y_cancelar_no_deja_rastro():
    s, _a, b = _libre()
    doc = s.doc
    comp = doc.estado_final.cuerpos[b].componente
    for dx in (10, 20):
        llamar(s, "drag_component", component=comp, offset=[dx, 0, 0])
    assert pendiente_de(doc).libres[comp] == pytest.approx([30, 0, 0])
    assert deshacer_arrastre(doc) and pendiente_de(doc).libres[comp] == pytest.approx([10, 0, 0])
    assert deshacer_arrastre(doc) and pendiente_de(doc) is None
    assert not deshacer_arrastre(doc)
    a = Arrastre(doc, b, [100, 0, 5])
    a.mover([120, 0, 5])
    assert pendiente_de(doc) is not None
    a.cancelar()
    assert pendiente_de(doc) is None
    a = Arrastre(doc, b, [100, 0, 5])
    a.soltar()                                                                    # agarró y soltó sin mover
    assert pendiente_de(doc) is None


def test_asm15_con_la_recta_del_cursor_el_deslizamiento_va_al_punto_mas_cercano():
    s, _base, _manivela, piston = _mecanismo()
    c0 = np.array(centro(s, piston))
    a = Arrastre(s.doc, piston, c0)
    a.mover(c0 + [20, 0, 500], np.array([0.0, 0.0, 1.0]))                         # mirando desde arriba: 20 mm en X
    a.soltar()
    assert list(pendiente_de(s.doc).valores.values())[0]["desliz"] == pytest.approx(70, abs=1e-3)


def test_asm15_arrastrar_un_cuerpo_suelto_no_es_un_componente():
    s = api.Sesion()
    c = _id(llamar(s, "create_box", length=10, width=10, height=10))
    with pytest.raises(ErrorOperacion):
        Arrastre(s.doc, c, [0, 0, 5])

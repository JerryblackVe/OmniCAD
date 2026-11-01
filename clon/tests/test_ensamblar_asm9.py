# -*- coding: utf-8 -*-
"""ASM-9: componentes anidados (subensamblajes). Nuevo componente con «Padre», mover al padre mueve a sus hijos (unión,
posición inicial, Capturar y Revertir, estudio de movimiento, arrastre), «Incluir componentes secundarios» del grupo
rígido, get_assembly y lista de materiales, y que las recetas viejas (sin `padre`) dan lo mismo."""
import json

import numpy as np
import pytest

from omnicad import api
from omnicad.nucleo import geometria as g
from omnicad.timeline.ops_ensamblar import OpComponente, OpGrupoRigido, familia, grupo_rigido, poses_de_estudio


def llamar(s, nombre, **args):
    r = api.llamar(s, nombre, args)
    assert r["ok"], r
    return r["result"]


def falla(s, nombre, kind, **args):
    receta = json.dumps(s.doc.a_dict(), sort_keys=True)
    r = api.llamar(s, nombre, args)
    assert not r["ok"] and r["error_kind"] == kind, r
    assert json.dumps(s.doc.a_dict(), sort_keys=True) == receta
    return r


def centro(s, cid):
    a, b = g.caja_envolvente(s.cuerpo(cid).forma)
    return [(a[i] + b[i]) / 2 for i in range(3)]


def _subensamblaje():
    """Base fija (100×100×10); Brazo (10×10×10 en x=200) y, colgando de él, Mano (10×10×10 en x=250)."""
    s = api.Sesion()
    base = llamar(s, "create_box", length=100, width=100, height=10)["bodies_created"][0]["id"]
    brazo = llamar(s, "create_box", length=10, width=10, height=10, x=200)["bodies_created"][0]["id"]
    mano = llamar(s, "create_box", length=10, width=10, height=10, x=250)["bodies_created"][0]["id"]
    llamar(s, "create_component", bodies=[base], name="Base", grounded=True)
    cb = llamar(s, "create_component", bodies=[brazo], name="Brazo")["component"]
    cm = llamar(s, "create_component", bodies=[mano], name="Mano", parent="Brazo")["component"]
    return s, base, brazo, mano, cb["id"], cm["id"]


def test_padre_en_la_receta_y_en_get_assembly():
    s, base, brazo, mano, kb, km = _subensamblaje()
    estado = s.doc.estado_final
    assert estado.componentes[km]["padre"] == kb and estado.componentes[kb]["padre"] == ""
    assert familia(estado, kb) == {kb, km} and familia(estado, km) == {km}
    comps = {c["name"]: c for c in llamar(s, "get_assembly")["components"]}
    assert comps["Mano"]["parent"] == kb and comps["Mano"]["path"] == "Brazo › Mano" and comps["Mano"]["children"] == []
    assert comps["Brazo"]["children"] == [km] and comps["Brazo"]["parent"] == "" and comps["Brazo"]["path"] == "Brazo"
    # el paso guarda el id del padre y lo declara como dependencia
    op = s.doc.operacion(km)
    assert op.p["padre"] == kb and kb in op.dependencias()
    # padre inexistente: error claro y el documento no cambia
    r = falla(s, "create_component", "COMPONENT_NOT_FOUND", bodies=[mano], name="Otra", parent="Nada")
    assert "Nada" in r["mensaje"]
    # la lista de materiales nombra el camino del subensamblaje
    filas = {f["name"]: f for f in llamar(s, "get_bill_of_materials")["rows"]}
    assert filas["Brazo › Mano"]["component"] == "Brazo › Mano" and filas["Brazo"]["quantity"] == 1


def test_una_union_sobre_el_padre_mueve_al_hijo():
    s, base, brazo, mano, kb, km = _subensamblaje()
    antes_brazo, antes_mano = centro(s, brazo), centro(s, mano)
    llamar(s, "create_joint", origin1="<Z", body1=brazo, origin2=">Z", body2=base, joint_type="revolute",
           rotation=90, name="Giro")
    # el brazo bajó a la base (su cara de abajo sobre la de arriba de la base) y giró 90°: la mano fue con él
    desp_brazo = np.subtract(centro(s, brazo), antes_brazo)
    desp_mano = np.subtract(centro(s, mano), antes_mano)
    assert desp_brazo[2] == pytest.approx(desp_mano[2], abs=1e-6)            # bajan lo mismo
    # la mano estaba a +50 en X del brazo; girada 90° alrededor del eje del brazo queda a +50 en Y
    rel = np.subtract(centro(s, mano), centro(s, brazo))
    assert rel[0] == pytest.approx(0, abs=1e-6) and abs(rel[1]) == pytest.approx(50, abs=1e-6)
    u = s.doc.estado_final.uniones["op7"]
    assert set(u["componentes"]) == {kb, km}
    # la matriz del hijo también se actualizó (lo usa el estudio y la selección por firma)
    assert not np.allclose(s.doc.estado_final.componentes[km]["matriz"], np.identity(4))
    # el estudio de movimiento mueve los dos con la unión
    poses = poses_de_estudio(s.doc.estado_final, {"op7": {"giro": 180}})
    assert brazo in poses and mano in poses
    # cambiar la cota del giro (editar la unión) recalcula y la mano sigue pegada
    llamar(s, "drive_joint", joint="Giro", rotation=0)
    rel = np.subtract(centro(s, mano), centro(s, brazo))
    assert rel[0] == pytest.approx(50, abs=1e-6) and rel[1] == pytest.approx(0, abs=1e-6)


def test_un_hijo_creado_despues_de_la_union_sigue_a_su_padre_en_el_estudio():
    s = api.Sesion()
    base = llamar(s, "create_box", length=100, width=100, height=10)["bodies_created"][0]["id"]
    brazo = llamar(s, "create_box", length=10, width=10, height=10, x=200)["bodies_created"][0]["id"]
    llamar(s, "create_component", bodies=[base], name="Base", grounded=True)
    llamar(s, "create_component", bodies=[brazo], name="Brazo")
    llamar(s, "create_joint", origin1="<Z", body1=brazo, origin2=">Z", body2=base, joint_type="revolute", name="Giro")
    dedo = llamar(s, "create_box", length=4, width=4, height=4, x=60)["bodies_created"][0]["id"]
    llamar(s, "create_component", bodies=[dedo], name="Dedo", parent="Brazo")
    poses = poses_de_estudio(s.doc.estado_final, {"op5": {"giro": 90}})
    assert dedo in poses and np.allclose(poses[dedo], poses[brazo])
    assert dedo in json.dumps(llamar(s, "motion_study_pose", values={"Giro": 90}))


def test_grupo_rigido_con_y_sin_componentes_secundarios():
    s, base, brazo, mano, kb, km = _subensamblaje()
    carro = llamar(s, "create_box", length=20, width=20, height=20, y=150)["bodies_created"][0]["id"]
    kc = llamar(s, "create_component", bodies=[carro], name="Carro")["component"]["id"]
    estado = s.doc.estado_final
    # sin la casilla: el grupo liga Carro y Brazo; Mano sigue a Brazo pero puede moverse sola
    r = llamar(s, "create_rigid_group", components=["Carro", "Brazo"], name="G1")
    assert [c["id"] for c in r["rigid_group"]["components"]] == [kc, kb]
    estado = s.doc.estado_final
    assert grupo_rigido(estado, kb) == {kb, km, kc} and grupo_rigido(estado, km) == {km}
    assert grupo_rigido(estado, kc) == {kc, kb, km}
    llamar(s, "undo")
    # con «Incluir componentes secundarios»: la Mano entra al grupo y mover la Mano mueve a todos
    r = llamar(s, "create_rigid_group", components=["Carro", "Brazo"], name="G2", include_children=True)
    assert [c["id"] for c in r["rigid_group"]["components"]] == [kc, kb, km]
    estado = s.doc.estado_final
    assert s.doc.operacion(r["rigid_group"]["id"]).p["incluir_hijos"] is True
    assert grupo_rigido(estado, km) == {km, kb, kc}
    antes = {c: centro(s, c) for c in (brazo, mano, carro)}
    llamar(s, "create_joint", origin1="<Z", body1=mano, origin2=">Z", body2=base, joint_type="rigid", name="Pega")
    desp = {c: np.subtract(centro(s, c), antes[c]) for c in (brazo, mano, carro)}
    assert np.allclose(desp[brazo], desp[mano]) and np.allclose(desp[carro], desp[mano])
    assert abs(desp[mano]).sum() > 1          # de verdad se movió
    # el paso guarda la opción y la receta vieja (sin la clave) sigue sin incluir hijos
    d = s.doc.a_dict()
    paso = next(o for o in d["operaciones"] if o["tipo"] == "grupo_rigido")
    assert paso["params"]["incluir_hijos"] is True
    del paso["params"]["incluir_hijos"]
    from omnicad.timeline.documento import Documento
    doc2 = Documento.desde_dict(d)
    assert doc2.operacion(paso["id"]).p.get("incluir_hijos", False) is False
    assert doc2.estado_final.grupos_rigidos[-1] == [kc, kb]


def test_posicion_inicial_capturar_y_revertir_alcanzan_al_subensamblaje():
    s, base, brazo, mano, kb, km = _subensamblaje()
    a_brazo, a_mano = centro(s, brazo), centro(s, mano)
    llamar(s, "set_component_initial_position", component="Brazo", offset=[10, 20, 0])
    assert np.allclose(np.subtract(centro(s, mano), a_mano), [10, 20, 0])
    assert np.allclose(np.subtract(centro(s, brazo), a_brazo), [10, 20, 0])
    # capturar el padre captura al hijo; revertir el padre devuelve a los dos
    llamar(s, "capture_position", components=["Brazo"])
    assert "captura" in s.doc.estado_final.componentes[km]
    llamar(s, "set_component_initial_position", component="Brazo", offset=[0, 0, 30])
    assert np.allclose(np.subtract(centro(s, mano), a_mano), [10, 20, 30])
    llamar(s, "revert_position", components=["Brazo"])
    assert np.allclose(np.subtract(centro(s, mano), a_mano), [10, 20, 0])
    assert np.allclose(np.subtract(centro(s, brazo), a_brazo), [10, 20, 0])


def test_arrastrar_el_padre_lleva_al_hijo_y_el_hijo_se_arrastra_solo():
    s, base, brazo, mano, kb, km = _subensamblaje()
    r = llamar(s, "drag_component", component="Brazo", offset=[0, 0, 40])
    poses = s.doc.posicion_pendiente.poses()
    assert brazo in poses and mano in poses and np.allclose(poses[mano][:3, 3], [0, 0, 40])
    s.doc.posicion_pendiente = None                       # Revertir de la barra
    llamar(s, "drag_component", component="Mano", offset=[0, 0, 40])
    poses = s.doc.posicion_pendiente.poses()
    assert mano in poses and brazo not in poses, r


def test_receta_vieja_sin_padre_da_lo_mismo():
    s, base, brazo, mano, kb, km = _subensamblaje()
    llamar(s, "create_joint", origin1="<Z", body1=brazo, origin2=">Z", body2=base, joint_type="revolute",
           rotation=45, name="Giro")
    d = s.doc.a_dict()
    for o in d["operaciones"]:
        if o["tipo"] == "componente":
            o["params"].pop("padre", None)       # una receta de antes de ASM-9
    from omnicad.timeline.documento import Documento
    doc2 = Documento.desde_dict(d)
    assert all(doc2.resultado(o.id).estado == "ok" for o in doc2.operaciones)
    for k in (kb, km):
        assert doc2.estado_final.componentes[k]["padre"] == "" and doc2.operacion(k).p["padre"] == ""
    # de un solo nivel, como antes: la unión del brazo no mueve a la mano
    assert set(doc2.estado_final.uniones["op7"]["componentes"]) == {kb}
    assert OpComponente.PARAMS["padre"] == "" and OpGrupoRigido.PARAMS["incluir_hijos"] is False


def test_comandos_nuevo_componente_con_padre_y_grupo_rigido_con_casilla():
    from omnicad.ui.comando import ContextoComando, hit_desde_ref
    from omnicad.ui.comandos.ensamblar import GrupoRigido, NuevoComponente
    s, base, brazo, mano, kb, km = _subensamblaje()
    doc = s.doc
    ctx = ContextoComando(doc)
    campos = {c.clave: c for c in NuevoComponente().campos(ctx)}
    assert set(campos["padre"].opciones) == {"", "op4", kb, km} and campos["padre"].opciones[km] == "Brazo › Mano"
    assert campos["padre"].opciones[""] == "(raíz)"
    dedo = llamar(s, "create_box", length=4, width=4, height=4, x=60)["bodies_created"][0]["id"]
    hit = hit_desde_ref({"tipo": "cuerpo", "cuerpo": dedo}, doc.estado_final)
    op = NuevoComponente().construir({"cuerpos": [hit], "fijo": False, "padre": km}, ctx)
    kd = op.id
    assert op.p["padre"] == km and doc.agregar(op).estado == "ok"
    assert doc.estado_final.componentes[kd]["padre"] == km and familia(doc.estado_final, kb) == {kb, km, kd}
    assert NuevoComponente().desde_op(op, ctx)["padre"] == km
    # al editar la Mano, ni ella ni sus hijos se ofrecen como padre (sería un lazo)
    ctx_edicion = ContextoComando(doc, op=doc.operacion(km))
    opciones = {c.clave: c for c in NuevoComponente().campos(ctx_edicion)}["padre"].opciones
    assert km not in opciones and kd not in opciones and kb in opciones
    casillas = {c.clave: c for c in GrupoRigido().campos(ctx)}
    assert casillas["incluir_hijos"].etiqueta == "Incluir componentes secundarios"
    hits = [hit_desde_ref({"tipo": "cuerpo", "cuerpo": c}, doc.estado_final) for c in (brazo, base)]
    op = GrupoRigido().construir({"cuerpos": hits, "incluir_hijos": True}, ctx)
    assert op.p["incluir_hijos"] is True and doc.agregar(op).estado == "ok"
    assert set(doc.estado_final.grupos_rigidos[-1]) == {kb, "op4", km, kd}
    assert GrupoRigido().desde_op(op, ctx)["incluir_hijos"] is True


def test_copiar_y_repetir_un_subensamblaje_entero():
    s, base, brazo, mano, kb, km = _subensamblaje()
    # Duplicar con uniones (el paso «Copiar componente») copia el padre y, debajo, su hijo
    llamar(s, "run_operation", type="copiar_componente", params={"componente": "Brazo"})
    estado = s.doc.estado_final
    copia = next(k for k, d in estado.componentes.items() if d["nombre"].startswith("Brazo") and k != kb)
    hijo = f"{copia}.s1"
    assert estado.componentes[hijo]["padre"] == copia and estado.componentes[hijo]["nombre"].startswith("Mano")
    assert len([c for c in estado.cuerpos.values() if c.componente == hijo]) == 1
    assert familia(estado, copia) == {copia, hijo}
    # un patrón de componentes repite el subensamblaje: 2 copias, cada una con su hijo, desplazadas
    r = llamar(s, "rectangular_pattern", components=["Brazo"], x_count=3, x_spacing=100)
    estado = s.doc.estado_final
    pid = r["step"]["id"] if "step" in r else r.get("feature", {}).get("id") or r.get("id")
    nuevos = [k for k in estado.componentes if k.startswith(f"{pid}.k")]
    assert sorted(nuevos) == [f"{pid}.k1", f"{pid}.k1.s1", f"{pid}.k2", f"{pid}.k2.s1"]
    assert estado.componentes[f"{pid}.k2.s1"]["padre"] == f"{pid}.k2"
    cuerpo_hijo = next(c for c in estado.cuerpos.values() if c.componente == f"{pid}.k2.s1")
    assert centro(s, cuerpo_hijo.id)[0] == pytest.approx(centro(s, mano)[0] + 200, abs=1e-6)

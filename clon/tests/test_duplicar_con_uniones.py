# -*- coding: utf-8 -*-
"""H-4: Duplicar con uniones (ENSAMBLAR; Fusion: Duplicate With Joints). Una copia del componente por destino, cada una
con su paso «Copiar componente» y su unión; todo o nada y en un solo deshacer. Posiciones por la caja envolvente."""
import json

from test_api_ensamble import caja, dos_cajas, falla, llamar

from omnicad import api

from omnicad.timeline.ops_ensamblar import OpCopiarComponente, OpUnion


def _escena():
    """Base 40×40×10 fija, bloque 10×10×10 apoyado en el centro de su cara de arriba y dos orígenes de unión sobre ella."""
    s, base, bloque = dos_cajas()
    llamar(s, "create_joint", origin1="<Z", body1=bloque, origin2=">Z", body2="Base", name="Apoyo")
    llamar(s, "create_joint_origin", geometry=">Z", body=base, offset=[15, 0, 0], name="Destino A")
    llamar(s, "create_joint_origin", geometry=">Z", body=base, offset=[-15, 5, 0], name="Destino B")
    return s, base, bloque


def test_duplica_el_componente_en_cada_destino_con_su_union():
    s, base, bloque = _escena()
    r = llamar(s, "duplicate_with_joints", joint="Apoyo", destinations=["Destino A", "Destino B"])
    assert r["count"] == 2 and r["source_joint"] == "op5" and r["source_component"]["name"] == "Bloque"
    assert [c["joint"]["type"] for c in r["copies"]] == ["rigid", "rigid"]
    assert all(c["joint"]["status"] == "ok" and c["component"]["name"].startswith("Bloque (copia") for c in r["copies"])
    ops = s.doc.operaciones
    assert [type(o) for o in ops[-4:]] == [OpCopiarComponente, OpUnion, OpCopiarComponente, OpUnion]
    assert ops[-4].p["componente"] == "op4" and ops[-4].nombre == "Copiar componente1"
    copia_a, copia_b = (c["component"]["bodies"][0]["id"] for c in r["copies"])
    assert caja(s, bloque) == [-5, -5, 10, 5, 5, 20]                      # el original no se movió
    assert caja(s, copia_a) == [10, -5, 10, 20, 5, 20] and caja(s, copia_b) == [-20, 0, 10, -10, 10, 20]
    a = llamar(s, "get_assembly")
    assert [c["name"] for c in a["components"]][:2] == ["Base", "Bloque"] and len(a["components"]) == 4
    assert len(a["joints"]) == 3


def test_la_copia_repite_el_tipo_y_los_limites_de_la_union_original():
    s, base, bloque = dos_cajas()
    llamar(s, "create_joint", origin1="<Z", body1=bloque, origin2=">Z", body2="Base", joint_type="revolute",
           rotation=20, minimum=-30, maximum=45, name="Bisagra")
    llamar(s, "create_joint_origin", geometry=">Z", body=base, offset=[15, 0, 0], name="Destino")
    (copia,) = llamar(s, "duplicate_with_joints", joint="Bisagra", destinations=["Destino"])["copies"]
    j = copia["joint"]
    assert j["type"] == "revolute" and j["values"] == {"rotation": 20} and float(j["limits"]["maximum"]) == 45
    # la copia gira sola: accionar su unión no toca el original
    llamar(s, "drive_joint", joint=j["id"], rotation=0)
    assert caja(s, bloque) != caja(s, copia["component"]["bodies"][0]["id"])


def test_flip_da_vuelta_la_copia_y_acepta_una_lista():
    s, base, bloque = _escena()
    r = llamar(s, "duplicate_with_joints", joint="op5", destinations=["Destino A", "Destino B"], flip=[True, False])
    ops = [o for o in s.doc.operaciones if isinstance(o, OpUnion)]
    assert [o.p["voltear"] for o in ops] == [False, True, False]
    assert r["count"] == 2
    falla(s, "duplicate_with_joints", "INVALID_ARGUMENTS", joint="op5", destinations=["Destino A"], flip=[True, False])


def test_todo_o_nada_y_un_solo_deshacer():
    s, base, bloque = _escena()
    antes = json.dumps(s.doc.a_dict(), sort_keys=True)
    falla(s, "duplicate_with_joints", "INVALID_ARGUMENTS", joint="Apoyo", destinations=[])
    falla(s, "duplicate_with_joints", "INVALID_ARGUMENTS", joint="Apoyo", destinations=["Destino A", "no-es-un-destino"])
    falla(s, "duplicate_with_joints", "JOINT_NOT_FOUND", joint="Fantasma", destinations=["Destino A"])
    assert json.dumps(s.doc.a_dict(), sort_keys=True) == antes
    llamar(s, "duplicate_with_joints", joint="Apoyo", destinations=["Destino A", "Destino B"])
    assert len(s.doc.operaciones) == 5 + 2 + 4
    llamar(s, "undo")
    assert json.dumps(s.doc.a_dict(), sort_keys=True) == antes            # las dos copias, un solo deshacer


def test_rechaza_una_union_como_esta_y_acepta_una_suprimida():
    s, base, bloque = _escena()
    otro = llamar(s, "create_box", length=6, width=6, height=6, x=200)["bodies_created"][0]["id"]
    llamar(s, "create_component", bodies=[otro], name="Otro")
    asbuilt = llamar(s, "create_as_built_joint", origin=">Z", body=otro, component2="Base", joint_type="revolute")
    falla(s, "duplicate_with_joints", "INVALID_ARGUMENTS", joint=asbuilt["joint"]["id"], destinations=["Destino A"])
    llamar(s, "suppress_feature", feature="Apoyo")                 # suprimida: el componente sigue ahí y se puede copiar
    assert llamar(s, "duplicate_with_joints", joint="Apoyo", destinations=["Destino A"])["count"] == 1


def test_el_paso_copiar_componente_solo_y_con_un_componente_que_no_existe():
    s, base, bloque = _escena()
    llamar(s, "run_operation", type="copiar_componente", params={"componente": "Bloque"})
    nombres = [c["name"] for c in llamar(s, "get_assembly")["components"]]
    assert nombres == ["Base", "Bloque", "Bloque (copia)"]
    falla(s, "run_operation", "OPERATION_FAILED", type="copiar_componente", params={"componente": "Nada"})


def test_la_receta_con_copias_se_guarda_y_se_restaura_igual():
    s, base, bloque = _escena()
    llamar(s, "duplicate_with_joints", joint="Apoyo", destinations=["Destino A", "Destino B"])
    cajas = {c.id: caja(s, c.id) for c in s.doc.estado_final.cuerpos.values()}
    receta = llamar(s, "get_recipe")
    s2 = api.Sesion()
    llamar(s2, "apply_recipe", recipe=receta["recipe"] if "recipe" in receta else receta)
    assert {c.id: caja(s2, c.id) for c in s2.doc.estado_final.cuerpos.values()} == cajas
    assert [o.TIPO for o in s2.doc.operaciones].count("copiar_componente") == 2

"""B-346: un agujero tan grande que se lleva el cuerpo entero daba un paso verde con el aviso «quedó vacío y se eliminó»
(y al aceptar, el cuerpo desaparecía). Ahora es un error: el paso queda en rojo y el cuerpo sigue."""
from omnicad import api


def _caja():
    s = api.Sesion()
    caja = api.llamar(s, "create_box", {"length": 30, "width": 30, "height": 20, "name": "Caja"})["result"]["bodies_created"][0]["id"]
    return s, caja


def test_un_agujero_que_se_lleva_el_cuerpo_entero_es_un_error_y_no_borra_nada():
    s, caja = _caja()
    antes = s.doc.a_dict()
    r = api.llamar(s, "create_hole", {"diameter": 406, "depth": 408, "face": ">Z", "body": caja})
    assert not r["ok"] and "deja sin material a Caja" in r["mensaje"], r
    assert s.doc.a_dict() == antes and caja in s.doc.estado_final.cuerpos          # atómica: ni paso ni cuerpo perdido


def test_un_agujero_que_deja_material_sigue_andando():
    s, caja = _caja()
    for d, prof in ((6, 8), (406, 8), (29, 20)):          # un agujero ancho pero poco profundo, o pasante y angosto
        r = api.llamar(s, "create_hole", {"diameter": d, "depth": prof, "face": ">Z", "body": caja})
        assert r["ok"] and caja in s.doc.estado_final.cuerpos, (d, prof, r)
        api.llamar(s, "undo", {})

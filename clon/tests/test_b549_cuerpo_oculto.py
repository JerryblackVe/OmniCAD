"""B-549: Unir/Cortar sin objetos elegidos no alcanza a un cuerpo oculto (como en Fusion), y el mensaje dice la causa en un
renglón: «el cuerpo está oculto», no «no hay cuerpos» ni «no tocó ningún cuerpo»."""
import pytest

from omnicad import api


def _caso(oculto=True):
    s = api.Sesion()
    s.doc.set_propiedad(["__navegador__"], "ocultos", [])
    api.llamar(s, "sketch_from_spec", {"name": "Placa", "entities": [{"type": "rectangle", "corner1": [0, -20], "corner2": [100, 20]}]})
    r = api.llamar(s, "extrude", {"sketch": "Placa", "distance": 10})
    assert r["ok"], r
    cid = r["result"]["bodies_created"][0]["id"]
    if oculto:
        s.doc.set_propiedad(["__navegador__"], "ocultos", [cid])
    api.llamar(s, "sketch_from_spec", {"name": "Perfil", "entities": [{"type": "rectangle", "corner1": [40, -5], "corner2": [50, 5]}]})
    return s, cid


def test_cortar_con_el_cuerpo_oculto_dice_que_esta_oculto():
    s, _ = _caso()
    antes = s.doc.a_dict()
    r = api.llamar(s, "extrude", {"sketch": "Perfil", "distance": 5, "operation": "cut"})
    assert not r["ok"] and r["error_kind"] == "NO_TARGET_BODY", r
    assert r["mensaje"].endswith("El cuerpo está oculto: mostralo para cortar."), r["mensaje"]
    assert s.doc.a_dict() == antes


def test_unir_con_el_cuerpo_oculto_avisa_que_esta_oculto():
    s, cid = _caso()
    r = api.llamar(s, "extrude", {"sketch": "Perfil", "distance": 5, "operation": "join"})
    assert r["ok"], r
    assert "El cuerpo está oculto: se creó uno nuevo." in str(r), r
    assert len(s.doc.estado_final.cuerpos) == 2 and cid in s.doc.estado_final.cuerpos


@pytest.mark.parametrize("operacion", ["cut", "join"])
def test_sin_cuerpos_el_mensaje_no_habla_de_ocultos(operacion):
    s = api.Sesion()
    api.llamar(s, "sketch_from_spec", {"name": "Perfil", "entities": [{"type": "rectangle", "corner1": [40, -5], "corner2": [50, 5]}]})
    r = api.llamar(s, "extrude", {"sketch": "Perfil", "distance": 5, "operation": operacion})
    assert "está oculto" not in str(r), r

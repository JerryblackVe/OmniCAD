"""B-474: si new_document falla por cambios sin guardar, el error dice que el documento viejo sigue abierto (regla 14: un renglón)."""
from omnicad import api


def test_el_error_dice_que_el_documento_viejo_sigue_activo():
    s = api.Sesion()
    assert api.llamar(s, "create_box", {"length": 10, "width": 10, "height": 10})["ok"]
    r = api.llamar(s, "new_document", {"name": "Otro"})
    assert r["error_kind"] == "UNSAVED_CHANGES"
    assert r["mensaje"].endswith("tiene cambios sin guardar y sigue abierto.") and len(r["mensaje"]) < 80
    assert any("sobre este documento" in p for p in r["pistas"])
    siguiente = api.llamar(s, "create_box", {"length": 1, "width": 1, "height": 1})   # corre sobre el viejo, como avisa el error
    assert siguiente["ok"] and len(s.doc.estado_final.cuerpos) == 2

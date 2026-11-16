"""B-565: una cara plana no es un eje de giro (Fusion no la acepta y el panel tampoco). Por la API se colaba y el eje
pasaba por el origen de la superficie de la cara, lejos de ella; ahora es un error claro. Una cara cilíndrica sigue."""
import pytest

from omnicad import api


def _sesion():
    s = api.Sesion()
    assert api.llamar(s, "create_cylinder", {"radius": 5, "height": 20})["ok"]
    assert api.llamar(s, "create_sketch", {"plane": "XZ", "name": "P"})["ok"]
    assert api.llamar(s, "draw_rectangle", {"sketch": "P", "x1": 20, "y1": 0, "x2": 30, "y2": 10})["ok"]
    caras = api.llamar(s, "find_faces", {"body": "Cuerpo1"})["result"]["faces"]       # los ids valen hasta el próximo cambio
    plana = next(f["id"] for f in caras if f["type"] == "plane")
    cilindro = next(f["id"] for f in caras if f["type"] == "cylinder")
    return s, plana, cilindro


@pytest.mark.parametrize("herramienta,args", [("revolve", {"sketch": "P", "profile": 0, "angle": 90}),
                                              ("project_spun_profile", {"sketch": "P", "bodies": ["Cuerpo1"]})])
def test_una_cara_plana_como_eje_es_un_error_claro(herramienta, args):
    s, plana, _ = _sesion()
    antes = s.doc.a_dict()
    r = api.llamar(s, herramienta, dict(args, axis=plana))
    assert not r["ok"] and r["error_kind"] == "INVALID_AXIS" and "cara plana" in r["mensaje"], r
    assert s.doc.a_dict() == antes


def test_una_cara_cilindrica_sigue_sirviendo_de_eje():
    s, _, cilindro = _sesion()
    r = api.llamar(s, "revolve", {"sketch": "P", "profile": 0, "angle": 90, "axis": cilindro, "operation": "new_body"})
    assert r["ok"], r

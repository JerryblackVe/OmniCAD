"""B-634: Vaciar la tapa circular de una solevación sólida rectángulo → círculo falla."""
from omnicad import api
from omnicad.nucleo import geometria as geo


def _ok(sesion, herramienta, **args):
    r = api.llamar(sesion, herramienta, args)
    assert r["ok"], r.get("mensaje", r)
    return r["result"]


def _pieza_solida():
    s = api.Sesion()
    _ok(s, "create_sketch", plane="XY", name="Boceto1")
    _ok(s, "draw_rectangle", center_x=0, center_y=0, width=80, height=36, center_diagonals=True)
    _ok(s, "create_construction_plane", plane="XY", offset=83.38, name="Plano1")
    _ok(s, "create_sketch", plane="Plano1", name="Boceto2")
    _ok(s, "draw_circle", center_x=0, center_y=0, radius=42)
    perfiles = [{"sketch": nombre, "profile": 0} for nombre in ("Boceto1", "Boceto2")]
    r = _ok(s, "loft", sections=perfiles)
    return s, r["bodies_created"][0]["id"]


def test_vaciar_tapa_circular():
    s, cid = _pieza_solida()
    antes = geo.volumen_exacto(s.cuerpo(cid).forma)
    _ok(s, "shell", body=cid, faces="+Z", thickness=1, direction="inside")
    forma = s.cuerpo(cid).forma
    assert geo.es_valida(forma) and 0 < geo.volumen_exacto(forma) < antes

"""B-850: Engrosar una solevación de superficie y después Vaciar un loft sólido, en el MISMO proceso.

El offset primario de Engrosar (BRepOffset) agrandaba IN PLACE las tolerancias de la topología
compartida con los perfiles cacheados del boceto: el loft sólido del paso siguiente nacía con
vértices de tolerancia ~2,7 mm y su Vaciado fallaba («el kernel no pudo hacerlo con 1 mm»),
aunque cada paso aislado pasaba. El arreglo copia la base antes de alimentar al kernel.
"""
from omnicad import api
from omnicad.nucleo import geometria as geo


def _ok(sesion, herramienta, **args):
    r = api.llamar(sesion, herramienta, args)
    assert r["ok"], r.get("mensaje", r)
    return r["result"]


def _perfiles(s):
    _ok(s, "create_sketch", plane="XY", name="Boceto1")
    _ok(s, "draw_rectangle", center_x=0, center_y=0, width=80, height=36, center_diagonals=True)
    _ok(s, "create_construction_plane", plane="XY", offset=83.38, name="Plano1")
    _ok(s, "create_sketch", plane="Plano1", name="Boceto2")
    _ok(s, "draw_circle", center_x=0, center_y=0, radius=42)
    return [{"sketch": n, "profile": 0} for n in ("Boceto1", "Boceto2")]


def test_vaciar_tras_engrosar_en_el_mismo_proceso():
    """Pasa aislado; fallaba si antes corría el engrosado (fuga de estado global, B-850)."""
    s1 = api.Sesion()
    r = _ok(s1, "create_surface_loft", profiles=_perfiles(s1))
    _ok(s1, "thicken", faces=r["bodies_created"][0]["id"], thickness=2)
    s2 = api.Sesion()
    r = _ok(s2, "loft", sections=_perfiles(s2))
    cid = r["bodies_created"][0]["id"]
    antes = geo.volumen_exacto(s2.cuerpo(cid).forma)
    _ok(s2, "shell", body=cid, faces="+Z", thickness=1, direction="inside")
    forma = s2.cuerpo(cid).forma
    assert geo.es_valida(forma) and 0 < geo.volumen_exacto(forma) < antes

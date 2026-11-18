"""B-633/B-634: operaciones sobre una solevación de rectángulo a círculo."""
import pytest

from omnicad import api
from omnicad.nucleo import geometria as geo


def _ok(sesion, herramienta, **args):
    r = api.llamar(sesion, herramienta, args)
    assert r["ok"], r.get("mensaje", r)
    return r["result"]


def _pieza(superficie):
    s = api.Sesion()
    _ok(s, "create_sketch", plane="XY", name="Boceto1")
    _ok(s, "draw_rectangle", center_x=0, center_y=0, width=80, height=36, center_diagonals=True)
    _ok(s, "create_construction_plane", plane="XY", offset=83.38, name="Plano1")
    _ok(s, "create_sketch", plane="Plano1", name="Boceto2")
    _ok(s, "draw_circle", center_x=0, center_y=0, radius=42)
    perfiles = [{"sketch": nombre, "profile": 0} for nombre in ("Boceto1", "Boceto2")]
    if superficie:
        r = _ok(s, "create_surface_loft", profiles=perfiles)
    else:
        r = _ok(s, "loft", sections=perfiles)
    return s, r["bodies_created"][0]["id"]


@pytest.mark.xfail(strict=True, reason="B-633", raises=pytest.RaisesExc(AssertionError, match="«Engrosar1»"))
def test_engrosar_solevacion():
    s, cid = _pieza(superficie=True)
    r = _ok(s, "thicken", faces=cid, thickness=2)
    forma = s.cuerpo(r["bodies_created"][0]["id"]).forma
    assert len(geo.solidos(forma)) == 1 and geo.es_valida(forma) and geo.volumen_exacto(forma) > 0


@pytest.mark.xfail(strict=True, reason="B-634", raises=pytest.RaisesExc(AssertionError, match="«Vaciado1»"))
def test_vaciar_tapa_circular():
    s, cid = _pieza(superficie=False)
    antes = geo.volumen_exacto(s.cuerpo(cid).forma)
    _ok(s, "shell", body=cid, faces="+Z", thickness=1, direction="inside")
    forma = s.cuerpo(cid).forma
    assert geo.es_valida(forma) and 0 < geo.volumen_exacto(forma) < antes

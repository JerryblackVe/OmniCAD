"""SOL-8: barrido con orientación alineada y superficie guía."""
import math

import pytest

from omnicad import api
from omnicad.nucleo import geometria as geo


def llamar(sesion, nombre, **args):
    r = api.llamar(sesion, nombre, args)
    assert r["ok"], r
    return r["result"]


def _anillo(**extra):
    """Un cilindro de radio 10 y un circulito de radio 1 barrido por su arista superior."""
    s = api.Sesion()
    llamar(s, "create_cylinder", radius=10, height=10, name="Cil")
    llamar(s, "create_sketch", plane="XZ", name="Perfil")
    llamar(s, "draw_circle", radius=1, center_x=10, center_y=10, sketch="Perfil")
    r = api.llamar(s, "sweep", {"sketch": "Perfil", "path_edges": "%CIRCLE and >Z", "body": "Cil", "operation": "new_body",
                                **extra})
    return s, r


def test_alineada_con_el_eje_binormal_da_el_mismo_toro():
    s0, r0 = _anillo()
    assert r0["ok"], r0
    s1, r1 = _anillo(orientation="aligned", align_axis="Z")
    assert r1["ok"], r1
    v0 = geo.volumen(s0.doc.estado_final.cuerpos["op4.c1"].forma) if "op4.c1" in s0.doc.estado_final.cuerpos else None
    cuerpos0 = [c for c in s0.doc.estado_final.cuerpos.values() if c.nombre != "Cil"]
    cuerpos1 = [c for c in s1.doc.estado_final.cuerpos.values() if c.nombre != "Cil"]
    toro = 2 * math.pi * 10 * math.pi
    assert v0 is None or v0 > 0
    assert geo.volumen(cuerpos0[0].forma) == pytest.approx(toro, rel=1e-2)
    assert geo.volumen(cuerpos1[0].forma) == pytest.approx(toro, rel=1e-2)


def test_superficie_guia_en_una_ruta_apoyada_en_ella():
    s, r = _anillo(guide_surface="%CYLINDER")
    assert r["ok"], r
    nuevo = [c for c in s.doc.estado_final.cuerpos.values() if c.nombre != "Cil"]
    assert geo.volumen(nuevo[0].forma) == pytest.approx(2 * math.pi * 10 * math.pi, rel=1e-2)


def test_errores():
    s, _ = _anillo()
    for args in ({"orientation": "aligned"},                                       # sin eje
                 {"guide_surface": "%CYLINDER", "twist_angle": 10},                # con torsión
                 {"orientation": "aligned", "align_axis": "no existe"}):
        r = api.llamar(s, "sweep", {"sketch": "Perfil", "path_edges": "%CIRCLE and >Z", "body": "Cil", **args})
        assert not r["ok"], args

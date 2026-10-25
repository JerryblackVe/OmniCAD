"""SOL-9: solevación con condiciones de borde de dirección y unión de aristas tangentes."""
import math

import pytest

from omnicad import api
from omnicad.nucleo import geometria as geo


def llamar(sesion, nombre, **args):
    r = api.llamar(sesion, nombre, args)
    assert r["ok"], r
    return r["result"]


def _dos_circulos():
    s = api.Sesion()
    llamar(s, "create_sketch", plane="XY", name="Base")
    llamar(s, "draw_circle", radius=10, sketch="Base")
    plano = llamar(s, "create_construction_plane", plane="XY", offset=30)["plane"]["id"]
    llamar(s, "create_sketch", plane=plano, name="Tapa")
    llamar(s, "draw_circle", radius=10, sketch="Tapa")
    return s


def _volumen(s):
    (c,) = s.doc.estado_final.cuerpos.values()
    assert geo.es_valida(c.forma)
    return geo.volumen(c.forma)


def test_sin_condiciones_es_un_cilindro():
    s = _dos_circulos()
    llamar(s, "loft", sketches=["Base", "Tapa"])
    assert _volumen(s) == pytest.approx(math.pi * 100 * 30, rel=1e-3)


def test_condicion_de_direccion_abre_o_cierra_la_superficie():
    abierta, cerrada = _dos_circulos(), _dos_circulos()
    llamar(abierta, "loft", sketches=["Base", "Tapa"], start_condition={"type": "direction", "angle": 45})
    llamar(cerrada, "loft", sketches=["Base", "Tapa"], start_condition={"type": "direction", "angle": 135})
    cilindro = math.pi * 100 * 30
    assert _volumen(abierta) > cilindro > _volumen(cerrada) > 0                 # <90: se ensancha; >90: se angosta


def test_condicion_libre_y_peso():
    s, t = _dos_circulos(), _dos_circulos()
    llamar(s, "loft", sketches=["Base", "Tapa"], end_condition={"type": "free"})
    assert _volumen(s) == pytest.approx(math.pi * 100 * 30, rel=1e-3)
    llamar(t, "loft", sketches=["Base", "Tapa"], end_condition={"type": "direction", "angle": 60, "weight": 2},
           merge_tangent_edges=True)
    assert _volumen(t) > math.pi * 100 * 30


def test_errores():
    s = _dos_circulos()
    for args in ({"start_condition": {"type": "tangent"}}, {"start_condition": {"type": "direction", "angle": 200}},
                 {"start_condition": {"type": "direction", "weight": 0}}, {"start_condition": {"clase": "x"}},
                 {"start_condition": {"type": "direction"}, "ruled": True}):
        r = api.llamar(s, "loft", {"sketches": ["Base", "Tapa"], **args})
        assert not r["ok"], args


def _radio_a(forma, z):
    """Radio de la sección circular del sólido a la altura z (por el volumen de una lonja fina)."""
    lonja = geo.booleano(forma, geo.caja(100, 100, 0.2, (-50, -50, z)), "intersecar")
    return math.sqrt(geo.volumen(lonja) / 0.2 / math.pi)


def _cilindro_y_circulo_grande():
    s = api.Sesion()
    llamar(s, "create_cylinder", radius=10, height=10, name="Cil")
    plano = llamar(s, "create_construction_plane", plane="XY", offset=30)["plane"]["id"]
    llamar(s, "create_sketch", plane=plano, name="Tapa")
    llamar(s, "draw_circle", radius=20, sketch="Tapa")
    return s


def test_condicion_tangente_sale_siguiendo_la_cara():
    libre, tangente = _cilindro_y_circulo_grande(), _cilindro_y_circulo_grande()
    seccion = {"sketch": "Tapa", "profile": 0}
    borde = "edges:%CIRCLE and >Z"
    llamar(libre, "loft", sections=[borde, seccion], body="Cil", operation="new_body")
    llamar(tangente, "loft", sections=[borde, seccion], body="Cil", operation="new_body",
           start_condition={"type": "tangent", "face": "%CYLINDER", "weight": 1})
    f_libre = [c for c in libre.doc.estado_final.cuerpos.values() if c.nombre != "Cil"][0].forma
    f_tang = [c for c in tangente.doc.estado_final.cuerpos.values() if c.nombre != "Cil"][0].forma
    assert geo.es_valida(f_tang)
    assert _radio_a(f_libre, 12) == pytest.approx(10 + 2 * 10 / 20, abs=0.6)     # el cono sube 0,5 mm por mm
    assert _radio_a(f_tang, 12) == pytest.approx(10, abs=0.6)                    # la tangente sigue vertical
    assert geo.volumen(f_tang) < geo.volumen(f_libre)


def test_tangente_sin_cara_o_suave_fallan_con_mensaje():
    s = _dos_circulos()
    r = api.llamar(s, "loft", {"sketches": ["Base", "Tapa"], "start_condition": {"type": "tangent"}})
    assert not r["ok"] and "face" in r["mensaje"]
    r = api.llamar(s, "loft", {"sketches": ["Base", "Tapa"], "start_condition": {"type": "smooth"}})
    assert not r["ok"] and "G2" in r["mensaje"]


def test_direccion_en_una_seccion_intermedia():
    s = api.Sesion()
    for nombre, z, radio in (("A", 0, 10), ("B", 20, 10), ("C", 40, 10)):
        plano = "XY" if z == 0 else llamar(s, "create_construction_plane", plane="XY", offset=z)["plane"]["id"]
        llamar(s, "create_sketch", plane=plano, name=nombre)
        llamar(s, "draw_circle", radius=radio, sketch=nombre)
    llamar(s, "loft", sketches=["A", "B", "C"], section_conditions={"2": {"type": "direction", "angle": 45}})
    (c,) = s.doc.estado_final.cuerpos.values()
    assert geo.es_valida(c.forma)
    recto = math.pi * 100 * 40
    assert geo.volumen(c.forma) != pytest.approx(recto, rel=1e-3)                # la sección del medio cambia la forma
    assert _radio_a(c.forma, 20) == pytest.approx(10, abs=0.5)                   # y sigue pasando por ella
    r = api.llamar(s, "loft", {"sketches": ["A", "B", "C"], "section_conditions": {"1": {"type": "direction"}}})
    assert not r["ok"] and r["error_kind"] == "INVALID_ARGUMENTS"


def test_tangente_con_un_selector_de_varias_caras_falla():
    s = _cilindro_y_circulo_grande()
    r = api.llamar(s, "loft", {"sections": ["edges:%CIRCLE and >Z", {"sketch": "Tapa", "profile": 0}], "body": "Cil",
                               "operation": "new_body", "start_condition": {"type": "tangent", "face": "all"}})
    assert not r["ok"] and "UNA cara" in r["mensaje"], r

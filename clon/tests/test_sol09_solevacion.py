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

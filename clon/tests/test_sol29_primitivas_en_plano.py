"""SOL-29: primitivas creadas sobre un plano o una cara cualquiera (también inclinada)."""
import math

import numpy as np
import pytest

from omnicad import api
from omnicad.nucleo import geometria as geo

N = np.array([1.0, 0.0, 1.0]) / math.sqrt(2)         # normal de la cara a 45°
CENTRO_CARA = np.array([5.0, 0.0, 15.0])
CARA = "nearest:[5,0,15]"
Y_LOCAL = math.sqrt(50)                              # distancia del origen del plano al centro de la cara, en su eje v


def llamar(sesion, nombre, **args):
    r = api.llamar(sesion, nombre, args)
    assert r["ok"], r
    return r["result"]


def _cuña():
    s = api.Sesion()
    llamar(s, "create_box", length=20, width=20, height=20, name="Base")
    arista = llamar(s, "find_edges", body="Base", selector="nearest:[10,0,20]")["edges"][0]["id"]
    llamar(s, "chamfer", edges=arista, distance=10)       # cara inclinada a 45° con centro en (5, 0, 15)
    return s


def _ultimo(s):
    return list(s.doc.estado_final.cuerpos.values())[-1].forma


def test_cilindro_sobre_una_cara_inclinada_crece_por_su_normal():
    s = _cuña()
    llamar(s, "create_cylinder", radius=1, height=5, plane=CARA, body="Base", x=0, y=Y_LOCAL, name="Perno")
    forma = _ultimo(s)
    assert geo.es_valida(forma) and geo.volumen(forma) == pytest.approx(math.pi * 5, rel=1e-6)
    assert np.allclose(geo.centro_masa(forma), CENTRO_CARA + N * 2.5, atol=1e-6)


def test_caja_esfera_y_toroide_sobre_la_cara():
    s = _cuña()
    llamar(s, "create_box", length=4, width=2, height=6, plane=CARA, body="Base", y=Y_LOCAL, name="Taco")
    forma = _ultimo(s)
    assert geo.volumen(forma) == pytest.approx(48, rel=1e-6)
    assert np.allclose(geo.centro_masa(forma), CENTRO_CARA + N * 3, atol=1e-6)
    llamar(s, "create_sphere", radius=2, plane=CARA, body="Base", y=Y_LOCAL, z=3, name="Bola")
    assert np.allclose(geo.centro_masa(_ultimo(s)), CENTRO_CARA + N * 3, atol=1e-6)
    llamar(s, "create_torus", major_radius=4, minor_radius=1, plane=CARA, body="Base", y=Y_LOCAL, z=5, name="Aro")
    forma = _ultimo(s)
    assert geo.volumen(forma) == pytest.approx(2 * math.pi ** 2 * 4, rel=1e-6)
    assert np.allclose(geo.centro_masa(forma), CENTRO_CARA + N * 5, atol=1e-6)


def test_deshacer_quita_el_cuerpo():
    s = _cuña()
    llamar(s, "create_cylinder", radius=1, height=5, plane=CARA, body="Base", x=0, y=Y_LOCAL, name="Perno")
    llamar(s, "undo")
    assert len(s.doc.estado_final.cuerpos) == 1


def test_plano_de_construccion_y_errores():
    s = api.Sesion()
    llamar(s, "create_cylinder", radius=1, height=5, plane="XZ", name="Horizontal")     # eje por la normal del plano XZ
    forma = _ultimo(s)
    c = np.array(geo.centro_masa(forma))
    assert abs(abs(c[1]) - 2.5) < 1e-6 and abs(c[0]) < 1e-6 and abs(c[2]) < 1e-6
    r = api.llamar(s, "create_box", {"length": 1, "width": 1, "height": 1, "plane": "X"})   # un eje no es un plano
    assert not r["ok"]

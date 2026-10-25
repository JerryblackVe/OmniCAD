"""SOL-19: volumen de fluido interno y externo, con tapas y caras separadas."""
import math

import pytest

from omnicad import api
from omnicad.nucleo import geometria as geo


def llamar(sesion, nombre, **args):
    r = api.llamar(sesion, nombre, args)
    assert r["ok"], r
    return r["result"]


def _cuerpo_nuevo(s):
    return list(s.doc.estado_final.cuerpos.values())[-1]


def _caja_hueca_cerrada():
    s = api.Sesion()
    llamar(s, "create_box", length=40, width=40, height=40, name="Caja")
    llamar(s, "shell", body="Caja", faces=[], thickness=5)
    return s


def test_volumen_interno_de_una_caja_hueca():
    s = _caja_hueca_cerrada()
    llamar(s, "create_fluid_volume", bodies=["Caja"])
    forma = _cuerpo_nuevo(s).forma
    assert geo.es_valida(forma)
    assert geo.volumen(forma) == pytest.approx(30 ** 3, rel=1e-4)
    assert len(s.doc.estado_final.componentes) == 1
    assert len(geo.caras(forma)) == 6


def test_externo_resta_el_modelo_y_el_hueco():
    s = _caja_hueca_cerrada()
    llamar(s, "create_fluid_volume", bodies=["Caja"], volume_type="external", margin=10)
    forma = _cuerpo_nuevo(s).forma
    assert geo.es_valida(forma)
    assert geo.volumen(forma) == pytest.approx(60 ** 3 - 40 ** 3, rel=1e-4)


def test_externo_cilindro_y_semiesfera():
    s = api.Sesion()
    llamar(s, "create_box", length=10, width=10, height=10, name="Bloque")
    llamar(s, "create_fluid_volume", bodies=["Bloque"], volume_type="external", outer_shape="cylinder", margin=5)
    radio = math.hypot(10, 10) / 2 + 5
    assert geo.volumen(_cuerpo_nuevo(s).forma) == pytest.approx(math.pi * radio ** 2 * 20 - 1000, rel=1e-3)
    llamar(s, "create_fluid_volume", bodies=["Bloque"], volume_type="external", outer_shape="hemisphere", margin=5)
    r = math.dist((5, 5, 0), (0, 0, 10)) + 5
    assert geo.volumen(_cuerpo_nuevo(s).forma) == pytest.approx(2 / 3 * math.pi * r ** 3 - 1000, rel=1e-3)


def test_interior_abierto_falla_y_con_tapa_anda():
    s = api.Sesion()
    llamar(s, "create_box", length=40, width=40, height=40, name="Caja")
    llamar(s, "shell", body="Caja", faces=[">Z"], thickness=5)        # vaso abierto arriba
    r = api.llamar(s, "create_fluid_volume", {"bodies": ["Caja"]})
    assert not r["ok"] and "aberturas" in r["mensaje"]
    # la tapa: un rectángulo del tamaño de la boca interior, convertido en parche, a z = 40
    llamar(s, "create_construction_plane", plane="XY", offset=40, name="Boca")
    llamar(s, "create_sketch", plane="Boca", name="Tapa")
    llamar(s, "draw_rectangle", x1=-15, y1=-15, x2=15, y2=15)
    tapa = llamar(s, "create_patch", boundary={"sketch": "Tapa", "profile": 0})
    nombre = tapa["bodies_created"][0]["id"]
    assert s.cuerpo(nombre).tipo == "superficie"
    llamar(s, "create_fluid_volume", bodies=["Caja"], caps=[nombre])
    forma = _cuerpo_nuevo(s).forma
    assert geo.es_valida(forma)
    assert geo.volumen(forma) == pytest.approx(30 * 30 * 35, rel=1e-3)

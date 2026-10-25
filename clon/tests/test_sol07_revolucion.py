"""SOL-7: revolución «A objeto» y Proyectar eje."""
import math

import pytest

from omnicad import api
from omnicad.nucleo import geometria as geo


def llamar(sesion, nombre, **args):
    r = api.llamar(sesion, nombre, args)
    assert r["ok"], r
    return r["result"]


def _perfil(x1=10, x2=20):
    """Rectángulo en el plano XZ (x de x1 a x2, z de 0 a 5) que gira alrededor del eje Z, desde +X hacia +Y."""
    s = api.Sesion()
    llamar(s, "create_sketch", plane="XZ", name="Perfil")
    llamar(s, "draw_rectangle", x1=x1, y1=0, x2=x2, y2=5)
    return s


def _cuerpo(s):
    return list(s.doc.estado_final.cuerpos.values())[-1]


def _sector(grados, r1=10, r2=20):
    return math.pi * (r2 ** 2 - r1 ** 2) * 5 * grados / 360


def test_hasta_un_plano_que_contiene_el_eje():
    s = _perfil()
    llamar(s, "revolve", sketch="Perfil", axis="z", to_object="YZ")
    forma = _cuerpo(s).forma
    assert geo.es_valida(forma)
    assert geo.volumen(forma) == pytest.approx(_sector(90), rel=1e-4)
    r = api.llamar(s, "revolve", {"sketch": "Perfil", "axis": "z", "to_object": "YZ", "direction": "symmetric"})
    assert not r["ok"] and r["error_kind"] == "INVALID_ARGUMENTS"


def test_hasta_un_vertice():
    s = api.Sesion()
    llamar(s, "create_box", length=10, width=10, height=10, name="Tope")          # esquinas en (±5, ±5)
    llamar(s, "create_sketch", plane="XZ", name="Perfil")
    llamar(s, "draw_rectangle", x1=20, y1=0, x2=30, y2=5)
    llamar(s, "revolve", sketch="Perfil", axis="z", to_object=[5, 5, 10], operation="new_body")
    assert geo.volumen(_cuerpo(s).forma) == pytest.approx(_sector(45, 20, 30), rel=1e-4)


def test_hasta_un_cuerpo_gira_hasta_el_primer_contacto():
    s = _perfil()
    llamar(s, "create_box", length=4, width=4, height=10, x=0, y=15, name="Poste")   # x ±2, y 13..17
    llamar(s, "revolve", sketch="Perfil", axis="z", to_object="Poste", operation="new_body")
    forma = _cuerpo(s).forma
    assert geo.es_valida(forma)
    assert geo.volumen(forma) == pytest.approx(_sector(math.degrees(math.atan2(13, 2))), rel=5e-3)


def test_el_plano_del_propio_perfil_lleva_a_media_vuelta():
    s = _perfil()
    llamar(s, "revolve", sketch="Perfil", axis="z", to_object="XZ")        # el semiplano opuesto está a 180°
    assert geo.volumen(_cuerpo(s).forma) == pytest.approx(_sector(180), rel=1e-4)


def test_proyectar_eje_lleva_un_eje_inclinado_al_plano_del_perfil():
    s = _perfil()
    llamar(s, "create_sketch", plane="YZ", name="Eje")
    llamar(s, "draw_line", start_x=0, start_y=0, end_x=20, end_y=10)           # dirección (0, 20, 10): inclinado respecto del plano
    eje = {"sketch": "Eje", "curve": 3}
    llamar(s, "revolve", sketch="Perfil", axis=eje, project_axis=True)
    assert geo.volumen(_cuerpo(s).forma) == pytest.approx(_sector(360), rel=1e-4)
    llamar(s, "revolve", sketch="Perfil", axis=eje)
    assert abs(geo.volumen(_cuerpo(s).forma) - _sector(360)) > 0.005 * _sector(360)


def test_hasta_un_plano_que_no_contiene_el_eje_recorta_y_exige_que_todo_el_perfil_llegue():
    from scipy.integrate import quad
    s = _perfil()
    llamar(s, "create_construction_plane", plane="XZ", offset=-8, name="Pared")      # la normal de XZ es −Y: y = 8: lo alcanza todo el perfil (r ≥ 10)
    llamar(s, "revolve", sketch="Perfil", axis="z", to_object="Pared", operation="new_body")
    esperado = 5 * quad(lambda r: r * math.asin(8 / r), 10, 20)[0]
    assert geo.volumen(_cuerpo(s).forma) == pytest.approx(esperado, rel=5e-3)
    # y = 13: el borde interno (r = 10) nunca llega, el resultado ya no depende del muestreo: es un error claro
    llamar(s, "create_construction_plane", plane="XZ", offset=-13, name="Lejos")
    r = api.llamar(s, "revolve", {"sketch": "Perfil", "axis": "z", "to_object": "Lejos", "operation": "new_body"})
    assert not r["ok"] and "nunca llega" in r["mensaje"]

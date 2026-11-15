"""B-385: extensión del barrido, punto tangente y opciones del nervio desde MCP/CLI."""
import math

import pytest

from omnicad import api
from omnicad.nucleo import geometria as geo


def _llamar(s, nombre, **args):
    r = api.llamar(s, nombre, args)
    assert r["ok"], (nombre, args, r)
    return r["result"]


def _barrido():
    s = api.Sesion()
    _llamar(s, "create_sketch", plane="XY", name="Perfil")
    _llamar(s, "draw_circle", radius=2)
    _llamar(s, "create_sketch", plane="XZ", name="Ruta")
    _llamar(s, "draw_line", start_x=0, start_y=0, end_x=0, end_y=10)
    _llamar(s, "create_sketch", plane="XZ", name="Carril")
    _llamar(s, "draw_line", start_x=5, start_y=0, end_x=5, end_y=6)
    return s


def _forma_creada(s, nombre, **args):
    r = _llamar(s, nombre, **args)
    forma = s.cuerpo(r["bodies_created"][0]["id"]).forma
    assert geo.es_valida(forma)
    return forma


def test_sweep_extension_perpendicular_por_defecto_y_completa():
    s = _barrido()
    args = {"sketch": "Perfil", "path_sketch": "Ruta", "rail_sketch": "Carril"}
    por_defecto = _forma_creada(s, "sweep", **args)
    perpendicular = _forma_creada(s, "sweep", **args, extent="perpendicular")
    completa = _forma_creada(s, "sweep", **args, extent="full")
    assert geo.volumen(por_defecto) == pytest.approx(math.pi * 4 * 6, rel=1e-4)
    assert geo.volumen(perpendicular) == pytest.approx(geo.volumen(por_defecto), rel=1e-6)
    assert geo.caja_envolvente(perpendicular)[1][2] == pytest.approx(6, abs=1e-5)
    assert geo.volumen(completa) == pytest.approx(152.47, abs=0.02)
    assert geo.volumen(completa) > geo.volumen(perpendicular)
    assert geo.caja_envolvente(completa)[1][2] == pytest.approx(10, abs=1e-5)


def test_sweep_distancia_carril_acepta_expresion_y_cambia_el_volumen():
    s = _barrido()
    args = {"sketch": "Perfil", "path_sketch": "Ruta", "rail_sketch": "Carril", "extent": "full"}
    completa = _forma_creada(s, "sweep", **args, rail_distance=1)
    mitad = _forma_creada(s, "sweep", **args, rail_distance="1 / 2")
    assert geo.volumen(mitad) == pytest.approx(207.76, abs=0.02)
    assert geo.volumen(mitad) > geo.volumen(completa)
    assert s.doc.operaciones[-1].p["distancia_carril"] == "1 / 2"


@pytest.mark.parametrize("distancia", [0, -0.1, 1.1, "0", "3 / 2"])
def test_sweep_rechaza_distancia_carril_fuera_de_rango(distancia):
    s = _barrido()
    pasos = len(s.doc.operaciones)
    r = api.llamar(s, "sweep", {"sketch": "Perfil", "path_sketch": "Ruta", "rail_sketch": "Carril",
                               "extent": "full", "rail_distance": distancia})
    assert not r["ok"] and r["error_kind"] == "INVALID_ARGUMENTS", r
    assert "rail_distance" in r["mensaje"] and "mayor que 0 y hasta 1" in r["mensaje"]
    assert len(s.doc.operaciones) == pasos


@pytest.mark.parametrize("distancia", [0, "parametro_inexistente"])
def test_sweep_sin_carril_ignora_extension_y_distancia(distancia):
    s = _barrido()
    forma = _forma_creada(s, "sweep", sketch="Perfil", path_sketch="Ruta", extent="full", rail_distance=distancia)
    assert geo.volumen(forma) == pytest.approx(math.pi * 4 * 10, rel=1e-4)


def _secciones():
    s = api.Sesion()
    _llamar(s, "create_sketch", plane="XY", name="Base")
    _llamar(s, "draw_circle", radius=10)
    _llamar(s, "create_sketch", plane="XZ", name="Punta")
    punto = _llamar(s, "draw_point", x=0, y=10)["points"][0]
    return s, [{"sketch": "Base", "profile": 0}, {"sketch": "Punta", "point": punto}]


@pytest.mark.parametrize("extremo", ["start_condition", "end_condition"])
def test_loft_punto_tangente_hace_cupula_en_cualquiera_de_los_extremos(extremo):
    s, secciones = _secciones()
    if extremo == "start_condition":
        secciones.reverse()
    cono = _forma_creada(s, "loft", sections=secciones)
    cupula = _forma_creada(s, "loft", sections=secciones, **{extremo: {"type": "point_tangent", "weight": 1}})
    assert geo.volumen(cono) == pytest.approx(math.pi * 100 * 10 / 3, rel=1e-4)
    assert geo.volumen(cupula) == pytest.approx(1570.8, rel=1e-3)   # B-464: la cúpula exacta de Fusion


@pytest.mark.parametrize("extremo", ["start_condition", "end_condition"])
def test_loft_punto_tangente_rechaza_extremo_que_no_es_punto(extremo):
    s, secciones = _secciones()
    if extremo == "end_condition":
        secciones.reverse()
    pasos = len(s.doc.operaciones)
    r = api.llamar(s, "loft", {"sections": secciones, extremo: {"type": "point_tangent"}})
    assert not r["ok"] and r["error_kind"] == "INVALID_ARGUMENTS", r
    assert "point_tangent" in r["mensaje"] and "es un punto" in r["mensaje"]
    assert len(s.doc.operaciones) == pasos


def test_loft_punto_tangente_no_se_admite_en_seccion_intermedia():
    s, secciones = _secciones()
    r = api.llamar(s, "loft", {"sections": [secciones[0], secciones[0], secciones[1]],
                              "section_conditions": {"2": {"type": "point_tangent"}}})
    assert not r["ok"] and r["error_kind"] == "INVALID_ARGUMENTS", r
    assert "section_conditions solo admite free y direction" in r["mensaje"]


def _nervio(**args):
    s = api.Sesion()
    cuerpo = _llamar(s, "create_box", length=40, width=20, height=20, anchor="corner")["bodies_created"][0]["id"]
    _llamar(s, "create_box", length=36, width=20, height=18, x=2, z=2, anchor="corner", operation="cut", target=cuerpo)
    if args.get("fillet_radius") == "":
        _llamar(s, "create_component", bodies=[cuerpo], name="Canal")
        _llamar(s, "assign_plastic_rule", component="Canal", rule="ABS 2 mm")
    _llamar(s, "create_construction_plane", plane="XZ", offset=-10, name="Plano nervio")
    _llamar(s, "create_sketch", plane="Plano nervio", name="Perfil")
    _llamar(s, "draw_line", start_x=10, start_y=8, end_x=30, end_y=8)
    _llamar(s, "create_rib", sketch="Perfil", thickness=2, target=cuerpo, **args)
    forma = s.cuerpo(cuerpo).forma
    assert geo.es_valida(forma)
    return forma


@pytest.mark.parametrize("radio", [1, "1 mm", ""])
def test_create_rib_radio_empalme_suma_material(radio):
    sin_empalme = _nervio(draft_angle=0, fillet_radius="0 mm")
    con_empalme = _nervio(draft_angle=0, fillet_radius=radio)
    assert geo.volumen(sin_empalme) == pytest.approx(40 * 20 * 20 - 36 * 20 * 18 + 36 * 6 * 2, rel=1e-5)
    assert geo.volumen(con_empalme) > geo.volumen(sin_empalme) + 1


def test_create_rib_invertir_extraccion_cambia_desmoldeo():
    normal = _nervio(draft_angle=3)
    invertido = _nervio(draft_angle=3, flip_draft_direction=True)
    assert abs(geo.volumen(normal) - geo.volumen(invertido)) > 1

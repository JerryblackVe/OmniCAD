"""Sólidos avanzados: geometría numérica, referencias persistentes y transacciones."""
import math

import numpy as np
import pytest

from omnicad import api
from omnicad.nucleo import geometria as geo
from omnicad.timeline.ops_superficie import OpSupExtruir


def _ok(s, nombre, **args):
    r = api.llamar(s, nombre, args)
    assert r["ok"], r
    return r["result"]


def _caja(s, **args):
    return _ok(s, "create_box", length=40, width=20, height=20, anchor="corner", **args)["bodies_created"][0]["id"]


def _boceto(s, plano="XY", offset=None):
    if offset is not None:
        _ok(s, "create_construction_plane", plane=plano, offset=offset, name="Plano de prueba")
        plano = "Plano de prueba"
    return _ok(s, "create_sketch", plane=plano)["sketch"]["id"]


def _linea(s, sketch, x1, y1, x2, y2):
    _ok(s, "draw_line", sketch=sketch, start_x=x1, start_y=y1, end_x=x2, end_y=y2)


def _volumen(s, cid, esperado):
    forma = s.cuerpo(cid).forma
    assert geo.es_valida(forma)
    assert geo.volumen(forma) == pytest.approx(esperado, rel=1e-5, abs=1e-5)


def _canal(s):
    cid = _caja(s)
    _ok(s, "create_box", length=36, width=20, height=18, x=2, z=2, anchor="corner", operation="cut", target=cid)
    return cid


def _tipo(s, resultado, tipo):
    assert resultado["feature"]["type"] == tipo
    assert s.paso(resultado["feature"]["id"]).TIPO == tipo


def test_create_coil():
    s = api.Sesion()
    r = _ok(s, "create_coil", coil_type="revolutions_pitch", diameter=20, revolutions=2, pitch=6,
            section="square", section_size=2)
    _tipo(s, r, "bobina")
    cid = r["bodies_created"][0]["id"]
    forma = s.cuerpo(cid).forma
    assert geo.es_valida(forma)
    # El cuadrado está inscrito en el círculo de diámetro section_size.
    # La trayectoria sube N·p y la sección agrega section_size/√2 a la caja.
    caja = geo.caja_envolvente(forma)
    assert caja[1][2] - caja[0][2] == pytest.approx(2 * 6 + math.sqrt(2), abs=1e-4)


def test_referencias_por_nombre_siguen_andando_con_un_scu_en_el_documento():
    """Un SCU deja ids de plano, eje y punto que no son pasos del timeline (op2_xy): resolver un nombre no los pisa."""
    s = api.Sesion()
    cid = _caja(s)
    _ok(s, "create_construction_plane", plane="XY", offset=30, name="Tapa")
    _ok(s, "create_ucs", origin="O")
    r = _ok(s, "create_coil", coil_type="revolutions_pitch", diameter=10, revolutions=1, pitch=4, section="square",
            section_size=1, plane="Tapa")
    assert r["bodies_created"]
    _ok(s, "scale_body", bodies=[cid], factor=1.5, point="O")
    assert geo.volumen(s.cuerpo(cid).forma) == pytest.approx(40 * 20 * 20 * 1.5 ** 3, rel=1e-5)


def test_create_pipe_hueco_y_limites():
    s = api.Sesion()
    b = _boceto(s, "XZ")
    _linea(s, b, 0, 0, 0, 30)
    r = _ok(s, "create_pipe", path_sketch=b, section_size=10, hollow=True, thickness=1)
    _tipo(s, r, "tuberia")
    _volumen(s, r["bodies_created"][0]["id"], math.pi * (25 - 16) * 30)
    r = _ok(s, "create_pipe", path_sketch=b, chain=False, start=0.25, end=0.75, section_size=2)
    _volumen(s, r["bodies_created"][0]["id"], math.pi * 15)


def test_create_pipe_arista_persistente():
    s = api.Sesion()
    cid = _caja(s)
    arista = _ok(s, "find_edges", body=cid, selector="|Z")["edges"][0]["id"]
    r = _ok(s, "create_pipe", edges=arista, chain=False, section_size=2)
    _volumen(s, r["bodies_created"][0]["id"], math.pi * 20)
    ruta = s.paso(r["feature"]["id"]).p["ruta"]
    assert ruta[0]["tipo"] == "arista" and "firma" in ruta[0]


@pytest.mark.parametrize("nombre,plano,offset,altura,aumento,tipo", [
    ("create_rib", "XZ", -10, 8, 36 * 6 * 2, "nervio"),
    ("create_web", "XY", 12, 10, 36 * 10 * 2, "red"),
])
def test_nervio_y_red(nombre, plano, offset, altura, aumento, tipo):
    s = api.Sesion()
    cid = _canal(s)
    inicial = geo.volumen(s.cuerpo(cid).forma)
    b = _boceto(s, plano, offset)
    _linea(s, b, 10, altura, 30, altura)
    r = _ok(s, nombre, sketch=b, thickness=2, target=cid)
    _tipo(s, r, tipo)
    _volumen(s, cid, inicial + aumento)


@pytest.mark.parametrize("modo,profundidad,signo", [("emboss", 1.5, 1), ("deboss", 1.5, -1),
                                                 ("emboss", -1.5, -1)])
def test_create_emboss(modo, profundidad, signo):
    s = api.Sesion()
    cid = _caja(s)
    b = _boceto(s, ">Z")
    _ok(s, "draw_rectangle", sketch=b, x1=5, y1=5, x2=15, y2=15)
    r = _ok(s, "create_emboss", sketch=b, faces=">Z", depth=profundidad, emboss_type=modo)
    _tipo(s, r, "repujado")
    _volumen(s, cid, 16000 + signo * 150)
    assert "firma" in s.paso(r["feature"]["id"]).p["caras"][0]


def test_create_boss():
    s = api.Sesion()
    cid = _caja(s)
    b = _boceto(s, ">Z")
    _ok(s, "draw_point", sketch=b, x=20, y=10)
    punto = next(iter(s.paso(b).boceto.puntos))
    r = _ok(s, "create_boss", positions=[{"sketch": b, "point": punto}],
            outer_diameter=8, hole_diameter=3, height=5)
    _tipo(s, r, "saliente")
    _volumen(s, cid, 16000 + math.pi * (16 - 2.25) * 5)


@pytest.mark.parametrize("modo,volumen", [("lip", 16000 + 40 * 1 * 1.5),
                                       ("groove", 16000 - 40 * 1.1 * 1.6)])
def test_create_lip_groove(modo, volumen):
    s = api.Sesion()
    cid = _caja(s)
    r = _ok(s, "create_lip_groove", body=cid, edges="|X and >Z and <Y", lip_type=modo,
            width=1, height=1.5, clearance=0.1, direction="Z")
    _tipo(s, r, "labio")
    _volumen(s, cid, volumen)
    assert "firma" in s.paso(r["feature"]["id"]).p["aristas"][0]


def test_create_boundary_fill():
    s = api.Sesion()
    cid = _caja(s)
    r = _ok(s, "create_boundary_fill", tools=[cid, "YZ"], cells=[1])
    _tipo(s, r, "relleno_contorno")
    _volumen(s, r["bodies_created"][0]["id"], 16000)


@pytest.mark.parametrize("forma,volumen", [("box", 42 * 22 * 22),
                                        ("cylinder", math.pi * (math.hypot(20, 10) + 1) ** 2 * 22)])
def test_create_bounding_solid(forma, volumen):
    s = api.Sesion()
    cid = _caja(s)
    r = _ok(s, "create_bounding_solid", bodies=cid, shape=forma, margin=1)
    _tipo(s, r, "solido_envolvente")
    _volumen(s, r["bodies_created"][0]["id"], volumen)


def test_thicken():
    s = api.Sesion()
    cid = _caja(s)
    r = _ok(s, "thicken", faces=">Z", body=cid, thickness=2, direction="symmetric")
    _tipo(s, r, "engrosar")
    _volumen(s, r["bodies_created"][0]["id"], 40 * 20 * 2)


def test_thicken_cuerpo_de_superficie():
    s = api.Sesion()
    b = _boceto(s)
    _linea(s, b, 0, 0, 10, 0)
    curva = next(iter(s.paso(b).boceto.curvas))
    # Preparación independiente del módulo de superficies que desarrolla otro ejecutor.
    op = OpSupExtruir(s.doc.nuevo_id(), "Superficie de prueba",
                      curvas=[{"tipo": "curva_boceto", "boceto": b, "curva": curva}], distancia="5 mm")
    s.doc.agregar(op)
    cid = next(iter(s.doc.estado_final.cuerpos))
    r = _ok(s, "thicken", faces=cid, thickness=2)
    _volumen(s, r["bodies_created"][0]["id"], 10 * 5 * 2)


def test_alinear_vertices_y_escalar_desde_vertice():
    s = api.Sesion()
    cid = _caja(s, x=10)
    r = _ok(s, "align_bodies", bodies=cid, source={"body": cid, "vertex": 1}, destination="O")
    _volumen(s, cid, 16000)
    ref = s.paso(r["feature"]["id"]).p["origen"]
    assert ref["tipo"] == "vertice" and "firma" in ref
    r = _ok(s, "scale_body", bodies=cid, factor=2, point={"body": cid, "vertex": 1})
    _volumen(s, cid, 16000 * 8)


@pytest.mark.parametrize("copiar", [False, True])
def test_align_bodies(copiar):
    s = api.Sesion()
    cid = _caja(s)
    otro = _caja(s, x=60)
    r = _ok(s, "align_bodies", bodies=cid, source="<X", source_body=cid,
            destination=">X", destination_body=otro, copy=copiar)
    _tipo(s, r, "alinear")
    movido = r["bodies_created"][0]["id"] if copiar else cid
    _volumen(s, movido, 16000)
    assert geo.caja_envolvente(s.cuerpo(movido).forma)[0][0] == pytest.approx(100)
    assert geo.caja_envolvente(s.cuerpo(otro).forma)[1][0] == pytest.approx(100)
    if copiar:
        assert geo.caja_envolvente(s.cuerpo(cid).forma)[0][0] == pytest.approx(0)


@pytest.mark.parametrize("opciones,factores", [({"factor": 2}, [2, 2, 2]),
    ({"scale_type": "non_uniform", "factor_x": 2, "factor_y": 3, "factor_z": 4}, [2, 3, 4])])
def test_scale_body_y_undo(opciones, factores):
    s = api.Sesion()
    cid = _caja(s)
    b = _boceto(s)
    _ok(s, "draw_point", sketch=b, x=5, y=6)
    punto = next(iter(s.paso(b).boceto.puntos))
    r = _ok(s, "scale_body", bodies=cid, point={"sketch": b, "point": punto}, **opciones)
    _tipo(s, r, "escala")
    _volumen(s, cid, 16000 * math.prod(factores))
    minimo, maximo = geo.caja_envolvente(s.cuerpo(cid).forma)
    assert np.subtract(maximo, minimo) == pytest.approx(np.array([40, 20, 20]) * factores)
    assert minimo == pytest.approx([5 * (1 - factores[0]), 6 * (1 - factores[1]), 0], abs=1e-6)
    _ok(s, "undo")
    _volumen(s, cid, 16000)
    assert r["feature"]["id"] not in [o.id for o in s.doc.operaciones]


@pytest.mark.parametrize("nombre,args", [
    ("create_coil", {"diameter": -1}),
    ("create_pipe", {"path_curves": [999]}),
    ("create_rib", {"sketch": "No existe"}),
    ("create_web", {"sketch": "No existe"}),
    ("create_emboss", {"sketch": "No existe", "faces": ">Z"}),
    ("create_boss", {"positions": []}),
    ("create_lip_groove", {"edges": ">Z", "height": -1}),
    ("create_boundary_fill", {"tools": "Caja", "cells": [0]}),
    ("create_bounding_solid", {"bodies": "No existe"}),
    ("thicken", {"faces": ">Z", "thickness": 0}),
    ("align_bodies", {"bodies": [], "source": "O", "destination": "O"}),
    ("scale_body", {"bodies": "Caja", "factor": 0}),
    ("scale_body", {"bodies": "Caja", "point": {"sketch": [], "point": 1}}),
    ("scale_body", {"bodies": "Caja", "point": {"body": [], "vertex": 1}}),
    ("scale_body", {"bodies": "Caja", "point": {"body": "Caja", "vertex": 0}}),
])
def test_errores_atomicos(nombre, args):
    s = api.Sesion()
    cid = _caja(s, name="Caja")
    pasos = len(s.doc.operaciones)
    r = api.llamar(s, nombre, args)
    assert not r["ok"], r
    assert r["error_kind"] in {"INVALID_ARGUMENTS", "SKETCH_NOT_FOUND", "BODY_NOT_FOUND", "OPERATION_FAILED", "INVALID_GEOMETRY"}, r
    assert len(s.doc.operaciones) == pasos
    _volumen(s, cid, 16000)


def test_catalogo_documentado():
    nombres = {"create_coil", "create_pipe", "create_rib", "create_web", "create_emboss", "create_boss",
               "create_lip_groove", "create_boundary_fill", "create_bounding_solid", "thicken", "align_bodies", "scale_body"}
    herramientas = [h for h in api.catalogo() if h["nombre"] in nombres]
    assert len(herramientas) == 12
    for h in herramientas:
        assert h["grupo"] == "solido" and h["modifica"]
        assert all(p.get("description") for p in h["esquema"]["properties"].values())

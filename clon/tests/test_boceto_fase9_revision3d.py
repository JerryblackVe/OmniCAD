# -*- coding: utf-8 -*-
"""Fase 9 · revisión del Boceto 3D: las curvas de Intersection Curve siguen al modelo una por una (por su índice en
el resultado), aunque se borre alguna o se repita la misma selección."""
import math

import numpy as np
import pytest

from omnicad import api


@pytest.fixture
def s():
    return api.Sesion()


def llamar(sesion, nombre, **args):
    r = api.llamar(sesion, nombre, args)
    assert r["ok"], r
    return r["result"]


def _xs(s, ids):
    """|x| de cada línea (las dos rectas del corte están en x = ±√(r² − 5²))."""
    e = {x["id"]: x for x in llamar(s, "get_sketch", sketch="Corte")["entities_3d"]}
    return sorted(abs(e[i]["start"][0]) for i in ids)


def _estado(s):
    return s.doc.resultados[next(k for k, op in enumerate(s.doc.operaciones) if op.nombre == "Corte")].estado


def _cilindro_y_plano(s):
    llamar(s, "create_parameter", name="r", expression="10 mm")
    llamar(s, "create_cylinder", radius="r", height=40, z=-20)
    plano = llamar(s, "create_construction_plane", plane="XZ", offset=5)["plane"]["id"]   # paralelo al eje
    llamar(s, "create_sketch", plane="XY", name="Corte")
    return plano


def test_borrar_una_de_las_dos_lineas_la_otra_sigue_al_modelo(s):
    plano = _cilindro_y_plano(s)
    a, b = llamar(s, "intersect_curves", faces=["%CYLINDER"], references=[plano])["entities"]
    assert _xs(s, [a, b]) == pytest.approx([math.sqrt(75)] * 2, abs=1e-3)
    llamar(s, "delete_sketch_entities_3d", entities=[a])
    llamar(s, "set_parameter", name="r", expression="15 mm")
    assert _xs(s, [b]) == pytest.approx([math.sqrt(200)], abs=1e-3)
    assert _estado(s) != "aviso"


def test_dos_llamadas_identicas_no_se_pisan(s):
    plano = _cilindro_y_plano(s)
    ids = [i for _ in range(2) for i in llamar(s, "intersect_curves", faces=["%CYLINDER"], references=[plano])["entities"]]
    llamar(s, "set_parameter", name="r", expression="15 mm")
    assert _xs(s, ids) == pytest.approx([math.sqrt(200)] * 4, abs=1e-3)
    assert _estado(s) != "aviso"
    e = {x["id"]: x for x in llamar(s, "get_sketch", sketch="Corte")["entities_3d"]}
    assert sorted(e[i]["source"]["index"] for i in ids) == [0, 0, 1, 1]
    assert np.sign(e[ids[0]]["start"][0]) == np.sign(e[ids[2]]["start"][0])   # mismo índice, misma recta

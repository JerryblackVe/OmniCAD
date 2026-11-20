# -*- coding: utf-8 -*-
"""PREP: opción «Pivote de giro (6 opciones)» del panel «Carácter» del boceto.

El pivote es el punto que no se mueve al girar el texto (ancla o una de las 5 esquinas/centro del marco).
Se prueba un valor numérico (girar 30° deja el pivote donde estaba) y el borde de un pivote inválido
(no existe esa esquina: la operación es atómica y no cambia el boceto)."""
import math

import pytest

from omnicad import api

# Fusion: el texto con marco gira alrededor del punto elegido (Text dialog, sin pivote fijo en la ayuda pública);
# OmniCAD lo resuelve en restricciones/boceto_texto.py (girar_texto + esquina_marco).


def ok(s, nombre, **args):
    r = api.llamar(s, nombre, args)
    assert r["ok"], r
    return r["result"]


def boceto():
    s = api.Sesion()
    ok(s, "create_sketch", plane="XY", name="B")
    return s


def resuelto(s):
    from omnicad.api.herramientas_boceto import boceto_activo
    return boceto_activo(s, None)[1].boceto


PIVOTES = [None, "corner:tl", "corner:tr", "corner:bl", "corner:br", "corner:center"]


def test_cada_pivote_gira_30_grados_y_no_se_mueve():
    s = boceto()
    tid = ok(s, "add_text", text="I", frame=True, box_width=40, frame_height=10, x=10, y=20)["entities"][0]["id"]
    for pivot in PIVOTES:
        ok(s, "edit_text", entity=tid, angle=0, pivot=pivot)
        b = resuelto(s)
        if pivot is None:
            antes = b.coords(b.curvas[tid].punto)
        else:
            antes = b.esquina_marco(tid, pivot.removeprefix("corner:"))
        ok(s, "edit_text", entity=tid, angle=30, pivot=pivot)
        b = resuelto(s)
        if pivot is None:
            despues = b.coords(b.curvas[tid].punto)
        else:
            despues = b.esquina_marco(tid, pivot.removeprefix("corner:"))
        assert b.angulo_texto(tid) == pytest.approx(30)
        assert math.dist(antes, despues) < 1e-6


def test_pivote_invalido_es_atomico():
    s = boceto()
    tid = ok(s, "add_text", text="I", frame=True, box_width=40, frame_height=10, x=10, y=20)["entities"][0]["id"]
    antes = s.doc.a_dict()
    r = api.llamar(s, "edit_text", {"entity": tid, "angle": 45, "pivot": "corner:otra"})
    assert not r["ok"]
    assert s.doc.a_dict() == antes

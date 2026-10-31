# -*- coding: utf-8 -*-
"""Herramientas MCP/CLI de patrones con las opciones nuevas: simetría por dirección, copias suprimidas por par [i, j],
circular Completo / Parcial / Simétrico, avisos de la ruta que no alcanza y multitransformación con las mismas opciones."""
import pytest

from omnicad import api


@pytest.fixture
def s():
    return api.Sesion()


def llamar(sesion, nombre, **args):
    r = api.llamar(sesion, nombre, args)
    assert r["ok"], r
    return r["result"]


def falla(sesion, nombre, **args):
    r = api.llamar(sesion, nombre, args)
    assert not r["ok"], r
    return r


def minimos(s, r):
    cuerpos = {c["id"]: c for c in llamar(s, "get_scene_info")["bodies"]}
    return sorted(tuple(round(v, 4) for v in cuerpos[b["id"]]["bounding_box"]["min"]) for b in r["bodies_created"])


def cubo(s, **kw):
    return llamar(s, "create_box", length=10, width=10, height=10, **kw)["bodies_created"][0]["id"]


def test_rectangular_simetria_por_direccion_y_supresion_de_cualquier_fila(s):
    c = cubo(s)
    r = llamar(s, "rectangular_pattern", bodies=c, x_count=2, x_spacing=20, y_count=2, y_spacing=30, axis2="y",
               symmetric=True, symmetric2=False, suppress=[[1, 1], -1])
    # 3 en X (−20, 0, 20) × 2 en Y (0, 30) = 6 instancias: sin el original y sin las dos suprimidas quedan tres copias
    # (el cubo mide 10 y está centrado: la esquina mínima es el centro − 5)
    assert minimos(s, r) == [(-25.0, 25.0, 0.0), (-5.0, 25.0, 0.0), (15.0, -5.0, 0.0)]
    op = s.doc.operaciones[-1]
    assert op.p["simetrico2"] is False and op.p["suprimir"] == [[1, 1], [-1, 0]]


def test_rectangular_suprimir_valida_los_identificadores(s):
    c = cubo(s)
    for malo in ([[0, 0]], [[5, 0]], [[0, 1]], [[-1, 0]], [[1, 2, 3]], ["a"]):
        falla(s, "rectangular_pattern", bodies=c, x_count=3, x_spacing=20, suppress=malo)
    assert llamar(s, "get_timeline")["steps"].__len__() == 1                                # nada quedó a medias


def test_circular_completo_parcial_y_simetrico(s):
    c = cubo(s, x=25)
    completo = llamar(s, "circular_pattern", bodies=c, count=4, axis="z", distribution="full")
    assert len(completo["bodies_created"]) == 3 and s.doc.operaciones[-1].p["distribucion"] == "completo"
    parcial = llamar(s, "circular_pattern", bodies=c, count=3, axis="z", total_angle=120, distribution="partial")
    assert len(parcial["bodies_created"]) == 2
    simetrico = llamar(s, "circular_pattern", bodies=c, count=2, axis="z", total_angle=90, distribution="symmetric")
    assert len(simetrico["bodies_created"]) == 2 and s.doc.operaciones[-1].p["distribucion"] == "simetrico"
    viejo = llamar(s, "circular_pattern", bodies=c, count=3, axis="z", total_angle=120)         # «extent»: como antes
    assert s.doc.operaciones[-1].p["distribucion"] == "extension" and len(viejo["bodies_created"]) == 2


def test_ruta_que_no_alcanza_avisa_en_vez_de_extrapolar(s):
    c = cubo(s)
    llamar(s, "create_sketch", plane="XY", name="Ruta")
    llamar(s, "draw_line", sketch="Ruta", start_x=0, start_y=0, end_x=20, end_y=0)
    r = api.llamar(s, "path_pattern", {"path_sketch": "Ruta", "bodies": c, "count": 5, "distance": 10,
                                       "spacing_mode": "spacing"})
    assert r["ok"] and any("La ruta no alcanza" in a for a in r.get("warnings", r.get("avisos", []))), r
    assert len(r["result"]["bodies_created"]) == 2          # el original y 2 copias caben en 20 mm; las otras 2 no se crean


def test_multi_transform_acepta_simetria_y_supresion(s):
    c = cubo(s)
    r = llamar(s, "multi_transform", bodies=c, transforms=[
        {"type": "rectangular", "axis": "x", "count": 2, "spacing": 20, "axis2": "y", "count2": 2, "spacing2": 30,
         "symmetric": True, "symmetric2": False, "suppress": [[1, 1]]},
        {"type": "circular", "axis": "z", "count": 2, "total_angle": 180, "distribution": "partial", "suppress": [1]}])
    op = s.doc.operaciones[-1]
    assert op.p["transformaciones"][0]["suprimir"] == [[1, 1]] and op.p["transformaciones"][0]["simetrico2"] is False
    assert op.p["transformaciones"][1]["distribucion"] == "parcial" and op.p["transformaciones"][1]["suprimir"] == [1]
    assert len(r["bodies_created"]) == 4                    # 5 instancias (6 − la suprimida) menos el original; el giro suprimido no suma
    falla(s, "multi_transform", bodies=c, transforms=[{"type": "rectangular", "axis": "x", "count": 2, "suppress": [[3, 0]]}])

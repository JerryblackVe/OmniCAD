# -*- coding: utf-8 -*-
"""P-120: Extruir varias regiones vecinas de un boceto las une en el plano y extruye una vez (sin booleana 3D).
Con el texto de un SVG (17 letras con splines) la vista previa tardaba 2,1 s por clic; ahora 0,13 s."""
import math
import time

import pytest
from OCP.BRepBuilderAPI import (BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakePolygon,
                                BRepBuilderAPI_MakeWire)
from OCP.GeomAPI import GeomAPI_PointsToBSpline
from OCP.collections import Array1_gp_Pnt
from OCP.gp import gp_Pnt

from omnicad.nucleo import geometria as geo


def _franjas(n=40, largo=60.0, alto=2.0, puntos=41):
    """`n` franjas vecinas separadas por splines onduladas: comparten cada borde como las regiones de un texto."""
    curvas = []
    for i in range(n + 1):
        arr = Array1_gp_Pnt(1, puntos)
        for k in range(puntos):
            x = largo * k / (puntos - 1)
            arr.SetValue(k + 1, gp_Pnt(x, i * alto + 0.6 * math.sin(x / 3 + i), 0))
        curvas.append(GeomAPI_PointsToBSpline(arr).Curve())
    caras = []
    for a, b in zip(curvas, curvas[1:], strict=False):
        w = BRepBuilderAPI_MakeWire()
        for e in (BRepBuilderAPI_MakeEdge(a).Edge(), BRepBuilderAPI_MakeEdge(a.EndPoint(), b.EndPoint()).Edge(),
                  BRepBuilderAPI_MakeEdge(b).Edge(), BRepBuilderAPI_MakeEdge(b.StartPoint(), a.StartPoint()).Edge()):
            w.Add(e)
        caras.append(BRepBuilderAPI_MakeFace(w.Wire(), True).Face())
    return caras


def _cuadrado(x, y, lado=10.0, z=0.0):
    p = BRepBuilderAPI_MakePolygon(gp_Pnt(x, y, z), gp_Pnt(x + lado, y, z), gp_Pnt(x + lado, y + lado, z),
                                   gp_Pnt(x, y + lado, z), True)
    return BRepBuilderAPI_MakeFace(p.Wire(), True).Face()


@pytest.fixture
def uniones(monkeypatch):
    """Cuenta las uniones 3D de más de un sólido que hace `extruir`."""
    llamadas = []
    original = geo.unir_todos
    monkeypatch.setattr(geo, "unir_todos", lambda formas: (llamadas.append(len(formas)), original(formas))[1])
    return llamadas


def test_regiones_vecinas_se_unen_en_el_plano(uniones):
    caras = _franjas()
    esperado = sum(geo.volumen(geo.extruir([c], (0, 0, 1), 5.0)) for c in caras)    # cada prisma suelto
    inicio = time.perf_counter()
    s = geo.extruir(caras, (0, 0, 1), 5.0)
    demora = time.perf_counter() - inicio
    assert geo.es_valida(s)
    assert len(geo.solidos(s)) == 1 and len(geo.caras(s)) == 6        # las 40 franjas: un solo prisma limpio
    assert geo.volumen(s) == pytest.approx(esperado, rel=1e-4)   # la integración de caras spline yerra ~1e-5
    assert all(n <= 1 for n in uniones)                                # sin la booleana 3D de los 40 prismas
    assert demora < 2.0, f"extruir 40 regiones tardó {demora:.2f} s (antes ~0,33 s; con la unión plana ~0,04 s)"


def test_simetrica_igual_volumen(uniones):
    caras = _franjas(n=8)
    s = geo.extruir(caras, (0, 0, 1), 6.0, simetrica=True)
    assert geo.volumen(s) == pytest.approx(sum(geo.volumen(geo.extruir([c], (0, 0, 1), 6.0)) for c in caras), rel=1e-4)
    (_, _, z0), (_, _, z1) = geo.caja_envolvente(s)
    assert (z0, z1) == (pytest.approx(-3.0, abs=1e-6), pytest.approx(3.0, abs=1e-6))
    assert all(n <= 1 for n in uniones)


def test_regiones_separadas_dan_un_solido_cada_una(uniones):
    s = geo.extruir([_cuadrado(0, 0), _cuadrado(30, 0), _cuadrado(0, 30)], (0, 0, 1), 4.0)
    assert len(geo.solidos(s)) == 3 and geo.es_valida(s)
    assert geo.volumen(s) == pytest.approx(3 * 400.0)
    assert not uniones                                                # ni se tocan: ni la booleana


def test_regiones_que_se_pisan_dan_la_union(uniones):
    s = geo.extruir([_cuadrado(0, 0), _cuadrado(5, 0)], (0, 0, 1), 2.0)
    assert len(geo.solidos(s)) == 1 and geo.es_valida(s)
    assert geo.volumen(s) == pytest.approx(15 * 10 * 2.0)


def test_caras_en_planos_distintos_unen_los_prismas(uniones):
    s = geo.extruir([_cuadrado(0, 0), _cuadrado(5, 0, z=1.0)], (0, 0, 1), 2.0)
    assert geo.es_valida(s) and uniones == [2]                        # no son coplanares: el camino de siempre
    assert geo.volumen(s) == pytest.approx(2 * 200.0 - 5 * 10 * 1.0)


def test_revolucion_de_regiones_vecinas_y_espejadas(uniones):
    s = geo.revolver([_cuadrado(5, 0), _cuadrado(15, 0)], (0, 0, 0), (0, 1, 0), 360)
    assert geo.es_valida(s) and len(geo.solidos(s)) == 1 and all(n <= 1 for n in uniones)
    assert geo.volumen(s) == pytest.approx(math.pi * (25 ** 2 - 5 ** 2) * 10, rel=1e-6)
    # una región y su espejo al otro lado del eje barren el mismo anillo: la unión 3D sigue haciendo falta
    s = geo.revolver([_cuadrado(5, 0), _cuadrado(-15, 0)], (0, 0, 0), (0, 1, 0), 360)
    assert geo.es_valida(s) and geo.volumen(s) == pytest.approx(math.pi * (15 ** 2 - 5 ** 2) * 10, rel=1e-6)

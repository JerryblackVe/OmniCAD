# -*- coding: utf-8 -*-
"""B-48: por defecto, la booleana de OpenCascade ESCRIBE en sus entradas (les agrega curvas sobre las caras del otro
cuerpo y les sube tolerancias; doc de OCCT, «Safe processing mode»). En paralelo, esas escrituras las hacen varios
hilos del kernel sobre aristas y vértices compartidos, y las formas tocadas son las del documento: estados anteriores
del timeline, la caché del visor y los reintentos de la misma booleana. Caso del llavero (AG-8 y B-293, las caídas
reproducidas en Windows): prismas apoyados sobre la cara de una caja."""
import math

import pytest

from omnicad.nucleo import geometria as geo
from omnicad.nucleo.intercambio import brep_a_texto


def _prisma(cx, cy, r, lados):
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakePolygon
    from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism
    from OCP.gp import gp_Pnt, gp_Vec
    p = BRepBuilderAPI_MakePolygon()
    for k in range(lados):
        a = 2 * math.pi * k / lados + 0.3
        p.Add(gp_Pnt(cx + r * math.cos(a), cy + r * math.sin(a), 20.0))
    p.Close()
    return BRepPrimAPI_MakePrism(BRepBuilderAPI_MakeFace(p.Wire()).Face(), gp_Vec(0, 0, 3)).Shape()


@pytest.mark.parametrize("unir", [lambda b, h, c: geo.booleano(b, c, "unir"),
                                  lambda b, h, c: geo.unir_todos([b, *h])], ids=["booleano", "unir_todos"])
def test_la_booleana_no_modifica_las_formas_que_recibe(unir):
    base = geo.caja(120, 80, 20)
    prismas = [_prisma(10 + 6.5 * i, 40 + 8 * math.sin(i), 3.2, 5 + i % 4) for i in range(17)]
    juntos = geo.compuesto(prismas)      # antes de la foto: armar el compuesto apaga la marca «libre» de cada prisma
    antes = [brep_a_texto(f) for f in (base, *prismas)]     # con el código viejo, la unión les sumaba 30 curvas 2D
    resultado = unir(base, prismas, juntos)
    assert geo.es_valida(resultado)
    assert abs(geo.volumen(resultado) - (120 * 80 * 20 + sum(geo.volumen(p) for p in prismas))) < 1e-3
    cambiadas = [i for i, (f, t) in enumerate(zip((base, *prismas), antes, strict=True)) if brep_a_texto(f) != t]
    assert cambiadas == []

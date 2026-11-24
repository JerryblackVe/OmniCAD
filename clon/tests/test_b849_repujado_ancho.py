# -*- coding: utf-8 -*-
"""B-849: repujado envolviendo un cilindro con un perfil ancho. Hasta una vuelta completa (2π·r) envuelve
entero (antes rechazaba en silencio más ancho que media circunferencia ≈ 109 mm y decía «Perfiles fuera de
las caras»); más ancho avisa «El dibujo es más ancho que el cilindro (máx. X mm)»."""
import math

import pytest
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakePolygon
from OCP.gp import gp_Pnt

from omnicad.nucleo import geometria as g
from omnicad.nucleo import solidos_crear as sc

RADIO, ALTO = 34.85, 40.0                                     # cilindro Ø69,7 del repro


def _poligono(puntos):
    mk = BRepBuilderAPI_MakePolygon()
    for p in puntos:
        mk.Add(gp_Pnt(*map(float, p)))
    mk.Close()
    return BRepBuilderAPI_MakeFace(mk.Wire(), True).Face()


def _repujar(ancho):
    """Rectángulo ancho×20 en el plano XZ (pasa por el eje), 1 mm de relieve sobre la cara lateral."""
    cil = g.cilindro(RADIO, ALTO)
    lateral = [c for c in g.caras(cil) if g.plano_de_cara(c) is None][0]
    perfil = _poligono([(-ancho / 2, 0, 10), (ancho / 2, 0, 10), (ancho / 2, 0, 30), (-ancho / 2, 0, 30)])
    return sc.repujado(cil, [perfil], lateral, 1.0, envolver=True)


@pytest.mark.parametrize("ancho", [115.0, 200.0])
def test_repujado_ancho_envuelve_hasta_una_vuelta_completa(ancho):
    """115 mm (más que media circunferencia ≈ 109 mm, que fallaba) y 200 mm (< 2π·r ≈ 219 mm) envuelven
    enteros: volumen del sector completo, abraza la cara a 1 mm y no cambia el alto del cilindro."""
    s = _repujar(ancho)
    assert g.es_valida(s)
    sector = (ancho / RADIO) / 2 * 20 * ((RADIO + 1) ** 2 - RADIO ** 2)
    assert g.volumen(s) == pytest.approx(math.pi * RADIO ** 2 * ALTO + sector, rel=1e-6)
    (x0, y0, _), (x1, y1, z1) = g.caja_envolvente(s)
    assert (z1, max(abs(x0), abs(x1), abs(y0), abs(y1))) == pytest.approx((ALTO, RADIO + 1))


def test_repujado_mas_ancho_que_una_vuelta_avisa_el_maximo_en_1_renglon():
    """230 mm > 2π·r ≈ 219 mm: el aviso nuevo con el máximo (1 renglón, UX-9), no «Perfiles fuera de las caras»."""
    with pytest.raises(g.ErrorGeometria) as e:
        _repujar(230)
    assert e.value.args[0] == f"Más ancho que el cilindro (máx. {2 * math.pi * RADIO:.1f} mm)."
    assert len(e.value.args[0]) <= 60

# -*- coding: utf-8 -*-
"""Reuso del BRepClass3d_SolidClassifier en fijaciones: el clasificador compartido responde
igual que uno nuevo por punto (`_dentro`), y `_material` sobre el borde de un agujero pasante
cuenta el material del anillo exterior y el vacío del interior."""
import math

import numpy as np
import pytest
from OCP.BRepClass3d import BRepClass3d_SolidClassifier

from omnicad.nucleo import fijaciones as fj
from omnicad.nucleo import geometria as g


def _cuerpo():
    """Caja de 20×20×10 mm con un agujero pasante de Ø6 centrado en (10, 10) sobre Z."""
    return g.booleano(g.caja(20, 20, 10), g.cilindro(3, 12, base=(10, 10, -1)), "cortar")


def test_dentro_con_clasificador_reusado_coincide_con_uno_por_punto():
    cuerpo = _cuerpo()
    assert g.es_valida(cuerpo)
    assert g.volumen(cuerpo) == pytest.approx(20 * 20 * 10 - math.pi * 3 ** 2 * 10)  # agujero pasante
    # (punto, valor esperado a mano): dentro del material, en el agujero (a menos de 3 mm del eje)
    # o fuera de la caja (0..20 en X e Y, 0..10 en Z).
    casos = [
        ((5, 5, 5), True),          # material: a 7,07 mm del eje del agujero
        ((16, 10, 5), True),        # material: a 6 mm del eje, dentro de la caja
        ((10, 13.5, 5), True),      # material: a 3,5 mm del eje, por fuera del Ø6
        ((10, 10, 5), False),       # sobre el eje: dentro del agujero
        ((10, 7.5, 5), False),      # a 2,5 mm del eje: dentro del agujero
        ((25, 10, 5), False),       # fuera de la caja en X
        ((10, 10, 15), False),      # por encima de la caja
    ]
    clf = BRepClass3d_SolidClassifier(cuerpo)               # UN clasificador para todos los puntos
    for punto, esperado in casos:
        assert fj._dentro(cuerpo, punto) == esperado, punto                # uno nuevo por punto
        assert fj._dentro(cuerpo, punto, clf) == esperado, punto           # el reusado da lo mismo
    # el clasificador reusado sigue respondiendo igual después de toda la tanda (no queda "pegado")
    assert fj._dentro(cuerpo, (5, 5, 5), clf) is True
    assert fj._dentro(cuerpo, (10, 10, 5), clf) is False


def test_material_en_el_borde_del_agujero():
    cuerpo = _cuerpo()
    centro = np.array([10.0, 10.0, 10.0])                    # boca del agujero en la cara superior
    n = np.array([0.0, 0.0, 1.0])
    radio = 3.0
    dlt = fj._delta(radio)                                   # 0,25 mm para Ø6
    # a 0,25 mm bajo la cara superior: los 8 puntos del anillo exterior caen en el material
    # (a 3,25 mm del eje, dentro de la caja) y los 8 del interior en el agujero (a 2,75 mm)
    assert fj._material(cuerpo, centro, n, radio, -dlt) == (8, 0)
    # lo mismo contado punto por punto con un clasificador nuevo cada vez (sin reuso)
    r_adentro = max(radio - dlt, radio * 0.5)
    manual = (sum(fj._dentro(cuerpo, p) for p in fj._muestras(centro, n, radio + dlt, -dlt)),
              sum(fj._dentro(cuerpo, p) for p in fj._muestras(centro, n, r_adentro, -dlt)))
    assert manual == (8, 0)
    # del otro lado de la cara (z = 10,25) no hay material: el agujero es pasante
    assert fj._material(cuerpo, centro, n, radio, dlt) == (0, 0)

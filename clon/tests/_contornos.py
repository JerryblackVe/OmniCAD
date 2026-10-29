# -*- coding: utf-8 -*-
"""Bocetos de prueba para el solver: contornos cerrados de splines encadenadas con tangentes (B-111).

Lo usan `tests/test_solver_splines.py`, `scripts/medir_solver_boceto.py` y `scripts/medir_ui_boceto.py`, así miden lo
mismo."""
import math

from omnicad.restricciones.boceto import Boceto


def contorno_splines(n, con_tangentes=True, conflicto=False, radio=100.0, boceto=None):
    """Contorno cerrado de `n` splines de ajuste de 4 puntos que comparten extremo. Con `con_tangentes`, G1 entre cada
    par vecino (trazo de raqueta); `conflicto` agrega dos cotas incompatibles entre sí. Se arma en `boceto` (el de un
    editor abierto) o en uno nuevo. Devuelve (boceto, valores de las cotas)."""
    b = boceto if boceto is not None else Boceto()
    m = 3 * n
    pts = [b.agregar_punto(radio * math.cos(2 * math.pi * k / m) * (1 + 0.08 * math.sin(14 * math.pi * k / m)),
                           radio * 0.6 * math.sin(2 * math.pi * k / m) * (1 + 0.08 * math.cos(10 * math.pi * k / m)))
           for k in range(m)]
    splines = [b.agregar_spline([pts[(3 * i + j) % m] for j in range(4)]) for i in range(n)]
    b.agregar_restriccion("fijo", [pts[0]])
    if con_tangentes:
        for i in range(n):
            b.agregar_restriccion("tangente", [splines[i], splines[(i + 1) % n]])
    valores = {}
    if conflicto:
        for valor in (40.0, 55.0):
            valores[b.agregar_cota("distancia", [pts[0], pts[3]], f"{valor}")] = valor
    return b, valores

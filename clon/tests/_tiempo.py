# -*- coding: utf-8 -*-
"""P-57: el mejor de hasta tres tiempos de reloj de pared, como en test_render_rapido."""
import time


def mejor_tiempo(funcion, tope, repeticiones=3):
    """Menor tiempo de hasta `repeticiones` corridas de `funcion` (corta apenas una cumple el tope): la carga ajena de
    la PC suma tiempo a una corrida, nunca se lo resta; una regresión real las hace fallar a todas. Devuelve
    (segundos, resultado de la última corrida)."""
    mejor, resultado = None, None
    for _ in range(repeticiones):
        inicio = time.perf_counter()
        resultado = funcion()
        segundos = time.perf_counter() - inicio
        mejor = segundos if mejor is None else min(mejor, segundos)
        if mejor < tope:
            break
    return mejor, resultado

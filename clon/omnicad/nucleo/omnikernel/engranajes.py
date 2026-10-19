# -*- coding: utf-8 -*-
"""Cremallera con OmniKernel (solo rectas). El engranaje de evolvente necesita curvas interpoladas por puntos que el
kernel no tiene (faltante FK-019): sin soporte."""
from .. import engranajes as comun
from .. import geometria as geo
from .. import perfiles


def cremallera(modulo, dientes, *, angulo_presion=20.0, ancho=10.0, alto=None, holgura=comun.HOLGURA, juego=0.0):
    puntos, b = comun._contorno_cremallera(modulo, dientes, angulo_presion, ancho, alto, holgura, juego)
    lineas = [("linea", i, puntos[i], puntos[(i + 1) % len(puntos)]) for i in range(len(puntos))]
    regiones = perfiles.detectar(lineas, geo.Plano("XY"))
    if len(regiones) != 1:
        raise geo.ErrorGeometria("Cremallera: el perfil no dio una sola región.")
    return comun._validar(geo.extruir([regiones[0].cara], (0, 0, 1), b), "Cremallera")

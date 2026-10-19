# -*- coding: utf-8 -*-
"""Consultas sobre el tipo nativo; las restantes se informan sin soporte."""
import numpy as np
import omnikernel


def es_forma(forma):
    return isinstance(forma, omnikernel.Cuerpo) and not forma.IsNull()


def centro_lineal(forma):
    if forma.tipo != "arista":
        from .. import motor
        motor.sin_soporte("el centro de longitud de una cara o un cuerpo")
    return np.array(forma.centro_lineal(), float)


def distancia(a, b):
    return a.distancia(b)


def dentro_solidos(solidos, punto, tolerancia=1e-7):
    return any(s.clasificar(list(map(float, punto)), float(tolerancia)) == "adentro" for s in solidos)


def centroide(forma):
    if forma.tipo == "cara":
        return np.array(forma.firma()["centro"], float)
    return centro_lineal(forma)


def hijos_compuesto(forma):
    return forma.subformas("solido") if forma.tipo == "cuerpo" else [forma]


def transformacion_identidad():
    return np.eye(4)

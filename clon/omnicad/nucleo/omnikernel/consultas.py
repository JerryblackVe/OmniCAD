# -*- coding: utf-8 -*-
"""Consultas sobre el tipo nativo; las restantes se informan sin soporte."""
import numpy as np
import omnikernel


def es_forma(forma):
    return isinstance(forma, omnikernel.Cuerpo) and not forma.IsNull()


def centro_lineal(forma):
    """Centro de longitud de una recta (su punto medio) o de un círculo entero (su centro); de un arco u otra curva el
    kernel no lo da todavía (faltante FK-010)."""
    f = forma.firma() if forma.tipo == "arista" else {}
    if f.get("geom") == "linea":
        return np.array(f["medio"], float)
    if f.get("geom") == "circulo" and np.allclose(*f["extremos"], rtol=0, atol=1e-9):
        return np.array(f["centro"], float)
    from .. import motor
    motor.sin_soporte("el centro de longitud de un arco, una curva o una cara")


def centroide(forma):
    if forma.tipo == "cara":
        return np.array(forma.firma()["centro"], float)
    return centro_lineal(forma)


def hijos_compuesto(forma):
    return forma.subformas("solido") if forma.tipo == "cuerpo" else [forma]

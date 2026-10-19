# -*- coding: utf-8 -*-
"""Simetría y patrones con OmniKernel: cada transformación es una matriz 4x4 de numpy (en OpenCascade, una gp_Trsf).
Las listas de los patrones las arman las funciones comunes de `nucleo/solidos_crear.py`; acá solo las piezas."""
import numpy as np

from .. import geometria as geo
from .geometria import matriz_rotacion


def _traslacion(v):
    m = np.eye(4)
    m[:3, 3] = np.asarray(v, float)
    return m


def _rotacion(punto, eje, radianes):
    return matriz_rotacion(punto, eje, radianes)


def _identidad():
    return np.eye(4)


def _componer(t, previa):
    return np.asarray(t, float) @ np.asarray(previa, float)


def _clave_trsf(t):
    return tuple(round(float(v), 6) + 0.0 for v in np.asarray(t, float)[:3, :4].ravel())


def transformacion_simetria(plano):
    n = np.asarray(plano.normal, float) / np.linalg.norm(plano.normal)
    m = np.eye(4)
    m[:3, :3] = np.eye(3) - 2 * np.outer(n, n)
    m[:3, 3] = 2 * float(np.asarray(plano.origen, float) @ n) * n
    return m


def aplicar(forma, trsf):
    return geo.transformar(forma, np.asarray(trsf, float))


def instanciar(forma, trsf):
    """Sin copias ligeras en el kernel: una copia de verdad (mismo resultado, más memoria)."""
    return aplicar(forma, trsf)


def unir_instancias(formas):
    return geo.unir_todos(formas)


def herramienta_agujero(punto, direccion, *, tipo="simple", diametro=None, profundidad=10.0, punta="angulo",
                        angulo_punta=118.0, diam_abocardado=None, prof_abocardado=None, diam_avellanado=None,
                        angulo_avellanado=90.0, roscado=None, mano="derecha", clase="", holgura=0.0,
                        conicidad=0.0):
    """El medio perfil común, girado por el kernel alrededor del eje del agujero."""
    from .. import motor, perfiles
    from .. import solidos_crear as comun
    a = comun._perfil_agujero(punto, direccion, tipo, diametro, profundidad, punta, angulo_punta, diam_abocardado,
                              prof_abocardado, diam_avellanado, angulo_avellanado, roscado, clase, holgura, conicidad)
    if roscado:                                               # después de validar, como en OpenCascade
        motor.sin_soporte("la rosca modelada de un agujero")
    p, d = a["punto"], a["direccion"]
    e = comun._perpendicular(d)
    plano = geo.Plano.desde_marco(p, np.cross(e, d), e)       # u = radial, v = eje del agujero
    pts = a["medio"]
    lineas = [("linea", i, pts[i], pts[(i + 1) % len(pts)]) for i in range(len(pts))]
    regiones = perfiles.detectar(lineas, plano)
    if len(regiones) != 1:
        raise geo.ErrorGeometria("Agujero: el medio perfil no dio una sola región.")
    return comun._validar(geo.revolver([regiones[0].cara], p, d, 360.0), "Agujero")

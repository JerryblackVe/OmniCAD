# -*- coding: utf-8 -*-
"""
Bocetos ↔ archivos 2D: INSERTAR › Insertar DXF / Insertar SVG (primitivas → entidades del boceto) y
«Guardar como DXF» de un boceto [GUID-BC1A5C26] (entidades del boceto → primitivas DXF).

Al insertar, los extremos que caen en el mismo lugar se convierten en el MISMO punto del boceto (si no,
los contornos no cerrarían en perfiles) y las curvas Bézier del SVG pasan a splines de puntos de control.
"""
import math

import numpy as np

from ..restricciones.boceto import Boceto, puntos_primitiva


def _transformacion(escala, desplazamiento, angulo_grados):
    c, s = math.cos(math.radians(angulo_grados)), math.sin(math.radians(angulo_grados))
    dx, dy = desplazamiento

    def f(p):
        x, y = float(p[0]) * escala, float(p[1]) * escala
        return (c * x - s * y + dx, s * x + c * y + dy)
    return f


def boceto_desde_primitivas(primitivas, *, escala=1.0, desplazamiento=(0.0, 0.0), angulo=0.0, tolerancia=1e-6):
    """Boceto nuevo con las primitivas de `dxf.leer_dxf` / `svg.leer_svg`, escaladas, giradas y movidas."""
    b = Boceto()
    f = _transformacion(escala, desplazamiento, angulo)
    puntos = {}

    def pid(p):
        x, y = f(p)
        clave = (round(x / tolerancia), round(y / tolerancia))
        if clave not in puntos:
            puntos[clave] = b.agregar_punto(x, y)
        return puntos[clave]

    def linea(a, c):
        ia, ic = pid(a), pid(c)
        if ia != ic:
            b.agregar_linea(ia, ic)

    for prim in primitivas:
        tipo = prim[0]
        if tipo == "linea":
            linea(prim[1], prim[2])
        elif tipo == "polilinea":
            pts = list(prim[1])
            for a, c in zip(pts, pts[1:], strict=False):
                linea(a, c)
            if prim[2] and len(pts) > 2:
                linea(pts[-1], pts[0])
        elif tipo == "circulo":
            (cx, cy), r = prim[1], prim[2]
            if r * escala > tolerancia:
                b.agregar_circulo(pid((cx, cy)), r * escala)
        elif tipo == "arco":
            (cx, cy), r, a0, a1 = prim[1], prim[2], prim[3], prim[4]
            ini = (cx + r * math.cos(a0), cy + r * math.sin(a0))
            fin = (cx + r * math.cos(a1), cy + r * math.sin(a1))
            if r * escala > tolerancia and pid(ini) != pid(fin):
                b.agregar_arco_centro(pid((cx, cy)), pid(ini), pid(fin))
        elif tipo == "bezier":
            p = prim[1]
            if np.allclose(p[0], p[1]) and np.allclose(p[2], p[3]):
                linea(p[0], p[3])                              # Bézier degenerada = recta
            else:
                ids = [pid(p[0])] + [b.agregar_punto(*f(q)) for q in p[1:3]] + [pid(p[3])]
                b.agregar_spline(ids, modo="control", grado=3)
        elif tipo == "texto":
            (x, y), altura, texto = prim[1], prim[2], prim[3]
            if str(texto).strip():
                b.agregar_texto(f((x, y)), texto, altura=altura * escala)
    if not b.curvas:
        raise ValueError("El archivo no tiene geometría para el boceto.")
    return b


def primitivas_dxf_de_boceto(boceto, incluir_construccion=False):
    """Entidades del boceto como primitivas del escritor DXF (líneas, círculos, arcos; lo demás, polilínea).
    La construcción va a la capa «CONSTRUCCION» si se incluye."""
    salida = []
    for prim in boceto.geometria(incluir_construccion=incluir_construccion):
        c = boceto.curvas.get(prim[1])
        capa = "CONSTRUCCION" if c is not None and getattr(c, "construccion", False) else "0"
        if prim[0] == "linea":
            dxf = ("linea", prim[2], prim[3])
        elif prim[0] == "circulo":
            dxf = ("circulo", prim[2], prim[3])
        elif prim[0] == "arco":
            dxf = ("arco", prim[2], prim[3], prim[4], prim[5])
        else:
            pts = puntos_primitiva(prim)
            cerrada = len(pts) > 2 and np.allclose(pts[0], pts[-1])
            dxf = ("polilinea", [tuple(p) for p in (pts[:-1] if cerrada else pts)], cerrada)
        salida.append((capa, dxf))
    return salida

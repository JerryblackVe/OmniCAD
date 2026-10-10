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


def _transformacion(escala, desplazamiento, angulo_grados, voltear=(False, False), centro=(0.0, 0.0)):
    """Punto → punto: voltea alrededor de `centro`, escala desde el origen, gira y mueve."""
    c, s = math.cos(math.radians(angulo_grados)), math.sin(math.radians(angulo_grados))
    dx, dy = desplazamiento
    fx, fy = (-1.0 if voltear[0] else 1.0), (-1.0 if voltear[1] else 1.0)
    cx, cy = centro

    def f(p):
        x, y = cx + fx * (float(p[0]) - cx), cy + fy * (float(p[1]) - cy)
        x, y = x * escala, y * escala
        return (c * x - s * y + dx, s * x + c * y + dy)
    return f


def _cerca(a, b, tol=1e-8):
    return abs(a[0] - b[0]) <= tol + 1e-5 * abs(b[0]) and abs(a[1] - b[1]) <= tol + 1e-5 * abs(b[1])


def caja_primitivas(primitivas):
    """((xmin, ymin), (xmax, ymax)) de las primitivas de `dxf.leer_dxf` / `svg.leer_svg` (las curvas se
    muestrean); None si no hay ninguna con puntos."""
    pts, beziers = [], []
    for prim in primitivas:
        tipo = prim[0]
        if tipo == "linea":
            pts += [prim[1], prim[2]]
        elif tipo in ("polilinea", "curva"):
            pts += list(prim[1])
        elif tipo == "circulo":
            (cx, cy), r = prim[1], prim[2]
            pts += [(cx - r, cy - r), (cx + r, cy + r)]
        elif tipo == "arco":
            (cx, cy), r, a0, a1 = prim[1], prim[2], prim[3], prim[4]
            barrido = (a1 - a0) % (2 * math.pi) or 2 * math.pi
            pts += [(cx + r * math.cos(a0 + barrido * k / 24), cy + r * math.sin(a0 + barrido * k / 24))
                    for k in range(25)]
        elif tipo == "bezier":
            beziers.append(prim[1])
        elif tipo == "texto":
            pts.append(tuple(prim[1]))
    if beziers:                            # todas juntas: (k, 4, 2) por la matriz de Bernstein (17, 4)
        t = np.linspace(0.0, 1.0, 17)[:, None]
        base = np.hstack([(1 - t) ** 3, 3 * (1 - t) ** 2 * t, 3 * (1 - t) * t ** 2, t ** 3])
        muestras = np.einsum("tk,bkd->btd", base, np.asarray(beziers, float)).reshape(-1, 2)
        pts.extend(map(tuple, muestras))
    if not pts:
        return None
    a = np.asarray(pts, float)
    return (float(a[:, 0].min()), float(a[:, 1].min())), (float(a[:, 0].max()), float(a[:, 1].max()))


def boceto_desde_primitivas(primitivas, *, escala=1.0, desplazamiento=(0.0, 0.0), angulo=0.0, tolerancia=1e-6,
                            voltear_h=False, voltear_v=False, ancho=None, destino=None):
    """Boceto con las primitivas de `dxf.leer_dxf` / `svg.leer_svg`, volteadas (alrededor del centro de su
    caja), escaladas, giradas y movidas, en ese orden. `ancho` (mm) fija el ancho final del dibujo y pisa a
    `escala`. Con `destino` (un Boceto) se agregan ahí en vez de crear uno nuevo."""
    caja = caja_primitivas(primitivas)
    if ancho is not None:
        if caja is None or caja[1][0] - caja[0][0] <= 1e-12:
            raise ValueError("No se puede ajustar el ancho: el dibujo no tiene ancho.")
        if not ancho > 0:
            raise ValueError("El ancho tiene que ser positivo.")
        escala = float(ancho) / (caja[1][0] - caja[0][0])
    if not escala > 0:
        raise ValueError("La escala tiene que ser positiva.")
    centro = ((caja[0][0] + caja[1][0]) / 2, (caja[0][1] + caja[1][1]) / 2) if caja else (0.0, 0.0)
    b = destino if destino is not None else Boceto()
    antes = len(b.curvas)
    espejo = bool(voltear_h) != bool(voltear_v)             # un espejo invierte el sentido de los arcos
    f = _transformacion(escala, desplazamiento, angulo, (voltear_h, voltear_v), centro)
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
        elif tipo == "curva":                                   # spline de ajuste por los puntos (imagen vectorizada)
            ids = [pid(q) for q in prim[1]]
            if len(set(ids)) >= (3 if prim[2] else 2):
                b.agregar_spline(ids, modo="ajuste", grado=3, cerrada=bool(prim[2]))
        elif tipo == "circulo":
            (cx, cy), r = prim[1], prim[2]
            if r * escala > tolerancia:
                b.agregar_circulo(pid((cx, cy)), r * escala)
        elif tipo == "arco":
            (cx, cy), r, a0, a1 = prim[1], prim[2], prim[3], prim[4]
            ini = (cx + r * math.cos(a0), cy + r * math.sin(a0))
            fin = (cx + r * math.cos(a1), cy + r * math.sin(a1))
            if espejo:
                ini, fin = fin, ini
            if r * escala > tolerancia and pid(ini) != pid(fin):
                b.agregar_arco_centro(pid((cx, cy)), pid(ini), pid(fin))
        elif tipo == "bezier":
            p = prim[1]
            if _cerca(p[0], p[1]) and _cerca(p[2], p[3]):
                linea(p[0], p[3])                              # Bézier degenerada = recta
            else:
                ids = [pid(p[0])] + [b.agregar_punto(*f(q)) for q in p[1:3]] + [pid(p[3])]
                b.agregar_spline(ids, modo="control", grado=3)
        elif tipo == "texto":
            (x, y), altura, texto = prim[1], prim[2], prim[3]
            if str(texto).strip():
                b.agregar_texto(f((x, y)), texto, altura=altura * escala, angulo=angulo)
    if len(b.curvas) == antes:
        raise ValueError("El archivo no tiene geometría para el boceto.")
    return b


def agregar_geometria(b, prims, tolerancia=1e-6):
    """Agrega al boceto `b` primitivas con el formato de `Boceto.geometria()` (las que salen de OpenCascade:
    'linea', 'circulo', 'arco', 'elipse', 'arco_elipse', 'spline'). Los extremos que coinciden pasan a ser el
    mismo punto. Devuelve los ids de las curvas nuevas."""
    from ..restricciones.boceto import puntos_primitiva
    puntos, nuevas = {}, []

    def pid(q):
        clave = (round(q[0] / tolerancia), round(q[1] / tolerancia))
        if clave not in puntos:
            puntos[clave] = b.agregar_punto(float(q[0]), float(q[1]))
        return puntos[clave]

    for prim in prims:
        tipo = prim[0]
        if tipo == "linea":
            a, c = pid(prim[2]), pid(prim[3])
            if a != c:
                nuevas.append(b.agregar_linea(a, c))
        elif tipo == "circulo":
            nuevas.append(b.agregar_circulo(pid(prim[2]), prim[3]))
        elif tipo == "arco":
            (cx, cy), r, a0, a1 = prim[2], prim[3], prim[4], prim[5]
            ini, fin = pid((cx + r * math.cos(a0), cy + r * math.sin(a0))), pid((cx + r * math.cos(a1), cy + r * math.sin(a1)))
            if ini != fin:
                nuevas.append(b.agregar_arco_centro(pid((cx, cy)), ini, fin))
        elif tipo == "elipse":
            (cx, cy), a, r_menor, ang = prim[2], prim[3], prim[4], prim[5]
            nuevas.append(b.agregar_elipse(pid((cx, cy)), (cx + a * math.cos(ang), cy + a * math.sin(ang)), r_menor,
                                           ejes=False))
        elif tipo == "spline":
            polos, nudos, grado, pesos = prim[2], prim[3], prim[4], prim[5]
            ids = [pid(polos[0])] + [b.agregar_punto(*map(float, q)) for q in polos[1:-1]]
            ultimo = pid(polos[-1])
            ids.append(ultimo if ultimo != ids[0] else b.agregar_punto(*map(float, polos[-1])))
            nuevas.append(b.agregar_spline(ids, modo="control", grado=grado, pesos=list(pesos) if pesos else None,
                                           nudos=list(nudos)))
        elif tipo == "arco_elipse":                      # sin arco de elipse libre: spline de ajuste por puntos
            q = puntos_primitiva(prim, 64)
            nuevas.append(b.agregar_spline([pid(q[0])] + [tuple(p) for p in q[1:-1]] + [pid(q[-1])], modo="ajuste"))
    return nuevas


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

# -*- coding: utf-8 -*-
"""Editar cara de Fusion (Edit Face), sin motor T-Spline: la cara se edita con una grilla de control sobre su dominio.

La grilla de Factor de longitud × Factor de anchura tiene (n_u + 3) × (n_v + 3) puntos, los de un B-spline cúbico uniforme
sujeto: el desplazamiento de cada punto se reparte con sus funciones de base y la superficie nueva es la de la cara más ese
campo, ajustada con un B-spline fino en el MISMO dominio UV. Por eso las aristas de la cara y sus curvas en el plano UV valen
tal cual y la cara nueva queda cosida al cuerpo sin coser. Los puntos que tocan el contorno de la cara quedan fijos (`fijos`):
un punto suelto movería el borde y los vecinos no lo siguen.
"""
import math

import numpy as np
from OCP.BRep import BRep_Builder, BRep_Tool
from OCP.BRepAdaptor import BRepAdaptor_Curve2d, BRepAdaptor_Surface
from OCP.BRepBuilderAPI import BRepBuilderAPI_Copy
from OCP.BRepTools import BRepTools
from OCP.Geom import Geom_BSplineSurface
from OCP.gp import gp_Pnt, gp_Pnt2d
from OCP.IntTools import IntTools_FClass2d
from OCP.OCP.collections import Array1_double, Array1_int, Array2_gp_Pnt
from OCP.ShapeFix import ShapeFix_ShapeTolerance
from OCP.TopAbs import TopAbs_EDGE, TopAbs_FORWARD, TopAbs_IN, TopAbs_REVERSED
from OCP.TopExp import TopExp_Explorer
from OCP.TopLoc import TopLoc_Location
from OCP.TopoDS import TopoDS

from . import geometria as geo

_GRADO = 3
_TOLERANCIA_AJUSTE = 2e-4           # mm entre la cara ajustada y la exacta
_SPANS_MAXIMOS = 192
_FACTOR_MAXIMO = 32                 # el mismo tope del panel: un archivo ajeno no pide una grilla que cuelgue el programa


def _nudos(a, b, spans):
    """Vector de nudos cúbico, uniforme y sujeto en [a, b]."""
    interior = np.linspace(a, b, spans + 1)
    return np.r_[[a] * _GRADO, interior, [b] * _GRADO]


def _base(nudos, x):
    """Funciones de base en los valores `x`: matriz (len(x), cantidad de puntos). Cox-de Boor."""
    x = np.asarray(x, float)
    n = len(nudos) - _GRADO - 1
    x = np.clip(x, nudos[0], nudos[-1])
    b = np.zeros((len(x), len(nudos) - 1))
    tramo = np.clip(np.searchsorted(nudos, x, side="right") - 1, _GRADO, n - 1)
    b[np.arange(len(x)), tramo] = 1.0
    for g in range(1, _GRADO + 1):
        nuevo = np.zeros_like(b)
        for i in range(len(nudos) - g - 1):
            d1, d2 = nudos[i + g] - nudos[i], nudos[i + g + 1] - nudos[i + 1]
            if d1 > 0:
                nuevo[:, i] += (x - nudos[i]) / d1 * b[:, i]
            if d2 > 0:
                nuevo[:, i] += (nudos[i + g + 1] - x) / d2 * b[:, i + 1]
        b = nuevo
    return b[:, :n]


def _greville(nudos):
    n = len(nudos) - _GRADO - 1
    return np.array([nudos[i + 1:i + _GRADO + 1].mean() for i in range(n)])


def _interpolar(bu, bv, m):
    """Puntos de control (Nu, Nv, 3) del B-spline que pasa por los puntos `m`, con las bases en esos mismos parámetros."""
    nu, nv = m.shape[:2]
    x = np.linalg.solve(bu, m.reshape(nu, -1)).reshape(nu, nv, 3)
    return np.linalg.solve(bv, x.transpose(1, 0, 2).reshape(nv, -1)).reshape(nv, nu, 3).transpose(1, 0, 2)


def _evaluar(sup, us, vs):
    return np.array([[(p.X(), p.Y(), p.Z()) for p in (sup.Value(float(u), float(v)) for v in vs)] for u in us], float)


def _contorno_uv(cara, por_arista=40):
    """Puntos UV del contorno de la cara."""
    puntos = []
    exp = TopExp_Explorer(cara, TopAbs_EDGE)
    while exp.More():
        arista = TopoDS.Edge(exp.Current())
        exp.Next()
        c, a, b = _pcurva(arista, cara)
        for t in np.linspace(a, b, por_arista):
            q = c.Value(float(t))
            puntos.append((q.X(), q.Y()))
    return np.array(puntos, float)


def _pcurva(arista, cara):
    """(curva en el plano UV de la cara, inicio, fin)."""
    ad = BRepAdaptor_Curve2d(arista, cara)
    return BRep_Tool.CurveOnSurface_s(arista, cara, 0.0, 0.0), ad.FirstParameter(), ad.LastParameter()


def _dominio(cara):
    return BRepTools.UVBounds_s(cara)


def grilla_cara(cara, n_u=1, n_v=1):
    """Grilla de control de una cara: {"puntos": (Nu, Nv, 3) sobre la cara, "fijos": (Nu, Nv) bool, "uv": (u0, u1, v0, v1),
    "signo": -1 si la normal de la superficie apunta hacia adentro del cuerpo}."""
    if not (1 <= n_u <= _FACTOR_MAXIMO and 1 <= n_v <= _FACTOR_MAXIMO):
        raise geo.ErrorGeometria(f"Los factores de longitud y anchura van de 1 a {_FACTOR_MAXIMO}.")
    u0, u1, v0, v1 = _dominio(cara)
    if not all(map(math.isfinite, (u0, u1, v0, v1))):
        raise geo.ErrorGeometria("La cara no tiene dominio finito: no se puede editar.")
    nudos_u, nudos_v = _nudos(u0, u1, n_u), _nudos(v0, v1, n_v)
    sup = BRepAdaptor_Surface(cara)
    puntos = _evaluar(sup, _greville(nudos_u), _greville(nudos_v))
    borde = _contorno_uv(cara)
    bu, bv = _base(nudos_u, borde[:, 0]) > 1e-9, _base(nudos_v, borde[:, 1]) > 1e-9
    fijos = (bu.astype(float).T @ bv.astype(float)) > 0
    dentro = IntTools_FClass2d(cara, 1e-7)
    for i, u in enumerate(_greville(nudos_u)):
        for j, v in enumerate(_greville(nudos_v)):
            fijos[i, j] |= dentro.Perform(gp_Pnt2d(float(u), float(v))) != TopAbs_IN    # afuera de un contorno que no es rectángulo
    return {"puntos": puntos, "fijos": fijos, "uv": (u0, u1, v0, v1), "signo": -1 if cara.Orientation() == TopAbs_REVERSED else 1}


def remuestrear(desplazamientos, n0, n1):
    """Puntos de una grilla de factores `n1` con el campo de la grilla `n0` (Dividir caras con la forma ya editada)."""
    viejo = [_nudos(0.0, 1.0, n) for n in n0]
    nudos = [_nudos(0.0, 1.0, n) for n in n1]
    gu, gv = _greville(nudos[0]), _greville(nudos[1])
    campo = _campo(desplazamientos, *n0, *viejo, gu, gv)
    bu, bv = _base(nudos[0], gu), _base(nudos[1], gv)
    d = _interpolar(bu, bv, campo)                      # interpola: la forma no se suaviza
    return {(i, j): [float(x) for x in d[i, j]] for i in range(d.shape[0]) for j in range(d.shape[1]) if np.abs(d[i, j]).max() > 1e-9}


def _campo(desplazamientos, n_u, n_v, nudos_u, nudos_v, us, vs):
    """Campo de desplazamiento (len(us), len(vs), 3) de los puntos movidos {(i, j): (dx, dy, dz)}."""
    d = np.zeros((n_u + _GRADO, n_v + _GRADO, 3))
    for (i, j), v in desplazamientos.items():
        if not (0 <= i < d.shape[0] and 0 <= j < d.shape[1]):
            raise geo.ErrorGeometria(f"El punto ({i}, {j}) no está en la grilla de {d.shape[0]} × {d.shape[1]}.")
        d[i, j] = v
    return np.einsum("ai,bj,ijk->abk", _base(nudos_u, us), _base(nudos_v, vs), d)


def _ajustar(sup, u0, u1, v0, v1, campo):
    """(nudos_u, nudos_v, polos (Nu, Nv, 3), error en mm) del B-spline fino de la cara más el campo."""
    spans = 8
    while True:
        nudos_u, nudos_v = _nudos(u0, u1, spans), _nudos(v0, v1, spans)
        gu, gv = _greville(nudos_u), _greville(nudos_v)
        muestra = _evaluar(sup, gu, gv) + campo(gu, gv)
        bu, bv = _base(nudos_u, gu), _base(nudos_v, gv)
        polos = _interpolar(bu, bv, muestra)
        mu, mv = (gu[:-1] + gu[1:]) / 2, (gv[:-1] + gv[1:]) / 2
        exacta = _evaluar(sup, mu, mv) + campo(mu, mv)
        fina = np.einsum("ai,bj,ijk->abk", _base(nudos_u, mu), _base(nudos_v, mv), polos)
        error = float(np.abs(fina - exacta).max())
        if error <= _TOLERANCIA_AJUSTE or spans >= _SPANS_MAXIMOS:
            return nudos_u, nudos_v, polos, error
        spans *= 2


def _superficie(nudos_u, nudos_v, polos):
    arr = Array2_gp_Pnt(1, polos.shape[0], 1, polos.shape[1])
    for i in range(polos.shape[0]):
        for j in range(polos.shape[1]):
            arr.SetValue(i + 1, j + 1, gp_Pnt(*map(float, polos[i, j])))

    def nudos_mult(nudos):
        unicos, cuentas = np.unique(nudos, return_counts=True)
        k, m = Array1_double(1, len(unicos)), Array1_int(1, len(unicos))
        for i, (x, c) in enumerate(zip(unicos, cuentas, strict=True)):
            k.SetValue(i + 1, float(x))
            m.SetValue(i + 1, int(c))
        return k, m
    ku, mu = nudos_mult(nudos_u)
    kv, mv = nudos_mult(nudos_v)
    return Geom_BSplineSurface(arr, ku, kv, mu, mv, _GRADO, _GRADO)


def editar_cara(forma, cara, n_u, n_v, desplazamientos):
    """Editar cara (Edit Face): mueve puntos de la grilla de `cara` y devuelve el cuerpo con la cara nueva, cosida a sus vecinas.
    `desplazamientos`: {(i, j): (dx, dy, dz)} en mm. Un punto fijo (ver `grilla_cara`) es un error."""
    fijos = grilla_cara(cara, n_u, n_v)["fijos"]
    if desplazamientos and not np.isfinite(np.array(list(desplazamientos.values()), float)).all():
        raise geo.ErrorGeometria("Los desplazamientos tienen que ser números finitos.")
    for i, j in desplazamientos:
        if 0 <= i < fijos.shape[0] and 0 <= j < fijos.shape[1] and fijos[i, j] and any(desplazamientos[(i, j)]):
            raise geo.ErrorGeometria(f"El punto ({i}, {j}) toca el contorno de la cara: queda fijo.")
    u0, u1, v0, v1 = _dominio(cara)
    nudos_u, nudos_v = _nudos(u0, u1, n_u), _nudos(v0, v1, n_v)
    sup = BRepAdaptor_Surface(cara)
    nu, nv, polos, error = _ajustar(sup, u0, u1, v0, v1, lambda us, vs: _campo(desplazamientos, n_u, n_v, nudos_u, nudos_v, us, vs))
    nueva = _superficie(nu, nv, polos)

    indice = next((i for i, c in enumerate(geo.caras(forma)) if c.IsSame(cara)), None)
    if indice is None:
        raise geo.ErrorGeometria("La cara no es de este cuerpo.")
    copia = BRepBuilderAPI_Copy(forma).Shape()
    destino = geo.caras(copia)[indice]

    b, curvas = BRep_Builder(), []
    exp = TopExp_Explorer(destino.Oriented(TopAbs_FORWARD), TopAbs_EDGE)
    while exp.More():
        arista = TopoDS.Edge(exp.Current())
        exp.Next()
        if any(arista.IsSame(c[0]) for c in curvas):
            continue
        if BRep_Tool.IsClosed_s(arista, destino):          # costura: dos curvas UV, una por cada lado
            curvas.append((arista, *(_pcurva(TopoDS.Edge(arista.Oriented(o)), destino)[0] for o in (TopAbs_FORWARD, TopAbs_REVERSED))))
        else:
            curvas.append((arista, _pcurva(arista, destino)[0], None))
    tol = max(error * 2, 1e-5)
    lugar = TopLoc_Location()
    b.UpdateFace(destino, nueva, lugar, tol)
    for arista, c1, c2 in curvas:
        if c2 is None:
            b.UpdateEdge(arista, c1, destino, tol)
        else:
            b.UpdateEdge(arista, c1, c2, destino, tol)
    ShapeFix_ShapeTolerance().LimitTolerance(destino, 0.0, max(tol * 4, 1e-4))
    if not geo.es_valida(copia):
        raise geo.ErrorGeometria("La cara editada deja un cuerpo no válido: probá con un desplazamiento menor.")
    return copia


def curvas_grilla(cara, n_u, n_v, desplazamientos, muestras=48):
    """Filas y columnas de la cara editada ({"u": [Kx3], "v": [Kx3]}): las curvas de Curvatura en peines."""
    u0, u1, v0, v1 = _dominio(cara)
    nudos_u, nudos_v = _nudos(u0, u1, n_u), _nudos(v0, v1, n_v)
    gu, gv = _greville(nudos_u), _greville(nudos_v)
    tu, tv = np.linspace(u0, u1, muestras), np.linspace(v0, v1, muestras)
    sup = BRepAdaptor_Surface(cara)
    a = _evaluar(sup, tu, gv) + _campo(desplazamientos, n_u, n_v, nudos_u, nudos_v, tu, gv)
    c = _evaluar(sup, gu, tv) + _campo(desplazamientos, n_u, n_v, nudos_u, nudos_v, gu, tv)
    return {"u": [a[:, j] for j in range(a.shape[1])], "v": [c[i] for i in range(c.shape[0])]}

# -*- coding: utf-8 -*-
"""Editar cara de Fusion (Edit Face), sin motor T-Spline: la cara se edita con una grilla de control sobre su dominio.

La grilla de Factor de longitud × Factor de anchura tiene (n_u + 3) × (n_v + 3) puntos, los de un B-spline cúbico uniforme
sujeto: el desplazamiento de cada punto se reparte con sus funciones de base y la superficie nueva es la de la cara más ese
campo, ajustada con un B-spline fino en el MISMO dominio UV. Por eso las aristas de la cara y sus curvas en el plano UV valen
tal cual y la cara nueva queda cosida al cuerpo sin coser. Si se mueve un punto que toca el contorno, el borde cambia y las
vecinas lo siguen: se prolongan sobre sus propias superficies y la superficie editada, extendida más allá de la cara, las recorta
(`_con_vecinas`). En una superficie no hay de dónde prolongar: se mueven los bordes libres (`_lamina`, `_recoser`). Quedan fijos los
puntos de una costura o un polo, que no tienen vecina, y los que caen afuera de un contorno que no es rectángulo.

Dividir caras suma líneas a la grilla: `n_u` × `n_v` tramos iguales, los cortes (`cortes_u`, `cortes_v`: fracciones de 0 a 1) que
deja la extrusión con Alt (`extruir_grilla`) y el Espaciado de contorno (`espaciado`, mm: una fila de cuadros junto al contorno).
"""
import math

import numpy as np
from . import motor as _motor


def _iniciar_opencascade():
    global BRep_Builder, BRep_Tool, BRepAdaptor_Curve2d, BRepAdaptor_Surface
    global BRepBuilderAPI_Copy, BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakeWire
    global BRepClass3d_SolidClassifier, BRepLib, BRepPrimAPI_MakePrism
    global BRepTools, BRepTools_WireExplorer, Geom_BSplineSurface, GeomAbs_Plane
    global gp_Pnt, gp_Pnt2d, gp_Vec, IntTools_FClass2d
    global Array1_double, Array1_int, Array2_gp_Pnt, ShapeFix_ShapeTolerance
    global TopAbs_EDGE, TopAbs_FORWARD, TopAbs_IN, TopAbs_OUT, TopAbs_REVERSED, TopAbs_WIRE
    global TopExp_Explorer, TopLoc_Location, TopoDS
    from OCP.BRep import BRep_Builder, BRep_Tool
    from OCP.BRepAdaptor import BRepAdaptor_Curve2d, BRepAdaptor_Surface
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Copy, BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakeWire
    from OCP.BRepClass3d import BRepClass3d_SolidClassifier
    from OCP.BRepLib import BRepLib
    from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism
    from OCP.BRepTools import BRepTools, BRepTools_WireExplorer
    from OCP.Geom import Geom_BSplineSurface
    from OCP.GeomAbs import GeomAbs_Plane
    from OCP.gp import gp_Pnt, gp_Pnt2d, gp_Vec
    from OCP.IntTools import IntTools_FClass2d
    from OCP.OCP.collections import Array1_double, Array1_int, Array2_gp_Pnt
    from OCP.ShapeFix import ShapeFix_ShapeTolerance
    from OCP.TopAbs import TopAbs_EDGE, TopAbs_FORWARD, TopAbs_IN, TopAbs_OUT, TopAbs_REVERSED, TopAbs_WIRE
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopLoc import TopLoc_Location
    from OCP.TopoDS import TopoDS


if _motor.motor_activo() == "opencascade":
    _iniciar_opencascade()

from . import geometria as geo

_GRADO = 3
_TOLERANCIA_AJUSTE = 2e-4           # mm entre la cara ajustada y la exacta
_SPANS_MAXIMOS = 192
_FACTOR_MAXIMO = 32                 # el mismo tope del panel: un archivo ajeno no pide una grilla que cuelgue el programa
_CORTES_MAXIMOS = 32                # tope de los cortes de la grilla, por lo mismo
_HUECO_VOTO = 0.02                  # mm debajo de la superficie editada donde se busca el lado que queda
_TOLERANCIA_COSTURA = 1e-3


def _nudos(a, b, spans, cortes=()):
    """Vector de nudos cúbico y sujeto en [a, b]: `spans` tramos iguales más los `cortes` (fracciones de 0 a 1)."""
    interior = np.linspace(a, b, spans + 1)
    for c in cortes:
        x = a + (b - a) * float(c)
        if np.abs(interior - x).min() > 1e-9 * (b - a):        # un nudo doble le sacaría continuidad a la superficie
            interior = np.sort(np.r_[interior, x])
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


def _contorno_uv(cara, por_arista=40, sin_vecina=False):
    """Puntos UV del contorno de la cara; con `sin_vecina`, solo los de las costuras y los polos."""
    puntos = []
    exp = TopExp_Explorer(cara, TopAbs_EDGE)
    while exp.More():
        arista = TopoDS.Edge(exp.Current())
        exp.Next()
        if sin_vecina and not (BRep_Tool.IsClosed_s(arista, cara) or BRep_Tool.Degenerated_s(arista)):
            continue
        c, a, b = _pcurva(arista, cara)
        for t in np.linspace(a, b, por_arista):
            q = c.Value(float(t))
            puntos.append((q.X(), q.Y()))
    return np.array(puntos, float).reshape(-1, 2)


def _pcurva(arista, cara):
    """(curva en el plano UV de la cara, inicio, fin)."""
    ad = BRepAdaptor_Curve2d(arista, cara)
    return BRep_Tool.CurveOnSurface_s(arista, cara, 0.0, 0.0), ad.FirstParameter(), ad.LastParameter()


def _dominio(cara):
    return BRepTools.UVBounds_s(cara)


def _largos(cara):
    """Largos en mm de las líneas medias de la cara, a lo largo y a lo ancho."""
    u0, u1, v0, v1 = _dominio(cara)
    sup = BRepAdaptor_Surface(cara)
    a = _evaluar(sup, np.linspace(u0, u1, 33), [(v0 + v1) / 2])[:, 0]
    b = _evaluar(sup, [(u0 + u1) / 2], np.linspace(v0, v1, 33))[0]
    return float(np.linalg.norm(np.diff(a, axis=0), axis=1).sum()), float(np.linalg.norm(np.diff(b, axis=0), axis=1).sum())


def divisiones(cara, n_u=1, n_v=1, cortes_u=(), cortes_v=(), espaciado=0.0):
    """Divisiones de la grilla: (n_u, n_v, cortes a lo largo, cortes a lo ancho), con el Espaciado de contorno ya como cortes."""
    if not (1 <= n_u <= _FACTOR_MAXIMO and 1 <= n_v <= _FACTOR_MAXIMO):
        raise geo.ErrorGeometria(f"Los factores de longitud y anchura van de 1 a {_FACTOR_MAXIMO}.")
    try:
        cortes = [float(c) for c in cortes_u], [float(c) for c in cortes_v]
    except (TypeError, ValueError):
        cortes = [math.nan], []
    if max(map(len, cortes)) > _CORTES_MAXIMOS or not all(0 < c < 1 for lista in cortes for c in lista):
        raise geo.ErrorGeometria(f"La grilla admite hasta {_CORTES_MAXIMOS} cortes, cada uno entre 0 y 1.")
    espaciado = float(espaciado)
    if not (math.isfinite(espaciado) and espaciado >= 0):
        raise geo.ErrorGeometria("El espaciado de contorno tiene que ser un número positivo o cero.")
    if espaciado:
        largos = _largos(cara)
        if espaciado >= min(largos) / 2:
            raise geo.ErrorGeometria(f"El espaciado de contorno tiene que ser menor que {min(largos) / 2:g} mm, la mitad de la cara.")
        cortes = tuple(lista + [espaciado / largo, 1 - espaciado / largo] for lista, largo in zip(cortes, largos, strict=True))
    return n_u, n_v, *cortes


def _nudos_cara(cara, n_u, n_v, cortes_u, cortes_v):
    u0, u1, v0, v1 = _dominio(cara)
    return _nudos(u0, u1, n_u, cortes_u), _nudos(v0, v1, n_v, cortes_v)


def _toca(nudos_u, nudos_v, uv):
    """(Nu, Nv) bool: ¿el punto de la grilla mueve alguno de los puntos `uv`?"""
    bu, bv = _base(nudos_u, uv[:, 0]) > 1e-9, _base(nudos_v, uv[:, 1]) > 1e-9
    return (bu.astype(float).T @ bv.astype(float)) > 0


def grilla_cara(cara, n_u=1, n_v=1, cortes_u=(), cortes_v=(), espaciado=0.0):
    """Grilla de control de una cara: {"puntos": (Nu, Nv, 3) sobre la cara, "fijos": (Nu, Nv) bool, "contorno": los que mueven el
    borde de la cara (sus vecinas lo siguen), "uv": (u0, u1, v0, v1), "signo": -1 si la normal de la superficie apunta hacia
    adentro del cuerpo}."""
    div = divisiones(cara, n_u, n_v, cortes_u, cortes_v, espaciado)
    u0, u1, v0, v1 = _dominio(cara)
    if not all(map(math.isfinite, (u0, u1, v0, v1))):
        raise geo.ErrorGeometria("La cara no tiene dominio finito: no se puede editar.")
    nudos_u, nudos_v = _nudos_cara(cara, *div)
    sup = BRepAdaptor_Surface(cara)
    puntos = _evaluar(sup, _greville(nudos_u), _greville(nudos_v))
    contorno = _toca(nudos_u, nudos_v, _contorno_uv(cara))
    fijos = _toca(nudos_u, nudos_v, _contorno_uv(cara, sin_vecina=True))
    dentro = IntTools_FClass2d(cara, 1e-7)
    for i, u in enumerate(_greville(nudos_u)):
        for j, v in enumerate(_greville(nudos_v)):
            fijos[i, j] |= dentro.Perform(gp_Pnt2d(float(u), float(v))) == TopAbs_OUT    # afuera de un contorno que no es rectángulo
    return {"puntos": puntos, "fijos": fijos, "contorno": contorno & ~fijos, "uv": (u0, u1, v0, v1),
            "signo": -1 if cara.Orientation() == TopAbs_REVERSED else 1}


def _nudos_01(div):
    return _nudos(0.0, 1.0, div[0], div[2] if len(div) > 2 else ()), _nudos(0.0, 1.0, div[1], div[3] if len(div) > 2 else ())


def remuestrear(desplazamientos, n0, n1):
    """Puntos de la grilla de divisiones `n1` con el campo de la grilla `n0` (Dividir caras con la forma ya editada). Cada una es
    (n_u, n_v) o lo que da `divisiones`."""
    viejo, nudos = _nudos_01(n0), _nudos_01(n1)
    gu, gv = _greville(nudos[0]), _greville(nudos[1])
    campo = _campo(desplazamientos, *viejo, gu, gv)
    bu, bv = _base(nudos[0], gu), _base(nudos[1], gv)
    d = _interpolar(bu, bv, campo)                      # interpola: la forma no se suaviza
    return {(i, j): [float(x) for x in d[i, j]] for i in range(d.shape[0]) for j in range(d.shape[1]) if np.abs(d[i, j]).max() > 1e-9}


def extruir_grilla(div, desplazamientos, puntos):
    """Extrusión con Alt: suma una línea de cada lado de `puntos` {(i, j)} en la grilla de divisiones `div` (lo que da `divisiones`),
    que quedan rodeados de cuadros nuevos. Devuelve {"cortes_u", "cortes_v": los cortes nuevos, solos; "desplazamientos": el campo
    en la grilla nueva; "puntos": {punto: dónde queda en ella}}. La forma no cambia hasta mover los puntos."""
    n_u, n_v, cortes_u, cortes_v = div
    nudos = _nudos_01(div)
    nuevos = []
    for eje in (0, 1):
        g = _greville(nudos[eje])
        lo, hi = min(p[eje] for p in puntos), max(p[eje] for p in puntos)
        if lo < 0 or hi >= len(g):
            raise geo.ErrorGeometria(f"Hay un punto afuera de la grilla, que va de 0 a {len(g) - 1}.")
        nuevos.append([float((g[k - 1] + g[k]) / 2) for k in (lo, hi + 1) if 0 < k < len(g)])
    if len(cortes_u) + len(nuevos[0]) > _CORTES_MAXIMOS or len(cortes_v) + len(nuevos[1]) > _CORTES_MAXIMOS:
        raise geo.ErrorGeometria(f"La grilla admite hasta {_CORTES_MAXIMOS} cortes: no se pueden sumar más caras.")
    final = (n_u, n_v, [*cortes_u, *nuevos[0]], [*cortes_v, *nuevos[1]])
    g0, g1 = [_greville(n) for n in nudos], [_greville(n) for n in _nudos_01(final)]
    lugar = [{i: int(np.argmin(np.abs(g1[eje] - x))) for i, x in enumerate(g0[eje])} for eje in (0, 1)]
    return {"cortes_u": nuevos[0], "cortes_v": nuevos[1], "desplazamientos": remuestrear(desplazamientos, div, final),
            "puntos": {(i, j): (lugar[0][i], lugar[1][j]) for i, j in puntos}}


def _celda(nudos):
    return float(np.diff(np.unique(nudos)).min())


def _extrapoladas(nudos, x):
    """Las bases en `x`, también fuera de [a, b]: siguen la tangente del extremo y en una celda se aplanan con una cúbica, para que
    el campo no se dispare lejos de la cara."""
    x = np.asarray(x, float)
    a, b = nudos[0], nudos[-1]
    c = np.clip(x, a, b)
    t = x - c
    h, celda = 1e-5 * (b - a), _celda(nudos)
    pendiente = np.where(t[:, None] > 0, (_base(nudos, [b]) - _base(nudos, [b - h])) / h, (_base(nudos, [a + h]) - _base(nudos, [a])) / h)
    y = np.minimum(np.abs(t), celda)
    return _base(nudos, c) + (np.sign(t) * (y - y ** 3 / (3 * celda ** 2)))[:, None] * pendiente


def _campo(desplazamientos, nudos_u, nudos_v, us, vs, extendido=False):
    """Campo de desplazamiento (len(us), len(vs), 3) de los puntos movidos {(i, j): (dx, dy, dz)}."""
    d = np.zeros((len(nudos_u) - _GRADO - 1, len(nudos_v) - _GRADO - 1, 3))
    for (i, j), v in desplazamientos.items():
        if not (0 <= i < d.shape[0] and 0 <= j < d.shape[1]):
            raise geo.ErrorGeometria(f"El punto ({i}, {j}) no está en la grilla de {d.shape[0]} × {d.shape[1]}.")
        d[i, j] = v
    base = _extrapoladas if extendido else _base
    return np.einsum("ai,bj,ijk->abk", base(nudos_u, us), base(nudos_v, vs), d, optimize=True)


def _ajustar(sup, u0, u1, v0, v1, campo, cortes_u=(), cortes_v=(), medir=None):
    """(nudos_u, nudos_v, polos (Nu, Nv, 3), error en mm) del B-spline fino de la cara (o de lo que da `sup(us, vs)`) más el campo.
    `medir` (u0, u1, v0, v1): el dominio donde cuenta el error; la extensión de afuera no tiene que ser fina."""
    evaluar = sup if callable(sup) else lambda us, vs: _evaluar(sup, us, vs)
    spans = 8
    while True:
        nudos_u, nudos_v = _nudos(u0, u1, spans, cortes_u), _nudos(v0, v1, spans, cortes_v)
        gu, gv = _greville(nudos_u), _greville(nudos_v)
        muestra = evaluar(gu, gv) + campo(gu, gv)
        bu, bv = _base(nudos_u, gu), _base(nudos_v, gv)
        polos = _interpolar(bu, bv, muestra)
        mu, mv = (gu[:-1] + gu[1:]) / 2, (gv[:-1] + gv[1:]) / 2
        if medir:
            mu, mv = mu[(mu >= medir[0]) & (mu <= medir[1])], mv[(mv >= medir[2]) & (mv <= medir[3])]
        exacta = evaluar(mu, mv) + campo(mu, mv)
        fina = np.einsum("ai,bj,ijk->abk", _base(nudos_u, mu), _base(nudos_v, mv), polos, optimize=True)
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


def _prolongada(sup, u0, u1, v0, v1):
    """Evaluador de la superficie en (us, vs) que sale del dominio por la tangente: exacto en un plano o a lo largo de un cilindro."""
    p, du, dv = gp_Pnt(), gp_Vec(), gp_Vec()

    def evaluar(us, vs):
        salida = np.empty((len(us), len(vs), 3))
        for a, u in enumerate(us):
            cu = min(max(float(u), u0), u1)
            for b, v in enumerate(vs):
                cv = min(max(float(v), v0), v1)
                sup.D1(cu, cv, p, du, dv)
                salida[a, b] = (p.X() + (u - cu) * du.X() + (v - cv) * dv.X(), p.Y() + (u - cu) * du.Y() + (v - cv) * dv.Y(),
                                p.Z() + (u - cu) * du.Z() + (v - cv) * dv.Z())
        return salida
    return evaluar


def _normales(sup, us, vs, signo):
    p, du, dv = gp_Pnt(), gp_Vec(), gp_Vec()
    salida = np.empty((len(us), len(vs), 3))
    for a, u in enumerate(us):
        for b, v in enumerate(vs):
            sup.D1(float(u), float(v), p, du, dv)
            n = du.Crossed(dv)
            salida[a, b] = (n.X(), n.Y(), n.Z())
    return signo * salida / np.maximum(np.linalg.norm(salida, axis=2, keepdims=True), 1e-12)


def _margen(sup, a, b, otro, largo, extra, eje):
    """Cuánto se extiende el dominio [a, b] de cada lado (en parámetro) para llegar `extra` mm más allá de la cara: nada si la cara
    se cierra sobre sí misma, nada del lado de un polo."""
    def valor(x, y):
        return sup.Value(x, y) if eje == 0 else sup.Value(y, x)

    if all(valor(a, y).Distance(valor(b, y)) < 1e-7 for y in otro):
        return 0.0, 0.0
    uno = extra * (b - a) / largo
    return tuple(0.0 if valor(x, otro[0]).Distance(valor(x, otro[1])) < 1e-7 else uno for x in (a, b))


def _prolongar(forma, cara, alto, normal):
    """`forma` con la cara corrida `alto` mm hacia afuera y las vecinas prolongadas. Una vecina tangente (un empalme) no se puede
    prolongar y el desfase se va de la pieza: si la cara es plana, sube a plomo desde su contorno."""
    from . import solidos_modificar as sm
    if not alto:
        return forma
    maximo = geo.volumen(forma) + 2 * geo.area(cara) * alto
    try:
        crecido = sm.desfasar_caras(forma, [cara], alto, tangente=False)
    except geo.ErrorGeometria:
        crecido = None
    if crecido is not None and geo.solidos(crecido) and geo.volumen(crecido) <= maximo:
        return crecido
    if BRepAdaptor_Surface(cara).GetType() != GeomAbs_Plane:
        raise geo.ErrorGeometria("Las caras vecinas no se pueden prolongar hasta el borde nuevo (pasa con vecinas tangentes a una "
                                 "cara curva): mové puntos de adentro o bajá el borde.")
    return geo.unir_todos([forma, BRepPrimAPI_MakePrism(cara, gp_Vec(*map(float, normal * alto))).Shape()])


def _con_vecinas(forma, cara, nudos_u, nudos_v, desplazamientos):
    """La cara editada con el borde movido, en un sólido: las vecinas se prolongan con un desfase de la cara, cada una sobre su
    propia superficie, y la superficie editada, extendida más allá de la cara, parte el resultado. Queda el lado del cuerpo."""
    from . import solidos_modificar as sm
    u0, u1, v0, v1 = _dominio(cara)
    sup = BRepAdaptor_Surface(cara)
    us, vs = np.linspace(u0, u1, 25), np.linspace(v0, v1, 25)
    normales = _normales(sup, us, vs, -1 if cara.Orientation() == TopAbs_REVERSED else 1)
    campo = _campo(desplazamientos, nudos_u, nudos_v, us, vs)
    avance = (campo * normales).sum(axis=2)
    if np.abs(avance).max() < 1e-6:
        raise geo.ErrorGeometria("Ese movimiento deja el borde sobre la misma superficie: la cara no cambia.")
    largos = _largos(cara)
    alto = float(avance.max()) * 1.25 + 0.02 * min(largos) if avance.max() > 1e-6 else 0.0
    extra = 2 * alto + 0.1 * max(largos)
    antes_u, despues_u = _margen(sup, u0, u1, (v0, v1), largos[0], extra, 0)
    antes_v, despues_v = _margen(sup, v0, v1, (u0, u1), largos[1], extra, 1)
    a, b, c, d = u0 - antes_u, u1 + despues_u, v0 - antes_v, v1 + despues_v
    # con los nudos del campo y los de su extensión, la superficie entra justa en el ajuste
    cortes_u = [x for x in (np.r_[np.unique(nudos_u), u0 - _celda(nudos_u), u1 + _celda(nudos_u)] - a) / (b - a) if 0 < x < 1]
    cortes_v = [x for x in (np.r_[np.unique(nudos_v), v0 - _celda(nudos_v), v1 + _celda(nudos_v)] - c) / (d - c) if 0 < x < 1]
    ajuste = _ajustar(_prolongada(sup, u0, u1, v0, v1), a, b, c, d,
                      lambda x, y: _campo(desplazamientos, nudos_u, nudos_v, x, y, extendido=True), cortes_u, cortes_v, (u0, u1, v0, v1))
    herramienta = BRepBuilderAPI_MakeFace(_superficie(*ajuste[:3]), a, b, c, d, 1e-6).Face()
    propio = next(s for s in geo.solidos(forma) if any(c.IsSame(cara) for c in geo.caras(s)))
    otros = [s for s in geo.solidos(forma) if not s.IsSame(propio)]
    piezas = geo.solidos(sm._partir(_prolongar(propio, cara, alto, normales[12, 12]), [herramienta]))
    if len(piezas) < 2:
        raise geo.ErrorGeometria("La cara editada no corta las vecinas: probá con un desplazamiento menor.")
    dentro, votos = IntTools_FClass2d(cara, 1e-7), [0] * len(piezas)
    clases = [BRepClass3d_SolidClassifier(p) for p in piezas]
    for i, u in enumerate(us):
        for j, v in enumerate(vs):
            if dentro.Perform(gp_Pnt2d(float(u), float(v))) != TopAbs_IN:
                continue
            q = sup.Value(float(u), float(v))
            punto = gp_Pnt(*map(float, np.array([q.X(), q.Y(), q.Z()]) + campo[i, j] - _HUECO_VOTO * normales[i, j]))
            for k, clase in enumerate(clases):
                clase.Perform(punto, 1e-7)
                votos[k] += clase.State() == TopAbs_IN
    quedan = [sm._unificar(p) for p, n in zip(piezas, votos, strict=True) if n] + otros
    if not quedan:
        raise geo.ErrorGeometria("La cara editada no deja material del lado del cuerpo: probá con un desplazamiento menor.")
    return sm._validar(geo.compuesto(quedan) if len(quedan) > 1 else quedan[0], "Editar cara")


def _lamina(cara, nueva):
    """La cara rehecha sobre la superficie `nueva` con las mismas curvas UV: una superficie de una cara, con el borde libre."""
    orientacion, cara = cara.Orientation(), TopoDS.Face(cara.Oriented(TopAbs_FORWARD))

    def alambre(w):
        mw = BRepBuilderAPI_MakeWire()
        exp = BRepTools_WireExplorer(w, cara)
        while exp.More():
            e = exp.Current()
            c, a, b = _pcurva(e, cara)
            mw.Add(TopoDS.Edge(BRepBuilderAPI_MakeEdge(c, nueva, a, b).Edge().Oriented(e.Orientation())))
            exp.Next()
        return mw.Wire()

    afuera = BRepTools.OuterWire_s(cara)
    mf = BRepBuilderAPI_MakeFace(nueva, alambre(afuera), True)
    for w in geo._explorar(cara, TopAbs_WIRE):
        if not w.IsSame(afuera):
            mf.Add(alambre(TopoDS.Wire(w)))
    nueva_cara = mf.Face()
    BRepLib.BuildCurves3d_s(nueva_cara)
    return TopoDS.Face(nueva_cara.Oriented(orientacion))


def _recoser(forma, hoja, otras):
    """La cara rehecha, cosida a las demás de una superficie. Si el borde movido era el que compartía con una de ellas, la costura
    se abre: una superficie no tiene de dónde prolongar a sus vecinas."""
    from . import superficies as sf
    cosidas = sf.bordes_de_costura(geo.caras(forma), _TOLERANCIA_COSTURA)["aristas_cosidas"]
    if sf.bordes_de_costura([hoja, *otras], _TOLERANCIA_COSTURA)["aristas_cosidas"] < cosidas:
        raise geo.ErrorGeometria("En una superficie cosida se puede mover un borde libre, no el que comparte con otra cara: mové "
                                 "puntos de adentro o de un borde libre.")
    return sf.coser([hoja, *otras], _TOLERANCIA_COSTURA)["forma"]


def editar_cara(forma, cara, n_u, n_v, desplazamientos, cortes_u=(), cortes_v=(), espaciado=0.0):
    """Editar cara (Edit Face): mueve puntos de la grilla de `cara` y devuelve el cuerpo con la cara nueva, cosida a sus vecinas.
    `desplazamientos`: {(i, j): (dx, dy, dz)} en mm. Un punto fijo (ver `grilla_cara`) es un error. Si se mueve el contorno, las
    vecinas lo siguen en un sólido; en una superficie se mueven los bordes libres, no los que comparte con otra cara."""
    grilla = grilla_cara(cara, n_u, n_v, cortes_u, cortes_v, espaciado)
    fijos = grilla["fijos"]
    if desplazamientos and not np.isfinite(np.array(list(desplazamientos.values()), float)).all():
        raise geo.ErrorGeometria("Los desplazamientos tienen que ser números finitos.")
    movidos = [p for p, d in desplazamientos.items() if 0 <= p[0] < fijos.shape[0] and 0 <= p[1] < fijos.shape[1] and any(d)]
    for p in movidos:
        if fijos[p]:
            raise geo.ErrorGeometria(f"El punto {p} está en una costura o afuera de la cara: queda fijo.")
    u0, u1, v0, v1 = _dominio(cara)
    nudos_u, nudos_v = _nudos_cara(cara, *divisiones(cara, n_u, n_v, cortes_u, cortes_v, espaciado))
    borde_movido = any(grilla["contorno"][p] for p in movidos)
    if borde_movido and geo.solidos(forma):
        return _con_vecinas(forma, cara, nudos_u, nudos_v, desplazamientos)
    sup = BRepAdaptor_Surface(cara)
    nu, nv, polos, error = _ajustar(sup, u0, u1, v0, v1, lambda us, vs: _campo(desplazamientos, nudos_u, nudos_v, us, vs))
    nueva = _superficie(nu, nv, polos)
    if borde_movido:
        hoja = _lamina(cara, nueva)
        otras = [c for c in geo.caras(forma) if not c.IsSame(cara)]
        if otras:
            hoja = _recoser(forma, hoja, otras)
        if not geo.es_valida(hoja):
            raise geo.ErrorGeometria("La cara editada deja una superficie no válida: probá con un desplazamiento menor.")
        return hoja

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


def curvas_grilla(cara, n_u, n_v, desplazamientos, muestras=48, cortes_u=(), cortes_v=(), espaciado=0.0):
    """Filas y columnas de la cara editada ({"u": [Kx3], "v": [Kx3]}): las curvas de Curvatura en peines."""
    u0, u1, v0, v1 = _dominio(cara)
    nudos_u, nudos_v = _nudos_cara(cara, *divisiones(cara, n_u, n_v, cortes_u, cortes_v, espaciado))
    gu, gv = _greville(nudos_u), _greville(nudos_v)
    tu, tv = np.linspace(u0, u1, muestras), np.linspace(v0, v1, muestras)
    sup = BRepAdaptor_Surface(cara)
    a = _evaluar(sup, tu, gv) + _campo(desplazamientos, nudos_u, nudos_v, tu, gv)
    c = _evaluar(sup, gu, tv) + _campo(desplazamientos, nudos_u, nudos_v, gu, tv)
    return {"u": [a[:, j] for j in range(a.shape[1])], "v": [c[i] for i in range(c.shape[0])]}


_motor.registrar(globals(), _iniciar_opencascade)

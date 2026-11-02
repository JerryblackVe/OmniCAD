# -*- coding: utf-8 -*-
"""Aristas de curvas 3D del boceto (línea, spline, arco, círculo, elipse, cónica), su muestreo, y las operaciones de
modelo que dejan curvas en un boceto 3D: Intersection Curve y Project To Surface de Fusion."""
import math

import numpy as np

from . import geometria as geo


def _pnt(p):
    from OCP.gp import gp_Pnt
    return gp_Pnt(*map(float, p))


def _dir(v):
    from OCP.gp import gp_Dir
    return gp_Dir(*map(float, v))


def _arista(curva):
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge
    return BRepBuilderAPI_MakeEdge(curva).Edge()


def arista_recta(p, q):
    """Arista recta entre dos puntos 3D (equivale a la línea de un boceto 3D de Fusion)."""
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge
    return BRepBuilderAPI_MakeEdge(_pnt(p), _pnt(q)).Edge()


def arista_spline(pts, tangentes=None, cerrada=False):
    """Arista spline por los puntos 3D `pts`; `tangentes` {índice: vector} fija la dirección en esos puntos; `cerrada`
    la cierra suave (periódica) del último punto al primero."""
    from OCP.GeomAPI import GeomAPI_Interpolate
    from OCP.gp import gp_Vec
    from OCP.OCP.collections import Array1_gp_Vec, HArray1_bool, HArray1_gp_Pnt
    tangentes = tangentes or {}
    arr = HArray1_gp_Pnt(1, len(pts))
    for i, p in enumerate(pts):
        arr.SetValue(i + 1, _pnt(p))
    interp = GeomAPI_Interpolate(arr, bool(cerrada), 1e-9)
    if tangentes:
        vecs, flags = Array1_gp_Vec(1, len(pts)), HArray1_bool(1, len(pts))
        for i in range(len(pts)):
            vecs.SetValue(i + 1, gp_Vec(*map(float, tangentes.get(i, (0, 0, 1)))))
            flags.SetValue(i + 1, i in tangentes)
        interp.Load(vecs, flags, True)
    interp.Perform()
    if not interp.IsDone():
        raise geo.ErrorGeometria("No se pudo interpolar la spline 3D.")
    return _arista(interp.Curve())


def arista_arco(a, m, b):
    """Arco de 3 puntos (Fusion: 3D Sketch › Arco): de `a` a `b` pasando por `m`."""
    from OCP.GC import GC_MakeArcOfCircle
    hecho = GC_MakeArcOfCircle(_pnt(a), _pnt(m), _pnt(b))
    if not hecho.IsDone():
        raise geo.ErrorGeometria("Los tres puntos del arco no definen un círculo.")
    return _arista(hecho.Value())


def arista_circulo(centro, radio, normal):
    from OCP.gp import gp_Ax2, gp_Circ
    return _arista_conica(gp_Circ(gp_Ax2(_pnt(centro), _dir(normal)), float(radio)))


def arista_elipse(centro, eje_mayor, radio_menor, normal):
    """Elipse con semieje `eje_mayor` (vector, perpendicular a `normal`) y semieje menor `radio_menor`."""
    from OCP.gp import gp_Ax2, gp_Elips
    eje = np.asarray(eje_mayor, float)
    grande, chico = float(np.linalg.norm(eje)), float(radio_menor)
    if chico > grande:                   # OCC pide mayor ≥ menor: el eje largo pasa a ser el otro
        eje, grande, chico = np.cross(normal, eje) / grande * chico, chico, grande
    return _arista_conica(gp_Elips(gp_Ax2(_pnt(centro), _dir(normal), _dir(eje)), grande, chico))


def _arista_conica(c):
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge
    return BRepBuilderAPI_MakeEdge(c).Edge()


def arista_conica(a, vertice, b, rho):
    """Curva cónica (Fusion: Conic Curve): Bézier racional de extremos a, b, vértice de control y peso rho/(1−rho)."""
    from OCP.Geom import Geom_BezierCurve
    from OCP.OCP.collections import Array1_double, Array1_gp_Pnt
    polos, pesos = Array1_gp_Pnt(1, 3), Array1_double(1, 3)
    for i, (p, w) in enumerate(((a, 1.0), (vertice, rho / (1 - rho)), (b, 1.0))):
        polos.SetValue(i + 1, _pnt(p))
        pesos.SetValue(i + 1, w)
    return _arista(Geom_BezierCurve(polos, pesos))


def compuesto_polilineas(polilineas):
    """Compuesto de aristas rectas de las polilíneas (Nx3): el texto 3D como forma."""
    aristas = [arista_recta(p, q) for poli in polilineas for p, q in zip(poli, poli[1:], strict=False)
               if math.dist(p, q) > 1e-9]
    return geo.compuesto(aristas)


def muestrear(arista, n=48):
    """Polilínea (n+1)x3 float32 sobre la arista, para dibujarla."""
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    ad = BRepAdaptor_Curve(arista)
    t0, t1 = ad.FirstParameter(), ad.LastParameter()
    return np.array([[q.X(), q.Y(), q.Z()] for q in (ad.Value(t0 + (t1 - t0) * i / n) for i in range(n + 1))],
                    np.float32)


def parametrica(arista):
    """La arista como C(t): (f, t0, t1), con `f(t)` = (punto, derivada) en arrays xyz y [t0, t1] su tramo."""
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    from OCP.gp import gp_Pnt, gp_Vec
    ad = BRepAdaptor_Curve(arista)

    def f(t):
        p, d = gp_Pnt(), gp_Vec()
        ad.D1(float(t), p, d)
        return np.array([p.X(), p.Y(), p.Z()]), np.array([d.X(), d.Y(), d.Z()])
    return f, ad.FirstParameter(), ad.LastParameter()


def longitud(forma):
    """Largo exacto (a 1e-9 mm) de una arista o de las aristas de un compuesto. `geo.longitud` (GProp) se queda corto
    en las elipses: 36,49 en vez de 36,37 mm para semiejes 8 y 3."""
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    from OCP.GCPnts import GCPnts_AbscissaPoint
    return sum(GCPnts_AbscissaPoint.Length_s(BRepAdaptor_Curve(e), 1e-9) for e in aristas_de(forma))


def aristas_de(forma):
    from OCP.TopAbs import TopAbs_EDGE
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopoDS import TopoDS
    ex, salida = TopExp_Explorer(forma, TopAbs_EDGE), []
    while ex.More():
        salida.append(TopoDS.Edge(ex.Current()))
        ex.Next()
    return salida


# ---------------------------------------------------------------- Intersection Curve / Project To Surface
def cara_de_plano(origen, normal, medio=1e4):
    """Cara plana finita (±`medio` mm) para cortar con un plano de construcción."""
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace
    from OCP.gp import gp_Pln
    return BRepBuilderAPI_MakeFace(gp_Pln(_pnt(origen), _dir(normal)), -medio, medio, -medio, medio).Face()


def extruir_arista(arista, direccion, medio=1e4):
    """Superficie que barre la arista a lo largo de `direccion` (±`medio` mm): la extrusión virtual de una curva de
    boceto que usa Intersection Curve."""
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
    from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism
    from OCP.gp import gp_Trsf, gp_Vec
    d = np.asarray(direccion, float) / np.linalg.norm(direccion)
    t = gp_Trsf()
    t.SetTranslation(gp_Vec(*(-d * medio)))
    base = BRepBuilderAPI_Transform(arista, t, True).Shape()
    return BRepPrimAPI_MakePrism(base, gp_Vec(*(d * 2 * medio))).Shape()


def seccion(a, b):
    """Aristas donde se cortan las formas `a` y `b` (Fusion: Intersection Curve)."""
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Section
    corte = BRepAlgoAPI_Section(a, b)
    corte.Build()
    if not corte.IsDone():
        raise geo.ErrorGeometria("No se pudo calcular la intersección.")
    return aristas_de(corte.Shape())


def proyectar_vector(arista, forma, direccion, ambos=False):
    """Proyección de la arista sobre `forma` a lo largo de `direccion` (Project To Surface › Along Vector). Se queda
    con lo que cae del lado al que apunta la dirección; con `ambos`, de los dos lados."""
    from OCP.BRepProj import BRepProj_Projection
    proy = BRepProj_Projection(arista, forma, _dir(direccion))
    if not proy.IsDone():
        return []
    d = np.asarray(direccion, float)
    origen = muestrear(arista, 4).astype(float)
    salida = []
    for e in aristas_de(proy.Shape()):
        if ambos or np.mean((muestrear(e, 4) - origen) @ d) >= -1e-6:
            salida.append(e)
    return salida


def proyectar_cercano(arista, forma, n=48):
    """Puntos (n+1)x3 de la arista llevados al punto más cercano de `forma` (Project To Surface › Closest Point)."""
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeVertex
    from OCP.BRepExtrema import BRepExtrema_DistShapeShape
    salida = []
    for p in muestrear(arista, n).astype(float):
        dist = BRepExtrema_DistShapeShape(BRepBuilderAPI_MakeVertex(_pnt(p)).Vertex(), forma)
        if not dist.IsDone() or dist.NbSolution() == 0:
            raise geo.ErrorGeometria("No se pudo proyectar un punto sobre la cara.")
        q = dist.PointOnShape2(1)
        salida.append([q.X(), q.Y(), q.Z()])
    return np.array(salida)


def describir(arista, muestras=32):
    """La arista como curva de boceto 3D, en coordenadas del mundo: {"tipo": "linea", "puntos": [p, q]},
    {"tipo": "circulo", "centro", "radio", "normal"}, {"tipo": "arco", "puntos": [a, m, b]},
    {"tipo": "elipse", "centro", "eje_mayor", "radio_menor", "normal"} o, si es otra curva, una spline de ajuste por
    `muestras`+1 puntos."""
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    from OCP.GeomAbs import GeomAbs_Circle, GeomAbs_Ellipse, GeomAbs_Line
    ad = BRepAdaptor_Curve(arista)
    t0, t1, tipo = ad.FirstParameter(), ad.LastParameter(), ad.GetType()
    xyz = lambda q: [q.X(), q.Y(), q.Z()]  # noqa: E731
    cerrada = abs(t1 - t0 - 2 * math.pi) < 1e-7
    if tipo == GeomAbs_Line:
        return {"tipo": "linea", "puntos": [xyz(ad.Value(t0)), xyz(ad.Value(t1))]}
    if tipo == GeomAbs_Circle:
        c = ad.Circle()
        if cerrada:
            return {"tipo": "circulo", "centro": xyz(c.Location()), "radio": c.Radius(),
                    "normal": xyz(c.Axis().Direction())}
        return {"tipo": "arco", "puntos": [xyz(ad.Value(t)) for t in (t0, (t0 + t1) / 2, t1)]}
    if tipo == GeomAbs_Ellipse and cerrada:
        e = ad.Ellipse()
        x = np.array(xyz(e.XAxis().Direction())) * e.MajorRadius()
        return {"tipo": "elipse", "centro": xyz(e.Location()), "eje_mayor": list(x), "radio_menor": e.MinorRadius(),
                "normal": xyz(e.Axis().Direction())}
    pts = muestrear(arista, muestras).astype(float)
    cerrada = math.dist(pts[0], pts[-1]) < 1e-7      # cerrada: spline periódica, sin repetir el primer punto
    return {"tipo": "spline", "puntos": [list(p) for p in (pts[:-1] if cerrada else pts)], "cerrada": cerrada}


# ---------------------------------------------------------------- Curva isoparamétrica (Project/Include › Isoparametric Curve)
TOPE_ISO = 200                 # curvas por pedido: más es un error de unidad (distancia en mm contra una cara enorme)
_MUESTRAS_ISO = 120            # shortcut: se busca dónde la curva está dentro de la cara con 120 muestras; un recorte
#                                más fino que 1/120 del largo de la cara (un agujero diminuto) no se ve


def _dentro(clasificador, cara, uv, tol):
    """¿Cae (u, v) dentro de la cara o sobre su borde? Un solo `BRepClass_FaceClassifier` sirve para todas las consultas."""
    from OCP.gp import gp_Pnt2d
    from OCP.TopAbs import TopAbs_IN, TopAbs_ON
    clasificador.Perform(cara, gp_Pnt2d(*uv), tol)
    return clasificador.State() in (TopAbs_IN, TopAbs_ON)


def _tramos_dentro(clasificador, cara, t0, t1, fijo, par, tol):
    """Intervalos [a, b] del parámetro de `curva` (entre t0 y t1) cuya posición cae dentro de la cara. `par(t)` arma el
    (u, v) con el parámetro libre t y el fijo; los bordes se afinan por bisección."""
    ts = [t0 + (t1 - t0) * i / _MUESTRAS_ISO for i in range(_MUESTRAS_ISO + 1)]
    estado = [_dentro(clasificador, cara, par(t, fijo), tol) for t in ts]

    def borde(fuera, dentro):
        for _ in range(45):
            m = (fuera + dentro) / 2
            fuera, dentro = (fuera, m) if _dentro(clasificador, cara, par(m, fijo), tol) else (m, dentro)
        return dentro
    tramos, inicio = [], (ts[0] if estado[0] else None)
    for i in range(1, len(ts)):
        if estado[i] and not estado[i - 1]:
            inicio = borde(ts[i - 1], ts[i])
        elif estado[i - 1] and not estado[i]:
            tramos.append((inicio, borde(ts[i], ts[i - 1])))
            inicio = None
    if inicio is not None:
        tramos.append((inicio, ts[-1]))
    return [(a, b) for a, b in tramos if b - a > 1e-7 * (t1 - t0)]


def isoparametricas(cara, punto, direccion="u", tipo="single", distancia=None, cantidad=None):
    """Curvas isoparamétricas de `cara` (Fusion: Isoparametric Curve), cada una como `describir` (coordenadas del
    mundo), recortadas al contorno de la cara. La curva de dirección «u» sigue el parámetro U (V constante) y la «v»
    el parámetro V; «both» da las dos. «single» es la que pasa por `punto` (se proyecta a la cara). «distributed»:
    las de toda la cara, a lo ancho de cada dirección, en una de dos formas (se mide a lo largo de la curva
    perpendicular que pasa por `punto`): con `distancia`, una curva cada tantos mm, una pasando por el punto; con
    `cantidad`, ese número de curvas parejas, sin tocar los bordes (Fusion real: la k-ésima de n cae en k/(n+1))."""
    from OCP.BRep import BRep_Tool
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge
    from OCP.BRepClass import BRepClass_FaceClassifier
    from OCP.BRepTools import BRepTools
    from OCP.GCPnts import GCPnts_AbscissaPoint
    from OCP.GeomAdaptor import GeomAdaptor_Curve
    from OCP.ShapeAnalysis import ShapeAnalysis_Surface
    from OCP.TopoDS import TopoDS
    if direccion not in ("u", "v", "both") or tipo not in ("single", "distributed"):
        raise geo.ErrorGeometria("Dirección: u, v o both. Tipo: single o distributed.")
    if tipo == "distributed":
        if (distancia is None) == (cantidad is None):
            raise geo.ErrorGeometria("Distribuidas: dá la distancia entre curvas o la cantidad, una de las dos.")
        if distancia is not None and not distancia > 0 or cantidad is not None and not cantidad >= 1:
            raise geo.ErrorGeometria("La distancia tiene que ser mayor que 0 y la cantidad, de 1 o más.")
    try:
        cara = TopoDS.Face(cara)
    except Exception as e:  # noqa: BLE001 — OCP lanza TypeError o Standard_Failure según la forma
        raise geo.ErrorGeometria("La curva isoparamétrica se saca de una cara.") from e
    sup = BRep_Tool.Surface_s(cara)
    u0, u1, v0, v1 = BRepTools.UVBounds_s(cara)
    uv = ShapeAnalysis_Surface(sup).ValueOfUV(_pnt(punto), 1e-6)
    tol = 1e-6
    clasificador = BRepClass_FaceClassifier()
    if not _dentro(clasificador, cara, (uv.X(), uv.Y()), tol):
        raise geo.ErrorGeometria("El punto no cae sobre la cara: elegí un punto de la cara.")
    p_u, p_v = uv.X(), uv.Y()
    salida = []
    for sentido in (("u", "v") if direccion == "both" else (direccion,)):
        libre, fijo0 = ((u0, u1), p_v) if sentido == "u" else ((v0, v1), p_u)          # recorre `libre`, queda `fijo`
        ancho = (v0, v1) if sentido == "u" else (u0, u1)                               # a lo ancho se reparte
        iso = (lambda t: sup.VIso(t)) if sentido == "u" else (lambda t: sup.UIso(t))
        par = (lambda t, f: (t, f)) if sentido == "u" else (lambda t, f: (f, t))
        if tipo == "single":
            fijos = [fijo0]
        else:
            ref = GeomAdaptor_Curve(sup.UIso(p_u) if sentido == "u" else sup.VIso(p_v), *ancho)
            largo = GCPnts_AbscissaPoint.Length_s(ref)
            if cantidad is not None:
                pasos = [(i + 1) * largo / (int(cantidad) + 1) for i in range(int(cantidad))]
            else:
                s0 = GCPnts_AbscissaPoint.Length_s(ref, ancho[0], p_v if sentido == "u" else p_u)
                k0 = math.ceil(-s0 / distancia - 1e-9)
                pasos = [s0 + k * distancia for k in range(k0, int((largo - s0) / distancia + 1e-9) + 1)]
                pasos = [s for s in pasos if 1e-9 < s < largo - 1e-9]
            if len(pasos) > TOPE_ISO:
                raise geo.ErrorGeometria(f"Salen {len(pasos)} curvas: el tope es {TOPE_ISO}. Subí la distancia o bajá la cantidad.")
            fijos = [GCPnts_AbscissaPoint(ref, s, ancho[0]).Parameter() for s in pasos]
        for f in fijos:
            curva = iso(f)
            for a, b in _tramos_dentro(clasificador, cara, *libre, f, par, tol):
                salida.append(describir(BRepBuilderAPI_MakeEdge(curva, a, b).Edge()))
    if not salida:
        raise geo.ErrorGeometria("La cara no deja ninguna curva con esos valores.")
    return salida

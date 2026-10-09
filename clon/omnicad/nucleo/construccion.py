# -*- coding: utf-8 -*-
"""
Geometría de construcción: el menú CONSTRUIR de Fusion 360 (planos, ejes y puntos de construcción)
y el sistema de coordenadas de usuario (SCU).

Representación (sin objetos nuevos pesados):
- plano → `geo.Plano` (origen, normal, u, v);
- eje   → `Eje(punto, direccion)`: una tupla con nombre (punto numpy y dirección unitaria numpy);
- punto → numpy (3,).

Las entradas aceptan lo que el usuario puede elegir en el lienzo: caras/aristas/vértices OCC,
`geo.Plano` (o su nombre "XY"/"XZ"/"YZ"), ejes y puntos numpy. `plano_de`, `eje_de` y `punto_de`
hacen esa conversión.
"""
import math
from typing import NamedTuple

import numpy as np
from OCP.BRep import BRep_Tool
from OCP.BRepAdaptor import BRepAdaptor_CompCurve, BRepAdaptor_Curve, BRepAdaptor_Surface
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeVertex, BRepBuilderAPI_MakeWire
from OCP.BRepExtrema import BRepExtrema_DistShapeShape, BRepExtrema_IsOnEdge
from OCP.BRepTools import BRepTools
from OCP.GCPnts import GCPnts_AbscissaPoint
from OCP.GeomAbs import (GeomAbs_Circle, GeomAbs_Cone, GeomAbs_Cylinder, GeomAbs_Ellipse, GeomAbs_Line,
                         GeomAbs_Plane, GeomAbs_Sphere, GeomAbs_SurfaceOfRevolution, GeomAbs_Torus)
from OCP.GeomAPI import GeomAPI_ProjectPointOnSurf
from OCP.OCP.collections import List_TopoDS_Shape
from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE, TopAbs_REVERSED, TopAbs_VERTEX, TopAbs_WIRE
from OCP.TopoDS import TopoDS, TopoDS_Shape
from OCP.gp import gp_Ax1, gp_Pnt, gp_Vec

from . import geometria as geo


class Eje(NamedTuple):
    """Eje de construcción: punto por el que pasa y dirección unitaria."""
    punto: np.ndarray
    direccion: np.ndarray


# ---------------------------------------------------------------- utilidades
def _np(p):
    return np.array([p.X(), p.Y(), p.Z()], float)


def _pnt(p):
    return gp_Pnt(*map(float, p))


def _unitario(v, que="La dirección"):
    v = np.asarray(v, float)
    n = np.linalg.norm(v)
    if n < 1e-12:
        raise geo.ErrorGeometria(f"{que} no puede ser nula.")
    return v / n


def _rotar(v, eje, angulo_rad):
    """Rotación de Rodrigues de v alrededor del eje unitario."""
    c, s = math.cos(angulo_rad), math.sin(angulo_rad)
    return v * c + np.cross(eje, v) * s + eje * float(eje @ v) * (1 - c)


def _tipo(entidad, tipo):
    return isinstance(entidad, TopoDS_Shape) and entidad.ShapeType() == tipo


def _arista(entidad):
    if not _tipo(entidad, TopAbs_EDGE):
        raise geo.ErrorGeometria("Se esperaba una arista.")
    return TopoDS.Edge(entidad)


def _cara(entidad):
    if not _tipo(entidad, TopAbs_FACE):
        raise geo.ErrorGeometria("Se esperaba una cara.")
    return TopoDS.Face(entidad)


def _evaluar(cara, u, v):
    """Punto, normal (según la orientación de la cara) y derivadas en (u, v)."""
    s = BRepAdaptor_Surface(cara)
    p, du, dv = gp_Pnt(), gp_Vec(), gp_Vec()
    s.D1(u, v, p, du, dv)
    n = _unitario(np.cross(_np(du), _np(dv)), "La normal de la cara")
    if cara.Orientation() == TopAbs_REVERSED:
        n = -n
    return _np(p), n, _np(du), _np(dv)


def _proyectar_en_cara(cara, punto):
    proy = GeomAPI_ProjectPointOnSurf(_pnt(punto), BRep_Tool.Surface_s(cara))
    if proy.NbPoints() == 0:
        raise geo.ErrorGeometria("No se pudo proyectar el punto sobre la cara.")
    return proy.LowerDistanceParameters()


def _alambre(aristas):
    if _tipo(aristas, TopAbs_WIRE):
        return TopoDS.Wire(aristas)
    lista = List_TopoDS_Shape()
    for e in ([aristas] if isinstance(aristas, TopoDS_Shape) else list(aristas)):
        lista.Append(_arista(e))
    mw = BRepBuilderAPI_MakeWire()
    mw.Add(lista)
    if not mw.IsDone():
        raise geo.ErrorGeometria("La ruta tiene que ser una cadena de aristas conectadas.")
    return mw.Wire()


def _en_ruta(aristas, distancia, absoluta):
    """(punto, tangente) a una distancia a lo largo de la ruta; fuera de [0, largo] se prolonga
    en línea recta por la tangente del extremo (Fusion deja pasarse del final)."""
    curva = BRepAdaptor_CompCurve(_alambre(aristas))
    largo = GCPnts_AbscissaPoint.Length_s(curva)
    s = float(distancia) if absoluta else float(distancia) * largo
    s_dentro = min(max(s, 0.0), largo)
    u = GCPnts_AbscissaPoint(curva, s_dentro, curva.FirstParameter()).Parameter()
    p, v = gp_Pnt(), gp_Vec()
    curva.D1(u, p, v)
    t = _unitario(_np(v), "La tangente de la ruta")
    return _np(p) + t * (s - s_dentro), t


# ---------------------------------------------------------------- conversiones
def punto_de(entidad):
    """numpy (3,) desde un punto numpy/lista, gp_Pnt o vértice OCC."""
    if isinstance(entidad, gp_Pnt):
        return _np(entidad)
    if isinstance(entidad, TopoDS_Shape):
        if entidad.ShapeType() != TopAbs_VERTEX:
            raise geo.ErrorGeometria("Se esperaba un vértice o un punto.")
        return _np(BRep_Tool.Pnt_s(TopoDS.Vertex(entidad)))
    p = np.asarray(entidad, float)
    if p.shape != (3,):
        raise geo.ErrorGeometria("Un punto necesita tres coordenadas.")
    return p


def plano_de(entidad):
    """`geo.Plano` desde un plano, su nombre ("XY", "XZ", "YZ") o una cara plana."""
    if isinstance(entidad, geo.Plano):
        return entidad
    if isinstance(entidad, str):
        return geo.Plano(entidad)
    pl = geo.plano_de_cara(_cara(entidad))
    if pl is None:
        raise geo.ErrorGeometria("La cara no es plana.")
    return pl


def eje_de(entidad):
    """`Eje` desde un eje/tupla (punto, dirección), gp_Ax1, arista recta o circular (su eje) o cara de
    revolución (cilindro, cono, toroide, esfera)."""
    if isinstance(entidad, gp_Ax1):
        return Eje(_np(entidad.Location()), _np(entidad.Direction()))
    if isinstance(entidad, TopoDS_Shape):
        if entidad.ShapeType() == TopAbs_FACE:
            return eje_cilindro(entidad)
        arista = _arista(entidad)
        if BRepAdaptor_Curve(arista).GetType() == GeomAbs_Circle:
            circ = BRepAdaptor_Curve(arista).Circle()
            return Eje(_np(circ.Location()), _np(circ.Axis().Direction()))
        return eje_arista(arista)
    punto, direccion = entidad
    return Eje(punto_de(punto), _unitario(direccion, "La dirección del eje"))


# ---------------------------------------------------------------- planos
def plano_desfase(base, distancia):
    """Plano desfasado [SLD-CONSTRUCT-OFFSET-PLANE] de un plano o cara plana."""
    return plano_de(base).desplazado(distancia, "Plano desfasado")


def plano_en_angulo(plano_base, eje_punto, eje_dir, angulo, *, desfase=0.0):
    """Plano en ángulo [SLD-CONSTRUCT-PLANE-AT-ANGLE]: contiene el eje y está girado `angulo` grados
    (regla de la mano derecha alrededor del eje) respecto de `plano_base`. El eje es (`eje_punto`,
    `eje_dir`), o una arista recta / `Eje` en `eje_punto` con `eje_dir=None`."""
    base = plano_de(plano_base)
    eje = eje_de(eje_punto) if eje_dir is None else Eje(punto_de(eje_punto), _unitario(eje_dir))
    a = eje.direccion
    n0 = base.normal - a * float(base.normal @ a)
    if np.linalg.norm(n0) < 1e-9:
        raise geo.ErrorGeometria("El eje es perpendicular al plano base: el ángulo no está definido.")
    n = _rotar(n0 / np.linalg.norm(n0), a, math.radians(angulo))
    origen = eje.punto + a * float((base.origen - eje.punto) @ a)
    return geo.Plano.desde_marco(origen, n, a, "Plano en ángulo").desplazado(desfase)


def plano_tangente(cara_curva, punto_referencia_o_angulo, plano_ref=None, *, desfase=0.0):
    """Plano tangente [SLD-CONSTRUCT-TANGENT-PLANE] a una cara cilíndrica o cónica.

    Con un punto (numpy o vértice): tangente donde la cara está más cerca del punto. Con un número:
    ángulo en grados alrededor del eje, medido desde la normal de `plano_ref` (si se da) o desde el
    eje X propio de la superficie; a media altura de la cara. Normal hacia afuera de la cara."""
    cara = _cara(cara_curva)
    sup = BRepAdaptor_Surface(cara)
    if sup.GetType() not in (GeomAbs_Cylinder, GeomAbs_Cone):
        raise geo.ErrorGeometria("El plano tangente necesita una cara cilíndrica o cónica.")
    if isinstance(punto_referencia_o_angulo, (int, float)):
        pos = sup.Cylinder().Position() if sup.GetType() == GeomAbs_Cylinder else sup.Cone().Position()
        a, x, y = _np(pos.Direction()), _np(pos.XDirection()), _np(pos.YDirection())
        ref = x
        if plano_ref is not None:
            r = plano_de(plano_ref).normal
            r = r - a * float(r @ a)
            if np.linalg.norm(r) < 1e-9:
                raise geo.ErrorGeometria("El plano de referencia es perpendicular al eje de la cara.")
            ref = r / np.linalg.norm(r)
        w = _rotar(ref, a, math.radians(punto_referencia_o_angulo))
        _, _, v0, v1 = BRepTools.UVBounds_s(cara)
        u, v = math.atan2(float(w @ y), float(w @ x)), (v0 + v1) / 2
    else:
        u, v = _proyectar_en_cara(cara, punto_de(punto_referencia_o_angulo))
    p, n, _, dv = _evaluar(cara, u, v)
    return geo.Plano.desde_marco(p, n, dv, "Plano tangente").desplazado(desfase)


def plano_medio(a, b):
    """Plano medio [SLD-CONSTRUCT-MIDPLANE] entre dos planos o caras planas.

    Paralelos: a mitad de distancia (normal la de `a`). No paralelos: el bisector que contiene la
    recta de intersección, con normal ∝ nA − nB (con caras de un sólido, de normales hacia afuera,
    es el bisector que cruza el material)."""
    pa, pb = plano_de(a), plano_de(b)
    if abs(abs(float(pa.normal @ pb.normal)) - 1.0) < 1e-9:
        d = float((pb.origen - pa.origen) @ pa.normal)
        return geo.Plano.desde_marco(pa.origen + pa.normal * d / 2, pa.normal, pa.u, "Plano medio")
    eje = eje_dos_planos(pa, pb)
    return geo.Plano.desde_marco(eje.punto, pa.normal - pb.normal, eje.direccion, "Plano medio")


def plano_dos_aristas(e1, e2, *, desfase=0.0):
    """Plano por dos aristas rectas o ejes coplanares [SLD-CONSTRUCT-PLANE-THROUGH-TWO-EDGES]."""
    a, b = eje_de(e1), eje_de(e2)
    n = np.cross(a.direccion, b.direccion)
    if np.linalg.norm(n) < 1e-9:   # paralelas: el plano lo fija el segmento que las une
        n = np.cross(a.direccion, b.punto - a.punto)
        if np.linalg.norm(n) < 1e-9:
            raise geo.ErrorGeometria("Las aristas son colineales: hay infinitos planos.")
    n = n / np.linalg.norm(n)
    if abs(float((b.punto - a.punto) @ n)) > 1e-6:
        raise geo.ErrorGeometria("No existe un plano que contenga ambas aristas (se cruzan sin cortarse).")
    return geo.Plano.desde_marco(a.punto, n, a.direccion, "Plano por dos aristas").desplazado(desfase)


def plano_tres_puntos(p1, p2, p3, *, desfase=0.0):
    """Plano por tres puntos o vértices [SLD-CONSTRUCT-PLANE-THROUGH-THREE-POINTS]."""
    a, b, c = punto_de(p1), punto_de(p2), punto_de(p3)
    n = np.cross(b - a, c - a)
    if np.linalg.norm(n) < 1e-9:
        raise geo.ErrorGeometria("Los tres puntos están alineados: no definen un plano.")
    return geo.Plano.desde_marco(a, n, b - a, "Plano por tres puntos").desplazado(desfase)


def plano_perpendicular(cara_o_arista, punto, *, direccion="U", distancia=0.0):
    """Plano perpendicular [SLD-CONSTRUCT-PLANE-TANGENT-TO-FACE-AT-POINT].

    Arista: plano normal a la curva en el punto de la curva más cercano a `punto`. Cara o plano:
    plano que pasa por `punto` (proyectado) y contiene la normal de la cara; su normal es la dirección
    U o V de la cara en ese punto (Plane Direction). `distancia` lo corre sobre su propia normal."""
    if direccion not in ("U", "V"):
        raise geo.ErrorGeometria("La dirección del plano perpendicular es 'U' o 'V'.")
    q = punto_de(punto)
    if _tipo(cara_o_arista, TopAbs_EDGE):
        arista = TopoDS.Edge(cara_o_arista)
        curva = BRepAdaptor_Curve(arista)
        dist = BRepExtrema_DistShapeShape(BRepBuilderAPI_MakeVertex(_pnt(q)).Vertex(), arista)
        if not dist.IsDone() or dist.NbSolution() == 0:
            raise geo.ErrorGeometria("No se pudo ubicar el punto sobre la arista.")
        if dist.SupportTypeShape2(1) == BRepExtrema_IsOnEdge:
            u = dist.ParOnEdgeS2(1)[0]
        else:   # el punto más cercano es un extremo
            u0, u1 = curva.FirstParameter(), curva.LastParameter()
            u = min((u0, u1), key=lambda w: np.linalg.norm(_np(curva.Value(w)) - q))
        pc, v = gp_Pnt(), gp_Vec()
        curva.D1(u, pc, v)
        p = _np(pc)
        t = _unitario(_np(v), "La tangente de la arista")
        if arista.Orientation() == TopAbs_REVERSED:
            t = -t
        return geo.Plano.desde_marco(p, t, np.zeros(3), "Plano perpendicular").desplazado(distancia)
    if isinstance(cara_o_arista, (geo.Plano, str)) or geo.plano_de_cara(_cara(cara_o_arista)) is not None:
        pl = plano_de(cara_o_arista)
        p = q - pl.normal * float((q - pl.origen) @ pl.normal)
        n, du, dv = pl.normal, pl.u, pl.v
    else:
        cara = _cara(cara_o_arista)
        p, n, du, dv = _evaluar(cara, *_proyectar_en_cara(cara, q))
    eje = du if direccion == "U" else dv
    eje = eje - n * float(eje @ n)
    return geo.Plano.desde_marco(p, eje, n, "Plano perpendicular").desplazado(distancia)


def plano_en_ruta(aristas_ruta, distancia_rel, *, absoluta=False):
    """Plano a lo largo de una ruta [SLD-CONSTRUCT-PLANE-ALONG-PATH], normal a la ruta.
    `distancia_rel` es la proporción del largo (Proportional); con `absoluta=True`, milímetros."""
    p, t = _en_ruta(aristas_ruta, distancia_rel, absoluta)
    return geo.Plano.desde_marco(p, t, np.zeros(3), "Plano en ruta")


# ---------------------------------------------------------------- ejes
def eje_cilindro(cara):
    """Eje por cilindro/cono/toroide [SLD-CONSTRUCT-AXIS-THROUGH-CYLINDER-CONE-TORUS] (también esfera
    y superficie de revolución). El punto es la proyección del centro de la cara sobre el eje."""
    sup = BRepAdaptor_Surface(_cara(cara))
    tipo = sup.GetType()
    if tipo == GeomAbs_Cylinder:
        ax = sup.Cylinder().Axis()
    elif tipo == GeomAbs_Cone:
        ax = sup.Cone().Axis()
    elif tipo == GeomAbs_Torus:
        ax = sup.Torus().Axis()
    elif tipo == GeomAbs_Sphere:
        ax = sup.Sphere().Position().Axis()
    elif tipo == GeomAbs_SurfaceOfRevolution:
        ax = sup.AxeOfRevolution()
    else:
        raise geo.ErrorGeometria("La cara no es de revolución (cilindro, cono, toroide o esfera).")
    o, d = _np(ax.Location()), _unitario(_np(ax.Direction()))
    c = np.array(geo.centro_masa(cara, superficie=True))
    return Eje(o + d * float((c - o) @ d), d)


def eje_perpendicular_cara(cara, punto):
    """Eje perpendicular a una cara (o plano) en un punto [SLD-CONSTRUCT-AXIS-PERPENDICULAR-AT-POINT].
    El punto se proyecta sobre la cara; la dirección es su normal (hacia afuera)."""
    q = punto_de(punto)
    if isinstance(cara, (geo.Plano, str)):
        pl = plano_de(cara)
        return Eje(q - pl.normal * float((q - pl.origen) @ pl.normal), pl.normal.copy())
    cara = _cara(cara)
    p, n, _, _ = _evaluar(cara, *_proyectar_en_cara(cara, q))
    return Eje(p, n)


def eje_dos_planos(p1, p2):
    """Eje en la intersección de dos planos o caras planas [SLD-CONSTRUCT-AXIS-THROUGH-TWO-PLANES].
    El punto es el de la recta más cercano al origen."""
    a, b = plano_de(p1), plano_de(p2)
    d = np.cross(a.normal, b.normal)
    if np.linalg.norm(d) < 1e-9:
        raise geo.ErrorGeometria("Los planos son paralelos: no se cortan.")
    c = float(a.normal @ b.normal)
    h1, h2 = float(a.normal @ a.origen), float(b.normal @ b.origen)
    punto = ((h1 - h2 * c) * a.normal + (h2 - h1 * c) * b.normal) / (1 - c * c)
    return Eje(punto, d / np.linalg.norm(d))


def eje_dos_puntos(a, b):
    """Eje por dos puntos o vértices [SLD-CONSTRUCT-AXIS-THROUGH-TWO-POINTS]."""
    pa, pb = punto_de(a), punto_de(b)
    return Eje(pa, _unitario(pb - pa, "La distancia entre los puntos"))


def eje_arista(arista):
    """Eje por una arista recta [SLD-CONSTRUCT-AXIS-THROUGH-EDGE], en el sentido de la arista."""
    arista = _arista(arista)
    curva = BRepAdaptor_Curve(arista)
    if curva.GetType() != GeomAbs_Line:
        raise geo.ErrorGeometria("La arista tiene que ser recta.")
    p0, p1 = _np(curva.Value(curva.FirstParameter())), _np(curva.Value(curva.LastParameter()))
    if arista.Orientation() == TopAbs_REVERSED:
        p0, p1 = p1, p0
    return Eje(p0, _unitario(p1 - p0, "La arista"))


# ---------------------------------------------------------------- puntos
def punto_vertice(v):
    """Punto en un vértice [SLD-CONSTRUCT-POINT-AT-VERTEX]."""
    return punto_de(v)


def punto_dos_aristas(e1, e2):
    """Punto por dos aristas [SLD-CONSTRUCT-POINT-THROUGH-TWO-EDGES]. Rectas o ejes: intersección de
    sus prolongaciones (si se cruzan sin cortarse, el punto medio de la perpendicular común). Curvas:
    punto medio entre los puntos más cercanos de ambas aristas (no se prolongan)."""
    rectas = all(not isinstance(e, TopoDS_Shape) or BRepAdaptor_Curve(_arista(e)).GetType() == GeomAbs_Line
                 for e in (e1, e2))
    if rectas:
        a, b = eje_de(e1), eje_de(e2)
        c = float(a.direccion @ b.direccion)
        if abs(abs(c) - 1.0) < 1e-12:
            raise geo.ErrorGeometria("Las aristas son paralelas: no se cortan.")
        w = a.punto - b.punto
        d1, d2 = float(a.direccion @ w), float(b.direccion @ w)
        s = (c * d2 - d1) / (1 - c * c)
        t = (d2 - c * d1) / (1 - c * c)
        return (a.punto + a.direccion * s + b.punto + b.direccion * t) / 2
    dist = BRepExtrema_DistShapeShape(_arista(e1), _arista(e2))
    if not dist.IsDone() or dist.NbSolution() == 0:
        raise geo.ErrorGeometria("No se pudo calcular el punto entre las aristas.")
    return (_np(dist.PointOnShape1(1)) + _np(dist.PointOnShape2(1))) / 2


def punto_tres_planos(p1, p2, p3):
    """Punto en la intersección de tres planos o caras planas [SLD-CONSTRUCT-POINT-THROUGH-THREE-PLANES]."""
    planos = [plano_de(p) for p in (p1, p2, p3)]
    m = np.array([p.normal for p in planos])
    if abs(np.linalg.det(m)) < 1e-9:
        raise geo.ErrorGeometria("Los tres planos no se cortan en un único punto (hay dos paralelos o comparten recta).")
    return np.linalg.solve(m, np.array([float(p.normal @ p.origen) for p in planos]))


def punto_centro(entidad):
    """Punto en el centro de un círculo/esfera/toroide [SLD-CONSTRUCT-POINT-AT-CENTER-OF-CIRCLE-SPHERE-TORUS]:
    arista circular o elíptica, cara esférica o toroidal, o cara plana limitada por un círculo."""
    if _tipo(entidad, TopAbs_EDGE):
        curva = BRepAdaptor_Curve(TopoDS.Edge(entidad))
        if curva.GetType() == GeomAbs_Circle:
            return _np(curva.Circle().Location())
        if curva.GetType() == GeomAbs_Ellipse:
            return _np(curva.Ellipse().Location())
        raise geo.ErrorGeometria("La arista no es circular.")
    cara = _cara(entidad)
    sup = BRepAdaptor_Surface(cara)
    if sup.GetType() == GeomAbs_Sphere:
        return _np(sup.Sphere().Location())
    if sup.GetType() == GeomAbs_Torus:
        return _np(sup.Torus().Location())
    if sup.GetType() == GeomAbs_Plane:
        centros = []
        for e in geo._explorar(BRepTools.OuterWire_s(cara), TopAbs_EDGE):
            curva = BRepAdaptor_Curve(TopoDS.Edge(e))
            if curva.GetType() != GeomAbs_Circle:
                centros = []
                break
            centros.append(_np(curva.Circle().Location()))
        if centros and all(np.allclose(c, centros[0], atol=1e-6) for c in centros):
            return centros[0]
    raise geo.ErrorGeometria("Se esperaba un círculo, una esfera, un toroide o una cara circular.")


def punto_arista_plano(arista, plano):
    """Punto donde una arista recta (o eje), prolongada, corta un plano o cara plana
    [SLD-CONSTRUCT-POINT-AT-EDGE-AND-PLANE]."""
    eje, pl = eje_de(arista), plano_de(plano)
    den = float(pl.normal @ eje.direccion)
    if abs(den) < 1e-12:
        raise geo.ErrorGeometria("La arista es paralela al plano: no lo corta.")
    return eje.punto + eje.direccion * float(pl.normal @ (pl.origen - eje.punto)) / den


def punto_en_ruta(aristas, distancia_rel, *, absoluta=False):
    """Punto a lo largo de una ruta [SLD-CONSTRUCT-POINT-ALONG-PATH]: `distancia_rel` de 0 a 1
    (Proportional; se puede pasar de los extremos); con `absoluta=True`, milímetros (Physical)."""
    return _en_ruta(aristas, distancia_rel, absoluta)[0]


# ---------------------------------------------------------------- sistema de coordenadas
def _direccion_de(entidad):
    if isinstance(entidad, TopoDS_Shape) or isinstance(entidad, Eje) or isinstance(entidad, gp_Ax1):
        return eje_de(entidad).direccion
    return _unitario(entidad)


def scu(origen, eje_x, eje_y=None, *, angulos=(0.0, 0.0, 0.0), desfase=(0.0, 0.0, 0.0)):
    """Sistema de coordenadas de usuario [SLD-DEFINE-UCS]: marco ortonormal derecho.

    `eje_x` manda; `eje_y` se ortogonaliza contra X (si falta, se elige uno perpendicular). Ejes:
    vectores, aristas rectas o `Eje`. `desfase` (Offset X/Y/Z) se mide en los ejes del SCU y
    `angulos` (X/Y/Z Angle, grados) giran el SCU alrededor de sus propios ejes X, luego Y, luego Z.
    Devuelve {"origen", "x", "y", "z", "matriz" (4×4 local→mundo), "plano" (su plano XY)}."""
    o = punto_de(origen)
    x = _direccion_de(eje_x)
    if eje_y is None:
        y = np.cross((0.0, 0.0, 1.0) if abs(x[2]) < 0.9 else (1.0, 0.0, 0.0), x)
    else:
        y = _direccion_de(eje_y)
        y = y - x * float(y @ x)
        if np.linalg.norm(y) < 1e-9:
            raise geo.ErrorGeometria("Los ejes X e Y del SCU son paralelos.")
    y = y / np.linalg.norm(y)
    z = np.cross(x, y)
    o = o + x * float(desfase[0]) + y * float(desfase[1]) + z * float(desfase[2])
    for k, ang in enumerate(angulos):
        if abs(ang) < 1e-12:
            continue
        eje = (x, y, z)[k]
        x, y, z = (_rotar(w, eje, math.radians(ang)) for w in (x, y, z))
    m = np.eye(4)
    m[:3, 0], m[:3, 1], m[:3, 2], m[:3, 3] = x, y, z, o
    return {"origen": o, "x": x, "y": y, "z": z, "matriz": m,
            "plano": geo.Plano.desde_marco(o, z, x, "SCU")}

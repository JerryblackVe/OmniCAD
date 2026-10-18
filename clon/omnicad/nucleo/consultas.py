# -*- coding: utf-8 -*-
"""Consultas geométricas para selección y manipuladores (Medir y Snap de Fusion).

Extraídas de timeline, API, importadores y visor; sin dependencias de interfaz.
"""
import math

import numpy as np
from . import motor as _motor


def _iniciar_opencascade():
    global BRepAdaptor_Curve, BRepAdaptor_Surface, BRepBndLib, BRepBuilderAPI_MakeFace
    global BRepBuilderAPI_MakeVertex, BRepClass3d_SolidClassifier, BRepClass_FaceClassifier
    global BRepExtrema_DistShapeShape, BRepGProp, BRepTools, Bnd_Box, GProp_GProps, GeomAbs_Circle
    global GeomAbs_Cylinder, TopAbs_COMPOUND, TopAbs_EDGE, TopAbs_FACE, TopAbs_IN, TopAbs_ON, TopExp_Explorer
    global TopoDS, TopoDS_Iterator, TopoDS_Shape, gp_Pnt, gp_Trsf, gp_Vec
    from OCP.Bnd import Bnd_Box
    from OCP.BRepAdaptor import BRepAdaptor_Curve, BRepAdaptor_Surface
    from OCP.BRepBndLib import BRepBndLib
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakeVertex
    from OCP.BRepClass import BRepClass_FaceClassifier
    from OCP.BRepClass3d import BRepClass3d_SolidClassifier
    from OCP.BRepExtrema import BRepExtrema_DistShapeShape
    from OCP.BRepGProp import BRepGProp
    from OCP.BRepTools import BRepTools
    from OCP.GeomAbs import GeomAbs_Circle, GeomAbs_Cylinder
    from OCP.GProp import GProp_GProps
    from OCP.TopAbs import TopAbs_COMPOUND, TopAbs_EDGE, TopAbs_FACE, TopAbs_IN, TopAbs_ON
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopoDS import TopoDS, TopoDS_Iterator, TopoDS_Shape
    from OCP.gp import gp_Pnt, gp_Trsf, gp_Vec


if _motor.motor_activo() == "opencascade":
    _iniciar_opencascade()

from . import geometria as geo


def es_forma(forma):
    return isinstance(forma, TopoDS_Shape) and not forma.IsNull()


def vertice(punto):
    return BRepBuilderAPI_MakeVertex(gp_Pnt(*map(float, punto))).Vertex()


def distancia(a, b):
    return BRepExtrema_DistShapeShape(a, b).Value()


def distancia_a_punto(forma, punto):
    d = BRepExtrema_DistShapeShape(forma, vertice(punto))
    return d.Value() if d.IsDone() else math.inf


def centro_lineal(forma):
    p = GProp_GProps()
    BRepGProp.LinearProperties_s(forma, p)
    c = p.CentreOfMass()
    return np.array([c.X(), c.Y(), c.Z()], float)


def centroide(forma):
    """Centro de superficie; en una curva sin área, centro de longitud."""
    p = GProp_GProps()
    BRepGProp.SurfaceProperties_s(forma, p)
    if p.Mass() <= 1e-12:
        return centro_lineal(forma)
    c = p.CentreOfMass()
    return np.array([c.X(), c.Y(), c.Z()])


def dentro_solidos(solidos, punto, tolerancia=1e-7):
    return any(BRepClass3d_SolidClassifier(s, gp_Pnt(*map(float, punto)), tolerancia).State() == TopAbs_IN
               for s in solidos)


def punto_en_cara(cara, punto, tolerancia=1e-3):
    c = BRepClass_FaceClassifier(cara, gp_Pnt(*[float(x) for x in punto]), tolerancia)
    return c.State() in (TopAbs_IN, TopAbs_ON)


def transformacion_identidad():
    return gp_Trsf()


def hijos_compuesto(forma):
    if forma.ShapeType() != TopAbs_COMPOUND:
        return [forma]
    hijos, it = [], TopoDS_Iterator(forma)
    while it.More():
        hijos.append(it.Value())
        it.Next()
    return hijos


def firma_importacion(forma, tipo):
    """Huella original del lector SAB: caja de polos, no la caja ajustada del visor."""
    caja = Bnd_Box()
    BRepBndLib.Add_s(forma, caja, False)
    caras, n = TopExp_Explorer(forma, TopAbs_FACE), 0
    while caras.More():
        n += 1
        caras.Next()
    if caja.IsVoid():
        return (tipo, n)
    p0, p1 = caja.CornerMin(), caja.CornerMax()
    return (tipo, n) + tuple(round(v, 2) for v in (p0.X(), p0.Y(), p0.Z(), p1.X(), p1.Y(), p1.Z()))


def extremos_arista(arista):
    c = BRepAdaptor_Curve(arista)
    p, q = c.Value(c.FirstParameter()), c.Value(c.LastParameter())
    return np.array([p.X(), p.Y(), p.Z()]), np.array([q.X(), q.Y(), q.Z()])


def eje_cara(cara, tipo):
    s = BRepAdaptor_Surface(cara)
    ax = s.Cylinder().Axis() if tipo == "cilindro" else s.Cone().Axis()
    p, d = ax.Location(), ax.Direction()
    return np.array([p.X(), p.Y(), p.Z()]), np.array([d.X(), d.Y(), d.Z()])


def eje_circulo(arista):
    d = BRepAdaptor_Curve(arista).Circle().Axis().Direction()
    return d.X(), d.Y(), d.Z()


def punto_del_eje(cara, p, z, punto_clave):
    s = BRepAdaptor_Surface(cara)
    u = (s.FirstUParameter() + s.LastUParameter()) / 2
    ts = []
    for v in (s.FirstVParameter(), s.LastVParameter()):
        q = s.Value(u, v)
        ts.append(float((np.array([q.X(), q.Y(), q.Z()]) - p) @ z))
    t0, t1 = min(ts), max(ts)
    return p + z * {"inicio": t0, "fin": t1}.get(punto_clave, (t0 + t1) / 2)


def contorno_exterior(cara):
    exterior = BRepTools.OuterWire_s(cara)
    return None if exterior.IsNull() else exterior


def cara_del_contorno(contorno, original):
    region = BRepBuilderAPI_MakeFace(contorno, True)
    return region.Face() if region.IsDone() else original


def punto_y_tangente(forma, fraccion=0.5):
    for e in geo._explorar(forma, TopAbs_EDGE):
        c = BRepAdaptor_Curve(TopoDS.Edge(e))
        a, b = c.FirstParameter(), c.LastParameter()
        p, d = gp_Pnt(), gp_Vec()
        c.D1(a + (b - a) * fraccion, p, d)
        t = np.array([d.X(), d.Y(), d.Z()], float)
        n = float(np.linalg.norm(t))
        return np.array([p.X(), p.Y(), p.Z()], float), (t / n if n > 1e-12 else t)
    return None


def inicio_rosca(cara, invertir=False):
    sup = BRepAdaptor_Surface(cara)
    if sup.GetType() != GeomAbs_Cylinder:
        return None
    eje = sup.Cylinder().Axis()
    loc = np.array([eje.Location().X(), eje.Location().Y(), eje.Location().Z()], float)
    d = np.array([eje.Direction().X(), eje.Direction().Y(), eje.Direction().Z()], float)
    return (loc + d * sup.LastVParameter(), -d) if invertir else (loc + d * sup.FirstVParameter(), d)


def puntos_enganche_cara(cara, maximo=60):
    salida = [(np.array(geo.centro_masa(cara, True), float), "centro")]

    def sumar(p, tipo):
        p = np.array([p.X(), p.Y(), p.Z()], float)
        if len(salida) < maximo and all(float(np.linalg.norm(p - q)) > 1e-4 for q, _ in salida):
            salida.append((p, tipo))

    for e in geo._explorar(cara, TopAbs_EDGE):
        c = BRepAdaptor_Curve(TopoDS.Edge(e))
        a, b = c.FirstParameter(), c.LastParameter()
        sumar(c.Value(a), "vertice")
        sumar(c.Value(b), "vertice")
        if c.GetType() == GeomAbs_Circle:
            sumar(c.Circle().Location(), "centro_arco")
        sumar(c.Value((a + b) / 2), "medio")
    return salida


def _unitario(v):
    v = np.asarray(v, float)
    n = float(np.linalg.norm(v))
    return v / n if n > 1e-12 else v * 0.0


def saliente_de_arista(arista, cuerpo):
    from .solidos_modificar import _ancestros, _padres, _punto_normal
    punto_tang = punto_y_tangente(arista)
    if punto_tang is None:
        return None
    medio, t = punto_tang
    caras = _padres(_ancestros(cuerpo, TopAbs_EDGE, TopAbs_FACE), arista)
    if not caras:
        return None
    cara = TopoDS.Face(caras[0])
    _p, n = _punto_normal(cara)
    d = np.cross(np.asarray(n, float), t)
    if np.linalg.norm(d) < 1e-9:
        return None
    d = d / np.linalg.norm(d)
    if float(d @ (medio - np.array(geo.centro_masa(cara, True)))) < 0:
        d = -d
    return medio, d


def datos_arista(arista, forma_cuerpo):
    from .solidos_modificar import _ancestros, _normal_en_arista, _padres
    c = BRepAdaptor_Curve(arista)
    t = (c.FirstParameter() + c.LastParameter()) / 2
    p = c.Value(t)
    medio = np.array([p.X(), p.Y(), p.Z()])
    caras = _padres(_ancestros(forma_cuerpo, TopAbs_EDGE, TopAbs_FACE), arista)
    if len(caras) != 2:
        d = c.DN(t, 1)
        d = _unitario([d.X(), d.Y(), d.Z()])
        a = np.array([1.0, 0.0, 0.0]) if abs(d[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
        return medio, _unitario(np.cross(d, a)), math.pi / 2
    n1 = _normal_en_arista(arista, TopoDS.Face(caras[0]), t)
    n2 = _normal_en_arista(arista, TopoDS.Face(caras[1]), t)
    bis = _unitario(n1 + n2)
    if np.linalg.norm(bis) < 1e-9:
        bis = _unitario(n1)
    fi = math.acos(max(-1.0, min(1.0, float(n1 @ n2))))
    paso = max(1e-3, 1e-3 * float(np.linalg.norm(medio)))
    q = medio - bis * paso
    hacia = -bis if dentro_solidos([forma_cuerpo], q) else bis
    return medio, hacia, fi


_motor.registrar(globals(), _iniciar_opencascade)

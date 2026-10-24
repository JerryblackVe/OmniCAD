# -*- coding: utf-8 -*-
"""Aristas de curvas 3D del boceto (línea y spline interpolada con tangentes) y su muestreo."""
import numpy as np

from . import geometria as geo


def arista_recta(p, q):
    """Arista recta entre dos puntos 3D (equivale a la línea de un boceto 3D de Fusion)."""
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge
    from OCP.gp import gp_Pnt
    return BRepBuilderAPI_MakeEdge(gp_Pnt(*map(float, p)), gp_Pnt(*map(float, q))).Edge()


def arista_spline(pts, tangentes=None):
    """Arista spline por los puntos 3D `pts`; `tangentes` {índice: vector} fija la dirección en esos puntos."""
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge
    from OCP.GeomAPI import GeomAPI_Interpolate
    from OCP.gp import gp_Pnt, gp_Vec
    from OCP.OCP.collections import Array1_gp_Vec, HArray1_bool, HArray1_gp_Pnt
    tangentes = tangentes or {}
    arr = HArray1_gp_Pnt(1, len(pts))
    for i, p in enumerate(pts):
        arr.SetValue(i + 1, gp_Pnt(*map(float, p)))
    interp = GeomAPI_Interpolate(arr, False, 1e-9)
    if tangentes:
        vecs, flags = Array1_gp_Vec(1, len(pts)), HArray1_bool(1, len(pts))
        for i in range(len(pts)):
            vecs.SetValue(i + 1, gp_Vec(*map(float, tangentes.get(i, (0, 0, 1)))))
            flags.SetValue(i + 1, i in tangentes)
        interp.Load(vecs, flags, True)
    interp.Perform()
    if not interp.IsDone():
        raise geo.ErrorGeometria("No se pudo interpolar la spline 3D.")
    return BRepBuilderAPI_MakeEdge(interp.Curve()).Edge()


def muestrear(arista, n=48):
    """Polilínea (n+1)x3 float32 sobre la arista, para dibujarla."""
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    ad = BRepAdaptor_Curve(arista)
    t0, t1 = ad.FirstParameter(), ad.LastParameter()
    return np.array([[q.X(), q.Y(), q.Z()] for q in (ad.Value(t0 + (t1 - t0) * i / n) for i in range(n + 1))],
                    np.float32)

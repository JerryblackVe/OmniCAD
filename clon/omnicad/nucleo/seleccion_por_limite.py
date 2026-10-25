# -*- coding: utf-8 -*-
"""
Seleccionar › Por límite [Select By Boundary de Fusion]: qué hay dentro o fuera de una caja, un cilindro o una esfera.
Funciones puras sobre formas OCC; la herramienta de la API (`api/herramientas_seleccion.py`) las usa.
"""
import numpy as np

from . import geometria as geo


def limite(forma_tipo, centro, x=None, y=None, z=None, radio=None, largo=None):
    """Sólido del límite centrado en `centro`: "box" (x, y, z), "cylinder" (largo sobre el eje X y radio) o "sphere" (radio)."""
    if forma_tipo == "box":
        for v, n in ((x, "x_size"), (y, "y_size"), (z, "z_size")):
            if not v or v <= 0:
                raise geo.ErrorGeometria(f"La caja necesita x_size, y_size y z_size positivos (falta {n}).")
        return geo.caja(x, y, z, (centro[0] - x / 2, centro[1] - y / 2, centro[2] - z / 2))
    if not radio or radio <= 0:
        raise geo.ErrorGeometria("Falta radius (positivo, en mm).")
    if forma_tipo == "sphere":
        return geo.esfera(radio, centro)
    if not largo or largo <= 0:
        raise geo.ErrorGeometria("El cilindro necesita length (su largo sobre el eje X) positivo.")
    return geo.cilindro(radio, largo, (centro[0] - largo / 2, centro[1], centro[2]), (1, 0, 0))


def puntos_de(sub, centro):
    """Centro y vértices de una cara o arista: con lo que se decide si está dentro del límite."""
    from OCP.BRep import BRep_Tool
    from OCP.TopAbs import TopAbs_VERTEX
    from OCP.TopoDS import TopoDS
    from . import solidos_modificar as sm
    pts = [tuple(np.asarray(centro, float))]
    for v in sm._unicos(sub, TopAbs_VERTEX):
        p = BRep_Tool.Pnt_s(TopoDS.Vertex(v))
        pts.append((p.X(), p.Y(), p.Z()))
    return pts


def clasificador(limite_solido):
    """Función puntos → "inside" (todos dentro) | "outside" (ninguno) | "crossing"."""
    from OCP.BRepClass3d import BRepClass3d_SolidClassifier
    from OCP.gp import gp_Pnt
    from OCP.TopAbs import TopAbs_IN
    clas = BRepClass3d_SolidClassifier(limite_solido)

    def estado(pts):
        dentro = 0
        for p in pts:
            clas.Perform(gp_Pnt(*map(float, p)), 1e-6)
            dentro += clas.State() == TopAbs_IN
        return "inside" if dentro == len(pts) else "outside" if dentro == 0 else "crossing"
    return estado


def estado_de_cuerpo(forma, limite_solido):
    """"inside" | "outside" | "crossing" de un cuerpo respecto del límite, por el volumen que comparten."""
    v = geo.volumen(forma)
    try:
        comun = geo.volumen(geo.booleano(forma, limite_solido, "intersecar"))
    except geo.ErrorGeometria:
        comun = 0.0
    return "inside" if comun > v * (1 - 1e-6) else "outside" if comun < v * 1e-9 else "crossing"

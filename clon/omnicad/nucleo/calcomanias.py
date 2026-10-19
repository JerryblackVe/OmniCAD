"""Calcomanía de Fusion: textura sobre la malla recortada de caras, sin alterar el sólido."""
import math

import numpy as np
from . import motor as _motor


def _iniciar_opencascade():
    global BRepAdaptor_Surface, GeomAbs_Cylinder, TopAbs_REVERSED
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.GeomAbs import GeomAbs_Cylinder
    from OCP.TopAbs import TopAbs_REVERSED


if _motor.motor_activo() == "opencascade":
    _iniciar_opencascade()

from . import geometria as geo
from .solidos_modificar import caras_tangentes


def superficie(cara, cuerpo=None, encadenar=False, centrada=True):
    """Equivale a Calcomanía: marco y triángulos de la cara, con coordenadas físicas de textura.

    En cilindros la anchura mide arco (desarrollo exacto); en las demás caras se proyecta
    desde el plano tangente. El recorte conserva bordes y agujeros de la cara.
    """
    s = BRepAdaptor_Surface(cara, True)
    cilindro = s.GetType() == GeomAbs_Cylinder
    pl = geo.plano_de_cara(cara)
    if pl is None:
        u = (s.FirstUParameter() + s.LastUParameter()) / 2
        v = (s.FirstVParameter() + s.LastVParameter()) / 2
        p = np.array(s.Value(u, v).Coord())
        du = np.array(s.Value(u + 1e-5, v).Coord()) - p
        dv = np.array(s.Value(u, v + 1e-5).Coord()) - p
        normal = np.cross(du, dv)
        if cara.Orientation() == TopAbs_REVERSED:
            normal = -normal
        if np.linalg.norm(du) < 1e-12 or np.linalg.norm(normal) < 1e-15:
            raise geo.ErrorGeometria("No se puede orientar la calcomanía en el polo de esta cara.")
        pl = geo.Plano.desde_marco(p, normal / np.linalg.norm(normal), du / np.linalg.norm(du))
    caras = caras_tangentes(cuerpo, cara) if encadenar and cuerpo is not None else [cara]
    vertices, normales, coords = [], [], []
    origen, eje_u, eje_v = (np.asarray(a, float) for a in (pl.origen, pl.u, pl.v))
    if cilindro:
        cil = s.Cylinder()
        pos = cil.Position()
        centro = np.array(pos.Location().Coord())
        x, y, z = (np.array(d.Coord()) for d in (pos.XDirection(), pos.YDirection(), pos.Direction()))
        a0 = (s.FirstUParameter() + s.LastUParameter()) / 2
    for f in caras:
        pts, ns = geo.teselar(f, 0.05)
        if cilindro:
            d = pts - centro
            ang = np.arctan2(d @ y, d @ x)
            ang = (ang - a0 + math.pi) % (2 * math.pi) - math.pi
            # La costura se abre en el lado opuesto al centro de la calcomanía.
            uv = np.column_stack((ang * cil.Radius(), (pts - origen) @ z))
            arcos = uv[:, 0].reshape(-1, 3)
            cruza = np.ptp(arcos, axis=1) > math.pi * cil.Radius()
            arcos[cruza] = np.where(arcos[cruza] < 0, arcos[cruza] + 2 * math.pi * cil.Radius(), arcos[cruza])
        else:
            uv = np.column_stack(((pts - origen) @ eje_u, (pts - origen) @ eje_v))
        vertices.append(pts + ns * 0.02)
        normales.append(ns)
        coords.append(uv)
    if not coords or not len(coords[0]):
        raise geo.ErrorGeometria("La cara no tiene una malla utilizable para la calcomanía.")
    base = coords[0]
    minimo, maximo = base.min(axis=0), base.max(axis=0)
    tamano = (np.array([(s.LastUParameter() - s.FirstUParameter()) * cil.Radius(),
                       s.LastVParameter() - s.FirstVParameter()]) if cilindro else maximo - minimo)
    desplazamiento = (minimo + maximo) / 2 if centrada and not cilindro else np.zeros(2)
    if np.any(desplazamiento):
        pl = geo.Plano.desde_marco(pl.a_3d(*desplazamiento), pl.normal, pl.u)
    return {"plano": pl, "vertices": np.concatenate(vertices), "normales": np.concatenate(normales),
            "coordenadas": np.concatenate(coords) - desplazamiento,
            "tamano": tamano, "caras": len(caras)}


def textura(coordenadas, ancho, alto, dx=0, dy=0, angulo=0, voltear_h=False, voltear_v=False):
    """Transformación inversa de Calcomanía: coordenadas de cara en mm → UV de imagen."""
    valores = np.asarray([ancho, alto, dx, dy, angulo], float)
    if not np.isfinite(valores).all() or ancho <= 0 or alto <= 0:
        raise geo.ErrorGeometria("Las medidas de la calcomanía deben ser finitas y positivas.")
    a = math.radians(angulo)
    c, s = math.cos(a), math.sin(a)
    xy = (np.asarray(coordenadas) - [dx, dy]) @ np.array([[c, -s], [s, c]])
    uv = xy / [ancho, alto] + 0.5
    if voltear_h:
        uv[:, 0] = 1 - uv[:, 0]
    if voltear_v:
        uv[:, 1] = 1 - uv[:, 1]
    return uv


_motor.registrar(globals(), _iniciar_opencascade)

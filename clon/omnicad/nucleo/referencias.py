# -*- coding: utf-8 -*-
"""
Referencias estables a caras, aristas y vértices de los cuerpos.

Fusion guarda referencias topológicas persistentes (`entityToken`, informe_analisis.md §5): un
empalme sigue apuntando a "su" arista aunque cambie una cota anterior. OpenCascade no trae
nombres persistentes, así que acá cada subforma se guarda con una FIRMA geométrica (tipo de
superficie o curva, centro, tamaño, normal o eje) y, al recalcular, se busca la subforma del
cuerpo nuevo que mejor coincide. Mientras los cambios sean moderados la referencia sobrevive;
si la geometría cambió demasiado, la operación avisa que la referencia se perdió (como el
"error de referencia" de Fusion).

Formato serializable de una referencia: {"tipo": "cara" | "arista" | "vertice", "cuerpo": id,
"firma": {...}}. Las referencias a planos, ejes, puntos y bocetos las resuelve `operaciones`.
"""
import math

import numpy as np
from OCP.BRep import BRep_Tool
from OCP.BRepAdaptor import BRepAdaptor_Curve, BRepAdaptor_Surface
from OCP.BRepGProp import BRepGProp
from OCP.GeomAbs import (GeomAbs_BSplineCurve, GeomAbs_BSplineSurface, GeomAbs_Circle, GeomAbs_Cone,
                         GeomAbs_Cylinder, GeomAbs_Ellipse, GeomAbs_Line, GeomAbs_Plane, GeomAbs_Sphere,
                         GeomAbs_Torus)
from OCP.GProp import GProp_GProps
from OCP.OCP.collections import IndexedMap_TopoDS_Shape_TopTools_ShapeMapHasher
from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE, TopAbs_REVERSED, TopAbs_VERTEX
from OCP.TopExp import TopExp
from OCP.TopoDS import TopoDS

_SUPERFICIES = {GeomAbs_Plane: "plano", GeomAbs_Cylinder: "cilindro", GeomAbs_Cone: "cono",
                GeomAbs_Sphere: "esfera", GeomAbs_Torus: "toro", GeomAbs_BSplineSurface: "bspline"}
_CURVAS = {GeomAbs_Line: "linea", GeomAbs_Circle: "circulo", GeomAbs_Ellipse: "elipse",
           GeomAbs_BSplineCurve: "bspline"}
_TIPOS_TOPO = {"cara": TopAbs_FACE, "arista": TopAbs_EDGE, "vertice": TopAbs_VERTEX}


def _xyz(p):
    return [float(p.X()), float(p.Y()), float(p.Z())]


def subformas(forma, tipo):
    """Caras, aristas o vértices ÚNICOS de la forma, en orden estable."""
    mapa = IndexedMap_TopoDS_Shape_TopTools_ShapeMapHasher()
    TopExp.MapShapes_s(forma, _TIPOS_TOPO[tipo], mapa)
    conv = {"cara": TopoDS.Face, "arista": TopoDS.Edge, "vertice": TopoDS.Vertex}[tipo]
    return [conv(mapa.FindKey(i)) for i in range(1, mapa.Size() + 1)]


def tipo_topologico(sub):
    t = sub.ShapeType()
    return {TopAbs_FACE: "cara", TopAbs_EDGE: "arista", TopAbs_VERTEX: "vertice"}.get(t)


# ---------------------------------------------------------------- firmas
def firma_cara(cara):
    sup = BRepAdaptor_Surface(cara)
    tipo = _SUPERFICIES.get(sup.GetType(), "otra")
    p = GProp_GProps()
    BRepGProp.SurfaceProperties_s(cara, p)
    f = {"geom": tipo, "centro": _xyz(p.CentreOfMass()), "area": float(p.Mass())}
    if tipo == "plano":
        d = sup.Plane().Axis().Direction()
        n = np.array([d.X(), d.Y(), d.Z()])
        f["normal"] = (-n if cara.Orientation() == TopAbs_REVERSED else n).tolist()
    elif tipo in ("cilindro", "cono"):
        eje = (sup.Cylinder() if tipo == "cilindro" else sup.Cone()).Axis()
        f["eje"] = _xyz(eje.Direction())
        if tipo == "cilindro":
            f["radio"] = float(sup.Cylinder().Radius())
    elif tipo == "esfera":
        f["radio"] = float(sup.Sphere().Radius())
    return f


def firma_arista(arista):
    c = BRepAdaptor_Curve(arista)
    tipo = _CURVAS.get(c.GetType(), "otra")
    t0, t1 = c.FirstParameter(), c.LastParameter()
    p = GProp_GProps()
    BRepGProp.LinearProperties_s(arista, p)
    f = {"geom": tipo, "medio": _xyz(c.Value((t0 + t1) / 2)), "largo": float(p.Mass()),
         "extremos": sorted([_xyz(c.Value(t0)), _xyz(c.Value(t1))])}
    if tipo == "circulo":
        f["radio"] = float(c.Circle().Radius())
        f["centro"] = _xyz(c.Circle().Location())
    return f


def firma_vertice(vertice):
    return {"geom": "punto", "punto": _xyz(BRep_Tool.Pnt_s(vertice))}


_PUNTO_REPRESENTATIVO = {"cara": "centro", "arista": "medio", "vertice": "punto"}


def firma(sub, caja=None):
    """Firma geométrica. Con `caja` (caja envolvente del cuerpo) agrega "rel": la posición del punto
    representativo relativa a esa caja (0..1 por eje). Es lo que más ayuda cuando una cota cambia el
    tamaño del cuerpo: la arista "de arriba adelante" sigue arriba adelante aunque se mueva."""
    tipo = tipo_topologico(sub)
    f = {"cara": firma_cara, "arista": firma_arista, "vertice": firma_vertice}[tipo](sub)
    if caja is not None:
        p = np.asarray(f[_PUNTO_REPRESENTATIVO[tipo]], float)
        mn, mx = np.asarray(caja[0], float), np.asarray(caja[1], float)
        tam = mx - mn
        f["rel"] = [float((p[i] - mn[i]) / tam[i]) if tam[i] > 1e-9 else 0.5 for i in range(3)]
    return f


def referencia(cuerpo_id, sub, forma=None, caja=None):
    """Referencia serializable a una subforma de un cuerpo (con `forma` o su `caja`, la firma lleva la
    posición relativa a la caja envolvente)."""
    from .geometria import caja_envolvente
    if caja is None and forma is not None:
        caja = caja_envolvente(forma)
    return {"tipo": tipo_topologico(sub), "cuerpo": cuerpo_id, "firma": firma(sub, caja)}


# ---------------------------------------------------------------- búsqueda
def _distancia(tipo, f, g, escala):
    """Qué tan distintas son dos firmas (0 = iguales). `escala` normaliza por el tamaño del cuerpo."""
    if f["geom"] != g["geom"]:
        return math.inf
    if "rel" in f and "rel" in g:
        # Con posición relativa a la caja, la distancia absoluta pesa poco: así sobrevive a cambios de tamaño.
        rel = math.dist(f["rel"], g["rel"])
        escala = escala * 4
    else:
        rel = 0.0
    if tipo == "vertice":
        return rel + math.dist(f["punto"], g["punto"]) / escala
        return math.dist(f["punto"], g["punto"]) / escala
    if tipo == "arista":
        d = rel + math.dist(f["medio"], g["medio"]) / escala
        d += abs(f["largo"] - g["largo"]) / max(f["largo"], g["largo"], 1e-9) * (0.15 if rel or "rel" in f else 0.5)
        d += min(math.dist(f["extremos"][0], g["extremos"][0]) + math.dist(f["extremos"][1], g["extremos"][1]),
                 math.dist(f["extremos"][0], g["extremos"][1]) + math.dist(f["extremos"][1], g["extremos"][0])
                 ) / escala * 0.5
        if "radio" in f and "radio" in g:
            d += abs(f["radio"] - g["radio"]) / max(f["radio"], g["radio"], 1e-9) * 0.5
        return d
    d = rel + math.dist(f["centro"], g["centro"]) / escala
    d += abs(f["area"] - g["area"]) / max(f["area"], g["area"], 1e-9) * (0.15 if "rel" in f else 0.5)
    if "normal" in f and "normal" in g:
        coseno = float(np.dot(f["normal"], g["normal"]))
        if coseno < 0.5:            # una cara plana no se da vuelta: otra orientación es otra cara
            return math.inf
        d += (1 - coseno) * 2
    if "eje" in f and "eje" in g:
        d += (1 - abs(float(np.dot(f["eje"], g["eje"])))) * 2
    if "radio" in f and "radio" in g:
        d += abs(f["radio"] - g["radio"]) / max(f["radio"], g["radio"], 1e-9) * 0.5
    return d


def resolver(forma, ref, umbral=0.35):
    """Subforma de `forma` que corresponde a la referencia, o None si ninguna se parece lo bastante.
    Se acepta la mejor candidata si está dentro del umbral, o si (hasta un umbral más amplio) le saca
    una ventaja clara a la segunda: así una referencia sobrevive a cambios grandes de cotas sin
    confundirse cuando hay dos candidatas parecidas."""
    from .geometria import caja_envolvente
    tipo = ref["tipo"]
    caja = caja_envolvente(forma)
    escala = max(math.dist(caja[0], caja[1]), 1e-6) if caja else 1.0
    con_rel = "rel" in ref["firma"]
    distancias = sorted(((_distancia(tipo, ref["firma"], firma(sub, caja if con_rel else None), escala), i, sub)
                         for i, sub in enumerate(subformas(forma, tipo))), key=lambda x: (x[0], x[1]))
    if not distancias or distancias[0][0] == math.inf:
        return None
    mejor_d, _, mejor = distancias[0]
    segunda = distancias[1][0] if len(distancias) > 1 else math.inf
    if mejor_d <= umbral or (mejor_d <= 1.2 and mejor_d < 0.5 * segunda):
        return mejor
    return None


def resolver_varias(forma, refs, umbral=0.35):
    """Resuelve varias referencias del mismo cuerpo sin repetir subformas. Devuelve (subformas, perdidas)."""
    salida, perdidas = [], 0
    for ref in refs:
        sub = resolver(forma, ref, umbral)
        if sub is None or any(sub.IsSame(u) for u in salida):
            perdidas += 1
            continue
        salida.append(sub)
    return salida, perdidas


def punto_de_vertice(v):
    return np.array(_xyz(BRep_Tool.Pnt_s(v)))

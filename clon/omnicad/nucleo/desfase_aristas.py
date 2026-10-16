# -*- coding: utf-8 -*-
"""
Desfase de aristas y de curvas de boceto (PL7: «Offset Edge» y «Offset Face Loop» de Plasticity).

Crea curvas NUEVAS a una distancia de las elegidas, sobre un plano, sin tocar el cuerpo ni cortarlo. Las aristas se
unen en cadenas por sus extremos (un lazo de cara es una cadena cerrada) y cada cadena se desfasa con
`BRepOffsetAPI_MakeOffset` sobre el plano. Pura: recibe formas OCC y un `geo.Plano`, devuelve alambres.
"""
import numpy as np
from OCP.BRep import BRep_Tool
from OCP.BRepAdaptor import BRepAdaptor_Curve
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakeVertex
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
from OCP.BRepOffsetAPI import BRepOffsetAPI_MakeOffset
from OCP.BRepTools import BRepTools_WireExplorer
from OCP.GeomAbs import GeomAbs_Arc, GeomAbs_Intersection
from OCP.gp import gp_Dir, gp_Pln, gp_Pnt, gp_Vec
from OCP.TopAbs import TopAbs_REVERSED, TopAbs_WIRE
from OCP.TopoDS import TopoDS

from . import geometria as geo
from . import referencias as refs
from .solidos_crear import _cadenas as cadenas
from .vectores import ESQUINAS

TOL_PLANO = 1e-3          # mm: cuánto pueden apartarse las aristas de un plano paralelo al elegido


def desfasar_aristas(aristas, plano, distancia, simetrico=False, esquinas="redondas"):
    """Desfase de aristas sobre `plano`: lista de alambres nuevos.

    distancia > 0: una cadena abierta se desfasa a la derecha de su recorrido (el de la primera arista, mirando de
    frente al plano con la normal hacia vos) y una cerrada crece hacia afuera; < 0 va al lado contrario.
    simetrico=True hace los dos lados a la vez (la distancia se toma en valor absoluto). esquinas: "redondas" (arcos)
    o "vivas" (se prolongan hasta cortarse). Levanta ErrorGeometria si la distancia es cero, las aristas no son
    paralelas al plano o el desfase desaparece."""
    if esquinas not in ESQUINAS:
        raise geo.ErrorGeometria(f"Esquinas desconocidas: {esquinas} (redondas o vivas).")
    if abs(distancia) < 1e-9:
        raise geo.ErrorGeometria("La distancia del desfase no puede ser cero.")
    normal = np.asarray(plano.normal, float)
    alturas = [float(np.dot(p, normal)) for a in aristas for p in _muestras(a, 9)]
    if alturas and max(alturas) - min(alturas) > TOL_PLANO:
        raise geo.ErrorGeometria("Las aristas no son paralelas al plano elegido: elegí la cara o el plano donde "
                                 "están.")
    union = GeomAbs_Arc if esquinas == "redondas" else GeomAbs_Intersection
    lados = (abs(distancia), -abs(distancia)) if simetrico else (float(distancia),)
    salida = []
    for cadena in cadenas(list(aristas)):
        for d in lados:
            salida.append(_desfasar_cadena(cadena, plano, d, union))
    return salida


def _desfasar_cadena(cadena, plano, d, union):
    if BRep_Tool.IsClosed_s(cadena):
        original = _area(cadena, plano)
        forma = _offset(cadena, d, union, False)
        if (_area(forma, plano) > original) != (d > 0):     # OpenCascade ya lo sacó para el lado contrario
            forma = _offset(cadena, -d, union, False)
        return forma
    t = _tangente_recta(cadena)
    if t is not None:                                       # una recta no define plano: se traslada y listo
        n = np.cross(t, np.asarray(plano.normal, float))
        m = np.identity(4)
        m[:3, 3] = n / np.linalg.norm(n) * d
        return geo.transformar(cadena, m)
    forma = _offset(cadena, d, union, True)
    if not _del_lado(forma, cadena, plano, d):              # OpenCascade elige el lado con SU plano, no con el nuestro
        forma = _offset(cadena, -d, union, True)
    return forma


def _del_lado(forma, cadena, plano, d):
    """¿El desfase `forma` quedó del lado pedido? Lado de `d` > 0 = a la derecha del recorrido de la cadena (su
    primera arista, en el sentido del alambre) mirando con la normal del plano hacia vos."""
    ex = BRepTools_WireExplorer(cadena)
    arista = ex.Current()
    curva = BRepAdaptor_Curve(arista)
    p, v = gp_Pnt(), gp_Vec()
    curva.D1((curva.FirstParameter() + curva.LastParameter()) / 2, p, v)
    tangente = np.array([v.X(), v.Y(), v.Z()]) * (-1.0 if arista.Orientation() == TopAbs_REVERSED else 1.0)
    derecha = np.cross(tangente, np.asarray(plano.normal, float))
    derecha /= np.linalg.norm(derecha)
    medio = np.array([p.X(), p.Y(), p.Z()])

    def distancia(punto):
        vertice = BRepBuilderAPI_MakeVertex(gp_Pnt(*map(float, punto))).Vertex()
        return BRepExtrema_DistShapeShape(vertice, forma).Value()

    pedido = medio + derecha * np.sign(d) * abs(d)
    return distancia(pedido) <= distancia(medio - derecha * np.sign(d) * abs(d))


def _offset(cadena, d, union, abierta):
    mk = BRepOffsetAPI_MakeOffset(cadena, union, abierta)
    mk.Perform(float(d))
    if not mk.IsDone() or mk.Shape().IsNull() or not refs.subformas(mk.Shape(), "arista"):
        raise geo.ErrorGeometria(f"El desfase de {d:g} mm no se pudo calcular: ¿las aristas están en el plano elegido, "
                                 "o el desfase hace desaparecer la curva?")
    return mk.Shape()


def _area(forma, plano):
    """Área que encierra el primer lazo de `forma` sobre el plano."""
    lazo = TopoDS.Wire(next(iter(geo._explorar(forma, TopAbs_WIRE))))
    cara = BRepBuilderAPI_MakeFace(gp_Pln(plano.ax2().Location(), gp_Dir(*map(float, plano.normal))), lazo).Face()
    return geo.area(cara)


def _tangente_recta(cadena):
    """Dirección unitaria de la cadena si todas sus aristas son rectas sobre una misma línea; si no, None."""
    firmas = [refs.firma_arista(a) for a in refs.subformas(cadena, "arista")]
    if any(f["geom"] != "linea" for f in firmas):
        return None
    a, b = (np.array(p) for p in firmas[0]["extremos"])         # el sentido lo da la primera arista
    t = b - a
    largo = np.linalg.norm(t)
    if largo < 1e-9:
        return None
    t = t / largo
    puntos = [np.array(p) for f in firmas for p in f["extremos"]]
    return t if all(np.linalg.norm(np.cross(p - a, t)) < 1e-6 for p in puntos) else None


def plano_de_aristas(aristas, tolerancia=1e-3):
    """El plano donde están TODAS las aristas (un `geo.Plano`), ajustado por mínimos cuadrados a puntos de cada una.
    La normal se orienta hacia arriba (la componente mayor, positiva), así «a la derecha» no cambia entre corridas.
    Levanta ErrorGeometria si están en línea recta (hay infinitos planos: hay que elegir uno) o no son coplanares."""
    puntos = np.array([_muestras(a, 9) for a in aristas]).reshape(-1, 3)
    centro = puntos.mean(axis=0)
    _, valores, vt = np.linalg.svd(puntos - centro)
    if valores[1] < 1e-6 * max(valores[0], 1.0):
        raise geo.ErrorGeometria("Las aristas están en línea recta: no definen un plano. Elegí también la cara o el "
                                 "plano donde se hace el desfase.")
    normal = vt[2]
    if valores[2] / np.sqrt(len(puntos)) > tolerancia:
        raise geo.ErrorGeometria("Las aristas no están en un mismo plano. Elegí también la cara o el plano donde se "
                                 "hace el desfase.")
    if normal[np.argmax(np.abs(normal))] < 0:
        normal = -normal
    return geo.Plano.desde_marco(centro, normal, vt[0])


def _muestras(arista, n):
    """`n` puntos repartidos a lo largo de la arista (en el orden de su parámetro)."""
    curva = BRepAdaptor_Curve(arista)
    a, b = curva.FirstParameter(), curva.LastParameter()
    return [[p.X(), p.Y(), p.Z()] for p in (curva.Value(a + (b - a) * k / (n - 1)) for k in range(n))]

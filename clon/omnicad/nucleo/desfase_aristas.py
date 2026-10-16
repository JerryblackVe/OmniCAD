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
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakeWire
from OCP.BRepOffsetAPI import BRepOffsetAPI_MakeOffset
from OCP.GeomAbs import GeomAbs_Arc, GeomAbs_Intersection
from OCP.gp import gp_Dir, gp_Pln
from OCP.TopAbs import TopAbs_WIRE
from OCP.TopExp import TopExp_Explorer
from OCP.TopoDS import TopoDS

from . import geometria as geo
from . import referencias as refs

ESQUINAS = ("redondas", "vivas")


def cadenas(aristas):
    """Une aristas en cadenas por sus extremos: lista de alambres (un lazo cerrado es una sola cadena)."""
    pendientes, salida = list(aristas), []
    while pendientes:
        mk = BRepBuilderAPI_MakeWire()
        mk.Add(pendientes.pop(0))
        avanzo = True
        while avanzo and pendientes:
            avanzo = False
            for a in list(pendientes):
                mk.Add(a)                                   # no se une: queda para otra cadena
                if mk.IsDone():
                    pendientes.remove(a)
                    avanzo = True
        salida.append(mk.Wire())
    return salida


def desfasar_aristas(aristas, plano, distancia, simetrico=False, esquinas="redondas"):
    """Desfase de aristas sobre `plano`: lista de alambres nuevos.

    distancia > 0: una cadena abierta se desfasa a la derecha de su recorrido (el de la primera arista, mirando de
    frente al plano con la normal hacia vos) y una cerrada crece hacia afuera; < 0 va al lado contrario.
    simetrico=True hace los dos lados a la vez (la distancia se toma en valor absoluto). esquinas: "redondas" (arcos)
    o "vivas" (se prolongan hasta cortarse). Levanta ErrorGeometria si la distancia es cero, las aristas no están en el
    plano o el desfase desaparece."""
    if esquinas not in ESQUINAS:
        raise geo.ErrorGeometria(f"Esquinas desconocidas: {esquinas} (redondas o vivas).")
    if abs(distancia) < 1e-9:
        raise geo.ErrorGeometria("La distancia del desfase no puede ser cero.")
    union = GeomAbs_Arc if esquinas == "redondas" else GeomAbs_Intersection
    lados = (abs(distancia), -abs(distancia)) if simetrico else (float(distancia),)
    salida = []
    for cadena in cadenas(aristas):
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
    return _offset(cadena, d, union, True)


def _offset(cadena, d, union, abierta):
    mk = BRepOffsetAPI_MakeOffset(cadena, union, abierta)
    mk.Perform(float(d))
    if not mk.IsDone() or mk.Shape().IsNull():
        raise geo.ErrorGeometria(f"El desfase de {d:g} mm no se pudo calcular: ¿las aristas están en el plano elegido, "
                                 "o el desfase hace desaparecer la curva?")
    return mk.Shape()


def _area(forma, plano):
    """Área que encierra el primer lazo de `forma` sobre el plano."""
    lazo = TopoDS.Wire(next(iter(_explorar(forma, TopAbs_WIRE))))
    cara = BRepBuilderAPI_MakeFace(gp_Pln(plano.ax2().Location(), gp_Dir(*map(float, plano.normal))), lazo).Face()
    return geo.area(cara)


def _explorar(forma, tipo):
    ex = TopExp_Explorer(forma, tipo)
    while ex.More():
        yield ex.Current()
        ex.Next()


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

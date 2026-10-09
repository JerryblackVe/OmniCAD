# -*- coding: utf-8 -*-
"""
Comandos SÓLIDO › CREAR de Fusion 360 en el núcleo: extrusión y revolución completas, barrido,
solevado, nervio, red, repujado, agujero, rosca, bobina, tubería, patrones y simetría, engrosar,
relleno de contorno y sólido envolvente; más saliente y labio de la pestaña PLÁSTICO (simplificados).

Funciones puras: reciben formas OCC, arrays o números y devuelven formas OCC (los patrones devuelven
listas de gp_Trsf). La booleana contra los cuerpos del documento la hace la capa de operaciones, salvo
donde el comando de Fusion entrega el cuerpo ya modificado (repujado, rosca, saliente, labio).
Unidades: mm y grados. Ayuda de cada comando: analisis/fusion_doc/paginas/<ID>.txt.
"""
import math
import re

import numpy as np
from OCP.BOPAlgo import BOPAlgo_MakerVolume
from OCP.BRep import BRep_Tool
from OCP.BRepAdaptor import BRepAdaptor_CompCurve, BRepAdaptor_Curve, BRepAdaptor_Surface
from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut, BRepAlgoAPI_Splitter
from OCP.BRepBuilderAPI import (BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakePolygon,
                                BRepBuilderAPI_MakeVertex, BRepBuilderAPI_MakeWire, BRepBuilderAPI_RightCorner,
                                BRepBuilderAPI_Sewing, BRepBuilderAPI_Transform)
from OCP.BRepClass import BRepClass_FaceClassifier
from OCP.BRepClass3d import BRepClass3d_SolidClassifier
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
from OCP.BRepFill import BRepFill_ContactOnBorder, BRepFill_NoContact
from OCP.BRepGProp import BRepGProp
from OCP.BRepLib import BRepLib
from OCP.BRepOffset import BRepOffset_MakeOffset, BRepOffset_Skin
from OCP.BRepOffsetAPI import (BRepOffsetAPI_DraftAngle, BRepOffsetAPI_MakeOffset, BRepOffsetAPI_MakeOffsetShape,
                               BRepOffsetAPI_MakePipeShell,
                               BRepOffsetAPI_ThruSections)
from OCP.BRepPrimAPI import BRepPrimAPI_MakeHalfSpace, BRepPrimAPI_MakePrism, BRepPrimAPI_MakeRevol
from OCP.BRepTools import BRepTools, BRepTools_WireExplorer
from OCP.GCPnts import GCPnts_AbscissaPoint
from OCP.Geom import Geom_ConicalSurface, Geom_CylindricalSurface
from OCP.Geom2d import Geom2d_Line, Geom2d_TrimmedCurve
from OCP.Geom2dAPI import Geom2dAPI_Interpolate
from OCP.GeomAbs import GeomAbs_Cylinder, GeomAbs_Intersection, GeomAbs_Line, GeomAbs_Plane
from OCP.GeomAPI import GeomAPI_Interpolate
from OCP.GProp import GProp_GProps
from OCP.IntCurvesFace import IntCurvesFace_ShapeIntersector
from OCP.Law import Law_Interpol, Law_Linear
from OCP.OCP.collections import Array1_gp_Pnt2d, HArray1_gp_Pnt, HArray1_gp_Pnt2d, List_TopoDS_Shape
from OCP.ShapeFix import ShapeFix_Face
from OCP.ShapeUpgrade import ShapeUpgrade_UnifySameDomain
from OCP.TopAbs import (TopAbs_EDGE, TopAbs_FACE, TopAbs_IN, TopAbs_REVERSED, TopAbs_SHELL, TopAbs_SOLID,
                        TopAbs_VERTEX, TopAbs_WIRE)
from OCP.TopExp import TopExp, TopExp_Explorer
from OCP.TopoDS import TopoDS
from OCP.gp import gp_Ax1, gp_Ax2, gp_Ax3, gp_Circ, gp_Dir, gp_Dir2d, gp_Lin, gp_Pln, gp_Pnt, gp_Pnt2d, gp_Trsf, gp_Vec

from . import geometria as geo

_MARGEN = 1.0   # mm que las herramientas "hasta" y "todo" pasan de largo antes de recortarse


# ================================================================ utilidades
def _unit(v, que="dirección"):
    v = np.asarray(v, float)
    n = np.linalg.norm(v)
    if n < 1e-12:
        raise geo.ErrorGeometria(f"La {que} no puede ser nula.")
    return v / n


def _pnt(p):
    return gp_Pnt(*map(float, p))


def _gdir(d):
    return gp_Dir(*map(float, d))


def _gvec(v):
    return gp_Vec(*map(float, v))


def _xyz(p):
    return np.array([p.X(), p.Y(), p.Z()], float)


def _perpendicular(n):
    n = _unit(n)
    aux = (0.0, 0.0, 1.0) if abs(n[2]) < 0.9 else (1.0, 0.0, 0.0)
    return _unit(np.cross(n, aux))


_CONVERTIR = {TopAbs_FACE: TopoDS.Face, TopAbs_WIRE: TopoDS.Wire, TopAbs_EDGE: TopoDS.Edge,
              TopAbs_SOLID: TopoDS.Solid, TopAbs_SHELL: TopoDS.Shell, TopAbs_VERTEX: TopoDS.Vertex}


def _tipado(forma):
    """Las transformaciones devuelven TopoDS_Shape genérico: se baja al tipo concreto (cara, alambre…)."""
    f = _CONVERTIR.get(forma.ShapeType())
    return f(forma) if f else forma


def _trasladar(forma, vector):
    return _tipado(geo.trasladar(forma, vector))


def _lista(x):
    if x is None:
        return []
    return [y for y in x if y is not None] if isinstance(x, (list, tuple)) else [x]


def _explorar(forma, tipo):
    ex = TopExp_Explorer(forma, tipo)
    while ex.More():
        yield ex.Current()
        ex.Next()


def _caras_de(x):
    """Caras de una cara, una forma o una lista de ellas."""
    salida = []
    for f in _lista(x):
        salida += [TopoDS.Face(c) for c in _explorar(f, TopAbs_FACE)]
    return salida


def _aristas_de(x):
    salida = []
    for f in _lista(x):
        if f.ShapeType() == TopAbs_WIRE:
            ex = BRepTools_WireExplorer(TopoDS.Wire(f))
            while ex.More():
                salida.append(ex.Current())
                ex.Next()
        else:
            salida += [TopoDS.Edge(e) for e in _explorar(f, TopAbs_EDGE)]
    return salida


def _extremos(arista):
    a = BRep_Tool.Pnt_s(TopExp.FirstVertex_s(arista, True))
    b = BRep_Tool.Pnt_s(TopExp.LastVertex_s(arista, True))
    return _xyz(a), _xyz(b)


def _cadenas(x, tol=1e-5):
    """Agrupa aristas sueltas (o alambres) en alambres encadenados. Devuelve una lista de alambres."""
    alambres = [TopoDS.Wire(f) for f in _lista(x) if f.ShapeType() == TopAbs_WIRE]
    pendientes = _aristas_de([f for f in _lista(x) if f.ShapeType() != TopAbs_WIRE])
    while pendientes:
        cadena = [pendientes.pop(0)]
        ini, fin = _extremos(cadena[0])
        agrego = True
        while agrego and pendientes:
            agrego = False
            for i, e in enumerate(pendientes):
                a, b = _extremos(e)
                if np.linalg.norm(a - fin) < tol or np.linalg.norm(b - fin) < tol:
                    cadena.append(e)
                    fin = b if np.linalg.norm(a - fin) < tol else a
                elif np.linalg.norm(a - ini) < tol or np.linalg.norm(b - ini) < tol:
                    cadena.insert(0, e)
                    ini = b if np.linalg.norm(a - ini) < tol else a
                else:
                    continue
                pendientes.pop(i)
                agrego = True
                break
        mk = BRepBuilderAPI_MakeWire()
        for e in cadena:
            mk.Add(e)
        if not mk.IsDone():
            raise geo.ErrorGeometria("No se pudo encadenar las aristas en un alambre.")
        alambres.append(mk.Wire())
    return alambres


def _alambre(x):
    """Un único alambre continuo a partir de aristas, un alambre o una lista de aristas."""
    alambres = _cadenas(x)
    if len(alambres) != 1:
        raise geo.ErrorGeometria("La ruta debe ser una sola cadena continua de aristas.")
    return alambres[0]


def _longitud(forma):
    p = GProp_GProps()
    BRepGProp.LinearProperties_s(forma, p)
    return p.Mass()


def _es_cerrado(alambre):
    a = BRep_Tool.Pnt_s(TopExp.FirstVertex_s(_aristas_de(alambre)[0], True))
    b = BRep_Tool.Pnt_s(TopExp.LastVertex_s(_aristas_de(alambre)[-1], True))
    return a.Distance(b) < 1e-6


def _punto_en(alambre, fraccion):
    """(punto, tangente unitaria) a una fracción 0..1 de la longitud del alambre."""
    c = BRepAdaptor_CompCurve(alambre)
    largo = GCPnts_AbscissaPoint.Length_s(c)
    fraccion = min(max(fraccion, 0.0), 1.0)
    if fraccion <= 0:
        u = c.FirstParameter()
    elif fraccion >= 1:
        u = c.LastParameter()
    else:
        u = GCPnts_AbscissaPoint(c, fraccion * largo, c.FirstParameter()).Parameter()
    p, v = gp_Pnt(), gp_Vec()
    c.D1(u, p, v)
    return _xyz(p), _unit(_xyz(v), "tangente de la ruta")


def _recortar_alambre(alambre, fraccion):
    """Primer tramo del alambre hasta una fracción de su longitud (opción Distancia de barrido y tubería)."""
    if fraccion >= 1.0 - 1e-9:
        return alambre
    if fraccion <= 1e-6:
        raise geo.ErrorGeometria("La distancia sobre la ruta debe ser mayor que cero.")
    objetivo, acumulado = fraccion * _longitud(alambre), 0.0
    mk = BRepBuilderAPI_MakeWire()
    for e in _aristas_de(alambre):
        largo = _longitud(e)
        if acumulado + largo < objetivo - 1e-9:
            mk.Add(e)
            acumulado += largo
            continue
        curva = BRepAdaptor_Curve(e)
        geom = BRep_Tool.Curve_s(e, 0.0, 0.0)
        resto = objetivo - acumulado
        if e.Orientation() == TopAbs_REVERSED:
            u1 = curva.LastParameter()
            u0 = GCPnts_AbscissaPoint(curva, -resto, u1).Parameter()
            nueva = BRepBuilderAPI_MakeEdge(geom, u0, u1).Edge().Reversed()
        else:
            u0 = curva.FirstParameter()
            u1 = GCPnts_AbscissaPoint(curva, resto, u0).Parameter()
            nueva = BRepBuilderAPI_MakeEdge(geom, u0, u1).Edge()
        mk.Add(TopoDS.Edge(nueva))
        break
    return mk.Wire()


def _marcos(alambre, n=64):
    """Muestras (punto, tangente, u, v) a lo largo del alambre con un marco de rotación mínima
    (método de doble reflexión): sirve para torsión de barridos y patrones orientados a la ruta."""
    c = BRepAdaptor_CompCurve(alambre)
    largo = GCPnts_AbscissaPoint.Length_s(c)
    pts, tans = [], []
    for i in range(n):
        s = largo * i / (n - 1)
        u = c.FirstParameter() if i == 0 else (
            c.LastParameter() if i == n - 1 else GCPnts_AbscissaPoint(c, s, c.FirstParameter()).Parameter())
        p, v = gp_Pnt(), gp_Vec()
        c.D1(u, p, v)
        pts.append(_xyz(p))
        tans.append(_unit(_xyz(v), "tangente de la ruta"))
    r = _perpendicular(tans[0])
    marcos = [(pts[0], tans[0], r, np.cross(tans[0], r))]
    for i in range(n - 1):
        v1 = pts[i + 1] - pts[i]
        c1 = float(v1 @ v1)
        if c1 < 1e-18:
            rl, tl = r, tans[i]
        else:
            rl = r - (2 / c1) * float(v1 @ r) * v1
            tl = tans[i] - (2 / c1) * float(v1 @ tans[i]) * v1
        v2 = tans[i + 1] - tl
        c2 = float(v2 @ v2)
        r = rl - (2 / c2) * float(v2 @ rl) * v2 if c2 > 1e-18 else rl
        r = _unit(r - tans[i + 1] * float(r @ tans[i + 1]))
        marcos.append((pts[i + 1], tans[i + 1], r, np.cross(tans[i + 1], r)))
    return marcos


def _unificar(forma):
    """Fusiona caras coplanares/cosuperficiales que dejan las uniones (como el resultado limpio de Fusion)."""
    try:
        u = ShapeUpgrade_UnifySameDomain(forma, True, True, False)
        u.Build()
        return u.Shape()
    except Exception:  # noqa: BLE001 — si no se puede simplificar, se devuelve tal cual
        return forma


def _unir(formas):
    formas = [f for f in formas if f is not None and not geo.esta_vacia(f)]
    if not formas:
        raise geo.ErrorGeometria("La operación no produjo geometría.")
    return _unificar(geo.unir_todos(formas)) if len(formas) > 1 else formas[0]


def _validar(forma, que):
    if forma is None or geo.esta_vacia(forma):
        raise geo.ErrorGeometria(f"{que}: el resultado quedó vacío.")
    if not geo.es_valida(forma):
        raise geo.ErrorGeometria(f"{que}: el kernel produjo un sólido inválido con estos valores.")
    return forma


def _piezas_que_tocan(forma, inicios, tol=1e-5):
    return [s for s in geo.solidos(forma) if any(geo.se_tocan(s, i, tol) for i in inicios)]


def _normal_superficie(cara):
    """Normal geométrica de una cara plana (sin tener en cuenta la orientación de la cara)."""
    sup = BRepAdaptor_Surface(cara)
    if sup.GetType() != GeomAbs_Plane:
        raise geo.ErrorGeometria("El perfil debe ser una cara plana.")
    d = sup.Plane().Axis().Direction()
    return np.array([d.X(), d.Y(), d.Z()])


def _caja_proyectada(forma, origen, direccion):
    """(mín, máx) de la proyección de la caja envolvente de `forma` sobre una recta."""
    bb = geo.caja_envolvente(forma)
    if bb is None:
        raise geo.ErrorGeometria("El objeto no tiene geometría.")
    return _proyectar_caja(bb, origen, direccion)


def _proyectar_caja(bb, origen, direccion):
    esquinas = np.array([[x, y, z] for x in (bb[0][0], bb[1][0]) for y in (bb[0][1], bb[1][1])
                         for z in (bb[0][2], bb[1][2])])
    proy = (esquinas - np.asarray(origen, float)) @ np.asarray(direccion, float)
    return float(proy.min()), float(proy.max())


def _rayo(forma, punto, direccion, largo=1e5):
    """Distancias a lo largo de un rayo a las que corta la forma (ordenadas)."""
    inter = IntCurvesFace_ShapeIntersector()
    inter.Load(forma, 1e-7)
    inter.Perform(gp_Lin(_pnt(punto), _gdir(direccion)), 0.0, largo)
    if not inter.IsDone():
        return []
    return sorted(inter.WParameter(i) for i in range(1, inter.NbPnt() + 1))


def _engrosar_lamina(lamina, espesor):
    """Sólido de dar espesor a una lámina (cara o cáscara) hacia su normal (negativo = hacia atrás)."""
    mk = BRepOffset_MakeOffset()
    mk.Initialize(lamina, float(espesor), 1e-6, BRepOffset_Skin, False, False, GeomAbs_Intersection, True)
    mk.MakeOffsetShape()
    if not mk.IsDone():
        raise geo.ErrorGeometria("No se pudo dar espesor a la superficie.")
    return mk.Shape()


def _poligono(puntos):
    mk = BRepBuilderAPI_MakePolygon()
    for p in puntos:
        mk.Add(_pnt(p))
    mk.Close()
    return mk.Wire()


def _cara(alambre):
    mk = BRepBuilderAPI_MakeFace(alambre, True)
    if not mk.IsDone():
        raise geo.ErrorGeometria("El contorno no es plano o no está cerrado.")
    return mk.Face()


def cara_de_plano(plano, tamano=1e3):
    """Cara cuadrada grande sobre un geo.Plano: así se pasan los planos de construcción como herramientas."""
    pln = gp_Pln(gp_Ax3(_pnt(plano.origen), _gdir(plano.normal), _gdir(plano.u)))
    return BRepBuilderAPI_MakeFace(pln, -tamano, tamano, -tamano, tamano).Face()


# ================================================================ 1. extrusión
def _prisma(cara, n, d, conicidad=0.0):
    """Extrusión de una cara plana una distancia `d` (con signo) según `n`, con ángulo de inclinación en
    grados (positivo = se ensancha, como en Fusion)."""
    if abs(d) < 1e-9:
        raise geo.ErrorGeometria("La distancia de extrusión no puede ser cero.")
    if abs(conicidad) < 1e-9:
        return BRepPrimAPI_MakePrism(cara, _gvec(np.asarray(n, float) * d)).Shape()
    if abs(conicidad) >= 89.0:
        raise geo.ErrorGeometria("El ángulo de inclinación debe estar entre -89° y 89°.")
    n = np.asarray(n, float)
    if abs(float(_normal_superficie(cara) @ n)) < 1 - 1e-6:
        raise geo.ErrorGeometria("Con inclinación, la extrusión debe ser perpendicular al perfil.")
    # Prisma recto + desmoldeo de las caras laterales con el plano del perfil como plano neutro: las
    # esquinas quedan vivas (tronco de pirámide), como en Fusion. LocOpe_DPrism las redondea al ensanchar.
    tirar = n * math.copysign(1.0, d)
    prisma = BRepPrimAPI_MakePrism(cara, _gvec(n * d)).Shape()
    centro = np.array(geo.centro_masa(cara, superficie=True))
    neutro = gp_Pln(_pnt(centro), _gdir(tirar))
    da = BRepOffsetAPI_DraftAngle(prisma)
    for f in geo.caras(prisma):
        pl = geo.plano_de_cara(f)
        if pl is not None and abs(abs(float(pl.normal @ tirar)) - 1) < 1e-9:
            continue   # tapas
        da.Add(f, _gdir(tirar), math.radians(-conicidad), neutro, True)
        if not da.AddDone():
            raise geo.ErrorGeometria("No se pudo inclinar una cara lateral de la extrusión.")
    da.Build()
    if not da.IsDone():
        raise geo.ErrorGeometria("El kernel no pudo aplicar la inclinación a la extrusión.")
    return _validar(da.Shape(), "Extrusión con inclinación")


def _desfase_alambre(alambre, d):
    """Desfase 2D de un alambre cerrado y plano (positivo = hacia afuera), con esquinas vivas."""
    mo = BRepOffsetAPI_MakeOffset(alambre, GeomAbs_Intersection, False)
    mo.Perform(float(d))
    if not mo.IsDone():
        raise geo.ErrorGeometria("No se pudo desfasar el contorno (espesor demasiado grande).")
    alambres = [TopoDS.Wire(w) for w in _explorar(mo.Shape(), TopAbs_WIRE)]
    if len(alambres) != 1:
        raise geo.ErrorGeometria("El desfase del contorno se partió en varios lazos: reducí el espesor.")
    return alambres[0]


def _bandas_cerradas(caras, espesor, ubicacion):
    """Caras planas de pared delgada a lo largo de cada lazo de los perfiles (Thin Extrude con perfil
    cerrado). lado1 = hacia afuera de cada lazo, lado2 = hacia adentro, centro = mitad y mitad."""
    if espesor <= 0:
        raise geo.ErrorGeometria("El espesor de pared debe ser positivo.")
    a, b = {"lado1": (0.0, espesor), "lado2": (-espesor, 0.0),
            "centro": (-espesor / 2, espesor / 2)}.get(ubicacion, (None, None))
    if a is None:
        raise geo.ErrorGeometria(f"Ubicación de pared desconocida: {ubicacion}")
    bandas = []
    for cara in caras:
        for w in _explorar(cara, TopAbs_WIRE):
            w = TopoDS.Wire(w)
            exterior = _cara(_desfase_alambre(w, b) if b else w)
            interior = _cara(_desfase_alambre(w, a) if a else w)
            bandas += _caras_de(geo.booleano(exterior, interior, "cortar"))
    return bandas


def _herramienta_extrusion(caras, abiertas, n, base, lados, delgado):
    """Une los prismas de cada lado (lista de (distancia con signo, conicidad))."""
    solidos = []
    for d, conicidad in lados:
        for cara in caras:
            solidos.append(_prisma(_trasladar(cara, n * base), n, d, conicidad))
    if abiertas:
        if any(abs(c) > 1e-9 for _, c in lados):
            raise geo.ErrorGeometria("La inclinación no se admite en la extrusión delgada de un perfil abierto.")
        lo = min([0.0] + [d for d, _ in lados])
        hi = max([0.0] + [d for d, _ in lados])
        t, ubic = float(delgado["espesor"]), delgado.get("ubicacion", "centro")
        for w in abiertas:
            lamina = BRepPrimAPI_MakePrism(_trasladar(w, n * (base + lo)), _gvec(n * (hi - lo))).Shape()
            if ubic == "lado1":
                solidos.append(_engrosar_lamina(lamina, t))
            elif ubic == "lado2":
                solidos.append(_engrosar_lamina(lamina, -t))
            elif ubic == "centro":
                solidos += [_engrosar_lamina(lamina, t / 2), _engrosar_lamina(lamina, -t / 2)]
            else:
                raise geo.ErrorGeometria(f"Ubicación de pared desconocida: {ubic}")
    return _unir(solidos)


def _distancia_a_plano(origen, n, cara_plana):
    pl = geo.plano_de_cara(cara_plana)
    coseno = float(n @ pl.normal)
    if abs(coseno) < 1e-9:
        raise geo.ErrorGeometria("El plano objetivo es paralelo a la dirección de extrusión.")
    return float((pl.origen - origen) @ pl.normal) / coseno


def extruir_avanzado(caras, normal, *, distancia1=None, inicio_desfase=0.0, direccion="un_lado", distancia2=None,
                     conicidad1=0.0, conicidad2=0.0, medida_simetrica="mitad", delgado=None, aristas=None,
                     hasta=None, hasta_modo="cara", hasta_desfase=0.0, hasta_caja=None):
    """Extrusión completa de Fusion [SLD-EXTRUDE-SOLID, SLD-REF-EXTRUDE]. Devuelve el sólido herramienta.

    - Inicio: plano del perfil desplazado `inicio_desfase` según la normal (Start = Offset).
    - Dirección: "un_lado" (distancia1 con signo), "dos_lados" (distancia1 hacia +n y distancia2 hacia -n,
      cada uno con su conicidad) o "simetrica" (`medida_simetrica` "mitad" = distancia1 a cada lado,
      "total" = distancia1 en total).
    - Conicidad: ángulo de inclinación en grados; positivo = se ensancha.
    - Delgada: `delgado={"espesor": t, "ubicacion": "lado1"|"lado2"|"centro"}`; con perfiles cerrados (caras)
      o abiertos (`aristas`, una o varias cadenas en el plano del boceto; lado1 = izquierda de la curva
      mirando desde +n).
    - Extensión "Al objeto" (lado 1): `hasta` = cara (plana o curva) o cuerpo; `hasta_modo` "cara" | "cuerpo"
      (hasta las caras del cuerpo) | "a_traves" (atraviesa el cuerpo); `hasta_desfase` corre el final.
    - Extensión "Todo": `hasta_caja` = caja envolvente ((x0,y0,z0),(x1,y1,z1)) de los cuerpos visibles.
    """
    n = _unit(normal, "normal de extrusión")
    caras = _caras_de(caras)
    abiertas = _cadenas(aristas) if aristas is not None else []
    if not caras and not abiertas:
        raise geo.ErrorGeometria("Elegí al menos un perfil para extruir.")
    if abiertas and not delgado:
        raise geo.ErrorGeometria("Los perfiles abiertos solo se extruyen como extrusión delgada.")
    if delgado and caras:
        caras = _bandas_cerradas(caras, float(delgado["espesor"]), delgado.get("ubicacion", "lado1"))
    if direccion not in ("un_lado", "dos_lados", "simetrica"):
        raise geo.ErrorGeometria(f"Dirección de extrusión desconocida: {direccion}")
    base = float(inicio_desfase)
    inicios = [_trasladar(f, n * base) for f in caras + abiertas]
    origen = np.mean([geo.centro_masa(f, superficie=True) if f.ShapeType() == TopAbs_FACE else
                      np.mean(_extremos(_aristas_de(f)[0]), axis=0) for f in inicios], axis=0)

    if hasta_caja is not None:                       # extensión "Todo"
        lo, hi = _proyectar_caja(hasta_caja, origen, n)
        signo = -1.0 if (distancia1 is not None and distancia1 < 0) else 1.0
        if direccion == "un_lado":
            alcance = (hi if signo > 0 else -lo) + _MARGEN
            if alcance <= _MARGEN:
                raise geo.ErrorGeometria("No hay cuerpos en el sentido de la extrusión.")
            lados = [(signo * alcance, conicidad1)]
        else:
            lados = [(max(hi, 0.0) + _MARGEN, conicidad1), (min(lo, 0.0) - _MARGEN, conicidad2)]
        return _validar(_herramienta_extrusion(caras, abiertas, n, base, lados, delgado), "Extrusión")

    if hasta is not None:                            # extensión "Al objeto" en el lado 1
        es_cara = hasta.ShapeType() == TopAbs_FACE
        plano_obj = geo.plano_de_cara(TopoDS.Face(hasta)) if es_cara else None
        if plano_obj is not None and abs(float(n @ plano_obj.normal)) > 1 - 1e-9:
            d = _distancia_a_plano(origen, n, TopoDS.Face(hasta))
            d += math.copysign(hasta_desfase, d)
            lados1 = [(d, conicidad1)]
            herr = None
        else:
            objeto = _trasladar(hasta, n * hasta_desfase) if hasta_desfase else hasta
            lo, hi = _caja_proyectada(objeto, origen, n)
            signo = -1.0 if (distancia1 is not None and distancia1 < 0) or (hi <= 0 < -lo) else 1.0
            alcance = (hi if signo > 0 else -lo) + _MARGEN
            if alcance <= _MARGEN:
                raise geo.ErrorGeometria("El objeto está del otro lado del perfil.")
            largo = _herramienta_extrusion(caras, abiertas, n, base, [(signo * alcance, conicidad1)], delgado)
            herr = _recortar_hasta(largo, inicios, objeto, hasta_modo, plano_obj, origen)
            lados1 = []
        lados2 = []
        if direccion == "dos_lados" and distancia2:
            lados2 = [(-abs(distancia2), conicidad2)]
        elif direccion == "simetrica":
            raise geo.ErrorGeometria("La extensión 'Al objeto' no se combina con dirección simétrica.")
        partes = [herr] if herr is not None else []
        if lados1 or lados2:
            partes.append(_herramienta_extrusion(caras, abiertas, n, base, lados1 + lados2, delgado))
        return _validar(_unir(partes), "Extrusión")

    if distancia1 is None or abs(distancia1) < 1e-9:
        raise geo.ErrorGeometria("Falta la distancia de extrusión.")
    if direccion == "un_lado":
        lados = [(float(distancia1), conicidad1)]
    elif direccion == "dos_lados":
        if distancia2 is None or abs(distancia2) < 1e-9:
            raise geo.ErrorGeometria("Falta la distancia del lado 2.")
        lados = [(abs(distancia1), conicidad1), (-abs(distancia2), conicidad2)]
    else:
        if medida_simetrica not in ("mitad", "total"):
            raise geo.ErrorGeometria(f"Medida simétrica desconocida: {medida_simetrica}")
        h = abs(distancia1) if medida_simetrica == "mitad" else abs(distancia1) / 2
        lados = [(h, conicidad1), (-h, conicidad1)]
    return _validar(_herramienta_extrusion(caras, abiertas, n, base, lados, delgado), "Extrusión")


def _recortar_hasta(herr, inicios, objeto, modo, plano_obj, origen):
    """Recorta una herramienta larga para que termine en el objeto (cara o cuerpo)."""
    if objeto.ShapeType() == TopAbs_FACE:
        if plano_obj is not None:   # plano oblicuo: semiespacio del lado del perfil
            semi = BRepPrimAPI_MakeHalfSpace(cara_de_plano(plano_obj, 1e5), _pnt(origen)).Solid()
            piezas = _piezas_que_tocan(geo.booleano(herr, semi, "intersecar"), inicios)
        else:                       # cara curva: se parte la herramienta con la cara
            sp = BRepAlgoAPI_Splitter()
            args, herramientas = List_TopoDS_Shape(), List_TopoDS_Shape()
            args.Append(herr)
            herramientas.Append(objeto)
            sp.SetArguments(args)
            sp.SetTools(herramientas)
            sp.Build()
            if not sp.IsDone():
                raise geo.ErrorGeometria("No se pudo cortar la extrusión con la cara objetivo.")
            piezas = _piezas_que_tocan(sp.Shape(), inicios)
            if len(geo.solidos(sp.Shape())) < 2:
                raise geo.ErrorGeometria("La extrusión no llega a la cara objetivo (la cara no la corta entera).")
        return _unir(piezas)
    if modo not in ("cara", "cuerpo", "a_traves"):
        raise geo.ErrorGeometria(f"Modo de extensión desconocido: {modo}")
    piezas = _piezas_que_tocan(geo.booleano(herr, objeto, "cortar"), inicios)
    if modo == "a_traves":
        piezas.append(geo.booleano(herr, objeto, "intersecar"))
    if not piezas:
        raise geo.ErrorGeometria("El perfil queda dentro del cuerpo objetivo.")
    return _unir(piezas)


# ================================================================ 2. revolución
def _girar(forma, eje, grados):
    t = gp_Trsf()
    t.SetRotation(eje, math.radians(grados))
    return _tipado(BRepBuilderAPI_Transform(forma, t, True).Shape())


def revolver_avanzado(caras, punto_eje, dir_eje, *, direccion="un_lado", angulo1=360.0, angulo2=None,
                      delgado=None, aristas=None):
    """Revolución de Fusion [SLD-REVOLVE-SOLID]. Devuelve el sólido herramienta.

    "un_lado": angulo1 con signo; "dos_lados": angulo1 hacia un lado y angulo2 hacia el otro; "simetrica":
    angulo1 a cada lado (total 2·angulo1, como `setAngleExtent(isSymmetric=True)` de la API de Fusion).
    Revolución delgada: `delgado={"espesor", "ubicacion"}` con caras o con `aristas` abiertas (se revoluciona
    la curva como superficie y se le da espesor: lado1 = +espesor según la normal de esa superficie).
    """
    eje = gp_Ax1(_pnt(punto_eje), _gdir(_unit(dir_eje, "dirección del eje")))
    caras = _caras_de(caras)
    abiertas = _cadenas(aristas) if aristas is not None else []
    if not caras and not abiertas:
        raise geo.ErrorGeometria("Elegí al menos un perfil para revolucionar.")
    if delgado and caras:
        caras = _bandas_cerradas(caras, float(delgado["espesor"]), delgado.get("ubicacion", "lado1"))
    elif abiertas and not delgado:
        raise geo.ErrorGeometria("Los perfiles abiertos solo se revolucionan como revolución delgada.")
    if direccion == "un_lado":
        tramos = [(0.0, float(angulo1))]
    elif direccion == "dos_lados":
        tramos = [(0.0, abs(angulo1)), (0.0, -abs(angulo2 or 0.0))]
    elif direccion == "simetrica":
        tramos = [(-abs(angulo1), 2 * abs(angulo1))]
    else:
        raise geo.ErrorGeometria(f"Dirección de revolución desconocida: {direccion}")
    if sum(abs(a) for _, a in tramos) >= 360.0 - 1e-9:
        tramos = [(0.0, 360.0)]
    solidos = []
    for inicio, ang in tramos:
        if abs(ang) < 1e-9:
            continue
        for perfil in caras + abiertas:
            base = _girar(perfil, eje, inicio) if inicio else perfil
            rev = BRepPrimAPI_MakeRevol(base, eje, math.radians(ang)).Shape()
            if perfil.ShapeType() == TopAbs_WIRE:
                t, ubic = float(delgado["espesor"]), delgado.get("ubicacion", "centro")
                partes = {"lado1": [t], "lado2": [-t], "centro": [t / 2, -t / 2]}.get(ubic)
                if partes is None:
                    raise geo.ErrorGeometria(f"Ubicación de pared desconocida: {ubic}")
                solidos += [_engrosar_lamina(rev, e) for e in partes]
            else:
                solidos.append(rev)
    if not solidos:
        raise geo.ErrorGeometria("El ángulo de revolución no puede ser cero.")
    return _validar(_unir(solidos), "Revolución (¿el perfil cruza el eje?)")


# ================================================================ 3. barrido
def _guia_torsion(ruta, grados, radio):
    """Curva auxiliar que gira `grados` alrededor de la ruta: con MakePipeShell en modo auxiliar
    (NoContact) la normal del perfil apunta a ella, así el perfil se tuerce."""
    marcos = _marcos(ruta, max(64, int(abs(grados) / 5) + 2))
    arr = HArray1_gp_Pnt(1, len(marcos))
    for i, (p, _t, u, v) in enumerate(marcos):
        th = math.radians(grados) * i / (len(marcos) - 1)
        arr.SetValue(i + 1, _pnt(p + radio * (math.cos(th) * u + math.sin(th) * v)))
    interp = GeomAPI_Interpolate(arr, False, 1e-7)
    interp.Perform()
    if not interp.IsDone():
        raise geo.ErrorGeometria("No se pudo construir la guía de torsión.")
    return BRepBuilderAPI_MakeWire(BRepBuilderAPI_MakeEdge(interp.Curve()).Edge()).Wire()


def _radio_referencia(alambre, punto):
    """Radio con el que la inclinación de un barrido se pasa a escala: distancia del punto de la ruta al
    contorno si está adentro (exacto en círculos y polígonos regulares centrados); si no, √(A/π)."""
    cara = _cara(alambre)
    d = BRepExtrema_DistShapeShape(BRepBuilderAPI_MakeVertex(_pnt(punto)).Vertex(), alambre).Value()
    if d > 1e-6 and _punto_en_cara(cara, punto):
        return d
    return math.sqrt(geo.area(cara) / math.pi)


def _punto_en_cara(cara, punto):
    """¿El punto (sobre el plano de la cara plana) cae dentro de la cara?"""
    sup = BRepAdaptor_Surface(cara)
    pln = sup.Plane()
    d = _xyz(pln.Location())
    xd, yd = pln.XAxis().Direction(), pln.YAxis().Direction()
    rel = np.asarray(punto, float) - d
    uv = gp_Pnt2d(float(rel @ _xyz(xd)), float(rel @ _xyz(yd)))
    return BRepClass_FaceClassifier(cara, uv, 1e-7).State() == TopAbs_IN


def _ley_escala_carril(ruta, carril, n=33):
    """Ley de escala = distancia(ruta, carril) / distancia inicial, emparejando por fracción de longitud."""
    d0 = None
    puntos = Array1_gp_Pnt2d(1, n)
    for i in range(n):
        f = i / (n - 1)
        d = float(np.linalg.norm(_punto_en(carril, f)[0] - _punto_en(ruta, f)[0]))
        if d0 is None:
            if d < 1e-6:
                raise geo.ErrorGeometria("El carril guía no puede empezar sobre la ruta.")
            d0 = d
        puntos.SetValue(i + 1, gp_Pnt2d(f, d / d0))
    ley = Law_Interpol()
    ley.Set(puntos, False)
    return ley


def _barrido_alambre(perfil, ruta, carril, orientacion, torsion, conicidad, escala_carril, solido, radio_guia):
    ps = BRepOffsetAPI_MakePipeShell(ruta)
    ley = None
    if carril is not None:
        if abs(torsion) > 1e-9 or abs(conicidad) > 1e-9:
            raise geo.ErrorGeometria("La torsión y la inclinación no se combinan con un carril guía.")
        if escala_carril not in ("escalar", "estirar", "ninguna"):
            raise geo.ErrorGeometria(f"Escala de carril desconocida: {escala_carril}")
        # El carril orienta el perfil (normal hacia el carril) y, salvo "ninguna", lo escala con la distancia
        # ruta→carril (ley propia: el modo ContactOnBorder de OCC solo funciona con perfiles suaves).
        ps.SetMode(carril, True, BRepFill_NoContact)
        if escala_carril != "ninguna":
            ley = _ley_escala_carril(ruta, carril)
    elif abs(torsion) > 1e-9:
        ps.SetMode(_guia_torsion(ruta, torsion, radio_guia), True, BRepFill_NoContact)
    elif orientacion == "paralela":
        p0, t0 = _punto_en(ruta, 0.0)
        ps.SetMode(gp_Ax2(_pnt(p0), _gdir(t0), _gdir(_perpendicular(t0))))
    elif orientacion == "perpendicular":
        ps.SetMode(False)           # triedro de Frenet corregido
    else:
        raise geo.ErrorGeometria(f"Orientación de barrido desconocida: {orientacion}")
    ps.SetTransitionMode(BRepBuilderAPI_RightCorner)
    if abs(conicidad) > 1e-9:
        p0, _ = _punto_en(ruta, 0.0)
        escala = 1.0 + _longitud(ruta) * math.tan(math.radians(conicidad)) / _radio_referencia(perfil, p0)
        if escala <= 0.01:
            raise geo.ErrorGeometria("La inclinación del barrido hace desaparecer el perfil antes del final.")
        ley = Law_Linear()
        ley.Set(0.0, 1.0, 1.0, escala)
    if ley is not None:
        ps.SetLaw(perfil, ley, False, False)
    else:
        ps.Add(perfil, False, False)
    try:
        ps.Build()
        hecho = ps.IsDone()
    except Exception:  # noqa: BLE001 — OCC lanza Standard_ConstructionError en los casos que no resuelve
        hecho = False
    if not hecho:
        raise geo.ErrorGeometria("El kernel no pudo barrer el perfil por la ruta.")
    if solido and not ps.MakeSolid():
        raise geo.ErrorGeometria("El barrido no cierra un sólido (¿el perfil está abierto?).")
    return ps.Shape()


def barrer(perfiles, ruta, *, carril=None, orientacion="perpendicular", distancia=1.0, torsion=0.0,
           conicidad=0.0, escala_carril="escalar", solido=True):
    """Barrido de Fusion [SLD-SWEEP-SOLID, SLD-REF-SWEEP] con BRepOffsetAPI_MakePipeShell.

    perfiles: caras planas (con agujeros) o alambres; ruta: aristas encadenadas o alambre. `distancia` =
    fracción 0..1 de la ruta. `torsion` y `conicidad` en grados (conicidad positiva = la región se ensancha;
    se aplica como escala lineal de cada lazo: los agujeros se achican). `carril` = Path + Guide Rail:
    `escala_carril` "escalar" (el perfil se agranda con la distancia ruta→carril), "ninguna" (el carril solo
    orienta); "estirar" (escala en una sola dirección) no existe en OCC y se hace como "escalar".
    `solido=False` devuelve la superficie.
    """
    ruta = _recortar_alambre(_alambre(ruta), float(distancia))
    carril = _alambre(carril) if carril is not None else None
    salida = []
    for perfil in _lista(perfiles):
        if perfil.ShapeType() == TopAbs_FACE:
            cara = TopoDS.Face(perfil)
            exterior = BRepTools.OuterWire_s(cara)
            interiores = [TopoDS.Wire(w) for w in _explorar(cara, TopAbs_WIRE) if not w.IsSame(exterior)]
        else:
            exterior, interiores = _alambre(perfil), []
        bb = geo.caja_envolvente(exterior)
        radio_guia = max(1.0, float(np.linalg.norm(np.subtract(bb[1], bb[0]))))
        forma = _barrido_alambre(exterior, ruta, carril, orientacion, torsion, conicidad, escala_carril, solido,
                                 radio_guia)
        if solido:
            for w in interiores:   # el agujero se achica cuando la región se ensancha
                hueco = _barrido_alambre(w, ruta, carril, orientacion, torsion, -conicidad, escala_carril, True,
                                         radio_guia)
                forma = geo.booleano(forma, hueco, "cortar")
        salida.append(forma)
    if not salida:
        raise geo.ErrorGeometria("Elegí al menos un perfil para barrer.")
    resultado = _unir(salida) if solido else geo.compuesto(salida)
    return _validar(resultado, "Barrido")


# ================================================================ 4. solevado
def _seccion(s):
    """('vertice', TopoDS_Vertex) | ('alambre', exterior, [interiores])."""
    if isinstance(s, (tuple, list, np.ndarray)) and len(s) == 3 and all(np.isscalar(c) for c in s):
        return ("vertice", BRepBuilderAPI_MakeVertex(_pnt(s)).Vertex())
    if s.ShapeType() == TopAbs_VERTEX:
        return ("vertice", TopoDS.Vertex(s))
    if s.ShapeType() == TopAbs_FACE:
        cara = TopoDS.Face(s)
        exterior = BRepTools.OuterWire_s(cara)
        interiores = [TopoDS.Wire(w) for w in _explorar(cara, TopAbs_WIRE) if not w.IsSame(exterior)]
        return ("alambre", exterior, interiores)
    return ("alambre", _alambre(s), [])


def _loft(alambres, solido, reglada, cerrada):
    ts = BRepOffsetAPI_ThruSections(solido, reglada)
    for tipo, forma in alambres:
        (ts.AddVertex if tipo == "vertice" else ts.AddWire)(forma)
    if cerrada:
        ts.AddWire(alambres[0][1])
    ts.Build()
    if not ts.IsDone():
        raise geo.ErrorGeometria("El kernel no pudo solevar estas secciones.")
    return ts.Shape()


def solevar(secciones, *, carriles=(), linea_central=None, cerrada=False, solido=True, reglada=False):
    """Solevado (Loft) de Fusion [SLD-LOFT-SOLID].

    secciones: caras (se respetan los agujeros si todas tienen la misma cantidad), alambres/aristas, o un
    punto/vértice como primera o última sección. `cerrada` une la última sección con la primera. Con
    `linea_central` se usa MakePipeShell con todas las secciones. Con `carriles`: OpenCascade no tiene
    solevado con varios carriles; se admite UNO, como guía de contacto (el borde del solevado lo sigue)
    sobre una línea central dada o sobre la polilínea de los centros de las secciones.
    """
    secs = [_seccion(s) for s in _lista(secciones)]
    if len(secs) < 2:
        raise geo.ErrorGeometria("El solevado necesita al menos dos secciones.")
    if any(s[0] == "vertice" for s in secs[1:-1]):
        raise geo.ErrorGeometria("Un punto solo puede ser la primera o la última sección.")
    if cerrada and any(s[0] == "vertice" for s in secs):
        raise geo.ErrorGeometria("Un solevado cerrado no admite puntos como sección.")
    carriles = _lista(carriles)
    if len(carriles) > 1:
        raise geo.ErrorGeometria("OpenCascade no admite solevado con varios carriles: usá uno solo o una "
                                 "línea central.")
    exteriores = [(s[0], s[1]) for s in secs]
    if linea_central is not None or carriles:
        if cerrada:
            raise geo.ErrorGeometria("El solevado cerrado no se combina con línea central ni carril.")
        if linea_central is not None:
            espina = _alambre(linea_central)
        else:
            # Polilínea por los centros. Se redondean: un ruido de 1e-14 en los centros hace fallar a
            # Approx_CurvlinFunc al barrer con carril.
            centros = [np.round(_xyz(BRep_Tool.Pnt_s(f)) if t == "vertice" else _centro_alambre(f), 9)
                       for t, f in exteriores]
            espina = _alambre([BRepBuilderAPI_MakeEdge(_pnt(a), _pnt(b)).Edge()
                               for a, b in zip(centros[:-1], centros[1:], strict=True)])
        ps = BRepOffsetAPI_MakePipeShell(espina)
        if carriles:
            ps.SetMode(_alambre(carriles[0]), True, BRepFill_ContactOnBorder)
        else:
            ps.SetMode(False)
        for _t, f in exteriores:
            ps.Add(f, False, False)
        try:
            ps.Build()
            hecho = ps.IsDone()
        except Exception:  # noqa: BLE001 — OCC lanza Standard_ConstructionError en los casos que no resuelve
            hecho = False
        if not hecho:
            raise geo.ErrorGeometria("El kernel no pudo solevar con ese carril (OpenCascade solo lo logra con "
                                     "secciones suaves, sin esquinas)." if carriles else
                                     "El kernel no pudo solevar con esa línea central.")
        if solido:
            ps.MakeSolid()
        forma = ps.Shape()
    else:
        forma = _loft(exteriores, solido, reglada, cerrada)
        huecos = [s[2] for s in secs if s[0] == "alambre"]
        if solido and huecos and all(huecos) and len({len(h) for h in huecos}) == 1:
            for k in range(len(huecos[0])):
                cadena = [("alambre", huecos[0][k])]
                for siguiente in huecos[1:]:   # empareja cada agujero con el más cercano de la sección siguiente
                    c = _centro_alambre(cadena[-1][1])
                    cercano = min(siguiente, key=lambda w, c=c: np.linalg.norm(_centro_alambre(w) - c))
                    cadena.append(("alambre", cercano))
                forma = geo.booleano(forma, _loft(cadena, True, reglada, cerrada), "cortar")
    return _validar(forma, "Solevado")


def _centro_alambre(w):
    p = GProp_GProps()
    BRepGProp.LinearProperties_s(w, p)
    return _xyz(p.CentreOfMass())


# ================================================================ 5. nervio y red
def _extender_extremos(alambre, largo):
    """Prolonga por la tangente los dos extremos de un alambre abierto (Extend Curves de Fusion)."""
    if _es_cerrado(alambre):
        return alambre
    p0, t0 = _punto_en(alambre, 0.0)
    p1, t1 = _punto_en(alambre, 1.0)
    return _alambre([BRepBuilderAPI_MakeEdge(_pnt(p0 - t0 * largo), _pnt(p0)).Edge()] + _aristas_de(alambre)
                    + [BRepBuilderAPI_MakeEdge(_pnt(p1), _pnt(p1 + t1 * largo)).Edge()])


def _sentido_hacia_cuerpo(cuerpo, alambre, candidatos, invertir):
    """De los sentidos candidatos, el que choca antes con el cuerpo partiendo del medio de la curva."""
    medio, _ = _punto_en(alambre, 0.5)
    mejor = None
    for d in candidatos:
        choques = [h for h in _rayo(cuerpo, medio, d) if h > 1e-7]
        if choques and (mejor is None or choques[0] < mejor[0]):
            mejor = (choques[0], d)
    if mejor is None:
        raise geo.ErrorGeometria("Desde la curva no se llega al cuerpo en ningún sentido.")
    return -mejor[1] if invertir else mejor[1]


def _caja_de(forma, margen):
    (x0, y0, z0), (x1, y1, z1) = geo.caja_envolvente(forma)
    return geo.caja(x1 - x0 + 2 * margen, y1 - y0 + 2 * margen, z1 - z0 + 2 * margen,
                    (x0 - margen, y0 - margen, z0 - margen))


def _diagonal(forma):
    bb = geo.caja_envolvente(forma)
    return float(np.linalg.norm(np.subtract(bb[1], bb[0])))


def _hasta_el_cuerpo(bruto, cuerpo, curvas, margen, que, profundidad):
    """Recorta un nervio/red largo: dentro de la caja del cuerpo, fuera del cuerpo, y solo el trozo que
    nace de las curvas. Sin profundidad (To Next) además tiene que tocar al cuerpo."""
    bruto = geo.booleano(bruto, _caja_de(cuerpo, margen), "intersecar")
    piezas = _piezas_que_tocan(geo.booleano(bruto, cuerpo, "cortar"), curvas)
    if not piezas:
        raise geo.ErrorGeometria(f"{que}: la curva queda dentro del cuerpo.")
    resultado = _unir(piezas)
    if profundidad is None and not geo.se_tocan(resultado, cuerpo, 1e-4):
        raise geo.ErrorGeometria(f"{que}: no llega al cuerpo (revisá el sentido o usá una profundidad).")
    return _validar(resultado, que)


def nervio(cuerpo, aristas_curva, normal_plano, espesor, *, profundidad=None, direccion="simetrica",
           invertir=False, extender=True):
    """Nervio (Rib) de Fusion [SLD-RIB]: pared delgada que crece desde una curva abierta, PARALELA al plano
    del boceto y perpendicular a la cuerda de la curva, hasta las caras más cercanas del cuerpo ("To Next")
    o una `profundidad`. El espesor se mide perpendicular al plano: "simetrica" (mitad a cada lado),
    "lado1" (hacia +normal) o "lado2". `invertir` cambia el sentido de crecimiento. Devuelve solo el nervio,
    ya recortado contra el cuerpo (la unión la hace la capa de operaciones)."""
    n = _unit(normal_plano, "normal del plano del boceto")
    w = _alambre(aristas_curva)
    if _es_cerrado(w):
        raise geo.ErrorGeometria("El nervio necesita una curva abierta.")
    if espesor <= 0:
        raise geo.ErrorGeometria("El espesor del nervio debe ser positivo.")
    cuerda = _punto_en(w, 1.0)[0] - _punto_en(w, 0.0)[0]
    m = _unit(np.cross(n, cuerda), "cuerda de la curva")
    m = _sentido_hacia_cuerpo(cuerpo, w, (m, -m), invertir)
    largo_max = 2 * _diagonal(cuerpo)
    w_ext = _extender_extremos(w, largo_max) if extender else w
    region = _unificar(BRepPrimAPI_MakePrism(w_ext, _gvec(m * (profundidad or largo_max))).Shape())
    lo, hi = {"simetrica": (-espesor / 2, espesor / 2), "lado1": (0.0, espesor),
              "lado2": (-espesor, 0.0)}.get(direccion, (None, None))
    if lo is None:
        raise geo.ErrorGeometria(f"Dirección de espesor desconocida: {direccion}")
    bruto = _unir([BRepPrimAPI_MakePrism(_trasladar(f, n * lo), _gvec(n * (hi - lo))).Shape()
                   for f in _caras_de(region)])
    return _hasta_el_cuerpo(bruto, cuerpo, [w], 0.0, "Nervio", profundidad)


def red(cuerpo, aristas_curvas, normal_plano, espesor, profundidad=None, *, direccion="simetrica",
        invertir=False, extender=True):
    """Red (Web) de Fusion [SLD-WEB]: una o varias curvas abiertas se extruyen PERPENDICULARES al plano del
    boceto hasta las caras más cercanas del cuerpo ("To Next") o una `profundidad`; el espesor va en el plano,
    a los dos lados de la curva ("simetrica") o a uno ("lado1" = izquierda de la curva mirando desde +normal).
    `extender` prolonga las curvas hasta el cuerpo. Devuelve el sólido de la red ya recortado."""
    n = _unit(normal_plano, "normal del plano del boceto")
    cadenas = _cadenas(aristas_curvas)
    if not cadenas or any(_es_cerrado(w) for w in cadenas):
        raise geo.ErrorGeometria("La red necesita curvas abiertas.")
    if espesor <= 0:
        raise geo.ErrorGeometria("El espesor de la red debe ser positivo.")
    d = _sentido_hacia_cuerpo(cuerpo, cadenas[0], (-n, n), invertir)
    # Engrosar la lámina con +t va a la izquierda de la curva mirando desde el sentido de extrusión.
    s = 1.0 if float(d @ n) > 0 else -1.0
    espesores = {"simetrica": [espesor / 2, -espesor / 2], "lado1": [s * espesor],
                 "lado2": [-s * espesor]}.get(direccion)
    if espesores is None:
        raise geo.ErrorGeometria(f"Dirección de espesor desconocida: {direccion}")
    largo_max = 2 * _diagonal(cuerpo)
    solidos = []
    for w in cadenas:
        w_ext = _extender_extremos(w, largo_max) if extender else w
        lamina = BRepPrimAPI_MakePrism(w_ext, _gvec(d * (profundidad or largo_max))).Shape()
        solidos += [_engrosar_lamina(lamina, e) for e in espesores]
    return _hasta_el_cuerpo(_unir(solidos), cuerpo, cadenas, 0.0, "Red", profundidad)


# ================================================================ 6. repujado
def repujado(cuerpo, caras_perfil, cara_objetivo, profundidad, *, tipo="relieve", envolver=False):
    """Repujado (Emboss) de Fusion [SLD-EMBOSS]: "relieve" agrega material, "grabado" lo quita (profundidad
    negativa invierte el efecto, como en Fusion). Devuelve el cuerpo resultante.

    Cara objetivo plana: los perfiles (en un plano paralelo) se proyectan sobre ella y el efecto se limita a la
    cara. Cara cilíndrica con `envolver=True`: el boceto (en un plano paralelo al eje) se enrolla sobre el
    cilindro conservando las longitudes (arco = distancia en el boceto) y se le da espesor radial."""
    if profundidad < 0:
        profundidad, tipo = -profundidad, ("grabado" if tipo == "relieve" else "relieve")
    if profundidad < 1e-9:
        raise geo.ErrorGeometria("La profundidad del repujado no puede ser cero.")
    if tipo not in ("relieve", "grabado"):
        raise geo.ErrorGeometria(f"Efecto de repujado desconocido: {tipo}")
    perfiles = _caras_de(caras_perfil)
    if not perfiles:
        raise geo.ErrorGeometria("Elegí al menos un perfil para repujar.")
    cara = TopoDS.Face(cara_objetivo)
    pl = geo.plano_de_cara(cara)
    sentido = 1.0 if tipo == "relieve" else -1.0
    if pl is not None:
        herr = []
        for f in perfiles:
            if abs(abs(float(_normal_superficie(f) @ pl.normal)) - 1) > 1e-6:
                raise geo.ErrorGeometria("Los perfiles deben estar en un plano paralelo a la cara objetivo.")
            c = np.array(geo.centro_masa(f, superficie=True))
            sobre = _trasladar(f, pl.normal * float((pl.origen - c) @ pl.normal))
            herr.append(_prisma(sobre, pl.normal, sentido * profundidad))
        herramienta = geo.booleano(_unir(herr), _prisma(cara, pl.normal, sentido * profundidad), "intersecar")
    elif BRepAdaptor_Surface(cara).GetType() == GeomAbs_Cylinder:
        if not envolver:
            raise geo.ErrorGeometria("Sobre una cara cilíndrica el repujado se hace envolviendo (envolver=True).")
        herramienta = _envolver_en_cilindro(perfiles, cara, profundidad, tipo)
    else:
        raise geo.ErrorGeometria("El repujado admite caras planas o cilíndricas (envolviendo).")
    if geo.esta_vacia(herramienta):
        raise geo.ErrorGeometria("Los perfiles no caen sobre la cara objetivo.")
    resultado = geo.booleano(cuerpo, herramienta, "unir" if tipo == "relieve" else "cortar")
    return _validar(_unificar(resultado), "Repujado")


def _normal_orientada(cara, u, v):
    sup = BRepAdaptor_Surface(cara)
    p, du, dv = gp_Pnt(), gp_Vec(), gp_Vec()
    sup.D1(u, v, p, du, dv)
    nrm = np.cross(_xyz(du), _xyz(dv))
    if cara.Orientation() == TopAbs_REVERSED:
        nrm = -nrm
    return _xyz(p), _unit(nrm, "normal de la cara")


def _segmento2d(a, b):
    largo = a.Distance(b)
    if largo < 1e-12:
        raise geo.ErrorGeometria("El boceto tiene un segmento de largo nulo.")
    return Geom2d_TrimmedCurve(Geom2d_Line(a, gp_Dir2d(b.X() - a.X(), b.Y() - a.Y())), 0.0, largo)


def _aristas_envueltas(e, a_uv, superficie):
    """Arista del boceto llevada al cilindro: las rectas quedan exactas (hélices); las curvas se interpolan,
    partidas en 4 tramos si son cerradas (un lazo de una sola arista BSpline deja mal el engrosado)."""
    curva = BRepAdaptor_Curve(e)
    u_a, u_b = curva.FirstParameter(), curva.LastParameter()
    if e.Orientation() == TopAbs_REVERSED:
        u_a, u_b = u_b, u_a
    if curva.GetType() == GeomAbs_Line:
        tramos = [_segmento2d(a_uv(_xyz(curva.Value(u_a))), a_uv(_xyz(curva.Value(u_b))))]
    else:
        partes = 4 if curva.Value(u_a).Distance(curva.Value(u_b)) < 1e-7 else 1
        tramos = []
        for i in range(partes):
            t0 = u_a + (u_b - u_a) * i / partes
            t1 = u_a + (u_b - u_a) * (i + 1) / partes
            muestras = 16
            arr = HArray1_gp_Pnt2d(1, muestras + 1)
            for k in range(muestras + 1):
                arr.SetValue(k + 1, a_uv(_xyz(curva.Value(t0 + (t1 - t0) * k / muestras))))
            interp = Geom2dAPI_Interpolate(arr, False, 1e-9)
            interp.Perform()
            tramos.append(interp.Curve())
    aristas = []
    for c2d in tramos:
        arista = BRepBuilderAPI_MakeEdge(c2d, superficie).Edge()
        BRepLib.BuildCurves3d_s(arista, 1e-6)
        aristas.append(arista)
    return aristas


def _envolver_en_cilindro(perfiles, cara, profundidad, tipo):
    sup = BRepAdaptor_Surface(cara)
    cil = sup.Cylinder()
    radio = cil.Radius()
    ax3 = cil.Position()
    o, z = _xyz(ax3.Location()), _xyz(ax3.Direction())
    x, y = _xyz(ax3.XDirection()), _xyz(ax3.YDirection())
    giro = 1.0 if float(np.cross(z, x) @ y) > 0 else -1.0     # terna derecha o izquierda del cilindro
    um = (sup.FirstUParameter() + sup.LastUParameter()) / 2
    vm = (sup.FirstVParameter() + sup.LastVParameter()) / 2
    p, nrm = _normal_orientada(cara, um, vm)
    afuera = float(nrm @ (p - o - z * float((p - o) @ z))) > 0      # cilindro macizo (True) o agujero
    superficie = Geom_CylindricalSurface(ax3, radio)
    herramientas = []
    for f in perfiles:
        nf = _normal_superficie(f)
        if abs(float(nf @ z)) > 1e-6:
            raise geo.ErrorGeometria("El boceto a envolver debe estar en un plano paralelo al eje del cilindro.")
        c = np.array(geo.centro_masa(f, superficie=True))
        er = nf if float((c - o) @ nf) >= 0 else -nf
        et = np.cross(z, er)
        u0 = math.atan2(float(er @ y), float(er @ x))

        def a_uv(q, et=et, u0=u0):
            rel = np.asarray(q, float) - o
            return gp_Pnt2d(u0 + giro * float(rel @ et) / radio, float(rel @ z))

        exterior = BRepTools.OuterWire_s(f)
        envueltos = []
        for w in [exterior] + [TopoDS.Wire(w) for w in _explorar(f, TopAbs_WIRE) if not w.IsSame(exterior)]:
            mk = BRepBuilderAPI_MakeWire()
            for e in _aristas_de(w):
                for arista in _aristas_envueltas(e, a_uv, superficie):
                    mk.Add(arista)
            if not mk.IsDone():
                raise geo.ErrorGeometria("No se pudo envolver el contorno sobre el cilindro.")
            envueltos.append(mk.Wire())
        mf = BRepBuilderAPI_MakeFace(superficie, envueltos[0], True)
        for w in envueltos[1:]:
            mf.Add(w)
        arreglo = ShapeFix_Face(mf.Face())
        arreglo.Perform()
        lamina = arreglo.Face()
        bu0, bu1, bv0, bv1 = BRepTools.UVBounds_s(lamina)
        p_l, n_l = _normal_orientada(lamina, (bu0 + bu1) / 2, (bv0 + bv1) / 2)
        normal_afuera = float(n_l @ (p_l - o - z * float((p_l - o) @ z))) > 0
        # relieve: hacia afuera del material (lejos del eje en un macizo, hacia el eje en un agujero)
        lejos_del_eje = (tipo == "relieve") == afuera
        herramientas.append(_engrosar_lamina(lamina, profundidad if lejos_del_eje == normal_afuera else -profundidad))
    return _unir(herramientas)


# ================================================================ 7. agujero
def herramienta_agujero(punto, direccion, *, tipo="simple", diametro=None, profundidad=10.0, punta="angulo",
                        angulo_punta=118.0, diam_abocardado=None, prof_abocardado=None, diam_avellanado=None,
                        angulo_avellanado=90.0, roscado=None, mano="derecha"):
    """Sólido a restar de un agujero de Fusion (revolución del medio perfil). `direccion` apunta hacia el
    material; `profundidad` llega hasta el hombro (sin la punta, como en Fusion). `roscado` = designación de
    TABLA_ROSCAS: el agujero se hace al diámetro menor básico y se le suma el surco helicoidal de la rosca."""
    d = _unit(direccion, "dirección del agujero")
    p = np.asarray(punto, float)
    if roscado:
        datos = datos_rosca(roscado)
        diametro = datos["diametro_menor"]
    if diametro is None or diametro <= 0:
        raise geo.ErrorGeometria("El diámetro del agujero debe ser positivo.")
    if profundidad is None or profundidad <= 0:
        raise geo.ErrorGeometria("La profundidad del agujero debe ser positiva.")
    r = diametro / 2
    medio = [(0.0, 0.0)]
    if tipo == "simple":
        medio.append((r, 0.0))
    elif tipo == "abocardado":
        if not diam_abocardado or diam_abocardado <= diametro or not prof_abocardado or prof_abocardado <= 0:
            raise geo.ErrorGeometria("El abocardado necesita diámetro mayor que el del agujero y profundidad positiva.")
        if prof_abocardado >= profundidad:
            raise geo.ErrorGeometria("La profundidad del abocardado supera la del agujero.")
        medio += [(diam_abocardado / 2, 0.0), (diam_abocardado / 2, prof_abocardado), (r, prof_abocardado)]
    elif tipo == "avellanado":
        if not diam_avellanado or diam_avellanado <= diametro or not 0 < angulo_avellanado < 180:
            raise geo.ErrorGeometria("El avellanado necesita diámetro mayor que el del agujero y ángulo entre "
                                     "0° y 180°.")
        h = (diam_avellanado - diametro) / 2 / math.tan(math.radians(angulo_avellanado) / 2)
        if h >= profundidad:
            raise geo.ErrorGeometria("El avellanado es más profundo que el agujero.")
        medio += [(diam_avellanado / 2, 0.0), (r, h)]
    else:
        raise geo.ErrorGeometria(f"Tipo de agujero desconocido: {tipo}")
    medio.append((r, profundidad))
    if punta == "angulo":
        if not 0 < angulo_punta < 180:
            raise geo.ErrorGeometria("El ángulo de la punta debe estar entre 0° y 180°.")
        medio.append((0.0, profundidad + r / math.tan(math.radians(angulo_punta) / 2)))
    elif punta == "plana":
        medio.append((0.0, profundidad))
    else:
        raise geo.ErrorGeometria(f"Punta de broca desconocida: {punta}")
    e = _perpendicular(d)
    perfil = _cara(_poligono([p + e * rho + d * zz for rho, zz in medio]))
    herramienta = BRepPrimAPI_MakeRevol(perfil, gp_Ax1(_pnt(p), _gdir(d)), 2 * math.pi).Shape()
    if roscado:
        surco = _surco_rosca(p, d, datos["diametro"], datos["paso"], 0.0, profundidad, True, mano, radio_cara=r)
        herramienta = geo.booleano(herramienta, surco, "unir")
    return _validar(herramienta, "Agujero")


def agujero(cuerpo, punto, direccion, *, profundidad=None, **opciones):
    """Agujero (Hole) de Fusion [GUID-0DFCBD4F…, GUID-3A76B269…]: devuelve la HERRAMIENTA a restar del
    cuerpo. `profundidad=None` = extensión "Todo" (pasante: llega al otro lado del cuerpo, punta plana).
    El resto de las opciones son las de `herramienta_agujero`."""
    d = _unit(direccion, "dirección del agujero")
    if profundidad is None:
        _, hi = _caja_proyectada(cuerpo, punto, d)
        if hi <= 0:
            raise geo.ErrorGeometria("El cuerpo no está en la dirección del agujero.")
        profundidad = hi + _MARGEN
        opciones["punta"] = "plana"
    return herramienta_agujero(punto, d, profundidad=profundidad, **opciones)


# ================================================================ 8. roscas
# Métrica ISO (ISO 261 / ISO 724, perfil básico de 60°) y unificada UNC/UNF (ASME B1.1). Broca para roscar:
# en métrica D − P redondeado como en las tablas de taller; en UN, la broca de número/letra/fracción usual.
_ISO_GRUESA = [(1.6, 0.35, 1.25), (2, 0.4, 1.6), (2.5, 0.45, 2.05), (3, 0.5, 2.5), (3.5, 0.6, 2.9), (4, 0.7, 3.3),
               (5, 0.8, 4.2), (6, 1.0, 5.0), (8, 1.25, 6.8), (10, 1.5, 8.5), (12, 1.75, 10.2), (14, 2.0, 12.0),
               (16, 2.0, 14.0), (18, 2.5, 15.5), (20, 2.5, 17.5), (22, 2.5, 19.5), (24, 3.0, 21.0), (27, 3.0, 24.0),
               (30, 3.5, 26.5), (33, 3.5, 29.5), (36, 4.0, 32.0), (39, 4.0, 35.0), (42, 4.5, 37.5), (45, 4.5, 40.5),
               (48, 5.0, 43.0), (52, 5.0, 47.0), (56, 5.5, 50.5), (60, 5.5, 54.5), (64, 6.0, 58.0)]
_ISO_FINA = [(1.6, 0.2), (2, 0.25), (2.5, 0.35), (3, 0.35), (4, 0.5), (5, 0.5), (6, 0.75), (8, 1.0), (10, 1.25),
             (10, 1.0), (12, 1.5), (12, 1.25), (14, 1.5), (16, 1.5), (18, 2.0), (18, 1.5), (20, 2.0), (20, 1.5),
             (22, 2.0), (22, 1.5), (24, 2.0), (27, 2.0), (30, 2.0), (33, 2.0), (36, 3.0), (39, 3.0), (42, 3.0),
             (45, 3.0), (48, 3.0), (52, 4.0), (56, 4.0), (60, 4.0), (64, 4.0)]
_UNC = [("#4", 0.112, 40, 0.0890), ("#6", 0.138, 32, 0.1065), ("#8", 0.164, 32, 0.1360), ("#10", 0.190, 24, 0.1495),
        ("1/4", 0.250, 20, 0.2010), ("5/16", 0.3125, 18, 0.2570), ("3/8", 0.375, 16, 0.3125),
        ("7/16", 0.4375, 14, 0.3680), ("1/2", 0.500, 13, 0.4219), ("9/16", 0.5625, 12, 0.4844),
        ("5/8", 0.625, 11, 0.5312), ("3/4", 0.750, 10, 0.6562), ("7/8", 0.875, 9, 0.7656), ("1", 1.000, 8, 0.8750)]
_UNF = [("#4", 0.112, 48, 0.0935), ("#6", 0.138, 40, 0.1130), ("#8", 0.164, 36, 0.1360), ("#10", 0.190, 32, 0.1590),
        ("1/4", 0.250, 28, 0.2130), ("5/16", 0.3125, 24, 0.2720), ("3/8", 0.375, 24, 0.3320),
        ("7/16", 0.4375, 20, 0.3906), ("1/2", 0.500, 20, 0.4531), ("9/16", 0.5625, 18, 0.5156),
        ("5/8", 0.625, 18, 0.5781), ("3/4", 0.750, 16, 0.6875), ("7/8", 0.875, 14, 0.8125), ("1", 1.000, 12, 0.9219)]


def _armar_tabla():
    tabla = {}
    for d, p, b in _ISO_GRUESA:
        tabla[f"M{d:g}x{p:g}"] = {"norma": "ISO métrica gruesa", "diametro": float(d), "paso": p, "broca": b}
    for d, p in _ISO_FINA:
        tabla[f"M{d:g}x{p:g}"] = {"norma": "ISO métrica fina", "diametro": float(d), "paso": p,
                                  "broca": round(d - p, 2)}
    for serie, filas in (("UNC", _UNC), ("UNF", _UNF)):
        for t, d, tpi, b in filas:
            tabla[f"{t}-{tpi} {serie}"] = {"norma": f"Unificada {serie}", "diametro": round(d * 25.4, 4),
                                          "paso": 25.4 / tpi, "broca": round(b * 25.4, 3)}
    return tabla


TABLA_ROSCAS = _armar_tabla()
_GRUESA_POR_D = {f"M{d:g}": f"M{d:g}x{p:g}" for d, p, _b in _ISO_GRUESA}


def datos_rosca(designacion):
    """Datos de una rosca: 'M6' (gruesa), 'M6x0.75', '1/4-20 UNC', '#10-32 UNF' (sin serie, prueba UNC y
    UNF). Agrega `designacion` canónica y `diametro_menor` básico = D − 1,0825·P (5H/4 del perfil de 60°)."""
    texto = str(designacion).strip().replace("×", "x").replace("X", "x")
    clave = None
    m = re.fullmatch(r"[Mm]\s*(\d+(?:\.\d+)?)(?:\s*x\s*(\d+(?:\.\d+)?))?", texto)
    if m:
        d = float(m.group(1))
        clave = f"M{d:g}x{float(m.group(2)):g}" if m.group(2) else _GRUESA_POR_D.get(f"M{d:g}")
    else:
        m = re.fullmatch(r"(#?\d+(?:/\d+)?)\s*-\s*(\d+)\s*(UNC|UNF|unc|unf)?", texto)
        if m:
            serie = (m.group(3) or "").upper()
            candidatas = [f"{m.group(1)}-{m.group(2)} {s}" for s in ((serie,) if serie else ("UNC", "UNF"))]
            clave = next((c for c in candidatas if c in TABLA_ROSCAS), None)
    if clave is None or clave not in TABLA_ROSCAS:
        raise geo.ErrorGeometria(f"Rosca desconocida: {designacion}")
    datos = dict(TABLA_ROSCAS[clave], designacion=clave)
    datos["diametro_menor"] = datos["diametro"] - 2 * (5 / 8) * (math.sqrt(3) / 2) * datos["paso"]
    return datos


def _helice(origen, eje, x, radio, paso, altura, mano="derecha", angulo=0.0):
    """Hélice como recta en el espacio (u, v) de un cilindro (o de un cono, con `angulo` en grados)."""
    if mano not in ("derecha", "izquierda"):
        raise geo.ErrorGeometria(f"Mano desconocida: {mano}")
    ax3 = gp_Ax3(_pnt(origen), _gdir(eje), _gdir(x))
    du = 2 * math.pi * (altura / paso) * (1 if mano == "derecha" else -1)
    if abs(angulo) > 1e-9:
        if abs(angulo) >= 89:
            raise geo.ErrorGeometria("El ángulo de la bobina debe estar entre -89° y 89°.")
        a = math.radians(angulo)
        sup, dv = Geom_ConicalSurface(ax3, a, radio), altura / math.cos(a)
    else:
        sup, dv = Geom_CylindricalSurface(ax3, radio), altura
    arista = BRepBuilderAPI_MakeEdge(Geom2d_Line(gp_Pnt2d(0.0, 0.0), gp_Dir2d(du, dv)), sup,
                                     0.0, math.hypot(du, dv)).Edge()
    BRepLib.BuildCurves3d_s(arista, 1e-6)
    return BRepBuilderAPI_MakeWire(arista).Wire()


def _barrido_helicoidal(perfil, helice):
    ps = BRepOffsetAPI_MakePipeShell(helice)
    ps.SetMode(True)      # Frenet: sobre una hélice es un movimiento helicoidal exacto del perfil
    ps.Add(perfil, False, False)
    ps.Build()
    if not ps.IsDone() or not ps.MakeSolid():
        raise geo.ErrorGeometria("El kernel no pudo barrer el perfil por la hélice.")
    return ps.Shape()


def _surco_rosca(origen, eje, diametro, paso, z0, largo, interna, mano, radio_cara=None):
    """Sólido helicoidal con la forma del hueco entre filetes (perfil básico ISO/UN de 60°) recortado al
    tramo [z0, z0 + largo] del eje. Rosca exterior: se le resta al cilindro; interior: al cuerpo agujereado."""
    z = _unit(eje)
    x = _perpendicular(z)
    o = np.asarray(origen, float)
    prof = 5 / 8 * math.sqrt(3) / 2 * paso         # 5H/8: altura del filete básico
    pend = 2 * math.tan(math.radians(30))          # ancho que gana el surco por mm radial (flancos a 60°)
    extra = 0.1 * paso                             # el surco sobresale del material para cortar limpio
    if interna:
        r_out, w_out = diametro / 2, paso / 8
        r_in, w_in = diametro / 2 - prof - extra, 3 * paso / 4 + pend * extra
        if radio_cara is not None and radio_cara >= r_out - 1e-6:
            raise geo.ErrorGeometria("El agujero es más grande que el diámetro mayor de la rosca.")
    else:
        r_in, w_in = diametro / 2 - prof, paso / 4
        r_out, w_out = diametro / 2 + extra, 7 * paso / 8 + pend * extra
        if radio_cara is not None and radio_cara > r_out - 0.01 * paso:
            raise geo.ErrorGeometria("El cilindro es más grueso que el diámetro mayor de la rosca.")
        if radio_cara is not None and radio_cara <= r_in:
            raise geo.ErrorGeometria("El cilindro es más fino que el núcleo de la rosca.")
    z_ini = z0 - paso                              # la hélice pasa de largo un paso en cada punta
    base = o + z * (z_ini + paso / 2)
    perfil = _poligono([base + x * r_in - z * w_in / 2, base + x * r_out - z * w_out / 2,
                        base + x * r_out + z * w_out / 2, base + x * r_in + z * w_in / 2])
    surco = _barrido_helicoidal(perfil, _helice(base, z, x, (r_in + r_out) / 2, paso, largo + 2 * paso, mano))
    tramo = geo.cilindro(r_out + 1.0, largo, base=tuple(o + z * z0), eje=tuple(z))
    surco = geo.booleano(surco, tramo, "intersecar")
    if interna and radio_cara is not None:
        # Se le saca al surco la parte que cae dentro del agujero: cortar el cuerpo con el surco entero falla
        # sin avisar en varios tamaños (M10, M12, M20), y con este paso previo sale bien en todos.
        hueco = geo.cilindro(radio_cara, largo + 2.0, base=tuple(o + z * (z0 - 1.0)), eje=tuple(z))
        surco = geo.booleano(surco, hueco, "cortar")
    return surco


def _caras_cilindricas(cuerpo):
    return [c for c in geo.caras(cuerpo) if BRepAdaptor_Surface(c).GetType() == GeomAbs_Cylinder]


def _radio_cilindro(cara):
    return BRepAdaptor_Surface(cara).Cylinder().Radius()


def rosca(cuerpo, cara=None, *, designacion=None, longitud=None, desfase=0.0, modelada=True, mano="derecha",
          interna=None, invertir=False):
    """Rosca (Thread) de Fusion [GUID-7BD8CD24…, GUID-C37E8172…] sobre una cara cilíndrica del cuerpo.

    `cara=None`: la cara cilíndrica que mejor calza con la designación (o la de mayor área).
    `designacion=None`: tamaño métrico automático según el diámetro de la cara, como Fusion. `longitud=None`
    = largo completo; `desfase` corre el inicio desde el extremo inferior del eje de la cara (el superior con
    `invertir`). `interna=None` detecta si la cara es un agujero. `modelada=False` = rosca cosmética (la
    geometría no cambia). Devuelve el cuerpo roscado."""
    if cara is None:
        candidatas = _caras_cilindricas(cuerpo)
        if not candidatas:
            raise geo.ErrorGeometria("El cuerpo no tiene caras cilíndricas para roscar.")
        if designacion:
            dat = datos_rosca(designacion)
            cara = min(candidatas, key=lambda c: min(abs(2 * _radio_cilindro(c) - dat["diametro"]),
                                                     abs(2 * _radio_cilindro(c) - dat["diametro_menor"])))
        else:
            cara = max(candidatas, key=geo.area)
    cara = TopoDS.Face(cara)
    sup = BRepAdaptor_Surface(cara)
    if sup.GetType() != GeomAbs_Cylinder:
        raise geo.ErrorGeometria("La rosca se aplica a una cara cilíndrica.")
    radio = _radio_cilindro(cara)
    eje = sup.Cylinder().Axis()
    o, z = _xyz(eje.Location()), _xyz(eje.Direction())
    p, nrm = _normal_orientada(cara, (sup.FirstUParameter() + sup.LastUParameter()) / 2,
                               (sup.FirstVParameter() + sup.LastVParameter()) / 2)
    es_interna = (float(nrm @ (p - o - z * float((p - o) @ z))) < 0) if interna is None else bool(interna)
    if designacion:
        datos = datos_rosca(designacion)
    else:
        clave_diam = "diametro_menor" if es_interna else "diametro"
        datos = min((datos_rosca(k) for k in TABLA_ROSCAS if k.startswith("M")),
                    key=lambda dt: (round(abs(2 * radio - dt[clave_diam]), 6), dt["norma"] != "ISO métrica gruesa"))
    alturas = []           # tramo axial de la cara: se proyectan puntos de sus aristas sobre el eje
    for e in _aristas_de(cara):
        curva = BRepAdaptor_Curve(e)
        a, b = curva.FirstParameter(), curva.LastParameter()
        alturas += [float((_xyz(curva.Value(a + (b - a) * k / 8)) - o) @ z) for k in range(9)]
    zmin, zmax = min(alturas), max(alturas)
    largo = (zmax - zmin - desfase) if longitud is None else float(longitud)
    if largo <= 1e-6 or desfase < 0 or desfase + largo > zmax - zmin + 1e-6:
        raise geo.ErrorGeometria("La longitud y el desfase de la rosca no entran en la cara.")
    if not modelada:
        return cuerpo
    z0 = zmax - desfase - largo if invertir else zmin + desfase
    surco = _surco_rosca(o, z, datos["diametro"], datos["paso"], z0, largo, es_interna, mano, radio)
    return _validar(_cortar_helicoidal(cuerpo, surco), "Rosca")


def _cortar_helicoidal(cuerpo, herramienta):
    """Corte con una herramienta helicoidal. El corte exacto a veces no hace nada sin avisar (las caras del
    surco rozan el cilindro del agujero: pasó con M10 y M20 interiores); con tolerancia difusa sale bien."""
    v0 = geo.volumen(cuerpo)
    for difuso in (0.0, 1e-5, 1e-4):
        op = BRepAlgoAPI_Cut()
        args, herr = List_TopoDS_Shape(), List_TopoDS_Shape()
        args.Append(cuerpo)
        herr.Append(herramienta)
        op.SetArguments(args)
        op.SetTools(herr)
        if difuso:
            op.SetFuzzyValue(difuso)
        op.Build()
        if op.IsDone() and geo.es_valida(op.Shape()) and geo.volumen(op.Shape()) < v0 * (1 - 1e-7):
            return op.Shape()
    raise geo.ErrorGeometria("El kernel no pudo cortar la rosca en el cuerpo.")


# ================================================================ 9. bobina
def _seccion_bobina(seccion, tamano):
    """Puntos (radial, axial) de la sección inscrita en un círculo de diámetro `tamano` (None = círculo)."""
    r = tamano / 2
    if seccion == "circular":
        return None
    if seccion == "cuadrada":
        a = r / math.sqrt(2)
        return [(-a, -a), (a, -a), (a, a), (-a, a)]
    if seccion == "triangular_externa":
        return [(r, 0.0), (-r / 2, r * math.sqrt(3) / 2), (-r / 2, -r * math.sqrt(3) / 2)]
    if seccion == "triangular_interna":
        return [(-r, 0.0), (r / 2, -r * math.sqrt(3) / 2), (r / 2, r * math.sqrt(3) / 2)]
    raise geo.ErrorGeometria(f"Sección de bobina desconocida: {seccion}")


def bobina(base_punto, eje, *, diametro, revoluciones=None, altura=None, paso=None, angulo=0.0,
           seccion="circular", tamano_seccion, posicion_seccion="sobre", horario=False, eje_x=None):
    """Bobina (Coil) de Fusion [SLD-COIL-SOLID, SLD-REF-COIL]: hélice de `diametro` con base en `base_punto`.
    Se dan dos de `revoluciones`, `altura` y `paso` (la altura va del centro de la sección inicial al de la
    final). `angulo` = inclinación (positivo = el radio crece con la altura). Sección "circular", "cuadrada",
    "triangular_externa" o "triangular_interna" de tamaño = diámetro del círculo circunscrito, ubicada
    "dentro", "sobre" o "fuera" del diámetro. `horario` invierte el giro."""
    if sum(v is not None for v in (revoluciones, altura, paso)) != 2:
        raise geo.ErrorGeometria("Dá exactamente dos de: revoluciones, altura y paso.")
    if revoluciones is None:
        revoluciones = altura / paso
    elif altura is None:
        altura = revoluciones * paso
    else:
        paso = altura / revoluciones
    if diametro <= 0 or tamano_seccion <= 0 or revoluciones <= 0 or altura <= 0:
        raise geo.ErrorGeometria("Diámetro, sección, revoluciones y altura deben ser positivos.")
    z = _unit(eje, "eje de la bobina")
    x = _perpendicular(z) if eje_x is None else _unit(np.asarray(eje_x, float) - z * float(np.asarray(eje_x) @ z))
    o = np.asarray(base_punto, float)
    pts = _seccion_bobina(seccion, tamano_seccion)
    radiales = [-tamano_seccion / 2, tamano_seccion / 2] if pts is None else [q[0] for q in pts]
    axiales = [-tamano_seccion / 2, tamano_seccion / 2] if pts is None else [q[1] for q in pts]
    r_c = {"dentro": diametro / 2 - max(radiales), "sobre": diametro / 2,
           "fuera": diametro / 2 - min(radiales)}.get(posicion_seccion)
    if r_c is None:
        raise geo.ErrorGeometria(f"Posición de sección desconocida: {posicion_seccion}")
    if r_c + min(radiales) <= 0:
        raise geo.ErrorGeometria("La sección no entra: cruza el eje de la bobina.")
    if paso <= max(axiales) - min(axiales) + 1e-6:
        raise geo.ErrorGeometria("El paso es menor que la sección: las espiras se superpondrían.")
    centro = o + x * r_c
    if pts is None:
        perfil = BRepBuilderAPI_MakeWire(BRepBuilderAPI_MakeEdge(
            gp_Circ(gp_Ax2(_pnt(centro), _gdir(np.cross(z, x))), tamano_seccion / 2)).Edge()).Wire()
    else:
        perfil = _poligono([centro + x * a + z * b for a, b in pts])
    helice = _helice(o, z, x, r_c, paso, altura, "izquierda" if horario else "derecha", angulo)
    return _validar(_barrido_helicoidal(perfil, helice), "Bobina")


# ================================================================ 10. tubería
def _seccion_tuberia(seccion, centro, u, v, radio):
    if seccion == "circular":
        return BRepBuilderAPI_MakeWire(BRepBuilderAPI_MakeEdge(
            gp_Circ(gp_Ax2(_pnt(centro), _gdir(np.cross(u, v)), _gdir(u)), radio)).Edge()).Wire()
    lados = {"cuadrada": 4, "triangular": 3}.get(seccion)
    if lados is None:
        raise geo.ErrorGeometria(f"Sección de tubería desconocida: {seccion}")
    giro = math.pi / 4 if lados == 4 else math.pi / 2
    return _poligono([centro + radio * (math.cos(giro + 2 * math.pi * k / lados) * u
                                        + math.sin(giro + 2 * math.pi * k / lados) * v) for k in range(lados)])


def tuberia(ruta, *, seccion="circular", tamano, hueca=False, espesor=0.0, distancia=1.0):
    """Tubería (Pipe) de Fusion [SLD-PIPE-SOLID]: sección "circular", "cuadrada" o "triangular" de tamaño =
    diámetro del círculo circunscrito, barrida por la ruta (fracción `distancia`). `hueca` con `espesor` de
    pared (paredes paralelas a las exteriores)."""
    w = _recortar_alambre(_alambre(ruta), float(distancia))
    if tamano <= 0:
        raise geo.ErrorGeometria("El tamaño de la sección debe ser positivo.")
    p0, t0 = _punto_en(w, 0.0)
    u = _perpendicular(t0)
    v = np.cross(t0, u)
    radio = tamano / 2
    args = (w, None, "perpendicular", 0.0, 0.0, "escalar", True, 1.0)
    forma = _barrido_alambre(_seccion_tuberia(seccion, p0, u, v, radio), *args)
    if hueca:
        lados = {"circular": None, "cuadrada": 4, "triangular": 3}[seccion]
        interior = radio - espesor / (1.0 if lados is None else math.cos(math.pi / lados))
        if espesor <= 0 or interior <= 1e-6:
            raise geo.ErrorGeometria("El espesor de la tubería hueca debe ser positivo y menor que la sección.")
        forma = geo.booleano(forma, _barrido_alambre(_seccion_tuberia(seccion, p0, u, v, interior), *args), "cortar")
    return _validar(forma, "Tubería")


# ================================================================ 11. patrones y simetría
def _indices(n, simetrico):
    if int(n) < 1:
        raise geo.ErrorGeometria("La cantidad del patrón debe ser al menos 1.")
    n = int(n)
    return list(range(-(n - 1), n)) if simetrico else list(range(n))


def _paso(n, distancia, distribucion):
    if distribucion == "extension":
        return distancia / (n - 1) if n > 1 else 0.0
    if distribucion == "espaciado":
        return distancia
    raise geo.ErrorGeometria(f"Distribución desconocida: {distribucion}")


def _traslacion(v):
    t = gp_Trsf()
    t.SetTranslation(_gvec(v))
    return t


def transformaciones_rectangulares(dir1, n1, d1, dir2=None, n2=1, d2=0.0, *, distribucion="extension",
                                   simetrico1=False, simetrico2=False, suprimir=()):
    """Patrón rectangular [SLD-REF-PATTERN]: lista de gp_Trsf en orden (i, j) — i por dir1, j por dir2 —
    que incluye la identidad (0, 0) = el original. "extension": d = largo total por dirección; "espaciado":
    d = paso. Simétrico: la misma cantidad hacia los dos lados (2n − 1). `suprimir` = pares (i, j) o índices
    i a omitir (el original no se suprime)."""
    u1 = _unit(dir1, "dirección 1")
    u2 = _unit(dir2, "dirección 2") if dir2 is not None else np.zeros(3)
    s1 = _paso(int(n1), d1, distribucion)
    s2 = _paso(int(n2), d2, distribucion) if dir2 is not None else 0.0
    fuera = {tuple(s) if isinstance(s, (tuple, list)) else (int(s), 0) for s in suprimir} - {(0, 0)}
    js = _indices(n2, simetrico2) if dir2 is not None else [0]
    return [_traslacion(i * s1 * u1 + j * s2 * u2) for i in _indices(n1, simetrico1) for j in js
            if (i, j) not in fuera]


def transformaciones_circulares(punto, eje, n, *, angulo_total=360.0, distribucion="completa", simetrico=False,
                                suprimir=()):
    """Patrón circular [SLD-REF-PATTERN]: lista de gp_Trsf (índice 0 = identidad). "completa": las instancias
    reparten `angulo_total` (con 360° la última no se superpone con el original); "espaciado":
    `angulo_total` es el ángulo entre instancias. Simétrico: n hacia cada lado del original."""
    n = int(n)
    if distribucion == "completa":
        if abs(abs(angulo_total) - 360.0) < 1e-9 and not simetrico:
            paso = angulo_total / n
        else:
            paso = angulo_total / (n - 1) if n > 1 else 0.0
    elif distribucion == "espaciado":
        paso = angulo_total
    else:
        raise geo.ErrorGeometria(f"Distribución desconocida: {distribucion}")
    ax = gp_Ax1(_pnt(punto), _gdir(_unit(eje, "eje del patrón")))
    fuera = set(suprimir) - {0}
    salida = []
    for k in _indices(n, simetrico):
        if k in fuera:
            continue
        t = gp_Trsf()
        t.SetRotation(ax, math.radians(k * paso))
        salida.append(t)
    return salida


def _trsf_de_marcos(p0, f0, p1, f1):
    """gp_Trsf que lleva el marco ortonormal f0 (columnas) ubicado en p0 al marco f1 ubicado en p1."""
    m = f1 @ f0.T
    tr = np.asarray(p1, float) - m @ np.asarray(p0, float)
    t = gp_Trsf()
    t.SetValues(*(float(c) for fila in np.hstack([m, tr[:, None]]) for c in fila))
    return t


def transformaciones_en_ruta(ruta, n, distancia, *, orientacion="identica", inicio=0.0, distribucion="extension",
                             simetrico=False, suprimir=()):
    """Patrón sobre ruta [SLD-REF-PATTERN]: el original está en la fracción `inicio` (0..1) de la ruta y las
    instancias avanzan `distancia` mm (largo total o paso, según `distribucion`). "identica" solo traslada;
    "direccion_ruta" además gira cada instancia con la ruta (marco de rotación mínima). En rutas abiertas se
    omiten las instancias que caen fuera; en las cerradas se da la vuelta."""
    if orientacion not in ("identica", "direccion_ruta"):
        raise geo.ErrorGeometria(f"Orientación desconocida: {orientacion}")
    w = _alambre(ruta)
    largo = _longitud(w)
    cerrada = _es_cerrado(w)
    paso = _paso(int(n), distancia, distribucion)
    if cerrada and distribucion == "extension" and abs(distancia - largo) < 1e-6 * largo:
        paso = largo / int(n)      # vuelta completa: la última instancia no cae encima del original
    marcos = _marcos(w, 257)

    def marco(s):
        p, t = _punto_en(w, s / largo)
        r = marcos[int(round(s / largo * (len(marcos) - 1)))][2]
        r = _unit(r - t * float(r @ t))
        return p, np.column_stack([t, r, np.cross(t, r)])

    s0 = min(max(float(inicio), 0.0), 1.0) * largo
    p0, f0 = marco(s0)
    fuera = set(suprimir) - {0}
    salida = []
    for k in _indices(n, simetrico):
        s = s0 + k * paso
        if k in fuera:
            continue
        if cerrada:
            s %= largo
        elif s < -1e-9 or s > largo + 1e-9:
            continue
        p1, f1 = marco(min(max(s, 0.0), largo))
        salida.append(_traslacion(p1 - p0) if orientacion == "identica" else _trsf_de_marcos(p0, f0, p1, f1))
    return salida


def aplicar(forma, trsf):
    """Aplica una gp_Trsf (o una matriz 4x4) a una forma y devuelve la copia transformada."""
    if not isinstance(trsf, gp_Trsf):
        m = np.asarray(trsf, float)
        trsf = gp_Trsf()
        trsf.SetValues(*(float(c) for fila in m[:3, :4] for c in fila))
    return _tipado(BRepBuilderAPI_Transform(forma, trsf, True).Shape())


def a_matriz(trsf):
    """gp_Trsf → matriz 4x4 de numpy (para guardar el patrón en el documento)."""
    m = np.eye(4)
    for i in range(3):
        for j in range(4):
            m[i, j] = trsf.Value(i + 1, j + 1)
    return m


def simetria(forma, plano):
    """Simetría (Mirror) de Fusion [SLD-REF-MIRROR-DIALOG]: copia reflejada respecto de un geo.Plano."""
    t = gp_Trsf()
    t.SetMirror(gp_Ax2(_pnt(plano.origen), _gdir(plano.normal)))
    return aplicar(forma, t)


# ================================================================ 12. engrosar
def engrosar(caras_o_cascaron, espesor, *, direccion="un_lado"):
    """Engrosar (Thicken) de Fusion [GUID-471827A2…]: sólido a partir de caras o una cáscara. "un_lado":
    espesor positivo hacia la normal de las caras, negativo hacia atrás; "simetrica": mitad a cada lado."""
    caras = _caras_de(caras_o_cascaron)
    if not caras:
        raise geo.ErrorGeometria("Elegí al menos una cara para engrosar.")
    if abs(espesor) < 1e-9:
        raise geo.ErrorGeometria("El espesor no puede ser cero.")
    if len(caras) == 1:
        lamina = caras[0]
    else:
        cosido = BRepBuilderAPI_Sewing(1e-6)
        for c in caras:
            cosido.Add(c)
        cosido.Perform()
        lamina = cosido.SewedShape()
    if direccion == "simetrica":
        mo = BRepOffsetAPI_MakeOffsetShape()
        mo.PerformByJoin(lamina, -espesor / 2, 1e-6, BRepOffset_Skin, False, False, GeomAbs_Intersection)
        if not mo.IsDone():
            raise geo.ErrorGeometria("No se pudo desfasar la superficie para el engrosado simétrico.")
        lamina = mo.Shape()
    elif direccion != "un_lado":
        raise geo.ErrorGeometria(f"Dirección de engrosado desconocida: {direccion}")
    return _validar(_engrosar_lamina(lamina, espesor), "Engrosar")


# ================================================================ 13. relleno de contorno
def relleno_contorno_celdas(herramientas, *, tamano_plano=1e3):
    """Celdas del Relleno de contorno (Boundary Fill) [GUID-575E005F…]: todos los volúmenes cerrados que
    forman las herramientas (cuerpos, caras/superficies o geo.Plano). Lista de dicts {solido, centroide,
    volumen} ordenada por centroide, para que el índice de cada celda sea estable."""
    args = List_TopoDS_Shape()
    for h in _lista(herramientas):
        args.Append(cara_de_plano(h, tamano_plano) if isinstance(h, geo.Plano) else h)
    mv = BOPAlgo_MakerVolume()
    mv.SetArguments(args)
    mv.SetIntersect(True)
    mv.Perform()
    if mv.HasErrors():
        raise geo.ErrorGeometria("No se pudieron calcular las celdas del relleno de contorno.")
    celdas = [{"solido": s, "centroide": tuple(round(c, 6) for c in geo.centro_masa(s)), "volumen": geo.volumen(s)}
              for s in geo.solidos(mv.Shape())]
    return sorted(celdas, key=lambda c: c["centroide"])


def relleno_contorno(herramientas, indices, **opciones):
    """Sólido formado por las celdas elegidas (índices de `relleno_contorno_celdas`)."""
    celdas = relleno_contorno_celdas(herramientas, **opciones)
    if not celdas:
        raise geo.ErrorGeometria("Las herramientas no encierran ningún volumen.")
    try:
        elegidas = [celdas[i]["solido"] for i in indices]
    except IndexError:
        raise geo.ErrorGeometria("Índice de celda fuera de rango.") from None
    return _validar(_unir(elegidas), "Relleno de contorno")


# ================================================================ 14. sólido envolvente
def _circulo_minimo(puntos):
    """Círculo mínimo que contiene puntos 2D (Welzl iterativo, orden aleatorio con semilla fija)."""
    pts = np.unique(np.round(np.asarray(puntos, float), 9), axis=0)
    pts = pts[np.random.default_rng(0).permutation(len(pts))]

    def circuncentro(a, b, c):
        d = 2 * (a[0] * (b[1] - c[1]) + b[0] * (c[1] - a[1]) + c[0] * (a[1] - b[1]))
        if abs(d) < 1e-12:       # alineados: el diámetro es el par más lejano
            par = max(((a, b), (a, c), (b, c)), key=lambda q: np.linalg.norm(q[0] - q[1]))
            return (par[0] + par[1]) / 2
        ux = ((a @ a) * (b[1] - c[1]) + (b @ b) * (c[1] - a[1]) + (c @ c) * (a[1] - b[1])) / d
        uy = ((a @ a) * (c[0] - b[0]) + (b @ b) * (a[0] - c[0]) + (c @ c) * (b[0] - a[0])) / d
        return np.array([ux, uy])

    c, r, eps = pts[0], 0.0, 1e-9
    for i in range(len(pts)):
        if np.linalg.norm(pts[i] - c) <= r + eps:
            continue
        c, r = pts[i], 0.0
        for j in range(i):
            if np.linalg.norm(pts[j] - c) <= r + eps:
                continue
            c = (pts[i] + pts[j]) / 2
            r = float(np.linalg.norm(pts[i] - c))
            for k in range(j):
                if np.linalg.norm(pts[k] - c) > r + eps:
                    c = circuncentro(pts[i], pts[j], pts[k])
                    r = float(np.linalg.norm(pts[i] - c))
    return c, r


def solido_envolvente(formas, *, tipo="caja", margen=0.0, eje="z"):
    """Sólido envolvente (Bounding Solid) [SLD-CREATE-BOUNDING-SOLID] alineado al modelo: "caja" (caja
    envolvente exacta) o "cilindro" alrededor de `eje` ("x", "y", "z" o vector) con el radio mínimo que
    contiene a la forma (círculo mínimo de su teselado fino). `margen` agranda en todas las direcciones."""
    comp = geo.compuesto(_lista(formas))
    bb = geo.caja_envolvente(comp)
    if bb is None:
        raise geo.ErrorGeometria("No hay geometría para envolver.")
    (x0, y0, z0), (x1, y1, z1) = bb
    if tipo == "caja":
        return geo.caja(x1 - x0 + 2 * margen, y1 - y0 + 2 * margen, z1 - z0 + 2 * margen,
                        (x0 - margen, y0 - margen, z0 - margen))
    if tipo != "cilindro":
        raise geo.ErrorGeometria(f"Tipo de sólido envolvente desconocido: {tipo}")
    ejes = {"x": (1.0, 0.0, 0.0), "y": (0.0, 1.0, 0.0), "z": (0.0, 0.0, 1.0)}
    if isinstance(eje, str) and eje not in ejes:
        raise geo.ErrorGeometria(f"Eje desconocido: {eje}")
    z = _unit(ejes[eje] if isinstance(eje, str) else eje, "eje del cilindro")
    u = _perpendicular(z)
    v = np.cross(z, u)
    verts, _ = geo.teselar(comp, deflexion=max(1e-3, 1e-4 * _diagonal(comp)), angular=0.1)
    pts = np.asarray(verts, float)
    centro2d, radio = _circulo_minimo(np.column_stack([pts @ u, pts @ v]))
    if isinstance(eje, str):
        lo, hi = _proyectar_caja(bb, (0.0, 0.0, 0.0), z)
    else:
        lo, hi = float((pts @ z).min()), float((pts @ z).max())
    base = centro2d[0] * u + centro2d[1] * v + z * (lo - margen)
    return geo.cilindro(radio + margen, hi - lo + 2 * margen, base=tuple(base), eje=tuple(z))


# ================================================================ 15. plástico (simplificado)
def saliente(cuerpo, punto, direccion, *, diametro_exterior, diametro_agujero, altura=None,
             profundidad_agujero=None, angulo_desmoldeo=0.0):
    """Saliente (Boss) de la pestaña Plástico [SLD-BOSS], versión simplificada: un solo lado, sin nervios ni
    sujetador. Columna de `diametro_exterior` que nace en `punto` y avanza según `direccion` hasta el cuerpo
    (o `altura`), con desmoldeo (más ancha en la base) y agujero piloto de `diametro_agujero` (profundidad =
    la de la columna si no se indica). Devuelve el cuerpo resultante."""
    d = _unit(direccion, "dirección del saliente")
    if diametro_agujero <= 0 or diametro_exterior <= diametro_agujero:
        raise geo.ErrorGeometria("El diámetro exterior del saliente debe superar al del agujero.")
    disco = _cara(BRepBuilderAPI_MakeWire(BRepBuilderAPI_MakeEdge(
        gp_Circ(gp_Ax2(_pnt(punto), _gdir(d)), diametro_exterior / 2)).Edge()).Wire())
    if altura is None:
        _, hi = _caja_proyectada(cuerpo, punto, d)
        if hi <= 0:
            raise geo.ErrorGeometria("El cuerpo no está en la dirección del saliente.")
        columna = _recortar_hasta(_prisma(disco, d, hi + _MARGEN, angulo_desmoldeo), [disco], cuerpo,
                                  "cuerpo", None, punto)
        if not geo.se_tocan(columna, cuerpo, 1e-4):
            raise geo.ErrorGeometria("El saliente no llega al cuerpo.")
        altura = _proyectar_caja(geo.caja_envolvente(columna), punto, d)[1]
    else:
        columna = _prisma(disco, d, altura, angulo_desmoldeo)
    resultado = _unificar(geo.booleano(cuerpo, columna, "unir"))
    hueco = herramienta_agujero(punto, d, diametro=diametro_agujero, profundidad=profundidad_agujero or altura,
                                punta="plana")
    return _validar(geo.booleano(resultado, hueco, "cortar"), "Saliente")


def labio_ranura(cuerpo, aristas, direccion_tirado, *, tipo="labio", ancho, alto, holgura=0.0):
    """Labio / ranura (Lip) de la pestaña Plástico [SLD-LIP], versión simplificada: sección rectangular barrida
    por la cadena de aristas del borde de la pared. "labio": `ancho` hacia adentro de la pared desde la arista
    y `alto` hacia `direccion_tirado` (se une); "ranura": la misma sección agrandada en `holgura`, hacia
    adentro del material (se corta). Sin desmoldeo ni reglas de plástico. Devuelve el cuerpo resultante."""
    if tipo not in ("labio", "ranura"):
        raise geo.ErrorGeometria(f"Tipo desconocido: {tipo}")
    if ancho <= 0 or alto <= 0 or holgura < 0:
        raise geo.ErrorGeometria("Ancho y alto deben ser positivos y la holgura no negativa.")
    w = _alambre(aristas)
    tirar = _unit(direccion_tirado, "dirección de tirado")
    p0, t0 = _punto_en(w, 0.0)
    m = _unit(np.cross(tirar, t0), "arista (no puede ser paralela a la dirección de tirado)")
    # De qué lado de la arista está la pared: se prueba en el medio de la primera arista (no en un vértice,
    # que suele ser una esquina sobre el borde del cuerpo).
    pm, tm = _punto_en(w, 0.5 * _longitud(_aristas_de(w)[0]) / _longitud(w))
    mm = _unit(np.cross(tirar, tm))
    eps = min(ancho, alto) * 0.25
    if BRepClass3d_SolidClassifier(cuerpo, _pnt(pm + mm * eps - tirar * eps), 1e-7).State() != TopAbs_IN:
        m = -m
    a, h = (ancho, alto) if tipo == "labio" else (ancho + holgura, -(alto + holgura))
    seccion = _poligono([p0, p0 + m * a, p0 + m * a + tirar * h, p0 + tirar * h])
    barrido = _barrido_alambre(seccion, w, None, "perpendicular", 0.0, 0.0, "escalar", True, 1.0)
    resultado = geo.booleano(cuerpo, barrido, "unir" if tipo == "labio" else "cortar")
    return _validar(_unificar(resultado), "Labio" if tipo == "labio" else "Ranura")

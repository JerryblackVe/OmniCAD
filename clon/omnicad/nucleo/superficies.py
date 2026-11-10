# -*- coding: utf-8 -*-
"""
Cuerpos de superficie: la pestaña SUPERFICIE de Fusion 360 (Design > Surface).

Un cuerpo de superficie es una cara o un cascarón ABIERTO (sin volumen). Se crean desde aristas o
alambres (extruir, revolver, barrer, solevar, parche, reglada), se modifican (recortar, destrimar,
extender, empalme/chaflán, invertir normal) y se convierten en sólidos (coser, engrosar).

Entradas de "aristas": `TopoDS_Edge`, `TopoDS_Wire`, una cara (se usan sus contornos), un compuesto
de aristas, o una lista de cualquiera de esas cosas. Las aristas sueltas que se tocan en los extremos
se encadenan solas en alambres.
"""
import math

import numpy as np
from . import motor as _motor


def _iniciar_opencascade():
    global Array1_double, Array1_gp_Pnt, BRepAdaptor_CompCurve, BRepAdaptor_Curve, BRepAdaptor_Curve2d
    global BRepAdaptor_Surface, BRepAlgoAPI_Splitter, BRepBuilderAPI_Copy, BRepBuilderAPI_MakeEdge
    global BRepBuilderAPI_FindPlane, BRepBuilderAPI_GTransform, BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakeSolid
    global BRepBuilderAPI_MakeVertex
    global BRepBuilderAPI_MakeWire, BRepBuilderAPI_RightCorner, BRepBuilderAPI_Sewing, BRepBuilderAPI_Transform
    global BRepExtrema_DistShapeShape
    global BRepClass_FaceClassifier, BRepFill, BRepFilletAPI_MakeChamfer, BRepFilletAPI_MakeFillet
    global BRepLib, BRepOffsetAPI_MakeDraft
    global BRepOffsetAPI_MakeFilling, BRepOffsetAPI_MakeOffsetShape, BRepOffsetAPI_MakePipeShell
    global BRepOffsetAPI_ThruSections, BRepOffset_MakeOffset, BRepOffset_Skin, BRepPrimAPI_MakePrism
    global BRepPrimAPI_MakeRevol, BRepTools, BRep_Tool, GCPnts_AbscissaPoint, GeomAPI_PointsToBSpline
    global GCPnts_UniformAbscissa, GeomAPI_ProjectPointOnSurf, Law_Linear
    global GeomAbs_Arc, GeomAbs_C0, GeomAbs_C1, GeomAbs_C2, GeomAbs_Cylinder, GeomAbs_G1, GeomAbs_Intersection
    global GeomAbs_Line, GeomAbs_Plane, IndexedDataMap_TopoDS_Shape_List_TopoDS_Shape_TopTools_ShapeMapHasher
    global GC_MakeCircle, List_TopoDS_Shape, ShapeAnalysis_Surface, ShapeFix_Edge, ShapeFix_Face, TopAbs_COMPOUND, TopAbs_EDGE, TopAbs_FACE, TopAbs_FORWARD
    global TopAbs_IN, TopAbs_ON, TopAbs_REVERSED, TopAbs_SHELL, TopAbs_SOLID, TopAbs_VERTEX, TopAbs_WIRE, TopExp
    global TopoDS, TopoDS_Face
    global TopoDS_Iterator, TopoDS_Shape, TopoDS_Vertex, _CAST, _CONTINUIDAD, gp_Ax1, gp_Ax2, gp_Dir, gp_Pln
    global gp_GTrsf, gp_Pnt, gp_Pnt2d, gp_Trsf, gp_Vec
    from OCP.BRep import BRep_Tool
    from OCP.BRepAdaptor import BRepAdaptor_CompCurve, BRepAdaptor_Curve, BRepAdaptor_Curve2d, BRepAdaptor_Surface
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Splitter
    from OCP.BRepBuilderAPI import (BRepBuilderAPI_Copy, BRepBuilderAPI_FindPlane, BRepBuilderAPI_GTransform,
                                    BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakeSolid,
                                    BRepBuilderAPI_MakeVertex, BRepBuilderAPI_MakeWire, BRepBuilderAPI_RightCorner,
                                    BRepBuilderAPI_Sewing, BRepBuilderAPI_Transform)
    from OCP.BRepExtrema import BRepExtrema_DistShapeShape
    from OCP.BRepClass import BRepClass_FaceClassifier
    from OCP.BRepFill import BRepFill
    from OCP.BRepFilletAPI import BRepFilletAPI_MakeChamfer, BRepFilletAPI_MakeFillet
    from OCP.BRepLib import BRepLib
    from OCP.BRepOffset import BRepOffset_MakeOffset, BRepOffset_Skin
    from OCP.BRepOffsetAPI import (BRepOffsetAPI_MakeDraft, BRepOffsetAPI_MakeFilling, BRepOffsetAPI_MakeOffsetShape,
                                   BRepOffsetAPI_MakePipeShell, BRepOffsetAPI_ThruSections)
    from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism, BRepPrimAPI_MakeRevol
    from OCP.BRepTools import BRepTools
    from OCP.GC import GC_MakeCircle
    from OCP.GCPnts import GCPnts_AbscissaPoint, GCPnts_UniformAbscissa
    from OCP.GeomAbs import (GeomAbs_Arc, GeomAbs_C0, GeomAbs_C1, GeomAbs_C2, GeomAbs_Cylinder, GeomAbs_G1,
                             GeomAbs_Intersection, GeomAbs_Line, GeomAbs_Plane)
    from OCP.GeomAPI import GeomAPI_PointsToBSpline, GeomAPI_ProjectPointOnSurf
    from OCP.Law import Law_Linear
    from OCP.OCP.collections import (Array1_double, Array1_gp_Pnt, IndexedDataMap_TopoDS_Shape_List_TopoDS_Shape_TopTools_ShapeMapHasher,
                                     List_TopoDS_Shape)
    from OCP.ShapeAnalysis import ShapeAnalysis_Surface
    from OCP.ShapeFix import ShapeFix_Edge, ShapeFix_Face
    from OCP.TopAbs import (TopAbs_COMPOUND, TopAbs_EDGE, TopAbs_FACE, TopAbs_FORWARD, TopAbs_IN, TopAbs_ON,
                            TopAbs_REVERSED, TopAbs_SHELL, TopAbs_SOLID, TopAbs_VERTEX, TopAbs_WIRE)
    from OCP.TopExp import TopExp
    from OCP.TopoDS import TopoDS, TopoDS_Face, TopoDS_Iterator, TopoDS_Shape, TopoDS_Vertex
    from OCP.gp import gp_Ax1, gp_Ax2, gp_Dir, gp_GTrsf, gp_Pln, gp_Pnt, gp_Pnt2d, gp_Trsf, gp_Vec
    _CAST = {TopAbs_COMPOUND: TopoDS.Compound, TopAbs_SOLID: TopoDS.Solid, TopAbs_SHELL: TopoDS.Shell,
             TopAbs_FACE: TopoDS.Face, TopAbs_WIRE: TopoDS.Wire, TopAbs_EDGE: TopoDS.Edge, TopAbs_VERTEX: TopoDS.Vertex}
    # BRepFill recibe la continuidad como entero 0..2 (G0, G1, G2): el valor 2 es GeomAbs_C1, no GeomAbs_G2 (3),
    # que el kernel rechaza con «The continuity is not G0 G1 or G2» (SUP-1).
    _CONTINUIDAD = {"G0": GeomAbs_C0, "G1": GeomAbs_G1, "G2": GeomAbs_C1}


if _motor.motor_activo() == "opencascade":
    _iniciar_opencascade()

from . import geometria as geo

_TOL = 1e-6        # tolerancia de costura "exacta" (piezas que ya comparten aristas)
_TOL_EXTREMO = 1e-4  # mm: dos aristas se encadenan si sus extremos están a menos de esto
# Superficies que se evalúan fuera de los límites de la cara (infinitas o periódicas); el resto hay que prolongarlo.
_SUPERFICIES_SIN_LIMITE = {"Geom_Plane", "Geom_CylindricalSurface", "Geom_ConicalSurface", "Geom_SphericalSurface",
                           "Geom_ToroidalSurface"}



# ---------------------------------------------------------------- utilidades
def _tipado(forma):
    """Devuelve la forma con su clase concreta (TopoDS_Face, TopoDS_Shell…). Una forma nula es un error: el kernel a
    veces da IsDone y una forma nula (desfase de una caja de 10 mm de alto, 6 mm hacia adentro) y `ShapeType()` sobre
    ella tiraba la app entera (fallo de segmentación)."""
    if forma is None or forma.IsNull():
        raise geo.ErrorGeometria("El kernel no devolvió ninguna forma con estos valores.")
    return _CAST.get(forma.ShapeType(), lambda s: s)(forma)


def _simplificar(forma):
    """Un compuesto con un único hijo se reemplaza por ese hijo."""
    forma = _tipado(forma)
    if forma.ShapeType() == TopAbs_COMPOUND:
        hijos = []
        it = TopoDS_Iterator(forma)
        while it.More():
            hijos.append(it.Value())
            it.Next()
        if len(hijos) == 1:
            return _simplificar(hijos[0])
    return forma


def _juntar(formas):
    formas = [f for f in formas if f is not None]
    if not formas:
        raise geo.ErrorGeometria("La operación no produjo geometría.")
    return _tipado(formas[0]) if len(formas) == 1 else geo.compuesto(formas)


def _coser_caras(caras, tolerancia=_TOL):
    """Une caras en un cascarón (cara suelta si es una sola; compuesto si quedan separadas)."""
    caras = list(caras)
    if len(caras) == 1:
        return _tipado(caras[0])
    cos = BRepBuilderAPI_Sewing(tolerancia)
    for c in caras:
        cos.Add(c)
    cos.Perform()
    return _simplificar(cos.SewedShape())


def _formas(entrada):
    if isinstance(entrada, TopoDS_Shape):
        return [entrada]
    salida = []
    for x in entrada:
        salida.extend(_formas(x))
    return salida


def _pnt(p):
    return gp_Pnt(*map(float, p))


def _np(p):
    return np.array([p.X(), p.Y(), p.Z()], float)


def _unitario(v, que="La dirección"):
    v = np.asarray(v, float)
    n = np.linalg.norm(v)
    if n < 1e-12:
        raise geo.ErrorGeometria(f"{que} no puede ser nula.")
    return v / n


def _extremos(arista):
    a, b = TopExp.FirstVertex_s(arista), TopExp.LastVertex_s(arista)
    return _np(BRep_Tool.Pnt_s(a)), _np(BRep_Tool.Pnt_s(b))


def alambres(entrada):
    """Convierte aristas/alambres/caras en una lista de alambres; las aristas sueltas que se tocan en
    los extremos se encadenan (Fusion lo llama "encadenar" — Chaining)."""
    salida, sueltas = [], []
    pila = _formas(entrada)
    while pila:
        s = pila.pop(0)
        t = s.ShapeType()
        if t == TopAbs_WIRE:
            salida.append(TopoDS.Wire(s))
        elif t == TopAbs_EDGE:
            sueltas.append(TopoDS.Edge(s))
        elif t == TopAbs_FACE:
            salida.extend(TopoDS.Wire(w) for w in geo._explorar(s, TopAbs_WIRE))
        elif t == TopAbs_COMPOUND:
            it = TopoDS_Iterator(s)
            while it.More():
                pila.append(it.Value())
                it.Next()
        else:
            raise geo.ErrorGeometria("Se esperaban aristas, alambres o caras.")
    # Agrupa las aristas sueltas por contacto de extremos (unión-búsqueda) y arma un alambre por grupo.
    padre = list(range(len(sueltas)))

    def raiz(i):
        while padre[i] != i:
            padre[i] = padre[padre[i]]
            i = padre[i]
        return i

    ext = [_extremos(e) for e in sueltas]
    for i in range(len(sueltas)):
        for j in range(i + 1, len(sueltas)):
            if min(np.linalg.norm(p - q) for p in ext[i] for q in ext[j]) < _TOL_EXTREMO:
                padre[raiz(i)] = raiz(j)
    grupos = {}
    for i, e in enumerate(sueltas):
        grupos.setdefault(raiz(i), []).append(e)
    for grupo in grupos.values():
        lista = List_TopoDS_Shape()
        for e in grupo:
            lista.Append(e)
        mw = BRepBuilderAPI_MakeWire()
        mw.Add(lista)
        if not mw.IsDone():
            raise geo.ErrorGeometria("No se pudieron encadenar las aristas en un alambre.")
        salida.append(mw.Wire())
    if not salida:
        raise geo.ErrorGeometria("No hay aristas para operar.")
    return salida


def _alambre_unico(entrada, que):
    ws = alambres(entrada)
    if len(ws) != 1:
        raise geo.ErrorGeometria(f"{que} tiene que ser una sola cadena de aristas conectadas (hay {len(ws)}).")
    return ws[0]


def _mapa_aristas(forma):
    m = IndexedDataMap_TopoDS_Shape_List_TopoDS_Shape_TopTools_ShapeMapHasher()
    TopExp.MapShapesAndAncestors_s(forma, TopAbs_EDGE, TopAbs_FACE, m)
    return m


def _caras_de(mapa, arista):
    if not mapa.Contains(arista):
        return []
    return [TopoDS.Face(f) for f in geo.lista_occ(mapa.FindFromKey(arista))]


def _orientacion_en(cara, arista):
    """Orientación de la arista dentro de la cara (tomada como FORWARD)."""
    for e in geo._explorar(cara.Oriented(TopAbs_FORWARD), TopAbs_EDGE):
        if e.IsSame(arista):
            return e.Orientation()
    raise geo.ErrorGeometria("La arista no pertenece a la cara.")


def _cara_plana_grande(plano, tam):
    pln = gp_Pln(_pnt(plano.origen), gp_Dir(*map(float, plano.normal)))
    return BRepBuilderAPI_MakeFace(pln, -tam, tam, -tam, tam).Face()


def _tam_referencia(forma):
    cj = geo.caja_envolvente(forma)
    if cj is None:
        return 1e3
    (x0, y0, z0), (x1, y1, z1) = cj
    centro = np.array([(x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2])
    return 4.0 * (math.dist((x0, y0, z0), (x1, y1, z1)) + float(np.linalg.norm(centro))) + 100.0


# ---------------------------------------------------------------- crear
LADOS_EXTRUSION = ("un_lado", "dos_lados", "simetrica")


def _rango_sobre(caja, origen, n):
    """(mínimo, máximo) de la caja `((x0, y0, z0), (x1, y1, z1))` medida desde `origen` a lo largo de `n`."""
    (x0, y0, z0), (x1, y1, z1) = caja
    esquinas = np.array([(x, y, z) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)], float)
    t = (esquinas - origen) @ n
    return float(t.min()), float(t.max())


def _altos(lados, distancia, distancia2, medida):
    """(alto hacia +n, alto hacia -n) de una extrusión por distancias. Un lado: el signo da el sentido."""
    if lados not in LADOS_EXTRUSION:
        raise geo.ErrorGeometria(f"Dirección de extrusión desconocida: {lados}")
    geo.exigir_longitud(distancia, "La distancia de extrusión")
    if lados == "un_lado":
        return (distancia, 0.0) if distancia > 0 else (0.0, -distancia)
    if lados == "dos_lados":
        geo.exigir_longitud(distancia2 if distancia2 is not None else 0.0, "La distancia del lado 2")
        return abs(distancia), abs(distancia2)
    if medida not in ("mitad", "total"):
        raise geo.ErrorGeometria(f"Medida simétrica desconocida: {medida}")
    h = abs(distancia) / 2 if medida == "total" else abs(distancia)
    return h, h


def _hacia_afuera(pieza, n):
    """SUP-23 (Fusion real): el tubo de un contorno cerrado tiene la normal hacia afuera. El lateral encierra área:
    por el teorema de la divergencia, ∑ (p − c)·normal dA medido a lo ancho de `n` es positivo si apunta afuera."""
    tris = np.concatenate([t for _, t in geo.teselar_por_cara(pieza)])
    relativos = tris.mean(axis=1) - tris.reshape(-1, 3).mean(axis=0)
    a_lo_ancho = relativos - np.outer(relativos @ n, n)
    areas = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    return pieza if float(np.sum(a_lo_ancho * areas)) >= 0 else _tipado(pieza.Reversed())


def _extruir_tramos(ws, n, arriba, abajo, conicidad, afuera=False):
    """Extrusión de los alambres `arriba` hacia +n y `abajo` hacia -n (superficies sin coser entre sí si no hay
    conicidad: un solo prisma que atraviesa la base). `afuera`: ver `_hacia_afuera`."""
    piezas = []
    for w in ws:
        if abs(conicidad) < 1e-9:
            if arriba == 0:       # solo hacia -n: se extruye hacia abajo (la normal de siempre con distancia negativa)
                piezas.append(BRepPrimAPI_MakePrism(w, gp_Vec(*map(float, -n * abajo))).Shape())
                continue
            base = geo.trasladar(w, -n * abajo) if abajo else w
            piezas.append(BRepPrimAPI_MakePrism(base, gp_Vec(*map(float, n * (arriba + abajo)))).Shape())
            continue
        caras = []
        cara = plano = None
        if BRep_Tool.IsClosed_s(w):
            mk = BRepBuilderAPI_MakeFace(w, True)
            if mk.IsDone():
                candidata = mk.Face()
                plano = geo.plano_de_cara(candidata)
                if plano is not None and 1e-9 < abs(float(plano.normal @ n)) < 1 - 1e-9:
                    cara = candidata
        for d, alto in ((n, arriba), (-n, abajo)):
            if alto <= 0:
                continue
            if cara is not None:
                # Inicio oblicuo: compartir los planos límite y el lateral con Extruir sólido.
                from .solidos_crear import _prisma
                forma = _prisma(cara, d, alto, conicidad)
                caras.extend(c for c in geo.caras(forma) if (p := geo.plano_de_cara(c)) is None
                             or abs(float(p.normal @ plano.normal)) < 1 - 1e-9)
                continue
            ang = math.radians(abs(conicidad))
            try:
                dr = BRepOffsetAPI_MakeDraft(w, gp_Dir(*map(float, d)), ang)
                dr.SetDraft(conicidad < 0)   # "interno" = hacia adentro del contorno
                dr.Perform(alto / math.cos(ang))
                hecho = dr.IsDone()
            except Exception:  # noqa: BLE001 — OCC lanza gp_VectorWithNullMagnitude, sin texto, con algunas rectas
                hecho = False
            if hecho:
                caras.extend(geo.caras(dr.Shape()))
            elif (t := _direccion_recta(w)) is not None:
                caras.extend(geo.caras(_prisma_inclinado(w, t, d, alto, conicidad)))
            else:
                raise geo.ErrorGeometria("No se pudo crear la extrusión de superficie con conicidad con estas curvas: "
                                         "probá con conicidad 0.")
        piezas.append(_coser_caras(caras))
    if afuera:
        piezas = [_hacia_afuera(p, n) if BRep_Tool.IsClosed_s(w) else p for p, w in zip(piezas, ws, strict=True)]
    return _simplificar(_juntar(piezas))


def extruir_superficie(aristas_o_alambre, direccion, distancia, *, simetrica=False, conicidad=0.0, lados=None,
                       distancia2=None, medida="total", desfase_inicio=0.0, hasta=None, hasta_desfase=0.0,
                       caja=None, afuera=False):
    """Extrusión de curvas en superficie [SFC-EXTRUDE]. Distancia negativa = sentido contrario.

    `lados`: "un_lado" (por defecto), "dos_lados" (`distancia` hacia +dirección y `distancia2` hacia -dirección) o
    "simetrica" (`medida` "total": la distancia es la longitud total; "mitad": es la de cada lado). `simetrica=True`
    equivale a lados="simetrica" con medida "total". `desfase_inicio`: la extrusión parte de las curvas movidas esa
    distancia según `direccion` (Start = Offset Plane / From Object).
    `conicidad` (grados, Taper Angle): positivo abre la superficie hacia afuera de un contorno cerrado,
    negativo la cierra; en una curva abierta, positivo inclina hacia la derecha del recorrido mirando
    desde `direccion`. La altura medida sobre `direccion` es siempre `distancia`.
    Extensión «A objeto» (Extent = To Object): `hasta` (superficie, `geo.Plano` o cuerpo) corta el lado 1, que va
    hasta el objeto movido `hasta_desfase`. «Todo» (Extent = All): `caja` = caja envolvente de los cuerpos.
    `afuera=True`: un contorno cerrado da un tubo con la normal hacia afuera, como Fusion; `False`, el lado que da el
    sentido del recorrido (las recetas viejas)."""
    if abs(conicidad) > 89.0:
        raise geo.ErrorGeometria("La conicidad tiene que estar entre -89° y 89°.")
    n = _unitario(direccion)
    lados = lados or ("simetrica" if simetrica else "un_lado")
    ws = alambres(aristas_o_alambre)
    if desfase_inicio:
        ws = [geo.trasladar(w, n * float(desfase_inicio)) for w in ws]
    if hasta is None and caja is None:
        return _extruir_tramos(ws, n, *_altos(lados, distancia, distancia2, medida), conicidad, afuera)
    if lados not in LADOS_EXTRUSION:
        raise geo.ErrorGeometria(f"Dirección de extrusión desconocida: {lados}")
    reunidas = _juntar(ws)
    origen = np.mean([_extremos(TopoDS.Edge(e))[0] for e in geo._explorar(reunidas, TopAbs_EDGE)], axis=0)
    if caja is not None:                                  # extensión «Todo»
        lo, hi = _rango_sobre(caja, origen, n)
        margen = 1.0 + 0.05 * (hi - lo)
        if lados == "un_lado":
            alto = (hi if distancia >= 0 else -lo) + margen
            if alto <= margen:
                raise geo.ErrorGeometria("No hay cuerpos en el sentido de la extrusión.")
            return _extruir_tramos(ws, n, *((alto, 0.0) if distancia >= 0 else (0.0, alto)), conicidad, afuera)
        return _extruir_tramos(ws, n, max(hi, 0.0) + margen, max(-lo, 0.0) + margen, conicidad, afuera)
    if lados == "simetrica":
        raise geo.ErrorGeometria("La extensión «A objeto» no se combina con la dirección simétrica.")
    tool = _herramienta(hasta, reunidas)
    signo = 1.0
    lo, hi = _rango_sobre(geo.caja_envolvente(tool), origen, n)
    if distancia < 0 or (hi <= 0 < -lo):
        signo = -1.0
    if hasta_desfase:
        tool = geo.trasladar(tool, n * signo * float(hasta_desfase))
        lo, hi = _rango_sobre(geo.caja_envolvente(tool), origen, n)
    alcance = (hi if signo > 0 else -lo) + 1.0 + 0.05 * (hi - lo)
    if alcance <= 1.0:
        raise geo.ErrorGeometria("El objeto está del otro lado de las curvas: invertí la distancia o elegí otro.")
    larga = _extruir_tramos(ws, n, *((alcance, 0.0) if signo > 0 else (0.0, alcance)), conicidad, afuera)
    regiones = regiones_recorte(larga, tool)
    toca = [r for r in regiones if BRepExtrema_DistShapeShape(r, reunidas).Value() < 1e-5]
    if len(regiones) < 2 or not toca:
        raise geo.ErrorGeometria("La extrusión no llega al objeto elegido: no lo corta.")
    caras = [c for r in toca for c in geo.caras(r)]
    if lados == "dos_lados":
        otro = _extruir_tramos(ws, n, *((0.0, abs(distancia2)) if signo > 0 else (abs(distancia2), 0.0)), conicidad)
        caras += geo.caras(otro)
    return _coser_caras(caras)


def _direccion_recta(alambre):
    """Dirección unitaria del alambre (de su primer vértice al último) si es un tramo recto: aristas rectas y
    alineadas. None si no lo es (o si es cerrado)."""
    v1, v2 = TopoDS_Vertex(), TopoDS_Vertex()
    TopExp.Vertices_s(alambre, v1, v2)
    if v1.IsNull() or v2.IsNull():
        return None
    a, b = _np(BRep_Tool.Pnt_s(v1)), _np(BRep_Tool.Pnt_s(v2))
    largo = float(np.linalg.norm(b - a))
    if largo < _TOL:
        return None
    t = (b - a) / largo
    for e in geo._explorar(alambre, TopAbs_EDGE):
        e = TopoDS.Edge(e)
        if BRepAdaptor_Curve(e).GetType() != GeomAbs_Line or \
                any(np.linalg.norm(np.cross(p - a, t)) > _TOL for p in _extremos(e)):
            return None
    return t


def _prisma_inclinado(alambre, t, d, alto, conicidad):
    """Superficie de un tramo recto (dirección `t`) extruido `alto` según `d` e inclinado `conicidad` grados hacia
    t × d (la derecha del recorrido mirando desde `d`): la misma cara plana que da MakeDraft cuando la resuelve."""
    lateral = np.cross(t, d)
    if np.linalg.norm(lateral) < 1e-9:
        raise geo.ErrorGeometria("La curva es paralela a la dirección de extrusión: no se puede extruir.")
    v = (np.asarray(d, float) + lateral * math.tan(math.radians(conicidad))) * alto
    return BRepPrimAPI_MakePrism(alambre, gp_Vec(*map(float, v))).Shape()


def _revolver_hasta(ws, punto, d, objeto):
    """Revolución «A objeto» [SFC-REVOLVE]: gira hasta un vértice (`("punto", xyz)`), un plano o cara plana
    (`("plano", geo.Plano)`) o un cuerpo (`("forma", forma)`, primer contacto por bisección)."""
    tipo, dato = objeto
    if tipo in ("punto", "plano"):
        from . import solidos_crear
        return solidos_crear.revolver_hasta(ws, punto, d, objeto)
    if tipo != "forma":
        raise geo.ErrorGeometria(f"Objeto de revolución desconocido: {tipo}")
    eje = gp_Ax1(_pnt(punto), gp_Dir(*map(float, d)))

    def girado(grados):
        return _juntar([BRepPrimAPI_MakeRevol(w, eje, math.radians(grados)).Shape() for w in ws])

    def toca(grados):
        medida = BRepExtrema_DistShapeShape(girado(grados), dato)
        return medida.IsDone() and medida.Value() < 1e-6

    if not toca(360.0):
        raise geo.ErrorGeometria("El perfil, al girar, no llega a ese cuerpo.")
    bajo, alto = 0.0, 360.0
    for _ in range(25):
        medio = (bajo + alto) / 2
        bajo, alto = (bajo, medio) if toca(medio) else (medio, alto)
    if alto < 1e-5:
        raise geo.ErrorGeometria("El cuerpo ya toca el perfil: elegí uno que esté a un ángulo.")
    return _simplificar(girado(alto))


def revolver_superficie(aristas, punto_eje, dir_eje, angulo, *, direccion="un_lado", angulo2=None, hasta=None):
    """Revolución de curvas en superficie [SFC-REVOLVE] (Partial; ±360 = Full).

    `direccion`: "un_lado" (`angulo` con signo), "dos_lados" (`angulo` hacia un lado y `angulo2` hacia el otro) o
    "simetrica" (`angulo` es el total, mitad para cada lado). `hasta`: Extent = To Object, `("punto", xyz)`,
    `("plano", geo.Plano)` o `("forma", cuerpo)`; gira hacia un solo lado."""
    if direccion not in LADOS_EXTRUSION:
        raise geo.ErrorGeometria(f"Dirección de revolución desconocida: {direccion}")
    d = _unitario(dir_eje, "La dirección del eje")
    ws = alambres(aristas)
    if hasta is not None:
        if direccion != "un_lado":
            raise geo.ErrorGeometria("«A objeto» gira hacia un solo lado: usá la dirección «Un lado».")
        return _revolver_hasta(ws, punto_eje, d, hasta)
    a2 = (angulo2 or 0.0) if direccion == "dos_lados" else 0.0
    if abs(angulo) < 1e-9:
        raise geo.ErrorGeometria("El ángulo de revolución no puede ser cero.")
    if abs(angulo) > 360.0 + 1e-6 or abs(a2) > 360.0 + 1e-6 or abs(angulo) + abs(a2) > 360.0 + 1e-6:
        raise geo.ErrorGeometria("El ángulo de revolución no puede pasar de 360° (en total): más de una vuelta se "
                                 "pisa a sí misma.")
    tramos = {"un_lado": [(0.0, angulo)], "simetrica": [(-angulo / 2, angulo)],
              "dos_lados": [(0.0, abs(angulo))] + ([(0.0, -abs(a2))] if abs(a2) > 1e-9 else [])}[direccion]
    if abs(angulo) + abs(a2) >= 360.0 - 1e-9 and direccion != "dos_lados":
        tramos = [(0.0, math.copysign(360.0, angulo))]
    eje = gp_Ax1(_pnt(punto_eje), gp_Dir(*map(float, d)))
    piezas = []
    for inicio, grados in tramos:
        for w in ws:
            base = geo.rotar(w, np.asarray(punto_eje, float), d, inicio) if inicio else w
            rev = BRepPrimAPI_MakeRevol(base, eje, math.radians(grados))
            if not rev.IsDone():
                raise geo.ErrorGeometria("No se pudo girar el perfil alrededor del eje: el perfil tiene que quedar de "
                                         "un solo lado del eje, sin cruzarlo ni apoyarse sobre él. Movelo o cambiá el eje.")
            piezas.append(rev.Shape())
    if len(tramos) == 1:
        return _simplificar(_juntar(piezas))
    return _coser_caras([c for pieza in piezas for c in geo.caras(pieza)])


def _marcos_ruta(ruta, n):
    """n marcos (punto, tangente, normal) equiespaciados en longitud a lo largo del alambre, con normal
    de rotación mínima (doble reflexión de Wang et al.): no gira alrededor de la tangente."""
    curva = BRepAdaptor_CompCurve(ruta)
    largo = GCPnts_AbscissaPoint.Length_s(curva)
    paso = max(8, math.ceil(64 / max(n - 1, 1)))   # muestras finas por tramo entre marcos
    m = paso * max(n - 1, 1)
    pts, tgs = [], []
    for i in range(m + 1):
        u = GCPnts_AbscissaPoint(curva, largo * i / m, curva.FirstParameter()).Parameter()
        p, v = gp_Pnt(), gp_Vec()
        curva.D1(u, p, v)
        pts.append(_np(p))
        tgs.append(_unitario(_np(v), "La tangente de la ruta"))
    t0 = tgs[0]
    r = np.cross(t0, (0.0, 0.0, 1.0) if abs(t0[2]) < 0.9 else (1.0, 0.0, 0.0))
    normales = [r / np.linalg.norm(r)]
    for i in range(m):
        v1 = pts[i + 1] - pts[i]
        c1 = float(v1 @ v1)
        ri, ti = normales[-1], tgs[i]
        if c1 < 1e-18:
            normales.append(ri)
            continue
        r_l = ri - (2 / c1) * float(v1 @ ri) * v1
        t_l = ti - (2 / c1) * float(v1 @ ti) * v1
        v2 = tgs[i + 1] - t_l
        c2 = float(v2 @ v2)
        r_n = r_l if c2 < 1e-18 else r_l - (2 / c2) * float(v2 @ r_l) * v2
        normales.append(r_n / np.linalg.norm(r_n))
    return [(pts[i * paso], tgs[i * paso], normales[i * paso]) for i in range(n)], largo


def _trsf_marco(p0, t0, r0, p1, t1, r1):
    """Transformación rígida que lleva el marco (p0, t0, r0) al marco (p1, t1, r1)."""
    f0 = np.column_stack([t0, r0, np.cross(t0, r0)])
    f1 = np.column_stack([t1, r1, np.cross(t1, r1)])
    rot = f1 @ f0.T
    tras = p1 - rot @ p0
    tr = gp_Trsf()
    tr.SetValues(*[float(x) for fila in np.column_stack([rot, tras]) for x in fila])
    return tr


# Torsión máxima del barrido de superficie: 50 vueltas. Lleva una sección cada ≤10° y el tiempo crece más que los
# grados (ruta de 200 mm: 3600° 0,8 s; 7200° 3,9 s; 18.000° 49 s; 36.000° 115 s y el kernel falla). Es otro tope que el
# del barrido sólido (TORSION_MAXIMA de solidos_crear) porque cuesta otra cosa: hasta 18.000° andaba y sigue andando.
TORSION_MAXIMA_SUPERFICIE = 18000.0


def _radio_conicidad(perfil, punto):
    """Distancia con la que el ángulo de conicidad se pasa a escala. Contorno cerrado: la del barrido sólido. Abierto: la
    del punto más lejano del perfil a la ruta, así ese punto se aparta de ella exactamente con el ángulo pedido."""
    from . import solidos_crear as sc
    if BRep_Tool.IsClosed_s(perfil):
        return sc._radio_referencia(perfil, punto)
    return max(float(np.linalg.norm(q - punto)) for q in _muestras(perfil, 33))


def _muestras(alambre, n):
    """n puntos equiespaciados en longitud a lo largo del alambre, en el sentido en que se recorre."""
    curva = BRepAdaptor_CompCurve(alambre)
    u = GCPnts_UniformAbscissa(curva, int(n), 1e-7)
    if not u.IsDone() or u.NbPoints() != n:
        raise geo.ErrorGeometria("No se pudo recorrer la curva.")
    return np.array([_np(curva.Value(u.Parameter(i + 1))) for i in range(n)])


def _primer_cruce(funcion):
    """Primera fracción 0..1 en la que `funcion` pasa de negativa a positiva (o llega a cero); None si no lo hace."""
    fs = np.linspace(0.0, 1.0, 129)
    valores = [funcion(f) for f in fs]
    for i in range(len(fs) - 1):
        if valores[i] < 0 <= valores[i + 1]:
            bajo, alto = fs[i], fs[i + 1]
            for _ in range(40):
                medio = (bajo + alto) / 2
                bajo, alto = (bajo, medio) if funcion(medio) >= 0 else (medio, alto)
            return float(alto)
    return None


def _recortar_perpendicular(ruta, riel):
    """Extent › Perpendicular To Path: el barrido termina en el plano perpendicular a la ruta en su final. El riel se
    corta en ese plano; si no llega, es la ruta la que se corta en el plano que pasa por el final del riel."""
    from . import solidos_crear as sc
    p, t = sc._punto_en(ruta, 1.0)
    f = _primer_cruce(lambda x: float((sc._punto_en(riel, x)[0] - p) @ t))
    if f is not None:
        return ruta, sc._recortar_alambre(riel, f)
    fin = sc._punto_en(riel, 1.0)[0]
    if float((fin - p) @ t) > 0:              # el riel pasa de largo sin cruzar: no hay nada que cortar
        return ruta, riel

    def altura(x):
        q, d = sc._punto_en(ruta, x)
        return float((q - fin) @ d)

    f = _primer_cruce(altura)
    if f is None:
        raise geo.ErrorGeometria("El riel guía no acompaña a la ruta: no se pudo cortar el barrido en un plano "
                                 "perpendicular a la ruta. Probá con «Extensión completa».")
    return sc._recortar_alambre(ruta, f), riel


def _ruta_sobre(espina, guia):
    """Copia de la ruta con sus curvas sobre las caras de `guia`: MakePipeShell las necesita para seguir la normal, y una
    curva de boceto apoyada en la superficie no las trae."""
    copia = TopoDS.Wire(BRepBuilderAPI_Copy(espina).Shape())
    caras = geo.caras(guia)
    arreglo = ShapeFix_Edge()
    for e in geo._explorar(copia, TopAbs_EDGE):
        e = TopoDS.Edge(e)
        curva = BRepAdaptor_Curve(e)
        puntos = [BRepBuilderAPI_MakeVertex(curva.Value(curva.FirstParameter() + (curva.LastParameter() - curva.FirstParameter()) * k / 2)).Vertex()
                  for k in range(3)]
        cara = next((c for c in caras if all(BRepExtrema_DistShapeShape(v, c).Value() < 1e-4 for v in puntos)), None)
        if cara is None:
            raise geo.ErrorGeometria("La ruta tiene que estar sobre la superficie guía: cada arista de la ruta, apoyada en "
                                     "una de sus caras.")
        arreglo.FixAddPCurve(e, cara, False, 1e-4)
    return copia


def _estirar(alambre, matriz):
    """Alambre deformado por una matriz 4x4 cualquiera (BRepBuilderAPI_Transform solo acepta giro y escala uniforme)."""
    g = gp_GTrsf()
    for fila in range(3):
        for col in range(4):
            g.SetValue(fila + 1, col + 1, float(matriz[fila, col]))
    return TopoDS.Wire(BRepBuilderAPI_GTransform(alambre, g, True).Shape())


# Secciones del barrido estirado: la superficie pasa por ellas; entre medio la ley ruta-riel se aproxima.
_SECCIONES_ESTIRADO = 33


def _barrido_estirado(perfiles, espina, riel, solido=False):
    """Profile Scaling › Stretch: el perfil se agranda solo en la dirección ruta-riel y conserva la altura. No existe
    en OCC: se arman secciones deformadas (cada una en el plano perpendicular a la ruta) y se soleva entre ellas.
    Con `solido` las tapas de los extremos las pone ThruSections (lo que pide el Barrido de Fusion)."""
    from . import solidos_crear as sc
    marcos, _ = _marcos_ruta(espina, _SECCIONES_ESTIRADO)

    def base(i):
        """(punto, ejes en columnas (hacia el riel, altura, tangente), distancia al riel) de la sección i."""
        p, t, _r = marcos[i]
        v = sc._punto_en(riel, i / (len(marcos) - 1))[0] - p
        x = v - t * float(v @ t)
        d = float(np.linalg.norm(x))
        if d < 1e-6:
            raise geo.ErrorGeometria("El riel guía toca la ruta: con «Estirar» tiene que ir separado de ella.")
        return p, np.column_stack([x / d, np.cross(t, x / d), t]), d

    p0, f0, d0 = base(0)
    piezas = []
    for perfil in perfiles:
        ts = BRepOffsetAPI_ThruSections(solido, False)
        for i in range(len(marcos)):
            p, f, d = base(i)
            m = np.identity(4)
            m[:3, :3] = f @ np.diag((d / d0, 1.0, 1.0)) @ f0.T
            m[:3, 3] = p - m[:3, :3] @ p0
            ts.AddWire(_estirar(perfil, m))
        ts.CheckCompatibility(False)            # copias de un mismo perfil: ya son compatibles
        ts.Build()
        if not ts.IsDone():
            raise geo.ErrorGeometria("No se pudo estirar el perfil entre la ruta y el riel: probá con «Escalar».")
        piezas.append(ts.Shape())
    return _simplificar(_juntar(piezas))


ESCALAS_RIEL = ("escalar", "estirar", "ninguna")
EXTENSIONES_RIEL = ("perpendicular", "completa")


def barrer_superficie(aristas_perfil, ruta, *, orientacion="perpendicular", torsion=0.0, distancia=1.0, conicidad=0.0,
                      carril=None, escala="escalar", extension="perpendicular", distancia_carril=1.0,
                      superficie_guia=None):
    """Barrido de curvas a lo largo de una ruta [SFC-SWEEP].

    Single Path. `orientacion`: "perpendicular" (el perfil acompaña a la ruta) o "paralela" (el perfil no rota).
    `torsion` (grados, Twist Angle): giro total del perfil alrededor de la ruta; solo con perpendicular.
    La torsión se construye con secciones intermedias cada ≤10° (aproximación muy fina, no exacta) y admite como
    máximo ±TORSION_MAXIMA_SUPERFICIE grados. `conicidad` (grados, Taper Angle): el perfil se abre (positivo) o se
    cierra de la ruta a lo largo del barrido; solo con perpendicular.
    `distancia` (Distance): hasta dónde llega el barrido sobre la ruta, de 0 (excluido) a 1 (toda la ruta).

    Path + Guide Rail: `carril` (el riel) orienta el perfil y `escala` dice cómo lo sigue: "escalar" (Scale), "estirar"
    (Stretch: solo en la dirección ruta-riel) o "ninguna" (None). `extension`: "perpendicular" (Perpendicular To Path:
    `distancia` y el barrido termina en un plano perpendicular a la ruta) o "completa" (Full Extents: `distancia` sobre
    la ruta y `distancia_carril` sobre el riel, cada uno en su fracción).

    Path + Guide Surface: `superficie_guia` (caras sobre las que va la ruta): el perfil sigue su normal."""
    if orientacion not in ("perpendicular", "paralela"):
        raise geo.ErrorGeometria(f"Orientación de barrido desconocida: {orientacion}")
    if not math.isfinite(torsion) or abs(torsion) > TORSION_MAXIMA_SUPERFICIE:
        raise geo.ErrorGeometria(f"La torsión del barrido de superficie admite como máximo "
                                 f"±{TORSION_MAXIMA_SUPERFICIE:g}° ({TORSION_MAXIMA_SUPERFICIE / 360:g} vueltas); "
                                 f"recibió {torsion:g}°.")
    if abs(torsion) > 1e-9 and orientacion != "perpendicular":
        raise geo.ErrorGeometria("La torsión solo existe con orientación perpendicular.")
    if not math.isfinite(conicidad) or abs(conicidad) >= 89.0:
        raise geo.ErrorGeometria(f"La conicidad del barrido tiene que estar entre -89° y 89°; recibió {conicidad:g}°.")
    if abs(conicidad) > 1e-9 and orientacion != "perpendicular":
        raise geo.ErrorGeometria("La conicidad solo existe con orientación perpendicular.")
    for valor in (distancia, distancia_carril):
        if not math.isfinite(valor) or not 0 < valor <= 1:
            raise geo.ErrorGeometria(f"La distancia del barrido sobre la ruta va de 0 (sin incluir) a 1; recibió {valor:g}.")
    if carril is not None and superficie_guia is not None:
        raise geo.ErrorGeometria("Elegí un riel guía o una superficie guía, no los dos.")
    guiado = carril is not None or superficie_guia is not None
    if guiado and (abs(torsion) > 1e-9 or abs(conicidad) > 1e-9):
        raise geo.ErrorGeometria("La torsión y la conicidad son del tipo «Ruta individual»: no se combinan con un riel "
                                 "ni con una superficie guía.")
    espina = _alambre_unico(ruta, "La ruta")
    from . import solidos_crear as sc      # diferido: solidos_crear importa este módulo
    if distancia < 1:
        espina = sc._recortar_alambre(espina, distancia)
    perfiles = alambres(aristas_perfil)
    if superficie_guia is not None:
        guia = _juntar(_formas(superficie_guia))
        return _simplificar(sc.barrer(perfiles, _ruta_sobre(espina, guia), superficie_guia=guia, solido=False))
    if carril is not None:
        if escala not in ESCALAS_RIEL:
            raise geo.ErrorGeometria(f"Escala del perfil desconocida: {escala}")
        if extension not in EXTENSIONES_RIEL:
            raise geo.ErrorGeometria(f"Extensión del barrido desconocida: {extension}")
        riel = _alambre_unico(carril, "El riel guía")
        if extension == "perpendicular":
            espina, riel = _recortar_perpendicular(espina, riel)
        elif distancia_carril < 1:
            riel = sc._recortar_alambre(riel, distancia_carril)
        if escala == "estirar":
            return _barrido_estirado(perfiles, espina, riel)
        return _simplificar(sc.barrer(perfiles, espina, carril=riel, escala_carril=escala, solido=False))
    largo = sc._longitud(espina)
    piezas = []
    for perfil in perfiles:
        ps = BRepOffsetAPI_MakePipeShell(espina)
        if orientacion == "paralela":
            ps.SetMode(gp_Ax2(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1), gp_Dir(1, 0, 0)))
        ps.SetTransitionMode(BRepBuilderAPI_RightCorner)     # SUP-3: la esquina viva no aplasta el perfil
        final = 1.0
        if abs(conicidad) > 1e-9:
            final = 1.0 + largo * math.tan(math.radians(conicidad)) / _radio_conicidad(perfil, sc._punto_en(espina, 0.0)[0])
            if final <= 0.01:
                raise geo.ErrorGeometria("Con esa conicidad el perfil desaparece antes del final de la ruta: probá con "
                                         "un ángulo menor.")
        ts = None
        try:
            if abs(torsion) < 1e-9 and final != 1.0:
                ley = Law_Linear()
                ley.Set(0.0, 1.0, 1.0, final)
                ps.SetLaw(perfil, ley, False, False)
            elif abs(torsion) < 1e-9:
                ps.Add(perfil, False, False)
            else:
                n = max(3, math.ceil(abs(torsion) / 10.0) + 1)
                marcos, _ = _marcos_ruta(espina, n)
                p0, t0, r0 = marcos[0]
                # Torsión con conicidad: MakePipeShell no resuelve contornos cerrados que cambian de tamaño entre secciones.
                ts = BRepOffsetAPI_ThruSections(False, False) if final != 1.0 else None
                for i, (p, t, r) in enumerate(marcos):
                    tr = _trsf_marco(p0, t0, r0, p, t, r)
                    giro = gp_Trsf()
                    giro.SetRotation(gp_Ax1(_pnt(p), gp_Dir(*map(float, t))), math.radians(torsion) * i / (n - 1))
                    esc = gp_Trsf()
                    esc.SetScale(_pnt(p), 1.0 + (final - 1.0) * i / (n - 1))
                    seccion = BRepBuilderAPI_Transform(perfil, esc.Multiplied(giro.Multiplied(tr)), True).Shape()
                    if ts is not None:
                        ts.AddWire(TopoDS.Wire(seccion))
                    else:
                        ps.Add(seccion, BRepBuilderAPI_MakeVertex(_pnt(p)).Vertex(), False, False)
            if ts is not None:
                ts.CheckCompatibility(False)
                ts.Build()
                if ts.IsDone():
                    piezas.append(ts.Shape())
                    continue
                hecho = False
            else:
                ps.Build()
                hecho = ps.IsDone()
        except geo.ErrorGeometria:
            raise
        except Exception:  # noqa: BLE001 — OCC crudo («PipeShell : uncompatible wires»): SUP-22
            hecho = False
        if not hecho:
            raise geo.ErrorGeometria(
                (f"No se pudo calcular el barrido con una torsión de {torsion:g}°: las secciones giradas no encajan "
                 "(la ruta es corta para tantas vueltas). Probá con menos torsión o con una ruta más larga."
                 if abs(torsion) > 1e-9 else
                 "No se pudo barrer el perfil por la ruta: revisá que el perfil no se autointersecte y que la ruta no "
                 "tenga quiebres muy cerrados."))
        piezas.append(ps.Shape())
    return _simplificar(_juntar(piezas))


def _es_punto(s):
    if isinstance(s, gp_Pnt):
        return True
    if isinstance(s, TopoDS_Shape):
        return s.ShapeType() == TopAbs_VERTEX
    try:
        return np.asarray(s, float).shape == (3,)
    except (TypeError, ValueError):
        return False


def _interpolar(puntos, periodica=False):
    """Arista por `puntos`; recta si son dos."""
    from .curvas3d import arista_recta, arista_spline
    return arista_recta(*puntos) if len(puntos) == 2 else arista_spline(puntos, cerrada=periodica)


def _auxiliar_puntos(w, direccion, delta, superficie=None):
    """Sección auxiliar de un perfil: cada punto `q` (a la fracción `s`, con tangente `t`) va a q + delta · direccion(s, q,
    t); con `superficie` se proyecta además sobre ella. Conserva las aristas del perfil; en una esquina, las dos aristas
    se encuentran donde se cruzan sus bordes corridos. Un círculo corrido que sigue siendo círculo sale exacto: una
    spline por sus puntos ondularía la solevación."""
    from . import solidos_crear as sc
    largos = [sc._longitud(e) for e in sc._aristas_de(w)]
    cortes = np.cumsum([0.0, *largos]) / sum(largos)
    cerrado = BRep_Tool.IsClosed_s(w)
    tramos, esquinas = [], []
    for a, b in zip(cortes[:-1], cortes[1:], strict=True):
        puntos = []
        for s in np.linspace(a, b, 17):
            q = sc._punto_en(w, s)[0]
            p = q + delta * direccion(s, q, sc._punto_en(w, min(max(s, a + 1e-6), b - 1e-6))[1])   # la tangente de ESTA arista
            if superficie is not None:
                proy = GeomAPI_ProjectPointOnSurf(_pnt(p), superficie)
                if proy.NbPoints() == 0:
                    raise geo.ErrorGeometria("La superficie de la cara no se prolonga hasta donde pide la condición Suave.")
                p = _np(proy.NearestPoint())
            puntos.append(p)
        tramos.append(puntos)
        esquinas.append(sc._punto_en(w, b)[0])
    if len(tramos) == 1 and cerrado:
        puntos = tramos[0][:-1]
        circulo = GC_MakeCircle(_pnt(puntos[0]), _pnt(puntos[4]), _pnt(puntos[8]))
        if circulo.IsDone() and all(circulo.Value().Circ().Distance(_pnt(p)) < 1e-6 for p in puntos):
            return "alambre", sc._alambre([BRepBuilderAPI_MakeEdge(circulo.Value()).Edge()])
        return "alambre", sc._alambre([_interpolar(puntos, True)])
    for i in range(len(tramos) if cerrado else len(tramos) - 1):
        siguiente = tramos[(i + 1) % len(tramos)]
        a, b = tramos[i][-1] - esquinas[i], siguiente[0] - esquinas[i]
        coseno = float(a @ b) / max(float(np.linalg.norm(a) * np.linalg.norm(b)), 1e-12)
        tramos[i][-1] = siguiente[0] = esquinas[i] + (a + b) / max(1.0 + coseno, 0.1)
    return "alambre", sc._alambre([_interpolar(p) for p in tramos])


def _direccion_alineada(w, cara, alineacion):
    """direccion(s, q, t) de un perfil sobre el borde de `cara`, hacia afuera de ella. Free Edges: perpendicular al perfil
    en el plano tangente. Align Edges (perfil abierto): en cada extremo sigue a la arista de la cara que llega ahí y no es
    tangente al perfil. Align to Surface: sigue a la curva paramétrica de la superficie que más se aparta del perfil.
    Entre los extremos, la corrección se reparte en línea recta."""
    from . import solidos_crear as sc
    if alineacion not in ("libre", "alinear", "superficie"):
        raise geo.ErrorGeometria(f"Alineación de bordes desconocida: {alineacion}")
    uv = ShapeAnalysis_Surface(BRep_Tool.Surface_s(cara))

    def libre(q, t):
        p = uv.ValueOfUV(_pnt(q), 1e-6)
        return _unitario(np.cross(sc._normal_orientada(cara, p.X(), p.Y())[1], t), "La tangente del perfil")

    q, t = sc._punto_en(w, 0.5)
    adentro = BRepClass_FaceClassifier(cara, uv.ValueOfUV(_pnt(q + 1e-3 * libre(q, t)), 1e-6), 1e-7).State() == TopAbs_IN
    signo = -1.0 if adentro else 1.0

    def del_extremo(q, t):
        afuera = signo * libre(q, t)
        if alineacion == "superficie":
            p, du, dv = uv.ValueOfUV(_pnt(q), 1e-6), gp_Vec(), gp_Vec()
            BRepAdaptor_Surface(cara).D1(p.X(), p.Y(), gp_Pnt(), du, dv)
            d = min((_unitario(_np(x)) for x in (du, dv)), key=lambda x: abs(float(x @ t)))
            return d if float(d @ afuera) > 0 else -d
        for e in geo._explorar(cara, TopAbs_EDGE):
            e = TopoDS.Edge(e)
            if BRep_Tool.Degenerated_s(e) or BRep_Tool.IsClosed_s(e, cara):
                continue
            a, b = _extremos(e)
            if min(np.linalg.norm(a - q), np.linalg.norm(b - q)) > 1e-5:
                continue
            curva = BRepAdaptor_Curve(e)
            u0, u1 = curva.FirstParameter(), curva.LastParameter()
            cerca = np.linalg.norm(_np(curva.Value(u0)) - q) < np.linalg.norm(_np(curva.Value(u1)) - q)
            p, v = gp_Pnt(), gp_Vec()
            curva.D1(u0 if cerca else u1, p, v)
            d = _unitario(_np(v)) * (-1.0 if cerca else 1.0)        # sale de la arista por este extremo
            if abs(float(d @ t)) < math.cos(math.radians(1.0)):      # no tangente al perfil
                return d
        return afuera                                               # Align Edges sin esa arista: queda libre

    correccion = {}
    if alineacion != "libre":
        if BRep_Tool.IsClosed_s(w):
            raise geo.ErrorGeometria("La alineación de bordes es de los perfiles abiertos: uno cerrado no tiene extremos.")
        for s in (0.0, 1.0):
            q, t = sc._punto_en(w, s)
            correccion[s] = del_extremo(q, t) - signo * libre(q, t)

    def direccion(s, q, t):
        d = signo * libre(q, t)
        if correccion:
            d = d + (1.0 - s) * correccion[0.0] + s * correccion[1.0]
        return _unitario(d, "La dirección de la condición de borde")
    return direccion


def _normal_seccion(w, hacia):
    """Normal del plano de un perfil, hacia `hacia`. Una recta no define plano: la perpendicular a ella que va a `hacia`."""
    plano = BRepBuilderAPI_FindPlane(w, 1e-6)
    if plano.Found():
        d = plano.Plane().Axis().Direction()
        n = np.array([d.X(), d.Y(), d.Z()])
    else:
        (a, b) = _extremos(TopoDS.Edge(next(iter(geo._explorar(w, TopAbs_EDGE)))))
        recta = _unitario(b - a, "El perfil")
        n = _unitario(hacia - recta * float(hacia @ recta), "La dirección entre los perfiles")
    return n if float(n @ hacia) >= 0 else -n


def _domo(punto, w, peso):
    """Secciones auxiliares de Point Tangent, de la más cercana al punto a la más lejana: copias del perfil `w` achicadas
    como una elipse hacia `punto`, para que la superficie llegue en forma de cúpula. `peso` (Tangency Weight) la llena."""
    from . import solidos_crear as sc
    c, salida = sc._centro_alambre(w), []
    for f in (0.98, 0.93, 0.85, 0.72, 0.5):
        escala = (1.0 - f * f) ** (0.5 / peso)
        m = np.identity(4)
        m[:3, :3] *= escala
        m[:3, 3] = c + (punto - c) * f - escala * c
        salida.append(("alambre", TopoDS.Wire(geo.transformar(w, m))))
    return salida


def _auxiliares(sec, otra, cond, signo, exacta=False):
    """Secciones auxiliares de la condición `cond` del perfil `sec` hacia su vecino `otra`, de la más cercana a la más
    lejana. La solevación pasa por ellas: así sale con la dirección pedida (aproximación, como en la solevación sólida).
    Con `exacta` un perfil cerrado también se corre punto por punto, y el ángulo vale en todo el contorno."""
    from . import solidos_crear as sc
    tipo, peso = cond["tipo"], float(cond.get("peso", 1.0))
    if peso <= 0:
        raise geo.ErrorGeometria("El peso de la condición de borde tiene que ser positivo.")

    def centro(s):
        return _np(BRep_Tool.Pnt_s(s[1])) if s[0] == "vertice" else sc._centro_alambre(s[1])

    if tipo == "punto_tangente":
        if sec[0] != "vertice" or otra[0] != "alambre":
            raise geo.ErrorGeometria("La condición «Punto tangente» es de un perfil que es un punto, junto a un contorno.")
        return _domo(centro(sec), otra[1], peso)
    if sec[0] != "alambre":
        raise geo.ErrorGeometria("La condición de borde necesita un perfil con contorno; un punto es agudo o tangente.")
    w, c = sec[1], centro(sec)
    hacia = centro(otra) - c
    delta = peso * 0.15 * float(np.linalg.norm(hacia))
    if tipo == "direccion":
        angulo = float(cond.get("angulo", 90.0))
        if not 0 < angulo < 180:
            raise geo.ErrorGeometria("El ángulo de la condición de borde está entre 0 y 180 grados.")
        n = _normal_seccion(w, hacia)
        if BRep_Tool.IsClosed_s(w) and not exacta:
            return [sc._auxiliar_direccion(w, n, delta, angulo, signo)]
        inclinacion = 1.0 / math.tan(math.radians(angulo))
        if BRep_Tool.IsClosed_s(w):                # hacia afuera del contorno, recorra para donde recorra
            q, t = sc._punto_en(w, 0.25)
            signo = signo * (1.0 if float(np.cross(t, n) @ (q - c)) > 0 else -1.0)
        return [_auxiliar_puntos(w, lambda _s, _q, t: _unitario(n + np.cross(t, n) * inclinacion * signo), delta)]
    if tipo not in ("tangente", "suave"):
        raise geo.ErrorGeometria(f"Condición de borde desconocida: {tipo}")
    cara = cond.get("cara")
    if cara is None:
        raise geo.ErrorGeometria("La condición Tangente o Suave necesita la cara a la que la superficie es tangente.")
    direccion = _direccion_alineada(w, cara, cond.get("alineacion", "libre"))
    if tipo == "tangente":
        return [_auxiliar_puntos(w, direccion, delta)]
    return [_auxiliar_puntos(w, direccion, k * delta, BRep_Tool.Surface_s(cara)) for k in (0.5, 1.5)]


def _con_condiciones(secs, inicio, fin, medias):
    """`secs` con las secciones auxiliares de las condiciones de borde del primer perfil, del último y («Dirección») de
    los de en medio (`medias`: {posición: condición}), cada una junto a su perfil y por el lado que corresponde."""
    n = len(secs)
    delante, detras = {}, {}
    for pos, cond in [(0, inicio), (n - 1, fin)] + sorted((int(k), v) for k, v in (medias or {}).items()):
        if not cond or cond.get("tipo", "libre") == "libre":
            continue
        if not 0 <= pos < n:
            raise geo.ErrorGeometria(f"No hay un perfil en la posición {pos + 1} para la condición de borde.")
        extremo = pos in (0, n - 1)
        if not extremo and cond["tipo"] != "direccion":
            raise geo.ErrorGeometria("Entre el primer perfil y el último solo vale la condición Dirección.")
        if pos < n - 1:
            delante[pos] = _auxiliares(secs[pos], secs[pos + 1], cond, 1.0)
        if pos > 0:
            detras[pos] = _auxiliares(secs[pos], secs[pos - 1], cond, 1.0 if extremo else -1.0)
    salida = []
    for i, sec in enumerate(secs):
        salida += reversed(detras.get(i, []))
        salida.append(sec)
        salida += delante.get(i, [])
    return salida


def _esquinas(alambre, n):
    """Índices de las `n` muestras de `alambre` donde la tangente salta más de 5° entre dos aristas."""
    from . import solidos_crear as sc
    aristas = sc._aristas_de(alambre)
    largos = np.array([sc._longitud(e) for e in aristas])
    salida = [0] if BRep_Tool.IsClosed_s(alambre) and len(aristas) > 1 else []
    for f in np.cumsum(largos)[:-1] / largos.sum():
        a, b = sc._punto_en(alambre, f - 1e-5)[1], sc._punto_en(alambre, f + 1e-5)[1]
        if float(a @ b) < math.cos(math.radians(5.0)):
            salida.append(int(round(f * (n - 1))))
    return salida


_MUESTRAS_PERFIL = 721    # puntos por perfil para ubicar los rieles y repartir el contorno
_SECCIONES_TRAMO = 6      # secciones por las que pasa la superficie entre dos perfiles
_BANDA_RIEL = 0.1         # fracción del contorno, a cada lado de un riel, donde la superficie vuelve a él


def _derivadas(q, auxiliares, sentido, peso):
    """(primera, segunda) derivada de la superficie en los puntos `q` de un perfil, a partir de sus secciones auxiliares: una da la
    dirección; dos (Suave) además la curvatura de la cara, que se lee de la parábola por los tres. `sentido` -1 en el último perfil,
    que se recorre llegando. El peso es la velocidad con que sale: 1 es la de avanzar a lo largo de la solevación."""
    v1 = auxiliares[0] - q
    t1 = np.maximum(np.linalg.norm(v1, axis=-1, keepdims=True), 1e-12)
    if len(auxiliares) == 1:
        return sentido * peso * v1 / t1, None
    v2 = auxiliares[1] - q
    t2 = np.maximum(np.linalg.norm(v2, axis=-1, keepdims=True), 1e-12)
    curva = 2.0 * (v2 / t2 - v1 / t1) / np.maximum(t2 - t1, 1e-12)
    d = v1 / t1 - curva * t1 / 2.0
    return sentido * peso * d / np.maximum(np.linalg.norm(d, axis=-1, keepdims=True), 1e-12), peso * peso * curva


def _solevar_con_rieles(secs, rieles, inicio=None, fin=None, medias=None, cerrada=False, exacta=False, *, solido=False):
    """Rails de la solevación [SFC-REF-LOFT-DLG]: cualquier cantidad de rieles, que tocan cada perfil y terminan en el
    primero y el último (o más allá). OCC admite uno solo y con perfiles lisos, así que se arman secciones intermedias:
    cada una es la interpolación de los perfiles más un corrimiento que la lleva hasta los rieles, repartido entre ellos
    a lo largo del contorno, y se soleva entre todas. Las esquinas se conservan si en todos los perfiles caen entre los
    mismos rieles; si no, el contorno queda liso entre riel y riel. `secs` son los perfiles como ("alambre" o "vertice",
    forma): un punto en un extremo vale si los rieles llegan a él. Con `cerrada` los rieles son lazos que pasan por todos.

    Las condiciones de borde mandan en el contorno y los rieles en sus puntos: entre un riel y otro la salida es la de la
    condición (la interpolación pasa por las secciones auxiliares y ahí el corrimiento no cuenta), y en la franja `_BANDA_RIEL`
    que rodea a cada riel la superficie vuelve a él, que la superficie tiene que seguir.

    Con `exacta` Dirección, Tangente y Suave no pasan por las auxiliares: de ellas sale la derivada con que la interpolación deja
    el perfil (la segunda en Suave), y así se cumplen en el perfil, con el peso como velocidad de salida. También sirve sin rieles,
    si los perfiles son compatibles (`_exacta_posible`). `solido` agrega las tapas sobre las mismas secciones reconstruidas."""
    from scipy.interpolate import CubicSpline, make_interp_spline

    from . import solidos_crear as sc
    if all(t == "vertice" for t, _f in secs):
        raise geo.ErrorGeometria("Con rieles hace falta al menos un perfil que sea una curva, no solo puntos.")
    anillo = BRep_Tool.IsClosed_s(next(f for t, f in secs if t == "alambre"))
    if any(t == "alambre" and BRep_Tool.IsClosed_s(f) != anillo for t, f in secs):
        raise geo.ErrorGeometria("Con rieles, los perfiles tienen que ser todos abiertos o todos cerrados.")
    if cerrada and not all(BRep_Tool.IsClosed_s(r) for r in rieles):
        raise geo.ErrorGeometria("En una solevación cerrada los rieles tienen que ser lazos cerrados que pasen por todos los perfiles.")
    fin_muestras = -1 if anillo else None
    m = _MUESTRAS_PERFIL - (1 if anillo else 0)
    contornos = [_muestras(f, _MUESTRAS_PERFIL)[:fin_muestras] if t == "alambre" else np.tile(_np(BRep_Tool.Pnt_s(f)), (m, 1))
                 for t, f in secs]
    originales = list(contornos)
    n = len(secs)
    toques, en_riel = np.empty((len(rieles), n), int), np.empty((len(rieles), n))
    for j, riel in enumerate(rieles):
        denso = _muestras(riel, 1441)
        for i, (_t, f) in enumerate(secs):
            d = BRepExtrema_DistShapeShape(f, riel)
            if not d.IsDone() or d.Value() > 0.01:
                raise geo.ErrorGeometria(f"El riel {j + 1} no toca el perfil {i + 1}: un riel tiene que cruzar todos los "
                                         "perfiles.")
            q = _np(d.PointOnShape1(1))
            toques[j, i] = np.argmin(np.linalg.norm(contornos[i] - q, axis=1))
            en_riel[j, i] = np.argmin(np.linalg.norm(denso - q, axis=1)) / (len(denso) - 1)
    if cerrada:                                    # cada riel da una vuelta entera: la fracción sigue creciendo (o bajando)
        en_riel = np.unwrap(np.column_stack([en_riel, en_riel[:, 0]]) * 2 * math.pi, axis=1) / (2 * math.pi)
        if np.any(np.abs(np.abs(en_riel[:, -1] - en_riel[:, 0]) - 1.0) > 1e-3):
            raise geo.ErrorGeometria("En una solevación cerrada cada riel tiene que dar la vuelta pasando por todos los perfiles.")
    # Cada perfil se recorre desde el primer riel y en el sentido en que más se parece al anterior.
    esquinas, ordenes = [], []
    for i, (t, f) in enumerate(secs):
        if t == "vertice":
            esquinas.append(set())
            ordenes.append(None)
            continue
        arranque = toques[0, i] if rieles else 0
        if i and not rieles:                       # empieza en la esquina más cercana al arranque del perfil anterior: así se emparejan
            lugares = sorted({q % m for q in _esquinas(f, _MUESTRAS_PERFIL)}) or list(range(m))
            arranque = lugares[int(np.argmin(np.linalg.norm(contornos[i][lugares] - contornos[i - 1][0], axis=1)))]
        candidatos = [np.roll(o, -int(np.nonzero(o == arranque)[0][0])) if anillo else o for o in (np.arange(m), np.arange(m)[::-1])]

        def parecido(o, i=i):
            a, b = contornos[i][o], contornos[i - 1]
            return float(np.linalg.norm((a - a.mean(axis=0)) - (b - b.mean(axis=0))))

        orden = min(candidatos, key=parecido) if i else candidatos[0]
        lugar = np.empty(m, int)
        lugar[orden] = np.arange(m)
        contornos[i] = contornos[i][orden]
        toques[:, i] = lugar[toques[:, i]]
        ordenes.append(orden)
        esquinas.append({int(lugar[q % m]) for q in _esquinas(f, _MUESTRAS_PERFIL)})
    for i, (t, _f) in enumerate(secs):
        if t == "vertice":                         # un punto se reparte igual que el perfil de al lado
            vecino = 1 if i == 0 else i - 1
            toques[:, i], esquinas[i] = toques[:, vecino], esquinas[vecino]

    def marcas(con_esquinas):
        """Índices que parten cada contorno en tramos, o None si los perfiles no se pueden emparejar así."""
        salida = []
        for i in range(n):
            cortes = {int(x) for x in toques[:, i]} | (esquinas[i] if con_esquinas else set())
            salida.append(sorted(cortes | ({0, m} if anillo else {0, m - 1})))
        lugares = {tuple(c.index(int(x)) for x in toques[:, i]) for i, c in enumerate(salida)}
        return salida if len(lugares) == 1 and len({len(c) for c in salida}) == 1 else None

    tramos = marcas(True) or marcas(False)
    if tramos is None:
        raise geo.ErrorGeometria("Los rieles se cruzan: tienen que seguir el mismo orden en todos los perfiles.")
    k = len(tramos[0]) - 1
    fr = np.linspace(0.0, 1.0, max(9, math.ceil(49 / k)))

    def tramo(contorno, marcas_perfil, j):
        a, b = marcas_perfil[j], marcas_perfil[j + 1]
        base = np.vstack([contorno, contorno[:1]]) if anillo else contorno
        return np.column_stack([np.interp(a + (b - a) * fr, np.arange(len(base)), base[:, c]) for c in range(3)])

    def centro(sec):
        return _np(BRep_Tool.Pnt_s(sec[1])) if sec[0] == "vertice" else sc._centro_alambre(sec[1])

    def de_auxiliar(sec):
        """(contorno de una sección auxiliar, en el orden del perfil más cercano; ese perfil)."""
        p = min((i for i, (t, _f) in enumerate(secs) if t == "alambre"), key=lambda i: np.linalg.norm(centro(secs[i]) - centro(sec)))
        a = _muestras(sec[1], _MUESTRAS_PERFIL)[:fin_muestras]
        if anillo:
            a0, b0 = a - a.mean(axis=0), originales[p] - originales[p].mean(axis=0)
            a0 = a0 * np.linalg.norm(b0[0]) / max(float(np.linalg.norm(a0, axis=1).mean()), 1e-9)
            a = np.roll(a, -int(np.argmin(np.linalg.norm(a0 - b0[0], axis=1))), axis=0)
        return a[ordenes[p]], p

    completo = _con_condiciones(secs, inicio, fin, medias) if (inicio or fin or medias) and not exacta else list(secs)
    reales = [i for i, sec in enumerate(completo) if any(sec is r for r in secs)]
    centros = np.array([centro(sec) for sec in completo])
    x = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(centros, axis=0), axis=1))])
    x_reales = x[reales]
    if cerrada:
        x_reales = np.r_[x_reales, x_reales[-1] + np.linalg.norm(centros[reales[-1]] - centros[reales[0]])]
    if np.any(np.diff(x_reales) < 1e-9):
        raise geo.ErrorGeometria("Hay dos perfiles en el mismo lugar.")
    grilla = np.array([[tramo(contornos[i], tramos[i], j) for j in range(k)] for i in range(n)])     # perfil, tramo, punto, xyz
    sin_condicion = CubicSpline(x_reales, np.concatenate([grilla, grilla[:1]]) if cerrada else grilla, axis=0,
                                bc_type="periodic" if cerrada else "not-a-knot")
    con_condicion = None

    def contorno_aux(sec):
        contorno, p = de_auxiliar(sec)
        return np.array([tramo(contorno, tramos[p], j) for j in range(k)])

    if exacta:
        lados = [(0, 1, 1.0, inicio), (n - 1, n - 2, -1.0, fin)]
        bordes = [None if not c or c.get("tipo", "libre") == "libre" else _derivadas(
            grilla[i], [contorno_aux(a) for a in _auxiliares(secs[i], secs[v], c, 1.0, True)], sentido, float(c.get("peso", 1.0)))
            for i, v, sentido, c in lados]
        if any(b is not None and b[1] is not None for b in bordes):
            cero = np.zeros_like(grilla[0])
            bc = [[(1, b[0]), (2, b[1] if b[1] is not None else cero)] if b is not None else [(2, cero), (3, cero)] for b in bordes]
            con_condicion = make_interp_spline(x_reales, grilla, k=5, bc_type=(bc[0], bc[1]), axis=0)
        else:
            con_condicion = CubicSpline(x_reales, grilla, axis=0, bc_type=tuple("not-a-knot" if b is None else (1, b[0]) for b in bordes))
    elif len(completo) > n:
        filas = []
        for sec in completo:
            if any(sec is r for r in secs):
                filas.append(grilla[next(i for i, r in enumerate(secs) if r is sec)])
            else:
                filas.append(contorno_aux(sec))
        con_condicion = CubicSpline(x, np.array(filas), axis=0)
    # A lo largo del contorno cada punto tiene una coordenada 0..1; cada riel, la del tramo donde empieza.
    coordenada = (np.arange(k)[:, None] + fr) / k
    donde = [tramos[0].index(int(a)) for a in toques[:, 0]]
    orden = np.argsort(donde)
    gs = np.array(donde, float)[orden] / k
    lejos = np.abs(coordenada[..., None] - gs)
    lejos = np.minimum(lejos, 1.0 - lejos) if anillo else lejos
    libre = np.clip(lejos.min(axis=-1, initial=1.0) / _BANDA_RIEL, 0.0, 1.0)
    libre = libre * libre * (3.0 - 2.0 * libre)                 # 0 sobre el riel, 1 lejos: ahí manda la condición

    def en_condicion(s):
        """1 en un perfil con condición, 0 desde el perfil vecino: el corrimiento de los rieles no le cambia la salida."""
        salida = 0.0
        for i, cond in [(0, inicio), (n - 1, fin), *sorted((int(a), b) for a, b in (medias or {}).items())]:
            if cond and cond.get("tipo", "libre") != "libre":
                vecino = i + (1 if s >= x_reales[i] else -1)
                if 0 <= vecino < n:
                    t = min(abs(s - x_reales[i]) / abs(x_reales[vecino] - x_reales[i]), 1.0)
                    salida = max(salida, (1.0 - t) ** 2 * (1.0 + 2.0 * t))
        return salida

    pasos = _SECCIONES_TRAMO * (3 if con_condicion else 1)
    ts = BRepOffsetAPI_ThruSections(solido, False)
    primera = None
    tramos_x = n if cerrada else n - 1
    for i in range(tramos_x):
        for paso in range(pasos + (i == tramos_x - 1 and not cerrada)):
            f = paso / pasos
            indice = i + 1 if paso == pasos else i
            if paso in (0, pasos) and secs[indice][0] == "vertice":
                ts.AddVertex(secs[indice][1])
                continue
            s = x_reales[i] + (x_reales[i + 1] - x_reales[i]) * f
            base = sin_condicion(s)
            reparto = 0.0
            if rieles:
                corrimiento = np.array([sc._punto_en(riel, (en_riel[j, i] + (en_riel[j, i + 1] - en_riel[j, i]) * f) % 1.0 if cerrada
                                                     else en_riel[j, i] + (en_riel[j, i + 1] - en_riel[j, i]) * f)[0]
                                        - (base[donde[j], 0] if donde[j] < k else base[k - 1, -1])
                                        for j, riel in enumerate(rieles)])
                reparto = np.stack([np.interp(coordenada, gs, corrimiento[orden, c], period=1.0 if anillo else None) for c in range(3)], axis=-1)
            if con_condicion is None:
                puntos = base + reparto
            else:
                peso = libre[..., None]
                puntos = base + peso * (con_condicion(s) - base) + reparto * (1.0 - peso * en_condicion(s))
            if k == 1 and anillo:
                w = sc._alambre([_interpolar(puntos[0, :-1], True)])
            else:
                w = sc._alambre([_interpolar(t) for t in puntos])
            ts.AddWire(w)
            primera = primera or w
    if cerrada:
        ts.AddWire(primera)
    ts.CheckCompatibility(False)              # todas tienen las mismas aristas, en el mismo orden
    ts.Build()
    if not ts.IsDone():
        raise geo.ErrorGeometria("No se pudo crear la superficie con esos rieles: revisá que toquen todos los perfiles y "
                                 "que no se crucen entre sí.")
    return ts.Shape()


def _exacta_posible(secs, condiciones):
    """¿Las condiciones se pueden cumplir con derivadas? Hace falta que sean de los extremos, que no haya perfiles punto y que los
    perfiles se puedan emparejar: todos abiertos o todos cerrados y con las mismas esquinas. Si no, quedan las secciones auxiliares."""
    if any(t == "vertice" for t, _f in secs) or any(c and c.get("tipo") == "punto_tangente" for c in condiciones):
        return False
    return len({(BRep_Tool.IsClosed_s(f), len(_esquinas(f, _MUESTRAS_PERFIL))) for _t, f in secs}) == 1


def solevar_superficie(secciones, *, cerrada=False, reglada=False, rieles=(), linea_central=None, condicion_inicio=None,
                       condicion_fin=None, condiciones_medias=None, fusionar_tangentes=False, condicion_exacta=False):
    """Solevado (loft) de superficie entre secciones [SFC-LOFT, SFC-REF-LOFT-DLG].

    Cada sección es una curva/alambre o un punto (numpy (3,), gp_Pnt o vértice) — los puntos solo
    pueden ir primero o último (End condition Sharp). `cerrada` une la última sección con la primera;
    `reglada` usa tramos rectos entre secciones.

    `condicion_inicio`, `condicion_fin` (End Condition): {"tipo": "libre"}; {"tipo": "direccion", "angulo": grados desde
    el plano del perfil (90 = perpendicular), "peso": 1} (Direction, Takeoff Angle y Takeoff Weight); {"tipo": "tangente"
    o "suave", "cara": cara cuyo borde es el perfil, "peso": 1, "alineacion": "libre", "alinear" o "superficie"} (Tangent
    G1 o Smooth G2, Tangency Weight y Free Edges, Align Edges o Align to Surface, que son de los perfiles abiertos);
    {"tipo": "punto_tangente", "peso": 1} en un perfil que es un punto (Point Tangent: cúpula; sin condición es Sharp).
    `condiciones_medias`: {posición: condición Dirección} en los perfiles de en medio.
    Las condiciones se aproximan con secciones auxiliares por las que pasa la superficie; con `condicion_exacta` Dirección, Tangente
    y Suave de los extremos fijan la derivada con que sale (ver `_exacta_posible`), sin línea central y sin perfiles de en medio.
    `rieles` (Rail): cualquier cantidad, ver `_solevar_con_rieles`. `linea_central` (Centerline): las secciones se
    mantienen normales a ella. Las dos guías se combinan con las condiciones. `fusionar_tangentes` (Tangent Edges › Merge)."""
    secciones = list(secciones)
    if len(secciones) < 2:
        raise geo.ErrorGeometria("El solevado necesita al menos dos secciones.")
    secs, primera = [], None
    for i, s in enumerate(secciones):
        es_punto = isinstance(s, gp_Pnt) or (isinstance(s, TopoDS_Shape) and s.ShapeType() == TopAbs_VERTEX) \
            or (not isinstance(s, (TopoDS_Shape, list, tuple)) or
                (isinstance(s, (list, tuple)) and len(s) == 3 and all(isinstance(c, (int, float)) for c in s)))
        if es_punto:
            if 0 < i < len(secciones) - 1 or cerrada:
                raise geo.ErrorGeometria("Un punto solo puede ser la primera o la última sección de un solevado abierto.")
            if isinstance(s, TopoDS_Shape):
                v = TopoDS.Vertex(s)
            else:
                v = BRepBuilderAPI_MakeVertex(s if isinstance(s, gp_Pnt) else _pnt(s)).Vertex()
            secs.append(("vertice", v))
        else:
            w = _alambre_unico(s, f"La sección {i + 1}")
            primera = primera or w
            secs.append(("alambre", w))
    if cerrada and len(secciones) < 3:
        raise geo.ErrorGeometria("Un solevado cerrado necesita al menos tres secciones.")
    rieles = list(rieles)
    if rieles and linea_central is not None:
        raise geo.ErrorGeometria("Elegí rieles o una línea central, no los dos.")
    guiada = bool(rieles) or linea_central is not None
    condiciones = any(c and c.get("tipo", "libre") != "libre"
                      for c in (condicion_inicio, condicion_fin, *(condiciones_medias or {}).values()))
    if (guiada or condiciones) and reglada:
        raise geo.ErrorGeometria("Las condiciones de borde, los rieles y la línea central no se combinan con tramos rectos.")
    if cerrada and (condiciones or linea_central is not None):
        raise geo.ErrorGeometria("Una solevación cerrada no tiene perfiles extremos: no admite condiciones de borde, y OpenCascade "
                                 "no la arma con línea central. Con rieles sí se puede.")
    exacta = (condicion_exacta and condiciones and not condiciones_medias and linea_central is None
              and _exacta_posible(secs, (condicion_inicio, condicion_fin)))
    if rieles or exacta:
        forma = _solevar_con_rieles(secs, [_alambre_unico(r, "El riel") for r in rieles], condicion_inicio, condicion_fin,
                                    condiciones_medias, cerrada, exacta)
    elif linea_central is not None:
        from . import solidos_crear as sc
        secs = _con_condiciones(secs, condicion_inicio, condicion_fin, condiciones_medias) if condiciones else secs
        forma = sc.solevar([x[1] for x in secs], linea_central=_alambre_unico(linea_central, "La línea central"), solido=False)
    else:
        if condiciones:
            secs = _con_condiciones(secs, condicion_inicio, condicion_fin, condiciones_medias)
        ts = BRepOffsetAPI_ThruSections(False, bool(reglada))
        for tipo, forma in secs:
            (ts.AddVertex if tipo == "vertice" else ts.AddWire)(forma)
        if cerrada:
            ts.AddWire(primera)
        # SUP-4: con secciones de distinto tipo (rectángulo + círculos) hay que dejar que OCC las haga
        # compatibles; desactivarlo hacía fallar RCC, CCR, RRC, CRC y RCR.
        ts.CheckCompatibility(True)
        ts.Build()
        if not ts.IsDone():
            raise geo.ErrorGeometria("No se pudo crear la superficie entre las secciones: revisá que estén en el orden "
                                     "en que se recorren, que no se crucen y que tengan una forma parecida (o probá con "
                                     "«Tramos rectos»).")
        forma = ts.Shape()
    forma = _simplificar(forma)
    return _simplificar(geo.unificar_caras(forma)) if fusionar_tangentes else forma


def _parche_imposible(continuidad):
    """Error claro cuando el kernel no puede cumplir la continuidad pedida (SUP-1: antes salía el texto crudo
    «Geom_RectangularTrimmedSurface::V1==V2» o «BRepFill : The continuity is not G0 G1 or G2»)."""
    que = {"G1": "tangente (G1)", "G2": "de curvatura (G2)"}.get(continuidad, "de conexión (G0)")
    return geo.ErrorGeometria(
        f"No se pudo construir el parche con continuidad {que}: el kernel no encuentra una superficie que cumpla "
        "esa continuidad con las caras vecinas en todo el contorno (en una esquina, dos caras que se tocan pueden "
        "pedir planos tangentes distintos). Probá con Conexión (G0), con menos aristas, o agregá una arista o un "
        "punto interior que guíe el parche.")


def parche(aristas_contorno, *, continuidad="G0", interior=(), soporte=None, por_arista=()):
    """Parche que cierra un contorno [SFC-PATCH].

    Contorno plano, G0 y sin guías interiores → cara plana exacta. Si no, superficie de relleno
    (BRepOffsetAPI_MakeFilling). G1/G2 necesita `soporte`: el cuerpo al que pertenecen las aristas
    (de ahí salen las caras vecinas para la tangencia). `interior`: puntos (numpy) o aristas guía
    (Interior Rails/Points). `por_arista`: pares (arista, continuidad) que reemplazan a `continuidad` en esa
    arista (Group Edges desmarcado: cada arista con la suya)."""
    por_arista = list(por_arista)
    pedidas = [continuidad] + [c for _, c in por_arista]
    for c in pedidas:
        if c not in _CONTINUIDAD:
            raise geo.ErrorGeometria(f"Continuidad desconocida: {c} (G0, G1 o G2).")
    if any(c != "G0" for c in pedidas) and soporte is None:
        raise geo.ErrorGeometria("Tangente (G1) y curvatura (G2) necesitan aristas de un cuerpo con caras vecinas: "
                                 "elegí las aristas del contorno sobre el cuerpo (no curvas de boceto) o usá "
                                 "Conexión (G0).")
    if any(not BRep_Tool.IsClosed_s(w) for w in alambres(aristas_contorno)):
        raise geo.ErrorGeometria("El contorno no es cerrado: el parche tapa un contorno cerrado (uní los "
                                 "extremos o elegí las aristas que lo cierran).")   # B-66: antes, crudo del kernel
    interior = list(interior)
    if all(c == "G0" for c in pedidas) and not interior:
        ws = alambres(aristas_contorno)
        if len(ws) == 1 and BRep_Tool.IsClosed_s(ws[0]):
            mf = BRepBuilderAPI_MakeFace(ws[0], True)
            if mf.IsDone():
                return mf.Face()
    mapa = _mapa_aristas(soporte) if soporte is not None else None
    rel = BRepOffsetAPI_MakeFilling()
    for w in alambres(aristas_contorno):
        for e in geo._explorar(w, TopAbs_EDGE):
            e = TopoDS.Edge(e)
            vecinas = _caras_de(mapa, e) if mapa is not None else []
            cont = next((c for a, c in por_arista if a.IsSame(e)), continuidad)
            try:
                if cont != "G0":
                    if not vecinas:
                        raise geo.ErrorGeometria(
                            f"La continuidad {cont} necesita que las aristas del parche pertenezcan a las caras "
                            "del cuerpo de soporte (no se encontró la cara vecina de una arista).")
                    rel.Add(e, vecinas[0], _CONTINUIDAD[cont], True)
                else:
                    rel.Add(e, GeomAbs_C0, True)
            except geo.ErrorGeometria:
                raise
            except Exception as exc:  # noqa: BLE001 — OCC crudo («continuity is not G0 G1 or G2»): SUP-22
                raise _parche_imposible(cont) from exc
    for g in interior:
        if isinstance(g, TopoDS_Shape):
            for e in geo._explorar(g, TopAbs_EDGE):
                rel.Add(TopoDS.Edge(e), GeomAbs_C0, False)
        else:
            rel.Add(_pnt(g))
    try:
        rel.Build()
    except Exception as exc:  # noqa: BLE001 — OCC crudo («V1==V2», «continuity is not…»): SUP-1
        raise _parche_imposible(continuidad) from exc
    if not rel.IsDone():
        raise _parche_imposible(continuidad)
    return _simplificar(rel.Shape())


_rotar = geo._rotar       # rotación de Rodrigues: compartida con nucleo/construccion.py


def _extremo_de_curva(muestras, fin):
    """(punto, tangente hacia afuera, vector de curvatura) de una curva muestreada en uno de sus extremos (0 = inicio,
    1 = fin): ajuste polinómico de las últimas muestras, parametrizado por la longitud de cuerda."""
    q = (muestras[::-1] if fin == 0 else muestras)[-6:]
    sigma = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(q, axis=0), axis=1))])
    sigma -= sigma[-1]
    grado = min(4, len(q) - 1)
    coef = [np.polyfit(sigma, q[:, k], grado) for k in range(3)]
    d1 = np.array([c[-2] for c in coef])
    d2 = np.array([2 * c[-3] if grado >= 2 else 0.0 for c in coef])
    t = d1 / np.linalg.norm(d1)
    return q[-1], t, (d2 - np.dot(d2, t) * t) / np.dot(d1, d1)


def _en_arco(extremo, s):
    """Punto a longitud de arco `s` del extremo por su circunferencia osculatriz (exacta en rectas y arcos; s < 0 vuelve
    sobre la curva) y la derivada del punto respecto de `s`."""
    p, t, c = extremo
    k = np.linalg.norm(c)
    if k < 1e-9:
        return p + s * t, t
    n = c / k
    return p + np.sin(k * s) / k * t + (1 - np.cos(k * s)) / k * n, np.cos(k * s) * t + np.sin(k * s) * n


def _cruce_de_extremos(ei, ej):
    """(si, sj): largos de arco con que dos curvas se encuentran, cada una prolongada (>0) o recortada (<0) por su
    circunferencia osculatriz. Newton desde el cruce de las tangentes. None si las tangentes son paralelas o las curvas
    no se cruzan (no están en un mismo plano)."""
    if np.linalg.norm(np.cross(ei[1], ej[1])) <= 1e-6:
        return None
    s = np.linalg.lstsq(np.column_stack([ei[1], -ej[1]]), ej[0] - ei[0], rcond=None)[0]
    for _ in range(30):
        (pi, di), (pj, dj) = _en_arco(ei, s[0]), _en_arco(ej, s[1])
        paso = np.linalg.lstsq(np.column_stack([di, -dj]), pj - pi, rcond=None)[0]
        s = s + paso
        if np.linalg.norm(paso) < 1e-12:
            break
    resto = np.linalg.norm(_en_arco(ei, s[0])[0] - _en_arco(ej, s[1])[0])
    return (s[0], s[1]) if resto < 1e-6 * (1 + np.linalg.norm(ei[0] - ej[0])) else None


def _mover_extremo(muestras, extremo, s, fin):
    """La curva muestreada con su extremo `fin` llevado a longitud de arco `s` del actual: prolongada por el arco
    osculatriz o recortada (se descartan las muestras que quedan más allá)."""
    q = muestras[::-1] if fin == 0 else muestras
    if len(q) == 2:
        if s <= -np.linalg.norm(q[1] - q[0]):
            raise geo.ErrorGeometria("Las esquinas ingleteadas recortan una arista más de lo que mide: desmarcá "
                                     "«Esquinas ingleteadas» o usá una distancia menor.")
        q = np.array([q[0], _en_arco(extremo, s)[0]])
    elif s >= 0:
        q = np.vstack([q, [_en_arco(extremo, s * k / 4)[0] for k in range(1, 5)]])
    else:
        largo = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(q, axis=0), axis=1))])
        quedan = largo < largo[-1] + s - 0.25 * largo[-1] / (len(q) - 1)
        if quedan.sum() < 3:
            raise geo.ErrorGeometria("Las esquinas ingleteadas recortan una arista más de lo que mide: desmarcá "
                                     "«Esquinas ingleteadas» o usá una distancia menor.")
        q = np.vstack([q[quedan], _en_arco(extremo, s)[0]])
    return q[::-1] if fin == 0 else q


def _lejanos_ingleteados(registros, distancia):
    """Bordes lejanos de las caras regladas con las esquinas ingleteadas (Mitered Corners): en cada vértice donde se
    tocan dos aristas (rectas, arcos o curvas), los bordes lejanos de las dos caras se prolongan o se recortan por su
    propia curva hasta cortarse, y la esquina queda en ángulo vivo. Devuelve ({registro: puntos del borde lejano} solo de
    los registros que cambian, [vértices que quedaron sin cortar]): una esquina queda sin cortar si sus bordes lejanos no
    coinciden y no se cruzan (curvas que no están en un plano, tangentes paralelas) o si en ella se juntan más de dos aristas."""
    lejos = [puntos + distancia * dirs for _, _, dirs, puntos, _ in registros]
    extremos = [(_extremo_de_curva(f, 0), _extremo_de_curva(f, 1)) for f in lejos]
    por_vertice = {}
    for i, (_, _, _, puntos, _) in enumerate(registros):
        for fin in (0, 1):
            por_vertice.setdefault(tuple(np.round(puntos[-fin], 5)), []).append((i, fin))
    movidos, sin_cortar = {}, []
    for lista in por_vertice.values():
        if len(lista) < 2:
            continue
        largos = _cruce_de_extremos(extremos[lista[0][0]][lista[0][1]], extremos[lista[1][0]][lista[1][1]])             if len(lista) == 2 else None
        if largos is None:
            lejanos = np.array([extremos[k][fin][0] for k, fin in lista])
            if np.max(np.linalg.norm(lejanos - lejanos[0], axis=1)) > 1e-6:
                sin_cortar.append(registros[lista[0][0]][3][-lista[0][1]])
            continue
        for (k, fin), s in zip(lista, largos, strict=True):
            movidos[k] = _mover_extremo(movidos.get(k, lejos[k]), extremos[k][fin], s, fin)
    return movidos, sin_cortar


def _borde_por_puntos(puntos, params):
    """Arista por `puntos` con parámetros crecientes `params`: un segmento si son dos, si no una B-spline cúbica."""
    if len(puntos) == 2:
        return BRepBuilderAPI_MakeEdge(_pnt(puntos[0]), _pnt(puntos[1])).Edge()
    n_m = len(puntos)
    arr, par = Array1_gp_Pnt(1, n_m), Array1_double(1, n_m)
    for k, (pt, u) in enumerate(zip(puntos, params, strict=True)):
        arr.SetValue(k + 1, _pnt(pt))
        par.SetValue(k + 1, float(u))
    return BRepBuilderAPI_MakeEdge(GeomAPI_PointsToBSpline(arr, par, 3, 8, GeomAbs_C2, 1e-6).Curve()).Edge()


def reglada(aristas, distancia, angulo=0.0, *, tipo="normal", direccion=None, referencia=None, ingletear=False,
            alternas=False, avisos=None):
    """Superficie reglada desde aristas [SFC-RULED].

    `tipo`: "normal" (sale perpendicular a la cara de la arista), "tangente" (sigue a la cara, hacia
    afuera del material) o "direccion" (hacia `direccion`). `angulo` (grados) gira la dirección
    alrededor de la arista. `referencia`: el cuerpo que contiene las aristas (para hallar su cara) o
    un `geo.Plano` si son curvas de boceto; con plano, "tangente" va a la derecha del recorrido.
    `ingletear` (Mitered Corners): las caras de aristas (rectas, arcos o curvas) que se tocan en una esquina se cortan
    en ángulo vivo en vez de dejar cada una su borde; donde las dos curvas siguen tangentes no hay esquina que cortar. `alternas` (Alternate Faces): con una arista compartida por dos caras, usa la
    otra cara para la dirección. Sin `ingletear`, cada arista da su propia cara. `avisos`: lista donde se anota el texto
    de lo que quedó a medias (hoy, las esquinas que no se pudieron cortar)."""
    if tipo not in ("normal", "tangente", "direccion"):
        raise geo.ErrorGeometria(f"Tipo de superficie reglada desconocido: {tipo}")
    if abs(distancia) < 1e-9:
        raise geo.ErrorGeometria("La distancia de la superficie reglada no puede ser cero.")
    d_fija = None
    if tipo == "direccion":
        d_fija = _unitario(direccion if direccion is not None else (0, 0, 0), "La dirección")
    plano = referencia if isinstance(referencia, geo.Plano) else None
    mapa = _mapa_aristas(referencia) if isinstance(referencia, TopoDS_Shape) else None
    ang = math.radians(angulo)
    registros = []
    for w in alambres(aristas):
        for e in geo._explorar(w, TopAbs_EDGE):
            e = TopoDS.Edge(e)
            if BRep_Tool.Degenerated_s(e):
                continue
            ef = TopoDS.Edge(e.Oriented(TopAbs_FORWARD))
            cara = None
            if tipo != "direccion" and plano is None:
                vecinas = _caras_de(mapa, e) if mapa is not None else []
                if not vecinas:
                    raise geo.ErrorGeometria("Para 'normal' o 'tangente' indicá `referencia`: el cuerpo de la "
                                             "arista o el plano del boceto.")
                cara = vecinas[1] if alternas and len(vecinas) > 1 else vecinas[0]
                invertida = _orientacion_en(cara, e) == TopAbs_REVERSED
            else:
                invertida = False
            curva = BRepAdaptor_Curve(e)
            u0, u1 = curva.FirstParameter(), curva.LastParameter()
            recta = curva.GetType() == GeomAbs_Line
            n_m = 2 if recta and (cara is None or BRepAdaptor_Surface(cara).GetType() == GeomAbs_Plane) else 41
            params = [u0 + (u1 - u0) * i / (n_m - 1) for i in range(n_m)]
            c2d = BRepAdaptor_Curve2d(e, cara) if cara is not None else None
            sup = BRepAdaptor_Surface(cara) if cara is not None else None
            dirs, puntos = [], []
            for u in params:
                p, v = gp_Pnt(), gp_Vec()
                curva.D1(u, p, v)
                t = _unitario(_np(v), "La tangente de la arista") * (-1 if invertida else 1)
                if cara is not None:
                    uv = c2d.Value(u)
                    ps, du, dv = gp_Pnt(), gp_Vec(), gp_Vec()
                    sup.D1(uv.X(), uv.Y(), ps, du, dv)
                    n_sup = _unitario(np.cross(_np(du), _np(dv)), "La normal de la cara")
                    n_cara = -n_sup if cara.Orientation() == TopAbs_REVERSED else n_sup
                    afuera = np.cross(t, n_sup)
                elif plano is not None:
                    n_cara = plano.normal
                    afuera = np.cross(t, n_cara)
                else:
                    n_cara = afuera = None
                d0 = {"normal": n_cara, "tangente": afuera, "direccion": d_fija}[tipo]
                dirs.append(_rotar(_unitario(d0), t, ang))
                puntos.append(_np(p))
            registros.append((ef, params, np.array(dirs), np.array(puntos), recta))
    lejos, sin_cortar = _lejanos_ingleteados(registros, distancia) if ingletear else ({}, [])
    if sin_cortar and avisos is not None:
        donde = ", ".join(str([round(float(c), 3) for c in q]) for q in sin_cortar[:3]) + ("…" if len(sin_cortar) > 3 else "")
        avisos.append(f"{len(sin_cortar)} {'esquina quedó' if len(sin_cortar) == 1 else 'esquinas quedaron'} sin cortar en "
                      f"ángulo vivo (en {donde} mm): los bordes de sus caras no se cruzan en un plano, o ahí se juntan más "
                      "de dos aristas, y cada cara conserva su borde.")
    caras = []
    for i, (ef, params, dirs, puntos, _) in enumerate(registros):
        if i in lejos:
            cuerda = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(lejos[i], axis=0), axis=1))])
            otra = _borde_por_puntos(lejos[i], cuerda)
        elif np.max(np.linalg.norm(dirs - dirs[0], axis=1)) < 1e-9:
            otra = TopoDS.Edge(geo.trasladar(ef, dirs[0] * distancia))
        else:
            otra = _borde_por_puntos(puntos + distancia * dirs, params)
        # SUP-24: BRepFill sube la tolerancia de la arista de entrada (de 1e-7 a 21 mm en un tubo r5).
        # La arista es la del cuerpo de origen y la comparte el documento: se le da una copia.
        caras.append(BRepFill.Face_s(TopoDS.Edge(BRepBuilderAPI_Copy(ef).Shape()), otra))
    return _coser_caras(caras)


def direccion_reglada(arista, referencia, tipo, angulo=0.0):
    """Dirección unitaria con la que `reglada` sale de `arista` en su punto medio (la flecha de distancia del comando).
    None si `tipo` es «direccion» (la fija el usuario) o la arista no tiene cara vecina ni plano."""
    if tipo not in ("normal", "tangente"):
        return None
    plano = referencia if isinstance(referencia, geo.Plano) else None
    arista = TopoDS.Edge(arista)
    cara, invertida = None, False
    if plano is None:
        vecinas = _caras_de(_mapa_aristas(referencia), arista) if isinstance(referencia, TopoDS_Shape) else []
        if not vecinas:
            return None
        cara = vecinas[0]
        invertida = _orientacion_en(cara, arista) == TopAbs_REVERSED
    curva = BRepAdaptor_Curve(arista)
    u = (curva.FirstParameter() + curva.LastParameter()) / 2
    p, v = gp_Pnt(), gp_Vec()
    curva.D1(u, p, v)
    t = _unitario(_np(v), "La tangente de la arista") * (-1 if invertida else 1)
    if cara is not None:
        uv = BRepAdaptor_Curve2d(arista, cara).Value(u)
        ps, du, dv = gp_Pnt(), gp_Vec(), gp_Vec()
        BRepAdaptor_Surface(cara).D1(uv.X(), uv.Y(), ps, du, dv)
        n_sup = _unitario(np.cross(_np(du), _np(dv)), "La normal de la cara")
        n_cara, afuera = (-n_sup if cara.Orientation() == TopAbs_REVERSED else n_sup), np.cross(t, n_sup)
    else:
        n_cara = plano.normal
        afuera = np.cross(t, n_cara)
    return _rotar(_unitario(n_cara if tipo == "normal" else afuera), t, math.radians(angulo))


def _desfase_imposible(original, resultado, distancia, *, engrosado=False):
    """True si el kernel no dejó cada cara desfasada a `distancia` de `original`. Pasa cuando la distancia supera el
    radio de curvatura del lado del desfase: la superficie se da vuelta por el centro (un cilindro de radio 10
    desfasado 12 mm hacia adentro quedaba de radio 2, a 8 mm del original) o se reduce a una línea (desfasado 10 mm).
    En un engrosado también valen las caras que tocan el original (la de partida y los bordes)."""
    d = abs(distancia)
    if geo.area(resultado) <= 1e-6 * geo.area(original):
        return True
    if not engrosado and geo.solidos(original) and \
            geo.volumen_exacto(resultado) <= 1e-9 * abs(geo.volumen_exacto(original)):
        return True             # un cuerpo desfasado hasta la mitad de su grosor queda chato (o «al revés»)
    borde = geo.compuesto(geo.caras(original))     # la superficie, no el sólido: adentro de un sólido la distancia es 0
    for cara in geo.caras(resultado):
        medida = BRepExtrema_DistShapeShape(cara, borde)
        medida.Perform()
        if not medida.IsDone():
            continue
        x = medida.Value()
        if x < d * (1 - 1e-3) - 1e-6 and not (engrosado and x <= 1e-4 * max(1.0, d)):
            return True
    return False


def desfasar_superficie(forma, distancia, *, tipo="agudo"):
    """Superficie desfasada [SFC-OFFSET] (BRepOffsetAPI_MakeOffsetShape). Distancia positiva = hacia
    la normal. `tipo`: "agudo" (Sharp Offset) o "redondeado" (Rounded Offset)."""
    if abs(distancia) < 1e-9:
        raise geo.ErrorGeometria("La distancia de desfase no puede ser cero.")
    junta = {"agudo": GeomAbs_Intersection, "redondeado": GeomAbs_Arc}.get(tipo)
    if junta is None:
        raise geo.ErrorGeometria(f"Tipo de desfase desconocido: {tipo}")
    off = BRepOffsetAPI_MakeOffsetShape()
    off.PerformByJoin(forma, float(distancia), 1e-6, BRepOffset_Skin, False, False, junta)
    if not off.IsDone():
        raise geo.ErrorGeometria("El desfase falló (¿la distancia supera el radio de curvatura?).")
    resultado = None if off.Shape().IsNull() else _simplificar(off.Shape())
    from . import revision                  # local: revision carga medio núcleo
    # B-171: un desfase enorme puede cruzarse consigo mismo sin que lo vea _desfase_imposible
    if (resultado is None or _desfase_imposible(forma, resultado, distancia)
            or revision._autointersecciones_seguras(resultado, 1, 5.0)[0]):
        raise geo.ErrorGeometria(f"El desfase falló: con {abs(distancia):g} mm la superficie se cruza consigo misma "
                                 "(la distancia es igual o mayor que su radio de curvatura de ese lado, o que la mitad "
                                 "del grosor del cuerpo). Probá una distancia menor.")
    return resultado


def primitiva_superficie(solido):
    """Primitivas de superficie [SFC-BOX … SFC-COIL]: el cascarón (caras) de un sólido primitivo
    (geo.caja, geo.cilindro, geo.esfera, geo.toroide o una espiral sólida)."""
    cascarones = [TopoDS.Shell(BRepBuilderAPI_Copy(s).Shape()) for s in geo._explorar(solido, TopAbs_SHELL)]
    if not cascarones:
        raise geo.ErrorGeometria("La forma no tiene cascarones.")
    return _juntar(cascarones)


def _filetear_cantos(forma, aristas, valor, clase_api, sustantivo, parametro):
    """Empalme (MakeFillet) o chaflán (MakeChamfer) de aristas: misma mecánica, cambia la clase OCC [SFC-FILLET-CHAMFER]."""
    if valor <= 0:
        raise geo.ErrorGeometria(f"El {parametro} del {sustantivo} debe ser positivo.")
    op = clase_api(forma)
    mapa = _mapa_aristas(forma)
    for e in _formas(aristas):
        if len(_caras_de(mapa, TopoDS.Edge(e))) < 2:
            raise geo.ErrorGeometria(f"La arista es libre (la toca una sola cara): el {sustantivo} necesita una arista "
                                     "compartida por dos caras.")
        if clase_api is BRepFilletAPI_MakeFillet:
            geo.rechazar_radio_de_arco(TopoDS.Edge(e), float(valor))
        op.Add(float(valor), TopoDS.Edge(e))
    # OCC lanza Standard_Failure con mensajes poco útiles
    try:
        op.Build()
    except Exception as exc:  # noqa: BLE001
        raise geo.ErrorGeometria(f"El {sustantivo} falló (¿{parametro} demasiado grande?).") from exc
    if not op.IsDone():
        raise geo.ErrorGeometria(f"El {sustantivo} falló (¿{parametro} demasiado grande o arista libre?).")
    return _simplificar(op.Shape())


def empalme_superficie(forma, aristas, radio):
    """Empalme (Fillet) de aristas compartidas por dos caras de un cuerpo de superficie [SFC-FILLET-CHAMFER]."""
    return _filetear_cantos(forma, aristas, radio, BRepFilletAPI_MakeFillet, "empalme", "radio")


def chaflan_superficie(forma, aristas, distancia):
    """Chaflán de distancia igual en aristas de un cuerpo de superficie [SFC-FILLET-CHAMFER]."""
    return _filetear_cantos(forma, aristas, distancia, BRepFilletAPI_MakeChamfer, "chaflán", "distancia")


# ---------------------------------------------------------------- modificar
def _herramienta(herramienta, forma):
    if isinstance(herramienta, geo.Plano):
        return _cara_plana_grande(herramienta, _tam_referencia(forma))
    if isinstance(herramienta, TopoDS_Shape):
        return herramienta
    return geo.compuesto(_formas(herramienta))


def regiones_recorte(forma, herramienta):
    """Parte la superficie con la herramienta (superficie, `geo.Plano` o aristas) y devuelve las
    regiones resultantes, cada una como cara o cascarón (para elegir cuál quitar)."""
    tool = _herramienta(herramienta, forma)
    sp = BRepAlgoAPI_Splitter()
    args, tools = List_TopoDS_Shape(), List_TopoDS_Shape()
    args.Append(forma)
    tools.Append(tool)
    sp.SetArguments(args)
    sp.SetTools(tools)
    sp.Build()
    if not sp.IsDone():
        raise geo.ErrorGeometria("No se pudo partir la superficie con la herramienta.")
    caras = geo.caras(sp.Shape())
    # Regiones = caras conectadas por aristas que NO están sobre la herramienta (las del corte separan).
    mapa = _mapa_aristas(sp.Shape())
    padre = list(range(len(caras)))

    def raiz(i):
        while padre[i] != i:
            padre[i] = padre[padre[i]]
            i = padre[i]
        return i

    def pos(cara):
        return next(i for i in range(len(caras)) if caras[i].IsSame(cara))

    for k in range(1, mapa.Extent() + 1):
        arista = TopoDS.Edge(mapa.FindKey(k))
        vecinas = [TopoDS.Face(f) for f in geo.lista_occ(mapa.FindFromIndex(k))]
        if len(vecinas) < 2:
            continue
        curva = BRepAdaptor_Curve(arista)
        medio = curva.Value((curva.FirstParameter() + curva.LastParameter()) / 2)
        dist = BRepExtrema_DistShapeShape(BRepBuilderAPI_MakeVertex(medio).Vertex(), tool)
        if dist.IsDone() and dist.Value() < 1e-5:
            continue
        a = pos(vecinas[0])
        for f in vecinas[1:]:
            padre[raiz(pos(f))] = raiz(a)
    grupos = {}
    for i, c in enumerate(caras):
        grupos.setdefault(raiz(i), []).append(c)
    return [_coser_caras(g) for g in grupos.values()]


def recortar(forma, herramienta, punto_a_quitar):
    """Recorte [SFC-TRIM]: parte la superficie con la herramienta y quita la región más cercana a
    `punto_a_quitar` (el clic del usuario sobre la parte a eliminar)."""
    regiones = regiones_recorte(forma, herramienta)
    if len(regiones) < 2:
        raise geo.ErrorGeometria("La herramienta no corta la superficie.")
    v = BRepBuilderAPI_MakeVertex(_pnt(punto_a_quitar)).Vertex()
    distancias = [BRepExtrema_DistShapeShape(v, r).Value() for r in regiones]
    quitar = int(np.argmin(distancias))
    return _coser_caras([c for i, r in enumerate(regiones) if i != quitar for c in geo.caras(r)])


def _limites_naturales(cara):
    """Límites UV de la superficie; donde es infinita (plano, cilindro en v) se usan los de la cara."""
    sup = BRep_Tool.Surface_s(cara)
    nu0, nu1, nv0, nv1 = sup.Bounds()
    cu0, cu1, cv0, cv1 = BRepTools.UVBounds_s(cara)
    infinito = 1e50
    return (cu0 if nu0 < -infinito else nu0, cu1 if nu1 > infinito else nu1,
            cv0 if nv0 < -infinito else nv0, cv1 if nv1 > infinito else nv1), sup


def cara_original(cara, antes):
    """La cara del cuerpo `antes` (previo a un recorte) que contiene a `cara`; None si no está.

    Destrimar necesita los límites de la cara SIN recortar: en una superficie infinita la cara recortada
    ya no los guarda (SUP-5). Se busca con un punto del medio UV de la cara recortada."""
    if antes is None:
        return None
    u0, u1, v0, v1 = BRepTools.UVBounds_s(cara)
    p = BRep_Tool.Surface_s(cara).Value((u0 + u1) / 2, (v0 + v1) / 2)
    for otra in geo.caras(antes):
        if BRepClass_FaceClassifier(otra, p, 1e-6).State() in (TopAbs_IN, TopAbs_ON):
            return otra
    return None


def _misma_arista(a, b):
    """Dos aristas que son la misma curva aunque vengan de formas distintas (la cara original y la recortada)."""
    ca, cb = BRepAdaptor_Curve(a), BRepAdaptor_Curve(b)
    pa = _np(ca.Value((ca.FirstParameter() + ca.LastParameter()) / 2))
    pb = _np(cb.Value((cb.FirstParameter() + cb.LastParameter()) / 2))
    return bool(np.linalg.norm(pa - pb) < 1e-5)


def destrimar(cara, *, contornos="exteriores", aristas=(), extension=0.0, original=None):
    """Destrimado [SFC-UNTRIM]: rehace la cara con los límites naturales de su superficie.

    "exteriores" (External Edges): el borde exterior vuelve al límite natural, se conservan agujeros.
    "interiores" (Internal Edges): solo se tapan los agujeros. "todos" (All Edges): ambas cosas.
    "manual" (Manual): solo los contornos de la cara a los que pertenece alguna de `aristas` (un agujero se tapa; el
    exterior vuelve al límite natural). `extension` (Extend, mm): estira los bordes exteriores del resultado.
    En superficies infinitas (plano; cilindro a lo largo del eje) el límite natural es el rectángulo
    UV que encierra la cara. `original`: la cara antes de un recorte; de ella salen los límites naturales (los
    contornos y las aristas elegidas siguen siendo los de `cara`)."""
    if contornos not in ("exteriores", "interiores", "todos", "manual"):
        raise geo.ErrorGeometria(f"Tipo de destrimado desconocido: {contornos}")
    if extension < 0:
        raise geo.ErrorGeometria("La distancia de extensión no puede ser negativa.")
    cara = TopoDS.Face(cara)
    adelante = TopoDS.Face(cara.Oriented(TopAbs_FORWARD))
    exterior = BRepTools.OuterWire_s(adelante)
    interiores = [TopoDS.Wire(w) for w in geo._explorar(adelante, TopAbs_WIRE) if not w.IsSame(exterior)]
    (u0, u1, v0, v1), sup = _limites_naturales(adelante if original is None else TopoDS.Face(original.Oriented(TopAbs_FORWARD)))
    natural = contornos != "interiores"
    if contornos == "manual":
        elegidas = [TopoDS.Edge(a) for a in _formas(aristas)]
        if not elegidas:
            raise geo.ErrorGeometria("En el modo manual elegí las aristas a destrimar.")

        def elegido(w):
            return any(_misma_arista(TopoDS.Edge(e), a) for e in geo._explorar(w, TopAbs_EDGE) for a in elegidas)

        natural = elegido(exterior)
        tapados = [w for w in interiores if elegido(w)]
        if not natural and not tapados:
            raise geo.ErrorGeometria("Ninguna de las aristas elegidas es un borde de la cara.")
        quedan = [w for w in interiores if not any(w.IsSame(t) for t in tapados)]
    else:
        quedan = interiores if contornos == "exteriores" else []
    mf = BRepBuilderAPI_MakeFace(sup, u0, u1, v0, v1, 1e-7) if natural else BRepBuilderAPI_MakeFace(sup, exterior, True)
    if not mf.IsDone():
        raise geo.ErrorGeometria("No se pudo rehacer la cara.")

    def arreglada(c):
        arreglo = ShapeFix_Face(c)
        arreglo.Perform()
        return arreglo.Face()

    nueva = arreglada(mf.Face())
    if extension > 1e-9:               # se estira sin agujeros: `extender` rehace la cara y se los llevaría puestos
        mapa = _mapa_aristas(nueva)           # la costura de un cilindro pertenece dos veces a la misma cara: no es un borde libre
        libres = [e for e in geo._explorar(BRepTools.OuterWire_s(nueva), TopAbs_EDGE)
                  if len(_caras_de(mapa, TopoDS.Edge(e))) == 1]
        nueva = extender(nueva, libres, extension)
    if quedan:
        mf = BRepBuilderAPI_MakeFace(TopoDS.Face(nueva))
        for w in quedan:
            mf.Add(w)
        nueva = arreglada(mf.Face())
    return TopoDS.Face(nueva.Reversed()) if cara.Orientation() == TopAbs_REVERSED else TopoDS.Face(nueva)


def _lado_iso(cara, arista, limites):
    """Qué borde iso-paramétrico de la cara es la arista: ("u"|"v", "min"|"max") o None."""
    u0, u1, v0, v1 = limites
    c2d = BRepAdaptor_Curve2d(arista, cara)
    pts = [c2d.Value(c2d.FirstParameter() + (c2d.LastParameter() - c2d.FirstParameter()) * k / 4) for k in range(5)]
    tol = 1e-6 * max(1.0, abs(u1 - u0), abs(v1 - v0))
    for lado, val, comp in (("u", u0, "min"), ("u", u1, "max"), ("v", v0, "min"), ("v", v1, "max")):
        if all(abs((p.X() if lado == "u" else p.Y()) - val) < tol for p in pts):
            return lado, comp
    return None


def _extension_libre(cara, arista, distancia, pasos=8, muestras=41):
    """Franja de `distancia` mm, medida sobre la superficie, más allá de un borde libre de una cara que no es plana
    (Extend › Natural › Free Edges, G0): de cada punto del borde se avanza por la superficie, hacia afuera de la cara y
    perpendicular al borde, siguiendo la geodésica (paso de punto medio; en cada paso la dirección se proyecta al plano
    tangente nuevo). Los puntos están sobre la superficie de la cara, así que la franja la prolonga con borde lateral
    libre. Una superficie acotada (B-spline) se prolonga antes con `BRepLib.ExtendFace`; si aun así se pliega (la de un
    parche de relleno), la franja es plana y tangente a la cara. Se arma con secciones (la primera es la arista real,
    para que cosa con la cara) y devuelve una forma."""
    ef = TopoDS.Edge(arista.Oriented(TopAbs_FORWARD))
    curva, c2d = BRepAdaptor_Curve(ef), BRepAdaptor_Curve2d(ef, cara)
    params = np.linspace(curva.FirstParameter(), curva.LastParameter(), muestras)
    surf = BRep_Tool.Surface_s(cara)
    marcha = surf
    if surf.DynamicType().Name() not in _SUPERFICIES_SIN_LIMITE:
        ampliada = TopoDS_Face()
        BRepLib.ExtendFace_s(cara, 2.0 * distancia, True, True, True, True, ampliada)
        if ampliada.IsNull():
            raise geo.ErrorGeometria("No se pudo prolongar la superficie de la cara para extenderla.")
        marcha = BRep_Tool.Surface_s(ampliada)          # conserva la parametrización: los (u, v) de la cara valen

    def marco(s, u, v):
        p, du, dv = gp_Pnt(), gp_Vec(), gp_Vec()
        s.D1(float(u), float(v), p, du, dv)
        return _np(p), np.column_stack([_np(du), _np(dv)])

    def normal(j):
        return _unitario(np.cross(j[:, 0], j[:, 1]), "La normal de la cara")

    def por_mm(j, w):                         # el desplazamiento (u, v) que mueve el punto 1 mm en la dirección w
        return np.linalg.lstsq(j, w, rcond=None)[0]

    arranques = []
    for u in params:
        uv = c2d.Value(float(u))
        p, j = marco(surf, uv.X(), uv.Y())
        v, t = gp_Pnt(), gp_Vec()
        curva.D1(float(u), v, t)
        w = _unitario(np.cross(normal(j), _np(t)), "La tangente de la arista")
        arranques.append((np.array([uv.X(), uv.Y()]), p, w, por_mm(j, w)))
    uv_c, _, _, desplazo = arranques[len(arranques) // 2]
    hacia_adentro = BRepClass_FaceClassifier(cara, gp_Pnt2d(*(uv_c + 1e-3 * distancia * desplazo)), 1e-7).State() == TopAbs_IN
    filas = [[a[1] for a in arranques]]
    estados = [(a[0], a[2] * (-1 if hacia_adentro else 1)) for a in arranques]
    for _ in range(pasos):
        fila = []
        for k, (uv, w) in enumerate(estados):
            h = distancia / pasos
            _, j = marco(marcha, *uv)
            _, j_medio = marco(marcha, *(uv + por_mm(j, w) * h / 2))        # punto medio: paso de segundo orden
            w_medio = _unitario(w - np.dot(w, normal(j_medio)) * normal(j_medio), "La dirección de la extensión")
            uv = uv + por_mm(j_medio, w_medio) * h
            p, j = marco(marcha, *uv)
            estados[k] = (uv, _unitario(w_medio - np.dot(w_medio, normal(j)) * normal(j), "La dirección de la extensión"))
            fila.append(p)
        paso = np.linalg.norm(np.array(fila) - np.array(filas[-1]), axis=1)
        if not np.all((paso > 0.8 * distancia / pasos) & (paso < 1.2 * distancia / pasos)):
            # shortcut: franja plana tangente si la B-spline de relleno se pliega fuera de sus límites, prolongar su relleno.
            return reglada([arista], distancia, tipo="tangente", referencia=cara)
        filas.append(fila)
    ts = BRepOffsetAPI_ThruSections(False, False)
    ts.AddWire(BRepBuilderAPI_MakeWire(ef).Wire())
    for fila in filas[1:]:
        ts.AddWire(BRepBuilderAPI_MakeWire(_borde_por_puntos(np.array(fila), params)).Wire())
    ts.Build()
    if not ts.IsDone():
        raise geo.ErrorGeometria("No se pudo extender la cara curva con alineación libre: probá con una distancia "
                                 "menor o con extensión tangente.")
    return ts.Shape()


def extender(forma, aristas, distancia, *, tipo="natural", alineacion="alinear"):
    """Extensión de bordes libres de una superficie [SFC-EXTEND].

    "natural": agranda la misma cara (plano y cilindro exactos; otras superficies con
    BRepLib.ExtendFace). Solo bordes iso-paramétricos de caras rectangulares en UV.
    "tangente": agrega caras planas tangentes a la cara (como reglada tangente).
    "perpendicular": agrega caras perpendiculares a la cara (como reglada normal).
    `alineacion` (Edge Alignment, solo "natural"): "alinear" (Align Edges, G1) exige que la extensión siga los lados de
    la cara (borde iso-paramétrico de una cara rectangular en UV); "libre" (Free Edges, G0) además admite una cara que
    no es rectangular: plana, el borde se extiende con una cara plana tangente de bordes laterales libres; curva, con una
    franja sobre su propia superficie (`_extension_libre`)."""
    if alineacion not in ("libre", "alinear"):
        raise geo.ErrorGeometria(f"Alineación de bordes desconocida: {alineacion} (libre o alinear).")
    if distancia <= 0:
        raise geo.ErrorGeometria("La distancia de extensión debe ser positiva.")
    if tipo in ("tangente", "perpendicular"):
        nuevas = reglada(aristas, distancia, tipo="tangente" if tipo == "tangente" else "normal", referencia=forma)
        return _coser_caras(geo.caras(forma) + geo.caras(nuevas))
    if tipo != "natural":
        raise geo.ErrorGeometria(f"Tipo de extensión desconocido: {tipo}")
    mapa = _mapa_aristas(forma)
    pedidos = {}   # índice de cara → (cara, set de lados)
    caras = geo.caras(forma)
    sueltas = []   # alineación libre: bordes de caras planas no rectangulares, extendidos con caras tangentes
    curvas = []    # alineación libre: (cara, borde) de caras curvas no rectangulares, extendidos sobre su superficie
    for e in _formas(aristas):
        e = TopoDS.Edge(e)
        vecinas = _caras_de(mapa, e)
        if len(vecinas) != 1:
            raise geo.ErrorGeometria("Solo se extienden aristas libres (bordes de una sola cara).")
        cara = vecinas[0]
        limites = BRepTools.UVBounds_s(cara)
        lado = _lado_iso(cara, e, limites)
        rectangular = lado is not None and all(
            _lado_iso(cara, TopoDS.Edge(otra), limites) is not None
            for otra in geo._explorar(BRepTools.OuterWire_s(cara), TopAbs_EDGE))
        if not rectangular:
            if alineacion == "libre":
                if BRepAdaptor_Surface(cara).GetType() == GeomAbs_Plane:
                    sueltas.append(e)
                else:
                    curvas.append((cara, e))
                continue
            raise geo.ErrorGeometria(
                "La cara no es rectangular en su parametrización: no se puede extender en forma natural; probá con "
                "alineación libre, o con extensión tangente o perpendicular.")
        k = next(i for i, c in enumerate(caras) if c.IsSame(cara))
        pedidos.setdefault(k, (cara, set()))[1].add(lado)
    reemplazos = {}
    for k, (cara, lados) in pedidos.items():
        sup = BRepAdaptor_Surface(cara)
        u0, u1, v0, v1 = BRepTools.UVBounds_s(cara)
        if sup.GetType() in (GeomAbs_Plane, GeomAbs_Cylinder):
            du = distancia if sup.GetType() == GeomAbs_Plane else distancia / sup.Cylinder().Radius()
            dv = distancia
            u0 -= du if ("u", "min") in lados else 0.0
            u1 += du if ("u", "max") in lados else 0.0
            v0 -= dv if ("v", "min") in lados else 0.0
            v1 += dv if ("v", "max") in lados else 0.0
            if u1 - u0 > 2 * math.pi + 1e-9 and sup.GetType() == GeomAbs_Cylinder:
                raise geo.ErrorGeometria("La extensión da más de una vuelta completa del cilindro.")
            nueva = BRepBuilderAPI_MakeFace(BRep_Tool.Surface_s(cara), u0, u1, v0, v1, 1e-7).Face()
        else:
            nueva = TopoDS_Face()
            BRepLib.ExtendFace_s(cara, float(distancia), ("u", "min") in lados, ("u", "max") in lados,
                                 ("v", "min") in lados, ("v", "max") in lados, nueva)
            if nueva.IsNull():
                raise geo.ErrorGeometria("No se pudo extender la cara.")
        if cara.Orientation() == TopAbs_REVERSED:
            nueva = TopoDS.Face(nueva.Reversed())
        reemplazos[k] = nueva
    extra = geo.caras(reglada(sueltas, distancia, tipo="tangente", referencia=forma)) if sueltas else []
    for cara, e in curvas:
        try:
            extra += geo.caras(_extension_libre(cara, e, distancia))
        except geo.ErrorGeometria:
            raise
        except Exception as exc:  # noqa: BLE001 — OCC crudo («out of range»…) o numérico: se dice qué probar
            raise geo.ErrorGeometria(
                "No se pudo extender la cara curva con alineación libre: la superficie no se puede prolongar más allá de "
                "su borde. Probá con extensión tangente o perpendicular.") from exc
    return _coser_caras([reemplazos.get(i, c) for i, c in enumerate(caras)] + extra)


def coser(formas, tolerancia=0.01):
    """Coser superficies [SFC-STITCH] (BRepBuilderAPI_Sewing). Si el resultado queda cerrado
    (estanco) se convierte en sólido, como Fusion. Devuelve {"forma", "es_solido", "aristas_libres", "libres_en",
    "aristas_cosidas"}; `libres_en` son los puntos medios (mm) de los bordes que quedaron libres (hasta 20), para saber
    cuáles son, y `aristas_cosidas` cuántas aristas entraron en la tolerancia."""
    if not math.isfinite(tolerancia) or tolerancia <= 0:
        raise geo.ErrorGeometria(f"La tolerancia de costura tiene que ser mayor que 0 mm; recibió {tolerancia:g} mm.")
    cos = BRepBuilderAPI_Sewing(float(tolerancia))
    for f in _formas(formas):
        cos.Add(f)
    cos.Perform()
    cosido = _simplificar(cos.SewedShape())
    libres, cosidas = cos.NbFreeEdges(), cos.NbContigousEdges()
    cascarones = [TopoDS.Shell(s) for s in geo._explorar(cosido, TopAbs_SHELL)]
    if libres == 0 and cascarones and all(BRep_Tool.IsClosed_s(s) for s in cascarones):
        solidos = []
        for s in cascarones:
            sol = BRepBuilderAPI_MakeSolid(s).Solid()
            BRepLib.OrientClosedSolid_s(sol)
            solidos.append(sol)
        return {"forma": _juntar(solidos), "es_solido": True, "aristas_libres": 0, "libres_en": [],
                "aristas_cosidas": cosidas}
    return {"forma": cosido, "es_solido": False, "aristas_libres": libres, "libres_en": _bordes_libres(cosido)[:20],
            "aristas_cosidas": cosidas}


def coser_previa(formas, tolerancia=0.01):
    """Lo que daría `coser`, sobre copias: no toca las formas del documento (sirve para mostrar los bordes libres)."""
    return coser([BRepBuilderAPI_Copy(f).Shape() for f in _formas(formas)], tolerancia)


def _polilinea(arista, n=25):
    curva = BRepAdaptor_Curve(arista)
    a, z = curva.FirstParameter(), curva.LastParameter()
    return np.array([_np(curva.Value(a + (z - a) * i / (n - 1))) for i in range(n)])


def _distancia_a_tramos(puntos, a, b):
    """Para cada punto, la distancia al segmento más cercano de los segmentos a[i]-b[i]."""
    ab = b - a
    t = np.clip(np.einsum("ijk,jk->ij", puntos[:, None] - a, ab) / np.maximum(np.einsum("ij,ij->i", ab, ab), 1e-18), 0.0, 1.0)
    return np.min(np.linalg.norm(puntos[:, None] - (a + t[..., None] * ab), axis=2), axis=1)


# Tope de filas de la tabla de bordes.
BORDES_MAXIMOS = 200


def bordes_de_costura(formas, tolerancia=0.01):
    """Lo que dibuja y lista el comando Coser [SFC-STITCH], sobre copias de `formas`:
    {"es_solido", "libres": [{"punto", "largo", "hueco", "polilinea"}], "total_libres", "cosidas": [polilíneas],
    "aristas_cosidas"}. `libres` (Unstitched Edges, hasta BORDES_MAXIMOS): cada borde abierto con su punto medio, su largo
    y su hueco: cuánto se aleja, en el peor punto, de los demás bordes libres que no se tocan con él (la tolerancia que
    haría falta para cerrarlo; None si no hay otro). `cosidas`: las aristas dentro de la tolerancia (verde en Fusion)."""
    if not math.isfinite(tolerancia) or tolerancia <= 0:
        raise geo.ErrorGeometria(f"La tolerancia de costura tiene que ser mayor que 0 mm; recibió {tolerancia:g} mm.")
    cos = BRepBuilderAPI_Sewing(float(tolerancia))
    for f in _formas(formas):
        cos.Add(BRepBuilderAPI_Copy(f).Shape())
    cos.Perform()
    cosido = cos.SewedShape()
    mapa = _mapa_aristas(cosido)
    aristas = [TopoDS.Edge(mapa.FindKey(k)) for k in range(1, mapa.Extent() + 1)
               if len(geo.lista_occ(mapa.FindFromIndex(k))) == 1 and not BRep_Tool.Degenerated_s(TopoDS.Edge(mapa.FindKey(k)))]
    polilineas = [_polilinea(e) for e in aristas[:BORDES_MAXIMOS]]
    libres = []
    for i, poli in enumerate(polilineas):
        otras = [o for j, o in enumerate(polilineas) if j != i and min(np.linalg.norm(o[[0, -1]] - x, axis=1).min() for x in poli[[0, -1]]) > 1e-6]
        hueco = None
        if otras:
            a, b = np.vstack([o[:-1] for o in otras]), np.vstack([o[1:] for o in otras])
            hueco = float(np.max(_distancia_a_tramos(poli[::4], a, b)))
        libres.append({"punto": [round(float(x), 3) for x in poli[len(poli) // 2]], "polilinea": poli, "hueco": hueco,
                       "largo": float(np.sum(np.linalg.norm(np.diff(poli, axis=0), axis=1)))})
    cosidas = [_polilinea(TopoDS.Edge(cos.ContigousEdge(i))) for i in range(1, cos.NbContigousEdges() + 1)]
    cascarones = [TopoDS.Shell(s) for s in geo._explorar(cosido, TopAbs_SHELL)]
    return {"es_solido": not aristas and bool(cascarones) and all(BRep_Tool.IsClosed_s(s) for s in cascarones),
            "libres": libres, "total_libres": len(aristas), "cosidas": cosidas, "aristas_cosidas": len(cosidas)}


def _bordes_libres(forma):
    """Puntos medios de las aristas de `forma` que pertenecen a una sola cara (los bordes abiertos)."""
    mapa = _mapa_aristas(forma)
    medios = []
    for k in range(1, mapa.Extent() + 1):
        if len(geo.lista_occ(mapa.FindFromIndex(k))) == 1:
            curva = BRepAdaptor_Curve(TopoDS.Edge(mapa.FindKey(k)))
            medios.append([round(float(x), 3) for x in _np(curva.Value((curva.FirstParameter() + curva.LastParameter()) / 2))])
    return medios


def descoser(forma):
    """Descoser [SFC-UNSTITCH]: separa un cuerpo (de superficie o sólido) en caras sueltas
    independientes (cada una con sus propias aristas)."""
    return [TopoDS.Face(BRepBuilderAPI_Copy(c).Shape()) for c in geo.caras(forma)]


def descoser_caras(forma, caras):
    """Descoser caras elegidas [SFC-UNSTITCH]: (resto, sueltas). `sueltas` son las caras de `caras` que pertenecen a
    `forma`, cada una por separado; `resto` es lo que queda del cuerpo cosido (None si no queda nada)."""
    todas = geo.caras(forma)
    elegidas = [c for c in todas if any(c.IsSame(x) for x in caras)]
    if not elegidas:
        raise geo.ErrorGeometria("Las caras elegidas no pertenecen al cuerpo.")
    resto = [c for c in todas if not any(c.IsSame(x) for x in elegidas)]
    return (_coser_caras(resto) if resto else None), [TopoDS.Face(BRepBuilderAPI_Copy(c).Shape()) for c in elegidas]


def invertir_normal(forma):
    """Invertir normal [GUID-3B2D0A04-B93C-4F63-9512-00D91F042C2D]: cambia el lado positivo de una
    superficie (no aplica a sólidos: su normal siempre apunta afuera)."""
    if any(True for _ in geo._explorar(forma, TopAbs_SOLID)):
        raise geo.ErrorGeometria("Invertir normal es solo para cuerpos de superficie.")
    return _tipado(forma.Reversed())


def normal_muestra(forma):
    """(punto, normal) sobre la primera cara de una superficie: la normal apunta al lado positivo (hacia donde van
    Desfase y Engrosar con distancia positiva). El punto está sobre la cara aunque esté recortada."""
    cara = geo.caras(forma)[0]
    u0, u1, v0, v1 = BRepTools.UVBounds_s(cara)
    sup = BRepAdaptor_Surface(cara)
    ps, du, dv = gp_Pnt(), gp_Vec(), gp_Vec()
    for k in range(25):                                 # el medio UV primero; si cae fuera de la cara, una grilla
        u = (u0 + u1) / 2 if k == 0 else u0 + (u1 - u0) * ((k % 5) + 0.5) / 5
        v = (v0 + v1) / 2 if k == 0 else v0 + (v1 - v0) * ((k // 5) + 0.5) / 5
        if BRepClass_FaceClassifier(cara, BRep_Tool.Surface_s(cara).Value(u, v), 1e-6).State() == TopAbs_IN:
            break
    sup.D1(u, v, ps, du, dv)
    n = _unitario(np.cross(_np(du), _np(dv)), "La normal de la cara")
    return _np(ps), -n if cara.Orientation() == TopAbs_REVERSED else n


def engrosar_superficie(forma, espesor, *, simetrica=False, tipo="agudo"):
    """Engrosar [GUID-471827A2-EDAE-411B-A1F5-C87B54615D53]: sólido a partir de una superficie.

    Espesor positivo crece hacia la normal, negativo hacia el otro lado. `simetrica`: mitad del
    espesor para cada lado. `tipo`: "agudo" (Sharp Thicken) o "redondeado" (Rounded Thicken)."""
    if abs(espesor) < 1e-9:
        raise geo.ErrorGeometria("El espesor no puede ser cero.")
    junta = {"agudo": GeomAbs_Intersection, "redondeado": GeomAbs_Arc}.get(tipo)
    if junta is None:
        raise geo.ErrorGeometria(f"Tipo de engrosado desconocido: {tipo}")
    if simetrica and tipo == "redondeado":
        # Desfasar −t/2 con juntas en arco y engrosar t después invierte esos arcos y OCC no da un sólido: se
        # engrosa cada mitad por su lado (esquina de afuera redondeada con radio t/2) y se unen.
        mitades = [engrosar_superficie(forma, s * abs(espesor) / 2, tipo=tipo) for s in (1, -1)]
        return _simplificar(geo.booleano(mitades[0], mitades[1], "unir"))
    base = _simplificar(forma)
    if base.ShapeType() == TopAbs_COMPOUND:
        base = _coser_caras(geo.caras(base))
    if simetrica:
        base = desfasar_superficie(base, -abs(espesor) / 2, tipo=tipo)
        espesor = abs(espesor)
    op = BRepOffset_MakeOffset()
    op.Initialize(base, float(espesor), 1e-6, BRepOffset_Skin, False, False, junta, True, False)
    op.MakeOffsetShape()
    if not op.IsDone() or op.Shape().IsNull():
        raise geo.ErrorGeometria("No se pudo engrosar (¿el espesor supera el radio de curvatura?).")
    resultado = _simplificar(op.Shape())
    if not geo.solidos(resultado):
        raise geo.ErrorGeometria("El engrosado no produjo un sólido.")
    # Más grueso que el radio de curvatura, el kernel daba «ok» con un sólido inválido (cilindro de radio 10 engrosado
    # 10 hacia adentro), dado vuelta por el eje (12 mm: un tubo de radio 2 a 10) o con volumen negativo (25 mm).
    if (not geo.es_valida(resultado) or geo.volumen_exacto(resultado) <= 0
            or _desfase_imposible(base, resultado, espesor, engrosado=True)):
        raise geo.ErrorGeometria(f"No se pudo engrosar: {abs(espesor):g} mm es igual o mayor que el radio de "
                                 "curvatura de la superficie de ese lado. Probá un espesor menor o engrosar hacia el "
                                 "otro lado.")
    return resultado


_motor.registrar(globals(), _iniciar_opencascade)

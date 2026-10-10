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
from OCP.BRep import BRep_Tool
from OCP.BRepAdaptor import BRepAdaptor_CompCurve, BRepAdaptor_Curve, BRepAdaptor_Curve2d, BRepAdaptor_Surface
from OCP.BRepAlgoAPI import BRepAlgoAPI_Splitter
from OCP.BRepBuilderAPI import (BRepBuilderAPI_Copy, BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeFace,
                                BRepBuilderAPI_MakeSolid, BRepBuilderAPI_MakeVertex, BRepBuilderAPI_MakeWire,
                                BRepBuilderAPI_Sewing, BRepBuilderAPI_Transform)
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
from OCP.BRepFill import BRepFill
from OCP.BRepFilletAPI import BRepFilletAPI_MakeChamfer, BRepFilletAPI_MakeFillet
from OCP.BRepLib import BRepLib
from OCP.BRepOffset import BRepOffset_MakeOffset, BRepOffset_Skin
from OCP.BRepOffsetAPI import (BRepOffsetAPI_MakeDraft, BRepOffsetAPI_MakeFilling, BRepOffsetAPI_MakeOffsetShape,
                               BRepOffsetAPI_MakePipeShell, BRepOffsetAPI_ThruSections)
from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism, BRepPrimAPI_MakeRevol
from OCP.BRepTools import BRepTools
from OCP.GCPnts import GCPnts_AbscissaPoint
from OCP.GeomAbs import (GeomAbs_Arc, GeomAbs_C0, GeomAbs_C2, GeomAbs_Cylinder, GeomAbs_G1, GeomAbs_G2,
                         GeomAbs_Intersection, GeomAbs_Line, GeomAbs_Plane)
from OCP.GeomAPI import GeomAPI_PointsToBSpline
from OCP.OCP.collections import (Array1_double, Array1_gp_Pnt, IndexedDataMap_TopoDS_Shape_List_TopoDS_Shape_TopTools_ShapeMapHasher,
                                 List_TopoDS_Shape)
from OCP.ShapeFix import ShapeFix_Face
from OCP.TopAbs import (TopAbs_COMPOUND, TopAbs_EDGE, TopAbs_FACE, TopAbs_FORWARD, TopAbs_REVERSED, TopAbs_SHELL,
                        TopAbs_SOLID, TopAbs_VERTEX, TopAbs_WIRE)
from OCP.TopExp import TopExp
from OCP.TopoDS import TopoDS, TopoDS_Face, TopoDS_Iterator, TopoDS_Shape, TopoDS_Vertex
from OCP.gp import gp_Ax1, gp_Ax2, gp_Dir, gp_Pln, gp_Pnt, gp_Trsf, gp_Vec

from . import geometria as geo

_TOL = 1e-6        # tolerancia de costura "exacta" (piezas que ya comparten aristas)
_TOL_EXTREMO = 1e-4  # mm: dos aristas se encadenan si sus extremos están a menos de esto

_CAST = {TopAbs_COMPOUND: TopoDS.Compound, TopAbs_SOLID: TopoDS.Solid, TopAbs_SHELL: TopoDS.Shell,
         TopAbs_FACE: TopoDS.Face, TopAbs_WIRE: TopoDS.Wire, TopAbs_EDGE: TopoDS.Edge, TopAbs_VERTEX: TopoDS.Vertex}


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
    return [TopoDS.Face(f) for f in mapa.FindFromKey(arista)]


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
def extruir_superficie(aristas_o_alambre, direccion, distancia, *, simetrica=False, conicidad=0.0):
    """Extrusión de curvas en superficie [SFC-EXTRUDE]. Distancia negativa = sentido contrario.

    `simetrica`: la distancia es la longitud total, mitad para cada lado (Measurement = Whole Length).
    `conicidad` (grados, Taper Angle): positivo abre la superficie hacia afuera de un contorno cerrado,
    negativo la cierra; en una curva abierta, positivo inclina hacia la derecha del recorrido mirando
    desde `direccion`. La altura medida sobre `direccion` es siempre `distancia`."""
    geo.exigir_longitud(distancia, "La distancia de extrusión")
    if abs(conicidad) >= 89.0:
        raise geo.ErrorGeometria("La conicidad tiene que estar entre -89° y 89°.")
    n = _unitario(direccion)
    piezas = []
    for w in alambres(aristas_o_alambre):
        if abs(conicidad) < 1e-9:
            base, vec = w, n * distancia
            if simetrica:
                base = geo.trasladar(w, -n * abs(distancia) / 2)
                vec = n * abs(distancia)
            piezas.append(BRepPrimAPI_MakePrism(base, gp_Vec(*map(float, vec))).Shape())
            continue
        lados = [(n, abs(distancia) / 2), (-n, abs(distancia) / 2)] if simetrica else \
            [(n if distancia > 0 else -n, abs(distancia))]
        caras = []
        for d, alto in lados:
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
    return _simplificar(_juntar(piezas))


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


def revolver_superficie(aristas, punto_eje, dir_eje, angulo):
    """Revolución de curvas en superficie [SFC-REVOLVE] (Partial; ±360 = Full)."""
    if abs(angulo) < 1e-9:
        raise geo.ErrorGeometria("El ángulo de revolución no puede ser cero.")
    ang = math.radians(max(-360.0, min(360.0, angulo)))
    eje = gp_Ax1(_pnt(punto_eje), gp_Dir(*map(float, _unitario(dir_eje, "La dirección del eje"))))
    piezas = []
    for w in alambres(aristas):
        rev = BRepPrimAPI_MakeRevol(w, eje, ang)
        if not rev.IsDone():
            raise geo.ErrorGeometria("La revolución falló en el kernel.")
        piezas.append(rev.Shape())
    return _simplificar(_juntar(piezas))


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


def barrer_superficie(aristas_perfil, ruta, *, orientacion="perpendicular", torsion=0.0):
    """Barrido de curvas a lo largo de una ruta [SFC-SWEEP] (Single Path).

    `orientacion`: "perpendicular" (el perfil acompaña a la ruta) o "paralela" (el perfil no rota).
    `torsion` (grados, Twist Angle): giro total del perfil alrededor de la ruta; solo con perpendicular.
    La torsión se construye con secciones intermedias cada ≤10° (aproximación muy fina, no exacta) y admite como
    máximo ±TORSION_MAXIMA_SUPERFICIE grados."""
    if orientacion not in ("perpendicular", "paralela"):
        raise geo.ErrorGeometria(f"Orientación de barrido desconocida: {orientacion}")
    if not math.isfinite(torsion) or abs(torsion) > TORSION_MAXIMA_SUPERFICIE:
        raise geo.ErrorGeometria(f"La torsión del barrido de superficie admite como máximo "
                                 f"±{TORSION_MAXIMA_SUPERFICIE:g}° ({TORSION_MAXIMA_SUPERFICIE / 360:g} vueltas); "
                                 f"recibió {torsion:g}°.")
    if abs(torsion) > 1e-9 and orientacion != "perpendicular":
        raise geo.ErrorGeometria("La torsión solo existe con orientación perpendicular.")
    espina = _alambre_unico(ruta, "La ruta")
    piezas = []
    for perfil in alambres(aristas_perfil):
        ps = BRepOffsetAPI_MakePipeShell(espina)
        if orientacion == "paralela":
            ps.SetMode(gp_Ax2(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1), gp_Dir(1, 0, 0)))
        if abs(torsion) < 1e-9:
            ps.Add(perfil, False, False)
        else:
            n = max(3, math.ceil(abs(torsion) / 10.0) + 1)
            marcos, _ = _marcos_ruta(espina, n)
            p0, t0, r0 = marcos[0]
            for i, (p, t, r) in enumerate(marcos):
                tr = _trsf_marco(p0, t0, r0, p, t, r)
                giro = gp_Trsf()
                giro.SetRotation(gp_Ax1(_pnt(p), gp_Dir(*map(float, t))), math.radians(torsion) * i / (n - 1))
                seccion = BRepBuilderAPI_Transform(perfil, giro.Multiplied(tr), True).Shape()
                ps.Add(seccion, BRepBuilderAPI_MakeVertex(_pnt(p)).Vertex(), False, False)
        ps.Build()
        if not ps.IsDone():
            raise geo.ErrorGeometria("El barrido falló en el kernel (revisá que el perfil no se autointerseque).")
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


def solevar_superficie(secciones, *, cerrada=False, reglada=False):
    """Solevado (loft) de superficie entre secciones [SFC-LOFT, SFC-REF-LOFT-DLG].

    Cada sección es una curva/alambre o un punto (numpy (3,), gp_Pnt o vértice) — los puntos solo
    pueden ir primero o último (End condition Sharp). `cerrada` une la última sección con la primera;
    `reglada` usa tramos rectos entre secciones."""
    secciones = list(secciones)
    if len(secciones) < 2:
        raise geo.ErrorGeometria("El solevado necesita al menos dos secciones.")
    ts = BRepOffsetAPI_ThruSections(False, bool(reglada))
    primera = None
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
            ts.AddVertex(v)
        else:
            w = _alambre_unico(s, f"La sección {i + 1}")
            primera = primera or w
            ts.AddWire(w)
    if cerrada:
        if len(secciones) < 3:
            raise geo.ErrorGeometria("Un solevado cerrado necesita al menos tres secciones.")
        ts.AddWire(primera)
    ts.CheckCompatibility(False)
    ts.Build()
    if not ts.IsDone():
        raise geo.ErrorGeometria("El solevado falló en el kernel.")
    return _simplificar(ts.Shape())


_CONTINUIDAD = {"G0": GeomAbs_C0, "G1": GeomAbs_G1, "G2": GeomAbs_G2}


def parche(aristas_contorno, *, continuidad="G0", interior=(), soporte=None):
    """Parche que cierra un contorno [SFC-PATCH].

    Contorno plano, G0 y sin guías interiores → cara plana exacta. Si no, superficie de relleno
    (BRepOffsetAPI_MakeFilling). G1/G2 necesita `soporte`: el cuerpo al que pertenecen las aristas
    (de ahí salen las caras vecinas para la tangencia). `interior`: puntos (numpy) o aristas guía
    (Interior Rails/Points)."""
    if continuidad not in _CONTINUIDAD:
        raise geo.ErrorGeometria(f"Continuidad desconocida: {continuidad} (G0, G1 o G2).")
    if continuidad != "G0" and soporte is None:
        raise geo.ErrorGeometria("La continuidad G1/G2 necesita el cuerpo vecino (`soporte`).")
    interior = list(interior)
    if continuidad == "G0" and not interior:
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
            if continuidad != "G0" and vecinas:
                rel.Add(e, vecinas[0], _CONTINUIDAD[continuidad], True)
            else:
                rel.Add(e, GeomAbs_C0, True)
    for g in interior:
        if isinstance(g, TopoDS_Shape):
            for e in geo._explorar(g, TopAbs_EDGE):
                rel.Add(TopoDS.Edge(e), GeomAbs_C0, False)
        else:
            rel.Add(_pnt(g))
    rel.Build()
    if not rel.IsDone():
        raise geo.ErrorGeometria("No se pudo construir el parche (¿el contorno está cerrado?).")
    return _simplificar(rel.Shape())


def _rotar(v, eje, angulo_rad):
    """Rotación de Rodrigues de v alrededor del eje unitario."""
    c, s = math.cos(angulo_rad), math.sin(angulo_rad)
    return v * c + np.cross(eje, v) * s + eje * float(eje @ v) * (1 - c)


def reglada(aristas, distancia, angulo=0.0, *, tipo="normal", direccion=None, referencia=None):
    """Superficie reglada desde aristas [SFC-RULED].

    `tipo`: "normal" (sale perpendicular a la cara de la arista), "tangente" (sigue a la cara, hacia
    afuera del material) o "direccion" (hacia `direccion`). `angulo` (grados) gira la dirección
    alrededor de la arista. `referencia`: el cuerpo que contiene las aristas (para hallar su cara) o
    un `geo.Plano` si son curvas de boceto; con plano, "tangente" va a la derecha del recorrido.
    Cada arista da su propia cara; las esquinas no se ingletean (Mitered Corners no implementado)."""
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
    caras = []
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
                cara = vecinas[0]
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
            dirs = np.array(dirs)
            if np.max(np.linalg.norm(dirs - dirs[0], axis=1)) < 1e-9:
                otra = TopoDS.Edge(geo.trasladar(ef, dirs[0] * distancia))
            else:
                arr, par = Array1_gp_Pnt(1, n_m), Array1_double(1, n_m)
                for i, (p, d) in enumerate(zip(puntos, dirs, strict=True)):
                    arr.SetValue(i + 1, _pnt(p + d * distancia))
                    par.SetValue(i + 1, params[i])
                aprox = GeomAPI_PointsToBSpline(arr, par, 3, 8, GeomAbs_C2, 1e-6)
                otra = BRepBuilderAPI_MakeEdge(aprox.Curve()).Edge()
            caras.append(BRepFill.Face_s(ef, otra))
    return _coser_caras(caras)


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
    if resultado is None or _desfase_imposible(forma, resultado, distancia):
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


def empalme_superficie(forma, aristas, radio):
    """Empalme (Fillet) de aristas compartidas por dos caras de un cuerpo de superficie [SFC-FILLET-CHAMFER]."""
    if radio <= 0:
        raise geo.ErrorGeometria("El radio del empalme debe ser positivo.")
    op = BRepFilletAPI_MakeFillet(forma)
    for e in _formas(aristas):
        op.Add(float(radio), TopoDS.Edge(e))
    try:
        op.Build()
    except Exception as exc:  # noqa: BLE001 — OCC lanza Standard_Failure con mensajes poco útiles
        raise geo.ErrorGeometria("El empalme falló (¿radio demasiado grande?).") from exc
    if not op.IsDone():
        raise geo.ErrorGeometria("El empalme falló (¿radio demasiado grande o arista libre?).")
    return _simplificar(op.Shape())


def chaflan_superficie(forma, aristas, distancia):
    """Chaflán de distancia igual en aristas de un cuerpo de superficie [SFC-FILLET-CHAMFER]."""
    if distancia <= 0:
        raise geo.ErrorGeometria("La distancia del chaflán debe ser positiva.")
    op = BRepFilletAPI_MakeChamfer(forma)
    for e in _formas(aristas):
        op.Add(float(distancia), TopoDS.Edge(e))
    try:
        op.Build()
    except Exception as exc:  # noqa: BLE001
        raise geo.ErrorGeometria("El chaflán falló (¿distancia demasiado grande?).") from exc
    if not op.IsDone():
        raise geo.ErrorGeometria("El chaflán falló (¿distancia demasiado grande o arista libre?).")
    return _simplificar(op.Shape())


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
        vecinas = [TopoDS.Face(f) for f in mapa.FindFromIndex(k)]
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


def destrimar(cara, *, contornos="exteriores"):
    """Destrimado [SFC-UNTRIM]: rehace la cara con los límites naturales de su superficie.

    "exteriores" (External Edges): el borde exterior vuelve al límite natural, se conservan agujeros.
    "interiores" (Internal Edges): solo se tapan los agujeros. "todos" (All Edges): ambas cosas.
    En superficies infinitas (plano; cilindro a lo largo del eje) el límite natural es el rectángulo
    UV que encierra la cara."""
    if contornos not in ("exteriores", "interiores", "todos"):
        raise geo.ErrorGeometria(f"Tipo de destrimado desconocido: {contornos}")
    cara = TopoDS.Face(cara)
    adelante = TopoDS.Face(cara.Oriented(TopAbs_FORWARD))
    exterior = BRepTools.OuterWire_s(adelante)
    interiores = [TopoDS.Wire(w) for w in geo._explorar(adelante, TopAbs_WIRE) if not w.IsSame(exterior)]
    (u0, u1, v0, v1), sup = _limites_naturales(adelante)
    if contornos == "interiores":
        mf = BRepBuilderAPI_MakeFace(sup, exterior, True)
    else:
        mf = BRepBuilderAPI_MakeFace(sup, u0, u1, v0, v1, 1e-7)
        if contornos == "exteriores":
            for w in interiores:
                mf.Add(w)
    if not mf.IsDone():
        raise geo.ErrorGeometria("No se pudo rehacer la cara.")
    arreglo = ShapeFix_Face(mf.Face())
    arreglo.Perform()
    nueva = arreglo.Face()
    return TopoDS.Face(nueva.Reversed()) if cara.Orientation() == TopAbs_REVERSED else nueva


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


def extender(forma, aristas, distancia, *, tipo="natural"):
    """Extensión de bordes libres de una superficie [SFC-EXTEND].

    "natural": agranda la misma cara (plano y cilindro exactos; otras superficies con
    BRepLib.ExtendFace). Solo bordes iso-paramétricos de caras rectangulares en UV.
    "tangente": agrega caras planas tangentes a la cara (como reglada tangente).
    "perpendicular": agrega caras perpendiculares a la cara (como reglada normal)."""
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
    for e in _formas(aristas):
        e = TopoDS.Edge(e)
        vecinas = _caras_de(mapa, e)
        if len(vecinas) != 1:
            raise geo.ErrorGeometria("Solo se extienden aristas libres (bordes de una sola cara).")
        cara = vecinas[0]
        limites = BRepTools.UVBounds_s(cara)
        lado = _lado_iso(cara, e, limites)
        if lado is None:
            raise geo.ErrorGeometria("Solo se extienden bordes iso-paramétricos (la arista no es un borde u/v de la cara).")
        for otra in geo._explorar(BRepTools.OuterWire_s(cara), TopAbs_EDGE):
            if _lado_iso(cara, TopoDS.Edge(otra), limites) is None:
                raise geo.ErrorGeometria("La cara no es rectangular en su parametrización: no se puede extender en forma natural.")
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
    return _coser_caras([reemplazos.get(i, c) for i, c in enumerate(caras)])


def coser(formas, tolerancia=0.01):
    """Coser superficies [SFC-STITCH] (BRepBuilderAPI_Sewing). Si el resultado queda cerrado
    (estanco) se convierte en sólido, como Fusion. Devuelve {"forma", "es_solido", "aristas_libres"}."""
    cos = BRepBuilderAPI_Sewing(float(tolerancia))
    for f in _formas(formas):
        cos.Add(f)
    cos.Perform()
    cosido = _simplificar(cos.SewedShape())
    libres = cos.NbFreeEdges()
    cascarones = [TopoDS.Shell(s) for s in geo._explorar(cosido, TopAbs_SHELL)]
    if libres == 0 and cascarones and all(BRep_Tool.IsClosed_s(s) for s in cascarones):
        solidos = []
        for s in cascarones:
            sol = BRepBuilderAPI_MakeSolid(s).Solid()
            BRepLib.OrientClosedSolid_s(sol)
            solidos.append(sol)
        return {"forma": _juntar(solidos), "es_solido": True, "aristas_libres": 0}
    return {"forma": cosido, "es_solido": False, "aristas_libres": libres}


def descoser(forma):
    """Descoser [SFC-UNSTITCH]: separa un cuerpo (de superficie o sólido) en caras sueltas
    independientes (cada una con sus propias aristas)."""
    return [TopoDS.Face(BRepBuilderAPI_Copy(c).Shape()) for c in geo.caras(forma)]


def invertir_normal(forma):
    """Invertir normal [GUID-3B2D0A04-B93C-4F63-9512-00D91F042C2D]: cambia el lado positivo de una
    superficie (no aplica a sólidos: su normal siempre apunta afuera)."""
    if any(True for _ in geo._explorar(forma, TopAbs_SOLID)):
        raise geo.ErrorGeometria("Invertir normal es solo para cuerpos de superficie.")
    return _tipado(forma.Reversed())


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

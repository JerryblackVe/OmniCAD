# -*- coding: utf-8 -*-
"""
Detección de perfiles (regiones cerradas) de un boceto, y geometría OCC que necesita el boceto.

Equivalencia con Fusion 360: `Sketch.profiles` — los perfiles NO se guardan, se derivan de los
lazos cerrados del boceto cada vez que cambia (informe_analisis.md §3.2 y §5). Igual que en
Fusion, un círculo dentro de un rectángulo da DOS perfiles: el anillo y el disco.

Método: se construye una cara plana enorme y se la parte con todas las curvas del boceto
(BRepAlgoAPI_Splitter de OpenCascade). Las regiones resultantes que no tocan el borde de la
cara enorme son los perfiles.

Cada perfil lleva una FIRMA: el conjunto de ids de las curvas del boceto que forman su borde (se
sigue con el historial del Splitter: qué arista salió de qué curva). Las operaciones (extrusión,
revolución) referencian perfiles por firma y no por índice, así la referencia sobrevive a cambios de
cotas (versión simple de las referencias estables de Fusion, `entityToken` — informe §5 y riesgo de
"nombres topológicos" en §9).

Además: contornos de un texto (Font de OCC, como el Texto de boceto de Fusion) y la proyección /
intersección de aristas, caras y cuerpos sobre el plano del boceto (Proyectar / Intersecar).
"""
import math

import numpy as np
from OCP.BRep import BRep_Tool
from OCP.BRepAdaptor import BRepAdaptor_Curve
from OCP.BRepLib import BRepLib
from OCP.BRepAlgoAPI import BRepAlgoAPI_Section, BRepAlgoAPI_Splitter
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeFace, BRepBuilderAPI_NurbsConvert
from OCP.Font import Font_FA_Bold, Font_FA_BoldItalic, Font_FA_Italic, Font_FA_Regular, Font_FontMgr, Font_StrictLevel_Any
from OCP.Geom import Geom_BSplineCurve
from OCP.GeomAbs import GeomAbs_BezierCurve, GeomAbs_Circle, GeomAbs_Line
from OCP.NCollection import NCollection_String
from OCP.OCP.collections import (Array1_double, Array1_gp_Pnt, Array1_int, List_TopoDS_Shape,
                                 Sequence_TCollection_HAsciiString)
from OCP.StdPrs import StdPrs_BRepFont, StdPrs_BRepTextBuilder
from OCP.TCollection import TCollection_AsciiString
from OCP.TopAbs import TopAbs_EDGE, TopAbs_VERTEX
from OCP.TopExp import TopExp_Explorer
from OCP.TopoDS import TopoDS
from OCP.gp import gp_Ax2, gp_Ax3, gp_Circ, gp_Dir, gp_Elips, gp_Pln

from ..restricciones.boceto import MEDIDA_MAXIMA, distancia_primitiva, puntos_primitiva
from . import geometria as geo

# mm: semilado de la cara "enorme" que se parte. Los perfiles valen dentro de ±_TAM_CARA/2 = ±MEDIDA_MAXIMA (el tope
# de las cotas, restricciones/boceto.py): una cota aceptada no deja el perfil afuera (con 1e5, un radio de 60 m lo perdía)
_TAM_CARA = 2 * MEDIDA_MAXIMA


class Perfil:
    def __init__(self, cara, area, centroide_uv, firma):
        self.cara = cara                  # TopoDS_Face (en 3D, sobre el plano del boceto)
        self.area = area                  # mm²
        self.centroide_uv = centroide_uv  # (u, v) en coordenadas del boceto
        self.firma = firma                # frozenset de ids de curvas del borde

    def descripcion(self):
        return f"área {self.area:.2f} mm², centro ({self.centroide_uv[0]:.1f}; {self.centroide_uv[1]:.1f})"


def _arista_elipse(plano, c, a, b, ang, t0=None, t1=None):
    xdir = plano.dir_3d(math.cos(ang), math.sin(ang))
    if a < b:      # gp_Elips exige radio mayor >= menor: se gira el marco 90° y se corre el parámetro
        a, b = b, a
        xdir = plano.dir_3d(-math.sin(ang), math.cos(ang))
        if t0 is not None:
            t0, t1 = t0 - math.pi / 2, t1 - math.pi / 2
    elips = gp_Elips(gp_Ax2(plano.pnt(*c), gp_Dir(*plano.normal), gp_Dir(*xdir)), a, b)
    if t0 is None:
        return BRepBuilderAPI_MakeEdge(elips)
    while t1 <= t0 + 1e-12:
        t1 += 2 * math.pi
    return BRepBuilderAPI_MakeEdge(elips, t0, t1)


def _arista_bspline(plano, polos, nudos, grado, pesos):
    unicos, mult = [], []
    for k in nudos:
        if unicos and abs(k - unicos[-1]) < 1e-12:
            mult[-1] += 1
        else:
            unicos.append(float(k))
            mult.append(1)
    P = Array1_gp_Pnt(1, len(polos))
    for i, q in enumerate(polos, start=1):
        P.SetValue(i, plano.pnt(*q))
    K, M = Array1_double(1, len(unicos)), Array1_int(1, len(mult))
    for i, (k, m) in enumerate(zip(unicos, mult, strict=True), start=1):
        K.SetValue(i, k)
        M.SetValue(i, m)
    if pesos:
        W = Array1_double(1, len(pesos))
        for i, w in enumerate(pesos, start=1):
            W.SetValue(i, float(w))
        curva = Geom_BSplineCurve(P, W, K, M, grado)
    else:
        curva = Geom_BSplineCurve(P, K, M, grado)
    return BRepBuilderAPI_MakeEdge(curva)


def _finita(prim):
    """True si todos los números de la primitiva (coordenadas, radios, ángulos, polos, nudos, pesos) son finitos."""
    pendientes = list(prim[2:])
    while pendientes:
        v = pendientes.pop()
        if isinstance(v, (tuple, list, np.ndarray)):
            pendientes.extend(v)
        elif isinstance(v, (float, np.floating)) and not math.isfinite(v):
            return False
    return True


def aristas_boceto(geometria, plano):
    """Crea aristas OCC a partir de las primitivas 2D de `Boceto.geometria()`. Devuelve [(id, arista)]."""
    aristas = []
    for prim in geometria:
        tipo, cid = prim[0], prim[1]
        if not _finita(prim):
            continue        # con una arista NaN o infinita el BRepAlgoAPI_Splitter de `detectar` no termina nunca
        try:
            if tipo == "linea":
                (u1, v1), (u2, v2) = prim[2], prim[3]
                if math.hypot(u2 - u1, v2 - v1) < 1e-9:
                    continue
                e = BRepBuilderAPI_MakeEdge(plano.pnt(u1, v1), plano.pnt(u2, v2))
            elif tipo == "circulo":
                (cu, cv), r = prim[2], prim[3]
                if r <= 1e-9:
                    continue
                e = BRepBuilderAPI_MakeEdge(gp_Circ(plano.ax2(cu, cv), r))
            elif tipo == "arco":
                (cu, cv), r, a0, a1 = prim[2], prim[3], prim[4], prim[5]
                if r <= 1e-9:
                    continue
                while a1 <= a0 + 1e-12:
                    a1 += 2 * math.pi
                e = BRepBuilderAPI_MakeEdge(gp_Circ(plano.ax2(cu, cv), r), a0, a1)
            elif tipo in ("elipse", "arco_elipse"):
                if min(prim[3], prim[4]) <= 1e-9:
                    continue
                e = _arista_elipse(plano, *prim[2:6], *(prim[6:8] if tipo == "arco_elipse" else ()))
            elif tipo == "spline":
                polos = prim[2]
                if max(abs(q[0] - polos[0][0]) + abs(q[1] - polos[0][1]) for q in polos[1:]) < 1e-9:
                    continue
                e = _arista_bspline(plano, prim[2], prim[3], prim[4], prim[5])
            else:
                continue
        except Exception:  # noqa: BLE001 — una curva degenerada (a medio dibujar) no rompe los perfiles
            continue
        if e.IsDone():
            aristas.append((cid, e.Edge()))
    return aristas


def _a_uv(plano, p3):
    d = np.asarray(p3, float) - plano.origen
    return float(d @ plano.u), float(d @ plano.v)


_CACHE_PERFILES = {}
_CACHE_MAX = 24


def _clave_plano(plano):
    return tuple(float(v) for arr in (plano.origen, plano.u, plano.v, plano.normal) for v in arr)


def detectar(geometria, plano, tolerancia=1e-4):
    """Devuelve la lista de Perfil ordenada de forma determinista (por centroide u, luego v).

    Con caché: recalcular el timeline sin tocar el boceto no vuelve a partir la cara (con miles de curvas,
    partir es lo que más tarda). La clave es la geometría misma (tuplas de números), así que cualquier cambio
    la invalida."""
    try:
        clave = (tuple(geometria), _clave_plano(plano), tolerancia)
        hash(clave)
    except TypeError:                      # alguna primitiva con listas: sin caché
        return _detectar(geometria, plano, tolerancia)
    if clave in _CACHE_PERFILES:
        return list(_CACHE_PERFILES[clave])
    perfiles = _detectar(geometria, plano, tolerancia)
    if len(_CACHE_PERFILES) >= _CACHE_MAX:
        _CACHE_PERFILES.pop(next(iter(_CACHE_PERFILES)))
    _CACHE_PERFILES[clave] = tuple(perfiles)
    return perfiles


def _aristas_de(forma):
    salida = []
    ex = TopExp_Explorer(forma, TopAbs_EDGE)
    while ex.More():
        salida.append(TopoDS.Edge(ex.Current()))
        ex.Next()
    return salida


def _punto_medio(arista):
    """Punto medio de la arista o None si no tiene curva 3D (aristas degeneradas)."""
    try:
        c = BRepAdaptor_Curve(arista)
        p = c.Value((c.FirstParameter() + c.LastParameter()) / 2)
    except Exception:  # noqa: BLE001 — Standard_NullObject y similares de OCC
        return None
    return p.X(), p.Y(), p.Z()


def _origen_aristas(aristas, caras, sp):
    """{hash de arista de las caras: id de la curva del boceto de la que salió}.

    El Splitter copia TODAS las aristas, y pedirle el historial (Modified) a cada una cuesta ~0,5 ms: con miles
    de curvas eran segundos. Las que no se partieron se reconocen por su punto medio (la copia es idéntica); el
    historial se pide solo para las que sí se partieron."""
    from scipy.spatial import cKDTree
    origen = {}
    unicas = {}
    for cara in caras:
        for a in _aristas_de(cara):
            unicas.setdefault(hash(a), a)
    if not aristas or not unicas:
        return origen
    usadas = np.zeros(len(aristas), bool)
    fuente = [(i, m) for i, m in ((i, _punto_medio(e)) for i, (_cid, e) in enumerate(aristas)) if m is not None]
    destino = [(h, m) for h, m in ((h, _punto_medio(a)) for h, a in unicas.items()) if m is not None]
    if fuente and destino:
        arbol = cKDTree(np.array([m for _i, m in fuente]))
        dist, idx = arbol.query(np.array([m for _h, m in destino]))
        for (h, _m), d, k in zip(destino, dist, idx, strict=True):
            if d < 1e-7:
                i = fuente[k][0]
                origen[h] = aristas[i][0]
                usadas[i] = True
    for i, (cid, e) in enumerate(aristas):
        if not usadas[i]:                  # se partió (o se superpone con otra): sus hijas por el historial
            for hija in sp.Modified(e):
                origen.setdefault(hash(hija), cid)
    return origen


def _detectar(geometria, plano, tolerancia=1e-4):
    aristas = aristas_boceto(geometria, plano)
    if not aristas:
        return []
    grande = BRepBuilderAPI_MakeFace(gp_Pln(plano.pnt(0, 0), gp_Dir(*plano.normal)),
                                     -_TAM_CARA, _TAM_CARA, -_TAM_CARA, _TAM_CARA).Face()
    args, herramientas = List_TopoDS_Shape(), List_TopoDS_Shape()
    args.Append(grande)
    for _, e in aristas:
        herramientas.Append(e)
    sp = BRepAlgoAPI_Splitter()
    sp.SetArguments(args)
    sp.SetTools(herramientas)
    sp.SetFuzzyValue(tolerancia)
    sp.Build()
    if not sp.IsDone():
        raise geo.ErrorGeometria("No se pudieron calcular los perfiles del boceto.")
    caras = list(geo.caras(sp.Shape()))
    origen = _origen_aristas(aristas, caras, sp)
    borde = {hash(a) for a in _aristas_de(grande)}
    for a in _aristas_de(grande):
        borde.update(hash(h) for h in sp.Modified(a))

    perfiles = []
    for cara in caras:
        aristas_cara = _aristas_de(cara)
        if any(hash(a) in borde for a in aristas_cara):
            continue  # región exterior (toca el borde de la cara enorme)
        firma = set()
        for arista in aristas_cara:
            cid = origen.get(hash(arista))
            if cid is None:          # respaldo geométrico: la curva más cercana al punto medio
                curva = BRepAdaptor_Curve(arista)
                pm = curva.Value((curva.FirstParameter() + curva.LastParameter()) / 2)
                uv = _a_uv(plano, (pm.X(), pm.Y(), pm.Z()))
                mejor = min(geometria, key=lambda prim: distancia_primitiva(prim, uv))
                if distancia_primitiva(mejor, uv) < 1e-3:
                    cid = mejor[1]
            if cid is not None:
                firma.add(cid)
        perfiles.append(Perfil(cara, geo.area(cara), _a_uv(plano, geo.centro_masa(cara, superficie=True)),
                               frozenset(firma)))
    perfiles.sort(key=lambda p: (round(p.centroide_uv[0], 4), round(p.centroide_uv[1], 4), p.area))
    return perfiles


def buscar_por_firma(perfiles, firma, centroide=None):
    """Perfil cuya firma coincide. Si varias regiones comparten firma (p. ej. un círculo cortado
    por una línea), desempata el centroide guardado más cercano. Si no hay coincidencia: None."""
    objetivo = frozenset(firma)
    candidatos = [p for p in perfiles if p.firma == objetivo]
    if not candidatos:
        return None
    if len(candidatos) == 1 or centroide is None:
        return candidatos[0]
    return min(candidatos, key=lambda p: math.dist(p.centroide_uv, centroide))


# ---------------------------------------------------------------- aristas OCC → primitivas 2D
def _aristas_unicas(forma):
    vistas, salida = set(), []
    ex = TopExp_Explorer(forma, TopAbs_EDGE)
    while ex.More():
        e = TopoDS.Edge(ex.Current())
        if hash(e) not in vistas and not BRep_Tool.Degenerated_s(e):
            vistas.add(hash(e))
            salida.append(e)
        ex.Next()
    return salida


def _spline_de_arista(arista, a_uv):
    """Primitiva 'spline' exacta de una arista cualquiera (se convierte a NURBS, se recorta a la arista y
    se llevan los polos al plano: la proyección ortogonal es afín, así que el resultado es exacto)."""
    ex = TopExp_Explorer(BRepBuilderAPI_NurbsConvert(arista).Shape(), TopAbs_EDGE)
    ad = BRepAdaptor_Curve(TopoDS.Edge(ex.Current()))
    f, l = ad.FirstParameter(), ad.LastParameter()
    if ad.GetType() == GeomAbs_BezierCurve:       # las letras de un texto vienen en tramos de Bézier
        bz = ad.Bezier()
        if f > 1e-12 or l < 1 - 1e-12:
            bz.Segment(f, l)
        n, p = bz.NbPoles(), bz.Degree()
        polos = [bz.Pole(i) for i in range(1, n + 1)]
        pesos = [bz.Weight(i) for i in range(1, n + 1)] if bz.IsRational() else None
        nudos = [0.0] * (p + 1) + [1.0] * (p + 1)
    else:
        bs = ad.BSpline()
        if bs.IsPeriodic():
            bs.SetNotPeriodic()
        if f > bs.FirstParameter() + 1e-12 or l < bs.LastParameter() - 1e-12:
            bs.Segment(f, l)
        n, p = bs.NbPoles(), bs.Degree()
        polos = [bs.Pole(i) for i in range(1, n + 1)]
        pesos = [bs.Weight(i) for i in range(1, n + 1)] if bs.IsRational() else None
        nudos = []
        for i in range(1, bs.NbKnots() + 1):
            nudos += [bs.Knot(i)] * bs.Multiplicity(i)
    polos = tuple(a_uv(q) for q in polos)
    if max(math.dist(polos[0], q) for q in polos[1:]) < 1e-9:
        return None
    if all(abs((q[0] - polos[0][0]) * (polos[-1][1] - polos[0][1]) - (q[1] - polos[0][1]) * (polos[-1][0] - polos[0][0]))
           < 1e-9 * max(1.0, math.dist(polos[0], polos[-1]) ** 2) for q in polos):
        # curva vista de canto (p. ej. un círculo perpendicular al plano): queda el segmento que recorre
        # (los polos de una curva racional pueden caer fuera de ella: se usan puntos de la curva)
        pts = puntos_primitiva(("spline", None, polos, tuple(nudos), p, tuple(pesos) if pesos else None), 128)
        lejos = max(((a, b) for a in pts[::4] + pts[-1:] for b in pts[::4] + pts[-1:]), key=lambda ab: math.dist(*ab))
        return ("linea", None, lejos[0], lejos[1]) if math.dist(*lejos) > 1e-9 else None
    return ("spline", None, polos, tuple(nudos), p, tuple(pesos) if pesos else None)


def arista_a_primitiva(arista, a_uv, normal=None):
    """Primitiva 2D (id None) de una arista OCC ya contenida en (o proyectada a) un plano. `a_uv` lleva un
    gp_Pnt a (u, v); `normal` (la del plano) permite reconocer círculos paralelos al plano."""
    curva = BRepAdaptor_Curve(arista)
    tipo, f, l = curva.GetType(), curva.FirstParameter(), curva.LastParameter()
    if tipo == GeomAbs_Line:
        p1, p2 = a_uv(curva.Value(f)), a_uv(curva.Value(l))
        return ("linea", None, p1, p2) if math.dist(p1, p2) > 1e-9 else None
    if tipo == GeomAbs_Circle and normal is not None:
        circ = curva.Circle()
        eje = circ.Axis().Direction()
        coseno = eje.X() * normal[0] + eje.Y() * normal[1] + eje.Z() * normal[2]
        if abs(abs(coseno) - 1) < 1e-9:
            c, r = a_uv(circ.Location()), circ.Radius()
            if abs(l - f - 2 * math.pi) < 1e-9:
                return ("circulo", None, c, r)
            a, b = a_uv(curva.Value(f)), a_uv(curva.Value(l))
            if coseno < 0:
                a, b = b, a
            return ("arco", None, c, r, math.atan2(a[1] - c[1], a[0] - c[0]), math.atan2(b[1] - c[1], b[0] - c[0]))
    return _spline_de_arista(arista, a_uv)


# ---------------------------------------------------------------- texto
_ASPECTOS = {(False, False): Font_FA_Regular, (True, False): Font_FA_Bold, (False, True): Font_FA_Italic,
             (True, True): Font_FA_BoldItalic}


def fuentes_disponibles():
    """Nombres de las fuentes para el Texto de boceto: todas las instaladas (catálogo de `fuentes`, que ve
    también las del usuario y las variables) más las que conoce el administrador de OpenCascade."""
    nombres = set()
    try:
        from . import fuentes
        nombres.update(fuentes.familias())
    except Exception:  # noqa: BLE001 — sin catálogo, quedan las de OpenCascade
        pass
    seq = Sequence_TCollection_HAsciiString()
    Font_FontMgr.GetInstance_s().GetAvailableFontsNames(seq)
    nombres.update(seq.Value(i).ToCString() for i in range(1, seq.Length() + 1))
    return sorted(nombres, key=str.casefold)


def _contornos_occ(texto, fuente, altura, negrita, cursiva):
    """Respaldo: contornos con el administrador de fuentes de OpenCascade (solo lo básico)."""
    f = StdPrs_BRepFont()
    if not f.FindAndInit(TCollection_AsciiString(str(fuente)), _ASPECTOS[(bool(negrita), bool(cursiva))],
                         float(altura), Font_StrictLevel_Any):
        raise geo.ErrorGeometria(f"No se encontró la fuente «{fuente}».")
    forma = StdPrs_BRepTextBuilder().Perform(f, NCollection_String(str(texto)), gp_Ax3())
    if forma.IsNull():
        return []
    BRepLib.BuildCurves3d_s(forma)          # las letras vienen con curvas 2D sobre el plano: se pasan a 3D
    a_uv = lambda p: (p.X(), p.Y())  # noqa: E731
    salida = []
    for e in _aristas_unicas(forma):
        prim = arista_a_primitiva(e, a_uv)          # sin normal: el texto guarda solo líneas y splines
        if prim is not None:
            salida.append(prim)
    return salida


def contornos_texto(texto, fuente="Arial", altura=5.0, negrita=False, cursiva=False, **opciones):
    """Contornos de un texto como primitivas 2D (líneas y B-splines) con el origen en la esquina inferior
    izquierda de la línea base (Texto de boceto de Fusion: fuente, altura, negrita, cursiva).

    Opciones (ver `fuentes.contornos_texto`): espaciado, interlineado, alineacion, ancla_v, ancho_caja,
    voltear_h, voltear_v. Usa fontTools; si la fuente no está en el catálogo cae al administrador de
    OpenCascade (que ignora las opciones)."""
    from . import fuentes
    try:
        return fuentes.contornos_texto(texto, fuente, altura, negrita, cursiva, **opciones)
    except fuentes.ErrorFuente as e:
        if fuentes.buscar_fuente(fuente) is not None:       # la fuente existe: el error es de las opciones
            raise geo.ErrorGeometria(str(e)) from e
    return _contornos_occ(texto, fuente, altura, negrita, cursiva)


# ---------------------------------------------------------------- Proyectar / Intersecar
def _vertices(forma):
    salida = []
    ex = TopExp_Explorer(forma, TopAbs_VERTEX)
    while ex.More():
        p = BRep_Tool.Pnt_s(TopoDS.Vertex(ex.Current()))
        salida.append(p)
        ex.Next()
    return salida


def proyectar_forma(forma, plano):
    """Proyectar (Fusion: Create > Project/Include > Project): proyección ortogonal de un vértice, una
    arista, una cara o un cuerpo sobre el plano del boceto. Es exacta: la proyección es afín, así que
    se proyectan los extremos de las rectas y los polos de las curvas (B-spline racional).
    Devuelve (primitivas, puntos sueltos (u, v))."""
    a_uv = lambda p: plano.a_uv((p.X(), p.Y(), p.Z()))  # noqa: E731
    aristas = _aristas_unicas(forma)
    if not aristas:
        return [], [a_uv(p) for p in _vertices(forma)]
    prims = []
    for e in aristas:
        prim = arista_a_primitiva(e, a_uv, tuple(plano.normal))
        if prim is not None:
            prims.append(prim)
    return prims, []


def intersecar_forma(forma, plano):
    """Intersecar (Fusion: Project/Include > Intersect): curvas donde la forma corta el plano del boceto.
    Devuelve (primitivas, puntos sueltos (u, v)) — una arista que atraviesa el plano da un punto."""
    sec = BRepAlgoAPI_Section(forma, gp_Pln(plano.pnt(0, 0), gp_Dir(*plano.normal)))
    sec.Build()
    if not sec.IsDone():
        raise geo.ErrorGeometria("No se pudo intersecar con el plano del boceto.")
    a_uv = lambda p: plano.a_uv((p.X(), p.Y(), p.Z()))  # noqa: E731
    prims = []
    for e in _aristas_unicas(sec.Shape()):
        prim = arista_a_primitiva(e, a_uv, tuple(plano.normal))
        if prim is not None:
            prims.append(prim)
    puntos = [] if prims else [a_uv(p) for p in _vertices(sec.Shape())]
    return prims, puntos

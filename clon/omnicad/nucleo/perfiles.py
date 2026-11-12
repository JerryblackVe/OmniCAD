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
import hashlib
import math
from functools import partial

import numpy as np
from .. import nativo
from . import motor as _motor


def _iniciar_opencascade():
    global Array1_double, Array1_gp_Pnt, Array1_int, BRepAdaptor_Curve, BRepAlgoAPI_Section
    global BRepAlgoAPI_Splitter, BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeFace, BRepBuilderAPI_NurbsConvert
    global BRepLib, BRep_Tool, Font_FA_Bold, Font_FA_BoldItalic, Font_FA_Italic, Font_FA_Regular, Font_FontMgr
    global Font_StrictLevel_Any, GeomAbs_BezierCurve, GeomAbs_Circle, GeomAbs_Line, Geom_BSplineCurve
    global List_TopoDS_Shape, NCollection_String, Sequence_TCollection_HAsciiString, StdPrs_BRepFont
    global StdPrs_BRepTextBuilder, TCollection_AsciiString, TopAbs_EDGE, TopAbs_VERTEX, TopExp_Explorer, TopoDS
    global _ASPECTOS, gp_Ax2, gp_Ax3, gp_Circ, gp_Dir, gp_Elips, gp_Pln, BRepGProp, GProp_GProps
    global BRepBuilderAPI_MakeVertex, BRepBuilderAPI_MakeWire, Geom_Circle, gp_Pnt
    from OCP.BRep import BRep_Tool
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    from OCP.BRepLib import BRepLib
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Section, BRepAlgoAPI_Splitter
    from OCP.BRepBuilderAPI import (BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakeVertex,
                                    BRepBuilderAPI_MakeWire, BRepBuilderAPI_NurbsConvert)
    from OCP.BRepGProp import BRepGProp
    from OCP.Font import Font_FA_Bold, Font_FA_BoldItalic, Font_FA_Italic, Font_FA_Regular, Font_FontMgr, Font_StrictLevel_Any
    from OCP.Geom import Geom_BSplineCurve, Geom_Circle
    from OCP.GProp import GProp_GProps
    from OCP.GeomAbs import GeomAbs_BezierCurve, GeomAbs_Circle, GeomAbs_Line
    from OCP.NCollection import NCollection_String
    from OCP.OCP.collections import (Array1_double, Array1_gp_Pnt, Array1_int, List_TopoDS_Shape,
                                     Sequence_TCollection_HAsciiString)
    from OCP.StdPrs import StdPrs_BRepFont, StdPrs_BRepTextBuilder
    from OCP.TCollection import TCollection_AsciiString
    from OCP.TopAbs import TopAbs_EDGE, TopAbs_VERTEX
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopoDS import TopoDS
    from OCP.gp import gp_Ax2, gp_Ax3, gp_Circ, gp_Dir, gp_Elips, gp_Pln, gp_Pnt
    _ASPECTOS = {(False, False): Font_FA_Regular, (True, False): Font_FA_Bold, (False, True): Font_FA_Italic,
                 (True, True): Font_FA_BoldItalic}


if _motor.motor_activo() == "opencascade":
    _iniciar_opencascade()

from ..restricciones.boceto import MEDIDA_MAXIMA, distancia_primitiva, puntos_primitiva
from . import geometria as geo

# mm: semilado de la cara "enorme" que se parte. Los perfiles valen dentro de ±_TAM_CARA/2 = ±MEDIDA_MAXIMA (el tope
# de las cotas, restricciones/boceto.py): una cota aceptada no deja el perfil afuera (con 1e5, un radio de 60 m lo perdía)
_TAM_CARA = 2 * MEDIDA_MAXIMA


class Perfil:
    def __init__(self, cara, area, centroide_uv, firma, fabrica=None, caja_uv=None):
        self._cara = cara                 # TopoDS_Face (en 3D, sobre el plano del boceto)
        self._fabrica = fabrica           # sin cara: cómo armarla al pedirla (BOC-28: con miles de perfiles, casi nadie la pide)
        self.area = area                  # mm²
        self.centroide_uv = centroide_uv  # (u, v) en coordenadas del boceto
        self.firma = firma                # frozenset de ids de curvas del borde
        self.caja_uv = caja_uv            # (u0, v0, u1, v1) si ya se conoce sin armar la cara

    @property
    def cara(self):
        if self._cara is None and self._fabrica is not None:
            self._cara, self._fabrica = self._fabrica(), None
        return self._cara

    def descripcion(self):
        return f"área {self.area:.2f} mm², centro ({self.centroide_uv[0]:.1f}; {self.centroide_uv[1]:.1f})"


def _punto_adentro(cara):
    """Un punto del material de la cara, también cuando el mallador no produce triángulos."""
    return geo.punto_dentro(cara)


def _cajas(caras):
    return np.array([geo.caja_envolvente(c) for c in caras], float).reshape(-1, 2, 3)


def _caras_con(q, cajas, caras):
    """Índices de las `caras` que contienen el punto `q`; `cajas` (de `_cajas`) descarta casi todas sin ir a OpenCascade."""
    from OCP.BRepClass import BRepClass_FaceClassifier
    from OCP.TopAbs import TopAbs_IN
    tol = 1e-3       # la malla viene en float32: lejos del origen (un plano a z = 177) el punto se corre ~1e-5 mm
    cerca = np.all((cajas[:, 0] - tol <= q) & (q <= cajas[:, 1] + tol), axis=1)
    return [j for j in np.flatnonzero(cerca)
            if BRepClass_FaceClassifier(caras[j], gp_Pnt(*map(float, q)), 1e-7).State() == TopAbs_IN]


def _capas_de_texto(del_texto):
    """(letras, huecos) de perfiles con el borde hecho solo de texto: los que quedan dentro de un número PAR de
    contornos exteriores de los demás son letras (0 = una letra; 1 = el hueco de una letra; 2 = una isla en un hueco)."""
    from OCP.BRepTools import BRepTools
    llenas = [BRepBuilderAPI_MakeFace(BRepTools.OuterWire_s(p.cara), True).Face() for p in del_texto]
    cajas = _cajas(llenas)
    letras, huecos = [], []
    for i, p in enumerate(del_texto):
        profundidad = sum(1 for j in _caras_con(_punto_adentro(p.cara), cajas, llenas) if j != i)
        (huecos if profundidad % 2 else letras).append(p)
    return letras, huecos


def partes_de_texto(perfiles, ids_texto):
    """(letras, huecos) de los textos `ids_texto` entre los perfiles de un boceto, como al elegir un texto en Fusion.
    Cada texto por su lado (`detectar_boceto`): una letra adentro de la «O» de otro texto no es un hueco."""
    letras, huecos = [], []
    for i in ids_texto:
        de_texto = _capas_de_texto([p for p in perfiles if p.firma == {i}])
        letras += de_texto[0]
        huecos += de_texto[1]
    return letras, huecos


def sin_huecos(perfiles, boceto):
    """Los `perfiles` de `boceto` menos los huecos de sus letras."""
    textos = [c.id for c in boceto.curvas.values() if c.tipo == "texto"]
    if not textos and not boceto.objetos:
        return list(perfiles)
    huecos = {id(p) for p in partes_de_texto(perfiles, textos)[1]}
    if boceto.objetos:
        from ..restricciones import objetos
        for oid in objetos.raices(boceto):
            cids = set(objetos.curvas(boceto, [oid]))
            propios = [p for p in perfiles if p.firma and p.firma <= cids]
            formas_svg = [o for o in boceto.objetos.values() if "regla_relleno" in o
                          and set(objetos.curvas(boceto, [o["id"]])) <= cids]
            if formas_svg:
                preparadas = [(objetos.caja(boceto, [o["id"]]), o["regla_relleno"],
                               [(g, o.get("sentidos_svg", {}).get(str(g[1]), 1) *
                                 (-1 if g[0] in ("arco", "arco_elipse") and
                                  np.linalg.det(objetos.indice(boceto)[g[1]][2][:2, :2]) < 0 else 1))
                                for g in objetos.primitivas(boceto, o["id"])])
                              for o in formas_svg]
                huecos.update(id(p) for p in propios if not _tinta_svg(p, preparadas))
            else:
                huecos.update(id(p) for p in _capas_de_texto(propios)[1])
    return [p for p in perfiles if id(p) not in huecos]


def _tinta_svg(perfil, formas):
    """Regla de relleno por elemento SVG; objetos superpuestos no se restan entre sí."""
    from ..restricciones.objetos import vueltas_primitiva
    # El centroide de una letra puede caer dentro de su agujero; usar un punto de la cara.
    plano = getattr(perfil, "plano_boceto", None)
    q = perfil.centroide_uv
    if plano is not None and not _cara_contiene(perfil.cara, q, plano):
        q = tuple(plano.a_uv(_punto_adentro(perfil.cara)))
    for limites, regla, primitivas in formas:
        x0, y0, x1, y1 = limites
        if not (x0 - 1e-7 <= q[0] <= x1 + 1e-7 and y0 - 1e-7 <= q[1] <= y1 + 1e-7):
            continue
        vueltas = sum(sentido * vueltas_primitiva(g, q) for g, sentido in primitivas)
        if (vueltas % 2) if regla == "evenodd" else (vueltas != 0):
            return True
    return False


def perfiles_de_boceto(br):
    """Todos los perfiles del boceto resuelto `br` menos los huecos de sus letras: lo que toma Fusion al elegir un
    boceto entero (Extrude reference, Profiles)."""
    return sin_huecos(br.perfiles, br.boceto)


def letras_de_texto(perfiles, ids_texto):
    """Las LETRAS de `partes_de_texto` (sin los huecos de la «o», la «a»…)."""
    return partes_de_texto(perfiles, ids_texto)[0]


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


def _curva_bspline(plano, polos, nudos, grado, pesos):
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
    return curva


def _arista_bspline(plano, polos, nudos, grado, pesos):
    return BRepBuilderAPI_MakeEdge(_curva_bspline(plano, polos, nudos, grado, pesos))


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


def detectar_boceto(boceto, plano, geometria=None):
    """Perfiles de un boceto, en el orden de `detectar`. Como en Fusion, cada texto va aparte: no parte las curvas ni a
    otro texto, así que sus letras se pisan con lo que tengan debajo (B-134). `geometria`: la de `Boceto.geometria()`
    si no se da (el editor la pasa con el contenido real de los textos ligados).

    shortcut: cada grupo usa una entrada del caché de `detectar`; con más textos que `_CACHE_MAX` se recalcula, y alcanza."""
    textos = {c.id for c in boceto.curvas.values() if c.tipo == "texto"}
    from ..restricciones import objetos
    indice = objetos.indice(boceto) if boceto.objetos else {}
    fuera = objetos.curvas_sin_perfil(boceto) if boceto.objetos else ()
    grupos = {}
    for g in boceto.geometria() if geometria is None else geometria:
        if g[1] in fuera:
            continue                       # objeto con «Participar en perfiles» apagado
        clave = ("texto", g[1]) if g[1] in textos else ("objeto", indice[g[1]][0]) if g[1] in indice else None
        grupos.setdefault(clave, []).append(g)
    locales = boceto
    if any(k is not None and k[0] == "objeto" for k in grupos):
        if any(not np.array_equal(boceto.objetos[i]["matriz"], objetos.IDENTIDAD) for i in objetos.raices(boceto)):
            locales = boceto.copia()
            for oid in objetos.raices(locales):
                locales.objetos[oid]["matriz"] = [list(f) for f in objetos.IDENTIDAD]
            objetos.invalidar(locales)
    perfiles = []
    for clave, grupo in grupos.items():
        if clave is None or clave[0] != "objeto":
            perfiles.extend(detectar(grupo, plano))
            continue
        # Una matriz no cambia qué curvas se intersectan dentro del recurso. Se intersecta una vez, en XY local.
        m = objetos.matriz(boceto.objetos[clave[1]]["matriz"])
        prims = [p for cid in dict.fromkeys(g[1] for g in grupo) for p in locales.primitivas(cid)]
        originales = detectar(prims, geo.Plano("XY"))
        matriz4 = np.eye(4)
        matriz4[:3, :2] = np.column_stack((plano.u, plano.v)) @ m[:2, :2]
        matriz4[:3, 3] = plano.a_3d(*m[:2, 2])
        # Con escala uniforme se conserva la representación analítica de círculos y elipses en OCC.
        escala = float(np.linalg.norm(m[:2, 0]))
        uniforme = np.allclose(m[:2, :2].T @ m[:2, :2], np.eye(2) * escala ** 2,
                              rtol=1e-10, atol=escala ** 2 * 1e-12)
        matriz4[:3, 2] = plano.normal * (escala if uniforme else 1.)
        factor = abs(float(np.linalg.det(m[:2, :2])))
        for p in originales:
            q = tuple(m[:2, :2] @ p.centroide_uv + m[:2, 2])
            nuevo = Perfil(None, p.area * factor, q, p.firma,
                           fabrica=partial(_cara_de_objeto, p, matriz4))
            nuevo.objeto = clave[1]
            nuevo.centroide_local = p.centroide_uv
            perfiles.append(nuevo)
    for p in perfiles:
        p.plano_boceto = plano
    perfiles.sort(key=lambda p: (round(p.centroide_uv[0], 4), round(p.centroide_uv[1], 4), p.area))
    return perfiles


def _cara_de_objeto(perfil, matriz4):
    """Sketch.profiles de un recurso rígido: transforma la cara local sin volver a intersectar curvas."""
    from .solidos_modificar import transformar
    if np.array_equal(matriz4, np.eye(4)):
        return perfil.cara
    caras = geo.caras(transformar(perfil.cara, matriz4))
    if len(caras) != 1:
        raise geo.ErrorGeometria("La transformación del perfil no produjo una única cara.")
    return caras[0]


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


def _sin_despacho(funcion):
    """La función sin la envoltura de `motor.registrar`: esa revisa los argumentos y el motor en cada llamada (~10 µs
    y, con listas grandes, mucho más), y estas se llaman una vez por cara o por arista (BOC-28)."""
    return getattr(funcion, "__wrapped__", funcion)


def _origen_aristas(aristas, por_cara, sp):
    """{hash de arista de las caras: id de la curva del boceto de la que salió}.

    Las aristas que el Splitter partió se siguen por su historial (`Modified`: ~20 µs cada una). Las que no se
    partieron las copia sin historial: se reconocen por su punto medio (la copia es idéntica)."""
    from scipy.spatial import cKDTree
    punto_medio = _sin_despacho(_punto_medio)
    origen, sin_hijas = {}, []
    for i, (cid, e) in enumerate(aristas):
        hijas = geo.lista_occ(sp.Modified(e))
        for hija in hijas:
            origen.setdefault(hash(hija), cid)
        if not hijas:
            sin_hijas.append(i)
    if not sin_hijas:
        return origen
    fuente = [(i, m) for i, m in ((i, punto_medio(aristas[i][1])) for i in sin_hijas) if m is not None]
    unicas = {}
    for ar in por_cara:
        for a in ar:
            if hash(a) not in origen:
                unicas.setdefault(hash(a), a)
    destino = [(h, m) for h, m in ((h, punto_medio(a)) for h, a in unicas.items()) if m is not None]
    if fuente and destino:
        arbol = cKDTree(np.array([m for _i, m in fuente]))
        dist, idx = arbol.query(np.array([m for _h, m in destino]))
        for (h, _m), d, k in zip(destino, dist, idx, strict=True):
            if d < 1e-7:
                origen[h] = aristas[fuente[k][0]][0]
    return origen


def _fabrica_caras(plano, prims, r):
    """`cara(i)`: arma a pedido la cara exacta del perfil `i` del arreglo planar `r` (BOC-28), con tramos de las curvas del
    boceto recortados en las intersecciones (sin Splitter). Las vecinas comparten vértices y aristas. Son cierres
    sueltos, no métodos: así la envoltura de `motor.registrar` se paga una vez por boceto y no por arista."""
    pieza, tramo = r[1].tolist(), r[2].tolist()                    # (curva, vértice inicial, final), (t0, t1)
    ciclo_ptr, semi_ptr, semi = r[7].tolist(), r[8].tolist(), r[9].tolist()
    xyz = (plano.origen + np.outer(r[0][:, 0], plano.u) + np.outer(r[0][:, 1], plano.v)).tolist()
    plano_occ = gp_Pln(plano.pnt(0, 0), gp_Dir(*plano.normal))
    vertices, aristas, curvas = {}, {}, {}

    def vertice(i):
        if i not in vertices:
            vertices[i] = BRepBuilderAPI_MakeVertex(gp_Pnt(*xyz[i])).Vertex()
        return vertices[i]

    def arista(h):
        if h not in aristas:
            e = h >> 1
            if h & 1:
                aristas[h] = TopoDS.Edge(arista(h - 1).Reversed())
                return aristas[h]
            k, va, vb = pieza[e]
            prim = prims[k]
            if prim[0] == "linea":
                creador = BRepBuilderAPI_MakeEdge(vertice(va), vertice(vb))
            else:
                if k not in curvas:
                    if prim[0] == "spline":
                        curvas[k] = _curva_bspline(plano, prim[2], prim[3], prim[4], prim[5])
                    else:
                        curvas[k] = Geom_Circle(gp_Circ(plano.ax2(*prim[2]), prim[3]))
                creador = BRepBuilderAPI_MakeEdge(curvas[k], vertice(va), vertice(vb), *tramo[e])
            if not creador.IsDone():
                raise geo.ErrorGeometria("No se pudo armar un perfil del boceto.")
            aristas[h] = creador.Edge()
        return aristas[h]

    def cara(i):
        alambres = []
        for c in range(ciclo_ptr[i], ciclo_ptr[i + 1]):
            alambre = BRepBuilderAPI_MakeWire()
            for h in semi[semi_ptr[c]:semi_ptr[c + 1]]:
                alambre.Add(arista(h))
            if not alambre.IsDone():
                raise geo.ErrorGeometria("No se pudo armar un perfil del boceto.")
            alambres.append(alambre.Wire())
        creador = BRepBuilderAPI_MakeFace(plano_occ, alambres[0], True)
        for hueco in alambres[1:]:
            creador.Add(hueco)
        return creador.Face()
    return cara


def _datos_rust(geometria):
    """(primitivas que entran, arreglos para `_rs.arreglo_planar`), o None si hay algo que Rust no hace (elipses…).
    Descarta las mismas primitivas que `aristas_boceto`."""
    prims, tipos, params, info, polos, pesos, nudos = [], [], [], [], [], [], []
    for prim in geometria:
        tipo = prim[0]
        if tipo in ("elipse", "arco_elipse"):
            return None
        if not _finita(prim):
            continue
        fila, inf = [0.0] * 6, [0, 0, 0, 0]
        if tipo == "linea":
            (u1, v1), (u2, v2) = prim[2], prim[3]
            if math.hypot(u2 - u1, v2 - v1) < 1e-9:
                continue
            codigo, fila[:4] = 0, [u1, v1, u2, v2]
        elif tipo in ("circulo", "arco"):
            (cu, cv), r = prim[2], prim[3]
            if r <= 1e-9:
                continue
            codigo, fila[:3] = (1 if tipo == "circulo" else 2), [cu, cv, r]
            if tipo == "arco":
                a0, a1 = prim[4], prim[5]
                while a1 <= a0 + 1e-12:
                    a1 += 2 * math.pi
                fila[3:5] = [a0, a1]
        elif tipo == "spline":
            ps, ks, grado, ws = prim[2], prim[3], prim[4], prim[5]
            if max(abs(q[0] - ps[0][0]) + abs(q[1] - ps[0][1]) for q in ps[1:]) < 1e-9:
                continue
            expandidos, ultimo = [], None              # los nudos que ve OpenCascade: únicos con su multiplicidad
            for k in ks:
                expandidos.append(k if ultimo is None or abs(k - ultimo) >= 1e-12 else ultimo)
                ultimo = expandidos[-1]
            if len(ws or ps) != len(ps) or len(expandidos) != len(ps) + grado + 1:
                return None
            codigo, inf = 3, [grado, len(pesos), len(ps), len(nudos)]
            polos += [list(map(float, q)) for q in ps]
            pesos += [float(w) for w in ws] if ws else [1.0] * len(ps)
            nudos += expandidos
        else:
            continue
        prims.append(prim)
        tipos.append(codigo)
        params.append(fila)
        info.append(inf)
    arreglos = (np.array(tipos, np.int64), np.array(params, float).reshape(-1, 6), np.array(info, np.int64).reshape(-1, 4),
                np.array(polos, float).reshape(-1, 2), np.array(pesos, float), np.array(nudos, float))
    if prims and max(np.abs(arreglos[1]).max(), np.abs(arreglos[3]).max(initial=0.0)) > _TAM_CARA / 4:
        return None                    # fuera del rango de la cara enorme que parte el camino de referencia
    return prims, arreglos


def _arreglo_coherente(r):
    """True si el arreglo planar `r` tiene sus regiones: en un grafo plano son aristas − vértices + componentes. Un
    cruce casi tangente puede desordenar las curvas en un vértice, y Rust une caras sin avisar (B-137: el disco
    desaparece cuando la base de una letra apoya sobre el círculo)."""
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    nv, piezas = len(r[0]), r[1]
    grafo = coo_matrix((np.ones(len(piezas)), (piezas[:, 1], piezas[:, 2])), shape=(nv, nv))
    return len(r[3]) == len(piezas) - nv + connected_components(grafo, directed=False)[0]


def _detectar_rust(geometria, plano, tolerancia=1e-4):
    """Los perfiles por el arreglo planar en Rust (BOC-28), o None si el módulo no está o no puede resolver este
    boceto con certeza (tangentes en un cruce, curvas superpuestas, elipses…): entonces rige la referencia."""
    rs = nativo.disponible()
    datos = _datos_rust(geometria) if rs is not None else None
    if datos is None:
        return None
    prims, arreglos = datos
    if not prims:
        return []
    try:
        r = rs.arreglo_planar(*arreglos, float(tolerancia))
    except ValueError:
        return None
    if not _arreglo_coherente(r):
        return None
    cara = _fabrica_caras(plano, prims, r)
    areas, centros, puntero, indices, cajas = r[3].tolist(), r[4].tolist(), r[5].tolist(), r[6].tolist(), r[10].tolist()
    ids, firmas, salida = [p[1] for p in prims], {}, []
    for i, area in enumerate(areas):
        curvas = tuple(indices[puntero[i]:puntero[i + 1]])
        if curvas not in firmas:
            firmas[curvas] = frozenset(ids[k] for k in curvas if ids[k] is not None)
        salida.append(Perfil(None, area, tuple(centros[i]), firmas[curvas], partial(cara, i), tuple(cajas[i])))
    salida.sort(key=lambda p: (round(p.centroide_uv[0], 4), round(p.centroide_uv[1], 4), p.area))
    return salida


def _es_cinta(area, largo):
    """True si un perfil de ese `area` y esa diagonal es una cinta de menos de 1 µm de ancho, mucho más larga que ancha:
    el resto entre dos curvas casi apoyadas (la base de una letra sobre un círculo). Un cuadrado de 1 µm es chico, pero
    es un perfil."""
    return area < 1.0 and area < largo * min(1e-3, largo / 100)


def cara_sin_area(cara):
    """True si la cara de un perfil es una cinta sin área (`_es_cinta`): extruirla no da un sólido."""
    area = geo.area(cara)
    return area < 1.0 and _es_cinta(area, math.dist(*geo.caja_envolvente(cara)))


def _sin_area(p):
    if p.area >= 1.0:
        return False
    return _es_cinta(p.area, math.hypot(p.caja_uv[2] - p.caja_uv[0], p.caja_uv[3] - p.caja_uv[1]) if p.caja_uv
                     else math.dist(*geo.caja_envolvente(p.cara)))


def _detectar(geometria, plano, tolerancia=1e-4):
    perfiles = _detectar_rust(geometria, plano, tolerancia)
    if perfiles is None:
        perfiles = _detectar_occ(geometria, plano, tolerancia)
    return [p for p in perfiles if not _sin_area(p)]


def _detectar_occ(geometria, plano, tolerancia=1e-4):
    """Camino de referencia: parte una cara enorme con las curvas (BRepAlgoAPI_Splitter)."""
    aristas = aristas_boceto(geometria, plano)
    if not aristas:
        return []
    perfiles, partidas = _perfiles_occ(geometria, plano, aristas, tolerancia)
    malas = [p.cara for p in perfiles if not geo.es_valida(p.cara)]
    if malas:
        corregidas = _partir_cruces(malas, partidas)
        if corregidas is not partidas:
            # La primera pasada ya unió los extremos difusos; no volver a fundir los cruces recién partidos.
            perfiles, _ = _perfiles_occ(geometria, plano, corregidas, min(tolerancia, 1e-7))
        # La región que no se pudo reparar no se ofrece como perfil (Fusion tampoco la ofrece): el boceto sigue
        # andando y nadie puede extruir una cara imposible (B-195).
        perfiles = [p for p in perfiles if geo.es_valida(p.cara)]
    return perfiles


def _partir_cruces(caras, aristas):
    """Sketch.profiles: parte solo los cruces interiores que el arreglo planar dejó en caras inválidas."""
    from OCP.GeomAPI import GeomAPI_ExtremaCurveCurve
    from OCP.Standard import Standard_OutOfRange
    from OCP.TopExp import TopExp
    bordes = list({hash(a): a for c in caras for a in _aristas_de(c)}.values())
    cajas = _cajas(bordes)
    curvas = [BRep_Tool.Curve_s(a, 0., 0.) for a in bordes]
    limites = [(BRepAdaptor_Curve(a).FirstParameter(), BRepAdaptor_Curve(a).LastParameter()) for a in bordes]
    puntas = [[(BRep_Tool.Pnt_s(v), BRep_Tool.Tolerance_s(v) + 1e-7)
               for v in (TopExp.FirstVertex_s(a), TopExp.LastVertex_s(a))] for a in bordes]
    cortes = {}
    for i, a in enumerate(bordes):
        cerca = np.all((cajas[:, 0] <= cajas[i, 1] + 1e-7) & (cajas[i, 0] <= cajas[:, 1] + 1e-7), axis=1)
        for j in np.flatnonzero(cerca):
            if j <= i or curvas[i] == curvas[j]:
                continue
            extremos = GeomAPI_ExtremaCurveCurve(curvas[i], curvas[j], *limites[i], *limites[j])
            for k in range(1, extremos.NbExtrema() + 1):
                try:
                    distancia = extremos.Distance(k)
                    parametros = extremos.Parameters(k)
                except Standard_OutOfRange:  # curvas coincidentes: OCC puede contar extremos sin puntos
                    continue
                if distancia > 1e-7:
                    continue
                # Los contactos con un extremo ya están unidos con su tolerancia en la primera pasada.
                if any(not limites[indice][0] < t < limites[indice][1] or
                       any(curvas[indice].Value(t).Distance(q) <= tol for q, tol in puntas[indice])
                       for indice, t in zip((i, j), parametros, strict=True)):
                    continue
                for indice, t in zip((i, j), parametros, strict=True):
                    cortes.setdefault(hash(bordes[indice]), set()).add(t)
    if not cortes:
        return aristas
    salida = []
    for cid, arista in aristas:
        if hash(arista) not in cortes:
            salida.append((cid, arista))
            continue
        curva = BRepAdaptor_Curve(arista)
        ts = [curva.FirstParameter(), *sorted(cortes[hash(arista)]), curva.LastParameter()]
        curva = BRep_Tool.Curve_s(arista, ts[0], ts[-1])
        vertices = [TopExp.FirstVertex_s(arista),
                    *(BRepBuilderAPI_MakeVertex(curva.Value(t)).Vertex() for t in ts[1:-1]),
                    TopExp.LastVertex_s(arista)]
        for k, (t0, t1) in enumerate(zip(ts[:-1], ts[1:], strict=True)):
            creador = BRepBuilderAPI_MakeEdge(curva, vertices[k], vertices[k + 1], t0, t1)
            if not creador.IsDone():
                raise geo.ErrorGeometria("No se pudo partir una curva en el cruce de los perfiles del boceto.")
            salida.append((cid, creador.Edge()))
    return salida


def _perfiles_occ(geometria, plano, aristas, tolerancia):
    """Arreglo planar y sus aristas con origen, conservando los vértices unidos por el Splitter."""
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
    sp.SetRunParallel(geo.PARALELO)        # BOC-28: con miles de letras, partir en paralelo tarda ~1/2
    sp.Build()
    if not sp.IsDone():
        raise geo.ErrorGeometria("No se pudieron calcular los perfiles del boceto.")
    aristas_de = _sin_despacho(_aristas_de)
    caras = list(geo.caras(sp.Shape()))
    por_cara = [aristas_de(c) for c in caras]            # una sola pasada por las aristas de cada cara
    origen = _origen_aristas(aristas, por_cara, sp)
    borde = {hash(a) for a in aristas_de(grande)}
    for a in aristas_de(grande):
        borde.update(hash(h) for h in geo.lista_occ(sp.Modified(a)))

    ux, uy, uz = (float(c) for c in plano.u)
    vx, vy, vz = (float(c) for c in plano.v)
    ox, oy, oz = (float(c) for c in plano.origen)
    perfiles = []
    for cara, aristas_cara in zip(caras, por_cara, strict=True):
        hashes = [hash(a) for a in aristas_cara]
        if any(h in borde for h in hashes):
            continue  # región exterior (toca el borde de la cara enorme)
        firma = set()
        for arista, h in zip(aristas_cara, hashes, strict=True):
            cid = origen.get(h)
            if cid is None:          # respaldo geométrico: la curva más cercana al punto medio
                curva = BRepAdaptor_Curve(arista)
                pm = curva.Value((curva.FirstParameter() + curva.LastParameter()) / 2)
                uv = _a_uv(plano, (pm.X(), pm.Y(), pm.Z()))
                mejor = min(geometria, key=lambda prim: distancia_primitiva(prim, uv))
                if distancia_primitiva(mejor, uv) < 1e-3:
                    cid = mejor[1]
            if cid is not None:
                firma.add(cid)
                origen[h] = cid
        props = GProp_GProps()             # cara plana: integración exacta; área y centro en una sola pasada
        BRepGProp.SurfaceProperties_s(cara, props)
        c = props.CentreOfMass()
        dx, dy, dz = c.X() - ox, c.Y() - oy, c.Z() - oz
        perfiles.append(Perfil(cara, props.Mass(), (dx * ux + dy * uy + dz * uz, dx * vx + dy * vy + dz * vz),
                               frozenset(firma)))
    perfiles.sort(key=lambda p: (round(p.centroide_uv[0], 4), round(p.centroide_uv[1], 4), p.area))
    partidas = {hash(a): a for grupo in por_cara for a in grupo if hash(a) not in borde}
    return perfiles, [(origen.get(h), a) for h, a in partidas.items()]


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


def _cara_contiene(cara, uv, plano):
    """True si el punto uv del plano del boceto cae dentro de la cara (o en su borde)."""
    from OCP.BRepClass import BRepClass_FaceClassifier
    from OCP.TopAbs import TopAbs_IN, TopAbs_ON
    return BRepClass_FaceClassifier(cara, plano.pnt(*uv), 1e-7).State() in (TopAbs_IN, TopAbs_ON)


def buscar_por_firma_tolerante(perfiles, firma, centroide=None, plano=None, boceto=None):
    """Busca por firma exacta; si no hay, re-enlaza al perfil que comparte más curvas de la firma

    (un cambio de parámetro degeneró una curva o una nueva curva parte la región), con el centroide
    guardado como desempate y ventaja clara. Si el empate sigue (B-154: una letra y su hueco quedan
    casi en el mismo lugar, y un pedazo viejo de letra no los distingue por el centroide), gana el más
    chico de los que contienen al centroide guardado; el parámetro plano es el del boceto, que ubica
    ese punto sobre las caras. Con el `boceto`, una región que solo partieron curvas nuevas vuelve entera y sin
    aviso, como en Fusion (B-329). Devuelve (perfil, nota) con nota None en el caso exacto o entero,
    o (None, None) si no hay un único candidato claro.
    """
    exacto = buscar_por_firma(perfiles, firma, centroide)
    if exacto is not None:
        return exacto, None
    objetivo = frozenset(firma)
    if boceto is not None and plano is not None:
        # Las curvas que la partieron no son de su firma: sin ellas, el contorno de siempre vuelve a cerrar la región.
        solas = [g for g in boceto.geometria() if g[1] in objetivo]
        entera = buscar_por_firma(detectar_boceto(boceto, plano, solas), objetivo, centroide)
        if entera is not None:
            return entera, None
    candidatos = [p for p in perfiles if p.firma & objetivo]
    if not candidatos:
        return None, None
    dif = lambda p: len(p.firma ^ objetivo)
    candidatos.sort(key=dif)
    mejor = candidatos[0]
    iguales = [p for p in candidatos if dif(p) == dif(mejor)]
    if len(iguales) > 1:
        if centroide is None:
            return None, None
        iguales.sort(key=lambda p: math.dist(p.centroide_uv, centroide))
        d0, d1 = math.dist(iguales[0].centroide_uv, centroide), math.dist(iguales[1].centroide_uv, centroide)
        if d1 <= 1e-12 or d0 >= 0.25 * d1:
            if plano is None:
                return None, None
            adentro = [p for p in iguales if p.cara is not None and _cara_contiene(p.cara, centroide, plano)]
            if not adentro:
                return None, None
            mejor = min(adentro, key=lambda p: p.area)
        else:
            mejor = iguales[0]
    return mejor, ("El perfil se re-vinculó con firma parcial: un cambio del boceto alteró su "
                   "contorno (revisá la operación).")


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
    lejano = max(polos, key=lambda q: math.dist(polos[0], q))      # en una curva cerrada el último polo es el primero
    if all(abs((q[0] - polos[0][0]) * (lejano[1] - polos[0][1]) - (q[1] - polos[0][1]) * (lejano[0] - polos[0][0]))
           < 1e-9 * max(1.0, math.dist(polos[0], lejano) ** 2) for q in polos):
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
    voltear_h, voltear_v, kerning, inclinacion, escala_h, escala_v, desfase_base, capitalizacion, subrayado,
    tachado, grosor_decoracion, sin_division. Usa fontTools; si la fuente no está en el catálogo cae al administrador de
    OpenCascade (que ignora las opciones)."""
    from . import fuentes
    try:
        return fuentes.contornos_texto(texto, fuente, altura, negrita, cursiva, **opciones)
    except fuentes.ErrorFuente as e:
        if fuentes.resolver_fuente(fuente) is not None:       # la fuente existe: el error es de las opciones
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


PLAZO_SILUETA = 3.0      # s para el HLR exacto de una forma libre, en un proceso aparte (la bala con empalme: 0,01 s)
POLOS_EXACTO = 300       # polos B-spline: con más, la silueta sale de la malla (H-80; bala 60, rosca M8 de 12 mm 780)
TOL_SILUETA = 0.01       # mm: lo más que se aleja una curva ajustada del borde de la sombra de la malla (H-78)
DESVIO_SILUETA = 0.03    # mm: desvío de la malla de la sombra; con TOL_SILUETA, la curva queda a < 0,05 mm (H-78)


def _hlr_exacto(forma, plano):
    """Aristas del HLR exacto de OpenCascade (aristas y siluetas, visibles y ocultas) llevadas al plano del boceto."""
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
    from OCP.HLRAlgo import HLRAlgo_Projector
    from OCP.HLRBRep import HLRBRep_Algo, HLRBRep_HLRToShape
    from OCP.gp import gp_Trsf
    ax2 = gp_Ax2(plano.pnt(0, 0), gp_Dir(*map(float, plano.normal)), gp_Dir(*map(float, plano.u)))
    algo = HLRBRep_Algo()
    algo.Add(forma)
    algo.Projector(HLRAlgo_Projector(ax2))
    algo.Update()
    algo.Hide()
    conv = HLRBRep_HLRToShape(algo)
    t = gp_Trsf()
    t.SetTransformation(gp_Ax3(ax2), gp_Ax3())          # del plano XY del proyector al plano del boceto
    aristas = []
    for nombre in ("VCompound", "OutLineVCompound", "Rg1LineVCompound", "HCompound", "OutLineHCompound",
                   "Rg1LineHCompound"):
        c = getattr(conv, nombre)()
        if c is not None and not c.IsNull():
            BRepLib.BuildCurves3d_s(c)                 # el HLR da aristas 2D: sin curva 3D no se transforman
            aristas += _aristas_unicas(BRepBuilderAPI_Transform(c, t, True).Shape())
    return aristas


def hlr_exacto_texto(forma, origen, normal, u):
    """`_hlr_exacto` como texto BREP: lo corre `aislado` en un proceso aparte (en una forma libre puede no terminar)."""
    from . import intercambio
    return intercambio.brep_a_texto(geo.compuesto(_hlr_exacto(forma, geo.Plano.desde_marco(origen, normal, u))))


def _polos(forma):
    """Polos de las caras B-spline y Bézier de la forma: mide lo que le cuesta el HLR exacto (H-80)."""
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.GeomAbs import GeomAbs_BezierSurface, GeomAbs_BSplineSurface
    total = 0
    for cara in geo.caras(forma):
        s = BRepAdaptor_Surface(cara)
        if s.GetType() in (GeomAbs_BSplineSurface, GeomAbs_BezierSurface):
            total += s.NbUPoles() * s.NbVPoles()
    return total


def _curvas_ajustadas(puntos, tol):
    """Primitivas por la cadena `puntos` (u, v). Primero se le sacan los dientes de la malla (Douglas-Peucker a tol/2) y
    se corta en las esquinas (más de 25°); cada tramo queda recto si cabe a `tol` de su cuerda o, si no, una B-spline suave
    por sus puntos (GeomAPI_PointsToBSpline a `tol`). Los extremos de cada tramo son puntos de la cadena: los tramos
    seguidos comparten el punto y el perfil cierra. Una cadena cerrada arranca en una esquina, si tiene."""
    from OCP.GeomAPI import GeomAPI_PointsToBSpline
    from OCP.GeomAbs import GeomAbs_C2
    pts = _simplificar([q for k, q in enumerate(puntos) if k == 0 or math.dist(q, puntos[k - 1]) > 1e-9], tol / 2)

    def esquina(a, b, c):
        u, w = np.subtract(b, a), np.subtract(c, b)
        return float(u @ w) < math.cos(math.radians(25)) * float(np.linalg.norm(u) * np.linalg.norm(w))
    if len(pts) > 3 and math.dist(pts[0], pts[-1]) < 1e-9:
        anillo = pts[:-1]
        k = next((k for k in range(len(anillo)) if esquina(anillo[k - 1], anillo[k], anillo[(k + 1) % len(anillo)])), 0)
        pts = anillo[k:] + anillo[:k] + [anillo[k]]
    cortes = [0] + [k for k in range(1, len(pts) - 1) if esquina(pts[k - 1], pts[k], pts[k + 1])] + [len(pts) - 1]
    salida = []
    for k0, k1 in zip(cortes, cortes[1:], strict=False):
        tramo = pts[k0:k1 + 1]
        if len(tramo) == 2 or len(_simplificar(tramo, tol)) == 2:
            if math.dist(tramo[0], tramo[-1]) > 1e-9:
                salida.append(("linea", None, tuple(tramo[0]), tuple(tramo[-1])))
            continue
        arr = Array1_gp_Pnt(1, len(tramo))
        for k, q in enumerate(tramo, start=1):
            arr.SetValue(k, gp_Pnt(float(q[0]), float(q[1]), 0.0))
        try:
            bs = GeomAPI_PointsToBSpline(arr, 3, 8, GeomAbs_C2, tol).Curve()
        except Exception:  # noqa: BLE001 — OCC no ajusta (puntos casi repetidos): queda la poligonal del tramo
            salida += [("linea", None, tuple(a), tuple(b)) for a, b in zip(tramo, tramo[1:], strict=False)
                       if math.dist(a, b) > 1e-9]
            continue
        polos = [(bs.Pole(i).X(), bs.Pole(i).Y()) for i in range(1, bs.NbPoles() + 1)]
        polos[0], polos[-1] = tuple(tramo[0]), tuple(tramo[-1])      # B-spline anclada: sus extremos son estos polos
        nudos = tuple(bs.Knot(i) for i in range(1, bs.NbKnots() + 1) for _ in range(bs.Multiplicity(i)))
        salida.append(("spline", None, tuple(polos), nudos, bs.Degree(), None))
    return salida


def _silueta_malla(forma, plano, caja):
    """Silueta de una forma libre (B-spline: roscas, solevados) por su malla: los triángulos de frente se proyectan y se
    unen en 2D (CrossSection de manifold3d, Clipper2) y el borde de la sombra se ajusta con curvas (`_curvas_ajustadas`).
    Para las que el HLR exacto no conviene: una rosca M8 vista desde su eje no termina en 30 s, y su contorno de malla,
    una vuelta encima de otra, tardaba ~10 s en partir la cara (H-80); así tarda 0,2 s."""
    import manifold3d as m3
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Copy
    escala = math.dist(*caja) if caja else 1.0
    copia = BRepBuilderAPI_Copy(forma, True, False).Shape()     # la malla de la sombra queda en la copia, no en la del visor
    tris = [t for _cara, t in geo.teselar_por_cara(copia, max(escala * 5e-4, DESVIO_SILUETA)) if len(t)]
    if not tris:
        return proyectar_forma(forma, plano)
    tris = np.concatenate(tris).astype(float)
    n = np.asarray(plano.normal, float)
    normal = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    frente = tris[normal @ n > 1e-12 * np.linalg.norm(normal, axis=1)]
    frente = frente[np.argsort(frente.mean(axis=1) @ n)]     # por profundidad: cada tanda tapa una franja y se une rápido
    uv = (frente - plano.origen) @ np.stack([plano.u, plano.v]).T
    partes = [m3.CrossSection(list(c), m3.FillRule.NonZero) for c in np.array_split(uv, max(1, len(uv) // 500))]
    lazos = []
    for lazo in m3.CrossSection.batch_boolean(partes, m3.OpType.Add).to_polygons():
        x, y = lazo[:, 0], lazo[:, 1]
        if abs(float(x @ np.roll(y, -1) - y @ np.roll(x, -1))) / 2 < (escala * 1e-4) ** 2:
            continue                                   # un poro entre caras de la malla que no comparten vértices
        puntos = [tuple(map(float, q)) for q in lazo]
        lazos.append(_curvas_ajustadas(puntos + puntos[:1], TOL_SILUETA))
    return _en_orden(lazos), []


def _en_orden(lazos):
    """Cada lazo arrancando por su punto de menor (u, v), y los lazos en ese orden: así `Boceto.reproyectar` reconoce la
    silueta cuando el cuerpo cambia de medida."""
    claves = []
    for lazo in (lz for lz in lazos if lz):
        inicio = [tuple(round(c, 6) for c in puntos_primitiva(p, 2)[0]) for p in lazo]
        k = inicio.index(min(inicio))
        claves.append((min(inicio), lazo[k:] + lazo[:k]))
    return [p for _clave, lazo in sorted(claves, key=lambda x: x[0]) for p in lazo]


_CACHE_SILUETA, _CACHE_SILUETA_MAX = {}, 32


def silueta_forma(forma, plano, tolerancia=1e-4):
    """Proyectar un cuerpo (Fusion: Project con el filtro Bodies, «projects closed profiles»): el contorno cerrado de
    su sombra sobre el plano del boceto, sin las aristas que quedan adentro. Sirve igual para cuerpos curvos vistos de
    costado (B-119): un cilindro acostado da un rectángulo; un toro desde arriba, sus dos círculos.
    Método: se parte una cara enorme con lo que da el HLR exacto (`_hlr_exacto`), se quedan las regiones cuya normal
    pega en el cuerpo y se unen (ShapeUpgrade_UnifySameDomain junta las caras y las aristas alineadas). Una forma libre
    va al HLR exacto en un proceso aparte, con tope; si es pesada (`POLOS_EXACTO`) o no termina, sale de su malla
    (`_silueta_malla`).
    Devuelve (primitivas, puntos sueltos): cada lazo en orden y arrancando por su punto de menor (u, v), para que
    `Boceto.reproyectar` las reconozca cuando el cuerpo cambia de medida (si cambia la cantidad de tramos, la proyección
    se rehace: `Boceto.rehacer_proyeccion`, H-77)."""
    caja = geo.caja_envolvente(forma)
    # recalcular el timeline sin cambiar el cuerpo no repite el HLR (una rosca tarda segundos): la clave es el texto
    # BREP de la forma (0,05 s en una rosca M8), igual aunque «Recalcular todo» la vuelva a construir; otro paso de
    # rosca con la misma caja da otro texto.
    from . import intercambio
    clave = (hashlib.sha1(intercambio.brep_a_texto(forma, 1).encode()).digest(), _clave_plano(plano), tolerancia)
    if clave in _CACHE_SILUETA:
        prims, puntos = _CACHE_SILUETA[clave]
        return list(prims), list(puntos)
    salida = _silueta(forma, plano, tolerancia, caja)
    if len(_CACHE_SILUETA) >= _CACHE_SILUETA_MAX:
        _CACHE_SILUETA.pop(next(iter(_CACHE_SILUETA)))
    _CACHE_SILUETA[clave] = (tuple(salida[0]), tuple(salida[1]))
    return salida


def _a_vertices(prim, arista, a_uv):
    """La unión difusa mueve los vértices hasta la holgura y deja la curva como estaba: los extremos de una línea o de
    una spline van a los vértices de la arista, para que el boceto los comparta y el perfil cierre."""
    if prim is None or prim[0] not in ("linea", "spline"):
        return prim
    from OCP.TopExp import TopExp
    vs = [a_uv(BRep_Tool.Pnt_s(v)) for v in (TopExp.FirstVertex_s(arista), TopExp.LastVertex_s(arista))]
    inicio = prim[2] if prim[0] == "linea" else prim[2][0]
    if math.dist(vs[1], inicio) < math.dist(vs[0], inicio):
        vs.reverse()
    if prim[0] == "linea":
        return ("linea", None, vs[0], vs[1])
    polos = list(prim[2])
    polos[0], polos[-1] = vs
    return (prim[0], prim[1], polos, *prim[3:])


def _silueta(forma, plano, tolerancia, caja):
    from OCP.BRep import BRep_Builder
    from OCP.BRepTools import BRepTools
    from OCP.IntCurvesFace import IntCurvesFace_ShapeIntersector
    from OCP.ShapeUpgrade import ShapeUpgrade_UnifySameDomain
    from OCP.TopAbs import TopAbs_WIRE
    from OCP.TopoDS import TopoDS_Compound
    from OCP.gp import gp_Lin
    if not geo.es_forma_libre(forma):
        aristas = _hlr_exacto(forma, plano)
    elif _polos(forma) > POLOS_EXACTO:
        return _silueta_malla(forma, plano, caja)
    else:                                   # forma libre chica (empalmes, solevados): exacta, aparte y con tope
        from . import aislado, intercambio
        try:
            aristas = _aristas_unicas(intercambio.forma_de_texto(aislado.correr(
                "silueta_exacta", forma, PLAZO_SILUETA, origen=[float(x) for x in plano.origen],
                normal=[float(x) for x in plano.normal], u=[float(x) for x in plano.u])))
        except aislado.TareaAislada:
            return _silueta_malla(forma, plano, caja)
    if not aristas:
        return proyectar_forma(forma, plano)            # sin área a la vista (un punto, una arista suelta)
    normal = gp_Dir(*map(float, plano.normal))
    grande = BRepBuilderAPI_MakeFace(gp_Pln(plano.pnt(0, 0), normal), -_TAM_CARA, _TAM_CARA, -_TAM_CARA,
                                     _TAM_CARA).Face()
    args, herramientas = List_TopoDS_Shape(), List_TopoDS_Shape()
    args.Append(grande)
    for e in aristas:
        herramientas.Append(e)
    sp = BRepAlgoAPI_Splitter()
    sp.SetArguments(args)
    sp.SetTools(herramientas)
    sp.SetFuzzyValue(max(tolerancia, math.dist(*caja) * 5e-5 if caja else 0.0))   # el HLR de un toro deja huecos ~1e-5
    sp.Build()
    if not sp.IsDone():
        raise geo.ErrorGeometria("No se pudo calcular la silueta del cuerpo.")
    borde = {hash(a) for a in _aristas_unicas(grande)}
    for a in _aristas_unicas(grande):
        borde.update(hash(h) for h in geo.lista_occ(sp.Modified(a)))
    rayo = IntCurvesFace_ShapeIntersector()
    rayo.Load(forma, 1e-7)
    constructor, sombra, hay = BRep_Builder(), TopoDS_Compound(), False
    constructor.MakeCompound(sombra)
    for cara in geo.caras(sp.Shape()):
        if any(hash(a) in borde for a in _aristas_unicas(cara)):
            continue                                    # la región de afuera (toca el borde de la cara enorme)
        try:
            adentro = geo.punto_dentro(cara)
        except geo.ErrorGeometria:
            continue                                    # una astilla sin área (dos curvas casi encimadas)
        rayo.Perform(gp_Lin(gp_Pnt(*map(float, adentro)), normal), -1e12, 1e12)
        if rayo.NbPnt():
            constructor.Add(sombra, cara)
            hay = True
    if not hay:
        return proyectar_forma(forma, plano)
    a_uv = lambda p: plano.a_uv((p.X(), p.Y(), p.Z()))  # noqa: E731
    unir = ShapeUpgrade_UnifySameDomain(sombra, True, True, True)
    try:
        unir.Build()
    except Exception:  # noqa: BLE001 — con miles de tramos del teselado (roscas) puede fallar por un tramo casi nulo
        veces = {}                                       # sin unir: el borde son las aristas de una sola región
        for cara in geo.caras(sombra):
            for a in _aristas_unicas(cara):
                veces.setdefault(hash(a), [a, 0])[1] += 1
        prims = [arista_a_primitiva(a, a_uv, tuple(plano.normal)) for a, n in veces.values() if n == 1]
        return [p for p in prims if p is not None], []
    lazos = []
    for cara in geo.caras(unir.Shape()):
        externo = BRepTools.OuterWire_s(cara)
        alambres = [externo] + [TopoDS.Wire(w) for w in geo._explorar(cara, TopAbs_WIRE) if not w.IsSame(externo)]
        for w in alambres:
            # en el orden del alambre (TopExp): BRepTools_WireExplorer se corta si la unión difusa dejó vértices sin
            # compartir y perdía tramos
            lazos.append([p for p in (_a_vertices(arista_a_primitiva(e, a_uv, tuple(plano.normal)), e, a_uv)
                                      for e in _aristas_unicas(w)) if p])
    return _en_orden(lazos), []


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


def _simplificar(puntos, tolerancia):
    """Douglas-Peucker: la polilínea con los menos vértices que quedan a `tolerancia` de la original."""
    if len(puntos) < 3:
        return list(puntos)
    a, b = np.asarray(puntos[0], float), np.asarray(puntos[-1], float)
    ab = b - a
    largo = float(np.linalg.norm(ab))
    resto = np.asarray(puntos[1:-1], float) - a
    d = np.linalg.norm(resto, axis=1) if largo < 1e-12 else np.abs(resto[:, 0] * ab[1] - resto[:, 1] * ab[0]) / largo
    k = int(np.argmax(d))
    if d[k] <= tolerancia:
        return [puntos[0], puntos[-1]]
    return _simplificar(puntos[:k + 2], tolerancia)[:-1] + _simplificar(puntos[k + 1:], tolerancia)


def proyectar_giro_forma(forma, plano, eje, tolerancia=0.1, invertir=False, muestras=64):
    """Perfil giratorio (Fusion: Project/Include > Spun Profile): gira la forma alrededor de `eje` (punto, dirección) y
    deja su perfil sobre el plano del boceto. Cada punto va a (h, r): h a lo largo del eje y r su distancia a él, sobre la
    proyección del eje en el plano (r hacia +u del boceto, o +v si el eje corre a lo largo de u; al lado contrario con `invertir`). Las aristas se muestrean y se
    simplifican a segmentos que quedan a `tolerancia` mm de la curva. Devuelve (primitivas, puntos sueltos (u, v)).
    shortcut: gira todas las aristas, sin sacar las que quedan dentro del cuerpo (no es solo el contorno exterior)."""
    p0, d = np.asarray(eje[0], float), np.asarray(eje[1], float)
    d = d / (np.linalg.norm(d) or 1.0)
    n = np.asarray(plano.normal, float)
    d2 = d - n * float(d @ n)
    largo = float(np.linalg.norm(d2))
    if largo < 1e-9:
        raise geo.ErrorGeometria("El eje es perpendicular al plano del boceto: no hay perfil giratorio que proyectar.")
    d2 = d2 / largo
    v2 = np.cross(n, d2)
    lado = float(v2 @ plano.u) if abs(float(v2 @ plano.u)) > 1e-9 else float(v2 @ plano.v)
    v2 = v2 * (-1.0 if (lado < 0) != bool(invertir) else 1.0)       # por defecto, r va hacia +u (o +v si el eje es horizontal)
    q = p0 - n * float((p0 - plano.origen) @ n)

    def a_uv(p):
        rel = np.array([p.X(), p.Y(), p.Z()]) - p0
        h = float(rel @ d)
        r = float(np.linalg.norm(rel - h * d))
        return plano.a_uv(q + d2 * h + v2 * r)
    prims = []
    for e in _aristas_unicas(forma):
        curva = BRepAdaptor_Curve(e)
        f, l = curva.FirstParameter(), curva.LastParameter()
        ts = np.linspace(f, l, muestras)
        pts = _simplificar([a_uv(curva.Value(float(t))) for t in ts], tolerancia)
        prims += [("linea", None, a, b) for a, b in zip(pts, pts[1:], strict=False) if math.dist(a, b) > 1e-9]
    prims += _frentes_en_el_eje(forma, p0, d, a_uv)
    if prims:
        return prims, []
    return [], [a_uv(p) for p in _vertices(forma)]


def _frentes_en_el_eje(forma, p0, d, a_uv):
    """Una cara que corta el eje (la tapa de un cilindro, el fondo de una caja) gira en un disco que llega hasta el eje,
    pero sus aristas giradas se quedan en su radio menor. Por cada corte, el segmento radial desde el eje (r = 0) hasta
    el vértice más lejano de esa cara a la misma altura: así el perfil giratorio cierra contra el eje.
    shortcut: solo usa los vértices de la cara a la altura del corte (tapas planas); una cara inclinada que corta el eje
    sin vértices a esa altura no suma frente."""
    from OCP.IntCurvesFace import IntCurvesFace_ShapeIntersector
    from OCP.gp import gp_Lin
    rayo = IntCurvesFace_ShapeIntersector()
    rayo.Load(forma, 1e-7)
    rayo.Perform(gp_Lin(gp_Pnt(*map(float, p0)), gp_Dir(*map(float, d))), -1e12, 1e12)
    salida = []
    for i in range(1, rayo.NbPnt() + 1):
        corte = np.array(rayo.Pnt(i).Coord())
        h = float((corte - p0) @ d)
        lejos = [q for q in (np.array(v.Coord()) for v in _vertices(rayo.Face(i))) if abs(float((q - p0) @ d) - h) < 1e-6]
        if lejos:
            q = max(lejos, key=lambda q: float(np.linalg.norm((q - p0) - d * float((q - p0) @ d))))
            a, b = a_uv(gp_Pnt(*corte)), a_uv(gp_Pnt(*q))
            if math.dist(a, b) > 1e-9:
                salida.append(("linea", None, a, b))
    return salida


_motor.registrar(globals(), _iniciar_opencascade)

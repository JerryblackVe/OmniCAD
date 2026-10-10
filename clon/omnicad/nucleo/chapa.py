# -*- coding: utf-8 -*-
"""
Chapa: el entorno SHEET METAL de Fusion 360 [GUID-309ACAF1]. Reglas [SM-RULES-REF], pestaña base, de arista
y de contorno [SM-REF-BASE-EDGE-CONTOUR-FLANGE], dobladillo [SM-CREATE-HEM-FLANGE], plegar [GUID-D11BA900],
desgarro [SM-RIP], unir plegando [SM-CREATE-JOIN-BY-BEND], desplegar/replegar [GUID-5125C823], patrón plano
[GUID-7EBD9424], exportar el patrón a DXF [GUID-9C211F95] y convertir a chapa [SM-TO-CONVERT-TO-SM].

Modelo «patrón plano maestro». Una pieza de chapa son DATOS simples (dicts, listas y números; van a JSON):
  - "regla": espesor t, radio de plegado R, factor K, alivios de plegado y de esquina, separación.
  - "marco": matriz 4x4 que lleva las coordenadas planas (x, y, w) de la placa raíz al mundo; w ∈ [0, t].
  - "placas": regiones 2D del patrón plano (caras = lazos de primitivas ["l", x0, y0, x1, y1],
    ["a", cx, cy, r, a0, a1] con barrido con signo, ["c", cx, cy, r]); una por cada parte plana.
  - "pliegues": franjas del patrón plano entre una placa padre y una hija: línea de inicio (punto "o" y normal
    "n" hacia la hija), ancho desarrollado "ba" = ángulo·(R + K·t), "tramos" [η0, η1] a lo largo del eje
    a = n × w, radio interior, ángulo, "sentido" (+1: la hija sube hacia +w) y si está desplegado.
Plegar es componer, desde la placa raíz, la transformación rígida de cada pliegue (cerrar la franja y girar la
hija alrededor del eje); cada tramo de franja se vuelve una cáscara cilíndrica de radios R y R + t. El patrón
plano es exacto por construcción (con el factor K) y desplegar/replegar ida y vuelta no pierde nada.
"""
import copy
import math
from pathlib import Path

import numpy as np
from OCP.BRep import BRep_Tool
from OCP.BRepAdaptor import BRepAdaptor_Curve, BRepAdaptor_Surface
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common, BRepAlgoAPI_Cut, BRepAlgoAPI_Fuse
from OCP.BRepBuilderAPI import (BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakePolygon,
                                BRepBuilderAPI_MakeVertex, BRepBuilderAPI_MakeWire)
from OCP.BRepClass import BRepClass_FaceClassifier
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism, BRepPrimAPI_MakeRevol
from OCP.BRepTools import BRepTools, BRepTools_WireExplorer
from OCP.GC import GC_MakeArcOfCircle
from OCP.GCPnts import GCPnts_QuasiUniformDeflection
from OCP.GeomAbs import GeomAbs_Circle, GeomAbs_Cylinder, GeomAbs_Line, GeomAbs_Plane
from OCP.gp import gp_Ax1, gp_Ax2, gp_Circ, gp_Dir, gp_Pnt, gp_Vec
from OCP.OCP.collections import List_TopoDS_Shape
from OCP.ShapeUpgrade import ShapeUpgrade_UnifySameDomain
from OCP.TopAbs import TopAbs_EDGE, TopAbs_IN, TopAbs_ON, TopAbs_REVERSED, TopAbs_VERTEX, TopAbs_WIRE
from OCP.TopExp import TopExp_Explorer
from OCP.TopoDS import TopoDS

from . import geometria as geo

TOL = 1e-5              # mm: coincidencia de puntos y rectas del patrón plano
_DELTA = 1e-3           # mm: paso para probar de qué lado de un borde hay material
_MARGEN = 0.05          # mm: los recortes pasan un poco del borde para no dejar astillas
_ANCHO_DESGARRO = 0.01  # mm: el alivio «desgarro» se modela como un corte finísimo

# ---------------------------------------------------------------- reglas
# Aproximaciones honestas de la biblioteca de Fusion: radio = espesor y K = 0,44 (los valores por defecto de
# Fusion); alivio de plegado redondo de ancho t y profundidad t/2; esquina recortada al pliegue; separación t.
# Como en Fusion, la regla trae su material físico (clave de analisis.TABLA_MATERIALES): el cuerpo lo toma.
REGLAS = {
    "Acero 1 mm": {"espesor": 1.0, "k": 0.44, "material": "Acero"},
    "Acero 2 mm": {"espesor": 2.0, "k": 0.44, "material": "Acero"},
    "Aluminio 1.5 mm": {"espesor": 1.5, "k": 0.44, "material": "Aluminio 6061"},
    "Acero inoxidable 1.2 mm": {"espesor": 1.2, "k": 0.44, "material": "Acero inoxidable"},
}
REGLA_DEFECTO = "Acero 1 mm"
FORMAS_ALIVIO = {"redondo": "Redondo", "recto": "Recto", "desgarro": "Desgarro"}
FORMAS_ESQUINA = {"recortar": "Recortar al pliegue", "redondo": "Redondo", "cuadrado": "Cuadrado",
                  "desgarro": "Desgarro"}
CAMPOS_REGLA = ("espesor", "radio", "k", "alivio_forma", "alivio_ancho", "alivio_profundidad", "esquina_forma",
                "esquina_tam", "separacion")


def regla(nombre=REGLA_DEFECTO, **ajustes):
    """Regla de chapa (dict) a partir de una regla de la biblioteca y ajustes ("Override rules"). Como en
    Fusion, los valores que dependen del espesor (radio, alivios, separación) lo siguen si no se ajustan."""
    if nombre not in REGLAS:
        raise geo.ErrorGeometria(f"Regla de chapa desconocida: {nombre}")
    ajustes = {k: v for k, v in ajustes.items() if v is not None}
    desconocidos = set(ajustes) - set(CAMPOS_REGLA)
    if desconocidos:
        raise geo.ErrorGeometria(f"Campos de regla desconocidos: {', '.join(sorted(desconocidos))}")
    t = float(ajustes.get("espesor", REGLAS[nombre]["espesor"]))
    r = {"nombre": nombre, "espesor": t, "radio": t, "k": REGLAS[nombre]["k"], "alivio_forma": "redondo",
         "alivio_ancho": t, "alivio_profundidad": t / 2, "esquina_forma": "recortar", "esquina_tam": 4 * t,
         "separacion": t, "material": REGLAS[nombre]["material"]}
    r.update(ajustes)
    for k in ("espesor", "radio", "k", "alivio_ancho", "alivio_profundidad", "esquina_tam", "separacion"):
        r[k] = float(r[k])
    if r["espesor"] <= 0:
        raise geo.ErrorGeometria("El espesor de la chapa tiene que ser positivo.")
    if r["radio"] < 0:
        raise geo.ErrorGeometria("El radio de plegado no puede ser negativo.")
    if not 0.0 <= r["k"] <= 1.0:
        raise geo.ErrorGeometria("El factor K va de 0 a 1 (posición de la fibra neutra dentro del espesor).")
    if r["alivio_ancho"] <= 0 or r["alivio_profundidad"] < 0 or r["esquina_tam"] <= 0 or r["separacion"] <= 0:
        raise geo.ErrorGeometria("Los alivios y la separación tienen que ser positivos.")
    if r["alivio_forma"] not in FORMAS_ALIVIO or r["esquina_forma"] not in FORMAS_ESQUINA:
        raise geo.ErrorGeometria("Forma de alivio desconocida.")
    return r


def longitud_pliegue(angulo, radio, espesor, k):
    """Longitud desarrollada del pliegue (bend allowance): BA = ángulo · (R + K·t), ángulo en grados."""
    return math.radians(angulo) * (radio + k * espesor)


# ---------------------------------------------------------------- matrices 4x4
def _tras(v):
    m = np.eye(4)
    m[:3, 3] = v
    return m


def _rot(punto, eje, angulo_rad):
    a = np.asarray(eje, float) / np.linalg.norm(eje)
    k = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    r = np.eye(3) + math.sin(angulo_rad) * k + (1 - math.cos(angulo_rad)) * (k @ k)
    m = np.eye(4)
    m[:3, :3] = r
    p = np.asarray(punto, float)
    m[:3, 3] = p - r @ p
    return m


def _aplicar(m, p):
    return (m @ np.array([p[0], p[1], p[2] if len(p) > 2 else 0.0, 1.0]))[:3]


def marco(origen, u, v, n):
    """Matriz 4x4 (lista) que lleva (x, y, w) planos a origen + x·u + y·v + w·n."""
    m = np.eye(4)
    m[:3, 0], m[:3, 1], m[:3, 2], m[:3, 3] = u, v, n, origen
    return m.tolist()


def _m(modelo):
    return np.array(modelo["marco"], float)


# ---------------------------------------------------------------- regiones 2D (datos ↔ caras OCC en z = 0)
def _pnt(x, y, z=0.0):
    return gp_Pnt(float(x), float(y), float(z))


def _hacia_arriba(cara):
    pln = BRepAdaptor_Surface(cara).Plane()
    nz = pln.Axis().Direction().Z()
    if not pln.Position().Direct():         # ejes indirectos: la normal es −eje
        nz = -nz
    if cara.Orientation() == TopAbs_REVERSED:
        nz = -nz
    return cara if nz > 0 else TopoDS.Face(cara.Reversed())


def _arista_prim(p):
    if p[0] == "l":
        return BRepBuilderAPI_MakeEdge(_pnt(p[1], p[2]), _pnt(p[3], p[4])).Edge()
    if p[0] == "c":
        return BRepBuilderAPI_MakeEdge(gp_Circ(gp_Ax2(_pnt(p[1], p[2]), gp_Dir(0, 0, 1)), float(p[3]))).Edge()
    cx, cy, r, a0, a1 = p[1:6]
    q = [_pnt(cx + r * math.cos(a), cy + r * math.sin(a)) for a in (a0, (a0 + a1) / 2, a1)]
    return BRepBuilderAPI_MakeEdge(GC_MakeArcOfCircle(*q).Value()).Edge()


def _cara_lazo(lazo):
    mw = BRepBuilderAPI_MakeWire()
    for p in lazo:
        mw.Add(_arista_prim(p))
        if not mw.IsDone():
            raise geo.ErrorGeometria("Un contorno de la chapa no cierra.")
    return _hacia_arriba(BRepBuilderAPI_MakeFace(mw.Wire(), True).Face())


def region_a_caras(region):
    """Caras OCC (plano z = 0, normal +z) de una región del patrón plano."""
    caras = []
    for lazos in region:
        cara = _cara_lazo(lazos[0])
        for hueco in lazos[1:]:
            cara = geo.booleano(cara, _cara_lazo(hueco), "cortar")
        caras.extend(_hacia_arriba(c) for c in geo.caras(cara))
    return caras


def _prims_arista(e, invertida):
    c = BRepAdaptor_Curve(e)
    t0, t1 = c.FirstParameter(), c.LastParameter()
    tipo = c.GetType()
    if tipo == GeomAbs_Line:
        p0, p1 = c.Value(t0), c.Value(t1)
        if invertida:
            p0, p1 = p1, p0
        return [["l", p0.X(), p0.Y(), p1.X(), p1.Y()]]
    if tipo == GeomAbs_Circle:
        ci = c.Circle()
        ce, r = ci.Location(), ci.Radius()
        if abs(abs(t1 - t0) - 2 * math.pi) < 1e-9:
            return [["c", ce.X(), ce.Y(), r]]
        s = 1.0 if ci.Axis().Direction().Z() > 0 else -1.0
        barrido = (t1 - t0) * s * (-1.0 if invertida else 1.0)
        p0 = c.Value(t1 if invertida else t0)
        a0 = math.atan2(p0.Y() - ce.Y(), p0.X() - ce.X())
        return [["a", ce.X(), ce.Y(), r, a0, a0 + barrido]]
    d = GCPnts_QuasiUniformDeflection(c, 0.005)        # elipses y splines: polilínea fina
    pts = [d.Value(i) for i in range(1, d.NbPoints() + 1)]
    if invertida:
        pts.reverse()
    return [["l", a.X(), a.Y(), b.X(), b.Y()] for a, b in zip(pts[:-1], pts[1:], strict=True)]


def _lazo(alambre, cara):
    prims = []
    ex = BRepTools_WireExplorer(alambre, cara)
    while ex.More():
        prims.extend(_prims_arista(ex.Current(), ex.Orientation() == TopAbs_REVERSED))
        ex.Next()
    return prims


def caras_a_region(caras):
    """Región (datos) de caras planas en z = 0: el primer lazo de cada cara es el exterior."""
    region = []
    for cara in caras:
        if geo.area(cara) < 1e-9:
            continue
        externo = BRepTools.OuterWire_s(cara)
        lazos = [_lazo(externo, cara)]
        ex = TopExp_Explorer(cara, TopAbs_WIRE)
        while ex.More():
            w = TopoDS.Wire(ex.Current())
            if not w.IsSame(externo):
                lazos.append(_lazo(w, cara))
            ex.Next()
        region.append(lazos)
    return region


def _unificar(forma):
    u = ShapeUpgrade_UnifySameDomain(forma, True, True, False)
    u.Build()
    return u.Shape()


def _booleana_lista(objetos, herramientas, operacion):
    """Booleana con cada forma como argumento propio: un compuesto de caras que se tocan entre sí no sirve de
    argumento (OCC no interseca las partes de un mismo argumento y deja astillas)."""
    op = {"unir": BRepAlgoAPI_Fuse, "cortar": BRepAlgoAPI_Cut, "intersecar": BRepAlgoAPI_Common}[operacion]()
    args, herr = List_TopoDS_Shape(), List_TopoDS_Shape()
    for x in objetos:
        args.Append(x)
    for x in herramientas:
        herr.Append(x)
    op.SetArguments(args)
    op.SetTools(herr)
    op.Build()
    if not op.IsDone():
        raise geo.ErrorGeometria(f"La operación '{operacion}' falló en el kernel.")
    return _unificar(op.Shape())


def _op2d(a, b, operacion):
    """Booleana entre listas de caras coplanares (z = 0). Devuelve la lista de caras resultante."""
    if not a:
        return list(b) if operacion == "unir" else []
    if not b:
        return [] if operacion == "intersecar" else list(a)
    r = _booleana_lista(a, b, operacion)
    return [_hacia_arriba(c) for c in geo.caras(r) if geo.area(c) > 1e-9]


def _poligono(pts):
    mp = BRepBuilderAPI_MakePolygon()
    for p in pts:
        mp.Add(_pnt(p[0], p[1]))
    mp.Close()
    return _hacia_arriba(BRepBuilderAPI_MakeFace(mp.Wire(), True).Face())


def _rect(o, a, n, e0, e1, x0, x1):
    """Rectángulo del patrón plano: η ∈ [e0, e1] a lo largo de `a` y ξ ∈ [x0, x1] a lo largo de `n`,
    desde `o`."""
    o, a, n = (np.asarray(v, float)[:2] for v in (o, a, n))
    return _poligono([o + e0 * a + x0 * n, o + e1 * a + x0 * n, o + e1 * a + x1 * n, o + e0 * a + x1 * n])


def _disco(c, r):
    e = BRepBuilderAPI_MakeEdge(gp_Circ(gp_Ax2(_pnt(*c), gp_Dir(0, 0, 1)), float(r))).Edge()
    return _hacia_arriba(BRepBuilderAPI_MakeFace(BRepBuilderAPI_MakeWire(e).Wire(), True).Face())


def _estado(caras, p, tol=1e-7):
    """TopAbs_IN, TopAbs_ON o None (afuera) del punto 2D respecto de las caras."""
    estados = {BRepClass_FaceClassifier(c, _pnt(p[0], p[1]), tol).State() for c in caras}
    return TopAbs_IN if TopAbs_IN in estados else (TopAbs_ON if TopAbs_ON in estados else None)


def _dentro(caras, p):
    return _estado(caras, p) == TopAbs_IN


def _area(caras):
    return sum(geo.area(c) for c in caras)


def _distancia(a, b):
    d = BRepExtrema_DistShapeShape(a, b)
    return d.Value() if d.IsDone() else math.inf


def _vertice(p):
    return BRepBuilderAPI_MakeVertex(_pnt(*p)).Vertex()


def _puntos_2d(forma):
    """Vértices y puntos de los arcos (los arcos pueden sobresalir de sus extremos)."""
    salida = []
    ex = TopExp_Explorer(forma, TopAbs_VERTEX)
    while ex.More():
        p = BRep_Tool.Pnt_s(TopoDS.Vertex(ex.Current()))
        salida.append((p.X(), p.Y()))
        ex.Next()
    ex = TopExp_Explorer(forma, TopAbs_EDGE)
    while ex.More():
        c = BRepAdaptor_Curve(TopoDS.Edge(ex.Current()))
        if c.GetType() != GeomAbs_Line:
            for i in range(9):
                q = c.Value(c.FirstParameter() + (c.LastParameter() - c.FirstParameter()) * i / 8)
                salida.append((q.X(), q.Y()))
        ex.Next()
    return salida


# ---------------------------------------------------------------- modelo: pliegues y transformaciones
def _eje(b):
    """Dirección del eje del pliegue en el plano: a = n × w."""
    return np.array([b["n"][1], -b["n"][0]])


def _datos_pliegue(padre, hija, o, n, ba, tramos, radio, angulo, sentido):
    return {"padre": padre, "hija": hija, "o": [float(o[0]), float(o[1])], "n": [float(n[0]), float(n[1])],
            "ba": float(ba), "tramos": [[float(e0), float(e1)] for e0, e1 in tramos], "radio": float(radio),
            "angulo": float(angulo), "sentido": int(sentido), "desplegado": False}


def _plegado(b):
    return not b["desplegado"] and b["angulo"] > 1e-9


def _matriz_pliegue(b, t):
    """Lleva las coordenadas planas de la hija a las coordenadas (plegadas) de la placa padre."""
    if not _plegado(b):
        return np.eye(4)
    o, n, a = np.array([*b["o"], 0.0]), np.array([*b["n"], 0.0]), np.array([*_eje(b), 0.0])
    s, r = b["sentido"], b["radio"]
    p_eje = o + np.array([0.0, 0.0, t + r if s > 0 else -r])
    return _rot(p_eje, a, s * math.radians(b["angulo"])) @ _tras(-b["ba"] * n)


def _hijos(modelo):
    hijos = {}
    for bid, b in modelo["pliegues"].items():
        hijos.setdefault(b["padre"], []).append(bid)
    return hijos


def transformaciones(modelo):
    """{placa: matriz 4x4} de coordenadas planas a coordenadas de la placa raíz, con los pliegues como están
    (plegados o desplegados)."""
    t = modelo["regla"]["espesor"]
    hijos = _hijos(modelo)
    mats = {modelo["raiz"]: np.eye(4)}
    cola = [modelo["raiz"]]
    while cola:
        p = cola.pop()
        for bid in hijos.get(p, []):
            b = modelo["pliegues"][bid]
            mats[b["hija"]] = mats[p] @ _matriz_pliegue(b, t)
            cola.append(b["hija"])
    if len(mats) != len(modelo["placas"]):
        raise geo.ErrorGeometria("El modelo de chapa quedó desconectado.")
    return mats


def _nuevo_id(modelo, prefijo):
    modelo["contador"] = modelo.get("contador", 0) + 1
    return f"{prefijo}{modelo['contador']}"


def modelo_nuevo(regla_chapa, matriz, region):
    """Pieza de una sola placa (pestaña base o chapa convertida)."""
    return {"version": 1, "regla": dict(regla_chapa), "marco": [list(map(float, f)) for f in np.asarray(matriz)],
            "raiz": "p0", "placas": {"p0": region}, "pliegues": {}, "contador": 0, "estacionaria": "p0"}


# ---------------------------------------------------------------- sólidos
def _prisma(cara, t):
    return BRepPrimAPI_MakePrism(cara, gp_Vec(0, 0, float(t))).Shape()


def _pieza_pliegue(b, t, e0, e1):
    """Pieza de un tramo del pliegue en coordenadas de la placa padre: cáscara cilíndrica (plegado) o franja
    plana (desplegado)."""
    o, n, a = np.array(b["o"]), np.array(b["n"]), _eje(b)
    if not _plegado(b):
        return _prisma(_rect(o, a, n, e0, e1, 0.0, b["ba"]), t)
    o3, a3 = np.array([*o, 0.0]), np.array([*a, 0.0])
    mp = BRepBuilderAPI_MakePolygon()
    for p in (o3 + e0 * a3, o3 + e1 * a3, o3 + e1 * a3 + (0, 0, t), o3 + e0 * a3 + (0, 0, t)):
        mp.Add(gp_Pnt(*map(float, p)))
    mp.Close()
    cara = BRepBuilderAPI_MakeFace(mp.Wire(), True).Face()
    s, r = b["sentido"], b["radio"]
    p_eje = o3 + np.array([0.0, 0.0, t + r if s > 0 else -r])
    eje = gp_Ax1(gp_Pnt(*map(float, p_eje)), gp_Dir(*map(float, a3 * s)))
    return BRepPrimAPI_MakeRevol(cara, eje, math.radians(b["angulo"])).Shape()


def _volumen_pliegue(b, t, largo):
    if not _plegado(b):
        return b["ba"] * t * largo
    return math.radians(b["angulo"]) * t * (b["radio"] + t / 2) * largo


def _piezas(modelo, plano=False):
    """[(forma, volumen esperado)] en coordenadas de la placa raíz (plegadas) o del patrón plano (plano=True)."""
    t = modelo["regla"]["espesor"]
    mats = transformaciones(modelo)
    piezas = []
    for pid, region in modelo["placas"].items():
        for c in region_a_caras(region):
            f = _prisma(c, t)
            piezas.append((f if plano else geo.transformar(f, mats[pid]), geo.area(c) * t))
    for b in modelo["pliegues"].values():
        bb = dict(b, desplegado=True) if plano else b
        for e0, e1 in b["tramos"]:
            f = _pieza_pliegue(bb, t, e0, e1)
            piezas.append((f if plano else geo.transformar(f, mats[b["padre"]]), _volumen_pliegue(bb, t, e1 - e0)))
    return piezas


def _fusionar(formas):
    return formas[0] if len(formas) == 1 else _booleana_lista(formas[:1], formas[1:], "unir")


def _armar(piezas, que):
    if not piezas:
        raise geo.ErrorGeometria("La chapa quedó sin material.")
    forma = _fusionar([p for p, _ in piezas])
    esperado = sum(v for _, v in piezas)
    real = geo.volumen(forma)
    if esperado - real > max(1e-6, 1e-7 * esperado):
        raise geo.ErrorGeometria(f"{que}: partes de la chapa se superponen ({esperado - real:.3g} mm³). Probá otra "
                                 "posición del pliegue, menos altura o un alivio de esquina.")
    sols = geo.solidos(forma)
    if len(sols) > 1:
        raise geo.ErrorGeometria(f"{que}: la chapa quedó partida en {len(sols)} piezas sueltas.")
    return sols[0] if sols else forma


def solido(modelo):
    """Sólido 3D de la pieza tal como está (pliegues plegados o desplegados), en el mundo. Falla si partes de la
    chapa se superponen o si quedó partida."""
    return geo.transformar(_armar(_piezas(modelo), "Chapa"), _m(modelo))


def solido_plano(modelo):
    """Patrón plano como sólido, en coordenadas planas (x, y, w)."""
    return _armar(_piezas(modelo, plano=True), "Patrón plano")


def patron_plano(modelo, estacionaria=None):
    """Patrón plano en el mundo, apoyado sobre la placa estacionaria (Create Flat Pattern de Fusion)."""
    pid = estacionaria or modelo.get("estacionaria") or modelo["raiz"]
    return geo.transformar(solido_plano(modelo), _m(modelo) @ transformaciones(modelo)[pid])


# ---------------------------------------------------------------- consultas sobre la pieza
def _recta_2d(p, q, puntos):
    """Posiciones (mm desde p) de los puntos sobre la recta p→q, o None si alguno está fuera de ella."""
    d = np.asarray(q, float) - np.asarray(p, float)
    d = d / np.linalg.norm(d)
    salida = []
    for x in puntos:
        v = np.asarray(x, float) - p
        if abs(v[0] * d[1] - v[1] * d[0]) > TOL:
            return None
        salida.append(float(v @ d))
    return salida


def _fusionar_intervalos(iv):
    salida = []
    for a, b in sorted([min(a, b), max(a, b)] for a, b in iv):
        if salida and a <= salida[-1][1] + TOL:
            salida[-1][1] = max(salida[-1][1], b)
        else:
            salida.append([a, b])
    return salida


def _restar_intervalos(iv, quitar):
    salida = [list(x) for x in iv]
    for q0, q1 in quitar:
        q0, q1 = min(q0, q1), max(q0, q1)
        nuevo = []
        for a, b in salida:
            if q1 <= a + TOL or q0 >= b - TOL:
                nuevo.append([a, b])
                continue
            if q0 > a + TOL:
                nuevo.append([a, q0])
            if q1 < b - TOL:
                nuevo.append([q1, b])
        salida = nuevo
    return [x for x in salida if x[1] - x[0] > TOL]


def _lineas_de_union(modelo, pid):
    """Segmentos (p, q) del borde de la placa donde se pega un pliegue (no son bordes libres)."""
    salida = []
    for b in modelo["pliegues"].values():
        o, n, a = np.array(b["o"]), np.array(b["n"]), _eje(b)
        base = o if b["padre"] == pid else (o + b["ba"] * n if b["hija"] == pid else None)
        if base is not None:
            salida.extend((base + e0 * a, base + e1 * a) for e0, e1 in b["tramos"])
    return salida


def _intervalos_libres(modelo, pid, p, q):
    """Partes del segmento p→q (en mm desde p) que son borde LIBRE de la placa."""
    largo = float(np.linalg.norm(np.asarray(q) - p))
    borde = []
    for lazos in modelo["placas"][pid]:
        for lazo in lazos:
            for prim in lazo:
                if prim[0] == "l":
                    s = _recta_2d(p, q, [prim[1:3], prim[3:5]])
                    if s is not None:
                        borde.append(s)
    borde = [[max(a, 0.0), min(b, largo)] for a, b in _fusionar_intervalos(borde)]
    borde = [x for x in borde if x[1] - x[0] > TOL]
    ocupado = [s for a, b in _lineas_de_union(modelo, pid) if (s := _recta_2d(p, q, [a, b])) is not None]
    return _restar_intervalos(borde, ocupado)


def _segmento_3d(arista):
    c = BRepAdaptor_Curve(arista)
    if c.GetType() != GeomAbs_Line:
        raise geo.ErrorGeometria("Elegí aristas rectas de la chapa.")
    p, q = c.Value(c.FirstParameter()), c.Value(c.LastParameter())
    return np.array([p.X(), p.Y(), p.Z()]), np.array([q.X(), q.Y(), q.Z()])


def ubicar_arista(modelo, arista):
    """(placa, p, q, w, intervalos libres) de una arista recta del borde de una cara plana de la pieza: p y q
    en coordenadas planas, w = 0 (cara de abajo) o t (cara de arriba)."""
    t = modelo["regla"]["espesor"]
    p3, q3 = _segmento_3d(arista)
    f = _m(modelo)
    for pid, mat in transformaciones(modelo).items():
        inv = np.linalg.inv(f @ mat)
        p, q = _aplicar(inv, p3), _aplicar(inv, q3)
        for w in (0.0, t):
            if abs(p[2] - w) < TOL and abs(q[2] - w) < TOL and np.linalg.norm(q[:2] - p[:2]) > TOL:
                libres = _intervalos_libres(modelo, pid, p[:2], q[:2])
                if libres:
                    return pid, p[:2], q[:2], w, libres
    raise geo.ErrorGeometria("La arista elegida no es un borde libre de una cara plana de la chapa (elegí una arista "
                             "del borde de la cara de arriba o de abajo, no la de un pliegue ni la del espesor).")


def _normal_exterior(caras, p, d, s):
    m = p + d * s
    izq = np.array([-d[1], d[0]])
    adentro_izq, adentro_der = _dentro(caras, m + izq * _DELTA), _dentro(caras, m - izq * _DELTA)
    if adentro_izq and not adentro_der:
        return -izq
    if adentro_der and not adentro_izq:
        return izq
    raise geo.ErrorGeometria("La arista elegida no está en el borde de la cara.")


def _punto_en_cara(cara):
    p = np.array(geo.centro_masa(cara, superficie=True))
    if BRepClass_FaceClassifier(cara, gp_Pnt(*map(float, p)), 1e-6).State() == TopAbs_IN:
        return p
    for _c, tris in geo.teselar_por_cara(cara, 0.5):
        if len(tris):
            areas = np.linalg.norm(np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0]), axis=1)
            return tris[int(np.argmax(areas))].mean(axis=0)
    return p


def placa_de_cara(modelo, cara, punto=None):
    """(placa, w) de una cara plana de arriba (w = t) o de abajo (w = 0) de la pieza. `punto` (el clic) desempata."""
    if BRepAdaptor_Surface(cara).GetType() != GeomAbs_Plane:
        raise geo.ErrorGeometria("Elegí una cara plana de la chapa (la de arriba o la de abajo).")
    t = modelo["regla"]["espesor"]
    x = np.asarray(punto, float) if punto is not None else _punto_en_cara(cara)
    f = _m(modelo)
    for pid, mat in transformaciones(modelo).items():
        local = _aplicar(np.linalg.inv(f @ mat), x)
        for w in (0.0, t):
            if abs(local[2] - w) < 1e-4 and _dentro(region_a_caras(modelo["placas"][pid]), local[:2]):
                return pid, w
    raise geo.ErrorGeometria("La cara elegida no es la cara de arriba ni la de abajo de una parte plana de la chapa.")


def pliegue_de_cara(modelo, cara):
    """Pliegue (plegado) al que pertenece una cara cilíndrica de la pieza."""
    s = BRepAdaptor_Surface(cara)
    if s.GetType() != GeomAbs_Cylinder:
        raise geo.ErrorGeometria("Elegí la cara curva de un pliegue.")
    cil = s.Cylinder()
    loc, dr = cil.Axis().Location(), cil.Axis().Direction()
    c0, d0 = np.array([loc.X(), loc.Y(), loc.Z()]), np.array([dr.X(), dr.Y(), dr.Z()])
    t = modelo["regla"]["espesor"]
    f = _m(modelo)
    mats = transformaciones(modelo)
    for bid, b in modelo["pliegues"].items():
        if not _plegado(b):
            continue
        w = f @ mats[b["padre"]]
        p_eje = _aplicar(w, [*b["o"], t + b["radio"] if b["sentido"] > 0 else -b["radio"]])
        a = w[:3, :3] @ np.array([*_eje(b), 0.0])
        if np.linalg.norm(np.cross(a, d0)) > 1e-6 or np.linalg.norm(np.cross(c0 - p_eje, a)) > 1e-4:
            continue
        if min(abs(cil.Radius() - b["radio"]), abs(cil.Radius() - b["radio"] - t)) < 1e-5:
            return bid
    raise geo.ErrorGeometria("La cara elegida no es un pliegue de esta chapa.")


# ---------------------------------------------------------------- pestañas (de arista y dobladillo)
POSICIONES = {"interior": "Interior", "exterior": "Exterior", "adyacente": "Adyacente", "tangente": "Tangente"}
REFERENCIAS_ALTURA = {"exterior": "Caras exteriores", "interior": "Caras interiores", "tangente": "Tangente al pliegue"}
TIPOS_ANCHO = {"completo": "Arista completa", "simetrico": "Simétrico", "dos_lados": "Dos lados"}


def recorte_y_largo(altura, angulo, radio, espesor, posicion="interior", referencia="exterior"):
    """(cuánto se recorta la cara de la que sale la pestaña, largo plano de la pestaña). La altura se mide desde
    la referencia de Fusion: exterior = intersección de las caras exteriores (línea de molde), interior = de las
    caras interiores, tangente = plano tangente al pliegue paralelo a la pestaña. Posición del pliegue: interior
    (la cara exterior de la pestaña queda en la arista), exterior (la interior queda en la arista), adyacente
    (el pliegue empieza en la arista) o tangente (la curva exterior toca la arista)."""
    if not 0 < angulo < 180:
        raise geo.ErrorGeometria("El ángulo de la pestaña va entre 0° y 180° (sin incluirlos).")
    th = math.radians(angulo)
    tg = math.tan(th / 2)
    tang = (radio + espesor) * (math.sin(th) if angulo <= 90 else 1.0)
    recortes = {"interior": (radio + espesor) * tg, "exterior": radio * tg, "adyacente": 0.0, "tangente": tang}
    retiros = {"exterior": (radio + espesor) * tg, "interior": radio * tg, "tangente": tang}
    if posicion not in recortes:
        raise geo.ErrorGeometria(f"Posición de pliegue desconocida: {posicion}")
    if referencia not in retiros:
        raise geo.ErrorGeometria(f"Referencia de altura desconocida: {referencia}")
    largo = altura - retiros[referencia]
    if largo <= TOL:
        raise geo.ErrorGeometria(f"La altura tiene que ser mayor que lo que ocupa el pliegue "
                                 f"({retiros[referencia]:.3g} mm).")
    return recortes[posicion], largo


def _intervalo_ancho(libres, ancho, distancia, distancia1, distancia2):
    s0, s1 = max(libres, key=lambda x: x[1] - x[0])
    if ancho == "completo":
        return s0, s1
    medio = (s0 + s1) / 2
    if ancho == "simetrico":
        a, b = medio - distancia / 2, medio + distancia / 2
    elif ancho == "dos_lados":
        a, b = medio - distancia1, medio + distancia2
    else:
        raise geo.ErrorGeometria(f"Tipo de ancho desconocido: {ancho}")
    if b - a <= TOL:
        raise geo.ErrorGeometria("El ancho de la pestaña tiene que ser positivo.")
    if a < s0 - TOL or b > s1 + TOL:
        raise geo.ErrorGeometria("La pestaña es más ancha que la arista elegida.")
    return a, b


def _alivio(o, a, n, extremo, lado, recorte, alivio):
    """Corte de alivio de plegado al costado de una pestaña más angosta que su arista: ancho `alivio["ancho"]`
    afuera de la pestaña y `alivio["profundidad"]` más allá del inicio del pliegue."""
    forma, w, prof = alivio["forma"], alivio["ancho"], alivio["profundidad"]
    if forma == "desgarro":
        w = _ANCHO_DESGARRO
    e0, e1 = (extremo - w, extremo) if lado < 0 else (extremo, extremo + w)
    if forma == "desgarro":
        return [_rect(o, a, n, e0, e1, 0.0, recorte + _MARGEN)] if recorte > TOL else []
    if forma == "recto":
        return [_rect(o, a, n, e0, e1, -prof, recorte + _MARGEN)]
    fondo = -prof + w / 2
    caras = [_rect(o, a, n, e0, e1, min(fondo, recorte), recorte + _MARGEN)]
    return caras + [_disco(np.asarray(o) + (e0 + e1) / 2 * a + fondo * n, w / 2)]


def _alivios_esquina(modelo, bid):
    """Donde el pliegue nuevo se cruza con otro se recorta la zona común de los dos («recortar al pliegue») y,
    según la regla, además un círculo o un cuadrado de `esquina_tam` centrado en la esquina."""
    r_ch = modelo["regla"]
    if r_ch["esquina_forma"] == "desgarro":
        return
    nuevo = modelo["pliegues"][bid]
    on, nn, an = np.array(nuevo["o"]), np.array(nuevo["n"]), _eje(nuevo)
    rects_nuevo = [_rect(on, an, nn, e0, e1, 0.0, nuevo["ba"]) for e0, e1 in nuevo["tramos"]]
    for kid, k in list(modelo["pliegues"].items()):
        ok_, nk = np.array(k["o"]), np.array(k["n"])
        if kid == bid or abs(nn[0] * nk[1] - nn[1] * nk[0]) < 1e-9:
            continue
        mat = np.array([nn, nk])
        verts = [np.linalg.solve(mat, [xi + on @ nn, xk + ok_ @ nk]) for xi in (0.0, nuevo["ba"])
                 for xk in (0.0, k["ba"])]
        zona = _poligono([verts[0], verts[1], verts[3], verts[2]])
        if min(_distancia(zona, r) for r in rects_nuevo) > TOL:
            continue
        tocada = False
        for pl in (nuevo, k):
            o, n, a = np.array(pl["o"]), np.array(pl["n"]), _eje(pl)
            proy = [float((v - o) @ a) for v in verts]
            for e0, e1 in list(pl["tramos"]):
                if _area(_op2d([zona], [_rect(o, a, n, e0, e1, 0.0, pl["ba"])], "intersecar")) > 1e-6:
                    pl["tramos"] = _restar_intervalos(pl["tramos"], [[min(proy), max(proy)]])
                    tocada = True
        if tocada and r_ch["esquina_forma"] in ("redondo", "cuadrado"):
            centro, tam = np.mean(verts, axis=0), r_ch["esquina_tam"]
            corte = _disco(centro, tam / 2) if r_ch["esquina_forma"] == "redondo" else \
                _rect(centro - (an + nn) * tam / 2, an, nn, 0.0, tam, 0.0, tam)
            _cortar_todo(modelo, corte)


def _cortar_todo(modelo, corte):
    """Quita una figura de todas las placas y, redondeada a tramos enteros, de las franjas de los pliegues
    (así la pieza plegada y el patrón plano siguen coincidiendo)."""
    for pid, region in modelo["placas"].items():
        caras = region_a_caras(region)
        if caras and _area(_op2d(caras, [corte], "intersecar")) > 1e-9:
            modelo["placas"][pid] = caras_a_region(_op2d(caras, [corte], "cortar"))
    for b in modelo["pliegues"].values():
        o, n, a = np.array(b["o"]), np.array(b["n"]), _eje(b)
        for e0, e1 in list(b["tramos"]):
            comun = _op2d([_rect(o, a, n, e0, e1, 0.0, b["ba"])], [corte], "intersecar")
            if _area(comun) > 1e-9:
                xs = [float((np.array(p) - o) @ a) for c in comun for p in _puntos_2d(c)]
                b["tramos"] = _restar_intervalos(b["tramos"], [[min(xs), max(xs)]])


def _agregar_pestana(modelo, pid, p, d, s0, s1, n, sentido, angulo, radio, largo, recorte, alivio):
    """Agrega un pliegue y su placa hija sobre el borde p + s·d (s ∈ [s0, s1]) de la placa `pid`, con normal
    exterior `n`. El borde se recorta `recorte` mm hacia adentro (posición del pliegue). Devuelve el id."""
    t, k = modelo["regla"]["espesor"], modelo["regla"]["k"]
    ba = longitud_pliegue(angulo, radio, t, k)
    a = np.array([n[1], -n[0]])
    o = np.asarray(p, float) - recorte * n
    sg = float(np.sign(d @ a))
    e0, e1 = sorted([s0 * sg, s1 * sg])
    caras = region_a_caras(modelo["placas"][pid])
    cortes = [_rect(o, a, n, e0, e1, 0.0, recorte + _MARGEN)] if recorte > TOL else []
    for extremo, lado in ((e0, -1), (e1, 1)):
        prueba = o + (extremo + lado * 10 * _DELTA) * a + (recorte - 10 * _DELTA) * n
        if _dentro(caras, prueba):
            cortes += _alivio(o, a, n, extremo, lado, recorte, alivio)
    if cortes:
        caras = _op2d(caras, cortes, "cortar")
    if not _dentro(caras, o + (e0 + e1) / 2 * a - _DELTA * n):
        raise geo.ErrorGeometria("La posición del pliegue se come la cara de la que sale la pestaña.")
    modelo["placas"][pid] = caras_a_region(caras)
    hija = _nuevo_id(modelo, "p")
    modelo["placas"][hija] = caras_a_region([_rect(o, a, n, e0, e1, ba, ba + largo)]) if largo > TOL else []
    bid = _nuevo_id(modelo, "b")
    modelo["pliegues"][bid] = _datos_pliegue(pid, hija, o, n, ba, [[e0, e1]], radio, angulo, sentido)
    _alivios_esquina(modelo, bid)
    return bid


def _alivio_de(modelo, alivio):
    r = modelo["regla"]
    a = {"forma": r["alivio_forma"], "ancho": r["alivio_ancho"], "profundidad": r["alivio_profundidad"]}
    a.update({k: v for k, v in (alivio or {}).items() if v is not None})
    if a["forma"] not in FORMAS_ALIVIO:
        raise geo.ErrorGeometria(f"Forma de alivio desconocida: {a['forma']}")
    return a


def _bordes(modelo, aristas):
    """Ubica todas las aristas ANTES de modificar la pieza: (placa, p, dirección, w)."""
    salida = []
    for e in aristas:
        pid, p, q, w, _libres = ubicar_arista(modelo, e)
        salida.append((pid, p, (q - p) / np.linalg.norm(q - p), q, w))
    return salida


def _libres_actuales(modelo, pid, p, q):
    # El borde pudo cambiar por una pestaña anterior de la misma operación: se vuelve a medir.
    libres = _intervalos_libres(modelo, pid, p, q)
    if not libres:
        raise geo.ErrorGeometria("Otra pestaña de esta misma operación ya ocupa esa arista.")
    return libres


def pestana_arista(modelo, aristas, altura, angulo=90.0, posicion="interior", referencia="exterior",
                   ancho="completo", distancia=0.0, distancia1=0.0, distancia2=0.0, invertir=False, radio=None,
                   alivio=None):
    """Pestaña de arista [SM-REF-BASE-EDGE-CONTOUR-FLANGE › Edge Flange] sobre aristas rectas del borde de la
    pieza: altura medida según `referencia`, `posicion` del pliegue, ancho completo, simétrico (`distancia`) o a
    dos lados (`distancia1`, `distancia2`) desde el medio de la arista. Va hacia el lado de la cara de la arista
    elegida (invertir la da vuelta). `radio` y `alivio` anulan la regla. Devuelve el modelo nuevo."""
    m = copy.deepcopy(modelo)
    t = m["regla"]["espesor"]
    r = m["regla"]["radio"] if radio is None else float(radio)
    if r < 0:
        raise geo.ErrorGeometria("El radio de plegado no puede ser negativo.")
    recorte, largo = recorte_y_largo(altura, angulo, r, t, posicion, referencia)
    alv = _alivio_de(m, alivio)
    for pid, p, d, q, w in _bordes(m, aristas):
        s0, s1 = _intervalo_ancho(_libres_actuales(m, pid, p, q), ancho, distancia, distancia1, distancia2)
        n = _normal_exterior(region_a_caras(m["placas"][pid]), p, d, (s0 + s1) / 2)
        sentido = (1 if w > t / 2 else -1) * (-1 if invertir else 1)
        _agregar_pestana(m, pid, p, d, s0, s1, n, sentido, angulo, r, largo, recorte, alv)
    return m


TIPOS_DOBLADILLO = {"cerrado": "Plano (cerrado)", "abierto": "Abierto", "lagrima": "Lágrima"}


def dobladillo(modelo, aristas, tipo="cerrado", longitud=10.0, separacion=None, radio=None, posicion="adyacente",
               invertir=False):
    """Dobladillo [SM-REF-HEM-FLANGE]: dobla el borde 180° sobre sí mismo. Cerrado (apoyado, radio 0),
    abierto (`separacion` entre capas) o en lágrima simplificada (radio `radio` y más de 180° hasta dejar
    `separacion` en la punta). `longitud`: del extremo doblado a la punta. Posición adyacente (empieza en la
    arista) o tangente (la curva no pasa de la arista)."""
    m = copy.deepcopy(modelo)
    t = m["regla"]["espesor"]
    sep = m["regla"]["separacion"] if separacion is None else float(separacion)
    if tipo == "cerrado":
        r = 0.0
    elif tipo == "abierto":
        if sep <= 0:
            raise geo.ErrorGeometria("La separación del dobladillo abierto tiene que ser positiva.")
        r = sep / 2
    elif tipo == "lagrima":
        r = m["regla"]["radio"] if radio is None else float(radio)
        if r <= 0:
            raise geo.ErrorGeometria("El radio de la lágrima tiene que ser positivo.")
    else:
        raise geo.ErrorGeometria(f"Tipo de dobladillo desconocido: {tipo}")
    if posicion not in ("adyacente", "tangente"):
        raise geo.ErrorGeometria("La posición del dobladillo es adyacente o tangente.")
    largo = longitud - (r + t)
    if largo <= TOL:
        raise geo.ErrorGeometria(f"La longitud del dobladillo tiene que ser mayor que {r + t:.3g} mm.")
    extra = 0.0
    if tipo == "lagrima" and sep < 2 * r:
        # Pasa de 180° hasta que la punta queda a `sep` de la cara: r·cos β − L·sen β = sep − r.
        extra = math.degrees(math.acos((sep - r) / math.hypot(r, largo)) - math.atan2(largo, r))
    recorte = r + t if posicion == "tangente" else 0.0
    alv = _alivio_de(m, None)
    for pid, p, d, q, w in _bordes(m, aristas):
        s0, s1 = max(_libres_actuales(m, pid, p, q), key=lambda x: x[1] - x[0])
        n = _normal_exterior(region_a_caras(m["placas"][pid]), p, d, (s0 + s1) / 2)
        sentido = (1 if w > t / 2 else -1) * (-1 if invertir else 1)
        _agregar_pestana(m, pid, p, d, s0, s1, n, sentido, 180.0 + extra, r, largo, recorte, alv)
    return m


# ---------------------------------------------------------------- creación: base, contorno, convertir
ORIENTACIONES = {"lado1": "Lado 1", "lado2": "Lado 2", "centro": "Centro"}


def _a_plano(cara, mat):
    """Cara 3D → caras en z = 0 de las coordenadas planas (la cara tiene que ser paralela al plano)."""
    local = geo.transformar(cara, np.linalg.inv(mat))
    caja = geo.caja_envolvente(local)
    if caja is None or caja[1][2] - caja[0][2] > 1e-5:
        raise geo.ErrorGeometria("El perfil no es plano.")
    return [_hacia_arriba(c) for c in geo.caras(geo.trasladar(local, (0, 0, -caja[0][2])))]


def pestana_base(caras, plano, regla_chapa, orientacion="lado1"):
    """Pestaña base [Base Flange]: perfiles cerrados de un boceto → placas planas del espesor de la regla
    (lado 1 = hacia la normal del boceto, lado 2 = al revés, centro = mitad y mitad). Devuelve un modelo por
    región separada (en Fusion, perfiles que no se tocan crean cuerpos distintos)."""
    t = regla_chapa["espesor"]
    corr = {"lado1": 0.0, "lado2": -t, "centro": -t / 2}
    if orientacion not in corr:
        raise geo.ErrorGeometria(f"Orientación desconocida: {orientacion}")
    if not caras:
        raise geo.ErrorGeometria("Elegí uno o más perfiles cerrados.")
    mat = np.array(marco(plano.origen + plano.normal * corr[orientacion], plano.u, plano.v, plano.normal))
    planas = []
    for c in caras:
        planas = _op2d(planas, _a_plano(c, mat), "unir")
    return [modelo_nuevo(regla_chapa, mat, caras_a_region([c])) for c in planas]


def _segmentos_perfil(aristas, plano):
    """Aristas de boceto → segmentos 2D orientados en UNA cadena abierta: dicts con p0, p1 y, en los arcos,
    centro c, radio r, barrido y sentido ccw. Arranca por el extremo libre de menor (u, v)."""
    segs = []
    for e in aristas:
        c = BRepAdaptor_Curve(e)
        t0, t1 = c.FirstParameter(), c.LastParameter()
        p0, p1 = (np.array(plano.a_uv([c.Value(x).X(), c.Value(x).Y(), c.Value(x).Z()])) for x in (t0, t1))
        if c.GetType() == GeomAbs_Line:
            segs.append({"tipo": "l", "p0": p0, "p1": p1})
        elif c.GetType() == GeomAbs_Circle:
            ci = c.Circle()
            ce, d = ci.Location(), ci.Axis().Direction()
            segs.append({"tipo": "a", "p0": p0, "p1": p1, "c": np.array(plano.a_uv([ce.X(), ce.Y(), ce.Z()])),
                         "r": ci.Radius(), "barrido": abs(t1 - t0),
                         "ccw": float(np.dot([d.X(), d.Y(), d.Z()], plano.normal)) > 0})
        else:
            raise geo.ErrorGeometria("El perfil del contorno solo puede tener líneas y arcos.")
    if not segs:
        raise geo.ErrorGeometria("Elegí las curvas del perfil abierto.")
    extremos = [s["p0"] for s in segs] + [s["p1"] for s in segs]
    grados = [sum(1 for q in extremos if np.linalg.norm(q - p) < 1e-6) for p in extremos]
    if max(grados) > 2:
        raise geo.ErrorGeometria("El perfil del contorno se bifurca: elegí una sola cadena de curvas.")
    libres = [p for p, g in zip(extremos, grados, strict=True) if g == 1]
    if len(libres) != 2:
        raise geo.ErrorGeometria("El perfil del contorno tiene que ser una cadena ABIERTA (para perfiles cerrados "
                                 "usá la pestaña base).")
    actual = min(libres, key=lambda p: (round(p[0], 6), round(p[1], 6)))
    restantes, cadena = list(segs), []
    while restantes:
        s = next((s for s in restantes if min(np.linalg.norm(s["p0"] - actual), np.linalg.norm(s["p1"] - actual))
                  < 1e-6), None)
        if s is None:
            raise geo.ErrorGeometria("Las curvas del perfil no están conectadas.")
        restantes.remove(s)
        if np.linalg.norm(s["p0"] - actual) > 1e-6:
            s = dict(s, p0=s["p1"], p1=s["p0"], ccw=not s.get("ccw", True))
        cadena.append(s)
        actual = s["p1"]
    return cadena


def _tangentes(s):
    """(tangente al entrar, tangente al salir) de un segmento orientado."""
    if s["tipo"] == "l":
        d = (s["p1"] - s["p0"]) / np.linalg.norm(s["p1"] - s["p0"])
        return d, d
    sg = 1.0 if s["ccw"] else -1.0
    r0, r1 = (s["p0"] - s["c"]) / s["r"], (s["p1"] - s["c"]) / s["r"]
    return sg * np.array([-r0[1], r0[0]]), sg * np.array([-r1[1], r1[0]])


def pestana_contorno(aristas, plano, regla_chapa, distancia, orientacion="lado1", direccion="un_lado",
                     distancia2=0.0):
    """Pestaña de contorno [Contour Flange]: perfil ABIERTO de líneas y arcos tangentes → chapa plegada, con el
    radio de la regla en cada esquina viva y el radio de cada arco. Lado 1 = el material a la izquierda del
    perfil (recorrido desde su extremo de menor u, v), lado 2 = a la derecha, centro = mitad y mitad. Extrusión
    de `distancia` a un lado (hacia la normal del boceto), a dos lados (`distancia2` del otro) o simétrica."""
    t, rr, k = regla_chapa["espesor"], regla_chapa["radio"], regla_chapa["k"]
    lam = {"lado1": 0.0, "lado2": -t, "centro": -t / 2}
    if orientacion not in lam:
        raise geo.ErrorGeometria(f"Orientación desconocida: {orientacion}")
    l0 = lam[orientacion]
    x0, x1 = {"un_lado": (0.0, distancia), "simetrica": (-distancia / 2, distancia / 2),
              "dos_lados": (-distancia2, distancia)}.get(direccion, (0.0, 0.0))
    if distancia <= 0 or x1 - x0 <= TOL:
        raise geo.ErrorGeometria("Dirección o distancias de la pestaña de contorno inválidas.")
    cadena = _segmentos_perfil(aristas, plano)
    # Secuencia alternada placa / pliegue: los tramos rectos pierden el retiro de cada esquina viva.
    seq = []

    def placa(largo):
        if seq and "placa" in seq[-1]:
            seq[-1]["placa"] += largo
        else:
            seq.append({"placa": largo})

    def pliegue(angulo, sentido, radio):
        if not seq or "placa" not in seq[-1]:
            seq.append({"placa": 0.0})
        seq.append({"angulo": angulo, "sentido": sentido, "radio": radio})
    for i, s in enumerate(cadena):
        if s["tipo"] == "l":
            placa(float(np.linalg.norm(s["p1"] - s["p0"])))
        else:
            sentido = 1 if s["ccw"] else -1
            ri = s["r"] - (l0 + t) if sentido > 0 else s["r"] + l0
            if ri < -1e-9:
                raise geo.ErrorGeometria(f"El radio del arco ({s['r']:.3g} mm) es menor que el espesor del lado "
                                         "interior del pliegue.")
            pliegue(math.degrees(s["barrido"]), sentido, max(ri, 0.0))
        if i + 1 == len(cadena):
            break
        d_sal, d_ent = _tangentes(s)[1], _tangentes(cadena[i + 1])[0]
        giro = math.atan2(d_sal[0] * d_ent[1] - d_sal[1] * d_ent[0], float(d_sal @ d_ent))
        if abs(giro) < 1e-7:
            continue
        if s["tipo"] != "l" or cadena[i + 1]["tipo"] != "l":
            raise geo.ErrorGeometria("Los arcos del perfil tienen que ser tangentes a los tramos vecinos.")
        if abs(abs(giro) - math.pi) < 1e-7:
            raise geo.ErrorGeometria("El perfil vuelve sobre sí mismo (giro de 180°).")
        sentido = 1 if giro > 0 else -1
        retiro = ((l0 + t + rr) if sentido > 0 else (rr - l0)) * math.tan(abs(giro) / 2)
        placa(-retiro)
        pliegue(math.degrees(abs(giro)), sentido, rr)
        placa(-retiro)
    if "placa" not in seq[-1]:
        seq.append({"placa": 0.0})
    if any("placa" in e and e["placa"] < -1e-7 for e in seq):
        raise geo.ErrorGeometria("Un tramo del perfil es demasiado corto para el radio de plegado.")
    d0 = plano.dir_3d(*_tangentes(cadena[0])[0])
    izq = np.cross(plano.normal, d0)
    m = modelo_nuevo(regla_chapa, marco(plano.a_3d(*cadena[0]["p0"]) + l0 * izq, plano.normal, d0, izq), [])
    m["placas"] = {}
    y, actual = 0.0, None
    for e in seq:
        if "placa" in e:
            pid = "p0" if actual is None else _nuevo_id(m, "p")
            largo = max(e["placa"], 0.0)
            m["placas"][pid] = caras_a_region([_rect((0, y), (1, 0), (0, 1), x0, x1, 0.0, largo)]) \
                if largo > TOL else []
            if actual is not None:
                m["pliegues"][actual]["hija"] = pid
            y += largo
            actual = pid
        else:
            ba = longitud_pliegue(e["angulo"], e["radio"], t, k)
            bid = _nuevo_id(m, "b")
            m["pliegues"][bid] = _datos_pliegue(actual, None, (0.0, y), (0.0, 1.0), ba, [[x0, x1]], e["radio"],
                                                e["angulo"], e["sentido"])
            y += ba
            actual = bid
    return m


def convertir(forma, cara, nombre_regla=REGLA_DEFECTO, **ajustes):
    """Convertir a chapa [SM-TO-CONVERT-TO-SM] para placas PLANAS de espesor constante: el cuerpo tiene que ser
    el prisma de la cara elegida. Como en Fusion, el espesor detectado reemplaza al de la regla elegida."""
    plano = geo.plano_de_cara(cara)
    if plano is None:
        raise geo.ErrorGeometria("Elegí una cara plana ancha del cuerpo.")
    alturas = []
    ex = TopExp_Explorer(forma, TopAbs_VERTEX)
    while ex.More():
        p = BRep_Tool.Pnt_s(TopoDS.Vertex(ex.Current()))
        alturas.append(float((np.array([p.X(), p.Y(), p.Z()]) - plano.origen) @ plano.normal))
        ex.Next()
    t = -min(alturas)
    if max(alturas) > 1e-5 or t <= 1e-6:
        raise geo.ErrorGeometria("La cara elegida no es una tapa del cuerpo.")
    vol = geo.volumen(forma)
    if abs(vol - geo.area(cara) * t) > max(1e-6, 1e-6 * vol):
        raise geo.ErrorGeometria(f"El cuerpo no es una placa plana de espesor constante: por ahora solo se convierten "
                                 f"placas planas (sin pliegues ni caras inclinadas). Espesor medido: {t:.4g} mm.")
    mat = np.array(marco(plano.origen - t * plano.normal, plano.u, plano.v, plano.normal))
    r = regla(nombre_regla, **{**ajustes, "espesor": t})
    return modelo_nuevo(r, mat, caras_a_region(_a_plano(cara, mat)))


def detectar_espesor(forma, cara):
    """Espesor de una placa plana medido desde la cara elegida (para mostrarlo en el diálogo)."""
    return convertir(forma, cara)["regla"]["espesor"]


# ---------------------------------------------------------------- desplegar, replegar, plegar
def _fijar(modelo, pid, mats_antes):
    """Ajusta el marco para que la placa `pid` quede donde estaba (la "cara estacionaria" de Fusion)."""
    mats = transformaciones(modelo)
    modelo["marco"] = (_m(modelo) @ mats_antes[pid] @ np.linalg.inv(mats[pid])).tolist()
    modelo["estacionaria"] = pid


def desplegar(modelo, cara=None, punto=None, pliegues=None):
    """Desplegar [GUID-5125C823]: endereza los pliegues elegidos (todos si `pliegues` es None) dejando fija la
    placa de la cara estacionaria (sin cara: la de la última vez o la raíz)."""
    m = copy.deepcopy(modelo)
    fija = placa_de_cara(m, cara, punto)[0] if cara is not None else m.get("estacionaria", m["raiz"])
    antes = transformaciones(m)
    elegidos = list(m["pliegues"]) if pliegues is None else list(pliegues)
    if not elegidos:
        raise geo.ErrorGeometria("La chapa no tiene pliegues para desplegar.")
    for bid in elegidos:
        if bid not in m["pliegues"]:
            raise geo.ErrorGeometria("Uno de los pliegues elegidos ya no existe.")
        m["pliegues"][bid]["desplegado"] = True
    _fijar(m, fija, antes)
    return m


def replegar(modelo, cara=None, punto=None):
    """Volver a plegar [Refold]: pliega otra vez todos los pliegues desplegados; queda fija la placa estacionaria."""
    m = copy.deepcopy(modelo)
    if not any(b["desplegado"] for b in m["pliegues"].values()):
        raise geo.ErrorGeometria("La chapa no tiene pliegues desplegados.")
    fija = placa_de_cara(m, cara, punto)[0] if cara is not None else m.get("estacionaria", m["raiz"])
    antes = transformaciones(m)
    for b in m["pliegues"].values():
        b["desplegado"] = False
    _fijar(m, fija, antes)
    return m


POSICIONES_LINEA = {"inicio": "Inicio", "centro": "Centro", "fin": "Fin"}


def plegar(modelo, cara, lineas, angulo=90.0, posicion="centro", invertir=False, radio=None, punto=None):
    """Plegar [GUID-D11BA900] (Fold): pliega la pieza por líneas rectas (pares de puntos 3D) que cruzan de lado a
    lado una cara plana. Queda fijo el lado del clic sobre la cara estacionaria (`punto`); el otro gira `angulo`
    hacia el lado de esa cara (invertir o ángulo negativo: hacia el otro). Posición de la línea respecto del
    pliegue: inicio, centro o fin."""
    m = copy.deepcopy(modelo)
    if not lineas:
        raise geo.ErrorGeometria("Elegí al menos una línea de plegado.")
    if not 0 < abs(angulo) < 180:
        raise geo.ErrorGeometria("El ángulo de plegado va entre −180° y 180° y no puede ser 0°.")
    if posicion not in POSICIONES_LINEA:
        raise geo.ErrorGeometria(f"Posición de la línea desconocida: {posicion}")
    t, k = m["regla"]["espesor"], m["regla"]["k"]
    r = m["regla"]["radio"] if radio is None else float(radio)
    pid0, w = placa_de_cara(m, cara, punto)
    sentido = (1 if w > t / 2 else -1) * (-1 if invertir else 1) * (1 if angulo > 0 else -1)
    ba = longitud_pliegue(abs(angulo), r, t, k)
    inv = np.linalg.inv(_m(m) @ transformaciones(m)[pid0])
    fijo = _aplicar(inv, punto if punto is not None else _punto_en_cara(cara))[:2]
    for p3, q3 in lineas:                 # todas en las coordenadas planas de la cara elegida
        p, q = _aplicar(inv, p3)[:2], _aplicar(inv, q3)[:2]
        _plegar_linea(m, p, q, fijo, ba, posicion, r, abs(angulo), sentido)
    return m


def _plegar_linea(m, p, q, fijo, ba, posicion, radio, angulo, sentido):
    antes = transformaciones(m)
    d = (q - p) / np.linalg.norm(q - p)
    izq = np.array([-d[1], d[0]])
    n = -izq if (fijo - p) @ izq > 0 else izq             # del lado fijo hacia el lado que gira
    a = np.array([n[1], -n[0]])
    o = p + {"inicio": 0.0, "centro": -ba / 2, "fin": -ba}[posicion] * n
    banda = _rect(o, a, n, -1e5, 1e5, 0.0, ba)
    medio = (p + q) / 2
    placa = next((pid for pid, reg in m["placas"].items() if reg and _estado(region_a_caras(reg), medio, 1e-6)),
                 None)
    if placa is None:
        raise geo.ErrorGeometria("La línea de plegado no está sobre una cara plana de la chapa.")
    caras = region_a_caras(m["placas"][placa])
    tramos = []
    for c in _op2d(caras, [banda], "intersecar"):
        xs = [float((np.array(v) - o) @ a) for v in _puntos_2d(c)]
        if abs(geo.area(c) - (max(xs) - min(xs)) * ba) > 1e-6 * max(1.0, geo.area(c)):
            raise geo.ErrorGeometria("En la zona del pliegue los bordes de la cara tienen que ser perpendiculares a "
                                     "la línea de plegado.")
        tramos.append([min(xs), max(xs)])
    resto = _op2d(caras, [banda], "cortar")
    lado_fijo = [c for c in resto if (np.array(geo.centro_masa(c, True)[:2]) - p) @ n < 0]
    lado_giro = [c for c in resto if (np.array(geo.centro_masa(c, True)[:2]) - p) @ n >= 0]
    if not tramos or not lado_fijo or not lado_giro:
        raise geo.ErrorGeometria("La línea de plegado tiene que cruzar la cara de lado a lado.")
    # La placa conserva el lado de su pliegue padre (o el fijo, si es la raíz); el otro es una placa nueva.
    padre = next((b for b in m["pliegues"].values() if b["hija"] == placa), None)
    conserva_fijo = True
    if padre is not None:
        ref = np.array(padre["o"]) + padre["ba"] * np.array(padre["n"]) + np.mean(padre["tramos"][0]) * _eje(padre)
        conserva_fijo = (ref - p) @ n < 0
    propio, otro = (lado_fijo, lado_giro) if conserva_fijo else (lado_giro, lado_fijo)
    nueva = _nuevo_id(m, "p")
    m["placas"][placa], m["placas"][nueva] = caras_a_region(propio), caras_a_region(otro)
    for b in m["pliegues"].values():
        if b["padre"] == placa:
            union = np.array(b["o"]) + np.mean(b["tramos"][0]) * _eje(b)
            if ((union - p) @ n >= 0) == conserva_fijo:
                b["padre"] = nueva
    nb, ob = (n, o) if conserva_fijo else (-n, o + ba * n)
    an = np.array([nb[1], -nb[0]])
    tr = sorted(sorted([e0 * float(a @ an), e1 * float(a @ an)]) for e0, e1 in tramos)
    m["pliegues"][_nuevo_id(m, "b")] = _datos_pliegue(placa, nueva, ob, nb, ba, tr, radio, angulo, sentido)
    _fijar(m, placa if conserva_fijo else nueva, {**antes, nueva: antes[placa]})


# ---------------------------------------------------------------- desgarro y división en cuerpos
def _separar(modelo, posiciones):
    """Modelos resultantes cuando se quitaron pliegues o placas: cada placa sin padre es raíz de una pieza, en la
    posición que tenía (`posiciones`: placa → matriz respecto de la raíz original)."""
    hijos = _hijos(modelo)
    tiene_padre = {b["hija"] for b in modelo["pliegues"].values()}
    raices = list(dict.fromkeys(p for p in [modelo["raiz"], *modelo["placas"]] if p in modelo["placas"] and
                                p not in tiene_padre))
    salida = []
    for raiz in raices:
        placas, pliegues, cola = [raiz], [], [raiz]
        while cola:
            for bid in hijos.get(cola.pop(), []):
                pliegues.append(bid)
                placas.append(modelo["pliegues"][bid]["hija"])
                cola.append(modelo["pliegues"][bid]["hija"])
        if not any(modelo["placas"][p] for p in placas) and not pliegues:
            continue
        sub = {k: copy.deepcopy(v) for k, v in modelo.items() if k not in ("placas", "pliegues")}
        sub["placas"] = {p: copy.deepcopy(modelo["placas"][p]) for p in placas}
        sub["pliegues"] = {b: copy.deepcopy(modelo["pliegues"][b]) for b in pliegues}
        sub["raiz"] = sub["estacionaria"] = raiz
        sub["marco"] = (_m(modelo) @ np.asarray(posiciones.get(raiz, np.eye(4)))).tolist()
        salida.append(sub)
    if not salida:
        raise geo.ErrorGeometria("No queda chapa después del desgarro.")
    return salida


def _en_borde(caras, p):
    return _estado(caras, p, 1e-5) == TopAbs_ON


def desgarrar(modelo, modo, cara=None, puntos=None, lado="centro", separacion=None):
    """Desgarro [SM-RIP]. modo "cara": quita la cara elegida (un pliegue o una parte plana); modo "puntos": corta
    una ranura de ancho `separacion` (lado 1 = a la izquierda de p1→p2, lado 2 o centrada) entre dos puntos del
    borde de una misma cara. Si la pieza queda partida devuelve un modelo por pedazo (cada uno, un cuerpo)."""
    m = copy.deepcopy(modelo)
    mats = transformaciones(m)
    posiciones = {}
    if modo == "cara":
        if cara is None:
            raise geo.ErrorGeometria("Elegí la cara a quitar.")
        if BRepAdaptor_Surface(cara).GetType() == GeomAbs_Cylinder:
            b = m["pliegues"].pop(pliegue_de_cara(m, cara))
            posiciones[b["hija"]] = mats[b["hija"]]
        else:
            pid, _w = placa_de_cara(m, cara)
            for bid, b in list(m["pliegues"].items()):
                if pid in (b["padre"], b["hija"]):
                    m["pliegues"].pop(bid)
                    posiciones[b["hija"]] = mats[b["hija"]]
            m["placas"].pop(pid)
    elif modo == "puntos":
        if not puntos or len(puntos) != 2:
            raise geo.ErrorGeometria("Elegí dos puntos del borde de una misma cara.")
        sep = m["regla"]["separacion"] if separacion is None else float(separacion)
        if sep <= 0:
            raise geo.ErrorGeometria("La separación del desgarro tiene que ser positiva.")
        if lado not in ORIENTACIONES:
            raise geo.ErrorGeometria(f"Lado desconocido: {lado}")
        t = m["regla"]["espesor"]
        destino = None
        for pid, mat in mats.items():
            inv = np.linalg.inv(_m(m) @ mat)
            p, q = (_aplicar(inv, x) for x in puntos)
            if not m["placas"][pid] or abs(p[2] - q[2]) > TOL or min(abs(p[2]), abs(p[2] - t)) > TOL:
                continue
            caras = region_a_caras(m["placas"][pid])
            if _en_borde(caras, p[:2]) and _en_borde(caras, q[:2]):
                destino = (pid, p[:2], q[:2], caras)
                break
        if destino is None:
            raise geo.ErrorGeometria("Los dos puntos tienen que estar en el borde de una misma cara plana.")
        pid, p, q, caras = destino
        largo = float(np.linalg.norm(q - p))
        if largo < TOL:
            raise geo.ErrorGeometria("Los dos puntos coinciden.")
        d = (q - p) / largo
        y0, y1 = {"lado1": (0.0, sep), "lado2": (-sep, 0.0), "centro": (-sep / 2, sep / 2)}[lado]
        ranura = _rect(p, d, np.array([-d[1], d[0]]), -sep, largo + sep, y0, y1)
        _repartir(m, pid, _op2d(caras, [ranura], "cortar"), ranura, mats, posiciones)
    else:
        raise geo.ErrorGeometria(f"Modo de desgarro desconocido: {modo}")
    return _separar(m, posiciones)


def _repartir(m, pid, piezas, corte, mats, posiciones):
    """La placa `pid` quedó en varias piezas: la del pliegue padre conserva el id; las demás son placas nuevas
    (raíces de piezas propias) que se llevan los pliegues hijos que les tocan."""
    if not piezas:
        raise geo.ErrorGeometria("El desgarro se come toda la cara.")

    def pieza_de(b, es_padre):
        o, n, a = np.array(b["o"]), np.array(b["n"]), _eje(b)
        base = o + b["ba"] * n if es_padre else o
        p0, p1 = base + b["tramos"][0][0] * a, base + b["tramos"][-1][1] * a
        linea = BRepBuilderAPI_MakeEdge(_pnt(*p0), _pnt(*p1)).Edge()
        if _distancia(corte, linea) < 1e-7:
            raise geo.ErrorGeometria("El desgarro no puede cortar la unión de un pliegue con la cara.")
        cerca = [i for i, c in enumerate(piezas) if _distancia(c, _vertice((p0 + p1) / 2)) < 1e-5]
        if len(cerca) != 1:
            raise geo.ErrorGeometria("No se pudo saber a qué lado del desgarro queda un pliegue.")
        return cerca[0]

    padre = next((b for b in m["pliegues"].values() if b["hija"] == pid), None)
    propia = pieza_de(padre, True) if padre is not None else 0
    ids = {i: (pid if i == propia else _nuevo_id(m, "p")) for i in range(len(piezas))}
    for i, c in enumerate(piezas):
        m["placas"][ids[i]] = caras_a_region([c])
        if i != propia:
            posiciones[ids[i]] = mats[pid]
    for b in m["pliegues"].values():
        if b["padre"] == pid:
            b["padre"] = ids[pieza_de(b, False)]


# ---------------------------------------------------------------- unir plegando
def _reenraizar(modelo, nueva):
    """La placa `nueva` pasa a ser la raíz (se dan vuelta los pliegues del camino); la pieza no se mueve."""
    m = copy.deepcopy(modelo)
    if nueva == m["raiz"]:
        return m
    mats = transformaciones(m)
    padre_de = {b["hija"]: bid for bid, b in m["pliegues"].items()}
    p = nueva
    while p != m["raiz"]:
        b = m["pliegues"][padre_de[p]]
        o, n = np.array(b["o"]), np.array(b["n"])
        p = b["padre"]
        b["padre"], b["hija"] = b["hija"], b["padre"]
        b["o"], b["n"] = (o + b["ba"] * n).tolist(), (-n).tolist()
        b["tramos"] = sorted([-e1, -e0] for e0, e1 in b["tramos"])
    m["marco"] = (_m(m) @ mats[nueva]).tolist()
    m["raiz"] = m["estacionaria"] = nueva
    return m


def _mapear(modelo, e3, voltear, prefijo):
    """Lleva el modelo por la transformación plana `e3` (afín 2D, 3x3; reflejo si `voltear`: la cara de arriba
    pasa a ser la de abajo y cambia el sentido de los pliegues). Renombra placas y pliegues con `prefijo`."""
    lin = e3[:2, :2]
    mat = np.eye(4)
    mat[:2, :2], mat[:2, 3] = lin, e3[:2, 2]
    if voltear:
        mat[2, 2] = -1.0           # reflejo en el plano + z → −z: es un movimiento rígido válido

    def pt(x):
        return (e3 @ np.array([x[0], x[1], 1.0]))[:2]
    nombres = {p: f"{prefijo}{p}" for p in modelo["placas"]}
    placas = {nombres[pid]: caras_a_region([_hacia_arriba(c) for x in region_a_caras(region)
                                            for c in geo.caras(geo.transformar(x, mat))])
              for pid, region in modelo["placas"].items()}
    pliegues = {}
    for bid, b in modelo["pliegues"].items():
        o, a = np.array(b["o"]), _eje(b)
        o2, n2 = pt(o), lin @ np.array(b["n"])
        a2 = np.array([n2[1], -n2[0]])
        tramos = sorted(sorted([float((pt(o + e0 * a) - o2) @ a2), float((pt(o + e1 * a) - o2) @ a2)])
                        for e0, e1 in b["tramos"])
        pliegues[f"{prefijo}{bid}"] = dict(b, padre=nombres[b["padre"]], hija=nombres[b["hija"]], o=o2.tolist(),
                                           n=n2.tolist(), tramos=tramos,
                                           sentido=-b["sentido"] if voltear else b["sentido"])
    return placas, pliegues, nombres


def _estirar(caras, p, d, n, s0, s1, xi):
    """Alarga (xi > 0) o recorta (xi < 0) la cara en el borde p + s·d (s ∈ [s0, s1]) hasta ξ = xi."""
    a = np.array([n[1], -n[0]])
    sg = float(np.sign(d @ a))
    e0, e1 = sorted([s0 * sg, s1 * sg])
    if xi > TOL:
        return _op2d(caras, [_rect(p, a, n, e0, e1, -_DELTA, xi)], "unir")
    if xi < -TOL:
        return _op2d(caras, [_rect(p, a, n, e0, e1, xi, _MARGEN)], "cortar")
    return caras


def unir_plegando(modelo_a, arista_a, modelo_b, arista_b, radio=None):
    """Unir plegando [SM-REF-JOIN-BY-BEND]: une dos piezas del mismo espesor con un pliegue entre dos aristas
    rectas paralelas de sus bordes. Cada cara se alarga o se recorta hasta las tangentes del pliegue (radio de la
    regla de la pieza A o `radio`). Devuelve el modelo unido (manda la pieza A: regla y marco)."""
    t, k = modelo_a["regla"]["espesor"], modelo_a["regla"]["k"]
    if abs(t - modelo_b["regla"]["espesor"]) > 1e-6:
        raise geo.ErrorGeometria("Las dos piezas tienen que tener el mismo espesor.")
    r = modelo_a["regla"]["radio"] if radio is None else float(radio)
    pa, a_p, a_q, _wa, libres_a = ubicar_arista(modelo_a, arista_a)
    pb, b_p, b_q, _wb, libres_b = ubicar_arista(modelo_b, arista_b)
    ma, mb = copy.deepcopy(modelo_a), _reenraizar(modelo_b, pb)
    wa, wb = _m(ma) @ transformaciones(ma)[pa], _m(mb)          # la raíz de B es ahora la placa de la arista
    ca, cb = region_a_caras(ma["placas"][pa]), region_a_caras(mb["placas"][pb])
    da2, db2 = (a_q - a_p) / np.linalg.norm(a_q - a_p), (b_q - b_p) / np.linalg.norm(b_q - b_p)
    sa0, sa1 = max(libres_a, key=lambda x: x[1] - x[0])
    sb0, sb1 = max(libres_b, key=lambda x: x[1] - x[0])
    na2, nb2 = _normal_exterior(ca, a_p, da2, (sa0 + sa1) / 2), _normal_exterior(cb, b_p, db2, (sb0 + sb1) / 2)
    e = wa[:3, :3] @ np.array([*da2, 0.0])
    if np.linalg.norm(np.cross(e, wb[:3, :3] @ np.array([*db2, 0.0]))) > 1e-6:
        raise geo.ErrorGeometria("Las aristas tienen que ser paralelas.")
    pa0 = _aplicar(wa, [*a_p, 0.0])
    # Sección perpendicular a las aristas: X a lo largo de A hacia afuera de su borde, Y = w de A.
    sec = np.array([wa[:3, :3] @ np.array([*na2, 0.0]), wa[:3, :3] @ np.array([0.0, 0.0, 1.0])])
    ub = sec @ (-(wb[:3, :3] @ np.array([*nb2, 0.0])))           # dirección hacia adentro de B
    ub = ub / np.linalg.norm(ub)
    pbs = sec @ (_aplicar(wb, [*b_p, t / 2]) - pa0)
    giro = math.atan2(ub[1], ub[0])
    if abs(giro) < 1e-6 or abs(abs(giro) - math.pi) < 1e-6:
        raise geo.ErrorGeometria("Las caras de las aristas son paralelas: no se pueden unir con un pliegue.")
    # Líneas medias: A = (s, t/2), B = pbs + q·ub; se cortan en V y el pliegue retira (R + t/2)·tan(θ/2).
    s_v, q_v = np.linalg.solve(np.array([[1.0, -ub[0]], [0.0, -ub[1]]]), pbs - np.array([0.0, t / 2]))
    retiro = (r + t / 2) * math.tan(abs(giro) / 2)
    xi_a, xi_b = s_v - retiro, -(q_v + retiro)
    angulo = math.degrees(abs(giro))
    # Tramo común de las dos aristas, medido a lo largo de e desde el comienzo de la de A.
    proy_a = sorted([sa0, sa1])
    proy_b = sorted(float((_aplicar(wb, [*(b_p + s * db2), 0.0]) - pa0) @ e) for s in (sb0, sb1))
    c0, c1 = max(proy_a[0], proy_b[0]), min(proy_a[1], proy_b[1])
    if c1 - c0 <= TOL:
        raise geo.ErrorGeometria("Las aristas no se enfrentan: no tienen un tramo en común.")
    ma["placas"][pa] = caras_a_region(_estirar(ca, a_p, da2, na2, sa0, sa1, xi_a))
    mb["placas"][pb] = caras_a_region(_estirar(cb, b_p, db2, nb2, sb0, sb1, xi_b))
    sg = float(np.sign(da2 @ np.array([na2[1], -na2[0]])))
    bid = _nuevo_id(ma, "b")
    nuevo = _datos_pliegue(pa, None, a_p + xi_a * na2, na2, longitud_pliegue(angulo, r, t, k),
                           [sorted([c0 * sg, c1 * sg])], r, angulo, 1 if giro > 0 else -1)
    # Dónde cae B en las coordenadas planas de A: E = (marco_A · M_pa · pliegue)⁻¹ · marco_B.
    e4 = np.linalg.inv(wa @ _matriz_pliegue(nuevo, t)) @ wb
    voltear = e4[2, 2] < 0
    if abs(abs(e4[2, 2]) - 1) > 1e-6 or np.linalg.norm(e4[2, :2]) > 1e-6 or \
            abs(e4[2, 3] - (t if voltear else 0.0)) > 1e-5 or (np.linalg.det(e4[:2, :2]) < 0) != voltear:
        raise geo.ErrorGeometria("Las dos piezas no quedan alineadas para unirse con un pliegue.")
    e3 = np.eye(3)
    e3[:2, :2], e3[:2, 2] = e4[:2, :2], e4[:2, 3]
    placas_b, pliegues_b, nombres = _mapear(mb, e3, voltear, f"u{bid}")
    nuevo["hija"] = nombres[pb]
    ma["placas"].update(placas_b)
    ma["pliegues"].update(pliegues_b)
    ma["pliegues"][bid] = nuevo
    return ma


# ---------------------------------------------------------------- cortes hechos con otras herramientas
def absorber(modelo, forma):
    """Incorpora al modelo los cortes hechos al cuerpo con herramientas comunes (agujeros, ranuras): cada parte
    plana se corta con su losa y se vuelve a medir a medio espesor. Devuelve (modelo, avisos)."""
    m = copy.deepcopy(modelo)
    t, f = m["regla"]["espesor"], _m(m)
    mats = transformaciones(m)
    avisos, total, esperado = [], 0.0, 0.0
    medio = geo.trasladar(_rect((-1e4, -1e4), (1, 0), (0, 1), 0, 2e4, 0, 2e4), (0, 0, t / 2))
    for pid, region in m["placas"].items():
        caras = region_a_caras(region)
        if not caras:
            continue
        w = f @ mats[pid]
        losa = geo.transformar(geo.compuesto([_prisma(c, t) for c in caras]), w)
        vol = _area(caras) * t
        comun = geo.booleano(forma, losa, "intersecar")
        v = geo.volumen(comun)
        esperado, total = esperado + vol, total + v
        if abs(v - vol) > max(1e-6, 1e-7 * vol):
            seccion = geo.booleano(geo.transformar(comun, np.linalg.inv(w)), medio, "intersecar")
            m["placas"][pid] = caras_a_region([_hacia_arriba(c) for c in
                                               geo.caras(geo.trasladar(seccion, (0, 0, -t / 2)))])
    for b in m["pliegues"].values():
        for e0, e1 in b["tramos"]:
            pieza = geo.transformar(_pieza_pliegue(b, t, e0, e1), f @ mats[b["padre"]])
            vol = _volumen_pliegue(b, t, e1 - e0)
            v = geo.volumen(geo.booleano(forma, pieza, "intersecar"))
            esperado, total = esperado + vol, total + v
            if abs(v - vol) > max(1e-6, 1e-6 * vol):
                avisos.append("Un corte atraviesa un pliegue: el modelo de chapa lo ignora (cortá las partes planas o "
                              "la pieza desplegada).")
    if total < 0.5 * esperado:
        raise geo.ErrorGeometria("El cuerpo de chapa cambió demasiado fuera del entorno de chapa (¿se movió?): "
                                 "hacé esos cambios antes de convertirlo, o solo en las partes planas.")
    if geo.volumen(forma) > total + max(1e-5, 1e-6 * total):
        avisos.append("Se agregó material fuera de la chapa (no tiene espesor constante): se ignora.")
    return m, list(dict.fromkeys(avisos))


# ---------------------------------------------------------------- patrón plano 2D y DXF
def contorno_plano(modelo):
    """Patrón plano en 2D (coordenadas planas): {"exteriores": [lazo], "interiores": [lazo], "centros": [(p, q)],
    "extensiones": [(p, q)], "area", "caja", "piezas"}. Lazos de primitivas ["l"…], ["a"…], ["c"…]."""
    caras = []
    for region in modelo["placas"].values():
        caras = _op2d(caras, region_a_caras(region), "unir")
    centros, extensiones, franjas = [], [], []
    for b in modelo["pliegues"].values():
        o, n, a = np.array(b["o"]), np.array(b["n"]), _eje(b)
        for e0, e1 in b["tramos"]:
            franjas.append(_rect(o, a, n, e0, e1, 0.0, b["ba"]))
            centros.append(((o + e0 * a + b["ba"] / 2 * n).tolist(), (o + e1 * a + b["ba"] / 2 * n).tolist()))
            extensiones += [((o + e0 * a + x * n).tolist(), (o + e1 * a + x * n).tolist()) for x in (0.0, b["ba"])]
    caras = _op2d(caras, franjas, "unir")
    region = caras_a_region(caras)
    pts = [v for c in caras for v in _puntos_2d(c)]
    caja = ((min(p[0] for p in pts), min(p[1] for p in pts)), (max(p[0] for p in pts), max(p[1] for p in pts))) \
        if pts else ((0.0, 0.0), (0.0, 0.0))
    return {"exteriores": [lazos[0] for lazos in region], "interiores": [x for lazos in region for x in lazos[1:]],
            "centros": centros, "extensiones": extensiones, "area": _area(caras), "caja": caja,
            "piezas": len(region)}


CAPAS_DXF = {"CONTORNO_EXTERIOR": {"color": 7}, "CONTORNOS_INTERIORES": {"color": 4},
             "LINEAS_PLIEGUE": {"color": 3, "tipo": "trazo_punto"}, "EXTENSION_PLIEGUE": {"color": 8, "tipo": "trazos"}}


def _prim_dxf(p, dx, dy):
    if p[0] == "l":
        return ("linea", (p[1] + dx, p[2] + dy), (p[3] + dx, p[4] + dy))
    if p[0] == "c":
        return ("circulo", (p[1] + dx, p[2] + dy), p[3])
    a0, a1 = (p[4], p[5]) if p[5] >= p[4] else (p[5], p[4])
    return ("arco", (p[1] + dx, p[2] + dy), p[3], a0, a1)


def entidades_dxf(modelo, centros=True, extensiones=False):
    """Pares (capa, primitiva) del patrón plano para `io_archivos.dxf.escribir_dxf`, con la esquina inferior
    izquierda en el origen: contorno exterior, contornos interiores y líneas de pliegue en capas separadas."""
    c = contorno_plano(modelo)
    dx, dy = -c["caja"][0][0], -c["caja"][0][1]
    ents = [("CONTORNO_EXTERIOR", _prim_dxf(p, dx, dy)) for lazo in c["exteriores"] for p in lazo]
    ents += [("CONTORNOS_INTERIORES", _prim_dxf(p, dx, dy)) for lazo in c["interiores"] for p in lazo]
    for clave, capa, activo in (("centros", "LINEAS_PLIEGUE", centros),
                                ("extensiones", "EXTENSION_PLIEGUE", extensiones)):
        if activo:
            ents += [(capa, ("linea", (p[0] + dx, p[1] + dy), (q[0] + dx, q[1] + dy))) for p, q in c[clave]]
    return ents


def exportar_dxf(modelo, ruta, centros=True, extensiones=False):
    """Exportar el patrón plano como DXF [GUID-9C211F95] (mm). Devuelve la ruta escrita."""
    from ..io_archivos.dxf import escribir_dxf
    return escribir_dxf(Path(ruta), entidades_dxf(modelo, centros, extensiones), CAPAS_DXF)


def resumen(modelo):
    """Datos para mostrar: regla, espesor, pliegues (y cuántos desplegados), tamaño y área del patrón plano."""
    c = contorno_plano(modelo)
    (x0, y0), (x1, y1) = c["caja"]
    return {"regla": modelo["regla"]["nombre"], "espesor": modelo["regla"]["espesor"],
            "pliegues": len(modelo["pliegues"]),
            "desplegados": sum(1 for b in modelo["pliegues"].values() if b["desplegado"]),
            "ancho": x1 - x0, "alto": y1 - y0, "area": c["area"]}

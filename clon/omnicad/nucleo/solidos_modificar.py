# -*- coding: utf-8 -*-
"""
SÓLIDO › MODIFICAR de Fusion sobre OpenCascade: empalme, chaflán, vaciado, desmoldeo, escala,
desfase / reemplazo / división de caras, división de cuerpo, división por silueta, mover/alinear y
supresión de caras (modelado directo).

Funciones puras: reciben formas OCC, numpy, `geo.Plano` o números y devuelven formas OCC (o
matrices 4x4 numpy). Milímetros y grados. Los errores salen como `geo.ErrorGeometria`.

Límites del kernel (no los tiene OpenCascade, no se emulan):
- Empalme: sin esquina "Setback", sin continuidad G2, sin radio asimétrico ni "Full Round".
  OpenCascade SIEMPRE propaga el empalme/chaflán por la cadena tangente de la arista
  (`cadena_tangente=False` no puede cortarla).
- Chaflán: el kernel solo hace la esquina "Chamfer" (cara triangular); "Miter" se arma con `_ingletear` y "Blend"
  con `_mezclar` (el inglete con las aristas entre chaflanes redondeadas).
- Desmoldeo: solo caras planas, cilíndricas o cónicas (BRepOffsetAPI_DraftAngle); sin "Parting Line".
"""
import math

import numpy as np
from . import motor as _motor


def _iniciar_opencascade():
    global Array1_gp_Pnt2d, BRepAdaptor_Curve, BRepAdaptor_Curve2d, BRepAdaptor_Surface
    global BRepAlgoAPI_Defeaturing, BRepAlgoAPI_Section, BRepAlgoAPI_Splitter, BRepBuilderAPI_GTransform
    global BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakeSolid, BRepBuilderAPI_MakeVertex
    global BRepBuilderAPI_Sewing
    global BRepBuilderAPI_Transform, BRepExtrema_DistShapeShape, BRepFeat_SplitShape, BRepFilletAPI_MakeChamfer
    global BRepFilletAPI_MakeFillet, BRepGProp_Face, BRepIntCurveSurface_Inter, BRepLib
    global BRepOffsetAPI_DraftAngle, BRepOffsetAPI_MakeOffsetShape, BRepOffsetAPI_MakeThickSolid
    global BRepOffset_Analyse, BRepOffset_MakeOffset, BRepOffset_Skin, BRepPrimAPI_MakePrism, BRepTools
    global BRep_Tool, ChFiDS_Concave, ChFiDS_Convex, ChFiDS_Tangential, Geom2dAPI_PointsToBSpline
    global GeomAPI_ProjectPointOnSurf, GeomAbs_Arc, GeomAbs_C2, GeomAbs_Cone, GeomAbs_Cylinder
    global GeomAbs_Intersection, GeomAbs_Line, GeomAbs_Plane, GeomAbs_Sphere, GeomAbs_Torus
    global IndexedDataMap_TopoDS_Shape_List_TopoDS_Shape_TopTools_ShapeMapHasher
    global IndexedMap_TopoDS_Shape_TopTools_ShapeMapHasher, List_TopoDS_Shape, ShapeFix_Face, ShapeFix_Shape
    global ShapeUpgrade_UnifySameDomain, TopAbs_EDGE, TopAbs_FACE, TopAbs_SHELL, TopAbs_VERTEX, TopExp, TopExp_Explorer
    global TopoDS, TopoDS_Edge, TopoDS_Face, TopoDS_Shape, gp_Ax3, gp_Cylinder, gp_Dir, gp_GTrsf, gp_Lin
    global gp_Mat, gp_Pln, gp_Pnt, gp_Pnt2d, gp_Trsf, gp_Vec, gp_XYZ
    from OCP.BRep import BRep_Tool
    from OCP.BRepAdaptor import BRepAdaptor_Curve, BRepAdaptor_Curve2d, BRepAdaptor_Surface
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Defeaturing, BRepAlgoAPI_Section, BRepAlgoAPI_Splitter
    from OCP.BRepBuilderAPI import (BRepBuilderAPI_GTransform, BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeFace,
                                    BRepBuilderAPI_MakeSolid, BRepBuilderAPI_MakeVertex, BRepBuilderAPI_Sewing,
                                    BRepBuilderAPI_Transform)
    from OCP.BRepExtrema import BRepExtrema_DistShapeShape
    from OCP.BRepFeat import BRepFeat_SplitShape
    from OCP.BRepFilletAPI import BRepFilletAPI_MakeChamfer, BRepFilletAPI_MakeFillet
    from OCP.BRepGProp import BRepGProp_Face
    from OCP.BRepIntCurveSurface import BRepIntCurveSurface_Inter
    from OCP.BRepLib import BRepLib
    from OCP.BRepOffset import BRepOffset_Analyse, BRepOffset_MakeOffset, BRepOffset_Skin
    from OCP.BRepOffsetAPI import (BRepOffsetAPI_DraftAngle, BRepOffsetAPI_MakeOffsetShape,
                                   BRepOffsetAPI_MakeThickSolid)
    from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism
    from OCP.BRepTools import BRepTools
    from OCP.ChFiDS import ChFiDS_Concave, ChFiDS_Convex, ChFiDS_Tangential
    from OCP.Geom2dAPI import Geom2dAPI_PointsToBSpline
    from OCP.GeomAbs import (GeomAbs_Arc, GeomAbs_C2, GeomAbs_Cone, GeomAbs_Cylinder, GeomAbs_Intersection,
                             GeomAbs_Line, GeomAbs_Plane, GeomAbs_Sphere, GeomAbs_Torus)
    from OCP.GeomAPI import GeomAPI_ProjectPointOnSurf
    from OCP.OCP.collections import (Array1_gp_Pnt2d, IndexedDataMap_TopoDS_Shape_List_TopoDS_Shape_TopTools_ShapeMapHasher,
                                     IndexedMap_TopoDS_Shape_TopTools_ShapeMapHasher, List_TopoDS_Shape)
    from OCP.ShapeFix import ShapeFix_Face, ShapeFix_Shape
    from OCP.ShapeUpgrade import ShapeUpgrade_UnifySameDomain
    from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE, TopAbs_SHELL, TopAbs_VERTEX
    from OCP.TopExp import TopExp, TopExp_Explorer
    from OCP.TopoDS import TopoDS, TopoDS_Edge, TopoDS_Face, TopoDS_Shape
    from OCP.gp import (gp_Ax3, gp_Cylinder, gp_Dir, gp_GTrsf, gp_Lin, gp_Mat, gp_Pln, gp_Pnt, gp_Pnt2d, gp_Trsf,
                        gp_Vec, gp_XYZ)


if _motor.motor_activo() == "opencascade":
    _iniciar_opencascade()

from . import geometria as geo

TOL = 1e-6


# ---------------------------------------------------------------- utilidades internas
def _np(p):
    return np.array([p.X(), p.Y(), p.Z()], float)


def _unicos(forma, tipo):
    mapa = IndexedMap_TopoDS_Shape_TopTools_ShapeMapHasher()
    TopExp.MapShapes_s(forma, tipo, mapa)
    return [mapa.FindKey(i) for i in range(1, mapa.Size() + 1)]


def _aristas(forma):
    return [TopoDS.Edge(e) for e in _unicos(forma, TopAbs_EDGE)]


def _ancestros(forma, tipo_hijo, tipo_padre):
    mapa = IndexedDataMap_TopoDS_Shape_List_TopoDS_Shape_TopTools_ShapeMapHasher()
    TopExp.MapShapesAndAncestors_s(forma, tipo_hijo, tipo_padre, mapa)
    return mapa


def _padres(mapa, hijo):
    """Padres únicos (sin repetir la cara de una arista de costura) en el orden del mapa."""
    if not mapa.Contains(hijo):
        return []
    salida = []
    for p in geo.lista_occ(mapa.FindFromKey(hijo)):
        if not any(p.IsSame(q) for q in salida):
            salida.append(p)
    return salida


def _contiene(lista, forma):
    return any(forma.IsSame(x) for x in lista)


def _lista_occ(formas):
    lista = List_TopoDS_Shape()
    for f in formas:
        lista.Append(f)
    return lista


def _diagonal(forma):
    caja = geo.caja_envolvente(forma)
    if caja is None:
        raise geo.ErrorGeometria("La forma está vacía.")
    return float(np.linalg.norm(np.subtract(caja[1], caja[0]))) or 1.0


def _centro(forma):
    p0, p1 = geo.caja_envolvente(forma)
    return (np.array(p0) + np.array(p1)) / 2


def _unificar(forma):
    """Junta caras y aristas coplanares que dejan los booleanos (como Fusion, que no deja costuras)."""
    u = ShapeUpgrade_UnifySameDomain(forma, True, True, False)
    u.Build()
    return u.Shape()


def _fusionar_costuras(forma):
    """Tras partir caras periódicas (cilindro, toro) la costura del kernel deja una cara de más:
    se vuelven a unir las piezas de la misma superficie SOLO a través de aristas de costura."""
    u = ShapeUpgrade_UnifySameDomain(forma, True, True, False)
    arista_caras = _ancestros(forma, TopAbs_EDGE, TopAbs_FACE)
    for e in _aristas(forma):
        if not any(BRep_Tool.IsClosed_s(e, TopoDS.Face(f)) for f in _padres(arista_caras, e)):
            u.KeepShape(e)
    u.Build()
    return u.Shape()


def _validar(forma, operacion):
    if forma is None or forma.IsNull() or geo.esta_vacia(forma):
        raise geo.ErrorGeometria(f"{operacion}: el kernel devolvió una forma vacía.")
    if not geo.es_valida(forma):
        arreglo = ShapeFix_Shape(forma)
        arreglo.Perform()
        forma = arreglo.Shape()
        if not geo.es_valida(forma):
            raise geo.ErrorGeometria(f"{operacion}: el resultado no es un sólido válido.")
    return forma


def _normal_en(cara, u, v):
    """Punto y normal unitaria (respeta la orientación de la cara: apunta hacia afuera del material)."""
    p, n = gp_Pnt(), gp_Vec()
    BRepGProp_Face(cara).Normal(float(u), float(v), p, n)
    m = n.Magnitude()
    return _np(p), (_np(n) / m if m > 1e-12 else np.zeros(3))


def _punto_normal(cara):
    """Punto representativo de la cara (proyección del centroide) y su normal hacia afuera."""
    c = geo.centro_masa(cara, superficie=True)
    proy = GeomAPI_ProjectPointOnSurf(gp_Pnt(*c), BRep_Tool.Surface_s(cara))
    if proy.NbPoints() > 0:
        u, v = proy.LowerDistanceParameters()
    else:
        u0, u1, v0, v1 = BRepTools.UVBounds_s(cara)
        u, v = (u0 + u1) / 2, (v0 + v1) / 2
    return _normal_en(cara, u, v)


def _normal_en_arista(arista, cara, t):
    uv = BRepAdaptor_Curve2d(arista, cara).Value(t)
    return _normal_en(cara, uv.X(), uv.Y())[1]


def _plano_de_cara(cara):
    """geo.Plano de una cara plana con la normal hacia afuera del material (None si no es plana)."""
    if BRepAdaptor_Surface(cara).GetType() != GeomAbs_Plane:
        return None
    p, n = _punto_normal(cara)
    return geo.Plano.desde_marco(p, n, (1.0, 0.0, 0.0))


def _cara_plana(plano, centro, semilado):
    """Cara rectangular grande sobre `plano`, centrada en la proyección de `centro`."""
    c = np.asarray(centro, float)
    c = c - plano.normal * float((c - plano.origen) @ plano.normal)
    ax3 = gp_Ax3(gp_Pnt(*c), gp_Dir(*plano.normal), gp_Dir(*plano.u))
    s = float(semilado)
    return BRepBuilderAPI_MakeFace(gp_Pln(ax3), -s, s, -s, s).Face()


def _cara_extendida(cara, valor):
    salida = TopoDS_Face()
    try:
        BRepLib.ExtendFace_s(cara, float(valor), True, True, True, True, salida)
    except Exception:  # noqa: BLE001 — superficies que no admiten extensión: se usa la original
        return cara
    return cara if salida.IsNull() else salida


def _herramienta_corte(herramienta, forma, extender):
    """Plano → cara grande; cara → cara (extendida si se pide); aristas/cuerpo → tal cual."""
    diag = _diagonal(forma)
    if isinstance(herramienta, geo.Plano):
        return _cara_plana(herramienta, _centro(forma), 2 * diag)
    if isinstance(herramienta, (list, tuple)):
        return geo.compuesto(list(herramienta))
    if isinstance(herramienta, TopoDS_Shape):
        if herramienta.ShapeType() == TopAbs_FACE:
            cara = TopoDS.Face(herramienta)
            if extender:
                if BRepAdaptor_Surface(cara).GetType() == GeomAbs_Plane:
                    return _cara_plana(_plano_de_cara(cara), _centro(forma), 2 * diag)
                return _cara_extendida(cara, 2 * diag)
            return cara
        return herramienta
    raise geo.ErrorGeometria("Herramienta de división no reconocida (plano, cara, aristas o cuerpo).")


def _partir(forma, herramientas):
    """BRepAlgoAPI_Splitter: parte `forma` con las herramientas (General Fuse)."""
    sp = BRepAlgoAPI_Splitter()
    sp.SetArguments(_lista_occ([forma]))
    sp.SetTools(_lista_occ(herramientas))
    sp.Build()
    if not sp.IsDone():
        raise geo.ErrorGeometria("La división falló en el kernel.")
    return sp.Shape()


def _tangente_en_vertice(arista, vertice):
    t = BRep_Tool.Parameter_s(TopoDS.Vertex(vertice), arista)
    p, v = gp_Pnt(), gp_Vec()
    BRepAdaptor_Curve(arista).D1(t, p, v)
    m = v.Magnitude()
    return _np(v) / m if m > 1e-12 else np.zeros(3)


def _analisis(forma, tol_ang):
    return BRepOffset_Analyse(forma, math.radians(tol_ang))


def _tipos_arista(analisis, arista):
    return {iv.Type() for iv in analisis.Type(arista)}


# ---------------------------------------------------------------- selección (cadenas tangentes)
def aristas_cadena_tangente(forma, arista, tol_ang=1.0):
    """Aristas unidas a `arista` con continuidad tangente en sus vértices (opción "Tangent Chain")."""
    vert_aristas = _ancestros(forma, TopAbs_VERTEX, TopAbs_EDGE)
    cadena, pendientes = [arista], [arista]
    sen_tol = math.sin(math.radians(tol_ang))
    while pendientes:
        e = pendientes.pop(0)
        for v in _unicos(e, TopAbs_VERTEX):
            te = _tangente_en_vertice(e, v)
            for otra in _padres(vert_aristas, v):
                otra = TopoDS.Edge(otra)
                if _contiene(cadena, otra) or BRep_Tool.Degenerated_s(otra):
                    continue
                if np.linalg.norm(np.cross(te, _tangente_en_vertice(otra, v))) < sen_tol:
                    cadena.append(otra)
                    pendientes.append(otra)
    return cadena


def caras_tangentes(forma, cara, tol_ang=1.0):
    """Cara + todas las caras unidas a ella por aristas tangentes (cadena de caras tangentes)."""
    analisis = _analisis(forma, tol_ang)
    arista_caras = _ancestros(forma, TopAbs_EDGE, TopAbs_FACE)
    cadena, pendientes = [cara], [cara]
    while pendientes:
        f = pendientes.pop(0)
        for e in _unicos(f, TopAbs_EDGE):
            e = TopoDS.Edge(e)
            if ChFiDS_Tangential not in _tipos_arista(analisis, e):
                continue
            for otra in _padres(arista_caras, e):
                if not _contiene(cadena, otra):
                    cadena.append(TopoDS.Face(otra))
                    pendientes.append(TopoDS.Face(otra))
    return cadena


def _ampliar_tangentes(forma, aristas, activo):
    if not activo:
        return list(aristas)
    salida = []
    for a in aristas:
        for e in aristas_cadena_tangente(forma, a):
            if not _contiene(salida, e):
                salida.append(e)
    return salida


# ---------------------------------------------------------------- empalme
def _angulo_entre_caras(forma, arista):
    """Ángulo (rad) entre las normales de las dos caras de la arista, en su punto medio."""
    caras = _padres(_ancestros(forma, TopAbs_EDGE, TopAbs_FACE), arista)
    if len(caras) != 2:
        raise geo.ErrorGeometria("La arista no separa exactamente dos caras.")
    c = BRepAdaptor_Curve(arista)
    t = (c.FirstParameter() + c.LastParameter()) / 2
    n1 = _normal_en_arista(arista, TopoDS.Face(caras[0]), t)
    n2 = _normal_en_arista(arista, TopoDS.Face(caras[1]), t)
    return math.acos(max(-1.0, min(1.0, float(n1 @ n2))))


def _perfil_de_empalme(c, p1, p2, continuidad):
    """Arista de la sección de un empalme por perfil: de `p1` a `p2` con la esquina `c` como punto de control.
    G1 (tangente): arco cónico (racional de grado 2), un círculo si las dos distancias a la esquina son iguales. G2 (curvatura):
    Bézier de grado 5 con los tres primeros y los tres últimos puntos de control en línea con las caras, así la curvatura
    es cero donde empalma con ellas."""
    from OCP.Geom import Geom_BezierCurve
    from OCP.OCP.collections import Array1_double, Array1_gp_Pnt
    c, p1, p2 = (np.asarray(x, float) for x in (c, p1, p2))
    if continuidad == "g2":
        puntos = [p1, p1 + 0.3 * (c - p1), p1 + 0.55 * (c - p1), p2 + 0.55 * (c - p2), p2 + 0.3 * (c - p2), p2]
        pesos = [1.0] * 6
    else:
        u1, u2 = (p1 - c) / np.linalg.norm(p1 - c), (p2 - c) / np.linalg.norm(p2 - c)
        alfa = math.acos(max(-1.0, min(1.0, float(u1 @ u2))))
        puntos, pesos = [p1, c, p2], [1.0, math.sin(alfa / 2), 1.0]
    arr, w = Array1_gp_Pnt(1, len(puntos)), Array1_double(1, len(puntos))
    for i, (q, k) in enumerate(zip(puntos, pesos, strict=True), 1):
        arr.SetValue(i, gp_Pnt(*map(float, q)))
        w.SetValue(i, k)
    return BRepBuilderAPI_MakeEdge(Geom_BezierCurve(arr, w)).Edge()


def plano_de_extremo(formas, direccion, extremo, nombre="Plano neutro"):
    """Plano de normal `direccion` que pasa por el vértice de `formas` más atrás (extremo "min") o más adelante ("max")
    en esa dirección: la bisagra de un desmoldeo con «Mover línea de partición» (el borde de la cara del lado contrario)."""
    d = np.asarray(direccion, float)
    d = d / np.linalg.norm(d)
    puntos = [np.array([q.X(), q.Y(), q.Z()]) for f in formas for q in (BRep_Tool.Pnt_s(TopoDS.Vertex(v)) for v in _unicos(f, TopAbs_VERTEX))]
    if not puntos:
        raise geo.ErrorGeometria("Las caras no tienen vértices de donde sacar el borde que no se mueve.")
    k = [float(p @ d) for p in puntos]
    p = puntos[k.index(min(k) if extremo == "min" else max(k))]
    return geo.Plano.desde_marco(p, d, (1.0, 0.0, 0.0), nombre)


def _reubicar_arista(forma, ref):
    """La arista de `forma` que ocupa el lugar de `ref` (una arista de la forma original, antes de un corte o relleno)."""
    c = BRepAdaptor_Curve(ref)
    q = c.Value((c.FirstParameter() + c.LastParameter()) / 2)
    medio, largo = np.array([q.X(), q.Y(), q.Z()]), geo.longitud(ref)
    for e in _aristas(forma):
        k = BRepAdaptor_Curve(e)
        r = k.Value((k.FirstParameter() + k.LastParameter()) / 2)
        if abs(r.X() - medio[0]) + abs(r.Y() - medio[1]) + abs(r.Z() - medio[2]) < 1e-6 and abs(geo.longitud(e) - largo) < 1e-6:
            return e
    raise geo.ErrorGeometria("Una arista del empalme ya no existe: los empalmes de radio asimétrico o G2 no pueden compartir "
                             "vértice con otro empalme del mismo paso (hacelos en pasos separados).")


def _empalme_por_perfil(forma, arista, radio1, radio2, continuidad):
    """Empalme de una arista recta entre dos caras planas con la sección que se pide (`_perfil_de_empalme`): radio
    asimétrico (`radio1` sobre la primera cara, `radio2` sobre la segunda) y/o continuidad G2. OpenCascade no los tiene:
    se corta (arista convexa) o se rellena (cóncava) con el prisma de la esquina, de la sección a lo largo de la arista.
    El «radio» de cada lado es el del círculo con esa distancia a la esquina (tangente = r / tan(α/2)); con radios iguales
    y G1 sale el empalme circular de siempre."""
    caras = [TopoDS.Face(f) for f in _padres(_ancestros(forma, TopAbs_EDGE, TopAbs_FACE), arista)]
    curva = BRepAdaptor_Curve(arista)
    if len(caras) != 2 or curva.GetType() != GeomAbs_Line or any(_plano_de_cara(f) is None for f in caras):
        raise geo.ErrorGeometria("El radio asimétrico y la continuidad G2 solo se hacen en aristas rectas entre dos caras "
                                 "planas.")
    a, b = (np.array([q.X(), q.Y(), q.Z()]) for q in (curva.Value(curva.FirstParameter()), curva.Value(curva.LastParameter())))
    largo = float(np.linalg.norm(b - a))
    t = (b - a) / largo
    direcciones = []
    for f in caras:
        n = np.asarray(_plano_de_cara(f).normal, float)
        u = np.cross(n, t)
        u /= np.linalg.norm(u)
        if float((geo.centro_masa(f, True) - a) @ u) < 0:
            u = -u
        direcciones.append(u)
    u1, u2 = direcciones
    alfa = math.acos(max(-1.0, min(1.0, float(u1 @ u2))))
    if alfa < 1e-3 or alfa > math.pi - 1e-3:
        raise geo.ErrorGeometria("La arista no tiene esquina que empalmar (las caras son tangentes).")
    d1, d2 = radio1 / math.tan(alfa / 2), radio2 / math.tan(alfa / 2)
    centro = (a + b) / 2
    convexa = geo.punto_toca(forma, tuple(centro + 1e-3 * (u1 + u2) / np.linalg.norm(u1 + u2)), 1e-9)
    p1, p2 = a + d1 * u1, a + d2 * u2
    for cara, u, d in ((caras[0], u1, d1), (caras[1], u2, d2)):      # el radio no puede pasar del ancho de la cara
        ancho = max(float((np.array([q.X(), q.Y(), q.Z()]) - a) @ u)
                    for q in (BRep_Tool.Pnt_s(TopoDS.Vertex(v)) for v in _unicos(cara, TopAbs_VERTEX)))
        if d > ancho * (1 - 1e-9):
            raise geo.ErrorGeometria("El empalme falló: el radio es demasiado grande para las caras vecinas (no entra). "
                                     "Achicalo.")
    # el prisma recto de la esquina sobraría (o dejaría una astilla) si las caras de los extremos no fueran perpendiculares
    por_vertice = _ancestros(forma, TopAbs_VERTEX, TopAbs_FACE)
    for v in _unicos(arista, TopAbs_VERTEX):
        for f in _padres(por_vertice, v):
            plano = _plano_de_cara(TopoDS.Face(f))
            if not any(f.IsSame(c) for c in caras) and (plano is None or abs(abs(float(np.asarray(plano.normal) @ t)) - 1) > 1e-6):
                raise geo.ErrorGeometria("El radio asimétrico y la continuidad G2 necesitan caras planas perpendiculares "
                                         "a la arista en sus extremos.")
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeWire
    perfil = BRepBuilderAPI_MakeWire()
    for e in (BRepBuilderAPI_MakeEdge(gp_Pnt(*map(float, a)), gp_Pnt(*map(float, p1))).Edge(),
              _perfil_de_empalme(a, p1, p2, continuidad),
              BRepBuilderAPI_MakeEdge(gp_Pnt(*map(float, p2)), gp_Pnt(*map(float, a))).Edge()):
        perfil.Add(e)
    prisma = geo.extruir([BRepBuilderAPI_MakeFace(perfil.Wire()).Face()], tuple(t), largo)
    return _validar(geo.booleano(forma, prisma, "cortar" if convexa else "unir"), "Empalme")


FACTOR_SETBACK = 1.6        # cuánto crece el radio justo en la esquina (en la distancia de setback vuelve al radio pedido)


def _radios_con_setback(arista, radio, setback, esquinas):
    """Puntos (posición 0..1, radio) de una arista con esquina «Setback»: constante salvo en los extremos que tocan una
    esquina (`esquinas`: vértices donde se juntan tres o más aristas empalmadas), donde el radio crece hasta
    `FACTOR_SETBACK` veces en el vértice y baja al radio pedido a `setback` mm de él."""
    largo = geo.longitud(arista)
    vertices = _unicos(arista, TopAbs_VERTEX)
    c = BRepAdaptor_Curve(arista)
    punto = lambda p: (p.X(), p.Y(), p.Z())  # noqa: E731
    en_inicio = any(_contiene(esquinas, v) and np.allclose(punto(BRep_Tool.Pnt_s(TopoDS.Vertex(v))), punto(c.Value(c.FirstParameter())), atol=1e-6)
                    for v in vertices)
    en_final = any(_contiene(esquinas, v) and np.allclose(punto(BRep_Tool.Pnt_s(TopoDS.Vertex(v))), punto(c.Value(c.LastParameter())), atol=1e-6)
                   for v in vertices)
    u = min(0.45, setback / largo)
    n = 8                           # con menos puntos OpenCascade interpola una ley que se hunde bajo el radio pedido

    def rampa(t):                   # radio a la fracción t (0 = en el vértice, 1 = a `setback` mm de él)
        return radio + radio * (FACTOR_SETBACK - 1) * (1 + math.cos(math.pi * t)) / 2
    inicio = [(u * i / n, rampa(i / n)) for i in range(n + 1)] if en_inicio else [(0.0, radio)]
    final = [(1 - u * i / n, rampa(i / n)) for i in range(n, -1, -1)] if en_final else [(1.0, radio)]
    medio = [(0.5, radio)] if inicio[-1][0] < 0.5 < final[0][0] else []
    return inicio + medio + final


def empalme(forma, grupos, *, cadena_tangente=True):
    """Empalme (Fillet, tipo Fillet) por conjuntos de selección, cada uno con su tipo de radio.

    grupos: [{"aristas": [TopoDS_Edge], "tipo": "constante" | "variable" | "cuerda",
              "radio": r, "radios": [(posición 0..1, r), ...], "cuerda": c}]
    "cuerda" (Chord Length): radio = c / (2·sen(φ/2)), φ = ángulo entre normales en el medio de la arista.
    "variable": la posición se mide sobre cada arista (0 = inicio, 1 = fin), como los Radius Points.
    "esquina": "bola" (Rolling Ball, por defecto) o "setback" (con "setback" mm): donde se juntan tres o más aristas
    del conjunto, el radio crece hacia el vértice y vuelve al pedido a esa distancia (aproximado con radio variable).
    "asimetrico": `radio` sobre una cara y `radio2` sobre la otra. "continuidad": "g1" (por defecto) o "g2". Estos dos
    se hacen con `_empalme_por_perfil` (aristas rectas entre caras planas, una por una, sin cadena tangente) y van antes
    que el resto de los conjuntos, que se hacen con el kernel.
    """
    if not grupos:
        raise geo.ErrorGeometria("Elegí al menos una arista para empalmar.")
    por_perfil = [g for g in grupos if g.get("tipo") == "asimetrico" or g.get("continuidad") == "g2"]
    if por_perfil:
        for g in por_perfil:
            if g.get("tipo", "constante") not in ("constante", "asimetrico") or float(g.get("radio", 0)) <= 0 or (
                    g.get("tipo") == "asimetrico" and float(g.get("radio2", 0)) <= 0):
                raise geo.ErrorGeometria("La continuidad G2 va con radio constante o asimétrico, y los radios deben ser positivos.")
            for e in g.get("aristas") or []:
                e = _reubicar_arista(forma, e)
                forma = _empalme_por_perfil(forma, e, float(g["radio"]),
                                            float(g["radio2"]) if g.get("tipo") == "asimetrico" else float(g["radio"]),
                                            g.get("continuidad", "g1"))
        grupos = [dict(g, aristas=[_reubicar_arista(forma, e) for e in g.get("aristas") or []])
                  for g in grupos if all(g is not x for x in por_perfil)]
        if not grupos:
            return forma
    mf = BRepFilletAPI_MakeFillet(forma)
    for grupo in grupos:
        tipo = grupo.get("tipo", "constante")
        aristas = _ampliar_tangentes(forma, grupo.get("aristas") or [], cadena_tangente)
        if not aristas:
            raise geo.ErrorGeometria("Un conjunto de empalme no tiene aristas.")
        esquinas = []
        if grupo.get("esquina") == "setback":
            if tipo != "constante" or float(grupo.get("setback", 0)) <= 0:
                raise geo.ErrorGeometria("La esquina Setback va con radio constante y una distancia de setback positiva.")
            incidencia = {}
            for e in aristas:
                for v in _unicos(e, TopAbs_VERTEX):
                    k = next((w for w in incidencia if w.IsSame(v)), v)
                    incidencia[k] = incidencia.get(k, 0) + 1
            esquinas = [v for v, n in incidencia.items() if n >= 3]
        for e in aristas:
            if mf.Contour(e):           # ya está en un contorno (OpenCascade propaga por tangencia)
                continue
            if tipo == "constante" and esquinas:
                r = float(grupo.get("radio", 0))
                if r <= 0:
                    raise geo.ErrorGeometria("El radio del empalme debe ser positivo.")
                puntos = _radios_con_setback(e, r, float(grupo["setback"]), esquinas)
                arr = Array1_gp_Pnt2d(1, len(puntos))
                for i, (u, rr) in enumerate(puntos, 1):
                    arr.SetValue(i, gp_Pnt2d(u, rr))
                mf.Add(arr, e)
            elif tipo == "constante":
                r = float(grupo.get("radio", 0))
                if r <= 0:
                    raise geo.ErrorGeometria("El radio del empalme debe ser positivo.")
                mf.Add(r, e)
            elif tipo == "cuerda":
                c = float(grupo.get("cuerda", 0))
                phi = _angulo_entre_caras(forma, e)
                if c <= 0 or phi < 1e-6:
                    raise geo.ErrorGeometria("La cuerda debe ser positiva y la arista no puede ser tangente.")
                mf.Add(c / (2 * math.sin(phi / 2)), e)
            elif tipo == "variable":
                puntos = sorted((float(u), float(r)) for u, r in grupo.get("radios", []))
                if len(puntos) < 2 or puntos[0][0] < 0 or puntos[-1][0] > 1 or min(r for _, r in puntos) <= 0:
                    raise geo.ErrorGeometria("El radio variable necesita ≥ 2 puntos con posición 0..1 y radio > 0.")
                arr = Array1_gp_Pnt2d(1, len(puntos))
                for i, (u, r) in enumerate(puntos, 1):
                    arr.SetValue(i, gp_Pnt2d(u, r))
                mf.Add(arr, e)
            else:
                raise geo.ErrorGeometria(f"Tipo de radio desconocido: {tipo}")
    if mf.NbContours() == 0:
        raise geo.ErrorGeometria("Las aristas elegidas no pertenecen al cuerpo.")
    try:
        mf.Build()
    except Exception:  # noqa: BLE001 — StdFail_NotDone
        pass
    if not mf.IsDone():
        # PL4 (tutorial «Fillet Order of Operations» de Plasticity): el orden de los empalmes es de
        # lo GRANDE a lo chico; un empalme chico hecho primero puede comerse el material del grande.
        raise geo.ErrorGeometria("El empalme falló: el radio es demasiado grande para las caras vecinas (no entra). "
                                 "Achicalo. Si el timeline tiene otros empalmes en la misma zona, probá primero el "
                                 "radio MAYOR y después los más chicos (de lo grande a lo chico) y reordená los "
                                 "empalmes del timeline en ese orden.")
    return _validar(mf.Shape(), "Empalme")


def empalme_completo(forma, central, lateral1, lateral2):
    """Redondeo completo (Full Round Fillet): la cara `central` se vuelve un semicírculo tangente a las dos caras laterales.
    Solo para dos caras laterales planas y paralelas, perpendiculares a la central, cuyas aristas con ella son rectas (el
    caso de una pared que se remata con media caña): el radio es la mitad de la distancia entre las laterales. El kernel
    no hace este empalme con un radio exacto (las dos superficies quedan tangentes entre sí), así que se corta la
    esquina con una caja menos un cilindro."""
    pc, p1, p2 = (_plano_de_cara(c) for c in (central, lateral1, lateral2))
    if None in (pc, p1, p2):
        raise geo.ErrorGeometria("El redondeo completo necesita tres caras planas (una central y dos laterales).")
    n, n1, n2 = (np.asarray(p.normal, float) for p in (pc, p1, p2))
    if abs(float(n1 @ n2) + 1) > 1e-6:
        raise geo.ErrorGeometria("Las dos caras laterales del redondeo completo tienen que ser paralelas y enfrentadas.")
    if abs(float(n @ n1)) > 1e-6:
        raise geo.ErrorGeometria("Las caras laterales tienen que ser perpendiculares a la cara central.")
    ancho = abs(float((np.asarray(p2.origen, float) - np.asarray(p1.origen, float)) @ n1))
    if ancho < 1e-6:
        raise geo.ErrorGeometria("Las caras laterales coinciden.")
    compartidas = _ancestros(forma, TopAbs_EDGE, TopAbs_FACE)
    aristas = [e for e in _aristas(central) if any(f.IsSame(lateral1) for f in _padres(compartidas, e))]
    if len(aristas) != 1:
        raise geo.ErrorGeometria("La cara central tiene que compartir una arista con la primera lateral.")
    e1 = aristas[0]
    a, b = (np.array([q.X(), q.Y(), q.Z()]) for q in (BRep_Tool.Pnt_s(TopExp.FirstVertex_s(e1)),
                                                     BRep_Tool.Pnt_s(TopExp.LastVertex_s(e1))))
    largo = float(np.linalg.norm(b - a))
    if largo < 1e-6:
        raise geo.ErrorGeometria("La arista del redondeo completo no tiene largo.")
    eje = (b - a) / largo
    if abs(float(eje @ n1)) > 1e-6 or abs(float(eje @ n)) > 1e-6 or BRepAdaptor_Curve(e1).GetType() != GeomAbs_Line:
        raise geo.ErrorGeometria("Las aristas del redondeo completo tienen que ser rectas y paralelas a las caras laterales.")
    r = ancho / 2
    m = -n1                                                   # de la primera lateral hacia la segunda
    centro = a + m * r - n * r                                # eje del cilindro, r por debajo de la cara central
    esquina = centro - m * r
    marco = np.identity(4)
    marco[:3, 0], marco[:3, 1], marco[:3, 2], marco[:3, 3] = m, eje, n, esquina
    herramienta = geo.booleano(geo.transformar(geo.caja(ancho, largo, r + 1.0), marco),
                               geo.cilindro(r, largo, tuple(centro), tuple(eje)), "cortar")
    return _validar(geo.unificar_caras(geo.booleano(forma, herramienta, "cortar")), "Redondeo completo")


def empalme_reglas(forma, caras_a, caras_b=None, *, radio, tipo="todas", redondeos="ambos"):
    """Rule Fillet: "todas" = todas las aristas de caras_a; "entre" = aristas compartidas entre
    caras_a y caras_b. redondeos: "ambos" | "redondeos" (solo convexas) | "empalmes" (solo cóncavas)."""
    if tipo not in ("todas", "entre"):
        raise geo.ErrorGeometria(f"Regla desconocida: {tipo}")
    if tipo == "entre" and not caras_b:
        raise geo.ErrorGeometria("La regla 'entre' necesita dos conjuntos de caras.")
    filtro = {"ambos": {ChFiDS_Convex, ChFiDS_Concave}, "redondeos": {ChFiDS_Convex},
              "empalmes": {ChFiDS_Concave}}.get(redondeos)
    if filtro is None:
        raise geo.ErrorGeometria(f"Opción Rounds/Fillets desconocida: {redondeos}")
    analisis = _analisis(forma, 1.0)
    arista_caras = _ancestros(forma, TopAbs_EDGE, TopAbs_FACE)
    elegidas = []
    for e in _aristas(forma):
        caras = _padres(arista_caras, e)
        if len(caras) != 2 or BRep_Tool.Degenerated_s(e) or not (_tipos_arista(analisis, e) & filtro):
            continue
        en_a = [_contiene(caras_a, f) for f in caras]
        if tipo == "todas":
            ok = any(en_a)
        else:
            en_b = [_contiene(caras_b, f) for f in caras]
            ok = (en_a[0] and en_b[1]) or (en_a[1] and en_b[0])
        if ok:
            elegidas.append(e)
    if not elegidas:
        raise geo.ErrorGeometria("La regla no encontró aristas para empalmar.")
    return empalme(forma, [{"aristas": elegidas, "tipo": "constante", "radio": radio}], cadena_tangente=False)


# ---------------------------------------------------------------- chaflán
def caras_entre_semilla_y_limite(forma, semilla, caras_limite=(), aristas_limite=()):
    """Seleccionar › Semilla y límite: las caras de `forma` a las que se llega desde la cara `semilla` pasando de cara
    en cara por las aristas, sin cruzar las aristas límite ni entrar en las caras límite (la semilla va primero)."""
    vecinas = _ancestros(forma, TopAbs_EDGE, TopAbs_FACE)
    vistas, pendientes = [semilla], [semilla]
    while pendientes:
        for a in _aristas(pendientes.pop()):
            if _contiene(aristas_limite, a):
                continue
            for otra in _padres(vecinas, a):
                if not _contiene(vistas, otra) and not _contiene(caras_limite, otra):
                    vistas.append(TopoDS.Face(otra))
                    pendientes.append(vistas[-1])
    return vistas


def _sobre_la_superficie(cara, superficie):
    """¿El centro de la cara está sobre `superficie` (compuesto de caras)? Distingue las caras que ya existían de las
    que creó una operación."""
    p, _ = _punto_normal(cara)
    return BRepExtrema_DistShapeShape(BRepBuilderAPI_MakeVertex(gp_Pnt(*p)).Vertex(), superficie).Value() < 1e-6


def _ingletear(original, chaflanado, alcance):
    """Esquina «Inglete» (Corner Type › Miter): donde se juntan varios chaflanes el kernel deja una cara chica que los
    une (esquina «Chaflán»); acá las caras de los chaflanes se prolongan hasta cortarse en un punto. En cada una de
    esas caras de unión, se agrega lo que queda entre ella y el vértice: el cuerpo original recortado por los planos
    de los chaflanes que llegan, dentro de una caja de lado `alcance` alrededor. Solo chaflanes planos."""
    superficie = geo.compuesto(geo.caras(original))
    nuevas = [c for c in geo.caras(chaflanado) if not _sobre_la_superficie(c, superficie)]
    arista_caras = _ancestros(chaflanado, TopAbs_EDGE, TopAbs_FACE)

    def vecinas_nuevas(cara):
        salida = []
        for e in _aristas(cara):
            salida += [f for f in _padres(arista_caras, e) if not f.IsSame(cara) and _contiene(nuevas, f)
                       and not _contiene(salida, f)]
        return salida
    resultado, hubo = chaflanado, False
    for union in nuevas:
        lados = vecinas_nuevas(union)
        if len(lados) < 3:               # una cara de unión toca a tres chaflanes; con menos no hay esquina que ingletear
            continue
        centro = geo.centro_masa(union, True)
        local = geo.caja(2 * alcance, 2 * alcance, 2 * alcance, tuple(c - alcance for c in centro))
        local = geo.booleano(original, local, "intersecar")
        for chaflan_ in lados:
            plano = geo.plano_de_cara(TopoDS.Face(chaflan_))
            if plano is None:
                raise geo.ErrorGeometria("La esquina «Inglete» solo funciona con chaflanes planos (aristas rectas "
                                         "entre caras planas).")
            # la losa se centra en el origen del plano (proyección del origen del mundo): se suma lo que se aleja la esquina
            tam = 4 * alcance + 4 * _diagonal(original) + float(np.linalg.norm(plano.origen - centro))
            detras = geo.extruir([geo.cara_de_plano(plano, tam)], plano.normal, -tam)
            local = geo.booleano(local, detras, "intersecar")
        resultado, hubo = geo.booleano(resultado, local, "unir"), True
    if not hubo:
        raise geo.ErrorGeometria("No hay esquinas donde se junten tres chaflanes: la esquina «Inglete» no tiene "
                                 "nada que hacer.")
    return _validar(geo.unificar_caras(resultado), "Chaflán")


def _mezclar(original, chaflanado, alcance, distancia):
    """Esquina «Mezcla» (Corner Type › Blend): el inglete de `_ingletear` con las aristas que unen los chaflanes
    entre sí redondeadas, así los chaflanes se funden en el vértice sin arista viva. Radio: 0,4 de la distancia menor;
    si el kernel no puede, se prueba con la mitad (hasta tres veces)."""
    inglete = _ingletear(original, chaflanado, alcance)
    superficie = geo.compuesto(geo.caras(original))
    nuevas = [c for c in geo.caras(inglete) if not _sobre_la_superficie(c, superficie)]
    arista_caras = _ancestros(inglete, TopAbs_EDGE, TopAbs_FACE)
    entre = []
    for cara in nuevas:
        for e in _aristas(cara):
            padres = _padres(arista_caras, e)
            if len(padres) == 2 and all(_contiene(nuevas, p) for p in padres) and not _contiene(entre, e):
                entre.append(e)
    radio = 0.4 * distancia
    for _ in range(3):
        try:
            return _validar(empalme(inglete, [{"aristas": entre, "tipo": "constante", "radio": radio}]), "Chaflán")
        except geo.ErrorGeometria:
            radio /= 2
    raise geo.ErrorGeometria("La esquina «Mezcla» no pudo redondear la unión de los chaflanes: probá «Inglete» o "
                             "una distancia menor.")


def chaflan(forma, grupos, *, cadena_tangente=True, esquina="chaflan"):
    """Chaflán (Chamfer) por conjuntos de selección.

    grupos: [{"aristas": [TopoDS_Edge], "tipo": "distancia_igual" | "dos_distancias" | "distancia_angulo",
              "distancia": d (d1), "distancia2": d2, "angulo": grados, "cara": TopoDS_Face opcional,
              "voltear": bool}]
    "cara" es el lado donde se mide la primera distancia; si no viene se toma la primera cara vecina
    de la arista (orden estable del kernel) y "voltear" pasa a la otra (botón Flip de Fusion).
    `esquina` (Corner Type): "chaflan" (Chamfer: el kernel une los chaflanes con una cara chica), "inglete"
    (Miter: se cortan en un punto, ver `_ingletear`) o "mezcla" (Blend: inglete con la unión redondeada, `_mezclar`).
    """
    if esquina not in ("chaflan", "inglete", "mezcla"):
        raise geo.ErrorGeometria(f"Tipo de esquina del chaflán desconocido: {esquina}")
    if not grupos:
        raise geo.ErrorGeometria("Elegí al menos una arista para el chaflán.")
    arista_caras = _ancestros(forma, TopAbs_EDGE, TopAbs_FACE)
    mc = BRepFilletAPI_MakeChamfer(forma)
    elegidas = []
    for grupo in grupos:
        tipo = grupo.get("tipo", "distancia_igual")
        d1 = float(grupo.get("distancia", 0))
        if d1 <= 0:
            raise geo.ErrorGeometria("La distancia del chaflán debe ser positiva.")
        aristas = _ampliar_tangentes(forma, grupo.get("aristas") or [], cadena_tangente)
        if not aristas:
            raise geo.ErrorGeometria("Un conjunto de chaflán no tiene aristas.")
        for e in aristas:
            if mc.Contour(e):
                continue
            elegidas.append(e)
            if tipo == "distancia_igual":
                mc.Add(d1, e)
                continue
            vecinas = _padres(arista_caras, e)
            if len(vecinas) != 2:
                raise geo.ErrorGeometria("La arista del chaflán no separa dos caras.")
            cara = grupo.get("cara")
            if cara is None or not _contiene(vecinas, cara):
                cara = vecinas[0]
            if grupo.get("voltear"):
                cara = vecinas[1] if cara.IsSame(vecinas[0]) else vecinas[0]
            cara = TopoDS.Face(cara)
            if tipo == "dos_distancias":
                d2 = float(grupo.get("distancia2", 0))
                if d2 <= 0:
                    raise geo.ErrorGeometria("La segunda distancia del chaflán debe ser positiva.")
                mc.Add(d1, d2, e, cara)
            elif tipo == "distancia_angulo":
                ang = float(grupo.get("angulo", 45.0))
                if not 0 < ang < 90:
                    raise geo.ErrorGeometria("El ángulo del chaflán debe estar entre 0 y 90 grados.")
                mc.AddDA(d1, math.radians(ang), e, cara)
            else:
                raise geo.ErrorGeometria(f"Tipo de chaflán desconocido: {tipo}")
    if mc.NbContours() == 0:
        raise geo.ErrorGeometria("Las aristas elegidas no pertenecen al cuerpo.")
    try:
        mc.Build()
    except Exception:  # noqa: BLE001 — StdFail_NotDone
        pass
    if not mc.IsDone():
        longitudes = []
        for e in elegidas:
            vertices = _unicos(e, TopAbs_VERTEX)
            for cara in _padres(arista_caras, e):
                for vecina in _aristas(cara):
                    if not vecina.IsSame(e) and any(_contiene(vertices, v) for v in _unicos(vecina, TopAbs_VERTEX)):
                        longitud = geo.longitud(vecina)
                        if longitud > TOL:
                            longitudes.append(longitud)
        pista = ""
        if longitudes:
            # shortcut: estimación local, usar búsqueda geométrica si se necesita un límite exacto.
            pista = (f" Distancia máxima aproximada: {min(longitudes) / 2:g} mm "
                     "(mitad de la arista vecina más corta; no garantiza que el chaflán sea realizable).")
        raise geo.ErrorGeometria("El chaflán falló: la distancia es demasiado grande para las caras vecinas." + pista)
    resultado = _validar(mc.Shape(), "Chaflán")
    if esquina != "chaflan":
        alcance = 1.5 * max(float(g.get(k, 0) or 0) for g in grupos for k in ("distancia", "distancia2"))
        if esquina == "inglete":
            resultado = _ingletear(forma, resultado, alcance)
        else:
            resultado = _mezclar(forma, resultado, alcance, min(float(g.get(k) or 0) for g in grupos
                                                                for k in ("distancia", "distancia2") if g.get(k)))
    return resultado


# ---------------------------------------------------------------- vaciado
def _cara_sigue_puesta(resultado, cara, espesor):
    """True si la cara quitada sigue tapando el resultado. Se mira el punto central de la cara: en un vaciado bien
    hecho queda en la abertura, lejos de las paredes. Solo se decide si ese punto cae dentro de la cara y a más de
    cuatro espesores de su borde (más cerca, el canto de una pared inclinada puede taparlo con razón)."""
    p, _ = _punto_normal(cara)
    v = BRepBuilderAPI_MakeVertex(gp_Pnt(*p)).Vertex()
    if not geo.se_tocan(v, cara, 1e-5) or geo.se_tocan(v, geo.compuesto(_aristas(cara)), 4 * espesor):
        return False
    return geo.se_tocan(v, resultado, 1e-5)


def _medida_minima(forma):
    """La medida más chica de la caja envolvente de `forma` (mm)."""
    (x0, y0, z0), (x1, y1, z1) = geo.caja_envolvente(forma)
    return min(x1 - x0, y1 - y0, z1 - z0)


def _demasiado_grueso(forma, espesor, hueco=False):
    """Mensaje si el espesor no entra en la pieza (None si entra): con caras quitadas, una pared no puede ser más
    gruesa que la medida más chica de la caja envolvente; en un hueco cerrado, ni la mitad (las dos paredes de
    enfrente se tocan y no queda cavidad)."""
    medida = _medida_minima(forma)
    limite = medida / 2 if hueco else medida
    if abs(espesor) < limite - 1e-9:
        return None
    if hueco:
        return (f"El vaciado falló: el espesor ({abs(espesor):g} mm) es demasiado grande para un hueco cerrado: tiene "
                f"que ser menor que la mitad de la medida más chica de la pieza ({medida:g} mm).")
    return (f"El vaciado falló: el espesor ({abs(espesor):g} mm) es demasiado grande para la pieza (su medida más "
            f"chica es {medida:g} mm).")


def _resultado_imposible(forma, resultado, espesor):
    """True si lo que devolvió el kernel no puede ser el vaciado de `forma`: volumen cero o negativo (un sólido «al
    revés»), o material fuera de donde puede quedar la pared (hacia adentro, dentro de la caja de la pieza y con menos
    volumen que ella; hacia afuera, dentro de la caja agrandada en el espesor). Pasaba sin error: una caja de
    40 × 40 × 10 vaciada 25 mm salía más alta y con más volumen; un prisma con cortes cerca de la cara quitada, con
    volumen negativo."""
    despues = geo.volumen_exacto(resultado)
    if despues <= 0:
        return True
    caja, caja_r = geo.caja_envolvente(forma), geo.caja_envolvente(resultado)
    if caja_r is None:
        return True
    holgura = max(0.0, espesor) + max(1e-4 * math.dist(*caja), 1e-5)
    if any(r < a - holgura for r, a in zip(caja_r[0], caja[0], strict=True)) or \
            any(r > b + holgura for r, b in zip(caja_r[1], caja[1], strict=True)):
        return True
    return espesor < 0 and despues > geo.volumen_exacto(forma) * (1 + 1e-9)


def _falla_kernel(forma, espesor, hueco=False):
    """Mensaje para un vaciado que el kernel no hizo (o hizo mal) con un espesor que, en principio, entra."""
    return _demasiado_grueso(forma, espesor, hueco) or (
        f"El vaciado falló: el kernel no pudo hacerlo con {abs(espesor):g} mm en esta geometría (¿una pared, un "
        "empalme o el hueco entre un corte y la cara quitada más finos que el espesor?). Probá un espesor menor o "
        "vaciar antes de cortar.")


def _tapa_del_hueco(cavidad, plano, profundidad):
    """Caras de `cavidad` paralelas al plano de una cara quitada y `profundidad` mm por debajo de ella."""
    n = np.asarray(plano.normal, float)
    o = np.asarray(plano.origen, float)
    salida = []
    for cara in geo.caras(cavidad):
        if BRepAdaptor_Surface(cara).GetType() != GeomAbs_Plane:
            continue
        p, normal = _punto_normal(cara)
        if float(np.dot(normal, n)) > 1 - 1e-6 and abs(float(np.dot(np.asarray(p) - o, n)) + profundidad) < 1e-4:
            salida.append(cara)
    return salida


def _cascara_por_desfase(forma, caras, espesor):
    """Plan B de `_cascara` hacia adentro (`espesor` > 0) cuando MakeThickSolid no puede, p. ej. con caras B-spline de una
    solevación (T-04 de la prueba de tortura): se desfasa el cuerpo ENTERO hacia adentro con unión redondeada (la que el
    kernel sostiene en superficies libres), se le suma un prisma que sale por cada cara quitada plana y se resta del
    cuerpo. None si no se pudo (cara quitada no plana, sin tapa en el desfase o resultado imposible)."""
    if not caras or any(_plano_de_cara(c) is None for c in caras):
        return None
    try:
        cavidad = _desfase_cuerpo(forma, -espesor, GeomAbs_Arc)
        herramientas = [cavidad]
        for cara in caras:
            plano = _plano_de_cara(cara)
            tapas = _tapa_del_hueco(cavidad, plano, espesor)
            if not tapas:
                return None
            salida = gp_Vec(*(np.asarray(plano.normal, float) * espesor * 1.5))
            herramientas += [BRepPrimAPI_MakePrism(tapa, salida).Shape() for tapa in tapas]
        resultado = geo.booleano(forma, geo.unir_todos(herramientas), "cortar")
    except Exception:  # noqa: BLE001 — cualquier fallo del plan B deja el error original del kernel, que es el que se informa
        return None
    if geo.volumen_exacto(resultado) >= geo.volumen_exacto(forma) or _resultado_imposible(forma, resultado, -espesor):
        return None
    return resultado


def _borde_con_bisel(forma, caras, espesor):
    """True si alguna cara vecina de las quitadas es una franja más angosta que el espesor: un chaflán o un empalme en
    el borde de la abertura (el kernel no puede desfasarlos hacia adentro y el vaciado falla culpando a otra cosa)."""
    arista_caras = _ancestros(forma, TopAbs_EDGE, TopAbs_FACE)
    for cara in caras:
        for e in _unicos(cara, TopAbs_EDGE):
            e = TopoDS.Edge(e)
            largo = geo.longitud(e)
            for otra in _padres(arista_caras, e):
                if not _contiene(caras, otra) and largo > 1e-9 and geo.area(otra) / largo < abs(espesor):
                    return True
    return False


def _cascara_exterior_por_desfase(forma, caras, espesor):
    """Plan B de `_cascara` hacia afuera (`espesor` > 0) cuando MakeThickSolid no puede con caras B-spline (T-04): se
    desfasa el cuerpo ENTERO hacia afuera con unión redondeada, se le resta el cuerpo (queda la pared cerrada) y se
    corta todo lo que pasa del plano de cada cara quitada. Solo vale si cada cara quitada es plana y extrema (el
    cuerpo entero queda de su lado de adentro). Las caras degeneradas del desfase B-spline se reparan y recosen
    antes del booleano; solo se acepta un sólido cerrado válido que conserve el volumen del desfase.
    None si no se pudo."""
    if not caras or any(_plano_de_cara(c) is None for c in caras):
        return None
    try:
        a, b = geo.caja_envolvente(forma)
        esquinas = [(x, y, z) for x in (a[0], b[0]) for y in (a[1], b[1]) for z in (a[2], b[2])]
        tolerancia = 1e-6 * max(1.0, math.dist(a, b))
        planos = [_plano_de_cara(c) for c in caras]
        if any(max(float((np.asarray(q) - pl.origen) @ pl.normal) for q in esquinas) > tolerancia for pl in planos):
            return None
        exterior = _desfase_cuerpo(forma, espesor, GeomAbs_Arc)
        if not geo.es_valida(exterior):
            volumen = geo.volumen_exacto(exterior)
            costura = BRepBuilderAPI_Sewing(TOL)
            for cara in geo.caras(exterior):
                arreglo = ShapeFix_Face(cara)
                arreglo.Perform()
                costura.Add(arreglo.Face())
            costura.Perform()
            cosida = costura.SewedShape()
            if (cosida.IsNull() or cosida.ShapeType() != TopAbs_SHELL
                    or costura.NbFreeEdges() or costura.NbMultipleEdges()):
                return None
            exterior = BRepBuilderAPI_MakeSolid(TopoDS.Shell(cosida)).Solid()
            if (not geo.es_valida(exterior) or _resultado_imposible(forma, exterior, espesor)
                    or abs(geo.volumen_exacto(exterior) - volumen) > abs(volumen) * 1e-4):
                return None
        pared = geo.booleano(exterior, forma, "cortar")
        semilado = 4.0 * (math.dist(a, b) + espesor)
        sobrante = [BRepPrimAPI_MakePrism(_cara_plana(pl, pl.origen, semilado),
                                          gp_Vec(*(np.asarray(pl.normal, float) * (espesor * 3 + 1.0)))).Shape()
                    for pl in planos]
        resultado = geo.booleano(pared, geo.unir_todos(sobrante), "cortar")
        # La pared es parte del desfase menos el cuerpo: más volumen que eso, o sin sólidos, es una cáscara rota.
        if (not geo.solidos(resultado)
                or geo.volumen_exacto(resultado) > abs(geo.volumen_exacto(exterior)) - geo.volumen_exacto(forma)
                + 1e-6 * abs(geo.volumen_exacto(exterior))):
            return None
    except Exception:  # noqa: BLE001 — cualquier fallo del plan B deja el error original del kernel, que es el que se informa
        return None
    if not geo.es_valida(resultado) or _resultado_imposible(forma, resultado, espesor):
        return None
    return resultado


def _cascara(forma, caras, espesor, union):
    try:
        return _validar(_cascara_del_kernel(forma, caras, espesor, union), "Vaciado")
    except geo.ErrorGeometria as e:
        alternativo = (_cascara_por_desfase(forma, caras, -espesor) if espesor < 0
                       else _cascara_exterior_por_desfase(forma, caras, espesor))
        if alternativo is not None:
            return alternativo
        if espesor > 0 and geo.es_forma_libre(forma):
            raise geo.ErrorGeometria(
                f"El vaciado hacia afuera falló con {espesor:g} mm: el kernel no pudo construir una pared válida "
                "sobre estas caras B-spline. No se modificó el cuerpo. Como alternativa, solevá los perfiles "
                "exteriores e interiores por separado y restalos con boolean_operation(operation='cut').") from e
        if not _demasiado_grueso(forma, espesor) and _borde_con_bisel(forma, caras, espesor):    # «muy grueso» manda
            raise geo.ErrorGeometria(
                f"El vaciado falló: la cara quitada tiene un chaflán o un empalme en su borde más angosto que el "
                f"espesor ({abs(espesor):g} mm) y el kernel no puede desfasarlo. Hacé el chaflán o el empalme "
                "DESPUÉS del vaciado.") from e
        raise


def _cascara_del_kernel(forma, caras, espesor, union):
    ts = BRepOffsetAPI_MakeThickSolid()
    try:
        ts.MakeThickSolidByJoin(forma, _lista_occ(caras), float(espesor), TOL, BRepOffset_Skin, False, False, union)
        ts.Build()
    except Exception as e:  # noqa: BLE001 — p. ej. Standard_NoSuchObject «BRep_Tool:: no parameter on edge»
        raise geo.ErrorGeometria(_demasiado_grueso(forma, espesor) or
                                 "El vaciado falló: el kernel no pudo con ese espesor en esta geometría. Probá otro "
                                 "espesor o vaciar antes de cortar.") from e
    if not ts.IsDone():
        raise geo.ErrorGeometria(_falla_kernel(forma, espesor))
    resultado = ts.Shape()
    if _resultado_imposible(forma, resultado, espesor):
        raise geo.ErrorGeometria(_falla_kernel(forma, espesor))
    # Con cortes que cruzan la cara quitada, MakeThickSolid puede dar IsDone y devolver el cuerpo tal cual o apenas
    # tocado, con la cara todavía puesta. La historia no sirve para verlo: en un vaciado bien hecho también da la
    # cara quitada por «modificada» y no por borrada.
    antes = geo.volumen_exacto(forma)
    if (abs(geo.volumen_exacto(resultado) - antes) <= 1e-9 * abs(antes)
            or any(_cara_sigue_puesta(resultado, c, abs(espesor)) for c in caras)):
        raise geo.ErrorGeometria(_demasiado_grueso(forma, espesor) or
                                 "El vaciado falló: el kernel no pudo quitar esas caras (¿cortes o agujeros que "
                                 "cruzan la cara quitada?). Probá otro espesor o vaciar antes de cortar.")
    return resultado


def _desfase_cuerpo(forma, distancia, union):
    """El cuerpo desfasado `distancia` (negativa = hacia adentro) para un hueco cerrado. Hacia adentro, si el
    espesor no deja cavidad falla antes de llamar al kernel (devolvía el cuerpo sin cambios o un error del corte).
    Hacia adentro, si la unión afilada falla (el kernel es caprichoso con superficies B-spline: con 1 mm sí y con
    1,2 mm no), se reintenta con la redondeada, que ahí es equivalente y más robusta."""
    if distancia < 0 and (mensaje := _demasiado_grueso(forma, distancia, hueco=True)):
        raise geo.ErrorGeometria(mensaje)
    try:
        return _desfase_una_vez(forma, distancia, union)
    except geo.ErrorGeometria:
        if distancia < 0 and union != GeomAbs_Arc:
            return _desfase_una_vez(forma, distancia, GeomAbs_Arc)
        raise


def _desfase_una_vez(forma, distancia, union):
    mo = BRepOffsetAPI_MakeOffsetShape()
    try:
        mo.PerformByJoin(forma, float(distancia), TOL, BRepOffset_Skin, False, False, union)
    except Exception as e:  # noqa: BLE001 — fallos de OCC sin texto útil
        raise geo.ErrorGeometria(_falla_kernel(forma, distancia, hueco=True)) from e
    if not mo.IsDone():
        raise geo.ErrorGeometria(_falla_kernel(forma, distancia, hueco=True))
    desfasado = mo.Shape()
    antes, despues = geo.volumen_exacto(forma), geo.volumen_exacto(desfasado)
    if (_resultado_imposible(forma, desfasado, distancia) or (distancia < 0 and despues >= antes)
            or (distancia > 0 and despues <= antes)):
        raise geo.ErrorGeometria(_falla_kernel(forma, distancia, hueco=True))
    return desfasado


def vaciado(forma, caras_quitar, *, espesor_interior, espesor_exterior=0.0, direccion="interior",
            tangente=True, tipo="afilado"):
    """Vaciado (Shell): quita `caras_quitar` y deja paredes de espesor constante.

    direccion: "interior" | "exterior" | "ambos" (usa espesor_interior / espesor_exterior).
    Sin caras = cuerpo hueco cerrado (cavidad interna, opción Body de Fusion).
    tangente: suma las caras tangentes a las elegidas (Tangent Chain).
    tipo: "afilado" (Sharp Offset) | "redondeado" (Rounded Offset).
    """
    if direccion not in ("interior", "exterior", "ambos"):
        raise geo.ErrorGeometria(f"Dirección de vaciado desconocida: {direccion}")
    union = {"afilado": GeomAbs_Intersection, "redondeado": GeomAbs_Arc}.get(tipo)
    if union is None:
        raise geo.ErrorGeometria(f"Tipo de vaciado desconocido: {tipo}")
    ti = float(espesor_interior) if direccion in ("interior", "ambos") else 0.0
    te = float(espesor_exterior) if direccion in ("exterior", "ambos") else 0.0
    if ti < 0 or te < 0 or (direccion != "exterior" and ti <= 0) or (direccion != "interior" and te <= 0):
        raise geo.ErrorGeometria("Los espesores del vaciado deben ser positivos.")
    caras = []
    for c in caras_quitar or []:
        for t in (caras_tangentes(forma, c) if tangente else [c]):
            if not _contiene(caras, t):
                caras.append(t)
    if caras and len(caras) >= len(geo.caras(forma)):
        raise geo.ErrorGeometria("Quitaste todas las caras: no queda pared que dejar. Elegí menos caras (o ninguna, para "
                                 "un hueco cerrado dentro del cuerpo).")
    if caras:
        partes = []
        if ti:
            partes.append(_cascara(forma, caras, -ti, union))
        if te:
            partes.append(_cascara(forma, caras, te, union))
        resultado = partes[0] if len(partes) == 1 else _unificar(geo.unir_todos(partes))
    else:
        exterior = _desfase_cuerpo(forma, te, union) if te else forma
        interior = _desfase_cuerpo(forma, -ti, union) if ti else forma
        resultado = geo.booleano(exterior, interior, "cortar")
    return _validar(resultado, "Vaciado")


# ---------------------------------------------------------------- desmoldeo
def _inclinacion(cara, direc):
    """Ángulo (grados) que la cara ya tiene respecto de la dirección de extracción: positivo = el cuerpo se angosta hacia
    ella (el sentido del ángulo del desmoldeo). Solo caras planas o cilíndricas con el eje paralelo a la dirección."""
    tipo = BRepAdaptor_Surface(cara).GetType()
    if tipo == GeomAbs_Cylinder:
        a = BRepAdaptor_Surface(cara).Cylinder().Axis().Direction()
        if abs(abs(np.dot([a.X(), a.Y(), a.Z()], direc)) - 1) > 1e-6:
            raise geo.ErrorGeometria("El modo relativo no sabe medir un cilindro inclinado respecto de la dirección de "
                                     "extracción: usá el modo absoluto.")
        return 0.0
    if tipo != GeomAbs_Plane:
        raise geo.ErrorGeometria("El modo relativo solo sirve con caras planas o cilíndricas: usá el modo absoluto.")
    _, n = _punto_normal(cara)
    return math.degrees(math.asin(max(-1.0, min(1.0, float(np.dot(n, direc))))))


def plano_de_particion(arista, direccion):
    """Plano de una línea de partición dada por una curva (Draft › Parting Line): el plano que contiene una curva plana;
    una recta solo define un plano si es perpendicular a la dirección de extracción (el plano pasa por ella)."""
    c = BRepAdaptor_Curve(arista)
    t0, t1 = c.FirstParameter(), c.LastParameter()
    pts = np.array([[p.X(), p.Y(), p.Z()] for p in (c.Value(t0 + (t1 - t0) * i / 24) for i in range(25))])
    centro = pts.mean(axis=0)
    s, vt = np.linalg.svd(pts - centro)[1:]
    if s[0] < 1e-9:
        raise geo.ErrorGeometria("La curva de la línea de partición no tiene largo.")
    if s[2] <= 1e-6 * s[0] and s[1] > 1e-6 * s[0]:
        normal = vt[2]
    elif s[1] <= 1e-6 * s[0]:
        d = np.asarray(direccion, float) / np.linalg.norm(direccion)
        if abs(float(vt[0] @ d)) > 1e-6:
            raise geo.ErrorGeometria("Una arista recta solo sirve de línea de partición si es perpendicular a la "
                                     "dirección de extracción; elegí un plano, una cara o una curva plana.")
        normal = d
    else:
        raise geo.ErrorGeometria("La línea de partición tiene que ser una curva plana: elegí un plano, una cara o una "
                                 "curva que quede en un plano.")
    return geo.Plano.desde_marco(centro, normal, (1.0, 0.0, 0.0))


def desmoldeo(forma, caras, direccion_extraccion, angulo, plano_neutro, *, lados="uno", angulo2=None, modo_angulo="absoluto"):
    """Desmoldeo (Draft, tipo Fixed Plane): inclina las caras `angulo` grados alrededor de su
    intersección con `plano_neutro`. Ángulo positivo = el cuerpo se angosta hacia la dirección de
    extracción (se quita material del lado al que apunta). lados: "uno" | "dos" (angulo2 del otro
    lado) | "simetrico". En "dos"/"simetrico" las caras se parten primero por el plano neutro.
    modo_angulo (Angle Mode): "absoluto" = el ángulo se mide desde la dirección de extracción, haya o no desmoldeo en la
    cara; "relativo" = se suma al que la cara ya tiene."""
    if modo_angulo not in ("absoluto", "relativo"):
        raise geo.ErrorGeometria(f"Modo de ángulo desconocido: {modo_angulo}")
    if lados not in ("uno", "dos", "simetrico"):
        raise geo.ErrorGeometria(f"Opción de lados desconocida: {lados}")
    if not caras:
        raise geo.ErrorGeometria("Elegí las caras a desmoldear.")
    d = np.asarray(direccion_extraccion, float)
    if np.linalg.norm(d) < 1e-12:
        raise geo.ErrorGeometria("La dirección de extracción no puede ser nula.")
    d = d / np.linalg.norm(d)
    a1 = float(angulo)
    a2 = a1 if lados == "simetrico" else (float(angulo2) if angulo2 is not None else None)
    if lados == "dos" and a2 is None:
        raise geo.ErrorGeometria("El desmoldeo de dos lados necesita el segundo ángulo.")
    pln = gp_Pln(gp_Pnt(*map(float, plano_neutro.origen)), gp_Dir(*map(float, plano_neutro.normal)))
    if lados == "uno":
        objetivo, trabajo = forma, [(c, d, a1) for c in caras]
    else:
        objetivo = dividir_cara(forma, caras, plano_neutro)
        piezas = []
        for c in caras:
            for f in geo.caras(objetivo):
                if _cara_dentro_de(f, c) and not _contiene(piezas, f):
                    piezas.append(f)
        trabajo = []
        for f in piezas:
            s = float((np.array(geo.centro_masa(f, True)) - plano_neutro.origen) @ d)
            trabajo.append((f, d, a1) if s >= 0 else (f, -d, a2))
    da = BRepOffsetAPI_DraftAngle(objetivo)
    hechas = 0
    for cara, direc, ang in trabajo:
        if modo_angulo == "relativo":
            ang += _inclinacion(cara, direc)
            if abs(ang) >= 90:
                raise geo.ErrorGeometria("Con el ángulo que ya tiene la cara, el desmoldeo relativo llega a 90 grados o más.")
        if abs(ang) < 1e-12:
            continue
        da.Add(cara, gp_Dir(*direc), math.radians(ang), pln)
        hechas += 1
        if not da.AddDone():
            raise geo.ErrorGeometria("Una cara no admite desmoldeo (solo planas, cilíndricas o cónicas, "
                                     "y no paralelas al plano neutro).")
    if not hechas:
        raise geo.ErrorGeometria("El ángulo de desmoldeo no cambia ninguna cara: no puede ser cero.")
    try:
        da.Build()
    except Exception:  # noqa: BLE001
        pass
    if not da.IsDone():
        raise geo.ErrorGeometria("El desmoldeo falló en el kernel (ángulo demasiado grande?).")
    return _validar(da.Shape(), "Desmoldeo")


def _cara_dentro_de(pieza, cara):
    """¿La pieza (resultado de partir) proviene de `cara`? Misma superficie y su centro sobre la cara."""
    if pieza.IsSame(cara):
        return True
    p, _ = _punto_normal(pieza)
    return geo.se_tocan(BRepBuilderAPI_MakeVertex(gp_Pnt(*p)).Vertex(), cara, 1e-5)


# ---------------------------------------------------------------- escala y transformaciones
def escalar(forma, punto, factor=None, factores=None):
    """Escala (Scale) desde `punto`: uniforme (`factor`) o no uniforme (`factores` = (sx, sy, sz))."""
    if (factor is None) == (factores is None):
        raise geo.ErrorGeometria("Indicá un factor uniforme o tres factores, no ambos.")
    p = np.asarray(punto, float)
    if factor is not None:
        if factor <= 0:
            raise geo.ErrorGeometria("El factor de escala debe ser positivo.")
        t = gp_Trsf()
        t.SetScale(gp_Pnt(*p), float(factor))
        return BRepBuilderAPI_Transform(forma, t, True).Shape()
    s = np.asarray(factores, float)
    if s.shape != (3,) or np.any(s <= 0):
        raise geo.ErrorGeometria("Los tres factores de escala deben ser positivos.")
    m = np.eye(4)
    m[:3, :3] = np.diag(s)
    m[:3, 3] = p - s * p
    return transformar(forma, m)


def matriz_traslacion(v):
    m = np.eye(4)
    m[:3, 3] = np.asarray(v, float)
    return m


def matriz_rotacion(punto, eje, angulo):
    """Rotación de `angulo` grados alrededor del eje (punto, dirección), regla de la mano derecha."""
    k = np.asarray(eje, float)
    if np.linalg.norm(k) < 1e-12:
        raise geo.ErrorGeometria("El eje de rotación no puede ser nulo.")
    k = k / np.linalg.norm(k)
    a = math.radians(float(angulo))
    kx = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    r = np.eye(3) + math.sin(a) * kx + (1 - math.cos(a)) * kx @ kx
    p = np.asarray(punto, float)
    m = np.eye(4)
    m[:3, :3] = r
    m[:3, 3] = p - r @ p
    return m


def matriz_desde_puntos(p_origen, p_destino):
    """Point to Point de Move/Copy: traslación que lleva p_origen a p_destino."""
    return matriz_traslacion(np.asarray(p_destino, float) - np.asarray(p_origen, float))


def transformar(forma, matriz4x4):
    """Move/Copy con una matriz 4x4 (filas: [R | t]). Rígida o con escala uniforme → gp_Trsf (exacto);
    con escala no uniforme o corte → gp_GTrsf (convierte la geometría a B-spline)."""
    m = np.asarray(matriz4x4, float)
    if m.shape != (4, 4) or not np.allclose(m[3], (0, 0, 0, 1)):
        raise geo.ErrorGeometria("La matriz de transformación debe ser 4x4 afín (última fila 0 0 0 1).")
    r, t = m[:3, :3], m[:3, 3]
    det = float(np.linalg.det(r))
    if abs(det) < 1e-12:
        raise geo.ErrorGeometria("La matriz de transformación es singular.")
    s = math.copysign(abs(det) ** (1 / 3), det)       # escala con signo: un espejo es escala −1 · giro
    rot = r / s
    if np.allclose(rot.T @ rot, np.eye(3), atol=1e-9):
        tr = gp_Trsf()
        tr.SetValues(*rot[0], 0.0, *rot[1], 0.0, *rot[2], 0.0)
        if abs(s - 1) > 1e-12:
            esc = gp_Trsf()
            esc.SetScaleFactor(s)
            tr = esc.Multiplied(tr)
        mov = gp_Trsf()
        mov.SetTranslation(gp_Vec(*t))
        return BRepBuilderAPI_Transform(forma, mov.Multiplied(tr), True).Shape()
    gt = gp_GTrsf()
    gt.SetVectorialPart(gp_Mat(*r[0], *r[1], *r[2]))
    gt.SetTranslationPart(gp_XYZ(*t))
    return BRepBuilderAPI_GTransform(forma, gt, True).Shape()


def _rotacion_entre(a, b):
    """Matriz 3x3 de giro mínimo que lleva el vector unitario a sobre b."""
    a, b = a / np.linalg.norm(a), b / np.linalg.norm(b)
    eje = np.cross(a, b)
    s, c = np.linalg.norm(eje), float(a @ b)
    if s < 1e-12:
        if c > 0:
            return np.eye(3)
        perp = np.cross(a, (1.0, 0.0, 0.0) if abs(a[0]) < 0.9 else (0.0, 1.0, 0.0))
        return matriz_rotacion((0, 0, 0), perp, 180.0)[:3, :3]
    return matriz_rotacion((0, 0, 0), eje, math.degrees(math.atan2(s, c)))[:3, :3]


def _datos_alineacion(ref):
    tipo = ref.get("tipo")
    if tipo == "punto":
        return tipo, np.asarray(ref["punto"], float), None
    if tipo == "plano":
        if "plano" in ref:
            return tipo, np.asarray(ref["plano"].origen, float), np.asarray(ref["plano"].normal, float)
        return tipo, np.asarray(ref["origen"], float), np.asarray(ref["normal"], float)
    if tipo == "eje":
        return tipo, np.asarray(ref["punto"], float), np.asarray(ref["direccion"], float)
    raise geo.ErrorGeometria(f"Referencia de alineación desconocida: {tipo}")


def alinear(forma, origen, destino, *, voltear=False):
    """Align: devuelve (forma alineada o None si forma es None, matriz 4x4) que lleva origen sobre destino.

    origen/destino: {"tipo": "punto", "punto"} | {"tipo": "plano", "origen", "normal"} (o "plano": geo.Plano)
    | {"tipo": "eje", "punto", "direccion"}. Plano sobre plano queda ENFRENTADO (normales opuestas, como
    al apoyar una cara contra otra en Fusion); eje sobre eje queda con la misma dirección. `voltear`
    invierte el resultado 180° (Flip). Un punto puede ir a cualquier destino (se usa su punto/origen).
    """
    t_o, p_o, d_o = _datos_alineacion(origen)
    t_d, p_d, d_d = _datos_alineacion(destino)
    r = np.eye(3)
    if t_o != "punto":
        if t_o != t_d:
            raise geo.ErrorGeometria("Solo se alinea plano con plano, eje con eje o un punto con cualquier cosa.")
        objetivo = -d_d if t_o == "plano" else d_d
        r = _rotacion_entre(d_o, -objetivo if voltear else objetivo)
    m = np.eye(4)
    m[:3, :3] = r
    m[:3, 3] = p_d - r @ p_o
    return (transformar(forma, m) if forma is not None else None), m


# ---------------------------------------------------------------- desfase y reemplazo de caras
def _cara_dada_vuelta(mo, forma, caras, resultado, dist):
    """True si el kernel desfasó una cara curva más que su radio y la «dio vuelta» por el eje: la cara nueva no queda
    a `dist` de la original (un cilindro de radio 10 achicado 12 mm salía de radio 2; un agujero de radio 5 llenado
    14,9 mm salía MÁS GRANDE, de radio 9,9) o el volumen cambia al revés de lo pedido (positivo agrega material)."""
    if geo.solidos(forma):          # en una superficie abierta el «volumen» no dice nada
        antes, despues = geo.volumen_exacto(forma), geo.volumen_exacto(resultado)
        if (dist > 0 and despues < antes) or (dist < 0 and despues > antes):
            return True
    for cara in caras:
        for nueva in geo.lista_occ(mo.Generated(cara)):
            medida = BRepExtrema_DistShapeShape(nueva, cara)
            medida.Perform()
            if medida.IsDone() and abs(medida.Value() - abs(dist)) > 1e-3 * abs(dist) + 1e-6:
                return True
    return False


def desfasar_caras(forma, caras, distancia, *, tangente=True):
    """Offset Face / Press Pull sobre caras: mueve las caras a lo largo de su normal (positivo = hacia
    afuera, agrega material) y extiende las vecinas. tangente: arrastra las caras tangentes."""
    if not caras:
        raise geo.ErrorGeometria("Elegí las caras a desfasar.")
    dist = float(distancia)
    if abs(dist) < 1e-9:
        raise geo.ErrorGeometria("La distancia de desfase no puede ser cero.")
    todas = []
    for c in caras:
        for t in (caras_tangentes(forma, c) if tangente else [c]):
            if not _contiene(todas, t):
                todas.append(t)
    resultado = None
    try:
        mo = BRepOffset_MakeOffset()
        mo.Initialize(forma, 0.0, TOL, BRepOffset_Skin, False, False, GeomAbs_Intersection, False, False)
        for c in todas:
            mo.SetOffsetOnFace(c, dist)
        mo.MakeOffsetShape()
        if mo.IsDone() and not mo.Shape().IsNull() and geo.es_valida(mo.Shape()) and not geo.esta_vacia(mo.Shape()):
            resultado = mo.Shape()
            dada_vuelta = _cara_dada_vuelta(mo, forma, todas, resultado, dist)
    except Exception:  # noqa: BLE001 — se intenta la alternativa por extrusión
        resultado = None
    if resultado is not None:
        if dada_vuelta:
            raise geo.ErrorGeometria(f"Desfase de caras: con {abs(dist):g} mm la cara se da vuelta: la distancia es igual "
                                     "o mayor que su radio de curvatura (un cilindro no se achica, ni un agujero se "
                                     "cierra, más que su radio). Probá una distancia menor.")
        return resultado
    planos = [_plano_de_cara(c) for c in todas]
    if any(p is None for p in planos):
        raise geo.ErrorGeometria("El desfase de caras falló en el kernel.")
    return _reemplazar(forma, [(c, p.desplazado(dist)) for c, p in zip(todas, planos, strict=True)],
                       operacion="Desfase de caras")


def _largo_extension(cara, destino, d, diag):
    if isinstance(destino, geo.Plano):
        dn = float(d @ destino.normal)
        if abs(dn) < 1e-9:
            raise geo.ErrorGeometria("El destino es perpendicular a la cara: no se puede extender hasta él.")
        ts = [abs(float((destino.origen - _np(BRep_Tool.Pnt_s(TopoDS.Vertex(v)))) @ destino.normal) / dn)
              for v in _unicos(cara, TopAbs_VERTEX)]
        return max(ts + [0.0]) + diag
    return 2 * (diag + _diagonal(destino))


def _cruce_rayo(punto, direccion, cara):
    """Parámetro (con signo) del cruce más cercano de la recta punto + t·dirección con la cara."""
    inter = BRepIntCurveSurface_Inter()
    inter.Init(cara, gp_Lin(gp_Pnt(*map(float, punto)), gp_Dir(*map(float, direccion))), 1e-7)
    ts = []
    while inter.More():
        ts.append(inter.W())
        inter.Next()
    ts = [t for t in ts if abs(t) > 1e-9]
    return min(ts, key=abs) if ts else None


def _reemplazar(forma, pares, operacion="Reemplazar cara"):
    """Replace Face por extrusión: cada cara origen se extruye a lo largo de su normal hacia afuera
    (lo que queda entre la cara y el destino se SUMA) y hacia adentro (se RESTA). `operacion` nombra el comando en
    los mensajes de error (también lo usa el desfase de caras)."""
    diag = _diagonal(forma)
    sumar, restar = [], []
    coincide = True        # todas las caras ya están sobre su plano destino
    for cara, destino in pares:
        c, d = _punto_normal(cara)
        coincide &= (isinstance(destino, geo.Plano) and abs(float((destino.origen - c) @ destino.normal)) < 1e-7
                     and abs(abs(float(d @ destino.normal)) - 1.0) < 1e-9)
        largo = _largo_extension(cara, destino, d, diag)
        lados = ((1.0, sumar), (-1.0, restar))
        if isinstance(destino, geo.Plano):
            herr = _cara_plana(destino, c, largo + 2 * diag)
        else:
            # un destino curvo puede cortar la normal de los dos lados (p. ej. un tubo que envuelve
            # al cuerpo): manda el cruce más cercano al centro de la cara → extender O recortar.
            herr = destino
            t = _cruce_rayo(c, d, destino)
            if t is None:
                raise geo.ErrorGeometria("El destino no corta la normal de la cara origen.")
            lados = lados[:1] if t > 0 else lados[1:]
        for signo, lista in lados:
            prisma = BRepPrimAPI_MakePrism(cara, gp_Vec(*(d * signo * largo)))
            tapa = prisma.LastShape()
            piezas = geo.solidos(_partir(prisma.Shape(), [herr]))
            if len(piezas) > 1:
                lista.extend(p for p in piezas if not geo.se_tocan(p, tapa, 1e-7))
    if not sumar and not restar:
        if coincide:
            raise geo.ErrorGeometria(f"{operacion}: la cara ya está sobre el plano destino, no hay nada que reemplazar.")
        raise geo.ErrorGeometria("El destino no corta por completo la extensión de las caras elegidas.")
    resultado = geo.unir_todos([forma] + sumar)
    for pieza in restar:
        resultado = geo.booleano(resultado, pieza, "cortar")
    if restar and (geo.esta_vacia(resultado) or not geo.solidos(resultado)):
        raise geo.ErrorGeometria(f"{operacion}: no queda material: la cara entra hasta atravesar todo el cuerpo. "
                                 "Probá una distancia menor.")
    return _validar(_unificar(resultado), operacion)


def reemplazar_cara(forma, caras_origen, destino):
    """Replace Face: quita las caras origen y lleva el cuerpo (extiende o recorta) hasta `destino`
    (geo.Plano o una cara plana o curva). Límite: la extensión es un prisma según la normal de cada
    cara origen; coincide con Fusion cuando las caras vecinas son perpendiculares a la cara origen
    (cuerpos prismáticos). Con vecinas inclinadas Fusion las prolonga y acá quedan "a plomo".
    Con destino curvo cada cara se extiende O se recorta entera (según el cruce más cercano de la
    normal en su centro); con destino plano puede extenderse de un lado y recortarse del otro."""
    if not caras_origen:
        raise geo.ErrorGeometria("Elegí las caras a reemplazar.")
    if isinstance(destino, TopoDS_Shape) and destino.ShapeType() == TopAbs_FACE:
        destino = TopoDS.Face(destino)
        plano = _plano_de_cara(destino)
        if plano is not None:
            destino = plano
        else:
            destino = _cara_extendida(destino, _diagonal(forma))
    elif not isinstance(destino, geo.Plano):
        raise geo.ErrorGeometria("El destino debe ser un plano o una cara.")
    return _reemplazar(forma, [(c, destino) for c in caras_origen])


def mover_caras(forma, caras, matriz):
    """Move/Copy de caras (modelado directo): cada cara PLANA se reemplaza por su plano transformado
    (las vecinas se extienden o recortan). Límite: solo caras planas; mover cilindros/curvas no está."""
    m = np.asarray(matriz, float)
    pares = []
    for c in caras:
        plano = _plano_de_cara(c)
        if plano is None:
            raise geo.ErrorGeometria("Mover caras solo admite caras planas.")
        o = m[:3, :3] @ plano.origen + m[:3, 3]
        n = np.linalg.inv(m[:3, :3]).T @ plano.normal
        pares.append((c, geo.Plano.desde_marco(o, n, m[:3, :3] @ plano.u)))
    try:
        return _reemplazar(forma, pares)
    except geo.ErrorGeometria as e:
        if "no corta" in str(e):
            return forma            # el movimiento deja las caras en su mismo plano
        raise


# ---------------------------------------------------------------- división
def _cortes_proyectados(herramienta, caras, tipo, direccion):
    """Aristas que parten las `caras` cuando la herramienta (aristas o una cara) se PROYECTA sobre ellas:
    "vector" a lo largo de `direccion` (cortes en los dos sentidos, uno por cada vez que cruza una cara) o
    "cercano" llevando cada punto de la herramienta al punto más cercano de la cara."""
    from . import curvas3d
    if isinstance(herramienta, TopoDS_Edge):
        origen = [herramienta]
    elif isinstance(herramienta, (list, tuple)):
        origen = [h for h in herramienta if isinstance(h, TopoDS_Edge)]
    elif isinstance(herramienta, TopoDS_Shape) and herramienta.ShapeType() != TopAbs_EDGE:
        origen = _aristas(herramienta)
    else:
        origen = []
    if not origen:
        raise geo.ErrorGeometria("Este tipo de división necesita curvas de boceto, aristas o una cara como herramienta "
                                 "(un plano no se puede proyectar).")
    if tipo == "vector" and (direccion is None or np.linalg.norm(np.asarray(direccion, float)) < 1e-12):
        raise geo.ErrorGeometria("Elegí la dirección de proyección (un eje, una arista o una cara).")
    cortes = []
    for cara in caras:
        for arista in origen:
            if tipo == "vector":
                cortes.extend(curvas3d.proyectar_vector(arista, cara, direccion, ambos=True))
                continue
            pts = curvas3d.proyectar_cercano(arista, cara)
            for a, b in zip(pts[:-1], pts[1:], strict=True):
                if np.linalg.norm(b - a) > 1e-7:
                    cortes.append(BRepBuilderAPI_MakeEdge(gp_Pnt(*a), gp_Pnt(*b)).Edge())
    return cortes


def dividir_cara(forma, caras, herramienta, *, extender=True, tipo="superficie", direccion=None):
    """Split Face: parte solo las `caras` elegidas con un plano, una cara o aristas.

    `tipo` (Split Type de Fusion): "superficie" (Split with Surface: la sección de la herramienta con cada cara),
    "vector" (Along Vector: la herramienta se proyecta sobre las caras a lo largo de `direccion`) o "cercano"
    (Closest Point: se proyecta al punto más cercano de cada cara).

    Se calcula la sección de la herramienta con cada cara y esas aristas parten la cara
    (BRepAlgoAPI_Splitter con aristas como herramienta: las vecinas no se tocan). Sin `extender`,
    la herramienta tiene que atravesar la cara por completo."""
    if not caras:
        raise geo.ErrorGeometria("Elegí las caras a dividir.")
    if tipo not in ("superficie", "vector", "cercano"):
        raise geo.ErrorGeometria(f"Tipo de división desconocido: {tipo}")
    if tipo == "cercano" and any(_plano_de_cara(c) is None for c in caras):
        raise geo.ErrorGeometria("«Punto más cercano» solo divide caras planas: sobre una cara curva las cuerdas rectas "
                                 "no caen en la superficie. Usá «Con superficie» o «A lo largo de un vector».")
    if tipo != "superficie":
        cortes = _cortes_proyectados(herramienta, caras, tipo, direccion)
    elif isinstance(herramienta, TopoDS_Edge) or (isinstance(herramienta, (list, tuple)) and herramienta
                                                  and all(isinstance(h, TopoDS_Edge) for h in herramienta)):
        cortes = [herramienta] if isinstance(herramienta, TopoDS_Edge) else list(herramienta)
    else:
        herr = _herramienta_corte(herramienta, forma, extender)
        cortes = []
        for c in caras:
            sec = BRepAlgoAPI_Section(c, herr, True)
            if sec.IsDone():
                cortes.extend(_aristas(sec.Shape()))
    if not cortes:
        raise geo.ErrorGeometria("La herramienta no corta las caras elegidas.")
    antes = len(geo.caras(forma))
    resultado = _fusionar_costuras(_partir(forma, cortes))
    if len(geo.caras(resultado)) <= antes:
        raise geo.ErrorGeometria("La herramienta no atraviesa las caras elegidas"
                                 + ("." if extender else " (probá extenderla)."))
    return _validar(resultado, "Dividir cara")


def dividir_cuerpo(forma, herramienta, *, extender=True):
    """Split Body: parte el cuerpo con un plano, una cara (extendida si se pide) o un cuerpo.
    Devuelve los sólidos —o, si el cuerpo es de superficie, sus caras o cascarones (SUP-2)— ordenados por centro."""
    herr = _herramienta_corte(herramienta, forma, extender)
    resultado = _partir(forma, [herr])
    piezas = geo.solidos(resultado)
    if not piezas:                                    # cuerpo de superficie
        piezas = [TopoDS.Shell(s) for s in _unicos(resultado, TopAbs_SHELL)]
        if len(piezas) < 2:
            piezas = geo.caras(resultado)
    if len(piezas) < 2:
        raise geo.ErrorGeometria("La herramienta no divide el cuerpo" + ("." if extender else " (probá extenderla)."))

    def clave(s):
        superficie = not geo.solidos(s)
        c = geo.centro_masa(s, superficie)
        medida = geo.area(s) if superficie else geo.volumen(s)
        return (round(c[0], 6), round(c[1], 6), round(c[2], 6), round(medida, 6))
    return [_validar(s, "Dividir cuerpo") for s in sorted(piezas, key=clave)]


def _herramientas_silueta(cara, d, diag):
    """Herramientas analíticas cuyo corte con la cara es su silueta (n·d = 0)."""
    sup = BRepAdaptor_Surface(cara)
    tipo = sup.GetType()
    if tipo == GeomAbs_Cylinder:
        ax = sup.Cylinder().Axis()
        a, p = _np(ax.Direction()), _np(ax.Location())
        dp = d - a * float(d @ a)
        if np.linalg.norm(dp) < 1e-9:
            return []
        return [_cara_plana(geo.Plano.desde_marco(p, dp, a), p, 2 * diag)]
    if tipo == GeomAbs_Sphere:
        c = _np(sup.Sphere().Location())
        return [_cara_plana(geo.Plano.desde_marco(c, d, (1, 0, 0)), c, 2 * diag)]
    if tipo == GeomAbs_Cone:
        cono = sup.Cone()
        pos = cono.Position()
        x, y, z = _np(pos.XDirection()), _np(pos.YDirection()), _np(pos.Direction())
        alfa, apice = cono.SemiAngle(), _np(cono.Apex())
        dx, dy, dz = float(d @ x), float(d @ y), float(d @ z)
        rho = math.hypot(dx, dy)
        if rho < 1e-12 or abs(math.tan(alfa) * dz / rho) >= 1:
            return []
        phi0, delta = math.atan2(dy, dx), math.acos(math.tan(alfa) * dz / rho)
        g = [math.sin(alfa) * (math.cos(u) * x + math.sin(u) * y) + math.cos(alfa) * z
             for u in (phi0 + delta, phi0 - delta)]
        n = np.cross(g[0], g[1])
        if np.linalg.norm(n) < 1e-12:
            return []
        return [_cara_plana(geo.Plano.desde_marco(apice, n, g[0]), apice, 2 * diag)]
    if tipo == GeomAbs_Torus:
        tor = sup.Torus()
        ax = tor.Position()
        a, c = _np(ax.Direction()), _np(ax.Location())
        dp = d - a * float(d @ a)
        if np.linalg.norm(dp) < 1e-9:
            return [_cara_plana(geo.Plano.desde_marco(c, a, (1, 0, 0)), c, 2 * diag)]
        if abs(float(d @ a)) < 1e-9:
            cil = gp_Cylinder(gp_Ax3(gp_Pnt(*c), gp_Dir(*a)), tor.MajorRadius())
            h = 2 * diag
            return [_cara_plana(geo.Plano.desde_marco(c, d, a), c, 2 * diag),
                    BRepBuilderAPI_MakeFace(cil, 0.0, 2 * math.pi, -h, h).Face()]
    return None


def _silueta_numerica(cara, d, n=40):
    """Silueta n·d = 0 por marching squares en el espacio (u, v) de la cara: aristas B-spline
    sobre la superficie (para toroides oblicuos y superficies libres)."""
    u0, u1, v0, v1 = BRepTools.UVBounds_s(cara)
    us, vs = np.linspace(u0, u1, n + 1), np.linspace(v0, v1, n + 1)

    def g(u, v):
        return float(_normal_en(cara, u, v)[1] @ d)

    G = np.array([[g(u, v) for v in vs] for u in us])

    def cruce(i, j, i2, j2):
        a, b = G[i, j], G[i2, j2]
        pa, pb = np.array([us[i], vs[j]]), np.array([us[i2], vs[j2]])
        for _ in range(3):               # secante sobre el lado de la grilla
            t = a / (a - b) if a != b else 0.5
            pm = pa + (pb - pa) * t
            gm = g(*pm)
            if abs(gm) < 1e-10:
                break
            if (gm > 0) == (a > 0):
                pa, a = pm, gm
            else:
                pb, b = pm, gm
        return pm

    puntos, vecinos = {}, {}
    for i in range(n):
        for j in range(n):
            lados = {("h", i, j): (i, j, i + 1, j), ("h", i, j + 1): (i, j + 1, i + 1, j + 1),
                     ("v", i, j): (i, j, i, j + 1), ("v", i + 1, j): (i + 1, j, i + 1, j + 1)}
            cortados = []
            for k, (a, b, c, e) in lados.items():
                if (G[a, b] > 0) != (G[c, e] > 0):
                    if k not in puntos:
                        puntos[k] = cruce(a, b, c, e)
                    cortados.append(k)
            for k1, k2 in zip(cortados[0::2], cortados[1::2], strict=False):
                vecinos.setdefault(k1, []).append(k2)
                vecinos.setdefault(k2, []).append(k1)
    superficie = BRep_Tool.Surface_s(cara)
    aristas, usados = [], set()
    for inicio in sorted(vecinos, key=lambda k: len(vecinos[k])):
        if inicio in usados:
            continue
        camino, actual = [inicio], inicio
        usados.add(inicio)
        while True:
            sig = [k for k in vecinos[actual] if k not in usados]
            if not sig:
                break
            actual = sig[0]
            usados.add(actual)
            camino.append(actual)
        if len(camino) < 2:
            continue
        arr = Array1_gp_Pnt2d(1, len(camino))
        for i, k in enumerate(camino, 1):
            arr.SetValue(i, gp_Pnt2d(*map(float, puntos[k])))
        curva = Geom2dAPI_PointsToBSpline(arr, 1, 3, GeomAbs_C2, 1e-7).Curve()
        arista = BRepBuilderAPI_MakeEdge(curva, superficie).Edge()
        BRepLib.BuildCurves3d_s(arista)
        aristas.append(arista)
    return aristas


def division_silueta(forma, direccion):
    """Silhouette Split (operación "Split Faces Only"): parte cada cara curva por su silueta vista
    desde `direccion` (lugar donde normal·dirección = 0). Cilindros, conos, esferas y toroides con
    vista axial o perpendicular: exacto (cortes con planos/cilindros). Toroides oblicuos y superficies
    libres: aproximado por marching squares (grilla 40x40 en u, v). Las caras planas no se parten."""
    d = np.asarray(direccion, float)
    if np.linalg.norm(d) < 1e-12:
        raise geo.ErrorGeometria("La dirección de vista no puede ser nula.")
    d = d / np.linalg.norm(d)
    diag = _diagonal(forma)
    resultado, partida = forma, False
    cortes = []
    for cara in geo.caras(forma):                       # 1) superficies analíticas: corte exacto
        if BRepAdaptor_Surface(cara).GetType() == GeomAbs_Plane:
            continue
        for h in _herramientas_silueta(cara, d, diag) or []:
            sec = BRepAlgoAPI_Section(cara, h, True)
            if sec.IsDone():
                cortes.extend(_aristas(sec.Shape()))
    if cortes:
        resultado, partida = _partir(forma, cortes), True
    divisor = BRepFeat_SplitShape(resultado)            # 2) resto: curvas numéricas sobre cada cara
    numericas = False
    for cara in geo.caras(resultado):
        if BRepAdaptor_Surface(cara).GetType() == GeomAbs_Plane or \
                _herramientas_silueta(cara, d, diag) is not None:
            continue
        for e in _silueta_numerica(cara, d):
            divisor.Add(e, cara)
            numericas = True
    if numericas:
        try:
            divisor.Build()
        except Exception:  # noqa: BLE001
            pass
        if not divisor.IsDone():
            raise geo.ErrorGeometria("No se pudo partir una cara libre por su silueta.")
        resultado, partida = divisor.Shape(), True
    if not partida:
        raise geo.ErrorGeometria("El cuerpo no tiene silueta en esa dirección.")
    return _validar(_fusionar_costuras(resultado), "División por silueta")


def _es_hueco(forma):
    """¿El cuerpo está vaciado? (tiene una cavidad cerrada, o es de pared fina: espesor medio 2V/A bajo la cuarta
    parte de su lado menor). shortcut: heurística, no mide el espesor real; mejorar si hace falta."""
    if len(_unicos(forma, TopAbs_SHELL)) > 1:
        return True
    (x0, y0, z0), (x1, y1, z1) = geo.caja_envolvente(forma)
    return 2 * geo.volumen(forma) / geo.area(forma) < 0.25 * min(x1 - x0, y1 - y0, z1 - z0)


def division_silueta_cuerpo(forma, direccion, *, modo="solido"):
    """Silhouette Split con «Split Shelled Body» (modo "vaciado": el cuerpo tiene que estar vaciado) o «Split Solid
    Body» (modo "solido"): parte las caras por la silueta y, si esa línea de partición es plana, corta el cuerpo
    por su plano en dos. Devuelve los sólidos ordenados como `dividir_cuerpo`."""
    from . import curvas3d
    if modo not in ("vaciado", "solido"):
        raise geo.ErrorGeometria(f"Operación de silueta desconocida: {modo}")
    if modo == "vaciado" and not _es_hueco(forma):
        raise geo.ErrorGeometria("«Cuerpo vaciado» necesita un cuerpo vaciado: aplicale Vaciado antes, o usá «Cuerpo sólido».")
    d = np.asarray(direccion, float)
    d = d / np.linalg.norm(d)
    partida = division_silueta(forma, d)
    originales = geo.compuesto(_aristas(forma))
    pts = []
    for e in _aristas(partida):
        medio = curvas3d.muestrear(e, 2).astype(float)[1]
        v = BRepBuilderAPI_MakeVertex(gp_Pnt(*medio)).Vertex()
        if BRepExtrema_DistShapeShape(v, originales).Value() > 1e-5:       # arista nueva, no un trozo de una vieja
            pts.extend(curvas3d.muestrear(e, 8).astype(float))
    if not pts:
        raise geo.ErrorGeometria("El cuerpo no tiene silueta en esa dirección.")
    pts = np.array(pts)
    centro = pts.mean(axis=0)
    _, valores, vt = np.linalg.svd(pts - centro)
    if valores[-1] > 1e-6 * max(1.0, valores[0]):
        raise geo.ErrorGeometria("La línea de partición no es plana: «Cuerpo sólido» y «Cuerpo vaciado» la necesitan "
                                 "plana. Usá «Solo caras».")
    normal = vt[-1]
    u = np.cross(normal, (0.0, 0.0, 1.0) if abs(normal[2]) < 0.9 else (1.0, 0.0, 0.0))
    return dividir_cuerpo(partida, geo.Plano.desde_marco(centro, normal, u / np.linalg.norm(u)))


# ---------------------------------------------------------------- supresión de caras
def quitar_caras(forma, caras):
    """Delete de caras en modelado directo (defeaturing): quita las caras y cierra el hueco
    prolongando las vecinas (agujeros, salientes, empalmes, chaflanes)."""
    if not caras:
        raise geo.ErrorGeometria("Elegí las caras a quitar.")
    df = BRepAlgoAPI_Defeaturing()
    df.SetShape(forma)
    for c in caras:
        df.AddFaceToRemove(c)
    df.SetRunParallel(False)
    df.Build()
    if not df.IsDone():
        raise geo.ErrorGeometria("No se pudieron quitar esas caras: las vecinas no cierran el hueco.")
    # Como Suprimir caras de Fusion: cura el hueco o falla (en Fusion, dejarlo abierto es otro comando, de superficies).
    # Con la tapa de una caja, el defeaturing da IsDone y devuelve el cuerpo tal cual sin borrar nada.
    if not all(df.IsDeleted(c) for c in caras):
        raise geo.ErrorGeometria("No se pueden borrar esas caras: las caras vecinas no alcanzan a cerrar el hueco "
                                 "(por ejemplo, la tapa de una caja).")
    return _validar(df.Shape(), "Quitar caras")


# ---------------------------------------------------------------- PL6: quitar empalmes (defeaturing)
def _aristas_de_cara(cara):
    """Aristas de una cara en el orden en que las recorre el cuerpo (iterator de TopExp a lista)."""
    salida, it = [], TopExp_Explorer(cara, TopAbs_EDGE)
    while it.More():
        salida.append(TopoDS.Edge(it.Current()))
        it.Next()
    return salida


def caras_de_empalme(forma, radio_max):
    """«Remove Fillets» de Plasticity: qué caras del cuerpo son un empalme/redondeo, como las
    marcaría el comando. Criterio: cara CILÍNDRICA de radio <= radio_max que comparte al menos una
    arista RECTA con una cara plana — así entra el redondeo de una arista y queda afuera el agujero
    taladrado (toca al resto por aristas circulares). Devuelve [(cara, radio)], en el orden del cuerpo."""
    from . import referencias as refs
    caras = [TopoDS.Face(f) for f in _unicos(forma, TopAbs_FACE)]
    arista_caras = _ancestros(forma, TopAbs_EDGE, TopAbs_FACE)
    encontradas = []
    for cara in caras:
        f = refs.firma_cara(cara)
        if f.get("geom") != "cilindro" or f.get("radio", float("inf")) > radio_max:
            continue
        for e in _aristas_de_cara(cara):
            if refs.firma_arista(e).get("geom") != "linea":
                continue
            if any(not vecina.IsSame(cara) and refs.firma_cara(TopoDS.Face(vecina)).get("geom") == "plano"
                   for vecina in _padres(arista_caras, e)):
                encontradas.append((cara, f["radio"]))
                break
    return encontradas


def quitar_empalmes(forma, radio_max):
    """«Remove Fillets from Shell» de Plasticity: quita TODOS los empalmes (radio <= radio_max) de
    una vez con defeaturing y une lo que queda (la topología redundante de esquinas: UnifySameDomain).
    Devuelve (forma nueva, [(radio, cuántas caras)]) con los radios que sacó. Falla si no hay
    ninguno con ese filtro."""
    caras = caras_de_empalme(forma, radio_max)
    if not caras:
        raise geo.ErrorGeometria(f"No se encontraron empalmes con radio <= {radio_max:g} mm en el cuerpo.")
    radios = {}
    for _cara, radio in caras:
        radios[radio] = radios.get(radio, 0) + 1
    nueva = quitar_caras(forma, [cara for cara, _r in caras])
    return geo.unificar_caras(nueva), sorted(radios.items())


_motor.registrar(globals(), _iniciar_opencascade)

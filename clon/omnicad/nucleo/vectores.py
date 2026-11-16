# -*- coding: utf-8 -*-
"""
Operaciones vectoriales 2D sobre perfiles de boceto (caras planas de OpenCascade): unir, restar, intersecar y
desfasar (offset). Sirven para limpiar un logo o un texto antes de cortarlo o extruirlo: juntar letras que se
pisan, restar un borde, sacar un contorno de grabado a X mm.

Fusion no las tiene como comandos de boceto (lo más parecido es elegir varios perfiles al extruir, y Desfase
solo con curvas encadenadas de líneas y arcos). Funciones puras: reciben caras OCC y devuelven formas OCC o
primitivas 2D del boceto.
"""
from . import motor as _motor


def _iniciar_opencascade():
    global BRepAdaptor_Curve, BRepAlgoAPI_Common, BRepAlgoAPI_Cut, BRepAlgoAPI_Fuse, BRepOffsetAPI_MakeOffset
    global GeomAbs_Arc, GeomAbs_Circle, GeomAbs_Intersection, GeomAbs_Line, List_TopoDS_Shape
    global ShapeUpgrade_UnifySameDomain, TopAbs_EDGE, TopAbs_WIRE, TopExp_Explorer, TopoDS
    global BRep_Tool, BRepAdaptor_Surface, BRepAlgoAPI_Splitter, BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakeVertex, BRepBuilderAPI_MakeWire
    global BRepExtrema_DistShapeShape, BRepMesh_IncrementalMesh, TopLoc_Location, gp_Pnt
    from OCP.BRep import BRep_Tool
    from OCP.BRepAdaptor import BRepAdaptor_Curve, BRepAdaptor_Surface
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Common, BRepAlgoAPI_Cut, BRepAlgoAPI_Fuse, BRepAlgoAPI_Splitter
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakeVertex, BRepBuilderAPI_MakeWire
    from OCP.BRepExtrema import BRepExtrema_DistShapeShape
    from OCP.BRepMesh import BRepMesh_IncrementalMesh
    from OCP.TopLoc import TopLoc_Location
    from OCP.gp import gp_Pnt
    from OCP.BRepOffsetAPI import BRepOffsetAPI_MakeOffset
    from OCP.GeomAbs import GeomAbs_Arc, GeomAbs_Circle, GeomAbs_Intersection, GeomAbs_Line
    from OCP.OCP.collections import List_TopoDS_Shape
    from OCP.ShapeUpgrade import ShapeUpgrade_UnifySameDomain
    from OCP.TopAbs import TopAbs_EDGE, TopAbs_WIRE
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopoDS import TopoDS


if _motor.motor_activo() == "opencascade":
    _iniciar_opencascade()

import numpy as np

from . import geometria as geo
from .perfiles import _a_uv, arista_a_primitiva

OPERACIONES = ("union", "resta", "interseccion")
ESQUINAS = ("redondas", "vivas")


def _lista(formas):
    lista = List_TopoDS_Shape()
    for f in formas:
        lista.Append(f)
    return lista


def _unificar(forma):
    """Junta las caras que quedaron partidas y borra las aristas internas (el contorno queda limpio)."""
    u = ShapeUpgrade_UnifySameDomain(forma, True, True, True)
    u.Build()
    return u.Shape()


def booleana_caras(caras_a, caras_b=(), operacion="union"):
    """Unir / restar / intersecar regiones planas (todas en el mismo plano). "union": todas las caras de a y b
    juntas; "resta": a menos b; "interseccion": lo común entre a y b. Devuelve la forma con las caras
    resultantes, unificadas. Levanta ErrorGeometria si no queda nada."""
    if operacion not in OPERACIONES:
        raise geo.ErrorGeometria(f"Operación desconocida: {operacion} (union, resta o interseccion).")
    caras_a, caras_b = list(caras_a), list(caras_b)
    if not caras_a:
        raise geo.ErrorGeometria("Hace falta al menos un perfil.")
    if operacion == "union":
        todas = caras_a + caras_b
        if len(todas) == 1:
            return _unificar(todas[0])
        op = BRepAlgoAPI_Fuse()
        op.SetArguments(_lista(todas[:1]))
        op.SetTools(_lista(todas[1:]))
    else:
        if not caras_b:
            raise geo.ErrorGeometria("Restar e intersecar necesitan perfiles herramienta.")
        op = BRepAlgoAPI_Cut() if operacion == "resta" else BRepAlgoAPI_Common()
        op.SetArguments(_lista(caras_a))
        op.SetTools(_lista(caras_b))
    op.SetFuzzyValue(1e-5)
    op.Build()
    if not op.IsDone():
        raise geo.ErrorGeometria("OpenCascade no pudo calcular la operación entre perfiles.")
    forma = _unificar(op.Shape())
    if not geo.caras(forma) or sum(geo.area(c) for c in geo.caras(forma)) < 1e-9:
        raise geo.ErrorGeometria("La operación no deja ninguna región (¿los perfiles no se tocan?).")
    return forma


def desfase_caras(caras, distancia, esquinas="redondas"):
    """Desfase (offset) del contorno de regiones planas: distancia > 0 agranda, < 0 achica (los agujeros se
    mueven al revés, como el material). esquinas: "redondas" (arcos) o "vivas" (se prolongan hasta cortarse).
    Devuelve la lista de formas (alambres) resultantes. Levanta ErrorGeometria si la región desaparece."""
    if esquinas not in ESQUINAS:
        raise geo.ErrorGeometria(f"Esquinas desconocidas: {esquinas} (redondas o vivas).")
    if abs(distancia) < 1e-9:
        raise geo.ErrorGeometria("La distancia del desfase no puede ser cero.")
    union = GeomAbs_Arc if esquinas == "redondas" else GeomAbs_Intersection
    salida = []
    for cara in caras:
        mk = BRepOffsetAPI_MakeOffset(TopoDS.Face(cara), union)
        # B-517: hacia adentro, un lazo con varias curvas libres seguidas (letras, trazados de SVG) cerraba el
        # programa en OpenCascade; pasado a arcos y rectas (±0,15 % de área) da un error. Una spline o elipse sola
        # queda exacta, y hacia afuera no se aproxima (ahí falla donde lo exacto anda).
        # shortcut: el criterio salió de medir letras (d, a, @ cierran; e, o no); si otra figura cierra, ampliarlo.
        if distancia < 0 and any(_curvas_libres(w) > 1 for w in geo._explorar(cara, TopAbs_WIRE)):
            mk.SetApprox(True)
        mk.Perform(float(distancia))
        if not mk.IsDone() or mk.Shape().IsNull() or next(geo._explorar(mk.Shape(), TopAbs_EDGE), None) is None:
            if distancia < 0 and esquinas == "redondas":    # B-503: un trazo que se parte (la cola de la «e», la «@»)
                try:
                    salida.append(booleana_caras([cara], _franjas(cara, -float(distancia)), "resta"))
                    continue
                except geo.ErrorGeometria:          # la región desaparece: el mensaje de siempre
                    pass
            raise geo.ErrorGeometria(f"El desfase de {distancia} mm no se pudo calcular (¿la región desaparece?).")
        salida.append(_sin_cruces(cara, float(distancia), mk.Shape()))
    return salida


def _franjas(cara, r):
    """B-503: las franjas a ≤ r de cada arista de la región (su contorno desfasado, con puntas redondas). Restadas,
    achican la región sin el desfase de OpenCascade, que falla cuando un trazo se parte (la cola de la «e», la «@»)."""
    plano = BRepBuilderAPI_MakeFace(BRepAdaptor_Surface(TopoDS.Face(cara)).Plane()).Face()   # una recta sola no lo define
    franjas = []
    for arista in geo._explorar(cara, TopAbs_EDGE):
        if BRep_Tool.IsClosed_s(TopoDS.Edge(arista)):
            # shortcut: una curva cerrada se desfasa a un solo lado; si una letra o un SVG la trae, armar su anillo
            raise geo.ErrorGeometria(f"El desfase de {-r} mm no se pudo calcular (¿la región desaparece?).")
        mk = BRepOffsetAPI_MakeOffset()
        mk.Init(plano, GeomAbs_Arc, False)
        mk.AddWire(BRepBuilderAPI_MakeWire(TopoDS.Edge(arista)).Wire())
        mk.Perform(r)
        franja = [BRepBuilderAPI_MakeFace(TopoDS.Wire(w), True).Face() for w in geo._explorar(mk.Shape(), TopAbs_WIRE)]
        if not franja or not all(map(geo.es_valida, franja)):
            raise geo.ErrorGeometria(f"El desfase de {-r} mm no se pudo calcular (¿la región desaparece?).")
        franjas += franja
    return franjas


def se_borra_al_achicar(cara, r):
    """True si achicar la región r la borra entera (el palo de la «i» con 0,5 mm): sus franjas la cubren."""
    try:
        franjas = _franjas(cara, r)
    except geo.ErrorGeometria:
        return False
    op = BRepAlgoAPI_Cut()
    op.SetArguments(_lista([cara]))
    op.SetTools(_lista(franjas))
    op.SetFuzzyValue(1e-5)
    op.Build()
    return op.IsDone() and sum(geo.area(c) for c in geo.caras(op.Shape())) < 1e-9


def _sin_cruces(cara, distancia, desfase):
    """B-528: el desfase de OpenCascade de una letra deja lazos que se cruzan a sí mismos (la «@» al engordar, los huecos
    de «e» y «a» al achicarse, con aristas de 1e-5 mm). Si algún lazo no da una cara válida, se parte el plano con las
    curvas desfasadas y quedan las celdas que están donde debe estar el desfase: a lo sumo `distancia` de la región
    (engordar) o adentro y a más de `distancia` de su borde (achicar). Devuelve las caras limpias (o el desfase tal
    cual si ya era válido)."""
    alambres = list(geo._explorar(desfase, TopAbs_WIRE))
    if all(geo.es_valida(BRepBuilderAPI_MakeFace(TopoDS.Wire(w), True).Face()) for w in alambres):
        return desfase
    a, b = geo.caja_envolvente(desfase)
    lado = 2 * max(b[i] - a[i] for i in range(3)) + 1.0
    pln = BRepAdaptor_Surface(TopoDS.Face(cara)).Plane()
    pln.SetLocation(gp_Pnt(*((np.asarray(a) + np.asarray(b)) / 2)))      # centrado en la figura
    plano = BRepBuilderAPI_MakeFace(pln, -lado, lado, -lado, lado).Face()
    partir = BRepAlgoAPI_Splitter()
    partir.SetArguments(_lista([plano]))
    partir.SetTools(_lista([e for w in alambres for e in geo._explorar(w, TopAbs_EDGE)]))
    partir.SetFuzzyValue(1e-5)
    partir.Build()
    borde = geo.compuesto(list(geo._explorar(cara, TopAbs_WIRE)))
    quedan = []
    for celda in geo.caras(partir.Shape()):        # cada celda queda entera adentro o afuera del desfase
        p = _punto_adentro(celda)
        if p is None:                              # una astilla que no se malla: no suma nada
            continue
        fuera = _distancia(p, cara)
        if fuera <= distancia if distancia > 0 else fuera < 1e-9 and _distancia(p, borde) >= -distancia:
            quedan.append(celda)
    if not quedan:
        raise geo.ErrorGeometria(f"El desfase de {distancia} mm no se pudo calcular (¿la región desaparece?).")
    return booleana_caras(quedan, [], "union")


def _punto_adentro(cara):
    """El centro del triángulo más grande de la malla de `cara`: un punto seguro adentro (None si no se malla)."""
    BRepMesh_IncrementalMesh(cara, 0.05, False, 0.3, True)
    loc = TopLoc_Location()
    tri = BRep_Tool.Triangulation_s(TopoDS.Face(cara), loc)
    if tri is None:
        return None
    mejor, punto = -1.0, None
    for k in range(1, tri.NbTriangles() + 1):
        p = [np.array(tri.Node(i).Transformed(loc.Transformation()).Coord()) for i in tri.Triangle(k).Get()]
        area = float(np.linalg.norm(np.cross(p[1] - p[0], p[2] - p[0])))
        if area > mejor:
            mejor, punto = area, gp_Pnt(*map(float, sum(p) / 3))
    return punto


def _distancia(punto, forma):
    d = BRepExtrema_DistShapeShape(BRepBuilderAPI_MakeVertex(punto).Vertex(), forma)
    d.Perform()
    return d.Value()


def _curvas_libres(alambre):
    return sum(BRepAdaptor_Curve(TopoDS.Edge(e)).GetType() not in (GeomAbs_Line, GeomAbs_Circle)
               for e in geo._explorar(alambre, TopAbs_EDGE))


def primitivas_de_formas(formas, plano):
    """Primitivas 2D del boceto ('linea', 'circulo', 'arco', 'spline', id None) de las aristas de las formas,
    sin repetir las compartidas."""
    vistas, salida = set(), []
    a_uv = lambda p: _a_uv(plano, (p.X(), p.Y(), p.Z()))  # noqa: E731
    for forma in formas:
        ex = TopExp_Explorer(forma, TopAbs_EDGE)
        while ex.More():
            arista = TopoDS.Edge(ex.Current())
            ex.Next()
            if hash(arista) in vistas:
                continue
            vistas.add(hash(arista))
            prim = arista_a_primitiva(arista, a_uv, tuple(plano.normal))
            if prim is not None:
                salida.append(prim)
    return salida


_motor.registrar(globals(), _iniciar_opencascade)

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
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Common, BRepAlgoAPI_Cut, BRepAlgoAPI_Fuse
    from OCP.BRepOffsetAPI import BRepOffsetAPI_MakeOffset
    from OCP.GeomAbs import GeomAbs_Arc, GeomAbs_Circle, GeomAbs_Intersection, GeomAbs_Line
    from OCP.OCP.collections import List_TopoDS_Shape
    from OCP.ShapeUpgrade import ShapeUpgrade_UnifySameDomain
    from OCP.TopAbs import TopAbs_EDGE, TopAbs_WIRE
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopoDS import TopoDS


if _motor.motor_activo() == "opencascade":
    _iniciar_opencascade()

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
            raise geo.ErrorGeometria(f"El desfase de {distancia} mm no se pudo calcular (¿la región desaparece?).")
        salida.append(mk.Shape())
    return salida


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

# -*- coding: utf-8 -*-
"""
Herramientas del Boceto 3D («3D Sketch» de Fusion): líneas, arcos, splines, rectángulos, círculos, elipses, puntos,
textos y cónicas fuera del plano de un boceto, con el bloqueo de eje o de plano de la tríada, restricciones y cotas 3D,
mover/rotar/escalar/copiar, y las curvas que dejan Intersection Curve y Project To Surface. La geometría vive en el mismo boceto (create_sketch)
y comparte sus ids; get_sketch la devuelve en entities_3d / points_3d / constraints_3d / dimensions_3d, y sus
curvas sirven de ruta de barrido (sweep path_sketch / path_curves) como las 2D. La lógica está en
`restricciones.boceto3d`; acá solo se valida y se informa.
"""
import math
from typing import Literal

import numpy as np

from ..nucleo import curvas3d
from ..nucleo import geometria as geo
from ..restricciones import boceto3d as b3
from ..restricciones.boceto import MEDIDA_MAXIMA, ErrorBoceto
from ..timeline import entidades as ent
from ..timeline.parametros import ANGULO, LONGITUD, ErrorExpresion, evaluar
from . import selectores as sl
from .errores import error
from .herramientas_boceto import _paso, _r, boceto_resuelto, op_boceto, texto_expr
from .registro import Expr, herramienta

RESTRICCIONES_3D = {"coincident": "coincidente", "axis": "eje", "parallel": "paralela", "perpendicular": "perpendicular",
                    "tangent": "tangente", "equal": "igual", "midpoint": "punto_medio", "fix": "fijo",
                    "concentric": "concentrica", "collinear": "colineal"}
_A_INGLES = {v: k for k, v in RESTRICCIONES_3D.items()}
_TIPO = {"linea": "line", "spline": "spline", "arco": "arc", "circulo": "circle", "elipse": "ellipse",
         "conica": "conic", "texto": "text"}
# Ejes (u, v) de los planos de la tríada; el texto queda derecho (v hacia arriba en yz y zx).
_PLANOS = {"xy": ((1, 0, 0), (0, 1, 0)), "yz": ((0, 1, 0), (0, 0, 1)), "zx": ((1, 0, 0), (0, 0, 1))}


def _punto(v, nombre):
    """[x, y, z] finitos o INVALID_ARGUMENTS; fuera de ±1 km, INVALID_GEOMETRY (como el boceto 2D)."""
    ok = isinstance(v, (list, tuple)) and len(v) == 3 and all(
        isinstance(c, (int, float)) and not isinstance(c, bool) and math.isfinite(c) for c in v)
    if not ok:
        raise error("INVALID_ARGUMENTS", f"'{nombre}' tiene que ser [x, y, z] con tres números finitos (llegó {v!r}).")
    if any(abs(c) > MEDIDA_MAXIMA for c in v):
        raise error("INVALID_GEOMETRY", f"'{nombre}' cae fuera del rango del boceto (hasta 1 km del origen).")
    return [float(c) for c in v]


def _estado(br):
    r = getattr(br, "solver3d", None)
    if r is None:
        return "unknown", None
    if not r.ok:
        return "over_constrained", None
    return ("fully_constrained" if r.gdl == 0 else "under_constrained"), r.gdl


def _editar(sesion, sketch, constructor, kind="INVALID_GEOMETRY"):
    """Aplica `constructor(boceto)` a una copia del boceto (partiendo de la geometría 3D ya resuelta) y la reemplaza
    en el timeline: un paso de deshacer. Devuelve (lo que devolvió el constructor, op nueva, resuelto)."""
    op = op_boceto(sesion, sketch)
    previo = boceto_resuelto(sesion, op)
    nueva = op.copia()
    b = nueva.boceto
    if previo is not None and previo.solver3d is not None and previo.solver3d.ok:
        for pid, xyz in previo.boceto.geo3d.get("puntos", {}).items():
            if pid in b3.datos(b)["puntos"]:
                b.geo3d["puntos"][pid] = list(xyz)
    try:
        salida = constructor(b)
    except ErrorBoceto as e:
        raise error(kind, str(e)) from e
    sesion.doc.reemplazar(op.id, nueva)
    br = boceto_resuelto(sesion, nueva)
    if br is not None and br.solver3d is not None and not br.solver3d.ok and (
            previo is None or previo.solver3d is None or previo.solver3d.ok):
        raise error("SKETCH_OVERCONSTRAINED", f"El cambio deja el boceto 3D «{op.nombre}» en conflicto: "
                    f"{br.solver3d.mensaje}")
    return salida, nueva, br


def _informe(sesion, op, br, **extra):
    estado, gdl = _estado(br)
    return {"sketch": _paso(op), **extra, "status_3d": estado, "dof_3d": gdl}


def _existen(b, ids):
    g = b3.datos(b)
    faltan = [i for i in ids if i not in g["puntos"] and i not in g["curvas"]]
    if faltan:
        raise error("ENTITY_NOT_FOUND", f"El boceto no tiene las entidades 3D {faltan}.",
                    "get_sketch las lista en entities_3d y points_3d.")


def _nuevas(b, antes, tabla):
    return [k for k in b.geo3d.get(tabla, {}) if k not in antes]


# ================================================================ herramientas
@herramienta("draw_line_3d", "boceto",
             "Boceto 3D: dibuja una línea en el espacio (Fusion: 3D Sketch › Línea). Coordenadas del boceto en mm: x, y "
             "sobre su plano y z a lo largo de su normal (en un boceto sobre XY son las del mundo). Bloqueos de la "
             "tríada: axis + length dibuja desde start a lo largo de x, y o z (largo con signo) y deja la restricción "
             "de eje; plane = xy, yz o zx deja el final en el plano por start paralelo a ese (copia la coordenada "
             "normal de start). Un extremo que cae sobre un punto 3D existente lo comparte (cadena).", modifica=True)
def draw_line_3d(sesion, start: list[float], end: list[float] | None = None, sketch: str | None = None,
                 axis: Literal["x", "y", "z"] | None = None, length: float | None = None,
                 plane: Literal["xy", "yz", "zx"] | None = None, construction: bool = False):
    """
    start: punto inicial [x, y, z] en mm (coordenadas del boceto).
    end: punto final [x, y, z]; vacío si se usa axis + length.
    sketch: id o nombre del boceto; vacío = el último boceto del timeline.
    axis: bloqueo de eje de la tríada: la línea va de start a lo largo de x, y o z (necesita length, sin end).
    length: con axis, largo en mm con signo (negativo = sentido contrario del eje).
    plane: bloqueo de plano de la tríada: el final queda en el plano xy, yz o zx que pasa por start.
    construction: true para una línea de construcción (no forma rutas por defecto).
    """
    inicio = _punto(start, "start")
    if axis is not None:
        if end is not None or length is None:
            raise error("INVALID_ARGUMENTS", "Con axis va length (el largo con signo) y no end.")
        if isinstance(length, bool) or not isinstance(length, (int, float)) or not math.isfinite(length):
            raise error("INVALID_ARGUMENTS", f"'length' tiene que ser un número finito (llegó {length!r}).")
        fin = [c + length * e for c, e in zip(inicio, b3.EJES[axis], strict=True)]
    else:
        if end is None:
            raise error("INVALID_ARGUMENTS", "Falta end (o axis + length).")
        if length is not None:
            raise error("INVALID_ARGUMENTS", "length solo vale con axis.")
        fin = _punto(end, "end")
    if plane is not None:
        k = {"xy": 2, "yz": 0, "zx": 1}[plane]
        fin[k] = inicio[k]
    _punto(fin, "end")

    def crear(b):
        antes = set(b3.datos(b)["restricciones"])
        cid = b3.agregar_linea(b, inicio, fin, construction)
        if axis is not None:
            b3.agregar_restriccion(b, "eje", [cid], eje=axis)
        return cid, _nuevas(b, antes, "restricciones")
    (cid, restricciones), op, br = _editar(sesion, sketch, crear)
    return _informe(sesion, op, br, entity=cid, points=op.boceto.geo3d["curvas"][cid]["puntos"],
                    constraints=restricciones)


@herramienta("draw_spline_3d", "boceto",
             "Boceto 3D: spline de ajuste en el espacio que pasa por points (Fusion: 3D Sketch › Spline), en "
             "coordenadas del boceto (x, y sobre el plano, z sobre la normal). Si empieza o termina en el extremo de "
             "una línea 3D comparte el punto, y add_constraint_3d type=tangent la deja tangente a esa línea.",
             modifica=True)
def draw_spline_3d(sesion, points: list[list[float]], sketch: str | None = None, construction: bool = False):
    """
    points: puntos de paso [[x, y, z], …] en mm, al menos dos.
    sketch: id o nombre del boceto; vacío = el último boceto del timeline.
    construction: true para una spline de construcción.
    """
    if not isinstance(points, (list, tuple)):
        raise error("INVALID_ARGUMENTS", "points es una lista de puntos [x, y, z].")
    pts = [_punto(p, f"points[{i}]") for i, p in enumerate(points)]
    cid, op, br = _editar(sesion, sketch, lambda b: b3.agregar_spline(b, pts, construction))
    return _informe(sesion, op, br, entity=cid, points=op.boceto.geo3d["curvas"][cid]["puntos"])


@herramienta("draw_point_3d", "boceto", "Boceto 3D: punto suelto en el espacio (Fusion: 3D Sketch › Punto), en "
             "coordenadas del boceto. Sirve de referencia para restricciones y cotas 3D.", modifica=True)
def draw_point_3d(sesion, x: float, y: float, z: float, sketch: str | None = None):
    """
    x: x en mm (sobre el plano del boceto).
    y: y en mm (sobre el plano del boceto).
    z: z en mm (a lo largo de la normal del boceto).
    sketch: id o nombre del boceto; vacío = el último boceto del timeline.
    """
    p = _punto([x, y, z], "x, y, z")
    pid, op, br = _editar(sesion, sketch, lambda b: b3.agregar_punto(b, p, unir=False))
    return _informe(sesion, op, br, point=pid)


@herramienta("add_constraint_3d", "boceto",
             "Boceto 3D: restricción entre entidades 3D (ids de get_sketch). type: coincident (punto–punto o punto "
             "sobre línea), axis (la Horizontal/Vertical de Fusion en 3D: alinea una línea con el eje axis), parallel, "
             "perpendicular, equal y collinear (dos líneas), tangent (línea o spline + spline que empieza o termina en "
             "un extremo de la otra; entre dos splines deja continuidad G1), midpoint (punto + línea), concentric "
             "(dos arcos, círculos o elipses: mismo centro) y fix (fija los puntos de las entidades). Son las de Fusion "
             "en 3D; las demás (simetría, curvatura, horizontal/vertical del plano) Fusion no las ofrece en 3D.",
             modifica=True)
def add_constraint_3d(sesion, type: Literal["coincident", "axis", "parallel", "perpendicular", "tangent", "equal",
                                            "midpoint", "fix", "concentric", "collinear"],
                      entities: list[int], sketch: str | None = None, axis: Literal["x", "y", "z"] | None = None):
    """
    type: tipo de restricción (ver la descripción).
    entities: ids de las entidades 3D, en cualquier orden.
    sketch: id o nombre del boceto; vacío = el último boceto del timeline.
    axis: con type=axis, el eje con el que se alinea la línea: x, y o z.
    """
    def crear(b):
        _existen(b, entities)
        return b3.agregar_restriccion(b, RESTRICCIONES_3D[type], entities, eje=axis)
    rid, op, br = _editar(sesion, sketch, crear, "INVALID_CONSTRAINT")
    return _informe(sesion, op, br, constraint=rid)


@herramienta("add_dimension_3d", "boceto",
             "Boceto 3D: cota en el espacio. type=distance: el largo de una línea (un id) o la distancia entre dos "
             "puntos 3D, en mm. type=angle: el ángulo entre dos líneas 3D, en grados (0 < ángulo < 180). value: número "
             "o expresión con parámetros (sigue al parámetro al recalcular).", modifica=True)
def add_dimension_3d(sesion, entities: list[int], value: Expr, sketch: str | None = None,
                     type: Literal["distance", "angle"] = "distance"):
    """
    entities: [id de una línea 3D] o [id de punto, id de punto]; con type=angle, [id de línea, id de línea].
    value: medida en mm (o en grados con type=angle): número o expresión con parámetros, p. ej. "largo / 2" o "30 deg".
    sketch: id o nombre del boceto; vacío = el último boceto del timeline.
    type: distance (distancia o largo) o angle (ángulo entre dos líneas).
    """
    expresion = texto_expr(value)
    angulo = type == "angle"
    try:
        medida = evaluar(expresion, ANGULO if angulo else LONGITUD, sesion.doc.parametros.valores())
    except ErrorExpresion as e:
        raise error("INVALID_EXPRESSION", f"value: {e}") from e
    if not (medida > 0 and (not angulo or medida < 180)):
        raise error("INVALID_DIMENSION", f"La cota tiene que medir más que 0{' y menos de 180°' if angulo else ' mm'} "
                    f"(dio {medida:g}).")

    def crear(b):
        _existen(b, entities)
        return b3.agregar_cota(b, entities, expresion, "angulo" if angulo else "distancia")
    kid, op, br = _editar(sesion, sketch, crear, "INVALID_DIMENSION")
    return _informe(sesion, op, br, dimension=kid)


@herramienta("delete_sketch_entities_3d", "boceto",
             "Boceto 3D: borra entidades, restricciones o cotas 3D por id. Con una curva se borran sus restricciones y "
             "cotas y los puntos que ninguna otra curva usa; con un punto, las curvas que pasan por él.", modifica=True)
def delete_sketch_entities_3d(sesion, entities: list[int], sketch: str | None = None):
    """
    entities: ids 3D a borrar (de get_sketch: entities_3d, points_3d, constraints_3d o dimensions_3d).
    sketch: id o nombre del boceto; vacío = el último boceto del timeline.
    """
    borrados, op, br = _editar(sesion, sketch, lambda b: b3.borrar(b, entities), "ENTITY_NOT_FOUND")
    return _informe(sesion, op, br, deleted=borrados)


# ---------------------------------------------------------------- más curvas (3D Sketch › Arco, Círculo, …)
def _numero(v, nombre):
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        raise error("INVALID_ARGUMENTS", f"'{nombre}' tiene que ser un número finito (llegó {v!r}).")
    return float(v)


def _vector(v, nombre):
    """[x, y, z] no nulo o INVALID_ARGUMENTS."""
    p = _punto(v, nombre)
    if math.hypot(*p) < 1e-12:
        raise error("INVALID_ARGUMENTS", f"'{nombre}' no puede ser el vector nulo.")
    return p


def _dibujar(sesion, sketch, constructor, **extra):
    cid, op, br = _editar(sesion, sketch, constructor)
    return _informe(sesion, op, br, entity=cid, points=list(op.boceto.geo3d["curvas"][cid]["puntos"]), **extra)


@herramienta("draw_arc_3d", "boceto", "Boceto 3D: arco de 3 puntos en el espacio (Fusion: 3D Sketch › Arco): va de "
             "start a end pasando por through, en coordenadas del boceto. Sus extremos se encadenan con los puntos 3D "
             "que ya estén ahí.", modifica=True)
def draw_arc_3d(sesion, start: list[float], through: list[float], end: list[float], sketch: str | None = None,
                construction: bool = False):
    """
    start: punto inicial [x, y, z] en mm.
    through: un punto del arco entre start y end [x, y, z].
    end: punto final [x, y, z].
    sketch: id o nombre del boceto; vacío = el último boceto del timeline.
    construction: true para un arco de construcción.
    """
    pts = [_punto(p, n) for p, n in ((start, "start"), (through, "through"), (end, "end"))]
    return _dibujar(sesion, sketch, lambda b: b3.agregar_arco(b, *pts, construction))


@herramienta("draw_circle_3d", "boceto", "Boceto 3D: círculo de centro y radio en el plano perpendicular a normal "
             "(Fusion: 3D Sketch › Círculo; normal = la del plano de la tríada), en coordenadas del boceto.",
             modifica=True)
def draw_circle_3d(sesion, center: list[float], radius: float, normal: list[float] | None = None,
                   sketch: str | None = None, construction: bool = False):
    """
    center: centro [x, y, z] en mm.
    radius: radio en mm (mayor que 0).
    normal: normal del plano del círculo [x, y, z]; vacío = [0, 0, 1] (el plano del boceto).
    sketch: id o nombre del boceto; vacío = el último boceto del timeline.
    construction: true para un círculo de construcción.
    """
    c, r = _punto(center, "center"), _numero(radius, "radius")
    n = _vector(normal if normal is not None else [0, 0, 1], "normal")
    return _dibujar(sesion, sketch, lambda b: b3.agregar_circulo(b, c, r, n, construction))


@herramienta("draw_ellipse_3d", "boceto", "Boceto 3D: elipse de centro, extremo del eje mayor y radio menor en el "
             "plano perpendicular a normal (Fusion: 3D Sketch › Elipse). major_end se proyecta a ese plano.",
             modifica=True)
def draw_ellipse_3d(sesion, center: list[float], major_end: list[float], minor_radius: float,
                    normal: list[float] | None = None, sketch: str | None = None, construction: bool = False):
    """
    center: centro [x, y, z] en mm.
    major_end: extremo del eje mayor [x, y, z] (fija su dirección y el semieje mayor).
    minor_radius: semieje menor en mm (mayor que 0).
    normal: normal del plano de la elipse [x, y, z]; vacío = [0, 0, 1].
    sketch: id o nombre del boceto; vacío = el último boceto del timeline.
    construction: true para una elipse de construcción.
    """
    c, m = np.array(_punto(center, "center")), np.array(_punto(major_end, "major_end"))
    n = np.array(_vector(normal if normal is not None else [0, 0, 1], "normal"))
    n = n / np.linalg.norm(n)
    eje = (m - c) - ((m - c) @ n) * n
    r = _numero(minor_radius, "minor_radius")
    return _dibujar(sesion, sketch, lambda b: b3.agregar_elipse(b, c, eje, r, n, construction))


@herramienta("draw_rectangle_3d", "boceto", "Boceto 3D: rectángulo de 2 puntos (Fusion: 3D Sketch › Rectángulo) en el "
             "plano de la tríada xy, yz o zx que pasa por corner; opposite se proyecta a ese plano. Deja cuatro líneas "
             "encadenadas con perpendicular y paralelas (sigue siendo rectángulo al acotarlo).", modifica=True)
def draw_rectangle_3d(sesion, corner: list[float], opposite: list[float],
                      plane: Literal["xy", "yz", "zx"] = "xy", sketch: str | None = None, construction: bool = False):
    """
    corner: esquina [x, y, z] en mm.
    opposite: esquina opuesta [x, y, z] (se proyecta al plano).
    plane: plano de la tríada por corner: xy, yz o zx.
    sketch: id o nombre del boceto; vacío = el último boceto del timeline.
    construction: true para líneas de construcción.
    """
    a, c = _punto(corner, "corner"), _punto(opposite, "opposite")
    u, v = _PLANOS[plane]
    lineas, op, br = _editar(sesion, sketch, lambda b: b3.agregar_rectangulo(b, a, c, u, v, construction))
    return _informe(sesion, op, br, entities=lineas)


@herramienta("draw_conic_3d", "boceto", "Boceto 3D: curva cónica (Fusion: 3D Sketch › Curva cónica): de start a end, "
             "con shoulder como vértice (cruce de las tangentes de los extremos) y rho (0 < rho < 1: menos de 0,5 "
             "elipse, 0,5 parábola, más hipérbola).", modifica=True)
def draw_conic_3d(sesion, start: list[float], shoulder: list[float], end: list[float], rho: float = 0.5,
                  sketch: str | None = None, construction: bool = False):
    """
    start: extremo inicial [x, y, z] en mm.
    shoulder: vértice de control [x, y, z] (donde se cruzan las tangentes de los extremos).
    end: extremo final [x, y, z].
    rho: forma de la cónica, entre 0 y 1 sin incluirlos.
    sketch: id o nombre del boceto; vacío = el último boceto del timeline.
    construction: true para una cónica de construcción.
    """
    pts = [_punto(p, n) for p, n in ((start, "start"), (shoulder, "shoulder"), (end, "end"))]
    r = _numero(rho, "rho")
    return _dibujar(sesion, sketch, lambda b: b3.agregar_conica(b, *pts, r, construction))


@herramienta("draw_text_3d", "boceto", "Boceto 3D: texto de una línea en el plano de la tríada (Fusion: 3D Sketch › "
             "Texto): la base empieza en origin; en xy corre por x y sube por y, en yz por y y z, en zx por x y z.",
             modifica=True)
def draw_text_3d(sesion, text: str, origin: list[float], height: float = 5.0,
                 plane: Literal["xy", "yz", "zx"] = "xy", font: str = "Arial", sketch: str | None = None):
    """
    text: el texto.
    origin: inicio de la línea base [x, y, z] en mm.
    height: altura del texto en mm (mayor que 0).
    plane: plano de la tríada donde queda el texto: xy, yz o zx.
    font: fuente instalada (list_fonts la lista).
    sketch: id o nombre del boceto; vacío = el último boceto del timeline.
    """
    o, h = _punto(origin, "origin"), _numero(height, "height")
    u, v = _PLANOS[plane]
    return _dibujar(sesion, sketch, lambda b: b3.agregar_texto(b, o, text, h, u, v, font))


def _giro(eje, grados):
    """Matriz de giro (Rodrigues) alrededor de `eje`."""
    k = np.array(eje, float) / np.linalg.norm(eje)
    kx = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    a = math.radians(grados)
    return np.identity(3) + math.sin(a) * kx + (1 - math.cos(a)) * kx @ kx


@herramienta("transform_sketch_3d", "boceto",
             "Boceto 3D: mover, rotar, escalar o copiar entidades 3D (Fusion: Mover/copiar y Escalar sobre el boceto "
             "3D). Cada punto p va a center + scale·R·(p − center) + translation, con R el giro de rotation_angle "
             "grados alrededor de rotation_axis. Con copy deja el original y devuelve las copias. Las restricciones "
             "siguen: si el movimiento las contradice, el paso queda en conflicto (SKETCH_OVERCONSTRAINED).",
             modifica=True)
def transform_sketch_3d(sesion, entities: list[int], translation: list[float] | None = None,
                        rotation_axis: list[float] | None = None, rotation_angle: float = 0.0, scale: float = 1.0,
                        center: list[float] | None = None, copy: bool = False, sketch: str | None = None):
    """
    entities: ids de curvas o puntos 3D.
    translation: desplazamiento [x, y, z] en mm; vacío = sin mover.
    rotation_axis: eje del giro [x, y, z]; vacío = [0, 0, 1].
    rotation_angle: giro en grados alrededor de rotation_axis, por center.
    scale: factor de escala uniforme (mayor que 0), desde center.
    center: centro del giro y de la escala [x, y, z]; vacío = el origen del boceto.
    copy: true copia las entidades (el original queda).
    sketch: id o nombre del boceto; vacío = el último boceto del timeline.
    """
    t = _punto(translation or [0, 0, 0], "translation")
    c = _punto(center or [0, 0, 0], "center")
    eje = _vector(rotation_axis or [0, 0, 1], "rotation_axis")
    if not _numero(scale, "scale") > 0:
        raise error("INVALID_ARGUMENTS", f"scale tiene que ser mayor que 0 (llegó {scale!r}).")
    m = scale * _giro(eje, _numero(rotation_angle, "rotation_angle"))

    def crear(b):
        _existen(b, entities)
        return b3.transformar(b, entities, m, t, c, copy)
    ids, op, br = _editar(sesion, sketch, crear)
    return _informe(sesion, op, br, entities=ids)


# ---------------------------------------------------------------- Intersection Curve / Project To Surface
def _curvas(sesion, op, curves):
    """Referencias de las curvas de boceto elegidas: un id (del boceto activo, 2D o 3D) o {"sketch", "curve"} de
    otro boceto."""
    from .herramientas_construccion import _referencia
    salida = []
    for valor in curves or []:
        if isinstance(valor, int) and not isinstance(valor, bool):
            ref = {"tipo": "curva_boceto", "boceto": op.id, "curva": valor}
        else:
            ref = _referencia(sesion, valor, {"curva_boceto"})
        try:
            ent.resolver(ref, sesion.doc.estado_final)
        except ent.ErrorReferencia as ex:
            raise error("ENTITY_NOT_FOUND", f"Curva {valor!r}: {ex}", "get_sketch lista las curvas del boceto.") from None
        salida.append(ref)
    return salida


def _agregar_curvas(sesion, sketch, origen, construction):
    """Calcula las curvas del «origen» (`aristas_de_origen`, lo mismo que el recálculo) y las agrega al boceto; cada
    una guarda su índice en el resultado para seguir al modelo."""
    from ..timeline.operaciones import aristas_de_origen
    try:
        aristas = aristas_de_origen(origen, sesion.doc.estado_final)
    except geo.ErrorGeometria as e:
        raise error("INVALID_GEOMETRY", str(e)) from e
    if not aristas:
        raise error("INVALID_GEOMETRY", "La selección no deja ninguna curva (no se cortan / no cae sobre la cara).")

    def crear(b):
        plano = boceto_resuelto(sesion, op_boceto(sesion, sketch)).plano
        return [b3.agregar_desde_mundo(b, d, plano, construction, {**origen, "index": i})
                for i, d in enumerate(aristas)]
    ids, op, br = _editar(sesion, sketch, crear)
    return _informe(sesion, op, br, entities=ids)


@herramienta("intersect_curves", "boceto",
             "Boceto 3D: Intersection Curve de Fusion. Con curves: cada curva de boceto se extruye a lo largo de la "
             "normal de su boceto y se corta con las caras, cuerpos o planos elegidos; sin curves: las curvas donde se "
             "cortan entre sí las caras, cuerpos y planos elegidos (al menos dos). El resultado queda como curvas 3D "
             "del boceto (líneas, arcos, círculos y elipses exactos; lo demás, spline por 33 puntos). Si el modelo "
             "cambia, se recalculan (source anota de dónde salió); si la referencia se pierde, quedan congeladas "
             "con aviso.", modifica=True)
def intersect_curves(sesion, faces: list[str] | str | None = None, bodies: list[str] | None = None,
                     references: list[str | dict] | None = None, curves: list[int | dict] | None = None,
                     body: str | None = None, sketch: str | None = None, construction: bool = False):
    """
    faces: caras a cortar: selector ('%CYLINDER') o ids de find_faces.
    bodies: ids o nombres de cuerpos enteros.
    references: planos de construcción o de origen ("XY", id o nombre).
    curves: curvas de boceto a extruir y cortar: id de una curva del boceto activo o {"sketch": …, "curve": id}.
    body: cuerpo donde se evalúan los selectores de faces; vacío = el único cuerpo.
    sketch: id o nombre del boceto 3D donde quedan las curvas; vacío = el último boceto del timeline.
    construction: true deja las curvas como construcción.
    """
    from .herramientas_construccion import _referencia
    refs = [sl.referencia(c, e) for c, e in sl.elegir(sesion, faces, "cara", body, permitir_vacio=True)]
    refs += [{"tipo": "cuerpo", "cuerpo": sesion.cuerpo(r).id} for r in bodies or []]
    for valor in references or []:
        ref = _referencia(sesion, valor, {"plano", "cara"}, body, "plano")
        ent.como_plano(ent.resolver(ref, sesion.doc.estado_final))     # tiene que ser plana
        refs.append(ref if ref["tipo"] == "plano" else {**ref, "infinito": True})
    fuente = _curvas(sesion, op_boceto(sesion, sketch), curves)
    if not refs or (not fuente and len(refs) < 2):
        raise error("INVALID_ARGUMENTS", "Elegí curves y dónde cortarlas (faces, bodies o references), o al menos dos "
                    "caras, cuerpos o planos para cortarlos entre sí.")
    return _agregar_curvas(sesion, sketch, {"tool": "intersection_curve", "refs": refs, "curves": fuente}, construction)


@herramienta("project_to_surface", "boceto",
             "Boceto 3D: Project To Surface de Fusion: proyecta curvas de boceto sobre caras. mode=closest (Closest "
             "Point): cada punto de la curva va al punto más cercano de las caras (spline por 49 puntos); mode=vector "
             "(Along Vector): proyecta a lo largo de direction (vector [x, y, z] del mundo o un eje: 'X', 'Y', 'Z', "
             "id de un eje o una arista recta), hacia donde apunta. El resultado queda como curvas 3D del boceto; si "
             "el modelo cambia, se recalculan (source anota de dónde salió); si la referencia se pierde, quedan "
             "congeladas con aviso.", modifica=True)
def project_to_surface(sesion, faces: list[str] | str, curves: list[int | dict],
                       mode: Literal["closest", "vector"] = "closest", direction: list[float] | str | None = None,
                       body: str | None = None, sketch: str | None = None, construction: bool = False):
    """
    faces: caras donde proyectar: selector ('>Z') o ids de find_faces.
    curves: curvas a proyectar: id de una curva del boceto activo (2D o 3D) o {"sketch": …, "curve": id}.
    mode: closest (punto más cercano) o vector (a lo largo de direction).
    direction: con mode=vector, la dirección: [x, y, z] del mundo o un eje ('X', 'Y', 'Z', id de eje o arista recta).
    body: cuerpo donde se evalúan los selectores de faces; vacío = el único cuerpo.
    sketch: id o nombre del boceto 3D donde quedan las curvas; vacío = el último boceto del timeline.
    construction: true deja las curvas como construcción.
    """
    refs = [sl.referencia(c, e) for c, e in sl.elegir(sesion, faces, "cara", body)]
    fuente = _curvas(sesion, op_boceto(sesion, sketch), curves)
    if not fuente:
        raise error("INVALID_ARGUMENTS", "Elegí qué curvas proyectar (curves).")
    if mode == "vector":
        if direction is None:
            raise error("INVALID_ARGUMENTS", "Con mode=vector va direction ([x, y, z] o un eje).")
        if isinstance(direction, str):
            from .herramientas_construccion import _referencia
            ref = _referencia(sesion, direction, {"eje", "arista", "curva_boceto"}, body, "eje")
            d = ent.como_eje(ent.resolver(ref, sesion.doc.estado_final))[1]
        else:
            d = _vector(direction, "direction")
    origen = {"tool": "project_to_surface", "mode": mode, "refs": refs, "curves": fuente,
              "direction": [float(x) for x in d] if mode == "vector" else None}
    return _agregar_curvas(sesion, sketch, origen, construction)


# ---------------------------------------------------------------- informe (get_sketch)
def info_3d(sesion, b, br):
    """Claves 3D de get_sketch: geometría resuelta (coordenadas del boceto), restricciones, cotas y estado."""
    g = b3.datos(b)
    fijos = b3.puntos_fijos(b)
    xyz = lambda p: [_r(c) for c in g["puntos"][p]]  # noqa: E731
    vec = lambda v: [_r(c) for c in v]  # noqa: E731
    entidades = []
    for cid, c in g["curvas"].items():
        t = c["tipo"]
        e = {"id": cid, "type": _TIPO[t], "construction": c["construccion"], "points": list(c["puntos"])}
        if t == "linea":
            e.update(start=xyz(c["puntos"][0]), end=xyz(c["puntos"][1]),
                     length=_r(math.dist(g["puntos"][c["puntos"][0]], g["puntos"][c["puntos"][1]])))
        else:
            e["length"] = _r(curvas3d.longitud(b3.arista(b, cid, geo.Plano("XY"))))
            if t in ("circulo", "elipse", "texto"):
                e["center" if t != "texto" else "origin"] = xyz(c["puntos"][0])
            else:
                e["vertices"] = [xyz(p) for p in c["puntos"]]
        if t == "arco":
            e.update(center=vec(b3.centro(b, cid)),
                     radius=_r(np.linalg.norm(b3.centro(b, cid) - np.array(g["puntos"][c["puntos"][0]]))))
        elif t == "circulo":
            e.update(radius=_r(c["radio"]), normal=vec(c["normal"]))
        elif t == "elipse":
            e.update(major_axis=vec(c["eje_mayor"]), minor_radius=_r(c["radio_menor"]), normal=vec(c["normal"]))
        elif t == "conica":
            e["rho"] = c["rho"]
        elif t == "texto":
            e.update(text=c["texto"], height=_r(c["altura"]), font=c["fuente"], x_axis=vec(c["u"]), y_axis=vec(c["v"]))
        elif t == "spline" and c.get("cerrada"):
            e["closed"] = True
        if "origen" in c:
            e["source"] = c["origen"]
        entidades.append(e)
    valores = sesion.doc.parametros.valores()

    def valor(expr, tipo):
        try:
            return _r(evaluar(expr, tipo, valores))
        except ErrorExpresion:
            return None
    estado, gdl = _estado(br)
    info = {"entities_3d": entidades,
            "points_3d": [{"id": p, "x": v[0], "y": v[1], "z": v[2], "fixed": p in fijos}
                          for p, v in ((p, xyz(p)) for p in g["puntos"])],
            "constraints_3d": [{"id": k, "type": _A_INGLES[r["tipo"]], "entities": list(r["entidades"]),
                                **({"axis": r["eje"]} if "eje" in r else {})} for k, r in g["restricciones"].items()],
            "dimensions_3d": [{"id": k, "entities": list(d["entidades"]), "expression": d["expresion"],
                               "type": "angle" if d.get("tipo") == "angulo" else "distance",
                               "value": valor(d["expresion"], ANGULO if d.get("tipo") == "angulo" else LONGITUD)}
                              for k, d in g["cotas"].items()],
            "status_3d": estado, "dof_3d": gdl}
    if br is not None and br.solver3d is not None and not br.solver3d.ok:
        info["message_3d"] = br.solver3d.mensaje
    return info

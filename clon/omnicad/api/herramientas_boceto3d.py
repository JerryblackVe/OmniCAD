# -*- coding: utf-8 -*-
"""
Herramientas del Boceto 3D («3D Sketch» de Fusion): líneas, splines y puntos fuera del plano de un boceto, con el
bloqueo de eje o de plano de la tríada, restricciones y cotas 3D. La geometría vive en el mismo boceto (create_sketch)
y comparte sus ids; get_sketch la devuelve en entities_3d / points_3d / constraints_3d / dimensions_3d, y sus
curvas sirven de ruta de barrido (sweep path_sketch / path_curves) como las 2D. La lógica está en
`restricciones.boceto3d`; acá solo se valida y se informa.
"""
import math
from typing import Literal

from ..nucleo import geometria as geo
from ..restricciones import boceto3d as b3
from ..restricciones.boceto import MEDIDA_MAXIMA, ErrorBoceto
from ..timeline.parametros import LONGITUD, ErrorExpresion, evaluar
from .errores import error
from .herramientas_boceto import _paso, _r, boceto_resuelto, op_boceto, texto_expr
from .registro import Expr, herramienta

RESTRICCIONES_3D = {"coincident": "coincidente", "axis": "eje", "parallel": "paralela", "perpendicular": "perpendicular",
                    "tangent": "tangente", "equal": "igual", "midpoint": "punto_medio", "fix": "fijo"}
_A_INGLES = {v: k for k, v in RESTRICCIONES_3D.items()}
_TIPO = {"linea": "line", "spline": "spline"}


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
             "perpendicular y equal (dos líneas), tangent (línea + spline que empieza o termina en un extremo de la "
             "línea), midpoint (punto + línea) y fix (fija los puntos de las entidades).", modifica=True)
def add_constraint_3d(sesion, type: Literal["coincident", "axis", "parallel", "perpendicular", "tangent", "equal",
                                            "midpoint", "fix"],
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
             "Boceto 3D: cota de distancia en el espacio: el largo de una línea (un id) o la distancia entre dos "
             "puntos 3D. value en mm, número o expresión con parámetros (sigue al parámetro al recalcular).",
             modifica=True)
def add_dimension_3d(sesion, entities: list[int], value: Expr, sketch: str | None = None):
    """
    entities: [id de una línea 3D] o [id de punto, id de punto].
    value: medida en mm (número o expresión con parámetros, p. ej. "largo / 2").
    sketch: id o nombre del boceto; vacío = el último boceto del timeline.
    """
    expresion = texto_expr(value)
    try:
        medida = evaluar(expresion, LONGITUD, sesion.doc.parametros.valores())
    except ErrorExpresion as e:
        raise error("INVALID_EXPRESSION", f"value: {e}") from e
    if not medida > 0:
        raise error("INVALID_DIMENSION", f"La cota tiene que medir más que 0 mm (dio {medida:g}).")

    def crear(b):
        _existen(b, entities)
        return b3.agregar_cota(b, entities, expresion)
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


# ---------------------------------------------------------------- informe (get_sketch)
def info_3d(sesion, b, br):
    """Claves 3D de get_sketch: geometría resuelta (coordenadas del boceto), restricciones, cotas y estado."""
    g = b3.datos(b)
    fijos = b3.puntos_fijos(b)
    xyz = lambda p: [_r(c) for c in g["puntos"][p]]  # noqa: E731
    entidades = []
    for cid, c in g["curvas"].items():
        e = {"id": cid, "type": _TIPO[c["tipo"]], "construction": c["construccion"], "points": list(c["puntos"])}
        if c["tipo"] == "linea":
            e.update(start=xyz(c["puntos"][0]), end=xyz(c["puntos"][1]),
                     length=_r(math.dist(g["puntos"][c["puntos"][0]], g["puntos"][c["puntos"][1]])))
        else:
            e.update(vertices=[xyz(p) for p in c["puntos"]],
                     length=_r(geo.longitud(b3.arista(b, cid, geo.Plano("XY")))))
        entidades.append(e)
    valores = sesion.doc.parametros.valores()

    def valor(expr):
        try:
            return _r(evaluar(expr, LONGITUD, valores))
        except ErrorExpresion:
            return None
    estado, gdl = _estado(br)
    info = {"entities_3d": entidades,
            "points_3d": [{"id": p, "x": v[0], "y": v[1], "z": v[2], "fixed": p in fijos}
                          for p, v in ((p, xyz(p)) for p in g["puntos"])],
            "constraints_3d": [{"id": k, "type": _A_INGLES[r["tipo"]], "entities": list(r["entidades"]),
                                **({"axis": r["eje"]} if "eje" in r else {})} for k, r in g["restricciones"].items()],
            "dimensions_3d": [{"id": k, "entities": list(d["entidades"]), "expression": d["expresion"],
                               "value": valor(d["expresion"])} for k, d in g["cotas"].items()],
            "status_3d": estado, "dof_3d": gdl}
    if br is not None and br.solver3d is not None and not br.solver3d.ok:
        info["message_3d"] = br.solver3d.mensaje
    return info

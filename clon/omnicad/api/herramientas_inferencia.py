"""Ayudas de dibujo del boceto para agentes: lo que el cursor propone en `x, y` (el motor de la interfaz, sin Qt)."""
import math

from ..restricciones.boceto import Boceto
from ..restricciones.inferencia import TIPOS_INFERENCIA, inferencias
from .errores import error
from .herramientas_boceto import _RESTRICCION_A_INGLES, _paso, _r, _sincronizar_con_solver, boceto_activo
from .registro import herramienta

_TIPOS = {"midpoint": "medio", "intersection": "interseccion", "tangent": "tangente", "perpendicular": "perpendicular",
          "on_curve": "curva", "alignment": "alineacion", "horizontal": "horizontal", "vertical": "vertical",
          "parallel": "paralela"}
assert set(_TIPOS.values()) == set(TIPOS_INFERENCIA)
_NOMBRE = {"punto_medio": "midpoint", "interseccion": "intersection", "tangente": "tangent",
           "perpendicular": "perpendicular", "sobre_curva": "on_curve", "alineado_h": "aligned_horizontal",
           "alineado_v": "aligned_vertical", "alineado_hv": "aligned_cross", "horizontal": "horizontal",
           "vertical": "vertical", "paralela": "parallel", "colineal": "collinear",
           "perpendicular_dir": "perpendicular_direction"}


def _par(a, b, nombre):
    if (a is None) != (b is None):
        raise error("INVALID_ARGUMENTS", f"{nombre}_x y {nombre}_y van juntos: pasá los dos o ninguno.")
    return None if a is None else (a, b)


def _restriccion(inf):
    """La restricción que dejaría confirmar la ayuda, o None si es solo una guía temporal."""
    if not inf.restriccion:
        return None
    tipo, *resto = inf.restriccion
    salida = {"type": _RESTRICCION_A_INGLES.get(tipo, tipo), "target": resto[0] if resto else None}
    extra = [{"type": _RESTRICCION_A_INGLES.get(t, t), "target": d} for t, d in resto[1:]]
    if extra:
        salida["also"] = extra
    return salida


def _candidata(inf):
    return {"type": _NOMBRE[inf.tipo], "x": _r(inf.xy[0]), "y": _r(inf.xy[1]), "label": inf.etiqueta,
            "priority": inf.clase, "distance": _r(inf.distancia), "constraint": _restriccion(inf),
            "guides": [[_r(a[0]), _r(a[1]), _r(b[0]), _r(b[1])] for a, b in inf.guias]}


@herramienta("infer_sketch_snap", "boceto",
             "Dice qué ayuda de dibujo (inferencia) propone la interfaz con el cursor en (x, y): punto medio, "
             "intersección, tangente, perpendicular, sobre la curva, paralela/perpendicular/colineal a una línea cercana, alineación con otros puntos (misma X o misma Y, "
             "solo guía y sin restricción) y horizontal/vertical desde un punto base. Devuelve las candidatas "
             "ordenadas (la primera es la que se activa; alternative elige otra, como la tecla Espacio) y, para cada "
             "una, el punto ajustado, las guías y la restricción que dejaría al confirmar. No modifica el boceto.")
def infer_sketch_snap(sesion, x: float, y: float, sketch: str | None = None, base_x: float | None = None,
                      base_y: float | None = None, tolerance: float = 0.5, types: list[str] | None = None,
                      exclude: list[int] | None = None, shift: bool = False, alternative: int = 0):
    """
    x: coordenada X del cursor en mm, sobre el plano del boceto.
    y: coordenada Y del cursor en mm, sobre el plano del boceto.
    sketch: id o nombre del boceto; vacío = el último boceto del timeline.
    base_x: X del punto anterior de la línea en curso (para tangente, perpendicular y horizontal/vertical); va con base_y.
    base_y: Y del punto anterior de la línea en curso.
    tolerance: radio de captura en mm (en pantalla son px / escala: con zoom 10 px/mm, 8 px son 0.8 mm).
    types: familias a considerar: midpoint, intersection, tangent, perpendicular, on_curve, alignment, horizontal, vertical, parallel; vacío = todas.
    exclude: ids de puntos o curvas que no cuentan (la geometría que se está dibujando).
    shift: true imita Mayús: el punto medio queda como coincidente en vez de punto medio.
    alternative: 0 = la mejor; 1, 2… recorren las otras en vueltas.
    """
    for nombre, valor in (("x", x), ("y", y), ("tolerance", tolerance)):
        if not math.isfinite(valor):
            raise error("INVALID_ARGUMENTS", f"{nombre} tiene que ser un número finito.")
    if not 0 < tolerance <= 1000:
        raise error("INVALID_ARGUMENTS", "tolerance es un radio en mm: mayor que 0 y hasta 1000.")
    if isinstance(alternative, bool) or not isinstance(alternative, int) or alternative < 0:
        raise error("INVALID_ARGUMENTS", "alternative es un entero desde 0.")
    base = _par(base_x, base_y, "base")
    if base is not None and not all(math.isfinite(v) for v in base):
        raise error("INVALID_ARGUMENTS", "La base tiene que ser finita.")
    elegidas = TIPOS_INFERENCIA
    if types:
        malos = [t for t in types if t not in _TIPOS]
        if malos:
            raise error("INVALID_ARGUMENTS", f"Familias desconocidas {malos}: usá {sorted(_TIPOS)}.")
        elegidas = tuple(_TIPOS[t] for t in types)
    op, _ = boceto_activo(sesion, sketch, derivados=False)
    b: Boceto = op.boceto.copia()
    _sincronizar_con_solver(sesion, op, b)
    lista = inferencias(b, (x, y), tolerance, base=base, excluir=exclude or (), coincidente=shift, tipos=elegidas)
    return {"sketch": _paso(op), "tolerance": tolerance, "count": len(lista),
            "selected": _candidata(lista[alternative % len(lista)]) if lista else None,
            "candidates": [_candidata(i) for i in lista]}

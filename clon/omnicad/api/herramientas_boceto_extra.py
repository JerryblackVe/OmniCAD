"""Espiral y edición de curvas con las operaciones del editor de bocetos."""
import math

from ..restricciones import ErrorBoceto
from ..restricciones.boceto import (
    MEDIDA_MAXIMA, MEDIDA_MINIMA, Arco, Circulo, cambiar_radio, mas_cercano, puntos_espiral,
)
from .errores import error
from .herramientas_boceto import (
    _curva, _dibujar, _exigir_finitos, _exigir_sin_conflicto, _xy, boceto_activo,
)
from .registro import herramienta


@herramienta("draw_spiral", "boceto", "Dibuja la espiral plana del editor como spline cúbica de ajuste abierta. "
             "El radio crece pitch mm por vuelta antihoraria. Hasta 200 puntos de ajuste.", modifica=True)
def draw_spiral(sesion, sketch: str, center: list[float], start: list[float], turns: float,
                pitch: float, construction: bool = False):
    """
    sketch: id o nombre del boceto.
    center: centro [x, y] en mm sobre el plano del boceto.
    start: inicio [x, y] en mm; su distancia al centro es el radio inicial.
    turns: cantidad positiva de vueltas, admite fracciones; hasta 200 puntos (8 tramos por vuelta).
    pitch: incremento de radio por vuelta en mm, admite valores negativos como el editor.
    construction: true para una spline de construcción (no forma perfiles).
    """
    _exigir_finitos(locals())
    centro, inicio = _xy(center, "center"), _xy(start, "start")
    # La interpolación y el solver trabajan con matrices densas: no aceptar listas ilimitadas desde la API.
    if turns > 199 / 8:
        raise error("INVALID_ARGUMENTS", "La espiral admite hasta 200 puntos de ajuste (turns ≤ 24.875).")
    return _dibujar(sesion, sketch, lambda b: b.agregar_spline(
        puntos_espiral(centro, inicio, turns, pitch), "ajuste", 3, False, construccion=construction))


def _editar_curva(sesion, sketch, curve, point, partir):
    punto = _xy(point, "point")
    op, previo = boceto_activo(sesion, sketch, derivados=False)
    partes = []

    def modificar(b):
        c = _curva(b, curve)
        if partir:
            if c.tipo == "texto":
                raise ErrorBoceto("Un texto no se puede partir: desglosalo primero.")
            if mas_cercano(b.primitivas(curve)[0], punto)[1] > 1e-7:
                raise ErrorBoceto("El punto no cae sobre la curva que se quiere partir (tolerancia 1e-7 mm).")
            partes.extend(b.partir(curve, punto))
        else:
            if c.tipo == "linea" and math.dist(*b._extremos_linea(curve)) < 1e-9:
                raise ErrorBoceto("No se puede alargar una línea de longitud cero.")
            b.alargar(curve, punto)

    informe = _dibujar(sesion, op.id, modificar, desde_solver=True)
    _exigir_sin_conflicto(sesion, op, previo.solver.ok, "La edición de la curva")
    if partir:
        informe["pieces"] = partes
    return informe


@herramienta("set_circle_radius", "boceto", "Cambia el radio de un círculo o arco libre, sin cota (lo que hace arrastrarlo "
             "en el editor): el círculo toma el radio nuevo y en un arco se corren sus extremos libres. Si tiene una "
             "cota de radio o diámetro, o las demás restricciones lo impiden, falla (para eso, edit_dimension).",
             modifica=True)
def set_circle_radius(sesion, sketch: str, curve: int, radius: float):
    """
    sketch: id o nombre del boceto.
    curve: id del círculo o arco (get_sketch).
    radius: radio nuevo en mm, entre 0,000001 y 1.000.000 (1 km).
    """
    _exigir_finitos(locals())
    if not MEDIDA_MINIMA <= radius <= MEDIDA_MAXIMA:
        raise error("INVALID_GEOMETRY", f"El radio tiene que medir entre {MEDIDA_MINIMA:g} mm y "
                    f"{MEDIDA_MAXIMA:,.0f} mm (1 km); llegó {radius:g}.".replace(",", "."))
    op, previo = boceto_activo(sesion, sketch, derivados=False)

    def modificar(b):
        c = _curva(b, curve)
        if not isinstance(c, (Circulo, Arco)):
            raise ErrorBoceto(f"La curva {curve} no es un círculo ni un arco.")
        if c.proyectada:
            raise ErrorBoceto("La geometría proyectada no se puede cambiar.")
        if any(k.tipo in ("radio", "diametro") and curve in k.entidades for k in b.cotas.values()):
            raise ErrorBoceto(f"El radio de la curva {curve} tiene una cota: cambiala con edit_dimension.")
        if cambiar_radio(b, curve, radius) is None and isinstance(c, Arco):
            raise ErrorBoceto(f"El arco {curve} tiene sus dos extremos fijos: no se puede cambiar su radio.")

    informe = _dibujar(sesion, op.id, modificar, desde_solver=True)
    _exigir_sin_conflicto(sesion, op, previo.solver.ok, "El nuevo radio")
    return informe


@herramienta("extend_sketch_curve", "boceto", "Alarga una línea o arco hasta la siguiente intersección, "
             "desde el extremo más cercano al punto. Falla si no hay una curva que alcanzar.", modifica=True)
def extend_sketch_curve(sesion, sketch: str, curve: int, point: list[float]):
    """
    sketch: id o nombre del boceto.
    curve: id de la línea o arco (get_sketch).
    point: [x, y] en mm del plano, cerca del extremo que se quiere alargar.
    """
    return _editar_curva(sesion, sketch, curve, point, False)


@herramienta("split_sketch_curve", "boceto", "Parte una curva en las intersecciones más cercanas al punto, "
             "como el editor; el punto debe caer sobre la curva. Devuelve los ids en pieces.", modifica=True)
def split_sketch_curve(sesion, sketch: str, curve: int, point: list[float]):
    """
    sketch: id o nombre del boceto.
    curve: id de la curva (get_sketch); no admite textos ni geometría proyectada.
    point: [x, y] en mm sobre la curva (tolerancia 1e-7 mm); elige las intersecciones donde partir.
    """
    return _editar_curva(sesion, sketch, curve, point, True)

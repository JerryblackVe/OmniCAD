# -*- coding: utf-8 -*-
"""Geometría de referencia, cotas y anotaciones del plano, sin Qt."""
from copy import copy
from math import isfinite
from typing import Literal

import numpy as np

from .errores import error
from .herramientas_dibujo import (
    cargar_dibujo, elemento, guardar_dibujo, info_elemento, punto, vista,
)
from .registro import herramienta


def _solo_vista(d, v):
    """Limita el enganche del modelo a la vista solicitada, incluso si hay superposición."""
    consulta = copy(d)
    seleccionada = copy(v)
    seleccionada.estilo = d.estilo_efectivo(v)
    consulta.vistas = [seleccionada]
    return consulta


def _enganchar(d, p):
    cercano = d.punto_cercano(p, 3.0)
    return cercano[2] if cercano is not None else p


def _circulo(d, p):
    cercano = d.circulo_cercano(p, 3.0)
    if cercano is None:
        raise error("INVALID_ARGUMENTS", "No hay una circunferencia a menos de 3 mm del punto.",
                    "Usá get_drawing_geometry para localizar las circunferencias de la vista.")
    return cercano


def _mm(p):
    """Punto o lista de puntos de la hoja redondeados a 0,0001 mm, como listas."""
    return np.round(np.asarray(p, float), 4).tolist()


def _texto(texto):
    if not texto.strip():
        raise error("INVALID_ARGUMENTS", "El texto no puede estar vacío.")
    return texto


def _guardar(sesion, d, a):
    guardar_dibujo(sesion, d)
    return info_elemento(d, a)


@herramienta("get_drawing_geometry", "dibujo", "Puntos clave, circunferencias y aristas rectas visibles de una vista, en mm de la hoja.")
def get_drawing_geometry(sesion, view: str, limit: int = 200):
    """
    view: id de la vista.
    limit: máximo de puntos, círculos y segmentos por separado; entero no negativo.
    """
    d = cargar_dibujo(sesion)
    v = vista(d, view)
    if limit < 0:
        raise error("INVALID_ARGUMENTS", "limit debe ser un entero no negativo.")
    return {"points": [_mm(ph) for _, _, ph in _solo_vista(d, v).puntos_clave()][:limit],
            "circles": [{"center": _mm(v.a_hoja(c)), "radius": round(r * v.escala, 4), "full": completo}
                        for c, r, completo in v.circulos][:limit],
            "segments": [_mm(v.a_hoja(pl)) for categoria in ("visibles", "silueta")
                         for pl in v.lineas[categoria] if len(pl) == 2][:limit]}


@herramienta("add_drawing_dimension", "dibujo", "Agrega una cota asociada a una vista; puntos y colocación en mm de la hoja.", modifica=True)
def add_drawing_dimension(sesion, view: str,
                          type: Literal["horizontal", "vertical", "aligned", "radius", "diameter", "angle", "ordinate_x", "ordinate_y"],
                          points: list[list[float]], place: list[float], text: str | None = None, snap: bool = True):
    """
    view: id de la vista.
    type: horizontal, vertical, aligned, radius, diameter, angle, ordinate_x u ordinate_y.
    points: dos puntos; radial: uno sobre la circunferencia; angular: dos sobre aristas o cuatro extremos explícitos.
    place: posición de la cota [x, y] en mm de la hoja.
    text: texto propio que reemplaza el valor; vacío restaura el valor medido.
    snap: enganchar puntos a puntos clave de esta vista dentro de 3 mm de hoja.
    """
    d = cargar_dibujo(sesion)
    v = vista(d, view)
    consulta = _solo_vista(d, v)
    tipos = {"horizontal": "horizontal", "vertical": "vertical", "aligned": "alineada", "radius": "radio",
             "diameter": "diametro", "angle": "angulo", "ordinate_x": "ordenada_x", "ordinate_y": "ordenada_y"}
    cantidades = (1,) if type in ("radius", "diameter") else ((2, 4) if type == "angle" else (2,))
    if type not in tipos or len(points) not in cantidades:
        raise error("INVALID_ARGUMENTS", "Tipo de cota o cantidad de puntos incorrectos.")
    puntos = [punto(p, "points") for p in points]
    lugar = punto(place, "place")
    extra = {"texto": text.strip() or None if text is not None else None}
    if type in ("radius", "diameter"):
        _, centro, radio, _ = _circulo(consulta, puntos[0])
        puntos = [v.a_hoja(centro)]
        extra["radio"] = radio * v.escala
    elif type == "angle" and len(puntos) == 2:
        extremos = []
        for p in puntos:
            segmento = consulta.segmento_cercano(p, 3.0)
            if segmento is None:
                raise error("INVALID_ARGUMENTS", "No hay una arista recta a menos de 3 mm del punto.",
                            "Usá get_drawing_geometry para localizar las aristas de la vista.")
            extremos.extend(v.a_hoja(segmento[1:]))
        puntos = extremos
    elif snap:
        puntos = [_enganchar(consulta, p) for p in puntos]
    return _guardar(sesion, d, d.agregar_cota(tipos[type], v.id, puntos, lugar, **extra))


@herramienta("add_drawing_centerline", "dibujo", "Agrega una línea de centro entre puntos enganchados de una vista.", modifica=True)
def add_drawing_centerline(sesion, view: str, start: list[float], end: list[float]):
    """
    view: id de la vista.
    start: primer punto [x, y] en mm de hoja; enganche a 3 mm.
    end: segundo punto [x, y] en mm de hoja; enganche a 3 mm.
    """
    d = cargar_dibujo(sesion)
    v = vista(d, view)
    consulta = _solo_vista(d, v)
    inicio, fin = (_enganchar(consulta, punto(p, nombre)) for p, nombre in ((start, "start"), (end, "end")))
    return _guardar(sesion, d, d.agregar_linea_centro(v.id, inicio, fin))


@herramienta("add_drawing_center_mark", "dibujo", "Agrega una marca de centro en la circunferencia más cercana (3 mm).", modifica=True)
def add_drawing_center_mark(sesion, view: str, point: list[float]):
    """
    view: id de la vista.
    point: punto [x, y] de hoja sobre el borde del círculo o arco.
    """
    d = cargar_dibujo(sesion)
    v = vista(d, view)
    _, centro, radio, _ = _circulo(_solo_vista(d, v), punto(point, "point"))
    return _guardar(sesion, d, d.agregar_marca_centro(v.id, v.a_hoja(centro), radio * v.escala))


@herramienta("add_drawing_text", "dibujo", "Agrega texto libre a la hoja del plano.", modifica=True)
def add_drawing_text(sesion, position: list[float], text: str, height: float = 3.5):
    """
    position: posición [x, y] en mm de hoja.
    text: texto no vacío, admite varias líneas.
    height: altura positiva y finita del texto en mm.
    """
    d = cargar_dibujo(sesion)
    if not isfinite(height) or height <= 0:
        raise error("INVALID_ARGUMENTS", "height debe ser una altura positiva y finita.")
    return _guardar(sesion, d, d.agregar_texto(punto(position, "position"), _texto(text), height))


@herramienta("add_drawing_note", "dibujo", "Agrega una nota con directriz, asociada a la vista bajo la flecha si no se indica otra.", modifica=True)
def add_drawing_note(sesion, arrow: list[float], position: list[float], text: str, view: str | None = None):
    """
    arrow: punto señalado [x, y] en mm de hoja, con enganche a 3 mm.
    position: posición del texto [x, y] en mm de hoja.
    text: texto no vacío de la nota.
    view: id de vista; vacío deduce la vista bajo la flecha.
    """
    d = cargar_dibujo(sesion)
    consulta = _solo_vista(d, vista(d, view)) if view is not None else d
    flecha = _enganchar(consulta, punto(arrow, "arrow"))
    vid = view if view is not None else d.vista_en(flecha)
    return _guardar(sesion, d, d.agregar_nota(flecha, punto(position, "position"), _texto(text), vid))


@herramienta("add_drawing_balloon", "dibujo", "Agrega un globo de pieza con número automático o propio.", modifica=True)
def add_drawing_balloon(sesion, view: str, point: list[float], position: list[float], number: str | None = None):
    """
    view: id de la vista.
    point: punto señalado [x, y] en mm de hoja, con enganche a 3 mm.
    position: posición del globo [x, y] en mm de hoja.
    number: número propio; vacío usa el elemento de la lista de piezas.
    """
    d = cargar_dibujo(sesion)
    v = vista(d, view)
    p = _enganchar(_solo_vista(d, v), punto(point, "point"))
    return _guardar(sesion, d, d.agregar_globo(v.id, p, punto(position, "position"), number))


@herramienta("add_drawing_table", "dibujo", "Agrega la lista de piezas del plano (parts_list de get_drawing). La lista de materiales del MODELO es get_bill_of_materials; esta tabla no la duplica.", modifica=True)
def add_drawing_table(sesion, position: list[float]):
    """
    position: posición [x, y] en mm de hoja de la tabla de piezas del plano.
    """
    d = cargar_dibujo(sesion)
    return _guardar(sesion, d, d.agregar_tabla(punto(position, "position")))


@herramienta("edit_drawing_annotation", "dibujo", "Edita el texto de una cota, nota, texto libre o el número de un globo.", modifica=True)
def edit_drawing_annotation(sesion, annotation: str, text: str):
    """
    annotation: id de la anotación editable.
    text: texto nuevo; en cotas, vacío restaura el valor medido.
    """
    d = cargar_dibujo(sesion)
    a = elemento(d, annotation)
    if not isinstance(a, dict) or a["tipo"] not in ("cota", "nota", "texto", "globo"):
        raise error("INVALID_ARGUMENTS", "El elemento no tiene texto editable.")
    if a["tipo"] == "cota":
        a["texto"] = text.strip() or None
    elif a["tipo"] == "globo":
        a["numero"] = _texto(text).strip()
    else:
        a["texto"] = _texto(text)
    return _guardar(sesion, d, a)


@herramienta("move_drawing_element", "dibujo", "Mueve una vista o anotación y devuelve el desplazamiento real permitido por su alineación.", modifica=True)
def move_drawing_element(sesion, element: str, delta: list[float]):
    """
    element: id de vista o anotación.
    delta: desplazamiento [dx, dy] en mm de hoja.
    """
    d = cargar_dibujo(sesion)
    a = elemento(d, element)
    desplazamiento = d.restringir_movimiento(element, punto(delta, "delta"))
    d.mover(element, desplazamiento)
    resultado = _guardar(sesion, d, a)
    resultado["moved"] = _mm(desplazamiento)
    return resultado


@herramienta("delete_drawing_element", "dibujo", "Borra una anotación o una vista con todas sus hijas y anotaciones asociadas.", modifica=True)
def delete_drawing_element(sesion, element: str):
    """
    element: id de vista o anotación a borrar.
    """
    d = cargar_dibujo(sesion)
    elemento(d, element)
    antes = [v.id for v in d.vistas] + [a["id"] for a in d.anotaciones]
    d.borrar(element)
    despues = {v.id for v in d.vistas} | {a["id"] for a in d.anotaciones}
    guardar_dibujo(sesion, d)
    return {"deleted": [eid for eid in antes if eid not in despues]}

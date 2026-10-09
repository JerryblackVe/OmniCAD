# -*- coding: utf-8 -*-
"""Herramientas del grupo "parametros": parámetros de usuario con expresiones y unidades."""
import difflib

from ..timeline.parametros import ANGULO, ESCALAR, LONGITUD, ErrorExpresion, TablaParametros
from .registro import Expr, herramienta
from .errores import error

_TIPO = {LONGITUD: "length", ANGULO: "angle", ESCALAR: "scalar"}
_UNIDAD = {LONGITUD: "mm", ANGULO: "deg", ESCALAR: ""}


def _copia(tabla):
    return TablaParametros.desde_lista(tabla.a_lista())


def info_parametros(doc):
    valores = doc.parametros.valores()
    usos = doc.parametros_usados()
    return [{"name": p.nombre, "expression": p.expresion, "value": round(valores[p.nombre], 6),
             "unit": _UNIDAD[p.tipo], "kind": _TIPO[p.tipo], "comment": p.comentario,
             "used_by": sorted(usos.get(p.nombre, ()))} for p in doc.parametros]


def _parametro(doc, nombre):
    if nombre not in doc.parametros:
        nombres = [p.nombre for p in doc.parametros]
        parecidos = difflib.get_close_matches(nombre, nombres, n=3)
        raise error("PARAMETER_NOT_FOUND", f"No existe el parámetro '{nombre}'.",
                    f"¿Quisiste decir: {', '.join(parecidos)}?" if parecidos
                    else f"Parámetros existentes: {', '.join(nombres) or '(ninguno)'}.")
    return next(p for p in info_parametros(doc) if p["name"] == nombre)


def _texto(expresion):
    return expresion if isinstance(expresion, str) else repr(float(expresion))


@herramienta("get_parameters", "parametros", "Lista los parámetros de usuario: expresión, valor calculado, "
             "unidad (mm o deg) y qué pasos del timeline los usan.")
def get_parameters(sesion):
    return {"parameters": info_parametros(sesion.doc)}


@herramienta("create_parameter", "parametros", "Crea un parámetro de usuario. La magnitud sale de la expresión: "
             "con unidad de ángulo (deg, rad, °) es un ángulo; si no, una longitud en mm.", modifica=True)
def create_parameter(sesion, name: str, expression: Expr, comment: str = ""):
    """
    name: nombre del parámetro (letras, números y '_', sin empezar con número), p. ej. "ancho".
    expression: valor: número (mm) o expresión con unidades y otros parámetros, p. ej. "60 mm", "ancho / 2", "30 deg".
    comment: comentario opcional que se ve en la tabla de parámetros.
    """
    tabla, texto = _copia(sesion.doc.parametros), _texto(expression)
    try:
        tabla.agregar(name, texto, LONGITUD, comment)
    except ErrorExpresion as e:
        if "es de angulo" not in str(e):
            raise
        tabla.agregar(name, texto, ANGULO, comment)
    sesion.doc.aplicar_parametros(tabla)
    return _parametro(sesion.doc, name)


@herramienta("set_parameter", "parametros", "Cambia la expresión de un parámetro existente y recalcula el modelo. "
             "Si algún paso queda con error, el cambio se descarta.", modifica=True)
def set_parameter(sesion, name: str, expression: Expr):
    """
    name: nombre exacto del parámetro.
    expression: valor nuevo: número (en la unidad del parámetro) o expresión, p. ej. "80 mm" o "ancho * 2".
    """
    anterior = _parametro(sesion.doc, name)["expression"]
    tabla = _copia(sesion.doc.parametros)
    tabla.modificar(name, _texto(expression))
    sesion.doc.aplicar_parametros(tabla)
    return dict(_parametro(sesion.doc, name), previous_expression=anterior)


@herramienta("delete_parameter", "parametros", "Borra un parámetro que no use ningún paso ni otro parámetro.",
             modifica=True)
def delete_parameter(sesion, name: str):
    """
    name: nombre exacto del parámetro.
    """
    _parametro(sesion.doc, name)
    tabla = _copia(sesion.doc.parametros)
    tabla.eliminar(name)
    sesion.doc.aplicar_parametros(tabla)
    return {"name": name, "deleted": True}

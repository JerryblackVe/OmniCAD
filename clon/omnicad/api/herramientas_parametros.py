# -*- coding: utf-8 -*-
"""Herramientas del grupo "parametros": parámetros de usuario con expresiones y unidades."""
import difflib
from typing import Literal

from ..timeline.parametros import (ANGULO, ESCALAR, LONGITUD, LONGITUD_MAXIMA, TEXTO, ErrorExpresion, TablaParametros,
                                   validar_nombre)
from ..timeline.operaciones import OpBoceto
from .registro import _sin_comillas, herramienta
from .errores import error

_TIPO = {LONGITUD: "length", ANGULO: "angle", ESCALAR: "scalar", TEXTO: "text"}
_UNIDAD = {LONGITUD: "mm", ANGULO: "deg", ESCALAR: "", TEXTO: ""}


def _copia(tabla):
    return TablaParametros.desde_lista(tabla.a_lista())


def info_parametros(doc):
    valores = doc.parametros.valores()
    usos = doc.parametros_usados()
    cotas = {c.nombre: {"source": "sketch", "sketch": o.id, "dimension": c.id}
             for o in doc.operaciones if isinstance(o, OpBoceto) for c in o.boceto.cotas.values()}
    return [{"name": p.nombre, "expression": p.expresion,
             "value": valores[p.nombre] if p.tipo == TEXTO else round(valores[p.nombre], 6),
             "unit": _UNIDAD[p.tipo], "kind": _TIPO[p.tipo], "comment": p.comentario,
             "used_by": sorted(usos.get(p.nombre, ())), **cotas.get(p.nombre, {})} for p in doc.parametros]


def _parametro(doc, nombre):
    if nombre not in doc.parametros:
        nombres = [p.nombre for p in doc.parametros]
        parecidos = difflib.get_close_matches(nombre, nombres, n=3)
        raise error("PARAMETER_NOT_FOUND", f"No existe el parámetro '{nombre}'.",
                    f"¿Quisiste decir: {', '.join(parecidos)}?" if parecidos
                    else f"Parámetros existentes: {', '.join(nombres) or '(ninguno)'}.")
    return next(p for p in info_parametros(doc) if p["name"] == nombre)


def _avisar_valor_raro(sesion, info):
    """Una longitud negativa no falla: invierte la dirección de lo que la usa (una caja se extruye hacia −Z). Una de
    más de 1 km tampoco, mientras nada la use: el paso que la use sí falla. En los dos casos se avisa."""
    if info["kind"] == "length" and info["value"] < 0:
        sesion.avisar(f"«{info['name']}» vale {info['value']:g} mm (negativo): lo que la usa puede invertir su "
                      "dirección o fallar.")
    elif info["kind"] == "length" and info["value"] > LONGITUD_MAXIMA:
        sesion.avisar(f"«{info['name']}» vale {info['value']:g} mm, más de 1 km: el paso que la use va a fallar.")
    return info


def _texto(expresion, tipo):
    if tipo == TEXTO:
        if not isinstance(expresion, str):
            raise error("INVALID_ARGUMENTS", "Un parámetro de texto necesita una cadena en expression.")
        return expresion
    return _sin_comillas(expresion) if isinstance(expresion, str) else repr(float(expresion))


@herramienta("get_parameters", "parametros", "Lista los parámetros de usuario y de cotas: expresión, valor calculado, "
             "unidad (mm o deg) y qué pasos del timeline los usan. Las cotas tienen source=sketch, sketch (id del "
             "boceto) y dimension (id de cota); sus nombres d1, d2… se pueden citar en cualquier expresión.")
def get_parameters(sesion):
    return {"parameters": info_parametros(sesion.doc)}


@herramienta("create_parameter", "parametros", "Crea un parámetro de usuario. Con kind=auto la magnitud sale de la "
             "expresión: con unidad de ángulo (deg, rad, °) es un ángulo; si no, una longitud en mm. kind=scalar crea un "
             "parámetro sin unidad (cantidades de un patrón, factores); kind=text guarda texto literal.", modifica=True)
def create_parameter(sesion, name: str, expression: str | int | float, comment: str = "",
                     kind: Literal["auto", "length", "angle", "scalar", "text"] = "auto"):
    """
    name: nombre del parámetro (letras, números y '_', sin empezar con número), p. ej. "ancho".
    expression: valor: número (mm) o expresión con unidades y otros parámetros, p. ej. "60 mm", "ancho / 2", "30 deg"; con kind=text es una cadena literal, incluidas comillas y saltos de línea.
    comment: comentario opcional que se ve en la tabla de parámetros.
    kind: auto (longitud o ángulo según la expresión), length, angle, scalar (número sin unidad) o text (texto literal; no se puede usar en expresiones numéricas).
    """
    tipo = {"angle": ANGULO, "scalar": ESCALAR, "text": TEXTO}.get(kind, LONGITUD)
    tabla, texto = _copia(sesion.doc.parametros), _texto(expression, tipo)
    try:
        tabla.agregar(name, texto, tipo, comment)
    except ErrorExpresion as e:
        if kind != "auto" or "es de angulo" not in str(e):
            raise
        tabla.agregar(name, texto, ANGULO, comment)
    sesion.doc.aplicar_parametros(tabla)
    return _avisar_valor_raro(sesion, _parametro(sesion.doc, name))


@herramienta("set_parameter", "parametros", "Cambia la expresión, el comentario o el nombre de un parámetro existente y "
             "recalcula el modelo. Si algún paso queda con error (p. ej. renombrar un parámetro que usa un paso), el "
             "cambio se descarta. Con un parámetro dN de boceto también cambia la cota y mueve su geometría; "
             "los nombres de cota son estables y no se pueden renombrar. El valor de una cota de referencia "
             "(driven) es medido y no se puede editar; se puede citar en otras expresiones.", modifica=True)
def set_parameter(sesion, name: str, expression: str | int | float | None = None, comment: str | None = None,
                  new_name: str | None = None):
    """
    name: nombre exacto del parámetro.
    expression: valor nuevo: número o expresión, p. ej. "80 mm" o "ancho * 2"; para parámetros text, cadena literal ("" la vacía); null = no cambia.
    comment: comentario nuevo ("" lo borra); vacío = no cambia.
    new_name: nombre nuevo (letras, números y '_'); falla si algún paso u otro parámetro usa el nombre actual, porque quedarían apuntando a un parámetro que ya no existe; vacío = no cambia.
    """
    anterior = _parametro(sesion.doc, name)["expression"]
    if expression is None and comment is None and new_name is None:
        raise error("INVALID_ARGUMENTS", "No pediste ningún cambio: pasá expression, comment o new_name.")
    if expression is not None and any(c.nombre == name and c.referencia
                                      for o in sesion.doc.operaciones if isinstance(o, OpBoceto)
                                      for c in o.boceto.cotas.values()):
        raise error("INVALID_DIMENSION", "Una cota de referencia mide la geometría: su valor no se puede editar.",
                    "Convertí primero la cota a driving con edit_dimension(reference=false).")
    tabla = _copia(sesion.doc.parametros)
    if expression is not None or comment is not None:
        tabla.modificar(name, None if expression is None else _texto(expression, tabla.obtener(name).tipo), comment)
    if new_name is not None and new_name != name:
        validar_nombre(new_name)
        if new_name in tabla:
            raise error("INVALID_ARGUMENTS", f"Ya existe el parámetro '{new_name}'.")
        datos = [dict(p, nombre=new_name) if p["nombre"] == name else p for p in tabla.a_lista()]
        tabla = TablaParametros.desde_lista(datos)
        name = new_name
    sesion.doc.aplicar_parametros(tabla)
    return dict(_avisar_valor_raro(sesion, _parametro(sesion.doc, name)), previous_expression=anterior)


@herramienta("delete_parameter", "parametros", "Borra un parámetro que no use ningún paso ni otro parámetro. "
             "Para quitar un dN de boceto, borrá su cota con delete_sketch_entities; falla si una expresión ajena la usa.",
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

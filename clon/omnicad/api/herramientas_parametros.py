# -*- coding: utf-8 -*-
"""Herramientas del grupo "parametros": parámetros de usuario con expresiones y unidades."""
import difflib
import re
from typing import Literal

from ..timeline.parametros import (ANGULO, ESCALAR, LONGITUD, LONGITUD_MAXIMA, MAGNITUD, TEXTO, ErrorExpresion,
                                   TablaParametros, texto_resuelto, tipo_de_unidad, unidad_de)
from ..timeline.operaciones import OpBoceto
from ..timeline.unidades import FAMILIAS
from .registro import _sin_comillas, herramienta
from .errores import error

_TIPO = {LONGITUD: "length", ANGULO: "angle", ESCALAR: "scalar", TEXTO: "text", MAGNITUD: "other"}


def _copia(tabla):
    return TablaParametros.desde_lista(tabla.a_lista())


def valor_visible(p, valores):
    """El valor de `p` en su propia unidad; None si el paso del que sale no se puede calcular."""
    if p.tipo == TEXTO:
        return texto_resuelto(p.expresion, valores)
    v = valores.get(p.nombre)
    return v if v is None else round(unidad_de(p.tipo, p.unidad).desde_interno(v), 6)


def info_parametros(doc, tabla=None):
    tabla = doc.parametros if tabla is None else tabla
    valores = tabla.valores()
    usos = doc.parametros_usados()
    cotas = {c.nombre: {"source": "sketch", "sketch": o.id, "dimension": c.id}
             for o in doc.operaciones if isinstance(o, OpBoceto) for c in o.boceto.cotas.values()}
    return [{"name": p.nombre, "expression": p.expresion, "value": valor_visible(p, valores),
             "unit": "" if p.tipo == TEXTO else p.texto_unidad, "kind": _TIPO[p.tipo], "comment": p.comentario,
             "used_by": sorted(usos.get(p.nombre, ())), **cotas.get(p.nombre, {}),
             **({"source": "feature", "feature": p.op, "role": p.clave} if p.op else {}),
             **({"favorite": True} if p.favorito else {})} for p in tabla]


def _natural(texto):
    """Clave de orden por letras y número: «d2» va antes de «d10» (`Parameters in Fusion` § Sort parameters)."""
    return [(0, int(t), "") if t.isdigit() else (1, 0, t.casefold()) for t in re.split(r"(\d+)", str(texto)) if t]


_CLAVES_ORDEN = {"name": lambda f: f["name"].casefold(), "unit": lambda f: f["unit"].casefold(),
                 "expression": lambda f: _natural(f["expression"]), "comment": lambda f: _natural(f["comment"]),
                 "value": lambda f: (not isinstance(f["value"], (int, float)), f["value"] if isinstance(f["value"], (int, float)) else 0)}


def filtrar_y_ordenar(filas, favorites_only=False, user_only=False, search="", sort_by="timeline", descending=False):
    """La barra superior de la tabla de parámetros (PAR-6); la ventana y `get_parameters` usan esta misma."""
    busca = search.casefold()
    salida = [f for f in filas if (not favorites_only or f.get("favorite")) and (not user_only or "source" not in f)
              and (not busca or busca in " ".join(str(f[k]) for k in ("name", "expression", "comment")).casefold())]
    return salida if sort_by == "timeline" else sorted(salida, key=_CLAVES_ORDEN[sort_by], reverse=descending)


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
    if info["kind"] != "length" or info["value"] is None:
        return info
    mm = unidad_de(LONGITUD, info["unit"]).a_interno(info["value"])
    if mm < 0:
        sesion.avisar(f"«{info['name']}» vale {mm:g} mm (negativo): lo que la usa puede invertir su "
                      "dirección o fallar.")
    elif mm > LONGITUD_MAXIMA:
        sesion.avisar(f"«{info['name']}» vale {mm:g} mm, más de 1 km: el paso que la use va a fallar.")
    return info


def _texto(expresion, tipo):
    if tipo == TEXTO:
        if not isinstance(expresion, str):
            raise error("INVALID_ARGUMENTS", "Un parámetro de texto necesita una cadena en expression.")
        return expresion
    return _sin_comillas(expresion) if isinstance(expresion, str) else repr(float(expresion))


@herramienta("get_parameters", "parametros", "Lista los parámetros de usuario y del modelo: expresión, valor calculado "
             "en su unidad, unidad y qué pasos del timeline los usan. Las cotas tienen source=sketch, sketch (id del "
             "boceto) y dimension (id de cota); los valores de un paso, source=feature, feature (id del paso) y role (qué "
             "valor es). Sus nombres d1, d2… se pueden citar en cualquier expresión. Los filtros son los de la tabla.")
def get_parameters(sesion, favorites_only: bool = False, user_only: bool = False, search: str = "",
                   sort_by: Literal["timeline", "name", "unit", "expression", "value", "comment"] = "timeline",
                   descending: bool = False):
    """
    favorites_only: true deja solo los favoritos.
    user_only: true deja solo los parámetros de usuario (sin cotas ni valores de pasos).
    search: texto a buscar en nombre, expresión y comentario, sin distinguir mayúsculas; vacío = todos.
    sort_by: timeline (orden de creación), name y unit por letras, expression y comment por letras y número, value por número.
    descending: true invierte el orden elegido en sort_by.
    """
    return {"parameters": filtrar_y_ordenar(info_parametros(sesion.doc), favorites_only, user_only, search, sort_by,
                                            descending)}


@herramienta("get_parameter_units", "parametros", "Lista las familias de unidades de Fusion que acepta la columna Unidad "
             "(abreviaturas por familia), además de sin unidad (\"\") y text. También valen combinaciones: mm^2, cm/s^2.")
def get_parameter_units(sesion):
    return {"families": {familia: list(unidades) for familia, (_, unidades) in FAMILIAS.items()}}


@herramienta("create_parameter", "parametros", "Crea un parámetro de usuario. Con kind=auto la magnitud sale de la "
             "expresión: con unidad de ángulo (deg, rad, °) es un ángulo; si no, una longitud en mm. kind=scalar crea un "
             "parámetro sin unidad (cantidades de un patrón, factores); kind=text guarda texto literal, y lo que va "
             "entre {llaves} se calcula. Con unit, cualquier unidad: la expresión tiene que dar esa magnitud y un número "
             "suelto la toma (unit=\"in\", expression=\"2\" son 2 pulgadas).", modifica=True)
def create_parameter(sesion, name: str, expression: str | int | float, comment: str = "",
                     kind: Literal["auto", "length", "angle", "scalar", "text"] = "auto", unit: str | None = None,
                     favorite: bool = False):
    """
    name: nombre del parámetro (letras, números, '_', '$', '"', '°' y 'µ', sin empezar con número), p. ej. "ancho".
    expression: valor: número o expresión con unidades y otros parámetros, p. ej. "60 mm", "ancho / 2", "30 deg", "if(ancho > 50 mm; 2; 3)"; con kind=text es texto, incluidas comillas y saltos de línea.
    comment: comentario opcional que se ve en la tabla de parámetros.
    kind: auto (longitud o ángulo según la expresión), length, angle, scalar (número sin unidad) o text (no se puede usar en expresiones numéricas). Con unit no hace falta.
    unit: unidad del parámetro, p. ej. "in", "kg", "mm^2", "text"; vacío = la que diga kind.
    favorite: true lo marca como favorito.
    """
    tipo = tipo_de_unidad(unit) if unit else {"angle": ANGULO, "scalar": ESCALAR, "text": TEXTO}.get(kind, LONGITUD)
    tabla, texto = _copia(sesion.doc.parametros), _texto(expression, tipo)
    unidad = unit if unit and tipo != TEXTO else None
    try:
        tabla.agregar(name, texto, tipo, comment, unidad, favorite)
    except ErrorExpresion as e:
        if kind != "auto" or unit or "es de ángulo" not in str(e):
            raise
        tabla.agregar(name, texto, ANGULO, comment, None, favorite)
    sesion.doc.aplicar_parametros(tabla)
    return _avisar_valor_raro(sesion, _parametro(sesion.doc, name))


@herramienta("set_parameter", "parametros", "Cambia la expresión, el comentario, la unidad, el favorito o el nombre de un "
             "parámetro existente y recalcula el modelo. Renombrar actualiza los parámetros, pasos, cotas y textos que lo "
             "citan. Si algún paso queda con error, el cambio se descarta. Con un parámetro dN también cambia la cota o el "
             "paso del que sale. El valor de una cota de referencia (driven) es medido y no se puede editar; se puede "
             "citar en otras expresiones.", modifica=True)
def set_parameter(sesion, name: str, expression: str | int | float | None = None, comment: str | None = None,
                  new_name: str | None = None, unit: str | None = None, favorite: bool | None = None):
    """
    name: nombre exacto del parámetro.
    expression: valor nuevo: número o expresión, p. ej. "80 mm" o "ancho * 2"; para parámetros text, texto literal ("" lo vacía); null = no cambia.
    comment: comentario nuevo ("" lo borra); vacío = no cambia.
    new_name: nombre nuevo; lo que citaba el nombre viejo pasa a citar el nuevo; vacío = no cambia.
    unit: unidad nueva, p. ej. "in", "mm^2", "text", "" para sin unidad; solo en parámetros de usuario; null = no cambia.
    favorite: true o false pone o quita la estrella; null = no cambia.
    """
    anterior = _parametro(sesion.doc, name)["expression"]
    if expression is None and comment is None and new_name is None and unit is None and favorite is None:
        raise error("INVALID_ARGUMENTS", "No pediste ningún cambio: pasá expression, comment, new_name, unit o favorite.")
    if unit is not None and (sesion.doc.parametros.obtener(name).op or "source" in _parametro(sesion.doc, name)):
        raise error("INVALID_ARGUMENTS", f"«{name}» es un parámetro del modelo: su unidad la da el paso o la cota.")
    if expression is not None and any(c.nombre == name and c.referencia
                                      for o in sesion.doc.operaciones if isinstance(o, OpBoceto)
                                      for c in o.boceto.cotas.values()):
        raise error("INVALID_DIMENSION", "Una cota de referencia mide la geometría: su valor no se puede editar.",
                    "Convertí primero la cota a driving con edit_dimension(reference=false).")
    tabla = _copia(sesion.doc.parametros)
    tipo = tabla.obtener(name).tipo if unit is None else tipo_de_unidad(unit)
    tabla.modificar(name, None if expression is None else _texto(expression, tipo), comment, unit, favorite)
    sesion.doc.aplicar_parametros(tabla)
    if new_name is not None and new_name != name:
        sesion.doc.renombrar_parametro(name, new_name)
        name = new_name
    return dict(_avisar_valor_raro(sesion, _parametro(sesion.doc, name)), previous_expression=anterior)


@herramienta("delete_parameter", "parametros", "Borra un parámetro que no use ningún paso ni otro parámetro. "
             "Para quitar un dN, borrá su cota con delete_sketch_entities o su paso; falla si una expresión ajena lo usa.",
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

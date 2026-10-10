# -*- coding: utf-8 -*-
"""
Nodos de puntos, vectores y planos (GH3): construir, descomponer, sumar, escalar, distancia, productos, grillas de
puntos y puntos en círculo. Python puro (mm y grados).
"""
import math

from ..timeline.parametros import ANGULO, LONGITUD
from .nodos import E, ErrorNodo, S, nodo
from .tipos import LIMITE_ITEMS, Plano, _cruz, _norma

ORIGEN = (0.0, 0.0, 0.0)
EJE_Z = (0.0, 0.0, 1.0)


def _mas(a, b):
    return tuple(x + y for x, y in zip(a, b, strict=True))


def _menos(a, b):
    return tuple(x - y for x, y in zip(a, b, strict=True))


def _por(v, f):
    return tuple(x * f for x in v)


@nodo("construir_punto", "Construir punto", "vectores", "Punto (x, y, z) en mm.",
      [E("x", "numero", 0.0, unidad=LONGITUD), E("y", "numero", 0.0, unidad=LONGITUD),
       E("z", "numero", 0.0, unidad=LONGITUD)], [S("punto", "punto")])
def _construir_punto(x, y, z):
    return (x, y, z)


@nodo("descomponer", "Descomponer punto", "vectores", "Las coordenadas x, y, z de un punto o vector.",
      [E("punto", "punto")], [S("x", "numero"), S("y", "numero"), S("z", "numero")])
def _descomponer(punto):
    return punto


@nodo("vector_2p", "Vector entre dos puntos", "vectores", "El vector de a hacia b (b − a) y su largo.",
      [E("a", "punto", ORIGEN), E("b", "punto", (1.0, 0.0, 0.0))], [S("vector", "vector"), S("largo", "numero")])
def _vector_2p(a, b):
    v = _menos(b, a)
    return v, _norma(v)


@nodo("sumar_vectores", "Sumar vectores", "vectores", "a + b (un punto más un vector es el punto desplazado).",
      [E("a", "vector", ORIGEN), E("b", "vector", ORIGEN)], [S("resultado", "vector")])
def _sumar_vectores(a, b):
    return _mas(a, b)


@nodo("escalar_vector", "Escalar vector", "vectores", "El vector multiplicado por un factor.",
      [E("vector", "vector", EJE_Z), E("factor", "numero", 1.0)], [S("vector", "vector")])
def _escalar_vector(vector, factor):
    return _por(vector, factor)


@nodo("distancia", "Distancia", "vectores", "Distancia entre dos puntos (mm).",
      [E("a", "punto", ORIGEN), E("b", "punto", ORIGEN)], [S("distancia", "numero")])
def _distancia(a, b):
    return math.dist(a, b)


@nodo("largo_vector", "Largo de vector", "vectores", "Largo (módulo) del vector.", [E("vector", "vector", EJE_Z)],
      [S("largo", "numero")])
def _largo_vector(vector):
    return _norma(vector)


@nodo("unitario", "Vector unitario", "vectores", "El vector con largo 1 (el nulo es error).",
      [E("vector", "vector", EJE_Z)], [S("vector", "vector")])
def _unitario(vector):
    n = _norma(vector)
    if n < 1e-12:
        raise ErrorNodo("El vector nulo no tiene dirección.")
    return tuple(x / n for x in vector)


@nodo("producto_escalar", "Producto escalar", "vectores", "a · b.",
      [E("a", "vector", EJE_Z), E("b", "vector", EJE_Z)], [S("resultado", "numero")])
def _producto_escalar(a, b):
    return sum(x * y for x, y in zip(a, b, strict=True))


@nodo("producto_vectorial", "Producto vectorial", "vectores", "a × b (perpendicular a los dos).",
      [E("a", "vector", (1.0, 0.0, 0.0)), E("b", "vector", (0.0, 1.0, 0.0))], [S("vector", "vector")])
def _producto_vectorial(a, b):
    return _cruz(a, b)


@nodo("plano_origen", "Plano de origen", "vectores", "Plano XY, XZ o YZ (como los del origen) pasando por un punto.",
      [E("nombre", "texto", "XY", "XY, XZ o YZ"), E("origen", "punto", ORIGEN)], [S("plano", "plano")])
def _plano_origen(nombre, origen):
    return Plano.de_nombre(nombre, origen)


@nodo("construir_plano", "Construir plano", "vectores",
      "Plano por un punto con una normal; el eje x (opcional) fija el giro dentro del plano.",
      [E("origen", "punto", ORIGEN), E("normal", "vector", EJE_Z), E("eje_x", "vector", None)], [S("plano", "plano")])
def _construir_plano(origen, normal, eje_x):
    return Plano.desde(origen, normal, eje_x)


@nodo("descomponer_plano", "Descomponer plano", "vectores", "Origen y ejes x, y, z (normal) de un plano.",
      [E("plano", "plano", "XY")], [S("origen", "punto"), S("eje_x", "vector"), S("eje_y", "vector"),
                                    S("normal", "vector")])
def _descomponer_plano(plano):
    return plano.origen, plano.x, plano.y, plano.z


@nodo("puntos_grilla", "Grilla de puntos", "vectores",
      "cantidad_x × cantidad_y puntos en una grilla rectangular sobre un plano (por defecto XY): filas a lo largo del "
      "eje y del plano, y en cada fila los puntos van en x. El primero está en el origen del plano.",
      [E("plano", "plano", "XY"), E("cantidad_x", "entero", 3), E("cantidad_y", "entero", 3),
       E("paso_x", "numero", 10.0, unidad=LONGITUD), E("paso_y", "numero", 10.0, unidad=LONGITUD)],
      [S("puntos", "punto", acceso="lista")])
def _puntos_grilla(plano, cantidad_x, cantidad_y, paso_x, paso_y):
    if cantidad_x < 1 or cantidad_y < 1:
        raise ErrorNodo("La grilla necesita al menos 1 punto por lado.")
    if cantidad_x * cantidad_y > LIMITE_ITEMS:
        raise ErrorNodo(f"La grilla de {cantidad_x} × {cantidad_y} supera el tope de {LIMITE_ITEMS} puntos.")
    return [plano.punto(i * paso_x, j * paso_y) for j in range(cantidad_y) for i in range(cantidad_x)]


@nodo("puntos_circulo", "Puntos en círculo", "vectores",
      "«cantidad» puntos repartidos en un círculo de radio dado alrededor del origen de un plano, desde el ángulo "
      "inicial (grados, medido desde el eje x del plano, antihorario mirando desde la normal).",
      [E("plano", "plano", "XY"), E("radio", "numero", 10.0, unidad=LONGITUD), E("cantidad", "entero", 6),
       E("angulo_inicial", "numero", 0.0, unidad=ANGULO)], [S("puntos", "punto", acceso="lista")])
def _puntos_circulo(plano, radio, cantidad, angulo_inicial):
    if cantidad < 1:
        raise ErrorNodo("Hace falta al menos 1 punto.")
    if cantidad > LIMITE_ITEMS:
        raise ErrorNodo(f"{cantidad} puntos superan el tope de {LIMITE_ITEMS}.")
    salida = []
    for k in range(cantidad):
        a = math.radians(angulo_inicial + 360.0 * k / cantidad)
        salida.append(plano.punto(radio * math.cos(a), radio * math.sin(a)))
    return salida

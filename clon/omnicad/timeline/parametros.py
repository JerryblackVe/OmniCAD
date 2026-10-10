# -*- coding: utf-8 -*-
"""
Parámetros y expresiones con unidades.

Equivalencia con Fusion 360: `UserParameters` + `ValueInput.createByString("10 mm")`
(informe_analisis.md §3.4). Igual que Fusion, hay UNA unidad interna por magnitud
y las expresiones llevan unidades explícitas o toman la unidad por defecto:
  - longitud: milímetros (mm)  — Fusion usa cm internamente; acá mm por STL/STEP e impresión 3D.
  - ángulo:   grados (deg)     — se convierten a radianes solo al llamar al kernel.

Las expresiones se evalúan con `ast` y una lista blanca de nodos: nunca con eval().
"""
import ast
import keyword
import math
import re
import unicodedata

LONGITUD, ANGULO, ESCALAR = "longitud", "angulo", "escalar"
TIPOS = (LONGITUD, ANGULO, ESCALAR)

# Factor a la unidad interna de cada magnitud.
UNIDADES = {
    "mm": (LONGITUD, 1.0), "cm": (LONGITUD, 10.0), "m": (LONGITUD, 1000.0),
    "in": (LONGITUD, 25.4), "ft": (LONGITUD, 304.8),
    "deg": (ANGULO, 1.0), "rad": (ANGULO, 180.0 / math.pi),
}
FUNCIONES = {
    "sin": lambda g: math.sin(math.radians(g)), "cos": lambda g: math.cos(math.radians(g)),
    "tan": lambda g: math.tan(math.radians(g)), "sqrt": math.sqrt, "abs": abs,
    "min": min, "max": max, "round": round, "floor": math.floor, "ceil": math.ceil,
}
CONSTANTES = {"pi": math.pi, "PI": math.pi}
RESERVADOS = set(UNIDADES) | set(FUNCIONES) | set(CONSTANTES)

_NUM_CON_UNIDAD = re.compile(
    r"(?<![\w.])((?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)\s*(°|" + "|".join(sorted(UNIDADES, key=len, reverse=True)) + r")(?![\w])")


class ErrorExpresion(ValueError):
    """La expresión no se puede evaluar (sintaxis, nombre desconocido, unidades o ciclo)."""


def _preprocesar(expr, tipo):
    """Reemplaza `10 mm` por `(10*1.0)` y valida que la unidad sea de la magnitud correcta."""
    def reemplazo(m):
        unidad = "deg" if m.group(2) == "°" else m.group(2)
        magnitud, factor = UNIDADES[unidad]
        if tipo != ESCALAR and magnitud != tipo:
            raise ErrorExpresion(f"La unidad '{unidad}' es de {magnitud}, se esperaba {tipo}.")
        return f"({m.group(1)}*{factor!r})"
    return _NUM_CON_UNIDAD.sub(reemplazo, expr.replace(",", ".") if expr.count(",") and "(" not in expr else expr)


def _evaluar_nodo(nodo, nombres):
    if isinstance(nodo, ast.Expression):
        return _evaluar_nodo(nodo.body, nombres)
    if isinstance(nodo, ast.Constant) and isinstance(nodo.value, (int, float)) and not isinstance(nodo.value, bool):
        return _real(nodo.value)
    if isinstance(nodo, ast.Name):
        if nodo.id in CONSTANTES:
            return CONSTANTES[nodo.id]
        if nodo.id in nombres:
            return nombres[nodo.id]
        raise ErrorExpresion(f"Nombre desconocido: '{nodo.id}'.")
    if isinstance(nodo, ast.UnaryOp) and isinstance(nodo.op, (ast.UAdd, ast.USub)):
        v = _evaluar_nodo(nodo.operand, nombres)
        return -v if isinstance(nodo.op, ast.USub) else v
    if isinstance(nodo, ast.BinOp):
        a, b = _evaluar_nodo(nodo.left, nombres), _evaluar_nodo(nodo.right, nombres)
        operaciones = {ast.Add: lambda: a + b, ast.Sub: lambda: a - b, ast.Mult: lambda: a * b,
                       ast.Div: lambda: a / b, ast.Pow: lambda: a ** b}
        if type(nodo.op) in operaciones:
            try:
                return _real(operaciones[type(nodo.op)]())
            except ZeroDivisionError:
                raise ErrorExpresion("División por cero.") from None
            except (OverflowError, ValueError, TypeError):
                raise ErrorExpresion("El resultado es demasiado grande o no es un número real.") from None
    if isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Name) and nodo.func.id in FUNCIONES and not nodo.keywords:
        args = [_evaluar_nodo(a, nombres) for a in nodo.args]
        try:
            return _real(FUNCIONES[nodo.func.id](*args))
        except (TypeError, ValueError, OverflowError) as e:
            raise ErrorExpresion(f"Error en {nodo.func.id}(): {e}") from None
    if isinstance(nodo, ast.Constant) and isinstance(nodo.value, str):
        raise ErrorExpresion(f"Expresión no permitida: el texto entre comillas ('{nodo.value}') no va; "
                             "escribí la medida sin comillas, p. ej. 60 mm.")
    raise ErrorExpresion("Expresión no permitida.")


def _real(v):
    """Solo números reales finitos: (-8)**0.5 da un complejo y floor(inf) un OverflowError."""
    if isinstance(v, complex):
        raise ErrorExpresion("El resultado no es un número real.")
    try:
        v = float(v)
    except OverflowError:
        raise ErrorExpresion("El número es demasiado grande.") from None
    if math.isnan(v) or math.isinf(v):
        raise ErrorExpresion("El resultado no es un número finito.")
    return v


def evaluar(expr, tipo=LONGITUD, nombres=None):
    """Evalúa `expr` y devuelve el valor en la unidad interna de `tipo`."""
    if tipo not in TIPOS:
        raise ValueError(f"tipo inválido: {tipo}")
    if isinstance(expr, (int, float)):
        return float(expr)
    texto = (expr or "").strip()
    if not texto:
        raise ErrorExpresion("Expresión vacía.")
    try:
        arbol = ast.parse(_preprocesar(texto, tipo), mode="eval")
    except SyntaxError:
        raise ErrorExpresion(f"Sintaxis inválida: '{texto}'.") from None
    return _real(_evaluar_nodo(arbol, nombres or {}))


def nombres_usados(expr):
    """Nombres de parámetros que aparecen en una expresión (sin unidades ni funciones)."""
    try:
        arbol = ast.parse(_preprocesar(str(expr), ESCALAR), mode="eval")
    except (SyntaxError, ErrorExpresion):
        return set()
    return {n.id for n in ast.walk(arbol) if isinstance(n, ast.Name) and n.id not in RESERVADOS}


def validar_nombre(nombre):
    """Como en Fusion, un nombre de parámetro es un identificador: letras (también ñ y acentos), dígitos y «_», sin
    empezar con dígito. Se exige la forma normalizada NFKC porque así lo lee el evaluador (si no, «ñ» escrita como
    n + tilde combinada no se encontraría nunca)."""
    if not (isinstance(nombre, str) and nombre.isidentifier() and unicodedata.normalize("NFKC", nombre) == nombre):
        raise ErrorExpresion(f"Nombre de parámetro inválido: '{nombre}'.")
    if keyword.iskeyword(nombre):
        raise ErrorExpresion(f"'{nombre}' es una palabra reservada (unidad, función o palabra de Python).")
    if nombre in RESERVADOS:
        raise ErrorExpresion(f"'{nombre}' es una palabra reservada (unidad o función).")


class Parametro:
    def __init__(self, nombre, expresion, tipo=LONGITUD, comentario=""):
        self.nombre, self.expresion, self.tipo, self.comentario = nombre, str(expresion), tipo, comentario

    def a_dict(self):
        return {"nombre": self.nombre, "expresion": self.expresion, "tipo": self.tipo, "comentario": self.comentario}


class TablaParametros:
    """Parámetros de usuario. Pueden referirse unos a otros; se detectan ciclos."""

    def __init__(self):
        self._params = {}

    def __iter__(self):
        return iter(self._params.values())

    def __len__(self):
        return len(self._params)

    def __contains__(self, nombre):
        return nombre in self._params

    def obtener(self, nombre):
        return self._params[nombre]

    def agregar(self, nombre, expresion, tipo=LONGITUD, comentario=""):
        validar_nombre(nombre)
        if nombre in self._params:
            raise ErrorExpresion(f"Ya existe el parámetro '{nombre}'.")
        if tipo not in TIPOS:
            raise ErrorExpresion(f"Tipo inválido: {tipo}")
        self._params[nombre] = Parametro(nombre, expresion, tipo, comentario)
        try:
            self.valores()
        except ErrorExpresion:
            del self._params[nombre]
            raise

    def modificar(self, nombre, expresion=None, comentario=None):
        p = self._params[nombre]
        anterior = p.expresion
        if expresion is not None:
            p.expresion = str(expresion)
        if comentario is not None:
            p.comentario = comentario
        try:
            self.valores()
        except ErrorExpresion:
            p.expresion = anterior
            raise

    def eliminar(self, nombre):
        usuarios = [p.nombre for p in self._params.values() if nombre in nombres_usados(p.expresion)]
        if usuarios:
            raise ErrorExpresion(f"No se puede borrar '{nombre}': lo usan {', '.join(usuarios)}.")
        del self._params[nombre]

    def valores(self):
        """Resuelve todos los parámetros (orden topológico). Lanza ErrorExpresion ante ciclos."""
        resueltos, en_curso = {}, set()

        def resolver(nombre):
            if nombre in resueltos:
                return resueltos[nombre]
            if nombre in en_curso:
                raise ErrorExpresion(f"Referencia circular en el parámetro '{nombre}'.")
            en_curso.add(nombre)
            p = self._params[nombre]
            deps = {n: resolver(n) for n in nombres_usados(p.expresion) if n in self._params}
            resueltos[nombre] = evaluar(p.expresion, p.tipo, deps)
            en_curso.discard(nombre)
            return resueltos[nombre]

        for nombre in self._params:
            resolver(nombre)
        return resueltos

    def evaluar(self, expr, tipo=LONGITUD):
        return evaluar(expr, tipo, self.valores())

    def a_lista(self):
        return [p.a_dict() for p in self._params.values()]

    @classmethod
    def desde_lista(cls, datos):
        t = cls()
        for d in datos or []:
            t._params[d["nombre"]] = Parametro(d["nombre"], d["expresion"], d.get("tipo", LONGITUD), d.get("comentario", ""))
        t.valores()
        return t

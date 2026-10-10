# -*- coding: utf-8 -*-
"""
Catálogo de tipos de nodo (GH3): cada nodo es una función pura con puertos de entrada y de salida tipados.

Agregar un nodo (en un módulo `nodos_*.py` de este paquete):

    @nodo("sumar", "Sumar", "matematica", "Suma dos números: a + b.",
          [E("a", "numero", 0.0), E("b", "numero", 0.0)], [S("resultado", "numero")])
    def _sumar(a, b):
        return a + b

  - Cada argumento de la función es una entrada (por nombre). Si la función tiene un argumento `ctx`, recibe el
    `ContextoNodo` (parámetros del documento y `ctx.aviso(texto)` para avisar sin fallar).
  - Devuelve el valor de la salida (una sola) o una tupla con una por salida, en orden.
  - Una entrada sin `defecto` es obligatoria: sin datos, el nodo no corre y avisa. `defecto=None` = opcional (llega
    None). Los textos en entradas numéricas son expresiones (`unidad`: longitud, angulo o escalar).
  - acceso "item": el nodo corre una vez por ítem (emparejado de listas); "lista": recibe la rama entera; "arbol":
    recibe el árbol entero (y devuelve árboles en sus salidas "arbol").
  - Para fallar: `raise ErrorNodo("mensaje en español")` (o cualquier error del núcleo): esa vuelta da nulo y el
    nodo queda en error con el mensaje; las demás vueltas siguen.
  - `usa_contexto=True` si el resultado depende de los parámetros del documento (no solo de sus entradas): así la
    caché del motor lo recalcula cuando cambian.

Los módulos de nodos se cargan recién con el primer `catalogo()` / `definicion()`: importar el paquete es liviano.
"""
import importlib
import inspect
from dataclasses import dataclass, field

from ..timeline.parametros import ANGULO, ESCALAR, LONGITUD
from .tipos import ACCESOS, TIPOS, UNIDADES, a_json, convertir

CATEGORIAS = {
    "entrada": "Entradas: números, deslizadores, puntos, rangos, series y parámetros del documento.",
    "matematica": "Operaciones, funciones y expresiones con números.",
    "listas": "Largo, ítem, sublista, invertir, ordenar, repetir, fusionar y filtrar listas.",
    "arboles": "Aplanar, injertar, simplificar e invertir árboles de datos.",
    "vectores": "Puntos, vectores, planos, grillas y puntos en círculo.",
    "curvas": "Curvas planas: línea, círculo, rectángulo, largo y extrusión.",
    "solidos": "Primitivas, mover, rotar, escalar, simetría, booleanas y medidas de cuerpos (núcleo OpenCascade).",
    "salida": "Resultados del grafo: lo que devuelve run_graph y lo que se hornea en el timeline.",
}
_MODULOS = ("nodos_basicos", "nodos_vectores", "nodos_geometria")


class _Falta:
    def __repr__(self):
        return "FALTA"


FALTA = _Falta()          # valor por defecto de una entrada obligatoria


class ErrorNodo(ValueError):
    """Falla de una vuelta de un nodo (dato fuera de rango, división por cero…)."""


@dataclass(frozen=True)
class Puerto:
    nombre: str
    tipo: str = "cualquiera"
    acceso: str = "item"
    defecto: object = FALTA
    unidad: str = ESCALAR
    descripcion: str = ""

    @property
    def obligatorio(self):
        return self.defecto is FALTA

    def a_json(self, salida=False):
        d = {"name": self.nombre, "type": self.tipo, "access": self.acceso}
        if not salida and self.tipo in ("numero", "punto"):      # cómo se lee un número o una expresión que llega
            d["unit"] = UNIDADES[self.unidad] if self.tipo == "numero" else "mm"
        if not salida:
            d["required"] = self.obligatorio
            if not self.obligatorio:
                d["default"] = a_json(self.defecto)
        if self.descripcion:
            d["description"] = self.descripcion
        return d


def E(nombre, tipo="cualquiera", defecto=FALTA, descripcion="", acceso="item", unidad=None):
    """Puerto de entrada. `unidad` por defecto: escalar (los ángulos y largos lo dicen explícito)."""
    if tipo not in TIPOS or acceso not in ACCESOS:
        raise ValueError(f"Puerto mal declarado: {nombre} ({tipo}, {acceso})")
    unidad = unidad or ESCALAR
    if unidad not in (LONGITUD, ANGULO, ESCALAR):
        raise ValueError(f"Unidad inválida en el puerto {nombre}: {unidad}")
    if defecto is not FALTA and defecto is not None:
        if acceso == "item":
            defecto = convertir(defecto, tipo, unidad)
        elif acceso == "lista":
            defecto = [convertir(x, tipo, unidad) for x in defecto]
    return Puerto(nombre, tipo, acceso, defecto, unidad, descripcion)


def S(nombre, tipo="cualquiera", descripcion="", acceso="item", unidad=None):
    """Puerto de salida."""
    if tipo not in TIPOS or acceso not in ACCESOS:
        raise ValueError(f"Puerto mal declarado: {nombre} ({tipo}, {acceso})")
    return Puerto(nombre, tipo, acceso, FALTA, unidad or ESCALAR, descripcion)


@dataclass(frozen=True)
class DefNodo:
    tipo: str
    titulo: str
    categoria: str
    descripcion: str
    entradas: tuple
    salidas: tuple
    funcion: object = field(repr=False)
    usa_contexto: bool = False
    recibe_ctx: bool = False

    @property
    def por_arbol(self):
        """True si alguna entrada recibe el árbol entero: el nodo corre una sola vez."""
        return any(p.acceso == "arbol" for p in self.entradas)

    def entrada(self, nombre):
        return next((p for p in self.entradas if p.nombre == nombre), None)

    def salida(self, nombre):
        return next((p for p in self.salidas if p.nombre == nombre), None)

    def a_json(self):
        return {"type": self.tipo, "title": self.titulo, "category": self.categoria, "description": self.descripcion,
                "inputs": [p.a_json() for p in self.entradas], "outputs": [p.a_json(salida=True) for p in self.salidas]}


_NODOS = {}
_CARGADO = False


def nodo(tipo, titulo, categoria, descripcion, entradas=(), salidas=(), usa_contexto=False):
    """Registra la función como tipo de nodo (ver el docstring del módulo)."""
    if categoria not in CATEGORIAS:
        raise ValueError(f"Categoría desconocida: {categoria}")

    def registrar(funcion):
        if tipo in _NODOS:
            raise ValueError(f"Tipo de nodo repetido: {tipo}")
        argumentos = set(inspect.signature(funcion).parameters)
        nombres = [p.nombre for p in entradas]
        if set(nombres) != argumentos - {"ctx"}:
            raise ValueError(f"El nodo {tipo} declara {nombres} pero la función recibe {sorted(argumentos)}")
        if len(set(p.nombre for p in salidas)) != len(salidas) or not salidas:
            raise ValueError(f"El nodo {tipo} necesita al menos una salida y sin nombres repetidos")
        _NODOS[tipo] = DefNodo(tipo, titulo, categoria, descripcion, tuple(entradas), tuple(salidas), funcion,
                               usa_contexto, "ctx" in argumentos)
        return funcion
    return registrar


def _cargar():
    global _CARGADO
    if not _CARGADO:
        _CARGADO = True
        for m in _MODULOS:
            importlib.import_module(f"{__package__}.{m}")


def catalogo():
    """{tipo: DefNodo} en orden de registro (por categoría)."""
    _cargar()
    return dict(_NODOS)


def definicion(tipo):
    """La DefNodo del tipo, o None si no existe."""
    _cargar()
    return _NODOS.get(tipo)


@dataclass
class ContextoNodo:
    """Lo que recibe una función de nodo con argumento `ctx`."""
    parametros: object
    avisos: list = field(default_factory=list)

    def aviso(self, texto):
        self.avisos.append(str(texto))

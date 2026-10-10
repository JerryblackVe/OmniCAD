# -*- coding: utf-8 -*-
"""
Árboles de datos del grafo (GH1 de `docs/brechas_grasshopper.md`): el modelo de datos de la programación visual.

Los datos viajan entre nodos como un `Arbol`: ramas con una `Ruta` (tupla de enteros, se escribe `{0;1}`) y una lista
de ítems cada una. Un valor suelto es un árbol de una rama `{0}` con un ítem; `None` es un ítem nulo. Las ramas se
recorren siempre en orden de ruta ({0} < {0;0} < {0;1} < {1}), así el resultado no depende del orden de carga.

Operaciones de árbol (las funciones de los árboles de Grasshopper, escritas desde cero):
  - aplanar: todos los ítems en una sola rama, en orden de ruta.
  - injertar: cada ítem a su propia rama (ruta de la rama + índice del ítem).
  - simplificar: quita los índices iniciales que comparten TODAS las rutas (cada ruta conserva al menos uno).
  - invertir: intercambia filas y columnas (ítem j de la rama i → ítem i de la rama {j}); los huecos quedan nulos.

Emparejado de listas (cómo se combinan las entradas de un nodo que corre ítem por ítem):
  - "larga": tantas vueltas como la lista más larga; las cortas repiten su último ítem.
  - "corta": tantas vueltas como la más corta; lo que sobra de las largas no se usa.
  - "cruzada": producto cruzado, todas contra todas (la primera lista varía más lento).
Entre árboles, las ramas se emparejan siempre como «larga» (manda el árbol con más ramas y da las rutas de salida).

Python puro: sin Qt y sin OpenCascade.
"""
import itertools
import math
import operator
import re

MODOS_EMPAREJADO = {"larga": "lista más larga (las cortas repiten su último ítem)",
                    "corta": "lista más corta (lo que sobra no se usa)",
                    "cruzada": "producto cruzado (todas contra todas)"}
MODIFICADORES = {"aplanar": "todos los ítems en una sola rama {0}",
                 "injertar": "cada ítem a su propia rama",
                 "simplificar": "quita los índices iniciales que comparten todas las rutas",
                 "invertir": "intercambia filas y columnas (ítem j de la rama i → rama {j})"}

_RUTA_TEXTO = re.compile(r"^\{\s*(\d+(?:\s*;\s*\d+)*)\s*\}$")


class ErrorArbol(ValueError):
    """Ruta, árbol o modo de emparejado mal formado."""


class Ruta(tuple):
    """Dirección de una rama: enteros ≥ 0. `Ruta(0, 1)`, `Ruta((0, 1))` y `Ruta.de("{0;1}")` son la misma."""

    def __new__(cls, *indices):
        if len(indices) == 1 and isinstance(indices[0], (tuple, list)):
            indices = tuple(indices[0])
        if not indices:
            raise ErrorArbol("Una ruta tiene al menos un índice, p. ej. {0}.")
        salida = []
        for i in indices:
            if isinstance(i, bool):
                raise ErrorArbol(f"Índice de ruta inválido: {i!r}.")
            try:
                n = operator.index(i)
            except TypeError:
                raise ErrorArbol(f"Índice de ruta inválido: {i!r} (van enteros ≥ 0).") from None
            if n < 0:
                raise ErrorArbol(f"Índice de ruta negativo: {n}.")
            salida.append(n)
        return super().__new__(cls, salida)

    @classmethod
    def de(cls, valor):
        """Ruta desde una Ruta, una tupla o lista de enteros, un entero o un texto «{0;1}»."""
        if isinstance(valor, Ruta):
            return valor
        if isinstance(valor, str):
            m = _RUTA_TEXTO.match(valor.strip())
            if not m:
                raise ErrorArbol(f"Ruta mal escrita: «{valor}» (se escribe entre llaves, p. ej. {{0;1}}).")
            return cls(*(int(x) for x in m.group(1).split(";")))
        if isinstance(valor, (tuple, list)):
            return cls(*valor)
        return cls(valor)

    def mas(self, indice):
        """Esta ruta con un índice más al final: {0}.mas(2) = {0;2}."""
        return Ruta(*self, indice)

    def __str__(self):
        return "{" + ";".join(str(i) for i in self) + "}"

    def __repr__(self):
        return f"Ruta{self}"


class Arbol:
    """Ramas ordenadas por ruta, cada una con su lista de ítems. Las operaciones devuelven árboles NUEVOS."""

    __slots__ = ("_ramas",)

    def __init__(self, ramas=None):
        self._ramas = {}
        if ramas:
            pares = ramas.items() if isinstance(ramas, dict) else ramas
            for ruta, items in pares:
                self.extender(ruta, items)

    # ------------------------------------------------------------ construcción
    @classmethod
    def de_valor(cls, valor, ruta=(0,)):
        """Un solo ítem en la rama `ruta` (por defecto {0})."""
        a = cls()
        a.agregar(ruta, valor)
        return a

    @classmethod
    def de_lista(cls, valores, ruta=(0,)):
        """Una sola rama con todos los valores (la rama existe aunque la lista esté vacía)."""
        a = cls()
        a.extender(ruta, valores)
        return a

    @classmethod
    def desde_dict(cls, datos):
        """{"{0}": [...], "{0;1}": [...]} → Arbol (lo que escribe `a_dict`)."""
        if not isinstance(datos, dict):
            raise ErrorArbol("Un árbol se escribe como objeto {\"{0}\": [ítems], \"{1}\": [ítems]}.")
        a = cls()
        for ruta, items in datos.items():
            if not isinstance(items, list):
                raise ErrorArbol(f"La rama {ruta} tiene que ser una lista de ítems.")
            a.extender(Ruta.de(ruta), items)
        return a

    def a_dict(self, convertir=None):
        """{"{0}": [...]} en orden de ruta; `convertir` (opcional) se aplica a cada ítem."""
        f = convertir or (lambda x: x)
        return {str(r): [f(x) for x in items] for r, items in self.ramas()}

    def agregar(self, ruta, valor):
        self._ramas.setdefault(Ruta.de(ruta), []).append(valor)

    def extender(self, ruta, valores):
        self._ramas.setdefault(Ruta.de(ruta), []).extend(valores)

    # ------------------------------------------------------------ consulta
    def rama(self, ruta):
        """Copia de los ítems de la rama (lista vacía si no existe)."""
        return list(self._ramas.get(Ruta.de(ruta), []))

    def rutas(self):
        return sorted(self._ramas)

    def ramas(self):
        """[(Ruta, [ítems])] en orden de ruta (las listas son copias)."""
        return [(r, list(self._ramas[r])) for r in sorted(self._ramas)]

    def items(self):
        """Todos los ítems en orden de ruta."""
        return [x for r in sorted(self._ramas) for x in self._ramas[r]]

    @property
    def cantidad_ramas(self):
        return len(self._ramas)

    @property
    def vacio(self):
        return not any(self._ramas.values())

    def primero(self, defecto=None):
        """El primer ítem (en orden de ruta) o `defecto` si no hay ninguno."""
        for r in sorted(self._ramas):
            if self._ramas[r]:
                return self._ramas[r][0]
        return defecto

    def __len__(self):
        return sum(len(v) for v in self._ramas.values())

    def __eq__(self, otro):
        return isinstance(otro, Arbol) and self.ramas() == otro.ramas()

    __hash__ = None

    def __repr__(self):
        cuerpo = ", ".join(f"{r}: {items!r}" for r, items in self.ramas())
        return f"Arbol({{{cuerpo}}})"

    # ------------------------------------------------------------ operaciones de árbol
    def mapear(self, funcion):
        """Árbol con las mismas ramas y `funcion(ítem)` en cada ítem."""
        return Arbol([(r, [funcion(x) for x in items]) for r, items in self.ramas()])

    def aplanar(self, ruta=(0,)):
        """Todos los ítems en una sola rama (por defecto {0})."""
        return Arbol.de_lista(self.items(), ruta)

    def injertar(self):
        """Cada ítem a su propia rama: el ítem i de la rama {a;b} va a {a;b;i}."""
        a = Arbol()
        for r, items in self.ramas():
            for i, x in enumerate(items):
                a.agregar(r.mas(i), x)
        return a

    def simplificar(self):
        """Quita los índices iniciales que comparten todas las rutas; cada ruta conserva al menos el último índice
        ({0;0;3} sola → {3}; {0;1;0} y {0;1;1} → {0} y {1})."""
        rutas = self.rutas()
        if not rutas:
            return Arbol()
        tope = min(len(r) for r in rutas) - 1
        k = 0
        while k < tope and all(r[k] == rutas[0][k] for r in rutas):
            k += 1
        return Arbol([(Ruta(*r[k:]), items) for r, items in self.ramas()])

    def invertir(self):
        """Intercambia filas y columnas: el ítem j de la i-ésima rama pasa a ser el ítem i de la rama {j}. Si las
        ramas tienen distinto largo, los huecos quedan nulos (None)."""
        ramas = [items for _r, items in self.ramas()]
        if not ramas:
            return Arbol()
        n = max(len(items) for items in ramas)
        return Arbol([(Ruta(j), [items[j] if j < len(items) else None for items in ramas]) for j in range(n)])

    def fusionar(self, otro):
        """Los dos árboles juntos: las ramas con la misma ruta se concatenan (primero los ítems de este)."""
        a = Arbol(self.ramas())
        for r, items in otro.ramas():
            a.extender(r, items)
        return a


def aplicar_modificador(arbol, nombre):
    """El modificador de entrada `nombre` (ver MODIFICADORES) aplicado a `arbol`; None o "" lo deja igual."""
    if not nombre:
        return arbol
    if nombre not in MODIFICADORES:
        raise ErrorArbol(f"Modificador desconocido: «{nombre}». Válidos: {', '.join(MODIFICADORES)}.")
    return getattr(arbol, nombre)()


def emparejar(listas, modo="larga"):
    """Combina listas para correr un nodo ítem por ítem: [(x1, x2, …)] con una tupla por vuelta.

    "larga": len = la más larga, las cortas repiten su último ítem; "corta": len = la más corta; "cruzada": producto
    cruzado. Si alguna lista está vacía no hay vueltas. Sin listas, una vuelta sin argumentos."""
    if modo not in MODOS_EMPAREJADO:
        raise ErrorArbol(f"Emparejado desconocido: «{modo}». Válidos: {', '.join(MODOS_EMPAREJADO)}.")
    listas = [list(x) for x in listas]
    if not listas:
        return [()]
    if any(not x for x in listas):
        return []
    if modo == "cruzada":
        return list(itertools.product(*listas))
    n = max(len(x) for x in listas) if modo == "larga" else min(len(x) for x in listas)
    return [tuple(x[min(i, len(x) - 1)] for x in listas) for i in range(n)]


def cantidad_vueltas(largos, modo="larga"):
    """Cuántas vueltas daría `emparejar` con listas de esos largos, sin armarlas (para frenar un producto cruzado
    gigante antes de llenar la memoria)."""
    if not largos:
        return 1
    if min(largos) == 0:
        return 0
    if modo == "cruzada":
        return math.prod(largos)
    return max(largos) if modo == "larga" else min(largos)


def emparejar_ramas(arboles):
    """Empareja las ramas de varios árboles como «lista más larga»: [(ruta de salida, [rama de cada árbol])].

    Manda el árbol con más ramas (el primero si empatan): da la cantidad de vueltas y las rutas de salida; los demás
    repiten su última rama. Un árbol sin ramas deja todo sin vueltas."""
    listas = [a.ramas() for a in arboles]
    if not listas or any(not x for x in listas):
        return []
    maestro = max(range(len(listas)), key=lambda k: len(listas[k]))
    n = len(listas[maestro])
    return [(listas[maestro][i][0], [x[min(i, len(x) - 1)][1] for x in listas]) for i in range(n)]

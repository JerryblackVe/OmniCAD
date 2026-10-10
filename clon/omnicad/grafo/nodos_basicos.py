# -*- coding: utf-8 -*-
"""
Nodos sin geometría (GH3): entradas, matemática, listas, árboles y salida. Python puro.

Las entradas numéricas aceptan expresiones con los parámetros del documento («ancho / 2», «10 mm»): así un grafo
se enlaza con la tabla de parámetros. Los ángulos van en grados.
"""
import math
import random

from ..timeline.parametros import ANGULO, ESCALAR, ErrorExpresion, evaluar
from .nodos import E, ErrorNodo, S, nodo
from .tipos import LIMITE_ITEMS


def _finito(v, que="El resultado"):
    v = float(v)
    if not math.isfinite(v):
        raise ErrorNodo(f"{que} no es un número finito.")
    return v


def _cantidad(n, que="La cantidad", minimo=0):
    if n < minimo:
        raise ErrorNodo(f"{que} tiene que ser al menos {minimo} (llegó {n}).")
    if n > LIMITE_ITEMS:
        raise ErrorNodo(f"{que} ({n}) supera el tope de {LIMITE_ITEMS} ítems.")
    return n


# ================================================================ entradas
@nodo("numero", "Número", "entrada", "Un número fijo o una expresión con parámetros del documento (p. ej. «ancho / 2»).",
      [E("valor", "numero", 0.0, "número o expresión")], [S("valor", "numero")])
def _numero(valor):
    return valor


@nodo("deslizador", "Deslizador", "entrada",
      "Número entre un mínimo y un máximo, con paso opcional (0 = continuo). Un valor fuera del rango se recorta "
      "(con aviso).",
      [E("valor", "numero", 5.0, "valor elegido"), E("minimo", "numero", 0.0), E("maximo", "numero", 10.0),
       E("paso", "numero", 0.0, "redondea al múltiplo más cercano desde el mínimo; 0 = continuo")],
      [S("valor", "numero")])
def _deslizador(valor, minimo, maximo, paso, ctx):
    if maximo < minimo:
        raise ErrorNodo(f"El máximo ({maximo:g}) es menor que el mínimo ({minimo:g}).")
    if paso < 0:
        raise ErrorNodo("El paso no puede ser negativo.")
    v = minimo + round((valor - minimo) / paso) * paso if paso > 0 else valor
    if v < minimo or v > maximo:
        recortado = min(max(v, minimo), maximo)
        ctx.aviso(f"{valor:g} está fuera de [{minimo:g}, {maximo:g}]: se usó {recortado:g}.")
        v = recortado
    return _finito(v)


@nodo("entero", "Entero", "entrada", "Un número entero fijo.", [E("valor", "entero", 1)], [S("valor", "entero")])
def _entero(valor):
    return valor


@nodo("booleano", "Interruptor", "entrada", "Verdadero o falso.", [E("valor", "booleano", False)],
      [S("valor", "booleano")])
def _booleano(valor):
    return valor


@nodo("texto", "Texto", "entrada", "Un texto fijo.", [E("valor", "texto", "")], [S("valor", "texto")])
def _texto(valor):
    return valor


@nodo("punto", "Punto", "entrada", "Un punto fijo [x, y, z] en mm (cada coordenada acepta expresiones).",
      [E("valor", "punto", (0.0, 0.0, 0.0))], [S("valor", "punto")])
def _punto(valor):
    return valor


@nodo("rango", "Rango", "entrada", "Divide el intervalo [inicio, fin] en «pasos» partes iguales: pasos + 1 números.",
      [E("inicio", "numero", 0.0), E("fin", "numero", 1.0), E("pasos", "entero", 10, "partes (≥ 1)")],
      [S("numeros", "numero", acceso="lista")])
def _rango(inicio, fin, pasos):
    _cantidad(pasos + 1, "La cantidad de números", 2)
    return [_finito(inicio + (fin - inicio) * i / pasos) for i in range(pasos + 1)]


@nodo("serie", "Serie", "entrada", "«cantidad» números que empiezan en «inicio» y crecen de a «paso».",
      [E("inicio", "numero", 0.0), E("paso", "numero", 1.0), E("cantidad", "entero", 10)],
      [S("numeros", "numero", acceso="lista")])
def _serie(inicio, paso, cantidad):
    _cantidad(cantidad)
    return [_finito(inicio + paso * i) for i in range(cantidad)]


@nodo("aleatorio", "Aleatorio", "entrada",
      "«cantidad» números al azar entre mínimo y máximo; la misma semilla da siempre los mismos números.",
      [E("minimo", "numero", 0.0), E("maximo", "numero", 1.0), E("cantidad", "entero", 10), E("semilla", "entero", 1)],
      [S("numeros", "numero", acceso="lista")])
def _aleatorio(minimo, maximo, cantidad, semilla):
    _cantidad(cantidad)
    azar = random.Random(semilla)
    return [azar.uniform(minimo, maximo) for _ in range(cantidad)]


@nodo("parametro", "Parámetro", "entrada",
      "El valor de un parámetro del documento (mm, grados o sin unidad, según su tipo): el grafo se recalcula cuando "
      "el parámetro cambia.",
      [E("nombre", "texto", descripcion="nombre exacto del parámetro")], [S("valor", "numero")], usa_contexto=True)
def _parametro(nombre, ctx):
    if nombre not in ctx.parametros:
        raise ErrorNodo(f"No existe el parámetro «{nombre}» en el documento.")
    return float(ctx.parametros[nombre])


# ================================================================ matemática
def _binario(tipo, titulo, descripcion, funcion, a=0.0, b=0.0):
    @nodo(tipo, titulo, "matematica", descripcion, [E("a", "numero", a), E("b", "numero", b)],
          [S("resultado", "numero")])
    def _f(a, b):
        return _finito(funcion(a, b))
    return _f


def _dividir(a, b):
    if b == 0:
        raise ErrorNodo("División por cero.")
    return a / b


def _resto(a, b):
    if b == 0:
        raise ErrorNodo("Resto de una división por cero.")
    return a % b


def _potencia(a, b):
    try:
        r = a ** b
    except (OverflowError, ZeroDivisionError):
        raise ErrorNodo("La potencia no da un número finito.") from None
    if isinstance(r, complex):
        raise ErrorNodo("La potencia no da un número real (base negativa con exponente no entero).")
    return r


_binario("sumar", "Sumar", "a + b.", lambda a, b: a + b)
_binario("restar", "Restar", "a − b.", lambda a, b: a - b)
_binario("multiplicar", "Multiplicar", "a · b.", lambda a, b: a * b, 1.0, 1.0)
_binario("dividir", "Dividir", "a / b (b = 0 es error).", _dividir, 1.0, 1.0)
_binario("potencia", "Potencia", "a elevado a b.", _potencia, 2.0, 2.0)
_binario("resto", "Resto", "Resto de a / b, con el signo de b (como el módulo de Python).", _resto, 1.0, 1.0)
_binario("minimo", "Mínimo", "El menor de a y b.", min)
_binario("maximo", "Máximo", "El mayor de a y b.", max)


@nodo("absoluto", "Valor absoluto", "matematica", "|x|.", [E("x", "numero", 0.0)], [S("resultado", "numero")])
def _absoluto(x):
    return abs(x)


@nodo("redondear", "Redondear", "matematica", "x redondeado a «decimales» decimales.",
      [E("x", "numero", 0.0), E("decimales", "entero", 0)], [S("resultado", "numero")])
def _redondear(x, decimales):
    if not -15 <= decimales <= 15:
        raise ErrorNodo("Los decimales van de −15 a 15.")
    return float(round(x, decimales))


@nodo("seno", "Seno", "matematica", "Seno de un ángulo en grados.", [E("angulo", "numero", 0.0, unidad=ANGULO)],
      [S("resultado", "numero")])
def _seno(angulo):
    return math.sin(math.radians(angulo))


@nodo("coseno", "Coseno", "matematica", "Coseno de un ángulo en grados.", [E("angulo", "numero", 0.0, unidad=ANGULO)],
      [S("resultado", "numero")])
def _coseno(angulo):
    return math.cos(math.radians(angulo))


_COMPARAR = {"<": lambda a, b: a < b, "<=": lambda a, b: a <= b, ">": lambda a, b: a > b, ">=": lambda a, b: a >= b,
             "==": lambda a, b: math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-9),
             "!=": lambda a, b: not math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-9)}


@nodo("comparar", "Comparar", "matematica", "Compara a y b con el operador (<, <=, >, >=, == o !=; == tolera 1e-9).",
      [E("a", "numero", 0.0), E("b", "numero", 0.0), E("operador", "texto", "<")], [S("resultado", "booleano")])
def _comparar(a, b, operador):
    if operador not in _COMPARAR:
        raise ErrorNodo(f"Operador desconocido: «{operador}». Válidos: {', '.join(_COMPARAR)}.")
    return _COMPARAR[operador](a, b)


class _Nombres:
    """x, y, z del nodo y, detrás, los parámetros del documento (sin copiarlos: solo se leen los que se usan)."""

    def __init__(self, locales, globales):
        self.locales, self.globales = locales, globales

    def __contains__(self, nombre):
        return nombre in self.locales or nombre in self.globales

    def __getitem__(self, nombre):
        return self.locales[nombre] if nombre in self.locales else self.globales[nombre]


@nodo("expresion", "Expresión", "matematica",
      "Evalúa una expresión con x, y, z y los parámetros del documento (+ − * / **, sin, cos, tan en grados, sqrt, "
      "abs, min, max, round, floor, ceil, pi; unidades mm, cm, m, in, ft, deg, rad).",
      [E("expresion", "texto", "x"), E("x", "numero", 0.0), E("y", "numero", 0.0), E("z", "numero", 0.0)],
      [S("resultado", "numero")], usa_contexto=True)
def _expresion(expresion, x, y, z, ctx):
    try:
        return evaluar(expresion, ESCALAR, _Nombres({"x": x, "y": y, "z": z}, ctx.parametros))
    except ErrorExpresion as e:
        raise ErrorNodo(f"Expresión «{expresion}»: {e}") from None


@nodo("promedio", "Promedio", "matematica", "Promedio de una lista de números.",
      [E("numeros", "numero", acceso="lista")], [S("resultado", "numero")])
def _promedio(numeros):
    valores = [v for v in numeros if v is not None]
    if not valores:
        raise ErrorNodo("La lista no tiene números.")
    return _finito(math.fsum(valores) / len(valores))


@nodo("total", "Total", "matematica", "Suma de una lista de números (los nulos no cuentan).",
      [E("numeros", "numero", acceso="lista")], [S("resultado", "numero")])
def _total(numeros):
    return _finito(math.fsum(v for v in numeros if v is not None))


# ================================================================ listas
@nodo("largo", "Largo de lista", "listas", "Cantidad de ítems de la lista (los nulos cuentan).",
      [E("lista", acceso="lista")], [S("largo", "entero")])
def _largo(lista):
    return len(lista)


@nodo("item", "Ítem de lista", "listas",
      "El ítem en «indice» (0 = el primero; negativos desde el final). Fuera de rango: nulo con aviso, o da la vuelta "
      "con envolver.",
      [E("lista", acceso="lista"), E("indice", "entero", 0), E("envolver", "booleano", False)], [S("item")])
def _item(lista, indice, envolver, ctx):
    if not lista:
        raise ErrorNodo("La lista está vacía.")
    if envolver:
        return lista[indice % len(lista)]
    if not -len(lista) <= indice < len(lista):
        ctx.aviso(f"El índice {indice} está fuera de la lista (0 a {len(lista) - 1}).")
        return None
    return lista[indice]


@nodo("sublista", "Sublista", "listas",
      "Los ítems desde «inicio» (incluido) hasta «fin» (excluido); negativos cuentan desde el final; sin fin = hasta "
      "el final.",
      [E("lista", acceso="lista"), E("inicio", "entero", 0), E("fin", "entero", None)],
      [S("lista", acceso="lista")])
def _sublista(lista, inicio, fin):
    return lista[inicio:fin]


@nodo("invertir_lista", "Invertir lista", "listas", "La lista al revés.", [E("lista", acceso="lista")],
      [S("lista", acceso="lista")])
def _invertir_lista(lista):
    return list(reversed(lista))


@nodo("ordenar", "Ordenar lista", "listas",
      "Ordena de menor a mayor (números o textos). Con «claves», ordena la lista según esas claves (una por ítem). "
      "Devuelve también los índices originales.",
      [E("lista", acceso="lista"), E("claves", acceso="lista", defecto=None)],
      [S("lista", acceso="lista"), S("indices", "entero", acceso="lista")])
def _ordenar(lista, claves):
    claves = lista if claves is None else claves
    if len(claves) != len(lista):
        raise ErrorNodo(f"Hay {len(claves)} claves para {len(lista)} ítems: tienen que ser la misma cantidad.")
    try:
        orden = sorted(range(len(lista)), key=lambda i: claves[i])
    except TypeError:
        raise ErrorNodo("Solo se ordenan números o textos (sin mezclar ni nulos).") from None
    return [lista[i] for i in orden], orden


@nodo("repetir", "Repetir lista", "listas", "La lista repetida «veces» veces seguidas.",
      [E("lista", acceso="lista"), E("veces", "entero", 2)], [S("lista", acceso="lista")])
def _repetir(lista, veces):
    if veces < 0:
        raise ErrorNodo("«veces» no puede ser negativo.")
    _cantidad(len(lista) * veces, "El largo resultante")
    return list(lista) * veces


@nodo("fusionar", "Fusionar listas", "listas", "Los ítems de a seguidos de los de b.",
      [E("a", acceso="lista"), E("b", acceso="lista", defecto=None)], [S("lista", acceso="lista")])
def _fusionar(a, b):
    return list(a) + list(b or [])


@nodo("filtrar", "Filtrar por patrón", "listas",
      "Deja los ítems cuyo valor del patrón es verdadero; el patrón se repite si es más corto que la lista.",
      [E("lista", acceso="lista"), E("patron", "booleano", acceso="lista", defecto=[True, False])],
      [S("lista", acceso="lista")])
def _filtrar(lista, patron):
    if not patron:
        raise ErrorNodo("El patrón está vacío.")
    return [x for i, x in enumerate(lista) if patron[i % len(patron)]]


@nodo("desplazar", "Desplazar lista", "listas",
      "Corre los ítems «cantidad» lugares hacia el principio (negativo: hacia el final). Con envolver, los que salen "
      "entran por el otro lado; sin envolver se pierden.",
      [E("lista", acceso="lista"), E("cantidad", "entero", 1), E("envolver", "booleano", True)],
      [S("lista", acceso="lista")])
def _desplazar(lista, cantidad, envolver):
    if not lista:
        return []
    if envolver:
        k = cantidad % len(lista)
        return list(lista[k:]) + list(lista[:k])
    return list(lista[cantidad:]) if cantidad >= 0 else list(lista[:cantidad])


# ================================================================ árboles
def _de_arbol(tipo, titulo, descripcion, metodo):
    @nodo(tipo, titulo, "arboles", descripcion, [E("arbol", acceso="arbol")], [S("arbol", acceso="arbol")])
    def _f(arbol):
        return getattr(arbol, metodo)()
    return _f


_de_arbol("aplanar", "Aplanar árbol", "Todos los ítems en una sola rama {0}, en orden de ruta.", "aplanar")
_de_arbol("injertar", "Injertar árbol", "Cada ítem a su propia rama: el ítem i de {a} va a {a;i}.", "injertar")
_de_arbol("simplificar", "Simplificar árbol",
          "Quita los índices iniciales que comparten todas las rutas (cada ruta conserva al menos uno).", "simplificar")
_de_arbol("invertir_matriz", "Invertir matriz",
          "Intercambia filas y columnas: el ítem j de la i-ésima rama pasa a la rama {j}; los huecos quedan nulos.",
          "invertir")


# ================================================================ salida
@nodo("salida", "Salida", "salida",
      "Resultado del grafo con un nombre: run_graph devuelve su valor y bake_graph hornea los cuerpos que lleguen acá.",
      [E("valor", acceso="arbol")], [S("valor", acceso="arbol")])
def _salida(valor):
    return valor


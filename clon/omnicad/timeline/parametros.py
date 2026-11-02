# -*- coding: utf-8 -*-
"""
Parámetros y expresiones con unidades.

Equivalencia con Fusion 360: `UserParameters` + `ValueInput.createByString("10 mm")`
(informe_analisis.md §3.4). Igual que Fusion, hay UNA unidad interna por magnitud
y las expresiones llevan unidades explícitas o toman la unidad por defecto:
  - longitud: milímetros (mm)  — Fusion usa cm internamente; acá mm por STL/STEP e impresión 3D.
  - ángulo:   grados (deg)     — se convierten a radianes solo al llamar al kernel.

Las expresiones las lee un lector propio (nunca eval) con la sintaxis del artículo `Parameters reference`. `evaluar`
tiene dos modos: el común da el valor sin mirar magnitudes, porque una receta vieja con `w * h` en una longitud tiene
que abrir con el mismo valor; `estricto=True` rechaza lo que Fusion rechaza y se usa con lo que se escribe ahora.
"""
import functools
import keyword
import math
import operator
import random
import re
import unicodedata

from .unidades import (ANGULO_DIM, LONGITUD_DIM, SIMBOLOS, SIN_DIMENSION, TABLA, combinar, familia, leer_unidad,
                       texto_dimension)

LONGITUD, ANGULO, ESCALAR, TEXTO, MAGNITUD = "longitud", "angulo", "escalar", "texto", "magnitud"
TIPOS = (LONGITUD, ANGULO, ESCALAR, TEXTO, MAGNITUD)     # MAGNITUD: cualquier otra unidad; calcula, no alimenta pasos
# Topes de lo que puede valer una longitud o un ángulo AL USARSE en un paso (`acotar`, que llama `Contexto.evaluar`;
# T-07 de la prueba de tortura: 1e300 mm y 1e9° pasaban sin error y rompían el modelo en silencio). Un parámetro suelto
# sí puede valer más (las cotas de boceto lo avisan por su cuenta). LONGITUD_MAXIMA es la de las primitivas
# (restricciones.boceto.MEDIDA_MAXIMA: un test comprueba que sean iguales).
LONGITUD_MAXIMA = 1e6           # mm (1 km)
ANGULO_MAXIMO = 1e6             # grados (unas 2.800 vueltas)
TOPE_ANIDADO = 64               # paréntesis y llamadas una dentro de otra

# Factor a la unidad interna de cada magnitud.
UNIDADES = {u: (LONGITUD if d.dim == LONGITUD_DIM else ANGULO, d.factor) for u, d in TABLA.items()
            if d.dim in (LONGITUD_DIM, ANGULO_DIM) and u.isidentifier()}
# Unidades con que el documento MUESTRA longitudes y masas (el modelo trabaja siempre en mm y g): factor a mm / a g.
LONGITUDES = {u: UNIDADES[u][1] for u in ("mm", "cm", "m", "in", "ft")}
MASAS = {"g": 1.0, "kg": 1000.0, "lb": 453.59237}
_POR_TIPO = {LONGITUD: "mm", ANGULO: "deg"}
_CAMPO_TIPO = {LONGITUD: LONGITUD_DIM, ANGULO: ANGULO_DIM}
_CLAVES_ANGULO = {"rx", "ry", "rz", "helice"}
_CLAVES_ESCALAR = {"area_minima", "densidad", "dientes", "dispersion", "escala", "factor", "fx", "fy", "fz", "inicio",
                   "intensidad", "mezcla", "proporcion", "revoluciones", "solidez", "solidez_desfase", "solidez_final"}


def _redondear(v):
    """Fusion: lo que termina en .5 se aleja de cero (B-139)."""
    return math.copysign(math.floor(abs(v) + 0.5), v)


# Sin unidad, un ángulo son grados: sin(45) es 0,7071, como en Fusion.
_DE_ANGULO = {"sin": lambda g: math.sin(math.radians(g)), "cos": lambda g: math.cos(math.radians(g)),
              "tan": lambda g: math.tan(math.radians(g)), "sinh": lambda g: math.sinh(math.radians(g)),
              "cosh": lambda g: math.cosh(math.radians(g)), "tanh": lambda g: math.tanh(math.radians(g))}
_A_ANGULO = {"asin": math.asin, "acos": math.acos, "atan": math.atan, "asinh": math.asinh, "acosh": math.acosh,
             "atanh": math.atanh}
_SIN_UNIDAD = {"exp": math.exp, "ln": math.log, "log": math.log10}
_CONSERVAN = {"abs": abs, "floor": math.floor, "ceil": math.ceil, "round": _redondear,
              "sign": lambda v: 1.0 if v > 0 else 0.0}      # sign(-3) = 0: lo midió Fusion real, no es una errata
FUNCIONES = {*_DE_ANGULO, *_A_ANGULO, *_SIN_UNIDAD, *_CONSERVAN, "sqrt", "min", "max", "pow", "random", "if", "not"}
CONSTANTES = {"pi": math.pi, "PI": math.pi, "E": math.e, "Gravity": 9806.65, "SpeedOfLight": 299792458000.0}
_DIM_CONSTANTE = {"Gravity": leer_unidad("mm/s^2").dim, "SpeedOfLight": leer_unidad("mm/s").dim}
RESERVADOS = set(UNIDADES) | FUNCIONES | set(CONSTANTES)
_COMPARA = {"<": operator.lt, ">": operator.gt, "<=": operator.le, ">=": operator.ge, "==": operator.eq,
            "<>": operator.ne}
_LETRAS_NOMBRE = r"[^\W\d][\w$\"°µ]*"            # Fusion además admite $ " ° y µ dentro del nombre

_NUM_CON_UNIDAD = re.compile(
    r"(?<![\w.])((?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)\s*("
    + "|".join(re.escape(u) for u in sorted(TABLA, key=len, reverse=True)) + r")(?![\w])")
_TOKEN = re.compile(r"\s*(?:(?P<num>(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)|(?P<pal>" + _LETRAS_NOMBRE + r")|"
                    r"(?P<sim>\*\*|<=|>=|==|<>|[-+*/%^()<>;,\"'°˚$]))")


class ErrorExpresion(ValueError):
    """La expresión no se puede evaluar (sintaxis, nombre desconocido, unidades o ciclo)."""


class ErrorMagnitud(ErrorExpresion):
    """La expresión se calcula, pero su magnitud no es la del campo (`w * h` en una longitud)."""


class Magnitud(float):
    """Valor de un parámetro: un número común que además recuerda su dimensión, para `evaluar(estricto=True)`."""

    def __new__(cls, valor, dim=None):
        v = super().__new__(cls, valor)
        v.dim = dim
        return v


def _comas(texto):
    """Pasa a punto las comas decimales. Solo separan argumentos en `min`, `max` y `round` sin `;`, por las recetas
    viejas (`max(w, h)`): con `;` la coma es decimal, como en `max(1,5 mm; 2 mm)`."""
    if "," not in texto:
        return texto
    grupos, abiertos = [[False, False, []]], [0]              # por paréntesis: [separa con comas, tiene «;», comas]
    for i, ch in enumerate(texto):
        if ch == "(":
            previo = re.search(r"(\w+)\s*$", texto[max(0, i - 40):i])       # todo lo anterior sería cuadrático en un archivo hostil
            grupos.append([bool(previo) and previo.group(1) in ("min", "max", "round"), False, []])
            abiertos.append(len(grupos) - 1)
        elif ch == ")" and len(abiertos) > 1:
            abiertos.pop()
        elif ch == ";":
            grupos[abiertos[-1]][1] = True
        elif ch == ",":
            grupos[abiertos[-1]][2].append(i)
    decimales = {i for separa, punto_y_coma, comas in grupos if punto_y_coma or not separa for i in comas}
    return "".join("." if i in decimales else ch for i, ch in enumerate(texto))


def _unidad_final(n):
    """True si `n` termina en una unidad: en «10 mm / s», `s` sigue siendo unidad (salvo que haya un parámetro `s`)."""
    if n[0] == "lit":
        return True
    return n[0] == "bin" and n[1] in "*/" and (n[3][0] == "unidad" or (n[3][0] == "pot" and n[3][1][0] == "unidad"))


class _Lector:
    """Descenso recursivo. Precedencia de `Parameters reference`: paréntesis, ^, signo, * / %, + -; debajo, las
    comparaciones, and y or. Los nodos son tuplas: el árbol se guarda en caché y nunca se modifica."""

    def __init__(self, texto):
        self.texto, self.i, self.anidado = texto, 0, 0
        self.tokens = []
        limpio, pos = texto.rstrip(), 0
        while pos < len(limpio):
            m = _TOKEN.match(limpio, pos)
            if not m:
                raise self.error()
            self.tokens.append((m.lastgroup, m.group(m.lastgroup), m.start(m.lastgroup)))
            pos = m.end()
        self.tokens.append(("fin", "", len(limpio)))

    def error(self):
        return ErrorExpresion(f"Sintaxis inválida: '{self.texto}'.")

    def ver(self, salto=0):
        return self.tokens[min(self.i + salto, len(self.tokens) - 1)]

    def toma(self, *opciones):
        """El token actual si es una de `opciones` (y avanza); si no, None."""
        tipo, valor, _ = self.ver()
        if tipo in ("sim", "pal") and valor in opciones:
            self.i += 1
            return valor
        return None

    def leer(self):
        n = self.o()
        if self.ver()[0] != "fin":
            raise self.error()
        return n

    def _izquierda(self, siguiente, clase, *ops):
        n = siguiente()
        while op := self.toma(*ops):
            n = (clase, op, n, siguiente())
        return n

    def o(self):
        return self._izquierda(self.y, "logica", "or")

    def y(self):
        return self._izquierda(self.comparacion, "logica", "and")

    def comparacion(self):
        return self._izquierda(self.suma, "cmp", "<=", ">=", "==", "<>", "<", ">")

    def suma(self):
        return self._izquierda(self.producto, "bin", "+", "-")

    def producto(self):
        n = self.unario()
        while op := self.toma("*", "/", "%"):
            n = ("bin", op, n, self._divisor() if op != "%" and _unidad_final(n) else self.unario())
        return n

    def _divisor(self):
        """Lo que sigue a «10 mm /»: una unidad suelta (también con ^n) o una expresión común."""
        tipo, valor, _ = self.ver()
        if tipo != "pal" or valor not in TABLA or self.ver(1)[1] == "(":
            return self.unario()
        self.i += 1
        return ("pot", ("unidad", valor), self.unario()) if self.toma("^", "**") else ("unidad", valor)

    def unario(self):
        if op := self.toma("-", "+"):
            n = self.unario()
            return ("neg", n) if op == "-" else n
        return self.potencia()

    def potencia(self):
        n = self.atomo()
        return ("pot", n, self.unario()) if self.toma("^", "**") else n

    def _unidad(self):
        """La unidad escrita justo después de un número: su nombre, o None."""
        tipo, valor, _ = self.ver()
        if tipo in ("pal", "sim") and valor in TABLA:
            self.i += 1
            return valor
        return None

    def atomo(self):
        tipo, valor, inicio = self.ver()
        if tipo == "num":
            self.i += 1
            unidad = self._unidad()
            return ("num", float(valor)) if unidad is None else _literal(float(valor), unidad)
        if valor in ("'", '"') and (fin := self.texto.find(valor, inicio + 1)) >= 0:
            raise ErrorExpresion(f"Expresión no permitida: el texto entre comillas ('{self.texto[inicio + 1:fin]}') "
                                 "no va; escribí la medida sin comillas, p. ej. 60 mm.")
        if tipo == "pal" and valor not in ("and", "or"):
            self.i += 1
            if self.ver()[1] == "(":
                return self._llamada(valor)
            if valor == "not":
                raise self.error()
            unidad = self._unidad() if valor in ("PI", "E") else None      # `PI rad` vale; `w mm` no
            return ("nombre", valor) if unidad is None else ("bin", "*", ("nombre", valor), _literal(1.0, unidad))
        if self.toma("("):
            n = self._adentro()
            if not self.toma(")"):
                raise self.error()
            return n
        raise self.error()

    def _adentro(self):
        self.anidado += 1
        if self.anidado > TOPE_ANIDADO:
            raise ErrorExpresion(f"La expresión tiene demasiados niveles de paréntesis (el tope es {TOPE_ANIDADO}).")
        n = self.o()
        self.anidado -= 1
        return n

    def _llamada(self, nombre):
        if nombre not in FUNCIONES:
            raise ErrorExpresion(f"Función desconocida: '{nombre}'.")
        self.toma("(")
        args = []
        if not self.toma(")"):
            args.append(self._adentro())
            while self.toma(";", ","):
                args.append(self._adentro())
            if not self.toma(")"):
                raise self.error()
        return ("fn", nombre, tuple(args))


def _literal(valor, unidad):
    u = TABLA[unidad]
    return ("lit", u.a_interno(valor), u.dim, unidad)


class _Calculo:
    """Lo que no cambia durante una evaluación."""

    def __init__(self, nombres, estricto, campo, dimensiones):
        self.nombres, self.estricto, self.campo = nombres, estricto, campo
        self.dimensiones = dimensiones       # los nombres aportan su magnitud; apagado, en recetas viejas

    def adoptar(self, v, dim):
        """Un número suelto toma la unidad del campo: `10 mm + 2` en mm es `10 mm + 2 mm`."""
        return self.campo.a_interno(v) if dim == self.campo.dim else v

    def exigir(self, dim, validas, que):
        if self.estricto and dim is not None and dim not in validas:
            raise ErrorMagnitud(f"Las unidades no coinciden: {que}, y esto es {familia(dim)}.")


def _alinear(a, b, c, que):
    """Dos valores que tienen que ser de la misma magnitud. Un número suelto adopta la del otro."""
    (va, da), (vb, db) = a, b
    if da is None and db is not None:
        return c.adoptar(va, db), vb, db
    if db is None and da is not None:
        return va, c.adoptar(vb, da), da
    if c.estricto and da != db:
        raise ErrorMagnitud(f"Las unidades no coinciden: {que} {familia(da)} y {familia(db)}.")
    return va, vb, da


def _dim_producto(da, db, signo):
    if da is None and db is None:
        return None
    return combinar(SIN_DIMENSION if da is None else da, SIN_DIMENSION if db is None else db, signo)


def _binaria(op, a, b, c):
    if op in ("+", "-", "%"):
        va, vb, dim = _alinear(a, b, c, "no se pueden combinar")
        if op == "%":
            return math.fmod(va, vb), dim
        return (va + vb if op == "+" else va - vb), dim
    if op == "*":
        return a[0] * b[0], _dim_producto(a[1], b[1], 1)
    return a[0] / b[0], _dim_producto(a[1], b[1], -1)


def _nombre(n, c):
    if n in ("pi", "PI"):
        return math.pi, None
    if n in c.nombres:
        v = c.nombres[n]
        if isinstance(v, str):
            raise ErrorExpresion(f"El parámetro '{n}' es de texto: no se puede usar en una expresión numérica.")
        return v, getattr(v, "dim", None) if c.dimensiones else None
    if n in CONSTANTES:                 # después de los nombres: un parámetro viejo `E` gana sobre la constante
        return CONSTANTES[n], _DIM_CONSTANTE.get(n)
    raise ErrorExpresion(f"Nombre desconocido: '{n}'.")


def _calc(n, c):
    """(valor en unidades internas, dimensión); dimensión None = número suelto, que adopta la que le toque."""
    clase = n[0]
    if clase == "num":
        return n[1], None
    if clase == "lit":
        return n[1], n[2]
    if clase == "nombre":
        return _nombre(n[1], c)
    if clase == "neg":
        v, d = _calc(n[1], c)
        return -v, d
    if clase == "unidad":
        return _nombre(n[1], c) if n[1] in c.nombres else (TABLA[n[1]].factor, TABLA[n[1]].dim)
    if clase == "bin":
        a, b = _calc(n[2], c), _calc(n[3], c)
        try:
            v, d = _binaria(n[1], a, b, c)
        except ErrorExpresion:
            raise
        except (ZeroDivisionError, ValueError):       # fmod(x, 0) es ValueError
            raise ErrorExpresion("División por cero.") from None
        except OverflowError:
            raise ErrorExpresion("El resultado es demasiado grande o no es un número real.") from None
        return _real(v), d
    if clase == "pot":
        return _potencia(_calc(n[1], c), _calc(n[2], c), c)
    if clase == "cmp":
        va, vb, _ = _alinear(_calc(n[2], c), _calc(n[3], c), c, "no se pueden comparar")
        return float(_COMPARA[n[1]](va, vb)), None
    if clase == "logica":
        a = _calc(n[2], c)[0] != 0
        if a == (n[1] == "or"):                       # `1 or x` y `0 and x` no necesitan a x
            return float(a), None
        return float(_calc(n[3], c)[0] != 0), None
    return _funcion(n[1], n[2], c)


def _potencia(base, exponente, c):
    (v, d), (e, de) = base, exponente
    c.exigir(de, (SIN_DIMENSION,), "el exponente no lleva unidad")
    try:
        r = _real(v ** e)
    except ZeroDivisionError:
        raise ErrorExpresion("División por cero.") from None
    except OverflowError:
        raise ErrorExpresion("El resultado es demasiado grande o no es un número real.") from None
    return r, None if d is None else tuple(x * e for x in d)


def _funcion(nombre, nodos, c):
    if nombre == "if":
        if len(nodos) != 3:
            raise ErrorExpresion("if necesita 3 argumentos separados con ';': if(condición; si es cierto; si es falso).")
        return _calc(nodos[1] if _calc(nodos[0], c)[0] != 0 else nodos[2], c)
    args = [_calc(a, c) for a in nodos]
    if nombre in ("min", "max"):
        if len(args) < 2:
            raise ErrorExpresion(f"{nombre} necesita 2 argumentos o más: {nombre}(a; b).")
        return _extremo(nombre, args, c)
    if nombre == "random":
        if args:
            raise ErrorExpresion("random no lleva argumentos: random().")
        return random.random(), None
    if nombre == "pow":
        if len(args) != 2:
            raise ErrorExpresion("pow necesita 2 argumentos: pow(base; exponente).")
        return _potencia(args[0], args[1], c)
    if nombre == "round" and len(args) == 2:          # round(x, n) de las recetas viejas
        return _real(round(args[0][0], int(args[1][0]))), args[0][1]
    if len(args) != 1:
        raise ErrorExpresion(f"{nombre} necesita un solo argumento.")
    return _de_un_argumento(nombre, *args[0], c)


def _de_un_argumento(nombre, v, d, c):
    try:
        if nombre == "not":
            return float(v == 0), None
        if nombre == "sqrt":
            return _real(math.sqrt(v)), None if d is None else tuple(x / 2 for x in d)
        if nombre in _DE_ANGULO:
            c.exigir(d, (ANGULO_DIM, SIN_DIMENSION), f"{nombre} espera un ángulo")
            return _real(_DE_ANGULO[nombre](v)), SIN_DIMENSION
        if nombre in _CONSERVAN:
            return _real(_CONSERVAN[nombre](v)), d
        c.exigir(d, (SIN_DIMENSION,), f"{nombre} espera un número sin unidad")
        if nombre in _A_ANGULO:
            return _real(math.degrees(_A_ANGULO[nombre](v))), ANGULO_DIM
        return _real(_SIN_UNIDAD[nombre](v)), None
    except ErrorExpresion:
        raise
    except (ValueError, OverflowError):
        raise ErrorExpresion(f"{nombre}() no da un número real con ese valor.") from None


def _extremo(nombre, args, c):
    v, d = args[0]
    elegir = max if nombre == "max" else min
    for otro in args[1:]:
        v1, v2, d = _alinear((v, d), otro, c, "no se pueden comparar")
        v = elegir(v1, v2)
    return v, d


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


def acotar(valor, tipo):
    """El valor, si cabe en el tope de su magnitud (LONGITUD_MAXIMA, ANGULO_MAXIMO); si no, ErrorExpresion."""
    if tipo == LONGITUD and abs(valor) > LONGITUD_MAXIMA:
        raise ErrorExpresion(f"La longitud ({valor:g} mm) pasa de {LONGITUD_MAXIMA:,.0f} mm (1 km): más grande, el "
                             "núcleo geométrico ya no calcula bien.".replace(",", "."))
    if tipo == ANGULO and abs(valor) > ANGULO_MAXIMO:
        raise ErrorExpresion(f"El ángulo ({valor:g}°) pasa de {ANGULO_MAXIMO:,.0f}°.".replace(",", "."))
    return valor


def unidad_de(tipo, unidad=None):
    """La Unidad de un campo: la escrita, o la interna de su tipo."""
    try:
        return leer_unidad(unidad if unidad is not None else _POR_TIPO.get(tipo, ""))
    except ValueError as e:
        raise ErrorExpresion(str(e)) from None


def tipo_de_unidad(unidad):
    """El tipo de un parámetro según su unidad: «text» es texto; sin unidad, escalar; mm o deg alimentan pasos."""
    if unidad.strip().lower() == "text":
        return TEXTO
    return {LONGITUD_DIM: LONGITUD, ANGULO_DIM: ANGULO, SIN_DIMENSION: ESCALAR}.get(unidad_de(MAGNITUD, unidad).dim, MAGNITUD)


def tipo_de_clave(clave, expresion):
    """Magnitud de un valor de un paso, por el nombre de su clave en `Operacion.p`. Si la expresión escribe otra unidad
    (una clave con nombre poco claro), manda la expresión."""
    if clave in _CLAVES_ANGULO or clave.startswith(("angulo", "conicidad", "giro", "torsion")):
        regla = ANGULO
    else:
        regla = ESCALAR if clave in _CLAVES_ESCALAR else LONGITUD
    for tipo in (regla, ANGULO, LONGITUD, ESCALAR):
        try:
            if tipo == ESCALAR or not _compilar(str(expresion).strip(), tipo)[1]:
                return tipo
        except ErrorExpresion:
            break
    return regla


def evaluar(expr, tipo=LONGITUD, nombres=None, estricto=False, unidad=None):
    """Evalúa `expr` y devuelve el valor en la unidad interna de `tipo`. `unidad`: la del parámetro o campo, si no es
    la interna; los números sueltos la toman. `estricto`: además exige la magnitud del campo, como Fusion."""
    if tipo not in TIPOS:
        raise ValueError(f"tipo inválido: {tipo}")
    if tipo == TEXTO:
        return str(expr)
    if isinstance(expr, (int, float)):
        return float(expr)
    texto = (expr or "").strip()
    if not texto:
        raise ErrorExpresion("Expresión vacía.")
    arbol, ajena = _compilar(texto, tipo)
    if ajena and not estricto:
        raise ErrorExpresion(ajena)
    c = _Calculo(nombres or {}, estricto, unidad_de(tipo, unidad), estricto or unidad is not None)
    try:
        v, dim = _calc(arbol, c)
    except RecursionError:
        raise ErrorExpresion("La expresión es demasiado larga.") from None
    return _real(_en_el_campo(v, dim, c))


def _en_el_campo(v, dim, c):
    campo = c.campo
    if dim is None or (dim == SIN_DIMENSION and campo.dim != SIN_DIMENSION):
        return campo.a_interno(v)                # `w / h` en mm vale `( w / h ) * 1 mm`
    if c.estricto and dim != campo.dim:
        raise ErrorMagnitud(f"La unidad '{texto_dimension(dim)}' es de {familia(dim)}, se esperaba {familia(campo.dim)}.")
    return v


def _unidad_ajena(n, tipo):
    """Sin mirar magnitudes, lo único que se rechaza es una unidad escrita de otra magnitud (`10 deg` en una longitud),
    fuera de la trigonometría: `sin(30 deg) * 2` es una longitud. Devuelve el mensaje, si la hay."""
    if n[0] == "lit":
        if n[2] == _CAMPO_TIPO[tipo]:
            return None
        return f"La unidad '{SIMBOLOS.get(n[3], n[3])}' es de {familia(n[2])}, se esperaba {familia(_CAMPO_TIPO[tipo])}."
    if n[0] == "fn" and n[1] in _DE_ANGULO:
        return None
    hijos = n[2] if n[0] == "fn" else [x for x in n[1:] if isinstance(x, tuple)]
    return next(filter(None, (_unidad_ajena(h, tipo) for h in hijos)), None)


@functools.lru_cache(maxsize=4096)
def _compilar(texto, tipo):
    """(árbol, mensaje de `_unidad_ajena`). Con caché: al arrastrar un boceto se evalúan las mismas cotas en cada evento
    del ratón y leer el texto era lo que más costaba. Un «nombre=» adelante no es parte de la expresión (PAR-9)."""
    if "=" in texto:
        texto = separar_nombre(texto)[1]
    try:
        arbol = _Lector(_comas(texto)).leer()
        return arbol, _unidad_ajena(arbol, tipo) if tipo in _CAMPO_TIPO else None
    except RecursionError:
        raise ErrorExpresion("La expresión es demasiado larga.") from None


def con_unidad(expr):
    """True si `expr` escribe un número con unidad («2 mm», «30°»)."""
    return _NUM_CON_UNIDAD.search(str(expr)) is not None


def _nombres_en(n, salida):
    if n[0] in ("nombre", "unidad"):
        salida.add(n[1])
    for hijo in n[2] if n[0] == "fn" else n[1:]:
        if isinstance(hijo, tuple):
            _nombres_en(hijo, salida)


def nombres_usados(expr):
    """Nombres de parámetros que aparecen en una expresión (sin unidades ni funciones)."""
    salida = set()
    try:
        _nombres_en(_compilar(str(expr), ESCALAR)[0], salida)
    except (ErrorExpresion, RecursionError):
        return set()
    return salida - {"pi", "PI"}


def renombrar_en(expr, viejo, nuevo):
    """`expr` con el parámetro `viejo` llamado `nuevo`. Una función (`min(`) o una unidad (`5 min`) no es el nombre."""
    def cambiar(m):
        antes = expr[:m.start()].rstrip()
        return m.group() if antes[-1:].isdigit() or antes[-1:] == "." else nuevo
    fuera = r"\w$\"°µ"
    return re.sub(rf"(?<![{fuera}.]){re.escape(viejo)}(?![{fuera}])(?!\s*\()", cambiar, str(expr))


def separar_nombre(texto):
    """«ANCHO=20mm» → ("ANCHO", "20mm"); sin «nombre=» → (None, texto). El «==» no cuenta como asignación."""
    m = re.match(r"\s*(" + _LETRAS_NOMBRE + r")\s*=(?!=)\s*(.*)$", str(texto), re.S)
    return (m.group(1), m.group(2)) if m else (None, texto)


def validar_nombre(nombre):
    """Como en Fusion, un nombre de parámetro tiene letras (también ñ y acentos), dígitos, «_», «$», «"», «°» y «µ», sin
    empezar con dígito. Se exige la forma compuesta: «ñ» escrita como n + tilde combinada no se encontraría nunca."""
    if isinstance(nombre, str) and unicodedata.normalize("NFC", nombre) != nombre:
        raise ErrorExpresion(f"Nombre de parámetro inválido: '{nombre}': tiene letras escritas como letra + marca "
                             f"combinada (p. ej. n + tilde); escribilo con las letras compuestas: "
                             f"'{unicodedata.normalize('NFC', nombre)}'.")
    if not (isinstance(nombre, str) and re.fullmatch(_LETRAS_NOMBRE, nombre)):
        raise ErrorExpresion(f"Nombre de parámetro inválido: '{nombre}'. Puede tener letras (también con acento y ñ), "
                             "números, '_', '$', '\"', '°' y 'µ', y no empezar con un número.")
    if keyword.iskeyword(nombre):
        raise ErrorExpresion(f"'{nombre}' es una palabra reservada (unidad, función o palabra de Python).")
    if nombre in RESERVADOS:
        raise ErrorExpresion(f"'{nombre}' es una palabra reservada (unidad o función).")


def texto_con_valores(texto, valores):
    """Texto con sus {expresión} reemplazadas por el valor que tienen con los parámetros `valores` (longitudes
    en mm, ángulos en grados, números sueltos o cadenas literales). Levanta ErrorExpresion si alguna no se puede calcular."""
    from ..restricciones.boceto import sustituir_expresiones

    def valor(expr):
        if expr in valores and isinstance(valores[expr], str):
            return valores[expr]
        ultimo = None
        for tipo in (LONGITUD, ANGULO, ESCALAR):
            try:
                return evaluar(expr, tipo, valores)
            except ErrorExpresion as e:
                ultimo = ultimo or e
        raise ultimo
    try:
        return sustituir_expresiones(texto, valor)
    except ValueError as e:                       # formato inválido: «{ancho:xyz}»
        if isinstance(e, ErrorExpresion):
            raise
        raise ErrorExpresion(f"Formato de número inválido en el texto: {e}") from e


def texto_resuelto(texto, valores):
    """Lo que se muestra de un parámetro de texto: una {llave} que no se puede calcular deja el texto como estaba.
    shortcut: resuelve un nivel, igual que el texto del boceto; un texto que cita a otro con llaves muestra esas llaves."""
    try:
        return texto_con_valores(texto, valores)
    except ErrorExpresion:
        return texto


def _nombres_de(p):
    """Los parámetros que usa `p`; en uno de texto, los de sus {llaves}."""
    if p.tipo != TEXTO:
        return nombres_usados(p.expresion)
    if "{" not in p.expresion:
        return set()
    from ..restricciones.boceto import expresiones_de_texto
    return {n for e in expresiones_de_texto(p.expresion) for n in nombres_usados(e)}


class Parametro:
    """`unidad`: la que eligió la persona si no es la interna de `tipo`. `op` y `clave`: de qué paso del timeline es
    este parámetro del modelo (la expresión vive en el paso; acá hay una copia para citarla y listarla)."""

    def __init__(self, nombre, expresion, tipo=LONGITUD, comentario="", unidad=None, favorito=False, op=None, clave=None):
        self.nombre, self.expresion, self.tipo, self.comentario = nombre, str(expresion), tipo, comentario
        self.unidad = unidad if isinstance(unidad, str) else None
        self.favorito, self.op, self.clave = bool(favorito), op, clave

    @property
    def texto_unidad(self):
        return "text" if self.tipo == TEXTO else _POR_TIPO.get(self.tipo, "") if self.unidad is None else self.unidad

    def a_dict(self):
        d = {"nombre": self.nombre, "expresion": self.expresion, "tipo": self.tipo, "comentario": self.comentario}
        extras = {"unidad": self.unidad, "favorito": self.favorito or None, "op": self.op, "clave": self.clave}
        return d | {k: v for k, v in extras.items() if v is not None}     # una receta sin nada de esto queda como antes


class TablaParametros:
    """Parámetros de usuario y del modelo. Pueden referirse unos a otros; se detectan ciclos."""

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

    def _exigir_libre(self, nombre):
        validar_nombre(nombre)
        if nombre.casefold() in {n.casefold() for n in self._params}:      # Fusion: `w` y `W` chocan
            raise ErrorExpresion(f"Ya existe el parámetro '{nombre}'.")

    def validar(self, nombre):
        """Lo que se escribe ahora tiene que dar la magnitud de su unidad; lo que vino en una receta, no (`desde_lista`)."""
        p, valores = self._params[nombre], self.valores()
        if p.tipo != TEXTO:
            evaluar(p.expresion, p.tipo, valores, estricto=True, unidad=p.unidad)

    def agregar(self, nombre, expresion, tipo=LONGITUD, comentario="", unidad=None, favorito=False):
        self._exigir_libre(nombre)
        if tipo not in TIPOS:
            raise ErrorExpresion(f"Tipo inválido: {tipo}")
        self._params[nombre] = Parametro(nombre, expresion, tipo, comentario, unidad, favorito)
        try:
            self.validar(nombre)
        except ErrorExpresion:
            del self._params[nombre]
            raise

    def modificar(self, nombre, expresion=None, comentario=None, unidad=None, favorito=None):
        """`unidad` cambia también el tipo. Una expresión o unidad nuevas se validan; el resto no toca el valor."""
        p = self._params[nombre]
        anterior = p.expresion, p.tipo, p.unidad
        if expresion is not None:
            p.expresion = str(expresion)
        if comentario is not None:
            p.comentario = comentario
        if favorito is not None:
            p.favorito = bool(favorito)
        if unidad is not None:
            p.tipo, p.unidad = tipo_de_unidad(unidad), None if unidad.strip().lower() == "text" else unidad.strip()
        try:
            if expresion is not None or unidad is not None:
                self.validar(nombre)
        except ErrorExpresion:
            p.expresion, p.tipo, p.unidad = anterior
            raise

    def renombrar(self, viejo, nuevo):
        """Cambia el nombre y lo actualiza en las expresiones de la tabla (B-140)."""
        p = self._params[viejo]
        otros = TablaParametros()
        otros._params = {n: x for n, x in self._params.items() if n != viejo}
        otros._exigir_libre(nuevo)
        p.nombre = nuevo
        self._params = {(nuevo if n == viejo else n): x for n, x in self._params.items()}
        for x in self._params.values():
            x.expresion = renombrar_en_texto(x.expresion, viejo, nuevo) if x.tipo == TEXTO else renombrar_en(x.expresion, viejo, nuevo)

    def eliminar(self, nombre):
        usuarios = [p.nombre for p in self._params.values() if p.nombre != nombre and nombre in _nombres_de(p)]
        if usuarios:
            raise ErrorExpresion(f"No se puede borrar '{nombre}': lo usan {', '.join(usuarios)}.")
        del self._params[nombre]

    def valores(self):
        """Resuelve todos los parámetros (orden topológico). Lanza ErrorExpresion ante ciclos. Con caché por el
        contenido de la tabla (nombre, expresión, tipo): el editor de bocetos lo pide por cada cota en cada evento."""
        clave = tuple((p.nombre, p.expresion, p.tipo, p.unidad) for p in self._params.values())
        if getattr(self, "_memo", (None,))[0] != clave:
            self._memo = (clave, self._resolver_todos())
        return dict(self._memo[1])

    def _resolver_todos(self):
        resueltos, en_curso = {}, set()

        def resolver(nombre):
            if nombre in resueltos:
                return resueltos[nombre]
            if nombre in en_curso:
                raise ErrorExpresion(f"Referencia circular en el parámetro '{nombre}'.")
            en_curso.add(nombre)
            try:
                p = self._params[nombre]
                resueltos[nombre] = p.expresion if p.tipo == TEXTO else numero(p)
            finally:
                en_curso.discard(nombre)
            return resueltos[nombre]

        def numero(p):
            deps = {n: resolver(n) for n in nombres_usados(p.expresion) if n in self._params}
            return Magnitud(evaluar(p.expresion, p.tipo, deps, unidad=p.unidad), unidad_de(p.tipo, p.unidad).dim)

        for nombre, p in self._params.items():
            try:
                resolver(nombre)
            except ErrorExpresion:
                if p.op is None:      # un paso con una expresión mala falla él solo, no deja al documento sin parámetros
                    raise
        return resueltos

    def evaluar(self, expr, tipo=LONGITUD, estricto=False):
        return evaluar(expr, tipo, self.valores(), estricto)

    def a_lista(self):
        return [p.a_dict() for p in self._params.values()]

    @classmethod
    def desde_lista(cls, datos):
        t = cls()
        for d in datos or []:
            t._params[d["nombre"]] = Parametro(d["nombre"], d["expresion"], d.get("tipo", LONGITUD), d.get("comentario", ""),
                                               d.get("unidad"), d.get("favorito", False), d.get("op"), d.get("clave"))
        t.valores()
        return t


def renombrar_en_texto(texto, viejo, nuevo):
    """Lo mismo que `renombrar_en`, solo dentro de las {llaves} de un texto."""
    return re.sub(r"\{([^{}]*)\}", lambda m: "{" + renombrar_en(m.group(1), viejo, nuevo) + "}", texto)

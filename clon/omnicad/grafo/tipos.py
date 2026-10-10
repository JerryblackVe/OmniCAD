# -*- coding: utf-8 -*-
"""
Tipos de dato de los puertos del grafo (GH3) y su conversión.

Cada puerto declara un tipo de dato y un acceso:
  - tipos: numero, entero, booleano, texto, punto, vector, plano, curva, cuerpo, cualquiera;
  - acceso: "item" (el nodo corre una vez por ítem), "lista" (recibe la rama entera como lista) o "arbol" (recibe el
    árbol entero). Así las listas y los árboles también son «tipos» de puerto, como en Grasshopper.

Representación en Python (sin OpenCascade en este módulo):
  - numero: float (mm, grados o sin unidad, según el puerto); entero: int; booleano: bool; texto: str;
  - punto y vector: tupla (x, y, z) de floats;
  - plano: `Plano` (origen y ejes x, y, z unitarios);
  - curva: `Curva` (primitivas 2D de boceto sobre un plano; se vuelve aristas OCC recién en un nodo de geometría);
  - cuerpo: la forma de OpenCascade (TopoDS_Shape) tal cual.

`convertir` acepta lo que llega por un cable o desde el JSON: números como texto o expresiones con parámetros
(«ancho / 2»), puntos como listas [x, y, z] (también con expresiones), planos por nombre ("XY", "XZ", "YZ"), etc.
"""
import math
from collections import namedtuple

from ..timeline.parametros import ANGULO, ESCALAR, LONGITUD, ErrorExpresion, evaluar

TIPOS = {
    "numero": "número real (mm, grados o sin unidad según el puerto)",
    "entero": "número entero",
    "booleano": "verdadero o falso",
    "texto": "texto",
    "punto": "punto [x, y, z] en mm",
    "vector": "vector [x, y, z]",
    "plano": "plano: \"XY\", \"XZ\", \"YZ\" o {\"origen\", \"normal\", \"eje_x\"}",
    "curva": "curva plana (línea, círculo, rectángulo…)",
    "cuerpo": "cuerpo sólido de OpenCascade",
    "cualquiera": "cualquier dato",
}
ACCESOS = {"item": "un ítem por vuelta", "lista": "la rama entera como lista", "arbol": "el árbol entero"}
UNIDADES = {LONGITUD: "mm", ANGULO: "grados", ESCALAR: "sin unidad"}
LIMITE_ITEMS = 100_000          # tope de ítems que puede generar un nodo (rango, serie, grilla…)


class ErrorTipo(ValueError):
    """Un dato que no se puede convertir al tipo del puerto."""


def _finito(v, que="El valor"):
    v = float(v)
    if not math.isfinite(v):
        raise ErrorTipo(f"{que} no es un número finito.")
    return v


def _norma(v):
    return math.sqrt(sum(c * c for c in v))


def _unitario(v, que="La dirección"):
    n = _norma(v)
    if n < 1e-12:
        raise ErrorTipo(f"{que} no puede ser el vector nulo.")
    return tuple(c / n for c in v)


def _cruz(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _punto_de(d, z=0.0):
    return (float(d[0]), float(d[1]), float(z if len(d) == 2 else d[2]))


class Plano(namedtuple("Plano", "origen x y z")):
    """Plano del grafo: origen y ejes x, y, z (normal) unitarios y ortogonales, como tuplas."""

    NOMBRES = {"XY": ((0, 0, 1), (1, 0, 0)), "XZ": ((0, -1, 0), (1, 0, 0)), "YZ": ((1, 0, 0), (0, 1, 0))}

    @classmethod
    def desde(cls, origen=(0.0, 0.0, 0.0), normal=(0.0, 0.0, 1.0), eje_x=None):
        """Plano por un punto con una normal; `eje_x` (opcional) se proyecta sobre el plano. Sin él, se elige uno
        perpendicular a la normal (el X global si se puede)."""
        z = _unitario(normal, "La normal del plano")
        x = None
        if eje_x is not None:
            d = sum(a * b for a, b in zip(eje_x, z, strict=True))
            x = tuple(a - d * b for a, b in zip(eje_x, z, strict=True))
            if _norma(x) < 1e-9:
                x = None
        if x is None:
            ref = (1.0, 0.0, 0.0) if abs(z[0]) < 0.9 else (0.0, 1.0, 0.0)
            d = sum(a * b for a, b in zip(ref, z, strict=True))
            x = tuple(a - d * b for a, b in zip(ref, z, strict=True))
        x = _unitario(x)
        y = _cruz(z, x)
        return cls(_punto_de(origen), x, y, z)

    @classmethod
    def de_nombre(cls, nombre, origen=(0.0, 0.0, 0.0)):
        clave = str(nombre).strip().upper()
        if clave not in cls.NOMBRES:
            raise ErrorTipo(f"Plano desconocido: «{nombre}» (van XY, XZ o YZ).")
        normal, u = cls.NOMBRES[clave]
        return cls.desde(origen, normal, u)

    def punto(self, u, v, w=0.0):
        """Punto de coordenadas (u, v, w) en el sistema del plano."""
        return tuple(o + u * a + v * b + w * c for o, a, b, c in zip(self.origen, self.x, self.y, self.z, strict=True))

    def a_json(self):
        return {"origen": list(self.origen), "normal": list(self.z), "eje_x": list(self.x)}


class Curva:
    """Curva plana: primitivas 2D con el formato de `Boceto.geometria()` (("linea", id, (u1, v1), (u2, v2)),
    ("circulo", id, (cu, cv), r), ("arco", id, (cu, cv), r, a0, a1)) sobre un `Plano`. `cerrada` dice si encierra
    una región (se puede extruir)."""

    __slots__ = ("plano", "primitivas", "cerrada", "descripcion")

    def __init__(self, plano, primitivas, cerrada, descripcion="curva"):
        self.plano, self.primitivas, self.cerrada, self.descripcion = plano, tuple(primitivas), bool(cerrada), descripcion

    def __repr__(self):
        return f"Curva({self.descripcion}, cerrada={self.cerrada})"


def es_forma(valor):
    """True si `valor` es una forma de OpenCascade (sin importar OCP)."""
    return hasattr(valor, "ShapeType") and hasattr(valor, "IsNull")


# ---------------------------------------------------------------- conversión
def _numero(v, unidad, parametros):
    if isinstance(v, bool):
        return 1.0 if v else 0.0
    if isinstance(v, (int, float)) or hasattr(v, "__float__") and not isinstance(v, (str, tuple, list)):
        try:
            return _finito(v)
        except (TypeError, ValueError):
            pass
    if isinstance(v, str):
        try:
            return evaluar(v, unidad, parametros or {})
        except ErrorExpresion as e:
            raise ErrorTipo(f"«{v}» no es un número ni una expresión válida: {e}") from None
    raise ErrorTipo(f"Se esperaba un número y llegó {_describir(v)}.")


def _entero(v, unidad, parametros):
    x = _numero(v, ESCALAR, parametros)
    if abs(x) > 1e12:
        raise ErrorTipo(f"El entero {x:g} es demasiado grande.")
    return int(round(x))


_VERDADEROS = {"true", "verdadero", "si", "sí", "1", "yes"}
_FALSOS = {"false", "falso", "no", "0"}


def _booleano(v, unidad, parametros):
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return v != 0
    if isinstance(v, str):
        t = v.strip().casefold()
        if t in _VERDADEROS:
            return True
        if t in _FALSOS:
            return False
    raise ErrorTipo(f"Se esperaba verdadero o falso y llegó {_describir(v)}.")


def _texto(v, unidad, parametros):
    if isinstance(v, str):
        return v
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, float):
        return str(int(v)) if v.is_integer() and abs(v) < 1e15 else repr(v)
    if isinstance(v, tuple) and len(v) == 3 and all(isinstance(c, float) for c in v):
        return "(" + ", ".join(_texto(c, unidad, parametros) for c in v) + ")"
    return str(v)


def _coordenadas(v, parametros, que):
    if isinstance(v, Plano):
        return v.origen
    if isinstance(v, (list, tuple)) and len(v) in (2, 3) and not any(isinstance(c, (list, tuple, dict)) for c in v):
        try:
            return _punto_de([_numero(c, LONGITUD if isinstance(c, str) else ESCALAR, parametros) for c in v])
        except ErrorTipo as e:
            raise ErrorTipo(f"Coordenada inválida en {que}: {e}") from None
    if hasattr(v, "tolist") and not isinstance(v, (str, bytes)):         # numpy
        return _coordenadas(v.tolist(), parametros, que)
    if isinstance(v, dict) and set(v) <= {"x", "y", "z"} and v:
        return _coordenadas([v.get("x", 0.0), v.get("y", 0.0), v.get("z", 0.0)], parametros, que)
    raise ErrorTipo(f"Se esperaba {que} [x, y, z] y llegó {_describir(v)}.")


def _punto(v, unidad, parametros):
    return _coordenadas(v, parametros, "un punto")


def _vector(v, unidad, parametros):
    return _coordenadas(v, parametros, "un vector")


def _plano(v, unidad, parametros):
    if isinstance(v, Plano):
        return v
    if isinstance(v, str):
        return Plano.de_nombre(v)
    if isinstance(v, dict):
        desconocidas = set(v) - {"origen", "normal", "eje_x", "nombre"}
        if desconocidas:
            raise ErrorTipo(f"Claves desconocidas en el plano: {', '.join(sorted(desconocidas))} "
                            "(van origen, normal, eje_x o nombre).")
        origen = _coordenadas(v.get("origen", (0, 0, 0)), parametros, "el origen del plano")
        if "nombre" in v:
            return Plano.de_nombre(v["nombre"], origen)
        normal = _coordenadas(v.get("normal", (0, 0, 1)), parametros, "la normal del plano")
        eje_x = _coordenadas(v["eje_x"], parametros, "el eje x del plano") if v.get("eje_x") is not None else None
        return Plano.desde(origen, normal, eje_x)
    if isinstance(v, (list, tuple)) and len(v) == 3:                       # un punto: plano XY por ese punto
        return Plano.de_nombre("XY", _coordenadas(v, parametros, "un punto"))
    raise ErrorTipo(f"Se esperaba un plano y llegó {_describir(v)}.")


def _curva(v, unidad, parametros):
    if isinstance(v, Curva):
        return v
    raise ErrorTipo(f"Se esperaba una curva y llegó {_describir(v)}.")


def _cuerpo(v, unidad, parametros):
    if es_forma(v):
        if v.IsNull():
            raise ErrorTipo("El cuerpo está vacío.")
        return v
    raise ErrorTipo(f"Se esperaba un cuerpo y llegó {_describir(v)}.")


def _cualquiera(v, unidad, parametros):
    return v


_CONVERSORES = {"numero": _numero, "entero": _entero, "booleano": _booleano, "texto": _texto, "punto": _punto,
                "vector": _vector, "plano": _plano, "curva": _curva, "cuerpo": _cuerpo, "cualquiera": _cualquiera}


def convertir(valor, tipo, unidad=ESCALAR, parametros=None):
    """`valor` convertido al `tipo` del puerto (None queda None). Los textos en puertos numéricos se evalúan como
    expresiones con los `parametros` del documento en la `unidad` del puerto. Lanza ErrorTipo."""
    if valor is None:
        return None
    try:
        return _CONVERSORES[tipo](valor, unidad, parametros)
    except KeyError:
        raise ErrorTipo(f"Tipo de puerto desconocido: {tipo}") from None


def _describir(v):
    if isinstance(v, (Curva, Plano)):
        return f"un(a) {type(v).__name__.lower()}"
    if es_forma(v):
        return "un cuerpo"
    texto = repr(v)
    return f"{texto[:60]}…" if len(texto) > 60 else texto


def describir(v):
    """Texto corto para un mensaje de error."""
    return _describir(v)


def es_coordenada_literal(v):
    """True si `v` (del JSON) es UN punto o vector: [x, y, z] o [x, y] de números o expresiones."""
    return (isinstance(v, (list, tuple)) and len(v) in (2, 3)
            and all(isinstance(c, (int, float, str)) and not isinstance(c, bool) for c in v))


def a_json(valor):
    """Valor del grafo → JSON (puntos como listas, planos y curvas como objetos; una forma OCC no es JSON: se
    resume en {"tipo": "cuerpo"})."""
    if valor is None or isinstance(valor, (bool, int, str)):
        return valor
    if isinstance(valor, float):
        return valor if math.isfinite(valor) else None
    if isinstance(valor, Plano):
        return valor.a_json()
    if isinstance(valor, Curva):
        return {"tipo": "curva", "descripcion": valor.descripcion, "cerrada": valor.cerrada}
    if es_forma(valor):
        return {"tipo": "cuerpo"}
    if isinstance(valor, (list, tuple)):
        return [a_json(x) for x in valor]
    return str(valor)

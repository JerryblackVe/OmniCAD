# -*- coding: utf-8 -*-
"""
Catálogo único de herramientas: cada herramienta se define UNA vez y de acá salen el MCP, la CLI y la
documentación.

Agregar una herramienta:

    @herramienta("set_parameter", "parametros", "Cambia la expresión de un parámetro.", modifica=True)
    def set_parameter(sesion, name: str, expression: Expr):
        '''
        name: nombre exacto del parámetro.
        expression: valor nuevo, número (mm o grados) o expresión de texto ("ancho / 2").
        '''
        ...
        return {"name": name, ...}

  - Primer argumento: la `Sesion`. El resto, con anotación de tipo; los que tienen valor por defecto son
    opcionales. Tipos soportados: str, int, float, bool, list[...], dict, dict[str, ...], Literal[...],
    `X | Y` y `X | None`. `Expr` (= float | str) es un número o una expresión con parámetros.
  - Descripción de cada parámetro: en el docstring, una línea `nombre: descripción` (las líneas siguientes
    más indentadas la continúan). El resto del docstring se ignora.
  - Nombres de herramientas, parámetros y claves del resultado en inglés snake_case; descripciones,
    mensajes y pistas en español. Unidades: mm y grados.
  - Devuelve datos JSON (dict, list, str, números, bool, None). Para fallar se lanza `ErrorAPI` (o una
    excepción del núcleo, que `errores.traducir` convierte). Avisos no fatales: `sesion.avisar(texto)`.
  - `modifica=True`: la llamada es UN paso de deshacer y es atómica (ver `Sesion.transaccion`).

Imágenes: una herramienta puede devolver `Imagen(png, ancho, alto)` dentro de su resultado (p. ej.
`{"image": Imagen(...)}`). `llamar` la deja tal cual; cada cara la convierte: el MCP en contenido de
imagen, la CLI en un archivo PNG o base64.

`llamar(sesion, nombre, args)` SIEMPRE devuelve un dict y nunca lanza:
    {"ok": True, "result": ..., "avisos": [...]}
    {"ok": False, "error_kind": "...", "mensaje": "...", "pistas": [...]}
"""
import difflib
import inspect
import re
import types
import typing
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Union

from .errores import error, traducir

Expr = float | str   # número (mm o grados) o expresión de texto con parámetros y unidades


@dataclass(frozen=True)
class Imagen:
    png: bytes
    ancho: int
    alto: int


@dataclass
class Herramienta:
    nombre: str
    grupo: str
    descripcion: str
    modifica: bool
    transaccion: bool
    funcion: typing.Callable
    tipos: dict
    defectos: dict
    esquema: dict


_CATALOGO = {}


# ---------------------------------------------------------------- esquema JSON
def _esquema_tipo(t):
    if t is typing.Any or t is inspect.Parameter.empty:
        return {}
    if t is type(None):
        return {"type": "null"}
    simples = {str: "string", bool: "boolean", int: "integer", float: "number", list: "array", dict: "object"}
    if t in simples:
        return {"type": simples[t]}
    origen, args = typing.get_origin(t), typing.get_args(t)
    if origen is Literal:
        tipos = {simples[type(a)] for a in args}
        return {"type": tipos.pop() if len(tipos) == 1 else sorted(tipos), "enum": list(args)}
    if origen in (Union, types.UnionType):
        partes = [_esquema_tipo(a) for a in args]
        if all(set(p) == {"type"} and isinstance(p["type"], str) for p in partes):
            return {"type": [p["type"] for p in partes]}
        return {"anyOf": partes}
    if origen is list:
        return {"type": "array", "items": _esquema_tipo(args[0])} if args else {"type": "array"}
    if origen is dict:
        return {"type": "object", "additionalProperties": _esquema_tipo(args[1])} if args else {"type": "object"}
    raise TypeError(f"Tipo no soportado en el esquema: {t!r}")


def _descripciones(funcion, nombres):
    """Líneas `nombre: descripción` del docstring (las más indentadas que siguen la continúan)."""
    resultado, actual, sangria = {}, None, 0
    for linea in (inspect.getdoc(funcion) or "").splitlines():
        m = re.match(r"^(\s*)(\w+):\s+(.+)$", linea)
        if m and m.group(2) in nombres:
            actual, sangria = m.group(2), len(m.group(1))
            resultado[actual] = m.group(3).strip()
        elif actual and linea.strip() and len(linea) - len(linea.lstrip()) > sangria:
            resultado[actual] += " " + linea.strip()
        else:
            actual = None
    return resultado


def herramienta(nombre, grupo, descripcion, modifica=False, transaccion=None):
    """Registra la función en el catálogo. `transaccion` (por defecto = `modifica`) envuelve la llamada en
    `Sesion.transaccion`; deshacer, rehacer, nuevo y abrir lo apagan porque manejan el documento ellos."""
    def registrar(funcion):
        if nombre in _CATALOGO:
            raise ValueError(f"Herramienta repetida: {nombre}")
        params = list(inspect.signature(funcion).parameters.values())[1:]   # el primero es la sesión
        tipos = typing.get_type_hints(funcion)
        textos = _descripciones(funcion, {p.name for p in params})
        propiedades, requeridos, defectos, anotados = {}, [], {}, {}
        for p in params:
            anotados[p.name] = tipos.get(p.name, typing.Any)
            prop = _esquema_tipo(anotados[p.name])
            if p.name in textos:
                prop["description"] = textos[p.name]
            if p.default is inspect.Parameter.empty:
                requeridos.append(p.name)
            else:
                prop["default"] = defectos[p.name] = p.default
            propiedades[p.name] = prop
        esquema = {"type": "object", "properties": propiedades, "required": requeridos, "additionalProperties": False}
        _CATALOGO[nombre] = Herramienta(nombre, grupo, descripcion, modifica,
                                        modifica if transaccion is None else transaccion,
                                        funcion, anotados, defectos, esquema)
        return funcion
    return registrar


def catalogo(grupos=None):
    """[{nombre, grupo, descripcion, modifica, esquema}] en orden de registro. `grupos`: str o lista."""
    if isinstance(grupos, str):
        grupos = [grupos]
    return [{"nombre": h.nombre, "grupo": h.grupo, "descripcion": h.descripcion, "modifica": h.modifica,
             "esquema": h.esquema} for h in _CATALOGO.values() if grupos is None or h.grupo in grupos]


# ---------------------------------------------------------------- validación de argumentos
class _NoCoincide(Exception):
    pass


def _sin_comillas(texto):
    """'"60 mm"' → '60 mm'. Algunos agentes mandan la expresión entre comillas dentro del JSON (visto en la prueba
    real con Claude Code del 2026-10-09: 12 create_parameter fallaron así). Unas comillas que envuelven TODA la
    expresión nunca son válidas, así que sacarlas no cambia el significado de nada."""
    t = texto.strip()
    if len(t) >= 2 and t[0] == t[-1] and t[0] in "\"'":
        return t[1:-1].strip()
    return texto


def _convertir(valor, t):
    """Valida `valor` contra el tipo `t` y lo normaliza (int → float, 2.0 → 2). Lanza _NoCoincide."""
    if t is typing.Any:
        return valor
    if t is type(None):
        if valor is None:
            return None
        raise _NoCoincide
    if t is bool:
        if isinstance(valor, bool):
            return valor
        raise _NoCoincide
    if t is int:
        if isinstance(valor, int) and not isinstance(valor, bool):
            return valor
        if isinstance(valor, float) and valor.is_integer():
            return int(valor)
        raise _NoCoincide
    if t is float:
        if isinstance(valor, (int, float)) and not isinstance(valor, bool):
            return float(valor)
        raise _NoCoincide
    if t is str:
        if isinstance(valor, str):
            return valor
        raise _NoCoincide
    origen, args = typing.get_origin(t), typing.get_args(t)
    if origen is Literal:
        if any(valor == a and type(valor) is type(a) for a in args):
            return valor
        raise _NoCoincide
    if origen in (Union, types.UnionType):
        if isinstance(valor, str) and set(args) - {type(None)} == {float, str}:
            valor = _sin_comillas(valor)          # Expr (o Expr | None)
        for a in args:
            try:
                return _convertir(valor, a)
            except _NoCoincide:
                pass
        raise _NoCoincide
    if t is list or origen is list:
        if not isinstance(valor, (list, tuple)):
            raise _NoCoincide
        return [_convertir(v, args[0]) for v in valor] if args else list(valor)
    if t is dict or origen is dict:
        if not isinstance(valor, dict) or not all(isinstance(k, str) for k in valor):
            raise _NoCoincide
        return {k: _convertir(v, args[1]) for k, v in valor.items()} if args else dict(valor)
    raise _NoCoincide


def _firma(h):
    partes = []
    for nombre, prop in h.esquema["properties"].items():
        tipo = prop.get("type") or "any"
        tipo = "|".join(tipo) if isinstance(tipo, list) else tipo
        partes.append(f"{nombre}: {tipo}" + ("" if nombre in h.esquema["required"] else f" = {prop['default']!r}"))
    return f"{h.nombre}(" + ", ".join(partes) + ")"


def _argumentos(h, args):
    if args is None:
        args = {}
    if not isinstance(args, dict):
        raise error("INVALID_ARGUMENTS", "Los argumentos tienen que ser un objeto JSON (dict).", f"Firma: {_firma(h)}")
    validos = list(h.tipos)
    desconocidos = [k for k in args if k not in h.tipos]
    if desconocidos:
        raise error("INVALID_ARGUMENTS", f"Argumentos desconocidos para {h.nombre}: {', '.join(map(str, desconocidos))}.",
                    f"Argumentos válidos: {', '.join(validos) or '(ninguno)'}.", f"Firma: {_firma(h)}")
    faltan = [k for k in h.esquema["required"] if k not in args]
    if faltan:
        raise error("INVALID_ARGUMENTS", f"Faltan argumentos obligatorios de {h.nombre}: {', '.join(faltan)}.",
                    f"Firma: {_firma(h)}")
    kwargs = {}
    for k, v in args.items():
        try:
            kwargs[k] = _convertir(v, h.tipos[k])
        except _NoCoincide:
            esperado = h.esquema["properties"][k]
            esperado = esperado.get("enum") or esperado.get("type") or esperado.get("anyOf")
            raise error("INVALID_ARGUMENTS", f"Tipo incorrecto en '{k}': {v!r} no es {esperado}.",
                        f"Argumentos válidos: {', '.join(validos)}.", f"Firma: {_firma(h)}") from None
    return kwargs


# ---------------------------------------------------------------- llamada
def _a_json(x):
    """Normaliza el resultado a tipos JSON (numpy, tuplas, Path, sets). Las `Imagen` quedan tal cual."""
    if isinstance(x, dict):
        return {str(k): _a_json(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_a_json(v) for v in x]
    if isinstance(x, (set, frozenset)):
        return sorted(_a_json(v) for v in x)
    if isinstance(x, Path):
        return str(x)
    if hasattr(x, "tolist") and not isinstance(x, Imagen):   # numpy: escalares y arreglos
        return _a_json(x.tolist())
    return x


def llamar(sesion, nombre, args=None):
    """Ejecuta una herramienta del catálogo. Nunca lanza: los errores vuelven como dict con error_kind."""
    try:
        h = _CATALOGO.get(nombre) if isinstance(nombre, str) else None
        if h is None:
            parecidas = difflib.get_close_matches(str(nombre), list(_CATALOGO), n=3)
            raise error("UNKNOWN_TOOL", f"No existe la herramienta '{nombre}'.",
                        *([f"¿Quisiste decir: {', '.join(parecidas)}?"] if parecidas else []))
        kwargs = _argumentos(h, args)
        sesion.avisos = []
        if h.transaccion:
            with sesion.transaccion():
                resultado = h.funcion(sesion, **kwargs)
        else:
            resultado = h.funcion(sesion, **kwargs)
        return {"ok": True, "result": _a_json(resultado), "avisos": list(sesion.avisos)}
    except Exception as e:  # noqa: BLE001 — contrato: llamar nunca lanza
        return traducir(e).a_dict()

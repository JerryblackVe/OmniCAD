# -*- coding: utf-8 -*-
"""Herramientas del grupo "avanzado": cualquier operación del timeline, la receta del documento, código Python y
la guía para agentes.

Sirven para lo que las herramientas específicas todavía no cubren: `run_operation` agrega CUALQUIER paso del
timeline con sus parámetros nativos (claves en español, las de `PARAMS` de cada operación) y
`describe_operation` explica cada tipo. Unidades: mm y grados.
"""
import contextlib
import difflib
import importlib
import inspect
import io
import json
import math
import re
import sys
import time
import traceback
from pathlib import Path
from typing import Literal

from ..timeline.documento import VERSION_RECETA
from ..timeline.operaciones import TIPOS_OPERACION, OpOperacionBase, operacion_desde_dict
from .errores import desde_mensaje, error
from .registro import _a_json, herramienta, llamar

_GUIA = Path(__file__).resolve().parent / "guia"
# Operaciones que guardan el archivo copiado en la receta (clave del contenido): por run_operation no leen rutas.
_CONTENIDO_EMBEBIDO = {"importar_step": "contenido", "importar_iges": "contenido", "insertar_malla": "datos",
                       "insertar_diseno": "receta"}
_SALIDA_MAXIMA = 20000        # caracteres de stdout que devuelve execute_code
_TRAZA_MAXIMA = 1500          # caracteres del mensaje de error de execute_code
PLAZO_CODIGO = 60.0           # segundos que corre execute_code por defecto antes de cortarse


# ---------------------------------------------------------------- tipos de operación
def _clase(tipo):
    clase = TIPOS_OPERACION.get(tipo)
    if clase is None:
        parecidos = difflib.get_close_matches(str(tipo), list(TIPOS_OPERACION), n=3)
        raise error("UNKNOWN_OPERATION_TYPE", f"No existe el tipo de operación '{tipo}'.",
                    *([f"¿Quisiste decir: {', '.join(parecidos)}?"] if parecidos else []))
    return clase


def _resumen_clase(clase):
    """Primera línea del docstring de la operación (si no tiene, su etiqueta)."""
    for linea in (inspect.getdoc(clase) or "").splitlines():
        if linea.strip():
            return linea.strip()
    return f"Operación «{clase.ETIQUETA or clase.TIPO}» (sin descripción: ver sus parámetros con describe_operation)."


def _claves_expresion(clase):
    """Claves de PARAMS que aceptan expresiones: las de `EXPRESIONES` y las que la operación devuelve en su
    método `expresiones()` (algunas, como la primitiva, lo sobrescriben según su forma y no usan EXPRESIONES).
    Se detectan poniendo un texto marcado en cada clave de texto y viendo si `expresiones()` lo devuelve."""
    claves = set(clase.EXPRESIONES)
    if isinstance(getattr(clase, "CAMPOS", None), dict):
        claves.update(k for campos in clase.CAMPOS.values() for k in campos if k in clase.PARAMS)
    marca = "§sonda§"
    for k, v in clase.PARAMS.items():
        if isinstance(v, str) and k not in claves:
            try:
                op = operacion_desde_dict({"tipo": clase.TIPO, "id": "_sonda", "params": {k: marca}})
                if marca in str(op.expresiones()):
                    claves.add(k)
            except Exception:  # noqa: BLE001 — sin sonda posible: se queda con las declaradas
                pass
    return claves


def _tipo_de_valor(clave, valor, expresiones):
    if clave in expresiones:
        return "expression"          # número (mm o grados) o texto con parámetros: "ancho / 2", "10 mm"
    if isinstance(valor, bool):      # bool va antes que int: True es un int en Python
        return "boolean"
    if isinstance(valor, int):
        return "integer"
    if isinstance(valor, float):
        return "number"
    if isinstance(valor, str):
        return "string"
    if isinstance(valor, list):
        return "array"
    if isinstance(valor, dict):
        return "object"
    return "any"                     # None: referencia opcional (cuerpo, cara, plano…) sin valor todavía


def _ejemplo(clase):
    expresiones = [k for k in clase.PARAMS if k in _claves_expresion(clase)]
    elegidas = (expresiones or list(clase.PARAMS))[:3]
    params = {k: clase.PARAMS[k] for k in elegidas}
    return {"tool": "run_operation", "args": {"type": clase.TIPO, "params": params}}


@herramienta("list_operation_types", "avanzado", "Lista todos los tipos de operación del timeline que acepta "
             "run_operation: tipo, etiqueta y una línea que dice qué hace.")
def list_operation_types(sesion):
    tipos = [{"type": t, "label": c.ETIQUETA, "summary": _resumen_clase(c)} for t, c in TIPOS_OPERACION.items()]
    return {"count": len(tipos), "types": tipos}


@herramienta("describe_operation", "avanzado", "Explica un tipo de operación: parámetros con su valor por defecto, "
             "tipo, si aceptan expresiones y, en los de lista cerrada, sus valores válidos (choices); el docstring "
             "completo y un ejemplo de llamada a run_operation.")
def describe_operation(sesion, type: str):
    """
    type: tipo de operación (list_operation_types los lista), p. ej. "primitiva".
    """
    clase = _clase(type)
    expresiones = _claves_expresion(clase)
    params = [{"name": k, "default": v, "type": _tipo_de_valor(k, v, expresiones), "accepts_expression": k in expresiones}
              for k, v in clase.PARAMS.items()]
    for p in params:
        if p["name"] in clase.OPCIONES:           # la misma lista con la que el paso valida al calcularse
            p["choices"] = list(clase.OPCIONES[p["name"]])
    return {"type": clase.TIPO, "label": clase.ETIQUETA, "summary": _resumen_clase(clase),
            "doc": inspect.getdoc(clase) or "", "params": params,
            "expressions": [k for k in clase.PARAMS if k in expresiones], "example": _ejemplo(clase)}


@herramienta("run_operation", "avanzado", "Agrega al timeline cualquier operación por su tipo y sus parámetros nativos "
             "(claves en español, las de describe_operation). Una llamada = un paso de deshacer; si el paso falla, "
             "el documento queda intacto.", modifica=True)
def run_operation(sesion, type: str, params: dict | None = None, name: str | None = None):
    """
    type: tipo de operación (list_operation_types los lista).
    params: parámetros a cambiar respecto de los valores por defecto, con las claves de describe_operation.
    name: nombre del paso en el timeline; vacío = el automático.
    """
    clase = _clase(type)
    params = params or {}
    desconocidos = [k for k in params if k not in clase.PARAMS]
    if desconocidos:
        raise error("INVALID_ARGUMENTS", f"La operación '{clase.TIPO}' no tiene los parámetros: {', '.join(desconocidos)}.",
                    f"Parámetros válidos: {', '.join(clase.PARAMS) or '(ninguno)'}.",
                    "describe_operation explica cada uno.")
    clave = _CONTENIDO_EMBEBIDO.get(clase.TIPO)
    if clave and not params.get(clave):
        raise error("INVALID_ARGUMENTS", f"«{clase.TIPO}» guarda el archivo copiado en «{clave}»: con la ruta sola no "
                    "alcanza.", "Usá insert_file(path=...): lee el archivo y lo agrega como un paso del documento actual.")
    cuerpos = params.get("cuerpos") if clase.TIPO == "operacion_base" else None
    if isinstance(cuerpos, list) and cuerpos and all(isinstance(c, str) for c in cuerpos):
        # Como «Crear operación base» de la ventana: los cuerpos nombrados se congelan en este momento.
        params = dict(params, cuerpos=OpOperacionBase.desde_cuerpos("_", [sesion.cuerpo(c) for c in cuerpos]).p["cuerpos"])
    doc = sesion.doc
    antes = set(doc.estado_final.cuerpos)
    op = operacion_desde_dict({"tipo": clase.TIPO, "id": doc.nuevo_id(), "nombre": name or None, "params": params})
    resultado = doc.agregar(op)
    if op.TIPO == "patron" and "distribucion" not in params and {"d1", "d2", "angulo"} & set(params):
        sesion.avisar(f"«{op.nombre}»: {op.aclaracion_distancias()}")
    nuevos = [c for c in doc.estado_final.cuerpos if c not in antes]
    return {"id": op.id, "name": op.nombre, "type": op.TIPO, "status": resultado.estado, "message": resultado.mensaje,
            "new_bodies": nuevos, "bodies": list(doc.estado_final.cuerpos)}


# ---------------------------------------------------------------- receta
@herramienta("get_recipe", "avanzado", "Devuelve la receta JSON completa del documento (parámetros, timeline y "
             "propiedades): es lo que guarda el archivo .omnicad y lo que acepta apply_recipe.")
def get_recipe(sesion):
    return {"recipe": sesion.doc.a_dict()}


def _validar_receta(receta):
    if not isinstance(receta.get("operaciones"), list) or not all(
            isinstance(d, dict) and "tipo" in d and "id" in d for d in receta["operaciones"]):
        raise error("INVALID_RECIPE", "La receta no tiene una lista 'operaciones' con objetos {tipo, id, params}.")
    if receta.get("version_receta", 1) > VERSION_RECETA:
        raise error("INVALID_RECIPE", f"La receta es de una versión más nueva ({receta['version_receta']}) que la "
                    f"soportada ({VERSION_RECETA}).")
    for d in receta["operaciones"]:
        if d["tipo"] not in TIPOS_OPERACION:
            raise error("UNKNOWN_OPERATION_TYPE", f"La receta usa el tipo de operación desconocido '{d['tipo']}'.")


def _renumerar(doc, ops_nuevas, propiedades):
    """Ids nuevos para los pasos que se agregan (y las referencias a ellos en sus parámetros), si chocan con los
    del documento. Devuelve (ops, propiedades)."""
    usados = {o.id for o in doc.operaciones}
    if not any(d["id"] in usados for d in ops_nuevas):
        return ops_nuevas, propiedades
    contador, mapa = doc._contador, {}
    for d in ops_nuevas:
        while True:
            contador += 1
            if f"op{contador}" not in usados:
                break
        mapa[d["id"]] = f"op{contador}"
        usados.add(mapa[d["id"]])
    patron = re.compile(r"(?<![\w])(" + "|".join(re.escape(k) for k in sorted(mapa, key=len, reverse=True)) + r")(?![\w])")

    def cambiar(x):                       # reemplaza ids dentro de cualquier estructura JSON (claves y textos)
        return json.loads(patron.sub(lambda m: mapa[m.group(1)], json.dumps(x)))
    salida = []
    for d in ops_nuevas:
        nuevo = cambiar({k: v for k, v in d.items() if k != "nombre"})
        nuevo["nombre"] = d.get("nombre")
        salida.append(nuevo)
    return salida, cambiar(propiedades)


@herramienta("apply_recipe", "avanzado", "Carga una receta JSON (la de get_recipe): 'replace' reemplaza todo el "
             "documento; 'append' agrega sus pasos y parámetros al final. Es un paso de deshacer; si algo falla, el "
             "documento queda intacto.", modifica=True)
def apply_recipe(sesion, recipe: dict, mode: Literal["replace", "append"] = "replace"):
    """
    recipe: la receta de get_recipe: su resultado {"recipe": …} tal cual o el objeto de adentro (con 'operaciones',
        'parametros', etc.).
    mode: "replace" reemplaza el contenido del documento (conserva su archivo); "append" suma al final del
        timeline los pasos y parámetros de la receta (renumera los ids que chocan; un parámetro con el mismo
        nombre y otra expresión es un error) y deja el marcador al final.
    """
    if "operaciones" not in recipe and isinstance(recipe.get("recipe"), dict):
        recipe = recipe["recipe"]                     # el resultado de get_recipe tal cual
    _validar_receta(recipe)
    doc = sesion.doc
    # Nombre, vistas, espacios y comentarios no son parte de `_cargar` ni de la transacción: se restauran acá.
    previos = (doc.nombre, doc.vistas, doc.espacios, doc.comentarios)
    estados = sesion._estados_pasos()
    try:
        if mode == "replace":
            doc._guardar_para_deshacer()
            doc._cargar(recipe)
            doc.nombre = recipe.get("nombre", "Sin título")
            doc.vistas, doc.espacios = dict(recipe.get("vistas", {})), dict(recipe.get("espacios", {}))
            doc.comentarios = [dict(c) for c in recipe.get("comentarios", [])]
        else:
            combinada = doc.a_dict()
            existentes = {p["nombre"]: p for p in combinada["parametros"]}
            for p in recipe.get("parametros") or []:
                previo = existentes.get(p["nombre"])
                if previo is None:
                    combinada["parametros"].append(p)
                elif previo["expresion"] != p["expresion"]:
                    raise error("PARAMETER_EXISTS", f"El parámetro '{p['nombre']}' ya existe con otra expresión "
                                f"('{previo['expresion']}' en el documento, '{p['expresion']}' en la receta).",
                                "Renombralo en la receta o usá mode='replace'.")
            ops, props = _renumerar(doc, recipe["operaciones"], recipe.get("propiedades") or {})
            combinada["operaciones"] += ops
            combinada["marcador"] = len(combinada["operaciones"])
            combinada["contador"] = max(doc._contador, len(combinada["operaciones"]))
            for k, v in props.items():
                combinada["propiedades"].setdefault(k, v)
            doc._guardar_para_deshacer()
            doc._cargar(combinada)
        for o, r in zip(doc.operaciones, doc.resultados, strict=False):      # un paso nuevo con error = receta mala
            if r.estado == "error" and estados.get(o.id, ("",))[0] != "error":
                raise desde_mensaje(r.mensaje, f"El paso «{o.nombre}» ({o.id}) de la receta quedó con error: ")
    except Exception as e:  # noqa: BLE001 — la transacción restaura el resto del documento al relanzar
        doc.nombre, doc.vistas, doc.espacios, doc.comentarios = previos
        if hasattr(e, "error_kind"):
            raise
        raise error("INVALID_RECIPE", f"No se pudo cargar la receta: {type(e).__name__}: {e}") from e
    return {"mode": mode, "added_steps": len(recipe["operaciones"]), "timeline_steps": len(doc.operaciones),
            "bodies": list(doc.estado_final.cuerpos)}


# ---------------------------------------------------------------- código
def _traza(e, codigo):
    """Traceback recortado: solo las líneas del código del agente (y el último punto interno si falló adentro)."""
    lineas_codigo = codigo.splitlines()
    if isinstance(e, SyntaxError):
        fuente = (lineas_codigo[e.lineno - 1].strip() if e.lineno and e.lineno <= len(lineas_codigo) else "")
        return f"SyntaxError en la línea {e.lineno}: {e.msg}\n    {fuente}".rstrip()
    marcos = traceback.extract_tb(e.__traceback__)
    propios = [m for m in marcos if m.filename == "<codigo>"][-4:]
    partes = [f"línea {m.lineno} ({m.name}): "
              f"{lineas_codigo[m.lineno - 1].strip() if 0 < m.lineno <= len(lineas_codigo) else ''}" for m in propios]
    if marcos and marcos[-1].filename != "<codigo>":
        interno = marcos[-1]
        partes.append(f"(falló dentro de {Path(interno.filename).name}:{interno.lineno} en {interno.name})")
    partes.append(f"{type(e).__name__}: {e}")
    return "\n".join(partes)


def _serializable(valor, sesion):
    valor = _a_json(valor)
    try:
        json.dumps(valor)
        return valor
    except (TypeError, ValueError):
        sesion.avisar("`result` no es JSON: se devuelve su texto (repr).")
        return repr(valor)[:2000]


class _TiempoAgotado(BaseException):
    """Corte de execute_code por plazo. BaseException: ni un `except Exception` del agente ni el de
    Documento.recalcular la atrapan; y se relanza en cada línea, así que tampoco la frena un `except:`."""

    def __init__(self, linea):
        super().__init__(linea)
        self.linea = linea


_VIGIA = {"id": None}         # id de sys.monitoring reservado (perezosamente) para vigilar el plazo
_limites = {}                 # objeto de código del agente → instante (monotonic) en que se corta


def _al_cambiar_de_linea(code, linea):
    limite = _limites.get(code)
    if limite is not None and time.monotonic() > limite:
        raise _TiempoAgotado(linea)


def _al_saltar(code, desde, _hacia):
    """Saltos (también hacia atrás dentro de una misma línea, p. ej. `while True: pass`, que no dispara LINE)."""
    limite = _limites.get(code)
    if limite is not None and time.monotonic() > limite:
        linea = next((ln for ini, fin, ln in code.co_lines() if ini <= desde < fin), None)
        raise _TiempoAgotado(linea)


_EVENTOS = sys.monitoring.events.LINE | sys.monitoring.events.JUMP


def _id_vigia():
    """Reserva un id de herramienta de sys.monitoring la primera vez. None si están todos ocupados."""
    if _VIGIA["id"] is None:
        mon = sys.monitoring
        for i in (3, 4):
            if mon.get_tool(i) is None:
                mon.use_tool_id(i, "omnicad-plazo")
                mon.register_callback(i, mon.events.LINE, _al_cambiar_de_linea)
                mon.register_callback(i, mon.events.JUMP, _al_saltar)
                _VIGIA["id"] = i
                break
    return _VIGIA["id"]


def _codigos(co):
    yield co
    for c in co.co_consts:
        if isinstance(c, type(co)):
            yield from _codigos(c)


@contextlib.contextmanager
def _plazo(compilado, segundos, sesion):
    """Vigila SOLO las líneas del código del agente (eventos LINE locales): una llamada interna larga no se
    corta a la mitad, el corte llega cuando vuelve al código del agente (nunca queda un recálculo a medias)."""
    vigia = _id_vigia() if segundos is not None else None
    if vigia is None:
        if segundos is not None:
            sesion.avisar("No se pudo vigilar el tiempo máximo (sys.monitoring ocupado): el código corre sin límite.")
        yield
        return
    codigos = [c for c in _codigos(compilado) if c not in _limites]
    limite = min([time.monotonic() + segundos, *_limites.values()])   # uno anidado no dura más que el de afuera
    for c in codigos:
        _limites[c] = limite
        sys.monitoring.set_local_events(vigia, c, _EVENTOS)
    try:
        yield
    finally:
        for c in codigos:
            sys.monitoring.set_local_events(vigia, c, 0)
            _limites.pop(c, None)


@herramienta("execute_code", "avanzado", "Ejecuta código Python con api, sesion, doc y llamar(nombre, args) ya definidos. "
             "Devuelve lo impreso (stdout) y la variable `result` si el código la define. Todo es un paso de "
             "deshacer; si el código lanza una excepción, el documento queda intacto. Corre como mucho `timeout` "
             f"segundos ({PLAZO_CODIGO:g} por defecto): al vencer se corta con CODE_TIMEOUT y el documento vuelve "
             "a como estaba.", modifica=True)
def execute_code(sesion, code: str, timeout: float | None = PLAZO_CODIGO):
    """
    code: código Python. Definidos: api (el paquete omnicad.api), sesion, doc (el documento activo) y llamar
        (atajo de api.llamar(sesion, nombre, args)). Asigná `result = ...` para devolver un valor.
    timeout: segundos como máximo (60 por defecto); al vencer se corta el código, el documento vuelve a como
        estaba y responde CODE_TIMEOUT. null = sin límite (en vivo no se acepta; el máximo es 100 s). Solo se
        vigila tu código: una llamada larga a una herramienta termina antes del corte.
    """
    if timeout is not None and not (math.isfinite(timeout) and timeout > 0):
        raise error("INVALID_ARGUMENTS", f"timeout tiene que ser un número de segundos mayor que 0 (o null); vino {timeout!r}.")
    api = importlib.import_module(__package__)
    espacio = {"__name__": "__codigo__", "api": api, "sesion": sesion, "doc": sesion.doc,
               "llamar": lambda nombre, args=None: llamar(sesion, nombre, args)}
    salida = io.StringIO()
    try:
        compilado = compile(code, "<codigo>", "exec")
        with contextlib.redirect_stdout(salida), contextlib.redirect_stderr(salida), _plazo(compilado, timeout, sesion):
            exec(compilado, espacio)  # noqa: S102 — es la función de la herramienta: ejecutar código del agente
    except _TiempoAgotado as e:
        lineas = code.splitlines()
        fuente = lineas[e.linea - 1].strip() if 0 < e.linea <= len(lineas) else ""
        texto = f"El código pasó el tiempo máximo ({timeout:g} s) y se cortó en la línea {e.linea}: {fuente}"
        if salida.getvalue():
            texto += "\nSalida hasta el corte:\n" + salida.getvalue()[-500:]
        raise error("CODE_TIMEOUT", texto[:_TRAZA_MAXIMA]) from None
    except (Exception, SystemExit) as e:  # noqa: BLE001
        texto = _traza(e, code)
        if salida.getvalue():
            texto += "\nSalida hasta el error:\n" + salida.getvalue()[-500:]
        raise error("CODE_ERROR", texto[:_TRAZA_MAXIMA]) from None
    stdout = salida.getvalue()
    resultado = {"stdout": stdout[:_SALIDA_MAXIMA], "stdout_truncated": len(stdout) > _SALIDA_MAXIMA}
    if "result" in espacio:
        resultado["result"] = _serializable(espacio["result"], sesion)
    return resultado


# ---------------------------------------------------------------- guía
def _temas():
    return sorted(p.stem for p in _GUIA.glob("*.md"))


@herramienta("get_guide", "avanzado", "Guía corta para agentes (ciclo de trabajo, unidades, cómo leer errores). Sin "
             "tema devuelve el índice.")
def get_guide(sesion, topic: str | None = None):
    """
    topic: tema de la guía (el índice los lista), p. ej. "flujo"; vacío = el índice.
    """
    tema = (topic or "indice").strip().lower().removesuffix(".md")
    archivo = _GUIA / f"{tema}.md"
    if not re.fullmatch(r"[a-z0-9_]+", tema) or not archivo.is_file():
        raise error("TOPIC_NOT_FOUND", f"No existe el tema '{topic}'.", f"Temas: {', '.join(_temas())}.")
    return {"topic": tema, "text": archivo.read_text(encoding="utf-8"), "topics": _temas()}

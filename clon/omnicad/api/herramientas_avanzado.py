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
from ..timeline.operaciones import TIPOS_OPERACION, OpExtrusion, OpOperacionBase, operacion_desde_dict
from . import selectores as sl
from .errores import ErrorAPI, desde_mensaje, error
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


# ---------------------------------------------------------------- referencias abreviadas
# Los pasos guardan referencias (los dicts de `timeline.entidades`: {"tipo": "cara", "cuerpo", "firma"}…), que un
# agente no puede escribir a mano. run_operation y edit_feature aceptan además estas formas cortas y las traducen
# acá, con el documento actual (la misma traducción para todas las operaciones).
FORMATOS_REFERENCIA = [
    'Cara o arista: el id de find_faces / find_edges ("Cuerpo1/F3", "Cuerpo1/E7"; vale hasta el próximo cambio) o '
    'un selector con prefijo: "faces:>Z", "edges:|Z" (sobre el único cuerpo) o {"faces": ">Z", "body": "Cuerpo1"}. '
    'En campos de caras o aristas («caras», «aristas»…) el selector va sin prefijo (">Z"). Se guarda la referencia '
    'persistente, que sigue a la cara cuando cambian los parámetros.',
    'Origen: "XY", "XZ", "YZ" (planos), "X", "Y", "Z" (ejes) y "O" (el punto de origen).',
    'Construcción y bocetos: id o nombre de un plano, eje o punto de construcción ("op3", "Plano1") o de un boceto '
    '(el boceto entero, como plano).',
    'Boceto: {"sketch": "Boceto1", "point": 3} (punto; get_sketch lista los ids), {"sketch": "Boceto1", "curve": 2} '
    '(curva) o {"sketch": "Boceto1", "profile": 0} (perfil: índice, lista, "all" o "largest"). Siguen al boceto si '
    'cambia.',
    'Cuerpo: {"body": "Cuerpo1"} (id o nombre). En los campos de ids de cuerpo («cuerpos», «objetivos»…) va el id o '
    'el nombre directo ("op2.c1", "Cuerpo1"; se guarda el id).',
    'La forma guardada (un dict con "tipo", como la muestra get_timeline) se acepta tal cual. Un texto que no es '
    'ninguna de estas formas llega sin cambios al paso, que dice qué campo está mal y qué esperaba.',
]
_CAMPOS_CUERPO = ("cuerpos", "objetivos", "objetivo", "cuerpo", "herramientas")     # ids de cuerpo como texto
_SIN_REFERENCIAS = ("marco", "receta", "datos", "ajustes", "suprimir", "celdas", "componentes", "pasos",
                    "coordenadas", "referencia_xyz", "transformaciones")
_ORIGEN = {"XY": ("plano", "XY"), "XZ": ("plano", "XZ"), "YZ": ("plano", "YZ"), "X": ("eje", "X"), "Y": ("eje", "Y"),
           "Z": ("eje", "Z"), "O": ("punto", "O")}
_SELECTOR_DE_CAMPO = {"cara": "cara", "caras": "cara", "caras_a": "cara", "caras_b": "cara", "aristas": "arista"}
_CAMPOS_PERFIL = ("perfiles", "perfil", "secciones")
_ID_CUERPO = re.compile(r"op\d+\.c\d+")
_PREFIJO = re.compile(r"^\s*(faces|edges)\s*:", re.IGNORECASE)
_LETRA_ID = re.compile(r"/([FE])\d+\s*$", re.IGNORECASE)


def tipo_de_campo(clase, clave):
    """Qué guarda el campo `clave` de la operación: "cuerpos" (ids de cuerpo como texto), "una" (UNA referencia),
    "lista" (lista de referencias) o None (otra cosa: números, textos, expresiones, marcos, contenido embebido)."""
    if clave not in clase.PARAMS or clave in _SIN_REFERENCIAS or clave in clase.EXPRESIONES:
        return None
    if clave in _CAMPOS_CUERPO and clave not in getattr(clase, "REFS", ()):
        return "cuerpos"
    defecto = clase.PARAMS[clave]
    if defecto is None:
        return "una"
    return "lista" if isinstance(defecto, list) else None


def _elementos_elegidos(sesion, clave, spec, body, elementos):
    """Referencias persistentes de las caras o aristas que elige un id efímero o un selector."""
    if not elementos:
        raise error("INVALID_ARGUMENTS", f"«{clave}»: {spec!r} es un id de find_faces / find_edges o un selector, y "
                    "acá no sirve: se evaluaría sobre la pieza terminada y no sobre la de antes del paso.",
                    "Borrá el paso (delete_feature) y crealo de nuevo con su herramienta o con run_operation (ahí sí "
                    "valen ids y selectores), o deshacelo con undo si recién lo creaste.")
    m, letra = _PREFIJO.match(spec), _LETRA_ID.search(spec)
    if m:
        tipo = "cara" if m.group(1).lower() == "faces" else "arista"
    elif sl.es_id(spec) and letra:
        tipo = "cara" if letra.group(1).upper() == "F" else "arista"
    else:
        tipo = _SELECTOR_DE_CAMPO[clave]
    try:
        elegidos = sl.elegir(sesion, spec, tipo, body)
    except ErrorAPI as e:
        if e.error_kind == "AMBIGUOUS_REFERENCE" and not body:
            raise error("AMBIGUOUS_REFERENCE", e.mensaje, 'Decí el cuerpo: {"faces": ">Z", "body": "Cuerpo1"}, o '
                        'usá ids de find_faces / find_edges.') from None
        raise
    return [sl.referencia(c, e) for c, e in elegidos]


def _de_boceto(sesion, clave, item):
    """{"sketch": …} con "point", "curve" o "profile" (o solo, el boceto entero) → referencias."""
    from .herramientas_boceto import boceto_activo, seleccionar_perfiles   # diferido: no cambia el orden del catálogo
    otras = set(item) - {"sketch"}
    if len(otras) > 1 or otras - {"point", "curve", "profile"}:
        raise error("INVALID_ARGUMENTS", f"«{clave}»: {item!r} no es una referencia de boceto.",
                    'Usá {"sketch": "Boceto1", "point": 3}, {"sketch": "Boceto1", "curve": 2} o '
                    '{"sketch": "Boceto1", "profile": 0} (una sola de point, curve o profile).')
    sop, br = boceto_activo(sesion, item["sketch"])
    if not otras:
        if clave in _CAMPOS_PERFIL:
            raise error("INVALID_ARGUMENTS", f"«{clave}» guarda perfiles: elegí uno del boceto «{sop.nombre}».",
                        f'Usá {{"sketch": "{sop.nombre}", "profile": 0}} (get_sketch lista los perfiles).')
        return [{"tipo": "boceto", "boceto": sop.id}]
    que = otras.pop()
    if que == "profile":
        return [dict(OpExtrusion.referencia_perfil(p), tipo="perfil", boceto=sop.id)
                for p in seleccionar_perfiles(br, sop, item["profile"])]
    numeros = item[que] if isinstance(item[que], list) else [item[que]]
    existentes, tipo, k = ((br.boceto.puntos, "punto_boceto", "punto") if que == "point"
                           else (br.boceto.curvas, "curva_boceto", "curva"))
    for n in numeros:
        if isinstance(n, bool) or not isinstance(n, int) or n not in existentes:
            raise error("ENTITY_NOT_FOUND", f"«{clave}»: el boceto «{sop.nombre}» ({sop.id}) no tiene "
                        f"{'el punto' if que == 'point' else 'la curva'} {n!r}.")
    return [{"tipo": tipo, "boceto": sop.id, k: n} for n in numeros]


def _de_texto(sesion, clave, texto):
    """Origen, construcción o boceto nombrado por un texto → [referencia]; None si el texto no nombra nada de eso
    (llega sin cambios al paso, que da el error con el campo y lo que esperaba)."""
    if texto.upper() in _ORIGEN:
        t, i = _ORIGEN[texto.upper()]
        return [{"tipo": t, "id": i}]
    estado, cf = sesion.doc.estado_final, texto.casefold()
    hallados = []                                # (por id, qué es, referencia)

    def anotar(i, nombre, que, ref):
        if i == texto or str(nombre or "").casefold() == cf:
            hallados.append((i == texto, f"{que} {i}", ref))
    for i, p in estado.planos.items():
        anotar(i, getattr(p, "nombre", ""), "plano", {"tipo": "plano", "id": i})
    for i, e in estado.ejes.items():
        anotar(i, e[2] if len(e) > 2 else "", "eje", {"tipo": "eje", "id": i})
    for i, p in estado.puntos.items():
        anotar(i, p[1] if len(p) > 1 else "", "punto", {"tipo": "punto", "id": i})
    for i, br in estado.bocetos.items():
        anotar(i, br.nombre, "boceto", {"tipo": "boceto", "boceto": i})
    hallados = [h for h in hallados if h[0]] or hallados
    if len(hallados) > 1:
        raise error("AMBIGUOUS_REFERENCE", f"«{clave}»: «{texto}» puede ser {', '.join(h[1] for h in hallados)}.",
                    "Usá el id.")
    if not hallados:
        return None
    ref = hallados[0][2]
    if ref["tipo"] == "boceto" and clave in _CAMPOS_PERFIL:
        return _de_boceto(sesion, clave, {"sketch": ref["boceto"]})        # da el error con la forma correcta
    return [ref]


def _es_corta(v):
    """True si `v` es una forma corta de un elemento (id efímero, selector con prefijo o dict abreviado)."""
    if isinstance(v, str):
        return sl.es_id(v) or bool(_PREFIJO.match(v))
    return isinstance(v, dict) and "tipo" not in v and bool(set(v) & {"sketch", "body", "faces", "edges"})


def _refs(sesion, clave, item, elementos):
    """Una forma corta (texto o dict) → lista de referencias; None si `item` no es una forma corta (queda igual)."""
    if isinstance(item, dict):
        if "tipo" in item:
            return None
        if "sketch" in item:
            return _de_boceto(sesion, clave, item)
        if item and set(item) <= {"body", "faces", "edges"}:
            if set(item) == {"body"}:
                return [{"tipo": "cuerpo", "cuerpo": sesion.cuerpo(item["body"]).id}]
            if {"faces", "edges"} <= set(item):
                raise error("INVALID_ARGUMENTS", f"«{clave}»: pasá faces o edges, no los dos.")
            que = "faces" if "faces" in item else "edges"
            return _elementos_elegidos(sesion, clave, f"{que}:{item[que]}", item.get("body"), elementos)
        # dict propio de la operación (p. ej. {"cara": …, "punto": [x, y, z]} del agujero): sus valores cortos
        if any(_es_corta(v) for v in item.values()):
            return [{k: (_una(sesion, k, v, elementos) if _es_corta(v) else v) for k, v in item.items()}]
        return None
    if not isinstance(item, str):
        return None
    texto = item.strip()
    if texto.upper() in _ORIGEN:
        return _de_texto(sesion, clave, texto)
    if _PREFIJO.match(texto) or sl.es_id(texto) or (clave in _SELECTOR_DE_CAMPO and sl.parece_selector(texto)):
        return _elementos_elegidos(sesion, clave, texto, None, elementos)
    return _de_texto(sesion, clave, texto)


def _una(sesion, clave, valor, elementos):
    refs = _refs(sesion, clave, valor, elementos)
    if refs is None:                     # no es una forma corta (p. ej. coordenadas [x, y, z] o la referencia guardada)
        return valor
    if len(refs) != 1:
        raise error("AMBIGUOUS_REFERENCE", f"«{clave}» guarda UNA referencia y {valor!r} eligió {len(refs)}.",
                    "Afiná el selector (p. ej. con and o nearest:[x,y,z]) o usá un id de find_faces / find_edges.")
    return refs[0]


def _lista(sesion, clave, valor, elementos):
    if not isinstance(valor, list):      # una sola forma corta (p. ej. "edges:|Z"); otra cosa queda igual
        refs = _refs(sesion, clave, valor, elementos)
        return valor if refs is None else refs
    salida = []
    for item in valor:
        refs = _refs(sesion, clave, item, elementos)
        salida.extend([item] if refs is None else refs)
    return salida


def _id_de_cuerpo(sesion, item, estricto):
    """Id del cuerpo que nombra `item`. Sin `estricto` (edit_feature) un nombre que no existe al final del timeline
    queda como está: el paso dice entonces qué cuerpo le falta y en qué paso."""
    if isinstance(item, dict) and set(item) == {"body"}:
        item = item["body"]
    if not isinstance(item, str) or not item.strip() or _ID_CUERPO.fullmatch(item.strip()):
        return item                      # vacío, un id (puede no existir al final: edit_feature) o el formato guardado
    try:
        return sesion.cuerpo(item).id
    except ErrorAPI as e:
        if estricto or e.error_kind != "BODY_NOT_FOUND":
            raise
        return item


def _cuerpos(sesion, valor, defecto, estricto):
    """Nombres de cuerpo → ids. Un texto suelto donde va una lista queda igual (el paso pide la lista)."""
    if isinstance(valor, list):
        return [_id_de_cuerpo(sesion, x, estricto) for x in valor]
    if isinstance(defecto, list):
        return valor
    return _id_de_cuerpo(sesion, valor, estricto)


def _perfiles_de_extrusion(sesion, valor, salida, actuales):
    """«perfiles» de extrusión y revolución (sin «tipo»: el boceto va en el campo «boceto»): índices, "all",
    "largest" o {"sketch", "profile"} → {"firma", "centroide"}. Completa «boceto» si falta."""
    from .herramientas_boceto import boceto_activo, op_boceto, seleccionar_perfiles
    lista = []
    for item in (valor if isinstance(valor, list) else [valor]):
        if isinstance(item, dict) and "sketch" not in item:
            lista.append(item)                                   # el formato guardado
            continue
        boceto = salida.get("boceto") or actuales.get("boceto")
        if isinstance(item, dict):
            if set(item) != {"sketch", "profile"}:
                raise error("INVALID_ARGUMENTS", f"«perfiles»: {item!r} no es un perfil.",
                            'Usá {"sketch": "Boceto1", "profile": 0} o el índice con «boceto».')
            sop = op_boceto(sesion, item["sketch"])
            if boceto and boceto != sop.id:
                raise error("INVALID_ARGUMENTS", f"Los perfiles tienen que ser del boceto del paso ({boceto}), no de "
                            f"«{sop.nombre}» ({sop.id}).")
            salida["boceto"], seleccion = sop.id, item["profile"]
        else:
            if not boceto:
                raise error("INVALID_ARGUMENTS", "Para elegir perfiles por índice, pasá también «boceto» (id o nombre).",
                            'O usá {"sketch": "Boceto1", "profile": 0}.')
            sop, seleccion = op_boceto(sesion, boceto), item
        sop, br = boceto_activo(sesion, sop.id)
        lista.extend(OpExtrusion.referencia_perfil(p) for p in seleccionar_perfiles(br, sop, seleccion))
    return lista


def traducir_referencias(sesion, clase, params, actuales=None, elementos=True):
    """(params con las formas cortas cambiadas por referencias, [campos cambiados]) para la operación `clase`.
    `actuales`: los parámetros del paso que se edita (el boceto de sus perfiles). Con `elementos=False` (edit_feature)
    no se aceptan ids de find_faces / find_edges ni selectores (valen para la pieza terminada, no para la de antes
    del paso) y un nombre de cuerpo que no está al final del timeline queda como está (el paso dirá cuál falta). El
    formato guardado pasa tal cual."""
    from .herramientas_boceto import op_boceto
    salida = dict(params)
    actuales = clase.PARAMS if actuales is None else actuales
    con_boceto = hasattr(clase, "referencia_perfil") and "boceto" in clase.PARAMS
    if con_boceto and isinstance(params.get("boceto"), str) and params["boceto"].strip():
        salida["boceto"] = op_boceto(sesion, params["boceto"]).id
    for clave, valor in params.items():
        if con_boceto and clave == "perfiles":
            salida[clave] = _perfiles_de_extrusion(sesion, valor, salida, actuales)
            continue
        if clave == "pivote" and isinstance(valor, str) and valor.strip().casefold() in ("center", "centro"):
            salida[clave] = None                    # Mover: el centro de la caja de los cuerpos (el valor por defecto)
            continue
        tipo = tipo_de_campo(clase, clave)
        if tipo is None or valor is None or (clase.TIPO == "operacion_base" and clave == "cuerpos"):
            continue
        if tipo == "cuerpos":
            salida[clave] = _cuerpos(sesion, valor, clase.PARAMS[clave], elementos)
        elif tipo == "una":
            salida[clave] = _una(sesion, clave, valor, elementos)
        else:
            salida[clave] = _lista(sesion, clave, valor, elementos)
    return salida, [k for k in salida if k not in params or salida[k] != params[k]]


@herramienta("list_operation_types", "avanzado", "Lista todos los tipos de operación del timeline que acepta "
             "run_operation: tipo, etiqueta y una línea que dice qué hace.")
def list_operation_types(sesion):
    tipos = [{"type": t, "label": c.ETIQUETA, "summary": _resumen_clase(c)} for t, c in TIPOS_OPERACION.items()]
    return {"count": len(tipos), "types": tipos}


# Qué espera cada campo de referencias, por su nombre; (tipo, campo) afina los que cambian según la operación.
_UN_PUNTO = ('un punto: "O" (origen), un punto de construcción, un punto de boceto ({"sketch": "Boceto1", "point": 3}) '
             'o un vértice')
_UN_EJE = ('un eje o una dirección: "X", "Y", "Z", un eje de construcción, una arista recta ("Cuerpo1/E7"), una línea '
           'de boceto ({"sketch": "Boceto1", "curve": 2}) o una cara plana (su normal)')
_CURVAS = 'curvas de boceto ({"sketch": "Boceto1", "curve": 2}) o aristas ("Cuerpo1/E7", "edges:>Z")'
_PERFILES = 'perfiles de boceto: {"sketch": "Boceto1", "profile": 0} (índice, lista, "all" o "largest")'
_ESPERA = {
    "cara": 'una cara ("Cuerpo1/F6", ">Z")', "caras": 'caras ("Cuerpo1/F6", ">Z", "%CYLINDER"…)',
    "caras_a": "caras", "caras_b": "caras", "aristas": 'aristas ("Cuerpo1/E7", "|Z"…)',
    "perfiles": _PERFILES, "perfil": _PERFILES,
    "secciones": 'perfiles ({"sketch": "Boceto1", "profile": 0}) o puntos, en el orden de la solevación',
    "posiciones": 'puntos de boceto ({"sketch": "Boceto1", "point": 3}: siguen al boceto), vértices, aristas circulares '
                  'o caras cilíndricas',
    "plano": 'un plano: "XY", "XZ", "YZ", un plano de construcción (id o nombre), un boceto o una cara plana',
    "eje": _UN_EJE, "eje_ref": _UN_EJE, "dir1": _UN_EJE, "dir2": _UN_EJE, "direccion": _UN_EJE, "eje_x": _UN_EJE,
    "eje_y": _UN_EJE,
    "pivote": _UN_PUNTO + '; vacío o "center" = el centro de la caja de los cuerpos',
    "punto": _UN_PUNTO, "centro": _UN_PUNTO, "origen": _UN_PUNTO, "destino": _UN_PUNTO, "puntos": "puntos (" + _UN_PUNTO + ")",
    "origen1": 'dónde se une el componente 1 (el que se mueve): una cara, una arista o un punto de un cuerpo suyo '
               '("Cuerpo1/F3")',
    "origen2": 'dónde se une el componente 2: una cara, una arista o un punto ("Cuerpo2/F5")',
    "ruta": _CURVAS, "carril": _CURVAS, "carriles": _CURVAS, "curvas": _CURVAS, "contorno": _CURVAS,
    "lineas": _CURVAS, "linea_central": _CURVAS, "pliegues": _CURVAS,
    "herramienta": 'un cuerpo, un plano o una cara', "herramientas": 'cuerpos ({"body": "Cuerpo1"}), planos ("XY") o caras',
    "hasta": "una cara, un plano o un cuerpo", "hasta2": "una cara, un plano o un cuerpo",
    "inicio_objeto": "una cara plana o un plano",
    "refs": "las referencias de la construcción, en orden: planos, ejes, puntos, caras, aristas, vértices o puntos de boceto",
}
_COORDENADAS = "coordenadas [x, y, z] en mm (no es una referencia)"
_ESPERA_TIPO = {
    ("plegar", "punto"): _COORDENADAS, ("desplegar", "punto"): _COORDENADAS, ("patron_plano", "punto"): _COORDENADAS,
    ("recortar_sup", "punto"): _COORDENADAS + ": el lado que se quita",
    ("patron", "referencia"): _UN_PUNTO + ' que se lleva a cada punto (forma_patron="puntos"); vacío = el origen',
    ("patron", "puntos"): 'puntos (' + _UN_PUNTO + ') o un boceto entero ("Boceto1": todos sus puntos sueltos)',
    ("origen_union", "origen"): 'dónde va el marco: una cara, una arista, un punto o un eje ("Cuerpo1/F3")',
    ("reemplazar_cara", "destino"): "la cara o el plano destino",
    ("alinear", "origen"): "lo que se mueve: una cara, una arista, un vértice o un punto",
    ("alinear", "destino"): "a dónde va: una cara, una arista, un vértice o un punto",
    ("operacion_base", "cuerpos"): 'ids o nombres de los cuerpos ("op1.c1", "Cuerpo1"): se congelan al crear el paso '
                                   '(guarda su B-rep)',
    ("grupo_rigido", "componentes"): 'componentes: el id del paso que creó cada uno ("op5"), su nombre o el id de uno '
                                     'de sus cuerpos (get_scene_info lista los componentes)',
    ("vinculo_movimiento", "union1"): 'el id del paso de la unión que manda ("op7"; get_scene_info lista las uniones)',
    ("vinculo_movimiento", "union2"): 'el id del paso de la unión que se mueve en proporción a union1',
}
_ESPERA_CUERPOS = 'ids o nombres de cuerpos (get_scene_info): "op1.c1", "Cuerpo1" o {"body": "Cuerpo1"}; se guarda el id'
# Aclaraciones de campos cuyo significado no sale del nombre (hallazgos de las pruebas de uso del 2026-10-09).
_NOTAS = {
    ("patron", "distribucion"): '"extension" (por defecto): d1, d2 y angulo son TOTALES, de la primera a la última '
                                'instancia; "espaciado": la separación (o el ángulo) entre instancias consecutivas. '
                                'rectangular_pattern guarda "espaciado"; circular_pattern, "extension".',
    ("patron", "d1"): 'con distribucion="extension" (por defecto) es la distancia TOTAL entre la primera y la última '
                      'instancia; con "espaciado", la separación entre instancias (el x_spacing de rectangular_pattern).',
    ("patron", "d2"): 'como d1, en la dirección 2.',
    ("patron", "angulo"): 'con distribucion="extension" (por defecto) es el ángulo TOTAL; con "espaciado", el ángulo '
                          'entre instancias.',
    ("primitiva", "ancho"): "caja: tamaño en X (el length de create_box).",
    ("primitiva", "largo"): "caja: tamaño en Y (el width de create_box).",
    ("primitiva", "alto"): "caja y cilindro: tamaño en Z (el height de create_box).",
    ("primitiva", "x"): "caja con caja_centrada=true (lo que guarda create_box): (x, y) es el centro de la base y z la "
                        "base; sin caja_centrada, (x, y, z) es la esquina mínima. Cilindro: centro de la base; esfera y "
                        "toroide: el centro.",
    ("primitiva", "caja_centrada"): "true: (x, y) es el centro de la base (create_box); false: la esquina mínima "
                                    "(recetas viejas y el diálogo con esa opción).",
    **dict.fromkeys((("mover", "dx"), ("mover", "dy"), ("mover", "dz")),
                    'tipo="libre" o "traslacion": desplazamiento que se SUMA a la posición actual (no es una posición); '
                    'para ir a una posición: tipo="punto_a_posicion" o move_body con position.'),
    **dict.fromkeys((("mover", "x"), ("mover", "y"), ("mover", "z")),
                    'tipo="punto_a_posicion": posición ABSOLUTA a la que va el punto «origen».'),
    ("agujero", "posiciones"): 'puntos de boceto ({"sketch": "Boceto1", "point": 3}): el agujero sigue al punto si el '
                               'boceto cambia (create_hole con sketch_points); dirección: hacia −normal del boceto.',
    ("agujero", "puntos_cara"): 'posiciones FIJAS: [{"cara": "Cuerpo1/F6" (o su referencia), "punto": [x, y, z]}] '
                                '(create_hole con points).',
    ("relleno_contorno", "celdas"): "índices de las regiones cerradas, ordenadas por centroide (x, y, z); [] = la 0.",
    **{(t, "objeto"): '"cuerpos" (repite los cuerpos de «cuerpos») u "operaciones" (repite la herramienta de los pasos '
                      'de «pasos»: un agujero, una extrusión que corta…, con la misma operación).'
       for t in ("patron", "multitransformar")},
    **{(t, "pasos"): 'ids de pasos anteriores ("op3") cuyo efecto se repite con objeto="operaciones".'
       for t in ("patron", "multitransformar")},
    ("patron", "giro"): 'forma_patron="ruta": giro total alrededor de la ruta; la copia k gira giro · k / (n1 − 1).',
    ("patron", "coordenadas"): 'forma_patron="puntos": puntos fijos [[x, y, z], …] (mm o expresiones).',
    ("patron", "referencia_xyz"): 'forma_patron="puntos": el punto [x, y, z] que se lleva a cada punto (si no hay '
                                    '«referencia»); [] = el origen.',
    ("multitransformar", "transformaciones"): 'lista ordenada de dicts {"tipo": "rectangular" | "circular" | "ruta" | '
                                              '"puntos" | "simetria", …} con las claves del patrón (dir1, n1, d1…) o '
                                              '"plano" en la simetría, con referencias guardadas ({"tipo": "eje", '
                                              '"id": "X"}); multi_transform las arma desde formas cortas.',
}


def _formato_de_campo(clase, clave):
    """Texto que dice qué espera un campo de referencias (None si el campo no guarda referencias)."""
    if (clase.TIPO, clave) in _ESPERA_TIPO:
        return _ESPERA_TIPO[(clase.TIPO, clave)]
    if hasattr(clase, "referencia_perfil") and clave == "perfiles":
        return 'perfiles del boceto de «boceto»: índices (0, [0, 2]), "all", "largest" o {"sketch": "Boceto1", "profile": 0}'
    tipo = tipo_de_campo(clase, clave)
    if tipo == "cuerpos":
        return _ESPERA_CUERPOS
    if tipo is None:
        return None
    espera = _ESPERA.get(clave, "una referencia" if tipo == "una" else "referencias")
    return ("UNA referencia: " if tipo == "una" else "lista de referencias: ") + espera


@herramienta("describe_operation", "avanzado", "Explica un tipo de operación: parámetros con su valor por defecto, "
             "tipo, si aceptan expresiones, en los de lista cerrada sus valores válidos (choices), en los que guardan "
             "referencias qué esperan y en qué formas cortas (format, reference_formats), aclaraciones (notes); el "
             "docstring completo y un ejemplo de llamada a run_operation.")
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
        formato = _formato_de_campo(clase, p["name"])
        if formato:
            p["format"] = formato
            if p["type"] == "any" and tipo_de_campo(clase, p["name"]) == "una" and "[x, y, z]" not in formato:
                p["type"] = "reference"
        nota = _NOTAS.get((clase.TIPO, p["name"]))
        if nota:
            p["notes"] = nota
    return {"type": clase.TIPO, "label": clase.ETIQUETA, "summary": _resumen_clase(clase),
            "doc": inspect.getdoc(clase) or "", "params": params,
            "expressions": [k for k in clase.PARAMS if k in expresiones],
            "reference_formats": FORMATOS_REFERENCIA, "example": _ejemplo(clase)}


@herramienta("run_operation", "avanzado", "Agrega al timeline cualquier operación por su tipo y sus parámetros nativos "
             "(claves en español, las de describe_operation). En los campos que guardan referencias acepta formas "
             "cortas y las traduce: ids de find_faces / find_edges (\"Cuerpo1/F3\"), selectores (\"faces:>Z\"), "
             "\"XY\", \"Z\", \"O\", planos/ejes/puntos de construcción y bocetos por id o nombre, "
             "{\"sketch\": …, \"point\" | \"curve\" | \"profile\": …}, {\"body\": …} y nombres de cuerpo en los "
             "campos de ids de cuerpo (describe_operation los lista). Lo que no reconoce llega igual al paso, que dice "
             "qué campo está mal. Una llamada = un paso de deshacer; si el paso falla, el documento queda intacto.",
             modifica=True)
def run_operation(sesion, type: str, params: dict | None = None, name: str | None = None):
    """
    type: tipo de operación (list_operation_types los lista).
    params: parámetros a cambiar respecto de los valores por defecto, con las claves de describe_operation. Las
        referencias pueden ir en forma corta (ver reference_formats de describe_operation).
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
    params, traducidos = traducir_referencias(sesion, clase, params)
    doc = sesion.doc
    antes = set(doc.estado_final.cuerpos)
    op = operacion_desde_dict({"tipo": clase.TIPO, "id": doc.nuevo_id(), "nombre": name or None, "params": params})
    resultado = doc.agregar(op)
    if op.TIPO == "patron" and "distribucion" not in params and {"d1", "d2", "angulo"} & set(params):
        sesion.avisar(f"«{op.nombre}»: {op.aclaracion_distancias()}")
    nuevos = [c for c in doc.estado_final.cuerpos if c not in antes]
    return {"id": op.id, "name": op.nombre, "type": op.TIPO, "status": resultado.estado, "message": resultado.mensaje,
            "new_bodies": nuevos, "bodies": list(doc.estado_final.cuerpos), "translated_params": traducidos}


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

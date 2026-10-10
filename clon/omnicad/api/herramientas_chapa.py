# -*- coding: utf-8 -*-
"""
Herramientas del grupo "chapa" (entorno CHAPA de Fusion; operaciones en `timeline/ops_chapa.py`, núcleo en
`nucleo/chapa.py`): reglas (de fábrica, propias y cambiar la de un cuerpo), pestaña base, de contorno y de arista,
dobladillo, plegar, desplegar y volver a plegar, patrón plano, convertir a chapa, desgarro, unir plegando,
exportar el patrón plano a DXF y la información de cada cuerpo de chapa.

REGLAS: espesor t, radio interior de plegado R, factor K (posición de la fibra neutra: la longitud desarrollada de
un pliegue es ángulo · (R + K·t)), alivios, separación y material físico (el cuerpo lo toma). Las de fábrica tienen
R = t y K = 0,44. Una regla propia (create_sheet_metal_rule) queda en la biblioteca del usuario (reglas_chapa.json
de la carpeta de datos, o la ruta de OMNICAD_REGLAS_CHAPA) y, al usarla, el paso guarda una copia en la receta: el
proyecto abre igual en otra PC. thickness, bend_radius y k_factor de cada herramienta anulan la regla (aceptan
expresiones con parámetros).

Caras y aristas se eligen como en el resto de la API: selector ('>Z', '%CYLINDER'…, evaluado sobre `body`) o id
de find_faces / find_edges ('Placa/F3', 'Placa/E7'); se guardan como referencias persistentes. La cara
estacionaria es la cara de arriba o de abajo de una parte plana: queda quieta al plegar o desplegar.
"""
import copy
import math
from pathlib import Path
from typing import Literal

import numpy as np

from ..nucleo import chapa
from ..nucleo import geometria as geo
from ..nucleo import referencias as nrefs
from ..timeline.ops_chapa import (OpConvertirChapa, OpDesgarro, OpDesplegar, OpDobladillo, OpPatronPlano, OpPestana,
                                  OpPlegar, OpUnirPlegando, es_chapa, es_patron_plano, exportar_dxf, modelo_actual)
from . import selectores as sl
from .errores import error
from .herramientas_boceto import boceto_activo, seleccionar_perfiles, texto_expr
from .herramientas_ensamble import nombre_paso
from .herramientas_material import nombre_material
from .herramientas_solido import _agregar, _numero_positivo, _ref_perfil
from .registro import Expr, herramienta

Elementos = str | list[str]
Lado = Literal["side1", "side2", "center"]
LADOS = {"side1": "lado1", "side2": "lado2", "center": "centro"}
ALIVIOS = {"round": "redondo", "straight": "recto", "tear": "desgarro"}
A_ALIVIOS = {v: k for k, v in ALIVIOS.items()}
Alivio = Literal["round", "straight", "tear"]
ESQUINAS = {"trim": "recortar", "round": "redondo", "square": "cuadrado", "tear": "desgarro"}
A_ESQUINAS = {v: k for k, v in ESQUINAS.items()}
Esquina = Literal["trim", "round", "square", "tear"]
DIRECCIONES = {"one_side": "un_lado", "two_sides": "dos_lados", "symmetric": "simetrica"}
REFERENCIAS = {"outer": "exterior", "inner": "interior", "tangent": "tangente"}
POSICIONES = {"inside": "interior", "outside": "exterior", "adjacent": "adyacente", "tangent": "tangente"}
ANCHOS = {"full": "completo", "symmetric": "simetrico", "two_sides": "dos_lados"}
DOBLADILLOS = {"closed": "cerrado", "open": "abierto", "teardrop": "lagrima"}
LINEAS = {"start": "inicio", "center": "centro", "end": "fin"}
UBICACIONES = {"in_place": "en_lugar", "beside": "junto"}
TOL_VERTICE = 1e-3          # mm: un punto de rip tiene que caer sobre un vértice de la chapa

_ELEGIR = ("se elige con un selector (evaluado sobre body) o un id de find_faces / find_edges. ")
_ANULAR = ("thickness, bend_radius y k_factor anulan la regla (vacío = el de la regla; aceptan número o expresión). ")


def _r(x):
    return None if x is None else round(float(x), 4) + 0.0


# ---------------------------------------------------------------- reglas
def _info_regla(r, origen=None):
    info = {"name": r["nombre"], "thickness": _r(r["espesor"]), "bend_radius": _r(r["radio"]), "k_factor": _r(r["k"]),
            "material": r.get("material"), "relief_shape": A_ALIVIOS.get(r["alivio_forma"], r["alivio_forma"]),
            "relief_width": _r(r["alivio_ancho"]), "relief_depth": _r(r["alivio_profundidad"]),
            "corner_relief": A_ESQUINAS.get(r["esquina_forma"], r["esquina_forma"]),
            "corner_size": _r(r["esquina_tam"]), "gap": _r(r["separacion"])}
    if origen:
        info["source"] = origen
    return info


def _pasos_con_regla(sesion):
    """Pasos que definen la regla de un cuerpo de chapa (pestaña base o de contorno, convertir a chapa)."""
    return [o for o in sesion.doc.operaciones if isinstance(o, OpConvertirChapa)
            or (isinstance(o, OpPestana) and o.p.get("tipo") in ("base", "contorno"))]


def _reglas_del_documento(sesion):
    """{nombre: definición} de las reglas propias copiadas en los pasos del documento."""
    salida = {}
    for o in _pasos_con_regla(sesion):
        d = o.p.get("regla_propia")
        if isinstance(d, dict) and d.get("nombre") == o.p.get("regla"):
            salida.setdefault(d["nombre"], d)
    return salida


def regla_para_paso(sesion, rule):
    """(nombre, definición o None) de la regla pedida: de fábrica (sin definición), propia del usuario o propia
    copiada en un paso del documento (con su definición, que el paso nuevo también copia). Sin distinguir
    mayúsculas; vacío = la regla por defecto."""
    if rule is None or not str(rule).strip():
        return chapa.REGLA_DEFECTO, None
    texto = str(rule).strip()
    del_doc = _reglas_del_documento(sesion)
    fuentes = [(chapa.REGLAS, False), (chapa.REGLAS_USUARIO, True), (del_doc, True)]
    for exacto in (True, False):
        for tabla, propia in fuentes:
            for n, d in tabla.items():
                if n == texto if exacto else n.casefold() == texto.casefold():
                    return n, (copy.deepcopy(d) if propia else None)
    todas = list(dict.fromkeys(list(chapa.REGLAS) + list(chapa.REGLAS_USUARIO) + list(del_doc)))
    raise error("SHEET_METAL_RULE_NOT_FOUND", f"No existe la regla de chapa «{texto}». Reglas: {', '.join(todas)}.")


def _ajustes(thickness=None, bend_radius=None, k_factor=None):
    for valor, que in ((thickness, "thickness"), (bend_radius, "bend_radius")):
        if valor is not None:
            _numero_positivo(valor, que)
    if isinstance(k_factor, (int, float)) and not 0 <= k_factor <= 1:
        raise error("INVALID_ARGUMENTS", f"k_factor va de 0 a 1 (recibió {k_factor:g}).")
    salida = {}
    for clave, valor in (("espesor", thickness), ("radio", bend_radius), ("k", k_factor)):
        if valor is not None:
            salida[clave] = texto_expr(valor)
    return salida


@herramienta("list_sheet_metal_rules", "chapa", "Reglas de chapa disponibles con todos sus valores (espesor, radio de "
             "plegado, factor K, alivios, separación y material): las de fábrica (builtin), las propias del usuario "
             "(user) y las propias copiadas en este documento (document), y qué pasos usa cada una.")
def list_sheet_metal_rules(sesion):
    usos = {}
    for o in _pasos_con_regla(sesion):
        usos.setdefault(o.p.get("regla") or chapa.REGLA_DEFECTO, []).append(o.id)
    reglas = [dict(_info_regla(chapa.regla(n), "builtin"), used_by=usos.get(n, [])) for n in chapa.REGLAS]
    reglas += [dict(_info_regla(chapa.regla(n, d), "user"), used_by=usos.get(n, []))
               for n, d in chapa.REGLAS_USUARIO.items() if n not in chapa.REGLAS]
    reglas += [dict(_info_regla(chapa.regla(n, d), "document"), used_by=usos.get(n, []))
               for n, d in _reglas_del_documento(sesion).items() if n not in chapa.REGLAS and n not in chapa.REGLAS_USUARIO]
    return {"rules": reglas, "default": chapa.REGLA_DEFECTO, "user_library_file": str(chapa.ruta_reglas_propias()),
            "units": {"length": "mm"}}


@herramienta("create_sheet_metal_rule", "chapa", "Crea una regla de chapa propia (Reglas de chapa › Nueva regla): "
             "espesor, factor K, radio de plegado, material y, si hace falta, alivios y separación; lo que no se da "
             "sigue al espesor como en las de fábrica (radio = t, alivio t × t/2, esquina 4·t, separación t). Queda en "
             "la biblioteca del usuario (save=true) para todos los documentos; los pasos que la usan guardan una "
             "copia en la receta. No pisa las de fábrica. No cambia el documento.")
def create_sheet_metal_rule(sesion, name: str, thickness: float, k_factor: float = 0.44, bend_radius: float | None = None,
                            material: str | None = None, relief_shape: Alivio | None = None,
                            relief_width: float | None = None, relief_depth: float | None = None,
                            corner_relief: Esquina | None = None, corner_size: float | None = None,
                            gap: float | None = None, overwrite: bool = False, save: bool = True):
    """
    name: nombre de la regla (p. ej. "Latón 0.8 mm").
    thickness: espesor de la chapa en mm.
    k_factor: factor K de 0 a 1 (posición de la fibra neutra); 0,44 por defecto.
    bend_radius: radio interior de plegado en mm; vacío = igual al espesor.
    material: material físico de la chapa (list_materials); vacío = sin material.
    relief_shape: alivio de plegado: "round", "straight" o "tear"; vacío = round.
    relief_width: ancho del alivio de plegado en mm; vacío = el espesor.
    relief_depth: profundidad del alivio en mm; vacío = la mitad del espesor.
    corner_relief: alivio de esquina entre dos pliegues: "trim", "round", "square" o "tear"; vacío = trim.
    corner_size: tamaño del alivio de esquina en mm; vacío = 4 × espesor.
    gap: separación de desgarros y esquinas en mm; vacío = el espesor.
    overwrite: true para reemplazar una regla propia que ya existe con ese nombre.
    save: true la guarda en la biblioteca del usuario para las próximas sesiones; false, solo en esta sesión.
    """
    texto = str(name).strip()
    if any(texto.casefold() == n.casefold() for n in chapa.REGLAS):
        raise error("NAME_EXISTS", f"«{texto}» es una regla de fábrica: no se puede redefinir.",
                    "Elegí otro nombre para la regla propia.")
    existente = next((n for n in chapa.REGLAS_USUARIO if n.casefold() == texto.casefold()), None)
    if existente is not None and not overwrite:
        raise error("NAME_EXISTS", f"Ya existe la regla propia «{existente}».")
    mat = None if material is None or not str(material).strip() else nombre_material(material)
    definicion = {"nombre": texto, "espesor": thickness, "k": k_factor, "material": mat, "radio": bend_radius,
                  "alivio_forma": None if relief_shape is None else ALIVIOS[relief_shape],
                  "alivio_ancho": relief_width, "alivio_profundidad": relief_depth,
                  "esquina_forma": None if corner_relief is None else ESQUINAS[corner_relief],
                  "esquina_tam": corner_size, "separacion": gap}
    try:
        chapa.definicion_regla(**definicion)                 # valida antes de tocar la biblioteca
        if existente is not None and existente != texto:
            chapa.quitar_regla(existente, guardar=save)
        d = chapa.definir_regla(definicion, guardar=save)
    except geo.ErrorGeometria as e:
        raise error("INVALID_ARGUMENTS", str(e)) from e
    resultado = {"rule": _info_regla(chapa.regla(d["nombre"], d), "user"), "replaced": existente is not None,
                 "saved": bool(save)}
    if save:
        resultado["library_file"] = str(chapa.ruta_reglas_propias())
    usan = [o.id for o in _pasos_con_regla(sesion) if o.p.get("regla") == d["nombre"]]
    if usan and existente is not None:
        sesion.avisar(f"Los pasos {', '.join(usan)} tienen la versión anterior copiada en la receta: para que tomen la "
                      "nueva, usá set_sheet_metal_rule con rule=«" + d["nombre"] + "».")
    return resultado


@herramienta("delete_sheet_metal_rule", "chapa", "Borra una regla propia de la biblioteca del usuario (las de fábrica no "
             "se borran). Los pasos que ya la usan siguen igual: tienen la regla copiada en la receta.")
def delete_sheet_metal_rule(sesion, name: str, save: bool = True):
    """
    name: nombre de la regla propia.
    save: true también la saca del archivo de la biblioteca; false, solo de esta sesión.
    """
    texto = str(name).strip()
    nombre = next((n for n in chapa.REGLAS_USUARIO if n.casefold() == texto.casefold()), None)
    if nombre is None:
        if any(texto.casefold() == n.casefold() for n in chapa.REGLAS):
            raise error("INVALID_ARGUMENTS", f"«{texto}» es una regla de fábrica: no se borra.")
        raise error("SHEET_METAL_RULE_NOT_FOUND", f"No hay una regla propia llamada «{texto}» en la biblioteca.")
    chapa.quitar_regla(nombre, guardar=save)
    return {"deleted": nombre}


# ---------------------------------------------------------------- cuerpos de chapa
def _es_de_chapa(c):
    return getattr(c, "chapa", None) is not None


def cuerpo_chapa(sesion, body=None, patron=False):
    """El cuerpo de chapa pedido o, sin `body`, el único que haya. `patron` acepta también un patrón plano."""
    estado = sesion.doc.estado_final
    if body is not None and str(body).strip():
        c = sesion.cuerpo(body)
        if not (es_chapa(c) or (patron and es_patron_plano(c))):
            raise error("NOT_SHEET_METAL", f"«{sesion.nombre_cuerpo(c)}» no es un cuerpo de chapa"
                        + (" (es un patrón plano)." if es_patron_plano(c) else "."))
        return c
    cuerpos = [c for c in estado.cuerpos.values() if es_chapa(c)]
    if not cuerpos:
        raise error("NOT_SHEET_METAL", "El documento no tiene cuerpos de chapa.")
    if len(cuerpos) > 1:
        raise error("AMBIGUOUS_REFERENCE", f"Hay {len(cuerpos)} cuerpos de chapa ("
                    + ", ".join(f"{sesion.nombre_cuerpo(c)} ({c.id})" for c in cuerpos) + "): elegí uno con body.")
    return cuerpos[0]


def info_chapa(sesion, c):
    m = modelo_actual(c)
    r = chapa.resumen(m)
    doc = sesion.doc
    return {"id": c.id, "name": sesion.nombre_cuerpo(c), "is_flat_pattern": es_patron_plano(c),
            "flat_pattern_of": m.get("patron_de"), "rule": _info_regla(m["regla"]), "rule_step": m.get("op_regla"),
            "bends": r["pliegues"], "unfolded_bends": r["desplegados"],
            "flat_size": [_r(r["ancho"]), _r(r["alto"])], "flat_area": _r(r["area"]),
            "volume": _r(geo.volumen(c.forma)),
            "material": doc.propiedad(c.id, "material") or getattr(c, "material", None)}


def _con_chapa(sesion, resultado):
    """Suma al informe de `_agregar` el estado de chapa de los cuerpos creados o modificados."""
    estado = sesion.doc.estado_final
    ids = [b["id"] for b in resultado["bodies_created"] + resultado["bodies_modified"]]
    resultado["sheet_metal"] = [info_chapa(sesion, estado.cuerpos[i]) for i in ids
                                if i in estado.cuerpos and _es_de_chapa(estado.cuerpos[i])]
    return resultado


def _agregar_chapa(sesion, op):
    return _con_chapa(sesion, _agregar(sesion, op))


def _refs(sesion, spec, tipo, body=None):
    elegidos = sl.elegir(sesion, spec, tipo, body)
    return [sl.referencia(c, e) for c, e in elegidos], elegidos


def _cara(sesion, face, body=None):
    c, e = sl.elegir_uno(sesion, face, "cara", body)
    sl.plano_de_cara(e)
    return sl.referencia(c, e), c, e


def _punto(p, que):
    if p is None:
        return None
    if len(p) != 3 or not all(math.isfinite(x) for x in p):
        raise error("INVALID_ARGUMENTS", f"{que} va como [x, y, z] en mm.")
    return [float(x) for x in p]


@herramienta("get_sheet_metal_info", "chapa", "Cuerpos de chapa (y patrones planos) con su regla (espesor, radio, K, "
             "material), el paso que la define, cantidad de pliegues y desplegados, y el tamaño (ancho × alto, mm) y "
             "el área del patrón plano. Sirve para verificar el desarrollo antes de exportar el DXF.")
def get_sheet_metal_info(sesion, body: str | None = None):
    """
    body: id o nombre de un cuerpo de chapa o de un patrón plano; vacío = todos.
    """
    if body is not None and str(body).strip():
        return {"bodies": [info_chapa(sesion, cuerpo_chapa(sesion, body, patron=True))]}
    return {"bodies": [info_chapa(sesion, c) for c in sesion.doc.estado_final.cuerpos.values() if _es_de_chapa(c)]}


# ---------------------------------------------------------------- pestañas
@herramienta("create_base_flange", "chapa", "Pestaña base (CHAPA › Pestaña, tipo base): convierte perfiles cerrados de "
             "un boceto en una placa de chapa con la regla elegida (crea un cuerpo de chapa nuevo por perfil). side: "
             "side1 (el espesor hacia la normal del boceto), side2 (hacia el otro lado) o center. " + _ANULAR,
             modifica=True)
def create_base_flange(sesion, sketch: str, profile: int | list[int] | str = 0, rule: str | None = None,
                       side: Lado = "side1", thickness: Expr | None = None, bend_radius: Expr | None = None,
                       k_factor: Expr | None = None, name: str | None = None):
    """
    sketch: id o nombre del boceto.
    profile: perfil(es): índice (get_sketch los lista), lista de índices, "all" o "largest".
    rule: regla de chapa (list_sheet_metal_rules); vacío = "Acero 1 mm".
    side: "side1", "side2" o "center".
    thickness: espesor en mm que anula el de la regla (número o expresión).
    bend_radius: radio de plegado en mm que anula el de la regla.
    k_factor: factor K que anula el de la regla (0 a 1).
    name: nombre del paso; vacío = «Pestaña<n>».
    """
    sop, br = boceto_activo(sesion, sketch)
    perfiles = seleccionar_perfiles(br, sop, profile)
    nombre, definicion = regla_para_paso(sesion, rule)
    doc = sesion.doc
    op = OpPestana(doc.nuevo_id(), nombre_paso(sesion, name, "Pestaña", OpPestana), tipo="base",
                   perfiles=[_ref_perfil(sop, x) for x in perfiles], orientacion=LADOS[side], regla=nombre,
                   regla_propia=definicion, ajustes=_ajustes(thickness, bend_radius, k_factor),
                   anular=any(v is not None for v in (thickness, bend_radius, k_factor)))
    resultado = _agregar_chapa(sesion, op)
    resultado["profiles_used"] = [br.perfiles.index(x) for x in perfiles]
    return resultado


@herramienta("create_contour_flange", "chapa", "Pestaña de contorno (CHAPA › Pestaña de contorno): un perfil ABIERTO de "
             "líneas y arcos de un boceto se extruye como chapa plegada, con el radio de la regla en cada esquina viva. "
             "direction: one_side (distance hacia la normal del boceto), two_sides (distance y distance2) o "
             "symmetric. side: de qué lado del perfil queda el espesor. " + _ANULAR, modifica=True)
def create_contour_flange(sesion, sketch: str, curves: list[int] | None = None, distance: Expr = 20,
                          rule: str | None = None, side: Lado = "side1",
                          direction: Literal["one_side", "two_sides", "symmetric"] = "one_side",
                          distance2: Expr | None = None, thickness: Expr | None = None, bend_radius: Expr | None = None,
                          k_factor: Expr | None = None, name: str | None = None):
    """
    sketch: id o nombre del boceto con el perfil abierto.
    curves: ids de las curvas del perfil (get_sketch), en cadena abierta; vacío = todas las no de construcción.
    distance: largo de la extrusión en mm (número o expresión).
    rule: regla de chapa (list_sheet_metal_rules); vacío = "Acero 1 mm".
    side: "side1", "side2" o "center".
    direction: "one_side", "two_sides" o "symmetric".
    distance2: largo del segundo lado con direction="two_sides"; vacío = 10 mm.
    thickness: espesor en mm que anula el de la regla.
    bend_radius: radio de plegado en mm que anula el de la regla.
    k_factor: factor K que anula el de la regla (0 a 1).
    name: nombre del paso; vacío = «Pestaña<n>».
    """
    _numero_positivo(distance, "distance")
    sop, br = boceto_activo(sesion, sketch)
    ids = list(curves) if curves else [c.id for c in br.boceto.curvas.values() if not c.construccion]
    for cid in ids:
        if cid not in br.boceto.curvas:
            raise error("ENTITY_NOT_FOUND", f"El boceto «{sop.nombre}» no tiene la curva {cid}.")
    if not ids:
        raise error("ENTITY_NOT_FOUND", f"El boceto «{sop.nombre}» no tiene curvas.")
    nombre, definicion = regla_para_paso(sesion, rule)
    doc = sesion.doc
    p = {"tipo": "contorno", "curvas": [{"tipo": "curva_boceto", "boceto": sop.id, "curva": cid} for cid in ids],
         "distancia": texto_expr(distance), "direccion": DIRECCIONES[direction], "orientacion": LADOS[side],
         "regla": nombre, "regla_propia": definicion, "ajustes": _ajustes(thickness, bend_radius, k_factor),
         "anular": any(v is not None for v in (thickness, bend_radius, k_factor))}
    if distance2 is not None:
        p["distancia2"] = texto_expr(distance2)
    op = OpPestana(doc.nuevo_id(), nombre_paso(sesion, name, "Pestaña", OpPestana), **p)
    resultado = _agregar_chapa(sesion, op)
    resultado["curves_used"] = ids
    return resultado


@herramienta("create_edge_flange", "chapa", "Pestaña de arista (CHAPA › Pestaña en aristas de chapa): levanta una "
             "pestaña con pliegue en cada arista recta del borde de la cara de arriba o de abajo de la chapa; las "
             "aristas " + _ELEGIR + "height_reference: outer (altura hasta las caras exteriores), inner o tangent (hasta "
             "donde termina el pliegue). bend_position: inside (la pestaña queda dentro del contorno), outside, adjacent "
             "o tangent. width: full (toda la arista), symmetric (width_distance centrado) o two_sides (width1 y "
             "width2 desde los extremos). bend_radius y los alivios anulan la regla.", modifica=True)
def create_edge_flange(sesion, edges: Elementos, height: Expr = 20, angle: Expr = 90,
                       height_reference: Literal["outer", "inner", "tangent"] = "outer",
                       bend_position: Literal["inside", "outside", "adjacent", "tangent"] = "inside",
                       width: Literal["full", "symmetric", "two_sides"] = "full", width_distance: Expr = 20,
                       width1: Expr = 10, width2: Expr = 10, flip: bool = False, bend_radius: Expr | None = None,
                       relief_shape: Alivio | None = None, relief_width: Expr | None = None,
                       relief_depth: Expr | None = None, body: str | None = None, name: str | None = None):
    """
    edges: aristas rectas de la chapa: selector (p. ej. ">Y and >Z" = la de arriba del lado +Y), id de find_edges o lista.
    height: altura de la pestaña en mm (número o expresión).
    angle: ángulo de plegado en grados (90 = a escuadra).
    height_reference: "outer", "inner" o "tangent".
    bend_position: "inside", "outside", "adjacent" o "tangent".
    width: "full", "symmetric" o "two_sides".
    width_distance: ancho de la pestaña con width="symmetric", en mm.
    width1: distancia desde el inicio de la arista con width="two_sides", en mm.
    width2: distancia desde el final de la arista con width="two_sides", en mm.
    flip: true pliega hacia el otro lado.
    bend_radius: radio de plegado en mm que anula el de la regla; vacío = el de la regla.
    relief_shape: forma del alivio de plegado que anula la regla: "round", "straight" o "tear".
    relief_width: ancho del alivio en mm que anula la regla.
    relief_depth: profundidad del alivio en mm que anula la regla.
    body: cuerpo de chapa sobre el que se evalúan los selectores; vacío = el único cuerpo.
    name: nombre del paso; vacío = «Pestaña<n>».
    """
    _numero_positivo(height, "height")
    if isinstance(angle, (int, float)) and not 0 < abs(angle) <= 180:
        raise error("INVALID_ARGUMENTS", f"angle va entre 0 y 180 grados (recibió {angle:g}).")
    for valor, que in ((bend_radius, "bend_radius"), (relief_width, "relief_width")):
        if valor is not None:
            _numero_positivo(valor, que)
    refs, elegidos = _refs(sesion, edges, "arista", body)
    anular = any(v is not None for v in (bend_radius, relief_shape, relief_width, relief_depth))
    doc = sesion.doc
    op = OpPestana(doc.nuevo_id(), nombre_paso(sesion, name, "Pestaña", OpPestana), tipo="arista", aristas=refs,
                   altura=texto_expr(height), angulo=texto_expr(angle), referencia=REFERENCIAS[height_reference],
                   posicion=POSICIONES[bend_position], ancho=ANCHOS[width], ancho_distancia=texto_expr(width_distance),
                   ancho1=texto_expr(width1), ancho2=texto_expr(width2), invertir=bool(flip), anular=anular,
                   radio="" if bend_radius is None else texto_expr(bend_radius),
                   alivio_forma="" if relief_shape is None else ALIVIOS[relief_shape],
                   alivio_ancho="" if relief_width is None else texto_expr(relief_width),
                   alivio_profundidad="" if relief_depth is None else texto_expr(relief_depth))
    resultado = _agregar_chapa(sesion, op)
    resultado["edges_used"] = len(elegidos)
    return resultado


@herramienta("create_hem", "chapa", "Dobladillo (CHAPA › Dobladillo): dobla el borde de la chapa sobre sí mismo en las "
             "aristas rectas elegidas; las aristas " + _ELEGIR + "hem_type: closed (plano, sin separación), open "
             "(con separación gap) o teardrop (lágrima, con radio). position: adjacent (el pliegue fuera del borde) o "
             "tangent.", modifica=True)
def create_hem(sesion, edges: Elementos, hem_type: Literal["closed", "open", "teardrop"] = "closed", length: Expr = 10,
               gap: Expr | None = None, radius: Expr | None = None,
               position: Literal["adjacent", "tangent"] = "adjacent", flip: bool = False, body: str | None = None,
               name: str | None = None):
    """
    edges: aristas rectas del borde de la chapa: selector, id de find_edges o lista.
    hem_type: "closed", "open" o "teardrop".
    length: largo del tramo doblado en mm (número o expresión).
    gap: separación entre la chapa y el tramo doblado en mm (open y teardrop); vacío = la de la regla.
    radius: radio de la lágrima en mm (teardrop); vacío = el de la regla.
    position: "adjacent" o "tangent".
    flip: true dobla hacia el otro lado.
    body: cuerpo de chapa sobre el que se evalúan los selectores; vacío = el único cuerpo.
    name: nombre del paso; vacío = «Dobladillo<n>».
    """
    _numero_positivo(length, "length")
    refs, elegidos = _refs(sesion, edges, "arista", body)
    doc = sesion.doc
    op = OpDobladillo(doc.nuevo_id(), nombre_paso(sesion, name, "Dobladillo", OpDobladillo), aristas=refs,
                      tipo=DOBLADILLOS[hem_type], longitud=texto_expr(length),
                      separacion="" if gap is None else texto_expr(gap),
                      radio="" if radius is None else texto_expr(radius), posicion=POSICIONES[position],
                      invertir=bool(flip))
    resultado = _agregar_chapa(sesion, op)
    resultado["edges_used"] = len(elegidos)
    return resultado


# ---------------------------------------------------------------- plegar, desplegar, patrón plano
@herramienta("fold", "chapa", "Plegar (CHAPA › Plegar): pliega la chapa por líneas rectas de un boceto dibujado sobre "
             "la cara (create_sketch con plane = la cara). face es la cara estacionaria (" + _ELEGIR.strip() +
             "); fixed_point dice qué lado de la línea queda quieto (un punto [x, y, z] sobre la cara; vacío = un "
             "punto de la cara). line_position: start, center o end (dónde cae la línea respecto del pliegue).",
             modifica=True)
def fold(sesion, face: str, sketch: str, lines: list[int] | None = None, angle: Expr = 90,
         line_position: Literal["start", "center", "end"] = "center", flip: bool = False,
         bend_radius: Expr | None = None, fixed_point: list[float] | None = None, body: str | None = None,
         name: str | None = None):
    """
    face: cara estacionaria (la de arriba o la de abajo de una parte plana): selector o id de find_faces.
    sketch: id o nombre del boceto con las líneas de plegado.
    lines: ids de las líneas del boceto (get_sketch); vacío = todas las líneas no de construcción.
    angle: ángulo de plegado en grados.
    line_position: "start", "center" o "end".
    flip: true pliega hacia el otro lado.
    bend_radius: radio de plegado en mm que anula el de la regla; vacío = el de la regla.
    fixed_point: punto [x, y, z] en mm sobre la cara, del lado que queda quieto; vacío = un punto de la cara.
    body: cuerpo de chapa sobre el que se evalúa el selector de face.
    name: nombre del paso; vacío = «Plegado<n>».
    """
    ref, _c, _e = _cara(sesion, face, body)
    sop, br = boceto_activo(sesion, sketch)
    ids = list(lines) if lines else [c.id for c in br.boceto.curvas.values()
                                     if not c.construccion and c.tipo == "linea"]
    for cid in ids:
        curva = br.boceto.curvas.get(cid)
        if curva is None:
            raise error("ENTITY_NOT_FOUND", f"El boceto «{sop.nombre}» no tiene la curva {cid}.")
        if curva.tipo != "linea":
            raise error("INVALID_ARGUMENTS", f"La curva {cid} de «{sop.nombre}» no es una línea: los plegados van por "
                        "líneas rectas.")
    if not ids:
        raise error("ENTITY_NOT_FOUND", f"El boceto «{sop.nombre}» no tiene líneas.")
    doc = sesion.doc
    op = OpPlegar(doc.nuevo_id(), nombre_paso(sesion, name, "Plegado", OpPlegar), cara=ref,
                  punto=_punto(fixed_point, "fixed_point"),
                  lineas=[{"tipo": "curva_boceto", "boceto": sop.id, "curva": cid} for cid in ids],
                  angulo=texto_expr(angle), posicion=LINEAS[line_position], invertir=bool(flip),
                  anular=bend_radius is not None, radio="" if bend_radius is None else texto_expr(bend_radius))
    resultado = _agregar_chapa(sesion, op)
    resultado["lines_used"] = ids
    return resultado


@herramienta("unfold", "chapa", "Desplegar (CHAPA › Desplegar): endereza pliegues de la chapa, todos o los elegidos "
             "(caras curvas de los pliegues), con la cara estacionaria quieta. Es un paso del timeline: lo que se "
             "agregue después (p. ej. agujeros que crucen un pliegue) se hace sobre la pieza desplegada; refold la "
             "vuelve a plegar.", modifica=True)
def unfold(sesion, face: str, bends: Elementos | None = None, fixed_point: list[float] | None = None,
           body: str | None = None, name: str | None = None):
    """
    face: cara estacionaria (la de arriba o la de abajo de una parte plana): selector o id de find_faces.
    bends: caras curvas de los pliegues a desplegar (selector como "%CYLINDER", id o lista); vacío = todos.
    fixed_point: punto [x, y, z] en mm sobre la cara estacionaria (desempata si hay varias); vacío = un punto de la cara.
    body: cuerpo de chapa sobre el que se evalúan los selectores.
    name: nombre del paso; vacío = «Desplegado<n>».
    """
    ref, _c, _e = _cara(sesion, face, body)
    pliegues = []
    if bends:
        pliegues, _ = _refs(sesion, bends, "cara", body)
    doc = sesion.doc
    op = OpDesplegar(doc.nuevo_id(), nombre_paso(sesion, name, "Desplegado", OpDesplegar,
                                                          lambda o: o.p.get("modo") == "desplegar"),
                     modo="desplegar", cara=ref, punto=_punto(fixed_point, "fixed_point"), todos=not pliegues,
                     pliegues=pliegues)
    return _agregar_chapa(sesion, op)


@herramienta("refold", "chapa", "Volver a plegar (CHAPA › Volver a plegar): vuelve a plegar los pliegues desplegados "
             "del cuerpo. face (opcional) es la cara que queda quieta; sin ella, la misma que al desplegar.",
             modifica=True)
def refold(sesion, body: str | None = None, face: str | None = None, fixed_point: list[float] | None = None,
           name: str | None = None):
    """
    body: id o nombre del cuerpo de chapa; vacío = el único cuerpo de chapa.
    face: cara estacionaria (selector o id); vacío = la del desplegado.
    fixed_point: punto [x, y, z] en mm sobre esa cara; vacío = un punto de la cara.
    name: nombre del paso; vacío = «Replegado<n>».
    """
    c = cuerpo_chapa(sesion, body)
    ref = None
    if face is not None and str(face).strip():
        ref, c2, _e = _cara(sesion, face, c.id)
        if c2.id != c.id:
            raise error("INVALID_ARGUMENTS", "La cara tiene que ser del mismo cuerpo de chapa.")
    doc = sesion.doc
    op = OpDesplegar(doc.nuevo_id(), nombre_paso(sesion, name, "Replegado", OpDesplegar,
                                                          lambda o: o.p.get("modo") == "replegar"),
                     modo="replegar", cuerpo=c.id, cara=ref, punto=_punto(fixed_point, "fixed_point"))
    return _agregar_chapa(sesion, op)


@herramienta("create_flat_pattern", "chapa", "Crear patrón plano (CHAPA › Crear patrón plano): cuerpo nuevo con la "
             "pieza desplegada (desarrollo exacto con el factor K) sobre la cara estacionaria (in_place) o al lado de "
             "la pieza sin tocar otros cuerpos (beside). Como en Fusion, no cuenta como pieza del modelo "
             "(propiedades, interferencias y exportar «todo» lo ignoran). Devuelve el tamaño del desarrollo.",
             modifica=True)
def create_flat_pattern(sesion, face: str, location: Literal["in_place", "beside"] = "in_place",
                        fixed_point: list[float] | None = None, body: str | None = None, name: str | None = None):
    """
    face: cara estacionaria (la de arriba o la de abajo de una parte plana): selector o id de find_faces.
    location: "in_place" (sobre la cara estacionaria) o "beside" (al lado de la pieza).
    fixed_point: punto [x, y, z] en mm sobre la cara (desempata); vacío = un punto de la cara.
    body: cuerpo de chapa sobre el que se evalúa el selector.
    name: nombre del paso; vacío = «Patrón plano<n>».
    """
    ref, _c, _e = _cara(sesion, face, body)
    doc = sesion.doc
    op = OpPatronPlano(doc.nuevo_id(), nombre_paso(sesion, name, "Patrón plano", OpPatronPlano), cara=ref,
                       punto=_punto(fixed_point, "fixed_point"), ubicacion=UBICACIONES[location])
    return _agregar_chapa(sesion, op)


# ---------------------------------------------------------------- convertir, desgarro, unir plegando
@herramienta("convert_to_sheet_metal", "chapa", "Convertir a chapa (CHAPA › Convertir a chapa): una placa plana de "
             "espesor constante (p. ej. una caja delgada) pasa a ser de chapa; el espesor se mide desde la cara elegida "
             "y reemplaza al de la regla, que aporta radio, K, alivios y material.", modifica=True)
def convert_to_sheet_metal(sesion, face: str, rule: str | None = None, bend_radius: Expr | None = None,
                           k_factor: Expr | None = None, body: str | None = None, name: str | None = None):
    """
    face: una cara plana ANCHA de la placa (la de arriba o la de abajo): selector o id de find_faces.
    rule: regla plantilla (list_sheet_metal_rules); vacío = "Acero 1 mm".
    bend_radius: radio de plegado en mm que anula el de la regla.
    k_factor: factor K que anula el de la regla (0 a 1).
    body: cuerpo sobre el que se evalúa el selector.
    name: nombre del paso; vacío = «Convertir a chapa<n>».
    """
    ref, c, _e = _cara(sesion, face, body)
    if _es_de_chapa(c):
        raise error("INVALID_ARGUMENTS", f"«{sesion.nombre_cuerpo(c)}» ya es un cuerpo de chapa.")
    nombre, definicion = regla_para_paso(sesion, rule)
    doc = sesion.doc
    op = OpConvertirChapa(doc.nuevo_id(), nombre_paso(sesion, name, "Convertir a chapa", OpConvertirChapa), cara=ref,
                          regla=nombre, regla_propia=definicion, ajustes=_ajustes(None, bend_radius, k_factor))
    return _agregar_chapa(sesion, op)


def _vertice(sesion, cuerpo, p):
    """Referencia al vértice de la chapa que está en `p` [x, y, z]."""
    vertices = nrefs.subformas(cuerpo.forma, "vertice")
    puntos = [np.array(nrefs.firma_vertice(v)["punto"], float) for v in vertices]
    if not puntos:
        raise error("ELEMENT_NOT_FOUND", f"«{sesion.nombre_cuerpo(cuerpo)}» no tiene vértices.")
    d = [float(np.linalg.norm(q - np.asarray(p, float))) for q in puntos]
    i = int(np.argmin(d))
    if d[i] > TOL_VERTICE:
        cerca = [_r(x) for x in puntos[i]]
        raise error("ELEMENT_NOT_FOUND", f"No hay un vértice de «{sesion.nombre_cuerpo(cuerpo)}» en {list(p)}: el más "
                    f"cercano está en {cerca} (a {d[i]:.3g} mm).",
                    "Para un punto que no es un vértice, dibujalo en un boceto y pasá {\"sketch\": …, \"point\": id}.")
    return nrefs.referencia(cuerpo.id, vertices[i], cuerpo.forma)


def _ref_punto(sesion, cuerpo, item):
    if isinstance(item, dict):
        if set(item) != {"sketch", "point"} or not isinstance(item["point"], int) or isinstance(item["point"], bool):
            raise error("INVALID_ARGUMENTS", f"Un punto de boceto va como {{\"sketch\": id o nombre, \"point\": id}}: "
                        f"llegó {item!r}.")
        sop, br = boceto_activo(sesion, item["sketch"])
        if item["point"] not in br.boceto.puntos:
            raise error("ENTITY_NOT_FOUND", f"El boceto «{sop.nombre}» no tiene el punto {item['point']}.")
        return {"tipo": "punto_boceto", "boceto": sop.id, "punto": item["point"]}
    if isinstance(item, (list, tuple)) and len(item) == 3 and all(
            isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) for x in item):
        return _vertice(sesion, cuerpo, item)
    raise error("INVALID_ARGUMENTS", f"Cada punto va como [x, y, z] (un vértice de la chapa) o {{\"sketch\": …, "
                f"\"point\": id}}: llegó {item!r}.")


@herramienta("rip", "chapa", "Desgarro (CHAPA › Desgarro): mode=face quita la cara elegida (un pliegue —cara curva— o "
             "una parte plana); mode=points corta una ranura de ancho gap entre dos puntos del borde de la cara "
             "elegida (vértices [x, y, z] de la chapa o puntos de un boceto {\"sketch\", \"point\"}), del lado side. Si "
             "la pieza queda partida, cada pedazo es un cuerpo de chapa (bodies_created).", modifica=True)
def rip(sesion, face: str, mode: Literal["face", "points"] = "face", points: list[list[float] | dict] | None = None,
        side: Lado = "center", gap: Expr | None = None, body: str | None = None, name: str | None = None):
    """
    face: con mode="face", la cara a quitar; con mode="points", la cara cuyo borde tiene los dos puntos (selector o id).
    mode: "face" o "points".
    points: con mode="points", dos puntos del borde: [x, y, z] de un vértice o {"sketch": id, "point": id}.
    side: con mode="points", de qué lado de la línea p1→p2 va la ranura: "side1", "side2" o "center".
    gap: ancho de la ranura en mm; vacío = la separación de la regla.
    body: cuerpo de chapa sobre el que se evalúa el selector.
    name: nombre del paso; vacío = «Desgarro<n>».
    """
    c, e = sl.elegir_uno(sesion, face, "cara", body)
    ref = sl.referencia(c, e)
    p = {"modo": "cara" if mode == "face" else "puntos", "cara": ref}
    if mode == "points":
        if not points or len(points) != 2:
            raise error("INVALID_ARGUMENTS", "mode=points necesita exactamente dos puntos del borde de la cara.")
        if gap is not None:
            _numero_positivo(gap, "gap")
        p.update(puntos=[_ref_punto(sesion, c, x) for x in points], lado=LADOS[side],
                 separacion="" if gap is None else texto_expr(gap))
    elif points:
        raise error("INVALID_ARGUMENTS", "points solo se usa con mode=points.")
    doc = sesion.doc
    op = OpDesgarro(doc.nuevo_id(), nombre_paso(sesion, name, "Desgarro", OpDesgarro), **p)
    return _agregar_chapa(sesion, op)


@herramienta("join_by_bend", "chapa", "Unir plegando (CHAPA › Unir plegando): une dos cuerpos de chapa del MISMO "
             "espesor con un pliegue entre dos aristas rectas paralelas (una de cada cuerpo, del borde de la cara de "
             "arriba o de abajo); quedan en un solo cuerpo. Cada arista: selector evaluado sobre body1 / body2 o id de "
             "find_edges.", modifica=True)
def join_by_bend(sesion, edge1: str, edge2: str, body1: str | None = None, body2: str | None = None,
                 bend_radius: Expr | None = None, name: str | None = None):
    """
    edge1: arista del primer cuerpo de chapa (queda con el id del cuerpo resultante).
    edge2: arista del segundo cuerpo de chapa (ese cuerpo se une al primero).
    body1: cuerpo sobre el que se evalúa el selector de edge1.
    body2: cuerpo sobre el que se evalúa el selector de edge2.
    bend_radius: radio de plegado en mm que anula el de la regla.
    name: nombre del paso; vacío = «Unión por pliegue<n>».
    """
    c1, e1 = sl.elegir_uno(sesion, edge1 if sl._PREFIJO.match(edge1) or sl.es_id(edge1) else "edges:" + edge1,
                           "arista", body1)
    c2, e2 = sl.elegir_uno(sesion, edge2 if sl._PREFIJO.match(edge2) or sl.es_id(edge2) else "edges:" + edge2,
                           "arista", body2)
    if c1.id == c2.id:
        raise error("INVALID_ARGUMENTS", "Las dos aristas son del mismo cuerpo: hace falta una de cada cuerpo de chapa.")
    for c in (c1, c2):
        if not es_chapa(c):
            raise error("NOT_SHEET_METAL", f"«{sesion.nombre_cuerpo(c)}» no es un cuerpo de chapa.")
    doc = sesion.doc
    op = OpUnirPlegando(doc.nuevo_id(), nombre_paso(sesion, name, "Unión por pliegue", OpUnirPlegando),
                        aristas=[sl.referencia(c1, e1), sl.referencia(c2, e2)], anular=bend_radius is not None,
                        radio="" if bend_radius is None else texto_expr(bend_radius))
    return _agregar_chapa(sesion, op)


# ---------------------------------------------------------------- regla de un cuerpo y DXF
@herramienta("set_sheet_metal_rule", "chapa", "Cambia la regla de un cuerpo de chapa (CHAPA › Reglas de chapa): otra "
             "regla de la biblioteca y/o valores que la anulan (espesor, radio, K, alivios, separación). Se edita el "
             "paso que creó el cuerpo y se recalcula todo lo que sigue. reset=true vuelve a los valores de la regla. "
             "En una chapa convertida el espesor es el medido: no se cambia.", modifica=True)
def set_sheet_metal_rule(sesion, body: str | None = None, rule: str | None = None, thickness: Expr | None = None,
                         bend_radius: Expr | None = None, k_factor: Expr | None = None,
                         relief_shape: Alivio | None = None, relief_width: Expr | None = None,
                         relief_depth: Expr | None = None, corner_relief: Esquina | None = None,
                         corner_size: Expr | None = None, gap: Expr | None = None, reset: bool = False):
    """
    body: id o nombre del cuerpo de chapa; vacío = el único cuerpo de chapa.
    rule: regla nueva (list_sheet_metal_rules); vacío = la que tiene.
    thickness: espesor en mm que anula el de la regla (número o expresión).
    bend_radius: radio de plegado en mm.
    k_factor: factor K (0 a 1).
    relief_shape: forma del alivio de plegado: "round", "straight" o "tear".
    relief_width: ancho del alivio de plegado en mm.
    relief_depth: profundidad del alivio de plegado en mm.
    corner_relief: alivio de esquina: "trim", "round", "square" o "tear".
    corner_size: tamaño del alivio de esquina en mm.
    gap: separación de desgarros y esquinas en mm.
    reset: true borra los valores anulados antes (vuelve a los de la regla).
    """
    c = cuerpo_chapa(sesion, body)
    op_id = (c.chapa or {}).get("op_regla")
    try:
        op = sesion.doc.operacion(op_id)
    except Exception:  # noqa: BLE001 — el modelo apunta a un paso que ya no está
        raise error("FEATURE_NOT_FOUND", f"No se encontró el paso que tiene la regla de «{sesion.nombre_cuerpo(c)}».") \
            from None
    ajustes = {} if reset else dict(op.p.get("ajustes") or {})
    ajustes.update(_ajustes(thickness, bend_radius, k_factor))
    for clave, valor, que in (("alivio_ancho", relief_width, "relief_width"),
                              ("alivio_profundidad", relief_depth, "relief_depth"),
                              ("esquina_tam", corner_size, "corner_size"), ("separacion", gap, "gap")):
        if valor is not None:
            if que != "relief_depth":                        # la profundidad del alivio puede ser 0
                _numero_positivo(valor, que)
            elif isinstance(valor, (int, float)) and valor < 0:
                raise error("INVALID_ARGUMENTS", f"relief_depth no puede ser negativa (recibió {valor:g}).")
            ajustes[clave] = texto_expr(valor)
    if relief_shape is not None:
        ajustes["alivio_forma"] = ALIVIOS[relief_shape]
    if corner_relief is not None:
        ajustes["esquina_forma"] = ESQUINAS[corner_relief]
    if op.TIPO == "convertir_chapa" and "espesor" in ajustes:
        raise error("INVALID_ARGUMENTS", "El espesor de una chapa convertida es el medido: no se puede cambiar.")
    params = dict(op.p, ajustes=ajustes)
    if rule is not None and str(rule).strip():
        nombre, definicion = regla_para_paso(sesion, rule)
        params.update(regla=nombre, regla_propia=definicion)
    if op.TIPO == "pestana":
        params["anular"] = bool(ajustes)
    antes = info_chapa(sesion, c)
    sesion.doc.reemplazar(op.id, op.__class__(op.id, op.nombre, op.suprimida, **params))
    despues = sesion.doc.estado_final.cuerpos.get(c.id)
    return {"feature": {"id": op.id, "name": op.nombre, "type": op.TIPO}, "before": antes,
            "after": info_chapa(sesion, despues) if despues is not None and _es_de_chapa(despues) else None}


@herramienta("export_flat_pattern_dxf", "chapa", "Exporta el patrón plano de un cuerpo de chapa (o de su patrón plano) a "
             "DXF en mm para corte láser o plegadora (CHAPA › Exportar DXF del patrón plano): capas CONTORNO_EXTERIOR, "
             "CONTORNOS_INTERIORES, LINEAS_PLIEGUE (centros de pliegue) y EXTENSION_PLIEGUE (límites de cada pliegue).")
def export_flat_pattern_dxf(sesion, path: str, body: str | None = None, bend_centerlines: bool = True,
                            bend_extensions: bool = False, overwrite: bool = False):
    """
    path: ruta del .dxf a escribir (si no termina en .dxf se le agrega).
    body: id o nombre del cuerpo de chapa o de su patrón plano; vacío = el único cuerpo de chapa.
    bend_centerlines: true dibuja la línea de centro de cada pliegue.
    bend_extensions: true dibuja las líneas de inicio y fin de cada pliegue.
    overwrite: true para reemplazar el archivo si ya existe.
    """
    c = cuerpo_chapa(sesion, body, patron=True)
    ruta = Path(path)
    if ruta.suffix.lower() != ".dxf":
        ruta = ruta.with_name(ruta.name + ".dxf")
    if ruta.exists() and not overwrite:
        raise error("FILE_EXISTS", f"Ya existe el archivo: {ruta}")
    if not ruta.parent.is_dir():
        raise error("FILE_NOT_FOUND", f"No existe la carpeta: {ruta.parent}")
    exportar_dxf(sesion.doc.estado_final, c.id, ruta, bool(bend_centerlines), bool(bend_extensions))
    info = info_chapa(sesion, c)
    return {"path": str(ruta.resolve()), "format": "dxf", "body": c.id, "size_bytes": ruta.stat().st_size,
            "flat_size": info["flat_size"], "flat_area": info["flat_area"], "bends": info["bends"]}

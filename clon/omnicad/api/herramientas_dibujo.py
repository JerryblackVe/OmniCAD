# -*- coding: utf-8 -*-
"""Herramientas del grupo "dibujo": el espacio DIBUJO para agentes (hoja, cajetín y vistas del plano 2D).

Todo sin Qt: el modelo del plano (`nucleo/dibujo.py` › `Dibujo`) calcula las vistas con el mismo HLR que la
ventana. El dibujo se guarda en `doc.espacios["dibujo"]` con el MISMO formato que la ventana
(`ui/dibujo.py` › `VentanaDibujo.a_dict`), así lo que crea un agente se ve en la app y se guarda en el .omnicad.
Unidades: milímetros y grados. Las posiciones son coordenadas de la HOJA en mm (origen abajo a la izquierda);
`get_drawing` devuelve el tamaño de la hoja y el recuadro de cada vista para elegirlas.

Este módulo trae lo común (`cargar_dibujo`, `guardar_dibujo`, `info_elemento`, `elemento`) que usan también
`herramientas_dibujo_notas` (cotas y anotaciones) y `herramientas_dibujo_salida` (exportar y ver la hoja).
"""
import json
from typing import Literal

import numpy as np

from ..nucleo import dibujo as nd
from ..nucleo import geometria as geo
from .errores import error
from .registro import Expr, herramienta

_ORIENTACIONES = {"front": "frontal", "back": "trasera", "top": "superior", "bottom": "inferior", "right": "derecha",
                  "left": "izquierda", "iso_se": "iso_se", "iso_sw": "iso_so", "iso_ne": "iso_ne", "iso_nw": "iso_no"}
_ESTILOS = {"visible": "visibles", "visible_hidden": "visibles_ocultas"}
_TANGENTES = {"full": "completas", "shortened": "acortadas", "off": "no"}
_METODOS = {"exact": "exacto", "fast": "rapido"}
_TIPOS_VISTA = {"base": "base", "projected": "proyectada", "section": "seccion", "detail": "detalle"}
_CAMPOS_CAJETIN = {"title": "titulo", "part_number": "numero_pieza", "author": "autor", "material": "material",
                   "sheet": "hoja", "date": "fecha", "scale": "escala"}


def _r(x, n=4):
    return None if x is None else round(float(x), n)


def _inv(tabla):
    return {v: k for k, v in tabla.items()}


# ---------------------------------------------------------------- acceso al dibujo del documento
def hay_dibujo(sesion):
    return bool(sesion.doc.espacios.get("dibujo"))


def _nuevo(sesion, size="A3", orientation="horizontal", standard="ISO", title=None):
    d = nd.Dibujo(size, orientation, standard)
    d.cajetin["titulo"] = title if title is not None else sesion.doc.nombre
    return d


def cargar_dibujo(sesion, crear=False):
    """`Dibujo` del documento con sus vistas recalculadas contra el modelo actual. Sin dibujo: DRAWING_NOT_FOUND,
    o uno nuevo vacío (A3 horizontal, ISO) si `crear`. La caché de geometría vive en el documento: llamar varias
    veces seguidas no repite el cálculo de las vistas que no cambiaron."""
    doc = sesion.doc
    datos = doc.espacios.get("dibujo")
    if datos:
        try:
            d = nd.Dibujo.desde_dict(json.loads(json.dumps(datos)))
        except (KeyError, ValueError, TypeError) as e:
            raise error("INVALID_ARGUMENTS", f"El dibujo guardado en el documento está dañado: {e}") from None
    elif crear:
        d = _nuevo(sesion)
    else:
        raise error("DRAWING_NOT_FOUND", "El documento todavía no tiene un dibujo.")
    d._cache = doc.__dict__.setdefault("_cache_dibujo", {})
    cuerpos = {c.id: c for c in doc.estado_final.cuerpos.values() if getattr(c, "tipo", "solido") != "malla"}
    d.actualizar({cid: c.forma for cid, c in cuerpos.items()}, {cid: sesion.nombre_cuerpo(c) for cid, c in cuerpos.items()})
    return d


def guardar_dibujo(sesion, d):
    """Escribe el dibujo en `doc.espacios` (la transacción de la herramienta lo vuelve UN paso de deshacer)."""
    datos = d.a_dict()
    json.dumps(datos)                  # garantiza que sea serializable, como VentanaDibujo.a_dict()
    sesion.doc.espacios["dibujo"] = datos


def elemento(d, ref):
    """Vista o anotación por id («v1», «a2»): DRAWING_ELEMENT_NOT_FOUND si no existe."""
    try:
        return d.elemento(str(ref))
    except geo.ErrorGeometria:
        ids = [v.id for v in d.vistas] + [a["id"] for a in d.anotaciones]
        raise error("DRAWING_ELEMENT_NOT_FOUND", f"El dibujo no tiene la vista ni la anotación «{ref}».",
                    "Hay: " + (", ".join(ids) if ids else "(nada todavía)") + ".") from None


def vista(d, ref):
    """Vista por id («v1»): DRAWING_ELEMENT_NOT_FOUND si no existe."""
    e = elemento(d, ref)
    if not isinstance(e, nd.Vista):
        raise error("DRAWING_ELEMENT_NOT_FOUND", f"«{ref}» es una anotación, no una vista.",
                    "Vistas: " + ", ".join(v.id for v in d.vistas) + ".")
    return e


def punto(p, nombre):
    """[x, y] de la hoja validado (también lo usan las herramientas de cotas y anotaciones)."""
    try:
        q = [float(x) for x in p]
    except (TypeError, ValueError):
        q = []
    if len(q) != 2 or not all(np.isfinite(q)):
        raise error("INVALID_ARGUMENTS", f"{nombre} tiene que ser [x, y] en mm de la hoja.")
    return q


def _escala(valor):
    try:
        return nd.leer_escala(valor)
    except geo.ErrorGeometria as e:
        raise error("INVALID_ARGUMENTS", str(e)) from None


# ---------------------------------------------------------------- lo que se devuelve
def info_vista(d, v):
    x0, y0, x1, y1 = v.caja_hoja(margen=0.0)
    return {"id": v.id, "type": _inv(_TIPOS_VISTA)[v.tipo], "parent": v.padre, "bodies": list(d.raiz(v).cuerpos),
            "orientation": _inv(_ORIENTACIONES).get(v.orientacion) if v.tipo == "base" else None,
            "direction": list(v.direccion) if v.direccion is not None else None,
            "scale": _r(v.escala, 6), "scale_text": nd.texto_escala(v.escala),
            "position": [_r(v.posicion[0]), _r(v.posicion[1])], "rotation": _r(v.rotacion),
            "style": _inv(_ESTILOS)[d.estilo_efectivo(v)], "tangents": _inv(_TANGENTES)[v.tangentes],
            "center_marks": bool(v.marcas_centro), "label": v.etiqueta or None,
            "bbox": [_r(x0), _r(y0), _r(x1), _r(y1)], "error": v.error or None}


def info_anotacion(d, a):
    """La anotación como la guarda el modelo (coordenadas del modelo 2D de su vista) más su texto visible."""
    info = {"id": a["id"], "type": a["tipo"], "view": a.get("vista")}
    if a["tipo"] == "cota":
        info.update(subtype=a["subtipo"], text=d.texto_cota(a), value=_r(d.valor_cota(a)), custom_text=a.get("texto"))
    elif a["tipo"] in ("texto", "nota"):
        info["text"] = a["texto"]
    elif a["tipo"] == "globo":
        info["text"] = a["numero"]
    for k in ("posicion", "flecha", "punto", "centro", "lugar", "puntos", "radio", "altura"):
        if k in a:
            info[{"posicion": "position", "flecha": "arrow", "punto": "point", "centro": "center", "lugar": "place",
                  "puntos": "points", "radio": "radius", "altura": "height"}[k]] = (
                np.round(np.asarray(a[k], float), 4).tolist() if a[k] is not None else None)
    return info


def info_elemento(d, e):
    return info_vista(d, e) if isinstance(e, nd.Vista) else info_anotacion(d, e)


def _info_hoja(d):
    x0, y0, x1, y1 = d.area_util()
    return {"size": d.tamano, "orientation": "horizontal" if d.orientacion == "horizontal" else "vertical",
            "standard": d.norma, "projection": "first_angle" if d.diedro == "primero" else "third_angle",
            "method": _inv(_METODOS)[d.metodo], "width": _r(d.ancho), "height": _r(d.alto),
            "usable_area": [_r(x0), _r(y0), _r(x1), _r(y1)]}


def _info_cajetin(d):
    return {k: d.campos_cajetin().get(v, "") for k, v in _CAMPOS_CAJETIN.items()}


def _resumen(d):
    return {"sheet": _info_hoja(d), "title_block": _info_cajetin(d), "views": [info_vista(d, v) for v in d.vistas],
            "annotations": [info_anotacion(d, a) for a in d.anotaciones]}


def _cuerpos_de_vista(sesion, bodies):
    """Ids de los cuerpos (por id o nombre) para una vista base; sin lista, todos los sólidos del modelo."""
    todos = [c for c in sesion.doc.estado_final.cuerpos.values() if getattr(c, "tipo", "solido") != "malla"]
    if not bodies:
        if not todos:
            raise error("NOTHING_TO_RENDER", "El documento no tiene cuerpos para dibujar (get_scene_info lista los que hay).")
        return [c.id for c in todos]
    ids = []
    for ref in bodies:
        c = sesion.cuerpo(ref)
        if getattr(c, "tipo", "solido") == "malla":
            raise error("INVALID_ARGUMENTS", f"«{ref}» es una malla: las vistas del dibujo son solo de sólidos y superficies.")
        ids.append(c.id)
    return list(dict.fromkeys(ids))


# ---------------------------------------------------------------- MCP-11: crear y consultar el plano
@herramienta("create_drawing", "dibujo", "Crea el dibujo (plano 2D) del documento, como DIBUJO › Nuevo dibujo desde el "
             "diseño: hoja y cajetín vacíos, o ya con la vista base frontal de los cuerpos que pidas. Un dibujo por "
             "documento; con replace=true se reemplaza el que haya.", modifica=True)
def create_drawing(sesion, size: str = "A3", orientation: Literal["horizontal", "vertical"] = "horizontal",
                   standard: Literal["ISO", "ASME"] = "ISO", title: str | None = None, bodies: list[str] | None = None,
                   replace: bool = False):
    """
    size: tamaño de hoja: ISO "A4", "A3", "A2", "A1", "A0" o ASME "ANSI A" a "ANSI E" (nd.TAMANOS_HOJA).
    orientation: "horizontal" o "vertical".
    standard: "ISO" (primer diedro) o "ASME" (tercer diedro).
    title: título del cajetín; vacío = el nombre del documento.
    bodies: ids o nombres de cuerpos; si se pasa, agrega la vista base frontal de esos cuerpos (la escala se elige
        sola para que entre en la hoja). Vacío = hoja sin vistas (add_drawing_view agrega las vistas).
    replace: true reemplaza el dibujo que ya tenga el documento; false lo rechaza (DRAWING_EXISTS).
    """
    if hay_dibujo(sesion) and not replace:
        raise error("DRAWING_EXISTS", "El documento ya tiene un dibujo.", "Pasá replace=true para reemplazarlo.")
    try:
        d = _nuevo(sesion, size, orientation, standard, title)
    except geo.ErrorGeometria as e:
        raise error("INVALID_ARGUMENTS", str(e), "Tamaños: " + ", ".join(nd.TAMANOS_HOJA) + ".") from None
    d.diedro = "primero" if standard == "ISO" else "tercero"
    sesion.doc.espacios.pop("dibujo", None)
    sesion.doc.__dict__.pop("_cache_dibujo", None)
    d._cache = sesion.doc.__dict__.setdefault("_cache_dibujo", {})
    if bodies:
        ids = _cuerpos_de_vista(sesion, bodies)
        cuerpos = {c.id: c for c in sesion.doc.estado_final.cuerpos.values()}
        d.actualizar({cid: cuerpos[cid].forma for cid in ids}, {cid: sesion.nombre_cuerpo(cuerpos[cid]) for cid in ids})
        d.agregar_vista_base(ids)
    guardar_dibujo(sesion, d)
    return _resumen(cargar_dibujo(sesion))


@herramienta("get_drawing", "dibujo", "Devuelve el dibujo del documento: hoja (tamaño, norma, área útil), cajetín, "
             "cada vista (tipo, padre, escala, posición y recuadro en la hoja) y cada anotación (cotas con su valor, "
             "notas, globos, líneas y marcas de centro), más la lista de piezas.")
def get_drawing(sesion):
    d = cargar_dibujo(sesion)
    resultado = _resumen(d)
    resultado["parts_list"] = d.lista_piezas()
    return resultado


# ---------------------------------------------------------------- MCP-12: hoja y cajetín
@herramienta("set_drawing_sheet", "dibujo", "Cambia la hoja del dibujo y los campos del cajetín, como DIBUJO › Hoja y "
             "cajetín: norma (ISO/ASME, que fija el diedro), tamaño, orientación, método de cálculo de las vistas y "
             "los textos del cajetín. Solo cambia lo que pasás.", modifica=True)
def set_drawing_sheet(sesion, standard: Literal["ISO", "ASME"] | None = None, size: str | None = None,
                      orientation: Literal["horizontal", "vertical"] | None = None,
                      method: Literal["exact", "fast"] | None = None, title: str | None = None,
                      part_number: str | None = None, author: str | None = None, material: str | None = None,
                      sheet: str | None = None, date: str | None = None, scale: str | None = None):
    """
    standard: "ISO" (primer diedro) o "ASME" (tercer diedro).
    size: tamaño de hoja: "A4" a "A0" o "ANSI A" a "ANSI E".
    orientation: "horizontal" o "vertical".
    method: cálculo de las vistas: "exact" (HLR exacto, más lento) o "fast" (aproximado).
    title: título del cajetín.
    part_number: número de pieza del cajetín.
    author: quién dibujó (cajetín).
    material: material (cajetín y lista de piezas).
    sheet: hoja, p. ej. "1 / 1".
    date: fecha (texto libre, p. ej. "20/10/2026").
    scale: texto de escala del cajetín; vacío ("") = la de la vista base.
    """
    d = cargar_dibujo(sesion)
    campos = {"title": title, "part_number": part_number, "author": author, "material": material, "sheet": sheet,
              "date": date, "scale": scale}
    if not any(x is not None for x in (standard, size, orientation, method, *campos.values())):
        raise error("INVALID_ARGUMENTS", "No pediste ningún cambio: pasá al menos un parámetro.")
    try:
        if size or orientation:
            nd.tamano_hoja(size or d.tamano, orientation or d.orientacion)
            d.tamano, d.orientacion = size or d.tamano, orientation or d.orientacion
    except geo.ErrorGeometria as e:
        raise error("INVALID_ARGUMENTS", str(e), "Tamaños: " + ", ".join(nd.TAMANOS_HOJA) + ".") from None
    if method:
        d.metodo = _METODOS[method]
    if standard and standard != d.norma:
        d.norma, d.diedro = standard, ("primero" if standard == "ISO" else "tercero")
    d.cajetin.update({_CAMPOS_CAJETIN[k]: str(v) for k, v in campos.items() if v is not None})
    guardar_dibujo(sesion, d)
    d = cargar_dibujo(sesion)
    return {"sheet": _info_hoja(d), "title_block": _info_cajetin(d), "views": [info_vista(d, v) for v in d.vistas]}


# ---------------------------------------------------------------- MCP-13 y MCP-85: vistas
@herramienta("add_drawing_view", "dibujo", "Agrega una vista al dibujo: base (de cuerpos, con orientación), proyectada "
             "(de una vista padre; la posición elige la dirección: a la derecha, arriba, en diagonal = isométrica…), "
             "de sección (corte por una línea sobre la vista padre) o de detalle (un círculo ampliado de la padre). "
             "Las posiciones, líneas y círculos van en mm de la HOJA (get_drawing da el tamaño y el recuadro de "
             "cada vista).", modifica=True)
def add_drawing_view(sesion, type: Literal["base", "projected", "section", "detail"] = "base",
                     bodies: list[str] | None = None,
                     orientation: Literal["front", "back", "top", "bottom", "right", "left", "iso_se", "iso_sw",
                                          "iso_ne", "iso_nw"] = "front",
                     parent: str | None = None, position: list[float] | None = None,
                     section_line: list[list[float]] | None = None, detail_center: list[float] | None = None,
                     detail_radius: float | None = None, scale: Expr | None = None,
                     style: Literal["visible", "visible_hidden"] = "visible_hidden",
                     tangents: Literal["full", "shortened", "off"] | None = None, center_marks: bool | None = None):
    """
    type: "base" (cuerpos + orientación), "projected" (sale de parent), "section" (corte de parent), "detail"
        (círculo ampliado de parent).
    bodies: base: ids o nombres de los cuerpos de la vista; vacío = todos los sólidos. Las demás vistas toman los de su padre.
    orientation: base: "front" (cámara en -Y), "back", "top", "bottom", "right", "left" o isométricas
        "iso_se", "iso_sw", "iso_ne", "iso_nw".
    parent: projected, section y detail: id de la vista padre («v1», de get_drawing).
    position: [x, y] mm de la hoja donde va el CENTRO de la vista. Base: vacío = arriba a la izquierda del área
        útil. Projected: obligatorio, respecto de la padre (a la derecha, abajo, arriba…). Section y detail: obligatorio.
    section_line: section: [[x1, y1], [x2, y2]] mm de la hoja, la línea de corte sobre la vista padre. Se muestra el
        lado donde está position.
    detail_center: detail: [x, y] mm de la hoja, centro del círculo de detalle sobre la vista padre.
    detail_radius: detail: radio del círculo de detalle en mm de la hoja.
    scale: razón de escala (0.5 = 1:2, 2 = 2:1) o texto "1:2", "2:1", "1/2". Base: vacío = la normalizada mayor que
        entra en la hoja. Projected y section heredan la de la padre. Detail: vacío = el doble de la padre.
    style: "visible" (solo aristas visibles) o "visible_hidden" (con las ocultas, en trazos). Solo en la base.
    tangents: "full", "shortened" u "off": cómo se muestran las aristas tangentes. Vacío = "full" en la base y lo de la
        vista padre en las demás.
    center_marks: true/false las marcas de centro de las circunferencias. Vacío = true en la base y lo de la padre
        en las demás.
    """
    d = cargar_dibujo(sesion, crear=True)
    k = _escala(scale) if scale is not None else None
    if type == "base":
        ids = _cuerpos_de_vista(sesion, bodies)
        pos = punto(position, "position") if position is not None else None
        v = d.agregar_vista_base(ids, _ORIENTACIONES[orientation], pos, k, _ESTILOS[style],
                                 _TANGENTES[tangents or "full"], True if center_marks is None else center_marks)
    else:
        if parent is None:
            raise error("INVALID_ARGUMENTS", f"Una vista {type} necesita parent (el id de la vista de la que sale).")
        padre = vista(d, parent).id
        if position is None:
            raise error("INVALID_ARGUMENTS", f"Una vista {type} necesita position: [x, y] mm de la hoja.")
        pos = punto(position, "position")
        if type == "projected":
            v = d.agregar_vista_proyectada(padre, pos)
        elif type == "section":
            if section_line is None or len(section_line) != 2:
                raise error("INVALID_ARGUMENTS", "section necesita section_line: [[x1, y1], [x2, y2]] en mm de la hoja.")
            v = d.agregar_vista_seccion(padre, punto(section_line[0], "section_line[0]"),
                                        punto(section_line[1], "section_line[1]"), pos)
        else:
            if detail_center is None or detail_radius is None:
                raise error("INVALID_ARGUMENTS", "detail necesita detail_center [x, y] y detail_radius (mm de la hoja).")
            v = d.agregar_vista_detalle(padre, punto(detail_center, "detail_center"), float(detail_radius), pos, k)
        cambios = {}
        if k is not None and type != "detail":      # el detalle ya recibió la escala; las otras la heredan
            cambios["escala"] = k
        if tangents is not None:
            cambios["tangentes"] = _TANGENTES[tangents]
        if center_marks is not None:
            cambios["marcas_centro"] = bool(center_marks)
        if cambios:
            d.editar_vista(v.id, **cambios)
    if v.error:
        raise error("OPERATION_FAILED", f"La vista {v.id} no se pudo calcular: {v.error}")
    guardar_dibujo(sesion, d)
    return info_vista(cargar_dibujo(sesion), v)


# ---------------------------------------------------------------- MCP-14: editar una vista
@herramienta("edit_drawing_view", "dibujo", "Cambia las propiedades de una vista del dibujo (escala, estilo de aristas, "
             "tangentes, marcas de centro, nombre/etiqueta) o la gira. Las vistas proyectadas y de sección heredan la "
             "escala nueva; las alineadas con su padre se vuelven a alinear.", modifica=True)
def edit_drawing_view(sesion, view: str, scale: Expr | None = None,
                      style: Literal["visible", "visible_hidden"] | None = None,
                      tangents: Literal["full", "shortened", "off"] | None = None,
                      center_marks: bool | None = None, label: str | None = None, rotate: float | None = None):
    """
    view: id de la vista («v1», de get_drawing).
    scale: nueva escala: razón (0.5 = 1:2) o texto "1:2", "2:1".
    style: "visible" o "visible_hidden" (aristas ocultas en trazos).
    tangents: "full", "shortened" u "off".
    center_marks: true/false las marcas de centro de las circunferencias.
    label: nombre/letra de la vista («A»; las secciones y detalles la usan en su rótulo).
    rotate: grados que se SUMAN al giro actual de la vista, antihorario (el giro queda entre 0 y 360).
    """
    d = cargar_dibujo(sesion)
    v = vista(d, view)
    cambios = {}
    if scale is not None:
        cambios["escala"] = _escala(scale)
    if style is not None:
        cambios["estilo"] = _ESTILOS[style]
    if tangents is not None:
        cambios["tangentes"] = _TANGENTES[tangents]
    if center_marks is not None:
        cambios["marcas_centro"] = bool(center_marks)
    if label is not None:
        cambios["etiqueta"] = str(label)
    if not cambios and rotate is None:
        raise error("INVALID_ARGUMENTS", "No pediste ningún cambio: pasá scale, style, tangents, center_marks, label o rotate.")
    if cambios:
        d.editar_vista(v.id, **cambios)
    if rotate is not None:
        if not np.isfinite(rotate):
            raise error("INVALID_ARGUMENTS", "rotate tiene que ser un número de grados.")
        d.girar(v.id, float(rotate))
    guardar_dibujo(sesion, d)
    return info_vista(cargar_dibujo(sesion), v)

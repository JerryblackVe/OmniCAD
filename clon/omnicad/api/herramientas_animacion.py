# -*- coding: utf-8 -*-
"""Herramientas del grupo "animacion": el espacio ANIMACIÓN para agentes (guiones gráficos, acciones,
explosión automática, cámara, cuadros y publicación de video).

Todo sin Qt: el modelo de guiones y la evaluación de cuadros viven en `nucleo/animacion.py` y la imagen
de cada cuadro sale del renderizador por software `nucleo/render_cpu` (el mismo de `get_viewport_image`).
Los datos se guardan en `doc.espacios["animacion"]` con el MISMO formato que la ventana
(`ui/animacion.py` › `VentanaAnimacion.a_dict`), así lo que crea un agente se ve en la app y se guarda en
el .omnicad. Unidades: mm y grados; los tiempos, en segundos.
"""
import io
import json
import math
import os
from pathlib import Path
from typing import Literal

import numpy as np

from ..nucleo import animacion as anim
from ..nucleo import geometria as geo
from ..nucleo import render_cpu as rc
from ..timeline import ops_chapa
from .errores import error
from .herramientas_inspeccion import (_LADO_MAXIMO, _LADO_MINIMO, _VISTAS, _camara, _esquinas, _es_malla,
                                      _objetos_render)
from .registro import Imagen, herramienta


# ---------------------------------------------------------------- datos del espacio ANIMACIÓN
def _guiones(doc, crear=False):
    """(datos, [Guion], actual) del espacio ANIMACIÓN; sin guiones, la lista viene vacía. `crear` agrega la
    entrada a `doc.espacios` si no estaba (solo las herramientas que escriben)."""
    base = {"version": 1, "actual": 0, "guiones": []}
    datos = doc.espacios.setdefault("animacion", base) if crear else (doc.espacios.get("animacion") or base)
    guiones = [anim.Guion.desde_dict(g) for g in datos.get("guiones") or []]
    actual = min(max(0, int(datos.get("actual", 0))), max(0, len(guiones) - 1))
    return datos, guiones, actual


def _guardar(doc, datos, guiones, actual):
    datos["version"], datos["actual"] = 1, int(actual)
    datos["guiones"] = [g.a_dict() for g in guiones]
    json.dumps(datos)                      # garantiza que sea serializable, como VentanaAnimacion.a_dict()


def _indice(guiones, ref, actual):
    """Índice del guion: None = el actual; int = índice; str = nombre exacto (sin distinguir mayúsculas)."""
    if not guiones:
        raise error("STORYBOARD_NOT_FOUND", "El documento no tiene guiones gráficos: create_storyboard crea el primero.")
    if ref is None:
        return actual
    if isinstance(ref, int) and not isinstance(ref, bool):
        if not 0 <= ref < len(guiones):
            raise error("STORYBOARD_NOT_FOUND", f"No hay guion gráfico número {ref}: hay {len(guiones)} (de 0 a "
                        f"{len(guiones) - 1}).")
        return ref
    if isinstance(ref, str):
        hallados = [i for i, g in enumerate(guiones) if g.nombre.casefold() == ref.strip().casefold()]
        if len(hallados) == 1:
            return hallados[0]
        if len(hallados) > 1:
            raise error("AMBIGUOUS_REFERENCE", f"Hay {len(hallados)} guiones gráficos llamados «{ref}»: usá el índice.")
    raise error("STORYBOARD_NOT_FOUND", f"No existe el guion gráfico «{ref}».",
                "Guiones: " + ", ".join(f"{g.nombre} ({i})" for i, g in enumerate(guiones)) + ".")


def _nombre_nuevo(guiones):
    """«Guion gráficoN» sin repetir, como la ventana."""
    nombres = {g.nombre.casefold() for g in guiones}
    n = len(guiones) + 1
    while f"guion gráfico{n}".casefold() in nombres:
        n += 1
    return f"Guion gráfico{n}"


def _ids(sesion, bodies, todos=None):
    """Ids de cuerpos por id o nombre (get_scene_info); sin lista, todos los del modelo."""
    if bodies is None:
        return [c.id for c in (todos if todos is not None else ops_chapa.cuerpos_del_modelo(sesion.doc.estado_final))]
    return [sesion.cuerpo(ref).id for ref in bodies]


# ---------------------------------------------------------------- cuadros sin ventana
def _camara_ajustada(sesion, vista, aspecto):
    """Cámara que encuadra todo el modelo desde una vista estándar (la misma cuenta que get_viewport_image)."""
    cuerpos = list(sesion.doc.estado_final.cuerpos.values())
    caja = [c.forma.caja() if _es_malla(c) else geo.caja_envolvente(c.forma) for c in cuerpos]
    caja = [b for b in caja if b]
    if not caja:
        raise error("NOTHING_TO_RENDER", "El documento no tiene cuerpos para animar (get_scene_info lista los que hay).")
    escena = rc.escena_normalizada(None)
    cam, _ = _camara(_VISTAS[vista], _esquinas(caja), aspecto, rc.focal_a_fov(escena["focal"]))
    return cam


def _objetos_del_cuadro(sesion, fr):
    """Objetos de `rc.renderizar` con las matrices y opacidades del cuadro `fr` (de `anim.evaluar`)."""
    objetos = []
    for c in ops_chapa.cuerpos_del_modelo(sesion.doc.estado_final):
        for o in _objetos_render(sesion, [c]):
            M = fr["matrices"].get(c.id)
            if M is not None:
                R, t = np.asarray(M, float)[:3, :3], np.asarray(M, float)[:3, 3]
                if not np.allclose(R, np.identity(3), atol=1e-9) or float(np.linalg.norm(t)) > 1e-9:
                    o["v"] = o["v"] @ R.T + t
                    o["n"] = o["n"] @ R.T
            o["opacidad"] = float(o.get("opacidad", 1.0)) * float(fr["opacidad"].get(c.id, 1.0))
            objetos.append(o)
    if not objetos:
        raise error("NOTHING_TO_RENDER", "El documento no tiene cuerpos para dibujar (get_scene_info lista los que hay).")
    return objetos


def _render_cuadro(sesion, fr, cam, ancho, alto):
    """Imagen RGB uint8 del cuadro (con sus anotaciones dibujadas), sin Qt."""
    objetos = _objetos_del_cuadro(sesion, fr)
    escena = rc.escena_normalizada(None)
    z_suelo = min(float(o["v"][:, 2].min()) for o in objetos)
    res = int(min(2048, max(512, 2 ** math.ceil(math.log2(max(ancho, alto) * 1.5)))))
    img = rc.renderizar(objetos, cam, escena, ancho, alto, supermuestreo=1, z_suelo=z_suelo, res_sombras=res,
                        mosaico=2048)
    if fr["notas"]:
        img = anim.dibujar_notas(img, anim.proyectar_notas(fr["notas"], cam, ancho, alto), max(1.0, alto / 480))
    return img


def _validar_lados(width, height):
    for nombre, valor in (("width", width), ("height", height)):
        if not _LADO_MINIMO <= valor <= _LADO_MAXIMO:
            raise error("INVALID_ARGUMENTS", f"{nombre} tiene que estar entre {_LADO_MINIMO} y {_LADO_MAXIMO} píxeles.")


def _estado_json(fr):
    """El cuadro como datos JSON: matrices (16 floats por cuerpo), opacidad, cámara y anotaciones."""
    return {"matrices": {c: np.asarray(M, float).reshape(16).tolist() for c, M in fr["matrices"].items()},
            "opacity": {c: round(float(v), 4) for c, v in fr["opacidad"].items()},
            "camera": fr["camara"],
            "notes": [{"text": n["texto"], "point": np.asarray(n["punto"], float).tolist(),
                       "action": n["id"]} for n in fr["notas"]]}


# ---------------------------------------------------------------- MCP-1 y MCP-2: guiones
@herramienta("create_storyboard", "animacion", "Crea un guion gráfico (storyboard) del espacio ANIMACIÓN: limpio o "
            "que continúa desde el final del actual, como Nuevo guion gráfico.", modifica=True)
def create_storyboard(sesion, name: str | None = None, from_final: bool = False):
    """
    name: nombre del guion nuevo; vacío = «Guion gráficoN» sin repetir (como la ventana).
    from_final: true arranca donde termina el guion actual (posición de los cuerpos y cámara); false = limpio.
    """
    doc = sesion.doc
    datos, guiones, actual = _guiones(doc, crear=True)
    centros = anim.centros_de(doc.estado_final)
    inicial = anim.estado_final(guiones[actual], centros) if from_final and guiones else None
    nombre = (name or "").strip() or _nombre_nuevo(guiones)
    if any(g.nombre.casefold() == nombre.casefold() for g in guiones):
        raise error("NAME_EXISTS", f"Ya hay un guion gráfico llamado «{nombre}».")
    guiones.append(anim.Guion(nombre, None, inicial))
    _guardar(doc, datos, guiones, len(guiones) - 1)
    return {"name": nombre, "index": len(guiones) - 1, "storyboards": len(guiones), "current": nombre}


@herramienta("list_storyboards", "animacion", "Lista los guiones gráficos (storyboards) del documento con su "
            "duración y su cantidad de acciones.")
def list_storyboards(sesion):
    datos, guiones, actual = _guiones(sesion.doc)
    return {"current": guiones[actual].nombre if guiones else None, "current_index": actual if guiones else None,
            "storyboards": [{"index": i, "name": g.nombre, "duration": round(g.duracion, 3),
                             "actions": len(g.acciones)} for i, g in enumerate(guiones)]}


@herramienta("get_storyboard", "animacion", "Devuelve un guion gráfico completo: estado inicial (posición de los "
            "cuerpos y cámara) y la lista de acciones con sus tiempos (para edit_animation_action y "
            "delete_animation_action).")
def get_storyboard(sesion, storyboard: str | int | None = None):
    """
    storyboard: nombre del guion gráfico, índice (desde 0) o vacío = el actual (list_storyboards los lista).
    """
    datos, guiones, actual = _guiones(sesion.doc)
    i = _indice(guiones, storyboard, actual)
    return {"index": i, "current": i == actual, "storyboard": guiones[i].a_dict()}


# ---------------------------------------------------------------- MCP-3: renombrar, copiar, borrar, invertir
@herramienta("rename_storyboard", "animacion", "Cambia el nombre de un guion gráfico.", modifica=True)
def rename_storyboard(sesion, storyboard: str | int | None = None, new_name: str = ""):
    """
    storyboard: nombre del guion gráfico, índice (desde 0) o vacío = el actual.
    new_name: nombre nuevo (no puede repetirse).
    """
    doc = sesion.doc
    datos, guiones, actual = _guiones(doc, crear=True)
    i = _indice(guiones, storyboard, actual)
    nombre = new_name.strip()
    if not nombre:
        raise error("INVALID_ARGUMENTS", "El nombre no puede estar vacío.")
    if any(g.nombre.casefold() == nombre.casefold() for j, g in enumerate(guiones) if j != i):
        raise error("NAME_EXISTS", f"Ya hay un guion gráfico llamado «{nombre}».")
    guiones[i].nombre = nombre
    _guardar(doc, datos, guiones, actual)
    return {"index": i, "name": nombre}


@herramienta("copy_storyboard", "animacion", "Duplica un guion gráfico con todas sus acciones (Copia de la ventana; "
            "el nuevo se llama «… (copia)»).", modifica=True)
def copy_storyboard(sesion, storyboard: str | int | None = None):
    """
    storyboard: nombre del guion gráfico a copiar, índice (desde 0) o vacío = el actual.
    """
    doc = sesion.doc
    datos, guiones, actual = _guiones(doc, crear=True)
    i = _indice(guiones, storyboard, actual)
    copia = anim.Guion.desde_dict(guiones[i].a_dict())
    copia.nombre = f"{guiones[i].nombre} (copia)"
    guiones.insert(i + 1, copia)
    _guardar(doc, datos, guiones, i + 1)
    return {"index": i + 1, "name": copia.nombre, "storyboards": len(guiones)}


@herramienta("delete_storyboard", "animacion", "Elimina un guion gráfico. Si es el único, queda uno limpio con el "
            "mismo nombre (como la ventana).", modifica=True)
def delete_storyboard(sesion, storyboard: str | int | None = None):
    """
    storyboard: nombre del guion gráfico a eliminar, índice (desde 0) o vacío = el actual.
    """
    doc = sesion.doc
    datos, guiones, actual = _guiones(doc, crear=True)
    i = _indice(guiones, storyboard, actual)
    if len(guiones) <= 1:
        guiones[0] = anim.Guion(guiones[0].nombre)
        nuevo_actual = 0
    else:
        del guiones[i]
        nuevo_actual = min(i, len(guiones) - 1)
    _guardar(doc, datos, guiones, nuevo_actual)
    return {"index": nuevo_actual, "storyboards": len(guiones)}


@herramienta("reverse_storyboard", "animacion", "Invierte un guion gráfico (Invertir de la ventana): empieza donde "
            "terminaba y hace las acciones al revés.", modifica=True)
def reverse_storyboard(sesion, storyboard: str | int | None = None):
    """
    storyboard: nombre del guion gráfico a invertir, índice (desde 0) o vacío = el actual.
    """
    doc = sesion.doc
    datos, guiones, actual = _guiones(doc, crear=True)
    i = _indice(guiones, storyboard, actual)
    guiones[i] = anim.invertir(guiones[i], anim.centros_de(doc.estado_final))
    _guardar(doc, datos, guiones, i)
    return {"index": i, "duration": round(guiones[i].duracion, 3), "actions": len(guiones[i].acciones)}


# ---------------------------------------------------------------- MCP-4 y MCP-5: acciones
@herramienta("add_animation_action", "animacion", "Agrega una acción al guion gráfico: transform (mover y girar "
            "componentes), restore (volver a la posición del diseño) o visibility (mostrar/ocultar), como "
            "TRANSFORMAR de ANIMACIÓN.", modifica=True)
def add_animation_action(sesion, storyboard: str | int | None = None,
                         type: Literal["transform", "restore", "visibility"] = "transform",
                         bodies: list[str] | None = None, translation: list[float] | None = None,
                         rotation: list[float] | None = None, visible: bool = False,
                         start: float = 0.0, duration: float = 1.0):
    """
    storyboard: nombre del guion gráfico, índice (desde 0) o vacío = el actual.
    type: "transform" mueve y gira; "restore" vuelve a la posición del diseño; "visibility" muestra u oculta.
    bodies: ids o nombres de los cuerpos (get_scene_info); obligatorio en los tres tipos.
    translation: [x, y, z] en mm (solo transform).
    rotation: [rx, ry, rz] ángulos en grados, primero X después Y después Z (solo transform).
    visible: true muestra, false oculta (solo visibility); con duration > 0 se desvanece.
    start: instante en que empieza la acción, en segundos.
    duration: cuánto dura, en segundos (0 = instantáneo).
    """
    doc = sesion.doc
    datos, guiones, actual = _guiones(doc, crear=True)
    g = guiones[_indice(guiones, storyboard, actual)]
    ids = _ids(sesion, bodies)
    if not ids:
        raise error("INVALID_ARGUMENTS", "Elegí uno o más cuerpos (bodies): get_scene_info los lista por id o nombre.")
    a = {"tipo": {"transform": "transformar", "restore": "restaurar", "visibility": "visibilidad"}[type],
         "cuerpos": ids, "inicio": max(0.0, float(start)), "duracion": max(0.0, float(duration))}
    if type == "transform":
        a["traslacion"] = [float(x) for x in (translation or (0.0, 0.0, 0.0))]
        a["giro"] = [float(x) for x in anim.euler_a_giro(*(float(x) for x in (rotation or (0.0, 0.0, 0.0))))]
    elif type == "visibility":
        a["visible"] = bool(visible)
    a = g.agregar(a)
    _guardar(doc, datos, guiones, actual)
    return {"id": a["id"], "type": type, "bodies": ids, "start": a["inicio"], "duration": a["duracion"],
            "duration_total": round(g.duracion, 3)}


@herramienta("edit_animation_action", "animacion", "Edita una acción del guion gráfico: moverla o estirar su barra "
            "(start, duration) y sus valores (movimiento, visibilidad, texto, cámara). Solo cambian los parámetros "
            "pasados.", modifica=True)
def edit_animation_action(sesion, storyboard: str | int | None = None, action: str = "",
                          start: float | None = None, duration: float | None = None,
                          translation: list[float] | None = None, rotation: list[float] | None = None,
                          visible: bool | None = None, text: str | None = None, camera: dict | None = None):
    """
    storyboard: nombre del guion gráfico, índice (desde 0) o vacío = el actual.
    action: id de la acción (a1, a2, …; lo lista get_storyboard).
    start: nuevo instante de inicio, en segundos.
    duration: nueva duración, en segundos (0 = instantáneo).
    translation: [x, y, z] en mm (solo acciones transform).
    rotation: [rx, ry, rz] ángulos en grados (solo acciones transform).
    visible: true muestra, false oculta (solo acciones visibility).
    text: texto nuevo (solo anotaciones).
    camera: cámara nueva, {"R", "objetivo", "distancia", "fov"} (solo acciones vista).
    """
    doc = sesion.doc
    datos, guiones, actual = _guiones(doc, crear=True)
    g = guiones[_indice(guiones, storyboard, actual)]
    try:
        a = g.accion(action)
    except geo.ErrorGeometria:
        raise error("ACTION_NOT_FOUND", f"No existe la acción «{action}» en el guion «{g.nombre}».",
                    "get_storyboard lista las acciones con su id.") from None
    if start is not None:
        a["inicio"] = max(0.0, float(start))
    if duration is not None:
        a["duracion"] = max(0.0, float(duration))
    if translation is not None:
        a["traslacion"] = [float(x) for x in translation]
    if rotation is not None:
        a["giro"] = [float(x) for x in anim.euler_a_giro(*(float(x) for x in rotation))]
    if visible is not None:
        a["visible"] = bool(visible)
    if text is not None:
        a["texto"] = str(text)
    if camera is not None:
        a["camara"] = camera
    _guardar(doc, datos, guiones, actual)
    return {"id": a["id"], "type": a["tipo"], "start": a["inicio"], "duration": a.get("duracion", 0.0),
            "duration_total": round(g.duracion, 3)}


@herramienta("delete_animation_action", "animacion", "Elimina una acción del guion gráfico.", modifica=True)
def delete_animation_action(sesion, storyboard: str | int | None = None, action: str = ""):
    """
    storyboard: nombre del guion gráfico, índice (desde 0) o vacío = el actual.
    action: id de la acción a eliminar (a1, a2, …; lo lista get_storyboard).
    """
    doc = sesion.doc
    datos, guiones, actual = _guiones(doc, crear=True)
    g = guiones[_indice(guiones, storyboard, actual)]
    try:
        g.accion(action)
    except geo.ErrorGeometria:
        raise error("ACTION_NOT_FOUND", f"No existe la acción «{action}» en el guion «{g.nombre}».",
                    "get_storyboard lista las acciones con su id.") from None
    g.quitar(action)
    _guardar(doc, datos, guiones, actual)
    return {"deleted": action, "actions": len(g.acciones), "duration_total": round(g.duracion, 3)}


# ---------------------------------------------------------------- MCP-6: explosión automática
@herramienta("auto_explode", "animacion", "Explosión automática (EXPLOSIÓN AUTOMÁTICA de ANIMACIÓN): agrega una "
            "acción que separa las piezas hacia afuera del centro, de un nivel o de todos los niveles.", modifica=True)
def auto_explode(sesion, storyboard: str | int | None = None, bodies: list[str] | None = None,
                 level: Literal["one", "all"] = "one", distance: float | None = None,
                 sequential: bool = False, start: float = 0.0, duration: float = 1.0):
    """
    storyboard: nombre del guion gráfico, índice (desde 0) o vacío = el actual.
    bodies: ids o nombres de los cuerpos a separar; vacío = todo el modelo.
    level: "one" = un nivel (los cuerpos de un mismo componente van juntos); "all" = todos los niveles (cada cuerpo
        por su lado).
    distance: escala de la explosión en mm: cuánto se aparta la pieza más lejana; vacío = 60 % del tamaño del modelo
        (como la ventana).
    sequential: true = las piezas explotan una después de la otra; false = todas a la vez.
    start: instante en que empieza la acción, en segundos.
    duration: cuánto dura, en segundos.
    """
    doc = sesion.doc
    datos, guiones, actual = _guiones(doc, crear=True)
    g = guiones[_indice(guiones, storyboard, actual)]
    estado = doc.estado_final
    ids = _ids(sesion, bodies)
    grupos = anim.grupos_explosion(estado, ids, {"one": "uno", "all": "todos"}[level])
    if not grupos:
        raise error("NOTHING_TO_RENDER", "El documento no tiene cuerpos para explotar (get_scene_info los lista).")
    if distance is None:
        caja = [c.forma.caja() if _es_malla(c) else geo.caja_envolvente(c.forma)
                for c in estado.cuerpos.values() if c.id in {x for grp in grupos for x in grp}]
        caja = [b for b in caja if b]
        distance = round(float(np.linalg.norm(np.ptp(_esquinas(caja), axis=0))) * 0.6, 1)
    distancia = float(distance)
    if distancia <= 0:
        raise error("INVALID_ARGUMENTS", "distance tiene que ser mayor que cero (en mm).")
    desplazamientos, orden = anim.calcular_explosion(anim.centros_de(estado), grupos, distancia)
    a = g.agregar({"tipo": "explosion", "cuerpos": [c for grp in grupos for c in grp],
                   "nivel": {"one": "uno", "all": "todos"}[level], "distancia": distancia,
                   "secuencial": bool(sequential), "desplazamientos": desplazamientos, "orden": orden,
                   "inicio": max(0.0, float(start)), "duracion": max(0.0, float(duration))})
    _guardar(doc, datos, guiones, actual)
    return {"id": a["id"], "bodies": a["cuerpos"], "distance": distancia, "level": level,
            "start": a["inicio"], "duration": a["duracion"], "duration_total": round(g.duracion, 3)}


# ---------------------------------------------------------------- MCP-7 y MCP-8: cámara y anotación
@herramienta("set_animation_camera", "animacion", "Agrega una acción Vista al guion: la cámara va (con la misma "
            "vista orbital de la ventana) desde la cámara inicial hasta la nueva.", modifica=True)
def set_animation_camera(sesion, storyboard: str | int | None = None, camera: dict | None = None,
                         view: Literal["iso", "front", "back", "right", "left", "top", "bottom"] = "iso",
                         start: float = 0.0, duration: float = 1.0):
    """
    storyboard: nombre del guion gráfico, índice (desde 0) o vacío = el actual.
    camera: cámara completa {"R": 3x3, "objetivo": [x, y, z], "distancia", "fov", "ortografica"} (la guarda el guion);
        si no se pasa, se arma una que encuadra todo el modelo.
    view: vista estándar para la cámara cuando no se pasa camera: iso, front, back, right, left, top o bottom.
    start: instante en que empieza la acción, en segundos.
    duration: cuánto dura el viaje de cámara, en segundos.
    """
    doc = sesion.doc
    datos, guiones, actual = _guiones(doc, crear=True)
    g = guiones[_indice(guiones, storyboard, actual)]
    cam = camera or _camara_ajustada(sesion, view, 16 / 9)
    if camera is not None and not all(k in camera for k in ("R", "objetivo", "distancia")):
        raise error("INVALID_ARGUMENTS", "camera necesita «R» (3x3), «objetivo» [x, y, z] y «distancia».",
                    "Sin camera se arma una cámara que encuadra todo el modelo desde view.")
    if g.inicial.get("camara") is None:
        g.inicial["camara"] = cam                       # cámara de referencia, como la ventana
    a = g.agregar({"tipo": "vista", "camara": cam, "inicio": max(0.0, float(start)),
                   "duracion": max(0.0, float(duration))})
    _guardar(doc, datos, guiones, actual)
    return {"id": a["id"], "start": a["inicio"], "duration": a["duracion"],
            "duration_total": round(g.duracion, 3)}


@herramienta("add_animation_annotation", "animacion", "Agrega una anotación (globo con texto) al guion gráfico: "
            "fija en un punto del mundo o pegada a un cuerpo, a la que sigue si se mueve.", modifica=True)
def add_animation_annotation(sesion, storyboard: str | int | None = None, text: str = "",
                             point: list[float] | None = None, body: str | None = None,
                             start: float = 0.0, duration: float = 2.0):
    """
    storyboard: nombre del guion gráfico, índice (desde 0) o vacío = el actual.
    text: texto de la anotación.
    point: [x, y, z] en mm donde va el alfiler de la anotación.
    body: id o nombre del cuerpo al que se pega (la anotación lo sigue); con body, point va en coordenadas del
        cuerpo; vacío = fija en el mundo.
    start: instante en que aparece, en segundos.
    duration: cuánto dura visible, en segundos (0 = hasta el final del guion).
    """
    doc = sesion.doc
    datos, guiones, actual = _guiones(doc, crear=True)
    g = guiones[_indice(guiones, storyboard, actual)]
    if not text.strip():
        raise error("INVALID_ARGUMENTS", "Escribí el texto de la anotación (text).")
    cuerpo = sesion.cuerpo(body).id if body else ""
    a = g.agregar({"tipo": "anotacion", "texto": text.strip(),
                   "punto": [float(x) for x in (point or (0.0, 0.0, 0.0))], "cuerpo": cuerpo,
                   "inicio": max(0.0, float(start)), "duracion": max(0.0, float(duration))})
    _guardar(doc, datos, guiones, actual)
    return {"id": a["id"], "text": a["texto"], "body": cuerpo, "start": a["inicio"],
            "duration": a["duracion"]}


# ---------------------------------------------------------------- MCP-9: cuadro
@herramienta("get_animation_frame", "animacion", "Devuelve el estado de la escena en un instante del guion gráfico "
            "(matrices y visibilidad de cada cuerpo, cámara, anotaciones) y una imagen renderizada del cuadro, "
            "sin abrir la ventana (como Ir a de ANIMACIÓN).")
def get_animation_frame(sesion, storyboard: str | int | None = None, time: float = 0.0,
                        width: int = 640, height: int = 480):
    """
    storyboard: nombre del guion gráfico, índice (desde 0) o vacío = el actual.
    time: instante en segundos (0 = comienzo; get_storyboard dice la duración total).
    width: ancho de la imagen en píxeles (16 a 2048).
    height: alto de la imagen en píxeles (16 a 2048).
    """
    _validar_lados(width, height)
    doc = sesion.doc
    datos, guiones, actual = _guiones(doc)
    g = guiones[_indice(guiones, storyboard, actual)]
    t = max(0.0, float(time))
    fr = anim.evaluar(g, t, anim.centros_de(doc.estado_final))
    cam = fr["camara"] or _camara_ajustada(sesion, "iso", width / height)
    img = _render_cuadro(sesion, fr, cam, width, height)
    from PIL import Image
    buf = io.BytesIO()
    Image.fromarray(np.ascontiguousarray(img[..., :3]), "RGB").save(buf, "PNG", compress_level=3)
    return {"storyboard": g.nombre, "time": t, "duration": round(g.duracion, 3), "state": _estado_json(fr),
            "image": Imagen(buf.getvalue(), width, height)}


# ---------------------------------------------------------------- MCP-10: publicar video
@herramienta("export_animation_video", "animacion", "Publica la animación como GIF animado o secuencia de imágenes "
            "PNG, renderizando cada cuadro con el renderizador por software (como PUBLICAR de ANIMACIÓN, sin abrir "
            "la ventana).")
def export_animation_video(sesion, path: str, storyboard: str | int | None = None,
                           all_storyboards: bool = False, format: Literal["gif", "png"] = "gif",
                           width: int = 640, height: int = 360, fps: int = 15):
    """
    path: archivo .gif a escribir, o carpeta para la secuencia de PNG (se crea si no existe).
    storyboard: nombre del guion gráfico a publicar, índice (desde 0) o vacío = el actual.
    all_storyboards: true publica todos los guiones del documento, uno tras otro.
    format: "gif" = GIF animado que se repite; "png" = secuencia de imágenes PNG (cuadro_0001.png, …).
    width: ancho del video en píxeles (16 a 2048).
    height: alto del video en píxeles (16 a 2048).
    fps: cuadros por segundo (1 a 60).
    """
    if not str(path).strip():
        raise error("MISSING_PATH", "Pasá dónde guardar el video (path).")
    if not 1 <= int(fps) <= 60:
        raise error("INVALID_ARGUMENTS", "fps tiene que estar entre 1 y 60.")
    _validar_lados(width, height)
    doc = sesion.doc
    datos, guiones, actual = _guiones(doc)
    if all_storyboards:
        elegidos = list(enumerate(guiones))
    else:
        i = _indice(guiones, storyboard, actual)
        elegidos = [(i, guiones[i])]
    tramos = [(g, t) for _i, g in elegidos for t in anim.tiempos(g.duracion, int(fps))]
    if not tramos:
        raise error("NOTHING_TO_RENDER", "Los guiones elegidos no tienen acciones: agregá alguna antes de publicar.")
    centros = anim.centros_de(doc.estado_final)
    ruta = Path(path)
    if format == "png":
        os.makedirs(ruta, exist_ok=True)
    elif ruta.parent and not ruta.parent.is_dir():
        raise error("FILE_NOT_FOUND", f"No existe la carpeta: {ruta.parent}",
                    "Creala primero, o usá una ruta de una carpeta que exista.")
    cam_defecto = _camara_ajustada(sesion, "iso", width / height)
    archivos, cuadros = [], []
    for i, (g, t) in enumerate(tramos):
        fr = anim.evaluar(g, t, centros)
        img = _render_cuadro(sesion, fr, fr["camara"] or cam_defecto, width, height)
        if format == "png":
            nombre = ruta / f"cuadro_{i + 1:04d}.png"
            rc.guardar_png(img, nombre)
            archivos.append(str(nombre))
        else:
            cuadros.append(anim.cuadro_gif(img))
    if format != "png":
        anim.guardar_gif(cuadros, ruta, int(fps))
        archivos = [str(ruta)]
    return {"files": archivos, "frames": len(tramos), "path": archivos[0] if len(archivos) == 1 else str(ruta),
            "format": format, "fps": int(fps)}

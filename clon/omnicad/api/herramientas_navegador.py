"""Grupos y conjuntos del navegador: metadatos del documento, sin Qt ni geometría nueva."""
import copy
from typing import Literal

from .errores import error
from .registro import herramienta


def datos_navegador(doc):
    """Lee solo las filas válidas; un proyecto viejo no tiene estos metadatos."""
    datos = doc.propiedad("__navegador__", "organizacion", {})
    salida = {}
    for clase in ("grupos", "conjuntos"):
        filas = datos.get(clase, {}) if isinstance(datos, dict) else {}
        salida[clase] = {k: {"nombre": v["nombre"], "miembros": list(v["miembros"])}
                         for k, v in filas.items() if isinstance(k, str) and isinstance(v, dict)
                         and isinstance(v.get("nombre"), str) and isinstance(v.get("miembros"), list)
                         and all(isinstance(m, str) for m in v["miembros"])} if isinstance(filas, dict) else {}
    return salida


def _elementos(sesion, items):
    estado = sesion.doc.estado_final
    ids = []
    for ident in items:
        if ident in estado.bocetos or ident in estado.lienzos or ident in estado.componentes:
            ids.append(ident)
        else:
            ids.append(sesion.cuerpo(ident).id)
    return list(dict.fromkeys(ids))


@herramienta("get_browser_state", "documento", "Lista los grupos y conjuntos de selección guardados en el navegador "
             "y los bocetos con su estado, como los marca el navegador: status (fully_constrained = candado, "
             "over_constrained = marca roja de conflicto, under_constrained) y dof (grados de libertad). Qué choca: "
             "get_sketch › conflicts.")
def get_browser_state(sesion):
    from .herramientas_boceto import estado_solver
    datos = datos_navegador(sesion.doc)
    bocetos = []
    for b in sesion.doc.estado_final.bocetos.values():
        status, dof = estado_solver(b)
        bocetos.append({"id": b.op_id, "name": b.nombre, "status": status, "dof": dof})
    return {"groups": [{"id": k, "name": v["nombre"], "items": v["miembros"]}
                       for k, v in datos["grupos"].items()],
            "selection_sets": [{"id": k, "name": v["nombre"], "items": v["miembros"]}
                               for k, v in datos["conjuntos"].items()],
            "sketches": bocetos}


@herramienta("manage_browser", "documento", "Organiza cuerpos, bocetos y calcomanías: crea grupos y conjuntos de selección, "
             "mueve elementos entre grupos, renombra o suprime un grupo (sin borrar su contenido). "
             "Se guarda en el proyecto y admite deshacer.", modifica=True)
def manage_browser(sesion, action: Literal["create_group", "create_set", "move", "rename_group", "delete_group"],
                   items: list[str] | None = None, name: str = "", group: str | None = None):
    """
    action: create_group, create_set, move, rename_group o delete_group.
    items: ids de cuerpos, bocetos o calcomanías; los cuerpos también aceptan nombres.
    name: nombre del grupo o conjunto que se crea, o nombre nuevo con rename_group.
    group: id del grupo destino; vacío con move devuelve los elementos a su carpeta original.
    """
    datos = datos_navegador(sesion.doc)
    grupos = datos["grupos"]
    ids = _elementos(sesion, items or [])
    if action in ("rename_group", "delete_group") or (action == "move" and group is not None):
        if group not in grupos:
            raise error("INVALID_ARGUMENTS", "El grupo elegido ya no existe.")
    if action in ("create_group", "create_set", "rename_group") and not name.strip():
        raise error("INVALID_ARGUMENTS", "Escribí un nombre para el grupo o conjunto.")
    ident = group
    if action in ("create_group", "create_set"):
        tabla = grupos if action == "create_group" else datos["conjuntos"]
        prefijo = "grupo:" if action == "create_group" else "conjunto:"
        n = 1
        while prefijo + str(n) in tabla:
            n += 1
        ident = prefijo + str(n)
        if action == "create_set" and not ids:
            raise error("INVALID_ARGUMENTS", "Elegí los cuerpos o bocetos del conjunto.")
        tabla[ident] = {"nombre": name.strip(), "miembros": ids if action == "create_set" else []}
    if action in ("create_group", "move"):
        for fila in grupos.values():
            fila["miembros"] = [i for i in fila["miembros"] if i not in ids]
        if ident is not None:
            grupos[ident]["miembros"].extend(ids)
    elif action == "rename_group":
        grupos[group]["nombre"] = name.strip()
    elif action == "delete_group":
        del grupos[group]
    sesion.doc.set_propiedad(["__navegador__"], "organizacion", copy.deepcopy(datos))
    return {"id": ident, **get_browser_state(sesion)}


@herramienta("set_browser_visibility", "documento", "Muestra u oculta cuerpos, componentes, bocetos, calcomanías o grupos en vivo, "
             "y los análisis (por su nombre: se guarda en el documento, sin ventana). Sin items, muestra todo. No "
             "modifica geometría.")
def set_browser_visibility(sesion, items: list[str] | None = None, visible: bool = True):
    """
    items: ids de cuerpos, componentes, bocetos, calcomanías o grupos, o nombres de análisis (get_scene_info / manage_analysis los lista); vacío muestra todo.
    visible: true muestra; false oculta los elementos pedidos.
    """
    doc = sesion.doc
    analisis = [i for i in items or [] if i in doc.analisis]
    resto = [i for i in items or [] if i not in analisis]
    ids = []
    if not items or resto:
        mostrar = getattr(sesion, "mostrar_elementos", None)
        if mostrar is None:
            raise error("APP_NOT_RUNNING", "La visibilidad del navegador necesita la ventana en vivo.")
        grupos = datos_navegador(sesion.doc)["grupos"]
        for ident in resto:
            ids.extend(grupos[ident]["miembros"] if ident in grupos else [ident])
        ids = _elementos(sesion, ids)                  # todo se comprueba antes de tocar el documento
    for nombre in analisis:
        doc.analisis[nombre]["visible"] = visible
    if analisis:
        doc.modificado = True
        doc._notificar()
    if ids or not items:
        mostrar(ids, visible)
    return {"items": analisis + ids, "visible": visible}


TIPOS_OBJETO = ("planos_origen", "ejes_origen", "punto_origen", "planos_usuario", "ejes_usuario", "puntos_usuario",
                "bocetos", "scu", "origenes_union", "ejes_union", "uniones")
_VISIBLES_DE_ORIGEN = {"planos_origen": True, "ejes_origen": True, "punto_origen": True, "planos_usuario": True,
                       "ejes_usuario": False, "puntos_usuario": False, "bocetos": True, "scu": False,
                       "origenes_union": False, "ejes_union": False, "uniones": False}


@herramienta("set_object_visibility", "documento", "Muestra u oculta tipos de objetos de trabajo en la vista, como Visibilidad "
             "del objeto del menú de visualización: planos, ejes y punto de origen, planos, ejes y puntos de usuario, "
             "bocetos, sistemas de coordenadas, orígenes y ejes de unión y uniones. El estado se guarda con el documento "
             "(doc.espacios['visor']) y la ventana en vivo lo aplica. Admite deshacer.", modifica=True)
def set_object_visibility(sesion, types: list[Literal["planos_origen", "ejes_origen", "punto_origen", "planos_usuario",
                                                     "ejes_usuario", "puntos_usuario", "bocetos", "scu",
                                                     "origenes_union", "ejes_union", "uniones", "all"]] | None = None,
                          visible: bool = True):
    """
    types: tipos de objeto: planos_origen, ejes_origen, punto_origen, planos_usuario, ejes_usuario, puntos_usuario, bocetos, scu, origenes_union, ejes_union, uniones, o "all" (todos); vacío = solo consulta el estado.
    visible: true muestra esos tipos; false los oculta.
    """
    datos = copy.deepcopy(sesion.doc.espacios.get("visor") or {})
    estado = {**_VISIBLES_DE_ORIGEN, **datos.get("visibilidad", {})}
    pedidos = TIPOS_OBJETO if "all" in (types or []) else list(types or [])
    for t in pedidos:
        estado[t] = bool(visible)
    if pedidos:
        datos["visibilidad"] = estado
        sesion.doc.espacios["visor"] = datos
    return {"visibility": estado}


@herramienta("find_in_window", "documento", "Selecciona cuerpos, los encuadra en la ventana y resalta su paso "
             "creador en el timeline, como Buscar en la ventana del navegador. Necesita la app en vivo.")
def find_in_window(sesion, bodies: list[str] | None = None):
    """
    bodies: ids o nombres de cuerpos; omitido o vacío busca todos los cuerpos del componente raíz.
    """
    buscar = getattr(sesion, "buscar_en_ventana", None)
    if buscar is None:
        raise error("APP_NOT_RUNNING", "Buscar en la ventana necesita la ventana de OmniCAD en vivo.")
    ids = list(dict.fromkeys(sesion.cuerpo(b).id for b in bodies)) if bodies else list(sesion.doc.estado_final.cuerpos)
    return buscar(ids)


@herramienta("set_body_opacity", "documento", "Cambia el Control de opacidad de cuerpos del navegador. "
             "Sin cuerpos, se aplica a todos los del componente raíz. Admite deshacer.", modifica=True)
def set_body_opacity(sesion, opacity: float, bodies: list[str] | None = None):
    """
    opacity: porcentaje de opacidad entre 0 y 100; 100 quita la anulación de opacidad.
    bodies: ids o nombres de cuerpos; omitido o vacío cambia todos los cuerpos del componente raíz.
    """
    if not 0 <= opacity <= 100:
        raise error("INVALID_ARGUMENTS", "La opacidad debe estar entre 0 y 100.")
    ids = list(dict.fromkeys(sesion.cuerpo(b).id for b in bodies)) if bodies else list(sesion.doc.estado_final.cuerpos)
    if not ids:
        raise error("INVALID_ARGUMENTS", "No hay cuerpos para cambiar la opacidad.")
    sesion.doc.set_propiedad(ids, "opacidad", None if opacity == 100 else opacity / 100)
    return {"bodies": ids, "opacity": opacity}


@herramienta("isolate_bodies", "documento", "Muestra solo los cuerpos elegidos; restore vuelve a mostrar todos. "
             "Guarda la visibilidad del navegador y admite deshacer.", modifica=True)
def isolate_bodies(sesion, bodies: list[str] | None = None, restore: bool = False):
    """
    bodies: nombres o ids de los cuerpos que deben quedar visibles.
    restore: true vuelve a mostrar todos los cuerpos.
    """
    todos = sesion.doc.estado_final.cuerpos
    ids = set(sesion.cuerpo(b).id for b in bodies or [])
    if not restore and not ids:
        raise error("INVALID_ARGUMENTS", "Elegí al menos un cuerpo para aislar.")
    ocultos = set(sesion.doc.propiedad("__navegador__", "ocultos", [])) - set(todos)
    if not restore:
        ocultos.update(set(todos) - ids)
    # Un componente oculto no debe impedir ver sus cuerpos elegidos.
    ocultos.difference_update(c.componente for c in todos.values() if restore or c.id in ids)
    sesion.doc.set_propiedad(["__navegador__"], "ocultos", sorted(ocultos))
    return {"bodies": [cid for cid in todos if cid not in ocultos], "count": len(todos) - len(set(todos) & ocultos)}


@herramienta("sketch_view", "documento", "Opera el boceto en la ventana: editar, seleccionar su plano, mirar "
             "de frente, encuadrar, encontrar en el timeline, terminar el boceto (finish: sale del editor y guarda) o "
             "mostrar/ocultar las opciones de la paleta del boceto (perfil, cotas, proyectadas, construcción, rejilla, "
             "forzar a la rejilla, corte, puntos y restricciones). Las opciones y finish solo están disponibles "
             "mientras se edita ese boceto.")
def sketch_view(sesion, sketch: str,
                action: Literal["edit", "select_plane", "look_at", "find_in_window", "find_in_timeline", "finish",
                                "profile", "dimensions", "projected", "construction", "grid", "snap", "cut", "points",
                                "constraints"],
                visible: bool | None = None):
    """
    sketch: id o nombre del boceto.
    action: edit, select_plane, look_at, find_in_window, find_in_timeline, finish (terminar el boceto), o una opción de la paleta: profile, dimensions, projected, construction, grid (rejilla del boceto), snap (forzar), cut (corte), points o constraints.
    visible: estado de la opción de la paleta; omitido la alterna (solo las acciones de opción).
    """
    op = sesion.paso(sketch)
    if op.id not in sesion.doc.estado_final.bocetos:
        raise error("SKETCH_NOT_FOUND", "El paso elegido no es un boceto disponible.")
    operar = getattr(sesion, "vista_boceto", None)
    if operar is None:
        raise error("APP_NOT_RUNNING", "sketch_view necesita la ventana de OmniCAD en vivo.")
    return operar(op.id, action, visible)

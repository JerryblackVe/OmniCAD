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
        if ident in estado.bocetos:
            ids.append(ident)
        else:
            ids.append(sesion.cuerpo(ident).id)
    return list(dict.fromkeys(ids))


@herramienta("get_browser_state", "documento", "Lista los grupos y conjuntos de selección guardados en el navegador.")
def get_browser_state(sesion):
    datos = datos_navegador(sesion.doc)
    return {"groups": [{"id": k, "name": v["nombre"], "items": v["miembros"]}
                       for k, v in datos["grupos"].items()],
            "selection_sets": [{"id": k, "name": v["nombre"], "items": v["miembros"]}
                               for k, v in datos["conjuntos"].items()]}


@herramienta("manage_browser", "documento", "Organiza cuerpos y bocetos: crea grupos y conjuntos de selección, "
             "mueve elementos entre grupos, renombra o suprime un grupo (sin borrar su contenido). "
             "Se guarda en el proyecto y admite deshacer.", modifica=True)
def manage_browser(sesion, action: Literal["create_group", "create_set", "move", "rename_group", "delete_group"],
                   items: list[str] | None = None, name: str = "", group: str | None = None):
    """
    action: create_group, create_set, move, rename_group o delete_group.
    items: ids de cuerpos o bocetos; los cuerpos también aceptan nombres.
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


@herramienta("set_browser_visibility", "documento", "Muestra u oculta cuerpos, bocetos o grupos en vivo. "
             "Sin items, muestra todo. No modifica geometría.")
def set_browser_visibility(sesion, items: list[str] | None = None, visible: bool = True):
    """
    items: ids de cuerpos, bocetos o grupos; vacío muestra todo.
    visible: true muestra; false oculta los elementos pedidos.
    """
    mostrar = getattr(sesion, "mostrar_elementos", None)
    if mostrar is None:
        raise error("APP_NOT_RUNNING", "La visibilidad del navegador necesita la ventana en vivo.")
    grupos = datos_navegador(sesion.doc)["grupos"]
    ids = []
    for ident in items or []:
        ids.extend(grupos[ident]["miembros"] if ident in grupos else [ident])
    ids = _elementos(sesion, ids)
    mostrar(ids, visible)
    return {"items": ids, "visible": visible}

# -*- coding: utf-8 -*-
"""
SELECCIONAR › Herramientas de selección, sin Qt: conjuntos de selección guardados, seleccionar por límite y por semilla y
límite. Calculan y devuelven lo elegido; si hay ventana, además lo marcan.
"""
from typing import Literal

from ..nucleo import geometria as geo
from ..nucleo import seleccion_por_limite as spl
from ..nucleo import solidos_modificar as sm
from ..timeline import entidades as ent
from . import selectores as sl
from .errores import error
from .registro import herramienta

_CLAVE = "conjuntos_seleccion"


def _conjuntos(sesion, escribir=True):
    """Los conjuntos del documento; `escribir=False` no crea la clave (leer no debe ensuciar el documento)."""
    espacios = sesion.doc.espacios
    return espacios.setdefault(_CLAVE, {}) if escribir else espacios.get(_CLAVE, {})


def _ids(sesion, cuerpo, tipo, formas):
    """Ids efímeros (find_faces / find_edges) de las formas dadas dentro de `cuerpo`."""
    return [sl.emitir_id(sesion, cuerpo, e) for e in sl.listar(cuerpo.forma, tipo) if any(e.sub.IsSame(f) for f in formas)]


def _resolver_ref(sesion, ref):
    """(cuerpo, forma) de una referencia guardada, o None si la geometría ya no existe."""
    try:
        e = ent.resolver(ref, sesion.doc.estado_final)
    except ent.ErrorReferencia:
        return None
    return sesion.doc.estado_final.cuerpos[e.cuerpo], e.forma


@herramienta("manage_selection_sets", "documento", "Conjuntos de selección guardados en el diseño (Seleccionar › Crear "
             "conjunto de selección): guarda cuerpos, caras o aristas bajo un nombre, los vuelve a elegir, les suma "
             "objetos (update) o los borra. Se guardan con el proyecto y cada cambio es un paso de deshacer. Una cara o arista cuya geometría cambió demasiado se cuenta en missing.", modifica=True)
def manage_selection_sets(sesion, action: Literal["list", "create", "update", "select", "rename", "delete"],
                          name: str = "", faces: list[str] | str | None = None, edges: list[str] | str | None = None,
                          bodies: list[str] | None = None, body: str | None = None, new_name: str = ""):
    """
    action: list, create (nuevo), update (suma objetos al conjunto), select (devuelve lo guardado y marca en la ventana solo los cuerpos), rename o delete.
    name: nombre del conjunto (en list se ignora).
    faces: caras a guardar: selector, ids de find_faces o lista de ambos.
    edges: aristas a guardar: selector, ids de find_edges o lista de ambos.
    bodies: cuerpos a guardar (ids o nombres).
    body: cuerpo donde se evalúan los selectores de caras y aristas; vacío = el único cuerpo.
    new_name: con rename, el nombre nuevo.
    """
    conjuntos = _conjuntos(sesion, escribir=action in ("create", "update"))
    name, new_name = name.strip(), new_name.strip()
    if action != "list":
        if not name:
            raise error("INVALID_ARGUMENTS", "Indicá el nombre del conjunto.")
        if action != "create" and name not in conjuntos:
            raise error("ENTITY_NOT_FOUND", f"No hay un conjunto de selección «{name}».", "action=list los muestra.")
    if action in ("create", "update"):
        if action == "create" and name in conjuntos:
            raise error("NAME_EXISTS", f"Ya existe el conjunto «{name}».", "action=update le suma objetos.")
        nuevos = [{"tipo": "cuerpo", "cuerpo": sesion.cuerpo(b).id} for b in bodies or []]
        for spec, tipo in ((faces, "cara"), (edges, "arista")):
            if spec:
                nuevos += [sl.referencia(c, e) for c, e in sl.elegir(sesion, spec, tipo, body)]
        if not nuevos:
            raise error("INVALID_ARGUMENTS", "Elegí al menos un cuerpo, cara o arista (bodies, faces, edges).")
        actuales = conjuntos.get(name, [])
        conjuntos[name] = actuales + [r for r in nuevos if r not in actuales]
    elif action == "rename":
        if not new_name or new_name in conjuntos:
            raise error("INVALID_ARGUMENTS", "El nombre nuevo está vacío o ya está en uso.")
        conjuntos[new_name] = conjuntos.pop(name)
    elif action == "delete":
        del conjuntos[name]
    if action not in ("list", "select"):
        sesion.doc.modificado = True
    if action == "select":
        salida = {"bodies": [], "faces": [], "edges": [], "missing": 0}
        for ref in conjuntos[name]:
            r = _resolver_ref(sesion, ref)
            if r is None:
                salida["missing"] += 1
            elif ref["tipo"] == "cuerpo":
                salida["bodies"].append(r[0].id)
            elif ref["tipo"] == "cara":
                salida["faces"] += _ids(sesion, r[0], "cara", [r[1]])
            else:
                salida["edges"] += _ids(sesion, r[0], "arista", [r[1]])
        elegir = getattr(sesion, "seleccionar_cuerpos", None)
        if elegir is not None and salida["bodies"]:
            elegir(salida["bodies"])
        return {"name": name, **salida}
    return {"sets": [{"name": n, "bodies": sum(r["tipo"] == "cuerpo" for r in refs),
                      "faces": sum(r["tipo"] == "cara" for r in refs), "edges": sum(r["tipo"] == "arista" for r in refs)}
                     for n, refs in conjuntos.items()], "count": len(conjuntos)}


@herramienta("select_by_boundary", "documento", "Elige los objetos que quedan dentro o fuera de un límite 3D (Seleccionar › "
             "Herramientas de selección › Por límite): una caja, un cilindro (eje X) o una esfera centrada en un cuerpo "
             "o en un punto. Cuerpos: dentro = entero dentro, intersected suma los que lo cruzan; fuera = ninguna parte "
             "dentro. Caras y aristas se deciden por su centro y sus vértices. No cambia el documento.")
def select_by_boundary(sesion, shape: Literal["box", "cylinder", "sphere"], center: str | list[float],
                       selection: Literal["inside", "outside"] = "inside", intersected: bool = False,
                       kind: Literal["body", "face", "edge"] = "body", x_size: float | None = None,
                       y_size: float | None = None, z_size: float | None = None, radius: float | None = None,
                       length: float | None = None, body: str | None = None):
    """
    shape: box (x_size, y_size, z_size), cylinder (length sobre X y radius) o sphere (radius).
    center: cuerpo (id o nombre) cuyo centro de masa es el centro del límite, o un punto [x, y, z] en mm.
    selection: inside (objetos dentro) u outside (objetos fuera).
    intersected: true suma también los objetos que quedan parcialmente dentro.
    kind: qué se elige: body, face o edge.
    x_size: caja: largo en X, en mm.
    y_size: caja: largo en Y, en mm.
    z_size: caja: largo en Z, en mm.
    radius: cilindro o esfera: radio en mm.
    length: cilindro: largo sobre el eje X, en mm.
    body: con face o edge, el cuerpo donde se buscan; vacío = todos.
    """
    if isinstance(center, str):
        centro = tuple(geo.centro_masa(sesion.cuerpo(center).forma))
    elif len(center) == 3:
        centro = tuple(float(c) for c in center)
    else:
        raise error("INVALID_ARGUMENTS", "center es un cuerpo (id o nombre) o un punto [x, y, z].")
    try:
        limite = spl.limite(shape, centro, x_size, y_size, z_size, radius, length)
    except geo.ErrorGeometria as e:
        raise error("INVALID_ARGUMENTS", str(e)) from e
    cuerpos = [sesion.cuerpo(body)] if body else [c for c in sesion.doc.estado_final.cuerpos.values()
                                                  if getattr(c, "tipo", "solido") == "solido"]
    estado_de = spl.clasificador(limite)

    def elegido(e):
        return e == selection or (intersected and e == "crossing")

    salida = {"bodies": [], "faces": [], "edges": []}
    for c in cuerpos:
        if kind == "body":
            if elegido(spl.estado_de_cuerpo(c.forma, limite)):
                salida["bodies"].append(c.id)
        else:
            tipo = "cara" if kind == "face" else "arista"
            for el in sl.listar(c.forma, tipo):
                if elegido(estado_de(spl.puntos_de(el.sub, el.centro))):
                    salida["faces" if kind == "face" else "edges"].append(sl.emitir_id(sesion, c, el))
    elegir = getattr(sesion, "seleccionar_cuerpos", None)
    if elegir is not None and kind == "body":
        elegir(salida["bodies"])
    return salida


@herramienta("select_by_seed_and_boundary", "documento", "Elige las caras de un cuerpo que hay entre unos objetos límite y una "
             "cara semilla (Seleccionar › Herramientas de selección › Semilla y límite): desde la semilla se avanza de "
             "cara en cara sin cruzar las caras ni las aristas límite. Si hay agujeros entre un lado y otro, pasan los "
             "dos a menos que se incluyan sus aristas como límite. Se puede guardar con manage_selection_sets. No "
             "cambia el documento.")
def select_by_seed_and_boundary(sesion, seed: str, boundary_faces: list[str] | str | None = None,
                                boundary_edges: list[str] | str | None = None, body: str | None = None):
    """
    seed: cara semilla (selector o id de find_faces).
    boundary_faces: caras límite: selector, ids o lista; la selección no las incluye ni las cruza.
    boundary_edges: aristas límite: selector, ids o lista; la selección no las cruza.
    body: cuerpo donde se evalúan los selectores; vacío = el único cuerpo.
    """
    if not boundary_faces and not boundary_edges:
        raise error("INVALID_ARGUMENTS", "Falta el límite: pasá boundary_faces o boundary_edges.")
    cuerpo, semilla = sl.elegir_uno(sesion, seed, "cara", body)
    limites_c = [e.sub for c, e in sl.elegir(sesion, boundary_faces, "cara", body, True) if c.id == cuerpo.id]
    limites_a = [e.sub for c, e in sl.elegir(sesion, boundary_edges, "arista", body, True) if c.id == cuerpo.id]
    if sm._contiene(limites_c, semilla.sub):
        raise error("INVALID_ARGUMENTS", "La semilla no puede ser una de las caras límite.")
    vistas = sm.caras_entre_semilla_y_limite(cuerpo.forma, semilla.sub, limites_c, limites_a)
    return {"faces": _ids(sesion, cuerpo, "cara", vistas), "count": len(vistas), "body": cuerpo.id}

# -*- coding: utf-8 -*-
"""Herramientas del timeline que no son de un cuerpo: el marcador (Fusion: «Rodar marcador aquí»), qué bocetos usa un
paso («Editar boceto de perfil» del menú), las carpetas de pasos (SC9) y copiar un paso (Ctrl+C y Ctrl+V del timeline)."""
from typing import Literal

from .errores import error
from .registro import herramienta


@herramienta("move_feature", "documento",
             "Mueve un paso del timeline a otro índice (como arrastrarlo en la app). Si no se puede (un "
             "paso que depende de otro quedaría antes), falla con OPERATION_FAILED y el motivo. Es lo que "
             "usa la pista del error de empalme: reordenar los empalmes de mayor a menor radio.",
             modifica=True, transaccion=False)
def move_feature(sesion, feature: str, index: int):
    """
    feature: id o nombre del paso a mover.
    index: índice nuevo (0 = primero, se recorta al final del timeline).
    """
    doc = sesion.doc
    try:
        op = sesion.paso(feature)
    except Exception as e:                     # noqa: BLE001 — el paso que no existe ya trae su mensaje
        raise error("FEATURE_NOT_FOUND", str(e).split(".")[0] + ".") from None
    antes = doc.indice(op.id)
    try:
        doc.mover(op.id, int(index))
    except Exception as e:                     # noqa: BLE001 — ErrorDocumento con el motivo
        raise error("OPERATION_FAILED", str(e)) from None
    return {"id": op.id, "name": op.nombre, "before": antes, "now": doc.indice(op.id)}


def _pasos(doc, desde):
    return [{"id": o.id, "name": o.nombre, "type": o.TIPO} for o in doc.operaciones[desde:]]


def bocetos_de_perfil(doc, op):
    """Bocetos que usa el paso `op` (perfiles de una extrusión o revolución, ruta de un barrido…), en el orden del
    timeline. Lo usan esta API y el menú del timeline («Editar boceto de perfil»)."""
    try:
        deps = op.dependencias()
    except Exception:  # noqa: BLE001 — un paso con parámetros rotos no tiene boceto de perfil que ofrecer
        return []
    return [o for o in doc.operaciones if o.id in deps and o.TIPO == "boceto" and o.id != op.id]


@herramienta("set_marker", "documento",
             "Mueve el marcador del timeline (Fusion: «Rodar marcador aquí» del menú contextual). Lo que queda a la "
             "derecha del marcador no se calcula (estado rolled_back) hasta volver a moverlo. Indicá UNO: position, "
             "after (el marcador queda justo después de ese paso, que sí se calcula) o before (justo antes). "
             "undo lo vuelve a donde estaba. Si al avanzar un paso queda con error, se avisa (errors) pero el marcador "
             "se mueve igual (como en la app).",
             modifica=True, transaccion=False)
def set_marker(sesion, position: int | None = None, after: str | None = None, before: str | None = None):
    """
    position: índice del marcador: 0 = antes del primer paso; la cantidad de pasos = al final (todo calculado).
    after: id o nombre de un paso: el marcador queda justo después (como «Rodar marcador aquí» sobre ese paso).
    before: id o nombre de un paso: el marcador queda justo antes (ni ese paso ni los siguientes se calculan).
    """
    doc = sesion.doc
    dados = [x for x in (position, after, before) if x is not None]
    if len(dados) != 1:
        raise error("INVALID_ARGUMENTS", "Indicá exactamente uno de position, after o before.")
    total = len(doc.operaciones)
    if position is not None:
        if not 0 <= position <= total:
            raise error("INVALID_ARGUMENTS", f"position tiene que estar entre 0 y {total} (cantidad de pasos).")
        nuevo = position
    elif after is not None:
        nuevo = doc.indice(sesion.paso(after).id) + 1
    else:
        nuevo = doc.indice(sesion.paso(before).id)
    if nuevo != doc.marcador:
        doc._guardar_para_deshacer()     # sin transacción (no rechaza avanzar sobre un paso con error): a mano
    doc.mover_marcador(nuevo)
    errores = [{"id": o.id, "name": o.nombre, "message": r.mensaje}
               for o, r in zip(doc.operaciones[:doc.marcador], doc.resultados, strict=False) if r.estado == "error"]
    if errores:
        sesion.avisar("Pasos con error antes del marcador: " + ", ".join(e["name"] for e in errores) + ".")
    return {"marker": doc.marcador, "steps": total, "rolled_back": _pasos(doc, doc.marcador), "errors": errores}


@herramienta("get_profile_sketches", "documento",
             "Bocetos que usa un paso del timeline (perfiles de una extrusión o revolución, ruta de un barrido…), "
             "en orden: lo mismo que abre «Editar boceto de perfil» en el timeline. Sus ids sirven como «sketch» "
             "de las herramientas de boceto (get_sketch, draw_line…); los derivados externos son de solo lectura.")
def get_profile_sketches(sesion, feature: str):
    """
    feature: id o nombre del paso (p. ej. una extrusión).
    """
    op = sesion.paso(feature)
    bocetos = [{"id": b.id, "name": b.nombre} for b in bocetos_de_perfil(sesion.doc, op)]
    bid = op.p.get("boceto")
    br = sesion.doc.estado_final.bocetos.get(bid) if isinstance(bid, str) else None
    if br is not None and br.op_id not in {b["id"] for b in bocetos}:
        bocetos.append({"id": br.op_id, "name": br.nombre})
    return {"feature": {"id": op.id, "name": op.nombre, "type": op.TIPO},
            "sketches": bocetos}


def _info_grupo(g):
    return {"id": g["id"], "name": g["nombre"], "steps": list(g["pasos"]), "collapsed": g["plegado"]}


def _grupo(sesion, ref):
    """La carpeta del timeline por id o por nombre (sin distinguir mayúsculas), como `Sesion.paso` con los pasos."""
    for g in sesion.doc.grupos:
        if g["id"] == ref or g["nombre"].casefold() == str(ref).casefold():
            return g
    raise error("GROUP_NOT_FOUND", f"No existe la carpeta '{ref}'.")


@herramienta("manage_feature_groups", "documento",
             "Carpetas del timeline (Fusion: Organize features into groups). action=create junta dos o más pasos "
             "(steps, con name opcional); rename le cambia el nombre a una carpeta (group, name); ungroup borra la "
             "carpeta y deja sus pasos sueltos, en el mismo orden (Edit Group › Expand); list las muestra todas. Una "
             "carpeta NO es un paso: agrupar no cambia el orden de ejecución, el recálculo ni el volumen.",
             modifica=True)
def manage_feature_groups(sesion, action: Literal["create", "rename", "ungroup", "list"],
                          steps: list[str] | None = None, group: str | None = None, name: str | None = None):
    """
    action: create, rename, ungroup o list.
    steps: ids o nombres de los pasos (create: hacen falta dos o más; nada en las demás).
    group: id o nombre de la carpeta (rename y ungroup).
    name: nombre de la carpeta (obligatorio en rename, opcional en create).
    """
    doc = sesion.doc
    if action == "list":
        if steps is not None or group is not None or name is not None:
            raise error("INVALID_ARGUMENTS", "action='list' no recibe steps, group ni name.")
        return {"groups": [_info_grupo(g) for g in doc.grupos]}
    if action == "create":
        if group is not None:
            raise error("INVALID_ARGUMENTS", "action='create' no recibe group: la carpeta nueva se crea acá.")
        if not steps or len(steps) < 2:
            raise error("INVALID_ARGUMENTS", "action='create' necesita steps con dos o más pasos del timeline.")
        return {"group": _info_grupo(doc.agrupar([sesion.paso(f).id for f in steps], name))}
    if action == "rename":
        if group is None or steps is not None or not (name or "").strip():
            raise error("INVALID_ARGUMENTS", "action='rename' necesita group y name (sin steps).")
        g = _grupo(sesion, group)
        doc.renombrar_grupo(g["id"], name)
        return {"group": _info_grupo(doc.grupo(g["id"]))}
    if group is None or steps is not None or name is not None:
        raise error("INVALID_ARGUMENTS", "action='ungroup' necesita solo group.")
    g = _grupo(sesion, group)
    doc.desagrupar(g["id"])
    return {"ungrouped": g["id"], "steps": g["pasos"], "groups": [_info_grupo(x) for x in doc.grupos]}


@herramienta("duplicate_feature", "documento",
             "Copia un paso del timeline (el Ctrl+C y Ctrl+V del timeline): mismo tipo y mismos parámetros, con id "
             "nuevo y nombre «X (1)», en el puesto donde el timeline inserta un paso nuevo (el marcador). Si el paso "
             "usa algo que no está antes de ese puesto (otro documento, un tramo retrocedido), falla con "
             "OPERATION_FAILED y no copia nada. Si la copia llega a no poder calcularse (un empalme cuyas aristas ya "
             "consumió el original), se pega igual, queda en rojo y se avisa en avisos.", modifica=True)
def duplicate_feature(sesion, feature: str):
    """
    feature: id o nombre del paso a copiar.
    """
    op = sesion.paso(feature)
    sesion.tolerar_errores = True      # la copia puede quedar en rojo (sus aristas ya las usó el original): se avisa, no se revierte
    try:
        nueva = sesion.doc.pegar(op.a_dict(), op.dependencias())
    except Exception as e:                     # noqa: BLE001 — ErrorDocumento ya trae el motivo en español
        raise error("OPERATION_FAILED", str(e)) from None
    return {"feature": {"id": nueva.id, "name": nueva.nombre, "type": nueva.TIPO}, "from": op.id,
            "index": sesion.doc.indice(nueva.id)}

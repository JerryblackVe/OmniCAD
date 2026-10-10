# -*- coding: utf-8 -*-
"""Herramientas del timeline que no cambian pasos: el marcador (Fusion: «Rodar marcador aquí»), y qué bocetos
usa un paso («Editar boceto de perfil» del menú contextual del timeline)."""
from .errores import error
from .registro import herramienta


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
             "de las herramientas de boceto (get_sketch, draw_line…).")
def get_profile_sketches(sesion, feature: str):
    """
    feature: id o nombre del paso (p. ej. una extrusión).
    """
    op = sesion.paso(feature)
    return {"feature": {"id": op.id, "name": op.nombre, "type": op.TIPO},
            "sketches": [{"id": b.id, "name": b.nombre} for b in bocetos_de_perfil(sesion.doc, op)]}

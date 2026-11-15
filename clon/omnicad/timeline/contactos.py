# -*- coding: utf-8 -*-
"""Conjuntos de contactos (Fusion: ENSAMBLAR › Activar conjuntos de contactos / Nuevo conjunto de contactos /
Activar todos los contactos / Desactivar todos los contactos).

Con el análisis de contacto prendido, accionar una unión no puede meter un componente dentro de otro: el movimiento que
haría que se superpongan se rechaza y todo queda donde estaba. Prendido es `modo`:
- "ninguno" (por defecto): sin análisis de contacto.
- "conjuntos": solo vigilan los pares de componentes que están en un mismo conjunto no suprimido.
- "todos": se vigilan todos los componentes entre sí, haya o no conjuntos.

Los conjuntos no son pasos del timeline (como las vistas guardadas): viven en `doc.espacios["contactos"]`, se guardan con
el proyecto y entran en deshacer. Sin Qt.
"""
from ..nucleo import analisis as an
from .ops_ensamblar import familia

MODOS = ("ninguno", "conjuntos", "todos")


def datos(doc):
    d = doc.espacios.get("contactos") or {}
    modo = d.get("modo") if d.get("modo") in MODOS else "ninguno"
    return {"modo": modo, "conjuntos": [dict(c) for c in d.get("conjuntos") or []]}


def guardar(doc, d):
    doc._guardar_para_deshacer()
    doc.espacios["contactos"] = d
    doc.modificado = True
    doc._notificar()


def _grupos(doc, estado):
    """Qué grupos de componentes se vigilan entre sí: una lista de listas de conjuntos de ids de componente (cada
    conjunto es un miembro con sus subcomponentes). Dentro de un grupo, dos miembros distintos no pueden superponerse."""
    d = datos(doc)
    if d["modo"] == "todos":
        return [[{k} for k in estado.componentes] + [{""}]]
    if d["modo"] == "conjuntos":
        return [[familia(estado, k) for k in c["componentes"] if k in estado.componentes]
                for c in d["conjuntos"] if not c.get("suprimido")]
    return []


def superposiciones(doc):
    """Los pares (id de cuerpo, id de cuerpo) que hoy se superponen y que el análisis de contacto vigila; vacío con el
    análisis apagado."""
    estado = doc.estado_final
    solidos = {c.id: c for c in estado.cuerpos.values() if c.tipo == "solido"}
    pares = set()
    for grupo in _grupos(doc, estado):
        miembro = {}
        for i, comps in enumerate(grupo):
            for c in solidos.values():
                if (c.componente or "") in comps:
                    miembro.setdefault(c.id, i)
        if len(set(miembro.values())) < 2:
            continue
        for i in an.interferencias({k: solidos[k].forma for k in miembro}):
            if miembro[i["a"]] != miembro[i["b"]]:
                pares.add(tuple(sorted((i["a"], i["b"]))))
    return pares


def bloqueo(doc, antes):
    """Mensaje si el último cambio hizo que se superpongan componentes vigilados (pares que no estaban en `antes`, lo
    que devolvió `superposiciones` antes del cambio); None si no. A propósito, un par que ya se superponía antes no
    bloquea: así un modelo que arranca superpuesto se puede seguir moviendo."""
    nuevos = superposiciones(doc) - antes
    if not nuevos:
        return None
    estado = doc.estado_final
    a, b = sorted(nuevos)[0]
    return f"⛔ «{estado.cuerpos[a].nombre}» chocaría con «{estado.cuerpos[b].nombre}». Apagá los contactos en ENSAMBLAR para moverlo."

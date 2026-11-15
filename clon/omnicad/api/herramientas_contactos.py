# -*- coding: utf-8 -*-
"""
Herramientas del grupo "ensamble" para los conjuntos de contactos (ENSAMBLAR › Activar conjuntos de contactos, Nuevo
conjunto de contactos, Activar todos los contactos, Desactivar todos los contactos; `timeline/contactos.py`).
Con el análisis de contacto prendido, drive_joint rechaza el movimiento que haría que se superpongan componentes
vigilados (error CONTACT_BLOCKED) y deja todo como estaba.
"""
from typing import Literal

from ..timeline import contactos as ct
from .errores import error
from .herramientas_ensamble import componente
from .registro import herramienta

_MODOS = {"none": "ninguno", "sets": "conjuntos", "all": "todos"}


def _info(sesion):
    d = ct.datos(sesion.doc)
    estado = sesion.doc.estado_final
    return {"mode": {v: k for k, v in _MODOS.items()}[d["modo"]],
            "sets": [{"id": c["id"], "name": c["nombre"], "suppressed": bool(c.get("suprimido")),
                      "components": [{"id": k, "name": str(estado.componentes.get(k, {}).get("nombre") or k)}
                                     for k in c["componentes"]]} for c in d["conjuntos"]]}


@herramienta("get_contact_sets", "ensamble", "Los conjuntos de contactos y si el análisis de contacto está prendido "
             "(ENSAMBLAR › Activar conjuntos de contactos): mode es none (apagado), sets (solo los conjuntos) o all "
             "(todos los componentes entre sí).")
def get_contact_sets(sesion):
    """
    """
    return _info(sesion)


@herramienta("set_contact_mode", "ensamble", "Prende o apaga el análisis de contacto (ENSAMBLAR › Activar conjuntos de "
             "contactos, Activar todos los contactos y Desactivar todos los contactos): con él prendido, drive_joint "
             "rechaza el movimiento que haría que se superpongan los componentes vigilados (CONTACT_BLOCKED).", modifica=True)
def set_contact_mode(sesion, mode: Literal["none", "sets", "all"]):
    """
    mode: "sets" vigila los pares de cada conjunto (Enable Contact Sets); "all" vigila todos los componentes entre sí (Enable All Contact); "none" apaga todo (Disable All Contact).
    """
    if mode not in _MODOS:
        raise error("INVALID_ARGUMENTS", f"mode es none, sets o all (llegó «{mode}»).")
    d = ct.datos(sesion.doc)
    if d["modo"] != _MODOS[mode]:
        ct.guardar(sesion.doc, dict(d, modo=_MODOS[mode]))
    return _info(sesion)


@herramienta("create_contact_set", "ensamble", "Crea un conjunto de contactos entre 2 o más componentes (ENSAMBLAR › "
             "Nuevo conjunto de contactos): con el análisis de contacto en «sets», esos componentes no pueden "
             "atravesarse. No lo prende: usá set_contact_mode.", modifica=True)
def create_contact_set(sesion, components: list[str], name: str = ""):
    """
    components: 2 o más componentes (id o nombre, o el id o nombre de uno de sus cuerpos).
    name: nombre del conjunto; vacío = «Conjunto de contactos<n>».
    """
    ids = list(dict.fromkeys(componente(sesion, c) for c in components or []))
    if len(ids) < 2:
        raise error("INVALID_ARGUMENTS", "Un conjunto de contactos necesita 2 o más componentes distintos.")
    d = ct.datos(sesion.doc)
    n = 1 + max([int(c["id"][2:]) for c in d["conjuntos"] if c["id"][2:].isdigit()] or [0])
    nombre = name.strip() or f"Conjunto de contactos{n}"
    if nombre.casefold() in {c["nombre"].casefold() for c in d["conjuntos"]}:
        raise error("INVALID_ARGUMENTS", f"Ya hay un conjunto de contactos llamado «{nombre}».")
    d["conjuntos"].append({"id": f"CS{n}", "nombre": nombre, "componentes": ids, "suprimido": False})
    ct.guardar(sesion.doc, d)
    return _info(sesion)


@herramienta("delete_contact_set", "ensamble", "Borra un conjunto de contactos (navegador › Conjuntos de contactos › "
             "Eliminar).", modifica=True)
def delete_contact_set(sesion, contact_set: str):
    """
    contact_set: id (CS1) o nombre del conjunto.
    """
    d = ct.datos(sesion.doc)
    hallado = next((c for c in d["conjuntos"] if contact_set in (c["id"], c["nombre"])), None)
    if hallado is None:
        raise error("INVALID_ARGUMENTS", f"No hay un conjunto de contactos «{contact_set}»: "
                    + (", ".join(c["id"] for c in d["conjuntos"]) or "no hay ninguno") + ".")
    d["conjuntos"].remove(hallado)
    ct.guardar(sesion.doc, d)
    return _info(sesion)

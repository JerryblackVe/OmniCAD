# -*- coding: utf-8 -*-
"""Cinta personalizable (P-164), sin Qt: cuántos botones grandes lleva cada sección de la cinta y en qué orden, más la
sección «FAVORITAS» que cada persona llena (como «Pin to toolbar» de Fusion). Lo usan la página «Cinta» de Preferencias y
las herramientas `get_ribbon` / `set_ribbon_section` / `reset_ribbon`.

Lo elegido se guarda en la preferencia `cinta/personal` (JSON «PESTAÑA/GRUPO» → lista de claves de comando); una sección
que no está ahí queda como de fábrica.
"""
import json

from .catalogo_atajos import CATALOGO
from .catalogo_cinta import SECCIONES, TITULOS_BOCETO

COMANDOS = {**CATALOGO, **{c: (t, "") for c, t in TITULOS_BOCETO.items()}}      # + los del boceto (P-187)
MAXIMO = 8          # botones grandes por sección: con más, la cinta no entra en una pantalla de 1024 px


def maximo(seccion):
    """Botones grandes que admite la sección: MAXIMO, o los de fábrica si son más (RESTRICCIONES del boceto, P-187)."""
    return max(MAXIMO, len(SECCIONES.get(seccion, ())))


def leer(texto):
    """{sección: [claves]} de la preferencia; un JSON roto, secciones que no existen, comandos que no existen, repetidos
    o más de MAXIMO se ignoran."""
    try:
        datos = json.loads(texto or "{}")
    except (ValueError, RecursionError):
        return {}
    if not isinstance(datos, dict):
        return {}
    salida = {}
    for seccion, claves in datos.items():
        if seccion in SECCIONES and isinstance(claves, list):
            limpias = list(dict.fromkeys(c for c in claves if isinstance(c, str) and c in COMANDOS))
            salida[seccion] = limpias[:maximo(seccion)]
    return salida


def efectivas(personal):
    """{sección: [claves vigentes]} de todas las secciones."""
    return {s: list(personal.get(s, base)) for s, base in SECCIONES.items()}


def diferencias(efectiva):
    """Lo que hay que guardar: solo las secciones que difieren de fábrica."""
    return {s: c for s, c in efectiva.items() if c != SECCIONES[s]}


def titulo(clave):
    return COMANDOS[clave][0]


def validar(seccion, claves):
    """La lista limpia para `seccion`, o un texto con el motivo si no sirve."""
    if seccion not in SECCIONES:
        return "No existe la sección «%s»." % seccion
    if not isinstance(claves, list) or not all(isinstance(c, str) for c in claves):
        return "Las herramientas van en una lista de claves de comando."
    malas = [c for c in claves if c not in COMANDOS]
    if malas:
        return "No existe el comando «%s»." % malas[0]
    if len(set(claves)) != len(claves):
        return "Hay herramientas repetidas."
    if len(claves) > maximo(seccion):
        return "Una sección lleva como mucho %d botones." % maximo(seccion)
    return None


def a_texto(personal):
    return json.dumps(personal, sort_keys=True, ensure_ascii=False)

# -*- coding: utf-8 -*-
"""Atajos de teclado de la ventana (P-165), sin Qt: los usan la página «Atajos de teclado» de Preferencias y las
herramientas `list_shortcuts` / `set_shortcut` / `reset_shortcuts`. Equivale a «Change Keyboard Shortcut» de Fusion.

Lo elegido se guarda en la preferencia `atajos/teclas` (JSON clave → combinación, solo lo que difiere de fábrica;
"" = sin atajo), la misma que usa «Más › Cambiar atajo de teclado» de la ventana.
"""
import json
import re

from .catalogo_atajos import CATALOGO

_MODIFICADORES = ("Meta", "Ctrl", "Alt", "Shift")          # el orden en que Qt los escribe
_ALIAS = {"control": "Ctrl", "ctrl": "Ctrl", "alt": "Alt", "shift": "Shift", "mayus": "Shift", "meta": "Meta",
          "escape": "Esc", "esc": "Esc", "delete": "Del", "del": "Del", "supr": "Del", "insert": "Ins", "ins": "Ins",
          "pageup": "PgUp", "pgup": "PgUp", "pagedown": "PgDown", "pgdown": "PgDown", "return": "Return",
          "enter": "Enter", "space": "Space", "espacio": "Space", "tab": "Tab", "backspace": "Backspace",
          "up": "Up", "down": "Down", "left": "Left", "right": "Right", "home": "Home", "end": "End"}
_TECLA = re.compile(r"^(F([1-9]|1[0-9]|2[0-4])|[A-Z0-9]|[`~!@#$%^&*()\-_=+\[\]{};:'\",.<>/?\\|])$")


def normalizar(texto):
    """'control+shift+s' → 'Ctrl+Shift+S' (el texto portable de Qt). None si no es una combinación válida
    (una sola tecla con a lo sumo los modificadores); "" = sin atajo."""
    texto = (texto or "").strip()
    if not texto:
        return ""
    if texto == "+" or texto.endswith("++"):       # la tecla es «+» ('Ctrl++')
        mods, tecla = [m for m in texto[:-1].split("+") if m], "+"
    else:
        *mods, tecla = [p.strip() for p in texto.split("+")]
    if not tecla:
        return None
    nombres = []
    for m in mods:
        n = _ALIAS.get(m.lower())
        if n not in _MODIFICADORES or n in nombres:
            return None
        nombres.append(n)
    tecla = _ALIAS.get(tecla.lower(), tecla.upper() if len(tecla) == 1 else tecla.upper())
    if tecla in ("Ctrl", "Alt", "Shift", "Meta"):
        return None
    if not (tecla in _ALIAS.values() or _TECLA.match(tecla)):
        return None
    return "+".join([m for m in _MODIFICADORES if m in nombres] + [tecla])


def leer(texto):
    """{clave: combinación} de la preferencia `atajos/teclas`; un JSON roto, ajeno o con valores inválidos se ignora."""
    try:
        datos = json.loads(texto or "{}")
    except (ValueError, RecursionError):
        return {}
    if not isinstance(datos, dict):
        return {}
    return {str(c): n for c, t in datos.items() if c in CATALOGO and isinstance(t, str)
            and (n := normalizar(t)) is not None}


def efectivos(teclas):
    """{clave: combinación vigente} de todos los comandos: la elegida o la de fábrica."""
    return {c: normalizar(teclas.get(c, d)) or "" for c, (_t, d) in CATALOGO.items()}


def contexto(clave):
    """«boceto» para las herramientas del boceto (sk_*), «diseno» para el resto: dentro del boceto las suyas tapan a las
    del mismo atajo de la ventana (`ModoBoceto._tapar_atajos`), así que solo chocan entre las del mismo contexto."""
    return "boceto" if clave.startswith("sk_") else "diseno"


def choques(efectivo):
    """{clave: [claves que usan su misma combinación en su contexto]} solo de los comandos en choque."""
    por_tecla = {}
    for c, t in efectivo.items():
        if t:
            por_tecla.setdefault((contexto(c), t), []).append(c)
    return {c: [o for o in cs if o != c] for cs in por_tecla.values() if len(cs) > 1 for c in cs}


def titulo(clave):
    return CATALOGO[clave][0]


def diferencias(efectivo):
    """Lo que hay que guardar: solo los comandos cuya combinación difiere de la de fábrica."""
    return {c: t for c, t in efectivo.items() if t != (normalizar(CATALOGO[c][1]) or "")}

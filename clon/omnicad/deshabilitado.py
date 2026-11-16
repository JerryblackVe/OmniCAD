# -*- coding: utf-8 -*-
"""Lo que hoy no funciona y por eso se ve en gris con «No disponible: <motivo>» (P-169). Sin Qt: la ventana, la cinta, los
paneles y la API leen esta misma lista.

Regla (Gerardo, 2026-11-16): toda función que falla en el uso común (un bug Abierto que rompe o pierde trabajo, o algo
que no hace nada) queda deshabilitada hasta que funcione y esté probada. Se deshabilita lo más chico posible: la opción,
no el comando entero.

Cómo se agrega una entrada: `"clave": ("motivo en 1 renglón, sin jerga", "B-123")`. La clave es:
  - `"extruir"`: un comando de la ventana (clave de `ui/comandos/`, la misma de la cinta y de los menús);
  - `"extruir.simetrico"`: un campo de su panel (`Campo.clave`);
  - `"extruir.tipo.dos_lados"`: una opción de un campo `Opciones`/`Botones` (la clave de la opción);
  - `"nombre_de_herramienta"`: una herramienta de la API/MCP/CLI (`api.llamar` la rechaza con `FEATURE_DISABLED`).
El ID es el del bug abierto en `docs/seguimiento/`. La entrada se QUITA en el mismo commit que cierra ese bug
(`tests/test_deshabilitado.py` falla si el ID ya no está en el seguimiento).
"""

DESHABILITADO: dict[str, tuple[str, str]] = {}


def entrada(clave):
    """(motivo, id de bug) de lo deshabilitado, o None si anda."""
    return DESHABILITADO.get(clave)


def motivo(clave):
    """«No disponible: <motivo>» para el tooltip, o None si anda."""
    e = DESHABILITADO.get(clave)
    return f"No disponible: {e[0]}" if e else None

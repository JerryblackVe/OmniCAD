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

DESHABILITADO: dict[str, tuple[str, str]] = {
}

# Ítems de la cinta y de los menús que nunca tuvieron comando (`_i("Texto")` sin clave): ya salen en gris y acá dicen por qué.
# La clave es el texto del ítem; el ID es la fila de `docs/seguimiento/` (también vale `despues.md`) y la entrada se quita
# cuando el comando existe y tiene su clave.
SIN_COMANDO: dict[str, tuple[str, str]] = {
    "Crear forma": ("todavía no se puede crear una forma libre", "P-25i"),
    "Crear placa de circuito impreso": ("la placa de circuito no está hecha", "P-25i"),
    "Administrar materiales": ("los materiales se cambian desde Aspecto", "P-25d"),
    "Crear reglas de configuración": ("las reglas de configuración no están hechas", "CFG-1"),
    "Edición directa": ("la edición directa de mallas no está hecha", "MAL-2"),
    "Alinear": ("alinear mallas no está hecho", "MAL-2"),
    "Extruir textura": ("extruir textura no está hecho", "MAL-2"),
    "Pestaña solevada": ("la pestaña solevada no está hecha", "CHA-1"),
    "Cierre de esquina": ("el cierre de esquina no está hecho", "CHA-1"),
    "Desplazar al grupo": ("los grupos dentro de grupos no están hechos", "P-23c3"),
    "Copiar": ("copiar cuerpos con sus referencias no está hecho", "P-23c2"),
    "Cortar": ("cortar cuerpos con sus referencias no está hecho", "P-23c2"),
}


def entrada(clave):
    """(motivo, id de bug) de lo deshabilitado, o None si anda."""
    return DESHABILITADO.get(clave)


def motivo_sin_comando(texto, defecto=None):
    """«No disponible: <motivo>» de un ítem gris sin comando (por su texto), o `defecto` si no figura."""
    e = SIN_COMANDO.get(texto)
    return f"No disponible: {e[0]}" if e else defecto


def motivo(clave):
    """«No disponible: <motivo>» para el tooltip, o None si anda."""
    e = DESHABILITADO.get(clave)
    return f"No disponible: {e[0]}" if e else None

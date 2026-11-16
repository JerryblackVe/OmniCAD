# -*- coding: utf-8 -*-
"""Temas de color de toda la app por MCP y CLI (P-166): lo mismo que Preferencias › Apariencia › tarjetas de temas.

Solo los temas incluidos y el del sistema: los temas del usuario son archivos en una carpeta y un agente no elige rutas.
"""
from ..ui import temas
from .errores import error
from .herramientas_preferencias import _ajustes
from .registro import herramienta

CLAVE = "general/tema"


def _actual(ajustes):
    return str(ajustes.value(CLAVE, temas.DEFECTO, type=str) or temas.DEFECTO)


@herramienta("list_themes", "documento", "Lista los temas de color de la interfaz (Preferencias › Apariencia): el del sistema "
             "y los incluidos, con sus colores principales para verlos sin abrir la ventana, y cuál está elegido.")
def list_themes(sesion):
    actual = _actual(_ajustes())
    filas = [{"theme": temas.SISTEMA, "name": "Tema del sistema", "current": actual == temas.SISTEMA,
              "colors": None}]
    for clave, t in temas.INCLUIDOS.items():
        c = t["colores"]
        filas.append({"theme": clave, "name": t["nombre"], "current": actual == clave,
                      "colors": {k: c[k] for k in ("fondo", "panel", "texto", "acento", "visor_arriba")}})
    return {"themes": filas, "current": actual}


@herramienta("set_theme", "documento", "Elige el tema de color de toda la interfaz (uno de list_themes). No modifica el "
             "documento ni entra en deshacer; la ventana lo toma al aplicar preferencias.", modifica=True,
             transaccion=False)
def set_theme(sesion, theme: str):
    """
    theme: clave de list_themes ('oscuro_moderno', 'claro_moderno', 'sistema'…).
    """
    if theme != temas.SISTEMA and theme not in temas.INCLUIDOS:
        raise error("INVALID_ARGUMENTS", f"No existe el tema «{theme}».", "list_themes lista los temas.")
    ajustes = _ajustes()
    ajustes.setValue(CLAVE, theme)
    ajustes.sync()
    if ajustes.status() != ajustes.Status.NoError:
        raise error("FILE_ERROR", "No se pudieron guardar las preferencias.")
    return {"theme": theme}

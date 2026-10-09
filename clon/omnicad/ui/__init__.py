# -*- coding: utf-8 -*-
"""Interfaz gráfica (PySide6): ventana, visor 3D, editor de bocetos, diálogos y timeline."""
import os
import sys


def _plataforma_linux():
    """Linux, antes de crear la QApplication y de importar OpenGL (por eso va acá: `OmniCAD.py` importa este paquete
    antes de crear la aplicación y solo `omnicad.ui` importa OpenGL).

    1. Qt: si hay servidor X (`DISPLAY`, también XWayland en escritorios Wayland y WSLg) se usa `xcb`. Con Wayland, el
       menú radial que abre la prueba de humo se cierra y se borra solo (en xcb no), y Wayland no deja ubicar ventanas
       en coordenadas de pantalla (caja S, menú radial junto al cursor). Para usar Wayland igual: QT_QPA_PLATFORM=wayland.
    2. PyOpenGL: elige EGL apenas ve `WAYLAND_DISPLAY`, pero Qt con `xcb` u `offscreen` crea contextos GLX: el visor no
       encontraba el contexto («Attempt to retrieve context when no valid context»). Se le pide GLX."""
    if not sys.platform.startswith("linux"):
        return
    if "QT_QPA_PLATFORM" not in os.environ and os.environ.get("DISPLAY"):
        os.environ["QT_QPA_PLATFORM"] = "xcb"
    qt = os.environ.get("QT_QPA_PLATFORM", "").split(";")[0].split(":")[0]
    if ("PYOPENGL_PLATFORM" not in os.environ and qt in ("xcb", "offscreen")
            and os.environ.get("QT_XCB_GL_INTEGRATION") != "xcb_egl"):
        os.environ["PYOPENGL_PLATFORM"] = "glx"


_plataforma_linux()

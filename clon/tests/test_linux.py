# -*- coding: utf-8 -*-
"""Linux (pendiente 1): plataforma de Qt y API de contexto de PyOpenGL. Corre en cualquier sistema (simula Linux)."""
import os
import sys

import pytest

from omnicad import ui

X, W = {"DISPLAY": ":0"}, {"WAYLAND_DISPLAY": "wayland-0"}


@pytest.mark.parametrize("plataforma, entorno, qt, pyopengl", [
    ("linux", {**X, **W}, "xcb", "glx"),                                  # WSLg y escritorios Wayland con XWayland
    ("linux", W, None, None),                                             # Wayland sin X: Qt y PyOpenGL usan EGL solos
    ("linux", X, "xcb", "glx"),                                           # escritorio X11
    ("linux", {**X, **W, "QT_QPA_PLATFORM": "wayland"}, "wayland", None),  # Wayland pedido a mano: se respeta
    ("linux", {**W, "QT_QPA_PLATFORM": "offscreen"}, "offscreen", "glx"),  # las pruebas
    ("linux", {**X, "QT_XCB_GL_INTEGRATION": "xcb_egl"}, "xcb", None),     # xcb con EGL
    ("linux", {**X, "PYOPENGL_PLATFORM": "egl"}, "xcb", "egl"),            # lo que pidió el usuario se respeta
    ("win32", {**X, **W}, None, None),
])
def test_plataforma_de_qt_y_pyopengl(monkeypatch, plataforma, entorno, qt, pyopengl):
    """Con WAYLAND_DISPLAY, PyOpenGL elegía EGL aunque Qt (offscreen/xcb) creara contextos GLX: el visor fallaba con
    «Attempt to retrieve context when no valid context» (40 pruebas en Ubuntu 24.04 sobre WSL2)."""
    falso = dict(entorno)               # entorno aparte: un PYOPENGL_PLATFORM=glx real rompería OpenGL en Windows
    monkeypatch.setattr(os, "environ", falso)
    monkeypatch.setattr(sys, "platform", plataforma)
    ui._plataforma_linux()
    assert (falso.get("QT_QPA_PLATFORM"), falso.get("PYOPENGL_PLATFORM")) == (qt, pyopengl)

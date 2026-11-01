# -*- coding: utf-8 -*-
import os
import sys
import tempfile
from pathlib import Path

import pytest

# Permite `import omnicad` corriendo pytest desde cualquier carpeta.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Todas las pruebas corren sin ventanas. Va acá, ANTES de importar cualquier módulo: en Linux `omnicad.ui` elige con
# esto la API de contexto de PyOpenGL (GLX para offscreen) y algunos archivos de prueba importan la interfaz sin fijarlo.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
# Sin esto, la primera QApplication que se crea (según el archivo que corra antes) dibuja el texto de los íconos con otra
# fuente que Segoe UI y cambia sus colores (B-112: test_iconos_gramatica); en Linux Qt ya usa fontconfig.
if sys.platform == "win32":
    os.environ.setdefault("QT_QPA_FONTDIR", os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts"))
# Las vistas animadas (P-45) no corren en pruebas: cada prueba espera la cámara al instante.
os.environ.setdefault("OMNICAD_SIN_ANIMACION", "1")
# El historial del Asistente (asistente/historial.py) nunca se escribe en la carpeta del usuario durante las pruebas.
os.environ.setdefault("OMNICAD_ASISTENTE_DIR", tempfile.mkdtemp(prefix="omnicad_chats_"))
os.environ.setdefault("OMNICAD_PREAJUSTES", os.path.join(tempfile.mkdtemp(prefix="omnicad_preajustes_"), "preajustes.json"))
os.environ.setdefault("OMNICAD_REGLAS_PLASTICO", os.path.join(tempfile.mkdtemp(prefix="omnicad_plastico_"), "reglas.json"))

if os.environ.get("OMNICAD_BLOQUEAR_OCP") == "1":
    from omnicad.bloqueo_ocp import activar
    activar()


@pytest.fixture(autouse=True)
def _sin_trabajador_entre_pruebas():
    """El trabajador de `nucleo/aislado.py` vive más que un cálculo: cada prueba arranca el suyo (con su `_comando`)."""
    yield
    if "omnicad.nucleo.aislado" in sys.modules:
        sys.modules["omnicad.nucleo.aislado"].cerrar_trabajador()


def pytest_sessionfinish(session, exitstatus):
    """Cierra y borra las ventanas que quedaron ANTES de que Python se apague: si las destruye el cierre del intérprete,
    Qt llama a métodos de objetos Python ya borrados y el proceso aborta («pure virtual method called») con todas las
    pruebas en verde (Linux; en Windows, segfault al salir)."""
    if "PySide6.QtWidgets" not in sys.modules:
        return
    from PySide6.QtCore import QCoreApplication, QEvent
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        return
    for w in app.topLevelWidgets():
        w.close()
        w.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    app.processEvents()

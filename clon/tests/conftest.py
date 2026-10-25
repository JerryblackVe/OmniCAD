# -*- coding: utf-8 -*-
import os
import sys
import tempfile
from pathlib import Path

# Permite `import omnicad` corriendo pytest desde cualquier carpeta.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Todas las pruebas corren sin ventanas. Va acá, ANTES de importar cualquier módulo: en Linux `omnicad.ui` elige con
# esto la API de contexto de PyOpenGL (GLX para offscreen) y algunos archivos de prueba importan la interfaz sin fijarlo.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
# El historial del Asistente (asistente/historial.py) nunca se escribe en la carpeta del usuario durante las pruebas.
os.environ.setdefault("OMNICAD_ASISTENTE_DIR", tempfile.mkdtemp(prefix="omnicad_chats_"))

if os.environ.get("OMNICAD_BLOQUEAR_OCP") == "1":
    from omnicad.bloqueo_ocp import activar
    activar()


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

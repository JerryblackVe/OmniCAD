# -*- coding: utf-8 -*-
"""
Arranque de la app: ícono de las ventanas y portada (pantalla de carga) mientras se importa lo pesado.

Como Fusion, que muestra su portada al abrir: `OmniCAD.py` la muestra apenas existe la QApplication, ANTES de importar
la ventana (OCP, OpenGL… casi 1 s), y la cierra cuando la ventana principal ya está a la vista.
"""
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QSplashScreen

from .. import NOMBRE_APP, RECURSOS

ANCHO_PORTADA = 768             # px lógicos (la imagen es de 1536: en pantallas 2x se ve nítida)
FRACCION_PANTALLA = 0.5         # y nunca más que la mitad del ancho de la pantalla


def poner_icono(app):
    """Ícono de todas las ventanas. En Windows además un AppUserModelID propio: sin él, la barra de tareas agrupa la
    ventana con python.exe y muestra el ícono de Python."""
    app.setWindowIcon(QIcon(str(RECURSOS / "omnicad.ico")))
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(f"{NOMBRE_APP}.{NOMBRE_APP}")
        except (AttributeError, OSError):
            pass


def mostrar_portada(app):
    """Muestra la portada centrada y la devuelve (para `finish`); None si no se pudo leer la imagen."""
    pm = QPixmap(str(RECURSOS / "portada.jpg"))
    if pm.isNull():
        return None
    pantalla = app.primaryScreen()
    dpr = pantalla.devicePixelRatio()
    ancho = min(ANCHO_PORTADA, int(pantalla.availableGeometry().width() * FRACCION_PANTALLA))
    pm = pm.scaledToWidth(int(ancho * dpr), Qt.SmoothTransformation)
    pm.setDevicePixelRatio(dpr)
    portada = QSplashScreen(pm)
    portada.show()
    app.processEvents()
    return portada

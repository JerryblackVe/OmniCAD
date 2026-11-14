# -*- coding: utf-8 -*-
"""
Arranque de la app: ícono de las ventanas y portada (pantalla de carga) mientras se importa lo pesado.

Como Fusion, que muestra su portada al abrir: `OmniCAD.py` la muestra apenas existe la QApplication, ANTES de importar
la ventana (kernel, OpenGL… casi 1 s), y la cierra cuando la ventana principal ya está a la vista.
"""
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QIcon, QImage, QPainter, QPixmap
from PySide6.QtWidgets import QSplashScreen

from .. import NOMBRE_APP, RECURSOS, VERSION

ANCHO_PORTADA = 768             # px lógicos (la imagen es de 1536: en pantallas 2x se ve nítida)
FRACCION_PANTALLA = 0.5         # y nunca más que la mitad del ancho de la pantalla
# La versión no va quemada en `portada.jpg`: se dibuja encima, en px de la imagen (1536 de ancho), a la izquierda del
# «| Open Source», con el color y el tamaño de ese texto. El ancho máximo (el de «0.1.0» original) deja libre la barra «|» (x = 365).
VERSION_X, VERSION_BASE, VERSION_ALTO_DIGITOS, VERSION_ANCHO_MAX = 269, 244, 28, 76
VERSION_COLOR = QColor(165, 194, 232)


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


def imagen_portada(version=VERSION):
    """La portada con `version` dibujada en su lugar (la imagen del disco no la trae); imagen nula si no se pudo leer."""
    img = QImage(str(RECURSOS / "portada.jpg"))
    if img.isNull():
        return img
    fuente = QFont()
    fuente.setFamilies(["Segoe UI", "Inter", "Noto Sans", "DejaVu Sans"])
    fuente.setPixelSize(round(VERSION_ALTO_DIGITOS / 0.72))      # los dígitos miden ~0,72 del cuerpo
    p = QPainter(img)
    p.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing)
    p.setFont(fuente)
    p.setPen(VERSION_COLOR)
    ancho = p.fontMetrics().horizontalAdvance(version)
    if ancho > VERSION_ANCHO_MAX:                                # versión larga («0.10.12»): achica en vez de pisar la barra
        fuente.setPixelSize(int(fuente.pixelSize() * VERSION_ANCHO_MAX / ancho))
        p.setFont(fuente)
    p.drawText(VERSION_X, VERSION_BASE, version)
    p.end()
    return img


def mostrar_portada(app):
    """Muestra la portada centrada y la devuelve (para `finish`); None si no se pudo leer la imagen."""
    pm = QPixmap.fromImage(imagen_portada())
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

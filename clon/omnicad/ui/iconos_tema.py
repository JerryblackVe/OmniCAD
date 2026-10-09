# -*- coding: utf-8 -*-
"""
Íconos sobre fondos oscuros.

Los íconos de `iconos.py` están dibujados con trazos gris oscuro (#4d4d4d, negro del marcador) pensados para la
cinta clara: sobre un tema oscuro casi no se ven. En vez de tocar el dibujo de cada ícono, acá se envuelve
`iconos.pixmap`: cuando el tema activo es oscuro, los píxeles gris oscuro sin color (ojo, flechas, reproducción,
marcador) pasan al color de texto del tema; los azules, naranjas y verdes quedan como están.

Limitación: los íconos se cachean y los widgets guardan su QIcon, así que se adaptan al tema con el que ARRANCA la
aplicación y se quedan así hasta reiniciar (todos igual, para que no se mezclen): al pasar de un tema claro a uno oscuro
(o al revés) con la aplicación abierta, el diálogo de Preferencias avisa que los íconos cambian al reiniciar.
Cuando los íconos pasen a ser sensibles al tema, este módulo sobra.
"""
import numpy as np
from PySide6.QtGui import QImage, QPixmap

from . import iconos, temas

SATURACION_MAX = 28     # un píxel «gris» tiene sus tres canales casi iguales
VALOR_MAX = 150         # y «oscuro» es menos que esto (los grises medios del dibujo se ven bien sobre el oscuro)
_original = None
_colores = None         # los colores del tema con el que se instaló (los íconos no cambian hasta reiniciar)


def tema_oscuro(colores=None):
    """True si el fondo del tema (barras y cinta) es oscuro."""
    return temas.luminancia((colores or temas.activo())["fondo"]) < 0.2


def adaptar(pm, colores=None):
    """Copia de `pm` con los píxeles gris oscuro cambiados por el color de texto del tema."""
    img = pm.toImage().convertToFormat(QImage.Format_ARGB32)
    ancho, alto = img.width(), img.height()
    px = np.frombuffer(img.constBits(), np.uint8).reshape(alto, ancho, 4).copy()      # B, G, R, A
    b, g, r = (px[..., i].astype(np.int16) for i in range(3))
    mayor, menor = np.maximum(np.maximum(r, g), b), np.minimum(np.minimum(r, g), b)
    gris_oscuro = (mayor - menor < SATURACION_MAX) & (mayor < VALOR_MAX) & (px[..., 3] > 0)
    luz = temas.rgb_f((colores or temas.activo())["texto"])
    px[gris_oscuro, 0], px[gris_oscuro, 1], px[gris_oscuro, 2] = (round(c * 255) for c in reversed(luz))
    salida = QPixmap.fromImage(QImage(px.tobytes(), ancho, alto, ancho * 4, QImage.Format_ARGB32).copy())
    salida.setDevicePixelRatio(pm.devicePixelRatio())
    return salida


def _pixmap(nombre, tam=32, escala=2):
    pm = _original(nombre, tam, escala)
    return adaptar(pm, _colores) if tema_oscuro(_colores) else pm


def instalar():
    """Envuelve `iconos.pixmap` (una sola vez, con el tema activo en ese momento)."""
    global _original, _colores
    if _original is None:
        _original, _colores = iconos.pixmap, dict(temas.activo())
        iconos.pixmap = _pixmap


def necesita_reiniciar(colores):
    """True si los íconos ya creados no combinan con el tema `colores` (uno claro frente a uno oscuro)."""
    return _colores is not None and tema_oscuro(_colores) != tema_oscuro(colores)

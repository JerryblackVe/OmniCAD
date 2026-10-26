# -*- coding: utf-8 -*-
"""
Íconos sobre fondos oscuros.

Los íconos de `iconos.py` están dibujados con trazos gris oscuro (#4d4d4d, negro del marcador) pensados para la
cinta clara: sobre un tema oscuro casi no se ven. En vez de tocar el dibujo de cada ícono, acá se envuelve
`iconos.pixmap`: cuando el tema activo es oscuro, los píxeles gris oscuro sin color (ojo, flechas, reproducción,
marcador) pasan al color de texto del tema; los azules, naranjas y verdes quedan como están.

Los íconos son `iconos.IconoVivo`: se dibujan al pedirlos, con el tema de ese momento. Al cambiar de tema solo hay que
vaciar su caché (`instalar` se engancha a `temas.observar`) y repintar: no hace falta reiniciar.
"""
import numpy as np
from PySide6.QtGui import QImage, QPixmap

from . import iconos, temas

SATURACION_MAX = 28     # un píxel «gris» tiene sus tres canales casi iguales
VALOR_MAX = 150         # y «oscuro» es menos que esto (los grises medios del dibujo se ven bien sobre el oscuro)
_original = None


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
    colores = temas.activo()
    return adaptar(pm, colores) if tema_oscuro(colores) else pm


def instalar():
    """Envuelve `iconos.pixmap` (una sola vez) y vacía la caché de íconos cada vez que cambia el tema."""
    global _original
    if _original is None:
        _original = iconos.pixmap
        iconos.pixmap = _pixmap
        temas.observar(iconos.vaciar_cache)

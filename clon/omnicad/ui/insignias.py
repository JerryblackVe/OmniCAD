# -*- coding: utf-8 -*-
"""
Insignias de los íconos (docs/plan_iconos.md): un disco chico en la esquina inferior derecha de la grilla 32×32, siempre
la misma, con un símbolo que NO depende del color (forma distinta para cada caso). En esa esquina no va nada más.

- Operación de un paso de cuerpo (`op.p["operacion"]`): nuevo `+` verde · unir `∪` azul · cortar `−` rojo · intersecar `∩` naranja.
- Estado de un paso (FeatureHealthStates de Fusion): aviso = triángulo ámbar con `!` · error = disco rojo con `!`.
  El estado manda sobre la operación (es lo que hay que mirar primero).
"""
from functools import lru_cache

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPolygonF

from . import iconos

CX, CY, R = 23.0, 23.0, 7.0                 # centro y radio del disco, en la grilla de 32
OPERACIONES = ("nuevo", "unir", "cortar", "intersecar")
COLOR_OPERACION = {"nuevo": QColor("#2fa84f"), "unir": QColor("#2b78c2"), "cortar": QColor("#d64545"),
                   "intersecar": QColor("#d9822b")}
BLANCO = QColor("#ffffff")


def _disco(p, color):
    p.setPen(QPen(BLANCO, 1.0))
    p.setBrush(color)
    p.drawEllipse(QPointF(CX, CY), R, R)


def _trazo(p, color=BLANCO, ancho=2.2):
    p.setPen(QPen(color, ancho, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.setBrush(Qt.NoBrush)


def _mas(p):
    _trazo(p)
    p.drawLine(QPointF(CX - 3.2, CY), QPointF(CX + 3.2, CY))
    p.drawLine(QPointF(CX, CY - 3.2), QPointF(CX, CY + 3.2))


def _menos(p):
    _trazo(p)
    p.drawLine(QPointF(CX - 3.4, CY), QPointF(CX + 3.4, CY))


def _arco(p, abajo):
    """∪ (`abajo`) o ∩: dos patas y un arco."""
    s = 1 if abajo else -1
    ruta = QPainterPath(QPointF(CX - 3.0, CY - 3.2 * s))
    ruta.lineTo(CX - 3.0, CY + 0.3 * s)
    ruta.arcTo(QRectF(CX - 3.0, CY - 2.7 if abajo else CY - 3.3, 6.0, 6.0), 180, 180 if abajo else -180)
    ruta.lineTo(CX + 3.0, CY - 3.2 * s)
    _trazo(p, ancho=2.0)
    p.drawPath(ruta)


def _exclamacion(p, color):
    _trazo(p, color, 2.0)
    p.drawLine(QPointF(CX, CY - 3.2), QPointF(CX, CY + 0.8))
    p.drawPoint(QPointF(CX, CY + 3.4))


def _aviso(p):
    p.setPen(QPen(BLANCO, 1.0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.setBrush(QColor("#f2b01e"))
    p.drawPolygon(QPolygonF([QPointF(CX, CY - R - 0.6), QPointF(CX + R + 0.8, CY + R - 0.6),
                             QPointF(CX - R - 0.8, CY + R - 0.6)]))
    _exclamacion(p, QColor("#3d2c00"))


def _error(p):
    _disco(p, QColor("#c62828"))
    _exclamacion(p, BLANCO)


def _de_operacion(nombre, glifo):
    def dibujar(p):
        _disco(p, COLOR_OPERACION[nombre])
        glifo(p)
    return dibujar


DIBUJOS_INSIGNIA = {
    "nuevo": _de_operacion("nuevo", _mas), "unir": _de_operacion("unir", lambda p: _arco(p, True)),
    "cortar": _de_operacion("cortar", _menos), "intersecar": _de_operacion("intersecar", lambda p: _arco(p, False)),
    "aviso": _aviso, "error": _error,
}


def insignia_de(op, estado):
    """Nombre de la insignia que lleva el paso `op` con ese estado (`Resultado.estado`), o None si no lleva."""
    if estado in ("aviso", "error"):
        return estado
    operacion = op.p.get("operacion")
    return operacion if operacion in OPERACIONES else None


def pixmap_con_insignia(nombre, insignia, tam=32, escala=2):
    """El dibujo `nombre` con la insignia encima (pasa por `iconos.pixmap`: respeta el tema oscuro)."""
    pm = iconos.pixmap(nombre, tam, escala)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.scale(tam / 32, tam / 32)
    DIBUJOS_INSIGNIA[insignia](p)
    p.end()
    return pm


@lru_cache(maxsize=None)
def icono_con_insignia(nombre, insignia):
    return QIcon(iconos.IconoVivo(("insignia", nombre, insignia),
                                  lambda lado: pixmap_con_insignia(nombre, insignia, lado, 1)))

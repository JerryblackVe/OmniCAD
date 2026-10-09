# -*- coding: utf-8 -*-
"""
Espacio de trabajo DIBUJO (Fusion › Drawing): ventana propia con su cinta (CREAR, MODIFICAR, GEOMETRÍA,
COTAS, TEXTO, TABLAS, EXPORTAR, HOJA), la hoja sobre un QGraphicsView y los comandos de vistas, cotas y
anotaciones. El modelo es `nucleo.dibujo.Dibujo`: esta ventana lo muestra y lo edita.

Punto de entrada para la ventana principal:
    ventana = VentanaDibujo(doc, parent)     # doc: timeline.documento.Documento
    ventana.desde_dict(datos)                # opcional: dibujo guardado con el documento
    ventana.show()
    datos = ventana.a_dict()                 # para persistirlo; la señal `cambiado` avisa cada edición
La ventana escucha al documento y recalcula sus vistas cuando el modelo cambia (`actualizar()`).

Ratón: rueda = zoom, botón del medio = encuadre, clic = seleccionar/arrastrar, doble clic = editar.
Regla de honestidad (como la cinta del diseño): lo que no está implementado aparece grisado.
"""
import json
import math
import os
import weakref

import numpy as np
from PySide6.QtCore import QMarginsF, QPointF, QRectF, QSize, QSizeF, Qt, QTimer, Signal
from PySide6.QtGui import (QAction, QColor, QFont, QFontMetricsF, QIcon, QKeySequence, QPageLayout,
                           QPageSize, QPainter, QPainterPath, QPdfWriter, QPen, QPixmap, QPolygonF)
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog,
                               QFormLayout, QFrame, QGraphicsItem, QGraphicsRectItem, QGraphicsScene,
                               QGraphicsView, QHBoxLayout, QInputDialog, QLineEdit, QListWidget, QListWidgetItem,
                               QMainWindow, QMenu, QMessageBox, QToolButton, QVBoxLayout, QWidget)

from .. import NOMBRE_APP, VERSION
from ..io_archivos import dxf
from ..nucleo import dibujo as nd
from ..nucleo.geometria import ErrorGeometria
from . import temas
from .cinta import ESPACIOS

FONDO_LIENZO = "#a3a3a3"
COLOR_PREVIA = QColor("#1f7fd0")
_PATRONES = {"trazos": (3.0, 1.5), "trazo_punto": (12.0, 3.0, 2.0, 3.0)}
_TEXTOS = {}      # texto → (ruta a 100 px, avance, altura de mayúscula)


# =============================================================== pintar primitivas de hoja
def _ruta_texto(texto):
    if texto not in _TEXTOS:
        fuente = QFont("Arial")
        fuente.setPixelSize(100)
        fm = QFontMetricsF(fuente)
        t = texto if fm.inFont("⌀") else texto.replace("⌀", "Ø")
        ruta = QPainterPath()
        ruta.addText(0, 0, fuente, t)
        _TEXTOS[texto] = (ruta, fm.horizontalAdvance(t), fm.capHeight() or 71.6)
    return _TEXTOS[texto]


class Pintura:
    """Primitivas de hoja (mm, y hacia arriba) convertidas a rutas de Qt en coordenadas de escena (y abajo)."""

    def __init__(self, primitivas):
        self.lineas, self.rellenos, self.textos = {}, {}, []
        self.primitivas = list(primitivas)
        self.cajas_texto = []      # esquinas (hoja) de cada texto, para elegirlo con el ratón
        xs, ys = [], []
        for capa, pr in primitivas:
            t = pr[0]
            if t == "texto":
                p, h, txt = pr[1], float(pr[2]), str(pr[3])
                rot = float(pr[4]) if len(pr) > 4 else 0.0
                alin = pr[5] if len(pr) > 5 else "izq"
                ruta, avance, cap = _ruta_texto(txt)
                k = h / cap
                ancho = avance * k
                dx = {"izq": 0.0, "centro": -ancho / 2, "der": -ancho}.get(alin, 0.0)
                self.textos.append((p[0], p[1], k, dx, rot, ruta))
                r = math.radians(rot)
                esquinas = [(p[0] + ex * math.cos(r) - ey * math.sin(r), p[1] + ex * math.sin(r) + ey * math.cos(r))
                            for ex, ey in ((dx, -0.3 * h), (dx + ancho, -0.3 * h), (dx + ancho, 1.3 * h),
                                           (dx, 1.3 * h))]
                self.cajas_texto.append(np.array(esquinas))
                xs += [q[0] for q in esquinas]
                ys += [q[1] for q in esquinas]
                continue
            if t == "solido":
                ruta = self.rellenos.setdefault(capa, QPainterPath())
                ruta.addPolygon(QPolygonF([QPointF(x, -y) for x, y in pr[1]]))
                ruta.closeSubpath()
                xs += [q[0] for q in pr[1]]
                ys += [q[1] for q in pr[1]]
                continue
            ruta = self.lineas.setdefault(capa, QPainterPath())
            if t == "linea":
                ruta.moveTo(pr[1][0], -pr[1][1])
                ruta.lineTo(pr[2][0], -pr[2][1])
                xs += [pr[1][0], pr[2][0]]
                ys += [pr[1][1], pr[2][1]]
            elif t in ("polilinea", "spline"):
                pts = pr[1]
                if len(pts) < 2:
                    continue
                ruta.moveTo(pts[0][0], -pts[0][1])
                for q in pts[1:]:
                    ruta.lineTo(q[0], -q[1])
                if len(pr) > 2 and bool(pr[2]):
                    ruta.closeSubpath()
                xs += [q[0] for q in pts]
                ys += [q[1] for q in pts]
            elif t == "circulo":
                c, r = pr[1], pr[2]
                ruta.addEllipse(QPointF(c[0], -c[1]), r, r)
                xs += [c[0] - r, c[0] + r]
                ys += [c[1] - r, c[1] + r]
            elif t == "arco":
                c, r, a0, a1 = pr[1], pr[2], pr[3], pr[4]
                caja = QRectF(c[0] - r, -c[1] - r, 2 * r, 2 * r)
                ruta.arcMoveTo(caja, math.degrees(a0))
                ruta.arcTo(caja, math.degrees(a0), math.degrees(a1 - a0))
                xs += [c[0] - r, c[0] + r]
                ys += [c[1] - r, c[1] + r]
        if xs:
            self.rect = QRectF(min(xs) - 1, -max(ys) - 1, max(xs) - min(xs) + 2, max(ys) - min(ys) + 2)
        else:
            self.rect = QRectF()

    def distancia(self, punto):
        """Distancia (mm de hoja) del punto al dibujo: trazos, arcos, sólidos o recuadros de texto."""
        q = np.asarray(punto, float)
        mejor = math.inf
        for caja in self.cajas_texto:       # dentro del recuadro (convexo) de un texto
            lados = np.roll(caja, -1, axis=0) - caja
            if np.all(lados[:, 0] * (q[1] - caja[:, 1]) - lados[:, 1] * (q[0] - caja[:, 0]) >= -1e-9):
                return 0.0
        for _, pr in self.primitivas:
            t = pr[0]
            if t in ("linea", "polilinea", "spline", "solido"):
                pts = np.array([pr[1], pr[2]] if t == "linea" else pr[1], float)
                if t == "solido" or (t == "polilinea" and len(pr) > 2 and pr[2]):
                    pts = np.vstack([pts, pts[:1]])
                a, b = pts[:-1], pts[1:]
                d = b - a
                largo2 = np.maximum((d * d).sum(1), 1e-18)
                s = np.clip(((q - a) * d).sum(1) / largo2, 0.0, 1.0)
                mejor = min(mejor, float(np.linalg.norm(q - (a + s[:, None] * d), axis=1).min()))
            elif t in ("circulo", "arco"):
                c, r = np.asarray(pr[1], float), float(pr[2])
                rel = q - c
                if t == "arco":
                    ang = (math.atan2(rel[1], rel[0]) - pr[3]) % (2 * math.pi)
                    if ang > pr[4] - pr[3]:
                        extremos = [c + r * np.array([math.cos(a_), math.sin(a_)]) for a_ in (pr[3], pr[4])]
                        mejor = min(mejor, *(float(np.linalg.norm(q - e)) for e in extremos))
                        continue
                mejor = min(mejor, abs(float(np.linalg.norm(rel)) - r))
        return mejor

    def pintar(self, p, color=None, pantalla=True):
        """Pinta con los grosores reales (mm). En pantalla, ninguna línea baja de un píxel."""
        escala = p.worldTransform().m11() if pantalla else 1.0
        minimo = 1.0 / escala if pantalla and escala > 0 else 0.0
        negro = QColor(color) if color is not None else QColor("#000000")
        p.setBrush(Qt.NoBrush)
        for capa, ruta in self.lineas.items():
            conf = nd.CAPAS.get(capa, {"grosor": 0.25, "tipo": "continua"})
            ancho = max(conf["grosor"], minimo)
            pluma = QPen(negro, ancho)
            pluma.setJoinStyle(Qt.RoundJoin)
            patron = _PATRONES.get(conf["tipo"])
            if patron:
                pluma.setCapStyle(Qt.FlatCap)
                pluma.setDashPattern([max(x / ancho, 0.5) for x in patron])
            else:
                pluma.setCapStyle(Qt.RoundCap)
            p.setPen(pluma)
            p.drawPath(ruta)
        p.setPen(Qt.NoPen)
        p.setBrush(negro)
        for ruta in self.rellenos.values():
            p.drawPath(ruta)
        for x, y, k, dx, rot, ruta in self.textos:
            p.save()
            p.translate(x, -y)
            p.rotate(-rot)
            p.translate(dx, 0)
            p.scale(k, k)
            p.drawPath(ruta)
            p.restore()
        p.setBrush(Qt.NoBrush)


class ItemElemento(QGraphicsItem):
    """Una vista, una anotación o la hoja (marco y cajetín) en la escena."""

    def __init__(self, clave, primitivas, seleccionable=True, color=None):
        super().__init__()
        self.clave = clave
        self.pintura = Pintura(primitivas)
        self.color = color
        self.setFlag(QGraphicsItem.ItemIsSelectable, seleccionable)

    def boundingRect(self):
        return self.pintura.rect

    def paint(self, p, opcion, widget=None):
        self.pintura.pintar(p, QColor(temas.color("acento")) if self.isSelected() else self.color)


# =============================================================== íconos propios de la cinta
_AZUL, _AZUL_CLARO, _AZUL_OSC = QColor("#4a9be0"), QColor("#9fcff5"), QColor("#1d5a94")
_GRIS, _ROJO, _VERDE = QColor("#4d4d4d"), QColor("#d64545"), QColor("#2fa84f")


def _pagina(p, x0=5.0, y0=3.0, x1=27.0, y1=29.0):
    p.setPen(QPen(QColor("#8a8a8a"), 1.0))
    p.setBrush(QColor("#ffffff"))
    p.drawRect(QRectF(x0, y0, x1 - x0, y1 - y0))


def _rect(p, x, y, w, h, relleno=_AZUL, borde=_AZUL_OSC):
    p.setPen(QPen(borde, 1.0))
    p.setBrush(relleno if relleno is not None else Qt.NoBrush)
    p.drawRect(QRectF(x, y, w, h))


def _trazo(p, color=_GRIS, ancho=1.4, estilo_linea=Qt.SolidLine):
    pluma = QPen(color, ancho, estilo_linea, Qt.RoundCap, Qt.RoundJoin)
    p.setPen(pluma)
    p.setBrush(Qt.NoBrush)


def _flecha_ico(p, x0, y0, x1, y1, color=_GRIS, ancho=1.4, punta=3.5):
    _trazo(p, color, ancho)
    p.drawLine(QPointF(x0, y0), QPointF(x1, y1))
    a = math.atan2(y1 - y0, x1 - x0)
    p.setPen(Qt.NoPen)
    p.setBrush(color)
    p.drawPolygon(QPolygonF([QPointF(x1 + math.cos(a), y1 + math.sin(a)),
                             QPointF(x1 - math.cos(a - 0.45) * punta, y1 - math.sin(a - 0.45) * punta),
                             QPointF(x1 - math.cos(a + 0.45) * punta, y1 - math.sin(a + 0.45) * punta)]))


def _letras(p, rect, texto, color=_GRIS, px=9, negrita=True):
    f = QFont("Segoe UI")
    f.setPixelSize(px)
    f.setBold(negrita)
    p.setFont(f)
    p.setPen(color)
    p.drawText(rect, Qt.AlignCenter, texto)


def _caja_iso(p, cx, cy, k=1.0):
    q = lambda x, y, z: QPointF(cx + (x - y) * 0.866 * k, cy + (x + y) * 0.5 * k - z * k)  # noqa: E731
    for pts, color in (([q(0, 6, 0), q(6, 6, 0), q(6, 6, 6), q(0, 6, 6)], _AZUL),
                       ([q(6, 0, 0), q(6, 6, 0), q(6, 6, 6), q(6, 0, 6)], QColor("#2b78c2")),
                       ([q(0, 0, 6), q(6, 0, 6), q(6, 6, 6), q(0, 6, 6)], _AZUL_CLARO)):
        p.setPen(QPen(_AZUL_OSC, 0.9))
        p.setBrush(color)
        p.drawPolygon(QPolygonF(pts))


def _i_vista_base(p):
    _pagina(p)
    _caja_iso(p, 16, 14, 1.3)


def _i_vista_proyectada(p):
    _pagina(p)
    _rect(p, 8, 16, 8, 9)
    _rect(p, 19, 16, 6, 9, None, _AZUL_OSC)
    _flecha_ico(p, 13, 11, 22, 11, _VERDE)


def _i_vista_seccion(p):
    _pagina(p)
    _rect(p, 9, 9, 14, 14, QColor("#dbe9f6"))
    p.save()
    p.setClipRect(QRectF(9, 9, 14, 14))
    _trazo(p, _AZUL_OSC, 0.8)
    for k in range(-14, 16, 3):
        p.drawLine(QPointF(9 + k, 23), QPointF(23 + k, 9))
    p.restore()
    _trazo(p, _ROJO, 1.2, Qt.DashDotLine)
    p.drawLine(QPointF(16, 5), QPointF(16, 27))


def _i_vista_detalle(p):
    _pagina(p)
    _rect(p, 8, 18, 9, 8)
    _trazo(p, _ROJO, 1.2)
    p.drawEllipse(QPointF(15, 19), 4, 4)
    _trazo(p, _AZUL_OSC, 1.4)
    p.drawEllipse(QPointF(21, 11), 6, 6)


def _i_mover(p):
    for x0, y0, x1, y1 in ((16, 16, 16, 4), (16, 16, 16, 28), (16, 16, 4, 16), (16, 16, 28, 16)):
        _flecha_ico(p, x0, y0, x1, y1, _GRIS, 1.6)


def _i_borrar(p):
    _trazo(p, _ROJO, 3.0)
    p.drawLine(QPointF(8, 8), QPointF(24, 24))
    p.drawLine(QPointF(24, 8), QPointF(8, 24))


def _i_girar(p):
    _rect(p, 11, 11, 10, 10)
    _trazo(p, _GRIS, 1.6)
    p.drawArc(QRectF(5, 5, 22, 22), 30 * 16, 260 * 16)
    _flecha_ico(p, 24, 9, 26.5, 12.5, _GRIS, 1.6)


def _i_linea_centro(p):
    _trazo(p, _AZUL_OSC, 1.3)
    p.drawEllipse(QPointF(8, 16), 4, 4)
    p.drawEllipse(QPointF(24, 16), 4, 4)
    _trazo(p, _ROJO, 1.3, Qt.DashDotLine)
    p.drawLine(QPointF(2, 16), QPointF(30, 16))


def _i_marca_centro(p):
    _trazo(p, _AZUL_OSC, 1.6)
    p.drawEllipse(QPointF(16, 16), 8, 8)
    _trazo(p, _ROJO, 1.3, Qt.DashDotLine)
    p.drawLine(QPointF(4, 16), QPointF(28, 16))
    p.drawLine(QPointF(16, 4), QPointF(16, 28))


def _cota_horizontal(p, y=12, texto="12"):
    _trazo(p, _GRIS, 1.0)
    p.drawLine(QPointF(5, 26), QPointF(5, y - 3))
    p.drawLine(QPointF(27, 26), QPointF(27, y - 3))
    _flecha_ico(p, 16, y, 5.5, y, _GRIS, 1.0, 3.0)
    _flecha_ico(p, 16, y, 26.5, y, _GRIS, 1.0, 3.0)
    _letras(p, QRectF(6, y - 10, 20, 9), texto, _AZUL_OSC, 9)
    _rect(p, 5, 22, 22, 4)


def _i_cota(p):
    _cota_horizontal(p)


def _i_cota_alineada(p):
    _rect(p, 6, 16, 16, 10)
    _trazo(p, _GRIS, 1.0)
    _flecha_ico(p, 15, 6, 4, 12, _GRIS, 1.0, 3.0)
    _flecha_ico(p, 15, 6, 26, 0.5, _GRIS, 1.0, 3.0)


def _i_cota_ordenadas(p):
    _rect(p, 5, 20, 22, 7)
    for x, t in ((6, "0"), (16, "8"), (26, "16")):
        _trazo(p, _GRIS, 1.0)
        p.drawLine(QPointF(x, 19), QPointF(x, 10))
        _letras(p, QRectF(x - 5, 1, 10, 9), t, _AZUL_OSC, 8)


def _i_cota_radial(p):
    _trazo(p, _AZUL_OSC, 1.6)
    p.drawEllipse(QPointF(14, 18), 10, 10)
    _flecha_ico(p, 14, 18, 21, 11, _GRIS, 1.2, 3.0)
    _letras(p, QRectF(18, 0, 14, 11), "R", _AZUL_OSC, 10)


def _i_cota_diametro(p):
    _trazo(p, _AZUL_OSC, 1.6)
    p.drawEllipse(QPointF(14, 18), 10, 10)
    _flecha_ico(p, 14, 18, 7, 25, _GRIS, 1.2, 3.0)
    _flecha_ico(p, 14, 18, 21, 11, _GRIS, 1.2, 3.0)
    _letras(p, QRectF(18, 0, 14, 11), "Ø", _AZUL_OSC, 10)


def _i_cota_angular(p):
    _trazo(p, _AZUL_OSC, 1.8)
    p.drawLine(QPointF(4, 27), QPointF(28, 27))
    p.drawLine(QPointF(4, 27), QPointF(22, 6))
    _trazo(p, _GRIS, 1.0)
    p.drawArc(QRectF(-10, 13, 28, 28), 0, 50 * 16)
    _letras(p, QRectF(16, 12, 14, 12), "°", _AZUL_OSC, 12)


def _i_texto(p):
    _letras(p, QRectF(0, 0, 32, 32), "A", _GRIS, 24, False)


def _i_nota(p):
    _flecha_ico(p, 18, 12, 6, 26, _GRIS, 1.2, 3.5)
    _trazo(p, _GRIS, 1.2)
    p.drawLine(QPointF(18, 12), QPointF(22, 12))
    _trazo(p, _AZUL_OSC, 1.6)
    p.drawLine(QPointF(23, 9), QPointF(30, 9))
    p.drawLine(QPointF(23, 14), QPointF(29, 14))


def _i_tabla(p):
    _rect(p, 4, 7, 24, 18, QColor("#ffffff"), _GRIS)
    p.fillRect(QRectF(4.5, 7.5, 23, 5), _AZUL_CLARO)
    _trazo(p, _GRIS, 0.9)
    for y in (13, 19):
        p.drawLine(QPointF(4, y), QPointF(28, y))
    for x in (10, 18):
        p.drawLine(QPointF(x, 7), QPointF(x, 25))


def _i_globo(p):
    _trazo(p, _GRIS, 1.1)
    p.drawLine(QPointF(18, 16), QPointF(6, 27))
    _trazo(p, _AZUL_OSC, 1.6)
    p.setBrush(QColor("#ffffff"))
    p.drawEllipse(QPointF(21, 11), 8, 8)
    _letras(p, QRectF(13, 3, 16, 16), "1", _AZUL_OSC, 11)


def _i_exportar(p, texto, color):
    _pagina(p, 6, 2, 26, 30)
    p.fillRect(QRectF(3, 17, 26, 10), color)
    _letras(p, QRectF(3, 17, 26, 10), texto, QColor("#ffffff"), 8)


def _i_hoja(p):
    _pagina(p, 3, 6, 29, 26)
    _trazo(p, _GRIS, 0.9)
    p.drawRect(QRectF(5, 8, 22, 16))
    p.fillRect(QRectF(16, 19, 11, 5), _AZUL_CLARO)
    p.drawRect(QRectF(16, 19, 11, 5))


_DIBUJOS_ICONO = {
    "vista_base": _i_vista_base, "vista_proyectada": _i_vista_proyectada, "vista_seccion": _i_vista_seccion,
    "vista_detalle": _i_vista_detalle, "mover": _i_mover, "borrar": _i_borrar, "girar": _i_girar,
    "linea_centro": _i_linea_centro, "marca_centro": _i_marca_centro, "cota": _i_cota,
    "cota_lineal": _i_cota, "cota_alineada": _i_cota_alineada, "cota_ordenadas": _i_cota_ordenadas,
    "cota_radial": _i_cota_radial, "cota_radio": _i_cota_radial, "cota_diametro": _i_cota_diametro,
    "cota_angular": _i_cota_angular, "texto": _i_texto, "nota": _i_nota, "tabla": _i_tabla, "globo": _i_globo,
    "exportar_pdf": lambda p: _i_exportar(p, "PDF", _ROJO), "exportar_dxf": lambda p: _i_exportar(p, "DXF", _AZUL),
    "hoja": _i_hoja,
}
_ICONOS = {}


def icono_dibujo(nombre):
    """Ícono propio (QPainter, grilla 32×32) de un comando de dibujo; vacío si no existe."""
    if nombre not in _ICONOS:
        ico = QIcon()
        for escala in (1, 2):
            pm = QPixmap(32 * escala, 32 * escala)
            pm.setDevicePixelRatio(escala)
            pm.fill(Qt.transparent)
            funcion = _DIBUJOS_ICONO.get(nombre)
            if funcion:
                p = QPainter(pm)
                p.setRenderHint(QPainter.Antialiasing)
                funcion(p)
                p.end()
            ico.addPixmap(pm)
        _ICONOS[nombre] = ico
    return _ICONOS[nombre]


# =============================================================== cinta del espacio DIBUJO
SEP = "-"
GRUPOS = [  # (título, botones rápidos, menú); un ítem ("texto",) es un comando no implementado (grisado)
    ("CREAR", ["vista_base", "vista_proyectada", "vista_seccion", "vista_detalle"],
     ["vista_base", "vista_proyectada", "vista_seccion", "vista_detalle", SEP,
      ("Vista de rotura",), ("Vista de sección parcial",), ("Vista recortada",), ("Crear boceto",)]),
    ("MODIFICAR", ["mover", "borrar"], ["mover", "girar", "borrar"]),
    ("GEOMETRÍA", ["linea_centro", "marca_centro"],
     ["linea_centro", "marca_centro", SEP, ("Patrón de marcas de centro",), ("Extensión de arista",)]),
    ("COTAS", ["cota", "cota_ordenadas", "cota_radial", "cota_angular"],
     ["cota", "cota_ordenadas", "cota_lineal", "cota_alineada", "cota_angular", "cota_radio", "cota_diametro",
      SEP, ("Cota de línea base",), ("Cota en cadena",), ("Corte de cota",)]),
    ("TEXTO", ["texto", "nota"], ["texto", "nota"]),
    ("TABLAS", ["tabla", "globo"], ["tabla", "globo", SEP, ("Renumerar",)]),
    ("EXPORTAR", ["exportar_pdf", "exportar_dxf"],
     ["exportar_pdf", "exportar_dxf", SEP, ("Exportar DWG",), ("Exportar CSV",)]),
    ("HOJA", ["hoja"], ["hoja"]),
]


class CintaDibujo(QWidget):
    """Cinta del espacio DIBUJO con el aspecto de la del diseño (ui/cinta.py)."""
    ir_a_diseno = Signal()

    def __init__(self, acciones, parent=None):
        super().__init__(parent)
        self.setObjectName("cinta")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.acciones = acciones
        self.no_disponibles = []
        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 2, 8, 0)
        lay.setSpacing(10)
        self.espacio = QToolButton(objectName="espacio_trabajo", text="DIBUJO  ▾")
        self.espacio.setFixedSize(108, 62)
        self.espacio.setPopupMode(QToolButton.InstantPopup)
        menu = QMenu(self.espacio)
        for nombre in ESPACIOS:
            a = menu.addAction(nombre)
            if nombre == "DIBUJO":
                a.setCheckable(True)
                a.setChecked(True)
            elif nombre == "DISEÑO":
                a.triggered.connect(self.ir_a_diseno.emit)
            else:
                a.setEnabled(False)
        self.espacio.setMenu(menu)
        lay.addWidget(self.espacio, 0, Qt.AlignVCenter)
        derecha = QVBoxLayout()
        derecha.setSpacing(0)
        fila = QHBoxLayout()
        fila.setSpacing(6)
        pestana = QToolButton(objectName="pestana", text="DIBUJO", checkable=True)
        pestana.setChecked(True)
        fila.addWidget(pestana)
        fila.addStretch(1)
        derecha.addLayout(fila)
        grupos = QHBoxLayout()
        grupos.setContentsMargins(0, 0, 0, 0)
        grupos.setSpacing(4)
        for n, (titulo, rapidos, items) in enumerate(GRUPOS):
            if n:
                sep = QFrame(objectName="separador_grupo")
                sep.setFixedWidth(1)
                grupos.addWidget(sep)
            grupos.addWidget(self._grupo(titulo, rapidos, items))
        grupos.addStretch(1)
        derecha.addLayout(grupos)
        lay.addLayout(derecha, 1)

    def _accion(self, ref):
        if isinstance(ref, str):
            return self.acciones[ref]
        a = QAction(ref[0], self)
        a.setEnabled(False)
        a.setToolTip(f"<b>{ref[0]}</b><br>No disponible en {NOMBRE_APP} {VERSION}.")
        self.no_disponibles.append(a)
        return a

    def _grupo(self, titulo, rapidos, items):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(2, 2, 2, 0)
        v.setSpacing(0)
        botones = QHBoxLayout()
        botones.setSpacing(2)
        for clave in rapidos:
            b = QToolButton()
            b.setDefaultAction(self.acciones[clave])
            b.setIconSize(QSize(30, 30))
            b.setFixedSize(38, 38)
            b.setToolButtonStyle(Qt.ToolButtonIconOnly)
            botones.addWidget(b)
        v.addLayout(botones)
        t = QToolButton(objectName="titulo_grupo", text=f"{titulo} ▾")
        t.setPopupMode(QToolButton.InstantPopup)
        m = QMenu(t)
        m.setToolTipsVisible(True)
        for it in items:
            if it == SEP:
                m.addSeparator()
            else:
                m.addAction(self._accion(it))
        t.setMenu(m)
        v.addWidget(t, 0, Qt.AlignHCenter)
        return w


# =============================================================== vista de la hoja (zoom y encuadre)
class VistaHoja(QGraphicsView):
    """QGraphicsView de la hoja: rueda = zoom bajo el cursor, botón del medio = encuadre. Los clics se pasan a
    la herramienta activa en coordenadas de hoja (mm, y hacia arriba)."""

    def __init__(self, ventana):
        super().__init__(ventana.escena, ventana)
        self.v = ventana
        self.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing)
        self.setBackgroundBrush(QColor(FONDO_LIENZO))
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setMouseTracking(True)
        self.setFrameShape(QFrame.NoFrame)
        self._paneo = None

    def a_hoja(self, pos):
        s = self.mapToScene(pos.toPoint())
        return np.array([s.x(), -s.y()])

    def tolerancia(self, px=9.0):
        """Tolerancia de enganche en mm de hoja equivalente a `px` píxeles de pantalla."""
        return px / max(self.transform().m11(), 1e-9)

    def ajustar(self):
        r = QRectF(0, -self.v.dibujo.alto, self.v.dibujo.ancho, self.v.dibujo.alto)
        self.fitInView(r.adjusted(-12, -12, 12, 12), Qt.KeepAspectRatio)

    def wheelEvent(self, e):
        f = 1.2 ** (e.angleDelta().y() / 120.0)
        actual = self.transform().m11()
        if 0.05 < actual * f < 400:
            self.scale(f, f)

    def mousePressEvent(self, e):
        if e.button() == Qt.MiddleButton:
            self._paneo = e.position()
            self.viewport().setCursor(Qt.ClosedHandCursor)
            return
        if e.button() == Qt.RightButton:
            self.v.terminar_herramienta()
            return
        if e.button() == Qt.LeftButton:
            self.v.herramienta.clic(self.a_hoja(e.position()), e)

    def mouseMoveEvent(self, e):
        if self._paneo is not None:
            d = e.position() - self._paneo
            self._paneo = e.position()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - int(round(d.x())))
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - int(round(d.y())))
            return
        self.v.herramienta.mover(self.a_hoja(e.position()), e)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MiddleButton:
            self._paneo = None
            self.viewport().unsetCursor()
            return
        if e.button() == Qt.LeftButton:
            self.v.herramienta.soltar(self.a_hoja(e.position()), e)

    def mouseDoubleClickEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.v.herramienta.doble_clic(self.a_hoja(e.position()), e)


# =============================================================== herramientas (comandos interactivos)
class Herramienta:
    indicacion = ""

    def __init__(self, ventana):
        self.v = ventana

    @property
    def d(self):
        return self.v.dibujo

    def iniciar(self):
        self.v.indicar(self.indicacion)

    def clic(self, p, e):
        pass

    def mover(self, p, e):
        pass

    def soltar(self, p, e):
        pass

    def doble_clic(self, p, e):
        pass

    def terminar(self):
        """Se llama al cambiar de herramienta (Esc, clic derecho u otro comando)."""
        self.v.previa([])


class HerrSeleccion(Herramienta):
    indicacion = "Clic para seleccionar; arrastrar para mover; doble clic para editar."

    def __init__(self, ventana, indicacion=None):
        super().__init__(ventana)
        self.arrastre = None
        if indicacion:
            self.indicacion = indicacion

    def clic(self, p, e):
        item = self.v.item_en(p)
        ctrl = bool(e.modifiers() & Qt.ControlModifier) if e is not None else False
        if item is None:
            if not ctrl:
                self.v.escena.clearSelection()
            self.arrastre = None
            return
        if ctrl:
            item.setSelected(not item.isSelected())
            return
        if not item.isSelected():
            self.v.escena.clearSelection()
            item.setSelected(True)
        self.arrastre = [item, p, np.zeros(2)]

    def mover(self, p, e):
        if not self.arrastre or (e is not None and not (e.buttons() & Qt.LeftButton)):
            return
        item, inicio, _ = self.arrastre
        delta = self.d.restringir_movimiento(item.clave, p - inicio)
        item.setPos(delta[0], -delta[1])
        self.arrastre[2] = delta

    def soltar(self, p, e):
        if not self.arrastre:
            return
        item, _, delta = self.arrastre
        self.arrastre = None
        if np.linalg.norm(delta) > 1e-9:
            self.v.modificar(lambda: self.d.mover(item.clave, delta))

    def doble_clic(self, p, e):
        item = self.v.item_en(p)
        if item is not None:
            self.v.editar_elemento(item.clave)
            return
        x0, y0, x1, y1 = nd.caja_cajetin(self.d.ancho, self.d.alto)
        if x0 <= p[0] <= x1 and y0 <= p[1] <= y1:
            self.v.editar_hoja()


class _ConVistaTemporal(Herramienta):
    """Herramientas que muestran la vista nueva pegada al cursor antes de colocarla (como Fusion)."""

    def __init__(self, ventana):
        super().__init__(ventana)
        self.temp = None
        self.antes = None
        self.base = None

    def _crear_temp(self, fabrica):
        if self.antes is None:
            self.antes = self.v.instantanea()
        self._quitar_temp()
        try:
            self.temp = fabrica()
        except ErrorGeometria as e:
            self.v.indicar(str(e))
            self.temp = None
            return
        self.base = self.temp.posicion.copy()
        self.v.redibujar()

    def _quitar_temp(self):
        if self.temp is not None:
            self.d.borrar(self.temp.id)
            self.temp = None
            self.v.redibujar()

    def _seguir(self, p):
        """Mueve la vista temporal con el cursor (sin recalcular: solo corre el ítem)."""
        item = self.v.items.get(self.temp.id) if self.temp else None
        if item is not None:
            delta = self.d.restringir_movimiento(self.temp.id, p - self.base)
            item.setPos(delta[0], -delta[1])
            return delta
        return np.zeros(2)

    def _confirmar(self, p):
        delta = self.d.restringir_movimiento(self.temp.id, p - self.base)
        self.d.mover(self.temp.id, delta)
        self.v.apilar_deshacer(self.antes)
        self.temp, self.antes = None, None
        self.v.redibujar()
        self.v.cambiado.emit()

    def terminar(self):
        self._quitar_temp()
        self.antes = None
        super().terminar()


class HerrVistaBase(_ConVistaTemporal):
    indicacion = "Clic en la hoja para colocar la vista base."

    def iniciar(self):
        cuerpos = self.v.cuerpos_disponibles()
        if not cuerpos:
            self.v.aviso("El diseño no tiene cuerpos para dibujar.")
            self.v.usar_seleccion()
            return
        dlg = DialogoVista(self.v, cuerpos=cuerpos)
        if dlg.exec() != QDialog.Accepted:
            self.v.usar_seleccion()
            return
        datos = dlg.valores()
        self._crear_temp(lambda: self.d.agregar_vista_base(**datos))
        super().iniciar()

    def mover(self, p, e):
        self._seguir(p)

    def clic(self, p, e):
        if self.temp is not None:
            self._confirmar(p)
            self.v.usar_seleccion()


class _ConPadre(_ConVistaTemporal):
    """Primero se elige la vista padre (o se usa la seleccionada)."""
    pedir_padre = "Clic en la vista padre."

    def iniciar(self):
        self.padre = self.v.vista_seleccionada()
        self.v.indicar(self.indicacion if self.padre else self.pedir_padre)

    def elegir_padre(self, p):
        vid = self.d.vista_en(p)
        if vid is None:
            return False
        self.padre = vid
        self.v.escena.clearSelection()
        self.v.indicar(self.indicacion)
        return True


class HerrProyectada(_ConPadre):
    indicacion = "Mové el cursor alrededor de la vista padre y hacé clic para colocar (Esc o clic derecho termina)."

    def iniciar(self):
        self.direccion = None
        super().iniciar()

    def mover(self, p, e):
        if not self.padre:
            return
        padre = self.d.vista(self.padre)
        dx, dy = (p - padre.posicion) @ padre._rot()
        if abs(dx) < 1e-6 and abs(dy) < 1e-6:
            return
        direccion = nd.direccion_proyectada(dx, dy)
        if direccion != self.direccion or self.temp is None:
            self.direccion = direccion
            self._crear_temp(lambda: self.d.agregar_vista_proyectada(self.padre, p))
        self._seguir(p)

    def clic(self, p, e):
        if not self.padre:
            self.elegir_padre(p)
            return
        if self.temp is not None:
            self._confirmar(p)
            self.direccion = None


class HerrSeccion(_ConPadre):
    indicacion = "Clic en el primer punto de la línea de corte."

    def iniciar(self):
        self.p1 = self.p2 = None
        self.lado = 0
        super().iniciar()

    def _punto(self, p):
        k = self.v.punto_cercano(p)
        return k[2] if k else p

    def _orto(self, p):
        """Línea de corte horizontal o vertical cuando está a menos de 4° de serlo."""
        d = p - self.p1
        if np.linalg.norm(d) < 1e-9:
            return p
        ang = math.degrees(math.atan2(d[1], d[0])) % 180.0
        if ang < 4 or ang > 176:
            return np.array([p[0], self.p1[1]])
        if abs(ang - 90.0) < 4:
            return np.array([self.p1[0], p[1]])
        return p

    def clic(self, p, e):
        if not self.padre:
            self.elegir_padre(p)
            return
        if self.p1 is None:
            self.p1 = self._punto(p)
            self.v.indicar("Clic en el segundo punto de la línea de corte.")
        elif self.p2 is None:
            q = self._orto(self._punto(p))
            if np.linalg.norm(q - self.p1) < 1e-6:
                return
            self.p2 = q
            self.v.previa([])
            self.v.indicar("Mové el cursor hacia el lado desde donde se mira y hacé clic para colocar la sección.")
        elif self.temp is not None:
            self._confirmar(p)
            self.v.usar_seleccion()

    def mover(self, p, e):
        if not self.padre:
            return
        if self.p2 is None:
            k = self.v.punto_cercano(p)
            if self.p1 is None:
                self.v.previa([], k[2] if k else None)
            else:
                q = self._orto(k[2] if k else p)
                self.v.previa([("SECCION", ("linea", tuple(self.p1), tuple(q)))], k[2] if k else None)
            return
        t = self.p2 - self.p1
        rel = p - self.p1
        lado = 1 if t[0] * rel[1] - t[1] * rel[0] >= 0 else -1
        if lado != self.lado or self.temp is None:
            self.lado = lado
            self._crear_temp(lambda: self.d.agregar_vista_seccion(self.padre, self.p1, self.p2, p))
        self._seguir(p)


class HerrDetalle(_ConPadre):
    indicacion = "Clic en el centro del círculo de detalle."

    def iniciar(self):
        self.centro = None
        self.radio = None
        super().iniciar()

    def clic(self, p, e):
        if not self.padre:
            self.elegir_padre(p)
            return
        if self.centro is None:
            k = self.v.punto_cercano(p)
            self.centro = k[2] if k else p
            self.v.indicar("Clic para fijar el radio del círculo de detalle.")
        elif self.radio is None:
            r = float(np.linalg.norm(p - self.centro))
            if r < 1e-3:
                return
            self.radio = r
            self.v.previa([])
            self.v.indicar("Clic para colocar la vista de detalle.")
        elif self.temp is not None:
            self._confirmar(p)
            self.v.usar_seleccion()

    def mover(self, p, e):
        if not self.padre:
            return
        if self.centro is None:
            k = self.v.punto_cercano(p)
            self.v.previa([], k[2] if k else None)
        elif self.radio is None:
            r = float(np.linalg.norm(p - self.centro))
            if r > 1e-3:
                self.v.previa([("CONTORNO", ("circulo", tuple(self.centro), r))])
        else:
            if self.temp is None:
                self._crear_temp(lambda: self.d.agregar_vista_detalle(self.padre, self.centro, self.radio, p))
            self._seguir(p)


class HerrCota(Herramienta):
    """Cota (Dimension): punto-punto, arista recta, dos aristas (ángulo) o circunferencia (radio/diámetro).
    `modo` = "lineal" (horizontal o vertical, Linear Dimension), "alineada" (Aligned Dimension),
    "horizontal" o "vertical"; sin modo se deduce de dónde se coloca."""
    indicacion = "Elegí un punto, una arista o una circunferencia de una vista."

    def __init__(self, ventana, modo=None):
        super().__init__(ventana)
        self.modo = modo
        self._reiniciar()

    def _reiniciar(self):
        self.estado = "inicio"
        self.vista_id = None
        self.p1 = self.p2 = None
        self.seg = self.seg2 = None
        self.circulo = None

    def iniciar(self):
        self._reiniciar()
        super().iniciar()

    def _seg_hoja(self, s):
        v = self.d.vista(s[0])
        return tuple(v.a_hoja([s[1], s[2]]))

    def _tipo_lineal(self, a, b, lugar):
        (x0, x1), (y0, y1) = sorted((a[0], b[0])), sorted((a[1], b[1]))
        fuera_y = lugar[1] > y1 or lugar[1] < y0
        fuera_x = lugar[0] > x1 or lugar[0] < x0
        if self.modo == "lineal":       # Linear Dimension: horizontal o vertical según el cursor
            return "vertical" if fuera_x and not fuera_y else "horizontal"
        if self.modo:
            return self.modo
        if fuera_y and not fuera_x:
            return "horizontal"
        if fuera_x and not fuera_y:
            return "vertical"
        if abs(b[0] - a[0]) < 1e-6:
            return "vertical"
        if abs(b[1] - a[1]) < 1e-6:
            return "horizontal"
        return "alineada"

    def _temporal(self, tipo, puntos, lugar, **extra):
        v = self.d.vista(self.vista_id)
        a = {"tipo": "cota", "subtipo": tipo, "vista": self.vista_id, "puntos": v.de_hoja(puntos).tolist(),
             "lugar": v.de_hoja([lugar])[0].tolist(), "texto": None}
        if "radio" in extra:
            a["radio"] = extra["radio"] / v.escala
        try:
            return self.d.primitivas_anotacion(a)
        except ErrorGeometria:
            return []

    def _plan(self, p):
        """(tipo, puntos, extra) de la cota que se crearía con el cursor en p."""
        if self.estado == "colocar_lineal" or (self.estado == "segmento" and self.seg2 is None):
            a, b = (self.p1, self.p2) if self.estado == "colocar_lineal" else self.seg
            return self._tipo_lineal(a, b, p), [a, b], {}
        if self.estado == "colocar_angular":
            return "angulo", [*self.seg, *self.seg2], {}
        if self.estado == "radial":
            vid, c, r, completo = self.circulo
            v = self.d.vista(vid)
            tipo = self.modo_radial or ("diametro" if completo else "radio")
            return tipo, [v.a_hoja(c)], {"radio": r * v.escala}
        return None

    modo_radial = None

    def mover(self, p, e):
        k = None
        if self.estado in ("inicio", "punto"):
            k = self.v.punto_cercano(p)
            if self.estado == "punto" and k and k[0] != self.vista_id:
                k = None
        plan = self._plan(p)
        prims = self._temporal(plan[0], plan[1], p, **plan[2]) if plan else []
        self.v.previa(prims, k[2] if k else None)

    def clic(self, p, e):
        tol = self.v.vista.tolerancia()
        if self.estado == "inicio":
            k = self.v.punto_cercano(p) if self.modo_radial is None else None
            if k:
                self.vista_id, self.p1, self.estado = k[0], k[2], "punto"
                self.v.indicar("Elegí el segundo punto.")
                return
            if self.modo is None:
                c = self.d.circulo_cercano(p, tol)
                if c:
                    self.vista_id, self.circulo, self.estado = c[0], c, "radial"
                    self.v.indicar("Clic para colocar la cota.")
                    return
            if self.modo_radial is None:
                s = self.d.segmento_cercano(p, tol)
                if s:
                    self.vista_id, self.seg, self.estado = s[0], self._seg_hoja(s), "segmento"
                    self.v.indicar("Clic para colocar la cota, o elegí otra arista para un ángulo.")
            return
        if self.estado == "punto":
            k = self.v.punto_cercano(p)
            if k and k[0] == self.vista_id and np.linalg.norm(k[2] - self.p1) > 1e-6:
                self.p2, self.estado = k[2], "colocar_lineal"
                self.v.indicar("Clic para colocar la cota.")
            return
        if self.estado == "segmento" and self.modo is None:
            s = self.d.segmento_cercano(p, tol)
            if s and s[0] == self.vista_id:
                seg2 = self._seg_hoja(s)
                if np.linalg.norm(np.subtract(seg2, self.seg)) > 1e-6:
                    self.seg2, self.estado = seg2, "colocar_angular"
                    self.v.indicar("Clic para colocar la cota angular.")
                    return
        plan = self._plan(p)
        if plan is None:
            return
        tipo, puntos, extra = plan
        self.v.modificar(lambda: self.d.agregar_cota(tipo, self.vista_id, puntos, p, **extra))
        self._reiniciar()
        self.v.indicar(self.indicacion)


class HerrCotaRadial(HerrCota):
    indicacion = "Elegí una circunferencia o un arco de una vista."

    def __init__(self, ventana, modo_radial=None):
        super().__init__(ventana, None)
        self.modo_radial = modo_radial

    def clic(self, p, e):
        if self.estado == "inicio":
            c = self.d.circulo_cercano(p, self.v.vista.tolerancia())
            if c:
                self.vista_id, self.circulo, self.estado = c[0], c, "radial"
                self.v.indicar("Clic para colocar la cota.")
            return
        super().clic(p, e)


class HerrCotaAngular(HerrCota):
    indicacion = "Elegí la primera arista recta."

    def clic(self, p, e):
        tol = self.v.vista.tolerancia()
        if self.estado == "inicio":
            s = self.d.segmento_cercano(p, tol)
            if s:
                self.vista_id, self.seg, self.estado = s[0], self._seg_hoja(s), "segmento"
                self.v.indicar("Elegí la segunda arista.")
            return
        if self.estado == "segmento":
            s = self.d.segmento_cercano(p, tol)
            if s and s[0] == self.vista_id:
                seg2 = self._seg_hoja(s)
                if np.linalg.norm(np.subtract(seg2, self.seg)) > 1e-6:
                    self.seg2, self.estado = seg2, "colocar_angular"
                    self.v.indicar("Clic para colocar la cota angular.")
            return
        super().clic(p, e)

    def mover(self, p, e):
        if self.estado == "segmento":
            self.v.previa([])
            return
        super().mover(p, e)


class HerrOrdenadas(Herramienta):
    indicacion = "Clic en el punto de origen (0, 0) de las cotas de ordenadas."

    def iniciar(self):
        self.origen = self.punto = self.vista_id = None
        super().iniciar()

    def _tipo(self, p):
        d = p - self.punto
        return "ordenada_x" if abs(d[1]) >= abs(d[0]) else "ordenada_y"

    def mover(self, p, e):
        if self.punto is None:
            k = self.v.punto_cercano(p)
            if k and self.vista_id and k[0] != self.vista_id:
                k = None
            self.v.previa([], k[2] if k else None)
            return
        v = self.d.vista(self.vista_id)
        a = {"tipo": "cota", "subtipo": self._tipo(p), "vista": self.vista_id, "texto": None,
             "puntos": v.de_hoja([self.origen, self.punto]).tolist(), "lugar": v.de_hoja([p])[0].tolist()}
        self.v.previa(self.d.primitivas_anotacion(a))

    def clic(self, p, e):
        if self.origen is None:
            k = self.v.punto_cercano(p)
            if k:
                self.vista_id, self.origen = k[0], k[2]
                self.v.indicar("Elegí un punto a acotar (el origen también vale).")
            return
        if self.punto is None:
            k = self.v.punto_cercano(p)
            if k and k[0] == self.vista_id:
                self.punto = k[2]
                self.v.indicar("Clic para colocar la directriz.")
            return
        tipo, origen, punto = self._tipo(p), self.origen, self.punto
        self.v.modificar(lambda: self.d.agregar_cota(tipo, self.vista_id, [origen, punto], p))
        self.punto = None
        self.v.indicar("Elegí otro punto a acotar (Esc termina).")


class HerrTexto(Herramienta):
    indicacion = "Clic donde va el texto."

    def clic(self, p, e):
        texto, ok = QInputDialog.getMultiLineText(self.v, "Texto", "Texto:")
        if ok and texto.strip():
            self.v.modificar(lambda: self.d.agregar_texto(p, texto))
        self.v.usar_seleccion()


class HerrNota(Herramienta):
    indicacion = "Clic en el punto que señala la directriz."

    def iniciar(self):
        self.flecha = None
        super().iniciar()

    def mover(self, p, e):
        if self.flecha is None:
            k = self.v.punto_cercano(p)
            self.v.previa([], k[2] if k else None)
        else:
            self.v.previa(nd.dibujar_nota(self.flecha, p, "Texto"))

    def clic(self, p, e):
        if self.flecha is None:
            k = self.v.punto_cercano(p)
            self.flecha = k[2] if k else p
            self.v.indicar("Clic donde va el texto de la nota.")
            return
        texto, ok = QInputDialog.getMultiLineText(self.v, "Nota con directriz", "Texto:")
        if ok and texto.strip():
            flecha, vid = self.flecha, self.d.vista_en(self.flecha)
            self.v.modificar(lambda: self.d.agregar_nota(flecha, p, texto, vid))
        self.v.usar_seleccion()


class HerrTabla(Herramienta):
    indicacion = "Clic para colocar la lista de piezas (en la mitad inferior, el encabezado va abajo)."

    def mover(self, p, e):
        self.v.previa(nd.dibujar_tabla(p, self.d.lista_piezas(), hacia_arriba=p[1] < self.d.alto / 2))

    def clic(self, p, e):
        self.v.modificar(lambda: self.d.agregar_tabla(p))
        self.v.usar_seleccion()


class HerrGlobo(Herramienta):
    indicacion = "Clic sobre una pieza en una vista."

    def iniciar(self):
        self.punto = self.vista_id = None
        super().iniciar()

    def mover(self, p, e):
        if self.punto is None:
            k = self.v.punto_cercano(p)
            self.v.previa([], k[2] if k else None)
        else:
            v = self.d.vista(self.vista_id)
            numero = self.d.numero_de_pieza(self.vista_id, v.de_hoja(self.punto))
            self.v.previa(nd.dibujar_globo(self.punto, p, str(numero)))

    def clic(self, p, e):
        if self.punto is None:
            k = self.v.punto_cercano(p)
            q = k[2] if k else p
            vid = self.d.vista_en(q)
            if vid:
                self.punto, self.vista_id = q, vid
                self.v.indicar("Clic para colocar el globo.")
            return
        punto, vid = self.punto, self.vista_id
        self.v.modificar(lambda: self.d.agregar_globo(vid, punto, p))
        self.punto = self.vista_id = None
        self.v.indicar(self.indicacion)


class HerrLineaCentro(Herramienta):
    indicacion = "Clic en el primer punto (centro de un agujero, punto medio…) de la línea de centro."

    def iniciar(self):
        self.p1 = self.vista_id = None
        super().iniciar()

    def mover(self, p, e):
        k = self.v.punto_cercano(p)
        if k and self.vista_id and k[0] != self.vista_id:
            k = None
        prims = nd.dibujar_linea_centro(self.p1, k[2] if k else p) if self.p1 is not None else []
        self.v.previa(prims, k[2] if k else None)

    def clic(self, p, e):
        k = self.v.punto_cercano(p)
        if not k:
            return
        if self.p1 is None:
            self.p1, self.vista_id = k[2], k[0]
            self.v.indicar("Clic en el segundo punto.")
        elif k[0] == self.vista_id and np.linalg.norm(k[2] - self.p1) > 1e-6:
            p1, vid = self.p1, self.vista_id
            self.v.modificar(lambda: self.d.agregar_linea_centro(vid, p1, k[2]))
            self.iniciar()


class HerrMarcaCentro(Herramienta):
    indicacion = "Clic en el borde de una circunferencia o arco."

    def clic(self, p, e):
        c = self.d.circulo_cercano(p, self.v.vista.tolerancia())
        if c:
            v = self.d.vista(c[0])
            self.v.modificar(lambda: self.d.agregar_marca_centro(c[0], v.a_hoja(c[1]), c[2] * v.escala))


class HerrBorrar(Herramienta):
    indicacion = "Clic en la vista o anotación a borrar."

    def clic(self, p, e):
        item = self.v.item_en(p)
        if item is not None:
            self.v.modificar(lambda: self.d.borrar(item.clave))


class HerrGirar(Herramienta):
    indicacion = "Clic en la vista a girar."

    def clic(self, p, e):
        vid = self.d.vista_en(p)
        if vid:
            self.v.girar_vista(vid)
            self.v.usar_seleccion()


# =============================================================== diálogos
ESTILOS = [("Aristas visibles", "visibles"), ("Aristas visibles y ocultas", "visibles_ocultas")]
TANGENTES = [("Longitud completa", "completas"), ("Acortadas", "acortadas"), ("Desactivadas", "no")]
ESCALAS_MENU = ["1:1", "1:2", "1:5", "1:10", "1:20", "1:50", "1:100", "2:1", "5:1", "10:1"]


def _combo(opciones, actual=None):
    c = QComboBox()
    for texto, dato in opciones:
        c.addItem(texto, dato)
    if actual is not None:
        i = c.findData(actual)
        if i >= 0:
            c.setCurrentIndex(i)
    return c


class DialogoVista(QDialog):
    """Vista base nueva (Base View) o propiedades de una vista existente (Drawing View)."""

    def __init__(self, parent, cuerpos=None, vista=None):
        super().__init__(parent)
        self.vista = vista
        self.setWindowTitle("Vista base" if vista is None else "Vista de dibujo")
        form = QFormLayout(self)
        self.lista = self.orientacion = self.etiqueta = None
        if vista is None:
            self.lista = QListWidget()
            for cid, nombre in cuerpos:
                it = QListWidgetItem(nombre)
                it.setData(Qt.UserRole, cid)
                it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
                it.setCheckState(Qt.Checked)
                self.lista.addItem(it)
            self.lista.setMaximumHeight(110)
            form.addRow("Cuerpos", self.lista)
            self.orientacion = _combo([(t, k) for k, t in nd.NOMBRES_ORIENTACION.items()], "frontal")
            form.addRow("Orientación", self.orientacion)
        opciones = ([("Desde el padre", None)] if vista is not None and vista.padre else []) + ESTILOS
        self.estilo = _combo(opciones, vista.estilo if vista is not None else "visibles_ocultas")
        form.addRow("Estilo", self.estilo)
        self.escala = QComboBox()
        self.escala.setEditable(True)
        self.escala.addItems((["Automática"] if vista is None else []) + ESCALAS_MENU)
        if vista is not None:
            self.escala.setEditText(nd.texto_escala(vista.escala))
        form.addRow("Escala", self.escala)
        self.tangentes = _combo(TANGENTES, vista.tangentes if vista is not None else "completas")
        form.addRow("Aristas tangentes", self.tangentes)
        self.marcas = QCheckBox("Marcas y líneas de centro automáticas")
        self.marcas.setChecked(vista.marcas_centro if vista is not None else True)
        form.addRow("", self.marcas)
        if vista is not None and vista.tipo in ("seccion", "detalle"):
            self.etiqueta = QLineEdit(vista.etiqueta)
            form.addRow("Nombre", self.etiqueta)
        botones = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        botones.accepted.connect(self.accept)
        botones.rejected.connect(self.reject)
        form.addRow(botones)

    def _escala(self):
        t = self.escala.currentText().strip()
        return None if t.lower().startswith("auto") else nd.leer_escala(t)

    def accept(self):
        try:
            self._escala()
        except ErrorGeometria as e:
            QMessageBox.warning(self, self.windowTitle(), str(e))
            return
        if self.lista is not None and not self._cuerpos():
            QMessageBox.warning(self, self.windowTitle(), "Elegí al menos un cuerpo.")
            return
        super().accept()

    def _cuerpos(self):
        return [self.lista.item(i).data(Qt.UserRole) for i in range(self.lista.count())
                if self.lista.item(i).checkState() == Qt.Checked]

    def valores(self):
        datos = {"estilo": self.estilo.currentData(), "escala": self._escala(),
                 "tangentes": self.tangentes.currentData(), "marcas_centro": self.marcas.isChecked()}
        if self.lista is not None:
            datos.update(cuerpos=self._cuerpos(), orientacion=self.orientacion.currentData())
        if self.etiqueta is not None:
            datos["etiqueta"] = self.etiqueta.text().strip() or self.vista.etiqueta
        if datos["escala"] is None and self.vista is not None:
            datos.pop("escala")
        return datos


class DialogoHoja(QDialog):
    """Tamaño de hoja (Sheet Size), norma (ISO 1.er diedro / ASME 3.er diedro) y atributos del cajetín."""

    def __init__(self, parent, dibujo):
        super().__init__(parent)
        self.setWindowTitle("Hoja y cajetín")
        form = QFormLayout(self)
        self.norma = _combo([("ISO (1.er diedro)", "ISO"), ("ASME (3.er diedro)", "ASME")], dibujo.norma)
        form.addRow("Norma", self.norma)
        tamanos = [(f"{k} ({a:g} × {b:g} mm)", k) for k, (a, b) in nd.TAMANOS_HOJA.items()]
        self.tamano = _combo(tamanos, dibujo.tamano)
        form.addRow("Tamaño", self.tamano)
        self.orientacion = _combo([("Horizontal", "horizontal"), ("Vertical", "vertical")], dibujo.orientacion)
        form.addRow("Orientación", self.orientacion)
        self.metodo = _combo([("Exacto (aristas B-rep)", "exacto"), ("Rápido (sobre la malla)", "rapido")],
                             dibujo.metodo)
        form.addRow("Cálculo de vistas", self.metodo)
        self.campos = {}
        for campo in ("titulo", "numero_pieza", "autor", "fecha", "escala", "hoja", "material"):
            e = QLineEdit(str(dibujo.cajetin.get(campo, "") or ""))
            if campo == "escala":
                e.setPlaceholderText("Automática (la de la vista base)")
            self.campos[campo] = e
            form.addRow(nd.CAMPOS_CAJETIN[campo], e)
        botones = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        botones.accepted.connect(self.accept)
        botones.rejected.connect(self.reject)
        form.addRow(botones)

    def valores(self):
        return {"norma": self.norma.currentData(), "tamano": self.tamano.currentData(),
                "orientacion": self.orientacion.currentData(), "metodo": self.metodo.currentData(),
                "cajetin": {k: e.text().strip() for k, e in self.campos.items()}}


# =============================================================== ventana
class _Oyente:
    """Suscripción al documento que no mantiene viva la ventana (el documento no tiene «desuscribir»)."""

    def __init__(self, ventana):
        self.ref = weakref.ref(ventana)

    def __call__(self):
        v = self.ref()
        if v is not None:
            try:
                v._modelo_cambio()
            except RuntimeError:     # el objeto de Qt ya se destruyó
                pass


class VentanaDibujo(QMainWindow):
    """Espacio de trabajo DIBUJO para el documento `doc` (ver el docstring del módulo)."""
    cambiado = Signal()

    def __init__(self, doc, parent=None):
        super().__init__(parent)
        app = QApplication.instance()
        if app is not None and not app.styleSheet():
            temas.aplicar_a_app(app)
        self.doc = doc
        self.setWindowTitle(f"{doc.nombre} — Dibujo — {NOMBRE_APP}")
        self.resize(1300, 820)
        self.dibujo = self._dibujo_nuevo()
        self.escena = QGraphicsScene(self)
        self.items = {}
        self._previa_item = None
        self._claves = None
        self._deshacer, self._rehacer = [], []
        self._programado = self._pendiente = False
        self._ajustada = False
        self.acciones = self._crear_acciones()
        self.cinta = CintaDibujo(self.acciones, self)
        self.cinta.ir_a_diseno.connect(self.close)
        self.vista = VistaHoja(self)
        central = QWidget()
        lay = QVBoxLayout(central)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(self.cinta)
        lay.addWidget(self.vista, 1)
        self.setCentralWidget(central)
        self.herramienta = HerrSeleccion(self)
        doc.suscribir(_Oyente(self))
        self.actualizar()
        self.herramienta.iniciar()

    def _dibujo_nuevo(self):
        d = nd.Dibujo("A3", "horizontal", "ISO")
        d.cajetin["titulo"] = self.doc.nombre
        d.cajetin["autor"] = os.environ.get("USERNAME") or os.environ.get("USER") or ""
        return d

    # ------------------------------------------------------------ acciones
    def _crear_acciones(self):
        definicion = [
            ("vista_base", "Vista base", lambda: self.usar(HerrVistaBase(self))),
            ("vista_proyectada", "Vista proyectada", lambda: self.usar(HerrProyectada(self))),
            ("vista_seccion", "Vista de sección", lambda: self.usar(HerrSeccion(self))),
            ("vista_detalle", "Vista de detalle", lambda: self.usar(HerrDetalle(self))),
            ("mover", "Mover", lambda: self.usar(HerrSeleccion(self, "Arrastrá una vista o una anotación."))),
            ("borrar", "Borrar", self.borrar_seleccion),
            ("girar", "Girar", self.girar_seleccion),
            ("linea_centro", "Línea de centro", lambda: self.usar(HerrLineaCentro(self))),
            ("marca_centro", "Marca de centro", lambda: self.usar(HerrMarcaCentro(self))),
            ("cota", "Cota", lambda: self.usar(HerrCota(self))),
            ("cota_ordenadas", "Cota de ordenadas", lambda: self.usar(HerrOrdenadas(self))),
            ("cota_lineal", "Cota lineal", lambda: self.usar(HerrCota(self, "lineal"))),
            ("cota_alineada", "Cota alineada", lambda: self.usar(HerrCota(self, "alineada"))),
            ("cota_radial", "Cota de radio/diámetro", lambda: self.usar(HerrCotaRadial(self))),
            ("cota_radio", "Cota de radio", lambda: self.usar(HerrCotaRadial(self, "radio"))),
            ("cota_diametro", "Cota de diámetro", lambda: self.usar(HerrCotaRadial(self, "diametro"))),
            ("cota_angular", "Cota angular", lambda: self.usar(HerrCotaAngular(self))),
            ("texto", "Texto", lambda: self.usar(HerrTexto(self))),
            ("nota", "Nota con directriz", lambda: self.usar(HerrNota(self))),
            ("tabla", "Tabla (lista de piezas)", lambda: self.usar(HerrTabla(self))),
            ("globo", "Globo", lambda: self.usar(HerrGlobo(self))),
            ("exportar_pdf", "Exportar PDF…", self.dialogo_exportar_pdf),
            ("exportar_dxf", "Exportar hoja como DXF…", self.dialogo_exportar_dxf),
            ("hoja", "Hoja y cajetín…", self.editar_hoja),
        ]
        acciones = {}
        for clave, texto, funcion in definicion:
            a = QAction(icono_dibujo(clave), texto, self)
            a.setToolTip(texto.rstrip("…"))
            a.triggered.connect(funcion)
            acciones[clave] = a
        for clave, texto, atajo, funcion in (
                ("deshacer", "Deshacer", QKeySequence.Undo, self.deshacer),
                ("rehacer", "Rehacer", QKeySequence.Redo, self.rehacer),
                ("cancelar", "Cancelar comando", QKeySequence(Qt.Key_Escape), self.usar_seleccion),
                ("terminar", "Terminar comando", QKeySequence(Qt.Key_Return), self.terminar_herramienta),
                ("suprimir", "Borrar selección", QKeySequence.Delete, self.borrar_seleccion),
                ("encuadrar", "Ajustar la hoja a la ventana", QKeySequence("F6"), lambda: self.vista.ajustar())):
            a = QAction(texto, self)
            a.setShortcut(atajo)
            a.setShortcutContext(Qt.WindowShortcut)
            a.triggered.connect(funcion)
            self.addAction(a)
            acciones[clave] = a
        return acciones

    def comando(self, clave):
        """Ejecuta un comando de la cinta por su clave (p. ej. "vista_base")."""
        self.acciones[clave].trigger()

    # ------------------------------------------------------------ herramientas
    def usar(self, herramienta):
        self.herramienta.terminar()
        self.herramienta = herramienta
        herramienta.iniciar()

    def usar_seleccion(self):
        if not isinstance(self.herramienta, HerrSeleccion) or self.herramienta.indicacion != HerrSeleccion.indicacion:
            self.usar(HerrSeleccion(self))

    def terminar_herramienta(self):
        self.usar_seleccion()

    def indicar(self, texto):
        self.statusBar().showMessage(texto)

    def aviso(self, texto):
        self.indicar(texto)
        if self.isVisible():
            QMessageBox.information(self, "Dibujo", texto)

    def previa(self, primitivas, marca=None):
        """Dibujo provisorio del comando (en azul) y el marcador del punto enganchado."""
        if self._previa_item is not None:
            self.escena.removeItem(self._previa_item)
            self._previa_item = None
        prims = list(primitivas)
        if marca is not None:
            s = self.vista.tolerancia(5.0)
            x, y = float(marca[0]), float(marca[1])
            prims.append(("CONTORNO", ("polilinea", [(x - s, y - s), (x + s, y - s), (x + s, y + s), (x - s, y + s)],
                                       True)))
        if prims:
            self._previa_item = ItemElemento("_previa", prims, False, COLOR_PREVIA)
            self._previa_item.setZValue(10)
            self.escena.addItem(self._previa_item)

    # ------------------------------------------------------------ consultas para las herramientas
    def item_en(self, p):
        """Ítem bajo el cursor: una anotación si se toca su dibujo; si no, la vista en cuyo recuadro cae."""
        p = np.asarray(p, float)
        tol = self.vista.tolerancia(6.0)
        mejor = None
        for it in self.escena.items(QRectF(p[0] - tol, -p[1] - tol, 2 * tol, 2 * tol)):
            if isinstance(it, ItemElemento) and it.zValue() >= 2 and it.clave != "_previa":
                d = it.pintura.distancia(p - (it.pos().x(), -it.pos().y()))
                if d <= tol and (mejor is None or d < mejor[0]):
                    mejor = (d, it)
        if mejor:
            return mejor[1]
        for it in self.escena.items(QPointF(p[0], -p[1])):
            if isinstance(it, ItemElemento) and it.zValue() == 1:
                return it
        return None

    def punto_cercano(self, p):
        """(vista, punto modelo, punto hoja) enganchado bajo el cursor, o None."""
        if self._claves is None:
            lista = self.dibujo.puntos_clave()
            self._claves = (lista, np.array([ph for _, _, ph in lista], float).reshape(-1, 2))
        lista, arr = self._claves
        if not lista:
            return None
        d = np.linalg.norm(arr - np.asarray(p, float), axis=1)
        i = int(np.argmin(d))
        return lista[i] if d[i] <= self.vista.tolerancia() else None

    def vista_seleccionada(self):
        ids = {v.id for v in self.dibujo.vistas}
        sel = [it.clave for it in self.escena.selectedItems() if isinstance(it, ItemElemento) and it.clave in ids]
        return sel[0] if len(sel) == 1 else None

    def cuerpos_disponibles(self):
        return [(cid, c.nombre) for cid, c in self.doc.estado_final.cuerpos.items()]

    # ------------------------------------------------------------ modelo ↔ escena
    def actualizar(self):
        """Recalcula las vistas si el modelo 3D cambió (Update drawing views) y redibuja la hoja."""
        self._programado = self._pendiente = False
        cuerpos = self.doc.estado_final.cuerpos
        self.dibujo.actualizar({cid: c.forma for cid, c in cuerpos.items()},
                               {cid: c.nombre for cid, c in cuerpos.items()})
        self.redibujar()

    def _modelo_cambio(self):
        if not self.isVisible():
            self._pendiente = True
            return
        if not self._programado:
            self._programado = True
            QTimer.singleShot(0, self.actualizar)

    def showEvent(self, e):
        super().showEvent(e)
        if self._pendiente:
            self.actualizar()
        if not self._ajustada:
            self._ajustada = True
            QTimer.singleShot(0, self.vista.ajustar)

    def redibujar(self):
        seleccion = {it.clave for it in self.escena.selectedItems() if isinstance(it, ItemElemento)}
        self.previa([])
        self.escena.clear()
        self.items = {}
        self._claves = None
        w, h = self.dibujo.ancho, self.dibujo.alto
        sombra = QGraphicsRectItem(QRectF(1.5, -h + 1.5, w, h))
        sombra.setBrush(QColor(0, 0, 0, 60))
        sombra.setPen(Qt.NoPen)
        papel = QGraphicsRectItem(QRectF(0, -h, w, h))
        papel.setBrush(QColor("#ffffff"))
        papel.setPen(Qt.NoPen)
        for it in (sombra, papel):
            it.setZValue(-2)
            self.escena.addItem(it)
        ids_vistas = {v.id for v in self.dibujo.vistas}
        for clave, prims in self.dibujo.primitivas_por_elemento():
            it = ItemElemento(clave, prims, clave != "hoja")
            it.setZValue(0 if clave == "hoja" else (1 if clave in ids_vistas else 2))
            self.escena.addItem(it)
            self.items[clave] = it
            if clave in seleccion:
                it.setSelected(True)
        self.escena.setSceneRect(QRectF(-w, -2 * h, 3 * w, 3 * h))

    # ------------------------------------------------------------ edición con deshacer
    def instantanea(self):
        return json.dumps(self.dibujo.a_dict())

    def apilar_deshacer(self, instantanea):
        self._deshacer.append(instantanea)
        del self._deshacer[:-50]
        self._rehacer.clear()

    def modificar(self, funcion):
        """Aplica un cambio al dibujo con deshacer; un error del núcleo se muestra y no deja nada a medias."""
        antes = self.instantanea()
        try:
            resultado = funcion()
        except ErrorGeometria as e:
            self._cargar(json.loads(antes))
            self.aviso(str(e))
            return None
        self.apilar_deshacer(antes)
        self.redibujar()
        self.cambiado.emit()
        return resultado

    def _cargar(self, datos):
        viejo = self.dibujo
        nuevo = nd.Dibujo.desde_dict(datos)
        nuevo._cache = viejo._cache      # la geometría ya calculada se reutiliza
        self.dibujo = nuevo
        self.actualizar()

    def deshacer(self):
        if self._deshacer:
            self.usar_seleccion()
            self._rehacer.append(self.instantanea())
            self._cargar(json.loads(self._deshacer.pop()))
            self.cambiado.emit()

    def rehacer(self):
        if self._rehacer:
            self.usar_seleccion()
            self._deshacer.append(self.instantanea())
            self._cargar(json.loads(self._rehacer.pop()))
            self.cambiado.emit()

    def borrar_seleccion(self):
        claves = [it.clave for it in self.escena.selectedItems() if isinstance(it, ItemElemento)]
        if not claves:
            self.usar(HerrBorrar(self))
            return

        def borrar():
            for c in claves:
                if any(v.id == c for v in self.dibujo.vistas) or any(a["id"] == c for a in self.dibujo.anotaciones):
                    self.dibujo.borrar(c)
        self.modificar(borrar)

    def girar_seleccion(self):
        vid = self.vista_seleccionada()
        if vid:
            self.girar_vista(vid)
        else:
            self.usar(HerrGirar(self))

    def girar_vista(self, vid):
        grados, ok = QInputDialog.getDouble(self, "Girar vista", "Ángulo (°, antihorario):", 90.0, -360.0, 360.0, 2)
        if ok and grados:
            self.modificar(lambda: self.dibujo.girar(vid, grados))

    def editar_elemento(self, clave):
        if any(v.id == clave for v in self.dibujo.vistas):
            v = self.dibujo.vista(clave)
            dlg = DialogoVista(self, vista=v)
            if dlg.exec() == QDialog.Accepted:
                datos = dlg.valores()
                self.modificar(lambda: self.dibujo.editar_vista(clave, **datos))
            return
        a = self.dibujo.anotacion(clave)
        if a["tipo"] == "cota":
            texto, ok = QInputDialog.getText(self, "Cota", "Texto (vacío = valor medido):", text=a.get("texto") or "")
            if ok:
                self.modificar(lambda: a.update(texto=texto.strip() or None))
        elif a["tipo"] in ("texto", "nota"):
            texto, ok = QInputDialog.getMultiLineText(self, "Texto", "Texto:", a["texto"])
            if ok and texto.strip():
                self.modificar(lambda: a.update(texto=texto))
        elif a["tipo"] == "globo":
            texto, ok = QInputDialog.getText(self, "Globo", "Número de elemento:", text=a["numero"])
            if ok and texto.strip():
                self.modificar(lambda: a.update(numero=texto.strip()))

    def editar_hoja(self):
        dlg = DialogoHoja(self, self.dibujo)
        if dlg.exec() == QDialog.Accepted:
            self.modificar(lambda: self.aplicar_hoja(**dlg.valores()))
            self.vista.ajustar()

    def aplicar_hoja(self, norma=None, tamano=None, orientacion=None, cajetin=None, metodo=None):
        """Cambia norma (y con ella el diedro), tamaño u orientación de la hoja, el cálculo de las vistas
        ("exacto" | "rapido") y los atributos del cajetín."""
        d = self.dibujo
        if metodo in ("exacto", "rapido"):
            d.metodo = metodo
        if tamano or orientacion:
            nd.tamano_hoja(tamano or d.tamano, orientacion or d.orientacion)
            d.tamano, d.orientacion = tamano or d.tamano, orientacion or d.orientacion
        if norma and norma != d.norma:
            d.norma, d.diedro = norma, ("primero" if norma == "ISO" else "tercero")
        if cajetin:
            d.cajetin.update(cajetin)
        self.actualizar()

    # ------------------------------------------------------------ exportar
    def exportar_pdf(self, ruta):
        """Hoja a PDF a escala real: 1 mm del dibujo = 1 mm del papel (QPdfWriter, vectorial)."""
        w, h = self.dibujo.ancho, self.dibujo.alto
        pdf = QPdfWriter(str(ruta))
        pdf.setResolution(1200)
        pdf.setCreator(f"{NOMBRE_APP} {VERSION}")
        pdf.setTitle(self.dibujo.cajetin.get("titulo") or "Dibujo")
        tam = QPageSize(QSizeF(min(w, h), max(w, h)), QPageSize.Unit.Millimeter, "",
                        QPageSize.SizeMatchPolicy.ExactMatch)
        orientacion = QPageLayout.Orientation.Landscape if w > h else QPageLayout.Orientation.Portrait
        pdf.setPageLayout(QPageLayout(tam, orientacion, QMarginsF(0, 0, 0, 0), QPageLayout.Unit.Millimeter))
        p = QPainter(pdf)
        try:
            k = pdf.resolution() / 25.4
            p.setRenderHint(QPainter.Antialiasing)
            p.scale(k, k)
            p.translate(0, h)
            Pintura(self.dibujo.primitivas()).pintar(p, pantalla=False)
        finally:
            p.end()
        return ruta

    def exportar_dxf(self, ruta, version="2000"):
        """Hoja a DXF (mm, una capa por tipo de línea: VISIBLE, OCULTA, CENTRO, COTAS…)."""
        return dxf.escribir_dxf(ruta, self.dibujo.primitivas(), capas=nd.CAPAS, version=version)

    def _ruta_salida(self, filtro, extension):
        nombre = (self.dibujo.cajetin.get("titulo") or self.doc.nombre or "dibujo").strip() + extension
        base = os.path.dirname(self.doc.ruta) if getattr(self.doc, "ruta", None) else os.path.expanduser("~")
        ruta, _ = QFileDialog.getSaveFileName(self, "Exportar", os.path.join(base, nombre), filtro)
        if ruta and not ruta.lower().endswith(extension):
            ruta += extension
        return ruta

    def dialogo_exportar_pdf(self):
        ruta = self._ruta_salida("PDF (*.pdf)", ".pdf")
        if ruta:
            self.exportar_pdf(ruta)
            self.indicar(f"PDF guardado: {ruta}")

    def dialogo_exportar_dxf(self):
        ruta = self._ruta_salida("DXF (*.dxf)", ".dxf")
        if ruta:
            try:
                self.exportar_dxf(ruta)
            except (OSError, dxf.ErrorDXF) as e:
                self.aviso(f"No se pudo guardar el DXF: {e}")
                return
            self.indicar(f"DXF guardado: {ruta}")

    # ------------------------------------------------------------ persistencia
    def a_dict(self):
        """Dibujo serializable (JSON) para guardarlo con el documento."""
        return self.dibujo.a_dict()

    def desde_dict(self, datos):
        """Carga un dibujo guardado con `a_dict()` y recalcula sus vistas con el modelo actual."""
        self.usar_seleccion()
        self.dibujo = nd.Dibujo.desde_dict(datos)
        self._deshacer.clear()
        self._rehacer.clear()
        self.actualizar()
        self.vista.ajustar()

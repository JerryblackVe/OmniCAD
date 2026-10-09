"""
Menú radial (marking menu) de Fusion: clic derecho en la vista y aparecen 8 comandos alrededor del
cursor, con la lista de contexto debajo. Se elige moviendo el ratón hacia el comando (se resalta su
sector) y haciendo clic en cualquier parte del sector; clic en el centro, fuera del menú o Esc lo cierran.
El comando de abajo ("Boceto") abre el segundo nivel con 8 comandos de boceto; la flecha del centro
vuelve al primero.

Orden de los sectores (como la referencia de Fusion, en sentido horario desde arriba):
N, NE, E, SE, S, SO, O, NO → índices 0..7.
"""
import math

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFontMetricsF, QIcon, QPainter, QPainterPath, QPen, QPolygonF
from PySide6.QtWidgets import QFrame, QVBoxLayout, QWidget

from . import temas

RADIO = 104                 # distancia del centro al punto de anclaje de cada comando
ALTO_PILDORA = 24
ANCHO_LISTA = 230
ALTO_FILA = 22


class ItemRadial:
    """Un comando del menú: texto, función, ícono (QIcon), habilitado y, opcional, un segundo nivel."""

    def __init__(self, texto, funcion=None, icono=None, activo=True, sub=None):
        self.texto, self.funcion, self.icono, self.activo, self.sub = texto, funcion, icono, activo, sub


def sector(dx, dy):
    """Índice 0..7 (N, NE, E, SE, S, SO, O, NO) para un desplazamiento en píxeles (y hacia abajo)."""
    angulo = math.degrees(math.atan2(dx, -dy)) % 360.0      # 0 = arriba, en sentido horario
    return int((angulo + 22.5) // 45) % 8


class _Fila(QWidget):
    """Fila de la lista de contexto (texto a la izquierda, atajo a la derecha)."""

    def __init__(self, texto, funcion, atajo="", activo=True, menu=None):
        super().__init__()
        self.texto, self.funcion, self.atajo, self.activo, self.menu = texto, funcion, atajo, activo, menu
        self.setFixedHeight(ALTO_FILA)
        self.setMouseTracking(True)
        self._sobre = False

    def enterEvent(self, _e):
        self._sobre = True
        self.update()

    def leaveEvent(self, _e):
        self._sobre = False
        self.update()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton and self.activo and self.funcion is not None:
            self.menu.ejecutar(self.funcion)

    def paintEvent(self, _e):
        p = QPainter(self)
        c = temas.activo()
        if self._sobre and self.activo:
            p.fillRect(self.rect(), QColor(c["menu_hover"]))
        p.setPen(QColor(c["texto"] if self.activo else c["texto_inactivo"]))
        r = self.rect().adjusted(12, 0, -10, 0)
        p.drawText(r, Qt.AlignVCenter | Qt.AlignLeft, self.texto)
        if self.atajo:
            p.setPen(QColor(c["texto_tenue"]))
            p.drawText(r, Qt.AlignVCenter | Qt.AlignRight, self.atajo)


class MenuRadial(QWidget):
    def __init__(self, items, contexto=(), parent=None):
        super().__init__(parent, Qt.Popup | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setMouseTracking(True)
        self.ensurePolished()                    # la fuente de la hoja de estilos, para medir bien los textos
        self.niveles = [self._ocho(items)]
        self.activo = None
        self.ejecutado = None
        self.ancho = 2 * (RADIO + 200)
        self.centro = QPointF(self.ancho / 2, RADIO + ALTO_PILDORA + 14)
        alto = int(self.centro.y() + RADIO + ALTO_PILDORA + 14)
        self.lista = None
        filas = [f for f in contexto]
        if filas:
            self.lista = QFrame(self)
            self.lista.setObjectName("lista_radial")
            lay = QVBoxLayout(self.lista)
            lay.setContentsMargins(0, 3, 0, 3)
            lay.setSpacing(0)
            for f in filas:
                if f is None:
                    linea = QFrame(objectName="linea_radial")
                    linea.setFixedHeight(7)
                    lay.addWidget(linea)
                    continue
                texto, funcion, *resto = f
                atajo = resto[0] if resto else ""
                activo = resto[1] if len(resto) > 1 else True
                lay.addWidget(_Fila(texto, funcion, atajo, activo, self))
            self.lista.setFixedWidth(ANCHO_LISTA)
            self.lista.adjustSize()
            self.lista.move(int(self.centro.x() - ANCHO_LISTA / 2), alto)
            alto += self.lista.height() + 2
        self.resize(self.ancho, alto)

    @staticmethod
    def _ocho(items):
        items = list(items)[:8]
        return items + [None] * (8 - len(items))

    @property
    def items(self):
        return self.niveles[-1]

    # ------------------------------------------------------------ abrir / ejecutar
    def abrir(self, pos_global):
        self.move(int(pos_global.x() - self.centro.x()), int(pos_global.y() - self.centro.y()))
        self.show()
        self.raise_()
        self.setFocus()

    def ejecutar(self, funcion):
        self.ejecutado = funcion
        self.close()
        QTimer.singleShot(0, funcion)

    # ------------------------------------------------------------ geometría de las píldoras
    def _rect(self, i, item):
        fm = QFontMetricsF(self.font())
        ancho = fm.horizontalAdvance(item.texto) + (34 if item.icono is not None else 20) + (12 if item.sub else 0)
        ang = math.radians(i * 45.0)
        dx, dy = math.sin(ang), -math.cos(ang)
        ax, ay = self.centro.x() + RADIO * dx, self.centro.y() + RADIO * dy
        if dx > 0.1:
            x = ax - 8
        elif dx < -0.1:
            x = ax + 8 - ancho
        else:
            x = ax - ancho / 2
        return QRectF(x, ay - ALTO_PILDORA / 2, ancho, ALTO_PILDORA)

    def _sector_en(self, pos):
        if self.lista is not None and self.lista.geometry().contains(pos.toPoint()):
            return None
        for i, item in enumerate(self.items):
            if item is not None and self._rect(i, item).contains(pos):
                return i
        d = pos - self.centro
        if math.hypot(d.x(), d.y()) < 16:
            return None
        i = sector(d.x(), d.y())
        return i if self.items[i] is not None else None

    # ------------------------------------------------------------ ratón y teclado
    def mouseMoveEvent(self, e):
        pos = e.position()
        nuevo = self._sector_en(pos)
        d = pos - self.centro
        if len(self.niveles) > 1 and math.hypot(d.x(), d.y()) < 14:
            self.niveles.pop()                         # la flecha del centro vuelve al primer nivel
            nuevo = None
        elif nuevo is not None and self.items[nuevo].sub and self._rect(nuevo, self.items[nuevo]).contains(pos):
            self.niveles.append(self._ocho(self.items[nuevo].sub))
            nuevo = None
        self.activo = nuevo
        self.update()

    def mousePressEvent(self, e):
        if e.button() not in (Qt.LeftButton, Qt.RightButton):
            return
        if not self.rect().contains(e.position().toPoint()):
            self.close()
            return
        i = self._sector_en(e.position())
        if i is None:
            d = e.position() - self.centro
            if math.hypot(d.x(), d.y()) < 16:
                if len(self.niveles) > 1:
                    self.niveles.pop()
                    self.update()
                else:
                    self.close()
            return
        item = self.items[i]
        if item.sub:
            self.niveles.append(self._ocho(item.sub))
            self.activo = None
            self.update()
        elif item.activo and item.funcion is not None:
            self.ejecutar(item.funcion)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(e)

    # ------------------------------------------------------------ dibujo
    def paintEvent(self, _e):
        p = QPainter(self)
        p.setFont(self.font())
        p.setRenderHint(QPainter.Antialiasing)
        c = self.centro
        tc = temas.activo()
        acento = QColor(tc["acento"])
        if self.activo is not None:              # sector resaltado
            p.setPen(Qt.NoPen)
            acento.setAlpha(46)
            p.setBrush(acento)
            r = RADIO - 18
            p.drawPie(QRectF(c.x() - r, c.y() - r, 2 * r, 2 * r), int((90 - self.activo * 45 - 22.5) * 16), 45 * 16)
        p.setPen(QPen(QColor(tc["texto_tenue"]), 1.2))
        pildora = QColor(tc["menu_fondo"])
        pildora.setAlpha(240)
        p.setBrush(pildora)
        p.drawEllipse(c, 9, 9)
        if len(self.niveles) > 1:                # flecha para volver al primer nivel
            p.setPen(QPen(QColor(tc["texto_tenue"]), 1.6))
            p.drawLine(QPointF(c.x() - 4, c.y() + 2), QPointF(c.x(), c.y() - 3))
            p.drawLine(QPointF(c.x(), c.y() - 3), QPointF(c.x() + 4, c.y() + 2))
        for i, item in enumerate(self.items):
            if item is None:
                continue
            r = self._rect(i, item)
            camino = QPainterPath()
            camino.addRoundedRect(r, 4, 4)
            resaltado = i == self.activo and item.activo
            p.setPen(QPen(QColor(tc["acento"]) if resaltado else QColor(tc["menu_borde"]), 1))
            p.setBrush(QColor(tc["menu_hover"]) if resaltado else pildora)
            p.drawPath(camino)
            x = r.left() + 7
            if item.icono is not None:
                icono = item.icono if isinstance(item.icono, QIcon) else QIcon(item.icono)
                modo = QIcon.Normal if item.activo else QIcon.Disabled
                p.drawPixmap(int(x), int(r.center().y() - 8), icono.pixmap(16, 16, modo))
                x += 21
            p.setPen(QColor(tc["texto"] if item.activo else tc["texto_inactivo"]))
            p.drawText(QRectF(x, r.top(), r.right() - x - (12 if item.sub else 4), r.height()),
                       Qt.AlignVCenter | Qt.AlignLeft, item.texto)
            if item.sub:
                p.setBrush(QColor(tc["texto_tenue"]))
                p.setPen(Qt.NoPen)
                cx, cy = r.right() - 9, r.center().y()
                p.drawPolygon(QPolygonF([QPointF(cx - 3, cy - 2), QPointF(cx + 3, cy - 2), QPointF(cx, cy + 2)]))

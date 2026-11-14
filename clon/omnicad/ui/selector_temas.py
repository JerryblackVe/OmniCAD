# -*- coding: utf-8 -*-
"""Elección visual de temas; el combo oculto conserva el valor de Preferencias."""

from PySide6.QtCore import QEvent, QPointF, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QIcon, QLinearGradient, QPainter, QPen, QPixmap, QPolygonF
from PySide6.QtWidgets import QGridLayout, QToolButton, QWidget

from . import temas


def miniatura_tema(colores, ancho=168, alto=104) -> QPixmap:
    """Dibuja cinta, navegador, visor y panel usando exclusivamente los tokens del tema."""
    c = {clave: QColor(valor) for clave, valor in colores.items()}
    imagen = QPixmap(ancho, alto)
    imagen.fill(c["fondo"])
    p = QPainter(imagen)
    p.scale(ancho / 168, alto / 104)

    # La primera fila del visor conserva el color exacto del extremo del degradado.
    degradado = QLinearGradient(0, 28.5, 0, 103.5)
    degradado.setColorAt(0, c["visor_arriba"])
    degradado.setColorAt(1, c["visor_abajo"])
    p.fillRect(QRectF(48, 28, 120, 76), degradado)
    p.setPen(QPen(c["rejilla"], 0.6))
    for x in range(54, 169, 22):
        p.drawLine(x, 68, x - 18, 104)
    for y in (76, 88, 100):
        p.drawLine(48, y, 168, y)

    p.fillRect(QRectF(0, 28, 48, 76), c["panel"])
    p.fillRect(QRectF(0, 28, 48, 12), c["panel_cabecera"])
    for i in range(3):
        y = 44 + 14 * i
        p.fillRect(QRectF(3, y, 42, 11), c["nav_fila"])
        p.fillRect(QRectF(9, y + 4, 29 - 5 * i, 2), c["texto_tenue"])

    p.setPen(QPen(c["borde"], 1))
    p.setBrush(c["boton"])
    for x in range(7, 148, 30):
        p.drawRoundedRect(QRectF(x, 7, 22, 13), 2, 2)
    p.fillRect(QRectF(7, 24, 45, 2), c["acento"])

    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(QPen(c["acento"], 1.5))
    p.setBrush(c["acento"])
    p.drawPolygon(QPolygonF([QPointF(75, 49), QPointF(91, 41), QPointF(107, 49), QPointF(91, 57)]))
    p.setBrush(c["boton"])
    p.drawPolygon(QPolygonF([QPointF(75, 49), QPointF(91, 57), QPointF(91, 76), QPointF(75, 68)]))
    p.setBrush(c["panel_cabecera"])
    p.drawPolygon(QPolygonF([QPointF(91, 57), QPointF(107, 49), QPointF(107, 68), QPointF(91, 76)]))

    p.setPen(QPen(c["borde"], 1))
    p.setBrush(c["flotante"])
    p.drawRoundedRect(QRectF(116, 51, 46, 46), 2, 2)
    p.fillRect(QRectF(122, 58, 31, 2), c["texto"])
    p.fillRect(QRectF(122, 66, 24, 2), c["texto_tenue"])
    p.fillRect(QRectF(132, 80, 24, 11), c["boton_primario"])
    p.fillRect(QRectF(138, 85, 12, 2), c["boton_primario_texto"])
    p.end()
    return imagen


class SelectorTemas(QWidget):
    """Grilla de tres columnas sincronizada con el QComboBox que guarda la elección."""

    tema_pasando = Signal(str)
    tema_salio = Signal()

    def __init__(self, combo, parent=None):
        super().__init__(parent)
        self.combo = combo
        combo.setParent(self)
        combo.hide()
        self._grilla = QGridLayout(self)
        self._grilla.setContentsMargins(0, 0, 0, 0)
        self._grilla.setSpacing(8)
        self._grilla.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self._demora = QTimer(self, singleShot=True, interval=300)
        self._demora.setTimerType(Qt.PreciseTimer)
        self._demora.timeout.connect(self._previsualizar)
        self._tarjeta_pasando = None
        self._previsualizando = False      # hay un tema de paso aplicado: al salir hay que volver al elegido
        combo.currentIndexChanged.connect(self._sincronizar)
        self.recargar()

    def recargar(self):
        """Reconstruye las tarjetas desde los ítems y la elección del combo, incluidos los propios."""
        self._demora.stop()
        self._tarjeta_pasando = None
        while self._grilla.count():
            tarjeta = self._grilla.takeAt(0).widget()
            tarjeta.hide()
            tarjeta.setParent(None)
            tarjeta.deleteLater()
        for i in range(self.combo.count()):
            clave = self.combo.itemData(i)
            tema, _avisos = temas.resolver(clave)
            c = tema["colores"]
            tarjeta = QToolButton(self, objectName="tarjeta_tema", text=self.combo.itemText(i))
            tarjeta.setProperty("clave_tema", clave)
            tarjeta.setCheckable(True)
            tarjeta.setFocusPolicy(Qt.StrongFocus)
            tarjeta.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            tarjeta.setIcon(QIcon(miniatura_tema(c)))
            tarjeta.setIconSize(QSize(168, 104))
            tarjeta.setFixedWidth(184)
            tarjeta.setToolTip(tarjeta.text())
            tarjeta.setAccessibleName(tarjeta.text())
            tarjeta.setStyleSheet(
                f"QToolButton#tarjeta_tema {{ background: {c['tarjeta']}; color: {c['texto']};"
                f" border: 2px solid {c['borde']}; border-radius: 4px; padding: 6px; }}"
                f"QToolButton#tarjeta_tema:checked {{ border-color: {c['acento']}; }}"
                f"QToolButton#tarjeta_tema:focus {{ border-style: dashed; border-color: {c['acento']}; }}")
            tarjeta.clicked.connect(lambda _marcado=False, indice=i: self.combo.setCurrentIndex(indice))
            tarjeta.clicked.connect(self._sincronizar)
            tarjeta.installEventFilter(self)
            self._grilla.addWidget(tarjeta, i // 3, i % 3)
        self._sincronizar()

    def _sincronizar(self, *_):
        self._demora.stop()
        self._previsualizando = False
        for i in range(self._grilla.count()):
            self._grilla.itemAt(i).widget().setChecked(i == self.combo.currentIndex())

    def eventFilter(self, tarjeta, evento):
        if evento.type() == QEvent.Enter:
            self._tarjeta_pasando = tarjeta
            self._demora.start()
        elif evento.type() == QEvent.Leave:
            self._demora.stop()
            self._tarjeta_pasando = None
        elif evento.type() == QEvent.KeyPress and evento.key() in (Qt.Key_Return, Qt.Key_Enter):
            tarjeta.click()
            return True
        return super().eventFilter(tarjeta, evento)

    def _previsualizar(self):
        if self._tarjeta_pasando is not None:
            self._previsualizando = True
            self.tema_pasando.emit(self._tarjeta_pasando.property("clave_tema"))

    def leaveEvent(self, evento):
        self._demora.stop()
        self._tarjeta_pasando = None
        if self._previsualizando:                  # sin vista previa aplicada no hay nada que revertir (evita re-aplicar el tema)
            self._previsualizando = False
            self.tema_salio.emit()
        super().leaveEvent(evento)

    def hideEvent(self, evento):
        self._demora.stop()
        self._tarjeta_pasando = None
        super().hideEvent(evento)

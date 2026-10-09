# -*- coding: utf-8 -*-
"""
Aviso flotante abajo a la derecha de la vista, como el de Fusion ("1 advertencia(s) — Las restricciones
o las cotas se han eliminado durante la operación. Más información"). Se cierra solo a los pocos
segundos o con la ×; "Más información" muestra el detalle completo.
"""
from PySide6.QtCore import QPointF, Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPixmap, QPolygonF
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QMessageBox, QToolButton, QVBoxLayout

COLORES = {"advertencia": "#f2b705", "error": "#d9382c", "info": "#2f7ed8"}


def _icono_aviso(nivel, lado=22):
    pm = QPixmap(lado, lado)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(COLORES.get(nivel, COLORES["advertencia"])))
    if nivel == "advertencia":
        p.drawPolygon(QPolygonF([QPointF(lado / 2, 1), QPointF(lado - 1, lado - 2), QPointF(1, lado - 2)]))
        signo_y = lado * 0.42
    else:
        p.drawEllipse(1, 1, lado - 2, lado - 2)
        signo_y = lado * 0.30
    p.setPen(QColor("#202020") if nivel == "advertencia" else QColor("#ffffff"))
    f = p.font()
    f.setBold(True)
    f.setPixelSize(int(lado * 0.55))
    p.setFont(f)
    p.drawText(0, int(signo_y - lado * 0.1), lado, int(lado * 0.6), Qt.AlignCenter, "i" if nivel == "info" else "!")
    p.end()
    return pm


class AvisoFlotante(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("AvisoFlotante")
        self.setStyleSheet("#AvisoFlotante { background: #ffffff; border: 1px solid #c9c9c9; border-radius: 2px; }"
                           "QLabel { color: #3c3c3c; background: transparent; }")
        self.setFixedWidth(250)
        fila = QHBoxLayout(self)
        fila.setContentsMargins(10, 8, 6, 8)
        fila.setSpacing(10)
        self.icono = QLabel()
        self.icono.setAlignment(Qt.AlignTop)
        fila.addWidget(self.icono)
        col = QVBoxLayout()
        col.setSpacing(2)
        self.titulo = QLabel()
        self.titulo.setStyleSheet("font-weight: bold; color: #222222;")
        self.texto = QLabel()
        self.texto.setWordWrap(True)
        self.texto.setStyleSheet("font-size: 11px;")
        self.enlace = QLabel("<a href='#' style='color:#0b6bcb;text-decoration:none'>Más información</a>")
        self.enlace.setStyleSheet("font-size: 11px;")
        self.enlace.linkActivated.connect(self._mas_informacion)
        for w in (self.titulo, self.texto, self.enlace):
            col.addWidget(w)
        fila.addLayout(col, 1)
        cerrar = QToolButton()
        cerrar.setText("×")
        cerrar.setAutoRaise(True)
        cerrar.setStyleSheet("QToolButton { border: none; color: #777777; font-size: 14px; }")
        cerrar.clicked.connect(self.hide)
        fila.addWidget(cerrar, 0, Qt.AlignTop)
        self._detalle = ""
        self._nivel = "advertencia"
        self._cuenta = 0
        self._t = QTimer(self, singleShot=True, interval=8000)
        self._t.timeout.connect(self.hide)
        self.hide()

    def mostrar(self, texto, nivel="advertencia", detalle=None):
        """Muestra (o suma a) el aviso. Varios avisos seguidos del mismo nivel se cuentan: "2 advertencia(s)"."""
        self._cuenta = self._cuenta + 1 if self.isVisible() and nivel == self._nivel else 1
        self._nivel = nivel
        nombre = {"advertencia": "advertencia(s)", "error": "error(es)", "info": "aviso(s)"}.get(nivel, "aviso(s)")
        self.titulo.setText(f"{self._cuenta} {nombre}")
        self.texto.setText(texto)
        self._detalle = detalle or texto
        self.icono.setPixmap(_icono_aviso(nivel))
        self.adjustSize()
        self.show()
        self.raise_()
        if self.parentWidget() is not None and hasattr(self.parentWidget(), "reubicar"):
            self.parentWidget().reubicar()
        self._t.start()

    def _mas_informacion(self, _href=""):
        caja = QMessageBox(QMessageBox.Warning if self._nivel != "info" else QMessageBox.Information,
                           self.titulo.text(), self._detalle, QMessageBox.Ok, self.window())
        caja.exec()

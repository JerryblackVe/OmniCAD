# -*- coding: utf-8 -*-
"""
P-149 · La página de Preferencias › Asas y superposiciones: una vista previa en vivo con las asas reales arriba, dos
ajustes globales («Tamaño» y «Color de las asas») y, en «Avanzado», una fila por elemento con su miniatura, su color
(muestra que se toca), su tamaño y su opacidad. Al pasar el mouse por una fila, ese elemento se resalta en la vista previa.
Los valores viven en las mismas claves `asas/<grupo>_*` de `estilo_asas`; este módulo solo arma los controles.
"""
from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import (QGridLayout, QHBoxLayout, QLabel, QPushButton, QSlider, QToolButton, QVBoxLayout,
                               QWidget)

from . import estilo_asas, temas
from .preferencias import CampoColor
from .vista_previa_asas import VistaPreviaAsas

GRUPOS_ASAS = ("flechas", "anillo", "puntos", "cajas")        # los que mueven los ajustes globales


class _Miniatura(QWidget):
    """El dibujito de un elemento (flecha, anillo, punto, caja, cuerpo…) con su color y su opacidad actuales."""

    def __init__(self, grupo):
        super().__init__()
        self.grupo = grupo
        self.setFixedSize(40, 28)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = QColor.fromRgbF(*estilo_asas.rgb(self.grupo))
        c.setAlphaF(estilo_asas.opacidad(self.grupo))
        g, r = self.grupo, QRectF(self.rect()).adjusted(4, 4, -4, -4)
        borde = QPen(QColor(temas.color("borde")), 1)
        if g == "flechas":
            p.setPen(QPen(c, 3))
            p.drawLine(QPointF(6, 22), QPointF(26, 10))
            p.setBrush(c)
            p.setPen(Qt.NoPen)
            p.drawPolygon(QPolygonF([QPointF(34, 6), QPointF(24, 6), QPointF(30, 15)]))
        elif g == "anillo":
            p.setPen(QPen(c, 2.5))
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(r)
        elif g == "puntos":
            p.setBrush(c)
            p.setPen(QPen(QColor("#101418"), 1))
            p.drawEllipse(QRectF(12, 6, 16, 16))
        elif g == "cajas":
            p.setBrush(QColor("#ffffff"))
            p.setPen(QPen(c, 2))
            p.drawRoundedRect(r, 3, 3)
            p.setPen(QColor("#1d1d1d"))
            p.drawText(r, Qt.AlignCenter, "12")
        else:                                       # cuerpos y caras: un rombo relleno
            p.setBrush(c)
            p.setPen(borde)
            p.drawPolygon(QPolygonF([QPointF(20, 4), QPointF(36, 14), QPointF(20, 24), QPointF(4, 14)]))
        p.end()


class _Fila(QWidget):
    """Una fila de «Avanzado»: se avisa al entrar o salir el mouse para resaltar su elemento en la vista previa."""
    entra = Signal(str)
    sale = Signal()

    def __init__(self, grupo):
        super().__init__()
        self.grupo = grupo
        self.setAttribute(Qt.WA_Hover, True)
        self.setMouseTracking(True)

    def enterEvent(self, e):
        self.entra.emit(self.grupo)
        super().enterEvent(e)

    def leaveEvent(self, e):
        self.sale.emit()
        super().leaveEvent(e)


class PaginaAsas(QWidget):
    """`controles`: clave → CampoColor o QSlider, los que la ventana de Preferencias guarda y restablece."""
    cambiado = Signal()

    def __init__(self, prefs):
        super().__init__()
        self.prefs = prefs
        self.controles = {}
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.vista = VistaPreviaAsas()
        lay.addWidget(self.vista)
        lay.addWidget(self._globales())
        self.avanzado = QToolButton(text="Avanzado: ajustar cada elemento", checkable=True, objectName="avanzado_asas")
        self.avanzado.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.avanzado.setArrowType(Qt.RightArrow)
        self.avanzado.toggled.connect(self._mostrar_avanzado)
        lay.addWidget(self.avanzado)
        self.detalle = self._detalle()
        self.detalle.setVisible(False)
        lay.addWidget(self.detalle)
        self.restablecer = QPushButton("Restablecer", objectName="restablecer_asas")
        self.restablecer.setToolTip("Vuelve todas las asas y superposiciones al color, tamaño y opacidad de fábrica.")
        lay.addWidget(self.restablecer, 0, Qt.AlignLeft)
        self.tam_global.setValue(self.controles[estilo_asas.clave("flechas", "tamano_pct")].value())
        self.color_global.setValue(self.controles[estilo_asas.clave("flechas", "color")].value())

    # ------------------------------------------------------------ construcción
    def _globales(self):
        w = QWidget()
        g = QGridLayout(w)
        g.setContentsMargins(0, 8, 0, 0)
        self.tam_global = QSlider(Qt.Horizontal, minimum=estilo_asas.TAMANO[0], maximum=estilo_asas.TAMANO[1],
                                  singleStep=5, pageStep=10, objectName="tamano_asas")
        self.tam_global.setValue(100)
        etiqueta = QLabel("100 %", alignment=Qt.AlignRight | Qt.AlignVCenter)
        etiqueta.setMinimumWidth(48)
        self.tam_global.valueChanged.connect(lambda v: etiqueta.setText(f"{v} %"))
        self.tam_global.valueChanged.connect(self._tam_global_cambiado)
        self.color_global = CampoColor("asas", "", "Color de las asas", fabrica=estilo_asas.fabrica("flechas"))
        self.color_global.cambiado.connect(self._color_global_cambiado)
        g.addWidget(QLabel("<b>Tamaño de las asas</b>"), 0, 0)
        g.addWidget(self.tam_global, 0, 1)
        g.addWidget(etiqueta, 0, 2)
        g.addWidget(QLabel("<b>Color de las asas</b>"), 1, 0)
        g.addWidget(self.color_global, 1, 1)
        g.setColumnStretch(1, 1)
        return w

    def _detalle(self):
        w = QWidget()
        g = QGridLayout(w)
        g.setContentsMargins(0, 0, 0, 0)
        g.setVerticalSpacing(2)
        g.addWidget(QLabel("Color"), 0, 2)
        g.addWidget(QLabel("Tamaño"), 0, 3)
        g.addWidget(QLabel("Opacidad"), 0, 4)
        for fila, (grupo, (titulo, _hex, tam, op, que)) in enumerate(estilo_asas.GRUPOS.items(), start=1):
            contenedor = _Fila(grupo)
            contenedor.entra.connect(self.vista.resaltar)
            contenedor.sale.connect(lambda: self.vista.resaltar("flechas"))
            h = QHBoxLayout(contenedor)
            h.setContentsMargins(4, 2, 4, 2)
            mini = _Miniatura(grupo)
            h.addWidget(mini)
            nombre = QLabel(titulo)
            nombre.setToolTip(que)
            nombre.setMinimumWidth(150)
            h.addWidget(nombre, 1)
            color = CampoColor(estilo_asas.clave(grupo, "color"), self.prefs[estilo_asas.clave(grupo, "color")], titulo,
                               fabrica=estilo_asas.fabrica(grupo))
            color.setFixedWidth(64)
            self.controles[estilo_asas.clave(grupo, "color")] = color
            color.cambiado.connect(mini.update)
            h.addWidget(color)
            for propiedad, existe, rango in (("tamano_pct", tam, estilo_asas.TAMANO), ("opacidad_pct", op, estilo_asas.OPACIDAD)):
                if not existe:
                    hueco = QWidget()
                    hueco.setFixedWidth(110)
                    h.addWidget(hueco)
                    continue
                clave = estilo_asas.clave(grupo, propiedad)
                s = QSlider(Qt.Horizontal, minimum=rango[0], maximum=rango[1], singleStep=5, pageStep=10)
                s.setValue(int(self.prefs[clave]))
                s.setFixedWidth(110)
                s.valueChanged.connect(mini.update)
                self.controles[clave] = s
                h.addWidget(s)
            g.addWidget(contenedor, fila, 0, 1, 5)
        return w

    # ------------------------------------------------------------ comportamiento
    def _mostrar_avanzado(self, abierto):
        self.avanzado.setArrowType(Qt.DownArrow if abierto else Qt.RightArrow)
        self.detalle.setVisible(abierto)

    def _tam_global_cambiado(self, valor):
        for g in GRUPOS_ASAS:
            self.controles[estilo_asas.clave(g, "tamano_pct")].setValue(valor)

    def _color_global_cambiado(self):
        for g in GRUPOS_ASAS:
            self.controles[estilo_asas.clave(g, "color")].setValue(self.color_global.value())

    def sincronizar_globales(self):
        """Tras restablecer o cargar: los ajustes globales siguen a los de las flechas."""
        self.tam_global.blockSignals(True)
        self.tam_global.setValue(self.controles[estilo_asas.clave("flechas", "tamano_pct")].value())
        self.tam_global.blockSignals(False)
        self.color_global.blockSignals(True)
        self.color_global.setValue(self.controles[estilo_asas.clave("flechas", "color")].value())
        self.color_global.blockSignals(False)

    def refrescar(self):
        self.vista.refrescar()
        for m in self.findChildren(_Miniatura):
            m.update()

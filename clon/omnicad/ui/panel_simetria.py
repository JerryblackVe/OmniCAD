# -*- coding: utf-8 -*-
"""Panel SIMETRÍA del boceto (Fusion: Mirror), con la misma cara que los paneles de comando: Objetos, Eje de simetría,
Vista previa, Aceptar y Cancelar. No guarda estado: `mostrar` lo llena con lo que manda el Lienzo (`estado_simetria`)
y cada botón sale como una señal. Los botones no toman el foco: Enter y Esc siguen siendo del Lienzo."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QAbstractButton, QCheckBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from .comando import _FilaSeleccion
from .formulario import ANCHOS, armar_cabecera, armar_estado, poner_estado
from .iconos import icono

CAMPOS = (("seleccion", "Objetos", "La geometría a reflejar: clic en cada curva o una ventana de selección."),
          ("eje", "Eje de simetría", "La línea de simetría: una línea del boceto, también de construcción."))


class PanelSimetria(QFrame):
    campo = Signal(str)          # «seleccion» o «eje»: lo que va a elegir el próximo clic
    limpiar = Signal(str)
    previa = Signal(bool)
    aceptado = Signal()
    cancelado = Signal()
    ANCHO = ANCHOS["simple"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("panel_comando")
        self.setAttribute(Qt.WA_StyledBackground, True)
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)
        cab, ico, titulo = armar_cabecera(self, self.cancelado)
        ico.setPixmap(icono("simetria_boceto").pixmap(18, 18))
        titulo.setText("SIMETRÍA")
        v.addWidget(cab)
        cuerpo = QWidget()
        g = QGridLayout(cuerpo)
        g.setContentsMargins(10, 8, 10, 6)
        g.setHorizontalSpacing(10)
        g.setVerticalSpacing(5)
        g.setColumnMinimumWidth(1, 150)
        self.filas = {}
        for fila, (clave, texto, ayuda) in enumerate(CAMPOS):
            etiqueta = QLabel(texto, objectName="etiqueta_cmd")
            etiqueta.setToolTip(ayuda)
            w = _FilaSeleccion(clave)
            w.activar.connect(lambda f: self.campo.emit(f.campo))
            w.limpiar.connect(lambda f: self.limpiar.emit(f.campo))
            g.addWidget(etiqueta, fila, 0)
            g.addWidget(w, fila, 1)
            self.filas[clave] = w
        self.casilla = QCheckBox()
        self.casilla.setChecked(True)
        self.casilla.setToolTip("Muestra la copia reflejada antes de aceptar.")
        self.casilla.toggled.connect(self.previa)
        g.addWidget(QLabel("Vista previa", objectName="etiqueta_cmd"), len(CAMPOS), 0)
        g.addWidget(self.casilla, len(CAMPOS), 1)
        v.addWidget(cuerpo)
        armar_estado(self, v, self.ANCHO)
        pie = QHBoxLayout()
        pie.setContentsMargins(10, 4, 10, 8)
        pie.addStretch(1)
        self.boton_ok = QPushButton("Aceptar", objectName="boton_primario")
        self.boton_ok.clicked.connect(self.aceptado)
        cancelar = QPushButton("Cancelar")
        cancelar.clicked.connect(self.cancelado)
        pie.addWidget(self.boton_ok)
        pie.addWidget(cancelar)
        v.addLayout(pie)
        for w in self.findChildren(QAbstractButton):
            w.setFocusPolicy(Qt.NoFocus)
        self.mostrar({"objetos": 0, "eje": False, "campo": "seleccion", "valido": False, "previa": True, "guia": "",
                      "error": ""})

    def mostrar(self, e):
        """Pinta el estado del Lienzo: conteo de cada campo y cuál está activo, si se puede aceptar y qué falta."""
        self.filas["seleccion"].set_estado(e["objetos"], e["campo"] == "seleccion")
        self.filas["eje"].set_estado(1 if e["eje"] else 0, e["campo"] == "eje")
        self.boton_ok.setEnabled(e["valido"])
        poner_estado(self, e["guia"], e["error"])
        self.casilla.blockSignals(True)
        self.casilla.setChecked(e["previa"])
        self.casilla.blockSignals(False)
        self.ajustar()

    def ajustar(self):
        self.setFixedWidth(self.ANCHO)
        self.layout().activate()
        self.adjustSize()

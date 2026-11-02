# -*- coding: utf-8 -*-
"""Panel de información que acompaña a un comando sobre el lienzo (el «Información del sistema de coordenadas» del SCU y
los de análisis): texto, sección plegable Consejos, Más información y botón Cerrar. Cerrarlo no cancela el comando."""
from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from .formulario import Seccion, armar_cabecera

ANCHO, MARGEN, SOBRE_COMENTARIOS = 400, 12, 48         # deja a la vista la barra de Comentarios
AYUDA_LOCAL = Path(__file__).resolve().parents[3] / "docs" / "fusion_docs" / "contenido"     # no va en el paquete ni en git


class PanelInfo(QFrame):
    def __init__(self, padre, titulo, texto, consejos="", articulo="", ancho=ANCHO, centrado=False):
        """`articulo`: ruta del artículo dentro de `AYUDA_LOCAL`. Si no está, «Más información» queda gris: nunca abre la web."""
        super().__init__(padre)
        self.setObjectName("panel_comando")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedWidth(min(ancho, max(padre.width() - 2 * MARGEN, ANCHO)))
        self.centrado = centrado
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(4)
        cab, _icono, self.titulo = armar_cabecera(self, None)
        self.titulo.setText(titulo.upper())
        v.addWidget(cab)
        self.texto = QLabel(texto, wordWrap=True)
        self.texto.setContentsMargins(12, 6, 12, 2)
        v.addWidget(self.texto)
        self.consejos = Seccion("Consejos")
        self.consejos.grilla.addWidget(QLabel(consejos, wordWrap=True), 0, 0)
        self.consejos.setContentsMargins(10, 0, 10, 0)
        self.consejos.plegada.connect(lambda _a: (self.adjustSize(), self.ubicar_informacion()))
        v.addWidget(self.consejos)
        self.consejos.setVisible(bool(consejos))
        self.boton_mas = None
        if articulo:
            ruta = AYUDA_LOCAL / articulo
            self.boton_mas = QPushButton("Más información", enabled=ruta.is_file(),
                                         toolTip="Abre la ayuda local." if ruta.is_file() else "La ayuda local no está instalada.")
            self.boton_mas.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(ruta))))
            fila = QHBoxLayout()
            fila.setContentsMargins(10, 0, 10, 0)
            fila.addStretch(1)
            fila.addWidget(self.boton_mas)
            v.addLayout(fila)
        pie = QHBoxLayout()
        pie.setContentsMargins(10, 4, 10, 8)
        pie.addStretch(1)
        self.boton_cerrar = QPushButton("Cerrar")
        self.boton_cerrar.clicked.connect(self.hide)
        pie.addWidget(self.boton_cerrar)
        v.addLayout(pie)
        self.adjustSize()
        self.ubicar_informacion()
        self.show()

    def ubicar_informacion(self):
        """Abajo a la izquierda del lienzo; si la persona lo movió, queda donde lo dejó. Siempre por encima del navegador,
        que en una ventana chica lo alcanza: `AreaVisor.reubicar` lo llama cada vez que acomoda el lienzo."""
        if self.posicion_usuario is None and self.centrado:
            self.move((self.parent().width() - self.width()) // 2, max(MARGEN, (self.parent().height() - self.height()) // 2))
        elif self.posicion_usuario is None:
            self.move(MARGEN, max(MARGEN, self.parent().height() - self.height() - SOBRE_COMENTARIOS))
        self.raise_()

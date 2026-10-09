"""
Panel COMENTARIOS de Fusion: barra plegada abajo a la izquierda de la vista ("COMENTARIOS  +"). El "+" agrega
un comentario al diseño; clic en el título despliega la lista; clic derecho sobre un comentario lo borra.
Los comentarios son datos del documento (`doc.comentarios`) y se guardan con el proyecto.
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QInputDialog, QLabel, QListWidget, QListWidgetItem, QMenu,
                               QToolButton, QVBoxLayout)

ANCHO = 200


class PanelComentarios(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("panel_comentarios")
        self.doc = None
        self.setFixedWidth(ANCHO)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        cabecera = QFrame()
        fila = QHBoxLayout(cabecera)
        fila.setContentsMargins(8, 1, 2, 1)
        self.titulo = QLabel("COMENTARIOS")
        self.titulo.setCursor(Qt.PointingHandCursor)
        self.titulo.mousePressEvent = lambda _e: self.plegar()
        fila.addWidget(self.titulo, 1)
        self.b_mas = QToolButton()
        self.b_mas.setText("+")
        self.b_mas.setAutoRaise(True)
        self.b_mas.setToolTip("<b>Agregar comentario</b><br>Deja una nota en el diseño (se guarda con el proyecto).")
        self.b_mas.clicked.connect(self.agregar)
        fila.addWidget(self.b_mas)
        lay.addWidget(cabecera)
        self.lista = QListWidget()
        self.lista.setWordWrap(True)
        self.lista.setContextMenuPolicy(Qt.CustomContextMenu)
        self.lista.customContextMenuRequested.connect(self._menu)
        self.lista.setFixedHeight(140)
        self.lista.hide()
        lay.addWidget(self.lista)

    def set_documento(self, doc):
        self.doc = doc
        self.actualizar()

    def actualizar(self):
        self.lista.clear()
        comentarios = getattr(self.doc, "comentarios", []) if self.doc is not None else []
        for c in comentarios:
            it = QListWidgetItem(f"{c['texto']}\n{c.get('fecha', '')}")
            it.setToolTip(c["texto"])
            self.lista.addItem(it)
        self.titulo.setText(f"COMENTARIOS ({len(comentarios)})" if comentarios else "COMENTARIOS")
        self.adjustSize()

    def plegar(self):
        self.lista.setVisible(self.lista.isHidden())
        self.adjustSize()
        if self.parentWidget() is not None and hasattr(self.parentWidget(), "reubicar"):
            self.parentWidget().reubicar()

    def agregar(self, texto=None):
        if self.doc is None:
            return
        if texto is None:
            texto, ok = QInputDialog.getMultiLineText(self.window(), "Agregar comentario", "Comentario:")
            if not ok:
                return
        if texto.strip():
            self.doc.agregar_comentario(texto.strip())
            if self.lista.isHidden():
                self.plegar()

    def _menu(self, pos):
        it = self.lista.itemAt(pos)
        if it is None or self.doc is None:
            return
        fila = self.lista.row(it)
        m = QMenu(self)
        m.addAction("Eliminar comentario", lambda: self.doc.borrar_comentario(fila))
        m.exec(self.lista.mapToGlobal(pos))

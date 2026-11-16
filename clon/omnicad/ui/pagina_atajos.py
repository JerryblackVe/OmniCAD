# -*- coding: utf-8 -*-
"""Preferencias › Atajos de teclado (P-165), como «Change Keyboard Shortcut» de Fusion: una lista buscable con todos
los comandos, una caja donde se pulsa la combinación nueva y el choque con otro comando marcado en rojo. Guarda lo
mismo que las herramientas `set_shortcut` / `reset_shortcuts` (la preferencia `atajos/teclas`, ver `api/atajos.py`).
"""
import json

from PySide6.QtCore import QSignalBlocker, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QKeySequence
from PySide6.QtWidgets import (QHBoxLayout, QKeySequenceEdit, QLabel, QLineEdit, QPushButton, QSizePolicy, QTreeWidget,
                               QTreeWidgetItem, QVBoxLayout, QWidget)

from ..api import atajos as at
from . import temas


class PaginaAtajos(QWidget):
    """Controla `atajos/teclas`: `value()` es el JSON de lo que difiere de fábrica; `valido()` es falso si hay choques."""
    cambiado = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._efectivo = at.efectivos({})
        self.buscar = QLineEdit(placeholderText="Buscar un comando o una tecla…", clearButtonEnabled=True)
        self.arbol = QTreeWidget(objectName="lista_atajos")
        self.arbol.setHeaderLabels(["Comando", "Atajo"])
        self.arbol.setRootIsDecorated(False)
        self.arbol.setFixedHeight(300)
        self.items = {}
        for clave in sorted(at.CATALOGO, key=lambda c: at.titulo(c).lower()):
            it = QTreeWidgetItem([at.titulo(clave).rstrip("…"), ""])
            it.setData(0, Qt.UserRole, clave)
            self.arbol.addTopLevelItem(it)
            self.items[clave] = it
        self.arbol.setColumnWidth(0, 260)
        self.editor = QKeySequenceEdit(objectName="caja_atajo")
        self.editor.setMaximumSequenceLength(1)
        self.editor.setToolTip("Pulsá la combinación de teclas que querés para el comando elegido.")
        self.b_quitar = QPushButton("Quitar atajo")
        self.b_fabrica = QPushButton("Volver al de fábrica")
        self.aviso = QLabel(wordWrap=True, objectName="aviso_atajos")
        self.aviso.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        self.aviso.setMinimumHeight(self.aviso.fontMetrics().height() * 2)
        fila = QHBoxLayout()
        for w in (QLabel("Tecla:"), self.editor, self.b_quitar, self.b_fabrica):
            fila.addWidget(w)
        fila.addStretch(1)
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.addWidget(self.buscar)
        v.addLayout(fila)                  # la tecla y el aviso arriba de la lista: se ven sin bajar la página (1024×700)
        v.addWidget(self.aviso)
        v.addWidget(self.arbol)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)     # la página no se estira: queda arriba, a su alto
        self.buscar.textChanged.connect(self._filtrar)
        self.arbol.currentItemChanged.connect(self._elegido)
        self.editor.keySequenceChanged.connect(self._tecla_pulsada)
        self.b_quitar.clicked.connect(lambda: self._poner(self._clave(), ""))
        self.b_fabrica.clicked.connect(lambda: self._poner(self._clave(), at.CATALOGO[self._clave()][1]))
        self._refrescar()

    # --- el control, para Preferencias
    def value(self):
        return json.dumps(at.diferencias(self._efectivo), sort_keys=True)

    def setValue(self, texto):
        self._efectivo = at.efectivos(at.leer(texto))
        self._refrescar()

    def valido(self):
        return not at.choques(self._efectivo)

    # --- interno
    def _clave(self):
        it = self.arbol.currentItem()
        return it.data(0, Qt.UserRole) if it is not None else None

    def _filtrar(self, texto):
        t = texto.strip().lower()
        for clave, it in self.items.items():
            it.setHidden(bool(t) and t not in at.titulo(clave).lower() and t not in self._efectivo[clave].lower()
                         and t not in clave.lower())

    def _elegido(self, *_):
        clave = self._clave()
        with QSignalBlocker(self.editor):
            self.editor.setKeySequence(QKeySequence(self._efectivo[clave] if clave else ""))
        self.editor.setEnabled(clave is not None)
        self.b_quitar.setEnabled(clave is not None)
        self.b_fabrica.setEnabled(clave is not None)
        self._refrescar()

    def _tecla_pulsada(self, secuencia):
        clave = self._clave()
        if clave is not None:
            self._poner(clave, at.normalizar(secuencia.toString(QKeySequence.PortableText)) or "")

    def _poner(self, clave, texto):
        if clave is None:
            return
        self._efectivo[clave] = at.normalizar(texto) or ""
        with QSignalBlocker(self.editor):
            self.editor.setKeySequence(QKeySequence(self._efectivo[clave]))
        self._refrescar()
        self.cambiado.emit()

    def _refrescar(self):
        choque = at.choques(self._efectivo)
        rojo = QBrush(QColor(temas.color("error")))
        for clave, it in self.items.items():
            it.setText(1, self._efectivo[clave])
            en_choque = clave in choque
            for col in (0, 1):
                it.setForeground(col, rojo if en_choque else QBrush())
            it.setToolTip(1, f"También la usa «{at.titulo(choque[clave][0])}»." if en_choque else "")
        clave = self._clave()
        if clave in choque:
            texto = f"⚠ {self._efectivo[clave]} ya la usa «{at.titulo(choque[clave][0])}». Cambiá una de las dos."
            temas.poner_rol(self.aviso, "error")
        else:
            texto = ("Hay teclas repetidas: están en rojo." if choque else
                     "Elegí un comando y pulsá su tecla nueva." if clave is None else "")
            temas.poner_rol(self.aviso, "tenue" if not choque else "error")
        self.aviso.setText(texto)

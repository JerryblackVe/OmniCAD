# -*- coding: utf-8 -*-
"""Preferencias › Cinta (P-164): elegir qué botones grandes lleva cada sección de la cinta y en qué orden, arrastrando
con el mouse; la sección «FAVORITAS» de la pestaña SÓLIDO se llena soltando herramientas de la lista (como «Pin to
toolbar» de Fusion). Guarda la preferencia `cinta/personal` (ver `api/cinta_personal.py`), la misma que escriben las
herramientas `set_ribbon_section` / `reset_ribbon`.
"""
from PySide6.QtCore import QSignalBlocker, QSize, Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (QComboBox, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QPushButton,
                               QSizePolicy, QVBoxLayout, QWidget)

from ..api import cinta_personal as cp
from . import temas


class _Tira(QListWidget):
    """Los botones de la sección, en fila: se reordenan arrastrando y aceptan herramientas soltadas desde la lista."""
    cambio = Signal()
    soltada = Signal(str, int)        # clave de la herramienta soltada y la posición donde cayó

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("tira_cinta")
        self.setFlow(QListWidget.LeftToRight)
        self.setWrapping(False)
        self.setViewMode(QListWidget.IconMode)
        self.setMovement(QListWidget.Snap)
        self.setIconSize(QSize(32, 32))
        self.setGridSize(QSize(92, 66))
        self.setFixedHeight(92)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setDragDropMode(QListWidget.DragDrop)
        self.setDefaultDropAction(Qt.MoveAction)
        self.setAcceptDrops(True)
        self.setSelectionMode(QListWidget.SingleSelection)
        self.model().rowsMoved.connect(lambda *_: self.cambio.emit())

    def dropEvent(self, e):
        origen = e.source()
        if origen is not None and origen is not self and origen.objectName() == "herramientas_cinta":
            for it in origen.selectedItems():
                fila = self.indexAt(e.position().toPoint()).row()
                self.soltada.emit(it.data(Qt.UserRole), fila if fila >= 0 else self.count())
            e.setDropAction(Qt.CopyAction)
            e.accept()
            return
        super().dropEvent(e)
        self.cambio.emit()

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key_Delete, Qt.Key_Backspace) and self.currentRow() >= 0:
            self.takeItem(self.currentRow())
            self.cambio.emit()
            return
        super().keyPressEvent(e)


class PaginaCinta(QWidget):
    """Controla `cinta/personal`: `value()` es el JSON de lo que difiere de fábrica."""
    cambiado = Signal()

    def __init__(self, acciones=None, parent=None):
        super().__init__(parent)
        self._acciones = acciones or {}
        self._efectivo = cp.efectivas({})
        self.seccion = QComboBox(objectName="seccion_cinta")
        for s in cp.SECCIONES:
            pestana, grupo = s.split("/")
            self.seccion.addItem(f"{pestana} › {grupo}", s)
        self.tira = _Tira()
        self.cuenta = QLabel(objectName="cuenta_cinta")
        self.aviso = QLabel(wordWrap=True, objectName="aviso_cinta")
        temas.poner_rol(self.aviso, "tenue")
        self.aviso.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        self.b_quitar = QPushButton("Quitar")
        self.b_fabrica = QPushButton("Volver al de fábrica")
        self.buscar = QLineEdit(placeholderText="Buscar una herramienta…", clearButtonEnabled=True)
        self.lista = QListWidget(objectName="herramientas_cinta")
        self.lista.setDragEnabled(True)
        self.lista.setDragDropMode(QListWidget.DragOnly)
        self.lista.setIconSize(QSize(24, 24))
        self.lista.setFixedHeight(180)
        for clave in sorted(cp.COMANDOS, key=lambda c: cp.titulo(c).lower()):
            it = QListWidgetItem(self._icono(clave), cp.titulo(clave).rstrip("…"))
            it.setData(Qt.UserRole, clave)
            self.lista.addItem(it)
        fila = QHBoxLayout()
        for w in (QLabel("Sección:"), self.seccion):
            fila.addWidget(w)
        fila.addStretch(1)
        fila.addWidget(self.cuenta)
        acciones_fila = QHBoxLayout()
        acciones_fila.addWidget(self.b_quitar)
        acciones_fila.addWidget(self.b_fabrica)
        acciones_fila.addStretch(1)
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.addLayout(fila)
        v.addWidget(self.tira)
        v.addLayout(acciones_fila)
        v.addWidget(self.aviso)
        v.addWidget(QLabel("Herramientas (arrastrá una hasta la sección, o doble clic):"))
        v.addWidget(self.buscar)
        v.addWidget(self.lista)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        self.seccion.currentIndexChanged.connect(self._mostrar)
        self.tira.cambio.connect(self._de_la_tira)
        self.tira.soltada.connect(self._agregar)
        self.lista.itemDoubleClicked.connect(lambda it: self._agregar(it.data(Qt.UserRole), None))
        self.buscar.textChanged.connect(self._filtrar)
        self.b_quitar.clicked.connect(self._quitar)
        self.b_fabrica.clicked.connect(self._fabrica)
        self._mostrar()

    # --- el control, para Preferencias
    def value(self):
        return cp.a_texto(cp.diferencias(self._efectivo))

    def setValue(self, texto):
        self._efectivo = cp.efectivas(cp.leer(texto))
        self._mostrar()

    def valido(self):
        return True

    # --- interno
    def _icono(self, clave):
        a = self._acciones.get(clave)
        return a.icon() if a is not None else QIcon()

    def _actual(self):
        return self.seccion.currentData()

    def _mostrar(self, *_):
        with QSignalBlocker(self.tira):
            self.tira.clear()
            for clave in self._efectivo[self._actual()]:
                it = QListWidgetItem(self._icono(clave), cp.titulo(clave).rstrip("…"))
                it.setData(Qt.UserRole, clave)
                it.setToolTip(cp.titulo(clave))
                self.tira.addItem(it)
        self._contar()

    def _contar(self, aviso=""):
        n = len(self._efectivo[self._actual()])
        self.cuenta.setText(f"{n} de {cp.MAXIMO} botones")
        self.aviso.setText(aviso or ("Arrastrá para cambiar el orden. Suprimir quita el elegido."
                                     if n else "Sin botones: soltá aquí una herramienta de la lista."))
        self.b_fabrica.setEnabled(self._efectivo[self._actual()] != cp.SECCIONES[self._actual()])

    def _de_la_tira(self):
        self._efectivo[self._actual()] = [self.tira.item(i).data(Qt.UserRole) for i in range(self.tira.count())]
        self._contar()
        self.cambiado.emit()

    def _agregar(self, clave, posicion):
        actual = self._efectivo[self._actual()]
        if clave in actual:
            self._contar("Esa herramienta ya está en la sección.")
            return
        if len(actual) >= cp.MAXIMO:
            self._contar(f"La sección ya tiene {cp.MAXIMO} botones: quitá uno antes.")
            return
        actual.insert(len(actual) if posicion is None else posicion, clave)
        self._mostrar()
        self.cambiado.emit()

    def _quitar(self):
        if self.tira.currentRow() >= 0:
            self.tira.takeItem(self.tira.currentRow())
            self._de_la_tira()

    def _fabrica(self):
        self._efectivo[self._actual()] = list(cp.SECCIONES[self._actual()])
        self._mostrar()
        self.cambiado.emit()

    def _filtrar(self, texto):
        t = texto.strip().lower()
        for i in range(self.lista.count()):
            it = self.lista.item(i)
            it.setHidden(bool(t) and t not in it.text().lower() and t not in it.data(Qt.UserRole).lower())

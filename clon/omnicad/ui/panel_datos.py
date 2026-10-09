# -*- coding: utf-8 -*-
"""
Panel de datos (columna izquierda, como el Data Panel de Fusion 360): "Mis datos recientes" con
la miniatura de cada proyecto, su nombre y la fecha de modificación. Doble clic = abrir.
En Fusion los datos viven en la nube; acá la lista son los .omnicad abiertos o guardados en esta
PC (rutas en QSettings) y la miniatura sale de `miniatura.png` dentro del propio proyecto.
"""
import time
import zipfile
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QMenu, QToolButton, QVBoxLayout,
                               QWidget)

from ..io_archivos import proyecto
from .iconos import icono


class _Tarjeta(QWidget):
    def __init__(self, ruta):
        super().__init__()
        self.setAttribute(Qt.WA_TranslucentBackground)
        h = QHBoxLayout(self)
        h.setContentsMargins(6, 6, 6, 6)
        mini = QLabel()
        mini.setFixedSize(64, 64)
        mini.setAlignment(Qt.AlignCenter)
        mini.setStyleSheet("background: #ffffff;")
        pm = QPixmap()
        try:
            datos = proyecto.leer_miniatura(ruta)
            if datos:
                pm.loadFromData(datos)
        except (OSError, zipfile.BadZipFile, KeyError):
            pass
        mini.setPixmap(pm.scaled(62, 62, Qt.KeepAspectRatio, Qt.SmoothTransformation) if not pm.isNull()
                       else icono("componente").pixmap(40, 40))
        h.addWidget(mini)
        v = QVBoxLayout()
        v.setSpacing(2)
        nombre = QLabel(f"<b>{Path(ruta).stem}</b>")
        nombre.setToolTip(str(ruta))
        fecha = QLabel(time.strftime("%d/%m/%Y %H:%M", time.localtime(Path(ruta).stat().st_mtime)))
        fecha.setStyleSheet("color: #5a5a5a; font-size: 8pt;")
        v.addWidget(nombre)
        v.addWidget(fecha)
        v.addStretch(1)
        h.addLayout(v, 1)


class PanelDatos(QWidget):
    abrir = Signal(str)
    cerrar = Signal()

    def __init__(self, prefs, parent=None):
        super().__init__(parent)
        self.setObjectName("panel_datos")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedWidth(330)
        self.prefs = prefs
        cab = QHBoxLayout()
        cab.setContentsMargins(10, 8, 6, 4)
        casa = QLabel()
        casa.setPixmap(icono("casa").pixmap(16, 16))
        cab.addWidget(casa)
        cab.addWidget(QLabel("›"))
        cab.addWidget(QLabel("<b>Mis datos recientes</b>"))
        cab.addStretch(1)
        b = QToolButton(text="✕")
        b.setToolTip("Cerrar el panel de datos")
        b.clicked.connect(self.cerrar)
        cab.addWidget(b)
        self.lista = QListWidget()
        self.lista.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.lista.itemDoubleClicked.connect(lambda it: self.abrir.emit(it.data(Qt.UserRole)))
        self.lista.setContextMenuPolicy(Qt.CustomContextMenu)
        self.lista.customContextMenuRequested.connect(self._menu)
        self.vacio = QLabel("Todavía no hay proyectos recientes.\nGuardá o abrí un .omnicad y aparece acá.")
        self.vacio.setAlignment(Qt.AlignCenter)
        self.vacio.setStyleSheet("color: #8a8a8a;")
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.addLayout(cab)
        v.addWidget(self.lista, 1)
        v.addWidget(self.vacio, 1)
        self.recargar()

    def recargar(self):
        self.lista.clear()
        for ruta in self.prefs.recientes():
            if not Path(ruta).is_file():
                continue
            it = QListWidgetItem()
            it.setData(Qt.UserRole, ruta)
            tarjeta = _Tarjeta(ruta)
            it.setSizeHint(tarjeta.sizeHint().expandedTo(tarjeta.minimumSizeHint()))
            self.lista.addItem(it)
            self.lista.setItemWidget(it, tarjeta)
        self.vacio.setVisible(self.lista.count() == 0)
        self.lista.setVisible(self.lista.count() > 0)

    def _menu(self, pos):
        it = self.lista.itemAt(pos)
        if it is None:
            return
        ruta = it.data(Qt.UserRole)
        m = QMenu(self)
        m.addAction("Abrir", lambda: self.abrir.emit(ruta))
        m.addAction("Quitar de la lista", lambda: (self.prefs.quitar_reciente(ruta), self.recargar()))
        m.exec(self.lista.mapToGlobal(pos))

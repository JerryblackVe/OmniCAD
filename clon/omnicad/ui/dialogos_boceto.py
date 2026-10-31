# -*- coding: utf-8 -*-
"""
Diálogos del boceto sobre algo ya hecho (editar un patrón se hace en su panel: `ui/panel_patron.py`):
  - Administrar proyecciones perdidas (Fusion: Manage Lost Projections): re-vincular, romper vínculo o borrar.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton, QVBoxLayout)

from .iconos import icono

MODOS_PROYECCION = {"project": "proyectar", "intersect": "intersecar", "giro": "perfil giratorio"}


class DialogoPerdidas(QDialog):
    """Las proyecciones perdidas del boceto (`lienzo.perdidas`): elegir una la selecciona en el lienzo."""

    def __init__(self, lienzo):
        super().__init__(lienzo)
        self.setWindowTitle("Administrar proyecciones perdidas")
        self.setWindowIcon(icono("proyectar"))
        self.lz = lienzo
        v = QVBoxLayout(self)
        aviso = QLabel("Estas proyecciones ya no coinciden con el modelo: quedaron como estaban. Re-vinculalas a "
                       "otra geometría, rompé su vínculo (quedan como geometría normal) o borralas.")
        aviso.setWordWrap(True)
        v.addWidget(aviso)
        self.lista = QListWidget()
        self.lista.currentRowChanged.connect(self._mostrar)
        v.addWidget(self.lista)
        self.atenuar = QCheckBox("Atenuar el resto")
        self.atenuar.setToolTip("Apaga lo que no es una proyección perdida para verlas mejor.")
        self.atenuar.toggled.connect(self.lz.atenuar_resto)
        self.finished.connect(lambda _r: self.lz.atenuar_resto(False))
        v.addWidget(self.atenuar)
        fila = QHBoxLayout()
        self.b_revincular = QPushButton("Re-vincular")
        self.b_romper = QPushButton("Romper vínculo")
        self.b_borrar = QPushButton("Borrar geometría")
        self.b_romper_todos = QPushButton("Romper todos")
        self.b_borrar_todos = QPushButton("Borrar todos")
        self.b_revincular.clicked.connect(self._revincular)
        self.b_romper.clicked.connect(lambda: self._tratar("break"))
        self.b_borrar.clicked.connect(lambda: self._tratar("delete"))
        self.b_romper_todos.clicked.connect(lambda: self._tratar("break", todas=True))
        self.b_borrar_todos.clicked.connect(lambda: self._tratar("delete", todas=True))
        for b in (self.b_revincular, self.b_romper, self.b_borrar, self.b_romper_todos, self.b_borrar_todos):
            fila.addWidget(b)
        v.addLayout(fila)
        cerrar = QDialogButtonBox(QDialogButtonBox.Close)
        cerrar.rejected.connect(self.reject)
        v.addWidget(cerrar)
        self._poblar()

    def _registro(self, pid):
        return next(r for r in self.lz.b.proyecciones if r["id"] == pid)

    def _poblar(self):
        self.lista.clear()
        for pid in self.lz.perdidas:
            r = self._registro(pid)
            item = QListWidgetItem(f"Proyección {pid} ({MODOS_PROYECCION.get(r['modo'], r['modo'])}, "
                                   f"{len(r['ids'])} entidades)")
            item.setData(Qt.UserRole, pid)
            self.lista.addItem(item)
        self.lz.atenuar_resto(self.atenuar.isChecked())       # las que quedan perdidas, cambiaron
        hay = self.lista.count() > 0
        for b in (self.b_revincular, self.b_romper, self.b_borrar, self.b_romper_todos, self.b_borrar_todos):
            b.setEnabled(hay)

    def _elegida(self):
        item = self.lista.currentItem()
        return item.data(Qt.UserRole) if item is not None else None

    def _mostrar(self, _fila):
        pid = self._elegida()
        if pid is None:
            return
        self.b_revincular.setEnabled(True)
        self.lz.seleccion = list(self._registro(pid)["ids"])
        self.lz.update()

    def _tratar(self, accion, todas=False):
        pid = self._elegida()
        pids = list(self.lz.perdidas) if todas else ([pid] if pid is not None else [])
        if pids and self.lz.tratar_perdidas(accion, pids):
            self._poblar()

    def _revincular(self):
        pid = self._elegida()
        if pid is not None:
            self.lz.revincular(pid)
            self.accept()

# -*- coding: utf-8 -*-
"""
Diálogos del boceto sobre algo ya hecho:
  - Editar patrón (Fusion: doble clic en el glifo del patrón): cantidades, distancias, dirección por ángulo o por
    una línea, simetría y una casilla por copia (destildada = suprimida). Devuelve los cambios para
    `Boceto.editar_patron` (el lienzo los aplica).
  - Administrar proyecciones perdidas (Fusion: Manage Lost Projections): re-vincular, romper vínculo o borrar.
"""
import math

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout,
                               QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton, QSpinBox, QVBoxLayout)

from .iconos import icono

MODOS_PROYECCION = {"project": "proyectar", "intersect": "intersecar", "giro": "perfil giratorio"}


class DialogoPatron(QDialog):
    def __init__(self, boceto, registro, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Editar patrón")
        p = registro["params"]
        self.rectangular = registro["tipo"] == "rectangular"
        self.setWindowIcon(icono("patron_rectangular" if self.rectangular else "patron_circular"))
        self._suprimidos = set(registro["suprimidos"])
        form = QFormLayout(self)
        if self.rectangular:
            lineas = [i for i, c in boceto.curvas.items() if c.tipo == "linea"]
            self.n1, self.n2 = self._entero(p["cantidad1"], 1), self._entero(p["cantidad2"], 1)
            self.d1, self.d2 = self._distancia(p["distancia1"]), self._distancia(p["distancia2"])
            self.modo = QComboBox()
            self.modo.addItem("Extensión (total)", "extension")
            self.modo.addItem("Espaciado (cada paso)", "espaciado")
            self.modo.setCurrentIndex(max(0, self.modo.findData(p["modo"])))
            self.linea1, self.ang1 = self._direccion(lineas, p.get("linea1"), p["dir1"])
            self.linea2, self.ang2 = self._direccion(lineas, p.get("linea2"), p["dir2"])
            for etiqueta, w in (("Cantidad 1", self.n1), ("Distancia 1", self.d1), ("Dirección 1", self.linea1),
                                ("Ángulo 1", self.ang1), ("Cantidad 2", self.n2), ("Distancia 2", self.d2),
                                ("Dirección 2", self.linea2), ("Ángulo 2", self.ang2), ("Distancia", self.modo)):
                form.addRow(etiqueta, w)
            cantidades = (self.n1, self.n2)
        else:
            self.n = self._entero(p["cantidad"], 2)
            self.total = QDoubleSpinBox(decimals=3, minimum=-360.0, maximum=360.0, suffix=" °")
            self.total.setValue(p["angulo_total"])
            form.addRow("Cantidad", self.n)
            form.addRow("Ángulo total", self.total)
            cantidades = (self.n,)
        self.simetrico = QCheckBox()
        self.simetrico.setChecked(bool(p["simetrico"]))
        form.addRow("Simétrico", self.simetrico)
        self.lista = QListWidget()
        self.lista.setToolTip("Destildá una copia para suprimirla.")
        form.addRow("Copias", self.lista)
        botones = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        botones.accepted.connect(self.accept)
        botones.rejected.connect(self.reject)
        form.addRow(botones)
        for sp in cantidades:
            sp.valueChanged.connect(self._poblar)
        self._poblar()

    @staticmethod
    def _entero(valor, minimo):
        sp = QSpinBox(minimum=minimo, maximum=10000)
        sp.setValue(int(valor))
        return sp

    @staticmethod
    def _distancia(valor):
        sp = QDoubleSpinBox(decimals=3, minimum=-1e6, maximum=1e6, suffix=" mm")
        sp.setValue(float(valor))
        return sp

    @staticmethod
    def _direccion(lineas, linea, vector):
        """Combo «Ángulo» o una línea del boceto, y el ángulo (grados) que se usa sin línea."""
        combo = QComboBox()
        combo.addItem("Ángulo", None)
        for i in lineas:
            combo.addItem(f"Línea {i}", i)
        if linea is not None:
            combo.setCurrentIndex(max(0, combo.findData(linea)))
        ang = QDoubleSpinBox(decimals=3, minimum=-360.0, maximum=360.0, suffix=" °")
        ang.setValue(math.degrees(math.atan2(vector[1], vector[0])))
        return combo, ang

    def _copias(self):
        return self.n1.value() * self.n2.value() - 1 if self.rectangular else self.n.value() - 1

    def _destildadas(self):
        return [k for k in range(self.lista.count()) if self.lista.item(k).checkState() == Qt.Unchecked]

    def _poblar(self):
        """Una casilla por copia; al cambiar la cantidad se conservan las suprimidas por índice."""
        if self.lista.count():
            self._suprimidos = set(self._destildadas())
        self.lista.clear()
        for k in range(max(self._copias(), 0)):
            item = QListWidgetItem(f"Copia {k + 1}")
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked if k in self._suprimidos else Qt.Checked)
            self.lista.addItem(item)

    def cambios(self):
        """Los parámetros para `Boceto.editar_patron`."""
        c = {"simetrico": self.simetrico.isChecked(), "suprimidos": self._destildadas()}
        if not self.rectangular:
            return c | {"cantidad": self.n.value(), "angulo_total": self.total.value()}
        c |= {"cantidad1": self.n1.value(), "distancia1": self.d1.value(), "cantidad2": self.n2.value(),
              "distancia2": self.d2.value(), "modo": self.modo.currentData()}
        for k, combo, ang in ((1, self.linea1, self.ang1), (2, self.linea2, self.ang2)):
            c[f"linea{k}"] = combo.currentData()
            if c[f"linea{k}"] is None:
                a = math.radians(ang.value())
                c[f"dir{k}"] = [math.cos(a), math.sin(a)]
        return c


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

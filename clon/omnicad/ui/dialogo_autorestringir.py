# -*- coding: utf-8 -*-
"""
Diálogo de AutoConstrain (SKT-AUTO-CONSTRAIN): varios resultados sugeridos, deslizador con la cantidad de
restricciones y cotas, tolerancias, datum, «Generar más», «Empezar de nuevo» y quitar una sugerencia.

El diálogo no toca el boceto: calcula con `sugerir_auto_restricciones` (sobre copias) y devuelve las opciones del
resultado elegido (`opciones()`), que el lienzo aplica con `auto_restringir`.
Cada resultado lleva el candado de Fusion (totalmente / parcialmente restringido) y una casilla que lo FIJA:
«Generar más» y «Empezar de nuevo» no descartan los fijados. «Elegir en el lienzo» cierra el diálogo con
`ELEGIR_DATUM`; el lienzo captura el clic en un punto y lo vuelve a abrir con `fijar_datum`.
"""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QApplication, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout,
                               QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton, QSlider,
                               QVBoxLayout)

from ..restricciones import sugerir_auto_restricciones
from .iconos import icono

MAX_DATUMS = 200                # puntos que se ofrecen como datum (los más cercanos al origen)
ELEGIR_DATUM = 2                # código de `exec()`: el usuario quiere elegir el datum con un clic en el lienzo


class DialogoAutoRestringir(QDialog):
    previa = Signal(list)

    def __init__(self, boceto, valores_cotas, datum=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Restringir automáticamente")
        self.setMinimumWidth(520)
        self.b, self.valores = boceto, valores_cotas
        self.pedidos, self.excluidas, self.resultados = 3, set(), []
        self.fijados = []               # resultados con la casilla marcada: sobreviven a recalcular
        self.tol_angulo = QDoubleSpinBox(decimals=2, minimum=0.01, maximum=45.0, singleStep=0.5, suffix=" °")
        self.tol_angulo.setValue(1.0)
        self.tol_distancia = QDoubleSpinBox(decimals=4, minimum=0.0001, maximum=10.0, singleStep=0.001, suffix=" mm")
        self.tol_distancia.setValue(0.001)
        self.datum = QComboBox()
        self.datum.addItem("Automático (origen)", None)
        cerca = sorted((p for p in boceto.puntos if not boceto.puntos[p].proyectado),
                       key=lambda p: (boceto.coords(p)[0] ** 2 + boceto.coords(p)[1] ** 2, p))[:MAX_DATUMS]
        for p in cerca:
            x, y = boceto.coords(p)
            self.datum.addItem(f"Punto {p} ({x:.3g}, {y:.3g})", p)
        if datum in cerca:
            self.datum.setCurrentIndex(self.datum.findData(datum))
        self.lista = QListWidget()
        self.lista.setMaximumHeight(110)
        self.cantidad = QSlider(Qt.Horizontal)
        self.etiqueta_cantidad = QLabel()
        self.detalle = QListWidget()
        self.estado = QLabel()
        generar = QPushButton("Generar más")
        reiniciar = QPushButton("Empezar de nuevo")
        quitar = QPushButton("Quitar la seleccionada")
        botones = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        botones.button(QDialogButtonBox.Ok).setText("Aceptar")
        botones.button(QDialogButtonBox.Cancel).setText("Cancelar")
        self.aceptar = botones.button(QDialogButtonBox.Ok)
        form = QFormLayout()
        form.addRow("Tolerancia de ángulo", self.tol_angulo)
        form.addRow("Tolerancia de distancia", self.tol_distancia)
        elegir = QPushButton("Elegir en el lienzo")
        elegir.setToolTip("Cierra el diálogo, hacé clic en un punto del boceto y vuelve con ese punto como datum.")
        elegir.clicked.connect(lambda: self.done(ELEGIR_DATUM))
        fila_datum = QHBoxLayout()
        fila_datum.addWidget(self.datum, 1)
        fila_datum.addWidget(elegir)
        form.addRow("Datum", fila_datum)
        acciones = QHBoxLayout()
        for w in (generar, reiniciar, quitar):
            acciones.addWidget(w)
        lay = QVBoxLayout(self)
        lay.addLayout(form)
        lay.addWidget(QLabel("Resultados:"))
        lay.addWidget(self.lista)
        lay.addWidget(self.etiqueta_cantidad)
        lay.addWidget(self.cantidad)
        lay.addWidget(self.detalle)
        lay.addWidget(self.estado)
        lay.addLayout(acciones)
        lay.addWidget(botones)
        botones.accepted.connect(self.accept)
        botones.rejected.connect(self.reject)
        generar.clicked.connect(self._generar_mas)
        reiniciar.clicked.connect(self._reiniciar)
        quitar.clicked.connect(self._quitar)
        self.lista.currentRowChanged.connect(self._elegir)
        self.lista.itemChanged.connect(self._fijar)
        self.cantidad.valueChanged.connect(self._mostrar_detalle)
        for w in (self.tol_angulo, self.tol_distancia):
            w.editingFinished.connect(self._calcular)
        self.datum.activated.connect(lambda _=0: self._calcular())
        self._calcular()

    # ---------------------------------------------------------------- cálculo
    def _opciones_base(self):
        return {"tol_angulo": self.tol_angulo.value(), "tol_distancia": self.tol_distancia.value(),
                "datum": self.datum.currentData(), "excluir": set(self.excluidas)}

    def _calcular(self):
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            nuevos = sugerir_auto_restricciones(self.b, self.valores, resultados=self.pedidos,
                                                **self._opciones_base())
        finally:
            QApplication.restoreOverrideCursor()
        vistos = {_firma(r) for r in self.fijados}
        self.resultados = self.fijados + [r for r in nuevos if _firma(r) not in vistos]
        self.lista.blockSignals(True)
        self.lista.clear()
        for r in self.resultados:
            nuevas = sum(s.clase == "restriccion" for s in r.sugerencias)
            item = QListWidgetItem(icono("boceto_bloqueado" if r.totalmente_restringido else "boceto"),
                                   f"{r.nombre}: {nuevas} restricciones, {len(r.sugerencias) - nuevas} cotas — "
                                   + ("totalmente restringido" if r.totalmente_restringido else f"quedan {r.gdl} GDL"))
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if any(r is f for f in self.fijados) else Qt.Unchecked)
            item.setToolTip("Marcá la casilla para fijar el resultado: «Generar más» y «Empezar de nuevo» lo conservan.")
            self.lista.addItem(item)
        self.lista.blockSignals(False)
        self.lista.setCurrentRow(0 if self.resultados else -1)
        self._elegir(0 if self.resultados else -1)

    def _generar_mas(self):
        self.pedidos += 2
        self._calcular()

    def _reiniciar(self):
        self.pedidos, self.excluidas = 3, set()
        self._calcular()

    def _quitar(self):
        fila, r = self.detalle.currentRow(), self.resultado()
        if r is not None and 0 <= fila < len(r.sugerencias):
            self.excluidas.add(r.sugerencias[fila].clave)
            self._calcular()

    def _fijar(self, item):
        r = self.resultados[self.lista.row(item)]
        self.fijados = [f for f in self.fijados if f is not r]
        if item.checkState() == Qt.Checked:
            self.fijados.append(r)

    def fijar_datum(self, pid):
        """Datum elegido con un clic en el lienzo: se suma a la lista si no estaba y se recalcula."""
        if self.datum.findData(pid) < 0:
            x, y = self.b.coords(pid)
            self.datum.addItem(f"Punto {pid} ({x:.3g}, {y:.3g})", pid)
        self.datum.setCurrentIndex(self.datum.findData(pid))
        self._calcular()

    # ---------------------------------------------------------------- selección y resultado
    def resultado(self):
        fila = self.lista.currentRow()
        return self.resultados[fila] if 0 <= fila < len(self.resultados) else None

    def _elegir(self, fila):
        r = self.resultado()
        self.cantidad.blockSignals(True)
        self.cantidad.setRange(0, len(r.sugerencias) if r else 0)
        self.cantidad.setValue(len(r.sugerencias) if r else 0)
        self.cantidad.blockSignals(False)
        self._mostrar_detalle()

    def _mostrar_detalle(self, *_):
        r, k = self.resultado(), self.cantidad.value()
        self.previa.emit(r.sugerencias[:k] if r is not None else [])
        self.detalle.clear()
        if r is None or not r.sugerencias:
            self.etiqueta_cantidad.setText("")
            self.estado.setText("No hay nada para agregar: el boceto ya está restringido o no se detectó nada.")
            self.aceptar.setEnabled(False)
            self.previa.emit([])
            return
        self.etiqueta_cantidad.setText(f"Cantidad de restricciones y cotas: {k} de {len(r.sugerencias)}")
        self.detalle.addItems([s.descripcion for s in r.sugerencias[:k]])
        gdl = r.sugerencias[k - 1].gdl if k else r.gdl_inicial
        self.estado.setText("Totalmente restringido." if gdl == 0 else f"Parcialmente restringido: quedan {gdl} GDL.")
        self.aceptar.setEnabled(k > 0)

    def opciones(self):
        """Opciones de `auto_restringir` que reproducen el resultado elegido con la cantidad del deslizador."""
        r = self.resultado()
        return {**r.opciones, "limite": self.cantidad.value()}


def _firma(resultado):
    """Las sugerencias de un resultado, para no repetir uno fijado al recalcular."""
    return tuple(s.clave for s in resultado.sugerencias)

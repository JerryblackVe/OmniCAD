# -*- coding: utf-8 -*-
"""
Diálogo de AutoConstrain (SKT-AUTO-CONSTRAIN): varios resultados sugeridos, deslizador con la cantidad de
restricciones y cotas, tolerancias, datum, «Generar más», «Empezar de nuevo» y quitar una sugerencia.

El diálogo no toca el boceto: calcula con `sugerir_auto_restricciones` (sobre copias) y devuelve las opciones del
resultado elegido (`opciones()`), que el lienzo aplica con `auto_restringir`.
shortcut: el datum se elige de una lista, no con un clic; ver BOC-5 en docs/seguimiento/faltantes.md.
"""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QApplication, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout,
                               QHBoxLayout, QLabel, QListWidget, QPushButton, QSlider, QVBoxLayout)

from ..restricciones import sugerir_auto_restricciones

MAX_DATUMS = 200                # puntos que se ofrecen como datum (los más cercanos al origen)


class DialogoAutoRestringir(QDialog):
    previa = Signal(list)

    def __init__(self, boceto, valores_cotas, datum=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Restringir automáticamente")
        self.setMinimumWidth(520)
        self.b, self.valores = boceto, valores_cotas
        self.pedidos, self.excluidas, self.resultados = 3, set(), []
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
        form.addRow("Datum", self.datum)
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
            self.resultados = sugerir_auto_restricciones(self.b, self.valores, resultados=self.pedidos,
                                                         **self._opciones_base())
        finally:
            QApplication.restoreOverrideCursor()
        self.lista.blockSignals(True)
        self.lista.clear()
        for r in self.resultados:
            nuevas = sum(s.clase == "restriccion" for s in r.sugerencias)
            self.lista.addItem(f"{r.nombre}: {nuevas} restricciones, {len(r.sugerencias) - nuevas} cotas — "
                               + ("totalmente restringido" if r.totalmente_restringido else f"quedan {r.gdl} GDL"))
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

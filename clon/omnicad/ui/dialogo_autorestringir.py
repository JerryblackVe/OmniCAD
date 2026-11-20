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
from PySide6.QtCore import QPointF, QSize, Qt, Signal
from PySide6.QtGui import QIcon, QPainter, QPen, QPixmap, QPolygonF
from PySide6.QtWidgets import (QApplication, QComboBox, QDialog, QFormLayout,
                               QHBoxLayout, QLabel, QListView, QListWidget, QListWidgetItem, QMenu, QPushButton,
                               QSlider, QToolButton, QVBoxLayout, QWhatsThis)

from .editor_boceto_comun import VIOLETA     # el mismo violeta que la previa del lienzo
from .formulario import NumeroDecimal     # B-202: acepta «0.25» y «0,25»
from ..restricciones import sugerir_auto_restricciones
from ..restricciones.boceto_geometria import puntos_primitiva
from .iconos import icono

MAX_DATUMS = 200                # puntos que se ofrecen como datum (los más cercanos al origen)
TAM_MINIATURA = QSize(120, 90)  # P-186: cada resultado es un mosaico con el boceto dibujado
AYUDA = ("Cada mosaico es una forma de restringir el boceto. Elegí uno, ajustá la cantidad y apretá Aceptar. "
         "Marcá la casilla para conservarlo al generar más.")
ELEGIR_DATUM = 2                # código de `exec()`: el usuario quiere elegir el datum con un clic en el lienzo


class DialogoAutoRestringir(QDialog):
    previa = Signal(list)

    def __init__(self, boceto, valores_cotas, datum=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Restringir automáticamente")
        self.b, self.valores = boceto, valores_cotas
        self.pedidos, self.excluidas, self.resultados = 3, set(), []
        self.fijados = []               # resultados con la casilla marcada: sobreviven a recalcular
        self.tol_angulo = NumeroDecimal(decimals=2, minimum=0.01, maximum=45.0, singleStep=0.5, suffix=" °")
        self.tol_angulo.setValue(1.0)
        self.tol_distancia = NumeroDecimal(decimals=4, minimum=0.0001, maximum=10.0, singleStep=0.001, suffix=" mm")
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
        self.lista.setViewMode(QListView.IconMode)         # mosaico, como Fusion
        self.lista.setIconSize(TAM_MINIATURA)
        self.lista.setResizeMode(QListView.Adjust)
        self.lista.setMovement(QListView.Static)
        self.lista.setWordWrap(True)
        fm = self.fontMetrics()                            # UX-17: el mosaico crece con la letra
        ancho = max(TAM_MINIATURA.width(), fm.horizontalAdvance("Restricciones: 00 /")) + 40
        alto = TAM_MINIATURA.height() + 3 * fm.height() + 20
        self.lista.setGridSize(QSize(ancho, alto))
        self.lista.setMinimumHeight(alto + 10)
        self.lista.setMaximumHeight(2 * alto + 10)
        self.setMinimumWidth(max(520, 3 * ancho + 60, 60 * fm.averageCharWidth()))   # 3 mosaicos en una fila
        self.lista.setContextMenuPolicy(Qt.CustomContextMenu)
        self.mas = QToolButton()                           # ⋮ de Fusion: opciones del resultado elegido
        self.mas.setText("⋮")
        self.mas.setToolTip("Más opciones del resultado elegido")
        self.mas.setPopupMode(QToolButton.InstantPopup)
        self.mas.setMenu(self._menu_mas())
        self.cantidad = QSlider(Qt.Horizontal)
        self.etiqueta_cantidad = QLabel()
        self.detalle = QListWidget()
        self.estado = QLabel()
        generar = QPushButton("Generar más")
        reiniciar = QPushButton("Empezar de nuevo")
        quitar = QPushButton("Quitar la seleccionada")
        self.aceptar = QPushButton("Aceptar")
        self.aceptar.setDefault(True)
        cancelar = QPushButton("Cancelar")
        botones = QHBoxLayout()                              # UX-6: Cancelar a la izquierda, Aceptar abajo a la derecha
        botones.addStretch(1)
        botones.addWidget(cancelar)
        botones.addWidget(self.aceptar)
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
        cabeza = QHBoxLayout()
        cabeza.addWidget(QLabel("Resultados:"), 1)
        ayuda = QToolButton()
        ayuda.setText("?")
        ayuda.setToolTip("Ayuda")
        ayuda.clicked.connect(lambda: QWhatsThis.showText(ayuda.mapToGlobal(ayuda.rect().bottomLeft()), AYUDA, ayuda))
        cabeza.addWidget(ayuda)
        cabeza.addWidget(self.mas)
        lay.addLayout(cabeza)
        lay.addWidget(self.lista)
        lay.addWidget(self.etiqueta_cantidad)
        lay.addWidget(self.cantidad)
        lay.addWidget(self.detalle)
        lay.addWidget(self.estado)
        lay.addLayout(acciones)
        lay.addLayout(botones)
        self.aceptar.clicked.connect(self.accept)
        cancelar.clicked.connect(self.reject)
        generar.clicked.connect(self._generar_mas)
        reiniciar.clicked.connect(self._reiniciar)
        quitar.clicked.connect(self._quitar)
        self.lista.currentRowChanged.connect(self._elegir)
        self.lista.customContextMenuRequested.connect(self._menu_en_mosaico)
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
        trazos = [puntos_primitiva(prim, 24) for c in self.b.curvas.values() for prim in self.b.primitivas(c.id)]
        self.lista.blockSignals(True)
        self.lista.clear()
        for r in self.resultados:
            nuevas = sum(s.clase == "restriccion" for s in r.sugerencias)
            item = QListWidgetItem(QIcon(_miniatura(self.b, r, trazos)),
                                   f"Restricciones: {nuevas} /\nCotas: {len(r.sugerencias) - nuevas} añadidas")
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if any(r is f for f in self.fijados) else Qt.Unchecked)
            item.setToolTip(f"{r.nombre}: " + ("totalmente restringido (candado)." if r.totalmente_restringido
                                               else f"quedan {r.gdl} grados de libertad.")
                            + " Marcá la casilla para fijarlo: «Generar más» y «Empezar de nuevo» lo conservan.")
            self.lista.addItem(item)
        self.lista.blockSignals(False)
        self.lista.setCurrentRow(0 if self.resultados else -1)
        self._elegir(0 if self.resultados else -1)

    def _menu_mas(self):
        menu = QMenu(self)
        menu.addAction("Establecer referencia").triggered.connect(lambda: self.done(ELEGIR_DATUM))
        return menu

    def _menu_en_mosaico(self, pos):
        if self.lista.itemAt(pos) is not None:
            self.lista.setCurrentItem(self.lista.itemAt(pos))
            self._menu_mas().exec(self.lista.viewport().mapToGlobal(pos))

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


def _miniatura(b, r, trazos):
    """Boceto dibujado en gris con lo que agrega el resultado en violeta (cotas como segmentos, restricciones como
    puntos) y el candado de Fusion si queda totalmente restringido."""
    pm = QPixmap(TAM_MINIATURA)
    paleta = QApplication.palette()                       # sigue el tema claro/oscuro
    pm.fill(paleta.base().color())
    xs = [x for t in trazos for x, _ in t] + [b.coords(q)[0] for q in b.puntos]
    ys = [y for t in trazos for _, y in t] + [b.coords(q)[1] for q in b.puntos]
    if xs:
        x0, y0 = min(xs), min(ys)
        esc = min((pm.width() - 16) / ((max(xs) - x0) or 1), (pm.height() - 16) / ((max(ys) - y0) or 1))
        a = lambda x, y: QPointF(8 + (x - x0) * esc, pm.height() - 8 - (y - y0) * esc)  # noqa: E731
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(paleta.windowText().color(), 1.4))
        for t in trazos:
            p.drawPolyline(QPolygonF([a(x, y) for x, y in t]))
        p.setPen(QPen(VIOLETA, 1.6))
        p.setBrush(VIOLETA)
        for s in r.sugerencias:
            ids = [e for e in s.entidades if e in b.puntos]
            if s.clase == "cota" and len(ids) >= 2:
                p.drawLine(a(*b.coords(ids[0])), a(*b.coords(ids[1])))
            else:
                for q in ids[:1]:
                    p.drawEllipse(a(*b.coords(q)), 2.5, 2.5)
        p.end()
    if r.totalmente_restringido:
        pl = icono("boceto_bloqueado").pixmap(20, 20)
        q = QPainter(pm)
        q.drawPixmap(pm.width() - 24, 4, pl)
        q.end()
    return pm

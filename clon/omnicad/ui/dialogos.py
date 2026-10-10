# -*- coding: utf-8 -*-
"""
Diálogos de creación/edición de operaciones y de parámetros.

Cada diálogo arma el "objeto de entrada" de la operación (patrón createInput → add de Fusion,
informe_analisis.md §5): los campos numéricos son EXPRESIONES con unidades que se validan en vivo.
Para editar un paso existente se usa el estado del modelo ANTERIOR a ese paso, como hace Fusion
al editar una feature del timeline.
"""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout,
                               QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMessageBox,
                               QPushButton, QRadioButton, QSpinBox, QTableWidget, QTableWidgetItem, QVBoxLayout)

from ..timeline.operaciones import OPERACIONES_CUERPO, OpPrimitiva
from ..timeline.parametros import ANGULO, ESCALAR, LONGITUD, ErrorExpresion, TablaParametros, validar_nombre
from . import temas

ETIQUETAS_CAMPO = {"ancho": "Ancho (X)", "largo": "Largo (Y)", "alto": "Alto (Z)", "radio": "Radio",
                   "radio_mayor": "Radio mayor", "radio_menor": "Radio menor", "x": "Posición X",
                   "y": "Posición Y", "z": "Posición Z"}


class CampoExpresion(QLineEdit):
    """Campo de texto que evalúa la expresión en vivo y se pone rojo si no es válida."""
    valido_cambio = Signal(bool)

    def __init__(self, texto, tabla, tipo=LONGITUD, parent=None):
        super().__init__(str(texto), parent)
        self.tabla, self.tipo = tabla, tipo
        self.textChanged.connect(self._validar)
        self._validar()

    def _validar(self):
        try:
            v = self.tabla.evaluar(self.text(), self.tipo)
            unidad = "°" if self.tipo == ANGULO else ("" if self.tipo == ESCALAR else " mm")
            self.setToolTip(f"= {v:.4g}{unidad}")
            self.setStyleSheet("")
            self.valido = True
        except ErrorExpresion as e:
            self.setToolTip(str(e))
            self.setStyleSheet(f"background: {temas.color('campo_error')};")
            self.valido = False
        self.valido_cambio.emit(self.valido)


def _combo(opciones, actual=None):
    c = QComboBox()
    for clave, texto in opciones.items():
        c.addItem(texto, clave)
    if actual is not None:
        i = c.findData(actual)
        if i >= 0:
            c.setCurrentIndex(i)
    return c


def _combo_cuerpos(estado, actual="", vacio="Automático"):
    c = QComboBox()
    if vacio is not None:
        c.addItem(vacio, "")
    for cuerpo in estado.cuerpos.values():
        c.addItem(cuerpo.nombre, cuerpo.id)
    _seleccionar_o_conservar(c, actual)
    return c


def _seleccionar_o_conservar(combo, actual):
    """Selecciona `actual`. Si ya no existe (paso con error o retrocedido), lo agrega marcado como
    no disponible en vez de cambiar en silencio a otra opción."""
    if not actual:
        return
    i = combo.findData(actual)
    if i < 0:
        combo.addItem(f"⚠ {actual} (no disponible)", actual)
        i = combo.count() - 1
    combo.setCurrentIndex(i)


class _DialogoBase(QDialog):
    def __init__(self, titulo, parent=None):
        super().__init__(parent)
        self.setWindowTitle(titulo)
        self.setMinimumWidth(420)
        self.form = QFormLayout()
        self.botones = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.botones.button(QDialogButtonBox.Ok).setText("Aceptar")
        self.botones.button(QDialogButtonBox.Cancel).setText("Cancelar")
        self.botones.accepted.connect(self._aceptar)
        self.botones.rejected.connect(self.reject)
        self.lay = QVBoxLayout(self)
        self.lay.addLayout(self.form)
        self.lay.addWidget(self.botones)
        self.campos = []

    def campo(self, etiqueta, texto, tabla, tipo=LONGITUD):
        c = CampoExpresion(texto, tabla, tipo)
        self.campos.append(c)
        self.form.addRow(etiqueta, c)
        c.valido_cambio.connect(self._actualizar_aceptar)
        self._actualizar_aceptar()
        return c

    def _actualizar_aceptar(self, *_):
        self.botones.button(QDialogButtonBox.Ok).setEnabled(all(c.valido for c in self.campos))

    def _aceptar(self):
        if any(not c.valido for c in self.campos):
            QMessageBox.warning(self, "Expresión inválida", "Hay campos con expresiones inválidas (en rojo).")
            return
        self.accept()


class DialogoRejilla(QDialog):
    """Parámetros de rejilla (Rejilla y forzados): adaptativa o fija con espaciado y subdivisiones."""

    def __init__(self, fija=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Parámetros de rejilla")
        self.adaptativa = QRadioButton("Adaptativa (cambia con el zoom)")
        self.fija = QRadioButton("Fija")
        self.espaciado = QDoubleSpinBox(decimals=3, minimum=0.001, maximum=100000.0, suffix=" mm")
        self.subdivisiones = QSpinBox(minimum=1, maximum=1000)
        mayor, sub = fija if fija else (10.0, 5)
        self.espaciado.setValue(mayor)
        self.subdivisiones.setValue(sub)
        (self.fija if fija else self.adaptativa).setChecked(True)
        form = QFormLayout()
        form.addRow(self.adaptativa)
        form.addRow(self.fija)
        form.addRow("Espaciado de la rejilla mayor", self.espaciado)
        form.addRow("Subdivisiones de la rejilla menor", self.subdivisiones)
        botones = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        botones.button(QDialogButtonBox.Ok).setText("Aceptar")
        botones.button(QDialogButtonBox.Cancel).setText("Cancelar")
        botones.accepted.connect(self.accept)
        botones.rejected.connect(self.reject)
        lay = QVBoxLayout(self)
        lay.addLayout(form)
        lay.addWidget(botones)

    def valor(self):
        return (self.espaciado.value(), self.subdivisiones.value()) if self.fija.isChecked() else None


class DialogoPrimitiva(_DialogoBase):
    def __init__(self, doc, forma="caja", op=None, parent=None):
        forma = op.p["forma"] if op else forma
        super().__init__(OpPrimitiva.ETIQUETAS[forma], parent)
        self.doc, self.op, self.forma = doc, op, forma
        estado = doc.estado_en(doc.indice(op.id)) if op else doc.estado_final
        p = op.p if op else OpPrimitiva.PARAMS
        self.valores = {}
        for clave in OpPrimitiva.CAMPOS[forma] + ["x", "y", "z"]:
            self.valores[clave] = self.campo(ETIQUETAS_CAMPO[clave], p[clave], doc.parametros)
        self.operacion = _combo(OPERACIONES_CUERPO, p["operacion"])
        self.form.addRow("Operación", self.operacion)
        self.objetivo = _combo_cuerpos(estado, p.get("objetivo", ""))
        self.form.addRow("Cuerpo objetivo", self.objetivo)
        nota = {"caja": "La posición es la esquina mínima.", "cilindro": "La posición es el centro de la base (eje Z).",
                "esfera": "La posición es el centro.", "toroide": "La posición es el centro (eje Z)."}[forma]
        self.caja_centrada = bool(op and op.p.get("caja_centrada"))      # cajas creadas con create_box
        if forma == "caja" and self.caja_centrada:
            nota = "La posición es el centro de la base."
        self.form.addRow("", QLabel(nota))

    def crear_operacion(self):
        params = {k: c.text().strip() for k, c in self.valores.items()}
        params.update(forma=self.forma, operacion=self.operacion.currentData(), objetivo=self.objetivo.currentData() or "",
                      caja_centrada=self.caja_centrada)
        if self.op:
            return OpPrimitiva(self.op.id, self.op.nombre, self.op.suprimida, **params)
        return OpPrimitiva(self.doc.nuevo_id(), **params)


class DialogoParametros(QDialog):
    """Tabla de parámetros de usuario (equivalente al diálogo "Change Parameters" de Fusion)."""
    COLUMNAS = ["Nombre", "Expresión", "Tipo", "Valor", "Comentario"]
    NOMBRES_TIPO = {LONGITUD: "Longitud (mm)", ANGULO: "Ángulo (°)", ESCALAR: "Sin unidad"}

    def __init__(self, tabla, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Parámetros")
        self.resize(760, 420)
        self.tabla_qt = QTableWidget(0, len(self.COLUMNAS))
        self.tabla_qt.setHorizontalHeaderLabels(self.COLUMNAS)
        self.tabla_qt.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.error = QLabel()                 # antes de cargar filas: cada fila recalcula y escribe acá
        temas.poner_rol(self.error, "error")
        self.resultado = None
        for p in tabla:
            self._agregar_fila(p.nombre, p.expresion, p.tipo, p.comentario)
        self.tabla_qt.itemChanged.connect(lambda *_: self._recalcular())
        agregar, quitar = QPushButton("Agregar"), QPushButton("Quitar")
        agregar.clicked.connect(lambda: self._agregar_fila(f"p{self.tabla_qt.rowCount() + 1}", "10 mm", LONGITUD, ""))
        quitar.clicked.connect(lambda: self.tabla_qt.removeRow(self.tabla_qt.currentRow()))
        botones = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        botones.accepted.connect(self._aceptar)
        botones.rejected.connect(self.reject)
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("Usá los nombres en cualquier cota o medida, p. ej. «ancho / 2» o «alto + 5 mm»."))
        lay.addWidget(self.tabla_qt)
        exportar, importar = QPushButton("Exportar parámetros…"), QPushButton("Importar parámetros…")
        exportar.clicked.connect(self._exportar)
        importar.clicked.connect(self._importar)
        fila = QHBoxLayout()
        fila.addWidget(agregar)
        fila.addWidget(quitar)
        fila.addStretch()
        fila.addWidget(importar)
        fila.addWidget(exportar)
        lay.addLayout(fila)
        lay.addWidget(self.error)
        lay.addWidget(botones)
        self.resultado = None
        self._recalcular()

    # Formato CSV de Fusion (Import/Export Parameters [SLD-IMPORT-EXPORT-PARAMETERS]): Name, Unit,
    # Expression, Value, Comments; la unidad dice el tipo (mm → longitud, deg → ángulo, vacío → sin unidad).
    UNIDADES_CSV = {LONGITUD: "mm", ANGULO: "deg", ESCALAR: ""}

    def filas_csv(self):
        self._recalcular()
        if self.resultado is None:
            raise ErrorExpresion(self.error.text() or "Hay parámetros inválidos.")
        valores = self.resultado.valores()
        return [[p.nombre, self.UNIDADES_CSV.get(p.tipo, ""), p.expresion, f"{valores[p.nombre]:.6g}", p.comentario]
                for p in self.resultado]

    def _exportar(self):
        import csv
        from PySide6.QtWidgets import QFileDialog
        try:
            filas = self.filas_csv()
        except ErrorExpresion as e:
            QMessageBox.warning(self, "Parámetros inválidos", str(e))
            return
        ruta, _ = QFileDialog.getSaveFileName(self, "Exportar parámetros", "parametros.csv", "CSV (*.csv)")
        if ruta:
            with open(ruta, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["Name", "Unit", "Expression", "Value", "Comments"])
                w.writerows(filas)

    def importar_csv(self, ruta):
        """Agrega o reemplaza (por nombre) los parámetros del CSV. Devuelve cuántos importó."""
        import csv
        tipos = {"mm": LONGITUD, "cm": LONGITUD, "m": LONGITUD, "in": LONGITUD, "deg": ANGULO, "rad": ANGULO, "": ESCALAR}
        existentes = {self._texto(f, 0): f for f in range(self.tabla_qt.rowCount())}
        n = 0
        with open(ruta, newline="", encoding="utf-8-sig") as f:
            for fila in csv.DictReader(f):
                nombre = (fila.get("Name") or fila.get("Nombre") or "").strip()
                expresion = (fila.get("Expression") or fila.get("Expresión") or "").strip()
                if not nombre or not expresion:
                    continue
                tipo = tipos.get((fila.get("Unit") or fila.get("Unidad") or "").strip().lower(), LONGITUD)
                comentario = (fila.get("Comments") or fila.get("Comentario") or "").strip()
                if nombre in existentes:
                    r = existentes[nombre]
                    self.tabla_qt.item(r, 1).setText(expresion)
                    self.tabla_qt.cellWidget(r, 2).setCurrentIndex(max(self.tabla_qt.cellWidget(r, 2).findData(tipo), 0))
                    self.tabla_qt.item(r, 4).setText(comentario)
                else:
                    self._agregar_fila(nombre, expresion, tipo, comentario)
                n += 1
        self._recalcular()
        return n

    def _importar(self):
        from PySide6.QtWidgets import QFileDialog
        ruta, _ = QFileDialog.getOpenFileName(self, "Importar parámetros", "", "CSV (*.csv)")
        if ruta:
            try:
                n = self.importar_csv(ruta)
                self.error.setText(f"Se importaron {n} parámetro(s).") if not self.error.text() else None
            except (OSError, ValueError) as e:
                QMessageBox.warning(self, "No se pudo importar", str(e))

    def _agregar_fila(self, nombre, expresion, tipo, comentario):
        self.tabla_qt.blockSignals(True)
        f = self.tabla_qt.rowCount()
        self.tabla_qt.insertRow(f)
        self.tabla_qt.setItem(f, 0, QTableWidgetItem(nombre))
        self.tabla_qt.setItem(f, 1, QTableWidgetItem(expresion))
        combo = _combo(self.NOMBRES_TIPO, tipo)
        combo.currentIndexChanged.connect(lambda *_: self._recalcular())
        self.tabla_qt.setCellWidget(f, 2, combo)
        valor = QTableWidgetItem("")
        valor.setFlags(valor.flags() & ~Qt.ItemIsEditable)
        self.tabla_qt.setItem(f, 3, valor)
        self.tabla_qt.setItem(f, 4, QTableWidgetItem(comentario))
        self.tabla_qt.blockSignals(False)
        self._recalcular()

    def _texto(self, fila, columna):
        item = self.tabla_qt.item(fila, columna)
        return item.text().strip() if item else ""

    def _leer(self):
        datos = []
        for f in range(self.tabla_qt.rowCount()):
            datos.append({"nombre": self._texto(f, 0), "expresion": self._texto(f, 1),
                          "tipo": self.tabla_qt.cellWidget(f, 2).currentData(), "comentario": self._texto(f, 4)})
        if len({d["nombre"] for d in datos}) != len(datos):
            raise ErrorExpresion("Hay nombres repetidos.")
        for d in datos:
            validar_nombre(d["nombre"])
        # Se valida todo junto (no fila por fila): un parámetro puede usar otro de más abajo.
        return TablaParametros.desde_lista(datos)

    def _recalcular(self):
        self.tabla_qt.blockSignals(True)
        try:
            t = self._leer()
            valores = t.valores()
            for f in range(self.tabla_qt.rowCount()):
                self.tabla_qt.item(f, 3).setText(f"{valores[self.tabla_qt.item(f, 0).text().strip()]:.4g}")
            self.error.setText("")
            self.resultado = t
        except (ErrorExpresion, KeyError, AttributeError) as e:
            self.error.setText(f"⚠ {e}")
            self.resultado = None
        finally:
            self.tabla_qt.blockSignals(False)

    def _aceptar(self):
        self._recalcular()
        if self.resultado is None:
            QMessageBox.warning(self, "Parámetros inválidos", self.error.text())
            return
        self.accept()

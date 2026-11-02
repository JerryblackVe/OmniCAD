# -*- coding: utf-8 -*-
"""Parámetros (Change Parameters de Fusion, artículos `Parameters in Fusion` y `Parameters reference`).

Diálogo no modal: el modelo se ve detrás y, con Cálculo automático, cada cambio se aplica. Se trabaja sobre una copia de
la tabla, así un valor en rojo o lo pendiente con la casilla apagada no tocan el documento. Todo lo que se hace mientras
está abierto es un solo paso de deshacer.
"""
from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QHBoxLayout,
                               QLabel, QLineEdit, QListWidget, QListWidgetItem, QPushButton, QStyledItemDelegate,
                               QToolButton, QTreeWidget, QTreeWidgetItem, QVBoxLayout)

from .. import api
from ..api.errores import ErrorAPI
from ..api.herramientas_parametros import filtrar_y_ordenar, info_parametros, valor_visible
from ..api.herramientas_parametros_csv import importar_filas, leer_csv
from ..timeline.documento import ErrorDocumento
from ..timeline.parametros import TEXTO, ErrorExpresion, TablaParametros, tipo_de_unidad
from ..timeline.unidades import FAMILIAS
from . import temas
from .campo_expresion import autocompletar, nombres_sugeridos
from .iconos import icono

PARAMETRO, NOMBRE, UNIDAD, EXPRESION, VALOR, COMENTARIOS = range(6)
COLUMNAS = ["Parámetro", "Nombre", "Unidad", "Expresión", "Valor", "Comentarios"]
ORDEN_COLUMNA = {NOMBRE: "name", UNIDAD: "unit", EXPRESION: "expression", VALOR: "value", COMENTARIOS: "comment"}
SIN_UNIDAD, TEXTO_UNIDAD = "Sin unidad", "Text"
LISTA_UNIDADES = [SIN_UNIDAD, TEXTO_UNIDAD, "mm", "cm", "m", "in", "ft", "deg", "rad"]
LISTA_UNIDADES += [u for _, unidades in FAMILIAS.values() for u in unidades if u not in LISTA_UNIDADES]
ROL = Qt.UserRole


def _copia(tabla):
    return TablaParametros.desde_lista(tabla.a_lista())


def _a_unidad(texto):
    """Lo que dice la columna Unidad a lo que entiende la tabla."""
    return {SIN_UNIDAD: "", TEXTO_UNIDAD: "text"}.get(texto.strip(), texto.strip())


def _rotulo_unidad(fila):
    return TEXTO_UNIDAD if fila["kind"] == "text" else fila["unit"] or SIN_UNIDAD


def texto_valor(fila):
    """El valor entero con su unidad, sin notación científica (B-143): 12345,678 mm."""
    v = fila["value"]
    if v is None:
        return "—"
    if isinstance(v, str):
        return v
    numero = f"{v:.6f}".rstrip("0").rstrip(".").replace(".", ",")
    return f"{numero} {fila['unit']}".strip()


class _Delegado(QStyledItemDelegate):
    """Qué se edita en cada columna: la Unidad en una lista, la Expresión con sugerencias, el resto en texto."""

    def __init__(self, dialogo):
        super().__init__(dialogo)
        self.dialogo = dialogo

    def createEditor(self, padre, opcion, indice):
        d, columna = self.dialogo, indice.column()
        nombre = d.arbol.itemFromIndex(indice).data(0, ROL)
        if nombre is None or columna in (PARAMETRO, VALOR) or (columna == UNIDAD and not d.es_de_usuario(nombre)):
            return None
        d.editando = True
        if columna == UNIDAD:
            combo = QComboBox(padre)
            combo.setEditable(True)
            combo.addItems(LISTA_UNIDADES)
            return combo
        editor = super().createEditor(padre, opcion, indice)
        if columna == EXPRESION:
            autocompletar(editor, lambda: nombres_sugeridos(d.tabla))
        return editor


class DialogoNuevoParametro(QDialog):
    """Agregar parámetro de usuario: Nombre, Unidad, Expresión, Valor calculado y Comentarios."""

    def __init__(self, tabla, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Agregar parámetro de usuario")
        self.setWindowIcon(icono("parametros"))
        self.tabla = _copia(tabla)
        self.nombre, self.expresion, self.comentario = QLineEdit(), QLineEdit(), QLineEdit()
        self.unidad = QComboBox(editable=True)
        self.unidad.addItems(LISTA_UNIDADES)
        self.unidad.setCurrentText("mm")
        self.valor = QLabel("—")
        self.error = QLabel(wordWrap=True)
        temas.poner_rol(self.error, "error")
        form = QFormLayout(self)
        for etiqueta, campo in (("Nombre", self.nombre), ("Unidad", self.unidad), ("Expresión", self.expresion),
                                ("Valor calculado", self.valor), ("Comentarios", self.comentario)):
            form.addRow(etiqueta, campo)
        form.addRow(self.error)
        self.botones = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.botones.button(QDialogButtonBox.Ok).setText("Aceptar")
        self.botones.button(QDialogButtonBox.Cancel).setText("Cancelar")
        self.botones.accepted.connect(self.accept)
        self.botones.rejected.connect(self.reject)
        form.addRow(self.botones)
        autocompletar(self.expresion, lambda: nombres_sugeridos(self.tabla))
        for senal in (self.nombre.textChanged, self.expresion.textChanged, self.unidad.currentTextChanged):
            senal.connect(self._recalcular)
        self._recalcular()

    def datos(self):
        unidad = _a_unidad(self.unidad.currentText())
        return {"nombre": self.nombre.text().strip(), "expresion": self.expresion.text(), "tipo": tipo_de_unidad(unidad),
                "comentario": self.comentario.text(), "unidad": None if unidad == "text" else unidad}

    def _recalcular(self):
        try:
            d = self.datos()
            prueba = _copia(self.tabla)
            prueba.agregar(d["nombre"], d["expresion"], d["tipo"], d["comentario"], d["unidad"])
            p = prueba.obtener(d["nombre"])
            self.valor.setText(texto_valor({"value": valor_visible(p, prueba.valores()), "unit": "" if p.tipo == TEXTO else p.texto_unidad}))
            self.error.setText("")
            valido = True
        except ErrorExpresion as e:
            self.valor.setText("—")
            self.error.setText(f"⚠ {e}" if self.nombre.text().strip() and self.expresion.text().strip() else "")
            valido = False
        self.botones.button(QDialogButtonBox.Ok).setEnabled(valido)


class DialogoImportarParametros(QDialog):
    """Parámetros seleccionados: una casilla por parámetro del CSV, todas marcadas."""

    def __init__(self, filas, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Parámetros seleccionados")
        self.setWindowIcon(icono("parametros_importar"))
        self.filas = filas
        self.lista = QListWidget()
        for f in filas:
            item = QListWidgetItem(f"{f['nombre']}   {f.get('unidad', '')}   {f['expresion']}".replace("      ", "   "))
            item.setCheckState(Qt.Checked)
            self.lista.addItem(item)
        botones = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        botones.button(QDialogButtonBox.Ok).setText("Importar")
        botones.button(QDialogButtonBox.Cancel).setText("Cancelar")
        botones.accepted.connect(self.accept)
        botones.rejected.connect(self.reject)
        v = QVBoxLayout(self)
        v.addWidget(QLabel("Desmarcá los parámetros que no quieras importar."))
        v.addWidget(self.lista)
        v.addWidget(botones)

    def elegidas(self):
        return [f for i, f in enumerate(self.filas) if self.lista.item(i).checkState() == Qt.Checked]


class DialogoParametros(QDialog):
    aplicado = Signal()               # el documento recibió los cambios

    def __init__(self, doc, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Parámetros")
        self.setWindowIcon(icono("parametros"))
        self.setModal(False)
        self.resize(900, 460)
        self.doc, self.tabla = doc, _copia(doc.parametros)
        self.editando = self._aplicando = self._pendiente = self._terminado = False
        self._marca_deshacer = len(doc._deshacer)
        self._orden = ("timeline", False)
        self._cerrados = set()        # grupos plegados por la persona: sobreviven a repoblar la tabla
        self._invalidas = {}          # (nombre, columna) → lo que se escribió y no vale: queda en rojo en su celda
        self._poblando = False
        self.dlg_nuevo = self.dlg_importar = None
        self._reloj = QTimer(self, singleShot=True, interval=250)
        self._reloj.timeout.connect(self._aplicar)
        self._armar()
        doc.suscribir(self._doc_cambio)
        self._poblar()

    # ------------------------------------------------------------ armado
    def _boton(self, nombre_icono, ayuda, al_pulsar=None, alternable=False):
        b = QToolButton(checkable=alternable, toolTip=ayuda)
        b.setIcon(icono(nombre_icono))
        if al_pulsar:
            b.clicked.connect(al_pulsar)
        return b

    def _armar(self):
        self.b_orden = self._boton("parametros", "Ordenar entradas de tabla de parámetros en orden de secuencia temporal",
                                   self._orden_temporal, alternable=True)
        self.b_orden.setChecked(True)
        self.b_usuario = self._boton("parametro_usuario", "Filtrar parámetros de usuario", self._poblar, alternable=True)
        self.b_favoritos = self._boton("estrella", "Filtrar parámetros favoritos", self._poblar, alternable=True)
        self.busqueda = QLineEdit(placeholderText="Filtrar todos los parámetros", clearButtonEnabled=True)
        self.busqueda.textChanged.connect(self._poblar)
        self.b_mas = self._boton("mas", "Agregar parámetro de usuario", self._nuevo)
        self.b_copiar = self._boton("copiar", "Copiar el parámetro seleccionado", self._copiar)
        self.b_borrar = self._boton("papelera", "Borrar el parámetro seleccionado", self._borrar)
        self.b_importar = self._boton("parametros_importar", "Importar parámetros", self._importar)
        self.b_exportar = self._boton("parametros_exportar", "Exportar parámetros", self._exportar)
        arriba = QHBoxLayout()
        for w in (self.b_orden, self.b_usuario, self.b_favoritos):
            arriba.addWidget(w)
        arriba.addWidget(self.busqueda, 1)
        for w in (self.b_mas, self.b_copiar, self.b_borrar, self.b_importar, self.b_exportar):
            arriba.addWidget(w)
        self.arbol = QTreeWidget(columnCount=len(COLUMNAS))
        self.arbol.setHeaderLabels(COLUMNAS)
        self.arbol.setEditTriggers(QTreeWidget.DoubleClicked | QTreeWidget.SelectedClicked | QTreeWidget.EditKeyPressed)
        self.arbol.setItemDelegate(_Delegado(self))
        self.arbol.itemDelegate().closeEditor.connect(self._editor_cerrado)
        self.arbol.itemChanged.connect(self._editar)
        self.arbol.itemClicked.connect(self._clic)
        self.arbol.itemCollapsed.connect(lambda i: self._cerrados.add(i.text(PARAMETRO)))
        self.arbol.itemExpanded.connect(lambda i: self._cerrados.discard(i.text(PARAMETRO)))
        self.arbol.itemSelectionChanged.connect(self._actualizar_botones)
        self.arbol.header().setSectionsClickable(True)
        self.arbol.header().sectionClicked.connect(self._ordenar_por)
        self.arbol.setColumnWidth(PARAMETRO, 230)
        self.error = QLabel(wordWrap=True)
        temas.poner_rol(self.error, "error")
        self.automatico = QCheckBox("Cálculo automático", checked=True)
        self.automatico.toggled.connect(self._automatico_cambiado)
        self.b_aplicar = QPushButton("Aplicar", visible=False)
        self.b_aplicar.clicked.connect(self._aplicar)
        self.b_info = self._boton("info", "Información", alternable=True)
        self.info = QLabel("Los parámetros de usuario y del modelo se citan por nombre en cualquier campo. Clic en la "
                           "estrella: favorito. Doble clic en una celda: editar.", wordWrap=True, visible=False)
        self.b_info.toggled.connect(self.info.setVisible)
        self.b_aceptar = QPushButton("Aceptar", default=True)
        self.b_aceptar.clicked.connect(self._aceptar)
        abajo = QHBoxLayout()
        abajo.addWidget(self.automatico)
        abajo.addStretch(1)
        abajo.addWidget(self.b_info)
        abajo.addWidget(self.b_aplicar)
        abajo.addWidget(self.b_aceptar)
        v = QVBoxLayout(self)
        v.addLayout(arriba)
        v.addWidget(self.arbol, 1)
        v.addWidget(self.info)
        v.addWidget(self.error)
        v.addLayout(abajo)

    # ------------------------------------------------------------ tabla
    def es_de_usuario(self, nombre):
        return nombre in self.tabla and "source" not in self._filas.get(nombre, {"source": ""})

    def _grupo(self, padre, titulo, nombre_icono=None):
        item = QTreeWidgetItem(padre, [titulo])
        if nombre_icono:
            item.setIcon(0, icono(nombre_icono))
        item.setExpanded(titulo not in self._cerrados)
        return item

    def _fila(self, padre, f):
        item = QTreeWidgetItem(padre, [f.get("role") or f.get("rol_boceto", ""), f["name"], _rotulo_unidad(f),
                                       f["expression"], texto_valor(f), f["comment"]])
        item.setData(0, ROL, f["name"])
        item.setFlags(item.flags() | Qt.ItemIsEditable)
        item.setIcon(0, icono("estrella" if f.get("favorite") else "estrella_vacia"))
        for (nombre, columna), texto in self._invalidas.items():
            if nombre == f["name"]:
                item.setText(columna, texto)
                item.setForeground(columna, QColor(temas.color("error")))
        return item

    def _poblar(self):
        if self.editando:             # no se le saca la celda de abajo de los dedos: `_editor_cerrado` vuelve a llamar
            return
        self._poblando = True
        self._invalidas = {k: v for k, v in self._invalidas.items() if k[0] in self.tabla}    # de una fila que ya no está
        seleccion = self._seleccionado()
        filas = info_parametros(self.doc, self.tabla)
        self._filas = {f["name"]: f for f in filas}
        for f in filas:
            if f.get("source") == "sketch":
                f["rol_boceto"] = "Cota"
        filas = filtrar_y_ordenar(filas, self.b_favoritos.isChecked(), self.b_usuario.isChecked(), self.busqueda.text(),
                                  *self._orden)
        pasos = {o.id: o.nombre for o in self.doc.operaciones}
        self.arbol.clear()
        favoritos = self._grupo(self.arbol, "Favoritos", "estrella")
        usuario = self._grupo(self.arbol, "Parámetros de usuario", "parametro_usuario")
        modelo = self._grupo(self.arbol, "Parámetros del modelo", "cuerpo")
        operaciones = {}
        for f in filas:
            if f.get("favorite"):
                self._fila(favoritos, f)
            if "source" not in f:
                self._fila(usuario, f)
                continue
            clave = f.get("feature") or f.get("sketch")
            if clave not in operaciones:
                operaciones[clave] = self._grupo(modelo, pasos.get(clave, clave))
            self._fila(operaciones[clave], f)
        for nombre in (seleccion,) if seleccion and not self._invalidas else ():      # el color de selección taparía el rojo
            for item in self.arbol.findItems(nombre, Qt.MatchExactly | Qt.MatchRecursive, NOMBRE)[:1]:
                self.arbol.setCurrentItem(item)
        self.arbol.resizeColumnToContents(NOMBRE)
        self._poblando = False
        self._actualizar_botones()

    def _seleccionado(self):
        item = self.arbol.currentItem() if self.arbol.selectedItems() else None
        return item.data(0, ROL) if item is not None else None

    def _actualizar_botones(self):
        nombre = self._seleccionado()
        de_usuario = nombre is not None and self.es_de_usuario(nombre)
        self.b_copiar.setEnabled(de_usuario)
        self.b_borrar.setEnabled(de_usuario)

    def _clic(self, item, columna):
        nombre = item.data(0, ROL)
        if nombre is not None and columna == PARAMETRO:        # la estrella
            self.tabla.modificar(nombre, favorito=not self.tabla.obtener(nombre).favorito)
            self._cambio()

    def _ordenar_por(self, columna):
        if columna == PARAMETRO:
            self._orden_temporal()
            return
        clave = ORDEN_COLUMNA[columna]
        self._orden = (clave, self._orden == (clave, False))
        self.b_orden.setChecked(False)
        self._poblar()

    def _orden_temporal(self):
        self._orden = ("timeline", False)
        self.b_orden.setChecked(True)
        self._poblar()

    def _editor_cerrado(self, *_):
        self.editando = False
        QTimer.singleShot(0, self._poblar)

    def _editar(self, item, columna):
        nombre = item.data(0, ROL)
        if self._poblando or nombre is None:
            return
        texto = item.text(columna)
        try:
            if columna == NOMBRE:
                if texto.strip() != nombre:
                    self._renombrar(nombre, texto.strip())
                    nombre = texto.strip()
            elif columna == EXPRESION:
                self.tabla.modificar(nombre, texto if self.tabla.obtener(nombre).tipo == TEXTO else texto.strip())
            elif columna == UNIDAD:
                self.tabla.modificar(nombre, unidad=_a_unidad(texto))
            elif columna == COMENTARIOS:
                self.tabla.modificar(nombre, comentario=texto)
        except (ErrorExpresion, ErrorDocumento) as e:
            self._invalidas[(nombre, columna)] = texto
            self._avisar(e)
            QTimer.singleShot(0, self._poblar)
            return
        for clave in [c for c in self._invalidas if c[1] == columna and c[0] == nombre]:
            del self._invalidas[clave]
        self._cambio()

    def _renombrar(self, viejo, nuevo):
        """El nombre va directo al documento: cambia pasos y cotas, no el modelo, y no depende de la casilla. Uno agregado
        y sin aplicar todavía está solo en la copia."""
        tabla = _copia(self.tabla)
        tabla.renombrar(viejo, nuevo)
        if viejo in self.doc.parametros:
            self._aplicando = True
            try:
                self.doc.renombrar_parametro(viejo, nuevo)
            finally:
                self._aplicando = False
        self.tabla = tabla
        self.aplicado.emit()

    def _avisar(self, e=""):
        self.error.setText(f"⚠ {e}" if e else "")

    def _cambio(self):
        """Algo cambió en la copia: a la tabla y, con la casilla, al modelo."""
        self._avisar()
        self._pendiente = True
        self.b_aplicar.setEnabled(True)
        if self.automatico.isChecked():
            self._reloj.start()
        QTimer.singleShot(0, self._poblar)

    def _automatico_cambiado(self, encendido):
        self.b_aplicar.setVisible(not encendido)          # capturas de Fusion: encendida no hay Aplicar
        if encendido and self._pendiente:
            self._reloj.start()

    def _aplicar(self):
        """Los cambios al documento. Un documento grande calcula en otro proceso y la ventana sigue viva (`al_esperar`);
        si llega otro cambio durante ese cálculo, se reintenta al terminar."""
        if not self._pendiente:
            return
        self._aplicando = True
        try:
            self.doc.aplicar_parametros(_copia(self.tabla))
        except ErrorDocumento as e:
            if "Ya hay un cálculo" in str(e):
                self._reloj.start()
            else:
                self._avisar(e)
            return
        except ErrorExpresion as e:
            self._avisar(e)
            return
        finally:
            self._aplicando = False
        self._pendiente = False
        self.b_aplicar.setEnabled(False)
        self.tabla = _copia(self.doc.parametros)
        self.aplicado.emit()
        self._poblar()

    def _doc_cambio(self):
        """El documento cambió por otro lado (deshacer, un comando): la tabla lo sigue. Lo que no se aplicó se armó sobre
        los valores de antes y pisaría ese cambio: se descarta y se avisa."""
        if self._aplicando:
            return
        if self._pendiente:
            self._pendiente = False
            self.b_aplicar.setEnabled(False)
            self._avisar("El documento cambió: se descartó lo que no se había aplicado.")
        self.tabla = _copia(self.doc.parametros)
        self._poblar()

    # ------------------------------------------------------------ botones
    def _nuevo(self):
        self.dlg_nuevo = DialogoNuevoParametro(self.tabla, self)
        self.dlg_nuevo.accepted.connect(lambda: self._agregar(self.dlg_nuevo.datos()))
        self.dlg_nuevo.open()

    def _agregar(self, d):
        self.tabla.agregar(d["nombre"], d["expresion"], d["tipo"], d["comentario"], d["unidad"])
        self._cambio()

    def _copiar(self):
        p = self.tabla.obtener(self._seleccionado())
        base, n = f"{p.nombre}_copia", 1
        nombre = base
        while nombre in self.tabla:
            n += 1
            nombre = f"{base}{n}"
        self.tabla.agregar(nombre, p.expresion, p.tipo, p.comentario, p.unidad)
        self._cambio()

    def _borrar(self):
        nombre = self._seleccionado()
        try:
            if nombre in self.doc.parametros_usados():
                raise ErrorExpresion(f"No se puede borrar '{nombre}': lo usan pasos del modelo.")
            self.tabla.eliminar(nombre)
        except ErrorExpresion as e:
            self._avisar(e)
            return
        self._cambio()

    def _exportar(self):
        ruta, _ = QFileDialog.getSaveFileName(self, "Exportar parámetros", "parametros.csv", "CSV (*.csv)")
        if ruta:
            self.exportar_csv(ruta)

    def exportar_csv(self, ruta):
        r = api.llamar(api.Sesion(self.doc), "export_parameters", {"path": ruta, "overwrite": True})
        self._avisar("" if r["ok"] else r["mensaje"])
        return r["ok"]

    def _importar(self):
        ruta, _ = QFileDialog.getOpenFileName(self, "Importar parámetros", "", "CSV (*.csv)")
        if ruta:
            self.elegir_importacion(ruta)

    def elegir_importacion(self, ruta):
        """Lee el CSV y abre Parámetros seleccionados."""
        try:
            filas = leer_csv(ruta)
        except (OSError, ErrorAPI) as e:
            self._avisar(e)
            return
        self.dlg_importar = DialogoImportarParametros(filas, self)
        self.dlg_importar.accepted.connect(lambda: self.importar(self.dlg_importar.elegidas()))
        self.dlg_importar.open()

    def importar(self, filas):
        if not filas:
            return
        self._aplicar()
        self._aplicando = True
        try:
            importar_filas(self.doc, filas)
        except (ErrorExpresion, ErrorDocumento) as e:
            self._avisar(e)
            return
        finally:
            self._aplicando = False
        self.tabla = _copia(self.doc.parametros)
        self.aplicado.emit()
        self._poblar()

    # ------------------------------------------------------------ cierre
    def _aceptar(self):
        if self._invalidas:
            self._avisar("Hay valores en rojo: corregilos antes de aceptar.")
            return
        self._aplicar()
        if not self._pendiente:
            self.accept()

    def done(self, resultado):
        """Aceptar, Esc o la X. Con Cálculo automático todo ya está aplicado; apagado, lo pendiente solo vale con Aceptar."""
        if not self._terminado:
            self._terminado = True
            self._reloj.stop()
            if self.automatico.isChecked() and self._pendiente and not self._invalidas:
                self._aplicar()
            self.doc.agrupar_deshacer(self._marca_deshacer)
            self.doc.desuscribir(self._doc_cambio)
        super().done(resultado)

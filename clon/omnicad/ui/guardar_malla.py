# -*- coding: utf-8 -*-
"""Diálogo Guardar como malla (Save As Mesh / 3D Print de Fusion)."""
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout, QGroupBox,
                               QLabel, QListWidget, QListWidgetItem, QVBoxLayout)

from ..io_archivos import exportar as ex
from ..nucleo import geometria as geo
from .dialogos import _combo


class DialogoGuardarMalla(QDialog):
    def __init__(self, cuerpos, seleccionados=(), nombres=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Guardar como malla")
        self.setMinimumWidth(440)
        self._cuerpos = list(cuerpos)
        self.triangulos = 0
        self.objetos = QListWidget()
        for c in self._cuerpos:
            item = QListWidgetItem((nombres or {}).get(c.id, c.nombre), self.objetos)
            item.setData(Qt.UserRole, c.id)
            item.setCheckState(Qt.Checked if not seleccionados or c.id in seleccionados else Qt.Unchecked)
        self.objetos.setMaximumHeight(140)
        self.formato = _combo(ex.FORMATOS_MALLA, "stl_binario")
        self.unidad = _combo({k: f"{v} ({k})" if k != v else k for k, v in ex.UNIDADES_MALLA.items()}, "mm")
        self.estructura = _combo({"un_archivo": "Un archivo", "uno_por_cuerpo": "Uno por cuerpo"})
        self.refinamiento = _combo({"bajo": "Bajo", "medio": "Medio", "alto": "Alto",
                                    "personalizado": "Personalizado"}, "personalizado")
        formulario = QFormLayout()
        for texto, campo in (("Objeto", self.objetos), ("Formato", self.formato), ("Unidad", self.unidad),
                             ("Estructura", self.estructura), ("Refinado", self.refinamiento)):
            formulario.addRow(texto, campo)
        self.personalizado = QGroupBox("Controles personalizados")
        controles = QFormLayout(self.personalizado)
        self.campos = {}
        for clave, texto, valor, minimo, maximo, sufijo in (
                ("desviacion", "Desviación de superficie", 0.02, 0.000001, 1e6, " mm"),
                ("angulo", "Desviación de normal", ex.ANGULO_MALLA, 0.000001, 179.999999, "°"),
                ("longitud_maxima", "Longitud máxima de arista", 0.0, 0.0, 1e6, " mm"),
                ("relacion_aspecto", "Relación de aspecto", 0.0, 0.0, 1e6, "")):
            campo = QDoubleSpinBox()
            campo.setDecimals(9)
            campo.setRange(minimo, maximo)
            campo.setValue(valor)
            campo.setSuffix(sufijo)
            campo.setKeyboardTracking(False)
            if minimo == 0:
                campo.setSpecialValueText("Sin límite")
            controles.addRow(texto, campo)
            self.campos[clave] = campo
        self.campos["relacion_aspecto"].setToolTip("Arista mayor / altura menor; mayor que 1,154701, o 0 sin límite.")
        self.recuento = QLabel()
        self.recuento.setWordWrap(True)
        self.botones = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.botones.button(QDialogButtonBox.Ok).setText("Aceptar")
        self.botones.button(QDialogButtonBox.Cancel).setText("Cancelar")
        self.botones.accepted.connect(self.accept)
        self.botones.rejected.connect(self.reject)
        caja = QVBoxLayout(self)
        caja.addLayout(formulario)
        caja.addWidget(self.personalizado)
        caja.addWidget(self.recuento)
        caja.addWidget(self.botones)
        self._temporizador = QTimer(self)
        self._temporizador.setSingleShot(True)
        self._temporizador.setInterval(180)
        self._temporizador.timeout.connect(self._actualizar_recuento)
        self.objetos.itemChanged.connect(self._programar_recuento)
        self.refinamiento.currentIndexChanged.connect(self._programar_recuento)
        for campo in self.campos.values():
            campo.valueChanged.connect(self._programar_recuento)
        self._actualizar_recuento()

    def cuerpos_elegidos(self):
        """Cuerpos marcados para exportar, en el orden del documento."""
        return [c for i, c in enumerate(self._cuerpos) if self.objetos.item(i).checkState() == Qt.Checked]

    def opciones(self):
        """Opciones compartidas con io_archivos.exportar_malla."""
        return dict(formato=self.formato.currentData(), unidades=self.unidad.currentData(),
                    estructura=self.estructura.currentData(), refinamiento=self.refinamiento.currentData(),
                    **{k: campo.value() for k, campo in self.campos.items()})

    def _programar_recuento(self):
        self.botones.button(QDialogButtonBox.Ok).setEnabled(False)
        self.personalizado.setEnabled(self.refinamiento.currentData() == "personalizado")
        self.recuento.setText("Calculando triángulos…")
        self._temporizador.start()

    def _actualizar_recuento(self):
        opciones = self.opciones()
        for k in ("formato", "unidades", "estructura"):
            opciones.pop(k)
        try:
            mallas = ex.preparar_mallas(self.cuerpos_elegidos(), **opciones)
            self.triangulos = sum(len(m.caras) for m in mallas)
            self.recuento.setText(f"Triángulos: {self.triangulos}")
            valido = True
        except (geo.ErrorGeometria, ex.ErrorExportacion, RuntimeError) as e:
            self.triangulos = 0
            self.recuento.setText(str(e))
            valido = False
        self.botones.button(QDialogButtonBox.Ok).setEnabled(valido)

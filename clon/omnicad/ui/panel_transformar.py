# -*- coding: utf-8 -*-
"""Panel ESCALA / MOVER/COPIAR del boceto (Fusion: Modify › Scale y Modify › Move/Copy): Objetos, Punto base, el factor o
ΔX/ΔY/ángulo (con «Copiar» en Mover), Vista previa, Aceptar y Cancelar.

Es el panel del patrón (`ui/panel_patron.py`) con otras filas: mismos botones, mismas señales y mismos campos `QLineEdit`
(las asas de la vista escriben en ellos). Lo maneja `ui/transformar_boceto.py`."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox

from .formulario import poner_estado
from .iconos import icono
from .panel_patron import PanelPatron

TITULOS = {"escala": "ESCALA", "mover": "MOVER/COPIAR"}
ICONOS = {"escala": "escala_boceto", "mover": "mover"}
ESTILO_MAL = "border: 1px solid #d9534f;"


class PanelTransformar(PanelPatron):
    TIPO_INICIAL = "escala"
    _visibles = None            # {clave de fila: herramientas con las que se ve}

    def _fila(self, clave, texto, widget, ayuda, grupo):
        super()._fila(clave, texto, widget, ayuda, "ninguno")
        if self._visibles is None:
            self._visibles = {}
        self._visibles[clave] = set(grupo)

    def _armar(self):
        E, M = ("escala",), ("mover",)
        self.sel = {
            "seleccion": self._seleccion("seleccion", "Objetos", "La geometría a transformar: clic en cada curva o una "
                                         "ventana de selección.", E + M),
            "base": self._seleccion("base", "Punto base", "Punto desde el que se escala o alrededor del cual se gira: un "
                                    "punto del dibujo, el origen o cualquier lugar. En Mover/copiar, sin punto base se "
                                    "usa el centro de lo elegido.", E + M)}
        self._valor("base_x", "Base X", "Coordenada X del punto base (mm).", E + M, "mm")
        self._valor("base_y", "Base Y", "Coordenada Y del punto base (mm).", E + M, "mm")
        self._valor("factor", "Factor", "Cuántas veces se agranda (mayor que 1) o se achica (entre 0 y 1) desde el punto "
                    "base. Las cotas de largo de lo escalado se multiplican por el factor.", E)
        self.sel["destino"] = self._seleccion("destino", "Destino", "Clic en el lugar al que va el punto base: llena ΔX y "
                                              "ΔY.", M)
        self._valor("dx", "ΔX", "Desplazamiento en X (mm).", M, "mm")
        self._valor("dy", "ΔY", "Desplazamiento en Y (mm).", M, "mm")
        self._valor("angulo", "Ángulo", "Giro alrededor del punto base, en grados (antihorario).", M, "°")
        self._casilla("copiar", "Crear copia", "Deja el original donde está y mueve una copia con sus restricciones "
                      "internas.", M)
        self.casilla_previa = QCheckBox()
        self.casilla_previa.setChecked(True)
        self.casilla_previa.setToolTip("Muestra el resultado antes de aceptar.")
        self.casilla_previa.toggled.connect(self.previa)
        self.casilla_previa.setFocusPolicy(Qt.NoFocus)
        self._fila("previa", "Vista previa", self.casilla_previa, self.casilla_previa.toolTip(), E + M)

    @property
    def lista_campos(self):
        return [self.campos["factor"]]

    def configurar(self, tipo, editando=False):
        """Muestra las filas de la herramienta `tipo`."""
        self.tipo = tipo
        self.titulo.setText(TITULOS[tipo])
        self.icono.setPixmap(icono(ICONOS[tipo]).pixmap(18, 18))
        for clave, (etiqueta, widget) in self.filas.items():
            visible = tipo in self._visibles[clave]
            etiqueta.setVisible(visible)
            widget.setVisible(visible)
        self.ajustar()

    def mostrar(self, e):
        """Pinta el estado del controlador: conteos de cada selección, campo activo, qué se ve y qué falta."""
        self.configurar(e["tipo"])
        for clave, fila in self.sel.items():
            fila.set_estado(e["conteos"].get(clave, 0), e["campo"] == clave)
            if e["etiquetas"].get(clave):
                fila.boton.setText(e["etiquetas"][clave])
        self.poner(e["campos"])
        for clave, c in self.campos.items():
            c.setStyleSheet(ESTILO_MAL if clave in e["malos"] else "")
        antes = self.size()
        self.boton_ok.setEnabled(e["valido"])
        poner_estado(self, e["guia"], e["error"])
        self.casilla_previa.blockSignals(True)
        self.casilla_previa.setChecked(e["previa"])
        self.casilla_previa.blockSignals(False)
        self.ajustar()
        if self.size() != antes and hasattr(self.parentWidget(), "reubicar"):
            self.parentWidget().reubicar()

"""Adaptador Qt del registro local; solo existe mientras la ventana está abierta."""
from PySide6.QtWidgets import QLabel

from .. import registro_uso as registro
from ..registro_uso.sistema import ram_total


class RegistroVentana:
    def __init__(self, ventana):
        self.ventana = ventana
        self.indicador = QLabel("● REG", objectName="indicador_registro_uso")
        self.indicador.setToolTip("Registro local de uso activo. No se envía nada.")
        ventana.statusBar().addPermanentWidget(self.indicador)
        self.indicador.hide()

    def configurar(self, encendido):
        v = self.ventana
        datos = {"proyecto": v.doc.ruta or v.doc.nombre, "ventana": [v.width(), v.height()],
                 "ram_total": ram_total() if encendido and registro.activo is None else None,
                 "gpu": getattr(v.visor, "info_gl", "no disponible"),
                 "opengl": getattr(v.visor, "info_gl", "no disponible")}
        estado = registro.configurar(encendido, datos)
        self.indicador.setVisible(estado["enabled"])
        return estado

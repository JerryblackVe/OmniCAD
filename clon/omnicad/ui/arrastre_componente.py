# -*- coding: utf-8 -*-
"""ENSAMBLAR › Posición en la ventana [Capture or revert position of components]: arrastrar un componente en el visor,
la barra «Posición» que aparece mientras hay algo sin capturar y la pregunta antes de un comando. Mueve solo el dibujo
(`visor.transformaciones`); las cuentas están en `timeline/posicion.py`."""
from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QMessageBox, QPushButton

from .. import NOMBRE_APP
from ..timeline.operaciones import ErrorOperacion
from ..timeline.posicion import Arrastre, deshacer_arrastre, pendiente_de


class BarraPosicion(QFrame):
    """Panel «Posición» de Fusion: solo se ve con componentes movidos sin capturar."""

    def __init__(self, control, parent):
        super().__init__(parent)
        self.setObjectName("barra_navegacion")
        caja = QHBoxLayout(self)
        caja.setContentsMargins(10, 4, 4, 4)
        caja.addWidget(QLabel("Posición sin capturar"))
        self.capturar = QPushButton("Capturar posición")
        self.capturar.clicked.connect(lambda: control.capturar())
        self.revertir = QPushButton("Revertir")
        self.revertir.clicked.connect(lambda: control.revertir())
        caja.addWidget(self.capturar)
        caja.addWidget(self.revertir)
        self.hide()


class ArrastreComponente:
    """Lo que el visor llama al arrastrar (`empezar`, `mover`, `soltar`, `cancelar`) y lo que la ventana usa para
    mantener el dibujo y la barra al día."""

    def __init__(self, ventana):
        self.v = ventana
        self.actual = None
        self.mostrado = False         # el dibujo muestra una posición sin capturar
        self.barra = BarraPosicion(self, ventana.area)
        ventana.area.barra_posicion = self.barra

    # ------------------------------------------------------------ arrastre
    def empezar(self, pos):
        """Arranca el arrastre si bajo `pos` hay un cuerpo de un componente. False deja seguir la selección por ventana."""
        v = self.v
        estudio = getattr(v, "_panel_estudio", None)
        ocupado = (v.panel is not None or v.modo_boceto.activo or (estudio is not None and estudio.isVisible())
                   or (v.visor.transformaciones and not self.mostrado))
        hit = None if ocupado else v.visor.cuerpo_bajo_cursor(pos)
        if hit is None or not v.doc.estado_final.cuerpo(hit[0]).componente:
            return False
        try:
            self.actual = Arrastre(v.doc, *hit)
        except ErrorOperacion as e:
            v.mensaje(str(e))
            return False
        return True

    def mover(self, pos):
        visor = self.v.visor
        o, d = visor.rayo(pos)
        vista = visor.rayo(QPointF(visor.width() / 2, visor.height() / 2))[1]    # el plano de la vista por el punto agarrado
        self.actual.mover(o + d * (float((self.actual.punto - o) @ vista) / float(d @ vista)), d)
        self.sincronizar()

    def soltar(self):
        self.actual.soltar()
        self.actual = None
        self.sincronizar()

    def cancelar(self):
        self.actual.cancelar()
        self.actual = None
        self.sincronizar()

    # ------------------------------------------------------------ posición sin capturar
    def sincronizar(self):
        """Deja el dibujo y la barra como está `doc.posicion_pendiente`."""
        v = self.v
        p = pendiente_de(v.doc)
        if p is None and not self.mostrado:
            return
        v.visor.transformaciones = p.poses() if p is not None else {}
        v.visor.update()
        if self.mostrado != (p is not None):
            self.mostrado = p is not None
            self.barra.setVisible(self.mostrado)
            v.area.reubicar()
            v._actualizar_deshacer()

    def capturar(self):
        from .. import api
        r = api.llamar(api.Sesion(self.v.doc), "capture_position", {})
        if not r["ok"]:
            self.v.mensaje(r["mensaje"])
        self.sincronizar()

    def revertir(self):
        self.v.doc.posicion_pendiente = None
        self.sincronizar()

    def deshacer(self):
        """Corta el arrastre en curso o deshace el último sin capturar. Devuelve si había alguno."""
        if self.actual is not None:
            self.v.visor.cancelar_arrastre()
            return True
        hecho = deshacer_arrastre(self.v.doc)
        self.sincronizar()
        return hecho

    def decidir(self, comando=None):
        """Antes de un comando con algo sin capturar. Capturar y Revertir actúan sobre eso; cualquier otro pregunta,
        como Fusion. Devuelve si el comando sigue."""
        from .comandos.ensamblar import CapturarPosicion, RevertirPosicion
        if self.actual is not None:             # un atajo con el botón apretado
            self.v.visor.cancelar_arrastre()
        if pendiente_de(self.v.doc) is None:
            return True
        if isinstance(comando, CapturarPosicion):
            self.capturar()
            return False
        if isinstance(comando, RevertirPosicion):
            self.revertir()
            return False
        caja = QMessageBox(QMessageBox.Question, NOMBRE_APP, "Algunos componentes se movieron.", parent=self.v)
        caja.setInformativeText("Capturá la posición actual o seguí en la posición anterior.")
        seguir = caja.addButton("Continuar", QMessageBox.DestructiveRole)
        capturar = caja.addButton("Capturar posición", QMessageBox.AcceptRole)
        caja.setDefaultButton(capturar)
        caja.addButton(QMessageBox.Cancel).setText("Cancelar")
        caja.exec()
        if caja.clickedButton() is seguir:
            self.revertir()
        elif caja.clickedButton() is capturar:
            self.capturar()
        else:
            return False
        return True

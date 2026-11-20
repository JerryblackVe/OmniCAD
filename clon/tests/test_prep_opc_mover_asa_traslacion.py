# -*- coding: utf-8 -*-
"""PREP: opción «Asa de traslación (ΔX y ΔY)» del comando «Mover/copiar» del boceto.

Fusion (docs/fusion_docs/contenido/fusion-sketch/sketch-modification-tools-a217fee171a.md):
«The Move/Copy tool moves selected sketch geometry… You select the sketch geometry to move, then specify the new location.»
Fusion (docs/fusion_docs/contenido/fusion-model/move-copy-reference-952166a90ef.md):
«Translate: Lets you move the object laterally in the X, Y, and Z directions… use the X, Y, Z manipulators in the canvas to move to the desired position, or specify the values manually in the dialog.»

El asa de traslación del panel MOVER/COPIAR escribe a la vez ΔX y ΔY (los dos campos) y se mueve con esos
valores: los campos → asa y el asa → campos. Se fija además el borde de los signos: al tirar el asa al
otro lado del punto base, ΔX y ΔY cambian de signo (no se traban en cero). No cambia código: fija lo que
ya hace y avisa si deja de hacerlo.
"""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, Qt  # noqa: E402
from PySide6.QtGui import QMouseEvent  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from omnicad.restricciones import Boceto  # noqa: E402
from omnicad.timeline.parametros import TablaParametros  # noqa: E402
from omnicad.ui import editor_boceto  # noqa: E402
from omnicad.ui.panel_transformar import PanelTransformar  # noqa: E402


@pytest.fixture
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def ventana(app):
    lz = editor_boceto.Lienzo(Boceto(), TablaParametros().evaluar)
    lz.resize(800, 600)
    lz.ajustar_grilla = False
    lz.show()
    panel = lz._panel_prueba = PanelTransformar()
    ctl = lz.transformar
    ctl.panel = panel
    panel.campo.connect(ctl.elegir_campo)
    panel.limpiar.connect(ctl.limpiar_campo)
    panel.cambio.connect(ctl.recibir)
    panel.previa.connect(ctl.set_previa)
    panel.aceptado.connect(ctl.aceptar)
    panel.cancelado.connect(ctl.cancelar)
    yield lz, panel, ctl
    lz.close()
    lz.deleteLater()
    app.processEvents()


def _raton(lz, tipo, xy, botones=Qt.LeftButton):
    q = lz.a_px(*xy)
    boton = Qt.LeftButton if tipo != QEvent.MouseMove else Qt.NoButton
    QApplication.sendEvent(lz, QMouseEvent(tipo, q, lz.mapToGlobal(q), boton,
                                           botones if tipo != QEvent.MouseButtonRelease else Qt.NoButton, Qt.NoModifier))


def _arrastrar(lz, desde, hasta, pasos=6):
    _raton(lz, QEvent.MouseButtonPress, desde)
    for k in range(1, pasos + 1):
        t = k / pasos
        _raton(lz, QEvent.MouseMove,
               (desde[0] + (hasta[0] - desde[0]) * t, desde[1] + (hasta[1] - desde[1]) * t), Qt.LeftButton)
    _raton(lz, QEvent.MouseButtonRelease, hasta)


def _mover(ventana):
    """Abre Mover/copiar con una línea y el punto base en el origen; devuelve el lienzo, el panel y el asa de traslación."""
    lz, panel, ctl = ventana
    ln = lz.b.agregar_linea((10, 0), (20, 0))
    lz.seleccion = [ln]
    lz.set_herramienta("mover")
    lz.encuadrar()
    ctl.base = (0.0, 0.0)
    ctl._texto_base()
    ctl._emitir()
    assert lz._asas is not None and len(lz._asas.asas) == 2
    return lz, panel, ctl, lz._asas.asas[0]


def test_el_asa_de_traslacion_lee_y_escribe_el_valor_numerico(ventana):
    lz, panel, ctl, asa = _mover(ventana)
    assert asa.campo == (0, 1) and asa.tipo == "long"            # escribe los campos «ΔX» y «ΔY»

    panel.campos["dx"].setText("7")
    panel.campos["dy"].setText("-4")
    assert asa.posicion(lz._asas.valores()) == pytest.approx((7.0, -4.0))      # campos → asa

    _arrastrar(lz, asa.posicion(lz._asas.valores()), (3.0, 5.0))
    assert float(panel.campos["dx"].text()) == pytest.approx(3, abs=0.5)        # asa → campos
    assert float(panel.campos["dy"].text()) == pytest.approx(5, abs=0.5)
    lz.cancelar()


def test_el_asa_de_traslacion_cambia_de_signo_al_otro_lado_del_punto_base(ventana):
    lz, panel, ctl, asa = _mover(ventana)

    _arrastrar(lz, asa.posicion(lz._asas.valores()), (-7.0, -4.0))
    assert float(panel.campos["dx"].text()) == pytest.approx(-7, abs=0.5)
    assert float(panel.campos["dy"].text()) == pytest.approx(-4, abs=0.5)
    lz.cancelar()

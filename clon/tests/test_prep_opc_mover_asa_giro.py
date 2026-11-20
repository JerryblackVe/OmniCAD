# -*- coding: utf-8 -*-
"""PREP: opción «Asa de giro» del comando «Mover/copiar» del boceto.

Fusion (docs/fusion_docs/contenido/fusion-sketch/sketch-modification-tools-a217fee171a.md):
«The Move/Copy tool moves selected sketch geometry… You select the sketch geometry to move, then specify the new location.»
Fusion (docs/fusion_docs/contenido/fusion-model/move-copy-reference-952166a90ef.md):
«Free Move: Displays a manipulator. Use the manipulator to move the object or enter values in the fields.»
y «X, Y, Z Angle: Specify the angle to rotate around the X, Y, or Z axis.»

El asa de giro del panel MOVER/COPIAR escribe el ángulo (°) del campo «Ángulo» y se mueve con ese
valor: el campo → asa y el asa → campo. Se fija además el borde de las varias vueltas: con un ángulo
mayor a una vuelta el asa conserva la vuelta actual en vez de volver a 0. No cambia código: fija lo que
ya hace y avisa si deja de hacerlo.
"""
import math
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

RADIO = 20.0          # la línea de (10, 0) a (20, 0) queda a 20 mm del punto base


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
    """Abre Mover/copiar con una línea y el punto base en el origen; devuelve el lienzo, el panel y el asa de giro."""
    lz, panel, ctl = ventana
    ln = lz.b.agregar_linea((10, 0), (20, 0))
    lz.seleccion = [ln]
    lz.set_herramienta("mover")
    lz.encuadrar()
    ctl.base = (0.0, 0.0)
    ctl._texto_base()
    ctl._emitir()
    assert lz._asas is not None and len(lz._asas.asas) == 2
    return lz, panel, ctl, lz._asas.asas[1]


def test_el_asa_de_giro_lee_y_escribe_el_valor_numerico(ventana):
    lz, panel, ctl, asa = _mover(ventana)
    assert asa.campo == 2 and asa.tipo == "ang"                    # escribe el campo «Ángulo»

    panel.campos["angulo"].setText("90")
    assert asa.posicion(lz._asas.valores()) == pytest.approx((0.0, RADIO), abs=1e-6)      # campo → asa

    _arrastrar(lz, asa.posicion(lz._asas.valores()),
               (RADIO * math.cos(math.radians(45)), RADIO * math.sin(math.radians(45))))
    assert float(panel.campos["angulo"].text()) == pytest.approx(45, abs=0.5)              # asa → campo


def test_el_asa_de_giro_conserva_las_vueltas(ventana):
    lz, panel, ctl, asa = _mover(ventana)

    panel.campos["angulo"].setText("540")
    assert asa.posicion(lz._asas.valores()) == pytest.approx((-RADIO, 0.0), abs=1e-6)
    destino = (RADIO * math.cos(math.radians(550)), RADIO * math.sin(math.radians(550)))
    _arrastrar(lz, asa.posicion(lz._asas.valores()), destino)
    assert float(panel.campos["angulo"].text()) == pytest.approx(550, abs=0.5)

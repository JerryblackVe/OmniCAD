# -*- coding: utf-8 -*-
"""Preparado del «Asa de factor» de Escala del boceto (fila sin test automático en `opciones_asas_boceto.md`).

Fusion (docs/fusion_docs/contenido/fusion-sketch/scale-sketch-geometry-07f04098012.md): «Specify the scale factor
value or drag the manipulator handle in the canvas». Se fijan las dos formas: el valor numérico va del campo al asa y
del asa al campo, y el asa para en su tope positivo (0,001) al tirar más allá del punto base. No cambia código: fija lo
que ya hace y avisa si deja de hacerlo.
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
    panel = PanelTransformar()
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
    QApplication.processEvents()


def _raton(lz, tipo, xy, botones=Qt.LeftButton):
    q = lz.a_px(*xy)
    boton = Qt.LeftButton if tipo != QEvent.MouseMove else Qt.NoButton
    QApplication.sendEvent(lz, QMouseEvent(tipo, q, lz.mapToGlobal(q), boton,
                                           botones if tipo != QEvent.MouseButtonRelease else Qt.NoButton, Qt.NoModifier))


def _arrastrar(lz, desde, hasta, pasos=6):
    _raton(lz, QEvent.MouseButtonPress, desde)
    for k in range(1, pasos + 1):
        t = k / pasos
        _raton(lz, QEvent.MouseMove, (desde[0] + (hasta[0] - desde[0]) * t, desde[1] + (hasta[1] - desde[1]) * t))
    _raton(lz, QEvent.MouseButtonRelease, hasta)


def _asa_factor(ventana):
    """Círculo en (10, 0) de R3 con punto base en el origen: el asa sale hacia el punto más lejano."""
    lz, panel, ctl = ventana
    c = lz.b.agregar_circulo((10, 0), 3)
    lz.seleccion = [c]
    lz.set_herramienta("escala")
    lz.encuadrar()
    ctl.base = (0.0, 0.0)
    ctl._texto_base()
    ctl._emitir()
    panel.campos["factor"].setText("1")
    return lz, panel, ctl, lz._asas.asas[0]


def test_el_asa_del_factor_lee_y_escribe_el_valor_numerico(ventana):
    """Como Fusion: el número escrito coloca el asa y el asa arrastrado escribe el número en el campo."""
    lz, panel, _ctl, asa = _asa_factor(ventana)
    base = lz.transformar.base

    def punto(factor):
        return (base[0] + (asa.posicion([1.0])[0] - base[0]) * factor,
                base[1] + (asa.posicion([1.0])[1] - base[1]) * factor)

    panel.campos["factor"].setText("2.5")
    assert asa.posicion(lz._asas.valores()) == pytest.approx(punto(2.5))       # campo → asa

    _arrastrar(lz, asa.posicion(lz._asas.valores()), punto(3))
    assert float(panel.campos["factor"].text()) == pytest.approx(3, abs=0.05)  # asa → campo
    lz.cancelar()


def test_el_asa_del_factor_no_baja_de_su_tope_positivo(ventana):
    """Al tirar del asa más allá del punto base el factor no cruza cero: para en 0,001 (el mínimo del asa)."""
    lz, panel, _ctl, asa = _asa_factor(ventana)
    _arrastrar(lz, asa.posicion(lz._asas.valores()), (-30, 0))
    assert float(panel.campos["factor"].text()) == pytest.approx(0.001)        # borde: no 0 ni negativo
    lz.cancelar()

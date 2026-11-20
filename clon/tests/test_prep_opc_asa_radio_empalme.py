# -*- coding: utf-8 -*-
"""PREP: asa de radio del comando Empalme del boceto (fila sin test automático en `opciones_asas_boceto.md`).

Fusion (docs/fusion_docs/contenido/fusion-sketch/add-fillets-to-sketch-geometry-89d2b427f79.md): «Drag the radius
manipulator handle in the canvas or specify a radius value». Se fijan el valor numérico (el campo coloca el asa en el
medio del arco y el asa arrastrado escribe el radio en el campo) y un borde (al tirar del asa más allá de la esquina el
radio nunca baja de cero: frena en el mínimo positivo). No cambia código: fija lo que ya hace y avisa si deja de hacerlo.
"""
import math
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, QPointF, Qt  # noqa: E402
from PySide6.QtGui import QMouseEvent  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from omnicad.restricciones import Boceto  # noqa: E402
from omnicad.timeline.parametros import TablaParametros  # noqa: E402
from omnicad.ui import editor_boceto  # noqa: E402


@pytest.fixture
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def lienzo(app):
    lz = editor_boceto.Lienzo(Boceto(), TablaParametros().evaluar)
    lz.resize(800, 600)
    lz.ajustar_grilla = False
    lz.show()
    yield lz
    lz.close()
    lz.deleteLater()
    app.processEvents()


def _raton(lz, tipo, xy, botones=Qt.LeftButton):
    q = lz.a_px(*xy) if not isinstance(xy, QPointF) else xy
    boton = Qt.LeftButton if tipo != QEvent.MouseMove else Qt.NoButton
    QApplication.sendEvent(lz, QMouseEvent(tipo, q, lz.mapToGlobal(q), boton,
                                           botones if tipo != QEvent.MouseButtonRelease else Qt.NoButton, Qt.NoModifier))


def _arrastrar(lz, desde, hasta):
    _raton(lz, QEvent.MouseButtonPress, desde)
    for k in range(1, 7):
        t = k / 6
        _raton(lz, QEvent.MouseMove,
               (desde[0] + (hasta[0] - desde[0]) * t, desde[1] + (hasta[1] - desde[1]) * t), Qt.LeftButton)
    _raton(lz, QEvent.MouseButtonRelease, hasta)


def _abrir_empalme(lz):
    """Esquina en el origen con dos líneas de 30 mm; abre la caja [Radio] con su asa."""
    a = lz.b.agregar_linea((0, 0), (30, 0))
    b = lz.b.agregar_linea((0, 0), (0, 30))
    lz.set_herramienta("empalme")
    lz.agregar_pick(a, (15.0, 0.0), QPointF(0, 0))
    lz.agregar_pick(b, (0.0, 15.0), QPointF(0, 0))
    lz.encuadrar()
    QApplication.processEvents()
    assert len(lz._asas.asas) == 1
    return lz._asas.asas[0]


def test_el_asa_de_radio_lee_y_escribe_el_valor_numerico(lienzo):
    """Como Fusion: el número escrito coloca el asa en el medio del arco y el asa arrastrado escribe el radio."""
    lz = lienzo
    asa = _abrir_empalme(lz)

    lz.entrada.campos[0].setText("5")
    m = 5 - 5 / math.sqrt(2)
    assert asa.posicion(lz._asas.valores()) == pytest.approx((m, m), abs=0.05)  # campo → asa

    k = 10 - 10 / math.sqrt(2)
    _arrastrar(lz, asa.posicion(lz._asas.valores()), (k, k))
    assert float(lz.entrada.campos[0].text()) == pytest.approx(10, abs=0.3)     # asa → campo


def test_el_asa_de_radio_no_baja_de_cero_en_la_esquina(lienzo):
    """Borde: tirar del asa al otro lado de la esquina nunca da radio cero ni negativo (frena en el mínimo)."""
    lz = lienzo
    asa = _abrir_empalme(lz)

    lz.entrada.campos[0].setText("5")
    _arrastrar(lz, asa.posicion(lz._asas.valores()), (-8.0, -8.0))
    assert float(lz.entrada.campos[0].text()) > 0

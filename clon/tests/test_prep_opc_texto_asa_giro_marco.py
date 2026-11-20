# -*- coding: utf-8 -*-
"""PREP: opción «Asa de giro del marco» del comando «Texto» del boceto.

Fusion (docs/fusion_docs/contenido/fusion-sketch/create-text-in-a-sketch-ca7edabd067.md):
«Use the rotation manipulator handle to rotate the text frame, or specify the angle.»
El asa escribe el ángulo (∠) de la caja del texto alrededor de su ancla; no aparece en el
texto sobre curva. Se fijan el valor numérico (campo → asa y asa → campo) y un borde
(ángulo de varias vueltas: el asa conserva la vuelta actual en vez de volver a 0).
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
    q = lz.a_px(*xy)
    boton = Qt.LeftButton if tipo != QEvent.MouseMove else Qt.NoButton
    QApplication.sendEvent(lz, QMouseEvent(tipo, q, lz.mapToGlobal(q), boton,
                                           botones if tipo != QEvent.MouseButtonRelease else Qt.NoButton, Qt.NoModifier))


def _arrastrar(lz, desde, hasta, pasos=6):
    _raton(lz, QEvent.MouseButtonPress, desde)
    for k in range(1, pasos + 1):
        t = k / pasos
        punto = (desde[0] + (hasta[0] - desde[0]) * t, desde[1] + (hasta[1] - desde[1]) * t)
        _raton(lz, QEvent.MouseMove, punto, Qt.LeftButton)
    _raton(lz, QEvent.MouseButtonRelease, hasta)


def _posicion(lz, i=0):
    return lz._asas.asas[i].posicion(lz._asas.valores())


def _textos(lz):
    return [c.text() for c in lz.entrada.campos]


def _crear_texto(lz):
    lz.set_herramienta("texto")
    lz.clics.append((None, (0.0, 0.0)))
    lz.clics.append((None, (40.0, 10.0)))
    lz._procesar_clics()
    lz.encuadrar()
    assert lz._asas is not None and len(lz._asas.asas) == 1


def test_el_asa_de_giro_del_marco_lee_y_escribe_el_valor_numerico(lienzo):
    lz = lienzo
    _crear_texto(lz)
    ancla = (0.0, 0.0)
    radio = 40.0

    # campo -> asa
    lz.entrada.campos[2].setText("90")
    assert _posicion(lz) == pytest.approx((ancla[0], ancla[1] + radio), abs=1e-6)

    # asa -> campo
    _arrastrar(lz, _posicion(lz), (ancla[0] + 20.0, ancla[1] + 20.0))
    assert float(_textos(lz)[2]) == pytest.approx(45, abs=1.0)

    lz._cerrar_entrada()


def test_el_asa_de_giro_del_marco_conserva_las_vueltas(lienzo):
    lz = lienzo
    _crear_texto(lz)
    ancla = (0.0, 0.0)
    radio = 40.0

    lz.entrada.campos[2].setText("540")
    # arrastrar la manija unos 10 grados mas, conservando la vuelta
    rad = math.radians(550)
    destino = (ancla[0] + radio * math.cos(rad), ancla[1] + radio * math.sin(rad))
    _arrastrar(lz, _posicion(lz), destino)
    assert float(_textos(lz)[2]) == pytest.approx(550, abs=1.0)

    lz._cerrar_entrada()

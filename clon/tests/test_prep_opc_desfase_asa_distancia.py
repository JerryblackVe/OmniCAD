# -*- coding: utf-8 -*-
"""PREP: asa de distancia (1 o 2, sobre la normal) del comando Desfase del boceto.

Fusion (docs/fusion_docs/contenido/fusion-sketch/offset-sketch-geometry-c7750d70285.md): el Desfase tiene
«One Side / Two Sides / Symmetric» y la distancia se puede tipear o tirar del manipulador (asa) en la vista;
en «Two Sides» hay un asa por cada distancia, las dos sobre la misma normal. Se fijan el valor numérico
(campo → asa y asa → campo) y un borde (el asa pasa por cero y cambia de signo; en Simétrico la distancia
es siempre positiva). No cambia código: fija lo que ya hace y avisa si deja de hacerlo.
"""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, Qt  # noqa: E402
from PySide6.QtGui import QMouseEvent  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from omnicad.restricciones import Boceto  # noqa: E402
from omnicad.timeline.parametros import TablaParametros  # noqa: E402
from omnicad.ui import editor_boceto  # noqa: E402

R = 67.125


def _evento(lz, tipo, pos, boton=Qt.NoButton, botones=Qt.NoButton):
    QApplication.sendEvent(lz, QMouseEvent(tipo, pos, pos, boton, botones, Qt.NoModifier))


def _mover(lz, pos, botones=Qt.NoButton):
    _evento(lz, QEvent.MouseMove, pos, Qt.NoButton, botones)


def _clic(lz, pos):
    _mover(lz, pos)
    _evento(lz, QEvent.MouseButtonPress, pos, Qt.LeftButton, Qt.LeftButton)
    _evento(lz, QEvent.MouseButtonRelease, pos, Qt.LeftButton, Qt.NoButton)


def _arrastrar_asa(lz, i, destino_mm):
    q = lz._asas.posiciones_px()[i][1]
    _mover(lz, q)
    _evento(lz, QEvent.MouseButtonPress, q, Qt.LeftButton, Qt.LeftButton)
    meta = lz.a_px(*destino_mm)
    for k in range(1, 6):
        _mover(lz, q + (meta - q) * (k / 5), Qt.LeftButton)
    _evento(lz, QEvent.MouseButtonRelease, meta, Qt.LeftButton, Qt.NoButton)


@pytest.fixture
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def lienzo(app):
    lz = editor_boceto.Lienzo(Boceto(), TablaParametros().evaluar)
    lz.resize(1280, 720)
    lz.ajustar_grilla = False
    lz.escala = 2.0
    lz.show()
    yield lz
    lz.close()
    lz.deleteLater()
    app.processEvents()


def _abrir(lz, modo="un", radio=R):
    c = lz.b.agregar_circulo((0, 0), radio)
    lz.resolver()
    lz.opciones["direccion_desfase"] = modo
    lz.set_herramienta("desfase")
    _clic(lz, lz.a_px(radio, 0))
    assert lz.entrada is not None
    return c


def _cerrar(lz):
    if lz.entrada is not None:
        QTest.keyClick(lz.entrada.campos[0], Qt.Key_Escape)


def test_el_desfase_dos_lados_tiene_dos_asas_y_los_otros_uno(lienzo):
    """«1 o 2, sobre la normal»: «Dos lados» arma dos asas; «Un lado» y «Simétrico», una."""
    for modo, cantidad in (("un", 1), ("simetrico", 1), ("dos", 2)):
        lz = lienzo
        _abrir(lz, modo)
        assert len(lz._asas.asas) == cantidad, modo
        _cerrar(lz)


def test_el_asa_de_distancia_lee_y_escribe_el_valor_numerico(lienzo):
    """Como Fusion: el número escrito coloca el asa y el asa arrastrado escribe el número en el campo."""
    lz = lienzo
    _abrir(lz, "un")
    asa = lz._asas.asas[0]

    lz.entrada.campos[0].setText("20")
    base = asa.posicion([0.0])
    uno = asa.posicion([1.0])
    esperado = (base[0] + (uno[0] - base[0]) * 20, base[1] + (uno[1] - base[1]) * 20)
    assert asa.posicion(lz._asas.valores()) == pytest.approx(esperado, abs=1e-6)  # campo → asa

    _arrastrar_asa(lz, 0, (R + 12, 0))
    assert float(lz.entrada.campos[0].text()) == pytest.approx(12, abs=0.5)  # asa → campo
    _cerrar(lz)


def test_el_asa_de_distancia_pasa_por_cero_y_cambia_de_signo(lienzo):
    """Borde: tirar el asa al otro lado del punto de la curva cambia el signo (no se traba en cero)."""
    lz = lienzo
    _abrir(lz, "un")
    _arrastrar_asa(lz, 0, (R - 30, 0))
    assert float(lz.entrada.campos[0].text()) == pytest.approx(-30, abs=0.5)
    _cerrar(lz)


def test_el_asa_simetrica_siempre_da_una_distancia_positiva(lienzo):
    """Borde del Simétrico: aunque el asa se tire al otro lado, la distancia queda en positivo (abs)."""
    lz = lienzo
    _abrir(lz, "simetrico")
    _arrastrar_asa(lz, 0, (R - 30, 0))
    assert float(lz.entrada.campos[0].text()) == pytest.approx(30, abs=0.5)
    _cerrar(lz)

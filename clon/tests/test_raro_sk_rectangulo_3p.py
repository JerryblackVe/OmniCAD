# -*- coding: utf-8 -*-
"""Valores raros del comando de boceto «sk_rectangulo_3p» (Rectángulo de 3 puntos).

Sus dos campos vivos son `ancho` (tras el primer clic, el lado A→B) y `alto` (tras el segundo clic, la
perpendicular que da el ancho), según `editor_boceto_cotas.py` › `_claves_vivas`. La ayuda de Fusion
(«Sketch tools (Edit Model)», docs/fusion_docs/contenido/fusion-generativedesign/sketch-tools-edit-model-cffd286ea47.md)
dice que los dos primeros puntos definen el borde y el tercero el ancho, con restricciones paralelas en vez de
horizontales y verticales. Cada campo se prueba vacío, 0, negativo, enorme, con unidades y con expresión:
nada cierra la app, deja el boceto roto ni emite un aviso de más de un renglón.
"""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, Qt  # noqa: E402
from PySide6.QtGui import QMouseEvent  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from omnicad.restricciones import Boceto, resolver  # noqa: E402
from omnicad.timeline.parametros import TablaParametros  # noqa: E402
from omnicad.ui import editor_boceto  # noqa: E402

# (campo, valor tecleado, ¿se rechaza?)
CASOS = [
    ("ancho", "", False),
    ("ancho", "0", True),
    ("ancho", "-5", True),
    ("ancho", "1e9", True),
    ("ancho", "30 mm", False),
    ("ancho", "10*3", False),
    ("alto", "", False),
    ("alto", "0", True),
    ("alto", "-5", True),
    ("alto", "1e9", True),
    ("alto", "20 mm", False),
    ("alto", "10*2", False),
]


@pytest.fixture
def lz():
    app = QApplication.instance() or QApplication([])
    lienzo = editor_boceto.Lienzo(Boceto(), TablaParametros().evaluar)
    lienzo.resize(800, 600)
    lienzo.ajustar_grilla = False
    lienzo.show()
    lienzo.mensajes = []
    lienzo.mensaje.connect(lienzo.mensajes.append)
    yield lienzo
    lienzo.close()
    lienzo.deleteLater()
    app.processEvents()


def _mover(lz, x, y):
    pos = lz.a_px(x, y)
    QApplication.sendEvent(lz, QMouseEvent(QEvent.MouseMove, pos, pos, Qt.NoButton, Qt.NoButton, Qt.NoModifier))


def _clic(lz, x, y):
    _mover(lz, x, y)
    pos = lz.a_px(x, y)
    for tipo, botones in ((QEvent.MouseButtonPress, Qt.LeftButton), (QEvent.MouseButtonRelease, Qt.NoButton)):
        QApplication.sendEvent(lz, QMouseEvent(tipo, pos, pos, Qt.LeftButton, botones, Qt.NoModifier))


def _abrir(lz, campo):
    lz.set_herramienta("rectangulo_3p")
    _clic(lz, 0, 0)
    if campo == "ancho":
        _mover(lz, 30, 0)
        assert lz._claves_vivas() == ["ancho"]
    else:
        _clic(lz, 30, 0)
        _mover(lz, 30, 20)
        assert lz._claves_vivas() == ["alto"]
    lz._editar_campo_vivo("")
    assert lz.entrada is not None


def _teclear(caja, texto):
    caja.setText(texto)
    QTest.keyClick(caja, Qt.Key_Return)
    QApplication.instance().processEvents()


def _terminar(lz, campo):
    if campo == "ancho":
        _clic(lz, 30, 20)
    assert len([c for c in lz.b.curvas.values() if c.tipo == "linea"]) == 4
    assert lz.resultado.ok
    assert resolver(lz.b).ok


@pytest.mark.parametrize(("campo", "valor", "rechazado"), CASOS, ids=[f"{c}_{v or 'vacio'}" for c, v, _ in CASOS])
def test_valores_raros_de_sk_rectangulo_3p(lz, campo, valor, rechazado):
    antes = lz.b.a_dict()
    _abrir(lz, campo)
    lz.mensajes.clear()
    caja = lz.entrada.campos[0]
    _teclear(caja, valor)

    assert QApplication.instance() is not None and lz.isVisible()
    assert all("\n" not in m and "\r" not in m for m in lz.mensajes), (campo, valor, lz.mensajes)
    assert (lz.entrada is not None) == rechazado, (campo, valor, lz.entrada is not None)
    if rechazado:
        assert lz.b.a_dict() == antes, (campo, valor, "el valor rechazado cambió el boceto")
        assert lz.mensajes, (campo, valor, "rechazo sin mensaje")
        _teclear(caja, "30" if campo == "ancho" else "20")
        assert lz.entrada is None, (campo, valor, "el valor correcto no se aceptó")

    _terminar(lz, campo)

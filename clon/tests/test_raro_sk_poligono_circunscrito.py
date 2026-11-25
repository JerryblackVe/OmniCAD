# -*- coding: utf-8 -*-
"""Valores raros del comando de boceto «sk_poligono_circunscrito»: los campos Radio y Lados de su caja viva en
vacío, 0, negativo, enorme, con unidades y con expresión. Aceptar nunca cierra la app ni deja el boceto roto, y
todo aviso es de un renglón."""
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


CASOS = [
    ("radio", "", True),
    ("radio", "0", False),
    ("radio", "-5", False),
    ("radio", "2000000", False),
    ("radio", "20 mm", True),
    ("radio", "5*2", True),
    ("lados", "", True),
    ("lados", "0", False),
    ("lados", "-5", False),
    ("lados", "100", False),
    ("lados", "6 mm", False),
    ("lados", "3+1", True),
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


@pytest.mark.parametrize(("campo", "texto", "valido"), CASOS, ids=[f"{c}_{t or 'vacio'}" for c, t, _ in CASOS])
def test_valores_raros_de_sk_poligono_circunscrito_no_rompen_el_boceto(lz, campo, texto, valido):
    lz.set_herramienta("poligono_circunscrito")
    _clic(lz, 0, 0)
    _mover(lz, 10, 0)
    assert lz._claves_vivas() == ["radio", "lados"]

    lz._activo = 0 if campo == "radio" else 1
    lz._editar_campo_vivo("")
    assert lz.entrada is not None

    lz.mensajes.clear()
    antes = lz.b.a_dict()
    caja = lz.entrada.campos[0]
    caja.setText(texto)
    QTest.keyClick(caja, Qt.Key_Return)
    QApplication.instance().processEvents()

    assert QApplication.instance() is not None
    assert lz.isVisible()
    resultado = resolver(lz.b)
    assert resultado.ok, (campo, texto, lz.mensajes)

    if not valido:
        assert lz.entrada is not None, (campo, texto)
        assert lz.b.a_dict() == antes, (campo, texto, "el valor rechazado cambió el boceto")
        assert lz.mensajes, (campo, texto, "rechazo sin mensaje")
        mensaje = lz.mensajes[-1]
        assert "\n" not in mensaje and "\r" not in mensaje, (campo, texto, mensaje)
        assert len(mensaje) <= 45, (campo, texto, mensaje)
        lz.entrada.cancelado.emit()
        QApplication.instance().processEvents()
    else:
        assert lz.entrada is None, (campo, texto)
        assert len(lz.b.curvas) >= 1, (campo, texto, len(lz.b.curvas))
        if (campo, texto) == ("lados", "3+1"):
            assert sum(lz.b.tipo_de(cid) == "linea" for cid in lz.b.curvas) == 4
        assert not [m for m in lz.mensajes if "mayor que 0" in m or "máximo" in m or "entre 3 y" in m], lz.mensajes

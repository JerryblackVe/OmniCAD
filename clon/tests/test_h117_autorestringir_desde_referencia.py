# -*- coding: utf-8 -*-
"""H-117: «Restricciones automáticas desde referencia» (Fusion: AutoConstrain From Datum) en el menú
RESTRICCIONES. El botón pide primero el punto datum con un clic en el lienzo y después abre el diálogo
de AutoConstrain con ese datum ya fijado. Reusa `auto_constrain` con `datum`: sin lógica nueva."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, Qt, QTimer  # noqa: E402
from PySide6.QtGui import QMouseEvent  # noqa: E402
from PySide6.QtWidgets import QApplication, QDialog, QWidget  # noqa: E402

from omnicad.restricciones import Boceto  # noqa: E402
from omnicad.timeline.parametros import TablaParametros  # noqa: E402
from omnicad.ui import editor_boceto  # noqa: E402
from omnicad.ui.cinta_boceto import GRUPOS_BOCETO  # noqa: E402
from omnicad.ui.dialogo_autorestringir import DialogoAutoRestringir  # noqa: E402
from omnicad.ui.modo_boceto import ModoBoceto  # noqa: E402


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


def _mover(lz, x, y, mods=Qt.NoModifier):
    pos = lz.a_px(x, y)
    QApplication.sendEvent(lz, QMouseEvent(QEvent.MouseMove, pos, pos, Qt.NoButton, Qt.NoButton, mods))


def _clic(lz, x, y, mods=Qt.NoModifier):
    _mover(lz, x, y, mods)
    pos = lz.a_px(x, y)
    for tipo, botones in ((QEvent.MouseButtonPress, Qt.LeftButton), (QEvent.MouseButtonRelease, Qt.NoButton)):
        QApplication.sendEvent(lz, QMouseEvent(tipo, pos, pos, Qt.LeftButton, botones, mods))


def _modo_con_lienzo(lz):
    """ModoBoceto real con el lienzo puesto: `activo` sin armar la ventana entera."""
    padre = QWidget()
    modo = ModoBoceto(padre)
    modo.lienzo = lz
    return modo


def test_el_menu_restricciones_tiene_desde_referencia_al_lado_de_automaticas():
    grupo = next(g for g in GRUPOS_BOCETO if g[0] == "RESTRICCIONES")
    claves = [m[2] if isinstance(m, tuple) else m for m in grupo[2]]
    assert claves[claves.index("sk_autorestringir") + 1] == "sk_autorestringir_referencia"


def test_la_accion_desde_referencia_existe_y_dice_su_nombre(app):
    modo = ModoBoceto(QWidget())
    a = modo.acciones["sk_autorestringir_referencia"]
    assert a.text() == "Restricciones automáticas desde referencia"
    assert a.toolTip().startswith("<b>Restricciones automáticas desde referencia</b>")


def test_desde_referencia_pide_el_punto_y_abre_el_dialogo_con_ese_datum(lienzo, monkeypatch):
    lz = lienzo
    lz.b.agregar_linea((-10, 0), (10, 0))
    lz.b.agregar_circulo((2, 3), 3)
    lz.resolver()
    lz.encuadrar()
    extremo = next(p for p in lz.b.puntos if lz.b.coords(p) == pytest.approx((10, 0)))
    modo = _modo_con_lienzo(lz)
    vistos = []

    def exec_falso(self):
        vistos.append(self.datum.currentData())
        return QDialog.Accepted
    monkeypatch.setattr(DialogoAutoRestringir, "exec", exec_falso)
    QTimer.singleShot(0, lambda: _clic(lz, 10, 0))     # el clic elige el punto datum
    modo._autorestringir_desde_referencia()
    assert vistos == [extremo]                         # el diálogo abrió ya con ese datum
    assert lz.resultado.gdl == 0                       # y aplicó el resultado (totalmente restringido)
    # las posiciones se midieron desde el datum: el punto elegido es la referencia de las cotas
    assert any(c.tipo in ("distancia_h", "distancia_v") and c.entidades[0] == extremo
               for c in lz.b.cotas.values())


def test_desde_referencia_con_esc_no_abre_el_dialogo(lienzo, monkeypatch):
    lz = lienzo
    lz.b.agregar_linea((0, 0), (10, 0))
    lz.resolver()
    modo = _modo_con_lienzo(lz)
    abiertos = []

    def exec_falso(self):
        abiertos.append(1)
        return QDialog.Accepted
    monkeypatch.setattr(DialogoAutoRestringir, "exec", exec_falso)
    QTimer.singleShot(0, lz.cancelar)
    assert modo._autorestringir_desde_referencia() is None
    assert abiertos == [] and not lz.b.restricciones

# -*- coding: utf-8 -*-
"""P-124: Terminar boceto redibuja el visor una vez. El documento avisa el cambio (`_actualizar` ya redibuja con el
estado nuevo) y `_boceto_terminado` volvía a llamar `_refrescar_visibilidad`: el mismo modelo dos veces, 0,6–0,8 s
cada una en el llavero de Gerardo (texto de un SVG)."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from omnicad import api  # noqa: E402

from PySide6.QtCore import QSettings  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402


@pytest.fixture(scope="module")
def ventana(tmp_path_factory):
    QApplication.instance() or QApplication([])
    from omnicad.ui.preferencias import Preferencias
    from omnicad.ui.ventana import VentanaPrincipal
    ruta = tmp_path_factory.mktemp("p124") / "preferencias.ini"
    v = VentanaPrincipal(prefs=Preferencias(QSettings(str(ruta), QSettings.IniFormat)))
    v.resize(1400, 900)
    v.show()
    QTest.qWait(1)
    yield v
    v.doc.modificado = False
    v.close()
    v.deleteLater()
    QTest.qWait(1)


@pytest.fixture
def v(ventana, monkeypatch):
    s = api.Sesion()
    assert api.llamar(s, "create_box", {"length": 100, "width": 60, "height": 20})["ok"]
    assert api.llamar(s, "create_sketch", {"plane": "XY"})["ok"]
    assert api.llamar(s, "draw_line", {"start_x": 0, "start_y": 0, "end_x": 30, "end_y": 0})["ok"]
    ventana.set_documento(s.doc)
    QTest.qWait(20)
    ventana.mostrados = []
    original = ventana.visor.set_modelo
    monkeypatch.setattr(ventana.visor, "set_modelo", lambda estado, *a, **k: (ventana.mostrados.append(estado),
                                                                               original(estado, *a, **k))[1])
    yield ventana
    if ventana.modo_boceto.activo:
        ventana.modo_boceto.cancelar()
    ventana.doc.modificado = False


def test_terminar_boceto_redibuja_una_vez(v):
    v.editar_operacion(v.doc.operaciones[-1].id)
    assert v.modo_boceto.activo
    v.modo_boceto.lienzo.b.agregar_linea((0, 10), (30, 10))
    v.mostrados.clear()
    assert v.modo_boceto.terminar()
    QTest.qWait(20)
    assert not v.modo_boceto.activo
    assert v.mostrados == [v.doc.estado_final], f"{len(v.mostrados)} redibujos"

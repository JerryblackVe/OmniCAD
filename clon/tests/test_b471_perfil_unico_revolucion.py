# -*- coding: utf-8 -*-
"""B-471: Revolución toma sola el perfil cuando hay uno solo a la vista (como Fusion); con varios o con ninguno, no elige.
Se abre el comando como lo hace la cinta (acción de la ventana); eventos simulados, nunca el cursor real."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from omnicad import api  # noqa: E402
from omnicad.ui.preferencias import Preferencias  # noqa: E402
from omnicad.ui.ventana import VentanaPrincipal  # noqa: E402


def _llamar(s, nombre, **args):
    r = api.llamar(s, nombre, args)
    assert r["ok"], r
    return r["result"]


def _ventana(tmp_path, rectangulos):
    app = QApplication.instance() or QApplication([])
    s = api.Sesion()
    _llamar(s, "create_sketch", name="B1", plane="XY")
    for i in range(rectangulos):
        _llamar(s, "draw_rectangle", sketch="B1", x1=20 * i, y1=0, x2=20 * i + 10, y2=10)
    v = VentanaPrincipal(s.doc, prefs=Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat)))
    v.resize(1000, 700)
    v.show()
    app.processEvents()
    return app, v


def _abrir_revolucion(app, v):
    v.acciones["revolucion"].trigger()
    app.processEvents()
    assert v.panel is not None
    return v.panel


@pytest.fixture
def cerrar():
    ventanas = []
    yield ventanas
    for v in ventanas:
        if v.panel is not None:
            v.panel.cancelar()
        v.doc.modificado = False
        v.close()
        v.deleteLater()


def test_con_un_solo_perfil_revolucion_lo_toma_sola(tmp_path, cerrar):
    app, v = _ventana(tmp_path, 1)
    cerrar.append(v)
    p = _abrir_revolucion(app, v)
    elegidos = p.valores.get("perfiles") or []
    assert len(elegidos) == 1 and elegidos[0]["ref"]["tipo"] == "perfil"


def test_con_dos_perfiles_no_elige_ninguno(tmp_path, cerrar):
    app, v = _ventana(tmp_path, 2)
    cerrar.append(v)
    assert not (_abrir_revolucion(app, v).valores.get("perfiles") or [])


def test_si_el_usuario_ya_eligio_algo_se_respeta(tmp_path, cerrar):
    app, v = _ventana(tmp_path, 1)
    cerrar.append(v)
    unico = v._perfil_unico()
    assert len(unico) == 1
    v._seleccionar(unico)
    p = _abrir_revolucion(app, v)
    assert len(p.valores.get("perfiles") or []) == 1                  # el mismo, una sola vez


def test_un_boceto_que_ya_se_uso_no_se_toma_solo(tmp_path, cerrar):
    """Fusion esconde el boceto consumido por un sólido: su único perfil no se precarga en el siguiente comando."""
    app = QApplication.instance() or QApplication([])
    s = api.Sesion()
    _llamar(s, "create_sketch", name="B1", plane="XY")
    _llamar(s, "draw_rectangle", sketch="B1", x1=0, y1=0, x2=10, y2=10)
    _llamar(s, "extrude", sketch="B1", distance=5)
    v = VentanaPrincipal(s.doc, prefs=Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat)))
    cerrar.append(v)
    v.show()
    app.processEvents()
    assert v._perfil_unico() == []

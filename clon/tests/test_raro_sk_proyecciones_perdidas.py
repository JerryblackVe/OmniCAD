# -*- coding: utf-8 -*-
"""Valores raros del comando de boceto «sk_proyecciones_perdidas» (Administrar proyecciones perdidas).

El diálogo (`DialogoPerdidas`) no tiene campos numéricos: es una lista de proyecciones perdidas con botones
(Re-vincular, Romper vínculo, Borrar geometría, Romper todos, Borrar todos) y la casilla «Atenuar el resto».
Acá se fija que ningún valor raro (lista vacía, ids inexistentes, ids negativos/enormes, casilla on/off) cierre
la app, deje el boceto roto ni emita un mensaje de más de un renglón.
"""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from omnicad.nucleo import geometria as geo
from omnicad.restricciones import Boceto
from omnicad.timeline.parametros import TablaParametros
from omnicad.ui import dialogos_boceto, editor_boceto

app_qt = None


@pytest.fixture
def app():
    global app_qt
    app = QApplication.instance() or QApplication([])
    app_qt = app
    yield app
    app.processEvents()


@pytest.fixture
def lienzo_xy(app):
    lz = editor_boceto.Lienzo(Boceto(), TablaParametros().evaluar, plano=geo.Plano("XY"))
    lz.resize(800, 600)
    lz.ajustar_grilla = False
    lz.show()
    yield lz
    lz.close()
    lz.deleteLater()
    app.processEvents()


REF = {"tipo": "cuerpo", "cuerpo": "op1.c1"}


def _proyeccion_perdida(lz):
    lz.proyectar_forma(geo.caja(20, 10, 10), "proyectar", REF)
    pid = lz.b.proyecciones[0]["id"]
    lz.perdidas = [pid]
    return pid


def test_administrar_perdidas_sin_perdidas_emite_mensaje_de_un_renglon(lienzo_xy):
    lz = lienzo_xy
    mensajes = []
    lz.mensaje.connect(mensajes.append)
    lz.administrar_perdidas()
    assert mensajes, "sin perdidas debe avisar"
    assert all("\n" not in m and "\r" not in m for m in mensajes), mensajes
    assert len(mensajes[-1]) <= 120, mensajes[-1]
    assert lz.isVisible()


@pytest.mark.parametrize("ids", [
    [],
    pytest.param([0], marks=pytest.mark.xfail(reason="B-804: DialogoPerdidas._registro asume id existente (StopIteration)", strict=False)),
    pytest.param([-1], marks=pytest.mark.xfail(reason="B-804: DialogoPerdidas._registro asume id existente (StopIteration)", strict=False)),
    pytest.param([10 ** 9], marks=pytest.mark.xfail(reason="B-804: DialogoPerdidas._registro asume id existente (StopIteration)", strict=False)),
    pytest.param([999999], marks=pytest.mark.xfail(reason="B-804: DialogoPerdidas._registro asume id existente (StopIteration)", strict=False)),
])
def test_dialogo_con_ids_raros_no_rompe_la_app(lienzo_xy, ids):
    lz = lienzo_xy
    lz.perdidas = list(ids)
    mensajes = []
    lz.mensaje.connect(mensajes.append)
    try:
        d = dialogos_boceto.DialogoPerdidas(lz)
    except Exception as e:  # noqa: BLE001
        pytest.fail(f"DialogoPerdidas crasheó con ids {ids!r}: {type(e).__name__}: {e}")
    assert d is not None
    d.deleteLater()
    QApplication.instance().processEvents()
    try:
        from omnicad.restricciones import resolver
        resolver(lz.b)
    except Exception as e:  # noqa: BLE001
        pytest.fail(f"resolver crashed after ids {ids!r}: {e}")
    assert lz.isVisible()


def test_dialogo_con_perdida_valida_botones_no_rompen(lienzo_xy):
    lz = lienzo_xy
    _proyeccion_perdida(lz)
    d = dialogos_boceto.DialogoPerdidas(lz)
    assert d.lista.count() == 1
    d.lista.setCurrentRow(0)
    # atenuar on/off
    d.atenuar.setChecked(True)
    assert lz._brillantes is not None
    d.atenuar.setChecked(False)
    assert lz._brillantes is None
    # romper vínculo de la elegida
    d.b_romper.click()
    assert lz.perdidas == [] and lz.b.proyecciones == []
    assert d.lista.count() == 0
    d.deleteLater()


def test_dialogo_borrar_todos_no_rompe(lienzo_xy):
    lz = lienzo_xy
    _proyeccion_perdida(lz)
    d = dialogos_boceto.DialogoPerdidas(lz)
    d.b_borrar_todos.click()
    assert lz.perdidas == [] and lz.b.proyecciones == []
    assert lz.isVisible()
    d.deleteLater()


@pytest.mark.xfail(reason="B-804: revincular asume id existente (StopIteration)", strict=False)
def test_revincular_con_id_raro_no_rompe(lienzo_xy):
    lz = lienzo_xy
    mensajes = []
    lz.mensaje.connect(mensajes.append)
    for pid in (0, -1, 10 ** 9):
        try:
            lz.revincular(pid)
        except Exception as e:  # noqa: BLE001
            pytest.fail(f"revincular({pid}) crasheó: {type(e).__name__}: {e}")
    assert all("\n" not in m and "\r" not in m for m in mensajes), mensajes
    assert lz.isVisible()

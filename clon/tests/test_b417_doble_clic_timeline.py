# -*- coding: utf-8 -*-
"""B-417: el doble clic sobre un paso NO elegido del timeline abre la edición al primer intento
(el primer clic no debe reconstruir la lista: Qt descarta el doble clic si el ítem apretado ya no existe)."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from test_b366_eliminar_varios import _doc  # noqa: E402
from test_hallazgos_ui import app_qt as app_qt, v as v, ventana as ventana  # noqa: E402, F401


def _doble_clic(v, op_id):
    """Como una persona: apretar, soltar, apretar (doble clic), soltar, con el intervalo real de Qt entre clics."""
    lista = v.timeline.lista
    item = next(lista.item(j) for j in range(lista.count()) if lista.item(j).data(Qt.UserRole) == op_id)
    pos = lista.visualItemRect(item).center()
    vp = lista.viewport()
    QTest.mousePress(vp, Qt.LeftButton, Qt.NoModifier, pos)
    QTest.qWait(60)
    QTest.mouseRelease(vp, Qt.LeftButton, Qt.NoModifier, pos)
    v.timeline.repintar_iconos()                # la lista se rearma entre el primer clic y el doble clic
    QTest.qWait(120)                            # lo que dispare el primer clic (temporizadores, avisos) corre ahora
    QTest.mouseDClick(vp, Qt.LeftButton, Qt.NoModifier, pos)


def test_doble_clic_en_un_paso_no_elegido_abre_la_edicion(v):
    v.set_documento(_doc())
    abiertos = []
    v.timeline.editar.connect(abiertos.append)
    for paso in ("op2", "op4", "op1"):          # extrusiones y un boceto, cada uno sin estar elegido
        abiertos.clear()
        _doble_clic(v, paso)
        assert abiertos == [paso], f"{paso}: el doble clic no abrió la edición ({abiertos})"

# -*- coding: utf-8 -*-
"""Activar / Terminar patrón plano (como Fusion): el patrón plano se ve solo en su modo, nunca en el modelo plegado."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402

from test_chapa import _cara, _doc_pestana  # noqa: E402


@pytest.fixture(scope="module")
def ventana(tmp_path_factory):
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    from omnicad.ui.preferencias import Preferencias
    from omnicad.ui.ventana import VentanaPrincipal
    carpeta = tmp_path_factory.mktemp("patron")
    v = VentanaPrincipal(prefs=Preferencias(QSettings(str(carpeta / "preferencias.ini"), QSettings.IniFormat)))
    v.show()
    yield v
    v.doc.modificado = False
    v.close()
    v.deleteLater()
    QTest.qWait(1)


def test_activar_y_terminar_patron_plano(ventana):
    from omnicad.ui.comando import ContextoComando
    from omnicad.ui.comandos.chapa import PatronPlano
    doc = _doc_pestana()
    ventana.set_documento(doc)
    accion = ventana.acciones["activar_patron_plano"]
    ventana.alternar_patron_plano()                      # sin patrón plano: avisa y no cambia nada
    assert ventana.patron_activo is None and not accion.isChecked()
    op = PatronPlano().construir(dict(cara=[_cara(doc, (50, 40, 2))], ubicacion="en_lugar"), ContextoComando(doc))
    ventana._comando_aceptado(op, False)                 # al crearlo queda a la vista, solo él
    estado = doc.estado_final
    patron = next(c.id for c in estado.cuerpos.values() if c.op_id == op.id)
    assert ventana.patron_activo == patron and accion.isChecked() and accion.text() == "Terminar patrón plano"
    assert ventana._ocultos_efectivos(estado) >= {"op2.c1"} and patron not in ventana._ocultos_efectivos(estado)
    ventana.alternar_patron_plano()                      # Terminar: vuelve la pieza plegada y el patrón se esconde
    assert ventana.patron_activo is None and not accion.isChecked() and accion.text() == "Activar patrón plano"
    ocultos = ventana._ocultos_efectivos(estado)
    assert patron in ocultos and "op2.c1" not in ocultos
    ventana.alternar_patron_plano()                      # Activar otra vez (el último creado)
    assert ventana.patron_activo == patron
    doc.deshacer()                                       # el patrón deja de existir: vuelve el modelo plegado
    assert ventana.patron_activo is None and not accion.isChecked()

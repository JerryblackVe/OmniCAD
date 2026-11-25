# -*- coding: utf-8 -*-
"""PREP del comando de boceto «sk_terminar_auto» (Terminar con AutoConstrain) contra la ayuda de Fusion.

Según `docs/fusion_docs/contenido/fusion-sketch/finish-a-sketch-with-autoconstrain-14a76c1b6f6.md`: Terminar con
AutoConstrain cierra el boceto aplicando restricciones y cotas automáticamente; la ficha «AutoConstrain reference»
muestra cuántas se agregaron y si quedó «Fully Constrained» (0 GDL). El mismo artículo lista como límite «the sketch
has 0 entities» y aclara que, si AutoConstrain no corre, «the sketch still finishes and a notification displays that
constraints and dimensions were not applied». No cambia código de la app: fija lo que ya hace y avisa si deja de hacerlo.
"""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from omnicad.nucleo import geometria as g
from omnicad.restricciones import Boceto, grados_de_libertad, resolver

PLANO = g.Plano("XY")


@pytest.fixture(scope="module")
def app_qt():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


@pytest.fixture
def ventana(app_qt, tmp_path):
    from PySide6.QtCore import QSettings
    from PySide6.QtTest import QTest
    from omnicad.ui.preferencias import Preferencias
    from omnicad.ui.ventana import VentanaPrincipal

    v = VentanaPrincipal(prefs=Preferencias(QSettings(str(tmp_path / "prefs.ini"), QSettings.IniFormat)))
    v.resize(1200, 800)
    v.show()
    QTest.qWait(1)
    from omnicad.timeline.documento import Documento
    v.set_documento(Documento())
    yield v
    if v.modo_boceto.activo:
        v.modo_boceto.cancelar()
    v.doc.modificado = False
    v.close()
    v.deleteLater()
    app_qt.processEvents()


def _iniciar(v, b):
    from PySide6.QtTest import QTest
    v.modo_boceto.iniciar(b, PLANO, {"op": None, "plano": "XY", "marco": PLANO.marco()})
    QTest.qWait(1)


def _valores(b):
    return {k.id: float(k.expresion) for k in b.cotas.values()}


def test_terminar_auto_aplica_la_cota_numerica_y_deja_el_boceto_totalmente_restringido(ventana):
    """Fusion: aplica cotas/restricciones y deja el boceto «Fully Constrained» (0 GDL)."""
    b = Boceto()
    b.agregar_linea((0, 0), (10, 0))
    _iniciar(ventana, b)

    assert ventana.modo_boceto.acciones["sk_terminar_auto"].isEnabled()
    termino, agregado = ventana.modo_boceto.terminar_con_autorestringir()

    assert termino and not ventana.modo_boceto.activo
    assert len(agregado) == 3                       # horizontal + fijo + la cota de largo
    boceto = ventana.modo_boceto.boceto
    assert len(boceto.cotas) == 1
    assert float(next(iter(boceto.cotas.values())).expresion) == pytest.approx(10.0)   # el largo de la recta
    assert grados_de_libertad(boceto, _valores(boceto)) == 0
    assert resolver(boceto, _valores(boceto)).ok


def test_terminar_auto_en_boceto_vacio_termina_igual_y_no_agrega_restricciones(ventana):
    """Fusion: con 0 entidades no corre AutoConstrain, pero el boceto cierra y avisa que no se aplicó nada."""
    _iniciar(ventana, Boceto())
    mensajes = []
    ventana.modo_boceto.lienzo.mensaje.connect(lambda *args: mensajes.append(" ".join(str(a) for a in args)))

    accion = ventana.modo_boceto.acciones["sk_terminar_auto"]
    assert accion.isEnabled()
    accion.trigger()

    assert not ventana.modo_boceto.activo
    assert any("vacío" in m and "sin restringir" in m for m in mensajes), mensajes
    boceto = ventana.modo_boceto.boceto
    assert not boceto.restricciones and not boceto.cotas


@pytest.mark.parametrize("existente", [False, True])
def test_b795_un_deshacer_revierte_terminar_auto(ventana, existente):
    from omnicad.timeline.operaciones import OpBoceto
    b = Boceto()
    b.agregar_linea((0, 0), (10, 0))
    if existente:
        op = OpBoceto(ventana.doc.nuevo_id(), "Boceto1", plano="XY", boceto=b)
        ventana.doc.agregar(op)
        ventana.editar_operacion(op.id)
    else:
        _iniciar(ventana, b)
    antes = ventana.doc.a_dict()
    termino, agregado = ventana.modo_boceto.terminar_con_autorestringir()
    assert termino and agregado
    assert not ventana.modo_boceto.activo
    ventana._deshacer()
    from _calculo_aparte import esperar_barra
    esperar_barra(ventana)
    assert ventana.doc.a_dict()["operaciones"] == antes["operaciones"]
    if existente:
        boceto = ventana.doc.operaciones[0].boceto
        assert not boceto.restricciones and not boceto.cotas

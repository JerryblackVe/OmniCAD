# -*- coding: utf-8 -*-
"""Gestos reales al widget: seleccionar el recurso, transformar sin tocar el modelo, confirmar o cancelar."""
import pytest
from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from omnicad.restricciones import Boceto
from omnicad.restricciones import objetos as ob
from omnicad.timeline.parametros import TablaParametros
from omnicad.ui.editor_boceto import Lienzo
from omnicad.ui.objetos_vectoriales import PanelObjetos


@pytest.fixture
def lienzo():
    app = QApplication.instance() or QApplication([])
    b = Boceto()
    curvas = b.agregar_rectangulo((10, 10), (50, 30))
    oid = ob.crear(b, curvas, "Logotipo")
    lz = Lienzo(b, TablaParametros().evaluar)
    lz.resize(1000, 700)
    lz.ajustar_grilla = False
    lz.objetos.snap = False
    lz.show()
    app.processEvents()
    yield lz, oid
    lz.close()
    lz.deleteLater()
    app.processEvents()


def raton(lz, tipo, pos, mods=Qt.NoModifier):
    q = pos if isinstance(pos, QPointF) else lz.a_px(*pos)
    QApplication.sendEvent(lz, QMouseEvent(tipo, q, lz.mapToGlobal(q),
                                          Qt.NoButton if tipo == QEvent.MouseMove else Qt.LeftButton,
                                          Qt.NoButton if tipo == QEvent.MouseButtonRelease else Qt.LeftButton, mods))


def clic(lz, pos, mods=Qt.NoModifier):
    raton(lz, QEvent.MouseButtonPress, pos, mods)
    raton(lz, QEvent.MouseButtonRelease, pos, mods)


def test_clic_interior_arrastre_cacheado_esc_y_un_solo_deshacer(lienzo, monkeypatch):
    lz, oid = lienzo
    clic(lz, (20, 15))
    assert lz.seleccion == [oid]
    assert lz._punto_cercano(lz.a_px(10, 10)) is None
    assert len(lz.objetos.manijas()) == 10  # ocho escalas, giro y pivote
    antes = lz.b.a_dict()
    raton(lz, QEvent.MouseButtonPress, (20, 15))
    # El gesto no ejecuta ni el solver ni el generador de geometría exacta.
    llamadas = []
    resolver = lz.resolver
    monkeypatch.setattr(lz, "resolver", lambda *a, **k: llamadas.append("solver") or resolver(*a, **k))
    for x in range(22, 70, 2):
        raton(lz, QEvent.MouseMove, (x, 25))
    assert llamadas == [] and lz.b.a_dict() == antes
    QTest.keyClick(lz, Qt.Key_Escape)
    raton(lz, QEvent.MouseButtonRelease, (68, 25))
    assert lz.b.a_dict() == antes
    raton(lz, QEvent.MouseButtonPress, (20, 15))
    raton(lz, QEvent.MouseMove, (60, 25))
    raton(lz, QEvent.MouseButtonRelease, (60, 25))
    assert ob.caja(lz.b, [oid]) == pytest.approx((50, 20, 90, 40))
    assert len(lz.historial) == 1 and len(llamadas) == 1
    lz.deshacer()
    assert lz.b.a_dict() == antes
    lz.rehacer()
    assert ob.caja(lz.b, [oid]) == pytest.approx((50, 20, 90, 40))


def test_ocho_asas_escala_proporcional_e_independiente_y_pivote(lienzo):
    lz, oid = lienzo
    clic(lz, (20, 15))
    asa = lz.objetos.manijas()["escala4"]
    raton(lz, QEvent.MouseButtonPress, asa)
    raton(lz, QEvent.MouseMove, (90, 50))
    raton(lz, QEvent.MouseButtonRelease, (90, 50))
    assert ob.caja(lz.b, [oid]) == pytest.approx((10, 10, 90, 50))
    lz.b.objetos[oid]["proporciones"] = False
    asa = lz.objetos.manijas()["escala3"]
    raton(lz, QEvent.MouseButtonPress, asa)
    raton(lz, QEvent.MouseMove, (130, 30))
    raton(lz, QEvent.MouseButtonRelease, (130, 30))
    assert ob.caja(lz.b, [oid]) == pytest.approx((10, 10, 130, 50))
    antes = lz.b.geometria()
    lz.objetos.editar_pivote = True
    asa = lz.objetos.manijas()["pivote"]
    raton(lz, QEvent.MouseButtonPress, asa)
    raton(lz, QEvent.MouseMove, (5, 5))
    raton(lz, QEvent.MouseButtonRelease, (5, 5))
    assert ob.pivote(lz.b, oid) == pytest.approx((5, 5)) and lz.b.geometria() == antes


def test_panel_tecleo_medidas_invalidas_y_modo_perfiles(lienzo):
    lz, oid = lienzo
    panel = PanelObjetos(lz.objetos, lz)
    panel.move(700, 0)
    clic(lz, (20, 15))
    panel.show()
    campo = panel.campos["ancho"]
    campo.setFocus()
    campo.selectAll()
    QTest.keyClicks(campo, "60 mm")
    assert lz.objetos.previa is not None
    QTest.keyClick(campo, Qt.Key_Return)
    assert ob.caja(lz.b, [oid])[2] - ob.caja(lz.b, [oid])[0] == pytest.approx(60)
    antes = lz.b.a_dict()
    campo.selectAll()
    QTest.keyClicks(campo, "-4")
    QTest.keyClick(campo, Qt.Key_Return)
    assert panel.error.text() and lz.b.a_dict() == antes
    campo.setModified(False)
    QTest.mouseClick(panel.perfiles, Qt.LeftButton, pos=QPoint(8, panel.perfiles.height() // 2))
    assert panel.perfiles.isChecked() and lz.objetos.modo_perfiles
    clic(lz, (30, 20))
    assert lz.perfiles_sel and not lz.seleccion
    panel.close()

# -*- coding: utf-8 -*-
"""B-473: después de Aceptar un Chaflán (y su gemelo, Empalme) no queda nada del comando en la vista: ni la flecha azul
del asa, ni su caja de valor, ni la previa; tampoco un rato después (un temporizador tardío no lo vuelve a dibujar).
Como una persona: clic en la arista del visor, Aceptar con el botón o con Enter en la caja junto al asa. Eventos
simulados al widget, nunca el cursor real."""
import numpy as np
import pytest
from PySide6.QtCore import QEvent, QPointF, QSettings, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from _calculo_aparte import esperar_barra
from omnicad.nucleo import motor
from omnicad.timeline.documento import Documento
from omnicad.timeline.operaciones import OpPrimitiva
from omnicad.ui.comandos.modificar import Chaflan, Empalme
from omnicad.ui.manipuladores import CajaValor
from omnicad.ui.preferencias import Preferencias
from omnicad.ui.ventana import VentanaPrincipal


@pytest.fixture
def ventana(tmp_path):
    app = QApplication.instance() or QApplication([])
    with motor.fijar_motor("opencascade"):
        v = VentanaPrincipal(prefs=Preferencias(QSettings(str(tmp_path / "prefs.ini"), QSettings.IniFormat)))
        doc = Documento()
        doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="40", largo="40", alto="40"))
        v.set_documento(doc)
        v.resize(1200, 800)
        v.show()
        app.processEvents()
        v.visor.encuadrar()
        yield v
        if v.panel is not None:
            v.panel.cancelar()
        v.doc.modificado = False
        v.close()
        v.deleteLater()
        app.processEvents()


def _raton(w, tipo, p, boton, botones):
    p = QPointF(float(p[0]), float(p[1]))
    QApplication.sendEvent(w, QMouseEvent(tipo, p, w.mapToGlobal(p), boton, botones, Qt.NoModifier))


def _restos(v):
    return ([k for k in ("manipuladores", "previa_comando", "seleccion") if k in v.visor._capas]
            + [c for c in v.visor.findChildren(CajaValor) if c.isVisible()])


@pytest.mark.parametrize("comando, clave", [(Chaflan, "distancia"), (Empalme, "radio")])
@pytest.mark.parametrize("como", ["boton", "enter_en_la_caja"])
def test_al_aceptar_no_queda_la_flecha_ni_la_caja(ventana, comando, clave, como):
    v = ventana
    panel = v.ejecutar_comando(comando())
    q = v.visor.proyectar(np.array((14.0, 0.0, 40.0)))           # clic sobre la arista de arriba, fuera del medio
    _raton(v.visor, QEvent.MouseMove, (q.x(), q.y()), Qt.NoButton, Qt.NoButton)
    _raton(v.visor, QEvent.MouseButtonPress, (q.x(), q.y()), Qt.LeftButton, Qt.LeftButton)
    _raton(v.visor, QEvent.MouseButtonRelease, (q.x(), q.y()), Qt.LeftButton, Qt.NoButton)
    QTest.qWait(300)
    assert len(panel.valores["aristas"]) == 1
    caja = panel.manipuladores.cajas[clave]
    caja.setFocus()
    caja.selectAll()
    QTest.keyClicks(caja, "4")
    QTest.qWait(600)
    assert "manipuladores" in v.visor._capas                     # la flecha azul está a la vista antes de Aceptar
    gestor = panel.manipuladores
    if como == "boton":
        QTest.mouseClick(panel.boton_ok, Qt.LeftButton)
    else:
        QTest.keyClick(caja, Qt.Key_Return)
    esperar_barra(v)
    assert v.panel is None and len(v.doc.operaciones) == 2
    assert gestor._cerrado and not gestor.manips and not gestor.cajas
    assert _restos(v) == []
    _raton(v.visor, QEvent.MouseMove, (q.x(), q.y()), Qt.NoButton, Qt.NoButton)    # el cursor pasa por donde estaba
    QTest.qWait(800)                                             # los temporizadores de previa y refinado ya saltaron
    assert _restos(v) == []

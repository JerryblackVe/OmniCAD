# -*- coding: utf-8 -*-
"""B-623: en Sólido › Dividir cuerpo, elegir la herramienta primero y después el cuerpo (el orden de Fusion, o el
inverso si se toca el plano antes) ya no deja el panel pidiendo «Seleccioná el cuerpo.» ni pisa la herramienta:
el clic del cuerpo entra a «Cuerpo para dividir»."""
import numpy as np
import pytest
from PySide6.QtCore import QPoint, QSettings, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from omnicad.timeline.documento import Documento
from omnicad.timeline.operaciones import OpPlano, OpPrimitiva
from omnicad.ui.comandos import CATALOGO
from omnicad.ui.preferencias import Preferencias
from omnicad.ui.ventana import VentanaPrincipal


@pytest.fixture
def ventana(tmp_path):
    """Una caja de 20 mm y un plano de construcción a z = 40 (arriba: el clic no lo tapa la caja)."""
    app = QApplication.instance() or QApplication([])
    doc = Documento()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="20", largo="20", alto="20", x="-10"))
    doc.agregar(OpPlano(doc.nuevo_id(), "Plano1", base="XY", distancia="40 mm"))
    v = VentanaPrincipal(doc, prefs=Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat)))
    v.resize(1280, 800)
    v.show()
    QTest.qWait(100)
    v.visor.encuadrar()
    QTest.qWait(100)
    yield v
    if v.panel is not None:
        v.panel.cancelar()
    v.doc.modificado = False
    v.close()
    v.deleteLater()
    app.processEvents()


def _clic(visor, punto):
    """Un clic de la persona en el visor (el panel escucha `entidad_elegida` y `clic_vacio`)."""
    q = visor.proyectar(np.array(punto, float))
    assert q is not None, f"el punto {punto} no se ve"
    QTest.mouseClick(visor, Qt.LeftButton, Qt.NoModifier, QPoint(int(q.x()), int(q.y())))
    QTest.qWait(80)


def test_b623_elegir_la_herramienta_primero_y_despues_el_cuerpo(ventana):
    v = ventana
    p = v.ejecutar_comando(CATALOGO["dividir_cuerpo"]())
    assert p.activa.clave == "cuerpo" and not p.valores["cuerpo"]

    _clic(v.visor, [0.0, 0.0, 40.0])                 # el plano: no lo acepta «Cuerpo», pasa a «Herramientas»
    assert [h["ref"]["tipo"] for h in p.valores["herramienta"]] == ["plano"]
    assert p.activa.clave == "cuerpo"                # el campo que falta queda activo (antes seguía en la herramienta)

    _clic(v.visor, [0.0, 10.0, 10.0])                # el cuerpo: tiene que entrar a «Cuerpo para dividir»
    assert [h["ref"]["cuerpo"] for h in p.valores["cuerpo"]] == ["op1.c1"]
    assert [h["ref"]["tipo"] for h in p.valores["herramienta"]] == ["plano"]     # y la herramienta no se pisa
    assert "Seleccioná el cuerpo" not in p.mensaje.text()
    op = p.comando.construir(p.valores, p.ctx)       # el comando se puede aceptar con lo elegido
    assert op.p["cuerpo"] == "op1.c1" and op.p["herramienta"]["tipo"] == "plano"

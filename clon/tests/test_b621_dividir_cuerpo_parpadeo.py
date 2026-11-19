# -*- coding: utf-8 -*-
"""B-621: comprobar los sólidos que recibe el visor durante Dividir cuerpo."""
import numpy as np
import pytest
from PySide6.QtCore import QPoint, QSettings, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from omnicad.nucleo import geometria as geo
from omnicad.timeline.documento import Documento
from omnicad.timeline.operaciones import OpPlano, OpPrimitiva
from omnicad.ui.comandos import CATALOGO
from omnicad.ui.preferencias import Preferencias
from omnicad.ui.ventana import VentanaPrincipal


@pytest.fixture
def ventana(tmp_path):
    app = QApplication.instance() or QApplication([])
    doc = Documento()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="20", largo="20", alto="20", x="-10"))
    doc.agregar(OpPlano(doc.nuevo_id(), "Plano1", base="XY", distancia="10 mm"))
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
    q = visor.proyectar(np.array(punto, float))
    assert q is not None, f"el punto {punto} no se ve"
    QTest.mouseClick(visor, Qt.LeftButton, Qt.NoModifier, QPoint(int(q.x()), int(q.y())))
    QTest.qWait(80)


def test_b621_dividir_cuerpo_no_envia_una_pieza_plana_al_visor(ventana, monkeypatch):
    v = ventana
    estados = []
    capas = []
    set_modelo = v.visor.set_modelo
    set_capa = v.visor.set_capa

    def registrar_modelo(estado, *args, **kwargs):
        set_modelo(estado, *args, **kwargs)
        estados.append([(len(geo.solidos(c.forma)), geo.volumen(c.forma)) for c in estado.cuerpos.values()])

    def registrar_capa(nombre, primitivas):
        set_capa(nombre, primitivas)
        if nombre == "seleccion":
            capas.append(primitivas)

    monkeypatch.setattr(v.visor, "set_modelo", registrar_modelo)
    monkeypatch.setattr(v.visor, "set_capa", registrar_capa)
    panel = v.ejecutar_comando(CATALOGO["dividir_cuerpo"]())
    _clic(v.visor, [0, 10, 20])   # cara superior de la caja
    _clic(v.visor, [14, 10, 10])  # parte del plano que sobresale de la caja
    QTest.qWait(300)
    assert [h["ref"]["tipo"] for h in panel.valores["herramienta"]] == ["plano"]
    assert [h["ref"]["cuerpo"] for h in panel.valores["cuerpo"]] == ["op1.c1"]
    QTest.mouseClick(panel.boton_ok, Qt.LeftButton)
    QTest.qWait(100)

    assert len(v.doc.estado_final.cuerpos) == 2
    for estado in estados:
        assert sum(volumen for _, volumen in estado) == pytest.approx(8000, abs=1e-6)
        assert all(solidos == 1 and volumen > 0 for solidos, volumen in estado)
    assert [volumen for _, volumen in estados[-1]] == pytest.approx([4000, 4000], abs=1e-6)
    assert capas[-1] is None

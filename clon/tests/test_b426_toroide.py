"""B-426: los diámetros del toroide nombran el círculo de referencia y el tubo, no el agujero."""
import math

import numpy as np
import pytest
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeVertex
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
from OCP.gp import gp_Pnt
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from omnicad import api
from omnicad.nucleo import geometria as geo
from omnicad.ui.comando import ContextoComando, PanelComando
from omnicad.ui.comandos import CATALOGO
from omnicad.ui.visor3d import Visor3D


@pytest.fixture(scope="module")
def app_qt():
    return QApplication.instance() or QApplication([])


def _llamar(sesion, nombre, **argumentos):
    respuesta = api.llamar(sesion, nombre, argumentos)
    assert respuesta["ok"], respuesta
    return respuesta["result"]


def _comprobar_agujero(forma, diametro=30):
    centro = BRepBuilderAPI_MakeVertex(gp_Pnt(0, 0, 0)).Vertex()
    distancia = BRepExtrema_DistShapeShape(centro, forma)
    assert distancia.IsDone()
    assert 2 * distancia.Value() == pytest.approx(diametro, abs=1e-6)
    assert geo.es_valida(forma)


@pytest.mark.parametrize("clave", ["toroide", "sup_toroide"])
def test_el_panel_nombra_los_diametros_y_explica_el_agujero(app_qt, clave):
    sesion = api.Sesion()
    visor = Visor3D()
    panel = PanelComando(CATALOGO[clave](), ContextoComando(sesion.doc), visor)
    panel.show()
    try:
        assert panel.etiquetas["diametro"].text() == "Diámetro del toroide"
        assert panel.etiquetas["diametro_tubo"].text() == "Diámetro del tubo"
        QTest.mouseClick(panel.boton_ayuda, Qt.LeftButton)
        assert panel.ayuda.isVisible()
        assert "línea central" in panel.ayuda.text()
        assert "30 mm" in panel.ayuda.text()
        for clave_campo, valor in (("diametro", "40"), ("diametro_tubo", "10")):
            campo = panel.widgets[clave_campo]
            QTest.mouseClick(campo, Qt.LeftButton)
            QTest.keyClick(campo, Qt.Key_A, Qt.ControlModifier)
            QTest.keyClicks(campo, valor)
        aceptadas = []
        panel.aceptado.connect(aceptadas.append)
        QTest.mouseClick(panel.boton_ok, Qt.LeftButton)
        assert len(aceptadas) == 1, panel.mensaje.text()
        sesion.doc.agregar(aceptadas[0])
        _comprobar_agujero(next(iter(sesion.doc.estado_final.cuerpos.values())).forma)
    finally:
        if not panel.cerrando:
            panel.cancelar()
        panel.deleteLater()
        visor.deleteLater()


@pytest.mark.parametrize("posicion, agujero", [("inside", 20), ("center", 30), ("outside", 40)])
def test_la_api_documenta_el_diametro_de_referencia_y_mide_el_agujero(posicion, agujero):
    sesion = api.Sesion()
    _llamar(sesion, "create_torus", major_diameter=40, minor_diameter=10, position=posicion)
    forma = next(iter(sesion.doc.estado_final.cuerpos.values())).forma
    _comprobar_agujero(forma, agujero)
    ficha = next(h for h in api.catalogo() if h["nombre"] == "create_torus")
    assert "línea central" in ficha["descripcion"]
    assert "30 mm" in ficha["descripcion"]


def test_radios_publicados_y_receta_antigua_conservan_geometria_al_reabrir(tmp_path):
    sesion = api.Sesion()
    _llamar(sesion, "create_torus", major_radius=20, minor_radius=5)
    receta = _llamar(sesion, "get_recipe")["recipe"]
    parametros = receta["operaciones"][0]["params"]
    assert float(parametros["radio_mayor"]) == 20
    assert float(parametros["radio_menor"]) == 5
    parametros.pop("posicion_toroide")  # Las recetas anteriores a Position no guardaban esta clave.
    antigua = api.Sesion()
    _llamar(antigua, "apply_recipe", recipe=receta)
    ruta = str(tmp_path / "toroide_antiguo.omnicad")
    _llamar(antigua, "save_document", path=ruta)
    reabierta = api.Sesion()
    _llamar(reabierta, "open_document", path=ruta)
    for documento in (sesion.doc, antigua.doc, reabierta.doc):
        forma = next(iter(documento.estado_final.cuerpos.values())).forma
        _comprobar_agujero(forma)
        assert geo.volumen(forma) == pytest.approx(1000 * math.pi ** 2, rel=1e-6)
        assert np.allclose(geo.caja_envolvente(forma), [(-25, -25, -5), (25, 25, 5)], atol=1e-6)

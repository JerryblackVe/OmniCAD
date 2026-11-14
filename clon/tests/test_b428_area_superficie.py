"""B-428: la barra mide el área de superficies, incluso cerradas, al seleccionarlas por API."""
import math

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from omnicad import api
from omnicad.ui.preferencias import Preferencias
from omnicad.ui.puente import PuenteAgentes
from omnicad.ui.ventana import VentanaPrincipal


@pytest.fixture(scope="module")
def ventana(tmp_path_factory):
    app = QApplication.instance() or QApplication([])
    ruta = tmp_path_factory.mktemp("b428") / "preferencias.ini"
    v = VentanaPrincipal(prefs=Preferencias(QSettings(str(ruta), QSettings.IniFormat)))
    v.resize(1280, 800)
    v.show()
    yield v
    v.doc.modificado = False
    v.close()
    v.deleteLater()
    QTest.qWait(1)
    assert app


def _llamar(sesion, nombre, **args):
    respuesta = api.llamar(sesion, nombre, args)
    assert respuesta["ok"], respuesta
    return respuesta["result"]


def _elegir(ventana, sesion, cuerpos):
    ventana.set_documento(sesion.doc)
    vivo = PuenteAgentes(ventana).sesion
    respuesta = _llamar(vivo, "select_entities", kind="body", selector=cuerpos)
    assert respuesta["count"] == len(cuerpos)
    return ventana.timeline.estado.toolTip()


@pytest.mark.parametrize("herramienta,etiqueta,valor,potencia", [
    ("create_surface_cylinder", "Área", 800 * math.pi, 2),
    ("create_cylinder", "Volumen", 3000 * math.pi, 3),
])
@pytest.mark.parametrize("unidad", ["mm", "cm"])
def test_la_barra_mide_segun_el_tipo_y_las_unidades(ventana, herramienta, etiqueta, valor, potencia, unidad):
    sesion = api.Sesion()
    creado = _llamar(sesion, herramienta, radius=10, height=30)
    cuerpo = creado["bodies_created"][0]["id"]
    propiedades = _llamar(sesion, "get_physical_properties", bodies=[cuerpo])["bodies"][0]
    if etiqueta == "Área":
        assert propiedades["type"] == "surface" and propiedades["volume"] is None
    _llamar(sesion, "set_document_units", length=unidad)
    factor = 10 if unidad == "cm" else 1
    esperado = f"1 Cuerpo | {etiqueta}: {valor / factor ** potencia:.3f} {unidad}^{potencia}"
    assert _elegir(ventana, sesion, [cuerpo]) == esperado
    assert ventana.timeline.estado.text() == esperado


def test_varias_superficies_suman_area_y_mezcladas_no_anuncian_volumen(ventana):
    sesion = api.Sesion()
    cuerpos = [_llamar(sesion, "create_surface_cylinder", radius=10, height=30, x=x)["bodies_created"][0]["id"]
               for x in (0, 50)]
    assert _elegir(ventana, sesion, cuerpos) == f"2 Cuerpos | Área: {1600 * math.pi:.3f} mm^2"
    solido = _llamar(sesion, "create_cylinder", radius=10, height=30, x=100)["bodies_created"][0]["id"]
    assert _elegir(ventana, sesion, [cuerpos[0], solido]) == "2 Cuerpos"


def test_la_malla_conserva_su_resumen(ventana):
    sesion = api.Sesion()
    solido = _llamar(sesion, "create_box", length=10, width=20, height=30)["bodies_created"][0]["id"]
    malla = _llamar(sesion, "tessellate", bodies=[solido])["bodies_created"][0]["id"]
    assert sesion.cuerpo(malla).tipo == "malla"
    assert _elegir(ventana, sesion, [malla]) == "1 Cuerpo"

# -*- coding: utf-8 -*-
"""B-443: clic derecho › Propiedades (cuerpo y componente), el botón de la cinta y la herramienta get_properties."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from omnicad import api
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QDialog, QMenu, QTableWidget


def _sesion():
    s = api.Sesion()
    assert api.llamar(s, "create_box", {"length": 20, "width": 20, "height": 20})["ok"]       # 8 cm³
    assert api.llamar(s, "set_material", {"bodies": ["op1.c1"], "material": "Acero"})["ok"]
    assert api.llamar(s, "create_component", {"bodies": ["op1.c1"], "name": "Tapa"})["ok"]
    return s


def test_get_properties_de_cuerpo_y_de_componente():
    s = _sesion()
    c = api.llamar(s, "get_properties", {"item": "op1.c1"})["result"]
    assert c["kind"] == "body" and c["component"] == "Tapa" and c["physical"]["total"]["volume"] == pytest.approx(8000)
    assert c["physical"]["total"]["mass_g"] == pytest.approx(62.8, abs=0.1)
    k = api.llamar(s, "get_properties", {"item": "Tapa"})["result"]
    assert k["kind"] == "component" and k["bodies_count"] == 1 and k["physical"]["total"]["volume"] == pytest.approx(8000)
    assert api.llamar(s, "get_properties", {"item": "NoExiste"})["ok"] is False


@pytest.fixture(scope="module")
def ventana(tmp_path_factory):
    from PySide6.QtCore import QSettings
    from PySide6.QtWidgets import QApplication
    from omnicad.ui.preferencias import Preferencias
    from omnicad.ui.ventana import VentanaPrincipal
    QApplication.instance() or QApplication([])
    ruta = tmp_path_factory.mktemp("b443") / "preferencias.ini"
    w = VentanaPrincipal(prefs=Preferencias(QSettings(str(ruta), QSettings.IniFormat)))
    w.resize(1280, 800)
    w.show()
    QTest.qWait(1)
    yield w
    w.doc.modificado = False
    w.close()
    w.deleteLater()


@pytest.fixture
def v(ventana):
    s = _sesion()
    ventana.set_documento(s.doc)
    QTest.qWait(30)
    yield ventana
    ventana.doc.modificado = False


def _abre_dialogo(v, accion):
    v._dialogo_propiedades = None
    accion.trigger()
    d = v._dialogo_propiedades
    assert isinstance(d, QDialog) and d.isVisible()
    tabla = d.findChild(QTableWidget)
    celdas = {tabla.item(i, 0).text(): tabla.item(i, 1).text() for i in range(tabla.rowCount())}
    d.close()
    return celdas


def test_menu_contextual_del_cuerpo_abre_propiedades(v):
    from omnicad.ui import acciones_navegador as an
    menu = an.menu(v, v.navegador.item("op1.c1"))
    celdas = _abre_dialogo(v, next(a for a in menu.actions() if a.text() == "Propiedades"))
    assert celdas["Nombre"] and celdas["Componente"] == "Tapa" and "62,8" in celdas["Masa"].replace(".", ",")


def test_menu_contextual_del_componente_tiene_propiedades(v, monkeypatch):
    menus = []

    class MenuSinAbrir(QMenu):                      # el menú real, sin abrirlo (exec bloquearía la prueba)
        def exec(self, *a):
            menus.append(self)
    monkeypatch.setattr("omnicad.ui.navegador.QMenu", MenuSinAbrir)
    comp = next(iter(v.doc.estado_final.componentes))
    item = v.navegador.item(comp)
    v.navegador.arbol.setCurrentItem(item)
    v.navegador._menu(v.navegador.arbol.visualItemRect(item).center())
    celdas = _abre_dialogo(v, next(a for a in menus[-1].actions() if a.text() == "Propiedades"))
    assert celdas["Nombre"] == "Tapa" and celdas["Cuerpos"] == "1"


def test_la_cinta_y_el_menu_radial_tienen_propiedades(v):
    assert "propiedades" in v.acciones
    v._seleccionar([v._hits_cuerpos(["op1.c1"])[0]])
    assert any(f and f[0] == "Propiedades" for f in v._contexto_radial())
    _abre_dialogo(v, v.acciones["propiedades"])

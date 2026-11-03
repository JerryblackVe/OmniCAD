# -*- coding: utf-8 -*-
"""B-185: al elegir un cuerpo en el navegador, la marca «De dónde viene» va solo a ese cuerpo (un paso puede
crear varios) y la fila elegida se sigue viendo elegida."""
import pytest
from PySide6.QtCore import QPoint, QRect, QSettings, Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QStyle, QStyleOptionViewItem

from omnicad import api
from omnicad.nucleo import referencias as refs
from omnicad.timeline.origen import origen_de
from omnicad.ui import temas
from omnicad.ui.navegador import ROL_ORIGEN


@pytest.fixture(scope="module")
def ventana(tmp_path_factory):
    from omnicad.ui.preferencias import Preferencias
    from omnicad.ui.ventana import VentanaPrincipal
    app = QApplication.instance() or QApplication([])
    prefs = QSettings(str(tmp_path_factory.mktemp("b185") / "prefs.ini"), QSettings.IniFormat)
    v = VentanaPrincipal(prefs=Preferencias(prefs))
    v.resize(1280, 800)
    v.show()
    app.processEvents()
    yield v
    v.doc.modificado = False
    v.close()
    v.deleteLater()
    app.processEvents()


def _documento(con_empalme=False):
    """Una caja y un patrón que la copia dos veces: el paso del patrón crea DOS cuerpos (como un STEP importado)."""
    s = api.Sesion()
    assert api.llamar(s, "create_box", {"length": 40, "width": 30, "height": 20})["ok"]
    assert api.llamar(s, "rectangular_pattern", {"bodies": ["op1.c1"], "x_count": 3, "x_spacing": 20})["ok"]
    if con_empalme:
        assert api.llamar(s, "fillet", {"edges": "|Z", "radius": 2, "body": "op2.c1"})["ok"]
    return s.doc


@pytest.fixture
def v(ventana):
    ventana.set_documento(_documento())
    yield ventana
    ventana.doc.modificado = False


def _clicar_fila(v, clave):
    arbol = v.navegador.arbol
    it = v.navegador.item(clave)
    arbol.scrollToItem(it)
    QTest.mouseClick(arbol.viewport(), Qt.LeftButton, Qt.NoModifier, arbol.visualItemRect(it).center())


def _cara_del_empalme(doc, cid):
    """La referencia de una cara que el empalme modificó (la que tiene el paso del empalme en «modificaron»)."""
    cuerpo = doc.estado_final.cuerpos[cid]
    for sub in refs.subformas(cuerpo.forma, "cara"):
        ref = refs.referencia(cuerpo.id, sub, cuerpo.forma)
        o = origen_de(doc, ref)
        if o and "op3" in o["modificaron"]:
            return ref
    raise AssertionError("Ninguna cara quedó modificada por el empalme.")


def _colores_de_la_fila(v, clave):
    """Los colores con los que se pinta la fila del navegador (relleno, borde y texto)."""
    arbol = v.navegador.arbol
    it = v.navegador.item(clave)
    opcion = QStyleOptionViewItem()
    opcion.rect = QRect(QPoint(0, 0), arbol.visualItemRect(it).size())      # la imagen arranca en (0, 0)
    opcion.state = QStyle.State_Selected if it.isSelected() else QStyle.State_None
    opcion.font = it.font(0)
    imagen = QImage(opcion.rect.size(), QImage.Format_ARGB32)
    imagen.fill(Qt.transparent)
    pintor = QPainter(imagen)
    v.navegador.delegado.paint(pintor, opcion, arbol.indexFromItem(it))
    pintor.end()
    return {imagen.pixelColor(x, y).name() for x in range(imagen.width()) for y in range(imagen.height())}


def _marca_del_timeline(v, op_id):
    """La marca de origen del paso en el timeline («creo» o «modifico»)."""
    from omnicad.ui.panel_timeline import ROL_ORIGEN as ROL_TIMELINE
    for i in range(v.timeline.lista.count()):
        it = v.timeline.lista.item(i)
        if it.data(Qt.UserRole) == op_id:
            return it.data(ROL_TIMELINE)
    return None


def test_elegir_un_cuerpo_marca_solo_ese_cuerpo(v):
    _clicar_fila(v, "op2.c1")
    assert v.seleccion and v.seleccion[0]["ref"]["cuerpo"] == "op2.c1"
    assert v.navegador.item("op2.c1").data(0, ROL_ORIGEN) == "creo"
    assert v.navegador.item("op2.c2").data(0, ROL_ORIGEN) is None      # el otro cuerpo del mismo paso
    assert v.navegador.item("op1.c1").data(0, ROL_ORIGEN) is None
    assert _marca_del_timeline(v, "op2") == "creo"                     # el timeline sigue marcando el paso


def test_el_empalme_no_marca_el_otro_cuerpo(ventana):
    ventana.set_documento(_documento(con_empalme=True))
    ventana.seleccionar_entidades([_cara_del_empalme(ventana.doc, "op2.c1")])
    assert ventana.navegador.item("op2.c1").data(0, ROL_ORIGEN) == "creo"
    assert ventana.navegador.item("op2.c2").data(0, ROL_ORIGEN) is None      # la marca suave no va al otro
    assert _marca_del_timeline(ventana, "op2") == "creo"
    assert _marca_del_timeline(ventana, "op3") == "modifico"
    ventana.doc.modificado = False


def test_la_fila_elegida_se_ve_elegida_aunque_tenga_marca_de_origen(v):
    _clicar_fila(v, "op2.c1")
    colores = _colores_de_la_fila(v, "op2.c1")
    assert temas.activo()["seleccion"] in colores          # se ve elegida
    assert temas.ORIGEN["borde"] in colores                 # y con la marca de origen
    assert temas.ORIGEN["creo"] not in colores              # el amarillo no tapa la selección

"""P23: efectos de la selección y de los menús del navegador."""
import pytest
from PySide6.QtCore import QPoint, QSettings, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from omnicad import api
from omnicad.timeline.documento import Documento
from omnicad.timeline.operaciones import OpPrimitiva
from omnicad.ui.navegador import ROL_CLAVE


@pytest.fixture(scope="module")
def ventana(tmp_path_factory):
    from omnicad.ui.preferencias import Preferencias
    from omnicad.ui.ventana import VentanaPrincipal
    app = QApplication.instance() or QApplication([])
    prefs = QSettings(str(tmp_path_factory.mktemp("p23") / "prefs.ini"), QSettings.IniFormat)
    v = VentanaPrincipal(prefs=Preferencias(prefs))
    v.resize(1280, 800)
    v.show()
    app.processEvents()
    yield v
    v.doc.modificado = False
    v.close()
    v.deleteLater()
    app.processEvents()


@pytest.fixture
def v(ventana):
    doc = Documento()
    for i in range(3):
        doc.agregar(OpPrimitiva(doc.nuevo_id(), f"Pieza {i + 1}", forma="caja", x=i * 40,
                               ancho=20, largo=20, alto=20))
    ventana.set_documento(doc)
    yield ventana
    if ventana.panel is not None:
        ventana.panel.cancelar()
    if ventana.modo_boceto.activo:
        ventana.modo_boceto.cancelar()


def elegidos(v):
    return {it.data(0, ROL_CLAVE) for it in v.navegador.arbol.selectedItems()}


def test_clic_en_cuerpo_revela_y_selecciona_en_navegador(v, monkeypatch):
    cid = next(iter(v.doc.estado_final.cuerpos))
    it = v.navegador.item(cid)
    it.parent().setExpanded(False)
    v.navegador.filtro.setText("no coincide")
    hit = v._hits_cuerpos([cid])[0]
    monkeypatch.setattr(v.visor, "elegir_entidad", lambda *_: hit)
    QTest.mouseClick(v.visor, Qt.LeftButton, pos=QPoint(600, 300))
    assert elegidos(v) == {cid}
    assert it.parent().isExpanded() and not it.parent().isHidden()
    assert v.navegador.filtro.text() == ""
    assert v.seleccion[0]["ref"]["cuerpo"] == cid


def test_api_selecciona_en_vivo_y_rechaza_cuerpo_inexistente_sin_cambiar(v, tmp_path):
    from omnicad.ui.puente import PuenteAgentes
    puente = PuenteAgentes(v, archivo=tmp_path / "puente.json")
    cid = next(iter(v.doc.estado_final.cuerpos))
    r = puente.ejecutar("select_bodies", {"bodies": [cid]})
    assert r["ok"] and r["result"]["selected_bodies"] == [cid]
    assert elegidos(v) == {cid}
    assert not puente.ejecutar("select_bodies", {"bodies": ["inexistente"]})["ok"]
    assert elegidos(v) == {cid}
    assert puente.ejecutar("select_bodies", {"bodies": []})["ok"]
    assert not elegidos(v)
    assert api.llamar(api.Sesion(), "select_bodies", {"bodies": []})["error_kind"] == "APP_NOT_RUNNING"

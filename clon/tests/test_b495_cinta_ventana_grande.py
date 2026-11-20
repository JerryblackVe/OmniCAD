"""B-495: con la ventana grande la cinta no entra en modo compacto ni corta rótulos."""

import pytest
from PySide6.QtCore import QSettings, QSize
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QToolButton

from omnicad.ejemplo import crear_documento_ejemplo
from omnicad.ui.preferencias import Preferencias
from omnicad.ui.ventana import VentanaPrincipal


@pytest.fixture
def ventana(tmp_path):
    app = QApplication.instance() or QApplication([])
    v = VentanaPrincipal(crear_documento_ejemplo(), prefs=Preferencias(
        QSettings(str(tmp_path / "preferencias.ini"), QSettings.IniFormat)))
    v.show()
    QTest.qWaitForWindowExposed(v)
    app.processEvents()
    yield v
    v.doc.modificado = False
    v.close()
    v.deleteLater()
    app.processEvents()


def _botones(v, pestana):
    cinta = v.cinta
    if pestana == "BOCETO":
        cinta.mostrar_contextual("BOCETO")
    else:
        next(b for b in cinta.pestanas if b.toolTip() == pestana).click()
    QApplication.processEvents()
    return cinta.pila.currentWidget().findChildren(QToolButton, "boton_cinta")


@pytest.mark.parametrize("ancho", [1920, 1783])
@pytest.mark.parametrize("pestana", ["BOCETO", "SÓLIDO"])
def test_crear_conserva_todos_sus_iconos_y_ningun_rotulo_se_corta(ventana, ancho, pestana):
    v = ventana
    v.resize(ancho, 900)
    QTest.qWait(30)
    botones = _botones(v, pestana)
    crear = next(b.parentWidget() for b in botones if b.parentWidget().parentWidget().findChild(QToolButton, "titulo_grupo")
                 .text().startswith("CREAR"))      # el botón cuelga de la zona de botones del grupo (P-187); el título, del grupo
    hijos = crear.findChildren(QToolButton, "boton_cinta")
    assert hijos and all(b.isVisible() for b in hijos), (ancho, pestana)
    for b in botones:
        if b.isVisible():
            assert "…" not in b.text()
    for t in v.cinta.pila.currentWidget().findChildren(QToolButton, "titulo_grupo"):
        if t.isVisible():
            ancho_texto = t.fontMetrics().horizontalAdvance(t.text())
            assert t.width() >= ancho_texto, (t.text(), t.width(), ancho_texto)


def test_la_pestana_boceto_no_compacta_a_1920(ventana):
    v = ventana
    v.resize(1920, 900)
    QTest.qWait(30)
    botones = _botones(v, "BOCETO")
    assert all(b.isVisible() for b in botones)


def test_en_800x520_sigue_el_compacto(ventana):
    v = ventana
    v.resize(QSize(800, 520))
    QTest.qWait(30)
    botones = _botones(v, "BOCETO")
    assert sum(b.isVisible() for b in botones) < len(botones)


@pytest.mark.parametrize("ancho", [1100, 1400])
@pytest.mark.parametrize("pestana", ["BOCETO", "SÓLIDO"])
def test_en_anchos_intermedios_cada_boton_queda_dentro_de_su_grupo(ventana, ancho, pestana):
    """Con compactación parcial (algunos grupos sí, otros no) ningún botón visible se sale ni se superpone."""
    v = ventana
    v.resize(ancho, 900)
    QTest.qWait(30)
    botones = _botones(v, pestana)
    visibles = [b for b in botones if b.isVisible()]
    assert visibles
    for b in visibles:
        assert b.parentWidget().rect().contains(b.geometry()), (ancho, pestana, b.defaultAction().text())
        for otro in visibles:
            if otro is not b and otro.parentWidget() is b.parentWidget():
                assert not b.geometry().intersects(otro.geometry()), (ancho, pestana, b.text(), otro.text())

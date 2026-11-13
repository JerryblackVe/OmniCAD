# -*- coding: utf-8 -*-
"""P-152: miniaturas reales, elección por tarjetas y vista previa sin cambiar lo guardado."""

import json
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, QPointF, QSettings, Qt  # noqa: E402
from PySide6.QtGui import QEnterEvent  # noqa: E402
from PySide6.QtTest import QSignalSpy, QTest  # noqa: E402
from PySide6.QtWidgets import QApplication, QToolButton  # noqa: E402

from omnicad.ui import temas  # noqa: E402
from omnicad.ui.preferencias import DialogoPreferencias, Preferencias  # noqa: E402
from omnicad.ui.selector_temas import miniatura_tema  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def dialogo(qapp, tmp_path, monkeypatch):
    monkeypatch.setenv(temas.VAR_CARPETA, str(tmp_path))
    (tmp_path / "mio.json").write_text(json.dumps({
        "nombre": "Mi tema", "base": "claro_moderno",
        "colores": {"fondo": "#123456", "visor_arriba": "#abcdef"},
    }), encoding="utf-8")
    prefs = Preferencias(QSettings(str(tmp_path / "prefs.ini"), QSettings.IniFormat))
    dlg = DialogoPreferencias(prefs)
    dlg.show()
    QTest.qWait(1)
    yield dlg
    dlg.reject()
    dlg.deleteLater()
    QTest.qWait(1)


def _tarjetas(dialogo):
    return dialogo.selector_temas.findChildren(QToolButton, "tarjeta_tema")


def _tarjeta(dialogo, clave):
    return next(t for t in _tarjetas(dialogo) if t.property("clave_tema") == clave)


def _entrar(widget):
    """Evento de entrada local: no mueve el cursor de la persona que usa la PC."""
    punto = QPointF(widget.rect().center())
    QApplication.sendEvent(widget, QEnterEvent(punto, punto, punto))


def _salir(widget):
    QApplication.sendEvent(widget, QEvent(QEvent.Leave))


@pytest.mark.parametrize("clave", list(temas.INCLUIDOS))
def test_miniatura_conserva_los_colores_reales(qapp, clave):
    colores = temas.INCLUIDOS[clave]["colores"]
    imagen = miniatura_tema(colores).toImage()
    assert (imagen.width(), imagen.height()) == (168, 104)
    assert imagen.pixelColor(160, 3).name() == colores["fondo"]
    assert imagen.pixelColor(110, 28).name() == colores["visor_arriba"]


def test_grilla_incluye_sistema_incluidos_y_propio_con_su_miniatura(dialogo):
    tarjetas = _tarjetas(dialogo)
    disponibles, _avisos = temas.disponibles()
    assert [t.property("clave_tema") for t in tarjetas] == [clave for clave, _nombre, _propio in disponibles]
    assert [t.text() for t in tarjetas] == [nombre + (" (propio)" if propio else "")
                                           for _clave, nombre, propio in disponibles]
    for i, tarjeta in enumerate(tarjetas):
        assert dialogo.selector_temas.layout().getItemPosition(i)[:2] == (i // 3, i % 3)
        assert not tarjeta.icon().isNull()
    propia = _tarjeta(dialogo, "usuario:mio")
    imagen = propia.icon().pixmap(168, 104).toImage()
    assert imagen.pixelColor(160, 3).name() == "#123456"
    assert imagen.pixelColor(110, 28).name() == "#abcdef"
    assert dialogo.controles["general/tema"].isHidden()
    assert [t.property("clave_tema") for t in tarjetas if t.isChecked()] == [temas.DEFECTO]


@pytest.mark.parametrize("clave", ["claro_moderno", "usuario:mio"])
def test_clic_cambia_el_combo_emite_y_se_guarda_al_aplicar(dialogo, clave):
    elegidos = []
    dialogo.tema_elegido.connect(elegidos.append)
    tarjeta = _tarjeta(dialogo, clave)
    dialogo.desplazador.ensureWidgetVisible(tarjeta)
    QTest.mouseClick(tarjeta, Qt.LeftButton)
    assert dialogo.controles["general/tema"].currentData() == clave
    assert elegidos[-1] == clave and tarjeta.isChecked()
    assert sum(t.isChecked() for t in _tarjetas(dialogo)) == 1
    assert dialogo.b_aplicar.isEnabled()
    assert dialogo.prefs["general/tema"] == temas.DEFECTO
    QTest.mouseClick(tarjeta, Qt.LeftButton)
    assert tarjeta.isChecked() and sum(t.isChecked() for t in _tarjetas(dialogo)) == 1
    dialogo.b_aplicar.click()
    assert dialogo.prefs["general/tema"] == clave


def test_cambiar_combo_por_otro_lado_marca_la_tarjeta_y_restablecer_la_sigue(dialogo):
    combo = dialogo.controles["general/tema"]
    combo.setCurrentIndex(combo.findData("minimalista"))
    assert _tarjeta(dialogo, "minimalista").isChecked()
    assert not _tarjeta(dialogo, temas.DEFECTO).isChecked()
    dialogo.b_restablecer.click()
    assert _tarjeta(dialogo, temas.DEFECTO).isChecked()
    assert not _tarjeta(dialogo, "minimalista").isChecked()


def test_hover_espera_300_ms_no_parpadea_entre_tarjetas_y_sale_al_elegido(dialogo):
    combo = dialogo.controles["general/tema"]
    combo.setCurrentIndex(combo.findData("minimalista"))
    elegidos = []
    dialogo.tema_elegido.connect(elegidos.append)
    espia = QSignalSpy(dialogo.tema_elegido)
    primera = _tarjeta(dialogo, "claro_moderno")
    segunda = _tarjeta(dialogo, "azul_profesional")
    _entrar(dialogo.selector_temas)
    _entrar(primera)
    QTest.qWait(150)
    assert elegidos == []
    assert espia.wait(2000)
    assert elegidos == ["claro_moderno"]
    _salir(primera)
    _entrar(segunda)
    QTest.qWait(150)
    assert elegidos == ["claro_moderno"]
    assert espia.wait(2000)
    assert elegidos == ["claro_moderno", "azul_profesional"]
    assert combo.currentData() == "minimalista"
    assert dialogo.prefs["general/tema"] == temas.DEFECTO
    assert dialogo.b_aplicar.isEnabled()
    assert _tarjeta(dialogo, "minimalista").isChecked()
    _salir(segunda)
    _salir(dialogo.selector_temas)
    assert elegidos == ["claro_moderno", "azul_profesional", "minimalista"]


def test_salir_antes_del_plazo_cancela_la_vista_previa(dialogo):
    elegidos = []
    dialogo.tema_elegido.connect(elegidos.append)
    tarjeta = _tarjeta(dialogo, "claro_moderno")
    _entrar(tarjeta)
    _salir(tarjeta)
    _salir(dialogo.selector_temas)
    QTest.qWait(350)
    assert elegidos == []          # nunca se aplicó la vista previa: no hay nada que revertir ni se re-aplica el tema


@pytest.mark.parametrize("tecla", [Qt.Key_Space, Qt.Key_Return, Qt.Key_Enter])
def test_tab_y_tecla_eligen_sin_aceptar_el_dialogo(dialogo, tecla):
    tarjetas = _tarjetas(dialogo)
    tarjetas[0].setFocus()
    QTest.keyClick(tarjetas[0], Qt.Key_Tab)
    assert tarjetas[1].hasFocus()
    QTest.keyClick(tarjetas[1], Qt.Key_Tab)
    assert tarjetas[2].hasFocus()
    elegidos = []
    dialogo.tema_elegido.connect(elegidos.append)
    QTest.keyClick(tarjetas[2], tecla)
    assert dialogo.controles["general/tema"].currentData() == "claro_moderno"
    assert tarjetas[2].isChecked() and elegidos[-1] == "claro_moderno"
    assert dialogo.isVisible()
    assert dialogo.prefs["general/tema"] == temas.DEFECTO


def test_exportar_plantilla_recarga_tarjetas_sin_cambiar_eleccion(dialogo):
    combo = dialogo.controles["general/tema"]
    combo.setCurrentIndex(combo.findData("azul_profesional"))
    elegidos = []
    dialogo.tema_elegido.connect(elegidos.append)
    dialogo._exportar_plantilla()
    tarjetas = _tarjetas(dialogo)
    assert len(tarjetas) == combo.count()
    assert _tarjeta(dialogo, "usuario:mi_tema").text().endswith(" (propio)")
    assert _tarjeta(dialogo, "azul_profesional").isChecked()
    assert combo.currentData() == "azul_profesional" and elegidos == []
    QTest.mouseClick(_tarjeta(dialogo, "usuario:mi_tema"), Qt.LeftButton)
    assert combo.currentData() == "usuario:mi_tema" and elegidos[-1] == "usuario:mi_tema"

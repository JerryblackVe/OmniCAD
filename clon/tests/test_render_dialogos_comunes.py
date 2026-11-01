# -*- coding: utf-8 -*-
"""UI-1: los diálogos de render (Renderizar/Capturar, Lienzo y los paneles flotantes Escena y Aspecto) usan el sistema común de
`ui/formulario.py`: ancho de la tabla `ANCHOS`, secciones con jerarquía, avisos tipados (símbolo y color) y la cabecera movible."""
import os

import pytest


@pytest.fixture(scope="module")
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def test_renderizar_tiene_ancho_fijo_secciones_y_no_se_ensancha_con_el_texto_largo(qapp, tmp_path):
    from PySide6.QtWidgets import QLabel
    from omnicad.ui import render as ur
    from omnicad.ui.formulario import ANCHOS
    d = ur.DialogoRenderizar(None, (640, 480), tmp_path / "a.png")
    d.show()
    assert d.width() == d.minimumWidth() == d.maximumWidth() == ANCHOS["ancho"]
    assert d.minimumSizeHint().width() <= d.width()                    # nada obliga a ensanchar: el combo largo se corta con «…»
    secciones = [lb.text() for lb in d.findChildren(QLabel) if lb.property("rol") == "seccion"]
    assert secciones == ["Tamaño de la imagen", "Calidad", "Salida"]
    d.close()


def test_renderizar_avisa_de_carpeta_inexistente_y_de_imagen_enorme_sin_impedir_renderizar(qapp, tmp_path):
    from omnicad.ui import render as ur
    d = ur.DialogoRenderizar(None, (640, 480), tmp_path / "a.png")
    d.show()
    assert d.mensaje.text() == "" and d.mensaje.isHidden() and d.icono_mensaje.isHidden()
    d.ruta.setText(str(tmp_path / "no_existe" / "a.png"))
    assert "no existe" in d.mensaje.text() and d.icono_mensaje.text() == "⚠" and d.mensaje.property("tipo") == "aviso"
    assert d.mensaje.isVisible()
    d.ruta.setText(str(tmp_path / "a.png"))
    assert d.mensaje.text() == ""
    d.preset.setCurrentIndex(len(ur.PRESETS) - 1)
    d.bloquear.setChecked(False)
    d.ancho.setValue(6000)
    d.alto.setValue(4000)
    assert "24 megapíxeles" in d.mensaje.text() and d.mensaje.isVisible()
    d.ruta.setText("")                                                  # sin ruta no se guarda: nada que avisar de la carpeta
    assert "megapíxeles" in d.mensaje.text()
    assert d.valores()["ancho"] == 6000 and d.valores()["ruta"] == ""   # el aviso no cambia lo que se renderiza
    d.close()


def test_lienzo_tiene_ancho_fijo_y_la_nota_en_tenue(qapp):
    from PySide6.QtWidgets import QLabel
    from omnicad.ui import render as ur
    from omnicad.ui.formulario import ANCHOS
    d = ur.DialogoLienzo(None, 2, True)
    d.show()
    assert d.width() == ANCHOS["normal"] + 40 and d.minimumSizeHint().width() <= d.width()
    nota = next(lb for lb in d.findChildren(QLabel) if lb.text().startswith("Más calidad"))
    assert nota.property("rol") == "tenue"
    assert d.calidad.currentData() == 2 and d.oclusion.isChecked()
    d.close()


def test_los_paneles_flotantes_de_render_usan_la_cabecera_movible_y_el_ancho_comun(qapp):
    from PySide6.QtWidgets import QLabel, QToolButton
    from omnicad.ejemplo import crear_documento_ejemplo
    from omnicad.ui import render as ur
    from omnicad.ui.formulario import ANCHOS
    from omnicad.ui.superposiciones import CabeceraMovible
    for panel in (ur.PanelEscena(), ur.PanelAspecto(crear_documento_ejemplo())):
        cab = panel.findChild(CabeceraMovible)
        assert cab is not None and panel.width() == ANCHOS["normal"] and panel.posicion_usuario is None
        titulo = cab.findChild(QLabel, "titulo_comando")
        assert titulo.text() == titulo.text().upper() and titulo.text()
        cruz = next(b for b in cab.findChildren(QToolButton) if b.text() == "✕")
        cerrados = []
        panel.cerrado.connect(lambda c=cerrados: c.append(1))
        cruz.click()
        assert cerrados == [1] and cruz.toolTip() == "Cerrar"


def test_el_panel_de_escena_se_mueve_por_la_cabecera_dentro_de_la_ventana_de_render(qapp):
    from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
    from PySide6.QtGui import QMouseEvent
    from PySide6.QtWidgets import QApplication
    from omnicad.ejemplo import crear_documento_ejemplo
    from omnicad.ui import render as ur
    from omnicad.ui.superposiciones import CabeceraMovible
    v = ur.VentanaRender(crear_documento_ejemplo())
    v.resize(1100, 900)                                                      # el panel mide ~560 px: en una ventana más baja no entra (UI-1, queda)
    v.show()
    v.mostrar_escena()
    qapp.processEvents()
    p = v.panel_escena
    base, cab = p.pos(), p.findChild(CabeceraMovible)

    def evento(tipo, global_):
        QApplication.sendEvent(cab, QMouseEvent(tipo, QPointF(cab.mapFromGlobal(global_)), QPointF(global_), Qt.LeftButton,
                                                Qt.LeftButton, Qt.NoModifier))
    ini = cab.mapToGlobal(QPoint(30, 8))
    evento(QEvent.MouseButtonPress, ini)
    for i in (1, 2, 3):
        evento(QEvent.MouseMove, ini + QPoint(-50 * i, 40 * i))
    evento(QEvent.MouseButtonRelease, ini + QPoint(-150, 120))
    assert p.pos() != base and v.area.rect().contains(p.geometry())
    evento(QEvent.MouseButtonDblClick, cab.mapToGlobal(QPoint(30, 8)))
    assert p.pos() == base                                                  # el doble clic lo devuelve a su lugar
    v.close()

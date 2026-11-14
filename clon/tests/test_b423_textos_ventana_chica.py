"""B-423: los rótulos angostos conservan su comienzo y el nombre completo en la ayuda."""

import pytest
from PySide6.QtCore import QSettings, QSize, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QStyle, QStyleOptionToolButton, QToolButton

from omnicad.ejemplo import crear_documento_ejemplo
from omnicad.ui.cinta import PESTANAS
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


def _ancho_texto(boton):
    opcion = QStyleOptionToolButton()
    boton.initStyleOption(opcion)
    opcion.text = ""
    margen = boton.style().sizeFromContents(QStyle.CT_ToolButton, opcion, QSize(0, 0), boton).width()
    return boton.width() - margen


@pytest.mark.parametrize("ancho,alto", [(800, 520), (1280, 800)])
def test_pestanas_legibles_y_botones_con_nombre_completo(ventana, ancho, alto):
    v = ventana
    v.resize(ancho, alto)
    QTest.qWait(20)
    assert v.size() == QSize(ancho, alto)
    for boton, (nombre, _) in zip(v.cinta.pestanas, PESTANAS, strict=True):
        assert boton.toolTip() == nombre
        texto = boton.text()
        assert texto.startswith(nombre[:4]), texto
        assert texto == nombre or (texto.endswith("…") and nombre.startswith(texto[:-1]))
        assert boton.fontMetrics().horizontalAdvance(texto) <= _ancho_texto(boton), texto
        if ancho == 1280:
            assert texto == nombre
    for boton, (nombre, _) in zip(v.cinta.pestanas, PESTANAS, strict=True):
        QTest.mouseClick(boton, Qt.LeftButton)
        QApplication.processEvents()
        assert v.cinta.pestana_actual() == nombre
        for b in v.cinta.pila.currentWidget().findChildren(QToolButton, "boton_cinta"):
            completo = b.defaultAction().text().split("\t")[0].replace("…", "").strip()
            assert completo in b.toolTip(), (completo, b.toolTip())
        for b in v.cinta.pila.currentWidget().findChildren(QToolButton, "titulo_grupo"):
            if b.menu() is not None:
                assert b.toolTip() == b.text().removesuffix(" ▾")
    # Volver a agrandar restaura los nombres, sin conservar abreviaturas de la ventana chica.
    v.resize(1280, 800)
    QTest.qWait(20)
    assert [b.text() for b in v.cinta.pestanas] == [n for n, _ in PESTANAS]


@pytest.mark.parametrize("ancho,alto", [(800, 520), (1280, 800)])
def test_resumen_legible_con_tooltip_y_restauracion(ventana, ancho, alto):
    v = ventana
    v.resize(ancho, alto)
    QTest.qWait(20)
    estado = v.timeline.estado
    assert estado.toolTip() == "2 cuerpo(s) · 8 paso(s)"
    if ancho == 800:
        # En la PC la etiqueta queda angosta; acá sobra lugar: se la achica a mano para forzar el resumen.
        estado.setMaximumWidth(estado.fontMetrics().horizontalAdvance("2 cuerpos · 8 pasos") + 10)
        v._mostrar_estado(v._texto_estado)
        QTest.qWait(20)
        assert estado.text() == "2 cuerpos · 8 pasos"
        estado.setMaximumWidth(16777215)
        v._mostrar_estado(v._texto_estado)
    assert estado.text() == estado.toolTip() or ancho == 800
    assert estado.fontMetrics().horizontalAdvance(estado.text()) <= estado.contentsRect().width()
    v.resize(1280, 800)
    QTest.qWait(20)
    assert estado.text() == estado.toolTip() == "2 cuerpo(s) · 8 paso(s)"


def test_mensaje_largo_conserva_el_comienzo_y_el_tooltip(ventana):
    ventana.resize(800, 520)
    QTest.qWait(20)
    mensaje = "Calculando Extrusión de la placa con muchos agujeros; Esc cancela la operación"
    ventana.mensaje(mensaje)
    estado = ventana.timeline.estado
    assert estado.toolTip() == mensaje
    assert estado.text().endswith("…")
    assert mensaje.startswith(estado.text()[:-1])


def test_pestana_contextual_tambien_conserva_cuatro_letras(ventana):
    ventana.resize(800, 520)
    ventana.cinta.mostrar_contextual("BOCETO")
    QTest.qWait(20)
    assert ventana.size() == QSize(800, 520)
    for b in [*ventana.cinta.pestanas, ventana.cinta.contextuales["BOCETO"]]:
        assert b.text().startswith(b.toolTip()[:4]), b.text()
        assert b.fontMetrics().horizontalAdvance(b.text()) <= _ancho_texto(b)
    ventana.cinta.ocultar_contextual("BOCETO")

"""B-423: los rótulos angostos conservan su comienzo y el nombre completo en la ayuda."""

import warnings
import pytest
from PySide6.QtCore import QPoint, QSettings, QSize, Qt
from PySide6.QtGui import QIcon
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMenu, QStyle, QStyleOptionToolButton, QToolButton, QToolTip

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


def test_iconos_enteros_sin_superposicion_y_accesos_restaurados(ventana):
    v = ventana
    v.resize(800, 520)
    for pestana in [*v.cinta.pestanas, v.cinta.contextuales["BOCETO"]]:
        if pestana is v.cinta.contextuales["BOCETO"]:
            v.cinta.mostrar_contextual("BOCETO")
        QTest.mouseClick(pestana, Qt.LeftButton)
        QTest.qWait(30)
        assert v.size() == QSize(800, 520)
        pagina = v.cinta.pila.currentWidget()
        botones = pagina.findChildren(QToolButton, "boton_cinta")
        visibles = [b for b in botones if b.isVisible()]
        for b in visibles:
            assert b.parentWidget().rect().contains(b.geometry()), b.defaultAction().text()
            assert b.visibleRegion().boundingRect() == b.rect(), b.defaultAction().text()
            for otro in visibles:
                if otro is not b and otro.parentWidget() is b.parentWidget():
                    assert not b.geometry().intersects(otro.geometry()), (b.text(), otro.text())
        for b in botones:
            if not b.isVisible():
                menus = b.parentWidget().findChildren(QMenu)
                assert any(b.defaultAction() in m.actions() for m in menus), b.text()

        # Medir la silueta pintada, no solo el iconSize declarado: el layout la recortaba.
        b = visibles[0]
        modo = QIcon.Normal if b.isEnabled() else QIcon.Disabled
        original = b.icon().pixmap(b.iconSize(), modo).toImage()
        colores = {original.pixel(x, y) for x in range(original.width()) for y in range(original.height())
                   if original.pixelColor(x, y).alpha() == 255}
        pintado = b.grab().toImage()
        def caja(imagen, colores):
            puntos = [(x, y) for x in range(imagen.width()) for y in range(imagen.height())
                      if imagen.pixel(x, y) in colores]
            assert puntos
            xs, ys = zip(*puntos, strict=True)
            return max(xs) - min(xs) + 1, max(ys) - min(ys) + 1
        ancho, alto = caja(pintado, colores)
        ancho_original, alto_original = caja(original, colores)
        assert ancho / alto == pytest.approx(ancho_original / alto_original, rel=0.1), b.text()

    v.cinta.ocultar_contextual("BOCETO")
    v.resize(4000, 800)
    QTest.qWait(30)
    for pestana in v.cinta.pestanas:
        QTest.mouseClick(pestana, Qt.LeftButton)
        QTest.qWait(30)
        assert all(b.isVisible() for b in v.cinta.pila.currentWidget().findChildren(QToolButton, "boton_cinta"))


@pytest.mark.parametrize("mostrar_ayuda", [True, False])
@pytest.mark.parametrize("contextual", [False, True])
def test_tooltip_de_pestana_con_retraso_normal_aun_sin_ayuda(ventana, mostrar_ayuda, contextual):
    v = ventana
    v.resize(800, 520)
    v.prefs["general/info_herramientas"] = mostrar_ayuda
    v.aplicar_preferencias()
    if contextual:
        v.cinta.mostrar_contextual("BOCETO")
    QTest.qWait(30)
    # Xvfb no tiene gestor de ventanas; activar solo el estado interno de Qt.
    with warnings.catch_warnings():     # obsoleto, pero es la única vía sin foco real (como scripts/prueba_ui/arnes.py)
        warnings.simplefilter("ignore", DeprecationWarning)
        QApplication.setActiveWindow(v)
    b = v.cinta.contextuales["BOCETO"] if contextual else v.cinta.pestanas[1]
    retraso = b.style().styleHint(QStyle.SH_ToolTip_WakeUpDelay, None, b)
    assert 500 <= retraso <= 1000
    try:
        QToolTip.hideText()
        QTest.qWait(400)
        # La sobrecarga QWindow simula eventos; la de QWidget mueve el cursor real.
        QTest.mouseMove(v.windowHandle(), QPoint(1, 1))
        QTest.mouseMove(v.windowHandle(), b.mapTo(v, b.rect().center()))
        QTest.qWait(200)
        assert not QToolTip.isVisible()
        QTest.qWait(retraso + 300)
        assert QToolTip.isVisible(), b.toolTip()
        assert QToolTip.text() == b.toolTip()
        if not mostrar_ayuda:
            QToolTip.hideText()
            QTest.qWait(400)
            comando = next(b for b in v.cinta.pila.currentWidget().findChildren(QToolButton, "boton_cinta")
                           if b.isVisible() and b.isEnabled())
            QTest.mouseMove(v.windowHandle(), comando.mapTo(v, comando.rect().center()))
            QTest.qWait(retraso + 500)
            assert not QToolTip.isVisible(), "La ayuda de comandos debe seguir apagada"
    finally:
        QToolTip.hideText()

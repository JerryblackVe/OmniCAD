"""B-442: el radio inválido del Empalme se señala al teclear, sin cambiar el boceto."""

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from omnicad.restricciones import Boceto
from omnicad.timeline.parametros import TablaParametros
from omnicad.ui import temas
from omnicad.ui.editor_boceto import Lienzo


@pytest.fixture
def lienzo():
    app = QApplication.instance() or QApplication([])
    boceto = Boceto()
    vertice = boceto.agregar_punto(10, 10)
    boceto.agregar_linea(vertice, (40, 10))
    boceto.agregar_linea(vertice, (10, 40))
    lienzo = Lienzo(boceto, TablaParametros().evaluar)
    lienzo.resize(800, 600)
    lienzo.ajustar_grilla = False
    lienzo.show()
    app.processEvents()
    yield lienzo
    lienzo._cerrar_entrada()
    lienzo.close()
    lienzo.deleteLater()
    app.processEvents()


@pytest.mark.parametrize("seleccion", ["curvas", "vertice"])
@pytest.mark.parametrize("texto", ["0", "-2", "abc", "", "1/0"])
def test_radio_invalido_se_marca_y_se_puede_corregir(lienzo, seleccion, texto):
    lienzo.set_herramienta("empalme")
    puntos = [(25, 10), (10, 25)] if seleccion == "curvas" else [(10, 10)]
    for punto in puntos:
        QTest.mouseClick(lienzo, Qt.LeftButton, pos=lienzo.a_px(*punto).toPoint())
    entrada = lienzo.entrada
    assert entrada is not None
    campo = entrada.campos[0]
    mensajes = []
    lienzo.mensaje.connect(mensajes.append)
    antes = lienzo.b.a_dict()

    QTest.keyClick(campo, Qt.Key_A, Qt.ControlModifier)
    QTest.keyClick(campo, Qt.Key_Backspace)
    QTest.keyClicks(campo, texto)

    assert temas.color("campo_error") in campo.styleSheet()
    assert campo.toolTip() and campo.toolTip() == mensajes[-1]
    if texto in ("0", "-2"):
        assert "mayor que cero" in campo.toolTip()
    QTest.keyClick(campo, Qt.Key_Return)
    assert lienzo.entrada is entrada
    assert lienzo.b.a_dict() == antes
    assert not lienzo.historial

    QTest.keyClick(campo, Qt.Key_A, Qt.ControlModifier)
    QTest.keyClicks(campo, "3 mm")
    assert not campo.styleSheet() and not campo.toolTip()
    QTest.keyClick(campo, Qt.Key_Return)
    assert lienzo.entrada is None
    arcos = [c.id for c in lienzo.b.curvas.values() if c.tipo == "arco"]
    assert len(arcos) == 1
    assert lienzo.b.radio(arcos[0]) == pytest.approx(3)
    assert len(lienzo.historial) == 1


def test_paralelas_no_rechazan_un_radio_ignorado_por_superar_el_tope(lienzo):
    """Entre paralelas la separación impone R5: el radio pedido no se convierte en cota."""
    lienzo.b.agregar_linea((10, 20), (40, 20))
    lienzo.set_herramienta("empalme")
    for punto in [(15, 10), (15, 20)]:
        QTest.mouseClick(lienzo, Qt.LeftButton, pos=lienzo.a_px(*punto).toPoint())
    assert lienzo.entrada is not None
    campo = lienzo.entrada.campos[0]
    avisos = []
    lienzo.aviso.connect(avisos.append)

    QTest.keyClick(campo, Qt.Key_A, Qt.ControlModifier)
    QTest.keyClicks(campo, "1000001 mm")
    QTest.keyClick(campo, Qt.Key_Return)

    assert lienzo.entrada is None
    arco, = [c.id for c in lienzo.b.curvas.values() if c.tipo == "arco"]
    assert lienzo.b.radio(arco) == pytest.approx(5)
    cota, = lienzo.b.cotas.values()
    assert lienzo.evaluar(cota.expresion) == pytest.approx(5)
    assert any("se ignoró el radio pedido" in aviso for aviso in avisos)
    assert len(lienzo.historial) == 1

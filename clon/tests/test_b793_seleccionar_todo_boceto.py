"""B-793/B-794: Seleccionar todo e Invertir con el boceto abierto cubren la geometría y sus puntos, como la ventana."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402
from PySide6.QtCore import QSettings, Qt  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication, QToolButton  # noqa: E402

from omnicad.restricciones import Boceto  # noqa: E402
from omnicad.timeline.parametros import TablaParametros  # noqa: E402
from omnicad.ui import editor_boceto  # noqa: E402
from omnicad.ui.ventana import VentanaPrincipal as Ventana  # noqa: E402


def test_seleccionar_todo_e_invertir():
    QApplication.instance() or QApplication([])
    b = Boceto()
    b.agregar_linea((0, 0), (10, 0))
    b.agregar_linea((10, 0), (10, 10))
    b.agregar_circulo((30, 30), 5)
    lz = editor_boceto.Lienzo(b, TablaParametros().evaluar)
    todos = lz.ids_seleccionables()
    assert len(todos) == len(b.curvas) + len(b.puntos) - sum(1 for p in b.puntos if p <= 0)
    fake = type("V", (), {"modo_boceto": type("M", (), {"activo": True, "lienzo": lz})()})()
    Ventana._seleccionar_todo(fake)
    assert sorted(lz.seleccion) == sorted(todos)
    assert all(i in lz.seleccion for i in b.puntos if i > 0)  # los puntos de las curvas también (antes quedaban afuera)
    lz.seleccion = todos[:2]
    Ventana._invertir_seleccion(fake)
    assert len(lz.seleccion) == len(todos) - 2


@pytest.fixture
def ventana_boceto(tmp_path):
    from omnicad.timeline.documento import Documento
    from omnicad.timeline.operaciones import OpBoceto
    from omnicad.ui.preferencias import Preferencias

    app = QApplication.instance() or QApplication([])
    b = Boceto()
    b.agregar_rectangulo((-10, -10), (10, 10))
    b.agregar_circulo((2, 3), 4)
    doc = Documento()
    doc.agregar(OpBoceto("sk", "Boceto1", boceto=b, plano="XY"))
    prefs = Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat))
    v = Ventana(doc, prefs=prefs)
    v.resize(1200, 800)
    try:
        v.show()
        v.editar_operacion("sk")
        app.processEvents()
        yield v
    finally:
        if v.modo_boceto.activo:
            v.modo_boceto.cancelar()
        v.doc.modificado = False
        v.close()
        v.deleteLater()
        app.processEvents()


def _pulsar_accion(v, clave):
    """Clic simulado que recorre la conexión de la QAction real."""
    boton = QToolButton(v)
    boton.setDefaultAction(v.acciones[clave])
    boton.show()
    QTest.mouseClick(boton, Qt.LeftButton)
    QApplication.processEvents()
    boton.deleteLater()


def test_b793_accion_selecciona_las_diez_entidades(ventana_boceto):
    """Fusion: seleccionar todo incluye las curvas y sus puntos."""
    v = ventana_boceto
    lz = v.modo_boceto.lienzo
    esperado = set(lz.b.curvas) | {p for p in lz.b.puntos if p > 0}
    assert len(esperado) == 10
    mensajes = []
    lz.mensaje.connect(mensajes.append)
    _pulsar_accion(v, "seleccionar_todo")
    assert set(lz.seleccion) == esperado
    assert len(lz.seleccion) == 10
    assert not mensajes  # no reemplazar el resultado por la ayuda de Seleccionar
    assert not v.seleccion
    assert v.modo_boceto.activo


def test_b794_accion_invierte_dos_en_ocho(ventana_boceto):
    """Fusion: invertir elige el complemento en el boceto activo."""
    v = ventana_boceto
    lz = v.modo_boceto.lienzo
    todos = set(lz.b.curvas) | {p for p in lz.b.puntos if p > 0}
    circulo = next(c for c in lz.b.curvas.values() if c.tipo == "circulo")
    inicial = {circulo.id, *circulo.puntos()}
    assert len(todos) == 10 and len(inicial) == 2
    lz.seleccion = list(inicial)
    _pulsar_accion(v, "invertir_seleccion")
    assert set(lz.seleccion) == todos - inicial
    assert len(lz.seleccion) == 8
    assert not v.seleccion
    _pulsar_accion(v, "invertir_seleccion")
    assert set(lz.seleccion) == inicial
    assert v.modo_boceto.activo

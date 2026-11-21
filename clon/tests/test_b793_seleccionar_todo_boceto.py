"""B-793/B-794: Seleccionar todo e Invertir con el boceto abierto cubren la geometría y sus puntos, como la ventana."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

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

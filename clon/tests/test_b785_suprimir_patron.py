# -*- coding: utf-8 -*-
"""B-785: la casilla «Suprimir» del patrón (Fusion): desmarcada quita las casillas de las copias y entran todas;
al volver a marcarla se recuperan las copias excluidas."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from omnicad.restricciones import Boceto  # noqa: E402
from omnicad.timeline.parametros import TablaParametros  # noqa: E402
from omnicad.ui import editor_boceto  # noqa: E402
from omnicad.ui.panel_patron import PanelPatron  # noqa: E402


def test_suprimir_desmarcada_incluye_todas_y_recuerda_las_excluidas():
    app = QApplication.instance() or QApplication([])
    lz = editor_boceto.Lienzo(Boceto(), TablaParametros().evaluar)
    lz.resize(800, 600)
    c = lz.b.agregar_circulo((0, 0), 3)
    panel = PanelPatron()
    ctl = lz.patron
    ctl.panel = panel
    panel.cambio.connect(ctl.recibir)
    lz.seleccion = [c]
    lz.set_herramienta("patron_rectangular")
    panel.campos["cantidad1"].setText("4")
    panel.campos["distancia1"].setText("30")
    app.processEvents()
    assert panel.casillas["suprimir"].isChecked()          # como Fusion: viene marcada
    assert len(ctl.casillas()) == 3                        # una casilla por copia
    ctl.suprimidos = {1}
    ctl._cache = None
    n_marcada = len(ctl.calcular()["polis"])
    panel.casillas["suprimir"].setChecked(False)
    app.processEvents()
    assert ctl.casillas() == []                            # sin casillas en el dibujo
    assert len(ctl.calcular()["polis"]) > n_marcada        # entran todas las copias
    panel.casillas["suprimir"].setChecked(True)
    app.processEvents()
    assert ctl.suprimidos == {1} and len(ctl.calcular()["polis"]) == n_marcada   # la excluida se conserva
    ctl.cancelar()

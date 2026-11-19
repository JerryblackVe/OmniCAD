# -*- coding: utf-8 -*-
"""B-661: el círculo del boceto se muestrea según el zoom (antes, 64 lados fijos: de cerca se veía facetado)."""
import math
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from omnicad.nucleo import geometria as geo  # noqa: E402
from omnicad.restricciones import Boceto  # noqa: E402
from omnicad.timeline.parametros import TablaParametros  # noqa: E402
from omnicad.ui import editor_boceto  # noqa: E402
from omnicad.ui.editor_boceto_comun import pasos_segun_zoom  # noqa: E402


def _desvio_px(poli, centro, r, escala):
    """Lo más que se aparta de la curva (en px) el medio de una cuerda."""
    return max((r - math.dist(((a[0] + b[0]) / 2, (a[1] + b[1]) / 2), centro)) * escala
               for a, b in zip(poli, poli[1:], strict=False))


@pytest.mark.parametrize("escala", [0.5, 5.0, 80.0])
def test_el_circulo_se_aparta_menos_de_un_cuarto_de_pixel_con_cualquier_zoom(escala):
    QApplication.instance() or QApplication([])
    b = Boceto()
    cid = b.agregar_circulo((0.0, 0.0), 10.0)
    lz = editor_boceto.Lienzo(b, TablaParametros().evaluar, plano=geo.Plano("XY"))
    lz.escala = escala
    [poli] = lz._polilineas(b.curvas[cid])
    assert _desvio_px(poli, (0.0, 0.0), 10.0, escala) <= 0.25
    assert len(poli) >= 65                                  # nunca menos que antes
    lz.deleteLater()


def test_pasos_en_potencias_de_dos_con_tope_y_lo_demas_igual():
    assert pasos_segun_zoom(("circulo", None, (0, 0), 10.0), 1.0) == 64
    assert pasos_segun_zoom(("circulo", None, (0, 0), 1e6), 100.0) == 4096
    assert pasos_segun_zoom(("arco", None, (0, 0), 10.0, 0.0, 1.0), 80.0) in (128, 256, 512, 1024)
    assert pasos_segun_zoom(("linea", None, (0, 0), (1, 1)), 80.0) == 64

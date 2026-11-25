# -*- coding: utf-8 -*-
"""B-596: el visor avisa el cambio de cámara apenas ocurre, para que el boceto dibujado encima se repinte con él."""
import time

import pytest
from PySide6.QtWidgets import QApplication

from omnicad.ui import visor3d as vis


@pytest.fixture
def visor():
    app = QApplication.instance() or QApplication([])
    v = vis.Visor3D()
    v.resize(400, 300)
    v.show()
    for _ in range(5):                         # el primer cuadro fija la cámara de la que se avisó
        app.processEvents()
    yield v
    v.close()
    v.deleteLater()
    app.processEvents()


@pytest.mark.parametrize("limite_fps", [0, 1])
def test_acercar_avisa_antes_de_pintar_y_no_dos_veces(visor, limite_fps):
    avisos = []
    visor.camara_cambiada.connect(lambda: avisos.append(1))
    visor.config.limite_fps = limite_fps
    visor._t_cuadro = time.perf_counter()
    visor.acercar(2)
    assert len(avisos) == 1                    # al instante: antes de que el visor termine de pintar
    assert visor._t_limite.isActive() == bool(limite_fps)
    visor._avisar_camara()                     # como al pintar, también sin contexto OpenGL
    for _ in range(5):
        QApplication.processEvents()
    assert len(avisos) == 1                    # y el cuadro que pinta después no repite el aviso


def test_sin_cambio_de_camara_no_avisa(visor):
    avisos = []
    visor.camara_cambiada.connect(lambda: avisos.append(1))
    visor.update()
    for _ in range(3):
        QApplication.processEvents()
    assert avisos == []

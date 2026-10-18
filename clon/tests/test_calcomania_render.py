# -*- coding: utf-8 -*-
"""Las calcomanías también se ven en RENDERIZAR: antes solo las dibujaba el visor de Diseño y el render las perdía."""
import os
from unittest import mock

import numpy as np
import pytest
from PIL import Image

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from omnicad import api

from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="module")
def app_qt():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def vr(app_qt, tmp_path):
    from omnicad.ui.render import VentanaRender
    imagen = tmp_path / "textura.png"
    Image.new("RGBA", (64, 32), "white").save(imagen)
    s = api.Sesion()
    assert api.llamar(s, "create_box", {"length": 40, "width": 30, "height": 20})["ok"]
    v = VentanaRender(s.doc)
    yield v, s, str(imagen)
    s.doc.modificado = False
    v.close()


def test_la_calcomania_llega_al_lienzo_de_render_y_sigue_al_documento(vr):
    v, s, imagen = vr
    assert v.lienzo.config.lienzos == []
    assert api.llamar(s, "set_decal", {"image": imagen, "face": ">Z"})["ok"]
    ident = s.doc.operaciones[-1].id
    v.actualizar()                                       # el documento cambió: el lienzo se vuelve a cargar
    assert [i for i, _ in v.lienzo.config.lienzos] == [ident]
    assert v.lienzo.config.lienzos[0][1]["calcomania"]


def test_pintar_calcomanias_usa_la_camara_y_deja_el_estado_de_gl_como_estaba(vr):
    v, s, imagen = vr
    gl = mock.MagicMock()
    with mock.patch("omnicad.ui.render.GL", gl), mock.patch.object(v.lienzo, "_dibujar_lienzos") as dibujar:
        v.lienzo._pintar_calcomanias(np.identity(4), np.identity(4))
    dibujar.assert_called_once_with()
    llamadas = gl.mock_calls
    assert (llamadas.index(mock.call.glEnable(gl.GL_POLYGON_OFFSET_FILL))
            < llamadas.index(mock.call.glDisable(gl.GL_POLYGON_OFFSET_FILL)))   # lo que enciende, lo apaga
    gl.glDepthFunc.assert_called_with(gl.GL_LESS)                              # el resto del cuadro sigue con GL_LESS
    gl.glDisable.assert_any_call(gl.GL_BLEND)

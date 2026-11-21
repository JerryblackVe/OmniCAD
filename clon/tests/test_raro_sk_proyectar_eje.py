# -*- coding: utf-8 -*-
"""Valores raros del comando de boceto «sk_proyectar_eje»: el eje elegido en la paleta (X, Y, Z, arista o un
valor raro) se proyecta sobre el plano del boceto. Vacío, 0, negativo, enorme, con unidades y con expresión se
rechazan con un aviso de un solo renglón, sin cerrar la app ni dejar el boceto roto; X, Y y Z proyectan el eje."""
import os
from types import SimpleNamespace

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from omnicad.nucleo import geometria as geo
from omnicad.restricciones import Boceto, resolver
from omnicad.timeline.parametros import TablaParametros
from omnicad.ui import editor_boceto


@pytest.fixture
def lienzo():
    app = QApplication.instance() or QApplication([])
    lz = editor_boceto.Lienzo(Boceto(), TablaParametros().evaluar, plano=geo.Plano("XZ"))
    lz.resize(800, 600)
    lz.ajustar_grilla = False
    lz.show()
    lz.mensajes = []
    lz.mensaje.connect(lz.mensajes.append)
    # estado vacío para que los ejes de construcción (X/Y/Z del origen) no necesiten el documento
    lz.estado_referencias = lambda: SimpleNamespace(ejes={}, planos={}, puntos={}, cuerpos={}, bocetos={},
                                                   componentes={})
    yield lz
    lz.close()
    lz.deleteLater()
    app.processEvents()


# ---------------------------------------------------------------- EJES VÁLIDOS
@pytest.mark.parametrize("eje", ["X", "Y", "Z"])
def test_proyectar_eje_valido_crea_la_linea_del_eje(lienzo, eje):
    lz = lienzo
    lz.opciones["eje_giro"] = eje
    lz.mensajes.clear()
    antes = len(lz.b.proyecciones)
    assert lz.proyectar_eje() is True
    assert len(lz.b.proyecciones) == antes + 1
    assert lz.b.proyecciones[-1]["refs"] == [{"tipo": "eje", "id": eje}]
    for mensaje in lz.mensajes:
        assert "\n" not in mensaje and "\r" not in mensaje
    assert lz.resultado.ok
    resolver(lz.b)


# ---------------------------------------------------------------- VALORES RAROS
@pytest.mark.parametrize("eje", ["", "0", "-5", "2000000", "5 mm", "5*2"])
def test_proyectar_eje_con_eje_raro_avisa_y_no_dibuja(lienzo, eje):
    lz = lienzo
    lz.opciones["eje_giro"] = eje
    lz.mensajes.clear()
    antes = len(lz.b.curvas)
    assert lz.proyectar_eje() is False
    assert len(lz.b.curvas) == antes
    assert lz.mensajes
    for mensaje in lz.mensajes:
        assert "\n" not in mensaje and "\r" not in mensaje
    assert len(lz.mensajes[-1]) <= 120
    assert lz.resultado.ok
    resolver(lz.b)


def test_proyectar_eje_arista_sin_seleccion_avisa_y_no_dibuja(lienzo):
    lz = lienzo
    lz.opciones["eje_giro"] = "arista"
    lz.mensajes.clear()
    antes = len(lz.b.curvas)
    assert lz.proyectar_eje() is False
    assert len(lz.b.curvas) == antes
    assert lz.mensajes
    for mensaje in lz.mensajes:
        assert "\n" not in mensaje and "\r" not in mensaje
    assert lz.resultado.ok
    resolver(lz.b)


def test_proyectar_eje_sin_plano_avisa_en_un_renglon(lienzo):
    lz = lienzo
    lz.plano = None
    lz.opciones["eje_giro"] = "Z"
    lz.mensajes.clear()
    antes = len(lz.b.curvas)
    assert lz.proyectar_eje() is False
    assert len(lz.b.curvas) == antes
    assert lz.mensajes
    assert any("Falta el plano" in m for m in lz.mensajes)
    for mensaje in lz.mensajes:
        assert "\n" not in mensaje and "\r" not in mensaje
    assert lz.resultado.ok
    resolver(lz.b)

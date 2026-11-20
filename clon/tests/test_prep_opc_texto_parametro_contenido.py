# -*- coding: utf-8 -*-
"""PREP: opción «Parámetro de texto y Contenido» del panel «Carácter» del boceto.

El campo «Parámetro de texto» nombra el parámetro ligado (o «Sin parámetro ligado») y «Contenido» es el mismo
texto del cuadro del visor: editarlo lo cambia con set_parameter. Se prueba un valor numérico (el contenido
«123» se conserva como texto) y el borde del texto vacío (no crea geometría y avisa)."""
import os
from types import SimpleNamespace

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QWidget  # noqa: E402

from omnicad import api  # noqa: E402
from omnicad.api.herramientas_boceto import op_boceto  # noqa: E402
from omnicad.ui import editor_boceto, modo_boceto  # noqa: E402


@pytest.fixture
def modo_texto():
    app = QApplication.instance() or QApplication([])
    s = api.Sesion()
    assert api.llamar(s, "create_sketch", {"plane": "XY"})["ok"]
    assert api.llamar(s, "add_text", {"text": "123", "x": 10, "y": 20})["ok"]
    b = op_boceto(s, None).boceto.copia()
    tid = next(i for i, c in b.curvas.items() if c.tipo == "texto")
    ventana = QWidget()
    ventana.doc = s.doc
    ventana.area = SimpleNamespace(reubicar=lambda: None)
    ventana.mensaje = lambda *a: None
    modo = modo_boceto.ModoBoceto(ventana)
    lz = editor_boceto.Lienzo(b, lambda *a: ventana.doc.parametros.evaluar(*a))
    lz.editar_parametro_texto = modo._editar_parametro_texto
    lz.valores_parametros = lambda: ventana.doc.parametros.valores()
    modo.lienzo, modo.boceto = lz, b
    modo.paleta, modo.caracter, modo.tarjeta = modo_boceto.PaletaBoceto(), modo_boceto.PanelCaracter(), modo_boceto.TarjetaHerramienta()
    modo.caracter.cambio.connect(modo._ajuste)
    lz.texto_en_edicion.connect(modo._opciones_de_texto)
    yield s, lz, tid, modo
    for w in (lz, modo.paleta, modo.caracter, modo.tarjeta, ventana):
        w.close()
        w.deleteLater()
    app.processEvents()


def test_parametro_texto_y_contenido_valor_numerico(modo_texto):
    s, lz, tid, modo = modo_texto
    panel = modo.caracter
    lz.editar_texto(tid, lz.a_px(10, 20))
    assert panel.parametro_texto.text() == "Text"
    assert panel.valor_parametro_texto.text() == "123"
    panel.valor_parametro_texto.setText("456")
    panel.valor_parametro_texto.editingFinished.emit()
    assert s.doc.parametros.valores()["Text"] == "456"
    assert panel.valor_parametro_texto.text() == "456"
    assert lz.entrada.campos[0].text() == "456"


def test_parametro_texto_y_contenido_borde_vacio(modo_texto):
    s, lz, tid, modo = modo_texto
    panel = modo.caracter
    lz.editar_texto(tid, lz.a_px(10, 20))
    panel.valor_parametro_texto.setText("")
    panel.valor_parametro_texto.editingFinished.emit()
    # el parámetro queda vacío y el panel lo refleja (borde aceptado por set_parameter)
    assert s.doc.parametros.valores()["Text"] == ""
    assert panel.valor_parametro_texto.text() == ""

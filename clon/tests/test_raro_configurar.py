# -*- coding: utf-8 -*-
"""Valores raros del comando «configurar» (tabla de configuraciones): una celda de parámetro con cada valor
raro (vacío, cero, negativo, enorme, con unidades, con expresión, no evaluable, unidad ajena). Aceptar nunca
cierra la app ni deja el modelo roto, y todo aviso es de un solo renglón."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication, QMessageBox

from omnicad.nucleo import geometria as geo
from omnicad.timeline.documento import Documento
from omnicad.timeline.operaciones import OpPrimitiva
from omnicad.ui.administrar import DialogoConfiguraciones
from omnicad.ui.preferencias import Preferencias
from omnicad.ui.ventana import VentanaPrincipal


@pytest.fixture
def ventana(tmp_path):
    app = QApplication.instance() or QApplication([])
    doc = Documento()
    doc.parametros.agregar("lado", "10 mm")
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="lado", largo="lado", alto="lado"))
    v = VentanaPrincipal(doc, prefs=Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat)))
    v.resize(900, 600)
    v.show()
    app.processEvents()
    yield v
    v.doc.modificado = False
    v.close()
    v.deleteLater()
    app.processEvents()


def _cuerpo(v):
    cuerpos = list(v.doc.estado_final.cuerpos.values())
    assert len(cuerpos) == 1, (len(cuerpos),)
    return cuerpos[0]


CASOS = [
    pytest.param("", id="vacio"),
    pytest.param("0", id="cero",
                 marks=pytest.mark.xfail(reason="B-785: valor 0 en columna de parámetro se aplica y deja el modelo sin cuerpos",
                                         strict=True)),
    pytest.param("-5", id="negativo",
                 marks=pytest.mark.xfail(reason="B-785: valor negativo en columna de parámetro se aplica y deja el modelo sin cuerpos",
                                         strict=True)),
    pytest.param("1e9", id="enorme",
                 marks=pytest.mark.xfail(reason="B-785: valor enorme en columna de parámetro se aplica y deja el modelo sin cuerpos",
                                         strict=True)),
    pytest.param("5 mm", id="unidades"),
    pytest.param("5*2", id="expresion"),
    pytest.param("veinte", id="no_evalua"),
    pytest.param("90 deg", id="unidad_ajena"),
]


@pytest.mark.parametrize("valor", CASOS)
def test_raro_configurar(ventana, monkeypatch, valor):
    v = ventana
    app = QApplication.instance()
    avisos = []
    monkeypatch.setattr(QMessageBox, "warning", lambda padre, titulo, texto: avisos.append(texto))
    datos = {"activa": "Predeterminada",
             "columnas": [{"tipo": "parametro", "nombre": "lado"}],
             "filas": [{"nombre": "Predeterminada", "valores": [valor]}]}
    monkeypatch.setattr(DialogoConfiguraciones, "exec", lambda self: 1)
    monkeypatch.setattr(DialogoConfiguraciones, "datos", lambda self: datos)

    v.acciones["configurar"].trigger()
    app.processEvents()

    assert app is not None
    assert v.isVisible()
    for m in avisos:
        assert "\n" not in m and "\r" not in m, m
    cuerpos = list(v.doc.estado_final.cuerpos.values())
    assert len(cuerpos) == 1, (valor, len(cuerpos))
    assert geo.es_valida(cuerpos[0].forma), valor

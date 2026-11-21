# -*- coding: utf-8 -*-
"""Valores raros del comando «mostrar_configuracion» (tabla de configuración): la celda de valor de un
parámetro con cada valor raro (vacío, cero, negativo, enorme, con unidades, con expresión). Los inválidos se
rechazan con un mensaje de un solo renglón y no tocan el documento; los válidos aplican la fila."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication, QMessageBox

@pytest.fixture
def ventana(tmp_path):
    from omnicad.timeline.documento import Documento
    from omnicad.timeline.operaciones import OpPrimitiva
    from omnicad.ui.preferencias import Preferencias
    from omnicad.ui.ventana import VentanaPrincipal

    app = QApplication.instance() or QApplication([])
    doc = Documento()
    doc.parametros.agregar("lado", "10 mm")
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="lado", largo="lado", alto="lado"))
    v = VentanaPrincipal(doc, prefs=Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat)))
    v.resize(1200, 800)
    v.show()
    app.processEvents()
    yield v
    v.doc.modificado = False
    v.close()
    v.deleteLater()
    app.processEvents()


CASOS = [
    pytest.param("", True, id="valor_vacio"),
    pytest.param("0", True, id="valor_cero"),
    pytest.param("-5", True, id="valor_negativo"),
    pytest.param("1e9", True, id="valor_enorme"),
    pytest.param("5 mm", True, id="valor_unidades"),
    pytest.param("10 mm*2", True, id="valor_expresion"),
    pytest.param("veinte", False, id="valor_invalido"),
]


def _cuerpo_unico(v):
    cuerpos = list(v.doc.estado_final.cuerpos.values())
    assert len(cuerpos) == 1
    return cuerpos[0]


@pytest.mark.parametrize(("valor", "valido"), CASOS)
def test_raro_mostrar_configuracion_valor(ventana, valor, valido, monkeypatch):
    from omnicad.ui.administrar import DialogoConfiguraciones

    v = ventana
    avisos = []
    monkeypatch.setattr(QMessageBox, "warning", lambda padre, titulo, texto: avisos.append(texto))
    datos = {"activa": "R", "columnas": [{"tipo": "parametro", "nombre": "lado"}],
             "filas": [{"nombre": "R", "valores": [valor]}]}
    monkeypatch.setattr(DialogoConfiguraciones, "exec", lambda _: 1)
    monkeypatch.setattr(DialogoConfiguraciones, "datos", lambda _: datos)

    antes = v.doc.parametros.obtener("lado").expresion
    v.acciones["mostrar_configuracion"].trigger()

    if not valido:
        assert avisos, (valor, avisos)
        for m in avisos:
            assert "\n" not in m and "\r" not in m
        assert v.doc.parametros.obtener("lado").expresion == antes
        assert not v.doc.configuraciones
    else:
        assert not avisos, (valor, avisos)
        if valor.strip():
            assert v.doc.parametros.obtener("lado").expresion == valor
        else:
            assert v.doc.parametros.obtener("lado").expresion == antes
        assert v.doc.configuraciones.get("activa") == "R"
        assert v.doc.estado_final is not None

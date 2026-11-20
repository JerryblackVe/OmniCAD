# -*- coding: utf-8 -*-
"""PREP-TEST-mostrar-configuracion: cobertura del comando «Mostrar tabla de configuración».

BOCETO › CONFIGURAR de la cinta (`mostrar_configuracion`), el único comando de ese grupo sin test automático
(docs/plan_boceto_perfecto.md). Equivale a «Display Configuration Table» de Fusion (docs/fusion_docs ›
fusion-configurations/configuration-table): activar una fila de la tabla aplica sus valores al diseño.

Un caso con valor numérico (la fila activa cambia el parámetro «lado» y con él el volumen de la caja, un solo
deshacer) y un caso borde (la fila activa lleva una expresión que no evalúa: como en Fusion no entra a la tabla,
se avisa y el documento queda como estaba).
"""
import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication, QMessageBox

from omnicad.nucleo import geometria as geo


@pytest.fixture
def ventana(tmp_path):
    """Ventana con una caja regida por el parámetro «lado» (10 mm → 1000 mm³)."""
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


def _cuerpo_unico(v):
    cuerpos = list(v.doc.estado_final.cuerpos.values())
    assert len(cuerpos) == 1
    return cuerpos[0]


def test_mostrar_configuracion_aplica_la_fila_activa_con_valor_numerico(ventana, monkeypatch):
    """Fusion › Activate a Configuration: activar «Grande» aplica su valor (lado 20 mm → 8000 mm³)."""
    from omnicad.ui.administrar import DialogoConfiguraciones
    v = ventana
    datos = {"activa": "Grande", "columnas": [{"tipo": "parametro", "nombre": "lado"}],
             "filas": [{"nombre": "Chica", "valores": ["10 mm"]},
                       {"nombre": "Grande", "valores": ["20 mm"]}]}
    monkeypatch.setattr(DialogoConfiguraciones, "exec", lambda _: 1)
    monkeypatch.setattr(DialogoConfiguraciones, "datos", lambda _: datos)
    v.acciones["mostrar_configuracion"].trigger()
    assert v.doc.configuraciones["activa"] == "Grande"
    assert v.doc.parametros.obtener("lado").expresion == "20 mm"
    forma = _cuerpo_unico(v).forma
    assert geo.es_valida(forma) and geo.volumen(forma) == pytest.approx(8000)
    v.doc.deshacer()                                   # un solo deshacer (un solo recálculo, como dice aplicar)
    assert v.doc.parametros.obtener("lado").expresion == "10 mm"
    assert geo.volumen(_cuerpo_unico(v).forma) == pytest.approx(1000)


def test_mostrar_configuracion_con_expresion_que_no_evalua_no_toca_el_documento(ventana, monkeypatch):
    """Caso borde: «veinte» no evalúa (Fusion no deja meterlo en la tabla); avisa y el diseño queda igual."""
    from omnicad.ui.administrar import DialogoConfiguraciones
    v = ventana
    avisos = []
    monkeypatch.setattr(QMessageBox, "warning", lambda padre, titulo, texto: avisos.append(texto))
    datos = {"activa": "Rota", "columnas": [{"tipo": "parametro", "nombre": "lado"}],
             "filas": [{"nombre": "Rota", "valores": ["veinte"]}]}
    monkeypatch.setattr(DialogoConfiguraciones, "exec", lambda _: 1)
    monkeypatch.setattr(DialogoConfiguraciones, "datos", lambda _: datos)
    v.acciones["mostrar_configuracion"].trigger()
    assert avisos and "veinte" in avisos[0]
    assert v.doc.parametros.obtener("lado").expresion == "10 mm"
    assert geo.volumen(_cuerpo_unico(v).forma) == pytest.approx(1000)
    assert not v.doc.configuraciones                     # la tabla con el valor roto no se guarda

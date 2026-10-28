# -*- coding: utf-8 -*-
"""B-48: teclear y aceptar una edición conserva el panel si el ensayo la rechaza."""
import sys

import pytest
from PySide6.QtCore import QSettings, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMessageBox

from omnicad.nucleo import aislado, motor
from omnicad.nucleo import geometria as geo
from omnicad.timeline.documento import Documento
from omnicad.timeline.operaciones import OpPrimitiva
from omnicad.ui.comandos.primitivas import Caja
from omnicad.ui.preferencias import Preferencias
from omnicad.ui.ventana import VentanaPrincipal


@pytest.fixture
def ventana(tmp_path):
    app = QApplication.instance() or QApplication([])
    with motor.fijar_motor("opencascade"):
        v = VentanaPrincipal(prefs=Preferencias(QSettings(str(tmp_path / "prefs.ini"), QSettings.IniFormat)))
        doc = Documento()
        for i in range(2):
            doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="2", largo="5", alto="3", x=str(10 * i)))
        v.set_documento(doc)
        v.show()
        app.processEvents()
        yield v
        if v.panel is not None:
            v.panel.cancelar()
        v.doc.modificado = False
        v.close()
        v.deleteLater()
        app.processEvents()


def _escribir(panel, valor):
    campo = panel.widgets["ancho"]
    QTest.mouseClick(campo, Qt.LeftButton)
    QTest.keyClick(campo, Qt.Key_A, Qt.ControlModifier)
    QTest.keyClicks(campo, valor)
    QTest.qWait(280)


def _rechazar(*args):
    raise aislado.TareaAislada("error nativo simulado")


def _aprobar(monkeypatch):
    def ensayar(tarea, datos, tope, esperar=None):
        with monkeypatch.context() as m:
            m.setattr(aislado, "EN_HIJO", True)
            return aislado._TAREAS_JSON[tarea](**datos)
    return ensayar


def test_previa_rechazada_muestra_error_y_permite_corregir(ventana, monkeypatch):
    v = ventana
    monkeypatch.setattr(aislado, "UMBRAL_PREVUELO_PARAMETROS", 2)
    monkeypatch.setattr(aislado, "correr_json", _rechazar)
    antes = v.doc.a_dict()
    panel = v.ejecutar_comando(Caja(), v.doc.operacion("op2"))
    _escribir(panel, "4 mm")
    assert not panel._previa_ok
    assert "error nativo simulado" in panel.mensaje.text()
    assert v.panel is panel and panel.isVisible()
    assert panel.widgets["ancho"].text() == "4 mm"
    assert v.doc.a_dict() == antes
    monkeypatch.setattr(aislado, "correr_json", _aprobar(monkeypatch))
    _escribir(panel, "6 mm")
    assert panel._previa_ok
    QTest.mouseClick(panel.boton_ok, Qt.LeftButton)
    assert v.panel is None
    assert geo.volumen(v.doc.estado_final.cuerpos["op2.c1"].forma) == pytest.approx(90)


def test_aceptar_sin_previa_conserva_panel_valores_y_deshacer_si_el_ensayo_falla(ventana, monkeypatch):
    v = ventana
    avisos, excepciones = [], []
    monkeypatch.setattr(QMessageBox, "warning", lambda padre, titulo, texto: avisos.append(texto))
    monkeypatch.setattr(sys, "excepthook", lambda *args: excepciones.append(args))
    monkeypatch.setattr(aislado, "UMBRAL_PREVUELO_PARAMETROS", 2)
    monkeypatch.setattr(aislado, "correr_json", _rechazar)
    comando = Caja()
    comando.PREVIA = False
    panel = v.ejecutar_comando(comando, v.doc.operacion("op2"))
    _escribir(panel, "6 mm")
    antes, deshacer = v.doc.a_dict(), list(v.doc._deshacer)
    QTest.mouseClick(panel.boton_ok, Qt.LeftButton)
    assert excepciones == []
    assert avisos and "error nativo simulado" in avisos[-1]
    assert v.panel is panel and panel.isVisible()
    assert panel.widgets["ancho"].text() == "6 mm"
    assert v.doc.a_dict() == antes and v.doc._deshacer == deshacer
    monkeypatch.setattr(aislado, "correr_json", _aprobar(monkeypatch))
    QTest.mouseClick(panel.boton_ok, Qt.LeftButton)
    assert v.panel is None and excepciones == []
    assert len(v.doc._deshacer) == len(deshacer) + 1
    assert geo.volumen(v.doc.estado_final.cuerpos["op2.c1"].forma) == pytest.approx(90)
    assert geo.es_valida(v.doc.estado_final.cuerpos["op2.c1"].forma)


def test_accionar_uniones_tambien_informa_el_rechazo_sin_excepcion_del_slot(ventana, monkeypatch):
    from test_gizmo_accionar import _doc_union
    from omnicad.ui.comandos.ensamblar import AccionarUniones

    v = ventana
    doc, _ = _doc_union()
    v.set_documento(doc)
    excepciones = []
    monkeypatch.setattr(sys, "excepthook", lambda *args: excepciones.append(args))
    monkeypatch.setattr(aislado, "UMBRAL_PREVUELO_PARAMETROS", 2)
    monkeypatch.setattr(aislado, "correr_json", _rechazar)
    panel = v.ejecutar_comando(AccionarUniones())
    campo = panel.widgets["giro"]
    QTest.mouseClick(campo, Qt.LeftButton)
    QTest.keyClick(campo, Qt.Key_A, Qt.ControlModifier)
    QTest.keyClicks(campo, "15 deg")
    QTest.qWait(280)
    antes, deshacer = doc.a_dict(), list(doc._deshacer)
    QTest.mouseClick(panel.boton_ok, Qt.LeftButton)
    assert excepciones == []
    assert v.panel is panel and panel.isVisible()
    assert "error nativo simulado" in panel.mensaje.text()
    assert campo.text() == "15 deg"
    assert doc.a_dict() == antes and doc._deshacer == deshacer


def test_ventana_avisa_calculando_pasado_un_segundo_y_sigue_atendiendo(ventana, monkeypatch):
    from PySide6.QtCore import QTimer

    from omnicad.timeline.documento import ErrorDocumento

    v = ventana
    monkeypatch.setattr(aislado, "UMBRAL_PREVUELO_PARAMETROS", 2)
    monkeypatch.setattr(aislado, "_comando", lambda tarea, carpeta: [sys.executable, "-c", "import time; time.sleep(1.4)"])
    mensajes, latidos = [], []
    original = v.mensaje
    monkeypatch.setattr(v, "mensaje", lambda texto, ms=5000: (mensajes.append(texto), original(texto, ms)))
    reloj = QTimer()
    reloj.timeout.connect(lambda: latidos.append(1))
    reloj.start(100)
    antes = v.doc.a_dict()
    with pytest.raises(ErrorDocumento, match="cálculo aislado"):     # el hijo de la prueba no entrega ningún resultado
        v.doc.suprimir("op2")
    reloj.stop()
    assert any(m.startswith("Calculando en un proceso aparte") for m in mensajes)
    assert len(latidos) >= 8                       # la ventana siguió atendiendo mientras esperaba
    assert v.doc.a_dict() == antes


def test_un_timer_no_lanza_un_segundo_calculo_mientras_se_espera_al_hijo(ventana, monkeypatch):
    from PySide6.QtCore import QTimer

    from omnicad.timeline.documento import ErrorDocumento

    v = ventana
    monkeypatch.setattr(aislado, "UMBRAL_PREVUELO_PARAMETROS", 2)
    monkeypatch.setattr(aislado, "_comando", lambda tarea, carpeta: [sys.executable, "-c", "import time; time.sleep(1.2)"])
    anidados = []

    def anidado():
        try:
            v.doc.suprimir("op1")
        except ErrorDocumento as e:
            anidados.append(str(e))

    QTimer.singleShot(300, anidado)
    with pytest.raises(ErrorDocumento, match="cálculo aislado"):
        v.doc.suprimir("op2")
    assert len(anidados) == 1 and "Ya hay un cálculo" in anidados[0]
    assert not v.doc.operacion("op1").suprimida and not v.doc.operacion("op2").suprimida


def test_calculando_repinta_una_vez_por_aviso_y_no_en_cada_vista_previa_seguida(ventana, monkeypatch):
    """P-37: el aviso se pinta ya (un paso largo bloquea la ventana), pero no otra vez si el texto es el mismo."""
    from types import SimpleNamespace

    v, pintadas = ventana, []
    etiqueta = v.timeline.estado
    original = etiqueta.repaint
    monkeypatch.setattr(etiqueta, "repaint", lambda: (pintadas.append(1), original()))
    v._calculando(SimpleNamespace(nombre="A"))
    v._calculando(SimpleNamespace(nombre="A"))
    assert len(pintadas) == 1
    v._calculando(SimpleNamespace(nombre="B"))
    assert len(pintadas) == 2

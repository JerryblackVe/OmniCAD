# -*- coding: utf-8 -*-
"""B-468: la caja de valor junto al asa se comporta como la de Fusion en TODAS las asas (código común del gestor):
aparece sola y enfocada, teclear entra directo, Enter aplica y acepta, un Esc cancela, un valor fuera de rango apaga
Aceptar y la previa sigue como estaba, y el menú radial ofrece «Repetir». Eventos simulados, nunca el cursor real."""
import os

import pytest
from PySide6.QtCore import QCoreApplication, Qt
from PySide6.QtTest import QTest

from omnicad.restricciones import Boceto
from omnicad.timeline.documento import Documento
from omnicad.timeline.operaciones import OpBoceto, OpExtrusion, OpPrimitiva


@pytest.fixture(scope="module")
def app_qt():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _panel(comando, doc, valores):
    from omnicad.ui.comando import ContextoComando, PanelComando
    from omnicad.ui.visor3d import Visor3D
    visor = Visor3D()
    visor.resize(800, 600)
    visor.set_modelo(doc.estado_final)
    visor.vista("iso")
    visor.encuadrar()
    panel = PanelComando(comando, ContextoComando(doc, None), visor, valores)
    panel.show()
    visor.show()
    for _ in range(3):
        QCoreApplication.processEvents()
    panel.manipuladores.sincronizar_cajas()
    QCoreApplication.processEvents()
    return panel, visor


def _caso(nombre):
    from omnicad.ui.comando import hit_desde_ref
    doc = Documento()
    if nombre in ("extruir", "revolucion"):
        b = Boceto()
        b.agregar_rectangulo((5, 0), (10, 10))
        doc.agregar(OpBoceto(doc.nuevo_id(), "Boceto1", plano="XZ", boceto=b))
        perfil = doc.estado_final.bocetos["op1"].perfiles[0]
        hit = hit_desde_ref({"tipo": "perfil", "boceto": "op1", **OpExtrusion.referencia_perfil(perfil)}, doc.estado_final)
        if nombre == "extruir":
            from omnicad.ui.comandos.solido import Extruir
            return doc, Extruir(), {"perfiles": [hit]}, "distancia"
        from omnicad.ui.comandos.solido import Revolucion
        eje = hit_desde_ref({"tipo": "eje", "id": "Z"}, doc.estado_final)
        return doc, Revolucion(), {"perfiles": [hit], "eje": [eje], "angulo": "90 deg"}, "angulo"
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="20", largo="20", alto="20"))
    if nombre == "empalme":
        from omnicad.ui.comandos.modificar import Empalme
        from omnicad.ui.comando import hit_desde_ref as h
        arista = _arista_de_arriba(doc, h)
        return doc, Empalme(), {"aristas": [arista], "radio": "2 mm"}, "radio"
    from omnicad.ui.comandos.construir import CATALOGO_LOCAL
    plano = hit_desde_ref({"tipo": "plano", "id": "XY"}, doc.estado_final)
    return doc, CATALOGO_LOCAL["plano_desfase"](), {"r0": [plano]}, "distancia"


def _arista_de_arriba(doc, hit_desde_ref):
    import numpy as np
    from omnicad.nucleo import geometria as g
    from omnicad.nucleo import referencias as refs
    forma = doc.estado_final.cuerpos["op1.c1"].forma
    arista = next(e for e in refs.subformas(forma, "arista") if np.allclose(refs.firma_arista(e)["medio"], (10, 0, 20)))
    return hit_desde_ref(refs.referencia("op1.c1", arista, caja=g.caja_envolvente(forma)), doc.estado_final)


CASOS = ["extruir", "revolucion", "empalme", "desfase"]


@pytest.mark.parametrize("nombre", CASOS)
def test_la_caja_sale_enfocada_y_teclear_entra_directo(app_qt, nombre):
    doc, comando, valores, clave = _caso(nombre)
    panel, visor = _panel(comando, doc, valores)
    gestor = panel.manipuladores
    caja = gestor.cajas[clave]
    QCoreApplication.processEvents()
    assert caja.hasFocus() or caja is gestor.cajas[clave] and gestor.cajas[clave].hasFocus(), "la caja debe quedar enfocada"
    QTest.keyClicks(caja, "7")                               # sin clic: el número entra directo
    assert caja.text().startswith("7")
    panel.cancelar()


@pytest.mark.parametrize("nombre", CASOS)
def test_enter_aplica_y_acepta_y_un_esc_cancela(app_qt, nombre):
    doc, comando, valores, clave = _caso(nombre)
    panel, visor = _panel(comando, doc, valores)
    cerrados = []
    panel.aceptado.connect(lambda *a: cerrados.append("aceptado"))
    caja = panel.manipuladores.cajas[clave]
    caja.setFocus()
    caja.selectAll()
    QTest.keyClicks(caja, "12")
    QTest.keyClick(caja, Qt.Key_Return)
    assert panel.valores[clave].split()[0] == "12", panel.valores[clave]
    assert panel._cerrado if hasattr(panel, "_cerrado") else not panel.isVisible()
    # un solo Esc cancela
    doc, comando, valores, clave = _caso(nombre)
    panel, visor = _panel(comando, doc, valores)
    caja = panel.manipuladores.cajas[clave]
    caja.setFocus()
    QTest.keyClick(caja, Qt.Key_Escape)
    assert panel.manipuladores._cerrado


def test_fuera_de_rango_apaga_aceptar_y_enter_no_acepta(app_qt):
    doc, comando, valores, clave = _caso("revolucion")
    panel, visor = _panel(comando, doc, valores)
    caja = panel.manipuladores.cajas["angulo"]
    caja.setFocus()
    caja.selectAll()
    QTest.keyClicks(caja, "400")
    QTest.keyClick(caja, Qt.Key_Return)
    assert not panel.boton_ok.isEnabled() and "angulo" in panel.invalidos, (panel.valores["angulo"], panel.widgets["angulo"].text(), panel.invalidos, panel.manipuladores._cerrado)
    assert not panel.manipuladores._cerrado                 # Enter no aceptó
    caja.selectAll()
    QTest.keyClicks(caja, "45")
    QTest.keyClick(caja, Qt.Key_Return)
    assert panel.manipuladores._cerrado                     # con un valor bueno sí


def test_teclear_con_el_foco_en_la_vista_entra_en_la_caja(app_qt):
    doc, comando, valores, clave = _caso("extruir")
    panel, visor = _panel(comando, doc, valores)
    visor.setFocus()
    QCoreApplication.processEvents()
    from PySide6.QtCore import QEvent
    from PySide6.QtGui import QKeyEvent
    QCoreApplication.sendEvent(visor, QKeyEvent(QEvent.KeyPress, Qt.Key_5, Qt.NoModifier, "5"))
    assert panel.manipuladores.cajas[clave].hasFocus()
    assert panel.manipuladores.cajas[clave].text().endswith("5")
    panel.cancelar()


def test_el_menu_radial_ofrece_repetir_el_comando_abierto(app_qt, tmp_path):
    """Con un panel abierto, «Repetir <comando>» acepta este y abre otro igual; con un valor inválido queda apagado."""
    from PySide6.QtCore import QSettings
    from omnicad.ui.comandos.primitivas import Caja
    from omnicad.ui.preferencias import Preferencias
    from omnicad.ui.ventana import VentanaPrincipal
    v = VentanaPrincipal(prefs=Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat)))
    try:
        v.show()
        v.ejecutar_comando(Caja())
        panel = v.panel
        assert panel is not None
        repetir = v._items_radial()[0]
        assert repetir.texto == f"Repetir {Caja.TITULO}" and repetir.activo == panel.boton_ok.isEnabled()
        pasos = len(v.doc.operaciones)
        repetir.funcion()
        QCoreApplication.processEvents()
        assert len(v.doc.operaciones) == pasos + 1                      # aceptó el primero
        assert v.panel is not None and v.panel is not panel and type(v.panel.comando) is Caja   # y abrió otro igual
    finally:
        v.doc.modificado = False        # que cerrar no abra «¿Guardar los cambios?» (diálogo modal)
        v.close()
        v.deleteLater()

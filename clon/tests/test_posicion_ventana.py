# -*- coding: utf-8 -*-
"""ASM-15 en la ventana: agarrar un componente en el visor con eventos simulados, soltar, Esc, otro botón, la barra
«Posición», Ctrl+Z, la pregunta antes de un comando y lo que queda en pausa mientras hay algo sin capturar."""
import os

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, QPointF, QSettings, Qt  # noqa: E402
from PySide6.QtGui import QMouseEvent  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: E402

from omnicad import api  # noqa: E402
from omnicad.timeline.posicion import pendiente_de  # noqa: E402
from omnicad.ui.comandos.ensamblar import CapturarPosicion, OrigenUnion, RevertirPosicion  # noqa: E402
from omnicad.ui.preferencias import Preferencias  # noqa: E402
from omnicad.ui.ventana import VentanaPrincipal  # noqa: E402

PUNTO = np.array([0.0, 0.0, 10.0])          # el centro de la cara de arriba del componente


@pytest.fixture
def ventana(tmp_path):
    app = QApplication.instance() or QApplication([])
    s = api.Sesion()
    cuerpos = [api.llamar(s, "create_box", {"length": 20, "width": 20, "height": 10, **extra})["result"]["bodies_created"][0]["id"]
               for extra in ({}, {"x": 80})]
    for cid, nombre in zip(cuerpos, ("Pieza", "Otra"), strict=True):
        assert api.llamar(s, "create_component", {"bodies": [cid], "name": nombre})["ok"]
    v = VentanaPrincipal(s.doc, prefs=Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat)))
    v.resize(1000, 700)
    v.show()
    app.processEvents()
    v.visor.encuadrar()
    v.cuerpo = cuerpos[0]
    yield v
    if v.panel is not None:
        v.panel.cancelar()
    v.doc.modificado = False
    v.close()
    v.deleteLater()
    app.processEvents()


def _evento(v, tipo, q, boton, botones):
    QApplication.sendEvent(v.visor, QMouseEvent(tipo, q, v.visor.mapToGlobal(q), boton, botones, Qt.NoModifier))


def _presionar_y_llevar(v, delta=QPointF(90, 30)):
    a = v.visor.proyectar(PUNTO)
    _evento(v, QEvent.MouseButtonPress, a, Qt.LeftButton, Qt.LeftButton)
    for i in range(1, 6):
        _evento(v, QEvent.MouseMove, a + delta * (i / 5), Qt.NoButton, Qt.LeftButton)
    return a + delta


def _arrastrar(v, delta=QPointF(90, 30)):
    b = _presionar_y_llevar(v, delta)
    _evento(v, QEvent.MouseButtonRelease, b, Qt.LeftButton, Qt.NoButton)
    return b


def _contestar(monkeypatch, texto):
    def clic(caja):
        next(b for b in caja.buttons() if b.text() == texto).click()
    monkeypatch.setattr(QMessageBox, "exec", clic)


def test_arrastrar_lleva_el_punto_agarrado_bajo_el_cursor_sin_tocar_el_timeline(ventana):
    v, pasos = ventana, len(ventana.doc.operaciones)
    b = _arrastrar(v)
    t = v.visor.transformaciones[v.cuerpo]
    q = v.visor.proyectar((t @ np.r_[PUNTO, 1.0])[:3])
    assert abs(q.x() - b.x()) + abs(q.y() - b.y()) < 1.5
    assert len(v.doc.operaciones) == pasos and pendiente_de(v.doc) is not None
    assert not v.arrastre.barra.isHidden()


def test_un_clic_elige_y_no_mueve(ventana):
    v = ventana
    QTest.mouseClick(v.visor, Qt.LeftButton, Qt.NoModifier, v.visor.proyectar(PUNTO).toPoint())
    assert v.seleccion and pendiente_de(v.doc) is None


def test_esc_y_otro_boton_cancelan_el_arrastre(ventana):
    v = ventana
    b = _presionar_y_llevar(v)
    QTest.keyClick(v.visor, Qt.Key_Escape)
    assert pendiente_de(v.doc) is None and not v.visor.transformaciones and not v.visor._arrastrando
    _evento(v, QEvent.MouseButtonRelease, b, Qt.LeftButton, Qt.NoButton)
    assert pendiente_de(v.doc) is None
    b = _presionar_y_llevar(v)
    _evento(v, QEvent.MouseButtonPress, b, Qt.RightButton, Qt.LeftButton | Qt.RightButton)
    assert pendiente_de(v.doc) is None and not v.visor._arrastrando
    _evento(v, QEvent.MouseButtonRelease, b, Qt.RightButton, Qt.LeftButton)
    _evento(v, QEvent.MouseButtonRelease, b, Qt.LeftButton, Qt.NoButton)
    assert pendiente_de(v.doc) is None and v.arrastre.barra.isHidden()


def test_la_barra_captura_y_revierte(ventana):
    v, pasos = ventana, len(ventana.doc.operaciones)
    _arrastrar(v)
    QTest.mouseClick(v.arrastre.barra.revertir, Qt.LeftButton)
    assert pendiente_de(v.doc) is None and not v.visor.transformaciones and len(v.doc.operaciones) == pasos
    _arrastrar(v)
    QTest.mouseClick(v.arrastre.barra.capturar, Qt.LeftButton)
    assert pendiente_de(v.doc) is None and not v.visor.transformaciones
    assert [o.TIPO for o in v.doc.operaciones[pasos:]] == ["posicion_inicial", "capturar_posicion"]
    assert v.arrastre.barra.isHidden()
    assert not v.timeline.estado.toolTip().startswith("Calculando")
    v._deshacer()
    assert len(v.doc.operaciones) == pasos                       # capturar se deshace de una vez


def test_deshacer_saca_un_arrastre_antes_que_un_paso_del_documento(ventana):
    v, pasos = ventana, len(ventana.doc.operaciones)
    _arrastrar(v)
    assert v.acciones["deshacer"].isEnabled()
    v._deshacer()
    assert pendiente_de(v.doc) is None and len(v.doc.operaciones) == pasos and not v.visor.transformaciones


def test_capturar_y_revertir_de_la_cinta_actuan_sobre_lo_arrastrado_sin_abrir_panel(ventana):
    v, pasos = ventana, len(ventana.doc.operaciones)
    _arrastrar(v)
    v.ejecutar_comando(RevertirPosicion())
    assert pendiente_de(v.doc) is None and v.panel is None and len(v.doc.operaciones) == pasos
    _arrastrar(v)
    v.ejecutar_comando(CapturarPosicion())
    assert v.panel is None and len(v.doc.operaciones) == pasos + 2


@pytest.mark.parametrize("boton, abre, sigue_pendiente, pasos_nuevos", [("Cancelar", False, True, 0), ("Continuar", True, False, 0),
                                                                        ("Capturar posición", True, False, 2)])
def test_otro_comando_pregunta_como_fusion(ventana, monkeypatch, boton, abre, sigue_pendiente, pasos_nuevos):
    v, pasos = ventana, len(ventana.doc.operaciones)
    _arrastrar(v)
    _contestar(monkeypatch, boton)
    v.ejecutar_comando(OrigenUnion())
    assert (v.panel is not None) is abre
    assert (pendiente_de(v.doc) is not None) is sigue_pendiente
    assert len(v.doc.operaciones) == pasos + pasos_nuevos


def test_sin_nada_arrastrado_no_pregunta(ventana, monkeypatch):
    monkeypatch.setattr(QMessageBox, "exec", lambda _caja: pytest.fail("no tenía que preguntar"))
    ventana.ejecutar_comando(OrigenUnion())
    assert ventana.panel is not None


def test_sin_capturar_ni_el_resaltado_ni_el_clic_eligen_la_posicion_vieja(ventana):
    v = ventana
    a = v.visor.proyectar(PUNTO)
    _arrastrar(v)
    _evento(v, QEvent.MouseMove, a, Qt.NoButton, Qt.NoButton)
    QTest.mouseClick(v.visor, Qt.LeftButton, Qt.NoModifier, a.toPoint())
    assert v.visor._hover_ent is None and not v.seleccion


def test_se_vuelve_a_agarrar_donde_quedo_dibujado(ventana):
    v = ventana
    b = _arrastrar(v)
    assert v.visor.cuerpo_bajo_cursor(b)[0] == v.cuerpo
    assert v.visor.cuerpo_bajo_cursor(v.visor.proyectar(PUNTO)) is None         # en el lugar viejo ya no hay nada


def test_ctrl_z_con_el_boton_apretado_corta_el_arrastre_sin_romperse(ventana):
    v, pasos = ventana, len(ventana.doc.operaciones)
    b = _presionar_y_llevar(v)
    v._deshacer()
    assert pendiente_de(v.doc) is None and not v.visor._arrastrando and len(v.doc.operaciones) == pasos
    _evento(v, QEvent.MouseMove, b + QPointF(20, 0), Qt.NoButton, Qt.LeftButton)
    _evento(v, QEvent.MouseButtonRelease, b, Qt.LeftButton, Qt.NoButton)
    assert pendiente_de(v.doc) is None


def test_un_atajo_de_comando_con_el_boton_apretado_corta_el_arrastre(ventana, monkeypatch):
    monkeypatch.setattr(QMessageBox, "exec", lambda _caja: pytest.fail("no había nada que capturar"))
    v = ventana
    _presionar_y_llevar(v)
    v.ejecutar_comando(OrigenUnion())
    assert v.panel is not None and pendiente_de(v.doc) is None and not v.visor._arrastrando


def test_si_el_boton_se_solto_fuera_de_la_ventana_el_arrastre_termina(ventana):
    v = ventana
    b = _presionar_y_llevar(v)
    _evento(v, QEvent.MouseMove, b + QPointF(200, 0), Qt.NoButton, Qt.NoButton)
    assert not v.visor._arrastrando and pendiente_de(v.doc) is not None
    assert v.visor.transformaciones[v.cuerpo][:3, 3] == pytest.approx(pendiente_de(v.doc).poses()[v.cuerpo][:3, 3])


def test_con_el_estudio_de_movimiento_abierto_no_se_arrastra(ventana):
    v = ventana
    a, b = (api.Sesion(v.doc), v.cuerpo)
    assert api.llamar(a, "create_as_built_joint", {"origin": ">Z", "body": b, "joint_type": "revolute"})["ok"]
    v._estudio_movimiento()
    assert not v.arrastre.empezar(v.visor.proyectar(PUNTO))
    v._panel_estudio.close()


def test_crear_boceto_con_algo_sin_capturar_pregunta(ventana, monkeypatch):
    v = ventana
    _arrastrar(v)
    _contestar(monkeypatch, "Cancelar")
    v.crear_boceto()
    assert v.visor.modo != "elegir_plano" and pendiente_de(v.doc) is not None
    _contestar(monkeypatch, "Continuar")
    v.crear_boceto()
    assert v.visor.modo == "elegir_plano" and pendiente_de(v.doc) is None
    v._cancelar_eleccion()


def test_editar_un_paso_capturar_con_algo_sin_capturar_pregunta_y_no_captura_de_mas(ventana, monkeypatch):
    v = ventana
    assert api.llamar(api.Sesion(v.doc), "capture_position", {})["ok"]
    paso = v.doc.operaciones[-1]
    _arrastrar(v)
    _contestar(monkeypatch, "Cancelar")
    v.ejecutar_comando(CapturarPosicion(), op=paso)
    assert pendiente_de(v.doc) is not None and v.panel is None


def test_editar_un_componente_de_una_receta_vieja_no_le_cambia_el_calculo(ventana):
    from omnicad.ui.comando import ContextoComando
    from omnicad.ui.comandos.ensamblar import NuevoComponente
    from omnicad.timeline.ops_ensamblar import OpComponente
    v = ventana
    op = v.doc.operaciones[-1]
    viejo = OpComponente(op.id, op.nombre, op.suprimida, **dict(op.p, version_pose=1))
    v.doc.reemplazar(op.id, viejo)
    ctx = ContextoComando(v.doc, v, viejo)
    c = NuevoComponente()
    nueva = c.construir(c.desde_op(viejo, ctx), ctx)
    assert nueva.p["version_pose"] == 1
    assert c.construir(c.desde_op(viejo, ContextoComando(v.doc, v, None)), ContextoComando(v.doc, v, None)).p["version_pose"] == 2


def test_un_cambio_del_documento_limpia_el_dibujo_y_la_barra(ventana):
    v = ventana
    _arrastrar(v)
    assert api.llamar(api.Sesion(v.doc), "create_box", {"length": 5, "width": 5, "height": 5, "x": 300})["ok"]
    assert pendiente_de(v.doc) is None and not v.visor.transformaciones and v.arrastre.barra.isHidden()

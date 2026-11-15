"""P-98: el cero del plano pertenece a la arista elegida, no al ángulo."""
import copy

import numpy as np
import pytest

from omnicad import api


def _llamar(sesion, herramienta, **argumentos):
    respuesta = api.llamar(sesion, herramienta, argumentos)
    assert respuesta["ok"], respuesta
    return respuesta["result"]


def _crear():
    sesion = api.Sesion()
    _llamar(sesion, "create_box", length=20, width=30, height=40, anchor="corner")
    plano = _llamar(sesion, "create_construction_plane", type="angle",
                    references=["edges:>X and >Y"], angle=30)["plane"]["id"]
    return sesion, plano


def test_api_cambiar_arista_reelige_el_cero_y_se_puede_deshacer(tmp_path):
    sesion, plano = _crear()
    assert sesion.paso(plano).p["eje_0"] == "Y"
    patron = _llamar(sesion, "create_construction_plane", type="angle",
                     references=["edges:>Y and >Z"], angle=30)["plane"]["id"]
    referencia = copy.deepcopy(sesion.paso(patron).p["refs"])
    _llamar(sesion, "edit_feature", feature=plano, params={"refs": referencia})
    assert sesion.paso(plano).p["eje_0"] == "Z"
    assert np.abs(sesion.doc.estado_final.planos[plano].normal) == pytest.approx((0, 0.5, 3 ** 0.5 / 2))
    _llamar(sesion, "undo")
    assert sesion.paso(plano).p["eje_0"] == "Y"
    _llamar(sesion, "redo")
    assert sesion.paso(plano).p["eje_0"] == "Z"
    ruta = tmp_path / "plano.omnicad"
    _llamar(sesion, "save_document", path=str(ruta))
    otra = api.Sesion()
    _llamar(otra, "open_document", path=str(ruta))
    assert otra.paso(plano).p["eje_0"] == "Z"
    assert otra.doc.estado_final.planos[plano].normal == pytest.approx(sesion.doc.estado_final.planos[plano].normal)


def test_api_cambiar_solo_angulo_conserva_un_cero_no_predeterminado():
    sesion, plano = _crear()
    _llamar(sesion, "edit_feature", feature=plano, params={"eje_0": "X"})
    antes = sesion.doc.estado_final.planos[plano].normal.copy()
    # Reenviar la misma referencia por valor tampoco es elegir otra arista.
    _llamar(sesion, "edit_feature", feature=plano,
             params={"angulo": "60 deg", "refs": copy.deepcopy(sesion.paso(plano).p["refs"])})
    assert sesion.paso(plano).p["eje_0"] == "X"
    assert not np.allclose(antes, sesion.doc.estado_final.planos[plano].normal)


def test_panel_cambiar_arista_con_clic_reelige_el_cero_y_teclear_angulo_lo_conserva():
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication

    from omnicad.ui.comando import ContextoComando, PanelComando
    from omnicad.ui.comandos import comando_para
    from omnicad.ui.visor3d import Visor3D

    app = QApplication.instance() or QApplication([])
    sesion, plano = _crear()
    _llamar(sesion, "edit_feature", feature=plano, params={"eje_0": "X"})
    op = sesion.paso(plano)
    visor = Visor3D()
    visor.resize(800, 600)
    visor.set_modelo(sesion.doc.estado_en(sesion.doc.indice(plano)))
    visor.vista("iso")
    visor.encuadrar()
    panel = PanelComando(comando_para(op)(), ContextoComando(sesion.doc, None, op), visor)
    aceptadas = []
    panel.aceptado.connect(aceptadas.append)
    visor.show()
    panel.show()
    app.processEvents()
    try:
        campo = panel.widgets["angulo"]
        QTest.keyClick(campo, Qt.Key_A, Qt.ControlModifier)
        QTest.keyClicks(campo, "60 deg")
        assert panel.comando.construir(panel.valores, panel.ctx).p["eje_0"] == "X"
        QTest.mouseClick(panel.filas_sel["r0"].boton, Qt.LeftButton)
        posicion = visor.proyectar((10, 30, 40))
        assert posicion is not None
        QTest.mouseClick(visor, Qt.LeftButton, pos=posicion.toPoint())
        assert panel.valores["r0"][0]["ref"] != op.p["refs"][0]
        nueva = panel.comando.construir(panel.valores, panel.ctx)
        assert nueva.p["eje_0"] == "Z"
        QTest.keyClick(campo, Qt.Key_A, Qt.ControlModifier)
        QTest.keyClicks(campo, "45 deg")
        assert panel.comando.construir(panel.valores, panel.ctx).p["eje_0"] == "Z"
        QTest.mouseClick(panel.boton_ok, Qt.LeftButton)
        assert len(aceptadas) == 1 and aceptadas[0].p["eje_0"] == "Z"
    finally:
        if not panel.cerrando:
            panel.cancelar()
        panel.close()
        visor.close()

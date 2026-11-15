"""B-435: Cantidad incluye el original y exige al menos dos instancias, también al teclear."""
import pytest
from PySide6.QtCore import QSettings, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from omnicad import api
from omnicad.nucleo import geometria as geo
from omnicad.ui import temas
from omnicad.ui.comando import hit_desde_ref
from omnicad.ui.comandos import CATALOGO
from omnicad.ui.preferencias import Preferencias
from omnicad.ui.ventana import VentanaPrincipal


MENSAJE = "⚠ Cantidad: un entero de 2 o más (cuenta el original)"


def _llamar(sesion, nombre, **args):
    respuesta = api.llamar(sesion, nombre, args)
    assert respuesta["ok"], respuesta
    return respuesta["result"]


def _caso():
    sesion = api.Sesion()
    cuerpo = _llamar(sesion, "create_box", length=4, width=4, height=4)["bodies_created"][0]["id"]
    _llamar(sesion, "create_sketch", name="Ruta", plane="XY")
    curva = _llamar(sesion, "draw_line", sketch="Ruta", start_x=0, start_y=0, end_x=60, end_y=0)["entities"][0]["id"]
    ruta = {"tipo": "curva_boceto", "boceto": sesion.paso("Ruta").id, "curva": curva}
    return sesion, cuerpo, ruta


@pytest.mark.parametrize("cantidad", [0, 1])
@pytest.mark.parametrize("herramienta", ["path_pattern", "run_operation"])
def test_api_rechaza_cantidad_menor_que_dos_sin_cambiar_el_documento(herramienta, cantidad):
    sesion, cuerpo, ruta = _caso()
    if herramienta == "path_pattern":
        args = {"bodies": cuerpo, "path_sketch": "Ruta", "count": cantidad, "distance": 30}
    else:
        args = {"type": "patron", "params": {
            "forma_patron": "ruta", "cuerpos": [cuerpo], "ruta": [ruta], "n1": cantidad, "d1": "30 mm"}}
    antes = sesion.doc.a_dict()
    respuesta = api.llamar(sesion, herramienta, args)
    assert not respuesta["ok"], respuesta
    assert respuesta["mensaje"].endswith(MENSAJE)
    assert sesion.doc.a_dict() == antes
    assert list(sesion.doc.estado_final.cuerpos) == [cuerpo]


def test_api_acepta_dos_instancias_y_la_copia_es_valida():
    sesion, cuerpo, _ = _caso()
    resultado = _llamar(sesion, "path_pattern", bodies=cuerpo, path_sketch="Ruta", count=2, distance=30)
    assert len(resultado["bodies_created"]) == 1
    copia = sesion.cuerpo(resultado["bodies_created"][0]["id"]).forma
    assert geo.es_valida(copia) and geo.volumen(copia) == pytest.approx(64)
    assert geo.caja_envolvente(copia)[0][0] == pytest.approx(28)


@pytest.mark.parametrize("cantidad", ["0", "1"])
@pytest.mark.parametrize("clave,pre", [("patron_ruta", ""), ("multitransformar", "t_")])
def test_teclear_cantidad_invalida_marca_rojo_y_aceptar_no_modifica(tmp_path, clave, pre, cantidad):
    app = QApplication.instance() or QApplication([])
    sesion, cuerpo, ruta = _caso()
    ventana = VentanaPrincipal(sesion.doc, prefs=Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat)))
    try:
        ventana.resize(1280, 800)
        ventana.show()
        panel = ventana.ejecutar_comando(CATALOGO[clave]())
        if pre:
            panel.set_valor("t_tipo", "ruta")
        estado = panel.ctx.estado
        panel.set_valor("cuerpos", [hit_desde_ref({"tipo": "cuerpo", "cuerpo": cuerpo}, estado)])
        panel.set_valor(pre + "ruta", [hit_desde_ref(ruta, estado)])
        app.processEvents()
        campo = panel.widgets[pre + "rn"]
        panel.desplazador.ensureWidgetVisible(campo)
        antes = sesion.doc.a_dict()
        ventana.activateWindow()
        campo.setFocus()
        app.processEvents()
        QTest.keyClick(campo, Qt.Key_A, Qt.ControlModifier)
        QTest.keyClicks(campo, cantidad)
        assert campo.text() == cantidad
        assert campo.hasFocus()  # sin Enter, Tab ni pérdida de foco
        assert temas.color("campo_error") in campo.styleSheet()
        assert campo.toolTip() == MENSAJE
        QTest.mouseClick(panel.boton_ok, Qt.LeftButton)
        assert ventana.panel is panel and sesion.doc.a_dict() == antes

        campo.setFocus()
        QTest.keyClick(campo, Qt.Key_A, Qt.ControlModifier)
        QTest.keyClicks(campo, "2")
        assert not campo.styleSheet() and pre + "rn" not in panel.invalidos
        QTest.mouseClick(panel.boton_ok, Qt.LeftButton)
        assert ventana.panel is None
        assert len(sesion.doc.operaciones) == len(antes["operaciones"]) + 1
        assert len(sesion.doc.estado_final.cuerpos) == 2
        assert all(geo.es_valida(c.forma) and geo.volumen(c.forma) == pytest.approx(64)
                   for c in sesion.doc.estado_final.cuerpos.values())
    finally:
        if ventana.panel is not None:
            ventana.panel.cancelar()
        ventana.doc.modificado = False
        ventana.close()
        ventana.deleteLater()
        app.processEvents()

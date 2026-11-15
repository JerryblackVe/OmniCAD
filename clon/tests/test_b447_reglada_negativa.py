"""B-447: distancia con signo, previa visible y rechazo atómico de regladas cruzadas."""
import math

import pytest
from PySide6.QtCore import QSettings, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from omnicad import api
from omnicad.nucleo import geometria as geo, revision
from omnicad.ui.comando import hit_desde_ref
from omnicad.ui.comandos import CATALOGO
from omnicad.ui.preferencias import Preferencias
from omnicad.ui.ventana import VentanaPrincipal


def _llamar(sesion, nombre, **args):
    respuesta = api.llamar(sesion, nombre, args)
    assert respuesta["ok"], respuesta
    return respuesta["result"]


def _circulo(radio):
    sesion = api.Sesion()
    _llamar(sesion, "create_sketch", name="Círculo")
    curva = _llamar(sesion, "draw_circle", radius=radio)["entities"][0]["id"]
    return sesion, {"sketch": "Círculo", "curve": curva}


def _comprobar(forma, tipo, distancia):
    assert geo.es_valida(forma)
    cantidad, _, completo = revision._autointersecciones_seguras(forma, 1, 5.0)
    assert completo and cantidad == 0
    caja = geo.caja_envolvente(forma)
    if tipo == "tangent":
        radio = 30 if distancia > 0 else 20
        assert caja[0] == pytest.approx((-radio, -radio, 0), abs=1e-5)
        assert caja[1] == pytest.approx((radio, radio, 0), abs=1e-5)
        assert geo.area(forma) == pytest.approx((500 if distancia > 0 else 300) * math.pi)
    else:
        assert caja[0] == pytest.approx((-20, -20, min(0, distancia)), abs=1e-5)
        assert caja[1] == pytest.approx((20, 20, max(0, distancia)), abs=1e-5)
        assert geo.area(forma) == pytest.approx(400 * math.pi)


@pytest.mark.parametrize("tipo", ["tangent", "normal", "direction"])
def test_api_distancia_con_signo_conserva_lado_y_geometria_sana(tipo):
    sesion, curva = _circulo(20)
    for distancia in (10, -10):
        resultado = _llamar(sesion, "create_ruled_surface", edges=curva, distance=distancia,
                            surface_type=tipo, direction="Z")
        _comprobar(sesion.cuerpo(resultado["bodies_created"][0]["id"]).forma, tipo, distancia)


@pytest.mark.parametrize("tipo,angulo", [("tangent", 0), ("normal", 90), ("direction", 90)])
@pytest.mark.parametrize("distancia", [-6, -10])
def test_api_rechaza_la_reglada_que_cruza_el_centro_sin_modificar_el_documento(tipo, angulo, distancia):
    sesion, curva = _circulo(5)
    antes = sesion.doc.a_dict()
    respuesta = api.llamar(sesion, "create_ruled_surface", {
        "edges": curva, "distance": distancia, "surface_type": tipo, "angle": angulo, "direction": "Z"})
    assert not respuesta["ok"], respuesta
    assert "La reglada se cruza" in respuesta["mensaje"]
    assert sesion.doc.a_dict() == antes


def _teclear(campo, texto):
    campo.setFocus()
    QTest.keyClick(campo, Qt.Key_A, Qt.ControlModifier)
    QTest.keyClicks(campo, texto)
    assert campo.text() == texto


def _esperar(condicion, mensaje):
    for _ in range(300):
        if condicion():
            return
        QTest.qWait(20)
    assert condicion(), mensaje()


@pytest.mark.parametrize("tipo", ["tangent", "normal", "direction"])
@pytest.mark.parametrize("radio", [20, 5])
def test_panel_teclear_signo_muestra_previa_o_error_y_se_recupera(tmp_path, tipo, radio):
    app = QApplication.instance() or QApplication([])
    sesion, curva = _circulo(radio)
    ventana = VentanaPrincipal(sesion.doc, prefs=Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat)))
    ventana.resize(1280, 800)
    ventana.show()
    try:
        panel = ventana.ejecutar_comando(CATALOGO["reglada"]())
        panel.set_valor("aristas", [hit_desde_ref({
            "tipo": "curva_boceto", "boceto": sesion.paso("Círculo").id, "curva": curva["curve"]}, panel.ctx.estado)])
        combo = panel.widgets["tipo"]
        combo.setFocus()
        QTest.keyClick(combo, Qt.Key_Home)
        for _ in range(combo.findData({"tangent": "tangente", "normal": "normal", "direction": "direccion"}[tipo])):
            QTest.keyClick(combo, Qt.Key_Down)
        if tipo == "direction":
            panel.set_valor("direccion", [hit_desde_ref({"tipo": "eje", "id": "Z"}, panel.ctx.estado)])
        app.processEvents()
        antes = sesion.doc.a_dict()
        for distancia in (10, -10, 10):
            _teclear(panel.widgets["distancia"], str(distancia))
            _esperar(lambda: not panel._t_previa.isActive() and panel._hijo_previa is None,
                     lambda: panel.mensaje.text())
            if radio == 5 and tipo == "tangent" and distancia < 0:
                assert not panel._previa_ok
                assert "La reglada se cruza" in panel.mensaje.text()
                assert not ventana._estado_previa.cuerpos
                QTest.mouseClick(panel.boton_ok, Qt.LeftButton)
                assert ventana.panel is panel
            else:
                assert panel._previa_ok, panel.mensaje.text()
                forma = next(iter(ventana._estado_previa.cuerpos.values())).forma
                assert geo.es_valida(forma)
                assert revision._autointersecciones_seguras(forma, 1, 5.0)[0] == 0
                assert ventana.visor.cuerpos_de_previa
                if radio == 20:
                    _comprobar(forma, tipo, distancia)
            assert sesion.doc.a_dict()["operaciones"] == antes["operaciones"]
            assert not sesion.doc.estado_final.cuerpos
        QTest.mouseClick(panel.boton_ok, Qt.LeftButton)
        assert ventana.panel is None
        assert len(sesion.doc.estado_final.cuerpos) == 1
    finally:
        if ventana.panel is not None:
            ventana.panel.cancelar()
        ventana.doc.modificado = False
        ventana.close()
        ventana.deleteLater()
        app.processEvents()

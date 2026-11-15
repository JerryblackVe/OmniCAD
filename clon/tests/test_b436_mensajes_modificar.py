"""B-436: cada medida imposible nombra su campo y su causa, sin culpar a otra herramienta."""
import pytest
from PySide6.QtCore import QSettings, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from omnicad import api
from omnicad.api import selectores as sl
from omnicad.nucleo import geometria as geo, solidos_modificar as sm
from omnicad.ui import temas
from omnicad.ui.comando import hit_desde_ref
from omnicad.ui.comandos import CATALOGO
from omnicad.ui.preferencias import Preferencias
from omnicad.ui.ventana import VentanaPrincipal


ARISTA = "|X and >Z and <Y"


def _llamar(sesion, nombre, **argumentos):
    respuesta = api.llamar(sesion, nombre, argumentos)
    assert respuesta["ok"], respuesta
    return respuesta["result"]


def _caja(redondeada=False):
    sesion = api.Sesion()
    _llamar(sesion, "create_box", length=40, width=30, height=20)
    if redondeada:
        _llamar(sesion, "fillet", edges=ARISTA, radius_type="variable", radius=1, end_radius=3)
    return sesion


@pytest.mark.parametrize("argumento,etiqueta", [("radius", "Radio"), ("end_radius", "Radio final")])
@pytest.mark.parametrize("valor", ["-1 mm", "0 mm"])
def test_api_empalme_variable_identifica_el_radio_invalido(argumento, etiqueta, valor):
    sesion = _caja()
    antes = sesion.doc.a_dict()
    argumentos = {"edges": ARISTA, "radius_type": "variable", "radius": 1, "end_radius": 3, argumento: valor}
    respuesta = api.llamar(sesion, "fillet", argumentos)
    assert not respuesta["ok"], respuesta
    mensaje = respuesta["mensaje"]
    assert etiqueta in mensaje and "mayor que 0" in mensaje and valor.split()[0] in mensaje, mensaje
    assert "2 puntos" not in mensaje
    assert sesion.doc.a_dict() == antes


def test_api_distancia_menos50_en_cara_con_empalme_no_culpa_a_las_roscas():
    sesion = _caja(redondeada=True)
    antes = sesion.doc.a_dict()
    respuesta = api.llamar(sesion, "offset_faces", {"faces": "+Z", "distance": -50})
    assert not respuesta["ok"], respuesta
    mensaje = respuesta["mensaje"]
    assert "Distancia" in mensaje and "-50" in mensaje and "atraviesa" in mensaje, mensaje
    assert "rosca" not in mensaje
    assert sesion.doc.a_dict() == antes


@pytest.mark.parametrize("distancia", [-5, 5])
def test_api_conserva_distancias_validas_de_ambos_signos(distancia):
    sesion = _caja()
    _llamar(sesion, "offset_faces", faces="+Z", distance=distancia)
    forma = next(iter(sesion.doc.estado_final.cuerpos.values())).forma
    assert geo.es_valida(forma)
    assert geo.volumen(forma) == pytest.approx(40 * 30 * (20 + distancia))


@pytest.mark.parametrize("clave,campo,etiqueta,texto,sano", [
    ("empalme_3d", "radio", "Radio", "-1", "1"),
    ("empalme_3d", "radio_fin", "Radio final", "-1", "3"),
    ("pulsar_tirar", "distancia", "Distancia", "-50", "-1"),
])
def test_teclear_marca_el_campo_correcto_y_no_deja_aceptar(tmp_path, monkeypatch, clave, campo, etiqueta, texto, sano):
    monkeypatch.setenv("OMNICAD_PREAJUSTES", str(tmp_path / "preajustes.json"))
    app = QApplication.instance() or QApplication([])
    sesion = _caja(redondeada=clave == "pulsar_tirar")
    ventana = VentanaPrincipal(sesion.doc, prefs=Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat)))
    try:
        ventana.resize(1280, 800)
        ventana.show()
        panel = ventana.ejecutar_comando(CATALOGO[clave]())
        if clave == "empalme_3d":
            panel.set_valor("tipo_radio", "variable")
        cuerpo, entidad = sl.elegir(sesion, ARISTA if clave == "empalme_3d" else "+Z",
                                    "arista" if clave == "empalme_3d" else "cara")[0]
        panel.set_valor("aristas" if clave == "empalme_3d" else "objetos",
                        [hit_desde_ref(sl.referencia(cuerpo, entidad), panel.ctx.estado)])
        app.processEvents()
        widget = panel.widgets[campo]
        panel.desplazador.ensureWidgetVisible(widget)
        antes = sesion.doc.a_dict()
        widget.setFocus()
        QTest.keyClick(widget, Qt.Key_A, Qt.ControlModifier)
        QTest.keyClicks(widget, texto)
        assert widget.text() == texto
        panel._t_previa.stop()
        panel._calcular_previa()
        assert campo in panel.invalidos and temas.color("campo_error") in widget.styleSheet()
        mensaje = widget.toolTip()
        assert etiqueta in mensaje and texto in mensaje, mensaje
        assert ("mayor que 0" if clave == "empalme_3d" else "atraviesa") in mensaje, mensaje
        assert "2 puntos" not in mensaje and "rosca" not in mensaje
        assert mensaje in panel.mensaje.text()
        QTest.mouseClick(panel.boton_ok, Qt.LeftButton)
        assert ventana.panel is panel and sesion.doc.a_dict() == antes

        QTest.keyClick(widget, Qt.Key_A, Qt.ControlModifier)
        QTest.keyClicks(widget, sano)
        panel._t_previa.stop()
        panel._calcular_previa()
        assert campo not in panel.invalidos and not widget.styleSheet()
    finally:
        if ventana.panel is not None:
            ventana.panel.cancelar()
        ventana.doc.modificado = False
        ventana.close()
        ventana.deleteLater()
        app.processEvents()


def test_empalme_variable_sigue_exigiendo_dos_puntos():
    sesion = _caja()
    cuerpo, arista = sl.elegir(sesion, ARISTA, "arista")[0]
    with pytest.raises(geo.ErrorGeometria, match="2 puntos"):
        sm.empalme(cuerpo.forma, [{"tipo": "variable", "aristas": [arista.sub], "radios": [(0, 1)]}])


def test_api_radio_intermedio_invalido_nombra_su_posicion():
    sesion = _caja()
    respuesta = api.llamar(sesion, "fillet", {"edges": ARISTA, "radius_type": "variable", "radius": 1, "end_radius": 3,
                                            "radius_points": [{"position": 0.5, "radius": "-1 mm"}]})
    assert not respuesta["ok"], respuesta
    assert "Radio en posición 0.5" in respuesta["mensaje"] and "mayor que 0" in respuesta["mensaje"]

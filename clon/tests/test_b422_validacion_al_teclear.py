"""B-422: las medidas imposibles se marcan al teclear y no llegan al timeline."""
import math

import pytest
from PySide6.QtCore import QSettings, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from omnicad import api
from omnicad.api import selectores as sl
from omnicad.nucleo import geometria as geo
from omnicad.timeline.operaciones import OpExtrusion
from omnicad.ui import comando as ui_comando, temas
from omnicad.ui.comando import hit_desde_ref
from omnicad.ui.comandos import CATALOGO
from omnicad.ui.preferencias import Preferencias
from omnicad.ui.ventana import VentanaPrincipal


MENSAJES = {"agujero": "La profundidad del agujero debe ser positiva.",
            "revolucion": "El ángulo de revolución no puede ser cero."}


def _llamar(sesion, nombre, **args):
    respuesta = api.llamar(sesion, nombre, args)
    assert respuesta["ok"], respuesta
    return respuesta["result"]


def _caso(clave):
    sesion = api.Sesion()
    if clave == "agujero":
        _llamar(sesion, "create_box", length=20, width=20, height=20)
        return sesion, "create_hole", {"face": ">Z", "diameter": 6}, "depth"
    _llamar(sesion, "create_sketch", name="Perfil", plane="XZ")
    _llamar(sesion, "draw_rectangle", sketch="Perfil", x1=5, y1=0, x2=10, y2=20)
    return sesion, "revolve", {"sketch": "Perfil", "axis": "z"}, "angle"


@pytest.mark.parametrize("clave,valor", [("agujero", -5), ("agujero", "-5 mm"), ("agujero", "0 mm"),
                                         ("revolucion", 0), ("revolucion", "0 deg")])
def test_api_rechaza_con_el_mensaje_del_nucleo_y_sin_cambiar_el_documento(clave, valor):
    sesion, herramienta, args, medida = _caso(clave)
    antes = sesion.doc.a_dict()
    respuesta = api.llamar(sesion, herramienta, {**args, medida: valor})
    assert not respuesta["ok"], respuesta
    # La API antepone el paso y la confirmación de que la transacción se deshizo.
    assert respuesta["mensaje"].endswith(MENSAJES[clave])
    assert sesion.doc.a_dict() == antes


def _teclear(campo, texto):
    campo.window().activateWindow()
    campo.setFocus()
    QTest.keyClick(campo, Qt.Key_A, Qt.ControlModifier)
    QTest.keyClicks(campo, texto)
    assert campo.text() == texto
    assert campo.hasFocus()                 # sin Enter, Tab ni pérdida del foco


@pytest.mark.parametrize("aparte", [False, True])
@pytest.mark.parametrize("clave,campo,texto,sano,volumen", [
    ("agujero", "profundidad", "-5", "5", 8000 - math.pi * 3**2 * 5),
    ("agujero", "profundidad", "0", "5", 8000 - math.pi * 3**2 * 5),
    ("revolucion", "angulo", "0", "90", math.pi * (10**2 - 5**2) * 20 / 4),
    ("revolucion", "angulo2", "0", "90", math.pi * (10**2 - 5**2) * 20 / 2),
])
def test_teclear_marca_rojo_muestra_el_motivo_y_aceptar_no_crea_el_paso(
        tmp_path, monkeypatch, aparte, clave, campo, texto, sano, volumen):
    monkeypatch.setenv("OMNICAD_PREAJUSTES", str(tmp_path / "preajustes.json"))
    monkeypatch.setattr(ui_comando, "PREVIA_APARTE", aparte)
    app = QApplication.instance() or QApplication([])
    sesion, _, _, _ = _caso(clave)
    ventana = VentanaPrincipal(sesion.doc, prefs=Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat)))
    try:
        ventana.resize(1280, 800)
        ventana.show()
        panel = ventana.ejecutar_comando(CATALOGO[clave]())
        estado = panel.ctx.estado
        if clave == "agujero":
            cuerpo, cara = sl.elegir(sesion, ">Z", "cara")[0]
            hit = hit_desde_ref(sl.referencia(cuerpo, cara), estado)
            hit["punto"] = cara.centro
            panel.set_valor("colocacion", [hit])
            panel.set_valor("punta", "plana")
        else:
            boceto = sesion.paso("Perfil").id
            perfil = estado.bocetos[boceto].perfiles[0]
            panel.set_valor("perfiles", [hit_desde_ref(
                {"tipo": "perfil", "boceto": boceto, **OpExtrusion.referencia_perfil(perfil)}, estado)])
            panel.set_valor("eje", [hit_desde_ref({"tipo": "eje", "id": "Z"}, estado)])
            if campo == "angulo2":
                panel.set_valor("direccion", "dos_lados")
                panel.set_valor("angulo", "90 deg")
        app.processEvents()
        widget = panel.widgets[campo]
        panel.desplazador.ensureWidgetVisible(widget)
        antes = sesion.doc.a_dict()
        _teclear(widget, texto)
        assert temas.color("campo_error") in widget.styleSheet(), "La medida imposible no quedó en rojo al teclear."
        assert widget.toolTip() == MENSAJES[clave]
        for _ in range(100):
            if panel.mensaje.text() == MENSAJES[clave]:
                break
            QTest.qWait(20)
        assert panel.mensaje.text() == MENSAJES[clave]
        invalido = sesion.doc.a_dict()
        assert invalido["operaciones"] == antes["operaciones"]
        QTest.mouseClick(panel.boton_ok, Qt.LeftButton)
        assert ventana.panel is panel and sesion.doc.a_dict() == invalido
        assert panel.ultima_op is None

        _teclear(widget, sano)
        assert not widget.styleSheet() and campo not in panel.invalidos
        QTest.mouseClick(panel.boton_ok, Qt.LeftButton)
        assert ventana.panel is None
        assert len(sesion.doc.operaciones) == len(antes["operaciones"]) + 1
        forma = next(iter(sesion.doc.estado_final.cuerpos.values())).forma
        assert geo.es_valida(forma) and geo.volumen(forma) == pytest.approx(volumen)
    finally:
        if ventana.panel is not None:
            ventana.panel.cancelar()
        ventana.doc.modificado = False
        ventana.close()
        ventana.deleteLater()
        app.processEvents()

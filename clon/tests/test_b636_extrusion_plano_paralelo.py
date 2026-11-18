"""B-636: un plano paralelo al avance no puede ser el límite de Extruir."""
import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from omnicad import api
from omnicad.ui import temas
from omnicad.ui.comando import hit_desde_ref
from omnicad.ui.comandos import CATALOGO
from omnicad.ui.preferencias import Preferencias
from omnicad.ui.ventana import VentanaPrincipal


@pytest.fixture
def boceto():
    sesion = api.Sesion()
    creado = api.llamar(sesion, "create_sketch", {"plane": "XY", "name": "B"})
    assert creado["ok"], creado
    linea = api.llamar(sesion, "draw_line", {"start_x": -10, "start_y": 0, "end_x": 10, "end_y": 0})
    assert linea["ok"], linea
    return sesion, linea["result"]["entities"][0]["id"]


def test_api_rechaza_el_plano_paralelo_sin_agregar_un_paso(boceto):
    sesion, curva = boceto
    antes = sesion.doc.a_dict()
    respuesta = api.llamar(sesion, "extrude", {"sketch": "B", "open_curves": [curva], "thin": True,
                                              "extent": "to_object", "to": "XZ"})
    assert not respuesta["ok"], respuesta
    assert "paralelo" in respuesta["mensaje"], respuesta
    assert sesion.doc.a_dict() == antes


@pytest.mark.parametrize("lado", ["", "2"])
def test_el_panel_marca_el_limite_paralelo_y_se_recupera(boceto, lado, tmp_path, monkeypatch):
    monkeypatch.setenv("OMNICAD_PREAJUSTES", str(tmp_path / "preajustes.json"))
    sesion, curva = boceto
    plano = api.llamar(sesion, "create_construction_plane", {"plane": "XY", "offset": 7})
    assert plano["ok"], plano
    app = QApplication.instance() or QApplication([])
    ventana = VentanaPrincipal(sesion.doc, prefs=Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat)))
    try:
        panel = ventana.ejecutar_comando(CATALOGO["extruir"]())
        estado = panel.ctx.estado
        perfil = hit_desde_ref({"tipo": "curva_boceto", "boceto": next(iter(estado.bocetos)), "curva": curva}, estado)
        campo = "hasta" + lado
        panel.set_valores({"tipo": "delgada", "perfiles": [perfil], "distancia": "5 mm",
                           "direccion": "dos_lados" if lado else "un_lado", "extension" + lado: "objeto",
                           campo: [hit_desde_ref({"tipo": "plano", "id": "XZ"}, estado)]})
        panel._t_previa.stop()
        panel._calcular_previa()

        mensaje = panel.mensaje.text()
        assert "paralelo" in mensaje and len(mensaje) <= 45 and "\n" not in mensaje, mensaje
        assert "⚠" not in mensaje and panel.icono_mensaje.text() == "✖"
        boton = panel.filas_sel[campo].boton
        assert temas.color("campo_error") in boton.styleSheet()
        assert not panel.boton_ok.isEnabled()

        panel.set_valor(campo, [hit_desde_ref({"tipo": "plano", "id": next(iter(estado.planos))}, estado)])
        panel._t_previa.stop()
        panel._calcular_previa()
        assert panel._previa_ok, panel.mensaje.text()
        assert not boton.styleSheet() and panel.boton_ok.isEnabled()
    finally:
        if ventana.panel is not None:
            ventana.panel.cancelar()
        sesion.doc.modificado = False
        ventana.close()
        ventana.deleteLater()
        app.processEvents()

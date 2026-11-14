"""B-431: una operación heredada no impide la primera previa de Solevación."""
import math

import pytest
from PySide6.QtCore import QSettings, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from omnicad import api
from omnicad.nucleo import geometria as geo
from omnicad.nucleo import preajustes
from omnicad.timeline.operaciones import OpExtrusion
from omnicad.ui.comando import hit_desde_ref
from omnicad.ui.comandos.crear import Solevacion
from omnicad.ui.preferencias import Preferencias
from omnicad.ui.ventana import VentanaPrincipal


def _llamar(sesion, nombre, **args):
    respuesta = api.llamar(sesion, nombre, args)
    assert respuesta["ok"], respuesta
    return respuesta["result"]


@pytest.fixture
def escena(tmp_path, monkeypatch):
    monkeypatch.setenv("OMNICAD_PREAJUSTES", str(tmp_path / "preajustes.json"))
    app = QApplication.instance() or QApplication([])
    sesion = api.Sesion()
    cuerpo = _llamar(sesion, "create_box", length=10, width=10, height=10, x=100)["bodies_created"][0]["id"]
    perfiles = []
    for z in (0, 20):
        plano = _llamar(sesion, "create_construction_plane", offset=z)["plane"]["id"]
        _llamar(sesion, "sketch_from_spec", plane=plano,
                entities=[{"type": "circle", "center": [0, 0], "radius": 5}])
        boceto = sesion.doc.operaciones[-1].id
        perfil = sesion.doc.estado_final.bocetos[boceto].perfiles[0]
        perfiles.append({"tipo": "perfil", "boceto": boceto, **OpExtrusion.referencia_perfil(perfil)})
    ventana = VentanaPrincipal(sesion.doc, prefs=Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat)))
    ventana.show()
    try:
        yield sesion, ventana, cuerpo, perfiles
    finally:
        if ventana.panel is not None:
            ventana.panel.cancelar()
        ventana.doc.modificado = False
        ventana.close()
        ventana.deleteLater()
        app.processEvents()


@pytest.mark.parametrize("origen", ["fabrica", "ultimo", "preajuste"])
def test_sin_objetivo_abre_en_nuevo_y_muestra_la_solevacion(escena, origen):
    sesion, ventana, cuerpo, perfiles = escena
    if origen == "ultimo":
        preajustes.guardar_ultimo("solevacion", {"operacion": "cortar"})
        _llamar(sesion, "manage_command_presets", command="solevacion", action="set_default", default="last_used")
    elif origen == "preajuste":
        _llamar(sesion, "manage_command_presets", command="solevacion", action="save", name="Corte",
                values={"operacion": "cortar"})
        _llamar(sesion, "manage_command_presets", command="solevacion", action="set_default", default="Corte")
    panel = ventana.ejecutar_comando(Solevacion())
    inicial = panel.widgets["operacion"].currentData()
    for ref in perfiles:
        ventana.visor.entidad_elegida.emit(hit_desde_ref(ref, panel.ctx.estado))
    QTest.qWait(500)
    assert panel._previa_ok, panel.mensaje.text()
    assert (inicial, bool(ventana.visor.cuerpos_de_previa)) == ("nuevo", True)
    assert panel.valores["operacion"] == "nuevo"
    assert ventana.visor.cuerpos_de_previa
    assert len(ventana.doc.estado_final.cuerpos) == 1  # la previa no aplica el paso
    QTest.mouseClick(panel.boton_ok, Qt.LeftButton)
    assert ventana.panel is None
    cuerpos = ventana.doc.estado_final.cuerpos
    assert geo.volumen(cuerpos[cuerpo].forma) == pytest.approx(1000)
    (nuevo,) = [c for cid, c in cuerpos.items() if cid != cuerpo]
    assert geo.es_valida(nuevo.forma)
    assert geo.volumen(nuevo.forma) == pytest.approx(math.pi * 25 * 20)

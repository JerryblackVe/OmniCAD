"""P-161: Extruir toma solo el único perfil a la vista (como Fusion y Revolución desde B-471), y la operación automática
sigue: Unir si el perfil se apoya en un sólido visible, Cuerpo nuevo si está lejos."""
import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from omnicad import api
from omnicad.ui.comandos.solido import Extruir
from omnicad.ui.preferencias import Preferencias
from omnicad.ui.ventana import VentanaPrincipal
from test_cuerpos_partidos import llamar, previa, rectangulo


@pytest.fixture
def abrir(tmp_path):
    app = QApplication.instance() or QApplication([])
    ventanas = []

    def _abrir(s):
        v = VentanaPrincipal(s.doc, prefs=Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat)))
        ventanas.append(v)
        v.show()
        return v.ejecutar_comando(Extruir())
    yield _abrir
    for v in ventanas:
        if v.panel is not None:
            v.panel.cancelar()
        v.doc.modificado = False
        v.close()
        v.deleteLater()
    app.processEvents()


@pytest.mark.parametrize("x, distancia, esperada", [(40, "-5", "unir"), (40, "5", "cortar"), (200, "-5", "nuevo")])
def test_p161_toma_el_perfil_unico_y_la_operacion_sigue_sola(abrir, x, distancia, esperada):
    s = api.Sesion()
    llamar(s, "extrude", sketch=rectangulo(s, 0, -20, 100, 20), distance=10)     # su boceto ya se usó: no cuenta
    perfil = rectangulo(s, x, -5, x + 10, 5)
    p = abrir(s)
    assert [h["ref"]["boceto"] for h in p.valores["perfiles"]] == [perfil]
    p.set_valor("distancia", distancia)          # hacia afuera de la placa une, hacia adentro corta
    previa(p)
    assert p.valores["operacion"] == esperada


def test_p161_con_dos_perfiles_no_elige_ninguno(abrir):
    s = api.Sesion()
    rectangulo(s, 0, 0, 10, 10)
    rectangulo(s, 20, 0, 30, 10)
    assert not abrir(s).valores.get("perfiles")

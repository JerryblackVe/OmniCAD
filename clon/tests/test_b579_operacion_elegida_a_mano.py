"""B-579: en Extruir, la operación elegida a mano antes de que llegue la previa no la pisa la automática, aunque sea
la que ya estaba («Cuerpo nuevo» sobre un perfil que se mete en los cuerpos pasaba solo a «Cortar» y los borraba)."""
import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

from omnicad import api
from test_cuerpos_partidos import cuerpos, llamar, previa, rectangulo
from test_p161_extruir_perfil_unico import abrir  # noqa: F401 — fixture


def elegir_en_lista(combo, clave):
    """Como una persona: abre la lista de Operación y hace clic en la opción, aunque sea la que ya está."""
    combo.showPopup()
    vista = combo.view()
    rect = vista.visualRect(combo.model().index(combo.findData(clave), 0))
    QTest.mouseClick(vista.viewport(), Qt.LeftButton, pos=rect.center())


@pytest.mark.parametrize("elegida, queda, n", [(None, "cortar", 0), ("nuevo", "nuevo", 3), ("unir", "unir", 1)])
def test_b579_la_operacion_elegida_a_mano_queda(abrir, elegida, queda, n):  # noqa: F811
    s = api.Sesion()
    llamar(s, "extrude", sketch=rectangulo(s, 0, -20, 100, 20), distance=10)
    llamar(s, "extrude", sketch=rectangulo(s, 0, 30, 100, 60), distance=10)
    rectangulo(s, -10, -30, 110, 70)          # tapa los dos cuerpos: con Cortar, el documento queda vacío
    p = abrir(s)
    assert p.valores["perfiles"] and p.valores["operacion"] == "unir"    # B-753: el perfil apoyado en un sólido abre en Unir
    p.set_valor("distancia", "10")
    if elegida:
        elegir_en_lista(p.widgets["operacion"], elegida)    # antes de que llegue la previa
    previa(p)
    assert p.valores["operacion"] == queda    # sin elegir, pasa sola a Cortar como Fusion
    p.aceptar()
    assert len(cuerpos(s)) == n               # «Cuerpo nuevo» no borra ninguno; Unir junta los tres

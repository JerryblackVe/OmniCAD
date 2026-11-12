"""P-137: las flechas del manipulador contrastan con la selección y salen hacia afuera de la cara que se mueve."""
import numpy as np
import pytest
from test_manipuladores import _doc_caja, _cara_de_arriba, _manip, _panel, app_qt  # noqa: F401

from omnicad.ui import manipuladores as mp
from omnicad.ui.comandos import CATALOGO

pytestmark = pytest.mark.usefixtures("app_qt")
CELESTES = ((0.45, 0.70, 1.0), (0.35, 0.62, 1.0), (0.10, 0.35, 0.85))     # colores de la selección y el resalte del visor


@pytest.mark.parametrize("seleccion", CELESTES)
def test_el_color_de_la_flecha_no_se_confunde_con_la_seleccion(seleccion):
    for color in (mp.AMARILLO, mp.AMARILLO_ACTIVO):
        assert np.linalg.norm(np.array(color) - np.array(seleccion)) > 0.6


@pytest.mark.parametrize("clave, valor", [("desfase_cara", "-5 mm"), ("pulsar_tirar", "-5 mm"),
                                          ("desfase_cara", "5 mm")])
def test_la_flecha_de_una_cara_sale_hacia_afuera_con_valor_negativo_o_positivo(clave, valor):
    doc = _doc_caja()
    cara = _cara_de_arriba(doc)
    panel, visor, _ = _panel(CATALOGO[clave](), doc, {"objetos" if clave == "pulsar_tirar" else "caras": [cara],
                                                        "distancia": valor})
    try:
        flecha = _manip(panel, "flecha:distancia")
        base, punta = flecha.puntos(panel.manipuladores)
        assert (punta - base) @ np.array([0.0, 0.0, 1.0]) > 0          # la normal de la cara de arriba es +Z
        assert panel.manipuladores.cajas["distancia"] is not None
    finally:
        panel.cancelar()
        panel.deleteLater()
        visor.deleteLater()


def test_extruir_con_valor_negativo_sigue_apuntando_hacia_donde_crece_el_cuerpo():
    from test_manipuladores import _doc_rectangulo, _perfil
    from omnicad.ui.comandos.solido import Extruir
    doc = _doc_rectangulo()
    panel, visor, _ = _panel(Extruir(), doc, {"perfiles": [_perfil(doc)], "distancia": "-10 mm"})
    try:
        base, punta = _manip(panel, "flecha:distancia").puntos(panel.manipuladores)
        assert punta[2] < base[2]
    finally:
        panel.cancelar()
        panel.deleteLater()
        visor.deleteLater()

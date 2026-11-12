"""P-148: la escala de los peines es relativa a la pieza y su deslizador no llega a tapar la vista."""
import numpy as np
import pytest

from omnicad import api
from omnicad.nucleo import analisis as an
from omnicad.ui.comandos import CATALOGO
from omnicad.ui.comandos.comunes import ESCALA_PEINE_MAX, campos_iso


def _escala(campos, clave):
    return next(c for c in campos if c.clave == clave)


def test_los_dos_deslizadores_de_escala_topan_en_lo_mismo():
    assert _escala(campos_iso(), "escala_peine").maximo == ESCALA_PEINE_MAX
    assert _escala(CATALOGO["curvatura_peine"]().campos(None), "escala").maximo == ESCALA_PEINE_MAX


def _largo_relativo(radio):
    s = api.Sesion()
    assert api.llamar(s, "create_sphere", {"radius": radio})["ok"]
    forma = next(iter(s.doc.estado_final.cuerpos.values())).forma
    d = an.isocurvas(forma, n_u=6, n_v=6)
    puas = np.array(an.peines_isocurva(d["u"] + d["v"], escala=ESCALA_PEINE_MAX)["puas"])
    return np.linalg.norm(puas[:, 1] - puas[:, 0], axis=1).max() / (2 * radio)


def test_la_pua_mas_larga_al_tope_es_la_misma_fraccion_de_la_pieza_y_no_la_tapa():
    chica, grande = _largo_relativo(5), _largo_relativo(500)
    assert chica == pytest.approx(grande, rel=1e-3)      # relativa al tamaño, no un tope en mm
    assert chica < 1.0                                    # al tope del deslizador la púa no pasa de la pieza


def test_en_el_panel_se_teclean_decimales_y_no_pasa_del_tope():
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication
    from omnicad.timeline.documento import Documento
    from omnicad.ui.comando import ContextoComando, PanelComando
    from omnicad.ui.visor3d import Visor3D

    app = QApplication.instance() or QApplication([])
    doc = Documento()
    visor = Visor3D()
    visor.set_modelo(doc.estado_final)
    panel = PanelComando(CATALOGO["curvatura_peine"](), ContextoComando(doc), visor)
    panel.show()
    caja = panel.widgets["escala"].numero
    caja.selectAll()
    for letra in "12,5":                          # antes de P-148 cada tecla reescribía «1» como «1.000» y los decimales se perdían
        QTest.keyClicks(caja, letra)
        app.processEvents()
    assert caja.value() == 12.5 and panel.valores["escala"] == 12.5
    caja.selectAll()
    QTest.keyClicks(caja, "54")                  # el 4 haría 54 > tope: no entra
    assert caja.value() == 5
    caja.setValue(54.867)
    assert caja.value() == ESCALA_PEINE_MAX

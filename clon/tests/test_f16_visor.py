# -*- coding: utf-8 -*-
"""F16 (brechas_freecad.md): indicador del centro de giro mientras se orbita e iluminación de tres puntos
seleccionable en Preferencias › Gráficos (y `lighting` de `get_viewport_image`)."""
import os
from io import BytesIO

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint, QSettings, Qt  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402

from omnicad import api  # noqa: E402
from omnicad.ejemplo import crear_documento_ejemplo  # noqa: E402
from omnicad.ui import visor3d  # noqa: E402
from omnicad.ui.preferencias import DEFECTOS, DialogoPreferencias, Preferencias  # noqa: E402


@pytest.fixture
def visor():
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    v = visor3d.Visor3D()
    v.resize(800, 600)
    v.config.esquema_raton = "omnicad"          # izquierdo: órbita
    yield v
    v.deleteLater()


def test_el_indicador_aparece_al_orbitar_y_se_oculta_al_soltar(visor):
    assert not visor.mostrando_centro_giro()
    QTest.mousePress(visor, Qt.LeftButton, Qt.NoModifier, QPoint(400, 300))
    assert visor.mostrando_centro_giro()
    QTest.mouseMove(visor, QPoint(430, 310))
    assert visor.mostrando_centro_giro()
    QTest.mouseRelease(visor, Qt.LeftButton, Qt.NoModifier, QPoint(430, 310))
    assert not visor.mostrando_centro_giro()


def test_el_indicador_no_sale_al_desplazar_ni_con_la_opcion_apagada(visor):
    QTest.mousePress(visor, Qt.MiddleButton, Qt.NoModifier, QPoint(400, 300))     # medio = encuadre, no órbita
    assert not visor.mostrando_centro_giro()
    QTest.mouseRelease(visor, Qt.MiddleButton, Qt.NoModifier, QPoint(400, 300))
    visor.config.indicador_giro = False
    QTest.mousePress(visor, Qt.LeftButton, Qt.NoModifier, QPoint(400, 300))
    assert not visor.mostrando_centro_giro()
    QTest.mouseRelease(visor, Qt.LeftButton, Qt.NoModifier, QPoint(400, 300))


def test_la_cruz_esta_en_el_centro_de_giro_y_mide_9_px(visor):
    visor.objetivo = np.array([12.0, -7.0, 30.0])
    visor.distancia = 400.0
    (_, cruz, _, _), (_, punto, _, _) = visor.primitivas_centro_giro()
    pts, delante = visor.puntos_pantalla(np.vstack([cruz, punto]))
    assert delante.all()
    assert np.allclose(pts[4], visor.puntos_pantalla([visor.objetivo])[0][0], atol=1e-3)
    assert np.allclose(np.abs(pts[0] - pts[1]), [18, 0], atol=0.1)       # brazo horizontal: 9 px a cada lado
    assert np.allclose(np.abs(pts[2] - pts[3]), [0, 18], atol=0.1)       # brazo vertical


def test_tres_luces_suman_relleno_y_contorno_sin_tocar_la_de_siempre():
    assert len(visor3d.LUCES_VISOR["una"]) == 1 and len(visor3d.LUCES_VISOR["tres"]) == 3
    assert visor3d.LUCES_VISOR["una"][0] == ((0.3, 0.6, 1.0), 1.0, 1.0)      # la luz de antes, idéntica
    relleno, contorno = visor3d.LUCES_VISOR["tres"][1:]
    assert relleno[0][0] < 0 < visor3d.LUCES_VISOR["tres"][0][0][0]          # relleno del lado opuesto a la principal
    assert contorno[0][2] < 0                                                # contorno desde atrás


def test_las_preferencias_nuevas_tienen_defecto_y_estan_en_la_pagina_graficos(tmp_path):
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    assert DEFECTOS["graficos/luces"] == "una" and DEFECTOS["graficos/indicador_giro"] is True
    prefs = Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat))
    dlg = DialogoPreferencias(prefs, None, "graficos")
    dlg._poner("graficos/luces", "tres")
    dlg._poner("graficos/indicador_giro", False)
    assert prefs["graficos/luces"] == "tres" and prefs["graficos/indicador_giro"] is False
    dlg.deleteLater()


def test_el_render_cambia_con_tres_puntos_o_solo_la_principal():
    from PIL import Image
    s = api.Sesion(crear_documento_ejemplo())
    # Un metal solo recibe brillos del relleno y el contorno; el plástico mate sí cambia de tono en las caras.
    assert api.llamar(s, "set_appearance", {"bodies": ["op2.c1", "op6.c1"], "appearance": "Plástico - Mate (Gris)"})["ok"]

    def imagen(luces):
        r = api.llamar(s, "get_viewport_image", {"width": 200, "height": 150, "lighting": luces})
        assert r["ok"], r
        return np.asarray(Image.open(BytesIO(r["result"]["image"].png)).convert("RGB"), float)

    tres, una = imagen("three_point"), imagen("key_only")
    assert imagen("three_point").tolist() == tres.tolist()                   # determinista
    cambiados = (np.abs(tres - una).max(axis=2) > 8).sum()
    assert cambiados > 1000                                                  # las 3 luces cambian el render (≈2900 px)
    assert api.llamar(s, "get_viewport_image", {"lighting": "otra"})["error_kind"] == "INVALID_ARGUMENTS"

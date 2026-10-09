# -*- coding: utf-8 -*-
"""Preferencias › Gráficos de rendimiento (pendiente 10, paso 2): detalle de las piezas, «Dinámico», límite de
cuadros, valores predefinidos y su aplicación al instante en el diálogo."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402

from omnicad.nucleo import geometria as geo  # noqa: E402
from omnicad.ui import visor3d  # noqa: E402
from omnicad.ui.preferencias import (CLAVES_GRAFICOS, DETALLES, PRESETS, DialogoPreferencias,  # noqa: E402
                                     Preferencias)


def _triangulos(forma, deflexion, angular, rehacer=False):
    return len(geo.teselar(forma, deflexion, angular, rehacer)[0]) // 3


def test_rehacer_respeta_un_detalle_mas_grueso():
    c = geo.cilindro(10, 30, (0, 0, 0))
    fino = _triangulos(c, 0.01, 0.2)
    assert _triangulos(c, 0.2, 0.6) == fino                    # sin rehacer, OpenCascade reusa la malla fina
    grueso = _triangulos(c, 0.2, 0.6, rehacer=True)
    assert grueso < fino / 3 and geo.es_valida(c)


def test_deflexion_automatica_sigue_al_tamano_con_topes():
    chica, grande = geo.caja(5, 5, 5, (0, 0, 0)), geo.caja(1000, 1000, 1000, (0, 0, 0))
    assert visor3d.deflexion_automatica(chica) == visor3d.DEFLEXION_MIN
    assert visor3d.deflexion_automatica(grande) == pytest.approx(min(1732.05 * visor3d.FACTOR_DETALLE_AUTO,
                                                                     visor3d.DEFLEXION_MAX), rel=1e-3)
    media = geo.caja(100, 100, 100, (0, 0, 0))
    assert visor3d.deflexion_automatica(media) == pytest.approx(173.205 * visor3d.FACTOR_DETALLE_AUTO, rel=1e-3)


def test_niveles_de_detalle_ordenados():
    c = geo.cilindro(10, 30, (0, 0, 0))
    cuentas = [_triangulos(c, *DETALLES[n], rehacer=True) for n in ("bajo", "medio", "alto")]
    assert cuentas == sorted(cuentas) and cuentas[0] < cuentas[2]


def test_cada_preset_fija_claves_que_existen_en_la_pagina():
    for valores in PRESETS.values():
        assert set(valores) <= set(CLAVES_GRAFICOS)
    assert PRESETS["rendimiento"]["graficos/detalle"] == "bajo" and not PRESETS["rendimiento"]["vista/efecto_aa"]
    assert PRESETS["calidad"]["graficos/detalle"] == "alto" and PRESETS["calidad"]["vista/efecto_sombra_suelo"]


@pytest.fixture
def visor():
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    v = visor3d.Visor3D()
    yield v
    v.deleteLater()


def test_dinamico_apaga_efectos_en_orden_al_navegar_y_vuelve_al_soltar(visor):
    cfg = visor.config
    cfg.efectos = {"cupula": True, "suelo": True, "sombra_suelo": True, "reflejo": True, "aa": True}
    cfg.fps_minimo = 30                          # presupuesto: 33 ms por cuadro
    visor._navegar()
    visor._ms_cuadro = 50                        # cuadros lentos
    visor._ajustar_degradado()
    assert not visor.efectos_visibles()["reflejo"] and visor.efectos_visibles()["suelo"]
    visor._ajustar_degradado()
    visor._ajustar_degradado()
    ef = visor.efectos_visibles()
    assert not (ef["suelo"] or ef["sombra_suelo"] or ef["aa"]) and ef["cupula"]
    visor._ms_cuadro = 5                         # se recupera de a un escalón
    visor._ajustar_degradado()
    assert visor._degradado == 2
    visor._fin_navegacion()
    assert visor._degradado == 0 and visor.efectos_visibles() == cfg.efectos


def test_sin_dinamico_o_sin_navegar_no_se_degrada(visor):
    visor._ms_cuadro = 500
    visor._ajustar_degradado()                   # no se está navegando
    assert visor._degradado == 0
    visor.config.dinamico = False
    visor._navegar()
    visor._ajustar_degradado()
    assert visor._degradado == 0


def test_limite_de_cuadros_junta_los_pedidos(visor):
    import time
    visor.config.limite_fps = 15
    visor._t_cuadro = time.perf_counter()        # recién se dibujó un cuadro
    visor.update()
    visor.update()
    assert visor._t_limite.isActive() and 0 < visor._t_limite.interval() <= 1000 // 15 + 1
    visor.config.limite_fps = 0
    visor._t_limite.stop()
    visor.update()
    assert not visor._t_limite.isActive()


@pytest.fixture
def dialogo(tmp_path):
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    prefs = Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat))
    dlg = DialogoPreferencias(prefs, None, "graficos")
    avisos = []
    dlg.graficos_cambiados.connect(lambda: avisos.append(dict((k, prefs[k]) for k in CLAVES_GRAFICOS)))
    yield dlg, prefs, avisos
    dlg.deleteLater()


def test_elegir_un_preset_pone_sus_valores_y_se_aplica_al_instante(dialogo):
    dlg, prefs, avisos = dialogo
    dlg._poner("graficos/preset", "calidad")
    assert dlg.valores()["graficos/detalle"] == "alto" and dlg.valores()["vista/efecto_suelo"] is True
    assert prefs["graficos/preset"] == "calidad" and prefs["graficos/detalle"] == "alto" and avisos


def test_tocar_un_control_del_preset_pasa_a_personalizar(dialogo):
    dlg, prefs, _ = dialogo
    dlg._poner("graficos/preset", "rendimiento")
    dlg._poner("vista/efecto_aa", True)
    assert dlg.valores()["graficos/preset"] == "personalizar" and prefs["graficos/preset"] == "personalizar"
    dlg._poner("graficos/preset", "rendimiento")
    dlg._poner("graficos/limite_fps", 30)        # el límite de cuadros no es parte del preset
    assert dlg.valores()["graficos/preset"] == "rendimiento" and prefs["graficos/limite_fps"] == 30


def test_cancelar_vuelve_a_lo_que_habia(dialogo):
    dlg, prefs, avisos = dialogo
    antes = {k: prefs[k] for k in CLAVES_GRAFICOS}
    dlg._poner("graficos/preset", "calidad")
    dlg._poner("graficos/fps_minimo", 60)
    dlg.reject()
    QTest.qWait(1)
    assert {k: prefs[k] for k in CLAVES_GRAFICOS} == antes and avisos[-1] == antes

# -*- coding: utf-8 -*-
"""Rendimiento (pendiente 10). Paso 2, Preferencias › Gráficos: detalle de las piezas, «Dinámico», límite de
cuadros, valores predefinidos y su aplicación al instante en el diálogo. Paso 4: mallas en la placa de video una
sola vez, rejilla con numpy y menos detalle a la distancia."""
import os

import numpy as np
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


# ---------------------------------------------------------------- paso 4: mallas en la placa y detalle a la distancia
def test_teselar_aparte_no_toca_la_malla_de_la_forma():
    c = geo.cilindro(10, 30, (0, 0, 0))
    fino = _triangulos(c, 0.01, 0.2, rehacer=True)
    grueso = len(geo.teselar_aparte(c, 0.2, 0.6)[0]) // 3
    assert grueso < fino / 3
    assert _triangulos(c, 0.01, 0.2) == fino and geo.es_valida(c)   # la malla guardada en la forma sigue siendo la fina


def test_nivel_lod_elige_el_mas_grueso_que_no_se_nota():
    assert visor3d.nivel_lod(500, 0.05) == 0                   # se ve grande: malla de siempre
    assert visor3d.nivel_lod(80, 0.05) == 1
    assert visor3d.nivel_lod(20, 0.01) == 2
    assert visor3d.nivel_lod(20, 0.2) == 0                     # chica, pero la malla gruesa erraría 0,8 px
    assert visor3d.nivel_lod([500, 80, 20], [0.05, 0.05, 0.01]).tolist() == [0, 1, 2]


def _rejilla_punto_por_punto(plano, paso, cu, cv, rgb, oscuro, n=40):
    """Lo que hacía `Visor3D._rejilla` antes del paso 4 (glVertex de a uno), como referencia."""
    ext, vert, col = paso * n, [], []
    for i in range(-n, n + 1):
        u, v = cu + i * paso, cv + i * paso
        mayor_u, mayor_v = round(u / paso) % 5 == 0, round(v / paso) % 5 == 0
        for mayor, a, b in ((mayor_u, (u, cv - ext), (u, cv + ext)), (mayor_v, (cu - ext, v), (cu + ext, v))):
            alfa = (0.40 if mayor else 0.16) if oscuro else (0.45 if mayor else 0.22)
            vert += [plano.a_3d(*a), plano.a_3d(*b)]
            col += [(*rgb, alfa)] * 2
    return np.array(vert, np.float32), np.array(col, np.float32)


@pytest.mark.parametrize("plano", [geo.Plano("XY"), geo.Plano.desde_marco((5, -3, 2), (0.3, 0.2, 0.9), (1, 0, 0))])
def test_lineas_rejilla_igual_que_punto_por_punto(plano):
    for paso, cu, cv, oscuro in ((10.0, 50.0, -100.0, True), (0.5, 2.5, 0.0, False)):
        v, c = visor3d.lineas_rejilla(plano, paso, (cu, cv), (0.6, 0.7, 0.8), oscuro)
        v0, c0 = _rejilla_punto_por_punto(plano, paso, cu, cv, (0.6, 0.7, 0.8), oscuro)
        assert v.shape == v0.shape == (2 * 81 * 2, 3) and np.allclose(v, v0, atol=1e-4) and np.allclose(c, c0)


class _GLFalso:
    """Lo justo de OpenGL para probar la caché de búferes sin placa de video."""
    GL_ARRAY_BUFFER, GL_STATIC_DRAW = 1, 2

    def __init__(self):
        self.subidas, self.borrados, self._n = 0, [], 0

    def glGenBuffers(self, _n):
        self._n += 1
        return self._n

    def glBindBuffer(self, *_):
        pass

    def glBufferData(self, *_):
        self.subidas += 1

    def glDeleteBuffers(self, _n, ids):
        self.borrados += list(ids)


def test_buffer_se_sube_una_vez_y_se_libera_cuando_el_array_muere(visor, monkeypatch):
    import gc
    gl = _GLFalso()
    monkeypatch.setattr(visor3d, "GL", gl)
    a, b = np.zeros((30, 3), np.float32), np.ones((30, 3), np.float32)
    ida = visor._buffer_gl(a)
    assert visor._buffer_gl(a) == ida and visor._buffer_gl(b) != ida and gl.subidas == 2
    del a
    gc.collect()
    visor._barrer_buffers()
    assert gl.borrados == [ida] and visor._buffer_gl(b) and gl.subidas == 2


def _estado_cilindro():
    from omnicad.timeline.documento import Documento
    from omnicad.timeline.operaciones import OpPrimitiva
    doc = Documento()
    doc.operaciones = [OpPrimitiva(doc.nuevo_id(), "Pieza", forma="cilindro", radio="10 mm", alto="30 mm", x="0",
                                   y="0", z="0", operacion="nuevo")]
    doc.marcador = 1
    doc.recalcular(0)
    return doc.estado_final


def test_de_lejos_se_dibuja_una_malla_mas_gruesa_y_de_cerca_la_fina(visor):
    visor.resize(800, 600)
    visor.set_modelo(_estado_cilindro())
    fina = len(visor._mallas[0]["v"]) // 3
    visor.encuadrar()
    assert visor.triangulos_dibujados() == fina and not visor._lod_pendientes
    visor.distancia *= 30                                      # la pieza queda de unos 20 px
    assert visor.triangulos_dibujados() == fina and visor._lod_pendientes   # mientras se calcula, la fina
    visor._calcular_lod()
    lejos = visor.triangulos_dibujados()
    assert lejos < fina / 2 and not visor._lod_pendientes
    visor.config.detalle_distancia = False
    assert visor.triangulos_dibujados() == fina
    visor.config.detalle_distancia = True
    visor.transformaciones = {visor._mallas[0]["id"]: np.identity(4)}   # animada: siempre la fina
    assert visor.triangulos_dibujados() == fina
    visor.transformaciones = {}
    visor.encuadrar()
    assert visor.triangulos_dibujados() == fina


def test_el_lienzo_de_render_sin_glsl_dibuja_como_el_visor(monkeypatch):
    """Visor3D.paintGL llamaba a `_pintar`, que LienzoRender redefine con otra firma: sin GLSL fallaba."""
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    from omnicad.ui.render import LienzoRender
    llamadas = []
    monkeypatch.setattr(visor3d.Visor3D, "_pintar_vista", lambda self, cfg: llamadas.append(cfg))
    lz = LienzoRender()
    lz._gl = None                                              # sin GLSL: cae al dibujo del Visor3D
    lz.paintGL()
    assert llamadas == [lz.config]
    lz.deleteLater()


def test_arrancar_no_importa_scipy():
    """Paso 5 (arranque rápido): scipy cuesta ~0,4 s y ~47 MB; se carga recién al usar una malla o el solver."""
    import subprocess
    import sys
    from pathlib import Path
    codigo = ("import sys; import OmniCAD, omnicad.ui.ventana; OmniCAD._verificar_dependencias(); "
              "print(sorted(m for m in sys.modules if m.split('.')[0] == 'scipy'))")
    salida = subprocess.run([sys.executable, "-c", codigo], capture_output=True, text=True, timeout=120,
                            cwd=Path(__file__).resolve().parents[1])
    assert salida.returncode == 0, salida.stderr
    assert salida.stdout.strip().splitlines()[-1] == "[]"


def test_la_malla_carga_scipy_al_usarla():
    from omnicad.nucleo import malla
    m = malla.Malla(np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]], float),
                    np.array([[0, 2, 1], [0, 1, 3], [0, 3, 2], [1, 2, 3]]))
    assert len(malla.generar_grupos(m, angulo=10).caras) == 4      # usa scipy adentro, importado al vuelo

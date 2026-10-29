"""P-45: las vistas (ViewCube, Ajustar, mirar al boceto) se animan ~250 ms; solo las órdenes del usuario y solo con la
preferencia; cualquier orbitar, desplazar, zoom o clic las corta sin saltos; las pruebas y la API siguen al instante."""
import numpy as np
import pytest
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from omnicad.nucleo import animacion
from omnicad.timeline.documento import Documento
from omnicad.timeline.operaciones import OpPrimitiva
from omnicad.ui import visor3d as vis


@pytest.fixture
def visor(monkeypatch):
    monkeypatch.delenv("OMNICAD_SIN_ANIMACION", raising=False)
    app = QApplication.instance() or QApplication([])
    d = Documento()
    d.agregar(OpPrimitiva(d.nuevo_id(), forma="caja", ancho="40", largo="30", alto="20"))
    v = vis.Visor3D()
    v.resize(640, 480)
    v.show()
    v.set_modelo(d.estado_final)
    v.config.animar_vistas = True
    QTest.qWait(50)
    yield v
    v.close()
    v.deleteLater()
    app.processEvents()


def instantaneo(visor, cambio):
    """Cámara a la que llega `cambio` de golpe, sin animar."""
    antes = visor._camara()
    visor.config.animar_vistas = False
    cambio()
    destino = visor._camara()
    visor.config.animar_vistas = True
    visor._poner_camara(antes)
    return destino


def test_la_vista_se_anima_y_llega_exactamente_al_mismo_destino(visor):
    destino = instantaneo(visor, lambda: visor.vista("frente"))
    inicio = visor._camara()
    visor.animar_vista(lambda: visor.vista("frente"))
    assert visor._animacion is not None and visor._camara() == inicio     # arranca donde estaba
    QTest.qWait(120)
    medio = visor._camara()
    assert medio != inicio and medio != destino                          # a mitad de camino
    assert np.allclose(np.linalg.det(medio["R"]), 1) and np.allclose(np.array(medio["R"]) @ np.array(medio["R"]).T, np.eye(3))
    QTest.qWait(250)
    assert visor._animacion is None and not visor._t_animacion.isActive()
    final = visor._camara()
    assert np.allclose(final["R"], destino["R"]) and np.allclose(final["objetivo"], destino["objetivo"])
    assert final["distancia"] == pytest.approx(destino["distancia"])


def test_los_pasos_siguen_la_interpolacion_suavizada_de_la_camara(visor):
    destino = instantaneo(visor, lambda: visor.vista("izquierda"))
    inicio = visor._camara()
    visor.animar_vista(lambda: visor.vista("izquierda"))
    c0, c1, _, t0 = visor._animacion
    esperado = animacion.interpolar_camara(c0, c1, animacion.suavizado(0.5))
    visor._animacion = (c0, c1, visor._animacion[2], t0 - visor.DURACION_VISTA_S / 2)     # va por la mitad del tiempo
    visor._paso_animacion()
    actual = visor._camara()
    assert np.allclose(actual["R"], esperado["R"], atol=0.05) and np.allclose(actual["objetivo"], esperado["objetivo"], atol=2)
    assert inicio["R"] != destino["R"]


@pytest.mark.parametrize("orden", ["orbitar", "desplazar", "acercar", "clic"])
def test_una_orden_del_usuario_corta_la_transicion_sin_saltos(visor, orden):
    from PySide6.QtCore import QEvent, QPointF, Qt
    from PySide6.QtGui import QMouseEvent
    visor.animar_vista(lambda: visor.vista("derecha"))
    QTest.qWait(100)
    visor._t_animacion.stop()
    antes = visor._camara()
    if orden == "orbitar":
        visor.orbitar(1, 0)
    elif orden == "desplazar":
        visor.desplazar(1, 0)
    elif orden == "acercar":
        visor.acercar(1)
    else:
        QApplication.sendEvent(visor, QMouseEvent(QEvent.MouseButtonPress, QPointF(50, 50), visor.mapToGlobal(QPointF(50, 50)),
                                                  Qt.MiddleButton, Qt.MiddleButton, Qt.NoModifier))
    assert visor._animacion is None and not visor._t_animacion.isActive()
    despues = visor._camara()
    assert np.allclose(despues["R"], antes["R"], atol=0.02) and np.allclose(despues["objetivo"], antes["objetivo"], atol=2)
    QTest.qWait(300)
    assert visor._camara()["R"] == despues["R"]      # no sigue hacia el destino


def test_sin_la_preferencia_la_vista_es_instantanea(visor):
    destino = instantaneo(visor, lambda: visor.vista("arriba"))
    visor.config.animar_vistas = False
    visor.animar_vista(lambda: visor.vista("arriba"))
    assert visor._animacion is None and visor._camara() == destino


def test_las_pruebas_y_la_api_no_animan_aunque_la_preferencia_este_activa(visor, monkeypatch):
    monkeypatch.setenv("OMNICAD_SIN_ANIMACION", "1")
    destino = instantaneo(visor, lambda: visor.vista("izquierda"))
    visor.animar_vista(lambda: visor.vista("izquierda"))
    assert visor._animacion is None and visor._camara() == destino
    c0 = visor._camara()
    visor.vista("atras")             # las llamadas directas (herramientas de la API, capturas) nunca animan
    assert visor._animacion is None and visor._camara() != c0


def test_terminar_la_animacion_llega_al_destino_para_las_capturas(visor):
    destino = instantaneo(visor, lambda: visor.vista("abajo"))
    visor.animar_vista(lambda: visor.vista("abajo"))
    assert visor._animacion is not None
    visor.terminar_animacion()
    assert visor._animacion is None and visor._camara() == destino
    visor.terminar_animacion()          # sin transición no hace nada


def test_una_vista_igual_a_la_actual_no_anima(visor):
    visor.animar_vista(lambda: visor.vista("frente"))
    visor.terminar_animacion()
    visor.animar_vista(lambda: visor.vista("frente"))
    assert visor._animacion is None


def test_la_preferencia_existe_y_esta_activa_por_defecto(tmp_path):
    from PySide6.QtCore import QSettings
    from omnicad.ui.preferencias import Preferencias
    p = Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat))
    assert p["general/animar_vistas"] is True

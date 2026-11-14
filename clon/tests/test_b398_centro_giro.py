"""B-398: la órbita gira alrededor del centro de lo que se ve (o del origen si no hay nada), no del objetivo de la cámara:
desplazar o acercar hacia el cursor corren el objetivo y la cruz de órbita quedaba en un punto vacío."""
import numpy as np
import pytest
from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QApplication

from omnicad.timeline.documento import Documento
from omnicad.timeline.operaciones import OpPrimitiva
from omnicad.ui import visor3d as vis


@pytest.fixture
def visor():
    QApplication.instance() or QApplication([])
    v = vis.Visor3D()
    v.resize(800, 600)
    yield v
    v.deleteLater()


def _con_caja(v, x=50.0):
    d = Documento()
    d.agregar(OpPrimitiva(d.nuevo_id(), forma="caja", ancho="40", largo="30", alto="20"))
    v.set_modelo(d.estado_final)
    original = v.centro_giro()
    v._mallas = [dict(m, v=m["v"] + np.array([x, 0, 0], np.float32)) for m in v._mallas]      # corrida: su centro deja de ser el origen
    v._caja_cache = (None, None, None)
    v.encuadrar()
    return original + np.array([x, 0, 0])


def _px(v, p):
    q = v.proyectar(p)
    return np.array([q.x(), q.y()])


def test_sin_nada_el_centro_de_giro_es_el_origen_y_la_cruz_esta_ahi(visor):
    assert np.allclose(visor.centro_giro(), 0)
    punto = visor.primitivas_centro_giro()[1][1]
    assert np.allclose(punto, [[0, 0, 0]])


def test_tras_desplazar_y_acercar_la_orbita_sigue_en_el_origen(visor):
    visor.vista("iso")
    visor.desplazar(60, -25)
    visor.acercar(3, QPointF(120, 90))                       # el objetivo se corre hacia el cursor
    assert not np.allclose(visor.objetivo, 0)
    antes = _px(visor, [0, 0, 0])
    for dx, dy in ((30, 5), (-12, 20), (40, -35)):
        visor.orbitar(dx, dy)
        assert np.allclose(_px(visor, [0, 0, 0]), antes, atol=1e-6), "el origen se movió en la pantalla al orbitar"
    assert np.allclose(visor.centro_giro(), 0)


@pytest.mark.parametrize("tipo", ["libre", "restringida"])
def test_con_geometria_gira_alrededor_del_centro_de_su_caja(visor, tipo):
    visor.config.tipo_orbita = tipo
    esperado = _con_caja(visor)
    centro = visor.centro_giro()
    assert np.allclose(centro, esperado, atol=1e-3) and abs(centro[0]) > 40      # el centro de la caja, no el origen
    visor.desplazar(40, 10)
    antes = _px(visor, centro)
    visor.orbitar(25, -15)
    visor.orbitar(-5, 30)
    assert np.allclose(_px(visor, centro), antes, atol=1e-6)


def test_ajustar_y_home_recentran_el_objetivo(visor):
    visor.desplazar(80, 40)
    visor.acercar(2, QPointF(10, 10))
    visor.encuadrar()                                        # Ajustar
    assert np.allclose(visor.objetivo, 0)
    visor.desplazar(80, 40)
    visor.vista("iso")                                       # Home (la casita del ViewCube)
    assert np.allclose(visor.objetivo, 0)
    _con_caja(visor)
    visor.desplazar(80, 40)
    visor.vista("iso")
    assert np.allclose(visor.objetivo, visor.centro_giro(), atol=1e-6)

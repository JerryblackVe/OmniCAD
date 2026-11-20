"""B-763/B-775: la rueda acerca hacia el cursor 1,111× fijo por muesca, sin aceleración, como Fusion (B-775). B-764: la rejilla del diseño es
finita (crece con el modelo, también ya modificado) y se desvanece hacia el borde y al mirarla rasante."""
import math

import numpy as np
import pytest
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QApplication

from omnicad.nucleo import geometria as g
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


def _rueda(v, muescas, pos):
    QApplication.sendEvent(v, QWheelEvent(QPointF(pos), QPointF(v.mapToGlobal(pos)), QPoint(), QPoint(0, 120 * muescas),
                                          Qt.NoButton, Qt.NoModifier, Qt.ScrollUpdate, False))


def test_muescas_acercan_fijo_1_111_sin_aceleracion(visor):
    """E11 con mouse real en Fusion: 3 muescas → 1,37×, 4 → 1,52×, 10 → 2,87× (1,111 por muesca, sin aceleración)."""
    visor.config.invertir_zoom = False
    cursor = QPoint(600, 150)
    antes = visor.punto_focal(QPointF(cursor))
    d0 = visor.distancia
    for n, esperado in ((3, 1.37), (4, 1.52), (10, 2.87)):
        visor.distancia = d0
        for _ in range(n):
            _rueda(visor, 1, cursor)
        assert d0 / visor.distancia == pytest.approx(esperado, rel=0.01)
        if n == 3:
            assert np.allclose(visor.punto_focal(QPointF(cursor)), antes, atol=1e-6 * d0)   # lo de bajo el cursor queda ahí
    visor.distancia = d0
    _rueda(visor, -1, cursor)
    assert visor.distancia / d0 == pytest.approx(1 / 0.9, rel=1e-6)    # alejar es la inversa


def test_arrastre_de_zoom_no_cambia_de_velocidad(visor):
    """Solo cambia la rueda: el zoom arrastrando sigue en 0,88 cada 30 px."""
    d0 = visor.distancia
    visor.acercar(-300 / vis.PX_ZOOM_ARRASTRE)
    assert visor.distancia / d0 == pytest.approx(0.88 ** -10, rel=1e-6)


def test_rejilla_finita_corta_las_lineas_en_el_limite():
    vert, col = vis.lineas_rejilla(g.Plano("XY"), 10.0, (0.0, 0.0), (0.5, 0.5, 0.5), False, n=40, cada=5, limite=100.0)
    assert np.abs(vert[:, :2]).max() == pytest.approx(100.0)        # sin límite llegaba a 400
    sin = vis.lineas_rejilla(g.Plano("XY"), 10.0, (0.0, 0.0), (0.5, 0.5, 0.5), False, n=40, cada=5)[0]
    assert np.abs(sin[:, :2]).max() == pytest.approx(400.0)
    lejos = vis.lineas_rejilla(g.Plano("XY"), 10.0, (900.0, 0.0), (0.5, 0.5, 0.5), False, n=40, cada=5, limite=100.0)
    assert len(lejos[0]) == 0                                        # mirando fuera de la rejilla no se dibuja nada


def test_rejilla_se_desvanece_hacia_el_borde():
    vert, col = vis.lineas_rejilla(g.Plano("XY"), 10.0, (0.0, 0.0), (0.5, 0.5, 0.5), True, n=40, cada=5)
    r = np.hypot(vert[:, 0], vert[:, 1])
    assert col[r < 100, 3].min() > 0.15 and col[r >= 400 * 0.999, 3].max() == 0.0


def test_limite_crece_con_el_modelo_ya_modificado(visor):
    paso = visor.paso_rejilla()
    vacio = visor.limite_rejilla(paso)
    assert vacio >= vis.REJILLA_MEDIO_LADO_MIN
    d = Documento()
    op = OpPrimitiva(d.nuevo_id(), forma="caja", ancho="40", largo="30", alto="20")
    d.agregar(op)
    visor.set_modelo(d.estado_final)
    op.p["ancho"] = "900"                                            # el cuerpo ya creado cambia de tamaño
    d.recalcular()
    visor.set_modelo(d.estado_final)
    grande = visor.limite_rejilla(paso)
    modelo = max(np.abs(visor._caja_escena()[0]).max(), np.abs(visor._caja_escena()[1]).max())
    assert modelo >= 450 and grande >= vis.REJILLA_POR_MODELO * modelo - 1e-6 and grande > vacio
    mayor = paso * visor.subdivisiones_rejilla()
    assert math.isclose(grande / mayor, round(grande / mayor))        # el borde cae en una línea mayor


def test_rasante_apaga_la_rejilla(visor):
    xy = g.Plano("XY")
    visor.elevacion = 45.0
    assert visor.opacidad_rasante(xy) == 1.0
    visor.elevacion = 1.0                                            # casi de canto: antes moiré hasta el horizonte
    assert visor.opacidad_rasante(xy) < 0.1

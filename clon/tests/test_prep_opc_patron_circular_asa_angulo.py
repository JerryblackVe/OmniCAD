# -*- coding: utf-8 -*-
"""PREP: asas del «Patrón circular» del boceto (ui/patron_boceto.py › `ControlPatron._asas_circular`).

Cubre la fila «Asa de ángulo total / paso y cantidad» de
`docs/seguimiento/preparado/opciones_asas_boceto.md`: el asa de ángulo total escribe «Ángulo total» (y se pega a
±360° al acercarse a la vuelta entera), y el asa de cantidad suma o quita copias de a un paso (`angulo_total / (n − 1)`
en ángulo parcial) sin bajar de 2 (Fusion: Angle/Quantity manipulator handles del patrón circular).
"""
import math
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, QPointF, Qt  # noqa: E402
from PySide6.QtGui import QMouseEvent  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from omnicad.restricciones import Boceto  # noqa: E402
from omnicad.timeline.parametros import TablaParametros  # noqa: E402
from omnicad.ui import editor_boceto  # noqa: E402


@pytest.fixture(scope="module")
def app_qt():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def lienzo(app_qt):
    lz = editor_boceto.Lienzo(Boceto(), TablaParametros().evaluar)
    lz.resize(800, 600)
    lz.ajustar_grilla = False
    lz.show()
    yield lz
    lz.close()
    lz.deleteLater()
    app_qt.processEvents()


def _raton(lz, tipo, xy, botones=Qt.LeftButton):
    q = lz.a_px(*xy) if not isinstance(xy, QPointF) else xy
    boton = Qt.LeftButton if tipo != QEvent.MouseMove else Qt.NoButton
    QApplication.sendEvent(lz, QMouseEvent(tipo, q, lz.mapToGlobal(q), boton,
                                           botones if tipo != QEvent.MouseButtonRelease else Qt.NoButton, Qt.NoModifier))


def arrastrar(lz, desde, hasta):
    """Press en `desde` (mm), mueve en tramos y suelta en `hasta` (mm)."""
    _raton(lz, QEvent.MouseButtonPress, desde)
    for k in range(1, 7):
        _raton(lz, QEvent.MouseMove, (desde[0] + (hasta[0] - desde[0]) * k / 6,
                                      desde[1] + (hasta[1] - desde[1]) * k / 6), Qt.LeftButton)
    _raton(lz, QEvent.MouseButtonRelease, hasta)


def posicion(lz, i):
    return lz._asas.asas[i].posicion(lz._asas.valores())


def sobre_el_centro(grados, radio=25.0):
    a = math.radians(grados)
    return (radio * math.cos(a), radio * math.sin(a))


def abrir(lz):
    """Abre «Patrón circular» con su panel, un círculo a 25 mm del origen (el centro) y 4 copias en 90°."""
    from omnicad.ui.panel_patron import PanelPatron
    c = lz.b.agregar_circulo((25, 0), 3)
    panel = lz._panel_prueba = PanelPatron()
    ctl = lz.patron
    ctl.panel = panel
    panel.cambio.connect(ctl.recibir)
    panel.aceptado.connect(ctl.aceptar)
    panel.cancelado.connect(ctl.cancelar)
    lz.seleccion = [c]
    lz.set_herramienta("patron_circular")
    ctl.centro = (0.0, 0.0)                          # el origen: las asas giran alrededor de él
    panel.combos["distribucion"].setCurrentIndex(panel.combos["distribucion"].findData("parcial"))
    panel.campos["cantidad"].setText("4")
    panel.campos["angulo_total"].setText("90")
    lz.encuadrar()
    QApplication.processEvents()
    return panel


def test_prep_asa_de_angulo_total_escribe_el_valor_y_se_pega_a_360(lienzo):
    """Fusion: arrastrar el asa de Angle fija el ángulo total; cerca de la vuelta entera cae en 360°, no en 358°."""
    lz = lienzo
    panel = abrir(lz)
    assert len(lz._asas.asas) == 2                       # ángulo total y cantidad
    assert posicion(lz, 0) == pytest.approx(sobre_el_centro(90), abs=1e-6)
    arrastrar(lz, posicion(lz, 0), sobre_el_centro(180))
    assert float(panel.campos["angulo_total"].text()) == pytest.approx(180, abs=1.0)
    arrastrar(lz, posicion(lz, 0), sobre_el_centro(358))
    assert float(panel.campos["angulo_total"].text()) == pytest.approx(360, abs=1e-6)   # 358° se pega a 360°
    assert float(panel.campos["angulo_total"].text()) <= 360.0                        # el asa no pasa de una vuelta
    lz.patron.cancelar()


def test_prep_asa_de_cantidad_suma_por_paso_y_frena_en_dos(lienzo):
    """Fusion: arrastrar el asa de Quantity suma copias de a un paso (90° / 3 = 30°) y no baja de 2."""
    lz = lienzo
    panel = abrir(lz)
    cantidad = panel.campos["cantidad"]
    assert int(cantidad.text()) == 4
    r = math.dist((0.0, 0.0), posicion(lz, 1))           # la cantidad va un poco más afuera que el ángulo
    arrastrar(lz, posicion(lz, 1), sobre_el_centro(120, r))     # un paso de 30° más allá de la última copia
    assert int(cantidad.text()) == 5
    arrastrar(lz, posicion(lz, 1), sobre_el_centro(0, r))       # muchos pasos atrás: frena en el mínimo
    assert int(cantidad.text()) == 2
    lz.patron.cancelar()

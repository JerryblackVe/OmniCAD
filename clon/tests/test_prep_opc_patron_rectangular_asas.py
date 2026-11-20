# -*- coding: utf-8 -*-
"""PREP: asas del «Patrón rectangular» del boceto (ui/patron_boceto.py › `ControlPatron._asas_rectangular`).

Cubre la fila «Asa de distancia y cantidad por dirección; giro sin línea» de
`docs/seguimiento/preparado/opciones_asas_boceto.md`: con dos direcciones y sin líneas de dirección hay un asa de
distancia, una de cantidad y una de giro por dirección; el giro escribe «Ángulo k» sin saltar al cruzar ±180°, y al
elegir una línea de dirección su asa de giro desaparece (Fusion: Distance/Quantity manipulator handle + Direction).
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


def abrir(lz):
    """Abre «Patrón rectangular» con su panel (sin mostrarlo) y un círculo elegido en el origen."""
    from omnicad.ui.panel_patron import PanelPatron
    c = lz.b.agregar_circulo((0, 0), 3)
    panel = lz._panel_prueba = PanelPatron()
    ctl = lz.patron
    ctl.panel = panel
    panel.cambio.connect(ctl.recibir)
    panel.aceptado.connect(ctl.aceptar)
    panel.cancelado.connect(ctl.cancelar)
    lz.seleccion = [c]
    lz.set_herramienta("patron_rectangular")
    panel.casillas["dos"].setChecked(True)              # dos direcciones: un juego de asas por dirección
    panel.campos["cantidad1"].setText("3")
    panel.campos["distancia1"].setText("20")
    panel.campos["cantidad2"].setText("2")
    panel.campos["distancia2"].setText("15")
    lz.encuadrar()
    QApplication.processEvents()
    return panel


def test_prep_asas_de_distancia_y_cantidad_por_direccion(lienzo):
    """Fusion: arrastrar el asa de Distance fija la última copia (Extensión) y la de Quantity suma copias por paso."""
    lz = lienzo
    panel = abrir(lz)
    assert len(lz._asas.asas) == 6                       # distancia y cantidad de cada dirección + dos giros sin línea
    assert posicion(lz, 0) == pytest.approx((20, 0), abs=1e-6)      # distancia 1: última copia a 20 mm
    assert posicion(lz, 2) == pytest.approx((0, 15), abs=1e-6)      # distancia 2: ángulo 2 por defecto = 90°
    arrastrar(lz, posicion(lz, 2), (0, 25))
    assert float(panel.campos["distancia2"].text()) == pytest.approx(25, abs=0.3)
    paso1 = float(panel.campos["distancia1"].text()) / (int(panel.campos["cantidad1"].text()) - 1)
    arrastrar(lz, posicion(lz, 1), (posicion(lz, 1)[0] + 2 * paso1, posicion(lz, 1)[1]))
    assert int(panel.campos["cantidad1"].text()) == 5    # la cantidad 1 sube de a una copia por paso
    arrastrar(lz, posicion(lz, 3), (25, posicion(lz, 3)[1] + 2 * 25))
    assert int(panel.campos["cantidad2"].text()) == 4    # lo mismo en la dirección 2, con su propio paso (distancia 2)
    lz.patron.cancelar()


def test_prep_giro_sin_linea_cruza_180_sin_saltar_y_desaparece_con_linea(lienzo):
    """El asa de giro escribe «Ángulo 1» sin saltar al cruzar ±180°; con una línea de dirección ya no hay giro."""
    lz = lienzo
    panel = abrir(lz)
    panel.campos["angulo1"].setText("170")
    gestor = lz._asas
    centro = gestor.asas[4].ancla(None)                 # las dos últimas asas son los giros (sin línea de dirección)
    radio = math.dist(posicion(lz, 4), centro)
    arrastrar(lz, posicion(lz, 4), (centro[0] + radio * math.cos(math.radians(190)),
                                    centro[1] + radio * math.sin(math.radians(190))))
    assert float(panel.campos["angulo1"].text()) == pytest.approx(190, abs=1.0)   # 190, no -170
    assert lz._asas is gestor                            # girar no rearma las asas a mitad del arrastre
    linea = lz.b.agregar_linea((0, 0), (1, 1))
    lz.patron.lineas["dir1"] = linea
    lz.patron._emitir()
    assert len(lz._asas.asas) == 5                       # la dirección 1 con línea pierde su asa de giro
    assert all(asa.ayuda != "Ángulo" or asa.campo != 6 for asa in lz._asas.asas)
    lz.patron.cancelar()

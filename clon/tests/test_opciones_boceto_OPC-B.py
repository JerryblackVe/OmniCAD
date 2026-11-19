# -*- coding: utf-8 -*-
"""Proyectar de la paleta del boceto (clave `sk_proyectar`, Fusion: Project): el clic en una cara del modelo suma la
referencia a la tarjeta sin tocar el boceto y Aceptar la proyecta en forma ORTOGONAL sobre el plano del boceto."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPointF  # noqa: E402
from PySide6.QtWidgets import QApplication, QWidget  # noqa: E402

from omnicad.nucleo import geometria as geo  # noqa: E402
from omnicad.restricciones import Boceto  # noqa: E402
from omnicad.timeline.parametros import TablaParametros  # noqa: E402
from omnicad.ui import editor_boceto, modo_boceto  # noqa: E402


@pytest.fixture
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def lienzo(app):
    lz = editor_boceto.Lienzo(Boceto(), TablaParametros().evaluar, plano=geo.Plano("XZ"))
    lz.resize(800, 600)
    lz.ajustar_grilla = False
    lz.show()
    yield lz
    lz.close()
    lz.deleteLater()
    app.processEvents()


class _Visor:
    """Lo mínimo de la vista 3D que usa el clic de Proyectar: siempre devuelve la misma referencia."""

    def __init__(self, info):
        self.info = info

    def mapFromGlobal(self, punto):
        return punto

    def elegir_entidad(self, _punto, _tipos):
        return self.info


def test_paleta_proyectar_cara_ortogonal_sobre_el_plano(lienzo):
    lz = lienzo
    ventana = QWidget()
    modo = modo_boceto.ModoBoceto(ventana)
    modo.lienzo = lz
    accion = modo.acciones["sk_proyectar"]                     # la fila «Proyectar» de la paleta
    accion.setEnabled(True)
    accion.trigger()
    assert lz.herramienta == "proyectar"

    forma = geo.caja(20, 10, 10, (0, 50, 0))                   # la caja arranca a 50 mm del plano XZ
    cara = next(c for c in geo.caras(forma) if geo.plano_de_cara(c).normal[1] > 0.99)
    lz.visor = _Visor({"tipo": "cara", "forma": cara})
    lz._clic_proyectar(QPointF(10, 10))                        # el clic solo suma a la tarjeta
    assert len(lz.b.curvas) == 0 and not lz.b.proyecciones     # el boceto todavía no cambió
    estado = lz.estado_proyeccion()
    assert estado["valido"] and len(estado["elegidos"]) == 1 and len(estado["prims"]) == 4

    assert lz.aceptar_proyeccion()
    assert lz.herramienta == "seleccionar" and len(lz.historial) == 1
    assert len(lz.b.curvas) == 4 and all(c.proyectada for c in lz.b.curvas.values())
    puntos = [lz.b.coords(p) for c in lz.b.curvas.values() for p in c.puntos()]
    xs, ys = [p[0] for p in puntos], [p[1] for p in puntos]
    # La proyección es ortogonal: los 50 mm de distancia al plano no cambian nada; queda el rectángulo 20 × 10.
    assert (min(xs), max(xs), min(ys), max(ys)) == pytest.approx((0, 20, 0, 10))
    ventana.deleteLater()

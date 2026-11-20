# -*- coding: utf-8 -*-
"""Proyectar (paleta): proyección ortogonal de una cara, también en el límite coplanar.

Fusion, «Project geometry onto a sketch plane»: la cara elegida se proyecta sobre el plano del boceto
(docs/fusion_docs/contenido/fusion-sketch/project-geometry-onto-a-sketch-plane-c6739f5631a.md).
"""
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
def lienzo():
    app = QApplication.instance() or QApplication([])
    ventana = QWidget()
    modo = modo_boceto.ModoBoceto(ventana)
    lz = editor_boceto.Lienzo(Boceto(), TablaParametros().evaluar, plano=geo.Plano("XZ"))
    modo.lienzo = lz
    lz.resize(800, 600)
    lz.ajustar_grilla = False
    lz.show()
    yield lz, modo
    lz.close()
    lz.deleteLater()
    ventana.deleteLater()
    app.processEvents()


class _Visor:
    """La vista mínima para que el clic de Proyectar devuelva la cara elegida."""

    def __init__(self, cara):
        self.cara = cara

    def mapFromGlobal(self, punto):
        return punto

    def elegir_entidad(self, _punto, tipos):
        assert "cara" in tipos
        return {"tipo": "cara", "forma": self.cara}


@pytest.mark.parametrize(("distancia", "normal_y"), [(60.0, 1.0), (0.0, -1.0)],
                         ids=["cara_alejada_60_mm", "borde_cara_coplanar"])
def test_proyectar_cara_conserva_30_por_15_mm_en_el_plano(lienzo, distancia, normal_y):
    lz, modo = lienzo
    accion = modo.acciones["sk_proyectar"]
    accion.setEnabled(True)
    accion.trigger()
    assert lz.herramienta == "proyectar"

    forma = geo.caja(30, 15, 15, (0, distancia, 0))
    cara = next(c for c in geo.caras(forma) if geo.plano_de_cara(c).normal[1] * normal_y > 0.99)
    lz.visor = _Visor(cara)
    lz._clic_proyectar(QPointF(10, 10))
    assert not lz.b.curvas and not lz.b.proyecciones       # el clic solo prepara la vista previa
    estado = lz.estado_proyeccion()
    assert estado["valido"] and len(estado["prims"]) == 4

    assert lz.aceptar_proyeccion()
    assert len(lz.b.curvas) == 4 and all(c.proyectada for c in lz.b.curvas.values())
    puntos = {lz.b.coords(p) for c in lz.b.curvas.values() for p in c.puntos()}
    xs, ys = [p[0] for p in puntos], [p[1] for p in puntos]
    assert (min(xs), max(xs), min(ys), max(ys)) == pytest.approx((0, 30, 0, 15))
    assert lz.herramienta == "seleccionar" and len(lz.historial) == 1

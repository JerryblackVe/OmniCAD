"""B-626 (reabierto): al abrir una herramienta salen solos los 3 planos de origen, grandes, y tapan la pieza.

En Fusion los planos de origen tienen un interruptor Hidden/Visible explícito y no aparecen solos al abrir
un comando; cuando un comando pide un plano (p. ej. Create Sketch) las opciones son planos de origen, planos
de trabajo y caras planas de la geometría. El crecimiento se reserva al modo ``elegir_plano`` (pedir un plano
de boceto); ver ``test_b610_planos_con_cuerpo_encima.py``.
"""
import os

import pytest

from omnicad.nucleo import geometria as g


@pytest.fixture(scope="module")
def visor():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    from omnicad.timeline.operaciones import EstadoModelo
    from omnicad.ui.visor3d import Visor3D

    QApplication.instance() or QApplication([])
    estado = EstadoModelo()
    estado.nuevo_cuerpo("op1", g.caja(40, 40, 40, origen=(-20, -20, -20)))   # cuerpo que tapa el origen
    v = Visor3D()
    v.resize(800, 600)
    v.set_modelo(estado)
    v.vista("iso")
    v.set_ortografica(True)
    v.ventana_libre = False          # hay un comando abierto (p. ej. Extrusión delgada)
    yield v
    v.set_filtro(None)
    v.close()


def test_b626_planos_origen_no_tapan_la_pieza_al_abrir_herramienta(visor):
    """B-626: con un cuerpo en la escena y un comando abierto, los planos de origen no deben crecerse
    hasta cubrir la pieza (en Fusion no aparecen solos al abrir una herramienta)."""
    visor.set_filtro({"plano"})
    try:
        rects = {r: rect for r, _pl, rect in visor.planos_elegibles()}
        for r in ("XY", "XZ", "YZ"):
            u0, v0, u1, v1 = rects[r]
            # la pieza va de -20 a 20 en los dos ejes del plano: cubrirla sería abarcar ese rango
            tapa = u0 <= -20 and v0 <= -20 and u1 >= 20 and v1 >= 20
            assert not tapa, f"el plano {r} tapa la pieza: {rects[r]}"
    finally:
        visor.set_filtro(None)

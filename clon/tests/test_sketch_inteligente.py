"""Sketch inteligente: ayudas de dibujo (inferencias, alineaciones, capturas) y restricciones que dejan al confirmar."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from test_boceto_fase5_ui import _clic, _mover  # noqa: E402
from test_boceto_fase5_ui import lienzo as lienzo  # noqa: E402,F401


def test_geometria_oculta_no_atrae_el_cursor(lienzo):
    """Una construcción oculta no se ve: tampoco puede capturar el cursor (ni su punto medio ni sus extremos)."""
    lz = lienzo
    lz.b.agregar_linea((30, 30), (70, 30), True)          # construcción
    lz.resolver()
    lz.mostrar["construccion"] = False
    lz.set_herramienta("linea")
    _mover(lz, 50.1, 30.1)                            # sobre su punto medio
    assert lz.inf_actual is None
    _mover(lz, 30.1, 30.1)                            # sobre su extremo
    assert lz.cursor == pytest.approx((30.1, 30.1), abs=1e-6)

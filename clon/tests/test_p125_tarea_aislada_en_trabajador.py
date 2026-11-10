# -*- coding: utf-8 -*-
"""P-125: las tareas aisladas con forma (el chequeo de autointersección de cada empalme o chaflán con caras B-spline)
van al trabajador que ya está vivo. Antes cada una arrancaba un proceso nuevo: ~0,9 s por clic en una arista de un
barrido, cuando el análisis tarda ~50 ms."""
import pytest

from omnicad.nucleo import aislado, motor, revision
from omnicad.nucleo import geometria as geo


@pytest.fixture(autouse=True)
def opencascade():
    with motor.fijar_motor("opencascade"):
        yield


def test_la_tarea_con_forma_no_arranca_un_proceso_nuevo(monkeypatch):
    caja = geo.caja(10, 20, 30)
    monkeypatch.setattr(aislado, "_ejecutar", lambda *a, **k: pytest.fail("arrancó un proceso de una sola tarea"))
    for _ in range(2):
        assert aislado.correr("autointersecciones", caja, 60, limite=1) == [0, [], True]
    assert revision._autointersecciones(caja, 1) == (0, [], True)


def test_con_el_trabajador_ocupado_va_a_un_proceso_aparte():
    caja = geo.caja(10, 20, 30)
    with aislado._ocupado:                        # otra previa lo está usando
        assert aislado.correr("autointersecciones", caja, 60, limite=1) == [0, [], True]

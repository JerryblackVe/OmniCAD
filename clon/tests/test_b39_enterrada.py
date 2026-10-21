# -*- coding: utf-8 -*-
"""B-39: unir una herramienta 100 % enterrada en la pared de una carcasa no suma volumen y no deja aristas libres.

El caso original (cilindro r2,5 en la carcasa del motor, arista libre en (27, 0, 129,5)) no se pudo reproducir
con ningún modelo guardado ni con este montaje; el test fija el comportamiento correcto para que una regresión se vea."""
import pytest

from omnicad.nucleo import geometria as geo
from omnicad.nucleo import revision as rv


@pytest.mark.parametrize("x0, largo", [(27.0, 2.0), (27.0, 2.5), (27.2, 2.3)])
def test_b39_herramienta_enterrada_en_la_pared_no_suma_ni_deja_aristas_libres(x0, largo):
    pared = geo.booleano(geo.cilindro(30, 140, (0, 0, 0)), geo.cilindro(27, 140, (0, 0, 0)), "cortar")
    herramienta = geo.cilindro(2.5, largo, (x0, 0, 129.5), eje=(1, 0, 0))      # apoyada tangente a la cara interior
    unida = geo.booleano(pared, herramienta, "unir")
    informe = rv.revisar(unida, autointersecciones=False)
    assert geo.volumen(unida) == pytest.approx(geo.volumen(pared), abs=1e-6)
    assert geo.es_valida(unida) and rv.es_estanca(unida) and len(geo.solidos(unida)) == 1
    assert informe["aristas_libres"] == 0 and informe["aristas_no_manifold"] == 0

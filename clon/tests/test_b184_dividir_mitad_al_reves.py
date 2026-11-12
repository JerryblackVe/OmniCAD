# -*- coding: utf-8 -*-
"""B-184: Dividir un cuerpo importado de STEP dejó una mitad con volumen negativo (−46 885 mm³) y el paso salió ok. El STEP
de Gerardo no está: se fuerza la mitad al revés en la salida del kernel."""
import numpy as np
import pytest

from omnicad.nucleo import geometria as geo, solidos_modificar as sm

_PLANO = geo.Plano.desde_marco(np.array([10.0, 0, 0]), np.array([1.0, 0, 0]), np.array([0, 1.0, 0]))


def _partir_y_tocar(monkeypatch, tocar):
    real = sm._partir

    def partir(forma, herramientas):
        piezas = geo.solidos(real(forma, herramientas))
        return geo.compuesto(tocar(piezas))
    monkeypatch.setattr(sm, "_partir", partir)


def test_la_mitad_al_reves_se_da_vuelta(monkeypatch):
    _partir_y_tocar(monkeypatch, lambda p: [geo.TopoDS.Solid(p[0].Reversed())] + p[1:])
    partes = sm.dividir_cuerpo(geo.caja(40, 20, 10), _PLANO)
    assert sorted(round(geo.volumen(p), 6) for p in partes) == [2000, 6000]


def test_partes_que_no_suman_el_cuerpo_dan_error(monkeypatch):
    _partir_y_tocar(monkeypatch, lambda p: [p[0], p[0]])          # una cáscara rota: las «mitades» no son el cuerpo
    with pytest.raises(geo.ErrorGeometria, match="Revisar geometría"):
        sm.dividir_cuerpo(geo.caja(40, 20, 10), _PLANO)

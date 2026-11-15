# -*- coding: utf-8 -*-
"""B-503 (parte 3): Cara de desfase sobre las paredes de un relieve (un logo: anillo y punto sobre una placa) va por el
contorno 2D y re-extruye, como Fusion: +3 une el punto con el anillo y −1,6 se come el anillo de 3 mm. Si el atajo no
puede, sigue el camino de siempre (regla de B-453), y también anda sobre un cuerpo ya desfasado."""
import math

import pytest

from omnicad.nucleo import geometria as geo
from omnicad.nucleo import solidos_modificar as sm
from omnicad.nucleo import vectores

H = 3          # alto del relieve, sobre una placa de 40 × 40 × 3


def _cuerpo(r_afuera=12.0, r_adentro=9.0, r_punto=2.5):
    placa = geo.caja(40, 40, 3, (-20, -20, 0))
    anillo = geo.booleano(geo.cilindro(r_afuera, H, (0, 0, 3)), geo.cilindro(r_adentro, H, (0, 0, 3)), "cortar")
    cuerpo = geo.booleano(placa, anillo, "unir")
    return geo.booleano(cuerpo, geo.cilindro(r_punto, H, (14, 14, 3)), "unir") if r_punto else cuerpo


def _paredes(forma):
    return [c for c in geo.caras(forma) if 3.1 < geo.centro_masa(c, True)[2] < 5.9]


V0 = 40 * 40 * 3


@pytest.mark.parametrize("d, anillo, punto", [(0.5, (12.5, 8.5), 3.0), (-0.5, (11.5, 9.5), 2.0)])
def test_logo_mas_y_menos_medio_milimetro(d, anillo, punto):
    forma = _cuerpo()
    r = sm.desfasar_caras(forma, _paredes(forma), d)
    esperado = V0 + math.pi * H * (anillo[0] ** 2 - anillo[1] ** 2 + punto ** 2)
    assert geo.volumen_exacto(r) == pytest.approx(esperado, rel=1e-6) and geo.es_valida(r)


def test_mas_3_une_el_punto_con_el_anillo_como_fusion():
    forma = _cuerpo()
    r = sm.desfasar_caras(forma, _paredes(forma), 3)
    esperado = _cuerpo(15, 6, 5.5)                   # el punto (r 5,5 a 19,8 del centro) se mete en el anillo (r 15)
    assert len(geo.solidos(r)) == 1 and geo.es_valida(r)
    assert geo.volumen_exacto(r) == pytest.approx(geo.volumen_exacto(esperado), rel=1e-6)


def test_menos_1_6_se_come_el_anillo_de_3_mm_como_fusion():
    forma = _cuerpo()
    r = sm.desfasar_caras(forma, _paredes(forma), -1.6)
    assert geo.volumen_exacto(r) == pytest.approx(V0 + math.pi * H * 0.9 ** 2, rel=1e-6) and geo.es_valida(r)


def test_si_el_atajo_no_puede_sigue_el_camino_de_siempre(monkeypatch):
    forma = _cuerpo()
    rapido = sm.desfasar_caras(forma, _paredes(forma), 0.5)

    def no_puedo(*_a, **_k):
        raise geo.ErrorGeometria("simulado")
    monkeypatch.setattr(vectores, "desfase_caras", no_puedo)
    assert sm._desfase_por_contorno(forma, _paredes(forma), 0.5) is None
    normal = sm.desfasar_caras(forma, _paredes(forma), 0.5)          # el offset 3D del kernel
    assert geo.volumen_exacto(normal) == pytest.approx(geo.volumen_exacto(rapido), rel=1e-6)


def test_sobre_un_cuerpo_ya_desfasado():
    forma = _cuerpo()
    una = sm.desfasar_caras(forma, _paredes(forma), 0.5)
    dos = sm.desfasar_caras(una, _paredes(una), 0.5)
    esperado = V0 + math.pi * H * (13 ** 2 - 8 ** 2 + 3.5 ** 2)
    assert geo.volumen_exacto(dos) == pytest.approx(esperado, rel=1e-6) and geo.es_valida(dos)


def test_una_cara_suelta_no_toma_el_atajo():
    """Una pared sola de una caja no está entre dos tapas paralelas: sigue el camino de siempre."""
    caja = geo.caja(10, 10, 10)
    lado = min(geo.caras(caja), key=lambda c: geo.centro_masa(c, True)[0])
    assert sm._desfase_por_contorno(caja, [lado], 1) is None
    assert geo.volumen_exacto(sm.desfasar_caras(caja, [lado], 1)) == pytest.approx(1100)

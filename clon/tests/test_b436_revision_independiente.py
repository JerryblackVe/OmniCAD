"""B-436: atravesar una franja de una cara no implica consumir todo el cuerpo."""

import pytest

from omnicad.nucleo import geometria as geo, solidos_modificar as sm


def test_desfase_de_media_cara_puede_atravesar_su_franja_y_conservar_el_resto():
    caja = geo.caja(20, 10, 10)
    frente = min(geo.caras(caja), key=lambda cara: geo.centro_masa(cara, True)[1])
    partida = sm.dividir_cara(caja, [frente], geo.Plano("XY", 5))
    abajo = min((cara for cara in geo.caras(partida) if geo.centro_masa(cara, True)[1] < 1e-6),
                key=lambda cara: geo.centro_masa(cara, True)[2])

    resultado = sm.desfasar_caras(partida, [abajo], -15)

    assert geo.es_valida(resultado)
    assert len(geo.solidos(resultado)) == 1
    assert geo.volumen(resultado) == pytest.approx(20 * 10 * 5)
    minimo, maximo = geo.caja_envolvente(resultado)
    assert minimo == pytest.approx((0, 0, 5))
    assert maximo == pytest.approx((20, 10, 10))

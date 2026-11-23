# -*- coding: utf-8 -*-
"""`se_tocan` entre cuerpos de muchas caras (un texto de 497 caras contra un cuerpo de 20 tardaba 98 s: 1039 distancias
exactas). Descarta primero por malla gruesa y mide exacto solo las caras cercanas; si la malla falla, sigue por el
camino exacto sin mostrar el error."""
import pytest

from omnicad.nucleo import geometria as geo


def _peine(n, y, alto=2.0, extra=()):
    """n cajas separadas (6·n caras) en una sola forma, en la fila de `y` (más las cajas `extra`)."""
    return geo.unir_todos([geo.caja(2, 2, alto, (4 * i, y, 0)) for i in range(n)] + list(extra))


def _fila_lejana(hueco):
    return _peine(15, 2 + hueco, alto=1.0, extra=[geo.caja(2, 2, 1, (0, -8, 0))])


def _modificado(forma):
    """Un cuerpo ya modificado por un paso anterior: la forma con un agujero cortado."""
    return geo.booleano(forma, geo.cilindro(0.5, 10, (1, 1, -1)), "cortar")


def _exacto(monkeypatch, a, b):
    with monkeypatch.context() as m:
        m.setattr(geo, "PARES_MALLA_SE_TOCAN", 10 ** 9)
        return geo.se_tocan(a, b)


@pytest.fixture
def usos(monkeypatch):
    """Cuenta cuántas veces la malla decidió algo (devolvió candidatas)."""
    veces = []
    original = geo._caras_cercanas_malla
    monkeypatch.setattr(geo, "_caras_cercanas_malla", lambda *x: veces.append(original(*x)) or veces[-1])
    return veces


@pytest.mark.parametrize("hueco, tocan", [(1.0, False), (0.0, True), (-0.5, True)])
def test_igual_que_el_camino_exacto_con_cuerpos_de_muchas_caras(monkeypatch, usos, hueco, tocan):
    a = _modificado(_peine(12, 0))                      # fila de 12 cajas en y = 0..2
    b = _fila_lejana(hueco)                             # su fila queda a `hueco` mm de la de `a`; una caja suelta
                                                        # lejos hace que las cajas envolventes se solapen
    assert len(geo.caras(a)) * len(geo.caras(b)) > geo.PARES_MALLA_SE_TOCAN
    assert geo.se_tocan(a, b) is tocan is _exacto(monkeypatch, a, b)
    assert usos and usos[0] is not None                 # la vía rápida decidió; no cayó al camino exacto


def test_la_malla_descarta_las_caras_lejanas(usos):
    a, b = _modificado(_peine(12, 0)), _fila_lejana(1.0)
    geo.se_tocan(a, b)
    caras_a, caras_b = usos[0]
    assert len(caras_a) < len(geo.caras(a)) and len(caras_b) < len(geo.caras(b))


def test_si_la_malla_falla_cae_al_camino_exacto_sin_error(monkeypatch):
    a, b = _modificado(_peine(12, 0)), _fila_lejana(0.0)

    def falla(*x):
        raise RuntimeError("sin malla")
    monkeypatch.setattr(geo, "BRepMesh_IncrementalMesh", falla)
    assert geo._caras_cercanas_malla(a, b, 1e-6) is None
    assert geo.se_tocan(a, b) is True

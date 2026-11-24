# -*- coding: utf-8 -*-
"""`se_tocan` entre cuerpos de muchas caras (un texto de 497 caras contra un cuerpo de 20 tardaba 98 s: 1039 distancias
exactas). Descarta primero por malla gruesa y mide exacto solo las caras cercanas; si la malla falla, sigue por el
camino exacto sin mostrar el error."""
import time

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
    caras_a, caras_b, _ = usos[0]
    assert len(caras_a) < len(geo.caras(a)) and len(caras_b) < len(geo.caras(b))


def test_si_la_malla_falla_cae_al_camino_exacto_sin_error(monkeypatch):
    a, b = _modificado(_peine(12, 0)), _fila_lejana(0.0)

    def falla(*x):
        raise RuntimeError("sin malla")
    monkeypatch.setattr(geo, "BRepMesh_IncrementalMesh", falla)
    assert geo._caras_cercanas_malla(a, b, 1e-6) is None
    assert geo.se_tocan(a, b) is True


@pytest.mark.parametrize("hueco, tocan", [(1.0, False), (0.0, True)])
def test_la_malla_tambien_decide_en_cuerpos_medianos(monkeypatch, usos, hueco, tocan):
    """B-837: un logo de 20 × 14 caras (280 pares, bajo los 1000 de antes) tardaba 2,9 s en distancias exactas."""
    a = _modificado(_peine(5, 0))
    b = _peine(4, 2 + hueco, alto=1.0, extra=[geo.caja(2, 2, 1, (0, -8, 0))])
    pares = len(geo.caras(a)) * len(geo.caras(b))
    assert geo.PARES_MALLA_SE_TOCAN < pares <= 1000
    assert geo.se_tocan(a, b) is tocan is _exacto(monkeypatch, a, b)
    assert usos and usos[0] is not None


def _mallada(forma):
    geo.teselar(forma)
    return forma


@pytest.mark.parametrize("separacion, lejos", [(8.0, True), (0.1, False), (0.0, False)])
def test_mallas_lejanas_nunca_separa_caras_que_se_acercan(separacion, lejos):
    a = _mallada(geo.caja(2, 2, 2))
    b = _mallada(geo.caja(2, 2, 2, (2 + separacion, 0, 0)))
    cache = {}
    veredictos = [geo._mallas_lejanas(fa, fb, 0.2, cache) for fa in geo.caras(a) for fb in geo.caras(b)]
    assert all(veredictos) is lejos
    if not lejos:   # una cara inclinada o con el hueco justo nunca se declara lejana si el exacto dice que se acercan
        exactas = [geo.BRepExtrema_DistShapeShape(fa, fb).Value() for fa in geo.caras(a) for fb in geo.caras(b)]
        assert all(not v or e > 0.2 for v, e in zip(veredictos, exactas, strict=True))


def test_mallas_lejanas_sin_malla_o_con_error_no_descarta(monkeypatch):
    sin_malla = geo.caras(geo.caja(2, 2, 2, (50, 0, 0)))[0]
    assert geo._mallas_lejanas(geo.caras(_mallada(geo.caja(2, 2, 2)))[0], sin_malla, 0.2, {}) is False
    cara = geo.caras(_mallada(geo.caja(2, 2, 2)))[0]
    monkeypatch.setattr(geo.np, "einsum", lambda *x: 1 / 0)
    assert geo._mallas_lejanas(cara, cara, 0.2, {}) is False


@pytest.mark.parametrize("separacion, lejos", [(8.0, True), (0.3, True), (0.1, False), (0.0, False)])
def test_puntos_lejanos_nunca_separa_caras_curvas_que_se_acercan(separacion, lejos):
    """B-838: la caja y el plano no separan caras curvas a 0,5-9 mm; las muestras sí, sin separar nunca las que se acercan."""
    a = _mallada(geo.cilindro(2, 4))
    b = _mallada(geo.cilindro(2, 4, (4 + separacion, 0, 0)))
    cache = {}
    veredictos = [geo._mallas_lejanas(fa, fb, 0.2, cache) for fa in geo.caras(a) for fb in geo.caras(b)]
    assert all(veredictos) is lejos or not lejos
    exactas = [geo.BRepExtrema_DistShapeShape(fa, fb).Value() for fa in geo.caras(a) for fb in geo.caras(b)]
    assert all(not v or e > 0.2 for v, e in zip(veredictos, exactas, strict=True))


def test_puntos_lejanos_falla_sin_error_y_no_descarta(monkeypatch):
    a = _mallada(geo.cilindro(2, 4))
    b = _mallada(geo.booleano(geo.cilindro(6, 4), geo.cilindro(2.6, 4, (0, 0, -1)), "cortar"))     # un cilindro dentro de un agujero a 0,6 mm
    pares = [(fa, fb) for fa in geo.caras(a) for fb in geo.caras(b)]
    antes = [geo._mallas_lejanas(fa, fb, 0.2, {}) for fa, fb in pares]
    monkeypatch.setattr(geo.np, "isinf", lambda *x: 1 / 0)
    despues = [geo._mallas_lejanas(fa, fb, 0.2, {}) for fa, fb in pares]
    assert sum(antes) > sum(despues)       # las muestras separaban pares que la caja y el plano no; si fallan, no se descarta nada


@pytest.mark.parametrize("hueco, tocan", [(0.4, False), (0.0, True)])
def test_se_tocan_con_curvas_sobre_cuerpo_ya_modificado(monkeypatch, usos, hueco, tocan):
    """Cuerpos con caras curvas (cilindros en fila) a `hueco` mm, `a` ya cortado por un paso anterior: igual que el exacto."""
    fila = lambda y: geo.unir_todos([geo.cilindro(1, 2, (4 * i, y, 0)) for i in range(8)]
                                    + [geo.caja(2, 2, 1, (0, y - 12, 0))])
    a = _modificado(fila(0))
    b = fila(2 + hueco)
    assert geo.se_tocan(a, b) is tocan is _exacto(monkeypatch, a, b)


# --- B-837: el par del logo de planos cruzados (tapa con agujeros contra cara inclinada, ~10 mm) ---

_N_BAJO = (-0.7227, 0.0, -0.6911)     # normal saliente de la cara inferior del prisma inclinado 46,31°


def _logo_de_planos_cruzados(delta_z):
    """(a, b) del par de B-837: placa con un agujero grande R=15 (la tapa queda de ~115 triángulos con agujeros, cuerpo
    ya modificado por los cortes) y un prisma 30×8×2 inclinado 46,31° cuyo borde bajo cruza el plano de la tapa DENTRO
    del agujero: los planos se cruzan, las cajas de los triángulos se solapan y la distancia real es ~10 mm (la fila
    medía 10,45 mm y su par exacto costaba ~0,3 s). Con `delta_z` el prisma penetra la placa."""
    a = geo.booleano(geo.caja(60, 50, 3), geo.cilindro(15, 5, (30, 25, -1)), "cortar")
    a = geo.booleano(a, geo.cilindro(3, 5, (52, 12, -1)), "cortar")
    a = geo.booleano(a, geo.cilindro(2, 8, (8, 40, -1)), "cortar")     # agujero de un paso anterior
    prisma = geo.rotar(geo.caja(30, 8, 2, (0, 21, 3 - delta_z)), (30, 0, 3), (0, 1, 0), 46.31)
    return a, prisma


def _caras_del_par(a, b):
    """(tapa de la placa, cara inferior del prisma)."""
    fa = next(f for f in geo.caras(a) if (pl := geo.plano_de_cara(f)) is not None and pl.normal[2] > 0.999)
    fb = max((f for f in geo.caras(b) if geo.plano_de_cara(f) is not None),
             key=lambda f: geo.plano_de_cara(f).normal @ _N_BAJO)
    return fa, fb


@pytest.mark.parametrize("delta_z, lejos", [(0.0, True), (15.06, False)])
def test_el_par_del_logo_de_planos_cruzados_se_descarta_sin_exacto(delta_z, lejos):
    """B-837: `_mallas_lejanas` descarta el par en milisegundos (cajas → planos → muestras KD de B-838) sin pagar la
    distancia exacta; si el prisma penetra la placa, no lo descarta (ante la duda, camino exacto)."""
    a, b = _logo_de_planos_cruzados(delta_z)
    _mallada(a)
    _mallada(b)
    fa, fb = _caras_del_par(a, b)
    t0 = time.perf_counter()
    assert geo._mallas_lejanas(fa, fb, 0.2, {}) is lejos
    if lejos:                           # el par de la fila: el exacto costaba ~0,3 s
        assert time.perf_counter() - t0 < 0.15
    d = geo.BRepExtrema_DistShapeShape(fa, fb)
    assert d.IsDone()
    if lejos:
        assert d.Value() > 5            # ~10 mm, como el par de 10,45 mm de la fila
    else:
        assert d.Value() <= 0.2         # se tocan: nunca se declara lejano lo que se acerca


def test_se_tocan_del_logo_de_planos_cruzados_no_mide_ningun_par_exacto(monkeypatch, usos):
    """B-837 (flujo entero): 108 pares de caras y ninguna distancia exacta — la malla gruesa no deja
    candidatos y el par de ~10 mm se saltea; el resultado es el mismo que el del camino exacto."""
    a, prisma = _logo_de_planos_cruzados(0.0)
    b = geo.unir_todos([prisma, geo.caja(6, 6, 2, (100, 0, 0))])
    assert len(geo.caras(a)) * len(geo.caras(b)) > geo.PARES_MALLA_SE_TOCAN
    medidas = []
    original = geo.BRepExtrema_DistShapeShape
    monkeypatch.setattr(geo, "BRepExtrema_DistShapeShape", lambda *x: medidas.append(1) or original(*x))
    assert geo.se_tocan(a, b) is False
    assert not medidas                     # el par de la fila ya no se mide exacto
    assert usos and usos[0] is not None    # la vía rápida decidió; no cayó al camino exacto
    assert _exacto(monkeypatch, a, b) is False

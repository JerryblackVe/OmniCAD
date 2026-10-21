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


# ---------------------------------------------------------------- B-39 (fuzzer): el kernel devolvía resultados imposibles
# Los tres montajes salieron de `scripts/fuzz_b39.py` (semilla b39) y fallaban SIN avisar: la unión devolvía solo la
# herramienta, un cuerpo que «no tocaba» la pared o una forma vacía. `geo.booleano` ahora verifica el resultado y reintenta.
def _pared():
    return geo.booleano(geo.cilindro(30, 140), geo.cilindro(27, 140), "cortar")


def _unir_creible(base, herramienta):
    unida = geo.booleano(base, herramienta, "unir")
    vb, vh, vu = (geo.volumen_exacto(f) for f in (base, herramienta, unida))
    assert max(vb, vh) - 1e-3 <= vu <= vb + vh + 1e-3
    assert geo.es_valida(unida)
    return unida, vb, vh, vu


def test_b39_esfera_centrada_a_un_micrometro_de_la_cara_interior_no_borra_la_pared():
    esfera = geo.esfera(5.774899598519848, (-25.0485835630025, 10.078120632701422, 40.294906809049834))
    unida, vb, vh, vu = _unir_creible(_pared(), esfera)
    assert vu > vb and len(geo.solidos(unida)) == 1          # antes: 806,7 mm³ (solo la esfera)


def test_b39_toro_que_cruza_la_pared_se_une_con_su_parte_de_afuera():
    toro = geo.toroide(2.4651789735093654, 1.3714429023683579)       # eje Z; girado al eje X como lo arma el fuzzer
    toro = geo.trasladar(geo.rotar(toro, (0, 0, 0), (0, 1, 0), 90), (-26.99695215674611, -0.46752031652268067, 112.5936192487904))
    unida, vb, vh, vu = _unir_creible(_pared(), toro)
    assert 35 < vu - vb < 50                                   # ~46 % del toro (91,5 mm³) queda del lado del hueco
    assert len(geo.solidos(unida)) == 1                        # antes: 2 sólidos, el toro «afuera» de la pared


def test_b39_union_con_solape_de_un_micrometro_no_queda_vacia():
    placa = geo.booleano(geo.caja(80, 60, 8, (-40, -30, 0)), geo.cilindro(10, 8), "cortar")
    r = 2.07862826
    perno = geo.cilindro(r, 5.4607566954, (0, 0, -2.7303783477))      # eje Z; girado al eje Y como lo arma el fuzzer
    perno = geo.trasladar(geo.rotar(perno, (0, 0, 0), (1, 0, 0), -90), (10, 0, 1e-6 - r))
    unida, vb, vh, vu = _unir_creible(placa, perno)
    assert vu == pytest.approx(vb + vh, abs=1e-3)              # antes: forma vacía, la placa desaparecía


def test_b39_booleano_reintenta_si_el_primer_resultado_es_imposible(monkeypatch):
    base, esfera = _pared(), geo.esfera(3, (28, 0, 70))
    original, llamadas = geo._booleana, []

    def primero_malo(objetivo, herramienta, operacion, **kw):
        llamadas.append(kw)
        return herramienta if not kw else original(objetivo, herramienta, operacion, **kw)

    monkeypatch.setattr(geo, "_booleana", primero_malo)
    unida = geo.booleano(base, esfera, "unir")
    assert len(llamadas) >= 2 and geo.volumen_exacto(unida) > geo.volumen_exacto(base)


def test_b39_booleano_prefiere_el_error_claro_a_la_geometria_equivocada(monkeypatch):
    monkeypatch.setattr(geo, "_booleana", lambda objetivo, herramienta, operacion, **kw: herramienta)
    with pytest.raises(geo.ErrorGeometria, match="imposible"):
        geo.booleano(_pared(), geo.esfera(3, (28, 0, 70)), "unir")


def test_b39_unir_con_un_cuerpo_vacio_o_cortar_todo_sigue_siendo_legitimo():
    caja = geo.caja(10, 10, 10)
    assert geo.esta_vacia(geo.booleano(caja, geo.caja(2, 2, 2, (50, 50, 50)), "intersecar"))     # sin nada en común
    assert geo.esta_vacia(geo.booleano(geo.caja(2, 2, 2, (1, 1, 1)), caja, "cortar"))            # la herramienta cubre todo


def test_b39_union_general_descarta_un_resultado_que_pierde_material():
    a, b, c = geo.caja(10, 10, 10), geo.caja(10, 10, 10, (5, 0, 0)), geo.caja(10, 10, 10, (10, 0, 0))
    correcta = geo.unir_todos([a, b, c])
    assert geo.volumen_exacto(correcta) == pytest.approx(2000)
    assert geo._union_general_creible([a, b, c], correcta)
    assert not geo._union_general_creible([a, b, c], geo.caja(5, 5, 5))     # menos que la caja más grande
    assert not geo._union_general_creible([a, b, c], geo.compuesto([]))      # vacía

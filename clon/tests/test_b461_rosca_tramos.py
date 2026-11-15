"""B-461: la rosca modelada corta el surco partido en tramos (`_en_tramos`): misma geometría y mismas caras que el
recorte de siempre, sobre un cuerpo ya modificado, y si la vía rápida falla cae sola al recorte de siempre."""
import pytest

from omnicad import api
from omnicad.nucleo import geometria as geo
from omnicad.nucleo import solidos_crear as sc


def _cuerpo(modificacion):
    sesion = api.Sesion()
    pasos = [("create_cylinder", {"radius": 5, "height": 30})]
    if modificacion == "chaflanado":
        pasos.append(("chamfer", {"edges": ">Z", "distance": 1}))
    else:
        pasos.append(("create_box", {"length": 24, "width": 18, "height": 3, "x": 2, "z": -3, "operation": "join"}))
    for herramienta, argumentos in pasos:
        resultado = api.llamar(sesion, herramienta, argumentos)
        assert resultado["ok"], resultado
    (cuerpo,) = sesion.doc.estado_final.cuerpos.values()
    return cuerpo.forma


def _roscar(forma):
    sc._surco_en_origen.cache_clear()
    return sc.rosca(forma, None, designacion="M10x1.5")


@pytest.mark.parametrize("modificacion", ["chaflanado", "unido_a_base"])
def test_b461_tramos_da_lo_mismo_que_el_recorte_normal(monkeypatch, modificacion):
    forma = _cuerpo(modificacion)
    usados, original = [], sc._en_tramos
    monkeypatch.setattr(sc, "_en_tramos", lambda *a: usados.append(1) or original(*a))
    rapida = _roscar(forma)
    assert usados, "M10×30 (20 vueltas) tiene que ir por la vía rápida"
    monkeypatch.setattr(sc, "_en_tramos", lambda *a: None)
    normal = _roscar(forma)
    assert geo.es_valida(rapida)
    assert geo.volumen_exacto(rapida, 1e-6) == pytest.approx(geo.volumen_exacto(normal, 1e-6), rel=1e-6)
    assert len(geo.caras(rapida)) == len(geo.caras(normal))     # las caras partidas se vuelven a juntar


def test_b461_si_la_via_rapida_sale_mal_cae_al_recorte_normal(monkeypatch):
    forma = _cuerpo("chaflanado")
    monkeypatch.setattr(sc, "_en_tramos", lambda *a: None)
    normal = _roscar(forma)
    monkeypatch.setattr(sc, "_en_tramos", lambda *a: geo.cilindro(1, 1))     # volumen equivocado: se descarta
    rota = _roscar(forma)
    assert geo.es_valida(rota)
    assert geo.volumen_exacto(rota, 1e-6) == pytest.approx(geo.volumen_exacto(normal, 1e-6), rel=1e-9)

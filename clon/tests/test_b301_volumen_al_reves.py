"""B-301: un empalme o chaflán grande en la arista vertical exterior de una caja vaciada a 1 mm salía «ok» con
casi la caja maciza (11 424 → 106 266 mm³): el kernel devuelve un sólido válido y sin cruces que rellena la cavidad.
En una arista convexa el volumen solo puede bajar."""
import pytest

from omnicad import api


def _caja_vaciada():
    """Caja 60 × 50 × 40 vaciada a 1 mm sin la base (11 424 mm³): `Cuerpo1/E1` es una arista vertical exterior."""
    s = api.Sesion()
    for nombre, args in (("create_box", {"length": 60, "width": 50, "height": 40}),
                         ("shell", {"body": "Cuerpo1", "thickness": 1, "faces": "<Z"})):
        assert api.llamar(s, nombre, args)["ok"]
    return s


@pytest.mark.parametrize("herramienta, medida", [("fillet", {"radius": 29}), ("fillet", {"radius": 39.999}),
                                                 ("chamfer", {"distance": 29})])
def test_rellenar_la_cavidad_es_un_error(herramienta, medida):
    s = _caja_vaciada()

    r = api.llamar(s, herramienta, {"body": "op1.c1", "edges": ["Cuerpo1/E1"], **medida})

    assert not r["ok"] and "supera el grosor de la pared" in r["mensaje"], r


@pytest.mark.parametrize("herramienta, medida, volumen", [("fillet", {"radius": 3.4}, 11324.8),
                                                         ("chamfer", {"distance": 1.9}, 11351.8)])
def test_los_que_entran_siguen_andando(herramienta, medida, volumen):
    s = _caja_vaciada()

    r = api.llamar(s, herramienta, {"body": "op1.c1", "edges": ["Cuerpo1/E1"], **medida})

    assert r["ok"], r
    assert r["result"]["bodies_modified"][0]["volume"] == pytest.approx(volumen, abs=0.1)


def test_empalme_concavo_que_agrega_material_sigue_andando():
    """Las aristas interiores (cóncavas) del vaciado ganan material al empalmar: eso no es «al revés»."""
    s = _caja_vaciada()
    r = api.llamar(s, "fillet", {"body": "op1.c1", "edges": ["Cuerpo1/E20"], "radius": 2})   # vertical interior

    assert r["ok"], r
    assert r["result"]["bodies_modified"][0]["volume"] > 11424.0

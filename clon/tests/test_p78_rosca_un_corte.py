"""P-78: la rosca modelada tira menos cortes que no sacan nada.

Con el surco en 0°, M40x3×30 y M12×1,75×12 hacían 3 y 4 cortes de ~0,4 s; ahora el respaldo es girar el CUERPO 229°
(acierta y la rosca conserva su fase): 2 cortes. La rosca larga corta sus dos mitades por separado en vez de unirlas
(M20x2.5×100: la unión sola tardaba 5,7 s)."""
import pytest

from omnicad.nucleo import geometria as geo
from omnicad.nucleo import solidos_crear as sc


@pytest.fixture
def cortes(monkeypatch):
    contador = {"n": 0}
    original = sc.BRepAlgoAPI_Cut

    class Contado(original):
        def Build(self, *a):
            contador["n"] += 1
            return super().Build(*a)

    monkeypatch.setattr(sc, "BRepAlgoAPI_Cut", Contado)
    sc._surco_en_origen.cache_clear()
    yield contador
    sc._surco_en_origen.cache_clear()


@pytest.mark.parametrize("designacion, diametro, alto, volumen", [
    ("M40x3", 40, 30, 33976.47),       # antes: 3 cortes (dos vacíos)
    ("M12x1.75", 12, 12, 1107.54),     # antes: 4 cortes (y la fase corrida 61°)
])
def test_p78_si_0_grados_falla_el_respaldo_acierta(cortes, designacion, diametro, alto, volumen):
    forma = sc.rosca(geo.cilindro(diametro / 2, alto), None, designacion=designacion, clase="6g")
    assert cortes["n"] == 2
    assert geo.es_valida(forma)
    assert geo.volumen_exacto(forma, 1e-6) == pytest.approx(volumen, rel=1e-5)


def test_p78_la_rosca_larga_corta_las_mitades_sin_unirlas(cortes, monkeypatch):
    uniones = []
    booleano = geo.booleano
    monkeypatch.setattr(geo, "booleano", lambda a, b, op, *r, **k: (uniones.append(op) if op == "unir" else None)
                        or booleano(a, b, op, *r, **k))
    forma = sc.rosca(geo.cilindro(10, 100), None, designacion="M20x2.5", clase="6g")
    assert geo.es_valida(forma)
    assert geo.volumen_exacto(forma, 1e-6) == pytest.approx(26495.18, rel=1e-5)
    assert cortes["n"] == 2            # un corte por mitad (el barrido entero sale incompleto: B-371)
    assert uniones == ["unir"]         # solo los dos torneados; los surcos no se unen

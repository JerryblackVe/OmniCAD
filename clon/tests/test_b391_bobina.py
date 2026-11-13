"""B-391: la Bobina cónica que llega al eje antes del final (o que sale dada vuelta) da error, no un sólido que se pisa."""
import pytest

from omnicad import api
from omnicad.nucleo import geometria as geo
from omnicad.nucleo import solidos_crear as sc


def test_conica_que_llega_al_eje_da_error_por_la_api():
    s = api.Sesion()
    assert api.llamar(s, "create_box", {"length": 60, "width": 50, "height": 20})["ok"]
    r = api.llamar(s, "create_coil", {"diameter": 19.3078, "height": 40.0, "angle": -30})   # r final ≈ 9,65 − 23 < 0
    assert not r["ok"] and "llega al eje" in str(r)


def test_conica_que_no_llega_al_eje_sigue_andando():
    forma = sc.bobina((0, 0, 0), (0, 0, 1), diametro=20, revoluciones=5, altura=30, angulo=-10, tamano_seccion=3)
    recta = sc.bobina((0, 0, 0), (0, 0, 1), diametro=20, revoluciones=5, altura=30, tamano_seccion=3)
    assert geo.es_valida(forma) and 0 < geo.volumen(forma) < geo.volumen(recta)     # el cono angosta: menos largo de hélice


def test_justo_antes_del_eje_tambien_da_error():
    # r_c 10, sección 3: el radio final 10 + 30·tan(−20°) = −0,92 deja la sección cruzando el eje
    with pytest.raises(geo.ErrorGeometria, match="llega al eje"):
        sc.bobina((0, 0, 0), (0, 0, 1), diametro=20, revoluciones=5, altura=30, angulo=-20, tamano_seccion=3)

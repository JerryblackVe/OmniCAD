# -*- coding: utf-8 -*-
"""Tolerancias normalizadas (`nucleo/tolerancias.py`): ajustes ISO 286, clases de rosca ISO 965-1 y ASME B1.1.
Los valores esperados son los de las tablas publicadas de cada norma."""
import pytest

from omnicad.nucleo import geometria as g
from omnicad.nucleo import tolerancias as tol

IN = 25.4


# ---------------------------------------------------------------- ISO 286
def test_grados_it_iso_286():
    assert tol.grado_it(25, 7) == pytest.approx(0.021)
    assert tol.grado_it(25, 6) == pytest.approx(0.013)
    assert tol.grado_it(3, 7) == pytest.approx(0.010)          # «hasta 3 inclusive»: primer escalón
    assert tol.grado_it(3.01, 7) == pytest.approx(0.012)
    assert tol.grado_it(500, 11) == pytest.approx(0.400)
    assert tol.grado_it(100, 5) == pytest.approx(0.015)
    with pytest.raises(g.ErrorGeometria):
        tol.grado_it(501, 7)
    with pytest.raises(g.ErrorGeometria):
        tol.grado_it(25, 12)


@pytest.mark.parametrize("nominal, clase, esperado", [
    (25, "H7", (0.021, 0.0)), (25, "g6", (-0.007, -0.020)), (25, "h6", (0.0, -0.013)), (25, "h7", (0.0, -0.021)),
    (25, "f7", (-0.020, -0.041)), (25, "k6", (0.015, 0.002)), (25, "n6", (0.028, 0.015)), (25, "p6", (0.035, 0.022)),
    (25, "s6", (0.048, 0.035)), (25, "j6", (0.009, -0.004)), (25, "H8", (0.033, 0.0)), (25, "H11", (0.130, 0.0)),
    (10, "H7", (0.015, 0.0)), (10, "g6", (-0.005, -0.014)), (50, "f7", (-0.025, -0.050)), (60, "s6", (0.072, 0.053)),
    (100, "s6", (0.093, 0.071)), (25, "G7", (0.028, 0.007)), (40, "e8", (-0.050, -0.089)), (40, "d9", (-0.080, -0.142)),
])
def test_desviaciones_iso_286(nominal, clase, esperado):
    assert tol.desviaciones(nominal, clase) == pytest.approx(esperado, abs=1e-9)


def test_ajustes_juego_transicion_y_apriete():
    a = tol.ajuste(25, "H7", "g6")
    assert a["tipo"] == "juego" and a["juego_maximo"] == pytest.approx(0.041) and a["juego_minimo"] == pytest.approx(0.007)
    assert a["agujero"]["maximo"] == pytest.approx(25.021) and a["eje"]["minimo"] == pytest.approx(24.980)
    k = tol.ajuste(25, "H7", "k6")
    assert k["tipo"] == "transicion" and k["juego_maximo"] == pytest.approx(0.019) and k["apriete_maximo"] == pytest.approx(0.015)
    p = tol.ajuste(25, "H7", "p6")
    assert p["tipo"] == "apriete" and p["apriete_minimo"] == pytest.approx(0.001) and p["apriete_maximo"] == pytest.approx(0.035)
    for malo in (("h7", "g6"), ("H7", "G6"), ("H7", "z6"), ("K7", "h6"), ("H7", "j7")):
        with pytest.raises(g.ErrorGeometria):
            tol.ajuste(25, *malo)


# ---------------------------------------------------------------- ISO 965-1 (rosca métrica)
@pytest.mark.parametrize("d, p, mayor, flancos", [
    (10, 1.5, (9.732, 9.968), (8.862, 8.994)), (6, 1.0, (5.794, 5.974), (5.212, 5.324)),
    (8, 1.25, (7.760, 7.972), (7.042, 7.160)), (12, 1.75, (11.701, 11.966), (10.679, 10.829)),
    (16, 2.0, (15.682, 15.962), (14.503, 14.663)), (20, 2.5, (19.623, 19.958), (18.164, 18.334)),
    (24, 3.0, (23.577, 23.952), (21.803, 22.003)), (3, 0.5, (2.874, 2.980), (2.580, 2.655)),
])
def test_iso_965_exterior_6g(d, p, mayor, flancos):
    lim = tol.limites_rosca("iso_metrica", d, p, "6g")
    assert lim["diametro_mayor"] == pytest.approx(mayor, abs=6e-4)
    assert lim["diametro_flancos"] == pytest.approx(flancos, abs=6e-4)
    assert lim["interna"] is False and lim["norma"] == "ISO 965-1"


@pytest.mark.parametrize("d, p, flancos, menor", [
    (10, 1.5, (9.026, 9.206), (8.376, 8.676)), (6, 1.0, (5.350, 5.500), (4.917, 5.153)),
    (8, 1.25, (7.188, 7.348), (6.647, 6.912)), (20, 2.5, (18.376, 18.600), (17.294, 17.744)),
])
def test_iso_965_interior_6h(d, p, flancos, menor):
    lim = tol.limites_rosca("iso_metrica", d, p, "6H")
    assert lim["diametro_flancos"] == pytest.approx(flancos, abs=6e-4)
    assert lim["diametro_menor"] == pytest.approx(menor, abs=6e-4)
    assert lim["diametro_mayor"] == [d, None]


def test_iso_965_clases_g_y_h_y_tamanos_sin_datos():
    assert tol.limites_rosca("iso_metrica", 10, 1.5, "6h")["diametro_mayor"] == pytest.approx([9.764, 10.0], abs=1e-4)
    assert tol.limites_rosca("iso_metrica", 10, 1.5, "6G")["diametro_flancos"][0] == pytest.approx(9.058, abs=6e-4)
    with pytest.raises(g.ErrorGeometria):
        tol.limites_rosca("iso_metrica", 2, 0.4, "6g")           # M2: sin datos verificados
    with pytest.raises(g.ErrorGeometria):
        tol.limites_rosca("iso_metrica", 10, 1.5, "4H5H")
    with pytest.raises(g.ErrorGeometria):
        tol.limites_rosca("trapezoidal", 20, 4, "7e")


# ---------------------------------------------------------------- ASME B1.1 (rosca unificada)
def _pulgadas(lim, k):
    return [None if x is None else round(x / IN, 4) for x in lim[k]]


@pytest.mark.parametrize("d, tpi, clase, mayor, flancos", [
    (0.25, 20, "2A", [0.2408, 0.2489], [0.2127, 0.2164]), (0.25, 20, "3A", [0.2419, 0.2500], [0.2147, 0.2175]),
    (0.25, 20, "2B", [0.2500, None], [0.2175, 0.2224]), (0.25, 20, "3B", [0.2500, None], [0.2175, 0.2211]),
    (0.5, 13, "2A", [0.4876, 0.4985], [0.4435, 0.4485]), (0.5, 13, "2B", [0.5000, None], [0.4500, 0.4565]),
    (0.25, 28, "2A", [0.2425, 0.2490], [0.2225, 0.2258]), (0.25, 28, "2B", [0.2500, None], [0.2268, 0.2311]),
])
def test_asme_b1_1(d, tpi, clase, mayor, flancos):
    lim = tol.limites_rosca("unificada", d * IN, IN / tpi, clase)
    assert _pulgadas(lim, "diametro_mayor") == pytest.approx(mayor, abs=1.1e-4)
    assert _pulgadas(lim, "diametro_flancos") == pytest.approx(flancos, abs=1.1e-4)


def test_resolver_clase_y_desfases():
    assert tol.resolver_clase("iso_metrica", 10, 1.5, "auto", True) == ("6H", None)
    assert tol.resolver_clase("iso_metrica", 10, 1.5, "auto", False) == ("6g", None)
    assert tol.resolver_clase("unificada", 6.35, 1.27, "auto", False) == ("2A", None)
    assert tol.resolver_clase("trapezoidal", 20, 4, "auto", True) == ("", None)
    clase, aviso = tol.resolver_clase("iso_metrica", 2, 0.4, "auto", True)
    assert clase == "" and "perfil básico" in aviso
    with pytest.raises(g.ErrorGeometria):
        tol.resolver_clase("iso_metrica", 10, 1.5, "6g", True)       # clase de eje en un agujero
    d2, d1 = 10 - 0.649519 * 1.5, 10 - 1.082532 * 1.5
    ext = tol.desfases_rosca("iso_metrica", 10, 1.5, "6g", False, d2, d1)
    assert ext["flancos"] == pytest.approx((0.032 + 0.132 / 2) / 2, abs=1e-4) and ext["menor"] == 0
    intr = tol.desfases_rosca("iso_metrica", 10, 1.5, "6H", True, d2, d1)
    assert intr["flancos"] == pytest.approx(0.180 / 4, abs=1e-4) and intr["menor"] == pytest.approx(0.300 / 4, abs=1e-4)
    assert tol.desfases_rosca("iso_metrica", 10, 1.5, "", True, d2, d1) == {"flancos": 0.0, "menor": 0.0, "limites": None}

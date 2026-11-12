"""B-368: clases métricas de las tablas, conservando los intervalos ISO 965-1 ya verificados."""
import pytest

from omnicad.nucleo import geometria as geo
from omnicad.nucleo import tablas_rosca, tolerancias as tol


METRICAS = ("iso_metrica", "ansi_metrica", "gb_metrica")
MEDIDAS = [
    (7, 1.0, "6g", False, (6.884, 6.2685, 5.744)),
    (7, 1.0, "6H", True, (7.1472, 6.4255, 6.0355)),
    (52, 5.0, "6g", False, (51.664, 48.5634, 45.9408)),
    (52, 5.0, "6H", True, (52.5183, 48.9099, 46.9423)),
]


@pytest.mark.parametrize("familia", METRICAS)
@pytest.mark.parametrize("diametro, paso, clase, interna, medidas", MEDIDAS)
def test_limites_metricos_fuera_de_la_formula(familia, diametro, paso, clase, interna, medidas):
    limites = tol.limites_rosca(familia, diametro, paso, clase, interna)
    mayor, flancos, menor = medidas
    assert limites["diametro_mayor"] == [mayor, None if interna else mayor]
    assert limites["diametro_flancos"] == [flancos, flancos]
    assert limites["diametro_menor"] == [menor, menor]
    assert limites["interna"] is interna


@pytest.mark.parametrize("familia", METRICAS)
@pytest.mark.parametrize("diametro, paso, clase, interna, medidas", MEDIDAS)
def test_auto_metrica_fuera_de_la_formula_no_avisa(familia, diametro, paso, clase, interna, medidas):
    assert tol.resolver_clase(familia, diametro, paso, "auto", interna) == (clase, None)


@pytest.mark.parametrize("familia", METRICAS)
def test_m10_conserva_los_intervalos_y_desfases_iso965(familia):
    limites = tol.limites_rosca(familia, 10, 1.5, "6g", False)
    assert limites["diametro_mayor"] == [9.732, 9.968]
    assert limites["diametro_flancos"] == [8.8617, 8.9937]
    assert limites["diametro_menor"] == [None, None]
    assert limites["norma"] == "ISO 965-1"
    assert tol.limites_rosca(familia, 10, 1.5, "6h")["diametro_mayor"] == [9.764, 10.0]
    assert tol.limites_rosca(familia, 10, 1.5, "6G")["diametro_flancos"][0] == 9.0577
    desfases = tol.desfases_rosca(familia, 10, 1.5, "6g", False, 9.0257, 8.3762)
    assert desfases["fondo"] is None and desfases["cresta"] is None


@pytest.mark.parametrize("diametro, paso, medidas", [
    (7, 1.0, (6.884, 6.289, 5.7645)), (52, 5.0, (51.664, 48.6064, 45.9838)),
    (10, 1.5, (9.85, 8.9515, 8.1645)),
])
def test_clase_4g6g_es_exterior_y_usa_la_tabla(diametro, paso, medidas):
    assert tol.CLASES_POR_FAMILIA["iso_metrica"]["4g6g"] is False
    assert tol.resolver_clase("iso_metrica", diametro, paso, "4g6g", False) == ("4g6g", None)
    limites = tol.limites_rosca("iso_metrica", diametro, paso, "4g6g", False)
    for clave, valor in zip(("diametro_mayor", "diametro_flancos", "diametro_menor"), medidas, strict=True):
        assert limites[clave] == [valor, valor]
    with pytest.raises(geo.ErrorGeometria, match="no es de rosca interior"):
        tol.resolver_clase("iso_metrica", diametro, paso, "4g6g", True)


@pytest.mark.parametrize("familia", METRICAS)
def test_designaciones_de_clases_coinciden_con_filas_y_solo_avisa_si_falta_el_tamano(familia):
    assert set(tablas_rosca.CLASES[familia]) == {fila[1] for fila in tablas_rosca.FILAS[familia]}
    assert tol.CLASES_ISO965.items() <= tol.CLASES_POR_FAMILIA[familia].items()
    assert tol.CLASE_AUTOMATICA[familia] == ("6H", "6g")
    clase, aviso = tol.resolver_clase(familia, 7, 0.1234, "auto", False)
    assert clase == "" and "Sin datos" in aviso

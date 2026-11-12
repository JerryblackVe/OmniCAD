"""B-367: como Fusion, el tamaño de la rosca pone el diámetro de TODA la cara, más fina o más gruesa que la rosca."""
import pytest

from omnicad.nucleo import geometria as geo
from tests.test_b251_rosca_parcial_diametro_cara import _comprobar_fuera_del_tramo, _crear_rosca
from tests.test_rosca_diametros_tabla import d_max, d_min


def _cresta(forma, interna):
    """Ø de la cresta en el medio del tramo roscado (z 10 a 20)."""
    losa = geo.booleano(forma, geo.caja(40, 40, 6, origen=(-20, -20, 12)), "intersecar")
    return d_min(losa) if interna else d_max(losa)


@pytest.mark.parametrize("designacion, radio, interna", [
    ("M36", 10, False),      # eje más fino: se rellena
    ("M12", 10, False),      # eje más grueso: se tornea
    ("M22", 10, False),      # entre el Ø menor y el mayor: antes quedaba en Ø20 con la cresta truncada
    ("M10", 4.5, True),      # agujero Ø9, más ancho que el taladro de M10: se rellena hasta 8,526
])
def test_la_cara_entera_toma_el_diametro_del_tamano(designacion, radio, interna):
    forma = _crear_rosca(radio, designacion, "6H" if interna else "6g", interna, length=10, offset=5)
    cresta = _cresta(forma, interna)
    assert abs(cresta - 2 * radio) > 0.1
    _comprobar_fuera_del_tramo(forma, cresta, interna)

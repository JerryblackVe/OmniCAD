"""B-371: la rosca modelada M20x2.5 con perfil básico (clase vacía) en un eje Ø20 × 100 cortaba solo el 57 % del filete:
el barrido largo del surco salía incompleto y el perfil básico no lo verificaba."""
import numpy as np
import pytest

from omnicad.nucleo import geometria as geo
from omnicad.nucleo import solidos_crear as sc


def test_surco_largo_incompleto_se_rechaza():
    # 100 mm: el barrido sale con 3 401 mm³ en vez de 6 003 (60,03 por mm, como con 30 o 90 mm)
    with pytest.raises(geo.ErrorGeometria, match="otro tamaño"):
        sc._surco_rosca(np.zeros(3), np.array([0.0, 0.0, 1.0]), 20, 2.5, 0, 100, False, "derecha", 10, partes=True)


def test_m20_basica_de_100_mm_corta_el_filete_entero():
    cilindro = geo.cilindro(10, 100)
    roscado = sc.rosca(cilindro, designacion="M20x2.5", clase="")
    quitado = geo.volumen_exacto(cilindro, sc._EPS_ROSCA) - geo.volumen_exacto(roscado, sc._EPS_ROSCA)
    assert geo.es_valida(roscado)
    assert quitado / 100 == pytest.approx(45.19, rel=0.01)      # lo mismo por mm que con 10 y 30 mm

"""B-460: caja 100 × 60 × 40, empalme de la arista de arriba de 100 mm. OmniCAD fallaba desde r41 («radio demasiado
grande»); Fusion acepta r55 y r59: se come entera la cara lateral (40 de alto) y la base recorta el cilindro
(`evidencias/reportes_pc/2026-11-14_e11_esfuerzo_empalme_chaflan/fusion_b_empalme_r55_acepta.png`)."""
import math

import pytest
from scipy.integrate import quad

from omnicad.nucleo import geometria as geo
from omnicad.nucleo import solidos_modificar as sm
from tests.test_b400_empalme_cara_entera import _arista


def _volumen_esperado(r, ancho=60, alto=40, largo=100):
    """Caja menos la esquina fuera del círculo (centro a r de la arista hacia adentro), recortada por la base."""
    def quitado(y):                        # alto que se va a la distancia y de la cara lateral
        z = alto - r + math.sqrt(max(0.0, r * r - (r - y) ** 2))
        return alto - max(0.0, min(alto, z))
    return ancho * alto * largo - quad(quitado, 0, r, limit=200)[0] * largo


def _empalmar(r, forma=None):
    forma = geo.caja(100, 60, 40) if forma is None else forma
    return sm.empalme(forma, [{"aristas": [_arista(forma, (50, 0, 40))], "tipo": "constante", "radio": r}])


@pytest.mark.parametrize("r", [41, 55, 59])
def test_radio_mayor_que_la_cara_lateral_entra_como_fusion(r):
    forma = _empalmar(r)
    assert geo.es_valida(forma)
    assert geo.volumen(forma) == pytest.approx(_volumen_esperado(r), rel=1e-6)
    (_, y0, z0), (_, y1, z1) = geo.caja_envolvente(forma)
    assert (y1, z0, z1) == pytest.approx((60, 0, 40), abs=1e-6) and y0 > 0    # la cara de adelante desapareció


def test_mas_que_la_cara_de_arriba_sigue_dando_error():
    with pytest.raises(geo.ErrorGeometria, match="El radio no entra"):
        _empalmar(61)


def test_no_corta_otra_parte_del_cuerpo():
    """Si debajo de la cara que se come sigue material (un escalón hacia afuera), el desborde lo cortaría: error."""
    base = geo.booleano(geo.caja(100, 60, 40), geo.trasladar(geo.caja(100, 100, 10), (0, -40, -10)), "unir")
    with pytest.raises(geo.ErrorGeometria, match="El radio no entra"):
        _empalmar(55, base)

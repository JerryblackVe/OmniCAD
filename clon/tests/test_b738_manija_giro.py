"""B-738: el largo de la manija dibujada cambia con el giro como en Fusion (período 90°)."""
import math

import numpy as np
import pytest

from omnicad.restricciones import boceto_geometria as g

_Q4 = [(0, 0), (20, 10), (40, -5), (60, 5)]
_Q5 = _Q4 + [(80, 0)]
# Fusion (E11, 20/11): largo total de la manija automática en el punto 0, por giro en grados
_FUSION = {"4p": (_Q4, {0: 19.890, 15: 19.68177, 30: 21.396, 45: 22.35416, 60: 22.403, 90: 19.890}),
           "5p": (_Q5, {0: 28.48022, 30: 31.806, 60: 32.38243, 90: 28.48022})}


def _largo(Q, giro):
    c, s = math.cos(math.radians(giro)), math.sin(math.radians(giro))
    Q = [(c * x - s * y, s * x + c * y) for x, y in Q]
    pol, nud, p = g._quintica_fusion(Q, False, None)
    d = g.evaluar_primitiva(("spline", None, pol, nud, p, None), 0.0, 1)[1]
    return 2 * math.hypot(*d) / g.escala_manija(Q, 0, np.array(d) / math.hypot(*d), 5)


@pytest.mark.parametrize("forma,tol", [("4p", 0.012), ("5p", 0.03)])
def test_el_largo_de_la_manija_sigue_a_fusion_en_cada_giro(forma, tol):
    Q, medidas = _FUSION[forma]
    for giro, fusion in medidas.items():
        assert _largo(Q, giro) == pytest.approx(fusion, rel=tol), (forma, giro)


def test_la_manija_tiene_periodo_90_grados():
    assert _largo(_Q4, 90) == pytest.approx(_largo(_Q4, 0), rel=1e-9)

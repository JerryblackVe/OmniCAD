"""H-82: las caras adyacentes no deben forzar la conicidad más allá del límite real."""
import math

import numpy as np
import pytest

from omnicad import api
from omnicad.nucleo import geometria as geo


def test_adyacentes_admite_conicidad_que_se_cierra_despues_de_la_cara_limite():
    sesion = api.Sesion()
    for nombre, argumentos in [
        ("create_box", {"length": 20, "width": 20, "height": 5, "z": 10, "name": "Tope"}),
        ("create_sketch", {"plane": "XY", "name": "Perfil"}),
        ("draw_rectangle", {"x1": -1, "y1": -2, "x2": 1, "y2": 2}),
    ]:
        respuesta = api.llamar(sesion, nombre, argumentos)
        assert respuesta["ok"], respuesta

    tangente = math.tan(math.radians(5))
    # Integral de (2 - 2*z*tangente) * (4 - 2*z*tangente), desde z=0 hasta z=10.
    volumen = 8 * 10 - 6 * tangente * 10**2 + 4 / 3 * tangente**2 * 10**3
    assert 10 < 1 / tangente < 15
    for modo in ("face", "adjacent"):
        respuesta = api.llamar(sesion, "extrude", {
            "sketch": "Perfil", "extent": "to_object", "to": "<Z", "body": "Tope",
            "to_mode": modo, "taper_angle": -5,
        })
        assert respuesta["ok"], respuesta
        forma = list(sesion.doc.estado_final.cuerpos.values())[-1].forma
        assert geo.es_valida(forma)
        assert geo.volumen_exacto(forma) == pytest.approx(volumen, abs=1e-6)
        assert np.allclose(geo.caja_envolvente(forma), [[-1, -2, 0], [1, 2, 10]], atol=1e-6)

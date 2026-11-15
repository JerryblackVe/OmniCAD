"""Revisión de P-98: el cero explícito prevalece sobre el automático."""
import copy

import pytest

from omnicad import api


def test_cambiar_arista_respeta_el_eje_cero_enviado_en_la_misma_edicion():
    sesion = api.Sesion()

    def llamar(herramienta, **argumentos):
        respuesta = api.llamar(sesion, herramienta, argumentos)
        assert respuesta["ok"], respuesta
        return respuesta["result"]

    llamar("create_box", length=20, width=30, height=40, anchor="corner")
    plano = llamar("create_construction_plane", type="angle",
                   references=["edges:>X and >Y"], angle=0)["plane"]["id"]
    patron = llamar("create_construction_plane", type="angle",
                    references=["edges:>Y and >Z"], angle=0)["plane"]["id"]
    referencia = copy.deepcopy(sesion.paso(patron).p["refs"])

    # El cero Y es válido tanto sobre la arista vertical como sobre la nueva, paralela a X.
    llamar("edit_feature", feature=patron, params={"eje_0": "Y"})
    esperada = sesion.doc.estado_final.planos[patron].normal.copy()
    assert esperada == pytest.approx((0, 1, 0))

    respuesta = llamar("edit_feature", feature=plano,
                       params={"refs": referencia, "eje_0": "Y"})

    assert respuesta["params"]["eje_0"] == "Y"
    assert sesion.doc.estado_final.planos[plano].normal == pytest.approx(esperada)

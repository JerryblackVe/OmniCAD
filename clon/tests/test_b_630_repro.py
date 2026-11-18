"""B-630: la vista previa de Engrosar se corta en un filete de rosca modelada."""
import pytest

from test_b341_engrosar_filete import test_engrosar_el_filete_no_congela_la_ventana as reproducir_engrosar
from test_b341_engrosar_filete import ventana as ventana


@pytest.mark.xfail(strict=True, reason="B-630", raises=AssertionError)
def test_b630_previa_de_engrosar_el_filete(ventana):
    try:
        reproducir_engrosar(ventana)
    except AssertionError as error:
        if "La vista previa tardaba demasiado y se cortó" not in str(error):
            pytest.fail(f"Falló por otro motivo: {error}")
        raise

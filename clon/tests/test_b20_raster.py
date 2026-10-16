"""B-20: no crear profundidad e índices de toda la caja de un triángulo fino."""
import tracemalloc

import numpy as np

from omnicad.nucleo import render_cpu as rc


def test_triangulo_fino_no_reserva_profundidad_de_toda_su_caja():
    lado = 512
    sx = np.array([[0, 511, 511]], float)
    sy = np.array([[0, 511, 510]], float)
    sz = np.full((1, 3), -0.5)
    tracemalloc.start()
    try:
        z, ids = rc.rasterizar(sx, sy, sz, lado, lado)
        _, pico = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    esperados = np.full((lado, lado), -1, np.int64)
    np.fill_diagonal(esperados[:511, :511], 0)
    np.testing.assert_array_equal(ids.reshape(lado, lado), esperados)
    np.testing.assert_allclose(z[ids >= 0], -0.5, rtol=0, atol=1e-15)
    assert np.isinf(z[ids < 0]).all()
    # Incluye los dos buffers de salida; límite de 40 bytes por píxel para esta escena dispersa.
    assert pico < lado * lado * 40, f"Pico de memoria de la caja dispersa: {pico} bytes"

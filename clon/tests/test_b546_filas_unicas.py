# -*- coding: utf-8 -*-
"""B-546: la previa barata de Extruir (prisma de 1 mm) agrupaba vértices con `np.unique(axis=0)`, 0,13 s por tecla con
los 17 perfiles del llavero; `_inversa_filas` (lexsort) da los mismos grupos 4-6 veces más rápido."""
import numpy as np

from omnicad.nucleo import render_cpu as rc


def test_b546_inversa_filas_igual_a_unique_y_prisma_de_un_perfil_con_agujero():
    rng = np.random.default_rng(7)
    for columnas in (2, 3, 4):
        a = rng.integers(-4, 4, (3000, columnas))
        assert np.array_equal(rc._inversa_filas(a), np.unique(a, axis=0, return_inverse=True)[1].reshape(-1))
    assert rc._inversa_filas(np.zeros((0, 3), np.int64)).shape == (0,)
    # un cuadrado de 10 con un agujero de 4 en el medio, en 8 triángulos: 8 lados de borde (4 afuera y 4 adentro)
    a, b, c, d = (0, 0, 0), (10, 0, 0), (10, 10, 0), (0, 10, 0)
    e, f, g, h = (3, 3, 0), (7, 3, 0), (7, 7, 0), (3, 7, 0)
    tris = np.array([(a, b, f), (a, f, e), (b, c, g), (b, g, f), (c, d, h), (c, h, g), (d, a, e), (d, e, h)], float)
    v, n, seg = rc.prisma_unidad(tris, (0, 0, 1))
    assert len(seg) == 8 * 4 and len(v) == 3 * (2 * 8 + 2 * 8)             # 8 lados de borde; 2 tapas de 8 y 2 por lado
    assert np.allclose(np.linalg.norm(n, axis=1), 1)
    assert (np.abs(n - (0, 0, 1)).max(axis=1) < 1e-6).sum() == 24 == (np.abs(n + (0, 0, 1)).max(axis=1) < 1e-6).sum()

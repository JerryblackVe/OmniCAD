"""Paridad del cálculo Rust con la referencia numpy y la herramienta pública."""
from io import BytesIO

import numpy as np
import pytest
from PIL import Image

from omnicad import api, nativo
from omnicad.nucleo import render_cpu as rc


@pytest.fixture
def motor(monkeypatch):
    monkeypatch.delenv("OMNICAD_SIN_RUST", raising=False)
    if nativo.disponible() is None:
        pytest.skip("Extensión Rust opcional no compilada en este entorno.")
    return nativo.disponible()


def test_forzar_python(monkeypatch):
    monkeypatch.setenv("OMNICAD_SIN_RUST", "1")
    assert nativo.disponible() is None


@pytest.mark.parametrize("base", [0, 17])
def test_rasterizador_paridad_y_desempate(motor, monkeypatch, base):
    rng = np.random.default_rng(18)
    sx = rng.uniform(-30, 80, (64, 3))
    sy = rng.uniform(-20, 60, (64, 3))
    sz = rng.uniform(-1, 1, (64, 3))
    sx[1:4] = sx[0]
    sy[1:4] = sy[0]
    sz[:4] = 0.0
    sx[-2], sy[-2] = 0, 0  # degenerado
    sz[-1] = np.inf
    validos = np.arange(64) % 5 != 4
    z_inicial = np.full(48 * 32, 0.75)
    ids_iniciales = np.full(48 * 32, -1, np.int64)
    rust = rc.rasterizar(sx, sy, sz, 48, 32, validos, z_inicial.copy(), ids_iniciales.copy(), base)
    monkeypatch.setenv("OMNICAD_SIN_RUST", "1")
    python = rc.rasterizar(sx, sy, sz, 48, 32, validos, z_inicial.copy(), ids_iniciales.copy(), base)
    np.testing.assert_array_equal(rust[0], python[0])
    np.testing.assert_array_equal(rust[1], python[1])


def test_sombras_y_oclusion_paridad(motor, monkeypatch):
    rng = np.random.default_rng(19)
    mapa = rc.MapaSombras(np.array([[[0, 0, 0], [5, 0, 0], [0, 5, 0]]]), rc.luces()[0], 32)
    p = rng.uniform(-5, 10, (80, 3))
    n = rc._unit(rng.normal(size=(80, 3)))
    proy, _ = rc.matrices_camara(rc.camara(np.eye(3), [0, 0, 0], 10), 1)
    pv = p - [0, 0, 20]
    zv = rng.uniform(-25, -10, 32 * 32)
    zv[::7] = -np.inf
    sombras = mapa.visibilidad(p, n)
    ao = rc._ssao(pv, n, zv, proy, 32, 32, 2.0)
    monkeypatch.setenv("OMNICAD_SIN_RUST", "1")
    np.testing.assert_array_equal(sombras, mapa.visibilidad(p, n))
    np.testing.assert_allclose(ao, rc._ssao(pv, n, zv, proy, 32, 32, 2.0), rtol=0, atol=1e-12)


def test_herramienta_png_con_rust_y_respaldo(motor, monkeypatch):
    sesion = api.Sesion()
    assert api.llamar(sesion, "create_box", {"length": 24, "width": 24, "height": 30})["ok"]

    def imagen():
        r = api.llamar(sesion, "get_viewport_image", {"width": 96, "height": 64})
        assert r["ok"], r
        return np.asarray(Image.open(BytesIO(r["result"]["image"].png)))

    rust = imagen()
    monkeypatch.setenv("OMNICAD_SIN_RUST", "1")
    np.testing.assert_array_equal(rust, imagen())


def test_entrada_nativa_invalida_no_aborta(motor):
    with pytest.raises(ValueError, match="Dimensiones"):
        motor.rasterizar(np.zeros((1, 2)), np.zeros((1, 2)), np.zeros((1, 2)),
                         np.array([0], np.int64), 2, 2, np.zeros(4), np.zeros(4, np.int64), 0)

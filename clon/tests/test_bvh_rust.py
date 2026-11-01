"""RS-R3: el BVH de Rust da las mismas distancias (1e-9) que los rayos numpy de referencia, y sin el módulo rige numpy."""
import math

import numpy as np
import pytest

from omnicad import nativo
from omnicad.nucleo import revision
from omnicad.ui import visor3d

EPS = 1e-7


@pytest.fixture
def rs(monkeypatch):
    monkeypatch.delenv("OMNICAD_SIN_RUST", raising=False)
    motor = nativo.disponible()
    if not hasattr(motor, "Bvh"):
        pytest.skip("Extensión Rust opcional no compilada (o vieja) en este entorno.")
    return motor


def _sopa(n, semilla=3):
    azar = np.random.default_rng(semilla)
    centros = azar.uniform(-10, 10, (n, 1, 3))
    return centros + azar.uniform(-1.2, 1.2, (n, 3, 3))


def _rayos(n, semilla=4):
    azar = np.random.default_rng(semilla)
    o = azar.uniform(-14, 14, (n, 3))
    d = azar.normal(size=(n, 3))
    return o, d / np.linalg.norm(d, axis=1, keepdims=True)


def _caja_triangulada(lado=2.0):
    """Cubo [0, lado]³ en 12 triángulos (cada cara partida en su diagonal)."""
    v = np.array([[x, y, z] for z in (0, lado) for y in (0, lado) for x in (0, lado)], float)
    caras = [(0, 1, 3), (0, 3, 2), (4, 6, 7), (4, 7, 5), (0, 4, 5), (0, 5, 1), (2, 3, 7), (2, 7, 6), (0, 2, 6), (0, 6, 4),
             (1, 5, 7), (1, 7, 3)]
    return v[np.array(caras)]


def _numpy_y_rust(monkeypatch, o, d, tris, eps=EPS):
    monkeypatch.setenv("OMNICAD_SIN_RUST", "1")
    ref = revision.primer_choque(o, d, tris, eps)
    monkeypatch.delenv("OMNICAD_SIN_RUST")
    return ref, revision.primer_choque(o, d, tris, eps)


def _igual(ref, rust, indices=True):
    (t0, i0), (t1, i1) = ref, rust
    assert np.array_equal(np.isfinite(t0), np.isfinite(t1))
    ok = np.isfinite(t0)
    assert np.abs(t0[ok] - t1[ok]).max(initial=0.0) < 1e-9
    assert np.array_equal(i0 == -1, i1 == -1)
    if indices:
        assert np.array_equal(i0, i1)


def test_primer_choque_igual_a_numpy_con_aciertos_y_fallos(rs, monkeypatch):
    tris = _sopa(400)
    o, d = _rayos(1500)
    ref, rust = _numpy_y_rust(monkeypatch, o, d, tris)
    hay = np.isfinite(ref[0])
    assert 100 < hay.sum() < len(o) - 100               # el caso mezcla rayos que tocan y rayos que no
    _igual(ref, rust)
    assert rust[0].dtype == np.float64 and rust[1].dtype == np.int64


def test_primer_choque_en_bordes_y_vertices(rs, monkeypatch):
    tris = _caja_triangulada()
    # sobre la diagonal de la cara z=0, sobre una arista, sobre un vértice, apenas fuera y rozando
    o = np.array([[1.0, 1.0, 5], [1.0, 0.0, 5], [0.0, 0.0, 5], [2.0, 2.0, 5], [-1e-12, 1.0, 5], [2.0 + 5e-10, 1.0, 5],
                  [3.0, 1.0, 5], [1.0, 1.0, -5]])
    d = np.tile([0.0, 0.0, -1.0], (len(o), 1))
    ref, rust = _numpy_y_rust(monkeypatch, o, d, tris)
    assert np.all(np.isfinite(ref[0][:6])) and not np.isfinite(ref[0][6])
    _igual(ref, rust, indices=False)
    assert np.all(rust[1][:6] >= 0) and rust[1][6] == -1
    assert not np.isfinite(rust[0][7])                   # el último rayo está debajo del cubo y se aleja


def test_primer_choque_rayos_paralelos_y_hacia_atras(rs, monkeypatch):
    tris = _caja_triangulada()
    o = np.array([[1.0, 1.0, 0.0], [1.0, 1.0, 5.0], [-3.0, 1.0, 1.0], [1.0, 1.0, 1.0]])
    d = np.array([[1.0, 0, 0], [0, 0, 1.0], [1.0, 0, 0], [0, 0, 1.0]])    # paralelo a la cara z=0 · se aleja · entra · dentro
    ref, rust = _numpy_y_rust(monkeypatch, o, d, tris)
    _igual(ref, rust, indices=False)
    assert not np.isfinite(rust[0][1]) and rust[0][2] == pytest.approx(3.0) and rust[0][3] == pytest.approx(1.0)


def test_primer_choque_vacios_y_degenerados(rs, monkeypatch):
    o, d = _rayos(5)
    t, i = revision.primer_choque(o, d, np.zeros((0, 3, 3)), EPS)
    assert np.all(np.isinf(t)) and np.all(i == -1)
    t, i = revision.primer_choque(np.zeros((0, 3)), np.zeros((0, 3)), _sopa(4), EPS)
    assert len(t) == 0 and len(i) == 0
    plano = np.array([[[0.0, 0, 0], [1, 0, 0], [2, 0, 0]], [[0.0, 0, 1], [1, 0, 1], [0, 1, 1]]])   # colineal · sano
    ref, rust = _numpy_y_rust(monkeypatch, np.array([[0.2, 0.2, 5.0], [1.0, 0.0, 5.0]]), np.tile([0.0, 0, -1], (2, 1)), plano)
    _igual(ref, rust)
    assert rust[1][0] == 1


def test_empate_de_triangulos_iguales_elige_el_primero(rs, monkeypatch):
    base = _caja_triangulada()
    tris = np.concatenate([base[:2], base[:2]])           # cada triángulo de la cara z=0 repetido
    o = np.array([[0.5, 0.25, 5.0], [1.5, 1.0, 5.0]])
    d = np.tile([0.0, 0, -1.0], (2, 1))
    ref, rust = _numpy_y_rust(monkeypatch, o, d, tris)
    _igual(ref, rust)
    assert set(rust[1]) <= {0, 1}


def test_espesores_igual_con_y_sin_rust(rs, monkeypatch):
    from omnicad.nucleo import geometria as geo
    from omnicad.nucleo import malla as ml
    cuerpo = geo.caja(30, 20, 4)
    m = ml.desde_brep(cuerpo)
    monkeypatch.setenv("OMNICAD_SIN_RUST", "1")
    ref = revision.espesores(m, muestras=500)
    monkeypatch.delenv("OMNICAD_SIN_RUST")
    rust = revision.espesores(m, muestras=500)
    assert np.allclose(ref[1], rust[1], atol=1e-9, equal_nan=True)
    assert np.array_equal(ref[0], rust[0]) and np.array_equal(ref[3], rust[3]) and np.nanmin(rust[1]) == pytest.approx(4.0)


def test_bvh_construccion_valida_la_forma(rs):
    with pytest.raises((TypeError, ValueError)):
        rs.Bvh(np.zeros((4, 3)))
    with pytest.raises(ValueError):
        rs.Bvh(np.zeros((4, 3, 3))[:, :, ::-1])             # no contiguo
    bvh = rs.Bvh(np.zeros((0, 3, 3)))
    assert len(bvh) == 0
    with pytest.raises(ValueError):
        rs.Bvh(_sopa(4)).primer_choque(np.zeros((3, 3)), np.zeros((2, 3)), 1e-9, 0.0, 0.0)
    t, i = bvh.primer_choque(np.zeros((2, 3)), np.array([[0.0, 0, 1]]), 1e-9, 0.0, 0.0)   # una dirección para todos
    assert np.all(np.isinf(t)) and np.all(i == -1)


def test_primer_rayo_triangulos_igual_a_min_y_argmin(rs, monkeypatch):
    tris = _sopa(500, semilla=9)
    o, d = _rayos(200, semilla=10)
    cache = {}
    for oi, di in zip(o, d, strict=True):
        ts = visor3d.rayo_triangulos(oi, di, tris)
        t, i = visor3d.primer_rayo_triangulos(oi, di, tris, cache, "k")
        if math.isinf(ts.min()):
            assert math.isinf(t) and i == -1
        else:
            assert t == pytest.approx(ts.min(), abs=1e-9) and i == int(np.argmin(ts))
    assert len(cache) == 1                                # un solo BVH para los 200 rayos
    bvh = cache["k"]
    visor3d.primer_rayo_triangulos(o[0], d[0], tris, cache, "k")
    assert cache["k"] is bvh


def test_primer_rayo_triangulos_sin_rust_usa_numpy(monkeypatch):
    monkeypatch.setenv("OMNICAD_SIN_RUST", "1")
    tris = _caja_triangulada()
    cache = {}
    t, i = visor3d.primer_rayo_triangulos(np.array([1.0, 0.5, 5]), np.array([0.0, 0, -1]), tris, cache, "k")
    assert t == pytest.approx(3.0) and tris[i][:, 2].max() == 2.0 and not cache
    t, i = visor3d.primer_rayo_triangulos(np.array([9.0, 9, 5]), np.array([0.0, 0, -1]), tris, cache, "k")
    assert math.isinf(t) and i == -1
    # float32 como en las mallas del visor: mismo resultado que con float64
    t32, _ = visor3d.primer_rayo_triangulos(np.array([1.0, 0.5, 5]), np.array([0.0, 0, -1]), tris.astype(np.float32), cache, "k")
    assert t32 == pytest.approx(3.0)


def test_pyd_viejo_sin_bvh_cae_a_numpy(monkeypatch):
    monkeypatch.setattr(nativo, "disponible", lambda: object())
    tris = _caja_triangulada()
    t, i = revision.primer_choque(np.array([[1.0, 0.5, 5]]), np.array([[0.0, 0, -1]]), tris, EPS)
    assert t[0] == pytest.approx(3.0) and i[0] >= 0

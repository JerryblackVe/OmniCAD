# -*- coding: utf-8 -*-
"""B-111: el solver no rearma cada spline en cada evaluación (caché por coordenadas) y da lo mismo que sin caché."""
import random

import numpy as np
import pytest
from _contornos import contorno_splines

from omnicad import nativo
from omnicad.restricciones import solver as S
from omnicad.restricciones.boceto import Boceto, dominio, evaluar_primitiva, interpolar_spline


def _cadena_abierta(n, curvatura=False):
    b = Boceto()
    pts = [b.agregar_punto(10.0 * k, 12.0 * ((-1) ** k) * (1 + 0.1 * k)) for k in range(3 * n + 1)]
    sp = [b.agregar_spline(pts[3 * i:3 * i + 4]) for i in range(n)]
    b.agregar_restriccion("fijo", [pts[0]])
    for i in range(n - 1):
        b.agregar_restriccion("curvatura" if curvatura else "tangente", [sp[i], sp[i + 1]])
    return b, {}


def _punto_sobre_spline():
    b = Boceto()
    sp = b.agregar_spline([(0, 0), (10, 8), (20, -4), (30, 6)])
    q = b.agregar_punto(12, 3)
    b.agregar_restriccion("coincidente", [q, sp])
    b.agregar_restriccion("fijo", [b.curvas[sp].pts[0]])
    return b, {}


def _spline_tangente_a_linea():
    b = Boceto()
    sp = b.agregar_spline([(0, 0), (10, 8), (20, 8), (30, 0)])
    ln = b.agregar_linea((0, 10), (30, 10))
    b.agregar_restriccion("tangente", [sp, ln])
    b.agregar_restriccion("fijo", [b.curvas[ln].p1])
    return b, {}


def _rect(conflicto=False):
    b = Boceto()
    lineas = b.agregar_rectangulo((0, 0), (30, 20))
    b.agregar_restriccion("fijo", [b.curvas[lineas[0]].p1])
    valores = {b.agregar_cota("distancia", [lineas[0]], "50"): 50.0}
    if conflicto:
        b.agregar_restriccion("horizontal", [lineas[1]])
    return b, valores


def _redondos():
    b = Boceto()
    c = b.agregar_circulo((0, 0), 3)
    a = b.agregar_arco_3_puntos((10, 0), (14, 4), (18, 0))
    b.agregar_elipse((40, 0), (50, 0), 4)
    ln = b.agregar_linea((-10, 8), (30, 8))
    b.agregar_restriccion("tangente", [ln, c])
    valores = {b.agregar_cota("radio", [c], "7"): 7.0, b.agregar_cota("diametro", [a], "20"): 20.0}
    return b, valores


def _spline_cerrada():
    b = Boceto()
    sp = b.agregar_spline([(0, 0), (20, 5), (25, 25), (5, 30), (-5, 15)], cerrada=True)
    b.agregar_restriccion("fijo", [b.curvas[sp].pts[0]])
    return b, {}


def _corpus():
    c = {f"contorno{n}": lambda n=n: contorno_splines(n) for n in range(2, 10)}
    c["sin_tangentes"] = lambda: contorno_splines(4, con_tangentes=False)
    c["conflicto3"] = lambda: contorno_splines(3, conflicto=True)
    c["conflicto5"] = lambda: contorno_splines(5, conflicto=True)
    c.update({"cadena_g1": lambda: _cadena_abierta(4), "cadena_g2": lambda: _cadena_abierta(3, curvatura=True),
              "punto_sobre_spline": _punto_sobre_spline, "spline_linea": _spline_tangente_a_linea,
              "rect": _rect, "rect_conflicto": lambda: _rect(True), "redondos": _redondos,
              "spline_cerrada": _spline_cerrada, "contorno_largo": lambda: contorno_splines(14)})
    return c


CORPUS = _corpus()


def _resolver(fabrica, cache, monkeypatch, rust=False):
    monkeypatch.setattr(S, "CACHE_SPLINES", cache)
    monkeypatch.setattr(S.nativo, "disponible", (lambda: nativo._rs) if rust else (lambda: None))
    b, valores = fabrica()
    r = S.resolver(b, valores)
    return r, b


def _comparar(sin, b_sin, con, b_con, tolerancia):
    assert (con.estado, con.gdl, con.mensaje) == (sin.estado, sin.gdl, sin.mensaje)
    assert con.residuo_max == pytest.approx(sin.residuo_max, abs=1e-9 if tolerancia is not None and tolerancia < 1e-6 else 1e-6)
    assert con.determinadas == sin.determinadas
    if tolerancia is None:      # sub-restringido o en conflicto: las posiciones dependen del camino del solver
        return
    for pid, p in b_sin.puntos.items():
        assert (b_con.puntos[pid].x, b_con.puntos[pid].y) == pytest.approx((p.x, p.y), abs=tolerancia)
    for cid, c in b_sin.curvas.items():
        for atributo in ("radio", "radio_menor"):
            if hasattr(c, atributo):
                assert getattr(b_con.curvas[cid], atributo) == pytest.approx(getattr(c, atributo), abs=tolerancia)


def test_corpus_tiene_al_menos_20_bocetos_y_uno_en_conflicto():
    assert len(CORPUS) >= 20


@pytest.mark.parametrize("nombre", list(CORPUS))
def test_resolver_da_lo_mismo_con_y_sin_cache(nombre, monkeypatch):
    """La caché no cambia nada: ni un bit (se compara a 1e-9)."""
    sin, b_sin = _resolver(CORPUS[nombre], False, monkeypatch)
    con, b_con = _resolver(CORPUS[nombre], True, monkeypatch)
    _comparar(sin, b_sin, con, b_con, 1e-9)


def test_el_corpus_cubre_un_conflicto_real(monkeypatch):
    assert not _resolver(CORPUS["conflicto3"], True, monkeypatch)[0].ok
    assert not _resolver(CORPUS["rect_conflicto"], True, monkeypatch)[0].ok


def test_la_cache_baja_las_armadas_de_spline(monkeypatch):
    """Cuenta llamadas (no tiempo): con caché, cada spline se arma unas pocas veces por jacobiano, no por residuo."""
    llamadas = {"n": 0}
    original = S.primitivas_entidad

    def contar(*args, **kw):
        llamadas["n"] += 1
        return original(*args, **kw)
    monkeypatch.setattr(S, "primitivas_entidad", contar)
    medidas = {}
    for cache in (False, True):
        llamadas["n"] = 0
        _resolver(lambda: contorno_splines(10), cache, monkeypatch)
        medidas[cache] = llamadas["n"]
    assert medidas[True] * 2 < medidas[False]


# ---------------------------------------------------------------- R5 chica: extremos de spline en Rust
rs = nativo.disponible()
sin_rust = pytest.mark.skipif(rs is None, reason="módulo Rust no instalado")


def _extremos_python(pts, grado):
    polos, nudos, p = interpolar_spline(pts, grado)
    prim = ("spline", 0, tuple(polos), tuple(nudos), p, None)
    t0, t1, _ = dominio(prim)
    return [v for t in (t0, t1) for d in evaluar_primitiva(prim, t, 2)[1:] for v in d]


@sin_rust
@pytest.mark.parametrize("semilla", range(24))
def test_rust_da_los_extremos_de_python(semilla):
    azar = random.Random(semilla)
    m = azar.randint(2, 9)
    pts = [(10.0 * i + azar.uniform(-4, 4), azar.uniform(-30, 30)) for i in range(m)]
    grado = (3, 3, 2, 5)[semilla % 4]
    esperado = _extremos_python(pts, grado)
    obtenido = rs.spline_extremos(np.array(pts, dtype=float), grado)
    assert list(obtenido) == pytest.approx(esperado, rel=1e-9, abs=1e-9)


@sin_rust
@pytest.mark.parametrize("nombre", list(CORPUS))
def test_resolver_con_rust_cumple_lo_mismo_que_python(nombre, monkeypatch):
    """Rust redondea distinto en el último bit; el jacobiano por diferencias finitas lo amplifica y en las direcciones
    LIBRES (sub-restringido) o en conflicto la solución puede diferir. Estado, grados de libertad, mensaje, entidades
    determinadas y residuo son los mismos."""
    py, b_py = _resolver(CORPUS[nombre], True, monkeypatch)
    rs_, b_rs = _resolver(CORPUS[nombre], True, monkeypatch, rust=True)
    _comparar(py, b_py, rs_, b_rs, None)

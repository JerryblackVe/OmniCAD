# -*- coding: utf-8 -*-
"""
Retícula volumétrica [Solid > Modify > Volumetric Lattice de Fusion]: llena un sólido con una estructura interna por celdas.

Formas de celda:
  - "cross" (Cross): tres barras, una por eje, que se cruzan en el centro de la celda;
  - "x_cell" (X-Cell): las cuatro diagonales de la celda;
  - "gyroid", "schwarz_p", "schwarz_d": superficies mínimas triplemente periódicas, engrosadas hasta la solidez pedida.
Las dos primeras salen como sólido (barras cilíndricas unidas y recortadas al cuerpo); las otras tres, como malla
(cuerpo de malla): el campo se muestrea en una grilla y se tria con tetraedros marchantes, así que el borde del cuerpo queda
escalonado al paso de la grilla.

La solidez es la fracción de volumen de material (0 a 1, p. ej. 0,3 = 30 %): para las barras se busca el diámetro que da esa
fracción en una celda; para las superficies, el espesor que deja esa fracción de volumen en el campo.
Tamaño de celda: (sx, sy, sz) en mm, a partir de la esquina mínima de la caja del cuerpo.
"""
import math

import numpy as np

from . import geometria as geo

FORMAS_BARRAS = ("cross", "x_cell")
FORMAS_TPMS = ("gyroid", "schwarz_p", "schwarz_d")
FORMAS = FORMAS_BARRAS + FORMAS_TPMS
MAXIMO_BARRAS = 800
MAXIMO_MUESTRAS = 4_000_000


# ---------------------------------------------------------------- barras
def _celda(forma, d, sx, sy, sz):
    """Un sólido [0,sx]×[0,sy]×[0,sz] con las barras de diámetro d de la forma de celda."""
    r = d / 2
    caja = geo.caja(sx, sy, sz)
    if forma == "cross":
        barras = [geo.cilindro(r, sx, (0, sy / 2, sz / 2), (1, 0, 0)), geo.cilindro(r, sy, (sx / 2, 0, sz / 2), (0, 1, 0)),
                  geo.cilindro(r, sz, (sx / 2, sy / 2, 0), (0, 0, 1))]
    else:
        barras = []
        for x, y in ((0, 0), (sx, 0), (0, sy), (sx, sy)):
            a = np.array([x, y, 0.0])
            b = np.array([sx - x, sy - y, sz])
            largo = float(np.linalg.norm(b - a))
            barras.append(geo.cilindro(r, largo, tuple(a), tuple((b - a) / largo)))
    return geo.booleano(geo.unir_todos(barras), caja, "intersecar")


def diametro_para(forma, solidez, sx, sy, sz):
    """Diámetro de barra que deja la fracción de material `solidez` en una celda (bisección sobre la celda real)."""
    objetivo = solidez * sx * sy * sz
    lo, hi = 1e-4 * min(sx, sy, sz), 0.45 * min(sx, sy, sz)
    if geo.volumen(_celda(forma, hi, sx, sy, sz)) < objetivo:
        raise geo.ErrorGeometria("Con ese tamaño de celda las barras no llegan a esa solidez: bajá la solidez o achicá la celda.")
    for _ in range(14):
        mid = (lo + hi) / 2
        if geo.volumen(_celda(forma, mid, sx, sy, sz)) < objetivo:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def _barras(forma, cuerpo_caja, d, sx, sy, sz):
    (x0, y0, z0), (x1, y1, z1) = cuerpo_caja
    nx, ny, nz = (max(1, math.ceil((b - a) / s - 1e-9)) for a, b, s in ((x0, x1, sx), (y0, y1, sy), (z0, z1, sz)))
    r = d / 2
    barras = []
    if forma == "cross":
        total = ny * nz + nx * nz + nx * ny
        if total > MAXIMO_BARRAS:
            raise geo.ErrorGeometria(f"La retícula tendría {total} barras (máximo {MAXIMO_BARRAS}): agrandá la celda.")
        for j in range(ny):
            for k in range(nz):
                barras.append(geo.cilindro(r, nx * sx, (x0, y0 + (j + .5) * sy, z0 + (k + .5) * sz), (1, 0, 0)))
        for i in range(nx):
            for k in range(nz):
                barras.append(geo.cilindro(r, ny * sy, (x0 + (i + .5) * sx, y0, z0 + (k + .5) * sz), (0, 1, 0)))
        for i in range(nx):
            for j in range(ny):
                barras.append(geo.cilindro(r, nz * sz, (x0 + (i + .5) * sx, y0 + (j + .5) * sy, z0), (0, 0, 1)))
    else:
        if 4 * nx * ny * nz > MAXIMO_BARRAS:
            raise geo.ErrorGeometria(f"La retícula tendría {4 * nx * ny * nz} barras (máximo {MAXIMO_BARRAS}): agrandá la celda.")
        for i in range(nx):
            for j in range(ny):
                for k in range(nz):
                    for dx, dy in ((0, 0), (1, 0), (0, 1), (1, 1)):
                        a = np.array([x0 + (i + dx) * sx, y0 + (j + dy) * sy, z0 + k * sz])
                        b = np.array([x0 + (i + 1 - dx) * sx, y0 + (j + 1 - dy) * sy, z0 + (k + 1) * sz])
                        largo = float(np.linalg.norm(b - a))
                        barras.append(geo.cilindro(r, largo, tuple(a), tuple((b - a) / largo)))
    return barras


def reticula_barras(forma, tipo_celda, solidez, sx, sy, sz):
    """Sólido: las barras de la retícula recortadas al cuerpo `forma`."""
    d = diametro_para(tipo_celda, solidez, sx, sy, sz)
    herramienta = geo.unir_todos(_barras(tipo_celda, geo.caja_envolvente(forma), d, sx, sy, sz))
    resultado = geo.booleano(forma, herramienta, "intersecar")
    if geo.sin_volumen(resultado):
        raise geo.ErrorGeometria("La retícula no deja material dentro del cuerpo: probá con otra celda.")
    return resultado, d


# ---------------------------------------------------------------- superficies mínimas
def campo(tipo, x, y, z, sx, sy, sz):
    kx, ky, kz = 2 * math.pi / sx, 2 * math.pi / sy, 2 * math.pi / sz
    X, Y, Z = kx * x, ky * y, kz * z
    if tipo == "gyroid":
        return np.sin(X) * np.cos(Y) + np.sin(Y) * np.cos(Z) + np.sin(Z) * np.cos(X)
    if tipo == "schwarz_p":
        return np.cos(X) + np.cos(Y) + np.cos(Z)
    return (np.sin(X) * np.sin(Y) * np.sin(Z) + np.sin(X) * np.cos(Y) * np.cos(Z) + np.cos(X) * np.sin(Y) * np.cos(Z)
            + np.cos(X) * np.cos(Y) * np.sin(Z))


def espesor_para(tipo, solidez):
    """Umbral t tal que la fracción de volumen con |campo| ≤ t es `solidez` (en un periodo de la superficie)."""
    n = np.linspace(0.0, 1.0, 48, endpoint=False) + 0.5 / 48
    x, y, z = np.meshgrid(n, n, n, indexing="ij")
    return float(np.quantile(np.abs(campo(tipo, x, y, z, 1.0, 1.0, 1.0)), solidez))


def _dentro(forma, xs, ys, zs):
    """Máscara (nx, ny, nz) de los nodos de la grilla que están dentro del sólido: un rayo vertical por columna."""
    from OCP.IntCurvesFace import IntCurvesFace_ShapeIntersector
    from OCP.gp import gp_Dir, gp_Lin, gp_Pnt
    inter = IntCurvesFace_ShapeIntersector()
    inter.Load(forma, 1e-7)
    masc = np.zeros((len(xs), len(ys), len(zs)), bool)
    z0 = zs[0] - 1.0
    for i, x in enumerate(xs):
        for j, y in enumerate(ys):
            inter.Perform(gp_Lin(gp_Pnt(float(x), float(y), float(z0)), gp_Dir(0, 0, 1)), 0.0, float(zs[-1] - z0) + 2.0)
            if not inter.IsDone() or inter.NbPnt() < 2:
                continue
            cortes = sorted(z0 + inter.WParameter(k) for k in range(1, inter.NbPnt() + 1))
            unicos = [c for n, c in enumerate(cortes) if n == 0 or c - cortes[n - 1] > 1e-7]
            for a, b in zip(unicos[0::2], unicos[1::2], strict=False):
                masc[i, j, (zs > a) & (zs < b)] = True
    return masc


_TETRAEDROS = ((0, 5, 1, 6), (0, 1, 2, 6), (0, 2, 3, 6), (0, 3, 7, 6), (0, 7, 4, 6), (0, 4, 5, 6))
_VERTICES = ((0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0), (0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1))


def _triangular_losa(g, pos, i):
    """Triángulos de la superficie g = 0 en la losa de celdas entre los planos x[i] y x[i+1] (tetraedros marchantes).
    g (nx,ny,nz) y pos (nx,ny,nz,3). Devuelve un arreglo (M, 3, 3)."""
    ny, nz = g.shape[1] - 1, g.shape[2] - 1
    jj, kk = np.meshgrid(np.arange(ny), np.arange(nz), indexing="ij")
    jj, kk = jj.ravel(), kk.ravel()
    esquinas_g = np.stack([g[i + dx, jj + dy, kk + dz] for dx, dy, dz in _VERTICES], axis=1)       # (C, 8)
    esquinas_p = np.stack([pos[i + dx, jj + dy, kk + dz] for dx, dy, dz in _VERTICES], axis=1)      # (C, 8, 3)
    cruza = (esquinas_g.min(axis=1) < 0) & (esquinas_g.max(axis=1) >= 0)
    if not cruza.any():
        return np.zeros((0, 3, 3))
    esquinas_g, esquinas_p = esquinas_g[cruza], esquinas_p[cruza]
    salida = []
    for tet in _TETRAEDROS:
        v, p = esquinas_g[:, tet], esquinas_p[:, tet]                                               # (C,4), (C,4,3)
        dentro = v < 0
        n_in = dentro.sum(axis=1)
        orden = np.argsort(~dentro, axis=1, kind="stable")                                           # primero los de adentro
        v = np.take_along_axis(v, orden, axis=1)
        p = np.take_along_axis(p, orden[:, :, None], axis=1)

        def corte(a, b, v=v, p=p, filas=None):
            va, vb = v[filas, a], v[filas, b]
            t = (va / (va - vb))[:, None]
            return p[filas, a] + (p[filas, b] - p[filas, a]) * t
        for caso in (1, 2, 3):
            f = np.nonzero(n_in == caso)[0]
            if not len(f):
                continue
            if caso == 1:
                tri = np.stack([corte(np.zeros(len(f), int), np.full(len(f), b), filas=f) for b in (1, 2, 3)], axis=1)
                salida.append(_orientar(tri, p[f, :1].mean(axis=1)))
            elif caso == 3:
                tri = np.stack([corte(np.full(len(f), a), np.full(len(f), 3), filas=f) for a in (0, 1, 2)], axis=1)
                salida.append(_orientar(tri, p[f, :3].mean(axis=1)))
            else:
                z = np.zeros(len(f), int)
                q = [corte(z + a, z + b, filas=f) for a, b in ((0, 2), (0, 3), (1, 3), (1, 2))]
                ref = p[f, :2].mean(axis=1)
                salida.append(_orientar(np.stack([q[0], q[1], q[2]], axis=1), ref))
                salida.append(_orientar(np.stack([q[0], q[2], q[3]], axis=1), ref))
    return np.concatenate(salida) if salida else np.zeros((0, 3, 3))


def _orientar(tri, referencia_dentro):
    """Da vuelta los triángulos cuya normal apunta hacia el material (hacia `referencia_dentro`)."""
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    hacia_dentro = np.einsum("ij,ij->i", n, referencia_dentro - tri.mean(axis=1)) > 0
    tri = tri.copy()
    tri[hacia_dentro] = tri[hacia_dentro][:, ::-1]
    return tri


def reticula_malla(forma, tipo_celda, solidez, sx, sy, sz, resolucion=8):
    """Cuerpo de malla con la superficie mínima engrosada, recortada al sólido `forma`. Devuelve (Malla, espesor)."""
    from .malla import Malla
    (x0, y0, z0), (x1, y1, z1) = geo.caja_envolvente(forma)
    h = min(sx, sy, sz) / max(4, int(resolucion))
    xs = np.arange(x0 - h, x1 + 1.5 * h, h)
    ys = np.arange(y0 - h, y1 + 1.5 * h, h)
    zs = np.arange(z0 - h, z1 + 1.5 * h, h)
    if len(xs) * len(ys) * len(zs) > MAXIMO_MUESTRAS:
        raise geo.ErrorGeometria(f"La grilla tendría más de {MAXIMO_MUESTRAS:,} muestras: agrandá la celda o bajá la "
                                 "resolución.".replace(",", "."))
    t = espesor_para(tipo_celda, solidez)
    X, Y, Z = np.meshgrid(xs - x0, ys - y0, zs - z0, indexing="ij")
    g = np.abs(campo(tipo_celda, X, Y, Z, sx, sy, sz)) - t
    g[~_dentro(forma, xs, ys, zs)] = 1.0                                       # fuera del cuerpo no hay material
    pos = np.stack(np.meshgrid(xs, ys, zs, indexing="ij"), axis=-1)
    tris = [t_ for i in range(len(xs) - 1) if len(t_ := _triangular_losa(g, pos, i))]
    if not tris:
        raise geo.ErrorGeometria("La retícula no deja material dentro del cuerpo: probá con otra celda o más solidez.")
    return Malla.desde_triangulos(np.concatenate(tris)), t

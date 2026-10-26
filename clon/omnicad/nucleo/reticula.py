# -*- coding: utf-8 -*-
"""
Retícula volumétrica [Solid > Modify > Volumetric Lattice de Fusion]: llena un sólido o una malla cerrada con una
estructura interna por celdas.

Formas de celda:
  - "cross" (Cross): tres barras, una por eje, que se cruzan en el centro de la celda;
  - "x_cell" (X-Cell): las cuatro diagonales de la celda;
  - "x_cell_25d" (2.5D X-Cell): las dos diagonales de la celda en XY, como paredes extruidas en Z;
  - "custom" (Custom): barras a medida, segmentos en coordenadas de la celda (0 a 1 en cada eje);
  - "gyroid", "schwarz_p", "schwarz_d": superficies mínimas triplemente periódicas, engrosadas hasta la solidez pedida.
Las cuatro primeras salen como sólido (barras o paredes unidas y recortadas al cuerpo; una malla cerrada se convierte
antes a B-rep); las otras tres, como cuerpo de malla: el campo se muestrea en una grilla y se tria con tetraedros
marchantes. El borde del cuerpo entra en el campo como distancia con signo, así que queda interpolado, no escalonado.

La solidez es la fracción de volumen de material (0 a 1): para las barras se busca el diámetro (o el espesor de pared)
que da esa fracción en una celda; para las superficies, el espesor que deja esa fracción de volumen en el campo.
La solidez puede variar punto a punto (`campo_solidez`): en gradiente a lo largo de una ruta y con una zona de desfase
(cerca de caras, aristas o puntos) que tiene su propia solidez y una distancia de mezcla. Con solidez variable las
barras son troncos de cono con el radio de cada nodo.
`Rejilla`: tamaño de celda (sx, sy, sz) en mm, a partir de la esquina mínima de la caja del cuerpo, más un
desplazamiento y un giro (Move / Rotate de Fusion).
"""
import math

import numpy as np

from . import geometria as geo

FORMAS_BARRAS = ("cross", "x_cell", "x_cell_25d", "custom")
FORMAS_TPMS = ("gyroid", "schwarz_p", "schwarz_d")
FORMAS = FORMAS_BARRAS + FORMAS_TPMS
MAXIMO_BARRAS = 800
MAXIMO_MUESTRAS = 4_000_000
MAXIMO_PUNTOS = 3_000_000
SEGMENTOS = {
    "cross": (((0, .5, .5), (1, .5, .5)), ((.5, 0, .5), (.5, 1, .5)), ((.5, .5, 0), (.5, .5, 1))),
    "x_cell": (((0, 0, 0), (1, 1, 1)), ((1, 0, 0), (0, 1, 1)), ((0, 1, 0), (1, 0, 1)), ((1, 1, 0), (0, 0, 1))),
    "x_cell_25d": (((0, 0, 0), (1, 1, 0)), ((1, 0, 0), (0, 1, 0))),            # paredes: segmento en XY extruido en Z
}


# ---------------------------------------------------------------- rejilla y solidez
def _rotacion(rx, ry, rz):
    """Matriz Rz·Ry·Rx (grados)."""
    cx, sx_, cy, sy_, cz, sz_ = (f(math.radians(a)) for a in (rx, ry, rz) for f in (math.cos, math.sin))
    return (np.array([[cz, -sz_, 0], [sz_, cz, 0], [0, 0, 1]]) @ np.array([[cy, 0, sy_], [0, 1, 0], [-sy_, 0, cy]])
            @ np.array([[1, 0, 0], [0, cx, -sx_], [0, sx_, cx]]))


class Rejilla:
    """Celdas de la retícula: tamaño, origen (esquina de la celda 0) y giro de las celdas."""

    def __init__(self, origen, tamano, desplazamiento=(0, 0, 0), giro=(0, 0, 0)):
        self.tam = np.array(tamano, float)
        if self.tam.min() <= 0:
            raise geo.ErrorGeometria("El tamaño de celda es positivo.")
        self.R = _rotacion(*giro)
        self.origen = np.asarray(origen, float) + np.asarray(desplazamiento, float)

    def a_local(self, p):
        return (np.asarray(p, float) - self.origen) @ self.R

    def a_mundo(self, q):
        return self.origen + np.asarray(q, float) @ self.R.T


def _parametro_en_ruta(p, P):
    """Fracción de largo (0 a 1) del punto de la polilínea P más cercano a cada punto de p."""
    if len(P) > 65:
        P = P[np.unique(np.linspace(0, len(P) - 1, 65).round().astype(int))]
    a, ab = P[:-1], P[1:] - P[:-1]
    largo = np.linalg.norm(ab, axis=1)
    acumulado = np.concatenate([[0.0], np.cumsum(largo)])
    if acumulado[-1] <= 1e-9:
        raise geo.ErrorGeometria("La ruta del gradiente no tiene largo.")
    salida = np.empty(len(p))
    for i in range(0, len(p), 5000):
        q = p[i:i + 5000, None, :]
        t = np.clip(np.einsum("nkj,kj->nk", q - a, ab) / np.maximum(largo ** 2, 1e-300), 0, 1)
        k = (((a + t[..., None] * ab) - q) ** 2).sum(-1).argmin(1)
        salida[i:i + 5000] = (acumulado[k] + t[np.arange(len(k)), k] * largo[k]) / acumulado[-1]
    return salida


def campo_solidez(solidez, solidez_final=None, ruta=None, zona=None, desfase=0.0, solidez_zona=1.0, mezcla=0.0):
    """Función puntos (N,3) → solidez (N,). `solidez_final` con `ruta` (polilínea Kx3): gradiente lineal por el largo
    de la ruta (Gradient Along Path). `zona` (puntos Mx3): hasta `desfase` mm de ella la solidez es `solidez_zona`, y en
    los `mezcla` mm siguientes pasa de a poco a la del resto (Offset + Blend Distance)."""
    if solidez_final is not None and (ruta is None or len(ruta) < 2):
        raise geo.ErrorGeometria("La solidez en gradiente necesita una ruta: una arista o curva, o dos puntos.")
    arbol = None
    if zona is not None and len(zona):
        from scipy.spatial import cKDTree
        arbol = cKDTree(np.asarray(zona, float))

    def solidez_en(p):
        p = np.asarray(p, float).reshape(-1, 3)
        s = np.full(len(p), float(solidez))
        if solidez_final is not None:
            s += (solidez_final - solidez) * _parametro_en_ruta(p, np.asarray(ruta, float))
        if arbol is not None:
            d = arbol.query(p)[0]
            w = np.clip((d - desfase) / mezcla, 0, 1) if mezcla > 0 else (d > desfase).astype(float)
            s = solidez_zona + (s - solidez_zona) * w
        return np.clip(s, 0.0, 1.0)
    return solidez_en


def _muestrear_triangulos(tris, paso):
    """Puntos sobre los triángulos, separados ≈ `paso` (vértices incluidos)."""
    tris = np.asarray(tris, float).reshape(-1, 3, 3)
    n = np.maximum(1, np.ceil(np.linalg.norm(tris - np.roll(tris, 1, axis=1), axis=2).max(axis=1) / paso)).astype(int)
    if ((n + 1) * (n + 2) // 2).sum() > MAXIMO_PUNTOS:
        raise geo.ErrorGeometria("La superficie es demasiado grande para la celda: agrandá la celda.")
    salida = []
    for k in np.unique(n):
        i, j = np.meshgrid(np.arange(k + 1), np.arange(k + 1), indexing="ij")
        m = i + j <= k
        u, v = (i[m] / k)[:, None], (j[m] / k)[:, None]
        t = tris[n == k][:, None]
        salida.append((t[..., 0, :] * (1 - u - v) + t[..., 1, :] * u + t[..., 2, :] * v).reshape(-1, 3))
    return np.concatenate(salida) if salida else np.zeros((0, 3))


def _muestrear_polilinea(P, paso):
    P = np.asarray(P, float)
    salida = [P[:1]]
    for a, b in zip(P[:-1], P[1:], strict=False):
        n = max(1, math.ceil(np.linalg.norm(b - a) / paso))
        salida.append(a + (b - a) * (np.arange(1, n + 1) / n)[:, None])
    return np.concatenate(salida)


def _triangulos(cuerpo, deflexion):
    """Triángulos (N,3,3) de una Malla o de una forma B-rep (teselada sobre una copia: no toca la malla de la vista)."""
    if hasattr(cuerpo, "triangulos"):
        return cuerpo.triangulos()
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Copy
    partes = [t for _, t in geo.teselar_por_cara(BRepBuilderAPI_Copy(cuerpo, False, False).Shape(), deflexion)]
    return np.concatenate(partes) if partes else np.zeros((0, 3, 3))


def muestrear(cuerpo, paso):
    """Nube de puntos sobre una Malla o una forma: sus caras; si no tiene, sus aristas; si no, sus vértices."""
    tris = _triangulos(cuerpo, paso / 2)
    if len(tris):
        return _muestrear_triangulos(tris, paso)
    lineas = [p for p in geo.polilineas_aristas(cuerpo, paso / 4) if len(p)]
    if lineas:
        return np.concatenate([_muestrear_polilinea(p, paso) for p in lineas])
    from . import referencias
    return np.array([referencias.punto_de_vertice(v) for v in referencias.subformas(cuerpo, "vertice")],
                    float).reshape(-1, 3)


def caja(cuerpo):
    """Caja envolvente ((x0,y0,z0), (x1,y1,z1)) de una forma o de una Malla."""
    return cuerpo.caja() if hasattr(cuerpo, "caja") else geo.caja_envolvente(cuerpo)


# ---------------------------------------------------------------- barras y paredes
def _pieza(a, b, ra, rb, altura=None):
    """Barra de a a b con radios ra y rb (cilindro o tronco de cono); con `altura` (vector), pared de semiancho ra/rb
    en a/b, en el plano normal a `altura`, extruida a lo largo de `altura`."""
    from OCP.gp import gp_Ax2, gp_Pnt, gp_Vec
    a, b = np.asarray(a, float), np.asarray(b, float)
    largo = float(np.linalg.norm(b - a))
    if largo < 1e-9 or max(ra, rb) < 1e-6:
        return None
    u = (b - a) / largo
    if altura is None:
        if abs(ra - rb) < 1e-9:
            return geo.cilindro(ra, largo, tuple(a), tuple(u))
        from OCP.BRepPrimAPI import BRepPrimAPI_MakeCone
        return geo._primitiva(lambda: BRepPrimAPI_MakeCone(gp_Ax2(gp_Pnt(*a), geo._dir(u)), float(ra), float(rb), largo),
                              "la barra")
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakePolygon
    from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism
    n = np.cross(altura, u)
    n /= np.linalg.norm(n)
    esquinas = [a + n * ra, b + n * rb, b - n * rb, a - n * ra]
    esquinas = [p for k, p in enumerate(esquinas) if np.linalg.norm(p - esquinas[k - 1]) > 1e-9]
    poligono = BRepBuilderAPI_MakePolygon()
    for p in esquinas:
        poligono.Add(gp_Pnt(*map(float, p)))
    poligono.Close()
    cara = BRepBuilderAPI_MakeFace(poligono.Wire()).Face()
    return geo._primitiva(lambda: BRepPrimAPI_MakePrism(cara, gp_Vec(*map(float, altura))), "la pared")


def _segmentos_unidad(tipo, segmentos=None):
    seg = np.asarray(segmentos if tipo == "custom" else SEGMENTOS.get(tipo, ()), float)
    if seg.size == 0 or seg.size % 6 or seg.min() < -1e-9 or seg.max() > 1 + 1e-9:
        raise geo.ErrorGeometria("La celda a medida necesita barras de 6 números (x1 y1 z1 x2 y2 z2), de 0 a 1.")
    return seg.reshape(-1, 2, 3)


def _vecindad(seg, tam, margen):
    """Segmentos de la celda y de sus 26 vecinas que pasan a menos de `margen` de la celda [0,tam] (una barra sobre una
    arista la comparten cuatro celdas), unidos los colineales."""
    desp = np.stack(np.meshgrid(*[np.arange(-1, 2)] * 3, indexing="ij"), -1).reshape(-1, 1, 1, 3)
    todos = ((seg[None] + desp) * tam).reshape(-1, 2, 3)
    t = np.linspace(0, 1, 9)[None, :, None]
    puntos = todos[:, :1] + (todos[:, 1:] - todos[:, :1]) * t
    cerca = ((puntos > -margen) & (puntos < tam + margen)).all(-1).any(-1)
    return _fusionar_colineales(todos[cerca, 0], todos[cerca, 1])


def _celda(seg, pared, d, sx, sy, sz, vecinas=False):
    """Un sólido [0,sx]×[0,sy]×[0,sz] con las barras (o paredes) de diámetro (o espesor) d. `vecinas`: suma lo que
    meten las celdas vecinas (barras a medida sobre las caras o aristas de la celda); las formas fijas no lo necesitan."""
    pares = _vecindad(seg, np.array([sx, sy, sz]), d / 2) if vecinas else [s_ * (sx, sy, sz) for s_ in seg]
    piezas = [_pieza(a, b, d / 2, d / 2, (0, 0, sz) if pared else None) for a, b in pares]
    return geo.booleano(geo.unir_todos(piezas), geo.caja(sx, sy, sz), "intersecar")


def diametro_para(tipo, solidez, sx, sy, sz, segmentos=None):
    """Diámetro de barra (espesor de pared en 2.5D) que deja la fracción de material `solidez` en una celda
    (bisección sobre la celda real)."""
    if solidez <= 0:
        return 0.0
    pared = tipo == "x_cell_25d"
    objetivo = solidez * sx * sy * sz
    lo, hi = 1e-4 * min(sx, sy, sz), 0.999 * min(sx, sy, sz)        # barras sobre las aristas de la celda: 1/4 adentro
    seg, vecinas = _segmentos_unidad(tipo, segmentos), tipo == "custom"
    if geo.volumen(_celda(seg, pared, hi, sx, sy, sz, vecinas)) < objetivo:
        raise geo.ErrorGeometria(f"Con ese tamaño de celda las barras no llegan a {solidez:.0%} de solidez: bajá la "
                                 "solidez o achicá la celda.")
    for _ in range(14):
        mid = (lo + hi) / 2
        if geo.volumen(_celda(seg, pared, mid, sx, sy, sz, vecinas)) < objetivo:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def _fusionar_colineales(A, B):
    """Une los segmentos colineales que se tocan o se pisan (solo para radio constante: menos piezas que unir)."""
    d = B - A
    largo = np.linalg.norm(d, axis=1)
    A, B, d, largo = A[largo > 1e-9], B[largo > 1e-9], d[largo > 1e-9], largo[largo > 1e-9]
    u = d / largo[:, None]
    u *= np.sign(u[np.arange(len(u)), np.argmax(np.abs(u) > 1e-9, axis=1)])[:, None]
    t0, t1 = np.einsum("ij,ij->i", A, u), np.einsum("ij,ij->i", B, u)
    pie = A - t0[:, None] * u
    grupos = {}
    for k, clave in enumerate(map(tuple, np.round(np.hstack([u, pie]), 5))):
        grupos.setdefault(clave, (u[k], pie[k], []))[2].append((min(t0[k], t1[k]), max(t0[k], t1[k])))
    salida = []
    for uk, pk, tramos in grupos.values():
        tramos.sort()
        a, b = tramos[0]
        for c, e in tramos[1:] + [(math.inf, math.inf)]:
            if c <= b + 1e-6:
                b = max(b, e)
                continue
            salida.append((pk + a * uk, pk + b * uk))
            a, b = c, e
    return salida


def reticula_barras(cuerpo, tipo, solidez_en, rejilla, segmentos=None):
    """Sólido: las barras (o paredes) de la retícula recortadas al cuerpo (forma B-rep o Malla cerrada).
    `solidez_en`: función de `campo_solidez`."""
    if hasattr(cuerpo, "triangulos"):
        from .malla import a_brep
        cuerpo = a_brep(cuerpo, metodo="prismatico")
        if not geo.solidos(cuerpo):
            raise geo.ErrorGeometria("La malla tiene que ser cerrada para llenarla con la retícula.")
    seg, pared = _segmentos_unidad(tipo, segmentos), tipo == "x_cell_25d"
    lo, hi = caja(cuerpo)
    local = rejilla.a_local(np.array([[x, y, z] for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])]))
    i0 = np.floor(local.min(0) / rejilla.tam + 1e-9).astype(int)
    i1 = np.maximum(np.ceil(local.max(0) / rejilla.tam - 1e-9).astype(int), i0 + 1)
    if np.prod(i1 - i0) * len(seg) > 50 * MAXIMO_BARRAS:
        raise geo.ErrorGeometria("La retícula tendría demasiadas barras: agrandá la celda.")
    indices = np.stack(np.meshgrid(*(np.arange(a, b) for a, b in zip(i0, i1, strict=True)), indexing="ij"), -1)
    indices = indices.reshape(-1, 1, 3)
    A = rejilla.a_mundo(((indices + seg[None, :, 0]) * rejilla.tam).reshape(-1, 3))
    B = rejilla.a_mundo(((indices + seg[None, :, 1]) * rejilla.tam).reshape(-1, 3))
    altura = rejilla.R[:, 2] * rejilla.tam[2] if pared else None
    sx, sy, sz = rejilla.tam
    s = np.concatenate([solidez_en(A + altura / 2), solidez_en(B + altura / 2)]) if pared else \
        np.concatenate([solidez_en(A), solidez_en(B)])
    if np.ptp(s) < 1e-9:                                                        # solidez uniforme: barras largas
        if pared:                                                               # una sola capa de paredes de alto completo
            capa = np.abs(np.einsum("ij,j->i", A - rejilla.origen, rejilla.R[:, 2]) - i0[2] * sz) < 1e-6
            A, B, altura = A[capa], B[capa], altura * (i1[2] - i0[2])
        d = diametro_para(tipo, float(s[0]), sx, sy, sz, segmentos)
        pares = _fusionar_colineales(A, B)
        radios = [(d / 2, d / 2)] * len(pares)
    else:
        valores = np.unique(np.round(np.linspace(s.min(), s.max(), 4), 6))
        diametros = [diametro_para(tipo, float(v), sx, sy, sz, segmentos) for v in valores]
        r = np.interp(s, valores, diametros) / 2
        pares, radios = list(zip(A, B, strict=True)), list(zip(r[:len(A)], r[len(A):], strict=True))
    if len(pares) > MAXIMO_BARRAS:
        raise geo.ErrorGeometria(f"La retícula tendría {len(pares)} barras (máximo {MAXIMO_BARRAS}): agrandá la celda.")
    piezas = [_pieza(a, b, ra, rb, altura) for (a, b), (ra, rb) in zip(pares, radios, strict=True)]
    resultado = geo.booleano(cuerpo, geo.unir_todos(piezas), "intersecar")
    if geo.sin_volumen(resultado):
        raise geo.ErrorGeometria("La retícula no deja material dentro del cuerpo: probá con otra celda.")
    return resultado


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


def _tabla_espesor(tipo):
    """(solidez, umbral): la fracción de volumen con |campo| ≤ umbral, en un periodo de la superficie."""
    n = np.linspace(0.0, 1.0, 48, endpoint=False) + 0.5 / 48
    x, y, z = np.meshgrid(n, n, n, indexing="ij")
    q = np.linspace(0.0, 1.0, 201)
    t = np.quantile(np.abs(campo(tipo, x, y, z, 1.0, 1.0, 1.0)), q)
    t[-1] = 10.0                                                    # 100 % = macizo: más que el máximo del campo (< 3)
    return q, t


def espesor_para(tipo, solidez):
    """Umbral t tal que la fracción de volumen con |campo| ≤ t es `solidez`."""
    return float(np.interp(solidez, *_tabla_espesor(tipo)))


def _dentro(tris, xs, ys, zs):
    """Máscara (nx, ny, nz) de los nodos de la grilla que están dentro de los triángulos cerrados: un rayo vertical por
    columna, corrido una nada para no pasar justo por una arista."""
    a, b, c = tris[:, 0], tris[:, 1], tris[:, 2]
    det = (b[:, 1] - c[:, 1]) * (a[:, 0] - c[:, 0]) + (c[:, 0] - b[:, 0]) * (a[:, 1] - c[:, 1])
    ok = np.abs(det) > 1e-14
    a, b, c, det = a[ok], b[ok], c[ok], det[ok]
    xmin, xmax = np.minimum(np.minimum(a[:, 0], b[:, 0]), c[:, 0]), np.maximum(np.maximum(a[:, 0], b[:, 0]), c[:, 0])
    ymin, ymax = np.minimum(np.minimum(a[:, 1], b[:, 1]), c[:, 1]), np.maximum(np.maximum(a[:, 1], b[:, 1]), c[:, 1])
    masc = np.zeros((len(xs), len(ys), len(zs)), bool)
    for i, x in enumerate(xs + 1.234567e-7):
        fx = np.nonzero((xmin <= x) & (x <= xmax))[0]
        for j, y in enumerate(ys + 7.654321e-8):
            f = fx[(ymin[fx] <= y) & (y <= ymax[fx])]
            if len(f) < 2:
                continue
            l1 = ((b[f, 1] - c[f, 1]) * (x - c[f, 0]) + (c[f, 0] - b[f, 0]) * (y - c[f, 1])) / det[f]
            l2 = ((c[f, 1] - a[f, 1]) * (x - c[f, 0]) + (a[f, 0] - c[f, 0]) * (y - c[f, 1])) / det[f]
            l3 = 1 - l1 - l2
            dentro = (l1 >= 0) & (l2 >= 0) & (l3 >= 0)
            cortes = np.sort(l1[dentro] * a[f[dentro], 2] + l2[dentro] * b[f[dentro], 2] + l3[dentro] * c[f[dentro], 2])
            cortes = cortes[np.concatenate([[True], np.diff(cortes) > 1e-7])] if len(cortes) else cortes
            for z0, z1 in zip(cortes[0::2], cortes[1::2], strict=False):
                masc[i, j, (zs > z0) & (zs < z1)] = True
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


def reticula_malla(cuerpo, tipo, solidez_en, rejilla, resolucion=8):
    """Cuerpo de malla con la superficie mínima engrosada (umbral según la solidez de cada punto), recortada al cuerpo
    (forma B-rep o Malla cerrada). El borde sale de la distancia con signo al cuerpo, interpolada en la grilla."""
    from scipy.spatial import cKDTree

    from .malla import Malla
    if hasattr(cuerpo, "es_cerrada") and not cuerpo.es_cerrada():
        raise geo.ErrorGeometria("La malla tiene que ser cerrada para llenarla con la retícula.")
    h = float(rejilla.tam.min()) / max(4, int(resolucion))
    tris = _triangulos(cuerpo, h / 20)
    if not len(tris):
        raise geo.ErrorGeometria("El cuerpo no tiene superficie para llenar.")
    lo, hi = tris.reshape(-1, 3).min(0), tris.reshape(-1, 3).max(0)
    # corrida una fracción rara del paso: un nodo sobre la pared daría g = 0 y triángulos degenerados (malla no cerrada)
    xs, ys, zs = (np.arange(lo[k] - 0.9137 * h, hi[k] + 1.5 * h, h) for k in range(3))
    if len(xs) * len(ys) * len(zs) > MAXIMO_MUESTRAS:
        raise geo.ErrorGeometria(f"La grilla tendría más de {MAXIMO_MUESTRAS:,} muestras: agrandá la celda o bajá la "
                                 "resolución.".replace(",", "."))
    dentro = _dentro(tris, xs, ys, zs)
    pos = np.stack(np.meshgrid(xs, ys, zs, indexing="ij"), axis=-1)
    puntos = pos.reshape(-1, 3)
    distancia = cKDTree(_muestrear_triangulos(tris, h / 4)).query(puntos)[0].reshape(dentro.shape)
    local = rejilla.a_local(puntos)
    f = campo(tipo, local[:, 0], local[:, 1], local[:, 2], *rejilla.tam).reshape(dentro.shape)
    umbral = np.interp(solidez_en(puntos), *_tabla_espesor(tipo)).reshape(dentro.shape)
    k = 2 * math.pi / float(rejilla.tam.min())                                 # distancia en mm → unidades del campo
    g = np.maximum(np.abs(f) - umbral, np.where(dentro, -distancia, distancia) * k)
    tris = [t_ for i in range(len(xs) - 1) if len(t_ := _triangular_losa(g, pos, i))]
    if not tris:
        raise geo.ErrorGeometria("La retícula no deja material dentro del cuerpo: probá con otra celda o más solidez.")
    return Malla.desde_triangulos(np.concatenate(tris))

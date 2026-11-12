# -*- coding: utf-8 -*-
"""
Comparar dos cuerpos: sólido contra malla, malla contra malla o versión vieja contra nueva (F10 y SC13; es el juez de
Reconstruir sólido, docs/plan_reconstruir_solido.md). Fusion no lo trae en el espacio de diseño: se parece a Mesh
Section Analysis y a los mapas de desviación de los programas de ingeniería inversa.

- `comparar`: desviación en los dos sentidos (máximo, media, percentil 95, % dentro de tolerancia), volumen, solapamiento
  y las zonas que pasan la tolerancia.
- `mapa`: valor con signo sobre la superficie de un cuerpo, para pintarlo.
- `solapamiento`: intersección sobre unión de dos cuerpos, contando por columnas (no pide mallas perfectas).

Signo: positivo = en ese punto A tiene material de más respecto de B; negativo = a A le falta.
Una forma OCC se tesela más fino que la tolerancia. Todo lo aleatorio usa semilla fija: dos corridas dan lo mismo.
"""
import itertools
import math

import numpy as np

from . import geometria as geo
from . import malla as ml

TOPE_TRIANGULOS = 2_000_000             # mallas ajenas: más que esto se rechaza con un mensaje claro
_TOPE_PEDAZOS = 60_000                  # triángulos partidos de una malla con caras enormes (búsqueda exacta)
_VECINOS = 8
_LEJOS = 6.0                            # más lejos que esto (en radios de pedazo) alcanza con los vecinos más próximos
_CANDIDATOS_TANDA = 2_000_000
_COLUMNAS = 256                         # columnas por lado del solapamiento
_ZONAS_MAX = 20
_SEMILLA = 20261101


def exigir_malla(m, que="La malla"):
    """Valida una malla ajena antes de medirla: que tenga triángulos con área y no pase del tope."""
    if not len(m.caras):
        raise geo.ErrorGeometria(f"{que} está vacía.")
    if len(m.caras) > TOPE_TRIANGULOS:
        raise geo.ErrorGeometria(f"{que} tiene {len(m.caras):,} triángulos y el máximo es {TOPE_TRIANGULOS:,}: reducila "
                                 "antes con MALLA › Modificar › Reducir (reduce_mesh).".replace(",", "."))
    if not m.area() > 0:
        raise geo.ErrorGeometria(f"{que} no tiene área: todos sus triángulos están degenerados.")


def a_malla(x, tolerancia):
    """Una Malla tal cual; una forma OCC teselada a un quinto de la tolerancia (como mínimo 0,002 mm)."""
    if isinstance(x, ml.Malla):
        exigir_malla(x)
        return x
    return ml.desde_brep(x, refinamiento="personalizado", desviacion=max(tolerancia / 5, 0.002), angulo=10.0)


class Superficie:
    """Punto más cercano sobre una malla, exacto: `malla._Referencia` da una cota, y con ella se revisan todos los
    triángulos que pueden estar más cerca. Los triángulos largos se parten antes, sin cambiar la superficie. Cada tamaño
    de triángulo tiene su árbol y su radio: con un solo radio, el del más largo, una zona de triángulos chicos da miles de
    candidatos por punto."""

    def __init__(self, m, pedazos=_TOPE_PEDAZOS):
        from scipy.spatial import cKDTree
        largo = math.sqrt(8 * max(m.area(), 1e-12) / pedazos)
        T = m.triangulos()
        # el tope holgado: si corta antes de tiempo quedan pedazos enormes y el radio de búsqueda abarca toda la pieza
        T = ml._partir_largos(T[m.areas_caras() > 0], largo, 8 * pedazos)
        self.T = T
        centros = T.mean(1)
        radios = np.linalg.norm(T - centros[:, None], axis=2).max(1)
        self.radio = float(radios.max())
        n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
        self.N = n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-300)
        self.arbol = cKDTree(centros)
        self.k = min(_VECINOS, len(T))
        tamano = np.floor(np.log2(np.maximum(radios, 1e-12))).astype(np.int64)
        self.clases = [(cKDTree(centros[idx]), idx, float(radios[idx].max()))
                       for idx in (np.flatnonzero(tamano == c) for c in np.unique(tamano))]

    def _tramo(self, P, idx):
        """Distancia y punto más cercano de P[i] a los triángulos idx[i]."""
        Q = ml._mas_cercano_tri(P, self.T[idx, 0], self.T[idx, 1], self.T[idx, 2])
        return np.linalg.norm(Q - P, axis=1), Q

    def _elegir(self, P, fila, idx, d, q, normal):
        """Por cada punto con candidatos, se queda con el más cercano; en un empate (arista o vértice compartido), con el de
        normal más franca: así el signo no depende de qué cara vecina salió primero."""
        nuevo, Q = self._tramo(P[fila], idx)
        franco = np.abs(np.einsum("ij,ij->i", P[fila] - Q, self.N[idx]))
        orden = np.lexsort((-franco, np.round(nuevo, 9), fila))
        primero = orden[np.r_[True, fila[orden][1:] != fila[orden][:-1]]]
        i = fila[primero]
        actual = np.round(d[i], 9)
        ganan = (np.round(nuevo[primero], 9) < actual) | ((np.round(nuevo[primero], 9) == actual) & (
            franco[primero] > np.abs(np.einsum("ij,ij->i", P[i] - q[i], normal[i]))))
        i, primero = i[ganan], primero[ganan]
        d[i], q[i], normal[i] = nuevo[primero], Q[primero], self.N[idx[primero]]

    def mas_cercano(self, P, suficiente=0.0):
        """(distancias, puntos, normales de la cara) de cada punto de P (Nx3). Un punto que ya tiene un triángulo a
        `suficiente` mm o menos no sigue buscando: alcanza para saber que está bien."""
        n = len(P)
        D, Q, N = np.empty(n), np.empty((n, 3)), np.empty((n, 3))
        for i in range(0, n, 20000):
            p = P[i:i + 20000]
            _, idx = self.arbol.query(p, k=self.k)
            idx = np.asarray(idx).reshape(len(p), self.k)
            d, q, normal = np.full(len(p), np.inf), np.zeros((len(p), 3)), np.zeros((len(p), 3))
            self._elegir(p, np.repeat(np.arange(len(p)), self.k), idx.ravel(), d, q, normal)
            cerca = np.flatnonzero((d > suficiente) & (d < _LEJOS * self.radio))
            for arbol, indices, radio in self.clases:
                for tramo in _tramos(arbol, p[cerca], d[cerca] + radio * (1 + 1e-9)):
                    if len(tramo["candidatos"]):
                        sel = cerca[tramo["indices"]]
                        vista = (d[sel], q[sel], normal[sel])
                        self._elegir(p[sel], tramo["fila"], indices[tramo["candidatos"]], *vista)
                        d[sel], q[sel], normal[sel] = vista
            D[i:i + 20000], Q[i:i + 20000], N[i:i + 20000] = d, q, normal
        return D, Q, N

    def con_signo(self, P, suficiente=0.0):
        """Distancia con signo: positiva si el punto queda del lado de afuera de la superficie."""
        d, Q, N = self.mas_cercano(P, suficiente)
        return d * np.where(np.einsum("ij,ij->i", P - Q, N) >= 0, 1.0, -1.0)


def _tramos(arbol, p, r):
    """Candidatos de cada punto, de a tandas: lejos de la superficie cada uno toca miles de triángulos, y armar las listas
    de golpe agotó la memoria. Por eso primero se cuentan."""
    if not len(p):
        return
    cuenta = arbol.query_ball_point(p, r, return_length=True)
    for grupo in np.split(np.arange(len(p)), np.flatnonzero(np.diff(np.cumsum(cuenta) // _CANDIDATOS_TANDA)) + 1):
        listas = arbol.query_ball_point(p[grupo], r[grupo], return_sorted=False)
        yield {"indices": grupo, "fila": np.repeat(np.arange(len(grupo)), cuenta[grupo]),
               "candidatos": np.fromiter(itertools.chain.from_iterable(listas), np.int64, int(cuenta[grupo].sum()))}


def muestrear(m, n, semilla=_SEMILLA):
    """`n` puntos repartidos por área sobre la malla (semilla fija), más todos sus vértices al final, porque los picos
    de desviación suelen estar ahí. Devuelve (puntos, cuántos de ellos son por área)."""
    rng = np.random.default_rng(semilla)
    area = m.areas_caras()
    cual = rng.choice(len(area), size=n, p=area / area.sum())
    r = np.sqrt(rng.random(n))
    s = rng.random(n)
    T = m.triangulos()[cual]
    P = (1 - r)[:, None] * T[:, 0] + (r * (1 - s))[:, None] * T[:, 1] + (r * s)[:, None] * T[:, 2]
    return np.vstack([P, m.vertices[np.unique(m.caras)]]), n


def _resumen(d, n):
    """Estadística de distancias: media y percentil solo por área (`n` primeras); máximo con todas."""
    a = np.abs(d[:n])
    return {"max": float(np.abs(d).max()), "mean": float(a.mean()), "p95": float(np.percentile(a, 95))}


def zonas(P, valores, tolerancia, area_por_punto):
    """Zonas de la superficie que pasan la tolerancia: puntos vecinos juntos (`P` y su valor con signo), de la mayor a la
    menor. `excess_mm` es lo que sobra en A y `missing_mm` lo que le falta."""
    fuera = np.flatnonzero(np.abs(valores) > tolerancia)
    if not len(fuera):
        return []
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    from scipy.spatial import cKDTree
    Q, v = P[fuera], valores[fuera]
    radio = 3 * math.sqrt(area_por_punto)
    # un punto por celda: los vértices se amontonan en los detalles finos y los pares llegaron a 32 millones
    _, uno, celda = np.unique(np.floor(Q / (radio / 2)).astype(np.int64), axis=0, return_index=True, return_inverse=True)
    pares = cKDTree(Q[uno]).query_pairs(radio, output_type="ndarray")
    grafo = coo_matrix((np.ones(len(pares)), (pares[:, 0], pares[:, 1])), shape=(len(uno), len(uno)))
    etiqueta = connected_components(grafo, directed=False)[1][celda.reshape(-1)]
    salida = []
    for k in np.unique(etiqueta):
        s = etiqueta == k
        w = np.abs(v[s])
        salida.append({"center": [round(float(x), 4) for x in Q[s][np.argmax(w)]],
                       "bbox_min": [round(float(x), 4) for x in Q[s].min(0)],
                       "bbox_max": [round(float(x), 4) for x in Q[s].max(0)],
                       "area": round(float(s.sum() * area_por_punto), 3), "max_deviation": round(float(w.max()), 4),
                       "excess_mm": round(max(float(v[s].max()), 0.0), 4),
                       "missing_mm": round(max(-float(v[s].min()), 0.0), 4)})
    return sorted(salida, key=lambda z: -z["area"] * z["max_deviation"])


def _eventos(m, x0, y0, paso, n):
    """Cruces de la malla con las columnas verticales de una grilla n×n: (columna, z, ±1). Baja la malla y entra +1."""
    T = m.triangulos()
    ij = (T[:, :, :2] - (x0, y0)) / paso
    a, b = np.ceil(ij.min(1)).astype(np.int64).clip(0, n), np.floor(ij.max(1)).astype(np.int64).clip(-1, n - 1)
    ancho, alto = b[:, 0] - a[:, 0] + 1, b[:, 1] - a[:, 1] + 1
    vivos = np.flatnonzero((ancho > 0) & (alto > 0))
    celdas = ancho[vivos] * alto[vivos]
    salida = []
    for lote in np.array_split(vivos, max(1, int(celdas.sum() // 2_000_000) + 1)):
        t = np.repeat(lote, ancho[lote] * alto[lote])
        if not len(t):
            continue
        inicio = np.r_[0, np.cumsum(ancho[lote] * alto[lote])[:-1]]
        k = np.arange(len(t)) - np.repeat(inicio, ancho[lote] * alto[lote])
        w = ancho[t]
        i, j = a[t, 0] + k % w, a[t, 1] + k // w
        P, A, B, C = np.stack([i, j], 1) * 1.0, ij[t, 0], ij[t, 1], ij[t, 2]
        d = (B[:, 0] - A[:, 0]) * (C[:, 1] - A[:, 1]) - (B[:, 1] - A[:, 1]) * (C[:, 0] - A[:, 0])
        with np.errstate(divide="ignore", invalid="ignore"):
            u = ((P[:, 0] - A[:, 0]) * (C[:, 1] - A[:, 1]) - (P[:, 1] - A[:, 1]) * (C[:, 0] - A[:, 0])) / d
            v = ((B[:, 0] - A[:, 0]) * (P[:, 1] - A[:, 1]) - (B[:, 1] - A[:, 1]) * (P[:, 0] - A[:, 0])) / d
            dentro = (u >= 0) & (v >= 0) & (u + v <= 1) & (d != 0)
        Z = T[t[dentro]][:, :, 2]
        z = Z[:, 0] + u[dentro] * (Z[:, 1] - Z[:, 0]) + v[dentro] * (Z[:, 2] - Z[:, 0])
        salida.append((i[dentro] + j[dentro] * n, z, np.where(d[dentro] > 0, -1, 1)))
    if not salida:
        return np.empty(0, np.int64), np.empty(0), np.empty(0, np.int64)
    return tuple(np.concatenate(c) for c in zip(*salida, strict=True))


def solapamiento(a, b, columnas=_COLUMNAS):
    """Intersección sobre unión (0 a 1) de dos mallas cerradas, sin booleana: en cada columna vertical de una grilla se
    miden los tramos que están adentro de cada una. La grilla arranca en un desfase irracional para no pasar justo por
    las aristas de una pieza alineada. Una malla sucia no la rompe: cuenta lo que encierra."""
    caja = np.array([*a.caja(), *b.caja()])
    menor = caja.min(0)
    paso = max(float(np.ptp(caja[:, :2], axis=0).max()) / (columnas - 1), 1e-9)
    x0, y0 = menor[:2] - paso * (math.sqrt(2) - 1) / 2, menor[:2] - paso * (math.sqrt(3) - 1) / 2
    columna_a, z_a, s_a = _eventos(a, x0[0], y0[1], paso, columnas + 1)
    columna_b, z_b, s_b = _eventos(b, x0[0], y0[1], paso, columnas + 1)
    col, z = np.r_[columna_a, columna_b], np.r_[z_a, z_b]
    orden = np.lexsort((z, col))
    col, z = col[orden], z[orden]
    en_a = np.cumsum(np.r_[s_a, np.zeros(len(s_b), np.int64)][orden])
    en_b = np.cumsum(np.r_[np.zeros(len(s_a), np.int64), s_b][orden])
    largo = np.where(col[1:] == col[:-1], np.diff(z), 0.0)
    ambos, alguno = (en_a[:-1] != 0) & (en_b[:-1] != 0), (en_a[:-1] != 0) | (en_b[:-1] != 0)   # != : normales invertidas
    union = float(largo[alguno].sum())
    return float(largo[ambos].sum()) / union if union > 0 else 0.0


def _volumen(x, m):
    return abs(m.volumen()) if isinstance(x, ml.Malla) else abs(geo.volumen(x))


def comparar(a, b, *, tolerancia=0.1, muestras=50000, semilla=_SEMILLA):
    """Compara `a` contra `b` (cada uno una Malla o una forma OCC). Devuelve la desviación de cada sentido y la mayor de
    las dos, el % de superficie dentro de `tolerancia`, volúmenes, solapamiento y zonas fuera de tolerancia."""
    if not (tolerancia > 0 and math.isfinite(tolerancia)):
        raise geo.ErrorGeometria("La tolerancia tiene que ser mayor que cero (mm).")
    if not 1000 <= muestras <= 2_000_000:
        raise geo.ErrorGeometria("La cantidad de muestras tiene que estar entre 1000 y 2.000.000.")
    ma, mb = a_malla(a, tolerancia), a_malla(b, tolerancia)
    sa, sb = Superficie(ma), Superficie(mb)
    pa, na = muestrear(ma, muestras, semilla)
    pb, nb = muestrear(mb, muestras, semilla + 1)
    bien = tolerancia / 20
    va, vb = sb.con_signo(pa, bien), -sa.con_signo(pb, bien)   # los dos con el mismo signo: positivo = sobra en A
    ida, vuelta = _resumen(va, na), _resumen(vb, nb)
    dentro = (np.abs(va[:na]) <= tolerancia).sum() + (np.abs(vb[:nb]) <= tolerancia).sum()
    volumen_a, volumen_b = _volumen(a, ma), _volumen(b, mb)
    cerradas = ma.es_cerrada() and mb.es_cerrada()
    area = (ma.area() + mb.area()) / (na + nb)
    todas = zonas(np.vstack([pa, pb]), np.r_[va, vb], tolerancia, area)
    caja_a, caja_b = np.array(ma.caja()), np.array(mb.caja())
    return {"max_deviation": max(ida["max"], vuelta["max"]), "mean_deviation": (ida["mean"] + vuelta["mean"]) / 2,
            "p95_deviation": max(ida["p95"], vuelta["p95"]), "a_to_b": ida, "b_to_a": vuelta,
            "within_tolerance_percent": 100.0 * float(dentro) / (na + nb), "tolerance": float(tolerancia),
            "volume_a": volumen_a, "volume_b": volumen_b, "volume_difference": volumen_a - volumen_b,
            "volume_difference_percent": 100.0 * (volumen_a - volumen_b) / volumen_b if volumen_b else None,
            "iou": solapamiento(ma, mb) if cerradas else None, "closed": cerradas,
            "bbox_difference": float(np.abs(caja_a - caja_b).max()), "zones": todas[:_ZONAS_MAX],
            "zones_total": len(todas)}


def mapa(a, b, *, tolerancia=0.1):
    """Valor con signo en cada vértice de la superficie de `a`, para pintarla: (triángulos sueltos V×3, normales V×3,
    valores V). Los triángulos grandes se parten: si no, una zona chica en una cara enorme no se ve."""
    ma, mb = a_malla(a, tolerancia), a_malla(b, tolerancia)
    largo = math.sqrt(ma.area() / 40000)
    T = ml._partir_largos(ma.triangulos()[ma.areas_caras() > 0], 2 * largo, 120_000)
    n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-300)
    v = T.reshape(-1, 3)
    unicos, inv = np.unique(np.round(v, 7), axis=0, return_inverse=True)
    valores = Superficie(mb).con_signo(unicos)[inv.reshape(-1)]
    return v, np.repeat(n, 3, axis=0), valores


# Escala de 4 colores (plan › Resultado): azul falta, verde bien, amarillo cerca del límite, rojo pasa.
ESCALA = ((0.13, 0.35, 0.85), (0.20, 0.72, 0.35), (0.95, 0.80, 0.15), (0.86, 0.16, 0.16))


def colores(valores, tolerancia):
    """Color de cada valor: adentro de la tolerancia, de verde a amarillo según cuánto se acerca al límite; afuera, rojo
    si sobra material y azul si falta."""
    v = np.asarray(valores, float)
    azul, verde, amarillo, rojo = (np.array(c) for c in ESCALA)
    t = np.clip(np.abs(v) / tolerancia, 0, 1)[:, None]
    c = verde + (amarillo - verde) * t
    c[v > tolerancia] = rojo
    c[v < -tolerancia] = azul
    return c

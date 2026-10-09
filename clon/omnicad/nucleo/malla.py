# -*- coding: utf-8 -*-
"""
Espacio MALLA (pestaña Mesh de Fusion): cuerpos de malla triangular y sus herramientas.

Una `Malla` son triángulos indexados: vértices Nx3 (mm), caras Mx3 (sentido antihorario visto desde
afuera, así la normal apunta hacia afuera) y un grupo por cara (los Face Groups de Fusion).
Todas las funciones son puras: devuelven una malla nueva y no tocan la de entrada.

El cálculo es numpy/scipy. `manifold3d` (opcional, Apache-2.0) hace las booleanas de Combinar; sin él
se usa el kernel B-rep (más lento). La conversión a sólido usa OpenCascade.
"""
import base64
import heapq
import itertools
import math
import re
import struct
import warnings
import xml.etree.ElementTree as ET
import zipfile
import zlib
from pathlib import Path

import numpy as np
from OCP.BRep import BRep_Builder
from OCP.BRepBuilderAPI import (BRepBuilderAPI_Copy, BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeFace,
                                BRepBuilderAPI_MakeSolid, BRepBuilderAPI_MakeVertex, BRepBuilderAPI_MakeWire)
from OCP.BRepLib import BRepLib
from OCP.ShapeUpgrade import ShapeUpgrade_UnifySameDomain
from OCP.TopoDS import TopoDS_Shell
from OCP.gp import gp_Dir, gp_Pln, gp_Pnt

from . import geometria as geo

# scipy se importa adentro de cada función que lo usa (perezoso): cuesta ~0,4 s y la app lo importaba al arrancar
# (vía `io_archivos.abrir_externo`) aunque no se abra ninguna malla.

try:
    import manifold3d as _manifold
except ImportError:  # opcional: sin él, Combinar usa el kernel B-rep
    _manifold = None

UNIDADES = {"mm": 1.0, "cm": 10.0, "m": 1000.0, "pulgadas": 25.4, "pies": 304.8}
_UNIDADES_3MF = {"micron": 0.001, "millimeter": 1.0, "centimeter": 10.0, "meter": 1000.0,
                 "inch": 25.4, "foot": 304.8}
_NOMBRE_3MF = {"mm": "millimeter", "cm": "centimeter", "m": "meter", "pulgadas": "inch", "pies": "foot"}


def _factor(unidades):
    if unidades not in UNIDADES:
        raise geo.ErrorGeometria(f"Unidad desconocida: {unidades!r} (usá {', '.join(UNIDADES)}).")
    return UNIDADES[unidades]


# ---------------------------------------------------------------- modelo
class Malla:
    """Cuerpo de malla (Mesh Body): vértices Nx3 en mm, caras Mx3 y un grupo de caras por cara."""

    def __init__(self, vertices, caras, grupos=None):
        v = np.array(vertices, dtype=np.float64).reshape(-1, 3)
        c = np.array(caras, dtype=np.int64).reshape(-1, 3)
        g = np.zeros(len(c), np.int64) if grupos is None else np.array(grupos, dtype=np.int64).reshape(-1)
        if len(g) != len(c):
            raise geo.ErrorGeometria("Tiene que haber un grupo por cara.")
        if len(c) and (c.min() < 0 or c.max() >= len(v)):
            raise geo.ErrorGeometria("Hay caras que apuntan a vértices que no existen.")
        if not np.isfinite(v).all():
            raise geo.ErrorGeometria("La malla tiene coordenadas no finitas (NaN o infinito).")
        self.vertices, self.caras, self.grupos = v, c, g

    @classmethod
    def desde_triangulos(cls, triangulos, grupos=None):
        """Malla indexada a partir de triángulos sueltos (Mx3x3): une los vértices idénticos."""
        t = np.asarray(triangulos, dtype=np.float64).reshape(-1, 3, 3)
        if not len(t):
            return cls(np.zeros((0, 3)), np.zeros((0, 3), np.int64))
        unicos, primero, inv = np.unique(t.reshape(-1, 3), axis=0, return_index=True, return_inverse=True)
        orden = np.argsort(primero)              # orden de primera aparición (estable en ida y vuelta)
        rango = np.empty_like(orden)
        rango[orden] = np.arange(len(orden))
        return cls(unicos[orden], rango[inv.reshape(-1)].reshape(-1, 3), grupos)

    def __repr__(self):
        return f"Malla({len(self.vertices)} vértices, {len(self.caras)} caras, {len(np.unique(self.grupos))} grupos)"

    def copia(self):
        return Malla(self.vertices, self.caras, self.grupos)

    def triangulos(self):
        return self.vertices[self.caras]

    def normales_caras(self, unitarias=True):
        t = self.triangulos()
        n = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0])
        if unitarias:
            largo = np.linalg.norm(n, axis=1, keepdims=True)
            largo[largo == 0] = 1.0
            n = n / largo
        return n

    def areas_caras(self):
        return 0.5 * np.linalg.norm(self.normales_caras(False), axis=1)

    def area(self):
        return float(self.areas_caras().sum())

    def volumen(self):
        """Volumen encerrado, con signo (negativo si las normales apuntan hacia adentro)."""
        if not len(self.caras):
            return 0.0
        t = self.triangulos() - self.vertices.mean(axis=0)
        return float(np.einsum("ij,ij->i", t[:, 0], np.cross(t[:, 1], t[:, 2])).sum() / 6.0)

    def caja(self):
        """((xmin, ymin, zmin), (xmax, ymax, zmax)) de los vértices usados; None si está vacía."""
        if not len(self.caras):
            return None
        usados = self.vertices[np.unique(self.caras)]
        return tuple(map(float, usados.min(0))), tuple(map(float, usados.max(0)))

    def es_cerrada(self):
        """Estanca y orientada (Mesh Is Closed + Mesh Is Oriented de Fusion): cada arista la comparten
        exactamente dos caras que la recorren en sentidos opuestos, sin caras degeneradas."""
        c = self.caras
        if not len(c) or np.any((c[:, 0] == c[:, 1]) | (c[:, 1] == c[:, 2]) | (c[:, 0] == c[:, 2])):
            return False
        n = len(self.vertices)
        he = _medias_aristas(c)
        directa = he[:, 0] * n + he[:, 1]
        if len(np.unique(directa)) != len(directa):
            return False
        return bool(np.isin(he[:, 1] * n + he[:, 0], directa).all())

    def a_dict(self):
        """Forma serializable a JSON (arrays comprimidos en base64) para la receta del proyecto."""
        return {"formato": "omnicad.malla/1", "n_vertices": len(self.vertices), "n_caras": len(self.caras),
                "vertices": _a_b64(self.vertices.astype("<f8")), "caras": _a_b64(self.caras.astype("<i4")),
                "grupos": _a_b64(self.grupos.astype("<i4"))}

    @classmethod
    def desde_dict(cls, datos):
        if datos.get("formato") not in ("omnicad.malla/1", "fusionclone.malla/1"):   # fusionclone: nombre anterior
            raise geo.ErrorGeometria("El dato guardado no es una malla de OmniCAD.")
        v = np.frombuffer(_de_b64(datos["vertices"]), "<f8").reshape(-1, 3)
        c = np.frombuffer(_de_b64(datos["caras"]), "<i4").reshape(-1, 3)
        g = np.frombuffer(_de_b64(datos["grupos"]), "<i4")
        if len(v) != datos["n_vertices"] or len(c) != datos["n_caras"]:
            raise geo.ErrorGeometria("La malla guardada está incompleta o dañada.")
        return cls(v, c, g)


def _a_b64(arr):
    return base64.b64encode(zlib.compress(np.ascontiguousarray(arr).tobytes(), 6)).decode("ascii")


def _de_b64(texto):
    return zlib.decompress(base64.b64decode(texto))


def analizar(m):
    """Análisis rápido de Reparar [MESH-REPAIR]: si la malla es cerrada, orientada y de volumen positivo,
    y cuántos problemas tiene (aristas de borde, aristas no-manifold, caras degeneradas)."""
    c = m.caras
    topo = _Topo(c, len(m.vertices))
    _, _, mismo, _ = topo.pares()
    diag = _diagonal(m.vertices)
    degenerados = int(np.count_nonzero((c[:, 0] == c[:, 1]) | (c[:, 1] == c[:, 2]) | (c[:, 0] == c[:, 2])
                                       | (m.areas_caras() <= (1e-9 * diag) ** 2)))
    vol = m.volumen()
    return {"vertices": len(m.vertices), "caras": len(c), "grupos": int(len(np.unique(m.grupos))),
            "cerrada": m.es_cerrada(), "orientada": not bool(mismo.any()), "volumen_positivo": vol > 0,
            "aristas_borde": int(np.count_nonzero(topo.cuenta == 1)),
            "aristas_no_manifold": int(np.count_nonzero(topo.cuenta > 2)),
            "degenerados": degenerados, "cascaras": int(_cascaras(c, len(m.vertices))[0].max() + 1) if len(c) else 0,
            "volumen": vol, "area": m.area()}


# ---------------------------------------------------------------- topología
def _diagonal(v):
    return float(np.linalg.norm(v.max(0) - v.min(0))) if len(v) else 0.0


def _medias_aristas(caras):
    """Medias aristas (3M x 2): la cara k aporta las filas 3k..3k+2 = (v0,v1), (v1,v2), (v2,v0)."""
    return caras[:, [0, 1, 1, 2, 2, 0]].reshape(-1, 2)


class _Topo:
    """Medias aristas, aristas sin orientar y vecindad de caras."""

    def __init__(self, caras, n_vertices):
        n = max(int(n_vertices), 1)
        self.he = _medias_aristas(caras)
        lo, hi = np.minimum(self.he[:, 0], self.he[:, 1]), np.maximum(self.he[:, 0], self.he[:, 1])
        unicas, inv, self.cuenta = np.unique(lo * n + hi, return_inverse=True, return_counts=True)
        self.inv = inv.reshape(-1)
        self.aristas = np.stack([unicas // n, unicas % n], axis=1)
        orden = np.argsort(self.inv, kind="stable")
        io = self.inv[orden]
        seguidos = io[1:] == io[:-1]
        self.h1, self.h2 = orden[:-1][seguidos], orden[1:][seguidos]   # medias aristas de la misma arista

    def pares(self, solo_manifold=True):
        """(cara1, cara2, mismo_sentido, id de arista) de las caras vecinas por una arista."""
        h1, h2 = self.h1, self.h2
        if solo_manifold:
            ok = self.cuenta[self.inv[h1]] == 2
            h1, h2 = h1[ok], h2[ok]
        return h1 // 3, h2 // 3, self.he[h1, 0] == self.he[h2, 0], self.inv[h1]

    def libres(self):
        """Medias aristas de borde (su arista la usa una sola cara)."""
        return self.he[self.cuenta[self.inv] == 1]


def _reetiquetar(etiquetas):
    """Etiquetas 0..k-1 en orden de primera aparición."""
    etiquetas = np.asarray(etiquetas)
    if not len(etiquetas):
        return etiquetas.astype(np.int64)
    _, primero, inv = np.unique(etiquetas, return_index=True, return_inverse=True)
    rango = np.argsort(np.argsort(primero))
    return rango[inv.reshape(-1)].astype(np.int64)


def _cascaras(c, n_vertices):
    """Cáscara (componente conexa por aristas) de cada cara y si cada cáscara es cerrada."""
    M = len(c)
    if not M:
        return np.zeros(0, np.int64), np.zeros(0, bool)
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    topo = _Topo(c, n_vertices)
    grafo = coo_matrix((np.ones(len(topo.h1)), (topo.h1 // 3, topo.h2 // 3)), shape=(M, M))
    etiqueta = _reetiquetar(connected_components(grafo, directed=False)[1])
    cerrada = np.ones(etiqueta.max() + 1, bool)
    cerrada[etiqueta[np.flatnonzero(topo.cuenta[topo.inv] != 2) // 3]] = False
    return etiqueta, cerrada


def _compactar(v, c, g):
    """Malla sin los vértices que no usa ninguna cara (conserva el orden)."""
    c = np.asarray(c, np.int64).reshape(-1, 3)
    usados = np.zeros(len(v), bool)
    usados[c.ravel()] = True
    nuevo = np.cumsum(usados) - 1
    return Malla(v[usados], nuevo[c], g)


def _invertir(c, mascara):
    c = c.copy()
    c[mascara] = c[mascara][:, [0, 2, 1]]
    return c


def _numero_de_giro(p, tris):
    """Número de giro de un punto respecto de triángulos cerrados (suma de ángulos sólidos / 4π)."""
    a, b, c = tris[:, 0] - p, tris[:, 1] - p, tris[:, 2] - p
    la, lb, lc = (np.linalg.norm(x, axis=1) for x in (a, b, c))
    num = np.einsum("ij,ij->i", a, np.cross(b, c))
    den = la * lb * lc + np.einsum("ij,ij->i", a, b) * lc + np.einsum("ij,ij->i", b, c) * la \
        + np.einsum("ij,ij->i", c, a) * lb
    return float(np.arctan2(num, den).sum() / (2 * np.pi))


def _anidamiento(v, c, etiqueta, cerrada):
    """Profundidad de cada cáscara cerrada (cuántas otras la contienen) y su contenedora inmediata."""
    k = len(cerrada)
    prof, padre = np.zeros(k, np.int64), np.full(k, -1)
    cerradas = np.flatnonzero(cerrada)
    if len(cerradas) < 2:
        return prof, padre
    tris = v[c]
    orden = np.argsort(etiqueta, kind="stable")
    cortes = np.searchsorted(etiqueta[orden], np.arange(k + 1))
    caras_de = [orden[cortes[i]:cortes[i + 1]] for i in range(k)]
    bmin, bmax = np.full((k, 3), np.inf), np.full((k, 3), -np.inf)
    np.minimum.at(bmin, etiqueta, tris.min(1))
    np.maximum.at(bmax, etiqueta, tris.max(1))
    t = tris - v.mean(0)
    vol = np.abs(np.bincount(etiqueta, np.einsum("ij,ij->i", t[:, 0], np.cross(t[:, 1], t[:, 2])), k))
    tol = 1e-9 * (_diagonal(v) or 1.0)
    for i in cerradas:
        p = tris[caras_de[i][0]].mean(0)
        dentro = (np.all(bmin[cerradas] <= bmin[i] + tol, 1) & np.all(bmax[cerradas] >= bmax[i] - tol, 1)
                  & (cerradas != i))
        contenedoras = [j for j in cerradas[dentro] if abs(_numero_de_giro(p, tris[caras_de[j]])) > 0.5]
        prof[i] = len(contenedoras)
        if contenedoras:
            padre[i] = min(contenedoras, key=lambda j: vol[j])
    return prof, padre


def _orientar_consistente(c, n_vertices):
    """Da vuelta las caras necesarias para que las vecinas recorran cada arista en sentidos opuestos."""
    M = len(c)
    if not M:
        return c
    from scipy.sparse import coo_matrix, csr_matrix
    from scipy.sparse.csgraph import breadth_first_order, connected_components
    f1, f2, mismo, _ = _Topo(c, n_vertices).pares()
    clave = np.minimum(f1, f2) * M + np.maximum(f1, f2)
    _, unicos = np.unique(clave, return_index=True)
    f1, f2, mismo = f1[unicos], f2[unicos], mismo[unicos]
    _, comp = connected_components(coo_matrix((np.ones(len(f1)), (f1, f2)), shape=(M, M)), directed=False)
    raices = np.unique(comp, return_index=True)[1]
    filas = np.r_[f1, f2, np.full(len(raices), M)]
    cols = np.r_[f2, f1, raices]
    datos = np.r_[mismo, mismo, np.zeros(len(raices), bool)].astype(np.int8) + 1
    grafo = csr_matrix((datos, (filas, cols)), shape=(M + 1, M + 1))
    orden, pred = breadth_first_order(grafo, M, directed=True, return_predecessors=True)
    nodos = orden[1:]
    rel = (np.asarray(grafo[nodos, pred[nodos]]).ravel() == 2).tolist()
    girar = [False] * (M + 1)
    for i, p, r in zip(nodos.tolist(), pred[nodos].tolist(), rel, strict=True):
        girar[i] = girar[p] ^ r
    return _invertir(c, np.array(girar[:M], bool))


def _orientar_hacia_afuera(v, c):
    """Invierte las cáscaras cerradas con el signo de volumen equivocado: positivo las exteriores,
    negativo las que están dentro de otra (los huecos de un cuerpo vaciado)."""
    if not len(c):
        return c
    etiqueta, cerrada = _cascaras(c, len(v))
    prof, _ = _anidamiento(v, c, etiqueta, cerrada)
    t = v[c] - v.mean(0)
    vol = np.bincount(etiqueta, np.einsum("ij,ij->i", t[:, 0], np.cross(t[:, 1], t[:, 2])), len(cerrada))
    deseado = np.where(prof % 2 == 0, 1.0, -1.0)
    return _invertir(c, (cerrada & (vol * deseado < 0))[etiqueta])


# ---------------------------------------------------------------- triangulación de polígonos (tapas y agujeros)
def _cruz(o, a, b):
    return (a[..., 0] - o[..., 0]) * (b[..., 1] - o[..., 1]) - (a[..., 1] - o[..., 1]) * (b[..., 0] - o[..., 0])


def _area_2d(P):
    Q = np.roll(P, -1, axis=0)
    return 0.5 * float(np.sum(P[:, 0] * Q[:, 1] - Q[:, 0] * P[:, 1]))


def _punto_en_poligono(p, P):
    X, Y = P[:, 0], P[:, 1]
    X2, Y2 = np.roll(X, -1), np.roll(Y, -1)
    with np.errstate(divide="ignore", invalid="ignore"):
        cruza = ((Y > p[1]) != (Y2 > p[1])) & (p[0] < (X2 - X) * (p[1] - Y) / (Y2 - Y) + X)
    return bool(np.count_nonzero(cruza) % 2)


def _localmente_adentro(xy, pol, j, q):
    """¿La dirección hacia q sale de pol[j] hacia el interior del polígono (antihorario)?"""
    a, p, b = xy[pol[j - 1]], xy[pol[j]], xy[pol[(j + 1) % len(pol)]]
    if _cruz(a, p, b) >= 0:
        return _cruz(p, b, q) >= 0 and _cruz(p, q, a) >= 0
    return _cruz(p, b, q) >= 0 or _cruz(p, q, a) >= 0


def _anillos(xy, anillos):
    """Extremos (E0, E1) de las aristas de varios anillos cerrados."""
    e0 = [xy[a] for a in anillos]
    e1 = [xy[np.roll(a, -1)] for a in anillos]
    return np.concatenate(e0), np.concatenate(e1)


def _puentear(xy, exterior, agujeros):
    """Une los agujeros (horarios) al exterior (antihorario) con puentes de ida y vuelta (como earcut)."""
    pol = list(exterior)
    agujeros = sorted(agujeros, key=lambda a: -xy[a, 0].max())
    for n_ag, ag in enumerate(agujeros):
        k = int(np.argmax(xy[ag, 0]))
        h, hp = ag[k], xy[ag[k]]
        E0, E1 = _anillos(xy, [np.array(pol)] + [np.array(a) for a in agujeros[n_ag:]])
        P = xy[pol]
        elegido = None
        for j in np.argsort(np.linalg.norm(P - hp, axis=1))[:64].tolist():
            p = P[j]
            if not _localmente_adentro(xy, pol, j, hp):
                continue
            o1, o2 = _cruz(p, hp, E0), _cruz(p, hp, E1)
            o3, o4 = _cruz(E0, E1, p), _cruz(E0, E1, hp)
            if np.any((o1 * o2 < 0) & (o3 * o4 < 0)):
                continue
            elegido = j
            break
        if elegido is None:
            elegido = int(np.argmin(np.linalg.norm(P - hp, axis=1)))
        ciclo = list(ag[k:]) + list(ag[:k]) + [h]
        pol = pol[:elegido + 1] + ciclo + [pol[elegido]] + pol[elegido + 1:]
    return pol


def _orejas(xy, pol):
    """Triangulación por recorte de orejas de un polígono antihorario (admite puentes repetidos)."""
    pol = list(pol)
    escala = float(np.ptp(xy[pol], axis=0).max()) or 1.0
    eps = 1e-14 * escala * escala
    tol = 1e-12 * escala
    tris = []
    i = 0
    while len(pol) > 3:
        n = len(pol)
        P = xy[pol]
        prev, nxt = np.roll(P, 1, axis=0), np.roll(P, -1, axis=0)
        conv = _cruz(prev, P, nxt)
        R = P[conv <= eps]
        elegido = None
        for t in range(n):
            j = (i + t) % n
            if conv[j] <= eps:
                continue
            a, b, c = prev[j], P[j], nxt[j]
            if len(R):
                dentro = (_cruz(a, b, R) >= -eps) & (_cruz(b, c, R) >= -eps) & (_cruz(c, a, R) >= -eps)
                if dentro.any():
                    Rd = R[dentro]
                    propio = ((np.abs(Rd - a) <= tol).all(1) | (np.abs(Rd - b) <= tol).all(1)
                              | (np.abs(Rd - c) <= tol).all(1))
                    if not propio.all():
                        continue
            elegido = j
            break
        if elegido is None:                 # polígono numéricamente roto: se corta la oreja más convexa
            elegido = int(np.argmax(conv))
        tris.append((pol[elegido - 1], pol[elegido], pol[(elegido + 1) % n]))
        del pol[elegido]
        i = max(elegido - 1, 0) % len(pol)
    tris.append(tuple(pol))
    return tris


def _triangular_2d(xy, contornos):
    """Triangula regiones 2D limitadas por contornos cerrados (listas de índices a xy). Los exteriores y
    los agujeros se deducen por anidamiento (par/impar). Triángulos antihorarios (K x 3)."""
    contornos = [np.asarray(k, np.int64) for k in contornos if len(k) >= 3]
    if not contornos:
        return np.zeros((0, 3), np.int64)
    escala = float(np.ptp(xy, axis=0).max()) or 1.0
    areas = np.array([_area_2d(xy[k]) for k in contornos])
    utiles = [i for i in range(len(contornos)) if abs(areas[i]) > 1e-14 * escala * escala]
    if not utiles:                          # todo degenerado: abanico para no dejar el agujero abierto
        k = contornos[0]
        return np.array([(k[0], k[i], k[i + 1]) for i in range(1, len(k) - 1)], np.int64)
    contornos, areas = [contornos[i] for i in utiles], areas[utiles]
    n = len(contornos)
    contiene = np.zeros((n, n), bool)
    for i in range(n):
        p = xy[contornos[i][0]]
        for j in range(n):
            if j != i and abs(areas[j]) > abs(areas[i]):
                contiene[j, i] = _punto_en_poligono(p, xy[contornos[j]])
    prof = contiene.sum(0)
    tris = []
    for e in range(n):
        if prof[e] % 2:
            continue
        ext = contornos[e] if areas[e] > 0 else contornos[e][::-1]
        hijos = [h for h in range(n) if contiene[e, h] and prof[h] == prof[e] + 1]
        ags = [list(contornos[h] if areas[h] < 0 else contornos[h][::-1]) for h in hijos]
        pol = _puentear(xy, list(ext), ags) if ags else list(ext)
        tris.extend(_orejas(xy, pol))
    return np.array(tris, np.int64).reshape(-1, 3)


def _base(normal):
    """Ejes u, w del plano con u × w = normal."""
    n = np.asarray(normal, float)
    n = n / np.linalg.norm(n)
    u = np.cross(n, (1.0, 0.0, 0.0) if abs(n[0]) < 0.9 else (0.0, 1.0, 0.0))
    u /= np.linalg.norm(u)
    return u, np.cross(n, u)


def _triangular_lazos(v, lazos, normal):
    """Triangula lazos de vértices (casi) contenidos en un plano: caras con la normal del lado de `normal`."""
    u, w = _base(normal)
    todos = np.concatenate([np.asarray(lz, np.int64) for lz in lazos])
    xy = np.stack([v[todos] @ u, v[todos] @ w], axis=1)
    xy -= xy.mean(0)
    contornos, ini = [], 0
    for lz in lazos:
        contornos.append(np.arange(ini, ini + len(lz)))
        ini += len(lz)
    tris = _triangular_2d(xy, contornos)
    return todos[tris] if len(tris) else np.zeros((0, 3), np.int64)


def _lazos(medias):
    """Encadena medias aristas (a→b) en lazos cerrados [v0, v1, ...] (v_i → v_i+1). Las cadenas abiertas
    se descartan."""
    sig = {}
    for a, b in np.asarray(medias).tolist():
        sig.setdefault(a, []).append(b)
    lazos = []
    tope = len(medias) + 1
    for a0 in list(sig):
        while sig.get(a0):
            lazo, a = [a0], a0
            while True:
                lista = sig.get(a)
                if not lista or len(lazo) > tope:
                    lazo = None
                    break
                b = lista.pop()
                if b == a0:
                    break
                lazo.append(b)
                a = b
            if lazo and len(lazo) >= 3:
                lazos.append(lazo)
    return lazos


def _normal_poligono(P):
    c = P.mean(0)
    return np.cross(P - c, np.roll(P, -1, axis=0) - c).sum(0)


def _tapar_lazo(v, lazo):
    """Caras que tapan un lazo de borde (recorrido en el sentido de sus medias aristas libres)."""
    pol = np.asarray(lazo[::-1], np.int64)
    normal = _normal_poligono(v[pol])
    if np.linalg.norm(normal) <= 1e-12 * (_diagonal(v[pol]) ** 2 or 1.0):
        return np.array([(pol[0], pol[i], pol[i + 1]) for i in range(1, len(pol) - 1)], np.int64)
    return _triangular_lazos(v, [pol], normal)


def _rellenar_lazos(v, c, g, lazos):
    """Tapa cada lazo con triángulos (Close Holes); cada tapa es un grupo nuevo."""
    siguiente = int(g.max()) + 1 if len(g) else 0
    nuevas, grupos = [c], [g]
    for lazo in lazos:
        tapa = _tapar_lazo(v, lazo)
        nuevas.append(tapa)
        grupos.append(np.full(len(tapa), siguiente))
        siguiente += 1
    return np.vstack(nuevas), np.concatenate(grupos)


# ---------------------------------------------------------------- lectura y escritura
_DT_STL = np.dtype([("normal", "<f4", 3), ("v", "<f4", (3, 3)), ("attr", "<u2")])


def leer_stl(ruta, *, unidades="mm"):
    """Insertar malla desde STL ASCII o binario [MESH-INSERT-MESH]. `unidades`: en qué unidad está el archivo."""
    f = _factor(unidades)
    datos = Path(ruta).read_bytes()
    n = struct.unpack_from("<I", datos, 80)[0] if len(datos) >= 84 else -1
    if n >= 0 and len(datos) == 84 + 50 * n:
        tris = np.frombuffer(datos, _DT_STL, n, 84)["v"].astype(np.float64)
    elif datos.lstrip()[:5].lower() == b"solid":
        numeros = re.findall(rb"vertex\s+(\S+)\s+(\S+)\s+(\S+)", datos)
        try:
            tris = np.array(numeros, dtype=np.float64).reshape(-1, 3, 3)
        except ValueError as e:
            raise geo.ErrorGeometria("El STL ASCII tiene coordenadas inválidas o triángulos incompletos.") from e
    elif n >= 0 and len(datos) > 84 + 50 * n:
        tris = np.frombuffer(datos, _DT_STL, n, 84)["v"].astype(np.float64)
    else:
        raise geo.ErrorGeometria("El archivo no es un STL válido.")
    if not len(tris):
        raise geo.ErrorGeometria("El STL no tiene triángulos.")
    return Malla.desde_triangulos(tris * f)


def escribir_stl(m, ruta, *, binario=True, unidades="mm"):
    """Guardar como malla STL binario o ASCII [MESH-SAVE-AS-MESH]. El binario guarda float32 (norma STL);
    el ASCII guarda los float64 completos. Devuelve la cantidad de triángulos."""
    t = m.triangulos() / _factor(unidades)
    n = m.normales_caras()
    if binario:
        reg = np.zeros(len(t), _DT_STL)
        reg["normal"], reg["v"] = n, t
        with open(ruta, "wb") as fh:
            fh.write(b"OmniCAD STL".ljust(80, b" "))
            fh.write(struct.pack("<I", len(t)))
            fh.write(reg.tobytes())
    else:
        lineas = ["solid omnicad"]
        for nn, tt in zip(n.tolist(), t.tolist(), strict=True):
            lineas.append(f"  facet normal {nn[0]:.6e} {nn[1]:.6e} {nn[2]:.6e}\n    outer loop")
            lineas.extend(f"      vertex {p[0]!r} {p[1]!r} {p[2]!r}" for p in tt)
            lineas.append("    endloop\n  endfacet")
        lineas.append("endsolid omnicad\n")
        Path(ruta).write_text("\n".join(lineas), encoding="ascii")
    return len(t)


def leer_obj(ruta, *, unidades="mm"):
    """Insertar malla desde OBJ [MESH-INSERT-MESH]: polígonos en abanico; cada 'g'/'o' es un grupo de caras."""
    f = _factor(unidades)
    verts, caras, nombres = [], [], []
    actual = None
    with open(ruta, encoding="utf-8", errors="replace") as fh:
        for linea in fh:
            p = linea.split()
            if not p:
                continue
            try:
                if p[0] == "v":
                    verts.append((float(p[1]), float(p[2]), float(p[3])))
                elif p[0] == "f":
                    idx = [int(tok.split("/")[0]) for tok in p[1:]]
                    idx = [i - 1 if i > 0 else len(verts) + i for i in idx]
                    for k in range(1, len(idx) - 1):
                        caras.append((idx[0], idx[k], idx[k + 1]))
                        nombres.append(actual)
                elif p[0] in ("g", "o"):
                    actual = " ".join(p[1:]) or None
            except (ValueError, IndexError) as e:
                raise geo.ErrorGeometria(f"El OBJ tiene una línea inválida: {linea.strip()[:60]}") from e
    if not caras:
        raise geo.ErrorGeometria("El OBJ no tiene caras.")
    ids = {}
    for nombre in dict.fromkeys(nombres):
        coincide = re.fullmatch(r"grupo_(-?\d+)", nombre or "")
        if coincide:
            ids[nombre] = int(coincide.group(1))
    siguiente = max(ids.values(), default=-1) + 1
    for nombre in dict.fromkeys(nombres):
        if nombre not in ids:
            ids[nombre], siguiente = siguiente, siguiente + 1
    return Malla(np.array(verts) * f, caras, [ids[nm] for nm in nombres])


def escribir_obj(m, ruta, *, unidades="mm", nombre="malla"):
    """Guardar como OBJ [MESH-SAVE-AS-MESH] con un 'g grupo_N' por grupo de caras (se recuperan al leer)."""
    v = m.vertices / _factor(unidades)
    lineas = [f"# OmniCAD OBJ, unidades: {unidades}", f"o {nombre}"]
    lineas += [f"v {x!r} {y!r} {z!r}" for x, y, z in v.tolist()]
    previo = None
    for (a, b, c), g in zip((m.caras + 1).tolist(), m.grupos.tolist(), strict=True):
        if g != previo:
            lineas.append(f"g grupo_{g}")
            previo = g
        lineas.append(f"f {a} {b} {c}")
    Path(ruta).write_text("\n".join(lineas) + "\n", encoding="utf-8")
    return len(m.caras)


_TIPOS_3MF = ('<?xml version="1.0" encoding="UTF-8"?>\n'
              '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
              '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
              '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>'
              '</Types>')
_RELS_3MF = ('<?xml version="1.0" encoding="UTF-8"?>\n'
             '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
             '<Relationship Target="/3D/3dmodel.model" Id="rel0" '
             'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
_NS_3MF = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"


def escribir_3mf(m, ruta, *, unidades="mm"):
    """Guardar como 3MF [MESH-SAVE-AS-MESH]: un objeto malla, unidad declarada en el archivo."""
    v = m.vertices / _factor(unidades)
    partes = ['<?xml version="1.0" encoding="UTF-8"?>',
              f'<model unit="{_NOMBRE_3MF[unidades]}" xml:lang="es-AR" xmlns="{_NS_3MF}">',
              '<metadata name="Application">OmniCAD</metadata>',
              '<resources><object id="1" type="model"><mesh><vertices>']
    partes += [f'<vertex x="{x!r}" y="{y!r}" z="{z!r}"/>' for x, y, z in v.tolist()]
    partes.append("</vertices><triangles>")
    partes += [f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in m.caras.tolist()]
    partes.append('</triangles></mesh></object></resources><build><item objectid="1"/></build></model>')
    with zipfile.ZipFile(ruta, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", _TIPOS_3MF)
        z.writestr("_rels/.rels", _RELS_3MF)
        z.writestr("3D/3dmodel.model", "\n".join(partes))
    return len(m.caras)


def _transformada_3mf(texto):
    """Matriz 4x3 de 3MF (p' = p·M + t); identidad si no hay atributo."""
    if not texto:
        return np.vstack([np.eye(3), np.zeros(3)])
    return np.array(texto.split(), float).reshape(4, 3)


def leer_3mf(ruta, *, unidades=None):
    """Insertar malla desde 3MF [MESH-INSERT-MESH]. Usa la unidad declarada en el archivo salvo que se
    indique `unidades`. Aplica las transformadas del armado y de los componentes; un grupo por objeto."""
    try:
        with zipfile.ZipFile(ruta) as z:
            nombre = "3D/3dmodel.model"
            if "_rels/.rels" in z.namelist():
                for r in ET.fromstring(z.read("_rels/.rels")).iter():
                    if r.get("Type", "").endswith("/3dmodel") and r.get("Target"):
                        nombre = r.get("Target").lstrip("/")
            raiz = ET.fromstring(z.read(nombre))
    except (zipfile.BadZipFile, KeyError, ET.ParseError) as e:
        raise geo.ErrorGeometria(f"El archivo no es un 3MF válido: {e}") from e
    ns = raiz.tag[1:].split("}")[0] if raiz.tag.startswith("{") else ""

    def q(etiqueta):
        return f"{{{ns}}}{etiqueta}" if ns else etiqueta

    if unidades is not None:
        f = _factor(unidades)
    else:
        unidad = raiz.get("unit", "millimeter")
        if unidad not in _UNIDADES_3MF:
            raise geo.ErrorGeometria(f"Unidad 3MF desconocida: {unidad}")
        f = _UNIDADES_3MF[unidad]
    objetos = {o.get("id"): o for o in raiz.iter(q("object"))}
    tris, grupos = [], []

    def agregar(oid, T, profundidad):
        obj = objetos.get(oid)
        if obj is None or profundidad > 16:
            raise geo.ErrorGeometria(f"El 3MF referencia un objeto inexistente o anidado de más: {oid}")
        malla = obj.find(q("mesh"))
        if malla is not None:
            V = np.array([(float(e.get("x")), float(e.get("y")), float(e.get("z")))
                          for e in malla.find(q("vertices"))], float).reshape(-1, 3)
            C = np.array([(int(e.get("v1")), int(e.get("v2")), int(e.get("v3")))
                          for e in malla.find(q("triangles"))], np.int64).reshape(-1, 3)
            if np.linalg.det(T[:3]) < 0:
                C = C[:, [0, 2, 1]]
            tris.append((V @ T[:3] + T[3])[C])
            grupos.append(np.full(len(C), len(grupos)))
        comps = obj.find(q("components"))
        for comp in comps if comps is not None else []:
            Tc = _transformada_3mf(comp.get("transform"))
            agregar(comp.get("objectid"), np.vstack([Tc[:3] @ T[:3], Tc[3] @ T[:3] + T[3]]), profundidad + 1)

    armado = raiz.find(q("build"))
    try:
        for item in armado if armado is not None else []:
            agregar(item.get("objectid"), _transformada_3mf(item.get("transform")), 0)
    except (TypeError, ValueError, IndexError) as e:
        raise geo.ErrorGeometria(f"El 3MF tiene datos de malla inválidos: {e}") from e
    if not tris:
        raise geo.ErrorGeometria("El 3MF no tiene mallas.")
    return Malla.desde_triangulos(np.concatenate(tris) * f, np.concatenate(grupos))


_TIPOS_PLY = {"char": "i1", "int8": "i1", "uchar": "u1", "uint8": "u1", "short": "i2", "int16": "i2",
              "ushort": "u2", "uint16": "u2", "int": "i4", "int32": "i4", "uint": "u4", "uint32": "u4",
              "float": "f4", "float32": "f4", "double": "f8", "float64": "f8"}


def _abanico(idx):
    return [(idx[0], idx[k], idx[k + 1]) for k in range(1, len(idx) - 1)]


def _ply_lista_caras(props):
    for i, (nombre, _tipo, cuenta) in enumerate(props):
        if cuenta is not None and nombre in ("vertex_indices", "vertex_index"):
            return i
    raise geo.ErrorGeometria("El PLY no tiene la lista 'vertex_indices' en las caras.")


def _ply_vertices(arr_o_columnas, nombres):
    try:
        return np.stack([np.asarray(arr_o_columnas[nombres.index(k)], float) for k in "xyz"], axis=1)
    except ValueError as e:
        raise geo.ErrorGeometria("El PLY no tiene las coordenadas x, y, z.") from e


def _ply_ascii(cuerpo, elementos):
    lineas = [ln for ln in cuerpo.decode("ascii", "replace").splitlines() if ln.strip()]
    pos, V, C = 0, None, []
    for nombre, n, props in elementos:
        bloque = lineas[pos:pos + n]
        pos += n
        if nombre == "vertex":
            arr = np.array([ln.split()[:len(props)] for ln in bloque], float).reshape(n, len(props))
            V = _ply_vertices(arr.T, [p[0] for p in props])
        elif nombre == "face":
            k_lista = _ply_lista_caras(props)
            for ln in bloque:
                t, i = ln.split(), 0
                for k, (_nombre, _tipo, cuenta) in enumerate(props):
                    if cuenta is None:
                        i += 1
                        continue
                    cant = int(t[i])
                    if k == k_lista:
                        C.extend(_abanico([int(x) for x in t[i + 1:i + 1 + cant]]))
                    i += 1 + cant
    return V, C


def _ply_binario(cuerpo, elementos, orden):
    off, V, C = 0, None, []
    for nombre, n, props in elementos:
        if all(cuenta is None for _n, _t, cuenta in props):
            dt = np.dtype([(pn, orden + tp) for pn, tp, _c in props])
            arr = np.frombuffer(cuerpo, dt, n, off)
            off += n * dt.itemsize
            if nombre == "vertex":
                V = _ply_vertices([arr[p[0]] for p in props], [p[0] for p in props])
            continue
        k_lista = _ply_lista_caras(props) if nombre == "face" else -1
        campos = []
        for pn, tp, cuenta in props:
            campos += [(pn, orden + tp)] if cuenta is None else [(pn + "__n", orden + cuenta), (pn, orden + tp, 3)]
        dt = np.dtype(campos)
        if off + n * dt.itemsize <= len(cuerpo):          # camino rápido: todas las listas de 3
            arr = np.frombuffer(cuerpo, dt, n, off)
            if all(np.all(arr[pn + "__n"] == 3) for pn, _t, cuenta in props if cuenta is not None):
                off += n * dt.itemsize
                if k_lista >= 0:
                    C.extend(map(tuple, arr[props[k_lista][0]].astype(np.int64).tolist()))
                continue
        for _ in range(n):                                  # camino general: polígonos de largo variable
            for k, (_pn, tp, cuenta) in enumerate(props):
                if cuenta is None:
                    off += np.dtype(tp).itemsize
                    continue
                cant = int(np.frombuffer(cuerpo, orden + cuenta, 1, off)[0])
                off += np.dtype(cuenta).itemsize
                lista = np.frombuffer(cuerpo, orden + tp, cant, off).astype(np.int64).tolist()
                off += cant * np.dtype(tp).itemsize
                if k == k_lista:
                    C.extend(_abanico(lista))
    return V, C


def leer_ply(ruta, *, unidades="mm"):
    """Insertar malla desde PLY ASCII o binario (little/big endian); polígonos en abanico."""
    f = _factor(unidades)
    datos = Path(ruta).read_bytes()
    fin = datos.find(b"end_header")
    if not datos.startswith(b"ply") or fin < 0:
        raise geo.ErrorGeometria("El archivo no es un PLY válido.")
    formato, elementos = None, []
    try:
        for linea in datos[:fin].decode("ascii", "replace").splitlines():
            p = linea.split()
            if not p:
                continue
            if p[0] == "format":
                formato = p[1]
            elif p[0] == "element":
                elementos.append((p[1], int(p[2]), []))
            elif p[0] == "property":
                if p[1] == "list":
                    elementos[-1][2].append((p[4], _TIPOS_PLY[p[3]], _TIPOS_PLY[p[2]]))
                else:
                    elementos[-1][2].append((p[2], _TIPOS_PLY[p[1]], None))
        cuerpo = datos[datos.index(b"\n", fin) + 1:]
        if formato == "ascii":
            V, C = _ply_ascii(cuerpo, elementos)
        elif formato in ("binary_little_endian", "binary_big_endian"):
            V, C = _ply_binario(cuerpo, elementos, "<" if formato == "binary_little_endian" else ">")
        else:
            raise geo.ErrorGeometria(f"Formato PLY no soportado: {formato}")
    except (KeyError, IndexError, ValueError) as e:
        raise geo.ErrorGeometria(f"El PLY está dañado o usa un tipo no soportado: {e}") from e
    if V is None or not C:
        raise geo.ErrorGeometria("El PLY no tiene vértices o caras.")
    return Malla(V * f, C)


def escribir_ply(m, ruta, *, binario=True, unidades="mm"):
    """Guarda como PLY (vértices en double, caras como lista de 3 índices)."""
    v = m.vertices / _factor(unidades)
    cab = ["ply", f"format {'binary_little_endian' if binario else 'ascii'} 1.0",
           f"comment OmniCAD, unidades: {unidades}", f"element vertex {len(v)}",
           "property double x", "property double y", "property double z",
           f"element face {len(m.caras)}", "property list uchar int vertex_indices", "end_header"]
    if binario:
        caras = np.zeros(len(m.caras), np.dtype([("n", "u1"), ("i", "<i4", 3)]))
        caras["n"], caras["i"] = 3, m.caras
        with open(ruta, "wb") as fh:
            fh.write(("\n".join(cab) + "\n").encode("ascii"))
            fh.write(v.astype("<f8").tobytes())
            fh.write(caras.tobytes())
    else:
        lineas = cab + [f"{x!r} {y!r} {z!r}" for x, y, z in v.tolist()]
        lineas += [f"3 {a} {b} {c}" for a, b, c in m.caras.tolist()]
        Path(ruta).write_text("\n".join(lineas) + "\n", encoding="ascii")
    return len(m.caras)


_LECTORES = {".stl": leer_stl, ".obj": leer_obj, ".3mf": leer_3mf, ".ply": leer_ply}
_ESCRITORES = {".stl": escribir_stl, ".obj": escribir_obj, ".3mf": escribir_3mf, ".ply": escribir_ply}


def leer(ruta, **opciones):
    """Lee una malla eligiendo el formato por la extensión (.stl, .obj, .3mf, .ply)."""
    ext = Path(ruta).suffix.lower()
    if ext not in _LECTORES:
        raise geo.ErrorGeometria(f"Formato de malla no soportado: {ext} (usá .stl, .obj, .3mf o .ply)")
    return _LECTORES[ext](ruta, **opciones)


def escribir(m, ruta, **opciones):
    """Guarda una malla eligiendo el formato por la extensión (.stl, .obj, .3mf, .ply)."""
    ext = Path(ruta).suffix.lower()
    if ext not in _ESCRITORES:
        raise geo.ErrorGeometria(f"Formato de malla no soportado: {ext} (usá .stl, .obj, .3mf o .ply)")
    return _ESCRITORES[ext](m, ruta, **opciones)


# ---------------------------------------------------------------- desde B-rep
_REFINAMIENTO = {"bajo": (2e-3, 30.0), "medio": (5e-4, 15.0), "alto": (1e-4, 8.0)}


def desde_brep(forma, *, refinamiento="medio", desviacion=None, angulo=None):
    """Teselar [MESH-TESSELLATE]: sólido o superficie → malla, un grupo de caras por cara B-rep.
    refinamiento 'bajo' | 'medio' | 'alto' (desvío = 0,2 % / 0,05 % / 0,01 % de la diagonal de la caja y
    30° / 15° / 8°; Fusion no publica sus valores) o 'personalizado'. `desviacion` (mm, Surface Deviation)
    y `angulo` (grados, Normal Deviation) pisan al preset."""
    if refinamiento not in (*_REFINAMIENTO, "personalizado"):
        raise geo.ErrorGeometria(f"Refinamiento desconocido: {refinamiento}")
    if refinamiento == "personalizado" and desviacion is None and angulo is None:
        raise geo.ErrorGeometria("El refinamiento personalizado necesita desviacion y/o angulo.")
    caja = geo.caja_envolvente(forma) if forma is not None else None
    if caja is None:
        raise geo.ErrorGeometria("La forma no tiene geometría para teselar.")
    diag = float(np.linalg.norm(np.subtract(caja[1], caja[0])))
    frac, ang = _REFINAMIENTO.get(refinamiento, _REFINAMIENTO["medio"])
    desv = float(desviacion) if desviacion is not None else frac * diag
    ang = float(angulo) if angulo is not None else ang
    if desv <= 0 or not 0 < ang < 180:
        raise geo.ErrorGeometria("La desviación debe ser positiva y el ángulo estar entre 0° y 180°.")
    copia = BRepBuilderAPI_Copy(forma, True, False).Shape()   # sin la malla de visualización previa
    tris, grupos = [], []
    for k, (_cara, t) in enumerate(geo.teselar_por_cara(copia, desv, math.radians(ang))):
        tris.append(t)
        grupos.append(np.full(len(t), k))
    if not tris:
        raise geo.ErrorGeometria("La forma no tiene caras para teselar.")
    m = Malla.desde_triangulos(np.concatenate(tris), np.concatenate(grupos))
    return _soldar(m, 1e-7 * diag)


# ---------------------------------------------------------------- reparar
def _soldar(m, tolerancia):
    """Une los vértices a menos de `tolerancia` (0 = idénticos) y quita las caras que quedan degeneradas."""
    v, c = m.vertices, m.caras
    if not len(c):
        return m.copia()
    if tolerancia > 0:
        from scipy.sparse import coo_matrix
        from scipy.sparse.csgraph import connected_components
        from scipy.spatial import cKDTree
        pares = cKDTree(v).query_pairs(tolerancia, output_type="ndarray")
        if len(pares):
            N = len(v)
            ncomp, etiqueta = connected_components(
                coo_matrix((np.ones(len(pares)), (pares[:, 0], pares[:, 1])), shape=(N, N)), directed=False)
            rep = np.full(ncomp, N)
            np.minimum.at(rep, etiqueta, np.arange(N))
            c = rep[etiqueta][c]
    else:
        _, primero, inv = np.unique(v, axis=0, return_index=True, return_inverse=True)
        c = primero[inv.reshape(-1)][c]
    ok = (c[:, 0] != c[:, 1]) & (c[:, 1] != c[:, 2]) & (c[:, 0] != c[:, 2])
    return _compactar(v, c[ok], m.grupos[ok])


def _sin_degenerados(m):
    """Quita las caras con índices repetidos o área ~0."""
    c = m.caras
    ok = (c[:, 0] != c[:, 1]) & (c[:, 1] != c[:, 2]) & (c[:, 0] != c[:, 2])
    ok &= m.areas_caras() > (1e-9 * (_diagonal(m.vertices) or 1.0)) ** 2
    return _compactar(m.vertices, c[ok], m.grupos[ok])


def _corregir_degenerados(m):
    """Caras de área ~0 con tres vértices distintos (alineados): se voltea su arista más larga con la
    vecina (quedan dos triángulos sanos); si no hay vecina, se quita."""
    v, c = m.vertices, m.caras.copy()
    areas = m.areas_caras()
    malas = np.flatnonzero(areas <= (1e-9 * (_diagonal(v) or 1.0)) ** 2)
    if not len(malas):
        return m
    duenio = {(a, b): k // 3 for k, (a, b) in enumerate(_medias_aristas(c).tolist())}
    tocadas, quitar = set(), []
    for f in malas.tolist():
        cf = c[f].tolist()
        largos = [np.linalg.norm(v[cf[(r + 1) % 3]] - v[cf[r]]) for r in range(3)]
        r = int(np.argmax(largos))
        i, j, k = cf[r], cf[(r + 1) % 3], cf[(r + 2) % 3]
        vecina = duenio.get((j, i))
        if vecina is None or vecina in tocadas or f in tocadas or areas[vecina] <= areas[f]:
            quitar.append(f)
            continue
        cv = c[vecina].tolist()
        d = next(x for x in cv if x not in (i, j))
        c[f], c[vecina] = (i, d, k), (d, j, k)
        tocadas.update((f, vecina))
    ok = np.ones(len(c), bool)
    ok[quitar] = False
    return _compactar(v, c[ok], m.grupos[ok])


def _quitar_duplicadas(m):
    """Deja una sola cara por terna de vértices (las caras dobles se quitan)."""
    _, primero = np.unique(np.sort(m.caras, axis=1), axis=0, return_index=True)
    primero = np.sort(primero)
    return Malla(m.vertices, m.caras[primero], m.grupos[primero])


def _quitar_cascaras_chicas(m, umbral):
    """Quita las cáscaras cuyo área es menor que `umbral` (fracción del área total)."""
    if umbral <= 0 or not len(m.caras):
        return m
    etiqueta, _ = _cascaras(m.caras, len(m.vertices))
    areas = m.areas_caras()
    por_cascara = np.bincount(etiqueta, areas)
    ok = por_cascara[etiqueta] >= umbral * areas.sum()
    return _compactar(m.vertices, m.caras[ok], m.grupos[ok])


def reparar(m, *, tipo="cerrar_agujeros", tolerancia=None, umbral_cascara=0.001, densidad=1.0):
    """Reparar [MESH-REPAIR]. Tipos:
    - 'unir_vertices': une los vértices a menos de `tolerancia` y quita las caras que se degeneran.
    - 'cerrar_agujeros' (Close Holes): une vértices idénticos, orienta las normales de forma consistente,
      tapa los agujeros (recorte de orejas por lazo de borde) y deja el volumen positivo.
    - 'coser_y_quitar' (Stitch and Remove): además cose con `tolerancia`, corrige caras degeneradas, quita
      caras dobles y cáscaras con menos de `umbral_cascara` del área total.
    - 'reconstruir' (Rebuild): 'coser_y_quitar' + remallado uniforme con `densidad`.
    tolerancia: mm (por defecto una millonésima de la diagonal de la caja)."""
    tipos = ("cerrar_agujeros", "unir_vertices", "coser_y_quitar", "reconstruir")
    if tipo not in tipos:
        raise geo.ErrorGeometria(f"Tipo de reparación desconocido: {tipo} (usá {', '.join(tipos)}).")
    if not len(m.caras):
        raise geo.ErrorGeometria("La malla está vacía.")
    tol = 1e-6 * _diagonal(m.vertices) if tolerancia is None else float(tolerancia)
    if tol < 0:
        raise geo.ErrorGeometria("La tolerancia no puede ser negativa.")
    if tipo == "unir_vertices":
        return _soldar(m, tol)
    if tipo == "cerrar_agujeros":
        r = _soldar(m, 0.0)
    else:
        r = _quitar_cascaras_chicas(_quitar_duplicadas(_corregir_degenerados(_soldar(m, tol))), umbral_cascara)
    v, g = r.vertices, r.grupos
    c = _orientar_consistente(r.caras, len(v))
    c, g = _rellenar_lazos(v, c, g, _lazos(_Topo(c, len(v)).libres()))
    r = Malla(v, _orientar_hacia_afuera(v, c), g)
    return remallar(r, densidad=densidad) if tipo == "reconstruir" else r


# ---------------------------------------------------------------- grupos de caras
def generar_grupos(m, *, angulo=30.0, tamano_minimo=0.0):
    """Generar grupos de caras, método rápido [MESH-GENERATE-FACE-GROUPS]: crecimiento de regiones que une
    caras vecinas cuyas normales difieren menos de `angulo` (Angle Threshold). `tamano_minimo`
    (Minimum Face Group Size): fracción 0-1 del área total; los grupos más chicos se suman al vecino con
    el que comparten más borde."""
    if not 0 < angulo < 180:
        raise geo.ErrorGeometria("El ángulo debe estar entre 0° y 180°.")
    if not 0 <= tamano_minimo < 1:
        raise geo.ErrorGeometria("El tamaño mínimo es una fracción entre 0 y 1.")
    M = len(m.caras)
    if not M:
        return m.copia()
    topo = _Topo(m.caras, len(m.vertices))
    f1, f2, _, arista = topo.pares()
    n = m.normales_caras()
    juntas = np.einsum("ij,ij->i", n[f1], n[f2]) >= math.cos(math.radians(angulo))
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    grafo = coo_matrix((np.ones(int(juntas.sum())), (f1[juntas], f2[juntas])), shape=(M, M))
    etiqueta = _reetiquetar(connected_components(grafo, directed=False)[1])
    if tamano_minimo > 0:
        areas = m.areas_caras()
        umbral = tamano_minimo * areas.sum()
        largo = np.linalg.norm(m.vertices[topo.aristas[arista, 0]] - m.vertices[topo.aristas[arista, 1]], axis=1)
        aislados = set()
        while True:
            k = int(etiqueta.max()) + 1
            ag = np.bincount(etiqueta, areas, k)
            chicos = [i for i in np.argsort(ag).tolist() if 0 < ag[i] < umbral and i not in aislados]
            if not chicos:
                break
            g0 = chicos[0]
            la, lb = etiqueta[f1], etiqueta[f2]
            borde = (la == g0) != (lb == g0)
            if not borde.any():
                aislados.add(g0)
                continue
            otros = np.where(la[borde] == g0, lb[borde], la[borde])
            etiqueta[etiqueta == g0] = int(np.argmax(np.bincount(otros, largo[borde], k)))
        etiqueta = _reetiquetar(etiqueta)
    return Malla(m.vertices, m.caras, etiqueta)


def combinar_grupos(m, ids):
    """Combinar grupos de caras [MESH-COMBINE-FACE-GROUPS]: todos pasan al id más chico. Tienen que estar
    unidos por aristas compartidas (como en Fusion)."""
    ids = np.unique(np.asarray(list(ids), np.int64))
    if len(ids) < 2:
        raise geo.ErrorGeometria("Elegí al menos dos grupos para combinar.")
    faltan = np.setdiff1d(ids, m.grupos)
    if len(faltan):
        raise geo.ErrorGeometria(f"La malla no tiene los grupos {faltan.tolist()}.")
    f1, f2, _, _ = _Topo(m.caras, len(m.vertices)).pares(solo_manifold=False)
    ga, gb = m.grupos[f1], m.grupos[f2]
    sel = np.isin(ga, ids) & np.isin(gb, ids) & (ga != gb)
    a, b = np.searchsorted(ids, ga[sel]), np.searchsorted(ids, gb[sel])
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    ncomp, _ = connected_components(coo_matrix((np.ones(len(a)), (a, b)), shape=(len(ids), len(ids))),
                                    directed=False)
    if ncomp > 1:
        raise geo.ErrorGeometria("Los grupos a combinar tienen que estar unidos por aristas compartidas.")
    g = m.grupos.copy()
    g[np.isin(g, ids)] = ids[0]
    return Malla(m.vertices, m.caras, g)


# ---------------------------------------------------------------- edición por aristas (reducir, remallar)
class _Editor:
    """Malla editable (colapsar, dividir y voltear aristas) que usan Reducir y Remallar."""

    def __init__(self, v, c, g):
        self.v = np.array(v, float)
        self.nv = len(self.v)
        self.c = [list(f) for f in np.asarray(c).tolist()]
        self.g = list(np.asarray(g).tolist())
        self.viva = [True] * len(self.c)
        self.vivo = [True] * self.nv
        self.fijo = [False] * self.nv
        self.vf = [set() for _ in range(self.nv)]
        for i, f in enumerate(self.c):
            for x in f:
                self.vf[x].add(i)
        self.rasgo, self.vr = set(), {}      # aristas (a<b) a respetar y sus vecinos por vértice
        self.area_min = (1e-9 * (_diagonal(self.v) or 1.0)) ** 2

    def _nuevo_vertice(self, p):
        if self.nv == len(self.v):
            self.v = np.vstack([self.v, np.zeros((max(self.nv, 16), 3))])
        self.v[self.nv] = p
        self.nv += 1
        self.vf.append(set())
        self.vivo.append(True)
        self.fijo.append(False)
        return self.nv - 1

    def poner_rasgo(self, a, b):
        self.rasgo.add((min(a, b), max(a, b)))
        self.vr.setdefault(a, set()).add(b)
        self.vr.setdefault(b, set()).add(a)

    def _quitar_rasgo(self, a, b):
        self.rasgo.discard((min(a, b), max(a, b)))
        self.vr.get(a, set()).discard(b)
        self.vr.get(b, set()).discard(a)

    def es_rasgo(self, a, b):
        return (min(a, b), max(a, b)) in self.rasgo

    def grado_rasgo(self, a):
        return len(self.vr.get(a, ()))

    def vecinos(self, a):
        s = set()
        for f in self.vf[a]:
            s.update(self.c[f])
        s.discard(a)
        return s

    def en_borde(self, a):
        return any(len(self.vf[a] & self.vf[b]) == 1 for b in self.vecinos(a))

    def _opuesto(self, f, x, y):
        cf = self.c[f]
        for r in range(3):
            if cf[r] == x and cf[(r + 1) % 3] == y:
                return cf[(r + 2) % 3]
        return None

    def _sin_pliegues(self, caras, mover, p, umbral=0.2):
        if not caras:
            return True
        F = np.array([self.c[f] for f in caras])
        P = self.v[F]
        Q = P.copy()
        for x in mover:
            Q[F == x] = p
        antes = np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0])
        despues = np.cross(Q[:, 1] - Q[:, 0], Q[:, 2] - Q[:, 0])
        la, ld = np.linalg.norm(antes, axis=1), np.linalg.norm(despues, axis=1)
        return bool(np.all((ld > self.area_min) & (np.einsum("ij,ij->i", antes, despues) > umbral * la * ld)))

    def colapsable(self, a, b, p):
        comunes = self.vf[a] & self.vf[b]
        if len(comunes) not in (1, 2):
            return False
        opuestos = {x for f in comunes for x in self.c[f]} - {a, b}
        na, nb = self.vecinos(a), self.vecinos(b)
        if (na & nb) != opuestos or len((na | nb) - {a, b}) < 3:
            return False
        if len(comunes) == 2 and self.en_borde(a) and self.en_borde(b):
            return False
        if any(len(self.vecinos(o)) <= 3 for o in opuestos):
            return False
        return self._sin_pliegues(list((self.vf[a] | self.vf[b]) - comunes), (a, b), p)

    def colapsar(self, a, b, p):
        """Une b en a (a queda en p). Devuelve cuántas caras desaparecen."""
        comunes = self.vf[a] & self.vf[b]
        for f in comunes:
            self.viva[f] = False
            for x in self.c[f]:
                self.vf[x].discard(f)
        for f in self.vf[b]:
            cf = self.c[f]
            cf[cf.index(b)] = a
            self.vf[a].add(f)
        self.vf[b] = set()
        self.vivo[b] = False
        self.v[a] = p
        for x in self.vr.pop(b, set()):
            self._quitar_rasgo(b, x)
            if x != a:
                self.poner_rasgo(a, x)
        return len(comunes)

    def dividir(self, a, b):
        m = self._nuevo_vertice((self.v[a] + self.v[b]) / 2)
        for f in list(self.vf[a] & self.vf[b]):
            cf = self.c[f]
            r = next(r for r in range(3) if {cf[r], cf[(r + 1) % 3]} == {a, b})
            x, y, z = cf[r], cf[(r + 1) % 3], cf[(r + 2) % 3]
            self.c[f] = [x, m, z]
            self.vf[y].discard(f)
            self.vf[m].add(f)
            self.c.append([m, y, z])
            self.g.append(self.g[f])
            self.viva.append(True)
            for w in (m, y, z):
                self.vf[w].add(len(self.c) - 1)
        if self.es_rasgo(a, b):
            self._quitar_rasgo(a, b)
            self.poner_rasgo(a, m)
            self.poner_rasgo(m, b)
        return m

    def voltear(self, a, b):
        comunes = list(self.vf[a] & self.vf[b])
        if len(comunes) != 2:
            return False
        f1, f2 = comunes
        o1 = self._opuesto(f1, a, b)
        if o1 is None:
            f1, f2 = f2, f1
            o1 = self._opuesto(f1, a, b)
        o2 = self._opuesto(f2, b, a)
        if o1 is None or o2 is None or o1 == o2 or o2 in self.vecinos(o1):
            return False
        nuevas = [[a, o2, o1], [o2, b, o1]]
        P = self.v[np.array([self.c[f1], self.c[f2]])]
        n_viejo = np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0]).sum(0)
        Q = self.v[np.array(nuevas)]
        n_nuevo = np.cross(Q[:, 1] - Q[:, 0], Q[:, 2] - Q[:, 0])
        largo = np.linalg.norm(n_nuevo, axis=1)
        if np.any(largo <= self.area_min) or np.any(n_nuevo @ n_viejo <= 0.3 * largo * np.linalg.norm(n_viejo)):
            return False
        self.c[f1], self.c[f2] = nuevas
        self.vf[b].discard(f1)
        self.vf[o2].add(f1)
        self.vf[a].discard(f2)
        self.vf[o1].add(f2)
        return True

    def caras_vivas(self):
        return np.array([f for f, viva in zip(self.c, self.viva, strict=True) if viva], np.int64).reshape(-1, 3)

    def aristas(self):
        F = self.caras_vivas()
        e = np.sort(F[:, [0, 1, 1, 2, 2, 0]].reshape(-1, 2), axis=1)
        return np.unique(e, axis=0)

    def exportar(self):
        g = np.array([x for x, viva in zip(self.g, self.viva, strict=True) if viva], np.int64)
        return _compactar(self.v[:self.nv], self.caras_vivas(), g)


def _optimo_qem(Q, pa, pb):
    """Costo y punto óptimo de colapsar aristas con cuádricas Q (Kx4x4): resuelve el sistema 3x3 y, si es
    singular, elige entre los extremos y el punto medio."""
    A, b, cc = Q[:, :3, :3], Q[:, :3, 3], Q[:, 3, 3]

    def costo(p):
        return np.einsum("ki,kij,kj->k", p, A, p) + 2 * np.einsum("ki,ki->k", b, p) + cc

    medio = (pa + pb) / 2
    escala = np.maximum(np.einsum("kii->k", A) / 3, 1e-300)
    ok = np.abs(np.linalg.det(A)) > 1e-9 * escala ** 3
    opt = medio.copy()
    if ok.any():
        opt[ok] = np.linalg.solve(A[ok], -b[ok][..., None])[..., 0]
    ok &= np.linalg.norm(opt - medio, axis=1) <= 2 * np.linalg.norm(pb - pa, axis=1)
    candidatos = [pa, pb, medio, opt]
    costos = np.stack([costo(p) for p in candidatos])
    costos[3, ~ok] = np.inf
    mejor = np.argmin(costos, axis=0)
    puntos = np.stack(candidatos)[mejor, np.arange(len(pa))]
    return np.maximum(costos[mejor, np.arange(len(pa))], 0.0), puntos


def _cuadricas(v, c, g, peso=1e3):
    """Cuádricas de error por vértice: planos de las caras + planos de penalización perpendiculares en los
    bordes abiertos y en los bordes entre grupos (para que no se deformen)."""
    nf = np.cross(v[c[:, 1]] - v[c[:, 0]], v[c[:, 2]] - v[c[:, 0]])
    largo = np.linalg.norm(nf, axis=1, keepdims=True)
    largo[largo == 0] = 1.0
    nf = nf / largo
    planos = np.c_[nf, -np.einsum("ij,ij->i", nf, v[c[:, 0]])]
    Q = np.zeros((len(v), 4, 4))
    K = planos[:, :, None] * planos[:, None, :]
    for k in range(3):
        np.add.at(Q, c[:, k], K)
    topo = _Topo(c, len(v))
    libres = np.flatnonzero(topo.cuenta[topo.inv] == 1)
    f1, f2, _, _ = topo.pares()
    distintos = np.flatnonzero(g[f1] != g[f2])
    h1 = topo.h1[topo.cuenta[topo.inv[topo.h1]] == 2]
    h2 = topo.h2[topo.cuenta[topo.inv[topo.h2]] == 2]
    hes = np.r_[libres, h1[distintos], h2[distintos]]
    if len(hes):
        a, b = topo.he[hes, 0], topo.he[hes, 1]
        pn = np.cross(v[b] - v[a], nf[hes // 3])
        lp = np.linalg.norm(pn, axis=1, keepdims=True)
        lp[lp == 0] = 1.0
        pn = pn / lp
        pl = np.c_[pn, -np.einsum("ij,ij->i", pn, v[a])]
        Kp = peso * pl[:, :, None] * pl[:, None, :]
        np.add.at(Q, a, Kp)
        np.add.at(Q, b, Kp)
    return Q


def reducir(m, *, objetivo_caras=None, proporcion=None, tolerancia=None, preservar_bordes=True):
    """Reducir [MESH-REDUCE]: decimación por colapso de aristas con error cuadrático (Garland-Heckbert).
    Tipos de Fusion: Face Count (`objetivo_caras`), Proportion (`proporcion` 0-1 de las caras actuales) y
    Tolerance (`tolerancia`: desvío máximo en mm; se puede combinar con los otros como segundo límite).
    Los bordes entre grupos se protegen con planos de penalización; con `preservar_bordes` los bordes
    abiertos no se tocan. Si no quedan colapsos válidos puede terminar por encima del objetivo."""
    if objetivo_caras is None and proporcion is None and tolerancia is None:
        raise geo.ErrorGeometria("Indicá objetivo_caras, proporcion o tolerancia.")
    M = len(m.caras)
    if not M:
        raise geo.ErrorGeometria("La malla está vacía.")
    if proporcion is not None and not 0 < proporcion <= 1:
        raise geo.ErrorGeometria("La proporción tiene que estar entre 0 y 1.")
    if objetivo_caras is not None and objetivo_caras < 4:
        raise geo.ErrorGeometria("El objetivo tiene que ser de al menos 4 caras.")
    if tolerancia is not None and tolerancia < 0:
        raise geo.ErrorGeometria("La tolerancia no puede ser negativa.")
    objetivo = 4
    if proporcion is not None:
        objetivo = max(4, int(round(M * proporcion)))
    elif objetivo_caras is not None:
        objetivo = int(objetivo_caras)
    tol2 = np.inf if tolerancia is None else float(tolerancia) ** 2
    if objetivo >= M and tolerancia is None:
        return m.copia()
    base = _sin_degenerados(m)
    v, c, g = base.vertices, base.caras, base.grupos
    ed = _Editor(v, c, g)
    Q = _cuadricas(v, c, g)
    frontera = np.zeros(len(v), bool)
    if preservar_bordes:
        frontera[_Topo(c, len(v)).libres().ravel()] = True
    version = [0] * len(v)
    contador = itertools.count()
    aristas = np.unique(np.sort(_medias_aristas(c), axis=1), axis=0)
    costos, puntos = _optimo_qem(Q[aristas[:, 0]] + Q[aristas[:, 1]], v[aristas[:, 0]], v[aristas[:, 1]])
    monton = [(cst, next(contador), a, b, 0, 0, p) for cst, (a, b), p in
              zip(costos.tolist(), aristas.tolist(), puntos, strict=True)]
    heapq.heapify(monton)
    vivas = len(c)
    while vivas > objetivo and monton:
        cst, _, a, b, va, vb, p = heapq.heappop(monton)
        if not (ed.vivo[a] and ed.vivo[b]) or version[a] != va or version[b] != vb:
            continue
        if cst > tol2:
            break
        if frontera[a] or frontera[b] or not ed.colapsable(a, b, p):
            continue
        vivas -= ed.colapsar(a, b, p)
        Q[a] += Q[b]
        version[a] += 1
        version[b] = -1
        vec = [x for x in ed.vecinos(a) if ed.vivo[x]]
        if vec:
            cs, ps = _optimo_qem(Q[a][None] + Q[vec], np.repeat(ed.v[a][None], len(vec), 0), ed.v[vec])
            for x, cx, px in zip(vec, cs.tolist(), ps, strict=True):
                heapq.heappush(monton, (cx, next(contador), a, x, version[a], version[x], px))
    return ed.exportar()


# ---------------------------------------------------------------- remallado isótropo
def _mas_cercano_tri(p, a, b, c):
    """Punto más cercano de cada triángulo (a, b, c) a cada punto p (Ericson, vectorizado)."""
    ab, ac, ap = b - a, c - a, p - a
    d1, d2 = np.einsum("ij,ij->i", ab, ap), np.einsum("ij,ij->i", ac, ap)
    bp = p - b
    d3, d4 = np.einsum("ij,ij->i", ab, bp), np.einsum("ij,ij->i", ac, bp)
    cp = p - c
    d5, d6 = np.einsum("ij,ij->i", ab, cp), np.einsum("ij,ij->i", ac, cp)
    va, vb, vc = d3 * d6 - d5 * d4, d5 * d2 - d1 * d6, d1 * d4 - d3 * d2
    with np.errstate(divide="ignore", invalid="ignore"):
        denom = va + vb + vc
        res = a + ab * (vb / denom)[:, None] + ac * (vc / denom)[:, None]
        hecho = np.zeros(len(p), bool)
        casos = [
            ((d1 <= 0) & (d2 <= 0), a),
            ((d3 >= 0) & (d4 <= d3), b),
            ((vc <= 0) & (d1 >= 0) & (d3 <= 0), a + ab * (d1 / (d1 - d3))[:, None]),
            ((d6 >= 0) & (d5 <= d6), c),
            ((vb <= 0) & (d2 >= 0) & (d6 <= 0), a + ac * (d2 / (d2 - d6))[:, None]),
            ((va <= 0) & (d4 - d3 >= 0) & (d5 - d6 >= 0), b + (c - b) * ((d4 - d3) / ((d4 - d3) + (d5 - d6)))[:, None]),
        ]
        for mascara, valor in casos:
            sel = mascara & ~hecho
            res[sel] = valor[sel]
            hecho |= sel
    return res


class _Referencia:
    """Superficie de referencia para proyectar puntos (punto más cercano entre los k triángulos de centro
    más próximo)."""

    def __init__(self, v, c, k=10):
        from scipy.spatial import cKDTree
        self.tris = v[c]
        self.arbol = cKDTree(self.tris.mean(1))
        self.k = min(k, len(c))

    def mas_cercano(self, puntos):
        _, idx = self.arbol.query(puntos, k=self.k)
        idx = np.asarray(idx).reshape(len(puntos), self.k)
        P = np.repeat(puntos, self.k, axis=0)
        T = self.tris[idx.ravel()]
        Q = _mas_cercano_tri(P, T[:, 0], T[:, 1], T[:, 2])
        d = np.linalg.norm(Q - P, axis=1).reshape(-1, self.k)
        j = np.argmin(d, axis=1)
        filas = np.arange(len(puntos))
        return d[filas, j], Q.reshape(-1, self.k, 3)[filas, j]


def _relajar(ed, ref, bordes_fijos, pasos):
    """Suavizado tangencial (con proyección sobre `ref`) o, sin referencia, laplaciano (membrana)."""
    F = ed.caras_vivas()
    n = ed.nv
    e = np.unique(np.sort(F[:, [0, 1, 1, 2, 2, 0]].reshape(-1, 2), axis=1), axis=0)
    from scipy.sparse import coo_matrix
    A = coo_matrix((np.ones(2 * len(e)), (np.r_[e[:, 0], e[:, 1]], np.r_[e[:, 1], e[:, 0]])), shape=(n, n)).tocsr()
    grado = np.asarray(A.sum(1)).ravel()
    he = F[:, [0, 1, 1, 2, 2, 0]].reshape(-1, 2)
    clave = np.minimum(he[:, 0], he[:, 1]) * n + np.maximum(he[:, 0], he[:, 1])
    _, inv, cuenta = np.unique(clave, return_inverse=True, return_counts=True)
    borde = np.zeros(n, bool)
    borde[he[cuenta[inv.reshape(-1)] == 1].ravel()] = True
    libres = (grado > 0) & ~np.array(ed.fijo) & ~np.array([ed.grado_rasgo(i) > 0 for i in range(n)])
    if bordes_fijos:
        libres &= ~borde
    if not libres.any():
        return
    V = ed.v[:n]
    for _ in range(pasos):
        centro = (A @ V) / np.maximum(grado, 1)[:, None]
        d = centro - V
        if ref is not None:
            nv = np.zeros((n, 3))
            nf = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
            for k in range(3):
                np.add.at(nv, F[:, k], nf)
            nv /= np.maximum(np.linalg.norm(nv, axis=1, keepdims=True), 1e-300)
            d -= np.einsum("ij,ij->i", d, nv)[:, None] * nv
        V[libres] += 0.5 * d[libres]
        if ref is not None:
            V[libres] = ref.mas_cercano(V[libres])[1]


def _remallar_nucleo(ed, largo, iteraciones, ref, bordes_fijos, pasos_relajar=1):
    alto, bajo = 4 / 3 * largo, 4 / 5 * largo
    for _ in range(iteraciones):
        for _ronda in range(12):                                 # dividir aristas largas
            e = ed.aristas()
            L = np.linalg.norm(ed.v[e[:, 0]] - ed.v[e[:, 1]], axis=1)
            sel = np.flatnonzero(L > alto)
            if not len(sel):
                break
            for a, b in e[sel[np.argsort(-L[sel])]].tolist():
                comunes = ed.vf[a] & ed.vf[b]
                if not comunes or (bordes_fijos and len(comunes) == 1):
                    continue
                ed.dividir(a, b)
        e = ed.aristas()                                         # colapsar aristas cortas
        L = np.linalg.norm(ed.v[e[:, 0]] - ed.v[e[:, 1]], axis=1)
        sel = np.flatnonzero(L < bajo)
        for a, b in e[sel[np.argsort(L[sel])]].tolist():
            if not (ed.vivo[a] and ed.vivo[b]) or not (ed.vf[a] & ed.vf[b]):
                continue
            if np.linalg.norm(ed.v[a] - ed.v[b]) >= bajo:
                continue
            quitar_a, quitar_b = _removible(ed, a, b, bordes_fijos), _removible(ed, b, a, bordes_fijos)
            if quitar_b:
                queda, sale = a, b
            elif quitar_a:
                queda, sale = b, a
            else:
                continue
            ambos_libres = quitar_a and quitar_b and ed.grado_rasgo(a) == 0 and ed.grado_rasgo(b) == 0
            p = (ed.v[a] + ed.v[b]) / 2 if ambos_libres else ed.v[queda].copy()
            vec = list((ed.vecinos(a) | ed.vecinos(b)) - {a, b})
            if np.any(np.linalg.norm(ed.v[vec] - p, axis=1) > alto):
                continue
            if ed.colapsable(queda, sale, p):
                ed.colapsar(queda, sale, p)
        for a, b in ed.aristas().tolist():                       # voltear hacia valencia 6 (4 en el borde)
            if ed.es_rasgo(a, b):
                continue
            comunes = list(ed.vf[a] & ed.vf[b])
            if len(comunes) != 2 or ed.g[comunes[0]] != ed.g[comunes[1]]:
                continue
            o = [x for f in comunes for x in ed.c[f] if x not in (a, b)]
            if len(o) != 2:
                continue
            val = [len(ed.vecinos(x)) for x in (a, b, o[0], o[1])]
            obj = [4 if ed.en_borde(x) else 6 for x in (a, b, o[0], o[1])]
            antes = sum(abs(x - y) for x, y in zip(val, obj, strict=True))
            val = [val[0] - 1, val[1] - 1, val[2] + 1, val[3] + 1]
            if sum(abs(x - y) for x, y in zip(val, obj, strict=True)) < antes:
                ed.voltear(a, b)
        _relajar(ed, ref, bordes_fijos, pasos_relajar)


def _removible(ed, x, otro, bordes_fijos):
    """¿Se puede eliminar x colapsándolo sobre `otro` sin romper rasgos ni bordes fijos?"""
    if ed.fijo[x] or (bordes_fijos and ed.en_borde(x)):
        return False
    grado = ed.grado_rasgo(x)
    return grado == 0 or (grado == 2 and ed.es_rasgo(x, otro))


def _preparar_rasgos(ed, m, *, preservar_bordes, angulo_vivo):
    """Marca como rasgo los bordes entre grupos, las aristas vivas (> angulo_vivo) y, si el borde no se
    congela, los bordes abiertos; fija las esquinas y los vértices no-manifold."""
    topo = _Topo(m.caras, len(m.vertices))
    f1, f2, _, arista = topo.pares()
    marcar = m.grupos[f1] != m.grupos[f2]
    if angulo_vivo is not None:
        n = m.normales_caras()
        marcar |= np.einsum("ij,ij->i", n[f1], n[f2]) < math.cos(math.radians(angulo_vivo))
    ids = arista[marcar].tolist()
    if not preservar_bordes:
        ids += np.flatnonzero(topo.cuenta == 1).tolist()
    for a, b in topo.aristas[ids].tolist():
        ed.poner_rasgo(a, b)
    for x in topo.aristas[topo.cuenta > 2].ravel().tolist():
        ed.fijo[x] = True
    for x in list(ed.vr):
        if ed.grado_rasgo(x) not in (0, 2):
            ed.fijo[x] = True


def remallar(m, *, densidad=1.0, longitud=None, preservar_bordes=True, preservar_aristas_vivas=True,
             angulo_vivo=30.0, iteraciones=5):
    """Remallar uniforme [MESH-REMESH] (remallado isótropo tipo Botsch-Kobbelt): divide aristas largas,
    colapsa cortas, voltea aristas hacia valencia 6 y relaja los vértices en el plano tangente,
    proyectándolos sobre la malla original. `densidad` > 1 da más caras (largo objetivo = largo medio /
    √densidad); `longitud` fija el largo objetivo en mm. Preserva los bordes entre grupos, las aristas
    vivas (Preserve Sharp Edges, > `angulo_vivo`) y, con `preservar_bordes`, los bordes abiertos intactos."""
    if not len(m.caras):
        raise geo.ErrorGeometria("La malla está vacía.")
    if densidad <= 0 or (longitud is not None and longitud <= 0):
        raise geo.ErrorGeometria("La densidad y la longitud tienen que ser positivas.")
    if iteraciones < 1:
        raise geo.ErrorGeometria("Hace falta al menos una iteración.")
    base = _sin_degenerados(m)
    topo = _Topo(base.caras, len(base.vertices))
    media = float(np.linalg.norm(base.vertices[topo.aristas[:, 0]] - base.vertices[topo.aristas[:, 1]], axis=1).mean())
    largo = float(longitud) if longitud is not None else media / math.sqrt(densidad)
    ed = _Editor(base.vertices, base.caras, base.grupos)
    _preparar_rasgos(ed, base, preservar_bordes=preservar_bordes,
                     angulo_vivo=angulo_vivo if preservar_aristas_vivas else None)
    _remallar_nucleo(ed, largo, int(iteraciones), _Referencia(base.vertices, base.caras), preservar_bordes)
    return ed.exportar()


# ---------------------------------------------------------------- cortar, vaciar, combinar
def cortar_plano(m, punto, normal, *, tipo="recortar", rellenar=True, invertir=False):
    """Corte por plano [MESH-PLANE-CUT]. tipo 'recortar' (Trim: queda el lado hacia donde apunta la normal;
    `invertir` = Flip), 'partir' (Split Body: devuelve (lado de la normal, lado opuesto)) o 'partir_caras'
    (Split Faces: una sola malla con las caras cortadas). `rellenar` tapa el corte con la triangulación
    del contorno (Fill Type 'Minimal'); la tapa es un grupo de caras nuevo."""
    if tipo not in ("recortar", "partir", "partir_caras"):
        raise geo.ErrorGeometria(f"Tipo de corte desconocido: {tipo}")
    n = np.asarray(normal, float)
    if np.linalg.norm(n) < 1e-12:
        raise geo.ErrorGeometria("La normal del plano de corte no puede ser nula.")
    n = n / np.linalg.norm(n) * (-1.0 if invertir else 1.0)
    v, c, g = m.vertices, m.caras, m.grupos
    if not len(c):
        raise geo.ErrorGeometria("La malla está vacía.")
    N = len(v)
    d = (v - np.asarray(punto, float)) @ n
    d[np.abs(d) <= 1e-9 * max(_diagonal(v), 1.0)] = 0.0
    s = np.sign(d).astype(np.int64)
    he = _medias_aristas(c)
    cruza = s[he[:, 0]] * s[he[:, 1]] < 0
    lo, hi = np.minimum(he[cruza, 0], he[cruza, 1]), np.maximum(he[cruza, 0], he[cruza, 1])
    claves, unicas = np.unique(lo * N + hi, return_index=True)
    lo, hi = lo[unicas], hi[unicas]
    t = d[lo] / (d[lo] - d[hi])
    V = np.vstack([v, v[lo] + t[:, None] * (v[hi] - v[lo])])
    D = np.r_[d, np.zeros(len(claves))]
    nuevo = dict(zip(claves.tolist(), range(N, N + len(claves)), strict=True))
    sc = s[c]
    plana = (sc == 0).all(1)
    plana_pos = plana & (m.normales_caras(False) @ n < 0)
    pos = (((sc >= 0).all(1) & (sc > 0).any(1)) | plana_pos)
    neg = (((sc <= 0).all(1) & (sc < 0).any(1)) | (plana & ~plana_pos))
    lados = {1: ([c[pos]], [g[pos]]), -1: ([c[neg]], [g[neg]])}
    for f in np.flatnonzero(~(pos | neg)).tolist():
        cara = c[f].tolist()
        polis = {1: [], -1: []}
        for k in range(3):
            i, j = cara[k], cara[(k + 1) % 3]
            if s[i] >= 0:
                polis[1].append(i)
            if s[i] <= 0:
                polis[-1].append(i)
            if s[i] * s[j] < 0:
                q = nuevo[min(i, j) * N + max(i, j)]
                polis[1].append(q)
                polis[-1].append(q)
        for lado, poli in polis.items():
            if len(poli) >= 3:
                tri = _abanico(poli)
                lados[lado][0].append(np.array(tri, np.int64))
                lados[lado][1].append(np.full(len(tri), g[f]))
    grupo_tapa = int(g.max()) + 1

    def armar(lado, normal_tapa):
        C, G = np.vstack(lados[lado][0]), np.concatenate(lados[lado][1])
        if rellenar and len(C):
            libres = _Topo(C, len(V)).libres()
            sobre = libres[(D[libres[:, 0]] == 0) & (D[libres[:, 1]] == 0)]
            lazos = _lazos(sobre)
            if lazos:
                tapa = _triangular_lazos(V, [np.array(lz[::-1]) for lz in lazos], normal_tapa)
                C, G = np.vstack([C, tapa]), np.r_[G, np.full(len(tapa), grupo_tapa)]
        return _compactar(V, C, G)

    if tipo == "partir_caras":
        return _compactar(V, np.vstack(lados[1][0] + lados[-1][0]), np.concatenate(lados[1][1] + lados[-1][1]))
    arriba = armar(1, -n)
    if tipo == "recortar":
        if not len(arriba.caras):
            raise geo.ErrorGeometria("Del lado que se conserva no queda nada de la malla.")
        return arriba
    abajo = armar(-1, n)
    if not len(arriba.caras) or not len(abajo.caras):
        raise geo.ErrorGeometria("El plano no corta la malla.")
    return arriba, abajo


def vaciar(m, espesor):
    """Vaciar [MESH-SHELL] (aproximado): cada vértice se desplaza hacia adentro `espesor` mm (el desfase que
    mejor respeta los planos de sus caras, así las paredes planas quedan exactas), esa copia se invierte
    y se suma como cáscara interior (grupos nuevos). No resuelve autointersecciones: avisa con
    RuntimeWarning si la cáscara interior se pliega o se acerca a la exterior."""
    if espesor <= 0:
        raise geo.ErrorGeometria("El espesor tiene que ser positivo.")
    if not m.es_cerrada():
        raise geo.ErrorGeometria("Para vaciar, la malla tiene que ser cerrada (estanca); repárela primero.")
    v, c, g = m.vertices, m.caras, m.grupos
    nf = m.normales_caras(False)
    nu = nf / np.maximum(np.linalg.norm(nf, axis=1), 1e-300)[:, None]
    # Pesos = ángulo de cada cara en el vértice (no depende de cómo esté teselada cada cara).
    t = v[c]
    angulos = np.zeros((len(c), 3))
    for k in range(3):
        e1, e2 = t[:, (k + 1) % 3] - t[:, k], t[:, (k + 2) % 3] - t[:, k]
        angulos[:, k] = np.arctan2(np.linalg.norm(np.cross(e1, e2), axis=1), np.einsum("ij,ij->i", e1, e2))
    A, s, normal = np.zeros((len(v), 3, 3)), np.zeros((len(v), 3)), np.zeros((len(v), 3))
    for k in range(3):
        w = angulos[:, k]
        np.add.at(A, c[:, k], w[:, None, None] * nu[:, :, None] * nu[:, None, :])
        np.add.at(s, c[:, k], w[:, None] * nu)
    # Desfase que deja cada plano vecino a `espesor` (mínimos cuadrados): exacto en aristas y esquinas.
    o = -espesor * np.einsum("nij,nj->ni", np.linalg.pinv(A, rcond=1e-2, hermitian=True), s)
    # En zonas lisas va por la normal pesada por ángulos (sin el ruido tangencial del ajuste).
    normal = s / np.maximum(np.linalg.norm(s, axis=1, keepdims=True), 1e-300)
    cos_min = np.full(len(v), np.inf)
    for k in range(3):
        np.minimum.at(cos_min, c[:, k], np.einsum("ij,ij->i", nu, normal[c[:, k]]))
    liso = cos_min > math.cos(math.radians(20))
    o[liso] = -espesor * normal[liso]
    largo = np.linalg.norm(o, axis=1)
    exceso = largo > 3 * espesor
    o[exceso] *= (3 * espesor / largo[exceso])[:, None]
    interior = v + o
    ti = interior[c]
    plegadas = int(np.count_nonzero(np.einsum("ij,ij->i", np.cross(ti[:, 1] - ti[:, 0], ti[:, 2] - ti[:, 0]), nf) <= 0))
    usados = np.unique(c)
    distancia, _ = _Referencia(v, c).mas_cercano(interior[usados])
    if plegadas or np.any(distancia < 0.8 * espesor):
        warnings.warn(f"Vaciar: con {espesor} mm la cáscara interior se autointersecta o se pliega "
                      f"({plegadas} caras invertidas); usá un espesor menor.", RuntimeWarning, stacklevel=2)
    return Malla(np.vstack([v, interior]), np.vstack([c, c[:, [0, 2, 1]] + len(v)]),
                 np.r_[g, g + int(g.max()) + 1])


def combinar(mallas, *, operacion="unir", motor="auto"):
    """Combinar [MESH-COMBINE]: la primera malla es el cuerpo objetivo y el resto herramientas.
    'unir' (Join), 'cortar' (Cut) e 'intersecar' (Intersect) son booleanas reales y exigen mallas cerradas;
    'fusionar' (Merge) junta las mallas sin tocarlas (conserva las estructuras internas).
    motor: 'manifold' (paquete manifold3d, conserva los grupos), 'brep' (kernel OpenCascade: convierte a
    sólido prismático, opera y vuelve a teselar; más lento y regenera los grupos) o 'auto'."""
    mallas = list(mallas)
    if operacion not in ("unir", "cortar", "intersecar", "fusionar"):
        raise geo.ErrorGeometria(f"Operación desconocida: {operacion}")
    if motor not in ("auto", "manifold", "brep"):
        raise geo.ErrorGeometria(f"Motor desconocido: {motor}")
    if not mallas:
        raise geo.ErrorGeometria("No hay mallas para combinar.")
    if operacion == "fusionar":
        V, C, G, base, desfase = [], [], [], 0, 0
        for mm in mallas:
            V.append(mm.vertices)
            C.append(mm.caras + base)
            G.append(mm.grupos + desfase)
            base += len(mm.vertices)
            desfase = int(np.concatenate(G).max()) + 1 if len(mm.grupos) else desfase
        return Malla(np.vstack(V), np.vstack(C), np.concatenate(G))
    if len(mallas) < 2:
        raise geo.ErrorGeometria("Combinar necesita un cuerpo objetivo y al menos una herramienta.")
    for i, mm in enumerate(mallas):
        if not mm.es_cerrada():
            raise geo.ErrorGeometria(f"La malla {i + 1} no es cerrada (estanca): repárela antes de combinar.")
    if motor == "manifold" and _manifold is None:
        raise geo.ErrorGeometria("Falta el paquete opcional manifold3d (pip install manifold3d).")
    if motor == "brep" or _manifold is None:
        return _combinar_brep(mallas, operacion)
    return _combinar_manifold(mallas, operacion)


def _combinar_manifold(mallas, operacion):
    objetos, desfase = [], 0
    for i, mm in enumerate(mallas):
        ids = mm.grupos - int(mm.grupos.min()) + desfase if i else mm.grupos - min(int(mm.grupos.min()), 0)
        desfase = int(ids.max()) + 1
        malla64 = _manifold.Mesh64(vert_properties=np.ascontiguousarray(mm.vertices),
                                   tri_verts=np.ascontiguousarray(mm.caras, dtype=np.uint64),
                                   face_id=np.ascontiguousarray(ids, dtype=np.uint64))
        obj = _manifold.Manifold(malla64)
        if obj.status() != _manifold.Error.NoError:
            raise geo.ErrorGeometria(f"manifold3d rechazó la malla {i + 1}: {obj.status().name}")
        objetos.append(obj)
    resultado = objetos[0]
    for obj in objetos[1:]:
        resultado = {"unir": resultado + obj, "cortar": resultado - obj, "intersecar": resultado ^ obj}[operacion]
    salida = resultado.to_mesh64()
    C = np.asarray(salida.tri_verts, np.int64).reshape(-1, 3)
    if not len(C):
        raise geo.ErrorGeometria("El resultado de la combinación quedó vacío.")
    V = np.asarray(salida.vert_properties, float)[:, :3]
    fid = np.asarray(salida.face_id, np.int64)
    return Malla(V, C, fid if len(fid) == len(C) else None)


def _combinar_brep(mallas, operacion):
    formas = [a_brep(mm, metodo="prismatico") for mm in mallas]
    resultado = formas[0]
    for f in formas[1:]:
        resultado = geo.booleano(resultado, f, operacion)
    if geo.esta_vacia(resultado):
        raise geo.ErrorGeometria("El resultado de la combinación quedó vacío.")
    return desde_brep(resultado, refinamiento="personalizado", desviacion=1e-3, angulo=15.0)


# ---------------------------------------------------------------- suavizar, normales, separar, escalar, alinear
def _adyacencia(c, n):
    from scipy.sparse import coo_matrix
    e = np.unique(np.sort(_medias_aristas(c), axis=1), axis=0)
    return coo_matrix((np.ones(2 * len(e)), (np.r_[e[:, 0], e[:, 1]], np.r_[e[:, 1], e[:, 0]])), shape=(n, n)).tocsr()


def suavizar(m, *, intensidad=0.5, iteraciones=10, grupos=None):
    """Suavizar [MESH-SMOOTH] con el filtro de Taubin (λ|μ), que no encoge la malla como el laplaciano
    simple. `intensidad` 0-1 (Smoothness de Fusion). Los vértices de borde quedan fijos; con `grupos`
    solo se mueven los vértices rodeados por caras de esos grupos."""
    if not 0 <= intensidad <= 1:
        raise geo.ErrorGeometria("La intensidad va de 0 a 1.")
    if iteraciones < 1:
        raise geo.ErrorGeometria("Hace falta al menos una iteración.")
    if intensidad == 0 or not len(m.caras):
        return m.copia()
    lam = 0.6 * intensidad
    mu = 1.0 / (0.1 - 1.0 / lam)
    n = len(m.vertices)
    A = _adyacencia(m.caras, n)
    grado = np.asarray(A.sum(1)).ravel()
    movibles = grado > 0
    movibles[_Topo(m.caras, n).libres().ravel()] = False
    if grupos is not None:
        fuera = ~np.isin(m.grupos, list(grupos))
        movibles[np.unique(m.caras[fuera])] = False
    v = m.vertices.copy()
    for _ in range(int(iteraciones)):
        for factor in (lam, mu):
            delta = (A @ v) / np.maximum(grado, 1)[:, None] - v
            v[movibles] += factor * delta[movibles]
    return Malla(v, m.caras, m.grupos)


def invertir_normales(m, caras=None, grupos=None):
    """Invertir normal [MESH-REVERSE-NORMAL]: de toda la malla, de las `caras` indicadas (índices o
    máscara) o de los `grupos` indicados."""
    mascara = np.ones(len(m.caras), bool)
    if caras is not None:
        sel = np.asarray(caras)
        mascara = sel.astype(bool) if sel.dtype == bool else np.isin(np.arange(len(m.caras)), sel)
    if grupos is not None:
        mascara &= np.isin(m.grupos, list(grupos))
    return Malla(m.vertices, _invertir(m.caras, mascara), m.grupos)


def separar(m, *, tipo="cascaras", grupos=None):
    """Separar [MESH-SEPARATE]: 'cascaras' (Mesh Shells: una malla por componente conexa) o 'grupos'
    (All Face Groups: una por grupo; con `grupos`, una por grupo elegido más otra con el resto)."""
    if tipo == "cascaras":
        etiqueta = _cascaras(m.caras, len(m.vertices))[0]
    elif tipo == "grupos":
        if grupos is None:
            etiqueta = _reetiquetar(m.grupos)
        else:
            sel = list(dict.fromkeys(grupos))
            faltan = set(sel) - set(m.grupos.tolist())
            if faltan:
                raise geo.ErrorGeometria(f"La malla no tiene los grupos {sorted(faltan)}.")
            etiqueta = np.full(len(m.caras), len(sel))
            for i, gid in enumerate(sel):
                etiqueta[m.grupos == gid] = i
    else:
        raise geo.ErrorGeometria(f"Tipo de separación desconocido: {tipo}")
    if not len(m.caras):
        return []
    return [_compactar(m.vertices, m.caras[etiqueta == k], m.grupos[etiqueta == k])
            for k in range(int(etiqueta.max()) + 1) if np.any(etiqueta == k)]


def escalar(m, fx, fy=None, fz=None, punto=(0.0, 0.0, 0.0)):
    """Escalar malla [MESH-SCALE-MESH] desde `punto`: uniforme (solo fx) o no uniforme (fx, fy, fz).
    Un factor negativo espeja; las caras se reordenan para que las normales sigan hacia afuera."""
    f = np.array([fx, fx if fy is None else fy, fx if fz is None else fz], float)
    if not np.all(np.isfinite(f)) or np.any(f == 0):
        raise geo.ErrorGeometria("Los factores de escala tienen que ser números distintos de cero.")
    p = np.asarray(punto, float)
    c = m.caras if np.prod(f) > 0 else m.caras[:, [0, 2, 1]]
    return Malla((m.vertices - p) * f + p, c, m.grupos)


def _rotacion_entre(a, b):
    """Matriz de rotación que lleva el vector unitario a sobre b."""
    eje = np.cross(a, b)
    s, cos = float(np.linalg.norm(eje)), float(a @ b)
    if s < 1e-12:
        if cos > 0:
            return np.eye(3)
        perp = np.cross(a, (1.0, 0.0, 0.0) if abs(a[0]) < 0.9 else (0.0, 1.0, 0.0))
        perp /= np.linalg.norm(perp)
        return 2 * np.outer(perp, perp) - np.eye(3)
    k = eje / s
    K = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    return np.eye(3) + s * K + (1 - cos) * K @ K


def alinear_a_plano(m, caras, plano, *, invertir=False):
    """Alinear malla [MESH-ALIGN]: mueve el cuerpo para que las `caras` elegidas (índice o lista; su normal
    y centro promediados por área) queden apoyadas sobre `plano` (geo.Plano) con la normal opuesta a la del
    plano, o sea el cuerpo del lado hacia donde apunta el plano. `invertir` = Flip (gira 180°)."""
    idx = np.atleast_1d(np.asarray(caras, np.int64))
    if not len(idx) or idx.min() < 0 or idx.max() >= len(m.caras):
        raise geo.ErrorGeometria("Las caras elegidas no existen en la malla.")
    nf = m.normales_caras(False)[idx]
    normal = nf.sum(0)
    if np.linalg.norm(normal) < 1e-12:
        raise geo.ErrorGeometria("Las caras elegidas no definen una dirección.")
    normal /= np.linalg.norm(normal)
    areas = np.linalg.norm(nf, axis=1)
    centro = (m.triangulos()[idx].mean(1) * areas[:, None]).sum(0) / areas.sum()
    pn = np.asarray(plano.normal, float)
    R = _rotacion_entre(normal, pn if invertir else -pn)
    v = (m.vertices - centro) @ R.T + centro
    v += pn * float((np.asarray(plano.origen, float) - centro) @ pn)
    return Malla(v, m.caras, m.grupos)


def borrar_y_rellenar(m, caras, *, tipo="uniforme", densidad=1.0):
    """Borrar y rellenar [MESH-ERASE-FILL]: quita las `caras` y tapa los agujeros que eso abre.
    'minimo' (Minimal: triángulos del contorno, pueden ser largos y finos) o 'uniforme' (Uniform: además
    remalla el parche con aristas del largo del contorno / √densidad, como una membrana tensa)."""
    if tipo not in ("uniforme", "minimo"):
        raise geo.ErrorGeometria(f"Tipo de relleno desconocido: {tipo}")
    if densidad <= 0:
        raise geo.ErrorGeometria("La densidad tiene que ser positiva.")
    idx = np.unique(np.atleast_1d(np.asarray(caras, np.int64)))
    if not len(idx) or idx.min() < 0 or idx.max() >= len(m.caras):
        raise geo.ErrorGeometria("Las caras elegidas no existen en la malla.")
    quedan = np.ones(len(m.caras), bool)
    quedan[idx] = False
    if not quedan.any():
        raise geo.ErrorGeometria("No se pueden borrar todas las caras.")
    v, c, g = m.vertices, m.caras[quedan], m.grupos[quedan]
    N = len(v)
    antes = _Topo(m.caras, N).libres()
    antes = set((antes[:, 0] * N + antes[:, 1]).tolist())
    lazos = [lz for lz in _lazos(_Topo(c, N).libres())
             if any(a * N + b not in antes for a, b in zip(lz, lz[1:] + lz[:1], strict=True))]
    if tipo == "minimo":
        c, g = _rellenar_lazos(v, c, g, lazos)
        return _compactar(v, c, g)
    siguiente = int(g.max()) + 1 if len(g) else 0
    for lazo in lazos:
        tapa = _tapar_lazo(v, lazo)
        largo = float(np.mean(np.linalg.norm(v[lazo] - v[np.roll(lazo, -1)], axis=1))) / math.sqrt(densidad)
        ed = _Editor(v, tapa, np.full(len(tapa), siguiente))
        _remallar_nucleo(ed, largo, 4, None, bordes_fijos=True, pasos_relajar=10)
        F = ed.caras_vivas()
        v = ed.v[:ed.nv]
        c = np.vstack([c, F])
        g = np.r_[g, np.full(len(F), siguiente)]
        siguiente += 1
    return _compactar(v, c, g)


# ---------------------------------------------------------------- a sólido
def a_brep(m, *, metodo="facetado", max_triangulos=50000):
    """Convertir malla [MESH-CONVERT-TO-SOLID], métodos Facetado y Prismático. Facetado: una cara plana
    por triángulo, con aristas y vértices compartidos (lo mismo que coser con BRepBuilderAPI_Sewing, sin
    buscar coincidencias). Si la malla es cerrada da un sólido (las cáscaras internas quedan como huecos);
    si no, una superficie (cáscaras abiertas), como Fusion. Prismático: además une las caras coplanares
    vecinas del mismo grupo (ShapeUpgrade_UnifySameDomain; no reconoce cilindros ni conos)."""
    if metodo not in ("facetado", "prismatico"):
        raise geo.ErrorGeometria(f"Método de conversión desconocido: {metodo}")
    base = _sin_degenerados(m)
    v, c, g = base.vertices, base.caras, base.grupos
    if not len(c):
        raise geo.ErrorGeometria("La malla está vacía.")
    if len(c) > max_triangulos:
        raise geo.ErrorGeometria(f"La malla tiene {len(c)} triángulos y el máximo para convertir es "
                                 f"{max_triangulos}: reducila antes con reducir().")
    puntos = [gp_Pnt(*p) for p in v.tolist()]
    vertices = [BRepBuilderAPI_MakeVertex(p).Vertex() for p in puntos]
    aristas = {}
    normales = base.normales_caras()
    caras_occ = []
    for k, (a, b, cc) in enumerate(c.tolist()):
        alambre = BRepBuilderAPI_MakeWire()
        for i, j in ((a, b), (b, cc), (cc, a)):
            clave = (i, j) if i < j else (j, i)
            if clave not in aristas:
                aristas[clave] = BRepBuilderAPI_MakeEdge(vertices[clave[0]], vertices[clave[1]]).Edge()
            alambre.Add(aristas[clave])
        plano = gp_Pln(puntos[a], gp_Dir(*normales[k].tolist()))
        caras_occ.append(BRepBuilderAPI_MakeFace(plano, alambre.Wire(), True).Face())
    etiqueta, cerrada = _cascaras(c, len(v))
    constructor = BRep_Builder()
    cascaras = []
    for k in range(len(cerrada)):
        sh = TopoDS_Shell()
        constructor.MakeShell(sh)
        for f in np.flatnonzero(etiqueta == k).tolist():
            constructor.Add(sh, caras_occ[f])
        sh.Closed(bool(cerrada[k]))
        cascaras.append(sh)
    if cerrada.all() and base.es_cerrada():
        prof, padre = _anidamiento(v, c, etiqueta, cerrada)
        solidos = []
        for k in np.flatnonzero(prof % 2 == 0).tolist():
            hacer = BRepBuilderAPI_MakeSolid(cascaras[k])
            for h in np.flatnonzero(padre == k).tolist():
                hacer.Add(cascaras[h])
            solido = hacer.Solid()
            BRepLib.OrientClosedSolid_s(solido)
            solidos.append(solido)
        forma = solidos[0] if len(solidos) == 1 else geo.compuesto(solidos)
    else:
        forma = cascaras[0] if len(cascaras) == 1 else geo.compuesto(cascaras)
    if metodo == "prismatico":
        unificar = ShapeUpgrade_UnifySameDomain(forma, True, True, False)
        topo = _Topo(c, len(v))
        f1, f2, _, arista = topo.pares()
        for a, b in topo.aristas[arista[g[f1] != g[f2]]].tolist():
            unificar.KeepShape(aristas[(a, b)])
        unificar.Build()
        forma = unificar.Shape()
    if not geo.es_valida(forma):
        raise geo.ErrorGeometria("La conversión dio un cuerpo inválido (¿la malla se autointersecta?).")
    return forma

# -*- coding: utf-8 -*-
"""
Sección de malla para ingeniería inversa (Fusion: MALLA › CREAR › Crear boceto de sección de malla
[MESH-CREATE-MESH-SECTION-SKETCH] y BOCETO › CREAR › Ajustar curvas a sección de malla [SKT-FIT-CURVE-TO-MESH-SECTION]).

- `seccion`: corta la malla con el plano del boceto → polilíneas (u, v).
- `primitivas_seccion`: esas polilíneas como splines de grado 1 (polilínea exacta) para `Boceto.agregar_proyeccion`:
  quedan fijas, de construcción y se guardan con el boceto (el «Mesh Section» de Fusion).
- `secciones_de_boceto`: las secciones que ya tiene un boceto.
- `tramo` / `ajustar`: el tramo entre dos puntos (camino corto o largo) y las curvas que lo aproximan: línea, arco,
  spline, spline cerrada, círculo, elipse, o «lineas_arcos» (líneas y arcos dentro de la desviación; no existe en
  Fusion, donde se eligen tramo por tramo).
- `agregar_curvas`: suma las curvas al boceto (comparten extremos) y devuelve la desviación real de cada una.
"""
import math

import numpy as np

from ..restricciones.boceto import Spline, primitivas_entidad, puntos_primitiva
from . import geometria as geo

TIPOS = ("linea", "arco", "spline", "spline_cerrada", "circulo", "elipse", "lineas_arcos")
CERRADOS = ("spline_cerrada", "circulo", "elipse")
_EPS = 1e-9


# ---------------------------------------------------------------- corte
def seccion(m, plano):
    """Corte de la malla `m` (nucleo.malla.Malla) con `plano` (geo.Plano) → [(Kx2 puntos u, v; cerrada)], una
    polilínea por lazo del corte. Un vértice justo sobre el plano se toma apenas del lado positivo."""
    v, c = m.vertices, m.caras
    if not len(c):
        raise geo.ErrorGeometria("La malla está vacía.")
    n = np.asarray(plano.normal, float)
    d = (v - plano.origen) @ n
    d[np.abs(d) < _EPS * max(float(np.ptp(v, axis=0).max()), 1.0)] = _EPS
    s = d > 0
    cruza = s[c].any(1) & ~s[c].all(1)
    if not cruza.any():
        raise geo.ErrorGeometria("El plano no corta la malla.")
    F = c[cruza]
    pares = np.stack([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]], 1)              # K x 3 aristas x 2 vértices
    corta = s[pares[..., 0]] != s[pares[..., 1]]                                   # dos por cara
    ar = np.sort(pares[corta].reshape(-1, 2, 2), axis=2)
    N = len(v)
    claves, nodo = np.unique(ar[..., 0] * N + ar[..., 1], return_inverse=True)
    nodo = nodo.reshape(-1, 2)                                                     # cada cara une dos nodos
    a, b = claves // N, claves % N
    t = d[a] / (d[a] - d[b])
    P3 = v[a] + t[:, None] * (v[b] - v[a])
    uv = np.c_[(P3 - plano.origen) @ plano.u, (P3 - plano.origen) @ plano.v]
    vecinos = [[] for _ in claves]
    for k, (p, q) in enumerate(nodo.tolist()):
        vecinos[p].append((k, q))
        vecinos[q].append((k, p))
    usada = np.zeros(len(nodo), bool)
    salida = []
    # primero las cadenas abiertas (nodos de grado impar), después los lazos
    for inicio in sorted(range(len(claves)), key=lambda i: len(vecinos[i]) % 2 == 0):
        while any(not usada[k] for k, _q in vecinos[inicio]):
            camino, actual = [inicio], inicio
            while True:
                sig = next(((k, q) for k, q in vecinos[actual] if not usada[k]), None)
                if sig is None:
                    break
                usada[sig[0]] = True
                actual = sig[1]
                camino.append(actual)
            cerrada = len(camino) > 3 and camino[-1] == camino[0]
            P = uv[camino[:-1] if cerrada else camino]
            P = P[np.r_[True, np.linalg.norm(np.diff(P, axis=0), axis=1) > _EPS]]     # sin puntos repetidos
            if len(P) >= 2:
                salida.append((P, cerrada))
    return salida


def primitivas_seccion(polilineas):
    """Primitivas de boceto (splines de control de grado 1 = la polilínea exacta) de las polilíneas de `seccion`."""
    return [("spline", 0, tuple(map(tuple, np.vstack([P, P[:1]]) if cerrada else P)), None, 1, None)
            for P, cerrada in polilineas]


def secciones_de_boceto(b):
    """{id de curva: (Kx2 puntos, cerrada)} de las secciones de malla del boceto: splines proyectadas, de construcción,
    de grado 1 (como las deja `primitivas_seccion`)."""
    salida = {}
    for c in b.curvas.values():
        if isinstance(c, Spline) and c.proyectada and c.construccion and c.modo == "control" and c.grado == 1:
            cerrada = len(c.pts) > 3 and c.pts[0] == c.pts[-1]
            salida[c.id] = (np.array([b.coords(p) for p in (c.pts[:-1] if cerrada else c.pts)], float), cerrada)
    return salida


# ---------------------------------------------------------------- tramos
def largo(P):
    return float(np.linalg.norm(np.diff(P, axis=0), axis=1).sum())


def cerrar(P):
    return np.vstack([P, P[:1]])


def distancia(q, P):
    """Distancia de cada punto q (Nx2) a la polilínea P (Mx2)."""
    q, a = np.atleast_2d(q)[:, None, :], P[None, :-1, :]
    d = P[None, 1:, :] - a
    t = np.clip(np.einsum("nmk,nmk->nm", q - a, d) / np.maximum(np.einsum("nmk,nmk->nm", d, d), 1e-300), 0, 1)
    return np.linalg.norm(a + t[..., None] * d - q, axis=2).min(1)


def _ubicar(P, q):
    """Distancia de recorrido (desde P[0]) del punto de la polilínea P más cercano a q, y ese punto."""
    a, d = P[:-1], np.diff(P, axis=0)
    t = np.clip(np.einsum("mk,mk->m", q - a, d) / np.maximum(np.einsum("mk,mk->m", d, d), 1e-300), 0, 1)
    cerca = a + t[:, None] * d
    k = int(np.argmin(np.linalg.norm(cerca - q, axis=1)))
    acumulado = np.r_[0.0, np.cumsum(np.linalg.norm(d, axis=1))]
    return acumulado[k] + t[k] * float(np.linalg.norm(d[k])), cerca[k]


def tramo(P, cerrada, inicio, fin, camino="corto"):
    """Puntos de la sección entre los puntos más cercanos a `inicio` y `fin` (en ese orden). En una sección cerrada
    hay dos caminos: «corto» o «largo» (Path Direction: Short / Long Path de Fusion)."""
    Q = cerrar(P) if cerrada else P
    S = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(Q, axis=0), axis=1))]
    L = S[-1]
    (sa, qa), (sb, qb) = _ubicar(Q, np.asarray(inicio, float)), _ubicar(Q, np.asarray(fin, float))
    if math.dist(qa, qb) < 1e-6 and (not cerrada or abs(sa - sb) < 1e-6 or abs(abs(sa - sb) - L) < 1e-6):
        raise geo.ErrorGeometria("El primer y el segundo punto caen en el mismo lugar de la sección.")
    S = S[:-1] if cerrada else S                      # un parámetro por vértice de P
    if cerrada:
        adelante = (sb - sa) % L
        if (adelante <= L / 2) != (camino == "corto"):
            sentido, avance = -1, (sa - S) % L                         # hacia atrás
            hasta = L - adelante
        else:
            sentido, avance = 1, (S - sa) % L
            hasta = adelante
    else:
        sentido = 1 if sb >= sa else -1
        avance, hasta = (S - sa) * sentido, abs(sb - sa)
    dentro = (avance > 1e-9) & (avance < hasta - 1e-9)
    orden = np.flatnonzero(dentro)[np.argsort(avance[dentro])]
    return np.vstack([qa, P[orden], qb])


# ---------------------------------------------------------------- ajustes
def _circulo(P):
    """Círculo por mínimos cuadrados (Kåsa) → (centro, radio) o None si los puntos están alineados."""
    m = P.mean(0)
    x, y = (P - m).T
    A = np.c_[2 * x, 2 * y, np.ones(len(P))]
    sol, *_ = np.linalg.lstsq(A, x * x + y * y, rcond=None)
    r2 = sol[2] + sol[0] ** 2 + sol[1] ** 2
    if r2 <= 0 or not np.isfinite(r2) or math.sqrt(r2) > 1e6:
        return None
    return sol[:2] + m, math.sqrt(r2)


def _elipse(P):
    """Elipse por mínimos cuadrados (Fitzgibbon, versión estable de Halír-Flusser) → (centro, punto del eje mayor,
    radio menor)."""
    m = P.mean(0)
    x, y = (P - m).T
    D1, D2 = np.c_[x * x, x * y, y * y], np.c_[x, y, np.ones(len(P))]
    S1, S2, S3 = D1.T @ D1, D1.T @ D2, D2.T @ D2
    try:
        T = -np.linalg.solve(S3, S2.T)
        M = S1 + S2 @ T
        M = np.array([M[2] / 2, -M[1], M[0] / 2])
        val, vec = np.linalg.eig(M)
    except np.linalg.LinAlgError as e:
        raise geo.ErrorGeometria("La sección no se puede aproximar con una elipse.") from e
    vec = np.real(vec)
    elegidos = vec[:, 4 * vec[0] * vec[2] - vec[1] ** 2 > 0]
    if not elegidos.shape[1]:
        raise geo.ErrorGeometria("La sección no se puede aproximar con una elipse.")
    A, B, C = elegidos[:, 0]
    Dd, E, F = T @ elegidos[:, 0]
    centro = np.linalg.solve([[2 * A, B], [B, 2 * C]], [-Dd, -E])
    Fc = A * centro[0] ** 2 + B * centro[0] * centro[1] + C * centro[1] ** 2 + Dd * centro[0] + E * centro[1] + F
    lam, ejes = np.linalg.eigh([[A, B / 2], [B / 2, C]])
    semi = -Fc / lam
    if not (semi > 0).all():
        raise geo.ErrorGeometria("La sección no se puede aproximar con una elipse.")
    semi = np.sqrt(semi)
    mayor = int(np.argmax(semi))
    c = centro + m
    return c, c + ejes[:, mayor] * semi[mayor], float(semi[1 - mayor])


def _dp(P, tol):
    """Douglas-Peucker: índices de los puntos de P que quedan con la tolerancia `tol`."""
    quedan, pila = {0, len(P) - 1}, [(0, len(P) - 1)]
    while pila:
        i, j = pila.pop()
        if j <= i + 1:
            continue
        a, d = P[i], P[j] - P[i]
        L = float(np.linalg.norm(d))
        Q = P[i + 1:j] - a
        dist = np.abs(Q[:, 0] * d[1] - Q[:, 1] * d[0]) / L if L > _EPS else np.linalg.norm(Q, axis=1)
        k = int(np.argmax(dist))
        if dist[k] > tol:
            quedan.add(i + 1 + k)
            pila += [(i, i + 1 + k), (i + 1 + k, j)]
    return sorted(quedan)


def _desvio_recta(Q):
    a, d = Q[0], Q[-1] - Q[0]
    L = float(np.linalg.norm(d))
    return float(np.abs((Q[:, 0] - a[0]) * d[1] - (Q[:, 1] - a[1]) * d[0]).max() / L) if L > _EPS else math.inf


def _arco3(Q):
    """Arco por el primer, el del medio y el último punto de Q; (centro, radio, desvío radial máximo) o None si
    los puntos no recorren el arco en un solo sentido (o están alineados)."""
    a, m, b = Q[0], Q[len(Q) // 2], Q[-1]
    det = 2 * ((m[0] - a[0]) * (b[1] - a[1]) - (m[1] - a[1]) * (b[0] - a[0]))
    if abs(det) < _EPS:
        return None
    A2, M2, B2 = a @ a, m @ m, b @ b
    cx = ((M2 - A2) * (b[1] - a[1]) - (B2 - A2) * (m[1] - a[1])) / det
    cy = ((B2 - A2) * (m[0] - a[0]) - (M2 - A2) * (b[0] - a[0])) / det
    c = np.array([cx, cy])
    r = float(np.linalg.norm(a - c))
    giro = np.diff(np.unwrap(np.arctan2(Q[:, 1] - cy, Q[:, 0] - cx)))
    if not ((giro > -1e-12).all() or (giro < 1e-12).all()) or abs(giro.sum()) > 2 * math.pi - 1e-3:
        return None
    return c, r, float(np.abs(np.linalg.norm(Q - c, axis=1) - r).max())


def _lineas_arcos(P, cerrada, tol):
    """Líneas y arcos dentro de la desviación `tol` (avance codicioso: en cada tramo, la curva que más avanza;
    a igual avance, la línea). Una sección cerrada arranca en su esquina más marcada."""
    # shortcut: barrido O(n²) por tramo, bien hasta ~1000 puntos de sección; con escaneos densos, reduce_mesh antes
    # o pasar a búsqueda por duplicación.
    if cerrada:
        circ = _circulo(P)
        if circ is not None and np.abs(np.linalg.norm(P - circ[0], axis=1) - circ[1]).max() <= tol:
            return [{"tipo": "circulo", "centro": circ[0], "radio": circ[1], "datos": P, "cerrada": True}]
        e1, e2 = P - np.roll(P, 1, 0), np.roll(P, -1, 0) - P
        giro = np.abs(np.arctan2(e1[:, 0] * e2[:, 1] - e1[:, 1] * e2[:, 0], (e1 * e2).sum(1)))
        P = cerrar(np.roll(P, -int(np.argmax(giro)), 0))
    curvas, i, n = [], 0, len(P)
    while i < n - 1:
        jl = i + 1
        while jl + 1 < n and _desvio_recta(P[i:jl + 2]) <= tol:
            jl += 1
        ja, j = None, i + 2
        while j < n:
            prueba = _arco3(P[i:j + 1])
            if prueba is None or prueba[2] > tol:
                break
            ja, j = j, j + 1
        if ja is not None and ja > jl:
            Q = P[i:ja + 1]
            curvas.append({"tipo": "arco", "puntos": [Q[0], Q[len(Q) // 2], Q[-1]], "datos": Q})
            i = ja
        else:
            curvas.append({"tipo": "linea", "puntos": [P[i], P[jl]], "datos": P[i:jl + 1]})
            i = jl
    return curvas


def ajustar(P, cerrada, tipo, *, inicio=None, fin=None, camino="corto", tolerancia=0.1, desviacion=0.1):
    """Ajustar curvas a sección de malla: curvas (dicts con "tipo", su geometría y los "datos" que aproximan) para
    la sección P (Kx2) según `tipo` (ver TIPOS). Las abiertas (linea, arco, spline) van de `inicio` a `fin` por el
    `camino` corto o largo; las cerradas siguen toda la sección. `tolerancia` (Spline Fit Tolerance): más chica,
    más puntos de spline; `desviacion` (Max Curve Deviation): el límite de «lineas_arcos»."""
    if tipo not in TIPOS:
        raise geo.ErrorGeometria(f"Tipo de curva desconocido: {tipo}")
    if (tipo in CERRADOS or tipo == "lineas_arcos") and inicio is None:
        if tipo in CERRADOS and not cerrada:
            raise geo.ErrorGeometria("La sección está abierta: una curva cerrada necesita una sección cerrada.")
        if tipo == "lineas_arcos":
            return _lineas_arcos(P, cerrada, desviacion)
        if tipo == "circulo":
            circ = _circulo(P)
            if circ is None:
                raise geo.ErrorGeometria("La sección no se puede aproximar con un círculo.")
            return [{"tipo": "circulo", "centro": circ[0], "radio": circ[1], "datos": P, "cerrada": True}]
        if tipo == "elipse":
            centro, mayor, menor = _elipse(P)
            return [{"tipo": "elipse", "centro": centro, "mayor": mayor, "radio_menor": menor, "datos": P,
                     "cerrada": True}]
        Q = cerrar(P)
        idx = _dp(Q, tolerancia)[:-1]
        if len(idx) < 3:
            idx = sorted({0, len(P) // 3, 2 * len(P) // 3})
        return [{"tipo": "spline", "puntos": list(P[idx]), "cerrada": True, "datos": P}]
    if inicio is None or fin is None:
        raise geo.ErrorGeometria("Las curvas abiertas necesitan el primer y el segundo punto sobre la sección.")
    Q = tramo(P, cerrada, inicio, fin, camino)
    if tipo == "lineas_arcos":
        return _lineas_arcos(Q, False, desviacion)
    if tipo == "linea":
        return [{"tipo": "linea", "puntos": [Q[0], Q[-1]], "datos": Q}]
    if tipo == "arco":
        S = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(Q, axis=0), axis=1))]
        medio = np.array([np.interp(S[-1] / 2, S, Q[:, 0]), np.interp(S[-1] / 2, S, Q[:, 1])])
        return [{"tipo": "arco", "puntos": [Q[0], medio, Q[-1]], "datos": Q}]
    if tipo == "spline":
        return [{"tipo": "spline", "puntos": list(Q[_dp(Q, tolerancia)]), "cerrada": False, "datos": Q}]
    raise geo.ErrorGeometria("Las curvas cerradas (spline cerrada, círculo, elipse) siguen toda la sección: "
                             "no llevan primer ni segundo punto.")


# ---------------------------------------------------------------- al boceto
def agregar_curvas(b, curvas):
    """Suma las curvas de `ajustar` al boceto `b`. Un extremo que cae sobre un punto ya dibujado (no proyectado) lo
    reusa: la curva siguiente arranca donde terminó la anterior y los lazos cierran perfil. Devuelve
    [(id de la curva, desviación máxima en mm respecto de los datos de la sección)]."""
    def punto(xy):
        xy = (float(xy[0]), float(xy[1]))
        for p in b.puntos.values():
            if not p.proyectado and math.hypot(p.x - xy[0], p.y - xy[1]) < 1e-6:
                return p.id
        return b.agregar_punto(*xy)

    salida = []
    for c in curvas:
        t = c["tipo"]
        if t == "linea":
            cid = b.agregar_linea(punto(c["puntos"][0]), punto(c["puntos"][1]))
        elif t == "arco":
            a, m, z = c["puntos"]
            cid = b.agregar_arco_3_puntos(punto(a), (float(m[0]), float(m[1])), punto(z))
        elif t == "circulo":
            cid = b.agregar_circulo((float(c["centro"][0]), float(c["centro"][1])), float(c["radio"]))
        elif t == "elipse":
            cid = b.agregar_elipse(tuple(map(float, c["centro"])), tuple(map(float, c["mayor"])),
                                   float(c["radio_menor"]))
        else:
            pts = [tuple(map(float, q)) for q in c["puntos"]]
            if not c["cerrada"]:
                pts[0], pts[-1] = punto(pts[0]), punto(pts[-1])
            cid = b.agregar_spline(pts, cerrada=c["cerrada"])
        muestras = np.vstack([puntos_primitiva(p, 256) for p in primitivas_entidad(b.curvas[cid], b.coords)])
        if c.get("cerrada"):
            muestras = cerrar(muestras)
        salida.append((cid, float(distancia(c["datos"], muestras).max())))
    return salida

# -*- coding: utf-8 -*-
"""
Medir las formas de una malla (F11; paso 2 de docs/plan_reconstruir_solido.md): planos, cilindros, conos, esferas y
toros con sus medidas, y el resto sin clasificar. Fusion no lo trae: su Convertir malla Prismático une caras pero no
reconoce cilindros (`nucleo/malla.py` › `a_brep`).

Cómo mide: los triángulos coplanares vecinos forman una «faceta» (en un cilindro teselado, cada tira). Desde la faceta
más grande sin clasificar se junta un parche de vecinas cada vez mayor, se le ajusta la forma más simple que entre en
la tolerancia y la forma se queda con todas las facetas conectadas que coinciden en posición Y en normal. Se ajusta
sobre los vértices, que un teselado deja sobre la superficie real: el centro de una faceta queda adentro de la cuerda.
Lo que no ajusta queda sin clasificar: nunca se fuerza.

Ajustes propios, de geometría pública: cilindro y cono por el plano que forman sus normales en la esfera de Gauss y
mínimos cuadrados algebraicos; toro por el complejo lineal de sus rectas normales (Pottmann y Randrup, 1998) y después
Gauss-Newton sobre la distancia real.
"""
import math

import numpy as np

from . import comparar_malla as cm
from . import geometria as geo
from . import malla_seccion as ms
from . import reconocer_funciones as rf

_ANGULO_COPLANAR = math.cos(math.radians(0.25))
_COPLANAR_EXACTO = math.cos(math.radians(0.01))
_ANGULO_SUAVE = math.cos(math.radians(40.0))    # hasta acá dos caras vecinas pueden ser de la misma superficie teselada
_NORMAL_PLANO = math.cos(math.radians(3.0))
_NORMAL_CURVA = math.cos(math.radians(30.0))    # una tira gruesa se aparta media división de la normal real
_FILO = math.cos(math.radians(20.0))
_VUELTA = math.cos(math.radians(50.0))          # giro máximo de un triángulo alrededor del eje de un cono o un toro
_RADIO_MAXIMO = 10.0                            # en diagonales de la caja: más que esto es un plano, no un cilindro
_ESCALAS = (1, 3, 6, 12, 24, 48, 96, 192, 384, 768)
_PESO = {"plane": 1.0, "cylinder": 1.0, "cone": 1.2, "sphere": 1.2, "torus": 2.5}   # lo simple gana salvo que falle
_TOPE_FALLAS = 300                              # semillas seguidas sin forma antes de dejar el resto sin clasificar
_SIN_VOTO = 2 / math.sin(math.radians(3.0))     # con ruido: en triángulos más bajos que esto × tol, la normal no dice nada
_SEMILLA = 20261101
_TOLERANCIA_RELATIVA = 2e-4


def _base(a):
    u = rf._perpendicular(a)
    return u, np.cross(a, u)


def _unit(v):
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-300)


# ---------------------------------------------------------------- modelos
class _Forma:
    """Una forma ajustada: `distancia` (con signo) y `normal` (unitaria, sin sentido garantizado) en puntos Nx3."""
    __slots__ = ("p", "a", "b", "c", "tipo")

    def __init__(self, tipo, p, a=None, b=0.0, c=0.0):
        self.tipo, self.p, self.a, self.b, self.c = tipo, np.asarray(p, float), None if a is None else _unit(np.asarray(a, float)), float(b), float(c)

    def _rz(self, P):
        q = P - self.p
        z = q @ self.a
        radial = q - z[:, None] * self.a
        rho = np.linalg.norm(radial, axis=1)
        return rho, z, radial / np.maximum(rho, 1e-300)[:, None]

    def distancia(self, P):
        t = self.tipo
        if t == "plane":
            return (P - self.p) @ self.a
        if t == "sphere":
            return np.linalg.norm(P - self.p, axis=1) - self.b
        rho, z, _ = self._rz(P)
        if t == "cylinder":
            return rho - self.b
        if t == "cone":
            return (rho - self.b - self.c * z) / math.hypot(1.0, self.c)
        return np.hypot(rho - self.b, z) - self.c

    def normal(self, P):
        t = self.tipo
        if t == "plane":
            return np.broadcast_to(self.a, P.shape)
        if t == "sphere":
            return _unit(P - self.p)
        rho, z, er = self._rz(P)
        if t == "cylinder":
            return er
        if t == "cone":
            return _unit(er - self.c * self.a)
        return _unit((rho - self.b)[:, None] * er + z[:, None] * self.a)


def _afinar(tipo, p, a, b, c, V):
    """Gauss-Newton sobre la distancia real: eje (dos giros y dos corrimientos) y medidas. Hace falta cuando el eje
    salió de normales de triángulos irregulares. Con la derivada exacta en vez de diferencias finitas, que eran la
    mitad del costo del ajuste."""
    from scipy.optimize import least_squares
    u, v = _base(a)

    def forma(x):
        return _Forma(tipo, p + x[2] * u + x[3] * v, _unit(a + x[0] * u + x[1] * v), x[4], x[5])

    muestra = V if len(V) <= 800 else V[np.random.default_rng(_SEMILLA).choice(len(V), 800, replace=False)]

    def jacobiana(x):
        f = forma(x)
        w = a + x[0] * u + x[1] * v
        da0 = (u - (f.a @ u) * f.a) / np.linalg.norm(w)      # d unit(w) / dx0
        da1 = (v - (f.a @ v) * f.a) / np.linalg.norm(w)
        q = muestra - f.p
        z = q @ f.a
        radial = q - z[:, None] * f.a
        rho = np.maximum(np.linalg.norm(radial, axis=1), 1e-300)
        er = radial / rho[:, None]
        J = np.empty((len(muestra), 6))
        if tipo == "cone":
            H = math.hypot(1.0, f.c)
            n = rho - f.b - f.c * z
            d_da = (-z[:, None] * er - f.c * q) / H
            d_dp = (-er + f.c * f.a) / H
            J[:, 4] = -1.0 / H
            J[:, 5] = -z / H - n * f.c / H ** 3
        else:                                                # torus: el único otro tipo con que se llama _afinar
            U = rho - f.b
            H = np.hypot(U, z)
            d_da = z[:, None] * (q - U[:, None] * er) / H[:, None]
            d_dp = -(U[:, None] * er + z[:, None] * f.a) / H[:, None]
            J[:, 4] = -U / H
            J[:, 5] = -1.0
        J[:, 0] = d_da @ da0
        J[:, 1] = d_da @ da1
        J[:, 2] = d_dp @ u
        J[:, 3] = d_dp @ v
        return J

    x = least_squares(lambda x: forma(x).distancia(muestra), [0.0, 0.0, 0.0, 0.0, b, c],
                      jac=jacobiana if tipo in ("cone", "torus") else "2-point", max_nfev=30).x
    return forma(x)


def ajustar_plano(V, _C, _N, _A):
    c = V.mean(0)
    return _Forma("plane", c, np.linalg.svd(V - c, full_matrices=False)[2][-1])


def _eje_gauss(N, A, centrado):
    """Eje: la dirección de menor varianza de las normales. Devuelve (eje, cuán bien definido está)."""
    M = N - np.average(N, axis=0, weights=A) if centrado else N
    val, vec = np.linalg.eigh((M * A[:, None]).T @ M / A.sum())
    return vec[:, 0], float(val[1])


def ajustar_cilindro(V, _C, N, A):
    a, firme = _eje_gauss(N, A, False)
    if firme < 1e-7 or len(V) < 6:
        return None
    u, v = _base(a)
    circulo = ms._circulo(np.c_[V @ u, V @ v])
    if circulo is None:
        return None
    (x, y), r = circulo
    return _Forma("cylinder", x * u + y * v, a, r)


def ajustar_cono(V, _C, N, A):
    a, firme = _eje_gauss(N, A, True)
    if firme < 1e-7 or len(V) < 8:
        return None
    # x² + y² = 2cx·x + 2cy·y + K + 2B·z + C·z²: lineal; sale exacto con los puntos sobre el cono
    u, v = _base(a)
    x, y, z = V @ u, V @ v, V @ a
    o = np.array([x.mean(), y.mean(), z.mean()])
    x, y, z = x - o[0], y - o[1], z - o[2]
    sol, *_ = np.linalg.lstsq(np.c_[2 * x, 2 * y, np.ones(len(x)), 2 * z, z * z], x * x + y * y, rcond=None)
    r2 = sol[2] + sol[0] ** 2 + sol[1] ** 2
    if not r2 > 0 or sol[4] < 0:
        return None
    r0 = math.sqrt(r2)
    forma = _Forma("cone", (o[0] + sol[0]) * u + (o[1] + sol[1]) * v + o[2] * a, a, r0, sol[3] / r0)
    error = float(np.abs(forma.distancia(V)).max())
    casi = error <= 0.5 and len(V) >= 12 and error > 1e-6
    return _afinar("cone", forma.p, forma.a, forma.b, forma.c, V) if casi else forma


def ajustar_esfera(V, _C, _N, _A):
    if len(V) < 8:
        return None
    m = V.mean(0)
    Q = V - m
    sol, *_ = np.linalg.lstsq(np.c_[2 * Q, np.ones(len(Q))], (Q * Q).sum(1), rcond=None)
    r2 = sol[3] + sol[:3] @ sol[:3]
    return _Forma("sphere", m + sol[:3], None, math.sqrt(r2)) if r2 > 0 else None


def _eje_rectas(C, N, A):
    """Eje de revolución: el complejo lineal de las rectas normales (son todas las que lo cortan). (punto, dirección)."""
    o = np.average(C, axis=0, weights=A)
    escala = max(float(np.linalg.norm(C - o, axis=1).max()), 1e-9)
    L = np.c_[N, np.cross((C - o) / escala, N)]
    val, vec = np.linalg.eigh((L * A[:, None]).T @ L)
    momento, d = vec[:3, 0], vec[3:, 0]                # d·(p×n) + momento·n = 0
    largo = float(np.linalg.norm(d))
    if largo < 1e-6:
        return None
    return o + escala * np.cross(d, momento) / largo ** 2, d / largo


def ajustar_toro(V, C, N, A):
    if len(V) < 12:
        return None
    eje = _eje_rectas(C, N, A)
    if eje is None:
        return None
    p, a = eje
    q = V - p
    z = q @ a
    rho = np.linalg.norm(q - z[:, None] * a, axis=1)
    circulo = ms._circulo(np.c_[rho, z])
    if circulo is None:
        return None
    (R, zc), r = circulo
    forma = _Forma("torus", p + a * zc, a, R, r)
    # igual que el cono: recién se afina cuando el ajuste algebraico ya está cerca; el Gauss-Newton es la parte cara y
    # en un par que no es un toro se va 30 iteraciones sin llegar a ninguna parte
    if forma.b > 0 and forma.c > 0 and float(np.abs(forma.distancia(V)).max()) <= 0.5:
        forma = _afinar("torus", forma.p, forma.a, forma.b, forma.c, V)
    return forma if forma.b > 0 and forma.c > 0 else None


_AJUSTES = (ajustar_plano, ajustar_cilindro, ajustar_cono, ajustar_esfera, ajustar_toro)
_POR_TIPO = {"plane": ajustar_plano, "cylinder": ajustar_cilindro, "cone": ajustar_cono, "sphere": ajustar_esfera,
             "torus": ajustar_toro}


# ---------------------------------------------------------------- grafo de facetas
class _Facetas:
    """La malla sin degenerados, con sus facetas (triángulos coplanares vecinos) y quién toca a quién."""

    def __init__(self, m, tol, ruidosa=False):
        from scipy.sparse import coo_matrix
        from scipy.sparse.csgraph import connected_components
        area = m.areas_caras()
        self.validos = np.flatnonzero(area > 0)
        self.V, self.F = m.vertices, m.caras[self.validos]
        self.area, self.N = area[self.validos], m.normales_caras()[self.validos]
        n = len(self.F)
        T = self.V[self.F]
        largo = np.linalg.norm(T - T[:, [1, 2, 0]], axis=2).max(1)
        self.astilla = 2 * self.area / largo < (_SIN_VOTO * tol if ruidosa else tol)  # la normal de una astilla no vota
        lados = np.sort(self.F[:, [0, 1, 1, 2, 2, 0]].reshape(-1, 2), axis=1)
        _, inversa, cuenta = np.unique(lados, axis=0, return_inverse=True, return_counts=True)
        inversa = inversa.reshape(-1)
        orden = np.argsort(inversa, kind="stable")
        cara = np.repeat(np.arange(n), 3)[orden]
        doble = cuenta[inversa[orden]] == 2                   # una arista no manifold no une nada
        pares = cara[doble].reshape(-1, 2)
        extremos = lados[orden][doble][::2]
        self.largo_arista = np.linalg.norm(self.V[extremos[:, 0]] - self.V[extremos[:, 1]], axis=1)
        self.t1, self.t2 = pares[:, 0], pares[:, 1]
        self.coseno = np.einsum("ij,ij->i", self.N[self.t1], self.N[self.t2])
        centro = self.V[self.F].mean(1)
        cerca = np.abs(np.einsum("ij,ij->i", centro[self.t2] - centro[self.t1], self.N[self.t1])) <= tol * 0.25
        pega = (self.coseno >= _ANGULO_COPLANAR) & cerca
        g = coo_matrix((np.ones(int(pega.sum())), (self.t1[pega], self.t2[pega])), shape=(n, n))
        _, faceta = connected_components(g, directed=False)
        faceta = self._solo_planas(faceta, tol)
        self.faceta, self.nf = faceta, int(faceta.max()) + 1
        self.area_f = np.bincount(faceta, self.area, self.nf)
        suma = np.stack([np.bincount(faceta, self.N[:, k] * self.area, self.nf) for k in range(3)], 1)
        self.N_f = _unit(suma)
        self.C_f = np.stack([np.bincount(faceta, centro[:, k] * self.area, self.nf) for k in range(3)], 1) / self.area_f[:, None]
        self.triangulos = np.split(np.argsort(faceta, kind="stable"), np.cumsum(np.bincount(faceta, minlength=self.nf))[:-1])
        distintas = faceta[self.t1] != faceta[self.t2]
        a, b = faceta[self.t1][distintas], faceta[self.t2][distintas]
        self._adyacencia(a, b, self.coseno[distintas], self.largo_arista[distintas])

    def _solo_planas(self, faceta, tol):
        """Un fino cilindro encadena tiras casi coplanares: la faceta que se aparta del plano vuelve a triángulos sueltos."""
        n = int(faceta.max()) + 1
        P = self.V[self.F]
        ref_n = np.zeros((n, 3))
        ref_n[faceta] = self.N
        ref_p = np.zeros((n, 3))
        ref_p[faceta] = P[:, 0]
        desvio = np.abs(np.einsum("ijk,ik->ij", P - ref_p[faceta][:, None], ref_n[faceta])).max(1)
        mala = np.zeros(n, bool)
        np.logical_or.at(mala, faceta, desvio > tol * 0.5)
        if not mala.any():
            return faceta
        sueltos = mala[faceta]
        salida = faceta.copy()
        salida[sueltos] = n + np.arange(int(sueltos.sum()))
        return np.unique(salida, return_inverse=True)[1]

    def _adyacencia(self, a, b, coseno, largo):
        """Vecinas de cada faceta (CSR): `self.vec`, y solo por aristas suaves: `self.suave`. Primero las que comparten
        más borde: dos tiras de un empalme se tocan a lo largo; las de dos empalmes, en una esquina."""
        def csr(x, y, peso):
            if not len(x):
                return np.zeros(self.nf + 1, np.int64), np.zeros(0, np.int64)
            u, inv = np.unique(np.r_[np.c_[x, y], np.c_[y, x]], axis=0, return_inverse=True)
            total = np.bincount(inv.reshape(-1), np.r_[peso, peso])
            u = u[np.lexsort((-total, u[:, 0]))]
            return np.r_[0, np.cumsum(np.bincount(u[:, 0], minlength=self.nf))], u[:, 1]
        self.vec = csr(a, b, largo)
        s = coseno >= _ANGULO_SUAVE
        self.suave = csr(a[s], b[s], largo[s])
        # filo: la faceta tiene alguna arista marcada: una cara real, no un pedazo de superficie libre
        self.filo = np.zeros(self.nf, bool)
        marcada = coseno < _FILO
        self.filo[a[marcada]] = True
        self.filo[b[marcada]] = True

    def vecinas(self, f, csr):
        return csr[1][csr[0][f]:csr[0][f + 1]]

    def parche(self, semilla, n, libre):
        """Hasta `n` facetas libres alrededor de `semilla`, por aristas suaves, las más cercanas primero."""
        vistas, cola, k = {semilla}, [semilla], 0
        while k < len(cola) and len(cola) < n:
            for g in self.vecinas(cola[k], self.suave).tolist():
                if g not in vistas and libre[g]:
                    vistas.add(g)
                    cola.append(g)
                    if len(cola) >= n:
                        break
            k += 1
        return np.array(cola)

    def indices(self, facetas):
        """Triángulos de esas facetas."""
        if len(facetas) < 2000:
            return np.concatenate([self.triangulos[f] for f in facetas.tolist()])
        return np.flatnonzero(np.isin(self.faceta, facetas))

    def datos(self, facetas):
        V = self.V[np.unique(self.F[self.indices(facetas)])]
        return V, self.C_f[facetas], self.N_f[facetas], self.area_f[facetas]

    def conectadas(self, semilla, buenas):
        """Facetas de `buenas` (máscara) conectadas con la semilla por cualquier arista."""
        marca = np.zeros(self.nf, bool)
        marca[semilla] = True
        frente = np.array([semilla])
        ini, ind = self.vec
        while len(frente):
            k = np.concatenate([ind[ini[f]:ini[f + 1]] for f in frente.tolist()]) if len(frente) < 256 else \
                ind[np.concatenate([np.arange(ini[f], ini[f + 1]) for f in frente.tolist()])]
            k = np.unique(k)
            k = k[buenas[k] & ~marca[k]]
            marca[k] = True
            frente = k
        return np.flatnonzero(marca)


def _coinciden(g, forma, triangulos, tol):
    """Por triángulo: los tres vértices en la tolerancia y, en cada uno, la normal de la forma de acuerdo con la del
    triángulo. Mirar la normal solo en el centro no alcanza: los bordes de una tapa y de un cilindro caben en una esfera,
    y en el centro de la tapa la normal de esa esfera es justo la de la tapa."""
    F = g.F[triangulos]
    unicos, inv = np.unique(F, return_inverse=True)
    inv = inv.reshape(-1, 3)
    V = g.V[unicos]
    cerca = (np.abs(forma.distancia(V)) <= tol)[inv].all(1)
    astilla = g.astilla[triangulos]
    if forma.tipo == "plane":
        return cerca & (astilla | (np.abs(g.N[triangulos] @ forma.a) >= _NORMAL_PLANO))
    acuerdo = np.abs(np.einsum("ijk,ik->ij", forma.normal(V)[inv], g.N[triangulos])) >= _NORMAL_CURVA
    salida = cerca & (astilla | acuerdo.all(1))
    if forma.tipo in ("cone", "torus"):
        # un anillo teselado da la vuelta de a pasos chicos: cuatro empalmes rectos juntos no son un toro
        er = forma._rz(V)[2][inv]
        menor = np.minimum.reduce([np.einsum("ij,ij->i", er[:, a], er[:, b]) for a, b in ((0, 1), (1, 2), (2, 0))])
        salida &= astilla | (menor >= _VUELTA)
    return salida


def _adentro(g, forma, tol, libre):
    """Facetas libres que coinciden con la forma en todos sus triángulos."""
    usados = np.flatnonzero(libre[g.faceta])
    malas = np.zeros(g.nf, bool)
    malas[g.faceta[usados[~_coinciden(g, forma, usados, tol)]]] = True
    return libre & ~malas


def _ajusta(g, forma, facetas, tol):
    """¿La forma entra en la tolerancia en estas facetas?"""
    A = g.area_f[facetas]
    # dos cuerdas seguidas siempre caben en un círculo: una curva teselada tiene tres o más, y ninguna manda
    if forma.tipo != "plane" and (len(facetas) < 3 or float(A.max()) > 0.6 * float(A.sum())):
        return False
    return bool(_coinciden(g, forma, g.indices(facetas), tol).all())


def _candidata(g, semilla, libre, tol, diagonal):
    """La forma que más área explica alrededor de la semilla: (forma, facetas) o None. Prueba parches cada vez mayores y
    corta cuando ya ninguna forma entra: un parche grande cruza a la superficie de al lado."""
    mejor, area_mejor, sin_forma = None, 0.0, 0
    for n in _ESCALAS:
        parche = g.parche(semilla, n, libre)
        chico = len(parche) < n
        V, C, N, A = g.datos(parche)
        hallada = None
        for ajuste in _AJUSTES:
            forma = ajuste(V, C, N, A)
            if forma is None or not _sensata(forma, diagonal):
                continue
            if _ajusta(g, forma, parche, tol):
                hallada = forma
                break
        if hallada is None:
            sin_forma += 1
            if sin_forma == 2 or chico:                            # un toro chico recién se define con más parche
                break
            continue
        sin_forma = 0
        forma = hallada
        for _ in range(6):                                         # afinar con todo lo que se fue sumando
            facetas = g.conectadas(semilla, _adentro(g, forma, tol, libre))
            area = float(g.area_f[facetas].sum())
            if len(facetas) < 2 and forma.tipo != "plane":
                area = 0.0
                break
            nueva = _POR_TIPO[forma.tipo](*g.datos(facetas))
            if nueva is None or not _ajusta(g, nueva, facetas, tol):
                break
            forma = nueva
            if len(g.conectadas(semilla, _adentro(g, forma, tol, libre))) <= len(facetas):
                break
        if area / _PESO[forma.tipo] > area_mejor:
            mejor, area_mejor = (forma, facetas), area / _PESO[forma.tipo]
        if chico or len(facetas) >= 4 * n:
            break
    return mejor


def _sensata(forma, diagonal):
    if forma.tipo == "torus" and forma.c >= forma.b:              # tubo más grueso que el anillo: no es una pieza real
        return False
    return forma.tipo == "plane" or max(forma.b, forma.c) <= _RADIO_MAXIMO * diagonal


def _absorber(g, vivas, etiqueta, tol):
    """Cada forma, ya afinada, se queda con las facetas sin clasificar que le corresponden: lo que un ajuste temprano
    dejó afuera, y que separaba a dos pedazos de la misma superficie."""
    for i, (forma, facetas) in vivas.items():
        libre = etiqueta < 0
        libre[facetas] = True
        nuevas = np.union1d(facetas, g.conectadas(int(facetas[0]), _adentro(g, forma, tol, libre)))
        vivas[i] = (forma, nuevas)
        etiqueta[nuevas] = i


def _fusionar(g, formas, etiqueta, tol, diagonal):
    """Una forma partida (un cono teselado con dos tramos de distinta resolución) vuelve a ser una: cada forma prueba
    quedarse con sus vecinas chicas, ajustando las dos juntas."""
    orden = sorted(range(len(formas)), key=lambda i: -float(g.area_f[formas[i][1]].sum()))
    vivas = dict(enumerate(formas))
    for _ in range(3):                                     # absorber acerca pedazos que recién ahí se pueden juntar
        cuantas = len(vivas)
        _absorber(g, vivas, etiqueta, tol)
        _juntar(g, vivas, etiqueta, orden, tol, diagonal)
        if len(vivas) == cuantas:
            break
    _absorber(g, vivas, etiqueta, tol)
    nuevo = {viejo: k for k, viejo in enumerate(sorted(vivas))}
    salida = np.full(len(etiqueta), -1, np.int64)
    for viejo, k in nuevo.items():
        salida[vivas[viejo][1]] = k
    return [vivas[i] for i in sorted(vivas)], salida


def _juntar(g, vivas, etiqueta, orden, tol, diagonal):
    for i in orden:
        if i not in vivas:
            continue
        hubo = True
        while hubo:
            hubo = False
            forma, facetas = vivas[i]
            vecinas = np.unique(np.concatenate([g.vecinas(f, g.vec) for f in facetas.tolist()]))
            for j in np.unique(etiqueta[vecinas]).tolist():
                if j == i or j not in vivas:
                    continue
                area_j, area_i = float(g.area_f[vivas[j][1]].sum()), float(g.area_f[facetas].sum())
                if area_j > area_i:
                    continue
                union = np.r_[facetas, vivas[j][1]]
                datos = g.datos(union)
                # una banda angosta de cono o de esfera cabe como cilindro: juntas se ve qué eran. Con un pedacito no
                # se cambia de tipo: tres triángulos sueltos no vuelven toro a un cilindro.
                for ajuste in (_POR_TIPO[forma.tipo], *(_AJUSTES[1:] if area_j >= 0.05 * area_i else ())):
                    nueva = ajuste(*datos)
                    if nueva is not None and _sensata(nueva, diagonal) and _ajusta(g, nueva, union, tol):
                        vivas[i] = (nueva, union)
                        etiqueta[vivas.pop(j)[1]] = i
                        hubo = True
                        break
                if hubo:
                    break


def _segmentar(g, tol, diagonal, area_total):
    """Reparte las facetas en formas: [(forma, facetas)] y la etiqueta de cada faceta (-1 = sin clasificar)."""
    libre = np.ones(g.nf, bool)
    probada = np.zeros(g.nf, bool)
    etiqueta = np.full(g.nf, -1, np.int64)
    formas, fallas = [], 0
    for semilla in np.argsort(-g.area_f, kind="stable").tolist():
        if not libre[semilla] or probada[semilla]:
            continue
        hallada = _candidata(g, semilla, libre, tol, diagonal)
        util = False
        if hallada is not None:
            forma, facetas = hallada
            # una sola faceta chica sin aristas marcadas no es una cara: es un pedazo de superficie libre
            util = forma.tipo != "plane" or len(g.triangulos[semilla]) >= 3 or g.filo[semilla] \
                or float(g.area_f[facetas].sum()) > 2e-3 * area_total
        if util:
            etiqueta[facetas] = len(formas)
            libre[facetas] = False
            formas.append((forma, facetas))
            fallas = 0
            continue
        fallas += 1
        probada[g.parche(semilla, 12, libre)] = True           # sigue libre: otra forma todavía puede quedársela
        if fallas >= _TOPE_FALLAS:
            break
    return _fusionar(g, formas, etiqueta, tol, diagonal)


# ---------------------------------------------------------------- la ficha
def _r(x, d=4):
    return round(float(x), d) + 0.0


def _v(x):
    return [_r(c, 6) for c in x]


def _extremos(forma, V):
    """(altura desde, altura hasta) a lo largo del eje."""
    z = (V - forma.p) @ forma.a
    return float(z.min()), float(z.max())


def _arco(forma, V):
    """Grados que recorre la forma alrededor de su eje."""
    q = V - forma.p
    u, v = _base(forma.a)
    ang = np.unique(np.round(np.arctan2(q @ v, q @ u), 6))
    pasos = np.diff(np.r_[ang, ang[0] + 2 * math.pi])
    hueco = float(pasos.max())
    return 360.0 if hueco <= 3 * float(np.median(pasos)) else 360.0 - math.degrees(hueco)


def _medidas(forma, V):
    """Medidas de la forma en mm y grados."""
    t = forma.tipo
    if t == "plane":
        return {"point": _v(V.mean(0)), "normal": _v(forma.a)}
    if t == "sphere":
        return {"center": _v(forma.p), "radius": _r(forma.b), "diameter": _r(2 * forma.b)}
    z0, z1 = _extremos(forma, V)
    base = {"axis_point": _v(forma.p + forma.a * z0), "axis": _v(forma.a), "height": _r(z1 - z0), "arc_degrees": _r(_arco(forma, V), 2)}
    if t == "cylinder":
        return dict(base, radius=_r(forma.b), diameter=_r(2 * forma.b))
    if t == "cone":
        return dict(base, radius_start=_r(forma.b + forma.c * z0), radius_end=_r(forma.b + forma.c * z1),
                    half_angle=_r(math.degrees(math.atan(abs(forma.c))), 3))
    return dict(base, center=_v(forma.p), major_radius=_r(forma.b), minor_radius=_r(forma.c))


def _ficha_forma(g, i, forma, facetas, tol):
    V, C, N, A = g.datos(facetas)
    d = forma.distancia(V)
    salida = {"id": i, "type": forma.tipo, "area": _r(A.sum(), 3), "sample_point": _v(V[np.argmin(((V - V.mean(0)) ** 2).sum(1))]),
              "triangles": int(sum(len(g.triangulos[f]) for f in facetas.tolist())), "fit_error": _r(np.sqrt((d * d).mean()), 6),
              "max_error": _r(np.abs(d).max(), 6)}
    salida.update(_medidas(forma, V))
    if forma.tipo != "plane":
        sentido = float((np.einsum("ij,ij->i", forma.normal(C), N) * A).sum())
        salida["concave"] = bool(sentido < 0)             # la normal hacia afuera del material mira al eje o al centro
    return salida


def _vecinas(g, etiqueta_f, n):
    a, b = etiqueta_f[g.faceta[g.t1]], etiqueta_f[g.faceta[g.t2]]
    s = (a != b) & (a >= 0) & (b >= 0)
    salida = [set() for _ in range(n)]
    for x, y in np.unique(np.c_[a[s], b[s]], axis=0).tolist():
        salida[x].add(y)
        salida[y].add(x)
    return [sorted(s) for s in salida]


def _agujeros(fichas):
    """Agujeros: cilindros cóncavos de vuelta completa. Ciego si una vecina los tapa (plano perpendicular del tamaño de
    la boca, o cono que cierra)."""
    salida = []
    for f in fichas:
        if f["type"] != "cylinder" or not f["concave"] or f["arc_degrees"] < 300:
            continue
        a = np.array(f["axis"])
        tapa = None
        for k in f["neighbors"]:
            o = fichas[k]
            if o["type"] == "plane" and abs(abs(float(np.dot(o["normal"], a))) - 1) < 1e-3 \
                    and abs(o["area"] - math.pi * f["radius"] ** 2) < 0.15 * math.pi * f["radius"] ** 2:
                tapa = k
            elif o["type"] == "cone" and min(o["radius_start"], o["radius_end"]) < 0.1 * f["radius"]:
                tapa = k
        salida.append({"shape": f["id"], "diameter": f["diameter"], "depth": f["height"], "axis_point": f["axis_point"],
                       "axis": f["axis"], "through": tapa is None, "floor_shape": tapa})
    return salida


def _patrones(agujeros, tol):
    grupos = {}
    for h in agujeros:
        grupos.setdefault((round(h["diameter"], 2), round(h["depth"], 2), h["through"]), []).append(h)
    salida = []
    for (diametro, _d, _t), miembros in grupos.items():
        if len(miembros) < 3:
            continue
        P = np.array([np.add(h["axis_point"], np.multiply(h["axis"], h["depth"] / 2)) for h in miembros])
        comun = {"feature": "hole", "diameter": diametro, "count": len(miembros), "shapes": [h["shape"] for h in miembros],
                 "centers": [_v(p) for p in P]}
        t = max(tol * 3, 1e-3)
        rejilla = rf._rejilla(P, t)
        circulo = None if rejilla else rf._circulo(P, t)
        if rejilla:
            salida.append(dict(comun, type="rectangular_pattern", directions=[
                {"direction": _v(u), "count": k, "step": _r(p)} for u, k, p in rejilla]))
        elif circulo:
            c, n, paso = circulo
            salida.append(dict(comun, type="circular_pattern", axis_point=_v(c), axis=_v(n), angle_step=_r(paso)))
    return salida


def _eje_revolucion(fichas, area_total):
    """El eje alrededor del cual gira más superficie, con la parte del área que explica."""
    mejor = None
    curvas = [f for f in fichas if f["type"] in ("cylinder", "cone", "torus")]
    for f in sorted(curvas, key=lambda x: -x["area"])[:12]:
        o, a = np.array(f["axis_point"]), np.array(f["axis"])
        total = 0.0
        for g in fichas:
            if g["type"] in ("cylinder", "cone", "torus"):
                if abs(abs(float(np.dot(g["axis"], a))) - 1) < 1e-3 \
                        and np.linalg.norm(np.cross(a, np.subtract(g["axis_point"], o))) < 1e-2 * max(1.0, f["height"]):
                    total += g["area"]
            elif g["type"] == "plane":
                total += g["area"] * (abs(abs(float(np.dot(g["normal"], a))) - 1) < 1e-3)
            elif np.linalg.norm(np.cross(a, np.subtract(g["center"], o))) < 1e-2 * max(1.0, g["radius"]):
                total += g["area"]
        if mejor is None or total > mejor["area"]:
            mejor = {"axis_point": f["axis_point"], "axis": f["axis"], "area": _r(total, 3), "share": _r(total / area_total, 4)}
    return mejor


def _simetrias(m, fichas, tol, superficie):
    """Planos de simetría que pasan por el centro de la superficie: normales candidatas, los ejes de inercia de la
    superficie y las normales de los planos mayores."""
    P, n = cm.muestrear(m, 600, _SEMILLA)
    P = P[:n]
    c = (m.areas_caras()[:, None] * m.triangulos().mean(1)).sum(0) / m.area()   # el de la muestra se corre décimas de mm
    candidatas = list(np.linalg.eigh(np.cov((P - c).T))[1].T)
    candidatas += [np.array(f["normal"]) for f in sorted((f for f in fichas if f["type"] == "plane"), key=lambda x: -x["area"])[:6]]
    salida, vistas = [], []
    for w in candidatas:
        if any(abs(abs(float(w @ x)) - 1) < 1e-4 for x in vistas):
            continue
        vistas.append(w)
        reflejo = P - 2 * ((P - c) @ w)[:, None] * w
        d = superficie.mas_cercano(reflejo)[0]
        if float(np.percentile(d, 99)) <= 3 * tol:
            salida.append({"plane_point": _v(c), "normal": _v(w), "mean_error": _r(d.mean(), 5)})
    return salida


def _calidad(m, fichas, tol):
    """CAD o escaneo: una malla de CAD deja las superficies sobre sus vértices, con un error mucho menor que la tolerancia
    y casi toda el área en facetas grandes."""
    a = m.caja()
    errores = [f["fit_error"] for f in fichas]
    ruido = float(np.median(errores)) if errores else None
    cerrada = m.es_cerrada()
    return {"closed": cerrada, "origin": "cad" if ruido is not None and ruido <= tol / 4 else "scan", "noise_mm": ruido,
            "bbox": {"min": _v(a[0]), "max": _v(a[1]), "size": _v(np.subtract(a[1], a[0]))}}


def con_ruido(m):
    """¿Malla de escaneo? En una de CAD abundan los pares de triángulos coplanares justos (planos y tiras de cilindros); con
    ruido casi no queda ninguno. Una esfera de CAD fina también cae acá: se mide igual, con la tolerancia que se pida."""
    return float(np.mean(_Facetas(m, 1e-3).coseno >= _COPLANAR_EXACTO)) < 0.02        # medido: CAD desde 0,026 y con ruido hasta 0,012


def medir(m, *, tolerancia=None):
    """Formas de la malla `m`. Devuelve (ficha, forma de cada triángulo de `m`, con -1 si no se clasificó, y las formas
    ajustadas). `tolerancia` en mm: cuánto puede apartarse un vértice de la forma; por defecto 2e-4 de la diagonal."""
    cm.exigir_malla(m)
    caja = np.array(m.caja())
    diagonal = float(np.linalg.norm(caja[1] - caja[0]))
    defecto = max(_TOLERANCIA_RELATIVA * diagonal, 1e-3)
    tol = float(tolerancia) if tolerancia is not None else defecto
    if not (tol > 0 and math.isfinite(tol)):
        raise geo.ErrorGeometria("La tolerancia tiene que ser mayor que cero (mm).")
    g = _Facetas(m, tol, ruidosa=tol > defecto)
    area_total = float(g.area.sum())
    pares, etiqueta_f = _segmentar(g, tol, diagonal, area_total)
    pares = [(f, np.sort(k)) for f, k in pares]
    fichas = [_ficha_forma(g, i, f, k, tol) for i, (f, k) in enumerate(pares)]
    for f, v in zip(fichas, _vecinas(g, etiqueta_f, len(fichas)), strict=True):
        f["neighbors"] = v
    agujeros = _agujeros(fichas)
    etiqueta = np.full(len(m.caras), -1, np.int64)
    etiqueta[g.validos] = etiqueta_f[g.faceta]
    sin = float(g.area[etiqueta_f[g.faceta] < 0].sum())
    ficha = {"triangles": len(m.caras), "area": _r(area_total, 3), "tolerance": _r(tol, 6), "quality": _calidad(m, fichas, defecto),
             "shapes": fichas, "summary": {t: sum(f["type"] == t for f in fichas) for t in _POR_TIPO},
             "unclassified_percent": _r(100.0 * sin / area_total, 3),
             "unclassified_triangles": int((etiqueta < 0).sum()), "holes": agujeros, "patterns": _patrones(agujeros, tol),
             "revolution_axis": _eje_revolucion(fichas, area_total),
             "symmetries": _simetrias(m, fichas, tol, cm.Superficie(m, pedazos=6000))}
    return ficha, etiqueta, [f for f, _k in pares]


def analizar(m, *, tolerancia=None):
    """Solo la ficha de `medir`."""
    return medir(m, tolerancia=tolerancia)[0]

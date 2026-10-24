# -*- coding: utf-8 -*-
"""
Solver numérico de restricciones de boceto (kernel de restricciones).

Fusion 360 no documenta su solver (informe_analisis.md §1: el módulo no se identificó),
solo su comportamiento: restricciones geométricas + cotas, estado "totalmente restringido"
(`isFullyConstrained`) y errores ante restricciones en conflicto. Acá se implementa con un
enfoque estándar y propio:

  - Incógnitas: coordenadas (u, v) de los puntos no fijos, radios de círculos y radios menores de
    elipses no fijos, y parámetros auxiliares de contacto (punto sobre spline, tangencia entre curvas
    libres) que se estiman en cada resolución.
  - Cada restricción/cota aporta residuos que valen 0 cuando se cumple.
  - Se minimiza la suma de cuadrados con `scipy.optimize.least_squares` (Levenberg-Marquardt),
    más una regularización muy débil hacia la posición actual: así lo que queda libre
    (sub-restringido) no "salta", se mueve lo mínimo.
  - Grados de libertad restantes = incógnitas − rango del jacobiano de las restricciones.
  - Antes del numérico (SC4), coincidencias y horizontales/verticales se cumplen por construcción: esas
    coordenadas comparten incógnita (`_Sistema._fusionar`). Mismo mínimo y mismos grados de libertad, con
    muchas menos incógnitas (400 líneas encadenadas: arrastre de 23 s a ~0,27 s).

`auto_restringir` es la versión propia de AutoConstrain (SKT-AUTO-CONSTRAIN).
"""
import math
from dataclasses import dataclass, field

import numpy as np

from . import auto_candidatos
from .boceto import (CIRCULARES, ELIPTICAS, Arco, ArcoElipse, Circulo, Elipse, ErrorBoceto, Linea, Spline,
                     _numero, distancia_con_circulo, dominio, evaluar_primitiva, mas_cercano, primitivas_entidad,
                     puntos_primitiva, signos_cuadrante)

TOLERANCIA = 1e-6
_PESO_REGULARIZACION = 1e-8  # No sesgar las restricciones de cadenas largas durante el arrastre.
_PESO_ARRASTRE = 1.0
_ESCALA_TANGENTE = 10.0      # mm: convierte el seno del ángulo en un residuo comparable a una distancia
_ESCALA_CURVATURA = 100.0    # mm²
TOPE_AUTO_RESTRINGIR = 500
MAX_INTENTOS_EXTRA = 6       # alternativas repetidas que se descartan antes de rendirse (cada una cuesta un cálculo entero)
TOPE_TERMINAR_AUTO = 250      # «Terminar con AutoConstrain» de Fusion no corre con más de 250 entidades


class ResultadoSolver:
    def __init__(self, estado, gdl, residuo_max, mensaje="", determinadas=frozenset()):
        self.estado = estado            # 'ok' | 'inconsistente'
        self.gdl = gdl                  # grados de libertad que quedan
        self.residuo_max = residuo_max
        self.mensaje = mensaje
        # Entidades que ya no se pueden mover (Fusion las dibuja en negro/blanco; las libres, en azul).
        self.determinadas = frozenset(determinadas)

    @property
    def ok(self):
        return self.estado == "ok"

    @property
    def totalmente_restringido(self):
        return self.ok and self.gdl == 0

    def descripcion(self):
        if not self.ok:
            return f"Restricciones en conflicto (error {self.residuo_max:.3g} mm). {self.mensaje}".strip()
        if self.gdl == 0:
            return "Totalmente restringido."
        return f"Sub-restringido: quedan {self.gdl} grados de libertad."


def _signo(v):
    return 1.0 if v >= 0 else -1.0


def _cruz(a, b):
    return a[0] * b[1] - a[1] * b[0]


def _unitario(v):
    n = math.hypot(*v) or 1e-12
    return v[0] / n, v[1] / n


class _Sistema:
    """Arma el vector de incógnitas y la función de residuos de un boceto."""

    def __init__(self, boceto, valores_cotas, grupo=None, fusionar=False):
        """`grupo` (de `_grupos`) limita el sistema a una parte independiente del boceto: sus incógnitas y
        sus términos. Sin grupo, el boceto entero (como siempre). `fusionar` (SC4): ver `_fusionar`."""
        self.b = boceto
        self.valores = valores_cotas
        self._curvas = list(boceto.curvas.values()) if grupo is None else grupo["curvas"]
        self._restricciones = list(boceto.restricciones.values()) if grupo is None else grupo["restricciones"]
        self._cotas = [c for c in (boceto.cotas.values() if grupo is None else grupo["cotas"]) if not c.referencia]
        self.fijos_p, self.fijos_r = _fijos(boceto)
        raiz, self._cumplidas = self._fusionar() if fusionar else ((lambda k: k), set())
        # idx_p[pid] = (índice de x, índice de y). Fusionadas, varias coordenadas comparten una incógnita, que
        # arranca en su promedio; `cuenta` dice cuántas coordenadas representa cada incógnita.
        self.idx_p, self.idx_r, x0, cuenta, var = {}, {}, [], [], {}
        for pid, p in boceto.puntos.items():
            if pid not in self.fijos_p and (grupo is None or pid in grupo["p"]):
                ij = []
                for k, v in ((0, p.x), (1, p.y)):
                    j = var.setdefault(raiz((pid, k)), len(x0))
                    if j == len(x0):
                        x0.append(0.0)
                        cuenta.append(0)
                    x0[j] += v
                    cuenta[j] += 1
                    ij.append(j)
                self.idx_p[pid] = tuple(ij)
        x0 = [s / k for s, k in zip(x0, cuenta, strict=True)]
        for cid, c in boceto.curvas.items():
            if isinstance(c, (Circulo, Elipse, ArcoElipse)) and cid not in self.fijos_r and (
                    grupo is None or cid in grupo["r"]):
                self.idx_r[cid] = len(x0)
                x0.append(c.radio if isinstance(c, Circulo) else c.radio_menor)
        self.n_base = len(x0)
        self.x0 = np.array(x0, dtype=float)
        self._extra = []
        self.terminos = []
        self._armar()
        if self._extra:
            self.x0 = np.concatenate([self.x0, np.array(self._extra, dtype=float)])
        self.cuenta = np.ones(len(self.x0))
        self.cuenta[:len(cuenta)] = cuenta

    def _fusionar(self):
        """SC4 (colocación por construcción): las coincidencias punto-punto y las horizontales/verticales se cumplen
        compartiendo incógnita (la x o la y de los puntos), así no entran al solver: una cadena de líneas queda con
        ~4 veces menos incógnitas. Las coordenadas fijas no se fusionan: esas restricciones quedan como término.
        Devuelve (raíz de cada coordenada (pid, eje), ids de las restricciones que ya se cumplen así)."""
        padre, cumplidas = {}, set()

        def raiz(k):
            padre.setdefault(k, k)
            while padre[k] != k:
                padre[k] = padre[padre[k]]
                k = padre[k]
            return k
        for r in self._restricciones:
            e, tipos = r.entidades, [self.b.tipo_de(i) for i in r.entidades]
            if r.tipo == "coincidente" and tipos == ["punto", "punto"]:
                pares = [(e[0], e[1], 0), (e[0], e[1], 1)]
            elif r.tipo in ("horizontal", "vertical"):
                a, c = (self.b.curvas[e[0]].p1, self.b.curvas[e[0]].p2) if tipos == ["linea"] else e
                pares = [(a, c, 1 if r.tipo == "horizontal" else 0)]
            else:
                continue
            if any(p in self.fijos_p for a, c, _k in pares for p in (a, c)):
                continue
            for a, c, k in pares:
                padre[raiz((a, k))] = raiz((c, k))
            cumplidas.add(r.id)
        return raiz, cumplidas

    def _parametro(self, valor):
        """Agrega una incógnita auxiliar (parámetro de contacto) y devuelve su índice."""
        self._extra.append(float(valor))
        return self.n_base + len(self._extra) - 1

    # ---- acceso a la geometría para un vector x
    def P(self, x, pid):
        i = self.idx_p.get(pid)
        if i is None:
            p = self.b.puntos[pid]
            return p.x, p.y
        return x[i[0]], x[i[1]]

    def Rv(self, x, cid):
        """Radio guardado (círculo) o radio menor (elipse)."""
        c = self.b.curvas[cid]
        i = self.idx_r.get(cid)
        if i is not None:
            return x[i]
        return c.radio if isinstance(c, Circulo) else c.radio_menor

    def R(self, x, cid):
        c = self.b.curvas[cid]
        if isinstance(c, Circulo):
            return self.Rv(x, cid)
        (cx, cy), (sx, sy) = self.P(x, c.centro), self.P(x, c.inicio)
        return math.hypot(sx - cx, sy - cy)

    def C(self, x, cid):
        return self.P(x, self.b.curvas[cid].centro)

    def L(self, x, lid):
        ln = self.b.curvas[lid]
        return self.P(x, ln.p1), self.P(x, ln.p2)

    def prim(self, x, cid):
        return primitivas_entidad(self.b.curvas[cid], lambda p: self.P(x, p), lambda k: self.Rv(x, k))[0]

    def elipse(self, x, cid):
        """(centro, a, b, ángulo del eje mayor)."""
        c = self.b.curvas[cid]
        (cx, cy), (mx, my) = self.P(x, c.centro), self.P(x, c.mayor)
        return (cx, cy), math.hypot(mx - cx, my - cy), self.Rv(x, cid), math.atan2(my - cy, mx - cx)

    def dist_signada(self, x, p, lid):
        (ax, ay), (bx, by) = self.L(x, lid)
        n = math.hypot(bx - ax, by - ay) or 1e-12
        return ((bx - ax) * (p[1] - ay) - (by - ay) * (p[0] - ax)) / n

    def sobre_elipse(self, x, p, cid):
        """Residuo radial (mm) de un punto respecto de una elipse."""
        (cx, cy), a, b, ang = self.elipse(x, cid)
        ca, sa = math.cos(ang), math.sin(ang)
        dx, dy = p[0] - cx, p[1] - cy
        qx, qy = ca * dx + sa * dy, -sa * dx + ca * dy
        r = math.hypot(qx, qy)
        if r < 1e-12:
            return -min(a, b)
        c, s = qx / r, qy / r
        return r - a * b / (math.hypot(b * c, a * s) or 1e-12)

    def separacion(self, x, o, d):
        """Distancia entre una curva y su desfase."""
        if isinstance(self.b.curvas[o], Linea):
            return abs(self.dist_signada(x, self.P(x, self.b.curvas[d].p1), o))
        return abs(self.R(x, d) - self.R(x, o))

    def extremo(self, x, cid, pid):
        """(tangente unitaria, curvatura con signo) al recorrer la curva ALEJÁNDOSE de su extremo pid."""
        prim = self.prim(x, cid)
        t0, t1, _ = dominio(prim)
        ini = self.b.curvas[cid].extremos()[0]
        _C, D1, D2 = evaluar_primitiva(prim, t0 if pid == ini else t1, 2)
        s = 1.0 if pid == ini else -1.0
        n = math.hypot(*D1) or 1e-12
        return (s * D1[0] / n, s * D1[1] / n), s * _cruz(D1, D2) / n ** 3

    # ---- residuos
    def _armar(self):
        b, x0, T = self.b, self.x0, self.terminos
        for c in self._curvas:
            if isinstance(c, Arco):
                T.append(lambda x, c=c: [math.dist(self.P(x, c.inicio), self.P(x, c.centro))
                                         - math.dist(self.P(x, c.fin), self.P(x, c.centro))])
            elif isinstance(c, ArcoElipse):
                T.append(lambda x, c=c: [self.sobre_elipse(x, self.P(x, c.inicio), c.id),
                                         self.sobre_elipse(x, self.P(x, c.fin), c.id)])
        for r in self._restricciones:
            t = r.tipo
            e = r.entidades
            tipos = [b.tipo_de(i) for i in e]
            if t == "fijo" or r.id in self._cumplidas:
                continue
            if t == "coincidente":
                if tipos[1] == "punto":
                    T.append(lambda x, a=e[0], c=e[1]: [self.P(x, a)[0] - self.P(x, c)[0], self.P(x, a)[1] - self.P(x, c)[1]])
                elif tipos[1] == "linea":
                    T.append(lambda x, a=e[0], l=e[1]: [self.dist_signada(x, self.P(x, a), l)])
                elif tipos[1] in CIRCULARES:
                    T.append(lambda x, a=e[0], c=e[1]: [math.dist(self.P(x, a), self.C(x, c)) - self.R(x, c)])
                elif tipos[1] in ELIPTICAS:
                    T.append(lambda x, a=e[0], c=e[1]: [self.sobre_elipse(x, self.P(x, a), c)])
                else:
                    self._contacto_punto(e[0], e[1])
            elif t in ("horizontal", "vertical"):
                k = 1 if t == "horizontal" else 0
                if tipos == ["linea"]:
                    T.append(lambda x, l=e[0], k=k: [self.L(x, l)[0][k] - self.L(x, l)[1][k]])
                else:
                    T.append(lambda x, a=e[0], c=e[1], k=k: [self.P(x, a)[k] - self.P(x, c)[k]])
            elif t in ("paralela", "perpendicular"):
                def f(x, l1=e[0], l2=e[1], par=(t == "paralela")):
                    (a, bb), (c, d) = self.L(x, l1), self.L(x, l2)
                    u = (bb[0] - a[0], bb[1] - a[1])
                    v = (d[0] - c[0], d[1] - c[1])
                    nu, nv = math.hypot(*u) or 1e-12, math.hypot(*v) or 1e-12
                    escala = (nu + nv) / 2
                    if par:
                        return [(u[0] * v[1] - u[1] * v[0]) / (nu * nv) * escala]
                    return [(u[0] * v[0] + u[1] * v[1]) / (nu * nv) * escala]
                T.append(f)
            elif t == "igual":
                if tipos == ["linea", "linea"]:
                    T.append(lambda x, l1=e[0], l2=e[1]: [math.dist(*self.L(x, l1)) - math.dist(*self.L(x, l2))])
                elif tipos[0] in ELIPTICAS:
                    T.append(lambda x, c1=e[0], c2=e[1]: [self.elipse(x, c1)[1] - self.elipse(x, c2)[1],
                                                          self.elipse(x, c1)[2] - self.elipse(x, c2)[2]])
                else:
                    T.append(lambda x, c1=e[0], c2=e[1]: [self.R(x, c1) - self.R(x, c2)])
            elif t == "tangente":
                self._tangencia(e, tipos)
            elif t == "curvatura":
                pa, pb = b.extremo_comun(e[0], e[1])

                def f(x, a=e[0], c=e[1], pa=pa, pb=pb):
                    (ta, ka), (tb, kb) = self.extremo(x, a, pa), self.extremo(x, c, pb)
                    return [_cruz(ta, tb) * _ESCALA_TANGENTE, (ka + kb) * _ESCALA_CURVATURA]
                T.append(f)
            elif t == "concentrica":
                T.append(lambda x, c1=e[0], c2=e[1]: [self.C(x, c1)[0] - self.C(x, c2)[0],
                                                      self.C(x, c1)[1] - self.C(x, c2)[1]])
            elif t == "punto_medio" and tipos[1] == "arco":
                def f(x, p=e[0], k=e[1]):
                    prim, q = self.prim(x, k), self.P(x, p)
                    m = evaluar_primitiva(prim, dominio(prim)[1] / 2)[0]
                    return [q[0] - m[0], q[1] - m[1]]
                T.append(f)
            elif t == "punto_medio":
                def f(x, p=e[0], l=e[1]):
                    (a, bb), q = self.L(x, l), self.P(x, p)
                    return [q[0] - (a[0] + bb[0]) / 2, q[1] - (a[1] + bb[1]) / 2]
                T.append(f)
            elif t == "colineal":
                T.append(lambda x, l1=e[0], l2=e[1]: [self.dist_signada(x, q, l1) for q in self.L(x, l2)])
            elif t == "simetrica":
                for a, c in self._pares_simetricos(e, tipos):
                    T.append(lambda x, a=a, c=c, l=e[2]: self._simetria(x, a, c, l))
                if tipos[0] in CIRCULARES:
                    T.append(lambda x, c1=e[0], c2=e[1]: [self.R(x, c1) - self.R(x, c2)])
                elif tipos[0] in ELIPTICAS:
                    T.append(lambda x, c1=e[0], c2=e[1]: [self.Rv(x, c1) - self.Rv(x, c2)])
            elif t == "poligono":
                vertices = b.vertices_cadena(e)

                def f(x, vs=tuple(vertices)):
                    P = [self.P(x, v) for v in vs]
                    m = len(P)
                    cx, cy = sum(p[0] for p in P) / m, sum(p[1] for p in P) / m
                    r0 = math.hypot(P[0][0] - cx, P[0][1] - cy)
                    l0 = math.dist(P[0], P[1])
                    return ([math.hypot(p[0] - cx, p[1] - cy) - r0 for p in P[1:]]
                            + [math.dist(P[i], P[(i + 1) % m]) - l0 for i in range(1, m)])
                T.append(f)
            elif t == "desfase":
                if len(e) == 4:
                    T.append(lambda x, e=tuple(e): [self.separacion(x, e[2], e[3]) - self.separacion(x, e[0], e[1])])
                else:
                    def f(x, k=e[0], p=e[1], q=e[2]):
                        a, c = self.P(x, p), self.P(x, q)
                        if isinstance(self.b.curvas[k], Linea):
                            d = _unitario(np.subtract(*self.L(x, k)[::-1]))
                            return [(c[0] - a[0]) * d[0] + (c[1] - a[1]) * d[1]]
                        o = self.C(x, k)
                        u = _unitario((a[0] - o[0], a[1] - o[1]))
                        return [_cruz(u, (c[0] - o[0], c[1] - o[1]))]
                    T.append(f)
            elif t == "patron":
                if len(e) == 2:
                    centro_fijo = r.datos.get("centro")      # B-55: giro alrededor de un centro FIJO (coordenadas)
                    if centro_fijo is not None:
                        def f(x, a=e[0], c=e[1], o=centro_fijo, ang=r.datos.get("angulo", 0.0)):
                            (px, py), (qx, qy) = self.P(x, a), self.P(x, c)
                            ca, sa = math.cos(ang), math.sin(ang)
                            return [o[0] + ca * (px - o[0]) - sa * (py - o[1]) - qx,
                                    o[1] + sa * (px - o[0]) + ca * (py - o[1]) - qy]
                        T.append(f)
                    else:
                        T.append(lambda x, a=e[0], c=e[1], dx=r.datos.get("dx", 0.0), dy=r.datos.get("dy", 0.0):
                                 [self.P(x, c)[0] - self.P(x, a)[0] - dx, self.P(x, c)[1] - self.P(x, a)[1] - dy])
                else:
                    def f(x, a=e[0], c=e[1], o=e[2], ang=r.datos.get("angulo", 0.0)):
                        (px, py), (qx, qy), (ox, oy) = self.P(x, a), self.P(x, c), self.P(x, o)
                        ca, sa = math.cos(ang), math.sin(ang)
                        return [ox + ca * (px - ox) - sa * (py - oy) - qx, oy + sa * (px - ox) + ca * (py - oy) - qy]
                    T.append(f)

        for c in self._cotas:
            if c.id not in self.valores:
                continue
            v, e, t = self.valores[c.id], c.entidades, c.tipo
            if c.datos.get("diametral"):
                v /= 2                    # cota con la línea central: el valor es el diámetro
            tipos = [b.tipo_de(i) for i in e]
            if t in ("radio", "diametro"):
                k = 1.0 if t == "radio" else 2.0
                T.append(lambda x, cid=e[0], v=v, k=k: [k * self.R(x, cid) - v])
            elif t == "desfase":
                T.append(lambda x, o=e[0], d=e[1], v=v: [self.separacion(x, o, d) - v])
            elif t == "angulo":
                def f(x, l1=e[0], l2=e[1], v=math.radians(v), s=signos_cuadrante(c.datos.get("cuadrante"))):
                    (a, bb), (cc, d) = self.L(x, l1), self.L(x, l2)
                    u = (s[0] * (bb[0] - a[0]), s[0] * (bb[1] - a[1]))
                    w = (s[1] * (d[0] - cc[0]), s[1] * (d[1] - cc[1]))
                    # Como paralela/perpendicular: residuo en mm, sin perder peso ni rango al crecer las líneas.
                    escala = (math.hypot(*u) + math.hypot(*w)) / 2
                    return [(math.atan2(abs(u[0] * w[1] - u[1] * w[0]), u[0] * w[0] + u[1] * w[1]) - v) * escala]
                T.append(f)
            elif t in ("distancia_h", "distancia_v"):
                k = 0 if t == "distancia_h" else 1
                s = c.datos.get("signo", 1.0)
                if tipos == ["linea"]:
                    T.append(lambda x, l=e[0], k=k, s=s, v=v: [s * (self.L(x, l)[1][k] - self.L(x, l)[0][k]) - v])
                else:
                    T.append(lambda x, p1=e[0], p2=e[1], k=k, s=s, v=v: [s * (self.P(x, p2)[k] - self.P(x, p1)[k]) - v])
            elif set(tipos) & set(CIRCULARES):
                self._distancia_circulo(e, tipos, c.datos.get("modo", "centro"), v)
            elif sorted(tipos) == ["punto", "spline"]:
                self._distancia_spline(e, tipos, v)
            elif tipos == ["punto", "punto"]:
                T.append(lambda x, p1=e[0], p2=e[1], v=v: [math.dist(self.P(x, p1), self.P(x, p2)) - v])
            elif tipos == ["linea"]:
                T.append(lambda x, l=e[0], v=v: [math.dist(*self.L(x, l)) - v])
            elif tipos == ["punto", "linea"]:
                s = _signo(self.dist_signada(x0, self.P(x0, e[0]), e[1]))
                T.append(lambda x, p=e[0], l=e[1], s=s, v=v: [s * self.dist_signada(x, self.P(x, p), l) - v])
            elif tipos == ["linea", "punto"]:
                s = _signo(self.dist_signada(x0, self.P(x0, e[1]), e[0]))
                T.append(lambda x, l=e[0], p=e[1], s=s, v=v: [s * self.dist_signada(x, self.P(x, p), l) - v])
            elif tipos == ["linea", "linea"]:
                s = _signo(self.dist_signada(x0, self.P(x0, b.curvas[e[1]].p1), e[0]))
                T.append(lambda x, l1=e[0], l2=e[1], s=s, v=v:
                         [s * self.dist_signada(x, self.P(x, b.curvas[l2].p1), l1) - v])

    def _distancia_circulo(self, e, tipos, modo, v):
        """Distancia con un círculo o arco (BOC-3): el signo y si dos círculos están anidados se toman de la
        geometría inicial, así el residuo es suave."""
        x0 = self.x0
        anidados = None
        if all(t in CIRCULARES for t in tipos):
            anidados = math.dist(self.C(x0, e[0]), self.C(x0, e[1])) < abs(self.R(x0, e[0]) - self.R(x0, e[1]))

        def medida(x):
            return distancia_con_circulo(tipos, e, modo, lambda p: self.P(x, p), lambda k: self.C(x, k),
                                         lambda k: self.R(x, k), lambda k: self.L(x, k), anidados)
        s = _signo(medida(x0))
        self.terminos.append(lambda x: [s * medida(x) - v])

    def _distancia_spline(self, e, tipos, v):
        """Punto a spline (BOC-3): parámetro auxiliar t del pie, |P − S(t)| = v y P − S(t) perpendicular a la curva.
        shortcut: si el pie más cercano es un extremo, el solver lo busca en la prolongación de la curva; recortarlo
        al dominio si hace falta."""
        p, k = e if tipos[0] == "punto" else e[::-1]
        j = self._parametro(mas_cercano(self.prim(self.x0, k), self.P(self.x0, p))[0])

        def f(x):
            q, d = evaluar_primitiva(self.prim(x, k), x[j], 1)
            a = self.P(x, p)
            w = (a[0] - q[0], a[1] - q[1])
            return [math.hypot(*w) - v, (w[0] * d[0] + w[1] * d[1]) / (math.hypot(*d) or 1e-12)]
        self.terminos.append(f)

    def _contacto_punto(self, pid, cid):
        """Punto sobre una curva libre (spline o cónica): un parámetro auxiliar t y P(t) = punto."""
        prim0 = self.prim(self.x0, cid)
        j = self._parametro(mas_cercano(prim0, self.P(self.x0, pid))[0])

        def f(x, pid=pid, cid=cid, j=j):
            q = evaluar_primitiva(self.prim(x, cid), x[j])[0]
            p = self.P(x, pid)
            return [q[0] - p[0], q[1] - p[1]]
        self.terminos.append(f)

    def _tangencia(self, e, tipos):
        T, x0 = self.terminos, self.x0
        comun = self.b.extremo_comun(e[0], e[1])
        if comun is not None:
            # Curvas encadenadas: tangentes paralelas en la unión (G1). Con un extremo compartido es la
            # única forma bien condicionada: la de "distancia al centro = radio" deja el jacobiano singular
            # justo en el punto de tangencia (y cuenta grados de libertad de más).
            pa, pb = comun
            T.append(lambda x, a=e[0], c=e[1], pa=pa, pb=pb:
                     [_cruz(self.extremo(x, a, pa)[0], self.extremo(x, c, pb)[0]) * _ESCALA_TANGENTE])
            return
        if "linea" in tipos and (tipos[0] in CIRCULARES or tipos[1] in CIRCULARES):
            l, c = (e[0], e[1]) if tipos[0] == "linea" else (e[1], e[0])
            s = _signo(self.dist_signada(x0, self.C(x0, c), l))
            T.append(lambda x, l=l, c=c, s=s: [s * self.dist_signada(x, self.C(x, c), l) - self.R(x, c)])
            return
        if tipos[0] in CIRCULARES and tipos[1] in CIRCULARES:
            c1, c2 = e
            d0 = math.dist(self.C(x0, c1), self.C(x0, c2))
            r1, r2 = self.R(x0, c1), self.R(x0, c2)
            if d0 < max(r1, r2):   # tangencia interior
                s = _signo(r1 - r2)
                T.append(lambda x, c1=c1, c2=c2, s=s: [math.dist(self.C(x, c1), self.C(x, c2))
                                                       - s * (self.R(x, c1) - self.R(x, c2))])
            else:                  # tangencia exterior
                T.append(lambda x, c1=c1, c2=c2: [math.dist(self.C(x, c1), self.C(x, c2))
                                                  - (self.R(x, c1) + self.R(x, c2))])
            return
        if "linea" in tipos and (tipos[0] in ELIPTICAS or tipos[1] in ELIPTICAS):
            l, c = (e[0], e[1]) if tipos[0] == "linea" else (e[1], e[0])
            s = _signo(self.dist_signada(x0, self.C(x0, c), l))

            def f(x, l=l, c=c, s=s):
                _o, a, bb, ang = self.elipse(x, c)
                (p, q) = self.L(x, l)
                n = _unitario((-(q[1] - p[1]), q[0] - p[0]))
                nu = n[0] * math.cos(ang) + n[1] * math.sin(ang)
                nv = -n[0] * math.sin(ang) + n[1] * math.cos(ang)
                return [s * self.dist_signada(x, self.C(x, c), l) - math.hypot(a * nu, bb * nv)]
            T.append(f)
            return
        # Caso general (curvas libres, elipses): un punto de contacto en cada curva, que coincidan y
        # con tangentes paralelas.
        pa0, pb0 = self.prim(x0, e[0]), self.prim(x0, e[1])
        ma = puntos_primitiva(pa0, 96)
        mejor = min(((math.dist(q, mas_cercano(pb0, q)[2]), q) for q in ma), key=lambda z: z[0])[1]
        ja = self._parametro(mas_cercano(pa0, mejor)[0])
        jb = self._parametro(mas_cercano(pb0, mejor)[0])

        def f(x, a=e[0], c=e[1], ja=ja, jb=jb):
            Ca, Da = evaluar_primitiva(self.prim(x, a), x[ja], 1)
            Cb, Db = evaluar_primitiva(self.prim(x, c), x[jb], 1)
            return [Ca[0] - Cb[0], Ca[1] - Cb[1], _cruz(_unitario(Da), _unitario(Db)) * _ESCALA_TANGENTE]
        T.append(f)

    def _pares_simetricos(self, e, tipos):
        """Pares de puntos que deben quedar espejados. En dos líneas se emparejan los extremos
        más cercanos al reflejo (así no se cruzan)."""
        if tipos[0] == "punto":
            return [(e[0], e[1])]
        d = lambda p, q: math.dist(self._reflejar(self.x0, self.P(self.x0, p), e[2]), self.P(self.x0, q))  # noqa: E731
        ca, cb = self.b.curvas[e[0]], self.b.curvas[e[1]]
        if tipos[0] in ("linea", "spline", "conica"):
            pa, pb = ca.puntos(), cb.puntos()
            directo = sum(d(p, q) for p, q in zip(pa, pb, strict=True))
            inverso = sum(d(p, q) for p, q in zip(pa, pb[::-1], strict=True))
            return list(zip(pa, pb if directo <= inverso else pb[::-1], strict=True))
        if tipos[0] == "elipse":
            return [(ca.centro, cb.centro), (ca.mayor, cb.mayor)]
        if tipos[:2] == ["arco", "arco"]:       # el reflejo invierte el sentido: inicio ↔ fin
            return [(ca.centro, cb.centro), (ca.inicio, cb.fin), (ca.fin, cb.inicio)]
        if tipos[0] == "arco_elipse":           # el reflejo invierte el sentido: inicio ↔ fin
            return [(ca.centro, cb.centro), (ca.mayor, cb.mayor), (ca.inicio, cb.fin), (ca.fin, cb.inicio)]
        return [(ca.centro, cb.centro)]

    def _reflejar(self, x, p, lid):
        (ax, ay), (bx, by) = self.L(x, lid)
        dx, dy = bx - ax, by - ay
        n2 = dx * dx + dy * dy or 1e-12
        t = ((p[0] - ax) * dx + (p[1] - ay) * dy) / n2
        fx, fy = ax + t * dx, ay + t * dy
        return 2 * fx - p[0], 2 * fy - p[1]

    def _simetria(self, x, a, c, lid):
        """El punto medio de a-c sobre la línea y el segmento a-c perpendicular a ella."""
        pa, pc = self.P(x, a), self.P(x, c)
        (ax, ay), (bx, by) = self.L(x, lid)
        dx, dy = bx - ax, by - ay
        n = math.hypot(dx, dy) or 1e-12
        medio = ((pa[0] + pc[0]) / 2, (pa[1] + pc[1]) / 2)
        return [self.dist_signada(x, medio, lid), ((pc[0] - pa[0]) * dx + (pc[1] - pa[1]) * dy) / n]

    def residuos(self, x):
        salida = []
        for f in self.terminos:
            salida.extend(f(x))
        return np.array(salida, dtype=float)

    def escribir(self, x):
        for pid, (i, j) in self.idx_p.items():
            self.b.puntos[pid].x, self.b.puntos[pid].y = float(x[i]), float(x[j])
        for cid, i in self.idx_r.items():
            c = self.b.curvas[cid]
            if isinstance(c, Circulo):
                c.radio = float(abs(x[i]))
            else:
                c.radio_menor = float(abs(x[i]))


def _jacobiano(sis, x, h=1e-7):
    """Jacobiano de los residuos por diferencias finitas, perturbando a la vez las incógnitas que ningún término
    comparte (columnas de un mismo «color»). Da lo mismo, bit a bit, que perturbar de a una, con muchas menos
    evaluaciones: el polígono de 24 lados pasaba de 95 evaluaciones por jacobiano a unas 5."""
    patron = _patron(sis, x)
    f0 = sis.residuos(x)
    J = np.zeros(patron.shape)
    for cols in _colorear(patron):
        xp = x.copy()
        xp[cols] += h
        J[:, cols] = ((sis.residuos(xp) - f0) / h)[:, None] * patron[:, cols]
    return J


def _patron(sis, x):
    """Matriz booleana (filas de residuos × incógnitas): qué incógnitas lee cada término al evaluarlo en x. Todo
    término lee x solo con `x[i]`, así que basta una evaluación con un lector que anota los índices."""
    leidos = set()

    class _Lector:
        def __getitem__(self, i):
            leidos.add(i)
            return x[i]

        def __len__(self):
            return len(x)

    lector, filas = _Lector(), []
    for f in sis.terminos:
        leidos.clear()
        k = len(f(lector))
        filas += [tuple(leidos)] * k
    patron = np.zeros((len(filas), len(x)), dtype=bool)
    for r, cols in enumerate(filas):
        patron[r, list(cols)] = True
    return patron


def _colorear(patron):
    """Columnas agrupadas sin filas en común (coloreo voraz): cada grupo se perturba en una sola evaluación."""
    colores, filas_de = [], []
    for j in range(patron.shape[1]):
        col = patron[:, j]
        for k, usadas in enumerate(filas_de):
            if not (usadas & col).any():
                colores[k].append(j)
                usadas |= col
                break
        else:
            colores.append([j])
            filas_de.append(col.copy())
    return colores


def _claves(b, eid):
    """Incógnitas posibles de una entidad: ('p', id) por punto y ('r', id) por radio."""
    if eid in b.puntos:
        return [("p", eid)]
    c = b.curvas.get(eid)
    if c is None:
        return []
    salida = [("p", p) for p in c.puntos()]
    if isinstance(c, (Circulo, Elipse, ArcoElipse)):
        salida.append(("r", eid))
    return salida


def _grupos(b):
    """Partes INDEPENDIENTES del boceto: dos incógnitas van juntas si alguna restricción, cota o curva con
    relación propia (arco, arco de elipse) las une. La geometría sin restricciones (un SVG o un texto
    importados) no forma ningún grupo: no entra al solver. Devuelve [{p, r, curvas, restricciones, cotas}]."""
    padre = {}

    def raiz(k):
        padre.setdefault(k, k)
        while padre[k] != k:
            padre[k] = padre[padre[k]]
            k = padre[k]
        return k

    def unir(claves):
        if claves:
            r0 = raiz(claves[0])
            for k in claves[1:]:
                padre[raiz(k)] = r0
            return r0
        return None
    con_terminos = []
    for c in b.curvas.values():
        if isinstance(c, (Arco, ArcoElipse)):
            con_terminos.append(("curvas", c, _claves(b, c.id)))
    for r in b.restricciones.values():
        if r.tipo != "fijo":
            con_terminos.append(("restricciones", r, [k for e in r.entidades for k in _claves(b, e)]))
    for k in b.cotas.values():
        if not k.referencia:
            con_terminos.append(("cotas", k, [q for e in k.entidades for q in _claves(b, e)]))
    for _tipo, _obj, claves in con_terminos:
        unir(claves)
    grupos = {}
    for tipo, obj, claves in con_terminos:
        if not claves:
            continue
        g = grupos.setdefault(raiz(claves[0]), {"p": set(), "r": set(), "curvas": [], "restricciones": [],
                                                "cotas": []})
        g[tipo].append(obj)
        for clase, i in claves:
            g[clase].add(i)
    return list(grupos.values())


def _sueltas(b, grupos, sis_fijos):
    """Incógnitas libres que no están en ningún grupo: (puntos, radios)."""
    en_grupo_p = set().union(*(g["p"] for g in grupos)) if grupos else set()
    en_grupo_r = set().union(*(g["r"] for g in grupos)) if grupos else set()
    fijos_p, fijos_r = sis_fijos
    puntos = {p for p in b.puntos if p not in fijos_p and p not in en_grupo_p}
    radios = {c for c, k in b.curvas.items() if isinstance(k, (Circulo, Elipse, ArcoElipse))
              and c not in fijos_r and c not in en_grupo_r}
    return puntos, radios


def _fijos(b):
    """(puntos fijos, radios fijos): restricción «fijo» y geometría proyectada (no son incógnitas)."""
    fijos_p, fijos_r = set(), set()
    for r in b.restricciones.values():
        if r.tipo == "fijo":
            for e in r.entidades:
                ent = b.entidad(e)
                if ent.tipo == "punto":
                    fijos_p.add(e)
                else:
                    fijos_p.update(ent.puntos())
                    if isinstance(ent, (Circulo, Elipse, ArcoElipse)):
                        fijos_r.add(e)
    for c in b.curvas.values():
        if c.proyectada:
            fijos_p.update(c.puntos())
            fijos_r.add(c.id)
    fijos_p.update(p.id for p in b.puntos.values() if p.proyectado)
    return fijos_p, fijos_r


def resolver(boceto, valores_cotas=None, arrastrado=None, previo=None):
    """Resuelve el boceto en el lugar (modifica coordenadas y radios). Devuelve ResultadoSolver.

    valores_cotas: {id_cota: valor} en mm o grados (ya evaluados desde sus expresiones).
    arrastrado: id de un punto que el usuario está moviendo; se intenta respetar su posición.
    previo: resultado del último `resolver` completo, para un evento de arrastre del ratón: se resuelve solo la
        parte que contiene a `arrastrado` (las otras ya estaban resueltas y no cambian) y se conservan los grados de
        libertad y las entidades determinadas de `previo` (arrastrar no cambia las restricciones). Al soltar, el
        editor vuelve a resolver todo sin `previo`.

    Se resuelve cada parte independiente por separado (`_grupos`): la geometría sin restricciones no entra,
    así un dibujo importado de miles de curvas no arma un sistema gigante (antes, 30 000 incógnitas pedían
    una matriz de 6,7 GB y fallaba).
    """
    valores = valores_cotas or {}
    grupos = _grupos(boceto)
    if previo is not None and arrastrado is not None:
        return _resolver_arrastre(boceto, valores, grupos, arrastrado, previo)
    fijos = _fijos(boceto)
    sueltos_p, sueltos_r = _sueltas(boceto, grupos, fijos)
    libres_p, libres_r = set(sueltos_p), set(sueltos_r)
    gdl, err_max, inconsistente = 2 * len(sueltos_p) + len(sueltos_r), 0.0, False
    for g in grupos:
        sis = _Sistema(boceto, valores, g, fusionar=True)
        x, err, J, rango = _resolver_grupo(sis, arrastrado)
        if x is not None:
            sis.escribir(x)   # también si es inconsistente: queda la mejor aproximación (el editor puede deshacer)
        gdl += len(sis.x0) - rango
        err_max = max(err_max, err)
        inconsistente = inconsistente or err >= TOLERANCIA
        lp, lr = _libres(sis, J, rango)
        libres_p |= lp
        libres_r |= lr
    determinadas = _determinadas(boceto, libres_p, libres_r)
    if inconsistente:
        return ResultadoSolver("inconsistente", gdl, err_max, "Revisá las últimas restricciones o cotas.", determinadas)
    colapsadas = _curvas_colapsadas(boceto) if grupos else ""
    if colapsadas:
        # Ej.: "horizontal" sobre una línea vertical se "cumple" achicándola a largo cero. Fusion lo
        # rechaza como conflicto; acá también.
        return ResultadoSolver("inconsistente", gdl, 0.0,
                               f"Para cumplirse, la geometría colapsa (largo o radio cero): {colapsadas}.")
    return ResultadoSolver("ok", gdl, err_max, determinadas=determinadas)


def restricciones_en_conflicto(boceto, valores_cotas=None):
    """Ids de restricciones/cotas cuya retirada individual deja el boceto consistente.

    Trabaja sobre copias: consultar el diagnóstico no mueve ni modifica el boceto.
    shortcut: prueba una retirada por vínculo, no busca conjuntos mínimos de varios
    conflictos independientes; ampliar si se necesita ese diagnóstico completo.
    """
    if resolver(boceto.copia(), valores_cotas).ok:
        return []
    conflictos = []
    for ident in sorted(set(boceto.restricciones) | {i for i, k in boceto.cotas.items() if not k.referencia}):
        prueba = boceto.copia()
        prueba.eliminar(ident)
        if resolver(prueba, valores_cotas).ok:
            conflictos.append(ident)
    return conflictos


def _resolver_arrastre(boceto, valores, grupos, arrastrado, previo):
    """`resolver` para un evento de arrastre: solo la parte del punto arrastrado y sin el rango ni el núcleo del
    jacobiano (se conservan los de `previo`)."""
    err = 0.0
    for g in grupos:
        if arrastrado in g["p"]:
            sis = _Sistema(boceto, valores, g, fusionar=True)
            x, err, _J, _rango = _resolver_grupo(sis, arrastrado, con_rango=False)
            if x is not None:
                sis.escribir(x)
            break
    if err >= TOLERANCIA:
        return ResultadoSolver("inconsistente", previo.gdl, err, "Revisá las últimas restricciones o cotas.",
                               previo.determinadas)
    return ResultadoSolver("ok", previo.gdl, err, determinadas=previo.determinadas)


def _resolver_grupo(sis, arrastrado, con_rango=True):
    """(x resuelto o None, error máximo, jacobiano, rango) de un grupo. Sin `con_rango`, el jacobiano y el rango
    quedan en None (un evento de arrastre no los usa)."""
    n = len(sis.x0)
    # Una incógnita fusionada vale por `cuenta` coordenadas: misma regularización que si estuvieran separadas.
    base = _PESO_REGULARIZACION * np.sqrt(sis.cuenta)
    pesos, ancla = base.copy(), sis.x0.copy()
    if arrastrado in sis.idx_p:
        ij = list(sis.idx_p[arrastrado])
        pesos[ij] = _PESO_ARRASTRE
        ancla[ij] = sis.b.coords(arrastrado)     # la incógnita arranca donde está el punto arrastrado
    if n == 0 or not sis.terminos:
        r = sis.residuos(sis.x0) if sis.terminos else np.zeros(0)
        err = float(np.max(np.abs(r))) if len(r) else 0.0
        return (ancla if n else None), err, np.zeros((0, n)), 0    # ancla ya cumple lo fusionado: se escribe

    def corrida(x_inicio, ancla, w):
        fun = lambda x: np.concatenate([sis.residuos(x), w * (x - ancla)])  # noqa: E731
        jac = lambda x: np.vstack([_jacobiano(sis, x), np.diag(w)])  # noqa: E731
        from scipy.optimize import least_squares   # perezoso: importarlo cuesta ~0,8 s al arrancar la CLI y el MCP
        # Levenberg-Marquardt (MINPACK, QR): "trf" hacía una SVD por iteración y con los hilos de OpenBLAS cada
        # una costaba ~2,4 ms en matrices de 100×100; con "lm" el arrastre del polígono de 24 lados baja a ~15 ms.
        return least_squares(fun, x_inicio, jac=jac, method="lm", xtol=1e-14, ftol=1e-14, gtol=1e-14,
                             max_nfev=200 * (n + 1)).x

    x = corrida(ancla, ancla, pesos)
    # Pulido: re-anclar en la solución elimina el sesgo de la regularización.
    x = corrida(x, x, base)
    res = sis.residuos(x)
    err = float(np.max(np.abs(res))) if len(res) else 0.0
    if not con_rango:
        return x, err, None, None
    J = _jacobiano(sis, x)
    rango = int(np.linalg.matrix_rank(J, tol=1e-6)) if J.size else 0
    return x, err, J, rango


def _libres(sis, J, rango, tol=1e-6):
    """(puntos, radios) del grupo que siguen libres: una incógnita está determinada si no aparece en el
    núcleo del jacobiano (ningún movimiento que respete las restricciones la cambia)."""
    n = len(sis.x0)
    if n == 0:
        return set(), set()
    if rango >= n:
        libres = np.zeros(n, bool)
    elif J.size:
        _, _, vt = np.linalg.svd(J)
        libres = np.linalg.norm(vt[rango:].T, axis=1) > tol
    else:
        libres = np.ones(n, bool)
    puntos = {pid for pid, (i, j) in sis.idx_p.items() if libres[i] or libres[j]}
    radios = {cid for cid, i in sis.idx_r.items() if libres[i]}
    return puntos, radios


def _determinadas(b, libres_p, libres_r):
    """Entidades que ya no se pueden mover: puntos sin coordenadas libres (los fijos y proyectados lo están
    siempre) y curvas con todos sus puntos determinados y el radio (si tiene) también."""
    puntos = {pid for pid in b.puntos if pid not in libres_p}
    salida = set(puntos)
    for cid, c in b.curvas.items():
        if set(c.puntos()) <= puntos and cid not in libres_r:
            salida.add(cid)
    return salida


def _curvas_colapsadas(boceto, minimo=1e-6):
    salida = []
    for c in boceto.curvas.values():
        if isinstance(c, Linea):
            if math.dist(boceto.coords(c.p1), boceto.coords(c.p2)) < minimo:
                salida.append(f"línea {c.id}")
        elif isinstance(c, (Circulo, Arco)):
            if boceto.radio(c.id) < minimo:
                salida.append(f"{c.tipo} {c.id}")
        elif isinstance(c, (Elipse, ArcoElipse)):
            if c.radio_menor < minimo or math.dist(boceto.coords(c.centro), boceto.coords(c.mayor)) < minimo:
                salida.append(f"elipse {c.id}")
        elif isinstance(c, Spline):
            pts = [boceto.coords(p) for p in c.pts]
            if max(math.dist(pts[0], q) for q in pts[1:]) < minimo:
                salida.append(f"spline {c.id}")
    return ", ".join(salida)


def grados_de_libertad(boceto, valores_cotas=None):
    """GDL sin mover la geometría (para mostrar el estado)."""
    valores = valores_cotas or {}
    grupos = _grupos(boceto)
    sueltos_p, sueltos_r = _sueltas(boceto, grupos, _fijos(boceto))
    gdl = 2 * len(sueltos_p) + len(sueltos_r)
    for g in grupos:
        sis = _Sistema(boceto, valores, g)
        if len(sis.x0) == 0:
            continue
        if not sis.terminos:
            gdl += len(sis.x0)
            continue
        J = _jacobiano(sis, sis.x0)
        gdl += len(sis.x0) - int(np.linalg.matrix_rank(J, tol=1e-6))
    return gdl


# ---------------------------------------------------------------- AutoConstrain
class _GradosAuto:
    """Rango incremental: AutoConstrain agrega términos, pero nunca mueve la geometría.

    Conserva una base ortonormal de las filas del jacobiano. Cada candidato solo necesita su
    jacobiano local y dos proyecciones (Gram-Schmidt con reortogonalización), no otra SVD global.
    """

    def __init__(self, boceto, valores):
        self.b, self.valores = boceto, valores
        self.sis = _Sistema(boceto, valores)
        n = len(self.sis.x0)
        self.base = np.empty((n, n))
        self.rango = 0
        J = _jacobiano(self.sis, self.sis.x0)
        if J.size:
            _, s, vt = np.linalg.svd(J, full_matrices=False)
            self.rango = int(np.count_nonzero(s > 1e-6))
            self.base[:self.rango] = vt[:self.rango]

    def __call__(self, ident=None, tolerancia=None):
        """Grados de libertad tras sumar la restricción o cota `ident`. Con `tolerancia` = (mm, seno del ángulo), una
        restricción que la geometría actual NO cumple (su residuo pasa la tolerancia) no suma filas: dejaría el rango
        contado de más y, al aplicarla, el solver movería la geometría."""
        n = len(self.sis.x0)
        if ident is None:
            return n - self.rango
        b = self.b
        r = b.restricciones.get(ident)
        c = b.cotas.get(ident)
        obj = r if r is not None else c
        claves = {k for e in obj.entidades for k in _claves(b, e)}
        if r is not None and r.tipo == "fijo":
            # Fijar coordenadas equivale a agregar sus filas unidad, sin renumerar el sistema.
            columnas = []
            for clase, eid in claves:
                indice = (self.sis.idx_p if clase == "p" else self.sis.idx_r).get(eid)
                if indice is not None:
                    columnas.extend(indice if clase == "p" else [indice])
            filas = np.zeros((len(columnas), n))
            for i, j in enumerate(columnas):
                filas[i, j] = 1
        else:
            grupo = {"p": {eid for clase, eid in claves if clase == "p"},
                     "r": {eid for clase, eid in claves if clase == "r"}, "curvas": [],
                     "restricciones": [r] if r is not None else [], "cotas": [c] if c is not None else []}
            local = _Sistema(b, self.valores, grupo)
            columnas = []
            for pid in local.idx_p:
                columnas.extend(self.sis.idx_p[pid])
            columnas.extend(self.sis.idx_r[cid] for cid in local.idx_r)
            J = _jacobiano(local, local.x0)
            filas = np.zeros((len(J), n))
            filas[:, columnas] = J
            if tolerancia is not None:
                res = local.residuos(local.x0)
                puntos = [b.coords(eid) for clase, eid in claves if clase == "p"]
                escala = max([float(np.ptp(puntos, axis=0).max()) if len(puntos) > 1 else 0.0,
                              *(b.radio(eid) for clase, eid in claves if clase == "r")])
                if len(res) and np.max(np.abs(res)) > (tolerancia[0] * max(1.0, escala)
                                                       + tolerancia[1] * max(escala, _ESCALA_TANGENTE)):
                    return n - self.rango
        for fila in filas:
            base, previa = self.base[:self.rango], np.linalg.norm(fila)
            for _ in range(2):
                fila -= (base @ fila) @ base
                norma = np.linalg.norm(fila)
                if norma > 0.5 * previa:      # sin cancelación fuerte, una pasada alcanza; si no, se reortogonaliza
                    break
                previa = norma
            if norma > 1e-6:
                self.base[self.rango] = fila / norma
                self.rango += 1
        return n - self.rango


TIPOS_AUTO = ("coincidente", "concentrica", "horizontal", "vertical", "colineal", "paralela", "perpendicular",
              "tangente", "igual", "punto_medio", "simetrica", "cota")
# Familias que AutoConstrain puede inferir, en el orden en que las prueba. «cota» incluye el dato (punto fijo en el
# origen) y las cotas con las medidas actuales.


@dataclass(frozen=True)
class Sugerencia:
    """Una restricción o cota que AutoConstrain agregó (o agregaría). `gdl`: grados de libertad que quedan con ella."""
    clase: str                   # "restriccion" | "cota"
    tipo: str
    entidades: tuple
    valor: float | None
    descripcion: str
    gdl: int

    @property
    def clave(self):
        """Identifica la sugerencia sin su valor: sirve para excluirla (`excluir=`) al regenerar."""
        return self.clase, self.tipo, self.entidades


@dataclass
class ResultadoAuto:
    """Una alternativa de AutoConstrain: lo que agregaría y cómo queda el boceto."""
    nombre: str
    sugerencias: list
    gdl_inicial: int
    gdl: int
    opciones: dict = field(default_factory=dict)      # las de `auto_restringir` que reproducen este resultado

    @property
    def totalmente_restringido(self):
        return self.gdl == 0


def contar_entidades(b):
    """Curvas más puntos sueltos: lo que cuenta el tope de AutoConstrain."""
    en_curvas = {p for c in b.curvas.values() for p in c.puntos()}
    return len(b.curvas) + len(b.puntos.keys() - en_curvas)


def _auto(b, valores_cotas, tol_angulo, tol_distancia, tipos, limite, datum, excluir):
    """Núcleo de AutoConstrain: agrega a `b` lo que cumple y baja los grados de libertad. Devuelve
    (sugerencias, gdl inicial, gdl final)."""
    tipos = set(TIPOS_AUTO if tipos is None else tipos)
    if tipos - set(TIPOS_AUTO):
        raise ErrorBoceto(f"Tipo de restricción desconocido: {', '.join(sorted(tipos - set(TIPOS_AUTO)))}. "
                          f"Los válidos son: {', '.join(TIPOS_AUTO)}.")
    if datum is not None and datum not in b.puntos:
        raise ErrorBoceto(f"El datum {datum} no es un punto del boceto.")
    cantidad = contar_entidades(b)
    if cantidad > TOPE_AUTO_RESTRINGIR:
        raise ErrorBoceto(f"El boceto tiene {cantidad} entidades; el tope para restringir automáticamente es "
                          f"{TOPE_AUTO_RESTRINGIR}. Simplificá o dividí el boceto.")
    excluir = set(excluir)
    valores = dict(valores_cotas or {})
    salida = []
    calcular_gdl = _GradosAuto(b, valores)
    gdl_inicial = gdl = calcular_gdl()
    sen = math.sin(math.radians(tol_angulo))

    def terminado():
        return gdl == 0 or (limite is not None and len(salida) >= limite)

    def probar(tipo, entidades, descripcion, valor=None):
        nonlocal gdl
        clase = "restriccion" if valor is None else "cota"
        if terminado() or ("cota" if clase == "cota" or tipo == "fijo" else tipo) not in tipos:
            return False
        if (clase, tipo, tuple(entidades)) in excluir:
            return False
        try:
            ident = (b.agregar_restriccion(tipo, entidades) if valor is None
                     else b.agregar_cota(tipo, entidades, _numero(valor)))
        except ErrorBoceto:
            return False
        if valor is not None:
            valores[ident] = valor
        # Red de seguridad: una restricción que la geometría no cumple dentro de la tolerancia no entra.
        nuevo = calcular_gdl(ident, (tol_distancia, sen) if valor is None else None)
        if nuevo < gdl:
            gdl = nuevo
            salida.append(Sugerencia(clase, tipo, tuple(entidades), valor, descripcion, gdl))
            return True
        b.eliminar(ident)
        valores.pop(ident, None)
        return False

    for etapa, produce in auto_candidatos.ETAPAS:
        if terminado():
            break
        if tipos.isdisjoint(produce):
            continue
        for tipo, entidades, descripcion in etapa(b, tol_angulo, tol_distancia, tipos):
            probar(tipo, entidades, descripcion)
            if terminado():
                break
    if "cota" in tipos and not terminado():
        _cotas_auto(b, probar, tol_distancia, datum)
    return salida, gdl_inicial, gdl


def _cotas_auto(b, probar, tol_distancia, datum):
    """Dato (punto fijo en el origen) y cotas con las medidas actuales: largos, radios, ángulos y posiciones."""
    lineas = [c for c in b.curvas.values() if isinstance(c, Linea) and not c.proyectada]
    if not b.puntos_fijos() and b.puntos:
        dato = datum if datum is not None else min(b.puntos, key=lambda p: math.hypot(*b.coords(p)))
        if math.hypot(*b.coords(dato)) < tol_distancia:
            probar("fijo", [dato], f"fijo {dato}")
        else:
            origen = b.agregar_punto(0.0, 0.0)
            b.agregar_restriccion("fijo", [origen])
            for tipo in ("distancia_h", "distancia_v"):
                probar(tipo, [origen, dato], f"{tipo} origen-{dato}", round(b.medir_cota(tipo, [origen, dato]), 4))
    for ln in lineas:
        probar("distancia", [ln.id], f"largo {ln.id}", round(math.dist(*b._extremos_linea(ln.id)), 4))
    for c in list(b.curvas.values()):
        if c.tipo in CIRCULARES and not c.proyectada:
            tipo = "diametro" if c.tipo == "circulo" else "radio"
            probar(tipo, [c.id], f"{tipo} {c.id}", round(b.medir_cota(tipo, [c.id]), 4))
    for i, l1 in enumerate(lineas):
        for l2 in lineas[i + 1:]:
            if set(l1.puntos()) & set(l2.puntos()):
                v = round(b.medir_cota("angulo", [l1.id, l2.id]), 4)
                if 1e-3 < v < 180 - 1e-3:
                    probar("angulo", [l1.id, l2.id], f"ángulo {l1.id}-{l2.id}", v)
    fijos = sorted(b.puntos_fijos())
    if fijos:
        referencia = fijos[0]
        if datum is not None and datum != referencia:       # el datum se ubica respecto del dato y ordena el resto
            for tipo in ("distancia_h", "distancia_v"):
                probar(tipo, [referencia, datum], f"{tipo} {referencia}-{datum}",
                       round(b.medir_cota(tipo, [referencia, datum]), 4))
            referencia = datum
        for p in list(b.puntos):
            if p != referencia:
                for tipo in ("distancia_h", "distancia_v"):
                    probar(tipo, [referencia, p], f"{tipo} {referencia}-{p}",
                           round(b.medir_cota(tipo, [referencia, p]), 4))


def auto_restringir(boceto, valores_cotas=None, tol_angulo=1.0, tol_distancia=1e-3, tipos=None, limite=None,
                    datum=None, excluir=()):
    """Restringir automáticamente (SKT-AUTO-CONSTRAIN): detecta lo que el boceto ya cumple (coincidencias,
    concentricidad, horizontales/verticales, colineales, paralelas, perpendiculares, tangencias, igualdades,
    puntos medios y simetrías) y después propone cotas (largos, radios, ángulos y posiciones desde un dato) hasta
    dejarlo totalmente restringido. Cada candidato se agrega solo si baja los grados de libertad sin entrar en
    conflicto. `tipos`: familias a inferir (`TIPOS_AUTO`; todas por defecto); `limite`: tope de agregados;
    `datum`: punto desde el que se miden las posiciones; `excluir`: claves de `Sugerencia` que no se agregan.
    Devuelve las `Sugerencia` agregadas, en orden."""
    return _auto(boceto, valores_cotas, tol_angulo, tol_distancia, tipos, limite, datum, excluir)[0]


def _variantes(b, opciones):
    """(nombre, cambios a las opciones) de las alternativas, en orden: el resultado completo, solo restricciones,
    tolerancias diez veces más estrictas y después una por cada punto elegido como datum."""
    tipos = TIPOS_AUTO if opciones["tipos"] is None else opciones["tipos"]
    yield "Completo", {}
    yield "Solo restricciones", {"tipos": [t for t in tipos if t != "cota"]}
    yield "Estricto", {"tol_angulo": opciones["tol_angulo"] / 10, "tol_distancia": opciones["tol_distancia"] / 10}
    for p in sorted((p for p in b.puntos if not b.puntos[p].proyectado and p != opciones["datum"]),
                    key=lambda p: (math.hypot(*b.coords(p)), p)):
        yield f"Datum en el punto {p}", {"datum": p}


def sugerir_auto_restricciones(boceto, valores_cotas=None, resultados=1, tol_angulo=1.0, tol_distancia=1e-3,
                               tipos=None, limite=None, datum=None, excluir=()):
    """Hasta `resultados` alternativas de AutoConstrain SIN tocar el boceto (se calculan sobre copias): cada una
    es un `ResultadoAuto` con sus sugerencias en orden de prioridad y los grados de libertad tras cada una, así
    cualquier prefijo es una alternativa más suave. Las alternativas que dan lo mismo que una anterior se saltean,
    así que pueden ser menos de las pedidas. Mismas opciones que `auto_restringir`."""
    opciones = {"tol_angulo": tol_angulo, "tol_distancia": tol_distancia, "tipos": tipos, "limite": limite,
                "datum": datum, "excluir": excluir}
    salida, vistos = [], set()
    for intento, (nombre, cambios) in enumerate(_variantes(boceto, opciones)):
        if len(salida) >= resultados or intento >= resultados + MAX_INTENTOS_EXTRA:
            break
        sugerencias, inicial, final = _auto(boceto.copia(), valores_cotas, **{**opciones, **cambios})
        huella = tuple((s.clave, s.valor) for s in sugerencias)
        if huella not in vistos:
            vistos.add(huella)
            salida.append(ResultadoAuto(nombre, sugerencias, inicial, final, {**opciones, **cambios}))
    return salida

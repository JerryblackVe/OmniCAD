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
  - Se minimiza la suma de cuadrados con `scipy.optimize.least_squares` (región de confianza),
    más una regularización muy débil hacia la posición actual: así lo que queda libre
    (sub-restringido) no "salta", se mueve lo mínimo.
  - Grados de libertad restantes = incógnitas − rango del jacobiano de las restricciones.

`auto_restringir` es la versión propia de AutoConstrain (SKT-AUTO-CONSTRAIN).
"""
import math

import numpy as np

from .boceto import (CIRCULARES, ELIPTICAS, Arco, ArcoElipse, Circulo, Elipse, ErrorBoceto, Linea, Spline,
                     _numero, dominio, evaluar_primitiva, mas_cercano, primitivas_entidad, puntos_primitiva)

TOLERANCIA = 1e-6
_PESO_REGULARIZACION = 1e-4
_PESO_ARRASTRE = 1.0
_ESCALA_TANGENTE = 10.0      # mm: convierte el seno del ángulo en un residuo comparable a una distancia
_ESCALA_CURVATURA = 100.0    # mm²


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

    def __init__(self, boceto, valores_cotas):
        self.b = boceto
        self.valores = valores_cotas
        self.fijos_p, self.fijos_r = set(), set()
        for r in boceto.restricciones.values():
            if r.tipo == "fijo":
                for e in r.entidades:
                    ent = boceto.entidad(e)
                    if ent.tipo == "punto":
                        self.fijos_p.add(e)
                    else:
                        self.fijos_p.update(ent.puntos())
                        if isinstance(ent, (Circulo, Elipse, ArcoElipse)):
                            self.fijos_r.add(e)
        for c in boceto.curvas.values():
            if c.proyectada:
                self.fijos_p.update(c.puntos())
                self.fijos_r.add(c.id)
        self.fijos_p.update(p.id for p in boceto.puntos.values() if p.proyectado)
        self.idx_p, self.idx_r, x0 = {}, {}, []
        for pid, p in boceto.puntos.items():
            if pid not in self.fijos_p:
                self.idx_p[pid] = len(x0)
                x0 += [p.x, p.y]
        for cid, c in boceto.curvas.items():
            if isinstance(c, (Circulo, Elipse, ArcoElipse)) and cid not in self.fijos_r:
                self.idx_r[cid] = len(x0)
                x0.append(c.radio if isinstance(c, Circulo) else c.radio_menor)
        self.n_base = len(x0)
        self.x0 = np.array(x0, dtype=float)
        self._extra = []
        self.terminos = []
        self._armar()
        if self._extra:
            self.x0 = np.concatenate([self.x0, np.array(self._extra, dtype=float)])

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
        return x[i], x[i + 1]

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
        for c in b.curvas.values():
            if isinstance(c, Arco):
                T.append(lambda x, c=c: [math.dist(self.P(x, c.inicio), self.P(x, c.centro))
                                         - math.dist(self.P(x, c.fin), self.P(x, c.centro))])
            elif isinstance(c, ArcoElipse):
                T.append(lambda x, c=c: [self.sobre_elipse(x, self.P(x, c.inicio), c.id),
                                         self.sobre_elipse(x, self.P(x, c.fin), c.id)])
        for r in b.restricciones.values():
            t = r.tipo
            e = r.entidades
            tipos = [b.tipo_de(i) for i in e]
            if t == "fijo":
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
                    T.append(lambda x, a=e[0], c=e[1], dx=r.datos.get("dx", 0.0), dy=r.datos.get("dy", 0.0):
                             [self.P(x, c)[0] - self.P(x, a)[0] - dx, self.P(x, c)[1] - self.P(x, a)[1] - dy])
                else:
                    def f(x, a=e[0], c=e[1], o=e[2], ang=r.datos.get("angulo", 0.0)):
                        (px, py), (qx, qy), (ox, oy) = self.P(x, a), self.P(x, c), self.P(x, o)
                        ca, sa = math.cos(ang), math.sin(ang)
                        return [ox + ca * (px - ox) - sa * (py - oy) - qx, oy + sa * (px - ox) + ca * (py - oy) - qy]
                    T.append(f)

        for c in b.cotas.values():
            if c.id not in self.valores:
                continue
            v, e, t = self.valores[c.id], c.entidades, c.tipo
            tipos = [b.tipo_de(i) for i in e]
            if t in ("radio", "diametro"):
                k = 1.0 if t == "radio" else 2.0
                T.append(lambda x, cid=e[0], v=v, k=k: [k * self.R(x, cid) - v])
            elif t == "desfase":
                T.append(lambda x, o=e[0], d=e[1], v=v: [self.separacion(x, o, d) - v])
            elif t == "angulo":
                def f(x, l1=e[0], l2=e[1], v=math.radians(v)):
                    (a, bb), (cc, d) = self.L(x, l1), self.L(x, l2)
                    u = (bb[0] - a[0], bb[1] - a[1])
                    w = (d[0] - cc[0], d[1] - cc[1])
                    return [math.atan2(abs(u[0] * w[1] - u[1] * w[0]), u[0] * w[0] + u[1] * w[1]) - v]
                T.append(f)
            elif t in ("distancia_h", "distancia_v"):
                k = 0 if t == "distancia_h" else 1
                s = c.datos.get("signo", 1.0)
                if tipos == ["linea"]:
                    T.append(lambda x, l=e[0], k=k, s=s, v=v: [s * (self.L(x, l)[1][k] - self.L(x, l)[0][k]) - v])
                else:
                    T.append(lambda x, p1=e[0], p2=e[1], k=k, s=s, v=v: [s * (self.P(x, p2)[k] - self.P(x, p1)[k]) - v])
            elif tipos == ["punto", "punto"]:
                T.append(lambda x, p1=e[0], p2=e[1], v=v: [math.dist(self.P(x, p1), self.P(x, p2)) - v])
            elif tipos == ["linea"]:
                T.append(lambda x, l=e[0], v=v: [math.dist(*self.L(x, l)) - v])
            elif tipos == ["punto", "linea"]:
                s = _signo(self.dist_signada(x0, self.P(x0, e[0]), e[1]))
                T.append(lambda x, p=e[0], l=e[1], s=s, v=v: [s * self.dist_signada(x, self.P(x, p), l) - v])
            elif tipos == ["linea", "linea"]:
                s = _signo(self.dist_signada(x0, self.P(x0, b.curvas[e[1]].p1), e[0]))
                T.append(lambda x, l1=e[0], l2=e[1], s=s, v=v:
                         [s * self.dist_signada(x, self.P(x, b.curvas[l2].p1), l1) - v])

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
        for pid, i in self.idx_p.items():
            self.b.puntos[pid].x, self.b.puntos[pid].y = float(x[i]), float(x[i + 1])
        for cid, i in self.idx_r.items():
            c = self.b.curvas[cid]
            if isinstance(c, Circulo):
                c.radio = float(abs(x[i]))
            else:
                c.radio_menor = float(abs(x[i]))


def _jacobiano(fun, x, h=1e-7):
    f0 = fun(x)
    J = np.zeros((len(f0), len(x)))
    for j in range(len(x)):
        xp = x.copy()
        xp[j] += h
        J[:, j] = (fun(xp) - f0) / h
    return J


def resolver(boceto, valores_cotas=None, arrastrado=None):
    """Resuelve el boceto en el lugar (modifica coordenadas y radios). Devuelve ResultadoSolver.

    valores_cotas: {id_cota: valor} en mm o grados (ya evaluados desde sus expresiones).
    arrastrado: id de un punto que el usuario está moviendo; se intenta respetar su posición.
    """
    sis = _Sistema(boceto, valores_cotas or {})
    n = len(sis.x0)
    if n == 0 or not sis.terminos:
        r = sis.residuos(sis.x0) if sis.terminos else np.zeros(0)
        err = float(np.max(np.abs(r))) if len(r) else 0.0
        return ResultadoSolver("ok" if err < TOLERANCIA else "inconsistente", n, err,
                               determinadas=_entidades_determinadas(sis, np.zeros((0, n)), 0))

    pesos = np.full(n, _PESO_REGULARIZACION)
    if arrastrado in sis.idx_p:
        i = sis.idx_p[arrastrado]
        pesos[i:i + 2] = _PESO_ARRASTRE

    def corrida(x_inicio, ancla, w):
        fun = lambda x: np.concatenate([sis.residuos(x), w * (x - ancla)])  # noqa: E731
        from scipy.optimize import least_squares   # perezoso: importarlo cuesta ~0,8 s al arrancar la CLI y el MCP
        return least_squares(fun, x_inicio, method="trf", xtol=1e-14, ftol=1e-14, gtol=1e-14, max_nfev=200 * (n + 1)).x

    x = corrida(sis.x0, sis.x0, pesos)
    # Pulido: re-anclar en la solución elimina el sesgo de la regularización.
    x = corrida(x, x, np.full(n, _PESO_REGULARIZACION))
    res = sis.residuos(x)
    err = float(np.max(np.abs(res))) if len(res) else 0.0
    J = _jacobiano(sis.residuos, x)
    rango = int(np.linalg.matrix_rank(J, tol=1e-6)) if J.size else 0
    determinadas = _entidades_determinadas(sis, J, rango)
    sis.escribir(x)   # también si es inconsistente: queda la mejor aproximación (el editor puede deshacer)
    if err >= TOLERANCIA:
        return ResultadoSolver("inconsistente", n - rango, err, "Revisá las últimas restricciones o cotas.", determinadas)
    colapsadas = _curvas_colapsadas(boceto)
    if colapsadas:
        # Ej.: "horizontal" sobre una línea vertical se "cumple" achicándola a largo cero. Fusion lo
        # rechaza como conflicto; acá también.
        return ResultadoSolver("inconsistente", n - rango, 0.0,
                               f"Para cumplirse, la geometría colapsa (largo o radio cero): {colapsadas}.")
    return ResultadoSolver("ok", n - rango, err, determinadas=determinadas)


def _entidades_determinadas(sis, J, rango, tol=1e-6):
    """
    Qué entidades quedan sin libertad: una incógnita está determinada si no aparece en el núcleo
    del jacobiano (ningún movimiento que respete las restricciones la cambia). Un punto lo está si
    lo están sus dos coordenadas; una curva, si lo están sus puntos (y el radio, en un círculo).
    """
    n = len(sis.x0)
    if rango >= n:
        libres = np.zeros(n, bool)
    else:
        _, _, vt = np.linalg.svd(J) if J.size else (None, None, np.identity(n))
        nucleo = vt[rango:].T if J.size else np.identity(n)
        libres = np.linalg.norm(nucleo, axis=1) > tol
    puntos = {pid for pid in sis.b.puntos
              if pid not in sis.idx_p or not (libres[sis.idx_p[pid]] or libres[sis.idx_p[pid] + 1])}
    salida = set(puntos)
    for cid, c in sis.b.curvas.items():
        radio_ok = cid not in sis.idx_r or not libres[sis.idx_r[cid]]
        if set(c.puntos()) <= puntos and radio_ok:
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
    sis = _Sistema(boceto, valores_cotas or {})
    if len(sis.x0) == 0:
        return 0
    if not sis.terminos:
        return len(sis.x0)
    J = _jacobiano(sis.residuos, sis.x0)
    return len(sis.x0) - int(np.linalg.matrix_rank(J, tol=1e-6))


# ---------------------------------------------------------------- AutoConstrain
def auto_restringir(boceto, valores_cotas=None, tol_angulo=1.0, tol_distancia=1e-3):
    """Restringir automáticamente (SKT-AUTO-CONSTRAIN): detecta coincidencias, horizontales/verticales
    e igualdades y después propone cotas (largos, radios, ángulos y posiciones respecto del origen)
    hasta dejar el boceto totalmente restringido. Cada candidato se agrega solo si baja los grados de
    libertad sin entrar en conflicto. Devuelve la lista de descripciones de lo agregado."""
    b = boceto
    valores = dict(valores_cotas or {})
    agregado = []
    gdl = [grados_de_libertad(b, valores)]

    def probar(funcion, descripcion, valor=None):
        if gdl[0] == 0:
            return False
        try:
            ident = funcion()
        except ErrorBoceto:
            return False
        if valor is not None:
            valores[ident] = valor
        nuevo = grados_de_libertad(b, valores)
        if nuevo < gdl[0]:
            gdl[0] = nuevo
            agregado.append(descripcion)
            return True
        b.eliminar(ident)
        valores.pop(ident, None)
        return False

    lineas = [c for c in b.curvas.values() if isinstance(c, Linea) and not c.proyectada]
    # 1) Coincidencias: puntos casi en el mismo lugar.
    ids = list(b.puntos)
    for i, p in enumerate(ids):
        for q in ids[i + 1:]:
            if math.dist(b.coords(p), b.coords(q)) < tol_distancia:
                probar(lambda p=p, q=q: b.agregar_restriccion("coincidente", [p, q]), f"coincidente {p}-{q}")
    # 2) Horizontales y verticales.
    for ln in lineas:
        (x1, y1), (x2, y2) = b._extremos_linea(ln.id)
        ang = math.degrees(math.atan2(y2 - y1, x2 - x1)) % 180
        if min(ang, 180 - ang) < tol_angulo:
            probar(lambda k=ln.id: b.agregar_restriccion("horizontal", [k]), f"horizontal {ln.id}")
        elif abs(ang - 90) < tol_angulo:
            probar(lambda k=ln.id: b.agregar_restriccion("vertical", [k]), f"vertical {ln.id}")
    # 3) Igualdades (largos y radios) con el primero de cada grupo.
    def grupos(items, medida):
        vistos = []
        for k in items:
            m = medida(k)
            base = next((g for g in vistos if abs(g[1] - m) < tol_distancia * max(1.0, m)), None)
            if base is None:
                vistos.append((k, m))
            else:
                probar(lambda a=base[0], c=k: b.agregar_restriccion("igual", [a, c]), f"igual {base[0]}-{k}")
    grupos([ln.id for ln in lineas if not ln.construccion], lambda k: math.dist(*b._extremos_linea(k)))
    grupos([c.id for c in b.curvas.values() if c.tipo in CIRCULARES and not c.proyectada], lambda k: b.radio(k))
    # 4) Origen: dato del boceto (como las cotas al origen de Fusion).
    fijos = b.puntos_fijos()
    if not fijos and b.puntos:
        dato = min(b.puntos, key=lambda p: math.hypot(*b.coords(p)))
        if math.hypot(*b.coords(dato)) < tol_distancia:
            probar(lambda: b.agregar_restriccion("fijo", [dato]), f"fijo {dato}")
        else:
            origen = b.agregar_punto(0.0, 0.0)
            b.agregar_restriccion("fijo", [origen])
            for tipo in ("distancia_h", "distancia_v"):
                v = b.medir_cota(tipo, [origen, dato])
                if v > tol_distancia:
                    probar(lambda t=tipo, v=v: b.agregar_cota(t, [origen, dato], _numero(round(v, 4))),
                           f"{tipo} origen-{dato}", round(v, 4))
    # 5) Cotas: largos, radios, ángulos entre líneas unidas y posiciones de lo que siga libre.
    for ln in lineas:
        v = round(math.dist(*b._extremos_linea(ln.id)), 4)
        probar(lambda k=ln.id, v=v: b.agregar_cota("distancia", [k], _numero(v)), f"largo {ln.id}", v)
    for c in list(b.curvas.values()):
        if c.tipo in CIRCULARES and not c.proyectada:
            tipo = "diametro" if c.tipo == "circulo" else "radio"
            v = round(b.medir_cota(tipo, [c.id]), 4)
            probar(lambda k=c.id, t=tipo, v=v: b.agregar_cota(t, [k], _numero(v)), f"{tipo} {c.id}", v)
    for i, l1 in enumerate(lineas):
        for l2 in lineas[i + 1:]:
            if set(l1.puntos()) & set(l2.puntos()):
                v = round(b.medir_cota("angulo", [l1.id, l2.id]), 4)
                if 1e-3 < v < 180 - 1e-3:
                    probar(lambda a=l1.id, c=l2.id, v=v: b.agregar_cota("angulo", [a, c], _numero(v)),
                           f"ángulo {l1.id}-{l2.id}", v)
    fijos = sorted(b.puntos_fijos())
    if fijos:
        dato = fijos[0]
        for p in list(b.puntos):
            if p == dato:
                continue
            for tipo in ("distancia_h", "distancia_v"):
                v = round(b.medir_cota(tipo, [dato, p]), 4)
                if v > tol_distancia:
                    probar(lambda t=tipo, p=p, v=v: b.agregar_cota(t, [dato, p], _numero(v)), f"{tipo} {dato}-{p}", v)
    return agregado

"""Boceto 2D: splines."""
import math

import numpy as np

from .boceto_entidades import ErrorBoceto, Linea, Spline
from .boceto_geometria import (
    dominio, evaluar_primitiva, _funciones_base, _insertar_nudo, mas_cercano, nudos_uniformes, parametros_cuerda,
    _tramo,
)


class _Splines:
    # ------------------------------------------------------------ MODIFICAR: curva de fusión
    def _salida_extremo(self, cid, pid):
        """(punto, dirección unitaria que SALE de la curva por el extremo `pid`)."""
        prim = self.primitivas(cid)[0]
        t0, t1, _ = dominio(prim)
        ini, _fin = self.curvas[cid].extremos()
        C, D = evaluar_primitiva(prim, t0 if pid == ini else t1, 1)
        s = -1.0 if pid == ini else 1.0
        n = math.hypot(*D) or 1.0
        return C, (s * D[0] / n, s * D[1] / n)

    def curva_fusion(self, c1, pick1, c2, pick2, continuidad="G1"):
        """Curva de fusión (SKT-BLEND-CURVE): spline de puntos de control entre los extremos de dos
        curvas, tangente (G1) o con curvatura continua (G2) en ambas uniones."""
        extremos = []
        for cid, pick in ((c1, pick1), (c2, pick2)):
            ext = self.curvas[cid].extremos()
            if not ext:
                raise ErrorBoceto("La fusión une extremos de curvas abiertas.")
            extremos.append(min(ext, key=lambda p, pick=pick: math.dist(self.coords(p), pick)))
        (e1, t1), (e2, t2) = self._salida_extremo(c1, extremos[0]), self._salida_extremo(c2, extremos[1])
        L = math.dist(e1, e2)
        if L < 1e-9:
            raise ErrorBoceto("Los extremos ya se tocan.")
        if continuidad == "G2":
            k = L / 5
            polos_extremos = []
            for cid, pid, e, t in ((c1, extremos[0], e1, t1), (c2, extremos[1], e2, t2)):
                prim = self.primitivas(cid)[0]
                inicio = pid == self.curvas[cid].extremos()[0]
                parametro = dominio(prim)[0 if inicio else 1]
                _, d1, d2 = evaluar_primitiva(prim, parametro, 2)
                signo = -1.0 if inicio else 1.0
                curvatura = signo * (d1[0] * d2[1] - d1[1] * d2[0]) / (math.hypot(*d1) or 1.0) ** 3
                # Seis polos de grado 5: Bézier con curvatura = (4/5) * desplazamiento normal / k².
                normal = 5 / 4 * curvatura * k ** 2
                polos_extremos.append([(e[0] + k * t[0], e[1] + k * t[1]),
                                       (e[0] + 2 * k * t[0] - normal * t[1],
                                        e[1] + 2 * k * t[1] + normal * t[0])])
            internos = polos_extremos[0] + polos_extremos[1][::-1]
            grado, tipo = 5, "curvatura"
        else:
            k = L / 3
            internos = [(e1[0] + k * t1[0], e1[1] + k * t1[1]), (e2[0] + k * t2[0], e2[1] + k * t2[1])]
            grado, tipo = 3, "tangente"
        sid = self.agregar_spline([extremos[0]] + internos + [extremos[1]], "control", grado)
        self.agregar_restriccion(tipo, [c1, sid])
        self.agregar_restriccion(tipo, [c2, sid])
        return sid

    # ------------------------------------------------------------ editar una spline (SKT-CREATE-SPLINES, BOC-11)
    def _spline(self, sid, modo=None):
        c = self.curvas.get(sid)
        if not isinstance(c, Spline):
            raise ErrorBoceto(f"La entidad {sid} no es una spline.")
        if modo and c.modo != modo:
            raise ErrorBoceto("Eso solo se puede en una spline de ajuste." if modo == "ajuste"
                              else "Eso solo se puede en una spline de puntos de control.")
        return c

    def _manija(self, c, pid):
        m = next((m for m in c.manijas if m[0] == pid), None)
        if m is None:
            raise ErrorBoceto(f"El punto {pid} no tiene manija activa.")
        return m

    def activar_manija(self, sid, pid, angulo=None, largo=None, curvatura=None):
        """Activa la manija de tangente (y, con `curvatura`, la de curvatura) en el punto de ajuste `pid`: una
        línea de construcción con la tangente actual de la curva (o `angulo`, grados) y largo `largo` (por defecto
        |C'| / tramos, que no cambia la forma). Devuelve el id de la línea."""
        c = self._spline(sid, "ajuste")
        if c.cerrada:
            raise ErrorBoceto("Las manijas piden una spline abierta: abrila.")
        if pid not in c.pts:
            raise ErrorBoceto(f"{pid} no es punto de ajuste de la spline.")
        if any(m[0] == pid for m in c.manijas):
            raise ErrorBoceto(f"El punto {pid} ya tiene manija: editala.")
        Q = [self.coords(p) for p in c.pts]
        u = parametros_cuerda(Q, c.grado)[c.pts.index(pid)]
        d = evaluar_primitiva(self.primitivas(sid)[0], u, 1)[1]
        a = math.radians(angulo) if angulo is not None else math.atan2(d[1], d[0])
        largo = math.hypot(*d) / (len(Q) - 1) if largo is None else largo       # la derivada de hoy: no cambia la forma
        if not 1e-6 < largo < math.inf:
            raise ErrorBoceto("El largo de la manija tiene que ser positivo.")
        fx, fy = self.coords(pid)
        punta = self.agregar_punto(fx + largo * math.cos(a), fy + largo * math.sin(a))
        c.manijas.append([pid, punta, None if curvatura is None else float(curvatura)])
        return self.agregar_linea(pid, punta, construccion=True)

    def editar_manija(self, sid, pid, angulo=None, largo=None, curvatura=None):
        """Cambia la dirección (grados), el largo o la curvatura (1/mm) de una manija activa."""
        c = self._spline(sid, "ajuste")
        m = self._manija(c, pid)
        (fx, fy), (ex, ey) = self.coords(pid), self.coords(m[1])
        a = math.radians(angulo) if angulo is not None else math.atan2(ey - fy, ex - fx)
        largo = math.hypot(ex - fx, ey - fy) if largo is None else largo
        if not 1e-6 < largo < math.inf:
            raise ErrorBoceto("El largo de la manija tiene que ser positivo.")
        q = self.puntos[m[1]]
        q.x, q.y = fx + largo * math.cos(a), fy + largo * math.sin(a)
        if curvatura is not None:
            m[2] = float(curvatura)

    def desactivar_manija(self, sid, pid):
        """Quita la manija del punto `pid` (su línea y su punta): la tangente vuelve a la natural."""
        c = self._spline(sid, "ajuste")
        m = self._manija(c, pid)
        c.manijas.remove(m)
        for lid in [l.id for l in self.curvas.values() if isinstance(l, Linea) and {l.p1, l.p2} == {m[0], m[1]}]:
            self.eliminar(lid)
        if m[1] in self.puntos and not self._punto_en_uso(m[1]):
            self.eliminar(m[1])

    def cerrar_spline(self, sid, cerrada=True):
        """Abrir / cerrar una spline de ajuste. Al cerrar, si el último punto cae sobre el primero se une con él; al
        abrir, se corta en el primer punto (queda un punto final nuevo encima)."""
        c = self._spline(sid, "ajuste")
        if c.cerrada == bool(cerrada):
            raise ErrorBoceto(f"La spline ya está {'cerrada' if cerrada else 'abierta'}.")
        if cerrada:
            if c.manijas:
                raise ErrorBoceto("Desactivá las manijas antes de cerrar.")
            ultimo = c.pts[-1]
            if len(c.pts) > 3 and math.dist(self.coords(c.pts[0]), self.coords(ultimo)) < 1e-9:
                c.pts.pop()
                self._depurar([ultimo])
            if len(c.pts) < 3:
                raise ErrorBoceto("Spline cerrada: al menos 3 puntos.")
            c.cerrada = True
        else:
            c.pts.append(self.agregar_punto(*self.coords(c.pts[0])))
            c.cerrada = False
        self._depurar()

    def insertar_punto_spline(self, sid, q):
        """Insertar punto de ajuste (en la de ajuste, sobre la curva, cerca de `q`) o punto de control (inserción de
        un nudo: la forma no cambia). Devuelve el id del punto nuevo."""
        c = self._spline(sid)
        prim = self.primitivas(sid)[0]
        t, _d, sobre = mas_cercano(prim, q)
        t0, t1, _ = dominio(prim)
        if not t0 + 1e-9 < t < t1 - 1e-9:
            raise ErrorBoceto("Punto nuevo: debe caer dentro de la spline.")
        if c.modo == "ajuste":
            Q = [self.coords(p) for p in c.pts]
            ub = parametros_cuerda(Q + [Q[0]] if c.cerrada else Q, c.grado)
            i = next(j for j in range(len(ub) - 1) if t <= ub[j + 1])
            if min(t - ub[i], ub[i + 1] - t) < 1e-6:
                raise ErrorBoceto("Ya hay un punto de ajuste ahí.")
            nuevo = self.agregar_punto(*sobre)
            c.pts.insert(i + 1, nuevo)
            return nuevo
        self._polos_propios(c)
        polos, nudos, p, pesos = prim[2], list(prim[3]), prim[4], prim[5]
        w = pesos or [1.0] * len(polos)
        ctrl = [[x * wi, y * wi, wi] for (x, y), wi in zip(polos, w, strict=True)]
        k = _tramo(nudos, p, len(polos) - 1, t)
        ctrl, c.nudos = _insertar_nudo(ctrl, nudos, p, t)
        for j in range(k - p + 1, k):
            self.puntos[c.pts[j]].x, self.puntos[c.pts[j]].y = ctrl[j][0] / ctrl[j][2], ctrl[j][1] / ctrl[j][2]
        nuevo = self.agregar_punto(ctrl[k][0] / ctrl[k][2], ctrl[k][1] / ctrl[k][2])
        c.pts.insert(k, nuevo)
        c.pesos = [h[2] for h in ctrl] if pesos else None
        return nuevo

    def _polos_propios(self, c):
        """Un polo interior que repite un punto de la spline (B-320: polo doble de un .f3d, texto o proyección) pasa
        a tener su propio punto en el mismo lugar (B-352): insertar un nudo o cambiar el grado los separa. Los
        extremos quedan como están (una spline cerrada sigue cerrada)."""
        vistos = {c.pts[0], c.pts[-1]}
        for j in range(1, len(c.pts) - 1):
            if c.pts[j] in vistos:
                c.pts[j] = self.agregar_punto(*self.coords(c.pts[j]))
            vistos.add(c.pts[j])

    def cambiar_grado_spline(self, sid, grado):
        """Change Spline Degree de Fusion (spline de puntos de control, 3 ↔ 5). Subir no cambia la forma (los nudos
        interiores ganan multiplicidad y suman polos); bajar la simplifica (menos polos, nudos uniformes) y conserva
        los extremos. Ajuste por mínimos cuadrados sobre la curva; una spline racional pasa a no racional."""
        c = self._spline(sid, "control")
        if grado not in (3, 5):
            raise ErrorBoceto("Grado de la spline de control: 3 o 5.")
        prim = self.primitivas(sid)[0]
        polos, nudos, p0 = prim[2], prim[3], prim[4]
        if grado == p0:
            raise ErrorBoceto(f"La spline ya es de grado {grado}.")
        t0, t1, _ = dominio(prim)
        if grado > p0:
            interiores = list(nudos[p0 + 1:len(nudos) - p0 - 1])
            nuevos = [t0] * (grado + 1) + sorted(interiores + [u for u in dict.fromkeys(interiores)
                                                                for _ in range(grado - p0)]) + [t1] * (grado + 1)
        else:
            nuevos = [t0 + (t1 - t0) * u for u in nudos_uniformes(max(grado + 1, len(polos) - (p0 - grado)), grado)]
        n = len(nuevos) - grado - 1
        ts = [t0 + (t1 - t0) * i / (20 * n) for i in range(20 * n + 1)]
        A = np.zeros((len(ts), n))
        for fila, t in enumerate(ts):
            k = _tramo(nuevos, grado, n - 1, t)
            A[fila, k - grado:k + 1] = _funciones_base(nuevos, grado, t, k)
        B = np.array([evaluar_primitiva(prim, t)[0] for t in ts])
        ini, fin = np.array(B[0]), np.array(B[-1])
        B = B - np.outer(A[:, 0], ini) - np.outer(A[:, -1], fin)
        medio = np.linalg.lstsq(A[:, 1:-1], B, rcond=None)[0]
        coords = [tuple(ini)] + [tuple(r) for r in medio] + [tuple(fin)]
        self._polos_propios(c)
        viejos = list(c.pts)
        ids = viejos[:min(n, len(viejos)) - 1]
        ids += [self.agregar_punto(0.0, 0.0) for _ in range(n - 1 - len(ids))] + [viejos[-1]]
        for pid, (x, y) in zip(ids, coords, strict=True):
            self.puntos[pid].x, self.puntos[pid].y = float(x), float(y)
        c.pts, c.grado, c.nudos, c.pesos = ids, grado, nuevos, None
        self._depurar([v for v in viejos if v not in ids])

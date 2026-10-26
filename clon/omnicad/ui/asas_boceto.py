# -*- coding: utf-8 -*-
"""Asas de arrastre del editor de boceto (el equivalente de `manipuladores.py` para las herramientas del boceto).

En Fusion, Empalme, Chaflán, los patrones, Escala, Texto y Cónica se ajustan tirando de un asa además de escribir el
valor. Acá la caja de valores (`EntradaValor`) sigue siendo la fuente: cada asa lee los valores de las cajas, se
dibuja donde corresponde y, al arrastrarla, escribe su valor en la caja de su campo (que repinta la vista previa).

Un `Asa2D` sabe dos cosas: dónde está (`posicion(v)`, en mm del boceto, con `v` la lista de valores ya evaluados de las
cajas) y qué valor le toca a la caja si el cursor está en `xy` (`valor(xy, v, v0, xy0)`; `v0` y `xy0` son los valores y
el cursor al empezar el arrastre, para las cantidades, que suben o bajan de a una desde ahí). `por_secante` calcula ese valor para
las asas cuya posición solo se conoce probando la operación (el centro de un empalme).
"""
import math

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QPen

from ..timeline.parametros import ANGULO, ESCALAR, LONGITUD
from . import formato

AZUL = QColor("#289acb")
AZUL_ACTIVO = QColor("#0b6fb0")
RADIO_PX = 6.0
TOL_PX = 10.0
_TIPOS = {"long": LONGITUD, "ang": ANGULO, "esc": ESCALAR, "int": ESCALAR}


class Asa2D:
    """Un asa de la vista: `campo` es el índice de la caja que escribe; `tipo`: "long", "ang", "esc" o "int" (entero).
    `ancla(v)` (opcional) es de dónde sale la línea guía hacia el asa."""

    def __init__(self, campo, posicion, valor, ancla=None, tipo="long", minimo=None, maximo=None, ayuda=""):
        self.campo, self.posicion, self.valor, self.ancla = campo, posicion, valor, ancla
        self.tipo, self.minimo, self.maximo, self.ayuda = tipo, minimo, maximo, ayuda


def por_secante(f, v0, objetivo, paso=None, vueltas=2):
    """Valor `v` tal que el punto `f(v)` (en mm, o None) queda lo más cerca de `objetivo` sobre el camino que recorre
    al variar `v`: se linealiza con una secante y se repite `vueltas` veces (exacto si el camino es recto)."""
    v = v0
    paso = paso if paso else (abs(v0) * 0.1 or 1.0)
    for _ in range(vueltas):
        p0, p1 = f(v), f(v + paso)
        if p0 is None or p1 is None:
            return v
        d = (p1[0] - p0[0], p1[1] - p0[1])
        n2 = d[0] * d[0] + d[1] * d[1]
        if n2 < 1e-18:
            return v
        v += paso * ((objetivo[0] - p0[0]) * d[0] + (objetivo[1] - p0[1]) * d[1]) / n2
    return v


class GestorAsas2D:
    """Une las asas de una herramienta con su caja de valores y con el lienzo del boceto."""

    def __init__(self, lienzo, entrada, asas, tipos, previa=None):
        self.l, self.entrada, self.asas, self.tipos, self.previa = lienzo, entrada, list(asas), list(tipos), previa
        self._ultimo = [0.0] * len(self.tipos)
        self._arrastre = None            # índice del asa que se está tirando
        self._inicio = None              # (valores, xy en mm) al empezar el arrastre: las cantidades parten de ahí
        self._hover = None
        self.valores()                   # fija el último valor válido de cada caja
        for c in entrada.campos:
            c.textChanged.connect(lienzo.update)

    @property
    def arrastrando(self):
        return self._arrastre is not None

    # ------------------------------------------------------------ valores
    def valores(self):
        """Valores numéricos de las cajas; si una está a medio escribir queda el último valor válido."""
        salida = []
        for i, c in enumerate(self.entrada.campos):
            try:
                texto = c.text().strip() or "0"
                self._ultimo[i] = float(self.l.evaluar(texto, _TIPOS[self.tipos[i]]))
            except Exception:  # noqa: BLE001 — una expresión a medias no rompe el dibujo
                pass
            salida.append(self._ultimo[i])
        return salida

    def _posicion(self, asa, v):
        try:
            return asa.posicion(v)
        except Exception:  # noqa: BLE001
            return None

    def posiciones_px(self):
        """[(asa, QPointF en pantalla o None)] con los valores de ahora."""
        v = self.valores()
        salida = []
        for asa in self.asas:
            xy = self._posicion(asa, v)
            salida.append((asa, self.l.a_px(*xy) if xy is not None else None))
        return salida

    # ------------------------------------------------------------ dibujo
    def dibujar(self, p):
        v = self.valores()
        if self.previa is not None:
            try:
                polis = self.previa(v) or []
            except Exception:  # noqa: BLE001 — la vista previa de un valor imposible simplemente no se ve
                polis = []
            p.setPen(QPen(AZUL, 1.8, Qt.DashLine))
            for poli in polis:
                self.l._dibujar_polilinea(p, poli)
        for i, (asa, q) in enumerate(self.posiciones_px()):
            if q is None:
                continue
            activa = i in (self._arrastre, self._hover)
            if asa.ancla is not None:
                try:
                    a = asa.ancla(v)
                except Exception:  # noqa: BLE001
                    a = None
                if a is not None:
                    p.setPen(QPen(AZUL_ACTIVO if activa else AZUL, 1.2, Qt.DashLine))
                    p.drawLine(self.l.a_px(*a), q)
            p.setPen(QPen(AZUL_ACTIVO if activa else AZUL, 2.0))
            p.setBrush(QBrush(AZUL_ACTIVO if activa else QColor(255, 255, 255)))
            p.drawEllipse(q, RADIO_PX, RADIO_PX)
        p.setBrush(Qt.NoBrush)

    # ------------------------------------------------------------ ratón
    def tocar(self, pos):
        """Índice del asa bajo `pos` (QPointF) o None."""
        mejor = None
        for i, (_asa, q) in enumerate(self.posiciones_px()):
            if q is None:
                continue
            d = math.hypot(q.x() - pos.x(), q.y() - pos.y())
            if d <= TOL_PX and (mejor is None or d < mejor[0]):
                mejor = (d, i)
        return None if mejor is None else mejor[1]

    def pasar(self, pos):
        """El cursor pasa por encima (sin botón): resalta el asa y devuelve si hay una."""
        nuevo = self.tocar(pos)
        if nuevo != self._hover:
            self._hover = nuevo
            self.l.setCursor(Qt.PointingHandCursor) if nuevo is not None else self.l.unsetCursor()
            self.l.update()
        return nuevo is not None

    def empezar(self, pos):
        i = self.tocar(pos)
        if i is None:
            return False
        self._arrastre = i
        self._inicio = (self.valores(), self.l.a_mm(pos))
        self.l.update()
        return True

    def mover(self, pos):
        if self._arrastre is None:
            return
        asa, v = self.asas[self._arrastre], self.valores()
        try:
            nuevo = asa.valor(self.l.a_mm(pos), v, *self._inicio)
        except Exception:  # noqa: BLE001
            return
        if nuevo is None or not math.isfinite(nuevo):
            return
        if asa.minimo is not None:
            nuevo = max(asa.minimo, nuevo)
        if asa.maximo is not None:
            nuevo = min(asa.maximo, nuevo)
        caja = self.entrada.campos[asa.campo]
        caja.setText(str(int(round(nuevo))) if asa.tipo == "int" else formato.numero(nuevo, angular=asa.tipo == "ang"))

    def soltar(self):
        if self._arrastre is None:
            return
        caja = self.entrada.campos[self.asas[self._arrastre].campo]
        self._arrastre = None
        caja.setFocus()
        caja.selectAll()
        self.l.update()

    def cerrar(self):
        self._arrastre = self._hover = None
        for c in self.entrada.campos:
            try:
                c.textChanged.disconnect(self.l.update)
            except (RuntimeError, TypeError):
                pass
        self.l.unsetCursor()


# ---------------------------------------------------------------- geometría de las herramientas
def _fuera_de(pt, base, r):
    return (base[0] + r[0] * pt, base[1] + r[1] * pt)


def polilineas_de(l, ids):
    """Polilíneas (mm) de las curvas y puntos elegidos."""
    polis = []
    for i in ids:
        c = l.b.curvas.get(i)
        if c is not None:
            polis += [list(p) for p in l._polilineas(c)]
        elif i in l.b.puntos:
            q = l.b.coords(i)
            polis.append([q, q])
    return polis


def centro_de(l, ids):
    """Centro de la caja que envuelve lo elegido (0, 0 si no hay nada)."""
    pts = [q for poli in polilineas_de(l, ids) for q in poli]
    if not pts:
        return (0.0, 0.0)
    xs, ys = [q[0] for q in pts], [q[1] for q in pts]
    return ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2)


def _aplicar(polis, f):
    return [[f(q) for q in poli] for poli in polis]


def _desfase_px(l, px=16.0):
    return px / max(l.px_por_mm(), 1e-9)


def asas_patron_rectangular(l, ids):
    """(asas, tipos, previa) de las cajas [Cant. X, Dist. X, Cant. Y, Dist. Y]."""
    c = centro_de(l, ids)
    polis = polilineas_de(l, ids)

    def modo():
        return l.opciones["patron_distancia"]

    def extension(n, d):                       # hasta dónde llega la última copia
        return d if modo() == "extension" else d * (n - 1 if n > 1 else 1)

    def paso(n, d):
        return (d / (n - 1) if modo() == "extension" else d) if n > 1 else 0.0

    def eje(i_n, i_d, e):                      # e: 0 = X, 1 = Y
        def ubicar(v, lateral=0.0):
            p = [c[0], c[1]]
            p[e] += extension(int(v[i_n]), v[i_d])
            p[1 - e] += lateral
            return tuple(p)

        def dist(xy, v, v0=None, xy0=None):
            n = int(v[i_n])
            div = 1.0 if modo() == "extension" or n <= 1 else n - 1
            return (xy[e] - c[e]) / div

        def cantidad(xy, v, v0=None, xy0=None):
            n0 = int(v0[i_n])
            return n0 + round((xy[e] - xy0[e]) / (paso(n0, v0[i_d]) or 10.0))
        lateral = lambda: -_desfase_px(l) if e == 0 else _desfase_px(l)  # noqa: E731
        return [Asa2D(i_d, ubicar, dist, ancla=lambda v: c, ayuda="Distancia"),
                Asa2D(i_n, lambda v: ubicar(v, lateral()), cantidad, tipo="int", minimo=1, maximo=500, ayuda="Cantidad")]

    def previa(v):
        params = {"cantidad1": int(v[0]), "distancia1": v[1], "cantidad2": int(v[2]), "distancia2": v[3],
                  "dir1": [1.0, 0.0], "dir2": [0.0, 1.0], "modo": modo(), "simetrico": False, "linea1": None,
                  "linea2": None}
        salida = []
        for fn, *_ in l.b._trans_rectangular(params):
            salida += _aplicar(polis, fn)
        return salida
    return eje(0, 1, 0) + eje(2, 3, 1), ["int", "long", "int", "long"], previa


def _ang(centro, q):
    return math.degrees(math.atan2(q[1] - centro[1], q[0] - centro[0]))


def asas_patron_circular(l, ids, centro):
    """(asas, tipos, previa) de las cajas [Cantidad, ∠ total] alrededor de `centro` (id de punto o xy)."""
    es_punto = isinstance(centro, int) and not isinstance(centro, bool)
    o = l.b.coords(centro) if es_punto else (float(centro[0]), float(centro[1]))
    c = centro_de(l, [i for i in ids if i != centro])
    radio = math.dist(c, o) or 25.0
    a0 = _ang(o, c) if math.dist(c, o) > 1e-9 else 0.0
    polis = polilineas_de(l, [i for i in ids if i != centro])

    def en(grados, r=radio):
        a = math.radians(a0 + grados)
        return (o[0] + r * math.cos(a), o[1] + r * math.sin(a))

    def paso_deg(v):
        n, total = max(int(v[0]), 1), v[1]
        return total / n if abs(abs(total) - 360.0) < 1e-9 else (total / (n - 1) if n > 1 else total)

    def desenvolver(grados, ref):                    # el ángulo del cursor más cercano a `ref` (± vueltas)
        return grados + 360.0 * round((ref - grados) / 360.0)

    def total(xy, v, v0=None, xy0=None):
        t = desenvolver(_ang(o, xy) - a0, v[1])
        return 360.0 if abs(t - 360.0) < 3.0 else (-360.0 if abs(t + 360.0) < 3.0 else t)

    def cantidad(xy, v, v0=None, xy0=None):
        p = paso_deg(v0) or 30.0
        return max(int(v0[0]), 1) + round(desenvolver(_ang(o, xy) - _ang(o, xy0), 0.0) / p)

    asas = [Asa2D(1, lambda v: en(v[1]), total, ancla=lambda v: o, tipo="ang", minimo=-360.0, maximo=360.0,
                  ayuda="Ángulo total"),
            Asa2D(0, lambda v: en(paso_deg(v) * (max(int(v[0]), 1) - 1), radio + _desfase_px(l)), cantidad,
                  tipo="int", minimo=2, maximo=500, ayuda="Cantidad")]

    def previa(v):
        params = {"centro": list(o), "cantidad": max(int(v[0]), 2), "angulo_total": v[1], "simetrico": False}
        salida = []
        for fn, *_ in l.b._trans_circular(params)[0]:
            salida += _aplicar(polis, fn)
        return salida
    return asas, ["int", "ang"], previa


def asas_escala(l, ids, base):
    """(asas, tipos, previa) de la caja [Factor]: el asa sale del punto base hacia lo más lejano de la selección."""
    polis = polilineas_de(l, ids)
    lejos = max((q for poli in polis for q in poli), key=lambda q: math.dist(q, base), default=(base[0] + 10, base[1]))
    r = (lejos[0] - base[0], lejos[1] - base[1])
    if math.hypot(*r) < 1e-9:
        r = (10.0, 0.0)
    r2 = r[0] ** 2 + r[1] ** 2

    def factor(xy, v, v0=None, xy0=None):
        return ((xy[0] - base[0]) * r[0] + (xy[1] - base[1]) * r[1]) / r2

    def previa(v):
        f = max(v[0], 1e-6)
        return _aplicar(polis, lambda q: (base[0] + f * (q[0] - base[0]), base[1] + f * (q[1] - base[1])))
    return ([Asa2D(0, lambda v: _fuera_de(v[0], base, r), factor, ancla=lambda v: base, tipo="esc", minimo=1e-3,
                   ayuda="Factor de escala")], ["esc"], previa)


class _Probador:
    """Aplica una operación del boceto sobre una copia con los valores `v` y devuelve (polilíneas nuevas, [puntos de
    asa]); recuerda el último resultado (el dibujo y las asas piden lo mismo en cada cuadro)."""

    def __init__(self, probar):
        self.probar, self._clave, self._res = probar, None, ([], [])

    def __call__(self, v):
        clave = tuple(round(x, 9) for x in v)
        if clave != self._clave:
            try:
                self._res = self.probar(v)
            except Exception:  # noqa: BLE001 — un valor imposible (radio 0, chaflán que no entra): sin vista previa
                self._res = ([], [])
            self._clave = clave
        return self._res


def _medio(poli):
    """El punto de la polilínea a la mitad de su largo."""
    largos = [math.dist(a, b) for a, b in zip(poli, poli[1:], strict=False)]
    mitad, acumulado = sum(largos) / 2, 0.0
    for (a, b), d in zip(zip(poli, poli[1:], strict=False), largos, strict=False):
        if acumulado + d >= mitad and d > 0:
            t = (mitad - acumulado) / d
            return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
        acumulado += d
    return poli[0]


def _polis_nuevas(copia, antes):
    from ..restricciones.boceto import puntos_primitiva
    return [list(puntos_primitiva(prim, 48)) for k in sorted(set(copia.curvas) - antes) for prim in copia.primitivas(k)]


def asas_empalme(l, picks, xys):
    """(asas, tipos, previa) de la caja [Radio]: el asa está en el medio del arco del empalme."""
    def probar(v):
        copia = l.b.copia()
        antes = set(copia.curvas)
        copia.empalme(picks[0], picks[1], v[0], xys[0], xys[1], repr(v[0]))
        polis = _polis_nuevas(copia, antes)
        return polis, [_medio(max(polis, key=len))]
    pr = _Probador(probar)

    def radio(xy, v, v0=None, xy0=None):
        def f(r):
            res = pr([r])[1]
            return res[0] if res else None
        return por_secante(f, v[0], xy, paso=max(0.5, abs(v[0]) * 0.2))
    return ([Asa2D(0, lambda v: pr(v)[1][0], radio, tipo="long", minimo=1e-3, ayuda="Radio")], ["long"],
            lambda v: pr(v)[0])


def asas_chaflan(l, herramienta, picks, xys):
    """(asas, tipos, previa) de las cajas del chaflán: [Distancia], [Dist. 1, Dist. 2] o [Distancia, ∠]. Cada asa está
    en un extremo del chaflán (el de la primera línea, y el de la segunda); con distancias iguales, en su medio."""
    n = 1 if herramienta == "chaflan" else 2

    def probar(v):
        copia = l.b.copia()
        antes = set(copia.curvas)
        d2 = v[1] if herramienta == "chaflan_dos_dist" else None
        ang = v[1] if herramienta == "chaflan_dist_angulo" else None
        copia.chaflan(picks[0], picks[1], v[0], d2, ang, xys[0], xys[1], repr(v[0]))
        polis = _polis_nuevas(copia, antes)
        linea = polis[0]
        a, b = linea[0], linea[-1]
        if math.dist(a, xys[0]) > math.dist(b, xys[0]):
            a, b = b, a
        return polis, [((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)] if n == 1 else [a, b]
    pr = _Probador(probar)
    tipos = ["long"] if n == 1 else ["long", "ang" if herramienta == "chaflan_dist_angulo" else "long"]

    def asa(i):
        def valor(xy, v, v0=None, xy0=None):
            def f(x):
                w = list(v)
                w[i] = x
                res = pr(w)[1]
                return res[i if n > 1 else 0] if res else None
            paso = 3.0 if tipos[i] == "ang" else max(0.5, abs(v[i]) * 0.2)
            return por_secante(f, v[i], xy, paso=paso)
        return Asa2D(i, lambda v: pr(v)[1][i if n > 1 else 0], valor, tipo=tipos[i], minimo=1e-3 if tipos[i] == "long" else 0.1,
                     maximo=179.0 if tipos[i] == "ang" else None, ayuda="Distancia" if tipos[i] == "long" else "Ángulo")
    return [asa(i) for i in range(n)], tipos, lambda v: pr(v)[0]


def asas_texto(l, ancla, ancho):
    """(asas, tipos, previa) de las cajas [Texto, Altura, ∠, Espaciado, Interlineado]: el asa de giro gira el marco del
    texto alrededor de su esquina `ancla`; `ancho`: el del marco (o 0)."""
    radio = max(ancho, 15.0)

    def posicion(v):
        a = math.radians(v[2])
        return (ancla[0] + radio * math.cos(a), ancla[1] + radio * math.sin(a))

    def angulo(xy, v, v0=None, xy0=None):
        g = math.degrees(math.atan2(xy[1] - ancla[1], xy[0] - ancla[0]))
        return g + 360.0 * round((v[2] - g) / 360.0) if abs(v[2]) > 180.0 else g
    return ([Asa2D(2, posicion, angulo, ancla=lambda v: ancla, tipo="ang", ayuda="Girar el texto")],
            ["long", "long", "ang", "long", "esc"], None)

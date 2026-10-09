# -*- coding: utf-8 -*-
"""
Manipuladores en la vista 3D, como los de Fusion 360.

Mientras un diálogo de comando está abierto, Fusion dibuja sobre el modelo asas que se arrastran con
el ratón y escriben en los campos del diálogo:
  - `Flecha`: flecha azul de distancia (Extruir, Agujero, Empalme, Chaflán, Pulsar/tirar, Vaciado,
    Plano de desfase). Arrastrarla mueve su punta sobre la recta y cambia el valor.
  - `Angulo`: arco con un asa (conicidad de Extruir, ángulo de Revolución, Girar de Mover/copiar).
  - `Triada`: la tríada de Mover/copiar: 3 flechas X/Y/Z (rojo, verde, azul), 3 arcos de giro,
    3 cuadraditos de plano y una esfera central (mover libre en el plano de la vista).
Cada flecha o arco lleva una caja de valor (`CajaValor`, un QLineEdit flotante sobre el visor) que
muestra el valor del campo, sigue al manipulador al mover la cámara y se puede editar (Enter aplica).

Los comandos los declaran con `Comando.manipuladores(ctx, valores)` → lista de manipuladores; el
`GestorManipuladores` (lo crea `PanelComando`) los dibuja con `visor.set_capa`, intercepta el ratón
con un eventFilter instalado en el visor (si el clic cae sobre un asa la toma; si no, el visor sigue
como siempre) y escribe los valores con `panel.set_valor`, así la vista previa se actualiza sola.
Todo el dibujo es en coordenadas del mundo, recalculado para que el tamaño en pantalla sea constante.
"""
import logging
import math

import numpy as np
from PySide6.QtCore import QEvent, QObject, QPointF, Qt, QTimer
from PySide6.QtGui import QPolygonF
from PySide6.QtWidgets import QLineEdit

from ..timeline.parametros import ANGULO, ESCALAR, LONGITUD

log = logging.getLogger(__name__)


def _rgb(hexa):
    hexa = hexa.lstrip("#")
    return tuple(int(hexa[i:i + 2], 16) / 255 for i in (0, 2, 4))


def _aclarar(color, k=0.45):
    return tuple(c + (1 - c) * k for c in color)


AZUL = _rgb("#2b7de9")                 # flecha de Fusion
AZUL_ACTIVO = _aclarar(AZUL)           # al pasar el ratón / arrastrando
COLORES_EJE = (_rgb("#e0302a"), _rgb("#2fa335"), _rgb("#2b6fe0"))   # X rojo, Y verde, Z azul
GRIS_ESFERA = (0.93, 0.93, 0.93)
BORDE_ESFERA = (0.35, 0.35, 0.37)
ROJO_PREVIA = (0.88, 0.18, 0.15)       # vista previa de lo que se corta (agujero)

TOL_PX = 9.0                           # distancia del cursor a un asa para tomarla
LARGO_FLECHA, LARGO_PUNTA, RADIO_PUNTA = 70.0, 18.0, 6.5     # píxeles
LARGO_TRIADA = 120.0
RADIO_ANGULO = 60.0
CAPA, CAPA_PREVIA = "manipuladores", "previa_comando"


# ---------------------------------------------------------------- geometría
def unitario(v):
    v = np.asarray(v, float)
    n = float(np.linalg.norm(v))
    return v / n if n > 1e-12 else v * 0.0


def perpendiculares(d):
    """Dos vectores unitarios perpendiculares a `d` y entre sí."""
    d = unitario(d)
    a = np.array([1.0, 0.0, 0.0]) if abs(d[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
    u = unitario(np.cross(d, a))
    return u, np.cross(d, u)


def mm_por_px(visor, p):
    """Milímetros que mide un píxel de pantalla en el punto `p` (sirve en perspectiva y ortográfica)."""
    p = np.asarray(p, float)
    R = getattr(visor, "R", None)
    paso = max(float(getattr(visor, "distancia", 100.0)) * 0.01, 1e-6)
    if R is not None:
        try:
            s, ok = visor.puntos_pantalla(np.array([p, p + np.asarray(R[0], float) * paso]))
            px = float(np.linalg.norm(s[1] - s[0]))
            if ok.all() and px > 1e-9:
                return paso / px
        except Exception:  # noqa: BLE001 — sin cámara utilizable se usa la escala general
            pass
    try:
        return 1.0 / visor.px_por_mm()
    except Exception:  # noqa: BLE001
        return 0.5


def recta_rayo(o, r, p0, d):
    """Parámetro s del punto de la recta p0 + s·d más cercano al rayo o + t·r (None si son paralelos)."""
    d, r = unitario(d), unitario(r)
    w0 = np.asarray(p0, float) - np.asarray(o, float)
    b = float(d @ r)
    den = 1.0 - b * b
    if den < 1e-6:
        return None
    return (b * float(r @ w0) - float(d @ w0)) / den


def plano_rayo(o, r, p0, n):
    den = float(np.asarray(r, float) @ np.asarray(n, float))
    if abs(den) < 1e-9:
        return None
    t = float((np.asarray(p0, float) - o) @ n) / den
    return None if t < 0 else np.asarray(o, float) + np.asarray(r, float) * t


def _dist_segmentos_px(q, s, ok):
    """Distancia en píxeles de q a la polilínea proyectada s (Nx2), ignorando tramos detrás de la cámara."""
    mejor = math.inf
    for i in range(len(s) - 1):
        if not (ok[i] and ok[i + 1]):
            continue
        a, b = s[i], s[i + 1]
        ab = b - a
        L = float(ab @ ab)
        t = 0.0 if L < 1e-12 else max(0.0, min(1.0, float((q - a) @ ab) / L))
        mejor = min(mejor, float(np.linalg.norm(a + ab * t - q)))
    if len(s) == 1 and ok[0]:
        mejor = float(np.linalg.norm(s[0] - q))
    return mejor


def _segs(poli):
    """Polilínea → segmentos sueltos para ("lineas", …)."""
    poli = np.asarray(poli, float)
    return np.repeat(poli, 2, axis=0)[1:-1] if len(poli) >= 2 else np.zeros((0, 3))


def _cono(base, eje, largo, radio, color, n=20):
    """Punta de flecha: triángulos (se ven si no los tapa el modelo) + generatrices densas en líneas
    (las líneas se dibujan siempre encima: el asa nunca queda escondida dentro del cuerpo)."""
    eje = unitario(eje)
    u, v = perpendiculares(eje)
    punta = base + eje * largo
    angs = np.linspace(0, 2 * math.pi, n + 1)
    anillo = np.array([base + (u * math.cos(a) + v * math.sin(a)) * radio for a in angs])
    tris = []
    for i in range(n):
        tris += [punta, anillo[i], anillo[i + 1], base, anillo[i + 1], anillo[i]]
    lineas = []
    for i in range(n):
        lineas += [punta, anillo[i]]
        for k in (0.33, 0.66):           # rellena la silueta vista de costado
            lineas += [punta, anillo[i] + (anillo[i + 1] - anillo[i]) * k]
    return [("tris", np.array(tris), color, 1.0), ("lineas", np.array(lineas), color, 1.6),
            ("lineas", _segs(anillo), color, 1.6)]


def _disco(visor, centro, radio, color, borde=None):
    """Disco de cara a la cámara relleno con líneas (siempre visible)."""
    R = getattr(visor, "R", np.identity(3))
    u, v = np.asarray(R[0], float), np.asarray(R[1], float)
    lineas = []
    n = 9
    for i in range(-n, n + 1):
        y = radio * i / n
        x = math.sqrt(max(radio * radio - y * y, 0.0))
        lineas += [centro - u * x + v * y, centro + u * x + v * y]
    prims = [("lineas", np.array(lineas), color, 2.0)]
    if borde is not None:
        angs = np.linspace(0, 2 * math.pi, 25)
        prims.append(("lineas", _segs([centro + (u * math.cos(a) + v * math.sin(a)) * radio for a in angs]), borde,
                      1.5))
    return prims


def _arco(centro, u, v, radio, a0, a1, n=None):
    n = n or max(6, int(abs(a1 - a0) / math.radians(4)) + 1)
    return np.array([centro + (u * math.cos(a) + v * math.sin(a)) * radio for a in np.linspace(a0, a1, n + 1)])


def _desenvolver(angulo, previo):
    """Ángulo equivalente (±2πk) más cercano al anterior: arrastrar más de media vuelta no salta."""
    return angulo + 2 * math.pi * round((previo - angulo) / (2 * math.pi))


# ---------------------------------------------------------------- manipuladores
class Manipulador:
    """Base. `ident` identifica al manipulador entre recálculos (hover, arrastre, cajas)."""
    ident = ""

    def dibujar(self, g, activo):
        """Primitivas para `visor.set_capa`. `activo`: sub-asa resaltada (o None)."""
        return []

    def tocar(self, g, q):
        """(distancia en píxeles del cursor q al asa más cercana, sub-asa)."""
        return math.inf, None

    def empezar(self, g, pos, sub):
        """Estado del arrastre (dict) o None si no se puede arrastrar desde ahí."""
        return None

    def mover(self, g, estado, pos):
        """Nuevos valores numéricos {clave: valor} para la posición del cursor."""
        return {}

    def cajas(self, g, arrastre):
        """[(clave, punto 3D)] de las cajas de valor a mostrar."""
        return []


class Flecha(Manipulador):
    """Flecha de distancia: su cola está en `origen + direccion·valor·factor` y apunta hacia afuera
    (si el valor es negativo, hacia el otro lado). Arrastrarla corre el valor lo mismo que el cursor
    sobre la recta (dividido por `factor`, p. ej. 0,5 en la extrusión simétrica de longitud total)."""

    def __init__(self, clave, origen, direccion, factor=1.0, minimo=None, maximo=None, caja=True, color=AZUL):
        self.clave, self.origen, self.direccion = clave, np.asarray(origen, float), unitario(direccion)
        self.factor, self.minimo, self.maximo, self.caja, self.color = factor, minimo, maximo, caja, color
        self.ident = f"flecha:{clave}"

    def _geom(self, g):
        v = g.valor(self.clave) * self.factor
        base = self.origen + self.direccion * v
        sentido = self.direccion * (-1.0 if v < 0 else 1.0)
        k = g.escala(base)
        return base, sentido, k

    def puntos(self, g):
        base, sentido, k = self._geom(g)
        return base, base + sentido * LARGO_FLECHA * k

    def dibujar(self, g, activo):
        base, sentido, k = self._geom(g)
        color = AZUL_ACTIVO if activo is not None else self.color
        cuello = base + sentido * (LARGO_FLECHA - LARGO_PUNTA) * k
        return [("lineas", np.array([base, cuello]), color, 3.0)] + _cono(
            cuello, sentido, LARGO_PUNTA * k, RADIO_PUNTA * k, color)

    def tocar(self, g, q):
        a, b = self.puntos(g)
        s, ok = g.pantalla([a, b])
        return _dist_segmentos_px(q, s, ok), "flecha"

    def empezar(self, g, pos, sub):
        o, r = g.rayo(pos)
        s0 = recta_rayo(o, r, self.origen, self.direccion)
        if s0 is None:
            return None
        return {"s0": s0, "v0": g.valor(self.clave), "origen": self.origen, "dir": self.direccion}

    def mover(self, g, estado, pos):
        o, r = g.rayo(pos)
        s = recta_rayo(o, r, estado["origen"], estado["dir"])
        if s is None or abs(self.factor) < 1e-12:
            return {}
        v = estado["v0"] + (s - estado["s0"]) / self.factor
        if self.minimo is not None:
            v = max(self.minimo, v)
        if self.maximo is not None:
            v = min(self.maximo, v)
        return {self.clave: v}

    def cajas(self, g, arrastre):
        if self.caja is True or (self.caja == "arrastre" and arrastre is not None):
            return [(self.clave, self.puntos(g)[1])]
        return []


class Angulo(Manipulador):
    """Arco con asa: gira alrededor de `eje` (regla de la mano derecha) desde la dirección `inicio`.
    El asa está a `valor·factor` grados. `radio` en mm (p. ej. el radio del perfil que gira) o None
    para un radio constante en pantalla."""

    def __init__(self, clave, centro, eje, inicio, radio=None, factor=1.0, minimo=-360.0, maximo=360.0,
                 caja=True, color=AZUL):
        self.clave, self.centro, self.eje = clave, np.asarray(centro, float), unitario(eje)
        ini = np.asarray(inicio, float)
        ini = ini - self.eje * float(ini @ self.eje)
        self.u = unitario(ini) if np.linalg.norm(ini) > 1e-9 else perpendiculares(self.eje)[0]
        self.v = np.cross(self.eje, self.u)
        self.radio, self.factor, self.minimo, self.maximo = radio, factor, minimo, maximo
        self.caja, self.color = caja, color
        self.ident = f"angulo:{clave}"

    def _r(self, g):
        if self.radio and self.radio > 1e-6:
            return float(self.radio)
        return RADIO_ANGULO * g.escala(self.centro)

    def _theta(self, g):
        return math.radians(g.valor(self.clave) * self.factor)

    def asa(self, g):
        t = self._theta(g)
        return self.centro + (self.u * math.cos(t) + self.v * math.sin(t)) * self._r(g)

    def dibujar(self, g, activo):
        color = AZUL_ACTIVO if activo is not None else self.color
        r, t = self._r(g), self._theta(g)
        asa = self.asa(g)
        k = g.escala(asa)
        prims = [("lineas", np.array([self.centro, self.centro + self.u * r, self.centro, asa]), color, 1.2)]
        if abs(t) > 1e-6:
            prims.append(("lineas", _segs(_arco(self.centro, self.u, self.v, r, 0.0, t)), color, 2.5))
        tangente = (-self.u * math.sin(t) + self.v * math.cos(t)) * (1.0 if t >= 0 else -1.0)
        prims += _cono(asa, tangente, LARGO_PUNTA * 0.8 * k, RADIO_PUNTA * k, color)
        prims += _disco(g.visor, asa, 4.5 * k, color)
        return prims

    def tocar(self, g, q):
        s, ok = g.pantalla([self.asa(g)])
        d = float(np.linalg.norm(s[0] - q)) - TOL_PX * 0.6 if ok[0] else math.inf
        t = self._theta(g)
        if abs(t) > 1e-6:
            sa, oka = g.pantalla(_arco(self.centro, self.u, self.v, self._r(g), 0.0, t, 24))
            d = min(d, _dist_segmentos_px(q, sa, oka))
        return d, "asa"

    def _angulo_en(self, g, pos, previo):
        o, r = g.rayo(pos)
        if abs(float(unitario(r) @ self.eje)) < 0.08:      # el plano del arco se ve de canto
            return None
        p = plano_rayo(o, r, self.centro, self.eje)
        if p is None:
            return None
        w = p - self.centro
        a = math.atan2(float(w @ self.v), float(w @ self.u))
        return _desenvolver(a, previo)

    def empezar(self, g, pos, sub):
        t0 = self._theta(g)
        a0 = self._angulo_en(g, pos, t0)
        if a0 is None:
            return None
        return {"a0": a0, "ultimo": a0, "v0": g.valor(self.clave)}

    def mover(self, g, estado, pos):
        a = self._angulo_en(g, pos, estado["ultimo"])
        if a is None or abs(self.factor) < 1e-12:
            return {}
        estado["ultimo"] = a
        v = estado["v0"] + math.degrees(a - estado["a0"]) / self.factor
        return {self.clave: max(self.minimo, min(self.maximo, v))}

    def cajas(self, g, arrastre):
        if self.caja is True or (self.caja == "arrastre" and arrastre is not None):
            return [(self.clave, self.asa(g))]
        return []


class Triada(Manipulador):
    """Tríada de Mover/copiar en `centro`, alineada con los ejes del diseño. `claves`: campos de
    traslación X/Y/Z; `giros`: campos de giro alrededor de X/Y/Z (None = sin arcos)."""
    ident = "triada"

    def __init__(self, centro, claves=("dx", "dy", "dz"), giros=("rx", "ry", "rz"), planos=True, esfera=True):
        self.centro, self.claves, self.giros = np.asarray(centro, float), tuple(claves), giros
        self.planos, self.esfera = planos, esfera

    @staticmethod
    def _base(i):
        e = np.identity(3)
        return e[i], e[(i + 1) % 3], e[(i + 2) % 3]

    def _partes(self, g):
        """[(sub, polilínea 3D para tocar)] de cada asa."""
        k = g.escala(self.centro)
        L, c = LARGO_TRIADA * k, self.centro
        partes = []
        for i in range(3):
            e = np.identity(3)[i]
            partes.append((("eje", i), np.array([c + e * L * 0.2, c + e * L])))
        if self.giros:
            for i in range(3):
                _, a, b = self._base(i)
                partes.append((("giro", i), _arco(c, a, b, L * 0.7, math.radians(15), math.radians(75), 14)))
        if self.planos:
            for i in range(3):
                _, a, b = self._base(i)
                lo, hi = L * 0.24, L * 0.40
                partes.append((("plano", i), np.array([c + a * lo + b * lo, c + a * hi + b * lo, c + a * hi + b * hi,
                                                       c + a * lo + b * hi, c + a * lo + b * lo])))
        return partes, k

    def dibujar(self, g, activo):
        partes, k = self._partes(g)
        c, L = self.centro, LARGO_TRIADA * k
        prims = []
        for sub, poli in partes:
            tipo, i = sub
            color = COLORES_EJE[i]
            if activo == sub:
                color = _aclarar(color, 0.5)
            if tipo == "eje":
                e = np.identity(3)[i]
                cuello = c + e * (L - LARGO_PUNTA * k)
                prims.append(("lineas", np.array([poli[0], cuello]), color, 3.0))
                prims += _cono(cuello, e, LARGO_PUNTA * k, RADIO_PUNTA * k, color)
            elif tipo == "giro":
                prims.append(("lineas", _segs(poli), color, 3.5))
                prims += _disco(g.visor, poli[len(poli) // 2], 4.0 * k, color)
            else:
                _, a, b = self._base(i)
                lineas = []
                for t in np.linspace(0, 1, 9):          # relleno con líneas: siempre visible
                    p0 = poli[0] + (poli[3] - poli[0]) * t
                    lineas += [p0, p0 + (poli[1] - poli[0])]
                prims.append(("tris", np.array([poli[0], poli[1], poli[2], poli[0], poli[2], poli[3]]), color, 0.55))
                prims.append(("lineas", np.array(lineas), _aclarar(color, 0.35), 2.0))
                prims.append(("lineas", _segs(poli), color, 1.5))
        if self.esfera:
            color = _aclarar(GRIS_ESFERA, 0.5) if activo == ("esfera", 0) else GRIS_ESFERA
            prims += _disco(g.visor, c, 7.0 * k, color, BORDE_ESFERA)
        return prims

    def tocar(self, g, q):
        partes, k = self._partes(g)
        mejor = (math.inf, None)
        for sub, poli in partes:
            s, ok = g.pantalla(poli)
            if sub[0] == "plano":                       # dentro del cuadradito también vale
                if ok.all():
                    xs, ys = s[:4, 0], s[:4, 1]
                    if QPolygonF([QPointF(float(x), float(y)) for x, y in zip(xs, ys, strict=True)]).containsPoint(
                            QPointF(float(q[0]), float(q[1])), Qt.OddEvenFill):
                        d = 0.0
                    else:
                        d = _dist_segmentos_px(q, s, ok)
                else:
                    d = math.inf
            else:
                d = _dist_segmentos_px(q, s, ok)
            if d < mejor[0]:
                mejor = (d, sub)
        if self.esfera:
            s, ok = g.pantalla([self.centro])
            if ok[0]:
                d = float(np.linalg.norm(s[0] - q)) - 7.0
                if d < mejor[0] or d <= 0:
                    mejor = (max(d, 0.0), ("esfera", 0))
        return mejor

    def _valores(self, g, claves):
        return np.array([g.valor(k) for k in claves], float)

    def empezar(self, g, pos, sub):
        o, r = g.rayo(pos)
        c = self.centro.copy()
        tipo, i = sub
        if tipo == "eje":
            s0 = recta_rayo(o, r, c, np.identity(3)[i])
            return None if s0 is None else {"sub": sub, "c": c, "s0": s0, "v0": g.valor(self.claves[i])}
        if tipo == "giro":
            _, a, b = self._base(i)
            p = plano_rayo(o, r, c, np.identity(3)[i])
            if p is None or abs(float(unitario(r)[i])) < 0.08:
                return None
            w = p - c
            ang = math.atan2(float(w @ b), float(w @ a))
            return {"sub": sub, "c": c, "a0": ang, "ultimo": ang, "v0": g.valor(self.giros[i])}
        n = np.identity(3)[i] if tipo == "plano" else np.asarray(g.visor.R[2], float)
        p0 = plano_rayo(o, r, c, n)
        if p0 is None:
            return None
        return {"sub": sub, "c": c, "n": n, "p0": p0, "v0": self._valores(g, self.claves)}

    def mover(self, g, estado, pos):
        o, r = g.rayo(pos)
        tipo, i = estado["sub"]
        c = estado["c"]
        if tipo == "eje":
            s = recta_rayo(o, r, c, np.identity(3)[i])
            return {} if s is None else {self.claves[i]: estado["v0"] + s - estado["s0"]}
        if tipo == "giro":
            _, a, b = self._base(i)
            p = plano_rayo(o, r, c, np.identity(3)[i])
            if p is None:
                return {}
            w = p - c
            ang = _desenvolver(math.atan2(float(w @ b), float(w @ a)), estado["ultimo"])
            estado["ultimo"] = ang
            return {self.giros[i]: estado["v0"] + math.degrees(ang - estado["a0"])}
        p = plano_rayo(o, r, c, estado["n"])
        if p is None:
            return {}
        delta = p - estado["p0"]
        if tipo == "plano":
            delta[i] = 0.0
        nuevos = estado["v0"] + delta
        return {k: float(v) for k, v in zip(self.claves, nuevos, strict=True)}

    def cajas(self, g, arrastre):
        if arrastre is None:
            return []
        tipo, i = arrastre
        k = g.escala(self.centro)
        if tipo == "eje":
            return [(self.claves[i], self.centro + np.identity(3)[i] * LARGO_TRIADA * k)]
        if tipo == "giro" and self.giros:
            _, a, b = self._base(i)
            return [(self.giros[i], self.centro + (a + b) * LARGO_TRIADA * k * 0.7 / math.sqrt(2))]
        return []


# ---------------------------------------------------------------- caja de valor
QSS_CAJA = f"""
QLineEdit#caja_manipulador {{ background: #ffffff; color: #1d1d1d; border: 1px solid #a8a8a8;
                              padding: 1px 4px; selection-background-color: #2b7de9; }}
QLineEdit#caja_manipulador:focus {{ border: 1px solid #{''.join(f'{int(c * 255):02x}' for c in AZUL)}; }}
"""


class CajaValor(QLineEdit):
    """Caja de valor flotante junto al manipulador (hija del visor). Enter aplica, Esc vuelve."""

    def __init__(self, gestor, clave):
        super().__init__(gestor.visor)
        self.gestor, self.clave = gestor, clave
        self.setObjectName("caja_manipulador")
        self.setStyleSheet(QSS_CAJA)
        self.setFixedWidth(96)
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.punto = None

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.gestor.aplicar_caja(self)
            e.accept()
            return
        if e.key() == Qt.Key_Escape:
            self.setText(str(self.gestor.panel.valores.get(self.clave, "")))
            self.gestor.visor.setFocus()
            e.accept()
            return
        super().keyPressEvent(e)

    def focusOutEvent(self, e):
        super().focusOutEvent(e)
        self.gestor.sincronizar_cajas()


# ---------------------------------------------------------------- gestor
class GestorManipuladores(QObject):
    """Une los manipuladores de un comando con el visor y el panel (ver el docstring del módulo)."""

    def __init__(self, panel):
        super().__init__(panel)
        self.panel, self.visor, self.ctx, self.comando = panel, panel.visor, panel.ctx, panel.comando
        self.manips = []
        self.cajas = {}                 # clave → CajaValor
        self._hover = None              # (ident, sub)
        self._arrastre = None           # {"m", "sub", "estado"}
        self._escribiendo = False
        self._sincronizando = False
        self._cerrado = False
        self._firma = None
        self._redibujo_pendiente = False
        self._decimales = 2
        self._cursor = None
        self.visor.installEventFilter(self)
        self.visor.camara_cambiada.connect(self._camara)

    # ------------------------------------------------------------ datos para los manipuladores
    def campo(self, clave):
        return next((c for c in self.panel.campos if c.clave == clave), None)

    def tipo(self, clave):
        return getattr(self.campo(clave), "tipo", LONGITUD)

    def valor(self, clave):
        """Valor numérico actual del campo (mm o grados); 0 si la expresión no se puede evaluar."""
        try:
            return float(self.ctx.evaluar(str(self.panel.valores.get(clave, "0")), self.tipo(clave)))
        except Exception:  # noqa: BLE001 — una expresión inválida no rompe el dibujo
            return 0.0

    def escala(self, p):
        return mm_por_px(self.visor, p)

    def pantalla(self, puntos):
        s, ok = self.visor.puntos_pantalla(np.asarray(puntos, float).reshape(-1, 3))
        return np.asarray(s, float), np.asarray(ok, bool)

    def rayo(self, pos):
        o, r = self.visor.rayo(pos)
        return np.asarray(o, float), np.asarray(r, float)

    @property
    def arrastrando(self):
        return self._arrastre is not None

    # ------------------------------------------------------------ ciclo de vida
    def actualizar(self):
        """Recalcula los manipuladores con los valores del panel (la selección cambia su origen)."""
        if self._cerrado or self._escribiendo:
            return
        try:
            self.manips = [m for m in (self.comando.manipuladores(self.ctx, self.panel.valores) or []) if m is not None]
        except Exception:  # noqa: BLE001 — un manipulador que no se puede calcular no rompe el comando
            log.debug("manipuladores de %s", self.comando.CLAVE, exc_info=True)
            self.manips = []
        if self._hover is not None and not any(m.ident == self._hover[0] for m in self.manips):
            self._hover = None
        self.redibujar()

    def redibujar(self):
        if self._cerrado:
            return
        prims = []
        for m in self.manips:
            activo = None
            if self._arrastre is not None and self._arrastre["m"].ident == m.ident:
                activo = self._arrastre["sub"]
            elif self._hover is not None and self._hover[0] == m.ident:
                activo = self._hover[1]
            try:
                prims += m.dibujar(self, activo)
            except Exception:  # noqa: BLE001
                log.debug("dibujo de manipulador", exc_info=True)
        self._firma = self._firma_camara()
        self.visor.set_capa(CAPA, prims or None)
        self.sincronizar_cajas()

    def mostrar_previa(self, prims):
        """Dibujo extra de la vista previa del comando (p. ej. el agujero en rojo); None lo borra."""
        if not self._cerrado:
            self.visor.set_capa(CAPA_PREVIA, prims or None)

    def cerrar(self):
        if self._cerrado:
            return
        self._cerrado = True
        self._arrastre = self._hover = None
        try:
            self.visor.removeEventFilter(self)
            self.visor.camara_cambiada.disconnect(self._camara)
        except (RuntimeError, TypeError):
            pass
        self._restaurar_cursor()
        self.visor.set_capa(CAPA, None)
        self.visor.set_capa(CAPA_PREVIA, None)
        for caja in self.cajas.values():
            self._quitar_caja(caja)
        self.cajas = {}
        self.manips = []

    @staticmethod
    def _quitar_caja(caja):
        caja.hide()
        caja.setParent(None)                 # deja de ser hija del visor ya mismo (no espera al bucle de eventos)
        caja.deleteLater()

    # ------------------------------------------------------------ cámara
    def _firma_camara(self):
        v = self.visor
        try:
            return (tuple(np.round(np.asarray(v.objetivo, float), 5)), round(float(v.distancia), 5),
                    tuple(np.round(np.asarray(v.R, float).ravel(), 6)), v.width(), v.height(), bool(v.ortografica))
        except Exception:  # noqa: BLE001
            return None

    def _camara(self):
        """La cámara cambió (se emite en cada cuadro): el tamaño en pantalla tiene que seguir constante
        y las cajas siguen a sus manipuladores. Solo se redibuja si la cámara se movió de verdad."""
        if self._cerrado:
            return
        if self._firma_camara() != self._firma and not self._redibujo_pendiente:
            self._redibujo_pendiente = True
            QTimer.singleShot(0, self._redibujar_por_camara)
        else:
            self._ubicar_cajas()

    def _redibujar_por_camara(self):
        self._redibujo_pendiente = False
        self.redibujar()

    # ------------------------------------------------------------ cajas de valor
    def sincronizar_cajas(self):
        if self._cerrado or self._sincronizando:
            return
        self._sincronizando = True
        try:
            self._sincronizar_cajas()
        finally:
            self._sincronizando = False

    def _sincronizar_cajas(self):
        sub = self._arrastre["sub"] if self._arrastre is not None else None
        pedidas = {}
        for m in self.manips:
            arr = sub if self._arrastre is not None and self._arrastre["m"].ident == m.ident else None
            try:
                for clave, punto in m.cajas(self, arr):
                    pedidas[clave] = punto
            except Exception:  # noqa: BLE001
                log.debug("cajas de manipulador", exc_info=True)
        for clave in [c for c in self.cajas if c not in pedidas]:
            self._quitar_caja(self.cajas.pop(clave))
        for clave, punto in pedidas.items():
            caja = self.cajas.get(clave)
            if caja is None:
                caja = self.cajas[clave] = CajaValor(self, clave)
            caja.punto = np.asarray(punto, float)
            if not caja.hasFocus():
                texto = str(self.panel.valores.get(clave, ""))
                if caja.text() != texto:
                    caja.setText(texto)
                    caja.setCursorPosition(0)
                caja.setStyleSheet(QSS_CAJA)
        self._ubicar_cajas()

    def _ubicar_cajas(self):
        for caja in self.cajas.values():
            if caja.punto is None:
                continue
            s, ok = self.pantalla([caja.punto])
            x, y = float(s[0][0]) + 14, float(s[0][1]) - caja.sizeHint().height() - 6
            w, h = self.visor.width(), self.visor.height()
            if not ok[0] or not (-40 <= s[0][0] <= w + 40 and -40 <= s[0][1] <= h + 40):
                caja.hide()
                continue
            caja.resize(caja.width(), caja.sizeHint().height())
            caja.move(int(max(2, min(w - caja.width() - 2, x))), int(max(2, min(h - caja.height() - 2, y))))
            if not caja.isVisible():
                caja.show()
            caja.raise_()

    def aplicar_caja(self, caja):
        texto = caja.text().strip()
        try:
            self.ctx.evaluar(texto, self.tipo(caja.clave))
        except Exception as e:  # noqa: BLE001 — se marca la caja en rojo, como el panel
            caja.setStyleSheet(QSS_CAJA + "QLineEdit#caja_manipulador { background: #ffd9d9; }")
            caja.setToolTip(str(e))
            return False
        caja.setToolTip("")
        self.panel.set_valor(caja.clave, texto)
        caja.selectAll()
        return True

    # ------------------------------------------------------------ ratón
    def _tocado(self, pos):
        q = np.array([pos.x(), pos.y()], float)
        mejor = (TOL_PX, None, None)
        for m in self.manips:
            try:
                d, sub = m.tocar(self, q)
            except Exception:  # noqa: BLE001
                continue
            if d < mejor[0]:
                mejor = (d, m, sub)
        return (mejor[1], mejor[2]) if mejor[1] is not None else None

    def _decimales_en(self, punto):
        mm = self.escala(punto)
        return int(max(0, min(3, -math.floor(math.log10(max(mm, 1e-6))) + 1)))

    def texto(self, clave, valor):
        """Valor redondeado como lo escribe Fusion en el campo: "30.33 mm", "15.5 deg"."""
        tipo = self.tipo(clave)
        dec, unidad = (1, "deg") if tipo == ANGULO else ((3, "") if tipo == ESCALAR else (self._decimales, "mm"))
        s = f"{valor:.{dec}f}"
        if "." in s:
            s = s.rstrip("0").rstrip(".")
        if s in ("-0", ""):
            s = "0"
        return f"{s} {unidad}".strip()

    def empezar_arrastre(self, pos):
        """Si `pos` (píxeles del visor) cae sobre un asa, empieza a arrastrarla. Devuelve True si la tomó."""
        if self._cerrado or getattr(self.visor, "modo", None) is not None:
            return False
        tocado = self._tocado(pos)
        if tocado is None:
            return False
        m, sub = tocado
        estado = m.empezar(self, pos, sub)
        if estado is None:
            return False
        o, r = self.rayo(pos)
        self._decimales = self._decimales_en(o + r * float(getattr(self.visor, "distancia", 100.0)))
        self._arrastre = {"m": m, "sub": sub, "estado": estado}
        self.redibujar()
        return True

    def arrastrar(self, pos):
        if self._arrastre is None:
            return
        a = self._arrastre
        try:
            nuevos = a["m"].mover(self, a["estado"], pos)
        except Exception:  # noqa: BLE001
            log.debug("arrastre de manipulador", exc_info=True)
            return
        self.escribir(nuevos)

    def soltar(self):
        if self._arrastre is None:
            return
        self._arrastre = None
        self.redibujar()

    def escribir(self, nuevos):
        """Escribe valores numéricos redondeados en los campos del panel (dispara la vista previa)."""
        cambio = False
        self._escribiendo = True
        try:
            for clave, v in nuevos.items():
                texto = self.texto(clave, v)
                if texto != str(self.panel.valores.get(clave)):
                    self.panel.set_valor(clave, texto)
                    cambio = True
        finally:
            self._escribiendo = False
        if cambio:
            self.actualizar()

    def _poner_cursor(self, mano):
        if mano and self._cursor is None:
            self._cursor = self.visor.cursor()
            self.visor.setCursor(Qt.PointingHandCursor)
        elif not mano:
            self._restaurar_cursor()

    def _restaurar_cursor(self):
        if self._cursor is not None:
            self.visor.setCursor(self._cursor)
            self._cursor = None

    def eventFilter(self, obj, e):
        if obj is not self.visor or self._cerrado or (not self.manips and self._arrastre is None):
            return False
        t = e.type()
        if t == QEvent.MouseButtonPress and e.button() == Qt.LeftButton:
            if self.empezar_arrastre(e.position()):
                e.accept()
                return True
        elif t == QEvent.MouseMove:
            if self._arrastre is not None:
                self.arrastrar(e.position())
                return True
            if not e.buttons() and getattr(self.visor, "modo", None) is None:
                tocado = self._tocado(e.position())
                nuevo = (tocado[0].ident, tocado[1]) if tocado is not None else None
                if nuevo != self._hover:
                    self._hover = nuevo
                    self._poner_cursor(nuevo is not None)
                    self.redibujar()
        elif t == QEvent.MouseButtonRelease and self._arrastre is not None and e.button() == Qt.LeftButton:
            self.soltar()
            return True
        elif t == QEvent.MouseButtonDblClick and self._tocado(e.position()) is not None:
            return True
        return False


# ---------------------------------------------------------------- ayudas para los comandos
def entidad(hit, estado):
    """Entidad resuelta de una selección (dict de hit o referencia); None si no se puede."""
    from ..timeline import entidades as ent
    ref = hit.get("ref", hit) if isinstance(hit, dict) else hit
    try:
        return ent.resolver(ref, estado)
    except Exception:  # noqa: BLE001
        return None


def centroide(forma):
    """Centro de una cara (superficie) o de una arista/alambre (longitud)."""
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps
    p = GProp_GProps()
    BRepGProp.SurfaceProperties_s(forma, p)
    if p.Mass() <= 1e-12:
        p = GProp_GProps()
        BRepGProp.LinearProperties_s(forma, p)
    c = p.CentreOfMass()
    return np.array([c.X(), c.Y(), c.Z()])


def base_perfiles(seleccion, estado):
    """(centro, plano, formas) de perfiles / caras planas / curvas elegidos, con el mismo plano que usa
    la extrusión (el del boceto si hay perfiles; si no, el de la primera cara). None si no hay nada."""
    puntos, formas, plano, plano_cara = [], [], None, None
    for h in seleccion or []:
        e = entidad(h, estado)
        if e is None or e.forma is None:
            continue
        if e.tipo == "perfil" and plano is None:
            plano = e.plano
        elif e.plano is not None and plano_cara is None:
            plano_cara = e.plano
        formas.append(e.forma)
        puntos.append(centroide(e.forma))
    plano = plano or plano_cara
    if plano is None or not puntos:
        return None
    return np.mean(puntos, axis=0), plano, formas


def punto_borde(formas, centro, direccion):
    """Punto del contorno de las formas más alejado del centro según `direccion` (para la conicidad)."""
    from ..nucleo import geometria as geo
    pts = []
    for f in formas:
        try:
            v = geo.teselar(f, 0.2)[0]
            pts.append(v if len(v) else np.array([centroide(f)]))
        except Exception:  # noqa: BLE001
            pts.append(np.array([centroide(f)]))
    pts = np.concatenate(pts).astype(float)
    return pts[int(np.argmax((pts - centro) @ direccion))]


def punto_normal_cara(cara):
    """Punto representativo de una cara y su normal hacia afuera del material."""
    from ..nucleo.solidos_modificar import _punto_normal
    p, n = _punto_normal(cara)
    return np.asarray(p, float), unitario(n)


def datos_arista(arista, forma_cuerpo):
    """(punto medio, dirección hacia donde avanza la superficie del empalme/chaflán al crecer, ángulo
    entre las normales de las caras en radianes) de una arista del cuerpo."""
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    from OCP.BRepClass3d import BRepClass3d_SolidClassifier
    from OCP.gp import gp_Pnt
    from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE, TopAbs_IN
    from OCP.TopoDS import TopoDS

    from ..nucleo.solidos_modificar import _ancestros, _normal_en_arista, _padres
    c = BRepAdaptor_Curve(arista)
    t = (c.FirstParameter() + c.LastParameter()) / 2
    p = c.Value(t)
    medio = np.array([p.X(), p.Y(), p.Z()])
    caras = _padres(_ancestros(forma_cuerpo, TopAbs_EDGE, TopAbs_FACE), arista)
    if len(caras) != 2:
        d = c.DN(t, 1)
        return medio, perpendiculares([d.X(), d.Y(), d.Z()])[0], math.pi / 2
    n1 = _normal_en_arista(arista, TopoDS.Face(caras[0]), t)
    n2 = _normal_en_arista(arista, TopoDS.Face(caras[1]), t)
    bis = unitario(n1 + n2)
    if np.linalg.norm(bis) < 1e-9:
        bis = unitario(n1)
    fi = math.acos(max(-1.0, min(1.0, float(n1 @ n2))))
    # Arista convexa: el material queda del lado contrario a las normales y el empalme avanza hacia
    # adentro; cóncava: el empalme agrega material en el hueco (hacia afuera).
    paso = max(1e-3, 1e-3 * float(np.linalg.norm(medio)))
    q = medio - bis * paso
    clas = BRepClass3d_SolidClassifier(forma_cuerpo, gp_Pnt(*map(float, q)), 1e-7)
    hacia = -bis if clas.State() == TopAbs_IN else bis
    return medio, hacia, fi


def herramientas_rojas(formas, deflexion=0.1):
    """Primitivas de la vista previa en rojo de lo que se va a cortar."""
    from ..nucleo import geometria as geo
    tris = [geo.teselar(f, deflexion)[0] for f in formas if f is not None]
    tris = [t for t in tris if len(t)]
    if not tris:
        return []
    return [("tris", np.concatenate(tris), ROJO_PREVIA, 0.45)]

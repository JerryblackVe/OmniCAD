# -*- coding: utf-8 -*-
"""
Tríada del Boceto 3D (3D Sketch Manipulator de Fusion [SKT-CREATE-3D-SKETCH, SKT-3D-SKETCH]) y el dibujo con el
ratón en la vista 3D. La tríada tiene tres ejes (rojo X, verde Y, azul Z), tres planos y tres asas de giro:
  - clic en un plano lo vuelve el plano activo (también Alt, que los recorre);
  - arrastrar un eje mueve la tríada a lo largo de él; arrastrar un asa de giro la rota alrededor de ese eje
    («Restablecer orientación» la vuelve a los ejes del boceto);
  - cada clic de una herramienta pone un punto en el plano activo (o sobre un punto 3D cercano) y la tríada se muda
    al último punto, como en Fusion; también sobre un eje o un asa de giro: esos solo se activan al arrastrar.
Herramientas: seleccionar (arrastra puntos y curvas 3D en el plano activo, con el solver 3D detrás), línea (encadena),
spline (Intro o doble clic la termina), punto, arco de 3 puntos (inicio, fin, paso), círculo (centro y radio),
rectángulo (2 esquinas), elipse (centro, eje mayor, punto del menor), cónica (inicio, fin, vértice) y texto (un clic).
`Triada` es la geometría pura; `Interaccion3D` filtra los eventos del lienzo del boceto mientras la casilla
«Boceto 3D» está activa (el botón izquierdo; el medio y el derecho siguen navegando).
"""
import math

import numpy as np
from PySide6.QtCore import QEvent, QObject, Qt

from ..restricciones import ErrorBoceto
from ..restricciones import boceto3d as b3
from ..restricciones import inferencia3d as inf3

PLANOS = {"xy": (0, 1, 2), "yz": (1, 2, 0), "zx": (2, 0, 1)}       # (eje u, eje v, normal) como filas de R
COLORES = ((0.9, 0.2, 0.2), (0.2, 0.75, 0.25), (0.2, 0.4, 1.0))
PUNTOS_HERRAMIENTA = {"linea": 2, "punto": 1, "arco": 3, "circulo": 2, "rectangulo": 2, "elipse": 3, "conica": 3,
                      "texto": 1}
_ASA_PX, _LARGO_PX = 10, 90
_CLIC_PX = 4                   # hasta cuántos px de temblor un clic sobre un asa sigue siendo un clic
_AYUDA_PX = 10                 # a cuántos px del cursor se engancha una ayuda de dibujo (BOC-47)
_COLOR_AYUDA = (0.2, 0.85, 0.95)


def _giro(eje, angulo):
    k = np.asarray(eje, float) / np.linalg.norm(eje)
    kx = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    return np.identity(3) + math.sin(angulo) * kx + (1 - math.cos(angulo)) * kx @ kx


def _rayo_plano(o, d, origen, normal):
    den = float(d @ normal)
    if abs(den) < 1e-9:
        return None
    return o + d * float((origen - o) @ normal) / den


class Triada:
    """Tríada en coordenadas del boceto: `origen`, `R` (filas = ejes x, y, z de la tríada) y `plano` activo."""

    def __init__(self):
        self.origen, self.R, self.plano = np.zeros(3), np.identity(3), "xy"

    def reiniciar_orientacion(self):
        self.R = np.identity(3)

    def base(self):
        """(u, v, normal) del plano activo."""
        i, j, k = PLANOS[self.plano]
        return self.R[i], self.R[j], self.R[k]

    def ciclar_plano(self):
        orden = list(PLANOS)
        self.plano = orden[(orden.index(self.plano) + 1) % 3]

    def punto_en_plano(self, o, d, por=None):
        """Donde el rayo (o, d) corta el plano activo que pasa por `por` (la tríada si no se da)."""
        return _rayo_plano(o, d, self.origen if por is None else np.asarray(por, float), self.base()[2])

    def parametro_en_eje(self, k, o, d):
        """Parámetro a lo largo del eje k (desde el origen) del punto del eje más cercano al rayo."""
        a = self.R[k]
        w = self.origen - o
        b = float(a @ d)
        den = 1 - b * b
        if den < 1e-9:
            return None
        return (b * float(d @ w) - float(a @ w)) / den

    def angulo_en_giro(self, k, o, d):
        """Ángulo (rad) del punto del rayo sobre el plano perpendicular al eje k, medido desde el eje siguiente."""
        p = _rayo_plano(o, d, self.origen, self.R[k])
        if p is None:
            return None
        w = p - self.origen
        return math.atan2(float(w @ self.R[(k + 2) % 3]), float(w @ self.R[(k + 1) % 3]))

    def girar(self, k, angulo):
        self.R = self.R @ _giro(self.R[k], angulo).T

    def asas(self, largo):
        """Geometría de las asas (coordenadas del boceto) para un eje de `largo` mm: {("eje", k): (origen, punta),
        ("plano", nombre): esquinas 4x3, ("giro", k): (arco Nx3, punto del asa)}."""
        o, salida = self.origen, {}
        for k in range(3):
            salida[("eje", k)] = (o, o + self.R[k] * largo)
            a, b = self.R[(k + 1) % 3], self.R[(k + 2) % 3]
            arco = np.array([o + 0.8 * largo * (math.cos(t) * a + math.sin(t) * b) for t in np.linspace(0.3, 1.27, 12)])
            salida[("giro", k)] = (arco, arco[6])
        for nombre, (i, j, _k) in PLANOS.items():
            u, v = self.R[i] * largo, self.R[j] * largo
            salida[("plano", nombre)] = np.array([o + 0.15 * u + 0.15 * v, o + 0.4 * u + 0.15 * v,
                                                  o + 0.4 * u + 0.4 * v, o + 0.15 * u + 0.4 * v])
        return salida


def _dist_segmento(q, a, b):
    ab = b - a
    t = max(0.0, min(1.0, float((q - a) @ ab) / max(float(ab @ ab), 1e-12)))
    return float(np.linalg.norm(q - (a + t * ab))), t


class Interaccion3D(QObject):
    """Dibujo y edición del Boceto 3D con el ratón y la tríada (filtro de eventos del lienzo del boceto)."""

    def __init__(self, modo):
        super().__init__()
        self.modo, self.triada = modo, Triada()
        self.picks, self.seleccion, self.arrastre, self.cursor = [], [], None, None
        self._clic_asa = None              # dónde se presionó un asa con una herramienta de dibujo, hasta que haya arrastre
        self.activo = False
        self.ayuda = None                  # `Ayuda3D` bajo el cursor: alineación, punto medio, intersección, tangente…
        self._proy = None                  # (clave, `Proyeccion`): el boceto 3D visto desde el plano activo
        self.uniones = {}                  # punto del clic (redondeado) → restricciones 3D que deja su ayuda (BOC-74)
        self._ayuda_clic = None

    # ------------------------------------------------------------ atajos al modo boceto
    @property
    def visor(self):
        return self.modo.v.visor

    @property
    def herramienta(self):
        return self.modo.paleta.h3d.currentData() if self.modo.paleta is not None else None

    def activar(self, valor):
        self.activo = bool(valor)
        self.picks, self.arrastre, self.uniones = [], None, {}
        self._sin_ayuda()
        self.dibujar()

    def reiniciar(self):
        """«Restablecer orientación de la tríada» de Fusion: vuelve a los ejes del boceto."""
        self.triada.reiniciar_orientacion()
        self.dibujar()

    def a_pantalla(self, p):
        """Punto del boceto [x, y, z] → posición en el lienzo (QPointF) o None."""
        return self.visor.proyectar(b3.a_mundo(self.modo.plano, p))

    def _rayo(self, pos):
        o, d = self.visor.rayo(pos)
        pl = self.modo.plano
        return np.array(b3.a_boceto(pl, o)), np.array(b3.a_boceto(pl, d, vector=True))

    def _largo(self):
        return _LARGO_PX / max(self.visor.px_por_mm(), 1e-9)

    def _px(self, p):
        q = self.a_pantalla(p)
        return None if q is None else np.array([q.x(), q.y()])

    # ------------------------------------------------------------ elegir
    def asa_en(self, pos):
        q = np.array([pos.x(), pos.y()])
        mejor = None
        for clave, geo in self.triada.asas(self._largo()).items():
            if clave[0] == "eje":
                a, b = self._px(geo[0]), self._px(geo[1])
                if a is None or b is None:
                    continue
                d, t = _dist_segmento(q, a, b)
                if t < 0.45:                   # cerca del origen mandan los planos
                    continue
            elif clave[0] == "giro":
                p = self._px(geo[1])
                if p is None:
                    continue
                d = float(np.linalg.norm(q - p))
            else:
                esquinas = [self._px(p) for p in geo]
                if any(e is None for e in esquinas):
                    continue
                d = float(np.linalg.norm(q - np.mean(esquinas, axis=0)))
                d = max(0.0, d - 0.25 * max(np.linalg.norm(esquinas[2] - esquinas[0]), 1))
            if d <= _ASA_PX and (mejor is None or d < mejor[0]):
                mejor = (d, clave)
        return None if mejor is None else mejor[1]

    def punto_en(self, pos, radio=8):
        """Id del punto 3D más cercano al cursor (a menos de `radio` px) o None."""
        q = np.array([pos.x(), pos.y()])
        mejor = None
        for pid, p in b3.datos(self.modo.boceto)["puntos"].items():
            s = self._px(p)
            if s is not None and np.linalg.norm(s - q) <= radio and (mejor is None or np.linalg.norm(s - q) < mejor[0]):
                mejor = (float(np.linalg.norm(s - q)), pid)
        return None if mejor is None else mejor[1]

    def curva_en(self, pos, radio=6):
        q = np.array([pos.x(), pos.y()])
        b, pl = self.modo.boceto, self.modo.plano
        for cid in b3.datos(b)["curvas"]:
            try:
                poli = b3.polilineas_de(b, cid, pl)
            except ErrorBoceto:
                continue
            for linea in poli:
                pts = [self.visor.proyectar(p) for p in linea]
                pts = [np.array([p.x(), p.y()]) for p in pts if p is not None]
                if any(_dist_segmento(q, a, c)[0] <= radio for a, c in zip(pts, pts[1:], strict=False)):
                    return cid
        return None

    def _punto_cursor(self, pos):
        """Punto del boceto bajo el cursor: un punto 3D existente si está cerca; si no, el del plano activo, ajustado a la
        ayuda de dibujo que haya (medio, intersección, tangente, alineación)."""
        self._ayuda_clic = None
        pid = self.punto_en(pos)
        if pid is not None:
            return np.array(b3.datos(self.modo.boceto)["puntos"][pid], float)
        p = self.triada.punto_en_plano(*self._rayo(pos))
        self._ayuda_clic = ayuda = self._ayuda_en(p, pos)
        return ayuda.punto if ayuda is not None else p

    # ------------------------------------------------------------ ayudas de dibujo (BOC-47)
    def _proyeccion(self):
        """El boceto 3D visto desde el plano activo (ver `restricciones/inferencia3d.py`): se rehace solo si cambió la
        tríada o la geometría."""
        u, v, _n = self.triada.base()
        g = b3.datos(self.modo.boceto)
        clave = (tuple(np.round(self.triada.origen, 9)), tuple(np.round(u, 9)), tuple(np.round(v, 9)),
                 tuple((k, tuple(p)) for k, p in g["puntos"].items()),
                 tuple((k, c["tipo"], tuple(c["puntos"]), c.get("radio"), tuple(c.get("normal", ())),
                        tuple(c.get("eje_mayor", ())), c.get("radio_menor")) for k, c in g["curvas"].items()))
        if self._proy is None or self._proy[0] != clave:
            self._proy = (clave, inf3.proyectar(self.modo.boceto, self.modo.plano, self.triada.origen, u, v))
        return self._proy[1]

    def _ayuda_en(self, p, pos):
        """La mejor ayuda de dibujo del cursor en `pos` (`p`: su punto en el plano activo), solo con una herramienta de
        dibujo. shortcut: la tolerancia en mm es la del objetivo de la vista; en perspectiva varía con la profundidad."""
        if self.herramienta in (None, "seleccionar"):
            return None
        tol = _AYUDA_PX / max(self.visor.px_por_mm(), 1e-9)
        lista = inf3.ayudas(self._proyeccion(), p, tol, self.picks[-1] if self.picks else None, previa=self.ayuda,
                            rayo=self._rayo(pos))
        return lista[0] if lista else None

    def _sin_ayuda(self):
        self.ayuda = None
        lz = self.modo.lienzo
        if lz is not None and lz.ayuda_3d is not None:
            lz.ayuda_3d = None
            lz.update()

    def _actualizar_ayuda(self, pos):
        """Con el ratón quieto sobre el plano activo: busca la ayuda y le avisa al lienzo (marcador y etiqueta)."""
        nueva = None
        if self.punto_en(pos) is None and self.asa_en(pos) is None:
            nueva = self._ayuda_en(self.triada.punto_en_plano(*self._rayo(pos)), pos)
        q = None if nueva is None else self.a_pantalla(nueva.punto)
        if q is None:
            nueva = None
        cambio = (nueva is None) != (self.ayuda is None) or (nueva is not None and (
            nueva.tipo != self.ayuda.tipo or not np.allclose(nueva.punto, self.ayuda.punto)))
        self.ayuda = nueva
        lz = self.modo.lienzo
        lz.ayuda_3d = None if nueva is None else (q, nueva.tipo, nueva.etiqueta)
        if cambio:
            lz.update()
        return cambio

    # ------------------------------------------------------------ eventos
    def eventFilter(self, obj, ev):
        if not self.activo or self.modo.paleta is None:
            return False
        t = ev.type()
        if t in (QEvent.MouseButtonPress, QEvent.MouseButtonDblClick) and ev.button() == Qt.LeftButton:
            return self.presionar(ev.position(), t == QEvent.MouseButtonDblClick)
        if t == QEvent.MouseMove:
            return self.mover(ev.position())
        if t == QEvent.MouseButtonRelease and ev.button() == Qt.LeftButton:
            return self.soltar()
        if t == QEvent.KeyPress:
            return self.tecla(ev.key())
        return False

    def presionar(self, pos, doble=False):
        if doble:
            return self._terminar_spline() or True
        asa, inicio = self.asa_en(pos), None
        tri = self.triada
        if asa is not None and asa[0] != "plano":
            o, d = self._rayo(pos)
            inicio = tri.parametro_en_eje(asa[1], o, d) if asa[0] == "eje" else tri.angulo_en_giro(asa[1], o, d)
        if asa is not None and asa[0] == "plano":
            tri.plano = asa[1]
        elif inicio is not None:
            self.arrastre = (asa, inicio, tri.origen.copy(), tri.R.copy())
            self._clic_asa = pos if self.herramienta not in (None, "seleccionar") else None
        elif self.herramienta == "seleccionar":
            self._elegir(pos)
        elif self.herramienta:
            self._poner_punto(pos)
        self.dibujar()
        return True

    def _poner_punto(self, pos):
        p = self._punto_cursor(pos)
        if p is None:
            return
        u = inf3.uniones(self._proyeccion(), self._ayuda_clic)
        if u["punto"] or u["curva"]:
            self.uniones[self._clave(p)] = u
        else:
            self.uniones.pop(self._clave(p), None)         # un clic sin ayuda no hereda la de uno anterior en ese lugar
        self.picks.append(p)
        self.triada.origen = np.array(p, float)
        self._crear()

    def _elegir(self, pos):
        pid = self.punto_en(pos)
        objetivo = pid if pid is not None else self.curva_en(pos)
        self.seleccion = [] if objetivo is None else [objetivo]
        if objetivo is None:
            return
        g = b3.datos(self.modo.boceto)
        puntos = [objetivo] if pid is not None else g["curvas"][objetivo]["puntos"]
        base = np.array(g["puntos"][puntos[0]], float)
        agarre = self.triada.punto_en_plano(*self._rayo(pos), por=base)
        if agarre is not None:
            self.modo.lienzo._instantanea()
            self.arrastre = ("geometria", agarre, {p: np.array(g["puntos"][p], float) for p in puntos}, base)

    def mover(self, pos):
        self.cursor = pos
        if self.arrastre is None:
            if self._actualizar_ayuda(pos) or self.picks:
                self.dibujar()
            return False                     # sin arrastre, el lienzo sigue viendo el ratón (navegación, hover)
        if self._clic_asa is not None:
            if (pos - self._clic_asa).manhattanLength() <= _CLIC_PX:
                return True
            self._clic_asa = None
        o, d = self._rayo(pos)
        tri = self.triada
        if self.arrastre[0] == "geometria":
            _, agarre, originales, base = self.arrastre
            p = tri.punto_en_plano(o, d, por=base)
            if p is not None:
                g = b3.datos(self.modo.boceto)
                for pid, xyz in originales.items():
                    g["puntos"][pid] = [float(c) for c in xyz + (p - agarre)]
                self._resolver()
                self.modo._capa3d()
        else:
            (tipo, k), inicio, origen, rot = self.arrastre
            tri.origen, tri.R = origen.copy(), rot.copy()      # se mide contra la tríada del momento de presionar
            if tipo == "eje":
                t = tri.parametro_en_eje(k, o, d)
                if t is not None:
                    tri.origen = origen + rot[k] * (t - inicio)
            else:
                a = tri.angulo_en_giro(k, o, d)
                if a is not None:
                    tri.R = rot.copy()
                    tri.girar(k, a - inicio)
        self.dibujar()
        return True

    def soltar(self):
        if self.arrastre is None:
            return False
        geometria = self.arrastre[0] == "geometria"
        movidos = self.arrastre[2] if geometria else ()
        clic, self._clic_asa = self._clic_asa, None
        self.arrastre = None
        if clic is not None:
            self._poner_punto(clic)
        elif geometria:
            lz = self.modo.lienzo
            if lz.historial and lz.historial[-1] == lz.b.a_dict():
                lz.historial.pop()              # un clic sin mover no deja un paso vacío de deshacer
            else:
                b3.soltar_del_modelo(self.modo.boceto, movidos)     # arrastrado a mano: ya no sigue al modelo
                lz.pila_rehacer.clear()
                self.modo._cambio()
        self.dibujar()
        return True

    def tecla(self, k):
        if k == Qt.Key_Escape and (self.picks or self.seleccion or self._clic_asa is not None):
            self.picks, self.seleccion, self._clic_asa = [], [], None      # Esc con el botón sobre un asa: al soltar no se pone el punto
        elif k in (Qt.Key_Return, Qt.Key_Enter) and self.herramienta == "spline":
            self._terminar_spline()
        elif k == Qt.Key_Alt:
            self.triada.ciclar_plano()
        else:
            return False
        self.dibujar()
        return True

    # ------------------------------------------------------------ crear geometría
    def _valores_cotas(self):
        """{id: medida} de las cotas 3D con los parámetros de ahora, o None si una expresión no se puede evaluar."""
        b = self.modo.boceto
        try:
            return {k: float(self.modo.lienzo.evaluar(c["expresion"])) for k, c in b3.datos(b)["cotas"].items()}
        except Exception:  # noqa: BLE001 — una expresión rota no frena el arrastre; el paso la avisará
            return None

    def _resolver(self):
        """Solver 3D con las cotas actuales (lo mismo que hará el paso del boceto)."""
        valores = self._valores_cotas()
        if valores is not None:
            b3.resolver(self.modo.boceto, valores)

    @staticmethod
    def _clave(p):
        return tuple(np.round(np.asarray(p, float), 6) + 0.0)

    def _dejar_uniones(self, picks, nuevo):
        """Las restricciones que dejaron las ayudas en los clics de lo recién creado (`nuevo`: id de la línea o del punto):
        al punto de cada clic y, con la línea, las de su último clic (perpendicular, eje). Solo las que ya se cumplen."""
        b = self.modo.boceto
        g, valores = b3.datos(b), self._valores_cotas()
        if valores is None:
            return
        nuevo = None if isinstance(nuevo, list) else nuevo        # un rectángulo: sus clics se unen por posición
        for i, p in enumerate(picks):
            u = self.uniones.get(self._clave(p))
            if not u:
                continue
            pid = nuevo if nuevo in g["puntos"] else next((k for k, q in g["puntos"].items() if math.dist(q, p) < 1e-6), None)
            linea = nuevo if i == len(picks) - 1 and g["curvas"].get(nuevo, {}).get("tipo") == "linea" else None
            b3.aplicar_uniones(b, u, pid, linea, valores)

    def _aplicar(self, funcion, picks=()):
        lz = self.modo.lienzo
        lz._instantanea()                   # Ctrl+Z del boceto también deshace lo 3D
        try:
            self._dejar_uniones(picks, funcion(self.modo.boceto))
        except ErrorBoceto as e:
            lz._restaurar(lz.historial.pop())
            self.modo.v.mensaje(f"Boceto 3D: {e}", 7000)
            return False
        lz.pila_rehacer.clear()
        self.modo._cambio()
        return True

    def _crear(self):
        h, p = self.herramienta, self.picks
        if h == "spline" or len(p) < PUNTOS_HERRAMIENTA.get(h, 99):
            return
        u, v, n = self.triada.base()
        if h == "linea":
            self._aplicar(lambda b: b3.agregar_linea(b, p[0], p[1]), p)
            self.picks = [p[1]]               # la línea sigue desde el último punto (Esc corta)
            return
        if h == "punto":
            accion = lambda b: b3.agregar_punto(b, p[0], unir=False)  # noqa: E731
        elif h == "arco":
            accion = lambda b: b3.agregar_arco(b, p[0], p[2], p[1])  # noqa: E731
        elif h == "circulo":
            accion = lambda b: b3.agregar_circulo(b, p[0], np.linalg.norm(p[1] - p[0]), n)  # noqa: E731
        elif h == "rectangulo":
            accion = lambda b: b3.agregar_rectangulo(b, p[0], p[1], u, v)  # noqa: E731
        elif h == "elipse":
            eje = (p[1] - p[0]) - float((p[1] - p[0]) @ n) * n
            w = p[2] - p[0]
            menor = np.linalg.norm(np.cross(eje / max(np.linalg.norm(eje), 1e-12), w - float(w @ n) * n))
            accion = lambda b: b3.agregar_elipse(b, p[0], eje, menor, n)  # noqa: E731
        elif h == "conica":
            accion = lambda b: b3.agregar_conica(b, p[0], p[2], p[1], 0.5)  # noqa: E731
        else:
            pal = self.modo.paleta
            accion = lambda b: b3.agregar_texto(b, p[0], pal.texto3d.text(), pal.altura3d.value(), u, v)  # noqa: E731
        self._aplicar(accion, p)
        self.picks = []

    def _terminar_spline(self):
        if self.herramienta != "spline" or len(self.picks) < 2:
            return False
        pts = list(self.picks)
        self.picks = []
        self._aplicar(lambda b: b3.agregar_spline(b, pts), pts)
        self.dibujar()
        return True

    # ------------------------------------------------------------ dibujo
    def dibujar(self):
        visor = self.visor
        if not self.activo:
            visor.set_capa("triada3d", None)
            return
        pl, tri = self.modo.plano, self.triada
        w = lambda p: b3.a_mundo(pl, p)  # noqa: E731
        prims = []
        for clave, geo in tri.asas(self._largo()).items():
            if clave[0] == "eje":
                prims.append(("lineas", np.array([w(geo[0]), w(geo[1])], np.float32), COLORES[clave[1]], 3.0))
            elif clave[0] == "giro":
                arco = np.array([w(p) for p in geo[0]], np.float32)
                segs = np.repeat(arco, 2, axis=0)[1:-1]
                prims.append(("lineas", segs, (0.55, 0.55, 0.55), 2.0))
                prims.append(("puntos", np.array([w(geo[1])], np.float32), COLORES[clave[1]], 9))
            else:
                e = [w(p) for p in geo]
                activo = clave[1] == tri.plano
                prims.append(("tris", np.array([e[0], e[1], e[2], e[0], e[2], e[3]], np.float32),
                              (0.25, 0.55, 1.0) if activo else (0.95, 0.75, 0.45), 0.6 if activo else 0.3))
        prims.append(("puntos", np.array([w(tri.origen)], np.float32), (0.9, 0.9, 0.9), 8))
        guia = list(self.picks)
        if self.picks and self.cursor is not None:
            c = self.ayuda.punto if self.ayuda is not None else self.triada.punto_en_plano(*self._rayo(self.cursor))
            if c is not None:
                guia.append(c)
        if self.ayuda is not None:                    # las guías de la ayuda (alineación, tangente…) y el punto al que engancha
            for a, c in self.ayuda.guias:
                prims.append(("lineas", np.array([w(a), w(c)], np.float32), _COLOR_AYUDA, 1.5))
            prims.append(("puntos", np.array([w(self.ayuda.punto)], np.float32), _COLOR_AYUDA, 9))
        if len(guia) >= 2:
            pts = np.array([w(p) for p in guia], np.float32)
            prims.append(("lineas", np.repeat(pts, 2, axis=0)[1:-1], (1.0, 0.6, 0.1), 1.5))
        g = b3.datos(self.modo.boceto)
        marcados = [w(g["puntos"][i]) for i in self.seleccion if i in g["puntos"]]
        for cid in self.seleccion:
            if cid in g["curvas"]:
                marcados += [w(g["puntos"][p]) for p in g["curvas"][cid]["puntos"]]
        if marcados:
            prims.append(("puntos", np.array(marcados, np.float32), (1.0, 0.85, 0.1), 10))
        visor.set_capa("triada3d", prims)


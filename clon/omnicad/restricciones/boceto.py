# -*- coding: utf-8 -*-
"""
Modelo de datos del boceto 2D paramétrico.

Equivalencias con Fusion 360 (informe_analisis.md §3.2 y ayuda "Design: Sketch", SKT-*):
  - SketchPoint / SketchLine / SketchCircle / SketchArc / SketchEllipse / SketchEllipticalArc /
    SketchFittedSpline / SketchControlPointSpline / SketchConicCurve / SketchText  →  Punto, Linea,
    Circulo, Arco, Elipse, ArcoElipse, Spline (modo "ajuste" o "control"), Conica y Texto.
  - El rectángulo y la ranura NO son entidades: igual que en Fusion se arman con líneas y arcos que
    comparten vértices, más sus restricciones.
  - Tipo de línea (Paleta de boceto): normal, construcción (no forma perfiles) o eje / línea central
    (sí forma perfiles; se dibuja con trazo y punto).
  - Geometría proyectada (violeta en Fusion): curvas con `proyectada=True`, fijas para el solver.
  - GeometricConstraints → `TIPOS_RESTRICCION`. "Fijar" en Fusion es la propiedad `isFixed`; acá es
    la restricción 'fijo' (mismo efecto). 'desfase' y 'patron' son las restricciones internas que
    Fusion muestra como glifo de desfase / patrón.
  - SketchDimensions → `TIPOS_COTA`; cada cota guarda una EXPRESIÓN (puede usar parámetros).
  - Comandos de MODIFICAR (empalme, chaflán, recortar, alargar, partir, desfase, escala, mover/copiar,
    curva de fusión) y de CREAR (simetría, patrones, desglosar texto) son métodos del Boceto.

Coordenadas en milímetros, en el sistema (u, v) del plano del boceto.
"""
import bisect
import copy
import math
import re
from functools import lru_cache

import numpy as np

TIPOS_RESTRICCION = {
    "coincidente": "Coincidente", "horizontal": "Horizontal", "vertical": "Vertical",
    "paralela": "Paralela", "perpendicular": "Perpendicular", "igual": "Igual",
    "tangente": "Tangente", "concentrica": "Concéntrica", "punto_medio": "Punto medio", "fijo": "Fijo",
    "colineal": "Colineal", "simetrica": "Simetría", "curvatura": "Curvatura", "poligono": "Polígono",
    "desfase": "Desfase", "patron": "Patrón",
}
TIPOS_COTA = {
    "distancia": "Distancia", "distancia_h": "Distancia horizontal", "distancia_v": "Distancia vertical",
    "radio": "Radio", "diametro": "Diámetro", "angulo": "Ángulo", "desfase": "Desfase",
}
COTAS_POSITIVAS = ("distancia", "distancia_h", "distancia_v", "radio", "diametro", "desfase")   # todas menos el ángulo
# mm (1 km): tope de una cota de largo. Más allá el núcleo ya no calcula bien (un barrido por una ruta de 1 km da el
# volumen exacto; por una de 10 km falla); nucleo/perfiles.py busca regiones cerradas en ±MEDIDA_MAXIMA
MEDIDA_MAXIMA = 1e6
CIRCULARES = ("circulo", "arco")
ELIPTICAS = ("elipse", "arco_elipse")
LIBRES = ("spline", "conica")
GEOMETRICAS = ("linea",) + CIRCULARES + ELIPTICAS + LIBRES      # todo menos el texto
CON_CENTRO = CIRCULARES + ELIPTICAS
_DOS_PI = 2 * math.pi


class ErrorBoceto(ValueError):
    pass


def validar_valor_cota(tipo, valor):
    """Como Fusion, una cota de largo, radio, diámetro o desfase tiene que ser mayor que cero (el solver
    toma el valor absoluto del radio: −5 quedaba guardado y dibujaba 5) y de hasta MEDIDA_MAXIMA (1 km; frena
    valores absurdos como un radio de 1e9 o infinito). Los ángulos no se validan acá."""
    if tipo not in COTAS_POSITIVAS:
        return
    nombre = TIPOS_COTA[tipo].lower()
    if not valor > 0:                                   # también NaN
        raise ErrorBoceto(f"La cota de {nombre} tiene que ser mayor que cero (vale {valor:g}).")
    if not valor <= MEDIDA_MAXIMA:                      # también infinito
        miles = f"{MEDIDA_MAXIMA:,.0f}".replace(",", ".")
        raise ErrorBoceto(f"La cota de {nombre} no puede pasar de {miles} mm (1 km; vale {valor:g} mm): más grande, "
                          "el núcleo geométrico ya no calcula bien.")


# ---------------------------------------------------------------- entidades
class Punto:
    tipo = "punto"

    def __init__(self, id, x, y, proyectado=False):
        self.id, self.x, self.y, self.proyectado = id, float(x), float(y), bool(proyectado)

    def a_dict(self):
        d = {"id": self.id, "x": self.x, "y": self.y}
        if self.proyectado:
            d["proyectado"] = True
        return d


class _Curva:
    """Base de las curvas: estilo (normal / construcción / eje) y si viene de una proyección."""
    tipo = ""
    PUNTOS = ()          # atributos que son ids de puntos del boceto
    DATOS = ()           # otros atributos que se guardan

    def _estilo(self, construccion, eje, proyectada):
        self.construccion, self.eje, self.proyectada = bool(construccion), bool(eje), bool(proyectada)

    def puntos(self):
        return [getattr(self, a) for a in self.PUNTOS]

    def extremos(self):
        """(inicio, fin) de las curvas abiertas; None en las cerradas."""
        return None

    def a_dict(self):
        d = {"tipo": self.tipo, "id": self.id}
        for a in self.PUNTOS + self.DATOS:
            v = getattr(self, a)
            d[a] = list(v) if isinstance(v, (list, tuple)) else v
        d["construccion"] = self.construccion
        if self.eje:
            d["eje"] = True
        if self.proyectada:
            d["proyectada"] = True
        return d

    def remapear(self, mapa, nuevo_id=None):
        """Copia con los ids de puntos cambiados según `mapa` (para copiar, simetría y patrones)."""
        c = copy.deepcopy(self)
        c.id = self.id if nuevo_id is None else nuevo_id
        for a in self.PUNTOS:
            setattr(c, a, mapa.get(getattr(self, a), getattr(self, a)))
        return c


class Linea(_Curva):
    tipo, PUNTOS = "linea", ("p1", "p2")

    def __init__(self, id, p1, p2, construccion=False, eje=False, proyectada=False):
        self.id, self.p1, self.p2 = id, p1, p2
        self._estilo(construccion, eje, proyectada)

    def extremos(self):
        return self.p1, self.p2


class Circulo(_Curva):
    tipo, PUNTOS, DATOS = "circulo", ("centro",), ("radio",)

    def __init__(self, id, centro, radio, construccion=False, eje=False, proyectada=False):
        self.id, self.centro, self.radio = id, centro, float(radio)
        self._estilo(construccion, eje, proyectada)


class Arco(_Curva):
    """Arco antihorario de `inicio` a `fin` alrededor de `centro` (radio = |inicio - centro|)."""
    tipo, PUNTOS = "arco", ("centro", "inicio", "fin")

    def __init__(self, id, centro, inicio, fin, construccion=False, eje=False, proyectada=False):
        self.id, self.centro, self.inicio, self.fin = id, centro, inicio, fin
        self._estilo(construccion, eje, proyectada)

    def extremos(self):
        return self.inicio, self.fin


class Elipse(_Curva):
    """Elipse de Fusion: centro, extremo del eje mayor (`mayor`, define a y el giro) y radio menor b."""
    tipo, PUNTOS, DATOS = "elipse", ("centro", "mayor"), ("radio_menor",)

    def __init__(self, id, centro, mayor, radio_menor, construccion=False, eje=False, proyectada=False):
        self.id, self.centro, self.mayor, self.radio_menor = id, centro, mayor, float(radio_menor)
        self._estilo(construccion, eje, proyectada)


class ArcoElipse(_Curva):
    """Arco de elipse antihorario de `inicio` a `fin` (sale de recortar o partir una elipse)."""
    tipo, PUNTOS, DATOS = "arco_elipse", ("centro", "mayor", "inicio", "fin"), ("radio_menor",)

    def __init__(self, id, centro, mayor, radio_menor, inicio, fin, construccion=False, eje=False,
                 proyectada=False):
        self.id, self.centro, self.mayor, self.radio_menor = id, centro, mayor, float(radio_menor)
        self.inicio, self.fin = inicio, fin
        self._estilo(construccion, eje, proyectada)

    def extremos(self):
        return self.inicio, self.fin


class Spline(_Curva):
    """Spline de Fusion. modo "ajuste": la curva PASA por sus puntos (Fit Point Spline); modo
    "control": los puntos son los polos (Control Point Spline, grado 3 o 5; con `pesos` y `nudos`
    explícitos cuando sale de recortar, proyectar o desglosar texto)."""
    tipo, DATOS = "spline", ("modo", "grado", "cerrada", "pesos", "nudos")

    def __init__(self, id, puntos, modo="ajuste", grado=3, cerrada=False, pesos=None, nudos=None,
                 construccion=False, eje=False, proyectada=False):
        self.id, self.pts, self.modo, self.grado = id, list(puntos), modo, int(grado)
        self.cerrada = bool(cerrada)
        self.pesos = None if pesos is None else [float(w) for w in pesos]
        self.nudos = None if nudos is None else [float(k) for k in nudos]
        self._estilo(construccion, eje, proyectada)

    def puntos(self):
        return list(self.pts)

    def extremos(self):
        return None if self.cerrada else (self.pts[0], self.pts[-1])

    def a_dict(self):
        d = super().a_dict()
        d["puntos"] = list(self.pts)
        return d

    def remapear(self, mapa, nuevo_id=None):
        c = super().remapear(mapa, nuevo_id)
        c.pts = [mapa.get(p, p) for p in self.pts]
        return c


class Conica(_Curva):
    """Curva cónica de Fusion: extremos, vértice (cruce de las tangentes) y Rho (0 < rho < 1;
    0.5 = parábola, menor = elipse, mayor = hipérbola)."""
    tipo, PUNTOS, DATOS = "conica", ("inicio", "vertice", "fin"), ("rho",)

    def __init__(self, id, inicio, vertice, fin, rho=0.5, construccion=False, eje=False, proyectada=False):
        self.id, self.inicio, self.vertice, self.fin, self.rho = id, inicio, vertice, fin, float(rho)
        self._estilo(construccion, eje, proyectada)

    def extremos(self):
        return self.inicio, self.fin


class Texto(_Curva):
    """Texto de boceto: `punto` es la esquina inferior izquierda de la línea base; el ángulo, en grados.
    Sus contornos forman perfiles (se pueden extruir), como en Fusion.

    Además de fuente, altura, negrita y cursiva: `espaciado` (mm entre letras), `interlineado` (factor),
    `alineacion` ("izq", "centro", "der" dentro de la caja), `ancla_v` ("base", "arriba", "medio", "abajo":
    qué parte del bloque cae sobre `punto`), `ancho_caja` (mm; 0 = sin caja, >0 parte las líneas) y
    `voltear_h` / `voltear_v` (espejo dentro del bloque).

    Texto en curva (Fusion: texto en trayectoria): `camino` es el id de una curva del mismo boceto; entonces
    `punto` y `angulo` no se usan y las letras siguen la curva. `camino_lado` ("izq" / "der": de qué lado del
    sentido de la curva van las letras), `camino_pos` (fracción 0-1 del largo donde cae el ancla, según
    `alineacion`), `camino_desfase` (mm entre la curva y la línea base) y `camino_ajustar` (repartir en todo el
    largo). Si la curva se borra, el texto vuelve a ser recto."""
    tipo, PUNTOS = "texto", ("punto",)
    DATOS = ("texto", "fuente", "altura", "angulo", "negrita", "cursiva", "espaciado", "interlineado", "alineacion",
             "ancla_v", "ancho_caja", "voltear_h", "voltear_v", "camino", "camino_lado", "camino_pos",
             "camino_desfase", "camino_ajustar")
    _PREDETERMINADOS = {"espaciado": 0.0, "interlineado": 1.0, "alineacion": "izq", "ancla_v": "base",
                        "ancho_caja": 0.0, "voltear_h": False, "voltear_v": False, "camino": None,
                        "camino_lado": "izq", "camino_pos": 0.5, "camino_desfase": 0.0, "camino_ajustar": False}

    def __init__(self, id, punto, texto, fuente="Arial", altura=5.0, angulo=0.0, negrita=False, cursiva=False,
                 construccion=False, eje=False, proyectada=False, espaciado=0.0, interlineado=1.0,
                 alineacion="izq", ancla_v="base", ancho_caja=0.0, voltear_h=False, voltear_v=False, camino=None,
                 camino_lado="izq", camino_pos=0.5, camino_desfase=0.0, camino_ajustar=False):
        self.id, self.punto, self.texto, self.fuente = id, punto, str(texto), str(fuente)
        self.altura, self.angulo = float(altura), float(angulo)
        self.negrita, self.cursiva = bool(negrita), bool(cursiva)
        self.espaciado, self.interlineado = float(espaciado), float(interlineado)
        self.alineacion, self.ancla_v, self.ancho_caja = str(alineacion), str(ancla_v), float(ancho_caja)
        self.voltear_h, self.voltear_v = bool(voltear_h), bool(voltear_v)
        self.camino = None if camino is None else int(camino)
        self.camino_lado, self.camino_pos = str(camino_lado), float(camino_pos)
        self.camino_desfase, self.camino_ajustar = float(camino_desfase), bool(camino_ajustar)
        self._estilo(construccion, eje, proyectada)

    def a_dict(self):
        """Como las demás curvas, pero sin las opciones que tienen su valor por defecto (los archivos viejos
        y los nuevos sin opciones quedan iguales)."""
        d = super().a_dict()
        for k, v in self._PREDETERMINADOS.items():
            if d.get(k) == v:
                del d[k]
        return d

    def opciones_contorno(self):
        """Opciones de `fuentes.contornos_texto` en el orden en que se guardan en el caché."""
        return (self.espaciado, self.interlineado, self.alineacion, self.ancla_v, self.ancho_caja,
                self.voltear_h, self.voltear_v)


class Restriccion:
    def __init__(self, id, tipo, entidades, datos=None):
        if tipo not in TIPOS_RESTRICCION:
            raise ErrorBoceto(f"Restricción desconocida: {tipo}")
        self.id, self.tipo, self.entidades, self.datos = id, tipo, list(entidades), dict(datos or {})

    def a_dict(self):
        return {"id": self.id, "tipo": self.tipo, "entidades": self.entidades, "datos": self.datos}


class Cota:
    def __init__(self, id, tipo, entidades, expresion, datos=None):
        if tipo not in TIPOS_COTA:
            raise ErrorBoceto(f"Cota desconocida: {tipo}")
        self.id, self.tipo, self.entidades, self.expresion = id, tipo, list(entidades), str(expresion)
        self.datos = dict(datos or {})

    def a_dict(self):
        return {"id": self.id, "tipo": self.tipo, "entidades": self.entidades,
                "expresion": self.expresion, "datos": self.datos}


_CURVAS = {k.tipo: k for k in (Linea, Circulo, Arco, Elipse, ArcoElipse, Spline, Conica, Texto)}
_CON_RADIO = (Circulo, Elipse, ArcoElipse)      # llevan un radio (o radio menor) como incógnita propia


# ---------------------------------------------------------------- B-splines (The NURBS Book, Piegl y Tiller)
def nudos_uniformes(n_polos, grado):
    """Vector de nudos sujeto (clamped) y uniforme en [0, 1]."""
    p = min(grado, n_polos - 1)
    interiores = n_polos - p - 1
    return [0.0] * (p + 1) + [i / (interiores + 1) for i in range(1, interiores + 1)] + [1.0] * (p + 1)


def _tramo(nudos, p, n, t):
    """Índice k del tramo [u_k, u_k+1) que contiene t (fuera del dominio, el tramo extremo: así la
    evaluación extrapola el polinomio del borde)."""
    if t >= nudos[n + 1]:
        k = n
        while k > p and nudos[k] >= nudos[n + 1]:
            k -= 1
        return k
    k = bisect.bisect_right(nudos, t) - 1
    return min(max(k, p), n)


def _de_boor(ctrl, nudos, p, t):
    n = len(ctrl) - 1
    k = _tramo(nudos, p, n, t)
    d = [list(ctrl[j + k - p]) for j in range(p + 1)]
    for r in range(1, p + 1):
        for j in range(p, r - 1, -1):
            i = j + k - p
            den = nudos[i + p - r + 1] - nudos[i]
            a = (t - nudos[i]) / den if den else 0.0
            d[j] = [(1 - a) * x0 + a * x1 for x0, x1 in zip(d[j - 1], d[j], strict=True)]
    return d[p]


def _ctrl_derivada(ctrl, nudos, p):
    q = []
    for i in range(len(ctrl) - 1):
        den = nudos[i + p + 1] - nudos[i + 1]
        f = p / den if den else 0.0
        q.append([f * (b - a) for a, b in zip(ctrl[i], ctrl[i + 1], strict=True)])
    return q, nudos[1:-1], p - 1


def evaluar_bspline(polos, nudos, grado, pesos, t, derivadas=0):
    """[C, C', C''][:derivadas+1] de una B-spline (racional si hay pesos) en t."""
    w = pesos or [1.0] * len(polos)
    ctrl = [(x * wi, y * wi, wi) for (x, y), wi in zip(polos, w, strict=True)]
    hs, k, q = [], list(nudos), grado
    c = ctrl
    for orden in range(derivadas + 1):
        hs.append(_de_boor(c, k, q, t) if q >= 0 and c else [0.0, 0.0, 0.0])
        if orden < derivadas:
            if q <= 0 or len(c) < 2:
                c, q = [], -1
            else:
                c, k, q = _ctrl_derivada(c, k, q)
    A = hs[0]
    ws = A[2] or 1e-300
    C = (A[0] / ws, A[1] / ws)
    salida = [C]
    if derivadas >= 1:
        A1 = hs[1]
        C1 = ((A1[0] - A1[2] * C[0]) / ws, (A1[1] - A1[2] * C[1]) / ws)
        salida.append(C1)
        if derivadas >= 2:
            A2 = hs[2]
            salida.append(((A2[0] - 2 * A1[2] * C1[0] - A2[2] * C[0]) / ws,
                           (A2[1] - 2 * A1[2] * C1[1] - A2[2] * C[1]) / ws))
    return salida


def _funciones_base(nudos, p, t, k):
    """N_{k-p..k, p}(t) (algoritmo A2.2)."""
    N = [1.0] + [0.0] * p
    izq, der = [0.0] * (p + 1), [0.0] * (p + 1)
    for j in range(1, p + 1):
        izq[j] = t - nudos[k + 1 - j]
        der[j] = nudos[k + j] - t
        salvado = 0.0
        for r in range(j):
            den = der[r + 1] + izq[j - r]
            temp = N[r] / den if den else 0.0
            N[r] = salvado + der[r + 1] * temp
            salvado = izq[j - r] * temp
        N[j] = salvado
    return N


def _resolver_lineal(A, B):
    try:
        return np.linalg.solve(A, B)
    except np.linalg.LinAlgError:
        return np.linalg.lstsq(A, B, rcond=None)[0]


def interpolar_spline(puntos, grado=3, cerrada=False):
    """(polos, nudos, grado) de la B-spline que PASA por los puntos (parámetros por cuerda, nudos
    promediados). Cerrada: vuelve al primer punto con la misma tangente (continuidad C1)."""
    Q = [(float(x), float(y)) for x, y in puntos]
    cerrar = cerrada and len(Q) >= 3
    if cerrar:
        Q = Q + [Q[0]]
    m = len(Q) - 1
    if m < 1:
        raise ErrorBoceto("Una spline necesita al menos dos puntos.")
    cuerdas = [math.dist(Q[i], Q[i - 1]) for i in range(1, m + 1)]
    total = sum(cuerdas)
    if total < 1e-12:
        cuerdas, total = [1.0] * m, float(m)
    cuerdas = [max(c, total * 1e-9) for c in cuerdas]
    total = sum(cuerdas)
    ub = [0.0]
    for c in cuerdas:
        ub.append(ub[-1] + c / total)
    ub[-1] = 1.0
    if cerrar:
        p, n = 3, m + 2
        nudos = [0.0] * 4 + ub[1:m] + [1.0] * 4
        A, B = np.zeros((n + 1, n + 1)), np.zeros((n + 1, 2))
        for fila, (u, q) in enumerate(zip(ub, Q, strict=True)):
            k = _tramo(nudos, p, n, u)
            A[fila, k - p:k + 1] = _funciones_base(nudos, p, u, k)
            B[fila] = q
        D = ((Q[1][0] - Q[m - 1][0]) / (ub[1] + 1 - ub[m - 1]), (Q[1][1] - Q[m - 1][1]) / (ub[1] + 1 - ub[m - 1]))
        f0, f1 = p / nudos[p + 1], p / (1 - nudos[n])
        A[m + 1, 0], A[m + 1, 1], B[m + 1] = -f0, f0, D
        A[m + 2, n - 1], A[m + 2, n], B[m + 2] = -f1, f1, D
    else:
        p, n = min(grado, m), m
        nudos = [0.0] * (p + 1) + [sum(ub[j:j + p]) / p for j in range(1, m - p + 1)] + [1.0] * (p + 1)
        A, B = np.zeros((n + 1, n + 1)), np.array(Q)
        for fila, u in enumerate(ub):
            k = _tramo(nudos, p, n, u)
            A[fila, k - p:k + 1] = _funciones_base(nudos, p, u, k)
    P = _resolver_lineal(A, B)
    return [(float(x), float(y)) for x, y in P], nudos, p


def _insertar_nudo(ctrl, nudos, p, t):
    """Inserción de un nudo (Boehm) en coordenadas homogéneas."""
    n = len(ctrl) - 1
    k = _tramo(nudos, p, n, t)
    nuevo = []
    for i in range(n + 2):
        if i <= k - p:
            nuevo.append(list(ctrl[i]))
        elif i <= k:
            den = nudos[i + p] - nudos[i]
            a = (t - nudos[i]) / den if den else 0.0
            nuevo.append([(1 - a) * x0 + a * x1 for x0, x1 in zip(ctrl[i - 1], ctrl[i], strict=True)])
        else:
            nuevo.append(list(ctrl[i - 1]))
    return nuevo, nudos[:k + 1] + [t] + nudos[k + 1:]


def tramo_bspline(polos, nudos, grado, pesos, ta, tb):
    """(polos, nudos, pesos) del pedazo [ta, tb] de una B-spline (subdivisión por inserción de nudos)."""
    w = pesos or [1.0] * len(polos)
    ctrl = [[x * wi, y * wi, wi] for (x, y), wi in zip(polos, w, strict=True)]
    k = list(nudos)
    p = grado
    for t, lado in ((ta, "der"), (tb, "izq")):
        dom0, dom1 = k[p], k[len(k) - p - 1]
        if (lado == "der" and t <= dom0 + 1e-12) or (lado == "izq" and t >= dom1 - 1e-12):
            continue
        for _ in range(p - sum(1 for u in k if abs(u - t) < 1e-12)):
            ctrl, k = _insertar_nudo(ctrl, k, p, t)
        r = next(i for i, u in enumerate(k) if abs(u - t) < 1e-12)
        if lado == "der":
            ctrl, k = ctrl[r - 1:], [t] + k[r:]
        else:
            ctrl, k = ctrl[:r], k[:r + p] + [t]
    polos_n = [(c[0] / c[2], c[1] / c[2]) for c in ctrl]
    pesos_n = [c[2] for c in ctrl] if pesos else None
    return polos_n, k, pesos_n


# ---------------------------------------------------------------- primitivas 2D (salida de geometria())
def _rot(x, y, ang):
    c, s = math.cos(ang), math.sin(ang)
    return c * x - s * y, s * x + c * y


def _barrido(a0, a1):
    return (a1 - a0) % _DOS_PI or _DOS_PI


def parametro_elipse(c, a, b, ang, q):
    """Parámetro t (ángulo excéntrico) del punto de la elipse más alineado con q."""
    x, y = _rot(q[0] - c[0], q[1] - c[1], -ang)
    return math.atan2(y / (b or 1e-12), x / (a or 1e-12))


def dominio(prim):
    """(t0, t1, periódica) del parámetro de una primitiva."""
    t = prim[0]
    if t == "linea":
        return 0.0, 1.0, False
    if t in ("circulo", "elipse"):
        return 0.0, _DOS_PI, True
    if t == "arco":
        return 0.0, _barrido(prim[4], prim[5]), False
    if t == "arco_elipse":
        return 0.0, _barrido(prim[6], prim[7]), False
    nudos, p = prim[3], prim[4]
    return nudos[p], nudos[len(nudos) - p - 1], False


def evaluar_primitiva(prim, t, derivadas=0):
    """[C, C', C''][:derivadas+1] de una primitiva en el parámetro t (fuera del dominio, extrapola)."""
    tipo = prim[0]
    if tipo == "linea":
        (x1, y1), (x2, y2) = prim[2], prim[3]
        return [(x1 + t * (x2 - x1), y1 + t * (y2 - y1)), (x2 - x1, y2 - y1), (0.0, 0.0)][:derivadas + 1]
    if tipo in ("circulo", "arco"):
        (cx, cy), r = prim[2], prim[3]
        a = t + (prim[4] if tipo == "arco" else 0.0)
        c, s = math.cos(a), math.sin(a)
        return [(cx + r * c, cy + r * s), (-r * s, r * c), (-r * c, -r * s)][:derivadas + 1]
    if tipo in ("elipse", "arco_elipse"):
        (cx, cy), a, b, ang = prim[2], prim[3], prim[4], prim[5]
        u = t + (prim[6] if tipo == "arco_elipse" else 0.0)
        c, s = math.cos(u), math.sin(u)
        locales = [(a * c, b * s), (-a * s, b * c), (-a * c, -b * s)][:derivadas + 1]
        salida = [_rot(x, y, ang) for x, y in locales]
        salida[0] = (salida[0][0] + cx, salida[0][1] + cy)
        return salida
    return evaluar_bspline(prim[2], prim[3], prim[4], prim[5], t, derivadas)


def _cantidad_muestras(prim, pasos):
    t0, t1, _ = dominio(prim)
    if prim[0] == "linea":
        return 1
    if prim[0] == "spline":
        tramos = max(1, len(set(prim[3])) - 1)
        return max(12, min(4 * pasos, tramos * max(8, pasos // 4)))
    return max(8, int(math.ceil(pasos * (t1 - t0) / _DOS_PI)))


def puntos_primitiva(prim, pasos=64):
    """Polilínea [(u, v), ...] que muestrea CUALQUIER primitiva de `Boceto.geometria()` (las cerradas
    repiten el primer punto al final). `pasos` = muestras por vuelta completa."""
    if prim[0] == "linea":
        return [tuple(prim[2]), tuple(prim[3])]
    t0, t1, _ = dominio(prim)
    n = _cantidad_muestras(prim, pasos)
    return [evaluar_primitiva(prim, t0 + (t1 - t0) * i / n)[0] for i in range(n + 1)]


def _muestras(prim, pasos=96):
    t0, t1, _ = dominio(prim)
    n = _cantidad_muestras(prim, pasos)
    ts = [t0 + (t1 - t0) * i / n for i in range(n + 1)]
    return ts, [evaluar_primitiva(prim, t)[0] for t in ts]


def mas_cercano(prim, q):
    """(t, distancia, punto) del punto de la primitiva más cercano a q."""
    tipo = prim[0]
    if tipo == "linea":
        (x1, y1), (x2, y2) = prim[2], prim[3]
        dx, dy = x2 - x1, y2 - y1
        L2 = dx * dx + dy * dy or 1e-18
        t = max(0.0, min(1.0, ((q[0] - x1) * dx + (q[1] - y1) * dy) / L2))
        p = (x1 + t * dx, y1 + t * dy)
        return t, math.dist(p, q), p
    if tipo in ("circulo", "arco"):
        cx, cy = prim[2]
        a = math.atan2(q[1] - cy, q[0] - cx)
        if tipo == "circulo":
            t = a % _DOS_PI
        else:
            t = (a - prim[4]) % _DOS_PI
            barr = _barrido(prim[4], prim[5])
            if t > barr:
                t = barr if math.dist(evaluar_primitiva(prim, barr)[0], q) < math.dist(evaluar_primitiva(prim, 0)[0], q) else 0.0
        p = evaluar_primitiva(prim, t)[0]
        return t, math.dist(p, q), p
    ts, pts = _muestras(prim, 128)
    i = min(range(len(pts)), key=lambda k: (pts[k][0] - q[0]) ** 2 + (pts[k][1] - q[1]) ** 2)
    lo, hi = ts[max(0, i - 1)], ts[min(len(ts) - 1, i + 1)]
    f = lambda t: (lambda p: (p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2)(evaluar_primitiva(prim, t)[0])  # noqa: E731
    g = (math.sqrt(5) - 1) / 2
    a, b = lo, hi
    c, d = b - g * (b - a), a + g * (b - a)
    fc, fd = f(c), f(d)
    for _ in range(60):
        if fc < fd:
            b, d, fd = d, c, fc
            c = b - g * (b - a)
            fc = f(c)
        else:
            a, c, fc = c, d, fd
            d = a + g * (b - a)
            fd = f(d)
    t = (a + b) / 2
    p = evaluar_primitiva(prim, t)[0]
    return t, math.dist(p, q), p


def distancia_primitiva(prim, q):
    """Distancia de un punto (u, v) a una primitiva."""
    return mas_cercano(prim, q)[1]


def caja_primitiva(prim):
    pts = puntos_primitiva(prim, 32)
    if prim[0] == "spline":       # la curva queda dentro del polígono de control
        pts = list(pts) + [tuple(p) for p in prim[2]]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def intersecciones(pa, pb, tol=1e-7):
    """[(ta, tb, (x, y))] cruces entre dos primitivas, dentro de sus dominios. Muestreo + Newton."""
    a0, a1, per_a = dominio(pa)
    b0, b1, per_b = dominio(pb)
    ta, A = _muestras(pa)
    tb, B = _muestras(pb)
    A, B = np.array(A), np.array(B)
    p0, p1, q0, q1 = A[:-1][:, None, :], A[1:][:, None, :], B[:-1][None, :, :], B[1:][None, :, :]
    r, s, w = p1 - p0, q1 - q0, q0 - p0
    den = r[..., 0] * s[..., 1] - r[..., 1] * s[..., 0]
    with np.errstate(divide="ignore", invalid="ignore"):
        u = (w[..., 0] * s[..., 1] - w[..., 1] * s[..., 0]) / den
        v = (w[..., 0] * r[..., 1] - w[..., 1] * r[..., 0]) / den
    m = (np.abs(den) > 1e-18) & (u >= -1e-6) & (u <= 1 + 1e-6) & (v >= -1e-6) & (v <= 1 + 1e-6)
    salida = []
    for i, j in zip(*np.nonzero(m), strict=True):
        x = ta[i] + float(u[i, j]) * (ta[i + 1] - ta[i])
        y = tb[j] + float(v[i, j]) * (tb[j + 1] - tb[j])
        for _ in range(30):
            Ca, Da = evaluar_primitiva(pa, x, 1)
            Cb, Db = evaluar_primitiva(pb, y, 1)
            F = (Ca[0] - Cb[0], Ca[1] - Cb[1])
            if abs(F[0]) + abs(F[1]) < 1e-13:
                break
            det = -Da[0] * Db[1] + Db[0] * Da[1]
            if abs(det) < 1e-18:
                break
            dx = (-F[0] * Db[1] + Db[0] * F[1]) / det
            dy = (Da[0] * F[1] - Da[1] * F[0]) / det
            x, y = x - dx, y - dy
        Ca, Cb = evaluar_primitiva(pa, x)[0], evaluar_primitiva(pb, y)[0]
        if math.dist(Ca, Cb) > tol:
            continue
        if per_a:
            x %= _DOS_PI
        if per_b:
            y %= _DOS_PI
        ea, eb = 1e-9 * (a1 - a0), 1e-9 * (b1 - b0)
        if not (a0 - ea <= x <= a1 + ea and b0 - eb <= y <= b1 + eb):
            continue
        x, y = min(max(x, a0), a1), min(max(y, b0), b1)
        if not any(math.dist(Ca, xy) < 1e-7 for _, _, xy in salida):
            salida.append((x, y, Ca))
    return salida


def recta_interseccion(a1, d1, a2, d2):
    """Cruce de dos rectas (punto, dirección). None si son paralelas."""
    den = d1[0] * d2[1] - d1[1] * d2[0]
    if abs(den) < 1e-12:
        return None
    t = ((a2[0] - a1[0]) * d2[1] - (a2[1] - a1[1]) * d2[0]) / den
    return a1[0] + t * d1[0], a1[1] + t * d1[1]


def _cruces_recta_circulo(a, d, c, r):
    """Cruces de la recta (a, d unitario) con la circunferencia (c, r)."""
    fx, fy = a[0] - c[0], a[1] - c[1]
    b = fx * d[0] + fy * d[1]
    disc = b * b - (fx * fx + fy * fy - r * r)
    if disc < -1e-12:
        return []
    raiz = math.sqrt(max(disc, 0.0))
    return [(a[0] + t * d[0], a[1] + t * d[1]) for t in {-b - raiz, -b + raiz}]


def _cruces_circulos(c1, r1, c2, r2):
    d = math.dist(c1, c2)
    if d < 1e-12 or d > r1 + r2 + 1e-12 or d < abs(r1 - r2) - 1e-12:
        return []
    a = (r1 * r1 - r2 * r2 + d * d) / (2 * d)
    h = math.sqrt(max(r1 * r1 - a * a, 0.0))
    ux, uy = (c2[0] - c1[0]) / d, (c2[1] - c1[1]) / d
    m = (c1[0] + a * ux, c1[1] + a * uy)
    return [(m[0] - h * uy, m[1] + h * ux), (m[0] + h * uy, m[1] - h * ux)]


@lru_cache(maxsize=256)
def _contornos_texto(texto, fuente, altura, negrita, cursiva, opciones=(0.0, 1.0, "izq", "base", 0.0, False, False)):
    from ..nucleo.perfiles import contornos_texto      # fontTools / OpenCascade solo hacen falta para el texto
    espaciado, interlineado, alineacion, ancla_v, ancho_caja, voltear_h, voltear_v = opciones
    try:
        return tuple(contornos_texto(texto, fuente, altura, negrita, cursiva, espaciado=espaciado,
                                     interlineado=interlineado, alineacion=alineacion, ancla_v=ancla_v,
                                     ancho_caja=ancho_caja, voltear_h=voltear_h, voltear_v=voltear_v))
    except Exception:  # noqa: BLE001 — una fuente rota no debe romper el boceto
        return ()


@lru_cache(maxsize=128)
def _contornos_camino(texto, fuente, altura, negrita, cursiva, espaciado, alineacion, pos, lado, desfase, ajustar,
                      camino):
    from ..nucleo.fuentes import contornos_en_camino
    try:
        return tuple(contornos_en_camino(texto, camino, fuente, altura, negrita, cursiva, espaciado=espaciado,
                                         alineacion=alineacion, posicion=pos, lado=lado, desfase=desfase,
                                         ajustar=ajustar))
    except Exception:  # noqa: BLE001 — una fuente rota o un camino degenerado no deben romper el boceto
        return ()


def polilinea_camino(prim, pasos=720):
    """Polilínea densa de una curva para apoyar texto (redondeada a 1e-9 para que sirva de clave de caché)."""
    return tuple((round(float(x), 9), round(float(y), 9)) for x, y in puntos_primitiva(prim, pasos))


def fraccion_en_camino(prim, q):
    """Fracción 0-1 del largo de la curva en el punto más cercano a `q` (para ubicar un texto donde se hizo clic)."""
    pts = np.asarray(polilinea_camino(prim), float)
    tramos = np.hypot(*np.diff(pts, axis=0).T)
    acum = np.concatenate([[0.0], np.cumsum(tramos)])
    if acum[-1] < 1e-12:
        return 0.5
    i = int(np.argmin(np.hypot(pts[:, 0] - q[0], pts[:, 1] - q[1])))
    return float(acum[i] / acum[-1])


def primitivas_entidad(c, P, R=None, curvas=None):
    """Primitivas 2D de una curva. `P(pid)` → (u, v); `R(cid)` → radio del círculo o radio menor de la
    elipse (por defecto, el guardado). El solver pasa sus propios accesores. `curvas` (las del boceto) hace
    falta para el texto en curva; sin ellas, el texto se dibuja recto."""
    if R is None:
        R = lambda _cid: c.radio if isinstance(c, Circulo) else c.radio_menor  # noqa: E731
    if isinstance(c, Linea):
        return [("linea", c.id, P(c.p1), P(c.p2))]
    if isinstance(c, Circulo):
        return [("circulo", c.id, P(c.centro), R(c.id))]
    if isinstance(c, Arco):
        (cx, cy), (sx, sy), (ex, ey) = P(c.centro), P(c.inicio), P(c.fin)
        return [("arco", c.id, (cx, cy), math.hypot(sx - cx, sy - cy),
                 math.atan2(sy - cy, sx - cx), math.atan2(ey - cy, ex - cx))]
    if isinstance(c, (Elipse, ArcoElipse)):
        (cx, cy), (mx, my) = P(c.centro), P(c.mayor)
        a, ang, b = math.hypot(mx - cx, my - cy), math.atan2(my - cy, mx - cx), R(c.id)
        if isinstance(c, Elipse):
            return [("elipse", c.id, (cx, cy), a, b, ang)]
        t0 = parametro_elipse((cx, cy), a, b, ang, P(c.inicio))
        t1 = parametro_elipse((cx, cy), a, b, ang, P(c.fin))
        return [("arco_elipse", c.id, (cx, cy), a, b, ang, t0, t1)]
    if isinstance(c, Spline):
        pts = [P(p) for p in c.pts]
        if c.modo == "ajuste":
            polos, nudos, p = interpolar_spline(pts, c.grado, c.cerrada)
            return [("spline", c.id, tuple(polos), tuple(nudos), p, None)]
        p = min(c.grado, len(pts) - 1)
        nudos = c.nudos if c.nudos is not None and len(c.nudos) == len(pts) + p + 1 else nudos_uniformes(len(pts), p)
        return [("spline", c.id, tuple(pts), tuple(nudos), p, tuple(c.pesos) if c.pesos else None)]
    if isinstance(c, Conica):
        w = c.rho / (1 - c.rho)
        return [("spline", c.id, (P(c.inicio), P(c.vertice), P(c.fin)), (0.0, 0.0, 0.0, 1.0, 1.0, 1.0), 2,
                 (1.0, w, 1.0))]
    if isinstance(c, Texto) and c.camino is not None and curvas is not None and c.camino != c.id \
            and not isinstance(curvas.get(c.camino, c), Texto):
        base = primitivas_entidad(curvas[c.camino], P)      # radios guardados (el solver no pide textos)
        if base:
            return [(p[0], c.id) + tuple(p[2:]) for p in _contornos_camino(
                c.texto, c.fuente, c.altura, c.negrita, c.cursiva, c.espaciado, c.alineacion, c.camino_pos,
                c.camino_lado, c.camino_desfase, c.camino_ajustar, polilinea_camino(base[0]))]
    if isinstance(c, Texto):
        ox, oy = P(c.punto)
        ang = math.radians(c.angulo)
        T = lambda q: (lambda r: (r[0] + ox, r[1] + oy))(_rot(q[0], q[1], ang))  # noqa: E731
        salida = []
        for prim in _contornos_texto(c.texto, c.fuente, c.altura, c.negrita, c.cursiva, c.opciones_contorno()):
            if prim[0] == "linea":
                salida.append(("linea", c.id, T(prim[2]), T(prim[3])))
            else:
                salida.append(("spline", c.id, tuple(T(q) for q in prim[2]), prim[3], prim[4], prim[5]))
        return salida
    return []


_FX = re.compile(r"\{([^{}]*)\}")


def _partes_fx(contenido):
    expresion, _, formato = contenido.partition(":")
    return expresion.strip(), formato.strip()


def expresiones_de_texto(texto):
    """Expresiones que lleva un texto entre llaves: «Ancho {ancho}» → ['ancho']; «{largo / 2:.1f}» → ['largo / 2']."""
    return [e for e, _f in (_partes_fx(m.group(1)) for m in _FX.finditer(str(texto))) if e]


def sustituir_expresiones(texto, valor):
    """Reemplaza cada {expresión} (o {expresión:formato}) por el número que devuelve `valor(expresión)`.
    Sin formato, hasta 4 decimales y sin ceros de más; con formato, el de Python (`.1f`, `05.0f`…).
    Lo que `valor` no pueda calcular lo deja `valor` (lanza); el que llama decide qué hacer con el error."""
    def reemplazo(m):
        expresion, formato = _partes_fx(m.group(1))
        if not expresion:
            return m.group(0)
        v = float(valor(expresion))
        if formato:
            return format(v, formato)
        s = f"{v:.4f}".rstrip("0").rstrip(".")
        return "0" if s in ("", "-0") else s
    return _FX.sub(reemplazo, str(texto))


_ORIENTADAS = ("horizontal", "vertical")
_COTAS_ORIENTADAS = ("distancia_h", "distancia_v")


def _cambia_orientacion(angulo):
    """True si un giro de `angulo` grados deja de respetar horizontales y verticales (no es múltiplo de 180°)."""
    resto = float(angulo) % 180.0
    return min(resto, 180.0 - resto) > 1e-9


def _validar_opciones_texto(op):
    """Opciones del Texto: claves conocidas, números finitos y valores de lista válidos."""
    desconocidas = set(op) - set(Texto._PREDETERMINADOS)
    if desconocidas:
        raise ErrorBoceto(f"Opciones de texto desconocidas: {', '.join(sorted(desconocidas))}.")
    for k in ("espaciado", "interlineado", "ancho_caja"):
        if k in op and not math.isfinite(float(op[k])):
            raise ErrorBoceto(f"«{k}» tiene que ser un número finito.")
    if "interlineado" in op and float(op["interlineado"]) <= 0:
        raise ErrorBoceto("El interlineado tiene que ser mayor que cero.")
    if "ancho_caja" in op and float(op["ancho_caja"]) < 0:
        raise ErrorBoceto("El ancho de la caja no puede ser negativo.")
    if op.get("alineacion", "izq") not in ("izq", "centro", "der"):
        raise ErrorBoceto("La alineación es izq, centro o der.")
    if op.get("ancla_v", "base") not in ("base", "arriba", "medio", "abajo"):
        raise ErrorBoceto("El anclaje vertical es base, arriba, medio o abajo.")
    if op.get("camino_lado", "izq") not in ("izq", "der"):
        raise ErrorBoceto("El lado del texto en curva es izq o der.")
    for k in ("camino_pos", "camino_desfase"):
        if k in op and not math.isfinite(float(op[k])):
            raise ErrorBoceto(f"«{k}» tiene que ser un número finito.")


# ---------------------------------------------------------------- boceto
class Boceto:
    def __init__(self):
        self.puntos = {}
        self.curvas = {}
        self.restricciones = {}
        self.cotas = {}
        self._siguiente = 1

    # ------------------------------------------------------------ ids
    def _nuevo_id(self):
        i = self._siguiente
        self._siguiente += 1
        return i

    def entidad(self, id):
        if id in self.puntos:
            return self.puntos[id]
        if id in self.curvas:
            return self.curvas[id]
        raise ErrorBoceto(f"No existe la entidad {id}.")

    def copia(self):
        """Copia independiente. Más rápida que deepcopy: los puntos y las curvas solo tienen números, textos y
        listas de números (lo que se copia aparte)."""
        b = copy.copy(self)
        b.puntos = {k: copy.copy(p) for k, p in self.puntos.items()}
        b.curvas = {}
        for k, c in self.curvas.items():
            n = copy.copy(c)
            for a, v in vars(c).items():
                if isinstance(v, (list, dict, set)):
                    setattr(n, a, copy.deepcopy(v))
            b.curvas[k] = n
        b.restricciones = copy.deepcopy(self.restricciones)
        b.cotas = copy.deepcopy(self.cotas)
        for a, v in vars(self).items():
            if a not in ("puntos", "curvas", "restricciones", "cotas") and isinstance(v, (list, dict, set)):
                setattr(b, a, copy.deepcopy(v))
        return b

    # ------------------------------------------------------------ creación
    def agregar_punto(self, x, y, proyectado=False):
        if not (math.isfinite(x) and math.isfinite(y)):     # con NaN o infinito, OCC no termina de partir la cara
            raise ErrorBoceto("Las coordenadas de un punto tienen que ser números finitos.")
        p = Punto(self._nuevo_id(), x, y, proyectado)
        self.puntos[p.id] = p
        return p.id

    def _punto(self, p):
        """Acepta un id de punto existente o una tupla (x, y) para crear uno nuevo."""
        if isinstance(p, (int, np.integer)) and not isinstance(p, bool):
            if int(p) not in self.puntos:
                raise ErrorBoceto(f"No existe el punto {p}.")
            return int(p)
        return self.agregar_punto(*p)

    def _agregar_curva(self, c):
        self.curvas[c.id] = c
        return c.id

    def agregar_linea(self, a, b, construccion=False, eje=False):
        p1, p2 = self._punto(a), self._punto(b)
        if p1 == p2:
            raise ErrorBoceto("Una línea necesita dos puntos distintos.")
        return self._agregar_curva(Linea(self._nuevo_id(), p1, p2, construccion, eje))

    def agregar_rectangulo(self, a, b, construccion=False):
        """Rectángulo por dos esquinas opuestas → 4 líneas + 2 horizontales + 2 verticales."""
        (x1, y1), (x2, y2) = a, b
        if abs(x2 - x1) < 1e-9 or abs(y2 - y1) < 1e-9:
            raise ErrorBoceto("El rectángulo no puede tener ancho o alto cero.")
        esquinas = [self.agregar_punto(x1, y1), self.agregar_punto(x2, y1),
                    self.agregar_punto(x2, y2), self.agregar_punto(x1, y2)]
        lineas = [self.agregar_linea(esquinas[i], esquinas[(i + 1) % 4], construccion) for i in range(4)]
        self.agregar_restriccion("horizontal", [lineas[0]])
        self.agregar_restriccion("horizontal", [lineas[2]])
        self.agregar_restriccion("vertical", [lineas[1]])
        self.agregar_restriccion("vertical", [lineas[3]])
        return lineas

    def agregar_circulo(self, centro, radio, construccion=False):
        if not 0 < radio < math.inf:                        # también NaN
            raise ErrorBoceto("El radio debe ser positivo y finito.")
        return self._agregar_curva(Circulo(self._nuevo_id(), self._punto(centro), radio, construccion))

    def agregar_arco_centro(self, centro, inicio, fin, construccion=False):
        a = Arco(self._nuevo_id(), self._punto(centro), self._punto(inicio), self._punto(fin), construccion)
        return self._agregar_curva(a)

    def agregar_arco_3_puntos(self, inicio, medio, fin, construccion=False):
        """Arco por inicio, un punto intermedio y fin (como `SketchArcs.addByThreePoints`)."""
        pi = self.coords(inicio) if isinstance(inicio, int) else inicio
        pf = self.coords(fin) if isinstance(fin, int) else fin
        c = circunferencia_3_puntos(pi, medio, pf)
        if c is None:
            raise ErrorBoceto("Los tres puntos están alineados: no definen un arco.")
        cx, cy, _ = c
        if not _antihorario_por(pi, medio, pf, (cx, cy)):
            inicio, fin = fin, inicio
        return self.agregar_arco_centro((cx, cy), inicio, fin, construccion)

    def agregar_elipse(self, centro, mayor, radio_menor, construccion=False, ejes=True):
        """Elipse por centro, extremo del eje mayor y radio menor (SKT-CREATE-ELLIPSE). Como Fusion,
        agrega sus ejes mayor y menor de construcción, con el centro en el punto medio de ambos."""
        c, m = self._punto(centro), self._punto(mayor)
        (cx, cy), (mx, my) = self.coords(c), self.coords(m)
        a = math.hypot(mx - cx, my - cy)
        if a < 1e-9 or not 1e-9 < radio_menor < math.inf:    # también NaN
            raise ErrorBoceto("La elipse necesita ejes de largo positivo.")
        eid = self._agregar_curva(Elipse(self._nuevo_id(), c, m, radio_menor, construccion))
        if ejes:
            ux, uy = (mx - cx) / a, (my - cy) / a
            b = radio_menor
            mayor = self.agregar_linea((cx - a * ux, cy - a * uy), m, True)
            menor = self.agregar_linea((cx + b * uy, cy - b * ux), (cx - b * uy, cy + b * ux), True)
            self.agregar_restriccion("punto_medio", [c, mayor])
            self.agregar_restriccion("punto_medio", [c, menor])
            self.agregar_restriccion("perpendicular", [mayor, menor])
            self.agregar_restriccion("coincidente", [self.curvas[menor].p2, eid])
        return eid

    def agregar_spline(self, puntos, modo="ajuste", grado=3, cerrada=False, pesos=None, nudos=None,
                       construccion=False):
        """Spline de ajuste de puntos o de puntos de control (SKT-CREATE-SPLINES)."""
        ids = []
        for p in puntos:
            i = self._punto(p)
            if not ids or i != ids[-1]:
                ids.append(i)
        if cerrada and len(ids) > 1 and ids[-1] == ids[0]:
            ids.pop()
        if len(ids) < 2 or (cerrada and len(ids) < 3):
            raise ErrorBoceto("La spline necesita más puntos.")
        primero = self.coords(ids[0])
        if all(math.dist(primero, self.coords(i)) < 1e-9 for i in ids[1:]):
            raise ErrorBoceto("Los puntos de la spline coinciden: no definen una curva.")
        if modo not in ("ajuste", "control"):
            raise ErrorBoceto(f"Tipo de spline desconocido: {modo}")
        return self._agregar_curva(Spline(self._nuevo_id(), ids, modo, grado, cerrada if modo == "ajuste" else False,
                                          pesos, nudos, construccion))

    def agregar_conica(self, inicio, vertice, fin, rho=0.5, construccion=False):
        """Curva cónica por sus extremos, el vértice y Rho (SKT-CREATE-CONIC-CURVE)."""
        if not 0 < rho < 1:
            raise ErrorBoceto("Rho tiene que estar entre 0 y 1.")
        a, v, b = self._punto(inicio), self._punto(vertice), self._punto(fin)
        if abs(distancia_punto_recta(self.coords(v), self.coords(a), self.coords(b))) < 1e-9:
            raise ErrorBoceto("El vértice no puede estar alineado con los extremos.")
        return self._agregar_curva(Conica(self._nuevo_id(), a, v, b, rho, construccion))

    def agregar_texto(self, posicion, texto, altura=5.0, angulo=0.0, fuente="Arial", negrita=False, cursiva=False,
                      **opciones):
        """Texto en el boceto (SKT-CREATE-TEXT): sus contornos dan perfiles para extruir. `opciones`: espaciado,
        interlineado, alineacion, ancla_v, ancho_caja, voltear_h, voltear_v (ver `Texto`)."""
        if not str(texto).strip():
            raise ErrorBoceto("El texto está vacío.")
        if not 0 < altura < math.inf:                       # también NaN
            raise ErrorBoceto("La altura del texto debe ser positiva.")
        _validar_opciones_texto(opciones)
        self._validar_camino(opciones.get("camino"))
        return self._agregar_curva(Texto(self._nuevo_id(), self._punto(posicion), texto, fuente, altura, angulo,
                                         negrita, cursiva, **opciones))

    def _validar_camino(self, camino):
        """El camino de un texto en curva tiene que ser una curva del boceto que no sea otro texto."""
        if camino is None:
            return
        c = self.curvas.get(camino)
        if c is None or isinstance(c, Texto):
            raise ErrorBoceto(f"El camino del texto tiene que ser una curva del boceto (no un texto): {camino}.")

    def agregar_ranura(self, tipo, puntos, ancho, construccion=False):
        """Ranuras de Fusion (SKT-CREATE-SLOTS), armadas con líneas y arcos tangentes:
        tipo "centro" (centro a centro), "total", "punto" (punto central), "arco_3p" y "arco_centro".
        `ancho` es el ancho total. Devuelve los ids de las curvas creadas."""
        w = ancho / 2
        if w <= 1e-9:
            raise ErrorBoceto("La ranura necesita un ancho.")
        coords = [self.coords(p) if isinstance(p, int) else (float(p[0]), float(p[1])) for p in puntos]
        if tipo in ("centro", "total", "punto"):
            if tipo == "punto":
                m, b = coords
                coords = [(2 * m[0] - b[0], 2 * m[1] - b[1]), b]
            a, b = coords
            L = math.dist(a, b)
            if tipo == "total":
                if L <= 2 * w + 1e-9:
                    raise ErrorBoceto("La ranura es más angosta que su ancho.")
                ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
                a, b = (a[0] + ux * w, a[1] + uy * w), (b[0] - ux * w, b[1] - uy * w)
            if math.dist(a, b) < 1e-9:
                raise ErrorBoceto("Los centros de la ranura coinciden.")
            pa = puntos[0] if tipo == "centro" and isinstance(puntos[0], int) else a
            pb = puntos[1] if tipo != "total" and isinstance(puntos[1], int) else b
            ids = self._ranura_lineal(pa, pb, w, construccion)
            if tipo == "punto":
                medio = puntos[0] if isinstance(puntos[0], int) else self.agregar_punto(*puntos[0])
                self.agregar_restriccion("punto_medio", [medio, ids[-1]])
            return ids
        if tipo == "arco_3p":
            a, b, q = coords
            circ = circunferencia_3_puntos(a, q, b)
            if circ is None:
                raise ErrorBoceto("Los tres puntos están alineados: no definen un arco.")
            centro = (circ[0], circ[1])
            if not _antihorario_por(a, q, b, centro):
                a, b = b, a
        elif tipo == "arco_centro":
            centro, a, b2 = coords
            R = math.dist(centro, a)
            ang = math.atan2(b2[1] - centro[1], b2[0] - centro[0])
            b = (centro[0] + R * math.cos(ang), centro[1] + R * math.sin(ang))
            a0 = math.atan2(a[1] - centro[1], a[0] - centro[0])
            if _barrido(a0, ang) > math.pi:
                a, b = b, a
        else:
            raise ErrorBoceto(f"Tipo de ranura desconocido: {tipo}")
        return self._ranura_arco(centro, a, b, w, construccion)

    def _ranura_lineal(self, a, b, w, construccion):
        pa, pb = self._punto(a), self._punto(b)
        (ax, ay), (bx, by) = self.coords(pa), self.coords(pb)
        L = math.hypot(bx - ax, by - ay)
        nx, ny = -(by - ay) / L * w, (bx - ax) / L * w
        q1, q2 = self.agregar_punto(ax + nx, ay + ny), self.agregar_punto(bx + nx, by + ny)
        q3, q4 = self.agregar_punto(bx - nx, by - ny), self.agregar_punto(ax - nx, ay - ny)
        l1 = self.agregar_linea(q1, q2, construccion)
        arco_b = self.agregar_arco_centro(pb, q3, q2, construccion)
        l2 = self.agregar_linea(q3, q4, construccion)
        arco_a = self.agregar_arco_centro(pa, q1, q4, construccion)
        eje = self.agregar_linea(pa, pb, True)
        for ln in (l1, l2):
            for arco in (arco_a, arco_b):
                self.agregar_restriccion("tangente", [ln, arco])
        self.agregar_restriccion("igual", [arco_a, arco_b])
        return [l1, arco_b, l2, arco_a, eje]

    def _ranura_arco(self, centro, a, b, w, construccion):
        C = self.agregar_punto(*centro)
        R = math.dist(centro, a)
        if R <= w + 1e-9:
            raise ErrorBoceto("El ancho de la ranura es mayor que el radio del arco.")
        pa, pb = self.agregar_punto(*a), self.agregar_punto(*b)

        def radial(q, r):
            return (centro[0] + (q[0] - centro[0]) * r / R, centro[1] + (q[1] - centro[1]) * r / R)
        oa, ob = self.agregar_punto(*radial(a, R + w)), self.agregar_punto(*radial(b, R + w))
        ia, ib = self.agregar_punto(*radial(a, R - w)), self.agregar_punto(*radial(b, R - w))
        afuera = self.agregar_arco_centro(C, oa, ob, construccion)
        adentro = self.agregar_arco_centro(C, ia, ib, construccion)
        tapa_b = self.agregar_arco_centro(pb, ob, ib, construccion)
        tapa_a = self.agregar_arco_centro(pa, ia, oa, construccion)
        eje = self.agregar_arco_centro(C, pa, pb, True)
        for k in (afuera, adentro):
            for tapa in (tapa_a, tapa_b):
                self.agregar_restriccion("tangente", [k, tapa])
        self.agregar_restriccion("igual", [tapa_a, tapa_b])
        return [afuera, tapa_b, adentro, tapa_a, eje]

    def agregar_circulo_tangente(self, lineas, ubicacion=None, radio=None, picks=None, construccion=False):
        """Círculo de 2 o 3 tangentes (SKT-CREATE-CIRCLES): se crea tangente a las líneas y se le
        agregan las restricciones de tangencia. Con 2 líneas, `ubicacion` elige el sector (y el
        tamaño, si no se da `radio`); con 3, `picks` elige entre el círculo inscrito y los exinscritos."""
        if len(lineas) not in (2, 3) or any(self.tipo_de(k) != "linea" for k in lineas):
            raise ErrorBoceto("Seleccioná dos o tres líneas.")
        datos = []
        for k in lineas:
            a, b = self._extremos_linea(k)
            L = math.dist(a, b)
            n = (-(b[1] - a[1]) / L, (b[0] - a[0]) / L)
            datos.append((n, n[0] * a[0] + n[1] * a[1], a, ((b[0] - a[0]) / L, (b[1] - a[1]) / L)))
        if len(lineas) == 2:
            (n1, h1, a1, d1), (n2, h2, a2, d2) = datos
            q = ubicacion or ((a1[0] + a2[0]) / 2, (a1[1] + a2[1]) / 2)
            s1 = 1.0 if n1[0] * q[0] + n1[1] * q[1] - h1 >= 0 else -1.0
            s2 = 1.0 if n2[0] * q[0] + n2[1] * q[1] - h2 >= 0 else -1.0
            if abs(n1[0] * n2[1] - n1[1] * n2[0]) < 1e-9:         # paralelas: el círculo va entre las dos
                ancho = abs(n1[0] * a2[0] + n1[1] * a2[1] - h1)
                r = ancho / 2
                medio = s1 * (n1[0] * q[0] + n1[1] * q[1] - h1) - r
                centro = (q[0] - s1 * n1[0] * medio, q[1] - s1 * n1[1] * medio)
            elif radio is not None:
                M = np.array([[s1 * n1[0], s1 * n1[1]], [s2 * n2[0], s2 * n2[1]]])
                centro = tuple(np.linalg.solve(M, [radio + s1 * h1, radio + s2 * h2]))
                r = radio
            else:
                g = (s1 * n1[0] - s2 * n2[0], s1 * n1[1] - s2 * n2[1])
                k = s1 * h1 - s2 * h2
                g2 = g[0] ** 2 + g[1] ** 2
                e = (g[0] * q[0] + g[1] * q[1] - k) / g2
                centro = (q[0] - g[0] * e, q[1] - g[1] * e)
                r = s1 * (n1[0] * centro[0] + n1[1] * centro[1] - h1)
        else:
            mejor = None
            for s in ((1, 1, 1), (1, 1, -1), (1, -1, 1), (-1, 1, 1), (1, -1, -1), (-1, 1, -1), (-1, -1, 1),
                      (-1, -1, -1)):
                M = np.array([[si * n[0], si * n[1], -1.0] for si, (n, *_r) in zip(s, datos, strict=True)])
                try:
                    cx, cy, rr = np.linalg.solve(M, [si * h for si, (_n, h, *_r) in zip(s, datos, strict=True)])
                except np.linalg.LinAlgError:
                    continue
                if rr <= 1e-9:
                    continue
                pies = [(cx - rr * si * n[0], cy - rr * si * n[1]) for si, (n, *_r) in zip(s, datos, strict=True)]
                if picks:
                    puntaje = sum(math.dist(p, q) for p, q in zip(pies, picks, strict=True))
                else:
                    puntaje = rr
                if mejor is None or puntaje < mejor[0]:
                    mejor = (puntaje, (cx, cy), rr)
            if mejor is None:
                raise ErrorBoceto("No hay un círculo tangente a esas tres líneas.")
            _, centro, r = mejor
        if r <= 1e-9:
            raise ErrorBoceto("Ubicá el círculo dentro del ángulo que forman las líneas.")
        cid = self.agregar_circulo((float(centro[0]), float(centro[1])), float(r), construccion)
        for k in lineas:
            self.agregar_restriccion("tangente", [k, cid])
        return cid

    def agregar_proyeccion(self, primitivas, puntos=()):
        """Agrega geometría proyectada (Proyectar / Intersecar de Fusion): curvas violetas, fijas.
        Los extremos que coinciden se comparten para que cierren perfiles."""
        existentes = [p for p in self.puntos.values() if p.proyectado]

        def punto(xy):
            for p in existentes:
                if math.hypot(p.x - xy[0], p.y - xy[1]) < 1e-6:
                    return p.id
            pid = self.agregar_punto(xy[0], xy[1], proyectado=True)
            existentes.append(self.puntos[pid])
            return pid
        ids = []
        lineas = {frozenset(c.puntos()) for c in self.curvas.values() if c.proyectada and isinstance(c, Linea)}
        for prim in primitivas:
            t = prim[0]
            if t == "linea":
                if math.dist(prim[2], prim[3]) < 1e-9:
                    continue
                extremos = frozenset((punto(prim[2]), punto(prim[3])))
                if extremos in lineas:        # dos aristas que se proyectan sobre la misma línea: una sola
                    continue
                lineas.add(extremos)
                c = Linea(self._nuevo_id(), punto(prim[2]), punto(prim[3]), proyectada=True)
            elif t == "circulo":
                c = Circulo(self._nuevo_id(), punto(prim[2]), prim[3], proyectada=True)
            elif t == "arco":
                (cx, cy), r = prim[2], prim[3]
                c = Arco(self._nuevo_id(), punto((cx, cy)), punto((cx + r * math.cos(prim[4]), cy + r * math.sin(prim[4]))),
                         punto((cx + r * math.cos(prim[5]), cy + r * math.sin(prim[5]))), proyectada=True)
            elif t in ELIPTICAS:
                (cx, cy), a, b, ang = prim[2], prim[3], prim[4], prim[5]
                centro, mayor = punto((cx, cy)), punto((cx + a * math.cos(ang), cy + a * math.sin(ang)))
                if t == "elipse":
                    c = Elipse(self._nuevo_id(), centro, mayor, b, proyectada=True)
                else:
                    p0, p1 = evaluar_primitiva(prim, 0.0)[0], evaluar_primitiva(prim, dominio(prim)[1])[0]
                    c = ArcoElipse(self._nuevo_id(), centro, mayor, b, punto(p0), punto(p1), proyectada=True)
            elif t == "spline":
                polos = [punto(q) for q in prim[2]]
                c = Spline(self._nuevo_id(), polos, "control", prim[4], False, prim[5], prim[3], proyectada=True)
            else:
                continue
            ids.append(self._agregar_curva(c))
        for xy in puntos:
            ids.append(punto(xy))
        return ids

    def agregar_restriccion(self, tipo, entidades, datos=None):
        self._validar_restriccion(tipo, entidades)
        r = Restriccion(self._nuevo_id(), tipo, entidades, datos)
        self.restricciones[r.id] = r
        return r.id

    def agregar_cota(self, tipo, entidades, expresion, datos=None):
        datos = dict(datos or {})
        self._validar_cota(tipo, entidades)
        if tipo in ("distancia_h", "distancia_v") and "signo" not in datos:
            (x1, y1), (x2, y2) = self._extremos_cota(entidades)
            d = (x2 - x1) if tipo == "distancia_h" else (y2 - y1)
            datos["signo"] = 1.0 if d >= 0 else -1.0
        c = Cota(self._nuevo_id(), tipo, entidades, expresion, datos)
        self.cotas[c.id] = c
        return c.id

    # ------------------------------------------------------------ borrado
    def eliminar(self, id):
        """Borra una entidad, restricción o cota, y en cascada lo que dependa de ella."""
        if id in self.restricciones:
            del self.restricciones[id]
            return
        if id in self.cotas:
            del self.cotas[id]
            return
        if id in self.curvas:
            curva = self.curvas.pop(id)
            for p in curva.puntos():
                if not self._punto_en_uso(p):
                    self.puntos.pop(p, None)
        elif id in self.puntos:
            for cid in [c.id for c in self.curvas.values() if id in c.puntos()]:
                self.curvas.pop(cid)
            del self.puntos[id]
        else:
            raise ErrorBoceto(f"No existe el elemento {id}.")
        self._quitar_huerfanas()

    def _quitar_huerfanas(self):
        vivos = set(self.puntos) | set(self.curvas)
        for c in self.curvas.values():
            if isinstance(c, Texto) and c.camino is not None and c.camino not in self.curvas:
                c.camino = None                            # se borró su curva: vuelve a ser texto recto
        for tabla in (self.restricciones, self.cotas):
            for k in [k for k, v in tabla.items() if not set(v.entidades) <= vivos]:
                del tabla[k]

    def _depurar(self, puntos_viejos=()):
        """Tras modificar geometría: borra los puntos viejos que quedaron sueltos y las restricciones o
        cotas que ya no aplican al nuevo tipo de las entidades."""
        for p in puntos_viejos:
            if p in self.puntos and not self._punto_en_uso(p) and not self._punto_referenciado(p):
                del self.puntos[p]
        self._quitar_huerfanas()
        for rid in list(self.restricciones):
            r = self.restricciones[rid]
            try:
                self._validar_restriccion(r.tipo, r.entidades)
            except ErrorBoceto:
                del self.restricciones[rid]
        for kid in list(self.cotas):
            k = self.cotas[kid]
            try:
                self._validar_cota(k.tipo, k.entidades)
            except ErrorBoceto:
                del self.cotas[kid]

    def _punto_en_uso(self, pid):
        return any(pid in c.puntos() for c in self.curvas.values())

    def _punto_referenciado(self, pid):
        return any(pid in r.entidades for r in self.restricciones.values()) or \
            any(pid in k.entidades for k in self.cotas.values())

    # ------------------------------------------------------------ consultas
    def coords(self, pid):
        p = self.puntos[pid]
        return (p.x, p.y)

    def radio(self, cid):
        c = self.curvas[cid]
        if isinstance(c, Circulo):
            return c.radio
        if isinstance(c, (Elipse, ArcoElipse)):
            return c.radio_menor
        (cx, cy), (sx, sy) = self.coords(c.centro), self.coords(c.inicio)
        return math.hypot(sx - cx, sy - cy)

    def tipo_de(self, id):
        return self.entidad(id).tipo

    def extremos(self, cid):
        return self.curvas[cid].extremos()

    def puntos_fijos(self):
        """Puntos inmóviles: por una restricción 'fijo' (sobre el punto o su curva) o por ser proyectados."""
        fijos = {p.id for p in self.puntos.values() if p.proyectado}
        for c in self.curvas.values():
            if c.proyectada:
                fijos.update(c.puntos())
        for r in self.restricciones.values():
            if r.tipo == "fijo":
                for e in r.entidades:
                    fijos.update([e] if e in self.puntos else self.curvas[e].puntos())
        return fijos

    def puntos_de(self, ids):
        """Puntos usados por las curvas de `ids` más los puntos sueltos de `ids`."""
        salida = []
        for i in ids:
            for p in ([i] if i in self.puntos else self.curvas[i].puntos() if i in self.curvas else []):
                if p not in salida:
                    salida.append(p)
        return salida

    def _extremos_cota(self, entidades):
        if len(entidades) == 2:
            return self.coords(entidades[0]), self.coords(entidades[1])
        ln = self.curvas[entidades[0]]
        return self.coords(ln.p1), self.coords(ln.p2)

    def separacion(self, original, desfasada):
        """Distancia entre una curva y su desfase (líneas paralelas o círculos/arcos concéntricos)."""
        o, d = self.curvas[original], self.curvas[desfasada]
        if isinstance(o, Linea):
            return abs(distancia_punto_recta(self.coords(d.p1), *self._extremos_linea(o.id)))
        return abs(self.radio(d.id) - self.radio(o.id))

    def medir_cota(self, tipo, entidades):
        """Valor actual (mm o grados) de una cota sobre la geometría actual: sirve de valor por defecto."""
        t = [self.tipo_de(e) for e in entidades]
        if tipo in ("radio", "diametro"):
            r = self.radio(entidades[0])
            return r if tipo == "radio" else 2 * r
        if tipo == "desfase":
            return self.separacion(*entidades)
        if tipo == "angulo":
            d1, d2 = (self._direccion(e) for e in entidades)
            return math.degrees(math.atan2(abs(d1[0] * d2[1] - d1[1] * d2[0]), d1[0] * d2[0] + d1[1] * d2[1]))
        if tipo == "distancia" and t == ["punto", "linea"]:
            return abs(distancia_punto_recta(self.coords(entidades[0]), *self._extremos_linea(entidades[1])))
        if tipo == "distancia" and t == ["linea", "linea"]:
            a = self.coords(self.curvas[entidades[1]].p1)
            return abs(distancia_punto_recta(a, *self._extremos_linea(entidades[0])))
        (x1, y1), (x2, y2) = self._extremos_cota(entidades)
        if tipo == "distancia_h":
            return abs(x2 - x1)
        if tipo == "distancia_v":
            return abs(y2 - y1)
        return math.hypot(x2 - x1, y2 - y1)

    def _extremos_linea(self, lid):
        ln = self.curvas[lid]
        return self.coords(ln.p1), self.coords(ln.p2)

    def _direccion(self, lid):
        (x1, y1), (x2, y2) = self._extremos_linea(lid)
        n = math.hypot(x2 - x1, y2 - y1) or 1.0
        return ((x2 - x1) / n, (y2 - y1) / n)

    def extremo_comun(self, a, b):
        """(punto de a, punto de b) donde se tocan dos curvas por sus extremos (el mismo punto o dos puntos
        con restricción coincidente); None si no comparten un extremo."""
        ea, eb = self.curvas[a].extremos(), self.curvas[b].extremos()
        if not ea or not eb:
            return None
        for p in ea:
            if p in eb:
                return p, p
        for r in self.restricciones.values():
            if r.tipo == "coincidente" and len(r.entidades) == 2:
                p, q = r.entidades
                if p in ea and q in eb:
                    return p, q
                if q in ea and p in eb:
                    return q, p
        return None

    def vertices_cadena(self, lineas):
        """Vértices en orden de una cadena CERRADA de líneas (para la restricción de polígono)."""
        lados = [tuple(self.curvas[k].puntos()) for k in lineas]
        orden = [lados[0][0], lados[0][1]]
        usados = {0}
        while len(usados) < len(lados):
            sig = next((i for i, (p, q) in enumerate(lados) if i not in usados and orden[-1] in (p, q)), None)
            if sig is None:
                raise ErrorBoceto("Las líneas del polígono deben formar una cadena cerrada.")
            p, q = lados[sig]
            orden.append(q if p == orden[-1] else p)
            usados.add(sig)
        if orden[-1] != orden[0]:
            raise ErrorBoceto("Las líneas del polígono deben formar una cadena cerrada.")
        return orden[:-1]

    # ------------------------------------------------------------ validación
    def _validar_restriccion(self, tipo, entidades):
        t = [self.tipo_de(e) for e in entidades]
        abiertas = ("linea", "arco", "arco_elipse", "spline", "conica")
        validas = {
            "coincidente": lambda: len(t) == 2 and t[0] == "punto" and t[1] in ("punto",) + GEOMETRICAS,
            "horizontal": lambda: (t == ["linea"] or t == ["punto", "punto"]),
            "vertical": lambda: (t == ["linea"] or t == ["punto", "punto"]),
            "paralela": lambda: t == ["linea", "linea"],
            "perpendicular": lambda: t == ["linea", "linea"],
            "igual": lambda: (t == ["linea", "linea"] or (len(t) == 2 and t[0] in CIRCULARES and t[1] in CIRCULARES)
                              or (len(t) == 2 and t[0] in ELIPTICAS and t[1] in ELIPTICAS)),
            "tangente": lambda: (len(t) == 2 and t[0] in GEOMETRICAS and t[1] in GEOMETRICAS and t != ["linea", "linea"]),
            "concentrica": lambda: len(t) == 2 and t[0] in CON_CENTRO and t[1] in CON_CENTRO,
            "punto_medio": lambda: t in (["punto", "linea"], ["punto", "arco"]),
            "fijo": lambda: len(t) >= 1,
            "colineal": lambda: t == ["linea", "linea"],
            # Simetría (como en Fusion): dos puntos, líneas, círculos/arcos, elipses, cónicas o splines
            # (con la misma cantidad de puntos) respecto de una línea.
            "simetrica": lambda: (len(t) == 3 and t[2] == "linea" and
                                  (t[:2] in (["punto", "punto"], ["linea", "linea"], ["conica", "conica"])
                                   or (t[0] in CIRCULARES and t[1] in CIRCULARES)
                                   or (t[0] in ELIPTICAS and t[0] == t[1])
                                   or (t[:2] == ["spline", "spline"] and
                                       len(self.curvas[entidades[0]].pts) == len(self.curvas[entidades[1]].pts)))),
            # Curvatura (G2): una spline (o cónica) y otra curva encadenada (SKT-CONSTRAIN-CURVATURE).
            "curvatura": lambda: (len(t) == 2 and t[0] in abiertas and t[1] in abiertas
                                  and (t[0] in LIBRES or t[1] in LIBRES)),
            "poligono": lambda: len(t) >= 3 and all(x == "linea" for x in t),
            "desfase": lambda: ((len(t) == 4 and all(x in GEOMETRICAS for x in t))
                                or (len(t) == 3 and t[0] in GEOMETRICAS and t[1:] == ["punto", "punto"])),
            "patron": lambda: t in (["punto", "punto"], ["punto", "punto", "punto"]),
        }
        if not validas[tipo]():
            raise ErrorBoceto(f"La restricción '{TIPOS_RESTRICCION[tipo]}' no aplica a: {', '.join(t) or 'nada'}.")
        if len(set(entidades)) != len(entidades):
            raise ErrorBoceto("Seleccioná entidades distintas.")
        if tipo == "curvatura" and self.extremo_comun(*entidades) is None:
            raise ErrorBoceto("La curvatura se aplica a dos curvas encadenadas (que compartan un extremo).")
        if tipo == "poligono":
            self.vertices_cadena(entidades)

    def _validar_cota(self, tipo, entidades):
        t = [self.tipo_de(e) for e in entidades]
        validas = {
            "distancia": lambda: t in (["punto", "punto"], ["linea"], ["punto", "linea"], ["linea", "linea"]),
            "distancia_h": lambda: t in (["punto", "punto"], ["linea"]),
            "distancia_v": lambda: t in (["punto", "punto"], ["linea"]),
            "radio": lambda: t in (["circulo"], ["arco"]),
            "diametro": lambda: t in (["circulo"], ["arco"]),
            "angulo": lambda: t == ["linea", "linea"],
            "desfase": lambda: t == ["linea", "linea"] or (len(t) == 2 and t[0] in CIRCULARES and t[1] in CIRCULARES),
        }
        if not validas[tipo]():
            raise ErrorBoceto(f"La cota '{TIPOS_COTA[tipo]}' no aplica a: {', '.join(t) or 'nada'}.")

    # ------------------------------------------------------------ geometría para perfiles y dibujo
    def primitivas(self, cid):
        """Primitivas 2D de una curva (un texto da varias; las demás, una)."""
        return primitivas_entidad(self.curvas[cid], self.coords, curvas=self.curvas)

    def geometria(self, incluir_construccion=False):
        """Lista de primitivas 2D (formato de cada tupla):
          ('linea', id, (x1, y1), (x2, y2))
          ('circulo', id, (cx, cy), r)
          ('arco', id, (cx, cy), r, ang_ini, ang_fin)                 antihorario, radianes
          ('elipse', id, (cx, cy), a, b, ang)                          a: semieje de `mayor`, ang: su giro
          ('arco_elipse', id, (cx, cy), a, b, ang, t_ini, t_fin)       antihorario en el parámetro t
          ('spline', id, polos, nudos, grado, pesos)                   B-spline sujeta; pesos None = no racional
        Las splines de ajuste, las cónicas y los textos salen como 'spline' (y 'linea'); un texto da
        varias primitivas con el mismo id. La construcción se omite salvo que se pida; los ejes
        (líneas centrales) y la geometría proyectada sí forman perfiles."""
        salida = []
        for c in self.curvas.values():
            if c.construccion and not incluir_construccion:
                continue
            salida.extend(self.primitivas(c.id))
        return salida

    # ------------------------------------------------------------ cadenas y cortes
    def cadena(self, cid):
        """Curvas (líneas y arcos) conectadas por sus extremos a `cid`, en orden de recorrido, como la
        selección de cadena de Fusion: ([(id, invertida), ...], cerrada)."""
        c = self.curvas[cid]
        if not isinstance(c, (Linea, Arco)):
            return [(cid, False)], isinstance(c, (Circulo, Elipse))
        por_punto = {}
        for k in self.curvas.values():
            if isinstance(k, (Linea, Arco)) and k.construccion == c.construccion:
                for p in k.extremos():
                    por_punto.setdefault(p, []).append(k.id)

        def siguiente(pid, actual):
            otros = [k for k in por_punto.get(pid, []) if k != actual]
            return otros[0] if len(otros) == 1 else None

        def caminar(pid, actual, usados):
            salida = []
            while True:
                k = siguiente(pid, actual)
                if k is None or k in usados:
                    return salida, k == cid
                ini, fin = self.curvas[k].extremos()
                inv = fin == pid
                salida.append((k, inv))
                usados.add(k)
                pid, actual = (ini if inv else fin), k
        ini, fin = c.extremos()
        adelante, cerrada = caminar(fin, cid, {cid})
        if cerrada:
            return [(cid, False)] + adelante, True
        atras, _ = caminar(ini, cid, {cid} | {k for k, _ in adelante})
        return [(k, not inv) for k, inv in reversed(atras)] + [(cid, False)] + adelante, False

    def _cortes(self, cid):
        """[(t, (x, y), id de la otra curva)] donde `cid` cruza o toca a otras curvas, ordenados."""
        prim = self.primitivas(cid)[0]
        t0, t1, per = dominio(prim)
        caja = caja_primitiva(prim)
        cortes = []
        for oid, otra in self.curvas.items():
            if oid == cid or isinstance(otra, Texto):
                continue
            for q in self.primitivas(oid):
                cq = caja_primitiva(q)
                if cq[0] > caja[2] + 1e-6 or cq[2] < caja[0] - 1e-6 or cq[1] > caja[3] + 1e-6 or cq[3] < caja[1] - 1e-6:
                    continue
                q0, q1, _ = dominio(q)
                for ta, tb, xy in intersecciones(prim, q):
                    # una curva de construcción corta solo si la cruza (p. ej. los ejes de una elipse, que
                    # terminan sobre ella, no la parten)
                    if otra.construccion and (abs(tb - q0) < 1e-9 * (q1 - q0) or abs(tb - q1) < 1e-9 * (q1 - q0)):
                        continue
                    cortes.append((ta, xy, oid))
            if otra.construccion:
                continue
            for p in otra.extremos() or ():
                xy = self.coords(p)
                t, d, _ = mas_cercano(prim, xy)
                if d < 1e-7:
                    cortes.append((t, xy, oid))
        eps = 1e-9 * (t1 - t0)
        salida = []
        for t, xy, oid in sorted(cortes):
            if not per and (t <= t0 + eps or t >= t1 - eps):
                continue
            if salida and abs(t - salida[-1][0]) < eps * 10:
                continue
            salida.append((t, xy, oid))
        if per and len(salida) > 1 and abs(salida[0][0] + (t1 - t0) - salida[-1][0]) < eps * 10:
            salida.pop()
        return salida

    def _punto_corte(self, corte, nuevos):
        """Punto en un corte: se reutiliza uno existente en ese lugar o se crea con su coincidencia."""
        _t, (x, y), otra = corte
        for p in self.puntos.values():
            if math.hypot(p.x - x, p.y - y) < 1e-6:
                return p.id
        pid = self.agregar_punto(x, y)
        nuevos.append((pid, otra))
        return pid

    def _coincidencias_de_corte(self, nuevos):
        for pid, otra in nuevos:
            if otra in self.curvas and pid in self.puntos and pid not in self.curvas[otra].puntos():
                try:
                    self.agregar_restriccion("coincidente", [pid, otra])
                except ErrorBoceto:
                    pass

    def _tramo(self, cid, prim, ini, fin, nuevo, nuevos, viejos):
        """Reemplaza `cid` por el pedazo [ini, fin] (cortes o None = extremo original); con `nuevo`,
        el pedazo es una entidad aparte. Devuelve su id."""
        c = self.curvas[cid]
        t0, t1, _ = dominio(prim)
        ext = c.extremos() or (None, None)
        pa = ext[0] if ini is None else self._punto_corte(ini, nuevos)
        pb = ext[1] if fin is None else self._punto_corte(fin, nuevos)
        ident = self._nuevo_id() if nuevo else cid
        estilo = dict(construccion=c.construccion, eje=c.eje, proyectada=c.proyectada)
        if isinstance(c, Linea):
            k = Linea(ident, pa, pb, **estilo)
        elif isinstance(c, (Arco, Circulo)):
            k = Arco(ident, c.centro, pa, pb, **estilo)
        elif isinstance(c, (Elipse, ArcoElipse)):
            k = ArcoElipse(ident, c.centro, c.mayor, c.radio_menor, pa, pb, **estilo)
        else:
            ta = t0 if ini is None else ini[0]
            tb = t1 if fin is None else fin[0]
            polos, nudos, pesos = tramo_bspline(prim[2], prim[3], prim[4], prim[5], ta, tb)
            internos = [self.agregar_punto(*q) for q in polos[1:-1]]
            k = Spline(ident, [pa] + internos + [pb], "control", prim[4], False, pesos, nudos, **estilo)
            viejos.extend(c.puntos())
        if not nuevo:
            viejos.extend(p for p in c.puntos() if p not in k.puntos())
        self.curvas[ident] = k
        return ident

    def _vincular_tramos(self, a, b):
        ta = self.tipo_de(a)
        try:
            if ta == "linea":
                self.agregar_restriccion("colineal", [a, b])
            elif ta in ("arco", "arco_elipse"):
                self.agregar_restriccion("igual", [a, b])
        except ErrorBoceto:
            pass

    def _sin_cotas_de_largo(self, cid):
        """Al cambiar el largo de una curva se quitan sus cotas y restricciones de largo (como Fusion)."""
        for k in [k for k, v in self.cotas.items() if v.entidades == [cid] and v.tipo.startswith("distancia")]:
            del self.cotas[k]
        for k in [k for k, v in self.restricciones.items()
                  if cid in v.entidades and ((v.tipo == "igual" and self.tipo_de(cid) == "linea") or v.tipo == "punto_medio")]:
            del self.restricciones[k]

    def _curva_modificable(self, cid):
        c = self.curvas.get(cid)
        if c is None:
            raise ErrorBoceto("Hacé clic en una curva.")
        if isinstance(c, Texto):
            raise ErrorBoceto("Un texto no se puede recortar ni partir: desglosalo primero.")
        if c.proyectada:
            raise ErrorBoceto("La geometría proyectada no se modifica (es una referencia fija).")
        return c

    # ------------------------------------------------------------ MODIFICAR: recortar, alargar, partir
    def recortar(self, cid, punto):
        """Recortar (SKT-TRIM-EXTEND): quita el tramo de `cid` donde se hizo clic, hasta las
        intersecciones más cercanas. Si no corta con nada, se borra la curva entera."""
        c = self._curva_modificable(cid)
        prim = self.primitivas(cid)[0]
        _t0, _t1, per = dominio(prim)
        tc = mas_cercano(prim, punto)[0]
        cortes = self._cortes(cid)
        nuevos, viejos = [], []
        if per:
            if len(cortes) < 2:
                self.eliminar(cid)
                return None
            antes = [k for k in cortes if k[0] < tc]
            despues = [k for k in cortes if k[0] > tc]
            lo = antes[-1] if antes else cortes[-1]
            hi = despues[0] if despues else cortes[0]
            self._tramo(cid, prim, hi, lo, False, nuevos, viejos)    # el radio no cambia: sus cotas siguen
        else:
            antes = [k for k in cortes if k[0] < tc]
            despues = [k for k in cortes if k[0] > tc]
            lo, hi = (antes[-1] if antes else None), (despues[0] if despues else None)
            if lo is None and hi is None:
                self.eliminar(cid)
                return None
            self._sin_cotas_de_largo(cid)
            if lo is not None and hi is not None:
                otro = self._tramo(cid, prim, hi, None, True, nuevos, viejos)
                self._tramo(cid, prim, None, lo, False, nuevos, viejos)
                self._vincular_tramos(cid, otro)
            elif lo is None:
                self._tramo(cid, prim, hi, None, False, nuevos, viejos)
            else:
                self._tramo(cid, prim, None, lo, False, nuevos, viejos)
        self._coincidencias_de_corte(nuevos)
        self._depurar(viejos)
        return c.id

    def partir(self, cid, punto):
        """Partir (SKT-BREAK): divide la curva en las intersecciones más cercanas al clic. Devuelve los ids."""
        self._curva_modificable(cid)
        prim = self.primitivas(cid)[0]
        _t0, _t1, per = dominio(prim)
        tc = mas_cercano(prim, punto)[0]
        cortes = self._cortes(cid)
        nuevos, viejos = [], []
        antes = [k for k in cortes if k[0] < tc]
        despues = [k for k in cortes if k[0] > tc]
        if per:
            if len(cortes) < 2:
                raise ErrorBoceto("Para partir una curva cerrada hacen falta dos intersecciones.")
            lo = antes[-1] if antes else cortes[-1]
            hi = despues[0] if despues else cortes[0]
            otro = self._tramo(cid, prim, lo, hi, True, nuevos, viejos)
            self._tramo(cid, prim, hi, lo, False, nuevos, viejos)
            ids = [cid, otro]
        else:
            lo, hi = (antes[-1] if antes else None), (despues[0] if despues else None)
            if lo is None and hi is None:
                raise ErrorBoceto("La curva no cruza con nada: no hay dónde partirla.")
            self._sin_cotas_de_largo(cid)
            ids = []
            if hi is not None:
                ids.append(self._tramo(cid, prim, hi, None, True, nuevos, viejos))
            if lo is not None:
                ids.append(self._tramo(cid, prim, lo, hi, True, nuevos, viejos))
                self._tramo(cid, prim, None, lo, False, nuevos, viejos)
            else:
                self._tramo(cid, prim, None, hi, False, nuevos, viejos)
            ids.insert(0, cid)
            for otro in ids[1:]:
                self._vincular_tramos(cid, otro)
        self._coincidencias_de_corte(nuevos)
        self._depurar(viejos)
        return ids

    def alargar(self, cid, punto):
        """Alargar (SKT-TRIM-EXTEND): extiende el extremo de una línea o un arco más cercano al clic
        hasta la próxima intersección."""
        c = self._curva_modificable(cid)
        if not isinstance(c, (Linea, Arco)):
            raise ErrorBoceto("Alargar funciona con líneas y arcos.")
        ini, fin = c.extremos()
        lado_fin = math.dist(self.coords(fin), punto) <= math.dist(self.coords(ini), punto)
        extremo = fin if lado_fin else ini
        xs = [p.x for p in self.puntos.values()]
        ys = [p.y for p in self.puntos.values()]
        grande = 10 * (max(xs) - min(xs) + max(ys) - min(ys)) + 1000
        if isinstance(c, Linea):
            a, b = self.coords(ini), self.coords(fin)
            if not lado_fin:
                a, b = b, a
            L = math.dist(a, b)
            d = ((b[0] - a[0]) / L, (b[1] - a[1]) / L)
            rayo = ("linea", None, b, (b[0] + d[0] * grande, b[1] + d[1] * grande))
        else:
            prim = self.primitivas(cid)[0]
            (cx, cy), r = prim[2], prim[3]
            rayo = ("arco", None, (cx, cy), r, prim[5], prim[4])     # lo que le falta al arco para ser círculo
        mejor = None
        for oid, otra in self.curvas.items():
            if oid == cid or isinstance(otra, Texto):
                continue
            for q in self.primitivas(oid):
                for t, _tb, xy in intersecciones(rayo, q):
                    if math.dist(xy, self.coords(extremo)) < 1e-7:
                        continue
                    clave = t if (isinstance(c, Linea) or lado_fin) else -t
                    if mejor is None or clave < mejor[0]:
                        mejor = (clave, xy, oid)
        if mejor is None:
            raise ErrorBoceto("No hay ninguna curva para alcanzar en esa dirección.")
        _, xy, oid = mejor
        nuevos, viejos = [], []
        otras = [k for k in self.curvas.values() if k.id != cid and extremo in k.puntos()]
        if otras or self._punto_referenciado(extremo):
            nuevo = self._punto_corte((0, xy, oid), nuevos)
            for a in ("p1", "p2", "inicio", "fin"):
                if getattr(c, a, None) == extremo:
                    setattr(c, a, nuevo)
            viejos.append(extremo)
        else:
            self.puntos[extremo].x, self.puntos[extremo].y = xy
            nuevos.append((extremo, oid))
        self._sin_cotas_de_largo(cid)
        self._coincidencias_de_corte(nuevos)
        self._depurar(viejos)
        return cid

    # ------------------------------------------------------------ MODIFICAR: empalme y chaflán
    def _esquina(self, l1, l2, pick1, pick2):
        """Datos de la esquina entre dos líneas: vértice X (cruce), direcciones desde X hacia lo que se
        conserva y, para cada línea, (punto cercano a X, punto lejano, largo disponible)."""
        (a1, b1), (a2, b2) = self._extremos_linea(l1), self._extremos_linea(l2)
        d1 = (b1[0] - a1[0], b1[1] - a1[1])
        d2 = (b2[0] - a2[0], b2[1] - a2[1])
        X = recta_interseccion(a1, d1, a2, d2)
        if X is None:
            raise ErrorBoceto("Las líneas son paralelas: no forman una esquina.")
        salida = []
        for lid, (a, b), pick in ((l1, (a1, b1), pick1), (l2, (a2, b2), pick2)):
            ln = self.curvas[lid]
            if pick is None:
                pick = a if math.dist(a, X) > math.dist(b, X) else b
            L = math.dist(a, b)
            u = ((b[0] - a[0]) / L, (b[1] - a[1]) / L)
            s = 1.0 if (pick[0] - X[0]) * u[0] + (pick[1] - X[1]) * u[1] >= 0 else -1.0
            d = (u[0] * s, u[1] * s)
            pa = (a[0] - X[0]) * d[0] + (a[1] - X[1]) * d[1]
            pb = (b[0] - X[0]) * d[0] + (b[1] - X[1]) * d[1]
            cerca, lejos = (ln.p1, ln.p2) if pa < pb else (ln.p2, ln.p1)
            salida.append((d, cerca, lejos, max(pa, pb)))
        return X, salida

    def _recortar_esquina(self, l1, l2, X, lados, t1, t2):
        """Lleva los extremos cercanos a la esquina hasta T1 y T2. Si el vértice viejo seguía en uso,
        queda como "vértice virtual" (punto suelto coincidente con ambas líneas) y las cotas de largo de
        las líneas pasan a medirse desde él."""
        (_d1, c1, f1, _L1), (_d2, c2, f2, _L2) = lados
        pt1, pt2 = self.agregar_punto(*t1), self.agregar_punto(*t2)
        cotas_largo = [k for k in self.cotas.values() if k.entidades in ([l1], [l2]) and k.tipo.startswith("distancia")]
        for k in [k for k, v in self.restricciones.items()
                  if (l1 in v.entidades or l2 in v.entidades) and v.tipo in ("igual", "punto_medio")]:
            del self.restricciones[k]
        for lid, cerca, nuevo in ((l1, c1, pt1), (l2, c2, pt2)):
            ln = self.curvas[lid]
            if ln.p1 == cerca:
                ln.p1 = nuevo
            else:
                ln.p2 = nuevo
        virtual = None
        vertices = {c1, c2}
        if cotas_largo or any(self._punto_en_uso(v) or self._punto_referenciado(v) for v in vertices):
            virtual = c1 if c1 == c2 else self.agregar_punto(*X)
            self.puntos[virtual].x, self.puntos[virtual].y = X
            for lid in (l1, l2):
                self.agregar_restriccion("coincidente", [virtual, lid])
            for k in cotas_largo:
                lejos = f1 if k.entidades == [l1] else f2
                ln = self.curvas[k.entidades[0]]
                k.entidades = [virtual, lejos] if ln.p2 == lejos else [lejos, virtual]
        self._depurar(vertices - {virtual})
        return pt1, pt2, virtual

    def empalme(self, c1, c2, radio, pick1=None, pick2=None, expresion=None):
        """Empalme (SKT-ADD-FILLETS): redondea la esquina entre dos curvas con un arco tangente de
        radio dado; recorta las curvas, agrega las tangencias y la cota de radio. Devuelve el arco."""
        if radio <= 0:
            raise ErrorBoceto("El radio del empalme debe ser positivo.")
        for k in (c1, c2):
            self._curva_modificable(k)
        tipos = (self.tipo_de(c1), self.tipo_de(c2))
        if tipos == ("linea", "linea"):
            X, lados = self._esquina(c1, c2, pick1, pick2)
            (d1, *_r1), (d2, *_r2) = lados
            theta = math.acos(max(-1.0, min(1.0, d1[0] * d2[0] + d1[1] * d2[1])))
            if theta < 1e-6 or theta > math.pi - 1e-6:
                raise ErrorBoceto("Las líneas no forman una esquina.")
            tang = radio / math.tan(theta / 2)
            if tang >= lados[0][3] - 1e-9 or tang >= lados[1][3] - 1e-9:
                raise ErrorBoceto("El radio es demasiado grande para esas líneas.")
            t1 = (X[0] + tang * d1[0], X[1] + tang * d1[1])
            t2 = (X[0] + tang * d2[0], X[1] + tang * d2[1])
            bis = (d1[0] + d2[0], d1[1] + d2[1])
            nb = math.hypot(*bis)
            h = radio / math.sin(theta / 2)
            F = (X[0] + bis[0] / nb * h, X[1] + bis[1] / nb * h)
            pt1, pt2, _v = self._recortar_esquina(c1, c2, X, lados, t1, t2)
        else:
            F, pt1, pt2 = self._empalme_general(c1, c2, radio, pick1, pick2)
        a = (self.coords(pt1)[0] - F[0], self.coords(pt1)[1] - F[1])
        b = (self.coords(pt2)[0] - F[0], self.coords(pt2)[1] - F[1])
        ini, fin = (pt1, pt2) if a[0] * b[1] - a[1] * b[0] > 0 else (pt2, pt1)
        arco = self.agregar_arco_centro(F, ini, fin)
        self.agregar_restriccion("tangente", [c1, arco])
        self.agregar_restriccion("tangente", [c2, arco])
        self.agregar_cota("radio", [arco], expresion or _numero(radio))
        return arco

    def _empalme_general(self, c1, c2, r, pick1, pick2):
        """Empalme con arcos o círculos: el centro sale de cruzar las curvas desfasadas en r."""
        def portadoras(cid):
            prim = self.primitivas(cid)[0]
            if prim[0] == "linea":
                a, b = prim[2], prim[3]
                L = math.dist(a, b)
                d = ((b[0] - a[0]) / L, (b[1] - a[1]) / L)
                n = (-d[1], d[0])
                return prim, [("recta", (a[0] + s * r * n[0], a[1] + s * r * n[1]), d) for s in (1, -1)]
            if prim[0] in CIRCULARES:
                c, R = prim[2], prim[3]
                return prim, [("circ", c, R + r)] + ([("circ", c, abs(R - r))] if abs(R - r) > 1e-9 else [])
            raise ErrorBoceto("El empalme funciona con líneas, arcos y círculos.")
        p1, o1 = portadoras(c1)
        p2, o2 = portadoras(c2)
        candidatos = []
        for g1 in o1:
            for g2 in o2:
                if g1[0] == "recta" and g2[0] == "recta":
                    q = recta_interseccion(g1[1], g1[2], g2[1], g2[2])
                    candidatos += [q] if q else []
                elif g1[0] == "recta":
                    candidatos += _cruces_recta_circulo(g1[1], g1[2], g2[1], g2[2])
                elif g2[0] == "recta":
                    candidatos += _cruces_recta_circulo(g2[1], g2[2], g1[1], g1[2])
                else:
                    candidatos += _cruces_circulos(g1[1], g1[2], g2[1], g2[2])
        mejor = None
        for F in candidatos:
            pies = []
            for prim in (p1, p2):
                if prim[0] == "linea":
                    a, b = prim[2], prim[3]
                    L2 = (b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2
                    t = ((F[0] - a[0]) * (b[0] - a[0]) + (F[1] - a[1]) * (b[1] - a[1])) / L2
                    pies.append(((a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])), t, prim))
                else:
                    c, R = prim[2], prim[3]
                    dd = math.dist(F, c) or 1e-12
                    q = (c[0] + (F[0] - c[0]) * R / dd, c[1] + (F[1] - c[1]) * R / dd)
                    pies.append((q, mas_cercano(prim, q)[0], prim))
            if any(math.dist(evaluar_primitiva(prim, t)[0], q) > 1e-6 for q, t, prim in pies if prim[0] == "arco"):
                continue
            ref1 = pick1 or pies[0][0]
            ref2 = pick2 or pies[1][0]
            puntaje = math.dist(pies[0][0], ref1) + math.dist(pies[1][0], ref2)
            if mejor is None or puntaje < mejor[0]:
                mejor = (puntaje, F, pies)
        if mejor is None:
            raise ErrorBoceto("No entra un empalme de ese radio entre esas curvas.")
        _, F, pies = mejor
        puntos_t, viejos = [], []
        for cid, (q, t, prim), pick in ((c1, pies[0], pick1), (c2, pies[1], pick2)):
            pid = self.agregar_punto(*q)
            puntos_t.append(pid)
            c = self.curvas[cid]
            if isinstance(c, Circulo):
                self.agregar_restriccion("coincidente", [pid, cid])
                continue
            tp = mas_cercano(prim, pick)[0] if pick is not None else None
            ini, fin = c.extremos()
            if tp is None:
                reemplazo = ini if math.dist(self.coords(ini), q) < math.dist(self.coords(fin), q) else fin
            else:
                reemplazo = ini if tp > t else fin
            for a in ("p1", "p2", "inicio", "fin"):
                if getattr(c, a, None) == reemplazo:
                    setattr(c, a, pid)
            viejos.append(reemplazo)
            self._sin_cotas_de_largo(cid)
        self._depurar(viejos)
        return F, puntos_t[0], puntos_t[1]

    def chaflan(self, l1, l2, distancia, distancia2=None, angulo=None, pick1=None, pick2=None, expresion=None):
        """Chaflán (SKT-ADD-CHAMFERS) entre dos líneas: de distancias iguales, de dos distancias
        (`distancia2`) o de distancia y ángulo (`angulo`, grados). Agrega la línea, el vértice virtual
        y las cotas. Devuelve la línea del chaflán."""
        for k in (l1, l2):
            if self.tipo_de(self._curva_modificable(k).id) != "linea":
                raise ErrorBoceto("El chaflán se aplica entre dos líneas.")
        if distancia <= 0:
            raise ErrorBoceto("La distancia del chaflán debe ser positiva.")
        X, lados = self._esquina(l1, l2, pick1, pick2)
        (d1, *_r1), (d2, *_r2) = lados
        theta = math.acos(max(-1.0, min(1.0, d1[0] * d2[0] + d1[1] * d2[1])))
        if angulo is not None:
            alfa = math.radians(angulo)
            if not 0 < alfa < math.pi - theta:
                raise ErrorBoceto("Ese ángulo no corta la esquina.")
            distancia2 = distancia * math.sin(alfa) / math.sin(theta + alfa)
        e1, e2 = distancia, (distancia if distancia2 is None else distancia2)
        if e1 >= lados[0][3] - 1e-9 or e2 >= lados[1][3] - 1e-9:
            raise ErrorBoceto("La distancia es demasiado grande para esas líneas.")
        t1 = (X[0] + e1 * d1[0], X[1] + e1 * d1[1])
        t2 = (X[0] + e2 * d2[0], X[1] + e2 * d2[1])
        pt1, pt2, virtual = self._recortar_esquina(l1, l2, X, lados, t1, t2)
        if virtual is None:
            virtual = self.agregar_punto(*X)
            for lid in (l1, l2):
                self.agregar_restriccion("coincidente", [virtual, lid])
        ln = self.agregar_linea(pt1, pt2)
        expr = expresion or _numero(e1)
        self.agregar_cota("distancia", [virtual, pt1], expr)
        if angulo is not None:
            medido = self.medir_cota("angulo", [ln, l1])
            self.agregar_cota("angulo", [ln, l1], _numero(angulo if abs(medido - angulo) < 1e-6 else 180 - angulo))
        else:
            self.agregar_cota("distancia", [virtual, pt2], expr if distancia2 is None else _numero(e2))
        return ln

    # ------------------------------------------------------------ MODIFICAR: desfase
    def desfase(self, cid, distancia, punto_lado=None, expresion=None, invertir=False):
        """Desfase (SKT-OFFSET) de la cadena conectada a `cid`: curvas paralelas a `distancia`, con las
        esquinas resueltas por intersección, la restricción de desfase y su cota. Por defecto, una cadena
        cerrada se desfasa hacia afuera (y una abierta, a la izquierda de su recorrido); `punto_lado` elige el
        lado e `invertir` pasa al lado contrario del que tocaba. Devuelve los ids nuevos."""
        if distancia <= 0:
            raise ErrorBoceto("La distancia de desfase debe ser positiva.")
        cadena, cerrada = self.cadena(cid)
        c0 = self.curvas[cid]
        if len(cadena) == 1 and isinstance(c0, Circulo):
            r = c0.radio
            fuera = (punto_lado is None or math.dist(punto_lado, self.coords(c0.centro)) > r) != bool(invertir)
            if not fuera and distancia >= r:
                raise ErrorBoceto("El desfase es mayor que el radio.")
            nuevo = self.agregar_circulo(c0.centro, r + distancia if fuera else r - distancia, c0.construccion)
            self.agregar_cota("desfase", [cid, nuevo], expresion or _numero(distancia))
            return [nuevo]
        if any(not isinstance(self.curvas[k], (Linea, Arco)) for k, _ in cadena):
            raise ErrorBoceto("El desfase funciona con cadenas de líneas y arcos, y con círculos.")
        elems = []
        for k, inv in cadena:
            c = self.curvas[k]
            ini, fin = c.extremos()
            a, b = (fin, ini) if inv else (ini, fin)
            elems.append((k, inv, c, self.coords(a), self.coords(b), a, b))

        def izquierda_de(elem, q):
            k, inv, c, a, b, *_r = elem
            if isinstance(c, Linea):
                return (b[0] - a[0]) * (q[1] - a[1]) - (b[1] - a[1]) * (q[0] - a[0]) > 0
            dentro = math.dist(q, self.coords(c.centro)) < self.radio(k)
            return dentro != inv
        if punto_lado is not None:
            ref = next(e for e in elems if e[0] == cid)
            s = 1.0 if izquierda_de(ref, punto_lado) else -1.0
        elif cerrada:
            pts = []
            for k, inv, c, a, b, *_r in elems:
                pts.append(a)
                if isinstance(c, Arco):
                    prim = self.primitivas(k)[0]
                    pts.append(evaluar_primitiva(prim, dominio(prim)[1] / 2)[0])
            area = sum(p[0] * q[1] - q[0] * p[1] for p, q in zip(pts, pts[1:] + pts[:1], strict=True))
            s = -1.0 if area > 0 else 1.0
        else:
            s = 1.0
        if invertir:
            s = -s
        dd = s * distancia
        portadoras = []      # (tipo, datos) de cada curva desfasada + sus extremos desfasados
        for k, inv, c, a, b, *_r in elems:
            if isinstance(c, Linea):
                L = math.dist(a, b)
                n = (-(b[1] - a[1]) / L, (b[0] - a[0]) / L)
                a2, b2 = (a[0] + n[0] * dd, a[1] + n[1] * dd), (b[0] + n[0] * dd, b[1] + n[1] * dd)
                portadoras.append((("recta", a2, ((b[0] - a[0]) / L, (b[1] - a[1]) / L)), a2, b2))
            else:
                C, R = self.coords(c.centro), self.radio(k)
                r2 = R + dd if inv else R - dd
                if r2 <= 1e-9:
                    raise ErrorBoceto("El desfase es mayor que el radio de un arco de la cadena.")
                rad = lambda q, C=C, R=R, r2=r2: (C[0] + (q[0] - C[0]) * r2 / R, C[1] + (q[1] - C[1]) * r2 / R)  # noqa: E731
                portadoras.append((("circ", C, r2), rad(a), rad(b)))
        m = len(elems)
        esquinas = []
        for i in range(m if cerrada else m - 1):
            j = (i + 1) % m
            fin_i, ini_j = portadoras[i][2], portadoras[j][1]
            if math.dist(fin_i, ini_j) < 1e-9:
                esquinas.append(fin_i)
                continue
            g1, g2 = portadoras[i][0], portadoras[j][0]
            if g1[0] == "recta" and g2[0] == "recta":
                cands = [q for q in [recta_interseccion(g1[1], g1[2], g2[1], g2[2])] if q]
            elif g1[0] == "recta":
                cands = _cruces_recta_circulo(g1[1], g1[2], g2[1], g2[2])
            elif g2[0] == "recta":
                cands = _cruces_recta_circulo(g2[1], g2[2], g1[1], g1[2])
            else:
                cands = _cruces_circulos(g1[1], g1[2], g2[1], g2[2])
            J = elems[i][4]
            esquinas.append(min(cands, key=lambda q, J=J: math.dist(q, J)) if cands else
                            ((fin_i[0] + ini_j[0]) / 2, (fin_i[1] + ini_j[1]) / 2))
        pids = [self.agregar_punto(*q) for q in esquinas]
        if cerrada:
            extremos = [(pids[i - 1], pids[i]) for i in range(m)]
        else:
            ini_p, fin_p = self.agregar_punto(*portadoras[0][1]), self.agregar_punto(*portadoras[-1][2])
            todos = [ini_p] + pids + [fin_p]
            extremos = [(todos[i], todos[i + 1]) for i in range(m)]
        nuevos = []
        grupo = self._siguiente
        for (k, inv, c, *_r), (pa, pb) in zip(elems, extremos, strict=True):
            if isinstance(c, Linea):
                nid = self.agregar_linea(pb, pa, c.construccion) if inv else self.agregar_linea(pa, pb, c.construccion)
                self.agregar_restriccion("paralela", [k, nid])
            else:
                nid = (self.agregar_arco_centro(c.centro, pb, pa, c.construccion) if inv
                       else self.agregar_arco_centro(c.centro, pa, pb, c.construccion))
            nuevos.append(nid)
        k0, n0 = elems[0][0], nuevos[0]
        for (k, *_r), nid in list(zip(elems, nuevos, strict=True))[1:]:
            self.agregar_restriccion("desfase", [k0, n0, k, nid], {"grupo": grupo})
        if not cerrada:
            self.agregar_restriccion("desfase", [elems[0][0], elems[0][5], extremos[0][0]], {"grupo": grupo})
            self.agregar_restriccion("desfase", [elems[-1][0], elems[-1][6], extremos[-1][1]], {"grupo": grupo})
        self.agregar_cota("desfase", [k0, n0], expresion or _numero(distancia))
        return nuevos

    # ------------------------------------------------------------ MODIFICAR: escala, mover/copiar
    def _transformar_puntos(self, pids, f):
        for p in pids:
            q = self.puntos[p]
            q.x, q.y = f((q.x, q.y))

    def _copiar(self, ids, f, restricciones=True, angulo=0.0, compartidos=()):
        """Copia curvas y puntos sueltos aplicando `f` a las coordenadas (los `compartidos` no se
        duplican). Devuelve (mapa de puntos nuevos, mapa de curvas)."""
        pts = [p for p in self.puntos_de(ids) if p not in compartidos]
        mapa = {p: self.agregar_punto(*f(self.coords(p))) for p in pts}
        mapa_c = {}
        for i in ids:
            if i in self.curvas:
                c = self.curvas[i].remapear(mapa, self._nuevo_id())
                c.proyectada = False
                if isinstance(c, Texto):
                    c.angulo += angulo
                self.curvas[c.id] = c
                mapa_c[i] = c.id
        if restricciones:
            todo = {**mapa, **mapa_c}
            gira = _cambia_orientacion(angulo)
            for r in list(self.restricciones.values()):
                if r.tipo not in ("fijo", "patron", "desfase") and set(r.entidades) <= set(todo) and not (
                        gira and r.tipo in _ORIENTADAS):
                    self.agregar_restriccion(r.tipo, [todo[e] for e in r.entidades], r.datos)
            for k in list(self.cotas.values()):
                if set(k.entidades) <= set(todo) and not (gira and k.tipo in _COTAS_ORIENTADAS):
                    self.agregar_cota(k.tipo, [todo[e] for e in k.entidades], k.expresion, k.datos)
        return mapa, mapa_c

    def transformar(self, ids, dx=0.0, dy=0.0, angulo=0.0, centro=(0.0, 0.0), copiar=False):
        """Mover/copiar (M): traslada (dx, dy) y gira `angulo` grados alrededor de `centro`. Con `copiar`
        duplica la geometría con sus restricciones internas. Devuelve los ids resultantes."""
        a = math.radians(angulo)

        def f(q):
            x, y = _rot(q[0] - centro[0], q[1] - centro[1], a)
            return x + centro[0] + dx, y + centro[1] + dy
        if copiar:
            mapa, mapa_c = self._copiar(ids, f, True, angulo)
            return list(mapa_c.values()) + [mapa[i] for i in ids if i in mapa]
        fijos = self.puntos_fijos()
        pts = self.puntos_de(ids)
        if any(p in fijos for p in pts):
            raise ErrorBoceto("Hay geometría fija (o proyectada) en la selección: no se puede mover.")
        self._transformar_puntos(pts, f)
        for i in ids:
            if isinstance(self.curvas.get(i), Texto):
                self.curvas[i].angulo += angulo
        if _cambia_orientacion(angulo):        # una horizontal girada 90° ya no es horizontal: si quedara, colapsa
            afectados = set(ids) | set(pts)
            for k in [k for k, r in self.restricciones.items()
                      if r.tipo in _ORIENTADAS and set(r.entidades) <= afectados]:
                del self.restricciones[k]
            for k in [k for k, c in self.cotas.items()
                      if c.tipo in _COTAS_ORIENTADAS and set(c.entidades) <= afectados]:
                del self.cotas[k]
        return list(ids)

    # ------------------------------------------------------------ limpiar geometría importada
    def _referencias(self):
        """Ids usados por alguna restricción o cota (eso no se toca al limpiar)."""
        return {e for t in (self.restricciones, self.cotas) for v in t.values() for e in v.entidades}

    def _usos_de_puntos(self):
        usos = {}
        for c in self.curvas.values():
            for p in c.puntos():
                usos.setdefault(p, []).append(c.id)
        return usos

    def _fusionar_punto(self, queda, sale):
        """Todo lo que usaba el punto `sale` pasa a usar `queda`; `sale` se borra."""
        for c in self.curvas.values():
            for a in c.PUNTOS:
                if getattr(c, a) == sale:
                    setattr(c, a, queda)
            if isinstance(c, Spline):
                c.pts = [queda if p == sale else p for p in c.pts]
        for t in (self.restricciones, self.cotas):
            for v in t.values():
                v.entidades = [queda if e == sale else e for e in v.entidades]
        self.puntos.pop(sale, None)

    def _clave_curva(self, c, tol):
        r = lambda q: (round(q[0] / tol), round(q[1] / tol))  # noqa: E731
        if isinstance(c, Linea):
            return ("linea", frozenset((r(self.coords(c.p1)), r(self.coords(c.p2)))))
        if isinstance(c, Circulo):
            return ("circulo", r(self.coords(c.centro)), round(c.radio / tol))
        if isinstance(c, Arco):
            return ("arco", r(self.coords(c.centro)), r(self.coords(c.inicio)), r(self.coords(c.fin)))
        if isinstance(c, Spline):
            pts = tuple(r(self.coords(p)) for p in c.pts)
            return ("spline", c.modo, c.grado, min(pts, pts[::-1]))
        return None

    def limpiar(self, tolerancia=0.01, duplicados=True, huecos=True, colineales=True):
        """Limpieza de geometría importada (SVG, DXF, imagen vectorizada), sin tocar lo que tiene restricciones o
        cotas: borra curvas repetidas, une extremos sueltos que quedaron a menos de `tolerancia` mm (cierra
        huecos para que los contornos formen perfiles) y junta líneas seguidas que están alineadas en una sola.
        Devuelve {"duplicadas": n, "huecos": n, "colineales": n}."""
        if not tolerancia > 0:
            raise ErrorBoceto("La tolerancia tiene que ser positiva.")
        refs = self._referencias()
        salida = {"duplicadas": 0, "huecos": 0, "colineales": 0}
        if duplicados:
            vistas = {}
            for cid in list(self.curvas):
                c = self.curvas[cid]
                clave = None if cid in refs or c.proyectada else self._clave_curva(c, tolerancia)
                if clave is None:
                    continue
                clave = (clave, c.construccion)
                if clave in vistas:
                    self.eliminar(cid)
                    salida["duplicadas"] += 1
                else:
                    vistas[clave] = cid
        if huecos:
            usos = self._usos_de_puntos()
            sueltos = [p for p, cs in usos.items() if len(cs) == 1 and p not in refs
                       and self.curvas[cs[0]].extremos() and p in self.curvas[cs[0]].extremos()
                       and not self.puntos[p].proyectado]
            hechos = set()
            for i, a in enumerate(sueltos):
                if a in hechos:
                    continue
                qa = self.coords(a)
                for b in sueltos[i + 1:]:
                    if b in hechos or usos[b] == usos[a]:
                        continue
                    if math.dist(qa, self.coords(b)) <= tolerancia:
                        self._fusionar_punto(a, b)
                        hechos.update((a, b))
                        salida["huecos"] += 1
                        break
        if colineales:
            cambio = True
            while cambio:
                cambio = False
                usos = self._usos_de_puntos()
                for p, cs in usos.items():
                    if len(cs) != 2 or p in refs or self.puntos[p].proyectado:
                        continue
                    l1, l2 = (self.curvas.get(k) for k in cs)
                    if not (isinstance(l1, Linea) and isinstance(l2, Linea)) or l1.construccion != l2.construccion \
                            or l1.id in refs or l2.id in refs:
                        continue
                    a = l1.p1 if l1.p2 == p else l1.p2
                    b = l2.p1 if l2.p2 == p else l2.p2
                    if a == b or abs(distancia_punto_recta(self.coords(p), self.coords(a), self.coords(b))) > tolerancia:
                        continue
                    qa, qb, qp = self.coords(a), self.coords(b), self.coords(p)
                    if (qp[0] - qa[0]) * (qb[0] - qp[0]) + (qp[1] - qa[1]) * (qb[1] - qp[1]) <= 0:
                        continue                       # vuelve para atrás: no es una sola recta
                    if l1.p1 == p:
                        l1.p1 = b
                    else:
                        l1.p2 = b
                    self.curvas.pop(l2.id)
                    self.puntos.pop(p, None)
                    salida["colineales"] += 1
                    cambio = True
                    break
        self._quitar_huerfanas()
        return salida

    def reflejar(self, ids, centro, horizontal=True):
        """Espejo en el lugar (sin copia) respecto de la recta vertical (horizontal=True) u horizontal que pasa
        por `centro`. Los arcos invierten su sentido para seguir siendo antihorarios. Los textos rectos no se
        pueden espejar así (sus letras no se reflejan): se dejan como están y se devuelven aparte.
        Devuelve (ids espejados, ids de textos que no se espejaron)."""
        cx, cy = centro
        textos = [i for i in ids if isinstance(self.curvas.get(i), Texto) and self.curvas[i].camino is None]
        ids = [i for i in ids if i not in textos]
        pts = self.puntos_de(ids)
        if any(p in self.puntos_fijos() for p in pts):
            raise ErrorBoceto("Hay geometría fija (o proyectada) en la selección: no se puede espejar.")
        self._transformar_puntos(pts, (lambda q: (2 * cx - q[0], q[1])) if horizontal else
                                 (lambda q: (q[0], 2 * cy - q[1])))
        for i in ids:
            c = self.curvas.get(i)
            if isinstance(c, (Arco, ArcoElipse)):
                c.inicio, c.fin = c.fin, c.inicio
            elif isinstance(c, Texto):                   # texto en curva: sigue a su curva, del otro lado
                c.camino_lado = "der" if c.camino_lado == "izq" else "izq"
                c.camino_pos = 1.0 - c.camino_pos
        return list(ids), textos

    def escalar(self, ids, base, factor):
        """Escala del boceto (SKT-SCALE): agranda o achica la geometría desde el punto base; las cotas
        de longitud de esa geometría se multiplican por el factor."""
        if factor <= 0:
            raise ErrorBoceto("El factor de escala debe ser positivo.")
        pts = self.puntos_de(ids)
        if any(p in self.puntos_fijos() for p in pts):
            raise ErrorBoceto("Hay geometría fija (o proyectada) en la selección: no se puede escalar.")
        self._transformar_puntos(pts, lambda q: (base[0] + factor * (q[0] - base[0]), base[1] + factor * (q[1] - base[1])))
        afectados = set(pts) | set(ids)
        for i in ids:
            c = self.curvas.get(i)
            if isinstance(c, Circulo):
                c.radio *= factor
            elif isinstance(c, (Elipse, ArcoElipse)):
                c.radio_menor *= factor
            elif isinstance(c, Texto):
                c.altura *= factor
                c.espaciado *= factor
                c.ancho_caja *= factor
                c.camino_desfase *= factor
        for k in self.cotas.values():
            if k.tipo != "angulo" and set(k.entidades) <= afectados:
                try:
                    k.expresion = _numero(float(k.expresion.replace(",", ".")) * factor)
                except ValueError:
                    k.expresion = f"({k.expresion}) * {_numero(factor)}"
        return list(ids)

    # ------------------------------------------------------------ CREAR: simetría y patrones
    def simetria(self, ids, eje):
        """Simetría (SKT-CREATE-MIRROR): copia espejada respecto de la línea `eje`, con restricciones
        de simetría entre los puntos (los que están sobre el eje se comparten). Devuelve las curvas nuevas."""
        if self.tipo_de(eje) != "linea":
            raise ErrorBoceto("La línea de simetría tiene que ser una línea.")
        ids = [i for i in ids if i != eje and not isinstance(self.curvas.get(i), Texto)]
        if not ids:
            raise ErrorBoceto("Seleccioná la geometría a reflejar.")
        a, b = self._extremos_linea(eje)

        def reflejo(q):
            dx, dy = b[0] - a[0], b[1] - a[1]
            t = ((q[0] - a[0]) * dx + (q[1] - a[1]) * dy) / (dx * dx + dy * dy)
            fx, fy = a[0] + t * dx, a[1] + t * dy
            return 2 * fx - q[0], 2 * fy - q[1]
        mapa = {}
        for p in self.puntos_de(ids):
            q = self.coords(p)
            if abs(distancia_punto_recta(q, a, b)) < 1e-9:
                mapa[p] = p
            else:
                mapa[p] = self.agregar_punto(*reflejo(q))
                self.agregar_restriccion("simetrica", [p, mapa[p], eje])
        nuevos = []
        for i in ids:
            if i not in self.curvas:
                continue
            c = self.curvas[i].remapear(mapa, self._nuevo_id())
            c.proyectada = False
            if isinstance(c, (Arco, ArcoElipse)):
                c.inicio, c.fin = c.fin, c.inicio
            self.curvas[c.id] = c
            nuevos.append(c.id)
            if isinstance(c, (Circulo, Elipse, ArcoElipse)):
                self.agregar_restriccion("igual", [i, c.id])
        return nuevos

    def _patron(self, ids, transformaciones, datos_restriccion):
        ids = [i for i in ids if i in self.curvas or i in self.puntos]
        if not ids:
            raise ErrorBoceto("Seleccioná la geometría del patrón.")
        grupo = self._siguiente
        nuevos = []
        for f, angulo, extra in transformaciones:
            mapa, mapa_c = self._copiar(ids, f, False, angulo, extra)
            for p, q in mapa.items():
                self.agregar_restriccion("patron", [p, q] + extra, {**datos_restriccion(f, angulo), "grupo": grupo})
            for i, k in mapa_c.items():
                if isinstance(self.curvas[i], (Circulo, Elipse, ArcoElipse)):
                    self.agregar_restriccion("igual", [i, k])
            nuevos += list(mapa_c.values())
        return nuevos

    def patron_rectangular(self, ids, cantidad1, distancia1, cantidad2=1, distancia2=0.0, dir1=(1.0, 0.0),
                           dir2=(0.0, 1.0), modo="extension", simetrico=False):
        """Patrón rectangular (SKT-CREATE-RECTANGULAR-PATTERN). modo "extension": la distancia es la total;
        "espaciado": la de cada paso. Las copias quedan atadas al original (restricción de patrón)."""
        if cantidad1 < 1 or cantidad2 < 1 or cantidad1 * cantidad2 < 2:
            raise ErrorBoceto("El patrón necesita al menos dos copias.")

        def paso(n, d):
            if n <= 1:
                return 0.0
            return d / (n - 1) if modo == "extension" else d
        n1 = math.hypot(*dir1) or 1.0
        n2 = math.hypot(*dir2) or 1.0
        u, w = (dir1[0] / n1, dir1[1] / n1), (dir2[0] / n2, dir2[1] / n2)
        s1, s2 = paso(cantidad1, distancia1), paso(cantidad2, distancia2)
        o1 = -(cantidad1 - 1) // 2 if simetrico else 0
        o2 = -(cantidad2 - 1) // 2 if simetrico else 0
        trans = []
        for i in range(cantidad1):
            for j in range(cantidad2):
                if i + o1 == 0 and j + o2 == 0:
                    continue
                dx = (i + o1) * s1 * u[0] + (j + o2) * s2 * w[0]
                dy = (i + o1) * s1 * u[1] + (j + o2) * s2 * w[1]
                trans.append((lambda q, dx=dx, dy=dy: (q[0] + dx, q[1] + dy), 0.0, []))
        return self._patron(ids, trans, lambda f, _a: dict(zip(("dx", "dy"), f((0.0, 0.0)), strict=True)))

    def patron_circular(self, ids, centro, cantidad, angulo_total=360.0, simetrico=False):
        """Patrón circular (SKT-CREATE-CIRCULAR-PATTERN) alrededor de `centro` (id de punto o (u, v))."""
        if cantidad < 2:
            raise ErrorBoceto("El patrón necesita al menos dos copias.")
        cp = self._punto(centro)
        c = self.coords(cp)
        completo = abs(abs(angulo_total) - 360.0) < 1e-9
        paso = angulo_total / cantidad if completo else angulo_total / (cantidad - 1)
        desde = -(cantidad - 1) // 2 if simetrico and not completo else 0
        trans = []
        for k in range(cantidad):
            if k + desde == 0:
                continue
            a = math.radians((k + desde) * paso)
            trans.append((lambda q, a=a: (lambda r: (r[0] + c[0], r[1] + c[1]))(_rot(q[0] - c[0], q[1] - c[1], a)),
                          math.degrees(a), [cp]))
        return self._patron([i for i in ids if i != cp], trans, lambda _f, ang: {"angulo": math.radians(ang)})

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
                raise ErrorBoceto("La curva de fusión une extremos de curvas abiertas.")
            extremos.append(min(ext, key=lambda p, pick=pick: math.dist(self.coords(p), pick)))
        (e1, t1), (e2, t2) = self._salida_extremo(c1, extremos[0]), self._salida_extremo(c2, extremos[1])
        L = math.dist(e1, e2)
        if L < 1e-9:
            raise ErrorBoceto("Los extremos ya se tocan.")
        if continuidad == "G2":
            k = L / 5
            internos = [(e1[0] + k * t1[0], e1[1] + k * t1[1]), (e1[0] + 2 * k * t1[0], e1[1] + 2 * k * t1[1]),
                        (e2[0] + 2 * k * t2[0], e2[1] + 2 * k * t2[1]), (e2[0] + k * t2[0], e2[1] + k * t2[1])]
            grado, tipo = 5, "curvatura"
        else:
            k = L / 3
            internos = [(e1[0] + k * t1[0], e1[1] + k * t1[1]), (e2[0] + k * t2[0], e2[1] + k * t2[1])]
            grado, tipo = 3, "tangente"
        sid = self.agregar_spline([extremos[0]] + internos + [extremos[1]], "control", grado)
        self.agregar_restriccion(tipo, [c1, sid])
        self.agregar_restriccion(tipo, [c2, sid])
        return sid

    # ------------------------------------------------------------ texto
    def desglosar_texto(self, tid):
        """Desglosar texto (SKT-EXPLODE-TEXT): el texto pasa a ser líneas y splines fijas."""
        c = self.curvas.get(tid)
        if not isinstance(c, Texto):
            raise ErrorBoceto("Hacé clic en un texto.")
        prims = self.primitivas(tid)
        if not prims:
            raise ErrorBoceto("No se pudo generar la geometría del texto (¿fuente disponible?).")
        cache = {}

        def punto(q):
            clave = (round(q[0], 6), round(q[1], 6))
            if clave not in cache:
                cache[clave] = self.agregar_punto(*q)
            return cache[clave]
        self.eliminar(tid)
        ids = []
        for prim in prims:
            if prim[0] == "linea":
                ids.append(self._agregar_curva(Linea(self._nuevo_id(), punto(prim[2]), punto(prim[3]))))
            else:
                ids.append(self._agregar_curva(Spline(self._nuevo_id(), [punto(q) for q in prim[2]], "control",
                                                      prim[4], False, prim[5], prim[3])))
        if ids:
            self.agregar_restriccion("fijo", ids)
        return ids

    # ------------------------------------------------------------ serialización
    def a_dict(self):
        return {"siguiente_id": self._siguiente,
                "puntos": [p.a_dict() for p in self.puntos.values()],
                "curvas": [c.a_dict() for c in self.curvas.values()],
                "restricciones": [r.a_dict() for r in self.restricciones.values()],
                "cotas": [c.a_dict() for c in self.cotas.values()]}

    @classmethod
    def desde_dict(cls, d):
        b = cls()
        b._siguiente = d.get("siguiente_id", 1)
        for p in d.get("puntos", []):
            b.puntos[p["id"]] = Punto(p["id"], p["x"], p["y"], p.get("proyectado", False))
        for c in d.get("curvas", []):
            datos = {k: v for k, v in c.items() if k != "tipo"}
            b.curvas[c["id"]] = _CURVAS[c["tipo"]](**datos)
        for r in d.get("restricciones", []):
            b.restricciones[r["id"]] = Restriccion(r["id"], r["tipo"], r["entidades"], r.get("datos"))
        for c in d.get("cotas", []):
            b.cotas[c["id"]] = Cota(c["id"], c["tipo"], c["entidades"], c["expresion"], c.get("datos"))
        todos = list(b.puntos) + list(b.curvas) + list(b.restricciones) + list(b.cotas)
        b._siguiente = max([b._siguiente] + [i + 1 for i in todos])
        return b


# ---------------------------------------------------------------- utilidades geométricas 2D
def _numero(v):
    return f"{v:.6f}".rstrip("0").rstrip(".")


def _antihorario_por(a, medio, b, centro):
    """True si el arco antihorario de a a b (alrededor de centro) pasa por `medio`."""
    a0 = math.atan2(a[1] - centro[1], a[0] - centro[0])
    am = math.atan2(medio[1] - centro[1], medio[0] - centro[0])
    a1 = math.atan2(b[1] - centro[1], b[0] - centro[0])
    return (am - a0) % _DOS_PI <= (a1 - a0) % _DOS_PI


def circunferencia_3_puntos(a, b, c):
    (ax, ay), (bx, by), (cx, cy) = a, b, c
    d = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
    if abs(d) < 1e-12:
        return None
    ux = ((ax * ax + ay * ay) * (by - cy) + (bx * bx + by * by) * (cy - ay) + (cx * cx + cy * cy) * (ay - by)) / d
    uy = ((ax * ax + ay * ay) * (cx - bx) + (bx * bx + by * by) * (ax - cx) + (cx * cx + cy * cy) * (bx - ax)) / d
    return ux, uy, math.hypot(ax - ux, ay - uy)


def distancia_punto_recta(p, a, b):
    """Distancia CON signo de p a la recta a→b (positiva a la izquierda)."""
    (px, py), (ax, ay), (bx, by) = p, a, b
    n = math.hypot(bx - ax, by - ay)
    if n < 1e-12:
        return math.hypot(px - ax, py - ay)
    return ((bx - ax) * (py - ay) - (by - ay) * (px - ax)) / n

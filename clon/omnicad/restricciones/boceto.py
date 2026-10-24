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
MEDIDA_MINIMA = 1e-6      # mm (1 nm): por debajo el solver ya no distingue una medida de cero
MAX_CARACTERES_TEXTO = 1000      # crear los perfiles de las letras cuesta ~10 ms por letra: 100.000 colgaban la ventana
ALTURA_MAXIMA_TEXTO = 10_000.0   # mm (10 m)
CIRCULARES = ("circulo", "arco")
ELIPTICAS = ("elipse", "arco_elipse")
LIBRES = ("spline", "conica")
GEOMETRICAS = ("linea",) + CIRCULARES + ELIPTICAS + LIBRES      # todo menos el texto
CON_CENTRO = CIRCULARES + ELIPTICAS
_DOS_PI = 2 * math.pi


def signos_cuadrante(cuadrante):
    """(s1, s2): signos de las direcciones de las dos líneas de una cota de ángulo según su cuadrante (BOC-25).
    Sin cuadrante (None) mide entre las dos direcciones tal como se dibujaron, como antes."""
    q = cuadrante or 0
    return (-1.0 if q in (1, 2) else 1.0), (-1.0 if q in (2, 3) else 1.0)


def _validar_cuadrante(tipo, cuadrante):
    if tipo != "angulo":
        raise ErrorBoceto("El cuadrante solo vale en una cota de ángulo.")
    if isinstance(cuadrante, bool) or cuadrante not in (0, 1, 2, 3):
        raise ErrorBoceto(f"Cuadrante inválido: {cuadrante!r} (0, 1, 2 o 3).")


class ErrorBoceto(ValueError):
    pass


def centro_arco_tangente(inicio, otro, fin):
    """(centro, antihorario) del arco tangente a la línea otro→inicio (Fusion: Arco tangente).

    None si el final está sobre la recta tangente o coincide con el inicio, como en el editor.
    """
    t = (inicio[0] - otro[0], inicio[1] - otro[1])
    nt = math.hypot(*t) or 1.0
    t = (t[0] / nt, t[1] / nt)
    d = (fin[0] - inicio[0], fin[1] - inicio[1])
    izquierda = t[0] * d[1] - t[1] * d[0] > 0
    n = (-t[1], t[0]) if izquierda else (t[1], -t[0])
    den = 2 * (d[0] * n[0] + d[1] * n[1])
    if abs(den) < 1e-9:
        return None
    r = (d[0] ** 2 + d[1] ** 2) / den
    return (inicio[0] + n[0] * r, inicio[1] + n[1] * r), izquierda


def cambiar_radio(b, cid, radio):
    """Cambia el radio de un círculo o un arco SIN cota (lo que hace arrastrarlo en el editor): el círculo guarda el
    radio nuevo; en un arco, sus extremos libres se corren sobre el radio nuevo. Devuelve el punto movido (o None)."""
    c = b.curvas[cid]
    if isinstance(c, Circulo):
        c.radio = radio
        return None
    cx, cy = b.coords(c.centro)
    fijos = b.puntos_fijos()
    movidos = []
    for pid in (c.inicio, c.fin):
        if pid in fijos:
            continue
        p = b.puntos[pid]
        d = math.hypot(p.x - cx, p.y - cy) or 1.0
        p.x, p.y = cx + (p.x - cx) * radio / d, cy + (p.y - cy) * radio / d
        movidos.append(pid)
    return movidos[0] if movidos else None


def agregar_linea_medio(b, medio, extremo, construccion=False):
    """Línea de punto medio (Fusion: Línea › Punto medio): `medio` (punto id o coordenadas) es su punto medio y
    `extremo` uno de sus extremos; el otro es el simétrico. Deja la restricción «punto medio». Devuelve el id."""
    pm, m = (medio, b.coords(medio)) if isinstance(medio, int) else (None, tuple(medio))
    pe, e = (extremo, b.coords(extremo)) if isinstance(extremo, int) else (None, tuple(extremo))
    inicio = (2 * m[0] - e[0], 2 * m[1] - e[1])
    lid = b.agregar_linea(inicio, pe if pe is not None else e, construccion)
    b.agregar_restriccion("punto_medio", [pm if pm is not None else b.agregar_punto(*m), lid])
    return lid


def agregar_rectangulo_centro(b, centro, esquina, construccion=False):
    """Rectángulo central (Fusion: Rectángulo › Centro): centro (punto id o coordenadas) y una esquina, con sus dos
    diagonales de construcción y el centro como punto medio de una. Devuelve los ids de las 4 líneas."""
    pc, m = (centro, b.coords(centro)) if isinstance(centro, int) else (None, tuple(centro))
    k = tuple(esquina)
    ls = b.agregar_rectangulo((2 * m[0] - k[0], 2 * m[1] - k[1]), k, construccion)
    d1 = b.agregar_linea(b.curvas[ls[0]].p1, b.curvas[ls[2]].p1, True)
    b.agregar_linea(b.curvas[ls[1]].p1, b.curvas[ls[3]].p1, True)
    b.agregar_restriccion("punto_medio", [pc if pc is not None else b.agregar_punto(*m), d1])
    return ls


def agregar_rectangulo_3p(b, a, bb, c, construccion=False):
    """Rectángulo de 3 puntos (Fusion: Rectángulo › 3 puntos): el lado A→B y un tercer punto C que da el ancho,
    perpendicular al lado. Queda con perpendicular y paralelas. Devuelve los ids de las 4 líneas."""
    (ax, ay), (bx, by), (cx, cy) = a, bb, c
    ux, uy = bx - ax, by - ay
    L = math.hypot(ux, uy)
    if L < 1e-9:
        raise ErrorBoceto("Los dos primeros puntos coinciden.")
    nx, ny = -uy / L, ux / L
    w = (cx - ax) * nx + (cy - ay) * ny
    if abs(w) < 1e-9:
        raise ErrorBoceto("El rectángulo no puede tener ancho cero.")
    esquinas = [b.agregar_punto(ax, ay), b.agregar_punto(bx, by),
                b.agregar_punto(bx + nx * w, by + ny * w), b.agregar_punto(ax + nx * w, ay + ny * w)]
    ls = [b.agregar_linea(esquinas[i], esquinas[(i + 1) % 4], construccion) for i in range(4)]
    b.agregar_restriccion("perpendicular", [ls[0], ls[1]])
    b.agregar_restriccion("paralela", [ls[0], ls[2]])
    b.agregar_restriccion("paralela", [ls[1], ls[3]])
    return ls


def puntos_espiral(centro, inicio, vueltas, paso):
    """Puntos de ajuste de la espiral plana del editor, en mm (no una hélice 3D de Fusion)."""
    if not all(math.isfinite(v) for v in (*centro, *inicio, vueltas, paso)):
        raise ErrorBoceto("La espiral necesita coordenadas, vueltas y paso finitos.")
    r0 = math.dist(centro, inicio)
    a0 = math.atan2(inicio[1] - centro[1], inicio[0] - centro[0])
    if vueltas <= 0:
        raise ErrorBoceto("La espiral necesita al menos una fracción de vuelta.")
    n = max(4, int(math.ceil(8 * vueltas)))
    pts = []
    for i in range(n + 1):
        th = 2 * math.pi * vueltas * i / n
        r = r0 + paso * th / (2 * math.pi)
        pts.append((centro[0] + r * math.cos(a0 + th), centro[1] + r * math.sin(a0 + th)))
    if r0 < 1e-9 and paso <= 0:
        raise ErrorBoceto("La espiral necesita un radio o un paso.")
    return pts


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


def validar_texto_boceto(texto=None, altura=None):
    """Tope del largo y de la altura de un texto de boceto (los que se pasan; None = no se mira)."""
    if texto is not None:
        if not str(texto).strip():
            raise ErrorBoceto("El texto está vacío.")
        if len(str(texto)) > MAX_CARACTERES_TEXTO:
            raise ErrorBoceto(f"El texto tiene {len(str(texto)):,} caracteres y el máximo es {MAX_CARACTERES_TEXTO:,}: "
                              "cada letra se vuelve un perfil y más de eso congela la ventana.".replace(",", "."))
    if altura is not None:
        if not 0 < altura < math.inf:                   # también NaN
            raise ErrorBoceto("La altura del texto debe ser positiva.")
        if altura > ALTURA_MAXIMA_TEXTO:
            raise ErrorBoceto(f"La altura del texto no puede pasar de {ALTURA_MAXIMA_TEXTO:,.0f} mm (vale "
                              f"{altura:g}).".replace(",", "."))


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
    explícitos cuando sale de recortar, proyectar o desglosar texto).

    `manijas` (solo la de ajuste abierta): [[punto de ajuste, punta, curvatura o None]]. La manija de tangente de
    Fusion es una línea de construcción del punto de ajuste a la `punta`: su dirección es la tangente de la curva
    ahí y su largo, la fuerza (largo = cuerda total / tramos deja la tangente natural). `curvatura` (1/mm, con
    signo: + gira a la izquierda) es la manija de curvatura. La punta es un punto del boceto: se acota y la mueve
    el solver."""
    tipo, DATOS = "spline", ("modo", "grado", "cerrada", "pesos", "nudos", "manijas")

    def __init__(self, id, puntos, modo="ajuste", grado=3, cerrada=False, pesos=None, nudos=None,
                 construccion=False, eje=False, proyectada=False, manijas=None):
        self.id, self.pts, self.modo, self.grado = id, list(puntos), modo, int(grado)
        self.cerrada = bool(cerrada)
        self.pesos = None if pesos is None else [float(w) for w in pesos]
        self.nudos = None if nudos is None else [float(k) for k in nudos]
        self.manijas = [[int(a), int(b), None if k is None else float(k)] for a, b, k in (manijas or [])]
        self._estilo(construccion, eje, proyectada)

    def puntos(self):
        return list(self.pts) + [m[1] for m in self.manijas]

    def extremos(self):
        return None if self.cerrada else (self.pts[0], self.pts[-1])

    def a_dict(self):
        d = super().a_dict()
        d["puntos"] = list(self.pts)
        if not self.manijas:
            del d["manijas"]
        return d

    def remapear(self, mapa, nuevo_id=None):
        c = super().remapear(mapa, nuevo_id)
        c.pts = [mapa.get(p, p) for p in self.pts]
        c.manijas = [[mapa.get(a, a), mapa.get(b, b), k] for a, b, k in self.manijas]
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

    Como el panel «Carácter» de los editores de diseño: `kerning` (False ignora los pares de la fuente),
    `inclinacion` (grados de sesgo), `escala_h` / `escala_v` (% del ancho y del alto de las letras),
    `desfase_base` (mm que sube el texto), `capitalizacion` ("ninguno", "mayusculas", "minusculas", "titulo",
    "versalitas"), `subrayado` y `tachado` ("ninguno", "simple", "doble"; barras que también forman perfiles),
    `grosor_decoracion` (mm; 0 = el de la fuente) y `sin_division` (True: `ancho_caja` no parte las líneas).

    Texto en curva (Fusion: texto en trayectoria): `camino` es el id de una curva del mismo boceto; entonces
    `punto` y `angulo` no se usan y las letras siguen la curva. `camino_lado` ("izq" / "der": de qué lado del
    sentido de la curva van las letras), `camino_pos` (fracción 0-1 del largo donde cae el ancla, según
    `alineacion`), `camino_desfase` (mm entre la curva y la línea base) y `camino_ajustar` (repartir en todo el
    largo). Si la curva se borra, el texto vuelve a ser recto. En curva no se dibujan subrayado ni tachado.

    Marco (Fusion: el rectángulo del texto, que se acota y restringe): `marco` = [esquina derecha, esquina de
    arriba], ids de puntos; con `punto` (esquina de abajo a la izquierda) definen el giro, el ancho de la caja y el
    alto donde se ubica el texto según `ancla_v`. `altura_expr`: la altura como expresión con parámetros (Fusion
    crea el parámetro «Text height»); el paso del boceto la evalúa y la deja en `altura`."""
    tipo, PUNTOS = "texto", ("punto",)
    DATOS = ("texto", "fuente", "altura", "angulo", "negrita", "cursiva", "espaciado", "interlineado", "alineacion",
             "ancla_v", "ancho_caja", "voltear_h", "voltear_v", "camino", "camino_lado", "camino_pos",
             "camino_desfase", "camino_ajustar", "kerning", "inclinacion", "escala_h", "escala_v", "desfase_base",
             "capitalizacion", "subrayado", "tachado", "grosor_decoracion", "sin_division", "ajustes_kerning",
             "marco", "altura_expr")
    _PREDETERMINADOS = {"espaciado": 0.0, "interlineado": 1.0, "alineacion": "izq", "ancla_v": "base",
                        "ancho_caja": 0.0, "voltear_h": False, "voltear_v": False, "camino": None,
                        "camino_lado": "izq", "camino_pos": 0.5, "camino_desfase": 0.0, "camino_ajustar": False,
                        "kerning": True, "inclinacion": 0.0, "escala_h": 100.0, "escala_v": 100.0,
                        "desfase_base": 0.0, "capitalizacion": "ninguno", "subrayado": "ninguno",
                        "tachado": "ninguno", "grosor_decoracion": 0.0, "sin_division": False,
                        "ajustes_kerning": [], "marco": None, "altura_expr": None}
    # opciones del panel «Carácter» que se guardan tal cual (el tipo de cada una, para convertir lo que llega)
    TIPOGRAFIA = {"kerning": bool, "inclinacion": float, "escala_h": float, "escala_v": float, "desfase_base": float,
                  "capitalizacion": str, "subrayado": str, "tachado": str, "grosor_decoracion": float,
                  "sin_division": bool,
                  "ajustes_kerning": lambda v: [[int(i), float(x)] for i, x in v]}

    def __init__(self, id, punto, texto, fuente="Arial", altura=5.0, angulo=0.0, negrita=False, cursiva=False,
                 construccion=False, eje=False, proyectada=False, espaciado=0.0, interlineado=1.0,
                 alineacion="izq", ancla_v="base", ancho_caja=0.0, voltear_h=False, voltear_v=False, camino=None,
                 camino_lado="izq", camino_pos=0.5, camino_desfase=0.0, camino_ajustar=False, kerning=True,
                 inclinacion=0.0, escala_h=100.0, escala_v=100.0, desfase_base=0.0, capitalizacion="ninguno",
                 subrayado="ninguno", tachado="ninguno", grosor_decoracion=0.0, sin_division=False,
                 ajustes_kerning=None, marco=None, altura_expr=None):
        self.id, self.punto, self.texto, self.fuente = id, punto, str(texto), str(fuente)
        self.altura, self.angulo = float(altura), float(angulo)
        self.negrita, self.cursiva = bool(negrita), bool(cursiva)
        self.espaciado, self.interlineado = float(espaciado), float(interlineado)
        self.alineacion, self.ancla_v, self.ancho_caja = str(alineacion), str(ancla_v), float(ancho_caja)
        self.voltear_h, self.voltear_v = bool(voltear_h), bool(voltear_v)
        self.camino = None if camino is None else int(camino)
        self.camino_lado, self.camino_pos = str(camino_lado), float(camino_pos)
        self.camino_desfase, self.camino_ajustar = float(camino_desfase), bool(camino_ajustar)
        self.kerning, self.inclinacion = bool(kerning), float(inclinacion)
        self.escala_h, self.escala_v, self.desfase_base = float(escala_h), float(escala_v), float(desfase_base)
        self.capitalizacion, self.subrayado, self.tachado = str(capitalizacion), str(subrayado), str(tachado)
        self.grosor_decoracion, self.sin_division = float(grosor_decoracion), bool(sin_division)
        self.ajustes_kerning = [[int(i), float(x)] for i, x in (ajustes_kerning or [])]
        self.marco = None if marco is None else [int(p) for p in marco]
        self.altura_expr = None if altura_expr is None else str(altura_expr)
        self._estilo(construccion, eje, proyectada)

    def puntos(self):
        return [self.punto] + (self.marco or [])

    def remapear(self, mapa, nuevo_id=None):
        c = super().remapear(mapa, nuevo_id)
        if self.marco:
            c.marco = [mapa.get(p, p) for p in self.marco]
        return c

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
                self.voltear_h, self.voltear_v) + self.opciones_tipografia()

    def opciones_tipografia(self):
        """Las del panel «Carácter» (kerning, inclinación, escalas, desfase de base, capitalización, subrayado,
        tachado, grosor y sin división), en el orden de `_contornos_texto`."""
        return (self.kerning, self.inclinacion, self.escala_h, self.escala_v, self.desfase_base,
                self.capitalizacion, self.subrayado, self.tachado, self.grosor_decoracion, self.sin_division,
                tuple((i, x) for i, x in self.ajustes_kerning))


class Restriccion:
    def __init__(self, id, tipo, entidades, datos=None):
        if tipo not in TIPOS_RESTRICCION:
            raise ErrorBoceto(f"Restricción desconocida: {tipo}")
        self.id, self.tipo, self.entidades, self.datos = id, tipo, list(entidades), dict(datos or {})

    def a_dict(self):
        return {"id": self.id, "tipo": self.tipo, "entidades": self.entidades, "datos": self.datos}


class Cota:
    def __init__(self, id, tipo, entidades, expresion, datos=None, nombre="", referencia=False):
        if tipo not in TIPOS_COTA:
            raise ErrorBoceto(f"Cota desconocida: {tipo}")
        self.id, self.tipo, self.entidades, self.expresion = id, tipo, list(entidades), str(expresion)
        self.datos = dict(datos or {})
        self.nombre = nombre
        self.referencia = referencia

    def a_dict(self):
        return {"id": self.id, "tipo": self.tipo, "entidades": self.entidades,
                "expresion": self.expresion, "datos": dict(self.datos),
                **({"nombre": self.nombre} if self.nombre else {}),
                **({"referencia": True} if self.referencia else {})}


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


def _base_derivada(nudos, p, t, k, d):
    """Derivada d-ésima de N_{k-p..k, p} en t (fórmula de la derivada de las funciones base)."""
    if d == 0:
        return _funciones_base(nudos, p, t, k)
    if d > p:
        return [0.0] * (p + 1)
    baja = [0.0] + _base_derivada(nudos, p - 1, t, k, d - 1) + [0.0]     # N_{k-p..k+1, p-1}
    salida = []
    for j, i in enumerate(range(k - p, k + 1)):
        d1, d2 = nudos[i + p] - nudos[i], nudos[i + p + 1] - nudos[i + 1]
        salida.append(p * ((baja[j] / d1 if d1 else 0.0) - (baja[j + 1] / d2 if d2 else 0.0)))
    return salida


def parametros_cuerda(Q):
    """Parámetro 0-1 de cada punto de ajuste (largo de cuerda acumulado; la cerrada repite el primero al final)."""
    m = len(Q) - 1
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
    return ub


def peine_curvatura(prim, densidad=30, escala=1.0):
    """Peine de curvatura de una curva del boceto (Fusion: Toggle Curvature Display), con la escala del de las
    aristas 3D (`nucleo.analisis.peine_curvatura`): [(punto, curvatura con signo, punta)] y el factor (mm por 1/mm).
    Curvatura + = gira a la izquierda; la púa sale del lado opuesto al centro de curvatura."""
    t0, t1, _ = dominio(prim)
    muestras = []
    for i in range(densidad):
        c, d1, d2 = evaluar_primitiva(prim, t0 + (t1 - t0) * i / (densidad - 1), 2)
        v = math.hypot(*d1)
        k = (d1[0] * d2[1] - d1[1] * d2[0]) / v ** 3 if v > 1e-12 else 0.0
        muestras.append((c, k, (-d1[1] / v, d1[0] / v) if v > 1e-12 else (0.0, 0.0)))
    xs, ys = [m[0][0] for m in muestras], [m[0][1] for m in muestras]
    kmax = max(abs(m[1]) for m in muestras)
    factor = escala * 0.2 * (math.hypot(max(xs) - min(xs), max(ys) - min(ys)) or 1.0) / kmax if kmax > 1e-12 else 0.0
    return [(c, k, (c[0] - n[0] * k * factor, c[1] - n[1] * k * factor)) for c, k, n in muestras], factor


def interpolar_spline(puntos, grado=3, cerrada=False, derivadas=None):
    """(polos, nudos, grado) de la B-spline que PASA por los puntos (parámetros por cuerda, nudos
    promediados). Cerrada: vuelve al primer punto con la misma tangente (continuidad C1).
    `derivadas` (solo abierta): {índice del punto: (C' o None, C'' o None)} respecto del parámetro 0-1; cada una
    suma un polo y un nudo (Piegl y Tiller, 9.2.4): son las manijas de tangente y de curvatura."""
    Q = [(float(x), float(y)) for x, y in puntos]
    cerrar = cerrada and len(Q) >= 3
    if cerrar:
        Q = Q + [Q[0]]
    m = len(Q) - 1
    if m < 1:
        raise ErrorBoceto("Una spline necesita al menos dos puntos.")
    ub = parametros_cuerda(Q)
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
        extra = [(ub[i], orden, v) for i, par in sorted((derivadas or {}).items()) if 0 <= i <= m
                 for orden, v in enumerate(par, 1) if v is not None]
        n = m + len(extra)
        p = min(grado, n)
        ua = sorted(ub + [u for u, _o, _v in extra])
        nudos = [0.0] * (p + 1) + [sum(ua[j:j + p]) / p for j in range(1, n - p + 1)] + [1.0] * (p + 1)
        A, B = np.zeros((n + 1, n + 1)), np.array(Q + [tuple(v) for _u, _o, v in extra], dtype=float)
        for fila, (u, orden) in enumerate([(u, 0) for u in ub] + [(u, o) for u, o, _v in extra]):
            k = _tramo(nudos, p, n, u)
            A[fila, k - p:k + 1] = _base_derivada(nudos, p, u, k, orden)
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


_CLAVES_TIPOGRAFIA = ("kerning", "inclinacion", "escala_h", "escala_v", "desfase_base", "capitalizacion", "subrayado",
                      "tachado", "grosor_decoracion", "sin_division", "ajustes_kerning")
_TIPOGRAFIA_BASE = (True, 0.0, 100.0, 100.0, 0.0, "ninguno", "ninguno", "ninguno", 0.0, False, ())


def _kwargs_texto(opciones):
    """Opciones de `Texto.opciones_contorno()` como argumentos con nombre de `fuentes.contornos_texto`."""
    espaciado, interlineado, alineacion, ancla_v, ancho_caja, voltear_h, voltear_v, *tipo = opciones
    tipo = tipo or list(_TIPOGRAFIA_BASE)
    return dict(zip(("espaciado", "interlineado", "alineacion", "ancla_v", "ancho_caja", "voltear_h", "voltear_v")
                    + _CLAVES_TIPOGRAFIA, [espaciado, interlineado, alineacion, ancla_v, ancho_caja, voltear_h,
                                           voltear_v, *tipo], strict=True))


@lru_cache(maxsize=256)
def _contornos_texto(texto, fuente, altura, negrita, cursiva, opciones=(0.0, 1.0, "izq", "base", 0.0, False, False)):
    from ..nucleo.perfiles import contornos_texto      # fontTools / OpenCascade solo hacen falta para el texto
    try:
        return tuple(contornos_texto(texto, fuente, altura, negrita, cursiva, **_kwargs_texto(opciones)))
    except Exception:  # noqa: BLE001 — una fuente rota no debe romper el boceto
        return ()


@lru_cache(maxsize=128)
def _contornos_camino(texto, fuente, altura, negrita, cursiva, espaciado, alineacion, pos, lado, desfase, ajustar,
                      camino, tipografia=()):
    from ..nucleo.fuentes import contornos_en_camino
    try:
        return tuple(contornos_en_camino(texto, camino, fuente, altura, negrita, cursiva, espaciado=espaciado,
                                         alineacion=alineacion, posicion=pos, lado=lado, desfase=desfase,
                                         ajustar=ajustar, **_tipografia_camino(tipografia)))
    except Exception:  # noqa: BLE001 — una fuente rota o un camino degenerado no deben romper el boceto
        return ()


def _tipografia_camino(tipografia):
    """De la tupla de `Texto.opciones_tipografia()` lo que se aplica a un texto en curva (sin decoraciones)."""
    if not tipografia:
        return {}
    kerning, inclinacion, escala_h, escala_v, _base, capitalizacion, *_resto, ajustes = tipografia
    return {"kerning": kerning, "inclinacion": inclinacion, "escala_h": escala_h, "escala_v": escala_v,
            "capitalizacion": capitalizacion, "ajustes_kerning": ajustes}


@lru_cache(maxsize=256)
def _mapa_texto(texto, fuente, altura, negrita, cursiva, opciones):
    from ..nucleo.fuentes import mapa_texto
    try:
        return mapa_texto(texto, fuente, altura, negrita, cursiva, **_kwargs_texto(opciones))
    except Exception:  # noqa: BLE001 — sin fuente, no hay mapa del cursor
        return None


@lru_cache(maxsize=64)
def _paradas_camino(texto, fuente, altura, negrita, cursiva, espaciado, alineacion, pos, lado, desfase, ajustar,
                    camino, tipografia=()):
    from ..nucleo.fuentes import paradas_en_camino
    try:
        return tuple(paradas_en_camino(texto, camino, fuente, altura, negrita, cursiva, espaciado=espaciado,
                                       alineacion=alineacion, posicion=pos, lado=lado, desfase=desfase,
                                       ajustar=ajustar, **_tipografia_camino(tipografia)))
    except Exception:  # noqa: BLE001
        return None


def paradas_cursor(t, origen, prim_camino=None):
    """Dónde cae el cursor en cada posición del texto `t`, o None si no se pudo componer. Devuelve
    {"paradas": n + 1 segmentos ((x, y) de abajo, (x, y) de arriba) en coordenadas del boceto, "lineas": [(ini, fin)]
    de cada línea de composición (índices del texto), "linea_de": nº de línea de cada posición}. `origen` (u, v) es
    el punto de anclaje; en un texto en curva, `prim_camino` es la primitiva de la curva que sigue. Es lo que usa el
    editor del lienzo para escribir y mover el cursor dentro del texto."""
    if t.camino is not None and prim_camino is not None:
        paradas = _paradas_camino(t.texto, t.fuente, t.altura, t.negrita, t.cursiva, t.espaciado, t.alineacion,
                                  t.camino_pos, t.camino_lado, t.camino_desfase + t.desfase_base, t.camino_ajustar,
                                  polilinea_camino(prim_camino), t.opciones_tipografia())
        if paradas is None:
            return None
        n = len(paradas) - 1
        return {"paradas": list(paradas), "lineas": [(0, n)], "linea_de": [0] * (n + 1)}
    m = _mapa_texto(t.texto, t.fuente, t.altura, t.negrita, t.cursiva, t.opciones_contorno())
    if m is None:
        return None
    ox, oy = origen
    ang = math.radians(t.angulo)
    sesgo, abajo, arriba = m["sesgo"], m["abajo"], m["arriba"]
    paradas = []
    for x, y in m["paradas"]:
        punta = []
        for off in (abajo, arriba):
            r = _rot(x + sesgo * off, y + off, ang)
            punta.append((r[0] + ox, r[1] + oy))
        paradas.append(tuple(punta))
    return {"paradas": paradas, "lineas": list(m["lineas"]), "linea_de": list(m["linea_de"])}


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


def _medidas_marco(a, b, t):
    """(giro en radianes, ancho, alto) del marco de un texto: `a` esquina de abajo a la izquierda, `b` la de la
    derecha y `t` la de arriba."""
    ang = math.atan2(b[1] - a[1], b[0] - a[0])
    alto = -math.sin(ang) * (t[0] - a[0]) + math.cos(ang) * (t[1] - a[1])
    return ang, math.dist(a, b), alto


def _derivadas_manijas(c, pts, P):
    """{índice: (C', C'')} de las manijas de una spline de ajuste abierta (ver `Spline`): C' = (punta − punto) ×
    tramos; con curvatura k, C'' = k·|C'|·(normal izquierda de C') (sin componente tangencial)."""
    if c.cerrada or not c.manijas:
        return None
    tramos, salida = len(pts) - 1, {}
    for a, b, k in c.manijas:
        if a not in c.pts:
            continue
        i = c.pts.index(a)
        (fx, fy), (ex, ey) = pts[i], P(b)
        d1 = ((ex - fx) * tramos, (ey - fy) * tramos)
        largo = math.hypot(*d1)
        if largo < 1e-12:
            continue
        salida[i] = (d1, None if k is None else (-k * largo * d1[1], k * largo * d1[0]))
    return salida


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
            polos, nudos, p = interpolar_spline(pts, c.grado, c.cerrada, _derivadas_manijas(c, pts, P))
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
                c.camino_lado, c.camino_desfase + c.desfase_base, c.camino_ajustar, polilinea_camino(base[0]),
                c.opciones_tipografia())]
    if isinstance(c, Texto):
        ox, oy = P(c.punto)
        ang = math.radians(c.angulo)
        opciones = c.opciones_contorno()
        if c.marco:
            ang, ancho, alto = _medidas_marco(P(c.punto), P(c.marco[0]), P(c.marco[1]))
            sube = {"arriba": alto, "medio": alto / 2}.get(c.ancla_v, 0.0)
            ox, oy = ox - math.sin(ang) * sube, oy + math.cos(ang) * sube
            ancla = "abajo" if c.ancla_v == "base" else c.ancla_v
            opciones = opciones[:3] + (ancla, ancho) + opciones[5:]
        T = lambda q: (lambda r: (r[0] + ox, r[1] + oy))(_rot(q[0], q[1], ang))  # noqa: E731
        salida = []
        for prim in _contornos_texto(c.texto, c.fuente, c.altura, c.negrita, c.cursiva, opciones):
            if prim[0] == "linea":
                salida.append(("linea", c.id, T(prim[2]), T(prim[3])))
            else:
                salida.append(("spline", c.id, tuple(T(q) for q in prim[2]), prim[3], prim[4], prim[5]))
        return salida
    return []


_FX = re.compile(r"\{([^{}]*)\}")


def _partes_fx(contenido):
    corte = contenido.rfind(":")
    if corte < max(contenido.rfind("'"), contenido.rfind('"')):     # el «:» va entre comillas: no es formato
        corte = -1
    if corte < 0:
        return contenido.strip(), ""
    return contenido[:corte].strip(), contenido[corte + 1:].strip()


def _sumandos(expresion):
    """Partes de «'abc' + expr + ...» (como los parámetros de texto de Fusion): [(literal?, texto)], cortando en los
    «+» que no están entre comillas ni paréntesis. Sin comillas, None (es una expresión numérica común)."""
    if "'" not in expresion and '"' not in expresion:
        return None
    partes, actual, comilla, nivel = [], "", None, 0
    for ch in expresion + "+":
        if comilla:
            actual += ch
            comilla = None if ch == comilla else comilla
        elif ch in "'\"":
            actual, comilla = actual + ch, ch
        elif ch == "+" and nivel == 0:
            s = actual.strip()
            literal = len(s) >= 2 and s[0] == s[-1] and s[0] in "'\""
            partes.append((literal, s[1:-1] if literal else s))
            actual = ""
        else:
            nivel += (ch == "(") - (ch == ")")
            actual += ch
    return partes


def expresiones_de_texto(texto):
    """Expresiones que lleva un texto entre llaves: «Ancho {ancho}» → ['ancho']; «{largo / 2:.1f}» → ['largo / 2'];
    «{'R-' + rev}» → ['rev']."""
    salida = []
    for e, _f in (_partes_fx(m.group(1)) for m in _FX.finditer(str(texto))):
        partes = _sumandos(e)
        salida += [e] if partes is None else [s for literal, s in partes if not literal]
    return [e for e in salida if e]


def sustituir_expresiones(texto, valor):
    """Reemplaza cada {expresión} (o {expresión:formato}) por el número que devuelve `valor(expresión)`.
    Sin formato, hasta 4 decimales y sin ceros de más; con formato, el de Python (`.1f`, `05.0f`…).
    Lo que `valor` no pueda calcular lo deja `valor` (lanza); el que llama decide qué hacer con el error."""
    def numero(expresion, formato):
        v = float(valor(expresion))
        if formato:
            return format(v, formato)
        s = f"{v:.4f}".rstrip("0").rstrip(".")
        return "0" if s in ("", "-0") else s

    def reemplazo(m):
        expresion, formato = _partes_fx(m.group(1))
        if not expresion:
            return m.group(0)
        partes = _sumandos(expresion)
        if partes is None:
            return numero(expresion, formato)
        return "".join(s if literal else numero(s, formato) for literal, s in partes)
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
    for k in ("camino_pos", "camino_desfase", "desfase_base", "inclinacion", "escala_h", "escala_v",
              "grosor_decoracion"):
        if k in op and not math.isfinite(float(op[k])):
            raise ErrorBoceto(f"«{k}» tiene que ser un número finito.")
    for k in ("escala_h", "escala_v"):
        if k in op and not 1.0 <= float(op[k]) <= 1000.0:
            raise ErrorBoceto(f"La escala {'horizontal' if k == 'escala_h' else 'vertical'} va de 1 a 1000 %.")
    if "inclinacion" in op and abs(float(op["inclinacion"])) > 80.0:
        raise ErrorBoceto("La inclinación va de -80 a 80 grados.")
    if "grosor_decoracion" in op and float(op["grosor_decoracion"]) < 0:
        raise ErrorBoceto("El grosor del subrayado y el tachado no puede ser negativo.")
    if op.get("capitalizacion", "ninguno") not in ("ninguno", "mayusculas", "minusculas", "titulo", "versalitas"):
        raise ErrorBoceto("La capitalización es ninguno, mayusculas, minusculas, titulo o versalitas.")
    for k in ("subrayado", "tachado"):
        if op.get(k, "ninguno") not in ("ninguno", "simple", "doble"):
            raise ErrorBoceto(f"El {k} es ninguno, simple o doble.")
    for par in op.get("ajustes_kerning") or []:
        try:
            i, x = par
            valido = int(i) >= 0 and math.isfinite(float(x))
        except (TypeError, ValueError):
            valido = False
        if not valido:
            raise ErrorBoceto("Los ajustes de kerning son pares [posición desde 0, mm].")


# ---------------------------------------------------------------- boceto
class Boceto:
    ORIGEN = 0
    EJE_X = -1
    EJE_Y = -2

    def __init__(self):
        self.puntos = {}
        self.curvas = {}
        self.restricciones = {}
        self.cotas = {}
        self.proyecciones = []
        self.patrones = []             # patrones de boceto editables (ver `_patron`)
        self.ultimo_patron = None
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
        if math.dist(self.coords(a), self.coords(b)) < 1e-9:
            raise ErrorBoceto("Los dos extremos de la cónica coinciden.")
        if abs(distancia_punto_recta(self.coords(v), self.coords(a), self.coords(b))) < 1e-9:
            raise ErrorBoceto("El vértice no puede estar alineado con los extremos.")
        return self._agregar_curva(Conica(self._nuevo_id(), a, v, b, rho, construccion))

    def agregar_texto(self, posicion, texto, altura=5.0, angulo=0.0, fuente="Arial", negrita=False, cursiva=False,
                      **opciones):
        """Texto en el boceto (SKT-CREATE-TEXT): sus contornos dan perfiles para extruir. `opciones`: espaciado,
        interlineado, alineacion, ancla_v, ancho_caja, voltear_h, voltear_v, el texto en curva y las del panel
        «Carácter» (kerning, inclinacion, escala_h, escala_v, desfase_base, capitalizacion, subrayado, tachado,
        grosor_decoracion, sin_division); ver `Texto`."""
        validar_texto_boceto(texto, altura)
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
            if math.dist(centro, b2) < 1e-9:
                raise ErrorBoceto("El tercer punto de la ranura de arco no puede coincidir con el centro.")
            ang = math.atan2(b2[1] - centro[1], b2[0] - centro[0])
            b = (centro[0] + R * math.cos(ang), centro[1] + R * math.sin(ang))
            a0 = math.atan2(a[1] - centro[1], a[0] - centro[0])
            if math.dist(a, b) < 1e-9:
                raise ErrorBoceto("El barrido de la ranura de arco es cero: el tercer punto está en la dirección del "
                                  "extremo inicial.")
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

    def agregar_proyeccion(self, primitivas, puntos=(), construccion=False, origen=None):
        """Agrega geometría proyectada (Proyectar / Intersecar de Fusion): curvas violetas, fijas.
        Los extremos que coinciden se comparten para que cierren perfiles. Con `construccion` las curvas quedan
        como líneas de construcción (no forman perfiles). Con `origen` recuerda las referencias para reproyectar."""
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
        circulos = [(c.centro, c.radio) for c in self.curvas.values() if c.proyectada and isinstance(c, Circulo)]
        for prim in primitivas:
            t = prim[0]
            if t == "linea":
                if math.dist(prim[2], prim[3]) < 1e-9:
                    continue
                extremos = frozenset((punto(prim[2]), punto(prim[3])))
                if extremos in lineas:        # dos aristas que se proyectan sobre la misma línea: una sola
                    continue
                lineas.add(extremos)
                c = Linea(self._nuevo_id(), punto(prim[2]), punto(prim[3]), construccion, proyectada=True)
            elif t == "circulo":
                centro, radio = punto(prim[2]), prim[3]
                if any(centro == pc and abs(radio - r) < 1e-6 for pc, r in circulos):
                    continue
                circulos.append((centro, radio))
                c = Circulo(self._nuevo_id(), centro, radio, construccion, proyectada=True)
            elif t == "arco":
                (cx, cy), r = prim[2], prim[3]
                c = Arco(self._nuevo_id(), punto((cx, cy)), punto((cx + r * math.cos(prim[4]), cy + r * math.sin(prim[4]))),
                         punto((cx + r * math.cos(prim[5]), cy + r * math.sin(prim[5]))), construccion, proyectada=True)
            elif t in ELIPTICAS:
                (cx, cy), a, b, ang = prim[2], prim[3], prim[4], prim[5]
                centro, mayor = punto((cx, cy)), punto((cx + a * math.cos(ang), cy + a * math.sin(ang)))
                if t == "elipse":
                    c = Elipse(self._nuevo_id(), centro, mayor, b, construccion, proyectada=True)
                else:
                    p0, p1 = evaluar_primitiva(prim, 0.0)[0], evaluar_primitiva(prim, dominio(prim)[1])[0]
                    c = ArcoElipse(self._nuevo_id(), centro, mayor, b, punto(p0), punto(p1), construccion, proyectada=True)
            elif t == "spline":
                polos = [punto(q) for q in prim[2]]
                c = Spline(self._nuevo_id(), polos, "control", prim[4], False, prim[5], prim[3], construccion, proyectada=True)
            else:
                continue
            ids.append(self._agregar_curva(c))
        for xy in puntos:
            ids.append(punto(xy))
        if origen is not None and ids:
            self.proyecciones.append({"id": max((r["id"] for r in self.proyecciones), default=0) + 1,
                                      "construccion": construccion, "ids": list(ids),
                                      **copy.deepcopy(origen)})
        return ids

    def _proyeccion(self, pid):
        r = next((r for r in self.proyecciones if r["id"] == pid), None)
        if r is None:
            raise ErrorBoceto(f"No existe la proyección {pid}.")
        return r

    def romper_vinculo(self, pid):
        """Romper vínculo (Fusion: Break Link): la geometría proyectada queda donde está, como geometría normal
        (editable, ya no fija) que no sigue más al modelo."""
        r = self.proyecciones.pop(self.proyecciones.index(self._proyeccion(pid)))
        siguen = {i for otra in self.proyecciones for i in otra["ids"]}
        for i in r["ids"]:
            if i in self.curvas:
                self.curvas[i].proyectada = False
                for q in self.curvas[i].puntos():
                    if not any(q in self.curvas[k].puntos() for k in siguen if k in self.curvas):
                        self.puntos[q].proyectado = False
            elif i in self.puntos and i not in siguen:
                self.puntos[i].proyectado = False

    def eliminar_proyeccion(self, pid):
        """Borrar geometría (Manage Lost Projections › Delete Geometry): quita la proyección y sus curvas y puntos."""
        r = self.proyecciones.pop(self.proyecciones.index(self._proyeccion(pid)))
        for i in r["ids"]:
            if i in self.curvas or i in self.puntos:
                self.eliminar(i)

    def revincular(self, pid, refs, primitivas, puntos):
        """Re-vincular (Manage Lost Projections › Re-Link): la proyección pasa a seguir las referencias `refs`, cuya
        proyección (`primitivas`, `puntos`) tiene que tener la misma forma que la que había."""
        r = self._proyeccion(pid)
        if not self.reproyectar(r, primitivas, puntos):
            raise ErrorBoceto("Lo que elegiste no se proyecta con la misma forma que la proyección original (otra "
                              "cantidad o tipo de curvas): usá Romper vínculo o Borrar geometría y proyectá de nuevo.")
        r["refs"] = copy.deepcopy(refs)

    def reproyectar(self, registro, primitivas, puntos) -> bool:
        """Actualiza Proyectar / Intersecar de Fusion conservando ids; si cambia la topología, no toca nada."""
        nuevo = Boceto()
        ids = nuevo.agregar_proyeccion(primitivas, puntos, registro["construccion"])
        if len(ids) != len(registro["ids"]):
            return False
        coordenadas, curvas = {}, []
        for anterior_id, nuevo_id in zip(registro["ids"], ids, strict=True):
            anterior = self.curvas.get(anterior_id, self.puntos.get(anterior_id))
            actual = nuevo.entidad(nuevo_id)
            if anterior is None or type(anterior) is not type(actual):
                return False
            if isinstance(anterior, Punto):
                anteriores, actuales = [anterior.id], [actual.id]
            else:
                anteriores, actuales = anterior.puntos(), actual.puntos()
                curvas.append((anterior, actual))
            if len(anteriores) != len(actuales) or any(p not in self.puntos for p in anteriores):
                return False
            for pid, qid in zip(anteriores, actuales, strict=True):
                xy = nuevo.coords(qid)
                if pid in coordenadas and math.dist(coordenadas[pid], xy) > 1e-6:
                    return False
                coordenadas[pid] = xy
        for pid, xy in coordenadas.items():
            self.puntos[pid].x, self.puntos[pid].y = xy
        for anterior, actual in curvas:
            for atributo in type(anterior).DATOS:
                setattr(anterior, atributo, copy.deepcopy(getattr(actual, atributo)))
        return True

    def agregar_restriccion(self, tipo, entidades, datos=None):
        self._validar_restriccion(tipo, entidades)
        if tipo == "fijo":
            for r in self.restricciones.values():
                if r.tipo == tipo and set(r.entidades) == set(entidades):
                    return r.id
        r = Restriccion(self._nuevo_id(), tipo, entidades, datos)
        self.restricciones[r.id] = r
        return r.id

    def anclar_al_origen(self, puntos_nuevos):
        """Fija el primer punto nuevo dibujado sobre (0, 0), como el editor de Fusion."""
        for pid in sorted(puntos_nuevos):
            x, y = self.coords(pid)
            if abs(x) < 1e-9 and abs(y) < 1e-9:
                return self.agregar_restriccion("fijo", [pid], {"origen": True})
        return None

    def asegurar_referencias(self, ids):
        """Materializa solo las referencias citadas: origen 0, eje X -1 y eje Y -2.

        Son geometría de construcción fija (proyectada); sus puntos auxiliares -3/-4
        no consumen ids de usuario ni aportan grados de libertad o perfiles.
        """
        if any(i in (self.ORIGEN, self.EJE_X, self.EJE_Y) for i in ids):
            self.puntos.setdefault(self.ORIGEN, Punto(self.ORIGEN, 0, 0, proyectado=True))
        for eje, pid, x, y in ((self.EJE_X, -3, 1, 0), (self.EJE_Y, -4, 0, 1)):
            if eje in ids:
                self.puntos.setdefault(pid, Punto(pid, x, y, proyectado=True))
                self.curvas.setdefault(eje, Linea(eje, self.ORIGEN, pid, construccion=True, proyectada=True))

    def agregar_cota(self, tipo, entidades, expresion, datos=None, referencia=False):
        """Crea una cota (Sketch Dimension); una referencia mide sin restringir la geometría. `datos["modo"]`
        ("centro" o "tangente") vale en una distancia con un círculo o arco; ahí se guarda siempre (falta = centro)."""
        datos = dict(datos or {})
        self._validar_cota(tipo, entidades)
        modo = datos.pop("modo", "centro")
        if modo not in ("centro", "tangente"):
            raise ErrorBoceto(f"Modo de cota desconocido: {modo} (centro o tangente).")
        if self.admite_modo(tipo, entidades):
            datos["modo"] = modo
        elif modo == "tangente":
            raise ErrorBoceto("El modo tangente solo vale en una cota de distancia con un círculo o un arco.")
        if tipo in ("distancia_h", "distancia_v") and "signo" not in datos:
            (x1, y1), (x2, y2) = self._extremos_cota(entidades)
            d = (x2 - x1) if tipo == "distancia_h" else (y2 - y1)
            datos["signo"] = 1.0 if d >= 0 else -1.0
        if "cuadrante" in datos:
            _validar_cuadrante(tipo, datos["cuadrante"])
        if referencia:
            expresion = repr(self.medir_cota(tipo, entidades, modo, datos.get("cuadrante"))
                             * (2 if datos.get("diametral") else 1))
        c = Cota(self._nuevo_id(), tipo, entidades, expresion, datos, referencia=referencia)
        self.cotas[c.id] = c
        return c.id

    def admite_modo(self, tipo, entidades):
        """True si la cota mide al centro o tangente: una distancia con un círculo o un arco (BOC-3)."""
        return tipo == "distancia" and any(self.tipo_de(e) in CIRCULARES for e in entidades)

    def cambiar_cota(self, cid, tipo=None, modo=None, cuadrante=None):
        """Menú de la cota (BOC-3). `tipo`: radio ↔ diámetro conservando el valor equivalente (la expresión se
        multiplica o divide por 2: la geometría no cambia). `modo`: centro ↔ tangente; la expresión queda y la
        geometría la cumple al resolver (una cota de referencia vuelve a medir). `cuadrante` (0..3, BOC-25): qué
        ángulo mide una cota de ángulo; igual que `modo`, la expresión queda."""
        k = self.cotas[cid]
        if cuadrante is not None:
            _validar_cuadrante(k.tipo, cuadrante)
            k.datos["cuadrante"] = cuadrante
            if k.referencia:
                k.expresion = repr(self.medir(k))
        if tipo is not None:
            if not {tipo, k.tipo} <= {"radio", "diametro"}:
                raise ErrorBoceto("Solo una cota de radio pasa a diámetro (o al revés).")
            if tipo != k.tipo:
                try:
                    v = float(k.expresion.replace(",", "."))      # como en escalar: el editor admite "6,5"
                    k.expresion = repr(v * 2 if tipo == "diametro" else v / 2)
                except ValueError:
                    k.expresion = f"({k.expresion}) {'* 2' if tipo == 'diametro' else '/ 2'}"
                k.tipo = tipo
        if modo is not None:
            if modo not in ("centro", "tangente"):
                raise ErrorBoceto(f"Modo de cota desconocido: {modo} (centro o tangente).")
            if not self.admite_modo(k.tipo, k.entidades):
                raise ErrorBoceto("Centro o tangente solo vale en una cota de distancia con un círculo o un arco.")
            k.datos["modo"] = modo
            if k.referencia:
                k.expresion = repr(self.medir(k))

    # ------------------------------------------------------------ borrado
    def eliminar(self, id):
        """Borra una entidad, restricción o cota, y en cascada lo que dependa de ella."""
        if id <= 0:
            raise ErrorBoceto("El origen y los ejes del boceto son referencias fijas: no se pueden borrar.")
        if id in self.restricciones:
            del self.restricciones[id]
            return
        if id in self.cotas:
            borrada = self.cotas.pop(id)
            for k in self.cotas.values():      # chaflán ligado (BOC-25): la que la citaba hereda su expresión
                if borrada.nombre and k.expresion == borrada.nombre:
                    k.expresion = borrada.expresion
            return
        if id in self.curvas:
            curva = self.curvas.pop(id)
            pts = curva.puntos()
            if isinstance(curva, Linea):             # borrar la línea de una manija la desactiva
                for s in self.curvas.values():
                    if isinstance(s, Spline):
                        s.manijas = [m for m in s.manijas if {m[0], m[1]} != {curva.p1, curva.p2}]
            for lid in self._lineas_auxiliares(curva):   # las manijas y el marco se van con su curva
                pts += self.curvas.pop(lid).puntos()
            for p in pts:
                if not self._punto_en_uso(p):
                    self.puntos.pop(p, None)
        elif id in self.puntos:
            for cid in [c.id for c in self.curvas.values() if id in c.puntos()
                        and not (isinstance(c, Spline) and id in [m[1] for m in c.manijas])]:
                self.curvas.pop(cid)
            del self.puntos[id]
        else:
            raise ErrorBoceto(f"No existe el elemento {id}.")
        self._quitar_huerfanas()

    def _lineas_auxiliares(self, c):
        """Ids de las líneas de las manijas de una spline o del marco de un texto (las que unen sus puntos)."""
        if isinstance(c, Spline):
            pares = [{a, b} for a, b, _k in c.manijas]
        elif isinstance(c, Texto) and c.marco:
            esquinas = set(c.puntos())
            pares = [{l.p1, l.p2} for l in self.curvas.values() if isinstance(l, Linea) and {l.p1, l.p2} <= esquinas]
        else:
            return []
        return [l.id for l in self.curvas.values() if isinstance(l, Linea) and {l.p1, l.p2} in pares]

    def _quitar_huerfanas(self):
        vivos = set(self.puntos) | set(self.curvas)
        for c in self.curvas.values():
            if isinstance(c, Texto) and c.camino is not None and c.camino not in self.curvas:
                c.camino = None                            # se borró su curva: vuelve a ser texto recto
            if isinstance(c, Spline) and c.manijas:        # se borró la punta de una manija
                c.manijas = [m for m in c.manijas if m[0] in self.puntos and m[1] in self.puntos]
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

    def ejes_cota(self, c):
        """Marco de una cota lineal (línea sola o dos puntos): (a, b, u, n, s0) —extremos medidos, eje a lo largo
        de la cota, eje normal y coordenada normal de la referencia—. None si la cota no se puede ubicar."""
        if c.tipo not in ("distancia", "distancia_h", "distancia_v"):
            return None
        if [self.tipo_de(e) for e in c.entidades] not in (["linea"], ["punto", "punto"]):
            return None
        a, b = self._extremos_cota(c.entidades)
        if c.tipo == "distancia_h":
            u, n = (1.0, 0.0), (0.0, 1.0)
        elif c.tipo == "distancia_v":
            u, n = (0.0, 1.0), (1.0, 0.0)
        else:
            largo = math.dist(a, b)
            if largo < 1e-12:
                return None
            u = ((b[0] - a[0]) / largo, (b[1] - a[1]) / largo)
            n = (-u[1], u[0])
        return a, b, u, n, max(a[0] * n[0] + a[1] * n[1], b[0] * n[0] + b[1] * n[1])

    def ubicar_cota(self, c, punto):
        """Guarda dónde van la línea de cota y su texto (datos «desfase» y «texto», en mm): la línea pasa por
        `punto` (x, y) y el texto queda a su altura. No cambia el valor ni la geometría."""
        if c.tipo == "angulo":                # BOC-25: el cuadrante bajo el cursor elige qué ángulo se mide
            c.datos["cuadrante"] = self.cuadrante_angulo(*c.entidades, punto)
            return
        marco = self.ejes_cota(c)
        if marco is not None:
            a, b, u, n, s0 = marco
            c.datos["desfase"] = round(punto[0] * n[0] + punto[1] * n[1] - s0, 6)
            medio = ((a[0] + b[0]) * u[0] + (a[1] + b[1]) * u[1]) / 2
            c.datos["texto"] = round(punto[0] * u[0] + punto[1] * u[1] - medio, 6)

    def separacion(self, original, desfasada):
        """Distancia entre una curva y su desfase (líneas paralelas o círculos/arcos concéntricos)."""
        o, d = self.curvas[original], self.curvas[desfasada]
        if isinstance(o, Linea):
            return abs(distancia_punto_recta(self.coords(d.p1), *self._extremos_linea(o.id)))
        return abs(self.radio(d.id) - self.radio(o.id))

    def medir(self, cota):
        """Valor actual de una cota existente (con su modo)."""
        medida = self.medir_cota(cota.tipo, cota.entidades, cota.datos.get("modo", "centro"), cota.datos.get("cuadrante"))
        return medida * 2 if cota.datos.get("diametral") else medida     # cota con la línea central: diámetro

    def cuadrante_angulo(self, l1, l2, punto):
        """Cuadrante (0..3) entre las rectas de l1 y l2 que contiene `punto` (x, y), como Fusion elige el ángulo
        con el cursor: 0 entre +d1 y +d2, 1 entre −d1 y +d2, 2 entre −d1 y −d2, 3 entre +d1 y −d2 (d = p1→p2)."""
        (a, _), (c, _) = self._extremos_linea(l1), self._extremos_linea(l2)
        d1, d2 = self._direccion(l1), self._direccion(l2)
        det = d1[0] * d2[1] - d1[1] * d2[0]
        if abs(det) < 1e-9:
            raise ErrorBoceto("Las líneas son paralelas: no forman ángulo.")
        # Cruce de las rectas: a + s·d1 = c + t·d2. Después, el punto en la base (d1, d2) desde el cruce.
        s = ((c[0] - a[0]) * d2[1] - (c[1] - a[1]) * d2[0]) / det
        o = (a[0] + s * d1[0], a[1] + s * d1[1])
        v = (punto[0] - o[0], punto[1] - o[1])
        k1 = (v[0] * d2[1] - v[1] * d2[0]) / det
        k2 = (d1[0] * v[1] - d1[1] * v[0]) / det
        return (0, 3, 1, 2)[(k1 < 0) * 2 + (k2 < 0)]

    def medir_cota(self, tipo, entidades, modo="centro", cuadrante=None):
        """Valor actual (mm o grados) de una cota sobre la geometría actual: sirve de valor por defecto. `modo`
        ("centro" o "tangente") vale en una distancia con un círculo o arco; `cuadrante` (0..3) en un ángulo."""
        t = [self.tipo_de(e) for e in entidades]
        if tipo == "distancia" and set(t) & set(CIRCULARES):
            return abs(distancia_con_circulo(t, entidades, modo, self.coords, lambda c: self.coords(self.curvas[c].centro),
                                             self.radio, self._extremos_linea))
        if tipo == "distancia" and sorted(t) == ["punto", "spline"]:
            p, s = entidades if t[0] == "punto" else entidades[::-1]
            return mas_cercano(self.primitivas(s)[0], self.coords(p))[1]
        if tipo in ("radio", "diametro"):
            r = self.radio(entidades[0])
            return r if tipo == "radio" else 2 * r
        if tipo == "desfase":
            return self.separacion(*entidades)
        if tipo == "angulo":
            d1, d2 = (self._direccion(e) for e in entidades)
            s1, s2 = signos_cuadrante(cuadrante)
            d1, d2 = (s1 * d1[0], s1 * d1[1]), (s2 * d2[0], s2 * d2[1])
            return math.degrees(math.atan2(abs(d1[0] * d2[1] - d1[1] * d2[0]), d1[0] * d2[0] + d1[1] * d2[1]))
        if tipo == "distancia" and t == ["punto", "linea"]:
            return abs(distancia_punto_recta(self.coords(entidades[0]), *self._extremos_linea(entidades[1])))
        if tipo == "distancia" and t == ["linea", "punto"]:
            return abs(distancia_punto_recta(self.coords(entidades[1]), *self._extremos_linea(entidades[0])))
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
            "distancia": lambda: (t in (["punto", "punto"], ["linea"], ["punto", "linea"], ["linea", "punto"],
                                        ["linea", "linea"]) or sorted(t) == ["punto", "spline"]
                                  or (len(t) == 2 and set(t) & set(CIRCULARES)
                                      and set(t) <= {"punto", "linea", *CIRCULARES})),
            "distancia_h": lambda: t in (["punto", "punto"], ["linea"]),
            "distancia_v": lambda: t in (["punto", "punto"], ["linea"]),
            "radio": lambda: t in (["circulo"], ["arco"]),
            "diametro": lambda: t in (["circulo"], ["arco"]),
            "angulo": lambda: t == ["linea", "linea"],
            "desfase": lambda: t == ["linea", "linea"] or (len(t) == 2 and t[0] in CIRCULARES and t[1] in CIRCULARES),
        }
        if not validas[tipo]():
            raise ErrorBoceto(f"La cota '{TIPOS_COTA[tipo]}' no aplica a: {', '.join(t) or 'nada'}.")
        if tipo == "angulo" and entidades[0] == entidades[1]:
            raise ErrorBoceto("Una cota de ángulo necesita dos líneas distintas.")
        if tipo == "distancia" and len(entidades) == 2 and entidades[0] == entidades[1]:
            raise ErrorBoceto("Una cota de distancia necesita dos entidades distintas.")

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

    def _cortes(self, cid, prim=None):
        """[(t, (x, y), id de la otra curva)] donde `cid` cruza o toca a otras curvas, ordenados."""
        prim = self.primitivas(cid)[0] if prim is None else prim
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
        """Alargar (SKT-TRIM-EXTEND): extiende el extremo más cercano al clic hasta la próxima
        intersección. Una spline abierta se prolonga por su tangente, sin cambiar el tramo original;
        pasa a puntos de control. Un arco circular o elíptico continúa sobre su curva portadora."""
        c = self._curva_modificable(cid)
        if not isinstance(c, (Linea, Arco, ArcoElipse, Spline)) or not c.extremos():
            raise ErrorBoceto("Alargar funciona con líneas, arcos circulares o elípticos y splines abiertas.")
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
            if L < 1e-9:
                raise ErrorBoceto("No se puede alargar una línea de longitud cero.")
            d = ((b[0] - a[0]) / L, (b[1] - a[1]) / L)
            rayo = ("linea", None, b, (b[0] + d[0] * grande, b[1] + d[1] * grande))
        else:
            prim = self.primitivas(cid)[0]
            if isinstance(c, Spline):
                t0, t1, _ = dominio(prim)
                b, tangente = evaluar_primitiva(prim, t1 if lado_fin else t0, 1)
                rapidez = math.hypot(*tangente)
                if rapidez < 1e-12:
                    raise ErrorBoceto("La spline no tiene una tangente definida en ese extremo.")
                signo = 1 if lado_fin else -1
                d = (signo * tangente[0] / rapidez, signo * tangente[1] / rapidez)
                rayo = ("linea", None, b, (b[0] + d[0] * grande, b[1] + d[1] * grande))
            else:
                # El complemento del arco, recorrido hacia adelante o hacia atrás según el extremo.
                rayo = prim[:4] + (prim[5], prim[4]) if isinstance(c, Arco) else prim[:6] + (prim[7], prim[6])
        mejor = None
        for t, xy, oid in self._cortes(cid, rayo):
            if math.dist(xy, self.coords(extremo)) < 1e-7:
                continue
            clave = t if (isinstance(c, (Linea, Spline)) or lado_fin) else -t
            if mejor is None or clave < mejor[0]:
                mejor = (clave, xy, oid)
        if mejor is None:
            raise ErrorBoceto("No hay ninguna curva para alcanzar en esa dirección.")
        _, xy, oid = mejor
        nuevos, viejos = [], []
        otras = [k for k in self.curvas.values() if k.id != cid and extremo in k.puntos()]
        if isinstance(c, Spline):
            polos, nudos, grado, pesos = prim[2:]
            ids = list(c.pts) if c.modo == "control" else (
                [ini] + [self.agregar_punto(*q) for q in polos[1:-1]] + [fin])
            viejos.extend(c.puntos())
            nuevo = self._punto_corte((0, xy, oid), nuevos)
            b = self.coords(extremo)
            internos = [self.agregar_punto(b[0] + (xy[0] - b[0]) * j / grado,
                                          b[1] + (xy[1] - b[1]) * j / grado) for j in range(1, grado)]
            delta = math.dist(b, xy) / rapidez
            # Un tramo Bézier recto, unido con multiplicidad grado: conserva exactamente la curva anterior.
            if lado_fin:
                ids += internos + [nuevo]
                nudos = list(nudos[:-1]) + [t1 + delta] * (grado + 1)
                pesos = None if pesos is None else list(pesos) + [pesos[-1]] * grado
            else:
                ids = [nuevo] + internos[::-1] + ids
                nudos = [t0 - delta] * (grado + 1) + list(nudos[1:])
                pesos = None if pesos is None else [pesos[0]] * grado + list(pesos)
            self.curvas[cid] = Spline(cid, ids, "control", grado, False, pesos, nudos,
                                      c.construccion, c.eje, c.proyectada)
        elif otras or self._punto_referenciado(extremo):
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
        radio dado; recorta las curvas, agrega las tangencias y la cota de radio. Entre paralelas,
        crea un semicírculo de radio igual a la mitad de su separación. Devuelve el arco."""
        if radio <= 0:
            raise ErrorBoceto("El radio del empalme debe ser positivo.")
        for k in (c1, c2):
            self._curva_modificable(k)
        tipos = (self.tipo_de(c1), self.tipo_de(c2))
        paralelas = False
        if tipos == ("linea", "linea"):
            d1, d2 = self._direccion(c1), self._direccion(c2)
            paralelas = abs(d1[0] * d2[1] - d1[1] * d2[0]) < 1e-12
        if paralelas:
            F, pt1, pt2, radio = self._empalme_paralelas(c1, c2, pick1, pick2)
            expresion = None       # el radio lo determina la separación, no la expresión pedida
        elif tipos == ("linea", "linea"):
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
        ini, fin = (pt1, pt2) if paralelas or a[0] * b[1] - a[1] * b[0] > 0 else (pt2, pt1)
        arco = self.agregar_arco_centro(F, ini, fin)
        self.agregar_restriccion("tangente", [c1, arco])
        self.agregar_restriccion("tangente", [c2, arco])
        self.agregar_cota("radio", [arco], expresion or _numero(radio))
        return arco

    def _empalme_paralelas(self, c1, c2, pick1, pick2):
        """Semicírculo tangente entre paralelas: cierra del lado opuesto a los puntos que se conservan."""
        a1, b1 = self._extremos_linea(c1)
        a2, b2 = self._extremos_linea(c2)
        if min(math.dist(a1, b1), math.dist(a2, b2)) < 1e-9:
            raise ErrorBoceto("El empalme necesita dos líneas de longitud positiva.")
        d = self._direccion(c1)
        if pick1 is not None:
            invertir = math.dist(pick1, a1) > math.dist(pick1, b1)
        elif pick2 is not None:
            conservar, cerrar = (a2, b2) if math.dist(pick2, a2) <= math.dist(pick2, b2) else (b2, a2)
            invertir = (cerrar[0] - conservar[0]) * d[0] + (cerrar[1] - conservar[1]) * d[1] < 0
        else:
            invertir = False
        if invertir:
            d = (-d[0], -d[1])
        distancia = (a2[0] - a1[0]) * -d[1] + (a2[1] - a1[1]) * d[0]
        if abs(distancia) < 1e-9:
            raise ErrorBoceto("Las líneas son colineales: no hay separación para un empalme.")
        lados = []
        for cid, pick in ((c1, pick1), (c2, pick2)):
            ids = sorted(self.curvas[cid].extremos(), key=lambda pid: (
                (self.coords(pid)[0] - a1[0]) * d[0] + (self.coords(pid)[1] - a1[1]) * d[1]))
            if pick is not None and math.dist(pick, self.coords(ids[0])) > math.dist(pick, self.coords(ids[1])):
                raise ErrorBoceto("Elegí el mismo lado a conservar en las dos líneas paralelas.")
            lados.append(ids)
        cierre = max((self.coords(ids[1])[0] - a1[0]) * d[0] +
                     (self.coords(ids[1])[1] - a1[1]) * d[1] for ids in lados)
        t1 = (a1[0] + cierre * d[0], a1[1] + cierre * d[1])
        t2 = (t1[0] - distancia * d[1], t1[1] + distancia * d[0])
        F = ((t1[0] + t2[0]) / 2, (t1[1] + t2[1]) / 2)
        pts, viejos = [], []
        for cid, ids, t in zip((c1, c2), lados, (t1, t2), strict=True):
            pid = self.agregar_punto(*t)
            pts.append(pid)
            ln = self.curvas[cid]
            if ln.p1 == ids[1]:
                ln.p1 = pid
            else:
                ln.p2 = pid
            viejos.append(ids[1])
            self._sin_cotas_de_largo(cid)
        self._depurar(viejos)
        if (t1[0] - F[0]) * d[1] - (t1[1] - F[1]) * d[0] < 0:
            pts.reverse()
        return F, *pts, abs(distancia) / 2

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
        primera = self.agregar_cota("distancia", [virtual, pt1], expr)
        if angulo is not None:
            medido = self.medir_cota("angulo", [ln, l1])
            self.agregar_cota("angulo", [ln, l1], _numero(angulo if abs(medido - angulo) < 1e-6 else 180 - angulo))
        elif distancia2 is None:
            # Distancias iguales (BOC-25): al nombrarse las cotas, la 2.ª pasa a ser «dN» de la 1.ª
            # (Documento._tabla_cotas), así editar una arrastra a la otra. Con distancia2, cada una es independiente.
            self.agregar_cota("distancia", [virtual, pt2], expr, {"igual_a": primera})
        else:
            self.agregar_cota("distancia", [virtual, pt2], _numero(e2))
        return ln

    # ------------------------------------------------------------ MODIFICAR: desfase
    def desfase(self, cid, distancia, punto_lado=None, expresion=None, invertir=False):
        """Desfase (SKT-OFFSET) de la cadena conectada a `cid`: curvas paralelas a `distancia`, con las
        esquinas resueltas por intersección, la restricción de desfase y su cota. Por defecto, una cadena
        cerrada se desfasa hacia afuera (y una abierta, a la izquierda de su recorrido); `punto_lado` elige el
        lado e `invertir` pasa al lado contrario del que tocaba. Devuelve los ids nuevos."""
        if distancia <= 0:
            raise ErrorBoceto("La distancia de desfase debe ser positiva.")
        c0 = self.curvas[cid]
        if isinstance(c0, (Spline, Elipse, ArcoElipse)):
            return [self._desfase_libre(cid, distancia, punto_lado, invertir)]
        cadena, cerrada = self.cadena(cid)
        if len(cadena) == 1 and isinstance(c0, Circulo):
            r = c0.radio
            fuera = (punto_lado is None or math.dist(punto_lado, self.coords(c0.centro)) > r) != bool(invertir)
            if not fuera and distancia >= r:
                raise ErrorBoceto("El desfase es mayor que el radio.")
            nuevo = self.agregar_circulo(c0.centro, r + distancia if fuera else r - distancia, c0.construccion)
            self.agregar_cota("desfase", [cid, nuevo], expresion or _numero(distancia))
            return [nuevo]
        if any(not isinstance(self.curvas[k], (Linea, Arco)) for k, _ in cadena):
            raise ErrorBoceto("El desfase funciona con cadenas de líneas y arcos, círculos, elipses y splines.")
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
        for i, (_, _, c, *_r) in enumerate(elems):
            if isinstance(c, Linea):
                a2 = esquinas[i - 1] if cerrada or i > 0 else portadoras[0][1]
                b2 = esquinas[i] if cerrada or i < m - 1 else portadoras[-1][2]
                direccion = portadoras[i][0][2]  # unitaria, en el sentido de recorrido original
                largo = (b2[0] - a2[0]) * direccion[0] + (b2[1] - a2[1]) * direccion[1]
                if largo <= 1e-9:
                    raise ErrorBoceto("El desfase deja un segmento de largo cero o invierte su dirección.")
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

    def _desfase_libre(self, cid, d, punto_lado, invertir, muestras=48):
        """Desfase de una spline, elipse o arco de elipse: spline de ajuste por puntos de la curva corridos `d` a
        lo largo de su normal (mismo lado por defecto que en las cadenas). shortcut: no queda asociada (sin
        restricción ni cota de desfase, la curva nueva es libre); pasar a un desfase exacto si hace falta."""
        c = self.curvas[cid]
        prim = self.primitivas(cid)[0]
        t0, t1, _ = dominio(prim)
        cerrada = isinstance(c, Elipse) or (isinstance(c, Spline) and c.cerrada)

        def normales(cantidad):
            salida = []
            for t in np.linspace(t0, t1, cantidad, endpoint=not cerrada):
                C, D = evaluar_primitiva(prim, float(t), 1)
                n = math.hypot(*D) or 1.0
                salida.append((C, (-D[1] / n, D[0] / n)))     # normal a la izquierda del recorrido
            return salida
        pts = normales(muestras)
        if punto_lado is not None:
            C, n = min(pts, key=lambda cn: math.dist(cn[0], punto_lado))
            s = 1.0 if n[0] * (punto_lado[0] - C[0]) + n[1] * (punto_lado[1] - C[1]) > 0 else -1.0
        elif cerrada:
            area = sum(p[0][0] * q[0][1] - q[0][0] * p[0][1] for p, q in zip(pts, pts[1:] + pts[:1], strict=True))
            s = -1.0 if area > 0 else 1.0
        else:
            s = 1.0
        if invertir:
            s = -s
        nuevos = [(C[0] + s * d * n[0], C[1] + s * d * n[1]) for C, n in pts]
        densos = [C for C, _n in normales(4 * muestras)]
        if any(min(math.dist(q, C) for C in densos) < 0.9 * d for q in nuevos):
            raise ErrorBoceto("El desfase es mayor que el radio de curvatura de la curva: se pliega sobre sí mismo.")
        return self.agregar_spline(nuevos, "ajuste", 3, cerrada, construccion=c.construccion)

    def soltar_desfase(self, cid, conservar_cota=False):
        """Suelta la asociación de un desfase (Fusion: borrar el glifo de desfase): quita las restricciones de
        desfase y de paralelismo entre la curva original y su copia, y la cota (salvo `conservar_cota`). Las
        curvas quedan. `cid` puede ser la original o la copia; si la original tiene varios desfases, los suelta todos."""
        cotas = [k for k in self.cotas.values() if k.tipo == "desfase" and cid in k.entidades]
        semilla = {cid}.union(*(k.entidades for k in cotas))
        grupos = {r.datos.get("grupo") for r in self.restricciones.values()
                  if r.tipo == "desfase" and semilla & set(r.entidades)}
        viejas = [r for r in self.restricciones.values() if r.tipo == "desfase" and r.datos.get("grupo") in grupos]
        if not viejas and not cotas:
            raise ErrorBoceto(f"La entidad {cid} no forma parte de un desfase.")
        pares = {frozenset(k.entidades) for k in cotas}
        for r in viejas:
            if len(r.entidades) == 4:
                pares |= {frozenset(r.entidades[:2]), frozenset(r.entidades[2:])}
        borrar = [r.id for r in viejas] + [r.id for r in self.restricciones.values()
                                           if r.tipo == "paralela" and frozenset(r.entidades) in pares]
        borrar += [] if conservar_cota else [k.id for k in cotas]
        for i in borrar:
            self.eliminar(i)

    def pegar_de(self, origen, ids, dx=0.0, dy=0.0):
        """Pegar elementos de OTRO boceto (Fusion: Copiar y Pegar entre bocetos): copia las curvas y los puntos
        `ids` de `origen`, corridos (dx, dy), con las restricciones y cotas que quedan enteras dentro de la selección.
        Lo pegado es geometría normal (la proyectada deja de ser fija). Devuelve los ids de las curvas y puntos nuevos."""
        ids = [i for i in ids if i > 0 and (i in origen.curvas or i in origen.puntos)]
        if not ids:
            raise ErrorBoceto("Seleccioná la geometría a copiar (el origen y los ejes no se copian).")
        mapa = {p: self.agregar_punto(origen.puntos[p].x + dx, origen.puntos[p].y + dy) for p in origen.puntos_de(ids)}
        mapa_c = {}
        for i in ids:
            if i in origen.curvas:
                c = origen.curvas[i].remapear(mapa, self._nuevo_id())
                c.proyectada = False
                self.curvas[c.id] = c
                mapa_c[i] = c.id
        for c in self.curvas.values():                      # el texto sobre una curva no copiada vuelve a ser recto
            if isinstance(c, Texto) and c.id in mapa_c.values():
                c.camino = mapa_c.get(c.camino)
        todo = {**mapa, **mapa_c}
        for r in origen.restricciones.values():
            if r.tipo not in ("fijo", "patron", "desfase") and set(r.entidades) <= set(todo):
                self.agregar_restriccion(r.tipo, [todo[e] for e in r.entidades], copy.deepcopy(r.datos))
        for k in origen.cotas.values():
            if set(k.entidades) <= set(todo):
                self.agregar_cota(k.tipo, [todo[e] for e in k.entidades], k.expresion, copy.deepcopy(k.datos),
                                  k.referencia)
        return list(mapa_c.values()) + [q for p, q in mapa.items() if p in ids]

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
                    self.agregar_cota(k.tipo, [todo[e] for e in k.entidades], k.expresion, k.datos, k.referencia)
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
                c.manijas = [[queda if p == sale else p for p in m[:2]] + m[2:] for m in c.manijas]
            if isinstance(c, Texto) and c.marco:
                c.marco = [queda if p == sale else p for p in c.marco]
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
        de longitud de esa geometría se multiplican por el factor. Un punto fijo puede ser la base."""
        if factor <= 0:
            raise ErrorBoceto("El factor de escala debe ser positivo.")
        pts = self.puntos_de(ids)
        fijos = self.puntos_fijos()          # un punto fijo puede ser la base: escalar desde él no lo mueve
        if any(p in fijos and math.dist(self.coords(p), base) > 1e-9 for p in pts):
            raise ErrorBoceto("Hay geometría fija (o proyectada) en la selección que no está en la base: no se puede escalar.")
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
                c.desfase_base *= factor
                c.grosor_decoracion *= factor
                c.ajustes_kerning = [[i, x * factor] for i, x in c.ajustes_kerning]
        for k in self.cotas.values():
            if k.tipo != "angulo" and set(k.entidades) <= afectados:
                for clave in ("desfase", "texto"):      # la ubicación de la cota crece con la figura
                    if clave in k.datos:
                        k.datos[clave] *= factor
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

    def _patron(self, ids, trans, tipo, params, suprimidos=(), pid=None):
        """Copia `ids` por cada transformación `(f, ángulo, extra, datos)` de `trans` (salvo las suprimidas, por
        índice) y registra el patrón para poder editarlo (`editar_patron`). Devuelve las curvas nuevas."""
        ids = [i for i in ids if i in self.curvas or i in self.puntos]
        if not ids:
            raise ErrorBoceto("Seleccioná la geometría del patrón.")
        grupo = self._siguiente
        nuevos, copias = [], {}
        for n, (f, angulo, extra, datos) in enumerate(trans):
            if n in suprimidos:
                continue
            mapa, mapa_c = self._copiar(ids, f, False, angulo, extra)
            for p, q in mapa.items():
                self.agregar_restriccion("patron", [p, q] + extra, {**datos, "grupo": grupo})
            for i, k in mapa_c.items():
                if isinstance(self.curvas[i], (Circulo, Elipse, ArcoElipse)):
                    self.agregar_restriccion("igual", [i, k])
            copias[str(n)] = list(mapa_c.values()) + list(mapa.values())
            nuevos += list(mapa_c.values())
        registro = {"id": pid if pid is not None else self._nuevo_id(), "tipo": tipo, "ids": list(ids),
                    "params": params, "suprimidos": sorted(suprimidos), "copias": copias}
        self.patrones = [r for r in self.patrones if r["id"] != registro["id"]] + [registro]
        self.ultimo_patron = registro["id"]
        return nuevos

    def _dir_patron(self, vector, linea):
        """Dirección de un patrón: la de la línea del boceto (de su inicio a su fin) o el vector dado."""
        if linea is None:
            return vector
        a, b = self._extremos_linea(linea)
        return b[0] - a[0], b[1] - a[1]

    def _trans_rectangular(self, p):
        n1, n2 = p["cantidad1"], p["cantidad2"]
        if n1 < 1 or n2 < 1 or n1 * n2 < 2:
            raise ErrorBoceto("El patrón necesita al menos dos copias.")
        dir1 = self._dir_patron(p["dir1"], p.get("linea1"))
        dir2 = self._dir_patron(p["dir2"], p.get("linea2"))
        largo1, largo2 = math.hypot(*dir1), math.hypot(*dir2)
        if largo1 < 1e-9 or largo2 < 1e-9:
            raise ErrorBoceto("La dirección del patrón no puede ser una línea de largo cero.")

        def paso(n, d):
            if n <= 1:
                return 0.0
            return d / (n - 1) if p["modo"] == "extension" else d
        u, w = (dir1[0] / largo1, dir1[1] / largo1), (dir2[0] / largo2, dir2[1] / largo2)
        s1, s2 = paso(n1, p["distancia1"]), paso(n2, p["distancia2"])
        o1 = -(n1 - 1) // 2 if p["simetrico"] else 0
        o2 = -(n2 - 1) // 2 if p["simetrico"] else 0
        trans = []
        for i in range(n1):
            for j in range(n2):
                if i + o1 == 0 and j + o2 == 0:
                    continue
                dx = (i + o1) * s1 * u[0] + (j + o2) * s2 * w[0]
                dy = (i + o1) * s1 * u[1] + (j + o2) * s2 * w[1]
                trans.append((lambda q, dx=dx, dy=dy: (q[0] + dx, q[1] + dy), 0.0, [], {"dx": dx, "dy": dy}))
        return trans

    def patron_rectangular(self, ids, cantidad1, distancia1, cantidad2=1, distancia2=0.0, dir1=(1.0, 0.0),
                           dir2=(0.0, 1.0), modo="extension", simetrico=False, linea1=None, linea2=None,
                           suprimir=()):
        """Patrón rectangular (SKT-CREATE-RECTANGULAR-PATTERN). modo "extension": la distancia es la total;
        "espaciado": la de cada paso. `linea1` / `linea2` toman la dirección de una línea del boceto. Las copias
        quedan atadas al original (restricción de patrón); `suprimir` son índices de copia que no se crean."""
        params = {"cantidad1": cantidad1, "distancia1": distancia1, "cantidad2": cantidad2, "distancia2": distancia2,
                  "dir1": list(dir1), "dir2": list(dir2), "modo": modo, "simetrico": simetrico,
                  "linea1": linea1, "linea2": linea2}
        return self._patron(ids, self._trans_rectangular(params), "rectangular", params, set(suprimir))

    def _trans_circular(self, p):
        if p["cantidad"] < 2:
            raise ErrorBoceto("El patrón necesita al menos dos copias.")
        centro = p["centro"]
        es_punto = isinstance(centro, (int, np.integer)) and not isinstance(centro, bool)
        cp = self._punto(centro) if es_punto else None
        c = self.coords(cp) if cp is not None else (float(centro[0]), float(centro[1]))
        cantidad, total = p["cantidad"], p["angulo_total"]
        completo = abs(abs(total) - 360.0) < 1e-9
        paso = total / cantidad if completo else total / (cantidad - 1)
        desde = -(cantidad - 1) // 2 if p["simetrico"] and not completo else 0
        trans = []
        for k in range(cantidad):
            if k + desde == 0:
                continue
            a = math.radians((k + desde) * paso)
            datos = {"angulo": a} if cp is not None else {"angulo": a, "centro": c}
            trans.append((lambda q, a=a: (lambda r: (r[0] + c[0], r[1] + c[1]))(_rot(q[0] - c[0], q[1] - c[1], a)),
                          math.degrees(a), [cp] if cp is not None else [], datos))
        return trans, cp

    def patron_circular(self, ids, centro, cantidad, angulo_total=360.0, simetrico=False, suprimir=()):
        """Patrón circular (SKT-CREATE-CIRCULAR-PATTERN) alrededor de `centro` (id de punto o (u, v)). Con
        coordenadas NO se crea un punto en el centro (B-55): el giro queda atado a un centro fijo; con id de
        punto, las copias lo siguen si se mueve. `suprimir`: índices de copia que no se crean."""
        es_punto = isinstance(centro, (int, np.integer)) and not isinstance(centro, bool)
        params = {"centro": int(centro) if es_punto else list(centro), "cantidad": cantidad,
                  "angulo_total": angulo_total, "simetrico": simetrico}
        trans, cp = self._trans_circular(params)
        return self._patron([i for i in ids if i != cp], trans, "circular", params, set(suprimir))

    def editar_patron(self, pid, **cambios):
        """Edita un patrón ya hecho (cantidades, distancias, direcciones, `suprimidos`): borra sus copias y las
        regenera con los parámetros nuevos, así que las cotas puestas sobre las copias se pierden. Devuelve las
        curvas nuevas."""
        registro = next((r for r in self.patrones if r["id"] == pid), None)
        if registro is None:
            raise ErrorBoceto(f"No existe el patrón {pid}.")
        suprimidos = set(cambios.pop("suprimidos", registro["suprimidos"]))
        params = {**registro["params"], **cambios}
        ids = [i for i in registro["ids"] if i in self.curvas or i in self.puntos]
        if not ids:
            raise ErrorBoceto("El patrón ya no tiene geometría original.")
        if registro["tipo"] == "rectangular":
            trans, cp = self._trans_rectangular(params), None
        else:
            trans, cp = self._trans_circular(params)
        copiado = [i for lista in registro["copias"].values() for i in lista]
        for i in [i for i in copiado if i in self.curvas] + [i for i in copiado if i in self.puntos]:
            if i in self.curvas or i in self.puntos:
                self.eliminar(i)
        return self._patron([i for i in ids if i != cp], trans, registro["tipo"], params, suprimidos, pid)

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
        la cuerda total / tramos, que no cambia la forma). Devuelve el id de la línea."""
        c = self._spline(sid, "ajuste")
        if c.cerrada:
            raise ErrorBoceto("Las manijas se activan en una spline de ajuste abierta: abrila primero.")
        if pid not in c.pts:
            raise ErrorBoceto(f"El punto {pid} no es un punto de ajuste de la spline {sid}.")
        if any(m[0] == pid for m in c.manijas):
            raise ErrorBoceto(f"El punto {pid} ya tiene manija: editala.")
        Q = [self.coords(p) for p in c.pts]
        u = parametros_cuerda(Q)[c.pts.index(pid)]
        d = evaluar_primitiva(self.primitivas(sid)[0], u, 1)[1]
        a = math.radians(angulo) if angulo is not None else math.atan2(d[1], d[0])
        largo = sum(math.dist(Q[i], Q[i - 1]) for i in range(1, len(Q))) / (len(Q) - 1) if largo is None else largo
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
                raise ErrorBoceto("Desactivá las manijas antes de cerrar la spline.")
            ultimo = c.pts[-1]
            if len(c.pts) > 3 and math.dist(self.coords(c.pts[0]), self.coords(ultimo)) < 1e-9:
                c.pts.pop()
                self._depurar([ultimo])
            if len(c.pts) < 3:
                raise ErrorBoceto("Una spline cerrada necesita al menos tres puntos.")
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
            raise ErrorBoceto("El punto nuevo tiene que caer entre los extremos de la spline.")
        if c.modo == "ajuste":
            Q = [self.coords(p) for p in c.pts]
            ub = parametros_cuerda(Q + [Q[0]] if c.cerrada else Q)
            i = next(j for j in range(len(ub) - 1) if t <= ub[j + 1])
            if min(t - ub[i], ub[i + 1] - t) < 1e-6:
                raise ErrorBoceto("Ya hay un punto de ajuste ahí.")
            nuevo = self.agregar_punto(*sobre)
            c.pts.insert(i + 1, nuevo)
            return nuevo
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

    def cambiar_grado_spline(self, sid, grado):
        """Change Spline Degree de Fusion (spline de puntos de control, 3 ↔ 5). Subir no cambia la forma (los nudos
        interiores ganan multiplicidad y suman polos); bajar la simplifica (menos polos, nudos uniformes) y conserva
        los extremos. Ajuste por mínimos cuadrados sobre la curva; una spline racional pasa a no racional."""
        c = self._spline(sid, "control")
        if grado not in (3, 5):
            raise ErrorBoceto("El grado de una spline de puntos de control es 3 o 5.")
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
        viejos = list(c.pts)
        ids = viejos[:min(n, len(viejos)) - 1]
        ids += [self.agregar_punto(0.0, 0.0) for _ in range(n - 1 - len(ids))] + [viejos[-1]]
        for pid, (x, y) in zip(ids, coords, strict=True):
            self.puntos[pid].x, self.puntos[pid].y = float(x), float(y)
        c.pts, c.grado, c.nudos, c.pesos = ids, grado, nuevos, None
        self._depurar([v for v in viejos if v not in ids])

    # ------------------------------------------------------------ texto
    def agregar_marco_texto(self, tid, ancho, alto):
        """Marco del texto (Fusion: el rectángulo de Text, que se acota): 4 líneas de construcción desde su `punto`
        (esquina de abajo a la izquierda) con el giro del texto; perpendicular y paralelas, así se puede girar.
        Devuelve los ids de las 4 líneas."""
        t = self.curvas[tid]
        if not (1e-6 < ancho < math.inf and 1e-6 < alto < math.inf):
            raise ErrorBoceto("El marco del texto necesita ancho y alto positivos.")
        (ax, ay), a = self.coords(t.punto), math.radians(t.angulo)
        u, v = (math.cos(a), math.sin(a)), (-math.sin(a), math.cos(a))
        der = self.agregar_punto(ax + ancho * u[0], ay + ancho * u[1])
        opuesta = self.agregar_punto(ax + ancho * u[0] + alto * v[0], ay + ancho * u[1] + alto * v[1])
        arriba = self.agregar_punto(ax + alto * v[0], ay + alto * v[1])
        lados = [self.agregar_linea(i, j, construccion=True)
                 for i, j in ((t.punto, der), (der, opuesta), (opuesta, arriba), (arriba, t.punto))]
        self.agregar_restriccion("perpendicular", [lados[0], lados[1]])
        self.agregar_restriccion("paralela", [lados[0], lados[2]])
        self.agregar_restriccion("paralela", [lados[1], lados[3]])
        t.marco, t.ancho_caja = [der, arriba], float(ancho)
        return lados

    def girar_texto(self, tid, angulo, pivote=None):
        """Gira el texto (y su marco) hasta `angulo` grados alrededor de `pivote` (por defecto, su ancla)."""
        t = self.curvas[tid]
        actual = math.degrees(_medidas_marco(*map(self.coords, t.puntos()))[0]) if t.marco else t.angulo
        self.transformar([tid] + self._lineas_auxiliares(t), angulo=angulo - actual,
                         centro=self.coords(t.punto) if pivote is None else pivote)
        t.angulo = float(angulo)

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
        d = {"siguiente_id": self._siguiente,
             "puntos": [p.a_dict() for p in self.puntos.values()],
             "curvas": [c.a_dict() for c in self.curvas.values()],
             "restricciones": [r.a_dict() for r in self.restricciones.values()],
             "cotas": [c.a_dict() for c in self.cotas.values()]}
        if self.proyecciones:
            d["proyecciones"] = copy.deepcopy(self.proyecciones)
        if self.patrones:
            d["patrones"] = copy.deepcopy(self.patrones)
        return d

    @classmethod
    def desde_dict(cls, d):
        b = cls()
        b._siguiente = d.get("siguiente_id", 1)
        b.proyecciones = copy.deepcopy(d.get("proyecciones", []))
        for n, r in enumerate(b.proyecciones, 1):          # los proyectos viejos no numeraban sus proyecciones
            r.setdefault("id", n)
        b.patrones = copy.deepcopy(d.get("patrones", []))
        for p in d.get("puntos", []):
            b.puntos[p["id"]] = Punto(p["id"], p["x"], p["y"], p.get("proyectado", False))
        for c in d.get("curvas", []):
            datos = {k: v for k, v in c.items() if k != "tipo"}
            b.curvas[c["id"]] = _CURVAS[c["tipo"]](**datos)
        for r in d.get("restricciones", []):
            b.restricciones[r["id"]] = Restriccion(r["id"], r["tipo"], r["entidades"], r.get("datos"))
        for c in d.get("cotas", []):
            b.cotas[c["id"]] = Cota(c["id"], c["tipo"], c["entidades"], c["expresion"], c.get("datos"), c.get("nombre", ""),
                                   c.get("referencia", False))
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


def distancia_con_circulo(tipos, entidades, modo, P, C, R, L, anidados=None):
    """Distancia CON signo de una cota de distancia con un círculo o arco (BOC-3; la medida es su valor absoluto).
    `P(pid)`, `C(cid)` (centro), `R(cid)` y `L(lid)` (extremos) dan la geometría: la usan el boceto y el solver.
    modo "centro": hasta el centro; "tangente": hasta el borde más cercano (entre círculos, de borde a borde;
    `anidados` congela si uno está adentro del otro, None = según la geometría)."""
    if tipos[0] not in CIRCULARES:
        tipos, entidades = tipos[::-1], entidades[::-1]
    c, o = entidades
    if tipos[1] == "punto":
        d = math.dist(P(o), C(c))
        return d if modo == "centro" else d - R(c)
    if tipos[1] == "linea":
        d = distancia_punto_recta(C(c), *L(o))
        return d if modo == "centro" else abs(d) - R(c)
    d = math.dist(C(c), C(o))
    if modo == "centro":
        return d
    r1, r2 = R(c), R(o)
    if anidados is None:
        anidados = d < abs(r1 - r2)
    return abs(r1 - r2) - d if anidados else d - r1 - r2


def distancia_punto_recta(p, a, b):
    """Distancia CON signo de p a la recta a→b (positiva a la izquierda)."""
    (px, py), (ax, ay), (bx, by) = p, a, b
    n = math.hypot(bx - ax, by - ay)
    if n < 1e-12:
        return math.hypot(px - ax, py - ay)
    return ((bx - ax) * (py - ay) - (by - ay) * (px - ax)) / n

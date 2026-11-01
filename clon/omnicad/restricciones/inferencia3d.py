# -*- coding: utf-8 -*-
"""Ayudas de dibujo del Boceto 3D (Fusion: 3D Sketch › ayudas de dibujo): alineaciones, punto medio, intersección,
tangente, perpendicular y sobre la curva, sin modificar el boceto.

Lo que es de la geometría se engancha EN EL ESPACIO (`_en_espacio`): medios, cruces reales, pies, contactos tangentes y
puntos sobre una curva son puntos 3D de verdad, se buscan por su distancia al rayo del cursor y pueden caer fuera del
plano activo, y `uniones` dice qué restricciones 3D dejan (también con arcos, círculos, elipses, cónicas y splines).
Lo que es del plano activo (alineaciones, horizontal/vertical con los ejes de la tríada, lo que solo se cruza visto desde
él) sale de proyectar la geometría a ESE plano (`Proyeccion`: un `Boceto` 2D de apoyo con las líneas, los puntos y los arcos
y círculos paralelos al plano; el resto entra como tramos rectos) y reusar `inferencias`: esas caen en el plano y no dejan
restricción si no se cumple. Quien dibuja agrega las restricciones solo si la geometría ya las cumple. Puro: sin Qt."""
import math
from dataclasses import dataclass, field
from itertools import combinations

import numpy as np

from . import boceto3d as b3
from .boceto import Boceto, ErrorBoceto, circunferencia_3_puntos
from .inferencia import FACTOR_HISTERESIS, TOPE_CRUCES, Indice, Inferencia, inferencias

TIPOS_3D = ("medio", "interseccion", "tangente", "perpendicular", "curva", "alineacion", "horizontal", "vertical")
PLANOS = {"xy": ((1, 0, 0), (0, 1, 0)), "yz": ((0, 1, 0), (0, 0, 1)), "zx": ((0, 0, 1), (1, 0, 0))}   # (u, v) de la tríada sin girar
TRAMOS_APROX = 24          # shortcut: elipse, cónica, spline y arco/círculo inclinados se aproximan con 24 tramos
MUESTRAS = 72              # puntos por curva para buscarla cerca del rayo del cursor (después se afina)
ANGULO = math.radians(3)   # como en `inferencias`: tolerancia de dirección de tangente y perpendicular
_EJES = {"horizontal": "el eje X de la tríada", "vertical": "el eje Y de la tríada"}


@dataclass
class Ayuda3D:
    """Una ayuda del cursor ya en coordenadas del boceto (x, y, z): dónde cae, qué guías dibujar y qué decir."""
    tipo: str
    punto: np.ndarray
    guias: list = field(default_factory=list)       # [(a, b)] con a y b = np.ndarray de 3
    etiqueta: str = ""
    inferencia: Inferencia | None = None
    uniones: dict | None = None                     # lo que deja un clic (ver `uniones`), si la ayuda es del espacio


class Proyeccion:
    """El boceto 3D `b` visto desde el plano (origen, u, v): lo que `inferencias` necesita, armado una sola vez."""

    def __init__(self, b, plano, origen, u, v):
        self.o, self.u, self.v = (np.asarray(x, float) for x in (origen, u, v))
        self.n = np.cross(self.u, self.v)
        self.b2, self.aprox, self._puntos_aprox = Boceto(), {}, set()     # aprox: tramo recto → id de su curva 3D
        self.lineas3d = {}                                # id de línea del boceto de apoyo → id de la línea 3D
        self.g = g = b3.datos(b)
        self.espacio = {}                                 # id de curva 3D → (`Curva`, parámetros, puntos muestreados)
        puntos = {pid: self.b2.agregar_punto(*self.a_plano(p)) for pid, p in g["puntos"].items()}
        self.puntos = {pid: self.a_plano(p) for pid, p in g["puntos"].items()}
        for cid, c in g["curvas"].items():
            try:
                if not self._exacta(b, g, puntos, cid, c):
                    self._aproximar(b, plano, puntos, cid, c)
            except ErrorBoceto:
                pass                                      # una curva degenerada vista desde acá (de canto): sin ayudas
            try:
                cur = b3.curva_parametrica(b, cid)
            except ErrorBoceto:
                continue                                  # un texto o una curva que no se puede construir
            ts = np.linspace(cur.t0, cur.t1, MUESTRAS + 1)
            self.espacio[cid] = (cur, ts, np.array([cur.f(t)[0] for t in ts]))
        self.indice = i = Indice(self.b2)
        i.refs = [r for r in i.refs if r[3] not in self._puntos_aprox and r[3] not in self.aprox]   # sus vértices no alinean
        i.rx, i.ry = np.array([r[0] for r in i.refs]), np.array([r[1] for r in i.refs])

    def a_plano(self, p):
        d = np.asarray(p, float) - self.o
        return (float(d @ self.u), float(d @ self.v))

    def a_3d(self, xy):
        return self.o + self.u * xy[0] + self.v * xy[1]

    def _paralela(self, normal):
        normal = np.asarray(normal, float)
        largo = float(np.linalg.norm(normal))
        return largo > 1e-12 and abs(abs(float(normal @ self.n)) / largo - 1.0) < 1e-9

    def _exacta(self, b, g, puntos, cid, c):
        """Agrega la curva con su forma si se ve igual desde el plano (línea, y arco o círculo paralelos). False si no."""
        t, ids = c["tipo"], c["puntos"]
        if t == "linea":
            self.lineas3d[self.b2.agregar_linea(puntos[ids[0]], puntos[ids[1]])] = cid
            return True
        if t == "circulo" and self._paralela(c["normal"]):
            self.b2.agregar_circulo(puntos[ids[0]], c["radio"])
            return True
        if t == "arco":
            a, m, f = (np.array(g["puntos"][i], float) for i in ids)
            if self._paralela(np.cross(m - a, f - a)) and circunferencia_3_puntos(*(self.a_plano(q) for q in (a, m, f))):
                self.b2.agregar_arco_3_puntos(puntos[ids[0]], self.a_plano(m), puntos[ids[2]])
                return True
        return False

    def _aproximar(self, b, plano, puntos, cid, c):
        if c["tipo"] == "texto":
            return
        for poli in b3.polilineas_de(b, cid, plano, TRAMOS_APROX):
            xy = [self.a_plano(b3.a_boceto(plano, q)) for q in poli]
            ids = [self.b2.agregar_punto(*q) for q in xy]
            self._puntos_aprox.update(ids)
            for (p, q), (i, j) in zip(zip(xy, xy[1:], strict=False), zip(ids, ids[1:], strict=False), strict=True):
                if math.dist(p, q) > 1e-9:
                    self.aprox[self.b2.agregar_linea(i, j)] = cid


def proyectar(b, plano, origen, u, v):
    return Proyeccion(b, plano, origen, u, v)


def _dist_al_rayo(o, d, q):
    """Distancia del punto q (o de los puntos Nx3) a la recta del rayo: es lo que el cursor ve en pantalla."""
    v = np.asarray(q, float) - o
    if v.ndim == 2:
        return np.linalg.norm(v - np.outer(v @ d, d), axis=1)
    return float(np.linalg.norm(v - float(v @ d) * d))


def _sobre_recta(p, t, o, d):
    """El punto de la recta p + s·t más cercano al rayo."""
    t = t / max(float(np.linalg.norm(t)), 1e-12)
    w, c = p - o, float(t @ d)
    den = 1.0 - c * c
    return p if den < 1e-12 else p + t * ((c * float(w @ d) - float(w @ t)) / den)


def _en_direccion(base, q, o, d):
    """Si la dirección base→q está a menos de `ANGULO` de la de base→cursor (el punto del rayo a la altura de q)."""
    u, v = o + float((q - o) @ d) * d - base, q - base
    return (float(np.linalg.norm(u)) > 1e-9 and float(np.linalg.norm(v)) > 1e-9
            and math.atan2(float(np.linalg.norm(np.cross(u, v))), float(u @ v)) <= ANGULO)


def _cercano_al_rayo(cur, ts, ds, o, d):
    """Parámetro de la curva más cercano al rayo: la mejor muestra de `ds`, afinada entre sus vecinas."""
    from scipy.optimize import minimize_scalar
    i = int(np.argmin(ds))
    paso = ts[1] - ts[0]
    lo, hi = ts[i] - paso, ts[i] + paso
    if cur.marco is None or cur.t1 < math.tau - 1e-9:
        lo, hi = max(lo, cur.t0), min(hi, cur.t1)
    return float(minimize_scalar(lambda t: _dist_al_rayo(o, d, cur.f(t)[0]), bounds=(lo, hi), method="bounded",
                                 options={"xatol": 1e-9}).x)


def _contactos(cur, base, o, d):
    """Tangentes desde `base` a un arco, círculo o elipse: (punto, True) en cada contacto o, con la base sobre la curva,
    (punto de su tangente más cercano al rayo, False). Con la base fuera de su plano no hay: esa recta no la toca tangente."""
    c, e1, e2, a, b = cur.marco
    v = base - c
    if abs(float(v @ np.cross(e1, e2))) > 1e-6:
        return
    x, y = float(v @ e1) / a, float(v @ e2) / b
    r, ang = math.hypot(x, y), math.atan2(y, x)
    if abs(r - 1.0) * max(a, b) < 1e-9:
        if cur.en_tramo(ang):
            yield _sobre_recta(base, cur.f(ang)[1], o, d), False
    elif r > 1.0:
        for t in (ang - math.acos(1 / r), ang + math.acos(1 / r)):
            if cur.en_tramo(t):
                yield cur.f(t)[0], True


def _cruce(ca, cc, s, t):
    """(s, t) donde las dos curvas se tocan de verdad, arrancando de (s, t); None si solo se cruzan vistas desde el cursor."""
    from scipy.optimize import least_squares
    sol = least_squares(lambda x: ca.f(x[0])[0] - cc.f(x[1])[0], [s, t], xtol=1e-14, ftol=1e-14, gtol=1e-14)
    return tuple(sol.x) if float(np.max(np.abs(sol.fun))) < 1e-8 else None


def _en_espacio(proy, o, d, tol, base, tipos):
    """Las ayudas que son puntos reales de la geometría 3D a menos de `tol` del rayo (o, d)."""
    salida, cerca = [], []

    def sumar(tipo, q, cid, clase, etiqueta, punto=(), curva=(), guias=(), refs=None):
        distancia = _dist_al_rayo(o, d, q)
        if distancia <= tol:
            inf = Inferencia(tipo, proy.a_plano(q), cid, None, [], etiqueta, distancia, clase, refs or (cid,))
            salida.append(Ayuda3D(tipo, np.array(q, float), list(guias), etiqueta, inf,
                                  {"punto": list(punto), "curva": list(curva)}))

    for cid, (cur, ts, pts) in proy.espacio.items():
        tipo = proy.g["curvas"][cid]["tipo"]
        if "medio" in tipos and tipo in ("linea", "arco"):
            sumar("punto_medio", cur.f((cur.t0 + cur.t1) / 2)[0], cid, 0, "Punto medio",
                  [("punto_medio" if tipo == "linea" else "coincidente", cid)])
        if base is not None and cur.marco is not None and "tangente" in tipos:
            for q, contacto in _contactos(cur, base, o, d):
                if _en_direccion(base, q, o, d):
                    sumar("tangente", q, cid, 1, "Tangente a la curva", [("coincidente", cid)] if contacto else (),
                          [("tangente", cid)], [(base, q)])
        ds = _dist_al_rayo(o, d, pts)
        if float(ds.min()) > tol + float(np.max(np.linalg.norm(pts[1:] - pts[:-1], axis=1))):
            continue                                     # lejos: ni se afina
        t = _cercano_al_rayo(cur, ts, ds, o, d)
        q = cur.f(t)[0]
        if _dist_al_rayo(o, d, q) > tol:
            continue
        cerca.append((_dist_al_rayo(o, d, q), cid, t))
        sobre_ella = False
        if base is not None and tipo == "linea":
            a, u = cur.f(0.0)
            sobre_ella = float(np.linalg.norm(np.cross(base - a, u))) < 1e-6 * float(np.linalg.norm(u))
            s = float((base - a) @ u) / float(u @ u)
            pie = a + s * u
            if "perpendicular" in tipos and not sobre_ella and _en_direccion(base, pie, o, d):
                sumar("perpendicular", pie, cid, 2, "Perpendicular a la línea", [("coincidente", cid)] if 0 <= s <= 1 else (),
                      [("perpendicular", cid)], [(base, pie)])
        if "curva" in tipos and not sobre_ella:          # dibujar por encima de la propia recta no es unirse a ella
            sumar("sobre_curva", q, cid, 3, "Sobre la curva", [("coincidente", cid)])

    if "interseccion" in tipos:
        cerca.sort(key=lambda c: c[:2])
        for (_, ca, s), (_, cc, t) in combinations(cerca[:TOPE_CRUCES], 2):
            cur_a, cur_c = proy.espacio[ca][0], proy.espacio[cc][0]
            x = _cruce(cur_a, cur_c, s, t)
            if x is None or not (cur_a.en_tramo(x[0]) and cur_c.en_tramo(x[1])):
                continue
            q = cur_a.f(x[0])[0]
            comunes = set(proy.g["curvas"][ca]["puntos"]) & set(proy.g["curvas"][cc]["puntos"])
            if not any(np.allclose(q, proy.g["puntos"][p], atol=1e-7) for p in comunes):   # un extremo compartido no es un cruce
                sumar("interseccion", q, ca, 0, "Intersección", [("coincidente", ca), ("coincidente", cc)],
                      refs=tuple(sorted((ca, cc))))
    return salida


def uniones(proy, ayuda):
    """Las restricciones 3D que deja un clic en la ayuda `ayuda`: {"punto": [(tipo, id de curva 3D)]} para el punto del
    clic (punto medio, sobre la curva) y {"curva": [(tipo, id de curva 3D o None)]} para la línea que sale de la base
    (perpendicular, tangente; `eje` con id None: el eje lo da la dirección de la línea al crearla)."""
    if ayuda is not None and ayuda.uniones is not None:
        return ayuda.uniones
    salida = {"punto": [], "curva": []}
    r = ayuda.inferencia.restriccion if ayuda is not None and ayuda.inferencia is not None else None
    if not r:
        return salida
    if r[0] in ("punto_medio", "coincidente"):
        destinos = [r[1]] + ([r[2][1]] if len(r) > 2 and r[2][0] == "coincidente" else [])    # la intersección une dos
        for d in destinos:
            if d in proy.lineas3d:
                salida["punto"].append(("punto_medio" if r[0] == "punto_medio" else "coincidente", proy.lineas3d[d]))
    elif r[0] == "perpendicular" and r[1] in proy.lineas3d:
        salida["curva"].append(("perpendicular", proy.lineas3d[r[1]]))
        if len(r) > 2:                                    # el pie cae sobre la línea (no en su prolongación)
            salida["punto"].append(("coincidente", proy.lineas3d[r[1]]))
    elif r[0] in ("horizontal", "vertical"):
        salida["curva"].append(("eje", None))
    return salida


def ayudas(proy, cursor, tol, base=None, tipos=None, previa=None, rayo=None):
    """Las ayudas del cursor, la mejor primero. `cursor` es su punto sobre el plano activo (None si la vista lo mira de
    canto) y `rayo` (origen, dirección) la recta que el cursor ve en el espacio; sin rayo, la perpendicular al plano por
    el cursor. `tol` en mm; `base`, el punto anterior de la herramienta (para tangente, perpendicular y
    horizontal/vertical); `previa`, la ayuda anterior (histéresis). Sin ayuda: lista vacía."""
    tipos = TIPOS_3D if tipos is None else tipos
    o, d = rayo if rayo is not None else (cursor, proy.n)
    o, d = np.asarray(o, float), np.asarray(d, float) / np.linalg.norm(d)
    anterior = previa.inferencia if previa is not None else None
    salida = [a for a in _en_espacio(proy, o, d, tol * FACTOR_HISTERESIS if previa is not None else tol, base, tipos)
              if a.inferencia.distancia <= tol or (anterior is not None and a.inferencia.clave() == anterior.clave())]
    del_plano = () if cursor is None else inferencias(
        proy.b2, proy.a_plano(cursor), tol, base=proy.a_plano(base) if base is not None else None, indice=proy.indice,
        tipos=[t for t in tipos if t not in ("medio", "curva")], previa=anterior)   # esas dos, siempre en el espacio
    for inf in del_plano:
        if inf.objetivo in proy.aprox and inf.tipo in ("tangente", "tangente_circulo", "perpendicular"):
            continue                                     # el contacto con un tramo de una curva aproximada no es de la curva
        if inf.tipo.startswith("interseccion") and (
                len({proy.aprox.get(r, r) for r in inf.referencias}) == 1                # dos tramos de la misma curva
                or any(math.dist(inf.xy, q) < 1e-9 for q in proy.puntos.values())):      # ahí ya hay un punto
            continue
        punto = proy.a_3d(inf.xy)
        if any(a.tipo == inf.tipo and np.allclose(a.punto, punto) for a in salida):
            continue                                     # la misma ayuda, ya encontrada en el espacio
        etiqueta = inf.etiqueta or inf.tipo.capitalize()
        if inf.tipo in _EJES:
            etiqueta = f"Alineado con {_EJES[inf.tipo]}"
        salida.append(Ayuda3D(inf.tipo, punto, [(proy.a_3d(a), proy.a_3d(c)) for a, c in inf.guias], etiqueta, inf))
    salida.sort(key=lambda a: (a.inferencia.clase, round(a.inferencia.distancia, 9), a.tipo != "interseccion",
                               a.inferencia.objetivo or 0, a.tipo))
    if anterior is not None and salida:                  # entre iguales, la que ya estaba activa no salta
        for i, a in enumerate(salida):
            if a.inferencia.clase == salida[0].inferencia.clase and a.inferencia.clave() == anterior.clave():
                salida.insert(0, salida.pop(i))
                break
    return salida

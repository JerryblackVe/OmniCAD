# -*- coding: utf-8 -*-
"""
Candidatos de AutoConstrain (SKT-AUTO-CONSTRAIN): lo que el boceto ya cumple y se puede convertir en restricción.

Cada función recorre la geometría y entrega tuplas (tipo, entidades, descripción) por prioridad. Solo MIRAN el
boceto: quien decide si un candidato entra es `solver.auto_restringir`, que lo prueba (baja los grados de
libertad, sin conflicto, con residuo cero) antes de dejarlo. Para no probar millones de pares, las líneas
paralelas, perpendiculares y colineales se agrupan en clases y cada miembro se compara con el primero de su clase.
"""
import math
from collections import defaultdict
from itertools import combinations

import numpy as np

from .boceto import (CIRCULARES, CON_CENTRO, ELIPTICAS, GEOMETRICAS, Linea, dominio, evaluar_primitiva,
                     mas_cercano, primitivas_entidad)

TOPE_EJES_SIMETRIA = 16     # shortcut: solo las primeras 16 líneas de construcción/eje se prueban como eje de simetría


def _lineas(b):
    return [c for c in b.curvas.values() if isinstance(c, Linea) and not c.proyectada]


def _angulo(b, lid):
    """Dirección de la línea en grados, en [0, 180)."""
    (x1, y1), (x2, y2) = b._extremos_linea(lid)
    return math.degrees(math.atan2(y2 - y1, x2 - x1)) % 180


def _es_eje(ang, tol):
    return min(ang, 180 - ang) < tol or abs(ang - 90) < tol


def _diferencia(a, c):
    """Diferencia entre dos direcciones en grados, módulo 180."""
    d = abs(a - c)
    return min(d, 180 - d)


def _fijan_ejes(tipos):
    """True si las horizontales y verticales ya se fijan por su propia restricción (paralela y perpendicular las saltean)."""
    return "horizontal" in tipos and "vertical" in tipos


def _prim(b, cid):
    return primitivas_entidad(b.curvas[cid], b.coords)[0]


# ---------------------------------------------------------------- coincidencias y concentricidad
def coincidencias(b, tol_angulo, tol_distancia, tipos):
    """Puntos en el mismo lugar: coincidente, o concentrica si son los centros de dos círculos/arcos/elipses."""
    ids = list(b.puntos)
    if len(ids) < 2:
        return
    xy = np.array([b.coords(p) for p in ids])
    centro_de = {}
    for c in b.curvas.values():
        if c.tipo in CON_CENTRO:
            centro_de.setdefault(c.centro, c.id)
    for i, p in enumerate(ids[:-1]):
        d = np.hypot(*(xy[i + 1:] - xy[i]).T)
        for j in np.nonzero(d < tol_distancia)[0]:
            q = ids[i + 1 + j]
            a, c = centro_de.get(p), centro_de.get(q)
            if a is not None and c is not None and "concentrica" in tipos:
                if a != c:
                    yield "concentrica", [a, c], f"concentrica {a}-{c}"
            else:
                yield "coincidente", [p, q], f"coincidente {p}-{q}"


# ---------------------------------------------------------------- líneas
def horizontales_verticales(b, tol_angulo, tol_distancia, tipos):
    for ln in _lineas(b):
        ang = _angulo(b, ln.id)
        if min(ang, 180 - ang) < tol_angulo:
            yield "horizontal", [ln.id], f"horizontal {ln.id}"
        elif abs(ang - 90) < tol_angulo:
            yield "vertical", [ln.id], f"vertical {ln.id}"


def colineales(b, tol_angulo, tol_distancia, tipos):
    """Líneas sobre la misma recta: cada una contra la primera de su clase."""
    clases = []     # (id, origen, dirección unitaria, ángulo)
    for ln in _lineas(b):
        (x1, y1), (x2, y2) = b._extremos_linea(ln.id)
        largo = math.hypot(x2 - x1, y2 - y1)
        if largo < 1e-9:
            continue
        u, ang = ((x2 - x1) / largo, (y2 - y1) / largo), _angulo(b, ln.id)
        for rep, (ox, oy), (ux, uy), a0 in clases:
            if (_diferencia(ang, a0) < tol_angulo and abs(ux * (y1 - oy) - uy * (x1 - ox)) < tol_distancia
                    and abs(ux * (y2 - oy) - uy * (x2 - ox)) < tol_distancia):
                yield "colineal", [rep, ln.id], f"colineal {rep}-{ln.id}"
                break
        else:
            clases.append((ln.id, (x1, y1), u, ang))


def _clases_de_angulo(b, tol_angulo, omitir_ejes):
    """[[ángulo, representante, miembros]]: líneas con la misma dirección (con `omitir_ejes`, sin las horizontales
    ni las verticales, que ya quedan fijadas por su propia restricción)."""
    clases = []
    for ln in _lineas(b):
        ang = _angulo(b, ln.id)
        if omitir_ejes and _es_eje(ang, tol_angulo):
            continue
        for c in clases:
            if _diferencia(ang, c[0]) < tol_angulo:
                c[2].append(ln.id)
                break
        else:
            clases.append([ang, ln.id, []])
    return clases


def paralelas(b, tol_angulo, tol_distancia, tipos):
    for _ang, rep, miembros in _clases_de_angulo(b, tol_angulo, _fijan_ejes(tipos)):
        for m in miembros:
            yield "paralela", [rep, m], f"paralela {rep}-{m}"


def perpendiculares(b, tol_angulo, tol_distancia, tipos):
    """Primero las líneas que comparten un punto (esquinas), después un representante de cada par de clases."""
    omitir_ejes = _fijan_ejes(tipos)
    angulos = {ln.id: _angulo(b, ln.id) for ln in _lineas(b)}
    if omitir_ejes:
        angulos = {k: a for k, a in angulos.items() if not _es_eje(a, tol_angulo)}
    por_punto = defaultdict(list)
    for k in angulos:
        for p in b.curvas[k].puntos():
            por_punto[p].append(k)
    vistos = set()
    for lineas in por_punto.values():
        for a, c in combinations(lineas, 2):
            if abs(_diferencia(angulos[a], angulos[c]) - 90) < tol_angulo and (a, c) not in vistos:
                vistos.add((a, c))
                yield "perpendicular", [a, c], f"perpendicular {a}-{c}"
    clases = _clases_de_angulo(b, tol_angulo, omitir_ejes)
    for c1, c2 in combinations(clases, 2):
        if abs(_diferencia(c1[0], c2[0]) - 90) < tol_angulo:
            yield "perpendicular", [c1[1], c2[1]], f"perpendicular {c1[1]}-{c2[1]}"


# ---------------------------------------------------------------- tangencias
def _tangente_en(b, cid, pid):
    """Tangente unitaria de la curva en su extremo `pid`, hacia adentro de la curva."""
    prim = _prim(b, cid)
    t0, t1, _ = dominio(prim)
    ini = b.curvas[cid].extremos()[0]
    _c, d = evaluar_primitiva(prim, t0 if pid == ini else t1, 1)
    n = math.hypot(*d) or 1e-12
    s = 1.0 if pid == ini else -1.0
    return s * d[0] / n, s * d[1] / n


def _encadenadas(b, tol_angulo):
    """Curvas que se tocan por un extremo (el mismo punto o dos con restricción coincidente) y siguen la misma
    tangente allí: línea-arco, arco-arco, spline-arco…"""
    extremos = defaultdict(set)
    for c in b.curvas.values():
        for p in c.extremos() or ():
            extremos[p].add(c.id)
    for r in b.restricciones.values():
        if r.tipo == "coincidente" and len(r.entidades) == 2 and all(e in b.puntos for e in r.entidades):
            p, q = r.entidades
            extremos[p] = extremos[q] = extremos[p] | extremos[q]
    seno = math.sin(math.radians(tol_angulo))
    for grupo in {frozenset(v) for v in extremos.values() if len(v) > 1}:
        for a, c in combinations(sorted(grupo), 2):
            ta, tc = b.curvas[a].tipo, b.curvas[c].tipo
            comun = b.extremo_comun(a, c)
            if comun is None or ta not in GEOMETRICAS or tc not in GEOMETRICAS or ta == tc == "linea":
                continue
            u, v = _tangente_en(b, a, comun[0]), _tangente_en(b, c, comun[1])
            if abs(u[0] * v[1] - u[1] * v[0]) < seno:
                yield a, c


def tangentes(b, tol_angulo, tol_distancia, tipos):
    """Tangencias: encadenadas por un extremo, línea con círculo/arco/elipse y círculos/arcos entre sí.
    shortcut: spline y cónica solo se detectan encadenadas; elipse con elipse no se detecta."""
    vistos = set()
    for a, c in _encadenadas(b, tol_angulo):
        vistos.add((a, c))
        yield "tangente", [a, c], f"tangente {a}-{c}"
    curvas = [c for c in b.curvas.values() if c.tipo in ("linea", *CIRCULARES, *ELIPTICAS)]
    lineas = [c for c in curvas if isinstance(c, Linea)]
    redondas = [c for c in curvas if c.tipo in CIRCULARES]
    for ln in lineas:
        pl = _prim(b, ln.id)
        (x1, y1), (x2, y2) = pl[2], pl[3]
        largo = math.hypot(x2 - x1, y2 - y1)
        if largo < 1e-9:
            continue
        nx, ny = -(y2 - y1) / largo, (x2 - x1) / largo
        for c in curvas:
            if c is ln or c.tipo == "linea" or (ln.id, c.id) in vistos or (c.id, ln.id) in vistos:
                continue
            (cx, cy) = b.coords(c.centro)
            firmada = nx * (cx - x1) + ny * (cy - y1)
            if c.tipo in CIRCULARES:
                if abs(abs(firmada) - b.radio(c.id)) >= tol_distancia:
                    continue
                contacto = (cx - nx * firmada, cy - ny * firmada)
                if (mas_cercano(pl, contacto)[1] < tol_distancia
                        and (c.tipo == "circulo" or mas_cercano(_prim(b, c.id), contacto)[1] < tol_distancia)
                        and b.extremo_comun(ln.id, c.id) is None):
                    yield "tangente", [ln.id, c.id], f"tangente {ln.id}-{c.id}"
            else:
                _o, a, bb, ang = _elipse(b, c.id)
                nu, nv = nx * math.cos(ang) + ny * math.sin(ang), -nx * math.sin(ang) + ny * math.cos(ang)
                if abs(abs(firmada) - math.hypot(a * nu, bb * nv)) < tol_distancia and b.extremo_comun(ln.id, c.id) is None:
                    yield "tangente", [ln.id, c.id], f"tangente {ln.id}-{c.id}"
    for c1, c2 in combinations(redondas, 2):
        if (c1.id, c2.id) in vistos:
            continue
        (x1, y1), (x2, y2) = b.coords(c1.centro), b.coords(c2.centro)
        d, r1, r2 = math.hypot(x2 - x1, y2 - y1), b.radio(c1.id), b.radio(c2.id)
        if d < tol_distancia:
            continue
        exterior = abs(d - (r1 + r2)) < tol_distancia
        if exterior or abs(d - abs(r1 - r2)) < tol_distancia:
            s = 1.0 if exterior or r1 > r2 else -1.0
            contacto = (x1 + s * r1 * (x2 - x1) / d, y1 + s * r1 * (y2 - y1) / d)
            if (all(c.tipo == "circulo" or mas_cercano(_prim(b, c.id), contacto)[1] < tol_distancia for c in (c1, c2))
                    and b.extremo_comun(c1.id, c2.id) is None):
                yield "tangente", [c1.id, c2.id], f"tangente {c1.id}-{c2.id}"


def _elipse(b, cid):
    """(centro, semieje mayor, semieje menor, giro) de una elipse o arco de elipse."""
    c = b.curvas[cid]
    (cx, cy), (mx, my) = b.coords(c.centro), b.coords(c.mayor)
    return (cx, cy), math.hypot(mx - cx, my - cy), c.radio_menor, math.atan2(my - cy, mx - cx)


# ---------------------------------------------------------------- igualdades
def iguales(b, tol_angulo, tol_distancia, tipos):
    """Largos de líneas (sin las de construcción) y radios iguales, cada uno contra el primero de su grupo."""
    def grupos(items, medida):
        vistos = []
        for k in items:
            m = medida(k)
            base = next((g for g in vistos if abs(g[1] - m) < tol_distancia * max(1.0, m)), None)
            if base is None:
                vistos.append((k, m))
            else:
                yield "igual", [base[0], k], f"igual {base[0]}-{k}"
    yield from grupos([ln.id for ln in _lineas(b) if not ln.construccion], lambda k: math.dist(*b._extremos_linea(k)))
    yield from grupos([c.id for c in b.curvas.values() if c.tipo in CIRCULARES and not c.proyectada], b.radio)


# ---------------------------------------------------------------- punto medio
def puntos_medios(b, tol_angulo, tol_distancia, tipos):
    """Puntos exactamente en el medio de una línea o de un arco."""
    ids = list(b.puntos)
    if not ids:
        return
    xy = np.array([b.coords(p) for p in ids])
    for c in b.curvas.values():
        if isinstance(c, Linea):
            (x1, y1), (x2, y2) = b._extremos_linea(c.id)
            medio = ((x1 + x2) / 2, (y1 + y2) / 2)
        elif c.tipo == "arco":
            prim = _prim(b, c.id)
            medio = evaluar_primitiva(prim, dominio(prim)[1] / 2)[0]
        else:
            continue
        for j in np.nonzero(np.hypot(xy[:, 0] - medio[0], xy[:, 1] - medio[1]) < tol_distancia)[0]:
            if ids[j] not in c.puntos():
                yield "punto_medio", [ids[j], c.id], f"punto_medio {ids[j]}-{c.id}"


# ---------------------------------------------------------------- simetría
def _reflejar(xy, a, u):
    """Reflejo de los puntos `xy` (n×2) respecto de la recta que pasa por `a` con dirección unitaria `u`."""
    v = xy - a
    paralela = (v @ u)[:, None] * u
    return a + 2 * paralela - v


def _dist(x, y):
    """Matriz de distancias entre los puntos de `x` (n×2) y los de `y` (m×2)."""
    return np.hypot(x[:, None, 0] - y[None, :, 0], x[:, None, 1] - y[None, :, 1])


def _pares(distancias, tol):
    """Pares (i, j), i < j, con distancia menor que `tol`."""
    i, j = np.nonzero(np.triu(distancias < tol, 1))
    return zip(i.tolist(), j.tolist(), strict=True)


def simetrias(b, tol_angulo, tol_distancia, tipos):
    """Pares de líneas, círculos/arcos y puntos simétricos respecto de una línea de construcción o línea central."""
    ejes = [c for c in b.curvas.values() if isinstance(c, Linea) and (c.eje or c.construccion)][:TOPE_EJES_SIMETRIA]
    ids = list(b.puntos)
    xy = np.array([b.coords(p) for p in ids]).reshape(-1, 2)
    usados = {e.id for e in ejes}
    lineas = [c for c in _lineas(b) if c.id not in usados]
    extremos = np.array([[*b.coords(c.p1), *b.coords(c.p2)] for c in lineas]).reshape(-1, 4)
    redondas = [c for c in b.curvas.values() if c.tipo in CIRCULARES]
    for eje in ejes:
        a, fin = np.array(b.coords(eje.p1)), np.array(b.coords(eje.p2))
        largo = float(np.hypot(*(fin - a)))
        if largo < 1e-9 or not len(ids):
            continue
        u = (fin - a) / largo
        sobre_eje = np.abs(u[0] * (xy[:, 1] - a[1]) - u[1] * (xy[:, 0] - a[0])) < tol_distancia
        if len(lineas) > 1:
            r1, r2 = _reflejar(extremos[:, :2], a, u), _reflejar(extremos[:, 2:], a, u)
            d = np.maximum(_dist(r1, extremos[:, :2]), _dist(r2, extremos[:, 2:]))
            d = np.minimum(d, np.maximum(_dist(r1, extremos[:, 2:]), _dist(r2, extremos[:, :2])))
            for i, j in _pares(d, tol_distancia):
                yield "simetrica", [lineas[i].id, lineas[j].id, eje.id], f"simetrica {lineas[i].id}-{lineas[j].id}/{eje.id}"
        for c1, c2 in combinations(redondas, 2):
            if c1.tipo != c2.tipo or abs(b.radio(c1.id) - b.radio(c2.id)) >= tol_distancia:
                continue
            q = _reflejar(np.array([b.coords(c1.centro)]), a, u)[0]
            if np.hypot(*(q - b.coords(c2.centro))) >= tol_distancia:
                continue
            if c1.tipo == "arco":      # el reflejo invierte el sentido: inicio ↔ fin
                p, f = _reflejar(np.array([b.coords(c1.inicio), b.coords(c1.fin)]), a, u)
                if (np.hypot(*(p - b.coords(c2.fin))) >= tol_distancia
                        or np.hypot(*(f - b.coords(c2.inicio))) >= tol_distancia):
                    continue
            yield "simetrica", [c1.id, c2.id, eje.id], f"simetrica {c1.id}-{c2.id}/{eje.id}"
        reflejo = _reflejar(xy, a, u)
        d = _dist(reflejo, xy)
        d[sobre_eje, :] = np.inf
        for i, j in _pares(d, tol_distancia):
            yield "simetrica", [ids[i], ids[j], eje.id], f"simetrica {ids[i]}-{ids[j]}/{eje.id}"


# (función, tipos que produce): en este orden se prueban
ETAPAS = (
    (coincidencias, ("coincidente", "concentrica")),
    (horizontales_verticales, ("horizontal", "vertical")),
    (colineales, ("colineal",)),
    (paralelas, ("paralela",)),
    (perpendiculares, ("perpendicular",)),
    (tangentes, ("tangente",)),
    (iguales, ("igual",)),
    (puntos_medios, ("punto_medio",)),
    (simetrias, ("simetrica",)),
)

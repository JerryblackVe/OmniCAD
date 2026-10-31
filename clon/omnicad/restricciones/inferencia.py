"""Ayudas de dibujo de Fusion (SKT-CREATE-LINES) sin modificar el boceto: ajuste a objetos y alineaciones.

Una `Inferencia` es una propuesta del cursor: dónde cae (`xy`), qué guías mostrar y, si corresponde, qué
restricción dejar al confirmar (`restriccion`). Las alineaciones con puntos existentes (misma X o misma Y) son
solo guías temporales: no llevan restricción. Todo el cálculo es puro (sin Qt) y determinista.
"""
import math
from dataclasses import dataclass, field

import numpy as np

from .boceto import (CON_CENTRO, Boceto, caja_primitiva, dominio, evaluar_primitiva, intersecciones, mas_cercano)

# Familias que se pueden encender o apagar (parámetro `tipos`).
TIPOS_INFERENCIA = ("medio", "interseccion", "tangente", "perpendicular", "curva", "alineacion", "horizontal",
                    "vertical", "paralela")
FACTOR_HISTERESIS = 1.4        # un candidato que ya estaba activo sigue hasta esta fracción más lejos de la tolerancia
RADIO_DIRECCION = 25           # shortcut: paralela/perpendicular/colineal solo con líneas a menos de 25 tolerancias del cursor
TOPE_CRUCES = 8                # shortcut: solo se cruzan las 8 curvas más cercanas al cursor; subir si falta alguna


@dataclass
class Inferencia:
    """Ajuste propuesto y restricción pendiente de completar con la entidad nueva.

    `restriccion` es (tipo, id_objetivo), o (tipo,) para horizontal/vertical, o None si es solo una guía.
    En perpendicular, un tercer elemento ("coincidente", id_objetivo) indica
    que también hay que unir el extremo nuevo al segmento. `objetivo` es None
    para horizontal/vertical; `guias` contiene segmentos en mm del plano.
    `etiqueta` explica la ayuda en una frase; `distancia` es lo que separa al cursor del ajuste (mm) y `clase`
    su prioridad (menor gana); `referencias` identifica en qué se apoya (para no saltar de un candidato a otro).
    """
    tipo: str
    xy: tuple[float, float]
    objetivo: int | None
    restriccion: tuple | None
    guias: list[tuple[tuple[float, float], tuple[float, float]]] = field(default_factory=list)
    etiqueta: str = ""
    distancia: float = 0.0
    clase: int = 0
    referencias: tuple = ()

    def clave(self):
        return (self.tipo, self.objetivo, self.referencias)


class Indice:
    """Geometría derivada de un boceto, lista para consultar con el cursor sin recorrer todo en Python.

    Se arma una vez y vale mientras el boceto no cambie (quien edita lo descarta). Guarda las primitivas de cada
    curva con su caja envolvente y los puntos de referencia para alinear: puntos del boceto, centros, puntos
    medios de líneas y arcos, y el origen.
    """

    def __init__(self, b: Boceto):
        self.b = b
        self.cids, self.prims, cajas = [], {}, []
        self.duenos = duenos = {}
        for cid, curva in b.curvas.items():
            if curva.tipo == "texto":
                continue
            prims = b.primitivas(cid)
            if not prims:
                continue
            self.cids.append(cid)
            self.prims[cid] = prims
            cs = [caja_primitiva(p) for p in prims]
            cajas.append((min(c[0] for c in cs), min(c[1] for c in cs), max(c[2] for c in cs), max(c[3] for c in cs)))
            for pid in curva.puntos():
                duenos.setdefault(pid, set()).add(cid)
        self.cajas = np.array(cajas, dtype=float).reshape(-1, 4)
        lineas = [(cid, *self.prims[cid][0][2], *self.prims[cid][0][3]) for cid in self.cids
                  if b.curvas[cid].tipo == "linea"]
        self.lineas = np.array(lineas, dtype=float).reshape(-1, 5)      # id, x1, y1, x2, y2
        centros = {c.centro for c in b.curvas.values() if c.tipo in CON_CENTRO}
        refs = [(0.0, 0.0, "origen", None, frozenset())]
        for pid, p in b.puntos.items():
            refs.append((p.x, p.y, "centro" if pid in centros else "punto", pid, frozenset(duenos.get(pid, ()))))
        for cid in self.cids:
            if b.curvas[cid].tipo in ("linea", "arco"):
                for prim in self.prims[cid]:
                    refs.append((*evaluar_primitiva(prim, dominio(prim)[1] / 2)[0], "medio", cid, frozenset((cid,))))
        self.refs = refs
        self.rx = np.array([r[0] for r in refs])
        self.ry = np.array([r[1] for r in refs])

    def curvas_cerca(self, xy, tol):
        """Ids de curvas cuya caja envolvente queda a menos de `tol` de `xy` (filtro barato, no exacto)."""
        if not self.cids:
            return []
        c = self.cajas
        m = (c[:, 0] - tol <= xy[0]) & (xy[0] <= c[:, 2] + tol) & (c[:, 1] - tol <= xy[1]) & (xy[1] <= c[:, 3] + tol)
        return [self.cids[i] for i in np.nonzero(m)[0]]

    def referencias_alineables(self, eje, cursor, tol, excluidos, base=None):
        """Referencias (x, y, clase, id, dueños) cuya coordenada `eje` (0 = X, 1 = Y) está a `tol` del cursor.

        Se saltean las excluidas, la propia base y las que están sobre el cursor (ahí manda el ajuste al punto)."""
        coord = self.rx if eje == 0 else self.ry
        for i in np.nonzero(np.abs(coord - cursor[eje]) <= tol)[0]:
            ref = self.refs[i]
            if ref[3] in excluidos or (ref[4] and ref[4] <= excluidos):
                continue
            if math.dist(ref[:2], cursor) <= tol or (base is not None and math.dist(ref[:2], base) < 1e-9):
                continue
            yield ref


def _direccion_cercana(base, cursor, punto, angulo_tol):
    """Direcciones no nulas, en el mismo sentido y dentro de la tolerancia angular."""
    ux, uy = cursor[0] - base[0], cursor[1] - base[1]
    vx, vy = punto[0] - base[0], punto[1] - base[1]
    if math.hypot(ux, uy) <= 1e-9 or math.hypot(vx, vy) <= 1e-9:
        return False
    return abs(math.atan2(ux * vy - uy * vx, ux * vx + uy * vy)) <= angulo_tol


def _tangencias(prim, base):
    """Contactos desde fuera o sobre la curva; normalizar la elipse la reduce al círculo unidad."""
    tipo, _, (cx, cy), a = prim[:4]
    eliptica = tipo in ("elipse", "arco_elipse")
    menor, giro = (prim[4], prim[5]) if eliptica else (a, 0.0)
    if a <= 1e-9 or menor <= 1e-9:
        return
    c, s = math.cos(giro), math.sin(giro)
    dx, dy = base[0] - cx, base[1] - cy
    x, y = (dx * c + dy * s) / a, (-dx * s + dy * c) / menor
    distancia = math.hypot(x, y)
    if abs(distancia - 1.0) * max(a, menor) < 1e-9:
        if mas_cercano(prim, base)[1] < 1e-9:
            yield base
        return
    if distancia <= 1.0:
        return
    direccion = math.atan2(y, x)
    apertura = math.acos(1 / distancia)
    inicio = prim[6] if tipo == "arco_elipse" else prim[4] if tipo == "arco" else 0.0
    fin = dominio(prim)[1]
    for angulo in (direccion - apertura, direccion + apertura):
        parametro = (angulo - inicio) % math.tau
        if parametro <= fin + 1e-12:
            yield evaluar_primitiva(prim, min(parametro, fin))[0]


_NOMBRE_REFERENCIA = {"punto": "un punto", "centro": "un centro", "medio": "un punto medio", "origen": "el origen"}


def _objetos(b, indice, cursor, tol, base, excluidos, coincidente, angulo_tol, tipos):
    """Ajustes a curvas: punto medio, intersección, tangente, perpendicular y sobre la curva."""
    candidatos, cerca = [], []
    vistas = set(indice.curvas_cerca(cursor, tol))
    if base is not None:
        vistas.update(indice.curvas_cerca(base, 1e-6))
    for cid in sorted(vistas):
        curva = b.curvas[cid]
        if cid in excluidos or excluidos.intersection(curva.puntos()):
            continue
        for prim in indice.prims[cid]:
            tipo = prim[0]
            if curva.tipo in ("linea", "arco") and "medio" in tipos:
                medio = evaluar_primitiva(prim, dominio(prim)[1] / 2)[0]
                distancia = math.dist(cursor, medio)
                if distancia <= tol:
                    restriccion = ("coincidente" if coincidente else "punto_medio", cid)
                    candidatos.append(Inferencia("punto_medio", medio, cid, restriccion, etiqueta="Punto medio",
                                                 distancia=distancia, clase=0, referencias=(cid,)))

            _, distancia_curva, cercano = mas_cercano(prim, cursor)
            if distancia_curva <= tol:
                cerca.append((distancia_curva, cid, prim))
            if base is not None:
                if tipo in ("circulo", "arco", "elipse", "arco_elipse") and "tangente" in tipos:
                    for punto in _tangencias(prim, base):
                        if punto == base:
                            parametro = mas_cercano(prim, base)[0]
                            tx, ty = evaluar_primitiva(prim, parametro, 1)[1]
                            avance = ((cursor[0] - base[0]) * tx + (cursor[1] - base[1]) * ty) / (tx * tx + ty * ty)
                            punto = (base[0] + avance * tx, base[1] + avance * ty)
                        elif distancia_curva > tol:
                            continue
                        distancia = math.dist(cursor, punto)
                        if distancia <= tol and _direccion_cercana(base, cursor, punto, angulo_tol):
                            candidatos.append(Inferencia("tangente", punto, cid, ("tangente", cid), [(base, punto)],
                                                         "Tangente a la curva", distancia, 1, (cid,)))
                elif tipo == "linea" and distancia_curva <= tol and "perpendicular" in tipos:
                    (x, y), (fx, fy) = prim[2:4]
                    dx, dy = fx - x, fy - y
                    largo2 = dx * dx + dy * dy
                    if largo2 > 1e-18:
                        t = ((base[0] - x) * dx + (base[1] - y) * dy) / largo2
                        pie = (x + t * dx, y + t * dy)
                        distancia = math.dist(cursor, pie)
                        if distancia <= tol and _direccion_cercana(base, cursor, pie, angulo_tol):
                            restriccion = ("perpendicular", cid)
                            if 0 <= t <= 1:
                                restriccion += (("coincidente", cid),)
                            candidatos.append(Inferencia("perpendicular", pie, cid, restriccion, [(base, pie)],
                                                         "Perpendicular a la línea", distancia, 2, (cid,)))

            if distancia_curva <= tol and "curva" in tipos:
                candidatos.append(Inferencia("sobre_curva", cercano, cid, ("coincidente", cid),
                                             etiqueta="Sobre la curva", distancia=distancia_curva, clase=3,
                                             referencias=(cid,)))

    if "interseccion" in tipos:
        cerca.sort(key=lambda c: c[:2])
        cerca = cerca[:TOPE_CRUCES]
        for i, (_, ca, pa) in enumerate(cerca):
            for _, cb, pb in cerca[i + 1:]:
                if ca == cb:
                    continue
                for _, _, xy in intersecciones(pa, pb):
                    distancia = math.dist(cursor, xy)
                    if distancia <= tol:
                        candidatos.append(Inferencia(
                            "interseccion", xy, ca, ("coincidente", ca, ("coincidente", cb)), etiqueta="Intersección",
                            distancia=distancia, clase=0, referencias=tuple(sorted((ca, cb)))))
    return candidatos


def _alineaciones(indice, cursor, tol, base, excluidos, angulo_tol, tipos, extra, previa):
    """Guías que alinean el cursor con puntos existentes (misma X o misma Y) y su cruce con horizontal/vertical."""
    refs = [list(indice.referencias_alineables(eje, cursor, tol, excluidos, base)) for eje in (0, 1)]
    for p in extra:                      # puntos ya clicados de la operación en curso que todavía no son geometría
        for eje in (0, 1):
            if abs(p[eje] - cursor[eje]) <= tol and math.dist(p, cursor) > tol and (base is None or p != base):
                refs[eje].append((p[0], p[1], "punto", None, frozenset()))
    # La mejor referencia de cada eje: la que ya estaba activa, y si no la más cercana en esa coordenada (el id
    # rompe el empate).
    activas = {r for r in previa.referencias if isinstance(r, tuple)} if previa is not None else set()

    def mejor(lista, eje):
        return min(lista, key=lambda r: ((r[2], r[3]) not in activas, abs(r[eje] - cursor[eje]), r[3] is None,
                                         r[3] or 0, r[2]), default=None)
    rx, ry = mejor(refs[0], 0), mejor(refs[1], 1)
    hv = None                            # horizontal o vertical desde la base, si el cursor ya está dentro del ángulo
    if base is not None and math.dist(base, cursor) > 1e-9:
        for tipo, punto in (("horizontal", (cursor[0], base[1])), ("vertical", (base[0], cursor[1]))):
            if tipo in tipos and _direccion_cercana(base, cursor, punto, angulo_tol):
                hv = (tipo, punto)
    candidatos = []
    if "alineacion" in tipos:
        if rx is not None and ry is not None:
            xy = (rx[0], ry[1])
            candidatos.append(Inferencia(
                "alineado_hv", xy, None, None,
                [((rx[0], rx[1]), xy), ((ry[0], ry[1]), xy)],
                f"Alineado con {_NOMBRE_REFERENCIA[rx[2]]} y con {_NOMBRE_REFERENCIA[ry[2]]}",
                max(abs(rx[0] - cursor[0]), abs(ry[1] - cursor[1])), 4, ((rx[2], rx[3]), (ry[2], ry[3]))))
        for eje, r, tipo, nombre in ((0, rx, "alineado_v", "misma X"), (1, ry, "alineado_h", "misma Y")):
            if r is None:
                continue
            if hv is not None and hv[0] == ("vertical" if eje == 0 else "horizontal"):
                continue                 # la dirección de la línea ya fija ese mismo eje
            if hv is not None:           # el otro eje lo fija la dirección horizontal/vertical de la línea
                xy = (r[0], base[1]) if eje == 0 else (base[0], r[1])
                candidatos.append(Inferencia(
                    hv[0], xy, None, (hv[0],), [(base, xy), ((r[0], r[1]), xy)],
                    f"{hv[0].capitalize()} y alineado con {_NOMBRE_REFERENCIA[r[2]]}",
                    abs(r[eje] - cursor[eje]), 4, (hv[0], (r[2], r[3]))))
            else:
                xy = (r[0], cursor[1]) if eje == 0 else (cursor[0], r[1])
                candidatos.append(Inferencia(
                    tipo, xy, None, None, [((r[0], r[1]), xy)],
                    f"Alineado con {_NOMBRE_REFERENCIA[r[2]]} ({nombre})",
                    abs(r[eje] - cursor[eje]), 5, ((r[2], r[3]),)))
    if hv is not None:
        tipo, punto = hv
        candidatos.append(Inferencia(tipo, punto, None, (tipo,), [(base, punto)], tipo.capitalize(), 0.0, 6))
    return candidatos


def _direcciones(indice, cursor, tol, base, excluidos, angulo_tol):
    """Líneas cercanas con la misma dirección que base→cursor (paralela, o colineal si la base está sobre ella) o la
    perpendicular. Ajusta el cursor al rayo desde la base; la mejor de cada familia, por ángulo."""
    L = indice.lineas
    if base is None or len(L) == 0 or math.dist(base, cursor) <= 1e-9:
        return []
    dx, dy = L[:, 3] - L[:, 1], L[:, 4] - L[:, 2]
    largo = np.hypot(dx, dy)
    cerca = (np.hypot(cursor[0] - (L[:, 1] + L[:, 3]) / 2, cursor[1] - (L[:, 2] + L[:, 4]) / 2)
             - largo / 2 <= tol * RADIO_DIRECCION) & (largo > 1e-9)
    ang = math.atan2(cursor[1] - base[1], cursor[0] - base[0])
    with np.errstate(divide="ignore", invalid="ignore"):
        dif = np.abs((ang - np.arctan2(dy, dx) + math.pi / 2) % math.pi - math.pi / 2)   # 0 = paralela, π/2 = perpendicular
    salida = []
    for ortogonal in (False, True):
        error = np.abs(dif - math.pi / 2) if ortogonal else dif
        mejor = None
        for i in np.nonzero(cerca & (error <= angulo_tol))[0]:
            cid = int(L[i, 0])
            if cid in excluidos or (mejor is not None and error[i] >= error[mejor]):
                continue
            mejor = i
        if mejor is None:
            continue
        cid = int(L[mejor, 0])
        ux, uy = (-dy[mejor], dx[mejor]) if ortogonal else (dx[mejor], dy[mejor])
        ux, uy = ux / largo[mejor], uy / largo[mejor]
        avance = (cursor[0] - base[0]) * ux + (cursor[1] - base[1]) * uy
        xy = (base[0] + avance * ux, base[1] + avance * uy)
        sobre = abs((base[0] - L[mejor, 1]) * dy[mejor] - (base[1] - L[mejor, 2]) * dx[mejor]) / largo[mejor]
        if ortogonal:
            tipo, restriccion, etiqueta = "perpendicular_dir", ("perpendicular", cid), "Perpendicular a la línea"
        elif sobre <= 1e-6 * (1 + abs(base[0]) + abs(base[1])):
            tipo, restriccion, etiqueta = "colineal", ("colineal", cid), "Colineal con la línea"
        else:
            tipo, restriccion, etiqueta = "paralela", ("paralela", cid), "Paralela a la línea"
        salida.append(Inferencia(tipo, xy, cid, restriccion, [], etiqueta, 0.0, 7, (cid,)))
    return salida


def inferencias(b: Boceto, cursor_xy, tol_mm, base=None, excluir=(), coincidente=False,
                angulo_tol=math.radians(3), *, previa=None, tipos=None, indice=None, extra=()) -> list[Inferencia]:
    """Todas las ayudas posibles del cursor, la mejor primero (la lista deja alternar entre ambiguas).

    Distancias en mm, ángulos en radianes. Orden: intersección y punto medio, tangente, perpendicular, sobre la
    curva, alineaciones (cruzadas antes que simples), horizontal/vertical y por último la dirección paralela,
    colineal o perpendicular a una línea cercana; dentro de cada prioridad gana el ajuste
    más cercano y los empates se resuelven por id de curva. Excluir un punto excluye también sus curvas.
    Desde fuera, las tangencias y los pies deben estar a `tol_mm` del cursor y próximos a la curva. Desde la
    curva, el cursor se proyecta a su tangente en la base, con la misma tolerancia de distancia y ángulo.
    Mayús (`coincidente`) conserva el ajuste al medio pero cambia su restricción.
    `previa` (la inferencia activa en el movimiento anterior) da histéresis: sigue siendo candidata hasta
    `FACTOR_HISTERESIS` veces la tolerancia y, si empata en prioridad con la mejor, se queda en el primer lugar.
    `tipos` limita las familias de `TIPOS_INFERENCIA` (None = todas). `indice` evita rearmar la geometría derivada.
    `extra` son puntos de la operación en curso que aún no están en el boceto.
    """
    cursor = tuple(cursor_xy)
    base = tuple(base) if base is not None else None
    indice = indice if indice is not None and indice.b is b else Indice(b)
    excluidos = set(excluir)
    for pid in tuple(excluidos):
        excluidos |= indice.duenos.get(pid, set())          # excluir un punto excluye sus curvas
    tipos = set(TIPOS_INFERENCIA if tipos is None else tipos)
    tol = tol_mm * FACTOR_HISTERESIS if previa is not None else tol_mm
    candidatos = _objetos(b, indice, cursor, tol, base, excluidos, coincidente, angulo_tol, tipos)
    candidatos += _alineaciones(indice, cursor, tol, base, excluidos, angulo_tol, tipos, extra, previa)
    if "paralela" in tipos:
        candidatos += _direcciones(indice, cursor, tol, base, excluidos, angulo_tol)
    if previa is not None:
        candidatos = [c for c in candidatos if c.distancia <= tol_mm or c.clave() == previa.clave()]
    # A igual lugar (la distancia se redondea: el mismo punto calculado de dos maneras difiere en el último bit)
    # la intersección gana al punto medio, porque deja las dos coincidencias.
    candidatos.sort(key=lambda c: (c.clase, round(c.distancia, 9), c.tipo != "interseccion", c.objetivo or 0, c.tipo))
    if previa is not None and candidatos:
        clase = candidatos[0].clase
        for i, c in enumerate(candidatos):
            if c.clase == clase and c.clave() == previa.clave():
                candidatos.insert(0, candidatos.pop(i))
                break
    return candidatos


def inferir(b: Boceto, cursor_xy, tol_mm, base=None, excluir=(), coincidente=False,
            angulo_tol=math.radians(3), alternativa=0, **opciones) -> Inferencia | None:
    """La mejor ayuda del cursor (o la `alternativa`-ésima, en vueltas, si hay varias): ver `inferencias`."""
    lista = inferencias(b, cursor_xy, tol_mm, base, excluir, coincidente, angulo_tol, **opciones)
    return lista[alternativa % len(lista)] if lista else None


def proyectar_bloqueo(inf: Inferencia, cursor_xy) -> Inferencia:
    """La ayuda `inf` bloqueada (el usuario quiere conservar su dirección): el cursor se proyecta sobre su guía.

    Vale para las que tienen una sola guía (alineación, horizontal/vertical, perpendicular, tangente); el resto
    queda en su punto. La restricción sigue valiendo en toda la guía, salvo el contacto con la curva, que solo
    se cumple en el pie o el punto de tangencia.
    """
    if len(inf.guias) != 1:
        return inf
    (ax, ay), (bx, by) = inf.guias[0]
    dx, dy = bx - ax, by - ay
    largo2 = dx * dx + dy * dy
    if largo2 <= 1e-18:
        return inf
    t = ((cursor_xy[0] - ax) * dx + (cursor_xy[1] - ay) * dy) / largo2
    xy = (ax + t * dx, ay + t * dy)
    restriccion = inf.restriccion
    if restriccion and len(restriccion) > 2 and math.dist(xy, inf.xy) > 1e-9:
        restriccion = restriccion[:2]
    return Inferencia(inf.tipo, xy, inf.objetivo, restriccion, [((ax, ay), xy)], inf.etiqueta, 0.0, inf.clase,
                      inf.referencias)

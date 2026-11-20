"""Boceto 2D: primitivas."""
import math
from functools import lru_cache

import numpy as np

from .boceto_entidades import Arco, ArcoElipse, Circulo, Conica, Elipse, Linea, Spline, Texto
from .boceto_geometria import (
    escala_manija, interpolar_spline, nudos_uniformes, parametro_elipse, puntos_primitiva, _rot)


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
                      camino, tipografia=(), colocacion="arriba", voltear=(False, False), alinear_camino=False):
    from ..nucleo.fuentes import contornos_en_camino
    try:
        return tuple(contornos_en_camino(texto, camino, fuente, altura, negrita, cursiva, espaciado=espaciado,
                                         alineacion=alineacion, posicion=pos, lado=lado, desfase=desfase,
                                         ajustar=ajustar, camino_colocacion=colocacion, voltear_h=voltear[0],
                                         voltear_v=voltear[1], alinear_camino=alinear_camino, **_tipografia_camino(tipografia)))
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
                    camino, tipografia=(), colocacion="arriba", voltear=(False, False), alinear_camino=False):
    from ..nucleo.fuentes import paradas_en_camino
    try:
        return tuple(paradas_en_camino(texto, camino, fuente, altura, negrita, cursiva, espaciado=espaciado,
                                       alineacion=alineacion, posicion=pos, lado=lado, desfase=desfase,
                                       ajustar=ajustar, camino_colocacion=colocacion, voltear_h=voltear[0],
                                       voltear_v=voltear[1], alinear_camino=alinear_camino, **_tipografia_camino(tipografia)))
    except Exception:  # noqa: BLE001
        return None


def paradas_cursor(t, origen, prim_camino=None):
    """Dónde cae el cursor en cada posición del texto `t`, o None si no se pudo componer. Devuelve
    {"paradas": n + 1 segmentos ((x, y) de abajo, (x, y) de arriba) en coordenadas del boceto, "lineas": [(ini, fin)]
    de cada línea de composición (índices del texto), "linea_de": nº de línea de cada posición}. `origen` (u, v) es
    el punto de anclaje; en un texto en curva, `prim_camino` es la primitiva de la curva que sigue. Es lo que usa el
    editor del lienzo para escribir y mover el cursor dentro del texto."""
    if t.camino is not None and prim_camino is not None:
        paradas = _paradas_camino(t.texto, t.fuente, t.tamano_fuente(), t.negrita, t.cursiva, t.espaciado, t.alineacion,
                                  t.camino_pos, t.camino_lado, t.camino_desfase + t.desfase_base, t.camino_ajustar,
                                  polilinea_camino(prim_camino), t.opciones_tipografia(), t.camino_colocacion,
                                  (t.voltear_h, t.voltear_v), t.camino_alineado)
        if paradas is None:
            return None
        n = len(paradas) - 1
        return {"paradas": list(paradas), "lineas": [(0, n)], "linea_de": [0] * (n + 1)}
    m = _mapa_texto(t.texto, t.fuente, t.tamano_fuente(), t.negrita, t.cursiva, t.opciones_contorno())
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


def lado_natural(prim):
    """`camino_lado` con que un texto sobre `prim` se lee de izquierda a derecha con las letras arriba de la curva: en
    una curva cerrada, por fuera."""
    poli = polilinea_camino(prim)
    return "izq" if poli[-1][0] > poli[0][0] else "der"


def fraccion_en_camino(prim, q):
    """Fracción 0-1 del largo de la curva en el punto más cercano a `q` (para ubicar un texto donde se hizo clic)."""
    pts = np.asarray(polilinea_camino(prim), float)
    tramos = np.hypot(*np.diff(pts, axis=0).T)
    acum = np.concatenate([[0.0], np.cumsum(tramos)])
    if acum[-1] < 1e-12:
        return 0.5
    # proyección sobre cada tramo, no el vértice más cercano: una línea da solo 2 vértices y cuantizaba a 0 o 1
    qv = np.asarray(q, float)
    a, b = pts[:-1], pts[1:]
    d = b - a
    dd = np.einsum("ij,ij->i", d, d)
    t = np.clip(np.einsum("ij,ij->i", qv - a, d) / np.maximum(dd, 1e-18), 0.0, 1.0)
    proy = a + t[:, None] * d
    i = int(np.argmin(np.hypot(proy[:, 0] - qv[0], proy[:, 1] - qv[1])))
    return float((acum[i] + t[i] * tramos[i]) / acum[-1])


def _medidas_marco(a, b, t):
    """(giro en radianes, ancho, alto) del marco de un texto: `a` esquina de abajo a la izquierda, `b` la de la
    derecha y `t` la de arriba."""
    ang = math.atan2(b[1] - a[1], b[0] - a[0])
    alto = -math.sin(ang) * (t[0] - a[0]) + math.cos(ang) * (t[1] - a[1])
    return ang, math.dist(a, b), alto


def _derivadas_manijas(c, pts, P):
    """{índice: (C', C'')} de las manijas de una spline de ajuste abierta (ver `Spline`): C' = (punta − punto) ×
    `escala_manija` (la de Fusion, B-463); con curvatura k, C'' = k·|C'|·(normal izquierda de C') (sin componente
    tangencial)."""
    if c.cerrada or not c.manijas:
        return None
    salida = {}
    for a, b, k in c.manijas:
        if a not in c.pts:
            continue
        i = c.pts.index(a)
        (fx, fy), (ex, ey) = pts[i], P(b)
        h = math.hypot(ex - fx, ey - fy)
        if h < 1e-12:
            continue
        f = escala_manija(pts, i, ((ex - fx) / h, (ey - fy) / h), c.grado)
        d1 = ((ex - fx) * f, (ey - fy) * f)
        largo = h * f
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
        pesos = tuple(c.pesos) if c.pesos and len(c.pesos) == len(pts) else None    # B-320: proyectos viejos descuadrados
        return [("spline", c.id, tuple(pts), tuple(nudos), p, pesos)]
    if isinstance(c, Conica):
        w = c.rho / (1 - c.rho)
        return [("spline", c.id, (P(c.inicio), P(c.vertice), P(c.fin)), (0.0, 0.0, 0.0, 1.0, 1.0, 1.0), 2,
                 (1.0, w, 1.0))]
    if isinstance(c, Texto) and c.camino is not None and curvas is not None and c.camino != c.id \
            and not isinstance(curvas.get(c.camino, c), Texto):
        base = primitivas_entidad(curvas[c.camino], P)      # radios guardados (el solver no pide textos)
        if base:
            return [(p[0], c.id) + tuple(p[2:]) for p in _contornos_camino(
                c.texto, c.fuente, c.tamano_fuente(), c.negrita, c.cursiva, c.espaciado, c.alineacion, c.camino_pos,
                c.camino_lado, c.camino_desfase + c.desfase_base, c.camino_ajustar, polilinea_camino(base[0]),
                c.opciones_tipografia(), c.camino_colocacion, (c.voltear_h, c.voltear_v), c.camino_alineado)]
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
        for prim in _contornos_texto(c.texto, c.fuente, c.tamano_fuente(), c.negrita, c.cursiva, opciones):
            if prim[0] == "linea":
                salida.append(("linea", c.id, T(prim[2]), T(prim[3])))
            else:
                salida.append(("spline", c.id, tuple(T(q) for q in prim[2]), prim[3], prim[4], prim[5]))
        return salida
    return []

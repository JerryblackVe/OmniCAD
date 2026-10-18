# -*- coding: utf-8 -*-
"""Regiones del boceto calculadas por OmniKernel; el orden y la firma siguen la política de la app."""
import math

import omnikernel as k

from .. import perfiles as comun

_SOPORTADAS = ("linea", "circulo", "arco", "elipse", "arco_elipse", "spline")


def _usable(prim):
    """Mismos descartes que `aristas_boceto` de OpenCascade: no finitas o degeneradas."""
    tipo = prim[0]
    if tipo not in _SOPORTADAS or not comun._finita.__wrapped__(prim):
        return False
    if tipo == "linea":
        (u1, v1), (u2, v2) = prim[2], prim[3]
        return math.hypot(u2 - u1, v2 - v1) >= 1e-9
    if tipo in ("circulo", "arco"):
        return prim[3] > 1e-9
    if tipo in ("elipse", "arco_elipse"):
        return min(prim[3], prim[4]) > 1e-9
    polos = prim[2]
    return max(abs(q[0] - polos[0][0]) + abs(q[1] - polos[0][1]) for q in polos[1:]) >= 1e-9


def _normalizar(prim):
    """Elipse con a < b: los mismos ejes y parámetro que `_arista_elipse` de OpenCascade (marco girado 90°)."""
    if prim[0] not in ("elipse", "arco_elipse"):
        return prim
    tipo, cid, c, a, b, ang, *t = prim
    if a < b:
        a, b, ang = b, a, ang + math.pi / 2
        t = [x - math.pi / 2 for x in t]
    if t:
        t0, t1 = t
        while t1 <= t0 + 1e-12:
            t1 += 2 * math.pi
        t = [t0, t1]
    return (tipo, cid, c, a, b, ang, *t)


def detectar(geometria, plano, tolerancia=1e-4):
    prims = [_normalizar(p) for p in geometria if _usable(p)]
    if not prims:
        return []
    perfiles = [comun.Perfil(cara, area, tuple(uv), frozenset(prims[i][1] for i in fuentes))
                for cara, area, uv, fuentes in k.regiones(prims, plano.origen.tolist(), plano.normal.tolist(),
                                                          plano.u.tolist(), tolerancia)]
    perfiles.sort(key=lambda p: (round(p.centroide_uv[0], 4), round(p.centroide_uv[1], 4), p.area))
    return perfiles


# Elegir el perfil por su firma es política de la app (sin geometría): la misma para los dos motores.
buscar_por_firma = comun.buscar_por_firma.__wrapped__
buscar_por_firma_tolerante = comun.buscar_por_firma_tolerante.__wrapped__

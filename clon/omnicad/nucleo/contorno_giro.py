"""Contorno exterior de un perfil giratorio (Fusion: Project/Include › Spun Profile, BOC-18).

`proyectar_giro_forma` (perfiles.py) gira TODAS las aristas del cuerpo: también las que quedan dentro de la silueta
(un agujero, las aristas medias de una cara). Acá se queda solo el contorno exterior: la envolvente de radio máximo a
lo largo del eje (la silueta de torneado) y los frentes de sus extremos. Trabaja con los segmentos ya girados sobre el
plano del boceto (sin OpenCascade): sirve igual al proyectar y al re-proyectar."""
import math
from bisect import bisect_left, bisect_right

_TOL = 1e-7


def _a_hr(q, o, d, n):
    rel = (q[0] - o[0], q[1] - o[1])
    return rel[0] * d[0] + rel[1] * d[1], rel[0] * n[0] + rel[1] * n[1]


def contorno_exterior(primitivas, eje):
    """Líneas ("linea", None, a, b) del contorno exterior de los segmentos girados `primitivas` (las que no son líneas
    se descartan). `eje` = ((u, v) de un punto del eje proyectado, (du, dv) su dirección), en coordenadas del boceto.
    Todos los puntos girados quedan del mismo lado del eje: r es su distancia a él y h su posición a lo largo."""
    o, (du, dv) = eje
    largo = math.hypot(du, dv)
    d = (du / largo, dv / largo)
    n = (-d[1], d[0])
    segs = [(_a_hr(p[2], o, d, n), _a_hr(p[3], o, d, n)) for p in primitivas if p[0] == "linea"]
    if not segs:
        return []
    lado = 1.0 if max((q for s in segs for q in s), key=lambda q: abs(q[1]))[1] >= 0 else -1.0
    inclinados, verticales = [], {}
    for (h0, r0), (h1, r1) in segs:
        r0, r1 = abs(r0), abs(r1)
        if abs(h1 - h0) <= _TOL:
            verticales.setdefault(round(h0 / _TOL), []).append((min(r0, r1), max(r0, r1)))
        else:
            inclinados.append((h0, r0, h1, r1) if h0 < h1 else (h1, r1, h0, r0))
    cortes = sorted({h for s in inclinados for h in (s[0], s[2])} | {k * _TOL for k in verticales})
    hs = []
    for h in cortes:                                  # junta los cortes que están a menos de la tolerancia
        if not hs or h - hs[-1] > 10 * _TOL:
            hs.append(h)

    def valor(s, h):
        return s[1] + (s[3] - s[1]) * (h - s[0]) / (s[2] - s[0])

    claves = sorted(verticales)

    def vertical(h):                                  # solo las claves cercanas (búsqueda binaria)
        c = h / _TOL
        cerca = claves[bisect_left(claves, c - 11):bisect_right(claves, c + 11)]
        return [v for k in cerca if abs(k * _TOL - h) <= 10 * _TOL for v in verticales[k]]

    # barrido por tramos: los segmentos que empiezan antes de `a` entran una vez y salen al terminar antes de `b`
    por_inicio, sig, activos, tramos = sorted(inclinados), 0, [], []
    for a, b in zip(hs, hs[1:], strict=False):
        nuevos = []
        while sig < len(por_inicio) and por_inicio[sig][0] <= a + 10 * _TOL:
            nuevos.append(por_inicio[sig])
            sig += 1
        activos = [s for s in activos + nuevos if s[2] >= b - 10 * _TOL]   # lista nueva: no pisa la del tramo anterior
        tramos.append(activos)
    polilineas, actual = [], []
    for k, h in enumerate(hs):
        izq = tramos[k - 1] if k > 0 else []
        der = tramos[k] if k < len(tramos) else []
        L = max((valor(s, h) for s in izq), default=None)
        R = max((valor(s, h) for s in der), default=None)
        V = vertical(h)
        presentes = [x for x in (L, R) if x is not None]
        bajo = min([v[0] for v in V] + presentes)
        tope = max([v[1] for v in V] + presentes)
        if not presentes:                             # un segmento radial suelto
            polilineas.append([(h, bajo), (h, tope)])
            continue
        actual = [(h, bajo)] if L is None else actual + [(h, L)]   # al arrancar, el frente sube desde su radio menor
        if tope > max(presentes):
            actual.append((h, tope))
        if R is None:                                 # al terminar, el frente baja hasta su radio menor
            actual.append((h, bajo))
            polilineas.append(actual)
            continue
        actual.append((h, R))
        # shortcut: un solo cruce por tramo (el de arriba al empezar con el de arriba al terminar); si tres segmentos se
        # turnan dentro del mismo tramo, el del medio se pierde: cortar el tramo en cada cruce si aparece el caso.
        a, b = h, hs[k + 1]
        s1 = max(der, key=lambda s: (valor(s, a), valor(s, b)))
        s2 = max(der, key=lambda s: (valor(s, b), valor(s, a)))
        if s1 is not s2:
            m1, m2 = (valor(s1, b) - valor(s1, a)) / (b - a), (valor(s2, b) - valor(s2, a)) / (b - a)
            if abs(m1 - m2) > 1e-12:
                hx = a + (valor(s2, a) - valor(s1, a)) / (m1 - m2)
                if a < hx < b:
                    actual.append((hx, valor(s1, hx)))
    salida = []
    for pl in polilineas:
        limpia = [pl[0]]
        for q in pl[1:]:
            if math.dist(q, limpia[-1]) > 1e-9:
                limpia.append(q)
        for (h0, r0), (h1, r1) in zip(limpia, limpia[1:], strict=False):
            a = (o[0] + h0 * d[0] + lado * r0 * n[0], o[1] + h0 * d[1] + lado * r0 * n[1])
            b = (o[0] + h1 * d[0] + lado * r1 * n[0], o[1] + h1 * d[1] + lado * r1 * n[1])
            salida.append(("linea", None, a, b))
    return _fusionar_colineales(salida)


def _fusionar_colineales(lineas):
    """Une segmentos seguidos alineados (la envolvente se arma por tramos)."""
    salida = []
    for prim in lineas:
        if salida:
            _t, _i, a, b = salida[-1]
            c = prim[3]
            if b == prim[2] and abs((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])) <= 1e-9 * (
                    math.dist(a, b) + math.dist(b, c)) ** 2 and (b[0] - a[0]) * (c[0] - b[0]) + (b[1] - a[1]) * (c[1] - b[1]) > 0:
                salida[-1] = ("linea", None, a, c)
                continue
        salida.append(prim)
    return salida

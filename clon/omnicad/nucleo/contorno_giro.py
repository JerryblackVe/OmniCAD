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


def contorno_exterior(primitivas, eje, tolerancia=0.1):
    """Líneas ("linea", None, a, b) del contorno exterior de los segmentos girados `primitivas` (las que no son líneas
    se descartan); los tramos curvos salen como arcos ("arco", None, c, r, a0, a1) a `tolerancia` mm, como Fusion (B-619c). `eje` = ((u, v) de un punto del eje proyectado, (du, dv) su dirección), en coordenadas del boceto.
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
    return _a_arcos(_fusionar_colineales(salida), tolerancia)


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


def _circulo_3(a, m, b):
    """(centro, radio) del círculo por tres puntos; None si están casi alineados."""
    d = 2 * (a[0] * (m[1] - b[1]) + m[0] * (b[1] - a[1]) + b[0] * (a[1] - m[1]))
    if abs(d) < 1e-12:
        return None
    s = [x[0] ** 2 + x[1] ** 2 for x in (a, m, b)]
    cx = (s[0] * (m[1] - b[1]) + s[1] * (b[1] - a[1]) + s[2] * (a[1] - m[1])) / d
    cy = (s[0] * (b[0] - m[0]) + s[1] * (a[0] - b[0]) + s[2] * (m[0] - a[0])) / d
    return (cx, cy), math.dist((cx, cy), a)


def _arco_de(pts, tol):
    """Arco ("arco", None, c, r, a0, a1) por los extremos de `pts` y su punto medio, si todos los puntos caen a `tol`
    de él y giran siempre hacia el mismo lado con quiebres suaves; si no, None."""
    giros = []
    for p, q, s in zip(pts, pts[1:], pts[2:], strict=False):
        u, v = (q[0] - p[0], q[1] - p[1]), (s[0] - q[0], s[1] - q[1])
        giros.append(math.atan2(u[0] * v[1] - u[1] * v[0], u[0] * v[0] + u[1] * v[1]))
    if not all(0 < abs(g) <= math.radians(25) for g in giros) or min(giros) * max(giros) < 0:
        return None
    ajuste = _circulo_3(pts[0], pts[len(pts) // 2], pts[-1])
    if ajuste is None or any(abs(math.dist(ajuste[0], q) - ajuste[1]) > tol for q in pts):
        return None
    c, r = ajuste
    a0, a1 = (math.atan2(q[1] - c[1], q[0] - c[0]) for q in (pts[0], pts[-1]))
    return ("arco", None, c, r, a0, a1) if giros[0] > 0 else ("arco", None, c, r, a1, a0)


def _a_arcos(lineas, tol):
    """Reemplaza los tramos de 3 o más segmentos seguidos que caen sobre un círculo (a `tol` mm) por un arco: la
    envolvente de una curva llega como poligonal y Fusion devuelve arcos (B-619c). Greedy: el arco más largo desde
    cada vértice. shortcut: un tramo de 2 segmentos queda en líneas; un arco de más de unos 180° no se arma."""
    salida, i = [], 0
    while i < len(lineas):
        cadena = [lineas[i][2], lineas[i][3]]
        j = i + 1
        while j < len(lineas) and lineas[j][2] == cadena[-1]:
            cadena.append(lineas[j][3])
            j += 1
        k = 0
        while k < len(cadena) - 1:
            mejor = None
            for f in range(k + 3, len(cadena)):
                arco = _arco_de(cadena[k:f + 1], tol)
                if arco is None:
                    break
                mejor = (f, arco)
            if mejor:
                salida.append(mejor[1])
                k = mejor[0]
            else:
                salida.append(("linea", None, cadena[k], cadena[k + 1]))
                k += 1
        i = j
    return salida

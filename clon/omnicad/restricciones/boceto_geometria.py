"""Boceto 2D: geometria."""
import bisect
import math

import numpy as np

from .boceto_entidades import _DOS_PI, ErrorBoceto


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
    w = pesos if pesos and len(pesos) == len(polos) else [1.0] * len(polos)   # B-605: pesos de más (archivo externo) se ignoran
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


def aviso_quitadas(antes, boceto):
    """B-480: el aviso de Fusion si un cambio quitó restricciones o cotas (girar quita las horizontales y verticales que
    ya no valen); `antes` = (restricciones, cotas) contadas antes. None si no quitó nada."""
    r, c = antes[0] - len(boceto.restricciones), antes[1] - len(boceto.cotas)
    if r > 0 or c > 0:
        cuantas = lambda n, uno, varios: f"{n} {uno if n == 1 else varios}"  # noqa: E731
        return (f"Las restricciones o las cotas se han eliminado durante la operación "
                f"({cuantas(r, 'restricción', 'restricciones')}, {cuantas(c, 'cota', 'cotas')}).")
    return None


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


def firma_primitiva(prim):
    """Tipo y siete puntos (redondeados a 1e-5 mm, sin importar el sentido) de una primitiva: dos curvas iguales dan la
    misma firma aunque vengan de aristas distintas. Una polilínea de sección (spline sin nudos) se identifica por sus polos."""
    if prim[0] == "spline" and prim[3] is None:
        puntos = prim[2]
    else:
        t0, t1, _ = dominio(prim)
        puntos = [evaluar_primitiva(prim, t0 + (t1 - t0) * k / 6)[0] for k in range(7)]
    return prim[0], frozenset((round(x, 5) + 0.0, round(y, 5) + 0.0) for x, y in puntos)


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
    t0, t1, periodica = dominio(prim)
    if periodica:
        # El pie puede estar del otro lado de la unión 0/2π.
        if i == 0:
            lo = ts[-2] - (t1 - t0)
        elif i == len(ts) - 1:
            hi = ts[1] + (t1 - t0)
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
    if periodica:
        t = t0 + (t - t0) % (t1 - t0)
    p = evaluar_primitiva(prim, t)[0]
    return t, math.dist(p, q), p


def pie_normal(prim, q, pasos=96):
    """(t, punto, derivada) del punto de la curva cuya recta normal pasa más cerca de q (Perpendicular línea–spline,
    B-586): ahí basta girar la línea alrededor de q para dejarla normal a la curva."""
    t0, t1 = dominio(prim)[:2]
    def lejos(t):
        c, d = evaluar_primitiva(prim, t, 1)
        n = math.hypot(*d) or 1e-12
        return abs((q[0] - c[0]) * d[0] + (q[1] - c[1]) * d[1]) / n
    t = min((t0 + (t1 - t0) * k / pasos for k in range(pasos + 1)), key=lejos)
    a, b = max(t0, t - (t1 - t0) / pasos), min(t1, t + (t1 - t0) / pasos)
    for _ in range(40):                       # afina entre las muestras vecinas (búsqueda ternaria)
        m1, m2 = a + (b - a) / 3, b - (b - a) / 3
        a, b = (a, m2) if lejos(m1) < lejos(m2) else (m1, b)
    t = (a + b) / 2
    return (t, *evaluar_primitiva(prim, t, 1))


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

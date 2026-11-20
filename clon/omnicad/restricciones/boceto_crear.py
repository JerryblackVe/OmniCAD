"""Boceto 2D: crear."""
import math

import numpy as np

from .boceto_entidades import (
    _antihorario_por, Arco, Circulo, circunferencia_3_puntos, Conica, distancia_punto_recta, Elipse, ErrorBoceto,
    Linea, MEDIDA_MAXIMA, _numero, Punto, Spline, Texto, validar_texto_boceto, validar_valor_cota,
)
from .boceto_geometria import _barrido
from .boceto_texto import _validar_opciones_texto


def aviso_radio_empalme(pedido, final):
    """Fusion: Empalme entre paralelas. Informa si la separación impuso otro radio."""
    if math.isclose(final, pedido, rel_tol=1e-9, abs_tol=1e-9):
        return ""
    return (f"Entre líneas paralelas el radio es la mitad de su separación: {final:g} mm; "
            "se ignoró el radio pedido.")


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


def agregar_arco_tangente(b, curva, inicio, fin=None, geometria=None, construccion=False, *,
                         radio=None, barrido=None, direccion=None):
    """Fusion: Arco tangente. Por final y (centro, antihorario), o radio, barrido y dirección de salida.

    El barrido positivo elige el centro a la izquierda de la salida; negativo, a la derecha (el cursor
    elige ese lado en la ventana). Devuelve el id del arco y el punto final, conservando el inicio compartido.
    """
    if radio is not None:
        validar_valor_cota("radio", radio)
        if barrido is None or not math.isfinite(barrido) or abs(barrido) < 1e-9 or abs(barrido) > 360 - 1e-6:
            raise ErrorBoceto("Barrido del arco: entre 0 y 360 grados.")
        p = b.coords(inicio)
        if direccion is None:
            _, direccion = b._salida_extremo(curva, inicio)
        nx, ny = -direccion[1], direccion[0]
        distancia = radio if barrido > 0 else -radio
        centro = (p[0] + nx * distancia, p[1] + ny * distancia)
        angulo = math.atan2(p[1] - centro[1], p[0] - centro[0]) + math.radians(barrido)
        fin = (centro[0] + radio * math.cos(angulo), centro[1] + radio * math.sin(angulo))
        geometria = centro, barrido > 0
    centro, izquierda = geometria
    ini, z = (inicio, fin) if izquierda else (fin, inicio)
    aid = b.agregar_arco_centro(centro, ini, z, construccion)
    b.agregar_restriccion("tangente", [curva, aid])
    arco = b.curvas[aid]
    return aid, arco.fin if izquierda else arco.inicio


def agregar_circulo_puntos(b, puntos, construccion=False):
    """Fusion: Círculo de 2 puntos (diámetro) o de 3 puntos. Devuelve el id del círculo."""
    if len(puntos) == 2:
        a, z = puntos
        radio = math.dist(a, z) / 2
        if radio < 1e-9:
            raise ErrorBoceto("Los dos puntos del diámetro coinciden.")
        centro = ((a[0] + z[0]) / 2, (a[1] + z[1]) / 2)
    else:
        circ = circunferencia_3_puntos(*puntos)
        if circ is None:
            raise ErrorBoceto("Tres puntos alineados: no hay círculo.")
        centro, radio = (circ[0], circ[1]), circ[2]
    return b.agregar_circulo(centro, radio, construccion)


def validar_lados_poligono(lados):
    """Tope propio de Polígono (Fusion no publica un máximo), compartido por dibujo y entrada dinámica."""
    if not 3 <= lados <= 64:
        raise ErrorBoceto("El polígono necesita entre 3 y 64 lados.")
    return lados


def vertices_poligono(centro, radio, lados, giro, circunscrito=False):
    """Fusion: Polígono inscrito/circunscrito; `giro` orienta el primer vértice, en radianes."""
    validar_lados_poligono(lados)
    cx, cy = centro
    rv = radio / math.cos(math.pi / lados) if circunscrito else radio
    return [(cx + rv * math.cos(giro + 2 * math.pi * k / lados), cy + rv * math.sin(giro + 2 * math.pi * k / lados))
            for k in range(lados)]


def agregar_poligono(b, centro, radio, lados, giro, circunscrito=False, construccion=False, centro_pid=None,
                     circulo=None):
    """Fusion: Polígono. Centro en coordenadas y punto guía opcional; devuelve (líneas, círculo guía). Con `circulo`
    usa ese círculo guía en vez de crear otro (P-154: rehacer con otra cantidad de lados conserva sus cotas)."""
    esquinas = vertices_poligono(centro, radio, lados, giro, circunscrito)
    cid = circulo if circulo is not None else b.agregar_circulo(centro_pid if centro_pid is not None else centro,
                                                                 radio, True)
    verts = [b.agregar_punto(*q) for q in esquinas]
    ls = [b.agregar_linea(verts[k], verts[(k + 1) % lados], construccion) for k in range(lados)]
    for k in range(1, lados):
        b.agregar_restriccion("igual", [ls[0], ls[k]])
    for v, ln in zip(verts, ls, strict=True):
        b.agregar_restriccion("tangente" if circunscrito else "coincidente", [ln if circunscrito else v, cid])
    if circunscrito:
        # Con lados pares, «igual» + «tangente» deja alternar los tramos de tangencia: sobra un grado de libertad.
        b.agregar_restriccion("poligono", list(ls))
    return ls, cid


def validar_puntas_estrella(puntas):
    """Tope de Estrella (BOC-84, herramienta propia: Fusion no la tiene), el mismo que el de Polígono."""
    if not 3 <= puntas <= 64:
        raise ErrorBoceto("La estrella necesita entre 3 y 64 puntas.")
    return puntas


def proporcion_estrella(puntas, salto=2):
    """Radio interior / exterior de la estrella regular {puntas/salto}: sus lados siguen las líneas del polígono
    estrellado (5/2 da 38,2 %). Con 3 o 4 puntas no hay estrella regular: la mitad."""
    validar_puntas_estrella(puntas)
    if puntas < 5:
        return 0.5
    if not 2 <= salto < puntas / 2:
        raise ErrorBoceto(f"Con {puntas} puntas el salto va de 2 a {math.ceil(puntas / 2) - 1}.")
    return math.cos(math.pi * salto / puntas) / math.cos(math.pi * (salto - 1) / puntas)


def redondeos_estrella(radio, interior, puntas, r_punta, r_valle):
    """B-496: los redondeos (punta, valle) que entran en la estrella sin comerse puntas. Si los pedidos no entran en
    el lado, los achica en la misma proporción y deja recto el 10 % del lado."""
    a = math.pi / puntas
    p, v = (radio, 0.0), (interior * math.cos(a), interior * math.sin(a))
    q, w = (radio * math.cos(2 * a), radio * math.sin(2 * a)), (v[0], -v[1])

    def tangente(x, y, z):                    # de la esquina y al punto de tangencia, por mm de radio
        u, t = (x[0] - y[0], x[1] - y[1]), (z[0] - y[0], z[1] - y[1])
        cos = (u[0] * t[0] + u[1] * t[1]) / (math.hypot(*u) * math.hypot(*t))
        return 1 / math.tan(math.acos(max(-1.0, min(1.0, cos))) / 2)

    usado = r_punta * tangente(v, p, w) + r_valle * tangente(p, v, q)
    tope = 0.9 * math.dist(p, v)
    if usado <= tope:
        return r_punta, r_valle
    return r_punta * tope / usado, r_valle * tope / usado


def _agrupar_estrella(b, antes, ls):
    """Las restricciones nuevas de la estrella, en un grupo: la ventana dibuja un glifo por tipo (B-496)."""
    for k in b.restricciones.keys() - antes:
        b.restricciones[k].datos["grupo"] = f"estrella{ls[0]}"


def vertices_estrella(centro, radio, puntas, giro, interior):
    """Puntas (radio `radio`) y valles (radio `interior`) alternados; `giro` orienta la primera punta, en radianes."""
    validar_puntas_estrella(puntas)
    if not 0 < interior < radio:
        raise ErrorBoceto("Radio interior: menor que el exterior.")
    cx, cy = centro
    return [(cx + (radio if k % 2 == 0 else interior) * math.cos(giro + math.pi * k / puntas),
             cy + (radio if k % 2 == 0 else interior) * math.sin(giro + math.pi * k / puntas))
            for k in range(2 * puntas)]


def agregar_estrella(b, centro, radio, puntas, giro, interior, construccion=False, centro_pid=None, circulos=True,
                     existentes=None):
    """Estrella (BOC-84): 2·puntas líneas iguales. Con `circulos`, las puntas van sobre un círculo de construcción y los
    valles sobre otro concéntrico: queda definida por centro, los dos radios y el giro. Devuelve (líneas, círculo
    exterior, círculo interior); sin círculos, los dos son None. `existentes` = (exterior, interior) ya dibujados
    (P-154: rehacer la estrella conserva sus cotas)."""
    esquinas = vertices_estrella(centro, radio, puntas, giro, interior)
    antes = set(b.restricciones)
    verts = [b.agregar_punto(*q) for q in esquinas]
    n = len(verts)
    ls = [b.agregar_linea(verts[k], verts[(k + 1) % n], construccion) for k in range(n)]
    for k in range(1, n):
        b.agregar_restriccion("igual", [ls[0], ls[k]])
    if not circulos:
        _agrupar_estrella(b, antes, ls)
        return ls, None, None
    if existentes is not None:
        ce, ci = existentes
    else:
        ce = b.agregar_circulo(centro_pid if centro_pid is not None else centro, radio, True)
        ci = b.agregar_circulo(b.curvas[ce].centro, interior, True)
    for k, v in enumerate(verts):
        b.agregar_restriccion("coincidente", [v, ce if k % 2 == 0 else ci])
    _agrupar_estrella(b, antes, ls)
    return ls, ce, ci


def redondear_estrella(b, ls, r_punta=0.0, r_valle=0.0):
    """Redondea las puntas y/o los valles de una estrella (`ls` de `agregar_estrella`). Los arcos de cada tipo son
    iguales y llevan una sola cota de radio; los vértices quedan virtuales sobre sus círculos, así la estrella sigue
    definida igual que filosa. Devuelve (arcos de las puntas, arcos de los valles)."""
    arcos = ([], [])
    antes = set(b.restricciones)
    for k in range(len(ls)):
        radio = r_punta if k % 2 == 0 else r_valle
        if radio:
            try:
                arcos[k % 2].append(b.empalme(ls[k - 1], ls[k], radio))
            except ErrorBoceto as e:
                que = "las puntas" if k % 2 == 0 else "los valles"
                raise ErrorBoceto(f"Redondeo de {que} ({_numero(radio)} mm) no entra.") from e
    for grupo in arcos:
        for a in grupo[1:]:
            for cid in [k for k, c in b.cotas.items() if c.entidades == [a]]:
                b.eliminar(cid)
            b.agregar_restriccion("igual", [grupo[0], a])
    _agrupar_estrella(b, antes, ls)
    return arcos


def centro_poligono_arista(a, z, lado, lados):
    """Fusion: Polígono por arista A→B; centro hacia el punto `lado` (A y B distintos)."""
    validar_lados_poligono(lados)
    largo = math.dist(a, z)
    mx, my = (a[0] + z[0]) / 2, (a[1] + z[1]) / 2
    nx, ny = -(z[1] - a[1]) / largo, (z[0] - a[0]) / largo
    if (lado[0] - mx) * nx + (lado[1] - my) * ny < 0:
        nx, ny = -nx, -ny
    apotema = largo / (2 * math.tan(math.pi / lados))
    return mx + nx * apotema, my + ny * apotema


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


VUELTAS_MAX_ESPIRAL = 199 / 8      # 200 puntos de ajuste (8 tramos por vuelta): el solver usa matrices densas


def puntos_espiral(centro, inicio, vueltas, paso):
    """Puntos de ajuste de la espiral plana del editor, en mm (no una hélice 3D de Fusion)."""
    if not all(math.isfinite(v) for v in (*centro, *inicio, vueltas, paso)):
        raise ErrorBoceto("La espiral necesita números finitos.")
    r0 = math.dist(centro, inicio)
    a0 = math.atan2(inicio[1] - centro[1], inicio[0] - centro[0])
    if vueltas <= 0:
        raise ErrorBoceto("La espiral necesita vueltas mayores que 0.")
    if vueltas > VUELTAS_MAX_ESPIRAL:
        raise ErrorBoceto(f"La espiral admite hasta {VUELTAS_MAX_ESPIRAL:g} vueltas.")
    if abs(paso) > MEDIDA_MAXIMA:
        raise ErrorBoceto(f"Paso: máximo {MEDIDA_MAXIMA:,.0f} mm.".replace(",", "."))
    n = max(4, int(math.ceil(8 * vueltas)))
    pts = []
    for i in range(n + 1):
        th = 2 * math.pi * vueltas * i / n
        r = r0 + paso * th / (2 * math.pi)
        pts.append((centro[0] + r * math.cos(a0 + th), centro[1] + r * math.sin(a0 + th)))
    if r0 < 1e-9 and paso <= 0:
        raise ErrorBoceto("La espiral necesita un radio o un paso.")
    return pts


class _Crear:
    # ------------------------------------------------------------ creación
    def agregar_punto(self, x, y, proyectado=False):
        if not (math.isfinite(x) and math.isfinite(y)):     # con NaN o infinito, OCC no termina de partir la cara
            raise ErrorBoceto("Las coordenadas del punto deben ser finitas.")
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
            raise ErrorBoceto("El rectángulo no puede tener lado cero.")
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
            raise ErrorBoceto("Tres puntos alineados: no hay arco.")
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
        repetidos = modo == "control" and (pesos is not None or nudos is not None)   # B-320: polos atados a pesos y nudos
        for p in puntos:
            i = self._punto(p)
            if not ids or i != ids[-1] or repetidos:
                ids.append(i)
        if cerrada and len(ids) > 1 and ids[-1] == ids[0]:
            ids.pop()
        if len(ids) < 2 or (cerrada and len(ids) < 3):
            raise ErrorBoceto("La spline necesita más puntos.")
        primero = self.coords(ids[0])
        if all(math.dist(primero, self.coords(i)) < 1e-9 for i in ids[1:]):
            raise ErrorBoceto("Puntos de spline iguales: no hay curva.")
        if modo not in ("ajuste", "control"):
            raise ErrorBoceto(f"Tipo de spline desconocido: {modo}")
        if modo == "control":
            grado = min(grado, len(ids) - 1)
        else:
            grado = 5           # B-463: la de ajuste es la quíntica de Fusion; las guardadas con grado 3 siguen cúbicas
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
            raise ErrorBoceto("Vértice alineado con los extremos.")
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
        tid = self._agregar_curva(Texto(self._nuevo_id(), self._punto(posicion), texto, fuente, altura, angulo,
                                        negrita, cursiva, **{"altura_a": True,
                                            "camino_alineado": opciones.get("camino") is not None and "camino_pos" not in opciones} | opciones))
        from . import objetos
        oid = objetos.crear(self, [tid], "Texto")
        self.objetos[oid]["texto_automatico"] = tid
        return tid

    def _validar_camino(self, camino):
        """El camino de un texto en curva tiene que ser una curva del boceto que no sea otro texto."""
        if camino is None:
            return
        c = self.curvas.get(camino)
        if c is None or isinstance(c, Texto):
            raise ErrorBoceto("Camino del texto: una curva, no un texto.")

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
                raise ErrorBoceto("Tres puntos alineados: no hay arco.")
            centro = (circ[0], circ[1])
            if not _antihorario_por(a, q, b, centro):
                a, b = b, a
        elif tipo == "arco_centro":
            centro, a, b2 = coords
            R = math.dist(centro, a)
            if math.dist(centro, b2) < 1e-9:
                raise ErrorBoceto("El tercer punto no puede ser el centro.")
            ang = math.atan2(b2[1] - centro[1], b2[0] - centro[0])
            b = (centro[0] + R * math.cos(ang), centro[1] + R * math.sin(ang))
            a0 = math.atan2(a[1] - centro[1], a[0] - centro[0])
            if math.dist(a, b) < 1e-9:
                raise ErrorBoceto("El barrido es 0: el tercer punto no gira.")
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
            raise ErrorBoceto("Ranura: ancho mayor que el radio del arco.")
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
                raise ErrorBoceto("No hay círculo tangente a esas 3 líneas.")
            _, centro, r = mejor
        if r <= 1e-9:
            raise ErrorBoceto("Ubicá el círculo dentro del ángulo.")
        cid = self.agregar_circulo((float(centro[0]), float(centro[1])), float(r), construccion)
        for k in lineas:
            self.agregar_restriccion("tangente", [k, cid])
        return cid

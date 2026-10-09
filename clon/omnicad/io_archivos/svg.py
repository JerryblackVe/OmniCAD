# -*- coding: utf-8 -*-
"""
Lector SVG para INSERTAR › Insertar SVG de Fusion [SLD-INS-SVG]: convierte la geometría del archivo en
primitivas 2D en milímetros (el eje Y del SVG apunta hacia abajo: acá se da vuelta para que el dibujo
quede derecho en el boceto).

Primitivas (las mismas que `dxf.leer_dxf` más las Bézier):
  ('linea', (x1, y1), (x2, y2)), ('circulo', (cx, cy), r), ('arco', (cx, cy), r, a0, a1),
  ('polilinea', [(x, y)…], cerrada), ('bezier', [p0, p1, p2, p3]).
Soporta path (M L H V C S Q T A Z, absolutos y relativos), rect, circle, ellipse, line, polyline,
polygon, grupos y el atributo transform (matrix, translate, scale, rotate, skewX/skewY).
"""
import math
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np

PX_MM = 25.4 / 96.0          # 96 px por pulgada (CSS)
_UNIDADES = {"mm": 1.0, "cm": 10.0, "in": 25.4, "pt": 25.4 / 72, "pc": 25.4 / 6, "px": PX_MM, "": PX_MM}


class ErrorSVG(ValueError):
    pass


def _longitud(texto):
    m = re.match(r"\s*([-+0-9.eE]+)\s*([a-z%]*)", texto or "")
    if not m:
        return None, ""
    return float(m.group(1)), m.group(2)


def _matriz(transform):
    """Matriz 3x3 de un atributo transform de SVG."""
    m = np.identity(3)
    for nombre, args in re.findall(r"(\w+)\s*\(([^)]*)\)", transform or ""):
        v = [float(x) for x in re.findall(r"[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?", args)]
        t = np.identity(3)
        if nombre == "matrix" and len(v) == 6:
            t = np.array([[v[0], v[2], v[4]], [v[1], v[3], v[5]], [0, 0, 1]])
        elif nombre == "translate":
            t[0, 2], t[1, 2] = v[0], (v[1] if len(v) > 1 else 0.0)
        elif nombre == "scale":
            t[0, 0], t[1, 1] = v[0], (v[1] if len(v) > 1 else v[0])
        elif nombre == "rotate":
            a = math.radians(v[0])
            r = np.array([[math.cos(a), -math.sin(a), 0], [math.sin(a), math.cos(a), 0], [0, 0, 1]])
            if len(v) == 3:
                t = np.array([[1, 0, v[1]], [0, 1, v[2]], [0, 0, 1]]) @ r @ np.array([[1, 0, -v[1]], [0, 1, -v[2]],
                                                                                      [0, 0, 1]])
            else:
                t = r
        elif nombre == "skewX":
            t[0, 1] = math.tan(math.radians(v[0]))
        elif nombre == "skewY":
            t[1, 0] = math.tan(math.radians(v[0]))
        m = m @ t
    return m


def _numeros(texto):
    return [float(x) for x in re.findall(r"[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?", texto or "")]


def _arco_a_beziers(p0, rx, ry, phi, grande, barrido, p1):
    """Arco elíptico de SVG (notación de extremos) → lista de Bézier cúbicas (≤ 90° cada una)."""
    if rx == 0 or ry == 0 or np.allclose(p0, p1):
        return [[p0, p0, p1, p1]]
    rx, ry = abs(rx), abs(ry)
    c, s = math.cos(math.radians(phi)), math.sin(math.radians(phi))
    dx, dy = (p0[0] - p1[0]) / 2, (p0[1] - p1[1]) / 2
    x1, y1 = c * dx + s * dy, -s * dx + c * dy
    lam = x1 * x1 / (rx * rx) + y1 * y1 / (ry * ry)
    if lam > 1:
        rx, ry = rx * math.sqrt(lam), ry * math.sqrt(lam)
    num = rx * rx * ry * ry - rx * rx * y1 * y1 - ry * ry * x1 * x1
    den = rx * rx * y1 * y1 + ry * ry * x1 * x1
    k = math.sqrt(max(num / den, 0.0)) * (-1 if grande == barrido else 1)
    cx1, cy1 = k * rx * y1 / ry, -k * ry * x1 / rx
    cx, cy = c * cx1 - s * cy1 + (p0[0] + p1[0]) / 2, s * cx1 + c * cy1 + (p0[1] + p1[1]) / 2
    ang = lambda ux, uy, vx, vy: math.atan2(ux * vy - uy * vx, ux * vx + uy * vy)  # noqa: E731
    t1 = ang(1, 0, (x1 - cx1) / rx, (y1 - cy1) / ry)
    dt = ang((x1 - cx1) / rx, (y1 - cy1) / ry, (-x1 - cx1) / rx, (-y1 - cy1) / ry)
    if not barrido and dt > 0:
        dt -= 2 * math.pi
    elif barrido and dt < 0:
        dt += 2 * math.pi
    n = max(1, int(math.ceil(abs(dt) / (math.pi / 2) - 1e-9)))
    salida, paso = [], dt / n
    alfa = 4 / 3 * math.tan(paso / 4)
    punto = lambda t: (cx + rx * math.cos(t) * c - ry * math.sin(t) * s, cy + rx * math.cos(t) * s + ry * math.sin(t) * c)  # noqa: E731,E501
    deriv = lambda t: (-rx * math.sin(t) * c - ry * math.cos(t) * s, -rx * math.sin(t) * s + ry * math.cos(t) * c)  # noqa: E731,E501
    for i in range(n):
        ta, tb = t1 + i * paso, t1 + (i + 1) * paso
        a, b = punto(ta), punto(tb)
        da, db = deriv(ta), deriv(tb)
        salida.append([a, (a[0] + alfa * da[0], a[1] + alfa * da[1]), (b[0] - alfa * db[0], b[1] - alfa * db[1]), b])
    salida[0][0], salida[-1][3] = tuple(p0), tuple(p1)
    return salida


def _path(d):
    """Comandos de un atributo d → lista de ('linea', a, b) | ('bezier', [4 puntos]) en coordenadas SVG."""
    fichas = re.findall(r"[MmLlHhVvCcSsQqTtAaZz]|[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?", d or "")
    salida, i = [], 0
    cur = inicio = (0.0, 0.0)
    ultimo_ctrl, ultimo_cmd, cmd = None, "", None

    def leer(n):
        nonlocal i
        vals = [float(x) for x in fichas[i:i + n]]
        i += n
        if len(vals) < n:
            raise ErrorSVG("Comando de trazado incompleto en el SVG.")
        return vals

    while i < len(fichas):
        if re.match(r"[A-Za-z]", fichas[i]):
            cmd = fichas[i]
            i += 1
            if cmd in "Zz":
                if cur != inicio:
                    salida.append(("linea", cur, inicio))
                cur = inicio
                ultimo_cmd = cmd
                continue
        if cmd is None:
            raise ErrorSVG("El trazado SVG no empieza con un comando.")
        rel = cmd.islower()
        base = cur if rel else (0.0, 0.0)
        c = cmd.upper()
        if c == "M":
            x, y = leer(2)
            cur = inicio = (base[0] + x, base[1] + y)
            cmd = "l" if rel else "L"            # los pares siguientes son líneas
        elif c == "L":
            x, y = leer(2)
            nuevo = (base[0] + x, base[1] + y)
            salida.append(("linea", cur, nuevo))
            cur = nuevo
        elif c == "H":
            (x,) = leer(1)
            nuevo = ((cur[0] + x) if rel else x, cur[1])
            salida.append(("linea", cur, nuevo))
            cur = nuevo
        elif c == "V":
            (y,) = leer(1)
            nuevo = (cur[0], (cur[1] + y) if rel else y)
            salida.append(("linea", cur, nuevo))
            cur = nuevo
        elif c in "CS":
            if c == "C":
                v = leer(6)
                c1 = (base[0] + v[0], base[1] + v[1])
                c2, fin = (base[0] + v[2], base[1] + v[3]), (base[0] + v[4], base[1] + v[5])
            else:
                v = leer(4)
                c1 = (2 * cur[0] - ultimo_ctrl[0], 2 * cur[1] - ultimo_ctrl[1]) if ultimo_cmd in "CcSs" else cur
                c2, fin = (base[0] + v[0], base[1] + v[1]), (base[0] + v[2], base[1] + v[3])
            salida.append(("bezier", [cur, c1, c2, fin]))
            ultimo_ctrl, cur = c2, fin
        elif c in "QT":
            if c == "Q":
                v = leer(4)
                q, fin = (base[0] + v[0], base[1] + v[1]), (base[0] + v[2], base[1] + v[3])
            else:
                v = leer(2)
                q = (2 * cur[0] - ultimo_ctrl[0], 2 * cur[1] - ultimo_ctrl[1]) if ultimo_cmd in "QqTt" else cur
                fin = (base[0] + v[0], base[1] + v[1])
            c1 = (cur[0] + 2 / 3 * (q[0] - cur[0]), cur[1] + 2 / 3 * (q[1] - cur[1]))
            c2 = (fin[0] + 2 / 3 * (q[0] - fin[0]), fin[1] + 2 / 3 * (q[1] - fin[1]))
            salida.append(("bezier", [cur, c1, c2, fin]))
            ultimo_ctrl, cur = q, fin
        elif c == "A":
            rx, ry, phi, grande, barrido, x, y = leer(7)
            fin = (base[0] + x, base[1] + y)
            for bz in _arco_a_beziers(cur, rx, ry, phi, bool(grande), bool(barrido), fin):
                salida.append(("bezier", bz))
            cur = fin
        ultimo_cmd = cmd
    return salida


def _transformar(prim, m):
    f = lambda p: tuple((m @ np.array([p[0], p[1], 1.0]))[:2])  # noqa: E731
    if prim[0] == "linea":
        return ("linea", f(prim[1]), f(prim[2]))
    if prim[0] == "bezier":
        return ("bezier", [f(p) for p in prim[1]])
    if prim[0] == "polilinea":
        return ("polilinea", [f(p) for p in prim[1]], prim[2])
    raise ErrorSVG(prim[0])


def _elipse_beziers(cx, cy, rx, ry):
    k = 0.5522847498
    p = [(cx + rx, cy), (cx, cy + ry), (cx - rx, cy), (cx, cy - ry)]
    salida = []
    for i in range(4):
        a, b = p[i], p[(i + 1) % 4]
        ta = [(0, ry * k), (-rx * k, 0), (0, -ry * k), (rx * k, 0)][i]
        tb = [(rx * k, 0), (0, ry * k), (-rx * k, 0), (0, -ry * k)][i]
        salida.append(("bezier", [a, (a[0] + ta[0], a[1] + ta[1]), (b[0] + tb[0], b[1] + tb[1]), b]))
    return salida


def leer_svg(ruta):
    """Primitivas 2D en mm del SVG (Y hacia arriba). Los círculos y arcos de círculo sin deformar quedan como
    círculos/arcos; las curvas como Bézier cúbicas."""
    try:
        raiz = ET.fromstring(Path(ruta).read_bytes())
    except (ET.ParseError, OSError) as e:
        raise ErrorSVG(f"No se pudo leer el SVG: {e}") from e
    ns = lambda t: t.split("}")[-1]  # noqa: E731
    # escala del documento: width/height con unidades + viewBox
    escala = PX_MM
    ancho, u = _longitud(raiz.get("width", ""))
    vb = _numeros(raiz.get("viewBox", ""))
    if ancho and len(vb) == 4 and vb[2] > 0:
        escala = ancho * _UNIDADES.get(u, PX_MM) / vb[2]
    elif ancho and u in _UNIDADES and u not in ("", "px"):
        escala = _UNIDADES[u]
    # Y hacia arriba y la esquina inferior izquierda del dibujo en el origen del boceto (como al
    # insertar un SVG en Fusion: el dibujo queda en el cuadrante positivo).
    if len(vb) == 4:
        x0, alto = vb[0], vb[1] + vb[3]
    else:
        alto_doc, u_alto = _longitud(raiz.get("height", ""))
        x0, alto = 0.0, (alto_doc * _UNIDADES.get(u_alto, PX_MM) / escala) if alto_doc else 0.0
    base = np.array([[escala, 0, -escala * x0], [0, -escala, escala * alto], [0, 0, 1.0]])
    salida = []

    def visitar(nodo, m):
        m = m @ _matriz(nodo.get("transform"))
        t = ns(nodo.tag)
        prims = []
        if t == "path":
            prims = _path(nodo.get("d"))
        elif t == "line":
            x1, y1, x2, y2 = (float(nodo.get(k, 0)) for k in ("x1", "y1", "x2", "y2"))
            prims = [("linea", (x1, y1), (x2, y2))]
        elif t in ("polyline", "polygon"):
            v = _numeros(nodo.get("points"))
            pts = list(zip(v[0::2], v[1::2], strict=False))
            if len(pts) >= 2:
                prims = [("polilinea", pts, t == "polygon")]
        elif t == "rect":
            x, y, w, h = (float(_longitud(nodo.get(k, "0"))[0] or 0) for k in ("x", "y", "width", "height"))
            prims = [("polilinea", [(x, y), (x + w, y), (x + w, y + h), (x, y + h)], True)]
        elif t in ("circle", "ellipse"):
            cx, cy = float(nodo.get("cx", 0)), float(nodo.get("cy", 0))
            rx = float(nodo.get("r", 0)) if t == "circle" else float(nodo.get("rx", 0))
            ry = float(nodo.get("r", 0)) if t == "circle" else float(nodo.get("ry", 0))
            total = m
            # círculo exacto si la transformación total es semejanza (sin deformar)
            a = total[:2, :2]
            sx, sy = np.linalg.norm(a[:, 0]), np.linalg.norm(a[:, 1])
            if abs(rx - ry) < 1e-9 and abs(sx - sy) < 1e-9 * max(sx, 1) and abs(float(a[:, 0] @ a[:, 1])) < 1e-9:
                c = total @ np.array([cx, cy, 1.0])
                salida.append(("circulo", (float(c[0]), float(c[1])), rx * sx))
                prims = []
            else:
                prims = _elipse_beziers(cx, cy, rx, ry)
        for p in prims:
            salida.append(_transformar(p, m))
        for hijo in nodo:
            if ns(hijo.tag) not in ("defs", "clipPath", "mask", "symbol", "style", "metadata", "title", "desc"):
                visitar(hijo, m)

    visitar(raiz, base)
    if not salida:
        raise ErrorSVG("El SVG no tiene geometría que se pueda importar.")
    return salida

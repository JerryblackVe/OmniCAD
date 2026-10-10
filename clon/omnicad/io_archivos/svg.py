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


_COLORES = {"black": "#000000", "white": "#ffffff", "red": "#ff0000", "green": "#008000", "lime": "#00ff00",
            "blue": "#0000ff", "yellow": "#ffff00", "cyan": "#00ffff", "magenta": "#ff00ff", "gray": "#808080",
            "grey": "#808080", "orange": "#ffa500", "purple": "#800080", "brown": "#a52a2a", "pink": "#ffc0cb"}
_NO_DIBUJAN = ("defs", "clipPath", "mask", "symbol", "style", "metadata", "title", "desc", "script")


def _color(valor):
    """Color de un atributo SVG en '#rrggbb' minúscula; 'none' si no se pinta; None si no está definido."""
    if valor is None:
        return None
    v = valor.strip().lower()
    if v in ("", "inherit", "currentcolor"):
        return None
    if v == "none" or v.startswith("url("):
        return "none"
    if v in _COLORES:
        return _COLORES[v]
    m = re.fullmatch(r"#([0-9a-f]{3})", v)
    if m:
        return "#" + "".join(c * 2 for c in m.group(1))
    m = re.fullmatch(r"rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)", v)
    if m:
        return "#%02x%02x%02x" % tuple(min(255, int(g)) for g in m.groups())
    return v


def _estilo(nodo):
    """{propiedad: valor} del atributo style y de los atributos de presentación (style gana)."""
    d = {k: nodo.get(k) for k in ("stroke", "fill", "display", "visibility") if nodo.get(k) is not None}
    for par in (nodo.get("style") or "").split(";"):
        if ":" in par:
            k, _, v = par.partition(":")
            d[k.strip().lower()] = v.strip()
    return d


def _recorrer(ruta):
    """[(primitiva, capa, color)] del SVG: `capa` es la tupla de ids/etiquetas de los grupos que la contienen
    y `color` el '#rrggbb' del trazo (o del relleno si no hay trazo); None si no se pinta."""
    try:
        raiz = ET.fromstring(Path(ruta).read_bytes())
    except (ET.ParseError, OSError) as e:
        raise ErrorSVG(f"No se pudo leer el SVG: {e}") from e
    ns = lambda t: t.split("}")[-1]  # noqa: E731
    ids = {n.get("id"): n for n in raiz.iter() if n.get("id")}
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

    def visitar(nodo, m, capa, heredado, profundidad=0):
        if profundidad > 40:
            return
        est = _estilo(nodo)
        if est.get("display") == "none" or est.get("visibility") in ("hidden", "collapse"):
            return
        t = ns(nodo.tag)
        stroke = _color(est.get("stroke")) or heredado[0]
        fill = _color(est.get("fill")) or heredado[1]
        heredado = (stroke, fill)
        if t == "g":
            nombre = nodo.get("{http://www.inkscape.org/namespaces/inkscape}label") or nodo.get("id")
            if nombre:
                capa = capa + (nombre,)
        if stroke not in (None, "none"):
            color = stroke
        elif fill not in (None, "none"):
            color = fill
        else:
            color = "#000000" if fill is None and stroke is None else None
        m = m @ _matriz(nodo.get("transform"))
        prims = []
        if t == "use":
            ref = (nodo.get("{http://www.w3.org/1999/xlink}href") or nodo.get("href") or "").lstrip("#")
            objetivo = ids.get(ref)
            if objetivo is not None:
                d = np.identity(3)
                d[0, 2], d[1, 2] = (float(_longitud(nodo.get(k, "0"))[0] or 0) for k in ("x", "y"))
                visitar(objetivo, m @ d, capa, heredado, profundidad + 1)
        elif t == "path":
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
            # círculo exacto si la transformación total es semejanza (sin deformar)
            a = m[:2, :2]
            sx, sy = np.linalg.norm(a[:, 0]), np.linalg.norm(a[:, 1])
            if abs(rx - ry) < 1e-9 and abs(sx - sy) < 1e-9 * max(sx, 1) and abs(float(a[:, 0] @ a[:, 1])) < 1e-9:
                c = m @ np.array([cx, cy, 1.0])
                salida.append((("circulo", (float(c[0]), float(c[1])), rx * sx), capa, color))
                prims = []
            else:
                prims = _elipse_beziers(cx, cy, rx, ry)
        for p in prims:
            salida.append((_transformar(p, m), capa, color))
        for hijo in nodo:
            if ns(hijo.tag) not in _NO_DIBUJAN:
                visitar(hijo, m, capa, heredado, profundidad)

    visitar(raiz, base, (), (None, None))
    return salida


def leer_svg(ruta, capas=None, colores=None):
    """Primitivas 2D en mm del SVG (Y hacia arriba). Los círculos y arcos de círculo sin deformar quedan como
    círculos/arcos; las curvas como Bézier cúbicas. Soporta `use`, grupos anidados y oculta lo que tiene
    display:none. `capas`: solo lo que está dentro de un grupo con alguno de esos ids o etiquetas;
    `colores`: solo los trazos (o rellenos) de esos '#rrggbb'. Ver `listar_capas_svg`."""
    capas = {str(c).casefold() for c in capas} if capas else None
    colores = {_color(c) or str(c).casefold() for c in colores} if colores else None
    salida = []
    for prim, capa, color in _recorrer(ruta):
        if capas is not None and not any(g.casefold() in capas for g in capa):
            continue
        if colores is not None and color not in colores:
            continue
        salida.append(prim)
    if not salida:
        filtro = " con ese filtro de capas o colores" if (capas or colores) else ""
        raise ErrorSVG(f"El SVG no tiene geometría que se pueda importar{filtro}.")
    return salida


def listar_capas_svg(ruta):
    """Resumen del SVG para elegir qué importar: {'capas': {nombre: cantidad}, 'colores': {'#rrggbb': cantidad},
    'total': n} (cantidad de primitivas)."""
    capas, colores, total = {}, {}, 0
    for _prim, capa, color in _recorrer(ruta):
        total += 1
        for g in capa:
            capas[g] = capas.get(g, 0) + 1
        if color is not None:
            colores[color] = colores.get(color, 0) + 1
    return {"capas": capas, "colores": colores, "total": total}


def _n(v):
    s = f"{v:.4f}".rstrip("0").rstrip(".")
    return "0" if s in ("", "-0") else s


def escribir_svg(ruta, primitivas, construccion=()):
    """Escribe un SVG en milímetros con las primitivas de `Boceto.geometria()` ('linea', 'circulo', 'arco',
    'elipse' y, muestreadas en polilíneas, 'arco_elipse' y 'spline'). La esquina inferior izquierda del dibujo
    queda en el origen del archivo y el eje Y se da vuelta (SVG crece hacia abajo): al insertarlo de nuevo con
    `leer_svg` vuelve a su lugar. `construccion`: ids de curvas que van en un grupo aparte con trazos.
    Devuelve (ancho, alto) en mm."""
    from ..restricciones.boceto import puntos_primitiva
    construccion = set(construccion)
    pts = []
    for p in primitivas:
        if p[0] == "circulo":
            (cx, cy), r = p[2], p[3]
            pts += [(cx - r, cy - r), (cx + r, cy + r)]
        else:
            pts += puntos_primitiva(p)
    if not pts:
        raise ErrorSVG("El boceto no tiene geometría para guardar.")
    x0, y0 = min(q[0] for q in pts), min(q[1] for q in pts)
    ancho, alto = max(q[0] for q in pts) - x0, max(q[1] for q in pts) - y0
    X = lambda x: _n(x - x0)           # noqa: E731
    Y = lambda y: _n(alto - (y - y0))  # noqa: E731
    normales, aparte = [], []
    for p in primitivas:
        t, cid = p[0], p[1]
        if t == "linea":
            d = f"<line x1=\"{X(p[2][0])}\" y1=\"{Y(p[2][1])}\" x2=\"{X(p[3][0])}\" y2=\"{Y(p[3][1])}\"/>"
        elif t == "circulo":
            d = f"<circle cx=\"{X(p[2][0])}\" cy=\"{Y(p[2][1])}\" r=\"{_n(p[3])}\"/>"
        elif t == "arco":
            (cx, cy), r, a0, a1 = p[2], p[3], p[4], p[5]
            barrido = (a1 - a0) % (2 * math.pi)
            ini = (cx + r * math.cos(a0), cy + r * math.sin(a0))
            fin = (cx + r * math.cos(a1), cy + r * math.sin(a1))
            grande = 1 if barrido > math.pi else 0
            d = (f"<path d=\"M {X(ini[0])} {Y(ini[1])} A {_n(r)} {_n(r)} 0 {grande} 1 {X(fin[0])} {Y(fin[1])}\"/>")
        elif t == "elipse":
            (cx, cy), a, b, ang = p[2], p[3], p[4], p[5]
            d = (f"<ellipse cx=\"{X(cx)}\" cy=\"{Y(cy)}\" rx=\"{_n(a)}\" ry=\"{_n(b)}\" "
                 f"transform=\"rotate({_n(-math.degrees(ang))} {X(cx)} {Y(cy)})\"/>")
        else:
            q = puntos_primitiva(p, pasos=128)
            d = "<path d=\"M " + " L ".join(f"{X(a)} {Y(b)}" for a, b in q) + "\"/>"
        (aparte if cid in construccion else normales).append(d)
    lineas = [f"<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"{_n(ancho)}mm\" height=\"{_n(alto)}mm\" "
              f"viewBox=\"0 0 {_n(ancho)} {_n(alto)}\">",
              "<g id=\"boceto\" fill=\"none\" stroke=\"#000000\" stroke-width=\"0.1\">", *normales, "</g>"]
    if aparte:
        lineas += ["<g id=\"construccion\" fill=\"none\" stroke=\"#0000ff\" stroke-width=\"0.1\" "
                   "stroke-dasharray=\"1 1\">", *aparte, "</g>"]
    lineas.append("</svg>")
    Path(ruta).write_text("\n".join(lineas) + "\n", encoding="utf-8")
    return ancho, alto

# -*- coding: utf-8 -*-
"""
Escritura de SVG a partir de las primitivas del dibujo (PL9: «Exportar líneas ocultas a SVG» de Plasticity).

Las mismas primitivas que lee `escribir_dxf`: pares (capa, primitiva) con "linea", "polilinea", "spline", "circulo",
"arco" (radianes, antihorario), "elipse", "texto" y "solido", en mm con Y hacia arriba. El SVG sale en mm (la unidad
del papel), con una capa `<g>` por tipo de línea: las ocultas en trazos, como en la hoja y en el DXF.
Lo contrario, leer un SVG, está en `svg.py`.
"""
import math
import re
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr

from .svg import _n

# Color ACI de las capas del dibujo → color de papel (el 7 es negro sobre blanco).
_COLOR = {1: "#d02020", 3: "#2a8a2a", 7: "#000000", 8: "#808080", 9: "#a0a0a0"}
_TRAZOS = {"trazos": "3 1.5", "trazo_punto": "6 1.5 0.5 1.5"}
_VIVAS = {"grosor": 0.25, "tipo": "continua", "color": 7}      # una capa usada sin datos, como en el DXF
_PASOS_CURVA = 48
MARGEN = 5.0                 # mm alrededor de lo dibujado cuando la hoja no trae su tamaño
# La altura de un texto del dibujo es la de las MAYÚSCULAS (como en el DXF y el PDF de la hoja); en SVG font-size es el
# cuerpo entero (em): en Arial las mayúsculas miden 0,716 em.
_MAYUSCULA_ARIAL = 0.716
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")     # caracteres que XML 1.0 no admite


def _es_par(e):
    """¿Es (capa, primitiva)? Una primitiva sola es («linea», punto, punto…): su segundo elemento no empieza con texto."""
    return (len(e) == 2 and isinstance(e[0], str) and isinstance(e[1], (tuple, list)) and bool(e[1])
            and isinstance(e[1][0], str))


def _cajas(prim):
    """Esquinas (mín, máx) de una primitiva en el plano del dibujo."""
    t = prim[0]
    if t == "linea":
        pts = [prim[1], prim[2]]
    elif t in ("circulo", "arco"):
        (cx, cy), r = prim[1], prim[2]
        pts = [(cx - r, cy - r), (cx + r, cy + r)]
    elif t == "elipse":
        pts = _puntos_elipse(prim)
    elif t == "texto":
        pts = [prim[1]]
    else:
        pts = list(prim[1])
    return pts


def _puntos_elipse(prim):
    _, c, m, razon, t0, t1 = prim
    if abs((t1 - t0) - 2 * math.pi) < 1e-9 or abs(t1 - t0) < 1e-12:
        t0, t1 = t0, t0 + 2 * math.pi
    mx, my = m
    nx, ny = -my * razon, mx * razon
    return [(c[0] + mx * math.cos(t) + nx * math.sin(t), c[1] + my * math.cos(t) + ny * math.sin(t))
            for t in (t0 + (t1 - t0) * k / _PASOS_CURVA for k in range(_PASOS_CURVA + 1))]


def _elemento(prim, y):
    """Elemento SVG de una primitiva; `y(v)` pasa la Y del dibujo (arriba) a la del SVG (abajo)."""
    t = prim[0]
    if t == "linea":
        (x1, y1), (x2, y2) = prim[1], prim[2]
        return f'<line x1="{_n(x1)}" y1="{_n(y(y1))}" x2="{_n(x2)}" y2="{_n(y(y2))}"/>'
    if t in ("polilinea", "spline"):
        pts = [tuple(p) for p in prim[1]]
        if len(pts) < 2:
            return ""
        cerrada = t == "polilinea" and len(prim) > 2 and bool(prim[2])
        lista = " ".join(f"{_n(px)},{_n(y(py))}" for px, py in pts)
        return f'<{"polygon" if cerrada else "polyline"} points="{lista}"/>'
    if t == "circulo":
        (cx, cy), r = prim[1], prim[2]
        return f'<circle cx="{_n(cx)}" cy="{_n(y(cy))}" r="{_n(r)}"/>'
    if t == "arco":
        (cx, cy), r, a0, a1 = prim[1], prim[2], prim[3], prim[4]
        barrido = (a1 - a0) % (2 * math.pi)
        if barrido < 1e-9:                                    # inicio = fin: una vuelta completa
            return _elemento(("circulo", (cx, cy), r), y)
        p0 = (cx + r * math.cos(a0), cy + r * math.sin(a0))
        p1 = (cx + r * math.cos(a0 + barrido), cy + r * math.sin(a0 + barrido))
        grande = 1 if barrido > math.pi else 0
        # Con Y hacia abajo, el antihorario del dibujo es sweep-flag 0.
        return (f'<path d="M {_n(p0[0])} {_n(y(p0[1]))} A {_n(r)} {_n(r)} 0 {grande} 0 '
                f'{_n(p1[0])} {_n(y(p1[1]))}"/>')
    if t == "elipse":
        pts = _puntos_elipse(prim)
        completa = abs((prim[5] - prim[4]) - 2 * math.pi) < 1e-9 or abs(prim[5] - prim[4]) < 1e-12
        return _elemento(("polilinea", pts, completa), y)
    if t == "texto":
        px, py = prim[1]
        altura, texto = prim[2], prim[3]
        rot = prim[4] if len(prim) > 4 else 0.0
        ancla = {"izq": "start", "centro": "middle", "der": "end"}.get(prim[5] if len(prim) > 5 else "izq", "start")
        giro = f' transform="rotate({_n(-rot)} {_n(px)} {_n(y(py))})"' if rot else ""
        return (f'<text x="{_n(px)}" y="{_n(y(py))}" font-size="{_n(altura / _MAYUSCULA_ARIAL)}" text-anchor="{ancla}" '
                f'font-family="Arial, sans-serif" fill="currentColor" stroke="none"{giro}>'
                f'{escape(_CONTROL.sub("", str(texto)))}</text>')
    if t == "solido":
        pts = [tuple(p) for p in prim[1]]
        if len(pts) < 3:
            return ""
        orden = pts if len(pts) == 3 else [pts[0], pts[1], pts[3], pts[2]]    # SOLID se recorre 1-2-4-3
        return f'<polygon points="{" ".join(f"{_n(px)},{_n(y(py))}" for px, py in orden)}" fill="currentColor"/>'
    raise ValueError(f"Primitiva desconocida para SVG: {t}")


def a_texto_svg(entidades, capas=None, ancho=None, alto=None):
    """Contenido SVG (str). entidades: primitivas (capa "0") o pares (capa, primitiva); capas: {nombre: {"color": ACI,
    "tipo": "continua" | "trazos" | "trazo_punto", "grosor": mm}}. Con `ancho` y `alto` (mm) la hoja mide eso, con el
    origen del dibujo abajo a la izquierda; sin ellos, la caja de lo dibujado más MARGEN mm alrededor."""
    pares = [e if _es_par(e) else ("0", e) for e in entidades]
    if ancho is None or alto is None:
        pts = [p for _c, prim in pares for p in _cajas(prim)]
        if not pts:
            raise ValueError("No hay nada que escribir en el SVG.")
        x0, y0 = min(p[0] for p in pts) - MARGEN, min(p[1] for p in pts) - MARGEN
        ancho, alto = max(p[0] for p in pts) + MARGEN - x0, max(p[1] for p in pts) + MARGEN - y0
        techo = y0 + alto
    else:
        x0, y0, techo = 0.0, 0.0, float(alto)
    por_capa = {}
    for capa, prim in pares:
        por_capa.setdefault(capa, []).append(_elemento(prim, lambda v: techo - v))
    capas = capas or {}
    salida = ['<?xml version="1.0" encoding="UTF-8"?>',
              f'<svg xmlns="http://www.w3.org/2000/svg" width="{_n(ancho)}mm" height="{_n(alto)}mm" '
              f'viewBox="{_n(x0)} 0 {_n(ancho)} {_n(alto)}" color="#000000">']
    for capa, elementos in por_capa.items():
        estilo = capas.get(capa, _VIVAS)
        trazo = _TRAZOS.get(estilo.get("tipo", "continua"))
        atributos = (f'fill="none" stroke="{_COLOR.get(estilo.get("color", 7), "#000000")}" '
                     f'stroke-width="{_n(estilo.get("grosor", 0.25))}" stroke-linecap="round" stroke-linejoin="round"'
                     + (f' stroke-dasharray="{trazo}"' if trazo else ""))
        salida.append(f'<g id={quoteattr(str(capa))} {atributos}>')
        salida += [f"  {e}" for e in elementos if e]
        salida.append("</g>")
    salida.append("</svg>")
    return "\n".join(salida) + "\n"


def escribir_svg(ruta, entidades, capas=None, ancho=None, alto=None):
    """Escribe el SVG en `ruta` (UTF-8); ver `a_texto_svg`. Devuelve la ruta."""
    Path(ruta).write_text(a_texto_svg(entidades, capas, ancho, alto), encoding="utf-8")
    return Path(ruta)

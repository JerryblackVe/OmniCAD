# -*- coding: utf-8 -*-
"""Herramientas del grupo "dibujo" para SACAR la hoja: exportar a DXF, SVG o PDF y verla como imagen.

Sin Qt: el DXF, el SVG y el PDF salen de las primitivas del plano (`Dibujo.primitivas()`, mm con Y hacia arriba)
con los escritores de `io_archivos` (`dxf`, `svg_salida`, `pdf_salida`); la imagen se dibuja con Pillow.
"""
import io
import math
from pathlib import Path
from typing import Literal

from ..io_archivos import dxf, pdf_salida, svg_salida
from ..nucleo import dibujo as nd
from .errores import error
from .herramientas_dibujo import cargar_dibujo
from .registro import Imagen, herramienta
from .sesion import borrar_carpetas, crear_carpeta

_FORMATOS = ("dxf", "svg", "pdf")
_ANCHO_MINIMO, _ANCHO_MAXIMO = 200, 4000
_PASO_CURVA = math.radians(3.0)


def _titulo(sesion, d):
    return (d.cajetin.get("titulo") or sesion.doc.nombre or "Dibujo").strip()


def _escribir(formato, ruta, d, titulo, version):
    prims = d.primitivas()
    if formato == "dxf":
        dxf.escribir_dxf(ruta, prims, capas=nd.CAPAS, version=version)
    elif formato == "svg":
        svg_salida.escribir_svg(ruta, prims, nd.CAPAS, d.ancho, d.alto)
    else:
        pdf_salida.escribir_pdf(ruta, prims, nd.CAPAS, d.ancho, d.alto, titulo)


@herramienta("export_drawing", "dibujo", "Exporta la hoja del dibujo (vistas, cotas, marco y cajetín) a DXF (capas por "
             "tipo de línea, en mm), SVG (mm, una capa por tipo de línea) o PDF vectorial a escala real; el formato sale "
             "de la extensión o de format. Crea las carpetas que falten (create_folders=false para que falle con "
             "FILE_NOT_FOUND).")
def export_drawing(sesion, path: str, format: Literal["dxf", "svg", "pdf"] | None = None, overwrite: bool = False,
                   create_folders: bool = True, dxf_version: Literal["2000", "R12"] = "2000"):
    """
    path: ruta del archivo a escribir; si no tiene la extensión del formato, se la agrega.
    format: "dxf", "svg" o "pdf"; vacío = el de la extensión de path.
    overwrite: true para reemplazar el archivo si ya existe.
    create_folders: true (por defecto) crea las carpetas de la ruta que no existen (se avisa); false = FILE_NOT_FOUND.
    dxf_version: solo para DXF: "2000" (AC1015) o "R12" (AC1009).
    """
    if not str(path).strip():
        raise error("INVALID_ARGUMENTS", "path está vacío: tiene que ser la ruta del archivo a escribir.")
    ruta = Path(path)
    if ruta.is_dir():
        raise error("INVALID_ARGUMENTS", f"path es una carpeta ({ruta}): tiene que ser un archivo.")
    formato = (format or ruta.suffix.lower().lstrip(".")).lower()
    if formato not in _FORMATOS:
        raise error("INVALID_FORMAT", f"Formato no soportado: {formato or '(sin extensión)'} (usá dxf, svg o pdf).")
    if ruta.suffix.lower() != f".{formato}":
        ruta = ruta.with_name(ruta.name + f".{formato}")
    d = cargar_dibujo(sesion)
    if not d.vistas:
        raise error("NOTHING_TO_RENDER", "El dibujo no tiene vistas: add_drawing_view agrega la primera.")
    if ruta.exists() and not overwrite:
        raise error("FILE_EXISTS", f"Ya existe el archivo: {ruta}")
    nuevas = crear_carpeta(ruta.parent) if create_folders else []
    if not ruta.parent.is_dir():
        raise error("FILE_NOT_FOUND", f"No existe la carpeta: {ruta.parent}",
                    "export_drawing crea las carpetas que faltan con create_folders=true.")
    try:
        _escribir(formato, ruta, d, _titulo(sesion, d), dxf_version)
    except (OSError, dxf.ErrorDXF, ValueError) as e:
        borrar_carpetas(nuevas)
        raise error("FILE_ERROR", f"No se pudo guardar {formato.upper()}: {e}") from None
    if nuevas:
        sesion.avisar(f"Se creó la carpeta {ruta.parent}.")
    return {"path": str(ruta.resolve()), "format": formato, "size_bytes": ruta.stat().st_size,
            "sheet": {"size": d.tamano, "width": d.ancho, "height": d.alto}}


# ---------------------------------------------------------------- imagen de la hoja (Pillow)
def _fuente(px):
    from PIL import ImageFont
    for nombre in ("arial.ttf", "segoeui.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(nombre, px)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size=px)
    except TypeError:
        return ImageFont.load_default()


def _puntos(prim):
    """Polilínea (mm de la hoja) de una primitiva de trazo, y si es cerrada; None si no se dibuja con líneas."""
    t = prim[0]
    if t == "linea":
        return [tuple(prim[1]), tuple(prim[2])], False
    if t in ("polilinea", "spline"):
        return [tuple(p) for p in prim[1]], t == "polilinea" and len(prim) > 2 and bool(prim[2])
    if t == "circulo":
        (cx, cy), r = prim[1], prim[2]
        n = max(24, math.ceil(2 * math.pi / _PASO_CURVA))
        return [(cx + r * math.cos(2 * math.pi * k / n), cy + r * math.sin(2 * math.pi * k / n)) for k in range(n + 1)], False
    if t == "arco":
        (cx, cy), r, a0, a1 = prim[1], prim[2], prim[3], prim[4]
        barrido = (a1 - a0) % (2 * math.pi) or 2 * math.pi
        n = max(2, math.ceil(barrido / _PASO_CURVA))
        return [(cx + r * math.cos(a0 + barrido * k / n), cy + r * math.sin(a0 + barrido * k / n))
                for k in range(n + 1)], False
    if t == "elipse":
        return svg_salida._puntos_elipse(prim), False
    return None


def _trazos(pts, patron):
    """Tramos de la polilínea `pts` (px) que quedan visibles con el patrón [raya, hueco, …] (px)."""
    tramos, actual, i, resto, pinta = [], [pts[0]], 0, patron[0], True
    for a, b in zip(pts, pts[1:], strict=False):
        largo = math.dist(a, b)
        pos = 0.0
        while largo - pos > resto:
            pos += resto
            p = (a[0] + (b[0] - a[0]) * pos / largo, a[1] + (b[1] - a[1]) * pos / largo)
            if pinta:
                tramos.append(actual + [p])
            actual = [p]
            i, pinta = (i + 1) % len(patron), not pinta
            resto = patron[i]
        resto -= largo - pos
        actual.append(b)
    if pinta and len(actual) > 1:
        tramos.append(actual)
    return tramos


def _texto(img, prim, k, alto_px):
    """Pega el texto (negro, con su giro y alineación) con la esquina izquierda de su línea base en (x, y) de la hoja."""
    from PIL import Image, ImageDraw
    (x, y), altura, texto = prim[1], float(prim[2]), str(prim[3]).replace("⌀", "Ø")   # Arial no trae el ⌀
    rot = float(prim[4]) if len(prim) > 4 else 0.0
    alin = prim[5] if len(prim) > 5 else "izq"
    fuente = _fuente(max(6, round(altura * k / 0.716)))
    ancho = ImageDraw.Draw(img).textlength(texto, font=fuente)
    lado = int(2 * ancho + 4 * altura * k + 8)
    capa = Image.new("L", (lado, lado), 0)
    dx = {"izq": 0.0, "centro": -ancho / 2, "der": -ancho}.get(alin, 0.0)
    ImageDraw.Draw(capa).text((lado / 2 + dx, lado / 2), texto, fill=255, font=fuente, anchor="ls")
    capa = capa.rotate(rot, resample=Image.BICUBIC)             # gira alrededor del centro = el anclaje
    img.paste((0, 0, 0), (round(x * k - lado / 2), round(alto_px - y * k - lado / 2)), capa)


@herramienta("get_drawing_image", "dibujo", "Devuelve la hoja del dibujo como imagen PNG (fondo blanco, líneas negras "
             "con los grosores y tipos de línea reales, cotas, texto, marco y cajetín): es la forma de VER el plano.")
def get_drawing_image(sesion, width: int = 1200):
    """
    width: ancho de la imagen en píxeles (200 a 4000); el alto sale de la proporción de la hoja.
    """
    from PIL import Image, ImageDraw
    if not _ANCHO_MINIMO <= width <= _ANCHO_MAXIMO:
        raise error("INVALID_ARGUMENTS", f"width tiene que estar entre {_ANCHO_MINIMO} y {_ANCHO_MAXIMO} píxeles.")
    d = cargar_dibujo(sesion)
    if not d.vistas:
        raise error("NOTHING_TO_RENDER", "El dibujo no tiene vistas: add_drawing_view agrega la primera.")
    k = width / d.ancho                                         # píxeles por mm de hoja
    alto_px = round(d.alto * k)
    img = Image.new("RGB", (width, alto_px), "white")
    dib = ImageDraw.Draw(img)

    def px(p):
        return (p[0] * k, alto_px - p[1] * k)

    for capa, prim in d.primitivas():
        conf = nd.CAPAS.get(capa, {"grosor": 0.25, "tipo": "continua"})
        grosor = max(1, round(conf["grosor"] * k))
        if prim[0] == "texto":
            _texto(img, prim, k, alto_px)
        elif prim[0] == "solido":
            pts = [px(p) for p in prim[1]]
            if len(pts) >= 3:
                dib.polygon(pts if len(pts) == 3 else [pts[0], pts[1], pts[3], pts[2]], fill=(0, 0, 0))
        else:
            r = _puntos(prim)
            if r is None:
                continue
            pts = [px(p) for p in r[0]] + ([px(r[0][0])] if r[1] else [])
            patron = {"trazos": (3.0, 1.5), "trazo_punto": (6.0, 1.5, 0.5, 1.5)}.get(conf["tipo"])
            for tramo in (_trazos(pts, [x * k for x in patron]) if patron and len(pts) > 1 else [pts]):
                dib.line(tramo, fill=(0, 0, 0), width=grosor, joint="curve")
    buf = io.BytesIO()
    img.save(buf, "PNG", compress_level=3)
    return {"image": Imagen(buf.getvalue(), width, alto_px), "width": width, "height": alto_px,
            "sheet": {"size": d.tamano, "width": d.ancho, "height": d.alto}, "views": len(d.vistas)}

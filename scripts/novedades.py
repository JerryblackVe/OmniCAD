# -*- coding: utf-8 -*-
r"""Novedades mensuales de Fusion 360, Blender y Rhino (P-12 de docs/seguimiento/).

Baja las páginas oficiales de novedades de los tres programas, escribe un informe corto en
`docs/novedades/<AAAA-MM>.md` y agrega cada titular que no estaba como pendiente sin clasificar al final
del `docs/brechas_*.md` que corresponda (sección «Novedades automáticas», para revisar y clasificar a
mano; es idempotente: correrlo otra vez no duplica).

Sin dependencias nuevas: urllib de la biblioteca estándar. Nada se paga, nada se instala.

Uso (desde la raíz del repo):
    clon/.venv/Scripts/python.exe scripts/novedades.py                 # mes en curso
    clon/.venv/Scripts/python.exe scripts/novedades.py --salida /tmp/informe.md --brechas /tmp
    clon/.venv/Scripts/python.exe scripts/novedades.py --offline      # no toca la red (prueba)

Tarea mensual de Windows (registro MANUAL, el script no toca el sistema):
    schtasks /Create /SC MONTHLY /D 1 /TN "OmniCAD novedades" /TR "\"D:\PROGRAMA\clon\.venv\Scripts\python.exe\" D:\PROGRAMA\scripts\novedades.py" /ST 09:00
"""
import argparse
import re
import sys
import time
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen

RAIZ = Path(__file__).resolve().parent.parent          # raíz del repo (docs/ vive ahí)

# (nombre, página oficial de novedades, archivo de brechas donde anotar lo nuevo, dentro de docs/)
FUENTES = {
    "fusion": ("Fusion 360", "https://help.autodesk.com/view/fusion360/ENU/?guid=WHATSNEW",
               "brechas_fusion.md"),
    "blender": ("Blender", "https://www.blender.org/news/", "brechas_blender.md"),
    "rhino": ("Rhino", "https://www.rhino3d.com/news/", "brechas_rhino.md"),
}
UA = "Mozilla/5.0 (OmniCAD novedades; +https://github.com/JerryblackVe/OmniCAD)"
TOPE_TITULARES = 20            # por fuente, en el informe
LARGO_TITULO = (12, 160)       # un titular razonable: ni un menú de 3 letras ni un párrafo entero
# Lo que NO se anota como pendiente en los brechas aunque sea un encabezado: fechas de noticias,
# «…, etc.» y otras etiquetas de sección que no dicen ninguna función.
_RUIDO_BRECHAS = re.compile(r"^(mon|tue|wed|thu|fri|sat|sun)[a-z]*,?\s+\w+\s+\d{1,2},?\s+\d{4}$"
                            r"|^(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{1,2},?\s+\d{4}$"
                            r"|,\s*etc\.?$", re.IGNORECASE)
_NAVEGACION = {"home", "login", "sign in", "read more", "learn more", "more", "news", "blog", "download",
               "documentation", "docs", "store", "pricing", "privacy", "cookie", "menu", "search",
               "skip to content", "english", "español", "contact", "about", "x", "twitter", "facebook",
               "instagram", "youtube", "linkedin", "press releases"}


class _Titulares(HTMLParser):
    """Junta el texto de los encabezados (h1 a h4) y de los enlaces que parecen titulares de entrada,
    con su href. Nada de DOM ni dependencias: alcanza para un informe corto."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.titulares = []           # (texto, href, es_encabezado)
        self._dentro = None            # [etiqueta, pedazos de texto, href]
        self._href = None

    def handle_starttag(self, etiqueta, atributos):
        if etiqueta == "a":
            self._href = dict(atributos).get("href")
            if self._dentro is not None:
                if self._dentro[0] != "a" and not self._dentro[2]:
                    self._dentro[2] = self._href      # un enlace adentro presta su href al encabezado
                return                                 # <a> dentro de otro <a>/h*: no abre uno nuevo
        if etiqueta in ("h1", "h2", "h3", "h4") or (etiqueta == "a" and self._dentro is None):
            self._dentro = [etiqueta, [], self._href]

    def handle_data(self, datos):
        if self._dentro is not None:
            self._dentro[1].append(datos)

    def _cerrar(self):
        texto = " ".join("".join(self._dentro[1]).split())
        href, es_h = self._dentro[2], self._dentro[0] != "a"
        self._dentro, self._href = None, None
        if texto and texto.lower() not in _NAVEGACION and not texto.lower().startswith(("ver ", "see ")):
            self.titulares.append((texto, href, es_h))

    def handle_endtag(self, etiqueta):
        if self._dentro is None:
            return
        if etiqueta == self._dentro[0]:
            self._cerrar()


def titulares_de(html):
    """[(texto, href, es_encabezado)] de una página HTML, sin repetidos, en el orden en que aparecen.
    Pura. Los encabezados (h1–h4) son la señal más firme de una entrada nueva; los enlaces sueltos
    llenan el informe pero no van a los brechas (menús, versiones viejas, llamados a la acción)."""
    p = _Titulares()
    try:
        p.feed(html)
    except Exception:                     # noqa: BLE001 — HTML roto: se queda con lo que juntó
        pass
    vistos, resultado = set(), []
    for texto, href, es_h in p.titulares:
        clave = texto.lower()
        if clave in vistos or not (LARGO_TITULO[0] <= len(texto) <= LARGO_TITULO[1]):
            continue
        vistos.add(clave)
        resultado.append((texto, href, es_h))
    return resultado


def bajar(url, timeout=20):
    """HTML de una página pública con User-Agent honesto. Falla con OSError/HTTPError."""
    pedido = Request(url, headers={"User-Agent": UA, "Accept-Language": "en"})
    with urlopen(pedido, timeout=timeout) as r:      # noqa: S310 — URLs fijas de arriba, no de usuario
        return r.read(2_000_000).decode("utf-8", errors="replace")


def informe(clave, url, titulares, error=None):
    """Bloque de una fuente para el informe mensual: encabezado, fuente y titulares (o el error)."""
    nombre = FUENTES[clave][0]
    lineas = [f"## {nombre}", "", f"Fuente: {url}"]
    if error is not None:
        lineas += ["", f"⚠ No se pudo leer la página este mes: {error}"]
    elif not titulares:
        lineas += ["", "⚠ La página no dio titulares reconocibles este mes: revisarla a mano."]
    else:
        lineas += ["", f"{len(titulares)} titulares:"]
        for texto, href, _es_h in titulares[:TOPE_TITULARES]:
            lineas.append(f"- {texto}" + (f"  \n  <{href}>" if href else ""))
    return "\n".join(lineas), titulares[:TOPE_TITULARES]


def anotar_en_brechas(ruta_brechas, clave, titulares, mes):
    """Agrega al final del brechas los titulares NUEVOS (solo ENCABEZADOS, no menús) como pendientes
    sin clasificar. Devuelve cuántos agregó. Es idempotente."""
    titulares = [t for t, _h, es_h in titulares if es_h and not _RUIDO_BRECHAS.search(t.strip())]
    if not titulares:
        return 0
    ruta = Path(ruta_brechas)
    contenido = ruta.read_text(encoding="utf-8") if ruta.is_file() else ""
    plano = re.sub(r"\s+", " ", contenido).strip().lower()          # ya listado en CUALQUIER sección
    nuevos = [t for t in titulares if re.sub(r"\s+", " ", t).strip().lower() not in plano]
    if not nuevos:
        return 0
    seccion = f"\n## Novedades automáticas ({mes}, sin clasificar)\n\n"
    if "## Novedades automáticas" not in contenido:
        contenido = contenido.rstrip("\n") + "\n" + seccion
    for titulo in nuevos:
        contenido += f"- [AUTO {mes}] {titulo} — pendiente de clasificar (fuente: {FUENTES[clave][1]})\n"
    ruta.write_text(contenido, encoding="utf-8", newline="\n")
    return len(nuevos)


def correr(mes=None, carpeta_novedades=None, carpeta_brechas=None, offline=False, bajar_html=None):
    """Baja las tres páginas, escribe docs/novedades/<AAAA-MM>.md y anota lo nuevo en los brechas.
    Devuelve (ruta del informe, texto). ``bajar_html`` reemplaza la red (pruebas)."""
    mes = mes or time.strftime("%Y-%m")
    carpeta_novedades = Path(carpeta_novedades) if carpeta_novedades else RAIZ / "docs" / "novedades"
    carpeta_brechas = Path(carpeta_brechas) if carpeta_brechas else RAIZ / "docs"
    carpeta_novedades.mkdir(parents=True, exist_ok=True)
    texto = (f"# Novedades del mes — {mes}\n\nInforme automático de `scripts/novedades.py` (pendiente 12): "
             f"titulares de las páginas oficiales de novedades de Fusion 360, Blender y Rhino. Lo nuevo "
             f"de cada uno queda como pendiente sin clasificar al final de su `docs/brechas_*.md`.\n")
    anotados = {}
    for clave in FUENTES:
        nombre, url, brechas = FUENTES[clave]
        titulares, error = [], None
        if offline:
            error = "corrida sin red"
        else:
            try:
                html = bajar_html(url) if bajar_html else bajar(url)
                titulares = titulares_de(html)
            except Exception as e:        # noqa: BLE001 — sin red no es una falla del informe
                error = f"{type(e).__name__}: {e}"
        bloque, recortados = informe(clave, url, titulares, error)
        texto += "\n" + bloque + "\n"
        if recortados:
            anotados[nombre] = anotar_en_brechas(carpeta_brechas / brechas, clave, recortados, mes)
    if anotados:
        texto += ("\n## Anotado en los brechas\n\n" +
                  "\n".join(f"- {n}: {c} pendiente(s) nuevo(s) al final de su archivo." for n, c in anotados.items())
                  + "\n")
    ruta = carpeta_novedades / f"{mes}.md"
    ruta.write_text(texto, encoding="utf-8", newline="\n")
    return ruta, texto


def main(argv=None):
    ap = argparse.ArgumentParser(description="Informe mensual de novedades de Fusion 360, Blender y Rhino")
    ap.add_argument("--mes", default=None, help="mes del informe, AAAA-MM (por defecto, el actual)")
    ap.add_argument("--salida", default=None, help="carpeta del informe (por defecto, docs/novedades)")
    ap.add_argument("--brechas", default=None, help="carpeta de los brechas_*.md (por defecto, docs)")
    ap.add_argument("--offline", action="store_true", help="no tocar la red (prueba del script)")
    args = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(errors="replace")       # consolas cp1252: el texto sigue saliendo
    except Exception:                                    # noqa: BLE001 — stdout raro: al print tal cual
        pass
    ruta, texto = correr(args.mes, args.salida, args.brechas, args.offline)
    print(f"escrito: {ruta}")
    print(texto[:400])
    return 0


if __name__ == "__main__":
    sys.exit(main())

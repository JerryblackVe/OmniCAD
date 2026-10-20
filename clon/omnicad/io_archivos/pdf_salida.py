# -*- coding: utf-8 -*-
"""
Escritura de PDF vectorial (PDF 1.4, sin dependencias ni Qt) a partir de las primitivas del dibujo.

Las mismas primitivas que lee `svg_salida`: pares (capa, primitiva) con "linea", "polilinea", "spline", "circulo",
"arco" (radianes, antihorario), "elipse", "texto" y "solido", en mm con Y hacia arriba. La página mide la hoja a
escala real (1 mm del dibujo = 1 mm del papel), con los grosores y tipos de línea de cada capa, todo en negro como el
PDF de la ventana. El texto va en Helvetica (WinAnsi: el ⌀ sale como Ø); los caracteres fuera de WinAnsi, como «?».
"""
import math
import zlib
from pathlib import Path

from .svg_salida import _TRAZOS, _VIVAS, _es_par, _puntos_elipse

MM_PT = 72.0 / 25.4
_MAYUSCULA = 0.718                  # altura de las mayúsculas de Helvetica por em
_PASO_ARCO = math.radians(2.0)
# Anchos de Helvetica (milésimas de em) de los caracteres 32..126 y de los WinAnsi que usa el dibujo.
_ANCHOS = ([278, 278, 355, 556, 556, 889, 667, 191, 333, 333, 389, 584, 278, 333, 278, 278]
           + [556] * 10 + [278, 278, 584, 584, 584, 556, 1015]
           + [667, 667, 722, 722, 667, 611, 778, 722, 278, 500, 667, 556, 833, 722, 778, 667, 778, 722, 667, 611, 722,
              667, 944, 667, 667, 611]
           + [278, 278, 278, 469, 556, 333]
           + [556, 556, 500, 556, 556, 278, 556, 556, 222, 222, 500, 222, 833, 556, 556, 556, 556, 333, 500, 278, 556,
              500, 722, 500, 500, 500]
           + [334, 260, 334, 584])
_ANCHOS_WIN = {0xB0: 400, 0xB1: 584, 0xD8: 778}


def _n(v):
    t = f"{float(v):.4f}".rstrip("0").rstrip(".")
    return "0" if t in ("-0", "") else t


def _bytes_texto(texto):
    return str(texto).replace("⌀", "Ø").replace("\r", " ").replace("\n", " ").encode("cp1252", "replace")


def _ancho_texto(datos, altura):
    """Ancho (mm) del texto con altura de mayúsculas `altura`."""
    em = altura / _MAYUSCULA
    return em * sum(_ANCHOS[b - 32] if 32 <= b <= 126 else _ANCHOS_WIN.get(b, 556) for b in datos) / 1000.0


def _curva(prim):
    """Puntos de una primitiva curva (arco, elipse) como polilínea fina."""
    if prim[0] == "arco":
        (cx, cy), r, a0, a1 = prim[1], prim[2], prim[3], prim[4]
        barrido = (a1 - a0) % (2 * math.pi) or 2 * math.pi
        n = max(2, math.ceil(barrido / _PASO_ARCO))
        return [(cx + r * math.cos(a0 + barrido * k / n), cy + r * math.sin(a0 + barrido * k / n)) for k in range(n + 1)]
    return _puntos_elipse(prim)


def _ruta(puntos, cerrada=False):
    ops = [f"{_n(puntos[0][0])} {_n(puntos[0][1])} m"]
    ops += [f"{_n(x)} {_n(y)} l" for x, y in puntos[1:]]
    return ops + (["h"] if cerrada else [])


def _operaciones(prim):
    """(operaciones de dibujo, tipo) de una primitiva: «trazo» (S), «relleno» (f) o «texto» (ya completo)."""
    t = prim[0]
    if t == "linea":
        return _ruta([tuple(prim[1]), tuple(prim[2])]), "trazo"
    if t in ("polilinea", "spline"):
        pts = [tuple(p) for p in prim[1]]
        cerrada = t == "polilinea" and len(prim) > 2 and bool(prim[2])
        return (_ruta(pts, cerrada) if len(pts) >= 2 else []), "trazo"
    if t == "circulo":
        (cx, cy), r = prim[1], prim[2]
        k = 0.5522847498 * r
        return [f"{_n(cx + r)} {_n(cy)} m",
                f"{_n(cx + r)} {_n(cy + k)} {_n(cx + k)} {_n(cy + r)} {_n(cx)} {_n(cy + r)} c",
                f"{_n(cx - k)} {_n(cy + r)} {_n(cx - r)} {_n(cy + k)} {_n(cx - r)} {_n(cy)} c",
                f"{_n(cx - r)} {_n(cy - k)} {_n(cx - k)} {_n(cy - r)} {_n(cx)} {_n(cy - r)} c",
                f"{_n(cx + k)} {_n(cy - r)} {_n(cx + r)} {_n(cy - k)} {_n(cx + r)} {_n(cy)} c", "h"], "trazo"
    if t in ("arco", "elipse"):
        return _ruta(_curva(prim)), "trazo"
    if t == "solido":
        pts = [tuple(p) for p in prim[1]]
        if len(pts) < 3:
            return [], "relleno"
        return _ruta(pts if len(pts) == 3 else [pts[0], pts[1], pts[3], pts[2]], True), "relleno"
    if t == "texto":
        (x, y), altura, datos = prim[1], float(prim[2]), _bytes_texto(prim[3])
        rot = math.radians(prim[4]) if len(prim) > 4 else 0.0
        ancho = _ancho_texto(datos, altura)
        dx = {"izq": 0.0, "centro": -ancho / 2, "der": -ancho}.get(prim[5] if len(prim) > 5 else "izq", 0.0)
        c, s = math.cos(rot), math.sin(rot)
        tx, ty = x + dx * c, y + dx * s
        escapado = datos.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)").decode("latin-1")
        return [f"BT /F1 {_n(altura / _MAYUSCULA)} Tf {_n(c)} {_n(s)} {_n(-s)} {_n(c)} {_n(tx)} {_n(ty)} Tm "
                f"({escapado}) Tj ET"], "texto"
    raise ValueError(f"Primitiva desconocida para PDF: {t}")


def a_bytes_pdf(entidades, capas, ancho, alto, titulo="Dibujo"):
    """Contenido del PDF (bytes). entidades: pares (capa, primitiva); capas: {nombre: {"grosor", "tipo"}}; la
    página mide `ancho` × `alto` mm."""
    pares = [e if _es_par(e) else ("0", e) for e in entidades]
    capas = capas or {}
    cont = ["0 0 0 RG 0 0 0 rg 1 J 1 j", f"{_n(MM_PT)} 0 0 {_n(MM_PT)} 0 0 cm"]
    for capa, prim in pares:
        ops, tipo = _operaciones(prim)
        if not ops:
            continue
        if tipo == "texto":
            cont += ops
            continue
        estilo = capas.get(capa, _VIVAS)
        trazos = _TRAZOS.get(estilo.get("tipo", "continua"))
        cont.append(f"{_n(estilo.get('grosor', 0.25))} w" + (f" [{trazos}] 0 d" if trazos else " [] 0 d"))
        cont += ops + ["f" if tipo == "relleno" else "S"]
    flujo = zlib.compress("\n".join(cont).encode("latin-1"))
    titulo_pdf = "".join(c for c in str(titulo) if ord(c) < 128 and c not in "()\\") or "Dibujo"
    cuerpos = [b"<< /Type /Catalog /Pages 2 0 R >>",
               b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
               (f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {_n(ancho * MM_PT)} {_n(alto * MM_PT)}] "
                "/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>").encode(),
               b"<< /Length %d /Filter /FlateDecode >>\nstream\n" % len(flujo) + flujo + b"\nendstream",
               b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
               f"<< /Title ({titulo_pdf}) /Producer (OmniCAD) >>".encode()]
    salida, desplazamientos = bytearray(b"%PDF-1.4\n"), []
    for i, cuerpo in enumerate(cuerpos, 1):
        desplazamientos.append(len(salida))
        salida += b"%d 0 obj\n" % i + cuerpo + b"\nendobj\n"
    xref = len(salida)
    salida += b"xref\n0 %d\n0000000000 65535 f \n" % (len(cuerpos) + 1)
    salida += b"".join(b"%010d 00000 n \n" % d for d in desplazamientos)
    salida += b"trailer\n<< /Size %d /Root 1 0 R /Info 6 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(cuerpos) + 1, xref)
    return bytes(salida)


def escribir_pdf(ruta, entidades, capas, ancho, alto, titulo="Dibujo"):
    """Escribe el PDF en `ruta`; ver `a_bytes_pdf`. Devuelve la ruta."""
    Path(ruta).write_bytes(a_bytes_pdf(entidades, capas, ancho, alto, titulo))
    return Path(ruta)

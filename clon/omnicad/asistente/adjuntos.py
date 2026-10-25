"""Adjuntos del chat del Asistente (IA-9): validar cada archivo y prepararlo como bloques neutrales. Sin Qt.

Son archivos de OTRO (AGENTS.md › Seguridad): solo las extensiones permitidas, con tope de tamaño, y nunca se
ejecutan ni se abren con programas externos. Las imágenes pasan por Pillow (se decodifican y se vuelven a escribir
como PNG, achicadas si son enormes); los PDF van tal cual como bloque `documento` (los lee la IA); SVG y DXF se leen
con los lectores de OmniCAD (`io_archivos`) solo para dibujar una vista previa.

Cada adjunto empieza con un bloque de texto que dice nombre, tipo y RUTA: con ella la IA puede llamar a
`insert_svg` / `insert_dxf`. Los bloques pesados (imagen y documento) llevan `"adjunto": nombre`: el historial no los
guarda (`historial.py`), queda solo ese texto.

Topes: PDF 20 MB (el pedido entero a la API de Claude admite 32 MB); PNG, JPG, SVG y DXF 10 MB; 10 por mensaje.
"""
import io
import json
import math
from dataclasses import dataclass
from pathlib import Path

CLASES = {".pdf": "pdf", ".png": "imagen", ".jpg": "imagen", ".jpeg": "imagen", ".svg": "svg", ".dxf": "dxf"}
NOMBRES = {"pdf": "PDF", "imagen": "imagen", "svg": "SVG", "dxf": "DXF"}
MAXIMO = 10
TOPE_PDF = 20 * 2**20
TOPE_OTROS = 10 * 2**20
TOPE_PIXELES = 50_000_000    # una imagen más grande ocupa cientos de MB al decodificarla (bomba de descompresión)
LADO_MAXIMO = 1568           # px del lado largo: más grande, la API de Claude la achica igual
TOPE_PNG = 3_500_000         # bytes: la API de Claude rechaza imágenes de más de 5 MB (en base64)
LADO_VISTA = 800             # px del lado largo de la vista previa de un SVG o DXF
TOPE_PRIMITIVAS = 20000      # la vista previa dibuja hasta estas: un DXF hostil no traba la ventana dibujando
TOPE_TEXTO_SVG = 4000        # caracteres del SVG que van como texto si no se pudo leer su geometría


class ErrorAdjunto(ValueError):
    """El archivo no se puede adjuntar; el mensaje es para la persona."""


@dataclass(eq=False)     # ✕ quita ESA ficha aunque el mismo archivo esté adjuntado dos veces
class Adjunto:
    ruta: str
    nombre: str
    clase: str       # "imagen", "pdf", "svg" o "dxf"
    bloques: list    # neutrales (proveedores/base.py): el primero es el texto que lo presenta

    @property
    def miniatura(self):
        """PNG de la imagen o de la vista previa; None (PDF, o SVG/DXF sin geometría legible)."""
        return next((b["png"] for b in self.bloques if b["tipo"] == "imagen"), None)


def _mb(n):
    return f"{n / 2**20:.1f}".replace(".", ",")


def _png(img):
    """PNG de una imagen de Pillow que entra en los topes de la API: (bytes, ancho, alto)."""
    img.thumbnail((LADO_MAXIMO, LADO_MAXIMO))
    while True:
        buf = io.BytesIO()
        img.save(buf, "PNG")
        if buf.tell() <= TOPE_PNG or max(img.size) <= 64:
            return buf.getvalue(), img.width, img.height
        img = img.resize((max(1, img.width * 3 // 4), max(1, img.height * 3 // 4)))


def _imagen(datos, nombre):
    from PIL import Image, ImageOps
    try:
        with Image.open(io.BytesIO(datos)) as img:
            ancho, alto = img.size
            if ancho * alto > TOPE_PIXELES:
                raise ErrorAdjunto(f"«{nombre}» tiene {ancho}×{alto} px: el máximo es {TOPE_PIXELES // 10**6} "
                                   "megapíxeles.")
            img.draft("RGB", (LADO_MAXIMO, LADO_MAXIMO))      # JPG: decodifica ya achicada
            img = ImageOps.exif_transpose(img)                   # fotos de celular: derechas
            if img.mode not in ("RGB", "RGBA"):
                img = img.convert("RGBA")
            return (ancho, alto), _png(img)
    except (OSError, ValueError, SyntaxError, Image.DecompressionBombError) as e:
        if isinstance(e, ErrorAdjunto):
            raise
        raise ErrorAdjunto(f"«{nombre}» no es una imagen PNG o JPG válida.") from None


def _muestras(prim):
    """Polilínea [(x, y), ...] de una primitiva de `svg.leer_svg` / `dxf.leer_dxf`; [] si no se dibuja (texto)."""
    tipo = prim[0]
    if tipo == "linea":
        return [prim[1], prim[2]]
    if tipo in ("polilinea", "curva"):
        pts = list(prim[1])
        return pts + pts[:1] if prim[2] else pts
    if tipo in ("circulo", "arco"):
        (cx, cy), r = prim[1], prim[2]
        a0, barrido = (0.0, 2 * math.pi) if tipo == "circulo" else (prim[3], (prim[4] - prim[3]) % (2 * math.pi)
                                                                    or 2 * math.pi)
        return [(cx + r * math.cos(a0 + barrido * k / 32), cy + r * math.sin(a0 + barrido * k / 32))
                for k in range(33)]
    if tipo == "bezier":
        p = prim[1]
        return [tuple(sum(c * q[i] for c, q in zip(((1 - t) ** 3, 3 * (1 - t) ** 2 * t, 3 * (1 - t) * t ** 2, t ** 3),
                                                    p, strict=True)) for i in (0, 1))
                for t in (k / 16 for k in range(17))]
    return []


def vista_previa(primitivas):
    """PNG (fondo blanco, trazo negro) del dibujo, con Y hacia arriba como en el boceto; None si no hay trazos."""
    from PIL import Image, ImageDraw
    trazos = [m for m in map(_muestras, primitivas[:TOPE_PRIMITIVAS]) if len(m) > 1]
    pts = [q for m in trazos for q in m]
    if not pts:
        return None
    xs, ys = [q[0] for q in pts], [q[1] for q in pts]
    x0, y0 = min(xs), min(ys)
    k = (LADO_VISTA - 20) / (max(max(xs) - x0, max(ys) - y0) or 1.0)
    ancho, alto = round((max(xs) - x0) * k) + 20, round((max(ys) - y0) * k) + 20
    img = Image.new("RGB", (ancho, alto), "white")
    dib = ImageDraw.Draw(img)
    for m in trazos:
        dib.line([(10 + (x - x0) * k, alto - 10 - (y - y0) * k) for x, y in m], fill=(0, 0, 0), width=2)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue(), ancho, alto


def _vectorial(ruta, nombre, clase, datos):
    """Texto (cuántas primitivas, tamaño y cómo insertarlo) y la vista previa. Un archivo dañado no falla: va
    el motivo (y, en un SVG, su texto recortado) para que la IA igual sepa qué es."""
    from ..io_archivos.boceto_archivos import caja_primitivas
    herramienta = "insert_svg" if clase == "svg" else "insert_dxf"
    try:
        if clase == "svg":
            from ..io_archivos.svg import leer_svg
            prims = leer_svg(ruta)
        else:
            from ..io_archivos.dxf import leer_dxf
            prims = leer_dxf(ruta)
        vista, caja = vista_previa(prims), caja_primitivas(prims)
    except Exception as e:  # noqa: BLE001 — archivo de otro: cualquier falla del lector se informa, no tira la app
        texto = f"No se pudo leer su geometría ({type(e).__name__}: {str(e)[:200]})."
        if clase == "svg":
            texto += " Texto del archivo (recortado):\n" + datos[:TOPE_TEXTO_SVG].decode("utf-8", "replace")
        return [{"tipo": "texto", "texto": f"Adjunto «{nombre}»: {NOMBRES[clase]} en {ruta}. {texto}"}]
    tam = f", {caja[1][0] - caja[0][0]:.1f} × {caja[1][1] - caja[0][1]:.1f} mm" if caja else ""
    recorte = f" (la vista previa dibuja las primeras {TOPE_PRIMITIVAS})" if len(prims) > TOPE_PRIMITIVAS else ""
    bloques = [{"tipo": "texto", "texto": f"Adjunto «{nombre}»: {NOMBRES[clase]} con {len(prims)} primitivas{tam}"
                                          f"{recorte}, en {ruta}. Para pasarlo a un boceto: "
                                          f"{herramienta}(path={json.dumps(str(ruta), ensure_ascii=False)})."}]
    if vista is not None:
        png, ancho, alto = vista
        bloques.append({"tipo": "imagen", "png": png, "ancho": ancho, "alto": alto, "adjunto": nombre})
    return bloques


def preparar(ruta, cantidad=0):
    """El archivo listo para el chat. `cantidad`: los adjuntos que ya tiene el mensaje (el 11.º se rechaza).
    ErrorAdjunto, con un mensaje para la persona, si no se puede adjuntar."""
    ruta = Path(ruta)
    nombre = ruta.name
    if cantidad >= MAXIMO:
        raise ErrorAdjunto(f"Máximo {MAXIMO} adjuntos por mensaje: «{nombre}» no se agregó.")
    clase = CLASES.get(ruta.suffix.lower())
    if clase is None:
        raise ErrorAdjunto(f"«{nombre}» no se puede adjuntar: solo PDF, PNG, JPG, SVG y DXF.")
    tope = TOPE_PDF if clase == "pdf" else TOPE_OTROS
    try:
        with open(ruta, "rb") as f:
            datos = f.read(tope + 1)                  # leer de más avisa si es grande sin cargarlo entero
    except OSError:
        raise ErrorAdjunto(f"No se pudo leer «{nombre}» (¿existe, es un archivo y tenés permiso?).") from None
    if len(datos) > tope:
        raise ErrorAdjunto(f"«{nombre}» pesa más de {_mb(tope)} MB, el máximo para {NOMBRES[clase]}.")
    if not datos:
        raise ErrorAdjunto(f"«{nombre}» está vacío.")
    if clase == "pdf":
        if not datos.startswith(b"%PDF-"):
            raise ErrorAdjunto(f"«{nombre}» no es un PDF válido.")
        bloques = [{"tipo": "texto", "texto": f"Adjunto «{nombre}»: PDF de {_mb(len(datos))} MB, en {ruta}."},
                   {"tipo": "documento", "pdf": datos, "nombre": nombre, "adjunto": nombre}]
    elif clase == "imagen":
        (ancho0, alto0), (png, ancho, alto) = _imagen(datos, nombre)
        achicada = f" (va achicada a {ancho}×{alto})" if (ancho, alto) != (ancho0, alto0) else ""
        bloques = [{"tipo": "texto", "texto": f"Adjunto «{nombre}»: imagen de {ancho0}×{alto0} px{achicada}, en {ruta}."},
                   {"tipo": "imagen", "png": png, "ancho": ancho, "alto": alto, "adjunto": nombre}]
    else:
        bloques = _vectorial(ruta, nombre, clase, datos)
    return Adjunto(str(ruta), nombre, clase, bloques)

# -*- coding: utf-8 -*-
"""
Herramientas del grupo "vectores": TEXTO y VECTORES del boceto: fuentes instaladas, texto con todas sus opciones,
e Insertar SVG / DXF / imagen vectorizada en un boceto (nuevo sobre un plano o en uno que ya existe).

El texto de un boceto es una curva más (`add_text`): sus letras dan perfiles para extruir; `explode_text` lo
vuelve líneas y splines fijas. Los archivos se insertan con `insert_svg`, `insert_dxf` y `trace_image`.
Unidades: mm y grados. En el boceto, y crece hacia arriba (como en Fusion).
"""
import math
from pathlib import Path
from typing import Literal

from ..io_archivos.boceto_archivos import boceto_desde_primitivas, caja_primitivas
from ..nucleo import fuentes
from ..restricciones import ErrorBoceto
from ..restricciones.boceto import Texto, _validar_opciones_texto
from ..timeline.operaciones import OpBoceto, texto_con_valores
from ..timeline.parametros import ErrorExpresion
from .errores import error
from .herramientas_boceto import (_dibujar, _exigir_finitos, _paso, boceto_activo, boceto_resuelto,
                                  estado_solver, nombre_nuevo, op_boceto, plano_o_cara)
from .registro import herramienta

_ALINEACION = {"left": "izq", "center": "centro", "right": "der"}
_ANCLAJE = {"baseline": "base", "top": "arriba", "middle": "medio", "bottom": "abajo"}
_ALINEACION_INV = {v: k for k, v in _ALINEACION.items()}
_ANCLAJE_INV = {v: k for k, v in _ANCLAJE.items()}


def _archivo(path, extensiones, que):
    ruta = Path(str(path)).expanduser()
    if not ruta.is_file():
        raise error("FILE_NOT_FOUND", f"No existe el archivo: {path}")
    if ruta.suffix.lower() not in extensiones:
        raise error("UNSUPPORTED_FILE_TYPE", f"{que} lee archivos {', '.join(extensiones)}; llegó "
                    f"{ruta.suffix or '(sin extensión)'}.")
    return ruta


# ---------------------------------------------------------------- fuentes
@herramienta("list_fonts", "vectores",
             "Lista las fuentes que puede usar el texto de boceto: todas las instaladas (sistema, usuario y "
             "carpetas sumadas con add_font_folder), TrueType, OpenType, colecciones y variables. Usá el nombre de "
             "la familia en add_text(font=...); font también acepta la ruta a un .ttf/.otf.")
def list_fonts(sesion, query: str | None = None, limit: int = 100, include_styles: bool = False):
    """
    query: texto a buscar dentro del nombre de la familia (sin distinguir mayúsculas); vacío = todas.
    limit: cuántas familias devolver como máximo (1 a 1000).
    include_styles: true para incluir los estilos de cada familia (peso, cursiva y archivo).
    """
    if not 1 <= int(limit) <= 1000:
        raise error("INVALID_ARGUMENTS", "limit va de 1 a 1000.")
    todas = fuentes.catalogo()
    q = (query or "").strip().casefold()
    por_familia = {}
    for r in todas:
        if not q or q in r["familia"].casefold():
            por_familia.setdefault(r["familia"], []).append(r)
    nombres = sorted(por_familia, key=str.casefold)
    salida = []
    for n in nombres[:int(limit)]:
        regs = por_familia[n]
        e = {"name": n, "styles_count": len(regs), "variable": any("wght" in r["ejes"] for r in regs)}
        if include_styles:
            e["styles"] = [{"style": r["estilo"], "weight": r["peso"], "italic": r["cursiva"], "file": r["ruta"]}
                           for r in sorted(regs, key=lambda r: (r["peso"], r["cursiva"]))]
        salida.append(e)
    return {"families": salida, "matching": len(nombres), "total_families": len(fuentes.familias()),
            "total_fonts": len(todas), "folders": [str(c) for c in fuentes.carpetas_de_fuentes()]}


@herramienta("add_font_folder", "vectores",
             "Suma una carpeta de fuentes (.ttf, .otf, .ttc) a las que ve OmniCAD en esta sesión. Para que "
             "quede fija, definí la variable de entorno OMNICAD_FUENTES con la carpeta.")
def add_font_folder(sesion, path: str):
    """
    path: carpeta con las fuentes (se busca también en sus subcarpetas).
    """
    try:
        sumadas = fuentes.agregar_carpeta(path)
    except fuentes.ErrorFuente as e:
        raise error("FILE_NOT_FOUND", str(e)) from e
    return {"added_fonts": sumadas, "total_fonts": len(fuentes.catalogo()), "total_families": len(fuentes.familias())}


# ---------------------------------------------------------------- texto
def _texto_de(b, entity):
    c = b.curvas.get(entity)
    if not isinstance(c, Texto):
        existe = "no es un texto" if c is not None else "no existe"
        raise error("ENTITY_NOT_FOUND", f"La entidad {entity} {existe} en el boceto.",
                    "get_sketch lista las curvas; los textos tienen type 'text'.")
    return c


def _opciones_camino(path_entity, path_side, path_position, path_offset, fit_path):
    """Opciones del texto en curva (solo las que llegaron). path_entity 0 = quitar el camino."""
    if path_side is not None and path_side not in ("left", "right"):
        raise error("INVALID_ARGUMENTS", "path_side es left o right.")
    if path_position is not None and not (math.isfinite(path_position) and 0.0 <= path_position <= 1.0):
        raise error("INVALID_ARGUMENTS", "path_position va de 0 a 1 (fracción del largo de la curva).")
    if path_offset is not None and not math.isfinite(path_offset):
        raise error("INVALID_ARGUMENTS", "path_offset tiene que ser un número finito (mm).")
    op = {}
    if path_entity is not None:
        op["camino"] = None if int(path_entity) == 0 else int(path_entity)
    if path_side is not None:
        op["camino_lado"] = "izq" if path_side == "left" else "der"
    if path_position is not None:
        op["camino_pos"] = float(path_position)
    if path_offset is not None:
        op["camino_desfase"] = float(path_offset)
    if fit_path is not None:
        op["camino_ajustar"] = bool(fit_path)
    return op


def _opciones_texto(letter_spacing, line_spacing, align, anchor, box_width, flip_h, flip_v):
    if align is not None and align not in _ALINEACION:
        raise error("INVALID_ARGUMENTS", "align es left, center o right.")
    if anchor is not None and anchor not in _ANCLAJE:
        raise error("INVALID_ARGUMENTS", "anchor es baseline, top, middle o bottom.")
    op = {}
    for clave, valor in (("espaciado", letter_spacing), ("interlineado", line_spacing), ("ancho_caja", box_width),
                         ("voltear_h", flip_h), ("voltear_v", flip_v)):
        if valor is not None:
            op[clave] = valor
    if align is not None:
        op["alineacion"] = _ALINEACION[align]
    if anchor is not None:
        op["ancla_v"] = _ANCLAJE[anchor]
    return op


def _verificar_fuente(font, bold, italic):
    if fuentes.buscar_fuente(font, bold, italic) is None:
        cercanas = [f for f in fuentes.familias() if str(font).casefold() in f.casefold()][:5]
        raise error("INVALID_ARGUMENTS", f"No se encontró la fuente «{font}».",
                    *([f"Parecidas: {', '.join(cercanas)}."] if cercanas else []),
                    "list_fonts(query=...) busca por nombre; font también acepta la ruta a un .ttf/.otf.")


@herramienta("add_text", "vectores",
             "Escribe un texto en el boceto (un paso de deshacer). Sus letras forman perfiles que se pueden extruir "
             "o cortar. (x, y) es el ancla: por defecto la esquina izquierda de la línea base. Varias líneas con "
             "'\\n'; con box_width > 0 las líneas se parten en palabras. Fuente: cualquier familia instalada "
             "(list_fonts) o la ruta a un .ttf/.otf. TEXTO EN CURVA: con path_entity (una línea, arco, círculo, "
             "elipse o spline del boceto) las letras siguen esa curva y (x, y, angle) no se usan; para un círculo, "
             "texto arriba por fuera = path_side right + path_position 0.25, abajo por dentro = left + 0.75.",
             modifica=True)
def add_text(sesion, text: str, x: float = 0.0, y: float = 0.0, height: float = 5.0, angle: float = 0.0,
             font: str = "Arial", bold: bool = False, italic: bool = False, letter_spacing: float = 0.0,
             line_spacing: float = 1.0, align: Literal["left", "center", "right"] | None = None,
             anchor: Literal["baseline", "top", "middle", "bottom"] = "baseline", box_width: float = 0.0,
             flip_h: bool = False, flip_v: bool = False, path_entity: int | None = None,
             path_side: Literal["left", "right"] = "left", path_position: float = 0.5, path_offset: float = 0.0,
             fit_path: bool = False, sketch: str | None = None):
    """
    text: el texto; '\\n' separa líneas. Con {parámetro} o {expresión:formato} (p. ej. 'Ancho {ancho:.1f} mm') muestra el valor del parámetro y se actualiza solo.
    x: x del ancla (mm).
    y: y del ancla (mm).
    height: tamaño de la fuente en mm (positivo).
    angle: giro del texto en grados alrededor del ancla (antihorario).
    font: familia (Arial, Segoe UI…) o ruta a un archivo de fuente.
    bold: negrita (el peso más cercano a 700 de la familia).
    italic: cursiva.
    letter_spacing: mm extra entre letras (negativo junta).
    line_spacing: factor del salto de línea de la fuente (1 = el de la fuente).
    align: alineación de cada línea dentro de la caja (left, center o right); en curva, qué parte del texto cae en path_position. Vacío = left (recto) o center (en curva).
    anchor: qué parte del bloque cae sobre (x, y): baseline (línea base de la primera), top, middle o bottom.
    box_width: ancho de la caja en mm; 0 = sin caja (el bloque mide lo que mide su línea más larga).
    flip_h: espejo horizontal del texto dentro de su bloque.
    flip_v: espejo vertical del texto dentro de su bloque.
    path_entity: id de la curva (get_sketch) que sigue el texto; vacío = texto recto.
    path_side: left = letras a la izquierda del sentido de la curva; right = la recorre al revés (letras del otro lado, se siguen leyendo derechas).
    path_position: fracción 0-1 del largo de la curva (en su sentido propio) donde cae el texto; un círculo empieza a la derecha y gira antihorario (0.25 = arriba).
    path_offset: mm entre la curva y la línea base (positivo = hacia el lado de las letras).
    fit_path: true reparte el texto en todo el largo de la curva.
    sketch: id o nombre del boceto; vacío = el último boceto del timeline.
    """
    _exigir_finitos({"x": x, "y": y, "height": height, "angle": angle})
    texto = str(text).replace("\\n", "\n")
    _verificar_fuente(font, bold, italic)
    if align is None:
        align = "center" if path_entity else "left"
    op = _opciones_texto(letter_spacing, line_spacing, align, anchor, box_width, flip_h, flip_v)
    if path_entity:
        op |= _opciones_camino(path_entity, path_side, path_position, path_offset, fit_path)
    return _dibujar(sesion, sketch, lambda b: b.agregar_texto((x, y), texto, altura=height, angulo=angle,
                                                              fuente=font, negrita=bold, cursiva=italic, **op))


@herramienta("edit_text", "vectores",
             "Cambia un texto existente del boceto (un paso de deshacer): lo que no se pasa queda como estaba. "
             "Los perfiles de las letras se recalculan; lo que dependa de ellos (extrusiones) sigue al texto.",
             modifica=True)
def edit_text(sesion, entity: int, text: str | None = None, x: float | None = None, y: float | None = None,
              height: float | None = None, angle: float | None = None, font: str | None = None,
              bold: bool | None = None, italic: bool | None = None, letter_spacing: float | None = None,
              line_spacing: float | None = None, align: Literal["left", "center", "right"] | None = None,
              anchor: Literal["baseline", "top", "middle", "bottom"] | None = None, box_width: float | None = None,
              flip_h: bool | None = None, flip_v: bool | None = None, path_entity: int | None = None,
              path_side: Literal["left", "right"] | None = None, path_position: float | None = None,
              path_offset: float | None = None, fit_path: bool | None = None, sketch: str | None = None):
    """
    entity: id de la curva de texto (get_sketch).
    text: texto nuevo ('\\n' separa líneas; {parámetro} muestra su valor).
    x: x nueva del ancla (mm).
    y: y nueva del ancla (mm).
    height: tamaño nuevo de la fuente en mm.
    angle: giro nuevo en grados.
    font: familia o ruta de la fuente nueva.
    bold: negrita.
    italic: cursiva.
    letter_spacing: mm extra entre letras.
    line_spacing: factor del salto de línea.
    align: left, center o right.
    anchor: baseline, top, middle o bottom.
    box_width: ancho de la caja en mm (0 = sin caja).
    flip_h: espejo horizontal.
    flip_v: espejo vertical.
    path_entity: id de la curva que sigue el texto; 0 = quitar la curva (texto recto otra vez).
    path_side: left o right (lado de la curva).
    path_position: fracción 0-1 del largo de la curva.
    path_offset: mm entre la curva y la línea base.
    fit_path: repartir el texto en todo el largo.
    sketch: id o nombre del boceto; vacío = el último boceto del timeline.
    """
    _exigir_finitos({k: v for k, v in (("x", x), ("y", y), ("height", height), ("angle", angle)) if v is not None})
    op = _opciones_texto(letter_spacing, line_spacing, align, anchor, box_width, flip_h, flip_v)
    op |= _opciones_camino(path_entity, path_side, path_position, path_offset, fit_path)

    def cambiar(b):
        t = _texto_de(b, entity)
        nuevo_texto = t.texto if text is None else str(text).replace("\\n", "\n")
        if not nuevo_texto.strip():
            raise ErrorBoceto("El texto está vacío.")
        if height is not None and not 0 < height < math.inf:
            raise ErrorBoceto("La altura del texto debe ser positiva.")
        _f, _b, _i = (t.fuente if font is None else font), (t.negrita if bold is None else bold), \
            (t.cursiva if italic is None else italic)
        _verificar_fuente(_f, _b, _i)
        _validar_opciones_texto(op)
        if op.get("camino") is not None:
            b._validar_camino(op["camino"])
        t.texto, t.fuente, t.negrita, t.cursiva = nuevo_texto, _f, _b, _i
        if height is not None:
            t.altura = float(height)
        if angle is not None:
            t.angulo = float(angle)
        for k, v in op.items():
            if k in ("espaciado", "interlineado", "ancho_caja", "camino_pos", "camino_desfase"):
                v = float(v)
            elif k.startswith("voltear") or k == "camino_ajustar":
                v = bool(v)
            setattr(t, k, v)
        if x is not None or y is not None:
            px, py = b.coords(t.punto)
            b.mover_punto(t.punto, px if x is None else x, py if y is None else y) \
                if hasattr(b, "mover_punto") else _mover(b, t.punto, px if x is None else x, py if y is None else y)
    return _dibujar(sesion, sketch, cambiar)


def _mover(b, pid, x, y):
    p = b.puntos[pid]
    p.x, p.y = float(x), float(y)


@herramienta("explode_text", "vectores",
             "Desglosa un texto del boceto (Fusion: Explode Text): el texto pasa a ser líneas y splines fijas, que "
             "se pueden editar curva por curva. Ya no se puede cambiar la fuente ni el contenido.", modifica=True)
def explode_text(sesion, entity: int, sketch: str | None = None):
    """
    entity: id de la curva de texto (get_sketch).
    sketch: id o nombre del boceto; vacío = el último boceto del timeline.
    """
    def desglosar(b):
        t = _texto_de(b, entity)
        if "{" in t.texto:                      # el desglose congela el texto con los valores de ahora
            try:
                t.texto = texto_con_valores(t.texto, sesion.doc.parametros.valores())
            except ErrorExpresion as e:
                raise ErrorBoceto(f"No se pudo calcular el texto: {e}") from e
        b.desglosar_texto(entity)
    return _dibujar(sesion, sketch, desglosar)


# ---------------------------------------------------------------- insertar archivos 2D
def _insertar(sesion, prims, plane, sketch, name, body, **transformacion):
    """Agrega las primitivas a un boceto nuevo sobre `plane` o al boceto `sketch` (por defecto, el último)."""
    doc = sesion.doc
    try:
        if plane is not None and str(plane).strip():
            b = boceto_desde_primitivas(prims, **transformacion)
            ref, marco, cara, ref_cara = plano_o_cara(sesion, plane, body)
            nombre = name.strip() if name and name.strip() else nombre_nuevo(doc, "Boceto", OpBoceto)
            op = OpBoceto(doc.nuevo_id(), nombre, plano=ref, marco=marco, cara=ref_cara, boceto=b)
            doc.agregar(op)
            nuevas = len(b.curvas)
        else:
            op0 = op_boceto(sesion, sketch)
            nueva = op0.copia()
            antes = len(nueva.boceto.curvas)
            boceto_desde_primitivas(prims, destino=nueva.boceto, **transformacion)
            nuevas = len(nueva.boceto.curvas) - antes
            doc.reemplazar(op0.id, nueva)
            op = nueva
    except ValueError as e:
        raise error("INVALID_GEOMETRY", str(e)) from e
    br = boceto_resuelto(sesion, op)
    estado, gdl = estado_solver(br)
    caja = caja_primitivas(prims)
    return {"sketch": _paso(op), "entities_added": nuevas, "profiles": None if br is None else len(br.perfiles),
            "dof": gdl, "status": estado,
            "source_size_mm": None if caja is None else [round(caja[1][0] - caja[0][0], 4),
                                                         round(caja[1][1] - caja[0][1], 4)]}


def _transformacion(scale, width, x, y, angle, flip_h, flip_v):
    _exigir_finitos({"scale": scale, "x": x, "y": y, "angle": angle})
    if width is not None and not (math.isfinite(width) and width > 0):
        raise error("INVALID_ARGUMENTS", "width tiene que ser un número positivo (mm).")
    if not scale > 0:
        raise error("INVALID_ARGUMENTS", "scale tiene que ser positivo.")
    return {"escala": scale, "ancho": width, "desplazamiento": (x, y), "angulo": angle,
            "voltear_h": flip_h, "voltear_v": flip_v}


@herramienta("inspect_svg", "vectores",
             "Mira un archivo SVG antes de insertarlo: tamaño en mm, y qué capas (grupos) y colores trae, con la "
             "cantidad de trazos de cada uno. Sirve para elegir layers o colors de insert_svg.")
def inspect_svg(sesion, path: str):
    """
    path: ruta del archivo .svg.
    """
    from ..io_archivos.svg import ErrorSVG, leer_svg, listar_capas_svg
    ruta = _archivo(path, (".svg",), "inspect_svg")
    try:
        info = listar_capas_svg(ruta)
        caja = caja_primitivas(leer_svg(ruta))
    except ErrorSVG as e:
        raise error("IMPORT_FAILED", str(e)) from e
    return {"layers": info["capas"], "colors": info["colores"], "primitives": info["total"],
            "size_mm": None if caja is None else [round(caja[1][0] - caja[0][0], 4), round(caja[1][1] - caja[0][1], 4)]}


@herramienta("insert_svg", "vectores",
             "Inserta un dibujo SVG en un boceto (Fusion: Insertar > Insertar SVG) y lo deja como curvas editables "
             "(las curvas Bézier pasan a splines de control; círculos y arcos quedan exactos). Con plane crea un "
             "boceto nuevo sobre ese plano o cara; sin plane suma el dibujo al boceto sketch (por defecto el "
             "último). Orden: voltear, escalar (o ajustar a width), girar y mover. Con layers o colors importa solo "
             "esa parte del archivo (inspect_svg dice cuáles hay).", modifica=True)
def insert_svg(sesion, path: str, plane: str | None = None, sketch: str | None = None, scale: float = 1.0,
               width: float | None = None, x: float = 0.0, y: float = 0.0, angle: float = 0.0,
               flip_h: bool = False, flip_v: bool = False, layers: list[str] | None = None,
               colors: list[str] | None = None, name: str | None = None, body: str | None = None):
    """
    path: ruta del archivo .svg.
    plane: "XY", "XZ", "YZ", un plano de construcción o una cara plana: crea un boceto nuevo ahí. Vacío = usar sketch.
    sketch: id o nombre del boceto donde sumar el dibujo (sin plane); vacío = el último boceto.
    scale: factor de escala sobre el tamaño del archivo (1 = tal cual, en mm reales).
    width: ancho final del dibujo en mm (pisa a scale); el alto sigue la proporción.
    x: desplazamiento en X del boceto (mm), después de escalar y girar.
    y: desplazamiento en Y del boceto (mm).
    angle: giro en grados (antihorario) alrededor del origen del boceto.
    flip_h: espejo horizontal alrededor del centro del dibujo.
    flip_v: espejo vertical alrededor del centro del dibujo.
    layers: solo los grupos con estos ids o etiquetas (inkscape:label); vacío = todo.
    colors: solo los trazos o rellenos de estos colores, como '#rrggbb'; vacío = todo.
    name: nombre del boceto nuevo (con plane); vacío = "BocetoN".
    body: cuerpo donde se evalúa el selector de cara de plane.
    """
    from ..io_archivos.svg import ErrorSVG, leer_svg
    ruta = _archivo(path, (".svg",), "insert_svg")
    transf = _transformacion(scale, width, x, y, angle, flip_h, flip_v)
    try:
        prims = leer_svg(ruta, capas=layers, colores=colors)
    except ErrorSVG as e:
        raise error("IMPORT_FAILED", str(e)) from e
    return _insertar(sesion, prims, plane, sketch, name, body, **transf)


@herramienta("insert_dxf", "vectores",
             "Inserta la geometría 2D de un archivo DXF en un boceto (Fusion: Insertar > Insertar DXF): líneas, "
             "arcos, círculos, polilíneas, splines y textos. Mismo manejo de plane / sketch / transformación que "
             "insert_svg. Las unidades del DXF se pasan a mm.", modifica=True)
def insert_dxf(sesion, path: str, plane: str | None = None, sketch: str | None = None, scale: float = 1.0,
               width: float | None = None, x: float = 0.0, y: float = 0.0, angle: float = 0.0,
               flip_h: bool = False, flip_v: bool = False, name: str | None = None, body: str | None = None):
    """
    path: ruta del archivo .dxf.
    plane: "XY", "XZ", "YZ", un plano de construcción o una cara plana: crea un boceto nuevo ahí. Vacío = usar sketch.
    sketch: id o nombre del boceto donde sumar el dibujo (sin plane); vacío = el último boceto.
    scale: factor de escala (1 = tal cual).
    width: ancho final del dibujo en mm (pisa a scale).
    x: desplazamiento en X (mm).
    y: desplazamiento en Y (mm).
    angle: giro en grados alrededor del origen del boceto.
    flip_h: espejo horizontal alrededor del centro del dibujo.
    flip_v: espejo vertical alrededor del centro del dibujo.
    name: nombre del boceto nuevo (con plane).
    body: cuerpo donde se evalúa el selector de cara de plane.
    """
    from ..io_archivos.dxf import ErrorDXF, leer_dxf
    ruta = _archivo(path, (".dxf",), "insert_dxf")
    transf = _transformacion(scale, width, x, y, angle, flip_h, flip_v)
    try:
        prims = leer_dxf(ruta)
    except (ErrorDXF, ValueError) as e:
        raise error("IMPORT_FAILED", str(e)) from e
    return _insertar(sesion, prims, plane, sketch, name, body, **transf)


@herramienta("trace_image", "vectores",
             "Vectoriza una imagen (PNG, JPG, BMP, GIF, WEBP) y la inserta en un boceto como contornos cerrados "
             "(logos, siluetas, dibujos en blanco y negro). Mismo manejo de plane / sketch / transformación que "
             "insert_svg. Los agujeros salen como contornos aparte (forman perfiles anillo). Con curves=true cada "
             "contorno es UNA spline suave; con false, una polilínea simplificada. El tamaño sale de width (mm) o, "
             "si falta, de dpi.", modifica=True)
def trace_image(sesion, path: str, plane: str | None = None, sketch: str | None = None, width: float | None = None,
                dpi: float = 96.0, threshold: float | None = None, invert: bool = False, smoothing: float = 1.0,
                tolerance: float = 0.5, min_area: float = 4.0,
                channel: Literal["auto", "luminance", "alpha"] = "auto", curves: bool = False, x: float = 0.0,
                y: float = 0.0, angle: float = 0.0, flip_h: bool = False, flip_v: bool = False,
                name: str | None = None, body: str | None = None):
    """
    path: ruta de la imagen.
    plane: "XY", "XZ", "YZ", un plano de construcción o una cara plana: crea un boceto nuevo ahí. Vacío = usar sketch.
    sketch: id o nombre del boceto donde sumar el dibujo (sin plane); vacío = el último boceto.
    width: ancho final en mm; vacío = el ancho de la imagen en píxeles según dpi.
    dpi: píxeles por pulgada para el tamaño cuando no hay width.
    threshold: umbral de la tinta (1 a 254); vacío = automático (Otsu).
    invert: true si la tinta es lo claro (letras blancas sobre fondo oscuro).
    smoothing: suavizado previo en píxeles (0 = ninguno); quita el ruido y el dentado.
    tolerance: desvío máximo al simplificar los contornos, en píxeles (más alto = menos puntos).
    min_area: los contornos de menos píxeles² se descartan como ruido.
    channel: auto (usa la transparencia si la hay), luminance o alpha.
    curves: true = una spline suave por contorno; false = polilínea.
    x: desplazamiento en X (mm).
    y: desplazamiento en Y (mm).
    angle: giro en grados alrededor del origen del boceto.
    flip_h: espejo horizontal alrededor del centro del dibujo.
    flip_v: espejo vertical alrededor del centro del dibujo.
    name: nombre del boceto nuevo (con plane).
    body: cuerpo donde se evalúa el selector de cara de plane.
    """
    from ..io_archivos.vectorizar import ErrorVectorizar, vectorizar_imagen
    ruta = _archivo(path, (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp", ".tif", ".tiff"), "trace_image")
    if not (math.isfinite(dpi) and dpi > 0):
        raise error("INVALID_ARGUMENTS", "dpi tiene que ser positivo.")
    transf = _transformacion(25.4 / dpi, width, x, y, angle, flip_h, flip_v)
    canal = {"auto": "auto", "luminance": "luminosidad", "alpha": "alfa"}[channel]
    try:
        prims = vectorizar_imagen(ruta, umbral=threshold, invertir=invert, suavizado=smoothing, tolerancia=tolerance,
                                  area_minima=min_area, canal=canal, curvas=curves)
    except ErrorVectorizar as e:
        raise error("IMPORT_FAILED", str(e)) from e
    return _insertar(sesion, prims, plane, sketch, name, body, **transf)


@herramienta("export_sketch", "vectores",
             "Guarda un boceto como archivo 2D para corte láser, vinilo o CNC (Fusion: Guardar como DXF); el formato "
             "sale de la extensión: .dxf o .svg. Las letras del texto salen como curvas. En SVG el dibujo queda con "
             "su esquina inferior izquierda en el origen y en milímetros reales; la geometría de construcción va en "
             "un grupo aparte (DXF: capa CONSTRUCCION) y solo si include_construction.")
def export_sketch(sesion, path: str, sketch: str | None = None, include_construction: bool = False,
                  overwrite: bool = False):
    """
    path: ruta del archivo a escribir (.dxf o .svg).
    sketch: id o nombre del boceto; vacío = el último boceto del timeline.
    include_construction: true para incluir las curvas de construcción.
    overwrite: true para reemplazar el archivo si ya existe.
    """
    from ..io_archivos.boceto_archivos import primitivas_dxf_de_boceto
    from ..io_archivos.dxf import ErrorDXF, escribir_dxf
    from ..io_archivos.svg import ErrorSVG, escribir_svg
    ruta = Path(str(path)).expanduser()
    ext = ruta.suffix.lower()
    if ext not in (".dxf", ".svg"):
        raise error("INVALID_FORMAT", f"export_sketch escribe .dxf o .svg; llegó {ext or '(sin extensión)'}.")
    op, br = boceto_activo(sesion, sketch)
    if ruta.exists() and not overwrite:
        raise error("FILE_EXISTS", f"Ya existe el archivo: {ruta}")
    if not ruta.parent.is_dir():
        raise error("FILE_NOT_FOUND", f"No existe la carpeta: {ruta.parent}")
    prims = br.boceto.geometria(incluir_construccion=include_construction)
    if not prims:
        raise error("NOTHING_TO_EXPORT", f"El boceto «{op.nombre}» no tiene geometría para guardar.")
    try:
        if ext == ".dxf":
            escribir_dxf(ruta, primitivas_dxf_de_boceto(br.boceto, incluir_construccion=include_construction),
                         capas={"CONSTRUCCION": {"color": 30, "tipo": "trazos"}})
            ancho = alto = None
        else:
            construccion = [c.id for c in br.boceto.curvas.values() if c.construccion]
            ancho, alto = escribir_svg(ruta, prims, construccion)
    except (ErrorDXF, ErrorSVG) as e:
        raise error("FILE_ERROR", str(e)) from e
    except PermissionError as e:
        raise error("PERMISSION_DENIED", str(e)) from e
    except OSError as e:
        raise error("FILE_ERROR", str(e)) from e
    return {"path": str(ruta.resolve()), "format": ext.lstrip("."), "sketch": _paso(op), "primitives": len(prims),
            "size_mm": None if ancho is None else [round(ancho, 4), round(alto, 4)],
            "size_bytes": ruta.stat().st_size}


# ---------------------------------------------------------------- operaciones con perfiles (fase 6)
def _perfiles_y_boceto(sesion, sketch, profiles, tool_profiles):
    from .herramientas_boceto import seleccionar_perfiles
    op, br = boceto_activo(sesion, sketch)
    a = seleccionar_perfiles(br, op, profiles)
    b_ = seleccionar_perfiles(br, op, tool_profiles) if tool_profiles is not None else []
    return op, br, a, b_


def _volcar(sesion, op, br, formas, borrar, area):
    from ..io_archivos.boceto_archivos import agregar_geometria
    from ..nucleo import vectores
    prims = vectores.primitivas_de_formas(formas, br.plano)
    if not prims:
        raise error("INVALID_GEOMETRY", "La operación no dejó curvas.")
    nueva = op.copia()
    b = nueva.boceto
    borradas = 0
    for cid in sorted(borrar):
        if cid in b.curvas:
            b.eliminar(cid)
            borradas += 1
    try:
        ids = agregar_geometria(b, prims)
    except ErrorBoceto as e:
        raise error("INVALID_GEOMETRY", str(e)) from e
    sesion.doc.reemplazar(op.id, nueva)
    brn = boceto_resuelto(sesion, nueva)
    estado, gdl = estado_solver(brn)
    return {"sketch": _paso(nueva), "entities_added": len(ids), "entities_deleted": borradas,
            "result_area": None if area is None else round(area, 4),
            "profiles": None if brn is None else len(brn.perfiles), "dof": gdl, "status": estado}


@herramienta("combine_profiles", "vectores",
             "Une, resta o interseca perfiles (regiones cerradas) del boceto y deja el contorno resultante como "
             "curvas nuevas, sin las líneas internas: juntar letras que se pisan, restar un marco, quedarse con lo "
             "común. Con keep_original=false (por defecto) se borran las curvas de los perfiles usados (un texto "
             "usado se borra entero). Índices de perfil: get_sketch.", modifica=True)
def combine_profiles(sesion, profiles: list[int] | str, operation: Literal["union", "subtract", "intersect"] = "union",
                     tool_profiles: list[int] | None = None, keep_original: bool = False, sketch: str | None = None):
    """
    profiles: índices de los perfiles (o "all"); en subtract e intersect son los que se cortan.
    operation: union (todo junto), subtract (profiles menos tool_profiles) o intersect (lo común).
    tool_profiles: índices de los perfiles herramienta (subtract e intersect); en union se suman a profiles.
    keep_original: true para dejar las curvas originales además del resultado.
    sketch: id o nombre del boceto; vacío = el último boceto del timeline.
    """
    from ..nucleo import geometria as geo
    from ..nucleo import vectores
    op, br, a, b_ = _perfiles_y_boceto(sesion, sketch, profiles, tool_profiles)
    oper = {"union": "union", "subtract": "resta", "intersect": "interseccion"}[operation]
    if oper != "union" and not b_:
        raise error("INVALID_ARGUMENTS", f"{operation} necesita tool_profiles.")
    try:
        forma = vectores.booleana_caras([p.cara for p in a], [p.cara for p in b_], oper)
    except geo.ErrorGeometria as e:
        raise error("OPERATION_FAILED", str(e)) from e
    area = sum(geo.area(c) for c in geo.caras(forma))
    borrar = set() if keep_original else set().union(*(p.firma for p in a + b_))
    return _volcar(sesion, op, br, [forma], borrar, area)


@herramienta("offset_profiles", "vectores",
             "Desfase (offset) del contorno de perfiles del boceto, con agujeros incluidos: distance > 0 agranda, < 0 "
             "achica. Sirve con cualquier curva (letras, splines de un SVG), no solo líneas y arcos encadenados. "
             "Esquinas redondas o vivas. Las curvas originales quedan (keep_original=true por defecto).",
             modifica=True)
def offset_profiles(sesion, profiles: list[int] | str, distance: float,
                    corners: Literal["round", "sharp"] = "round", keep_original: bool = True,
                    sketch: str | None = None):
    """
    profiles: índices de los perfiles (get_sketch) o "all".
    distance: mm; positivo agranda la región, negativo la achica.
    corners: round (arcos en las esquinas) o sharp (las esquinas se prolongan hasta cortarse).
    keep_original: false para borrar las curvas de los perfiles usados.
    sketch: id o nombre del boceto; vacío = el último boceto del timeline.
    """
    from ..nucleo import geometria as geo
    from ..nucleo import vectores
    if not math.isfinite(distance) or abs(distance) < 1e-9:
        raise error("INVALID_ARGUMENTS", "distance tiene que ser un número distinto de cero (mm).")
    op, br, a, _ = _perfiles_y_boceto(sesion, sketch, profiles, None)
    try:
        formas = vectores.desfase_caras([p.cara for p in a], distance, "redondas" if corners == "round" else "vivas")
    except geo.ErrorGeometria as e:
        raise error("OPERATION_FAILED", str(e)) from e
    borrar = set() if keep_original else set().union(*(p.firma for p in a))
    return _volcar(sesion, op, br, formas, borrar, None)


@herramienta("transform_sketch", "vectores",
             "Mueve, gira, escala y/o espeja curvas de un boceto (un paso de deshacer): lo importado de un SVG, un "
             "texto, una selección. Orden: espejo, escala, giro y desplazamiento, todo alrededor del centro (por "
             "defecto el de la caja de la selección). Con copy=true trabaja sobre una copia. Las cotas de largo de "
             "lo escalado se multiplican por el factor.", modifica=True)
def transform_sketch(sesion, entities: list[int] | None = None, dx: float = 0.0, dy: float = 0.0, angle: float = 0.0,
                     scale: float = 1.0, mirror: Literal["none", "horizontal", "vertical"] = "none",
                     center_x: float | None = None, center_y: float | None = None, copy: bool = False,
                     sketch: str | None = None):
    """
    entities: ids de curvas o puntos (get_sketch); vacío = todas las curvas del boceto.
    dx: desplazamiento en X (mm).
    dy: desplazamiento en Y (mm).
    angle: giro en grados (antihorario) alrededor del centro.
    scale: factor de escala (positivo; 1 = igual).
    mirror: horizontal (izquierda ↔ derecha), vertical (arriba ↔ abajo) o none.
    center_x: x del centro de giro, escala y espejo; vacío = centro de la caja de la selección.
    center_y: y del centro; vacío = centro de la caja de la selección.
    copy: true para transformar una copia y dejar el original.
    sketch: id o nombre del boceto; vacío = el último boceto del timeline.
    """
    from ..restricciones.boceto import puntos_primitiva
    _exigir_finitos({"dx": dx, "dy": dy, "angle": angle, "scale": scale})
    if not scale > 0:
        raise error("INVALID_ARGUMENTS", "scale tiene que ser positivo.")
    avisos = []

    def cambiar(b):
        ids = list(entities) if entities else list(b.curvas)
        faltan = [i for i in ids if i not in b.curvas and i not in b.puntos]
        if faltan:
            raise error("ENTITY_NOT_FOUND", f"No existen en el boceto: {faltan}.")
        if not ids:
            raise ErrorBoceto("El boceto no tiene curvas para transformar.")
        cx, cy = center_x, center_y
        if cx is None or cy is None:
            pts = [q for i in ids for prim in (b.primitivas(i) if i in b.curvas else [("punto",)])
                   for q in (puntos_primitiva(prim, 32) if prim[0] != "punto" else [b.coords(i)])]
            xs, ys = [q[0] for q in pts], [q[1] for q in pts]
            cx = (min(xs) + max(xs)) / 2 if cx is None else cx
            cy = (min(ys) + max(ys)) / 2 if cy is None else cy
        if copy:
            ids = b.transformar(ids, copiar=True)
            ids = [i for i in ids if i in b.curvas or i in b.puntos]
        if mirror != "none":
            _hechos, textos = b.reflejar(ids, (cx, cy), horizontal=(mirror == "horizontal"))
            if textos:
                avisos.append(f"Los textos {textos} no se espejan (usá flip_h / flip_v de edit_text).")
        if abs(scale - 1.0) > 1e-12:
            b.escalar(ids, (cx, cy), scale)
        if angle or dx or dy:
            b.transformar(ids, dx=dx, dy=dy, angulo=angle, centro=(cx, cy))
    r = _dibujar(sesion, sketch, cambiar)
    for a in avisos:
        sesion.avisar(a)
    return r


# ---------------------------------------------------------------- limpiar y editar nodos
@herramienta("clean_sketch", "vectores",
             "Limpia geometría importada (SVG, DXF, imagen vectorizada): borra curvas repetidas, une extremos sueltos "
             "a menos de tolerance mm (cierra huecos para que los contornos formen perfiles) y junta líneas seguidas "
             "alineadas en una sola. No toca nada que tenga restricciones o cotas.", modifica=True)
def clean_sketch(sesion, tolerance: float = 0.01, remove_duplicates: bool = True, close_gaps: bool = True,
                 merge_collinear: bool = True, sketch: str | None = None):
    """
    tolerance: distancia máxima en mm para considerar dos puntos iguales o tres puntos alineados.
    remove_duplicates: borrar curvas repetidas.
    close_gaps: unir extremos sueltos cercanos.
    merge_collinear: juntar líneas seguidas alineadas.
    sketch: id o nombre del boceto; vacío = el último boceto del timeline.
    """
    if not (math.isfinite(tolerance) and tolerance > 0):
        raise error("INVALID_ARGUMENTS", "tolerance tiene que ser positiva (mm).")
    hecho = {}

    def limpiar(b):
        hecho.update(b.limpiar(tolerance, remove_duplicates, close_gaps, merge_collinear))
    r = _dibujar(sesion, sketch, limpiar)
    r.pop("entities", None)
    r.update(duplicates_removed=hecho["duplicadas"], gaps_closed=hecho["huecos"],
             lines_merged=hecho["colineales"])
    return r


@herramienta("move_sketch_point", "vectores",
             "Mueve un punto del boceto (edición de nodos): extremos de líneas y arcos, puntos de control de splines "
             "(las curvas Bézier de un SVG), centros. El solver vuelve a cumplir las restricciones que tenga.",
             modifica=True)
def move_sketch_point(sesion, point: int, x: float, y: float, sketch: str | None = None):
    """
    point: id del punto (get_sketch lista los puntos de cada curva en 'points').
    x: x nueva (mm).
    y: y nueva (mm).
    sketch: id o nombre del boceto; vacío = el último boceto del timeline.
    """
    _exigir_finitos({"x": x, "y": y})

    def mover(b):
        if point not in b.puntos:
            raise error("ENTITY_NOT_FOUND", f"No existe el punto {point} en el boceto.")
        if point in b.puntos_fijos():
            raise ErrorBoceto(f"El punto {point} está fijo (o es proyectado): no se puede mover.")
        _mover(b, point, x, y)
    return _dibujar(sesion, sketch, mover)


@herramienta("delete_sketch_entities", "vectores",
             "Borra curvas, puntos, restricciones o cotas del boceto (un paso de deshacer); lo que dependa de ellos se "
             "borra también (un punto se lleva sus curvas).", modifica=True)
def delete_sketch_entities(sesion, entities: list[int], sketch: str | None = None):
    """
    entities: ids a borrar (get_sketch).
    sketch: id o nombre del boceto; vacío = el último boceto del timeline.
    """
    if not entities:
        raise error("INVALID_ARGUMENTS", "entities está vacía.")
    borradas = []

    def borrar(b):
        faltan = [i for i in entities if i not in b.curvas and i not in b.puntos and i not in b.restricciones
                  and i not in b.cotas]
        if faltan:
            raise error("ENTITY_NOT_FOUND", f"No existen en el boceto: {faltan}.")
        for i in entities:
            if i in b.curvas or i in b.puntos or i in b.restricciones or i in b.cotas:
                b.eliminar(i)
                borradas.append(i)
    r = _dibujar(sesion, sketch, borrar)
    r["deleted"] = borradas
    return r

# -*- coding: utf-8 -*-
"""
Textos del servidor: `instructions`, guías como resources y prompts.

La fuente única de la guía son los .md de `api/guia/`: acá no se copia su texto, solo se leen. Los prompts
nombran herramientas reales del catálogo (un test comprueba que existan).
"""
import re
from pathlib import Path

from .. import api

CARPETA_GUIA = Path(api.__file__).resolve().parent / "guia"

_PRESENTACION = (
    "OmniCAD es un CAD 3D paramétrico: el documento es una receta (parámetros + pasos de un timeline) que se "
    "recalcula entera con cada cambio. Todas las herramientas devuelven JSON con ok, result y avisos (o "
    "error_kind, mensaje y pistas). Las imágenes llegan como contenido de imagen. Más guías: resources "
    "omnicad://guia/{tema} o la herramienta get_guide.")


def temas_guia():
    return sorted(p.stem for p in CARPETA_GUIA.glob("*.md"))


def leer_guia(tema):
    """Texto de `api/guia/<tema>.md`. Lanza ValueError si el tema no existe."""
    tema = str(tema).strip().lower().removesuffix(".md")
    archivo = CARPETA_GUIA / f"{tema}.md"
    if not re.fullmatch(r"[a-z0-9_]+", tema) or not archivo.is_file():
        raise ValueError(f"No existe el tema de guía '{tema}'. Temas: {', '.join(temas_guia())}.")
    return archivo.read_text(encoding="utf-8")


def instrucciones():
    """`instructions` del servidor: presentación corta + `flujo.md` (el ciclo de trabajo)."""
    return f"{_PRESENTACION}\n\n{leer_guia('flujo')}"


# ---------------------------------------------------------------- prompts
def disenar_pieza(descripcion):
    return (
        f"Diseñá en OmniCAD esta pieza: {descripcion}\n\n"
        "Trabajá en vueltas cortas y mirá el resultado después de cada cambio:\n"
        "1. Mirar: get_scene_info y get_timeline. Si no leíste la guía, get_guide con topic=\"flujo\".\n"
        "2. Medidas: dejá cada medida importante como parámetro (create_parameter) para poder cambiarla después con "
        "set_parameter. Unidades: mm y grados.\n"
        "3. Hacer, un cambio por vez: formas simples con create_box, create_cylinder, create_sphere o create_torus; "
        "formas con perfil con create_sketch + draw_rectangle / draw_circle / draw_line + extrude o revolve. Si no hay "
        "una herramienta específica, list_operation_types y describe_operation dicen qué acepta run_operation.\n"
        "4. Ver la imagen: get_viewport_image desde 2 o 3 vistas (iso, front, top). Compará con lo pedido antes de seguir.\n"
        "5. Medir: get_physical_properties (volumen, masa, caja envolvente), measure_distance y, si hay varias piezas, "
        "check_interference.\n"
        "6. Guardar: save_document con una ruta absoluta. Si algo sale mal, undo.\n")


def preparar_impresion_3d():
    return (
        "Preparar el diseño actual de OmniCAD para impresión 3D:\n"
        "1. get_scene_info y get_timeline: confirmá que todos los pasos están sin error.\n"
        "2. get_physical_properties: la caja envolvente tiene que entrar en la cama de la impresora y el volumen da "
        "una idea del material y del tiempo.\n"
        "3. check_interference si hay varias piezas (las que encastran necesitan holgura; medila con measure_distance).\n"
        "4. get_viewport_image desde iso, front, top y bottom: buscá paredes muy finas, voladizos grandes y detalles "
        "más chicos que la boquilla.\n"
        "5. Corregí con set_parameter (para eso conviene tener las medidas como parámetros) y volvé a mirar la imagen.\n"
        "6. export a .stl o .3mf con una ruta absoluta (una pieza por archivo si se imprimen por separado) y "
        "save_document para guardar el proyecto.\n")


def revisar_diseno():
    return (
        "Revisá el diseño actual de OmniCAD y decí qué está bien y qué no:\n"
        "1. get_timeline: pasos con estado de error o aviso. get_parameters: valores y expresiones con sentido.\n"
        "2. get_sketch en cada boceto: perfiles cerrados y grados de libertad en cero (boceto bien definido).\n"
        "3. get_viewport_image desde iso, front, top y right: compará con la intención del diseño.\n"
        "4. get_physical_properties y measure_distance: contrastá las medidas reales con las pedidas.\n"
        "5. check_interference si hay varias piezas.\n"
        "No cambies nada sin avisar: informá los hallazgos con el id del paso o del cuerpo, y recién después "
        "corregí (set_parameter, edit_feature). Si algo empeora, undo.\n")

# -*- coding: utf-8 -*-
"""Herramientas que necesitan la ventana de OmniCAD en vivo (B-80, MCP-46 y MCP-50). Sin ventana fallan con
APP_NOT_RUNNING; la ventana les da sus funciones como atributos de la `Sesion` (`ui/puente.py`), el mismo camino
de `select_bodies`.

  - `capture_viewport`: la vista 3D REAL tal como la ve la persona (cámara, estilo visual, selección, análisis).
    `get_viewport_image` renderiza aparte, sin ventana; esta captura lo que hay en pantalla.
  - `get_selection`: lo que la persona tiene elegido (cuerpos, caras, aristas, perfiles…).
  - `select_entities`: elige caras, aristas, perfiles o cuerpos en la ventana, por el mismo camino que el clic.
"""
from typing import Literal

from ..timeline.operaciones import OpExtrusion
from .errores import error
from .herramientas_boceto import boceto_activo, seleccionar_perfiles
from .herramientas_modificar import _refs
from .registro import Imagen, herramienta

_LADO_MAXIMO = 4096
_LADO_MINIMO = 16


def _hook(sesion, nombre, herramienta_):
    f = getattr(sesion, nombre, None)
    if f is None:
        raise error("APP_NOT_RUNNING", f"{herramienta_} necesita la ventana de OmniCAD en vivo.",
                    "Abrí la app con el modo en vivo encendido (Preferencias › Agentes) o usá get_viewport_image.")
    return f


@herramienta("capture_viewport", "inspeccion", "Captura la vista 3D REAL de la ventana de OmniCAD tal como la ve la "
             "persona: cámara, estilo visual, entorno, selección y análisis mostrados. Solo en vivo. Para una imagen "
             "sin ventana, con la cámara que pidas, usá get_viewport_image.")
def capture_viewport(sesion, width: int | None = None, height: int | None = None):
    """
    width: ancho en píxeles de la imagen devuelta (16 a 4096); con height. Vacío = el tamaño de la vista en pantalla.
    height: alto en píxeles de la imagen devuelta (16 a 4096); con width.
    """
    capturar = _hook(sesion, "capturar_visor", "capture_viewport")
    if (width is None) != (height is None):
        raise error("INVALID_ARGUMENTS", "Pasá width y height juntos, o ninguno.")
    for nombre, valor in (("width", width), ("height", height)):
        if valor is not None and (isinstance(valor, bool) or not _LADO_MINIMO <= valor <= _LADO_MAXIMO):
            raise error("INVALID_ARGUMENTS", f"{nombre} tiene que estar entre {_LADO_MINIMO} y {_LADO_MAXIMO} píxeles.")
    png, ancho, alto = capturar(width, height)
    return {"image": Imagen(png, ancho, alto), "width": ancho, "height": alto}


def _describir(ref):
    return {"type": ref.get("tipo"), "body": ref.get("cuerpo"), "sketch": ref.get("boceto"), "ref": ref}


@herramienta("get_selection", "documento", "Lee lo que la persona tiene elegido en la ventana: cuerpos, caras, aristas, "
             "perfiles, bocetos, planos… Cada elemento trae su referencia persistente (ref), que sirve como argumento "
             "de las herramientas que reciben referencias. Solo en vivo; no cambia el documento.")
def get_selection(sesion):
    elegidos = [_describir(r) for r in _hook(sesion, "leer_seleccion", "get_selection")()]
    return {"selection": elegidos, "count": len(elegidos)}


@herramienta("select_entities", "documento", "Elige en la ventana cuerpos, caras, aristas o perfiles de boceto, por el "
             "mismo camino que el clic: quedan resaltados y en el navegador. Solo en vivo; no cambia el documento. "
             "Las caras y aristas se eligen con selectores (\">Z\", \"|Z\") o ids de find_faces / find_edges.")
def select_entities(sesion, kind: Literal["body", "face", "edge", "profile"], selector: str | list[str] | None = None,
                    body: str | None = None, sketch: str | None = None, profile: int | list[int] | str = "all",
                    mode: Literal["replace", "add", "remove"] = "replace"):
    """
    kind: body (cuerpos), face (caras), edge (aristas) o profile (perfiles de un boceto).
    selector: body: ids o nombres de cuerpos; face y edge: selector o ids de find_faces / find_edges (o lista). No se usa con profile.
    body: cuerpo donde se evalúan los selectores de face y edge; vacío = el único cuerpo.
    sketch: profile: id o nombre del boceto.
    profile: profile: índice, lista de índices, "all" o "largest".
    mode: replace (por defecto) cambia la selección; add suma a la actual; remove la resta.
    """
    elegir = _hook(sesion, "seleccionar_entidades", "select_entities")
    leer = _hook(sesion, "leer_seleccion", "select_entities")
    if kind == "profile":
        if sketch is None:
            raise error("INVALID_ARGUMENTS", "profile necesita sketch.")
        op, br = boceto_activo(sesion, sketch)
        refs = [{"tipo": "perfil", "boceto": op.id, **OpExtrusion.referencia_perfil(p)}
                for p in seleccionar_perfiles(br, op, profile)]
    else:
        if selector is None or selector == []:
            raise error("INVALID_ARGUMENTS", f"{kind} necesita selector.")
        if kind == "body":
            ids = [selector] if isinstance(selector, str) else selector
            refs = [{"tipo": "cuerpo", "cuerpo": sesion.cuerpo(c).id} for c in ids]
        else:
            refs = _refs(sesion, selector, "cara" if kind == "face" else "arista", body)[0]
    elegir(refs, mode)
    elegidos = [_describir(r) for r in leer()]
    return {"selection": elegidos, "count": len(elegidos)}

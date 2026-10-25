# -*- coding: utf-8 -*-
"""
Preajustes de comandos [Create and use presets de Fusion]: los valores de un diálogo (Nervio, Red, Agujero…) guardados
con un nombre para volver a usarlos.

Se guardan solo en esta PC (no viajan con el diseño, como en Fusion), en `preajustes.json` de la carpeta de datos de la
app o en la ruta de la variable OMNICAD_PREAJUSTES. Un preajuste es un dict clave de campo → valor simple (texto,
número o casilla): lo que se elige en la vista (cuerpos, caras, perfiles) no se guarda.

Por comando hay además un «predeterminado», lo que el diálogo trae al abrirse: "fabrica" (los valores de fábrica),
"ultimo" (los últimos que se usaron) o el nombre de un preajuste.
"""
import json
import os
from pathlib import Path

from . import geometria as geo

VAR_PREAJUSTES = "OMNICAD_PREAJUSTES"
FABRICA, ULTIMO = "fabrica", "ultimo"


def ruta_preajustes():
    from .. import carpeta_datos
    return Path(os.environ[VAR_PREAJUSTES]) if os.environ.get(VAR_PREAJUSTES) else carpeta_datos() / "preajustes.json"


def _leer():
    """Los preajustes guardados; {} solo si el archivo no existe. Si está roto, lo aparta como `.bak` antes de que el
    próximo `guardar` lo pise (se perderían los demás preajustes)."""
    ruta = ruta_preajustes()
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (OSError, ValueError):
        try:
            os.replace(ruta, ruta.with_suffix(".bak"))
        except OSError:
            pass
        return {}
    return datos if isinstance(datos, dict) else {}


def _guardar(datos):
    ruta = ruta_preajustes()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    tmp = ruta.with_suffix(".tmp")
    tmp.write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, ruta)


def _comando(datos, clave):
    c = datos.get(clave)
    return c if isinstance(c, dict) else {}


def simples(valores):
    """Solo los valores que se pueden guardar: texto, números y casillas (no las selecciones de la vista)."""
    return {k: v for k, v in (valores or {}).items() if isinstance(v, (str, int, float, bool))}


def _nombre(nombre):
    texto = str(nombre or "").strip()
    if not texto:
        raise geo.ErrorGeometria("Escribí el nombre del preajuste.")
    return texto


def listar(clave):
    """{"presets": [nombres], "default": "fabrica" | "ultimo" | nombre} del comando."""
    c = _comando(_leer(), clave)
    presets = c.get("preajustes") if isinstance(c.get("preajustes"), dict) else {}
    return {"presets": list(presets), "default": c.get("defecto", FABRICA)}


def obtener(clave, nombre):
    """Los valores de un preajuste; error si no existe."""
    presets = _comando(_leer(), clave).get("preajustes") or {}
    if nombre not in presets:
        raise geo.ErrorGeometria(f"El comando «{clave}» no tiene un preajuste «{nombre}».")
    return dict(presets[nombre])


def guardar(clave, nombre, valores, sobrescribir=True):
    """Crea (o actualiza) un preajuste con los valores simples de `valores`. Devuelve los valores guardados."""
    nombre = _nombre(nombre)
    datos = _leer()
    c = datos.setdefault(clave, {})
    presets = c.setdefault("preajustes", {})
    if nombre in presets and not sobrescribir:
        raise geo.ErrorGeometria(f"Ya existe el preajuste «{nombre}».")
    presets[nombre] = simples(valores)
    _guardar(datos)
    return presets[nombre]


def renombrar(clave, nombre, nuevo):
    nuevo = _nombre(nuevo)
    datos = _leer()
    c = _comando(datos, clave)
    presets = c.get("preajustes") or {}
    if nombre not in presets:
        raise geo.ErrorGeometria(f"El comando «{clave}» no tiene un preajuste «{nombre}».")
    if nuevo in presets and nuevo != nombre:
        raise geo.ErrorGeometria(f"Ya existe el preajuste «{nuevo}».")
    c["preajustes"] = {(nuevo if n == nombre else n): v for n, v in presets.items()}
    if c.get("defecto") == nombre:
        c["defecto"] = nuevo
    _guardar(datos)


def borrar(clave, nombre):
    datos = _leer()
    c = _comando(datos, clave)
    presets = c.get("preajustes") or {}
    if nombre not in presets:
        raise geo.ErrorGeometria(f"El comando «{clave}» no tiene un preajuste «{nombre}».")
    del presets[nombre]
    if c.get("defecto") == nombre:
        c["defecto"] = FABRICA
    _guardar(datos)


def definir_defecto(clave, defecto):
    """Predeterminado del comando: "fabrica", "ultimo" o el nombre de un preajuste existente."""
    datos = _leer()
    c = datos.setdefault(clave, {})
    if defecto not in (FABRICA, ULTIMO) and defecto not in (c.get("preajustes") or {}):
        raise geo.ErrorGeometria(f"El comando «{clave}» no tiene un preajuste «{defecto}».")
    c["defecto"] = defecto
    _guardar(datos)


def guardar_ultimo(clave, valores):
    """Recuerda los últimos valores usados (los que trae el diálogo con el predeterminado «ultimo»)."""
    datos = _leer()
    datos.setdefault(clave, {})["ultimo"] = simples(valores)
    _guardar(datos)


def valores_iniciales(clave):
    """Valores con que se abre el diálogo según su predeterminado; {} = los de fábrica."""
    c = _comando(_leer(), clave)
    defecto = c.get("defecto", FABRICA)
    if defecto == ULTIMO:
        return dict(c.get("ultimo") or {})
    if defecto != FABRICA:
        return dict((c.get("preajustes") or {}).get(defecto) or {})
    return {}

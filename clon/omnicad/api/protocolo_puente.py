# -*- coding: utf-8 -*-
"""
Protocolo del puente en vivo: lo comparten la app (`ui/puente.py`, con Qt) y el cliente del servidor MCP
(`servidor_mcp/puente_cliente.py`, sin Qt). Este módulo no importa Qt ni el paquete `mcp`.

Transporte: TCP SOLO en 127.0.0.1, líneas JSON en UTF-8 (un objeto por línea, terminado en "\\n").

    pedido    {"id": 1, "token": "...", "tool": "create_box", "args": {...}}
    respuesta {"id": 1, "ok": true, "result": {...}, "avisos": [...]}
              {"id": 1, "ok": false, "error_kind": "APP_BUSY", "mensaje": "...", "pistas": [...]}

  - La respuesta es la de `api.llamar` más el `id` del pedido. Cada `api.Imagen` viaja como
    {"png_base64": "...", "width": W, "height": H}.
  - Pedidos especiales (no son herramientas del catálogo): "ping" y "status".
  - Token incorrecto → error UNAUTHORIZED y la app cierra la conexión.

Descubrimiento: al escuchar, la app escribe `puente.json` ({port, token, pid, version, protocol}) en
%LOCALAPPDATA%/OmniCAD (o en la carpeta de la variable OMNICAD_PUENTE_DIR, que usan las pruebas) y lo borra
al cerrar. Ese archivo es la única forma de conseguir el token.
"""
import base64
import json
import os
from pathlib import Path

from .registro import Imagen

PUERTO_POR_DEFECTO = 27191
PUERTOS_EXTRA = 10                  # si el puerto está ocupado se prueban los 10 siguientes
PROTOCOLO = 1
LINEA_MAXIMA = 64 * 1024 * 1024     # una receta con STEP embebido puede pesar varios MB; más que esto se corta
PEDIDOS_ESPECIALES = ("ping", "status")
VARIABLE_CARPETA = "OMNICAD_PUENTE_DIR"


def carpeta_info():
    """Carpeta de `puente.json`: OMNICAD_PUENTE_DIR o %LOCALAPPDATA%/OmniCAD (por usuario)."""
    propia = os.environ.get(VARIABLE_CARPETA)
    if propia:
        return Path(propia)
    base = os.environ.get("LOCALAPPDATA")
    return (Path(base) if base else Path.home() / ".local" / "share") / "OmniCAD"


def ruta_info():
    return carpeta_info() / "puente.json"


def leer_info(ruta=None):
    """Datos de `puente.json` ({port, token, pid, version, protocol}) o None si no hay o está dañado."""
    try:
        datos = json.loads(Path(ruta or ruta_info()).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(datos, dict) or not isinstance(datos.get("port"), int) or not isinstance(datos.get("token"), str):
        return None
    return datos


def escribir_info(ruta, datos):
    """Escritura atómica (archivo temporal + reemplazo): un lector nunca ve el JSON a medias."""
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    temporal = ruta.with_name(ruta.name + f".{os.getpid()}.tmp")
    temporal.write_text(json.dumps(datos), encoding="utf-8")
    os.replace(temporal, ruta)


def borrar_info(ruta, token):
    """Borra `puente.json` solo si sigue siendo el nuestro (otra instancia de la app pudo pisarlo)."""
    datos = leer_info(ruta)
    if datos is not None and datos.get("token") == token:
        try:
            Path(ruta).unlink()
        except OSError:
            pass


# ---------------------------------------------------------------- imágenes por el cable
def a_cable(valor):
    """Copia de `valor` con cada `Imagen` convertida en {"png_base64", "width", "height"}."""
    if isinstance(valor, Imagen):
        return {"png_base64": base64.b64encode(valor.png).decode("ascii"), "width": valor.ancho, "height": valor.alto}
    if isinstance(valor, dict):
        return {k: a_cable(v) for k, v in valor.items()}
    if isinstance(valor, (list, tuple)):
        return [a_cable(v) for v in valor]
    return valor


def desde_cable(valor):
    """Inverso de `a_cable`: cada {"png_base64", "width", "height"} vuelve a ser una `Imagen`."""
    if isinstance(valor, dict):
        if set(valor) == {"png_base64", "width", "height"} and isinstance(valor["png_base64"], str):
            return Imagen(base64.b64decode(valor["png_base64"]), int(valor["width"]), int(valor["height"]))
        return {k: desde_cable(v) for k, v in valor.items()}
    if isinstance(valor, list):
        return [desde_cable(v) for v in valor]
    return valor


def linea(objeto):
    """Objeto → una línea JSON en UTF-8 terminada en "\\n"."""
    return (json.dumps(objeto, ensure_ascii=False) + "\n").encode("utf-8")

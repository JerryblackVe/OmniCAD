"""Historial local de chats del Asistente (IA-7): un JSON por chat en `carpeta_datos()/asistente/`.

Cada chat guarda título (las primeras palabras del primer pedido), fecha, modo, proveedor, modelo, los mensajes
neutrales (`proveedores/base.py`) y, en modo suscripción, el id de sesión de cada CLI para seguir con `--resume`.
Nada sale de la PC. NUNCA se guarda una clave: no está en los mensajes ni en la configuración.

Imágenes: van en base64 si pesan hasta TOPE_IMAGEN; las más grandes se reemplazan por una marca de texto (una captura
del visor pesa ~100 KB; el tope evita que un chat largo con capturas enormes pese decenas de MB).
Adjuntos (IA-9): de cada uno queda solo su texto (nombre, tipo y ruta); la imagen o el PDF no se guardan.
"""
import base64
import json
import os
import re
import uuid
from datetime import datetime
from pathlib import Path

VAR_CARPETA = "OMNICAD_ASISTENTE_DIR"     # reemplaza la carpeta del historial (pruebas)
TOPE_IMAGEN = 1_000_000                   # bytes de PNG por imagen
PALABRAS_TITULO = 8
_ID = re.compile(r"^[0-9]{8}-[0-9]{6}-[0-9a-f]{6}$")   # el id es el nombre del archivo: nunca una ruta


class ErrorHistorial(Exception):
    """Chat inexistente o archivo dañado; el mensaje es para el usuario."""


def carpeta():
    from .. import carpeta_datos
    return Path(os.environ[VAR_CARPETA]) if os.environ.get(VAR_CARPETA) else carpeta_datos() / "asistente"


def _ruta(id_chat):
    if not isinstance(id_chat, str) or not _ID.match(id_chat):
        raise ErrorHistorial(f"Id de chat inválido: {id_chat!r}.")
    return carpeta() / f"{id_chat}.json"


def titulo_de(mensajes):
    """Las primeras palabras del primer pedido de texto."""
    for m in mensajes:
        for b in m["contenido"] if m["rol"] == "usuario" else ():
            if b.get("tipo") == "texto" and b["texto"].strip():
                palabras = b["texto"].split()
                return " ".join(palabras[:PALABRAS_TITULO]) + ("…" if len(palabras) > PALABRAS_TITULO else "")
    return "Chat sin título"


def _a_json(bloque):
    if bloque.get("tipo") == "imagen":
        png = bloque["png"]
        if len(png) > TOPE_IMAGEN:
            return {"tipo": "texto", "texto": f"(imagen no guardada en el historial: pesaba {len(png) // 1024} KB)"}
        return {**bloque, "png": base64.b64encode(png).decode("ascii")}
    if bloque.get("tipo") == "resultado_herramienta":
        return {**bloque, "contenido": [_a_json(b) for b in bloque["contenido"]]}
    return bloque


# Lo que el panel lee de cada bloque: un archivo editado a mano no puede romper la ventana al mostrarlo.
_CAMPOS = {"texto": {"texto": str}, "imagen": {"png": str}, "pedido_herramienta": {"nombre": str, "args": dict},
           "resultado_herramienta": {"contenido": list}}


def _de_json(bloque):
    campos = _CAMPOS.get(bloque.get("tipo")) if isinstance(bloque, dict) else None
    if campos is None or not all(isinstance(bloque.get(k), t) for k, t in campos.items()):
        raise ValueError("bloque inválido")
    if bloque["tipo"] == "imagen":
        return {**bloque, "png": base64.b64decode(bloque["png"], validate=True)}
    if bloque["tipo"] == "resultado_herramienta":
        return {**bloque, "contenido": [_de_json(b) for b in bloque["contenido"]]}
    return bloque


def guardar(mensajes, modo, proveedor, modelo, id_chat=None, sesiones_cli=None):
    """Escribe el chat (nuevo si `id_chat` es None) y devuelve su id. Escritura atómica: un corte no lo rompe."""
    id_chat = id_chat or f"{datetime.now():%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:6]}"
    ruta = _ruta(id_chat)
    datos = {"id": id_chat, "titulo": titulo_de(mensajes), "fecha": datetime.now().isoformat(timespec="seconds"),
             "modo": modo, "proveedor": proveedor, "modelo": modelo, "sesiones_cli": {k: v for k, v in (sesiones_cli or {}).items() if v},
             "mensajes": [{"rol": m["rol"], "contenido": [_a_json(b) for b in m["contenido"] if not b.get("adjunto")]}
                          for m in mensajes]}
    ruta.parent.mkdir(parents=True, exist_ok=True)
    temporal = ruta.with_suffix(".tmp")
    temporal.write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
    os.replace(temporal, ruta)
    return id_chat


def _leer(ruta):
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    if not isinstance(datos, dict) or not isinstance(datos.get("mensajes"), list):
        raise ValueError("sin mensajes")
    return datos


def listar():
    """Resumen de cada chat, el más nuevo primero. Los archivos dañados se saltean (no tiran la app)."""
    chats = []
    # shortcut: lee cada JSON entero (con sus imágenes); con cientos de chats largos el diálogo tardaría en abrir:
    # pasar a un índice con los resúmenes si eso pasa.
    for ruta in carpeta().glob("*.json") if carpeta().is_dir() else ():
        try:
            d = _leer(ruta)
            chats.append((ruta.stat().st_mtime_ns, {
                "id": ruta.stem, "titulo": str(d.get("titulo", "")), "fecha": str(d.get("fecha", "")),
                "modo": d.get("modo"), "proveedor": d.get("proveedor"), "modelo": d.get("modelo"),
                "mensajes": len(d["mensajes"])}))
        except (OSError, ValueError, AttributeError):
            continue
    # Por la hora del archivo: dos chats guardados en el mismo segundo quedan igual en orden.
    return [c for _t, c in sorted(chats, key=lambda x: x[0], reverse=True) if _ID.match(c["id"])]


def cargar(id_chat):
    """El chat entero, con las imágenes otra vez en bytes. ErrorHistorial si no existe o está dañado."""
    ruta = _ruta(id_chat)
    try:
        d = _leer(ruta)
        d["mensajes"] = [{"rol": m["rol"], "contenido": [_de_json(b) for b in m["contenido"]]}
                         for m in d["mensajes"] if m["rol"] in ("usuario", "asistente")]
        d["sesiones_cli"] = {str(k): str(v) for k, v in (d.get("sesiones_cli") or {}).items() if v}
    except FileNotFoundError:
        raise ErrorHistorial(f"No existe el chat {id_chat}.") from None
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        raise ErrorHistorial(f"El chat {id_chat} está dañado y no se puede abrir.") from None
    return d


def borrar(id_chat):
    """Borra un chat. ErrorHistorial si no existe."""
    try:
        _ruta(id_chat).unlink()
    except FileNotFoundError:
        raise ErrorHistorial(f"No existe el chat {id_chat}.") from None

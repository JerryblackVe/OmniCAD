# -*- coding: utf-8 -*-
"""Línea de comandos del servidor MCP: `omnicad-mcp` o `python -m omnicad.servidor_mcp`."""
import argparse
import sys

from .. import VERSION, api
from .servidor import GRUPOS_CONOCIDOS, GRUPOS_POR_DEFECTO, MODOS, crear_servidor

HOST = "127.0.0.1"          # fijo a propósito: el servidor HTTP nunca escucha en otra interfaz
PUERTO_POR_DEFECTO = 27190


def _parser():
    p = argparse.ArgumentParser(prog="omnicad-mcp", description="Servidor MCP de OmniCAD (stdio por defecto).")
    p.add_argument("--modo", choices=MODOS, default="auto",
                   help="vivo: la app abierta (puente en vivo); sin_ventana: un documento propio; auto (por defecto): "
                        "la app si está escuchando y si no, sin ventana")
    p.add_argument("--doc", metavar="RUTA", help="proyecto .omnicad para abrir al arrancar (implica --modo sin_ventana)")
    p.add_argument("--toolsets", metavar="LISTA", help="grupos de herramientas separados por coma "
                   f"(por defecto: {','.join(GRUPOS_POR_DEFECTO)})")
    p.add_argument("--dev", action="store_true", help="suma el grupo 'dev' (herramientas de desarrollo)")
    p.add_argument("--http", action="store_true", help=f"servir por HTTP en {HOST} en vez de stdio")
    p.add_argument("--port", type=int, help=f"puerto del modo --http (por defecto {PUERTO_POR_DEFECTO})")
    p.add_argument("--log-level", default="WARNING", choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                   help="nivel de log (siempre a stderr)")
    p.add_argument("--version", action="version", version=f"omnicad-mcp {VERSION}")
    return p


def _log(texto):
    print(texto, file=sys.stderr, flush=True)       # stdout es del protocolo: nada de prints ahí


def main(argv=None):
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(errors="replace")    # consola cp1252: que un carácter raro no tire el servidor
    parser = _parser()
    args = parser.parse_args(argv)
    if args.port is not None and not args.http:
        parser.error("--port solo tiene sentido con --http")
    if args.port is not None and not 1 <= args.port <= 65535:
        parser.error("--port tiene que estar entre 1 y 65535")
    modo = args.modo
    if args.doc:
        if modo == "vivo":
            parser.error("--doc abre un documento sin ventana: no se combina con --modo vivo")
        modo = "sin_ventana"            # un documento explícito = una sesión propia, nunca la de la ventana
    toolsets = None
    if args.toolsets:
        toolsets = [t.strip() for t in args.toolsets.split(",") if t.strip()]
        desconocidos = [t for t in toolsets if t not in GRUPOS_CONOCIDOS]
        if desconocidos or not toolsets:
            parser.error(f"toolsets desconocidos: {', '.join(desconocidos) or '(vacío)'}. "
                         f"Válidos: {', '.join(GRUPOS_CONOCIDOS)}")
    sesion = api.Sesion()
    if args.doc:
        try:
            sesion.abrir(args.doc)
        except Exception as e:  # noqa: BLE001 — cualquier falla al abrir corta el arranque con un mensaje claro
            _log(f"omnicad-mcp: no se pudo abrir --doc {args.doc}: {getattr(e, 'mensaje', e)}")
            return 2
    servidor = crear_servidor(sesion, toolsets, args.dev, args.log_level, modo=modo)
    try:
        if args.http:
            puerto = args.port or PUERTO_POR_DEFECTO
            _log(f"omnicad-mcp {VERSION}: {len(servidor.nombres)} herramientas en http://{HOST}:{puerto}/mcp, modo {modo}")
            servidor.run("streamable-http", host=HOST, port=puerto)
        else:
            _log(f"omnicad-mcp {VERSION}: {len(servidor.nombres)} herramientas por stdio, modo {modo}")
            servidor.run("stdio")
    except KeyboardInterrupt:
        return 130
    finally:
        servidor.cerrar()
    return 0

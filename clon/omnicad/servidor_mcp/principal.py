# -*- coding: utf-8 -*-
"""Línea de comandos del servidor MCP: `omnicad-mcp` o `python -m omnicad.servidor_mcp`.

En modo `--http` el acceso EXIGE un token: cada arranque genera uno (`secrets.token_urlsafe(32)`) y lo
escribe en `mcp_http.json` (carpeta de datos del usuario; la variable OMNICAD_PUENTE_DIR la redirige,
como a `puente.json`). Todo pedido HTTP tiene que llevar el header `Authorization: Bearer <token>` o
recibe 401: sin eso, cualquier proceso local podría llamar a `execute_code`. Por stdio no hace falta
token: quien controla la entrada estándar ya controla el proceso.
"""
import argparse
import json
import os
import secrets
import sys

from .. import VERSION, api
from ..api import protocolo_puente as proto
from .servidor import GRUPOS_CONOCIDOS, GRUPOS_POR_DEFECTO, MODOS, crear_servidor

HOST = "127.0.0.1"          # fijo a propósito: el servidor HTTP nunca escucha en otra interfaz
PUERTO_POR_DEFECTO = 27190
NOMBRE_INFO_HTTP = "mcp_http.json"


class ExigirBearer:
    """Envoltorio ASGI (el app del SDK queda intacto adentro): todo pedido HTTP sin el header
    `Authorization: Bearer <token>` correcto recibe 401 y nunca llega a las herramientas.

    La comparación va con `secrets.compare_digest` (sin filtraciones por tiempo). Los scopes que no son
    http (arranque y parada del servidor) pasan tal cual.
    """

    def __init__(self, app, token):
        self.app = app
        self.token = token

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            cabeceras = {clave.decode("latin-1").lower(): valor.decode("latin-1")
                         for clave, valor in scope.get("headers", [])}
            if not secrets.compare_digest(cabeceras.get("authorization", "").encode("utf-8"),
                                          f"Bearer {self.token}".encode("utf-8")):
                cuerpo = json.dumps({"ok": False, "error_kind": "UNAUTHORIZED",
                                     "mensaje": "Token ausente o incorrecto: mandá el header "
                                                f"'Authorization: Bearer <token>' (el token está en "
                                                f"{NOMBRE_INFO_HTTP}, en la carpeta de datos de OmniCAD).",
                                     "pistas": []}).encode("utf-8")
                await send({"type": "http.response.start", "status": 401,
                            "headers": [(b"content-type", b"application/json; charset=utf-8"),
                                        (b"www-authenticate", b"Bearer")]})
                await send({"type": "http.response.body", "body": cuerpo})
                return
        await self.app(scope, receive, send)


def correr_http(servidor, puerto, token, nivel_log):
    """Sirve por HTTP con el token exigido: lo mismo que `run("streamable-http")` del SDK (uvicorn sobre
    `streamable_http_app()`), pero con el app envuelto en `ExigirBearer`."""
    import uvicorn                          # import tardío como en el SDK: el modo stdio no lo necesita
    app = ExigirBearer(servidor.streamable_http_app(), token)
    uvicorn.Server(uvicorn.Config(app, host=HOST, port=puerto, log_level=nivel_log.lower())).run()


def _parser():
    p = argparse.ArgumentParser(prog="omnicad-mcp", description="Servidor MCP de OmniCAD (stdio por defecto).")
    p.add_argument("--modo", choices=MODOS, default="auto",
                   help="vivo: la app abierta (puente en vivo); sin_ventana: un documento propio; auto (por defecto): "
                        "la app si está escuchando y si no, sin ventana")
    p.add_argument("--doc", metavar="RUTA", help="proyecto .omnicad para abrir al arrancar (implica --modo sin_ventana)")
    p.add_argument("--toolsets", metavar="LISTA", help="grupos de herramientas separados por coma "
                   f"(por defecto: {','.join(GRUPOS_POR_DEFECTO)})")
    p.add_argument("--tools", metavar="LISTA", help="solo estas herramientas, por nombre y separadas por coma (dentro "
                   "de los grupos activos); la usa el Asistente para darle al CLI una lista corta")
    p.add_argument("--dev", action="store_true", help="suma el grupo 'dev' (herramientas de desarrollo)")
    p.add_argument("--http", action="store_true", help=f"servir por HTTP en {HOST} en vez de stdio "
                   f"(exige token: se genera uno por arranque y queda en {NOMBRE_INFO_HTTP}, "
                   "en la carpeta de datos)")
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
    herramientas = None
    if args.tools is not None:
        herramientas = [t.strip() for t in args.tools.split(",") if t.strip()]
        conocidas = {h["nombre"] for h in api.catalogo()}
        desconocidas = [t for t in herramientas if t not in conocidas]
        if desconocidas or not herramientas:
            parser.error(f"herramientas desconocidas en --tools: {', '.join(desconocidas) or '(vacío)'}")
    sesion = api.Sesion()
    if args.doc:
        try:
            sesion.abrir(args.doc)
        except Exception as e:  # noqa: BLE001 — cualquier falla al abrir corta el arranque con un mensaje claro
            _log(f"omnicad-mcp: no se pudo abrir --doc {args.doc}: {getattr(e, 'mensaje', e)}")
            return 2
    servidor = crear_servidor(sesion, toolsets, args.dev, args.log_level, modo=modo, herramientas=herramientas)
    try:
        if args.http:
            puerto = args.port or PUERTO_POR_DEFECTO
            token = secrets.token_urlsafe(32)
            ruta_info = proto.carpeta_info() / NOMBRE_INFO_HTTP
            proto.escribir_info(ruta_info, {"port": puerto, "token": token, "pid": os.getpid(),
                                            "version": VERSION})
            _log(f"omnicad-mcp {VERSION}: {len(servidor.nombres)} herramientas en http://{HOST}:{puerto}/mcp, "
                 f"modo {modo}")
            _log(f"omnicad-mcp: el HTTP exige token (header 'Authorization: Bearer <token>'); "
                 f"está en {ruta_info}")
            try:
                correr_http(servidor, puerto, token, args.log_level)
            finally:
                proto.borrar_info(ruta_info, token)       # solo si sigue siendo el nuestro
        else:
            _log(f"omnicad-mcp {VERSION}: {len(servidor.nombres)} herramientas por stdio, modo {modo}")
            servidor.run("stdio")
    except KeyboardInterrupt:
        return 130
    finally:
        servidor.cerrar()
    return 0

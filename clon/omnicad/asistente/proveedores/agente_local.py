"""Modo suscripción (IA-6): lanza el Claude Code, Codex u OpenCode que la persona ya instaló y logueó.

El agente externo se conecta a la ventana abierta con `omnicad-mcp --modo vivo` (puente en vivo: el servidor MCP lee
`puente.json`, así que ningún token pasa por la línea de comandos ni por los archivos temporales). Este módulo traduce
la salida JSON de cada CLI a los mismos eventos que el modo API (texto, herramienta, imagen, uso, error). Sin Qt.
OmniCAD nunca ve, pide ni guarda las credenciales de la suscripción: el login lo hace cada CLI con su propio flujo.

Seguridad en Windows: los CLI de npm son `.cmd` y pasan por cmd.exe, que interpreta `&|<>^%`. Por eso el pedido de la
persona va SIEMPRE por la entrada estándar, nunca en los argumentos; en los argumentos solo hay flags fijos, nombres
de herramientas, rutas temporales y modelos/sesiones validados con `SEGURO`.
"""
import base64
import binascii
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from collections import deque

from omnicad import api

from ..herramientas import Herramientas
from .base import ErrorProveedor

# tipo → (nombre visible, ejecutable por defecto, prefijo de las herramientas MCP en su salida)
AGENTES = {
    "claude_code": ("Claude Code", "claude", "mcp__omnicad__"),
    "codex": ("Codex", "codex", ""),
    "opencode": ("OpenCode", "opencode", "omnicad_"),
}
SEGURO = re.compile(r"^[\w.:/@+-]*$")      # modelos, variantes e ids de sesión: nada que cmd.exe interprete
MCP = [sys.executable, "-m", "omnicad.servidor_mcp", "--modo", "vivo"]
ESPERA_HERRAMIENTA = 300   # s: la persona puede tardar en apretar Aplicar en la tarjeta de plan
NO_LOGUEADO = re.compile(r"log ?in|logged|authenticat|unauthori[sz]ed|\b401\b|api key|credential", re.I)
if os.name == "nt":
    # sin ventana de consola (OmniCAD es una app de ventanas) y en su propio grupo, para matar el árbol entero
    LANZAR = {"creationflags": subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP}
else:
    LANZAR = {"start_new_session": True}


def ejecutable(tipo, ruta=""):
    """Ruta completa del CLI (la de Preferencias o la del PATH); None si no está."""
    return shutil.which((ruta or "").strip() or AGENTES[tipo][1])


def matar(proceso):
    """Corta el proceso y TODOS sus hijos (cmd.exe → node → omnicad-mcp): sin huérfanos."""
    if proceso.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(proceso.pid)], capture_output=True, **LANZAR)
    else:
        import signal
        try:
            os.killpg(proceso.pid, signal.SIGKILL)
        except OSError:
            pass


def _respuesta(contenido, es_error):
    """Resultado de una herramienta MCP (texto con el JSON de `api.llamar` e imágenes) → (respuesta, imágenes)."""
    bloques = [{"type": "text", "text": contenido}] if isinstance(contenido, str) else (contenido or [])
    textos, imagenes = [], []
    for b in bloques:
        if not isinstance(b, dict):
            continue
        if b.get("type") == "text":
            textos.append(b.get("text") or "")
        elif b.get("type") == "image":
            datos = (b.get("source") or {}).get("data") or b.get("data")   # Claude: source.data; MCP crudo: data
            try:
                imagenes.append(api.Imagen(base64.b64decode(datos), 0, 0))
            except (TypeError, ValueError, binascii.Error):
                pass
    texto = "\n".join(textos)
    try:
        respuesta = json.loads(texto)
    except ValueError:
        respuesta = None
    if not isinstance(respuesta, dict) or "ok" not in respuesta:
        respuesta = {"ok": not es_error, "result": texto}
    return respuesta, imagenes


class AgenteLocal:
    """Un CLI instalado. `sesion` es el id de su conversación: el panel lo guarda para seguir el chat."""

    def __init__(self, tipo, ruta="", modelo="", variante=""):
        if tipo not in AGENTES:
            raise ErrorProveedor(f"Agente desconocido: {tipo!r}. Opciones: {', '.join(AGENTES)}.")
        nombre, comando, _prefijo = AGENTES[tipo]
        self.tipo, self.nombre = tipo, nombre
        self.ruta = ejecutable(tipo, ruta)
        if self.ruta is None:
            donde = f"en «{ruta}»" if (ruta or "").strip() else f"en el PATH (comando «{comando}»)"
            raise ErrorProveedor(f"{nombre} no está instalado o no se encuentra {donde}. Instalalo y logueate, o "
                                 "poné la ruta del ejecutable en Preferencias › Asistente IA.")
        for valor in (modelo, variante):
            if not SEGURO.match(valor or ""):
                raise ErrorProveedor(f"Valor inválido para {nombre}: {valor!r} (solo letras, números y . : / @ + -).")
        self.modelo, self.variante = modelo or "", variante or ""
        self.sesion = None
        self.proceso = None     # el CLI del pedido en curso (el panel lo mata al cancelar o cerrar la app)

    def version(self):
        """`<cli> --version` (Preferencias › Probar conexión): confirma que está instalado; el login lo ve el pedido."""
        r = subprocess.run([self.ruta, "--version"], capture_output=True, stdin=subprocess.DEVNULL, timeout=60,
                           **LANZAR)
        salida = (r.stdout or r.stderr).decode("utf-8", "replace").strip()
        return salida.splitlines()[0][:80] if r.returncode == 0 and salida else None

    # ------------------------------------------------------------ cómo se lanza cada CLI
    def argumentos(self, modo, carpeta, sistema):
        """Línea de comandos (lista, sin shell) y variables de entorno extra. `sistema` ya está en `carpeta`."""
        herramientas = Herramientas(modo=modo)
        permitidas = sorted(herramientas.catalogo)
        todas = modo in ("guiar", "hacer")    # en Guiar y Hacer los cambios los frena la tarjeta Aplicar del panel
        if self.sesion is not None and not SEGURO.match(self.sesion):
            self.sesion = None
        if self.tipo == "claude_code":
            ruta_mcp = os.path.join(carpeta, "mcp.json")
            with open(ruta_mcp, "w", encoding="utf-8") as f:
                json.dump({"mcpServers": {"omnicad": {"command": MCP[0], "args": MCP[1:]}}}, f)
            # con todas las herramientas, la lista explícita pasaría el tope de 8191 caracteres de cmd.exe
            reglas = "mcp__omnicad" if todas else ",".join("mcp__omnicad__" + n for n in permitidas)
            argv = [self.ruta, "-p", "--output-format", "stream-json", "--verbose", "--mcp-config", ruta_mcp,
                    "--strict-mcp-config", "--tools", "", "--allowedTools", reglas,
                    "--disallowedTools", "mcp__omnicad__execute_code", "--permission-prompts", "none",
                    "--append-system-prompt-file", sistema]
            argv += ["--model", self.modelo] if self.modelo else []
            argv += ["--resume", self.sesion] if self.sesion else []
            return argv, {"MCP_TOOL_TIMEOUT": str(ESPERA_HERRAMIENTA * 1000)}
        if self.tipo == "opencode":
            with open(sistema, encoding="utf-8") as f:
                prompt = f.read()
            # «*» primero y lo permitido después: en OpenCode gana la última regla que coincide
            permisos = {"*": "deny", **({"omnicad_*": "allow"} if todas else
                                        {"omnicad_" + n: "allow" for n in permitidas}),
                        "omnicad_execute_code": "deny"}
            config = {"mcp": {"omnicad": {"type": "local", "command": MCP, "enabled": True,
                                          "timeout": ESPERA_HERRAMIENTA * 1000}},
                      "agent": {"omnicad": {"mode": "primary", "prompt": prompt, "permission": permisos,
                                            # solo las de OmniCAD en el contexto: los MCP del usuario no gastan tokens
                                            "tools": {"*": False, "omnicad_*": True}}}}
            argv = [self.ruta, "run", "--format", "json", "--agent", "omnicad", "--title", "OmniCAD"]
            argv += ["-m", self.modelo] if self.modelo else []
            argv += ["--variant", self.variante] if self.variante else []
            argv += ["-s", self.sesion] if self.sesion else []
            # config en línea (encima de la del usuario, sin tocar su archivo global)
            return argv, {"OPENCODE_CONFIG_CONTENT": json.dumps(config, ensure_ascii=False)}
        herramientas_codex = (f"mcp_servers.omnicad.disabled_tools={json.dumps(['execute_code'])}" if todas else
                              f"mcp_servers.omnicad.enabled_tools={json.dumps(permitidas)}")
        argv = [self.ruta, "exec", "--json", "--skip-git-repo-check", "--sandbox", "read-only",
                "-c", f"model_instructions_file={json.dumps(sistema)}",
                "-c", f"mcp_servers.omnicad.command={json.dumps(MCP[0])}",
                "-c", f"mcp_servers.omnicad.args={json.dumps(MCP[1:])}",
                "-c", f"mcp_servers.omnicad.tool_timeout_sec={ESPERA_HERRAMIENTA}",
                "-c", "mcp_servers.omnicad.required=true", "-c", 'approval_policy="never"', "-c", herramientas_codex]
        argv += ["-m", self.modelo] if self.modelo else []
        argv += ["resume", self.sesion] if self.sesion else []
        return argv + ["-"], {}

    # ------------------------------------------------------------ de su salida JSON a los eventos del panel
    def traducir(self, evento, estado, emitir):
        """Un objeto JSON de la salida del CLI → eventos. `estado`: pedidos de herramientas pendientes y texto de los errores."""
        prefijo = AGENTES[self.tipo][2]

        def herramienta(nombre, args, contenido, es_error):
            respuesta, imagenes = _respuesta(contenido, es_error)
            emitir("herramienta", {"nombre": nombre.removeprefix(prefijo), "args": args or {}, "respuesta": respuesta})
            for imagen in imagenes:
                emitir("imagen", imagen)

        def error(texto):
            estado["error"] += texto + " "
            emitir("error", texto)

        tipo = evento.get("type")
        if self.tipo == "claude_code":
            self.sesion = evento.get("session_id") or self.sesion
            if tipo == "system" and evento.get("subtype") == "init":
                caidos = [s for s in evento.get("mcp_servers") or [] if s.get("name") == "omnicad"
                          and s.get("status") != "connected"]
                if caidos:
                    error(f"Claude Code no pudo conectarse con OmniCAD (MCP: {caidos[0].get('status')}).")
            elif tipo == "assistant":
                for b in (evento.get("message") or {}).get("content") or []:
                    if b.get("type") == "text" and b.get("text"):
                        emitir("texto", b["text"])
                    elif b.get("type") == "tool_use":
                        estado["pendientes"][b.get("id")] = (b.get("name") or "", b.get("input"))
            elif tipo == "user":
                for b in (evento.get("message") or {}).get("content") or []:
                    if isinstance(b, dict) and b.get("type") == "tool_result":
                        nombre, args = estado["pendientes"].pop(b.get("tool_use_id"), ("?", {}))
                        herramienta(nombre, args, b.get("content"), bool(b.get("is_error")))
            elif tipo == "result":
                u = evento.get("usage") or {}
                emitir("uso", {"entrada": sum(u.get(k) or 0 for k in ("input_tokens", "cache_creation_input_tokens",
                                                                         "cache_read_input_tokens")),
                               "salida": u.get("output_tokens") or 0, "costo_usd": None})
                if evento.get("is_error") or evento.get("subtype") != "success":
                    error(f"Claude Code terminó con error: {evento.get('result') or evento.get('subtype')}")
        elif self.tipo == "opencode":
            self.sesion = evento.get("sessionID") or self.sesion
            parte = evento.get("part") or {}
            if tipo == "text" and parte.get("text"):
                emitir("texto", parte["text"])
            elif tipo == "tool_use":
                st = parte.get("state") or {}
                if st.get("status") in ("completed", "error"):
                    texto = st.get("output") if st.get("status") == "completed" else st.get("error")
                    imagenes = [{"type": "image", "data": a["url"].split(",", 1)[1]} for a in st.get("attachments") or []
                                if str(a.get("url", "")).startswith("data:image/")]
                    herramienta(parte.get("tool") or "?", st.get("input"),
                                [{"type": "text", "text": texto or ""}, *imagenes], st.get("status") == "error")
            elif tipo == "step_finish":
                t = parte.get("tokens") or {}
                cache = t.get("cache") or {}
                emitir("uso", {"entrada": (t.get("input") or 0) + (cache.get("read") or 0) + (cache.get("write") or 0),
                               "salida": (t.get("output") or 0) + (t.get("reasoning") or 0), "costo_usd": None})
            elif tipo == "error":
                e = evento.get("error") or {}
                error("OpenCode: " + str((e.get("data") or {}).get("message") or e.get("message") or e.get("name")
                                         or e))
        else:
            item = evento.get("item") or {}
            if tipo == "thread.started":
                self.sesion = evento.get("thread_id") or self.sesion
            elif tipo == "item.completed" and item.get("type") == "agent_message" and item.get("text"):
                emitir("texto", item["text"])
            elif tipo == "item.completed" and item.get("type") == "mcp_tool_call":
                fallo = item.get("error") or {}
                herramienta(item.get("tool") or "?", item.get("arguments"),
                            (item.get("result") or {}).get("content") or fallo.get("message") or "",
                            item.get("status") == "failed" or bool(fallo))
            elif tipo == "turn.completed":
                u = evento.get("usage") or {}
                emitir("uso", {"entrada": u.get("input_tokens") or 0, "salida": u.get("output_tokens") or 0,
                               "costo_usd": None})
            elif tipo in ("turn.failed", "error"):
                error("Codex: " + str((evento.get("error") or {}).get("message") or evento.get("message") or evento))

    # ------------------------------------------------------------ un pedido
    def correr(self, texto, sistema, modo, al_evento=None, cancelado=None):
        """Lanza el CLI con el pedido por stdin y emite sus eventos. Devuelve {"motivo", "uso"} como `bucle.correr`.

        `cancelado()` se consulta cada 0,1 s: si da True, se mata el árbol de procesos y el motivo es «cancelado».
        Los archivos temporales (config MCP y prompt de sistema) se borran al terminar, pase lo que pase.
        """
        resultado = {"motivo": "fin", "uso": {"entrada": 0, "salida": 0, "costo_usd": None}}
        estado = {"pendientes": {}, "error": ""}

        def emitir(tipo, datos):
            if tipo == "uso":
                for k in ("entrada", "salida"):
                    resultado["uso"][k] += datos[k]
            if al_evento is not None:
                al_evento(tipo, datos)

        with tempfile.TemporaryDirectory(prefix="omnicad_agente_", ignore_cleanup_errors=True) as carpeta:
            ruta_sistema = os.path.join(carpeta, "sistema.md")
            with open(ruta_sistema, "w", encoding="utf-8") as f:
                f.write(sistema)
            argv, extra = self.argumentos(modo, carpeta, ruta_sistema)
            try:
                # cwd en la carpeta temporal: el agente no lee ni toca archivos de donde se abrió OmniCAD
                self.proceso = proceso = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                           cwd=carpeta, env={**os.environ, **extra}, **LANZAR)
            except OSError as e:
                raise ErrorProveedor(f"No se pudo lanzar {self.nombre} ({self.ruta}): {e}") from None
            errores = deque(maxlen=40)
            lector = threading.Thread(target=lambda: errores.extend(
                l.decode("utf-8", "replace").rstrip() for l in proceso.stderr), daemon=True)
            lector.start()

            def vigilar():
                while proceso.poll() is None:
                    if cancelado is not None and cancelado():
                        matar(proceso)
                        return
                    time.sleep(0.1)

            threading.Thread(target=vigilar, daemon=True).start()

            def escribir():   # en su hilo: si el CLI imprime mucho antes de leer stdin, nadie se traba
                try:
                    proceso.stdin.write(texto.encode("utf-8"))
                    proceso.stdin.close()
                except OSError:
                    pass   # el CLI terminó antes de leer (no instalado bien, sin login): lo dice stderr

            escritor = threading.Thread(target=escribir, daemon=True)
            escritor.start()
            try:
                for linea in proceso.stdout:
                    try:
                        evento = json.loads(linea)
                    except ValueError:
                        continue   # líneas de log sueltas
                    if isinstance(evento, dict):
                        self.traducir(evento, estado, emitir)
            except BaseException:
                matar(proceso)     # una salida rara que rompa traducir() no deja el CLI corriendo solo
                raise
            proceso.wait()
            escritor.join(5)
            lector.join(5)
        if cancelado is not None and cancelado():
            resultado["motivo"] = "cancelado"
        elif estado["error"] or proceso.returncode != 0:
            if not estado["error"]:
                detalle = " ".join(errores)[-500:] or f"código de salida {proceso.returncode}"
                emitir("error", f"{self.nombre} terminó con error: {detalle}")
            if NO_LOGUEADO.search(" ".join(errores) + estado["error"]):
                emitir("error", f"¿{self.nombre} está logueado? Abrí una terminal, corré «{AGENTES[self.tipo][1]}» "
                                "y entrá con tu cuenta.")
            resultado["motivo"] = "error"
        return resultado

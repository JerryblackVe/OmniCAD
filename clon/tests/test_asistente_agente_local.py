# -*- coding: utf-8 -*-
"""Modo suscripción del Asistente (IA-6, asistente/proveedores/agente_local.py) SIN lanzar procesos reales:
`subprocess.Popen` parcheado y alimentado con salidas JSON de cada CLI.

Las líneas de OpenCode y el `init` de Claude Code son recortes de corridas reales del 2026-10-25 (opencode 1.19.3,
claude 2.1.296). Los mensajes de herramientas de Claude siguen el formato stream-json del Agent SDK; los de Codex,
el esquema de `codex exec --json` de su documentación (Codex no está instalado en esta PC).
"""
import asyncio
import io
import json
import os
import sys
import threading

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from omnicad.asistente import config  # noqa: E402
from omnicad.asistente.herramientas import Herramientas  # noqa: E402
from omnicad.asistente.proveedores import agente_local  # noqa: E402
from omnicad.asistente.proveedores.agente_local import AgenteLocal  # noqa: E402
from omnicad.asistente.proveedores.base import ErrorProveedor  # noqa: E402
# importado acá: importarlo por primera vez desde el hilo del pedido se colgó (2026-10-25, causa sin investigar)
from omnicad.servidor_mcp.puente_cliente import ClientePuente  # noqa: E402
from omnicad.servidor_mcp.servidor import crear_servidor  # noqa: E402

TOKEN = "TOKEN-SECRETO-DEL-PUENTE-1234567890"
PNG = "iVBORw0KGgo="          # cabecera PNG en base64: alcanza para probar que la imagen llega al panel
CAJA_OK = json.dumps({"ok": True, "result": {"feature": {"id": "op1", "name": "Caja1", "type": "primitiva"}},
                      "avisos": []})

OPENCODE = [
    {"type": "step_start", "sessionID": "ses_A1", "part": {"type": "step-start"}},
    {"type": "tool_use", "sessionID": "ses_A1", "part": {"type": "tool", "tool": "omnicad_create_box", "state": {
        "status": "completed", "input": {"length": 10, "width": 10, "height": 10}, "output": CAJA_OK}}},
    {"type": "tool_use", "sessionID": "ses_A1", "part": {"type": "tool", "tool": "omnicad_get_viewport_image",
                                                         "state": {"status": "completed", "input": {},
                                                                   "output": json.dumps({"ok": True, "result": {}}),
                                                                   "attachments": [{"type": "file", "mime": "image/png",
                                                                                    "url": "data:image/png;base64," + PNG}]}}},
    {"type": "step_finish", "sessionID": "ses_A1", "part": {"type": "step-finish", "tokens": {
        "total": 89556, "input": 183, "output": 29, "reasoning": 0, "cache": {"write": 0, "read": 89344}}, "cost": 0}},
    {"type": "text", "sessionID": "ses_A1", "part": {"type": "text", "text": "Caja de 10 × 10 × 10 mm creada."}},
    {"type": "step_finish", "sessionID": "ses_A1", "part": {"type": "step-finish", "tokens": {
        "input": 657, "output": 21, "reasoning": 0, "cache": {"write": 0, "read": 89472}}, "cost": 0}},
]
CLAUDE = [
    {"type": "system", "subtype": "hook_started", "session_id": "uuid-1"},
    {"type": "system", "subtype": "init", "session_id": "uuid-1", "model": "claude-sonnet-5-5",
     "mcp_servers": [{"name": "omnicad", "status": "connected", "source": "dynamic"}]},
    {"type": "assistant", "session_id": "uuid-1", "message": {"content": [
        {"type": "text", "text": "Creo la caja."},
        {"type": "tool_use", "id": "tu1", "name": "mcp__omnicad__create_box", "input": {"length": 10}}]}},
    {"type": "user", "session_id": "uuid-1", "message": {"content": [
        {"type": "tool_result", "tool_use_id": "tu1", "is_error": False, "content": [
            {"type": "text", "text": CAJA_OK},
            {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": PNG}}]}]}},
    {"type": "assistant", "session_id": "uuid-1", "message": {"content": [{"type": "text", "text": "Listo."}]}},
    {"type": "result", "subtype": "success", "is_error": False, "session_id": "uuid-1", "total_cost_usd": 0.03,
     "usage": {"input_tokens": 10, "cache_creation_input_tokens": 100, "cache_read_input_tokens": 1000,
               "output_tokens": 50}},
]
CODEX = [
    {"type": "thread.started", "thread_id": "0199a213-81c0"},
    {"type": "turn.started"},
    {"type": "item.completed", "item": {"id": "item_1", "type": "mcp_tool_call", "server": "omnicad",
                                        "tool": "create_box", "arguments": {"length": 10}, "status": "completed",
                                        "result": {"content": [{"type": "text", "text": CAJA_OK}]}}},
    {"type": "item.completed", "item": {"id": "item_2", "type": "agent_message", "text": "Hecho."}},
    {"type": "turn.completed", "usage": {"input_tokens": 2000, "cached_input_tokens": 1500, "output_tokens": 40}},
]


class ProcesoFalso:
    """Lo que devuelve Popen: stdout con las líneas JSON grabadas, stdin que guarda lo que manda OmniCAD."""
    pid = 4242

    def __init__(self, lineas, returncode=0, stderr=b"", colgado=False):
        self.lineas = [(json.dumps(e) + "\n").encode() if isinstance(e, dict) else e for e in lineas]
        self.stdin = io.BytesIO()
        self.stdin.close = lambda: None          # para leer lo escrito después de cerrarlo
        self.stderr = io.BytesIO(stderr)
        self.returncode = None
        self._final = returncode
        self.muerto = threading.Event()
        self.colgado = colgado

    @property
    def stdout(self):
        yield from self.lineas
        if self.colgado:                         # un CLI trabajando: no termina hasta que lo matan
            self.muerto.wait(5)
            self._final = 1
        self.returncode = self._final

    def poll(self):
        return self.returncode

    def wait(self, timeout=None):
        return self.returncode


@pytest.fixture
def lanzar(monkeypatch, tmp_path):
    """Parchea which (CLI «instalado») y Popen; devuelve la lista de lanzamientos: (argv, kwargs, proceso)."""
    monkeypatch.setattr(agente_local.shutil, "which", lambda nombre: f"C:/bin/{nombre}.cmd")
    puente = tmp_path / "puente"
    puente.mkdir()
    (puente / "puente.json").write_text(json.dumps({"port": 27191, "token": TOKEN}), encoding="utf-8")
    monkeypatch.setenv("OMNICAD_PUENTE_DIR", str(puente))
    class Lanzados(list):
        respuestas = None

    lanzados = Lanzados()
    respuestas = []

    def popen(argv, **kw):
        archivos = {n: open(os.path.join(kw["cwd"], n), encoding="utf-8").read() for n in os.listdir(kw["cwd"])}
        proceso = respuestas.pop(0)
        lanzados.append({"argv": argv, "kw": kw, "proceso": proceso, "archivos": archivos})
        return proceso

    monkeypatch.setattr(agente_local.subprocess, "Popen", popen)
    lanzados.respuestas = respuestas
    return lanzados


def correr(agente, lanzar, proceso, modo="hacer", texto="Creá una caja de 10 mm", cancelado=None):
    lanzar.respuestas.append(proceso)
    eventos = []
    r = agente.correr(texto, "SISTEMA DE PRUEBA", modo, lambda t, d: eventos.append((t, d)), cancelado)
    return r, eventos


# ---------------------------------------------------------------- de la salida JSON a los eventos del panel
def test_opencode_traduce_texto_herramientas_imagen_y_uso(lanzar):
    a = AgenteLocal("opencode", modelo="openai/gpt-6.1-sol", variante="high")
    r, eventos = correr(a, lanzar, ProcesoFalso(OPENCODE))
    herr = [d for t, d in eventos if t == "herramienta"]
    assert [h["nombre"] for h in herr] == ["create_box", "get_viewport_image"]
    assert herr[0]["args"] == {"length": 10, "width": 10, "height": 10}
    assert herr[0]["respuesta"]["result"]["feature"]["id"] == "op1"
    assert [d for t, d in eventos if t == "texto"] == ["Caja de 10 × 10 × 10 mm creada."]
    assert [d.png[:4] for t, d in eventos if t == "imagen"] == [b"\x89PNG"]
    assert r == {"motivo": "fin", "uso": {"entrada": 183 + 89344 + 657 + 89472, "salida": 50, "costo_usd": None}}
    assert a.sesion == "ses_A1"


def test_claude_traduce_eventos_sesion_imagen_y_uso_sin_costo(lanzar):
    a = AgenteLocal("claude_code")
    r, eventos = correr(a, lanzar, ProcesoFalso(CLAUDE))
    assert [t for t, _ in eventos] == ["texto", "herramienta", "imagen", "texto", "uso"]
    h = eventos[1][1]
    assert h["nombre"] == "create_box" and h["respuesta"]["ok"] and h["args"] == {"length": 10}
    assert eventos[-1][1] == {"entrada": 1110, "salida": 50, "costo_usd": None}   # suscripción: sin USD
    assert r["motivo"] == "fin" and a.sesion == "uuid-1"


def test_codex_traduce_eventos_del_esquema_documentado(lanzar):
    a = AgenteLocal("codex")
    r, eventos = correr(a, lanzar, ProcesoFalso(CODEX))
    assert [t for t, _ in eventos] == ["herramienta", "texto", "uso"]
    assert eventos[0][1]["nombre"] == "create_box" and eventos[0][1]["respuesta"]["ok"]
    assert r["uso"] == {"entrada": 2000, "salida": 40, "costo_usd": None} and a.sesion == "0199a213-81c0"


def test_call_tool_se_muestra_con_el_nombre_real(lanzar):
    """IA-11: el CLI llama call_tool(name, args); el panel muestra la herramienta de verdad."""
    salida = [{**CODEX[2], "item": {**CODEX[2]["item"], "tool": "call_tool",
                                    "arguments": {"name": "set_appearance", "args": {"color": "#ff0000"}}}}]
    _r, eventos = correr(AgenteLocal("codex"), lanzar, ProcesoFalso(salida))
    assert eventos[0][1]["nombre"] == "set_appearance" and eventos[0][1]["args"] == {"color": "#ff0000"}


def test_claude_sin_conexion_mcp_y_herramienta_con_error(lanzar):
    salida = [{"type": "system", "subtype": "init", "session_id": "s",
               "mcp_servers": [{"name": "omnicad", "status": "failed"}]},
              {"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "t", "name": "mcp__omnicad__x",
                                                             "input": {}}]}},
              {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "t", "is_error": True,
                                                        "content": "MCP error -32001: Request timed out"}]}},
              b"linea de log que no es JSON\n",
              {"type": "result", "subtype": "success", "is_error": False, "usage": {}}]
    r, eventos = correr(AgenteLocal("claude_code"), lanzar, ProcesoFalso(salida))
    assert "no pudo conectarse con OmniCAD" in eventos[0][1]
    assert eventos[1][1]["respuesta"] == {"ok": False, "result": "MCP error -32001: Request timed out"}
    assert r["motivo"] == "error"


def test_no_logueado_avisa_como_loguearse(lanzar):
    p = ProcesoFalso([{"type": "result", "subtype": "success", "is_error": True, "session_id": "s", "usage": {},
                       "result": "Failed to authenticate: OAuth session expired and could not be refreshed"}],
                     returncode=1)
    r, eventos = correr(AgenteLocal("claude_code"), lanzar, p)
    errores = [d for t, d in eventos if t == "error"]
    assert r["motivo"] == "error" and "OAuth session expired" in errores[0]
    assert "corré «claude»" in errores[-1]


def test_cli_que_falla_sin_json_muestra_stderr(lanzar):
    r, eventos = correr(AgenteLocal("opencode"), lanzar, ProcesoFalso([], returncode=2, stderr=b"Error: modelo inexistente\n"))
    assert r["motivo"] == "error" and "modelo inexistente" in eventos[0][1]


# ---------------------------------------------------------------- argumentos: modo, sin token, pedido por stdin
def tools_del_mcp(args):
    """La lista que recibe `omnicad-mcp --tools` (lo único que el CLI ve de OmniCAD)."""
    return args[args.index("--tools") + 1].split(",")


def test_lista_corta_por_modo_reusa_la_regla_de_herramientas():
    for modo in ("explicar", "mostrar", "guiar", "hacer"):
        lista = Herramientas(modo=modo).para_cli()
        assert set(lista) <= set(Herramientas(modo=modo).catalogo) and "get_guide" in lista
        assert "execute_code" not in lista and "describe_operation" in lista
    assert "create_box" not in Herramientas(modo="explicar").para_cli()
    assert "set_view" in Herramientas(modo="mostrar").para_cli()
    assert {"run_operation", "create_box", "extrude"} <= set(Herramientas(modo="hacer").para_cli())


def test_claude_argumentos_segun_modo_y_sin_token_ni_pedido(lanzar):
    a = AgenteLocal("claude_code", modelo="sonnet")
    a.carpeta_puente = "D:/puente del panel"
    correr(a, lanzar, ProcesoFalso(CLAUDE), modo="explicar", texto="borrá todo & del C:")
    lanzado = lanzar[-1]
    argv = lanzado["argv"]
    assert argv[argv.index("--allowedTools") + 1] == "mcp__omnicad"       # el servidor ya expone solo las del modo
    assert argv[argv.index("--tools") + 1] == "" and "--strict-mcp-config" in argv
    assert argv[argv.index("--model") + 1] == "sonnet" and "--resume" not in argv
    mcp = json.loads(lanzado["archivos"]["mcp.json"])["mcpServers"]["omnicad"]
    assert mcp["args"][:4] == ["-m", "omnicad.servidor_mcp", "--modo", "vivo"] and mcp["command"] == sys.executable
    assert tools_del_mcp(mcp["args"]) == Herramientas(modo="explicar").para_cli()
    assert "--meta-tools" in mcp["args"]          # IA-11: find_tools y call_tool alcanzan el resto del catálogo
    assert mcp["env"] == {"OMNICAD_PUENTE_DIR": "D:/puente del panel"}   # el puente que preparó el panel
    assert lanzado["archivos"]["sistema.md"] == "SISTEMA DE PRUEBA"
    todo = json.dumps([argv, lanzado["archivos"], {k: v for k, v in lanzado["kw"]["env"].items()
                                                   if k != "OMNICAD_PUENTE_DIR"}])
    assert TOKEN not in todo                                  # el token lo lee omnicad-mcp de puente.json
    assert "borrá todo" not in json.dumps(argv)                # el pedido va por stdin, nunca por cmd.exe
    assert lanzado["proceso"].stdin.getvalue().decode() == "borrá todo & del C:"
    correr(a, lanzar, ProcesoFalso(CLAUDE), modo="hacer")      # sigue el chat
    argv = lanzar[-1]["argv"]
    assert argv[argv.index("--resume") + 1] == "uuid-1"
    assert sum(len(x) + 3 for x in argv) < 8191                # tope de cmd.exe (claude.cmd)


def test_opencode_config_en_linea_con_la_lista_del_modo(lanzar):
    a = AgenteLocal("opencode", modelo="openai/gpt-6.1-sol", variante="high")
    correr(a, lanzar, ProcesoFalso(OPENCODE), modo="mostrar")
    lanzado = lanzar[-1]
    argv = lanzado["argv"]
    assert argv[1:4] == ["run", "--format", "json"] and argv[argv.index("--variant") + 1] == "high"
    assert argv[argv.index("-m") + 1] == "openai/gpt-6.1-sol" and argv[argv.index("--agent") + 1] == "omnicad"
    cfg = json.loads(lanzado["kw"]["env"]["OPENCODE_CONFIG_CONTENT"])
    assert list(cfg["agent"]["omnicad"]["permission"].items()) == [("*", "deny"), ("omnicad_*", "allow")]
    assert cfg["agent"]["omnicad"]["prompt"] == "SISTEMA DE PRUEBA"
    comando = cfg["mcp"]["omnicad"]["command"]
    assert tools_del_mcp(comando) == Herramientas(modo="mostrar").para_cli() and TOKEN not in json.dumps(cfg)
    assert cfg["mcp"]["omnicad"]["environment"] == {"OMNICAD_PUENTE_DIR": os.environ["OMNICAD_PUENTE_DIR"]}
    correr(a, lanzar, ProcesoFalso(OPENCODE), modo="guiar")
    assert lanzar[-1]["argv"][lanzar[-1]["argv"].index("-s") + 1] == "ses_A1"


def test_codex_argumentos_coinciden_con_su_help(lanzar):
    a = AgenteLocal("codex")
    correr(a, lanzar, ProcesoFalso(CODEX), modo="explicar")
    argv = lanzar[-1]["argv"]
    # `codex exec --help` (codex-cli 0.164.0-alpha.11.1): --json, --skip-git-repo-check, -c; prompt «-» = stdin
    assert argv[1:4] == ["exec", "--json", "--skip-git-repo-check"] and argv[-1] == "-"
    assert 'sandbox_mode="read-only"' in argv and "--sandbox" not in argv
    # Codex no le pasa el entorno al MCP: la carpeta del puente va explícita (si no, iría a otra OmniCAD abierta)
    assert f"mcp_servers.omnicad.env={{OMNICAD_PUENTE_DIR = {json.dumps(os.environ['OMNICAD_PUENTE_DIR'])}}}" in argv
    assert 'mcp_servers.omnicad.default_tools_approval_mode="approve"' in argv   # aprueba la tarjeta del panel
    args = json.loads(next(x for x in argv if x.startswith("mcp_servers.omnicad.args=")).split("=", 1)[1])
    assert tools_del_mcp(args) == Herramientas(modo="explicar").para_cli()
    correr(a, lanzar, ProcesoFalso(CODEX), modo="hacer")
    argv = lanzar[-1]["argv"]
    # `codex exec resume --help`: [OPTIONS] [SESSION_ID] [PROMPT]; resume no acepta --sandbox
    assert argv[1:3] == ["exec", "resume"] and argv[-2:] == ["0199a213-81c0", "-"]


def test_codex_de_la_store_fuera_del_path(monkeypatch, tmp_path):
    exe = tmp_path / "OpenAI.Codex_1.2.3_x64__abc" / "app" / "resources" / "codex.exe"
    exe.parent.mkdir(parents=True)
    exe.write_bytes(b"")
    llamadas = []

    def run(argv, **kw):
        llamadas.append(argv)
        return agente_local.subprocess.CompletedProcess(argv, 0, (str(exe.parents[2]) + "\r\n").encode(), b"")

    monkeypatch.setattr(agente_local.shutil, "which", lambda nombre: None)
    monkeypatch.setattr(agente_local.os, "name", "nt")
    monkeypatch.setattr(agente_local.subprocess, "run", run)
    agente_local.codex_de_la_store.cache_clear()
    try:
        assert agente_local.ejecutable("codex") == str(exe)
        assert agente_local.ejecutable("codex") == str(exe) and len(llamadas) == 1   # PowerShell una sola vez
        assert llamadas[0][0] == "powershell" and "Get-AppxPackage -Name OpenAI.Codex" in llamadas[0][-1]
        assert agente_local.ejecutable("claude_code") is None and len(llamadas) == 1  # solo para Codex
        assert agente_local.ejecutable("codex", "D:/otro/codex.exe") is None          # ruta de Preferencias: manda
        agente_local.codex_de_la_store.cache_clear()
        monkeypatch.setattr(agente_local.subprocess, "run",
                            lambda argv, **kw: agente_local.subprocess.CompletedProcess(argv, 0, b"\r\n", b""))
        assert agente_local.ejecutable("codex") is None                               # sin la app de la Store
    finally:
        agente_local.codex_de_la_store.cache_clear()


def test_archivos_temporales_se_borran_al_terminar(lanzar):
    correr(AgenteLocal("claude_code"), lanzar, ProcesoFalso(CLAUDE))
    carpeta = lanzar[-1]["kw"]["cwd"]
    assert set(lanzar[-1]["archivos"]) == {"mcp.json", "sistema.md"} and not os.path.exists(carpeta)


def test_valores_que_cmd_interpretaria_se_rechazan(lanzar):
    with pytest.raises(ErrorProveedor, match="Valor inválido"):
        AgenteLocal("opencode", modelo="x & calc")
    a = AgenteLocal("claude_code")
    a.sesion = "id & calc"                       # una sesión rara no llega a la línea de comandos
    correr(a, lanzar, ProcesoFalso(CLAUDE))
    assert "--resume" not in lanzar[-1]["argv"]


# ---------------------------------------------------------------- cancelar y ejecutable ausente
def test_cancelar_mata_el_arbol_de_procesos(lanzar, monkeypatch):
    p = ProcesoFalso([CLAUDE[1]], colgado=True)
    matados = []
    monkeypatch.setattr(agente_local, "matar", lambda proc: (matados.append(proc.pid), proc.muerto.set()))
    pedido = threading.Event()
    r, eventos = correr(AgenteLocal("claude_code"), lanzar, p,
                        cancelado=lambda: pedido.is_set() or bool(pedido.set()))   # cancela al primer vistazo
    assert matados == [4242] and r["motivo"] == "cancelado"
    assert not [d for t, d in eventos if t == "error"]       # cancelar no es un error
    assert not os.path.exists(lanzar[-1]["kw"]["cwd"])


def test_matar_usa_taskkill_con_el_arbol_en_windows(monkeypatch):
    llamados = []
    monkeypatch.setattr(agente_local.os, "name", "nt")
    monkeypatch.setattr(agente_local.subprocess, "run", lambda argv, **kw: llamados.append(argv))
    proc = ProcesoFalso([])
    agente_local.matar(proc)
    assert llamados == [["taskkill", "/T", "/F", "/PID", "4242"]]
    proc.returncode = 0
    agente_local.matar(proc)                     # ya terminó: no se llama de nuevo
    assert len(llamados) == 1


def test_ejecutable_ausente_mensaje_claro(monkeypatch):
    monkeypatch.setattr(agente_local.shutil, "which", lambda nombre: None)
    with pytest.raises(ErrorProveedor, match="Claude Code no está instalado"):
        config.crear_proveedor({"proveedor": "claude_code"})
    with pytest.raises(ErrorProveedor, match="en «D:/no/existe.exe»"):
        config.crear_proveedor({"proveedor": "codex", "ruta_codex": "D:/no/existe.exe"})


def test_crear_proveedor_arma_el_agente_con_ruta_modelo_y_variante(monkeypatch):
    monkeypatch.setattr(agente_local.shutil, "which", lambda nombre: nombre if nombre.endswith(".exe") else None)
    a = config.crear_proveedor({"proveedor": "opencode", "ruta_opencode": "D:/oc/opencode.exe", "variante": " high ",
                                "modelo": ""})
    assert (a.ruta, a.modelo, a.variante) == ("D:/oc/opencode.exe", "openai/gpt-6.1-sol", "high")
    c = config.crear_proveedor({"proveedor": "claude_code", "ruta_claude_code": "C:/c/claude.exe", "variante": "high"})
    assert (c.modelo, c.variante) == ("", "")   # la variante es solo de OpenCode


# ---------------------------------------------------------------- en la ventana: puente temporal y tarjeta Aplicar
@pytest.fixture(scope="module")
def ventana(tmp_path_factory):
    from PySide6.QtCore import QSettings
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication

    from omnicad.ui.preferencias import Preferencias
    from omnicad.ui.ventana import VentanaPrincipal
    QApplication.instance() or QApplication([])
    carpeta = tmp_path_factory.mktemp("agente_local")
    v = VentanaPrincipal(prefs=Preferencias(QSettings(str(carpeta / "prefs.ini"), QSettings.IniFormat)))
    v.show()
    v.mostrar_asistente(True)
    v.asistente.puente.archivo = carpeta / "puente.json"
    yield v
    v.doc.modificado = False
    v.close()
    v.deleteLater()
    QTest.qWait(1)


class AgenteFalso(AgenteLocal):
    """Hace lo que haría el CLI: llama herramientas por el puente en vivo (TCP + token de puente.json)."""

    def __init__(self, archivo, llamadas):
        self.tipo, self.nombre, self.sesion, self.proceso = "claude_code", "Claude Code", None, None
        self.archivo, self.llamadas, self.respuestas, self.sesiones = archivo, llamadas, [], []

    def correr(self, texto, sistema, modo, al_evento=None, cancelado=None, adjuntos=()):
        self.sesiones.append(self.sesion)
        cliente = ClientePuente(self.archivo)
        for nombre, args in self.llamadas:
            r = cliente.llamar(nombre, args)
            self.respuestas.append(r)
            al_evento("herramienta", {"nombre": nombre, "args": args, "respuesta": r})
        cliente.cerrar()
        self.sesion = "sesion-claude-1"
        return {"motivo": "fin", "uso": {"entrada": 0, "salida": 0, "costo_usd": None}}


def pedir(v, agente, modo, decidir=None, texto="caja"):
    """Manda un pedido con el CLI simulado; `decidir` = "aplicar" o "cancelar" en cada tarjeta (clic real)."""
    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtTest import QTest
    from omnicad.timeline.documento import Documento
    p = v.asistente
    v.set_documento(Documento())
    p.crear_proveedor = lambda cfg: agente
    p.modo.setCurrentIndex(p.modo.findData(modo))
    clics = []

    def clic():                                  # corre adentro del bucle de la tarjeta, como la persona
        if decidir and p.tarjeta is not None and p.tarjeta.pendiente:
            clics.append(p.tarjeta)
            QTest.mouseClick(p.tarjeta.b_aplicar if decidir == "aplicar" else p.tarjeta.b_cancelar, Qt.LeftButton)

    reloj = QTimer(interval=40, timeout=clic)
    reloj.start()
    p.campo.setPlainText(texto)
    from PySide6.QtWidgets import QLabel
    assert p.enviar(), [w.text() for w in p.lista.findChildren(QLabel)][-3:]
    for _ in range(400):
        if not p.trabajando:
            break
        QTest.qWait(20)
    reloj.stop()
    assert not p.trabajando, ([w.text() for w in p.lista.findChildren(QLabel)][-4:], clics, getattr(agente, "respuestas", None))
    return clics


CAJA = ("create_box", {"length": 10, "width": 10, "height": 10})


class AgenteMeta(AgenteFalso):
    """Como un CLI con `omnicad-mcp --meta-tools --modo vivo`: cada herramienta va por call_tool del servidor MCP."""

    def correr(self, texto, sistema, modo, al_evento=None, cancelado=None, adjuntos=()):
        servidor = crear_servidor(modo="vivo", cliente=ClientePuente(self.archivo), meta=True, herramientas=[])
        try:
            for nombre, args in self.llamadas:
                r = asyncio.run(servidor.call_tool("call_tool", {"name": nombre, "args": args}))
                self.respuestas.append(json.loads(r.content[0].text))
                al_evento("herramienta", {"nombre": nombre, "args": args, "respuesta": self.respuestas[-1]})
        finally:
            servidor.cerrar()
        return {"motivo": "fin", "uso": {"entrada": 0, "salida": 0, "costo_usd": None}}


def test_call_tool_en_hacer_pide_aplicar_con_el_nombre_real(ventana):
    p = ventana.asistente
    vistos, original = [], p._aprobar_en_vivo
    p._aprobar_en_vivo = lambda pedidos: vistos.extend(x.nombre for x in pedidos) or original(pedidos)
    try:
        agente = AgenteMeta(p.puente.archivo, [CAJA, ("set_appearance", {"bodies": ["op1.c1"], "color": "#ff0000"})])
        assert len(pedir(ventana, agente, "hacer", "aplicar")) == 1
    finally:
        p._aprobar_en_vivo = original
    assert vistos == ["create_box"]                    # la tarjeta muestra la herramienta real, no «call_tool»
    assert [r["ok"] for r in agente.respuestas] == [True, True], agente.respuestas
    assert ventana.doc.operaciones and p.b_deshacer is not None and p.b_deshacer.isEnabled()   # «Deshacer este pedido»


def test_call_tool_en_explicar_bloquea_lo_que_modifica(ventana):
    agente = AgenteMeta(ventana.asistente.puente.archivo, [("get_timeline", {}), CAJA,
                                                           ("set_appearance", {"color": "#ff0000"})])
    assert pedir(ventana, agente, "explicar", "aplicar") == []
    assert [r.get("error_kind") for r in agente.respuestas] == [None, "TOOL_NOT_AVAILABLE", "TOOL_NOT_AVAILABLE"]
    assert ventana.doc.operaciones == []


def test_call_tool_no_llega_a_assistant_ask_ni_execute_code(ventana):
    agente = AgenteMeta(ventana.asistente.puente.archivo, [("assistant_ask", {"prompt": "hola"}),
                                                           ("execute_code", {"code": "1"})])
    pedir(ventana, agente, "hacer", "aplicar")
    assert [r["error_kind"] for r in agente.respuestas] == ["TOOL_NOT_AVAILABLE", "TOOL_NOT_AVAILABLE"]


def test_puente_temporal_tarjeta_aplicar_y_sesion(ventana):
    p = ventana.asistente
    archivo = p.puente.archivo
    agente = AgenteFalso(archivo, [("get_scene_info", {}), CAJA, CAJA])
    assert not p.puente.activo and not archivo.exists()
    clics = pedir(ventana, agente, "hacer", "aplicar")
    assert len(clics) == 1                       # Hacer: una tarjeta por pedido, la segunda caja sigue sola
    assert [r["ok"] for r in agente.respuestas] == [True, True, True] and len(ventana.doc.operaciones) == 2
    assert not p.puente.activo and not archivo.exists() and p.puente.filtro is None   # se apagó al terminar
    assert p._sesiones == {"claude_code": "sesion-claude-1"}
    assert agente.carpeta_puente == os.path.dirname(archivo)   # el CLI va al puente que encendió el panel
    pedir(ventana, agente, "hacer", "aplicar")
    assert agente.sesiones[-1] == "sesion-claude-1"   # el segundo pedido sigue el chat del CLI
    p.nuevo_chat()
    assert p._sesiones == {}


def test_guiar_tarjeta_por_cambio_y_cancelar_devuelve_cancelled(ventana):
    agente = AgenteFalso(ventana.asistente.puente.archivo, [CAJA, CAJA])
    assert len(pedir(ventana, agente, "guiar", "aplicar")) == 2
    agente = AgenteFalso(ventana.asistente.puente.archivo, [CAJA])
    pedir(ventana, agente, "hacer", "cancelar")
    assert agente.respuestas[0]["error_kind"] == "CANCELLED" and ventana.doc.operaciones == []


def test_explicar_rechaza_lo_que_cambia_sin_tarjeta(ventana):
    agente = AgenteFalso(ventana.asistente.puente.archivo, [("get_scene_info", {}), CAJA, ("save_document", {})])
    assert pedir(ventana, agente, "explicar", "aplicar") == []
    assert [r.get("error_kind") for r in agente.respuestas] == [None, "TOOL_NOT_AVAILABLE", "TOOL_NOT_AVAILABLE"]
    assert ventana.doc.operaciones == []


def test_puente_ya_prendido_no_se_apaga(ventana, tmp_path):
    from omnicad.ui.puente import PuenteAgentes
    ventana.puente = PuenteAgentes(ventana, archivo=tmp_path / "puente.json")
    assert ventana.puente.iniciar()
    try:
        agente = AgenteFalso(ventana.puente.archivo, [CAJA])
        pedir(ventana, agente, "hacer", "aplicar")
        assert agente.respuestas[0]["ok"] and ventana.puente.activo and ventana.puente.filtro is None
        assert not ventana.asistente.puente.activo   # usó el de la ventana, no prendió el propio
    finally:
        ventana.puente.detener()
        ventana.puente = None


def test_salida_que_rompe_el_traductor_no_deja_el_cli_corriendo(lanzar, monkeypatch):
    matados = []
    monkeypatch.setattr(agente_local, "matar", lambda proc: matados.append(proc.pid))
    monkeypatch.setattr(AgenteLocal, "traducir", lambda *a: 1 / 0)
    with pytest.raises(ZeroDivisionError):
        correr(AgenteLocal("claude_code"), lanzar, ProcesoFalso(CLAUDE))
    assert matados == [4242] and not os.path.exists(lanzar[-1]["kw"]["cwd"])

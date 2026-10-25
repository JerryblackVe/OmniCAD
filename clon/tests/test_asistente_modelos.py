# -*- coding: utf-8 -*-
"""Modelos de cada proveedor del Asistente (IA-10, asistente/modelos.py) SIN lanzar procesos ni ir a la red:
`subprocess.run` y `urlopen` parcheados con salidas grabadas el 2026-10-25 en esta PC (opencode `models --verbose`,
`codex debug models` y `~/.codex/config.toml`, recortados a pocos modelos y campos)."""
import io
import json
import subprocess
import urllib.request

import pytest

from omnicad.asistente import config, modelos  # noqa: F401 — config primero: evita el ciclo con agente_local
from omnicad.asistente.proveedores.agente_local import AgenteLocal

# opencode models --verbose: «proveedor/modelo» y su JSON con sangría de 2, uno tras otro
OPENCODE = "".join(f"{m}\n{json.dumps(d, indent=2)}\n" for m, d in [
    ("opencode/beam-free", {"id": "beam-free", "providerID": "opencode", "name": "Beam Free", "status": "active",
                            "variants": {"low": {"reasoningEffort": "low"}, "medium": {"reasoningEffort": "medium"},
                                         "high": {"reasoningEffort": "high"}}}),
    ("opencode/big-pickle", {"id": "big-pickle", "providerID": "opencode", "name": "Big Pickle", "variants": {}}),
    ("openai/gpt-6.1-sol", {"id": "gpt-6.1-sol", "providerID": "openai", "name": "GPT-6.1 Sol",
                            "variants": {"low": {}, "medium": {}, "high": {}, "xhigh": {}}}),
])
CODEX = json.dumps({"models": [
    {"slug": "gpt-6.1-sol", "display_name": "GPT-6.1-Sol", "default_reasoning_level": "low", "visibility": "list",
     "supported_reasoning_levels": [{"effort": e, "description": "…"} for e in ("low", "medium", "high", "xhigh")]},
    {"slug": "gpt-6-chat-thinking", "visibility": "hide", "supported_reasoning_levels": [{"effort": "low"}]},
    {"slug": "gpt-6-luna", "visibility": "list", "supported_reasoning_levels": [{"effort": "medium"}]},
]})
CONFIG_CODEX = 'model = "gpt-6.1-sol"\nmodel_reasoning_effort = "medium"\n\n[mcp_servers.x]\ncommand = "y"\n'


@pytest.fixture
def cli(monkeypatch, tmp_path):
    """CLI «instalados», casa propia (para ~/.codex) y `subprocess.run` que contesta lo que diga `cli.salidas`."""
    monkeypatch.setattr(modelos, "_memoria", {})
    monkeypatch.setattr(modelos, "ejecutable", lambda tipo, ruta="": f"C:/bin/{tipo}.exe")
    monkeypatch.setattr(modelos.Path, "home", lambda: tmp_path)
    (tmp_path / ".codex").mkdir()
    (tmp_path / ".codex" / "config.toml").write_text(CONFIG_CODEX, encoding="utf-8")

    class Cli:
        salidas, llamadas = {}, []

    def run(argv, **kw):
        Cli.llamadas.append((argv, kw))
        salida = Cli.salidas[argv[1]]
        if isinstance(salida, Exception):
            raise salida
        codigo, texto = salida if isinstance(salida, tuple) else (0, salida)
        return subprocess.CompletedProcess(argv, codigo, texto.encode() if codigo == 0 else b"",
                                           b"" if codigo == 0 else texto.encode())

    monkeypatch.setattr(modelos.subprocess, "run", run)
    return Cli


def test_opencode_lista_modelos_y_variantes_sin_shell_y_con_timeout(cli):
    cli.salidas = {"models": OPENCODE}
    r = modelos.modelos_disponibles("opencode")
    assert r["modelos"] == ["opencode/beam-free", "opencode/big-pickle", "openai/gpt-6.1-sol"]
    assert r["variantes"]["opencode/beam-free"] == ["low", "medium", "high"] and r["variantes"]["opencode/big-pickle"] == []
    assert r["fabrica"] == "openai/gpt-6.1-sol" and r["motivo"] == ""
    argv, kw = cli.llamadas[0]
    assert argv == ["C:/bin/opencode.exe", "models", "--verbose"] and "shell" not in kw and kw["timeout"] == modelos.ESPERA
    assert modelos.modelos_disponibles("opencode") is r and len(cli.llamadas) == 1        # en memoria
    modelos.modelos_disponibles("opencode", refrescar=True)
    assert len(cli.llamadas) == 2


def test_codex_solo_los_visibles_con_esfuerzos_y_el_de_fabrica_de_su_config(cli):
    cli.salidas = {"debug": CODEX}
    r = modelos.modelos_disponibles("codex")
    assert r["modelos"] == ["gpt-6.1-sol", "gpt-6-luna"] and r["fabrica"] == "gpt-6.1-sol · medium"
    assert r["variantes"] == {"gpt-6.1-sol": ["low", "medium", "high", "xhigh"], "gpt-6-luna": ["medium"]}
    assert cli.llamadas[0][0] == ["C:/bin/codex.exe", "debug", "models"]


def test_codex_si_el_comando_falla_usa_la_cache(cli, tmp_path):
    cli.salidas = {"debug": (1, "error: unknown subcommand")}
    (tmp_path / ".codex" / "models_cache.json").write_text(CODEX, encoding="utf-8")
    assert modelos.modelos_disponibles("codex")["modelos"] == ["gpt-6.1-sol", "gpt-6-luna"]


def test_claude_code_alias_y_nombres_sin_lanzar_nada(cli):
    r = modelos.modelos_disponibles("claude_code")
    assert r["modelos"][:3] == ["fable", "opus", "sonnet"] and "claude-opus-5-5" in r["modelos"]
    assert r["fabrica"] == "" and cli.llamadas == []


@pytest.mark.parametrize("salida, motivo", [
    (FileNotFoundError("no existe"), "FileNotFoundError"),
    (subprocess.TimeoutExpired("opencode", 20), "TimeoutExpired"),
    ((1, "Error: not logged in"), "not logged in"),
    ("{ esto no es JSON", "JSONDecodeError"),
])
def test_un_cli_que_falla_da_lista_vacia_y_motivo_y_no_queda_en_memoria(cli, salida, motivo):
    cli.salidas = {"models": salida}
    r = modelos.modelos_disponibles("opencode")
    assert r["modelos"] == [] and motivo in r["motivo"]
    cli.salidas = {"models": OPENCODE}
    assert len(modelos.modelos_disponibles("opencode")["modelos"]) == 3          # el próximo intento vuelve a probar


def test_cli_no_instalado(cli, monkeypatch):
    monkeypatch.setattr(modelos, "ejecutable", lambda tipo, ruta="": None)
    r = modelos.modelos_disponibles("codex", "D:/no/codex.exe")
    assert r["modelos"] == [] and "no se encuentra «codex»" in r["motivo"]
    assert modelos.modelos_disponibles("proveedor_raro")["motivo"].startswith("proveedor desconocido")


# ---------------------------------------------------------------- por API: GET /models, gratis
class _Respuesta(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


@pytest.fixture
def red(monkeypatch):
    pedidos = []

    def urlopen(pedido, timeout=None):
        pedidos.append((pedido.full_url, {k.lower(): v for k, v in pedido.header_items()}, pedido.get_method()))
        return _Respuesta(json.dumps({"data": [{"id": "modelo-a"}, {"id": "modelo-b"}, {"sin_id": 1}]}).encode())

    monkeypatch.setattr(modelos, "_memoria", {})
    monkeypatch.setattr(urllib.request, "urlopen", urlopen)
    for v in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OPENROUTER_API_KEY"):
        monkeypatch.delenv(v, raising=False)
    return pedidos


def test_api_lista_con_get_y_la_clave_solo_donde_va(red, monkeypatch):
    assert "falta la variable ANTHROPIC_API_KEY" in modelos.modelos_disponibles("anthropic")["motivo"] and red == []
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-x")
    assert modelos.modelos_disponibles("anthropic")["modelos"] == ["modelo-a", "modelo-b"]
    url, encabezados, metodo = red[-1]
    assert url.startswith("https://api.anthropic.com/v1/models") and encabezados["x-api-key"] == "sk-ant-x"
    assert metodo == "GET"
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai")
    modelos.modelos_disponibles("local", base_url="http://localhost:1234/v1/")
    assert red[-1][0] == "http://localhost:1234/v1/models" and "authorization" not in red[-1][1]   # no viaja
    modelos.modelos_disponibles("openai")
    assert red[-1][0] == "https://api.openai.com/v1/models" and red[-1][1]["authorization"] == "Bearer sk-openai"


# ---------------------------------------------------------------- Codex: el esfuerzo llega al CLI
def test_codex_recibe_el_esfuerzo_y_opencode_la_variante(monkeypatch):
    monkeypatch.setattr(config.agente_local, "AgenteLocal", lambda tipo, ruta, modelo, variante: (tipo, modelo, variante))
    assert config.crear_proveedor({"proveedor": "codex", "modelo": "gpt-6-luna", "variante": " high "}) == \
        ("codex", "gpt-6-luna", "high")
    assert config.crear_proveedor({"proveedor": "claude_code", "variante": "high"})[2] == ""
    a = AgenteLocal.__new__(AgenteLocal)
    a.tipo, a.ruta, a.modelo, a.variante, a.sesion, a.carpeta_puente = "codex", "C:/bin/codex.exe", "", "high", None, None
    argv, _extra = a.argumentos("explicar", "C:/tmp", "C:/tmp/sistema.md")
    assert argv[argv.index('model_reasoning_effort="high"') - 1] == "-c" and argv[-1] == "-"

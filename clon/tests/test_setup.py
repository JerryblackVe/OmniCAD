# -*- coding: utf-8 -*-
"""`omnicad setup` (conecta OmniCAD a Claude Code y OpenCode) y la skill `.claude/skills/omnicad/SKILL.md`.

Ninguna prueba toca la configuración real: todo va a una carpeta temporal (`--inicio`), HOME apunta a otra carpeta
temporal y cualquier subproceso (`claude`) está prohibido salvo el simulado de la prueba que lo pide."""
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from omnicad.cli import construir_parser, main
from omnicad.cli import cmd_setup

RAIZ = Path(__file__).resolve().parent.parent          # D:/PROGRAMA/clon
REPO = RAIZ.parent                                     # D:/PROGRAMA
SKILL = REPO / ".claude" / "skills" / "omnicad" / "SKILL.md"
PYTHON = str(Path(sys.executable).absolute()).replace("\\", "/")


@pytest.fixture(autouse=True)
def aislar(monkeypatch, tmp_path_factory):
    """HOME falso, `claude` inexistente y subprocesos prohibidos: un error de código nunca toca lo real."""
    falso = tmp_path_factory.mktemp("home_falso")
    monkeypatch.setenv("USERPROFILE", str(falso))
    monkeypatch.setenv("HOME", str(falso))
    monkeypatch.setenv("APPDATA", str(falso / "AppData" / "Roaming"))
    monkeypatch.setattr(cmd_setup, "_buscar", lambda nombre: None)

    def prohibido(*a, **k):
        raise AssertionError("se intentó correr un subproceso real")
    monkeypatch.setattr(cmd_setup, "_ejecutar", prohibido)
    return falso


@pytest.fixture
def home(tmp_path):
    carpeta = tmp_path / "usuario"
    carpeta.mkdir()
    return carpeta


def correr(capsys, *argv):
    capsys.readouterr()
    codigo = main([str(a) for a in argv])
    salida = capsys.readouterr()
    return codigo, salida.out, salida.err


def setup_json(capsys, home, *extra):
    codigo, out, _ = correr(capsys, "setup", "--inicio", home, "--json", *extra)
    return codigo, json.loads(out)


def estados(res):
    return {(a["client"], a["kind"]): a["status"] for a in res["result"]["actions"]}


def instantanea(carpeta):
    return {str(p.relative_to(carpeta)): p.read_bytes() for p in sorted(carpeta.rglob("*")) if p.is_file()}


ENTRADA_OPENCODE = {"type": "local", "command": [PYTHON, "-m", "omnicad.servidor_mcp"], "enabled": True,
                    "timeout": 30000}
ENTRADA_CLAUDE = {"type": "stdio", "command": PYTHON, "args": ["-m", "omnicad.servidor_mcp"], "env": {}}


def _escribir(ruta, datos):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(datos, indent=2), encoding="utf-8")


# ---------------------------------------------------------------- sin --aplicar: no escribe nada
def test_sin_aplicar_no_escribe_nada(capsys, home):
    codigo, res = setup_json(capsys, home, "--cliente", "todos")
    assert codigo == 0 and res["ok"] and res["result"]["applied"] is False
    assert set(estados(res).values()) == {"pending"} and len(res["result"]["actions"]) == 3   # 2 MCP + 1 skill
    assert list(home.rglob("*")) == []                  # ni carpetas ni archivos


def test_sin_aplicar_texto_dice_que_es_un_plan(capsys, home):
    codigo, out, _ = correr(capsys, "setup", "--inicio", home)
    assert codigo == 0 and "PLAN" in out and "--aplicar" in out and "omnicad.servidor_mcp" in out
    assert list(home.rglob("*")) == []


def test_sin_aplicar_con_configuracion_existente_no_la_toca(capsys, home):
    _escribir(home / ".claude.json", {"mcpServers": {"otro": {"command": "x"}}})
    _escribir(home / ".config" / "opencode" / "opencode.json", {"mcp": {"otro": {"type": "local"}}})
    antes = instantanea(home)
    correr(capsys, "setup", "--inicio", home)
    assert instantanea(home) == antes                   # ni .bak ni cambios


# ---------------------------------------------------------------- --aplicar: Claude Code
def test_aplicar_claude_code_fusiona_sin_borrar_y_respalda(capsys, home):
    original = {"numStartups": 7, "mcpServers": {"otro": {"type": "stdio", "command": "x", "args": ["-y"], "env": {}}}}
    _escribir(home / ".claude.json", original)
    bytes_originales = (home / ".claude.json").read_bytes()
    codigo, res = setup_json(capsys, home, "--cliente", "claude-code", "--aplicar")
    assert codigo == 0 and estados(res) == {("claude-code", "mcp"): "done", ("claude-code", "skill"): "done"}
    datos = json.loads((home / ".claude.json").read_text(encoding="utf-8"))
    assert datos["numStartups"] == 7                                    # lo demás intacto
    assert datos["mcpServers"]["otro"] == original["mcpServers"]["otro"]  # el otro servidor sigue
    assert datos["mcpServers"]["omnicad"] == ENTRADA_CLAUDE
    assert (home / ".claude.json.bak").read_bytes() == bytes_originales  # copia del estado previo
    assert not (home / ".config").exists()                              # solo se tocó Claude Code


def test_aplicar_claude_code_crea_el_archivo_si_no_existe(capsys, home):
    codigo, res = setup_json(capsys, home, "--cliente", "claude-code", "--aplicar")
    assert codigo == 0
    assert json.loads((home / ".claude.json").read_text(encoding="utf-8")) == {"mcpServers": {"omnicad": ENTRADA_CLAUDE}}
    assert not (home / ".claude.json.bak").exists()                     # no había nada que respaldar


# ---------------------------------------------------------------- --aplicar: OpenCode
def test_aplicar_opencode_fusiona_sin_borrar_y_respalda(capsys, home):
    ruta = home / ".config" / "opencode" / "opencode.json"
    original = {"$schema": "https://opencode.ai/config.json", "model": "x/y",
                "mcp": {"otro": {"type": "local", "command": ["a"], "enabled": False}}}
    _escribir(ruta, original)
    bytes_originales = ruta.read_bytes()
    codigo, res = setup_json(capsys, home, "--cliente", "opencode", "--aplicar")
    assert codigo == 0 and estados(res) == {("opencode", "mcp"): "done", ("opencode", "skill"): "done"}
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    assert datos["model"] == "x/y" and datos["mcp"]["otro"] == original["mcp"]["otro"]
    assert datos["mcp"]["omnicad"] == ENTRADA_OPENCODE
    assert (ruta.parent / "opencode.json.bak").read_bytes() == bytes_originales
    assert not (home / ".claude").exists()


def test_opencode_crea_opencode_json_con_esquema_si_no_hay_config(capsys, home):
    codigo, _ = setup_json(capsys, home, "--cliente", "opencode", "--aplicar")
    assert codigo == 0
    datos = json.loads((home / ".config" / "opencode" / "opencode.json").read_text(encoding="utf-8"))
    assert datos == {"$schema": "https://opencode.ai/config.json", "mcp": {"omnicad": ENTRADA_OPENCODE}}


def test_opencode_edita_el_jsonc_existente_y_no_crea_otro_archivo(capsys, home):
    ruta = home / ".config" / "opencode" / "opencode.jsonc"
    _escribir(ruta, {"mcp": {"otro": {"type": "local", "command": ["a"]}}})        # JSON estricto con extensión .jsonc
    codigo, _ = setup_json(capsys, home, "--cliente", "opencode", "--aplicar")
    assert codigo == 0
    assert set(json.loads(ruta.read_text(encoding="utf-8"))["mcp"]) == {"otro", "omnicad"}
    assert not (ruta.parent / "opencode.json").exists() and (ruta.parent / "opencode.jsonc.bak").is_file()


def test_opencode_con_comentarios_no_se_reescribe(capsys, home):
    ruta = home / ".config" / "opencode" / "opencode.jsonc"
    ruta.parent.mkdir(parents=True)
    ruta.write_text('{\n  // mis servidores\n  "mcp": {"otro": {"type": "local", "command": ["a"],},},\n}\n', encoding="utf-8")
    antes = ruta.read_bytes()
    codigo, res = setup_json(capsys, home, "--cliente", "opencode")       # plan: informa, no es una falla
    assert codigo == 0 and estados(res)[("opencode", "mcp")] == "manual"
    codigo, res = setup_json(capsys, home, "--cliente", "opencode", "--aplicar")
    assert codigo == 1 and estados(res)[("opencode", "mcp")] == "manual"   # no se pudo completar solo
    accion = next(a for a in res["result"]["actions"] if a["kind"] == "mcp")
    assert accion["merge"] == {"mcp": {"omnicad": ENTRADA_OPENCODE}} and "a mano" in accion["message"]
    assert ruta.read_bytes() == antes and not list(ruta.parent.glob("*.bak"))   # intacto y sin respaldo inútil
    assert (home / ".config" / "opencode" / "skills" / "omnicad" / "SKILL.md").is_file()  # la skill sí se copia


def test_json_roto_es_un_error_y_no_se_toca(capsys, home):
    (home / ".claude.json").write_text("{esto no es json", encoding="utf-8")
    codigo, res = setup_json(capsys, home, "--cliente", "claude-code", "--aplicar")
    assert codigo == 1 and estados(res)[("claude-code", "mcp")] == "error"
    assert (home / ".claude.json").read_text(encoding="utf-8") == "{esto no es json"
    assert estados(res)[("claude-code", "skill")] == "done"             # una falla no frena lo demás


# ---------------------------------------------------------------- idempotencia y actualización
def test_idempotente_dos_veces_no_duplica_ni_reescribe(capsys, home):
    _escribir(home / ".claude.json", {"mcpServers": {"otro": {"command": "x"}}})
    _escribir(home / ".config" / "opencode" / "opencode.json", {"mcp": {"otro": {"type": "local"}}})
    codigo, res = setup_json(capsys, home, "--aplicar")
    assert codigo == 0 and set(estados(res).values()) == {"done"}
    despues_de_la_primera = instantanea(home)
    codigo, res = setup_json(capsys, home, "--aplicar")
    assert codigo == 0 and set(estados(res).values()) == {"unchanged"}
    assert instantanea(home) == despues_de_la_primera                   # mismos archivos, mismos bytes, sin .bak nuevos
    datos = json.loads((home / ".claude.json").read_text(encoding="utf-8"))
    assert list(datos["mcpServers"]) == ["otro", "omnicad"]
    codigo, res = setup_json(capsys, home)                              # el plan posterior también dice "ya está"
    assert set(estados(res).values()) == {"unchanged"}


def test_actualiza_la_entrada_si_cambio_el_python_y_conserva_lo_demas(capsys, home):
    ruta = home / ".config" / "opencode" / "opencode.json"
    _escribir(ruta, {"mcp": {"omnicad": {"type": "local", "command": ["C:/viejo/python.exe", "-m", "omnicad.servidor_mcp"],
                                         "enabled": False, "environment": {"A": "1"}}}})
    _escribir(home / ".claude.json", {"mcpServers": {"omnicad": {"type": "stdio", "command": "C:/viejo/python.exe",
                                                                  "args": ["-m", "omnicad.servidor_mcp"], "env": {}}}})
    codigo, res = setup_json(capsys, home, "--aplicar")
    assert codigo == 0 and estados(res)[("opencode", "mcp")] == "done" and estados(res)[("claude-code", "mcp")] == "done"
    entrada = json.loads(ruta.read_text(encoding="utf-8"))["mcp"]["omnicad"]
    assert entrada["command"][0] == PYTHON                              # comando nuevo
    assert entrada["enabled"] is False and entrada["environment"] == {"A": "1"}   # lo que puso el usuario, intacto
    assert json.loads((home / ".claude.json").read_text(encoding="utf-8"))["mcpServers"]["omnicad"]["command"] == PYTHON


def test_dos_cambios_distintos_no_pisan_el_primer_respaldo(capsys, home):
    _escribir(home / ".claude.json", {"mcpServers": {"omnicad": {"command": "C:/viejo/python.exe", "args": ["-m", "omnicad.servidor_mcp"]}}})
    setup_json(capsys, home, "--cliente", "claude-code", "--aplicar")
    primero = (home / ".claude.json.bak").read_bytes()
    _escribir(home / ".claude.json", {"mcpServers": {"omnicad": {"command": "C:/otro/python.exe", "args": ["-m", "omnicad.servidor_mcp"]}}})
    setup_json(capsys, home, "--cliente", "claude-code", "--aplicar")
    assert (home / ".claude.json.bak").read_bytes() == primero          # el primer .bak sigue ahí
    assert len(list(home.glob(".claude.json.bak*"))) == 2               # y el segundo tiene su propio nombre


# ---------------------------------------------------------------- la skill se copia
def test_todos_copia_la_skill_una_sola_vez(capsys, home):
    """OpenCode también lee ~/.claude/skills: con «todos» la skill va solo ahí (dos copias = «duplicate skill name»)."""
    codigo, _ = setup_json(capsys, home, "--aplicar")
    assert codigo == 0
    destino = home / ".claude" / "skills" / "omnicad"
    assert (destino / "SKILL.md").read_bytes() == SKILL.read_bytes() and not list(destino.glob("*.bak"))
    assert not (home / ".config" / "opencode" / "skills").exists()


def test_solo_opencode_copia_la_skill_en_su_carpeta(capsys, home):
    codigo, _ = setup_json(capsys, home, "--cliente", "opencode", "--aplicar")
    assert codigo == 0
    assert (home / ".config" / "opencode" / "skills" / "omnicad" / "SKILL.md").read_bytes() == SKILL.read_bytes()


def test_skill_distinta_se_reemplaza_guardando_la_anterior(capsys, home):
    destino = home / ".claude" / "skills" / "omnicad"
    destino.mkdir(parents=True)
    (destino / "SKILL.md").write_text("version vieja", encoding="utf-8")
    codigo, res = setup_json(capsys, home, "--cliente", "claude-code", "--aplicar")
    assert codigo == 0 and estados(res)[("claude-code", "skill")] == "done"
    assert (destino / "SKILL.md").read_bytes() == SKILL.read_bytes()
    assert (destino / "SKILL.md.bak").read_text(encoding="utf-8") == "version vieja"   # *.bak no se carga como skill


def test_skill_origen_propio_y_archivos_extra(capsys, home, tmp_path):
    origen = tmp_path / "mi_skill"
    (origen / "referencias").mkdir(parents=True)
    (origen / "SKILL.md").write_text("---\nname: omnicad\ndescription: x\n---\n", encoding="utf-8")
    (origen / "referencias" / "a.md").write_text("a", encoding="utf-8")
    codigo, _ = setup_json(capsys, home, "--cliente", "claude-code", "--skill-origen", origen, "--aplicar")
    assert codigo == 0
    assert (home / ".claude" / "skills" / "omnicad" / "referencias" / "a.md").read_text(encoding="utf-8") == "a"


# ---------------------------------------------------------------- errores de uso
def test_inicio_inexistente_es_error_de_uso(capsys, tmp_path):
    codigo, out, err = correr(capsys, "setup", "--inicio", tmp_path / "no_existe", "--json")
    assert codigo == 2 and json.loads(out)["error_kind"] == "CLI_USAGE"


def test_skill_origen_sin_skill_md_es_error_de_uso(capsys, home, tmp_path):
    codigo, out, _ = correr(capsys, "setup", "--inicio", home, "--skill-origen", tmp_path, "--json")
    assert codigo == 2 and "SKILL.md" in json.loads(out)["mensaje"] and list(home.rglob("*")) == []


def test_cliente_invalido_es_error_de_uso(capsys, home):
    codigo, _, err = correr(capsys, "setup", "--inicio", home, "--cliente", "cursor")
    assert codigo == 2 and "opción inválida" in err


def test_setup_esta_en_la_ayuda(capsys):
    assert "setup" in construir_parser().format_help()
    codigo, out, _ = correr(capsys, "setup", "--help")
    assert codigo == 0 and "--aplicar" in out and "--inicio" in out and "opencode debug paths" in out


def test_el_modulo_setup_no_carga_la_api_pesada():
    r = subprocess.run([sys.executable, "-c", "import sys; import omnicad.cli.cmd_setup; "
                        "print('omnicad.api' in sys.modules)"], capture_output=True, text=True, cwd=RAIZ, timeout=60,
                       env=dict(os.environ, PYTHONPATH=str(RAIZ)))
    assert r.returncode == 0 and r.stdout.strip() == "False", r.stderr


# ---------------------------------------------------------------- con el ejecutable `claude` (simulado)
class ClaudeFalso:
    """Imita `claude mcp add|remove --scope user` escribiendo el .claude.json de la carpeta falsa."""

    def __init__(self, carpeta, codigo=0):
        self.carpeta, self.codigo, self.llamadas = carpeta, codigo, []

    def __call__(self, comando, **kw):
        self.llamadas.append(list(comando))
        if self.codigo:
            return SimpleNamespace(returncode=self.codigo, stdout="", stderr="algo falló\nno se pudo guardar")
        cfg = self.carpeta / ".claude.json"
        datos = json.loads(cfg.read_text(encoding="utf-8")) if cfg.is_file() else {}
        if comando[1:3] == ["mcp", "add"]:
            i = comando.index("--")
            datos.setdefault("mcpServers", {})[comando[5]] = {"type": "stdio", "command": comando[i + 1],
                                                              "args": comando[i + 2:], "env": {}}
        elif comando[1:3] == ["mcp", "remove"]:
            datos.get("mcpServers", {}).pop(comando[-1], None)
        cfg.write_text(json.dumps(datos), encoding="utf-8")
        return SimpleNamespace(returncode=0, stdout="", stderr="")


def test_con_claude_instalado_usa_claude_mcp_add_scope_user(capsys, monkeypatch, aislar):
    falso = ClaudeFalso(aislar)
    monkeypatch.setattr(cmd_setup, "_buscar", lambda nombre: "claude" if nombre == "claude" else None)
    monkeypatch.setattr(cmd_setup, "_ejecutar", falso)
    _escribir(aislar / ".claude.json", {"mcpServers": {"otro": {"command": "x"}}})
    previo = (aislar / ".claude.json").read_bytes()
    assert Path.home() == aislar                                        # el HOME es el falso, nunca el real
    codigo, out, _ = correr(capsys, "setup", "--cliente", "claude-code", "--json")   # plan: no corre nada
    plan = json.loads(out)
    assert falso.llamadas == [] and plan["result"]["actions"][0]["command"] == \
        ["claude", "mcp", "add", "--scope", "user", "omnicad", "--", PYTHON, "-m", "omnicad.servidor_mcp"]
    codigo, out, _ = correr(capsys, "setup", "--cliente", "claude-code", "--aplicar", "--json")
    res = json.loads(out)
    assert codigo == 0 and estados(res)[("claude-code", "mcp")] == "done"
    assert falso.llamadas == [["claude", "mcp", "add", "--scope", "user", "omnicad", "--", PYTHON, "-m", "omnicad.servidor_mcp"]]
    assert (aislar / ".claude.json.bak").read_bytes() == previo         # respaldo ANTES de que la CLI escriba
    assert set(json.loads((aislar / ".claude.json").read_text(encoding="utf-8"))["mcpServers"]) == {"otro", "omnicad"}
    codigo, out, _ = correr(capsys, "setup", "--cliente", "claude-code", "--aplicar", "--json")   # idempotente
    assert estados(json.loads(out))[("claude-code", "mcp")] == "unchanged" and len(falso.llamadas) == 1


def test_con_claude_y_entrada_vieja_la_quita_antes_de_agregar(capsys, monkeypatch, aislar):
    falso = ClaudeFalso(aislar)
    monkeypatch.setattr(cmd_setup, "_buscar", lambda nombre: "claude")
    monkeypatch.setattr(cmd_setup, "_ejecutar", falso)
    _escribir(aislar / ".claude.json", {"mcpServers": {"omnicad": {"command": "C:/viejo/python.exe", "args": ["-m", "x"]}}})
    codigo, _, _ = correr(capsys, "setup", "--cliente", "claude-code", "--aplicar")
    assert codigo == 0
    assert [c[1:3] for c in falso.llamadas] == [["mcp", "remove"], ["mcp", "add"]]
    assert falso.llamadas[0] == ["claude", "mcp", "remove", "--scope", "user", "omnicad"]
    assert json.loads((aislar / ".claude.json").read_text(encoding="utf-8"))["mcpServers"]["omnicad"]["command"] == PYTHON


def test_si_claude_falla_es_un_error_con_su_mensaje(capsys, monkeypatch, aislar):
    monkeypatch.setattr(cmd_setup, "_buscar", lambda nombre: "claude")
    monkeypatch.setattr(cmd_setup, "_ejecutar", ClaudeFalso(aislar, codigo=3))
    codigo, out, _ = correr(capsys, "setup", "--cliente", "claude-code", "--aplicar", "--json")
    accion = next(a for a in json.loads(out)["result"]["actions"] if a["kind"] == "mcp")
    assert codigo == 1 and accion["status"] == "error" and "código 3" in accion["message"] and "no se pudo guardar" in accion["message"]


def test_con_inicio_o_sin_cli_no_se_usa_claude_nunca(capsys, monkeypatch, home, aislar):
    monkeypatch.setattr(cmd_setup, "_buscar", lambda nombre: "claude")      # `claude` existe, pero no se llama
    codigo, _ = setup_json(capsys, home, "--cliente", "claude-code", "--aplicar")      # _ejecutar prohíbe subprocesos
    assert codigo == 0 and (home / ".claude.json").is_file()
    codigo, out, _ = correr(capsys, "setup", "--cliente", "claude-code", "--sin-cli", "--aplicar", "--json")
    assert codigo == 0 and (aislar / ".claude.json").is_file()              # editó a mano el HOME falso


# ---------------------------------------------------------------- SKILL.md
def _separar(texto):
    m = re.match(r"\A---\r?\n(.*?)\r?\n---\r?\n(.*)\Z", texto, re.S)
    assert m, "SKILL.md tiene que empezar con un frontmatter entre líneas ---"
    return m.group(1), m.group(2)


def _frontmatter(bloque):
    """Frontmatter mínimo `clave: valor` (valor plano o entre comillas dobles, como lo escribe esta skill)."""
    claves = {}
    for linea in bloque.splitlines():
        m = re.match(r"^([A-Za-z][\w-]*):\s*(.*)$", linea)
        assert m, f"línea de frontmatter que no es `clave: valor`: {linea[:60]}"
        valor = m.group(2).strip()
        claves[m.group(1)] = json.loads(valor) if valor.startswith('"') else valor
    return claves


def test_skill_md_tiene_frontmatter_valido():
    bloque, cuerpo = _separar(SKILL.read_text(encoding="utf-8"))
    fm = _frontmatter(bloque)
    assert set(fm) == {"name", "description"}
    assert fm["name"] == SKILL.parent.name == "omnicad"
    assert re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", fm["name"]) and len(fm["name"]) <= 64   # regla de OpenCode y Claude
    assert 100 <= len(fm["description"]) <= 1024
    for frase in ("soporte en L", "design a bracket", "STL", "OmniCAD", "NO usarla"):      # cuándo sí y cuándo no
        assert frase in fm["description"]
    assert len(SKILL.read_text(encoding="utf-8").splitlines()) <= 150


# Palabras entre comillas invertidas que NO son herramientas (vistas, valores, operadores, módulos, claves de la respuesta).
NO_HERRAMIENTAS = {"and", "or", "not", "body", "cut", "join", "new_body", "error_kind", "flujo", "selectores", "front",
                   "iso", "right", "top", "io_archivos", "mensaje", "nucleo", "omnicad", "pistas", "push", "reverse",
                   "timeline", "topic", "restricciones", "llamar"}


def _codigo_en_linea(texto):
    return re.findall(r"`([^`]+)`", texto)


def test_skill_md_cada_herramienta_nombrada_existe_en_el_catalogo():
    from omnicad import api
    catalogo = {h["nombre"] for h in api.catalogo()}
    cuerpo = _separar(SKILL.read_text(encoding="utf-8"))[1]
    sueltas = {s for s in _codigo_en_linea(cuerpo) if re.fullmatch(r"[a-z][a-z0-9_]*", s)}
    llamadas = {m.group(1) for s in _codigo_en_linea(cuerpo) if (m := re.match(r"([a-z][a-z0-9_]*)\(", s))}
    desconocidas = sorted((sueltas | llamadas) - catalogo - NO_HERRAMIENTAS)
    assert not desconocidas, (f"{desconocidas} no están en api.catalogo(): corregí el nombre en SKILL.md o, si no es una "
                              "herramienta, sumalo a NO_HERRAMIENTAS")
    nombradas = (sueltas | llamadas) & catalogo
    assert {"get_scene_info", "get_viewport_image", "get_physical_properties", "save_document", "get_guide"} <= nombradas


def _subparsers():
    parser = construir_parser()
    accion = next(a for a in parser._actions if isinstance(a, argparse._SubParsersAction))
    return accion.choices


def _opciones(parser):
    return {o for a in parser._actions for o in a.option_strings}


def test_skill_md_cada_comando_omnicad_es_un_subcomando_real_con_opciones_reales():
    subs = _subparsers()
    cuerpo = _separar(SKILL.read_text(encoding="utf-8"))[1]
    comandos = [s for s in _codigo_en_linea(cuerpo) if re.match(r"omnicad\s+[a-z]", s)]
    assert len(comandos) >= 8
    for texto in comandos:
        palabras = texto.split()
        assert palabras[1] in subs, f"`omnicad {palabras[1]}` no es un subcomando (hay: {', '.join(subs)})"
        parser = subs[palabras[1]]
        if palabras[1] == "dev":
            hijo = next(a for a in parser._actions if isinstance(a, argparse._SubParsersAction))
            assert palabras[2] in hijo.choices, f"`omnicad dev {palabras[2]}` no existe"
            parser = hijo.choices[palabras[2]]
        for opcion in re.findall(r"--[a-z][a-z-]*", texto):
            assert opcion in _opciones(parser), f"`{texto}`: {opcion} no existe en omnicad {palabras[1]}"
    assert {"tools", "describe", "new", "call", "render", "export", "batch", "run", "info", "setup", "dev"} <= \
        {t.split()[1] for t in comandos}


def test_skill_md_cada_error_kind_existe_y_cada_herramienta_de_ejemplo_acepta_sus_argumentos():
    from omnicad.api import errores
    cuerpo = _separar(SKILL.read_text(encoding="utf-8"))[1]
    kinds = {s for s in _codigo_en_linea(cuerpo) if re.fullmatch(r"[A-Z][A-Z_]+", s)}
    assert len(kinds) >= 10
    assert not kinds - set(errores.PISTAS), f"error_kind inexistentes: {sorted(kinds - set(errores.PISTAS))}"
    # Los ejemplos con la forma nombre(arg=..., ...) usan parámetros que existen en el esquema de la herramienta.
    from omnicad import api
    por_nombre = {h["nombre"]: h for h in api.catalogo()}
    for s in _codigo_en_linea(cuerpo):
        m = re.match(r"([a-z][a-z0-9_]*)\((.*)\)$", s)
        if m and m.group(1) in por_nombre:
            props = por_nombre[m.group(1)]["esquema"]["properties"]
            for arg in re.findall(r"(\w+)=", m.group(2)):
                assert arg in props, f"{s}: {m.group(1)} no tiene el parámetro {arg}"


def test_skill_md_los_enlaces_a_archivos_del_repo_existen():
    cuerpo = _separar(SKILL.read_text(encoding="utf-8"))[1]
    rutas = {r for s in _codigo_en_linea(cuerpo) for r in re.findall(r"(?:docs/agentes/)?[\w]+\.md", s)}
    assert {"docs/agentes/guia_diseno.md", "docs/agentes/conectar.md", "AGENTS.md", "PROJECT_LOG.md"} <= rutas
    for r in rutas:
        assert (REPO / r).is_file(), f"SKILL.md nombra {r} y no existe en el repo"


# ---------------------------------------------------------------- complemento de Fusion 360
def _api_fusion(home):
    api_fusion = home / "AppData" / "Roaming" / "Autodesk" / "Autodesk Fusion 360" / "API"
    api_fusion.mkdir(parents=True)
    return api_fusion / "AddIns" / "OmniCADPuente"


@pytest.mark.skipif(os.name != "nt", reason="la carpeta de Windows; macOS usa ~/Library/Application Support")
def test_fusion_instala_el_complemento_en_la_carpeta_del_usuario(capsys, home):
    destino = _api_fusion(home)
    codigo, res = setup_json(capsys, home, "--cliente", "fusion")            # plan: no escribe
    assert codigo == 0 and estados(res) == {("fusion", "addin"): "pending"} and not destino.exists()
    codigo, res = setup_json(capsys, home, "--cliente", "fusion", "--aplicar")
    assert codigo == 0 and estados(res) == {("fusion", "addin"): "done"}
    origen = cmd_setup._origen_complemento()
    assert instantanea(destino) == instantanea(origen)
    manifiesto = json.loads((destino / "OmniCADPuente.manifest").read_text(encoding="utf-8"))
    assert manifiesto["type"] == "addin" and manifiesto["runOnStartup"] is True
    codigo, res = setup_json(capsys, home, "--cliente", "fusion", "--aplicar")   # idempotente
    assert estados(res) == {("fusion", "addin"): "unchanged"}


def test_fusion_con_todos_solo_si_esta_instalado(capsys, home):
    codigo, res = setup_json(capsys, home)
    assert ("fusion", "addin") not in estados(res)
    assert any("Fusion 360 no" in a for a in res["avisos"])


def test_fusion_nunca_en_la_instalacion_de_autodesk(monkeypatch):
    monkeypatch.setattr(cmd_setup, "carpeta_addins", lambda inicio=None: Path("D:/Autodesk/API/AddIns"))
    accion, aviso = cmd_setup._accion_fusion(None, True)
    assert accion.status == "error" and "solo lectura" in accion.message and aviso is None

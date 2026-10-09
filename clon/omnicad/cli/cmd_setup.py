# -*- coding: utf-8 -*-
"""Subcomando `setup`: conecta OmniCAD a Claude Code y a OpenCode (registra el MCP y copia la skill `omnicad`) y
instala en Fusion 360 el complemento OmniCADPuente (para abrir .f3d/.f3z desde OmniCAD).

SEGURO POR DEFECTO: sin `--aplicar` solo muestra el plan y no escribe nada. Con `--aplicar`:
  - cada archivo de configuración que se modifica se respalda antes (`archivo.bak`; si ya hay uno, `.bak-FECHA`);
  - el JSON se fusiona sin tocar los demás servidores y la escritura es atómica;
  - es idempotente: lo que ya está igual da "unchanged" y no se vuelve a escribir.
`--inicio DIR` reemplaza la carpeta del usuario (las pruebas nunca tocan la configuración real).

Dónde va cada cosa (ver el epílogo de la ayuda para las fuentes):
  Claude Code: MCP con `claude mcp add --scope user` (queda en ~/.claude.json); skill en ~/.claude/skills/omnicad/.
  OpenCode:    MCP en la clave "mcp" de ~/.config/opencode/opencode.jsonc (o .json); skill en ~/.config/opencode/skills/omnicad/ (con «todos», la de ~/.claude/skills).
  Fusion 360:  complemento en la carpeta AddIns DEL USUARIO (%APPDATA%/Autodesk/Autodesk Fusion 360/API/AddIns);
               nunca en la instalación de Fusion (p. ej. D:/Autodesk, que es solo lectura).

No importa `omnicad.api` (arranque instantáneo). `_buscar` y `_ejecutar` se pueden reemplazar en las pruebas.
"""
import importlib.metadata
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

from . import util

NOMBRE = "omnicad"                      # nombre del servidor MCP y de la skill
ARGS_MCP = ["-m", "omnicad.servidor_mcp"]
ESQUEMA_OPENCODE = "https://opencode.ai/config.json"
TIMEOUT_OPENCODE_MS = 30000             # el arranque en frío puede pasar los 5 s por defecto de OpenCode

_buscar = shutil.which                  # reemplazables en las pruebas: nunca se corre `claude` de verdad
_ejecutar = subprocess.run


class _Falla(Exception):
    """Una acción no se pudo hacer: el mensaje dice por qué (la configuración queda como estaba)."""


@dataclass
class Accion:
    client: str                         # "claude-code" | "opencode"
    kind: str                           # "mcp" | "skill"
    status: str                         # pending | unchanged | manual | error | done
    file: str
    detail: str
    command: list | None = None         # comando de `claude` que se correría
    merge: dict | None = None           # lo que se fusiona en el JSON
    backup: str = ""
    message: str = ""
    aplicar: object = field(default=None, repr=False)   # callable sin argumentos; no sale en el JSON

    def a_dict(self):
        d = {"client": self.client, "kind": self.kind, "status": self.status, "file": self.file, "detail": self.detail}
        for clave in ("command", "merge"):
            if getattr(self, clave) is not None:
                d[clave] = getattr(self, clave)
        for clave in ("backup", "message"):
            if getattr(self, clave):
                d[clave] = getattr(self, clave)
        return d


# ---------------------------------------------------------------- utilidades de archivos
def _python():
    """Ruta absoluta del intérprete con barras `/` (sin duplicar `\\` en JSON; Windows las acepta)."""
    return os.path.abspath(sys.executable).replace("\\", "/")


def _norm(texto):
    return str(texto).replace("\\", "/")


def _leer_json(ruta):
    """(datos, error). `datos` es un dict. Un archivo con comentarios o comas finales NO es JSON: error."""
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as e:
        return None, str(e)
    if not isinstance(datos, dict):
        return None, "la raíz no es un objeto JSON"
    return datos, None


def _escribir_json(ruta, datos, como_original=""):
    """Escritura atómica (archivo temporal + reemplazo). Conserva el salto de línea del original."""
    salto = "\r\n" if "\r\n" in como_original else "\n"
    ruta.parent.mkdir(parents=True, exist_ok=True)
    temporal = ruta.with_name(ruta.name + ".tmp-omnicad")
    try:
        with open(temporal, "w", encoding="utf-8", newline=salto) as f:
            f.write(json.dumps(datos, indent=2, ensure_ascii=False) + "\n")
        os.replace(temporal, ruta)
    finally:
        temporal.unlink(missing_ok=True)


def _respaldar(ruta):
    """Copia `ruta` a `ruta.bak` (o `.bak-AAAAMMDD-HHMMSS[-n]` si ya hay uno). Devuelve la copia, o '' si no hay archivo."""
    if not ruta.is_file():
        return ""
    destino = ruta.with_name(ruta.name + ".bak")
    n = 0
    while destino.exists():
        sello = time.strftime("%Y%m%d-%H%M%S")
        destino = ruta.with_name(f"{ruta.name}.bak-{sello}" + (f"-{n}" if n else ""))
        n += 1
    shutil.copy2(ruta, destino)
    return str(destino)


def _guardar_fusion(ruta, modificar):
    """Lee `ruta` (o parte de cero), aplica `modificar(datos)`, respalda y escribe. Devuelve la ruta del respaldo."""
    original = ""
    datos = {}
    if ruta.is_file():
        original = ruta.read_text(encoding="utf-8-sig")
        datos, error = _leer_json(ruta)
        if datos is None:
            raise _Falla(f"{ruta} no es JSON válido ({error}): no se toca.")
    modificar(datos)
    respaldo = _respaldar(ruta)
    _escribir_json(ruta, datos, original)
    return respaldo


# ---------------------------------------------------------------- skill
def _origen_skill(ns):
    candidatos = [Path(ns.skill_origen)] if ns.skill_origen else \
        [Path(__file__).resolve().parents[3] / ".claude" / "skills" / NOMBRE]
    for c in candidatos:
        if (c / "SKILL.md").is_file():
            return c
    raise util.UsoError(f"No encuentro la skill (SKILL.md) en {candidatos[0]}.",
                        ["Con una instalación no editable pasá --skill-origen <carpeta con SKILL.md>.",
                         "En el repo está en .claude/skills/omnicad/."])


def _archivos(carpeta):
    return sorted(p.relative_to(carpeta) for p in carpeta.rglob("*")
                  if p.is_file() and "__pycache__" not in p.parts and ".bak" not in p.name)


def _accion_skill(cliente, origen, destino, tipo="skill", mensaje=""):
    archivos = _archivos(origen)
    distintos = [r for r in archivos
                 if not (destino / r).is_file() or (destino / r).read_bytes() != (origen / r).read_bytes()]
    detalle = f"copia {len(archivos)} archivo(s) desde {origen}"
    if not distintos:
        que = "la skill" if tipo == "skill" else "el complemento"
        return Accion(cliente, tipo, "unchanged", str(destino), f"{que} ya está copiado y es idéntico")

    def aplicar():
        respaldos = []
        for r in distintos:
            if (destino / r).is_file():
                respaldos.append(_respaldar(destino / r))     # SKILL.md.bak: no se carga como skill
            (destino / r).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(origen / r, destino / r)
        if any((destino / r).read_bytes() != (origen / r).read_bytes() for r in archivos):
            raise _Falla(f"la copia a {destino} no quedó idéntica.")
        return ", ".join(respaldos)

    return Accion(cliente, tipo, "pending", str(destino), detalle, aplicar=aplicar, message=mensaje)


# ---------------------------------------------------------------- complemento de Fusion 360
COMPLEMENTO = "OmniCADPuente"
# Instalaciones de Fusion: solo lectura. El complemento va SIEMPRE a la carpeta del usuario.
_PROHIBIDAS = [Path("D:/Autodesk")]


def _origen_complemento():
    origen = Path(__file__).resolve().parents[1] / "integraciones" / "fusion" / COMPLEMENTO
    if not (origen / f"{COMPLEMENTO}.py").is_file():
        raise util.UsoError(f"No encuentro el complemento de Fusion en {origen}.",
                            ["Reinstalá OmniCAD (pip install -e .) desde el repo."])
    return origen


def carpeta_addins(inicio=None):
    """Carpeta AddIns de Fusion del usuario, o None si el sistema no tiene Fusion (Linux)."""
    if sys.platform == "darwin":
        base = Path(inicio) if inicio else Path.home()
        return base / "Library" / "Application Support" / "Autodesk" / "Autodesk Fusion 360" / "API" / "AddIns"
    if os.name == "nt":
        appdata = Path(inicio) / "AppData" / "Roaming" if inicio else Path(os.environ.get("APPDATA") or
                                                                            Path.home() / "AppData" / "Roaming")
        return appdata / "Autodesk" / "Autodesk Fusion 360" / "API" / "AddIns"
    return None


def _prohibida(destino):
    destino = Path(destino).resolve()
    return any(destino == p.resolve() or p.resolve() in destino.parents for p in _PROHIBIDAS)


def _accion_fusion(inicio, explicito):
    addins = carpeta_addins(inicio)
    if addins is None:
        return None, "Fusion 360 no existe para este sistema: no se instala el complemento."
    destino = addins / COMPLEMENTO
    if _prohibida(destino):
        return Accion("fusion", "addin", "error", str(destino), "no se instala ahí",
                      message="Esa carpeta es de la instalación de Fusion (solo lectura)."), None
    if not addins.parent.is_dir() and not explicito:
        return None, "Fusion 360 no está instalado para este usuario: no se instala el complemento (--cliente fusion lo fuerza)."
    return _accion_skill("fusion", _origen_complemento(), destino, "addin",
                         "Después: reiniciá Fusion o, en Utilidades › Complementos (Mayús+S), ejecutá OmniCADPuente."), None


# ---------------------------------------------------------------- Claude Code
def _entrada_claude():
    return {"type": "stdio", "command": _python(), "args": list(ARGS_MCP), "env": {}}


def _accion_claude_mcp(ns, inicio):
    cfg = inicio / ".claude.json"
    py = _python()
    existente = None
    if cfg.is_file():
        datos, error = _leer_json(cfg)
        if datos is None:
            return Accion("claude-code", "mcp", "error", str(cfg), "no se puede leer la configuración",
                          message=f"{cfg} no es JSON válido ({error}): no se toca.")
        servidores = datos.get("mcpServers", {})
        if not isinstance(servidores, dict):
            return Accion("claude-code", "mcp", "error", str(cfg), "no se puede fusionar",
                          message='"mcpServers" no es un objeto JSON: no se toca.')
        existente = servidores.get(NOMBRE)
    if isinstance(existente, dict) and _norm(existente.get("command", "")) == py and existente.get("args") == ARGS_MCP:
        return Accion("claude-code", "mcp", "unchanged", str(cfg), f'"{NOMBRE}" ya está registrado con este Python')
    reemplaza = existente is not None
    claude = None if (ns.inicio or ns.sin_cli) else _buscar("claude")
    if claude:
        comando = [claude, "mcp", "add", "--scope", "user", NOMBRE, "--", py, *ARGS_MCP]
        detalle = (f"{'reemplaza la entrada existente y ' if reemplaza else ''}registra el MCP para todos tus proyectos "
                   f"(alcance user); la CLI edita ese archivo y se respalda antes")

        def aplicar():
            respaldo = _respaldar(cfg)
            if reemplaza:
                _correr([claude, "mcp", "remove", "--scope", "user", NOMBRE])
            _correr(comando)
            datos2, error2 = _leer_json(cfg)
            nuevo = (datos2 or {}).get("mcpServers", {}).get(NOMBRE)
            if not isinstance(nuevo, dict) or _norm(nuevo.get("command", "")) != py:
                raise _Falla(f"`claude mcp add` terminó bien pero {NOMBRE} no aparece en {cfg}"
                             + (f" ({error2})" if error2 else "") + ".")
            return respaldo

        return Accion("claude-code", "mcp", "pending", str(cfg), detalle, command=comando, aplicar=aplicar)
    entrada = _entrada_claude()

    def aplicar():
        def poner(datos):
            datos.setdefault("mcpServers", {})[NOMBRE] = entrada
        return _guardar_fusion(cfg, poner)

    motivo = "con --inicio" if ns.inicio else ("por --sin-cli" if ns.sin_cli else "no hay ejecutable `claude`")
    return Accion("claude-code", "mcp", "pending", str(cfg),
                  f"edita el archivo a mano ({motivo}), con copia .bak; cerrá Claude Code antes: lo reescribe seguido",
                  merge={"mcpServers": {NOMBRE: entrada}}, aplicar=aplicar)


def _correr(comando):
    try:
        r = _ejecutar(comando, capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.SubprocessError) as e:
        raise _Falla(f"no se pudo correr {' '.join(map(str, comando[:3]))}: {e}") from None
    if r.returncode != 0:
        salida = (r.stderr or r.stdout or "").strip().splitlines()
        raise _Falla(f"`{' '.join(map(str, comando[1:4]))}` salió con código {r.returncode}"
                     + (f": {salida[-1]}" if salida else "") + ".")


# ---------------------------------------------------------------- OpenCode
def _entrada_opencode():
    return {"type": "local", "command": [_python(), *ARGS_MCP], "enabled": True, "timeout": TIMEOUT_OPENCODE_MS}


def _accion_opencode_mcp(inicio):
    base = inicio / ".config" / "opencode"
    ruta = next((base / n for n in ("opencode.jsonc", "opencode.json") if (base / n).is_file()), base / "opencode.json")
    deseado = _entrada_opencode()
    snippet = {"mcp": {NOMBRE: deseado}}
    datos = {}
    if ruta.is_file():
        datos, error = _leer_json(ruta)
        if datos is None:
            texto = ruta.read_text(encoding="utf-8-sig", errors="replace")
            ya = f' Ya aparece la palabra "{NOMBRE}": revisá que no esté duplicado.' if f'"{NOMBRE}"' in texto else ""
            return Accion("opencode", "mcp", "manual", str(ruta),
                          "no se reescribe: tiene comentarios o comas finales (JSONC) y se perderían",
                          merge=snippet, message=f"Sumá a mano la entrada dentro de la clave \"mcp\" ({error}).{ya}")
        if not isinstance(datos.get("mcp", {}), dict):
            return Accion("opencode", "mcp", "error", str(ruta), "no se puede fusionar",
                          message='"mcp" no es un objeto JSON: no se toca.')
    existente = datos.get("mcp", {}).get(NOMBRE)
    if isinstance(existente, dict) and [_norm(c) for c in existente.get("command", [])] == deseado["command"] \
            and existente.get("type") == "local":
        return Accion("opencode", "mcp", "unchanged", str(ruta), f'"{NOMBRE}" ya está registrado con este Python')

    def aplicar():
        def poner(d):
            d.setdefault("$schema", ESQUEMA_OPENCODE)
            previa = d.setdefault("mcp", {}).get(NOMBRE)
            # Si ya había una entrada con otro comando se conserva lo demás (p. ej. enabled, environment).
            d["mcp"][NOMBRE] = {**deseado, **{k: v for k, v in previa.items() if k not in ("type", "command")}} \
                if isinstance(previa, dict) else deseado
        return _guardar_fusion(ruta, poner)

    verbo = "fusiona" if ruta.is_file() else "crea"
    extra = " (reemplaza el comando de la entrada existente)" if existente is not None else ""
    return Accion("opencode", "mcp", "pending", str(ruta),
                  f"{verbo} la clave mcp.{NOMBRE}" + (", con copia .bak" if ruta.is_file() else "") + extra,
                  merge=snippet, aplicar=aplicar)


# ---------------------------------------------------------------- plan y aplicación
def _planear(ns):
    inicio = Path(ns.inicio) if ns.inicio else Path.home()
    origen = _origen_skill(ns)
    acciones, avisos = [], []
    if ns.cliente in ("claude-code", "todos"):
        acciones.append(_accion_claude_mcp(ns, inicio))
        acciones.append(_accion_skill("claude-code", origen, inicio / ".claude" / "skills" / NOMBRE))
    if ns.cliente in ("opencode", "todos"):
        acciones.append(_accion_opencode_mcp(inicio))
    if ns.cliente in ("fusion", "todos"):
        accion, aviso = _accion_fusion(ns.inicio, ns.cliente == "fusion")
        acciones += [accion] if accion else []
        avisos += [aviso] if aviso else []
    if ns.cliente == "opencode":
        acciones.append(_accion_skill("opencode", origen, inicio / ".config" / "opencode" / "skills" / NOMBRE))
    elif ns.cliente == "todos":
        # OpenCode también lee ~/.claude/skills: una segunda copia en su carpeta daría «duplicate skill name».
        avisos.append("OpenCode usa la skill de ~/.claude/skills (la lee también): no se copia dos veces.")
    try:
        importlib.metadata.distribution("omnicad")
    except importlib.metadata.PackageNotFoundError:
        avisos.append("omnicad no está instalado en este Python (pip install -e .): el MCP registrado solo arranca si "
                      "Python encuentra el paquete.")
    return acciones, avisos


def _aplicar(acciones):
    for a in acciones:
        if a.status != "pending":
            continue
        try:
            a.backup = a.aplicar() or ""
            a.status = "done"
        except _Falla as e:
            a.status, a.message = "error", str(e)
        except OSError as e:
            a.status, a.message = "error", f"{type(e).__name__}: {e}"


_ROTULO = {"pending": "HARÍA", "done": "HECHO", "unchanged": "YA ESTÁ", "manual": "A MANO", "error": "ERROR"}
_CLIENTE = {"claude-code": "Claude Code", "opencode": "OpenCode", "fusion": "Fusion 360"}


def _mostrar(acciones, avisos, aplicado):
    util.decir("omnicad setup: " + ("resultado." if aplicado else
                                    "PLAN, no se escribió nada. Para aplicarlo agregá --aplicar."))
    actual = None
    for a in acciones:
        if a.client != actual:
            actual = a.client
            util.decir(f"\n{_CLIENTE[actual]}")
        rotulo = _ROTULO[a.status] if not (aplicado and a.status == "pending") else "PENDIENTE"
        util.decir(f"  {a.kind:<5} {rotulo:<8} {a.file}")
        util.decir(f"        {a.detail}")
        if a.command:
            util.decir(f"        comando: {' '.join(map(str, a.command))}")
        if a.merge and a.status in ("pending", "manual", "done"):
            util.decir("        contenido: " + util.a_json(a.merge))
        if a.backup:
            util.decir(f"        respaldo: {a.backup}")
        if a.message:
            util.decir(f"        {a.message}")
    for aviso in avisos:
        util.decir(f"\naviso: {aviso}")


def setup(ns):
    if ns.inicio and not Path(ns.inicio).is_dir():
        raise util.UsoError(f"--inicio tiene que ser una carpeta que exista: {ns.inicio}")
    acciones, avisos = _planear(ns)
    if ns.aplicar:
        _aplicar(acciones)
    malas = {"error", "manual"} if ns.aplicar else {"error"}
    fallo = any(a.status in malas for a in acciones)
    if ns.json:
        print(util.a_json({"ok": not fallo, "result": {"applied": bool(ns.aplicar), "actions": [a.a_dict() for a in acciones]},
                           "avisos": avisos}))
    else:
        _mostrar(acciones, avisos, ns.aplicar)
    return 1 if fallo else 0


EPILOGO = """\
dónde escribe (carpeta del usuario; --inicio la reemplaza):
  Claude Code  MCP    claude mcp add --scope user  (queda en ~/.claude.json)
               skill  ~/.claude/skills/omnicad/
  OpenCode     MCP    ~/.config/opencode/opencode.jsonc (o opencode.json), clave "mcp"
               skill  ~/.config/opencode/skills/omnicad/ (solo con --cliente opencode; con «todos» usa la de
                      ~/.claude/skills, que OpenCode también lee)
fuentes: code.claude.com/docs/en/mcp y /skills; opencode.ai/docs/mcp-servers, /skills y /config. La carpeta de
OpenCode en Windows se confirmó con `opencode debug paths` (la documentación solo dice ~/.config/opencode/).
no confirmado: que se respeten CLAUDE_CONFIG_DIR ni XDG_CONFIG_HOME (se usa siempre ~/.claude.json y ~/.config).
Un opencode.jsonc con comentarios no se reescribe (se perderían): el comando muestra qué sumar a mano.
  Fusion 360   complemento  %APPDATA%/Autodesk/Autodesk Fusion 360/API/AddIns/OmniCADPuente/ (macOS: ~/Library/
               Application Support/...); con «todos» solo si Fusion está instalado. Nunca en D:/Autodesk.
"""


def registrar(sub, comun):
    p = sub.add_parser("setup", parents=[comun], epilog=EPILOGO,
                       help="conecta OmniCAD a Claude Code y OpenCode (MCP + skill) y a Fusion 360 (complemento); sin --aplicar "
                            "solo muestra el plan",
                       description="Registra el servidor MCP de OmniCAD y copia la skill `omnicad` en Claude Code y/o "
                                   "OpenCode. SIN --aplicar solo muestra qué haría y no escribe nada. Con --aplicar "
                                   "respalda (.bak) cada archivo de configuración que modifica, fusiona el JSON sin "
                                   "borrar otros servidores y es idempotente. El MCP se registra con el Python que "
                                   "corre este comando (ruta absoluta).")
    p.add_argument("--cliente", "-c", choices=["claude-code", "opencode", "fusion", "todos"], default="todos",
                   help="a quién conectar (defecto todos)")
    p.add_argument("--aplicar", action="store_true", help="escribir de verdad (sin esto solo muestra el plan)")
    p.add_argument("--inicio", metavar="DIR", help="usar esta carpeta en lugar de la del usuario (para pruebas); "
                   "implica editar ~/.claude.json a mano en vez de correr `claude`")
    p.add_argument("--sin-cli", action="store_true",
                   help="no usar el ejecutable `claude`: editar ~/.claude.json a mano (con copia .bak)")
    p.add_argument("--skill-origen", metavar="DIR",
                   help="carpeta de la skill a copiar (por defecto .claude/skills/omnicad del repo)")
    p.set_defaults(func=setup)

"""Modelos disponibles de cada proveedor del Asistente (IA-10), para el combo «Modelo» de Preferencias. Sin Qt.

- OpenCode: `opencode models --verbose` (un `proveedor/modelo` por línea seguido de su JSON, con las variantes).
- Codex: `codex debug models` (catálogo JSON; solo los de visibilidad «list», con sus niveles de esfuerzo); si el
  comando falla, la caché `~/.codex/models_cache.json`. El de fábrica es el `model` de `~/.codex/config.toml`.
- Claude Code no tiene comando para listar: sus alias y los nombres completos actuales.
- Por API: `GET /models` (no gasta). Con los que piden clave, solo si la variable de la clave está definida.

El resultado queda en memoria mientras dure la sesión (`refrescar=True` lo vuelve a pedir). Nunca lanza: si algo
falla, la lista viene vacía y `motivo` dice por qué.
"""
import json
import os
import subprocess
import tomllib
import urllib.request
from pathlib import Path

from . import config
from .proveedores.agente_local import AGENTES, LANZAR, ejecutable

CLAUDE_CODE = ["fable", "opus", "sonnet", "claude-fable-5-1", "claude-opus-5-5", "claude-sonnet-5-5",
               "claude-haiku-5-5"]
ESPERA = 20          # s: listar no puede trabar Preferencias (corre en un hilo, pero el CLI podría colgarse)
_memoria = {}


def _correr(tipo, ruta, *args):
    exe = ejecutable(tipo, ruta)
    if exe is None:
        raise RuntimeError(f"no se encuentra «{AGENTES[tipo][1]}» (instalalo o poné su ruta)")
    r = subprocess.run([exe, *args], capture_output=True, stdin=subprocess.DEVNULL, timeout=ESPERA, **LANZAR)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.decode("utf-8", "replace").strip()[-200:] or f"código de salida {r.returncode}")
    return r.stdout.decode("utf-8", "replace")


def _opencode(ruta):
    """{modelo: [variantes]} en el orden de `opencode models --verbose`."""
    texto, salida, i = _correr("opencode", ruta, "models", "--verbose"), {}, 0
    decodificar = json.JSONDecoder().raw_decode
    while (llave := texto.find("{", i)) >= 0:
        modelo = texto[i:llave].strip()
        datos, i = decodificar(texto, llave)
        salida[modelo] = list(datos.get("variants") or {}) if isinstance(datos, dict) else []
    return salida


def _codex(ruta):
    """{modelo: [esfuerzos]} de los modelos visibles de Codex, y el de fábrica de su config."""
    try:
        catalogo = json.loads(_correr("codex", ruta, "debug", "models"))
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError):
        cache = Path.home() / ".codex" / "models_cache.json"
        if not cache.is_file():
            raise                                # sin caché, que se vea por qué falló el comando
        catalogo = json.loads(cache.read_text(encoding="utf-8"))
    modelos = {m["slug"]: [n["effort"] for n in m.get("supported_reasoning_levels") or []]
               for m in catalogo["models"] if m.get("visibility") == "list"}
    try:
        cfg = tomllib.loads((Path.home() / ".codex" / "config.toml").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        cfg = {}
    fabrica = " · ".join(str(cfg[k]) for k in ("model", "model_reasoning_effort") if cfg.get(k))
    return modelos, fabrica


def _api(proveedor, base_url):
    """Los modelos de `GET /models` (Anthropic u OpenAI compatible)."""
    variable = config.variable_clave(proveedor)
    clave = os.environ.get(variable) if variable else None
    if proveedor in ("anthropic", "openai") and not clave:
        raise RuntimeError(f"falta la variable {variable}")
    if proveedor == "anthropic":
        url, encabezados = "https://api.anthropic.com/v1/models?limit=100", {"x-api-key": clave,
                                                                            "anthropic-version": "2023-06-01"}
    else:
        url = ((base_url or "").strip() or config.PROVEEDORES[proveedor][3]).rstrip("/") + "/models"
        # «local» va a un servidor que eligió la persona: la clave de OpenAI del entorno no viaja ahí
        encabezados = {"authorization": f"Bearer {clave}"} if clave and proveedor != "local" else {}
    with urllib.request.urlopen(urllib.request.Request(url, headers=encabezados), timeout=ESPERA) as r:
        datos = json.loads(r.read().decode("utf-8"))
    return [m["id"] for m in datos.get("data") or [] if isinstance(m, dict) and m.get("id")]


def modelos_disponibles(proveedor, ruta="", base_url="", refrescar=False):
    """{"modelos": [...], "fabrica": el que usa sin elegir ("" = el del CLI), "variantes": {modelo: [...]},
    "motivo": "" o por qué la lista vino vacía}."""
    clave = (proveedor, ruta or "", base_url or "")
    if not refrescar and clave in _memoria:
        return _memoria[clave]
    resultado = {"modelos": [], "fabrica": config.PROVEEDORES.get(proveedor, ("", "", ""))[2], "variantes": {},
                 "motivo": ""}
    try:
        if proveedor == "claude_code":
            resultado["modelos"] = list(CLAUDE_CODE)
        elif proveedor == "opencode":
            resultado["variantes"] = _opencode(ruta)
            resultado["modelos"] = list(resultado["variantes"])
        elif proveedor == "codex":
            resultado["variantes"], resultado["fabrica"] = _codex(ruta)
            resultado["modelos"] = list(resultado["variantes"])
        elif proveedor in config.PROVEEDORES:
            resultado["modelos"] = _api(proveedor, base_url)
        else:
            raise RuntimeError(f"proveedor desconocido: {proveedor!r}")
    except Exception as e:  # noqa: BLE001 — salida de otro programa o de la red: se informa, nunca rompe Preferencias
        resultado["motivo"] = (str(e) if isinstance(e, RuntimeError) else f"{type(e).__name__}: {e}")[:300]
    if resultado["modelos"] or not resultado["motivo"]:
        _memoria[clave] = resultado        # una falla no queda guardada: el próximo intento vuelve a probar
    return resultado

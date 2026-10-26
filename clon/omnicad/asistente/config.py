"""Configuración del asistente: arma el proveedor elegido en Preferencias › Asistente IA.

La clave de API NUNCA está en la configuración ni en las preferencias: sale de la variable de entorno del proveedor.
"""
import os

from .proveedores import agente_local  # el módulo: agente_local → api → herramientas_asistente → acá (ciclo)
from .proveedores.anthropic import ProveedorAnthropic
from .proveedores.base import ErrorProveedor
from .proveedores.openai_compat import OLLAMA, OPENAI, OPENROUTER, ProveedorOpenAI

# clave → (nombre visible, variable de la clave o None, modelo de fábrica, base_url de fábrica)
PROVEEDORES = {
    "anthropic": ("Claude por API", "ANTHROPIC_API_KEY", "claude-opus-5-5", ""),
    "openai": ("OpenAI", "OPENAI_API_KEY", "gpt-6.1-sol", OPENAI),
    "openrouter": ("OpenRouter", "OPENROUTER_API_KEY", "anthropic/claude-sonnet-5-5", OPENROUTER),
    "local": ("Local compatible con OpenAI (Ollama, LM Studio)", None, "qwen3", OLLAMA),
    # Modo suscripción (IA-6): el CLI que la persona ya instaló y logueó; modelo vacío = el que use el CLI
    "claude_code": ("Claude Code (tu suscripción)", None, "", ""),
    "codex": ("Codex (tu suscripción ChatGPT)", None, "", ""),
    "opencode": ("OpenCode", None, "openai/gpt-6.1-sol", ""),
}
AGENTES_LOCALES = ("claude_code", "codex", "opencode")
# Preferencias del asistente (prefijo «asistente/»): las usan la ventana (ui/preferencias.py) y el catálogo
# (api/herramientas_asistente.py). Nunca la clave: sale de la variable de entorno del proveedor.
DEFECTOS = {
    "proveedor": "anthropic",
    "modelo": "",            # vacío = el de fábrica del proveedor
    "base_url": "",          # vacío = la del proveedor (OpenAI, OpenRouter, Ollama)
    "modo": "guiar",
    "tope_usd": 0.5,         # gasto máximo por pedido; 0 = sin tope
    "imagenes": True,        # mandarle al modelo las imágenes del visor
    "variante": "",          # esfuerzo: --variant de OpenCode o model_reasoning_effort de Codex; vacío = el de fábrica
    "ruta_claude_code": "",  # modo suscripción: ruta del CLI; vacío = el del PATH
    "ruta_codex": "",
    "ruta_opencode": "",
    "instrucciones": "",     # instrucciones propias de la persona (IA-12): van al prompt de todos los chats
    "permisos": "una_vez",   # cuándo pregunta (IA-15): cada_paso, una_vez o nunca (asistente/herramientas.PERMISOS)
    "ver_herramientas": False,   # el chat muestra una línea por herramienta que usa la IA (IA-15)
}
# Lo que lee crear_proveedor de las preferencias (prefijo «asistente/»). ruta_<agente> vacía = el del PATH.
CLAVES = ("proveedor", "modelo", "base_url", "variante") + tuple(f"ruta_{a}" for a in AGENTES_LOCALES)


def variable_clave(proveedor):
    """Nombre de la variable de entorno con la clave del proveedor (None si no pide clave)."""
    return PROVEEDORES[proveedor][1] if proveedor in PROVEEDORES else None


def clave_definida(proveedor):
    """True si la variable de la clave tiene algo; nunca devuelve la clave."""
    variable = variable_clave(proveedor)
    return bool(variable and os.environ.get(variable))


def modelo_de(config):
    """El modelo elegido o el de fábrica del proveedor."""
    return (config.get("modelo") or "").strip() or PROVEEDORES[config["proveedor"]][2]


def crear_proveedor(config):
    """Proveedor listo desde CLAVES; ErrorProveedor si el proveedor no existe, falta la clave o no está el CLI."""
    nombre = config.get("proveedor")
    if nombre not in PROVEEDORES:
        raise ErrorProveedor(f"Proveedor desconocido: {nombre!r}. Opciones: {', '.join(PROVEEDORES)}.")
    modelo = modelo_de(config)
    if nombre in AGENTES_LOCALES:
        return agente_local.AgenteLocal(nombre, config.get(f"ruta_{nombre}") or "", modelo,
                           (config.get("variante") or "").strip() if nombre in ("opencode", "codex") else "")
    if nombre == "anthropic":
        return ProveedorAnthropic(modelo)
    base_url = (config.get("base_url") or "").strip() or PROVEEDORES[nombre][3]
    proveedor = ProveedorOpenAI(modelo, base_url=base_url)
    if nombre == "openai" and not proveedor.clave:
        raise ErrorProveedor("Falta la clave de API de OpenAI: definí la variable OPENAI_API_KEY.")
    if nombre == "openrouter" and "openrouter.ai" not in base_url:
        proveedor.clave = os.environ.get("OPENROUTER_API_KEY")   # con otra base_url el proveedor leería la de OpenAI
    if nombre == "openrouter" and not proveedor.clave:
        raise ErrorProveedor("Falta la clave de API de OpenRouter: definí la variable OPENROUTER_API_KEY.")
    if nombre == "local":
        proveedor.clave = None    # la clave de OpenAI del entorno no viaja a un servidor que eligió el usuario
    return proveedor

"""Proveedor de Claude por clave de API (Anthropic Messages API), con urllib y sin SDK."""
import base64

from .base import ErrorProveedor, PedidoHerramienta, Proveedor, Respuesta, clave_de, pedir_json

URL = "https://api.anthropic.com/v1/messages"
VERSION_API = "2023-06-01"
# USD por millón de tokens (entrada, salida). Fuente: skill claude-api, tabla «Current Models» del 2026-10-06.
# shortcut: Haiku 5.5 cobra 0,50/2,50 con más de 100K de entrada; ajustar si se usa con contextos tan largos.
PRECIOS = {
    "claude-fable-5-1": (10.0, 50.0),
    "claude-fable-5": (10.0, 50.0),
    "claude-opus-5-5": (4.0, 20.0),
    "claude-opus-5": (5.0, 25.0),
    "claude-opus-4-8": (5.0, 25.0),
    "claude-sonnet-5-5": (2.0, 10.0),
    "claude-sonnet-5": (2.0, 10.0),
    "claude-haiku-5-5": (0.10, 0.50),
    "claude-haiku-4-5": (1.0, 5.0),
}


CACHE = {"type": "ephemeral"}
ESCRIBIR_CACHE, LEER_CACHE = 1.25, 0.1    # × el precio de entrada (skill claude-api, caché de 5 min)


def costo_usd(modelo, entrada, salida, cache_escrita=0, cache_leida=0):
    """Costo del pedido según PRECIOS; None si el modelo no está en la tabla. `entrada` es la NO cacheada."""
    if modelo not in PRECIOS:
        return None
    precio_entrada, precio_salida = PRECIOS[modelo]
    return ((entrada + cache_escrita * ESCRIBIR_CACHE + cache_leida * LEER_CACHE) * precio_entrada
            + salida * precio_salida) / 1_000_000


def _bloque(bloque):
    if bloque["tipo"] == "texto":
        return {"type": "text", "text": bloque["texto"]}
    if bloque["tipo"] == "imagen":
        return {"type": "image", "source": {"type": "base64", "media_type": "image/png",
                                            "data": base64.b64encode(bloque["png"]).decode("ascii")}}
    if bloque["tipo"] == "documento":
        return {"type": "document", "source": {"type": "base64", "media_type": "application/pdf",
                                               "data": base64.b64encode(bloque["pdf"]).decode("ascii")}}
    if bloque["tipo"] == "pedido_herramienta":
        return {"type": "tool_use", "id": bloque["id"], "name": bloque["nombre"], "input": bloque["args"]}
    return {"type": "tool_result", "tool_use_id": bloque["id"], "is_error": bloque["error"],
            "content": [_bloque(b) for b in bloque["contenido"]]}


class ProveedorAnthropic(Proveedor):
    def __init__(self, modelo="claude-opus-5-5", clave=None, timeout=300, max_tokens=16000):
        self.modelo, self.timeout, self.max_tokens = modelo, timeout, max_tokens
        self.clave = clave_de(clave, "ANTHROPIC_API_KEY")
        if not self.clave:
            raise ErrorProveedor("Falta la clave de API de Anthropic: definí la variable ANTHROPIC_API_KEY.")

    def cuerpo(self, sistema, mensajes, herramientas):
        """El JSON del pedido a la Messages API."""
        # Caché del prompt: las herramientas (orden estable, las habilitadas al final) y el sistema llevan su marca;
        # la de arriba del todo cachea la conversación hasta el último bloque.
        cuerpo = {
            "model": self.modelo,
            "max_tokens": self.max_tokens,
            "cache_control": CACHE,
            "messages": [{"role": "user" if m["rol"] == "usuario" else "assistant",
                          "content": [_bloque(b) for b in m["contenido"]]} for m in mensajes],
        }
        if herramientas:
            cuerpo["tools"] = [{"name": h["nombre"], "description": h["descripcion"], "input_schema": h["esquema"]}
                               for h in herramientas]
            cuerpo["tools"][-1]["cache_control"] = CACHE
        if sistema:
            cuerpo["system"] = [{"type": "text", "text": sistema, "cache_control": CACHE}]
        return cuerpo

    def responder(self, sistema, mensajes, herramientas):
        """Manda la conversación y traduce texto, pedidos de herramientas y uso."""
        datos = pedir_json(URL, self.cuerpo(sistema, mensajes, herramientas),
                           {"x-api-key": self.clave, "anthropic-version": VERSION_API}, self.timeout, self.clave)
        if datos.get("stop_reason") == "refusal":
            categoria = (datos.get("stop_details") or {}).get("category") or "sin categoría"
            raise ErrorProveedor(f"El modelo se negó a responder (filtro de seguridad: {categoria}).")
        contenido = datos.get("content") or []
        uso = datos.get("usage") or {}
        entrada, salida = uso.get("input_tokens") or 0, uso.get("output_tokens") or 0
        escrita, leida = uso.get("cache_creation_input_tokens") or 0, uso.get("cache_read_input_tokens") or 0
        return Respuesta(
            texto="\n".join(b["text"] for b in contenido if b.get("type") == "text"),
            herramientas=[PedidoHerramienta(b["id"], b["name"], b.get("input") or {})
                          for b in contenido if b.get("type") == "tool_use"],
            uso={"entrada": entrada + escrita + leida, "salida": salida,
                 "costo_usd": costo_usd(self.modelo, entrada, salida, escrita, leida)},
        )

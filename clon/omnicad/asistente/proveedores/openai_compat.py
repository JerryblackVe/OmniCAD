"""Proveedor con formato OpenAI Chat Completions: OpenAI, OpenRouter, Ollama y LM Studio por base_url."""
import base64
import json

from .base import ErrorProveedor, PedidoHerramienta, Proveedor, Respuesta, clave_de, pedir_json

OPENAI = "https://api.openai.com/v1"
OPENROUTER = "https://openrouter.ai/api/v1"
OLLAMA = "http://localhost:11434/v1"


def _imagen(bloque):
    return {"type": "image_url",
            "image_url": {"url": "data:image/png;base64," + base64.b64encode(bloque["png"]).decode("ascii")}}


def _mensajes(sistema, mensajes):
    """Traduce el chat neutral. El rol tool no acepta imágenes: van en un mensaje de usuario a continuación."""
    salida = [{"role": "system", "content": sistema}] if sistema else []
    for mensaje in mensajes:
        if mensaje["rol"] == "asistente":
            texto = "\n".join(b["texto"] for b in mensaje["contenido"] if b["tipo"] == "texto")
            llamadas = [{"id": b["id"], "type": "function",
                         "function": {"name": b["nombre"], "arguments": json.dumps(b["args"], ensure_ascii=False)}}
                        for b in mensaje["contenido"] if b["tipo"] == "pedido_herramienta"]
            asistente = {"role": "assistant", "content": texto or None}
            if llamadas:
                asistente["tool_calls"] = llamadas
            salida.append(asistente)
            continue
        partes = []
        for bloque in mensaje["contenido"]:
            if bloque["tipo"] == "resultado_herramienta":
                salida.append({"role": "tool", "tool_call_id": bloque["id"],
                               "content": "\n".join(b["texto"] for b in bloque["contenido"] if b["tipo"] == "texto")})
                partes += [_imagen(b) for b in bloque["contenido"] if b["tipo"] == "imagen"]
            elif bloque["tipo"] == "imagen":
                partes.append(_imagen(bloque))
            else:
                partes.append({"type": "text", "text": bloque["texto"]})
        if partes:
            salida.append({"role": "user", "content": partes})
    return salida


class ProveedorOpenAI(Proveedor):
    def __init__(self, modelo, base_url=OPENAI, clave=None, timeout=300):
        self.modelo, self.timeout = modelo, timeout
        self.url = base_url.rstrip("/") + "/chat/completions"
        # Local (Ollama, LM Studio) no pide clave: sin ella no se manda Authorization.
        self.clave = clave_de(clave, "OPENROUTER_API_KEY" if "openrouter.ai" in base_url else "OPENAI_API_KEY")

    def cuerpo(self, sistema, mensajes, herramientas):
        """El JSON del pedido a /chat/completions."""
        cuerpo = {"model": self.modelo, "messages": _mensajes(sistema, mensajes)}
        if herramientas:
            cuerpo["tools"] = [{"type": "function", "function": {"name": h["nombre"], "description": h["descripcion"],
                                                                 "parameters": h["esquema"]}} for h in herramientas]
        return cuerpo

    def responder(self, sistema, mensajes, herramientas):
        """Manda la conversación y traduce texto, tool_calls y uso (costo solo si lo informa, p. ej. OpenRouter)."""
        encabezados = {"authorization": f"Bearer {self.clave}"} if self.clave else {}
        datos = pedir_json(self.url, self.cuerpo(sistema, mensajes, herramientas), encabezados, self.timeout,
                           self.clave)
        try:
            mensaje = datos["choices"][0]["message"]
        except (KeyError, IndexError, TypeError):
            raise ErrorProveedor("La respuesta del proveedor no trae ningún mensaje.") from None
        pedidos = []
        for i, llamada in enumerate(mensaje.get("tool_calls") or []):
            funcion = llamada.get("function") or {}
            try:
                args = json.loads(funcion.get("arguments") or "{}")
            except ValueError:
                args = None
            if not isinstance(args, dict):  # la herramienta rechaza la clave rara y el error vuelve al modelo
                args = {"_argumentos_invalidos": funcion.get("arguments")}
            pedidos.append(PedidoHerramienta(llamada.get("id") or f"llamada_{i}", funcion.get("name") or "", args))
        uso = datos.get("usage") or {}
        return Respuesta(texto=mensaje.get("content") or "", herramientas=pedidos,
                         uso={"entrada": uso.get("prompt_tokens") or 0, "salida": uso.get("completion_tokens") or 0,
                              "costo_usd": uso.get("cost")})

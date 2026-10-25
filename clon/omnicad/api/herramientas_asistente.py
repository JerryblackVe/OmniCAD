"""Asistente IA desde el catálogo (IA-7): su configuración, pedidos sin ventana y el historial de chats.

Grupo `asistente`, FUERA de los grupos por defecto del MCP: `assistant_ask` gasta plata en la API elegida. El panel de
chat no está acá (un agente externo ya ES el asistente: ver docs/brechas_mcp.md). La clave de API nunca pasa por estas
herramientas: se lee de la variable de entorno del proveedor y solo se informa si está definida.
"""
from typing import Literal
from urllib.parse import urlsplit

from ..asistente import config, historial
from .errores import error
from .herramientas_preferencias import _ajustes
from .registro import herramienta

TOPE_PROMPT = 20000          # caracteres, como el campo del panel: un pegado gigante por error gastaría plata
# Un agente solo puede apuntar base_url a la de un proveedor o a la propia PC: con otra dirección la clave de OpenAI
# del entorno viajaría a un servidor ajeno. Otra dirección la elige la persona en Preferencias › Asistente IA.
_HOSTS_LOCALES = {"localhost", "127.0.0.1", "::1"}


def _leer_config(ajustes):
    """Las preferencias «asistente/*» con su tipo (mismo criterio que ui/preferencias.Preferencias)."""
    cfg = {}
    for clave, defecto in config.DEFECTOS.items():
        valor = ajustes.value(f"asistente/{clave}", defecto)
        if isinstance(defecto, bool):
            valor = valor if isinstance(valor, bool) else str(valor).lower() in ("true", "1")
        elif isinstance(defecto, float):
            try:
                valor = float(valor)
            except (TypeError, ValueError):
                valor = defecto
        else:
            valor = str(valor)
        cfg[clave] = valor
    return cfg


def _resumen(cfg):
    proveedor = cfg["proveedor"]
    conocido = proveedor in config.PROVEEDORES
    return {"provider": proveedor, "model": cfg["modelo"], "effective_model": config.modelo_de(cfg) if conocido else "",
            "base_url": cfg["base_url"], "default_mode": cfg["modo"], "max_usd": cfg["tope_usd"],
            "send_images": cfg["imagenes"], "key_env_var": config.variable_clave(proveedor),
            "key_set": config.clave_definida(proveedor), "providers": list(config.PROVEEDORES)}


@herramienta("get_assistant_config", "asistente", "Configuración del Asistente IA (Preferencias › Asistente IA): "
             "proveedor, modelo, base_url, modo por defecto, tope de gasto e imágenes. De la clave de API solo dice "
             "qué variable de entorno la lleva y si está definida; nunca su valor.")
def get_assistant_config(sesion):
    return _resumen(_leer_config(_ajustes()))


@herramienta("set_assistant_config", "asistente", "Cambia la configuración del Asistente IA (solo los campos pasados). "
             "No acepta claves de API ni rutas de ejecutables. No modifica el documento ni entra en deshacer.",
             modifica=True, transaccion=False)
def set_assistant_config(sesion, provider: str | None = None, model: str | None = None, base_url: str | None = None,
                         default_mode: Literal["explicar", "mostrar", "guiar", "hacer"] | None = None,
                         max_usd: float | None = None, send_images: bool | None = None):
    """
    provider: proveedor (lista en get_assistant_config › providers), p. ej. "anthropic", "openai", "local".
    model: modelo del proveedor; "" vuelve al de fábrica.
    base_url: dirección del servidor: "" (la del proveedor), la de un proveedor conocido o una de esta PC (localhost).
    default_mode: modo con que arranca el panel.
    max_usd: gasto máximo por pedido en USD, de 0 (sin tope) a 100.
    send_images: si se le mandan al modelo las imágenes del visor.
    """
    cambios = {}
    if provider is not None:
        if provider not in config.PROVEEDORES:
            raise error("INVALID_ARGUMENTS", f"Proveedor desconocido: {provider!r}.",
                        "Opciones: " + ", ".join(config.PROVEEDORES) + ".")
        cambios["proveedor"] = provider
    if model is not None:
        model = model.strip()
        if len(model) > 200 or not model.isprintable():
            raise error("INVALID_ARGUMENTS", "El modelo tiene que ser un nombre corto, sin saltos de línea.")
        cambios["modelo"] = model
    if base_url is not None:
        base_url = base_url.strip()
        partes = urlsplit(base_url)
        if base_url and not (partes.scheme in ("http", "https") and (
                base_url.rstrip("/") in {v[3].rstrip("/") for v in config.PROVEEDORES.values() if v[3]}
                or partes.hostname in _HOSTS_LOCALES)):
            raise error("INVALID_ARGUMENTS", "base_url tiene que ser vacía, la de un proveedor conocido o una "
                        "dirección de esta PC (http://localhost:…): otra se elige a mano en Preferencias › Asistente IA.")
        cambios["base_url"] = base_url
    if default_mode is not None:
        cambios["modo"] = default_mode
    if max_usd is not None:
        if not 0 <= max_usd <= 100:
            raise error("INVALID_ARGUMENTS", f"max_usd fuera de rango: {max_usd} (va de 0 a 100; 0 = sin tope).")
        cambios["tope_usd"] = float(max_usd)
    if send_images is not None:
        cambios["imagenes"] = send_images
    ajustes = _ajustes()
    for clave, valor in cambios.items():
        ajustes.setValue(f"asistente/{clave}", valor)
    ajustes.sync()
    if ajustes.status() != ajustes.Status.NoError:
        raise error("FILE_ERROR", "No se pudieron guardar las preferencias del Asistente.")
    return {**_resumen(_leer_config(ajustes)), "updated": sorted(cambios)}


@herramienta("assistant_ask", "asistente", "Corre un pedido al Asistente IA SIN ventana, sobre el documento de esta "
             "sesión, con el proveedor configurado (get_assistant_config). GASTA en la API elegida. Es UN paso de "
             "deshacer. En Guiar y Hacer no hay tarjeta de plan: los cambios se aprueban solos (lo dice un aviso).",
             modifica=True)
def assistant_ask(sesion, prompt: str, mode: Literal["explicar", "mostrar", "guiar", "hacer"] = "hacer",
                  attachments: list[str] | None = None):
    """
    prompt: el pedido, en lenguaje natural (p. ej. "hacé una caja de 40 mm con empalme de 3").
    mode: explicar y mostrar no cambian el documento; guiar y hacer sí.
    attachments: rutas de archivos que van con el pedido, como el clip del panel: PDF, PNG, JPG, SVG o DXF, hasta 10.
    """
    from .. import api
    from ..asistente import adjuntos, bucle
    from ..asistente.herramientas import Herramientas
    from ..asistente.prompt import armar_sistema
    from ..asistente.proveedores.base import ErrorProveedor

    prompt = prompt.strip()
    if not prompt or len(prompt) > TOPE_PROMPT:
        raise error("INVALID_ARGUMENTS", f"El pedido tiene que tener entre 1 y {TOPE_PROMPT} caracteres.")
    bloques = []
    for i, ruta in enumerate(attachments or ()):
        try:
            bloques += adjuntos.preparar(ruta, i).bloques
        except adjuntos.ErrorAdjunto as e:
            raise error("INVALID_ARGUMENTS", str(e)) from None
    cfg = _leer_config(_ajustes())
    if cfg["proveedor"] in config.AGENTES_LOCALES:
        raise error("PROVIDER_ERROR", f"El proveedor {cfg['proveedor']!r} (modo suscripción) trabaja sobre la ventana "
                    "abierta: sin ventana no tiene documento.",
                    "Usá el panel Asistente de OmniCAD, o elegí un proveedor por API con set_assistant_config.")
    try:
        proveedor = config.crear_proveedor(cfg)
    except ErrorProveedor as e:
        raise error("PROVIDER_ERROR", str(e)) from None

    if mode in ("guiar", "hacer"):
        sesion.avisar(f"Modo {mode} sin ventana: no hay tarjeta de plan, los cambios se aprobaron solos.")
    uso, textos, usadas = {"costo_usd": 0.0}, [], []

    def al_evento(tipo, datos):
        if tipo == "uso":
            uso["costo_usd"] += datos.get("costo_usd") or 0
        elif tipo == "texto":
            textos.append(datos)
        elif tipo == "herramienta":
            usadas.append({"name": datos["nombre"], "ok": bool(datos["respuesta"].get("ok"))})
        elif tipo == "error":
            sesion.avisar(datos)

    def ejecutar(nombre, args):
        respuesta = api.llamar(sesion, nombre, args)
        return respuesta if cfg["imagenes"] else bucle.sin_imagenes(respuesta)

    tope = cfg["tope_usd"]
    mensajes = [{"rol": "usuario", "contenido": [{"tipo": "texto", "texto": prompt}, *bloques]}]
    resultado = bucle.correr(proveedor, mensajes, ejecutar, Herramientas(modo=mode), armar_sistema(sesion, mode),
                             al_evento, cancelado=lambda: tope > 0 and uso["costo_usd"] > tope,
                             aprobar=lambda pedidos: True)
    if resultado["motivo"] == "cancelado":     # el único que cancela sin ventana es el tope de gasto
        raise error("BUDGET_EXCEEDED", f"Se cortó el pedido: el gasto ({uso['costo_usd']:.4f} USD) superó el tope de "
                    f"{tope:.2f} USD.")
    return {"text": "\n\n".join(textos), "tools": usadas, "stop_reason": resultado["motivo"],
            "turns": resultado["vueltas"], "usage": {"input_tokens": resultado["uso"]["entrada"],
                                                    "output_tokens": resultado["uso"]["salida"],
                                                    "cost_usd": resultado["uso"]["costo_usd"]}}


@herramienta("list_assistant_chats", "asistente", "Lista los chats guardados del Asistente (el más nuevo primero): "
             "id, título, fecha, modo, proveedor, modelo y cantidad de mensajes.")
def list_assistant_chats(sesion):
    return {"chats": [{"id": c["id"], "title": c["titulo"], "date": c["fecha"], "mode": c["modo"],
                       "provider": c["proveedor"], "model": c["modelo"], "messages": c["mensajes"]}
                      for c in historial.listar()]}


@herramienta("get_assistant_chat", "asistente", "Lee un chat guardado del Asistente: los textos de la conversación y "
             "las herramientas que usó, sin imágenes.")
def get_assistant_chat(sesion, chat_id: str):
    """
    chat_id: id del chat (list_assistant_chats).
    """
    try:
        chat = historial.cargar(chat_id)
    except historial.ErrorHistorial as e:
        raise error("NOT_FOUND", str(e)) from None
    mensajes = []
    for m in chat["mensajes"]:
        for b in m["contenido"]:
            if b["tipo"] == "texto":
                mensajes.append({"role": m["rol"], "text": b["texto"]})
            elif b["tipo"] == "pedido_herramienta":
                mensajes.append({"role": m["rol"], "tool": b["nombre"], "args": b["args"]})
    return {"id": chat_id, "title": chat.get("titulo"), "date": chat.get("fecha"), "mode": chat.get("modo"),
            "provider": chat.get("proveedor"), "model": chat.get("modelo"), "messages": mensajes}

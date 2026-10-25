# -*- coding: utf-8 -*-
"""
Servidor MCP de OmniCAD: cada herramienta del catálogo de `omnicad.api` queda expuesta tal cual.

Decisiones:
  - El esquema de entrada de cada herramienta es EXACTAMENTE el del catálogo (`api.catalogo()`): no se
    regenera desde ninguna firma. Por eso se sobrescriben `list_tools` y `call_tool` de `MCPServer` en vez de
    registrar funciones con `add_tool` (que construiría el esquema desde la firma de Python).
  - Los argumentos los valida `api.llamar` (con errores `INVALID_ARGUMENTS` y pistas), no el SDK.
  - Una sola `Sesion` por servidor. Las llamadas corren en UN hilo propio (una a la vez y siempre el mismo):
    el bucle de eventos sigue contestando mientras se renderiza y el documento nunca se toca en paralelo.
  - El catálogo se toma al crear el servidor (lo que haya registrado en ese momento) y se filtra por toolsets.
  - Modos (`modo`): "sin_ventana" (la `Sesion` propia), "vivo" (cada llamada va a la app abierta por el puente,
    `puente_cliente.py`) y "auto" (la app si está escuchando; si no, la sesión propia). En auto, cuando cambia de
    un modo al otro, la respuesta trae un aviso en `avisos`: el agente pasó a OTRO documento. En vivo y auto se
    suma la herramienta `get_mode` (solo del MCP: la CLI no tiene modo en vivo). Las del grupo `dev` corren
    siempre en el proceso del servidor.
  - `meta=True` (`--meta-tools`, solo para el Asistente en modo suscripción): suma `find_tools` y `call_tool`, que
    llegan a TODO el catálogo que puede usar el chat sin listarlo entero. `call_tool` despacha por el nombre REAL,
    así que en vivo pasa por los mismos controles del puente (modo, tarjeta Aplicar, APP_BUSY, bloqueos); los
    resultados se recortan como en el modo API (`asistente.herramientas.recortar`).
"""
import asyncio
import json
from concurrent.futures import ThreadPoolExecutor

from mcp.server.mcpserver import MCPServer
from mcp_types import Tool, ToolAnnotations

from .. import VERSION, api
from ..asistente.herramientas import TOPE_BUSQUEDA, Herramientas, encontrar, recortar, resumen
from . import textos
from .conversion import a_resultado_mcp
from .puente_cliente import ClientePuente

GRUPOS_CONOCIDOS = ("documento", "parametros", "boceto", "vectores", "solido", "chapa", "malla", "ensamble",
                    "material", "inspeccion", "animacion", "dibujo", "render", "avanzado", "grafo", "asistente", "dev")
# `dev` solo con --dev; `asistente` solo con --toolsets: assistant_ask gasta plata en la API del usuario.
GRUPOS_POR_DEFECTO = tuple(g for g in GRUPOS_CONOCIDOS if g not in ("dev", "asistente"))
MODOS = ("auto", "vivo", "sin_ventana")
AVISO_VIVO = ("MODO EN VIVO: desde ahora trabajás sobre el documento ABIERTO en la ventana de OmniCAD ({doc}), no "
              "sobre el documento sin ventana del servidor. El usuario ve cada cambio.")
AVISO_SIN_VENTANA = ("MODO SIN VENTANA: OmniCAD se cerró o apagó el puente. Desde ahora trabajás sobre el documento "
                     "propio del servidor ({doc}), que NO es el de la ventana: lo hecho en vivo no está acá.")
HERRAMIENTA_MODO = {"nombre": "get_mode", "grupo": "documento", "modifica": False,
                    "descripcion": "Dice en qué modo trabaja el servidor: 'vivo' (el documento abierto en la ventana de "
                                   "OmniCAD) o 'sin_ventana' (un documento propio del servidor), y el estado de la app.",
                    "esquema": {"type": "object", "properties": {}, "required": [], "additionalProperties": False}}
FIND_TOOLS = {"nombre": "find_tools", "grupo": "avanzado", "modifica": False,
              "descripcion": "Busca herramientas de OmniCAD que no están en tu lista (el índice del prompt dice cuáles "
                             f"hay) y devuelve hasta {TOPE_BUSQUEDA} con su esquema de argumentos, para usarlas con "
                             "call_tool. Pedilas por names (exactos, lo mejor), por query (palabras) o por group.",
              "esquema": {"type": "object", "properties": {
                  "names": {"type": "array", "items": {"type": "string"}, "description": "Nombres exactos."},
                  "query": {"type": "string", "description": "Qué necesitás, en pocas palabras."},
                  "group": {"type": "string", "description": "Un grupo del índice (p. ej. material, render)."}},
                  "additionalProperties": False}}
CALL_TOOL = {"nombre": "call_tool", "grupo": "avanzado", "modifica": True,
             "descripcion": "Ejecuta cualquier herramienta de OmniCAD por su nombre real (las del índice que no están "
                            "en tu lista), con sus argumentos. Si no sabés los argumentos, primero find_tools.",
             "esquema": {"type": "object", "properties": {
                 "name": {"type": "string", "description": "Nombre real de la herramienta (p. ej. set_appearance)."},
                 "args": {"type": "object", "description": "Sus argumentos, como en su esquema."}},
                 "required": ["name"], "additionalProperties": False}}


def _error(kind, mensaje, *pistas):
    return {"ok": False, "error_kind": kind, "mensaje": mensaje, "pistas": list(pistas)}


class ServidorOmniCAD(MCPServer):
    """`MCPServer` cuyas herramientas salen del catálogo de la API (ver el docstring del módulo)."""

    def __init__(self, sesion, herramientas, modo="sin_ventana", cliente=None, meta=False, **kwargs):
        super().__init__(**kwargs)
        if modo not in MODOS:
            raise ValueError(f"Modo desconocido: {modo} (válidos: {', '.join(MODOS)})")
        self.sesion = sesion
        self.modo = modo
        self.cliente = None if modo == "sin_ventana" else (cliente or ClientePuente())
        self.modo_activo = None                     # "vivo" | "sin_ventana": el de la última llamada
        self._herramientas = {h["nombre"]: h for h in herramientas}     # {nombre: entrada del catálogo}
        if self.cliente is not None:
            self._herramientas[HERRAMIENTA_MODO["nombre"]] = HERRAMIENTA_MODO
        # lo que el chat puede usar (sin dev, asistente ni execute_code); en vivo, el puente aplica además el modo
        self._alcance = Herramientas(modo="hacer").catalogo if meta else None
        if meta:
            self._herramientas.update({h["nombre"]: h for h in (FIND_TOOLS, CALL_TOOL)})
        self._ejecutor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="omnicad-api")

    @property
    def nombres(self):
        return list(self._herramientas)

    async def en_hilo(self, funcion, *args):
        """Ejecuta `funcion` en el hilo de la API (una llamada a la vez)."""
        return await asyncio.get_running_loop().run_in_executor(self._ejecutor, funcion, *args)

    def cerrar(self):
        self._ejecutor.shutdown(wait=False, cancel_futures=True)
        if self.cliente is not None:
            self.cliente.cerrar()

    # ------------------------------------------------------------ modos (corre en el hilo de la API)
    def despachar(self, nombre, args):
        """Ejecuta la herramienta donde corresponda según el modo. Devuelve el dict de `api.llamar`."""
        if nombre == HERRAMIENTA_MODO["nombre"] and self.cliente is not None:
            return self._get_mode()
        if self.cliente is None or self._herramientas.get(nombre, {}).get("grupo") == "dev":
            return api.llamar(self.sesion, nombre, args)
        if self.modo == "vivo":
            respuesta = self.cliente.llamar(nombre, args)
            self.modo_activo = None if respuesta.get("error_kind") == "APP_NOT_RUNNING" else "vivo"
            return respuesta
        vivo = self.cliente.conectar()                     # auto: la app, si está escuchando
        aviso = self._cambio_de_modo("vivo" if vivo else "sin_ventana")
        respuesta = self.cliente.llamar(nombre, args) if vivo else api.llamar(self.sesion, nombre, args)
        if aviso:
            respuesta["avisos"] = [aviso, *respuesta.get("avisos", [])]
        return respuesta

    def _cambio_de_modo(self, nuevo):
        """Aviso si el modo cambió, o si arranca en vivo (el agente espera un documento propio). Solo en auto."""
        anterior, self.modo_activo = self.modo_activo, nuevo
        if nuevo == anterior or (anterior is None and nuevo == "sin_ventana"):
            return None
        if nuevo == "vivo":
            estado = self.cliente.llamar("status", {})
            doc = f"«{estado['result']['document']}»" if estado.get("ok") else "el de la app"
            return AVISO_VIVO.format(doc=doc)
        return AVISO_SIN_VENTANA.format(doc=f"«{self.sesion.doc.nombre}»")

    def _get_mode(self):
        aviso = None
        if self.modo == "auto":
            aviso = self._cambio_de_modo("vivo" if self.cliente.conectar() else "sin_ventana")
        else:
            self.modo_activo = "vivo" if self.cliente.conectar() else None
        resultado = {"configured": self.modo, "active": self.modo_activo, "app": None}
        if self.modo_activo == "vivo":
            estado = self.cliente.llamar("status", {})
            resultado["app"] = estado["result"] if estado.get("ok") else None
            resultado["explanation"] = ("Las herramientas actúan sobre el documento abierto en la ventana de OmniCAD; "
                                        "el usuario ve cada cambio.")
        elif self.modo == "vivo":
            resultado["explanation"] = ("OmniCAD no está abierto con el puente encendido: las herramientas fallan con "
                                        "APP_NOT_RUNNING hasta que se abra.")
        else:
            resultado["explanation"] = (f"Las herramientas actúan sobre un documento propio del servidor "
                                        f"(«{self.sesion.doc.nombre}»), sin ventana. Si se abre OmniCAD con el puente "
                                        "encendido, el servidor pasa solo al modo en vivo y lo avisa.")
        return {"ok": True, "result": resultado, "avisos": [aviso] if aviso else []}

    # ------------------------------------------------------------ herramientas
    def _tool_input_schema(self, nombre):
        h = self._herramientas.get(nombre)
        return None if h is None else h["esquema"]

    async def list_tools(self):
        return [Tool(name=h["nombre"], description=h["descripcion"], input_schema=h["esquema"],
                     annotations=ToolAnnotations(read_only_hint=not h["modifica"]))
                for h in self._herramientas.values()]

    async def call_tool(self, name, arguments=None, context=None):
        arguments = arguments or {}
        if name not in self._herramientas:
            respuesta = _error("UNKNOWN_TOOL", f"No hay una herramienta activa llamada '{name}'.",
                               "Las activas dependen de --toolsets; tools/list las muestra.")
        elif self._alcance is not None and name == "find_tools":
            respuesta = self._find_tools(arguments)
        elif self._alcance is not None and name == "call_tool":
            real, args = arguments.get("name"), arguments.get("args")
            args = {} if args is None else args
            if not isinstance(real, str) or real not in self._alcance:
                respuesta = _error("TOOL_NOT_AVAILABLE", f"'{real}' no es una herramienta que el Asistente pueda usar.",
                                   "Las de desarrollo (dev), las del grupo asistente y execute_code no se usan desde "
                                   "el chat. find_tools busca las que sí.")
            elif not isinstance(args, dict):
                respuesta = _error("INVALID_ARGUMENTS", "args tiene que ser un objeto con los argumentos de la "
                                   "herramienta.", "find_tools(names=[...]) da su esquema.")
            else:
                respuesta = await self.en_hilo(self.despachar, real, args)
        else:
            respuesta = await self.en_hilo(self.despachar, name, arguments)
        resultado = a_resultado_mcp(respuesta)
        if self._alcance is not None and name != "find_tools":     # los esquemas que da find_tools no se cortan
            resultado.content[0].text = recortar(resultado.content[0].text)
        return resultado

    def _find_tools(self, args):
        try:
            encontradas, sobrantes, desconocidas = encontrar(self._alcance, args.get("query"), args.get("names"),
                                                             args.get("group"))
        except api.ErrorAPI as e:
            return e.a_dict()
        resultado = {"tools": [{"name": n, "description": resumen(self._alcance[n]["descripcion"]),
                                "modifies": self._alcance[n]["modifica"], "input_schema": self._alcance[n]["esquema"]}
                               for n in encontradas]}
        if sobrantes:
            resultado["more"] = sobrantes
        if desconocidas:
            resultado["unknown"] = desconocidas
        return {"ok": True, "result": resultado, "avisos": []}


def _registrar_recursos(servidor):
    def lector(tema):
        return lambda: textos.leer_guia(tema)

    for tema in textos.temas_guia():
        # Un resource fijo por tema: aparece en resources/list (los clientes que no usan plantillas lo ven).
        servidor.resource(f"omnicad://guia/{tema}", name=f"guia_{tema}", mime_type="text/markdown",
                          description=f"Guía para agentes: tema '{tema}'.")(lector(tema))

    @servidor.resource("omnicad://guia/{tema}", name="guia", mime_type="text/markdown",
                       description="Guía para agentes por tema (los .md de api/guia).")
    def guia(tema: str) -> str:
        return textos.leer_guia(tema)

    @servidor.resource("omnicad://receta", name="receta", mime_type="application/json",
                       description="Receta JSON del documento actual (parámetros, timeline y propiedades).")
    async def receta() -> str:
        r = await servidor.en_hilo(servidor.despachar, "get_recipe", {})
        if not r["ok"]:
            raise ValueError(r["mensaje"])
        return json.dumps(r["result"]["recipe"], ensure_ascii=False)


def _registrar_prompts(servidor):
    @servidor.prompt(name="disenar_pieza", description="Guía para diseñar una pieza: mirar, hacer, ver la imagen, "
                     "medir y guardar.")
    def disenar_pieza(descripcion: str) -> str:
        return textos.disenar_pieza(descripcion)

    @servidor.prompt(name="preparar_impresion_3d", description="Revisión del diseño actual para imprimirlo en 3D y "
                     "exportarlo.")
    def preparar_impresion_3d() -> str:
        return textos.preparar_impresion_3d()

    @servidor.prompt(name="revisar_diseno", description="Revisión del diseño actual: pasos, bocetos, imagen y "
                     "medidas.")
    def revisar_diseno() -> str:
        return textos.revisar_diseno()


def crear_servidor(sesion=None, toolsets=None, dev=False, log_level="WARNING", modo="sin_ventana", cliente=None,
                   herramientas=None, meta=False):
    """Arma el servidor. `toolsets`: grupos a exponer (por defecto todos menos `dev`); `dev=True` suma `dev`.
    `modo`: "sin_ventana" (por defecto acá: determinista para pruebas y scripts), "vivo" o "auto" (ver arriba);
    `cliente`: un `ClientePuente` propio (p. ej. con otro puente.json); `herramientas`: nombres (None = todas las
    de los grupos); `meta`: suma find_tools y call_tool (ver arriba)."""
    grupos = list(toolsets) if toolsets else list(GRUPOS_POR_DEFECTO)
    if dev and "dev" not in grupos:
        grupos.append("dev")
    catalogo = [h for h in api.catalogo(grupos) if herramientas is None or h["nombre"] in herramientas]
    servidor = ServidorOmniCAD(
        sesion if sesion is not None else api.Sesion(), catalogo, modo=modo, cliente=cliente, meta=meta,
        name="omnicad", title="OmniCAD", version=VERSION, instructions=textos.instrucciones(),
        log_level=log_level)
    _registrar_recursos(servidor)
    _registrar_prompts(servidor)
    return servidor

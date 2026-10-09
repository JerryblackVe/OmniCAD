# -*- coding: utf-8 -*-
"""
Cliente del puente en vivo (sin Qt): manda cada llamada a la app abierta por TCP local con el token de
`puente.json`. Protocolo: `omnicad/api/protocolo_puente.py`.

  - Una conexión persistente mientras la app responda (la app muestra «Agente IA conectado»). Antes de usarla se
    comprueba que siga viva; si la app se reinició, se relee puente.json y se reconecta.
  - Nunca lanza: los problemas vuelven como el dict de error de `api.llamar` (APP_NOT_RUNNING,
    APP_NOT_RESPONDING, BRIDGE_ERROR).
  - Lo usa un solo hilo (el de la API del servidor MCP): no hace falta bloqueo.
"""
import json
import select
import socket

from ..api import protocolo_puente as proto
from ..api.errores import error

TIEMPO_CONEXION = 2.0       # segundos para conectar a 127.0.0.1
TIEMPO_RESPUESTA = 120.0    # segundos para que la app conteste (un recálculo pesado puede tardar)


class ClientePuente:
    def __init__(self, archivo=None, tiempo_respuesta=TIEMPO_RESPUESTA):
        self.archivo = archivo                 # None = protocolo_puente.ruta_info() (se relee en cada conexión)
        self.tiempo_respuesta = tiempo_respuesta
        self.info = None                       # datos de puente.json de la conexión actual
        self._socket = None
        self._buffer = b""
        self._contador = 0

    # ------------------------------------------------------------ conexión
    def _vivo(self):
        """La conexión abierta sigue sirviendo: no hay nada para leer (la app no la cerró)."""
        if self._socket is None:
            return False
        try:
            legibles, _, _ = select.select([self._socket], [], [], 0)
            if not legibles:
                return True
            return bool(self._socket.recv(1, socket.MSG_PEEK))   # b"" = la app cerró la conexión
        except OSError:
            return False

    def conectar(self):
        """True si hay una app escuchando con el puente encendido (y deja la conexión abierta)."""
        if self._vivo():
            return True
        self.cerrar()
        info = proto.leer_info(self.archivo)
        if info is None:
            return False
        try:
            self._socket = socket.create_connection(("127.0.0.1", info["port"]), timeout=TIEMPO_CONEXION)
        except OSError:
            self._socket = None
            return False
        self.info, self._buffer = info, b""
        return True

    def cerrar(self):
        if self._socket is not None:
            try:
                self._socket.close()
            except OSError:
                pass
        self._socket, self.info, self._buffer = None, None, b""

    # ------------------------------------------------------------ llamadas
    def llamar(self, herramienta, args=None):
        """Llama `herramienta` en la app. Devuelve el dict de `api.llamar` con las imágenes como `api.Imagen`."""
        if not self.conectar():
            return error("APP_NOT_RUNNING", "OmniCAD no está abierto con el puente para agentes encendido "
                         f"(no hay una app escuchando según {self.archivo or proto.ruta_info()}).").a_dict()
        self._contador += 1
        ident = self._contador
        pedido = {"id": ident, "token": self.info["token"], "tool": herramienta, "args": args or {}}
        try:
            self._socket.settimeout(self.tiempo_respuesta)
            self._socket.sendall(proto.linea(pedido))
            texto = self._leer_linea()
        except TimeoutError:
            self.cerrar()                      # la respuesta tardía desordenaría la próxima: conexión nueva
            return error("APP_NOT_RESPONDING", f"OmniCAD no contestó «{herramienta}» en {self.tiempo_respuesta:g} s.").a_dict()
        except OSError as e:
            self.cerrar()
            return error("BRIDGE_ERROR", f"Se cortó la conexión con OmniCAD durante «{herramienta}» ({e}): no se sabe "
                         "si se aplicó.").a_dict()
        try:
            respuesta = json.loads(texto)
        except ValueError:
            self.cerrar()
            return error("BRIDGE_ERROR", "La app devolvió una respuesta que no es JSON.").a_dict()
        if not isinstance(respuesta, dict) or respuesta.get("id") != ident or "ok" not in respuesta:
            self.cerrar()
            return error("BRIDGE_ERROR", "La app devolvió una respuesta inesperada (id o formato).").a_dict()
        if respuesta.get("error_kind") == "UNAUTHORIZED":
            self.cerrar()                      # la app ya cerró esta conexión
        respuesta.pop("id")
        return proto.desde_cable(respuesta)

    def _leer_linea(self):
        while b"\n" not in self._buffer:
            trozo = self._socket.recv(1 << 16)
            if not trozo:
                raise ConnectionResetError("la app cerró la conexión")
            self._buffer += trozo
            if len(self._buffer) > proto.LINEA_MAXIMA:
                raise ConnectionError("respuesta demasiado grande")
        linea, _, self._buffer = self._buffer.partition(b"\n")
        return linea

# -*- coding: utf-8 -*-
"""
Puente para agentes IA (MCP en vivo): un agente ve y controla la app ABIERTA con las mismas herramientas de
`omnicad.api` que usa sin ventana. Protocolo y descubrimiento: `api/protocolo_puente.py`.

Decisiones:
  - `QTcpServer` SOLO en 127.0.0.1, dentro del bucle de eventos de Qt: sin hilos. Cada pedido corre entero en
    el hilo de la interfaz, así que nunca toca el documento al mismo tiempo que el usuario.
  - Token aleatorio (`secrets`) por arranque, en `puente.json` (carpeta del usuario). Token malo → UNAUTHORIZED y
    la conexión se cierra.
  - Las herramientas que MODIFICAN se rechazan con APP_BUSY si el usuario tiene un comando abierto, edita un
    boceto, está eligiendo un plano o hay un diálogo modal. Las que solo leen funcionan siempre.
  - `new_document` / `open_document`: si la ventana tiene cambios sin guardar → UNSAVED_CHANGES (no se
    descarta nada); si no, la ventana pasa a mostrar el documento nuevo.
  - `execute_code` en vivo: NO se permite salvo la preferencia `general/puente_codigo`. Corre Python en el hilo
    de la interfaz: un bucle infinito congelaría la app (con el trabajo del usuario adentro) y no hay forma
    segura de cortarlo desde el mismo hilo. Sin ventana (servidor MCP --modo sin_ventana) no tiene ese riesgo.
  - Las herramientas del grupo `dev` no corren en vivo: son del servidor MCP (pytest, capturas…).
"""
import json
import os
import secrets
from collections import deque

from PySide6.QtCore import QCoreApplication, QObject, Signal
from PySide6.QtNetwork import QHostAddress, QTcpServer
from PySide6.QtWidgets import QApplication, QLabel

from .. import VERSION, api
from ..api import protocolo_puente as proto
from ..api.errores import error

ESTILO_ESPERANDO = "color: #8a8a8a; padding: 0 10px;"
ESTILO_CONECTADO = "color: #1f1f1f; background: #6fcf6f; border-radius: 3px; padding: 0 8px; font-weight: bold;"


class PuenteAgentes(QObject):
    """Servidor local del modo en vivo. `ventana`: la `VentanaPrincipal` (su `doc` cambia con el tiempo).
    `archivo`: dónde escribir el puente.json (por defecto `protocolo_puente.ruta_info()`)."""

    conectados_cambio = Signal(int)

    def __init__(self, ventana, archivo=None):
        super().__init__(ventana)
        self.ventana = ventana
        self.archivo = archivo or proto.ruta_info()
        self.servidor = None
        self.puerto = None
        self.token = None
        self.sesion = api.Sesion(ventana.doc)
        self._conexiones = {}               # socket → {"buffer": bytearray, "autenticado": bool, "cerrando": bool}
        self._cola = deque()                # (socket, línea) pendientes: se atienden de a uno, sin reentrar
        self._atendiendo = False
        self._herramientas = {h["nombre"]: h for h in api.catalogo()}
        self.indicador = None
        app = QCoreApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self.detener)

    # ------------------------------------------------------------ encendido
    @property
    def activo(self):
        return self.servidor is not None and self.servidor.isListening()

    @property
    def conectados(self):
        return sum(1 for c in self._conexiones.values() if c["autenticado"])

    def iniciar(self, puerto=proto.PUERTO_POR_DEFECTO):
        """Escucha en 127.0.0.1 (el puerto pedido o uno de los 10 siguientes) y escribe puente.json."""
        if self.activo:
            return True
        servidor = QTcpServer(self)
        for p in range(puerto, puerto + proto.PUERTOS_EXTRA + 1):
            if servidor.listen(QHostAddress(QHostAddress.SpecialAddress.LocalHost), p):
                break
        else:
            servidor.deleteLater()
            return False
        servidor.newConnection.connect(self._nueva_conexion)
        self.servidor, self.puerto, self.token = servidor, servidor.serverPort(), secrets.token_urlsafe(32)
        try:
            proto.escribir_info(self.archivo, {"port": self.puerto, "token": self.token, "pid": os.getpid(),
                                               "version": VERSION, "protocol": proto.PROTOCOLO})
        except OSError:
            self.detener()
            return False
        self._actualizar_indicador()
        return True

    def detener(self):
        """Cierra las conexiones, deja de escuchar y borra puente.json (si sigue siendo el nuestro)."""
        for socket in list(self._conexiones):
            self._cerrar(socket)
        self._conexiones.clear()
        self._cola.clear()
        if self.servidor is not None:
            self.servidor.close()
            self.servidor.deleteLater()
            self.servidor = None
        if self.token is not None:
            proto.borrar_info(self.archivo, self.token)
        self.puerto = self.token = None
        self._actualizar_indicador()

    # ------------------------------------------------------------ estado de la ventana
    def motivo_ocupado(self):
        """Texto de por qué la app no acepta cambios ahora (o None si los acepta)."""
        v = self.ventana
        if v.panel is not None:
            titulo = getattr(getattr(v.panel, "comando", None), "TITULO", "") or "un comando"
            return f"el usuario está usando el comando «{titulo}»"
        if v.modo_boceto.activo:
            return "el usuario está editando un boceto"
        if v._eleccion is not None:
            return "el usuario está eligiendo un plano en la vista"
        modal = QApplication.activeModalWidget()
        if modal is not None:
            return f"hay un diálogo abierto en OmniCAD («{modal.windowTitle() or 'sin título'}»)"
        return None

    def estado(self):
        doc = self.ventana.doc
        motivo = self.motivo_ocupado()
        return {"app": "OmniCAD", "version": VERSION, "protocol": proto.PROTOCOLO, "pid": os.getpid(),
                "port": self.puerto, "document": doc.nombre, "path": doc.ruta, "modified": doc.modificado,
                "bodies": len(doc.estado_final.cuerpos), "timeline_steps": len(doc.operaciones),
                "busy": motivo is not None, "busy_reason": motivo,
                "command_open": self.ventana.panel is not None, "sketch_open": self.ventana.modo_boceto.activo,
                "execute_code_allowed": self.permite_codigo(), "agents_connected": self.conectados}

    def permite_codigo(self):
        return bool(self.ventana.prefs["general/puente_codigo"])

    # ------------------------------------------------------------ conexiones
    def _nueva_conexion(self):
        while self.servidor is not None and self.servidor.hasPendingConnections():
            socket = self.servidor.nextPendingConnection()
            self._conexiones[socket] = {"buffer": bytearray(), "autenticado": False, "cerrando": False}
            socket.readyRead.connect(lambda s=socket: self._leer(s))
            socket.disconnected.connect(lambda s=socket: self._desconectado(s))

    def _desconectado(self, socket):
        if self._conexiones.pop(socket, None) is not None:
            socket.deleteLater()
            self._actualizar_indicador()

    def _cerrar(self, socket):
        datos = self._conexiones.get(socket)
        if datos is not None:
            datos["cerrando"] = True
        try:
            socket.disconnectFromHost()       # manda lo pendiente (p. ej. la respuesta UNAUTHORIZED) y cierra
        except RuntimeError:                  # el objeto de Qt ya no existe
            pass

    def _leer(self, socket):
        datos = self._conexiones.get(socket)
        if datos is None or datos["cerrando"]:
            return
        datos["buffer"] += bytes(socket.readAll())
        while b"\n" in datos["buffer"]:
            linea, _, resto = bytes(datos["buffer"]).partition(b"\n")
            datos["buffer"] = bytearray(resto)
            if linea.strip():
                self._cola.append((socket, linea))
        if len(datos["buffer"]) > proto.LINEA_MAXIMA:
            self._responder(socket, {"id": None, **error("INVALID_REQUEST", "La línea supera el tamaño máximo.").a_dict()})
            self._cerrar(socket)
            return
        self._atender_cola()

    def _atender_cola(self):
        if self._atendiendo:                  # un diálogo o processEvents dentro de una herramienta: sin reentrar
            return
        self._atendiendo = True
        try:
            while self._cola:
                socket, linea = self._cola.popleft()
                datos = self._conexiones.get(socket)
                if datos is None or datos["cerrando"]:
                    continue
                respuesta = self._atender(datos, linea)
                self._responder(socket, respuesta)
                if respuesta.get("error_kind") == "UNAUTHORIZED":
                    self._cerrar(socket)      # después de mandar la respuesta: disconnectFromHost la despacha
        finally:
            self._atendiendo = False

    def _responder(self, socket, respuesta):
        try:
            socket.write(proto.linea(proto.a_cable(respuesta)))
            socket.flush()
        except RuntimeError:
            pass

    # ------------------------------------------------------------ pedidos
    def _atender(self, datos, linea):
        try:
            pedido = json.loads(linea.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            return {"id": None, **error("INVALID_REQUEST", "El pedido no es JSON válido en UTF-8.").a_dict()}
        if not isinstance(pedido, dict):
            return {"id": None, **error("INVALID_REQUEST", "El pedido tiene que ser un objeto JSON.").a_dict()}
        ident = pedido.get("id")
        token = pedido.get("token")
        if not isinstance(token, str) or self.token is None or not secrets.compare_digest(token, self.token):
            return {"id": ident, **error("UNAUTHORIZED", "Token incorrecto: conexión rechazada.").a_dict()}
        if not datos["autenticado"]:
            datos["autenticado"] = True
            self._actualizar_indicador()
        try:
            return {"id": ident, **self.ejecutar(pedido.get("tool"), pedido.get("args"))}
        except Exception as e:  # noqa: BLE001 — una falla del puente nunca tira la interfaz
            return {"id": ident, **error("INTERNAL_ERROR", f"{type(e).__name__}: {e}").a_dict()}

    def ejecutar(self, herramienta, args):
        """Atiende un pedido ya autenticado. Devuelve el dict de `api.llamar` (o un error del puente)."""
        v = self.ventana
        if herramienta == "ping":
            return {"ok": True, "result": {"pong": True, "version": VERSION, "protocol": proto.PROTOCOLO}, "avisos": []}
        if herramienta == "status":
            return {"ok": True, "result": self.estado(), "avisos": []}
        h = self._herramientas.get(herramienta) if isinstance(herramienta, str) else None
        if h is not None and h["grupo"] == "dev":
            return error("LIVE_NOT_ALLOWED", f"«{herramienta}» es una herramienta de desarrollo: corre en el servidor "
                         "MCP, no dentro de la ventana.").a_dict()
        if herramienta == "execute_code" and not self.permite_codigo():
            return error("LIVE_NOT_ALLOWED", "execute_code está desactivado en vivo: correría Python en el hilo de la "
                         "interfaz y un bucle infinito congelaría OmniCAD.").a_dict()
        modifica = h is not None and h["modifica"]
        if modifica:
            motivo = self.motivo_ocupado()
            if motivo:
                return error("APP_BUSY", f"OmniCAD está ocupado: {motivo}.",
                             "El usuario está usando la app: esperá o pedile que termine lo que está haciendo.").a_dict()
            if herramienta in ("new_document", "open_document") and v.doc.modificado:
                return error("UNSAVED_CHANGES", f"«{v.doc.nombre}» tiene cambios sin guardar en la ventana.").a_dict()
        doc = self.sesion.doc = v.doc
        pasos = len(doc.operaciones)
        respuesta = api.llamar(self.sesion, herramienta, args)
        if self.sesion.doc is not doc:                       # new_document / open_document
            v.set_documento(self.sesion.doc)
            if herramienta == "open_document" and respuesta["ok"] and self.sesion.doc.ruta:
                v._recordar(self.sesion.doc.ruta)
        elif modifica:
            if v.seleccion:
                v._seleccionar([])                           # lo elegido puede ya no existir
            v._actualizar()                                  # título, deshacer, «modificado» tras un rollback
        if modifica and respuesta["ok"]:
            nuevo = f" → {self.sesion.doc.operaciones[-1].nombre}" if len(self.sesion.doc.operaciones) > pasos else ""
            v.mensaje(f"Agente IA: {herramienta}{nuevo}", 5000)
        return respuesta

    # ------------------------------------------------------------ indicador visible
    def _actualizar_indicador(self):
        try:
            self._pintar_indicador()
        except RuntimeError:                  # al salir de la app la ventana ya puede no existir
            pass

    def _pintar_indicador(self):
        estado = self.ventana.timeline.estado
        if self.indicador is None:
            self.indicador = QLabel(objectName="indicador_agente")
            lay = estado.parentWidget().layout()
            lay.insertWidget(lay.indexOf(estado), self.indicador)
        n = self.conectados
        if not self.activo:
            self.indicador.hide()
        elif n:
            self.indicador.setText("● Agente IA conectado" + (f" ({n})" if n > 1 else ""))
            self.indicador.setStyleSheet(ESTILO_CONECTADO)
            self.indicador.setToolTip(f"{n} agente(s) IA controlan OmniCAD por el puente MCP en vivo "
                                      f"(127.0.0.1:{self.puerto}). Se apaga en Preferencias › General.")
            self.indicador.show()
        else:
            self.indicador.setText("Puente IA activo")
            self.indicador.setStyleSheet(ESTILO_ESPERANDO)
            self.indicador.setToolTip(f"OmniCAD acepta agentes IA en 127.0.0.1:{self.puerto} (con el token de "
                                      "puente.json). Se apaga en Preferencias › General.")
            self.indicador.show()
        self.conectados_cambio.emit(n)

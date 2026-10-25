# -*- coding: utf-8 -*-
"""
Panel del Asistente IA (IA-4), como el Autodesk Assistant de Fusion: acoplado a la derecha, con chat nuevo (+), menú
Chat (biblioteca de prompts), estrella con el aviso de IA, modos Explicar · Mostrar · Guiar · Hacer, campo
«Preguntale al Asistente» (Enter envía, Mayús+Enter salta de línea) y Enviar, que pasa a Cancelar mientras trabaja.

Hilos: el pedido a la IA corre en un hilo aparte (la red no congela la ventana). Las herramientas corren SIEMPRE en
el hilo de la interfaz, por `PuenteAgentes.ejecutar` (APP_BUSY, sin `dev` ni execute_code, refresco de la ventana),
y el hilo de trabajo espera el resultado (BlockingQueuedConnection). No usa el servidor TCP del puente: anda con
Preferencias › General › «agentes IA» apagado.

Permisos (IA-5), como *With me* / *For me* de Fusion: en Hacer y Guiar, antes de cambiar el documento el chat muestra
la tarjeta de plan con Aplicar y Cancelar (Hacer la pide una vez por pedido; Guiar, en cada tanda) y el hilo de
trabajo espera la respuesta. Antes de cada pedido se toma una marca del documento: Cancelar o el tope de gasto vuelven
a ella, y al terminar «Deshacer este pedido» también (si después no cambiaste nada a mano).
"""
import json
import threading

from PySide6.QtCore import QEventLoop, QObject, Qt, QTimer, Signal, Slot
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (QComboBox, QDockWidget, QFrame, QHBoxLayout, QLabel, QMenu, QPlainTextEdit, QPushButton,
                               QScrollArea, QSizePolicy, QToolButton, QVBoxLayout, QWidget)

from .. import api
from ..api.errores import error
from ..asistente import bucle, config, marca
from ..asistente.herramientas import MODOS, Herramientas
from ..asistente.prompt import armar_sistema, cargar_prompts
from ..asistente.proveedores.agente_local import AgenteLocal, matar
from ..asistente.proveedores.base import ErrorProveedor, PedidoHerramienta
from . import temas
from .puente import PuenteAgentes

TOPE_PEDIDO = 20000        # caracteres: un pegado gigante por error no se manda (gastaría plata)
SALUDO = "Hola, soy el Asistente de OmniCAD. Contame qué querés hacer o preguntame cómo se hace algo."
AVISO_IA = "El Asistente usa modelos de IA generativa: puede equivocarse. Revisá siempre lo que hace."
NOMBRES_MODO = {"explicar": "Explicar", "mostrar": "Mostrar", "guiar": "Guiar", "hacer": "Hacer"}
AYUDA_MODO = {"explicar": "Responde y explica; no cambia nada.", "mostrar": "Señala en el modelo: mueve la cámara y "
              "selecciona, sin cambiar el documento.", "guiar": "Propone un paso por vez y espera tu OK.",
              "hacer": "Arma un plan y, con tu OK, lo ejecuta."}


def config_de(prefs):
    return {k: prefs[f"asistente/{k}"] for k in config.CLAVES}


def _sin_imagenes(valor):
    """Respuesta de una herramienta sin las imágenes (Preferencias › «mandar imágenes del visor» apagado)."""
    if isinstance(valor, api.Imagen):
        return "(imagen no enviada: Preferencias › Asistente IA)"
    if isinstance(valor, dict):
        return {k: _sin_imagenes(v) for k, v in valor.items()}
    if isinstance(valor, list):
        return [_sin_imagenes(v) for v in valor]
    return valor


def _usd(valor):
    return f"{valor:.4f}".replace(".", ",") + " USD"


def resumen_herramienta(nombre, respuesta):
    """Línea plegada de una herramienta: «✓ extrude → op5» o «✗ fillet: OPERATION_FAILED»."""
    if not respuesta.get("ok"):
        return f"✗ {nombre}: {respuesta.get('error_kind', 'ERROR')}"
    resultado = respuesta.get("result")
    paso = resultado.get("feature") if isinstance(resultado, dict) else None
    return f"✓ {nombre}" + (f" → {paso['id']}" if isinstance(paso, dict) and paso.get("id") else "")


def resumen_pedido(nombre, args):
    """Línea legible de la tarjeta de plan: «extrude(profile="op2", distance=10)», con valores recortados."""
    partes = []
    for k, v in (args or {}).items():
        texto = json.dumps(v, ensure_ascii=False, default=str)
        partes.append(f"{k}={texto if len(texto) <= 40 else texto[:39] + '…'}")
    return f"{nombre}({', '.join(partes)})"


class _Tarjeta(QFrame):
    """Tarjeta de plan en el chat: lo que el Asistente va a cambiar, con Aplicar y Cancelar (Esc = Cancelar)."""

    def __init__(self, titulo, pedidos, decidir):
        super().__init__(objectName="tarjeta_asistente", frameShape=QFrame.StyledPanel)
        self.decidir = decidir
        self.pendiente = True
        v = QVBoxLayout(self)
        v.setContentsMargins(6, 6, 6, 6)
        cab = QLabel(titulo, wordWrap=True)
        temas.poner_rol(cab, "titulo")
        lista = QLabel("\n".join("• " + resumen_pedido(p.nombre, p.args) for p in pedidos), wordWrap=True,
                       textInteractionFlags=Qt.TextSelectableByMouse)
        for etiqueta in (cab, lista):
            etiqueta.setTextFormat(Qt.PlainText)
            etiqueta.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)   # angosto: corta, no ensancha
        self.estado = QLabel(wordWrap=True)
        temas.poner_rol(self.estado, "tenue")
        self.estado.hide()
        self.b_aplicar = QPushButton("Aplicar", objectName="boton_primario", toolTip="Hace los cambios de la lista.")
        self.b_cancelar = QPushButton("Cancelar", toolTip="No hace nada de la lista (Esc).")
        self.b_aplicar.clicked.connect(lambda: self.responder(True))
        self.b_cancelar.clicked.connect(lambda: self.responder(False))
        botones = QHBoxLayout()
        botones.addStretch(1)
        botones.addWidget(self.b_cancelar)
        botones.addWidget(self.b_aplicar)
        for w in (cab, lista, self.estado):
            v.addWidget(w)
        v.addLayout(botones)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape and self.pendiente:
            self.responder(False)
            return
        super().keyPressEvent(e)

    def responder(self, si):
        if self.pendiente:
            self.cerrar("✓ Aplicado" if si else "✗ No aprobado: no se hizo nada de la lista.")
            self.decidir(si)

    def cerrar(self, texto):
        self.pendiente = False
        for b in (self.b_aplicar, self.b_cancelar):
            b.hide()
        self.estado.setText(texto)
        self.estado.show()


class CampoPedido(QPlainTextEdit):
    """Campo multilínea: Enter envía, Mayús+Enter salta de línea, Esc avisa y Tab pasa al botón."""
    enviar = Signal()
    escape = Signal()

    def __init__(self):
        super().__init__(objectName="campo_asistente")
        self.setPlaceholderText("Preguntale al Asistente")
        self.setTabChangesFocus(True)
        self.setFixedHeight(self.fontMetrics().lineSpacing() * 4 + 12)

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key_Return, Qt.Key_Enter):
            if e.modifiers() & Qt.ShiftModifier:
                self.insertPlainText("\n")
            else:
                self.enviar.emit()
            return
        if e.key() == Qt.Key_Escape:
            self.escape.emit()
            return
        super().keyPressEvent(e)


class _EjecutorUI(QObject):
    """Vive en el hilo de la interfaz; el hilo de trabajo le pide una herramienta y espera la respuesta."""
    pedido = Signal(str, object, object)

    def __init__(self, puente, parent):
        super().__init__(parent)
        self.puente = puente
        self.pedido.connect(self._ejecutar, Qt.BlockingQueuedConnection)

    @Slot(str, object, object)
    def _ejecutar(self, nombre, args, caja):
        try:
            caja["r"] = self.puente.ejecutar(nombre, args)
        except Exception as e:  # noqa: BLE001 — una falla del puente nunca tira la interfaz
            caja["r"] = error("INTERNAL_ERROR", f"{type(e).__name__}: {e}").a_dict()

    def ejecutar(self, nombre, args):
        """Se llama desde el hilo de trabajo."""
        caja = {}
        self.pedido.emit(nombre, args, caja)
        return caja.get("r") or error("INTERNAL_ERROR", "La ventana de OmniCAD ya no está.").a_dict()


class _Trabajo(QObject):
    """Un pedido: corre `bucle.correr` en un hilo y avisa cada evento. El tope de gasto lo corta como un Cancelar."""
    evento = Signal(str, object)
    termino = Signal(object)

    def __init__(self, proveedor, mensajes, ejecutar, herramientas, sistema, tope_usd, texto=""):
        super().__init__()
        self.args = (proveedor, mensajes, ejecutar, herramientas, sistema)
        self.texto = texto              # modo suscripción: el pedido va entero al CLI, que guarda su propio chat
        self.listo = False
        self.tope_usd = tope_usd
        self.gasto = 0.0
        self.cancelar = threading.Event()
        self._decidido = threading.Event()
        self._aprobado = False

    @property
    def sobre_tope(self):
        return self.tope_usd > 0 and self.gasto > self.tope_usd

    def cancelado(self):
        return self.cancelar.is_set() or self.sobre_tope

    def aprobar(self, pedidos):
        """Hilo de trabajo: muestra la tarjeta de plan y espera Aplicar o Cancelar (un Cancelar del pedido corta)."""
        self._decidido.clear()
        self._aprobado = False
        self.evento.emit("aprobar", pedidos)
        while not self._decidido.wait(0.1):
            if self.cancelado():
                return False
        return self._aprobado

    def decidir(self, si):
        """Hilo de la interfaz: la respuesta de la tarjeta."""
        self._aprobado = si
        self._decidido.set()

    def _al_evento(self, tipo, datos):
        if tipo == "uso":
            self.gasto += datos.get("costo_usd") or 0
        self.evento.emit(tipo, datos)

    def correr(self):
        proveedor, mensajes, ejecutar, herramientas, sistema = self.args
        try:
            if isinstance(proveedor, AgenteLocal):
                resultado = proveedor.correr(self.texto, sistema, herramientas.modo, self._al_evento, self.cancelado)
            else:
                resultado = bucle.correr(proveedor, mensajes, ejecutar, herramientas, sistema, self._al_evento,
                                         cancelado=self.cancelado, aprobar=self.aprobar)
        except ErrorProveedor as e:
            self.evento.emit("error", str(e))
            resultado = {"motivo": "error"}
        except Exception as e:  # noqa: BLE001 — el hilo no tiene a quién avisar si no es por la señal
            self.evento.emit("error", f"{type(e).__name__}: {e}")
            resultado = {"motivo": "error"}
        if resultado["motivo"] == "cancelado" and self.sobre_tope and not self.cancelar.is_set():
            resultado["motivo"] = "tope_gasto"
        self.listo = True
        self.termino.emit(resultado)


class PanelAsistente(QDockWidget):
    cerrado = Signal()

    def __init__(self, ventana):
        super().__init__("Asistente", ventana)
        self.setObjectName("panel_asistente")
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.ventana = ventana
        self.puente = PuenteAgentes(ventana)          # sin iniciar(): no abre el puerto TCP
        self._ejecutor = _EjecutorUI(self.puente, self)
        self.crear_proveedor = config.crear_proveedor  # los tests ponen el proveedor falso
        self.mensajes = []
        self.trabajo = None
        self.tarjeta = None             # tarjeta de plan esperando Aplicar o Cancelar
        self._marca = None              # el documento antes del pedido en curso
        self.b_deshacer = None          # «Deshacer este pedido» del último pedido (los anteriores se apagan)
        self._aviso_ocupado = False
        self._uso = None
        self._sesiones = {}             # modo suscripción: id del chat de cada CLI, para seguir la conversación
        self._puente_vivo = None        # el puente por donde entra el CLI durante el pedido
        self._puente_temporal = False   # lo encendió el pedido (Preferencias › General lo tenía apagado)
        self._espera = None             # bucle de eventos mientras una tarjeta espera Aplicar dentro del puente
        self._aprobado = False

        cuerpo = QWidget()
        lay = QVBoxLayout(cuerpo)
        lay.setContentsMargins(6, 6, 6, 6)
        lay.setSpacing(6)

        cab = QHBoxLayout()
        self.etiqueta_modelo = QLabel(objectName="modelo_asistente")
        temas.poner_rol(self.etiqueta_modelo, "tenue")
        self.etiqueta_modelo.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.b_nuevo = QToolButton(text="+", toolTip="<b>Chat nuevo</b><br>Empieza una conversación desde cero.")
        self.b_nuevo.clicked.connect(self.nuevo_chat)
        self.b_chat = QToolButton(text="Chat", toolTip="<b>Chat</b><br>Biblioteca de prompts e historial.",
                                  popupMode=QToolButton.InstantPopup)
        self.b_chat.setMenu(self._menu_chat())
        self.b_aviso = QToolButton(text="✦", toolTip=AVISO_IA, autoRaise=True)
        for w in (self.b_nuevo, self.b_chat, self.b_aviso):
            w.setAutoRaise(True)
        cab.addWidget(self.etiqueta_modelo, 1)
        cab.addWidget(self.b_nuevo)
        cab.addWidget(self.b_chat)
        cab.addWidget(self.b_aviso)
        lay.addLayout(cab)

        self.area = QScrollArea(widgetResizable=True, frameShape=QFrame.NoFrame)
        self.lista = QWidget()
        self.lay_mensajes = QVBoxLayout(self.lista)
        self.lay_mensajes.setContentsMargins(0, 0, 0, 0)
        self.lay_mensajes.addStretch(1)
        self.area.setWidget(self.lista)
        self.area.verticalScrollBar().rangeChanged.connect(
            lambda _a, b: self.area.verticalScrollBar().setValue(b))   # siempre se ve lo último
        lay.addWidget(self.area, 1)

        self.pie = QLabel(objectName="uso_asistente", wordWrap=True)
        temas.poner_rol(self.pie, "tenue")
        lay.addWidget(self.pie)
        self.campo = CampoPedido()
        self.campo.enviar.connect(self.enviar)
        self.campo.escape.connect(self._escape)
        lay.addWidget(self.campo)
        abajo = QHBoxLayout()
        self.modo = QComboBox(objectName="modo_asistente")
        for clave in MODOS:
            self.modo.addItem(NOMBRES_MODO[clave], clave)
            self.modo.setItemData(self.modo.count() - 1, AYUDA_MODO[clave], Qt.ToolTipRole)
        self.modo.setToolTip("Modo del Asistente: Explicar y Mostrar no cambian el documento.")
        self.modo.setCurrentIndex(max(self.modo.findData(ventana.prefs["asistente/modo"]), 0))
        self.b_enviar = QPushButton("Enviar", objectName="boton_primario")
        self.b_enviar.clicked.connect(self._enviar_o_cancelar)
        abajo.addWidget(self.modo)
        abajo.addStretch(1)
        abajo.addWidget(self.b_enviar)
        lay.addLayout(abajo)
        self.setWidget(cuerpo)
        self.setMinimumWidth(190)       # con 821 px de visor (lo mínimo de la ventana) entra en 1024 de ancho
        self.actualizar_cabecera()
        self._agregar_texto(SALUDO)

    # ------------------------------------------------------------ cabecera y menú Chat
    def actualizar_cabecera(self):
        cfg = config_de(self.ventana.prefs)
        nombre = config.PROVEEDORES.get(cfg["proveedor"], (cfg["proveedor"],))[0]
        modelo = config.modelo_de(cfg) if cfg["proveedor"] in config.PROVEEDORES else ""
        texto = nombre + (f" · {modelo}" if modelo else "")
        self.etiqueta_modelo.setText(texto)
        self.etiqueta_modelo.setToolTip(texto + "<br>Se cambia en Preferencias › Asistente IA.")

    def _menu_chat(self):
        menu = QMenu(self)
        biblioteca = menu.addMenu("Biblioteca de prompts")
        espacios = {}
        for p in cargar_prompts():
            if p["espacio"] not in espacios:
                espacios[p["espacio"]] = biblioteca.addMenu(p["espacio"])
            a = espacios[p["espacio"]].addAction(f"{p['titulo']} ({NOMBRES_MODO[p['modo']]})")
            a.setToolTip(p["texto"])
            a.triggered.connect(lambda _=False, p=p: self.usar_prompt(p))
        historial = menu.addAction("Historial de chats")
        historial.setEnabled(False)                    # llega con IA-7 (historial local)
        historial.setToolTip("Todavía no: el historial de chats llega en una versión próxima.")
        menu.setToolTipsVisible(True)
        return menu

    def usar_prompt(self, p):
        """Biblioteca de prompts: deja el texto en el campo y el modo del ejemplo, sin mandarlo."""
        if self.trabajo is None:
            self.modo.setCurrentIndex(self.modo.findData(p["modo"]))
        self.campo.setPlainText(p["texto"])
        self.campo.setFocus()

    # ------------------------------------------------------------ mensajes
    def _agregar(self, widget):
        self.lay_mensajes.insertWidget(self.lay_mensajes.count() - 1, widget)
        return widget

    def _agregar_texto(self, texto, rol=None, usuario=False):
        etiqueta = QLabel(texto, wordWrap=True, textInteractionFlags=Qt.TextSelectableByMouse)
        etiqueta.setTextFormat(Qt.PlainText if usuario or rol else Qt.MarkdownText)
        if usuario:
            etiqueta.setFrameShape(QFrame.StyledPanel)
            etiqueta.setMargin(4)
            etiqueta.setObjectName("mensaje_usuario")
        if rol:
            temas.poner_rol(etiqueta, rol)
        return self._agregar(etiqueta)

    def _agregar_herramienta(self, nombre, args, respuesta):
        caja = QWidget()
        v = QVBoxLayout(caja)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)
        linea = QToolButton(text=resumen_herramienta(nombre, respuesta), checkable=True, autoRaise=True,
                            objectName="herramienta_asistente")
        linea.setToolTip("Clic para ver los argumentos y la respuesta.")
        detalle = QLabel(json.dumps({"args": args, "respuesta": respuesta}, ensure_ascii=False, indent=1,
                                    default=str)[:3000], wordWrap=True, textInteractionFlags=Qt.TextSelectableByMouse)
        detalle.setTextFormat(Qt.PlainText)
        temas.poner_rol(detalle, "tenue")
        detalle.hide()
        linea.toggled.connect(detalle.setVisible)
        v.addWidget(linea, 0, Qt.AlignLeft)
        v.addWidget(detalle)
        return self._agregar(caja)

    def _agregar_imagen(self, imagen):
        pm = QPixmap()
        pm.loadFromData(imagen.png, "PNG")
        etiqueta = QLabel(objectName="miniatura_asistente")
        etiqueta.setPixmap(pm.scaledToWidth(min(220, pm.width() or 220), Qt.SmoothTransformation))
        return self._agregar(etiqueta)

    def _mostrar_uso(self):
        u = self._uso
        if u is None:
            self.pie.clear()
            return
        costo = "costo no informado" if u["costo_usd"] is None else _usd(u["costo_usd"])
        self.pie.setText(f"Último pedido: {u['entrada']} tokens de entrada · {u['salida']} de salida · {costo}")

    # ------------------------------------------------------------ eventos del hilo de trabajo (llegan en cola)
    @Slot(str, object)
    def _evento(self, tipo, datos):
        if tipo == "texto":
            self._agregar_texto(datos)
        elif tipo == "herramienta":
            self._agregar_herramienta(datos["nombre"], datos["args"], datos["respuesta"])
            if datos["respuesta"].get("error_kind") == "APP_BUSY" and not self._aviso_ocupado:
                self._aviso_ocupado = True
                self._agregar_texto(f"⚠ {datos['respuesta'].get('mensaje', 'OmniCAD está ocupado.')} Terminá o "
                                    "cancelá el comando abierto (o salí del boceto) y reintentá el pedido.", "aviso")
        elif tipo == "aprobar":
            titulo = ("Plan del Asistente: con tu OK hace esto y sigue hasta terminar el pedido."
                      if self.trabajo.args[3].modo == "hacer" else "Próximo paso: con tu OK el Asistente hace esto.")
            self.tarjeta = self._agregar(_Tarjeta(titulo, datos, self._decidir))
        elif tipo == "imagen":
            self._agregar_imagen(datos)
        elif tipo == "error":
            self._agregar_texto(f"⚠ {datos}", "error")
        elif tipo == "uso":
            u = self._uso
            for k in ("entrada", "salida"):
                u[k] += datos.get(k) or 0
            if datos.get("costo_usd") is not None:
                u["costo_usd"] = (u["costo_usd"] or 0) + datos["costo_usd"]
            self._mostrar_uso()

    def _decidir(self, si):
        self.tarjeta = None
        if self.trabajo is not None:
            self.trabajo.decidir(si)

    @Slot(object)
    def _termino(self, resultado):
        if self._espera is not None:      # llegó con una tarjeta esperando adentro del puente: después de cerrarla
            QTimer.singleShot(50, lambda: self._termino(resultado))
            return
        proveedor = self.trabajo.args[0]
        if isinstance(proveedor, AgenteLocal):
            self._sesiones[proveedor.tipo] = proveedor.sesion
            self._soltar_puente()
        motivo, m = resultado["motivo"], self._marca
        if motivo == "tope_gasto":
            self._agregar_texto(f"⚠ Se cortó el pedido: el gasto superó el tope de {_usd(self.trabajo.tope_usd)} "
                                "(Preferencias › Asistente IA).", "aviso")
        elif motivo == "rechazado":
            self._agregar_texto("No aprobaste los cambios: no se hicieron.", "tenue")
        cambio = marca.cambio(m, self.ventana.doc)
        if motivo in ("cancelado", "tope_gasto"):
            if not cambio:
                self._agregar_texto("Pedido cancelado: el documento no cambió.", "tenue")
            elif self._volver(m):
                self._agregar_texto("Pedido cancelado: el documento volvió a como estaba antes del pedido.", "tenue")
                cambio = False
        if cambio:
            self._boton_deshacer(m, self.ventana.doc._instantanea())
        self.trabajo = None
        self._ocupado(False)

    # ------------------------------------------------------------ modo suscripción: puente en vivo y permisos
    def _preparar_puente(self, proveedor):
        """El CLI entra por el puente en vivo: usa el de la ventana si está prendido; si no, enciende el propio solo
        mientras dure el pedido. Pone el filtro de permisos y la sesión del CLI para seguir el chat."""
        v = self.ventana
        vivo = v.puente if v.puente is not None and v.puente.activo else self.puente
        self._puente_temporal = not vivo.activo
        if self._puente_temporal and not vivo.iniciar():
            self._agregar_texto("⚠ No se pudo encender el puente para agentes IA (puertos ocupados o carpeta sin "
                                "permiso): el agente no tendría cómo llegar a OmniCAD.", "error")
            return False
        vivo.filtro = self._filtro_en_vivo
        self._puente_vivo = vivo
        proveedor.sesion = self._sesiones.get(proveedor.tipo)
        return True

    def _soltar_puente(self):
        if self._puente_vivo is not None:
            self._puente_vivo.filtro = None
            if self._puente_temporal:
                self._puente_vivo.detener()
            self._puente_vivo = None

    def _filtro_en_vivo(self, nombre, args):
        """`PuenteAgentes.filtro` durante el pedido: la misma regla de modo que el modo API y la misma tarjeta
        Aplicar (Hacer aprueba una vez por pedido; Guiar, cada cambio). Corre en el hilo de la interfaz."""
        t = self.trabajo
        if t is None:
            return None
        herramientas = t.args[3]
        if nombre not in herramientas.catalogo:
            return error("TOOL_NOT_AVAILABLE", f"La herramienta '{nombre}' no se puede usar en el modo "
                         f"{herramientas.modo} del Asistente.",
                         "Explicale a la persona qué harías y que cambie a modo Guiar o Hacer.").a_dict()
        if self._aprobado or not herramientas.necesita_aprobacion(nombre):
            return None
        if self._aprobar_en_vivo([PedidoHerramienta("", nombre, args if isinstance(args, dict) else {})]):
            self._aprobado = herramientas.modo == "hacer"
            return None
        return error("CANCELLED", "La persona no aprobó este cambio; no se ejecutó nada.",
                     "Preguntale qué quiere cambiar del plan antes de proponer otro.").a_dict()

    def _aprobar_en_vivo(self, pedidos):
        """Muestra la tarjeta y espera Aplicar o Cancelar sin congelar la ventana (el puente está adentro de un
        pedido: los demás quedan en su cola). También corta si se cancela el pedido o el CLI terminó."""
        t = self.trabajo
        t._decidido.clear()
        t._aprobado = False
        self._evento("aprobar", pedidos)
        self._espera = espera = QEventLoop(self)
        reloj = QTimer(self, interval=50)
        reloj.timeout.connect(lambda: (t._decidido.is_set() or t.cancelado() or t.listo) and espera.quit())
        reloj.start()
        espera.exec()
        reloj.stop()
        reloj.deleteLater()
        self._espera = None
        if self.tarjeta is not None and not t._decidido.is_set():
            self.tarjeta.cerrar("El agente dejó de esperar: no se hizo nada de la lista.")
            self.tarjeta = None
        return t._aprobado and not t.cancelado()

    # ------------------------------------------------------------ deshacer el pedido entero
    def _volver(self, m):
        """Vuelve a la marca refrescando la ventana. Si no se puede ahora, lo dice en el chat y devuelve False."""
        v = self.ventana
        if v.doc is not m["doc"]:
            self._agregar_texto("⚠ No se pudo volver atrás: el pedido abrió o creó otro documento.", "aviso")
            return False
        ocupado = self.puente.motivo_ocupado()
        if ocupado:
            self._agregar_texto(f"⚠ No se pudo volver atrás: {ocupado}. Terminá o cancelá el comando abierto y usá "
                                "«Deshacer este pedido».", "aviso")
            return False
        marca.volver(m)
        if v.seleccion:
            v._seleccionar([])           # lo elegido puede ya no existir
        v.releer_espacios()
        return True

    def _boton_deshacer(self, m, fin):
        boton = QPushButton("Deshacer este pedido", objectName="deshacer_pedido",
                            toolTip="Deja el documento como estaba antes de este pedido.")
        boton.clicked.connect(lambda: self._deshacer_pedido(m, fin))
        self.b_deshacer = self._agregar(boton)

    def _apagar_deshacer(self, motivo="Solo se puede deshacer entero el último pedido; usá Deshacer (Ctrl+Z)."):
        """Apaga el botón y suelta su marca: guarda el documento y su pila de deshacer (pueden pesar cientos de MB con
        un STEP importado), por eso solo el último pedido se deshace entero."""
        if self.b_deshacer is not None:
            self.b_deshacer.clicked.disconnect()
            self.b_deshacer.setEnabled(False)
            self.b_deshacer.setToolTip(motivo)
            self.b_deshacer = None

    def _deshacer_pedido(self, m, fin):
        """Solo si el documento sigue como lo dejó el pedido: nunca se deshace trabajo hecho después a mano."""
        if self.trabajando:
            self._agregar_texto("Esperá a que termine el pedido en curso.", "tenue")
            return
        if self.ventana.doc is not m["doc"] or self.ventana.doc._instantanea() != fin:
            self._apagar_deshacer("Deshabilitado: el documento cambió después de este pedido.")
            self._agregar_texto("No se deshizo: el documento cambió después de este pedido (a mano o con otro "
                                "pedido) y se perdería ese trabajo. Usá Deshacer (Ctrl+Z) paso a paso.", "aviso")
            return
        if self._volver(m):
            self._apagar_deshacer("El pedido ya se deshizo.")
            self._agregar_texto("Listo: el documento volvió a como estaba antes del pedido.", "tenue")

    # ------------------------------------------------------------ enviar, cancelar, chat nuevo
    @property
    def trabajando(self):
        return self.trabajo is not None

    def _ocupado(self, si):
        self.b_enviar.setText("Cancelar" if si else "Enviar")
        self.b_enviar.setEnabled(True)
        for w in (self.modo, self.b_nuevo):
            w.setEnabled(not si)

    def _enviar_o_cancelar(self):
        self.cancelar() if self.trabajando else self.enviar()

    def _escape(self):
        if self.tarjeta is not None:
            self.tarjeta.responder(False)
        elif self.trabajando:
            self.cancelar()
        else:
            self.ventana.visor.setFocus()

    def enviar(self):
        """Manda lo escrito con el modo elegido. Campo vacío o pedido en curso: no hace nada."""
        texto = self.campo.toPlainText().strip()
        if self.trabajando or not texto:
            return False
        if len(texto) > TOPE_PEDIDO:
            self._agregar_texto(f"⚠ El pedido es muy largo ({len(texto)} caracteres; el máximo es {TOPE_PEDIDO}). "
                                "No se mandó.", "error")
            return False
        prefs = self.ventana.prefs
        try:
            proveedor = self.crear_proveedor(config_de(prefs))
        except ErrorProveedor as e:
            self._agregar_texto(f"⚠ {e}", "error")
            return False
        agente = isinstance(proveedor, AgenteLocal)
        if agente and not self._preparar_puente(proveedor):
            return False
        modo = self.modo.currentData()
        self.puente.sesion.doc = self.ventana.doc
        sistema = armar_sistema(self.puente.sesion, modo, self.ventana.leer_seleccion() or None)
        bloque = {"tipo": "texto", "texto": texto}
        if agente:
            pass                         # el CLI guarda la conversación (--resume / -s): acá no se acumula
        elif self.mensajes and self.mensajes[-1]["rol"] == "usuario":   # tras un Cancelar o un error: un solo turno
            self.mensajes[-1]["contenido"].append(bloque)
        else:
            self.mensajes.append({"rol": "usuario", "contenido": [bloque]})
        self._agregar_texto(texto, usuario=True)
        self.campo.clear()
        ejecutar = self._ejecutor.ejecutar
        if not prefs["asistente/imagenes"]:
            ejecutar = lambda nombre, args: _sin_imagenes(self._ejecutor.ejecutar(nombre, args))  # noqa: E731
        self._uso = {"entrada": 0, "salida": 0, "costo_usd": None}
        self._mostrar_uso()
        self._apagar_deshacer()
        self._marca = marca.tomar(self.ventana.doc)
        self._aviso_ocupado = False
        self._aprobado = False
        self.trabajo = _Trabajo(proveedor, self.mensajes, ejecutar, Herramientas(modo=modo), sistema,
                                prefs["asistente/tope_usd"], texto)
        self.trabajo.evento.connect(self._evento)
        self.trabajo.termino.connect(self._termino)
        self._ocupado(True)
        # Hilo de Python y no QThread: un pedido en vuelo al cerrar la app no aborta el proceso (daemon).
        threading.Thread(target=self.trabajo.correr, daemon=True, name="asistente").start()
        return True

    def cancelar(self):
        """Corta el bucle en la próxima vuelta o herramienta; al terminar, el documento vuelve a la marca."""
        if self.trabajando:
            self.trabajo.cancelar.set()
            proceso = getattr(self.trabajo.args[0], "proceso", None)
            if proceso is not None:
                matar(proceso)           # ya, sin esperar al vigía: al cerrar la app no queda el CLI huérfano
            if self.tarjeta is not None:
                self.tarjeta.cerrar("Pedido cancelado.")
                self.tarjeta = None
            self.b_enviar.setText("Cancelando…")
            self.b_enviar.setEnabled(False)

    def nuevo_chat(self):
        if self.trabajando:
            return
        self.mensajes = []
        self._sesiones = {}
        self._apagar_deshacer()
        while self.lay_mensajes.count() > 1:
            self.lay_mensajes.takeAt(0).widget().deleteLater()
        self._uso = None
        self._mostrar_uso()
        self._agregar_texto(SALUDO)
        self.campo.setFocus()

    def closeEvent(self, e):
        super().closeEvent(e)
        self.cerrado.emit()

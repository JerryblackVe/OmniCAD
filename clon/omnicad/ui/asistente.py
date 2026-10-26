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

Historial (IA-7): el chat se guarda solo al terminar cada pedido (`asistente/historial.py`, un JSON por chat, sin
claves); «Chat › Historial de chats» lista los guardados para abrir uno (la conversación sigue desde ahí) o borrarlo.

Adjuntos (IA-9): el clip (o Ctrl+V con una imagen, o arrastrar archivos al panel) suma PDF, PNG, JPG, SVG y DXF, hasta
10 por pedido (`asistente/adjuntos.py` los valida y prepara). Se ven como fichas arriba del campo y se van con el
pedido al enviar.

Selección (IA-13): lo elegido en el visor se ve en una ficha «🎯 …» arriba del campo y va descripto en el prompt («esto»
= la selección); su ✕ la saca de ese pedido.

Antes y después (IA-14): en Guiar y Hacer, al enviar se captura el visor y su cámara; si el pedido cambió el documento,
al terminar se captura otra vez con ESA cámara (y se devuelve la que dejó la IA) y el chat muestra las dos miniaturas;
clic (o Enter) en una la abre grande. No van al modelo; el historial las guarda achicadas.
"""
import json
import os
import tempfile
import threading

from PySide6.QtCore import QBuffer, QEventLoop, QIODevice, QObject, QSize, Qt, QTimer, Signal, Slot
from PySide6.QtGui import QImage, QPainter, QPixmap
from PySide6.QtWidgets import (QComboBox, QDialog, QDockWidget, QFileDialog, QFrame, QHBoxLayout, QLabel,
                               QListWidget, QListWidgetItem, QMenu, QMessageBox, QPlainTextEdit, QPushButton, QScrollArea,
                               QSizePolicy, QStyle, QToolButton, QVBoxLayout, QWidget)

from .. import api
from ..api.errores import ErrorAPI, error
from ..asistente import adjuntos, bucle, config, historial, marca
from ..asistente.herramientas import MODOS, Herramientas
from ..asistente.prompt import armar_sistema, cargar_prompts, resumen_seleccion
from ..asistente.proveedores.agente_local import AgenteLocal, matar
from ..asistente.proveedores.base import ErrorProveedor, PedidoHerramienta
from . import iconos, temas
from .preferencias import CampoInstrucciones
from .puente import PuenteAgentes

TOPE_PEDIDO = 20000        # caracteres: un pegado gigante por error no se manda (gastaría plata)
SALUDO = "Hola, soy el Asistente de OmniCAD. Contame qué querés hacer o preguntame cómo se hace algo."
AVISO_IA = "El Asistente usa modelos de IA generativa: puede equivocarse. Revisá siempre lo que hace."
NOMBRES_MODO = {"explicar": "Explicar", "mostrar": "Mostrar", "guiar": "Guiar", "hacer": "Hacer"}
AYUDA_MODO = {"explicar": "Responde y explica; no cambia nada.", "mostrar": "Señala en el modelo: mueve la cámara y "
              "selecciona, sin cambiar el documento.", "guiar": "Propone un paso por vez y espera tu OK.",
              "hacer": "Arma un plan y, con tu OK, lo ejecuta."}
ANCHO_HISTORIAL = 320      # px de las miniaturas de antes y después que se guardan en el historial
FILTRO_ADJUNTOS = ("Adjuntos (*.pdf *.png *.jpg *.jpeg *.svg *.dxf);;PDF (*.pdf);;Imágenes (*.png *.jpg *.jpeg);;"
                   "SVG (*.svg);;DXF (*.dxf)")


def config_de(prefs):
    return {k: prefs[f"asistente/{k}"] for k in config.CLAVES}


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


def achicar(png, ancho=ANCHO_HISTORIAL):
    """El PNG reescalado a `ancho` px (si es más ancho), para el historial."""
    imagen = QImage.fromData(png, "PNG")
    if imagen.width() <= ancho:
        return png
    buf = QBuffer()
    buf.open(QIODevice.WriteOnly)
    imagen.scaledToWidth(ancho, Qt.SmoothTransformation).save(buf, "PNG")
    return bytes(buf.data())


class _Miniatura(QWidget):
    """Una captura que se dibuja al ancho que le toca (dos entran lado a lado en el panel angosto); clic, Enter o
    espacio la abren grande."""

    def __init__(self, png, titulo, abrir):
        super().__init__(objectName="miniatura_comparacion", cursor=Qt.PointingHandCursor, focusPolicy=Qt.StrongFocus,
                         toolTip=f"{titulo}: clic para verla grande.")
        self.png, self.titulo, self.abrir = png, titulo, abrir
        self.pm = QPixmap()
        self.pm.loadFromData(png, "PNG")
        if self.pm.width() > ANCHO_HISTORIAL:     # la de tamaño completo pesa ~5 MB: un chat largo no la acumula
            self.pm = self.pm.scaledToWidth(ANCHO_HISTORIAL, Qt.SmoothTransformation)
        politica = QSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        politica.setHeightForWidth(True)
        self.setSizePolicy(politica)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, ancho):
        return max(1, round(ancho * self.pm.height() / max(self.pm.width(), 1)))

    def sizeHint(self):
        return QSize(120, self.heightForWidth(120))

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        p.drawPixmap(self.rect(), self.pm)
        if self.hasFocus():
            p.setPen(self.palette().highlight().color())
            p.drawRect(self.rect().adjusted(0, 0, -1, -1))

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.abrir(self.png, self.titulo)

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space):
            self.abrir(self.png, self.titulo)
            return
        super().keyPressEvent(e)


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


class DialogoInstrucciones(QDialog):
    """Chat › Instrucciones de este proyecto: se guardan dentro del .omnicad (con Guardar) y no entran en deshacer."""

    def __init__(self, panel):
        super().__init__(panel, objectName="instrucciones_proyecto", windowTitle="Instrucciones de este proyecto")
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.panel = panel
        v = QVBoxLayout(self)
        ayuda = QLabel("Van dentro del archivo: quien lo abra las verá. Se suman a tus instrucciones propias "
                       "(Preferencias › Asistente IA) y no pueden saltear los modos, la tarjeta Aplicar ni el tope "
                       "de gasto.", wordWrap=True)
        temas.poner_rol(ayuda, "tenue")
        self.campo = CampoInstrucciones(panel.ventana.doc.instrucciones,
                                        ayuda="Por ejemplo: «Es una pieza para imprimir en PETG; tolerancias de 0,2 mm».")
        b_cancelar = QPushButton("Cancelar")
        self.b_aceptar = QPushButton("Aceptar", objectName="boton_primario", default=True)
        b_cancelar.clicked.connect(self.reject)
        self.b_aceptar.clicked.connect(self.accept)
        botones = QHBoxLayout()
        botones.addWidget(self.campo.contador, 1)
        botones.addWidget(b_cancelar)
        botones.addWidget(self.b_aceptar)
        v.addWidget(ayuda)
        v.addWidget(self.campo, 1)
        v.addLayout(botones)
        self.resize(420, 300)

    def accept(self):
        doc = self.panel.ventana.doc
        doc.fijar_instrucciones(self.campo.texto())   # el campo ya corta al tope: no puede fallar por largo
        self.panel._avisadas.add(doc.token)            # las escribió la persona: no hace falta avisarle
        super().accept()


class DialogoHistorial(QDialog):
    """Chat › Historial de chats: los guardados, el más nuevo primero. Abrir (doble clic o Enter) lo carga en el panel;
    Borrar… (o Supr) pregunta antes."""

    def __init__(self, panel):
        super().__init__(panel, objectName="historial_asistente", windowTitle="Historial de chats")
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.panel = panel
        v = QVBoxLayout(self)
        self.vacio = QLabel("Todavía no hay chats guardados: se guardan solos al terminar cada pedido.", wordWrap=True)
        temas.poner_rol(self.vacio, "tenue")
        self.lista = QListWidget(objectName="lista_historial")
        self.lista.itemActivated.connect(self.abrir)
        self.lista.currentRowChanged.connect(self._botones)
        self.b_abrir = QPushButton("Abrir", default=True, toolTip="Carga el chat en el panel para seguirlo.")
        self.b_borrar = QPushButton("Borrar…", toolTip="Borra el chat elegido (pregunta antes; no se puede deshacer).")
        b_cerrar = QPushButton("Cerrar")
        self.b_abrir.clicked.connect(self.abrir)
        self.b_borrar.clicked.connect(self.borrar)
        b_cerrar.clicked.connect(self.reject)
        botones = QHBoxLayout()
        botones.addWidget(self.b_borrar)
        botones.addStretch(1)
        botones.addWidget(b_cerrar)
        botones.addWidget(self.b_abrir)
        v.addWidget(self.vacio)
        v.addWidget(self.lista, 1)
        v.addLayout(botones)
        self.resize(360, 400)
        self.releer()

    def releer(self):
        self.lista.clear()
        for c in historial.listar():
            fecha = c["fecha"].replace("T", " ")[:16]
            proveedor = config.PROVEEDORES.get(c["proveedor"], (c["proveedor"] or "",))[0]
            item = QListWidgetItem(f"{c['titulo']}\n{fecha} · {NOMBRES_MODO.get(c['modo'], c['modo'])} · {proveedor}")
            item.setData(Qt.UserRole, c["id"])
            item.setToolTip(f"{c['mensajes']} mensajes · {c['modelo'] or 'modelo de fábrica'}")
            self.lista.addItem(item)
        self.vacio.setVisible(self.lista.count() == 0)
        self.lista.setCurrentRow(0)
        self._botones()

    def _botones(self, *_):
        for b in (self.b_abrir, self.b_borrar):
            b.setEnabled(self.lista.currentItem() is not None)

    def _elegido(self):
        item = self.lista.currentItem()
        return item.data(Qt.UserRole) if item is not None else None

    def abrir(self, *_):
        id_chat = self._elegido()
        if id_chat and self.panel.cargar_chat(id_chat):
            self.accept()

    def borrar(self):
        id_chat = self._elegido()
        if not id_chat:
            return
        titulo = self.lista.currentItem().text().split("\n")[0]
        if QMessageBox.question(self, "Borrar chat", f"¿Borrar el chat «{titulo}»? No se puede deshacer.",
                                QMessageBox.Ok | QMessageBox.Cancel, QMessageBox.Cancel) != QMessageBox.Ok:
            return
        try:
            historial.borrar(id_chat)
        except (historial.ErrorHistorial, OSError) as e:
            QMessageBox.warning(self, "Borrar chat", f"No se pudo borrar: {e}")
            return
        if self.panel.id_chat == id_chat:
            self.panel.id_chat = None          # el chat sigue en pantalla: el próximo pedido lo guarda como nuevo
        self.releer()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Delete:
            self.borrar()
            return
        super().keyPressEvent(e)


class _Ficha(QFrame):
    """Un adjunto arriba del campo: miniatura (o su tipo), nombre y ✕ para quitarlo."""

    def __init__(self, adjunto, quitar):
        super().__init__(objectName="ficha_adjunto", frameShape=QFrame.StyledPanel, toolTip=adjunto.ruta)
        h = QHBoxLayout(self)
        h.setContentsMargins(3, 1, 1, 1)
        h.setSpacing(3)
        icono = QLabel(alignment=Qt.AlignCenter)
        icono.setFixedSize(24, 24)
        if adjunto.miniatura:
            pm = QPixmap()
            pm.loadFromData(adjunto.miniatura, "PNG")
            icono.setPixmap(pm.scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            icono.setText(adjuntos.NOMBRES[adjunto.clase])
        nombre = QLabel(self.fontMetrics().elidedText(adjunto.nombre, Qt.ElideMiddle, 90))
        self.b_quitar = QToolButton(text="✕", autoRaise=True, toolTip=f"Quitar «{adjunto.nombre}» del pedido.")
        self.b_quitar.clicked.connect(lambda: quitar(adjunto))
        for w in (icono, nombre, self.b_quitar):
            h.addWidget(w)


def _rutas_locales(mime):
    return [u.toLocalFile() for u in mime.urls() if u.isLocalFile()] if mime.hasUrls() else []


class CampoPedido(QPlainTextEdit):
    """Campo multilínea: Enter envía, Mayús+Enter salta de línea, Esc avisa y Tab pasa al botón. Pegar o soltar
    archivos los adjunta, y pegar una imagen sola (sin texto) también; el texto se pega como siempre."""
    enviar = Signal()
    escape = Signal()
    archivos = Signal(list)
    imagen = Signal(object)

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

    def canInsertFromMimeData(self, mime):
        return bool(_rutas_locales(mime)) or mime.hasImage() or super().canInsertFromMimeData(mime)

    def insertFromMimeData(self, mime):
        """Ctrl+V y soltar sobre el campo. Con texto e imagen a la vez (copiar de Word) gana el texto."""
        rutas = _rutas_locales(mime)
        if rutas:
            self.archivos.emit(rutas)
        elif mime.hasImage() and not mime.hasText():
            self.imagen.emit(mime.imageData())
        else:
            super().insertFromMimeData(mime)


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

    def __init__(self, proveedor, mensajes, ejecutar, herramientas, sistema, tope_usd, texto="", adjuntos=()):
        super().__init__()
        self.args = (proveedor, mensajes, ejecutar, herramientas, sistema)
        self.texto = texto              # modo suscripción: el pedido va entero al CLI, que guarda su propio chat
        self.adjuntos = adjuntos        # modo suscripción: los bloques imagen y documento de los adjuntos
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
                resultado = proveedor.correr(self.texto, sistema, herramientas.modo, self._al_evento, self.cancelado,
                                             self.adjuntos)
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
        self.id_chat = None             # el JSON del historial donde se guarda este chat (None: todavía no se guardó)
        self.trabajo = None
        self.tarjeta = None             # tarjeta de plan esperando Aplicar o Cancelar
        self._marca = None              # el documento antes del pedido en curso
        self.b_deshacer = None          # «Deshacer este pedido» del último pedido (los anteriores se apagan)
        self._antes = None              # (PNG, cámara) del visor al enviar en Guiar o Hacer
        self.comparaciones = []         # antes y después de este chat, achicados, para el historial
        self._aviso_ocupado = False
        self._uso = None
        self._sesiones = {}             # modo suscripción: id del chat de cada CLI, para seguir la conversación
        self._puente_vivo = None        # el puente por donde entra el CLI durante el pedido
        self._puente_temporal = False   # lo encendió el pedido (Preferencias › General lo tenía apagado)
        self._espera = None             # bucle de eventos mientras una tarjeta espera Aplicar dentro del puente
        self._aprobado = False
        self.adjuntos = []              # los del próximo pedido (asistente.adjuntos.Adjunto)
        self._pegados = None            # carpeta temporal de las imágenes pegadas (se borra al cerrar OmniCAD)
        self._avisadas = set()          # documentos (token) cuyas instrucciones de proyecto ya se avisaron
        self.setAcceptDrops(True)       # soltar archivos en cualquier parte del panel los adjunta

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
        self.fila_adjuntos = QWidget(objectName="adjuntos_asistente")
        fila = QHBoxLayout(self.fila_adjuntos)
        fila.setContentsMargins(0, 0, 0, 0)
        self.fichas = QWidget()
        self.lay_fichas = QHBoxLayout(self.fichas)
        self.lay_fichas.setContentsMargins(0, 0, 0, 0)
        self.lay_fichas.setSpacing(4)
        self.lay_fichas.addStretch(1)
        zona = QScrollArea(widgetResizable=True, frameShape=QFrame.NoFrame)
        zona.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        zona.setWidget(self.fichas)
        zona.setFixedHeight(32 + self.style().pixelMetric(QStyle.PM_ScrollBarExtent))   # muchas fichas: se desplazan
        self.contador = QLabel(objectName="contador_adjuntos")
        temas.poner_rol(self.contador, "tenue")
        fila.addWidget(zona, 1)
        fila.addWidget(self.contador)
        self.fila_adjuntos.hide()
        lay.addWidget(self.fila_adjuntos)
        self.ficha_sel = QFrame(objectName="ficha_seleccion", frameShape=QFrame.StyledPanel)
        h = QHBoxLayout(self.ficha_sel)
        h.setContentsMargins(4, 1, 1, 1)
        h.setSpacing(3)
        self.texto_sel = QLabel(wordWrap=True)       # en 190 px la medida baja a otra línea en vez de cortarse
        self.texto_sel.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)   # un texto largo no ensancha el panel
        self.b_sin_sel = QToolButton(text="✕", autoRaise=True, toolTip="No mandar la selección en este pedido. "
                                                                       "Vuelve si elegís otra cosa.")
        self.b_sin_sel.clicked.connect(self.quitar_seleccion)
        h.addWidget(self.texto_sel, 1)
        h.addWidget(self.b_sin_sel)
        self.ficha_sel.hide()
        lay.addWidget(self.ficha_sel)
        self._sin_seleccion = None      # la selección que ✕ sacó del pedido (otra selección la vuelve a mostrar)
        self.campo = CampoPedido()
        self.campo.enviar.connect(self.enviar)
        self.campo.escape.connect(self._escape)
        self.campo.archivos.connect(self.adjuntar)
        self.campo.imagen.connect(self.pegar_imagen)
        self.b_clip = QToolButton(objectName="clip_asistente", icon=iconos.icono("clip"), autoRaise=True,
                                  toolTip=f"<b>Adjuntar</b><br>PDF, imágenes (PNG, JPG), SVG o DXF; hasta "
                                          f"{adjuntos.MAXIMO} por pedido. También: Ctrl+V con una imagen copiada, o "
                                          "arrastrar archivos al panel.")
        self.b_clip.clicked.connect(self.elegir_archivos)
        fila_campo = QHBoxLayout()      # el clip al lado del campo (en la fila de Enviar ensanchaba el panel)
        fila_campo.setSpacing(2)
        fila_campo.addWidget(self.campo, 1)
        fila_campo.addWidget(self.b_clip, 0, Qt.AlignTop)
        lay.addLayout(fila_campo)
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
        self.revisar_instrucciones()
        self.actualizar_seleccion()

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
        accion = menu.addAction("Instrucciones de este proyecto…")
        accion.setToolTip("Lo que el Asistente tiene que saber de ESTE diseño; se guarda dentro del archivo. Las tuyas, "
                          "para todos los chats, van en Preferencias › Asistente IA.")
        accion.triggered.connect(self.editar_instrucciones)
        accion = menu.addAction("Historial de chats")
        accion.setToolTip("Los chats guardados en esta PC: abrir uno para seguirlo, o borrarlo.")
        accion.triggered.connect(self.abrir_historial)
        menu.setToolTipsVisible(True)
        return menu

    def editar_instrucciones(self):
        dialogo = DialogoInstrucciones(self)
        dialogo.open()
        return dialogo

    def revisar_instrucciones(self):
        """La primera vez que un documento abierto trae instrucciones de proyecto, lo avisa en el chat: son texto de
        quien hizo el archivo y van al prompt en cada pedido."""
        doc = self.ventana.doc
        if doc is None or not doc.instrucciones or doc.token in self._avisadas:
            return
        self._avisadas.add(doc.token)
        texto = doc.instrucciones if len(doc.instrucciones) <= 300 else doc.instrucciones[:300] + "…"
        self._agregar_texto(f"⚠ Este archivo trae instrucciones para el Asistente (las escribió quien lo hizo): «{texto}». "
                            "Se usan como preferencias, nunca para saltear la tarjeta Aplicar. Revisalas o borralas en "
                            "Chat › Instrucciones de este proyecto.", "aviso")

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
            if isinstance(self.trabajo.args[0], AgenteLocal):     # el modo API ya lo guarda el bucle
                self._sumar("asistente", {"tipo": "texto", "texto": datos})
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
        elif tipo == "aviso":
            self._agregar_texto(f"⚠ {datos}", "aviso")
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
        if cambio and self._antes is not None:
            self._antes_despues(*self._antes)
        self._antes = None
        if cambio:
            self._boton_deshacer(m, self.ventana.doc._instantanea())
        modo = self.trabajo.args[3].modo
        self.trabajo = None
        self._ocupado(False)
        self._guardar_chat(modo)

    # ------------------------------------------------------------ antes y después (IA-14)
    def _camara(self):
        v = self.ventana.visor
        return v.objetivo.copy(), v.distancia, v.R.copy(), v._orto_cara, v.config.camara, v.fov

    def _poner_camara(self, c):
        v = self.ventana.visor
        v.objetivo, v.distancia, v.R = c[0].copy(), c[1], c[2].copy()
        v._orto_cara, v.config.camara, v.fov = c[3:]

    def _capturar(self):
        try:
            return self.ventana.capturar_visor()[0]
        except ErrorAPI:                 # el visor todavía no dibujó: el pedido sigue, sin antes y después
            return None

    def _antes_despues(self, antes, camara):
        """Captura «Después» con la cámara de «Antes» y deja la que puso la IA; muestra el par y lo suma al historial."""
        de_la_ia = self._camara()
        self._poner_camara(camara)
        despues = self._capturar()
        self._poner_camara(de_la_ia)
        self.ventana.visor.update()
        if despues is not None:
            self._mostrar_comparacion(antes, despues)
            self.comparaciones.append({"pos": len(self.mensajes), "antes": achicar(antes),
                                       "despues": achicar(despues)})

    def _mostrar_comparacion(self, antes, despues):
        caja = QWidget(objectName="antes_despues")
        h = QHBoxLayout(caja)
        h.setContentsMargins(0, 0, 0, 0)
        for titulo, png in (("Antes", antes), ("Después", despues)):
            col = QVBoxLayout()
            col.setSpacing(2)
            rotulo = QLabel(titulo)
            temas.poner_rol(rotulo, "tenue")
            col.addWidget(rotulo)
            col.addWidget(_Miniatura(png, titulo, self.ver_grande))
            h.addLayout(col, 1)
        return self._agregar(caja)

    def ver_grande(self, png, titulo):
        """La captura en un diálogo, achicada si no entra en la pantalla; Esc lo cierra."""
        dialogo = QDialog(self, objectName="imagen_grande", windowTitle=titulo)
        dialogo.setAttribute(Qt.WA_DeleteOnClose)
        pm = QPixmap()
        pm.loadFromData(png, "PNG")
        lugar = (self.screen().availableSize() * 0.85).boundedTo(pm.size())
        etiqueta = QLabel(pixmap=pm.scaled(lugar, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        QVBoxLayout(dialogo).addWidget(etiqueta)
        dialogo.open()
        return dialogo

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
        proveedor.carpeta_puente = os.path.dirname(vivo.archivo)   # el CLI va a ESTE puente, no a otra OmniCAD abierta
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
        """Manda lo escrito y los adjuntos con el modo elegido. Sin texto ni adjuntos, o con un pedido en curso: no
        hace nada."""
        texto = self.campo.toPlainText().strip()
        if self.trabajando or not (texto or self.adjuntos):
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
        self.revisar_instrucciones()
        refs = self.ventana.leer_seleccion()
        sistema = armar_sistema(self.puente.sesion, modo, refs if refs and refs != self._sin_seleccion else None,
                                prefs["asistente/instrucciones"])
        self._sin_seleccion = None      # el ✕ vale para este pedido
        self.actualizar_seleccion()
        # El CLI del modo suscripción guarda su propia conversación (--resume / -s): acá se suma solo para el historial.
        bloques = [b for a in self.adjuntos for b in a.bloques]
        for bloque in ([{"tipo": "texto", "texto": texto}] if texto else []) + bloques:
            self._sumar("usuario", bloque)
        if texto:
            self._agregar_texto(texto, usuario=True)
        if self.adjuntos:
            self._agregar_texto("Adjuntos: " + ", ".join(a.nombre for a in self.adjuntos), "tenue")
        texto_cli = "\n\n".join(([texto] if texto else []) + [b["texto"] for b in bloques if b["tipo"] == "texto"])
        self.adjuntos = []
        self._mostrar_fichas()
        self.campo.clear()
        ejecutar = self._ejecutor.ejecutar
        if not prefs["asistente/imagenes"]:
            ejecutar = lambda nombre, args: bucle.sin_imagenes(self._ejecutor.ejecutar(nombre, args))  # noqa: E731
        self._uso = {"entrada": 0, "salida": 0, "costo_usd": None}
        self._mostrar_uso()
        self._apagar_deshacer()
        self._marca = marca.tomar(self.ventana.doc)
        png = self._capturar() if modo in ("guiar", "hacer") else None
        self._antes = (png, self._camara()) if png is not None else None
        self._aviso_ocupado = False
        self._aprobado = False
        self.trabajo = _Trabajo(proveedor, self.mensajes, ejecutar, Herramientas(modo=modo), sistema,
                                prefs["asistente/tope_usd"], texto_cli,
                                [b for b in bloques if b["tipo"] in ("imagen", "documento")])
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

    # ------------------------------------------------------------ selección del visor (IA-13)
    def actualizar_seleccion(self):
        """La ficha «🎯 1 cara de Caja (40 × 20 mm)» arriba del campo; la ventana la llama en cada cambio de selección.
        Sin selección, o con la que se sacó con ✕, no hay ficha."""
        refs = self.ventana.leer_seleccion()
        if refs != self._sin_seleccion:
            self._sin_seleccion = None
        self.puente.sesion.doc = self.ventana.doc
        texto = resumen_seleccion(self.puente.sesion, refs) if refs and self._sin_seleccion is None else ""
        self.texto_sel.setText(f"🎯 {texto}")
        self.ficha_sel.setToolTip(f"Selección: {texto}. El Asistente la entiende como «esto».")
        self.ficha_sel.setVisible(bool(texto))

    def quitar_seleccion(self):
        self._sin_seleccion = self.ventana.leer_seleccion()
        self.actualizar_seleccion()

    # ------------------------------------------------------------ adjuntos
    def elegir_archivos(self):
        """Clic en el clip: diálogo de archivos con los tipos permitidos."""
        rutas, _filtro = QFileDialog.getOpenFileNames(self, "Adjuntar al pedido", "", FILTRO_ADJUNTOS)
        return self.adjuntar(rutas)

    def adjuntar(self, rutas):
        """Suma los archivos al próximo pedido; los que no se pueden (tipo, tamaño, el 11.º) se avisan en el chat.
        Devuelve cuántos sumó."""
        sumados = 0
        for ruta in rutas:
            # shortcut: lee y dibuja en el hilo de la interfaz (un DXF de 10 MB la congela ~1 s); pasarlo a un hilo
            # si molesta.
            try:
                self.adjuntos.append(adjuntos.preparar(ruta, len(self.adjuntos)))
                sumados += 1
            except adjuntos.ErrorAdjunto as e:
                self._agregar_texto(f"⚠ {e}", "aviso")
        self._mostrar_fichas()
        return sumados

    def pegar_imagen(self, imagen):
        """Ctrl+V con una imagen en el portapapeles: la guarda como PNG temporal y la adjunta."""
        if self._pegados is None:
            self._pegados = tempfile.TemporaryDirectory(prefix="omnicad_pegado_", ignore_cleanup_errors=True)
        ruta = os.path.join(self._pegados.name, f"pegada_{len(os.listdir(self._pegados.name)) + 1}.png")
        if imagen is None or imagen.isNull() or not imagen.save(ruta, "PNG"):
            self._agregar_texto("⚠ No se pudo pegar la imagen del portapapeles.", "aviso")
            return 0
        return self.adjuntar([ruta])

    def quitar_adjunto(self, adjunto):
        self.adjuntos.remove(adjunto)
        self._mostrar_fichas()

    def _mostrar_fichas(self):
        while self.lay_fichas.count() > 1:
            self.lay_fichas.takeAt(0).widget().deleteLater()
        for a in self.adjuntos:
            self.lay_fichas.insertWidget(self.lay_fichas.count() - 1, _Ficha(a, self.quitar_adjunto))
        self.contador.setText(f"{len(self.adjuntos)}/{adjuntos.MAXIMO}")
        self.fila_adjuntos.setVisible(bool(self.adjuntos))

    def dragEnterEvent(self, e):
        if _rutas_locales(e.mimeData()):
            e.acceptProposedAction()

    def dropEvent(self, e):
        rutas = _rutas_locales(e.mimeData())
        if rutas:
            e.acceptProposedAction()
            self.adjuntar(rutas)

    def _sumar(self, rol, bloque):
        """Agrega un bloque al chat; dos seguidos del mismo rol van en un solo turno (tras un Cancelar o un error)."""
        if self.mensajes and self.mensajes[-1]["rol"] == rol:
            self.mensajes[-1]["contenido"].append(bloque)
        else:
            self.mensajes.append({"rol": rol, "contenido": [bloque]})

    def _limpiar(self):
        self._apagar_deshacer()
        while self.lay_mensajes.count() > 1:
            self.lay_mensajes.takeAt(0).widget().deleteLater()
        self._uso = None
        self._mostrar_uso()

    def nuevo_chat(self):
        if self.trabajando:
            return
        self.mensajes = []
        self.comparaciones = []
        self.id_chat = None
        self._sesiones = {}
        self._limpiar()
        self._agregar_texto(SALUDO)
        self.campo.setFocus()

    # ------------------------------------------------------------ historial de chats
    def _guardar_chat(self, modo):
        """Al terminar cada pedido. Si el disco falla lo dice en el chat; el chat sigue andando."""
        if not self.mensajes:
            return
        cfg = config_de(self.ventana.prefs)
        modelo = config.modelo_de(cfg) if cfg["proveedor"] in config.PROVEEDORES else ""
        try:
            self.id_chat = historial.guardar(self.mensajes, modo, cfg["proveedor"], modelo, self.id_chat,
                                             self._sesiones, self.comparaciones)
        except OSError as e:
            self._agregar_texto(f"⚠ No se pudo guardar el chat en el historial: {e}", "aviso")

    def abrir_historial(self):
        dialogo = DialogoHistorial(self)
        dialogo.open()
        return dialogo

    def cargar_chat(self, id_chat):
        """Carga un chat guardado: lo muestra y la conversación sigue desde ahí. False si no se pudo."""
        if self.trabajando:
            self._agregar_texto("Esperá a que termine el pedido en curso para abrir otro chat.", "tenue")
            return False
        try:
            chat = historial.cargar(id_chat)
        except historial.ErrorHistorial as e:
            self._agregar_texto(f"⚠ {e}", "error")
            return False
        self.mensajes, self.id_chat, self._sesiones = chat["mensajes"], id_chat, chat["sesiones_cli"]
        self.comparaciones = chat["comparaciones"]
        self._limpiar()
        indice = self.modo.findData(chat.get("modo"))
        if indice >= 0:
            self.modo.setCurrentIndex(indice)
        pedidos = {}
        for i, m in enumerate(self.mensajes, 1):
            for b in m["contenido"]:
                if b["tipo"] == "texto":
                    self._agregar_texto(b["texto"], usuario=m["rol"] == "usuario")
                elif b["tipo"] == "imagen":
                    self._agregar_imagen(api.Imagen(b["png"], b.get("ancho", 0), b.get("alto", 0)))
                elif b["tipo"] == "pedido_herramienta":
                    pedidos[b.get("id")] = b
                elif b["tipo"] == "resultado_herramienta":
                    self._mostrar_resultado(pedidos.get(b.get("id"), {}), b)
            for c in self.comparaciones:
                if c["pos"] == i:
                    self._mostrar_comparacion(c["antes"], c["despues"])
        fecha = str(chat.get("fecha", "")).replace("T", " ")[:16]
        self._agregar_texto(f"Chat del {fecha}: escribí para seguirlo.", "tenue")
        self.campo.setFocus()
        return True

    def _mostrar_resultado(self, pedido, bloque):
        """La línea plegada de una herramienta de un chat guardado (la respuesta va como texto JSON) y sus imágenes."""
        respuesta = None
        for b in bloque["contenido"]:
            if b["tipo"] == "texto" and respuesta is None:
                try:
                    respuesta = json.loads(b["texto"])
                except ValueError:
                    pass
        if not isinstance(respuesta, dict):
            respuesta = {"ok": not bloque.get("error")}
        self._agregar_herramienta(pedido.get("nombre", "herramienta"), pedido.get("args", {}), respuesta)
        for b in bloque["contenido"]:
            if b["tipo"] == "imagen":
                self._agregar_imagen(api.Imagen(b["png"], b.get("ancho", 0), b.get("alto", 0)))

    def closeEvent(self, e):
        super().closeEvent(e)
        self.cerrado.emit()

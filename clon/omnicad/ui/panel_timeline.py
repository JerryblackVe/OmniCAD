# -*- coding: utf-8 -*-
"""
Barra de timeline inferior (como la línea de tiempo de Fusion 360): botones de reproducción
(inicio, anterior, siguiente, fin), un ícono chico por paso y el marcador negro que separa lo
activo de lo retrocedido. El estado de cada paso (FeatureHealthStates de Fusion) se ve en el
fondo: amarillo = aviso, rojo = error; suprimido o retrocedido = ícono gris.
Se arrastra el marcador o un paso para moverlos; doble clic edita; menú contextual completo.
"""
from PySide6.QtCore import QSize, Qt, QTimer, Signal
from PySide6.QtGui import QBrush, QColor, QIcon
from PySide6.QtWidgets import (QAbstractItemView, QHBoxLayout, QLabel, QListView, QListWidget, QListWidgetItem, QMenu,
                               QToolButton, QWidget)

from .iconos import icono

COLORES = {"aviso": QColor(255, 214, 102), "error": QColor(255, 140, 140)}
MARCADOR = "__marcador__"
ICONO_TIPO = {"boceto": "boceto", "extrusion": "extruir", "revolucion": "revolucion", "combinar": "combinar",
              "importar_step": "importar", "plano": "plano_desfase"}


def icono_operacion(op):
    return op.p["forma"] if op.TIPO == "primitiva" else ICONO_TIPO.get(op.TIPO, "caja")


def destino_arrastre(claves, origen, fila_destino):
    """
    Dónde queda lo arrastrado. `claves`: filas actuales (ids de pasos y MARCADOR); `origen`: la
    clave arrastrada; `fila_destino`: fila ANTES de la cual se soltó (len(claves) = al final).
    Devuelve el índice nuevo entre los pasos (sin contar el marcador ni lo arrastrado), que es
    lo que esperan Documento.mover y Documento.mover_marcador.
    """
    return sum(1 for c in claves[:fila_destino] if c not in (MARCADOR, origen))


class _Lista(QListWidget):
    soltado = Signal(str, int)          # clave arrastrada, fila antes de la que se soltó

    def dropEvent(self, e):
        item = self.currentItem()
        pos = e.position().toPoint()
        destino = self.indexAt(pos)
        if destino.isValid():
            fila = destino.row() + (1 if pos.x() > self.visualRect(destino).center().x() else 0)
        else:
            fila = self.count()
        e.setDropAction(Qt.IgnoreAction)
        e.accept()
        if item is not None:
            self.soltado.emit(item.data(Qt.UserRole), fila)


class PanelTimeline(QWidget):
    editar = Signal(str)
    renombrar = Signal(str)
    suprimir = Signal(str, bool)
    eliminar = Signal(str)
    mover = Signal(str, int)
    marcador = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("barra_timeline")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.doc = None
        self.lista = _Lista()
        self.lista.setFlow(QListView.LeftToRight)
        self.lista.setWrapping(False)
        self.lista.setFixedHeight(38)
        self.lista.setIconSize(QSize(24, 24))
        self.lista.setSpacing(1)
        self.lista.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.lista.setDragDropMode(QAbstractItemView.InternalMove)
        self.lista.setDefaultDropAction(Qt.MoveAction)
        self.lista.setContextMenuPolicy(Qt.CustomContextMenu)
        self.lista.customContextMenuRequested.connect(self._menu)
        self.lista.itemDoubleClicked.connect(self._doble_clic)
        self.lista.soltado.connect(self._soltado)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 0, 4, 0)
        lay.setSpacing(0)
        for ico, ayuda, funcion in (("tl_inicio", "Ir al inicio", lambda: self.marcador.emit(0)),
                                    ("tl_anterior", "Paso anterior", lambda: self._paso(-1)),
                                    ("tl_reproducir", "Reproducir (avanza el marcador paso a paso hasta el final)",
                                     self._reproducir),
                                    ("tl_siguiente", "Paso siguiente", lambda: self._paso(1)),
                                    ("tl_fin", "Ir al final", lambda: self.marcador.emit(len(self.doc.operaciones)))):
            b = QToolButton()
            b.setIcon(icono(ico))
            b.setIconSize(QSize(18, 18))
            b.setToolTip(ayuda)
            b.setAutoRaise(True)
            b.clicked.connect(funcion)
            lay.addWidget(b)
        lay.addSpacing(8)
        lay.addWidget(self.lista, 1)
        # «Unidades: mm, g ▾» (docs/diseno/): el menú lo arma la ventana, que tiene las preferencias.
        self.unidades = QToolButton(objectName="selector_unidades", text="Unidades: mm, g  ▾")
        self.unidades.setIcon(icono("unidades"))
        self.unidades.setIconSize(QSize(16, 16))
        self.unidades.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.unidades.setPopupMode(QToolButton.InstantPopup)
        self.unidades.setToolTip("<b>Unidades del documento</b><br>Unidades y precisión con que se muestran los valores.")
        lay.addWidget(self.unidades)
        lay.addSpacing(12)
        self.estado = QLabel(objectName="estado_timeline")
        lay.addWidget(self.estado)

    # ------------------------------------------------------------ navegación
    def _paso(self, delta):
        if self.doc:
            self.marcador.emit(max(0, min(len(self.doc.operaciones), self.doc.marcador + delta)))

    def _reproducir(self):
        """Como el ▶ de Fusion: recorre el historial desde el principio, un paso por vez."""
        if not self.doc:
            return
        total = len(self.doc.operaciones)
        self.marcador.emit(0)
        for i in range(1, total + 1):
            QTimer.singleShot(350 * i, lambda i=i: self.marcador.emit(i))

    # ------------------------------------------------------------ contenido
    def actualizar(self, doc):
        self.doc = doc
        self.lista.clear()
        for i, (op, res) in enumerate(zip(doc.operaciones, doc.resultados, strict=True)):
            if i == doc.marcador:
                self._agregar_marcador()
            ico = icono(icono_operacion(op))
            apagado = res.estado in ("suprimida", "retrocedida")
            it = QListWidgetItem(QIcon(ico.pixmap(48, 48, QIcon.Disabled)) if apagado else ico, "")
            it.setSizeHint(QSize(32, 34))
            it.setData(Qt.UserRole, op.id)
            if res.estado in COLORES:
                it.setBackground(QBrush(COLORES[res.estado]))
            estado = {"ok": "OK", "aviso": "Aviso", "error": "Error", "suprimida": "Suprimida",
                      "retrocedida": "Retrocedida (después del marcador)"}[res.estado]
            it.setToolTip(f"<b>{op.nombre}</b><br>{op.ETIQUETA} · {op.id}<br>Estado: {estado}"
                          + (f"<br>{res.mensaje}" if res.mensaje else "")
                          + "<br><i>Doble clic: editar · clic derecho: más opciones</i>")
            self.lista.addItem(it)
        if doc.marcador == len(doc.operaciones):
            self._agregar_marcador()

    def _agregar_marcador(self):
        it = QListWidgetItem(icono("marcador"), "")
        it.setSizeHint(QSize(18, 34))
        it.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsDragEnabled)
        it.setData(Qt.UserRole, MARCADOR)
        it.setToolTip("Marcador del timeline: arrastralo. Lo que queda a la derecha no se calcula.")
        self.lista.addItem(it)

    def resaltar(self, op_id):
        """"Buscar en el timeline": elige el ícono del paso y lo trae a la vista."""
        for i in range(self.lista.count()):
            it = self.lista.item(i)
            if it.data(Qt.UserRole) == op_id:
                self.lista.setCurrentItem(it)
                self.lista.scrollToItem(it)
                return True
        return False

    def claves(self):
        return [self.lista.item(i).data(Qt.UserRole) for i in range(self.lista.count())]

    def _soltado(self, clave, fila):
        if self.doc is None:
            return
        nuevo = destino_arrastre(self.claves(), clave, fila)
        if clave == MARCADOR:
            if nuevo != self.doc.marcador:
                self.marcador.emit(nuevo)
        elif nuevo != self.doc.indice(clave):
            self.mover.emit(clave, nuevo)

    def _doble_clic(self, item):
        op_id = item.data(Qt.UserRole)
        if op_id and op_id != MARCADOR:
            self.editar.emit(op_id)

    def _menu(self, pos):
        item = self.lista.itemAt(pos)
        if item is None or item.data(Qt.UserRole) in (None, MARCADOR) or self.doc is None:
            return
        op_id = item.data(Qt.UserRole)
        i = self.doc.indice(op_id)
        op = self.doc.operaciones[i]
        m = QMenu(self)
        m.addAction("Editar operación…", lambda: self.editar.emit(op_id))
        m.addAction("Renombrar…", lambda: self.renombrar.emit(op_id))
        m.addAction("Desuprimir operación" if op.suprimida else "Suprimir operación",
                    lambda: self.suprimir.emit(op_id, not op.suprimida))
        m.addSeparator()
        m.addAction("Mover a la izquierda", lambda: self.mover.emit(op_id, i - 1)).setEnabled(i > 0)
        m.addAction("Mover a la derecha", lambda: self.mover.emit(op_id, i + 1)).setEnabled(i < len(self.doc.operaciones) - 1)
        m.addAction("Retroceder hasta aquí", lambda: self.marcador.emit(i + 1))
        m.addAction("Retroceder antes de este paso", lambda: self.marcador.emit(i))
        m.addSeparator()
        m.addAction("Eliminar", lambda: self.eliminar.emit(op_id))
        m.exec(self.lista.mapToGlobal(pos))

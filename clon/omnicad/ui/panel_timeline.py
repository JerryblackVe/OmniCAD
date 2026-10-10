# -*- coding: utf-8 -*-
"""
Barra de timeline inferior (como la línea de tiempo de Fusion 360): botones de reproducción
(inicio, anterior, siguiente, fin), un ícono chico por paso y el marcador negro que separa lo
activo de lo retrocedido. El estado de cada paso (FeatureHealthStates de Fusion) se ve en el
fondo: amarillo = aviso, rojo = error; suprimido o retrocedido = ícono gris.
Se arrastra el marcador o un paso para moverlos; doble clic edita. El clic derecho abre un menú distinto
según el tipo de paso, como Fusion: boceto (Editar boceto), operación (Editar operación y «Editar boceto de
perfil»), unión (Editar unión, Animar unión); todos con Renombrar, Suprimir, Mover, «Rodar marcador aquí»,
«Retroceder antes de este paso», «Buscar en navegador» y Eliminar.
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
    buscar_navegador = Signal(str)      # «Buscar en navegador»: elige el elemento del paso en el navegador
    animar_union = Signal(str)          # «Animar unión» (menú de un paso de unión)

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

    def entradas_menu(self, op_id):
        """Menú contextual del paso, distinto según su tipo como en Fusion (boceto, operación, unión):
        [Entrada | None (separador)]. Una Entrada con `hijos` es un submenú."""
        doc = self.doc
        i = doc.indice(op_id)
        op = doc.operaciones[i]
        tipo = tipo_menu(op)
        E = Entrada
        emitir = lambda senal, *args: (lambda: senal.emit(*args))  # noqa: E731
        if tipo == "boceto":
            arriba = [E("Editar boceto", emitir(self.editar, op_id))]
        elif tipo == "union":
            arriba = [E("Editar unión…", emitir(self.editar, op_id))]
            if op.TIPO == "union":
                arriba.append(E("Animar unión", emitir(self.animar_union, op_id)))
        else:
            arriba = [E("Editar operación…", emitir(self.editar, op_id))]
            bocetos = bocetos_de_perfil(doc, op)
            if len(bocetos) == 1:
                arriba.append(E("Editar boceto de perfil", emitir(self.editar, bocetos[0].id)))
            elif bocetos:
                arriba.append(E("Editar boceto de perfil", None, hijos=[
                    E(b.nombre, emitir(self.editar, b.id)) for b in bocetos]))
        sufijo = "boceto" if tipo == "boceto" else ("unión" if tipo == "union" else "operación")
        return arriba + [
            E("Renombrar…", emitir(self.renombrar, op_id)),
            E(f"Desuprimir {sufijo}" if op.suprimida else f"Suprimir {sufijo}",
              emitir(self.suprimir, op_id, not op.suprimida)),
            None,
            E("Mover a la izquierda", emitir(self.mover, op_id, i - 1), i > 0),
            E("Mover a la derecha", emitir(self.mover, op_id, i + 1), i < len(doc.operaciones) - 1),
            # «Rodar marcador aquí» de Fusion (antes «Retroceder hasta aquí»): el paso queda calculado
            E("Rodar marcador aquí", emitir(self.marcador, i + 1), doc.marcador != i + 1,
              "El marcador queda justo después de este paso: lo que sigue no se calcula."),
            E("Retroceder antes de este paso", emitir(self.marcador, i), doc.marcador != i,
              "El marcador queda justo antes: este paso y lo que sigue no se calculan."),
            None,
            E("Buscar en navegador", emitir(self.buscar_navegador, op_id),
              ayuda="Elige en el navegador el elemento que crea o modifica este paso."),
            None,
            E("Eliminar", emitir(self.eliminar, op_id)),
        ]

    def _menu(self, pos):
        item = self.lista.itemAt(pos)
        if item is None or item.data(Qt.UserRole) in (None, MARCADOR) or self.doc is None:
            return
        m = QMenu(self)
        _llenar_menu(m, self.entradas_menu(item.data(Qt.UserRole)))
        m.exec(self.lista.mapToGlobal(pos))


class Entrada:
    """Opción del menú contextual del timeline (`hijos`: submenú)."""

    def __init__(self, texto, funcion, habilitada=True, ayuda="", hijos=None):
        self.texto, self.funcion, self.habilitada, self.ayuda, self.hijos = texto, funcion, habilitada, ayuda, hijos

    def __repr__(self):
        return f"Entrada({self.texto!r})"


def _llenar_menu(menu, entradas):
    for e in entradas:
        if e is None:
            menu.addSeparator()
        elif e.hijos:
            _llenar_menu(menu.addMenu(e.texto), e.hijos)
        else:
            a = menu.addAction(e.texto, e.funcion)
            a.setEnabled(bool(e.habilitada))
            if e.ayuda:
                a.setToolTip(e.ayuda)
    menu.setToolTipsVisible(True)


TIPOS_UNION = ("union", "grupo_rigido", "vinculo_movimiento")


def tipo_menu(op):
    """Qué menú lleva el paso: "boceto", "union" (uniones de ENSAMBLAR) u "operacion" (el resto)."""
    if op.TIPO == "boceto":
        return "boceto"
    return "union" if op.TIPO in TIPOS_UNION else "operacion"


def bocetos_de_perfil(doc, op):
    """Bocetos que usa el paso: lo que abre «Editar boceto de perfil» sin pasar por el navegador (misma regla que
    la herramienta `get_profile_sketches` de la API)."""
    from ..api.herramientas_timeline import bocetos_de_perfil as bocetos
    return bocetos(doc, op)

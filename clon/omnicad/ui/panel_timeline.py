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
El engranaje de la derecha («Opciones» de Fusion) tiene «Muestra de color por componente»: pinta el fondo de cada
paso con el color de su componente. «Ocultar pasos inactivos» y «Cambiar a modelado directo» no están: OmniCAD no
tiene componente activo ni modo sin historial.
"""
from PySide6.QtCore import QSize, Qt, QTimer, Signal
from PySide6.QtGui import QBrush, QColor, QIcon
from PySide6.QtWidgets import (QAbstractItemView, QHBoxLayout, QLabel, QListView, QListWidget, QListWidgetItem, QMenu,
                               QToolButton, QWidget)

from ..timeline.operaciones import OPERACIONES_CUERPO
from .iconos import icono
from .insignias import icono_con_insignia, insignia_de

COLORES = {"aviso": QColor(255, 214, 102), "error": QColor(255, 140, 140)}
MARCADOR = "__marcador__"
# Colores de la muestra por componente (suaves, para que el ícono se siga viendo); se repiten si hay más componentes.
PALETA_COMPONENTES = [QColor(*c) for c in ((141, 196, 255), (255, 183, 120), (168, 225, 148), (214, 170, 240),
                                           (255, 165, 175), (130, 220, 215), (240, 220, 120), (190, 190, 200))]
# Pasos que ningún comando de la cinta crea: su ícono. Todos los demás usan el del comando que los crea (`comando_para`).
ICONO_TIPO = {"boceto": "boceto", "importar_step": "importar", "importar_iges": "importar_iges",
              "operacion_base": "operacion_base", "insertar_malla": "insertar_malla",
              "insertar_diseno": "insertar_diseno", "grafo": "grafo", "borrar_caras": "borrar_caras",
              "calibracion_holguras": "calibracion_holguras"}


def icono_operacion(op):
    """Nombre del dibujo del paso: el del comando que lo crea (una sola fuente de verdad)."""
    if op.TIPO == "primitiva":
        return op.p["forma"]
    if op.TIPO in ICONO_TIPO:
        return ICONO_TIPO[op.TIPO]
    from .comandos import comando_para      # acá y no arriba: los comandos importan media interfaz
    comando = comando_para(op)
    return comando.ICONO if comando else "caja"


def colores_por_componente(doc):
    """{id de paso: color} de los pasos que pertenecen a un componente: el propio paso Componente y los que crearon
    cuerpos que hoy están dentro de uno (el color sigue el orden en que se crearon los componentes). Los demás no
    figuran."""
    ids = [op.id for op in doc.operaciones if op.TIPO == "componente"]
    de_cuerpo = {}
    for c in doc.estado_final.cuerpos.values():
        if c.componente:
            de_cuerpo.setdefault(c.op_id, c.componente)
    colores = {}
    for op in doc.operaciones:
        comp = op.id if op.TIPO == "componente" else de_cuerpo.get(op.id)
        if comp in ids:
            colores[op.id] = PALETA_COMPONENTES[ids.index(comp) % len(PALETA_COMPONENTES)]
    return colores


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
    color_componente_cambiado = Signal(bool)    # casilla «Muestra de color por componente» del engranaje

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("barra_timeline")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.doc = None
        self.color_componente = False
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
        # Engranaje de la derecha (Opciones del timeline de Fusion).
        self.engranaje = QToolButton(objectName="opciones_timeline")
        self.engranaje.setIcon(icono("engranaje"))
        self.engranaje.setIconSize(QSize(16, 16))
        self.engranaje.setAutoRaise(True)
        self.engranaje.setPopupMode(QToolButton.InstantPopup)
        self.engranaje.setToolTip("<b>Opciones del timeline</b>")
        menu = QMenu(self.engranaje)
        self.accion_color = menu.addAction("Muestra de color por componente")
        self.accion_color.setCheckable(True)
        self.accion_color.setToolTip("Pinta cada paso con el color del componente al que pertenece.")
        self.accion_color.triggered.connect(self.poner_color_componente)
        menu.setToolTipsVisible(True)
        self.engranaje.setMenu(menu)
        lay.addWidget(self.engranaje)

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

    def poner_color_componente(self, activo):
        """Enciende o apaga la muestra de color por componente (la ventana lo guarda en las preferencias)."""
        activo = bool(activo)
        self.accion_color.setChecked(activo)
        if activo != self.color_componente:
            self.color_componente = activo
            self.color_componente_cambiado.emit(activo)
            if self.doc is not None:
                self.actualizar(self.doc)

    # ------------------------------------------------------------ contenido
    def repintar_iconos(self):
        """Cambió el tema: los pasos apagados llevan un ícono gris ya dibujado, así que se rearma la lista."""
        self._firma = None
        if self.doc is not None:
            barra, actual = self.lista.horizontalScrollBar(), self.lista.currentItem()
            posicion, clave = barra.value(), actual.data(Qt.UserRole) if actual else None
            self.actualizar(self.doc)
            if clave is not None:
                self.resaltar(clave)
            barra.setValue(posicion)

    def actualizar(self, doc):
        # Sin cambios en lo que se muestra no se reconstruye (llega en cada aviso del documento).
        colores = colores_por_componente(doc) if self.color_componente else {}
        nombres = [icono_operacion(op) for op in doc.operaciones]       # una vez por paso: resolver el comando recorre el catálogo
        firma = (id(doc), doc.marcador, [(op.id, op.nombre, op.ETIQUETA, nombre, insignia_de(op, res.estado),
                                          res.estado, res.mensaje, colores.get(op.id))
                                         for op, res, nombre in zip(doc.operaciones, doc.resultados, nombres, strict=True)])
        if doc is self.doc and firma == getattr(self, "_firma", None):
            return
        self._firma = firma
        self.doc = doc
        self.lista.clear()
        for i, (op, res) in enumerate(zip(doc.operaciones, doc.resultados, strict=True)):
            if i == doc.marcador:
                self._agregar_marcador()
            insignia = insignia_de(op, res.estado)
            ico = icono_con_insignia(nombres[i], insignia) if insignia else icono(nombres[i])
            apagado = res.estado in ("suprimida", "retrocedida")
            it = QListWidgetItem(QIcon(ico.pixmap(48, 48, QIcon.Disabled)) if apagado else ico, "")
            it.setSizeHint(QSize(32, 34))
            it.setData(Qt.UserRole, op.id)
            fondo = COLORES.get(res.estado) or colores.get(op.id)       # aviso o error mandan sobre el componente
            if fondo is not None:
                it.setBackground(QBrush(fondo))
            estado = {"ok": "OK", "aviso": "Aviso", "error": "Error", "suprimida": "Suprimida",
                      "retrocedida": "Retrocedida (después del marcador)"}[res.estado]
            it.setToolTip(f"<b>{op.nombre}</b><br>{op.ETIQUETA} · {op.id}<br>Estado: {estado}"
                          + (f"<br>Operación: {OPERACIONES_CUERPO[op.p['operacion']]}" if op.p.get("operacion") in OPERACIONES_CUERPO else "")
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

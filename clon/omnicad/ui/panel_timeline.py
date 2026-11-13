# -*- coding: utf-8 -*-
"""
Barra de timeline inferior (como la línea de tiempo de Fusion 360): botones de reproducción
(inicio, anterior, siguiente, fin), un ícono chico por paso y el marcador negro que separa lo
activo de lo retrocedido. El estado de cada paso (FeatureHealthStates de Fusion) se ve en el
fondo: amarillo = aviso, rojo = error; suprimido o retrocedido = ícono gris.
Se arrastra el marcador o un paso para moverlos; doble clic edita. El clic derecho abre un menú distinto
según el tipo de paso, como Fusion: boceto (Editar boceto), operación (Editar operación y «Editar boceto de
perfil»), unión (Editar unión, Animar unión); todos con Renombrar, Suprimir, Configurar, Mover, «Rodar marcador aquí»,
«Retroceder antes de este paso», «Buscar en navegador», «Buscar en la ventana», «Crear conjunto de selección» y Eliminar.
Con Ctrl se eligen varios pasos: Suprimir (Fusion: «Suprimir operaciones»), Buscar en la ventana y Crear conjunto actúan sobre todos.
Varios elegidos + clic derecho → «Agrupar N pasos» (Fusion: Create Group): forman una carpeta que va delante de sus pasos; su menú
la contrae o la expande (+/− de Fusion), la suprime entera y la desagrupa (Edit Group › Expand), y doble clic la renombra. La
carpeta no es un paso: sólo ordena la vista. Ctrl+C y Ctrl+V copian y pegan el paso elegido (SC9).
El engranaje de la derecha («Opciones» de Fusion) tiene «Muestra de color por componente»: pinta el fondo de cada
paso con el color de su componente. «Ocultar pasos inactivos» y «Cambiar a modelado directo» no están: OmniCAD no
tiene componente activo ni modo sin historial.
"""
from PySide6.QtCore import QSize, Qt, QTimer, Signal
from PySide6.QtGui import QBrush, QColor, QIcon, QPen
from PySide6.QtWidgets import (QAbstractItemView, QHBoxLayout, QInputDialog, QLabel, QListView, QListWidget,
                               QListWidgetItem, QMenu, QStyle, QStyledItemDelegate, QStyleOptionViewItem, QToolButton,
                               QWidget)

from ..timeline import aspectos_doc
from ..timeline.operaciones import OPERACIONES_CUERPO
from . import temas
from .iconos import icono
from .insignias import icono_con_insignia, insignia_de

COLORES = {"aviso": QColor(255, 214, 102), "error": QColor(255, 140, 140)}
MARCADOR = "__marcador__"
GRUPO = "grupo:"              # prefijo de la fila de una carpeta del timeline (Fusion: Timeline Group)
ROL_ORIGEN = Qt.UserRole + 1     # «creo» | «modifico»: el paso es de donde viene lo elegido en la vista (amarillo)
PALETA_COMPONENTES = [QColor(*c) for c in aspectos_doc.PALETA_COMPONENTES]
# Pasos que ningún comando de la cinta crea: su ícono. Todos los demás usan el del comando que los crea (`comando_para`).
ICONO_TIPO = {"boceto": "boceto", "importar_step": "importar", "importar_iges": "importar_iges",
              "operacion_base": "operacion_base", "insertar_malla": "insertar_malla",
              "insertar_diseno": "insertar_diseno", "grafo": "grafo",
              "calibracion_holguras": "calibracion_holguras", "copiar_componente": "duplicar_con_uniones"}


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
    ids = aspectos_doc.colores_componentes(doc)
    de_cuerpo = {}
    for c in doc.estado_final.cuerpos.values():
        if c.componente:
            de_cuerpo.setdefault(c.op_id, c.componente)
    colores = {}
    for op in doc.operaciones:
        comp = op.id if op.TIPO == "componente" else de_cuerpo.get(op.id)
        if comp in ids:
            colores[op.id] = QColor(*ids[comp])
    return colores


def destino_arrastre(claves, origen, fila_destino):
    """
    Dónde queda lo arrastrado. `claves`: filas actuales (ids de pasos y MARCADOR); `origen`: la
    clave arrastrada; `fila_destino`: fila ANTES de la cual se soltó (len(claves) = al final).
    Devuelve el índice nuevo entre los pasos (sin contar el marcador, las carpetas ni lo arrastrado), que es
    lo que esperan Documento.mover y Documento.mover_marcador.
    """
    return sum(1 for c in claves[:fila_destino] if c not in (MARCADOR, origen) and not str(c).startswith(GRUPO))


class _Delegado(QStyledItemDelegate):
    """Pinta los pasos de «De dónde viene esta cara»: fondo amarillo y marco ámbar (el fondo solo se confundiría con el
    aviso). Lo dibuja acá porque la hoja de estilos de la app pisa el `setBackground` de los ítems."""

    def paint(self, p, option, index):
        origen = index.data(ROL_ORIGEN)
        caja = option.rect.adjusted(1, 1, -2, -2)
        if origen:
            p.fillRect(caja, QColor(temas.ORIGEN[origen]))
            option = QStyleOptionViewItem(option)
            option.state &= ~QStyle.State_Selected      # elegido en el timeline, el amarillo sigue a la vista
        super().paint(p, option, index)
        if origen:
            p.save()
            p.setPen(QPen(QColor(temas.ORIGEN["borde"]), 2 if origen == "creo" else 1))
            p.setBrush(Qt.NoBrush)
            p.drawRect(caja)
            p.restore()


class _Lista(QListWidget):
    soltado = Signal(str, int)          # clave arrastrada, fila antes de la que se soltó
    copiar = Signal()                   # Ctrl+C: copiar el paso elegido (SC9)
    pegar = Signal()                    # Ctrl+V: pegar la copia

    def keyPressEvent(self, e):
        if e.modifiers() == Qt.ControlModifier and e.key() in (Qt.Key_C, Qt.Key_V):
            (self.copiar if e.key() == Qt.Key_C else self.pegar).emit()
            return                      # en el timeline Ctrl+C copia el paso, no lo elegido de la lista
        super().keyPressEvent(e)

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
    eliminar_varios = Signal(list)         # «Eliminar N pasos» con varios elegidos (y Supr): ids, en UN paso de deshacer
    mover = Signal(str, int)
    marcador = Signal(int)
    buscar_navegador = Signal(str)      # «Buscar en navegador»: elige el elemento del paso en el navegador
    animar_union = Signal(str)          # «Animar unión» (menú de un paso de unión)
    suprimir_varios = Signal(list, bool)   # «Suprimir N pasos» con varios elegidos: ids, suprimir (True) o reactivar
    configurar = Signal(str)            # «Configurar»: suma la supresión del paso a la tabla de configuraciones
    buscar_ventana = Signal(list)       # «Buscar en la ventana»: ids de los pasos cuyos cuerpos se encuadran
    crear_conjunto = Signal(list)       # «Crear conjunto de selección»: ids de los pasos cuyos cuerpos se guardan
    tocado = Signal(str)                # clic en un paso: un comando abierto lo puede tomar (Simetría › Operaciones)
    color_componente_cambiado = Signal(bool)    # casilla «Muestra de color por componente» del engranaje
    agrupar = Signal(list)              # «Agrupar N pasos» (Fusion: Create Group): los ids elegidos
    desagrupar = Signal(str)            # «Desagrupar» (Fusion: Edit Group › Expand): id de la carpeta
    plegar = Signal(str, bool)          # clic en la carpeta: su id y si queda contraída
    renombrar_grupo = Signal(str, str)  # doble clic en la carpeta: id y nombre nuevo
    pegar = Signal(dict, list)          # Ctrl+V: la receta copiada y los pasos que usaba el original

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("barra_timeline")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.doc = None
        self.color_componente = False
        self.colores_en_lienzo = False      # Mostrar colores de componente también pinta las muestras
        self.muestras = {}                  # id de paso → color de lo último que se dibujó
        self._copiado = None                # Ctrl+C del timeline: (receta del paso, los pasos que usa)
        self._origen = ((), ())            # (pasos que crearon lo elegido, pasos que lo modificaron): `resaltar_origen`
        self.lista = _Lista()
        self.lista.setItemDelegate(_Delegado(self.lista))
        self.lista.setFlow(QListView.LeftToRight)
        self.lista.setWrapping(False)
        self.lista.setFixedHeight(38)
        self.lista.setIconSize(QSize(24, 24))
        self.lista.setSpacing(1)
        self.lista.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.lista.setSelectionMode(QAbstractItemView.ExtendedSelection)      # Ctrl: varios pasos, como en Fusion
        self.lista.setDragDropMode(QAbstractItemView.InternalMove)
        self.lista.setDefaultDropAction(Qt.MoveAction)
        self.lista.setContextMenuPolicy(Qt.CustomContextMenu)
        self.lista.customContextMenuRequested.connect(self._menu)
        self.lista.itemDoubleClicked.connect(self._doble_clic)
        self.lista.itemClicked.connect(self._clic)
        self.lista.soltado.connect(self._soltado)
        self.lista.copiar.connect(self._copiar_paso)
        self.lista.pegar.connect(self._pegar_paso)
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
        colores = self.muestras = colores_por_componente(doc) if self.color_componente or self.colores_en_lienzo else {}
        nombres = [icono_operacion(op) for op in doc.operaciones]       # una vez por paso: resolver el comando recorre el catálogo
        existentes = {op.id for op in doc.operaciones}
        plegados = {i for g in doc.grupos if g["plegado"] for i in g["pasos"]}
        chips = {}                        # carpeta que va delante de este paso (la de su paso más antiguo)
        for g in doc.grupos:
            reales = [i for i in g["pasos"] if i in existentes]
            if reales:
                chips[min(reales, key=doc.indice)] = g
        firma = (id(doc), doc.marcador, [(op.id, op.nombre, op.ETIQUETA, nombre, insignia_de(op, res.estado),
                                          res.estado, res.mensaje, colores.get(op.id))
                                         for op, res, nombre in zip(doc.operaciones, doc.resultados, nombres, strict=True)],
                 self._origen, [(g["id"], g["nombre"], g["plegado"], tuple(g["pasos"])) for g in doc.grupos])
        if doc is self.doc and firma == getattr(self, "_firma", None):
            return
        self._firma = firma
        if doc is not self.doc:
            self._copiado = None              # lo copiado en OTRO documento no se pega acá: los ids significan otra cosa
        self.doc = doc
        self.lista.clear()
        for i, (op, res) in enumerate(zip(doc.operaciones, doc.resultados, strict=True)):
            if op.id in chips:
                self._agregar_grupo(chips[op.id])
            if i == doc.marcador:
                self._agregar_marcador()                  # dentro de una carpeta contraída asoma detrás de su fila
            if op.id in plegados:
                continue                                  # contraída: sus pasos no se dibujan
            insignia = insignia_de(op, res.estado)
            ico = icono_con_insignia(nombres[i], insignia) if insignia else icono(nombres[i])
            apagado = res.estado in ("suprimida", "retrocedida")
            it = QListWidgetItem(QIcon(ico.pixmap(48, 48, QIcon.Disabled)) if apagado else ico, "")
            it.setSizeHint(QSize(32, 34))
            it.setData(Qt.UserRole, op.id)
            fondo = COLORES.get(res.estado) or colores.get(op.id)       # aviso o error mandan sobre el componente
            marca = self._marca_origen(op.id)
            if marca:                                                   # el amarillo de «de dónde viene» manda sobre todo
                fondo = QColor(temas.ORIGEN[marca])
                it.setData(ROL_ORIGEN, marca)
            if fondo is not None:
                it.setBackground(QBrush(fondo))
            estado = {"ok": "OK", "aviso": "Aviso", "error": "Error", "suprimida": "Suprimida",
                      "retrocedida": "Retrocedida (después del marcador)"}[res.estado]
            it.setToolTip(f"<b>{op.nombre}</b><br>{op.ETIQUETA} · {op.id}<br>Estado: {estado}"
                          + (f"<br>Operación: {OPERACIONES_CUERPO[op.p['operacion']]}" if op.p.get("operacion") in OPERACIONES_CUERPO else "")
                          + (f"<br>{res.mensaje}" if res.mensaje else "")
                          + {"creo": "<br><b>Creó lo que está elegido en la vista</b>",
                             "modifico": "<br><b>Modificó lo que está elegido en la vista</b>"}.get(marca, "")
                          + "<br><i>Doble clic: editar · clic derecho: más opciones</i>")
            self.lista.addItem(it)
        if doc.marcador == len(doc.operaciones):
            self._agregar_marcador()

    def _marca_origen(self, op_id):
        creo, modificaron = self._origen
        return "creo" if op_id in creo else "modifico" if op_id in modificaron else None

    def resaltar_origen(self, creo=(), modificaron=()):
        """«De dónde viene esta cara»: pinta de amarillo fuerte los pasos `creo` (ids; uno solo puede ir como texto) y de
        suave los `modificaron`, y trae el primero que creó a la vista (sin elegirlo). Sin argumentos saca el resaltado."""
        nuevo = ((creo,) if isinstance(creo, str) else tuple(creo), tuple(modificaron))
        if nuevo == self._origen:
            return
        self._origen = nuevo
        if self.doc is not None:
            self.repintar_iconos()          # arma de nuevo la lista (guarda la posición y el paso elegido)
            primero = next((it for i in range(self.lista.count()) if (it := self.lista.item(i)).data(ROL_ORIGEN) == "creo"),
                           None)
            if primero is not None:
                self.lista.scrollToItem(primero)

    def _agregar_marcador(self):
        it = QListWidgetItem(icono("marcador"), "")
        it.setSizeHint(QSize(18, 34))
        it.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsDragEnabled)
        it.setData(Qt.UserRole, MARCADOR)
        it.setToolTip("Marcador del timeline: arrastralo. Lo que queda a la derecha no se calcula.")
        self.lista.addItem(it)

    def _grupo(self, clave):
        """La carpeta de una fila «grupo:id»; None si la fila no es una carpeta o la carpeta ya no está."""
        if not isinstance(clave, str) or not clave.startswith(GRUPO):
            return None
        return next((g for g in (self.doc.grupos if self.doc else []) if g["id"] == clave[len(GRUPO):]), None)

    def _agregar_grupo(self, g):
        """La fila de una carpeta (Fusion: el bloque del grupo con su botón +/−): contraída se ve con ▸ y esconde sus
        pasos; la carpeta no es un paso, así que no tiene estado ni insignia propia."""
        n = len(g["pasos"])
        suprimidos = sum(1 for o in self.doc.operaciones if o.id in g["pasos"] and o.suprimida)
        texto = ("▸ " if g["plegado"] else "▾ ") + g["nombre"]
        it = QListWidgetItem(icono("carpeta"), texto)
        it.setSizeHint(QSize(24 + self.lista.fontMetrics().horizontalAdvance(texto), 34))
        it.setData(Qt.UserRole, GRUPO + g["id"])
        it.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)     # la carpeta no se arrastra: se arrastran sus pasos
        it.setToolTip(f"<b>{g['nombre']}</b> · {n} pasos"
                      + (f"<br>{suprimidos} de {n} suprimidos" if suprimidos else "")
                      + "<br>Doble clic: renombrar · clic derecho: contraer, suprimir el grupo o desagrupar")
        self.lista.addItem(it)

    def resaltar(self, op_id):
        """"Buscar en el timeline": elige el ícono del paso y lo trae a la vista."""
        for g in (self.doc.grupos if self.doc else []):
            if g["plegado"] and op_id in g["pasos"]:
                self.plegar.emit(g["id"], False)        # si está en una carpeta contraída, primero la expande
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
        existentes = {o.id for o in self.doc.operaciones}

        def ranura(c):
            """Las filas que ocupa una fila de la lista: una carpeta contraída ocupa las de sus pasos escondidos."""
            g = self._grupo(c)
            return [i for i in g["pasos"] if i in existentes] if g is not None and g["plegado"] else [c]

        claves = self.claves()
        paso_de_fila = sum(len(ranura(c)) for c in claves[:fila])
        nuevo = destino_arrastre([x for c in claves for x in ranura(c)], clave, paso_de_fila)
        if clave == MARCADOR:
            if nuevo != self.doc.marcador:
                self.marcador.emit(nuevo)
        elif nuevo != self.doc.indice(clave):
            self.mover.emit(clave, nuevo)

    def _clic(self, item):
        clave = item.data(Qt.UserRole)
        if clave in (None, MARCADOR) or self._grupo(clave) is not None:
            return                      # la carpeta se maneja con su menú: un clic suyo reconstruiría la lista a mitad
        self.tocado.emit(clave)

    def _doble_clic(self, item):
        clave = item.data(Qt.UserRole)
        if not clave or clave == MARCADOR:
            return
        g = self._grupo(clave)
        if g is None:
            self.editar.emit(clave)
        else:
            self._renombrar_grupo(g)                        # Fusion: Rename sobre el bloque del grupo

    def _renombrar_grupo(self, g):
        """Fusion: Rename sobre la carpeta (doble clic en el nombre o desde su menú); Esc o Cancelar no cambian nada."""
        nombre, ok = QInputDialog.getText(self, "Renombrar grupo", "Nombre:", text=g["nombre"])
        if ok and nombre.strip():
            self.renombrar_grupo.emit(g["id"], nombre.strip())

    def _copiar_paso(self):
        """Ctrl+C: guarda la receta del paso elegido y los pasos que usa, para pegarla con Ctrl+V (SC9)."""
        it = self.lista.currentItem()
        clave = it.data(Qt.UserRole) if it is not None else None
        op = None if not clave or clave == MARCADOR or self._grupo(clave) else self.doc.operacion(clave)
        self._copiado = (op.a_dict(), sorted(op.dependencias())) if op is not None else None

    def _pegar_paso(self):
        """Ctrl+V: Documento.pegar copia el paso al final; si una referencia no está, la ventana avisa y no pega nada."""
        if self._copiado is not None:
            self.pegar.emit(*self._copiado)

    def elegidos(self):
        """Ids de los pasos elegidos en la lista (sin el marcador ni las carpetas)."""
        return [i for i in (it.data(Qt.UserRole) for it in self.lista.selectedItems())
                if i not in (None, MARCADOR) and not str(i).startswith(GRUPO)]

    def entradas_menu(self, op_id, ids=None):
        """Menú contextual del paso, distinto según su tipo como en Fusion (boceto, operación, unión):
        [Entrada | None (separador)]. Una Entrada con `hijos` es un submenú. `ids`: todos los pasos elegidos (con
        varios, suprimir, buscar en la ventana y crear conjunto los toman a todos)."""
        doc = self.doc
        ids = ids if ids and op_id in ids else [op_id]
        crean = {c.op_id for c in doc.estado_final.cuerpos.values()}
        crea = any(i in crean for i in ids)
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
            (E(f"{'Desuprimir' if op.suprimida else 'Suprimir'} {len(ids)} pasos",
               emitir(self.suprimir_varios, ids, not op.suprimida)) if len(ids) > 1 else
             E(f"Desuprimir {sufijo}" if op.suprimida else f"Suprimir {sufijo}",
               emitir(self.suprimir, op_id, not op.suprimida))),
            E("Configurar", emitir(self.configurar, op_id),
              ayuda="Suma la supresión de este paso a la tabla de configuraciones (una columna «Suprimir»).",
              habilitada=len(ids) == 1),
            None,
            # Fusion: Create Group sobre las operaciones elegidas; con un solo paso no hay nada que agrupar (SC9).
            *([E(f"Agrupar {len(ids)} pasos", emitir(self.agrupar, ids),
                 ayuda="Los pasos elegidos pasan a una carpeta del timeline.")] if len(ids) > 1 else []),
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
            E("Buscar en la ventana", emitir(self.buscar_ventana, ids), crea,
              "Elige en la vista los cuerpos que crea el paso y los encuadra." if crea else
              "Este paso no creó ningún cuerpo que siga vivo."),
            E("Crear conjunto de selección…", emitir(self.crear_conjunto, ids), crea,
              "Guarda los cuerpos que crea el paso como un conjunto de selección." if crea else
              "Este paso no creó ningún cuerpo que siga vivo."),
            None,
            (E(f"Eliminar {len(ids)} pasos", emitir(self.eliminar_varios, ids),
               ayuda="Borra todos los pasos elegidos juntos (un solo paso de deshacer).") if len(ids) > 1 else
             E("Eliminar", emitir(self.eliminar, op_id))),
        ]

    def entradas_grupo(self, g):
        """Menú de una carpeta (Fusion: Rename, Supprimir operaciones y Edit Group › Expand)."""
        E = Entrada
        n = len(g["pasos"])
        todas = all(self.doc.operacion(i).suprimida for i in g["pasos"])
        return [
            E(f"{'Expandir' if g['plegado'] else 'Contraer'} el grupo", lambda: self.plegar.emit(g["id"],
                                                                                                 not g["plegado"]),
              ayuda="El +/− del bloque: contraído esconde sus pasos en la barra (no cambia el modelo)."),
            E("Renombrar…", lambda: self._renombrar_grupo(g)),
            E(f"{'Desuprimir' if todas else 'Suprimir'} el grupo ({n} pasos)",
              lambda: self.suprimir_varios.emit(g["pasos"], not todas),
              ayuda="Suprime o reactiva de una vez todos los pasos de la carpeta (un solo paso de deshacer)."),
            None,
            E("Desagrupar", lambda: self.desagrupar.emit(g["id"]),
              ayuda="Borra la carpeta y deja sus pasos sueltos, sin tocar el modelo."),
        ]

    def _menu(self, pos):
        item = self.lista.itemAt(pos)
        if item is None or self.doc is None:
            return
        clave = item.data(Qt.UserRole)
        grupo = self._grupo(clave)
        if grupo is not None:
            entradas = self.entradas_grupo(grupo)
        elif clave in (None, MARCADOR):
            return
        else:
            entradas = self.entradas_menu(clave, self.elegidos())
        m = QMenu(self)
        _llenar_menu(m, entradas)
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

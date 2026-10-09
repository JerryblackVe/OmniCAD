# -*- coding: utf-8 -*-
"""
Navegador flotante sobre el lienzo (arriba a la izquierda), como el BROWSER de Fusion 360:
componente raíz → Configuración del documento (unidades) → Vistas guardadas → Origen (O, X, Y, Z,
XY, XZ, YZ) → Construcción (planos de desfase) → Cuerpos → Bocetos.
Cada fila es una "cajita" clara sobre el fondo oscuro; el ojo muestra/oculta (clic sobre el ojo).
Doble clic sobre un boceto lo edita (como "Editar boceto" en Fusion); sobre una vista guardada, la
restaura. Clic derecho: nueva vista con nombre, renombrar o eliminar vistas, editar boceto o plano.
"""
from PySide6.QtCore import QEvent, QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFontMetricsF, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QMenu, QStyle, QStyledItemDelegate, QToolButton,
                               QTreeWidget, QTreeWidgetItem, QVBoxLayout)

from .estilo import TEXTO
from .iconos import icono

ROL_CLAVE, ROL_OJO, ROL_ICONO, ROL_TIPO = Qt.UserRole, Qt.UserRole + 1, Qt.UserRole + 2, Qt.UserRole + 3
ALTO_FILA = 24
EXPANDIDOS_INICIALES = {"__raiz__", "__config__", "__cuerpos__", "__bocetos__", "__planos__", "__analisis__",
                        "__uniones__"}
ORIGEN = [("__o__", "O", "punto"), ("__x__", "X", "linea"), ("__y__", "Y", "linea"), ("__z__", "Z", "linea"),
          ("__xy__", "XY", "plano_desfase"), ("__xz__", "XZ", "plano_desfase"), ("__yz__", "YZ", "plano_desfase")]


class _Delegado(QStyledItemDelegate):
    ojo_clic = Signal(str)

    def _medidas(self, option, index):
        f = option.font
        f.setBold(index.data(ROL_TIPO) == "raiz")
        texto = index.data(Qt.DisplayRole) or ""
        con_ojo = index.data(ROL_OJO) is not None
        ancho = (20 if con_ojo else 0) + 22 + QFontMetricsF(f).horizontalAdvance(texto) + 14
        return f, texto, con_ojo, ancho

    def paint(self, p, option, index):
        f, texto, con_ojo, ancho = self._medidas(option, index)
        r = option.rect
        caja = QRectF(r.left() + 1, r.top() + 2, ancho, r.height() - 4)
        p.save()
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#cfe6f7") if option.state & QStyle.State_Selected else QColor(245, 245, 245, 242))
        p.drawRect(caja)
        x = caja.left() + 4
        y = caja.center().y() - 8
        if con_ojo:
            visible = bool(index.data(ROL_OJO))
            p.drawPixmap(QRectF(x, y, 16, 16), icono("ojo" if visible else "ojo_no").pixmap(32, 32), QRectF(0, 0, 32, 32))
            x += 20
        p.drawPixmap(QRectF(x, y, 16, 16), icono(index.data(ROL_ICONO) or "").pixmap(32, 32), QRectF(0, 0, 32, 32))
        x += 22
        p.setFont(f)
        p.setPen(QColor(TEXTO) if index.data(ROL_OJO) is not False else QColor("#9a9a9a"))
        p.drawText(QRectF(x, caja.top(), caja.right() - x, caja.height()), Qt.AlignVCenter | Qt.AlignLeft, texto)
        p.restore()

    def sizeHint(self, option, index):
        return QSize(int(self._medidas(option, index)[3]) + 4, ALTO_FILA)

    def updateEditorGeometry(self, editor, option, index):
        """Renombrar en el lugar: la caja de texto va donde está el nombre (después del ojo y del ícono)."""
        _f, _t, con_ojo, ancho = self._medidas(option, index)
        x = option.rect.left() + 1 + 4 + (20 if con_ojo else 0) + 22
        editor.setGeometry(int(x), option.rect.top() + 1, max(140, int(ancho) - int(x) + option.rect.left() + 30),
                           option.rect.height() - 2)

    def editorEvent(self, evento, modelo, option, index):
        if (evento.type() == QEvent.MouseButtonPress and evento.button() == Qt.LeftButton
                and index.data(ROL_OJO) is not None):
            ojo = QRectF(option.rect.left() + 3, option.rect.center().y() - 9, 20, 18)
            if ojo.contains(evento.position()):
                self.ojo_clic.emit(index.data(ROL_CLAVE))
                return True
        return False


class _Arbol(QTreeWidget):
    def drawBranches(self, p, rect, index):
        item = self.itemFromIndex(index)
        if item is None or not item.childCount():
            return
        p.save()
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(QColor("#d6d9de"), 1.6))
        cx, cy = rect.right() - 9, rect.center().y()
        if item.isExpanded():
            p.drawPolyline(QPolygonF([QPointF(cx - 4, cy - 2), QPointF(cx, cy + 2), QPointF(cx + 4, cy - 2)]))
        else:
            p.drawPolyline(QPolygonF([QPointF(cx - 2, cy - 4), QPointF(cx + 2, cy), QPointF(cx - 2, cy + 4)]))
        p.restore()


RENOMBRABLES = {"cuerpo", "boceto", "plano", "eje", "punto"}


class Navegador(QFrame):
    ojo = Signal(str)            # clave de lo que se mostró/ocultó
    seleccionado = Signal(str)   # id de cuerpo o de boceto
    editar = Signal(str)         # id de la operación de boceto o de plano (doble clic / menú)
    vista_nueva = Signal()
    vista_ir = Signal(str)
    vista_renombrar = Signal(str)
    vista_borrar = Signal(str)
    accion = Signal(str, str)    # (acción del menú contextual, clave del elemento): renombrar, opacidad:50…
    renombrado = Signal(str, str, str)  # (tipo, clave, nombre nuevo): renombrar en el lugar

    def __init__(self, parent=None):
        super().__init__(parent)
        self.analisis = []           # [(clave "analisis:Nombre", nombre, visible)] (los pasa la ventana)
        self.componentes = []        # [(id, nombre, fijo, [(id de cuerpo, nombre)])]
        self.uniones = []            # [(id de la operación, nombre)]
        self.lienzos = []            # [(id, nombre, visible)] (Lienzos y calcomanías)
        self.setFixedWidth(300)
        cabecera = QFrame(objectName="cabecera_navegador")
        h = QHBoxLayout(cabecera)
        h.setContentsMargins(8, 1, 2, 1)
        h.addWidget(QLabel("NAVEGADOR"))
        h.addStretch(1)
        self.b_plegar = QToolButton(text="–")
        self.b_plegar.setToolTip("Plegar / desplegar el navegador")
        self.b_plegar.clicked.connect(self._plegar)
        h.addWidget(self.b_plegar)
        self.cabecera = cabecera

        self.arbol = _Arbol(objectName="arbol_navegador")
        self.arbol.setHeaderHidden(True)
        self.arbol.setIndentation(18)
        self.arbol.setRootIsDecorated(True)
        self.arbol.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.arbol.setFocusPolicy(Qt.NoFocus)
        self.arbol.viewport().setAutoFillBackground(False)
        self.delegado = _Delegado(self.arbol)
        self.delegado.ojo_clic.connect(self.ojo)
        self.arbol.setItemDelegate(self.delegado)
        self.arbol.itemClicked.connect(self._clic)
        self.arbol.itemDoubleClicked.connect(self._doble_clic)
        self.arbol.itemChanged.connect(self._cambio_nombre)
        self._renombrando = None            # (ítem, nombre anterior) mientras se edita el nombre en el lugar
        self.arbol.itemExpanded.connect(self.ajustar_alto)
        self.arbol.itemCollapsed.connect(self.ajustar_alto)
        self.arbol.setContextMenuPolicy(Qt.CustomContextMenu)
        self.arbol.customContextMenuRequested.connect(self._menu)

        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(4)
        v.addWidget(cabecera)
        v.addWidget(self.arbol)
        self._expandidos = set(EXPANDIDOS_INICIALES)
        self._items = {}

    # ------------------------------------------------------------ contenido
    def _item(self, padre, clave, texto, ico, tipo, ojo=None):
        it = QTreeWidgetItem([texto])
        it.setData(0, ROL_CLAVE, clave)
        it.setData(0, ROL_ICONO, ico)
        it.setData(0, ROL_TIPO, tipo)
        it.setData(0, ROL_OJO, ojo)
        (padre.addChild(it) if padre else self.arbol.addTopLevelItem(it))
        self._items[clave] = it
        return it

    def actualizar(self, titulo, cuerpos, bocetos, ocultos, vis, planos=(), vistas=()):
        """cuerpos / bocetos / planos: [(id, nombre)]; vistas: [nombre];
        vis: dict con 'todo', 'origen', 'planos', 'cuerpos', 'bocetos'."""
        if self._items:
            self._expandidos = {k for k, it in self._items.items() if it.isExpanded()}
        actual = self.arbol.currentItem()
        clave_actual = actual.data(0, ROL_CLAVE) if actual else None
        self.arbol.clear()
        self._items = {}
        raiz = self._item(None, "__raiz__", titulo, "componente", "raiz", vis["todo"])
        config = self._item(raiz, "__config__", "Configuración del documento", "engranaje", "info")
        self._item(config, "__unidades__", "Unidades: mm, g", "unidades", "info")
        self._item(config, "__tipo_diseno__", "Diseño de piezas", "unidades", "info")   # como Fusion 2026
        carpeta = self._item(raiz, "__vistas__", "Vistas guardadas", "carpeta", "vistas")
        for nombre in vistas:
            self._item(carpeta, f"vista:{nombre}", nombre, "visualizacion", "vista")
        origen = self._item(raiz, "__origen__", "Origen", "carpeta", "carpeta", vis["origen"])
        for clave, texto, ico in ORIGEN:
            self._item(origen, clave, texto, ico, "origen", clave not in ocultos)
        for clave, titulo_c, ico, elementos in (("__planos__", "Construcción", "plano_desfase", planos),
                                                ("__cuerpos__", "Cuerpos", "cuerpo", cuerpos),
                                                ("__bocetos__", "Bocetos", "boceto", bocetos)):
            if not elementos:
                continue
            carpeta = self._item(raiz, clave, titulo_c, "carpeta", "carpeta", vis[clave.strip("_")])
            tipo = {"plano_desfase": "plano"}.get(ico, ico)
            for elemento in elementos:
                ident, nombre = elemento[0], elemento[1]
                ico_e = elemento[2] if len(elemento) > 2 else ico
                tipo_e = {"plano_desfase": "plano", "eje_arista": "eje", "punto_vertice": "punto"}.get(ico_e, tipo)
                self._item(carpeta, ident, nombre, ico_e, tipo_e, ident not in ocultos)
        for ident, nombre, fijo, cuerpos_c in self.componentes:     # componentes con sus cuerpos
            comp = self._item(raiz, ident, nombre + ("  (fijo)" if fijo else ""), "componente", "componente",
                              ident not in ocultos)
            if cuerpos_c:
                carpeta_c = self._item(comp, f"{ident}:cuerpos", "Cuerpos", "carpeta", "carpeta")
                for cid, nombre_c in cuerpos_c:
                    self._item(carpeta_c, cid, nombre_c, "cuerpo", "cuerpo", cid not in ocultos)
        if self.lienzos:                    # carpeta «Lienzos»
            carpeta = self._item(raiz, "__lienzos__", "Lienzos", "carpeta", "carpeta")
            for ident, nombre, visible in self.lienzos:
                self._item(carpeta, ident, nombre, "lienzo", "plano", visible)
        if self.uniones:                    # carpeta «Uniones»
            carpeta = self._item(raiz, "__uniones__", "Uniones", "carpeta", "carpeta")
            for ident, nombre in self.uniones:
                self._item(carpeta, ident, nombre, "union", "union")
        if self.analisis:                   # carpeta «Análisis» (sección, cebra, curvatura…)
            carpeta = self._item(raiz, "__analisis__", "Análisis", "carpeta", "carpeta")
            for ident, nombre, visible in self.analisis:
                self._item(carpeta, ident, nombre, "seccion", "analisis", visible)
        for clave, it in self._items.items():
            it.setExpanded(clave in self._expandidos)
        if clave_actual in self._items:
            self.arbol.setCurrentItem(self._items[clave_actual])
        self.ajustar_alto()

    def item(self, clave):
        return self._items.get(clave)

    # ------------------------------------------------------------ interacción
    def _clic(self, item, _col):
        if item.data(0, ROL_TIPO) in ("cuerpo", "boceto", "plano", "eje", "punto", "origen"):
            self.seleccionado.emit(item.data(0, ROL_CLAVE))

    def _doble_clic(self, item, _col):
        """Como el navegador de Fusion: doble clic sobre el nombre lo renombra en el lugar (editar un boceto o
        un plano queda en el clic derecho y en el timeline)."""
        tipo, clave = item.data(0, ROL_TIPO), item.data(0, ROL_CLAVE)
        if tipo in RENOMBRABLES:
            self.renombrar_en_linea(item)
        elif tipo == "union":
            self.editar.emit(clave.split("_")[0])
        elif tipo == "vista":
            self.vista_ir.emit(clave.split(":", 1)[1])

    def renombrar_en_linea(self, item=None):
        """F2 o doble clic: caja de texto sobre el nombre; Enter confirma, Esc cancela."""
        item = item or self.arbol.currentItem()
        if item is None or item.data(0, ROL_TIPO) not in RENOMBRABLES:
            return False
        self._renombrando = (item, item.text(0))
        item.setFlags(item.flags() | Qt.ItemIsEditable)
        self.arbol.editItem(item, 0)
        return True

    def _cambio_nombre(self, item, _col):
        if self._renombrando is None or item is not self._renombrando[0]:
            return
        _item, anterior = self._renombrando
        nuevo = item.text(0).strip()
        if nuevo == anterior:
            return                          # cambio de banderas al abrir la caja: todavía no se escribió nada
        self._renombrando = None
        if not nuevo:
            self.arbol.blockSignals(True)
            item.setText(0, anterior)
            self.arbol.blockSignals(False)
            return
        self.renombrado.emit(item.data(0, ROL_TIPO), item.data(0, ROL_CLAVE), nuevo)

    def _menu(self, pos):
        item = self.arbol.itemAt(pos)
        if item is None:
            return
        tipo, clave = item.data(0, ROL_TIPO), item.data(0, ROL_CLAVE)
        m = QMenu(self)
        if tipo == "vistas":
            m.addAction("Nueva vista con nombre", self.vista_nueva.emit)
        elif tipo == "vista":
            nombre = clave.split(":", 1)[1]
            m.addAction("Ir a la vista", lambda: self.vista_ir.emit(nombre))
            m.addAction("Renombrar…", lambda: self.vista_renombrar.emit(nombre))
            m.addAction("Eliminar", lambda: self.vista_borrar.emit(nombre))
        elif tipo == "boceto":
            m.addAction("Editar boceto", lambda: self.editar.emit(clave))
            m.addAction("Guardar como DXF…", lambda: self.accion.emit("boceto_dxf", clave))
            m.addAction("Renombrar…", lambda: self.accion.emit("renombrar_paso", clave))
            m.addAction("Buscar en el timeline", lambda: self.accion.emit("buscar_timeline", clave))
            m.addSeparator()
            m.addAction("Suprimir", lambda: self.accion.emit("borrar_paso", clave))
        elif tipo in ("plano", "eje", "punto"):
            m.addAction("Editar…", lambda: self.editar.emit(clave.split("_")[0]))
            m.addAction("Buscar en el timeline", lambda: self.accion.emit("buscar_timeline", clave.split("_")[0]))
            m.addSeparator()
            m.addAction("Suprimir", lambda: self.accion.emit("borrar_paso", clave.split("_")[0]))
        elif tipo == "union":
            m.addAction("Editar unión…", lambda: self.editar.emit(clave))
            m.addAction("Animar unión", lambda: self.accion.emit("animar_union", clave))
            m.addAction("Accionar unión…", lambda: self.accion.emit("accionar_union", clave))
            m.addSeparator()
            m.addAction("Suprimir", lambda: self.accion.emit("borrar_paso", clave))
        elif tipo == "componente":
            m.addAction("Fijar / liberar", lambda: self.accion.emit("fijar_componente", clave))
            m.addAction("Aislar", lambda: self.accion.emit("aislar_componente", clave))
            m.addAction("Desaislar", lambda: self.accion.emit("desaislar", clave))
            m.addAction("Renombrar…", lambda: self.accion.emit("renombrar_paso", clave))
            m.addAction("Buscar en el timeline", lambda: self.accion.emit("buscar_timeline", clave))
        elif tipo == "analisis":
            m.addAction("Mostrar u ocultar", lambda: self.accion.emit("analisis_ojo", clave))
            m.addAction("Suprimir", lambda: self.accion.emit("analisis_borrar", clave))
        elif tipo == "cuerpo":
            m.addAction("Mover/copiar", lambda: self.accion.emit("mover", clave))
            m.addSeparator()
            m.addAction("Renombrar…", lambda: self.accion.emit("renombrar_cuerpo", clave))
            m.addAction("Aspecto…", lambda: self.accion.emit("aspecto", clave))
            m.addAction("Material físico…", lambda: self.accion.emit("material", clave))
            m.addAction("Propiedades", lambda: self.accion.emit("propiedades", clave))
            m.addSeparator()
            opacidad = m.addMenu("Control de opacidad")
            for pct in (100, 70, 50, 30, 10):
                opacidad.addAction(f"{pct} %", lambda p=pct: self.accion.emit(f"opacidad:{p}", clave))
            m.addAction("Aislar", lambda: self.accion.emit("aislar", clave))
            m.addAction("Desaislar", lambda: self.accion.emit("desaislar", clave))
            m.addAction("Buscar en el timeline", lambda: self.accion.emit("buscar_timeline", clave.split(".c")[0]))
            m.addSeparator()
            m.addAction("Quitar", lambda: self.accion.emit("quitar", clave))
            m.addAction("Suprimir", lambda: self.accion.emit("suprimir", clave))
        if not m.isEmpty():
            m.exec(self.arbol.viewport().mapToGlobal(pos))

    def _plegar(self):
        self.arbol.setVisible(self.arbol.isHidden())
        self.b_plegar.setText("+" if self.arbol.isHidden() else "–")
        self.ajustar_alto()

    def ajustar_alto(self, *_):
        filas = 0
        pila = [self.arbol.topLevelItem(i) for i in range(self.arbol.topLevelItemCount())]
        while pila:
            it = pila.pop()
            filas += 1
            if it.isExpanded():
                pila.extend(it.child(i) for i in range(it.childCount()))
        alto = self.cabecera.sizeHint().height() + (filas * ALTO_FILA + 8 if not self.arbol.isHidden() else 0)
        limite = (self.parentWidget().height() - 150) if self.parentWidget() else alto
        self.setFixedHeight(max(self.cabecera.sizeHint().height(), min(alto, max(limite, 120))))

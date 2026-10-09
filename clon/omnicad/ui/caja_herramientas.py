# -*- coding: utf-8 -*-
"""Caja de herramientas (tecla S), como la «Model Toolbox» de Fusion.

Qué hace, según la ayuda de Fusion (referencia de atajos: «Model Toolbox · S») y su tutorial «Use the Fusion
Toolbox»:
  - S la abre junto al ratón, con un buscador arriba y debajo los comandos FIJADOS («atajos»). En Diseño vienen
    fijados Extruir y Empalme; dentro de un boceto la caja tiene su propia lista (atajos de boceto, vacía al
    principio: Fusion no dice cuáles trae).
  - El buscador filtra todos los comandos que se pueden usar en ese momento mientras se escribe; las flechas
    recorren la lista y Enter o un clic ejecuta el comando.
  - En cada resultado, la chinche fija el comando en la caja o lo quita.
  - Los atajos se reordenan arrastrándolos y la caja se agranda desde la esquina de abajo a la derecha.
Lo fijado se guarda en las preferencias (`atajos/diseno`, `atajos/boceto`: claves separadas por comas).

Es un widget hijo de la ventana (no una ventana aparte): no depende del gestor de ventanas (Windows y Linux). Se cierra con Esc, al ejecutar un comando o al hacer clic afuera.
"""
from PySide6.QtCore import QEvent, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (QApplication, QFrame, QHBoxLayout, QLabel, QLineEdit, QListView, QListWidget,
                               QListWidgetItem, QSizeGrip, QStyledItemDelegate, QStyleOptionViewItem, QToolButton,
                               QVBoxLayout, QWidget)

from .busqueda_comandos import coincidencias, comandos_disponibles, nombre_accion
from .iconos import icono

CONTEXTOS = {"diseno": "ATAJOS DE DISEÑO", "boceto": "ATAJOS DE BOCETO"}
TAMANO_INICIAL = QSize(300, 250)
MAXIMO_RESULTADOS = 30


def leer_fijados(prefs, contexto):
    return [c for c in prefs[f"atajos/{contexto}"].split(",") if c]


def guardar_fijados(prefs, contexto, claves):
    prefs[f"atajos/{contexto}"] = ",".join(claves)


class _IconoArriba(QStyledItemDelegate):
    """Atajos como en una grilla de íconos (ícono arriba, nombre abajo) sin dejar el modo lista, que es el que
    reordena al arrastrar (en modo ícono Qt solo cambia la posición en pantalla, no el orden)."""

    def initStyleOption(self, opcion, indice):
        super().initStyleOption(opcion, indice)
        opcion.decorationPosition = QStyleOptionViewItem.Top
        opcion.displayAlignment = Qt.AlignHCenter | Qt.AlignTop
        opcion.features |= QStyleOptionViewItem.WrapText


class _ListaAtajos(QListWidget):
    reordenada = Signal()

    def dropEvent(self, e):
        super().dropEvent(e)
        self.reordenada.emit()


class _FilaResultado(QWidget):
    """Ícono, nombre (con su atajo de teclado) y la chinche para fijar o quitar."""

    def __init__(self, accion, fijado, al_fijar):
        super().__init__()
        h = QHBoxLayout(self)
        h.setContentsMargins(6, 2, 2, 2)
        h.setSpacing(6)
        ico = QLabel()
        ico.setPixmap(accion.icon().pixmap(18, 18))
        ico.setFixedWidth(20)
        h.addWidget(ico)
        partes = accion.text().split("\t")
        h.addWidget(QLabel(nombre_accion(accion)), 1)
        if len(partes) > 1:
            h.addWidget(QLabel(partes[1], objectName="atajo_teclado"))
        self.chinche = QToolButton(objectName="chinche", checkable=True, checked=fijado)
        self.chinche.setIcon(icono("chinche"))
        self.chinche.setIconSize(QSize(14, 14))
        self.chinche.setAutoRaise(True)
        self.chinche.setToolTip("Quitar de atajos" if fijado else "Fijar en atajos")
        self.chinche.toggled.connect(al_fijar)
        h.addWidget(self.chinche)


class CajaHerramientas(QFrame):
    """La caja de la tecla S. `acciones`: dict clave → QAction de la ventana; `prefs`: Preferencias."""

    def __init__(self, acciones, prefs, parent):
        super().__init__(parent)
        self.setObjectName("caja_herramientas")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setWindowFlags(Qt.SubWindow)            # así la esquina (QSizeGrip) la agranda a ella, no a la ventana
        self.acciones = acciones
        self.prefs = prefs
        self.contexto = "diseno"
        self._foco_anterior = None
        self.resize(TAMANO_INICIAL)
        self.setMinimumSize(200, 140)

        self.titulo = QLabel(objectName="titulo_caja")
        self.campo = QLineEdit(placeholderText="Buscar")
        self.campo.addAction(icono("buscar"), QLineEdit.LeadingPosition)
        self.campo.setClearButtonEnabled(True)
        self.campo.textEdited.connect(self._filtrar)
        self.campo.returnPressed.connect(self._ejecutar_actual)
        self.campo.installEventFilter(self)

        self.atajos = _ListaAtajos(objectName="atajos_caja")
        self.atajos.setFlow(QListView.LeftToRight)
        self.atajos.setWrapping(True)
        self.atajos.setResizeMode(QListView.Adjust)
        self.atajos.setGridSize(QSize(74, 62))
        self.atajos.setIconSize(QSize(24, 24))
        self.atajos.setItemDelegate(_IconoArriba(self.atajos))
        self.atajos.setDragDropMode(QListWidget.InternalMove)
        self.atajos.setDefaultDropAction(Qt.MoveAction)
        self.atajos.setFocusPolicy(Qt.NoFocus)
        self.atajos.itemClicked.connect(lambda it: self._ejecutar(it.data(Qt.UserRole)))
        self.atajos.reordenada.connect(self._guardar_orden)
        self.vacio = QLabel("Buscá un comando y fijalo con la chinche para tenerlo acá.", objectName="vacio_caja",
                            wordWrap=True, alignment=Qt.AlignCenter)

        self.resultados = QListWidget(objectName="resultados_caja")
        self.resultados.setFocusPolicy(Qt.NoFocus)
        self.resultados.itemClicked.connect(lambda it: self._ejecutar(it.data(Qt.UserRole)))

        v = QVBoxLayout(self)
        v.setContentsMargins(8, 6, 8, 2)
        v.setSpacing(6)
        v.addWidget(self.titulo)
        v.addWidget(self.campo)
        v.addWidget(self.atajos, 1)
        v.addWidget(self.vacio, 1)
        v.addWidget(self.resultados, 1)
        v.addWidget(QSizeGrip(self), 0, Qt.AlignRight | Qt.AlignBottom)
        self.hide()

    # ------------------------------------------------------------ abrir y cerrar
    def abrir(self, contexto, pos):
        """Abre la caja de `contexto` ("diseno" o "boceto") con la esquina de arriba a la izquierda cerca de `pos`
        (coordenadas de la ventana), sin salirse de ella."""
        self.contexto = contexto
        foco = QApplication.focusWidget()
        if foco is None or not self.isAncestorOf(foco):
            self._foco_anterior = foco      # al cerrar vuelve ahí (p. ej. el lienzo del boceto)
        self.titulo.setText(CONTEXTOS[contexto])
        self.campo.clear()
        self._llenar_atajos()
        self._mostrar_resultados(False)
        padre = self.parentWidget().rect()
        x = min(max(pos.x() - 20, 0), max(padre.width() - self.width(), 0))
        y = min(max(pos.y() - 20, 0), max(padre.height() - self.height(), 0))
        self.move(x, y)
        self.show()
        self.raise_()
        self.campo.setFocus(Qt.PopupFocusReason)
        QApplication.instance().installEventFilter(self)

    def cerrar(self):
        QApplication.instance().removeEventFilter(self)
        self.hide()
        # Sin esto el foco queda en cualquier widget y las teclas siguientes disparan atajos de la ventana: en un
        # boceto, escribir «2» elegía «Selección de forma libre» en vez de abrir la entrada de longitud.
        foco, self._foco_anterior = self._foco_anterior, None
        try:
            if foco is not None and foco.isVisible():
                foco.setFocus(Qt.PopupFocusReason)
        except RuntimeError:                # el widget ya no existe (p. ej. se cerró el boceto)
            pass

    def eventFilter(self, obj, e):
        tipo = e.type()
        if obj is self.campo and tipo == QEvent.ShortcutOverride and e.key() == Qt.Key_Escape:
            e.accept()                      # Esc cierra la caja antes que el «cancelar» de la ventana
            return True
        if obj is self.campo and tipo == QEvent.KeyPress:
            if e.key() == Qt.Key_Escape:
                self.cerrar()
                return True
            if e.key() in (Qt.Key_Down, Qt.Key_Up) and self.resultados.isVisible() and self.resultados.count():
                paso = 1 if e.key() == Qt.Key_Down else -1
                fila = max(0, min(self.resultados.count() - 1, self.resultados.currentRow() + paso))
                self.resultados.setCurrentRow(fila)
                return True
        if tipo == QEvent.MouseButtonPress and self.isVisible():
            dentro = self.rect().contains(self.mapFromGlobal(e.globalPosition().toPoint()))
            if not dentro:
                self.cerrar()               # clic afuera: se cierra y el clic sigue su camino
        return False

    # ------------------------------------------------------------ atajos fijados
    def fijados(self):
        return leer_fijados(self.prefs, self.contexto)

    def fijar(self, clave, si):
        claves = [c for c in self.fijados() if c != clave] + ([clave] if si else [])
        guardar_fijados(self.prefs, self.contexto, claves)
        self._llenar_atajos()

    def _llenar_atajos(self):
        self.atajos.clear()
        for clave in self.fijados():
            a = self.acciones.get(clave)
            if a is None:
                continue                    # un comando que ya no existe: se ignora (sigue guardado)
            it = QListWidgetItem(a.icon(), nombre_accion(a))
            it.setData(Qt.UserRole, clave)
            it.setToolTip(a.toolTip())
            if not a.isEnabled():
                it.setFlags(it.flags() & ~Qt.ItemIsEnabled)
            self.atajos.addItem(it)
        if not self.resultados.isVisible():
            self._mostrar_resultados(False)

    def _guardar_orden(self):
        visibles = [self.atajos.item(i).data(Qt.UserRole) for i in range(self.atajos.count())]
        ocultos = [c for c in self.fijados() if c not in visibles]     # guardados pero sin acción hoy
        guardar_fijados(self.prefs, self.contexto, visibles + ocultos)

    # ------------------------------------------------------------ búsqueda
    def _mostrar_resultados(self, si):
        self.resultados.setVisible(si)
        self.atajos.setVisible(not si and self.atajos.count() > 0)
        self.vacio.setVisible(not si and self.atajos.count() == 0)

    def _filtrar(self, texto):
        self.resultados.clear()
        if not texto.strip():
            self._mostrar_resultados(False)
            return
        fijados = set(self.fijados())
        for clave in coincidencias(texto, comandos_disponibles(self.acciones), MAXIMO_RESULTADOS):
            it = QListWidgetItem()
            it.setData(Qt.UserRole, clave)
            fila = _FilaResultado(self.acciones[clave], clave in fijados, lambda si, c=clave: self.fijar(c, si))
            it.setSizeHint(fila.sizeHint())
            self.resultados.addItem(it)
            self.resultados.setItemWidget(it, fila)
        if self.resultados.count():
            self.resultados.setCurrentRow(0)
        else:
            it = QListWidgetItem(f"Ningún comando contiene «{texto.strip()}»")
            it.setFlags(Qt.NoItemFlags)
            self.resultados.addItem(it)
        self._mostrar_resultados(True)

    def _ejecutar_actual(self):
        it = self.resultados.currentItem() if self.resultados.isVisible() else None
        if it is not None:
            self._ejecutar(it.data(Qt.UserRole))

    def _ejecutar(self, clave):
        a = self.acciones.get(clave) if clave else None
        if a is None or not a.isEnabled():
            return
        self.cerrar()
        QTimer.singleShot(0, a.trigger)     # después de cerrar: el comando abre su panel

    def pos_raton(self):
        """Posición del ratón en coordenadas de la ventana (dónde abrir la caja)."""
        return self.parentWidget().mapFromGlobal(QCursor.pos())

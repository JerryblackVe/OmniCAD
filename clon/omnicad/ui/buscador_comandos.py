# -*- coding: utf-8 -*-
"""Buscador de comandos de la cinta: «Buscar comando…» (Ctrl+K).

Se escribe parte del nombre de un comando, sin importar mayúsculas ni tildes («chaflan» encuentra «Chaflán»), y
Enter o un clic lo ejecuta. Lista solo los comandos que se pueden usar en ese momento: los grisados no aparecen
(la misma regla de honestidad de la cinta) y los de boceto, solo dentro de un boceto.

La lista es un widget hijo de la ventana, no una ventana aparte: el foco se queda en el campo (se sigue
escribiendo) y no depende del gestor de ventanas (igual en Windows y en Linux).
`coincidencias` es pura (sin Qt) y se prueba sola.
"""
import re
import unicodedata

from PySide6.QtCore import QEvent, QPoint, QSize, Qt, QTimer
from PySide6.QtWidgets import QLineEdit, QListWidget, QListWidgetItem

from .iconos import icono

MAXIMO = 12                         # filas de la lista
ANCHO = 280                         # ancho del campo en la cinta
# Fuera de la búsqueda: el buscador, la caja de herramientas y los filtros de selección («Caras», «Cuerpos»…),
# que sueltos parecen comandos.
EXCLUIDAS = ("buscar_comando", "caja_herramientas")
PREFIJOS_EXCLUIDOS = ("filtro_",)


def _plano(texto):
    """Minúsculas y sin tildes: «Chaflán» → «chaflan»."""
    return "".join(c for c in unicodedata.normalize("NFD", texto.lower()) if unicodedata.category(c) != "Mn")


def coincidencias(consulta, entradas, maximo=MAXIMO):
    """Claves de `entradas` ((clave, nombre), …) cuyo nombre contiene TODAS las palabras de `consulta`, de la más
    parecida a la menos: primero los nombres que empiezan con la consulta, después los que tienen una palabra que
    empieza con ella y al final el resto; a igual puntaje, el nombre más corto. Sin mayúsculas ni tildes."""
    palabras = _plano(consulta).split()
    if not palabras:
        return []
    frase = " ".join(palabras)
    puntuadas = []
    for orden, (clave, nombre) in enumerate(entradas):
        n = _plano(nombre)
        if not all(p in n for p in palabras):
            continue
        if n.startswith(frase):
            puntaje = 0
        elif any(w.startswith(palabras[0]) for w in re.findall(r"\w+", n)):
            puntaje = 1
        else:
            puntaje = 2
        puntuadas.append((puntaje, len(n), orden, clave))
    return [clave for *_, clave in sorted(puntuadas)][:maximo]


def nombre_accion(accion):
    """Nombre de un comando sin el atajo ni los «&»: «Extruir\tE» → «Extruir»."""
    return accion.text().split("\t")[0].replace("&", "").strip()


def comandos_disponibles(acciones):
    """(clave, nombre) de los comandos que se pueden usar ahora (habilitados y visibles), sin nombres repetidos.
    También la usa la caja de herramientas (tecla S)."""
    vistos, lista = set(), []
    for clave, a in acciones.items():
        nombre = nombre_accion(a)
        if (not nombre or nombre in vistos or not a.isEnabled() or not a.isVisible() or clave in EXCLUIDAS
                or clave.startswith(PREFIJOS_EXCLUIDOS)):
            continue
        vistos.add(nombre)
        lista.append((clave, nombre))
    return lista


class BuscadorComandos(QLineEdit):
    """Campo «Buscar comando…» de la cinta. `acciones`: dict clave → QAction (las de la ventana)."""

    def __init__(self, acciones, parent=None):
        super().__init__(parent)
        self.setObjectName("buscador_comandos")
        self.acciones = acciones
        self.lista = None               # se crea al primer uso, hija de la ventana
        self.setPlaceholderText("Buscar comando…  (Ctrl+K)")
        self.addAction(icono("buscar"), QLineEdit.LeadingPosition)
        self.setClearButtonEnabled(True)
        self.setFixedWidth(ANCHO)
        self.textEdited.connect(self._filtrar)
        self.returnPressed.connect(self._ejecutar)

    # ------------------------------------------------------------ uso
    def enfocar(self):
        """Ctrl+K: pone el cursor en el buscador con el texto anterior elegido."""
        self.setFocus(Qt.ShortcutFocusReason)
        self.selectAll()
        if self.text().strip():
            self._filtrar(self.text())

    def disponibles(self):
        return comandos_disponibles(self.acciones)

    # ------------------------------------------------------------ lista desplegable
    def _crear_lista(self):
        lista = QListWidget(self.window())
        lista.setObjectName("lista_comandos")
        lista.setFocusPolicy(Qt.NoFocus)        # el foco se queda en el campo
        lista.setUniformItemSizes(True)
        lista.setIconSize(QSize(20, 20))
        lista.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        lista.itemClicked.connect(self._ejecutar)
        lista.hide()
        return lista

    def _filtrar(self, texto):
        if self.lista is None:
            self.lista = self._crear_lista()
        lista = self.lista
        lista.clear()
        if not texto.strip():
            lista.hide()
            return
        nombres = dict(self.disponibles())
        for clave in coincidencias(texto, list(nombres.items())):
            a = self.acciones[clave]
            partes = a.text().split("\t")
            it = QListWidgetItem(a.icon(), f"{nombres[clave]}    {partes[1]}" if len(partes) > 1 else nombres[clave])
            it.setData(Qt.UserRole, clave)
            lista.addItem(it)
        if lista.count():
            lista.setCurrentRow(0)
        else:
            it = QListWidgetItem(f"Ningún comando contiene «{texto.strip()}»")
            it.setFlags(Qt.NoItemFlags)
            lista.addItem(it)
        self._ubicar_lista()

    def _ubicar_lista(self):
        lista = self.lista
        filas = min(lista.count(), MAXIMO)
        alto = filas * max(lista.sizeHintForRow(0), 24) + 2 * lista.frameWidth() + 4
        ancho = max(self.width(), 320)
        pos = self.mapTo(self.window(), QPoint(self.width() - ancho, self.height() + 2))
        lista.setGeometry(max(pos.x(), 0), pos.y(), ancho, alto)
        lista.raise_()
        lista.show()

    def _ejecutar(self, item=None):
        """Enter o clic: ejecuta el comando elegido (o el primero de la lista)."""
        lista = self.lista
        if not isinstance(item, QListWidgetItem):
            item = lista.currentItem() if lista is not None and lista.isVisible() else None
        clave = item.data(Qt.UserRole) if item is not None else None
        if not clave:
            return
        self._cerrar()
        QTimer.singleShot(0, self.acciones[clave].trigger)     # después de soltar el foco: el comando abre su panel

    def _cerrar(self):
        self.clear()
        if self.lista is not None:
            self.lista.hide()
        self.clearFocus()

    # ------------------------------------------------------------ teclado y foco
    def event(self, e):
        # Esc cierra el buscador: sin esto, el atajo Esc de la ventana (cancelar comando) se lo lleva antes.
        if e.type() == QEvent.ShortcutOverride and e.key() == Qt.Key_Escape:
            e.accept()
            return True
        return super().event(e)

    def keyPressEvent(self, e):
        lista = self.lista
        if e.key() == Qt.Key_Escape:
            self._cerrar()
            return
        if lista is not None and lista.isVisible() and e.key() in (Qt.Key_Down, Qt.Key_Up):
            paso = 1 if e.key() == Qt.Key_Down else -1
            lista.setCurrentRow(max(0, min(lista.count() - 1, lista.currentRow() + paso)))
            return
        super().keyPressEvent(e)

    def focusOutEvent(self, e):
        if self.lista is not None:
            self.lista.hide()
        super().focusOutEvent(e)

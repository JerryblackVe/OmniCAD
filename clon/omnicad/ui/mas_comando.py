# -*- coding: utf-8 -*-
"""Botón «Más» (⋮) de los comandos de los menús de la cinta, como en Fusion (P9).

Al pasar el ratón por una fila de un menú aparece un «⋮» a la derecha; al hacerle clic (o con clic derecho sobre
la fila) se abre un menú con:
  - «Fijar en atajos» / «Quitar de atajos»: la caja de herramientas (tecla S) del contexto actual.
  - «Fijar en la barra» / «Quitar de la barra»: el comando queda como botón en la barra de arriba, junto a Rehacer.
  - «Cambiar atajo de teclado…»: elige otra combinación (avisa si ya la usa otro comando) o vuelve a la de fábrica.
Todo se guarda en las preferencias: `atajos/diseno`, `atajos/boceto` (los de la caja), `atajos/barra` (claves
separadas por comas) y `atajos/teclas` (JSON clave → combinación; solo los que difieren de fábrica).
"""
import json

from PySide6.QtCore import QEvent, QObject, QPointF, QRect, Qt
from PySide6.QtGui import QKeySequence, QPainter
from PySide6.QtWidgets import (QDialog, QDialogButtonBox, QHBoxLayout, QKeySequenceEdit, QLabel, QMenu, QPushButton,
                               QVBoxLayout)

from .caja_herramientas import guardar_fijados, leer_fijados

ANCHO_MAS = 22           # px de la zona del «⋮» contra el borde derecho de la fila


# ---------------------------------------------------------------- preferencias
def leer_teclas(prefs):
    """{clave de comando: combinación elegida por el usuario}; un JSON roto o ajeno se ignora, y también cada valor
    que no es una combinación de teclas ("" = sin atajo)."""
    try:
        datos = json.loads(prefs["atajos/teclas"] or "{}")
    except (ValueError, RecursionError):
        return {}
    if not isinstance(datos, dict):
        return {}
    return {str(c): t for c, t in datos.items() if isinstance(t, str) and (t == "" or _normal(t))}


def guardar_teclas(prefs, teclas):
    prefs["atajos/teclas"] = json.dumps(teclas, sort_keys=True)


def leer_barra(prefs):
    return [c for c in prefs["atajos/barra"].split(",") if c]


def guardar_barra(prefs, claves):
    prefs["atajos/barra"] = ",".join(claves)


def _normal(secuencia):
    """La combinación en el texto portable de Qt ('Ctrl+Shift+S'), para compararla y guardarla."""
    return QKeySequence(secuencia or "").toString(QKeySequence.PortableText)


def alternar(lista, clave):
    """Copia de `lista` con `clave` agregada al final, o quitada si ya estaba."""
    return [c for c in lista if c != clave] if clave in lista else [*lista, clave]


def conflicto(acciones, clave, secuencia):
    """Título del OTRO comando que ya usa `secuencia` (texto de combinación), o None."""
    if not secuencia:
        return None
    buscada = QKeySequence(secuencia)
    for otra, a in acciones.items():
        if otra != clave and not a.shortcut().isEmpty() and a.shortcut() == buscada:
            return a.property("titulo") or a.text().split("\t")[0]
    return None


# ---------------------------------------------------------------- cambiar el atajo
class DialogoAtajo(QDialog):
    """Pide la combinación nueva. `conflicto_de(texto)` devuelve el título del comando que ya la usa (o None)."""

    def __init__(self, titulo, actual, defecto, conflicto_de, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Cambiar atajo de teclado: {titulo}")
        self._conflicto_de, self._defecto = conflicto_de, defecto
        v = QVBoxLayout(self)
        v.addWidget(QLabel(f"Pulsá la combinación que querés para <b>{titulo}</b>."))
        self.editor = QKeySequenceEdit(QKeySequence(actual))
        self.editor.setMaximumSequenceLength(1)
        self.editor.keySequenceChanged.connect(self._revisar)
        v.addWidget(self.editor)
        self.aviso = QLabel()
        self.aviso.setWordWrap(True)
        v.addWidget(self.aviso)
        fila = QHBoxLayout()
        self.restablecer = QPushButton("Restablecer")
        self.restablecer.setToolTip(f"Vuelve a la combinación de fábrica: {defecto or 'ninguna'}.")
        self.restablecer.clicked.connect(lambda: self.editor.setKeySequence(QKeySequence(defecto)))
        self.quitar = QPushButton("Sin atajo")
        self.quitar.clicked.connect(self.editor.clear)
        fila.addWidget(self.restablecer)
        fila.addWidget(self.quitar)
        fila.addStretch(1)
        v.addLayout(fila)
        self.botones = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.botones.accepted.connect(self.accept)
        self.botones.rejected.connect(self.reject)
        v.addWidget(self.botones)
        self._revisar()

    def secuencia(self):
        return self.editor.keySequence().toString(QKeySequence.PortableText)

    def _revisar(self, *_):
        otro = self._conflicto_de(self.secuencia())
        self.aviso.setText(f"<span style='color:#e8a33d'>Ya lo usa «{otro}».</span>" if otro else "")
        self.botones.button(QDialogButtonBox.Ok).setEnabled(otro is None)


# ---------------------------------------------------------------- el «⋮» de los menús
class FiltroMas(QObject):
    """Se instala en los menús de la cinta: dibuja el «⋮» en la fila activa y abre el menú «Más»."""

    def __init__(self, ventana):
        super().__init__(ventana)
        self.ventana = ventana
        self.menu_abierto = None           # el menú «Más» en pantalla (las pruebas lo leen)
        self._origen = None                # el menú de la cinta desde el que se abrió

    def clave(self, accion):
        """La clave del comando de la ventana, o None (separadores, submenús, ítems grisados «no disponible»)."""
        if accion is None or accion.menu() is not None or accion.property("atajo_defecto") is None:
            return None
        return accion.property("clave")

    @staticmethod
    def zona(menu, accion):
        fila = menu.actionGeometry(accion)
        return QRect(fila.right() - ANCHO_MAS, fila.top(), ANCHO_MAS, fila.height())

    def eventFilter(self, obj, e):
        if not isinstance(obj, QMenu):
            return False
        tipo = e.type()
        if tipo == QEvent.Paint:
            activa = obj.activeAction()
            if activa is not None and activa.isEnabled() and self.clave(activa):
                obj.event(e)                                           # primero el dibujo normal del menú
                p = QPainter(obj)
                p.setRenderHint(QPainter.Antialiasing)
                p.setPen(Qt.NoPen)
                p.setBrush(obj.palette().text().color())
                centro = self.zona(obj, activa).center()
                for dy in (-5, 0, 5):                                  # tres puntos en vertical: «⋮» (no depende de la fuente)
                    p.drawEllipse(QPointF(centro.x(), centro.y() + dy), 1.7, 1.7)
                p.end()
                return True
        elif tipo in (QEvent.MouseButtonPress, QEvent.MouseButtonRelease) and e.button() == Qt.LeftButton:
            accion = obj.actionAt(e.position().toPoint())
            if accion is not None and accion.isEnabled() and self.clave(accion) \
                    and self.zona(obj, accion).contains(e.position().toPoint()):
                if tipo == QEvent.MouseButtonRelease:
                    self.abrir(obj, accion)
                return True                                            # el clic en el «⋮» no ejecuta el comando
        elif tipo == QEvent.ContextMenu:
            accion = obj.actionAt(e.pos())
            if accion is not None and accion.isEnabled() and self.clave(accion):
                self.abrir(obj, accion, e.globalPos())
                return True
        return False

    # ------------------------------------------------------------ menú «Más»
    def construir_menu(self, accion):
        v, clave = self.ventana, self.clave(accion)
        contexto = v.contexto_atajos()
        m = QMenu(v)
        m.setToolTipsVisible(True)
        fijado = clave in leer_fijados(v.prefs, contexto)
        a = m.addAction("Quitar de atajos" if fijado else "Fijar en atajos")
        a.setToolTip("Caja de herramientas (tecla S): " + ("saca" if fijado else "agrega") + " este comando.")
        a.triggered.connect(lambda: self.alternar_atajo(clave))
        en_barra = clave in leer_barra(v.prefs)
        a = m.addAction("Quitar de la barra" if en_barra else "Fijar en la barra")
        a.setToolTip("Barra de arriba, junto a Rehacer: " + ("saca" if en_barra else "agrega") + " el botón del comando.")
        a.triggered.connect(lambda: self.alternar_barra(clave))
        m.addSeparator()
        a = m.addAction("Cambiar atajo de teclado…")
        a.triggered.connect(lambda: self.cambiar_tecla(clave))
        return m

    def abrir(self, menu, accion, pos=None):
        """Abre el menú «Más» del comando de la fila (sin bloquear: `popup`)."""
        self._origen = menu
        if self.menu_abierto is not None:                           # cada clic arma un menú hijo de la ventana: no se juntan
            self.menu_abierto.deleteLater()
        self.menu_abierto = self.construir_menu(accion)
        self.menu_abierto.aboutToHide.connect(self._cerrar_menus)   # al elegir algo, el menú de la cinta también se va
        zona = self.zona(menu, accion)
        self.menu_abierto.popup(pos if pos is not None else menu.mapToGlobal(zona.bottomRight()))
        return self.menu_abierto

    def _cerrar_menus(self):
        w = self._origen
        while isinstance(w, QMenu):
            w.hide()
            w = w.parentWidget()

    def alternar_atajo(self, clave):
        v = self.ventana
        contexto = v.contexto_atajos()
        guardar_fijados(v.prefs, contexto, alternar(leer_fijados(v.prefs, contexto), clave))
        return contexto

    def alternar_barra(self, clave):
        v = self.ventana
        guardar_barra(v.prefs, alternar(leer_barra(v.prefs), clave))
        v.refrescar_barra_fijados()

    def cambiar_tecla(self, clave, secuencia=None):
        """Con `secuencia` (texto de combinación, "" = sin atajo) la aplica directo; sin ella abre el diálogo.
        Devuelve la combinación que quedó o None si se canceló o la usa otro comando."""
        v = self.ventana
        accion = v.acciones[clave]
        defecto = _normal(accion.property("atajo_defecto"))
        if secuencia is None:
            dlg = DialogoAtajo(accion.property("titulo"), accion.shortcut().toString(QKeySequence.PortableText),
                               defecto, lambda s: conflicto(v.acciones, clave, s), v)
            if dlg.exec() != QDialog.Accepted:
                return None
            secuencia = dlg.secuencia()
        secuencia = _normal(secuencia)
        if conflicto(v.acciones, clave, secuencia):
            return None
        teclas = leer_teclas(v.prefs)
        if secuencia == defecto:
            teclas.pop(clave, None)
        else:
            teclas[clave] = secuencia
        guardar_teclas(v.prefs, teclas)
        v.aplicar_teclas()
        return secuencia

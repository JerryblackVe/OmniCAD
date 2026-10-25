# -*- coding: utf-8 -*-
"""
Fila de PREAJUSTES de un diálogo de comando [Create and use presets de Fusion]: una lista con los preajustes del
comando, «＋» para guardar los valores actuales con un nombre y «⋯» con Guardar, Renombrar, Eliminar y Predeterminado
(Actual, Último usado o Valores de fábrica). La lógica y el archivo están en `nucleo/preajustes.py`.
"""
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QInputDialog, QMenu, QToolButton, QWidget

from ..nucleo import geometria as geo
from ..nucleo import preajustes as pre

FABRICA = "Valores de fábrica"


def tiene_preajustes(panel):
    """Los diálogos de un paso nuevo con algún valor que se pueda guardar (no los que solo miden o eligen)."""
    from .comando import Casilla, Entero, Expresion, Opciones, Texto
    return (not panel.comando.SIN_OP and panel.ctx.op is None
            and any(isinstance(c, (Expresion, Opciones, Casilla, Entero, Texto)) for c in panel.campos))


def valores_guardables(panel):
    """Los valores del panel que van a un preajuste: los de campos simples (no las selecciones de la vista)."""
    from .comando import Casilla, Entero, Expresion, Opciones, Texto
    claves = {c.clave for c in panel.campos if isinstance(c, (Expresion, Opciones, Casilla, Entero, Texto))}
    return {k: v for k, v in panel.valores.items() if k in claves}


def _encaja(campo, v):
    """¿El valor guardado sirve para el campo? Un preajuste escrito a mano o por el MCP puede traer un tipo malo
    ({"rayos": "muchos"} en un entero) y eso dejaría el diálogo sin abrir."""
    from .comando import Casilla, Entero, Opciones
    if isinstance(campo, Casilla):
        return isinstance(v, bool)
    if isinstance(campo, Entero):
        return isinstance(v, int | float) and not isinstance(v, bool) and float(v).is_integer() and campo.minimo <= v <= campo.maximo
    if isinstance(campo, Opciones):
        return isinstance(v, str) and v in campo.opciones
    return isinstance(v, str | int | float) and not isinstance(v, bool)


def _para_campo(campo, v):
    """El valor con el tipo que espera el campo (los enteros guardados como 8.0 pasan a 8)."""
    from .comando import Entero
    return int(v) if isinstance(campo, Entero) else v


def aplicar_valores(panel, valores):
    """Pone en el panel los valores de un preajuste (solo los campos que el diálogo tiene y a los que el valor les sirve)."""
    campos = {c.clave: c for c in panel.campos}
    guardables = valores_guardables(panel)
    for k, v in valores.items():
        if k in campos and k in guardables and _encaja(campos[k], v):
            panel.set_valor(k, _para_campo(campos[k], v))


def valores_iniciales(panel):
    """Valores con que abre el diálogo según su predeterminado (solo campos simples)."""
    if not tiene_preajustes(panel):
        return {}
    try:
        guardables, campos = valores_guardables(panel), {c.clave: c for c in panel.campos}
        return {k: _para_campo(campos[k], v) for k, v in pre.valores_iniciales(panel.comando.CLAVE).items()
                if k in guardables and _encaja(campos[k], v)}
    except (OSError, ValueError):
        return {}


def recordar_ultimo(panel):
    """Al aceptar: si el predeterminado es «último usado», guarda los valores usados."""
    if tiene_preajustes(panel) and pre.listar(panel.comando.CLAVE)["default"] == pre.ULTIMO:
        pre.guardar_ultimo(panel.comando.CLAVE, valores_guardables(panel))


class FilaPreajustes(QWidget):
    def __init__(self, panel):
        super().__init__()
        self.panel, self.clave = panel, panel.comando.CLAVE
        h = QHBoxLayout(self)
        h.setContentsMargins(10, 6, 10, 0)
        h.setSpacing(4)
        self.lista = QComboBox(objectName="preajuste_lista")
        self.lista.setToolTip("Preajustes: valores guardados de este comando.")
        h.addWidget(self.lista, 1)
        self.mas = QToolButton(text="＋", objectName="preajuste_nuevo")
        self.mas.setToolTip("Guardar los valores actuales como preajuste nuevo")
        self.mas.clicked.connect(self.nuevo)
        h.addWidget(self.mas)
        self.menu_boton = QToolButton(text="⋯", objectName="preajuste_menu")
        self.menu_boton.setToolTip("Guardar, renombrar, eliminar o elegir el predeterminado")
        self.menu_boton.setPopupMode(QToolButton.InstantPopup)
        self.menu = QMenu(self.menu_boton)
        self.menu_boton.setMenu(self.menu)
        self.menu.aboutToShow.connect(self._armar_menu)
        h.addWidget(self.menu_boton)
        self.actual = None                          # nombre del preajuste elegido (None = valores de fábrica)
        self.recargar()
        self.lista.activated.connect(self._elegido)

    # ------------------------------------------------------------ datos
    def recargar(self, elegir=None):
        info = pre.listar(self.clave)
        self.lista.blockSignals(True)
        self.lista.clear()
        self.lista.addItem(FABRICA, None)
        for n in info["presets"]:
            self.lista.addItem(n + (" (predeterminado)" if info["default"] == n else ""), n)
        if info["default"] == pre.ULTIMO:
            self.lista.setItemText(0, FABRICA + " · el predeterminado es el último usado")
        self.actual = elegir if elegir in info["presets"] else None
        self.lista.setCurrentIndex(max(self.lista.findData(self.actual), 0))
        self.lista.blockSignals(False)

    def _avisar(self, texto):
        self.panel._mostrar(texto, aviso=True)

    def _elegido(self, _i):
        nombre = self.lista.currentData()
        self.actual = nombre
        if nombre is None:                          # valores de fábrica
            for c in self.panel.campos:
                if c.clave in valores_guardables(self.panel):
                    self.panel.set_valor(c.clave, list(c.defecto) if isinstance(c.defecto, list) else c.defecto)
            return
        try:
            aplicar_valores(self.panel, pre.obtener(self.clave, nombre))
        except geo.ErrorGeometria as e:
            self._avisar(str(e))

    # ------------------------------------------------------------ acciones
    def nuevo(self):
        nombre, ok = QInputDialog.getText(self, "Nuevo preajuste", "Nombre del preajuste:")
        if ok:
            self._guardar(nombre, sobrescribir=False)

    def _guardar(self, nombre, sobrescribir=True):
        try:
            pre.guardar(self.clave, nombre, valores_guardables(self.panel), sobrescribir)
        except geo.ErrorGeometria as e:
            self._avisar(str(e))
            return
        self.recargar(nombre.strip())

    def _renombrar(self):
        nuevo, ok = QInputDialog.getText(self, "Renombrar preajuste", "Nombre nuevo:", text=self.actual)
        if ok:
            try:
                pre.renombrar(self.clave, self.actual, nuevo)
            except geo.ErrorGeometria as e:
                self._avisar(str(e))
                return
            self.recargar(nuevo.strip())

    def _eliminar(self):
        pre.borrar(self.clave, self.actual)
        self.recargar()

    def _predeterminado(self, que):
        try:
            pre.definir_defecto(self.clave, que)
        except geo.ErrorGeometria as e:
            self._avisar(str(e))
            return
        self.recargar(self.actual)

    def _armar_menu(self):
        self.menu.clear()
        con = self.actual is not None
        self.menu.addAction("Guardar", lambda: self._guardar(self.actual)).setEnabled(con)
        self.menu.addAction("Renombrar…", self._renombrar).setEnabled(con)
        self.menu.addAction("Eliminar", self._eliminar).setEnabled(con)
        self.menu.addSeparator()
        sub = self.menu.addMenu("Establecer como predeterminado")
        sub.addAction("Actual", lambda: self._predeterminado(self.actual)).setEnabled(con)
        sub.addAction("Último usado", lambda: self._predeterminado(pre.ULTIMO))
        sub.addAction("Valores de fábrica", lambda: self._predeterminado(pre.FABRICA))

# -*- coding: utf-8 -*-
"""
PREAJUSTES de un diálogo de comando [Create and use presets de Fusion]: un botón «⋯» en la cabecera con un menú (los
preajustes del comando, guardar los valores actuales con un nombre, Guardar, Renombrar, Eliminar y Predeterminado: Actual,
Último usado o Valores de fábrica). La lógica y el archivo están en `nucleo/preajustes.py`.
"""
from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QActionGroup
from PySide6.QtWidgets import QInputDialog, QMenu, QToolButton

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


class BotonPreajustes(QToolButton):
    """Botón «⋯» de la cabecera del diálogo (el «Preset» de Fusion va arriba del diálogo): su menú lista Valores de fábrica
    y los preajustes guardados, y trae Guardar como nuevo, Guardar, Renombrar, Eliminar y Establecer como predeterminado."""

    def __init__(self, panel):
        super().__init__(text="⋯", objectName="preajuste_menu")
        self.panel, self.clave = panel, panel.comando.CLAVE
        self.setPopupMode(QToolButton.InstantPopup)
        self.setFocusPolicy(Qt.StrongFocus)         # alcanzable con Tab (el panel lo deja al final del recorrido) y se abre con Espacio o Enter
        self.menu = QMenu(self)
        self.setMenu(self.menu)
        self.menu.aboutToShow.connect(self._armar_menu)
        self.actual = None                          # nombre del preajuste elegido (None = valores de fábrica)
        self.orden = pre.orden_de(self.clave)       # se recuerda entre diálogos, por comando
        self.recargar()

    def event(self, e):
        if e.type() == QEvent.ShortcutOverride and e.key() in (Qt.Key_Space, Qt.Key_Return, Qt.Key_Enter):
            e.accept()                              # Espacio es un atajo de la ventana (Boceto sobre la cara): con el foco acá abre el menú
            return True
        return super().event(e)

    # ------------------------------------------------------------ datos
    def recargar(self, elegir=None):
        self.actual = elegir if elegir in pre.listar(self.clave)["presets"] else None
        self.setToolTip(f"Preajustes: {self.actual or FABRICA}. Aplicar, guardar los valores actuales, renombrar, "
                        "eliminar o elegir el predeterminado")

    def _avisar(self, texto):
        self.panel._mostrar(texto, aviso=True)

    def _elegir(self, nombre):
        self.recargar(nombre)
        if nombre is None:                        # valores de fábrica
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
        info = pre.listar(self.clave)
        nombres = pre.ordenar_presets(self.clave, self.orden)
        grupo = QActionGroup(self.menu)
        fabrica = FABRICA + (" · el predeterminado es el último usado" if info["default"] == pre.ULTIMO else "")
        opciones = [(fabrica, None)] + [(n + (" (predeterminado)" if info["default"] == n else ""), n)
                                        for n in nombres]
        for texto, nombre in opciones:
            a = grupo.addAction(self.menu.addAction(texto, lambda n=nombre: self._elegir(n)))
            a.setCheckable(True)
            a.setChecked(nombre == self.actual)
        self.menu.addSeparator()
        self.menu.addAction("Restablecer", lambda: self._elegir(self.actual))
        con = self.actual is not None
        self.menu.addAction("Guardar los valores actuales como nuevo…", self.nuevo)
        self.menu.addAction("Guardar", lambda: self._guardar(self.actual)).setEnabled(con)
        self.menu.addAction("Renombrar…", self._renombrar).setEnabled(con)
        self.menu.addAction("Eliminar", self._eliminar).setEnabled(con)
        self.menu.addSeparator()
        sub = self.menu.addMenu("Establecer como predeterminado")
        sub.addAction("Actual", lambda: self._predeterminado(self.actual)).setEnabled(con)
        sub.addAction("Último usado", lambda: self._predeterminado(pre.ULTIMO))
        sub.addAction("Valores de fábrica", lambda: self._predeterminado(pre.FABRICA))
        sub = self.menu.addMenu("Ordenar por")
        grupo_orden = QActionGroup(sub)
        for texto, por in (("Última creación", "creacion"), ("Nombre", "nombre"),
                           ("Última modificación", "modificacion"), ("Último uso", "uso")):
            a = grupo_orden.addAction(sub.addAction(texto, lambda p=por: self._ordenar(p)))
            a.setCheckable(True)
            a.setChecked(por == self.orden)

    def _ordenar(self, por):
        pre.guardar_orden(self.clave, por)          # se recuerda entre diálogos, por comando
        self.orden = por

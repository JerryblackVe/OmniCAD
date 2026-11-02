# -*- coding: utf-8 -*-
"""Campo donde se escribe una expresión (PAR-9): sugiere parámetros mientras se teclea y alterna expresión y valor."""
import re

from PySide6.QtCore import QStringListModel, Qt
from PySide6.QtWidgets import QCompleter, QLineEdit

from ..timeline.parametros import ErrorExpresion
from . import formato
from .iconos import icono

_PALABRA = re.compile(r'[^\W\d][\w$"°µ]*$')


def nombres_sugeridos(tabla):
    """Lo que se ofrece al teclear: los favoritos primero, después los de usuario; un dN sin estrella no."""
    return [p.nombre for p in sorted(tabla, key=lambda p: not p.favorito)
            if p.favorito or not (p.op or re.fullmatch(r"d\d+", p.nombre))]


def autocompletar(campo, nombres):
    """Lista de `nombres()` debajo de `campo` para la palabra que se está escribiendo. Después de un número es una
    unidad, no un parámetro: no se ofrece nada."""
    modelo = QStringListModel(campo)
    lista = QCompleter(modelo, campo)
    lista.setCaseSensitivity(Qt.CaseInsensitive)
    lista.setWidget(campo)

    def palabra():
        return _PALABRA.search(QLineEdit.text(campo)[:campo.cursorPosition()])

    def tecleado(_texto):
        m = palabra()
        vale = m is not None and not re.search(r"[\d.]\s*$", QLineEdit.text(campo)[:m.start()])
        modelo.setStringList(nombres() if vale else [])
        lista.setCompletionPrefix(m.group() if vale else "")
        lista.complete()                # sin coincidencias cierra la lista, y no la crea si nunca se abrió

    def elegido(nombre):
        m = palabra()
        if m is not None:
            campo.setSelection(m.start(), m.end() - m.start())
            campo.insert(nombre)

    campo.textEdited.connect(tecleado)
    lista.activated[str].connect(elegido)
    return lista


class CampoExpresion(QLineEdit):
    """Con el ícono fx apretado se ve el valor, y `text()` sigue dando la expresión: nada se reescribe."""

    def __init__(self, texto, ctx, tipo):
        super().__init__(texto)
        self.ctx, self.tipo = ctx, tipo
        self._expresion = None
        self.accion_fx = self.addAction(icono("parametros"), QLineEdit.ActionPosition.TrailingPosition)
        self.accion_fx.setCheckable(True)
        self.accion_fx.setToolTip("Alternar entre la expresión y su valor")
        self.accion_fx.toggled.connect(self._alternar)
        self.lista = autocompletar(self, lambda: nombres_sugeridos(ctx.parametros))

    def text(self):
        return super().text() if self._expresion is None else self._expresion

    def setText(self, texto):
        self.accion_fx.setChecked(False)
        super().setText(texto)

    def _alternar(self, ver_valor):
        self.blockSignals(True)             # lo que se muestra no es lo que el comando guarda
        try:
            if not ver_valor:
                if self._expresion is not None:
                    super().setText(self._expresion)
                self._expresion = None
            else:
                valor = self.ctx.evaluar(super().text(), self.tipo)
                self._expresion = super().text()
                super().setText(formato.tooltip_valor(valor, self.tipo == "angulo", self.tipo == "escalar").removeprefix("= "))
        except ErrorExpresion:              # una expresión a medias no tiene valor que mostrar
            self.accion_fx.setChecked(False)
        finally:
            self.setReadOnly(self._expresion is not None)
            self.blockSignals(False)

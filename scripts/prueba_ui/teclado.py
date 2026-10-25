# -*- coding: utf-8 -*-
"""Escribir en los campos del panel como una persona: clic, borrar todo, teclear tecla por tecla, pegar."""
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication


def teclear(panel, clave, texto, accion=None):
    """Clic en el campo, Ctrl+A, y escribe `texto` con las teclas (vacío: Supr). `accion`: tecla final opcional
    (Qt.Key_Return, Qt.Key_Tab, Qt.Key_Escape). Devuelve el widget del campo."""
    w = panel.widgets[clave]
    QTest.mouseClick(w, Qt.LeftButton)
    QTest.keyClick(w, Qt.Key_A, Qt.ControlModifier)
    if texto == "":
        QTest.keyClick(w, Qt.Key_Delete)
    else:
        QTest.keyClicks(w, texto)
    if accion is not None:
        QTest.keyClick(w, accion)
    QTest.qWait(60)
    return w


def pegar(panel, clave, texto):
    """Pega `texto` con Ctrl+V en el campo (pasa por el portapapeles)."""
    QApplication.clipboard().setText(texto)
    w = panel.widgets[clave]
    QTest.mouseClick(w, Qt.LeftButton)
    QTest.keyClick(w, Qt.Key_A, Qt.ControlModifier)
    QTest.keyClick(w, Qt.Key_V, Qt.ControlModifier)
    QTest.qWait(60)
    return w

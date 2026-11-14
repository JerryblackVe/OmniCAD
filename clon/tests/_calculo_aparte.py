# -*- coding: utf-8 -*-
"""FL-3b: Aceptar, editar, deshacer y rehacer con el cálculo en el proceso aparte siguen en otro hilo, con una barra modal
«Calculando en un proceso aparte…»; la ventana aplica el resultado al cerrarla."""
import time

from PySide6.QtTest import QTest
from PySide6.QtWidgets import QProgressDialog


def barra(ventana):
    """La barra abierta del cálculo aparte, o None."""
    return next((d for d in ventana.findChildren(QProgressDialog) if d.isVisible()), None)


def esperar_barra(ventana, segundos=60):
    """Espera a que la barra se cierre (el cambio quedó aplicado, cancelado o con su aviso)."""
    fin = time.monotonic() + segundos
    while barra(ventana) is not None and time.monotonic() < fin:
        QTest.qWait(20)
    assert barra(ventana) is None, f"la barra del cálculo aparte siguió abierta {segundos} s"

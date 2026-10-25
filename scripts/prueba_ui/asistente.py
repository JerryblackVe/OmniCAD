# -*- coding: utf-8 -*-
"""Asistente IA como una persona: clic real en el botón de la barra, teclear en el campo (texto, vacío, enorme, pegar),
Enter, Mayús+Enter, Esc, Tab, Cancelar, cambiar de modo, biblioteca de prompts, chat nuevo y ventana chica (el campo y
Enviar tienen que entrar). El proveedor es el falso: sin red ni gasto."""
import sys
import threading

import arnes as A
import escena
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QToolButton

from omnicad.asistente.proveedores.base import PedidoHerramienta, ProveedorFalso, Respuesta

s, ids = escena.construir()
app, v = A.iniciar(s.doc)
AR = "ASISTENTE"
CAJA = PedidoHerramienta("h1", "create_box", {"length": 30, "width": 20, "height": 10})


def esperar(p, ms=8000):
    for _ in range(ms // 20):
        if not p.trabajando:
            return True
        QTest.qWait(20)
    return False


def lineas(p):
    return [b.text() for b in p.lista.findChildren(QToolButton, "herramienta_asistente")]


def escribir(p, texto, tecla=None, mod=Qt.NoModifier):
    QTest.mouseClick(p.campo.viewport(), Qt.LeftButton)
    QTest.keyClick(p.campo, Qt.Key_A, Qt.ControlModifier)
    QTest.keyClick(p.campo, Qt.Key_Delete)
    if texto:
        QTest.keyClicks(p.campo, texto)
    if tecla is not None:
        QTest.keyClick(p.campo, tecla, mod)
    QTest.qWait(60)


def dentro(w, ventana):
    """El widget entero se ve dentro de la ventana (no quedó cortado ni afuera)."""
    caja = w.rect().translated(w.mapTo(ventana, w.rect().topLeft()))
    return w.isVisible() and ventana.rect().contains(caja)


def pedido():
    # ---------------------------------------------------------------- botón de la barra de la aplicación
    boton = next(b for b in v.findChildren(QToolButton) if b.defaultAction() is v.acciones["asistente"])
    QTest.mouseClick(boton, Qt.LeftButton)
    A.esperar(200)
    p = v.asistente
    A.reg(AR, "clic en el botón Asistente abre el panel", p is not None and p.isVisible() and boton.isVisible())
    A.reg(AR, "el foco queda en el campo", QApplication.focusWidget() is p.campo, f"foco={QApplication.focusWidget()}")
    A.reg(AR, "cabecera con proveedor y modelo", "·" in p.etiqueta_modelo.text(), p.etiqueta_modelo.text())
    A.foto(v, "asistente_abierto")
    p.guion = []
    p.crear_proveedor = lambda _cfg: ProveedorFalso(p.guion)

    # ---------------------------------------------------------------- vacío, espacios, Mayús+Enter, Enter
    n = len(v.doc.operaciones)
    for texto in ("", "    "):
        escribir(p, texto, Qt.Key_Return)
        A.reg(AR, f"Enter con el campo «{texto}» no manda nada", not p.trabajando and p.mensajes == [])
    QTest.mouseClick(p.b_enviar, Qt.LeftButton)
    A.reg(AR, "clic en Enviar con el campo vacío no manda nada", not p.trabajando and p.mensajes == [])
    escribir(p, "linea uno", Qt.Key_Return, Qt.ShiftModifier)
    QTest.keyClicks(p.campo, "linea dos")
    A.reg(AR, "Mayús+Enter salta de línea sin mandar", p.campo.toPlainText() == "linea uno\nlinea dos" and not p.trabajando,
          repr(p.campo.toPlainText()))
    # ---------------------------------------------------------------- modo Hacer: crea la caja
    p.modo.setCurrentIndex(p.modo.findData("hacer"))
    p.guion = [Respuesta(herramientas=[CAJA], uso={"entrada": 120, "salida": 30, "costo_usd": 0.0012}),
               Respuesta(texto="Listo: **caja** de 30 x 20 x 10 mm.")]
    QTest.keyClick(p.campo, Qt.Key_Return)
    trabajando = p.trabajando and p.b_enviar.text() == "Cancelar" and not p.modo.isEnabled()
    esperar(p)
    A.reg(AR, "Enter manda: mientras trabaja Enviar dice Cancelar y el modo se bloquea", trabajando)
    A.reg(AR, "modo Hacer: la caja aparece en la ventana y la línea de la herramienta",
          len(v.doc.operaciones) == n + 1 and lineas(p)[-1:] == [f"✓ create_box → {v.doc.operaciones[-1].id}"],
          f"pasos={len(v.doc.operaciones) - n} lineas={lineas(p)}")
    A.reg(AR, "pie con tokens y USD", "120 tokens de entrada" in p.pie.text() and "0,0012 USD" in p.pie.text(),
          p.pie.text())
    linea = p.lista.findChildren(QToolButton, "herramienta_asistente")[-1]
    QTest.mouseClick(linea, Qt.LeftButton)
    A.esperar(80)
    detalle = linea.parentWidget().findChildren(type(p.pie))[0]
    A.reg(AR, "clic en la línea de la herramienta despliega el detalle", detalle.isVisible() and "length" in detalle.text(),
          detalle.text()[:80])
    A.foto(v, "asistente_caja")
    A.deshacer(v)
    A.reg(AR, "deshacer de la ventana saca la caja del asistente", len(v.doc.operaciones) == n)

    # ---------------------------------------------------------------- modo Explicar: no cambia nada
    p.modo.setCurrentIndex(p.modo.findData("explicar"))
    p.guion = [Respuesta(herramientas=[CAJA]), Respuesta(texto="Se hace con CREAR › Caja.")]
    escribir(p, "como hago una caja", Qt.Key_Return)
    esperar(p)
    A.reg(AR, "modo Explicar no cambia el documento", len(v.doc.operaciones) == n and lineas(p)[-1] ==
          "✗ create_box: TOOL_NOT_AVAILABLE", lineas(p)[-1])

    # ---------------------------------------------------------------- Cancelar (botón) y Esc
    for como in ("botón Cancelar", "Esc"):
        suelta = threading.Event()

        class Lento(ProveedorFalso):
            def responder(self, *a, suelta=suelta):
                suelta.wait(5)
                return super().responder(*a)

        p.crear_proveedor = lambda _cfg: Lento([Respuesta(herramientas=[CAJA])])
        p.modo.setCurrentIndex(p.modo.findData("hacer"))
        escribir(p, "caja lenta", Qt.Key_Return)
        if como == "Esc":
            QTest.keyClick(p.campo, Qt.Key_Escape)
        else:
            QTest.mouseClick(p.b_enviar, Qt.LeftButton)
        cancelando = p.b_enviar.text() == "Cancelando…"
        suelta.set()
        esperar(p)
        A.reg(AR, f"{como} corta el pedido: no se crea nada", cancelando and len(v.doc.operaciones) == n
              and lineas(p)[-1] == "✗ create_box: CANCELLED" and p.b_enviar.text() == "Enviar", lineas(p)[-1])
    p.crear_proveedor = lambda _cfg: ProveedorFalso(p.guion)
    QTest.keyClick(p.campo, Qt.Key_Escape)
    A.reg(AR, "Esc sin pedido en curso devuelve el foco al visor", QApplication.focusWidget() is v.visor
          and p.isVisible(), f"foco={QApplication.focusWidget()}")

    # ---------------------------------------------------------------- Tab, texto enorme, pegar
    QTest.mouseClick(p.campo.viewport(), Qt.LeftButton)
    QTest.keyClick(p.campo, Qt.Key_Tab)
    A.reg(AR, "Tab pasa del campo al siguiente control (no escribe un tabulador)",
          QApplication.focusWidget() is not p.campo and "\t" not in p.campo.toPlainText(), f"foco={QApplication.focusWidget()}")
    mensajes = len(p.mensajes)
    QApplication.clipboard().setText("x" * 25000)
    QTest.mouseClick(p.campo.viewport(), Qt.LeftButton)
    QTest.keyClick(p.campo, Qt.Key_A, Qt.ControlModifier)
    QTest.keyClick(p.campo, Qt.Key_V, Qt.ControlModifier)
    pegado = len(p.campo.toPlainText())
    QTest.keyClick(p.campo, Qt.Key_Return)
    aviso = [w.text() for w in p.lista.findChildren(type(p.pie))][-1]
    A.reg(AR, "pegar un texto enorme (25000) y Enter: no se manda y avisa", pegado == 25000 and not p.trabajando
          and len(p.mensajes) == mensajes and "muy largo" in aviso, aviso)
    QApplication.clipboard().setText("  hola desde el portapapeles  ")
    QTest.keyClick(p.campo, Qt.Key_A, Qt.ControlModifier)
    QTest.keyClick(p.campo, Qt.Key_V, Qt.ControlModifier)
    p.guion = [Respuesta(texto="Hola.")]
    QTest.keyClick(p.campo, Qt.Key_Return)
    esperar(p)
    A.reg(AR, "pegar y Enter manda el texto sin los espacios de los bordes",
          p.mensajes[-2]["contenido"][-1]["texto"] == "hola desde el portapapeles", p.mensajes[-2]["contenido"][-1])

    # ---------------------------------------------------------------- biblioteca de prompts y chat nuevo
    menu = p.b_chat.menu()
    biblioteca = next(a.menu() for a in menu.actions() if a.text() == "Biblioteca de prompts")
    item = biblioteca.actions()[0].menu().actions()[0]
    item.trigger()
    A.reg(AR, "Biblioteca de prompts deja el ejemplo en el campo sin mandarlo", bool(p.campo.toPlainText())
          and not p.trabajando, p.campo.toPlainText()[:60])
    historial = next(a for a in menu.actions() if a.text() == "Historial de chats")
    A.reg(AR, "Historial de chats grisado (llega con IA-7)", not historial.isEnabled())
    QTest.mouseClick(p.b_nuevo, Qt.LeftButton)
    A.esperar(50)                              # los mensajes viejos se borran con deleteLater
    A.reg(AR, "+ empieza un chat nuevo", p.mensajes == [] and lineas(p) == [] and p.pie.text() == "")
    A.reg(AR, "la estrella avisa que es IA", "puede equivocarse" in p.b_aviso.toolTip())

    # ---------------------------------------------------------------- ventana chica
    for ancho, alto in ((1024, 640), (800, 520)):
        p.hide()
        A.esperar(150)
        v.resize(ancho, alto)
        A.esperar(300)
        sin_panel = v.width()                  # la ventana no baja de 821 de ancho ni sin el panel (B-105)
        p.show()
        v.resize(ancho, alto)
        A.esperar(300)
        ok = dentro(p.campo, v) and dentro(p.b_enviar, v) and dentro(p.modo, v)
        A.reg(AR, f"ventana {ancho}x{alto}: el campo, el modo y Enviar entran", ok,
              f"ventana={v.width()}x{v.height()} panel={p.width()}x{p.height()}")
        if ancho >= sin_panel:
            A.reg(AR, f"ventana {ancho}x{alto}: el panel no agranda la ventana", v.width() == ancho,
                  f"con panel {v.width()} px")
        else:
            print(f"NOTA ventana {ancho}x{alto}: ni sin el panel baja de {sin_panel} px (B-105); con el panel mide "
                  f"{v.width()} px", flush=True)
        A.foto(v, f"asistente_{ancho}x{alto}")
    v.resize(1900, 1000)
    A.esperar(200)

    # ---------------------------------------------------------------- atajo y cerrar
    QTest.keyClick(v, Qt.Key_A, Qt.ControlModifier | Qt.ShiftModifier)
    A.esperar(100)
    A.reg(AR, "Ctrl+Mayús+A cierra el panel", not p.isVisible() and not v.acciones["asistente"].isChecked())
    QTest.keyClick(v, Qt.Key_A, Qt.ControlModifier | Qt.ShiftModifier)
    A.esperar(100)
    A.reg(AR, "Ctrl+Mayús+A lo vuelve a abrir", p.isVisible())


n_err = len(A.ERRORES)
A.correr(AR, pedido)
A.reg(AR, "ninguna excepción escapada en slots de Qt", len(A.ERRORES) == n_err, "\n".join(A.ERRORES[n_err:])[-600:])
A.guardar_registro("asistente")
fallas = [r for r in A.REGISTRO if not r["ok"]]
print(f"\n=== {len(A.REGISTRO)} comprobaciones, {len(fallas)} con ✗ ===")
v.doc.modificado = False
v.close()
sys.exit(0)

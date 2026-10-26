# -*- coding: utf-8 -*-
"""Botón grande del Asistente IA en la CINTA (a la derecha del grupo SELECCIONAR) como lo usa una persona: está en todas las
pestañas, alineado con los demás botones grandes y con su texto «Asistente IA» debajo (solo ícono si la ventana es angosta);
clic real que abre y cierra el dock y deja el botón marcado, Ctrl+Mayús+A, ventana de 1900×1000, 1024×640 y 800×520, tema
oscuro y claro, y el cambio de tema EN VIVO con el panel abierto. No hay barra a la derecha: el visor ocupa todo el ancho.
Deja una captura de la ventana y de la cinta de cada caso."""
import sys

import arnes as A
import escena
from omnicad.ui import cinta as ci
from omnicad.ui import temas
from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QToolBar, QToolButton, QWidget

AR = "BOTÓN ASISTENTE"
TAMANOS = [(1900, 1000), (1024, 640), (800, 520)]
TEMAS = ["oscuro_moderno", "claro_moderno"]

s, _ids = escena.construir()
app, v = A.iniciar(s.doc)
c = v.cinta
accion = v.acciones["asistente"]


def atajo():
    """Ctrl+Mayús+A como lo teclea una persona; el atajo necesita que la ventana tenga el foco."""
    v.activateWindow()
    v.raise_()
    A.esperar(100)
    QTest.keyClick(v, Qt.Key_A, Qt.ControlModifier | Qt.ShiftModifier)


def dentro(w, ventana):
    """El widget entero se ve dentro de la ventana (no quedó cortado ni afuera)."""
    caja = w.rect().translated(w.mapTo(ventana, w.rect().topLeft()))
    return w.isVisible() and ventana.rect().contains(caja)


def izquierda(w):
    return w.mapTo(v, QPoint(0, 0)).x()


def derecha(w):
    return w.mapTo(v, QPoint(w.width(), 0)).x()


def arriba(w):
    return w.mapTo(v, QPoint(0, 0)).y()


def boton():
    """El botón del Asistente de la pestaña que se ve (cada pestaña tiene el suyo)."""
    return [b for b in c.pila.currentWidget().findChildren(QToolButton, "boton_cinta")
            if b.defaultAction() is accion and b.isVisible()]


def vecino(ref):
    """Un botón grande de SELECCIONAR (el grupo de al lado); en la pestaña sin ese grupo, el último que no es del Asistente."""
    if ref:
        return ref[0].parentWidget().findChildren(QToolButton, "boton_cinta")[0]
    return [b for b in c.pila.currentWidget().findChildren(QToolButton, "boton_cinta")
            if b.defaultAction() is not accion and b.isVisible()][-1]


def icono_pintado(b):
    img = b.icon().pixmap(28, 28).toImage()
    return sum(img.pixelColor(x, y).alpha() > 0 for x in range(28) for y in range(28))


def fondo_cinta():
    return c.grab().toImage().pixelColor(c.width() - 5, 5)


def prueba():
    barra_app = v.findChild(QWidget, "barra_app")
    A.reg(AR, "no hay barra a la derecha ni botón chico arriba: el visor ocupa todo el ancho",
          not v.findChildren(QToolBar) and derecha(v.area) >= v.width() - 1
          and not [b for b in barra_app.findChildren(QToolButton) if b.defaultAction() is accion],
          f"visor hasta x={derecha(v.area)} de {v.width()}")
    A.reg(AR, "el tooltip dice el atajo", "Mayúsculas+A" in accion.toolTip(), accion.toolTip()[:100])
    # ---- el botón está en TODAS las pestañas, a la derecha de SELECCIONAR (o al final si no la tiene), alineado y del mismo tamaño
    for i in range(c.pila.count()):
        c.pila.setCurrentIndex(i)
        A.esperar(150)
        nombre, grupos = (ci.PESTANAS + ci.CONTEXTUALES)[i]
        bs = boton()
        ref = [b for b in c.pila.currentWidget().findChildren(QToolButton, "titulo_grupo") if b.text().startswith("SELECCIONAR")]
        otro = vecino(ref)
        ok_lugar = len(bs) == 1 and (not ref or izquierda(bs[0]) > derecha(ref[0]) - 1)
        A.reg(AR, f"pestaña {nombre}: un solo botón del Asistente, " + ("a la derecha de SELECCIONAR" if ref else "al final (sin SELECCIONAR)"),
              ok_lugar, f"botones={len(bs)} grupos={[g[0] for g in grupos]}")
        if len(bs) == 1:
            b = bs[0]
            A.reg(AR, f"pestaña {nombre}: mismo tamaño de ícono, misma altura y misma fila que los demás botones grandes",
                  b.iconSize() == otro.iconSize() and b.height() == otro.height() and abs(arriba(b) - arriba(otro)) <= 1,
                  f"él={b.size()} y {arriba(b)}, otro={otro.size()} y {arriba(otro)}")
            A.reg(AR, f"pestaña {nombre}: entra entero en la ventana", dentro(b, v), f"{derecha(b)} de {v.width()}")
        A.foto(v, f"asistente_cinta_{nombre}")
    c.pila.setCurrentIndex(0)
    for tema in TEMAS:
        v.aplicar_tema(tema)
        for ancho, alto in TAMANOS:
            if v.asistente is not None and v.asistente.isVisible():       # Qt no achica la ventana al cerrar el dock
                v.mostrar_asistente(False)
                A.esperar(150)
            v.resize(ancho, alto)
            A.esperar(500)
            caso = f"{ancho}x{alto} {tema}"
            nom = caso.replace(" ", "_")
            b = boton()[0]
            angosta = b.toolButtonStyle() == Qt.ToolButtonIconOnly
            A.reg(AR, f"{caso}: el botón se ve entero y no tapa el visor ni el ViewCube ({'solo ícono' if angosta else 'con texto'})",
                  dentro(b, v) and dentro(v.area.viewcube, v) and derecha(v.area) >= v.width() - 1,
                  f"ventana={v.width()}x{v.height()} botón={b.geometry()} texto={b.text()!r}")
            A.reg(AR, f"{caso}: con lugar lleva «Asistente IA» debajo del ícono; angosta, solo el ícono",
                  (b.toolButtonStyle() == Qt.ToolButtonTextUnderIcon and "Asistente" in b.text())
                  if not angosta else b.width() == ci.ANCHO_SOLO_ICONO, f"estilo={b.toolButtonStyle()}")
            A.reg(AR, f"{caso}: el ícono del robot se dibuja", icono_pintado(b) > 150, f"píxeles opacos: {icono_pintado(b)}")
            A.foto(v, f"asistente_{nom}_cerrado")
            c.grab().save(str(A.CAPTURAS / f"asistente_{nom}_cinta.png"))
            QTest.mouseClick(b, Qt.LeftButton)                          # clic real: abre el dock
            A.esperar(300)
            p = v.asistente
            A.reg(AR, f"{caso}: clic abre el panel y el botón queda marcado",
                  p is not None and p.isVisible() and b.isChecked() and accion.isChecked())
            A.reg(AR, f"{caso}: con el panel abierto el botón sigue entero y el campo y Enviar entran",
                  dentro(boton()[0], v) and dentro(p.campo, v) and dentro(p.b_enviar, v),
                  f"ventana={v.width()}x{v.height()} panel={p.geometry()}")
            A.foto(v, f"asistente_{nom}_abierto")
            b = boton()[0]
            QTest.mouseClick(b, Qt.LeftButton)                          # el mismo botón cierra
            A.esperar(250)
            A.reg(AR, f"{caso}: otro clic cierra el panel y el botón se desmarca",
                  not p.isVisible() and not b.isChecked() and not accion.isChecked())
            atajo()
            A.esperar(250)
            A.reg(AR, f"{caso}: Ctrl+Mayús+A abre y el botón se marca", p.isVisible() and b.isChecked(),
                  f"ventana activa={v.isActiveWindow()}")
            atajo()
            A.esperar(250)
            A.reg(AR, f"{caso}: Ctrl+Mayús+A cierra y el botón se desmarca", not p.isVisible() and not b.isChecked(),
                  f"ventana activa={v.isActiveWindow()}")
            if v.width() != ancho:       # el panel abierto agranda la ventana hasta su mínimo
                print(f"NOTA {caso}: con el panel abierto la ventana mide {v.width()} px", flush=True)
    # ---- cambio de tema en vivo con el panel abierto
    v.resize(1900, 1000)
    v.aplicar_tema("claro_moderno")
    v.mostrar_asistente(True)
    A.esperar(400)
    claro = fondo_cinta()
    v.aplicar_tema("oscuro_moderno")                                  # con la ventana abierta: es el cambio «en vivo»
    A.esperar(500)
    A.foto(v, "asistente_cinta_en_vivo_oscuro")
    b = boton()[0]
    A.reg(AR, "cambiar de tema en vivo repinta la cinta y el botón sigue marcado con su ícono",
          fondo_cinta() != claro and fondo_cinta().name() == temas.activo()["fondo"] and b.isChecked()
          and icono_pintado(b) > 150, f"{fondo_cinta().name()} vs {temas.activo()['fondo']}")
    v.aplicar_tema("claro_moderno")
    A.esperar(500)
    A.reg(AR, "al volver al claro la cinta queda como antes", fondo_cinta() == claro)
    v.mostrar_asistente(False)


n_err = len(A.ERRORES)
A.correr(AR, prueba)
A.reg(AR, "ninguna excepción escapada en slots de Qt", len(A.ERRORES) == n_err, "\n".join(A.ERRORES[n_err:])[-600:])
A.guardar_registro("boton_asistente")
fallas = [r for r in A.REGISTRO if not r["ok"]]
print(f"\n=== {len(A.REGISTRO)} comprobaciones, {len(fallas)} con ✗ ===")
v.doc.modificado = False
v.close()
sys.exit(0)

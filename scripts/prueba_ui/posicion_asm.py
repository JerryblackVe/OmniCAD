# -*- coding: utf-8 -*-
"""ENSAMBLAR › Posición (ASM-15) en la ventana real y como una persona: agarrar un componente en el visor y arrastrarlo,
libre o siguiendo su unión; soltar, Esc y clic derecho a mitad de camino; Ctrl+Z; la barra «Posición» (Capturar, Revertir);
la pregunta antes de un comando; clic y ventana de selección sin cambios; ventana chica; y una pieza de dos componentes con
una unión: girar, mover, capturar, cambiar una cota, deshacer."""
import sys

import arnes as A
import numpy as np
from omnicad import api
from omnicad.timeline.posicion import pendiente_de
from PySide6.QtCore import QEvent, QPointF, Qt, QTimer
from PySide6.QtGui import QMouseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox

AR = "POSICIÓN ASM"
s = api.Sesion()


def L(nombre, **a):
    r = api.llamar(s, nombre, a)
    assert r["ok"], (nombre, a, r)
    return r["result"]


L("create_parameter", name="largo", expression="120 mm")
base = L("create_box", name="Base", length=200, width=200, height=10)["bodies_created"][0]["id"]
brazo = L("create_box", name="Brazo", length="largo", width=12, height=12, x=300)["bodies_created"][0]["id"]
carro = L("create_box", name="Carro", length=30, width=30, height=30, y=70, z=10)["bodies_created"][0]["id"]
bloque = L("create_box", name="Bloque", length=30, width=30, height=30, x=-250)["bodies_created"][0]["id"]
L("create_component", bodies=[base], name="CBase", grounded=True)
L("create_component", bodies=[brazo], name="CBrazo")
L("create_component", bodies=[carro], name="CCarro")
L("create_component", bodies=[bloque], name="CBloque")
L("create_joint", origin1="<Z", body1=brazo, origin2=">Z", body2=base, joint_type="revolute", name="Giro")
L("create_as_built_joint", origin="<Z", body=carro, component2="CBase", joint_type="slider", slide_axis="X", minimum=-60,
  maximum=60, name="Carril")
exec_real = QDialog.exec                 # el arnés anula los diálogos modales: esta pregunta se contesta con clics
app, v = A.iniciar(s.doc)
QMessageBox.exec = exec_real
vis = v.visor


def evento(tipo, q, boton, botones):
    QApplication.sendEvent(vis, QMouseEvent(tipo, q, vis.mapToGlobal(q), boton, botones, Qt.NoModifier))


def pantalla(p):
    return vis.proyectar(np.array(p, float))


def presionar(a):
    evento(QEvent.MouseMove, a, Qt.NoButton, Qt.NoButton)
    evento(QEvent.MouseButtonPress, a, Qt.LeftButton, Qt.LeftButton)


def llevar(a, b, pasos=10):
    for i in range(1, pasos + 1):
        evento(QEvent.MouseMove, a + (b - a) * (i / pasos), Qt.NoButton, Qt.LeftButton)
        QTest.qWait(10)


def soltar(b):
    evento(QEvent.MouseButtonRelease, b, Qt.LeftButton, Qt.NoButton)
    A.esperar(60)


def arrastrar(a, b, pasos=10):
    presionar(a)
    llevar(a, b, pasos)
    soltar(b)


def pend():
    return pendiente_de(v.doc)


def visto(cuerpo, p):
    """Dónde se dibuja el punto `p` del cuerpo (mundo del modelo) con lo que está sin capturar."""
    t = vis.transformaciones.get(cuerpo, np.identity(4))
    return (np.asarray(t, float) @ np.r_[p, 1.0])[:3]


def cerca(q1, q2, tol=3.0):
    return abs(q1.x() - q2.x()) + abs(q1.y() - q2.y()) <= tol


def responder(texto):
    """Cuando salga la pregunta, aprieta el botón `texto` como una persona."""
    def clic():
        caja = QApplication.activeModalWidget()
        for b in caja.buttons():
            if b.text() == texto:
                QTest.mouseClick(b, Qt.LeftButton)
                return
        caja.reject()
    QTimer.singleShot(250, clic)


def run(nombre, f):
    A.correr(f"{AR} · {nombre}", f)


# 1. Sin unión: libre --------------------------------------------------------------------------------------------------
PB = np.array([-250.0, 0.0, 30.0])              # el centro de la cara de arriba del bloque


def libre():
    pasos = A.n_ops(v)
    a = pantalla(PB)
    b = a + QPointF(160, 40)
    arrastrar(a, b)
    A.reg(AR, "sin unión: el bloque sigue al cursor", cerca(pantalla(visto(bloque, PB)), b), f"{pantalla(visto(bloque, PB))} ↔ {b}")
    A.reg(AR, "el timeline no cambió y la barra Posición aparece", A.n_ops(v) == pasos and v.arrastre.barra.isVisible(), "")
    A.reg(AR, "Capturar y Revertir de la barra se ven", v.arrastre.barra.capturar.isVisible() and v.arrastre.barra.revertir.isVisible(), "")
    A.esperar(120)
    A.reg(AR, "no queda el resaltado en la posición vieja", vis._hover_ent is None, "")
    A.foto(v, "posicion_asm_sin_capturar")
    v._seleccionar([])
    evento(QEvent.MouseMove, pantalla(PB), Qt.NoButton, Qt.NoButton)
    QTest.mouseClick(vis, Qt.LeftButton, Qt.NoModifier, pantalla(PB).toPoint())
    A.esperar(80)
    A.reg(AR, "sin capturar, ni el resaltado ni el clic eligen el fantasma de la posición vieja",
          vis._hover_ent is None and not v.seleccion, f"{len(v.seleccion)}")
    # otro arrastre, agarrándolo donde se ve ahora
    a2 = pantalla(visto(bloque, PB))
    arrastrar(a2, a2 + QPointF(0, 60))
    A.reg(AR, "se puede volver a agarrar donde quedó dibujado", cerca(pantalla(visto(bloque, PB)), a2 + QPointF(0, 60)), "")
    A.reg(AR, "dos arrastres son dos pasos de deshacer", len(pend().historia) == 2, f"{len(pend().historia)}")
    QTest.keyClick(vis, Qt.Key_Z, Qt.ControlModifier)
    A.esperar(100)
    A.reg(AR, "Ctrl+Z deshace el último arrastre", cerca(pantalla(visto(bloque, PB)), b) and pend() is not None, "")
    v.acciones["deshacer"].trigger()
    A.esperar(100)
    A.reg(AR, "deshacer el primero: nada sin capturar, la barra se va", pend() is None and not v.arrastre.barra.isVisible()
          and bloque not in vis.transformaciones, "")


run("libre", libre)


# 2. Cancelar a mitad de camino ------------------------------------------------------------------------------------------
def cancelar():
    a = pantalla(PB)
    presionar(a)
    llevar(a, a + QPointF(100, 0))
    QTest.keyClick(vis, Qt.Key_Escape)
    A.esperar(50)
    A.reg(AR, "Esc durante el arrastre: vuelve a donde estaba", pend() is None and bloque not in vis.transformaciones, "")
    llevar(a + QPointF(100, 0), a + QPointF(160, 0))
    soltar(a + QPointF(160, 0))
    A.reg(AR, "seguir moviendo y soltar después de Esc no hace nada", pend() is None and not vis._arrastrando, "")
    presionar(a)
    llevar(a, a + QPointF(100, 0))
    evento(QEvent.MouseButtonPress, a + QPointF(100, 0), Qt.RightButton, Qt.LeftButton | Qt.RightButton)
    evento(QEvent.MouseButtonRelease, a + QPointF(100, 0), Qt.RightButton, Qt.LeftButton)
    soltar(a + QPointF(100, 0))
    A.reg(AR, "clic derecho durante el arrastre: cancela", pend() is None, "")


run("cancelar", cancelar)


# 3. Lo de siempre sigue igual -------------------------------------------------------------------------------------------
def de_siempre():
    a = pantalla(PB)
    v._seleccionar([])
    QTest.mouseClick(vis, Qt.LeftButton, Qt.NoModifier, a.toPoint())
    A.esperar(80)
    A.reg(AR, "un clic en el componente elige, no mueve", bool(v.seleccion) and pend() is None, f"{len(v.seleccion)}")
    v._seleccionar([])
    q = QPointF(30, vis.height() - 60)
    arrastrar(q, q + QPointF(120, -50))
    A.reg(AR, "arrastrar desde el vacío hace la ventana de selección", pend() is None and vis._banda_inicio is None, "")
    v._seleccionar([])
    b = pantalla([-60, -60, 10])
    arrastrar(b, b + QPointF(60, 30))
    A.reg(AR, "la base fija no se arrastra y lo dice", pend() is None, "")
    mensaje = v.timeline.estado.toolTip()
    A.reg(AR, "el mensaje nombra el componente fijo", "CBase" in mensaje and "fijo" in mensaje, mensaje)
    v._seleccionar([])
    A.esperar(100)
    A.clic_derecho(vis, a.toPoint())
    A.reg(AR, "clic derecho en el visor no se rompe", True, "")
    for m in list(A.MENUS):
        m.close()
    A.MENUS.clear()
    if v.modo_boceto.activo:
        v._salir_de_boceto()


run("lo de siempre", de_siempre)


# 4. Con unión -----------------------------------------------------------------------------------------------------------
def con_union():
    punta = np.array([55.0, 0.0, 22.0])         # la punta del brazo, ya sobre la base
    a = pantalla(punta)
    b = pantalla([0.0, 55.0, 22.0])
    arrastrar(a, b, 20)
    uid = next(k for k, u in v.doc.estado_final.uniones.items() if u["nombre"] == "Giro")
    giro = pend().valores[uid]["giro"]
    A.reg(AR, "revolución: el brazo gira 90° siguiendo el cursor", abs(giro % 360 - 90) < 2, f"{giro:.2f}°")
    A.reg(AR, "la punta se ve bajo el cursor", cerca(pantalla(visto(brazo, punta)), b, 4), "")
    A.reg(AR, "la altura del brazo no cambió (solo gira)", abs(visto(brazo, punta)[2] - 22) < 1e-6, "")
    A.esperar(120)
    A.foto(v, "posicion_asm_giro")
    QTest.mouseClick(v.arrastre.barra.revertir, Qt.LeftButton)
    A.esperar(100)
    A.reg(AR, "Revertir de la barra: vuelve y no agrega pasos", pend() is None and not v.arrastre.barra.isVisible(), "")
    pc = np.array([0.0, 70.0, 40.0])
    a = pantalla(pc)
    arrastrar(a, pantalla(pc + [300, 0, 80]))
    uid2 = next(k for k, u in v.doc.estado_final.uniones.items() if u["nombre"] == "Carril")
    A.reg(AR, "deslizante: el límite de 60 mm lo frena", abs(pend().valores[uid2]["desliz"] - 60) < 1e-6,
          f"{pend().valores[uid2]['desliz']:.3f}")
    A.reg(AR, "no se sale de su eje", abs(visto(carro, pc)[1] - 70) < 1e-6 and abs(visto(carro, pc)[2] - 40) < 1e-6, "")
    v.acciones["revertir_posicion"].trigger()
    A.esperar(100)
    A.reg(AR, "Revertir de la cinta con algo sin capturar: no abre panel ni agrega paso", pend() is None and v.panel is None, "")


run("con unión", con_union)


# 5. La pregunta antes de un comando ---------------------------------------------------------------------------------------
def pregunta():
    a = pantalla(PB)
    pasos = A.n_ops(v)
    arrastrar(a, a + QPointF(80, 0))
    responder("Cancelar")
    v.acciones["origen_union"].trigger()
    A.esperar(120)
    A.reg(AR, "Cancelar: no abre el comando y sigue sin capturar", v.panel is None and pend() is not None, "")
    responder("Continuar")
    v.acciones["origen_union"].trigger()
    A.esperar(150)
    A.reg(AR, "Continuar: vuelve a la posición anterior y abre el comando", v.panel is not None and pend() is None
          and bloque not in vis.transformaciones, "")
    if v.panel is not None:
        v.panel.cancelar()
        A.esperar(80)
    arrastrar(a, a + QPointF(80, 0))
    responder("Capturar posición")
    v.acciones["origen_union"].trigger()
    A.esperar(400)
    A.reg(AR, "Capturar posición: queda en el timeline y abre el comando", v.panel is not None and pend() is None
          and A.n_ops(v) == pasos + 2, f"{A.n_ops(v)} ← {pasos}")
    if v.panel is not None:
        v.panel.cancelar()
        A.esperar(80)
    A.deshacer(v)
    A.esperar(200)
    A.reg(AR, "capturar es un solo paso de deshacer", A.n_ops(v) == pasos, f"{A.n_ops(v)} ← {pasos}")


run("pregunta", pregunta)


# 6. Un cambio del documento descarta lo arrastrado ------------------------------------------------------------------------
def cambio():
    a = pantalla(PB)
    arrastrar(a, a + QPointF(80, 0))
    L("set_parameter", name="largo", expression="130 mm")
    A.esperar(200)
    A.reg(AR, "cambiar una cota sin capturar: descarta y limpia el dibujo", pend() is None and not v.arrastre.barra.isVisible()
          and not vis.transformaciones, "")
    A.deshacer(v)
    A.esperar(200)


run("cambio del documento", cambio)


# 7. Pieza de dos componentes con una unión --------------------------------------------------------------------------------
def pieza():
    pasos = A.n_ops(v)
    punta = np.array([55.0, 0.0, 22.0])
    arrastrar(pantalla(punta), pantalla([0.0, 55.0, 22.0]), 20)
    a = pantalla(PB)
    arrastrar(a, a + QPointF(60, 60))
    A.esperar(100)
    QTest.mouseClick(v.arrastre.barra.capturar, Qt.LeftButton)
    A.esperar(400)
    giro = next(j for j in api.llamar(s, "get_assembly", {})["result"]["joints"] if j["name"] == "Giro")["values"]["rotation"]
    A.reg(AR, "capturar: la unión guarda el giro", abs(giro % 360 - 90) < 2, f"{giro}")
    A.reg(AR, "capturar: el bloque queda en un paso de posición", A.n_ops(v) == pasos + 2, f"{A.n_ops(v)} ← {pasos}")
    A.reg(AR, "no quedó nada sin capturar", pend() is None and not vis.transformaciones, "")
    A.reg(AR, "terminado el cálculo no queda «Calculando…»", "Calculando" not in v.timeline.estado.toolTip(), v.timeline.estado.toolTip())
    L("set_parameter", name="largo", expression="150 mm")
    A.esperar(300)
    from omnicad.nucleo import geometria as geo
    lo, hi = geo.caja_envolvente(v.doc.estado_final.cuerpos[brazo].forma)
    A.reg(AR, "la cota nueva entra en la posición capturada (largo sobre Y)", abs(hi[1] - lo[1] - 150) < 1.5, f"{hi[1] - lo[1]:.2f}")
    A.esperar(150)
    A.foto(v, "posicion_asm_pieza")
    for _ in range(2):
        A.deshacer(v)
        A.esperar(200)
    A.reg(AR, "deshacer en cadena: vuelve al principio y el modelo sigue sano", A.n_ops(v) == pasos
          and all(r.estado != "error" for r in v.doc.resultados), f"{A.n_ops(v)}")


run("pieza", pieza)


# 8. Ventana chica ---------------------------------------------------------------------------------------------------------
def chica():
    for w, h in ((1024, 640), (800, 520)):
        v.resize(w, h)
        A.esperar(300)
        vis.encuadrar()
        A.esperar(200)
        a = pantalla(PB)
        arrastrar(a, a + QPointF(30, 0))
        barra = v.arrastre.barra
        A.reg(AR, f"ventana {w}x{h}: la barra entra entera y no pisa el navegador ni el ViewCube", barra.isVisible()
              and vis.geometry().contains(barra.geometry()) and not barra.geometry().intersects(v.area.viewcube.geometry())
              and not any(n.isVisible() and barra.geometry().intersects(n.geometry()) for n in v.area.arriba_izq), f"{barra.geometry()}")
        A.foto(v, f"posicion_asm_{w}x{h}")
        QTest.mouseClick(barra.revertir, Qt.LeftButton)
        A.esperar(100)
    v.resize(1900, 1000)


run("ventana chica", chica)

A.guardar_registro("posicion_asm")
fallas = [r for r in A.REGISTRO if not r["ok"]]
print(f"\n=== {len(A.REGISTRO)} comprobaciones, {len(fallas)} con ✗ ===")
QMessageBox.exec = QDialog.exec          # «¿Guardar cambios?» al cerrar no tiene quién la conteste
v.close()
sys.exit(0)

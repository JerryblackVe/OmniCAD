# -*- coding: utf-8 -*-
"""BOCETO · grupo «sin ninguna prueba» (PRUEBA-CMDS, E7): Selección en ventana / forma libre, Seleccionar todo, Invertir,
por nombre, por tamaño, Terminar con AutoConstrain (normal, vacío y con más de 250 entidades) y los comandos de otras
pestañas que se tocan con el boceto abierto (Mostrar tabla de configuración, Barrido de parámetros, Buscar similares, Revisar
geometría). Contra Fusion: Selection Window / Free-form / Select All / Finish with AutoConstrain. Eventos simulados al Lienzo."""
import sys

import arnes as A
import numpy as np
from omnicad import api
from PySide6.QtCore import Qt, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

AR = "BOCETO·SEL+TERMINAR"
s = api.Sesion()


def L(nombre, **a):
    r = api.llamar(s, nombre, a)
    assert r["ok"], (nombre, a, r)
    return r["result"]


L("create_box", length=40, width=30, height=20, name="Caja")
L("create_sketch", plane="XY", name="T")
for a, b, c, d in ((-10, -10, 10, -10), (10, -10, 10, 10), (10, 10, -10, 10), (-10, 10, -10, -10)):
    L("draw_line", sketch="T", start_x=a, start_y=b, end_x=c, end_y=d)
L("draw_circle", sketch="T", center_x=0, center_y=0, radius=4)
L("create_sketch", plane="XY", name="Vacio")
L("create_sketch", plane="XY", name="Grande")
for i in range(260):
    L("draw_line", sketch="Grande", start_x=i * 3, start_y=40, end_x=i * 3 + 1, end_y=45)
ID = {n: s.paso(n).id for n in ("T", "Vacio", "Grande")}
app, v = A.iniciar(s.doc, 1280, 720)
A.esperar(400)
MS = []


def entrar(nombre="T"):
    v.editar_operacion(ID[nombre])
    A.esperar(500)
    v.visor.encuadrar()
    v.visor.vista("arriba")
    A.esperar(300)
    lz = v.modo_boceto.lienzo
    lz.mensaje.connect(MS.append)
    return lz


def salir():
    """Deja la ventana sin boceto ni comando abierto, para que el caso siguiente parta limpio."""
    if v.panel is not None:
        v.panel.cancelar() if hasattr(v.panel, "cancelar") else QTest.keyClick(v.panel, Qt.Key_Escape)
        A.esperar(200)
    if v.modo_boceto.activo:
        v.modo_boceto.terminar()
        A.esperar(300)
    v.visor.set_modo(None)


def pt(lz, x, y):
    return lz.mapFromGlobal(v.visor.mapToGlobal(v.visor.proyectar(np.array((x, y, 0.0))).toPoint()))


def arrastrar(lz, a, b):
    QTest.mousePress(lz, Qt.LeftButton, Qt.NoModifier, a)
    A.esperar(80)
    for i in range(1, 7):
        QTest.mouseMove(lz, a + (b - a) * i / 6)
        A.esperar(40)
    QTest.mouseRelease(lz, Qt.LeftButton, Qt.NoModifier, b)
    A.esperar(250)


def modal_esc():
    w = QApplication.activeModalWidget()
    if w:
        QTest.keyClick(w, Qt.Key_Escape)


def activar(clave):
    v.activateWindow()
    A.esperar(200)
    v.acciones[clave].trigger()
    A.esperar(800)


# ------------------------------------------------ selección por ventana con el mouse (el comportamiento de base)
lz = entrar()
n_ent = 10                                       # 4 líneas + círculo + sus 5 puntos
v.activateWindow()
A.esperar(200)
arrastrar(lz, pt(lz, -30, -30), pt(lz, 30, 30))
A.reg(AR, "ventana de izquierda a derecha con todo adentro elige las 10 entidades", len(lz.seleccion) == n_ent, len(lz.seleccion))
lz.seleccion = []
arrastrar(lz, pt(lz, -15, -5), pt(lz, 15, 5))
A.reg(AR, "ventana L→R: solo lo que queda entero adentro (círculo y centro)", len(lz.seleccion) == 2, len(lz.seleccion))
lz.seleccion = []
arrastrar(lz, pt(lz, 15, 5), pt(lz, -15, -5))
A.reg(AR, "ventana R→L: también lo que toca (círculo, centro y las 2 verticales)", len(lz.seleccion) == 4, len(lz.seleccion))
lz.seleccion = []
arrastrar(lz, pt(lz, 200, 200), pt(lz, 220, 220))
A.reg(AR, "una ventana en el vacío no elige nada ni rompe", not lz.seleccion and v.modo_boceto.activo, len(lz.seleccion))

# ------------------------------------------------ comandos del grupo SELECCIONAR con el boceto abierto
for clave, texto in (("sel_ventana", "Selección en ventana"), ("sel_libre", "Selección de forma libre")):
    lz = entrar() if not v.modo_boceto.activo else v.modo_boceto.lienzo
    activar(clave)
    A.reg(AR, f"{texto} desde el boceto no lo cierra (en Fusion elige geometría del boceto)", v.modo_boceto.activo,
          f"boceto {'abierto' if v.modo_boceto.activo else 'CERRADO'}, modo del visor {v.visor.modo}")
    A.foto(v, f"sel_{clave}")
    salir()

lz = entrar()
activar("seleccionar_todo")
A.reg(AR, "Seleccionar todo con el boceto abierto elige toda su geometría (Fusion)", len(lz.seleccion) == n_ent,
      f"{len(lz.seleccion)} elegidas; mensajes {MS[-1:]}")
salir()
lz = entrar()
lz.seleccion = lz.seleccion[:0]
arrastrar(lz, pt(lz, -15, -5), pt(lz, 15, 5))
antes = len(lz.seleccion)
activar("invertir_seleccion")
A.reg(AR, "Invertir selección con el boceto abierto invierte la geometría del boceto, no elige cuerpos",
      len(lz.seleccion) == n_ent - antes and not v.seleccion, f"{antes} → {len(lz.seleccion)} del boceto; cuerpos elegidos {len(v.seleccion)}")
v.seleccion and v._seleccionar([])
for clave, texto in (("seleccion_nombre", "por nombre"), ("seleccion_tamano", "por tamaño")):
    QTimer.singleShot(500, modal_esc)
    activar(clave)
    A.reg(AR, f"Seleccionar {texto}: el diálogo se cierra con Esc y el boceto sigue", QApplication.activeModalWidget() is None
          and v.modo_boceto.activo, "")
salir()

# ------------------------------------------------ Terminar con AutoConstrain
lz = entrar()
n0 = len(lz.b.restricciones)
activar("sk_terminar_auto")
op = next(o for o in v.doc.operaciones if o.id == ID["T"])
A.reg(AR, "Terminar con AutoConstrain: restringe y termina el boceto, con aviso", not v.modo_boceto.activo
      and len(op.boceto.restricciones) > n0 and any("restricc" in m.lower() for m in MS[-3:]), f"{len(op.boceto.restricciones)} restricciones; {MS[-1:]}")
v.activateWindow()
A.esperar(150)
QTest.keyClick(v, Qt.Key_Z, Qt.ControlModifier)
A.esperar(500)
A.reg(AR, "Ctrl+Z deshace AutoConstrain y el terminar en un paso razonable (el boceto vuelve a sus 0 restricciones o queda abierto)",
      len(next(o for o in v.doc.operaciones if o.id == ID["T"]).boceto.restricciones) == n0 or v.modo_boceto.activo,
      len(next(o for o in v.doc.operaciones if o.id == ID["T"]).boceto.restricciones))
salir()
lz = entrar("Vacio")
MS.clear()
activar("sk_terminar_auto")
A.reg(AR, "Terminar con AutoConstrain en un boceto vacío termina y lo dice", not v.modo_boceto.activo and any("vacío" in m for m in MS), MS[-1:])
lz = entrar("Grande")
MS.clear()
activar("sk_terminar_auto")
A.reg(AR, "Terminar con AutoConstrain con más del tope de entidades termina sin restringir y dice el tope",
      not v.modo_boceto.activo and any("tope" in m for m in MS), MS[-1:])

# ------------------------------------------------ comandos de otras pestañas con el boceto abierto
for clave in ("mostrar_configuracion", "barrido_parametros", "buscar_similares", "revisar_geometria"):
    lz = entrar()
    n = len(lz.b.curvas)
    activar(clave)
    abierto = v.panel is not None
    A.foto(v, f"sel_{clave}")
    salir()
    op = next(o for o in v.doc.operaciones if o.id == ID["T"])
    A.reg(AR, f"{clave} con el boceto abierto: abre su comando o dice por qué, y el boceto no pierde curvas",
          len(op.boceto.curvas) == n and (abierto or bool(MS[-1:])), f"panel {abierto}, curvas {len(op.boceto.curvas)}/{n}")

A.reg(AR, "ninguna excepción en un slot de Qt", not A.ERRORES, A.ERRORES[:1])
A.guardar_registro("boceto_seleccion_terminar")
print(f"\n=== {len(A.REGISTRO)} comprobaciones, {len([r for r in A.REGISTRO if not r['ok']])} con ✗ ===", flush=True)
v.doc.modificado = False
v.close()
sys.exit(0)

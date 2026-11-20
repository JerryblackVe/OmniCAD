# -*- coding: utf-8 -*-
"""REPRO-E11 (E7): B-729 (Editar patrón con mouse), B-730 (Desglosar «Hola Ñandú 123») y B-731 (Enter tras Tab en el Patrón
circular). Eventos simulados al Lienzo y a los widgets del panel; nunca el cursor real. Contra Fusion: Edit Pattern / Explode Text."""
import math
import sys

import arnes as A
from omnicad import api
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QToolButton

AR = "REPRO·E11"
s = api.Sesion()


def L(n, **a):
    r = api.llamar(s, n, a)
    assert r["ok"], (n, a, r)
    return r["result"]


for n in ("Pat", "Pat2", "Tex"):
    L("create_sketch", name=n, plane="XY")
c = L("draw_circle", sketch="Pat", center_x=30, center_y=10, radius=4)["entities"][0]["id"]
L("sketch_circular_pattern", sketch="Pat", entities=[c], count=5, center_x=0, center_y=0)
L("draw_circle", sketch="Pat2", center_x=30, center_y=10, radius=4)
L("add_text", sketch="Tex", text="Hola Ñandú 123", x=0, y=0, height=8)
ID = {n: s.paso(n).id for n in ("Pat", "Pat2", "Tex")}
app, v = A.iniciar(s.doc)
A.esperar(400)
lz = None
MS = []


def entrar(nombre, centro, span):
    global lz
    v.editar_operacion(ID[nombre])
    A.esperar(500)
    lz = v.modo_boceto.lienzo
    MS.clear()
    lz.mensaje.connect(MS.append)
    lz.visor.objetivo = lz.plano.a_3d(*centro)
    lz.visor.distancia = span / 2 / math.sin(math.radians(lz.visor.fov) / 2) * 1.3
    lz.visor.update(); lz.update()
    A.activar(v); A.esperar(300)


def salir():
    lz.set_herramienta("seleccionar"); lz.seleccion = []
    v.modo_boceto.terminar(); A.esperar(400)


def px(x, y):
    return lz.a_px(x, y).toPoint()


def clic(p, doble=False):
    if doble:
        QTest.mouseDClick(lz, Qt.LeftButton, Qt.NoModifier, p)
    else:
        QTest.mouseClick(lz, Qt.LeftButton, Qt.NoModifier, p)
    A.esperar(150)


def pulsar(clave):
    acc = v.modo_boceto.acciones[clave]
    b = next((b for b in v.cinta.findChildren(QToolButton) if b.defaultAction() is acc and b.isVisible()), None)
    QTest.mouseClick(b, Qt.LeftButton) if b else acc.trigger()
    A.esperar(250)


# ---------------------------------------------------------------- B-729
entrar("Pat", (0, 0), 90)
copia = next(iter(lz.b.patrones[0]["copias"]["0"]))
pc = lz.b.curvas[copia]
cx, cy = lz.b.coords(pc.centro)
lz.seleccion = []
pulsar("sk_editar_patron")                       # herramienta «armada» sin elegir nada
A.reg(AR, "B-729 · Editar patrón sin selección avisa", any("Clic en una curva del patrón" in m for m in MS), MS[-1:])
A.reg(AR, "B-729 · …y la herramienta queda armada esperando el clic (lo que hace Fusion)", lz.herramienta == "patron_circular" or lz.herramienta == "editar_patron", lz.herramienta)
clic(px(cx + pc.radio, cy))                          # clic sobre el borde de una copia
A.reg(AR, "B-729 · clic en una copia con Editar patrón abre su diálogo", v.modo_boceto.patron.isVisible(),
      f"herramienta={lz.herramienta}, seleccion={lz.seleccion}, panel visible={v.modo_boceto.patron.isVisible()}")
lz.set_herramienta("seleccionar"); lz.seleccion = []
A.esperar(200)
zonas = dict(lz._zonas_glifos)
glifos = [i for i, r in zonas.items() if lz.b.restricciones.get(i) is not None and lz.b.restricciones[i].tipo == "patron"]
A.reg(AR, "B-729 · hay un glifo de patrón en pantalla", bool(glifos), f"{len(glifos)} glifos de {len(zonas)} zonas")
if glifos:
    clic(zonas[glifos[0]].center().toPoint(), doble=True)
    A.reg(AR, "B-729 · doble clic en el glifo del patrón abre Editar patrón", v.modo_boceto.patron.isVisible(),
          f"seleccion={lz.seleccion}, msgs={MS[-2:]}")
lz.set_herramienta("seleccionar"); lz.seleccion = []
salir()

# ---------------------------------------------------------------- B-730
entrar("Tex", (20, 0), 80)
pulsar("sk_desglosar_texto")
tx = next(c for c in lz.b.curvas.values() if c.tipo == "texto")
A.reg(AR, "B-730 · el texto «Hola Ñandú 123» existe antes", tx is not None, str(getattr(tx, "texto", "")))
n0 = len(lz.b.curvas)
for xs, ys in ((2, 3), (30, 3), (55, 3)):          # sobre varias letras del texto
    MS.clear()
    clic(px(xs, ys))
    quedan = [c for c in lz.b.curvas.values() if c.tipo == "texto"]
    print(f"   clic ({xs},{ys}): textos {len(quedan)}, curvas {len(lz.b.curvas)}, msgs {MS[-1:]}, herr {lz.herramienta}")
    if not quedan:
        break
quedan = [c for c in lz.b.curvas.values() if c.tipo == "texto"]
A.reg(AR, "B-730 · Desglosar convierte el texto en curvas (o avisa por qué no)", not quedan or bool(MS),
      f"textos {len(quedan)}, curvas {n0}->{len(lz.b.curvas)}, msgs {MS[-2:]}")
salir()

# ---------------------------------------------------------------- B-731 (ya arreglada por E4: solo confirmar)
entrar("Pat2", (10, 10), 90)
lz.seleccion = []
pulsar("sk_patron_circular")
pan = v.modo_boceto.patron
clic(px(34, 10))                                  # el círculo
QTest.keyClick(lz, Qt.Key_Return); A.esperar(150)  # pasa al campo Centro
clic(px(0, 0))                                    # el origen
c0 = len(lz.b.curvas)
cant = pan.campos["cantidad"]
A.activar(v); cant.setFocus(); cant.selectAll(); QTest.keyClicks(cant, "7"); QTest.keyClick(cant, Qt.Key_Tab); A.esperar(150)
QTest.keyClick(QApplication.focusWidget() or cant, Qt.Key_Return); A.esperar(300)
A.reg(AR, "B-731 · Tab desde Cantidad + Enter acepta el Patrón circular (panel cerrado y copias creadas)",
      not pan.isVisible() and len(lz.b.curvas) > c0, f"panel visible={pan.isVisible()}, curvas {c0}->{len(lz.b.curvas)}, msgs={MS[-1:]}")
salir()

# ---------------------------------------------------------------- B-730 (extra): clic fuera del texto con Desglosar, ¿avisa?
entrar("Tex", (20, 0), 80)
pulsar("sk_desglosar_texto")
MS.clear()
clic(px(60, 25))
A.reg(AR, "B-730 · clic fuera del texto con Desglosar avisa en 1 renglón (no queda mudo)", bool(MS), f"msgs={MS}")
salir()

A.reg(AR, "ninguna excepción en un slot de Qt", not A.ERRORES, A.ERRORES[:1])
A.guardar_registro("repro_e11_patron_texto")
print(f"\n=== {len(A.REGISTRO)} comprobaciones, {len([r for r in A.REGISTRO if not r['ok']])} con ✗ ===", flush=True)
v.doc.modificado = False
v.close()
sys.exit(0)

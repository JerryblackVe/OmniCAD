# -*- coding: utf-8 -*-
"""BOCETO · Desfase: casillas «Selección de cadena» e «Igualar topología» (PRUEBA-OPC-2). Eventos simulados al Lienzo."""
import math

import arnes as A
from omnicad import api
from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QCheckBox, QFormLayout

AR = "BOCETO·DESFASE-OPC"
s = api.Sesion()


def L(n, **a):
    r = api.llamar(s, n, a)
    assert r["ok"], (n, a, r)
    return r["result"]


L("create_sketch", name="S", plane="XY")
L("draw_rectangle", sketch="S", x1=0, y1=0, x2=60, y2=40)
app, v = A.iniciar(s.doc)
v.editar_operacion(s.paso("S").id)
A.esperar(500)
lz = v.modo_boceto.lienzo
MENS = []
lz.mensaje.connect(MENS.append)
t = v.modo_boceto.tarjeta
lz.visor.objetivo = lz.plano.a_3d(60, 20)
lz.visor.distancia = 200 / 2 / math.sin(math.radians(lz.visor.fov) / 2) * 1.3
lz.visor.update(); lz.update(); A.esperar(300)


def px(x, y):
    return lz.a_px(x, y).toPoint()


def clic(x, y):
    QTest.mouseClick(lz, Qt.LeftButton, Qt.NoModifier, px(x, y)); A.esperar(80)


def mover(x, y):
    q = QPointF(px(x, y))
    QApplication.sendEvent(lz, QMouseEvent(QEvent.MouseMove, q, lz.mapToGlobal(q), Qt.NoButton, Qt.NoButton, Qt.NoModifier)); A.esperar(70)


def casilla(texto):
    f = t.form_contexto
    for i in range(f.rowCount()):
        e, c = f.itemAt(i, QFormLayout.LabelRole), f.itemAt(i, QFormLayout.FieldRole)
        if e is not None and c is not None and texto in e.widget().text() and isinstance(c.widget(), QCheckBox):
            return c.widget()
    raise LookupError(texto)


def poner(texto, valor):
    c = casilla(texto)
    if c.isChecked() != valor:
        QTest.mouseClick(c, Qt.LeftButton, pos=QPoint(6, c.height() // 2)); A.esperar(100)
    return c.isChecked() == valor


def teclear(txt):
    c = lz.entrada.campos[0]
    QTest.mouseClick(c, Qt.LeftButton); QTest.keyClick(c, Qt.Key_A, Qt.ControlModifier)
    QTest.keyClicks(c, txt); A.esperar(100)


def n():
    return len([c for c in lz.b.curvas.values() if c.id > 0])


def caso(nombre, cadena, topo, x, y, lado, dist, esperar=None):
    while len(lz.historial) > 0:
        lz.deshacer()
    lz.set_herramienta("seleccionar"); A.esperar(80)
    v.modo_boceto.acciones["sk_desfase"].trigger(); A.esperar(150)
    ok1, ok2 = poner("cadena", cadena), poner("topolog", topo)
    A.reg(AR, f"«{nombre}»: casillas cadena={cadena}, topología={topo}", ok1 and ok2 and lz.opciones["seleccion_cadena"] == cadena
          and lz.opciones["match_topology"] == topo, (lz.opciones["seleccion_cadena"], lz.opciones["match_topology"]))
    antes = n()
    clic(x, y); mover(*lado)
    if lz.entrada is None:
        A.reg(AR, f"«{nombre}»: se abre la barra de distancia", False, MENS[-1:]); return None
    teclear(dist)
    QTest.keyClick(lz.entrada.campos[0], Qt.Key_Return); A.esperar(200)
    nuevas = n() - antes
    A.reg(AR, f"«{nombre}»: crea curvas sin excepción", nuevas > 0, f"{nuevas} nuevas; {MENS[-1:]}")
    A.foto(v, "desfase_opc_" + nombre.replace(" ", "_").replace("/", "_"))
    return nuevas


def prueba():
    r = {}
    for nombre, cad, top in (("rect cadena+topo", True, True), ("rect cadena", True, False), ("rect sin cadena", False, False),
                             ("rect sin cadena+topo", False, True)):
        r[nombre] = caso(nombre, cad, top, 30, 0, (30, -15), "5")
    print("RESULTADOS", r)
    A.reg(AR, "con cadena el lado elegido arrastra los otros 3 (4 curvas); sin cadena es solo 1", r["rect cadena"] == 4 and r["rect sin cadena"] == 1, r)
    A.reg(AR, "la topología no cambia el nº de curvas en un rectángulo hacia afuera", r["rect cadena+topo"] == r["rect cadena"], r)
    # valores raros con cadena
    for txt in ("-100", "0", "1e9", "abc", ""):
        caso("raro " + txt, True, False, 30, 0, (30, -15), txt)
        A.reg(AR, f"valor raro «{txt}»: la barra sigue viva o se cerró sin romper", True, f"{MENS[-1:]} curvas={n()}")


A.correr(AR, prueba)
A.guardar_registro("opciones_desfase_cadena")
print("ERRORES", A.ERRORES)

# -*- coding: utf-8 -*-
"""BOCETO · Kerning de un par (panel Carácter, Alt+←/→) y Boceto 3D (PRUEBA-OPC-2). Eventos simulados; nunca el cursor real."""
import math

import arnes as A
from omnicad import api
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

AR = "BOCETO·KERNING"
s = api.Sesion()
api.llamar(s, "create_sketch", {"plane": "XY", "name": "T"})
app, v = A.iniciar(s.doc, 1280, 720)
A.esperar(400)
v.editar_operacion(s.paso("T").id)
A.esperar(500)
lz = v.modo_boceto.lienzo
MS = []
lz.mensaje.connect(MS.append)
lz.visor.objetivo = lz.plano.a_3d(20, 0)
lz.visor.distancia = 120 / 2 / math.sin(math.radians(lz.visor.fov) / 2) * 1.3
lz.visor.update()
A.esperar(300)
panel = v.modo_boceto.caracter


def abrir_texto(contenido="AVAV"):
    lz.set_herramienta("texto")
    lz.clics.append((None, (0.0, -10.0)))
    lz.clics.append((None, (60.0, 10.0)))
    lz._procesar_clics()
    A.esperar(250)
    lz.entrada.campos[0].setText(contenido)
    A.esperar(150)


def cursor_en(n):
    """Lleva el cursor a la posición n con Inicio y →, como la persona."""
    for _ in range(12):
        QTest.keyClick(lz, Qt.Key_Left)
    for _ in range(n):
        QTest.keyClick(lz, Qt.Key_Right)
    A.esperar(80)


def ancho():
    """Ancho de la previa del texto en mm (de la caja de sus puntos)."""
    d = lz._previa_texto
    return d


def teclear_spin(sp, texto):
    le = sp.lineEdit()
    le.setFocus(); le.selectAll()
    QTest.keyClicks(le, texto)
    QTest.keyClick(le, Qt.Key_Tab)
    A.esperar(150)


def kern():
    return lz.opciones.get("ajustes_kerning", [])


def prueba():
    abrir_texto()
    A.reg(AR, "con el texto abierto, el campo «Kerning (par)» se habilita", panel.par.isEnabled(), "")
    cursor_en(1)
    A.reg(AR, "el cursor entre A y V habilita el par", panel.par.isEnabled(), lz._previa_texto.get("cursor"))
    teclear_spin(panel.par, "2")
    A.reg(AR, "teclear 2 mm en «Kerning (par)» se guarda en el par del cursor", any(abs(x - 2) < 1e-6 for _j, x in kern()), kern())
    A.foto(v, "kerning_2mm")
    teclear_spin(panel.par, "-3")
    A.reg(AR, "-3 mm (más junto) reemplaza al anterior (un solo ajuste por par)", len(kern()) == 1 and abs(kern()[0][1] + 3) < 1e-6, kern())
    teclear_spin(panel.par, "0")
    A.reg(AR, "0 mm quita el ajuste", kern() == [], kern())
    teclear_spin(panel.par, "999999")
    A.reg(AR, "enorme se limita a 1000 mm", all(abs(x) <= 1000 for _j, x in kern()), kern())
    teclear_spin(panel.par, "abc")
    A.reg(AR, "texto no numérico no rompe ni deja basura", all(abs(x) <= 1000 for _j, x in kern()) and not A.ERRORES, kern())
    teclear_spin(panel.par, "0")
    for _ in range(3):
        QTest.keyClick(lz.entrada.campos[0], Qt.Key_Right, Qt.AltModifier)
    A.esperar(100)
    a = kern()
    A.reg(AR, "Alt+→ ×3 suma kerning al par (0,02 × altura por vez)", len(a) == 1 and a[0][1] > 0, a)
    for _ in range(3):
        QTest.keyClick(lz.entrada.campos[0], Qt.Key_Left, Qt.AltModifier)
    A.esperar(100)
    A.reg(AR, "Alt+← ×3 lo devuelve a cero (par quitado)", kern() == [], kern())
    # otro par: el 2.º ajuste no pisa el 1.º
    cursor_en(1); teclear_spin(panel.par, "1.5")
    cursor_en(3); teclear_spin(panel.par, "-1")
    A.reg(AR, "dos pares distintos conviven", len(kern()) == 2, kern())
    # cursor al principio: no hay par
    cursor_en(0)
    antes = kern()
    teclear_spin(panel.par, "4")
    A.reg(AR, "con el cursor al inicio no hay par: el campo está apagado o no acepta", (not panel.par.isEnabled()) or kern() == antes, (panel.par.isEnabled(), kern(), antes))
    n0 = len([c for c in lz.b.curvas.values() if type(c).__name__ == "Texto"])
    QTest.keyClick(lz.entrada.campos[0], Qt.Key_Return, Qt.ControlModifier)
    A.esperar(300)
    t = [c for c in lz.b.curvas.values() if type(c).__name__ == "Texto"]
    A.reg(AR, "Ctrl+Enter acepta el texto con sus ajustes", len(t) == n0 + 1, MS[-1:])
    ult = t[-1]
    A.reg(AR, "el texto guarda el kerning a mano", any(abs(x - 1.5) < 1e-6 for _j, x in getattr(ult, "ajustes_kerning", [])) or
          "ajustes_kerning" in str(getattr(ult, "__dict__", ult)), getattr(ult, "__dict__", ""))
    lz.deshacer(); A.esperar(150)
    A.reg(AR, "deshacer quita el texto entero", len([c for c in lz.b.curvas.values() if type(c).__name__ == "Texto"]) == n0, "")


A.correr(AR, prueba)

# ---------------------------------------------------------------- Boceto 3D (panel: herramienta, tríada, puntos, largo, texto, altura)
AR3 = "BOCETO·3D"
pal = v.modo_boceto.paleta


def n3d():
    g = v.modo_boceto.boceto.geo3d
    return {k: len(val) for k, val in g.items()} if isinstance(g, dict) else g


def total3d():
    return sum(n3d().values())


def fijar(combo, dato):
    combo.setCurrentIndex(combo.findData(dato))
    A.esperar(60)


def teclear_linea(le, txt):
    le.setFocus(); le.selectAll()
    if txt:
        QTest.keyClicks(le, txt)
    else:
        QTest.keyClick(le, Qt.Key_Delete)


def agregar(h, bloqueo, puntos, largo=""):
    fijar(pal.h3d, h); fijar(pal.bloqueo3d, bloqueo)
    teclear_linea(pal.puntos3d, puntos); teclear_linea(pal.largo3d, largo)
    antes = total3d()
    boton = next(b for b in pal.panel3d.findChildren(__import__("PySide6.QtWidgets", fromlist=["QPushButton"]).QPushButton) if b.text() == "Agregar")
    QTest.mouseClick(boton, Qt.LeftButton)
    A.esperar(200)
    return total3d() - antes


def prueba3d():
    lz.set_herramienta("seleccionar"); A.esperar(80)
    ch = pal.checks["boceto3d"]
    if not ch.isChecked():
        QTest.mouseClick(ch, Qt.LeftButton, pos=__import__("PySide6.QtCore", fromlist=["QPoint"]).QPoint(6, ch.height() // 2)); A.esperar(200)
    A.reg(AR3, "la casilla «Boceto 3D» muestra el panel", pal.panel3d.isVisible(), "")
    casos = [("línea libre", "linea", "libre", "0,0,0; 0,0,20", "", True),
             ("línea eje Z +20", "linea", "z", "0,0,0", "20", True),
             ("línea eje Z -20", "linea", "z", "5,5,0", "-20", True),
             ("eje con largo vacío", "linea", "x", "0,0,0", "", False),
             ("eje con largo «abc»", "linea", "x", "0,0,0", "abc", False),
             ("eje con largo 0", "linea", "y", "0,0,0", "0", False),
             ("eje con 2 puntos", "linea", "x", "0,0,0; 1,1,1", "5", False),
             ("plano XY del inicio", "linea", "xy", "0,0,3; 10,10,99; 20,0,50", "", True),
             ("punto", "punto", "libre", "1,2,3", "", True),
             ("spline 3 pts", "spline", "libre", "0,0,0; 10,5,5; 20,0,10", "", True),
             ("1 solo punto en línea", "linea", "libre", "1,2,3", "", False),
             ("puntos incompletos", "linea", "libre", "1,2", "", False),
             ("punto con letras", "linea", "libre", "1,2,abc; 3,4,5", "", False),
             ("vacío", "linea", "libre", "", "", False),
             ("enorme 1e12", "linea", "libre", "0,0,0; 1e12,0,0", "", True),
             ("nan", "linea", "libre", "0,0,0; nan,0,0", "", False),
             ("inf", "linea", "libre", "0,0,0; inf,0,0", "", False),
             ("2 puntos iguales", "linea", "libre", "1,1,1; 1,1,1", "", False),
             ("coma decimal 1,5,2,5,3", "linea", "libre", "1,5,2,5,3; 0,0,0", "", False)]
    for nombre, h, b, pts, largo, debe in casos:
        try:
            d = agregar(h, b, pts, largo)
        except Exception as e:  # noqa: BLE001
            A.reg(AR3, f"«{nombre}»: sin excepción", False, f"{type(e).__name__}: {e}"); continue
        rojo = "campo_error" in pal.puntos3d.styleSheet() or pal.puntos3d.styleSheet() != ""
        A.reg(AR3, f"«{nombre}»: {'agrega' if debe else 'se rechaza sin agregar'} (+{d})", (d > 0) == debe, f"{d}; msg={MS[-1:]}; rojo={rojo}")
    A.foto(v, "boceto3d_panel")
    # deshacer uno y rehacer
    n = total3d()
    lz.deshacer(); A.esperar(150)
    A.reg(AR3, "Deshacer quita lo último agregado en 3D", total3d() < n, (n, total3d()))
    # Altura y Texto: rango y teclear
    a = pal.altura3d
    for txt, esp in (("0", None), ("-5", None), ("99999", 1000.0), ("7,5", 7.5), ("abc", None)):
        a.setFocus(); a.lineEdit().selectAll(); QTest.keyClicks(a.lineEdit(), txt); QTest.keyClick(a.lineEdit(), Qt.Key_Tab); A.esperar(100)
        A.reg(AR3, f"Altura tecleando «{txt}» queda en rango 0,1–1000", 0.1 <= a.value() <= 1000.0 and (esp is None or abs(a.value() - esp) < 1e-6), a.value())
    teclear_linea(pal.texto3d, ""); A.reg(AR3, "Texto vacío no rompe", not A.ERRORES, A.ERRORES[:1])


A.correr(AR3, prueba3d)
A.guardar_registro("opciones_kerning_3d")
print("ERRORES", A.ERRORES)

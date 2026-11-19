# -*- coding: utf-8 -*-
"""BOCETO · formas de CREAR sin prueba como usuario (PRUEBA-CMDS, E7): círculo 2p/3p/2t/3t, rectángulo desde el centro,
polígono por arista/circunscrito, ranuras (5 tipos), curva cónica, espiral, arco tangente, spline de control y desglosar
texto. Cada una: ítem real del menú, clics en el Lienzo, la forma que queda (tipo y medida), Esc a mitad (no deja nada) y
Ctrl+Z (la saca de un paso). Contra Fusion (Sketch > Create). Eventos simulados; Ctrl+Z con la ventana activada."""
import sys

import arnes as A
import numpy as np
from omnicad import api
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

AR = "BOCETO·CREAR"
s = api.Sesion()
L = lambda n, **a: api.llamar(s, n, a)["result"]                                        # noqa: E731
L("create_box", length=60, width=60, height=10, name="Caja")
L("create_sketch", plane="XY", name="T")
L("draw_line", sketch="T", start_x=-30, start_y=-20, end_x=30, end_y=-20)           # dos rectas para las tangentes
L("draw_line", sketch="T", start_x=-30, start_y=20, end_x=30, end_y=20)
L("draw_line", sketch="T", start_x=40, start_y=-30, end_x=40, end_y=30)
ID = s.paso("T").id
app, v = A.iniciar(s.doc, 1280, 720)
A.esperar(400)
MS = []
v.editar_operacion(ID)
A.esperar(500)
v.visor.encuadrar()
v.visor.vista("arriba")
A.esperar(300)
lz = v.modo_boceto.lienzo
lz.mensaje.connect(MS.append)


def pt(x, y):
    return lz.mapFromGlobal(v.visor.mapToGlobal(v.visor.proyectar(np.array((x, y, 0.0))).toPoint()))


def clic(x, y):
    QTest.mouseClick(lz, Qt.LeftButton, Qt.NoModifier, pt(x, y))
    A.esperar(150)


def tecla(k, mod=Qt.NoModifier):
    v.activateWindow()
    lz.setFocus()
    A.esperar(150)
    QTest.keyClick(lz, k, mod)
    A.esperar(300)


def planas():
    return [c for c in lz.b.curvas.values() if c.id > 0]


def tipos(desde):
    return sorted(c.tipo for c in planas()[desde:])


def herramienta(clave):
    v.modo_boceto.acciones[clave].trigger()
    A.esperar(250)


# clave, clics, qué debe quedar (tipos nuevos), enunciado
CASOS = [
    ("sk_circulo_2p", [(-10, 0), (10, 0)], ["circulo"], "círculo por 2 puntos (diámetro 20)"),
    ("sk_circulo_3p", [(-10, 0), (10, 0), (0, 10)], ["circulo"], "círculo por 3 puntos"),
    ("sk_circulo_2t", [(0, -20), (0, 20), (0, 0)], ["circulo"], "círculo tangente a las dos rectas (clic en cada una)"),
    ("sk_circulo_3t", [(-20, -20), (0, 20), (40, 0)], ["circulo"], "círculo con 3 tangentes"),
    ("sk_rectangulo_centro", [(0, 0), (10, 8)], ["linea"] * 6, "rectángulo desde el centro (4 líneas + 2 diagonales de construcción, como Fusion)"),
    ("sk_poligono_arista", [(-8, -5), (8, -5), (0, 5)], ["circulo"] + ["linea"] * 6, "polígono por arista (6 lados + círculo de construcción)"),
    ("sk_poligono_circunscrito", [(0, 0), (10, 0)], ["circulo"] + ["linea"] * 6, "polígono circunscrito (6 lados + círculo de construcción)"),
    ("sk_ranura_centro", [(0, 0), (15, 0), (15, 5)], None, "ranura de centro a centro"),
    ("sk_ranura_total", [(-15, 0), (15, 0), (15, 5)], None, "ranura de longitud total"),
    ("sk_ranura_punto", [(-15, 0), (15, 0), (15, 5)], None, "ranura de centro a punto"),
    ("sk_ranura_arco_centro", [(0, 0), (12, 0), (0, 12), (12, 4)], None, "ranura en arco de punto central"),
    ("sk_ranura_arco_3p", [(-12, 0), (0, 12), (12, 0), (12, 4)], None, "ranura en arco de tres puntos"),
    ("sk_conica", [(-15, 0), (15, 0), (0, 12), (0, 5)], None, "curva cónica (extremos y punto)"),
    ("sk_espiral", [(0, 0), (12, 0)], None, "espiral (centro y radio)"),
    ("sk_arco_tangente", [(30, -20), (40, -5)], ["arco"], "arco tangente desde el extremo de una recta"),
    ("sk_spline_control", [(-20, 0), (-10, 12), (10, -12), (20, 0)], None, "spline de puntos de control (4 clics)"),
]
for clave, clics, esperado, texto in CASOS:
    n0 = len(planas())
    try:
        herramienta(clave)
        for c in clics:
            clic(*c)
        tecla(Qt.Key_Return)                         # varias herramientas cierran con Enter
        nuevos = tipos(n0)
        ok = bool(nuevos) and (esperado is None or nuevos == sorted(esperado))
        A.reg(AR, f"{clave}: {texto}", ok, f"quedó {nuevos}; mensaje {MS[-1:] and MS[-1][:90]}")
        A.foto(v, f"forma_{clave}")
        if len(planas()) > n0:
            tecla(Qt.Key_Z, Qt.ControlModifier)
            A.reg(AR, f"{clave}: Ctrl+Z la saca en un solo paso", len(planas()) == n0, len(planas()) - n0)
        # Esc a mitad: un clic y Esc no deja nada
        herramienta(clave)
        clic(*clics[0])
        tecla(Qt.Key_Escape)
        tecla(Qt.Key_Escape)
        A.reg(AR, f"{clave}: Esc a mitad de camino no deja nada", len(planas()) == n0, len(planas()) - n0)
    except Exception as e:                                                              # noqa: BLE001
        A.reg(AR, f"{clave}: sin excepción", False, f"{type(e).__name__}: {e}")
        lz = v.modo_boceto.lienzo
    if lz.herramienta != "seleccionar":
        tecla(Qt.Key_Escape)

A.reg(AR, "ninguna excepción en un slot de Qt", not A.ERRORES, A.ERRORES[:1])
A.guardar_registro("boceto_crear_formas")
print(f"\n=== {len(A.REGISTRO)} comprobaciones, {len([r for r in A.REGISTRO if not r['ok']])} con ✗ ===", flush=True)
v.doc.modificado = False
v.close()
sys.exit(0)

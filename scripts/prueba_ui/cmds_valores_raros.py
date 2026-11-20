# -*- coding: utf-8 -*-
"""PRUEBA-CMDS (E7), valores raros: Seleccionar por tamaño / por nombre (tecleando en el diálogo real), Seleccionar todo e
Invertir (con y sin cuerpos, con el boceto abierto), Selección en ventana y de forma libre con el mouse simulado (ventana
de 0 px, fuera de todo, con Esc a medias) y las restricciones Colineal, Concéntrica, Igual y Perpendicular con
selecciones que no corresponden, repetidas y contradictorias. Eventos simulados; nunca el cursor real."""

import arnes as A
import numpy as np
from omnicad import api
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

AR = "CMDS·RAROS"
s = api.Sesion()


def L(n, **a):
    r = api.llamar(s, n, a)
    assert r["ok"], (n, a, r)
    return r["result"]


L("create_box", length=10, width=10, height=10, name="Caja chica")
L("create_box", length=50, width=50, height=50, name="Caja grande")
L("create_cylinder", radius=5, height=5, name="Cilindro")
L("create_sketch", plane="XY", name="R")
LIN = {}
for k, (a, b, c, d) in {"L1": (0, 0, 20, 0), "L2": (30, 0, 40, 10), "L3": (50, 0, 50, 20)}.items():
    LIN[k] = L("draw_line", sketch="R", start_x=a, start_y=b, end_x=c, end_y=d)["entities"][0]["id"]
CIR = {"C1": L("draw_circle", sketch="R", center_x=0, center_y=40, radius=5)["entities"][0]["id"],
       "C2": L("draw_circle", sketch="R", center_x=20, center_y=40, radius=8)["entities"][0]["id"]}
app, v = A.iniciar(s.doc, 1280, 720)
A.esperar(500)
MS = []
CUERPOS = {c.id: v.nombre_cuerpo(c) for c in v.doc.estado_final.cuerpos.values()}


def activar(clave):
    v.activateWindow()
    A.esperar(150)
    v.acciones[clave].trigger()
    A.esperar(500)


from PySide6.QtWidgets import QInputDialog  # noqa: E402


def _num(txt):
    """Lo que devuelve el spin del diálogo al teclear `txt`: coma = punto, fuera de rango se limita a 0–1e6, texto no numérico no acepta."""
    try:
        return min(max(float(txt.replace(",", ".")), 0.0), 1e6), True
    except ValueError:
        return 0.0, False


def con_dialogo(texto, clave):
    QInputDialog.getText = staticmethod(lambda *a, **k: ("" if texto is None else texto, texto is not None))
    activar(clave)


def elegidos():
    return sorted(CUERPOS.get(h["ref"].get("cuerpo"), "?") for h in v.seleccion if h["tipo"] == "cuerpo")


def limpiar():
    v._seleccionar([])
    A.esperar(120)


def tamano(minimo, maximo):
    limpiar()
    vals = iter((_num(minimo), _num(maximo)))
    QInputDialog.getDouble = staticmethod(lambda *a, **k: next(vals))
    activar("seleccion_tamano")
    return elegidos()


def seleccion_cuerpos():
    # diagonal: chica 17,3 · cilindro 15 · grande 86,6
    for mn, mx, esp, nombre in (("0", "1000", ["Caja chica", "Caja grande", "Cilindro"], "todo"),
                                ("50", "1000", ["Caja grande"], "solo la grande"),
                                ("0", "16", ["Cilindro"], "solo el cilindro (diagonal 15)"),
                                ("100", "10", [], "mínimo > máximo (nada, sin romper)"),
                                ("-5", "1000", ["Caja chica", "Caja grande", "Cilindro"], "mínimo negativo (se limita a 0)"),
                                ("0", "1e9", None, "máximo enorme 1e9"),
                                ("abc", "1000", None, "mínimo «abc»"),
                                ("0,5", "1000", None, "coma decimal"),
                                ("", "", None, "vacíos"),
                                ("17.32", "17.33", ["Caja chica"], "ventana estrecha de la diagonal 17,32")):
        try:
            r = tamano(mn, mx)
        except Exception as e:  # noqa: BLE001
            A.reg(AR, f"tamaño «{nombre}»: sin excepción", False, f"{type(e).__name__}: {e}"); continue
        ok = (r == sorted(esp)) if esp is not None else not A.ERRORES
        A.reg(AR, f"Seleccionar por tamaño, {nombre}", ok, f"eligió {r}; errores {A.ERRORES[:1]}")
        if QApplication.activeModalWidget() is not None:
            A.reg(AR, f"tamaño «{nombre}»: no deja un diálogo abierto", False, "")
            QTest.keyClick(QApplication.activeModalWidget(), Qt.Key_Escape)

    for texto, esp, nombre in (("caja", ["Caja chica", "Caja grande"], "«caja»"), ("CAJA", ["Caja chica", "Caja grande"], "MAYÚSCULAS"),
                               ("  chica  ", ["Caja chica"], "con espacios alrededor (Fusion ignora)"), ("*", ["Caja chica", "Caja grande", "Cilindro"], "«*» = todos"),
                               ("", ["Caja chica", "Caja grande", "Cilindro"], "vacío (todos)"),
                               ("zzz", [], "sin coincidencias"), ("[a-z]+", [], "símbolos de regex tomados literal"),
                               ("%$#", [], "símbolos"), ("ñandú", [], "unicode"), ("c*a", ["Caja chica", "Caja grande"], "«*» en el medio"),
                               ("x" * 5000, [], "5000 letras")):
        limpiar()
        con_dialogo(texto, "seleccion_nombre")
        A.esperar(300)
        r = elegidos()
        A.reg(AR, f"Seleccionar por nombre, {nombre}", r == sorted(esp), f"eligió {r}; errores {A.ERRORES[:1]}")
    limpiar()
    con_dialogo(None, "seleccion_nombre")
    A.reg(AR, "por nombre: Esc no elige nada ni rompe", not v.seleccion and QApplication.activeModalWidget() is None, elegidos())


def todo_invertir():
    limpiar()
    activar("seleccionar_todo")
    A.reg(AR, "Seleccionar todo elige los 3 cuerpos", len(elegidos()) == 3, elegidos())
    activar("invertir_seleccion")
    A.reg(AR, "Invertir con todo elegido deja nada", elegidos() == [], elegidos())
    activar("invertir_seleccion")
    A.reg(AR, "Invertir sin nada elegido elige todo", len(elegidos()) == 3, elegidos())
    limpiar()
    v._seleccionar(v._hits_cuerpos([next(i for i, n in CUERPOS.items() if n == "Cilindro")]))
    A.esperar(150)
    activar("invertir_seleccion"); a = elegidos()
    activar("invertir_seleccion")
    A.reg(AR, "Invertir dos veces vuelve a la selección original", a == ["Caja chica", "Caja grande"] and elegidos() == ["Cilindro"], (a, elegidos()))


def pt3(x, y, z=0.0):
    return v.visor.mapFromGlobal(v.visor.mapToGlobal(v.visor.proyectar(np.array((x, y, z), float)).toPoint()))


def arrastre(pts, modo):
    limpiar()
    v.visor.set_modo(modo)
    A.esperar(120)
    QTest.mousePress(v.visor, Qt.LeftButton, Qt.NoModifier, pts[0]); A.esperar(60)
    for p in pts[1:]:
        # QTest.mouseMove no manda el botón apretado: el lazo no sumaba puntos. Evento con LeftButton, como un arrastre real.
        ev = QMouseEvent(QEvent.MouseMove, QPointF(p), v.visor.mapToGlobal(QPointF(p)), Qt.NoButton, Qt.LeftButton, Qt.NoModifier)
        QApplication.sendEvent(v.visor, ev); A.esperar(40)
    QTest.mouseRelease(v.visor, Qt.LeftButton, Qt.NoModifier, pts[-1]); A.esperar(300)
    r = elegidos()
    v.visor.set_modo(None)
    return r


def ventana_libre():
    from PySide6.QtCore import QPoint
    r0 = v.visor.rect()
    vacio = QPoint(5, 5)
    A.reg(AR, "sel_ventana: arrastre de 0 px no elige nada ni rompe", arrastre([vacio, vacio], "sel_ventana") == [] and not A.ERRORES, A.ERRORES[:1])
    A.reg(AR, "sel_ventana: ventana en el vacío no elige nada", arrastre([vacio, vacio + QPoint(20, 20)], "sel_ventana") == [], "")
    todo = arrastre([QPoint(2, 2), QPoint(r0.width() - 2, r0.height() - 2)], "sel_ventana")
    A.reg(AR, "sel_ventana: ventana de toda la vista elige los cuerpos visibles", len(todo) >= 2, todo)
    tri = [QPoint(2, 2), QPoint(r0.width() - 2, 2), QPoint(r0.width() - 2, r0.height() - 2), QPoint(2, r0.height() - 2), QPoint(2, 2)]
    lib = arrastre(tri, "sel_libre")
    A.reg(AR, "sel_libre: lazo grande elige cuerpos", len(lib) >= 1, lib)
    fuera = arrastre([QPoint(-500, -500), QPoint(r0.width() + 500, r0.height() + 500)], "sel_ventana")
    A.reg(AR, "sel_ventana: arrastrar hasta fuera de la ventana no rompe", not A.ERRORES, (fuera, A.ERRORES[:1]))
    # Esc a medias
    limpiar()
    v.visor.set_modo("sel_ventana"); QTest.mousePress(v.visor, Qt.LeftButton, Qt.NoModifier, QPoint(5, 5)); QTest.mouseMove(v.visor, QPoint(300, 300)); A.esperar(80)
    QTest.keyClick(v.visor, Qt.Key_Escape); A.esperar(150)
    QTest.mouseRelease(v.visor, Qt.LeftButton, Qt.NoModifier, QPoint(300, 300)); A.esperar(250)
    A.reg(AR, "sel_ventana: Esc con el botón apretado no deja nada elegido por la mitad", not A.ERRORES, elegidos())
    v.visor.set_modo(None)
    c = r0.center()
    A.reg(AR, "sel_libre: 2 puntos (menos de 3) no elige nada ni rompe", arrastre([c, c + QPoint(30, 0)], "sel_libre") == [] and not A.ERRORES, A.ERRORES[:1])
    lazo8 = [QPoint(10, 10), QPoint(400, 300), QPoint(10, 300), QPoint(400, 10), QPoint(10, 10)]
    A.reg(AR, "sel_libre: lazo que se cruza a sí mismo no rompe", arrastre(lazo8, "sel_libre") is not None and not A.ERRORES, A.ERRORES[:1])
    A.foto(v, "cmds_sel_libre")


def restricciones():
    v.editar_operacion(s.paso("R").id)
    A.esperar(500)
    lz = v.modo_boceto.lienzo
    lz.mensaje.connect(MS.append)
    lz.visor.encuadrar(); A.esperar(200)

    def n():
        return len(lz.b.restricciones)

    def aplicar(clave, ids, nombre, esperar_ok):
        while len(lz.historial) > 0:
            lz.deshacer()
        lz.set_herramienta("seleccionar"); lz.seleccion = list(ids); lz.update(); A.esperar(80)
        n0, ms0 = n(), len(MS)
        try:
            v.modo_boceto.acciones[clave].trigger(); A.esperar(350)
        except Exception as e:  # noqa: BLE001
            A.reg(AR, f"{clave} «{nombre}»: sin excepción", False, repr(e)); return
        nuevas = n() - n0
        msg = MS[ms0:]
        buena = (nuevas > 0) if esperar_ok else (nuevas == 0 and bool(msg))
        A.reg(AR, f"{clave} «{nombre}»: {'aplica' if esperar_ok else 'rechaza con mensaje y sin cambiar nada'}", buena,
              f"+{nuevas} restricciones; mensajes {msg[-2:]}; conflicto={getattr(lz.resultado, 'conflictos', None)}")
        lz.set_herramienta("seleccionar")
        return nuevas

    L1, L2, L3, C1, C2 = LIN["L1"], LIN["L2"], LIN["L3"], CIR["C1"], CIR["C2"]
    for clave, buenos, malos in (("sk_r_colineal", [("L1+L2", [L1, L2])], [("L1+C1", [L1, C1]), ("C1+C2", [C1, C2]), ("una sola", [L1]), ("3 líneas", [L1, L2, L3])]),
                                 ("sk_r_concentrica", [("C1+C2", [C1, C2])], [("L1+L2", [L1, L2]), ("L1+C1", [L1, C1]), ("una sola", [C1])]),
                                 ("sk_r_igual", [("L1+L2", [L1, L2]), ("C1+C2", [C1, C2])], [("L1+C1", [L1, C1]), ("una sola", [L1])]),
                                 ("sk_r_perpendicular", [("L1+L2", [L1, L2])], [("C1+C2", [C1, C2]), ("L1+C1", [L1, C1]), ("una sola", [L1])])):
        for nombre, ids in buenos:
            aplicar(clave, ids, nombre, True)
        for nombre, ids in malos:
            aplicar(clave, ids, nombre, False)
        # sin nada elegido: la herramienta se arma y espera clics (no rompe)
        aplicar(clave, [], "nada elegido (espera clics)", False) if False else None
    # repetida y contradictoria
    while len(lz.historial) > 0:
        lz.deshacer()
    lz.seleccion = [L1, L2]; v.modo_boceto.acciones["sk_r_perpendicular"].trigger(); A.esperar(300)
    n1 = n()
    lz.set_herramienta("seleccionar"); lz.seleccion = [L1, L2]; v.modo_boceto.acciones["sk_r_perpendicular"].trigger(); A.esperar(300)
    A.reg(AR, "perpendicular dos veces sobre el mismo par no duplica la restricción", n() <= n1 + 0 or "redund" in " ".join(MS[-3:]).lower(), f"{n1}→{n()}; {MS[-2:]}")
    lz.set_herramienta("seleccionar"); lz.seleccion = [L1, L2]; v.modo_boceto.acciones["sk_r_igual"].trigger(); A.esperar(300)
    lz.set_herramienta("seleccionar"); lz.seleccion = [L1, L2]
    try:
        v.modo_boceto.acciones["sk_r_colineal"].trigger(); A.esperar(350)   # perpendicular + colineal: contradictorio
    except Exception as e:  # noqa: BLE001
        A.reg(AR, "colineal sobre un par perpendicular: sin excepción", False, repr(e))
    res = lz.resultado
    A.reg(AR, "perpendicular + colineal: el boceto avisa conflicto (rojo) o no deja aplicarla", bool(getattr(res, "conflictos", None)) or any("conflict" in m.lower() or "contradic" in m.lower() or "redund" in m.lower() for m in MS[-4:]), f"{MS[-3:]}; {getattr(res, 'conflictos', None)}")
    A.foto(v, "cmds_restricciones")
    lz.deshacer(); A.esperar(200)
    A.reg(AR, "deshacer tras el conflicto vuelve a un boceto resoluble", not getattr(lz.resultado, "conflictos", None), getattr(lz.resultado, "conflictos", None))
    v.modo_boceto.terminar(); A.esperar(300)


A.correr(AR + " tamaño/nombre", seleccion_cuerpos)
A.correr(AR + " todo/invertir", todo_invertir)
A.correr(AR + " ventana/libre", ventana_libre)
A.correr(AR + " restricciones", restricciones)
A.reg(AR, "ninguna excepción en un slot de Qt", not A.ERRORES, A.ERRORES[:1])
A.guardar_registro("cmds_valores_raros")

# -*- coding: utf-8 -*-
"""BOCETO › Sketch inteligente en la ventana real, como Fusion: guías de alineación al mover el ratón, punto medio,
intersección, vertical/horizontal con alineación, Ctrl apaga, Espacio alterna, Flecha arriba bloquea, restricciones que
quedan al confirmar, deshacer y rehacer, guardar y reabrir, preferencias y ventana chica (1024x640 y 800x520)."""
import sys

import arnes as A
from omnicad import api
from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

AR = "BOCETO·INFERENCIAS"
print("[omnicad]", api.__file__, flush=True)
s = api.Sesion()


def L(nombre, **a):
    r = api.llamar(s, nombre, a)
    assert r["ok"], (nombre, a, r)
    return r["result"]


L("create_sketch", name="S", plane="XY")
for a, b in (((-75, 0), (0, 0)), ((0, 0), (0, 75)), ((0, 75), (-75, 0))):
    L("draw_line", sketch="S", start_x=a[0], start_y=a[1], end_x=b[0], end_y=b[1])
L("draw_line", sketch="S", start_x=100, start_y=-20, end_x=140, end_y=20)
L("draw_line", sketch="S", start_x=100, start_y=20, end_x=140, end_y=-20)       # se cruzan en (120, 0)
app, v = A.iniciar(s.doc)
v.editar_operacion(s.paso("S").id)
A.esperar(500)
lz = v.modo_boceto.lienzo
A.reg(AR, "entrar al boceto", v.modo_boceto.activo and lz is not None, "")
v.visor.encuadrar()
A.esperar(300)


def mover(x, y, mods=Qt.NoModifier):
    pos = lz.a_px(x, y)
    QApplication.sendEvent(lz, QMouseEvent(QEvent.MouseMove, pos, pos, Qt.NoButton, Qt.NoButton, mods))
    A.esperar(40)


def clic(x, y, mods=Qt.NoModifier):
    mover(x, y, mods)
    pos = lz.a_px(x, y)
    for tipo, botones in ((QEvent.MouseButtonPress, Qt.LeftButton), (QEvent.MouseButtonRelease, Qt.NoButton)):
        QApplication.sendEvent(lz, QMouseEvent(tipo, pos, pos, Qt.LeftButton, botones, mods))
    A.esperar(60)


def tecla(k, mods=Qt.NoModifier):
    QTest.keyClick(lz, k, mods)
    A.esperar(40)


def restricciones():
    return sorted(c["type"] for c in L("get_sketch", sketch="S").get("constraints", []))


def volver():
    """Termina la operación en curso y deshace lo creado, para que cada caso parta del triángulo solo."""
    lz.cancelar()
    while lz.historial:
        lz.deshacer()


def tipos_locales():
    return sorted(r.tipo for r in lz.b.restricciones.values())


def inf():
    return lz.inf_actual.tipo if lz.inf_actual is not None else None


# 1. alineación horizontal con el vértice (0, 75): guía temporal, el extremo cae exacto y no queda restricción
antes = restricciones()
lz.set_herramienta("linea")
clic(40, 10)
mover(60.1, 75.2)
A.reg(AR, "hover cerca de la altura del vértice: aparece la guía de alineación", inf() == "alineado_h", str(inf()))
A.foto(v, "inferencias_01_alineacion")
clic(60.1, 75.2)
linea = lz.b.curvas[lz._ultima_linea]
fin = lz.b.coords(linea.p2)
A.reg(AR, "el clic confirma el extremo exactamente a la altura del vértice", abs(fin[1] - 75) < 1e-6 and abs(fin[0] - 60.1) < 1e-6, str(fin))
A.reg(AR, "una alineación no deja restricciones (es solo guía)", [r.tipo for r in lz.b.restricciones.values() if linea.id in r.entidades] == [], str(restricciones()))
volver()

# 2. vertical desde la base alineada con otro punto: queda solo la restricción vertical
clic(40, 10)
mover(40.2, 75.2)
A.reg(AR, "vertical + alineado con el vértice", inf() == "vertical" and lz.inferencia == "vertical", str(inf()))
A.foto(v, "inferencias_02_vertical")
clic(40.2, 75.2)
linea = lz.b.curvas[lz._ultima_linea]
tipos = [r.tipo for r in lz.b.restricciones.values() if linea.id in r.entidades]
A.reg(AR, "la línea queda vertical y termina a la altura del vértice", tipos == ["vertical"] and abs(lz.b.coords(linea.p2)[1] - 75) < 1e-6, str(tipos))
volver()

# 3. punto medio de la hipotenusa
clic(30, -30)
mover(-37.6, 37.4)
A.reg(AR, "punto medio de la hipotenusa", inf() == "punto_medio", str(inf()))
A.foto(v, "inferencias_03_medio")
clic(-37.6, 37.4)
linea = lz.b.curvas[lz._ultima_linea]
A.reg(AR, "el clic en el medio deja la restricción de punto medio",
      any(r.tipo == "punto_medio" and linea.p2 in r.entidades for r in lz.b.restricciones.values()),
      str(restricciones()))
volver()

# 4. intersección real de dos líneas
clic(160, 60)
mover(120.2, 0.2)
A.reg(AR, "intersección de dos líneas", inf() in ("interseccion",), str(inf()))
A.foto(v, "inferencias_04_interseccion")
clic(120.2, 0.2)
linea = lz.b.curvas[lz._ultima_linea]
destinos = {r.entidades[1] for r in lz.b.restricciones.values() if r.tipo == "coincidente" and r.entidades[0] == linea.p2}
A.reg(AR, "el extremo queda coincidente con las dos líneas", len(destinos) == 2, str(destinos))
volver()

# 5. Ctrl apaga las ayudas; sin Ctrl vuelven
clic(40, 10)
mover(60.1, 75.2, Qt.ControlModifier)
A.reg(AR, "con Ctrl no hay ayuda", inf() is None, str(inf()))
mover(60.1, 75.2)
A.reg(AR, "sin Ctrl vuelve la ayuda", inf() is not None, str(inf()))

# 6. bloquear con Flecha arriba y soltar
tecla(Qt.Key_Up)
mover(90, 110)
A.reg(AR, "bloqueada: el cursor sigue la guía horizontal", abs(lz.cursor[1] - 75) < 1e-6 and abs(lz.cursor[0] - 90) < 1e-6, str(lz.cursor))
tecla(Qt.Key_Up)
mover(90, 110)
A.reg(AR, "al soltar el bloqueo el cursor es libre", abs(lz.cursor[1] - 110) < 1e-6, str(lz.cursor))
volver()

# 7. Espacio alterna entre ayudas ambiguas (el punto medio coincide con la intersección)
clic(160, 60)
mover(120.1, 0.1)
n = len(lz.inf_lista)
primera = lz.inf_actual
tecla(Qt.Key_Space)
A.reg(AR, "Espacio cambia a otra ayuda cuando hay varias", n < 2 or lz.inf_actual != primera,
      f"{n} ayudas {[i.tipo for i in lz.inf_lista]}, alt={lz._inf_alt}, activa {lz.inf_actual.tipo}, foco {lz.hasFocus()}")
volver()

# 8. deshacer y rehacer con Ctrl+Z / Ctrl+Y
estado = lz.b.a_dict()
clic(40, 10)
clic(40.2, 75.2)
creado = lz.b.a_dict()
tecla(Qt.Key_Z, Qt.ControlModifier)
A.reg(AR, "Ctrl+Z deshace la línea con su restricción", lz.b.a_dict() == estado)
tecla(Qt.Key_Y, Qt.ControlModifier)
A.reg(AR, "Ctrl+Y la rehace igual", lz.b.a_dict() == creado)
volver()

# 9. preferencias: apagar las inferencias desde las preferencias de la aplicación
lz.set_herramienta("linea")
clic(40, 10)
v.prefs["boceto/inferencias"] = False
v.aplicar_preferencias()
mover(60.1, 75.2)
A.reg(AR, "con la preferencia apagada no hay ayuda", not lz.ajustes_inf["inferencias"] and inf() is None, str(lz.ajustes_inf))
v.prefs["boceto/inferencias"] = True
v.aplicar_preferencias()
mover(60.1, 75.2)
A.reg(AR, "al volver a encender la preferencia vuelve la ayuda al instante", inf() == "alineado_h", str(inf()))
volver()

# 10. ventana chica: la ayuda sigue funcionando y el panel entra
for ancho, alto in ((1024, 640), (800, 520)):
    v.resize(ancho, alto)
    A.esperar(400)
    v.visor.encuadrar()
    A.esperar(250)
    lz.set_herramienta("linea")
    clic(40, 10)
    mover(60.1, 75.2)
    visible = lz.inf_actual is not None
    A.reg(AR, f"{ancho}x{alto}: la guía de alineación aparece", visible and lz.isVisible(), str(inf()))
    A.foto(v, f"inferencias_10_{ancho}x{alto}")
    volver()

# 11. guardar y reabrir: las restricciones confirmadas siguen
lz.set_herramienta("linea")
clic(40, 10)
clic(40.2, 75.2)
lz.cancelar()
confirmadas = tipos_locales()
v.modo_boceto.terminar()
A.esperar(400)
v.editar_operacion(s.paso("S").id)
A.esperar(500)
lz = v.modo_boceto.lienzo
A.reg(AR, "reabrir el boceto conserva la restricción vertical", tipos_locales() == confirmadas and "vertical" in confirmadas, f"{confirmadas} -> {tipos_locales()}")
v.modo_boceto.terminar()

A.guardar_registro("u2d_inferencias")
fallas = [r for r in A.REGISTRO if not r["ok"]]
print(f"\n=== {len(A.REGISTRO)} comprobaciones, {len(fallas)} con ✗ ===")
for r in fallas:
    print("✗", r)
v.close()
sys.exit(0)

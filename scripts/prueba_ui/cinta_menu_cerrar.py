# -*- coding: utf-8 -*-
"""B-774 (E7): al cerrar el menú de CREAR del boceto, ¿hay algún destello? Abre el menú con un clic simulado en el botón de
grupo y lo cierra de 3 formas (Esc, clic fuera, elegir un ítem); anota todo Show/Hide/Opacidad de ventanas emergentes y los
fotogramas de pintura del menú tras cerrarse. Eventos simulados; nunca el cursor real."""
import arnes as A
from omnicad import api
from PySide6.QtCore import QEvent, QObject, QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QMenu, QToolButton

s = api.Sesion()
api.llamar(s, "create_sketch", {"plane": "XY", "name": "B"})
app, v = A.iniciar(s.doc, 1280, 720)
A.esperar(500)
r = api.llamar(s, "draw_line", {"sketch": "B", "start_x": 0, "start_y": 0, "end_x": 10, "end_y": 0})
v.editar_boceto("B") if hasattr(v, "editar_boceto") else None
A.esperar(500)
EV = []


class Esp(QObject):
    def eventFilter(self, o, e):
        if isinstance(o, QMenu) and e.type() in (QEvent.Show, QEvent.Hide, QEvent.Paint, QEvent.WindowOpacityChange if hasattr(QEvent, "WindowOpacityChange") else QEvent.Show):
            EV.append((e.type().name, o.windowOpacity(), bool(o.isVisible())))
        return False


esp = Esp()
app.installEventFilter(esp)
botones = [b for b in v.findChildren(QToolButton) if b.menu() is not None and b.isVisible()]
crear = [b for b in botones if b.text().startswith("CREAR")]
A.reg("B-774", f"botón CREAR encontrado ({len(crear)})", bool(crear))
if not crear:
    A.guardar_registro("cinta_menu_cerrar")
    raise SystemExit(1)
b = crear[0]
m = b.menu()
for modo in ("esc", "fuera", "item"):
    EV.clear()
    m.popup(b.mapToGlobal(QPoint(0, b.height())))
    A.esperar(200)
    n_abrir = len(EV)
    if modo == "esc":
        QTest.keyClick(m, Qt.Key_Escape)
    elif modo == "fuera":
        m.close()      # un clic simulado a otro widget no cierra un popup: Qt lo cierra con el agarre del mouse real
    else:
        a = [x for x in m.actions() if x.isEnabled() and not x.isSeparator() and not x.menu()]
        m.setActiveAction(a[0])
        QTest.keyClick(m, Qt.Key_Return)
    A.esperar(300)
    tipos = [e[0] for e in EV[n_abrir:]]
    ops = {round(e[1], 2) for e in EV}
    A.reg("B-774", f"cerrar por {modo}: visible={m.isVisible()} eventos tras abrir={tipos[:8]} opacidades={sorted(ops)}",
          not m.isVisible() and ops <= {1.0} and tipos.count("Show") == 0)
    if v.modo_comando if hasattr(v, "modo_comando") else False:
        pass
A.guardar_registro("cinta_menu_cerrar")

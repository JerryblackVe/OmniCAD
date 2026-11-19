# -*- coding: utf-8 -*-
"""BOCETO · PRUEBA-CMDS parte 2, grupo A (E7): Recortar, Alargar, Partir, Curva de fusión, Soltar desfase, Desglosar texto,
Restringir automáticamente (y desde referencia). Botón real de la cinta, clics simulados al Lienzo, Esc, Enter, Ctrl+Z,
casos raros (clic en el vacío, en lo que no corresponde, dos veces la misma curva, sin intersección). Contra Fusion:
Trim / Extend / Break / Blend Curve / Release Offset / Explode Text / AutoConstrain. Eventos simulados; nunca el cursor real."""
import math
import sys

import arnes as A
from omnicad import api
from PySide6.QtCore import Qt, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QToolButton

AR = "BOCETO·CORTES"
s = api.Sesion()


def L(nombre, **a):
    r = api.llamar(s, nombre, a)
    assert r["ok"], (nombre, a, r)
    return r["result"]


def ids(r):
    return [e["id"] for e in r["entities"]]


L("create_box", length=40, width=20, height=5, name="Caja")
for n in ("Rec", "Alar", "Part", "Fus", "Des", "Tex", "Auto", "Vacio"):
    L("create_sketch", name=n, plane="XY")
# Recortar: horizontal cruzada por una vertical y por un círculo; una línea suelta sin cruces
L("draw_line", sketch="Rec", start_x=0, start_y=0, end_x=60, end_y=0)
L("draw_line", sketch="Rec", start_x=20, start_y=-15, end_x=20, end_y=15)
L("draw_line", sketch="Rec", start_x=0, start_y=30, end_x=60, end_y=30)           # suelta
# Alargar: horizontal que termina antes de una pared; otra que no llega a nada; un círculo
L("draw_line", sketch="Alar", start_x=0, start_y=0, end_x=30, end_y=0)
L("draw_line", sketch="Alar", start_x=50, start_y=-20, end_x=50, end_y=20)
L("draw_line", sketch="Alar", start_x=0, start_y=30, end_x=20, end_y=30)           # no llega a nada
L("draw_circle", sketch="Alar", center_x=20, center_y=-30, radius=5)
# Partir: dos líneas que se cruzan y una suelta
L("draw_line", sketch="Part", start_x=0, start_y=0, end_x=60, end_y=0)
L("draw_line", sketch="Part", start_x=30, start_y=-15, end_x=30, end_y=15)
L("draw_line", sketch="Part", start_x=0, start_y=30, end_x=60, end_y=30)
# Fusión: dos líneas separadas; dos colineales
L("draw_line", sketch="Fus", start_x=0, start_y=0, end_x=20, end_y=0)
L("draw_line", sketch="Fus", start_x=40, start_y=20, end_x=60, end_y=20)
L("draw_line", sketch="Fus", start_x=0, start_y=-30, end_x=20, end_y=-30)
L("draw_line", sketch="Fus", start_x=40, start_y=-30, end_x=60, end_y=-30)
# Desfase: círculo + su copia asociada; una línea común
CIRC = ids(L("draw_circle", sketch="Des", center_x=0, center_y=0, radius=10))[0]
L("draw_line", sketch="Des", start_x=40, start_y=0, end_x=60, end_y=0)
L("offset_sketch_curves", sketch="Des", distance=4, entity=CIRC, side_x=0, side_y=18)
# Texto
L("add_text", sketch="Tex", text="OK", x=0, y=0, height=12)
L("draw_line", sketch="Tex", start_x=40, start_y=0, end_x=60, end_y=0)
# AutoConstrain: rectángulo suelto
L("draw_rectangle", sketch="Auto", center_x=0, center_y=0, width=30, height=20)
ID = {n: s.paso(n).id for n in ("Rec", "Alar", "Part", "Fus", "Des", "Tex", "Auto", "Vacio")}
app, v = A.iniciar(s.doc)
A.esperar(400)
lz = None
MS = []


def encuadrar(x, y, span=90):
    lz.visor.objetivo = lz.plano.a_3d(x, y)
    lz.visor.distancia = span / 2 / math.sin(math.radians(lz.visor.fov) / 2) * 1.3
    lz.visor.update()
    lz.update()
    A.esperar(150)


def entrar(nombre, centro=(30, 0), span=110):
    global lz
    v.editar_operacion(ID[nombre])
    A.esperar(500)
    lz = v.modo_boceto.lienzo
    MS.clear()
    try:
        lz.mensaje.disconnect(MS.append)
    except (RuntimeError, TypeError):
        pass
    lz.mensaje.connect(MS.append)
    encuadrar(*centro, span)
    A.activar(v)
    A.esperar(150)


def tecla(k, mod=Qt.NoModifier):
    A.activar(v)
    A.esperar(150)                            # bajo xvfb la primera tecla tras activar se pierde sin esta pausa
    QTest.keyClick(lz, k, mod)
    A.esperar(150)


def salir():
    if lz.entrada is not None:
        tecla(Qt.Key_Escape)
    lz.set_herramienta("seleccionar")
    lz.seleccion = []
    v.modo_boceto.terminar()
    A.esperar(400)


def px(x, y):
    return lz.a_px(x, y).toPoint()


def clic(x, y):
    QTest.mouseClick(lz, Qt.LeftButton, Qt.NoModifier, px(x, y))
    A.esperar(120)


def pulsar(clave):
    acc = v.modo_boceto.acciones[clave]
    try:
        b = next(b for b in v.cinta.findChildren(QToolButton) if b.defaultAction() is acc and b.isVisible())
        QTest.mouseClick(b, Qt.LeftButton)
    except StopIteration:
        acc.trigger()
    A.esperar(200)


def estado():
    return lz.b.a_dict()


def n_lineas():
    return sum(1 for c in lz.b.curvas.values() if c.tipo == "linea")


def sin_error(titulo):
    A.reg(AR, f"{titulo}: sin excepción en slots de Qt", not A.ERRORES, A.ERRORES[:1])
    A.ERRORES.clear()


# ============================================================ RECORTAR
entrar("Rec")
pulsar("sk_recortar")
A.reg(AR, "Recortar: el botón activa la herramienta", lz.herramienta == "recortar", lz.herramienta)
e0 = estado()
n0 = n_lineas()
clic(40, 15)                                 # vacío
A.reg(AR, "Recortar: clic en el vacío no cambia nada ni rompe", estado() == e0, f"{MS[-1:]}")
clic(40, 30)                                 # línea suelta sin intersecciones: Fusion la borra entera
A.reg(AR, "Recortar: clic en una línea sin cruces la quita entera (Fusion), 1 línea menos", n_lineas() == n0 - 1, f"{n0}→{n_lineas()} {MS[-1:]}")
tecla(Qt.Key_Z, Qt.ControlModifier)
A.reg(AR, "Recortar: Ctrl+Z devuelve la línea suelta", estado() == e0, "")
clic(40, 0)                                  # tramo derecho de la horizontal
A.reg(AR, "Recortar: clic en el tramo derecho de la horizontal lo quita hasta el cruce", estado() != e0 and lz.resultado.ok, f"{MS[-1:]}")
A.foto(v, "rec_1")
tecla(Qt.Key_Z, Qt.ControlModifier)
A.reg(AR, "Recortar: Ctrl+Z vuelve al boceto original", estado() == e0, "")
tecla(Qt.Key_Escape)
A.reg(AR, "Recortar: Esc deja la herramienta (vuelve a seleccionar)", lz.herramienta != "recortar", lz.herramienta)
pulsar("sk_recortar")
clic(20, 8)                                  # tramo de la vertical, justo sobre el cruce de borde
clic(20, 8)                                  # otra vez en el mismo lugar (ya recortado): no debe romper
sin_error("Recortar (doble clic en el mismo tramo)")
salir()

# ============================================================ ALARGAR
entrar("Alar")
pulsar("sk_alargar")
A.reg(AR, "Alargar: el botón activa la herramienta", lz.herramienta == "alargar", lz.herramienta)
e0 = estado()
clic(20, 30)                                 # línea que no llega a nada, cerca de su extremo
A.reg(AR, "Alargar: línea sin nada adelante no cambia y avisa", estado() == e0 and bool(MS), f"{MS[-1:]}")
clic(25, -30)                                # borde del círculo (no se alarga)
A.reg(AR, "Alargar: clic en un círculo no cambia nada y avisa", estado() == e0, f"{MS[-1:]}")
clic(60, 10)                                 # vacío
A.reg(AR, "Alargar: clic en el vacío no cambia nada", estado() == e0, "")
MS.clear()
clic(29, 0)                                  # extremo derecho de la horizontal
xs = sorted(round(max(x for x, _ in lz.b._extremos_linea(c.id)), 3) for c in lz.b.curvas.values() if c.tipo == "linea")
A.reg(AR, "Alargar: clic cerca del extremo lleva la línea hasta la pared en x=50", 50.0 in xs and estado() != e0, f"x máx {xs} {MS[-1:]}")
A.foto(v, "alar_1")
tecla(Qt.Key_Z, Qt.ControlModifier)
A.reg(AR, "Alargar: Ctrl+Z vuelve al original", estado() == e0, "")
tecla(Qt.Key_Escape)
sin_error("Alargar")
salir()

# ============================================================ PARTIR
entrar("Part")
pulsar("sk_partir")
A.reg(AR, "Partir: el botón activa la herramienta", lz.herramienta == "partir", lz.herramienta)
e0, n0 = estado(), n_lineas()
clic(40, 30)
A.reg(AR, "Partir: línea suelta sin cruces no cambia y avisa", estado() == e0 and bool(MS), f"{MS[-1:]}")
clic(60, 12)
A.reg(AR, "Partir: clic en el vacío no cambia nada", estado() == e0, "")
clic(10, 0)
A.reg(AR, "Partir: clic en la horizontal la parte en el cruce (una línea más)", n_lineas() == n0 + 1, f"{n0}→{n_lineas()} {MS[-1:]}")
A.foto(v, "part_1")
tecla(Qt.Key_Z, Qt.ControlModifier)
A.reg(AR, "Partir: Ctrl+Z vuelve al original", estado() == e0, f"{n_lineas()} líneas")
sin_error("Partir")
tecla(Qt.Key_Escape)
salir()

# ============================================================ CURVA DE FUSIÓN
entrar("Fus")
pulsar("sk_curva_fusion")
A.reg(AR, "Curva de fusión: el botón activa la herramienta", lz.herramienta == "curva_fusion", lz.herramienta)
e0 = estado()
clic(19, 0)
clic(19, 0)                                  # la misma curva dos veces
A.reg(AR, "Curva de fusión: elegir la misma curva dos veces no crea nada (ni rompe)", estado() == e0, f"{MS[-1:]}")
sin_error("Curva de fusión (misma curva dos veces)")
tecla(Qt.Key_Escape)
pulsar("sk_curva_fusion")
clic(19, 0)
tecla(Qt.Key_Escape)
A.reg(AR, "Curva de fusión: Esc a mitad (1 de 2 elegido) cancela y no deja nada elegido", not lz.picks and estado() == e0, f"picks={lz.picks}")
pulsar("sk_curva_fusion")
clic(19, 0)
clic(41, 20)
A.reg(AR, "Curva de fusión: dos líneas separadas generan la spline", any(c.tipo == "spline" for c in lz.b.curvas.values()),
      f"{sorted(c.tipo for c in lz.b.curvas.values())} {MS[-1:]}")
A.foto(v, "fus_1")
tecla(Qt.Key_Z, Qt.ControlModifier)
A.reg(AR, "Curva de fusión: Ctrl+Z quita la spline", estado() == e0, "")
# colineales
pulsar("sk_curva_fusion")
clic(19, -30)
clic(41, -30)
tipos = sorted(c.tipo for c in lz.b.curvas.values())
A.reg(AR, "Curva de fusión: dos líneas colineales dan spline recta o aviso, sin excepción", not A.ERRORES, f"{tipos[-2:]} {MS[-1:]}")
sin_error("Curva de fusión colineal")
tecla(Qt.Key_Escape)
salir()

# ============================================================ SOLTAR DESFASE
entrar("Des", centro=(20, 0), span=80)
e0 = estado()
lz.seleccion = []
pulsar("sk_soltar_desfase")
A.reg(AR, "Soltar desfase: sin nada elegido avisa y no cambia", estado() == e0 and bool(MS), f"{MS[-1:]}")
clic(50, 0)                                  # línea común
pulsar("sk_soltar_desfase")
A.reg(AR, "Soltar desfase: una línea que no es desfase avisa y no cambia", estado() == e0, f"{MS[-1:]}")
lz.seleccion = []
clic(0, 14)                                  # el círculo desfasado (r=14)
sel = list(lz.seleccion)


e1 = estado()
pulsar("sk_soltar_desfase")
A.reg(AR, "Soltar desfase: con la copia elegida suelta el desfase (el boceto cambia y no hay error)", sel and estado() != e1 and not A.ERRORES,
      f"elegido {sel}; {MS[-1:]}")
e1 = estado()
pulsar("sk_soltar_desfase")
A.reg(AR, "Soltar desfase: repetirlo sobre la misma curva ya suelta avisa y no cambia", estado() == e1, f"{MS[-1:]}")
e2 = estado()
tecla(Qt.Key_Z, Qt.ControlModifier)
A.reg(AR, "Soltar desfase: Ctrl+Z vuelve a tener el desfase (el boceto original)", estado() == e0 and estado() != e2, "")
sin_error("Soltar desfase")
salir()

# ============================================================ DESGLOSAR TEXTO
entrar("Tex", centro=(20, 5), span=80)
pulsar("sk_desglosar_texto")
A.reg(AR, "Desglosar texto: el botón activa la herramienta", lz.herramienta == "desglosar_texto", lz.herramienta)
e0 = estado()
clic(50, 0)                                  # una línea, no es texto
A.reg(AR, "Desglosar texto: clic en una línea (no texto) no cambia nada", estado() == e0, f"{MS[-1:]}")
clic(60, 25)
A.reg(AR, "Desglosar texto: clic en el vacío no cambia nada", estado() == e0, "")
clic(3, 4)                                   # sobre la O
textos = [c for c in lz.b.curvas.values() if c.tipo == "texto"]
A.reg(AR, "Desglosar texto: clic en el texto lo vuelve curvas fijas", not textos and len(lz.b.curvas) > 3, f"{len(lz.b.curvas)} curvas, {MS[-1:]}")
A.foto(v, "tex_1")
tecla(Qt.Key_Z, Qt.ControlModifier)
A.reg(AR, "Desglosar texto: Ctrl+Z devuelve el texto editable", estado() == e0, "")
tecla(Qt.Key_Escape)
sin_error("Desglosar texto")
salir()

# ============================================================ RESTRINGIR AUTOMÁTICAMENTE
def modal(fn):
    """Cuando aparece el diálogo (se busca entre las ventanas visibles, el modal activo no existe bajo xvfb sin foco) corre fn."""
    def _():
        w = next((w for w in QApplication.topLevelWidgets() if w.isVisible() and w.windowTitle() == "Restringir automáticamente"), None)
        if w is None:
            QTimer.singleShot(150, _)
            return
        fn(w)
    return _


from PySide6.QtCore import QEventLoop  # noqa: E402
from PySide6.QtWidgets import QDialog  # noqa: E402


def _exec_real(self):
    """El arnés deja QDialog.exec sin bloquear; el diálogo de AutoConstrain se prueba con uno de verdad."""
    lazo = QEventLoop()
    self.finished.connect(lazo.quit)
    self.setWindowModality(Qt.ApplicationModal)
    self.show()
    lazo.exec()
    return self.result()


_exec_falso = QDialog.exec
QDialog.exec = _exec_real
entrar("Auto", centro=(0, 0), span=60)
e0 = estado()
vistos = {}


def ver_y_cancelar(w):
    vistos["titulo"] = w.windowTitle()
    vistos["n"] = len(w.resultados) if hasattr(w, "resultados") else None
    QTest.keyClick(w, Qt.Key_Escape)


QTimer.singleShot(300, modal(ver_y_cancelar))
pulsar("sk_autorestringir")
A.esperar(500)
A.reg(AR, "Restringir automáticamente: abre el diálogo y Esc lo cierra sin tocar el boceto", vistos.get("titulo") and estado() == e0, str(vistos))


def aceptar(w):
    w.accept()


QTimer.singleShot(300, modal(aceptar))
pulsar("sk_autorestringir")
A.esperar(500)
A.reg(AR, "Restringir automáticamente: Aceptar aplica restricciones al boceto", len(lz.b.restricciones) > 0 and estado() != e0,
      f"{len(lz.b.restricciones)} restricciones; {MS[-1:]}")
tecla(Qt.Key_Z, Qt.ControlModifier)
_d = estado()
A.reg(AR, "Restringir automáticamente: Ctrl+Z lo deshace de una vez", _d == e0,
      [k for k in set(e0) | set(_d) if e0.get(k) != _d.get(k)])


def valores_raros(w):
    vistos["ang"] = w.tol_angulo.value()
    w.tol_angulo.setValue(0)             # tope mínimo del campo
    w.tol_distancia.setValue(1e9)
    w.tol_angulo.editingFinished.emit()
    QTimer.singleShot(200, modal(lambda x: x.reject()))


QTimer.singleShot(300, modal(valores_raros))
pulsar("sk_autorestringir")
A.esperar(800)
A.reg(AR, "Restringir automáticamente: tolerancias fuera de rango se acotan sin excepción", not A.ERRORES and estado() == e0, A.ERRORES[:1])
sin_error("Restringir automáticamente")
def botones_dialogo(w):
    from PySide6.QtWidgets import QPushButton
    for texto in ("Generar más", "Generar más", "Quitar la seleccionada", "Empezar de nuevo", "Quitar la seleccionada"):
        b = next(b for b in w.findChildren(QPushButton) if b.text() == texto)
        b.click()
        A.esperar(150)
    w.cantidad.setValue(w.cantidad.maximum())
    w.cantidad.setValue(w.cantidad.minimum())
    w.datum.setCurrentIndex(w.datum.count() - 1)
    w.datum.activated.emit(w.datum.count() - 1)
    A.esperar(200)
    w.reject()


QTimer.singleShot(300, modal(botones_dialogo))
pulsar("sk_autorestringir")
A.esperar(500)
A.reg(AR, "Restringir automáticamente: Generar más, Quitar, Empezar de nuevo, cantidad min/máx y otro datum sin excepción y sin tocar el boceto",
      not A.ERRORES and estado() == e0, A.ERRORES[:1])
sin_error("Restringir automáticamente (botones del diálogo)")
QTimer.singleShot(300, modal(aceptar))
pulsar("sk_autorestringir")
A.esperar(500)
tecla(Qt.Key_Z, Qt.ControlModifier)
e_deshecho = estado()
tecla(Qt.Key_Y, Qt.ControlModifier)
A.reg(AR, "Restringir automáticamente: Ctrl+Z y Ctrl+Y (rehacer) van y vuelven", e_deshecho == e0 and estado() != e0, "")
tecla(Qt.Key_Z, Qt.ControlModifier)
# desde referencia: Esc cancela; clic en el vacío no rompe
QTimer.singleShot(500, lambda: QTest.keyClick(lz, Qt.Key_Escape))
pulsar("sk_autorestringir_referencia")
A.esperar(300)
A.reg(AR, "Restringir desde referencia: Esc cancela la elección del punto sin diálogo ni cambios", QApplication.activeModalWidget() is None
      and estado() == e0, f"{MS[-1:]}")
sin_error("Restringir desde referencia")
salir()
QDialog.exec = _exec_falso
entrar("Vacio")
MS.clear()
pulsar("sk_autorestringir")
A.esperar(300)
A.reg(AR, "Restringir automáticamente en un boceto vacío avisa «está vacío» y no abre diálogo", QApplication.activeModalWidget() is None
      and any("vac" in m.lower() for m in MS), f"{MS[-1:]}")
salir()

A.reg(AR, "ninguna excepción en un slot de Qt", not A.ERRORES, A.ERRORES[:1])
A.guardar_registro("boceto_modificar_cortes")
print(f"\n=== {len(A.REGISTRO)} comprobaciones, {len([r for r in A.REGISTRO if not r['ok']])} con ✗ ===", flush=True)
v.doc.modificado = False
v.close()
sys.exit(0)

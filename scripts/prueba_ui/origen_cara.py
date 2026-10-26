# -*- coding: utf-8 -*-
"""«De dónde viene esta cara» en la ventana real, con clics simulados al visor (nunca el cursor real): una caja con un
agujero y un empalme; al elegir una cara se resalta en amarillo el paso que la creó (fuerte) y los que la modificaron
(suave) en el timeline y el navegador, el clic derecho ofrece «Ir a la operación» y «Editar la operación», y al
deseleccionar el amarillo se va. Se repite en un tema oscuro y uno claro."""
import math
import sys

import arnes as A
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QColor
from PySide6.QtTest import QTest

from omnicad import api
from omnicad.nucleo import referencias as refs
from omnicad.ui import temas
from omnicad.ui.menu_radial import _Fila
from omnicad.ui.panel_timeline import ROL_ORIGEN

AR = "ORIGEN·CARA"
s = api.Sesion()


def llamar(herramienta, **a):
    r = api.llamar(s, herramienta, a)
    assert r["ok"], r
    return r["result"]


llamar("create_box", length=40, width=30, height=20)
llamar("create_hole", face=">Z", diameter=8, depth=10)
llamar("create_cylinder", height=5, radius=3, x=100)         # un cuerpo aparte: el amarillo solo marca el elegido
llamar("fillet", edges="|Z", radius=2, body="op1.c1")
CAJA, HOLE, FILLET = "op1", "op2", "op4"
assert [o.id for o in s.doc.operaciones][:2] == [CAJA, HOLE] and s.doc.operaciones[-1].id == FILLET
app, v = A.iniciar(s.doc)
vis, tl, nav = v.visor, v.timeline, v.navegador


def amarillos():
    """({creo}, {modifico}) de los pasos pintados en el timeline."""
    marcas = {}
    for i in range(tl.lista.count()):
        it = tl.lista.item(i)
        m = it.data(ROL_ORIGEN)
        if m:
            marcas.setdefault(m, set()).add(it.data(Qt.UserRole))
    return marcas.get("creo", set()), marcas.get("modifico", set())


def en_navegador():
    return {k: it.data(0, Qt.UserRole + 5) for k, it in nav._items.items() if it.data(0, Qt.UserRole + 5)}


def punto_en_pantalla(p3):
    q = vis.proyectar(p3)
    return QPoint(int(q.x()), int(q.y()))


def clic(p3, derecho=False):
    pos = punto_en_pantalla(p3)
    if derecho:
        A.clic_derecho(vis, pos)
    else:
        QTest.mouseClick(vis, Qt.LeftButton, Qt.NoModifier, pos)
    A.esperar(150)
    return pos


def filas_del_menu():
    m = getattr(v, "_menu_radial", None)
    return m, ({f.texto: f for f in m.lista.findChildren(_Fila)} if m is not None and m.lista is not None else {})


def pulsar(fila):
    QTest.mouseRelease(fila, Qt.LeftButton, Qt.NoModifier, QPoint(5, 5))
    A.esperar(200)


def caso(tema):
    temas.activar(tema)
    A.esperar(200)
    v._seleccionar([])
    A.reg(AR, f"[{tema}] sin nada elegido no hay amarillo", amarillos() == (set(), set()) and not en_navegador(),
          f"{amarillos()} {en_navegador()}")

    # 1) cara de arriba: la creó la caja, la modificaron el agujero y el empalme
    clic((14, 8, 20))
    sel = v.seleccion[0] if v.seleccion else None
    A.reg(AR, f"[{tema}] el clic elige la cara de arriba", sel is not None and sel["tipo"] == "cara", f"{sel and sel['tipo']}")
    creo, modifico = amarillos()
    A.reg(AR, f"[{tema}] la cara de arriba: creó {CAJA} (amarillo fuerte)", creo == {CAJA}, f"{creo}")
    A.reg(AR, f"[{tema}] la cara de arriba: modificaron {HOLE} y {FILLET} (suave)", modifico == {HOLE, FILLET}, f"{modifico}")
    colores = {tl.lista.item(i).data(Qt.UserRole): tl.lista.item(i).background().color().name()
               for i in range(tl.lista.count()) if tl.lista.item(i).data(ROL_ORIGEN)}
    A.reg(AR, f"[{tema}] los colores son los de temas.ORIGEN",
          colores.get(CAJA) == QColor(temas.ORIGEN["creo"]).name() and colores.get(HOLE) == QColor(temas.ORIGEN["modifico"]).name(),
          f"{colores}")
    marcas = en_navegador()
    A.reg(AR, f"[{tema}] el navegador pinta el cuerpo creado por {CAJA}", marcas.get("op1.c1") == "creo", f"{marcas}")
    A.foto(v, f"origen_cara_{tema}_cara")

    # 2) clic derecho: «Ir a…» y «Editar…» (con 3 pasos la edición abre una lista)
    clic((14, 8, 20), derecho=True)
    menu, filas = filas_del_menu()
    ir = next((f for t, f in filas.items() if t.startswith("Ir a la operación que creó esta cara")), None)
    ed = next((f for t, f in filas.items() if t.startswith("Editar la operación de esta cara")), None)
    A.reg(AR, f"[{tema}] el clic derecho ofrece «Ir a la operación que creó esta cara» y «Editar la operación…»",
          ir is not None and ed is not None, f"{list(filas)[:5]}")
    if ir is not None and ed is not None:
        pulsar(ir)
        actual = tl.lista.currentItem()
        A.reg(AR, f"[{tema}] «Ir a la operación» elige el paso {CAJA} en el timeline",
              actual is not None and actual.data(Qt.UserRole) == CAJA, f"{actual and actual.data(Qt.UserRole)}")
        A.reg(AR, f"[{tema}] «Ir a la operación» no cambia la selección ni el amarillo",
              v.seleccion and v.seleccion[0]["tipo"] == "cara" and amarillos()[0] == {CAJA}, f"{amarillos()}")
        clic((14, 8, 20), derecho=True)
        menu, filas = filas_del_menu()
        ed = next((f for t, f in filas.items() if t.startswith("Editar la operación de esta cara")), None)
        pulsar(ed)
        lista = getattr(v, "_menu_origen", None)
        textos = [a.text() for a in lista.actions() if not a.isSeparator() and a.text()] if lista is not None else []
        A.reg(AR, f"[{tema}] con 3 pasos, «Editar…» lista cada uno (el que la creó primero)",
              len(textos) == 3 and textos[0].endswith("la creó") and all(t.endswith("la modificó") for t in textos[1:]),
              f"{textos}")
        if lista is not None:
            lista.actions()[1].trigger()          # el primer paso (los dos de arriba son el título y «la creó»)
            A.esperar(350)
            A.reg(AR, f"[{tema}] elegir un paso de la lista abre su comando en modo edición",
                  v.panel is not None and v.panel.isVisible(), f"panel={v.panel}")
            limpiar_panel()
            lista.close()

    # 3) cara del empalme (vertical, redonda): la creó el empalme y nadie la modificó
    v._seleccionar([])
    hit = hit_cara = None
    for ang in (45, 135, 225, 315):
        cx, cy = (18 if ang in (45, 315) else -18), (13 if ang in (45, 135) else -13)
        p3 = (cx + 2 * math.cos(math.radians(ang)) * 1, cy + 2 * math.sin(math.radians(ang)), 10)
        q = vis.proyectar(p3)
        h = vis.elegir_entidad(q, {"cara"}) if q is not None else None
        if h and h.get("forma") is not None and refs.firma_cara(h["forma"])["geom"] == "cilindro" \
                and abs(refs.firma_cara(h["forma"])["radio"] - 2) < 1e-6:
            hit, hit_cara = p3, h
            break
    A.reg(AR, f"[{tema}] hay una cara de empalme visible para elegir", hit is not None)
    if hit is not None:
        v._clic_en_vista(hit_cara)          # la selección del visor con filtro de caras (un clic suelto caería en la arista tangente)
        A.esperar(150)
        creo, modifico = amarillos()

        A.reg(AR, f"[{tema}] la cara del empalme: creó {FILLET} y nada la modificó", creo == {FILLET} and not modifico,
              f"{creo} {modifico}")
        A.foto(v, f"origen_cara_{tema}_empalme")

    # 3b) la arista tangente del empalme (un clic real sobre ella): la creó el empalme, no la caja
    v._seleccionar([])
    clic((-18, -15, 10))
    sel = v.seleccion[0] if v.seleccion else None
    creo, modifico = amarillos()
    A.reg(AR, f"[{tema}] la arista tangente del empalme: creó {FILLET}",
          sel is not None and sel["tipo"] == "arista" and creo == {FILLET} and not modifico,
          f"{sel and sel['tipo']} {creo} {modifico}")

    # 4) deseleccionar (clic en el vacío) saca el amarillo
    clic((300, 300, 300))
    A.reg(AR, f"[{tema}] el clic en el vacío saca el amarillo del timeline y del navegador",
          not v.seleccion and amarillos() == (set(), set()) and not en_navegador(), f"{amarillos()} {en_navegador()}")


def limpiar_panel():
    try:
        if v.panel is not None and v.panel.isVisible():
            v.panel.cancelar()
    except RuntimeError:
        pass
    A.esperar(100)


for clave in temas.INCLUIDOS:           # el amarillo se ve en los 5 temas, oscuros y claros
    A.correr(AR, lambda clave=clave: caso(clave))

A.reg("GENERAL", "ninguna excepción escapó de un slot de Qt en toda la corrida", not A.ERRORES,
      f"{len(A.ERRORES)}: {A.ERRORES[:1]}")
A.guardar_registro("origen_cara")
fallas = [r for r in A.REGISTRO if not r["ok"]]
print(f"\n=== {len(A.REGISTRO)} comprobaciones, {len(fallas)} con ✗ ===")
v.doc.modificado = False
v.close()
sys.exit(0)

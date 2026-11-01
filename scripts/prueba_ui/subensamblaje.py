# -*- coding: utf-8 -*-
"""ASM-9 en la ventana real y como una persona: un subensamblaje de dos niveles (Base fija, Brazo con una unión de
revolución y Mano colgada del Brazo). El navegador en árbol y su menú (Aislar), el panel Nuevo componente con «Padre»,
el panel Grupo rígido con «Incluir componentes secundarios», accionar la unión del padre (la mano gira con él), cambiar
una cota, arrastrar el padre en el visor, Capturar y Revertir, guardar y reabrir, deshacer en cadena y ventana chica."""
import sys
import tempfile
from pathlib import Path

import arnes as A
import numpy as np
import teclado as T
from omnicad import api
from omnicad.nucleo import geometria as geo
from omnicad.timeline.posicion import pendiente_de
from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox

AR = "SUBENSAMBLAJE"
s = api.Sesion()


def L(nombre, **a):
    r = api.llamar(s, nombre, a)
    assert r["ok"], (nombre, a, r)
    return r["result"]


L("create_parameter", name="largo", expression="50 mm")
base = L("create_box", name="Base", length=200, width=200, height=10)["bodies_created"][0]["id"]
brazo = L("create_box", name="Brazo", length="largo", width=12, height=12, x=300)["bodies_created"][0]["id"]
mano = L("create_box", name="Mano", length=20, width=20, height=20, x=360)["bodies_created"][0]["id"]
dedo = L("create_box", name="Dedo", length=6, width=6, height=6, x=400)["bodies_created"][0]["id"]
L("create_component", bodies=[base], name="CBase", grounded=True)
kb = L("create_component", bodies=[brazo], name="CBrazo")["component"]["id"]
km = L("create_component", bodies=[mano], name="CMano", parent="CBrazo")["component"]["id"]
L("create_joint", origin1="<Z", body1=brazo, origin2=">Z", body2=base, joint_type="revolute", name="Giro")
app, v = A.iniciar(s.doc)
vis = v.visor


def centro(cid):
    a, b = geo.caja_envolvente(v.doc.estado_final.cuerpo(cid).forma)
    return (np.asarray(a) + np.asarray(b)) / 2


def ens():
    return api.llamar(s, "get_assembly", {})["result"]


def items():
    arbol = v.navegador.arbol

    def rec(it):
        yield it
        for j in range(it.childCount()):
            yield from rec(it.child(j))
    for i in range(arbol.topLevelItemCount()):
        yield from rec(arbol.topLevelItem(i))


def item(texto):
    return next((i for i in items() if i.text(0).split("  (")[0] == texto), None)


def menu_de(widget, pos):
    A.MENUS.clear()
    A.clic_derecho(widget, pos)
    return A.MENUS[-1] if A.MENUS else None


def accion(menu, texto):
    return next((a for a in menu.actions() if a.text() == texto), None)


def aceptar(p):
    p.aceptar()
    A.esperar(300)


def run(nombre, f):
    A.correr(f"{AR} · {nombre}", f)


# 1. Navegador en árbol y Aislar ------------------------------------------------------------------------------------------
def navegador():
    it_mano, it_brazo = item("CMano"), item("CBrazo")
    A.reg(AR, "el navegador muestra CMano debajo de CBrazo", it_mano is not None and it_mano.parent() is it_brazo,
          f"padre={None if it_mano is None or it_mano.parent() is None else it_mano.parent().text(0)}")
    A.reg(AR, "CBrazo cuelga de la raíz", it_brazo is not None and it_brazo.parent() is not None
          and it_brazo.parent().parent() is None, "")
    it_mano.parent().setExpanded(True)
    arbol = v.navegador.arbol
    arbol.scrollToItem(it_mano)
    A.esperar(100)
    A.foto(v, "subensamblaje_navegador")
    r = arbol.visualItemRect(it_brazo)
    menu = menu_de(arbol.viewport(), r.center())
    A.reg(AR, "clic derecho en CBrazo: menú con Aislar", menu is not None and accion(menu, "Aislar") is not None,
          "" if menu is None else " | ".join(a.text() for a in menu.actions()))
    if menu is not None and accion(menu, "Aislar") is not None:
        accion(menu, "Aislar").trigger()
        A.esperar(200)
        A.reg(AR, "Aislar el padre deja ver la mano y oculta la base y el dedo",
              mano not in v.ocultos and brazo not in v.ocultos and base in v.ocultos and dedo in v.ocultos, str(sorted(v.ocultos)))
        A.foto(v, "subensamblaje_aislar_padre")
        v.ocultos.clear()
        v._refrescar_visibilidad()


run("navegador", navegador)


# 2. Nuevo componente con «Padre» ------------------------------------------------------------------------------------------
def nuevo_componente():
    p = A.abrir(v, "nuevo_componente")
    et = {c[0]: (c[1], c[2]) for c in A.etiquetas(p)}
    A.reg(AR, "el panel tiene el campo «Padre» (lista)", et.get("padre") == ("Opciones", "Padre"), str(et))
    combo = p.widgets["padre"]
    textos = [combo.itemText(i) for i in range(combo.count())]
    A.reg(AR, "Padre ofrece la raíz y cada componente con su camino", textos == ["(raíz)", "CBase", "CBrazo", "CBrazo › CMano"], str(textos))
    combo.setCurrentIndex(textos.index("CBrazo › CMano"))
    A.esperar(60)
    A.elegir(p, "cuerpos", A.hit_cuerpo(v, dedo))
    pasos = A.n_ops(v)
    aceptar(p)
    nuevo = next((k for k, d in v.doc.estado_final.componentes.items() if d["nombre"] == "Componente4" or
                  (d.get("padre") == km)), None)
    A.reg(AR, "Aceptar crea el componente colgado de CMano", nuevo is not None and A.n_ops(v) == pasos + 1
          and v.doc.estado_final.componentes[nuevo]["padre"] == km, str(nuevo))
    it = item(v.doc.estado_final.componentes[nuevo]["nombre"]) if nuevo else None
    A.reg(AR, "el navegador lo muestra debajo de CMano", it is not None and it.parent() is item("CMano"), "")
    # reabrir con doble clic: el padre vuelve elegido y no se ofrece a sí mismo
    lista = v.timeline.lista
    fila = next(lista.item(i) for i in range(lista.count()) if lista.item(i).data(Qt.UserRole) == nuevo)
    lista.scrollToItem(fila)
    c = lista.visualItemRect(fila).center()
    QTest.mouseClick(lista.viewport(), Qt.LeftButton, Qt.NoModifier, c)
    A.esperar(60)
    QTest.mouseDClick(lista.viewport(), Qt.LeftButton, Qt.NoModifier, c)
    A.esperar(300)
    p = v.panel
    ok = p is not None and p.valores.get("padre") == km
    textos = [p.widgets["padre"].itemText(i) for i in range(p.widgets["padre"].count())] if p is not None else []
    A.reg(AR, "doble clic: el panel vuelve con «CBrazo › CMano» y no se ofrece a sí mismo como padre",
          ok and "CBrazo › CMano" in textos and not any(t.endswith("Componente4") for t in textos), str(textos))
    if p is not None:
        QTest.keyClick(p.widgets["padre"], Qt.Key_Escape)
        A.esperar(150)
    A.reg(AR, "Esc cierra la edición sin cambiar nada", v.panel is None and A.n_ops(v) == pasos + 1, "")
    A.foto(v, "subensamblaje_nuevo_componente")
    A.deshacer(v)
    A.reg(AR, "deshacer quita el componente nuevo", A.n_ops(v) == pasos and nuevo not in v.doc.estado_final.componentes, "")


run("nuevo componente", nuevo_componente)


# 3. Grupo rígido con «Incluir componentes secundarios» -------------------------------------------------------------------
def grupo_rigido():
    p = A.abrir(v, "grupo_rigido")
    et = {c[0]: (c[1], c[2]) for c in A.etiquetas(p)}
    A.reg(AR, "el panel tiene la casilla «Incluir componentes secundarios»",
          et.get("incluir_hijos") == ("Casilla", "Incluir componentes secundarios"), str(et))
    QTest.mouseClick(p.widgets["incluir_hijos"], Qt.LeftButton, Qt.NoModifier, QPoint(8, 7))     # el cuadradito
    A.esperar(60)
    A.reg(AR, "clic en el cuadradito marca la casilla", p.valores.get("incluir_hijos") is True, str(p.valores.get("incluir_hijos")))
    A.esperar(60)
    A.elegir(p, "cuerpos", A.hit_cuerpo(v, brazo), A.hit_cuerpo(v, base))
    pasos = A.n_ops(v)
    aceptar(p)
    g = v.doc.estado_final.grupos_rigidos
    A.reg(AR, "Aceptar: el grupo incluye a CMano", A.n_ops(v) == pasos + 1 and g and set(g[-1]) == {kb, km, "op5"}, str(g))
    A.deshacer(v)
    p = A.abrir(v, "grupo_rigido")
    A.elegir(p, "cuerpos", A.hit_cuerpo(v, brazo), A.hit_cuerpo(v, base))
    aceptar(p)
    g = v.doc.estado_final.grupos_rigidos
    A.reg(AR, "sin la casilla: el grupo son solo los dos elegidos", g and set(g[-1]) == {kb, "op5"}, str(g))
    A.deshacer(v)


run("grupo rígido", grupo_rigido)


# 4. Pieza real: accionar la unión del padre, cambiar la cota, arrastrar, capturar y revertir -------------------------------
def pieza():
    c0_brazo, c0_mano = centro(brazo), centro(mano)
    pa = A.abrir(v, "accionar_uniones")
    pa.set_valor("union", "op8")
    T.teclear(pa, "giro", "90 deg", Qt.Key_Return)
    A.esperar(100)
    if v.panel is not None:
        aceptar(pa)
    rel0, rel1 = c0_mano - c0_brazo, centro(mano) - centro(brazo)
    A.reg(AR, "accionar 90° el brazo: la mano gira con él (de +X a ±Y)", abs(rel1[0]) < 0.05 and abs(abs(rel1[1]) - abs(rel0[0])) < 0.05,
          f"antes={rel0} ahora={rel1}")
    A.foto(v, "subensamblaje_girado")
    L("set_parameter", name="largo", expression="80 mm")
    A.esperar(400)
    rel2 = centro(mano) - centro(brazo)
    A.reg(AR, "cambiar la cota «largo»: el brazo crece y la mano sigue girada con él",
          abs(rel2[0]) < 0.05 and abs(abs(rel2[1]) - abs(rel0[0])) < 0.5 and all(r.estado != "error" for r in v.doc.resultados), f"{rel2}")
    A.foto(v, "subensamblaje_cota")
    # arrastrar el brazo en el visor: la mano se dibuja movida también
    q = vis.proyectar(centro(brazo))
    QApplication.sendEvent(vis, QMouseEvent(QEvent.MouseMove, q, vis.mapToGlobal(q), Qt.NoButton, Qt.NoButton, Qt.NoModifier))
    QApplication.sendEvent(vis, QMouseEvent(QEvent.MouseButtonPress, q, vis.mapToGlobal(q), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier))
    for i in range(1, 11):
        q2 = q + QPointF(12 * i, 0)
        QApplication.sendEvent(vis, QMouseEvent(QEvent.MouseMove, q2, vis.mapToGlobal(q2), Qt.NoButton, Qt.LeftButton, Qt.NoModifier))
        QTest.qWait(10)
    QApplication.sendEvent(vis, QMouseEvent(QEvent.MouseButtonRelease, q2, vis.mapToGlobal(q2), Qt.LeftButton, Qt.NoButton, Qt.NoModifier))
    A.esperar(100)
    p = pendiente_de(v.doc)
    A.reg(AR, "arrastrar el brazo: la mano se mueve con él en el dibujo", p is not None and mano in vis.transformaciones
          and brazo in vis.transformaciones, str(None if p is None else sorted(vis.transformaciones)))
    A.foto(v, "subensamblaje_arrastre")
    pasos = A.n_ops(v)
    QTest.mouseClick(v.arrastre.barra.capturar, Qt.LeftButton)
    A.esperar(400)
    rel_cap = centro(mano) - centro(brazo)          # el arrastre giró la unión: la mano sigue a 60 mm del brazo, en el plano
    A.reg(AR, "Capturar posición agrega un paso y la mano sigue pegada al brazo girado", A.n_ops(v) == pasos + 1
          and abs(np.linalg.norm(rel_cap[:2]) - abs(rel0[0])) < 0.5 and abs(rel_cap[2] - rel0[2]) < 0.05, str(rel_cap))
    L("set_component_initial_position", component="CBrazo", offset=[0, 0, 25])
    A.esperar(300)
    L("revert_position", components=["CBrazo"])
    A.esperar(300)
    A.reg(AR, "mover el padre y Revertir el padre devuelve a la mano también", np.allclose(centro(mano) - centro(brazo), rel_cap, atol=0.05)
          and all(r.estado != "error" for r in v.doc.resultados), str(centro(mano) - centro(brazo)))
    # guardar y reabrir
    ruta = Path(tempfile.mkdtemp(prefix="omnicad_sub_")) / "sub.omnicad"
    L("save_document", path=str(ruta))
    s2 = api.Sesion()
    r = api.llamar(s2, "open_document", {"path": str(ruta)})
    comps = {c["name"]: c for c in api.llamar(s2, "get_assembly", {})["result"]["components"]} if r["ok"] else {}
    A.reg(AR, "guardar y reabrir conserva el padre y el camino", r["ok"] and comps.get("CMano", {}).get("parent") == kb
          and comps.get("CMano", {}).get("path") == "CBrazo › CMano", str({k: c.get("parent") for k, c in comps.items()}))
    # deshacer en cadena hasta el principio
    n_err = len(A.ERRORES)
    for _ in range(12):
        if not v.acciones["deshacer"].isEnabled():
            break
        A.deshacer(v)
    A.reg(AR, "deshacer en cadena: sin excepciones y el modelo sano", len(A.ERRORES) == n_err
          and all(r.estado != "error" for r in v.doc.resultados), f"{A.n_ops(v)} pasos")


run("pieza", pieza)


# 5. Ventana chica -------------------------------------------------------------------------------------------------------
def chica():
    for w, h in ((1024, 640), (800, 520)):
        v.resize(w, h)
        A.esperar(300)
        p = A.abrir(v, "nuevo_componente")
        visible = p.isVisible() and p.widgets["padre"].isVisible() and v.rect().contains(p.geometry())
        A.reg(AR, f"ventana {w}x{h}: el panel Nuevo componente entra entero con «Padre» a la vista", visible, f"{p.geometry()} en {v.rect()}")
        A.foto(v, f"subensamblaje_{w}x{h}")
        p.cancelar()
        A.esperar(100)
    v.resize(1900, 1000)


run("ventana chica", chica)

A.guardar_registro("subensamblaje")
fallas = [r for r in A.REGISTRO if not r["ok"]]
print(f"\n=== {len(A.REGISTRO)} comprobaciones, {len(fallas)} con ✗ ===")
for r in fallas:
    print("✗", r)
QMessageBox.exec = QDialog.exec          # «¿Guardar cambios?» al cerrar no tiene quién la conteste
v.close()
sys.exit(0)

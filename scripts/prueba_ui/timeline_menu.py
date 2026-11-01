# -*- coding: utf-8 -*-
"""H-6 y H-4 en la ventana real, con clics simulados a la lista del timeline y al panel (nunca el cursor real):
el menú del clic derecho (Configurar, Buscar en la ventana, Crear conjunto de selección, Suprimir varios pasos elegidos
con Ctrl) y «Duplicar con uniones» (botón de la cinta, destinos, Aceptar, deshacer, errores, ventana chica)."""
import sys

import arnes as A
from omnicad import api
from omnicad.nucleo import geometria as geo
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QContextMenuEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QInputDialog

AR = "TIMELINE·MENÚ"
s = api.Sesion()


def L(nombre, **a):
    r = api.llamar(s, nombre, a)
    assert r["ok"], (nombre, a, r)
    return r["result"]


base = L("create_box", length=40, width=40, height=10)["bodies_created"][0]["id"]
bloque = L("create_box", length=10, width=10, height=10, x=100, y=50)["bodies_created"][0]["id"]
L("create_component", bodies=[base], name="Base", grounded=True)
L("create_component", bodies=[bloque], name="Bloque")
L("create_joint", origin1="<Z", body1=bloque, origin2=">Z", body2="Base", name="Apoyo")
L("create_joint_origin", geometry=">Z", body=base, offset=[15, 0, 0], name="Destino A")
L("create_joint_origin", geometry=">Z", body=base, offset=[-15, 5, 0], name="Destino B")
app, v = A.iniciar(s.doc)
tl = v.timeline
QInputDialog.getText = staticmethod(lambda *a, **k: ("Mi conjunto", True))


def caja(cid):
    return [round(float(x), 2) for p in geo.caja_envolvente(v.doc.estado_final.cuerpos[cid].forma) for x in p]


def centro(op_id):
    for i in range(tl.lista.count()):
        it = tl.lista.item(i)
        if it.data(Qt.UserRole) == op_id:
            return tl.lista.visualItemRect(it).center()
    raise RuntimeError(f"el paso {op_id} no está en el timeline")


def clic(op_id, ctrl=False):
    QTest.mouseClick(tl.lista.viewport(), Qt.LeftButton, Qt.ControlModifier if ctrl else Qt.NoModifier, centro(op_id))
    A.esperar(80)


def menu(op_id):
    """Clic derecho en el paso: el menú real (QMenu.exec queda en A.MENUS) como {texto: acción}."""
    A.MENUS.clear()
    pos = centro(op_id)
    QTest.mouseClick(tl.lista.viewport(), Qt.RightButton, Qt.NoModifier, pos)
    QApplication.sendEvent(tl.lista.viewport(), QContextMenuEvent(QContextMenuEvent.Mouse, pos, tl.lista.viewport().mapToGlobal(pos)))
    A.esperar(80)
    if not A.MENUS:
        return {}
    return {a.text(): a for a in A.MENUS[-1].actions() if not a.isSeparator()}


def run(nombre, f):
    A.correr(f"{AR} · {nombre}", f)


def entradas():
    for op_id, creo in (("op1", True), ("op2", True), ("op5", False)):          # caja, caja, unión
        m = menu(op_id)
        faltan = [t for t in ("Configurar", "Buscar en la ventana", "Crear conjunto de selección…") if t not in m]
        A.reg(AR, f"{op_id}: el clic derecho trae Configurar, Buscar en la ventana y Crear conjunto", not faltan, f"faltan {faltan}: {list(m)}")
        if "Buscar en la ventana" in m:
            A.reg(AR, f"{op_id}: «Buscar en la ventana» y «Crear conjunto» {'habilitados' if creo else 'grisados (no creó cuerpos)'}",
                  m["Buscar en la ventana"].isEnabled() == creo and m["Crear conjunto de selección…"].isEnabled() == creo,
                  f"{m['Buscar en la ventana'].isEnabled()} {m['Crear conjunto de selección…'].isEnabled()}")


run("entradas del menú", entradas)


def buscar():
    clic("op1")
    m = menu("op1")
    m["Buscar en la ventana"].trigger()
    A.esperar(250)
    cuerpos = [h["ref"].get("cuerpo") for h in v.seleccion]
    actual = tl.lista.currentItem()
    A.reg(AR, "«Buscar en la ventana» elige en la vista el cuerpo que creó el paso y deja el paso elegido en el timeline",
          cuerpos == [base] and actual is not None and actual.data(Qt.UserRole) == "op1", f"{cuerpos} {actual and actual.data(Qt.UserRole)}")
    A.foto(v, "timeline_menu_buscar")


run("buscar en la ventana", buscar)


def conjunto():
    m = menu("op2")
    m["Crear conjunto de selección…"].trigger()
    A.esperar(150)
    guardado = v.doc.espacios.get("conjuntos_seleccion", {}).get("Mi conjunto")
    A.reg(AR, "«Crear conjunto de selección…» guarda los cuerpos del paso bajo el nombre escrito",
          guardado == [{"tipo": "cuerpo", "cuerpo": bloque}], f"{guardado}")
    r = L("manage_selection_sets", action="select", name="Mi conjunto")
    A.reg(AR, "el conjunto se vuelve a elegir desde la API", r["bodies"] == [bloque], f"{r}")


run("conjunto de selección", conjunto)


def configurar():
    m = menu("op5")
    m["Configurar"].trigger()
    A.esperar(150)
    cols = v.doc.configuraciones.get("columnas", [])
    A.reg(AR, "«Configurar» suma la columna «Suprimir» del paso a la tabla de configuraciones", cols == [{"tipo": "suprimir", "op": "op5"}], f"{cols}")
    n = len(v.doc._deshacer)
    menu("op5")["Configurar"].trigger()
    A.esperar(150)
    A.reg(AR, "«Configurar» otra vez no repite la columna ni deja un paso de deshacer",
          len(v.doc.configuraciones["columnas"]) == 1 and len(v.doc._deshacer) == n, f"{v.doc.configuraciones} {len(v.doc._deshacer)} vs {n}")


run("configurar", configurar)


def suprimir_varios():
    clic("op6")
    clic("op7", ctrl=True)
    elegidos = tl.elegidos()
    A.reg(AR, "Ctrl+clic elige dos pasos del timeline", sorted(elegidos) == ["op6", "op7"], f"{elegidos}")
    m = menu("op7")
    A.reg(AR, "el menú con dos pasos elegidos ofrece «Suprimir 2 pasos» y no «Configurar»", "Suprimir 2 pasos" in m and not m["Configurar"].isEnabled(), f"{list(m)}")
    m["Suprimir 2 pasos"].trigger()
    A.esperar(250)
    ops = v.doc.operaciones
    A.reg(AR, "«Suprimir 2 pasos» suprime los dos", ops[5].suprimida and ops[6].suprimida, f"{ops[5].suprimida} {ops[6].suprimida}")
    v.acciones["deshacer"].trigger()
    A.esperar(250)
    A.reg(AR, "un solo Deshacer los reactiva a los dos", not v.doc.operaciones[5].suprimida and not v.doc.operaciones[6].suprimida, "")
    clic("op6")                                              # un clic simple vuelve a un solo paso elegido
    A.reg(AR, "un clic simple deja un solo paso elegido", tl.elegidos() == ["op6"], f"{tl.elegidos()}")
    m = menu("op6")
    A.reg(AR, "con un solo paso elegido el menú vuelve a «Suprimir operación»", "Suprimir operación" in m, f"{list(m)}")


run("suprimir varios con Ctrl", suprimir_varios)


def suprimir_con_dependientes():
    """Como suprimir uno desde la ventana: lo que depende queda en rojo con aviso y no se rechaza todo."""
    clic("op1")                                               # las dos cajas: los componentes (op3, op4) las usan
    clic("op2", ctrl=True)
    n = len(v.doc._deshacer)
    menu("op2")["Suprimir 2 pasos"].trigger()
    A.esperar(300)
    ops, res = v.doc.operaciones, v.doc.resultados
    A.reg(AR, "«Suprimir 2 pasos» con pasos de los que otros dependen: se suprimen y los componentes (op3 y op4) quedan en rojo",
          ops[0].suprimida and ops[1].suprimida and res[2].estado == "error" and res[3].estado == "error",
          f"{ops[0].suprimida} {ops[1].suprimida} {res[2].estado} {res[3].estado}")
    mensaje = tl.estado.text()
    A.reg(AR, "el aviso lo dice en la barra del timeline y fue UN solo paso de deshacer", len(v.doc._deshacer) == n + 1 and "error" in mensaje,
          f"{len(v.doc._deshacer) - n} «{mensaje[:110]}»")
    v.acciones["deshacer"].trigger()
    A.esperar(300)
    A.reg(AR, "un Deshacer devuelve los dos y los componentes vuelven a estar bien",
          not v.doc.operaciones[0].suprimida and not v.doc.operaciones[1].suprimida and v.doc.resultados[2].estado == "ok", "")


run("suprimir con dependientes", suprimir_con_dependientes)


def arrastrar_con_dos_elegidos():
    from PySide6.QtCore import QMimeData, QPointF
    from PySide6.QtGui import QDropEvent
    clic("op6")                                               # los dos orígenes de unión: solo dependen de la base
    clic("op7", ctrl=True)
    vp = tl.lista.viewport()
    QTest.mousePress(vp, Qt.LeftButton, Qt.NoModifier, centro("op6"))          # se aprieta el PRIMERO que se eligió
    dest = centro("op7")
    tl.lista.dropEvent(QDropEvent(QPointF(dest.x() + 8, dest.y()), Qt.MoveAction, QMimeData(), Qt.LeftButton, Qt.NoModifier))
    QTest.mouseRelease(vp, Qt.LeftButton, Qt.NoModifier, centro("op6"))
    A.esperar(250)
    orden = [o.id for o in v.doc.operaciones]
    A.reg(AR, "arrastrar un paso con dos elegidos mueve el arrastrado, no el último elegido (el soltar es un QDropEvent armado: QDrag no se maneja con eventos)",
          orden[5:7] == ["op7", "op6"], f"{orden}")
    v.acciones["deshacer"].trigger()
    A.esperar(250)


run("arrastrar con dos elegidos", arrastrar_con_dos_elegidos)


# ------------------------------------------------------------------ H-4 · Duplicar con uniones
def duplicar():
    accion = v.acciones.get("duplicar_con_uniones")
    A.reg(AR, "el botón «Duplicar con uniones» de la cinta existe y está activo", accion is not None and accion.isEnabled(), f"{accion}")
    n0, ncomp = A.n_ops(v), len(L("get_assembly")["components"])
    p = A.abrir(v, "duplicar_con_uniones")
    A.reg(AR, "el comando abre su panel", p is not None and p.isVisible(), f"{p}")
    if p is None:
        return
    p.aceptar()                                               # sin destinos: se rechaza con un mensaje y el panel sigue abierto
    A.esperar(150)
    msg = p.mensaje.text() if p.mensaje.isVisible() else ""
    A.reg(AR, "Aceptar sin destinos avisa «Elegí al menos un destino» y no cambia el documento",
          "destino" in msg and A.n_ops(v) == n0, f"«{msg}» ops={A.n_ops(v)}")
    A.elegir(p, "destinos", A.hit_plano(v, "Destino A"), A.hit_plano(v, "Destino B"))
    A.foto(v, "duplicar_con_uniones_panel")
    p.aceptar()
    A.esperar(400)
    comps = L("get_assembly")["components"]
    copias = [c for c in comps if "copia" in c["name"]]
    A.reg(AR, "Aceptar agrega dos componentes copia y 4 pasos (2 copias + 2 uniones)", len(copias) == 2 and A.n_ops(v) == n0 + 4,
          f"{[c['name'] for c in comps]} ops={A.n_ops(v)}")
    cajas = [caja(c["bodies"][0]["id"]) for c in copias]
    A.reg(AR, "cada copia queda sobre su destino", cajas == [[10.0, -5.0, 10.0, 20.0, 5.0, 20.0], [-20.0, 0.0, 10.0, -10.0, 10.0, 20.0]], f"{cajas}")
    A.reg(AR, "el original no se movió", caja(bloque) == [-5.0, -5.0, 10.0, 5.0, 5.0, 20.0], f"{caja(bloque)}")
    A.reg(AR, "el timeline muestra los pasos nuevos con su ícono", tl.lista.count() >= n0 + 4, f"{tl.lista.count()}")
    A.foto(v, "duplicar_con_uniones_resultado")
    v.acciones["deshacer"].trigger()
    A.esperar(300)
    A.reg(AR, "un solo Deshacer saca las dos copias y sus uniones", A.n_ops(v) == n0 and len(L("get_assembly")["components"]) == ncomp, f"ops={A.n_ops(v)}")
    v.acciones["rehacer"].trigger()
    A.esperar(300)
    A.reg(AR, "Rehacer las vuelve", A.n_ops(v) == n0 + 4, f"ops={A.n_ops(v)}")
    v.acciones["deshacer"].trigger()
    A.esperar(300)


run("duplicar con uniones", duplicar)


def chica():
    for ancho, alto in ((1024, 640), (800, 520)):
        v.resize(ancho, alto)
        A.esperar(500)
        p = A.abrir(v, "duplicar_con_uniones")
        entra = p is not None and v.rect().contains(p.mapTo(v, p.rect().bottomRight())) and v.rect().contains(p.mapTo(v, p.rect().topLeft()))
        boton = getattr(p, "b_aceptar", None)
        A.foto(v, f"duplicar_con_uniones_{ancho}x{alto}")
        A.reg(AR, f"{ancho}x{alto}: el panel con Aceptar y Cancelar entra en la ventana", entra and (boton is None or boton.isVisible()), f"{p and p.geometry()} ventana={v.rect()}")
        if p is not None:
            p.cancelar()
            A.esperar(150)
    v.resize(1900, 1000)
    A.esperar(300)


run("ventana chica", chica)

A.reg("GENERAL", "ninguna excepción escapó de un slot de Qt en toda la corrida", not A.ERRORES, f"{len(A.ERRORES)}: {A.ERRORES[:1]}")
A.guardar_registro("timeline_menu")
fallas = [r for r in A.REGISTRO if not r["ok"]]
print(f"\n=== {len(A.REGISTRO)} comprobaciones, {len(fallas)} con ✗ ===")
v.doc.modificado = False
v.close()
sys.exit(0)

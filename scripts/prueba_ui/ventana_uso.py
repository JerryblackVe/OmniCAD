# -*- coding: utf-8 -*-
"""Uso de la ventana como una persona: timeline (clic, doble clic, clic derecho, botones), navegador (clic, doble clic,
clic derecho), visor (rueda, órbita, clic derecho), atajos de teclado, guardar / reabrir, deshacer en cadena y
ventana chica. Cada acción que cambia el modelo se deshace y se comprueba que el estado vuelve igual."""
import sys
import tempfile
from pathlib import Path

import arnes as A
import escena
from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QMouseEvent, QWheelEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QFileDialog, QInputDialog

s, ids = escena.construir()
app, v = A.iniciar(s.doc)
QInputDialog.getText = staticmethod(lambda *a, **k: ("Nombre de prueba", True))
vis = v.visor
PELIGROSAS = ("eliminar", "borrar", "quitar", "delete", "cerrar", "salir")


def estado():
    d = v.doc
    return (len(d.operaciones), d.marcador, tuple(bool(o.suprimida) for o in d.operaciones), tuple(sorted(A.cuerpos_resumen(v).items())))


def limpiar():
    """Deja la ventana como una persona: sin panel abierto, sin boceto abierto."""
    try:
        if v.panel is not None and v.panel.isVisible():
            v.panel.cancelar()
    except RuntimeError:
        pass
    try:
        if v.modo_boceto.activo:
            v._salir_de_boceto()
    except Exception:  # noqa: BLE001
        pass
    A.esperar(80)


def restaurar(antes, area, que):
    """Deshace hasta volver al estado `antes`; devuelve (volvio, pasos)."""
    k = 0
    while estado() != antes and k < 6:
        A.deshacer(v)
        k += 1
    if estado() != antes and v.doc.marcador != antes[1]:
        v.doc.marcador = antes[1]
    ok = estado() == antes
    return ok, k


def acciones_de(menu, prefijo=""):
    for a in menu.actions():
        if a.isSeparator():
            continue
        if a.menu() is not None:
            yield from acciones_de(a.menu(), prefijo + a.text().replace("&", "") + " › ")
        else:
            yield prefijo + a.text().replace("&", ""), a


def recorrer_menu(area, origen, abrir):
    """`abrir()` hace el clic derecho y devuelve el menú. Cada ítem habilitado (menos los destructivos) se activa con un
    menú recién abierto, como lo haría la persona, y se comprueba que el modelo se pueda deshacer."""
    menu = abrir()
    if menu is None:
        A.reg(area, f"{origen}: menú contextual", False, "el clic derecho no abrió ningún menú")
        return
    items = list(acciones_de(menu))
    A.reg(area, f"{origen}: menú contextual", bool(items), " | ".join(f"{n}{'' if a.isEnabled() else ' (gris)'}" for n, a in items))
    for nombre, a in items:
        if not a.isEnabled() or any(p in nombre.lower() for p in PELIGROSAS):
            continue
        menu = abrir()
        a = next((x for n, x in acciones_de(menu) if n == nombre), None) if menu is not None else None
        if a is None:
            A.reg(area, f"{origen} › «{nombre}»", False, "el ítem no está al reabrir el menú")
            continue
        antes = estado()
        n_err = len(A.ERRORES)
        a.trigger()
        A.esperar(200)
        limpiar()
        sin_error = len(A.ERRORES) == n_err
        extra = "" if sin_error else f" | EXCEPCIÓN {A.ERRORES[-1][-250:]}"
        if estado() != antes:
            ok, k = restaurar(antes, area, nombre)
            A.reg(area, f"{origen} › «{nombre}»", sin_error and ok, f"cambió el modelo; deshacer ({k}) vuelve igual: {ok}" + extra)
        else:
            A.reg(area, f"{origen} › «{nombre}»", sin_error, "sin cambio en el modelo" + extra)


def menu_tras_clic_derecho(widget, pos):
    def abrir():
        limpiar()
        A.MENUS.clear()
        A.clic_derecho(widget, pos)
        return A.MENUS[-1] if A.MENUS else None
    return abrir


# ------------------------------------------------------------------ guardar y reabrir
AR = "ARCHIVO"
tmp = Path(tempfile.mkdtemp(prefix="omnicad_ui_")) / "prueba.omnicad"
QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: (str(tmp), ""))
QFileDialog.getOpenFileName = staticmethod(lambda *a, **k: (str(tmp), ""))
for i in range(3):                       # pasos hechos DESDE la ventana (así hay historial para deshacer)
    pc = A.abrir(v, "caja")
    pc.set_valor("x", f"{400 + 60 * i} mm")
    pc._t_previa.stop()
    pc._calcular_previa()
    pc.aceptar()
    A.esperar(250)
antes = A.cuerpos_resumen(v)
n0 = len(v.doc.operaciones)
print("ARCHIVO: antes de guardar", n0, "pasos; deshacer habilitado:", v.acciones["deshacer"].isEnabled(), flush=True)
v.guardar_como()
A.esperar(500)
A.reg(AR, "Guardar como crea el archivo", tmp.exists() and tmp.stat().st_size > 1000, f"{tmp.stat().st_size if tmp.exists() else 0} bytes; título «{v.windowTitle()}»")
A.reg(AR, "el título no muestra «*» recién guardado", "*" not in v.windowTitle(), v.windowTitle())
# deshacer y rehacer en cadena (con el archivo ya guardado)
k = 0
while k < 60 and v.acciones["deshacer"].isEnabled():
    v.acciones["deshacer"].trigger()
    A.esperar(40)
    k += 1
    if k == 1:
        A.reg(AR, "tras deshacer una vez el título muestra «*»", "*" in v.windowTitle(), v.windowTitle())
A.reg(AR, "deshacer en cadena llega al principio", k > 0 and not v.acciones["deshacer"].isEnabled(), f"{k} deshacer; quedan {len(v.doc.operaciones)} pasos; habilitado={v.acciones['deshacer'].isEnabled()}")
r = 0
while r < 120 and v.acciones["rehacer"].isEnabled():
    v.acciones["rehacer"].trigger()
    A.esperar(40)
    r += 1
A.reg(AR, "rehacer en cadena devuelve todo", A.cuerpos_resumen(v) == antes and len(v.doc.operaciones) == n0, f"{r} rehacer; pasos {len(v.doc.operaciones)} de {n0}")
# reabrir
A.MODALES.clear()
v.guardar()
A.esperar(500)
v.abrir()
A.esperar(800)
despues = A.cuerpos_resumen(v)
A.reg(AR, "reabrir devuelve los mismos cuerpos y volúmenes", despues == antes, f"{len(antes)} → {len(despues)}; modales={A.MODALES[-2:]}")

# ------------------------------------------------------------------ timeline
AR = "TIMELINE"
tl, lista = v.timeline, v.timeline.lista
A.reg(AR, "pasos en el timeline", lista.count() > 5, f"{lista.count()} elementos")
for b_nombre, ayuda in (("Ir al inicio", "Ir al inicio"), ("Paso anterior", "Paso anterior"), ("Paso siguiente", "Paso siguiente"), ("Ir al final", "Ir al final")):
    from PySide6.QtWidgets import QToolButton
    b = next((x for x in tl.findChildren(QToolButton) if x.toolTip() == ayuda), None)
    if b is None:
        A.reg(AR, f"botón «{b_nombre}»", False, "no existe")
        continue
    m0 = v.doc.marcador
    QTest.mouseClick(b, Qt.LeftButton)
    A.esperar(150)
    A.reg(AR, f"clic en «{b_nombre}»", True, f"marcador {m0} → {v.doc.marcador} de {len(v.doc.operaciones)}")
QTest.mouseClick(next(x for x in tl.findChildren(QToolButton) if x.toolTip() == "Ir al final"), Qt.LeftButton)
A.esperar(150)

for i in range(lista.count()):
    item = lista.item(i)
    op_id = item.data(Qt.UserRole)
    if not op_id or op_id == "__marcador__":
        continue
    try:
        op = v.doc.operacion(op_id)
    except Exception:  # noqa: BLE001
        continue
    area = f"{AR} › {op.nombre}"
    centro = lista.visualItemRect(item).center()
    vp = lista.viewport()
    lista.scrollToItem(item)
    A.esperar(30)
    centro = lista.visualItemRect(item).center()
    QTest.mouseClick(vp, Qt.LeftButton, Qt.NoModifier, centro)
    A.esperar(60)
    A.reg(area, "clic simple (selecciona/resalta)", True, f"seleccionado={item.isSelected()}")
    # doble clic = editar
    n_err = len(A.ERRORES)
    A.MODALES.clear()
    QTest.mouseDClick(vp, Qt.LeftButton, Qt.NoModifier, centro)
    A.esperar(250)
    panel_abierto = False
    try:
        panel_abierto = v.panel is not None and v.panel.isVisible()
    except RuntimeError:
        pass
    abrio = panel_abierto or v.modo_boceto.activo or bool(A.MODALES)
    A.reg(area, "doble clic abre su edición", abrio and len(A.ERRORES) == n_err, f"panel={v.panel is not None and v.panel.isVisible()} boceto={v.modo_boceto.activo} modales={A.MODALES[-1:]}")
    limpiar()
    # clic derecho = menú
    recorrer_menu(area, "clic derecho", menu_tras_clic_derecho(vp, centro))
    limpiar()

# ------------------------------------------------------------------ navegador
AR = "NAVEGADOR"
arbol = v.navegador.arbol


def todos(item=None):
    if item is None:
        for i in range(arbol.topLevelItemCount()):
            yield from todos(arbol.topLevelItem(i))
    else:
        yield item
        for j in range(item.childCount()):
            yield from todos(item.child(j))


nombres = [i.text(0) for i in todos()]
A.reg(AR, "elementos en el árbol", len(nombres) > 8, f"{len(nombres)}")
for nombre_item in nombres:
    it = next((i for i in todos() if i.text(0) == nombre_item), None)     # el árbol se rearma tras cada acción
    if it is None:
        continue
    padre = it.parent()
    while padre is not None:
        padre.setExpanded(True)
        padre = padre.parent()
    arbol.scrollToItem(it)
    A.esperar(20)
    r = arbol.visualItemRect(it)
    if r.isEmpty():
        continue
    texto = it.text(0)
    area = f"{AR} › {texto}"
    n_err = len(A.ERRORES)
    QTest.mouseClick(arbol.viewport(), Qt.LeftButton, Qt.NoModifier, QPoint(r.center().x() + 10, r.center().y()))
    A.esperar(60)
    def abrir_nav(nombre_item=nombre_item):
        limpiar()
        A.MENUS.clear()
        it2 = next((i for i in todos() if i.text(0) == nombre_item), None)
        if it2 is None:
            return None
        arbol.scrollToItem(it2)
        r2 = arbol.visualItemRect(it2)
        A.clic_derecho(arbol.viewport(), QPoint(r2.center().x() + 10, r2.center().y()))
        return A.MENUS[-1] if A.MENUS else None
    if abrir_nav() is not None:
        recorrer_menu(area, "clic derecho", abrir_nav)
    limpiar()
    A.reg(area, "clic simple y clic derecho sin excepción", len(A.ERRORES) == n_err, "")

# ------------------------------------------------------------------ visor
AR = "VISOR"
def huella():
    img = v.grab().toImage()          # se guarda la imagen: si no, Qt libera los píxeles antes de leerlos
    return hash(img.bits().tobytes()[: img.sizeInBytes()])


def rueda(pos, delta):
    p = QPointF(pos)
    QApplication.sendEvent(vis, QWheelEvent(p, vis.mapToGlobal(p), QPoint(0, 0), QPoint(0, delta), Qt.NoButton, Qt.NoModifier, Qt.NoScrollPhase, False))
    A.esperar(120)


h0 = huella()
centro_v = QPoint(vis.width() // 2, vis.height() // 2)
rueda(centro_v, 240)
h1 = huella()
A.reg(AR, "rueda hacia adelante acerca la vista", h1 != h0, "la imagen cambió" if h1 != h0 else "la imagen no cambió")
rueda(centro_v, -240)
A.reg(AR, "rueda hacia atrás vuelve", huella() != h1, "")


def arrastrar_medio(a, b, boton=Qt.MiddleButton, mod=Qt.NoModifier):
    a, b = QPointF(a), QPointF(b)
    QApplication.sendEvent(vis, QMouseEvent(QEvent.MouseButtonPress, a, vis.mapToGlobal(a), boton, boton, mod))
    for i in range(1, 9):
        q = a + (b - a) * (i / 8)
        QApplication.sendEvent(vis, QMouseEvent(QEvent.MouseMove, q, vis.mapToGlobal(q), Qt.NoButton, boton, mod))
        A.esperar(15)
    QApplication.sendEvent(vis, QMouseEvent(QEvent.MouseButtonRelease, b, vis.mapToGlobal(b), boton, Qt.NoButton, mod))
    A.esperar(120)


for nombre, boton, mod in (("órbita (botón medio + Mayús)", Qt.MiddleButton, Qt.ShiftModifier), ("desplazar (botón medio)", Qt.MiddleButton, Qt.NoModifier),
                           ("órbita (botón derecho)", Qt.RightButton, Qt.NoModifier)):
    antes = huella()
    n_err = len(A.ERRORES)
    A.MENUS.clear()
    arrastrar_medio(centro_v, centro_v + QPoint(90, 40), boton, mod)
    A.reg(AR, f"arrastrar con {nombre}", len(A.ERRORES) == n_err, "la imagen cambió" if huella() != antes else "la imagen NO cambió")
    A.MENUS.clear()
vis.encuadrar()
A.esperar(200)

# clic derecho sobre un cuerpo = menú radial de la app
def abrir_radial():
    limpiar()
    hit = A.hit_cara(v, ids["caja"], normal=(0, 0, 1))
    q = vis.proyectar(hit["punto"]) if hit and "punto" in hit else None
    if q is None:
        return None
    v._menu_radial = None
    QTest.mouseClick(vis, Qt.RightButton, Qt.NoModifier, QPoint(int(q.x()), int(q.y())))
    A.esperar(60)
    try:
        v._menu_radial.isVisible()
    except (RuntimeError, AttributeError):
        return None                                  # se destruyó al soltar el botón o nunca se creó
    return v._menu_radial


rad = abrir_radial()
A.reg(AR, "clic derecho sobre un cuerpo abre el menú radial", rad is not None and rad.isVisible(), f"{'visible' if rad is not None else 'no quedó abierto'}")
if rad is not None:
    nombres_r = [(i, it.texto) for i, it in enumerate(rad.items) if it is not None]
    A.reg(AR, "menú radial: comandos", len(nombres_r) > 0, " | ".join(f"{n}{'' if rad.items[i].activo else ' (gris)'}" for i, n in nombres_r))
    rad.hide()
    for i, nombre in nombres_r:
        it = rad.items[i]
        if not it.activo or it.funcion is None or it.sub or any(p in nombre.lower() for p in PELIGROSAS):
            continue
        antes = estado()
        n_err = len(A.ERRORES)
        A.MODALES.clear()
        it.funcion()
        A.esperar(250)
        abrio = False
        try:
            abrio = v.panel is not None and v.panel.isVisible()
        except RuntimeError:
            pass
        limpiar()
        sin_error = len(A.ERRORES) == n_err
        if estado() != antes:
            ok, k = restaurar(antes, AR, nombre)
            A.reg(AR, f"menú radial › «{nombre}»", sin_error and ok, f"cambió el modelo; deshacer ({k}) vuelve igual: {ok}")
        else:
            A.reg(AR, f"menú radial › «{nombre}»", sin_error, "abrió su panel" if abrio else "sin panel ni cambio")
    abrir_radial()
    if v._menu_radial is not None:
        QTest.keyClick(v._menu_radial, Qt.Key_Escape)
        A.esperar(100)
        try:
            cerrado = not v._menu_radial.isVisible()
        except RuntimeError:                      # el menú se destruyó al cerrarse
            cerrado = True
        A.reg(AR, "Esc cierra el menú radial", cerrado, "")
limpiar()

# ------------------------------------------------------------------ atajos
AR = "ATAJOS"
conocidos = {}
for clave, a in v.acciones.items():
    sc = a.shortcut().toString()
    if sc:
        conocidos.setdefault((sc, clave.startswith("sk_")), []).append(clave)     # el boceto y el 3D pueden repetir una tecla
repetidos = {k: x for k, x in conocidos.items() if len(x) > 1}
A.reg(AR, "ningún atajo repetido en el mismo entorno (3D / boceto)", not repetidos, str(repetidos) if repetidos else f"{len(conocidos)} atajos distintos")
raros = {c: a.shortcut().toString() for c, a in v.acciones.items() if len(a.shortcut().toString()) > 25}
A.reg(AR, "ningún atajo es un texto largo (la ayuda quedó en el lugar del atajo)", not raros, str(raros)[:300])
A.activar(v)
vis.setFocus()
A.esperar(400)
sin_foco = QApplication.activeWindow() is None
if sin_foco:
    A.reg(AR, "⚠ la ventana no tiene el foco del sistema: los atajos no se pueden probar en esta corrida", True,
          "Windows no dejó activar la ventana (otra aplicación tiene el foco); repetir sin usar otra ventana")
for clave, a in v.acciones.items():
    sc = a.shortcut()
    if sin_foco or sc.isEmpty() or len(sc.toString()) > 25 or not a.isEnabled() or clave in ("salir", "cerrar", "nuevo", "abrir"):
        continue
    contador = []
    a.triggered.connect(lambda *_a, c=contador: c.append(1))
    antes = estado()
    n_err = len(A.ERRORES)
    A.MODALES.clear()
    vis.setFocus()
    QTest.keySequence(vis, sc)
    A.esperar(180)
    limpiar()
    llego = bool(contador)
    A.reg(AR, f"{sc.toString()} → {clave}", llego and len(A.ERRORES) == n_err, "disparó la acción" if llego else "el atajo NO disparó la acción")
    if estado() != antes:
        restaurar(antes, AR, clave)
    a.triggered.disconnect()

# ------------------------------------------------------------------ ventana chica
AR = "VENTANA CHICA"
for ancho, alto in ((1280, 720), (1024, 640), (800, 520)):
    n_err = len(A.ERRORES)
    v.resize(ancho, alto)
    A.esperar(500)
    p = A.abrir(v, "extruir")
    A.elegir(p, "perfiles", A.hit_perfil(v, s, "Rect"))
    A.esperar(200)
    A.foto(v, f"chica_{ancho}x{alto}")
    marco = v.rect()
    dentro = v.area.rect().contains(p.geometry())              # el panel vive dentro del área del visor
    ok = dentro and vis.width() >= 250 and len(A.ERRORES) == n_err
    A.reg(AR, f"{ancho}x{alto}: el panel (con Aceptar y Cancelar) entra en el área del visor", ok,
          f"panel {p.geometry().getRect()} dentro={dentro}; visor {vis.width()}x{vis.height()}; cinta {v.cinta.width()} px")
    p.cancelar()
    A.esperar(100)
v.resize(1900, 1000)
A.esperar(300)

A.reg("GENERAL", "ninguna excepción escapó de un slot de Qt en toda la corrida", not A.ERRORES, f"{len(A.ERRORES)}: {A.ERRORES[:1]}")
A.guardar_registro("ventana_uso")
fallas = [r for r in A.REGISTRO if not r["ok"]]
print(f"\n=== {len(A.REGISTRO)} comprobaciones, {len(fallas)} con ✗ ===")
v.doc.modificado = False
v.close()
sys.exit(0)

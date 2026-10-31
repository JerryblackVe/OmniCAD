# -*- coding: utf-8 -*-
"""BOCETO · Simetría (Mirror) con el panel SIMETRÍA, como la usa una persona: botón de la cinta, clic en las líneas, campo
Eje de simetría, vista previa, Aceptar / Cancelar / Enter / Esc, ventana de selección, mensajes de error, deshacer y
rehacer, ventanas chicas, y lo que viene después (perfiles, extrusión, guardar y reabrir, cotas). Eventos simulados al
Lienzo y a los botones del panel (nunca el cursor real). Caso del video de Fusion: A(-50, 0), B(0, 0), C(0, 70) con la
vertical BC como eje (el reflejo da A'(50, 0)). Ver evidencias/simetria_boceto_2026-10-30/INFORME.md."""
import math
import os
import tempfile

import arnes as A
from omnicad import api
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QPushButton, QToolButton

AR = "BOCETO·SIMETRÍA"
s = api.Sesion()


def L(nombre, **a):
    r = api.llamar(s, nombre, a)
    assert r["ok"], (nombre, a, r)
    return r["result"]


L("create_sketch", name="S", plane="XY")
tri = [L("draw_line", sketch="S", **d)["entities"][0]["id"] for d in (
    {"start_x": -50, "start_y": 0, "end_x": 0, "end_y": 0}, {"start_x": 0, "start_y": 0, "end_x": 0, "end_y": 70},
    {"start_x": 0, "start_y": 70, "end_x": -50, "end_y": 0})]
AB, BC, CA = tri
circ = L("draw_circle", sketch="S", center_x=-120, center_y=-60, radius=12)["entities"][0]["id"]
app, v = A.iniciar(s.doc)
v.editar_operacion(s.paso("S").id)
A.esperar(500)
lz = v.modo_boceto.lienzo
panel = v.modo_boceto.simetria
A.reg(AR, "entrar al boceto: el modo tiene el panel SIMETRÍA (oculto)", v.modo_boceto.activo and panel is not None and not panel.isVisible(), "")
MENSAJES = []
lz.mensaje.connect(MENSAJES.append)
lz.visor.objetivo = lz.plano.a_3d(-45, 5)
lz.visor.distancia = 260 / 2 / math.sin(math.radians(lz.visor.fov) / 2) * 1.3
lz.visor.update()
lz.update()
A.esperar(300)


def px(x, y):
    return lz.a_px(x, y).toPoint()


def clic(x, y, mod=Qt.NoModifier):
    QTest.mouseClick(lz, Qt.LeftButton, mod, px(x, y))
    A.esperar(70)


def tecla(k, mod=Qt.NoModifier):
    QTest.keyClick(lz, k, mod)
    A.esperar(90)


def ventana(x0, y0, x1, y1):
    """Arrastra una ventana de selección con el botón izquierdo (press, varios movimientos, release)."""
    a, b = QPointF(px(x0, y0)), QPointF(px(x1, y1))
    QTest.mousePress(lz, Qt.LeftButton, Qt.NoModifier, a.toPoint())
    for i in range(1, 7):
        q = a + (b - a) * (i / 6)
        QApplication.sendEvent(lz, QMouseEvent(QEvent.MouseMove, q, lz.mapToGlobal(q), Qt.NoButton, Qt.LeftButton, Qt.NoModifier))
        A.esperar(20)
    QTest.mouseRelease(lz, Qt.LeftButton, Qt.NoModifier, b.toPoint())
    A.esperar(120)


def boton_cinta(clave):
    accion = v.modo_boceto.acciones[clave]
    return next(b for b in v.cinta.findChildren(QToolButton) if b.defaultAction() is accion and b.isVisible())


def pulsar(boton):
    QTest.mouseClick(boton, Qt.LeftButton)
    A.esperar(120)


def boton_cancelar():
    return next(b for b in panel.findChildren(QPushButton) if b.text() == "Cancelar")


def n_curvas():
    return len(lz.b.curvas)


def n_restr(tipo):
    return sum(1 for r in lz.b.restricciones.values() if r.tipo == tipo)


def texto_objetos():
    return panel.filas["seleccion"].boton.text()


def texto_eje():
    return panel.filas["eje"].boton.text()


def abrir_simetria():
    """Lo que hace la persona: apretar «Simetría» en la cinta del boceto."""
    lz.set_herramienta("seleccionar")
    lz.seleccion = []
    pulsar(boton_cinta("sk_simetria"))


def elegir_tres_lineas():
    for xy in ((-25, 0), (0, 35), (-25, 35)):
        clic(*xy)


def puntos_de(polis):
    return [q for poli in polis for q in poli]


def hay_punto(polis, xy, tol=1e-6):
    return any(math.dist(q, xy) < tol for q in puntos_de(polis))


def probar(nombre, funcion):
    try:
        funcion()
    except Exception as e:  # noqa: BLE001
        import traceback
        A.reg(AR, f"{nombre}: EXCEPCIÓN", False, f"{type(e).__name__}: {e}")
        traceback.print_exc()
        lz.set_herramienta("seleccionar")


# ---------------------------------------------------------------- 1) apretar el botón: aparece el panel
def abrir():
    abrir_simetria()
    A.reg(AR + " · panel", "el botón de la cinta queda marcado y la herramienta es «simetria»",
          lz.herramienta == "simetria" and v.modo_boceto.acciones["sk_simetria"].isChecked(), f"herr={lz.herramienta}")
    A.reg(AR + " · panel", "aparece el panel SIMETRÍA", panel.isVisible(), "")
    titulo = next((w.text() for w in panel.findChildren(type(panel.guia)) if w.objectName() == "titulo_comando"), "")
    A.reg(AR + " · panel", "título «SIMETRÍA», campos Objetos y Eje de simetría y casilla Vista previa activada",
          titulo == "SIMETRÍA" and panel.casilla.isChecked() and "Seleccionar" in texto_objetos() and "Seleccionar" in texto_eje(), titulo)
    A.reg(AR + " · panel", "el campo Objetos es el activo y Aceptar está deshabilitado",
          panel.filas["seleccion"].boton.property("activa") is True and not panel.boton_ok.isEnabled(), "")
    A.reg(AR + " · panel", "la guía dice qué hacer", "geometría" in panel.guia.text(), panel.guia.text())
    A.foto(v, "simetria_1_panel_vacio")


probar("abrir", abrir)


# ---------------------------------------------------------------- 2) elegir las tres líneas del triángulo
def objetos():
    elegir_tres_lineas()
    A.reg(AR + " · objetos", "tres clics eligen las tres líneas y el panel dice «3 seleccionados»",
          sorted(lz.seleccion) == sorted(tri) and texto_objetos() == "3 seleccionados", f"sel={lz.seleccion} panel={texto_objetos()}")
    A.reg(AR + " · objetos", "sin eje, Aceptar sigue deshabilitado y la guía manda a elegir la línea",
          not panel.boton_ok.isEnabled() and "línea" in panel.guia.text(), panel.guia.text())
    A.foto(v, "simetria_2_tres_lineas")


probar("objetos", objetos)


# ---------------------------------------------------------------- 3) el campo Eje de simetría, la línea y la vista previa
def eje():
    pulsar(panel.filas["eje"].boton)
    A.reg(AR + " · eje", "clic en el campo Eje de simetría lo activa", lz.fase == "eje" and panel.filas["eje"].boton.property("activa") is True, f"fase={lz.fase}")
    clic(0, 35)
    A.reg(AR + " · eje", "clic sobre la vertical BC la elige como eje (no la saca de la selección)",
          lz._eje_simetria == BC and texto_eje() == "1 seleccionado" and BC in lz.seleccion, f"eje={lz._eje_simetria} sel={lz.seleccion}")
    A.reg(AR + " · eje", "Aceptar se habilita y no se creó nada todavía", panel.boton_ok.isEnabled() and n_curvas() == 4, f"curvas={n_curvas()}")
    polis, error = lz._calcular_simetria()
    A.reg(AR + " · previa", "la vista previa tiene A'(50, 0), B(0, 0) y C(0, 70) y ningún error",
          hay_punto(polis, (50, 0)) and hay_punto(polis, (0, 0)) and hay_punto(polis, (0, 70)) and not error, f"{len(polis)} polilíneas, error={error!r}")
    A.reg(AR + " · previa", "la previa no es parte del modelo: el boceto sigue con 3 líneas + el círculo", n_curvas() == 4, "")
    lz.update()
    A.esperar(150)
    con = lz.grab().toImage()
    A.foto(v, "simetria_3_eje_y_previa")
    panel.casilla.setChecked(False)
    A.esperar(150)
    sin = lz.grab().toImage()
    A.reg(AR + " · previa", "la casilla Vista previa apaga y enciende la copia dibujada (la imagen cambia)",
          not lz.previa_simetria and con != sin, f"previa={lz.previa_simetria}")
    A.foto(v, "simetria_3b_sin_previa")
    panel.casilla.setChecked(True)
    A.esperar(150)
    A.reg(AR + " · previa", "al volver a tildarla, la imagen es la de antes", lz.previa_simetria and lz.grab().toImage() == con, "")


probar("eje", eje)


# ---------------------------------------------------------------- 4) Esc y Cancelar no tocan el boceto
def cancelar():
    antes = n_curvas()
    tecla(Qt.Key_Escape)
    A.reg(AR + " · cancelar", "Esc cierra el panel, vuelve a Seleccionar y no cambia el boceto",
          not panel.isVisible() and lz.herramienta == "seleccionar" and n_curvas() == antes and n_restr("simetrica") == 0, f"curvas={n_curvas()}")
    abrir_simetria()
    elegir_tres_lineas()
    pulsar(panel.filas["eje"].boton)
    clic(0, 35)
    pulsar(boton_cancelar())
    A.reg(AR + " · cancelar", "el botón Cancelar hace lo mismo",
          not panel.isVisible() and lz.herramienta == "seleccionar" and n_curvas() == antes, f"curvas={n_curvas()}")
    abrir_simetria()
    pulsar(panel.findChildren(QToolButton)[0])
    A.reg(AR + " · cancelar", "la ✕ del encabezado también cancela", not panel.isVisible() and lz.herramienta == "seleccionar", "")


probar("cancelar", cancelar)


# ---------------------------------------------------------------- 5) Aceptar crea la copia: real, con restricciones, deshacer y rehacer
def aceptar():
    abrir_simetria()
    elegir_tres_lineas()
    pulsar(panel.filas["eje"].boton)
    clic(0, 35)
    antes = n_curvas()
    pulsar(panel.boton_ok)
    A.reg(AR + " · aceptar", "Aceptar crea las 2 curvas reflejadas (las del eje no se duplican) y cierra el panel",
          n_curvas() == antes + 2 and not panel.isVisible() and lz.herramienta == "seleccionar", f"curvas {antes}->{n_curvas()}")
    pts = sorted((round(p.x, 6), round(p.y, 6)) for p in lz.b.puntos.values() if p.id in {q for c in lz.b.curvas.values() for q in c.puntos()})
    A.reg(AR + " · aceptar", "aparece A'(50, 0) y B y C siguen siendo un solo punto cada uno",
          (50.0, 0.0) in pts and pts.count((0.0, 0.0)) == 1 and pts.count((0.0, 70.0)) == 1, str(pts))
    A.reg(AR + " · aceptar", "quedó la restricción de simetría y el solver no ve conflictos", n_restr("simetrica") == 1 and lz.resultado.ok, f"simetrica={n_restr('simetrica')} ok={lz.resultado.ok}")
    A.foto(v, "simetria_4_aceptada")
    tecla(Qt.Key_Z, Qt.ControlModifier)
    A.reg(AR + " · deshacer", "Ctrl+Z deshace la simetría entera de una vez", n_curvas() == antes and n_restr("simetrica") == 0, f"curvas={n_curvas()}")
    tecla(Qt.Key_Y, Qt.ControlModifier)
    A.reg(AR + " · deshacer", "Ctrl+Y la rehace", n_curvas() == antes + 2 and n_restr("simetrica") == 1, f"curvas={n_curvas()}")
    A.reg(AR + " · aceptar", "quedan 6 curvas: las 3 del triángulo, las 2 copias y el círculo", n_curvas() == 6, f"curvas={n_curvas()}")


probar("aceptar", aceptar)


# ---------------------------------------------------------------- 6) lo mismo solo con el teclado: Enter pasa al eje y Enter acepta
def con_enter():
    tecla(Qt.Key_Z, Qt.ControlModifier)                      # vuelve a 3 líneas + círculo
    antes = n_curvas()
    abrir_simetria()
    elegir_tres_lineas()
    tecla(Qt.Key_Return)
    A.reg(AR + " · Enter", "con la geometría lista, Enter pasa al campo Eje de simetría", lz.fase == "eje" and panel.filas["eje"].boton.property("activa") is True, f"fase={lz.fase}")
    tecla(Qt.Key_Return)
    A.reg(AR + " · Enter", "Enter sin línea de simetría no crea nada ni cierra el panel", n_curvas() == antes and panel.isVisible(), f"curvas={n_curvas()}")
    clic(0, 35)
    tecla(Qt.Key_Return)
    A.reg(AR + " · Enter", "Enter con todo elegido acepta", n_curvas() == antes + 2 and not panel.isVisible(), f"curvas {antes}->{n_curvas()}")
    tecla(Qt.Key_Z, Qt.ControlModifier)


probar("enter", con_enter)


# ---------------------------------------------------------------- 7) ventana de selección y ✕ de cada campo
def ventana_y_borrar():
    abrir_simetria()
    ventana(-70, -15, 15, 85)                                # de izquierda a derecha: lo que queda adentro
    A.reg(AR + " · ventana", "arrastrar una ventana en el campo Objetos elige las 3 líneas del triángulo (y no el círculo lejano)",
          set(tri) <= set(lz.seleccion) and circ not in lz.seleccion, f"sel={lz.seleccion}")
    pulsar(panel.filas["seleccion"].borrar)
    A.reg(AR + " · ventana", "la ✕ de Objetos vacía la selección", lz.seleccion == [] and "Seleccionar" in texto_objetos() and lz.fase == "seleccion", f"sel={lz.seleccion}")
    elegir_tres_lineas()
    pulsar(panel.filas["eje"].boton)
    clic(0, 35)
    pulsar(panel.filas["eje"].borrar)
    A.reg(AR + " · ventana", "la ✕ del eje lo quita y vuelve a deshabilitar Aceptar", lz._eje_simetria is None and not panel.boton_ok.isEnabled() and lz.fase == "eje", "")
    tecla(Qt.Key_Escape)


probar("ventana", ventana_y_borrar)


# ---------------------------------------------------------------- 8) mensajes claros ante lo que no sirve
def errores():
    antes = n_curvas()
    abrir_simetria()
    pulsar(panel.filas["eje"].boton)
    A.reg(AR + " · mensajes", "sin geometría elegida, el campo Eje avisa «Primero elegí la geometría»",
          "Primero" in panel.mensaje.text() and panel.mensaje.isVisible() and lz.fase == "seleccion", panel.mensaje.text())
    clic(-25, 0)
    pulsar(panel.filas["eje"].boton)
    clic(-60, 60)                                            # espacio vacío
    A.reg(AR + " · mensajes", "clic en el vacío en lugar del eje: «Ahí no hay ninguna línea»", "no hay ninguna línea" in panel.mensaje.text() and lz._eje_simetria is None, panel.mensaje.text())
    clic(-120, -48)                                          # el círculo
    A.reg(AR + " · mensajes", "clic sobre un círculo: «la línea de simetría tiene que ser recta»", "recta" in panel.mensaje.text() and lz._eje_simetria is None, panel.mensaje.text())
    clic(-25, 0)                                             # la misma línea que ya es objeto, ahora como eje
    A.reg(AR + " · mensajes", "la única línea elegida como eje: «elegí la geometría a reflejar» y Aceptar deshabilitado",
          "Además de la línea" in panel.mensaje.text() and not panel.boton_ok.isEnabled(), panel.mensaje.text())
    tecla(Qt.Key_Return)
    A.reg(AR + " · mensajes", "Enter en ese estado no crea nada", n_curvas() == antes and panel.isVisible(), f"curvas={n_curvas()}")
    A.foto(v, "simetria_5_mensaje")
    tecla(Qt.Key_Escape)


probar("errores", errores)


# ---------------------------------------------------------------- 9) ventanas chicas: Aceptar y Cancelar tienen que entrar
def chica(ancho, alto):
    v.resize(ancho, alto)
    A.esperar(500)
    v.area.reubicar()
    abrir_simetria()
    elegir_tres_lineas()
    pulsar(panel.filas["eje"].boton)
    clic(0, 35)
    A.esperar(200)
    area = v.area.rect()
    ok = panel.isVisible() and all(area.contains(b.mapTo(v.area, b.rect().topLeft())) and area.contains(b.mapTo(v.area, b.rect().bottomRight()))
                                   for b in (panel.boton_ok, boton_cancelar()))
    barra = v.area.barra
    libre = not panel.geometry().intersects(barra.geometry()) if barra is not None and barra.isVisible() else True
    A.reg(AR + f" · {ancho}x{alto}", "el panel con Aceptar y Cancelar entra en la ventana", ok,
          f"panel={panel.geometry().getRect()} área={area.getRect()} ok={panel.boton_ok.geometry().getRect()}")
    A.reg(AR + f" · {ancho}x{alto}", "y la barra de vista de abajo no lo tapa", libre, f"barra={barra.geometry().getRect() if barra is not None else None}")
    A.foto(v, f"simetria_6_{ancho}x{alto}")
    tecla(Qt.Key_Escape)


for ancho, alto in ((1024, 640), (800, 520)):
    probar(f"chica {ancho}", lambda a=ancho, h=alto: chica(a, h))
v.resize(1900, 1000)
A.esperar(500)
lz.visor.objetivo = lz.plano.a_3d(-45, 5)
lz.update()
A.esperar(200)


# ---------------------------------------------------------------- 10) terminar el boceto, extruir las dos mitades, guardar y reabrir
def despues():
    abrir_simetria()
    elegir_tres_lineas()
    pulsar(panel.filas["eje"].boton)
    clic(0, 35)
    pulsar(panel.boton_ok)
    A.reg(AR + " · después", "la copia está hecha", n_curvas() == 6, f"curvas={n_curvas()}")
    v.modo_boceto.terminar()
    A.esperar(400)
    sk = L("get_sketch", sketch="S")
    areas = sorted(round(p["area"], 3) for p in sk["profiles"])
    A.reg(AR + " · perfiles", "al terminar, el boceto tiene 3 perfiles: círculo y las dos mitades del triángulo (1750 mm² cada una)", areas == [round(math.pi * 144, 3), 1750.0, 1750.0], str(areas))
    L("extrude", sketch="S", profile=[i for i, p in enumerate(sk["profiles"]) if abs(p["area"] - 1750) < 1e-6], distance=10)
    vol = L("get_physical_properties")["total"]["volume"]
    A.reg(AR + " · extrusión", "las dos mitades extruyen 10 mm: volumen 35 000 mm³ (2 × 1750 × 10)", vol is not None and abs(vol - 35000) < 1e-3, f"volumen={vol}")
    A.foto(v, "simetria_7_extruido")
    ruta = os.path.join(tempfile.mkdtemp(prefix="omnicad_sim_"), "simetria.omnicad")
    L("save_document", path=ruta)
    s2 = api.Sesion()
    r2 = api.llamar(s2, "open_document", {"path": ruta})
    sk2 = api.llamar(s2, "get_sketch", {"sketch": "S"})["result"]
    A.reg(AR + " · guardar", "guardar y reabrir conserva las curvas reflejadas y la restricción de simetría",
          r2["ok"] and len(sk2["entities"]) == len(sk["entities"]) and any(c["type"] == "symmetry" for c in sk2["constraints"]),
          f"entidades {len(sk['entities'])}->{len(sk2['entities'])} tipos={sorted({c['type'] for c in sk2['constraints']})}")


probar("después", despues)


# ---------------------------------------------------------------- 11) paramétrico: cambiar una cota del original y la copia lo sigue
def parametrico():
    L("add_constraint", sketch="S", type="fix", entities=[BC])         # el eje no se mueve: la base es lo que cambia
    d = L("add_dimension", sketch="S", type="distance", entities=[AB], value=50)["dimension"]["id"]
    L("edit_dimension", dimension=d, value=60)
    xs = sorted(round(q["x"], 6) for q in L("get_sketch", sketch="S")["points"])
    A.reg(AR + " · paramétrico", "al cambiar la base del triángulo de 50 a 60, la copia sigue: el reflejo queda en x = +60 (la simetría se conserva)",
          -60.0 in xs and 60.0 in xs, str(sorted(set(xs))))


probar("paramétrico", parametrico)

A.reg(AR, "no se escapó ninguna excepción dentro de un slot de Qt", not A.ERRORES, "; ".join(A.ERRORES)[:300])
A.guardar_registro("simetria_boceto")
fallas = sum(1 for r in A.REGISTRO if not r["ok"])
print(f"=== {len(A.REGISTRO)} comprobaciones, {fallas} con ✗", flush=True)

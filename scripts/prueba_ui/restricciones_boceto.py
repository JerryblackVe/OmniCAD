# -*- coding: utf-8 -*-
"""BOCETO · las 13 restricciones del menú RESTRICCIONES, como las usa una persona: botón de la cinta, clic en la
geometría con el mouse, el símbolo (glifo) que aparece, arrastrar un punto con el mouse y comprobar que la relación
se conserva, elegir el símbolo, Supr, clic derecho, Ctrl+Z / Ctrl+Y, repetir una restricción (sobra), contradecirla
(conflicto) y guardar / reabrir. La relación matemática de cada una se mide con los mismos invariantes de
clon/tests/test_restricciones_matematica.py (no con el solver). Eventos simulados al Lienzo (nunca el cursor real).
Evidencia: evidencias/restricciones_boceto_2026-10-31/."""
import importlib.util
import math
import os
import tempfile

import arnes as A
from omnicad import api
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QToolButton

AR = "BOCETO·RESTRICCIONES"
s = api.Sesion()
MATE = importlib.util.spec_from_file_location("mate", A.RAIZ / "clon" / "tests" / "test_restricciones_matematica.py")
mate = importlib.util.module_from_spec(MATE)
MATE.loader.exec_module(mate)


def L(nombre, **a):
    r = api.llamar(s, nombre, a)
    assert r["ok"], (nombre, a, r)
    return r["result"]


L("create_sketch", name="S", plane="XY")
app, v = A.iniciar(s.doc)
v.editar_operacion(s.paso("S").id)
A.esperar(500)
lz = v.modo_boceto.lienzo
A.reg(AR, "entrar al boceto", v.modo_boceto.activo and lz is not None, "")
MENSAJES = []
lz.mensaje.connect(MENSAJES.append)
HERRAMIENTA = {"horizontal": "r_horizontal_vertical", "vertical": "r_horizontal_vertical", "coincidente": "r_coincidente",
               "tangente": "r_tangente", "igual": "r_igual", "paralela": "r_paralela",
               "perpendicular": "r_perpendicular", "fijo": "r_fijo", "punto_medio": "r_punto_medio",
               "concentrica": "r_concentrica", "colineal": "r_colineal", "simetrica": "r_simetria",
               "curvatura": "r_curvatura", "poligono": "r_poligono"}


def px(x, y):
    return lz.a_px(x, y).toPoint()


def clic(x, y, mod=Qt.NoModifier):
    QTest.mouseClick(lz, Qt.LeftButton, mod, px(x, y))
    A.esperar(70)


def tecla(k, mod=Qt.NoModifier):
    QTest.keyClick(lz, k, mod)
    A.esperar(90)


def mover_a(q):
    q = QPointF(q)
    QApplication.sendEvent(lz, QMouseEvent(QEvent.MouseMove, q, lz.mapToGlobal(q), Qt.NoButton, Qt.NoButton, Qt.NoModifier))
    A.esperar(40)


def arrastrar(x0, y0, x1, y1, pasos=8):
    """Como la persona: botón apretado sobre el punto, el mouse se mueve de a poco y se suelta."""
    a, b = QPointF(px(x0, y0)), QPointF(px(x1, y1))
    QTest.mousePress(lz, Qt.LeftButton, Qt.NoModifier, a.toPoint())
    for i in range(1, pasos + 1):
        q = a + (b - a) * (i / pasos)
        QApplication.sendEvent(lz, QMouseEvent(QEvent.MouseMove, q, lz.mapToGlobal(q), Qt.NoButton, Qt.LeftButton, Qt.NoModifier))
        A.esperar(25)
    QTest.mouseRelease(lz, Qt.LeftButton, Qt.NoModifier, b.toPoint())
    A.esperar(150)


def boton_cinta(clave):
    accion = v.modo_boceto.acciones[clave]
    return next(b for b in v.cinta.findChildren(QToolButton) if b.defaultAction() is accion and b.isVisible())


def pulsar(boton):
    QTest.mouseClick(boton, Qt.LeftButton)
    A.esperar(120)


def n_restr(tipo=None):
    return sum(1 for r in lz.b.restricciones.values() if tipo is None or r.tipo == tipo)


def repintar():
    lz.repaint()
    A.esperar(60)


def limpiar():
    lz.set_herramienta("seleccionar")
    lz.seleccion = []


def punto_de_clic(b, ent):
    """Dónde hace clic una persona para elegir esa entidad: el punto, o un lugar de la curva lejos de sus extremos."""
    if ent in b.puntos:
        return b.coords(ent)
    prim = b.primitivas(ent)[0]
    t0, t1, _ = mate.dominio(prim)
    t = math.pi / 2 if prim[0] in ("circulo", "elipse") else (t0 + t1) / 2
    if prim[0] == "spline":
        t = t0 + (t1 - t0) * 0.25
    return mate.evaluar_primitiva(prim, t)[0]


def instalar(b):
    """Pone el boceto de un escenario en el Lienzo (el mismo objeto que miden los invariantes)."""
    lz.set_herramienta("seleccionar")
    lz.b = b
    lz.historial.clear()
    lz.pila_rehacer.clear()
    lz.seleccion = []
    lz.resolver()
    lz.encuadrar()
    A.esperar(250)
    repintar()


def glifo(rid):
    repintar()
    return lz._zonas_glifos.get(rid)


def probar(nombre, funcion):
    try:
        funcion()
    except Exception as e:  # noqa: BLE001
        import traceback
        A.reg(AR, f"{nombre}: EXCEPCIÓN", False, f"{type(e).__name__}: {e}")
        traceback.print_exc()
        limpiar()


# ---------------------------------------------------------------- 1) el menú: 13 botones, ícono, tooltip, activan la herramienta
def menu():
    nombres = {"r_horizontal_vertical": "Horizontal/Vertical", "r_coincidente": "Coincidente", "r_tangente": "Tangente",
               "r_igual": "Igual", "r_paralela": "Paralelo", "r_perpendicular": "Perpendicular",
               "r_fijo": "Fijar", "r_punto_medio": "Punto medio", "r_concentrica": "Concéntrica", "r_colineal": "Colineal",
               "r_simetria": "Simetría", "r_curvatura": "Curvatura", "r_poligono": "Polígono"}
    instalar(mate.Boceto())
    for herr, nombre in nombres.items():
        clave = f"sk_{herr}"
        acc = v.modo_boceto.acciones.get(clave)
        A.reg(AR + " · menú", f"{herr}: existe la acción y tiene ícono", acc is not None and not acc.icon().isNull(), "")
        if acc is None:
            continue
        b = boton_cinta(clave)
        A.reg(AR + " · menú", f"{herr}: el botón está activo y su nombre dice «{nombre.split('/')[0]}»",
              b.isEnabled() and nombre.split("/")[0].lower() in (acc.text() + b.toolTip()).lower(),
              f"texto={acc.text()!r} tooltip={b.toolTip()[:60]!r} activo={b.isEnabled()}")
        pulsar(b)
        A.reg(AR + " · menú", f"{herr}: el clic activa la herramienta", lz.herramienta == herr, f"herramienta={lz.herramienta}")
        A.reg(AR + " · menú", f"{herr}: el mensaje de ayuda dice qué hacer", bool(MENSAJES) and nombre.split("/")[0] in MENSAJES[-1],
              MENSAJES[-1][:90] if MENSAJES else "")
        tecla(Qt.Key_Escape)
        A.reg(AR + " · menú", f"{herr}: Esc vuelve a Seleccionar", lz.herramienta == "seleccionar", f"herramienta={lz.herramienta}")
    A.foto(v, "restr_menu")


# ---------------------------------------------------------------- 2) cada restricción: clics → relación → glifo → arrastrar → Supr → Ctrl+Z / Ctrl+Y
def ciclo(nombre):
    b, tipo, ents, cumple, mover, quita = mate.ESCENARIOS[nombre]()
    instalar(b)
    area = AR + f" · {nombre}"
    gdl0, restr0 = lz.resultado.gdl, n_restr()
    herr = HERRAMIENTA[tipo]
    pulsar(boton_cinta(f"sk_{herr}"))
    picks = [ents[0]] if tipo == "poligono" else list(ents)
    # Fusion: una línea, un clic; coincidente/punto medio: primero el punto
    for e in picks:
        clic(*punto_de_clic(b, e))
    A.esperar(120)
    creada = n_restr() == restr0 + 1
    A.reg(area, "los clics con el mouse la crean", creada, f"{restr0}->{n_restr()} msg={MENSAJES[-1:]}")
    if not creada:
        limpiar()
        return
    r = list(lz.b.restricciones.values())[-1]
    A.reg(area, f"es del tipo {tipo}", r.tipo == tipo, f"tipo={r.tipo}")
    A.reg(area, "el solver la deja resuelta y consistente", lz.resultado.ok, lz.resultado.descripcion())
    A.reg(area, "la relación se cumple (invariante matemático medido aparte)", bool(cumple()), "")
    A.reg(area, f"quita {quita} grado(s) de libertad", gdl0 - lz.resultado.gdl == quita, f"{gdl0}->{lz.resultado.gdl}")
    limpiar()
    caja = glifo(r.id)
    A.reg(area, "aparece su símbolo sobre la geometría", caja is not None and lz.rect().contains(caja.toRect()), f"caja={caja}")
    if caja is None:
        return
    A.foto(v, f"restr_{nombre}_1_creada")
    ent = r.entidades[-1] if r.tipo in ("coincidente", "punto_medio") else (r.entidades[2] if r.tipo == "simetrica" else r.entidades[0])
    ancla = lz._ancla(ent)
    cerca = math.hypot(caja.center().x() - ancla.x(), caja.center().y() - ancla.y())
    A.reg(area, "el símbolo está al lado de su entidad (menos de 60 px)", cerca < 60, f"{cerca:.1f}px")
    # arrastrar un punto con el mouse: la relación sigue y el símbolo acompaña
    for pid, x, y in mover[:2]:
        if pid not in b.puntos:
            continue
        x0, y0 = b.coords(pid)
        arrastrar(x0, y0, x, y)
        A.reg(area, f"arrastrar el punto {pid} con el mouse: el boceto sigue consistente", lz.resultado.ok, lz.resultado.descripcion())
        A.reg(area, f"arrastrar el punto {pid}: la relación se conserva", bool(cumple()), f"msg={MENSAJES[-1:]}")
        nueva = glifo(r.id)
        ancla2 = lz._ancla(ent)
        sigue = nueva is not None and abs((nueva.center().x() - ancla2.x()) - (caja.center().x() - ancla.x())) < 1.5 \
            and abs((nueva.center().y() - ancla2.y()) - (caja.center().y() - ancla.y())) < 1.5
        A.reg(area, "el símbolo acompaña a la geometría (no queda en la posición vieja)", sigue,
              f"antes={caja.center()} ancla {ancla}->{ancla2} ahora={None if nueva is None else nueva.center()}")
        caja, ancla = nueva or caja, ancla2
    # elegir el símbolo con un clic: se elige la restricción, no la geometría
    caja = glifo(r.id)
    QTest.mouseClick(lz, Qt.LeftButton, Qt.NoModifier, caja.center().toPoint())
    A.esperar(120)
    A.reg(area, "un clic en el símbolo elige SOLO la restricción", lz.seleccion == [r.id], f"seleccion={lz.seleccion}")
    otras = {k for k in lz.b.restricciones if k != r.id}
    nc, np_ = len(lz.b.curvas), len(lz.b.puntos)
    tecla(Qt.Key_Delete)
    A.reg(area, "Supr la borra", r.id not in lz.b.restricciones, f"restr={list(lz.b.restricciones)}")
    A.reg(area, "no borra otras restricciones ni geometría",
          otras <= set(lz.b.restricciones) and len(lz.b.curvas) == nc and len(lz.b.puntos) == np_, "")
    repintar()
    A.reg(area, "su símbolo desaparece enseguida", r.id not in lz._zonas_glifos, "")
    A.reg(area, "recupera los grados de libertad", lz.resultado.gdl == gdl0, f"{lz.resultado.gdl} vs {gdl0}")
    A.foto(v, f"restr_{nombre}_2_borrada")
    tecla(Qt.Key_Z, Qt.ControlModifier)
    A.reg(area, "Ctrl+Z la devuelve (con su símbolo)", r.id in lz.b.restricciones and glifo(r.id) is not None, "")
    A.reg(area, "al volver, la relación se cumple", bool(cumple()) and lz.resultado.ok, "")
    tecla(Qt.Key_Y, Qt.ControlModifier)
    A.reg(area, "Ctrl+Y la quita otra vez", r.id not in lz.b.restricciones, "")
    tecla(Qt.Key_Z, Qt.ControlModifier)
    limpiar()


# ---------------------------------------------------------------- 3) selección primero, herramienta después
def seleccion_primero():
    b, tipo, ents, cumple, _m, _q = mate.ESCENARIOS["paralela"]()
    instalar(b)
    area = AR + " · selección primero"
    clic(*punto_de_clic(b, ents[0]))
    clic(*punto_de_clic(b, ents[1]), mod=Qt.ControlModifier)
    A.reg(area, "dos líneas elegidas con Ctrl+clic", set(lz.seleccion) == set(ents), f"seleccion={lz.seleccion}")
    pulsar(boton_cinta("sk_r_paralela"))
    A.reg(area, "al apretar «Paralelo» se aplica sin más clics", n_restr("paralela") == 1 and cumple(), f"msg={MENSAJES[-1:]}")
    # H/V con dos líneas elegidas: cada una queda horizontal (Fusion)
    b2, _t, e2, _c, _m2, _q2 = mate.ESCENARIOS["paralela"]()
    instalar(b2)
    clic(*punto_de_clic(b2, e2[0]))
    clic(*punto_de_clic(b2, e2[1]), mod=Qt.ControlModifier)
    pulsar(boton_cinta("sk_r_horizontal_vertical"))
    horizontales = [r for r in b2.restricciones.values() if r.tipo in ("horizontal", "vertical")]
    A.reg(area, "H/V con dos líneas elegidas restringe LAS DOS", len(horizontales) == 2, f"restr={[(r.tipo, r.entidades) for r in b2.restricciones.values()]}")
    limpiar()


# ---------------------------------------------------------------- 4) repetir (sobra) y contradecir (conflicto)
def sobra_y_choca():
    b, _t, ents, _c, _m, _q = mate.ESCENARIOS["horizontal"]()
    instalar(b)
    area = AR + " · repetir y contradecir"
    pulsar(boton_cinta("sk_r_horizontal_vertical"))
    clic(*punto_de_clic(b, ents[0]))
    A.reg(area, "la primera horizontal se pone", n_restr("horizontal") == 1, "")
    pulsar(boton_cinta("sk_r_horizontal_vertical"))
    clic(*punto_de_clic(b, ents[0]))
    A.reg(area, "repetirla NO la agrega (no quita ningún grado de libertad)", n_restr() == 1, f"restr={n_restr()}")
    A.reg(area, "y lo dice con un mensaje claro", bool(MENSAJES) and "sobre" in MENSAJES[-1].lower(), MENSAJES[-1:] and MENSAJES[-1])
    A.foto(v, "restr_repetida")
    # contradecir: vertical sobre la misma línea (ya horizontal) → colapsa → conflicto
    pulsar(boton_cinta("sk_r_horizontal_vertical"))
    l = ents[0]
    lz.aplicar_restriccion("vertical", [l])
    A.reg(area, "una vertical sobre la línea horizontal se rechaza", n_restr("vertical") == 0 and lz.resultado.ok,
          f"vertical={n_restr('vertical')} ok={lz.resultado.ok} msg={MENSAJES[-1:]}")
    A.reg(area, "el boceto no se movió", abs(b.coords(b.curvas[l].p1)[1] - b.coords(b.curvas[l].p2)[1]) < 1e-6, "")
    limpiar()


# ---------------------------------------------------------------- 5) clic derecho en el símbolo
def menu_contextual():
    b, tipo, ents, cumple, _m, _q = mate.ESCENARIOS["perpendicular"]()
    instalar(b)
    area = AR + " · clic derecho"
    rid = b.agregar_restriccion(tipo, ents)
    lz.resolver()
    caja = glifo(rid)
    A.esperar(100)
    n_menus = len(A.MENUS)
    A.clic_derecho(lz, caja.center().toPoint())
    A.reg(area, "clic derecho en el símbolo abre un menú", len(A.MENUS) > n_menus, f"menus={len(A.MENUS)}")
    if len(A.MENUS) > n_menus:
        textos = [a.text() for a in A.MENUS[-1].actions() if a.text()]
        A.reg(area, "ofrece borrar y elegir la geometría", any("Borrar" in t for t in textos) and any("geometría" in t for t in textos), str(textos))
        accion = next(a for a in A.MENUS[-1].actions() if "geometría" in a.text())
        accion.trigger()
        A.reg(area, "«Seleccionar la geometría» elige las dos líneas", set(lz.seleccion) == set(ents), f"seleccion={lz.seleccion}")
        accion = next(a for a in A.MENUS[-1].actions() if "Borrar" in a.text())
        accion.trigger()
        A.esperar(100)
        A.reg(area, "«Borrar» quita solo esa restricción", rid not in b.restricciones and len(b.curvas) == 2, f"restr={list(b.restricciones)}")
    limpiar()


# ---------------------------------------------------------------- 6) símbolos juntos: rectángulo con varias restricciones por esquina
def densidad():
    area = AR + " · símbolos juntos"
    b = mate.Boceto()
    lz.set_herramienta("seleccionar")
    ls = b.agregar_rectangulo((20, 20), (80, 60))
    # varias restricciones en la misma línea
    b.agregar_restriccion("igual", [ls[0], ls[2]])
    b.agregar_restriccion("paralela", [ls[1], ls[3]])
    b.agregar_restriccion("perpendicular", [ls[0], ls[1]])
    instalar(b)
    cajas = list(lz._zonas_glifos.items())
    superpuestos = sum(1 for i in range(len(cajas)) for j in range(i + 1, len(cajas))
                       if cajas[i][1].intersects(cajas[j][1]))
    A.reg(area, f"{len(cajas)} símbolos, ninguno encima de otro", superpuestos == 0, f"{superpuestos} pares superpuestos")
    A.foto(v, "restr_densidad")
    for zoom in (30, 120, 400):
        lz.visor.objetivo = lz.plano.a_3d(50, 40)
        lz.visor.distancia = zoom / 2 / math.sin(math.radians(lz.visor.fov) / 2) * 1.3
        lz.visor.update()
        A.esperar(200)
        repintar()
        # cada símbolo se puede elegir con un clic en su centro
        malos = []
        for rid, caja in lz._zonas_glifos.items():
            lz.seleccion = []
            QTest.mouseClick(lz, Qt.LeftButton, Qt.NoModifier, caja.center().toPoint())
            A.esperar(40)
            if lz.seleccion != [rid]:
                malos.append((rid, lz.seleccion))
        A.reg(area, f"zoom {zoom} mm: cada símbolo se elige con un clic en el suyo", not malos, f"fallan={malos}")
        A.foto(v, f"restr_zoom_{zoom}")
    limpiar()


# ---------------------------------------------------------------- 7) guardar y reabrir
def persistencia():
    area = AR + " · guardar"
    lz.set_herramienta("seleccionar")
    L("create_sketch", name="P", plane="XY")
    a = L("draw_line", sketch="P", start_x=0, start_y=0, end_x=40, end_y=7)["entities"][0]["id"]
    c = L("draw_line", sketch="P", start_x=60, start_y=10, end_x=90, end_y=40)["entities"][0]["id"]
    k = L("draw_circle", sketch="P", center_x=30, center_y=-30, radius=9)["entities"][0]["id"]
    L("add_constraint", sketch="P", type="horizontal", entities=[a])
    L("add_constraint", sketch="P", type="perpendicular", entities=[a, c])
    L("add_constraint", sketch="P", type="tangent", entities=[a, k])
    antes = L("get_sketch", sketch="P")
    ruta = os.path.join(tempfile.mkdtemp(prefix="omnicad_restr_"), "restr.omnicad")
    L("save_document", path=ruta)
    s2 = api.Sesion()
    r2 = api.llamar(s2, "open_document", {"path": ruta})
    despues = api.llamar(s2, "get_sketch", {"sketch": "P"})["result"]
    tipos = lambda sk: sorted((x["type"], tuple(x["entities"])) for x in sk["constraints"])      # noqa: E731
    A.reg(area, "guardar y reabrir conserva las restricciones y sus referencias", r2["ok"] and tipos(antes) == tipos(despues),
          f"{tipos(antes)} -> {tipos(despues)}")
    A.reg(area, "y el estado de grados de libertad", antes["dof"] == despues["dof"], f"{antes['dof']} vs {despues['dof']}")


# ---------------------------------------------------------------- 8) Fijar: el punto no se deja arrastrar, y anular la fijación
def fijar():
    area = AR + " · Fijar"
    b = mate.Boceto()
    a, c = b.agregar_punto(40, 30), b.agregar_punto(80, 50)
    b.agregar_linea(a, c)
    instalar(b)
    gdl0 = lz.resultado.gdl
    pulsar(boton_cinta("sk_r_fijo"))
    clic(40, 30)
    r = next((r for r in b.restricciones.values() if r.tipo == "fijo"), None)
    A.reg(area, "un clic en el punto lo fija", r is not None and r.entidades == [a], f"restr={[(r.tipo, r.entidades) for r in b.restricciones.values()]}")
    A.reg(area, "quita 2 grados de libertad", gdl0 - lz.resultado.gdl == 2, f"{gdl0}->{lz.resultado.gdl}")
    limpiar()
    caja = glifo(r.id) if r else None
    A.reg(area, "aparece el candado junto al punto", caja is not None, "")
    A.foto(v, "restr_fijo_candado")
    arrastrar(40, 30, 10, 10)
    A.reg(area, "arrastrar el punto fijo con el mouse no lo mueve", b.coords(a) == (40, 30), f"queda en {b.coords(a)}")
    A.reg(area, "y dice por qué", bool(MENSAJES) and "fijo" in MENSAJES[-1].lower(), MENSAJES[-1:] and MENSAJES[-1][:90])
    arrastrar(80, 50, 90, 70)
    A.reg(area, "el otro extremo sí se mueve y el fijo se queda", b.coords(a) == (40, 30) and math.dist(b.coords(c), (90, 70)) < 0.05, f"{b.coords(a)} {b.coords(c)}")
    limpiar()                                           # el punto arrastrado quedó elegido: con la herramienta activada se fijaría solo
    pulsar(boton_cinta("sk_r_fijo"))
    clic(40, 30)
    A.reg(area, "otro clic con Fijar anula la fijación", not any(x.tipo == "fijo" for x in b.restricciones.values()), f"restr={len(b.restricciones)}")
    tecla(Qt.Key_Z, Qt.ControlModifier)
    A.reg(area, "Ctrl+Z vuelve a fijarlo", any(x.tipo == "fijo" for x in b.restricciones.values()), "")
    limpiar()


# ---------------------------------------------------------------- 9) lo que no aplica, y Esc a medio camino
def incompatible_y_esc():
    area = AR + " · selección incompatible"
    b = mate.Boceto()
    k = b.agregar_circulo((60, 40), 10)
    ln = b.agregar_linea((20, 70), (100, 80))
    instalar(b)
    pulsar(boton_cinta("sk_r_paralela"))
    clic(*punto_de_clic(b, k))
    clic(*punto_de_clic(b, ln))
    A.reg(area, "Paralelo con un círculo y una línea no crea nada", n_restr() == 0, f"restr={n_restr()}")
    A.reg(area, "dice que no aplica", bool(MENSAJES) and "no aplica" in MENSAJES[-1], MENSAJES[-1:] and MENSAJES[-1][:100])
    A.reg(area, "la herramienta sigue activa y sin clics a medias", lz.herramienta == "r_paralela" and not lz.picks, f"{lz.herramienta} picks={lz.picks}")
    clic(*punto_de_clic(b, ln))
    A.reg(area, "un solo clic queda esperando el segundo", lz.picks == [ln], f"picks={lz.picks}")
    tecla(Qt.Key_Escape)
    A.reg(area, "Esc corta lo que estaba a medias y la herramienta sigue", not lz.picks and lz.herramienta == "r_paralela", f"{lz.herramienta} picks={lz.picks}")
    tecla(Qt.Key_Escape)
    A.reg(area, "otro Esc sale a Seleccionar", lz.herramienta == "seleccionar", lz.herramienta)
    tecla(Qt.Key_Delete)
    A.reg(area, "Supr sin nada elegido no rompe ni borra", len(b.curvas) == 2 and not A.ERRORES, "")
    limpiar()


# ---------------------------------------------------------------- 10) F5 «Qué choca» dice qué sobra; Cambiar por; Supr
def sobra_y_cambiar():
    area = AR + " · F5 y Cambiar por"
    b = mate.Boceto()
    l1, l2 = b.agregar_linea((40, 30), (70, 39)), b.agregar_linea((40, 60), (80, 70))
    b.agregar_restriccion("horizontal", [l1])
    repetida = b.agregar_restriccion("horizontal", [l1])             # lo que trae un archivo viejo: repetida
    rid = b.agregar_restriccion("paralela", [l1, l2])
    instalar(b)
    tecla(Qt.Key_F5)                                   # «Qué choca» no está en la cinta: es la tecla F5
    A.reg(area, "F5 dice cuál sobra", bool(MENSAJES) and "Sobra" in MENSAJES[-1], MENSAJES[-1:] and MENSAJES[-1][:120])
    A.reg(area, "y la deja elegida", lz.seleccion == [repetida], f"seleccion={lz.seleccion}")
    repintar()
    A.foto(v, "restr_sobra_elegida")
    tecla(Qt.Key_Delete)
    A.reg(area, "Supr la borra y las demás siguen", repetida not in b.restricciones and rid in b.restricciones and n_restr("horizontal") == 1, f"restr={list(b.restricciones)}")
    caja = glifo(rid)
    n = len(A.MENUS)
    A.clic_derecho(lz, caja.center().toPoint())
    menu_ = A.MENUS[-1] if len(A.MENUS) > n else None
    cambiar = next((a for a in menu_.actions() if a.text() == "Cambiar por"), None) if menu_ else None
    A.reg(area, "el menú del símbolo ofrece «Cambiar por»", cambiar is not None, "")
    if cambiar is not None:
        opciones = {a.text(): a for a in cambiar.menu().actions()}
        A.reg(area, "para una paralela: perpendicular, igual y colineal", set(opciones) == {"Perpendicular", "Igual", "Colineal"}, str(sorted(opciones)))
        opciones["Perpendicular"].trigger()
        A.esperar(100)
        A.reg(area, "elegir Perpendicular la cambia (mismo id, mismas líneas)", b.restricciones[rid].tipo == "perpendicular" and b.restricciones[rid].entidades == [l1, l2], f"{b.restricciones[rid].tipo}")
        A.reg(area, "la relación nueva se cumple", abs(mate._punto(mate._dir(b, l1), mate._dir(b, l2))) < 1e-7 and lz.resultado.ok, "")
        repintar()
        A.foto(v, "restr_cambiada")
        tecla(Qt.Key_Z, Qt.ControlModifier)
        A.reg(area, "Ctrl+Z la devuelve a Paralela", b.restricciones[rid].tipo == "paralela", b.restricciones[rid].tipo)
    limpiar()


# ---------------------------------------------------------------- 11) acciones repetidas deprisa
def deprisa():
    area = AR + " · acciones repetidas"
    b, _tipo, ents, cumple, mover, _q = mate.ESCENARIOS["paralela"]()
    instalar(b)
    for i in range(12):
        pulsar(boton_cinta("sk_r_paralela"))
        clic(*punto_de_clic(b, ents[0]))
        clic(*punto_de_clic(b, ents[1]))
        if i % 3 == 0:
            tecla(Qt.Key_Z, Qt.ControlModifier)
            tecla(Qt.Key_Y, Qt.ControlModifier)
        pid, x, y = mover[i % len(mover)]
        x0, y0 = b.coords(pid)
        arrastrar(x0, y0, x + i, y - i, pasos=3)
        if i % 4 == 3:
            tecla(Qt.Key_Z, Qt.ControlModifier)
        limpiar()
    A.reg(area, "doce vueltas de aplicar, deshacer, rehacer y arrastrar no dejan duplicados", n_restr("paralela") <= 1, f"paralelas={n_restr('paralela')}")
    A.reg(area, "el boceto sigue resuelto", lz.resultado.ok, lz.resultado.descripcion())
    if n_restr("paralela") == 1:
        A.reg(area, "y la relación se cumple", bool(cumple()), "")
    A.reg(area, "cada restricción cita geometría que existe", all(all(e in b.puntos or e in b.curvas for e in r.entidades) for r in b.restricciones.values()), "")
    A.reg(area, "sin excepciones en slots de Qt", not A.ERRORES, "; ".join(A.ERRORES)[:200])
    limpiar()


# ---------------------------------------------------------------- 12) ventana chica: los 13 botones se pueden apretar
def ventana_chica():
    area = AR + " · ventana chica"
    original = v.size()
    for ancho, alto in ((1024, 640), (800, 520)):
        v.resize(ancho, alto)
        A.esperar(400)
        faltan = []
        for herr in HERRAMIENTA.values():
            try:
                b = boton_cinta(f"sk_{herr}")
                if not v.rect().contains(b.mapTo(v, b.rect().center())):
                    faltan.append(herr)
            except StopIteration:
                faltan.append(herr)
        faltan = sorted(set(faltan))
        A.reg(area, f"{ancho}x{alto}: cuántos botones quedan fuera de la ventana", not faltan, f"fuera: {faltan}" if faltan else "todos a la vista")
        A.foto(v, f"restr_ventana_{ancho}")
    v.resize(original)
    A.esperar(300)


# ---------------------------------------------------------------- 13) rendimiento con la ventana real y eventos de mouse
def rendimiento():
    import statistics
    import sys
    import time
    carpeta = str(A.RAIZ / "scripts")
    if carpeta not in sys.path:
        sys.path.insert(0, carpeta)
    from bench_restricciones import cadena
    for n in (100, 400):
        area = AR + f" · rendimiento {n} piezas"
        b, pts, ls = cadena(n)
        t0 = time.perf_counter()
        instalar(b)
        A.reg(area, "abrir y resolver el boceto", True, f"{(time.perf_counter() - t0) * 1000:.0f} ms (incluye pintar y las esperas de la prueba)")
        lz.visor.objetivo = lz.plano.a_3d(*b.coords(pts[n // 2]))
        lz.visor.distancia = 120 / 2 / math.sin(math.radians(lz.visor.fov) / 2) * 1.3
        lz.visor.update()
        A.esperar(300)
        xy = punto_de_clic(b, ls[n // 2])
        tiempos = []
        for _ in range(9):
            t0 = time.perf_counter()
            QTest.mouseClick(lz, Qt.LeftButton, Qt.NoModifier, px(*xy))
            QApplication.processEvents()
            tiempos.append((time.perf_counter() - t0) * 1000)
        lz.seleccion = []
        A.reg(area, "elegir una línea con un clic", statistics.median(tiempos) < 250, f"mediana {statistics.median(tiempos):.0f} ms (máx {max(tiempos):.0f})")
        t0 = time.perf_counter()
        pulsar(boton_cinta("sk_r_paralela"))
        QTest.mouseClick(lz, Qt.LeftButton, Qt.NoModifier, px(*punto_de_clic(b, ls[n // 2 - 1])))
        QTest.mouseClick(lz, Qt.LeftButton, Qt.NoModifier, px(*punto_de_clic(b, ls[n // 2 + 1])))
        QApplication.processEvents()
        dur = (time.perf_counter() - t0) * 1000
        A.reg(area, "aplicar una restricción (clic, clic y resolver todo)", dur < 5000, f"{dur:.0f} ms; restricciones {len(b.restricciones)}; mensaje: {MENSAJES[-1:] and MENSAJES[-1][:70]}")
        limpiar()
        pid = pts[n // 2]
        x0, y0 = b.coords(pid)
        QTest.mousePress(lz, Qt.LeftButton, Qt.NoModifier, px(x0, y0))
        pasos = []
        for i in range(1, 16):
            q = QPointF(px(x0 + i * 0.4, y0 + i * 0.2))
            t0 = time.perf_counter()
            QApplication.sendEvent(lz, QMouseEvent(QEvent.MouseMove, q, lz.mapToGlobal(q), Qt.NoButton, Qt.LeftButton, Qt.NoModifier))
            QApplication.processEvents()
            pasos.append((time.perf_counter() - t0) * 1000)
        QTest.mouseRelease(lz, Qt.LeftButton, Qt.NoModifier, px(x0 + 6, y0 + 3))
        A.esperar(100)
        pasos.sort()
        p95 = pasos[max(0, int(len(pasos) * 0.95) - 1)]
        A.reg(area, "arrastrar un punto: cada movimiento del mouse", p95 < 250, f"mediana {statistics.median(pasos):.0f} ms, p95 {p95:.0f} ms")
        A.reg(area, "y el boceto queda resuelto", lz.resultado.ok, lz.resultado.descripcion())
        limpiar()


for nombre, f in (("menu", menu),):
    probar(nombre, f)
for nombre in mate.ESCENARIOS:
    probar(nombre, lambda n=nombre: ciclo(n))
for nombre, f in (("seleccion_primero", seleccion_primero), ("sobra_y_choca", sobra_y_choca),
                  ("menu_contextual", menu_contextual), ("densidad", densidad), ("persistencia", persistencia),
                  ("fijar", fijar), ("incompatible_y_esc", incompatible_y_esc), ("sobra_y_cambiar", sobra_y_cambiar),
                  ("deprisa", deprisa), ("ventana_chica", ventana_chica), ("rendimiento", rendimiento)):
    probar(nombre, f)

v.modo_boceto.cancelar()
A.esperar(300)
A.reg(AR, "no se escapó ninguna excepción dentro de un slot de Qt", not A.ERRORES, "; ".join(A.ERRORES)[:300])
A.guardar_registro("restricciones_boceto")
fallas = sum(1 for r in A.REGISTRO if not r["ok"])
print(f"=== {len(A.REGISTRO)} comprobaciones, {fallas} con ✗", flush=True)

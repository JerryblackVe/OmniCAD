# -*- coding: utf-8 -*-
"""BOCETO · Patrón circular y Patrón rectangular con sus paneles, como los usa una persona: botón de la cinta, clic en la
geometría, clic en el centro o en la línea de dirección, teclear cantidades, distancias y ángulos, combos y casillas,
invertir, excluir copias con su casilla, tirar de las asas de la vista, Aceptar / Cancelar / Enter / Esc, editar un patrón
hecho, deshacer y rehacer, valores inválidos, ventanas chicas, estabilidad (alternar herramientas y cancelar), y lo que viene
después (guardar y reabrir, cotas, perfiles y extrusión). Eventos simulados al Lienzo y a los widgets del panel (nunca el
cursor real). Los combos se cambian con la flecha del teclado sobre el combo (no se abre la lista desplegable).
Ver evidencias/patrones_boceto_2026-10-31/INFORME.md."""
import math
import os
import tempfile

import arnes as A
from omnicad import api
from omnicad.restricciones.boceto import MAX_COPIAS_PATRON
from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QPushButton, QToolButton

AR = "BOCETO·PATRONES"
s = api.Sesion()


def L(nombre, **a):
    r = api.llamar(s, nombre, a)
    assert r["ok"], (nombre, a, r)
    return r["result"]


L("create_sketch", name="C", plane="XY")
circ_c = L("draw_circle", sketch="C", center_x=30, center_y=10, radius=4)["entities"][0]["id"]
L("create_sketch", name="R", plane="XY")
circ_r = L("draw_circle", sketch="R", center_x=0, center_y=0, radius=3)["entities"][0]["id"]
guia = L("draw_line", sketch="R", start_x=60, start_y=-20, end_x=60, end_y=-30)["entities"][0]["id"]      # vertical
app, v = A.iniciar(s.doc)
lz = panel = ctl = None


def entrar(nombre, centro=(0, 0), span=150, ancho=1900, alto=1000):
    """Abre el boceto en la ventana y deja los atajos a su lienzo, su panel y su controlador."""
    global lz, panel, ctl
    v.resize(ancho, alto)
    A.esperar(400)
    v.editar_operacion(s.paso(nombre).id)
    A.esperar(500)
    lz, panel = v.modo_boceto.lienzo, v.modo_boceto.patron
    ctl = lz.patron
    lz.visor.objetivo = lz.plano.a_3d(*centro)
    lz.visor.distancia = span / 2 / math.sin(math.radians(lz.visor.fov) / 2) * 1.3
    lz.visor.update()
    lz.update()
    A.esperar(300)


def px(x, y):
    return lz.a_px(x, y).toPoint()


def clic(x, y, mod=Qt.NoModifier):
    QTest.mouseClick(lz, Qt.LeftButton, mod, px(x, y))
    A.esperar(70)


def clic_px(p):
    QTest.mouseClick(lz, Qt.LeftButton, Qt.NoModifier, p.toPoint() if hasattr(p, "toPoint") else p)
    A.esperar(70)


def tecla(k, mod=Qt.NoModifier):
    QTest.keyClick(lz, k, mod)
    A.esperar(90)


def pulsar(boton):
    QTest.mouseClick(boton, Qt.LeftButton)
    A.esperar(120)


def escribir(clave, texto):
    """Teclea en un campo del panel como una persona: foco, seleccionar todo, escribir (o Supr si queda vacío)."""
    c = panel.campos[clave]
    c.setFocus()
    c.selectAll()
    if texto:
        QTest.keyClicks(c, texto)
    else:
        QTest.keyClick(c, Qt.Key_Delete)
    A.esperar(90)


def combo(clave, dato):
    """Cambia un combo con la flecha del teclado hasta el dato."""
    c = panel.combos[clave]
    for _ in range(c.count()):
        if c.currentData() == dato:
            break
        QTest.keyClick(c, Qt.Key_Down)
    for _ in range(c.count()):
        if c.currentData() == dato:
            break
        QTest.keyClick(c, Qt.Key_Up)
    A.esperar(90)
    return c.currentData() == dato


def casilla(clave, marcada):
    c = panel.casillas[clave]
    if c.isChecked() != marcada:
        QTest.mouseClick(c, Qt.LeftButton, Qt.NoModifier, QPoint(8, c.height() // 2))      # sobre el cuadrito, como una persona
        A.esperar(90)


ACCIONES_MENU = []          # ⚠ los ítems del menú desplegable CREAR ▾ se activan con QAction.trigger(), sin abrir el popup


def activar(clave):
    """Aprieta el botón de la cinta; los ítems que solo viven en el menú CREAR ▾ se disparan como lo haría ese ítem."""
    accion = v.modo_boceto.acciones[clave]
    visible = next((b for b in v.cinta.findChildren(QToolButton) if b.defaultAction() is accion and b.isVisible()), None)
    if visible is not None:
        QTest.mouseClick(visible, Qt.LeftButton)
    else:
        ACCIONES_MENU.append(clave)
        accion.trigger()
    A.esperar(120)


def abrir(herr):
    lz.set_herramienta("seleccionar")
    lz.seleccion = []
    activar("sk_" + herr)


def boton(texto):
    return next(b for b in panel.findChildren(QPushButton) if b.text() == texto)


def arrastrar(a, b):
    """Press en `a`, varios movimientos y release en `b` (px)."""
    a, b = QPointF(a), QPointF(b)
    QTest.mousePress(lz, Qt.LeftButton, Qt.NoModifier, a.toPoint())
    for i in range(1, 8):
        q = a + (b - a) * (i / 7)
        QApplication.sendEvent(lz, QMouseEvent(QEvent.MouseMove, q, lz.mapToGlobal(q), Qt.NoButton, Qt.LeftButton, Qt.NoModifier))
        A.esperar(20)
    QTest.mouseRelease(lz, Qt.LeftButton, Qt.NoModifier, b.toPoint())
    A.esperar(120)


def asa(nombre):
    """Posición en px del asa de la vista con esa ayuda («Distancia», «Cantidad», «Ángulo total»), o None."""
    if lz._asas is None:
        return None
    return next((q for a, q in lz._asas.posiciones_px() if a.ayuda == nombre and q is not None), None)


def circulos():
    return sorted(tuple(round(c, 4) for c in lz.b.coords(k.centro)) for k in lz.b.curvas.values() if k.tipo == "circulo")


def prox(a, b, t=0.01):
    resto = list(b)
    if len(a) != len(b):
        return False
    for q in a:
        m = min(resto, key=lambda r: math.dist(q, r))
        if math.dist(q, m) > t:
            return False
        resto.remove(m)
    return True


def centros_previa():
    """Centro (de la caja que envuelve sus vértices) de cada copia de la vista previa que dibuja la ventana: un círculo
    de 64 lados, así que coincide con el centro real a menos de 0,01 mm."""
    polis = ctl.calcular()["polis"]
    return [((min(q[0] for q in p) + max(q[0] for q in p)) / 2, (min(q[1] for q in p) + max(q[1] for q in p)) / 2) for p in polis]


def en_circulo(c, r, grados):
    return [(c[0] + r * math.cos(math.radians(g)), c[1] + r * math.sin(math.radians(g))) for g in grados]


def probar(nombre, funcion):
    try:
        funcion()
    except Exception as e:  # noqa: BLE001
        import traceback
        A.reg(AR, f"{nombre}: EXCEPCIÓN", False, f"{type(e).__name__}: {e}")
        traceback.print_exc()
        if lz is not None:
            lz.set_herramienta("seleccionar")


# ================================================================ A) PATRÓN CIRCULAR
entrar("C", centro=(10, 10))
R30 = math.hypot(30, 10)
A0 = math.degrees(math.atan2(10, 30))


def circular_abrir():
    n = len(lz.b.curvas)
    abrir("patron_circular")
    A.reg(AR + " · circular", "el botón de la cinta marca la herramienta y aparece el panel PATRÓN CIRCULAR",
          lz.herramienta == "patron_circular" and panel.isVisible() and panel.titulo.text() == "PATRÓN CIRCULAR"
          and v.modo_boceto.acciones["sk_patron_circular"].isChecked(), f"herr={lz.herramienta} título={panel.titulo.text()}")
    A.reg(AR + " · circular", "el panel muestra Objetos, Centro, Distribución, Ángulo total y Cantidad y NO las filas del rectangular",
          all(panel.filas[k][1].isVisible() for k in ("seleccion", "centro", "distribucion", "angulo_total", "cantidad"))
          and not panel.filas["dir1"][1].isVisible() and not panel.filas["cantidad1"][1].isVisible(), "")
    A.reg(AR + " · circular", "Objetos es el campo activo y Aceptar está deshabilitado con una guía",
          panel.sel["seleccion"].boton.property("activa") is True and not panel.boton_ok.isEnabled() and "geometría" in panel.guia.text(),
          panel.guia.text())
    clic(34, 10)
    A.reg(AR + " · circular", "un clic en el círculo lo elige y el panel dice «1 seleccionado»",
          lz.seleccion == [circ_c] and panel.sel["seleccion"].boton.text() == "1 seleccionado", f"sel={lz.seleccion}")
    tecla(Qt.Key_Return)
    A.reg(AR + " · circular", "Enter pasa al campo Centro y la guía manda a elegirlo",
          lz.patron.campo == "centro" and panel.sel["centro"].boton.property("activa") is True and "centro" in panel.guia.text().lower(),
          panel.guia.text())
    A.reg(AR + " · circular", "sin centro no se puede aceptar y no se creó nada", not panel.boton_ok.isEnabled() and len(lz.b.curvas) == n, "")
    A.foto(v, "patrones_c1_sin_centro")


probar("circular_abrir", circular_abrir)


def circular_centro():
    clic(0, 0)
    A.reg(AR + " · circular", "clic en el origen lo toma como centro: el botón dice «Origen» y los campos X e Y valen 0",
          panel.sel["centro"].boton.text() == "Origen" and panel.campos["centro_x"].text() == "0"
          and panel.campos["centro_y"].text() == "0", panel.sel["centro"].boton.text())
    A.reg(AR + " · circular", "con el centro puesto Aceptar se habilita y la previa tiene 5 copias (6 en total con el original)",
          panel.boton_ok.isEnabled() and ctl.calcular()["copias"] == 5 and len(ctl.calcular()["polis"]) == 5,
          f"copias={ctl.calcular()['copias']} polis={len(ctl.calcular()['polis'])}")
    A.reg(AR + " · circular", "la previa pone las copias cada 60° alrededor del origen y NO modifica el boceto",
          prox(centros_previa(), en_circulo((0, 0), R30, [A0 + 60 * k for k in range(1, 6)])) and len(lz.b.curvas) == 1, "")
    A.foto(v, "patrones_c2_centro_origen")


probar("circular_centro", circular_centro)


def circular_valores():
    escribir("cantidad", "8")
    A.reg(AR + " · circular", "cantidad 8: la previa tiene 7 copias cada 45° (la cantidad incluye al original)",
          prox(centros_previa(), en_circulo((0, 0), R30, [A0 + 45 * k for k in range(1, 8)])), f"copias={ctl.calcular()['copias']}")
    A.reg(AR + " · circular", "la distribución «Completa» fija el ángulo en 360 y deshabilita su campo",
          panel.campos["angulo_total"].text() == "360" and not panel.campos["angulo_total"].isEnabled(), panel.campos["angulo_total"].text())
    A.reg(AR + " · circular", "cambiar la distribución a «Ángulo» habilita el campo", combo("distribucion", "parcial") and panel.campos["angulo_total"].isEnabled(), "")
    escribir("angulo_total", "180")
    A.reg(AR + " · circular", "ángulo 180 con 8 ejemplares: pasos de 180/7 y el último en el extremo",
          prox(centros_previa(), en_circulo((0, 0), R30, [A0 + 180 / 7 * k for k in range(1, 8)])), "")
    pulsar(panel.filas["angulo_total"][1].findChildren(QToolButton)[0])
    A.reg(AR + " · circular", "el botón ⇄ invierte el sentido: el campo pasa a -180 y las copias van en sentido horario",
          panel.campos["angulo_total"].text() == "-180"
          and prox(centros_previa(), en_circulo((0, 0), R30, [A0 - 180 / 7 * k for k in range(1, 8)])), panel.campos["angulo_total"].text())
    A.foto(v, "patrones_c3_180_horario")
    combo("distribucion", "simetrico")
    A.reg(AR + " · circular", "«Simétrica»: el original queda en el medio (3 copias de un lado y 4 del otro)",
          len(ctl.calcular()["polis"]) == 7 and ctl.calcular()["params"]["simetrico"], "")
    combo("distribucion", "completo")
    A.reg(AR + " · circular", "volver a «Completa» deja 360 con el sentido horario (-360)", panel.campos["angulo_total"].text() == "-360", panel.campos["angulo_total"].text())
    pulsar(panel.filas["angulo_total"][1].findChildren(QToolButton)[0])
    combo("distribucion", "parcial")
    escribir("angulo_total", "180")


probar("circular_valores", circular_valores)


def circular_excluir():
    casillas = ctl.casillas()
    A.reg(AR + " · circular", "hay una casilla por cada copia de la vista previa (7)", len(casillas) == 7, f"{len(casillas)}")
    i, caja, _s = casillas[2]
    clic_px(caja.center())
    A.reg(AR + " · circular", "clic en la casilla de la copia 3 la excluye: la previa queda con 6 y la casilla se ve destildada",
          ctl.suprimidos == {2} and len(ctl.calcular()["polis"]) == 6 and ctl.casillas()[2][2] is True, f"supr={ctl.suprimidos}")
    A.foto(v, "patrones_c4_excluida")


probar("circular_excluir", circular_excluir)


def circular_asas():
    q = asa("Ángulo total")
    A.reg(AR + " · circular", "la vista muestra el asa del ángulo total y la de la cantidad", q is not None and asa("Cantidad") is not None, "")
    if q is None:
        return
    destino = lz.a_px(*en_circulo((0, 0), R30, [A0 + 90])[0])
    arrastrar(q, destino)
    t = panel.campos["angulo_total"].text()
    A.reg(AR + " · circular", "tirar del asa del ángulo escribe el valor en el campo del panel (≈ 90°)",
          abs(float(t.replace(",", ".").replace("°", "")) - 90) < 6, f"campo={t}")
    q2 = asa("Cantidad")
    n0 = int(panel.campos["cantidad"].text())
    paso = float(t.replace(",", ".").replace("°", "")) / (n0 - 1)
    arrastrar(q2, lz.a_px(*en_circulo((0, 0), R30 + 8, [A0 + paso * (n0 - 1) + paso * 2])[0]))
    A.reg(AR + " · circular", "tirar del asa de la cantidad la sube y el campo lo refleja", int(panel.campos["cantidad"].text()) > n0, f"{n0}->{panel.campos['cantidad'].text()}")
    escribir("cantidad", "6")
    escribir("angulo_total", "180")
    A.reg(AR + " · circular", "escribir de nuevo en los campos mueve las asas (siguen sincronizadas)",
          asa("Ángulo total") is not None and prox([(lz.a_mm(asa("Ángulo total"))[0], lz.a_mm(asa("Ángulo total"))[1])], [en_circulo((0, 0), R30, [A0 + 180])[0]], 0.5), "")
    A.foto(v, "patrones_c5_asas")


probar("circular_asas", circular_asas)


def circular_aceptar():
    n = len(lz.b.curvas)
    pulsar(boton("Aceptar"))
    A.reg(AR + " · circular", "Aceptar crea el patrón (6 ejemplares menos 1 excluida = 4 copias nuevas) y cierra el panel",
          len(lz.b.curvas) == n + 4 and not panel.isVisible() and lz.herramienta == "seleccionar", f"curvas {n}->{len(lz.b.curvas)}")
    r = lz.b.patrones[0]
    A.reg(AR + " · circular", "el patrón guarda cantidad 6, ángulo 180, centro (0,0) y la copia excluida",
          r["tipo"] == "circular" and r["params"]["cantidad"] == 6 and r["params"]["angulo_total"] == 180.0
          and r["params"]["centro"] == [0.0, 0.0] and r["suprimidos"] == [2], str(r["params"]))
    quedan = [g for k, g in enumerate([0, 36, 72, 108, 144, 180]) if k not in (3,)]       # la copia 2 es la posición 3
    A.reg(AR + " · circular", "las copias reales coinciden con la vista previa (36° de paso, sin la posición excluida)",
          prox(circulos(), en_circulo((0, 0), R30, [A0 + g for g in quedan])), str(circulos()))
    A.reg(AR + " · circular", "el solver no ve conflictos", lz.resultado.ok, "")
    A.foto(v, "patrones_c6_aceptado")
    tecla(Qt.Key_Z, Qt.ControlModifier)
    A.reg(AR + " · circular", "Ctrl+Z deshace el patrón entero de una vez", len(lz.b.curvas) == n and not lz.b.patrones, f"curvas={len(lz.b.curvas)}")
    tecla(Qt.Key_Y, Qt.ControlModifier)
    A.reg(AR + " · circular", "Ctrl+Y lo rehace", len(lz.b.curvas) == n + 4 and len(lz.b.patrones) == 1, f"curvas={len(lz.b.curvas)}")


probar("circular_aceptar", circular_aceptar)


def circular_editar():
    pid = lz.b.patrones[0]["id"]
    antes = (len(lz.b.curvas), dict(lz.b.patrones[0]["params"]), list(lz.b.patrones[0]["suprimidos"]))
    lz.seleccion = [next(iter(lz.b.patrones[0]["copias"]["0"]))]
    activar("sk_editar_patron")
    A.reg(AR + " · editar", "el botón Editar patrón abre el mismo panel con el título EDITAR PATRÓN CIRCULAR y los valores del patrón",
          panel.isVisible() and panel.titulo.text() == "EDITAR PATRÓN CIRCULAR" and panel.campos["cantidad"].text() == "6"
          and panel.campos["angulo_total"].text() == "180" and ctl.suprimidos == {2} and panel.sel["centro"].boton.text() == "Origen",
          f"{panel.titulo.text()} cant={panel.campos['cantidad'].text()}")
    escribir("cantidad", "12")
    pulsar(boton("Cancelar"))
    A.reg(AR + " · editar", "Cancelar deja el patrón exactamente como estaba",
          (len(lz.b.curvas), lz.b.patrones[0]["params"], lz.b.patrones[0]["suprimidos"]) == antes, f"curvas={len(lz.b.curvas)}")
    lz.seleccion = [next(iter(lz.b.patrones[0]["copias"]["0"]))]
    activar("sk_editar_patron")
    escribir("cantidad", "12")
    pulsar(boton("Aceptar"))
    A.reg(AR + " · editar", "Aceptar regenera con 12 ejemplares menos la excluida (el id del patrón no cambia)",
          len(lz.b.patrones) == 1 and lz.b.patrones[0]["id"] == pid and lz.b.patrones[0]["params"]["cantidad"] == 12
          and len(lz.b.curvas) == 1 + 11 - 1, f"curvas={len(lz.b.curvas)}")
    # el centro se cambia después de crear el patrón
    lz.seleccion = [next(iter(lz.b.patrones[0]["copias"]["0"]))]
    activar("sk_editar_patron")
    escribir("centro_x", "10")
    escribir("centro_y", "0")
    A.reg(AR + " · editar", "escribir otro centro en los campos X e Y (coordenada manual) lo cambia y la previa se rearma",
          ctl.calcular()["params"]["centro"] == [10.0, 0.0] and panel.sel["centro"].boton.text() == "(10, 0)",
          f"{ctl.calcular()['params']['centro']} {panel.sel['centro'].boton.text()}")
    pulsar(boton("Aceptar"))
    cs = circulos()
    A.reg(AR + " · editar", "después de aceptar, todas las copias están a la misma distancia del nuevo centro",
          len(cs) == 11 and all(abs(math.dist(q, (10, 0)) - math.dist((30, 10), (10, 0))) < 1e-3 for q in cs), f"{len(cs)} círculos")
    tecla(Qt.Key_Z, Qt.ControlModifier)
    tecla(Qt.Key_Z, Qt.ControlModifier)
    A.reg(AR + " · editar", "dos Ctrl+Z vuelven al patrón de 6 con el centro en el origen",
          lz.b.patrones[0]["params"]["cantidad"] == 6 and lz.b.patrones[0]["params"]["centro"] == [0.0, 0.0], str(lz.b.patrones[0]["params"]))
    A.foto(v, "patrones_c7_editado")


probar("circular_editar", circular_editar)


def circular_invalidos():
    lz.seleccion = []
    abrir("patron_circular")
    clic(34, 10)
    tecla(Qt.Key_Return)
    clic(0, 0)
    for texto, esperado in (("0", "entero de 2"), ("1", "entero de 2"), ("-3", "entero de 2"), ("2.5", "entero"), ("abc", "cantidad"),
                            ("", "Falta"), (str(MAX_COPIAS_PATRON + 2), "admite hasta"), ("8", "")):   # B-381: una copia más que el tope
        escribir("cantidad", texto)
        ok = (panel.boton_ok.isEnabled() if not esperado else not panel.boton_ok.isEnabled()) and (
            esperado.lower() in panel.mensaje.text().lower() if esperado else not panel.mensaje.isVisible())
        A.reg(AR + " · inválidos", f"cantidad «{texto}»: " + ("Aceptar se deshabilita y dice «…%s…»" % esperado if esperado else "vuelve a ser válida"),
              ok, f"msg={panel.mensaje.text()!r} ok={panel.boton_ok.isEnabled()}")
    combo("distribucion", "parcial")
    for texto, esperado in (("0", "distinto de cero"), ("361", "-360 a 360"), ("-400", "-360 a 360"), ("nan", "")):
        escribir("angulo_total", texto)
        A.reg(AR + " · inválidos", f"ángulo «{texto}» no se acepta",
              not panel.boton_ok.isEnabled() and (esperado in panel.mensaje.text() if esperado else panel.mensaje.isVisible()), panel.mensaje.text())
    A.reg(AR + " · inválidos", "el campo con error se marca en rojo", "border" in panel.campos["angulo_total"].styleSheet(), "")
    escribir("angulo_total", "90")
    pulsar(panel.sel["centro"].boton)
    clic(30, 10)                                             # el centro justo sobre el centro del círculo original
    A.reg(AR + " · inválidos", "el centro sobre la geometría elegida se rechaza con su causa",
          not panel.boton_ok.isEnabled() and "coincide" in panel.mensaje.text(), panel.mensaje.text())
    A.foto(v, "patrones_c8_invalido")
    tecla(Qt.Key_Escape)
    A.reg(AR + " · inválidos", "Esc cierra y no queda ninguna operación a medias (1 patrón, las curvas de antes)",
          lz.herramienta == "seleccionar" and len(lz.b.patrones) == 1 and ctl.tipo is None, "")


probar("circular_invalidos", circular_invalidos)
v.modo_boceto.terminar()
A.esperar(400)

# ================================================================ B) PATRÓN RECTANGULAR
entrar("R", centro=(30, 0), span=73)


def rect_abrir():
    abrir("patron_rectangular")
    A.reg(AR + " · rectangular", "aparece el panel PATRÓN RECTANGULAR con Dirección 1, Cantidad 1, Distancia 1 y la casilla Dirección 2",
          panel.isVisible() and panel.titulo.text() == "PATRÓN RECTANGULAR"
          and all(panel.filas[k][1].isVisible() for k in ("dir1", "angulo1", "modo", "cantidad1", "distancia1", "dos"))
          and not panel.filas["cantidad2"][1].isVisible(), panel.titulo.text())
    clic(-2.1213, -2.1213)
    A.reg(AR + " · rectangular", "clic en el círculo lo elige y ya se puede aceptar (3 ejemplares de 30 mm en X por defecto)",
          lz.seleccion == [circ_r] and panel.boton_ok.isEnabled() and ctl.calcular()["copias"] == 2, f"sel={lz.seleccion}")
    A.foto(v, "patrones_r1_abierto")


probar("rect_abrir", rect_abrir)


def rect_valores():
    escribir("cantidad1", "4")
    combo("modo", "espaciado")
    escribir("distancia1", "20")
    escribir("angulo1", "30")
    c30 = (math.cos(math.radians(30)), math.sin(math.radians(30)))
    A.reg(AR + " · rectangular", "4 ejemplares, espaciado 20 mm, dirección 30°: P(i) = P0 + i·20·(cos30, sen30)",
          prox(centros_previa(), [(20 * k * c30[0], 20 * k * c30[1]) for k in range(1, 4)]), str(centros_previa()))
    combo("modo", "extension")
    A.reg(AR + " · rectangular", "pasar a Extensión con 20 mm: el paso pasa a ser 20/3",
          prox(centros_previa(), [(20 / 3 * k * c30[0], 20 / 3 * k * c30[1]) for k in range(1, 4)]), "")
    combo("modo", "espaciado")
    casilla("dos", True)
    A.reg(AR + " · rectangular", "tildar Dirección 2 muestra Dirección 2, Ángulo 2, Cantidad 2, Distancia 2 y Simétrico",
          all(panel.filas[k][1].isVisible() for k in ("dir2", "angulo2", "cantidad2", "distancia2", "simetrico2")), "")
    escribir("cantidad2", "3")
    escribir("distancia2", "15")
    escribir("angulo2", "100")
    d2 = (math.cos(math.radians(100)), math.sin(math.radians(100)))
    esperado = [(20 * i * c30[0] + 15 * j * d2[0], 20 * i * c30[1] + 15 * j * d2[1]) for i in range(4) for j in range(3) if (i, j) != (0, 0)]
    A.reg(AR + " · rectangular", "dirección 2 a 100° (NO ortogonal): 4×3 = 12 ejemplares con P(i,j) = P0 + i·V1 + j·V2",
          prox(centros_previa(), esperado), f"{len(centros_previa())} copias")
    A.foto(v, "patrones_r2_dos_direcciones")
    pulsar(panel.filas["distancia1"][1].findChildren(QToolButton)[0])
    A.reg(AR + " · rectangular", "⇄ en la distancia 1 invierte esa dirección (-20) sin tocar la 2",
          panel.campos["distancia1"].text() == "-20"
          and all(any(math.dist(q, (-20 * k * c30[0], -20 * k * c30[1])) < 1e-3 for q in centros_previa()) for k in range(1, 4)),
          panel.campos["distancia1"].text())
    pulsar(panel.filas["distancia1"][1].findChildren(QToolButton)[0])


probar("rect_valores", rect_valores)


def rect_direccion_linea():
    pulsar(panel.sel["dir2"].boton)
    A.reg(AR + " · rectangular", "el campo Dirección 2 se activa", lz.fase == "dir2" and panel.sel["dir2"].boton.property("activa") is True, f"fase={lz.fase}")
    clic(0, 50)                                              # vacío: sin línea
    A.reg(AR + " · rectangular", "clic en el vacío: «Ahí no hay ninguna línea»", "no hay ninguna línea" in panel.mensaje.text(), panel.mensaje.text())
    clic(60, -25)                                            # la línea vertical
    A.reg(AR + " · rectangular", "clic sobre la línea guía la toma como dirección 2 (vertical): el campo Ángulo 2 se deshabilita",
          ctl.lineas["dir2"] == guia and not panel.campos["angulo2"].isEnabled(), f"lineas={ctl.lineas}")
    d = ctl.calcular()["params"]["dir2"]
    A.reg(AR + " · rectangular", "la dirección 2 de la previa es la de la línea (0, -1 hacia su fin)", abs(d[0]) < 1e-9 and abs(d[1] + 1) < 1e-9, str(d))
    pulsar(panel.sel["dir2"].borrar)
    A.reg(AR + " · rectangular", "la ✕ de Dirección 2 la suelta y vuelve el ángulo escrito", ctl.lineas["dir2"] is None and panel.campos["angulo2"].isEnabled(), "")
    escribir("angulo2", "90")


probar("rect_direccion_linea", rect_direccion_linea)


def rect_excluir_y_asas():
    casillas = ctl.casillas()
    A.reg(AR + " · rectangular", "una casilla por cada una de las 11 copias", len(casillas) == 11, f"{len(casillas)}")
    clic_px(casillas[4][1].center())
    clic_px(ctl.casillas()[7][1].center())
    A.reg(AR + " · rectangular", "excluir dos copias deja 9 en la previa", ctl.suprimidos == {4, 7} and len(ctl.calcular()["polis"]) == 9, f"supr={ctl.suprimidos}")
    q = asa("Distancia")
    A.reg(AR + " · rectangular", "hay asas de distancia y de cantidad en las dos direcciones", q is not None and asa("Cantidad") is not None, "")
    if q is None:
        return
    escribir("angulo1", "0")
    A.esperar(100)
    q = asa("Distancia")
    arrastrar(q, QPointF(q.x() + 30, q.y()))
    A.reg(AR + " · rectangular", "tirar del asa de la distancia cambia el valor del campo (el paso crece)",
          float(panel.campos["distancia1"].text().replace(",", ".")) > 20.0, f"campo={panel.campos['distancia1'].text()}")
    escribir("distancia1", "20")
    A.foto(v, "patrones_r3_excluidas_asas")


probar("rect_excluir_y_asas", rect_excluir_y_asas)


def rect_aceptar():
    n = len(lz.b.curvas)
    antes_pasos = len(lz.historial)
    tecla(Qt.Key_Return)                                     # Enter con todo bien: acepta
    A.reg(AR + " · rectangular", "Enter acepta: 12 ejemplares - 2 excluidos = 9 copias nuevas, un solo paso de deshacer",
          len(lz.b.curvas) == n + 9 and lz.herramienta == "seleccionar" and len(lz.historial) == antes_pasos + 1,
          f"curvas {n}->{len(lz.b.curvas)} pasos {antes_pasos}->{len(lz.historial)}")
    r = lz.b.patrones[0]
    c1, c2 = (1.0, 0.0), (math.cos(math.radians(90)), math.sin(math.radians(90)))
    todas = [(20 * i * c1[0] + 15 * j * c2[0], 20 * i * c1[1] + 15 * j * c2[1]) for i in range(4) for j in range(3)]
    A.reg(AR + " · rectangular", "las posiciones reales son P0 + i·20·X + j·15·Y menos las dos excluidas",
          len(circulos()) == 10 and all(any(math.dist(q, t) < 1e-3 for t in todas) for q in circulos()), str(circulos()))
    A.reg(AR + " · rectangular", "guarda el modo espaciado, las cantidades 4 y 3 y las exclusiones",
          r["params"]["modo"] == "espaciado" and (r["params"]["cantidad1"], r["params"]["cantidad2"]) == (4, 3)
          and r["suprimidos"] == [4, 7], str(r["params"]))
    A.foto(v, "patrones_r4_aceptado")
    tecla(Qt.Key_Z, Qt.ControlModifier)
    A.reg(AR + " · rectangular", "Ctrl+Z lo deshace entero", len(lz.b.curvas) == n and not lz.b.patrones, "")
    tecla(Qt.Key_Y, Qt.ControlModifier)
    A.reg(AR + " · rectangular", "Ctrl+Y lo rehace", len(lz.b.curvas) == n + 9, "")


probar("rect_aceptar", rect_aceptar)


def rect_editar():
    lz.seleccion = [next(iter(lz.b.patrones[0]["copias"]["0"]))]
    activar("sk_editar_patron")
    A.reg(AR + " · editar", "Editar patrón carga cantidades, distancias, modo, direcciones y exclusiones",
          panel.titulo.text() == "EDITAR PATRÓN RECTANGULAR" and panel.campos["cantidad1"].text() == "4"
          and panel.casillas["dos"].isChecked() and ctl.suprimidos == {4, 7} and panel.combos["modo"].currentData() == "espaciado",
          f"{panel.titulo.text()}")
    escribir("cantidad2", "1")
    casilla("dos", False)
    pulsar(boton("Aceptar"))
    A.reg(AR + " · editar", "sacar la dirección 2 deja una sola fila de 4 (las exclusiones que ya no existen se descartan sin romper)",
          len(circulos()) in (3, 4) and lz.b.patrones[0]["params"]["cantidad2"] == 1, f"{len(circulos())} círculos")
    tecla(Qt.Key_Z, Qt.ControlModifier)


probar("rect_editar", rect_editar)


def cancelar():
    n, pasos, patrones = len(lz.b.curvas), len(lz.historial), len(lz.b.patrones)
    for como in ("esc", "boton", "x"):
        abrir("patron_rectangular")
        clic(-2.1213, -2.1213)
        escribir("cantidad1", "9")
        casilla("dos", True)
        if como == "esc":
            tecla(Qt.Key_Escape)
        elif como == "boton":
            pulsar(boton("Cancelar"))
        else:
            pulsar(panel.findChildren(QToolButton)[0])
        A.reg(AR + " · cancelar", f"cancelar con {como}: sin geometría nueva, sin paso en el historial y sin patrón nuevo",
              len(lz.b.curvas) == n and len(lz.historial) == pasos and len(lz.b.patrones) == patrones
              and not panel.isVisible() and lz.herramienta == "seleccionar" and ctl.tipo is None and lz._asas is None,
              f"curvas={len(lz.b.curvas)} pasos={len(lz.historial)}")


probar("cancelar", cancelar)


def inválidos_rect():
    abrir("patron_rectangular")
    clic(-2.1213, -2.1213)
    casilla("dos", True)
    for clave, texto, esperado in (("cantidad1", "0", "entero"), ("cantidad1", "-2", "entero"), ("cantidad1", "2.5", "entero"),
                                   ("cantidad1", "3", ""), ("distancia1", "0", "encima"), ("distancia1", "abc", "distancia"),
                                   ("distancia1", "20", ""), ("angulo2", "0", "paralelas"), ("angulo2", "180", "paralelas"),
                                   ("angulo2", "90", ""), ("cantidad2", "1000", "admite hasta"), ("cantidad2", "2", "")):
        escribir(clave, texto)
        mal = bool(esperado)
        ok = (not panel.boton_ok.isEnabled() and esperado.lower() in panel.mensaje.text().lower()) if mal else (
            panel.boton_ok.isEnabled() and not panel.mensaje.isVisible())
        A.reg(AR + " · inválidos", f"{clave} = «{texto}»: " + (f"se rechaza («…{esperado}…»)" if mal else "vuelve a ser válido"), ok,
              f"msg={panel.mensaje.text()!r}")
    escribir("distancia1", "2+3*4")
    A.reg(AR + " · inválidos", "una expresión con unidades y operaciones (2+3*4) se evalúa: distancia 14", panel.boton_ok.isEnabled()
          and abs(ctl.calcular()["params"]["distancia1"] - 14) < 1e-9, "")
    A.foto(v, "patrones_r5_validos")
    tecla(Qt.Key_Escape)


probar("inválidos_rect", inválidos_rect)


def estabilidad():
    base = (len(lz.b.curvas), len(lz.b.patrones), len(lz.historial))
    herramientas = ("patron_rectangular", "patron_circular", "linea", "patron_rectangular", "simetria", "patron_circular")
    for k in range(24):
        h = herramientas[k % len(herramientas)]
        if h == "linea":
            lz.set_herramienta("linea")
        else:
            abrir(h)
        if h.startswith("patron"):
            clic(-2.1213, -2.1213)
            if h == "patron_circular":
                tecla(Qt.Key_Return)
                clic(40, 5 * (k % 3))
            for clave, texto in (("cantidad", str(2 + k % 5)), ("cantidad1", str(2 + k % 4)), ("distancia1", str(5 + k))):
                if clave in panel.campos and panel.campos[clave].isVisible():
                    escribir(clave, texto)
        if k % 3 == 0:
            tecla(Qt.Key_Escape)
        lz.set_herramienta("seleccionar")
    A.reg(AR + " · estabilidad", "24 vueltas de abrir, elegir, teclear, cancelar y alternar herramientas: nada quedó a medias",
          (len(lz.b.curvas), len(lz.b.patrones), len(lz.historial)) == base and ctl.tipo is None and lz._asas is None
          and not panel.isVisible(), f"{(len(lz.b.curvas), len(lz.b.patrones), len(lz.historial))} vs {base}")


probar("estabilidad", estabilidad)


def chica(ancho, alto, herr):
    v.resize(ancho, alto)
    A.esperar(500)
    v.area.reubicar()
    abrir(herr)
    clic(-2.1213, -2.1213)
    if herr == "patron_circular":
        tecla(Qt.Key_Return)
        clic(0, 0)
    else:
        casilla("dos", True)
    A.esperar(250)
    area = v.area.rect()
    entra = panel.isVisible() and all(area.contains(b.mapTo(v.area, b.rect().topLeft())) and area.contains(b.mapTo(v.area, b.rect().bottomRight()))
                                      for b in (panel.boton_ok, boton("Cancelar")))
    barra = v.area.barra
    libre = not panel.geometry().intersects(barra.geometry()) if barra is not None and barra.isVisible() else True
    A.reg(AR + f" · {ancho}x{alto}", f"{herr}: el panel con Aceptar y Cancelar entra en la ventana (el cuerpo se desplaza si hace falta)", entra,
          f"panel={panel.geometry().getRect()} área={area.getRect()}")
    A.reg(AR + f" · {ancho}x{alto}", f"{herr}: y la barra de vista no lo tapa", libre, "")
    A.foto(v, f"patrones_chica_{herr}_{ancho}x{alto}")
    tecla(Qt.Key_Escape)


for ancho, alto in ((1024, 640), (800, 520)):
    for herr in ("patron_rectangular", "patron_circular"):
        probar(f"chica {ancho} {herr}", lambda a=ancho, h=alto, g=herr: chica(a, h, g))
v.resize(1900, 1000)
A.esperar(500)


# ================================================================ C) después: guardar, reabrir, perfiles, cotas y extrusión
def despues():
    while lz.b.patrones:                                     # parte de un boceto limpio: el círculo original y la línea guía
        tecla(Qt.Key_Z, Qt.ControlModifier)
    abrir("patron_rectangular")
    clic(-2.1213, -2.1213)
    escribir("cantidad1", "4")
    escribir("distancia1", "18")
    combo("modo", "espaciado")
    casilla("dos", True)
    escribir("cantidad2", "2")
    escribir("distancia2", "12")
    escribir("angulo2", "60")
    clic_px(ctl.casillas()[1][1].center())
    pulsar(boton("Aceptar"))
    circulos_n = len(circulos())
    v.modo_boceto.terminar()
    A.esperar(400)
    sk = L("get_sketch", sketch="R")
    par = sk["patterns"][0]["parameters"]
    A.reg(AR + " · después", "al terminar el boceto el patrón sigue en el documento con sus parámetros (4×2, espaciado 18 y 12, 60°, copia 1 excluida)",
          len(sk["patterns"]) == 1 and (par["count1"], par["count2"], par["distance1"], par["distance2"], par["angle2"]) == (4, 2, 18.0, 12.0, 60.0)
          and par["spacing"] == "spacing" and sk["patterns"][0]["suppressed"] == [1], str(par))
    A.reg(AR + " · perfiles", f"cada círculo copiado es un perfil cerrado: {len(sk['profiles'])} perfiles de {circulos_n} círculos",
          len(sk["profiles"]) == circulos_n == 4 * 2 - 1, f"{len(sk['profiles'])}")
    # guardar y reabrir ANTES de extruir: editar el patrón después de una extrusión invalida los perfiles que ésta nombra
    ruta = os.path.join(tempfile.mkdtemp(prefix="omnicad_pat_"), "patron.omnicad")
    L("save_document", path=ruta)
    s2 = api.Sesion()
    r2 = api.llamar(s2, "open_document", {"path": ruta})
    sk2 = api.llamar(s2, "get_sketch", {"sketch": "R"})["result"]
    A.reg(AR + " · guardar", "guardar y reabrir conserva geometría, parámetros, exclusiones y direcciones",
          r2["ok"] and sk2["patterns"][0]["parameters"] == par and sk2["patterns"][0]["suppressed"] == [1]
          and len(sk2["entities"]) == len(sk["entities"]), f"{sk2['patterns'][0]['parameters']}")
    ed = api.llamar(s2, "edit_sketch_pattern", {"sketch": "R", "pattern": sk2["patterns"][0]["id"], "count1": 5})
    A.reg(AR + " · guardar", "el patrón del documento reabierto se edita por la API (5 columnas)", ed["ok"], str(ed.get("mensaje", "")))
    L("add_dimension", sketch="R", type="radius", entities=[circ_r], value=2.5)
    radios = sorted({round(e["radius"], 4) for e in L("get_sketch", sketch="R")["entities"] if e["type"] == "circle"})
    A.reg(AR + " · cotas", "acotar el radio del original a 2,5 mm lo cambia en todas las copias (restricción de igualdad)", radios == [2.5], str(radios))
    sk = L("get_sketch", sketch="R")
    L("extrude", sketch="R", profile=list(range(len(sk["profiles"]))), distance=5)
    vol = L("get_physical_properties")["total"]["volume"]
    esperado = len(sk["profiles"]) * math.pi * 2.5 ** 2 * 5
    A.reg(AR + " · extrusión", f"extruir los {len(sk['profiles'])} perfiles 5 mm da el volumen exacto (π·2,5²·5 por copia)",
          abs(vol - esperado) < 1e-3, f"volumen={vol:.4f} esperado={esperado:.4f}")


probar("después", despues)

A.reg(AR, "no se escapó ninguna excepción dentro de un slot de Qt", not A.ERRORES, "; ".join(A.ERRORES)[:300])
A.reg(AR, "⚠ ítems de CREAR ▾ activados con trigger() (no se abrió el popup): " + ", ".join(sorted(set(ACCIONES_MENU))), True, "")
A.guardar_registro("patrones_boceto")
fallas = sum(1 for r in A.REGISTRO if not r["ok"])
print(f"=== {len(A.REGISTRO)} comprobaciones, {fallas} con ✗", flush=True)

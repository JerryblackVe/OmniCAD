# -*- coding: utf-8 -*-
"""BOCETO › Cota de boceto como la ayuda de Fusion (Dimensions): clic en la geometría, clic para ubicar, teclear el valor
o una expresión, Enter; doble clic para editar; menú de la cota; qué tipo sale según lo elegido; lo que Fusion permite
y OmniCAD ya cubre (menú antes de ubicar, clic en otra cota para citarla, Mostrar cotas en el navegador)."""
import sys

import arnes as A
from omnicad import api
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

AR = "BOCETO·COTAS"
s = api.Sesion()


def L(nombre, **a):
    r = api.llamar(s, nombre, a)
    assert r["ok"], (nombre, a, r)
    return r["result"]


L("create_sketch", name="S", plane="XY")
L("draw_rectangle", sketch="S", x1=0, y1=0, x2=25, y2=25)
L("draw_circle", sketch="S", center_x=60, center_y=10, radius=5)
L("draw_line", sketch="S", start_x=100, start_y=0, end_x=125, end_y=0)
L("draw_line", sketch="S", start_x=100, start_y=0, end_x=112, end_y=18)
L("draw_point", sketch="S", x=150, y=0)
L("draw_point", sketch="S", x=170, y=12)
app, v = A.iniciar(s.doc)
v.editar_operacion(s.paso("S").id)
A.esperar(500)
lz = v.modo_boceto.lienzo
A.reg(AR, "entrar al boceto con doble clic/editar", v.modo_boceto.activo and lz is not None, "")
v.visor.encuadrar()
A.esperar(300)


def px(x, y):
    return lz.a_px(x, y).toPoint()


def clic(x, y, mod=Qt.NoModifier):
    QTest.mouseClick(lz, Qt.LeftButton, mod, px(x, y))
    A.esperar(70)


def doble(x, y, mod=Qt.NoModifier):
    QTest.mouseDClick(lz, Qt.LeftButton, mod, px(x, y))
    A.esperar(120)


def escribir(texto):
    campo = lz.entrada.campos[0]
    campo.selectAll()
    QTest.keyClicks(campo, texto)
    QTest.keyClick(campo, Qt.Key_Return)
    A.esperar(120)


def derecho(pos, ms=0):
    """Clic derecho (rápido, o apretado `ms` milisegundos antes de soltar: con una cota a medias abre sus opciones)."""
    QTest.mousePress(lz, Qt.RightButton, Qt.NoModifier, pos)
    if ms:
        A.esperar(ms)
    QTest.mouseRelease(lz, Qt.RightButton, Qt.NoModifier, pos)
    A.esperar(80)


def cotas():
    return list(lz.b.cotas.values())


def cota_nueva(antes):
    return next((c for c in cotas() if c.id not in antes), None)


def acotar(picks, ubicar, texto, etiqueta, deshacer=True):
    """Herramienta Cota: un clic por entidad, un clic para ubicar y teclear el valor. Devuelve (cota o None, mensaje)."""
    antes = {c.id for c in cotas()}
    lz.set_herramienta("cota")
    A.esperar(60)
    for p in picks:
        clic(*p)
    if ubicar:
        clic(*ubicar)
    abierta = lz.entrada is not None and lz.entrada.isVisible()
    if abierta and texto is not None:
        escribir(texto)
    c = cota_nueva(antes)
    msg = lz.entrada.campos[0].styleSheet() if lz.entrada is not None and lz.entrada.isVisible() else ""
    A.reg(AR, etiqueta, bool(abierta) and (c is not None or texto is None),
          f"caja de valor abierta={abierta}; cota={(c.tipo, c.expresion, c.nombre, c.referencia) if c else None}; caja sigue abierta con error={'campo_error' in msg or bool(msg)}")
    if lz.entrada is not None and lz.entrada.isVisible():
        QTest.keyClick(lz.entrada.campos[0], Qt.Key_Escape)
        A.esperar(80)
    if c is not None and deshacer:
        lz.deshacer()
        A.esperar(100)
        A.reg(AR, f"{etiqueta}: deshacer la quita", cota_nueva(antes) is None, "")
    return c


def run(nombre, f):
    A.correr(f"{AR} · {nombre}", f)


def tipos():
    # Fusion: una línea → lineal; dos líneas paralelas → lineal; dos puntos → lineal; no paralelas → angular; círculo → diámetro
    c = acotar([(12.5, 25)], (12.5, 36), "25", "línea → cota lineal", deshacer=False)
    A.reg(AR, "línea → cota lineal", c is not None and c.tipo == "distancia", str(c and c.tipo))
    lz.deshacer()
    c = acotar([(60, 15)], None, "10", "círculo, un clic y teclear → diámetro")
    A.reg(AR, "círculo → diámetro", c is not None and c.tipo == "diametro", str(c and c.tipo))
    c = acotar([(112.5, 0), (106, 9)], (118, 10), "40", "dos líneas no paralelas → ángulo")
    A.reg(AR, "dos líneas no paralelas → ángulo", c is not None and c.tipo == "angulo", str(c and c.tipo))
    c = acotar([(150, 0), (170, 12)], (160, 24), "20", "dos puntos, ubicar arriba → horizontal")
    A.reg(AR, "dos puntos ubicados arriba → horizontal", c is not None and c.tipo == "distancia_h", str(c and c.tipo))
    c = acotar([(150, 0), (170, 12)], (185, 6), "12", "dos puntos, ubicar al costado → vertical")
    A.reg(AR, "dos puntos ubicados al costado → vertical", c is not None and c.tipo == "distancia_v", str(c and c.tipo))
    lz.opcion_cota = "alineada"
    c = acotar([(150, 0), (170, 12)], (160, 24), "20", "dos puntos con opción «Alineada» → distancia directa")
    A.reg(AR, "opción Alineada da la distancia directa entre los puntos", c is not None and c.tipo == "distancia", str(c and c.tipo))
    lz.opcion_cota = "auto"


run("qué tipo sale según lo elegido", tipos)


def valores():
    """Lo que se teclea en la caja de valor (la persona escribe y Enter). La tercera columna es lo esperado."""
    casos = [("25", True), ("12,5", True), ("1 in", True), ("2*12,5", True), ("25 mm", True), ("abc", False), ("", True), ("0", False),
             ("-5", False), ("1e9", False), ("5 deg", False), ("10 +", False), ("nan", False)]
    for texto, acepta in casos:
        antes = {c.id for c in cotas()}
        lz.set_herramienta("cota")
        clic(12.5, 25)
        clic(12.5, 36)
        escribir(texto)
        c = cota_nueva(antes)
        sigue = lz.entrada is not None and lz.entrada.isVisible()
        rojo = sigue and bool(lz.entrada.campos[0].styleSheet())
        ok = (c is not None) == acepta
        A.reg(AR, f"teclear «{texto}» en una cota lineal", ok, f"cota={(c.expresion, c.nombre) if c else None}; la caja sigue abierta={sigue}; en rojo={rojo}")
        if sigue:
            QTest.keyClick(lz.entrada.campos[0], Qt.Key_Escape)
            A.esperar(80)
        if c is not None:
            lz.deshacer()
            A.esperar(100)


run("valores tecleados", valores)


def editar_y_menu():
    antes = {c.id for c in cotas()}
    lz.set_herramienta("cota")
    clic(12.5, 25)
    clic(12.5, 36)
    escribir("25")
    c = cota_nueva(antes)
    lz.set_herramienta("seleccionar")
    A.esperar(60)
    zona = lz._zonas_cotas.get(c.id)
    A.reg(AR, "la cota dibujada tiene zona para clic", zona is not None, "")
    if zona is None:
        return
    centro = zona.center().toPoint() if hasattr(zona, "center") else None
    QTest.mouseDClick(lz, Qt.LeftButton, Qt.NoModifier, centro)
    A.esperar(150)
    abierta = lz.entrada is not None and lz.entrada.isVisible()
    A.reg(AR, "doble clic en la cota abre su caja de valor", abierta, "")
    if abierta:
        escribir("30")
        A.reg(AR, "editar la cota a 30 la cambia", lz.b.cotas[c.id].expresion == "30", lz.b.cotas[c.id].expresion)
    A.MENUS.clear()
    A.clic_derecho(lz, centro)
    textos = [a.text() for a in A.MENUS[-1].actions() if a.text()] if A.MENUS else None
    A.reg(AR, "clic derecho en la cota abre su menú", bool(textos), str(textos))
    QTest.mouseDClick(lz, Qt.LeftButton, Qt.ShiftModifier, centro)
    A.esperar(150)
    A.reg(AR, "Mayús + doble clic la pasa a referencia (driven)", lz.b.cotas[c.id].referencia, "")
    lz.deshacer()
    lz.deshacer()
    A.esperar(100)


run("editar, menú y referencia", editar_y_menu)


def mover_con_el_mouse():
    """Arrastrar el texto de la cota con el botón izquierdo la ubica en otro lado sin cambiar su valor."""
    for k in cotas():
        lz.b.eliminar(k.id)
    antes = {c.id for c in cotas()}
    lz.set_herramienta("cota")
    clic(12.5, 25)
    clic(12.5, 36)
    escribir("25")
    c = cota_nueva(antes)
    lz.set_herramienta("seleccionar")
    A.esperar(80)
    lz.grab()
    zona = lz._zonas_cotas.get(c.id)
    ini = zona.center().toPoint()
    datos0, expr0 = repr(sorted(lz.b.cotas[c.id].datos.items())), lz.b.cotas[c.id].expresion
    QTest.mouseMove(lz, ini)          # la persona primero apoya el mouse encima
    A.esperar(80)
    QTest.mousePress(lz, Qt.LeftButton, Qt.NoModifier, ini)
    for k in range(1, 7):
        QTest.mouseMove(lz, ini + type(ini)(0, -8 * k))
        A.esperar(30)
    QTest.mouseRelease(lz, Qt.LeftButton, Qt.NoModifier, ini + type(ini)(0, -48))
    A.esperar(120)
    datos1 = repr(sorted(lz.b.cotas[c.id].datos.items()))
    A.reg(AR, "arrastrar el texto de la cota con el mouse la ubica en otro lado", datos0 != datos1, f"datos antes {datos0[:90]} / después {datos1[:90]}")
    A.reg(AR, "arrastrar la cota no cambia su valor", lz.b.cotas[c.id].expresion == expr0, lz.b.cotas[c.id].expresion)
    lz.deshacer()
    A.esperar(80)
    A.reg(AR, "un Ctrl+Z deshace el arrastre y no borra la cota", c.id in lz.b.cotas and repr(sorted(lz.b.cotas[c.id].datos.items())) == datos0,
          f"cota sigue={c.id in lz.b.cotas}")
    lz.deshacer()
    A.esperar(80)


run("mover la cota con el mouse", mover_con_el_mouse)


def lo_que_fusion_tiene():
    # Fusion: antes de ubicar, clic derecho da Radio/Diámetro, Driven/Driving y Centro/Tangente.
    for c in cotas():
        lz.b.eliminar(c.id)
    lz.set_herramienta("cota")
    clic(12.5, 25)
    A.MENUS.clear()
    derecho(px(12.5, 36), 550)
    items = [a.text() for a in A.MENUS[-1].actions() if a.text()] if A.MENUS else []
    A.reg(AR, "clic derecho ANTES de ubicar la cota abre sus opciones: Driven/Driving, Radio/Diámetro, Centro/Tangente (como Fusion)",
          any("referencia" in x.lower() for x in items) and not lz.b.cotas, f"menú={items}; cotas en el boceto={len(lz.b.cotas)}")
    QTest.keyClick(lz, Qt.Key_Escape)
    A.esperar(80)


run("lo que Fusion tiene", lo_que_fusion_tiene)


def menu_previo_y_citar():
    """BOC-34 con el mouse: clic derecho antes de ubicar la cota, con un círculo elegido."""
    for c in cotas():
        lz.b.eliminar(c.id)
    antes = {c.id for c in cotas()}
    lz.set_herramienta("cota")
    clic(60, 15)                                   # el círculo: la caja de diámetro queda abierta
    abierta = lz.entrada is not None and lz.entrada.isVisible()
    A.MENUS.clear()
    derecho(px(70, 25), 550)
    items = [a.text() for a in A.MENUS[-1].actions() if a.text()] if A.MENUS else []
    A.reg(AR, "clic derecho con un círculo elegido ofrece Radio y Diámetro además de driven/driving",
          abierta and {"Radio", "Diámetro"} <= set(items) and not cotas(), f"menú={items}")
    if A.MENUS:
        next(a for a in A.MENUS[-1].actions() if a.text() == "Radio").trigger()
        A.esperar(80)
        A.reg(AR, "elegir Radio rehace la caja con el radio (5)", lz.entrada is not None and lz.entrada.campos[0].text() == "5",
              lz.entrada.campos[0].text() if lz.entrada is not None else "sin caja")
        next(a for a in A.MENUS[-1].actions() if "(driven)" in a.text()).trigger()
        escribir("99")
        c = cota_nueva(antes)
        A.reg(AR, "con «driven» elegido, Enter crea una cota de radio de referencia que mide 5",
              c is not None and c.tipo == "radio" and c.referencia and abs(float(c.expresion) - 5) < 1e-6,
              str(c and (c.tipo, c.referencia, c.expresion)))
        lz.deshacer()
        A.esperar(100)
    lz.deshacer()
    A.esperar(100)


run("menú antes de ubicar la cota (BOC-34)", menu_previo_y_citar)
def mover(pos):
    """Movimiento del mouse SIMULADO enviado al lienzo (QTest.mouseMove mueve el cursor real de Windows)."""
    from PySide6.QtCore import QEvent
    from PySide6.QtGui import QMouseEvent
    QApplication.sendEvent(lz, QMouseEvent(QEvent.MouseMove, pos, lz.mapToGlobal(pos), Qt.NoButton, Qt.NoButton, Qt.NoModifier))


def citar_una_cota():
    """BOC-35 con el mouse: con la caja de valor abierta, un clic en otra cota (que ya tiene nombre dN) la cita."""
    global lz
    v._salir_de_boceto()
    A.esperar(300)
    linea = L("draw_line", sketch="S", start_x=200, start_y=0, end_x=230, end_y=0)["entities"][0]["id"]
    base = L("add_dimension", sketch="S", type="distance", entities=[linea], value=30)["dimension"]
    v.editar_operacion(s.paso("S").id)
    A.esperar(500)
    lz = v.modo_boceto.lienzo
    v.visor.encuadrar()
    A.esperar(300)
    for k in cotas():                                  # solo queda la de 30; las demás de pruebas anteriores se borran
        if k.id != base["id"]:
            lz.b.eliminar(k.id)
    lz.set_herramienta("cota")
    clic(60, 15)                                       # el círculo: la caja de diámetro queda abierta
    lz.grab()
    zona = lz._zonas_cotas.get(base["id"])
    A.reg(AR, "la cota con nombre se ve y tiene zona de clic", zona is not None and base["name"] == lz.b.cotas[base["id"]].nombre,
          f"zona={zona}, nombre={base['name']}")
    if zona is None or lz.entrada is None:
        return
    mover(zona.center())                                   # pasar el mouse con la caja abierta resalta la cota
    A.esperar(100)
    A.reg(AR, "con la caja abierta, pasar el mouse sobre otra cota la resalta", lz._cita_sobre == base["id"], f"_cita_sobre={lz._cita_sobre}")
    QTest.mouseClick(lz, Qt.LeftButton, Qt.NoModifier, zona.center().toPoint())
    A.esperar(100)
    texto = lz.entrada.campos[0].text() if lz.entrada is not None else ""
    A.reg(AR, "clic en otra cota la cita por su nombre en la caja", texto == base["name"], f"caja=«{texto}», nombre={base['name']!r}")
    if lz.entrada is not None:
        antes = {c.id for c in cotas()}
        campo = lz.entrada.campos[0]
        QTest.keyClicks(campo, " / 2")
        QTest.keyClick(campo, Qt.Key_Return)
        A.esperar(120)
        c = cota_nueva(antes)
        A.reg(AR, "Enter con «dN / 2» crea el diámetro citando a la otra", c is not None and c.expresion == f"{base['name']} / 2",
              str(c and c.expresion))
        A.reg(AR, "la cota con expresión se lee con «fx:» delante (como Fusion)",
              c is not None and lz._texto_cota(c, lz.b.medir(c)).startswith("fx: "), str(c and lz._texto_cota(c, lz.b.medir(c))))
        if c is not None:
            lz.deshacer()
            A.esperar(100)
    # una cota creada en esta misma edición también se cita: toma su nombre al citarla
    antes = {c.id for c in cotas()}
    lz.set_herramienta("cota")
    clic(12.5, 25)
    clic(12.5, 36)
    escribir("25")
    fresca = cota_nueva(antes)
    lz.set_herramienta("cota")
    clic(25, 12.5)
    clic(36, 12.5)
    lz.grab()
    zona = lz._zonas_cotas.get(fresca.id) if fresca is not None else None
    if zona is not None and lz.entrada is not None:
        QTest.mouseClick(lz, Qt.LeftButton, Qt.NoModifier, zona.center().toPoint())
        A.esperar(100)
        texto = lz.entrada.campos[0].text() if lz.entrada is not None else ""
        A.reg(AR, "clic en una cota recién creada la nombra y la cita", bool(fresca.nombre) and texto == fresca.nombre,
              f"caja=«{texto}», nombre={fresca.nombre!r}")
        campo = lz.entrada.campos[0] if lz.entrada is not None else None
        if campo is not None:
            antes2 = {c.id for c in cotas()}
            QTest.keyClicks(campo, " * 2")
            QTest.keyClick(campo, Qt.Key_Return)
            A.esperar(120)
            c = cota_nueva(antes2)
            A.reg(AR, "Enter con «dN * 2» se evalúa (50) y crea la cota", c is not None and c.expresion == f"{fresca.nombre} * 2",
                  str(c and c.expresion))
            if c is not None:
                lz.deshacer()
                A.esperar(100)
    else:
        A.reg(AR, "cota recién creada: preparación", False, f"zona={zona}")
    lz.set_herramienta("seleccionar")


run("citar una cota con un clic (BOC-35)", citar_una_cota)

def arrastrar_todas():
    """Fusion deja arrastrar toda cota con el mouse (la línea o el arco y el texto siguen al cursor; el valor no cambia):
    diámetro, radio y ángulo, además de las lineales que ya se movían."""
    for k in cotas():
        lz.b.eliminar(k.id)
    lz.set_herramienta("seleccionar")
    A.esperar(60)
    casos = [("diámetro", [(60, 15)], None, "10", None),
             ("radio", [(60, 15)], None, "5", "Radio"),
             ("ángulo", [(112.5, 0), (106, 9)], (118, 10), "40", None)]
    for nombre, picks, ubicar, texto, menu in casos:
        antes = {c.id for c in cotas()}
        lz.set_herramienta("cota")
        A.esperar(60)
        for q in picks:
            clic(*q)
        if ubicar:
            clic(*ubicar)
        if menu is not None and lz.entrada is not None:
            A.MENUS.clear()
            derecho(px(70, 25), 550)
            next(a for a in A.MENUS[-1].actions() if a.text() == menu).trigger()
            A.esperar(60)
        if lz.entrada is not None:
            escribir(texto)
        c = cota_nueva(antes)
        A.reg(AR, f"{nombre}: la cota se crea", c is not None, str(c and (c.tipo, c.expresion, c.referencia)))
        if c is None:
            continue
        lz.set_herramienta("seleccionar")
        A.esperar(80)
        lz.grab()
        zona = lz._zonas_cotas.get(c.id)
        if zona is None:
            A.reg(AR, f"{nombre}: tiene zona para arrastrar", False, "")
            continue
        ini = zona.center().toPoint()
        valor0, expr0 = lz.b.medir(c), c.expresion
        mover(zona.center())
        A.esperar(80)
        QTest.mousePress(lz, Qt.LeftButton, Qt.NoModifier, ini)
        for k in range(1, 7):
            mover(zona.center() + zona.center().__class__(9 * k, -9 * k))
            A.esperar(30)
        QTest.mouseRelease(lz, Qt.LeftButton, Qt.NoModifier, ini + type(ini)(54, -54))
        A.esperar(120)
        c = lz.b.cotas[c.id]
        lz.grab()
        zona2 = lz._zonas_cotas.get(c.id)
        movio = zona2 is not None and (abs(zona2.center().x() - zona.center().x()) > 15 or abs(zona2.center().y() - zona.center().y()) > 15)
        A.reg(AR, f"{nombre}: arrastrarla con el mouse la mueve", "ubic" in c.datos and movio,
              f"datos={sorted(c.datos)}; zona antes={zona.center().toPoint()}, después={zona2.center().toPoint() if zona2 else None}")
        A.reg(AR, f"{nombre}: arrastrarla no cambia su valor", c.expresion == expr0 and abs(lz.b.medir(c) - valor0) < 1e-6,
              f"{c.expresion} / {lz.b.medir(c):.4f}")
        lz.deshacer()
        A.esperar(80)
        A.reg(AR, f"{nombre}: un Ctrl+Z deshace el arrastre y la cota sigue", c.id in lz.b.cotas and "ubic" not in lz.b.cotas[c.id].datos,
              f"cota sigue={c.id in lz.b.cotas}")
        lz.deshacer()
        A.esperar(80)


run("arrastrar toda cota (radio, diámetro y ángulo)", arrastrar_todas)


def clic_derecho_sale():
    """Clic derecho rápido en una herramienta: corta lo que está a medias y se queda; sin nada a medias, sale a Seleccionar
    (igual que Esc). Arrastrado sigue siendo del visor (gesto del menú radial) y en Seleccionar, su menú de siempre."""
    for k in cotas():
        lz.b.eliminar(k.id)
    pedidos = []
    lz.visor.menu_contextual.connect(lambda *a: pedidos.append("menu"))
    lz.visor.gesto_radial.connect(lambda sector: pedidos.append(("gesto", sector)))
    for herramienta in ("linea", "rectangulo", "circulo", "arco", "spline_ajuste"):
        lz.set_herramienta(herramienta)
        A.esperar(60)
        clic(200, 60)
        puesto = bool(lz.clics)
        derecho(px(250, 30))
        A.reg(AR, f"{herramienta}: el clic derecho corta lo puesto y sigue en la herramienta",
              puesto and not lz.clics and lz.herramienta == herramienta, f"clics={lz.clics}, herramienta={lz.herramienta}")
        derecho(px(250, 30))
        A.reg(AR, f"{herramienta}: otro clic derecho sale a Seleccionar", lz.herramienta == "seleccionar", lz.herramienta)
    lz.set_herramienta("linea")
    clic(200, 60)
    QTest.keyClick(lz, Qt.Key_Escape)
    A.esperar(60)
    quedo = lz.herramienta == "linea" and not lz.clics
    QTest.keyClick(lz, Qt.Key_Escape)
    A.esperar(60)
    A.reg(AR, "Esc hace lo mismo: corta, y otro Esc sale", quedo and lz.herramienta == "seleccionar", lz.herramienta)
    lz.set_herramienta("cota")
    clic(12.5, 25)
    derecho(px(250, 30))
    A.reg(AR, "cota: el clic derecho rápido suelta la línea elegida y sigue en la herramienta",
          not lz.picks and lz.herramienta == "cota", f"picks={lz.picks}, herramienta={lz.herramienta}")
    clic(60, 15)
    abierta = lz.entrada is not None and lz.entrada.isVisible()
    derecho(px(250, 30))
    A.reg(AR, "cota con la caja de valor abierta: el clic derecho la cierra y suelta lo elegido",
          abierta and lz.entrada is None and not lz.picks and not cotas(), f"abierta={abierta}, picks={lz.picks}")
    derecho(px(250, 30))
    A.reg(AR, "cota: otro clic derecho sale de la herramienta", lz.herramienta == "seleccionar", lz.herramienta)
    lz.set_herramienta("linea")
    clic(200, 60)
    ini = px(250, 30)
    pedidos.clear()
    QTest.mousePress(lz, Qt.RightButton, Qt.NoModifier, ini)
    for k in range(1, 9):
        mover(ini + type(ini)(10 * k, 0))
        A.esperar(20)
    QTest.mouseRelease(lz, Qt.RightButton, Qt.NoModifier, ini + type(ini)(80, 0))
    A.esperar(100)
    A.reg(AR, "clic derecho arrastrado en una herramienta no es un clic rápido: llega al visor como gesto del menú radial",
          any(isinstance(x, tuple) for x in pedidos) and "menu" not in pedidos, f"clics={lz.clics}, visor={pedidos}")
    QTest.keyClick(lz, Qt.Key_Escape)
    QTest.keyClick(lz, Qt.Key_Escape)
    A.esperar(60)
    pedidos.clear()
    lz.set_herramienta("seleccionar")
    derecho(px(250, 30))
    A.reg(AR, "en Seleccionar el clic derecho queda como antes (menú del visor) y no cambia de herramienta",
          "menu" in pedidos and lz.herramienta == "seleccionar", f"visor={pedidos}")


run("clic derecho cancela o sale (herramientas del boceto)", clic_derecho_sale)


# Navegador: «Mostrar cotas» del boceto (Fusion: clic derecho en el boceto)
v._salir_de_boceto()
A.esperar(300)
arbol = v.navegador.arbol


def todos(it=None):
    if it is None:
        for i in range(arbol.topLevelItemCount()):
            yield from todos(arbol.topLevelItem(i))
    else:
        yield it
        for j in range(it.childCount()):
            yield from todos(it.child(j))


def menu_navegador():
    it = next((i for i in todos() if i.text(0) == "S"), None)
    if it is None:
        return None
    p = it.parent()
    while p is not None:
        p.setExpanded(True)
        p = p.parent()
    arbol.scrollToItem(it)
    r = arbol.visualItemRect(it)
    A.MENUS.clear()
    A.clic_derecho(arbol.viewport(), r.center())
    return [a.text() for a in A.MENUS[-1].actions() if a.text()] if A.MENUS else None


textos = menu_navegador()
A.reg(AR, "el menú del boceto en el navegador tiene «Mostrar cotas» (como Fusion)", bool(textos) and any("cota" in t.lower() for t in textos), str(textos))

A.guardar_registro("u2d_boceto_cotas")
fallas = [r for r in A.REGISTRO if not r["ok"]]
print(f"\n=== {len(A.REGISTRO)} comprobaciones, {len(fallas)} con ✗ ===")
v.close()
sys.exit(0)

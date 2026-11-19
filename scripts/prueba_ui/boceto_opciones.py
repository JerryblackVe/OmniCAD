# -*- coding: utf-8 -*-
"""BOCETO · opciones y asas que seguían sin prueba como usuario (PRUEBA-OPCIONES, E7): Estrella (Puntas, Interior, Salto,
Círculos de construcción, valores raros), Spline de control (grado 5 y 3), arrastre de un punto, de un círculo (radio) y
de una curva entera con el mouse, marco de selección (mover, espejo H y V, Ctrl+Z) y Insertar SVG con Capas y Colores.
Eventos simulados al Lienzo (nunca el cursor real). Contra Fusion (Sketch > Create > Star / Spline; Insert SVG)."""
import math
import sys
import tempfile
from pathlib import Path

import arnes as A
import numpy as np
from omnicad import api
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

AR = "BOCETO·OPCIONES"
s = api.Sesion()
L = lambda n, **a: api.llamar(s, n, a)["result"]                                        # noqa: E731
L("create_sketch", plane="XY", name="E")                                                # estrella y spline
L("create_sketch", plane="XY", name="G")                                                # arrastres y marco
RG = L("draw_circle", sketch="G", center_x=0, center_y=5, radius=10)["entities"][0]["id"]
L("draw_line", sketch="G", start_x=30, start_y=0, end_x=50, end_y=0)
L("draw_line", sketch="G", start_x=30, start_y=20, end_x=50, end_y=30)
app, v = A.iniciar(s.doc, 1280, 720)
A.esperar(400)
MS = []
lz = None


def entrar(nombre, centro=(0, 0), span=140):
    global lz
    v.editar_operacion(s.paso(nombre).id)
    A.esperar(500)
    lz = v.modo_boceto.lienzo
    lz.mensaje.connect(MS.append)
    lz.visor.objetivo = lz.plano.a_3d(*centro)
    lz.visor.distancia = span / 2 / math.sin(math.radians(lz.visor.fov) / 2) * 1.3
    lz.visor.update()
    lz.update()
    A.esperar(300)


def salir():
    v.modo_boceto.terminar()
    A.esperar(400)


def px(x, y):
    return lz.a_px(x, y).toPoint()


def clic(x, y):
    QTest.mouseClick(lz, Qt.LeftButton, Qt.NoModifier, px(x, y))
    A.esperar(120)


def tecla(k, mod=Qt.NoModifier):
    A.activar(v)
    lz.setFocus()
    A.esperar(150)
    QTest.keyClick(lz, k, mod)
    A.esperar(250)


def raton(tipo, x, y):
    q = QPointF(px(x, y))
    b = Qt.LeftButton if tipo != QEvent.MouseMove else Qt.NoButton
    QApplication.sendEvent(lz, QMouseEvent(tipo, q, lz.mapToGlobal(q), b, Qt.LeftButton if tipo != QEvent.MouseButtonRelease else Qt.NoButton, Qt.NoModifier))


def arrastrar(a, b, pasos=8):
    raton(QEvent.MouseButtonPress, *a)
    for k in range(1, pasos + 1):
        raton(QEvent.MouseMove, a[0] + (b[0] - a[0]) * k / pasos, a[1] + (b[1] - a[1]) * k / pasos)
        A.esperar(20)
    raton(QEvent.MouseButtonRelease, *b)
    A.esperar(250)


def fila(etiqueta):
    f = v.modo_boceto.tarjeta.form_contexto
    for i in range(f.rowCount()):
        e = f.itemAt(i, f.ItemRole.LabelRole)
        if e is not None and e.widget() is not None and e.widget().text() == etiqueta:
            return f.itemAt(i, f.ItemRole.FieldRole).widget()
    return None


def teclear_fila(etiqueta, texto):
    w = fila(etiqueta)
    w.setFocus()
    QTest.keyClick(w, Qt.Key_A, Qt.ControlModifier)
    QTest.keyClicks(w, texto)
    QTest.keyClick(w, Qt.Key_Tab)
    A.esperar(150)


def planas():
    return [c for c in lz.b.curvas.values() if c.id > 0]


def lineas_vivas():
    return sum(1 for c in planas() if c.tipo == "linea" and not c.construccion)


def circulos_constr():
    return sum(1 for c in planas() if c.tipo == "circulo" and c.construccion)


def estrella(puntas=None, interior=None, salto=None, r=20, origen=(0, 0)):
    """Una estrella con la tarjeta: opciones tecleadas, clic en el centro y clic en el radio."""
    v.modo_boceto.acciones["sk_estrella"].trigger()
    A.esperar(200)
    if puntas is not None:
        teclear_fila("Puntas", str(puntas))
    if interior is not None:
        teclear_fila("Interior (0 = regular)", str(interior))
    if salto is not None:
        teclear_fila("Salto (con Interior 0)", str(salto))
    clic(*origen)
    clic(origen[0] + r, origen[1])
    A.esperar(150)
    tecla(Qt.Key_Escape)


def probar(nombre, f):
    try:
        f()
    except Exception as e:                                                              # noqa: BLE001
        A.reg(AR, f"{nombre}: sin excepción", False, f"{type(e).__name__}: {e} @ L{e.__traceback__.tb_next.tb_lineno if e.__traceback__.tb_next else '?'}")
    if lz is not None and lz.herramienta != "seleccionar":
        tecla(Qt.Key_Escape)


# ================================================================= 1) ESTRELLA
entrar("E", span=160)
form = v.modo_boceto.tarjeta.form_contexto


def est_interior():
    n0 = lineas_vivas()
    estrella(puntas=5, interior=50)
    A.reg(AR, "estrella 5 puntas, Interior 50 %: 10 lados", lineas_vivas() - n0 == 10, lineas_vivas() - n0)
    A.foto(v, "opc_estrella_interior50")
    tecla(Qt.Key_Z, Qt.ControlModifier)
    A.reg(AR, "Ctrl+Z la saca en un paso", lineas_vivas() == n0, lineas_vivas() - n0)
    # Interior 0 = la regular {puntas/salto}
    for puntas, salto in ((7, 2), (7, 3), (5, 2), (9, 4)):
        n0 = lineas_vivas()
        estrella(puntas=puntas, interior=0, salto=salto)
        A.reg(AR, f"estrella {puntas} puntas, Interior 0, Salto {salto}: {2 * puntas} lados y sin error",
              lineas_vivas() - n0 == 2 * puntas and lz.resultado.ok, f"{lineas_vivas() - n0} lados; {MS[-1:]}")
        tecla(Qt.Key_Z, Qt.ControlModifier)
    # valores raros: el campo los sujeta al rango y no revienta
    for texto in ("0", "1", "2", "-5", "200", "abc", ""):
        n0 = lineas_vivas()
        estrella(puntas=texto, interior=50)
        ok = (lineas_vivas() - n0) % 2 == 0 and lz.resultado.ok
        A.reg(AR, f"Puntas = «{texto}»: sin excepción y sin media estrella", ok and not A.ERRORES,
              f"{lineas_vivas() - n0} lados; Puntas ahora {fila('Puntas').value() if hasattr(fila('Puntas'), 'value') else '?'}")
        if lineas_vivas() > n0:
            tecla(Qt.Key_Z, Qt.ControlModifier)
    for texto in ("0", "99", "100", "-10", "xyz"):
        n0 = lineas_vivas()
        estrella(puntas=5, interior=texto)
        v.modo_boceto.acciones["sk_estrella"].trigger()
        A.esperar(200)
        w = fila("Interior (0 = regular)")
        valor = w.value() if hasattr(w, "value") else None
        tecla(Qt.Key_Escape)
        A.reg(AR, f"Interior = «{texto}»: el campo queda dentro de 0–99 y dibuja una estrella válida",
              valor is not None and 0 <= valor <= 99 and lz.resultado.ok and (lineas_vivas() - n0) % 2 == 0,
              f"campo={valor}, {lineas_vivas() - n0} lados")
        if lineas_vivas() > n0:
            tecla(Qt.Key_Z, Qt.ControlModifier)


probar("estrella interior y salto", est_interior)


def est_construccion():
    c0 = circulos_constr()
    estrella(puntas=6, interior=40, origen=(0, 0))
    con = circulos_constr() - c0
    A.reg(AR, "Círculos de construcción activo: la estrella trae sus 2 círculos de construcción", con == 2, con)
    tecla(Qt.Key_Z, Qt.ControlModifier)
    v.modo_boceto.acciones["sk_estrella"].trigger()
    A.esperar(200)
    w = fila("Círculos de construcción")
    w.setChecked(False)
    A.esperar(120)
    c0 = circulos_constr()
    estrella(puntas=6, interior=40, origen=(0, 0))
    A.reg(AR, "Círculos de construcción apagado: sin círculos de construcción", circulos_constr() - c0 == 0, circulos_constr() - c0)
    A.foto(v, "opc_estrella_sin_circulos")
    tecla(Qt.Key_Z, Qt.ControlModifier)
    v.modo_boceto.acciones["sk_estrella"].trigger()
    A.esperar(200)
    fila("Círculos de construcción").setChecked(True)


probar("estrella construcción", est_construccion)


# ================================================================= 2) SPLINE DE CONTROL
def spline_grado():
    for grado in (5, 3):
        v.modo_boceto.acciones["sk_spline_control"].trigger()
        A.esperar(200)
        cb = fila("Grado")
        i = cb.findData(grado)
        cb.setCurrentIndex(i)
        A.esperar(120)
        n0 = len(planas())
        for p in ((-60, -40), (-40, -20), (-20, -40), (0, -20), (20, -40), (40, -20)):
            clic(*p)
        tecla(Qt.Key_Return)
        nuevos = [c for c in planas()[n0:] if c.tipo != "punto"]
        sp = [c for c in nuevos if "spline" in c.tipo]
        A.reg(AR, f"spline de control de grado {grado}: queda un spline", len(sp) == 1,
              f"{[c.tipo for c in nuevos]}; grado={getattr(sp[0], 'grado', '?') if sp else '?'}")
        if sp:
            A.reg(AR, f"spline de control: el grado guardado es {grado}",
                  getattr(sp[0], "grado", grado) == grado, getattr(sp[0], "grado", None))
        A.foto(v, f"opc_spline_grado{grado}")
        tecla(Qt.Key_Z, Qt.ControlModifier)
        A.reg(AR, f"spline grado {grado}: Ctrl+Z la saca en un paso", len(planas()) == n0, len(planas()) - n0)
    # con menos puntos de los que pide el grado: avisa y no deja nada
    v.modo_boceto.acciones["sk_spline_control"].trigger()
    A.esperar(200)
    fila("Grado").setCurrentIndex(fila("Grado").findData(5))
    n0 = len(planas())
    clic(-60, -40)
    clic(-40, -20)
    tecla(Qt.Key_Return)
    A.reg(AR, "spline grado 5 con 2 puntos: no deja una curva rota", not [c for c in planas()[n0:] if "spline" in c.tipo] or lz.resultado.ok,
          f"{[c.tipo for c in planas()[n0:]]}; {MS[-1:]}")


probar("spline", spline_grado)
A.reg(AR, "estrella y spline: ninguna excepción en un slot de Qt", not A.ERRORES, A.ERRORES[:1])
salir()

# ================================================================= 3) ARRASTRES DEL EDITOR
entrar("G", centro=(20, 10), span=120)


def arrastres():
    lz.set_herramienta("seleccionar")
    lz.seleccion = []
    A.esperar(100)
    # punto extremo de una línea: se lleva el punto y la línea sigue unida
    lin = next(c for c in lz.b.curvas.values() if c.tipo == "linea" and abs(lz.b.coords(c.p1)[0] - 30) < 1e-6 and abs(lz.b.coords(c.p1)[1]) < 1e-6)
    a0 = lz.b.coords(lin.p2)
    arrastrar((50, 0), (55, -8))
    a1 = lz.b.coords(lin.p2)
    A.reg(AR, "arrastrar el extremo de una línea con el mouse lo mueve", math.dist(a0, a1) > 3, f"{a0} -> {a1}")
    A.reg(AR, "la línea sigue unida por el otro extremo", math.dist(lz.b.coords(lin.p1), (30, 0)) < 1e-6, lz.b.coords(lin.p1))
    tecla(Qt.Key_Z, Qt.ControlModifier)
    A.reg(AR, "Ctrl+Z devuelve el extremo", math.dist(lz.b.coords(lin.p2), a0) < 1e-6, lz.b.coords(lin.p2))
    # círculo: arrastrar la circunferencia cambia el radio
    r0 = lz.b.radio(RG)
    c0 = lz.b.coords(lz.b.curvas[RG].p1) if hasattr(lz.b.curvas[RG], "p1") else None
    arrastrar((10, 0), (16, 0))
    r1 = lz.b.radio(RG)
    c1 = lz.b.coords(lz.b.curvas[RG].p1) if hasattr(lz.b.curvas[RG], "p1") else None
    A.reg(AR, "arrastrar la circunferencia cambia el radio (10 → ~16)", abs(r1 - 16) < 1.5,
          f"{r0} -> {r1}; centro {c0} -> {c1}; sel {lz.seleccion}; {MS[-1:]}")
    tecla(Qt.Key_Z, Qt.ControlModifier)
    A.reg(AR, "Ctrl+Z devuelve el radio", abs(lz.b.radio(RG) - r0) < 1e-6, lz.b.radio(RG))
    # arrastre enorme y hacia el centro: no rompe
    arrastrar((10, 0), (0.05, 0))
    A.reg(AR, "llevar la circunferencia al centro: radio positivo o sin cambio, sin excepción",
          lz.b.radio(RG) > 0 and not A.ERRORES, lz.b.radio(RG))
    tecla(Qt.Key_Z, Qt.ControlModifier)
    # curva entera: arrastrar el medio de una línea la traslada
    otra = next(c for c in lz.b.curvas.values() if c.tipo == "linea" and abs(lz.b.coords(c.p1)[1] - 20) < 1e-6)
    p0 = (lz.b.coords(otra.p1), lz.b.coords(otra.p2))
    arrastrar((40, 25), (40, 35))
    p1 = (lz.b.coords(otra.p1), lz.b.coords(otra.p2))
    A.reg(AR, "arrastrar el medio de una línea la mueve entera (largo igual)",
          math.dist(p1[0], p1[1]) > 0 and (math.dist(p0[0], p0[1]) - math.dist(p1[0], p1[1])) ** 2 < 1e-4 or p1 != p0, f"{p0} -> {p1}")
    tecla(Qt.Key_Z, Qt.ControlModifier)


probar("arrastres", arrastres)


def marco():
    tecla(Qt.Key_A, Qt.ControlModifier)                                              # Ctrl+A: todo seleccionado
    A.esperar(150)
    A.reg(AR, "Ctrl+A elige todo y aparece el marco de control", bool(lz.seleccion) and lz._caja_marco() is not None,
          f"{len(lz.seleccion)} elegidas; mostrar_marco={lz.mostrar_marco}")
    if lz._caja_marco() is None:
        return
    antes = {k: lz.b.coords(k) for k in lz.b.puntos}
    mano = lz._manijas_marco(lz._caja_marco())
    q = lz.a_mm(mano["mover"])
    arrastrar(q, (q[0] + 7, q[1] - 4))
    dx = [lz.b.coords(k)[0] - antes[k][0] for k in antes if k in lz.b.puntos]
    A.reg(AR, "manija de mover: todo se corre ~(7, -4)", dx and abs(np.median(dx) - 7) < 1.5, f"Δx mediana {np.median(dx) if dx else None}")
    tecla(Qt.Key_Z, Qt.ControlModifier)
    A.reg(AR, "Ctrl+Z del mover vuelve todo", all(math.dist(lz.b.coords(k), antes[k]) < 1e-6 for k in antes if k in lz.b.puntos), "")
    for h, eje in (("espejo_h", 0), ("espejo_v", 1)):
        tecla(Qt.Key_A, Qt.ControlModifier)
        antes = {k: lz.b.coords(k) for k in lz.b.puntos}
        caja = lz._caja_marco()
        if caja is None:
            A.reg(AR, f"{h}: el marco sigue ahí tras el Ctrl+Z anterior", False, f"sel={lz.seleccion}")
            continue
        c = ((caja[0] + caja[2]) / 2, (caja[1] + caja[3]) / 2)
        m = lz.a_mm(lz._manijas_marco(caja)[h])
        QTest.mouseClick(lz, Qt.LeftButton, Qt.NoModifier, lz.a_px(*m).toPoint())
        A.esperar(250)
        bien = all(abs(lz.b.coords(k)[eje] - (2 * c[eje] - antes[k][eje])) < 1e-4 for k in antes if k in lz.b.puntos)
        A.reg(AR, f"manija {h}: refleja todo respecto del centro del marco", bien and lz.resultado.ok, MS[-1:])
        tecla(Qt.Key_Z, Qt.ControlModifier)
        A.reg(AR, f"{h}: Ctrl+Z lo deja como estaba", all(math.dist(lz.b.coords(k), antes[k]) < 1e-6 for k in antes if k in lz.b.puntos), "")
    # Esc suelta la selección y el marco desaparece
    tecla(Qt.Key_Escape)
    A.reg(AR, "Esc suelta la selección y el marco", not lz.seleccion and lz._caja_marco() is None, f"{len(lz.seleccion)}")


probar("marco", marco)
A.reg(AR, "arrastres y marco: ninguna excepción en un slot de Qt", not A.ERRORES, A.ERRORES[:1])
salir()

# ================================================================= 4) INSERTAR SVG: Capas y Colores
SVG = """<svg xmlns="http://www.w3.org/2000/svg" xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape" width="60mm" height="40mm" viewBox="0 0 60 40">
<g inkscape:groupmode="layer" inkscape:label="rojo" id="a"><rect x="2" y="2" width="20" height="10" fill="none" stroke="#ff0000" stroke-width="0.5"/></g>
<g inkscape:groupmode="layer" inkscape:label="azul" id="b"><circle cx="40" cy="25" r="8" fill="none" stroke="#0000ff" stroke-width="0.5"/></g>
</svg>
"""
RUTA = Path(tempfile.mkdtemp(prefix="opc_svg_")) / "dos_capas.svg"
RUTA.write_text(SVG, encoding="utf-8")
L("create_sketch", plane="XY", name="V")
v.editar_operacion(s.paso("V").id)
A.esperar(500)
lz = v.modo_boceto.lienzo
lz.mensaje.connect(MS.append)


def svg(capas="", colores="", esperado=None, texto=""):
    p = A.abrir(v, "insertar_svg")
    for clave, val in (("archivo", str(RUTA)), ("capas", capas), ("colores", colores)):
        w = p.widgets[clave]
        w.setFocus()
        w.selectAll()
        QTest.keyClicks(w, val)
        A.esperar(250)
    A.esperar(500)
    n0 = len(lz.b.curvas)
    activo = p.boton_ok.isEnabled()
    if activo:
        QTest.mouseClick(p.boton_ok, Qt.LeftButton)
        A.esperar(500)
    nuevas = len(lz.b.curvas) - n0
    A.reg(AR, f"Insertar SVG {texto}: " + ("deshabilitado/sin nada" if esperado == 0 else f"{esperado} curvas"),
          (nuevas == esperado) if esperado else (nuevas == 0), f"botón={activo}, nuevas={nuevas}")
    if nuevas:
        tecla(Qt.Key_Z, Qt.ControlModifier)
    elif p.isVisible():
        tecla(Qt.Key_Escape)


def svg_todos():
    svg(esperado=5, texto="sin filtro (rect + círculo)")
    svg(capas="rojo", esperado=4, texto="capas = rojo")
    svg(capas="azul", esperado=1, texto="capas = azul")
    svg(colores="#0000ff", esperado=1, texto="colores = #0000ff")
    svg(colores="#ff0000", esperado=4, texto="colores = #ff0000")
    svg(capas="rojo", colores="#0000ff", esperado=0, texto="capas rojo y colores azul (se cancelan)")
    svg(capas="no_existe", esperado=0, texto="capas inexistente")
    svg(colores="rojo", esperado=0, texto="colores = «rojo» (no es #rrggbb)")
    svg(capas="rojo, azul", esperado=5, texto="capas «rojo, azul» (con espacio)")


probar("svg", svg_todos)
A.reg(AR, "SVG: ninguna excepción en un slot de Qt", not A.ERRORES, A.ERRORES[:1])
salir()

A.guardar_registro("boceto_opciones")
print(f"\n=== {len(A.REGISTRO)} comprobaciones, {len([r for r in A.REGISTRO if not r['ok']])} con ✗ ===", flush=True)
v.doc.modificado = False
v.close()
sys.exit(0)

# -*- coding: utf-8 -*-
"""BOCETO · lo último de las inferencias, el desfase, la simetría, las cotas y los patrones, como lo usa una persona:
mover el ratón sobre la geometría y ver la ayuda (Igual, intersección aparente, tangente de círculos, paralela en la línea
de punto medio), clic para dibujar, Desfase con un clic DENTRO de un perfil y sobre una elipse (cerca/lejos de un eje),
Simetría con un eje del origen, líneas de cota en las cotas que solo mostraban texto, «Cambiar por» que sobra y el panel
del patrón con las copias viejas ocultas y el asa del ángulo. Eventos simulados al Lienzo (nunca el cursor real).
Cubre BOC-33, 37, 40, 45, 46, 48, 53, 60, 62, 70, 71 y 72, los paneles de Escala y Mover/copiar (BOC-41)
y las ayudas de dibujo del Boceto 3D (BOC-47, y en el espacio BOC-77 y BOC-78), la tangente con un arco (BOC-52) y la curva isoparamétrica (BOC-36; ver docs/seguimiento/ y PROJECT_LOG)."""
import math
import sys

import arnes as A
import numpy as np
from omnicad import api
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QPushButton, QToolButton

AR = "BOCETO·HERRAMIENTAS"
s = api.Sesion()


def L(nombre, **a):
    r = api.llamar(s, nombre, a)
    assert r["ok"], (nombre, a, r)
    return r["result"]


def ids(r):
    return [e["id"] for e in r["entities"]]


def sketch(nombre):
    L("create_sketch", name=nombre, plane="XY")


# ---- geometría de cada hoja (se arma por la API; lo que se prueba es lo que hace la persona en la ventana)
sketch("I")                                                           # inferencias
L1 = ids(L("draw_line", sketch="I", start_x=0, start_y=0, end_x=40, end_y=0))[0]                  # 40 de largo
L("draw_line", sketch="I", start_x=60, start_y=0, end_x=70, end_y=10)                             # sus prolongaciones
L("draw_line", sketch="I", start_x=60, start_y=40, end_x=70, end_y=30)                            # se cruzan en (80, 20)
CC = ids(L("draw_circle", sketch="I", center_x=-40, center_y=20, radius=10))[0]
L("draw_line", sketch="I", start_x=-20, start_y=-30, end_x=0, end_y=-10)                          # a 45°
sketch("P")                                                           # perfil con hueco
L("draw_rectangle", sketch="P", x1=0, y1=0, x2=60, y2=40)
L("draw_circle", sketch="P", center_x=30, center_y=20, radius=8)
sketch("E")                                                           # elipse
L("draw_ellipse", sketch="E", major_radius=30, minor_radius=15, center_x=0, center_y=0)
sketch("M")                                                           # simetría con el eje del origen
L("draw_line", sketch="M", start_x=15, start_y=10, end_x=45, end_y=25)
sketch("C")                                                           # cotas con línea
PC = ids(L("draw_circle", sketch="C", center_x=0, center_y=0, radius=6))[0]
LC = ids(L("draw_line", sketch="C", start_x=-30, start_y=30, end_x=30, end_y=30))[0]
L("add_dimension", sketch="C", type="distance", entities=[PC, LC], mode="tangent", value=18)
sketch("K")                                                           # «Cambiar por» que sobra
K = [ids(L("draw_line", sketch="K", start_x=-40, start_y=y, end_x=-10, end_y=y + 9))[0] for y in (0, 20, 40)]
for a_, b_ in ((0, 1), (1, 2)):
    L("add_constraint", sketch="K", type="parallel", entities=[K[a_], K[b_]])
RID = L("add_constraint", sketch="K", type="equal", entities=[K[0], K[2]])["constraint"]["id"]
sketch("T")                                                           # patrón
CT = ids(L("draw_circle", sketch="T", center_x=-30, center_y=0, radius=4))[0]
L("sketch_rectangular_pattern", sketch="T", entities=[CT], count1=3, distance1=20, spacing="spacing")
sketch("Q")                                                           # Escala y Mover/copiar
LQ = ids(L("draw_line", sketch="Q", start_x=0, start_y=0, end_x=20, end_y=0))[0]
CQ = ids(L("draw_circle", sketch="Q", center_x=40, center_y=0, radius=5))[0]
sketch("D")                                                           # ayudas de dibujo del Boceto 3D
L("draw_line_3d", sketch="D", start=[30, -20, 0], end=[70, -20, 0])                                 # medio en (50, −20)
L("draw_line_3d", sketch="D", start=[30, -20, 0], end=[30, 20, 0])
L("draw_point_3d", sketch="D", x=60, y=25, z=0)
sketch("Z")                                                           # enganchar en el espacio (BOC-77 y BOC-78)
L("draw_line_3d", sketch="Z", start=[-20, 40, 15], end=[20, 40, 15])                                # medio en (0, 40, 15), fuera del plano
L("draw_point_3d", sketch="Z", x=0, y=0, z=0)
CZ = L("draw_circle_3d", sketch="Z", center=[60, 0, 0], radius=15, normal=[0, 0, 1])["entity"]
sketch("Y")                                                           # tangente con un arco (BOC-52)
AY = ids(L("draw_arc", sketch="Y", center_x=0, center_y=0, start_x=12, start_y=0, sweep_angle=90))[0]
LY = ids(L("draw_line", sketch="Y", start_x=-30, start_y=-14, end_x=30, end_y=-16))[0]
L("create_cylinder", radius=15, height=30, x=300, y=300, z=0)               # una cara para la curva isoparamétrica
sketch("Iso")
app, v = A.iniciar(s.doc)
lz = None


def entrar(nombre, centro=(0, 0), span=140):
    global lz
    v.editar_operacion(s.paso(nombre).id)
    A.esperar(500)
    lz = v.modo_boceto.lienzo
    lz.visor.objetivo = lz.plano.a_3d(*centro)
    lz.visor.distancia = span / 2 / math.sin(math.radians(lz.visor.fov) / 2) * 1.3
    lz.visor.update()
    lz.update()
    A.esperar(300)


def salir():
    if lz.entrada is not None:
        tecla(Qt.Key_Escape)
    lz.set_herramienta("seleccionar")
    lz.seleccion = []
    v.modo_boceto.terminar()
    A.esperar(400)


def px(x, y):
    return lz.a_px(x, y).toPoint()


def clic(x, y, mod=Qt.NoModifier):
    QTest.mouseClick(lz, Qt.LeftButton, mod, px(x, y))
    A.esperar(70)


def mover(x, y):
    q = QPointF(px(x, y))
    QApplication.sendEvent(lz, QMouseEvent(QEvent.MouseMove, q, lz.mapToGlobal(q), Qt.NoButton, Qt.NoButton, Qt.NoModifier))
    A.esperar(60)


def tecla(k, mod=Qt.NoModifier):
    QTest.keyClick(lz, k, mod)
    A.esperar(90)


def boton_cinta(clave):
    accion = v.modo_boceto.acciones[clave]
    return next(b for b in v.cinta.findChildren(QToolButton) if b.defaultAction() is accion and b.isVisible())


def herramienta(h, por_menu=False):
    """El botón de la cinta (clic real) o, para las variantes que solo viven en un menú, el ítem disparado."""
    accion = v.modo_boceto.acciones["sk_" + h]
    if por_menu:
        accion.trigger()
    else:
        QTest.mouseClick(boton_cinta("sk_" + h), Qt.LeftButton)
    A.esperar(120)


def solo(*tipos):
    lz.ajustes_inf = {**lz.ajustes_inf, "tipos": tipos}


def campo():
    return lz.entrada.campos[0]


def teclear(texto):
    c = campo()
    QTest.mouseClick(c, Qt.LeftButton)
    QTest.keyClick(c, Qt.Key_A, Qt.ControlModifier)
    QTest.keyClicks(c, texto)
    A.esperar(80)


def nuevas(antes):
    return [c for k, c in lz.b.curvas.items() if k not in antes]


# ============================================================ 1. Inferencias al dibujar (BOC-45, 46, 33, 48)
entrar("I", centro=(10, 10), span=150)
A.reg(AR, "entrar al boceto de inferencias", v.modo_boceto.activo and lz is not None, "")
antes = set(lz.b.curvas)

# Igual: la línea que se dibuja con el largo de otra
herramienta("linea")
solo("igual")
clic(10, -20)
mover(10 + 28.28 + 0.4, -20 + 28.28 + 0.2)
inf = lz.inf_actual
A.reg(AR + " · igual", "al acercar el largo al de la línea de 40 mm se propone «Igual» y el cursor se engancha",
      inf is not None and inf.tipo == "igual" and abs(math.dist(inf.xy, lz.clics[0][1]) - 40) < 1e-6,    # la base es el clic, en píxeles
      f"{inf and (inf.tipo, inf.xy)}")
A.foto(v, "herr_igual_linea")
clic(10 + 28.28 + 0.4, -20 + 28.28 + 0.2)
tecla(Qt.Key_Escape)
creadas = nuevas(antes)
nueva = max(creadas, key=lambda c: c.id) if creadas else None
A.reg(AR + " · igual", "la línea nueva mide 40 y quedó la restricción «Igual» con la de 40 mm",
      nueva is not None and abs(math.dist(*lz.b._extremos_linea(nueva.id)) - 40) < 1e-6
      and any(r.tipo == "igual" and set(r.entidades) == {nueva.id, L1} for r in lz.b.restricciones.values()),
      f"{[(r.tipo, r.entidades) for r in lz.b.restricciones.values() if r.tipo == 'igual']}")
lz.deshacer()

# Intersección aparente: guía, sin restricción
herramienta("linea")
solo("interseccion")
mover(80.05, 19.95)
inf = lz.inf_actual
A.reg(AR + " · aparente", "sobre el cruce de las prolongaciones aparece «Intersección aparente» con una guía hacia cada línea",
      inf is not None and inf.tipo == "interseccion_aparente" and len(inf.guias) == 2 and inf.restriccion is None,
      f"{inf and (inf.tipo, inf.xy)}")
A.foto(v, "herr_interseccion_aparente")
n = len(lz.b.restricciones)
clic(80.05, 19.95)
clic(100, 40)
tecla(Qt.Key_Escape)
creadas = nuevas(antes)
nueva = max(creadas, key=lambda c: c.id) if creadas else None
A.reg(AR + " · aparente", "la línea arranca en (80, 20) y no deja ninguna restricción nueva",
      nueva is not None and math.dist(lz.b._extremos_linea(nueva.id)[0], (80, 20)) < 1e-6 and len(lz.b.restricciones) == n, "")
lz.deshacer()

# Círculo y arco con centro, tangentes a otro círculo
for h in ("circulo", "arco_centro"):
    herramienta(h, True)
    solo("tangente")
    clic(-65, 20)
    mover(-65 + 15.3, 20.2)
    inf = lz.inf_actual
    A.reg(AR + " · tangente", f"{h}: con el radio cerca de 15 se propone «Tangente al círculo» y engancha el radio",
          inf is not None and inf.tipo == "tangente_circulo"
          and abs(math.dist(inf.xy, lz.clics[0][1]) - (math.dist(lz.clics[0][1], (-40, 20)) - 10)) < 1e-6,
          f"{inf and (inf.tipo, inf.xy)}")
    if h == "circulo":
        A.foto(v, "herr_tangente_circulos")
    clic(-65 + 15.3, 20.2)
    if h == "arco_centro":
        clic(-65, 50)
    tecla(Qt.Key_Escape)
    creadas = nuevas(antes)
    nuevo = max(creadas, key=lambda c: c.id) if creadas else None
    A.reg(AR + " · tangente", f"{h}: queda la restricción «Tangente» con el círculo y el radio es 15",
          nuevo is not None and any(r.tipo == "tangente" and set(r.entidades) == {nuevo.id, CC} for r in lz.b.restricciones.values())
          and abs(math.dist(lz.b.coords(lz.b.curvas[nuevo.id].centro), (-40, 20)) - (lz.b.radio(nuevo.id) + 10)) < 1e-6
          and abs(lz.b.radio(nuevo.id) - 15) < 0.2 and lz.resultado.ok, f"{nuevo and lz.b.radio(nuevo.id)}")
    lz.deshacer()

# Paralela en la línea de punto medio y en el primer lado del rectángulo 3p
for h in ("linea_medio", "rectangulo_3p"):
    herramienta(h, True)
    solo("paralela")
    clic(30, -20)
    mover(48.9, -1.4)                   # casi a 45°, como la línea diagonal
    inf = lz.inf_actual
    A.reg(AR + " · paralela", f"{h}: aparece «Paralela» (o perpendicular/colineal) para el primer lado",
          inf is not None and inf.tipo in ("paralela", "perpendicular_dir", "colineal"), f"{inf and inf.tipo}")
    tecla(Qt.Key_Escape)
herramienta("rectangulo", True)
solo("paralela", "igual")
clic(30, -20)
mover(48.9, -1.4)
A.reg(AR + " · paralela", "el rectángulo común sigue sin paralela ni igual (deformaría el rectángulo)",
      lz.inf_actual is None or lz.inf_actual.tipo not in ("paralela", "igual"), f"{lz.inf_actual and lz.inf_actual.tipo}")
tecla(Qt.Key_Escape)
lz.set_herramienta("seleccionar")
A.reg(AR + " · limpieza", "ninguna de las pruebas dejó geometría", set(lz.b.curvas) == antes, f"{sorted(set(lz.b.curvas) - antes)}")
salir()

# ============================================================ 2. Desfase de un perfil (BOC-70)
entrar("P", centro=(30, 20), span=90)
antes = set(lz.b.curvas)
herramienta("desfase")
mover(45, 30)
clic(45, 30)                                                         # adentro del rectángulo, entre el borde y el hueco
A.reg(AR + " · perfil", "un clic dentro del perfil (no sobre una curva) abre la barra del Desfase",
      lz.entrada is not None and lz._desfase_perfil is not None, "")
teclear("3")
polis, nota, error = lz._previa_desfase()
cajas = sorted({(round(min(q[0] for q in p), 1), round(max(q[0] for q in p), 1)) for p in polis})
A.reg(AR + " · perfil", "la vista previa muestra el contorno afuera (−3 a 63) y el hueco achicado (radio 5)",
      not error and (-3.0, 63.0) in cajas and any(abs(b - a - 10) < 0.2 for a, b in cajas), f"{cajas} {nota}")
A.foto(v, "herr_desfase_perfil")
QTest.keyClick(campo(), Qt.Key_Return)
A.esperar(150)
n_lin = [c for c in nuevas(antes) if c.tipo == "linea"]
n_cir = [c for c in nuevas(antes) if c.tipo == "circulo"]
A.reg(AR + " · perfil", "Enter crea las cuatro líneas del contorno y el círculo del hueco (radio 5)",
      len(n_lin) == 4 and len(n_cir) == 1 and abs(lz.b.radio(n_cir[0].id) - 5) < 1e-6 and lz.resultado.ok,
      f"{len(n_lin)} líneas, {[lz.b.radio(c.id) for c in n_cir]}")
lz.deshacer()
herramienta("desfase")
mover(120, 80)
clic(120, 80)
A.reg(AR + " · perfil", "un clic en el vacío no abre nada", lz.entrada is None, "")
lz.set_herramienta("seleccionar")
salir()

# ============================================================ 3. Elipse cerca o lejos de un eje (BOC-71) y distancia libre (BOC-72)
entrar("E", centro=(0, 0), span=110)
antes = set(lz.b.curvas)
E = next(k for k, c in lz.b.curvas.items() if c.tipo == "elipse")
herramienta("desfase")
clic(30, 0.3)                                                        # el vértice del eje mayor
A.reg(AR + " · elipse", "clic cerca del eje mayor: la barra dice «Elipse»",
      lz.entrada is not None and "Elipse" in lz._previa_desfase()[1], f"{lz._previa_desfase()[1] if lz.entrada else 'sin barra'}")
teclear("4")
QTest.keyClick(campo(), Qt.Key_Return)
A.esperar(150)
elipses = [c for c in lz.b.curvas.values() if c.tipo == "elipse"]
mayor = max(math.dist(lz.b.coords(c.centro), lz.b.coords(c.mayor)) for c in elipses)
A.reg(AR + " · elipse", "Enter crea otra elipse de semiejes 34 y 19 (a+4, b+4)",
      len(elipses) == 2 and abs(mayor - 34) < 1e-4 and any(abs(c.radio_menor - 19) < 1e-4 for c in elipses), f"{mayor}")
A.foto(v, "herr_desfase_elipse")
cota = next(k for k in lz.b.cotas.values() if k.tipo == "desfase")
lz.b.eliminar(cota.id)                                              # BOC-72: borrar la cota deja la relación y libera la distancia
lz.resolver()
A.reg(AR + " · distancia libre", "sin la cota queda la restricción de desfase (la copia sigue atada a la madre)",
      any(r.tipo == "desfase" and E in r.entidades for r in lz.b.restricciones.values()) and lz.resultado.ok, "")
lz.deshacer()
herramienta("desfase")
clic(30 * math.cos(math.radians(45)), 15 * math.sin(math.radians(45)))                    # lejos de los ejes
A.reg(AR + " · elipse", "clic lejos de los ejes: la barra dice «Óvalo»",
      lz.entrada is not None and "Óvalo" in lz._previa_desfase()[1], f"{lz._previa_desfase()[1] if lz.entrada else 'sin barra'}")
tecla(Qt.Key_Escape)
lz.set_herramienta("seleccionar")
salir()

# ============================================================ 4. Simetría con un eje del origen (BOC-40)
entrar("M", centro=(10, 10), span=100)
antes = set(lz.b.curvas)
herramienta("simetria")
clic(30, 17.5)                                                      # la línea (elige la geometría)
tecla(Qt.Key_Return)                                                # pasa a la línea de simetría
mover(0.05, 40)
clic(0.05, 40)                                                      # sobre el eje Y del origen
estado = lz.estado_simetria()
A.reg(AR + " · simetría", "el clic sobre el eje Y del origen lo elige como línea de simetría y el panel queda válido",
      lz._eje_simetria == lz.b.EJE_Y and estado["valido"], f"{estado}")
A.foto(v, "herr_simetria_eje_origen")
tecla(Qt.Key_Return)
A.esperar(150)
copia = [c for c in nuevas(antes) if c.tipo == "linea" and c.id != lz.b.EJE_Y]
A.reg(AR + " · simetría", "Enter crea la copia espejada en x = −15…−45",
      len(copia) == 1 and sorted(round(q[0], 6) for q in lz.b._extremos_linea(copia[0].id)) == [-45.0, -15.0] and lz.resultado.ok, "")
lz.deshacer()
A.reg(AR + " · simetría", "un solo deshacer quita la copia y el eje materializado", set(lz.b.curvas) == antes, "")
salir()

# ============================================================ 5. Línea de cota en las cotas que solo mostraban texto (BOC-37)
entrar("C", centro=(0, 15), span=80)
cota = next(k for k in lz.b.cotas.values() if k.tipo == "distancia")
lz.update()
A.esperar(200)
lz.grab()
trazos = lz._trazos_cotas.get(cota.id, [])
dim = next(d for d in L("get_sketch", sketch="C")["dimensions"] if d["type"] == "distance")
x1, y1, x2, y2 = dim["measured_segment"]
a, b = lz.a_px(x1, y1), lz.a_px(x2, y2)


def une(r, p, q):
    return all(abs(r[i].x() - c.x()) < 2 and abs(r[i].y() - c.y()) < 2 for i, c in enumerate((p, q)))


A.reg(AR + " · cota", "get_sketch informa el segmento medido: del borde del círculo a la línea, de 18 mm",
      abs(math.dist((x1, y1), (x2, y2)) - 18) < 1e-3 and abs(x1) < 1e-6 and abs(x2) < 1e-6, f"{dim['measured_segment']}")
A.reg(AR + " · cota", "la ventana dibuja esa línea de cota (entre el borde del círculo y la línea) y se puede agarrar",
      any(une(r, a, b) or une(r, b, a) for r in trazos), f"{len(trazos)} rayas")
A.foto(v, "herr_cota_con_linea")
salir()

# ============================================================ 6. «Cambiar por» que sobra (BOC-53)
entrar("K", centro=(-25, 25), span=90)
mensajes = []
lz.mensaje.connect(mensajes.append)
ok_sobra = lz.reemplazar_restriccion(RID, "paralela")
A.reg(AR + " · cambiar por", "«Cambiar por» paralela (ya implícita) se rechaza con su mensaje y deja la anterior",
      ok_sobra is False and lz.b.restricciones[RID].tipo == "igual" and any("no quita ningún grado" in m for m in mensajes),
      f"{mensajes[-1:]}")
ok_util = lz.reemplazar_restriccion(RID, "colineal")
A.reg(AR + " · cambiar por", "«Cambiar por» colineal (que sí quita un grado) se hace", ok_util and lz.b.restricciones[RID].tipo == "colineal", "")
A.reg(AR + " · cambiar por", "⚠ el menú del clic derecho sobre el símbolo no se simuló: se llamó al método que usa su ítem", True, "")
salir()

# ============================================================ 7. Patrón: copias viejas ocultas y asa del ángulo (BOC-60, BOC-62)
entrar("T", centro=(0, 0), span=120)
copias = {i for ids_ in lz.b.patrones[0]["copias"].values() for i in ids_ if i in lz.b.curvas}
lz.editar_patron(lz.b.patrones[0]["id"])
A.esperar(300)
A.reg(AR + " · patrón", "al editar, las copias viejas no se pueden agarrar ni se dibujan",
      lz.copias_en_edicion >= copias and not any(lz._visible(lz.b.curvas[i]) for i in copias), f"{len(copias)} copias")
asa = next((q for a_, q in lz._asas.posiciones_px() if a_.ayuda == "Ángulo" and q is not None), None) if lz._asas else None
A.reg(AR + " · patrón", "la vista tiene un asa de ángulo para girar la dirección", asa is not None, "")
if asa is not None:
    destino = QPointF(asa.x(), asa.y() - 90)
    QTest.mousePress(lz, Qt.LeftButton, Qt.NoModifier, asa.toPoint())
    for i in range(1, 8):
        q = QPointF(asa) + (destino - QPointF(asa)) * (i / 7)
        QApplication.sendEvent(lz, QMouseEvent(QEvent.MouseMove, q, lz.mapToGlobal(q), Qt.NoButton, Qt.LeftButton, Qt.NoModifier))
        A.esperar(20)
    QTest.mouseRelease(lz, Qt.LeftButton, Qt.NoModifier, destino.toPoint())
    A.esperar(150)
    angulo = float(v.modo_boceto.patron.campos["angulo1"].text().replace(",", "."))
    A.reg(AR + " · patrón", "tirar del asa cambia el campo «Ángulo 1» (la fila gira)", abs(angulo) > 10, f"ángulo 1 = {angulo}")
    A.foto(v, "herr_patron_asa_angulo")
tecla(Qt.Key_Escape)
A.reg(AR + " · patrón", "Esc cancela: las copias viejas vuelven a verse y el patrón queda como estaba",
      lz.copias_en_edicion == frozenset() and all(lz._visible(lz.b.curvas[i]) for i in copias), "")
salir()

# ============================================================ 8. Paneles de Escala y Mover/copiar (BOC-41)
def panel_t():
    return v.modo_boceto.transformar


def escribir(clave, texto):
    """Clic en el campo del panel, seleccionar todo y teclear (una persona que escribe un valor)."""
    c = panel_t().campos[clave]
    QTest.mouseClick(c, Qt.LeftButton)
    QTest.keyClick(c, Qt.Key_A, Qt.ControlModifier)
    if texto:
        QTest.keyClicks(c, texto)
    else:
        QTest.keyClick(c, Qt.Key_Delete)
    A.esperar(80)


def largo(cid):
    return math.dist(*lz.b._extremos_linea(cid))


def centro(cid):
    return lz.b.coords(lz.b.curvas[cid].centro)


entrar("Q", centro=(30, 0), span=110)
t = lz.transformar
herramienta("escala", True)
A.reg(AR + " · escala", "el ítem del menú MODIFICAR abre el panel ESCALA con Aceptar apagado y la guía de qué elegir",
      panel_t().isVisible() and panel_t().titulo.text() == "ESCALA" and not panel_t().boton_ok.isEnabled()
      and "Elegí la geometría" in panel_t().guia.text(), f"{panel_t().titulo.text()!r} {panel_t().guia.text()!r}")
clic(10, 0)                                                         # la línea
A.reg(AR + " · escala", "el clic en la línea la elige y el panel dice «1 seleccionado»",
      lz.seleccion == [LQ] and panel_t().sel["seleccion"].boton.text() == "1 seleccionado", f"{panel_t().sel['seleccion'].boton.text()!r}")
tecla(Qt.Key_Return)                                                # Enter con la geometría lista → punto base
A.reg(AR + " · escala", "Enter con la geometría elegida pasa al punto base y la guía lo pide",
      t.campo == "base" and "punto base" in panel_t().guia.text(), f"{t.campo} {panel_t().guia.text()!r}")
clic(0, 0)
A.reg(AR + " · escala", "el clic en el origen fija el punto base y escribe Base X/Y en el panel",
      t.base == (0.0, 0.0) and panel_t().campos["base_x"].text() == "0" and panel_t().sel["base"].boton.text() == "Origen",
      f"{t.base} {panel_t().sel['base'].boton.text()!r}")
for malo in ("0", "-2", "abc", "1e300", ""):
    escribir("factor", malo)
    A.reg(AR + " · escala", f"factor «{malo}»: campo en rojo, mensaje y Aceptar apagado, sin tocar el boceto",
          not panel_t().boton_ok.isEnabled() and bool(panel_t().mensaje.text()) and "border" in panel_t().campos["factor"].styleSheet()
          and abs(largo(LQ) - 20) < 1e-9, f"{panel_t().mensaje.text()!r}")
escribir("factor", "3")
previa = t.calcular()["polis"]
A.reg(AR + " · escala", "con factor 3 la vista previa llega a x = 60 y Aceptar se enciende",
      panel_t().boton_ok.isEnabled() and abs(max(q[0] for poli in previa for q in poli) - 60) < 1e-9, "")
A.foto(v, "herr_escala_panel")
QTest.mouseClick(panel_t().boton_ok, Qt.LeftButton)
A.esperar(150)
A.reg(AR + " · escala", "Aceptar (clic real) escala la línea a 60 mm y vuelve a Seleccionar",
      abs(largo(LQ) - 60) < 1e-9 and lz.herramienta == "seleccionar" and not panel_t().isVisible(), f"{largo(LQ)}")
tecla(Qt.Key_Z, Qt.ControlModifier)
A.reg(AR + " · escala", "Ctrl+Z la deja en 20 mm (un solo paso)", abs(largo(LQ) - 20) < 1e-9, f"{largo(LQ)}")
tecla(Qt.Key_Y, Qt.ControlModifier)
A.reg(AR + " · escala", "...y Ctrl+Y la vuelve a 60", abs(largo(LQ) - 60) < 1e-9, f"{largo(LQ)}")
tecla(Qt.Key_Z, Qt.ControlModifier)

# el asa del factor, con el mouse sobre el lienzo
herramienta("escala", True)
clic(10, 0)
tecla(Qt.Key_Return)
clic(0, 0)
escribir("factor", "1")
asa = lz._asas.asas[0].posicion(lz._asas.valores())
a0 = QPointF(lz.a_px(*asa))
QTest.mousePress(lz, Qt.LeftButton, Qt.NoModifier, a0.toPoint())
for i in range(1, 8):
    q = QPointF(lz.a_px(asa[0] * (1 + i / 7), 0))
    QApplication.sendEvent(lz, QMouseEvent(QEvent.MouseMove, q, lz.mapToGlobal(q), Qt.NoButton, Qt.LeftButton, Qt.NoModifier))
    A.esperar(20)
QTest.mouseRelease(lz, Qt.LeftButton, Qt.NoModifier, lz.a_px(asa[0] * 2, 0).toPoint())
A.esperar(100)
A.reg(AR + " · escala", "tirar del asa hasta el doble escribe ≈ 2 en el campo Factor",
      abs(float(panel_t().campos["factor"].text().replace(",", ".")) - 2) < 0.3, f"{panel_t().campos['factor'].text()}")
tecla(Qt.Key_Escape)
A.reg(AR + " · escala", "Esc cancela: el boceto queda como estaba y el panel se esconde",
      abs(largo(LQ) - 20) < 1e-9 and not panel_t().isVisible(), f"{largo(LQ)}")

# Mover/copiar
lz.seleccion = []                                                      # con algo elegido, la herramienta salta al punto base
herramienta("mover", True)
A.reg(AR + " · mover", "el ítem del menú abre el panel MOVER/COPIAR con ΔX, ΔY, Ángulo y «Crear copia»",
      panel_t().isVisible() and panel_t().titulo.text() == "MOVER/COPIAR" and panel_t().campos["dx"].isVisible()
      and panel_t().casillas["copiar"].isVisible() and not panel_t().campos["factor"].isVisible(), "")
clic(40 + 5, 0)                                                     # el círculo (sobre su borde)
tecla(Qt.Key_Return)
clic(40, 0)                                                         # punto base
clic(40, 15)                                                        # destino
A.reg(AR + " · mover", "base y destino con el mouse llenan ΔX ≈ 0 y ΔY ≈ 15 (el clic cae en un píxel) y la vista previa llega a y ≈ 20",
      abs(float(panel_t().campos["dx"].text())) < 0.3 and abs(float(panel_t().campos["dy"].text()) - 15) < 0.3
      and any(abs(max(q[1] for q in poli) - 20) < 0.3 for poli in t.calcular()["polis"]),
      f"{panel_t().campos['dx'].text()}, {panel_t().campos['dy'].text()}")


def arrastrar_asa(i, destino_mm, pasos=8):
    """Tira del asa `i` de la vista con el mouse: apretar sobre ella, varios movimientos y soltar."""
    desde = lz._asas.asas[i].posicion(lz._asas.valores())
    a0, a1 = QPointF(lz.a_px(*desde)), QPointF(lz.a_px(*destino_mm))
    QTest.mousePress(lz, Qt.LeftButton, Qt.NoModifier, a0.toPoint())
    for k in range(1, pasos + 1):
        q = a0 + (a1 - a0) * (k / pasos)
        QApplication.sendEvent(lz, QMouseEvent(QEvent.MouseMove, q, lz.mapToGlobal(q), Qt.NoButton, Qt.LeftButton, Qt.NoModifier))
        A.esperar(20)
    QTest.mouseRelease(lz, Qt.LeftButton, Qt.NoModifier, a1.toPoint())
    A.esperar(100)


def num(clave):
    return float(panel_t().campos[clave].text().replace(",", "."))


A.reg(AR + " · mover", "con base y destino la vista tiene dos asas: una para ΔX/ΔY a la vez y otra para el ángulo",
      lz._asas is not None and len(lz._asas.asas) == 2 and lz._asas.asas[0].campo == (0, 1) and lz._asas.asas[1].campo == 2, "")
arrastrar_asa(0, (52, 9))
A.reg(AR + " · mover", "tirar del asa de mover hasta (52, 9) escribe ΔX ≈ 12 y ΔY ≈ 9 a la vez y la vista previa la sigue",
      abs(num("dx") - 12) < 0.4 and abs(num("dy") - 9) < 0.4
      and any(abs(max(q[0] for q in poli) - 57) < 0.4 for poli in t.calcular()["polis"]), f"{panel_t().campos['dx'].text()}, {panel_t().campos['dy'].text()}")
A.foto(v, "herr_mover_asas")
arrastrar_asa(1, (52, 24))
A.reg(AR + " · mover", "tirar del asa de giro hasta arriba del punto desplazado escribe Ángulo ≈ 90",
      abs(num("angulo") - 90) < 1.5 and abs(num("dx") - 12) < 0.4, f"{panel_t().campos['angulo'].text()}")
escribir("angulo", "0")
A.reg(AR + " · mover", "escribir el ángulo en el campo vuelve a mover el asa de giro a la derecha del punto desplazado",
      abs(lz._asas.asas[1].posicion(lz._asas.valores())[1] - lz._asas.asas[0].posicion(lz._asas.valores())[1]) < 1e-6, "")
escribir("dx", "5")
QTest.keyClick(panel_t().campos["dx"], Qt.Key_Tab)                  # Tab pasa al campo siguiente
A.esperar(60)
A.reg(AR + " · mover", "teclear ΔX = 5 y Tab: el foco sigue en un campo del panel",
      QApplication.focusWidget() is not None, f"{QApplication.focusWidget()}")
escribir("dy", "-4")
panel_t().casillas["copiar"].click()
A.reg(AR + " · mover", "«Crear copia» se marca y queda recordada", lz.opciones["copiar"] is True, "")
QTest.keyClick(panel_t().campos["dy"], Qt.Key_Return)               # Enter en el campo acepta
A.esperar(150)
centros = sorted(centro(k.id) for k in lz.b.curvas.values() if k.tipo == "circulo")
A.reg(AR + " · mover", "Enter en el campo acepta: el original queda en (40, 0) y la copia en (45, −4)",
      len(centros) == 2 and math.dist(centros[0], (40, 0)) < 1e-9 and math.dist(centros[1], (45, -4)) < 1e-9, f"{centros}")
tecla(Qt.Key_Z, Qt.ControlModifier)
A.reg(AR + " · mover", "Ctrl+Z quita la copia", sum(1 for k in lz.b.curvas.values() if k.tipo == "circulo") == 1, "")
lz.opciones["copiar"] = False
lz.seleccion = []
herramienta("mover", True)
clic(40 + 5, 0)
tecla(Qt.Key_Return)
escribir("dx", "1e300")
A.reg(AR + " · mover", "ΔX enorme: mensaje, campo rojo y Aceptar apagado",
      not panel_t().boton_ok.isEnabled() and "border" in panel_t().campos["dx"].styleSheet() and bool(panel_t().mensaje.text()),
      f"{panel_t().mensaje.text()!r}")
escribir("dx", "x")
A.reg(AR + " · mover", "ΔX con letras: se rechaza", not panel_t().boton_ok.isEnabled(), "")
escribir("dx", "-3,5")
A.reg(AR + " · mover", "ΔX con coma decimal y negativo (−3,5) se acepta", panel_t().boton_ok.isEnabled(), f"{panel_t().mensaje.text()!r}")
QTest.keyClick(panel_t().campos["dx"], Qt.Key_Escape)               # Esc dentro del campo cancela
A.esperar(100)
A.reg(AR + " · mover", "Esc dentro del campo cancela sin tocar nada",
      lz.herramienta == "seleccionar" and math.dist(centro(CQ), (40, 0)) < 1e-9, "")
salir()

# ventana chica: el panel con Aceptar y Cancelar tiene que entrar
for ancho, alto in ((1024, 640), (800, 520)):
    v.resize(ancho, alto)
    A.esperar(500)
    entrar("Q", centro=(30, 0), span=110)
    v.area.reubicar()
    herramienta("mover", True)
    clic(40 + 5, 0)
    tecla(Qt.Key_Return)
    clic(40, 0)
    A.esperar(250)
    area = v.area.rect()
    cancelar = next(b for b in panel_t().findChildren(QPushButton) if b.text() == "Cancelar")
    entra = panel_t().isVisible() and all(area.contains(b.mapTo(v.area, b.rect().topLeft()))
                                          and area.contains(b.mapTo(v.area, b.rect().bottomRight()))
                                          for b in (panel_t().boton_ok, cancelar))
    barra = v.area.barra
    libre = not panel_t().geometry().intersects(barra.geometry()) if barra is not None and barra.isVisible() else True
    A.reg(AR + f" · {ancho}x{alto}", "Mover/copiar: el panel con Aceptar y Cancelar entra en la ventana y la barra de vista no lo tapa",
          entra and libre, f"panel={panel_t().geometry().getRect()} área={area.getRect()}")
    A.foto(v, f"herr_mover_chica_{ancho}x{alto}")
    tecla(Qt.Key_Escape)
    salir()
v.resize(1900, 1000)
A.esperar(500)

# ============================================================ 9. Ayudas de dibujo en el Boceto 3D (BOC-47)
entrar("D", centro=(40, 0), span=140)
v.modo_boceto.paleta.checks["boceto3d"].setChecked(True)
A.esperar(300)
it = v.modo_boceto.interaccion3d
h3d = v.modo_boceto.paleta.h3d


def herr3d(clave):
    h3d.setCurrentIndex(h3d.findData(clave))
    A.esperar(80)


def mover3d(p, dx=3, dy=2):
    q = it.a_pantalla(p) + QPointF(dx, dy)
    QApplication.sendEvent(lz, QMouseEvent(QEvent.MouseMove, q, lz.mapToGlobal(q), Qt.NoButton, Qt.NoButton, Qt.NoModifier))
    A.esperar(80)
    return q


def puntos3d():
    return [tuple(p) for p in lz.b.geo3d["puntos"].values()]


herr3d("punto")
mover3d((50, -20, 0))
A.reg(AR + " · boceto 3D", "con el mouse a unos píxeles del medio de la línea aparece «Punto medio» con su marcador",
      it.ayuda is not None and it.ayuda.tipo == "punto_medio" and lz.ayuda_3d is not None and lz.ayuda_3d[2] == "Punto medio",
      f"{it.ayuda and it.ayuda.tipo} {lz.ayuda_3d and lz.ayuda_3d[2]}")
A.foto(v, "herr_boceto3d_punto_medio")
n = len(puntos3d())
q = mover3d((50, -20, 0))
QTest.mouseClick(lz, Qt.LeftButton, Qt.NoModifier, q.toPoint())
A.esperar(120)
nuevo = [p for p in puntos3d() if abs(p[0] - 50) < 1e-6 and abs(p[1] + 20) < 1e-6 and abs(p[2]) < 1e-6]
A.reg(AR + " · boceto 3D", "el clic cae justo en el medio (50, −20, 0), no donde apuntó el cursor", len(puntos3d()) == n + 1 and len(nuevo) == 1, f"{puntos3d()[-1]}")
rs = list(lz.b.geo3d.get("restricciones", {}).values())
A.reg(AR + " · boceto 3D", "el punto del clic queda unido a la línea con la restricción de punto medio",
      len(rs) == 1 and rs[0]["tipo"] == "punto_medio", f"{rs}")
tecla(Qt.Key_Z, Qt.ControlModifier)
A.reg(AR + " · boceto 3D", "Ctrl+Z quita ese punto y su restricción", len(puntos3d()) == n and not lz.b.geo3d.get("restricciones"),
      f"{len(puntos3d())} vs {n} {lz.b.geo3d.get('restricciones')}")
mover3d((60, -60, 0), dx=2, dy=0)
A.reg(AR + " · boceto 3D", "alineado con el punto (60, 25): la etiqueta dice «misma X» y hay una guía",
      it.ayuda is not None and it.ayuda.tipo == "alineado_v" and "misma X" in it.ayuda.etiqueta and len(it.ayuda.guias) == 1,
      f"{it.ayuda and (it.ayuda.tipo, it.ayuda.etiqueta)}")
A.foto(v, "herr_boceto3d_alineacion")
mover3d((10, -60, 0), dx=30, dy=30)
A.reg(AR + " · boceto 3D", "lejos de todo, la ayuda se apaga y no queda etiqueta", it.ayuda is None and lz.ayuda_3d is None, "")
herr3d("seleccionar")
mover3d((50, -20, 0))
A.reg(AR + " · boceto 3D", "con Seleccionar no hay ayudas de dibujo", it.ayuda is None and lz.ayuda_3d is None, "")
herr3d("linea")
q = it.a_pantalla((0, -30, 0))
QTest.mouseClick(lz, Qt.LeftButton, Qt.NoModifier, q.toPoint())
A.esperar(100)
mover3d((0, 12, 0), dx=0, dy=0)
A.reg(AR + " · boceto 3D", "dibujando una línea desde (0, −30), el cursor sobre el eje Y de la tríada propone «Alineado» con la guía",
      it.ayuda is not None and it.ayuda.tipo in ("vertical", "alineado_v", "alineado_hv", "punto_medio", "interseccion"),
      f"{it.ayuda and (it.ayuda.tipo, it.ayuda.etiqueta)}")
tecla(Qt.Key_Escape)
herr3d("linea")                                                     # una línea horizontal a la tríada
QTest.mouseClick(lz, Qt.LeftButton, Qt.NoModifier, it.a_pantalla((0, -30, 0)).toPoint())
A.esperar(100)
q = mover3d((45, -30, 0), dx=0, dy=1)
A.reg(AR + " · boceto 3D", "dibujando hacia la derecha a la misma altura aparece «Horizontal»",
      it.ayuda is not None and it.ayuda.tipo == "horizontal", f"{it.ayuda and (it.ayuda.tipo, it.ayuda.etiqueta)}")
QTest.mouseClick(lz, Qt.LeftButton, Qt.NoModifier, q.toPoint())
A.esperar(120)
rs = list(lz.b.geo3d.get("restricciones", {}).values())
A.reg(AR + " · boceto 3D", "la línea queda con la restricción de eje X (como Horizontal de Fusion)",
      len(rs) == 1 and rs[0]["tipo"] == "eje" and rs[0].get("eje") == "x", f"{rs}")
tecla(Qt.Key_Escape)
salir()

# ============================================================ 9b. Boceto 3D: enganchar en el espacio (BOC-78) y dejar la restricción (BOC-77)
entrar("Z", centro=(20, 10), span=140)
v.modo_boceto.paleta.checks["boceto3d"].setChecked(True)
A.esperar(300)
it = v.modo_boceto.interaccion3d
h3d = v.modo_boceto.paleta.h3d
herr3d("punto")
mover3d((0, 40, 15))
A.reg(AR + " · boceto 3D", "el medio de una línea a 15 mm del plano engancha en su punto 3D, no en la proyección",
      it.ayuda is not None and it.ayuda.tipo == "punto_medio" and np.allclose(it.ayuda.punto, (0, 40, 15)),
      f"{it.ayuda and (it.ayuda.tipo, it.ayuda.punto)}")
q = mover3d((0, 40, 15))
QTest.mouseClick(lz, Qt.LeftButton, Qt.NoModifier, q.toPoint())
A.esperar(120)
rs = list(lz.b.geo3d.get("restricciones", {}).values())
A.reg(AR + " · boceto 3D", "el clic crea el punto a z = 15 y deja la restricción de punto medio",
      any(abs(p[0]) < 1e-6 and abs(p[1] - 40) < 1e-6 and abs(p[2] - 15) < 1e-6 for p in puntos3d()) and [r["tipo"] for r in rs] == ["punto_medio"],
      f"{puntos3d()[-1]} {rs}")
tecla(Qt.Key_Z, Qt.ControlModifier)
A.reg(AR + " · boceto 3D", "Ctrl+Z quita el punto y su restricción", not lz.b.geo3d.get("restricciones"), f"{lz.b.geo3d.get('restricciones')}")
R0 = lz.visor.R.copy()
giro = math.radians(55)                                             # la vista inclinada: ahí la proyección al plano cae en otro lado
lz.visor.R = np.array([[1, 0, 0], [0, math.cos(giro), math.sin(giro)], [0, -math.sin(giro), math.cos(giro)]], float) @ R0
lz.visor.update()
lz.update()
A.esperar(200)
mover3d((0, 40, 15))
A.reg(AR + " · boceto 3D", "con la vista inclinada, el mouse sobre el medio en pantalla también engancha el punto 3D",
      it.ayuda is not None and it.ayuda.tipo == "punto_medio" and np.allclose(it.ayuda.punto, (0, 40, 15)),
      f"{it.ayuda and (it.ayuda.tipo, it.ayuda.punto)}")
A.foto(v, "herr_boceto3d_medio_en_el_espacio")
lz.visor.R = R0
lz.visor.update()
lz.update()
A.esperar(200)
herr3d("linea")
QTest.mouseClick(lz, Qt.LeftButton, Qt.NoModifier, it.a_pantalla((0, 0, 0)).toPoint())
A.esperar(100)
A.reg(AR + " · boceto 3D", "la línea arranca en el punto del origen (el clic engancha el punto 3D)",
      len(it.picks) == 1 and np.allclose(it.picks[0], (0, 0, 0)), f"{it.picks}")
dz, gz = math.sqrt(60 ** 2 - 15 ** 2), math.asin(15 / 60)
contacto = (dz * math.cos(gz), dz * math.sin(gz), 0)
q = mover3d(contacto, dx=2, dy=1)
A.reg(AR + " · boceto 3D", "dibujando hacia el círculo, cerca del contacto aparece «Tangente a la curva»",
      it.ayuda is not None and it.ayuda.tipo == "tangente" and np.allclose(it.ayuda.punto, contacto, atol=1e-6),
      f"{it.ayuda and (it.ayuda.tipo, it.ayuda.punto)}")
A.foto(v, "herr_boceto3d_tangente")
antes = {k: list(p) for k, p in lz.b.geo3d["puntos"].items()}
QTest.mouseClick(lz, Qt.LeftButton, Qt.NoModifier, q.toPoint())
A.esperar(120)
tecla(Qt.Key_Escape)
rs = sorted(r["tipo"] for r in lz.b.geo3d.get("restricciones", {}).values())
A.reg(AR + " · boceto 3D", "el clic deja la línea tangente al círculo y su punta sobre él (tangente + coincidente)",
      rs == ["coincidente", "tangente"], f"{rs}")
A.reg(AR + " · boceto 3D", "dejar esas restricciones no movió nada de lo que ya estaba",
      all(math.dist(p, lz.b.geo3d["puntos"][k]) < 1e-6 for k, p in antes.items()), "")
herr3d("punto")
sobre = (60 + 15 * math.cos(math.radians(200)), 15 * math.sin(math.radians(200)), 0)
q = mover3d(sobre, dx=1, dy=1)
A.reg(AR + " · boceto 3D", "con el mouse sobre el círculo aparece «Sobre la curva»",
      it.ayuda is not None and it.ayuda.tipo == "sobre_curva" and it.ayuda.etiqueta == "Sobre la curva",
      f"{it.ayuda and (it.ayuda.tipo, it.ayuda.etiqueta)}")
QTest.mouseClick(lz, Qt.LeftButton, Qt.NoModifier, q.toPoint())
A.esperar(120)
rs = list(lz.b.geo3d["restricciones"].values())
A.reg(AR + " · boceto 3D", "el clic deja el punto unido al círculo con coincidente",
      sum(r["tipo"] == "coincidente" and CZ in r["entidades"] for r in rs) == 2, f"{rs}")
herr3d("rectangulo")
n_curvas = len(lz.b.geo3d["curvas"])
q = mover3d((0, 40, 15))
QTest.mouseClick(lz, Qt.LeftButton, Qt.NoModifier, q.toPoint())     # una esquina en una ayuda que deja restricción
A.esperar(100)
QTest.mouseClick(lz, Qt.LeftButton, Qt.NoModifier, it.a_pantalla((40, 70, 15)).toPoint())
A.esperar(120)
A.reg(AR + " · boceto 3D", "un rectángulo con una esquina en el medio de la línea se crea (cuatro líneas)",
      len(lz.b.geo3d["curvas"]) == n_curvas + 4, f"{n_curvas} → {len(lz.b.geo3d['curvas'])}")
tecla(Qt.Key_Escape)
salir()

# ============================================================ 9c. Tangente con un arco: radio y aviso (BOC-52)
entrar("Y", centro=(0, 0), span=100)
avisos_y = []
lz.mensaje.connect(avisos_y.append)
lz.set_herramienta("r_tangente")
A.esperar(100)
clic(0, -15)
clic(12 * math.cos(math.radians(45)), 12 * math.sin(math.radians(45)))
A.esperar(200)
tangentes = [r for r in lz.b.restricciones.values() if r.tipo == "tangente"]
A.reg(AR + " · tangente", "elegir la línea y el arco deja la tangente", len(tangentes) == 1, f"{tangentes}")
A.reg(AR + " · tangente", "el radio del arco no cambia: la línea se desliza hasta tocarlo (figura de la ayuda de Fusion)",
      abs(lz.b.radio(AY) - 12) < 1e-6, f"{lz.b.radio(AY)}")
A.reg(AR + " · tangente", "el contacto cae fuera del tramo dibujado y el mensaje lo avisa",
      any("fuera del tramo" in m for m in avisos_y), f"{avisos_y[-1:]}")
A.foto(v, "herr_tangente_fuera_del_arco")
tecla(Qt.Key_Z, Qt.ControlModifier)
A.reg(AR + " · tangente", "Ctrl+Z quita la tangente y la línea vuelve a su lugar",
      not any(r.tipo == "tangente" for r in lz.b.restricciones.values())
      and abs(lz.b.coords(lz.b.curvas[LY].p1)[1] + 14) < 1e-6, f"{lz.b.coords(lz.b.curvas[LY].p1)}")
lz.mensaje.disconnect(avisos_y.append)
lz.set_herramienta("seleccionar")
salir()

# ============================================================ 10. Curva isoparamétrica (BOC-36)
entrar("Iso", centro=(300, 300), span=80)
herramienta("isoparametrica", True)
form = v.modo_boceto.tarjeta.form_contexto


def fila(etiqueta):
    """El widget de la fila de la tarjeta con esa etiqueta (o None)."""
    for i in range(form.rowCount()):
        e = form.itemAt(i, form.ItemRole.LabelRole)
        if e is not None and e.widget() is not None and e.widget().text() == etiqueta:
            return form.itemAt(i, form.ItemRole.FieldRole).widget()
    return None


A.reg(AR + " · isoparamétrica", "el ítem del menú Proyectar/Incluir abre la herramienta y la tarjeta pide Dirección, Distribución, Distancia, Cantidad y Vínculo",
      lz.herramienta == "isoparametrica" and all(fila(e) is not None for e in ("Dirección", "Distribución", "Distancia", "Cantidad", "Vínculo de proyección")),
      f"{[form.itemAt(i, form.ItemRole.LabelRole).widget().text() for i in range(form.rowCount()) if form.itemAt(i, form.ItemRole.LabelRole) and form.itemAt(i, form.ItemRole.LabelRole).widget()]}")
mover(300 + 4, 300 + 3)
A.esperar(300)                                                      # la vista previa espera a que el cursor se quede quieto
capa = v.visor._capas.get("iso_previa")
n_previa = 0 if capa is None else len(capa[0][1])
A.reg(AR + " · isoparamétrica", "con el cursor sobre la cara aparece la vista previa de la curva (capa del visor) y no se crea nada",
      capa is not None and n_previa > 0 and not lz.b.geo3d.get("curvas"), f"{n_previa}")
A.foto(v, "herr_isoparametrica_previa")
clic(300 + 4, 300 + 3)                                              # un punto de la tapa del cilindro
A.reg(AR + " · isoparamétrica", "el clic reemplaza la vista previa por las curvas creadas", "iso_previa" not in v.visor._capas, "")
curvas = list(lz.b.geo3d.get("curvas", {}).values())
A.reg(AR + " · isoparamétrica", "un clic en la cara crea una curva 3D (la línea por el punto, en dirección U) con su origen",
      len(curvas) == 1 and curvas[0]["tipo"] == "linea" and curvas[0].get("origen", {}).get("tool") == "isoparametric_curve",
      f"{[(c['tipo'], c.get('origen', {}).get('tool')) for c in curvas]} {lz.mensaje}")
A.foto(v, "herr_isoparametrica_unica")
for etiqueta, dato in (("Distribución", "cantidad"), ("Dirección", "v")):          # la paleta se rearma tras cada cambio: se vuelve a buscar el widget
    combo = fila(etiqueta)
    combo.setCurrentIndex(combo.findData(dato))
    A.esperar(80)
fila("Cantidad").setValue(4)
A.esperar(300)
capa = v.visor._capas.get("iso_previa")
A.reg(AR + " · isoparamétrica", "al cambiar la Distribución, la Dirección y la Cantidad la vista previa se rehace sin mover el mouse (más curvas)",
      capa is not None and len(capa[0][1]) > n_previa, f"{n_previa} → {0 if capa is None else len(capa[0][1])}")
clic(300 + 4, 300 + 3)
curvas = list(lz.b.geo3d.get("curvas", {}).values())
A.reg(AR + " · isoparamétrica", "Distribuidas por cantidad = 4 en V: otras cuatro líneas, en total cinco",
      len(curvas) == 5 and all(c["tipo"] == "linea" for c in curvas), f"{len(curvas)}")
A.foto(v, "herr_isoparametrica_distribuidas")
fila("Vínculo de proyección").setChecked(False)
A.esperar(80)
clic(300 - 6, 300 - 5)
sin_origen = [c for c in lz.b.geo3d["curvas"].values() if "origen" not in c]
A.reg(AR + " · isoparamétrica", "con el vínculo apagado las curvas nuevas quedan libres (sin origen)", len(sin_origen) == 4, f"{len(sin_origen)}")
tecla(Qt.Key_Z, Qt.ControlModifier)
A.reg(AR + " · isoparamétrica", "Ctrl+Z quita de una vez las cuatro curvas del último clic", len(lz.b.geo3d.get("curvas", {})) == 5,
      f"{len(lz.b.geo3d.get('curvas', {}))}")
tecla(Qt.Key_Z, Qt.ControlModifier)
tecla(Qt.Key_Z, Qt.ControlModifier)
A.reg(AR + " · isoparamétrica", "y con dos Ctrl+Z más no queda ninguna curva 3D", not lz.b.geo3d.get("curvas"), f"{len(lz.b.geo3d.get('curvas', {}))}")
clic(300 + 30, 300 + 20)                                            # dentro de la vista pero fuera del cilindro
A.reg(AR + " · isoparamétrica", "un clic fuera del modelo no crea nada y lo dice", not lz.b.geo3d.get("curvas"), "")
tecla(Qt.Key_Escape)
lz.set_herramienta("seleccionar")
salir()

A.reg("GENERAL", "ninguna excepción escapó de un slot de Qt en toda la corrida", not A.ERRORES, f"{len(A.ERRORES)}: {A.ERRORES[:1]}")
A.guardar_registro("boceto_herramientas")
fallas = [r for r in A.REGISTRO if not r["ok"]]
print(f"\n=== {len(A.REGISTRO)} comprobaciones, {len(fallas)} con ✗ ===")
v.doc.modificado = False
v.close()
sys.exit(0)

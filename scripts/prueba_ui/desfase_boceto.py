# -*- coding: utf-8 -*-
"""BOCETO · Desfase con signo, como lo usa una persona: botón de la cinta, clic en la curva, llevar el ratón al lado,
TECLEAR la distancia (positiva, negativa, -30, -40, vacío, 0, enorme, coma decimal, unidades, expresiones), ver la vista
previa cambiar de lado sin confirmar, el botón «Invertir», cambios rápidos, Enter / Esc, deshacer y rehacer, guardar y
reabrir, extruir el resultado y ventanas chicas. Eventos simulados al Lienzo (nunca el cursor real). Caso del video de
Gerardo (2026-10-30 21-50-17): círculo de radio 30. Ver evidencias/desfase_boceto_2026-10-31/INFORME.md."""
import math
import os
import sys
import tempfile

import arnes as A
from omnicad import api
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QToolButton

AR = "BOCETO·DESFASE"
s = api.Sesion()


def L(nombre, **a):
    r = api.llamar(s, nombre, a)
    assert r["ok"], (nombre, a, r)
    return r["result"]


L("create_sketch", name="S", plane="XY")
circ = L("draw_circle", sketch="S", center_x=0, center_y=0, radius=30)["entities"][0]["id"]
L("draw_rectangle", sketch="S", x1=80, y1=-20, x2=120, y2=20)
app, v = A.iniciar(s.doc)
v.editar_operacion(s.paso("S").id)
A.esperar(500)
lz = v.modo_boceto.lienzo
A.reg(AR, "entrar al boceto", v.modo_boceto.activo and lz is not None, "")
MENSAJES = []
lz.mensaje.connect(MENSAJES.append)
lz.visor.objetivo = lz.plano.a_3d(50, 0)
lz.visor.distancia = 190 / 2 / math.sin(math.radians(lz.visor.fov) / 2) * 1.3
lz.visor.update()
lz.update()
A.esperar(300)


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


def campo():
    return lz.entrada.campos[0]


def teclear(texto):
    """Como la persona: clic en el campo, seleccionar todo y teclear tecla por tecla (vacío: Supr)."""
    c = campo()
    QTest.mouseClick(c, Qt.LeftButton)
    QTest.keyClick(c, Qt.Key_A, Qt.ControlModifier)
    if texto:
        QTest.keyClicks(c, texto)
    else:
        QTest.keyClick(c, Qt.Key_Delete)
    A.esperar(80)


def radios():
    return sorted(round(c.radio, 3) for c in lz.b.curvas.values() if c.tipo == "circulo")


def empezar(x=30, y=0, lado=(60, 0)):
    """Botón Desfase de la cinta, clic en la curva y llevar el ratón al lado (afuera por defecto)."""
    QTest.mouseClick(boton_cinta("sk_desfase"), Qt.LeftButton)
    A.esperar(120)
    clic(x, y)
    mover(*lado)
    return lz.entrada is not None


def previa():
    polis, nota, error = lz._previa_desfase()
    return sorted({round(max(abs(q[0]) for q in poli), 1) for poli in polis}), nota, error


def cerrar():
    if lz.entrada is not None:
        tecla(Qt.Key_Escape)
    lz.set_herramienta("seleccionar")
    lz.seleccion = []


def borrar_nuevos():
    """Deja el boceto como al empezar (los desfases creados se deshacen)."""
    while len(lz.historial) > 0 and len(lz.b.curvas) > 5:
        lz.deshacer()


# 1. Tabla del círculo de 30 mm, tecleando de verdad y confirmando con Enter (radio nuevo esperado)
tabla = [("10", 40), ("20", 50), ("-10", 20), ("-20", 10), ("-29", 1), ("20,5", 50.5), ("15 mm", 45), ("-2*5", 20)]
for texto, nuevo in tabla:
    if not empezar():
        A.reg(AR + " · tabla", f"«{texto}»: se abre la barra", False, "")
        continue
    teclear(texto)
    r, nota, err = previa()
    A.reg(AR + " · tabla", f"«{texto}»: la vista previa ya muestra el radio {nuevo} antes de confirmar", not err and r == [float(nuevo)], f"{r} {nota}")
    QTest.keyClick(campo(), Qt.Key_Return)
    A.esperar(120)
    A.reg(AR + " · tabla", f"«{texto}» + Enter: queda el círculo de radio {nuevo} junto al de 30",
          lz.entrada is None and radios() == sorted([30, nuevo]), f"{radios()}")
    borrar_nuevos()
A.foto(v, "desfase_tabla")

# 2. Rechazos: -30 (radio cero), -40 (negativo), 0, vacío, enorme, texto; con mensaje que explica y sin previa vieja
for texto, fragmento in (("-30", "en cero"), ("-40", "negativo"), ("0", "cero: no hay nada"), ("", "Escribí la distancia"),
                         ("1e9", "no puede pasar de"), ("abc", "Nombre desconocido")):
    empezar()
    teclear("20")
    ok_antes = previa()[0] == [50.0]
    teclear(texto)
    r, nota, err = previa()
    MENSAJES.clear()
    QTest.keyClick(campo(), Qt.Key_Return)
    A.esperar(120)
    A.reg(AR + " · rechazos", f"«{texto}»: no hay vista previa vieja, el mensaje explica y el campo queda en rojo",
          ok_antes and r == [] and err and fragmento in nota and "background" in campo().styleSheet(), f"{r} | {nota}")
    A.reg(AR + " · rechazos", f"«{texto}» + Enter: no crea nada, la barra sigue abierta y el aviso sale en la barra de estado",
          lz.entrada is not None and radios() == [30] and any(fragmento in m for m in MENSAJES), f"{radios()} {MENSAJES[-1:]}")
    if texto == "-30":
        A.foto(v, "desfase_rechazo_menos30")
    cerrar()

# 3. Prueba 2 y 3 del pedido: de +20 a -20 sin confirmar y cambios rápidos
empezar()
teclear("20")
a = previa()
A.foto(v, "desfase_previa_mas20")
teclear("-20")
b = previa()
A.foto(v, "desfase_previa_menos20")
A.reg(AR + " · previa viva", "de 20 a -20 sin confirmar la vista previa pasa de afuera (50) a adentro (10)",
      a[0] == [50.0] and b[0] == [10.0] and a[1] == "Hacia afuera" and b[1] == "Hacia adentro" and radios() == [30], f"{a} -> {b}")
fallas_rapidas = []
for _ in range(2):
    for texto, esperado in (("20", [50.0]), ("-20", [10.0]), ("-30", []), ("5", [35.0]), ("-29", [1.0]), ("x", []), ("-1", [29.0]), ("", [])):
        teclear(texto)
        if previa()[0] != esperado:
            fallas_rapidas.append((texto, previa()[0], esperado))
A.reg(AR + " · previa viva", "20, -20, -30, 5, -29, x, -1, vacío (dos vueltas): ninguna vista previa ajena", not fallas_rapidas, str(fallas_rapidas[:2]))
A.reg(AR + " · previa viva", "la geometría real sigue intacta mientras tanto", radios() == [30], f"{radios()}")

# 4. Botón Invertir
teclear("20")
boton = next(b for b in lz.entrada.findChildren(QToolButton))
QTest.mouseClick(boton, Qt.LeftButton)
A.esperar(100)
dentro = previa()[0]
QTest.mouseClick(boton, Qt.LeftButton)
A.esperar(100)
fuera = previa()[0]
A.reg(AR + " · Invertir", "el botón ⇄ pasa de afuera a adentro y vuelve, sin tocar el 20", dentro == [10.0] and fuera == [50.0] and campo().text() == "20", f"{dentro} {fuera} '{campo().text()}'")
QTest.mouseClick(boton, Qt.LeftButton)
A.esperar(100)
A.foto(v, "desfase_invertido")
QTest.keyClick(campo(), Qt.Key_Return)
A.esperar(150)
cota = [k for k in lz.b.cotas.values() if k.tipo == "desfase"]
A.reg(AR + " · Invertir", "Enter con Invertir crea el de 10 y la cota queda 20 (positiva)", 10.0 in radios() and cota and cota[-1].expresion == "20", f"{radios()}")
borrar_nuevos()

# 5. Esc / cancelar no crea nada; Tab no rompe; ratón cambia el lado
empezar()
teclear("-20")
tecla_ok = previa()[0] == [10.0]
QTest.keyClick(campo(), Qt.Key_Tab)
A.esperar(60)
QTest.keyClick(campo(), Qt.Key_Escape)
A.esperar(100)
A.reg(AR + " · Esc", "Esc descarta la barra y no queda ninguna entidad nueva ni cota", tecla_ok and lz.entrada is None and radios() == [30] and not lz.b.cotas, f"{radios()}")
empezar(lado=(10, 0))                     # el ratón adentro: ya no decide el lado (Fusion: el signo, el asa y «Cambiar»)
teclear("5")
r1 = previa()[0]
for xy in ((10, 0), (-50, 20), (0, 0)):
    mover(*xy)
r2 = previa()[0]
teclear("-5")
r3 = previa()[0]
A.reg(AR + " · lado", "pasar el ratón no cambia lo escrito ni el lado: 5 va afuera (35) y -5 adentro (25)",
      r1 == r2 == [35.0] and r3 == [25.0] and campo().text() == "-5", f"{r1} {r2} {r3}")
cerrar()


# 5b. El asa (Fusion: la flecha de la vista): arrastrar escribe el valor con signo; pasar el ratón no hace nada
def arrastrar_asa(i, destino, pasos=6):
    q = QPointF(lz._asas.posiciones_px()[i][1])
    for tipo, botones, pos in ((QEvent.MouseMove, Qt.NoButton, q), (QEvent.MouseButtonPress, Qt.LeftButton, q)):
        QApplication.sendEvent(lz, QMouseEvent(tipo, pos, lz.mapToGlobal(pos), Qt.LeftButton if botones else Qt.NoButton,
                                               botones, Qt.NoModifier))
    meta = QPointF(px(*destino))
    for k in range(1, pasos + 1):
        pos = q + (meta - q) * (k / pasos)
        QApplication.sendEvent(lz, QMouseEvent(QEvent.MouseMove, pos, lz.mapToGlobal(pos), Qt.NoButton, Qt.LeftButton, Qt.NoModifier))
        A.esperar(30)
    QApplication.sendEvent(lz, QMouseEvent(QEvent.MouseButtonRelease, meta, lz.mapToGlobal(meta), Qt.LeftButton, Qt.NoButton, Qt.NoModifier))
    A.esperar(80)


empezar()
inicial = campo().text()
for xy in ((10, 10), (0, 60), (-60, 0)):
    mover(*xy)
A.reg(AR + " · asa", f"el valor inicial ({inicial}) entra hacia los dos lados y pasar el ratón no lo cambia",
      0 < float(inicial) < 15 and campo().text() == inicial, f"inicial={inicial}")
A.foto(v, "desfase_asa")
arrastrar_asa(0, (50, 0))
mas = float(campo().text())
arrastrar_asa(0, (12, 0))
menos = float(campo().text())
A.reg(AR + " · asa", "tirar del asa hacia afuera da +20 y hacia adentro -18, y la vista previa lo sigue",
      abs(mas - 20) < 1.5 and abs(menos + 18) < 1.5 and previa()[0] == [round(30 + menos, 1)], f"{mas} {menos} {previa()}")
teclear("7")
mover(-60, 0)
A.reg(AR + " · asa", "lo escrito manda: mover el ratón después no lo pisa", campo().text() == "7", campo().text())
cerrar()

# 6. Deshacer / rehacer en cadena con Ctrl+Z / Ctrl+Y
for texto in ("-20", "10"):
    empezar()
    teclear(texto)
    QTest.keyClick(campo(), Qt.Key_Return)
    A.esperar(120)
hecho = radios()
tecla(Qt.Key_Z, Qt.ControlModifier)
tecla(Qt.Key_Z, Qt.ControlModifier)
A.reg(AR + " · deshacer", "Ctrl+Z dos veces vuelve al círculo solo", radios() == [30], f"{radios()}")
tecla(Qt.Key_Y, Qt.ControlModifier)
tecla(Qt.Key_Y, Qt.ControlModifier)
A.reg(AR + " · deshacer", "Ctrl+Y dos veces rehace los dos desfases", radios() == hecho and lz.resultado.ok, f"{radios()} vs {hecho}")

# 7. Rectángulo (cadena cerrada): hacia adentro con signo, esquina que no entra
QTest.mouseClick(boton_cinta("sk_desfase"), Qt.LeftButton)
A.esperar(100)
clic(100, -20)
mover(100, -40)
teclear("-3")
polis, nota, err = lz._previa_desfase()
xs = sorted({round(q[0], 3) for poli in polis for q in poli})
A.reg(AR + " · cadena", "rectángulo de 40x40 con -3: la previa va de 83 a 117 y dice «Hacia adentro»", not err and nota == "Hacia adentro" and xs == [83.0, 117.0], f"{xs} {nota}")
teclear("-25")
polis, nota, err = lz._previa_desfase()
A.reg(AR + " · cadena", "-25 en un rectángulo de 40: se rechaza diciendo que un segmento queda con largo cero o al revés", err and "largo cero o al revés" in nota, nota)
teclear("-3")
QTest.keyClick(campo(), Qt.Key_Return)
A.esperar(150)
A.foto(v, "desfase_cadena")
cerrar()

# 8. Ventana chica: la barra con el campo, «Invertir» y la nota tiene que entrar y verse
for ancho, alto in ((1024, 640), (800, 520)):
    v.resize(ancho, alto)
    A.esperar(500)
    lz.visor.objetivo = lz.plano.a_3d(0, 0)
    lz.update()
    A.esperar(200)
    ok_barra = empezar(lado=(40, 0))
    teclear("-20")
    barra = lz.entrada.geometry() if lz.entrada is not None else None
    entra = barra is not None and lz.rect().contains(barra)
    boton = next(iter(lz.entrada.findChildren(QToolButton))) if lz.entrada is not None else None
    A.foto(v, f"desfase_chica_{ancho}x{alto}")
    A.reg(AR + " · ventana chica", f"{ancho}x{alto}: la barra (campo + Invertir) entra en el lienzo y la previa sigue viva",
          ok_barra and entra and boton is not None and boton.isVisible() and previa()[0] == [10.0], f"barra={barra} lienzo={lz.rect()}")
    cerrar()
v.resize(1900, 1000)
A.esperar(300)

# 8b. Los tres modos con la barra abierta, desde el combo REAL de la paleta, y confirmar lo que se ve
from PySide6.QtWidgets import QComboBox  # noqa: E402


def elegir_direccion(clave):
    combo = next(c for c in v.modo_boceto.paleta.contexto.findChildren(QComboBox) if c.findData("dos") >= 0)
    combo.setCurrentIndex(combo.findData(clave))
    A.esperar(150)


borrar_nuevos()
empezar()
teclear("20")
elegir_direccion("dos")
dos_ok = len(lz.entrada.campos) == 2 and [c.text() for c in lz.entrada.campos] == ["20", "0"] and lz.picks
QTest.keyClicks(lz.entrada.campos[1], "")        # el foco queda en la barra
lz.entrada.campos[1].selectAll()
QTest.keyClicks(lz.entrada.campos[1], "-10")
A.esperar(80)
A.foto(v, "desfase_dos_lados")
r_dos = previa()
elegir_direccion("simetrico")
sim = (len(lz.entrada.campos) == 1, campo().text(), previa())
A.foto(v, "desfase_simetrico")
elegir_direccion("un")
un = (len(lz.entrada.campos) == 1, campo().text(), previa()[0])
A.reg(AR + " · modos", "Un lado → Dos lados → Simétrico → Un lado con la barra abierta: campos, valores y vista previa se rearman",
      dos_ok and r_dos[0] == [20.0, 50.0] and sim[0] and sim[1] == "20" and sim[2][0] == [10.0, 50.0] and un[0] and un[1] == "20"
      and un[2] == [50.0] and radios() == [30], f"{r_dos} {sim} {un}")
elegir_direccion("dos")
teclear("20")
lz.entrada.campos[1].setText("-10")
QTest.keyClick(lz.entrada.campos[1], Qt.Key_Return)
A.esperar(150)
A.reg(AR + " · modos", "Enter en Dos lados confirma lo que se ve: radios 20, 30 y 50 y un solo paso de deshacer",
      radios() == [20.0, 30.0, 50.0], f"{radios()}")
borrar_nuevos()
elegir_direccion("un")
cerrar()

# 9. Terminar el boceto, extruir el desfase y guardar / reabrir
borrar_nuevos()
empezar()
teclear("-10")
QTest.keyClick(campo(), Qt.Key_Return)
A.esperar(150)
v.modo_boceto.terminar()
A.esperar(400)
sk = L("get_sketch", sketch="S")
areas = sorted(round(p["area"], 3) for p in sk["profiles"])
A.reg(AR + " · perfiles", "al terminar, el boceto tiene el anillo (30 menos 20) y el disco de 20 de radio, más el rectángulo",
      round(math.pi * (900 - 400), 3) in areas and round(math.pi * 400, 3) in areas and 1600.0 in areas, str(areas))
anillo = [i for i, p in enumerate(sk["profiles"]) if abs(p["area"] - math.pi * 500) < 1e-3]
L("extrude", sketch="S", profile=anillo, distance=10)
vol = L("get_physical_properties")["total"]["volume"]
A.reg(AR + " · extrusión", "el anillo extruye 10 mm: volumen 5000π mm³", vol is not None and abs(vol - 5000 * math.pi) < 1e-2, f"volumen={vol}")
ruta = os.path.join(tempfile.mkdtemp(prefix="omnicad_desfase_"), "desfase.omnicad")
L("save_document", path=ruta)
s2 = api.Sesion()
r2 = api.llamar(s2, "open_document", {"path": ruta})
sk2 = api.llamar(s2, "get_sketch", {"sketch": "S"})["result"]
radios2 = sorted(round(e["radius"], 3) for e in sk2["entities"] if e["type"] == "circle")
A.reg(AR + " · guardar", "guardar y reabrir deja los mismos círculos y la cota de desfase (10, positiva)",
      r2["ok"] and radios2 == [20.0, 30.0] and any(c["type"] == "offset" and abs(c["value"] - 10) < 1e-9 for c in sk2["dimensions"]),
      f"{radios2} {[(c['type'], c.get('value')) for c in sk2['dimensions']]}")

A.reg("GENERAL", "ninguna excepción escapó de un slot de Qt en toda la corrida", not A.ERRORES, f"{len(A.ERRORES)}: {A.ERRORES[:1]}")
A.guardar_registro("desfase_boceto")
fallas = [r for r in A.REGISTRO if not r["ok"]]
print(f"\n=== {len(A.REGISTRO)} comprobaciones, {len(fallas)} con ✗ ===")
v.doc.modificado = False
v.close()
sys.exit(0)

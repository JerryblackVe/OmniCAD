# -*- coding: utf-8 -*-
"""BOCETO · Portón 3 de la auditoría CREAR/MODIFICAR (`docs/auditorias/porton_auditoria.md`): una pieza real de principio
a fin, dibujada en la ventana. Varilla de abanico de 180 × 14 × 3 mm con el agujero del eje (Ø 4) y la punta redondeada
(dos empalmes R5): Rectángulo con ancho y alto tecleados, Círculo con el diámetro tecleado, Empalme con clic en la esquina
y radio tecleado, Terminar boceto, Extruir 3 mm y, al final, doble clic en la cota del largo para pasarla a 160 y ver que
el sólido sigue. Eventos simulados al Lienzo (nunca el cursor real); capturas en cada etapa."""
import math

import arnes as A
from omnicad import api
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

AR = "BOCETO·PIEZA VARILLA"
s = api.Sesion()


def L(nombre, **a):
    r = api.llamar(s, nombre, a)
    assert r["ok"], (nombre, a, r)
    return r["result"]


L("create_sketch", name="Varilla", plane="XY")
app, v = A.iniciar(s.doc)
lz = None


def entrar():
    global lz
    v.editar_operacion(s.paso("Varilla").id)
    A.esperar(500)
    lz = v.modo_boceto.lienzo
    lz.ajustar_grilla = False
    lz.visor.objetivo = lz.plano.a_3d(90, 0)
    lz.visor.distancia = 220 / 2 / math.sin(math.radians(lz.visor.fov) / 2) * 1.3
    lz.visor.update()
    lz.update()
    A.esperar(300)


def salir():
    lz.set_herramienta("seleccionar")
    lz.seleccion = []
    v.modo_boceto.terminar()
    A.esperar(500)


def px(x, y):
    return lz.a_px(x, y).toPoint()


def clic(x, y):
    QTest.mouseClick(lz, Qt.LeftButton, Qt.NoModifier, px(x, y))
    A.esperar(90)


def mover(x, y):
    """Movimiento simulado al Lienzo (nunca el cursor real)."""
    q = QPointF(lz.a_px(x, y))
    QApplication.sendEvent(lz, QMouseEvent(QEvent.MouseMove, q, lz.mapToGlobal(q), Qt.NoButton, Qt.NoButton, Qt.NoModifier))
    A.esperar(60)


def escribir(texto, fin=Qt.Key_Tab):
    """Teclea sobre el Lienzo como la persona: el primer carácter abre la caja activa, el resto va a su campo, y `fin`
    (Tab bloquea el valor, Enter acepta)."""
    QTest.keyClick(lz, texto[0])
    A.esperar(60)
    for ch in texto[1:]:
        QTest.keyClick(lz.entrada.campos[0], ch)
    QTest.keyClick(lz.entrada.campos[0], fin)
    A.esperar(200)


def herramienta(clave):
    v.modo_boceto.acciones[clave].trigger()                    # el ítem del menú (Rectángulo y Círculo viven en submenús)
    A.esperar(150)


def teclear(*valores):
    """Cada valor en su campo de la caja (Tab entre campos, como la persona) y Enter al final."""
    for campo, texto in zip(lz.entrada.campos, valores, strict=False):
        campo.setFocus()
        campo.selectAll()
        QTest.keyClicks(campo, texto)
        A.esperar(60)
    QTest.keyClick(lz.entrada.campos[len(valores) - 1], Qt.Key_Return)
    A.esperar(250)


def caja():
    bordes = [c for c in lz.b.curvas.values() if c.id > 0 and not c.construccion and c.tipo != "circulo"]
    xs = [lz.b.coords(p)[0] for c in bordes for p in c.extremos()]
    ys = [lz.b.coords(p)[1] for c in bordes for p in c.extremos()]
    return round(min(xs), 4), round(max(xs), 4), round(min(ys), 4), round(max(ys), 4)


def dibujar():
    entrar()
    herramienta("sk_rectangulo")
    clic(0, 0)                                                 # la esquina en el origen: la ventana la ancla
    mover(50, 5)
    A.reg(AR, "Rectángulo: tras el primer clic y mover, las cajas vivas son ancho y alto", lz._claves_vivas() == ["ancho", "alto"],
          str(lz._claves_vivas()))
    escribir("180")                                            # Tab: el ancho queda bloqueado
    mover(60, 8)
    escribir("14", Qt.Key_Return)
    x0, x1, y0, y1 = caja()
    A.reg(AR, "teclear 180 y 14 y Enter: el rectángulo va de (0, 0) a (180, 14)", (x0, x1, y0, y1) == (0, 180, 0, 14),
          f"caja={caja()}")
    cotas = sorted(round(float(lz.evaluar(c.expresion)), 6) for c in lz.b.cotas.values())
    A.reg(AR, "y deja las dos cotas de lo tecleado", cotas == [14, 180], str(cotas))
    herramienta("sk_circulo")
    clic(x0 + 10, 7)
    mover(x0 + 13, 7)
    A.reg(AR, "Círculo: tras el clic del centro, la caja viva es el diámetro", lz._claves_vivas() == ["diametro"],
          str(lz._claves_vivas()))
    escribir("4", Qt.Key_Return)
    circ = [c for c in lz.b.curvas.values() if c.tipo == "circulo"]
    A.reg(AR, "teclear 4: agujero Ø 4 con su cota", len(circ) == 1 and math.isclose(lz.b.radio(circ[0].id), 2, abs_tol=1e-6),
          f"{[lz.b.radio(c.id) for c in circ]}")
    for y in (y1, y0):
        herramienta("sk_empalme")
        clic(x1, y)
        A.reg(AR, f"Empalme: clic en la esquina ({x1:g}, {y}) pide el radio", lz.entrada is not None, "")
        if lz.entrada is not None:
            teclear("5")
    arcos = [c for c in lz.b.curvas.values() if c.tipo == "arco"]
    A.reg(AR, "dos empalmes R5 en la punta, el perfil sigue cerrado", len(arcos) == 2 and
          all(math.isclose(lz.b.radio(a.id), 5, abs_tol=1e-6) for a in arcos) and lz.resultado.ok, f"arcos={len(arcos)}")
    A.foto(v, "boceto")
    salir()


def extruir():
    g = L("get_sketch", sketch="Varilla")
    perfil = max(range(len(g["profiles"])), key=lambda i: g["profiles"][i]["area"])
    L("extrude", sketch="Varilla", profile=perfil, distance=3)
    A.esperar(400)
    v.visor.encuadrar()
    A.esperar(300)
    A.foto(v, "solido_180")
    return L("get_physical_properties")


def area_esperada(largo):
    return largo * 14 - 2 * (25 - math.pi * 25 / 4) - math.pi * 4


def cambiar_largo():
    entrar()
    c = next(k for k in lz.b.cotas.values() if math.isclose(float(lz.evaluar(k.expresion)), 180))
    lz.set_herramienta("seleccionar")
    lz.update()
    A.esperar(200)
    zona = lz._zonas_cotas.get(c.id)
    A.reg(AR + " · cambio", "la cota de 180 se ve y tiene zona de clic", zona is not None, "")
    QTest.mouseDClick(lz, Qt.LeftButton, Qt.NoModifier, zona.center().toPoint())
    A.esperar(200)
    A.reg(AR + " · cambio", "doble clic en la cota abre su caja", lz.entrada is not None, "")
    teclear("160")
    x0, x1, _, _ = caja()
    A.reg(AR + " · cambio", "la cota en 160 acorta desde la punta (la esquina anclada no se mueve) y los empalmes siguen",
          (x0, x1) == (0, 160) and len([k for k in lz.b.curvas.values() if k.tipo == "arco"]) == 2
          and lz.resultado.ok, f"caja={caja()}")
    salir()
    A.esperar(400)
    v.visor.encuadrar()
    A.esperar(300)
    A.foto(v, "solido_160")


def probar():
    dibujar()
    p = extruir()
    vol = p["total"]["volume"] if "total" in p else p["bodies"][0]["volume"]
    A.reg(AR, "el sólido de 180 mide lo esperado (área del perfil × 3)", math.isclose(vol, area_esperada(180) * 3, rel_tol=1e-4),
          f"{vol:.3f} vs {area_esperada(180) * 3:.3f}")
    cambiar_largo()
    p = L("get_physical_properties")
    vol = p["total"]["volume"] if "total" in p else p["bodies"][0]["volume"]
    A.reg(AR + " · cambio", "el sólido sigue a la cota: volumen con 160 de largo", math.isclose(vol, area_esperada(160) * 3, rel_tol=1e-4),
          f"{vol:.3f} vs {area_esperada(160) * 3:.3f}")
    tl = L("get_timeline")
    A.reg(AR + " · cambio", "ningún paso del timeline quedó con error", not any(st.get("error") for st in tl.get("steps", [])),
          str([st.get("error") for st in tl.get("steps", []) if st.get("error")]))


A.correr(AR, probar)
A.reg(AR, "no se escapó ninguna excepción dentro de un slot de Qt", not A.ERRORES, "; ".join(A.ERRORES)[:300])
A.guardar_registro("cm_pieza_varilla")
fallas = sum(1 for r in A.REGISTRO if not r["ok"])
print(f"=== {len(A.REGISTRO)} comprobaciones, {fallas} con ✗", flush=True)

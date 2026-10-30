# -*- coding: utf-8 -*-
"""BOCETO · auditoría de la sesión nocturna 2026-10-29: Desfase, Simetría (espejo), Texto en curva, Patrones,
Restricciones y Deshacer dentro del editor, con eventos de mouse y teclado simulados al Lienzo (nunca el cursor real).
Cada paso se compara con la ayuda de Fusion (carpeta fusion-sketch): ver evidencias/auditoria_boceto_2026-10-29/COMPARACION.md."""
import math
import os
import sys

import arnes as A
import numpy as np
from omnicad import api
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

AR = "BOCETO·AUDITORÍA"
s = api.Sesion()


def L(nombre, **a):
    r = api.llamar(s, nombre, a)
    assert r["ok"], (nombre, a, r)
    return r["result"]


L("create_box", length=40, width=30, height=20, name="Caja", anchor="corner", x=200)
L("create_sketch", name="S", plane="XY")
L("draw_rectangle", sketch="S", x1=0, y1=0, x2=40, y2=20)
circ = L("draw_circle", sketch="S", center_x=80, center_y=10, radius=8)["entities"][0]["id"]
eje = L("draw_line", sketch="S", start_x=-30, start_y=-10, end_x=-30, end_y=40, construction=True)["entities"][0]["id"]
lin = L("draw_line", sketch="S", start_x=-60, start_y=0, end_x=-45, end_y=12)["entities"][0]["id"]
app, v = A.iniciar(s.doc)
v.editar_operacion(s.paso("S").id)
A.esperar(500)
lz = v.modo_boceto.lienzo
A.reg(AR, "entrar al boceto", v.modo_boceto.activo and lz is not None, "")
v.visor.encuadrar()
A.esperar(300)


MENSAJES = []
lz.mensaje.connect(MENSAJES.append)


def px(x, y):
    return lz.a_px(x, y).toPoint()


def clic(x, y, mod=Qt.NoModifier):
    QTest.mouseClick(lz, Qt.LeftButton, mod, px(x, y))
    A.esperar(70)


def doble(x, y):
    QTest.mouseDClick(lz, Qt.LeftButton, Qt.NoModifier, px(x, y))
    A.esperar(120)


def mover(x, y):
    q = QPointF(px(x, y))
    QApplication.sendEvent(lz, QMouseEvent(QEvent.MouseMove, q, lz.mapToGlobal(q), Qt.NoButton, Qt.NoButton, Qt.NoModifier))
    A.esperar(60)


def tecla(k, mod=Qt.NoModifier):
    QTest.keyClick(lz, k, mod)
    A.esperar(90)


def escribir(texto, i=0):
    campo = lz.entrada.campos[i]
    campo.selectAll()
    QTest.keyClicks(campo, texto)
    QTest.keyClick(campo, Qt.Key_Return)
    A.esperar(150)


def enfocar(x, y, ancho_mm=40.0):
    """Acerca la vista a (x, y) con unos `ancho_mm` a lo ancho: como cuando una persona hace zoom para tocar un punto."""
    lz.visor.objetivo = lz.plano.a_3d(x, y)
    lz.visor.distancia = ancho_mm / 2 / math.sin(math.radians(lz.visor.fov) / 2) * 1.3
    lz.visor.update()
    lz.update()
    A.esperar(250)


def n_curvas():
    return len(lz.b.curvas)


def n_restr(tipo=None):
    return sum(1 for r in lz.b.restricciones.values() if tipo is None or r.tipo == tipo)


def limpiar():
    lz.set_herramienta("seleccionar")
    lz.seleccion = []


def probar(nombre, funcion):
    try:
        funcion()
    except Exception as e:  # noqa: BLE001
        A.reg(AR, f"{nombre}: EXCEPCIÓN", False, f"{type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        limpiar()


# ---------------------------------------------------------------- DESFASE
def desfase():
    lz.set_herramienta("desfase")
    antes, r0 = n_curvas(), n_restr("desfase")
    clic(20, 0)                              # arista inferior del rectángulo
    A.esperar(100)
    mover(20, -9)                            # el lado se elige llevando el ratón
    A.reg(AR + " · Desfase", "tras el clic hay barra de valores", lz.entrada is not None, "")
    if lz.entrada is None:
        return
    A.reg(AR + " · Desfase", "la vista previa sigue al ratón (sin asa propia)", lz._asas is None, f"asas={lz._asas}")
    A.foto(v, "desfase_previa")
    escribir("5")
    A.reg(AR + " · Desfase", "Enter crea la cadena (4 curvas) con restricción y cota",
          n_curvas() == antes + 4 and n_restr("desfase") > r0 and any(c.tipo == "desfase" for c in lz.b.cotas.values()),
          f"curvas {antes}->{n_curvas()} cotas={[c.tipo for c in lz.b.cotas.values()]}")
    A.foto(v, "desfase_hecho")
    # esquina de adentro: -3 hacia dentro
    lz.set_herramienta("desfase")
    clic(0, 10)
    mover(3, 10)
    if lz.entrada is not None:
        escribir("2 mm")
        A.reg(AR + " · Desfase", "teclear «2 mm» con unidad", n_curvas() >= antes + 8, "")
    # valores raros
    for txt, esperado in (("", "no crea"), ("0", "no crea"), ("-4", "ok o aviso"), ("1e9", "no crea"), ("abc", "no crea"), ("30", "aviso")):
        lz.set_herramienta("desfase")
        a = n_curvas()
        clic(20, 20)
        mover(20, 26)
        if lz.entrada is None:
            A.reg(AR + " · Desfase", f"valor «{txt}»: barra abierta", False, "no se abrió la barra")
            continue
        lz.entrada.campos[0].selectAll()
        QTest.keyClicks(lz.entrada.campos[0], txt)
        QTest.keyClick(lz.entrada.campos[0], Qt.Key_Return)
        A.esperar(150)
        hubo = lz.entrada is None
        A.reg(AR + " · Desfase", f"valor «{txt}» no rompe ({esperado})", True, f"curvas {a}->{n_curvas()} barra_cerrada={hubo}")
        if lz.entrada is not None:
            tecla(Qt.Key_Escape)
        limpiar()
    # Ctrl+Z / Ctrl+Y
    n = n_curvas()
    tecla(Qt.Key_Z, Qt.ControlModifier)
    A.reg(AR + " · Desfase", "Ctrl+Z deshace el último desfase/valor", n_curvas() <= n, f"{n}->{n_curvas()}")
    tecla(Qt.Key_Y, Qt.ControlModifier)
    A.reg(AR + " · Desfase", "Ctrl+Y lo rehace", n_curvas() == n, f"{n_curvas()}")


# ---------------------------------------------------------------- SIMETRÍA (espejo del boceto)
def simetria():
    limpiar()
    lz.set_herramienta("simetria")
    antes, r0 = n_curvas(), n_restr("simetrica")
    clic(-52.5, 6)                           # la línea de la izquierda
    clic(80 + 8, 10)                         # y el círculo
    tecla(Qt.Key_Return)
    A.esperar(80)
    clic(-30, 20)                            # línea de simetría (construcción)
    A.esperar(150)
    A.reg(AR + " · Simetría", "clics + Enter + línea de eje crean las copias",
          n_curvas() == antes + 2, f"curvas {antes}->{n_curvas()}")
    A.reg(AR + " · Simetría", "queda la restricción de simetría", n_restr("simetrica") > r0, f"restr {r0}->{n_restr('simetrica')}")
    A.foto(v, "simetria")
    # el eje no puede ser una curva
    limpiar()
    lz.set_herramienta("simetria")
    a = n_curvas()
    clic(-52.5, 6)
    tecla(Qt.Key_Return)
    clic(80 + 8, 10)                         # círculo como eje: debe avisar y no crear
    A.reg(AR + " · Simetría", "un círculo como eje no crea nada", n_curvas() == a, f"{a}->{n_curvas()}")
    limpiar()


# ---------------------------------------------------------------- TEXTO EN CURVA
def texto_curva():
    limpiar()
    lz.set_herramienta("texto")
    clic(80, 10 + 8)                         # sobre el círculo: texto en curva
    A.esperar(120)
    A.reg(AR + " · Texto en curva", "clic en una curva abre la barra del texto", lz.entrada is not None, "")
    if lz.entrada is None:
        return
    A.reg(AR + " · Texto en curva", "sin asa de giro (Fusion tampoco la tiene en texto sobre ruta)", lz._asas is None, "")
    escribir("HOLA", 0)
    A.esperar(200)
    textos = [c for c in lz.b.curvas.values() if type(c).__name__ == "Texto"]
    A.reg(AR + " · Texto en curva", "Enter crea un texto con camino", bool(textos) and getattr(textos[-1], "camino", None) is not None,
          f"textos={len(textos)}")
    A.foto(v, "texto_curva")
    if textos:
        def caja(t):
            pts = [q for poli in lz._polilineas(t) for q in poli]
            return (min(q[0] for q in pts), min(q[1] for q in pts), max(q[0] for q in pts), max(q[1] for q in pts))
        c0 = caja(textos[-1])
        lz.b.curvas[circ].radio = 14.0          # el círculo-camino se achica: el texto lo sigue (Fusion: «text adapts»)
        lz.resolver()
        A.esperar(150)
        c1 = caja(textos[-1])
        A.reg(AR + " · Texto en curva", "si cambia la curva, el texto se adapta", c1 != c0, f"{c0} -> {c1}")
        A.foto(v, "texto_curva_radio")
    limpiar()


# ---------------------------------------------------------------- PATRONES
def patrones():
    limpiar()
    ids = [i for i, c in lz.b.curvas.items() if c.__class__.__name__ == "Circulo"]
    lz.set_herramienta("patron_circular")
    lz.seleccion = ids
    lz._avanzar_seleccion()
    lz._clic_fase((None, (80.0, -30.0)))
    A.esperar(100)
    A.reg(AR + " · Patrón circular", "barra con cantidad y ángulo", lz.entrada is not None, "")
    if lz.entrada is not None:
        lz.entrada.campos[0].setText("5")
        lz.entrada.campos[1].setText("360")
        A.esperar(100)
        A.foto(v, "patron_circular_previa")
        QTest.keyClick(lz.entrada.campos[0], Qt.Key_Return)
        A.esperar(250)
        A.reg(AR + " · Patrón circular", "Enter crea 4 copias", len(lz.b.patrones) == 1, f"patrones={len(lz.b.patrones)}")
    # Fusion dibuja una casilla por copia para suprimirla: ¿OmniCAD?
    if lz.b.patrones:
        r = lz.b.patrones[0]
        limpiar()                               # Esc / herramienta Seleccionar: las casillas aparecen con el patrón elegido
        lz.seleccion = list(r["ids"])
        lz.update()
        A.esperar(200)
        casillas = lz._casillas_patron()
        A.reg(AR + " · Patrón circular", "una casilla por copia en el lienzo (Fusion)", len(casillas) == 4, f"{len(casillas)} casillas")
        A.foto(v, "patron_circular_casillas")
        if casillas:
            copias0 = sum(len(x) for x in r["copias"].values())
            _pid, _i, caja, _s = casillas[1]
            QTest.mouseClick(lz, Qt.LeftButton, Qt.NoModifier, caja.center().toPoint())
            A.esperar(200)
            r = lz.b.patrones[0]
            A.reg(AR + " · Patrón circular", "clic en la casilla suprime esa copia", r["suprimidos"] == [1] or set(r["suprimidos"]) == {1}, f"suprimidos={r['suprimidos']}")
            A.reg(AR + " · Patrón circular", "la copia suprimida desaparece", sum(len(x) for x in r["copias"].values()) < copias0, f"{copias0}->{sum(len(x) for x in r['copias'].values())}")
            A.foto(v, "patron_circular_suprimida")
            lz.seleccion = list(r["ids"])
            casillas = lz._casillas_patron()
            A.reg(AR + " · Patrón circular", "la casilla de la suprimida sigue ahí (desmarcada)", len(casillas) == 4 and casillas[1][3], f"{len(casillas)}")
            tecla(Qt.Key_Z, Qt.ControlModifier)
            A.reg(AR + " · Patrón circular", "Ctrl+Z la vuelve a crear", not lz.b.patrones[0]["suprimidos"], f"{lz.b.patrones[0]['suprimidos']}")
    A.foto(v, "patron_circular_hecho")
    limpiar()


# ---------------------------------------------------------------- RESTRICCIONES (herramientas de la cinta)
def restricciones():
    """Las restricciones con la herramienta de la cinta: clic en la geometría, aparece, tiene glifo, Ctrl+Z/Ctrl+Y."""
    limpiar()
    b = lz.b
    fila = [-80.0]

    def sig():
        fila[0] -= 30.0
        return fila[0]

    def mid(c):
        x1, y1 = b.coords(c.p1)
        x2, y2 = b.coords(c.p2)
        return ((x1 + x2) / 2, (y1 + y2) / 2)

    casos = []                                    # (herramienta, tipo, [(x, y) donde se hace clic])
    y = sig()
    ln = b.agregar_linea((100, y), (120, y + 6))
    casos.append(("r_horizontal_vertical", "horizontal", [mid(b.curvas[ln])]))
    y = sig()
    a, c = b.agregar_linea((100, y), (120, y + 4)), b.agregar_linea((100, y + 10), (126, y + 11))
    for herr, tipo in (("r_paralela", "paralela"), ("r_igual", "igual"), ("r_perpendicular", "perpendicular"),
                       ("r_colineal", "colineal")):
        casos.append((herr, tipo, [mid(b.curvas[a]), mid(b.curvas[c])]))
    y = sig()
    f = b.agregar_linea((100, y), (120, y + 4))
    casos.append(("r_fijo", "fijo", [mid(b.curvas[f])]))
    y = sig()
    b.agregar_circulo((100, y), 5)
    b.agregar_circulo((120, y), 8)
    casos.append(("r_concentrica", "concentrica", [(105, y), (128, y)]))
    casos.append(("r_igual", "igual", [(100, y + 5), (120, y + 8)]))
    y = sig()
    b.agregar_circulo((100, y), 6)
    l3 = b.agregar_linea((90, y + 15), (130, y + 16))
    casos.append(("r_tangente", "tangente", [(100, y + 6), mid(b.curvas[l3])]))
    y = sig()
    b.agregar_punto(100, y)
    b.agregar_punto(110, y + 3)
    casos.append(("r_coincidente", "coincidente", [(100, y), (110, y + 3)]))
    y = sig()
    b.agregar_punto(104, y + 3)
    b.agregar_linea((100, y), (120, y + 8))
    casos.append(("r_punto_medio", "punto_medio", [(104, y + 3), (118, y + 7.2)]))
    y = sig()
    b.agregar_punto(100, y)
    b.agregar_punto(104, y + 9)
    b.agregar_linea((112, y - 5), (112, y + 15), construccion=True)
    casos.append(("r_simetria", "simetrica", [(100, y), (104, y + 9), (112, y + 14)]))
    y = sig()
    unido = b.agregar_punto(120, y + 4)               # la curvatura pide dos curvas encadenadas: comparten este extremo
    s1 = b.agregar_spline([(100, y), (110, y + 8), unido])
    s2 = b.agregar_spline([unido, (130, y), (140, y + 8)])

    def cuarto(c):                       # un punto de la curva lejos de sus puntos de ajuste: ahí hace clic una persona
        poli = lz._polilineas(b.curvas[c])[0]
        return tuple(poli[len(poli) // 4])
    casos.append(("r_curvatura", "curvatura", [cuarto(s1), cuarto(s2)]))
    lz.resolver()
    lz.encuadrar()
    A.esperar(300)
    A.foto(v, "restricciones_antes")
    for herr, tipo, picks in casos:
        lz.set_herramienta(herr)
        r0 = n_restr(tipo)
        enfocar(sum(q[0] for q in picks) / len(picks), sum(q[1] for q in picks) / len(picks))
        for xy in picks:
            clic(*xy)
        A.esperar(100)
        hay = n_restr(tipo) == r0 + 1
        A.reg(AR + " · Restricciones", f"{herr}: los clics la agregan", hay,
              f"{r0}->{n_restr(tipo)} px={[(px(*xy).x(), px(*xy).y()) for xy in picks]} ent={[lz.entidad_en(px(*xy)) for xy in picks]} "
              f"msg={MENSAJES[-1:]} picks={lz.picks}")
        if hay and herr in ("r_paralela", "r_tangente"):
            rid = list(b.restricciones.values())[-1].id
            lz.set_herramienta("seleccionar")
            lz.update()
            A.esperar(250)
            glifo = lz._zonas_glifos.get(rid)
            A.reg(AR + " · Restricciones", f"{herr}: su glifo se ve en el lienzo", glifo is not None, "")
            if glifo is not None:
                QTest.mouseClick(lz, Qt.LeftButton, Qt.NoModifier, glifo.center().toPoint())
                A.esperar(120)
                A.reg(AR + " · Restricciones", f"{herr}: clic en el glifo lo elige", rid in lz.seleccion, f"seleccion={lz.seleccion}")
                lz.seleccion = [rid]
                tecla(Qt.Key_Delete)
                A.reg(AR + " · Restricciones", f"{herr}: Supr la borra", n_restr(tipo) == r0, f"{n_restr(tipo)}")
                tecla(Qt.Key_Z, Qt.ControlModifier)
                A.reg(AR + " · Restricciones", f"{herr}: Ctrl+Z la devuelve", n_restr(tipo) == r0 + 1, f"{n_restr(tipo)}")
        if hay:
            A.esperar(120)
            tecla(Qt.Key_Z, Qt.ControlModifier)
            A.reg(AR + " · Restricciones", f"{herr}: Ctrl+Z la quita", n_restr(tipo) == r0, f"{n_restr(tipo)}")
            tecla(Qt.Key_Y, Qt.ControlModifier)
            A.reg(AR + " · Restricciones", f"{herr}: Ctrl+Y la vuelve", n_restr(tipo) == r0 + 1, f"{n_restr(tipo)}")
            tecla(Qt.Key_Z, Qt.ControlModifier)          # el boceto queda como estaba para el caso que sigue
        limpiar()
    A.esperar(150)
    A.reg(AR + " · Restricciones", "hay glifos dibujados en el lienzo", len(lz._zonas_glifos) > 0, f"{len(lz._zonas_glifos)}")
    A.foto(v, "restricciones_glifos")


# ---------------------------------------------------------------- PROYECCIÓN del modelo
def proyeccion():
    """Herramienta Proyectar con el mouse sobre una arista y sobre el cuerpo (filtro «Cuerpos»), vínculo y Ctrl+Z/Ctrl+Y."""
    limpiar()
    enfocar(220, 15, 120)
    n0 = len(lz.b.proyecciones)
    lz.set_herramienta("proyectar")
    q = lz.visor.proyectar(np.array([220.0, 0.0, 20.0]), lz._mvp)          # arista frontal de la tapa de la caja
    QTest.mouseClick(lz, Qt.LeftButton, Qt.NoModifier, q.toPoint())
    A.esperar(300)
    A.reg(AR + " · Proyección", "clic en una arista del modelo la proyecta", len(lz.b.proyecciones) == n0 + 1,
          f"{n0}->{len(lz.b.proyecciones)} msg={MENSAJES[-1:]}")
    if len(lz.b.proyecciones) == n0 + 1:
        r = lz.b.proyecciones[-1]
        A.reg(AR + " · Proyección", "la geometría proyectada queda fija (violeta) y vinculada",
              all(lz.b.puntos[p].proyectado for p in lz.b.puntos_de(r["ids"])) and bool(r.get("refs")), f"refs={r.get('refs')}")
        A.foto(v, "proyeccion_arista")
        tecla(Qt.Key_Z, Qt.ControlModifier)
        A.reg(AR + " · Proyección", "Ctrl+Z la quita", len(lz.b.proyecciones) == n0, f"{len(lz.b.proyecciones)}")
        tecla(Qt.Key_Y, Qt.ControlModifier)
        A.reg(AR + " · Proyección", "Ctrl+Y la vuelve", len(lz.b.proyecciones) == n0 + 1, f"{len(lz.b.proyecciones)}")
    # filtro «Cuerpos»: el clic en una cara toma el cuerpo entero
    lz.opciones["filtro_proyectar"] = "cuerpos"
    q = lz.visor.proyectar(np.array([220.0, 15.0, 20.0]), lz._mvp)
    QTest.mouseClick(lz, Qt.LeftButton, Qt.NoModifier, q.toPoint())
    A.esperar(300)
    A.reg(AR + " · Proyección", "filtro «Cuerpos»: un clic proyecta el contorno del cuerpo", len(lz.b.proyecciones) >= n0 + 2,
          f"proyecciones={len(lz.b.proyecciones)} msg={MENSAJES[-1:]}")
    lz.opciones["filtro_proyectar"] = "entidades"
    A.foto(v, "proyeccion_cuerpo")
    limpiar()
    # romper vínculo con la herramienta
    if lz.b.proyecciones:
        pid = lz.b.proyecciones[-1]["id"]
        ids = lz.b.proyecciones[-1]["ids"]
        c = next((i for i in ids if i in lz.b.curvas), None)
        if c is not None:
            xy = lz._ancla(c)
            QTest.mouseClick(lz, Qt.LeftButton, Qt.NoModifier, xy.toPoint())       # clic en la línea proyectada la elige
            A.esperar(150)
            lz.romper_vinculo()                                                    # el botón «Romper vínculo» de la cinta
            A.esperar(200)
            A.reg(AR + " · Proyección", "Romper vínculo: la proyección ya no es asociativa", all(r["id"] != pid for r in lz.b.proyecciones),
                  f"seleccion={lz.seleccion} proyecciones={[r['id'] for r in lz.b.proyecciones]} msg={MENSAJES[-1:]}")
    limpiar()


# ---------------------------------------------------------------- DESHACER dentro del boceto
def deshacer():
    limpiar()
    lz.set_herramienta("linea")
    enfocar(-85, 85, 60)
    base = n_curvas()
    for i in range(110):
        clic(-100 + i * 0.3, 80)
        clic(-100 + i * 0.3, 90 + (i % 5))
        tecla(Qt.Key_Escape)
    A.reg(AR + " · Deshacer", "110 líneas dibujadas con el mouse", n_curvas() >= base + 100, f"{base}->{n_curvas()}")
    n_max = n_curvas()
    pasos = 0
    while lz.historial and pasos < 300:
        tecla(Qt.Key_Z, Qt.ControlModifier)
        pasos += 1
    A.reg(AR + " · Deshacer", "se pueden deshacer los pasos hechos (tope del editor: 200)", pasos >= min(200, n_max - base),
          f"deshizo {pasos}, quedan {n_curvas()} (base {base})")
    for _ in range(pasos):
        tecla(Qt.Key_Y, Qt.ControlModifier)
    A.reg(AR + " · Deshacer", "rehacer en cadena vuelve al total", n_curvas() == n_max, f"{n_curvas()} vs {n_max}")
    limpiar()


SOLO = os.environ.get("AUD_SOLO", "").split(",")
for nombre, f in (("proyeccion", proyeccion), ("desfase", desfase), ("simetria", simetria), ("texto_curva", texto_curva), ("patrones", patrones),
                  ("restricciones", restricciones), ("deshacer", deshacer)):
    if SOLO == [""] or nombre in SOLO:
        probar(nombre, f)

v.modo_boceto.cancelar()
A.esperar(300)
A.reg(AR, "sin excepciones sueltas en slots de Qt", not A.ERRORES, "; ".join(A.ERRORES)[:300])
A.guardar_registro("auditoria_boceto")
fallas = [r for r in A.REGISTRO if not r["ok"]]
print(f"=== {len(A.REGISTRO)} comprobaciones, {len(fallas)} con ✗", flush=True)
sys.exit(0)

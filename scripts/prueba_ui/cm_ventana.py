# -*- coding: utf-8 -*-
"""BOCETO · CREAR y MODIFICAR en la ventana real, lo que hasta el 2026-11-08 solo se había probado con eventos a un Lienzo
suelto (auditoría `docs/auditoria_boceto_crear_modificar.md`, fase 6): Recortar arrastrando sobre varios tramos con un
solo deshacer (H-110), Curva de fusión con clic en una arista del modelo (P-73), Mover/copiar y el marco de control sobre
una ranura anclada al origen (B-245, B-253) y los glifos de punto medio e igualdad después del empalme (P-75). Botón
real de la cinta, clics y arrastres simulados al Lienzo, valores tecleados y Enter; nunca el cursor real."""
import math

import arnes as A
import numpy as np
from omnicad import api
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QToolButton

AR = "BOCETO·CM-VENTANA"
s = api.Sesion()


def L(nombre, **a):
    r = api.llamar(s, nombre, a)
    assert r["ok"], (nombre, a, r)
    return r["result"]


def ids(r):
    return [e["id"] for e in r["entities"]]


# ---- geometría (por la API; lo que se prueba es lo que hace la persona en la ventana)
L("create_box", length=40, width=20, height=5, name="Caja")
L("create_sketch", name="R", plane="XY")                                           # H-110
VERT = [ids(L("draw_line", sketch="R", start_x=x, start_y=-20, end_x=x, end_y=20))[0] for x in (10, 30, 50)]
HORIZ = ids(L("draw_line", sketch="R", start_x=0, start_y=0, end_x=60, end_y=0))[0]
L("create_sketch", name="F", plane="XY")                                           # P-73
LINEA_F = ids(L("draw_line", sketch="F", start_x=40, start_y=30, end_x=60, end_y=30))[0]
L("create_sketch", name="A", plane="XY")                                           # B-245 y B-253: ranura anclada
r = L("draw_slot", sketch="A", kind="center_point", points=[[0, 0], [30, 0]], width=20)
g = L("get_sketch", sketch="A")
eje = next(e for e in g["entities"] if e["construction"])
centro = next(c["entities"][0] for c in g["constraints"] if c["type"] == "midpoint")
arco = next(e["id"] for e in g["entities"] if e["type"] == "arc")
L("add_constraint", sketch="A", type="coincident", entities=[centro, 0])
L("add_constraint", sketch="A", type="horizontal", entities=[eje["id"]])
L("add_dimension", sketch="A", type="distance", entities=[eje["id"]], value=60)
L("add_dimension", sketch="A", type="radius", entities=[arco], value=10)
RANURA = [e for e in ids(r) if e != eje["id"]]
L("create_sketch", name="E", plane="XY")                                           # P-75: cuadrado con punto medio e igual
L("draw_rectangle", sketch="E", center_x=0, center_y=0, width=100, height=100)
LADOS = [e["id"] for e in L("get_sketch", sketch="E")["entities"] if e["type"] == "line"]
for lado, (x, y), ej in ((LADOS[0], (0, -50), -2), (LADOS[1], (50, 0), -1)):
    pm, = L("draw_point", sketch="E", x=x, y=y)["points"]
    L("add_constraint", sketch="E", type="midpoint", entities=[pm, lado])
    L("add_constraint", sketch="E", type="coincident", entities=[pm, ej])
L("add_constraint", sketch="E", type="equal", entities=LADOS[:2])
L("add_dimension", sketch="E", type="distance", entities=[LADOS[0]], value=100)
assert L("get_sketch", sketch="A")["dof"] == 0 and L("get_sketch", sketch="E")["dof"] == 0

app, v = A.iniciar(s.doc)
CAJA = next(iter(v.doc.estado_final.cuerpos))
lz = None
MENSAJES = []


def entrar(nombre, centro=(0, 0), span=140):
    global lz
    v.editar_operacion(s.paso(nombre).id)
    A.esperar(500)
    lz = v.modo_boceto.lienzo
    MENSAJES.clear()
    try:
        lz.mensaje.disconnect(MENSAJES.append)
    except (RuntimeError, TypeError):
        pass
    lz.mensaje.connect(MENSAJES.append)
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
    A.esperar(90)


def clic_3d(punto):
    """Clic sobre un punto del modelo, pasado por el visor (como en proyectar_boceto.py)."""
    q = lz.mapFromGlobal(v.visor.mapToGlobal(v.visor.proyectar(np.array(punto, float)).toPoint()))
    QTest.mouseClick(lz, Qt.LeftButton, Qt.NoModifier, q)
    A.esperar(120)


def tecla(k, mod=Qt.NoModifier):
    QTest.keyClick(lz, k, mod)
    A.esperar(90)


def mover(a, b, botones, pasos=6):
    for i in range(1, pasos + 1):
        q = a + (b - a) * (i / pasos)
        QApplication.sendEvent(lz, QMouseEvent(QEvent.MouseMove, q, lz.mapToGlobal(q), Qt.NoButton, botones, Qt.NoModifier))
        A.esperar(15)


def boton_cinta(clave):
    accion = v.modo_boceto.acciones[clave]
    return next(b for b in v.cinta.findChildren(QToolButton) if b.defaultAction() is accion and b.isVisible())


def pulsar_cinta(clave):
    """Botón de la cinta si está a la vista; si vive en un submenú, el ítem del menú (lo mismo que hace la persona)."""
    try:
        QTest.mouseClick(boton_cinta(clave), Qt.LeftButton)
    except StopIteration:
        v.modo_boceto.acciones[clave].trigger()
    A.esperar(180)


def teclear_entrada(texto):
    campo = lz.entrada.campos[0]
    campo.setFocus()
    campo.selectAll()
    QTest.keyClicks(campo, texto)
    QTest.keyClick(campo, Qt.Key_Return)
    A.esperar(250)


# ---------------------------------------------------------------- H-110: Recortar arrastrando sobre tres tramos
def h110():
    entrar("R", centro=(30, 0), span=100)
    pulsar_cinta("sk_recortar")
    A.reg(AR + " · H-110", "el botón Recortar de la cinta activa la herramienta", lz.herramienta == "recortar", lz.herramienta)
    original = lz.b.a_dict()
    pasos = len(lz.historial)
    a, b = QPointF(lz.a_px(0, 10)), QPointF(lz.a_px(60, 10))
    QTest.mousePress(lz, Qt.LeftButton, Qt.NoModifier, a.toPoint())
    mover(a, b, Qt.LeftButton, pasos=12)
    mover(b, a, Qt.LeftButton, pasos=6)                       # volver por lo borrado no toca la horizontal de abajo
    QTest.mouseRelease(lz, Qt.LeftButton, Qt.NoModifier, a.toPoint())
    A.esperar(200)
    A.foto(v, "h110_recortado")
    ext = [lz.b._extremos_linea(c) for c in VERT]
    ok = all(e == ((x, -20), (x, 0)) or e == ((x, 0), (x, -20)) for e, x in zip(ext, (10, 30, 50), strict=True))
    A.reg(AR + " · H-110", "arrastrar de x=0 a x=60 por encima de la horizontal recorta las tres verticales hasta y=0",
          ok and lz.b._extremos_linea(HORIZ) == ((0, 0), (60, 0)), str(ext))
    A.reg(AR + " · H-110", "todo el arrastre es UN paso de deshacer", len(lz.historial) == pasos + 1, f"{pasos}->{len(lz.historial)}")
    recortado = lz.b.a_dict()
    tecla(Qt.Key_Z, Qt.ControlModifier)
    A.reg(AR + " · H-110", "Ctrl+Z una vez devuelve las tres verticales enteras", lz.b.a_dict() == original, "")
    tecla(Qt.Key_Y, Qt.ControlModifier)
    A.reg(AR + " · H-110", "Ctrl+Y rehace el recorte entero", lz.b.a_dict() == recortado, "")
    tecla(Qt.Key_Escape)
    salir()
    sk = L("get_sketch", sketch="R")
    largos = sorted(round(e["length"], 6) for e in sk["entities"] if e["type"] == "line")
    A.reg(AR + " · H-110", "al terminar el boceto el documento guarda el recorte (3 de 20 y la horizontal de 60)",
          largos == [20, 20, 20, 60], str(largos))


# ---------------------------------------------------------------- P-73: Curva de fusión con una arista del modelo
def p73():
    from omnicad.nucleo import referencias as refs
    entrar("F", centro=(20, 15), span=120)
    forma = v.doc.estado_final.cuerpos[CAJA].forma
    aristas = [refs.firma_arista(a) for a in refs.subformas(forma, "arista")]
    paralelas_x = [f for f in aristas if f["geom"] == "linea"
                   and abs(np.subtract(*f["extremos"])[1]) + abs(np.subtract(*f["extremos"])[2]) < 1e-6]
    medio = max(paralelas_x, key=lambda f: (f["medio"][1], f["medio"][2]))["medio"]   # la de arriba, del lado +Y
    pulsar_cinta("sk_curva_fusion")
    A.reg(AR + " · P-73", "el botón Curva de fusión activa la herramienta", lz.herramienta == "curva_fusion", lz.herramienta)
    antes = len(lz.b.curvas)
    clic_3d(medio)
    proy = [c for c in lz.b.curvas.values() if getattr(c, "proyectada", False)]
    A.reg(AR + " · P-73", "clic en la arista de la caja: queda proyectada y elegida (1 de 2)",
          len(lz.picks) == 1 and len(proy) == 1 and len(lz.b.proyecciones) == 1,
          f"picks={lz.picks} proyectadas={len(proy)} mensajes={MENSAJES[-1:]}")
    clic(55, 30)
    A.esperar(200)
    A.foto(v, "p73_fusion")
    tipos = sorted(c.tipo for c in lz.b.curvas.values() if c.id > 0 and not getattr(c, "proyectada", False))
    A.reg(AR + " · P-73", "clic en la línea del boceto: nace la spline de fusión entre las dos",
          "spline" in tipos and len(lz.b.curvas) > antes and lz.resultado.ok, f"{tipos} {MENSAJES[-1:]}")
    tecla(Qt.Key_Z, Qt.ControlModifier)
    A.reg(AR + " · P-73", "Ctrl+Z quita la fusión y la proyección juntas",
          not any(getattr(c, "proyectada", False) for c in lz.b.curvas.values()) and
          not any(c.tipo == "spline" for c in lz.b.curvas.values()), str(sorted(c.tipo for c in lz.b.curvas.values())))
    tecla(Qt.Key_Y, Qt.ControlModifier)
    salir()
    sk = L("get_sketch", sketch="F")
    A.reg(AR + " · P-73", "terminado el boceto, el documento tiene la spline y la arista proyectada",
          any(e["type"] == "spline" for e in sk["entities"]), str(sorted(e["type"] for e in sk["entities"])))


# ---------------------------------------------------------------- B-245 y B-253: mover lo anclado al origen
def anclado():
    entrar("A", centro=(0, 0), span=120)
    p = lz.b.curvas[RANURA[0]].puntos()[0]
    antes = lz.b.coords(p)
    pasos = len(lz.historial)
    for c in RANURA:                                           # elegir con clics, Mayús suma
        k = lz.b.curvas[c]
        if k.tipo == "linea":
            (x1, y1), (x2, y2) = lz.b._extremos_linea(c)
            clic((x1 + x2) / 2, (y1 + y2) / 2, Qt.ShiftModifier)
    lz.seleccion = list(RANURA)                                # los arcos se suman como en la ventana de selección
    lz.update()
    A.esperar(150)
    pulsar_cinta("sk_mover")
    panel = v.modo_boceto.transformar
    A.reg(AR + " · B-245", "Mover/copiar abre su panel con la ranura elegida", lz.herramienta == "mover" and panel.isVisible(),
          lz.herramienta)
    campo = panel.campos["dx"]
    campo.setFocus()
    campo.selectAll()
    QTest.keyClicks(campo, "200")
    A.esperar(200)
    QTest.mouseClick(panel.boton_ok, Qt.LeftButton)
    A.esperar(300)
    A.foto(v, "b245_mover_anclado")
    A.reg(AR + " · B-245", "Aceptar con X = 200 no mueve la ranura anclada ni suma un paso de deshacer",
          np.allclose(lz.b.coords(p), antes) and len(lz.historial) == pasos,
          f"{antes}->{lz.b.coords(p)} pasos {pasos}->{len(lz.historial)}")
    A.reg(AR + " · B-245", "y lo dice: el mensaje nombra el origen", bool(MENSAJES) and "origen" in MENSAJES[-1], str(MENSAJES[-1:]))
    tecla(Qt.Key_Escape)
    lz.set_herramienta("seleccionar")
    lz.seleccion = list(RANURA)
    lz.encuadrar()
    A.esperar(250)
    MENSAJES.clear()
    q = lz._manijas_marco(lz._caja_marco())["mover"]
    QTest.mousePress(lz, Qt.LeftButton, Qt.NoModifier, q.toPoint())
    mover(QPointF(q), QPointF(q.x() + 60, q.y()), Qt.LeftButton)
    QTest.mouseRelease(lz, Qt.LeftButton, Qt.NoModifier, QPointF(q.x() + 60, q.y()).toPoint())
    A.esperar(250)
    A.foto(v, "b253_marco_anclado")
    A.reg(AR + " · B-253", "arrastrar el asa de mover del marco de control no la mueve ni deja un paso de deshacer",
          np.allclose(lz.b.coords(p), antes) and len(lz.historial) == pasos, f"{antes}->{lz.b.coords(p)}")
    A.reg(AR + " · B-253", "y avisa que está anclada al origen", bool(MENSAJES) and "origen" in MENSAJES[-1], str(MENSAJES[-1:]))
    salir()


# ---------------------------------------------------------------- P-75: glifos de punto medio e igualdad tras el empalme
def p75():
    entrar("E", centro=(0, 0), span=150)
    tipos = ("punto_medio", "igual")
    rels = {k for k, r in lz.b.restricciones.items() if r.tipo in tipos}
    construccion = {k for k, c in lz.b.curvas.items() if c.construccion}

    def con_glifo():
        lz.update()
        A.esperar(200)
        zonas = set(lz._zonas_glifos) | {i for i, _ in lz._zonas_glifos_extra}
        return rels & zonas

    antes = con_glifo()
    A.reg(AR + " · P-75", "antes del empalme se ven los glifos de punto medio e igual", antes == rels, f"{sorted(antes)} de {sorted(rels)}")
    pulsar_cinta("sk_empalme")
    clic(50, 50)                                               # clic en el vértice de la esquina
    A.reg(AR + " · P-75", "clic en la esquina pide el radio", lz.entrada is not None, str(MENSAJES[-1:]))
    if lz.entrada is not None:
        teclear_entrada("10")
    A.foto(v, "p75_empalme")
    arcos = [c for c in lz.b.curvas.values() if c.tipo == "arco"]
    A.reg(AR + " · P-75", "teclear 10 y Enter crea el empalme de radio 10, el perfil sigue en 0 grados de libertad",
          len(arcos) == 1 and math.isclose(lz.b.radio(arcos[0].id), 10, abs_tol=1e-6) and lz.resultado.ok and lz.resultado.gdl == 0,
          f"arcos={len(arcos)} gdl={lz.resultado.gdl}")
    A.reg(AR + " · P-75", "no aparece ninguna línea guía de construcción",
          {k for k, c in lz.b.curvas.items() if c.construccion} == construccion, "")
    A.reg(AR + " · P-75", "punto medio e igual siguen y sus glifos se siguen viendo",
          {k for k, r in lz.b.restricciones.items() if r.tipo in tipos} == rels and con_glifo() == rels,
          f"glifos {sorted(con_glifo())}")
    salir()


for nombre, f in (("H-110", h110), ("P-73", p73), ("B-245/B-253", anclado), ("P-75", p75)):
    A.correr(AR + " · " + nombre, f)
    if v.modo_boceto.activo:
        salir()

A.reg(AR, "no se escapó ninguna excepción dentro de un slot de Qt", not A.ERRORES, "; ".join(A.ERRORES)[:300])
A.guardar_registro("cm_ventana")
fallas = sum(1 for r in A.REGISTRO if not r["ok"])
print(f"=== {len(A.REGISTRO)} comprobaciones, {fallas} con ✗", flush=True)

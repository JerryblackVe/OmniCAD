# -*- coding: utf-8 -*-
"""INSPECCIONAR › Mapa de desviación (F10, SC13), como una persona: se abre desde la cinta, se elige el cuerpo y la referencia
con clics en el visor, se teclea la tolerancia, se mira el color, la escala, el mínimo y el máximo, se pasa el cursor por el
agujero corrido y se lee su valor, se acepta, se reabre desde el análisis guardado y se prueba en una ventana chica."""
import sys

import arnes as A
import numpy as np
import teclado as T
from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QImage, QMouseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from omnicad import api

AR = "MAPA·DESVIACIÓN"
s = api.Sesion()


def L(nombre, **a):
    r = api.llamar(s, nombre, a)
    assert r["ok"], (nombre, a, r)
    return r["result"]


# dos placas iguales salvo un agujero corrido 1 mm, una al lado de la otra
L("create_box", length=80, width=50, height=8, x=-50)
L("create_hole", face=">Z", diameter=10, points=[[-40, 0, 8]], through_all=True, body="op1.c1")
L("create_box", length=80, width=50, height=8, x=50)
L("create_hole", face=">Z", diameter=10, points=[[61, 0, 8]], through_all=True, body="op3.c1")
L("move_body", body="op3.c1", translate=[-100, 0, 0], copy=False)
a, b = "op1.c1", "op3.c1"
app, v = A.iniciar(s.doc)
vis = v.visor
vis.encuadrar()
A.esperar(300)


def contar(canal):
    """Píxeles de la pieza donde manda ese canal (0 rojo, 1 verde, 2 azul): solo alrededor del agujero, sin la escala del panel."""
    cx, cy = vis.puntos_pantalla(np.array([[-40.0, 0.0, 8.0]]))[0][0]
    x = vis.grabFramebuffer().convertToFormat(QImage.Format_RGB888)
    arr = np.frombuffer(x.constBits(), np.uint8).reshape(x.height(), x.bytesPerLine())[:, :x.width() * 3]
    arr = arr.reshape(x.height(), x.width(), 3).astype(int)
    e = x.width() / vis.width()
    y0, x0 = int((cy - 70) * e), int((cx - 110) * e)
    zona = arr[max(y0, 0):int((cy + 70) * e), max(x0, 0):int((cx + 110) * e)]
    otros = np.delete(zona, canal, axis=2).max(2)
    return int((zona[:, :, canal] > 1.5 * otros + 8).sum())


def mover(w, pos):
    """Movimiento simulado: no toca el cursor real de Windows."""
    QApplication.sendEvent(w, QMouseEvent(QEvent.MouseMove, QPointF(pos), w.mapToGlobal(QPointF(pos)), Qt.NoButton, Qt.NoButton,
                                          Qt.NoModifier))


from omnicad.ui import cinta  # noqa: E402

A.reg(AR, "el botón está en INSPECCIONAR de la cinta", any("mapa_desviacion" in str(g) for g in cinta.INSPECCIONAR), "")
p = A.abrir(v, "mapa_desviacion")
A.reg(AR, "el panel pide cuerpo, referencia y tolerancia",
      [c.clave for c in p.campos if c.clave in ("cuerpos", "referencia", "tolerancia")] == ["cuerpos", "referencia", "tolerancia"], "")
A.elegir(p, "cuerpos", A.hit_cuerpo(v, a))
A.reg(AR, "con solo el cuerpo no pinta nada ni falla", not vis.mallas_analisis, "")
A.elegir(p, "referencia", A.hit_cuerpo(v, b))
A.esperar(1500)
A.reg(AR, "con los dos elegidos el visor pinta el cuerpo", a in vis.mallas_analisis, str(list(vis.mallas_analisis)))
A.foto(v, "mapa_desviacion_pintado")
verde, rojo, azul = contar(1), contar(0), contar(2)
A.reg(AR, "casi todo verde, y rojo y azul alrededor del agujero corrido", verde > 8 * rojo and rojo > 30 and azul > 30,
      f"{verde} verdes, {rojo} rojos, {azul} azules")
texto = p.widgets["extremos"].text()
A.reg(AR, "muestra mínimo y máximo con unidades, de −1 a +1 mm", "Mínimo -1" in texto and "Máximo 0.99" in texto, texto)

# tolerancia tecleada, con coma y con unidades; vacío y 0 no rompen
T.teclear(p, "tolerancia", "2 mm", Qt.Key_Tab)
A.esperar(1500)
rojo2 = contar(0)
A.reg(AR, "con tolerancia de 2 mm ya nada pasa: el rojo desaparece", rojo2 < rojo * 0.2, f"{rojo} → {rojo2}")
for malo in ("0 mm", "-1 mm"):
    T.teclear(p, "tolerancia", malo, Qt.Key_Tab)
    A.esperar(300)
    A.reg(AR, f"tolerancia «{malo}»: no pinta de nuevo ni se cierra", p.isVisible(), "")
T.teclear(p, "tolerancia", "0,1 mm", Qt.Key_Tab)
A.esperar(1500)

# ✕ en Referencia: el mapa se apaga; al volver a elegirla, vuelve
p.widgets["referencia"].borrar.click()
A.esperar(600)
A.reg(AR, "quitar la referencia apaga el mapa", a not in vis.mallas_analisis, str(list(vis.mallas_analisis)))
A.elegir(p, "referencia", A.hit_cuerpo(v, b))
A.esperar(1500)
A.reg(AR, "volver a elegirla lo pinta de nuevo", a in vis.mallas_analisis, "")

# valor bajo el cursor: se pasa por la pared del agujero corrido
centro = np.array([-45.0, 0.0, 6.0])
pantalla, delante = vis.puntos_pantalla(centro.reshape(1, 3))
A.reg(AR, "el punto de prueba se ve", bool(delante[0]), str(pantalla))
mover(vis, QPoint(int(pantalla[0, 0]), int(pantalla[0, 1])))
A.esperar(300)
leyenda = p.widgets["cursor"].findChild(type(p.widgets["extremos"])).text()
A.reg(AR, "en la pared corrida el cursor lee cerca de 1 mm", "Bajo el cursor" in leyenda and "mm" in leyenda
      and abs(abs(float(leyenda.split(":")[1].split()[0].replace(",", "."))) - 1) < 0.15, leyenda)
A.foto(v, "mapa_desviacion_cursor")

# Aceptar: queda en la carpeta Análisis y sigue pintado
p.aceptar()
A.esperar(600)
nombres = [n for n, x in s.doc.analisis.items() if x["tipo"] == "desviacion"]
A.reg(AR, "Aceptar lo guarda en Análisis", nombres == ["Desviación1"], str(nombres))
A.reg(AR, "guardado sigue pintado", a in vis.mallas_analisis, "")
A.reg(AR, "guarda cuerpo, referencia y tolerancia", s.doc.analisis["Desviación1"]["params"]["referencia"] == b, "")

# ventana chica: el panel entero entra
v.resize(800, 520)
A.esperar(300)
p = A.abrir(v, "mapa_desviacion")
A.foto(v, "mapa_desviacion_chica")
A.reg(AR, "a 800×520 el panel entra en el visor", v.area.rect().contains(p.geometry()), str(p.geometry().getRect()))
QTest.keyClick(p, Qt.Key_Escape)
A.esperar(200)
A.reg(AR, "ninguna excepción escapó de un slot de Qt", not A.ERRORES, str(A.ERRORES[:1]))
A.guardar_registro("mapa_desviacion")
fallas = [r for r in A.REGISTRO if not r["ok"]]
print(f"\n=== {len(A.REGISTRO)} comprobaciones, {len(fallas)} con ✗ ===")
v.close()
sys.exit(0)

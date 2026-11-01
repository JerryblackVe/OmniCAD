# -*- coding: utf-8 -*-
"""BOCETO › Administrar proyecciones perdidas con «Atenuar el resto» (ayuda de Fusion: Project geometry onto a sketch
plane, Tips): en un boceto con un rectángulo suelto y una proyección marcada como perdida se abre el diálogo, se elige la
proyección con un clic en la lista, se tilda la casilla con el mouse y se mira que lo demás del lienzo quede apagado y la
proyección siga a color; al destildar o cerrar todo vuelve a su color. También en ventana chica (1024x640 y 800x520).
B-110: una cara con arcos que cambia de forma deja UNA proyección perdida y su marca en el navegador; repetir la proyección
no apila nada, terminar y reabrir el boceto tampoco, y la marca se va al tratarla con clics en el diálogo."""
import sys

import arnes as A
import numpy as np
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QImage
from PySide6.QtTest import QTest

from omnicad import api
from omnicad.ui import dialogos_boceto
from omnicad.ui.editor_boceto import VIOLETA

AR = "PERDIDAS·ATENUAR"
s = api.Sesion()


def L(nombre, **a):
    r = api.llamar(s, nombre, a)
    assert r["ok"], (nombre, a, r)
    return r["result"]


L("create_box", length=10, width=8, height=10)
L("create_sketch", name="S", plane="XY")
L("draw_rectangle", sketch="S", x1=-10, y1=-6, x2=10, y2=6)          # lo suelto, rodea la proyección: se tiene que apagar
L("project_to_sketch", sketch="S", bodies=["op1.c1"])
L("create_sketch", name="Perfil", plane="XY")                         # B-110: otra pieza, con arcos, lejos de la primera
L("draw_arc", sketch="Perfil", start_x=240, start_y=0, mid_x=200, mid_y=40, end_x=160, end_y=0)
L("draw_arc", sketch="Perfil", start_x=220, start_y=0, mid_x=200, mid_y=20, end_x=180, end_y=0)
L("draw_line", sketch="Perfil", start_x=160, start_y=0, end_x=180, end_y=0)
L("draw_line", sketch="Perfil", start_x=220, start_y=0, end_x=240, end_y=0)
L("extrude", sketch="Perfil", profile=0, distance=10)
pieza = L("get_scene_info")["bodies"][-1]["id"]
L("create_sketch", name="Sobre", plane=">Z", body=pieza, project_edges=True)
app, v = A.iniciar(s.doc)
v.editar_operacion(s.paso("S").id)
A.esperar(500)
lz = v.modo_boceto.lienzo
v.visor.encuadrar()
A.esperar(300)
registro = lz.b.proyecciones[0]
lz.perdidas = [registro["id"]]              # lo que el modo marca al recalcular cuando el vínculo se pierde


def imagen():
    a = v.grab().toImage().convertToFormat(QImage.Format_RGB888)
    arr = np.frombuffer(a.constBits(), np.uint8).reshape(a.height(), a.bytesPerLine())[:, :a.width() * 3]
    return arr.reshape(a.height(), a.width(), 3).astype(int)


def contar(color, tol=60):
    """Píxeles del lienzo cercanos a `color` (r, g, b)."""
    return int((np.abs(imagen() - np.array(color)).sum(axis=2) < tol).sum())


def contraste():
    """Cuánto se despega del fondo la línea de arriba del rectángulo suelto (en px de la pantalla: ~0 si está apagada)."""
    arr = imagen()
    q = lz.mapTo(v, lz.a_px(6, 6).toPoint())                  # lejos del glifo de restricción del medio
    franja = arr[q.y() - 3:q.y() + 4, q.x() - 20:q.x() + 20]
    fondo = arr[q.y() - 18, q.x() - 20:q.x() + 20]
    return int(np.abs(franja - fondo[None]).sum(axis=2).max())


violeta = (VIOLETA.red(), VIOLETA.green(), VIOLETA.blue())
CELESTE = (0, 180, 255)                                   # lo elegido en el lienzo: la proyección que se marcó en la lista

normal_azul, normal_violeta = contraste(), contar(violeta)
A.foto(v, "perdidas_atenuar_normal")
A.reg(AR, "antes de abrir: se ve la geometría suelta y la proyección", normal_azul > 150 and normal_violeta > 20,
      f"{normal_azul} de contraste, {normal_violeta} violetas")

d = dialogos_boceto.DialogoPerdidas(lz)
d.show()
A.esperar(200)
A.reg(AR, "el diálogo trae «Atenuar el resto», apagada por defecto", d.atenuar.text() == "Atenuar el resto" and not d.atenuar.isChecked()
      and lz._brillantes is None, "")
QTest.mouseClick(d.lista.viewport(), Qt.LeftButton, Qt.NoModifier, d.lista.visualItemRect(d.lista.item(0)).center())
A.esperar(150)
QTest.mouseClick(d.atenuar, Qt.LeftButton, Qt.NoModifier, QPoint(8, d.atenuar.height() // 2))
A.esperar(300)
A.foto(v, "perdidas_atenuar_activa")
con_azul, con_celeste = contraste(), contar(CELESTE)
A.reg(AR, "con la casilla: lo suelto queda apagado y la proyección perdida elegida sigue a color",
      d.atenuar.isChecked() and con_azul < normal_azul * 0.45 and con_celeste > 20,
      f"contraste {normal_azul} → {con_azul}; celeste {con_celeste}")

QTest.mouseClick(d.atenuar, Qt.LeftButton, Qt.NoModifier, QPoint(8, d.atenuar.height() // 2))
A.esperar(300)
A.reg(AR, "al destildar la geometría suelta vuelve a su color", contraste() > normal_azul * 0.9, f"{contraste()} de contraste")

QTest.mouseClick(d.atenuar, Qt.LeftButton, Qt.NoModifier, QPoint(8, d.atenuar.height() // 2))
A.esperar(200)
d.reject()
A.esperar(300)
A.reg(AR, "al cerrar el diálogo con la casilla tildada el lienzo vuelve a lo normal",
      lz._brillantes is None and contraste() > normal_azul * 0.9, f"{contraste()} de contraste")

for ancho, alto in ((1024, 640), (800, 520)):
    n_err = len(A.ERRORES)
    v.resize(ancho, alto)
    A.esperar(500)
    d = dialogos_boceto.DialogoPerdidas(lz)
    d.show()
    A.esperar(250)
    d.atenuar.setChecked(True)
    A.esperar(250)
    A.foto(v, f"perdidas_atenuar_{ancho}x{alto}")
    entra = d.width() <= ancho and d.height() <= alto and d.atenuar.isVisible() and d.b_borrar_todos.isVisible()
    A.reg(AR, f"{ancho}x{alto}: el diálogo con la casilla entra en la ventana", entra and len(A.ERRORES) == n_err,
          f"diálogo {d.width()}x{d.height()}")
    d.reject()
    A.esperar(150)

# ---------------------------------------------------------------- B-110: la cara cambia de verdad
v.modo_boceto.terminar()
A.esperar(300)
sobre = s.paso("Sobre")


def perdidas_y_registros():
    return len(L("get_sketch", sketch="Sobre")["projections"]), [p["id"] for p in L("get_sketch", sketch="Sobre")["projections"] if p["lost"]]


def marca():
    v._refrescar_visibilidad()
    return v.navegador.estados.get(sobre.id)


for _ in range(2):
    L("project_to_sketch", faces=">Z", body=pieza, sketch="Sobre")
A.reg(AR, "B-110: proyectar otra vez lo mismo no apila nada ni marca el boceto", perdidas_y_registros() == (1, []) and marca() is None,
      str(perdidas_y_registros()))
geo_perfil = L("get_sketch", sketch="Perfil")["entities"]
L("sketch_fillet", sketch="Perfil", radius=2, entity1=next(e["id"] for e in geo_perfil if e["type"] == "line"),
  entity2=next(e["id"] for e in geo_perfil if e["type"] == "arc"))
A.esperar(400)
n, perdidas = perdidas_y_registros()
A.reg(AR, "B-110: la cara gana una arista: una proyección perdida, marcada en el navegador", n == 1 and len(perdidas) == 1 and marca() == "aviso",
      f"{n} registros, perdidas {perdidas}, marca {marca()}")
for _ in range(2):
    L("project_to_sketch", faces=">Z", body=pieza, sketch="Sobre")
for _ in range(2):
    v.editar_operacion(sobre.id)
    A.esperar(400)
    v.modo_boceto.terminar()
    A.esperar(300)
A.reg(AR, "B-110: reproyectar dos veces, terminar y reabrir dos veces deja 2 registros y la misma perdida",
      perdidas_y_registros() == (2, perdidas), str(perdidas_y_registros()))
v.editar_operacion(sobre.id)
A.esperar(400)
lz = v.modo_boceto.lienzo
d = dialogos_boceto.DialogoPerdidas(lz)
d.show()
A.esperar(200)
A.foto(v, "perdidas_b110_dialogo")
QTest.mouseClick(d.lista.viewport(), Qt.LeftButton, Qt.NoModifier, d.lista.visualItemRect(d.lista.item(0)).center())
A.esperar(150)
QTest.mouseClick(d.b_romper, Qt.LeftButton)
A.esperar(300)
A.reg(AR, "B-110: «Romper vínculo» con clics vacía la lista del diálogo", d.lista.count() == 0, f"{d.lista.count()} filas")
d.reject()
v.modo_boceto.terminar()
A.esperar(400)
A.reg(AR, "B-110: tratada la perdida, se va la marca del navegador", perdidas_y_registros()[1] == [] and marca() is None,
      f"{perdidas_y_registros()}, marca {marca()}")

A.reg(AR, "ninguna excepción escapó de un slot de Qt", not A.ERRORES, str(A.ERRORES[:1]))
A.guardar_registro("perdidas_atenuar")
fallas = [r for r in A.REGISTRO if not r["ok"]]
print(f"\n=== {len(A.REGISTRO)} comprobaciones, {len(fallas)} con ✗ ===")
v.close()
sys.exit(0)

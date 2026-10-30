# -*- coding: utf-8 -*-
"""BOCETO › Administrar proyecciones perdidas con «Atenuar el resto» (ayuda de Fusion: Project geometry onto a sketch
plane, Tips): en un boceto con un rectángulo suelto y una proyección marcada como perdida se abre el diálogo, se elige la
proyección con un clic en la lista, se tilda la casilla con el mouse y se mira que lo demás del lienzo quede apagado y la
proyección siga a color; al destildar o cerrar todo vuelve a su color. También en ventana chica (1024x640 y 800x520)."""
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

A.reg(AR, "ninguna excepción escapó de un slot de Qt", not A.ERRORES, str(A.ERRORES[:1]))
A.guardar_registro("perdidas_atenuar")
fallas = [r for r in A.REGISTRO if not r["ok"]]
print(f"\n=== {len(A.REGISTRO)} comprobaciones, {len(fallas)} con ✗ ===")
v.close()
sys.exit(0)

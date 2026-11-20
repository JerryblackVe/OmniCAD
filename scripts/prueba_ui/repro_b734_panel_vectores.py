# -*- coding: utf-8 -*-
"""B-734 (E7): clic en un texto de un boceto desde la vista 3D (fuera del boceto): ¿el panel «Objetos vectoriales y texto» queda
abierto vacío? Eventos simulados al visor; nunca el cursor real."""
import sys

import arnes as A
import numpy as np
from omnicad import api
from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication

AR = "REPRO·B734"
s = api.Sesion()
api.llamar(s, "create_sketch", {"name": "N", "plane": "XY"})
api.llamar(s, "add_text", {"sketch": "N", "text": "Rochi", "x": 0, "y": 0, "height": 12})
op = s.paso("N").id
app, v = A.iniciar(s.doc)
A.esperar(500)
v.visor.vista("arriba")
v.visor.encuadrar()
A.esperar(400)


def clic(px):
    q = QPoint(round(px[0]), round(px[1]))
    for t, b, bs in ((QEvent.MouseMove, Qt.NoButton, Qt.NoButton), (QEvent.MouseButtonPress, Qt.LeftButton, Qt.LeftButton),
                     (QEvent.MouseButtonRelease, Qt.LeftButton, Qt.NoButton)):
        QApplication.sendEvent(v.visor, QMouseEvent(t, QPointF(q), QPointF(v.visor.mapToGlobal(q)), b, bs, Qt.NoModifier))
        A.esperar(80)
    A.esperar(200)


br = v.doc.estado_final.bocetos[op]
for u in (6, 12, 18):                                   # sobre las letras
    px = v.visor.puntos_pantalla(np.array([br.plano.a_3d(u, 4)], float))[0][0]
    clic(px)
    lz = v.vectores.activo
    pan = lz.objetos.panel if lz is not None else None
    visible = pan is not None and pan.isVisible()
    print(f"   clic u={u}: capa activa={lz is not None}, panel visible={visible}, selección={getattr(lz, 'seleccion', None)}")
    if visible:
        break
clic(v.visor.puntos_pantalla(np.array([br.plano.a_3d(90, 60)], float))[0][0])           # clic en el vacío
lz = v.vectores.activo
vacio = lz is not None and lz.objetos.panel.isVisible() and not lz.seleccion
print(f"   clic en el vacío: capa activa={lz is not None}, panel visible={lz is not None and lz.objetos.panel.isVisible()}, selección={getattr(lz, 'seleccion', None)}")
A.reg(AR, "B-734 · un clic en el vacío cierra el panel (no lo deja abierto sin selección)", not vacio, f"panel abierto y vacío={vacio}")
A.reg(AR, "ninguna excepción en un slot de Qt", not A.ERRORES, A.ERRORES[:1])
A.guardar_registro("repro_b734_panel_vectores")
v.doc.modificado = False
v.close()
sys.exit(0)

# -*- coding: utf-8 -*-
"""BOCETO · Deshacer y Rehacer como los usa una persona (Ctrl+Z / Ctrl+Y / botones) en un boceto NUEVO sobre un documento
vacío, dentro de un boceto que ya está en el timeline, y después de terminar el boceto (deshacer del documento)."""
import sys

import arnes as A
from omnicad import api
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

AR = "UNDO"
s = api.Sesion()
app, v = A.iniciar(s.doc)


def tecla(w, k, mod=Qt.NoModifier):
    QTest.keyClick(w, k, mod)
    A.esperar(120)


def entrar_nuevo():
    hit = A.hit_plano(v, "XY")
    v._iniciar_boceto(v._boceto_nuevo(hit["plano"], None), hit["plano"],
                      {"op": None, "plano": hit["ref"], "marco": hit["plano"].marco(), "cara": None})
    A.esperar(400)
    return v.modo_boceto.lienzo


lz = entrar_nuevo()
A.reg(AR, "boceto nuevo en documento vacío", lz is not None and not s.doc.puede_deshacer(), f"doc.puede_deshacer={s.doc.puede_deshacer()}")
v.visor.encuadrar()


def px(x, y):
    return lz.a_px(x, y).toPoint()


def linea(x1, y1, x2, y2):
    lz.set_herramienta("linea")
    QTest.mouseClick(lz, Qt.LeftButton, Qt.NoModifier, px(x1, y1))
    A.esperar(60)
    QTest.mouseClick(lz, Qt.LeftButton, Qt.NoModifier, px(x2, y2))
    A.esperar(120)
    QTest.keyClick(lz, Qt.Key_Escape)
    A.esperar(60)


linea(0, 0, 20, 5)
linea(0, 10, 20, 15)
n = len(lz.b.curvas)
A.reg(AR, "dos líneas dibujadas con el mouse", n == 2, f"{n}")
A.reg(AR, "el botón/atajo Deshacer está habilitado dentro del boceto", v.acciones["deshacer"].isEnabled(),
      f"habilitado={v.acciones['deshacer'].isEnabled()}")
tecla(lz, Qt.Key_Z, Qt.ControlModifier)
A.reg(AR, "Ctrl+Z quita la segunda línea (boceto nuevo, documento vacío)", len(lz.b.curvas) == 1, f"{len(lz.b.curvas)}")
A.reg(AR, "el botón Rehacer se habilita dentro del boceto", v.acciones["rehacer"].isEnabled(),
      f"habilitado={v.acciones['rehacer'].isEnabled()}")
tecla(lz, Qt.Key_Y, Qt.ControlModifier)
A.reg(AR, "Ctrl+Y la vuelve", len(lz.b.curvas) == 2, f"{len(lz.b.curvas)}")
tecla(lz, Qt.Key_Z, Qt.ControlModifier)
tecla(lz, Qt.Key_Z, Qt.ControlModifier)
A.reg(AR, "dos Ctrl+Z dejan el boceto vacío", len(lz.b.curvas) == 0, f"{len(lz.b.curvas)}")
tecla(lz, Qt.Key_Y, Qt.ControlModifier)
tecla(lz, Qt.Key_Y, Qt.ControlModifier)
A.reg(AR, "dos Ctrl+Y las traen de nuevo", len(lz.b.curvas) == 2, f"{len(lz.b.curvas)}")
# una restricción puesta con la herramienta, borrada con Supr y deshecha
def n_par():
    return sum(1 for r in lz.b.restricciones.values() if r.tipo == "paralela")


lz.set_herramienta("r_paralela")
for xy in ((10, 2.5), (10, 12.5)):
    QTest.mouseClick(lz, Qt.LeftButton, Qt.NoModifier, px(*xy))
    A.esperar(80)
A.reg(AR, "la herramienta Paralela agrega la restricción", n_par() == 1, f"{n_par()}")
lz.set_herramienta("seleccionar")
rid = next(r.id for r in lz.b.restricciones.values() if r.tipo == "paralela")
h0 = len(lz.historial)
lz.seleccion = [rid]
tecla(lz, Qt.Key_Delete)
A.reg(AR, "Supr borra la restricción elegida", n_par() == 0, f"{n_par()} historial {h0}->{len(lz.historial)}")
tecla(lz, Qt.Key_Z, Qt.ControlModifier)
A.reg(AR, "Ctrl+Z devuelve la restricción borrada con Supr", n_par() == 1, f"{n_par()} historial={len(lz.historial)}")
tecla(lz, Qt.Key_Y, Qt.ControlModifier)
A.reg(AR, "Ctrl+Y la vuelve a borrar", n_par() == 0, f"{n_par()}")
tecla(lz, Qt.Key_Z, Qt.ControlModifier)
# terminar el boceto: queda UN paso del timeline; Ctrl+Z del documento lo quita entero
v.modo_boceto.terminar()
A.esperar(400)
A.reg(AR, "al terminar queda un paso en el timeline", len(s.doc.operaciones) == 1, f"{len(s.doc.operaciones)}")
tecla(v, Qt.Key_Z, Qt.ControlModifier)
A.reg(AR, "Ctrl+Z del documento quita el boceto entero", len(s.doc.operaciones) == 0, f"{len(s.doc.operaciones)}")
tecla(v, Qt.Key_Y, Qt.ControlModifier)
A.reg(AR, "Ctrl+Y del documento lo trae de vuelta", len(s.doc.operaciones) == 1, f"{len(s.doc.operaciones)}")
A.reg(AR, "sin excepciones sueltas en slots de Qt", not A.ERRORES, "; ".join(A.ERRORES)[:300])
A.guardar_registro("auditoria_undo")
fallas = [r for r in A.REGISTRO if not r["ok"]]
print(f"=== {len(A.REGISTRO)} comprobaciones, {len(fallas)} con ✗", flush=True)
v.close()
sys.exit(0)

# -*- coding: utf-8 -*-
"""Capturas de RENDERIZAR › Aspecto (panel, caras, selector rápido y Editor de materiales) con OpenGL real.

Uso desde clon/ (con turno, abre ventanas):  python ../scripts/capturar_aspecto_render.py carpeta_destino
Arma un documento nuevo (caja + cilindro), no toca ningún archivo del usuario y usa un archivo de «Mis aspectos» temporal.
"""
import os
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "clon"))
os.environ["QT_QPA_PLATFORM"] = "windows"
os.environ["OMNICAD_ASPECTOS"] = str(Path(tempfile.mkdtemp(prefix="omnicad_aspectos_")) / "aspectos.json")

from PySide6.QtGui import QSurfaceFormat
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

formato = QSurfaceFormat()
formato.setDepthBufferSize(24)
formato.setStencilBufferSize(8)
formato.setSamples(4)
QSurfaceFormat.setDefaultFormat(formato)
app = QApplication([])

from omnicad import api
from omnicad.api import selectores as sl
from omnicad.timeline import aspectos_doc as ad
from omnicad.ui.render import VentanaRender


def _foto(widget, ruta):
    """Captura de pantalla real (incluye el OpenGL y las ventanas emergentes)."""
    QApplication.primaryScreen().grabWindow(int(widget.winId())).save(str(ruta))


destino = Path(sys.argv[1]).resolve()
destino.mkdir(parents=True, exist_ok=True)
s = api.Sesion()
assert api.llamar(s, "create_box", {"length": 100, "width": 60, "height": 20})["ok"]
assert api.llamar(s, "create_cylinder", {"height": 30, "radius": 10, "x": 90})["ok"]
caja, cilindro = list(s.doc.estado_final.cuerpos)
v = VentanaRender(s.doc)
v.resize(1400, 900)
v.show()
QTest.qWait(600)
v.lienzo.encuadrar()
(c, e), = sl.elegir(s, ">Z", "cara", caja)
v.aplicar_aspecto("Pintura - Metalizada (Azul)", [caja])
v.aplicar_aspecto("Latón - Pulido", [cilindro])
v.aplicar_aspecto("Pintura - Brillante (Rojo)", caras=[(caja, sl.referencia(c, e))])
v.mostrar_aspecto()
QTest.qWait(400)
pa = v.panel_aspecto
pa._seleccionar("Oro - Pulido")
QTest.qWait(300)
_foto(v, destino / "render_aspecto_ventana.png")
pa.radios.r_caras.setChecked(True)
QTest.qWait(200)
_foto(v, destino / "render_aspecto_modo_caras.png")
aid = ad.lista(s.doc)[1]["id"]                                  # el latón, para editarlo
selector = pa.aspectos.editar(aid)
QTest.qWait(300)
selector.cambiado.emit({"color": [0.2, 0.55, 0.3]})            # como mover el espectro: se ve en el lienzo sin escribir
QTest.qWait(300)
_foto(selector, destino / "render_aspecto_selector_rapido.png")
_foto(v, destino / "render_aspecto_vista_previa.png")
selector.avanzada.emit()
QTest.qWait(400)
_foto(pa.aspectos.editor, destino / "render_aspecto_editor_materiales.png")
pa.aspectos.editor.close()
s.doc.modificado = False
v.close()
print("listo:", destino)

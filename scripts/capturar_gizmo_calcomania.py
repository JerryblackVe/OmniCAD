"""Captura reproducible del gizmo sobre el abanico de ejemplo, sin cambiar el archivo original.

Uso desde clon/: python ../scripts/capturar_gizmo_calcomania.py modelo.omnicad carpeta_destino
"""
import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "clon"))
os.environ["QT_QPA_PLATFORM"] = "windows"

from PIL import Image, ImageDraw
from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QSurfaceFormat
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

formato = QSurfaceFormat()
formato.setDepthBufferSize(24)
formato.setStencilBufferSize(8)
QSurfaceFormat.setDefaultFormat(formato)
app = QApplication([])

from omnicad import api
from omnicad.io_archivos import proyecto
from omnicad.ui.preferencias import Preferencias
from omnicad.ui.ventana import VentanaPrincipal

destino = Path(sys.argv[2]).resolve()
destino.mkdir(parents=True, exist_ok=True)
s = api.Sesion(proyecto.abrir(sys.argv[1]))
caras = api.llamar(s, "find_faces", {"selector": "+Z"})
assert caras["ok"], caras
cara = max(caras["result"]["faces"], key=lambda f: f["area"])
imagen = destino / "imagen_ejemplo.png"
img = Image.new("RGB", (800, 400), "white")
dibujo = ImageDraw.Draw(img)
dibujo.ellipse((80, 95, 270, 285), outline="#b75294", width=8)
dibujo.text((112, 168), "OmniCAD", fill="#333333", font_size=24)
dibujo.text((480, 160), "CALCOMANIA", fill="#333333", font_size=24)
img.save(imagen)
resultado = api.llamar(s, "set_decal", {"image": str(imagen), "face": cara["id"], "width": 420})
assert resultado["ok"], resultado
prefs = Preferencias(QSettings(str(destino / "prefs.ini"), QSettings.IniFormat))
v = VentanaPrincipal(s.doc, prefs=prefs)
v.resize(1500, 950)
v.show()
QTest.qWait(400)
v.visor.vista("arriba")
v.visor.encuadrar()
v.editar_operacion(resultado["result"]["feature"]["id"])
v.panel._calcular_previa()
QTest.qWait(400)
assert v.panel._previa_ok
g = v.panel.manipuladores
assert len(g.manips) == 7
assert v.grab().save(str(destino / "abanico_gizmo.png"))
assert v.visor.grab().save(str(destino / "visor_gizmo.png"))
centro = g.pantalla([g.manips[0].punto])[0][0]
detalle = v.visor.grab().copy(int(centro[0]) - 140, int(centro[1]) - 115, 315, 205)
assert detalle.scaledToWidth(945, Qt.SmoothTransformation).save(str(destino / "detalle_gizmo.png"))
print(destino / "abanico_gizmo.png")
v.panel.cancelar()
v.doc.modificado = False
v.close()

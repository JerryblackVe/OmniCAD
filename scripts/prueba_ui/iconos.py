# -*- coding: utf-8 -*-
"""Íconos como los ve una persona (docs/plan_iconos.md, F5): el timeline, el navegador y la cinta con el documento del dron
(si no está en el disco, un documento armado por la API) en 1920×1080, 1024×640 y 800×520, con tema oscuro y claro y el cambio
de tema EN VIVO (sin reiniciar). Deja una captura de cada zona y la hoja de la prueba de identificación: 20 pasos al azar,
solo el ícono (sin tooltip). Quien mira escribe sus respuestas en `identificacion_respuestas.json` ({"1": "extruir", ...};
el nombre del dibujo o la etiqueta del paso) y la pieza las corrige contra `identificacion_verdad.json` (meta: 18 de 20)."""
import json
import random
import sys
from pathlib import Path

import arnes as A
import escena
from omnicad import api
from omnicad.ui import temas
from omnicad.ui.panel_timeline import COLORES, icono_operacion
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QImage, QPainter

AR = "ÍCONOS"
DRON = Path(r"C:\Users\mosos\Desktop\f3z\Dron_A1_76mm_prototipo_v01.omnicad")
TAMANOS = [(1920, 1080), (1024, 640), (800, 520)]
TEMAS = ["oscuro_moderno", "claro_moderno"]
N_IDENTIFICAR = 20
SEMILLA = 7

s = api.Sesion()
if DRON.exists():
    A.reg(AR, "abrir el dron real", api.llamar(s, "open_document", {"path": str(DRON)})["ok"], DRON.name)
else:
    s, _ids = escena.construir()
    A.reg(AR, "el dron no está en el disco: se usa la escena de prueba de la API", True, "documento equivalente, no el dron")
app, v = A.iniciar(s.doc, *TAMANOS[0])
ops = v.doc.operaciones
bytes_icono = lambda i: bytes(v.timeline.lista.item(i).icon().pixmap(24, 24).toImage().constBits())  # noqa: E731


def zona(nombre, widget, w, h, tema):
    ruta = A.CAPTURAS / f"iconos_{w}x{h}_{tema}_{nombre}.png"
    widget.grab().save(str(ruta))
    return ruta


for w, h in TAMANOS:
    v.resize(w, h)
    A.esperar(500)
    for tema in TEMAS:
        n_err = len(A.ERRORES)
        v.aplicar_tema(tema)                      # con la ventana abierta: es el cambio «en vivo»
        A.esperar(600)
        A.foto(v, f"iconos_{w}x{h}_{tema}")
        for nombre, widget in (("timeline", v.timeline), ("navegador", v.navegador), ("cinta", v.cinta)):
            zona(nombre, widget, w, h, tema)
        lista = v.timeline.lista
        en_blanco = [i for i in range(lista.count()) if lista.item(i).data(Qt.UserRole) in {o.id for o in ops}
                     and not any(lista.item(i).icon().pixmap(24, 24).toImage().pixelColor(x, y).alpha()
                                 for x in range(24) for y in range(24))]
        A.reg(AR, f"{w}×{h} {tema}: ventana de {v.width()}×{v.height()}, timeline visible con {lista.count()} filas",
              v.timeline.isVisible() and lista.count() >= len(ops))
        A.reg(AR, f"{w}×{h} {tema}: todos los íconos del timeline se dibujan", not en_blanco, f"en blanco: {en_blanco[:5]}")
        A.reg(AR, f"{w}×{h} {tema}: ninguna excepción", len(A.ERRORES) == n_err)

# cambio de tema en vivo: el boceto (trazo gris oscuro) tiene que verse distinto sobre cada fondo
v.aplicar_tema("claro_moderno")
A.esperar(500)
claro = bytes_icono(0)
v.aplicar_tema("oscuro_moderno")
A.esperar(500)
A.reg(AR, "cambiar de tema con la ventana abierta repinta el ícono del primer paso", bytes_icono(0) != claro)
v.aplicar_tema("claro_moderno")
A.esperar(500)
A.reg(AR, "y al volver al claro queda igual que antes", bytes_icono(0) == claro)

# ---- prueba de identificación: solo el ícono, sin tooltip
azar = random.Random(SEMILLA)
elegidos = azar.sample(range(len(ops)), min(N_IDENTIFICAR, len(ops)))
fondo = QColor(temas.activo()["fondo"])
hoja = QImage(5 * 84 + 8, 4 * 72 + 8, QImage.Format_ARGB32)
hoja.fill(QColor(temas.activo()["panel"]))
p = QPainter(hoja)
p.setRenderHint(QPainter.TextAntialiasing)
fuente = QFont("Segoe UI")
fuente.setPixelSize(12)
p.setFont(fuente)
verdad = {}
for k, i in enumerate(elegidos, start=1):
    op, res = ops[i], v.doc.resultados[i]
    x, y = 8 + ((k - 1) % 5) * 84, 8 + ((k - 1) // 5) * 72
    p.fillRect(QRectF(x, y + 18, 40, 40), COLORES.get(res.estado, fondo))
    p.setPen(QColor(temas.activo()["texto"]))
    p.drawText(QRectF(x, y, 60, 16), Qt.AlignLeft, str(k))
    p.drawPixmap(x + 8, y + 26, v.timeline.lista.item(i + (1 if i >= v.doc.marcador else 0)).icon().pixmap(24, 24))
    verdad[str(k)] = {"paso": op.id, "dibujo": icono_operacion(op), "etiqueta": op.ETIQUETA,
                      "operacion": op.p.get("operacion"), "estado": res.estado}
p.end()
hoja.save(str(A.CAPTURAS / "iconos_identificacion.png"))
(A.SALIDA / "identificacion_verdad.json").write_text(json.dumps(verdad, ensure_ascii=False, indent=1), encoding="utf-8")
A.reg(AR, f"hoja de identificación de {len(elegidos)} pasos (semilla {SEMILLA})", True,
      f"{len({d['dibujo'] for d in verdad.values()})} dibujos distintos entre los elegidos")
respuestas = A.SALIDA / "identificacion_respuestas.json"
if respuestas.exists():
    dadas = json.loads(respuestas.read_text(encoding="utf-8"))
    bien = [k for k, d in verdad.items() if str(dadas.get(k, "")).strip().lower() in (d["dibujo"], d["etiqueta"].lower())]
    A.reg(AR, f"identificación sin tooltip: {len(bien)} de {len(verdad)} (meta 18)", len(bien) >= 18,
          f"falló: {[(k, dadas.get(k), verdad[k]['dibujo']) for k in verdad if k not in bien]}")

A.guardar_registro("iconos")
fallas = [r for r in A.REGISTRO if not r["ok"]]
print(f"\n=== {len(A.REGISTRO)} comprobaciones, {len(fallas)} con ✗ ===")
v.doc.modificado = False
v.close()
sys.exit(0)

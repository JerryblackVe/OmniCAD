# -*- coding: utf-8 -*-
"""AUDITORÍA UX del boceto (E7, regla 14): recorre cada comando de la cinta del boceto y anota cuántas tarjetas quedan abiertas a la
vez (panel de comando, tarjeta de herramienta, paleta, barra, panel de vectores…) y qué campos se repiten entre ellas. Solo mira y
cuenta: no arregla. Eventos simulados; nunca el cursor real. Salida: tabla en `evidencias/auditoria_ux_boceto/`."""
import json
import sys
from pathlib import Path

import arnes as A
from omnicad import api
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QAbstractButton, QApplication, QComboBox, QLabel, QToolButton, QWidget

s = api.Sesion()
L = lambda n, **a: api.llamar(s, n, a)["result"]            # noqa: E731
L("create_box", length=40, width=20, height=5, name="Caja")
L("create_sketch", name="B", plane="XY")
c1 = L("draw_circle", sketch="B", center_x=0, center_y=0, radius=8)["entities"][0]["id"]
L("draw_line", sketch="B", start_x=20, start_y=-10, end_x=40, end_y=10)
L("draw_line", sketch="B", start_x=20, start_y=10, end_x=40, end_y=-10)
L("draw_rectangle", sketch="B", center_x=-30, center_y=0, width=20, height=14)
L("add_text", sketch="B", text="Hola", x=0, y=-30, height=8)
ID = s.paso("B").id
app, v = A.iniciar(s.doc)
A.esperar(400)
v.editar_operacion(ID)
A.esperar(600)
mb = v.modo_boceto
lz = mb.lienzo
lz.visor.objetivo = lz.plano.a_3d(0, 0)
lz.visor.update(); lz.update()
A.activar(v); A.esperar(300)


def tarjetas():
    """Tarjetas visibles sobre el visor: hijos directos del área, más ventanas sueltas, más el panel de vectores."""
    area = v.area
    out = []
    for w in area.findChildren(QWidget, options=Qt.FindDirectChildrenOnly):
        if w is v.visor or not w.isVisible() or w.width() < 40 or w.height() < 20:
            continue
        out.append(w)
    for w in QApplication.topLevelWidgets():
        if w is not v and w.isVisible() and type(w).__name__ not in ("QMenu", "QTipLabel", "VentanaPrincipal") and w.width() > 40:
            out.append(w)
    return out


def campos(w):
    """Etiquetas de los campos de la tarjeta: texto de cada QLabel que acompaña un campo editable, o el del propio botón."""
    ets = []
    for lab in w.findChildren(QLabel):
        t = lab.text().strip().rstrip(":").lower()
        if lab.isVisible() and 0 < len(t) < 30 and not t.startswith("<"):
            ets.append(t)
    for b in w.findChildren(QAbstractButton):          # casillas, botones y opciones también cuentan como campos
        t = b.text().replace("&", "").strip().lower()
        if b.isVisible() and 0 < len(t) < 30:
            ets.append(t)
    for cb in w.findChildren(QComboBox):
        if cb.isVisible():
            ets.append("combo:" + cb.currentText().strip().lower())
    return ets


def foto(clave):
    ts = tarjetas()
    return {"clave": clave, "tarjetas": [type(w).__name__ for w in ts], "campos": {type(w).__name__: campos(w) for w in ts}}


def reiniciar():
    lz.set_herramienta("seleccionar"); lz.seleccion = []
    for _ in range(2):
        A.activar(v); A.esperar(80)
        QTest.keyClick(lz, Qt.Key_Escape); A.esperar(120)
    for w in QApplication.topLevelWidgets():
        if w.isVisible() and type(w).__name__ in ("QDialog", "DialogoAutoRestringir"):
            w.reject()
    A.esperar(150)


def pulsar(clave):
    acc = mb.acciones[clave]
    b = next((b for b in v.cinta.findChildren(QToolButton) if b.defaultAction() is acc and b.isVisible()), None)
    if acc.isEnabled():
        QTest.mouseClick(b, Qt.LeftButton) if b else acc.trigger()
    A.esperar(250)


base = foto("(ninguno)")
print("BASE", base["tarjetas"])
RES = []
import os
DESDE = os.environ.get("AUD_DESDE")
claves = [k for k in mb.acciones if (k.startswith("sk_") or k in ("configurar", "mostrar_configuracion", "proyectar")) and "terminar" not in k]  # terminar cierra el boceto
if DESDE:
    claves = claves[claves.index(DESDE):]
for clave in claves:
    reiniciar()
    if clave in ("sk_editar_patron", "sk_soltar_desfase", "sk_romper_vinculo"):
        lz.seleccion = [c1]
    try:
        pulsar(clave)
        f = foto(clave)
    except Exception as e:                                   # noqa: BLE001 - la auditoría sigue con los demás
        f = {"clave": clave, "error": f"{type(e).__name__}: {e}"}
    RES.append(f)
    print(json.dumps(f, ensure_ascii=False), flush=True)
reiniciar()
carpeta = Path(__file__).resolve().parents[2] / "evidencias" / "auditoria_ux_boceto"
carpeta.mkdir(parents=True, exist_ok=True)
(carpeta / "tarjetas.json").write_text(json.dumps({"base": base, "comandos": RES}, ensure_ascii=False, indent=1), encoding="utf-8")
A.reg("AUDITORÍA·UX", "recorrió los comandos del boceto", len(RES) >= 50, f"{len(RES)} comandos")
A.reg("AUDITORÍA·UX", "ninguna excepción en un slot de Qt", not A.ERRORES, A.ERRORES[:1])
A.guardar_registro("auditoria_ux_boceto")
v.doc.modificado = False
v.close()
sys.exit(0)

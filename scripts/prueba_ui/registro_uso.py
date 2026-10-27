"""Sesión real con teclado y clics simulados al widget; no mueve el cursor de Windows."""
import json
import os
import sys
import tempfile
from pathlib import Path

import arnes as A
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QDialog, QToolButton

from omnicad import api
from omnicad import registro_uso as ru

os.environ["OMNICAD_REGISTRO_DIR"] = tempfile.mkdtemp(prefix="omnicad_registro_ui_")
s = api.Sesion()
app, v = A.iniciar(s.doc)
v.registro_uso.configurar(True)
A.reg("REG", "indicador visible", v.registro_uso.indicador.isVisible())


def escribir(campo, texto):
    campo.setFocus()
    QTest.keyClick(campo, Qt.Key_A, Qt.ControlModifier)
    QTest.keyClicks(campo, texto)
    A.esperar(300)


# Botón de cinta real, con la misma QAction de la ventana.
boton = next(b for b in v.findChildren(QToolButton) if b.defaultAction() == v.acciones["extruir"] and b.isVisible())
QTest.mouseClick(boton, Qt.LeftButton)
A.esperar(250)
QTest.keyClick(v.panel, Qt.Key_Escape)
A.esperar(150)
v.acciones["cilindro"].trigger()
A.esperar(250)
p = v.panel
escribir(p.widgets["alto"], "35")
QTest.mouseClick(p.boton_ok, Qt.LeftButton)
A.esperar(350)
A.reg("REG", "aceptar crea el cilindro de 35 mm", len(v.doc.operaciones) == 1 and v.doc.operaciones[0].p["alto"] == "35")

# Abrir, cambiar una cota, aceptar; guardar y reabrir una pieza real.
paso = v.doc.operaciones[0].id
v.editar_operacion(paso)
A.esperar(250)
p = v.panel
escribir(p.widgets["alto"], "42 mm")
QTest.mouseClick(p.boton_ok, Qt.LeftButton)
A.esperar(250)
ruta = Path(os.environ["OMNICAD_REGISTRO_DIR"]) / "pieza.omnicad"
v._guardar_en(str(ruta))
v.abrir_ruta(str(ruta))
A.reg("REG", "pieza reabierta conserva cota 42 mm", v.doc.operaciones[0].p["alto"] == "42 mm")

v.acciones["cilindro"].trigger()
A.esperar(250)
p = v.panel
escribir(p.widgets["alto"], "-1")
A.reg("REG", "el error aparece en el panel", bool(p.mensaje.text()))
QTest.keyClick(p, Qt.Key_Escape)
A.esperar(150)
v.editar_operacion(paso)
A.esperar(200)
p = v.panel
escribir(p.widgets["alto"], "43")
QTest.mouseClick(p.boton_ok, Qt.LeftButton)
A.esperar(200)
v.activateWindow()
v.raise_()
QTest.qWaitForWindowActive(v, 2000)
QTest.keyClick(v, Qt.Key_Z, Qt.ControlModifier)
A.esperar(200)

# La prueba acepta el diálogo de marca sin captura; el atajo pasa por Qt.
anterior = QDialog.exec
QDialog.exec = lambda d: QDialog.Accepted
QTest.keyClick(v, Qt.Key_M, Qt.ControlModifier | Qt.ShiftModifier)
A.esperar(200)
QDialog.exec = anterior

ru.activo.cola.join()
vivo = api.llamar(s, "get_usage_log", {"limit": 5000})
A.reg("REG", "get_usage_log lee la sesión viva mientras la app está abierta",
      vivo["ok"] and vivo["result"]["active"] and vivo["result"]["count"] >= 20)
es = [json.loads(l) for p in sorted(ru.carpeta().glob("sesion_*.jsonl")) for l in p.read_text(encoding="utf-8").splitlines()]
for tipo in ("comando_abierto", "comando_editado", "comando_aceptado", "comando_cancelado", "op_ejecutada",
             "recalculo", "archivo_guardar", "archivo_abrir", "deshacer", "error", "marca", "atajo", "boton_cinta"):
    A.reg("REG", f"archivo crece en vivo: {tipo}", any(e["tipo"] == tipo for e in es))
v.registro_uso.configurar(False)
A.reg("REG", "indicador desaparece y reloj se detiene", not v.registro_uso.indicador.isVisible() and not v.registro_uso.reloj.isActive())
crudo = api.llamar(s, "get_usage_log", {"limit": 5000})
A.reg("REG", "la herramienta lee el archivo de la ventana en vivo",
      crudo["ok"] and crudo["result"]["count"] >= 20)
resumen = api.llamar(s, "get_usage_summary", {})
A.reg("REG", "el resumen ve el comando cilindro y los hallazgos",
      resumen["ok"] and resumen["result"]["comandos"].get("cilindro", {}).get("aceptados", 0) >= 1
      and resumen["result"]["hallazgos_por_severidad"]["alta"] >= 0)
informe = api.llamar(s, "build_usage_report", {})
ruta_informe = Path(informe["result"]["path"]) if informe["ok"] else None
texto = ruta_informe.read_text(encoding="utf-8") if ruta_informe and ruta_informe.is_file() else ""
if texto:
    (A.SALIDA / "informe_sesion.md").write_text(texto, encoding="utf-8", newline="\n")
A.reg("REG", "el informe de la sesión real queda escrito",
      bool(texto) and "Informe de sesión" in texto and "Línea de tiempo" in texto)
A.reg("REG", "el informe trae la operación, la apertura del archivo y el comando",
      "op_ejecutada" in texto and "archivo_abrir" in texto and "comando=cilindro" in texto)
A.reg("REG", "ninguna excepción de Qt", not A.ERRORES, str(A.ERRORES[:1]))
A.guardar_registro("registro_uso")
print(f"\n=== {len(A.REGISTRO)} comprobaciones, {sum(not r['ok'] for r in A.REGISTRO)} con ✗ ===")
v.doc.modificado = False
v.close()
sys.exit(int(any(not r["ok"] for r in A.REGISTRO)))

# -*- coding: utf-8 -*-
"""INSPECCIONAR › Análisis de sección con «Color de la sección» y «Mostrar rayado» (ayuda de Fusion: Create a 3D section
view): se abre el comando como una persona, se elige el plano con un clic, se cambia el color del corte (personalizado y
del componente), se tilda el rayado, se acepta y se mira que el visor pinte lo elegido, que el análisis guardado
conserve las opciones y que en una ventana chica entren el color, el rayado y los botones."""
import sys

import arnes as A
import numpy as np
from PySide6.QtGui import QImage

from omnicad import api

AR = "SECCIÓN·COLOR"
s = api.Sesion()


def L(nombre, **a):
    r = api.llamar(s, nombre, a)
    assert r["ok"], (nombre, a, r)
    return r["result"]


L("create_box", length=40, width=40, height=30)
L("create_cylinder", height=30, radius=10, x=80)
L("set_appearance", bodies=["op2.c1"], color="#2060d0")            # el cilindro azul; la caja queda con el aspecto de siempre
app, v = A.iniciar(s.doc)
vis = v.visor
vis.encuadrar()
A.esperar(300)


def contar(img, color, tol=40):
    """Píxeles de la ventana cercanos a `color` (r, g, b de 0 a 255)."""
    a = img.toImage().convertToFormat(QImage.Format_RGB888)
    arr = np.frombuffer(a.constBits(), np.uint8).reshape(a.height(), a.bytesPerLine())[:, :a.width() * 3]
    arr = arr.reshape(a.height(), a.width(), 3).astype(int)
    return int((np.abs(arr - np.array(color)).sum(axis=2) < tol).sum())


p = A.abrir(v, "seccion")
A.reg(AR, "el comando trae «Color de la sección», «Color» y «Mostrar rayado»",
      [c.clave for c in p.campos if c.clave in ("color_modo", "color", "rayado")] == ["color_modo", "color", "rayado"], "")
A.elegir(p, "plano", A.hit_plano(v, "XY"))
p.set_valor("desfase", "15 mm")
A.esperar(400)
roja = contar(v.grab(), (217, 77, 64))
A.foto(v, "seccion_color_defecto")
A.reg(AR, "por defecto la tapa sale del rojo de siempre y sin rayado", roja > 300 and not p.valores["rayado"], f"{roja} px rojos")

p.set_valor("color_modo", "componente")
A.esperar(500)
A.foto(v, "seccion_color_componente")
azul, rojo = contar(v.grab(), (32, 96, 208)), contar(v.grab(), (217, 77, 64))
A.reg(AR, "«Del componente»: el cilindro corta en azul y el botón de color se esconde",
      azul > 100 and rojo < roja * 0.3 and not p._visible(next(c for c in p.campos if c.clave == "color")),
      f"{azul} px azules, {rojo} rojos")

p.set_valor("color_modo", "personalizado")
p._cambiar("color", [0.0, 0.7, 0.2])                                # lo que deja el selector de colores al elegir un verde
A.esperar(500)
verde = contar(v.grab(), (0, 178, 51))
A.reg(AR, "«Personalizado»: toda la tapa toma el verde elegido", verde > 300, f"{verde} px verdes")

p.set_valor("rayado", True)
A.esperar(500)
A.foto(v, "seccion_color_rayado")
con_rayas = contar(v.grab(), (0, 178, 51))
A.reg(AR, "«Mostrar rayado» dibuja rayas oscuras sobre la tapa (queda menos verde a la vista)", con_rayas < verde * 0.9,
      f"{verde} → {con_rayas} px verdes")
boton = p.widgets["color"]
A.reg(AR, "el botón de color es una muestra del color elegido, sin números",
      "RGB" not in boton.text() and "#" not in boton.text() and "background" in boton.styleSheet(), boton.text())

p.aceptar()
A.esperar(300)
nombre, a = next(iter(s.doc.analisis.items()))
A.reg(AR, "Aceptar guarda color y rayado en la carpeta «Análisis»",
      a["params"].get("rayado") is True and a["params"].get("color") == [0.0, 0.7, 0.2] and a["params"].get("color_modo") == "personalizado",
      str(a["params"]))
A.foto(v, "seccion_color_aceptada")

# «Del componente» también se acepta (el botón de color queda oculto) y se guarda sin color propio
pc = A.abrir(v, "seccion")
A.elegir(pc, "plano", A.hit_plano(v, "XY"))
pc.set_valor("color_modo", "componente")
pc.aceptar()
A.esperar(300)
ultimo = list(s.doc.analisis.values())[-1]["params"]
A.reg(AR, "Aceptar en «Del componente» guarda el modo y no falla", ultimo.get("color_modo") == "componente" and not A.ERRORES, str(ultimo))
A.deshacer(v)

# guardar, cerrar y reabrir: las opciones sobreviven
ruta = str(A.SALIDA / "seccion_color.omnicad")
L("save_document", path=ruta, overwrite=True)
s2 = api.Sesion()
r = api.llamar(s2, "open_document", {"path": ruta})
p2 = next(iter(s2.doc.analisis.values()))["params"]
A.reg(AR, "guardar y reabrir conserva color y rayado", r["ok"] and p2.get("rayado") is True and p2.get("color") == [0.0, 0.7, 0.2], str(p2))

# deshacer / rehacer
A.deshacer(v)
A.reg(AR, "deshacer quita el análisis", not s.doc.analisis, "")
v.acciones["rehacer"].trigger()
A.esperar(250)
A.reg(AR, "rehacer lo vuelve con sus opciones", bool(s.doc.analisis) and next(iter(s.doc.analisis.values()))["params"].get("rayado") is True, "")

# ventana chica
for ancho, alto in ((1024, 640), (800, 520)):
    n_err = len(A.ERRORES)
    v.resize(ancho, alto)
    A.esperar(500)
    pc = A.abrir(v, "seccion")
    A.elegir(pc, "plano", A.hit_plano(v, "XY"))
    A.esperar(250)
    A.foto(v, f"seccion_color_{ancho}x{alto}")
    dentro = v.area.rect().contains(pc.geometry())
    A.reg(AR, f"{ancho}x{alto}: el panel de la sección entra en el visor", dentro and len(A.ERRORES) == n_err,
          f"panel {pc.geometry().getRect()} dentro={dentro}")
    pc.cancelar()
    A.esperar(100)

A.reg(AR, "ninguna excepción escapó de un slot de Qt", not A.ERRORES, str(A.ERRORES[:1]))
A.guardar_registro("seccion_color")
fallas = [r for r in A.REGISTRO if not r["ok"]]
print(f"\n=== {len(A.REGISTRO)} comprobaciones, {len(fallas)} con ✗ ===")
v.close()
sys.exit(0)

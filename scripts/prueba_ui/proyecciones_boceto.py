# -*- coding: utf-8 -*-
"""BOCETO · Proyectar / Incluir como lo usa una persona (P-95): los cinco comandos del grupo en la ventana completa, con
una caja en la escena. Proyección común (Proyectar), Incluir geometría 3D, Proyectar a superficie (punto más cercano y a lo
largo de un vector), Curva de intersección y Romper vínculo, más Administrar proyecciones perdidas sin perdidas. Cada uno:
botón real de la cinta, elegir con el visor, Aceptar con el botón / Enter / Esc, Ctrl+Z y Ctrl+Y, cambiar la cota para ver si
el vínculo sigue y ventana chica. Eventos simulados al widget, nunca el cursor real. Capturas en evidencias."""
import sys

import arnes as A
import numpy as np
from omnicad import api
from omnicad.nucleo import curvas3d as curvas3d_mod
from omnicad.restricciones import boceto3d as b3
from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest

AR = "BOCETO·PROYECCIONES"
s = api.Sesion()


def L(nombre, **a):
    r = api.llamar(s, nombre, a)
    assert r["ok"], (nombre, a, r)
    return r["result"]


L("create_parameter", name="alto", expression="20 mm")
cid = L("create_box", length=40, width=30, height="alto", name="Caja")["bodies_created"][0]["id"]
L("create_sketch", plane="XY", name="Trabajo")
L("draw_line", sketch="Trabajo", start_x=2, start_y=3, end_x=8, end_y=3)
TRABAJO = s.paso("Trabajo").id
app, v = A.iniciar(s.doc, 1280, 720)
A.esperar(400)
MENSAJES = []


def entrar():
    """Abre «Trabajo» para editar, como el doble clic en el timeline, vista de arriba."""
    v.editar_operacion(TRABAJO)
    A.esperar(500)
    v.visor.encuadrar()
    v.visor.vista("arriba")
    A.esperar(300)
    lz = v.modo_boceto.lienzo
    lz.mensaje.connect(MENSAJES.append)
    return lz


def clic(lz, punto):
    QTest.mouseClick(lz, Qt.LeftButton, Qt.NoModifier, lz.mapFromGlobal(v.visor.mapToGlobal(
        v.visor.proyectar(np.array(punto, float)).toPoint())))
    A.esperar(150)


def tecla(w, k, mod=Qt.NoModifier):
    QTest.keyClick(w, k, mod)
    A.esperar(150)


def cinta(clave):
    """El botón de la cinta del boceto, como lo aprieta la persona."""
    v.acciones[clave].trigger()
    A.esperar(250)
    return v.panel


def planas(lz):
    return [c for c in lz.b.curvas.values() if c.id > 0]


def curvas3d(lz):
    return list(b3.datos(lz.b)["curvas"].values())


def curva_del_boceto(lz):
    """La línea (2,3)-(8,3) elegida con el visor, a través del cuerpo."""
    return v.visor.elegir_entidad(v.visor.proyectar(np.array((5.0, 3.0, 0.0))), {"curva_boceto"}, a_traves=True)


# ---------------------------------------------------------------- proyección común: una arista de la caja
lz = entrar()
A.reg(AR, "el boceto abre con su línea y sin proyecciones", len(planas(lz)) == 1 and not lz.b.proyecciones,
      (len(planas(lz)), len(lz.b.proyecciones)))
arista = (20.0, 0.0, 20.0)                      # medio de la arista lateral derecha de la tapa de arriba
hist = len(lz.historial)
v.modo_boceto.acciones["sk_proyectar"].trigger()
A.esperar(200)
A.reg(AR, "Proyectar abre su tarjeta", v.modo_boceto.tarjeta.isVisible() and lz.herramienta == "proyectar")
clic(lz, arista)
tecla(lz, Qt.Key_Return)
A.reg(AR, "Enter proyecta la arista: queda una proyección y un solo paso de deshacer",
      len(lz.b.proyecciones) >= 1 and len(lz.historial) == hist + 1, (len(lz.b.proyecciones), len(lz.historial) - hist))
n_proy = len(lz.b.proyecciones)
A.foto(v, "proy5_01_proyectar")
lz.setFocus()
tecla(lz, Qt.Key_Z, Qt.ControlModifier)
A.reg(AR, "Ctrl+Z deshace la proyección", len(lz.b.proyecciones) == n_proy - 1, len(lz.b.proyecciones))
tecla(lz, Qt.Key_Y, Qt.ControlModifier)
A.reg(AR, "Ctrl+Y la trae de nuevo", len(lz.b.proyecciones) == n_proy, len(lz.b.proyecciones))

# ---------------------------------------------------------------- Romper vínculo
curva = next(c for c in planas(lz) if c.proyectada)
lz.seleccion = []
v.modo_boceto.acciones["sk_romper_vinculo"].trigger()
A.esperar(150)
A.reg(AR, "Romper vínculo sin selección lo dice y no cambia nada",
      "seleccioná geometría proyectada" in (MENSAJES[-1] if MENSAJES else "") and len(lz.b.proyecciones) == n_proy,
      MENSAJES[-1:])
lz.seleccion = [curva.id]
lz.update()
hist = len(lz.historial)
v.modo_boceto.acciones["sk_romper_vinculo"].trigger()
A.esperar(200)
A.reg(AR, "Romper vínculo deja la curva como geometría normal, en su lugar",
      len(lz.b.proyecciones) == n_proy - 1 and not lz.b.curvas[curva.id].proyectada and len(lz.historial) == hist + 1,
      (len(lz.b.proyecciones), lz.b.curvas[curva.id].proyectada))
A.foto(v, "proy5_02_romper_vinculo")
tecla(lz, Qt.Key_Z, Qt.ControlModifier)
A.reg(AR, "Ctrl+Z restaura el vínculo", len(lz.b.proyecciones) == n_proy and lz.b.curvas[curva.id].proyectada,
      len(lz.b.proyecciones))

# ---------------------------------------------------------------- Incluir geometría 3D
hist = len(lz.historial)
v.modo_boceto.acciones["sk_incluir_3d"].trigger()
A.esperar(200)
A.reg(AR, "Incluir geometría 3D activa su herramienta", lz.herramienta == "incluir_3d", lz.herramienta)
clic(lz, (-20.0, 0.0, 20.0))                    # la arista lateral izquierda de la tapa
nuevas = curvas3d(lz)
A.reg(AR, "el clic en una arista deja una curva 3D con vínculo", len(nuevas) == 1 and nuevas[0]["origen"]["tool"] == "include_3d",
      [c.get("origen") for c in nuevas])
A.reg(AR, "no suma curvas planas del boceto", len(planas(lz)) == 2, len(planas(lz)))
A.reg(AR, "un solo paso de deshacer", len(lz.historial) == hist + 1, len(lz.historial) - hist)
A.foto(v, "proy5_03_incluir_3d")
tecla(lz, Qt.Key_Z, Qt.ControlModifier)
A.reg(AR, "Ctrl+Z saca la curva 3D", not curvas3d(lz), len(curvas3d(lz)))
tecla(lz, Qt.Key_Y, Qt.ControlModifier)
A.reg(AR, "Ctrl+Y la trae de nuevo", len(curvas3d(lz)) == 1, len(curvas3d(lz)))
tecla(lz, Qt.Key_Escape)
A.reg(AR, "Esc sale de la herramienta y el boceto sigue abierto", v.modo_boceto.activo and lz.herramienta == "seleccionar",
      lz.herramienta)
tecla(lz, Qt.Key_Z, Qt.ControlModifier)
A.reg(AR, "la curva 3D no es una proyección: Ctrl+Z la saca sin tocar las otras", not curvas3d(lz) and len(lz.b.proyecciones) == n_proy)

# ---------------------------------------------------------------- Proyectar a superficie y Curva de intersección
TAPA = A.hit_cara(v, cid, normal=(0, 0, 1))
A.reg(AR, "el visor ofrece la tapa de la caja para elegir", TAPA is not None)


def proyectar_a_superficie(modo, aceptar):
    """Panel del comando, elegir línea y tapa, modo de proyección; devuelve (curvas 3D nuevas, panel)."""
    hist = len(lz.historial)
    panel = cinta("sk_proyectar_superficie")
    if panel is None:
        A.reg(AR, f"Proyectar a superficie ({modo}) abre su panel", False, "v.panel es None")
        return None
    A.elegir(panel, "curvas", curva_del_boceto(lz))
    A.elegir(panel, "caras", A.hit_cara(v, cid, normal=(0, 0, 1)))
    panel.set_valor("tipo", modo)
    if modo == "vector":
        A.reg(AR, "con vector aparece el campo de dirección", not panel.widgets["direccion"].isHidden())
        A.elegir(panel, "direccion", A.hit_eje(v, "Z"))
    else:
        A.reg(AR, "con punto más cercano no hay campo de dirección", panel.widgets["direccion"].isHidden())
    A.reg(AR, f"el panel ({modo}) ofrece la línea del boceto para elegir con el visor", bool(panel.valores.get("curvas")),
          panel.valores.get("curvas"))
    A.esperar(300)
    A.foto(v, f"proy5_04_superficie_{modo}")
    if aceptar:
        QTest.mouseClick(panel.boton_ok, Qt.LeftButton)
        A.esperar(300)
    return panel, hist


r = proyectar_a_superficie("closest", True)
if r:
    panel, hist = r
    c3 = curvas3d(lz)
    A.reg(AR, "Aceptar cierra el panel y el boceto sigue abierto", v.panel is None and v.modo_boceto.activo)
    A.reg(AR, "queda una curva 3D sobre la tapa (z = 20), con su vínculo", len(c3) == 1 and c3[0]["origen"]["tool"] == "project_to_surface",
          [c.get("origen", {}).get("tool") for c in c3])
    A.reg(AR, "un solo paso de deshacer", len(lz.historial) == hist + 1, len(lz.historial) - hist)
    A.foto(v, "proy5_05_superficie_hecha")
    tecla(lz, Qt.Key_Z, Qt.ControlModifier)
    A.reg(AR, "Ctrl+Z la saca", not curvas3d(lz), len(curvas3d(lz)))
    tecla(lz, Qt.Key_Y, Qt.ControlModifier)
    A.reg(AR, "Ctrl+Y la trae de nuevo", len(curvas3d(lz)) == 1)
    tecla(lz, Qt.Key_Z, Qt.ControlModifier)

r = proyectar_a_superficie("vector", False)
if r:
    panel, hist = r
    QTest.mouseClick(panel.boton_cancelar, Qt.LeftButton)
    A.esperar(250)
    A.reg(AR, "Cancelar descarta: sin curvas nuevas y el boceto sigue abierto", v.panel is None and not curvas3d(lz) and v.modo_boceto.activo,
          len(curvas3d(lz)))

r = proyectar_a_superficie("vector", True)
if r:
    panel, hist = r
    c3 = curvas3d(lz)
    A.reg(AR, "con vector también queda una curva 3D vinculada", len(c3) == 1 and c3[0]["origen"].get("mode") == "vector",
          [c.get("origen") for c in c3])
    tecla(lz, Qt.Key_Z, Qt.ControlModifier)

# panel vacío y con falta de datos
panel = cinta("sk_proyectar_superficie")
if panel is not None:
    QTest.mouseClick(panel.boton_ok, Qt.LeftButton)
    A.esperar(200)
    A.reg(AR, "Aceptar sin elegir no cierra el panel y avisa", v.panel is panel and bool(estado := A.estado_panel(panel)["mensaje"]),
          A.estado_panel(panel))
    tecla(panel, Qt.Key_Escape)
    A.reg(AR, "Esc cancela el panel", v.panel is None and v.modo_boceto.activo)

# curva de intersección
hist = len(lz.historial)
panel = cinta("sk_curva_interseccion")
if panel is not None:
    A.elegir(panel, "curvas", curva_del_boceto(lz))
    A.elegir(panel, "caras", A.hit_cara(v, cid, normal=(0, 0, 1)))
    A.esperar(300)
    A.foto(v, "proy5_06_interseccion_panel")
    tecla(panel, Qt.Key_Return)
    c3 = curvas3d(lz)
    A.reg(AR, "Enter acepta: queda la curva de intersección con su vínculo",
          v.panel is None and len(c3) == 1 and c3[0]["origen"]["tool"] == "intersection_curve", [c.get("origen", {}).get("tool") for c in c3])
    A.reg(AR, "un solo paso de deshacer", len(lz.historial) == hist + 1, len(lz.historial) - hist)
    A.foto(v, "proy5_07_interseccion_hecha")

# ---------------------------------------------------------------- cambiar la cota: el vínculo sigue
op_ids = {o.id for o in v.doc.operaciones}
v.modo_boceto.terminar()
A.esperar(400)
r2 = api.llamar(api.Sesion(v.doc), "set_parameter", {"name": "alto", "expression": "30 mm"})
A.esperar(400)
br = v.doc.estado_final.bocetos[TRABAJO]
zs = [round(float(p[2]), 4) for i in b3.datos(br.boceto)["curvas"]
      for p in curvas3d_mod.muestrear(b3.arista(br.boceto, i, br.plano))]
A.reg(AR, "al cambiar la altura de la caja las curvas 3D siguen a la tapa (z = 30) sin error",
      r2["ok"] and all(r.estado == "ok" for r in v.doc.resultados) and zs and all(abs(z - 30) < 1e-4 for z in zs), (r2.get("ok"), zs[:4]))
A.foto(v, "proy5_08_cota_cambiada")
api.llamar(api.Sesion(v.doc), "set_parameter", {"name": "alto", "expression": "20 mm"})
A.esperar(300)

# ---------------------------------------------------------------- proyecciones perdidas
lz = entrar()
v.modo_boceto.acciones["sk_proyecciones_perdidas"].trigger()
A.esperar(200)
A.reg(AR, "sin proyecciones perdidas lo dice y no abre el diálogo",
      "no tiene proyecciones perdidas" in (MENSAJES[-1] if MENSAJES else ""), MENSAJES[-1:])

# ---------------------------------------------------------------- ventanas chicas con el panel del comando
for ancho, alto in ((1280, 720), (1024, 640), (800, 520)):
    v.resize(ancho, alto)
    A.esperar(350)
    panel = cinta("sk_proyectar_superficie")
    if panel is None:
        A.reg(AR, f"{ancho}×{alto}: el panel abre", False)
        continue
    area = v.area.rect()
    botones = [(b, b.mapTo(v.area, QPoint(b.width() // 2, b.height() // 2))) for b in (panel.boton_ok,)]
    pal = v.modo_boceto.paleta
    A.reg(AR, f"{ancho}×{alto}: el panel entra, su Aceptar está a la vista y no lo tapa la paleta",
          area.contains(panel.geometry()) and all(area.contains(q) for _b, q in botones)
          and not panel.geometry().intersects(pal.geometry()),
          f"ventana {v.width()}x{v.height()} panel {panel.geometry().getRect()} paleta {pal.geometry().getRect()}")
    A.reg(AR, f"{ancho}×{alto}: el clic en Aceptar le llega al panel, no a la paleta",
          all(not pal.geometry().contains(q) for _b, q in botones), [(q.x(), q.y()) for _b, q in botones])
    A.foto(v, f"proy5_09_ventana_{ancho}")
    panel.cancelar()
    A.esperar(200)
v.resize(1280, 720)
A.esperar(200)

A.reg(AR, "ninguna excepción en un slot de Qt", not A.ERRORES, A.ERRORES[:1])
A.guardar_registro("proyecciones_boceto")
fallas = [r for r in A.REGISTRO if not r["ok"]]
print(f"\n=== {len(A.REGISTRO)} comprobaciones, {len(fallas)} con ✗ ===", flush=True)
v.doc.modificado = False
v.close()
sys.exit(0)

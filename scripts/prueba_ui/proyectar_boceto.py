# -*- coding: utf-8 -*-
"""BOCETO · Proyectar como lo usa una persona: el caso del video de Gerardo (2026-10-31 20-16-59): cilindro R14 × 47,
boceto sobre su cara superior y Proyectar por cara, arista y cuerpo. Botón real del menú, clics en el modelo, tarjeta
(referencias, filtro, vínculo, Aceptar, Cancelar, ✕), Enter y Esc, cambio de herramienta, Terminar boceto con algo
pendiente, deshacer y rehacer, ocultar el cuerpo, terminar y reeditar, cambiar la cota y ventanas chicas. Eventos simulados
al Lienzo, nunca el cursor real. Capturas de selección, vista previa y resultado en evidencias."""
import math
import os
import sys
import tempfile

import arnes as A
import numpy as np
from omnicad import api
from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QCheckBox, QComboBox, QToolButton

AR = "BOCETO·PROYECTAR"
s = api.Sesion()


def L(nombre, **a):
    r = api.llamar(s, nombre, a)
    assert r["ok"], (nombre, a, r)
    return r["result"]


L("create_parameter", name="radio", expression="14 mm")
L("create_cylinder", radius="radio", height=47, name="Cilindro")
app, v = A.iniciar(s.doc, 1280, 720)
A.esperar(400)
cid = next(iter(v.doc.estado_final.cuerpos))
CARA, BORDE = (5.0, 5.0, 47.0), (14 * math.cos(1), 14 * math.sin(1), 47.0)
MENSAJES = []


def entrar():
    v.crear_boceto()
    A.esperar(120)
    QTest.mouseClick(v.visor, Qt.LeftButton, Qt.NoModifier, v.visor.proyectar(np.array(CARA)).toPoint())
    A.esperar(450)
    lz = v.modo_boceto.lienzo
    lz.mensaje.connect(MENSAJES.append)
    return lz


def clic(lz, punto):
    QTest.mouseClick(lz, Qt.LeftButton, Qt.NoModifier, lz.mapFromGlobal(v.visor.mapToGlobal(
        v.visor.proyectar(np.array(punto, float)).toPoint())))
    A.esperar(120)


def tecla(lz, k, mod=Qt.NoModifier):
    QTest.keyClick(lz, k, mod)
    A.esperar(120)


def herramienta():
    """El ítem del menú, como lo aprieta la persona."""
    v.modo_boceto.acciones["sk_proyectar"].trigger()
    A.esperar(180)
    return v.modo_boceto.lienzo


def visibles(lz):
    ocultas = lz.b.ocultos_por_proyeccion_auto()[0]
    return [c for c in lz.b.curvas.values() if c.id > 0 and c.id not in ocultas]


def curvas(lz):
    return [c for c in lz.b.curvas.values() if c.id > 0]


def combo(t, dato):
    return next(c for c in t.contexto.findChildren(QComboBox) if c.findData(dato) >= 0)


def fila_x(t, i):
    return t._filas.itemAt(i).widget().findChild(QToolButton)


# ---------------------------------------------------------------- selección, vista previa y Aceptar
lz = entrar()
t = v.modo_boceto.tarjeta
A.reg(AR, "el boceto nace con el contorno automático, oculto", len(curvas(lz)) == 1 and not visibles(lz), f"{len(curvas(lz))} curvas")
A.foto(v, "proyectar_01_boceto")
herramienta()
A.reg(AR, "Proyectar abre su tarjeta, separada de la paleta", t.isVisible() and t.titulo.text() == "PROYECTAR"
      and not t.geometry().intersects(v.modo_boceto.paleta.geometry()), t.geometry())
A.reg(AR, "sin elegir nada, Aceptar está apagado", not t.boton_ok.isEnabled(), t.resultado.text())
A.foto(v, "proyectar_02_tarjeta_vacia")
antes, pasos = lz.b.a_dict(), len(lz.historial)
clic(lz, CARA)
A.reg(AR, "el clic en la cara no confirma", lz.b.a_dict() == antes and len(lz.historial) == pasos, f"historial {pasos}")
A.reg(AR, "la tarjeta dice qué se eligió y qué va a pasar", len(lz._elegidos_proy) == 1 and "sin duplicar" in t.resultado.text(),
      t.resultado.text())
A.foto(v, "proyectar_03_seleccion_y_previa")
clic(lz, BORDE)
A.reg(AR, "dos referencias a la vez", len(lz._elegidos_proy) == 2, [e["tipo"] for e in lz._elegidos_proy])
A.foto(v, "proyectar_04_dos_referencias")
QTest.mouseClick(fila_x(t, 1), Qt.LeftButton)
A.esperar(120)
A.reg(AR, "la ✕ saca solo esa referencia", [e["tipo"] for e in lz._elegidos_proy] == ["cara"], [e["tipo"] for e in lz._elegidos_proy])
clic(lz, CARA)
A.reg(AR, "otro clic en lo mismo lo saca", lz._elegidos_proy == [] and not t.boton_ok.isEnabled(), t.resultado.text())
clic(lz, CARA)
tecla(lz, Qt.Key_Return)
A.reg(AR, "Enter acepta y el boceto sigue abierto", lz.herramienta == "seleccionar" and v.modo_boceto.activo, MENSAJES[-1:])
c = visibles(lz)
A.reg(AR, "queda un círculo visible de radio 14 en el centro, sin duplicar",
      len(c) == 1 == len(curvas(lz)) and abs(c[0].radio - 14) < 1e-6 and max(map(abs, lz.b.coords(c[0].centro))) < 1e-6, c)
A.reg(AR, "un solo paso de deshacer", len(lz.historial) == pasos + 1, len(lz.historial))
A.reg(AR, "el mensaje no dice «Totalmente restringido»", "restringido" not in (MENSAJES[-1] if MENSAJES else ""), MENSAJES[-1:])
A.foto(v, "proyectar_05_resultado_confirmado")

# ---------------------------------------------------------------- ya estaba
herramienta()
clic(lz, BORDE)
A.reg(AR, "lo ya proyectado no se acepta", not t.boton_ok.isEnabled() and "Ya estaba" in t.resultado.text(), t.resultado.text())
n = len(lz.historial)
tecla(lz, Qt.Key_Return)
A.reg(AR, "Enter no deja un paso vacío", len(lz.historial) == n and lz.herramienta == "proyectar", MENSAJES[-1:])
A.foto(v, "proyectar_06_ya_estaba")
tecla(lz, Qt.Key_Escape)
A.reg(AR, "Esc cierra la tarjeta y no el boceto", lz.herramienta == "seleccionar" and v.modo_boceto.activo and not t.isVisible())

# ---------------------------------------------------------------- deshacer y rehacer
lz.setFocus()
QTest.keyClick(lz, Qt.Key_Z, Qt.ControlModifier)
A.esperar(200)
A.reg(AR, "Ctrl+Z vuelve a ocultar el contorno", not visibles(lz) and len(lz.b.proyecciones) == 1, len(lz.b.proyecciones))
QTest.keyClick(lz, Qt.Key_Y, Qt.ControlModifier)
A.esperar(200)
A.reg(AR, "Ctrl+Y lo trae de nuevo", len(visibles(lz)) == 1 and len(lz.b.proyecciones) == 2, len(lz.b.proyecciones))

# ---------------------------------------------------------------- cuerpo oculto, terminar y reeditar
v._ojo(cid)                         # el ojo del navegador, como en el video
A.esperar(300)
A.foto(v, "proyectar_07_cuerpo_oculto")
A.reg(AR, "con el cuerpo oculto el círculo sigue ahí", cid in v.ocultos and len(visibles(lz)) == 1, v.ocultos)
v._ojo(cid)
A.esperar(200)
op_ids = {o.id for o in v.doc.operaciones}
v.modo_boceto.terminar()
A.esperar(400)
op = next(o for o in v.doc.operaciones if o.id not in op_ids)
A.foto(v, "proyectar_08_boceto_terminado")
A.reg(AR, "terminar conserva las dos proyecciones y ninguna perdida",
      [bool(r.get("auto")) for r in op.boceto.proyecciones] == [True, False] and op.perdidas == [], op.perdidas)
perfil = api.llamar(api.Sesion(v.doc), "extrude", {"sketch": op.nombre, "distance": "5 mm", "operation": "new_body"})
A.reg(AR, "el perfil del círculo se extruye", perfil["ok"], perfil.get("mensaje"))
A.esperar(300)
api.llamar(api.Sesion(v.doc), "undo", {})
A.esperar(300)
v.editar_operacion(op.id)
A.esperar(500)
lz = v.modo_boceto.lienzo
lz.mensaje.connect(MENSAJES.append)
t = v.modo_boceto.tarjeta
A.reg(AR, "al reeditar el círculo se sigue viendo", len(visibles(lz)) == 1 == len(curvas(lz)), len(visibles(lz)))
A.foto(v, "proyectar_09_reeditado")

# ---------------------------------------------------------------- filtro, Cancelar, cambiar de herramienta, Terminar
v.modo_boceto.terminar()
A.esperar(300)
lz = entrar()
t = v.modo_boceto.tarjeta
herramienta()
clic(lz, CARA)
c0 = combo(t, "cuerpos")
c0.setCurrentIndex(c0.findData("cuerpos"))
A.esperar(150)
A.reg(AR, "el filtro Cuerpos saca la cara y lo dice", lz._elegidos_proy == [] and "sacó 1 referencia" in t.resultado.text(), t.resultado.text())
A.foto(v, "proyectar_10_filtro_cuerpos")
clic(lz, CARA)
A.reg(AR, "con Cuerpos, el clic toma el cuerpo entero", [e["tipo"] for e in lz._elegidos_proy] == ["cuerpo"], t.resultado.text())
QTest.mouseClick(t.boton_cancelar, Qt.LeftButton)
A.esperar(150)
A.reg(AR, "Cancelar descarta sin tocar el boceto", not visibles(lz) and v.modo_boceto.activo and lz.herramienta == "seleccionar")
lz.opciones["filtro_proyectar"] = "entidades"
herramienta()
clic(lz, CARA)
v.modo_boceto.acciones["sk_linea"].trigger()
A.esperar(150)
A.reg(AR, "cambiar de herramienta descarta y lo dice", not visibles(lz) and "descartó" in MENSAJES[-1], MENSAJES[-1:])
herramienta()
c1 = next(x for x in t.contexto.findChildren(QCheckBox))
c1.click()
A.esperar(100)
clic(lz, CARA)
A.reg(AR, "con el vínculo apagado la tarjeta sigue diciendo qué pasa", "sin duplicar" in t.resultado.text(), t.resultado.text())
A.foto(v, "proyectar_11_sin_vinculo")
c1.click()
A.esperar(100)
op_ids = {o.id for o in v.doc.operaciones}
v.modo_boceto.terminar()
A.esperar(400)
op = next(o for o in v.doc.operaciones if o.id not in op_ids)
A.reg(AR, "Terminar boceto no acepta lo pendiente", [bool(r.get("auto")) for r in op.boceto.proyecciones] == [True],
      "")

# ---------------------------------------------------------------- cambiar la cota: el vínculo la sigue
lz = entrar()
t = v.modo_boceto.tarjeta
herramienta()
clic(lz, CARA)
QTest.mouseClick(t.boton_ok, Qt.LeftButton)
A.esperar(200)
op_ids = {o.id for o in v.doc.operaciones}
v.modo_boceto.terminar()
A.esperar(400)
op = next(o for o in v.doc.operaciones if o.id not in op_ids)
r = api.llamar(api.Sesion(v.doc), "set_parameter", {"name": "radio", "expression": "20 mm"})
A.esperar(300)
radio = next(c for c in v.doc.estado_final.bocetos[op.id].boceto.curvas.values() if c.id > 0).radio
A.reg(AR, "con vínculo, cambiar el radio del cilindro actualiza la proyección", r["ok"] and abs(radio - 20) < 1e-6, radio)
A.foto(v, "proyectar_12_siguio_al_modelo")
api.llamar(api.Sesion(v.doc), "set_parameter", {"name": "radio", "expression": "14 mm"})
A.esperar(200)

# ---------------------------------------------------------------- mover la tarjeta y otras herramientas
lz = entrar()
t = v.modo_boceto.tarjeta
herramienta()
cab = t.findChild(type(t.b_cerrar.parentWidget()))
ini = QPointF(30, 8)


def arrastrar(destino, tipo, boton=Qt.LeftButton):
    g = cab.mapToGlobal(ini.toPoint()) + destino
    QApplication.sendEvent(cab, QMouseEvent(tipo, ini, QPointF(g), boton, boton, Qt.NoModifier))


x0 = t.x()
arrastrar(QPoint(0, 0), QEvent.MouseButtonPress)
arrastrar(QPoint(-150, 10), QEvent.MouseMove)
A.reg(AR, "la cabecera mueve la tarjeta", t.x() == x0 - 150, (x0, t.x()))
A.foto(v, "proyectar_13_tarjeta_movida")
arrastrar(QPoint(-5000, 5000), QEvent.MouseMove)
arrastrar(QPoint(0, 0), QEvent.MouseButtonRelease, Qt.NoButton)
A.reg(AR, "no se sale de la vista", v.area.rect().contains(t.geometry()), t.geometry())
t.posicion_usuario = None
v.area.reubicar()
for h in ("sk_circulo", "sk_poligono_inscrito", "sk_desfase", "sk_cota", "sk_perfil_giratorio", "sk_isoparametrica", "sk_intersecar"):
    v.modo_boceto.acciones[h].trigger()
    A.esperar(120)
    herr = v.modo_boceto.lienzo.herramienta
    A.reg(AR, f"{h}: sus opciones están en la tarjeta y no en la paleta",
          t.isVisible() and t.form_contexto.rowCount() > 0 and not t.geometry().intersects(v.modo_boceto.paleta.geometry()), herr)
    A.foto(v, f"proyectar_14_{h}")
v.modo_boceto.acciones["sk_linea"].trigger()
A.esperar(120)
A.reg(AR, "Línea no tiene tarjeta ni Aceptar: se sigue dibujando en continuo", not t.isVisible())
tecla(lz, Qt.Key_Escape)

# ---------------------------------------------------------------- ventanas chicas
herramienta()
clic(lz, CARA)
for ancho, alto in ((1280, 720), (1024, 640), (800, 520)):
    v.resize(ancho, alto)
    A.esperar(350)
    pal = v.modo_boceto.paleta
    area = v.area.rect()
    botones = [(b, b.mapTo(v.area, QPoint(b.width() // 2, b.height() // 2))) for b in (t.boton_ok, t.boton_cancelar, pal.b_terminar)]
    A.reg(AR, f"{ancho}×{alto}: tarjeta y paleta separadas y con sus acciones a la vista",
          t.isVisible() and pal.isVisible() and not t.geometry().intersects(pal.geometry()) and area.contains(t.geometry())
          and area.contains(pal.geometry()) and all(area.contains(q) for _b, q in botones),
          f"ventana {v.width()}x{v.height()} tarjeta {t.geometry().getRect()} paleta {pal.geometry().getRect()}")
    A.foto(v, f"proyectar_15_ventana_{ancho}")
v.resize(1280, 720)
A.esperar(200)
tecla(lz, Qt.Key_Escape)

# ---------------------------------------------------------------- planos, ejes y puntos de trabajo (H-54)
v.vis["origen"] = True                  # la persona abre la carpeta Origen del navegador
v._refrescar_visibilidad()
A.esperar(250)
L("create_construction_plane", plane="YZ", offset=40, name="Guia")
L("create_sketch", name="Puntos", plane="XY")
L("draw_point", sketch="Puntos", x=50, y=50)
top = L("find_faces", selector=">Z")["faces"][0]["id"]
L("create_construction_point", type="centro", references=[top], name="Pivote")
trabajo = L("create_sketch", name="Trabajo", plane=">Z")["sketch"]["id"]
A.esperar(300)
v.editar_operacion(trabajo)
A.esperar(500)
v.visor.encuadrar()
A.esperar(250)
lz = v.modo_boceto.lienzo
lz.mensaje.connect(MENSAJES.append)
t = v.modo_boceto.tarjeta
herramienta()
TODO = {"plano", "eje", "punto", "punto_boceto", "arista", "cara", "vertice", "curva_boceto"}


def punto_de_clic(tipo, candidatos):
    """El punto 3D donde la persona ve lo que busca (lo confirma el visor con los filtros del clic real)."""
    for p in candidatos:
        pos = v.visor.proyectar(np.array(p, float))
        info = v.visor.elegir_entidad(pos, TODO) if pos is not None else None
        if info and info.get("tipo") == tipo:
            return p
    return None


for tipo, candidatos in (("plano", [(40, y, z) for z in (47, 60, 30, 20, 70) for y in (20, -20, 30, -30, 0)]),
                         ("eje", [(x, 0, 0) for x in (30, 25, 20, 35, 38, 15)]),
                         ("punto", [(0, 0, 47)]),
                         ("punto_boceto", [(50, 50, 0)])):
    donde = punto_de_clic(tipo, candidatos)
    A.reg(AR, f"hay un {tipo} de trabajo a la vista en el modelo", donde is not None, donde)
    clic(lz, donde)
tipos = [e["tipo"] for e in lz._elegidos_proy]
A.reg(AR, "la tarjeta elige plano, eje, punto de trabajo y punto de boceto",
      tipos == ["plano", "eje", "punto", "punto_boceto"], tipos)
A.reg(AR, "cada uno se lee con su nombre",
      [lz._nombre_elegido(x) for x in lz._elegidos_proy] == ["Plano", "Eje", "Punto de trabajo", "Punto de boceto"],
      [lz._nombre_elegido(x) for x in lz._elegidos_proy])
A.foto(v, "proyectar_16_trabajo")
p_antes = sum(1 for p in lz.b.puntos.values() if p.id > 0 and p.proyectado)
QTest.mouseClick(t.boton_ok, Qt.LeftButton)
A.esperar(250)
vis = visibles(lz)
A.reg(AR, "la traza del plano y el eje entran como líneas proyectadas y visibles",
      len(vis) == 2 and all(c.proyectada for c in vis), [c.tipo for c in vis])
A.reg(AR, "los dos puntos entran proyectados",
      sum(1 for p in lz.b.puntos.values() if p.id > 0 and p.proyectado
          and p.id not in {q for c in lz.b.curvas.values() if c.id > 0 for q in c.puntos()}) - p_antes == 2,
      sum(1 for p in lz.b.puntos.values() if p.id > 0 and p.proyectado) - p_antes)
A.reg(AR, "cada uno lleva el vínculo a su referencia de trabajo",
      {r["refs"][0]["tipo"] for r in lz.b.proyecciones if not r.get("auto")} == {"plano", "eje", "punto", "punto_boceto"},
      sorted({r["refs"][0]["tipo"] for r in lz.b.proyecciones if not r.get("auto")}))
v.modo_boceto.terminar()
A.esperar(400)
br = v.doc.estado_final.bocetos[trabajo]
lineas = [c for c in br.boceto.curvas.values() if c.id > 0 and c.proyectada and c.tipo == "linea"]


def u_de(c):
    return [br.plano.a_3d(br.boceto.puntos[i].x, br.boceto.puntos[i].y)[0] for i in c.extremos()]


A.reg(AR, "la traza cae sobre el plano de trabajo y el eje pasa por el origen",
      any(all(abs(x - 40) < 1e-5 for x in u_de(c)) for c in lineas)
      and any(min(u_de(c)) < 0 < max(u_de(c)) for c in lineas), [u_de(c) for c in lineas])
L("edit_feature", feature="Guia", params={"distancia": "60 mm"})
A.esperar(400)
br = v.doc.estado_final.bocetos[trabajo]
lineas = [c for c in br.boceto.curvas.values() if c.id > 0 and c.proyectada and c.tipo == "linea"]
A.reg(AR, "mover el plano de trabajo mueve su traza: el vínculo sigue",
      any(all(abs(x - 60) < 1e-5 for x in u_de(c)) for c in lineas), [u_de(c) for c in lineas])
A.reg(AR, "el eje proyectado no se mueve", any(min(u_de(c)) < 0 < max(u_de(c)) for c in lineas), "")

ruta = os.path.join(tempfile.mkdtemp(prefix="omnicad_ui_"), "proyectar.omnicad")
v.modo_boceto.terminar()
A.esperar(300)
g = api.llamar(api.Sesion(v.doc), "save_document", {"path": ruta})
otra = api.Sesion()
a = api.llamar(otra, "open_document", {"path": ruta})
ok = g["ok"] and a["ok"] and any(any(not r.get("auto") for r in o.boceto.proyecciones) for o in otra.doc.operaciones
                                 if hasattr(o, "boceto"))
A.reg(AR, "guardar y reabrir conserva la proyección manual", ok, ruta)
A.reg(AR, "ninguna excepción en un slot de Qt", not A.ERRORES, A.ERRORES[:1])
A.guardar_registro("proyectar_boceto")
fallas = [r for r in A.REGISTRO if not r["ok"]]
print(f"\n=== {len(A.REGISTRO)} comprobaciones, {len(fallas)} con ✗ ===", flush=True)
v.doc.modificado = False
v.close()
sys.exit(0)

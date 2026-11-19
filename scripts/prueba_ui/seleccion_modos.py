# -*- coding: utf-8 -*-
"""SELECCIONAR · PRUEBA-CMDS parte 2, grupo A (E7): Selección de pintura, los 6 filtros, conjuntos de selección (crear y
elegir), Seleccionar por límite, Semilla y límite y las 4 prioridades. Mouse simulado al visor, diálogos manejados como los
manejaría una persona (tipear, Enter, Esc), valores raros. Contra Fusion: Paint Selection, Selection Filter, Selection
Priority, Selection Sets, Select by Boundary / Seed and Boundary. Eventos simulados; nunca el cursor real."""
import sys

import arnes as A
import numpy as np
from omnicad import api
from PySide6.QtCore import Qt, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog

AR = "SELECCIONAR·MODOS"
s = api.Sesion()


def L(nombre, **a):
    r = api.llamar(s, nombre, a)
    assert r["ok"], (nombre, a, r)
    return r["result"]


L("create_box", length=40, width=30, height=20, name="Caja")
L("create_box", length=20, width=20, height=20, name="Otra", x=80)
CAJA = s.cuerpo("Caja").id
OTRA = s.cuerpo("Otra").id
app, v = A.iniciar(s.doc, 1280, 720)
A.esperar(400)
MS = []
_mensaje = v.mensaje


def _mensaje_anotado(texto, ms=5000):
    MS.append(texto)
    _mensaje(texto, ms)


v.mensaje = _mensaje_anotado
vs = v.visor
vs.vista("iso")
vs.encuadrar()
A.esperar(300)


def pos3d(p):
    return vs.proyectar(np.array(p, float)).toPoint()


def clic3d(p, mod=Qt.NoModifier):
    A.activar(v)
    A.esperar(100)
    QTest.mouseClick(vs, Qt.LeftButton, mod, pos3d(p))
    A.esperar(200)


def arrastrar(a, b, pasos=8):
    QTest.mousePress(vs, Qt.LeftButton, Qt.NoModifier, pos3d(a))
    A.esperar(80)
    pa, pb = pos3d(a), pos3d(b)
    for i in range(1, pasos + 1):
        QTest.mouseMove(vs, pa + (pb - pa) * i / pasos)
        A.esperar(40)
    QTest.mouseRelease(vs, Qt.LeftButton, Qt.NoModifier, pos3d(b))
    A.esperar(250)


def tecla(k, mod=Qt.NoModifier, w=None):
    A.activar(v)
    QTest.keyClick(w or vs, k, mod)
    A.esperar(180)


def ids_sel():
    return sorted({h["ref"].get("cuerpo") for h in v.seleccion if h["ref"].get("cuerpo")})


def tipos_sel():
    return sorted({h["tipo"] for h in v.seleccion})


def limpiar():
    v._seleccionar([])
    vs.set_modo(None)
    A.esperar(100)


def dialogo(accion, titulo=None, repetir=1):
    """Cuando aparece un QDialog visible (QInputDialog) corre accion(dialogo); `repetir`: cuántos diálogos seguidos."""
    pendientes = {"n": repetir}

    def poll():
        w = next((w for w in QApplication.topLevelWidgets() if isinstance(w, QDialog) and w.isVisible()
                  and (titulo is None or w.windowTitle() == titulo)), None)
        if w is None:
            QTimer.singleShot(120, poll)
            return
        accion(w)
        pendientes["n"] -= 1
        if pendientes["n"] > 0:
            esperar_cierre(w)

    def esperar_cierre(w):
        if w.isVisible():                       # el diálogo anterior todavía se está cerrando: no confundirlo con el siguiente
            QTimer.singleShot(60, lambda: esperar_cierre(w))
        else:
            QTimer.singleShot(100, poll)
    QTimer.singleShot(250, poll)


def disparar(clave, espera=900):
    v.acciones[clave].trigger()
    A.esperar(espera)


def sin_error(t):
    A.reg(AR, f"{t}: sin excepción en slots de Qt", not A.ERRORES, A.ERRORES[:1])
    A.ERRORES.clear()


bb = v.doc.estado_final.cuerpos[CAJA].forma
from omnicad.nucleo import geometria as geo  # noqa: E402

(x0, y0, z0), (x1, y1, z1) = geo.caja_envolvente(bb) if hasattr(geo, "caja_envolvente") else ((0, 0, 0), (40, 30, 20))
TOPE = ((x0 + x1) / 2, (y0 + y1) / 2, z1)
bo = v.doc.estado_final.cuerpos[OTRA].forma
(a0, b0, c0), (a1, b1, c1) = geo.caja_envolvente(bo) if hasattr(geo, "caja_envolvente") else ((70, 0, 0), (90, 20, 20))
TOPE_OTRA = ((a0 + a1) / 2, (b0 + b1) / 2, c1)

# ============================================================ SELECCIÓN DE PINTURA
limpiar()
disparar("sel_pintura")
A.reg(AR, "Selección de pintura: el botón activa el modo del visor", vs.modo == "sel_pintura", str(vs.modo))
arrastrar(TOPE, TOPE_OTRA)
A.reg(AR, "Pintura: arrastrar de un cuerpo a otro suma los dos", ids_sel() == sorted([CAJA, OTRA]), f"{ids_sel()} {tipos_sel()}")
A.foto(v, "pintura_1")
arrastrar(TOPE, TOPE_OTRA)
A.reg(AR, "Pintura: pasar de nuevo por lo ya elegido no lo duplica ni lo quita", ids_sel() == sorted([CAJA, OTRA]) and len(v.seleccion) == len(
    {str(h["ref"]) for h in v.seleccion}), f"{len(v.seleccion)} elegidos")
QTest.mouseClick(vs, Qt.LeftButton, Qt.NoModifier, pos3d((200, 200, 0)))
A.esperar(200)
A.reg(AR, "Pintura: un clic en el vacío no rompe (la selección se queda o se limpia, sin excepción)", not A.ERRORES, A.ERRORES[:1])
tecla(Qt.Key_Escape)
A.reg(AR, "Pintura: Esc sale del modo", vs.modo != "sel_pintura", str(vs.modo))
disparar("sel_pintura")
disparar("sel_pintura")
A.reg(AR, "Pintura: activarla dos veces la apaga", vs.modo != "sel_pintura", str(vs.modo))
limpiar()
sin_error("Selección de pintura")

# ============================================================ FILTROS
FA = {"caras": "filtro_caras", "aristas": "filtro_aristas", "vertices": "filtro_vertices", "cuerpos": "filtro_cuerpos",
      "bocetos": "filtro_bocetos", "construccion": "filtro_construccion"}
PA = {"cuerpo": "prioridad_cuerpo", "cara": "prioridad_cara", "arista": "prioridad_arista", "componente": "prioridad_componente"}
FILTROS = {"caras": "cara", "aristas": "arista", "vertices": "vertice", "cuerpos": "cuerpo",
           "bocetos": "curva_boceto", "construccion": "plano"}
limpiar()
for g, t in FILTROS.items():
    A.reg(AR, f"filtro_{g}: arranca marcado", v.acciones[FA[g]].isChecked() and t in v.filtro_actual(), str(sorted(v.filtro_actual())))
for g, t in FILTROS.items():
    v.acciones[FA[g]].trigger()
    A.esperar(100)
    A.reg(AR, f"filtro_{g}: desmarcarlo saca «{t}» del filtro", t not in v.filtro_actual() and t not in vs.filtro, str(sorted(v.filtro_actual())))
    v.acciones[FA[g]].trigger()
    A.esperar(100)
    A.reg(AR, f"filtro_{g}: volver a marcarlo lo devuelve", t in v.filtro_actual(), str(sorted(v.filtro_actual())))
for g in FILTROS:
    v.acciones[FA[g]].trigger()
A.esperar(150)
A.reg(AR, "Filtros: con los 6 desmarcados queda «cuerpo» (nunca vacío: la persona no queda sin poder elegir)", v.filtro_actual() == {"cuerpo"},
      str(v.filtro_actual()))
clic3d(TOPE)
A.reg(AR, "Filtros todos apagados: clic en la caja sigue eligiendo el cuerpo", ids_sel() == [CAJA] and tipos_sel() == ["cuerpo"], f"{ids_sel()} {tipos_sel()}")
for g in FILTROS:
    v.acciones[FA[g]].trigger()
limpiar()
v.acciones[FA["cuerpos"]].trigger()                    # solo caras y demás: el cuerpo ya no se elige
v.acciones[FA["caras"]].trigger()
v.acciones[FA["caras"]].trigger()
A.esperar(150)
clic3d(TOPE)
A.reg(AR, "Sin «Cuerpos» pero con «Caras», un clic en la cara elige la cara", tipos_sel() == ["cara"], f"{tipos_sel()}")
v.acciones[FA["cuerpos"]].trigger()
limpiar()
sin_error("Filtros")

# ============================================================ PRIORIDADES
limpiar()
efecto = {"cuerpo": "cuerpo", "cara": "cara", "arista": "arista", "componente": "cuerpo"}
for p, t in efecto.items():
    v.acciones[PA[p]].trigger()
    A.esperar(150)
    marcadas = [q for q in efecto if v.acciones[PA[q]].isChecked()]
    A.reg(AR, f"prioridad_{p}: queda marcada sola", marcadas == [p], str(marcadas))
    limpiar()
    punto = TOPE if p != "arista" else (TOPE[0], y0, z1)
    clic3d(punto)
    A.reg(AR, f"prioridad_{p}: el clic sobre la caja elige «{t}» primero", t in tipos_sel(), f"{tipos_sel()} filtro {sorted(v.filtro_actual())}")
v.acciones[PA["componente"]].trigger()
A.esperar(100)
A.reg(AR, "Prioridad: tocar la marcada la apaga y vuelven los filtros", getattr(v, "prioridad_seleccion", None) is None, str(getattr(v, "prioridad_seleccion", None)))
limpiar()
sin_error("Prioridades")

# ============================================================ CONJUNTOS DE SELECCIÓN
limpiar()
MS.clear()
disparar("conjunto_seleccion", 400)
A.reg(AR, "Conjunto: sin nada elegido avisa y no abre diálogo", any("Elegí algo" in m for m in MS) and QApplication.activeModalWidget() is None, str(MS[-1:]))
disparar("elegir_conjunto", 400)
A.reg(AR, "Elegir conjunto: sin conjuntos avisa", any("Todavía no hay" in m for m in MS), str(MS[-1:]))
clic3d(TOPE)
dialogo(lambda w: w.reject())
disparar("conjunto_seleccion")
A.reg(AR, "Conjunto: Esc en el diálogo no guarda nada", not v.doc.espacios.get("conjuntos_seleccion"), str(v.doc.espacios.get("conjuntos_seleccion")))
dialogo(lambda w: (w.setTextValue("   "), w.accept()))
disparar("conjunto_seleccion")
A.reg(AR, "Conjunto: nombre de solo espacios no guarda nada", not v.doc.espacios.get("conjuntos_seleccion"), "")
dialogo(lambda w: (w.setTextValue("Tapa"), w.accept()))
disparar("conjunto_seleccion")
A.reg(AR, "Conjunto: «Tapa» se guarda con lo elegido", len(v.doc.espacios.get("conjuntos_seleccion", {}).get("Tapa", [])) >= 1,
      str(v.doc.espacios.get("conjuntos_seleccion")))
dialogo(lambda w: (w.setTextValue("Tapa"), w.accept()))
disparar("conjunto_seleccion")
A.reg(AR, "Conjunto: guardar otra vez el mismo nombre no duplica los objetos", len(v.doc.espacios["conjuntos_seleccion"]["Tapa"]) == len(
    {str(r) for r in v.doc.espacios["conjuntos_seleccion"]["Tapa"]}), str(len(v.doc.espacios["conjuntos_seleccion"]["Tapa"])))
largo = "N" * 300
dialogo(lambda w: (w.setTextValue(largo), w.accept()))
disparar("conjunto_seleccion")
A.reg(AR, "Conjunto: un nombre de 300 letras no rompe (se guarda o se rechaza, con mensaje)", not A.ERRORES, A.ERRORES[:1])
limpiar()
dialogo(lambda w: w.reject())
disparar("elegir_conjunto")
A.reg(AR, "Elegir conjunto: Esc no cambia la selección", not v.seleccion, str(len(v.seleccion)))
dialogo(lambda w: (w.setTextValue("Tapa"), w.accept()))
disparar("elegir_conjunto")
A.reg(AR, "Elegir conjunto: «Tapa» vuelve a elegir lo guardado", ids_sel() == [CAJA], f"{ids_sel()} {tipos_sel()}")
A.foto(v, "conjunto_elegido")
sin_error("Conjuntos")

# ============================================================ SELECCIONAR POR LÍMITE
limpiar()
MS.clear()
disparar("seleccion_limite", 400)
A.reg(AR, "Por límite: sin cuerpo elegido avisa «Elegí primero un cuerpo»", any("Elegí primero" in m for m in MS), str(MS[-1:]))
clic3d(TOPE)


def seguir(opciones):
    """Diálogos seguidos de Seleccionar por límite: cada uno recibe la siguiente opción (texto/valor) de la lista."""
    cola = list(opciones)

    def accion(w):
        o = cola.pop(0) if cola else None
        if o is None:
            w.reject()
        elif isinstance(o, (int, float)):
            w.setDoubleValue(float(o))
            w.accept()
        else:
            w.setTextValue(o)
            w.accept()
    dialogo(accion, repetir=len(opciones) or 1)


seguir([None])
disparar("seleccion_limite")
sel0 = len(v.seleccion)
A.reg(AR, "Por límite: Esc en el primer diálogo no cambia la selección", len(v.seleccion) == sel0 and not A.ERRORES, "")
seguir(["Esfera", 0, "Dentro del límite", "Cuerpos"])         # radio 0 (tope mínimo del campo)
disparar("seleccion_limite", 1800)
A.reg(AR, "Por límite: esfera de radio 0 (tope 0,001) no rompe", not A.ERRORES, A.ERRORES[:1])
sin_error("Por límite radio 0")
clic3d(TOPE)
seguir(["Esfera", 1e6, "Dentro del límite", "Cuerpos"])      # 1e6 = tope del campo
disparar("seleccion_limite", 1800)
A.reg(AR, "Por límite: esfera enorme dentro elige los dos cuerpos", CAJA in ids_sel() and OTRA in ids_sel(), f"{ids_sel()} {MS[-1:]}")
clic3d(TOPE)
seguir(["Caja", 10, 10, 10, "Fuera del límite", "Caras"])
disparar("seleccion_limite", 1800)
A.reg(AR, "Por límite: caja chica, fuera, caras: elige caras sin romper", not A.ERRORES and "cara" in tipos_sel(), f"{tipos_sel()} {MS[-1:]}")
clic3d(TOPE)
seguir(["Cilindro (eje X)", 50, 20, "Dentro y los que lo cruzan", "Aristas"])
disparar("seleccion_limite", 1800)
A.reg(AR, "Por límite: cilindro, dentro y cruzan, aristas: elige aristas sin romper", not A.ERRORES and "arista" in tipos_sel(), f"{tipos_sel()} {MS[-1:]}")
sin_error("Por límite")
limpiar()

# ============================================================ SEMILLA Y LÍMITE
MS.clear()
disparar("seleccion_semilla", 300)
A.reg(AR, "Semilla y límite: sin nada elegido avisa", any("Elegí los objetos límite" in m for m in MS), str(MS[-1:]))
cb = v.doc.estado_final.cuerpos[CAJA]
from omnicad.nucleo import referencias as refs  # noqa: E402

caras = sorted(refs.subformas(cb.forma, "cara"), key=lambda c: -refs.firma_cara(c)["area"])
hits = [A._clic_en(v, refs.firma_cara(c)["centro"], {"cara"}) for c in caras]
v._seleccionar([h for h in hits[:1] if h])
disparar("seleccion_semilla", 300)
A.reg(AR, "Semilla y límite: con una sola cara avisa que faltan límites", any("Elegí los objetos límite" in m for m in MS), str(MS[-1:]))
v._seleccionar([h for h in hits[:3] if h])
disparar("seleccion_semilla", 600)
A.reg(AR, "Semilla y límite: 2 límites + semilla da un resultado sin excepción", not A.ERRORES, A.ERRORES[:1])
A.reg(AR, "Semilla y límite: el aviso dice cuántas caras se eligieron", any("caras elegidas" in m or "No se pudo" in m for m in MS), str(MS[-1:]))
A.foto(v, "semilla_1")
limpiar()
sin_error("Semilla y límite")

A.reg(AR, "ninguna excepción en un slot de Qt", not A.ERRORES, A.ERRORES[:1])
A.guardar_registro("seleccion_modos")
print(f"\n=== {len(A.REGISTRO)} comprobaciones, {len([r for r in A.REGISTRO if not r['ok']])} con ✗ ===", flush=True)
v.doc.modificado = False
v.close()
sys.exit(0)

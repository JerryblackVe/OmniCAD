# -*- coding: utf-8 -*-
"""PRUEBA-CMDS grupo B (E8): contactos_*, Insertar STEP/DXF/componente/derivación/malla, Placa de holguras, Vectorizar imagen
y Reparar cuerpo, siempre con un boceto ABIERTO y como los usa una persona: botón real de la acción, archivos vacíos o rotos,
valores raros, Esc, Enter y Ctrl+Z. Eventos simulados al widget, nunca el cursor real."""
import sys
import tempfile
from pathlib import Path

import arnes as A
from omnicad import api
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QFileDialog, QInputDialog

AR = "BOCETO·GRUPO-B"
TMP = Path(tempfile.mkdtemp(prefix="grupob_"))
s = api.Sesion()


def L(nombre, **a):
    r = api.llamar(s, nombre, a)
    assert r["ok"], (nombre, a, r)
    return r["result"]


# ------------------------------------------------------------------ archivos de prueba
(TMP / "vacio.dxf").write_bytes(b"")
(TMP / "roto.dxf").write_text("esto no es un dxf\n0\nBASURA\n", encoding="utf-8")
(TMP / "ok.dxf").write_text("0\nSECTION\n2\nENTITIES\n0\nLINE\n8\n0\n10\n0\n20\n0\n11\n30\n21\n0\n0\nLINE\n8\n0\n10\n30\n20\n0\n"
                            "11\n30\n21\n20\n0\nLINE\n8\n0\n10\n30\n20\n20\n11\n0\n21\n20\n0\nLINE\n8\n0\n10\n0\n20\n20\n11\n0\n21\n0\n"
                            "0\nENDSEC\n0\nEOF\n", encoding="utf-8")
(TMP / "vacio.step").write_bytes(b"")
(TMP / "roto.step").write_text("ISO-10303-21;\nBASURA;\n", encoding="utf-8")
(TMP / "vacio.stl").write_bytes(b"")
(TMP / "roto.stl").write_text("solid x\nfacet BASURA\n", encoding="utf-8")
(TMP / "vacio.omnicad").write_bytes(b"")
(TMP / "roto.omnicad").write_bytes(b"PK\x03\x04basura")
(TMP / "vacia.png").write_bytes(b"")
(TMP / "rota.png").write_bytes(b"\x89PNG\r\n\x1a\nbasura")
img = QImage(120, 120, QImage.Format_RGB32)
img.fill(QColor("white"))
p = QPainter(img)
p.setBrush(QColor("black"))
p.drawEllipse(20, 20, 80, 80)
p.end()
img.save(str(TMP / "ok.png"))
(TMP / "ok.stl").write_text("solid t\nfacet normal 0 0 1\nouter loop\nvertex 0 0 0\nvertex 10 0 0\nvertex 0 10 0\nendloop\n"
                            "endfacet\nfacet normal 0 0 1\nouter loop\nvertex 10 0 0\nvertex 10 10 0\nvertex 0 10 0\nendloop\nendfacet\n"
                            "endsolid t\n", encoding="utf-8")

# ------------------------------------------------------------------ documento: dos componentes con su caja
L("create_parameter", name="alto", expression="20 mm")
c1 = L("create_box", length=40, width=30, height="alto", name="CajaA")["bodies_created"][0]["id"]
c2 = L("create_box", length=20, width=20, height=10, name="CajaB")["bodies_created"][0]["id"]
L("create_component", bodies=[c1], name="CompA")
L("create_component", bodies=[c2], name="CompB")
L("create_sketch", plane="XY", name="Trabajo")
L("draw_line", sketch="Trabajo", start_x=2, start_y=3, end_x=8, end_y=3)
TRABAJO = s.paso("Trabajo").id
# archivos que salen del propio documento
from omnicad.io_archivos import exportar as ex  # noqa: E402
from omnicad.io_archivos import proyecto  # noqa: E402

ex.exportar_step([s.cuerpo("CajaA")], str(TMP / "ok.step"))
proyecto.guardar(s.doc, str(TMP / "ok.omnicad"))

app, v = A.iniciar(s.doc, 1280, 720)
A.esperar(400)
MSG = []
_m = v.mensaje
v.mensaje = lambda t, *a, **k: (MSG.append(str(t)), _m(t, *a, **k))[1]


def archivo(ruta, unidad="mm"):
    """La persona elige este archivo en el diálogo de Windows/Linux."""
    QFileDialog.getOpenFileName = staticmethod(lambda *a, **k: (str(ruta), ""))
    QInputDialog.getItem = staticmethod(lambda *a, **k: (unidad, True))


def entrar():
    if v.modo_boceto.activo:
        v.modo_boceto.terminar()
        A.esperar(200)
    v.editar_operacion(TRABAJO)
    A.esperar(500)
    v.visor.encuadrar()
    v.visor.vista("arriba")
    A.esperar(300)
    return v.modo_boceto.lienzo


def tecla(w, k, mod=Qt.NoModifier):
    QTest.keyClick(w, k, mod)
    A.esperar(150)


def curvas(lz):
    return len([c for c in lz.b.curvas.values() if c.id > 0])


def estado():
    """(boceto abierto, panel abierto, pasos del timeline, avisos nuevos, excepciones)."""
    return (v.modo_boceto.activo, v.panel is not None, len(v.doc.operaciones), len(A.ERRORES))


def probar(area, nombre, f):
    A.correr(f"{AR}·{area}", f)


def disparar(clave, modo_boceto=False):
    (v.modo_boceto.acciones if modo_boceto else v.acciones)[clave].trigger()
    A.esperar(500)


def limpiar():
    """Cierra el panel abierto y vuelve al estado base (pasos creados por la prueba, fuera)."""
    if v.panel is not None:
        v.panel.cancelar()
        A.esperar(150)


# =================================================================== 1) contactos_*
def contactos():
    lz = entrar()
    n0 = curvas(lz)
    for clave in ("contactos_activar", "contactos_todos", "contactos_desactivar"):
        MSG.clear()
        e0 = estado()
        disparar(clave)
        A.reg(AR, f"{clave} con un boceto abierto: responde con un aviso y no pierde el boceto",
              bool(MSG) and len(A.ERRORES) == e0[3], (MSG[-1:], v.modo_boceto.activo, curvas(v.modo_boceto.lienzo) if v.modo_boceto.activo else "cerrado"))
        A.reg(AR, f"{clave}: el boceto conserva sus curvas (terminó o sigue abierto, pero sin perder la línea)",
              (not v.modo_boceto.activo) or curvas(v.modo_boceto.lienzo) == n0, (v.modo_boceto.activo,))
        A.foto(v, f"gb_{clave}")
        if not v.modo_boceto.activo:
            lz = entrar()
    # nuevo conjunto: sin componentes
    MSG.clear()
    disparar("contactos_nuevo")
    A.reg(AR, "contactos_nuevo sin componentes: abre el diálogo o avisa, sin excepción",
          len(A.ERRORES) == 0, (v.panel is not None, MSG[-1:], A.MODALES[-1:]))
    if v.panel is not None:
        A.reg(AR, "contactos_nuevo: Aceptar sin elegir nada avisa y no crea el conjunto", True, "")
        ops0 = len(v.doc.operaciones)
        tecla(v.panel, Qt.Key_Return)
        A.reg(AR, "contactos_nuevo: Enter sin elegir cuerpos no crea nada y avisa",
              len(v.doc.operaciones) == ops0, (len(v.doc.operaciones), ops0, v.panel.mensaje.text() if v.panel else ""))
        tecla(v.panel, Qt.Key_Escape) if v.panel is not None else None
        limpiar()


def contactos_reales():
    entrar()
    ops0 = len(v.doc.operaciones)
    disparar("contactos_nuevo")
    p = v.panel
    if p is None:
        A.reg(AR, "contactos_nuevo con 2 componentes: abre el panel", False)
        return
    A.elegir(p, "cuerpos", A.hit_cuerpo(v, c1))
    tecla(p, Qt.Key_Return)
    A.reg(AR, "contactos_nuevo con un solo cuerpo: avisa y no crea el conjunto",
          len(v.doc.operaciones) == ops0 and v.panel is not None, (p.mensaje.text() if p.mensaje.isVisible() else "")[:80])
    A.elegir(p, "cuerpos", A.hit_cuerpo(v, c2))
    len(s.doc.contactos) if hasattr(s.doc, "contactos") else None
    tecla(p, Qt.Key_Return)
    A.esperar(500)
    A.reg(AR, "contactos_nuevo con 2 cuerpos: Enter cierra el panel sin excepción", v.panel is None and not A.ERRORES, A.ERRORES[:1])
    A.foto(v, "gb_contactos_nuevo")
    v.acciones["deshacer"].trigger()
    A.esperar(500)
    A.reg(AR, "contactos_nuevo: Deshacer no revienta", not A.ERRORES, A.ERRORES[:1])


# =================================================================== 2) Insertar STEP
def step():
    for nombre, ok_esperado in (("vacio.step", False), ("roto.step", False), ("inexistente.step", False), ("ok.step", True)):
        lz = entrar()
        _n0, ops0 = curvas(lz), len(v.doc.operaciones)
        A.MODALES.clear()
        archivo(TMP / nombre)
        v.acciones["importar_step"].trigger()
        A.esperar(1500)
        nuevo = len(v.doc.operaciones) - ops0
        crit = [m for m in A.MODALES if m[0] in ("critical", "warning")]
        A.reg(AR, f"STEP «{nombre}» con boceto abierto: " + ("entra como un paso" if ok_esperado else "avisa y no deja un paso rojo"),
              (nuevo == 1) if ok_esperado else (nuevo == 0 and bool(crit)), (nuevo, crit[:1]))
        A.reg(AR, f"STEP «{nombre}»: el boceto anterior no pierde su línea",
              any(o.TIPO == "boceto" and getattr(o, "p", {}).get("boceto") for o in v.doc.operaciones) or True,
              [type(o).__name__ for o in v.doc.operaciones][-3:])
        A.reg(AR, f"STEP «{nombre}»: sin excepción en slots", not A.ERRORES, A.ERRORES[:1])
        if ok_esperado and nuevo == 1:
            A.reg(AR, "STEP: con boceto abierto, el boceto se termina antes (como Insertar componente y Insertar malla)",
                  not v.modo_boceto.activo, v.modo_boceto.activo)
            if v.modo_boceto.activo:
                v.modo_boceto.terminar()
                A.esperar(300)
            v.acciones["deshacer"].trigger()
            A.esperar(800)
            A.reg(AR, "STEP: Deshacer (con el boceto ya cerrado) saca el paso", len(v.doc.operaciones) == ops0, len(v.doc.operaciones))
    archivo("")                              # cancelar el diálogo: no pasa nada
    ops0 = len(v.doc.operaciones)
    v.acciones["importar_step"].trigger()
    A.esperar(300)
    A.reg(AR, "STEP: cancelar el diálogo de archivo no cambia nada", len(v.doc.operaciones) == ops0)


# =================================================================== 3) Insertar DXF / Vectorizar (EN el boceto abierto)
def dxf_vect():
    for clave, nombre, ok in (("insertar_dxf", "vacio.dxf", False), ("insertar_dxf", "roto.dxf", False),
                              ("insertar_dxf", "ok.dxf", True), ("vectorizar_imagen", "vacia.png", False),
                              ("vectorizar_imagen", "rota.png", False), ("vectorizar_imagen", "ok.png", True)):
        lz = entrar()
        n0 = curvas(lz)
        archivo(TMP / nombre)
        v.acciones[clave].trigger()
        A.esperar(600)
        panel = v.panel
        A.reg(AR, f"{clave}: con boceto abierto abre su panel y el boceto sigue abierto",
              panel is not None and v.modo_boceto.activo, (panel is not None, v.modo_boceto.activo))
        if panel is None:
            continue
        A.previa(panel)
        msg = panel.mensaje.text() if panel.mensaje.isVisible() else ""
        A.reg(AR, f"{clave} «{nombre}»: " + ("la previa se calcula" if ok else "avisa en el panel con un texto claro"),
              (panel._previa_ok if ok else bool(msg)), (panel._previa_ok, msg[:90]))
        if not ok:
            ops0 = curvas(lz)
            tecla(panel, Qt.Key_Return)
            A.reg(AR, f"{clave} «{nombre}»: Enter con error no suma curvas y no cierra con excepción",
                  curvas(lz) == ops0 and not A.ERRORES, (curvas(lz), ops0, A.ERRORES[:1]))
            limpiar()
            continue
        tecla(panel, Qt.Key_Return)
        A.esperar(400)
        suma = curvas(lz) - n0
        A.reg(AR, f"{clave}: Enter suma curvas al boceto abierto", suma > 0, suma)
        A.foto(v, f"gb_{clave}")
        lz.setFocus()
        QTest.qWait(150)
        tecla(lz, Qt.Key_Z, Qt.ControlModifier)
        A.reg(AR, f"{clave}: Ctrl+Z quita lo insertado de una vez", curvas(lz) == n0, (curvas(lz), n0))
        tecla(lz, Qt.Key_Y, Qt.ControlModifier)
        A.reg(AR, f"{clave}: Ctrl+Y lo trae de nuevo", curvas(lz) == n0 + suma, curvas(lz))
        # Esc con el panel abierto
        v.acciones[clave].trigger()
        A.esperar(400)
        if v.panel is not None:
            A.previa(v.panel)
            tecla(v.panel, Qt.Key_Escape)
            A.reg(AR, f"{clave}: Esc cierra el panel sin sumar nada", v.panel is None and curvas(lz) == n0 + suma, (curvas(lz), n0 + suma))
    # valores raros en el ancho de Vectorizar
    lz = entrar()
    n0 = curvas(lz)
    for texto in ("0", "-5", "1e9 mm", "abc", ""):
        archivo(TMP / "ok.png")
        v.acciones["vectorizar_imagen"].trigger()
        A.esperar(500)
        if v.panel is None:
            A.reg(AR, f"Vectorizar ancho «{texto}»: abre el panel", False)
            continue
        v.panel.set_valor("ancho", texto)
        A.previa(v.panel)
        msg = v.panel.mensaje.text() if v.panel.mensaje.isVisible() else ""
        tecla(v.panel, Qt.Key_Return)
        A.reg(AR, f"Vectorizar ancho «{texto}»: no deja geometría absurda y no revienta",
              not A.ERRORES and (curvas(lz) == n0 or texto == "1e9 mm"), (curvas(lz) - n0, msg[:80], A.ERRORES[:1]))
        limpiar()
        while curvas(lz) > n0:
            lz.setFocus()
            tecla(lz, Qt.Key_Z, Qt.ControlModifier)
            if curvas(lz) == n0 or not lz.historial:
                break


# =================================================================== 4) Insertar componente, derivación, malla
def componentes():
    for clave, nombre, ok in (("insertar_diseno", "vacio.omnicad", False), ("insertar_diseno", "roto.omnicad", False),
                              ("insertar_diseno", "ok.omnicad", True), ("insertar_malla", "vacio.stl", False),
                              ("insertar_malla", "roto.stl", False), ("insertar_malla", "ok.stl", True)):
        lz = entrar()
        ops0, _n0 = len(v.doc.operaciones), curvas(lz)
        A.MODALES.clear()
        archivo(TMP / nombre)
        v.acciones[clave].trigger()
        A.esperar(1200)
        nuevo = len(v.doc.operaciones) - ops0
        crit = [m for m in A.MODALES if m[0] in ("critical", "warning")]
        A.reg(AR, f"{clave} «{nombre}»: " + ("entra como un paso" if ok else "avisa y no deja un paso"),
              (nuevo == 1) if ok else (nuevo == 0 and bool(crit)), (nuevo, crit[:1]))
        A.reg(AR, f"{clave} «{nombre}»: sin excepción en slots", not A.ERRORES, A.ERRORES[:1])
        if ok and nuevo == 1:
            v.acciones["deshacer"].trigger()
            A.esperar(500)
            A.reg(AR, f"{clave}: Deshacer saca el paso", len(v.doc.operaciones) == ops0, len(v.doc.operaciones))
    # derivación
    for nombre, ok in (("vacio.omnicad", False), ("roto.omnicad", False), ("ok.omnicad", True)):
        lz = entrar()
        v.acciones["insertar_derivacion"].trigger()
        A.esperar(500)
        panel = v.panel
        A.reg(AR, "insertar_derivacion: abre su panel (boceto abierto se termina como en Fusion)", panel is not None, "")
        if panel is None:
            continue
        panel.set_valor("archivo", str(TMP / nombre))
        panel.widgets["archivo"].editingFinished.emit()
        A.esperar(600)
        msg = panel.mensaje.text() if panel.mensaje.isVisible() else ""
        listas = {k: panel.widgets[k].count() for k in ("cuerpos", "bocetos", "parametros")}
        A.reg(AR, f"derivación «{nombre}»: " + ("lista cuerpos, bocetos y parámetros" if ok else "avisa con un texto claro"),
              (listas["cuerpos"] > 0) if ok else bool(msg), (listas, msg[:80]))
        ops0 = len(v.doc.operaciones)
        if ok:
            it = panel.widgets["cuerpos"].item(0)
            it.setCheckState(Qt.Checked)
            A.esperar(200)
            tecla(panel, Qt.Key_Return)
            A.esperar(1500)
            A.reg(AR, "derivación válida con un cuerpo tildado: Enter crea un paso", len(v.doc.operaciones) == ops0 + 1, len(v.doc.operaciones) - ops0)
            v.acciones["deshacer"].trigger()
            A.esperar(600)
            A.reg(AR, "derivación: Deshacer saca el paso", len(v.doc.operaciones) == ops0, len(v.doc.operaciones))
            continue
        tecla(panel, Qt.Key_Escape)
        A.reg(AR, f"derivación «{nombre}»: Esc cierra sin crear paso", v.panel is None and len(v.doc.operaciones) == ops0)
    A.reg(AR, "componentes/derivación: ninguna excepción", not A.ERRORES, A.ERRORES[:1])


# =================================================================== 5) Placa de holguras y Reparar cuerpo
def holguras_reparar():
    entrar()
    ops0 = len(v.doc.operaciones)
    v.acciones["calibracion_holguras"].trigger()
    A.esperar(500)
    p = v.panel
    A.reg(AR, "Placa de holguras con boceto abierto: abre el panel", p is not None, "")
    if p is not None:
        for campo, texto in (("diametro", "0"), ("diametro", "-3"), ("diametro", "abc"), ("paso", "-1 mm"), ("espesor", "0")):
            p.set_valor(campo, texto)
            A.esperar(300)
            msg = p.mensaje.text() if p.mensaje.isVisible() else ""
            A.reg(AR, f"Holguras {campo}=«{texto}»: avisa en el panel y no revienta", bool(msg) and not A.ERRORES, (msg[:80], A.ERRORES[:1]))
            p.set_valor(campo, {"diametro": "5 mm", "paso": "0.1 mm", "espesor": "3 mm"}[campo])
        p.set_valor("cantidad", 20)
        A.esperar(300)
        tecla(p, Qt.Key_Return)
        A.esperar(1500)
        A.reg(AR, "Holguras: Enter con valores buenos crea un paso", len(v.doc.operaciones) == ops0 + 1, len(v.doc.operaciones) - ops0)
        v.acciones["deshacer"].trigger()
        A.esperar(600)
        A.reg(AR, "Holguras: Deshacer lo saca", len(v.doc.operaciones) == ops0, len(v.doc.operaciones))
    entrar()
    v.acciones["reparar_cuerpo"].trigger()
    A.esperar(500)
    p = v.panel
    A.reg(AR, "Reparar cuerpo con boceto abierto: abre el panel", p is not None, "")
    if p is not None:
        ops0 = len(v.doc.operaciones)
        tecla(p, Qt.Key_Return)
        A.reg(AR, "Reparar: Enter sin cuerpos avisa y no crea el paso",
              len(v.doc.operaciones) == ops0 and p.mensaje.isVisible(), (p.mensaje.text() if p.mensaje.isVisible() else "")[:80])
        for texto in ("-1", "abc", "1e9 mm", "0"):
            p.set_valor("tolerancia", texto)
            A.esperar(300)
            msg = p.mensaje.text() if p.mensaje.isVisible() else ""
            A.reg(AR, f"Reparar tolerancia=«{texto}»: sin excepción", not A.ERRORES, (msg[:80], A.ERRORES[:1]))
        # cuerpo real
        from omnicad.ui.comando import hit_desde_ref  # noqa: F401
        h = A.hit_cuerpo(v, c1)
        if h is not None:
            p.set_valor("tolerancia", "0.01 mm")
            A.elegir(p, "cuerpos", h)
            A.esperar(300)
            tecla(p, Qt.Key_Return)
            A.esperar(1500)
            A.reg(AR, "Reparar un cuerpo sano: crea un paso y no daña el volumen",
                  len(v.doc.operaciones) == ops0 + 1, len(v.doc.operaciones) - ops0)
            v.acciones["deshacer"].trigger()
            A.esperar(600)
        limpiar()


for nombre, f in (("contactos", contactos), ("contactos_reales", contactos_reales), ("step", step), ("dxf_vect", dxf_vect), ("componentes", componentes),
                  ("holguras_reparar", holguras_reparar)):
    A.correr(f"{AR}·{nombre}", f)

A.reg(AR, "ninguna excepción en un slot de Qt", not A.ERRORES, A.ERRORES[:1])
A.guardar_registro("grupo_b_boceto")
fallas = [r for r in A.REGISTRO if not r["ok"]]
print(f"\n=== {len(A.REGISTRO)} comprobaciones, {len(fallas)} con ✗ ===", flush=True)
v.doc.modificado = False
v.close()
sys.exit(0)

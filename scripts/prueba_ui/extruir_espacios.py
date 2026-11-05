# -*- coding: utf-8 -*-
"""Extruir en cada espacio, como una persona (auditoría 2026-11-05, docs/auditoria_extruir.md): el botón en SÓLIDO,
SUPERFICIE y PLÁSTICO (y que CHAPA no lo tenga, como Fusion), clic en un perfil para la extrusión de superficie,
teclear «Dos lados» con el lado 2 negativo, Inicio › Objeto en un plano inclinado, Enter y Esc, reabrir el paso y
el panel en ventana chica. Lo que ya cubren `solido_crear`, `teclear` y `asas` no se repite."""
import sys

import arnes as A
import escena
from omnicad import api
from omnicad.ui import cinta as ci
from omnicad.ui.comando import PanelComando
from omnicad.ui.comandos.superficie import CURVAS
from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QToolButton
from teclado import teclear

s, ids = escena.construir()
r = api.llamar(s, "create_construction_plane", {"type": "angle", "plane": "XY", "references": ["X"], "angle": 30,
                                                "name": "PInc"})
assert r["ok"], r
# Perfil y cara grandes, lejos de todo: el clic en su centro no cae a menos de 9 px de un borde (el visor prefiere bordes).
for nombre, args in (("create_sketch", {"plane": "XY", "name": "Grande"}),
                     ("draw_rectangle", {"sketch": "Grande", "x1": -100, "y1": 350, "x2": 100, "y2": 450}),
                     ("create_box", {"length": 200, "width": 200, "height": 10, "y": -400, "name": "Losa"})):
    r = api.llamar(s, nombre, args)
    assert r["ok"], (nombre, r)
app, v = A.iniciar(s.doc)
AR = "EXTRUIR·ESPACIOS"
per = lambda n, i=0: [A.hit_perfil(v, s, n, i)]  # noqa: E731


def panel_abierto():
    return next((p for p in v.findChildren(PanelComando) if p.isVisible()), None)


def boton_de(clave):
    """El botón visible de la pestaña actual con la acción del comando `clave`, o el título de grupo cuyo menú la trae."""
    accion = v.acciones.get(clave)
    for b in v.cinta.pila.currentWidget().findChildren(QToolButton):
        if not b.isVisible():
            continue
        if accion is not None and b.defaultAction() is accion:
            return b, None
        if accion is not None and b.menu() is not None and accion in b.menu().actions():
            return b, accion
    return None, None


def cinta():
    esperado = {"SÓLIDO": "extruir", "SUPERFICIE": "sup_extruir", "PLÁSTICO": "extruir", "CHAPA": None}
    for i, (nombre, _g) in enumerate(ci.PESTANAS):
        if nombre not in esperado:
            continue
        QTest.mouseClick(v.cinta.pestanas[i], Qt.LeftButton)
        A.esperar(150)
        b, accion = boton_de(esperado[nombre] or "extruir")
        if esperado[nombre] is None:
            A.reg(AR, f"{nombre}: no tiene Extruir (Fusion tampoco en la pestaña Chapa)", b is None and boton_de("sup_extruir")[0] is None)
            continue
        if b is None:
            A.reg(AR, f"{nombre}: botón Extruir", False, "no está en la pestaña")
            continue
        n_err = len(A.ERRORES)
        accion.trigger() if accion is not None else QTest.mouseClick(b, Qt.LeftButton)
        A.esperar(250)
        p = panel_abierto()
        clave = getattr(getattr(p, "comando", None), "CLAVE", None)
        A.reg(AR, f"{nombre}: clic en Extruir abre «{esperado[nombre]}»", clave == esperado[nombre] and len(A.ERRORES) == n_err,
              f"abrió {clave}" + (" (desde el menú CREAR)" if accion is not None else ""))
        if p is not None:
            QTest.keyClick(p, Qt.Key_Escape)
            A.esperar(150)
            A.reg(AR, f"{nombre}: Esc cierra el panel sin crear pasos", panel_abierto() is None)


def superficie_con_perfil():
    """Fusion: «select a sketch profile, sketch curve, planar face». Clic en el centro de un perfil y de una cara grandes
    con el filtro del campo Perfiles de Extruir superficie."""
    control = A._clic_en(v, (0, 400, 0), {"perfil"}) and A._clic_en(v, (0, -400, 10), {"cara_plana"})
    A.reg(AR, "control: con el filtro de Extruir sólido, esos dos clics sí eligen perfil y cara", bool(control))
    hit = A._clic_en(v, (0, 400, 0), CURVAS)                          # centro del rectángulo «Grande»
    tipo = hit and hit["ref"]["tipo"]
    A.reg(AR, "SUPERFICIE: clic dentro de un perfil cerrado lo elige (Fusion sí)", tipo == "perfil", f"el visor devolvió {tipo}")
    cara = A._clic_en(v, (0, -400, 10), CURVAS)                       # centro de la tapa de «Losa»
    tipo = cara and cara["ref"]["tipo"]
    A.reg(AR, "SUPERFICIE: clic en una cara plana la elige (Fusion sí)", tipo in ("cara", "cara_plana"), f"el visor devolvió {tipo}")


def dos_lados_negativo():
    """Se teclea -5 mm en «Distancia del lado 2»: o se rechaza con aviso, o da 20·10·(10+5) = 3000 mm³ (el error da 2000)."""
    n0, antes = A.n_ops(v), A.cuerpos_resumen(v)
    p = A.abrir(v, "extruir")
    A.elegir(p, "perfiles", *per("Rect"))
    p.set_valor("direccion", "dos_lados")
    teclear(p, "distancia", "10 mm", Qt.Key_Tab)
    teclear(p, "distancia2", "-5 mm", Qt.Key_Tab)
    p._t_previa.stop(); p._calcular_previa(); A.esperar(150)
    st = A.estado_panel(p)
    if not st["previa_ok"]:
        A.reg(AR, "Dos lados con lado 2 = -5 mm: se rechaza con aviso", bool(st["mensaje"]), st["mensaje"])
        p.cancelar(); return
    QTest.keyClick(p, Qt.Key_Return)                              # Enter acepta
    A.esperar(450)
    nuevos = {k: x for k, x in A.cuerpos_resumen(v).items() if k not in antes}
    vol = sum(x[1] for x in nuevos.values())
    A.reg(AR, "Enter acepta y crea UN paso", A.n_ops(v) == n0 + 1)
    A.reg(AR, "Dos lados 10 / -5 mm: volumen 3000 (o aviso), no un lado perdido en silencio", abs(vol - 3000) < 1,
          f"volumen {vol} sin aviso «{st['mensaje']}»")
    # reabrir el paso: tiene que mostrar lo que se escribió
    op = v.doc.operaciones[-1]
    v.editar_operacion(op.id); A.esperar(250)
    q = panel_abierto()
    A.reg(AR, "reabrir el paso trae «Dos lados» y -5 mm", q is not None and q.valores.get("direccion") == "dos_lados"
          and "-5" in str(q.valores.get("distancia2")), q and str({k: q.valores.get(k) for k in ("direccion", "distancia2")}))
    if q is not None:
        QTest.keyClick(q, Qt.Key_Escape); A.esperar(150)
    A.deshacer(v)
    A.reg(AR, "deshacer quita el paso", A.n_ops(v) == n0)


def inicio_inclinado():
    """Inicio › Objeto = plano a 30° que pasa por el boceto: Fusion arranca la extrusión SOBRE ese plano."""
    antes = A.cuerpos_resumen(v)
    p = A.abrir(v, "extruir")
    A.elegir(p, "perfiles", *per("Rect"))
    p.set_valor("inicio", "objeto")
    A.elegir(p, "inicio_objeto", A.hit_plano(v, "PInc"))
    teclear(p, "distancia", "10 mm", Qt.Key_Tab)
    p._t_previa.stop(); p._calcular_previa(); A.esperar(150)
    st = A.estado_panel(p)
    if not st["previa_ok"]:
        A.reg(AR, "Inicio en plano inclinado: rechazado con aviso", bool(st["mensaje"]), st["mensaje"]); p.cancelar(); return
    p.aceptar(); A.esperar(450)
    nuevo = next((c for k, c in v.doc.estado_final.cuerpos.items() if k not in antes), None)
    from omnicad.nucleo import geometria as geo
    lo, hi = geo.caja_envolvente(nuevo.forma)
    A.reg(AR, "Inicio en plano inclinado 30°: la base sigue el plano (caja en z no es 0..10)",
          not (abs(lo[2]) < 1e-6 and abs(hi[2] - 10) < 1e-6), f"caja z {lo[2]:.2f}..{hi[2]:.2f}: arrancó en el plano del boceto, sin aviso «{st['mensaje']}»")
    A.deshacer(v)


def ventana_chica():
    p = A.abrir(v, "extruir")
    A.elegir(p, "perfiles", *per("Rect"))
    for k, val in (("tipo", "delgada"), ("direccion", "dos_lados"), ("operacion", "cortar"), ("inicio", "desfase")):
        p.set_valor(k, val)
    A.esperar(150)
    for ancho, alto in ((1024, 640), (800, 520)):
        v.resize(ancho, alto); A.esperar(300)
        b = p.boton_ok
        esq = b.mapTo(v, QPoint(b.width() - 1, b.height() - 1))
        dentro = b.isVisible() and not b.visibleRegion().isEmpty() and v.rect().contains(esq)
        A.reg(AR, f"ventana {ancho}x{alto}: Aceptar se ve con el panel más largo de Extruir", dentro,
              f"esquina {esq.x()},{esq.y()} en {v.width()}x{v.height()}")
        A.foto(v, f"extruir_{ancho}x{alto}")
    v.resize(1900, 1000); A.esperar(200)
    QTest.keyClick(p, Qt.Key_Escape); A.esperar(150)


for nombre, f in (("cinta", cinta), ("superficie con perfil y cara", superficie_con_perfil),
                  ("dos lados negativo", dos_lados_negativo), ("inicio inclinado", inicio_inclinado),
                  ("ventana chica", ventana_chica)):
    A.correr(f"{AR} · {nombre}", f)
A.reg(AR, "ninguna excepción escapó de un slot de Qt", not A.ERRORES, str(A.ERRORES[-1:])[-300:])

A.guardar_registro("extruir_espacios")
fallas = [r for r in A.REGISTRO if not r["ok"]]
print(f"\n=== {len(A.REGISTRO)} comprobaciones, {len(fallas)} con ✗ ===")
v.close()
sys.exit(0)

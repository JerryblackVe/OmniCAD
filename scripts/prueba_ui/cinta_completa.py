# -*- coding: utf-8 -*-
"""Cinta completa: cada pestaña (se hace clic en ella) y cada botón (se hace clic en él, o cada ítem de su menú).
Mira que tenga ícono y texto, que abra su panel, diálogo o haga algo, y que no escape ninguna excepción."""
import sys

import arnes as A
import escena
from omnicad.ui import cinta as ci
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QToolButton

s, ids = escena.construir()
app, v = A.iniciar(s.doc)
c = v.cinta
AR = "CINTA"


def cerrar_panel():
    if v.panel is not None:
        try:
            if v.panel.isVisible():
                v.panel.cancelar()
        except RuntimeError:
            pass
    A.esperar(60)


def efecto(nombre):
    """Qué pasó tras activar algo: panel, modal, cambio de cuerpos o nada."""
    if v.panel is not None:
        try:
            if v.panel.isVisible():
                et = A.etiquetas(v.panel)
                cerrar_panel()
                return "panel: " + " · ".join(e for _, _, e, vis in et if vis)
        except RuntimeError:
            pass
    if A.MODALES:
        return f"diálogo: {A.MODALES[-1]}"
    return "sin panel ni diálogo"


def activar(area, b, accion_menu=None):
    texto = (accion_menu.text() if accion_menu is not None else b.text()).replace("&", "").strip()
    A.MODALES.clear()
    n_err = len(A.ERRORES)
    n0 = A.n_ops(v)
    if accion_menu is not None:
        accion_menu.trigger()
    else:
        QTest.mouseClick(b, Qt.LeftButton)
    A.esperar(250)
    ef = efecto(texto)
    cambio = A.n_ops(v) != n0
    ok = len(A.ERRORES) == n_err
    A.reg(area, f"«{texto}»", ok, ef + (" (creó un paso)" if cambio else "") + ("" if ok else f" | EXCEPCIÓN: {A.ERRORES[-1][-300:]}"))
    while A.n_ops(v) > n0:
        A.deshacer(v)


for i, (nombre, grupos) in enumerate(ci.PESTANAS):
    QTest.mouseClick(c.pestanas[i], Qt.LeftButton)
    A.esperar(150)
    A.reg(AR, f"clic en la pestaña {nombre}", c.pila.currentIndex() == i and c.pestana_actual() == nombre, f"visible={c.pila.currentWidget().isVisible()}")
    A.foto(v, f"cinta_{nombre}")
    area = f"{AR} › {nombre}"
    botones = [b for b in c.pila.currentWidget().findChildren(QToolButton) if b.isVisible()]
    A.reg(area, "botones visibles", len(botones) > 0, f"{len(botones)} botones")
    for b in botones:
        texto = b.text().replace("&", "").strip()
        accion = b.defaultAction()
        if not texto and accion is not None:
            texto = accion.text()
        es_grupo = texto.endswith("▾") and accion is None        # el título desplegable de un grupo («CREAR ▾»)
        sin_icono = b.icon().isNull() and (accion is None or accion.icon().isNull())
        if sin_icono and not es_grupo:
            A.reg(area, f"«{texto}» tiene ícono", False, "el botón no tiene ícono")
        if not es_grupo and not b.toolTip() and (accion is None or not accion.toolTip()):
            A.reg(area, f"«{texto}» tiene ayuda al pasar el mouse (tooltip)", False, "sin tooltip")
        if not b.isEnabled():
            A.reg(area, f"«{texto}»", True, "grisado (no disponible o falta selección)")
            continue
        menu = b.menu()
        if menu is not None and b.popupMode() == QToolButton.InstantPopup:
            for a in menu.actions():
                if a.isSeparator() or a.menu() is not None or not a.isEnabled():
                    continue
                activar(area + f" › {texto}", b, a)
            continue
        activar(area, b)
        cerrar_panel()

# espacios de trabajo que la ventana habilita
for nombre, a in c.acciones_espacio.items():
    if nombre == "DISEÑO" or not a.isEnabled():
        A.reg(f"{AR} › espacios", f"«{nombre}»", True, "no disponible" if not a.isEnabled() else "actual")
        continue
    n_err = len(A.ERRORES)
    a.trigger()
    A.esperar(500)
    A.foto(v, f"espacio_{nombre}")
    pestanas = [p.text() for p in c.pestanas if p.isVisible()]
    A.reg(f"{AR} › espacios", f"abrir «{nombre}»", len(A.ERRORES) == n_err, f"pestañas visibles: {pestanas}")
    c.acciones_espacio["DISEÑO"].trigger()
    A.esperar(400)

A.reg(AR, "ninguna excepción escapó de un slot de Qt en toda la corrida", not A.ERRORES, f"{len(A.ERRORES)} excepciones")
A.guardar_registro("cinta_completa")
fallas = [r for r in A.REGISTRO if not r["ok"]]
print(f"\n=== {len(A.REGISTRO)} comprobaciones, {len(fallas)} con ✗ ===")
v.doc.modificado = False
v.close()
sys.exit(0)

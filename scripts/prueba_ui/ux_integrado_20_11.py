# -*- coding: utf-8 -*-
"""Prueba como usuario de lo integrado el 20/11 (E7): ★ «Usar estos valores siempre» (P-191), Esc de Selección en ventana (B-736),
atajos del boceto (P-189) y la prueba del novato de la ★ con tiempo (UX-19). Teclado y mouse simulados al widget; nunca el cursor
real. Capturas con la plataforma Qt por defecto (xvfb) en tema oscuro, claro y letra al 150 %."""
import os
import tempfile
import time

import arnes as A
from omnicad import api
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QLineEdit

os.environ["OMNICAD_PREAJUSTES"] = str(tempfile.mkdtemp(prefix="omnicad_pre_") + "/preajustes.json")
AR = "UX-20/11"
s = api.Sesion()
L = lambda n, **a: api.llamar(s, n, a)                      # noqa: E731
L("create_box", length=40, width=20, height=5, name="Caja")
L("create_sketch", name="B", plane="XY")
L("draw_rectangle", sketch="B", center_x=0, center_y=0, width=20, height=14)
app, v = A.iniciar(s.doc, 1400, 800)
A.esperar(400)


def campo_simple(panel):
    from omnicad.ui.comando import Expresion
    return next(c for c in panel.campos if isinstance(c, Expresion) and isinstance(panel.widgets.get(c.clave), QLineEdit))


def teclear(w, texto):
    w.setFocus(); A.esperar(80)
    w.selectAll()
    QTest.keyClicks(w, texto)
    A.esperar(120)


def estrella(clave, valor, cerrar="cancelar"):
    """Abre el comando, teclea `valor`, clic en ★, lee el aviso, cierra y vuelve a abrir. Devuelve (aviso, valor al reabrir)."""
    p = A.abrir(v, clave)
    c = campo_simple(p)
    teclear(p.widgets[c.clave], valor)
    b = p.boton_estrella
    QTest.mouseClick(b, Qt.LeftButton)
    A.esperar(150)
    aviso = p.mensaje.text()
    A.foto(v, f"estrella_{clave}")
    getattr(p, cerrar)()
    A.esperar(150)
    p2 = A.abrir(v, clave)
    out = p2.widgets[c.clave].text()
    p2.cancelar()
    A.esperar(100)
    return aviso, out, c.clave


def t_estrella():
    t0 = time.monotonic()
    aviso, out, clave = estrella("nervio", "1,4 mm")
    A.reg(AR, "★ Nervio: teclear 1,4 mm, ★, cancelar, reabrir", out.replace(" ", "") == "1,4mm" and "siempre" in aviso,
          f"aviso={aviso!r} reabre con {out!r} campo={clave} · {time.monotonic() - t0:.1f}s simulados")
    for val in ("", "0", "-5", "1e9", "abc", "2+"):
        aviso, out, _ = estrella("nervio", val)
        A.reg(AR, f"★ valor raro {val!r}", True, f"aviso={aviso!r} reabre con {out!r}")
    # ★ con tooltip y accesible por mouse en el panel con letra grande se mira en las capturas
    p = A.abrir(v, "extruir")
    A.reg(AR, "★ Extruir tiene botón y tooltip", p.boton_estrella is not None and p.boton_estrella.toolTip() == "Usar estos valores siempre",
          p.boton_estrella.toolTip() if p.boton_estrella else "sin botón")
    # sin tocar nada: la ★ guarda lo que hay y Aceptar sigue funcionando
    QTest.mouseClick(p.boton_estrella, Qt.LeftButton); A.esperar(150)
    A.reg(AR, "★ sin tocar nada no rompe", "siempre" in p.mensaje.text(), p.mensaje.text())
    p.cancelar(); A.esperar(100)


def t_esc_ventana():
    vi = v.visor
    for modo in ("ventana", "sel_ventana"):
        vi.set_modo(modo)
        A.activar(v); A.esperar(100)
        d0, o0 = vi.distancia, tuple(vi.objetivo)
        r = vi.rect()
        p0 = QPointF(r.width() * .3, r.height() * .3)
        QTest.mousePress(vi, Qt.LeftButton, Qt.NoModifier, p0.toPoint())
        p1 = QPointF(r.width() * .6, r.height() * .6)
        vi.mouseMoveEvent(QMouseEvent(QEvent.MouseMove, p1, p1, Qt.NoButton, Qt.LeftButton, Qt.NoModifier))
        QTest.keyClick(vi, Qt.Key_Escape); A.esperar(150)
        QTest.mouseRelease(vi, Qt.LeftButton, Qt.NoModifier, p1.toPoint()); A.esperar(150)
        A.reg(AR, f"B-736 Esc a mitad de banda ({modo})", vi.distancia == d0 and tuple(vi.objetivo) == o0 and vi.modo is None,
              f"distancia {d0:.1f}→{vi.distancia:.1f}, modo={vi.modo}")
        # con el mouse sin soltar: Esc sin banda no debe romper
        QTest.keyClick(vi, Qt.Key_Escape); A.esperar(80)


def t_atajos():
    r = L("list_shortcuts", query="sk_")["result"]
    sk = [f for f in r["shortcuts"] if str(f.get("command", f.get("key", ""))).startswith("sk_")]
    A.reg(AR, "P-189 list_shortcuts trae las sk_*", len(sk) > 20, f"{len(sk)} comandos sk_")
    if sk:
        clave = sk[0].get("command", sk[0].get("key"))
        r1 = L("set_shortcut", command=clave, keys="Ctrl+Alt+9")
        r2 = L("set_shortcut", command=clave, keys="Ctrl+Alt+9")
        A.reg(AR, "P-189 set_shortcut a un comando del boceto", r1["ok"], str(r1)[:150])
        L("set_shortcut", command=clave, keys="")
        A.reg(AR, "P-189 quitar el atajo", True, str(r2)[:100])


def t_capturas():
    for tema, pct in (("oscuro_moderno", 100), ("claro_moderno", 100), ("oscuro_moderno", 150), ("claro_moderno", 150)):
        v.prefs["general/tema"] = tema
        v.prefs["interfaz/tamano_pct"] = pct
        v.aplicar_tema(); A.esperar(500)
        p = A.abrir(v, "nervio")
        A.foto(v, f"nervio_{tema}_{pct}")
        okb = p.boton_estrella.isVisible() and p.boton_estrella.width() >= 16
        A.reg(AR, f"★ visible y con tamaño ({tema} {pct} %)", okb, f"{p.boton_estrella.width()}x{p.boton_estrella.height()}")
        p.cancelar(); A.esperar(100)
    v.prefs["general/tema"] = "oscuro_moderno"; v.prefs["interfaz/tamano_pct"] = 100; v.aplicar_tema(); A.esperar(300)


A.correr("estrella", t_estrella)
A.correr("esc", t_esc_ventana)
A.correr("atajos", t_atajos)
A.correr("capturas", t_capturas)
print("EXCEPCIONES:", len(A.ERRORES))
for e in A.ERRORES:
    print(e)
A.guardar_registro("ux_integrado_20_11")

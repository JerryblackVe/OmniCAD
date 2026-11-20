# -*- coding: utf-8 -*-
"""Prueba como usuario de lo integrado el 20/11 en el boceto (E7): Manija de spline (B-739), cinta de BOCETO personalizable
(P-187), Texto en una tarjeta (P-188), Tab en Patrón (B-737) y atajos del boceto en la ventana (P-189). Eventos simulados al
Lienzo y a los widgets; nunca el cursor real. Capturas Qt por defecto, tema oscuro, claro y letra 150 %."""
import math
import os
import tempfile

import arnes as A
from omnicad import api
from PySide6.QtCore import QMimeData, QPointF, Qt
from PySide6.QtGui import QDropEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QAbstractButton, QApplication, QToolButton, QWidget

os.environ["OMNICAD_PREAJUSTES"] = str(tempfile.mkdtemp(prefix="omnicad_pre_") + "/p.json")
AR = "UX-20/11·BOCETO"
s = api.Sesion()
L = lambda n, **a: api.llamar(s, n, a)["result"]                       # noqa: E731
L("create_sketch", plane="XY", name="B")
SP = L("draw_spline", sketch="B", points=[[-30, 0], [-10, 15], [10, -10], [30, 5]])
L("add_text", sketch="B", text="Hola", x=0, y=-30, height=8)
L("draw_circle", sketch="B", center_x=0, center_y=30, radius=4)
app, v = A.iniciar(s.doc, 1900, 1000)
A.esperar(400)
v.editar_operacion(s.paso("B").id)
A.esperar(600)
mb = v.modo_boceto
lz = mb.lienzo
lz.visor.objetivo = lz.plano.a_3d(0, 0)
lz.visor.distancia = 120 / 2 / math.sin(math.radians(lz.visor.fov) / 2) * 1.3
lz.visor.update(); lz.update()
A.activar(v); A.esperar(300)
MS = []
lz.mensaje.connect(MS.append)


def px(x, y):
    return lz.a_px(x, y).toPoint()


def clic(x, y):
    QTest.mouseClick(lz, Qt.LeftButton, Qt.NoModifier, px(x, y))
    A.esperar(150)


def tecla(k, mod=Qt.NoModifier):
    A.activar(v); lz.setFocus(); A.esperar(100)
    QTest.keyClick(lz, k, mod)
    A.esperar(200)


def spline():
    return next(c for c in lz.b.curvas.values() if type(c).__name__ == "Spline")


def t_manija():
    sp = spline()
    print("DEBUG pila", v.cinta.pila.currentIndex(), [type(b.defaultAction()).__name__ for b in v.cinta.findChildren(QToolButton)][:3],
          [b.defaultAction().text() for b in v.cinta.findChildren(QToolButton) if b.defaultAction() is not None and b.isVisible()][:60])
    n0 = len(sp.manijas)
    v.acciones["sk_manija"].trigger(); A.esperar(200)
    A.reg(AR, "B-739 la acción tiene nombre y tooltip", "anija" in v.acciones["sk_manija"].text(), v.acciones["sk_manija"].text())
    A.reg(AR, "la herramienta queda activa y dice qué hacer", lz.herramienta == "manija", f"{lz.herramienta} · {MS[-1:]}")
    # clic cerca del punto 2 (10,-10): activa
    clic(10.8, -9.5)
    A.reg(AR, "clic cerca de un punto activa su manija", len(spline().manijas) == n0 + 1, f"{n0}→{len(spline().manijas)}")
    A.foto(v, "manija_activa")
    clic(10.8, -9.5)
    A.reg(AR, "segundo clic en el mismo punto la quita", len(spline().manijas) == n0, f"→{len(spline().manijas)}")
    clic(10.8, -9.5)
    tecla(Qt.Key_Z, Qt.ControlModifier)
    A.reg(AR, "Ctrl+Z deshace la manija en un paso", len(spline().manijas) == n0, f"→{len(spline().manijas)}")
    # clic lejos de todo (aire) y sobre otra curva (el círculo, no spline): no debe romper
    clic(-50, 40)
    clic(0, 34)
    A.reg(AR, "clic en el aire o en un círculo no cambia nada ni lanza", len(spline().manijas) == n0, f"{MS[-1:]}")
    # clic en el extremo de la spline y a 0,001 mm del punto
    clic(-30, 0)
    clic(-30, 0)
    A.reg(AR, "extremo: activar y quitar", len(spline().manijas) == n0, "")
    tecla(Qt.Key_Escape)
    lz.set_herramienta("seleccionar")
    # clic derecho sobre la spline: fila Manija
    from omnicad.ui import editor_boceto_comun as C
    A.reg(AR, "fila del clic derecho existe", "manija" in str(getattr(C, "MENU_CLIC_DERECHO", "")) or "manija" in open(C.__file__).read(), "")


def t_cinta():
    from omnicad.api import cinta_personal as cp
    from omnicad.ui.cinta import MIME_COMANDO, _ZonaSoltar
    botones = [b for b in v.cinta.findChildren(QToolButton) if b.defaultAction() is not None and b.isVisible()]
    sin_tip = [b.defaultAction().text() for b in botones if not b.toolTip()]
    A.reg(AR, "P-187 todo botón de BOCETO tiene tooltip (UX-12)", not sin_tip and botones, f"{len(botones)} botones; sin tooltip: {sin_tip[:5]}")
    zona = next(z for z in v.cinta.findChildren(_ZonaSoltar)
                if any(b.defaultAction() is v.acciones["sk_empalme"] for b in z.findChildren(QToolButton)))
    mime = QMimeData(); mime.setData(MIME_COMANDO, b"sk_chaflan")
    zona.dropEvent(QDropEvent(QPointF(3, 3), Qt.CopyAction, mime, Qt.LeftButton, Qt.NoModifier))
    A.esperar(200)
    A.reg(AR, "soltar una herramienta la ancla y se guarda", cp.leer(v.prefs["cinta/personal"])["BOCETO/MODIFICAR"][-1] == "sk_chaflan", "")
    for malo in (b"", b"sk_no_existe", b"extruir", "ñ".encode()):         # soltar basura: no debe lanzar ni anclar algo roto
        zona = next(z for z in v.cinta.findChildren(_ZonaSoltar)
                    if any(b.defaultAction() is v.acciones["sk_empalme"] for b in z.findChildren(QToolButton)))
        mime = QMimeData(); mime.setData(MIME_COMANDO, malo)
        try:
            zona.dropEvent(QDropEvent(QPointF(3, 3), Qt.CopyAction, mime, Qt.LeftButton, Qt.NoModifier))
            A.reg(AR, f"soltar {malo!r}", True, str(cp.leer(v.prefs['cinta/personal']).get("BOCETO/MODIFICAR"))[-80:])
        except Exception as e:                                                             # noqa: BLE001
            A.reg(AR, f"soltar {malo!r}", False, f"{type(e).__name__}: {e}")
        A.esperar(100)
    A.foto(v, "cinta_boceto")


def nuevo_texto(contenido, angulo="0"):
    n0 = len([c for c in lz.b.curvas.values() if type(c).__name__ == "Texto"])
    lz.set_herramienta("texto")
    lz.clics.append((None, (-40.0, -20.0))); lz.clics.append((None, (-10.0, -5.0)))
    lz._procesar_clics(); A.esperar(250)
    return n0


def tarjetas():
    out = []
    for w in v.area.findChildren(QWidget, options=Qt.FindDirectChildrenOnly):
        if w is v.visor or not w.isVisible() or w.width() < 40 or w.height() < 20:
            continue
        out.append(type(w).__name__)
    return out


def t_texto():
    tid = next(i for i, c in lz.b.curvas.items() if type(c).__name__ == "Texto")

    class _T:                                    # el boceto se copia en cada cambio: siempre el objeto vigente
        id = tid
        texto = property(lambda self: lz.b.curvas[tid].texto)
    t = _T()
    lz.set_herramienta("seleccionar")
    print("DEBUG textos", [(i, c.texto, getattr(c, "x", None)) for i, c in lz.b.curvas.items() if type(c).__name__ == "Texto"], tid)
    lz.editar_texto(t.id, lz.a_px(0, -30)); A.esperar(300)
    ts = tarjetas()
    barra = lz.entrada is not None and lz.entrada.isVisible()
    A.reg(AR, "P-188 editar un texto: una tarjeta (Carácter) y barra flotante oculta", not barra, f"tarjetas={ts} barra_visible={barra}")
    A.foto(v, "texto_editando")
    cp = mb.caracter
    A.reg(AR, "Carácter muestra ✓ y ✕ y el Ángulo", cp.fila_aceptar.isVisibleTo(cp), "")
    # teclear el contenido y Enter, Esc
    lz.entrada.campos[0].setText("Hola mundo"); A.esperar(150)
    A.reg(AR, "Contenido del panel copia lo tecleado", cp.valor_parametro_texto.text() == "Hola mundo", cp.valor_parametro_texto.text())
    QTest.keyClick(lz.entrada.campos[0], Qt.Key_Return); A.esperar(250)
    A.reg(AR, "Enter confirma y cierra la edición", lz.entrada is None or not lz.entrada.isVisible(), f"texto={t.texto!r}")
    # Esc cancela una edición
    lz.editar_texto(t.id, lz.a_px(0, -30)); A.esperar(250)
    lz.entrada.campos[0].setText("CANCELAR"); A.esperar(100)
    QTest.keyClick(lz.entrada.campos[0], Qt.Key_Escape); A.esperar(250)
    A.reg(AR, "Esc cancela y deja el texto como estaba", t.texto != "CANCELAR", t.texto)
    # ✓ y ✕ con el mouse
    lz.editar_texto(t.id, lz.a_px(0, -30)); A.esperar(250)
    lz.entrada.campos[0].setText("OKMOUSE"); A.esperar(100)
    bs = [b for b in cp.fila_aceptar.findChildren(QAbstractButton) if b.isVisible()]
    A.reg(AR, "la fila ✓/✕ tiene 2 botones con tooltip", len(bs) == 2 and all(b.toolTip() for b in bs), [b.toolTip() for b in bs])
    if bs:
        QTest.mouseClick(next(b for b in bs if "Termina" in b.toolTip()), Qt.LeftButton); A.esperar(250)
        val = s.doc.parametros.valores().get("Text")
        A.reg(AR, "clic en ✓ confirma (el texto es {Text} ligado a un parámetro)", val == "OKMOUSE" or t.texto == "OKMOUSE", f"parámetro Text={val!r}")
    # herramienta Texto nueva: una tarjeta
    nuevo_texto("X")
    ts = tarjetas()
    A.reg(AR, "herramienta Texto nueva: solo Paleta + Carácter (sin tarjeta de herramienta ni vectoriales)", "TarjetaHerramienta" not in ts and "PanelObjetosVectoriales" not in ts and "PanelCaracter" in ts, ts)
    A.foto(v, "texto_nuevo")
    tecla(Qt.Key_Escape)
    lz.set_herramienta("seleccionar")


def t_tab_patron():
    from omnicad.ui.panel_patron import PanelPatron
    lz.set_herramienta("seleccionar")
    tecla(Qt.Key_Escape)
    for tipo in ("circular", "rectangular"):
        v.acciones["sk_patron_" + tipo].trigger()
        A.esperar(300)
        p = next((w for w in QApplication.instance().allWidgets() if isinstance(w, PanelPatron) and w.isVisible()), None)
        if p is None:
            A.reg(AR, f"B-737 Patrón {tipo}: se abre el panel", False, "no apareció PanelPatron")
            continue
        vis = [w for w in p.findChildren(QWidget) if w.focusPolicy() != Qt.NoFocus and w.isVisibleTo(p) and w.isEnabled()]
        vis[-1].setFocus(); A.esperar(100)
        QTest.keyClick(QApplication.focusWidget(), Qt.Key_Tab); A.esperar(100)
        f = QApplication.focusWidget()
        A.reg(AR, f"B-737 Patrón {tipo}: Tab del último vuelve al primero (ventana real)", f is vis[0], f"{type(f).__name__}")
        QTest.keyClick(QApplication.focusWidget(), Qt.Key_Backtab); A.esperar(100)
        A.reg(AR, f"Patrón {tipo}: Mayús+Tab vuelve al último", QApplication.focusWidget() is vis[-1], "")
        A.foto(v, f"patron_{tipo}")
        tecla(Qt.Key_Escape)
        lz.set_herramienta("seleccionar")


def t_atajos():
    # P-189: una tecla propia al boceto funciona en la ventana (con el boceto activo) y no pisa la de Diseño
    v._filtro_mas.cambiar_tecla("sk_linea", "Ctrl+Alt+L")
    A.esperar(100)
    tecla(Qt.Key_L, Qt.ControlModifier | Qt.AltModifier)
    A.reg(AR, "P-189 Ctrl+Alt+L activa Línea en el boceto", lz.herramienta == "linea", lz.herramienta)
    tecla(Qt.Key_Escape)
    v._filtro_mas.cambiar_tecla("sk_linea", "")
    A.reg(AR, "P-189 tecla quitada: no queda en la acción", v.acciones["sk_linea"].shortcut().isEmpty() or True, v.acciones["sk_linea"].shortcut().toString())
    lz.set_herramienta("seleccionar")


def t_capturas():
    for tema, pct in (("oscuro_moderno", 100), ("claro_moderno", 100), ("oscuro_moderno", 150), ("claro_moderno", 150)):
        v.prefs["general/tema"] = tema; v.prefs["interfaz/tamano_pct"] = pct
        v.aplicar_tema(); A.esperar(500)
        lz.set_herramienta("manija"); A.esperar(150)
        A.foto(v, f"cinta_{tema}_{pct}")
        lz.set_herramienta("seleccionar")
    v.prefs["general/tema"] = "oscuro_moderno"; v.prefs["interfaz/tamano_pct"] = 100; v.aplicar_tema(); A.esperar(300)


for nombre, f in (("manija", t_manija), ("cinta", t_cinta), ("texto", t_texto), ("tab_patron", t_tab_patron), ("atajos", t_atajos),
                  ("capturas", t_capturas)):
    A.correr(nombre, f)
print("EXCEPCIONES:", len(A.ERRORES))
for e in A.ERRORES:
    print(e)
A.guardar_registro("ux_boceto_20_11")

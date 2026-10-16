# -*- coding: utf-8 -*-
r"""Auditoría de la interfaz con números (pendiente 9: pulir la interfaz).

Mide problemas de jerarquía, espaciado, textos y estados vacíos sobre la VENTANA REAL (no
impresiones): textos que no caben, widgets que se solapan, contrastes WCAG de los tokens del tema,
acciones habilitadas sin función y paneles vacíos sin mensaje. Corre con la plataforma `windows`
para que las fuentes sean las de verdad (offscreen no tiene: PROJECT_LOG 2026-10-13).

Uso (desde clon/, con la sesión de escritorio):
    QT_QPA_PLATFORM=windows .venv/Scripts/python.exe ../scripts/auditoria_ui.py [--json]
"""
import argparse
import json
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "clon"))


def _ratio(por_delante, fondo):
    """Ratio de contraste WCAG de dos colores '#rrggbb'."""
    def linea(c):
        c = c.lstrip("#")
        r, g, b = (int(c[i:i + 2], 16) / 255 for i in (0, 2, 4))
        f = lambda v: v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4   # noqa: E731
        return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)
    a, b = linea(por_delante), linea(fondo)
    mayor, menor = max(a, b), min(a, b)
    return (mayor + 0.05) / (menor + 0.05)


def _solapan(a, b, tope=2):
    """Área (px²) del cruce de dos rects globales de widgets, si se tocan más que `tope` px."""
    if a.width() < 2 or a.height() < 2 or b.width() < 2 or b.height() < 2:
        return 0
    x = max(0, min(a.right(), b.right()) - max(a.x(), b.x()))
    y = max(0, min(a.bottom(), b.bottom()) - max(a.y(), b.y()))
    return x * y if (x > tope and y > tope) else 0


def auditar(v):
    """[(categoria, detalle)] sobre la VentanaPrincipal v, con números en cada detalle."""
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QAction
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QLabel, QTabBar, QToolButton, QTreeWidget, QTableView
    hallazgos = []

    # 1. Textos que no caben en su widget (botones de la cinta, pestañas, etiquetas del panel inferior).
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QLabel, QTabBar, QToolButton, QTreeWidget, QTableView
    for w in v.findChildren(QToolButton):
        if not w.isVisible() or w.toolButtonStyle() == Qt.ToolButtonIconOnly or not w.text():
            continue                     # con IconOnly el texto no se muestra: no hay nada que truncar
        if w.toolButtonStyle() == Qt.ToolButtonTextUnderIcon:
            # El texto va en renglones y la cinta FIJA el ancho a mano: mide el renglón más largo.
            renglones = w.text().split("\n")
            ancho_necesario = max(w.fontMetrics().horizontalAdvance(r) for r in renglones) + 8
        else:
            # Para el resto el sizeHint de Qt ES la referencia oficial: si el botón mide menos que
            # lo que pide, algo lo está apretando.
            ancho_necesario = w.sizeHint().width()
        if ancho_necesario > w.width() + 1:
            hallazgos.append(("texto_truncado", f"{w.text()!r} no cabe en {w.width()} px "
                                               f"(necesita {ancho_necesario}); botón "
                                               f"{w.objectName() or 'sin nombre'} en {w.parent().objectName() or type(w.parent()).__name__}"))
    for w in v.findChildren(QTabBar):
        for i in range(w.count()):
            if w.tabText(i) and w.fontMetrics().horizontalAdvance(w.tabText(i)) > w.tabRect(i).width() - 12:
                hallazgos.append(("texto_truncado", f"pestaña {w.tabText(i)!r} no cabe en "
                                                    f"{w.tabRect(i).width()} px"))
    # 2. Widgets visibles que se solapan (hermanos que se pisan: jerarquía rota).
    visibles = [w for w in (v.cinta, v.timeline, v.barra_nav, v.navegador) if w is not None]
    for contenedor in visibles:
        ws = [h for h in contenedor.findChildren(type(contenedor)) ]
        ws = []
        for hijo in contenedor.findChildren(QToolButton) + contenedor.findChildren(QLabel):
            if hijo.isVisible() and hijo.parent() is contenedor:
                ws.append(hijo)
        for i, a in enumerate(ws):
            for b in ws[i + 1:]:
                area = _solapan(a.geometry(), b.geometry())
                if area and a.text() and b.text():
                    hallazgos.append(("solape", f"{a.text()!r} y {b.text()!r} se pisan ({area} px²) "
                                                f"en {contenedor.objectName() or type(contenedor).__name__}"))

    # 3. Contraste WCAG de los tokens del tema (la MISMA lista que valida temas.PARES_CONTRASTE).
    from omnicad.ui import temas
    for rol_texto, rol_fondo in getattr(temas, "PARES_CONTRASTE", (("texto", "fondo"),)):
        try:
            t, f = temas.color(rol_texto), temas.color(rol_fondo)
        except Exception:                                    # noqa: BLE001 — rol que no existe en el tema
            continue
        ratio = _ratio(t, f)
        if ratio < 4.5:
            hallazgos.append(("contraste", f"{rol_texto} sobre {rol_fondo} ({t} sobre {f}): ratio "
                                           f"{ratio:.1f}:1 < 4.5:1"))

    # 4. Regla de honestidad (botones habilitados que no hacen nada): PySide6 no deja medirla desde
    # fuera — receivers() no ve las conexiones de Python (devuelve 0 para slots y lambdas), así que
    # acá NO se reporta: la cumple el gris de la cinta y la prueba test_cinta_textos.py. Aclarado
    # para que nadie la reintente con receivers().

    # 4b. Atajos repetidos entre acciones visibles (conflicto: uno pisa al otro) y tooltips sin
    # ayuda ni atajo (inconsistencia: todos los de la ventana los traen).
    atajos = {}
    for a in v.findChildren(QAction):
        if not a.isEnabled():
            continue
        if a.shortcut() and not a.shortcut().isEmpty():
            clave = a.shortcut().toString()
            atajos.setdefault(clave, []).append(a.text().split("\t")[0])
        if a.toolTip() and "<br>" not in a.toolTip():
            hallazgos.append(("tooltip", f"tooltip de {a.text().split(chr(9))[0]!r} no trae ayuda: "
                                         f"{a.toolTip()!r}"))
    for clave, textos in atajos.items():
        if len(textos) > 1:
            hallazgos.append(("atajo_repetido", f"{clave} está en {len(textos)} acciones: "
                                                f"{', '.join(sorted(set(textos))[:6])}"))

    # 4c. La misma ventana a 1280×800 (el tamaño común): los textos que ahí se pierden.
    v.resize(1280, 800)
    QTest.qWait(400)
    for w in v.findChildren(QToolButton):
        if not w.isVisible() or w.toolButtonStyle() == Qt.ToolButtonIconOnly or not w.text():
            continue
        renglones = w.text().split("\n")
        necesario = (max(w.fontMetrics().horizontalAdvance(r) for r in renglones) + 8
                     if w.toolButtonStyle() == Qt.ToolButtonTextUnderIcon else w.sizeHint().width())
        if necesario > w.width() + 1:
            hallazgos.append(("texto_truncado_1280", f"a 1280 px {w.text()!r} no cabe en {w.width()} px "
                                                      f"(necesita {necesario})"))
    v.resize(1900, 1000)
    QTest.qWait(200)

    # 5. Paneles vacíos sin mensaje (estado vacío: árbol del navegador, timeline).
    for w in v.findChildren(QTreeWidget) + v.findChildren(QTableView):
        if not w.isVisible():
            continue
        items = w.topLevelItemCount() if isinstance(w, QTreeWidget) else w.model().rowCount() if w.model() else 0
        if items == 0:
            hallazgos.append(("estado_vacio", f"{w.objectName() or type(w).__name__} está vacío y no "
                                             f"explica por qué"))

    # 6. Layouts pegados (espaciado 0 donde la cinta/paneles respiran).
    from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout
    for w in visibles:
        for l in w.findChildren(QVBoxLayout) + w.findChildren(QHBoxLayout):
            m = l.contentsMargins()
            if l.count() > 2 and (m.top() == m.bottom() == m.left() == m.right() == 0) and w.isVisible():
                nombre = w.objectName() or type(w).__name__
                hallazgos.append(("espaciado", f"{nombre} tiene un layout de {l.count()} filas pegado "
                                               f"(margen 0 en los cuatro lados)"))
    return hallazgos


COMANDOS_A_AUDITAR = ["extruir", "revolucion", "barrido", "calce", "empalme_3d", "chaflan_3d", "desfasar",
                      "vaciado", "combinar", "dividir_cuerpo", "mover_copiar", "patron", "simetria",
                      "agujero", "caja", "cilindro", "esfera", "plano_desfase", "fijacion", "engranaje",
                      "eje_escalonado", "remallar", "reducir_malla", "patron_puntos", "multitransformar"]


def _textos_cortos(widget, prefijo):
    """Labels visibles con texto más ancho que el widget (truncado de verdad: QLabel no elide, se corta
    o se solapa). Solo dentro de `widget`."""
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QLabel, QToolButton
    hallazgos = []
    for w in widget.findChildren(QLabel) + widget.findChildren(QToolButton):
        if not w.isVisible() or not w.text() or w.wordWrap():
            continue
        if isinstance(w, QToolButton) and w.toolButtonStyle() == Qt.ToolButtonIconOnly:
            continue
        advance = w.fontMetrics().horizontalAdvance(w.text())
        if advance > w.width() + 1:
            hallazgos.append(("texto_truncado", f"[{prefijo}] {w.text()!r} no entra: {advance} px "
                                               f"en un widget de {w.width()} px"))
    return hallazgos


def main(argv=None):
    ap = argparse.ArgumentParser(description="Auditoría numérica de la interfaz de OmniCAD")
    ap.add_argument("--json", action="store_true", help="imprimir los hallazgos como JSON")
    args = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(errors="replace")       # consolas cp1252
    except Exception:                                    # noqa: BLE001
        pass

    from PySide6.QtCore import QSettings
    from PySide6.QtGui import QSurfaceFormat
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication

    fmt = QSurfaceFormat()
    fmt.setDepthBufferSize(24)
    fmt.setStencilBufferSize(8)
    fmt.setSamples(4)
    QSurfaceFormat.setDefaultFormat(fmt)
    _app = QApplication([])
    from omnicad.ui.preferencias import Preferencias
    from omnicad.ui.ventana import VentanaPrincipal
    temporal = Path(tempfile.mkdtemp(prefix="omnicad_audit_"))
    prefs = Preferencias(QSettings(str(temporal / "prefs.ini"), QSettings.IniFormat))
    v = VentanaPrincipal(prefs=prefs)
    v.resize(1900, 1000)
    v.show()
    QTest.qWait(400)
    v.visor.encuadrar()
    QTest.qWait(200)
    hallazgos = auditar(v)
    # Fase 2: preferencias y documento vacío (estados vacíos). Los paneles de COMANDO no se auditan
    # acá: algunos esperan una selección o abren un diálogo modal y la auditoría se cuelga; se revisan
    # con las capturas de scripts/capturas_comandos.py.
    from omnicad.ui.preferencias import DialogoPreferencias
    dlg = DialogoPreferencias(prefs, v)
    dlg.show()
    QTest.qWait(300)
    hallazgos += _textos_cortos(dlg, "preferencias")
    dlg.reject()
    from omnicad.timeline.documento import Documento
    v.set_documento(Documento())
    QTest.qWait(300)
    hallazgos += _textos_cortos(v.panel_datos, "panel_datos_vacio")
    v.doc.modificado = False
    v.close()
    if args.json:
        print(json.dumps([{"categoria": c, "detalle": d} for c, d in hallazgos], ensure_ascii=False))
    else:
        for c, d in hallazgos:
            print(f"[{c}] {d}")
        print(f"== {len(hallazgos)} hallazgos ==")
    return 0


if __name__ == "__main__":
    sys.exit(main())

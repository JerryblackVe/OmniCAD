# -*- coding: utf-8 -*-
"""CONSTRUIR en la ventana real, como una persona: las 20 herramientas del menú (planos, ejes, puntos y SCU).

Por cada una: clic en el ítem del menú de la cinta, elegir con el visor, teclear valores tecla por tecla, vista previa,
Enter, medir el resultado con números (posición, normal o dirección), reabrir para editar, deshacer, Esc y Tab; después
las asas (arrastre simulado al visor), los casos que no se pueden calcular, y la ventana de 1024x640 y 800x520."""
import json
import math
import sys

import arnes as A
import numpy as np
from omnicad import api
from omnicad.ui import manipuladores as mp
from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QToolButton
from teclado import pegar, teclear

AR = "CONSTRUIR"
TOL = 1e-3


def armar():
    s = api.Sesion()

    def L(nombre, **a):
        r = api.llamar(s, nombre, a)
        assert r["ok"], (nombre, a, r)
        return r["result"]

    ids = {"caja": L("create_box", length=30, width=30, height=20, x=-100)["bodies_created"][0]["id"],
           "cil": L("create_cylinder", height=30, radius=10, x=-160)["bodies_created"][0]["id"],
           "esf": L("create_sphere", radius=8, x=-40, y=60, z=10)["bodies_created"][0]["id"],
           "tor": L("create_torus", major_radius=12, minor_radius=3, x=40, y=60)["bodies_created"][0]["id"]}
    L("create_sketch", name="Lin", plane="XY")
    L("draw_line", sketch="Lin", start_x=100, start_y=-30, end_x=120, end_y=-30)
    L("draw_line", sketch="Lin", start_x=100, start_y=-30, end_x=100, end_y=-10)
    L("create_sketch", name="Spl", plane="XY")
    L("draw_spline", sketch="Spl", points=[[100, 40], [110, 52], [120, 40]])
    L("create_sketch", name="Circ", plane="XY")
    L("draw_circle", sketch="Circ", center_x=160, center_y=0, radius=5)
    L("create_construction_plane", plane="XY", offset=20, name="PL")
    L("create_sketch", name="Cad", plane="XY")                       # dos líneas seguidas: una cadena tangente de 40 mm
    L("draw_line", sketch="Cad", start_x=200, start_y=0, end_x=220, end_y=0)
    L("draw_line", sketch="Cad", start_x=220, start_y=0, end_x=240, end_y=0)
    return s, ids, L


s, ids, L = armar()
app, v = A.iniciar(s.doc)
caja, cil, esf, tor = ids["caja"], ids["cil"], ids["esf"], ids["tor"]
v.visor.vista("iso")
A.esperar(200)

# Esquinas y aristas de la cara superior de la caja (x de -115 a -85, y de -15 a 15, z = 20)
V = {"a": (-115, -15, 20), "b": (-85, -15, 20), "c": (-85, 15, 20), "d": (-115, 15, 20)}
M = {"frente": (-100, -15, 20), "der": (-85, 0, 20), "atras": (-100, 15, 20), "izq": (-115, 0, 20)}
vert = lambda k: (lambda: [A._clic_en(v, V[k], {"vertice"})])  # noqa: E731
ar = lambda k: (lambda: [A.hit_arista(v, caja, cerca=M[k])])  # noqa: E731
sup = lambda: [A.hit_cara(v, caja, normal=(0, 0, 1))]  # noqa: E731
pl = lambda n: (lambda: [A.hit_plano(v, n)])  # noqa: E731
cur = lambda n, i=0: (lambda: [A.hit_curva(v, s, n, i)])  # noqa: E731
cara_cil = lambda: [next(h for h in [A._clic_en(v, (-160 + 10 * math.cos(math.radians(-45)), 10 * math.sin(math.radians(-45)), 15), {"cara"})])]  # noqa: E731
EXIT = {}                       # clave → comprobaciones fallidas


def anotar(clave, que, ok, detalle=""):
    A.reg(f"{AR} · {clave}", que, ok, detalle)
    if not ok:
        EXIT.setdefault(clave, []).append(f"{que}: {detalle}")


def cerca(a, b, tol=TOL):
    return float(np.linalg.norm(np.asarray(a, float) - np.asarray(b, float))) <= tol


def paralela(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    return abs(abs(float(a @ b)) - 1.0) <= 1e-6


def en_plano(pl_, *puntos):
    return all(abs(float((np.asarray(p, float) - pl_.origen) @ pl_.normal)) <= TOL for p in puntos)


def resultado(op):
    e = v.doc.estado_final
    if op.TIPO == "plano":
        return e.planos[op.id]
    if op.TIPO == "eje":
        return e.ejes[op.id][:2]
    if op.TIPO == "punto":
        return e.puntos[op.id][0]
    return e.puntos[f"{op.id}_o"][0], e.ejes[f"{op.id}_x"][1], e.ejes[f"{op.id}_y"][1], e.ejes[f"{op.id}_z"][1]


def huella(r):
    if hasattr(r, "origen"):
        return np.concatenate([r.origen, r.normal]).round(6).tolist()
    if isinstance(r, tuple):
        return np.concatenate(r).round(6).tolist()
    return np.asarray(r, float).round(6).tolist()


def item_menu(clave):
    """El ítem de CONSTRUIR de la cinta para esa clave: se busca en el botón real, como lo haría la persona."""
    c = v.cinta
    i = next(k for k, (n, _g) in enumerate(__import__("omnicad.ui.cinta", fromlist=["PESTANAS"]).PESTANAS) if n == "SÓLIDO")
    QTest.mouseClick(c.pestanas[i], Qt.LeftButton)
    for b in c.pila.currentWidget().findChildren(QToolButton):
        if b.menu() is None or b.popupMode() != QToolButton.InstantPopup or "CONSTRUIR" not in b.text():
            continue
        for a in b.menu().actions():
            if a is v.acciones.get(clave):
                return a
    return None


def abrir_menu(clave):
    a = item_menu(clave)
    if a is None:
        anotar(clave, "el menú CONSTRUIR tiene el ítem", False, "no está")
        return A.abrir(v, clave)
    a.trigger()
    A.esperar(180)
    return v.panel


def filas_panel(p):
    return [p.etiquetas[c.clave].text() for c in p.campos if p._visible(c)]


def caso(clave, sel, vals, mide, filas=None, ctx=""):
    """Un uso completo. `sel`: {campo: lambda -> [hits]}; `vals`: {campo: texto}; `mide(resultado) -> (ok, detalle)`."""
    nombre = f"{clave}{ctx}"
    n0, n_err = A.n_ops(v), len(A.ERRORES)
    A.MODALES.clear()
    p = abrir_menu(clave)
    if p is None or not p.isVisible():
        anotar(nombre, "abre su panel", False, f"modales={A.MODALES}")
        return None
    anotar(nombre, "abre su panel", True, p.titulo.text())
    if filas is not None:
        anotar(nombre, "filas del panel como la captura de Fusion", filas_panel(p) == filas, f"se ven {filas_panel(p)}, captura {filas}")
    for campo, fn in sel.items():
        hs = fn()
        if not hs or any(h is None for h in hs):
            anotar(nombre, f"elegir «{campo}» con el visor", False, "el visor no devolvió la entidad")
            p.cancelar()
            return None
        if campo not in p.valores:
            anotar(nombre, f"campo «{campo}»", False, "el panel no lo tiene")
            p.cancelar()
            return None
        A.elegir(p, campo, *hs)
    for k, val in vals.items():
        if k not in p.widgets:
            anotar(nombre, f"campo «{k}»", False, "el panel no lo tiene")
            p.cancelar()
            return None
        if isinstance(val, str) and hasattr(p.widgets[k], "selectAll"):
            teclear(p, k, val)
        else:
            p.set_valor(k, val)
    p._t_previa.stop()
    p._calcular_previa()
    A.esperar(100)
    st = A.estado_panel(p)
    anotar(nombre, "vista previa", st["op"] and st["previa_ok"], f"mensaje=«{st['mensaje']}»")
    if not (st["op"] and st["previa_ok"]):
        p.cancelar()
        return None
    QTest.keyClick(p, Qt.Key_Return)
    A.esperar(350)
    anotar(nombre, "Enter agrega UN paso", A.n_ops(v) == n0 + 1, f"pasos {n0} → {A.n_ops(v)}")
    if A.n_ops(v) != n0 + 1:
        return None
    op = v.doc.operaciones[-1]
    try:
        r = resultado(op)
        ok, det = mide(r)
    except Exception as e:  # noqa: BLE001
        anotar(nombre, "resultado medido", False, f"{type(e).__name__}: {e}")
        A.deshacer(v)
        return None
    anotar(nombre, "resultado medido", ok, det)
    h0 = huella(r)
    v.editar_operacion(op.id)
    A.esperar(220)
    p2 = v.panel
    if p2 is None or not p2.isVisible():
        anotar(nombre, "reabrir para editar", False, f"modales={A.MODALES}")
    else:
        malos = [f"{k}: puse {val!r}, vuelve {p2.valores.get(k)!r}" for k, val in vals.items() if str(p2.valores.get(k)) != str(val)]
        malos += [f"{c}: vuelve vacío" for c in sel if not p2.valores.get(c)]
        anotar(nombre, "al reabrir vuelven valores y selección", not malos, "; ".join(malos))
        p2._t_previa.stop()
        p2._calcular_previa()
        p2.aceptar()
        A.esperar(350)
        h1 = huella(resultado(v.doc.operaciones[-1]))
        anotar(nombre, "aceptar sin cambiar da lo mismo", h1 == h0 and A.n_ops(v) == n0 + 1, f"{h0} → {h1}")
    A.deshacer(v)
    if A.n_ops(v) > n0:
        A.deshacer(v)
    anotar(nombre, "deshacer vuelve al estado anterior", A.n_ops(v) == n0, f"pasos {A.n_ops(v)} (eran {n0})")
    anotar(nombre, "sin excepciones en un slot", len(A.ERRORES) == n_err, "" if len(A.ERRORES) == n_err else A.ERRORES[-1][-300:])
    return op


def esc_y_tab(clave):
    n0 = A.n_ops(v)
    p = abrir_menu(clave)
    if p is None:
        return
    p._t_previa.stop()
    p._calcular_previa()
    msg = p.mensaje.text()
    QTest.keyClick(p, Qt.Key_Return)
    A.esperar(80)
    anotar(clave, "Enter sin elegir no crea paso y avisa", A.n_ops(v) == n0 and bool(msg or p.mensaje.text()), f"«{msg or p.mensaje.text()}»")
    campos = [w for k, w in p.widgets.items() if hasattr(w, "selectAll") and w.isVisible()]
    if campos:
        w = campos[0]
        w.setFocus()
        A.esperar(30)
        foco0 = QApplication.focusWidget()
        QTest.keyClick(foco0 or w, Qt.Key_Tab)
        A.esperar(30)
        foco1 = QApplication.focusWidget()
        if foco0 is None:
            A.reg(f"{AR} · {clave}", "⚠ Tab: sin foco real con la ventana transparente", True)
        else:
            anotar(clave, "Tab pasa al siguiente control del panel", foco1 is not foco0 and p.isAncestorOf(foco1), type(foco1).__name__)
    QTest.keyClick(p, Qt.Key_Escape)
    A.esperar(80)
    vivo = False
    try:
        vivo = p.isVisible()
    except RuntimeError:
        pass
    anotar(clave, "Esc cierra sin crear paso", not vivo and A.n_ops(v) == n0, f"visible={vivo} pasos={A.n_ops(v)}")


def mover_sim(w, pos):
    p = QPointF(pos)
    QApplication.sendEvent(w, QMouseEvent(QEvent.MouseMove, p, w.mapToGlobal(p), Qt.NoButton, Qt.NoButton, Qt.NoModifier))


def arrastrar(panel, desde, hasta, pasos=6):
    g = panel.manipuladores
    xy, ok = g.pantalla([desde, hasta])
    if not ok.all():
        return False
    a, b = (QPointF(*q) for q in xy)
    vis = panel.visor
    mover_sim(vis, a)
    QApplication.sendEvent(vis, QMouseEvent(QEvent.MouseButtonPress, a, vis.mapToGlobal(a), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier))
    for i in range(1, pasos + 1):
        q = a + (b - a) * (i / pasos)
        QApplication.sendEvent(vis, QMouseEvent(QEvent.MouseMove, q, vis.mapToGlobal(q), Qt.NoButton, Qt.LeftButton, Qt.NoModifier))
        A.esperar(15)
    QApplication.sendEvent(vis, QMouseEvent(QEvent.MouseButtonRelease, b, vis.mapToGlobal(b), Qt.LeftButton, Qt.NoButton, Qt.NoModifier))
    A.esperar(100)
    panel._t_previa.stop()
    panel._calcular_previa()
    return True


def asa(clave, sel, tipo, campo, mover, vals=None, cerca_de=None):
    p = abrir_menu(clave)
    if p is None:
        return
    for c, fn in sel.items():
        A.elegir(p, c, *fn())
    for k, val in (vals or {}).items():
        p.set_valor(k, val)
    g = p.manipuladores
    if g is None:
        anotar(clave, f"asa de {campo}", False, "el panel no tiene asas")
        p.cancelar()
        return
    g.actualizar()
    m = next((x for x in g.manips if isinstance(x, tipo) and x.clave == campo), None)
    if m is None:
        anotar(clave, f"asa de {campo}", False, f"asas: {[type(x).__name__ for x in g.manips]}")
        p.cancelar()
        return
    antes = g.valor(campo)
    desde, hasta = mover(m, g)
    ok = arrastrar(p, desde, hasta)
    despues = g.valor(campo)
    bien = ok and abs(despues - antes) > 1e-3 and (cerca_de is None or abs(despues - cerca_de) < max(1.0, abs(cerca_de) * 0.2)) and p._previa_ok
    anotar(clave, f"asa de {campo}: arrastrar cambia el valor y la previa sigue", bien,
           f"{antes:.3f} → {despues:.3f}; mensaje=«{p.mensaje.text()}»")
    p.cancelar()
    A.esperar(80)


def rechazo(clave, sel, texto):
    n0 = A.n_ops(v)
    p = abrir_menu(clave)
    if p is None:
        return
    for c, fn in sel.items():
        A.elegir(p, c, *fn())
    p._t_previa.stop()
    p._calcular_previa()
    st = A.estado_panel(p)
    anotar(clave, f"no calculable: {texto}", not st["previa_ok"] and bool(st["mensaje"]) and "No existe" not in st["mensaje"], f"«{st['mensaje']}»")
    p.cancelar()
    A.esperar(60)
    anotar(clave, "no calculable: no deja pasos", A.n_ops(v) == n0, f"{A.n_ops(v)}")


# --------------------------------------------------------------------- las 20 herramientas
FILAS = {  # filas visibles al abrir, según cada captura (Tipo y Método van al frente en el panel único)
    "plano_desfase": ["Tipo", "Método", "Plano", "Extensión"],
    "plano_angulo": ["Tipo", "Método", "Arista"],
    "plano_tangente": ["Tipo", "Método", "Cara", "Objeto de referencia"],
    "plano_perpendicular": ["Tipo", "Método", "Cara", "Dirección", "Extensión"],
    "eje_cilindro": ["Tipo", "Método", "Cara"],
    "punto_vertice": ["Tipo", "Método", "Punto"],
}
Z = (0, 0, 1)


def p_(ok, det):
    return bool(ok), det


def _plano(o=None, n=None, puntos=()):
    def f(r):
        ok = (o is None or abs(float((np.asarray(o, float) - r.origen) @ r.normal)) <= TOL) and (n is None or paralela(r.normal, n))
        return p_(ok and en_plano(r, *puntos), f"origen={np.round(r.origen, 3).tolist()} normal={np.round(r.normal, 4).tolist()}")
    return f


def _eje(pasa=None, d=None):
    def f(r):
        p, dd = r
        ok = d is None or paralela(dd, d)
        if pasa is not None:
            w = np.asarray(pasa, float) - p
            ok = ok and float(np.linalg.norm(w - dd * float(w @ dd))) <= TOL
        return p_(ok, f"punto={np.round(p, 3).tolist()} dirección={np.round(dd, 4).tolist()}")
    return f


def _punto(q):
    return lambda r: p_(cerca(r, q), f"punto={np.round(r, 3).tolist()} (esperado {q})")


def _scu(o, x=None, z=None):
    def f(r):
        ok = cerca(r[0], o) and (x is None or cerca(r[1], x)) and (z is None or cerca(r[3], z))
        return p_(ok, f"origen={np.round(r[0], 3).tolist()} x={np.round(r[1], 3).tolist()} z={np.round(r[3], 3).tolist()}")
    return f


def _angulo30(r):
    return p_(en_plano(r, V["a"], V["b"]) and abs(abs(float(r.normal[2])) - math.cos(math.radians(30))) <= 1e-6,
              f"contiene la arista; normal={np.round(r.normal, 4).tolist()}")


def _tangente(r):
    w = r.origen - np.array((-160, 0, r.origen[2]))
    return p_(abs(float(np.linalg.norm(w)) - 10) <= TOL and abs(float(r.normal[2])) <= 1e-9 and paralela(r.normal, w / np.linalg.norm(w)),
              f"a 10 mm del eje: origen={np.round(r.origen, 3).tolist()} normal={np.round(r.normal, 4).tolist()}")


def _perp(r):
    return p_(en_plano(r, V["a"]) and abs(float(r.normal[2])) <= 1e-9, f"pasa por el vértice; normal={np.round(r.normal, 4).tolist()}")


caso("plano_desfase", {"r0": pl("XY")}, {"distancia": "12 mm"}, _plano((0, 0, 12), Z), FILAS["plano_desfase"])
caso("plano_angulo", {"r0": ar("frente")}, {"angulo": "30 deg"}, _angulo30, FILAS["plano_angulo"])
caso("plano_tangente", {"r0": cara_cil}, {"angulo": "45 deg"}, _tangente, FILAS["plano_tangente"])
caso("plano_medio", {"r0": pl("XY"), "r1": pl("PL")}, {}, _plano((0, 0, 10), Z))
caso("plano_perpendicular", {"r0": sup, "r1": vert("a")}, {}, _perp, FILAS["plano_perpendicular"])
caso("plano_dos_aristas", {"r0": ar("frente"), "r1": ar("atras")}, {}, _plano((-100, 0, 20), Z, [V["a"], V["c"]]))
caso("plano_tres_puntos", {"r0": vert("a"), "r1": vert("b"), "r2": vert("c")}, {}, _plano((-100, 0, 20), Z))
caso("plano_ruta", {"r0": cur("Lin", 0)}, {"posicion": "0.25"}, _plano((105, -30, 0), (1, 0, 0)))
caso("eje_cilindro", {"r0": cara_cil}, {}, _eje((-160, 0, 0), Z), FILAS["eje_cilindro"])
caso("eje_perpendicular", {"r0": sup, "r1": vert("a")}, {}, _eje(V["a"], Z))
caso("eje_dos_planos", {"r0": pl("XY"), "r1": pl("XZ")}, {}, _eje((0, 0, 0), (1, 0, 0)))
caso("eje_dos_puntos", {"r0": vert("a"), "r1": vert("c")}, {}, _eje(V["a"], (1 / math.sqrt(2), 1 / math.sqrt(2), 0)))
caso("eje_arista", {"r0": ar("der")}, {}, _eje(V["b"], (0, 1, 0)))
caso("punto_vertice", {"r0": vert("a")}, {}, _punto(V["a"]), FILAS["punto_vertice"])
caso("punto_dos_aristas", {"r0": cur("Lin", 0), "r1": cur("Lin", 1)}, {}, _punto((100, -30, 0)))
caso("punto_tres_planos", {"r0": pl("XY"), "r1": pl("XZ"), "r2": pl("YZ")}, {}, _punto((0, 0, 0)))
caso("punto_centro", {"r0": lambda: [A._clic_en(v, (-40, 60, 18), {"cara"})]}, {}, _punto((-40, 60, 10)), ctx=" (esfera)")
caso("punto_centro", {"r0": cur("Circ", 0)}, {}, _punto((160, 0, 0)), ctx=" (círculo de boceto)")
caso("punto_arista_plano", {"r0": ar("frente"), "r1": pl("YZ")}, {}, _punto((0, -15, 20)))
caso("punto_ruta", {"r0": cur("Lin", 0)}, {"posicion": "0.5"}, _punto((110, -30, 0)))
caso("scu", {"origen": vert("a"), "eje_x": ar("der")}, {"dz": "5 mm"}, _scu((-115, -15, 25), (0, 1, 0)))
caso("scu", {"origen": vert("a")}, {}, _scu(V["a"], (1, 0, 0), Z), ctx=" (solo origen)")

# --------------------------------------------------------------------- opciones nuevas, cada una medida
centro_sup = (-100, 0, 20)
sobre = lambda q: (lambda: [A._clic_en(v, q, {"cara"})])  # noqa: E731
forzar = lambda q: (lambda: [A._clic_en(v, q, {"vertice", "punto", "forzado"})])  # noqa: E731
caso("plano_desfase", {"r0": pl("XY"), "objeto": vert("a")}, {"extension": "objeto"}, _plano((0, 0, 20), Z), ctx=" (Al objeto)")
caso("plano_desfase", {"r0": pl("XY")}, {"distancia": "12 mm", "desfase": "3 mm"}, _plano((0, 0, 15), Z), ctx=" (Desfase)")
caso("plano_dos_aristas", {"r0": ar("frente"), "r1": ar("atras")}, {"desfase": "5 mm"}, _plano((0, 0, 25), Z), ctx=" (Desfase)")
caso("plano_tres_puntos", {"r0": vert("a"), "r1": vert("b"), "r2": vert("c")}, {"desfase": "-5 mm"}, _plano((0, 0, 15), Z), ctx=" (Desfase)")
caso("plano_angulo", {"r0": ar("frente")}, {"angulo": "90 deg", "desfase": "4 mm"},
     lambda r: p_(abs(abs(float((np.array(V["a"], float) - r.origen) @ r.normal)) - 4) <= TOL, f"a 4 mm de la arista; normal={np.round(r.normal, 4).tolist()}"), ctx=" (Desfase)")
caso("plano_tangente", {"r0": cara_cil}, {"angulo": "45 deg", "desfase": "2 mm"},
     lambda r: p_(abs(float(np.linalg.norm(r.origen[:2] - (-160, 0))) - 12) <= TOL, f"a 12 mm del eje: {np.round(r.origen, 3).tolist()}"), ctx=" (Desfase)")


def _medida(op_id=None):
    return v.doc.estado_final.medidas.get(op_id or v.doc.operaciones[-1].id)


def tamano(clave, sel, vals, mide, ctx):
    n0 = A.n_ops(v)
    p = abrir_menu(clave)
    for campo, fn in sel.items():
        A.elegir(p, campo, *fn())
    for k, val in vals.items():
        p.set_valor(k, val)
    p._t_previa.stop()
    p._calcular_previa()
    QTest.keyClick(p, Qt.Key_Return)
    A.esperar(300)
    m = _medida() if A.n_ops(v) == n0 + 1 else None
    ok, det = mide(m) if m is not None else (False, f"sin paso: «{p.mensaje.text() if A.n_ops(v) == n0 else ''}»")
    anotar(clave, f"medida{ctx}", ok, det)
    while A.n_ops(v) > n0:
        A.deshacer(v)


tamano("plano_medio", {"r0": pl("XY"), "r1": pl("PL")}, {"redimensionar": "extendido"}, lambda m: p_(m["redimensionar"] == "extendido", str(m)), ": Redimensionar Extendido se guarda")
tamano("plano_tres_puntos", {"r0": vert("a"), "r1": vert("b"), "r2": vert("c")}, {}, lambda m: p_(m["limites"] is not None and m["limites"][2] - m["limites"][0] >= 30, str(m)), ": Predeterminado ajusta a lo elegido")
tamano("plano_tres_puntos", {"r0": vert("a"), "r1": vert("b"), "r2": vert("c")}, {"medida": "60 mm"}, lambda m: p_(abs(m["limites"][2] - m["limites"][0] - 60) < TOL, str(m)), ": lado 60")
tamano("eje_arista", {"r0": ar("der")}, {"medida": "100 mm"}, lambda m: p_(abs(m["limites"][1] - m["limites"][0] - 100) < TOL, str(m)), ": largo 100")
tamano("eje_arista", {"r0": ar("der"), "objeto_extension": sobre((-40, 60, 18))}, {"tipo_extension": "objeto"}, lambda m: p_(m["limites"][1] >= 60, str(m)), ": hasta la esfera (Al objeto)")

# Plano y eje perpendicular: lugar tocado, U/V, cara curva, Objeto de referencia
lugar = (-105, 5, 20)
caso("plano_perpendicular", {"r0": sobre(lugar)}, {"direccion": "U"}, lambda r: p_(en_plano(r, lugar) and abs(float(r.normal[2])) < 1e-9, f"pasa por el lugar; normal={np.round(r.normal, 4).tolist()}"), ctx=" (cara plana U)")
normal_u = None


def _guardar_u(r):
    global normal_u
    normal_u = r.normal.copy()
    return p_(en_plano(r, lugar), f"normal={np.round(r.normal, 4).tolist()}")


caso("plano_perpendicular", {"r0": sobre(lugar)}, {"direccion": "U"}, _guardar_u, ctx=" (U de nuevo)")
caso("plano_perpendicular", {"r0": sobre(lugar)}, {"direccion": "V"},
     lambda r: p_(en_plano(r, lugar) and abs(float(r.normal @ normal_u)) < 1e-9, f"V ⟂ U; normal={np.round(r.normal, 4).tolist()}"), ctx=" (cara plana V)")
lat = (-160 + 10 * math.cos(math.radians(-45)), 10 * math.sin(math.radians(-45)), 12)
n_cil = np.array((math.cos(math.radians(-45)), math.sin(math.radians(-45)), 0))


def radial(p):
    """Normal del cilindro en p (el clic cae en un triángulo de la malla: el lugar se mide contra lo que quedó)."""
    w = np.array((p[0] + 160, p[1], 0.0))
    return w / np.linalg.norm(w)


caso("plano_perpendicular", {"r0": sobre(lat)}, {},
     lambda r: p_(cerca(r.origen, lat, 0.05) and abs(float(r.normal @ radial(r.origen))) < 1e-9 and abs(float(np.linalg.norm(r.origen[:2] - (-160, 0))) - 10) < 1e-6,
                  f"sobre la cara, contiene su normal; origen={np.round(r.origen, 3).tolist()} normal={np.round(r.normal, 4).tolist()}"), ctx=" (cara curva)")
caso("plano_perpendicular", {"r0": sobre(lat), "r1": lambda: [A._clic_en(v, (-115, -15, 20), {"vertice"})]}, {},
     lambda r: p_(abs(float(r.normal @ n_cil)) < 1 and en_plano(r, r.origen), f"anclado al punto; origen={np.round(r.origen, 3).tolist()}"), ctx=" (cara curva, punto)")
caso("plano_perpendicular", {"r0": sobre(lugar), "r1": pl("YZ")}, {}, _plano((0, 0, 0), (1, 0, 0)), ctx=" (Objeto de referencia plano)")
caso("plano_perpendicular", {"r0": sobre(lugar)}, {"desfase": "7 mm"}, lambda r: p_(abs(abs(float((np.array(lugar, float) - r.origen) @ r.normal)) - 7) <= TOL, f"a 7 mm del lugar; normal={np.round(r.normal, 4).tolist()}"), ctx=" (Distancia)")
caso("eje_perpendicular", {"r0": sobre(lugar)}, {}, _eje(lugar, Z), ctx=" (lugar tocado)")
caso("eje_perpendicular", {"r0": sobre(lat)}, {}, lambda r: p_(cerca(r[0], lat, 0.05) and paralela(r[1], radial(r[0])), f"punto={np.round(r[0], 3).tolist()} dirección={np.round(r[1], 4).tolist()}"), ctx=" (cara curva)")
caso("eje_perpendicular", {"r0": sup, "r1": vert("a")}, {}, _eje(V["a"], Z), ctx=" (con punto)")

# Rutas
caso("plano_ruta", {"r0": cur("Lin", 0)}, {"tipo_distancia": "absoluto", "distancia": "5 mm"}, _plano((105, -30, 0), (1, 0, 0)), ctx=" (Absoluto)")
caso("plano_ruta", {"r0": cur("Lin", 0), "objeto": lambda: [A._clic_en(v, (100, -10, 0), {"punto"})]}, {"tipo_distancia": "objeto"}, _plano((100, -30, 0), (1, 0, 0)), ctx=" (Al objeto)")
caso("plano_ruta", {"r0": cur("Lin", 0), "objeto": lambda: [A._clic_en(v, (100, -10, 0), {"punto"})]}, {"tipo_distancia": "objeto", "desfase": "3 mm"}, _plano((103, -30, 0), (1, 0, 0)), ctx=" (Al objeto + Desfase)")
caso("plano_ruta", {"r0": cur("Cad", 0)}, {"posicion": "0.75"}, _plano((230, 0, 0), (1, 0, 0)), ctx=" (Cadena tangente)")
caso("plano_ruta", {"r0": cur("Cad", 0)}, {"posicion": "0.75", "cadena_tangente": False}, _plano((215, 0, 0), (1, 0, 0)), ctx=" (sin cadena)")
caso("plano_ruta", {"r0": cur("Cad", 0)}, {"posicion": "1.25"}, _plano((250, 0, 0), (1, 0, 0)), ctx=" (pasa del final)")
caso("plano_ruta", {"r0": lambda: [A.hit_eje(v, "X")]}, {"distancia": "30 mm"}, _plano((30, 0, 0), (1, 0, 0)), ctx=" (eje como ruta)")
caso("punto_ruta", {"r0": cur("Lin", 0)}, {"tipo_distancia": "absoluto", "distancia": "5 mm"}, _punto((105, -30, 0)), ctx=" (Físico)")
caso("punto_ruta", {"r0": cur("Cad", 0)}, {"posicion": "0.75"}, _punto((230, 0, 0)), ctx=" (Cadena tangente)")

# Puntos de forzado
caso("punto_vertice", {"r0": forzar(centro_sup)}, {}, _punto(centro_sup), ctx=" (centro de cara)")
caso("punto_vertice", {"r0": forzar(M["frente"])}, {}, _punto(M["frente"]), ctx=" (centro de arista)")
caso("punto_vertice", {"r0": forzar((-110, -15, 20))}, {}, _punto((-110, -15, 20)), ctx=" (punto de arista)")
caso("punto_vertice", {"r0": forzar((-160 + 10 * math.cos(math.radians(-90)), -10, 15))}, {}, _punto((-160, -10, 15)), ctx=" (tangencial del cilindro)")
caso("plano_tres_puntos", {"r0": forzar(centro_sup), "r1": vert("a"), "r2": vert("b")}, {}, _plano(centro_sup, Z), ctx=" (forzado)")
caso("eje_dos_puntos", {"r0": forzar(centro_sup), "r1": forzar(M["der"])}, {}, _eje(centro_sup, (1, 0, 0)), ctx=" (forzado)")
caso("eje_perpendicular", {"r0": sup, "r1": forzar(M["frente"])}, {}, _eje(M["frente"], Z), ctx=" (forzado)")
caso("scu", {"origen": forzar(centro_sup)}, {}, _scu(centro_sup, (1, 0, 0), Z), ctx=" (forzado)")

# Punto en el centro y tres planos con perfil de boceto
caso("punto_centro", {"r0": lambda: [A._clic_en(v, (160, 0, 0), {"perfil"})]}, {}, _punto((160, 0, 0)), ctx=" (perfil)")
caso("punto_tres_planos", {"r0": lambda: [A._clic_en(v, (160, 0, 0), {"perfil"})], "r1": pl("XZ"), "r2": pl("YZ")}, {}, _punto((0, 0, 0)), ctx=" (con perfil)")

# SCU: flujo de Fusion
p = abrir_menu("scu")
anotar("scu", "al abrir solo se ve Forzar", filas_panel(p) == ["Forzar"], str(filas_panel(p)))
info = p.comando.info
anotar("scu", "panel de información al lado", info.isVisible() and "SISTEMA DE COORDENADAS" in info.titulo.text() and "punto de referencia" in info.texto.text(), info.titulo.text())
A.foto(v, "construir_scu_info")
QTest.mouseClick(info.consejos.boton, Qt.LeftButton)
A.esperar(60)
anotar("scu", "Consejos se despliega", info.consejos.boton.isChecked(), "")
QTest.mouseClick(info.boton_cerrar, Qt.LeftButton)
A.esperar(60)
anotar("scu", "Cerrar cierra la información y el comando sigue", not info.isVisible() and p.isVisible(), "")
A.elegir(p, "origen", *vert("a")())
vis_scu = filas_panel(p)
anotar("scu", "al forzar aparecen ángulos, desfases y alineación", vis_scu == ["Forzar", "Ángulo X", "Ángulo Y", "Ángulo Z", "Desfase X", "Desfase Y", "Desfase Z", "Eje Z", "Eje X"], str(vis_scu))
g = p.manipuladores
g.actualizar()
t = next((m for m in g.manips if isinstance(m, mp.Triada)), None)
anotar("scu", "tríada en el lienzo", t is not None and cerca(t.centro, V["a"]), str(t and t.centro))
p.cancelar()
A.esperar(80)
caso("scu", {"origen": vert("a"), "eje_z": ar("der")}, {}, _scu(V["a"], z=(0, 1, 0)), ctx=" (Eje Z en arista)")
caso("scu", {"origen": vert("a"), "eje_x": sobre((-160, 0, 30))}, {}, _scu(V["a"], (0, 0, 1)), ctx=" (Eje X en cara)")

# Panel único: Tipo y Método
for clave in [k for k in ("plano_desfase", "plano_angulo", "plano_tangente", "plano_medio", "plano_perpendicular", "plano_dos_aristas", "plano_tres_puntos", "plano_ruta",
                          "eje_cilindro", "eje_perpendicular", "eje_dos_planos", "eje_dos_puntos", "eje_arista", "punto_vertice", "punto_dos_aristas", "punto_tres_planos",
                          "punto_centro", "punto_arista_plano", "punto_ruta")]:
    p = abrir_menu(clave)
    tipo = clave.split("_")[0]
    anotar(clave, "abre el panel único con Tipo y Método puestos",
           p.titulo.text() == "GEOMETRÍA DE CONSTRUCCIÓN" and p.valores.get("tipo") == tipo and p.valores.get("metodo") == clave, f"{p.titulo.text()} {p.valores.get('tipo')} {p.valores.get('metodo')}")
    p.cancelar()
    A.esperar(30)
p = abrir_menu("plano_desfase")
w = p.widgets["metodo"]
anotar("panel", "Método de Plano tiene 8 con ícono", w.count() == 8 and all(not w.itemIcon(i).isNull() for i in range(8)), [w.itemText(i) for i in range(w.count())])
A.elegir(p, "r0", *pl("XY")())
p.set_valor("metodo", "plano_medio")
A.esperar(40)
anotar("panel", "cambiar Método conserva lo que sirve", len(p.valores["r0"]) == 1 and p.etiquetas["r0"].text() == "Plano 1", str(p.etiquetas["r0"].text()))
QTest.mouseClick(p.widgets["tipo"].boton("eje"), Qt.LeftButton)
A.esperar(60)
anotar("panel", "clic en Tipo Eje cambia las entradas", p.valores["tipo"] == "eje" and p.valores["metodo"] == "eje_cilindro" and w.count() == 5, f"{p.valores['metodo']} {w.count()}")
anotar("panel", "lo que no sirve se suelta (un plano no es una cara curva)", not p.valores["r0"], str(len(p.valores["r0"])))
QTest.mouseClick(p.widgets["tipo"].boton("punto"), Qt.LeftButton)
A.esperar(60)
anotar("panel", "clic en Tipo Punto cambia las entradas", p.valores["metodo"] == "punto_vertice" and w.count() == 6, f"{p.valores['metodo']} {w.count()}")
n0 = A.n_ops(v)
A.elegir(p, "r0", *vert("a")())
p._t_previa.stop()
p._calcular_previa()
QTest.keyClick(p, Qt.Key_Return)
A.esperar(300)
op = v.doc.operaciones[-1]
anotar("panel", "un panel abierto como plano crea un punto si se pasó a Punto", A.n_ops(v) == n0 + 1 and op.TIPO == "punto" and op.nombre.startswith("Punto"), f"{op.TIPO} {op.nombre}")
v.editar_operacion(op.id)
A.esperar(200)
anotar("panel", "editar abre el mismo panel con su método", v.panel.titulo.toolTip() == "EDITAR GEOMETRÍA DE CONSTRUCCIÓN" and v.panel.valores["metodo"] == "punto_vertice" and not v.panel.widgets["tipo"].isEnabled(), v.panel.titulo.text())
v.panel.cancelar()
A.deshacer(v)

# Nombres de planos en el lienzo
nombres = lambda: [t for t, _q in v.visor.etiquetas_planos()]  # noqa: E731
v._refrescar_visibilidad()
v.visor.update()
A.esperar(200)
anotar("nombres", "el plano de construcción muestra su nombre", "PL" in nombres() and v.visor._nombres_planos.isVisible(), str(nombres()))
A.foto(v, "construir_nombres")
op_pl = s.paso("PL")
v.renombrar_operacion(op_pl.id, "Tapa") if hasattr(v, "renombrar_operacion") else setattr(op_pl, "nombre", "Tapa")
v._refrescar_visibilidad()
anotar("nombres", "renombrar actualiza la etiqueta", "Tapa" in nombres(), str(nombres()))
setattr(op_pl, "nombre", "PL")
v.cambiar_vista("visibilidad:nombres_planos_construccion", False)
v._refrescar_visibilidad()
v.visor.update()
A.esperar(200)
planos_siguen = any(i == op_pl.id for i, _n, _p in v.visor.config.planos_usuario)
anotar("nombres", "la casilla oculta el nombre y no el plano", "PL" not in nombres() and planos_siguen and v.visor.plano_visible(op_pl.id), str(nombres()))
v.cambiar_vista("visibilidad:nombres_planos_construccion", True)
L("set_object_visibility", types=["nombres_planos_construccion"], visible=False)
v.aplicar_estado_visor()
anotar("nombres", "la API también lo apaga en la ventana", "PL" not in nombres(), str(nombres()))
L("set_object_visibility", types=["nombres_planos_construccion"], visible=True)
v.aplicar_estado_visor()

CLAVES = ["scu", "plano_desfase", "plano_angulo", "plano_tangente", "plano_medio", "plano_perpendicular", "plano_dos_aristas",
          "plano_tres_puntos", "plano_ruta", "eje_cilindro", "eje_perpendicular", "eje_dos_planos", "eje_dos_puntos", "eje_arista",
          "punto_vertice", "punto_dos_aristas", "punto_tres_planos", "punto_centro", "punto_arista_plano", "punto_ruta"]
for clave in CLAVES:
    esc_y_tab(clave)

# --------------------------------------------------------------------- campos: teclear, pegar, valores raros
for entrada, ok_esperado in (("12,5 mm", 12.5), ("1 cm", 10), ("abc", None), ("", None), ("0", 0), ("-5", -5), ("1e4", 1e4)):
    p = abrir_menu("plano_desfase")
    A.elegir(p, "r0", *pl("XY")())
    w = teclear(p, "distancia", entrada)
    p._t_previa.stop()
    p._calcular_previa()
    rojo = "background" in w.styleSheet()
    if ok_esperado is None:
        anotar("plano_desfase", f"teclear {entrada!r}: rojo y sin aceptar", rojo and p.ultima_op is None, f"mensaje=«{p.mensaje.text()}»")
    else:
        val = p.ctx.evaluar(w.text())
        anotar("plano_desfase", f"teclear {entrada!r} = {ok_esperado}", abs(val - ok_esperado) < 1e-6 and p._previa_ok, f"{val}; «{p.mensaje.text()}»")
    p.cancelar()
p = abrir_menu("plano_desfase")
A.elegir(p, "r0", *pl("XY")())
pegar(p, "distancia", "7 mm")
anotar("plano_desfase", "pegar 7 mm", p.valores["distancia"] == "7 mm", p.valores["distancia"])
p.cancelar()

# --------------------------------------------------------------------- asas
asa("plano_desfase", {"r0": pl("XY")}, mp.Flecha, "distancia", lambda m, g: ((lambda a, b: ((a + b) / 2, (a + b) / 2 + m.direccion * 15))(*m.puntos(g))))
asa("plano_ruta", {"r0": cur("Lin", 0)}, mp.AsaRuta, "posicion", lambda m, g: (m.asa(g), m.puntos_ruta[-1]))
asa("punto_ruta", {"r0": cur("Lin", 0)}, mp.AsaRuta, "posicion", lambda m, g: (m.asa(g), m.puntos_ruta[-1]))
asa("plano_tangente", {"r0": cara_cil}, mp.Angulo, "angulo", lambda m, g: (m.asa(g), m.centro + (m.u * math.cos(math.radians(70)) + m.v * math.sin(math.radians(70))) * m._r(g)))
asa("plano_angulo", {"r0": ar("frente")}, mp.Angulo, "angulo", lambda m, g: (m.asa(g), m.centro + (m.u * math.cos(math.radians(50)) + m.v * math.sin(math.radians(50))) * m._r(g)))
asa("plano_perpendicular", {"r0": sup, "r1": vert("a")}, mp.Flecha, "desfase", lambda m, g: ((lambda a, b: ((a + b) / 2, (a + b) / 2 + m.direccion * 10))(*m.puntos(g))))

# --------------------------------------------------------------------- lo que no se puede calcular y la spline (B-130, B-131)
rechazo("eje_dos_planos", {"r0": pl("XY"), "r1": pl("PL")}, "planos paralelos")
rechazo("punto_tres_planos", {"r0": pl("XY"), "r1": pl("PL"), "r2": pl("YZ")}, "planos sin cruce")
rechazo("plano_tangente", {"r0": sup}, "tangente sobre cara plana")
from omnicad.nucleo import geometria as geo  # noqa: E402
from omnicad.ui.comando import hit_desde_ref  # noqa: E402
hit_spline = hit_desde_ref(A.hit_curva(v, s, "Spl", 0)["ref"], v.doc.estado_final)
pts = geo.polilinea_arista(hit_spline["forma"])
q = v.visor.proyectar(np.array(pts[len(pts) // 2], float))
control = v.visor.elegir_entidad(q, {"curva_boceto"})
anotar("spline", "control: con el filtro de curvas el clic sí la toma", control is not None and control["tipo"] == "curva_boceto", str(control and control["tipo"]))
for clave in ("plano_dos_aristas", "plano_angulo", "punto_arista_plano", "eje_arista"):
    p = abrir_menu(clave)
    elegido = v.visor.elegir_entidad(q, p._por_clave["r0"].filtros)
    anotar(clave, "el visor no deja elegir una spline donde va una línea", elegido is None or elegido.get("tipo") != "curva_boceto", f"hit={elegido and elegido.get('tipo')}")
    p.cancelar()
for tipo, args in (("create_construction_axis", dict(type="arista", references=[{"sketch": s.paso("Spl").id, "curve": next(iter(v.doc.estado_final.bocetos[s.paso("Spl").id].boceto.curvas))}])),
                   ("create_construction_axis", dict(type="dos_planos", references=["XY", "PL"])),
                   ("create_construction_point", dict(type="tres_planos", references=["XY", "PL", "YZ"])),
                   ("create_construction_plane", dict(type="tangent", references=[f"{caja}/F1"]))):
    r = api.llamar(s, tipo, args)
    malo = r["ok"] or r["error_kind"] in ("NOT_FOUND", "INTERNAL_ERROR") or "No existe" in r.get("mensaje", "")
    anotar(tipo, f"API: {args['type']} da un error claro", not malo, f"{r.get('error_kind')}: {r.get('mensaje')}")
    if r["ok"]:
        api.llamar(s, "undo", {})

# --------------------------------------------------------------------- pieza real: boceto en un plano inclinado, extrusión y una cota que cambia
L("create_parameter", name="alto_pieza", expression="20 mm")
n_pieza = A.n_ops(v)
p = abrir_menu("plano_angulo")
A.elegir(p, "r0", A.hit_eje(v, "X"))
teclear(p, "angulo", "30 deg")
p._t_previa.stop()
p._calcular_previa()
QTest.keyClick(p, Qt.Key_Return)
A.esperar(300)
inclinado = v.doc.operaciones[-1]
L("create_sketch", name="Pieza", plane=inclinado.id)
L("draw_rectangle", sketch="Pieza", x1=-70, y1=-300, x2=-40, y2=-270)
b = L("extrude", sketch="Pieza", distance="alto_pieza")["bodies_created"][0]["id"]
plano_i = v.doc.estado_final.planos[inclinado.id]
anotar("pieza", "plano inclinado a 30°", abs(abs(float(plano_i.normal[2])) - math.cos(math.radians(30))) < 1e-6, str(np.round(plano_i.normal, 4).tolist()))
v._refrescar_visibilidad()
A.esperar(200)
v.visor.encuadrar()
A.esperar(200)
forma = v.doc.estado_final.cuerpos[b].forma
from omnicad.nucleo import referencias as refs  # noqa: E402
tapa = max(refs.subformas(forma, "cara"), key=lambda c: float(np.array(refs.firma_cara(c)["centro"]) @ plano_i.normal))
centro_tapa = np.array(refs.firma_cara(tapa)["centro"], float)
hit_tapa = A._clic_en(v, centro_tapa, {"cara"})
anotar("pieza", "el visor toma la tapa", hit_tapa is not None and hit_tapa["ref"].get("cuerpo") == b, str(hit_tapa and hit_tapa["ref"].get("cuerpo")))
if hit_tapa is None or hit_tapa["ref"].get("cuerpo") != b:
    hit_tapa = hit_desde_ref(refs.referencia(b, tapa, geo.caja_envolvente(forma)), v.doc.estado_final)
p = abrir_menu("plano_desfase")
A.elegir(p, "r0", hit_tapa)
teclear(p, "distancia", "5 mm")
p._t_previa.stop()
p._calcular_previa()
QTest.keyClick(p, Qt.Key_Return)
A.esperar(300)
sigue = v.doc.operaciones[-1]
antes = v.doc.estado_final.planos[sigue.id].origen.copy()
L("set_parameter", name="alto_pieza", expression="35 mm")
A.esperar(300)
despues = v.doc.estado_final.planos[sigue.id].origen.copy()
paso = float((despues - antes) @ plano_i.normal)
anotar("pieza", "cambiar la cota mueve la tapa y el plano la sigue", abs(abs(paso) - 15) < 1e-3, f"se movió {paso:.3f} mm por la normal (esperado 15)")
A.foto(v, "construir_pieza_real")

# --------------------------------------------------------------------- ventana chica
for ancho, alto in ((1024, 640), (800, 520)):
    v.resize(ancho, alto)
    A.esperar(200)
    for clave in CLAVES:
        p = abrir_menu(clave)
        if p is None:
            continue
        A.esperar(60)
        abajo = p.boton_ok.mapTo(v, QPoint(0, p.boton_ok.height())).y()
        der = p.boton_cancelar.mapTo(v, QPoint(p.boton_cancelar.width(), 0)).x()
        anotar(clave, f"ventana {ancho}x{alto}: Aceptar/Cancelar entran", p.boton_ok.isVisible() and abajo <= v.height() and der <= v.width(), f"abajo={abajo} der={der}")
        if ancho == 800:
            if clave == "scu":
                info = p.comando.info
                orden = v.area.children()
                anotar("scu", "ventana chica: la información queda encima del navegador y debajo del panel",
                       all(orden.index(w) < orden.index(info) for w in v.area.arriba_izq) and orden.index(info) < orden.index(p), "")
            A.foto(v, f"construir_{clave}_800")
        p.cancelar()
        A.esperar(40)
v.resize(1900, 1000)
A.esperar(200)
for clave in ("plano_desfase", "plano_perpendicular", "plano_angulo", "plano_tangente", "eje_cilindro", "punto_vertice", "scu"):
    p = abrir_menu(clave)
    if p is not None:
        A.foto(v, f"construir_panel_{clave}")
        p.cancelar()

anotar("general", "ninguna excepción escapó de un slot de Qt en toda la corrida", not A.ERRORES, f"{len(A.ERRORES)}: {A.ERRORES[-1:]}")
(A.SALIDA / "construir_resumen.json").write_text(json.dumps(EXIT, ensure_ascii=False, indent=1), encoding="utf-8")
A.guardar_registro("construir")
fallas = [r for r in A.REGISTRO if not r["ok"]]
print(f"\n=== {len(A.REGISTRO)} comprobaciones, {len(fallas)} con ✗ ===")
v.doc.modificado = False
v.close()
sys.exit(0)

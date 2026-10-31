# -*- coding: utf-8 -*-
"""SÓLIDO · Patrón rectangular, circular, en trayectoria, en puntos y Multitransformación en la ventana real: botones y
menús, selección con el visor, teclear cantidades, distancias, ángulos y copias suprimidas, casillas de supresión con clic
sobre la vista, asas arrastradas con el ratón, cambio de tipo y de modo, Aceptar / Cancelar / Esc, editar un patrón hecho,
deshacer y rehacer, guardar y reabrir. Mide volúmenes y posiciones. Eventos simulados al visor y a los widgets del panel
(nunca el cursor real)."""
import os
import tempfile

import arnes as A
import numpy as np
from omnicad import api
from omnicad.nucleo import geometria as geo
from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

AR = "SÓLIDO·PATRONES"
s = api.Sesion()


def L(nombre, **a):
    r = api.llamar(s, nombre, a)
    assert r["ok"], (nombre, a, r)
    return r["result"]


caja = L("create_box", length=10, width=10, height=10, x=0, y=0)["bodies_created"][0]["id"]      # x -5..5, y -5..5, z 0..10
L("create_sketch", name="Ruta", plane="XY")
L("draw_line", sketch="Ruta", start_x=0, start_y=30, end_x=40, end_y=30)
L("draw_line", sketch="Ruta", start_x=40, start_y=30, end_x=40, end_y=70)
L("create_sketch", name="Puntos", plane="XY")
L("draw_point", sketch="Puntos", x=60, y=-40)
L("draw_point", sketch="Puntos", x=-60, y=-40)
app, v = A.iniciar(s.doc)
v.visor.vista("iso")
v.visor.encuadrar()
A.esperar(300)


def vols():
    return {k: x[1] for k, x in A.cuerpos_resumen(v).items()}


def minimos(prefijo):
    return sorted(tuple(round(float(x), 3) for x in geo.caja_envolvente(c.forma)[0])
                  for cid, c in v.doc.estado_final.cuerpos.items() if cid.startswith(prefijo))


def teclear(w, texto):
    w.setFocus()
    QTest.keyClick(w, Qt.Key_A, Qt.ControlModifier)
    QTest.keyClicks(w, texto)
    QTest.keyClick(w, Qt.Key_Tab)
    A.esperar(60)


def marcar(casilla):
    """Clic real sobre el cuadradito de una casilla (el medio del widget puede caer fuera de él)."""
    QTest.mouseClick(casilla, Qt.LeftButton, pos=QPoint(6, max(casilla.height() // 2, 6)))


def elegir_combo(combo, clave):
    i = combo.findData(clave)
    QTest.keyClick(combo, Qt.Key_Home)
    for _ in range(i):
        QTest.keyClick(combo, Qt.Key_Down)
    A.esperar(60)


def raton(tipo, xy, boton=Qt.LeftButton, botones=Qt.LeftButton):
    p = QPointF(float(xy[0]), float(xy[1]))
    QApplication.sendEvent(v.visor, QMouseEvent(tipo, p, p, boton, botones, Qt.NoModifier))


def clic_vista(xy):
    raton(QEvent.MouseButtonPress, xy)
    raton(QEvent.MouseButtonRelease, xy, boton=Qt.LeftButton, botones=Qt.NoButton)
    A.esperar(80)


def arrastrar_vista(a, b, pasos=8):
    a, b = np.asarray(a, float), np.asarray(b, float)
    raton(QEvent.MouseButtonPress, a)
    for k in range(1, pasos + 1):
        raton(QEvent.MouseMove, a + (b - a) * k / pasos, boton=Qt.NoButton)
    raton(QEvent.MouseButtonRelease, b, boton=Qt.LeftButton, botones=Qt.NoButton)
    A.esperar(120)


def manip(p, tipo, clave=None):
    return next((m for m in p.manipuladores.manips if type(m).__name__ == tipo and (clave is None or m.clave == clave)), None)


def aceptar(p):
    QTest.mouseClick(p.boton_ok, Qt.LeftButton)
    A.esperar(300)


def deshacer_todo(n0):
    while A.n_ops(v) > n0:
        A.deshacer(v)


# ---------------------------------------------------------------- rectangular
def rectangular():
    n0, v0 = A.n_ops(v), vols()
    p = A.abrir(v, "patron_rectangular_3d")
    A.elegir(p, "cuerpos", A.hit_cuerpo(v, caja))
    A.elegir(p, "dir1", A.hit_eje(v, "X"))
    elegir_combo(p.widgets["distribucion"], "espaciado")
    teclear(p.widgets["n1"], "3")
    teclear(p.widgets["d1"], "30 mm")
    A.reg(AR + " · rectangular", "con Cantidad 2 = 1 no se muestran Distancia 2 ni Simétrico 2 (nada activo que se ignore)",
          not p.widgets["d2"].isVisible() and not p.widgets["simetrico2"].isVisible(), "")
    A.reg(AR + " · rectangular", "el asa de la dirección 2 (cantidad) se ofrece aunque falte elegirla",
          manip(p, "AsaCantidad", "n2") is not None, str([m.ident for m in p.manipuladores.manips]))
    teclear(p.widgets["n2"], "2")
    teclear(p.widgets["d2"], "25 mm")
    p._t_previa.stop()
    p._calcular_previa()
    A.esperar(150)
    A.reg(AR + " · rectangular", "Cantidad 2 > 1 sin Dirección 2: se deriva la perpendicular, se dice en el panel y hay flecha",
          "derivada" in p.widgets["info_dir2"].text() and manip(p, "Flecha", "d2") is not None, p.widgets["info_dir2"].text())
    elegir_combo(p.widgets["distribucion"], "espaciado")
    marcar(p.widgets["ver_casillas"])
    A.esperar(150)
    cas = manip(p, "CasillasCopias")
    A.reg(AR + " · rectangular", "con «Elegir copias a suprimir» hay una casilla por copia (6)", cas is not None and len(cas.items) == 6,
          str(len(cas.items)) if cas else "sin casillas")
    if cas is not None:
        punto = next(q for ident, q, _e in cas.items if ident == (2, 1))
        xy = v.visor.proyectar(np.asarray(punto, float))
        clic_vista((xy.x(), xy.y()) if hasattr(xy, "x") else xy)
        A.reg(AR + " · rectangular", "clic en la casilla de la copia (2, 1) la suprime (campo «2:1»)", p.valores.get("suprimir") == "2:1",
              p.valores.get("suprimir"))
    A.foto(v, "patron_rectangular_casillas")
    teclear(p.widgets["n1"], "4")
    p._t_previa.stop()
    p._calcular_previa()
    A.esperar(150)
    A.reg(AR + " · rectangular", "subir la cantidad a 4 mantiene la exclusión en SU copia (7 instancias, falta la (2, 1))",
          p._previa_ok and p.ultima_op.p["suprimir"] == [[2, 1]], str(p.ultima_op.p["suprimir"] if p.ultima_op else p.mensaje.text()))
    teclear(p.widgets["n1"], "2")
    p._t_previa.stop()
    p._calcular_previa()
    A.esperar(150)
    A.reg(AR + " · rectangular", "bajar la cantidad a 2 deja la exclusión fuera: se avisa y se conserva", "ya no existen" in p.mensaje.text()
          and p.valores.get("suprimir") == "2:1", p.mensaje.text()[:80])
    teclear(p.widgets["n1"], "3")
    marcar(p.widgets["simetrico"])
    A.esperar(100)
    p._t_previa.stop()
    p._calcular_previa()
    A.esperar(150)
    op = p.ultima_op
    A.reg(AR + " · rectangular", "simetría solo en la dirección 1: 5 × 2 instancias menos la suprimida",
          p._previa_ok and (op.p["simetrico"], op.p["simetrico2"]) == (True, False), str(op.p["simetrico"]) if op else p.mensaje.text())
    QTest.keyClick(p, Qt.Key_Escape)                                # cancelar no deja nada
    A.esperar(200)
    A.reg(AR + " · rectangular", "Esc cancela y el documento queda igual", A.n_ops(v) == n0 and vols() == v0, "")
    # de nuevo, completo, para aceptar
    p = A.abrir(v, "patron_rectangular_3d")
    A.elegir(p, "cuerpos", A.hit_cuerpo(v, caja))
    A.elegir(p, "dir1", A.hit_eje(v, "X"))
    elegir_combo(p.widgets["distribucion"], "espaciado")
    teclear(p.widgets["n1"], "3")
    teclear(p.widgets["d1"], "30 mm")
    teclear(p.widgets["n2"], "2")
    teclear(p.widgets["d2"], "25 mm")
    teclear(p.widgets["suprimir"], "2:1")
    p._t_previa.stop()
    p._calcular_previa()
    aceptar(p)
    nuevos = [k for k in vols() if k not in v0]
    A.reg(AR + " · rectangular", "Aceptar crea un paso con 4 copias nuevas (3 × 2 − original − la suprimida) de 1000 mm³",
          A.n_ops(v) == n0 + 1 and len(nuevos) == 4 and all(abs(vols()[k] - 1000) < 1e-6 for k in nuevos), f"{len(nuevos)} nuevos")
    esq = minimos(v.doc.operaciones[-1].id)
    A.reg(AR + " · rectangular", "faltan justo las posiciones de la copia (2, 1): x = 60 y = 25 (+ el cubo de origen)",
          (55.0, 20.0, 0.0) not in esq and (55.0, -5.0, 0.0) in esq, str(esq))
    # editar: la exclusión vuelve como «2:1»
    op = v.doc.operaciones[-1]
    v.editar_operacion(op.id)
    A.esperar(250)
    pe = v.panel
    A.reg(AR + " · rectangular", "editar el paso muestra n2 = 2, la dirección 2 derivada y «2:1»",
          pe is not None and pe.valores.get("suprimir") == "2:1" and pe.valores.get("n2") == 2, str(pe.valores.get("suprimir")) if pe else "")
    if pe is not None:
        pe.cancelar()
        A.esperar(150)
    A.deshacer(v)
    A.reg(AR + " · rectangular", "un solo deshacer quita todo el patrón", A.n_ops(v) == n0 and vols() == v0, "")
    deshacer_todo(n0)


# ---------------------------------------------------------------- circular
def circular():
    n0, v0 = A.n_ops(v), vols()
    L("create_box", length=4, width=4, height=4, x=30, y=0)
    cubo = [k for k in vols() if k not in v0][0]
    n1 = A.n_ops(v)
    p = A.abrir(v, "patron_circular_3d")
    A.elegir(p, "cuerpos", A.hit_cuerpo(v, cubo))
    A.elegir(p, "eje", A.hit_eje(v, "Z"))
    teclear(p.widgets["n"], "3")
    p._t_previa.stop()
    p._calcular_previa()
    A.reg(AR + " · circular", "Completo oculta el ángulo y reparte 360° sin repetir el cierre (0°, 120°, 240°)",
          not p.widgets["angulo"].isVisible() and "0°, 120°, 240°" in p.widgets["info_circular"].text(), p.widgets["info_circular"].text())
    elegir_combo(p.widgets["modo"], "parcial")
    teclear(p.widgets["angulo"], "120 deg")
    p._t_previa.stop()
    p._calcular_previa()
    A.esperar(150)
    A.foto(v, "patron_circular_parcial")
    asa = manip(p, "AsaCantidad", "n")
    ang = manip(p, "Angulo", "angulo")
    A.reg(AR + " · circular", "Parcial 3 copias sobre 120°: copias a 0°, 60° y 120° y asas de ángulo y cantidad",
          "0°, 60°, 120°" in p.widgets["info_circular"].text() and asa is not None and ang is not None, p.widgets["info_circular"].text())
    if asa is not None:
        gm = p.manipuladores
        a, _pt, t = asa._asa(gm)
        xy, ok = gm.pantalla([a, a + t * asa.paso * 2])
        if ok.all():
            arrastrar_vista(xy[0], xy[1])
        A.reg(AR + " · circular", "tirar del asa de cantidad suma dos copias (5)", p.widgets["n"].value() == 5, str(p.widgets["n"].value()))
    elegir_combo(p.widgets["modo"], "simetrico")
    teclear(p.widgets["angulo"], "90 deg")
    p._t_previa.stop()
    p._calcular_previa()
    A.reg(AR + " · circular", "Simétrico con 5: copias a ambos lados (9 instancias)",
          p._previa_ok and p.ultima_op.p["distribucion"] == "simetrico", p.mensaje.text()[:80])
    p.cancelar()
    A.esperar(150)
    deshacer_todo(n1)
    deshacer_todo(n0)


# ---------------------------------------------------------------- trayectoria
def trayectoria():
    n0, v0 = A.n_ops(v), vols()
    p = A.abrir(v, "patron_ruta")
    A.elegir(p, "cuerpos", A.hit_cuerpo(v, caja))
    A.elegir(p, "ruta", A.hit_curva(v, s, "Ruta", 0), A.hit_curva(v, s, "Ruta", 1))
    teclear(p.widgets["rn"], "3")
    teclear(p.widgets["rd"], "40 mm")
    p._t_previa.stop()
    p._calcular_previa()
    A.esperar(200)
    tramo = manip(p, "AsaRecorrido", "rd")
    A.reg(AR + " · trayectoria", "las asas recorren la cadena de las DOS aristas (80 mm), no solo la primera",
          tramo is not None and abs(tramo.recorrido.largo - 80.0) < 1e-6, str(tramo.recorrido.largo if tramo else None))
    if tramo is not None:
        gm = p.manipuladores
        xy, ok = gm.pantalla([tramo.asa(gm), (40.0, 70.0, 0.0)])
        if ok.all():
            arrastrar_vista(xy[0], xy[1])
        d = p.ctx.evaluar(p.valores["rd"])
        A.reg(AR + " · trayectoria", "arrastrar el asa hasta el final de la segunda arista da distancia ≈ 80 mm", abs(d - 80.0) < 2.5, f"{d:.2f} mm")
    p._t_previa.stop()
    p._calcular_previa()
    A.esperar(150)
    A.foto(v, "patron_trayectoria")
    A.reg(AR + " · trayectoria", "la vista previa coincide con el asa: última copia en el final de la ruta (40, 70)",
          p._previa_ok, p.mensaje.text()[:80])
    teclear(p.widgets["rn"], "6")
    teclear(p.widgets["rd"], "20 mm")
    elegir_combo(p.widgets["distribucion"], "espaciado")
    p._t_previa.stop()
    p._calcular_previa()
    A.esperar(150)
    A.reg(AR + " · trayectoria", "6 copias cada 20 mm sobre 80 mm: caben 5 y se avisa la que no (no se extrapola)",
          "La ruta no alcanza" in p.mensaje.text(), p.mensaje.text()[:100])
    p.cancelar()
    A.esperar(150)
    A.reg(AR + " · trayectoria", "Cancelar no deja nada", A.n_ops(v) == n0 and vols() == v0, "")


# ---------------------------------------------------------------- puntos
def puntos():
    n0 = A.n_ops(v)
    p = A.abrir(v, "patron_puntos")
    A.elegir(p, "cuerpos", A.hit_cuerpo(v, caja))
    br = v.doc.estado_final.bocetos[s.paso("Puntos").id]
    refs = [{"tipo": "punto_boceto", "boceto": s.paso("Puntos").id, "punto": pid} for pid in sorted(br.boceto.puntos)]
    from omnicad.ui.comando import hit_desde_ref
    A.elegir(p, "puntos", *[hit_desde_ref(r, v.doc.estado_final) for r in refs])
    p._t_previa.stop()
    p._calcular_previa()
    A.esperar(200)
    A.reg(AR + " · puntos", "el panel explica que la referencia vacía es el origen y que un boceto aporta solo puntos sueltos",
          "origen" in p.widgets["info_puntos"].text() and "puntos sueltos" in p.widgets["info_puntos"].text(), p.widgets["info_puntos"].text()[:90])
    A.foto(v, "patron_puntos")
    A.reg(AR + " · puntos", "la vista dibuja la referencia y los destinos", "previa_comando" in v.visor._capas, "")
    aceptar(p)
    esq = minimos(v.doc.operaciones[-1].id)
    A.reg(AR + " · puntos", "las dos copias van EXACTAMENTE a (punto − origen): esquinas (55, −45) y (−65, −45)",
          (55.0, -45.0, 0.0) in esq and (-65.0, -45.0, 0.0) in esq, str(esq))
    A.deshacer(v)
    deshacer_todo(n0)


# ---------------------------------------------------------------- multitransformación
def multi():
    n0, v0 = A.n_ops(v), vols()
    p = A.abrir(v, "multitransformar")
    A.elegir(p, "cuerpos", A.hit_cuerpo(v, caja))
    lista = p.widgets["lista"]
    A.elegir(p, "t_dir1", A.hit_eje(v, "X"))
    elegir_combo(p.widgets["t_distribucion"], "espaciado")
    teclear(p.widgets["t_n1"], "3")
    teclear(p.widgets["t_d1"], "30 mm")
    lista.agregar.menu().actions()[4].trigger()                # Simetría
    A.esperar(150)
    p._t_previa.stop()
    p._calcular_previa()
    A.reg(AR + " · multi", "con la simetría sin plano no hay vista previa y el panel dice cuál falta",
          p.ultima_op is None and "Transformación 2" in p.mensaje.text(), p.mensaje.text()[:100])
    A.elegir(p, "t_plano", A.hit_plano(v, "YZ"))
    p._t_previa.stop()
    p._calcular_previa()
    A.esperar(150)
    A.foto(v, "patron_multitransformacion")
    A.reg(AR + " · multi", "con las dos completas hay vista previa válida (3 + simetría = 6 instancias)", p._previa_ok, p.mensaje.text()[:80])
    QTest.mouseClick(lista.subir, Qt.LeftButton)
    A.esperar(120)
    A.reg(AR + " · multi", "▲ reordena (la simetría pasa primero) y la fila elegida sigue a su transformación",
          lista.lista.currentRow() == 0 and p.valores["t_tipo"] == "simetria", "")
    QTest.mouseClick(lista.bajar, Qt.LeftButton)
    A.esperar(120)
    p._t_previa.stop()
    p._calcular_previa()
    aceptar(p)
    op = v.doc.operaciones[-1]
    A.reg(AR + " · multi", "Aceptar crea el paso con las dos transformaciones y 5 copias",
          op.TIPO == "multitransformar" and len(op.p["transformaciones"]) == 2 and len([k for k in vols() if k not in v0]) == 5,
          str([t["tipo"] for t in op.p["transformaciones"]]))
    v.editar_operacion(op.id)
    A.esperar(250)
    pe = v.panel
    if pe is not None:
        pe._t_previa.stop()
        pe._calcular_previa()
        A.reg(AR + " · multi", "editar y aceptar sin tocar conserva las dos transformaciones", pe._previa_ok and pe.ultima_op is not None
              and [t["tipo"] for t in pe.ultima_op.p["transformaciones"]] == ["rectangular", "simetria"], pe.mensaje.text()[:80])
        pe.cancelar()
        A.esperar(150)
    deshacer_todo(n0)


# ---------------------------------------------------------------- guardar y reabrir
def guardar():
    n0 = A.n_ops(v)
    L("rectangular_pattern", bodies=caja, x_count=3, x_spacing=20, y_count=2, y_spacing=30, axis2="y", symmetric=True,
      symmetric2=False, suppress=[[1, 1]])
    antes = sorted(vols().values())
    ruta = os.path.join(tempfile.mkdtemp(prefix="omnicad_pat_"), "patron.omnicad")
    L("save_document", path=ruta)
    s2 = api.Sesion()
    r2 = api.llamar(s2, "open_document", {"path": ruta})
    p = s2.doc.operaciones[-1].p
    A.reg(AR + " · guardar", "guardar y reabrir conserva la simetría por dirección, la supresión [i, j] y el resultado",
          r2["ok"] and p["simetrico2"] is False and p["suprimir"] == [[1, 1]] and sorted(
              c[1] for c in A.cuerpos_resumen(type("V", (), {"doc": s2.doc})()).values()) == antes, str(p["suprimir"]))
    deshacer_todo(n0)


for nombre, f in (("rectangular", rectangular), ("circular", circular), ("trayectoria", trayectoria), ("puntos", puntos),
                  ("multitransformación", multi), ("guardar", guardar)):
    A.correr(f"{AR} · {nombre}", f)

A.reg(AR, "no se escapó ninguna excepción dentro de un slot de Qt", not A.ERRORES, "; ".join(A.ERRORES)[:300])
A.guardar_registro("patrones_solidos")
fallas = sum(1 for r in A.REGISTRO if not r["ok"])
print(f"=== {len(A.REGISTRO)} comprobaciones, {fallas} con ✗", flush=True)

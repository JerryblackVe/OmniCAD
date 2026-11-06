# -*- coding: utf-8 -*-
"""Nervio, Red y Repujado en cada espacio, como una persona (auditoría 2026-11-05, docs/auditoria_nervio_red_repujado.md):
los botones en SÓLIDO y PLÁSTICO (SUPERFICIE, CHAPA y MALLA no los tienen, como Fusion), elegir en el visor, teclear
cada campo (coma, expresión, vacío, unidad mala, pegar), Tab, Enter, Esc, las asas (arrastrar y pasar por cero),
Invertir, desmoldeo negativo, varias curvas sueltas, cadena tangente del repujado, reabrir y deshacer (corredor),
ventana chica y guardar → reabrir. Lo que ya cubre `solido_crear` (caso simple y negativos) no se repite."""
import sys
import tempfile
from pathlib import Path

import arnes as A
import corredor as C
from omnicad import api
from omnicad.ui import cinta as ci
from omnicad.ui import manipuladores as mp
from omnicad.ui.comando import PanelComando
from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QToolButton
from teclado import pegar, teclear

s = api.Sesion()


def L(nombre, **a):
    r = api.llamar(s, nombre, a)
    assert r["ok"], (nombre, a, r)
    return r["result"]


# Escuadra (piso x 0..40, y −30..30, z 0..5 + pared x 0..5, z 0..50 = 25500 mm³). En XZ (y = 0) la línea (35, 5) →
# (5, 45): nervio de 600 mm² de cara; con 2 mm, +1200 mm³ (cuenta igual que las sondas de la API).
L("create_box", length=40, width=60, height=5, x=0, y=-30, z=0, anchor="corner")
L("create_box", length=5, width=60, height=50, x=0, y=-30, z=0, anchor="corner", operation="join")
ESC = next(iter(s.doc.estado_final.cuerpos))
L("create_parameter", name="e", expression="1.5 mm")
L("create_sketch", plane="XZ", name="N1"); L("draw_line", sketch="N1", start_x=35, start_y=5, end_x=5, end_y=45)
L("create_sketch", plane="XZ", name="N2")
L("draw_line", sketch="N2", start_x=35, start_y=5, end_x=5, end_y=45)
L("draw_line", sketch="N2", start_x=30, start_y=5, end_x=5, end_y=38.333333)
# Caja hueca 40³ en x 100..140, abierta en y = 0, y un boceto adentro en y = 15 (el plano XZ desplazado −15 mira a −Y):
# la Red va a la pared del fondo (y = 38): 36·23·2 = 1656 mm³. Hacia −Y no hay pared (Fusion: Invertir → error).
L("create_box", length=40, width=40, height=40, x=100, y=0, z=0, anchor="corner")
HUE = [c for c in s.doc.estado_final.cuerpos][-1]
L("shell", body=HUE, faces="<Y", thickness=2)
L("create_construction_plane", plane="XZ", offset=-15, name="P15")
L("create_sketch", plane="P15", name="W"); L("draw_line", sketch="W", start_x=110, start_y=20, end_x=130, end_y=20)
# Placa 60×40×10 en x 200..260 con las aristas de arriba empalmadas r 3; cuadro 10×10 encima: relieve 1 = +100 mm³.
L("create_box", length=60, width=40, height=10, x=200, y=0, z=0, anchor="corner")
PLA = [c for c in s.doc.estado_final.cuerpos][-1]
L("fillet", edges=">Z", radius=3, body=PLA)
L("create_construction_plane", plane="XY", offset=10, name="Arriba")
L("create_sketch", plane="Arriba", name="E"); L("draw_rectangle", sketch="E", x1=220, y1=15, x2=230, y2=25)

app, v = A.iniciar(s.doc)
AR = "NER·RED·REP"
cur = lambda n, i=0: A.hit_curva(v, s, n, i)  # noqa: E731
per = lambda n, i=0: A.hit_perfil(v, s, n, i)  # noqa: E731
CLAVES = ("nervio", "red", "repujado")


def panel_abierto():
    return next((p for p in v.findChildren(PanelComando) if p.isVisible()), None)


def boton_de(clave):
    """El botón visible de la pestaña actual con la acción `clave`, o el título de grupo cuyo menú la trae."""
    accion = v.acciones.get(clave)
    for b in v.cinta.pila.currentWidget().findChildren(QToolButton):
        if not b.isVisible() or accion is None:
            continue
        if b.defaultAction() is accion:
            return b, None
        if b.menu() is not None and accion in b.menu().actions():
            return b, accion
    return None, None


def previa(p):
    p._t_previa.stop(); p._calcular_previa(); A.esperar(150)
    return A.estado_panel(p)


def cinta():
    """Fusion: Rib, Web y Emboss están en SÓLIDO › Crear y en PLÁSTICO › Crear; no en Superficie, Chapa ni Malla."""
    esperado = {"SÓLIDO": CLAVES, "PLÁSTICO": CLAVES, "SUPERFICIE": (), "CHAPA": (), "MALLA": ()}
    for i, (nombre, _g) in enumerate(ci.PESTANAS):
        if nombre not in esperado:
            continue
        QTest.mouseClick(v.cinta.pestanas[i], Qt.LeftButton)
        A.esperar(150)
        if not esperado[nombre]:
            A.reg(AR, f"{nombre}: sin Nervio, Red ni Repujado (Fusion tampoco)", all(boton_de(k)[0] is None for k in CLAVES))
            continue
        for clave in CLAVES:
            b, accion = boton_de(clave)
            if b is None:
                A.reg(AR, f"{nombre}: botón de «{clave}»", False, "no está en la pestaña")
                continue
            n0, n_err = A.n_ops(v), len(A.ERRORES)
            accion.trigger() if accion is not None else QTest.mouseClick(b, Qt.LeftButton)
            A.esperar(250)
            p = panel_abierto()
            abierto = getattr(getattr(p, "comando", None), "CLAVE", None)
            A.reg(AR, f"{nombre}: el botón abre «{clave}»", abierto == clave and len(A.ERRORES) == n_err, f"abrió {abierto}")
            if p is not None:
                QTest.keyClick(p, Qt.Key_Escape); A.esperar(150)
                A.reg(AR, f"{nombre}: Esc cierra «{clave}» sin crear pasos", panel_abierto() is None and A.n_ops(v) == n0)
    QTest.mouseClick(v.cinta.pestanas[0], Qt.LeftButton); A.esperar(150)


def nervio_caso():
    """Caso completo por el corredor: elegir curva y cuerpo, previa, aceptar (+1200), reabrir, deshacer."""
    C.caso(v, AR, "nervio", {"curvas": lambda: [cur("N1")], "objetivo": lambda: [A.hit_cuerpo(v, ESC)]},
           {"espesor": "2 mm"}, esperado=1200, foto="nervio_escuadra", etiqueta="Nervio escuadra")


def nervio_teclear():
    """Grosor tecleado: coma, expresión con parámetro, vacío, unidad de ángulo, pegar; Tab avanza; Enter acepta."""
    n0, antes = A.n_ops(v), A.cuerpos_resumen(v)
    p = A.abrir(v, "nervio")
    A.elegir(p, "curvas", cur("N1"))
    for texto, valido in (("2,5", True), ("e * 2", True), ("", False), ("10 deg", False), ("abc", False)):
        teclear(p, "espesor", texto, Qt.Key_Tab)
        st = previa(p)
        A.reg(AR, f"Nervio › Grosor «{texto}»: {'previa' if valido else 'aviso'}",
              st["previa_ok"] if valido else (not st["previa_ok"] and bool(st["mensaje"])), st["mensaje"])
    pegar(p, "espesor", "3 mm")
    st = previa(p)
    A.reg(AR, "Nervio › Grosor pegado «3 mm» (Ctrl+V): previa", st["previa_ok"], st["mensaje"])
    w = p.widgets["espesor"]
    QTest.mouseClick(w, Qt.LeftButton); QTest.keyClick(w, Qt.Key_Tab); A.esperar(80)
    foco = QApplication.focusWidget()
    if foco is None:            # minimizada: la ventana transparente no recibe el foco de Windows
        print("⚠ Tab: sin foco en la ventana (correr con --ventana visible para comprobarlo)", flush=True)
    else:
        A.reg(AR, "Nervio › Tab saca el foco del Grosor al campo siguiente", foco is not w, type(foco).__name__)
    QTest.keyClick(p, Qt.Key_Return); A.esperar(450)
    vol = round(sum(x[1] for k, x in A.cuerpos_resumen(v).items()) - sum(x[1] for x in antes.values()), 2)
    A.reg(AR, "Nervio › Enter acepta con Grosor 3 mm: +1800 mm³ (600·3) y UN paso", A.n_ops(v) == n0 + 1 and abs(vol - 1800) < 1,
          f"pasos {A.n_ops(v) - n0}, volumen +{vol}")
    if A.n_ops(v) > n0:
        A.deshacer(v)
    A.reg(AR, "Nervio › deshacer vuelve atrás", A.n_ops(v) == n0 and A.cuerpos_resumen(v) == antes)


def nervio_invertir():
    """B-213: Invertir manda el nervio hacia afuera; Fusion no encuentra cara y avisa. OmniCAD lo rellena hasta la caja."""
    C.caso(v, AR, "nervio", {"curvas": lambda: [cur("N1")], "objetivo": lambda: [A.hit_cuerpo(v, ESC)]},
           {"espesor": "2 mm", "invertir": True}, error="no llega", foto="nervio_invertido", etiqueta="Nervio invertido")


def nervio_varias_curvas():
    """B-214: dos curvas sueltas (Fusion: un nervio por curva, la ayuda muestra 4 en un paso)."""
    C.caso(v, AR, "nervio", {"curvas": lambda: [cur("N2", 0), cur("N2", 1)], "objetivo": lambda: [A.hit_cuerpo(v, ESC)]},
           {"espesor": "2 mm"}, etiqueta="Nervio con dos curvas sueltas", rt=False)


def nervio_desmoldeo():
    """B-215: ángulo de desmoldeo −1° (la API acepta −45..45) y +1° con dirección de extracción."""
    C.caso(v, AR, "nervio", {"curvas": lambda: [cur("N1")], "objetivo": lambda: [A.hit_cuerpo(v, ESC)]},
           {"espesor": "2 mm", "angulo_desmoldeo": "-1 deg"}, etiqueta="Nervio desmoldeo −1°", rt=False)
    C.caso(v, AR, "nervio", {"curvas": lambda: [cur("N1")], "objetivo": lambda: [A.hit_cuerpo(v, ESC)],
                             "direccion_desmoldeo": lambda: [A.hit_plano(v, "XY")]},
           {"espesor": "2 mm", "angulo_desmoldeo": "1 deg"}, etiqueta="Nervio desmoldeo 1° con extracción", rt=False)


def nervio_campos_fusion():
    """Fusion Rib: Fillet Radius y Flip (pull direction). Se miran los campos del panel con «Más opciones» abierto."""
    p = A.abrir(v, "nervio")
    if p.seccion is not None and not p.seccion.abierta:
        QTest.mouseClick(p.seccion.boton, Qt.LeftButton); A.esperar(120)
    vis = {c.clave for c in p.campos if p._visible(c)}
    A.reg(AR, "Nervio › tiene Radio del empalme (Fusion Rib: Fillet Radius)", "radio_empalme" in vis, f"campos {sorted(vis)}")
    A.foto(v, "nervio_panel")
    QTest.keyClick(p, Qt.Key_Escape); A.esperar(150)


def red_invertir():
    """B-216: Invertir en la Red. Hacia +Y la pared del fondo (1656 mm³); invertida, hacia la boca abierta (Fusion: error)."""
    C.caso(v, AR, "red", {"curvas": lambda: [cur("W")], "objetivo": lambda: [A.hit_cuerpo(v, HUE)]},
           {"espesor": "2 mm"}, esperado=1656, etiqueta="Red dentro de la caja", rt=False, foto="red_caja")
    C.caso(v, AR, "red", {"curvas": lambda: [cur("W")], "objetivo": lambda: [A.hit_cuerpo(v, HUE)]},
           {"espesor": "2 mm", "invertir": True}, error="no", etiqueta="Red invertida hacia la boca abierta",
           foto="red_invertida")


def repujado():
    """Relieve 1 mm sobre la cara de arriba de la placa empalmada: +100; con cadena tangente también tiene que dar +100
    (B-217: lo repuja además en los costados). Profundidad negativa tecleada: Fusion cambia el Efecto a Grabado."""
    C.caso(v, AR, "repujado", {"perfiles": lambda: [per("E")], "caras": lambda: [A.hit_cara(v, PLA, normal=(0, 0, 1))]},
           {"profundidad": "1 mm"}, esperado=100, etiqueta="Repujado placa", foto="repujado_placa")
    C.caso(v, AR, "repujado", {"perfiles": lambda: [per("E")], "caras": lambda: [A.hit_cara(v, PLA, normal=(0, 0, 1))]},
           {"profundidad": "1 mm", "cadena_tangente": True}, esperado=100, etiqueta="Repujado con cadena tangente",
           rt=False, foto="repujado_cadena")
    p = A.abrir(v, "repujado")
    A.elegir(p, "perfiles", per("E")); A.elegir(p, "caras", A.hit_cara(v, PLA, normal=(0, 0, 1)))
    for texto, valido in (("0,5", True), ("-1 mm", True), ("0", False), ("", False), ("2 deg", False)):
        teclear(p, "profundidad", texto, Qt.Key_Tab)
        st = previa(p)
        A.reg(AR, f"Repujado › Profundidad «{texto}»: {'previa' if valido else 'aviso'}",
              st["previa_ok"] if valido else (not st["previa_ok"] and bool(st["mensaje"])), st["mensaje"])
        if texto == "-1 mm":
            A.reg(AR, "Repujado › con profundidad negativa el Tipo pasa a Grabado (Fusion: Effect cambia solo)",
                  p.valores.get("tipo") == "grabado", f"Tipo = {p.valores.get('tipo')}")
    QTest.keyClick(p, Qt.Key_Escape); A.esperar(150)


def _mover(w, q):
    QApplication.sendEvent(w, QMouseEvent(QEvent.MouseMove, q, w.mapToGlobal(q), Qt.NoButton, Qt.NoButton, Qt.NoModifier))


def _arrastrar(p, g, desde, hasta, pasos=6):
    """Press, varios movimientos y release simulados al visor (no mueve el cursor real)."""
    xy, ok = g.pantalla([desde, hasta])
    if not ok.all():
        return False
    a, b = (QPointF(*q) for q in xy)
    vis = p.visor
    _mover(vis, a)
    QApplication.sendEvent(vis, QMouseEvent(QEvent.MouseButtonPress, a, vis.mapToGlobal(a), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier))
    for i in range(1, pasos + 1):
        q = a + (b - a) * (i / pasos)
        QApplication.sendEvent(vis, QMouseEvent(QEvent.MouseMove, q, vis.mapToGlobal(q), Qt.NoButton, Qt.LeftButton, Qt.NoModifier))
        A.esperar(15)
    QApplication.sendEvent(vis, QMouseEvent(QEvent.MouseButtonRelease, b, vis.mapToGlobal(b), Qt.LeftButton, Qt.NoButton, Qt.NoModifier))
    A.esperar(120)
    previa(p)
    return True


def asas():
    """Cada flecha: 3 mm hacia afuera (el valor sube 3 / factor) y después más allá del cero (tope, sin excepción)."""
    casos = (("nervio", {"curvas": [cur("N1")]}, {"extension": "profundidad", "profundidad": "5 mm"}),
             ("red", {"curvas": [cur("W")]}, {"extension": "profundidad", "profundidad": "5 mm"}),
             ("repujado", {"perfiles": [per("E")], "caras": [A.hit_cara(v, PLA, normal=(0, 0, 1))]}, {}))
    for clave, sel, vals in casos:
        p = A.abrir(v, clave)
        for campo, hs in sel.items():
            A.elegir(p, campo, *hs)
        for k, x in vals.items():
            p.set_valor(k, x)
        previa(p)
        g = p.manipuladores
        claves = [getattr(m, "clave", None) for m in (g.manips if g else [])]
        A.reg(AR, f"{clave}: asas en la vista", bool(claves), str(claves))
        if clave == "repujado":
            A.reg(AR, "Repujado › asas de alineación (horizontal, vertical, giro) como Fusion",
                  {"desfase_h", "desfase_v", "giro"} <= set(claves), str(claves))
        A.foto(v, f"asas_{clave}")
        for cl in [c for c in claves if c]:
            m = next((x for x in p.manipuladores.manips if getattr(x, "clave", None) == cl and isinstance(x, mp.Flecha)), None)
            if m is None:
                continue
            g = p.manipuladores
            texto_antes, antes = p.valores.get(cl), g.valor(cl)
            a, b = m.puntos(g)
            ok = _arrastrar(p, g, (a + b) / 2, (a + b) / 2 + m.direccion * 3.0)
            despues = p.manipuladores.valor(cl)
            esperado = 3.0 / (m.factor or 1.0)
            A.reg(AR, f"{clave} › arrastrar «{cl}» 3 mm", ok and abs((despues - antes) - esperado) < max(0.35, esperado * 0.1),
                  f"{antes:g} → {despues:g} (esperado +{esperado:g}); «{p.mensaje.text()}»")
            m = next(x for x in p.manipuladores.manips if getattr(x, "clave", None) == cl)
            g = p.manipuladores
            a, b = m.puntos(g)
            n_err = len(A.ERRORES)
            ok = _arrastrar(p, g, (a + b) / 2, (a + b) / 2 - m.direccion * (abs(despues) + 6) * (m.factor or 1.0))
            final = p.manipuladores.valor(cl)
            A.reg(AR, f"{clave} › «{cl}» arrastrada más allá del cero: tope (si tiene) y sin excepción",
                  ok and (m.minimo is None or final >= m.minimo - 1e-9) and len(A.ERRORES) == n_err,
                  f"{despues:g} → {final:g}")      # el asa del Repujado no tiene tope: negativa graba (H-99)
            p.set_valor(cl, texto_antes)
            st = previa(p)
            A.reg(AR, f"{clave} › «{cl}»: al escribir de nuevo {texto_antes!r} la previa se recupera", st["previa_ok"], st["mensaje"])
        QTest.keyClick(p, Qt.Key_Escape); A.esperar(150)


def ventana_chica():
    """El panel más largo: Red con «Más opciones» abierto (desmoldeo, empalme) y Cuerpo."""
    p = A.abrir(v, "red")
    if p.seccion is not None and not p.seccion.abierta:
        QTest.mouseClick(p.seccion.boton, Qt.LeftButton)
    p.set_valor("extension", "profundidad")
    A.esperar(150)
    for ancho, alto in ((1024, 640), (800, 520)):
        v.resize(ancho, alto); A.esperar(300)
        b = p.boton_ok
        esq = b.mapTo(v, QPoint(b.width() - 1, b.height() - 1))
        dentro = b.isVisible() and not b.visibleRegion().isEmpty() and v.rect().contains(esq)
        A.reg(AR, f"ventana {ancho}x{alto}: Aceptar se ve con la Red y «Más opciones»", dentro,
              f"esquina {esq.x()},{esq.y()} en {v.width()}x{v.height()}")
        A.foto(v, f"red_{ancho}x{alto}")
    v.resize(1900, 1000); A.esperar(200)
    QTest.keyClick(p, Qt.Key_Escape); A.esperar(150)


def guardar_reabrir():
    """Nervio + Red + Repujado aceptados en la ventana: guardar y abrir de nuevo da los mismos volúmenes."""
    n0 = A.n_ops(v)
    C.caso(v, AR, "nervio", {"curvas": lambda: [cur("N1")]}, {"espesor": "2 mm"}, rt=False, deshacer=False, etiqueta="(guardar) nervio")
    C.caso(v, AR, "red", {"curvas": lambda: [cur("W")]}, {"espesor": "2 mm"}, rt=False, deshacer=False, etiqueta="(guardar) red")
    C.caso(v, AR, "repujado", {"perfiles": lambda: [per("E")], "caras": lambda: [A.hit_cara(v, PLA, normal=(0, 0, 1))]},
           {"profundidad": "1 mm"}, rt=False, deshacer=False, etiqueta="(guardar) repujado")
    antes = A.cuerpos_resumen(v)
    ruta = Path(tempfile.mkdtemp()) / "nrr.omnicad"
    r = api.llamar(s, "save_document", {"path": str(ruta)})
    s2 = api.Sesion()
    r2 = api.llamar(s2, "open_document", {"path": str(ruta)})
    from omnicad.nucleo import geometria as geo
    despues = {cid: round(geo.volumen(c.forma), 3) for cid, c in s2.doc.estado_final.cuerpos.items()}
    igual = r["ok"] and r2["ok"] and all(abs(antes[k][1] - despues.get(k, -1)) < 0.01 for k in antes)
    A.reg(AR, f"guardar y reabrir con los tres pasos ({A.n_ops(v) - n0} nuevos): mismos volúmenes", igual,
          f"antes {antes}; después {despues}")


for nombre, f in (("cinta", cinta), ("nervio caso", nervio_caso), ("nervio teclear", nervio_teclear),
                  ("nervio invertir", nervio_invertir), ("nervio varias curvas", nervio_varias_curvas),
                  ("nervio desmoldeo", nervio_desmoldeo), ("nervio campos de Fusion", nervio_campos_fusion),
                  ("red invertir", red_invertir), ("repujado", repujado), ("asas", asas),
                  ("ventana chica", ventana_chica), ("guardar y reabrir", guardar_reabrir)):
    A.correr(f"{AR} · {nombre}", f)
A.reg(AR, "ninguna excepción escapó de un slot de Qt", not A.ERRORES, str(A.ERRORES[-1:])[-300:])

A.guardar_registro("nervio_red_repujado")
fallas = [r for r in A.REGISTRO if not r["ok"]]
print(f"\n=== {len(A.REGISTRO)} comprobaciones, {len(fallas)} con ✗ ===")
v.close()
sys.exit(0)

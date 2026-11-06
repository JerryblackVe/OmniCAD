# -*- coding: utf-8 -*-
"""Revolución, Barrido y Solevación en cada espacio, como una persona (auditoría 2026-11-05,
docs/auditoria_revolucion_barrido_solevacion.md): los botones en SÓLIDO, SUPERFICIE y PLÁSTICO (CHAPA solo tiene la
Pestaña solevada, como Fusion), teclear el ángulo del lado 2 negativo, «A objeto» con «Dos lados», las opciones del
carril del barrido y su volumen, las condiciones de un perfil punto en la solevación, Enter, Esc, reabrir el paso,
deshacer y el panel más largo en ventana chica. Lo que ya cubren `solido_crear`, `superficie` y `asas` no se repite."""
import math
import sys

import arnes as A
import escena
from omnicad import api
from omnicad.ui import cinta as ci
from omnicad.ui.comando import PanelComando
from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QComboBox, QToolButton
from teclado import teclear

PI = math.pi
s, ids = escena.construir()


def L(nombre, **a):
    r = api.llamar(s, nombre, a)
    assert r["ok"], (nombre, a, r)
    return r["result"]


# Barrido con carril, lejos de la escena: cuadrado 4×4 en el plano x=300 centrado en (300, 200, 0), ruta en X de 50 y
# carril paralelo a la ruta (y=202), tocando el borde del perfil. Con «Ninguna» tiene que dar 4·4·50 = 800 mm³.
L("create_construction_plane", plane="YZ", offset=300, name="PX")
marco = L("create_sketch", plane="PX", name="Cua")["plane_frame"]
assert abs(marco["origin"][0] - 300) < 1e-6 and abs(marco["u_axis"][1]) > 0.99, marco    # u = ±Y, v = ±Z
uy = marco["u_axis"][1]
L("draw_rectangle", sketch="Cua", x1=uy * 198, y1=-2, x2=uy * 202, y2=2)
L("create_sketch", plane="XY", name="RutaC"); L("draw_line", sketch="RutaC", start_x=300, start_y=200, end_x=350, end_y=200)
L("create_sketch", plane="XY", name="CarC"); L("draw_line", sketch="CarC", start_x=300, start_y=202, end_x=350, end_y=202)
# Solevación: cuadrado 10×10 en z 0 y 20×20 en z 10 (PM), lejos; y un punto de construcción en (−300, 0, 20) (PL).
L("create_sketch", plane="XY", name="LA"); L("draw_rectangle", sketch="LA", x1=-305, y1=-5, x2=-295, y2=5)
L("create_sketch", plane="PM", name="LB"); L("draw_rectangle", sketch="LB", x1=-310, y1=-10, x2=-290, y2=10)
L("create_construction_plane", plane="YZ", offset=-300, name="PXm")
L("create_construction_point", type="tres_planos", references=["XZ", "PXm", "PL"], name="Punta")
app, v = A.iniciar(s.doc)
AR = "REV·BAR·SOL"
per = lambda n, i=0: A.hit_perfil(v, s, n, i)  # noqa: E731
cur = lambda n, i=0: A.hit_curva(v, s, n, i)  # noqa: E731


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


def nuevos_desde(antes):
    return {k: x for k, x in A.cuerpos_resumen(v).items() if k not in antes}


def cinta():
    esperado = {"SÓLIDO": ("revolucion", "barrido", "solevacion"), "PLÁSTICO": ("revolucion", "barrido", "solevacion"),
                "SUPERFICIE": ("sup_revolucion", "sup_barrido", "sup_solevacion"), "CHAPA": ()}
    for i, (nombre, _g) in enumerate(ci.PESTANAS):
        if nombre not in esperado:
            continue
        QTest.mouseClick(v.cinta.pestanas[i], Qt.LeftButton)
        A.esperar(150)
        if not esperado[nombre]:
            ninguno = all(boton_de(k)[0] is None for k in ("revolucion", "barrido", "solevacion", "sup_revolucion",
                                                           "sup_barrido", "sup_solevacion"))
            A.reg(AR, f"{nombre}: sin Revolución, Barrido ni Solevación (Fusion: solo Pestaña solevada, CHA-1)", ninguno)
            continue
        for clave in esperado[nombre]:
            b, accion = boton_de(clave)
            if b is None:
                A.reg(AR, f"{nombre}: botón de «{clave}»", False, "no está en la pestaña")
                continue
            n_err = len(A.ERRORES)
            accion.trigger() if accion is not None else QTest.mouseClick(b, Qt.LeftButton)
            A.esperar(250)
            p = panel_abierto()
            abierto = getattr(getattr(p, "comando", None), "CLAVE", None)
            A.reg(AR, f"{nombre}: el botón abre «{clave}»", abierto == clave and len(A.ERRORES) == n_err, f"abrió {abierto}")
            if p is not None:
                QTest.keyClick(p, Qt.Key_Escape)
                A.esperar(150)
                A.reg(AR, f"{nombre}: Esc cierra «{clave}» sin crear pasos", panel_abierto() is None)


def revolucion_dos_lados_negativo():
    """Rect 20×10 sobre el eje X: lado 1 = 90°, lado 2 tecleado −45°. Sólido y superficie tienen que dar lo mismo
    (por la API: sólido 1570,80 mm³, que pierde el lado 2; superficie 235,62 mm² como si fuera +45°)."""
    n0, antes = A.n_ops(v), A.cuerpos_resumen(v)
    p = A.abrir(v, "revolucion")
    A.elegir(p, "perfiles", per("Rect"))
    A.elegir(p, "eje", A.hit_eje(v, "X"))
    p.set_valor("direccion", "dos_lados")
    teclear(p, "angulo", "90 deg", Qt.Key_Tab)
    teclear(p, "angulo2", "-45 deg", Qt.Key_Tab)
    p._t_previa.stop(); p._calcular_previa(); A.esperar(150)
    st = A.estado_panel(p)
    if not st["previa_ok"]:
        A.reg(AR, "Revolución dos lados 90 / −45°: se rechaza con aviso", bool(st["mensaje"]), st["mensaje"])
        p.cancelar(); return
    QTest.keyClick(p, Qt.Key_Return)
    A.esperar(450)
    vol = sum(x[1] for x in nuevos_desde(antes).values())
    A.reg(AR, "Enter acepta la revolución y crea UN paso", A.n_ops(v) == n0 + 1)
    # 90 + 45 a lados opuestos = 1570,80 · 1,5 = 2356,19; si el −45 vuelve sobre el lado 1 queda 1570,80 sin aviso.
    A.reg(AR, "Revolución dos lados 90 / −45°: o aviso o 2356,19 mm³ (como la superficie), no el lado 2 perdido",
          abs(vol - PI * 100 * 20 * 135 / 360) < 1, f"volumen {vol:.2f} sin aviso «{st['mensaje']}»")
    op = v.doc.operaciones[-1]
    v.editar_operacion(op.id); A.esperar(250)
    q = panel_abierto()
    A.reg(AR, "reabrir la revolución trae «Dos lados» y −45°", q is not None and q.valores.get("direccion") == "dos_lados"
          and "-45" in str(q.valores.get("angulo2")), q and str({k: q.valores.get(k) for k in ("direccion", "angulo2")}))
    if q is not None:
        QTest.keyClick(q, Qt.Key_Escape); A.esperar(150)
    A.deshacer(v)
    A.reg(AR, "deshacer quita la revolución", A.n_ops(v) == n0)
    v.acciones["rehacer"].trigger(); A.esperar(250)
    A.reg(AR, "rehacer la vuelve a poner", A.n_ops(v) == n0 + 1)
    A.deshacer(v)


def revolucion_objeto_dos_lados():
    """Fusion: con Tipo de extensión «A objeto», la Dirección ofrece Un lado y Dos lados."""
    for clave in ("revolucion", "sup_revolucion"):
        p = A.abrir(v, clave)
        p.set_valor("extension", "objeto"); A.esperar(100)
        campo = "direccion" if clave == "revolucion" else "lados"
        c = next(c for c in p.campos if c.clave == campo)
        A.reg(AR, f"{clave}: con «A objeto» se ve la Dirección (Un lado / Dos lados, como Fusion)", p._visible(c))
        QTest.keyClick(p, Qt.Key_Escape); A.esperar(150)


def proyectar_eje_por_defecto():
    """Fusion: «Project Axis», que en el panel en español dice «Eje de proyecto» y viene marcado
    (captura: analisis/capturas_fusion/SUPERFICIE/Revolucion). Sólido y superficie tienen que arrancar igual."""
    vals = {}
    for clave in ("revolucion", "sup_revolucion"):
        p = A.abrir(v, clave)
        c = next(c for c in p.campos if c.clave == "proyectar_eje")
        vals[clave] = (bool(p.valores.get("proyectar_eje")), c.etiqueta)
        QTest.keyClick(p, Qt.Key_Escape); A.esperar(150)
    A.reg(AR, "Eje de proyecto arranca igual en sólido y superficie", vals["revolucion"][0] == vals["sup_revolucion"][0], str(vals))
    A.reg(AR, "la casilla se llama «Eje de proyecto» en los dos paneles (Fusion: Project Axis)",
          all(x[1] == "Eje de proyecto" for x in vals.values()),
          " ".join(f"{k}: «{x[1]}»" for k, x in vals.items()))
    A.reg(AR, "«Eje de proyecto» arranca marcado, como en el panel de Fusion", vals["revolucion"][0] is True, str(vals))


def barrido_carril():
    """Ruta + Rail guía: Fusion ofrece Escalar, Estirar y Ninguna, y la Extensión (Perpendicular a la ruta / Completa)."""
    n0, antes = A.n_ops(v), A.cuerpos_resumen(v)
    p = A.abrir(v, "barrido")
    p.set_valor("tipo", "ruta_carril"); A.esperar(100)
    c = next(c for c in p.campos if c.clave == "escala_carril")
    A.reg(AR, "Barrido sólido › Escala del perfil ofrece Estirar (Fusion: Scale, Stretch, None)", "estirar" in c.opciones,
          f"ofrece {list(c.opciones)}")
    A.reg(AR, "Barrido sólido › Ruta + Rail guía tiene Extensión (Fusion: Perpendicular to Path / Full Extents)",
          any(c.clave == "extension" for c in p.campos))
    A.elegir(p, "perfiles", per("Cua"))
    A.elegir(p, "ruta", cur("RutaC"))
    A.elegir(p, "carril", cur("CarC"))
    p.set_valor("escala_carril", "ninguna")
    p._t_previa.stop(); p._calcular_previa(); A.esperar(150)
    st = A.estado_panel(p)
    QTest.keyClick(p, Qt.Key_Return); A.esperar(450)
    vol = sum(x[1] for x in nuevos_desde(antes).values())
    A.reg(AR, "Barrido con carril paralelo y escala Ninguna: 800 mm³ (cuadrado 4×4 por 50)", abs(vol - 800) < 1,
          f"volumen {vol:.2f}, pasos {A.n_ops(v) - n0}, mensaje «{st['mensaje']}»")
    A.foto(v, "barrido_carril")
    if A.n_ops(v) > n0:
        A.deshacer(v)


def barrido_teclear():
    """Distancia del barrido tecleada con coma decimal y fuera de rango: 0,5 = la mitad; 0 y 1,5 se avisan."""
    p = A.abrir(v, "barrido")
    A.elegir(p, "perfiles", per("Cua"))
    A.elegir(p, "ruta", cur("RutaC"))
    for texto, valido in (("0,5", True), ("0", False), ("1,5", False), ("", False)):
        teclear(p, "distancia", texto, Qt.Key_Tab)
        p._t_previa.stop(); p._calcular_previa(); A.esperar(150)
        st = A.estado_panel(p)
        A.reg(AR, f"Barrido › Distancia «{texto}»: {'previa' if valido else 'aviso'}",
              st["previa_ok"] if valido else (not st["previa_ok"] and bool(st["mensaje"])), st["mensaje"])
    QTest.keyClick(p, Qt.Key_Escape); A.esperar(150)


def solevacion():
    """Dos cuadros y una punta: tronco 2333,33 mm³ al aceptar; la fila de la punta ofrece Aguda y Punto tangente."""
    n0, antes = A.n_ops(v), A.cuerpos_resumen(v)
    p = A.abrir(v, "solevacion")
    A.elegir(p, "secciones", per("LA"), per("LB"))
    p._t_previa.stop(); p._calcular_previa(); A.esperar(150)
    st = A.estado_panel(p)
    QTest.keyClick(p, Qt.Key_Return); A.esperar(450)
    vol = sum(x[1] for x in nuevos_desde(antes).values())
    A.reg(AR, "Solevación de dos cuadros: 2333,33 mm³ con Enter", abs(vol - 7000 / 3) < 0.5 and A.n_ops(v) == n0 + 1,
          f"volumen {vol:.2f}, mensaje «{st['mensaje']}»")
    if A.n_ops(v) > n0:
        A.deshacer(v)
    p = A.abrir(v, "solevacion")
    from omnicad.ui.comando import hit_desde_ref
    punta = hit_desde_ref({"tipo": "punto", "id": next(o.id for o in v.doc.operaciones if o.nombre == "Punta")},
                          v.doc.estado_final)
    A.elegir(p, "secciones", per("LB"), punta)
    A.esperar(150)
    textos = [[c.itemText(i) for i in range(c.count())] for c in p.findChildren(QComboBox) if c.isVisible()]
    fila_punta = next((t for t in textos if "Aguda" in t), None)
    A.reg(AR, "Solevación: la fila del punto ofrece Aguda y Punto tangente (Fusion: Sharp / Point Tangent)",
          fila_punta is not None and any("tangente" in x.lower() for x in fila_punta), f"opciones {fila_punta}")
    A.foto(v, "solevacion_punta")
    QTest.keyClick(p, Qt.Key_Escape); A.esperar(150)


def ventana_chica():
    """El panel más largo: Barrido Ruta + Rail guía con cortar (campos de carril y objetivos visibles)."""
    p = A.abrir(v, "barrido")
    for k, val in (("tipo", "ruta_carril"), ("operacion", "cortar")):
        p.set_valor(k, val)
    A.esperar(150)
    for ancho, alto in ((1024, 640), (800, 520)):
        v.resize(ancho, alto); A.esperar(300)
        b = p.boton_ok
        esq = b.mapTo(v, QPoint(b.width() - 1, b.height() - 1))
        dentro = b.isVisible() and not b.visibleRegion().isEmpty() and v.rect().contains(esq)
        A.reg(AR, f"ventana {ancho}x{alto}: Aceptar se ve con el Barrido con carril", dentro,
              f"esquina {esq.x()},{esq.y()} en {v.width()}x{v.height()}")
        A.foto(v, f"barrido_{ancho}x{alto}")
    v.resize(1900, 1000); A.esperar(200)
    QTest.keyClick(p, Qt.Key_Escape); A.esperar(150)


for nombre, f in (("cinta", cinta), ("revolución dos lados negativo", revolucion_dos_lados_negativo),
                  ("revolución a objeto dos lados", revolucion_objeto_dos_lados),
                  ("proyectar eje por defecto", proyectar_eje_por_defecto), ("barrido con carril", barrido_carril),
                  ("barrido teclear", barrido_teclear), ("solevación", solevacion), ("ventana chica", ventana_chica)):
    A.correr(f"{AR} · {nombre}", f)
A.reg(AR, "ninguna excepción escapó de un slot de Qt", not A.ERRORES, str(A.ERRORES[-1:])[-300:])

A.guardar_registro("revolucion_barrido_solevacion")
fallas = [r for r in A.REGISTRO if not r["ok"]]
print(f"\n=== {len(A.REGISTRO)} comprobaciones, {len(fallas)} con ✗ ===")
v.close()
sys.exit(0)

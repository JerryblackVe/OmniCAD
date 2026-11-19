# -*- coding: utf-8 -*-
"""BOCETO · los 5 tipos del diálogo PROYECTAR como los usa una persona (PRUEBA-PROY, E7): Proyectar, Intersecar,
Incluir geometría 3D, Perfil giratorio y Curva isoparamétrica. Caja 40×30×20 y un boceto sobre un plano a z=10 (así
Intersecar corta de verdad). Por tipo: ítem real del menú, elegir en el visor (cara, arista, cuerpo), Filtro, Vínculo
on/off, Aceptar / Enter / Cancelar / Esc, deshacer y rehacer, y selecciones raras. Contra docs/fusion_docs (Project,
Intersect, Include 3D, Spun Profile, Isoparametric). Eventos simulados al Lienzo, nunca el cursor real."""
import sys

import arnes as A
import numpy as np
from omnicad import api
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QCheckBox, QComboBox, QDoubleSpinBox, QLabel, QSpinBox

AR = "BOCETO·PROY5"
s = api.Sesion()


def L(nombre, **a):
    r = api.llamar(s, nombre, a)
    assert r["ok"], (nombre, a, r)
    return r["result"]


L("create_box", length=40, width=30, height=20, name="Caja")
plano = L("create_construction_plane", plane="XY", offset=10, name="P10")["plane"]["id"]
L("create_sketch", plane=plano, name="Trabajo")
L("draw_line", sketch="Trabajo", start_x=-5, start_y=-5, end_x=5, end_y=-5)
TRABAJO = s.paso("Trabajo").id
app, v = A.iniciar(s.doc, 1280, 720)
A.esperar(400)
MENSAJES = []
TOP = {"cara": (5.0, 5.0, 20.0), "arista": (20.0, 0.0, 20.0)}     # vista de arriba: tapa y una arista de la tapa
LAT = (5.0, -15.0, 10.0)                                            # vista de frente: cara lateral, cruza el plano z=10


def entrar(vista="arriba"):
    v.editar_operacion(TRABAJO)
    A.esperar(500)
    v.visor.encuadrar()
    v.visor.vista(vista)
    A.esperar(300)
    lz = v.modo_boceto.lienzo
    lz.mensaje.connect(MENSAJES.append)
    return lz


def abrir():
    return v.modo_boceto.lienzo if v.modo_boceto.activo else entrar()


def clic(lz, punto):
    QTest.mouseClick(lz, Qt.LeftButton, Qt.NoModifier, lz.mapFromGlobal(v.visor.mapToGlobal(
        v.visor.proyectar(np.array(punto, float)).toPoint())))
    A.esperar(150)


def tecla(w, k, mod=Qt.NoModifier):
    v.activateWindow()                        # sin gestor de ventanas (xvfb) los atajos no llegan a una ventana sin activar
    w.setFocus()
    A.esperar(150)                            # la primera tecla tras activar la ventana se pierde si no se espera
    QTest.keyClick(w, k, mod)
    A.esperar(300)


def menu(clave, limpio=True):
    """El ítem del menú, como lo aprieta la persona. `limpio`: opciones de la tarjeta en su valor de fábrica (cada sección
    parte igual; la persistencia entre herramientas se prueba aparte)."""
    if limpio:
        o = v.modo_boceto.lienzo.opciones
        o.update(filtro_proyectar="entidades", vinculo_proyeccion=True, eje_giro="Z", iso_direccion="u", iso_tipo="unica")
    v.modo_boceto.acciones[clave].trigger()
    A.esperar(300)
    return v.modo_boceto.tarjeta


def planas(lz):
    return [c for c in lz.b.curvas.values() if c.id > 0]


def n3d(lz):
    from omnicad.restricciones import boceto3d as b3
    return len(b3.datos(lz.b)["curvas"])


def casilla(t, texto):
    """La casilla de la fila cuya etiqueta contiene `texto` (las casillas de la tarjeta no llevan texto propio)."""
    f = t.form_contexto
    for i in range(f.rowCount()):
        et, ch = f.itemAt(i, f.ItemRole.LabelRole), f.itemAt(i, f.ItemRole.FieldRole)
        if et and ch and texto in et.widget().text() and isinstance(ch.widget(), QCheckBox):
            return ch.widget()
    return None


def combo(t, dato):
    return next((c for c in t.contexto.findChildren(QComboBox) if c.findData(dato) >= 0), None)


def textos(t):
    return [w.text() for w in t.findChildren(QLabel) if w.text()]


def poner(c, dato):
    c.setCurrentIndex(c.findData(dato))
    A.esperar(200)


def paso(nombre, f):
    """Cada sección en su propia red: una excepción es un hallazgo, no corta la prueba."""
    try:
        f()
    except Exception as e:                                           # noqa: BLE001
        A.reg(AR, f"{nombre}: sin excepción", False, f"{type(e).__name__}: {e}")


def inter_lateral():
    lz = entrar("frente")
    t = menu("sk_intersecar")
    A.reg(AR, "Intersecar abre su tarjeta con Aceptar apagado", t.isVisible() and t.titulo.text().upper().startswith("INTERSEC")
          and not t.boton_ok.isEnabled(), t.titulo.text())
    A.foto(v, "proy5_inter_01_vacia")
    n0, h0 = len(planas(lz)), len(lz.historial)
    clic(lz, LAT)
    A.reg(AR, "Intersecar: elegir una cara lateral muestra la previa y habilita Aceptar", t.boton_ok.isEnabled(), t.resultado.text())
    A.foto(v, "proy5_inter_02_cara_lateral")
    tecla(lz, Qt.Key_Return)
    nuevas = len(planas(lz)) - n0
    A.reg(AR, "Intersecar: Enter deja la línea donde la cara corta el plano, en un solo paso", nuevas >= 1 and len(lz.historial) == h0 + 1,
          f"{nuevas} curvas, historial {len(lz.historial) - h0}")
    tecla(lz, Qt.Key_Z, Qt.ControlModifier)
    A.reg(AR, "Intersecar: Ctrl+Z las saca", len(planas(lz)) == n0, len(planas(lz)))
    tecla(lz, Qt.Key_Y, Qt.ControlModifier)
    A.reg(AR, "Intersecar: Ctrl+Y las trae de nuevo", len(planas(lz)) == n0 + nuevas, len(planas(lz)))
    tecla(lz, Qt.Key_Z, Qt.ControlModifier)
    # una cara que NO cruza el plano (la tapa, z=20) no puede dar curvas
    lz = v.modo_boceto.lienzo
    v.visor.vista("arriba")
    A.esperar(250)
    t = menu("sk_intersecar")
    clic(lz, TOP["cara"])
    A.reg(AR, "Intersecar: una cara que no cruza el plano no acepta y lo dice", not t.boton_ok.isEnabled() and any("no deja nada" in x for x in textos(t)),
          textos(t)[-1:])
    A.foto(v, "proy5_inter_03_no_cruza")
    tecla(lz, Qt.Key_Escape)
    A.reg(AR, "Intersecar: Esc cierra la tarjeta y el boceto sigue", not t.isVisible() and v.modo_boceto.activo)
    # Filtro: Cuerpos
    t = menu("sk_intersecar")
    f = combo(t, "cuerpos")
    A.reg(AR, "Intersecar: tiene el Filtro (Entidades / Cuerpos)", f is not None)
    if f is not None:
        poner(f, "cuerpos")
        clic(lz, TOP["cara"])
        A.reg(AR, "Intersecar con Filtro Cuerpos: elegir la caja da el contorno completo", t.boton_ok.isEnabled(), t.resultado.text())
        A.foto(v, "proy5_inter_04_cuerpo")
        n1 = len(planas(lz))
        tecla(lz, Qt.Key_Return)
        A.reg(AR, "Intersecar cuerpo: 4 líneas (el rectángulo 40×30)", len(planas(lz)) - n1 >= 4, len(planas(lz)) - n1)
        # Vínculo apagado
        tecla(lz, Qt.Key_Z, Qt.ControlModifier)
        t = menu("sk_intersecar")
    k = casilla(t, "Vínculo")
    A.reg(AR, "Intersecar: tiene la casilla Vínculo de proyección, tildada por defecto", k is not None and k.isChecked(), k and k.isChecked())
    if k is not None:
        k.click()
        A.esperar(150)
        f = combo(t, "cuerpos")
        poner(f, "cuerpos")
        clic(lz, TOP["cara"])
        npr = len(lz.b.proyecciones)
        tecla(lz, Qt.Key_Return)
        A.reg(AR, "Intersecar sin Vínculo: queda geometría sin vínculo", len(lz.b.proyecciones) == npr and len(planas(lz)) > 1,
              f"{len(lz.b.proyecciones)} vínculos, {len(planas(lz))} curvas")
        tecla(lz, Qt.Key_Z, Qt.ControlModifier)
    # Cancelar con el botón
    t = menu("sk_intersecar")
    clic(lz, TOP["cara"])
    n2 = len(planas(lz))
    t.boton_cancelar.click() if hasattr(t, "boton_cancelar") else tecla(lz, Qt.Key_Escape)
    A.esperar(150)
    A.reg(AR, "Intersecar: Cancelar descarta sin tocar el boceto", len(planas(lz)) == n2 and not t.isVisible(), len(planas(lz)))
    tecla(lz, Qt.Key_Escape)


def proyectar_raros():
    lz = abrir()
    v.visor.vista("arriba")
    A.esperar(250)
    t = menu("sk_proyectar")
    f = combo(t, "cuerpos")
    A.reg(AR, "Proyectar: Filtro Entidades / Cuerpos presente", f is not None)
    n0 = len(planas(lz))
    clic(lz, TOP["cara"])
    A.reg(AR, "Proyectar: cara elegida habilita Aceptar", t.boton_ok.isEnabled(), t.resultado.text())
    k = casilla(t, "Vínculo")
    if k is not None:
        k.click()
        A.esperar(150)
    npr = len(lz.b.proyecciones)
    tecla(lz, Qt.Key_Return)
    A.reg(AR, "Proyectar sin Vínculo: curvas planas sin vínculo", len(planas(lz)) > n0 and len(lz.b.proyecciones) == npr,
          f"{len(planas(lz)) - n0} curvas, {len(lz.b.proyecciones) - npr} vínculos")
    A.foto(v, "proy5_proy_01_sin_vinculo")
    tecla(lz, Qt.Key_Z, Qt.ControlModifier)
    # Filtro Cuerpos
    t = menu("sk_proyectar")
    f = combo(t, "cuerpos")
    if f is not None:
        poner(f, "cuerpos")
        clic(lz, TOP["cara"])          # una cara con el filtro de cuerpos: no es un cuerpo
        A.reg(AR, "Proyectar con Filtro Cuerpos: un clic en la cara elige el cuerpo entero", t.boton_ok.isEnabled(), t.resultado.text())
        A.foto(v, "proy5_proy_02_filtro_cuerpos")
    tecla(lz, Qt.Key_Escape)
    # clic en el vacío y doble Aceptar
    t = menu("sk_proyectar")
    clic(lz, (200.0, 200.0, 0.0))
    A.reg(AR, "Proyectar: clic en el vacío no elige nada ni rompe", not t.boton_ok.isEnabled(), t.resultado.text())
    tecla(lz, Qt.Key_Return)
    A.reg(AR, "Proyectar: Enter sin selección no deja un paso vacío ni sale", lz.herramienta == "proyectar", lz.herramienta)
    tecla(lz, Qt.Key_Escape)


def incluir3d():
    lz = abrir()
    t = menu("sk_incluir_3d")
    A.reg(AR, "Incluir 3D abre su herramienta", lz.herramienta == "incluir_3d", lz.herramienta)
    A.reg(AR, "Incluir 3D: no tiene Filtro ni Vínculo (solo curvas y puntos 3D)", casilla(t, "Vínculo") is None, "")
    n3, h0 = n3d(lz), len(lz.historial)
    m0 = len(MENSAJES)
    clic(lz, TOP["cara"])                  # Fusion (Include 3D Geometry): «You can select faces, edges, and points»
    A.reg(AR, "Incluir 3D: un clic en una cara la incluye (Fusion admite caras, aristas y puntos)", n3d(lz) > n3,
          f"{n3d(lz) - n3} curvas, mensajes {MENSAJES[m0:]}")
    A.foto(v, "proy5_inc_00_cara")
    n3, h0 = n3d(lz), len(lz.historial)
    clic(lz, TOP["arista"])
    A.reg(AR, "Incluir 3D: la arista queda como curva 3D con un paso de deshacer", n3d(lz) == n3 + 1 and len(lz.historial) == h0 + 1,
          f"{n3d(lz) - n3} curvas, {len(lz.historial) - h0} pasos")
    A.foto(v, "proy5_inc_01_arista")
    clic(lz, TOP["arista"])
    A.reg(AR, "Incluir 3D: la misma arista dos veces no se duplica", n3d(lz) == n3 + 1, n3d(lz) - n3)
    tecla(lz, Qt.Key_Z, Qt.ControlModifier)
    A.reg(AR, "Incluir 3D: Ctrl+Z la saca", n3d(lz) == n3, n3d(lz) - n3)
    tecla(lz, Qt.Key_Escape)
    A.reg(AR, "Incluir 3D: Esc sale de la herramienta", lz.herramienta == "seleccionar" and v.modo_boceto.activo, lz.herramienta)


def giratorio():
    lz = abrir()
    v.visor.vista("arriba")
    A.esperar(250)
    t = menu("sk_perfil_giratorio")
    A.reg(AR, "Perfil giratorio abre su tarjeta", t.isVisible() and lz.herramienta == "perfil_giratorio", lz.herramienta)
    A.foto(v, "proy5_giro_01_tarjeta")
    eje = combo(t, "X")
    A.reg(AR, "Perfil giratorio: tiene Eje (X, Y, Z, arista recta)", eje is not None and eje.findData("arista") >= 0)
    for etiqueta in ("Vínculo", "Invertir", "Solo contorno exterior", "Proyectar eje"):
        A.reg(AR, f"Perfil giratorio: casilla «{etiqueta}»", casilla(t, etiqueta) is not None)
    tol = next((d for d in t.contexto.findChildren(QDoubleSpinBox)), None)
    A.reg(AR, "Perfil giratorio: tiene Tolerancia numérica", tol is not None)
    n0, h0 = len(planas(lz)), len(lz.historial)
    m0 = len(MENSAJES)
    if eje is not None:
        poner(eje, "Z")
    clic(lz, TOP["cara"])         # eje Z = perpendicular al boceto: no hay perfil y tiene que decirlo
    A.reg(AR, "Perfil giratorio con eje perpendicular: no crea nada y lo dice en la barra", len(planas(lz)) == n0
          and any("perpendicular" in m for m in MENSAJES[m0:]), MENSAJES[m0:][-1:])
    tecla(lz, Qt.Key_Escape)
    t = menu("sk_perfil_giratorio")
    poner(combo(t, "X"), "X")
    clic(lz, TOP["cara"])
    A.reg(AR, "Perfil giratorio eje X: elegir una cara deja el perfil (3 curvas) en un solo paso y con vínculo",
          len(planas(lz)) - n0 == 3 and len(lz.historial) == h0 + 1 and len(lz.b.proyecciones) == 1,
          f"{len(planas(lz)) - n0} curvas, {len(lz.historial) - h0} pasos, {len(lz.b.proyecciones)} vínculos")
    A.foto(v, "proy5_giro_02_cara_eje_x")
    h1 = len(lz.historial)
    tecla(lz, Qt.Key_Return)
    A.reg(AR, "Perfil giratorio: Enter después de elegir no suma un paso vacío", len(lz.historial) == h1, len(lz.historial) - h1)
    tecla(lz, Qt.Key_Z, Qt.ControlModifier)
    A.reg(AR, "Perfil giratorio: Ctrl+Z lo saca", len(planas(lz)) == n0, len(planas(lz)))
    # valores raros: tolerancia mínima y máxima, eje arista sin arista
    t = menu("sk_perfil_giratorio")
    if tol is not None:
        tol = next(d for d in t.contexto.findChildren(QDoubleSpinBox))
        for valor in (tol.minimum(), tol.maximum(), 0.0, -3.0):
            tol.setValue(valor)
            A.esperar(120)
            A.reg(AR, f"Perfil giratorio: tolerancia {valor} queda dentro de [{tol.minimum()}, {tol.maximum()}]",
                  tol.minimum() <= tol.value() <= tol.maximum(), tol.value())
        tol.setValue(0.1)
    eje = combo(t, "arista")
    if eje is not None:
        poner(eje, "arista")
        clic(lz, TOP["cara"])         # sin arista recta de eje, elegir una cara
        A.reg(AR, "Perfil giratorio con eje Arista: una cara como primer clic no la toma de eje y el aviso pide una arista RECTA",
              len(planas(lz)) == n0 and "recta" in MENSAJES[-1], MENSAJES[-1:])
        A.foto(v, "proy5_giro_03_eje_arista_con_cara")
        clic(lz, TOP["arista"])
        A.foto(v, "proy5_giro_04_eje_arista")
    tecla(lz, Qt.Key_Escape)
    A.reg(AR, "Perfil giratorio: Esc cierra la tarjeta y el boceto sigue", v.modo_boceto.activo and lz.herramienta == "seleccionar")
    # Proyectar eje
    n1 = len(planas(lz))
    menu("sk_proyectar_eje")
    A.esperar(200)
    A.foto(v, "proy5_giro_05_proyectar_eje")
    A.reg(AR, "Proyectar eje: no deja el boceto en un estado raro", v.modo_boceto.activo, lz.herramienta)
    tecla(lz, Qt.Key_Escape)
    A.reg(AR, "Proyectar eje: no creó curvas sin Aceptar", len(planas(lz)) == n1, len(planas(lz)) - n1)


def iso():
    lz = abrir()
    v.visor.vista("arriba")
    A.esperar(250)
    t = menu("sk_isoparametrica")
    A.reg(AR, "Isoparamétrica abre su herramienta con Dirección y Distribución",
          lz.herramienta == "isoparametrica" and combo(t, "u") is not None and combo(t, "unica") is not None, lz.herramienta)
    A.foto(v, "proy5_iso_01_tarjeta")
    n3, h0 = n3d(lz), len(lz.historial)
    clic(lz, TOP["cara"])
    A.reg(AR, "Isoparamétrica: un clic en la cara crea curvas 3D (una por defecto) en un solo paso",
          n3d(lz) > n3 and len(lz.historial) == h0 + 1, f"{n3d(lz) - n3} curvas, {len(lz.historial) - h0} pasos")
    A.foto(v, "proy5_iso_02_una")
    tecla(lz, Qt.Key_Z, Qt.ControlModifier)
    A.reg(AR, "Isoparamétrica: Ctrl+Z las saca", n3d(lz) == n3, n3d(lz) - n3)
    t = menu("sk_isoparametrica")
    poner(combo(t, "both"), "both")
    clic(lz, TOP["cara"])
    A.reg(AR, "Isoparamétrica Ambas: crea las dos curvas (U y V)", n3d(lz) - n3 == 2, n3d(lz) - n3)
    tecla(lz, Qt.Key_Z, Qt.ControlModifier)
    poner(combo(t, "cantidad"), "cantidad")
    ent = next((e for e in t.contexto.findChildren(QSpinBox)), None)
    A.reg(AR, "Isoparamétrica: Cantidad es un campo entero", ent is not None)
    if ent is not None:
        for q in (1, 5, ent.maximum(), 0, -2):
            ent.setValue(q)
            A.esperar(100)
            A.reg(AR, f"Isoparamétrica: cantidad {q} queda en [{ent.minimum()}, {ent.maximum()}]", ent.minimum() <= ent.value() <= ent.maximum(), ent.value())
        ent.setValue(5)
        clic(lz, TOP["cara"])
        A.reg(AR, "Isoparamétrica: 5 por cantidad y dirección Ambas = 10 curvas", n3d(lz) - n3 == 10, n3d(lz) - n3)
        A.foto(v, "proy5_iso_03_cantidad_5")
        tecla(lz, Qt.Key_Z, Qt.ControlModifier)
    poner(combo(t, "distancia"), "distancia")
    clic(lz, TOP["cara"])
    A.reg(AR, "Isoparamétrica por distancia: crea curvas sin romper", n3d(lz) > n3, n3d(lz) - n3)
    A.foto(v, "proy5_iso_04_distancia")
    tecla(lz, Qt.Key_Z, Qt.ControlModifier)
    clic(lz, (200.0, 200.0, 0.0))
    A.reg(AR, "Isoparamétrica: clic en el vacío no crea nada", n3d(lz) == n3, n3d(lz) - n3)
    clic(lz, TOP["arista"])
    A.reg(AR, "Isoparamétrica: clic en una arista (no cara) no rompe", True, MENSAJES[-1:])
    tecla(lz, Qt.Key_Escape)
    A.reg(AR, "Isoparamétrica: Esc sale de la herramienta", lz.herramienta == "seleccionar" and v.modo_boceto.activo, lz.herramienta)


# Cada sección en su proceso (`proyectar_cinco.py intersecar`): así el boceto de una no ensucia a la otra. Sin argumento, todas.
SECCIONES = {"intersecar": inter_lateral, "proyectar": proyectar_raros, "incluir": incluir3d, "giratorio": giratorio, "iso": iso}
for nombre in (sys.argv[1:] or SECCIONES):
    if nombre not in SECCIONES:
        sys.exit(f"sección desconocida: {nombre}; hay {', '.join(SECCIONES)}")
    paso(nombre, SECCIONES[nombre])
A.reg(AR, "ninguna excepción en un slot de Qt", not A.ERRORES, A.ERRORES[:1])
A.guardar_registro("proyectar_cinco")
fallas = [r for r in A.REGISTRO if not r["ok"]]
print(f"\n=== {len(A.REGISTRO)} comprobaciones, {len(fallas)} con ✗ ===", flush=True)
v.doc.modificado = False
v.close()
sys.exit(0)

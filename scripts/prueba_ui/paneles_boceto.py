# -*- coding: utf-8 -*-
"""Paneles del boceto (UI-5 de `docs/seguimiento/mejoras.md`: Simetría, Patrón circular, Escala y Carácter) con lo mismo que
los paneles de comando, como los usa una persona, en la ventana real y a 1280x720, 1024x640 y 800x520:
  - cada herramienta abre su panel con su título, ancho de la tabla común y la instrucción con su símbolo (➜);
  - un valor mal escrito muestra el error con su símbolo (✖) y deshabilita Aceptar;
  - la cabecera se arrastra (press, varios movimientos, release): el panel queda dentro de la vista con Aceptar y Cancelar
    a la vista, y el doble clic en la cabecera lo devuelve a su lugar;
  - la ✕ cancela la herramienta; Carácter (texto) se mueve y se pliega con su botón.
    paneles_boceto.py   → capturas en `evidencias/ui_paneles_2026-10-31/boceto_paneles/`. Eventos simulados al widget."""
import math

import arnes as A
from omnicad import api
from PySide6.QtCore import QEvent, QPoint, QPointF, QRect, Qt
from PySide6.QtGui import QMouseEvent, QWheelEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QPushButton, QToolButton

from omnicad.ui.formulario import ANCHOS
from omnicad.ui.superposiciones import CabeceraMovible

AR = "PANELES·boceto"
CARPETA = A.SALIDA.parent / "ui_paneles_2026-10-31" / "boceto_paneles"
CARPETA.mkdir(parents=True, exist_ok=True)
s = api.Sesion()


def L(nombre, **a):
    r = api.llamar(s, nombre, a)
    assert r["ok"], (nombre, a, r)
    return r["result"]


L("create_sketch", name="S", plane="XY")
circ = L("draw_circle", sketch="S", center_x=30, center_y=10, radius=6)["entities"][0]["id"]
L("draw_line", sketch="S", start_x=-40, start_y=-20, end_x=-40, end_y=40)
app, v = A.iniciar(s.doc, 1280, 720)
A.esperar(300)
v.editar_operacion(s.paso("S").id)
A.esperar(500)
modo = v.modo_boceto
lz = modo.lienzo
PANELES = {"simetria": (modo.simetria, "sk_simetria", "SIMETRÍA", "simple"),
           "patron": (modo.patron, "sk_patron_circular", "PATRÓN CIRCULAR", "normal"),
           "escala": (modo.transformar, "sk_escala", "ESCALA", "normal")}


def encuadrar():
    lz.visor.objetivo = lz.plano.a_3d(0, 10)
    lz.visor.distancia = 150 / 2 / math.sin(math.radians(lz.visor.fov) / 2) * 1.3
    lz.visor.update()
    lz.update()
    A.esperar(250)


def evento(w, tipo, global_):
    QApplication.sendEvent(w, QMouseEvent(tipo, QPointF(w.mapFromGlobal(global_)), QPointF(global_), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier))


def arrastrar(panel, dx, dy, pasos=5):
    cab = panel.findChild(CabeceraMovible)
    ini = cab.mapToGlobal(QPoint(30, 8))
    evento(cab, QEvent.MouseButtonPress, ini)
    for i in range(1, pasos + 1):
        evento(cab, QEvent.MouseMove, ini + QPoint(dx * i // pasos, dy * i // pasos))
    evento(cab, QEvent.MouseButtonRelease, ini + QPoint(dx, dy))
    A.esperar(80)


def entra(p):
    return v.area.rect().adjusted(0, 0, 1, 1).contains(p.geometry())


def rueda(w, pasos):
    """Gira la rueda del ratón sobre `w` (un paso = una muesca; negativo = hacia abajo): evento simulado, sin tocar el cursor real."""
    centro = QPointF(w.width() / 2, w.height() / 2)
    for _ in range(abs(pasos)):                  # Qt corta cada evento a una página: se gira muesca por muesca, como la mano
        QApplication.sendEvent(w, QWheelEvent(centro, QPointF(w.mapToGlobal(centro.toPoint())), QPoint(0, 0),
                                              QPoint(0, 120 if pasos > 0 else -120), Qt.NoButton, Qt.NoModifier, Qt.NoScrollPhase, False))
    A.esperar(60)


def cabecera_entra(p):
    """Carácter mide ~540 px y en una ventana baja no cabe entera (UI-8): al menos su cabecera tiene que estar a la vista."""
    cab = p.findChild(CabeceraMovible)
    return v.area.rect().adjusted(0, 0, 1, 1).contains(QRect(cab.mapTo(v.area, QPoint(0, 0)), cab.size()))


def botones_a_la_vista(p):
    marco = v.area.rect()
    cancelar = next(b for b in p.findChildren(QPushButton) if b.text() == "Cancelar")
    barra = v.area.barra.geometry() if v.area.barra is not None and v.area.barra.isVisible() else None
    return all(marco.contains(b.mapTo(v.area, b.rect().topLeft())) and marco.contains(b.mapTo(v.area, b.rect().bottomRight()))
               and (barra is None or not barra.intersects(p.geometry())) for b in (p.boton_ok, cancelar))


def teclear(campo, texto):
    campo.setFocus()
    campo.selectAll()
    QTest.keyClicks(campo, texto)
    A.esperar(120)


def panel_de(tag, clave):
    panel, accion, titulo, ancho = PANELES[clave]
    modo.herramienta("seleccionar")
    A.esperar(100)
    modo.acciones[accion].trigger()
    A.esperar(250)
    A.reg(AR, f"{tag} · {clave}: la herramienta abre su panel «{titulo}»",
          panel.isVisible() and panel.findChild(type(panel.guia), "titulo_comando").text() == titulo, f"visible={panel.isVisible()}")
    A.reg(AR, f"{tag} · {clave}: el ancho es el de la tabla común ({ANCHOS[ancho]} px)", panel.width() == ANCHOS[ancho], f"{panel.width()}")
    A.reg(AR, f"{tag} · {clave}: la instrucción lleva su símbolo ➜ y el error está oculto",
          panel.guia.isVisible() and panel.icono_guia.text() == "➜" and panel.mensaje.isHidden(), panel.guia.text())
    return panel


def movimiento(tag, clave):
    panel = panel_de(tag, clave)
    base = panel.pos()
    panel.grab().save(str(CARPETA / f"{clave}_{tag}.png"))
    arrastrar(panel, -260, 90)
    A.reg(AR, f"{tag} · {clave}: arrastrar la cabecera lo mueve y no cambia su tamaño", panel.pos() != base and entra(panel),
          f"{base.x()},{base.y()} → {panel.x()},{panel.y()}")
    A.reg(AR, f"{tag} · {clave}: Aceptar y Cancelar siguen a la vista", botones_a_la_vista(panel), "")
    v.grab().save(str(CARPETA / f"ventana_{clave}_movido_{tag}.png"))
    arrastrar(panel, -9000, 9000)
    A.reg(AR, f"{tag} · {clave}: más allá del borde queda dentro de la vista y con los botones", entra(panel) and botones_a_la_vista(panel),
          f"{panel.x()},{panel.y()} {panel.width()}x{panel.height()}")
    arrastrar(panel, 9000, -9000)
    A.reg(AR, f"{tag} · {clave}: y hacia el otro extremo", entra(panel) and botones_a_la_vista(panel), f"{panel.x()},{panel.y()}")
    cab = panel.findChild(CabeceraMovible)
    evento(cab, QEvent.MouseButtonDblClick, cab.mapToGlobal(QPoint(30, 8)))
    A.esperar(100)
    A.reg(AR, f"{tag} · {clave}: el doble clic en la cabecera lo devuelve a su lugar", panel.pos() == base and panel.posicion_usuario is None,
          f"{base} vs {panel.pos()}")
    cruz = next(b for b in panel.findChildren(QToolButton) if b.text() == "✕")
    A.reg(AR, f"{tag} · {clave}: la ✕ dice «Cancelar (Esc)» y no toma el foco", cruz.toolTip() == "Cancelar (Esc)" and cruz.focusPolicy() == Qt.NoFocus, "")
    cruz.click()
    A.esperar(200)
    A.reg(AR, f"{tag} · {clave}: la ✕ cancela la herramienta y el panel se va", not panel.isVisible() and lz.herramienta == "seleccionar",
          f"herr={lz.herramienta} visible={panel.isVisible()}")


def error_tipado(tag):
    panel = panel_de(tag, "escala")
    QTest.mouseClick(lz, Qt.LeftButton, Qt.NoModifier, lz.a_px(30, 16).toPoint())      # el borde del círculo
    A.esperar(150)
    teclear(panel.campos["base_x"], "0")
    teclear(panel.campos["base_y"], "0")
    teclear(panel.campos["factor"], "abc")
    A.reg(AR, f"{tag} · Escala: un factor mal escrito muestra el error con ✖ y Aceptar queda deshabilitado",
          panel.mensaje.isVisible() and panel.icono_mensaje.text() == "✖" and panel.mensaje.property("tipo") == "invalido"
          and not panel.boton_ok.isEnabled(), f"«{panel.mensaje.text()}»")
    panel.grab().save(str(CARPETA / f"escala_error_{tag}.png"))
    teclear(panel.campos["factor"], "2")
    A.reg(AR, f"{tag} · Escala: corregir el valor saca el error y deja aceptar", panel.mensaje.isHidden() and panel.boton_ok.isEnabled(),
          f"«{panel.mensaje.text()}»")
    modo.herramienta("seleccionar")
    lz.seleccion = []
    A.esperar(100)


def caracter(tag):
    modo.herramienta("seleccionar")
    modo.acciones["sk_texto"].trigger()
    A.esperar(300)
    p = modo.caracter
    A.reg(AR, f"{tag} · Carácter: la herramienta Texto muestra su panel con la cabecera común y sin ✕",
          p.isVisible() and p.findChild(CabeceraMovible) is not None and not [b for b in p.findChildren(QToolButton) if b.text() == "✕"], "")
    base, alto0, ancho0 = p.pos(), p.height(), p.width()
    p.grab().save(str(CARPETA / f"caracter_{tag}.png"))
    barra = p.desplazador.verticalScrollBar()
    natural = p.cuerpo.sizeHint().height() + p._cabecera.sizeHint().height()
    A.reg(AR, f"{tag} · Carácter: entra en el lienzo ({p.height()} de {v.area.height()} px) y, si no cabe, el cuerpo tiene barra",
          entra(p) and (barra.maximum() > 0) == (natural > v.area.height() - 16), f"natural {natural} · barra {barra.maximum()}")
    for seccion in ("Decoraciones", "Transformaciones", "Avanzado"):        # como una persona: abre cada sección y baja con la rueda
        boton = next(b for b in p.findChildren(QToolButton) if b.text().endswith(seccion))
        if boton.text().startswith("▸"):
            QTest.mouseClick(boton, Qt.LeftButton)
            A.esperar(120)
    rueda(p.desplazador.viewport(), -40)
    vista = p.desplazador.viewport()
    pie = p.sin_division.mapTo(vista, QPoint(0, p.sin_division.height())).y()
    A.reg(AR, f"{tag} · Carácter: con todas las secciones abiertas, la rueda llega hasta «Sin división»",
          entra(p) and barra.value() == barra.maximum() and 0 < pie <= vista.height(), f"alto {p.height()} · pie {pie}/{vista.height()}")
    p.grab().save(str(CARPETA / f"caracter_abierto_{tag}.png"))
    for boton in [b for b in p.findChildren(QToolButton) if b.text().startswith("▾") and not b.text().endswith("Espaciado")
                  and not b.text().endswith("Alineación y curva")]:
        QTest.mouseClick(boton, Qt.LeftButton)                              # vuelve a dejar plegadas las tres que se abrieron
    A.esperar(120)
    alto0 = p.height()
    arrastrar(p, -200, 60)
    A.reg(AR, f"{tag} · Carácter: arrastrar la cabecera lo mueve y queda dentro de la vista", p.pos() != base and cabecera_entra(p), f"{base} → {p.pos()}")
    arrastrar(p, -9000, 9000)
    A.reg(AR, f"{tag} · Carácter: más allá del borde su cabecera queda a la vista", cabecera_entra(p) and entra(p), f"{p.pos()} {p.width()}x{p.height()}")
    v.grab().save(str(CARPETA / f"ventana_caracter_movido_{tag}.png"))
    QTest.mouseClick(p.b_plegar, Qt.LeftButton)
    A.esperar(150)
    A.reg(AR, f"{tag} · Carácter: el botón pliega el panel y sigue siendo movible", p.height() < alto0 and not p.cuerpo.isVisible(), f"{alto0} → {p.height()}")
    QTest.mouseClick(p.b_plegar, Qt.LeftButton)
    A.esperar(150)
    cab = p.findChild(CabeceraMovible)
    evento(cab, QEvent.MouseButtonDblClick, cab.mapToGlobal(QPoint(30, 8)))
    A.esperar(100)
    A.reg(AR, f"{tag} · Carácter: desplegar y doble clic en la cabecera lo devuelve a su lugar", p.pos() == base and p.cuerpo.isVisible() and p.width() == ancho0, f"{base} vs {p.pos()} · {ancho0} vs {p.width()}")
    modo.herramienta("seleccionar")


def todo():
    for ancho, alto in ((1280, 720), (1024, 640), (800, 520)):
        v.resize(ancho, alto)
        A.esperar(250)
        encuadrar()
        tag = f"{ancho}x{alto}"
        for clave in PANELES:
            movimiento(tag, clave)
        error_tipado(tag)
        caracter(tag)


A.correr(AR, todo)
A.reg(AR, "no se escapó ninguna excepción dentro de un slot de Qt", not A.ERRORES, "; ".join(A.ERRORES)[:300])
A.guardar_registro("paneles_boceto")
fallas = sum(1 for r in A.REGISTRO if not r["ok"])
print(f"=== {len(A.REGISTRO)} comprobaciones, {fallas} con ✗", flush=True)

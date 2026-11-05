# -*- coding: utf-8 -*-
"""Recorrido humano de vectores: cinta, visor principal, campos, perfiles CAD, archivos y texto editable."""
import math

import arnes as A
import numpy as np
from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QFileDialog, QToolButton

from omnicad.nucleo import geometria as geo
from omnicad.nucleo.perfiles import sin_huecos
from omnicad.restricciones import objetos as ob
from omnicad.timeline.documento import Documento

AR = "MANIPULACIÓN VECTORIAL"
app, v = A.iniciar(Documento(), 1440, 900)


def accion(clave):
    """Clic real en el botón o en la acción de su menú de cinta."""
    a = v.acciones[clave]
    pulsadas = []
    contar = lambda _v=False: pulsadas.append(True)
    a.triggered.connect(contar)
    botones = [b for b in v.cinta.findChildren(QToolButton) if b.isVisible() and b.defaultAction() is a]
    if botones:
        QTest.mouseClick(botones[0], Qt.LeftButton)
    else:
        b, m = next((b, m) for b in v.cinta.findChildren(QToolButton) if b.isVisible() and b.menu()
                    for m in [b.menu(), *b.menu().findChildren(A.QMenu)] if a in m.actions())
        # El arnés sustituye QMenu.exec para no bloquear; popup permite pulsar el ítem visible con QTest.
        m.popup(b.mapToGlobal(b.rect().bottomLeft()))
        A.esperar(80)
        for _ in m.actions():
            if m.activeAction() is a:
                break
            QTest.keyClick(m, Qt.Key_Down)
        assert m.activeAction() is a, (clave, m.activeAction())
        QTest.keyClick(m, Qt.Key_Return)
        m.hide()
    A.esperar(200)
    a.triggered.disconnect(contar)
    A.reg(AR, f"la cinta ejecuta {clave} al primer intento", len(pulsadas) == 1,
          {"pulsadas": pulsadas, "modo": v.visor.modo, "panel": type(v.panel).__name__})


def raton(widget, tipo, pos, mods=Qt.NoModifier):
    pos = QPointF(pos)
    QApplication.sendEvent(widget, QMouseEvent(tipo, pos, widget.mapToGlobal(pos),
        Qt.NoButton if tipo == QEvent.MouseMove else Qt.LeftButton,
        Qt.NoButton if tipo == QEvent.MouseButtonRelease else Qt.LeftButton, mods))


def gesto(widget, inicio, fin, foto=None):
    raton(widget, QEvent.MouseButtonPress, inicio)
    for k in range(1, 9):
        raton(widget, QEvent.MouseMove, inicio + (fin - inicio) * k / 8)
        A.esperar(16)
    if foto:
        A.foto(v, foto)
    raton(widget, QEvent.MouseButtonRelease, fin)
    A.esperar(250)


def teclear(panel, clave, texto, tecla=Qt.Key_Return):
    campo = panel.campos[clave] if clave in panel.campos else getattr(panel, clave)
    panel.desplazador.ensureWidgetVisible(campo)
    campo.setFocus()
    campo.selectAll()
    QTest.keyClicks(campo, texto)
    QTest.keyClick(campo, tecla)
    A.esperar(150)


def casilla(widget):
    QTest.mouseClick(widget, Qt.LeftButton, pos=QPoint(8, widget.height() // 2))
    A.esperar(100)


def boton(panel, nombre):
    panel.desplazador.ensureWidgetVisible(panel.botones[nombre])
    QTest.mouseClick(panel.botones[nombre], Qt.LeftButton)
    A.esperar(180)


def importar_y_cad():
    ruta = A.SALIDA / "anillo_interaccion.svg"
    ruta.write_text('<svg width="60mm" height="40mm" viewBox="0 0 60 40">'
                    '<path fill-rule="evenodd" d="M10 10H40V30H10Z M20 15H30V25H20Z"/></svg>', encoding="utf-8")
    v.visor.vista("arriba")
    QFileDialog.getOpenFileName = staticmethod(lambda *a, **k: (str(ruta), ""))
    accion("insertar_svg")
    p = v.panel
    limite = v.visor.distancia * 0.22
    q = v.visor.proyectar(np.array([limite / 2, limite / 2, 0.]))
    QTest.mouseClick(v.visor, Qt.LeftButton, pos=q.toPoint())
    p.widgets["archivo"].setFocus()
    p.widgets["archivo"].selectAll()
    QTest.keyClicks(p.widgets["archivo"], str(ruta).replace("\\", "/"))
    A.esperar(800)
    assert p.boton_ok.isEnabled(), A.estado_panel(p)
    QTest.mouseClick(p.boton_ok, Qt.LeftButton)
    A.esperar(400)
    assert v.panel is None and v.vectores.activo is not None
    lz = v.vectores.activo
    oid = ob.raices(lz.b)[0]
    v.visor.encuadrar()
    A.esperar(200)
    lz.seleccion = []
    lz._notificar_seleccion()
    QTest.mouseClick(v.visor, Qt.LeftButton, pos=lz.a_px(15, 20).toPoint())
    A.esperar(100)
    A.reg(AR, "un clic selecciona el SVG terminado con diez controles", lz.objetos.seleccion() == [oid]
          and len(lz.objetos.manijas()) == 10 and not v.modo_boceto.activo)
    A.foto(v, "directo_01_seleccion")
    panel = lz.objetos.panel
    A.reg(AR, "panel esencial y avanzado cerrado", not panel.avanzadas.abierta
          and not panel.campos["sx"].isVisible() and not panel.texto.isVisible())
    QTest.mouseClick(panel.avanzadas.boton, Qt.LeftButton)
    casilla(panel.imanes)
    QTest.mouseClick(panel.avanzadas.boton, Qt.LeftButton)
    antes = ob.caja(lz.b, [oid])
    gesto(v.visor, lz.a_px(15, 20), lz.a_px(25, 15), "directo_02_movimiento")
    A.reg(AR, "soltar confirma el desplazamiento sin otro clic", np.allclose(np.array(ob.caja(lz.b, [oid])) - antes, [10, -5, 10, -5]))
    asa = lz.objetos.manijas()["escala3"]
    gesto(v.visor, asa, asa + QPointF(45, 0), "directo_03_escala")
    e = lz.objetos.estado()
    A.reg(AR, "el tirador lateral también conserva proporciones", abs(e["ancho"] / e["alto"] - 1.5) < 1e-7)
    asa = lz.objetos.manijas()["rotar"]
    p0 = np.array(lz.objetos.pivote())
    u = np.array(lz.a_mm(asa)) - p0
    a = math.radians(30)
    fin = p0 + np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]]) @ u
    gesto(v.visor, asa, lz.a_px(*fin), "directo_04_rotacion")
    A.reg(AR, "giro visual de treinta grados confirmado", abs(lz.objetos.estado()["angulo"] - 30) < 1e-6)
    teclear(panel, "angulo", "0 deg")
    teclear(panel, "ancho", "60 mm")
    teclear(panel, "x", "-12,5 mm", Qt.Key_Tab)
    A.reg(AR, "medidas, coma decimal y Tab", abs(lz.objetos.estado()["ancho"] - 60) < 1e-7
          and abs(lz.objetos.estado()["x"] + 12.5) < 1e-7)
    receta = v.doc.a_dict()
    teclear(panel, "ancho", "90 mm", Qt.Key_Escape)
    QTest.mouseClick(panel.nombre, Qt.LeftButton)
    A.reg(AR, "Esc cancela también al cambiar después el foco", receta == v.doc.a_dict())
    for texto in ("", "0", "-5", "1e9 mm", "abc"):
        campo = panel.campos["ancho"]
        campo.setFocus()
        campo.selectAll()
        QTest.keyClick(campo, Qt.Key_Backspace)
        QTest.keyClicks(campo, texto)
        QTest.keyClick(campo, Qt.Key_Return)
        A.reg(AR, f"ancho inválido {texto!r} explica y conserva", bool(panel.error.text()) and receta == v.doc.a_dict(), panel.error.text())
        QTest.keyClick(campo, Qt.Key_Escape)
    for ancho, alto in ((1024, 640), (800, 520)):
        v.resize(ancho, alto)
        A.esperar(200)
        v.area.reubicar()
        panel.desplazador.ensureWidgetVisible(panel.campos["angulo"])
        A.reg(AR, f"controles accesibles sin scroll horizontal {ancho}×{alto}",
              v.area.rect().contains(panel.geometry()) and panel.desplazador.horizontalScrollBar().maximum() == 0,
              panel.geometry())
        A.foto(v, f"directo_05_panel_{ancho}x{alto}")
    v.resize(1440, 900)
    A.esperar(150)
    casilla(panel.perfiles)
    x0, y0, x1, y1 = ob.caja(lz.b, [oid])
    q = lz.a_px(x0 + (x1 - x0) / 8, (y0 + y1) / 2)
    QTest.mouseClick(v.visor, Qt.LeftButton, pos=q.toPoint())
    A.esperar(120)
    A.reg(AR, "en perfiles se elige una región sin arrastrar el objeto", bool(v.seleccion)
          and v.seleccion[0]["tipo"] == "perfil" and lz.objetos.arrastre is None)
    accion("extruir")
    p = v.panel
    A.reg(AR, "Extruir recibe la región preseleccionada", bool(p.valores.get("perfiles")))
    p.widgets["distancia"].setFocus()
    p.widgets["distancia"].selectAll()
    QTest.keyClicks(p.widgets["distancia"], "3 mm")
    QTest.keyClick(p.widgets["distancia"], Qt.Key_Tab)
    A.esperar(550)
    QTest.mouseClick(p.boton_ok, Qt.LeftButton)
    A.esperar(250)
    cuerpos = list(v.doc.estado_final.cuerpos.values())
    A.reg(AR, "extrusión con agujero válida y volumen exacto", len(cuerpos) == 1
          and geo.es_valida(cuerpos[0].forma) and abs(geo.volumen(cuerpos[0].forma) - 6000) < 1e-4)
    casilla(panel.perfiles)
    teclear(panel, "ancho", "90 mm")
    cuerpo = next(iter(v.doc.estado_final.cuerpos.values()))
    A.reg(AR, "transformar después recalcula la extrusión", abs(geo.volumen(cuerpo.forma) - 13500) < 1e-4
          and all(r.estado != "error" for r in v.doc.resultados))
    A.foto(v, "directo_06_solido_parametrico")
    archivo = A.SALIDA / "interaccion_parametrica.omnicad"
    QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: (str(archivo), ""))
    QTest.keyClick(v.visor, Qt.Key_S, Qt.ControlModifier)
    A.esperar(200)
    A.reg(AR, "Guardar de la interfaz crea el proyecto", archivo.exists())
    v.set_documento(Documento())
    QFileDialog.getOpenFileName = staticmethod(lambda *a, **k: (str(archivo), ""))
    QTest.keyClick(v.visor, Qt.Key_O, Qt.ControlModifier)
    A.esperar(350)
    A.reg(AR, "Abrir conserva ids, transformación y sólido", bool(v.doc.estado_final.cuerpos)
          and oid in v.doc.operaciones[0].boceto.objetos)
    v.vectores.seleccionar(v.doc.operaciones[0].id, [oid])
    lz = v.vectores.activo
    panel = lz.objetos.panel
    teclear(panel, "x", "25 mm")
    posicion = lz.objetos.estado()["x"]
    QTest.keyClick(v.visor, Qt.Key_Z, Qt.ControlModifier)
    QTest.keyClick(v.visor, Qt.Key_Y, Qt.ControlModifier)
    A.reg(AR, "modificar, deshacer y rehacer después de reabrir", abs(posicion - 25) < 1e-6
          and abs(lz.objetos.estado()["x"] - 25) < 1e-6 and lz.objetos.seleccion() == [oid])


def texto():
    v.set_documento(Documento())
    v.visor.vista("arriba")
    accion("boceto")
    limite = v.visor.distancia * 0.22
    q = v.visor.proyectar(np.array([limite / 2, limite / 2, 0.])).toPoint()
    hit = v.visor.elegir(QPointF(q))
    A.reg(AR, "plano XY bajo el clic de creación", hit is not None and hit["ref"] == "XY", (q, hit))
    QTest.mouseClick(v.visor, Qt.LeftButton, pos=q)
    A.esperar(200)
    assert v.modo_boceto.activo, (v.visor.modo, q, hit, A.MODALES)
    accion("sk_texto")
    lz = v.modo_boceto.lienzo
    for pos in (QPoint(450, 300), QPoint(850, 420)):
        QTest.mouseClick(lz, Qt.LeftButton, pos=pos)
    QTest.keyClicks(lz, "OB8")
    QTest.keyClick(lz, Qt.Key_Return, Qt.ControlModifier)
    QTest.keyClick(lz, Qt.Key_Escape)
    A.esperar(200)
    lz.encuadrar()
    A.esperar(150)
    tid = next(i for i, c in lz.b.curvas.items() if c.tipo == "texto")
    oid = ob.indice(lz.b)[tid][0]
    x0, y0, x1, y1 = ob.caja(lz.b, [oid])
    QTest.mouseClick(lz, Qt.LeftButton, pos=lz.a_px((x0 + x1) / 2, (y0 + y1) / 2).toPoint())
    panel = v.modo_boceto.objetos
    A.reg(AR, "crear palabra con teclado y seleccionar como objeto", lz.objetos.seleccion() == [oid] and panel.texto.isVisible())
    gesto(lz, lz.a_px((x0 + x1) / 2, (y0 + y1) / 2), lz.a_px((x0 + x1) / 2 + 12, (y0 + y1) / 2 + 8))
    teclear(panel, "angulo", "25 deg")
    teclear(panel, "ancho", "40 mm")
    boton(panel, "Editar texto")
    QTest.keyClick(lz, Qt.Key_A, Qt.ControlModifier)
    QTest.keyClicks(lz, "AB8")
    QTest.keyClick(lz, Qt.Key_Return, Qt.ControlModifier)
    A.esperar(250)
    A.reg(AR, "editar contenido transformado conserva el objeto", oid in lz.b.objetos and lz.b.curvas[tid].texto == "AB8")
    QTest.keyClick(lz, Qt.Key_F6)
    A.esperar(150)
    A.foto(v, "directo_07_texto_editable")
    QTest.mouseClick(panel.avanzadas.boton, Qt.LeftButton)
    QTest.mouseClick(panel.geometria.boton, Qt.LeftButton)
    antes = sum(p.area for p in sin_huecos(lz._perfiles(), lz.b))
    boton(panel, "Convertir texto")
    despues = sum(p.area for p in sin_huecos(lz._perfiles(), lz.b))
    A.reg(AR, "convertir conserva la tinta y los agujeros", tid not in lz.b.curvas and abs(despues - antes) < antes * 2e-5)
    boton(panel, "Separar regiones")
    A.reg(AR, "separar regiones deja tres letras con sus agujeros", len(lz.objetos.seleccion()) == 3)
    boton(panel, "Validar")
    A.reg(AR, "Validar informa resultados reales", bool(panel.error.text()), panel.error.text())
    A.foto(v, "directo_08_texto_convertido")


try:
    A.correr(AR, importar_y_cad)
    A.correr(AR, texto)
    A.reg(AR, "ninguna excepción de Qt", not A.ERRORES, A.ERRORES)
finally:
    if v.modo_boceto.activo:
        v.modo_boceto.cancelar()
    v.doc.modificado = False
    v.close()
    app.processEvents()
A.guardar_registro("manipulacion_vectorial")
fallas = sum(not r["ok"] for r in A.REGISTRO)
print(f"=== {len(A.REGISTRO)} comprobaciones, {fallas} con ✗ ===")
raise SystemExit(1 if fallas else 0)

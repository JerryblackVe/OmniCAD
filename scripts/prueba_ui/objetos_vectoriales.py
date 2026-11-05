# -*- coding: utf-8 -*-
"""Importar → seleccionar → arrastrar → escalar → girar → posicionar → extruir en la ventana real.

Incluye un SVG de 606 curvas, capturas durante el gesto, campos tecleados, deshacer,
guardar/reabrir y ventanas bajas. Usa eventos al widget, nunca el cursor real.
"""
import math
from pathlib import Path
import sys

import arnes as A
import numpy as np
from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QMouseEvent, QWheelEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QToolButton

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bench_objetos_vectoriales import logo  # noqa: E402
from omnicad import api  # noqa: E402
from omnicad.io_archivos import proyecto  # noqa: E402
from omnicad.nucleo import geometria as geo  # noqa: E402
from omnicad.nucleo import perfiles as perfiles_mod  # noqa: E402
from omnicad.restricciones import objetos as ob  # noqa: E402

AR = "OBJETOS VECTORIALES"
s = api.Sesion()


def L(nombre, **args):
    r = api.llamar(s, nombre, args)
    assert r["ok"], r
    return r["result"]


L("create_sketch", plane="XY", name="Logo")
app, v = A.iniciar(s.doc, 1440, 900)
op = s.paso("Logo").id
v.editar_operacion(op)
A.esperar(300)
lz = v.modo_boceto.lienzo
ruta = A.SALIDA / "logo606.svg"
ruta.write_text(logo(), encoding="utf-8")


def raton(tipo, punto, mods=Qt.NoModifier):
    q = punto if isinstance(punto, QPointF) else lz.a_px(*punto)
    QApplication.sendEvent(lz, QMouseEvent(tipo, q, lz.mapToGlobal(q),
                                          Qt.NoButton if tipo == QEvent.MouseMove else Qt.LeftButton,
                                          Qt.NoButton if tipo == QEvent.MouseButtonRelease else Qt.LeftButton, mods))


def clic(punto, mods=Qt.NoModifier):
    raton(QEvent.MouseButtonPress, punto, mods)
    raton(QEvent.MouseButtonRelease, punto, mods)
    A.esperar(100)


def teclear(campo, texto, tecla=Qt.Key_Return):
    campo.setFocus()
    campo.selectAll()
    QTest.keyClicks(campo, texto)
    QTest.keyClick(campo, tecla)
    A.esperar(300)


def prueba():
    # Insertar en el boceto abierto: ruta tecleada y botón Aceptar reales.
    p = A.abrir(v, "insertar_svg")
    campo = p.widgets["archivo"]
    campo.setFocus()
    QTest.keyClicks(campo, str(ruta).replace("\\", "/"))
    A.esperar(900)
    A.reg(AR, "la inserción tiene vista previa antes de aceptar", p.boton_ok.isEnabled(), A.estado_panel(p))
    QTest.mouseClick(p.boton_ok, Qt.LeftButton)
    A.esperar(700)
    A.reg(AR, "606 curvas, un objeto raíz y sin grados internos", len(lz.b.curvas) == 606
          and len(ob.raices(lz.b)) == 1 and lz.resultado.gdl == 0, (len(lz.b.curvas), lz.resultado.gdl))
    oid = ob.raices(lz.b)[0]
    lz.encuadrar()
    A.esperar(300)
    punto = (45.5, 54.5)
    clic(punto)
    A.reg(AR, "el clic elige el logo completo", lz.seleccion == [oid], lz.seleccion)
    A.reg(AR, "los controles internos no se pueden capturar", all(p in lz._ocultos()[1] for p in lz.b.puntos))
    A.foto(v, "vectores_01_seleccion_606")
    panel = v.modo_boceto.objetos
    A.reg(AR, "el panel integrado aparece", panel.isVisible())
    QTest.mouseClick(panel.avanzadas.boton, Qt.LeftButton)
    panel.desplazador.ensureWidgetVisible(panel.imanes)
    QTest.mouseClick(panel.imanes, Qt.LeftButton, pos=QPoint(8, panel.imanes.height() // 2))
    A.reg(AR, "la casilla apaga las guías", not lz.objetos.snap)
    QTest.mouseClick(panel.avanzadas.boton, Qt.LeftButton)

    antes, caja0 = lz.b.a_dict(), ob.caja(lz.b, [oid])
    n = len(lz.historial)
    raton(QEvent.MouseButtonPress, punto)
    for k in range(1, 7):
        raton(QEvent.MouseMove, (punto[0] + k * 2, punto[1] - k))
        A.esperar(20)
    A.reg(AR, "durante el arrastre no cambia la receta", lz.b.a_dict() == antes)
    A.reg(AR, "la capa CAD vieja está retirada durante el gesto", len(v.visor._perfiles) == 0)
    A.foto(v, "vectores_02_durante_arrastre")
    raton(QEvent.MouseButtonRelease, (punto[0] + 12, punto[1] - 6))
    A.esperar(350)
    caja1 = ob.caja(lz.b, [oid])
    A.reg(AR, "al soltar queda el desplazamiento exacto", np.allclose(np.array(caja1) - caja0, [12, -6, 12, -6]))
    A.reg(AR, "el gesto es un único deshacer", len(lz.historial) == n + 1)
    lz.deshacer()
    A.reg(AR, "deshacer restaura toda la receta", lz.b.a_dict() == antes)
    lz.rehacer()
    lz.seleccion = [oid]
    lz._notificar_seleccion()
    A.esperar(100)

    # Escala de esquina, sin deformar el logo.
    x0, y0, x1, y1 = lz.objetos.caja()
    asa = lz.objetos.manijas()["escala0"]
    destino = (x1 + 0.85 * (x0 - x1), y1 + 0.85 * (y0 - y1))
    raton(QEvent.MouseButtonPress, asa)
    raton(QEvent.MouseMove, destino)
    raton(QEvent.MouseButtonRelease, destino)
    A.esperar(200)
    m = ob.acumulada(lz.b, oid)
    A.reg(AR, "la esquina conserva proporciones", abs(np.linalg.norm(m[:2, 0]) - np.linalg.norm(m[:2, 1])) < 1e-8)

    # Rotación visual incremental.
    asa = lz.objetos.manijas()["rotar"]
    px, py = lz.objetos.pivote()
    ix, iy = lz.a_mm(asa)
    a = math.radians(30)
    destino = (px + math.cos(a) * (ix - px) - math.sin(a) * (iy - py),
               py + math.sin(a) * (ix - px) + math.cos(a) * (iy - py))
    raton(QEvent.MouseButtonPress, asa)
    raton(QEvent.MouseMove, destino, Qt.ShiftModifier)
    raton(QEvent.MouseButtonRelease, destino, Qt.ShiftModifier)
    A.esperar(300)
    A.reg(AR, "la manija gira treinta grados con Mayús", abs(lz.objetos.estado()["angulo"] - 30) < 1e-6,
          lz.objetos.estado()["angulo"])

    # Medidas absolutas en el panel, con unidades y con error visible.
    panel.desplazador.ensureWidgetVisible(panel.campos["ancho"])
    teclear(panel.campos["ancho"], "120 mm")
    A.reg(AR, "ancho tecleado exacto", abs(lz.objetos.estado()["ancho"] - 120) < 1e-6, lz.objetos.estado()["ancho"])
    buena = lz.b.a_dict()
    teclear(panel.campos["ancho"], "-5")
    A.reg(AR, "un ancho negativo se explica y no modifica", panel.error.text() and lz.b.a_dict() == buena, panel.error.text())
    teclear(panel.campos["ancho"], "120 mm")
    A.foto(v, "vectores_03_transformado")

    for ancho, alto in ((1024, 640), (800, 520)):
        v.resize(ancho, alto)
        A.esperar(250)
        v.area.reubicar()
        A.reg(AR, f"el panel es accesible en {ancho}x{alto}", v.width() == ancho and v.height() == alto and panel.height() <= v.area.height()
              and panel.desplazador.horizontalScrollBar().maximum() == 0, panel.geometry())
        A.foto(v, f"vectores_04_panel_{ancho}x{alto}")
    v.resize(1440, 900)
    A.esperar(250)

    matriz_final = ob.acumulada(lz.b, oid)
    QTest.mouseClick(v.modo_boceto.paleta.b_terminar, Qt.LeftButton)
    A.esperar(500)
    A.reg(AR, "terminar conserva el objeto en el timeline", bool(v.doc.operaciones[0].boceto.objetos))
    # Botón real de Extruir, perfil elegido en el visor, valor tecleado y vista previa.
    botones = [b for b in v.cinta.findChildren(QToolButton) if b.defaultAction() is v.acciones["extruir"] and b.isVisible()]
    assert botones, "No se encontró el botón visible de Extruir"
    QTest.mouseClick(botones[0], Qt.LeftButton)
    A.esperar(250)
    p = v.panel
    br = v.doc.estado_final.bocetos[op]
    # Vista desde arriba (menú Vista) y zoom con la rueda sobre la pieza más grande: el visor elige por píxeles
    # y, sin zoom, la tolerancia de 9 px del trazo se come la pieza rellena.
    grande = max(perfiles_mod.sin_huecos(br.perfiles, br.boceto), key=lambda x: x.area)
    objetivo = np.asarray(grande.centroide_uv, float)
    v.acciones["vista_arriba"].trigger()
    A.esperar(300)
    for _ in range(10):
        q = v.visor.proyectar(np.asarray(br.plano.a_3d(*objetivo))).toPoint()
        QApplication.sendEvent(v.visor, QWheelEvent(QPointF(q), v.visor.mapToGlobal(QPointF(q)),
                                                   QPoint(0, 0), QPoint(0, 120), Qt.NoButton, Qt.NoModifier,
                                                   Qt.NoScrollPhase, False))
    A.esperar(250)
    q = v.visor.proyectar(np.asarray(br.plano.a_3d(*objetivo))).toPoint()
    QTest.mouseClick(v.visor, Qt.LeftButton, pos=q)
    A.esperar(200)
    A.reg(AR, "el visor elige la región rellena y no el trazo",
          bool(p.valores.get("perfiles")) and p.valores["perfiles"][0]["ref"].get("tipo") == "perfil",
          [h["ref"].get("tipo") for h in p.valores.get("perfiles", [])])
    teclear(p.widgets["distancia"], "2 mm", Qt.Key_Tab)   # Tab: Return en un panel de comando lo acepta
    A.esperar(600)
    A.reg(AR, "el perfil tiene una extrusión previsualizada", p._previa_ok and p.ultima_op is not None, A.estado_panel(p))
    A.foto(v, "vectores_05_previa_extrusion")
    QTest.mouseClick(p.boton_ok, Qt.LeftButton)
    A.esperar(500)
    cuerpos = list(v.doc.estado_final.cuerpos.values())
    A.reg(AR, "la extrusión aceptada es un sólido válido", bool(cuerpos) and all(geo.es_valida(c.forma) and geo.volumen(c.forma) > 0 for c in cuerpos))
    A.foto(v, "vectores_06_solido")
    archivo = A.SALIDA / "vector_transformado.omnicad"
    proyecto.guardar(v.doc, archivo)
    doc = proyecto.abrir(archivo)
    A.reg(AR, "guardar/reabrir mantiene los ids y las matrices", ob.raices(doc.operaciones[0].boceto) == [oid]
          and np.allclose(ob.acumulada(doc.estado_final.bocetos[op].boceto, oid), matriz_final))
    A.reg(AR, "guardar/reabrir mantiene el volumen", abs(sum(geo.volumen(c.forma) for c in doc.estado_final.cuerpos.values())
          - sum(geo.volumen(c.forma) for c in cuerpos)) < 1e-5)


try:
    A.correr(AR, prueba)
    A.reg(AR, "ninguna excepción escapó de un slot de Qt", not A.ERRORES, A.ERRORES)
finally:
    if v.modo_boceto.activo:
        v.modo_boceto.cancelar()
    v.doc.modificado = False
    v.close()
    app.processEvents()
A.guardar_registro("objetos_vectoriales")
fallas = sum(not r["ok"] for r in A.REGISTRO)
print(f"=== {len(A.REGISTRO)} comprobaciones, {fallas} con ✗ ===")
sys.exit(1 if fallas else 0)

# -*- coding: utf-8 -*-
"""Una placa paramétrica de principio a fin, por los widgets de la ventana real.

Solo el rectángulo inicial y la gemela de referencia se construyen con la API.
Las cotas, selecciones, valores, aceptación y edición usan clics/teclas simulados.
"""
import math
import sys
import tempfile
from pathlib import Path

import arnes as A
from omnicad import api
from omnicad.nucleo import geometria as geo
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (
    QAbstractButton,
    QFileDialog,
    QLineEdit,
    QScrollArea,
)

AR = "PIEZA·COMPLETA"
s = api.Sesion()
app, v = A.iniciar(s.doc, ancho=1280, alto=720)


def llamar(sesion, nombre, **argumentos):
    respuesta = api.llamar(sesion, nombre, argumentos)
    if not respuesta["ok"]:
        raise RuntimeError(f"{nombre}({argumentos}): {respuesta}")
    return respuesta["result"]


def foto(nombre):
    ruta = A.foto(v, nombre)
    print(f"CAPTURA: {ruta}", flush=True)


def pulsar(widget):
    for zona in v.findChildren(QScrollArea):
        if zona.isAncestorOf(widget):
            zona.ensureWidgetVisible(widget)
    QTest.mouseClick(widget, Qt.LeftButton)
    A.esperar(150)


def boton(contenedor, texto):
    return next(b for b in contenedor.findChildren(QAbstractButton)
                if b.isVisible() and b.text().replace("&", "").strip() == texto)


def teclear(campo, texto, enter=False):
    pulsar(campo)
    campo.selectAll()
    QTest.keyClicks(campo, texto)
    if enter:
        QTest.keyClick(campo, Qt.Key_Return)
    A.esperar(200)


def campo_panel(panel, clave, texto):
    widget = panel.widgets[clave]
    campo = widget if isinstance(widget, QLineEdit) else next(
        c for c in widget.findChildren(QLineEdit) if c.isVisible())
    teclear(campo, texto)
    QTest.keyClick(campo, Qt.Key_Tab)
    A.esperar(250)


def volumen():
    return sum(geo.volumen(c.forma) for c in v.doc.estado_final.cuerpos.values())


def comprobar_volumen(etiqueta, esperado):
    obtenido = volumen()
    A.reg(AR, etiqueta, math.isclose(obtenido, esperado, rel_tol=0.001),
          f"esperado={esperado:.6f} mm³; obtenido={obtenido:.6f} mm³; tolerancia=0,1 %")


def entrar_boceto():
    lista = v.timeline.lista
    item = next(lista.item(i) for i in range(lista.count())
                if lista.item(i).data(Qt.UserRole) == boceto_id)
    lista.scrollToItem(item)
    A.esperar(100)
    pos = lista.visualItemRect(item).center()
    QTest.mouseClick(lista.viewport(), Qt.LeftButton, Qt.NoModifier, pos)
    QTest.mouseDClick(lista.viewport(), Qt.LeftButton, Qt.NoModifier, pos)
    A.esperar(500)
    activo = v.modo_boceto.activo and v.modo_boceto.lienzo is not None
    A.reg(AR, "doble clic en el timeline abre el boceto", activo, f"boceto={boceto_id}")
    if not activo:
        return None
    v.visor.encuadrar()
    A.esperar(250)
    return v.modo_boceto.lienzo


def salir_boceto():
    candidatos = [b for b in v.cinta.findChildren(QAbstractButton)
                  if b.isVisible() and "boceto" in b.text().lower()
                  and any(t in b.text().lower() for t in ("terminar", "finalizar", "salir"))]
    if not candidatos:
        raise RuntimeError("No se encontró el botón de terminar el boceto en la cinta")
    pulsar(candidatos[0])
    A.esperar(500)
    A.reg(AR, "salir del boceto con clic en la cinta", not v.modo_boceto.activo,
          candidatos[0].text())


def acotar(lienzo, lado, ubicacion, texto):
    antes = set(lienzo.b.cotas)
    # El mismo selector de herramienta que usa boceto_cotas; los picks son eventos al lienzo.
    lienzo.set_herramienta("cota")
    for punto in (lado, ubicacion):
        QTest.mouseClick(lienzo, Qt.LeftButton, Qt.NoModifier, lienzo.a_px(*punto).toPoint())
        A.esperar(100)
    abierta = lienzo.entrada is not None and lienzo.entrada.isVisible()
    if abierta:
        teclear(lienzo.entrada.campos[0], texto, enter=True)
    nueva = next((c for c in lienzo.b.cotas.values() if c.id not in antes), None)
    A.reg(AR, f"cota {texto}: clic en lado, ubicar y teclear Enter",
          abierta and nueva is not None and nueva.expresion == texto,
          f"caja abierta={abierta}; cota={nueva and (nueva.id, nueva.expresion)}")
    return nueva.id if nueva else None


def abrir_cota(lienzo):
    lienzo.set_herramienta("seleccionar")
    lienzo.grab()  # actualiza las zonas de los textos antes del doble clic
    zona = lienzo._zonas_cotas.get(cota_ancho)
    if zona is None:
        raise RuntimeError(f"La cota {cota_ancho} no tiene zona visible de doble clic")
    QTest.mouseDClick(lienzo, Qt.LeftButton, Qt.NoModifier, zona.center().toPoint())
    A.esperar(150)
    abierta = lienzo.entrada is not None and lienzo.entrada.isVisible()
    A.reg(AR, "doble clic en la cota abre la caja", abierta, f"cota={cota_ancho}")
    return lienzo.entrada.campos[0] if abierta else None


def elegir_punto(panel, clave, punto, modificador=Qt.NoModifier):
    pulsar(panel.widgets[clave])
    pos = v.visor.proyectar(A.np.array(punto, float))
    if pos is None or not v.visor.rect().contains(pos.toPoint()):
        raise RuntimeError(f"El punto de selección {punto} queda fuera del visor")
    QTest.mouseClick(v.visor, Qt.LeftButton, modificador, pos.toPoint())
    A.esperar(250)


def aceptar(panel, etiqueta):
    for _ in range(200):
        A.esperar(50)
        if not panel._t_previa.isActive() and panel._hijo_previa is None:
            break
    estado = A.estado_panel(panel)
    A.reg(AR, f"{etiqueta}: vista previa", estado["previa_ok"] and estado["op"], str(estado))
    foto(f"{etiqueta}_previa")
    antes = len(v.doc.operaciones)
    pulsar(boton(panel, "Aceptar"))
    A.esperar(500)
    creado = len(v.doc.operaciones) == antes + 1
    A.reg(AR, f"{etiqueta}: clic en Aceptar agrega un paso", creado,
          f"pasos={antes} → {len(v.doc.operaciones)}")
    if not creado:
        pulsar(boton(panel, "Cancelar"))
    v.visor.encuadrar()
    A.esperar(250)
    foto(etiqueta)
    return creado


def gemela(ancho):
    sesion = api.Sesion()
    llamar(sesion, "create_sketch", name="Gemela", plane="XY")
    llamar(sesion, "draw_rectangle", sketch="Gemela", x1=0, y1=0, x2=ancho, y2=25)
    llamar(sesion, "extrude", sketch="Gemela", distance=10)
    llamar(sesion, "fillet", edges="|Z", radius=3)
    llamar(sesion, "create_hole", face=">Z", diameter=6, through_all=True)
    return sum(geo.volumen(c.forma) for c in sesion.doc.estado_final.cuerpos.values())


def comprobar_recalculo(ancho, etiqueta):
    actual = api.Sesion(v.doc)
    medidas = llamar(actual, "get_physical_properties")
    pasos = llamar(actual, "get_timeline")["steps"]
    tamano = medidas["total"]["bounding_box"]["size"] if medidas["bodies"] else []
    A.reg(AR, f"{etiqueta}: caja envolvente {ancho}×25×10",
          len(tamano) == 3 and all(math.isclose(a, b, abs_tol=0.001)
                                  for a, b in zip(tamano, (ancho, 25, 10), strict=True)), tamano)
    malos = [(p["name"], p["status"], p["message"]) for p in pasos if p["status"] != "ok"]
    A.reg(AR, f"{etiqueta}: cuatro pasos sin errores", len(pasos) == 4 and not malos,
          f"pasos={len(pasos)}; errores={malos}")
    comprobar_volumen(f"{etiqueta}: volumen igual a gemela API desde cero", gemela(ancho))
    A.reg(AR, f"{etiqueta}: un sólido válido", len(v.doc.estado_final.cuerpos) == 1
          and all(geo.es_valida(c.forma) for c in v.doc.estado_final.cuerpos.values()))
    foto(etiqueta)


def cambiar_cota(texto, ancho, etiqueta):
    lienzo = entrar_boceto()
    if lienzo is None:
        return
    campo = abrir_cota(lienzo)
    if campo is not None:
        teclear(campo, texto, enter=True)
        cota = lienzo.b.cotas[cota_ancho]
        A.reg(AR, f"{etiqueta}: acepta «{texto}»", cota.expresion == texto,
              f"expresión={cota.expresion}; medida={lienzo.b.medir(cota)}")
    salir_boceto()
    comprobar_recalculo(ancho, etiqueta)


def valor_invalido():
    antes = A.cuerpos_resumen(v)
    lienzo = entrar_boceto()
    if lienzo is None:
        return
    cota = lienzo.b.cotas[cota_ancho]
    expresion, medida = cota.expresion, lienzo.b.medir(cota)
    campo = abrir_cota(lienzo)
    if campo is not None:
        teclear(campo, "abc", enter=True)
        abierta = lienzo.entrada is not None and lienzo.entrada.isVisible()
        estilo = campo.styleSheet()
        mensaje = v.timeline.estado.toolTip()    # el aviso del boceto va a la etiqueta de abajo (barra del timeline), no a statusBar()
        A.reg(AR, "«abc» queda en rojo, con mensaje y caja abierta",
              abierta and "#5c2a2d" in estilo.lower() and "abc" in mensaje.lower(),
              f"abierta={abierta}; estilo={estilo!r}; mensaje={mensaje!r}")
        foto("cota_abc")
        cota = lienzo.b.cotas[cota_ancho]
        A.reg(AR, "«abc» no cambia la cota ni su medida",
              cota.expresion == expresion and math.isclose(lienzo.b.medir(cota), medida, abs_tol=1e-6),
              f"antes={expresion!r}/{medida}; después={cota.expresion!r}/{lienzo.b.medir(cota)}")
        if abierta:
            QTest.keyClick(campo, Qt.Key_Escape)
    salir_boceto()
    A.reg(AR, "«abc» no cambia ningún volumen", A.cuerpos_resumen(v) == antes,
          f"antes={antes}; después={A.cuerpos_resumen(v)}")


def cadena():
    antes = A.cuerpos_resumen(v)
    pasos = llamar(api.Sesion(v.doc), "get_timeline")
    cuentas = []
    for clave, tecla in (("deshacer", Qt.Key_Z), ("rehacer", Qt.Key_Y)):
        cantidad = 0
        disparos = []
        accion = v.acciones[clave]
        def contar(*_, disparos=disparos):
            disparos.append(1)
        accion.triggered.connect(contar)
        while accion.isEnabled() and cantidad < 100:
            A.activar(v)
            v.visor.setFocus()
            QTest.keyClick(v.visor, tecla, Qt.ControlModifier)
            A.esperar(180)
            cantidad += 1
            if len(disparos) < cantidad:
                break
        accion.triggered.disconnect(contar)
        cuentas.append(cantidad)
        A.reg(AR, f"Ctrl+{tecla.name[-1]}: {clave} en cadena agota el historial",
              cantidad > 0 and len(disparos) == cantidad and not accion.isEnabled(),
              f"teclas={cantidad}; acciones={len(disparos)}; pasos={len(v.doc.operaciones)}")
        if clave == "deshacer":
            A.reg(AR, "deshacer llega al documento vacío",
                  not v.doc.estado_final.cuerpos and not v.doc.operaciones,
                  f"pasos={len(v.doc.operaciones)}; cuerpos={A.cuerpos_resumen(v)}")
    A.reg(AR, "rehacer recupera cuerpos, volúmenes y timeline completos",
          A.cuerpos_resumen(v) == antes and llamar(api.Sesion(v.doc), "get_timeline") == pasos,
          f"deshacer/rehacer={cuentas}; antes={antes}; después={A.cuerpos_resumen(v)}")
    foto("rehacer")


def guardar_reabrir():
    ruta = Path(tempfile.mkdtemp(prefix="pieza_completa_", dir=A.SALIDA)) / "placa.omnicad"
    QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: (str(ruta), ""))
    QFileDialog.getOpenFileName = staticmethod(lambda *a, **k: (str(ruta), ""))
    antes = A.cuerpos_resumen(v)
    pasos = llamar(api.Sesion(v.doc), "get_timeline")
    v.acciones["guardar"].trigger()
    A.esperar(500)
    A.reg(AR, "Guardar de la ventana crea .omnicad", ruta.exists() and ruta.stat().st_size > 0, ruta)
    # El historial pertenece al documento abierto, no al archivo: mismo orden que ventana_uso.
    cadena()
    v.acciones["guardar"].trigger()
    A.esperar(300)
    # OmniCAD reemplaza el documento con Nuevo; no tiene una QAction «cerrar».
    v.acciones["nuevo"].trigger()
    A.esperar(400)
    A.reg(AR, "Nuevo cierra el documento guardado y deja uno vacío",
          not v.doc.operaciones and not v.doc.estado_final.cuerpos, f"pasos={len(v.doc.operaciones)}")
    v.acciones["abrir"].trigger()
    A.esperar(700)
    A.reg(AR, "reabrir conserva los volúmenes por cuerpo", A.cuerpos_resumen(v) == antes,
          f"antes={antes}; después={A.cuerpos_resumen(v)}")
    despues = llamar(api.Sesion(v.doc), "get_timeline")
    A.reg(AR, "reabrir conserva todos los pasos del timeline", despues == pasos,
          f"antes={[(p['id'], p['type'], p['status']) for p in pasos['steps']]}; "
          f"después={[(p['id'], p['type'], p['status']) for p in despues['steps']]}")
    comprobar_recalculo(30, "reabierta")


def construir():
    global boceto_id, cota_ancho
    A.reg(AR, "documento vacío en ventana 1280×720", not v.doc.operaciones
          and v.width() == 1280 and v.height() == 720, f"{v.width()}×{v.height()}")
    llamar(s, "create_sketch", name="Placa", plane="XY")
    llamar(s, "draw_rectangle", sketch="Placa", x1=0, y1=0, x2=40, y2=25)
    boceto_id = s.paso("Placa").id
    # La preparación API no notifica a la ventana: refrescar el documento al terminarla.
    v.doc.recalcular()
    v.editar_operacion(boceto_id)
    A.esperar(500)
    lienzo = v.modo_boceto.lienzo
    v.visor.encuadrar()
    A.esperar(250)
    cota_ancho = acotar(lienzo, (20, 25), (20, 33), "40")
    acotar(lienzo, (40, 12.5), (48, 12.5), "25")
    foto("boceto_cotas")
    salir_boceto()
    foto("boceto")
    panel = A.abrir(v, "extruir")
    perfil = A.hit_perfil(v, s, "Placa")
    A.reg(AR, "el visor encuentra el perfil", perfil is not None)
    elegir_punto(panel, "perfiles", (20, 12.5, 0))
    campo_panel(panel, "distancia", "10")
    if not aceptar(panel, "extrusion"):
        return
    comprobar_volumen("extrusión: 40·25·10", 10000)
    cuerpo_id = next(iter(v.doc.estado_final.cuerpos))
    panel = A.abrir(v, "empalme_3d")
    for x, y in ((0, 0), (40, 0), (40, 25), (0, 25)):
        # Girar hacia cada esquina deja la arista visible, sin seleccionar a través del sólido.
        v.visor.vista_direccion((1 if x else -1, 1 if y else -1, 0.6))
        A.esperar(200)
        elegir_punto(panel, "aristas", (x, y, 5), Qt.ShiftModifier)
        seleccionadas = panel.valores["aristas"]
        medios = [h["ref"].get("firma", {}).get("medio") for h in seleccionadas]
        A.reg(AR, f"clic en arista vertical ({x}, {y}) selecciona esa arista",
              any(m is not None and A.np.linalg.norm(A.np.array(m) - (x, y, 5)) < 0.01
                  for m in medios), f"puntos medios elegidos={medios}")
    A.reg(AR, "cuatro aristas elegidas mediante clics", len(panel.valores["aristas"]) == 4,
          f"selecciones={len(panel.valores['aristas'])}")
    campo_panel(panel, "radio", "3")
    if not aceptar(panel, "empalme"):
        return
    comprobar_volumen("empalme: resta 4·(1−π/4)·3²·10", 10000 - 4 * (1 - math.pi / 4) * 9 * 10)
    v.visor.vista("iso")
    A.esperar(200)
    panel = A.abrir(v, "agujero")
    hit = A.hit_cara(v, cuerpo_id, normal=(0, 0, 1))
    A.reg(AR, "la cara superior se elige con el visor", hit is not None)
    elegir_punto(panel, "colocacion", (20, 12.5, 10))
    campo_panel(panel, "diametro", "6")
    campo_panel(panel, "profundidad", "10")
    if not aceptar(panel, "agujero"):
        return
    comprobar_volumen("agujero: resta π·3²·10", 10000 - 4 * (1 - math.pi / 4) * 9 * 10 - math.pi * 9 * 10)
    cambiar_cota("50", 50, "ancho_50")
    cambiar_cota("40 * 1,25", 50, "expresion_50")
    valor_invalido()
    cambiar_cota("30", 30, "ancho_30")
    guardar_reabrir()


try:
    A.correr(AR, construir)
finally:
    A.reg(AR, "ninguna excepción escapó de un slot de Qt", not A.ERRORES,
          f"{len(A.ERRORES)}: {A.ERRORES}")
    A.guardar_registro("pieza_completa")
    fallas = [r for r in A.REGISTRO if not r["ok"]]
    print(f"\n=== {len(A.REGISTRO)} comprobaciones, {len(fallas)} con ✗ ===")
    v.doc.modificado = False
    v.close()
sys.exit(1 if fallas else 0)

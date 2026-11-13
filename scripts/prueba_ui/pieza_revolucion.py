# -*- coding: utf-8 -*-
"""Un eje por revolución, chaflán y rosca modelada, de principio a fin.

Solo el rectángulo inicial y las gemelas se construyen con la API, como en
pieza_completa. Cotas, selecciones y ediciones usan clics/teclas simulados.
El historial se prueba antes de Nuevo: no se serializa en el .omnicad.
"""
import math
import sys
import tempfile
from pathlib import Path

import arnes as A
from omnicad import api
from omnicad.nucleo import geometria as geo
from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QAbstractButton, QFileDialog, QLineEdit, QScrollArea

AR = "PIEZA·REVOLUCIÓN"
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


def comprobar_solido(etiqueta):
    cuerpos = list(v.doc.estado_final.cuerpos.values())
    cantidades = [len(geo.solidos(c.forma)) for c in cuerpos]
    A.reg(AR, f"{etiqueta}: un cuerpo, UN sólido válido", len(cuerpos) == 1
          and cantidades == [1] and geo.es_valida(cuerpos[0].forma),
          f"cuerpos={len(cuerpos)}; sólidos por cuerpo={cantidades}")


def abrir_paso(ident):
    lista = v.timeline.lista
    item = next(lista.item(i) for i in range(lista.count())
                if lista.item(i).data(Qt.UserRole) == ident)
    lista.scrollToItem(item)
    A.esperar(100)
    pos = lista.visualItemRect(item).center()
    QTest.mouseClick(lista.viewport(), Qt.LeftButton, Qt.NoModifier, pos)
    QTest.mouseDClick(lista.viewport(), Qt.LeftButton, Qt.NoModifier, pos)
    A.esperar(500)


def entrar_boceto():
    abrir_paso(boceto_id)
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
    zona = lienzo._zonas_cotas.get(cota_radio)
    if zona is None:
        raise RuntimeError(f"La cota {cota_radio} no tiene zona visible de doble clic")
    QTest.mouseDClick(lienzo, Qt.LeftButton, Qt.NoModifier, zona.center().toPoint())
    A.esperar(150)
    abierta = lienzo.entrada is not None and lienzo.entrada.isVisible()
    A.reg(AR, "doble clic en la cota abre la caja", abierta, f"cota={cota_radio}")
    return lienzo.entrada.campos[0] if abierta else None


def elegir_punto(panel, clave, punto):
    pulsar(panel.widgets[clave].boton)
    pos = v.visor.proyectar(A.np.array(punto, float))
    if pos is None or not v.visor.rect().contains(pos.toPoint()):
        raise RuntimeError(f"El punto de selección {punto} queda fuera del visor")
    QTest.mouseClick(v.visor, Qt.LeftButton, Qt.NoModifier, pos.toPoint())
    A.esperar(250)
    seleccion = panel.valores.get(clave) or []
    A.reg(AR, f"clic en el visor elige {clave}", len(seleccion) == 1,
          [h["ref"] for h in seleccion])
    return seleccion


def esperar_previa(panel):
    for _ in range(1200):
        A.esperar(50)
        if not panel._t_previa.isActive() and panel._hijo_previa is None:
            break
    return A.estado_panel(panel)


def aceptar(panel, etiqueta):
    estado = esperar_previa(panel)
    A.reg(AR, f"{etiqueta}: vista previa", estado["previa_ok"] and estado["op"], str(estado))
    foto(f"{etiqueta}_previa")
    antes = len(v.doc.operaciones)
    pulsar(boton(panel, "Aceptar"))
    A.esperar(500)
    creado = len(v.doc.operaciones) == antes + 1 and v.panel is None
    A.reg(AR, f"{etiqueta}: clic en Aceptar agrega un paso", creado,
          f"pasos={antes} → {len(v.doc.operaciones)}; modales={A.MODALES}")
    if not creado and v.panel is panel:
        pulsar(boton(panel, "Cancelar"))
    v.visor.encuadrar()
    A.esperar(250)
    foto(etiqueta)
    return creado


def gemela(radio):
    sesion = api.Sesion()
    llamar(sesion, "create_sketch", name="Gemela", plane="XZ")
    llamar(sesion, "draw_rectangle", sketch="Gemela", x1=0, y1=0, x2=radio, y2=40)
    llamar(sesion, "revolve", sketch="Gemela", axis="z", angle=360)
    llamar(sesion, "chamfer", edges="%CIRCLE and >Z", distance=1)
    llamar(sesion, "create_thread", faces="%CYLINDER", modeled=True, thread_class="")
    return sum(geo.volumen(c.forma) for c in sesion.doc.estado_final.cuerpos.values())


def comprobar_recalculo(radio, etiqueta):
    actual = api.Sesion(v.doc)
    medidas = llamar(actual, "get_physical_properties")
    pasos = llamar(actual, "get_timeline")["steps"]
    tamano = medidas["total"]["bounding_box"]["size"] if medidas["bodies"] else []
    A.reg(AR, f"{etiqueta}: caja envolvente X = {2 * radio} (diámetro)",
          len(tamano) == 3 and math.isclose(tamano[0], 2 * radio, abs_tol=0.001), tamano)
    malos = [(p["name"], p["status"], p["message"]) for p in pasos if p["status"] != "ok"]
    A.reg(AR, f"{etiqueta}: cuatro pasos sin errores", len(pasos) == 4 and not malos,
          f"pasos={len(pasos)}; errores={malos}")
    comprobar_volumen(f"{etiqueta}: volumen igual a gemela API desde cero", gemela(radio))
    comprobar_solido(etiqueta)
    v.visor.vista("iso")
    v.visor.encuadrar()
    A.esperar(200)
    foto(etiqueta)


def cambiar_cota(texto, radio, etiqueta):
    lienzo = entrar_boceto()
    if lienzo is None:
        return
    campo = abrir_cota(lienzo)
    if campo is not None:
        teclear(campo, texto, enter=True)
        cota = lienzo.b.cotas[cota_radio]
        A.reg(AR, f"{etiqueta}: acepta «{texto}»", cota.expresion == texto,
              f"expresión={cota.expresion}; medida={lienzo.b.medir(cota)}")
    salir_boceto()
    comprobar_recalculo(radio, etiqueta)


def valor_invalido():
    antes = A.cuerpos_resumen(v)
    pasos = llamar(api.Sesion(v.doc), "get_timeline")
    lienzo = entrar_boceto()
    if lienzo is None:
        return
    cota = lienzo.b.cotas[cota_radio]
    expresion, medida = cota.expresion, lienzo.b.medir(cota)
    campo = abrir_cota(lienzo)
    if campo is not None:
        teclear(campo, "abc", enter=True)
        abierta = lienzo.entrada is not None and lienzo.entrada.isVisible()
        estilo = campo.styleSheet()
        mensaje = v.timeline.estado.toolTip()
        A.reg(AR, "«abc» queda en rojo, con mensaje en el timeline y caja abierta",
              abierta and "#5c2a2d" in estilo.lower() and "abc" in mensaje.lower(),
              f"abierta={abierta}; estilo={estilo!r}; mensaje={mensaje!r}")
        foto("cota_abc")
        cota = lienzo.b.cotas[cota_radio]
        A.reg(AR, "«abc» no cambia la cota ni su medida",
              cota.expresion == expresion and math.isclose(lienzo.b.medir(cota), medida, abs_tol=1e-6),
              f"antes={expresion!r}/{medida}; después={cota.expresion!r}/{lienzo.b.medir(cota)}")
        if abierta:
            QTest.keyClick(campo, Qt.Key_Escape)
    salir_boceto()
    A.reg(AR, "«abc» no cambia volúmenes ni parámetros del timeline", A.cuerpos_resumen(v) == antes
          and llamar(api.Sesion(v.doc), "get_timeline") == pasos,
          f"antes={antes}; después={A.cuerpos_resumen(v)}")


def paneles_chicos():
    antes = A.cuerpos_resumen(v)
    for op in list(v.doc.operaciones)[1:]:
        abrir_paso(op.id)
        panel = v.panel
        A.reg(AR, f"800×520: doble clic abre {op.nombre}", panel is not None)
        if panel is None:
            continue
        if panel.seccion is not None and op.TIPO == "rosca":
            pulsar(panel.seccion.boton)
        esperar_previa(panel)
        marco = v.area.rect()
        rect_panel = QRect(panel.mapTo(v.area, QPoint(0, 0)), panel.size())
        barra = v.area.barra
        for texto in ("Aceptar", "Cancelar"):
            b = boton(panel, texto)
            rect_boton = QRect(b.mapTo(v.area, QPoint(0, 0)), b.size())
            dentro = (b.isVisible() and marco.contains(rect_boton)
                      and b.visibleRegion().contains(b.rect())
                      and (barra is None or not barra.isVisible()
                           or not barra.geometry().intersects(rect_boton)))
            A.reg(AR, f"800×520 · {op.nombre}: {texto} visible y dentro del lienzo",
                  v.size().width() == 800 and v.height() == 520 and dentro and marco.contains(rect_panel),
                  f"lienzo={marco}; panel={rect_panel}; botón={rect_boton}")
        foto(f"800_{panel.comando.CLAVE}")
        pulsar(boton(panel, "Cancelar"))
        A.reg(AR, f"800×520 · {op.nombre}: clic en Cancelar cierra sin cambiar la pieza",
              v.panel is None and A.cuerpos_resumen(v) == antes)


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
    ruta = Path(tempfile.mkdtemp(prefix="pieza_revolucion_", dir=A.SALIDA)) / "eje.omnicad"
    QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: (str(ruta), ""))
    QFileDialog.getOpenFileName = staticmethod(lambda *a, **k: (str(ruta), ""))
    antes = A.cuerpos_resumen(v)
    pasos = llamar(api.Sesion(v.doc), "get_timeline")
    v.acciones["guardar"].trigger()
    A.esperar(500)
    A.reg(AR, "Guardar de la ventana crea .omnicad", ruta.exists() and ruta.stat().st_size > 0, ruta)
    # Como pieza_completa: el historial pertenece al documento abierto, no al archivo.
    cadena()
    v.acciones["guardar"].trigger()
    A.esperar(300)
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
          f"antes={pasos}; después={despues}")
    comprobar_recalculo(10, "reabierta")


def construir():
    global boceto_id, cota_radio
    A.reg(AR, "documento vacío en ventana 1280×720", not v.doc.operaciones
          and v.width() == 1280 and v.height() == 720, f"{v.width()}×{v.height()}")
    llamar(s, "create_sketch", name="Perfil del eje", plane="XZ")
    llamar(s, "draw_rectangle", sketch="Perfil del eje", x1=0, y1=0, x2=10, y2=40)
    boceto_id = s.paso("Perfil del eje").id
    # La preparación API no notifica a la ventana: refrescar al terminarla.
    v.doc.recalcular()
    v.editar_operacion(boceto_id)
    A.esperar(500)
    lienzo = v.modo_boceto.lienzo
    v.visor.encuadrar()
    A.esperar(250)
    cota_radio = acotar(lienzo, (5, 40), (5, 44), "10")
    acotar(lienzo, (10, 20), (16, 20), "40")
    foto("boceto_cotas")
    salir_boceto()
    foto("boceto")

    panel = A.abrir(v, "revolucion")
    elegir_punto(panel, "perfiles", (5, 0, 20))
    elegidos = elegir_punto(panel, "eje", (0, 0, 20))
    A.reg(AR, "el eje elegido pasa por el lado vertical del perfil",
          len(elegidos) == 1 and (elegidos[0]["ref"] == {"tipo": "eje", "id": "Z"}
          or elegidos[0]["ref"].get("tipo") == "curva_boceto"), [h["ref"] for h in elegidos])
    campo_panel(panel, "angulo", "360")
    if not aceptar(panel, "revolucion"):
        return
    comprobar_volumen("revolución: π·10²·40", math.pi * 10**2 * 40)
    comprobar_solido("revolución")

    v.visor.vista_direccion((1, -1, 0.8))
    A.esperar(200)
    panel = A.abrir(v, "chaflan_3d")
    punto = (10 / math.sqrt(2), -10 / math.sqrt(2), 40)
    elegidos = elegir_punto(panel, "aristas", punto)
    firmas = [h["ref"].get("firma", {}) for h in elegidos]
    A.reg(AR, "chaflán: clic elige la arista circular superior",
          len(firmas) == 1 and firmas[0].get("geom") == "circulo"
          and math.isclose(firmas[0].get("centro", [0, 0, -1])[2], 40, abs_tol=0.001), firmas)
    campo_panel(panel, "distancia", "1")
    antes = volumen()
    if not aceptar(panel, "chaflan"):
        return
    # Cilindro de alto d menos tronco de cono de radios R y R-d: π·(R·d²-d³/3).
    quitado = math.pi * (10 * 1**2 - 1**3 / 3)
    A.reg(AR, "chaflán 1 mm: quita π·(R·d²−d³/3)",
          math.isclose(antes - volumen(), quitado, rel_tol=0.001),
          f"esperado quitado={quitado:.6f}; obtenido={antes - volumen():.6f} mm³")
    comprobar_volumen("chaflán: volumen del cilindro menos el anillo triangular", math.pi * 100 * 40 - quitado)

    panel = A.abrir(v, "rosca")
    elegidos = elegir_punto(panel, "caras", (10 / math.sqrt(2), -10 / math.sqrt(2), 20))
    A.reg(AR, "rosca: clic elige la cara cilíndrica", len(elegidos) == 1
          and elegidos[0]["ref"].get("firma", {}).get("geom") == "cilindro",
          [h["ref"] for h in elegidos])
    if panel.seccion is not None and not panel.seccion.boton.isChecked():
        pulsar(panel.seccion.boton)
    # La clase automática 6g tornea el diámetro; el perfil básico conserva el Ø20/Ø24 pedido.
    combo = panel.widgets["clase_iso_metrica"]
    for zona in v.findChildren(QScrollArea):
        if zona.isAncestorOf(combo):
            zona.ensureWidgetVisible(combo)
    QTest.keyClick(combo, Qt.Key_Home)
    for _ in range(combo.findData("")):
        QTest.keyClick(combo, Qt.Key_Down)
    QTest.keyClick(combo, Qt.Key_Tab)
    A.esperar(150)
    A.reg(AR, "rosca: teclado elige Sin clase (perfil básico), conserva el diámetro nominal",
          panel.valores["clase_iso_metrica"] == "", combo.currentText())
    casilla = panel.widgets["modelada"]
    for zona in v.findChildren(QScrollArea):
        if zona.isAncestorOf(casilla):
            zona.ensureWidgetVisible(casilla)
    QTest.mouseClick(casilla, Qt.LeftButton, Qt.NoModifier, QPoint(8, 7))
    A.esperar(150)
    A.reg(AR, "rosca: clic tilda Modelado, Longitud completa y tamaño automático",
          panel.valores["modelada"] and panel.valores["largo_completo"]
          and panel.valores["tam_iso_metrica"] == "auto", str({k: panel.valores[k]
          for k in ("modelada", "largo_completo", "tam_iso_metrica", "clase_iso_metrica")}))
    antes = volumen()
    if not aceptar(panel, "rosca"):
        return
    comprobar_solido("rosca modelada")
    A.reg(AR, "rosca modelada: volumen menor al cilindro chaflanado", 0 < volumen() < antes,
          f"antes={antes:.6f}; después={volumen():.6f} mm³")
    comprobar_recalculo(10, "radio_10_inicial")

    cambiar_cota("12", 12, "radio_12")
    valor_invalido()
    v.resize(800, 520)
    A.esperar(500)
    A.reg(AR, "ventana real redimensionada a 800×520", v.width() == 800 and v.height() == 520,
          f"{v.width()}×{v.height()}")
    cambiar_cota("10", 10, "radio_10_800")
    paneles_chicos()
    guardar_reabrir()


try:
    A.correr(AR, construir)
finally:
    A.reg(AR, "ninguna excepción escapó de un slot de Qt", not A.ERRORES,
          f"{len(A.ERRORES)}: {A.ERRORES}")
    A.guardar_registro("pieza_revolucion")
    fallas = [r for r in A.REGISTRO if not r["ok"]]
    print(f"\n=== {len(A.REGISTRO)} comprobaciones, {len(fallas)} con ✗ ===", flush=True)
    v.doc.modificado = False
    v.close()
sys.exit(1 if fallas else 0)

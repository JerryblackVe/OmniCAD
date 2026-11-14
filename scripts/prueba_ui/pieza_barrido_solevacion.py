# -*- coding: utf-8 -*-
"""Dos cuerpos paramétricos por Barrido y Solevación, de principio a fin.

La API prepara la geometría de los bocetos, las anclas y el plano desfasado.
Cotas, selecciones, aceptación y edición usan eventos simulados a la ventana.
La gemela se arma desde cero; el historial se prueba antes de Nuevo porque
el archivo .omnicad no guarda los pasos de deshacer (como pieza_revolucion).
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
from PySide6.QtWidgets import QAbstractButton, QFileDialog, QScrollArea

AR = "PIEZA·BARRIDO·SOLEVACIÓN"
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


def entrar_boceto(nombre):
    abrir_paso(next(o.id for o in v.doc.operaciones if o.nombre == nombre))
    activo = v.modo_boceto.activo and v.modo_boceto.lienzo is not None
    A.reg(AR, f"{nombre}: doble clic en el timeline abre el boceto", activo)
    if not activo:
        raise RuntimeError(f"No se abrió el boceto {nombre}")
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


def acotar(lienzo, punto, ubicacion, texto, tipo):
    antes = set(lienzo.b.cotas)
    lienzo.set_herramienta("cota")
    # En un círculo, el primer clic ya abre la caja de diámetro (boceto_cotas).
    puntos = (punto,) if ubicacion is None else (punto, ubicacion)
    for lugar in puntos:
        QTest.mouseClick(lienzo, Qt.LeftButton, Qt.NoModifier, lienzo.a_px(*lugar).toPoint())
        A.esperar(100)
    abierta = lienzo.entrada is not None and lienzo.entrada.isVisible()
    if abierta:
        teclear(lienzo.entrada.campos[0], texto, enter=True)
    nueva = next((c for c in lienzo.b.cotas.values() if c.id not in antes), None)
    A.reg(AR, f"cota {texto}: clic, ubicar si es lineal y teclear Enter",
          abierta and nueva is not None and nueva.expresion == texto
          and nueva.tipo == tipo and not nueva.referencia
          and math.isclose(lienzo.b.medir(nueva), float(texto), abs_tol=0.001),
          f"caja abierta={abierta}; cota={nueva and (nueva.id, nueva.tipo, nueva.expresion, nueva.referencia)}")
    return nueva.id if nueva else None


def abrir_cota(lienzo, ident):
    lienzo.set_herramienta("seleccionar")
    lienzo.grab()  # actualiza las zonas de los textos antes del doble clic
    zona = lienzo._zonas_cotas.get(ident)
    if zona is None:
        raise RuntimeError(f"La cota {ident} no tiene zona visible de doble clic")
    QTest.mouseDClick(lienzo, Qt.LeftButton, Qt.NoModifier, zona.center().toPoint())
    A.esperar(150)
    abierta = lienzo.entrada is not None and lienzo.entrada.isVisible()
    A.reg(AR, "doble clic en la cota abre la caja", abierta, f"cota={ident}")
    return lienzo.entrada.campos[0] if abierta else None


def elegir_punto(panel, clave, punto, bocetos):
    fila = panel.widgets[clave]
    pulsar(fila.mas if clave == "secciones" else fila.boton)
    pos = v.visor.proyectar(A.np.array(punto, float))
    if pos is None or not v.visor.rect().contains(pos.toPoint()):
        raise RuntimeError(f"El punto de selección {punto} queda fuera del visor")
    QTest.mouseClick(v.visor, Qt.LeftButton, Qt.NoModifier, pos.toPoint())
    A.esperar(250)
    referencias = [h["ref"] for h in panel.valores.get(clave) or []]
    esperados = [next(o.id for o in v.doc.operaciones if o.nombre == n) for n in bocetos]
    tipo = "curva_boceto" if clave == "ruta" else "perfil"
    A.reg(AR, f"clic en el visor elige {clave} en orden {bocetos}",
          [r.get("boceto") for r in referencias] == esperados
          and all(r.get("tipo") == tipo for r in referencias), referencias)


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


def preparar_ruta(sesion):
    llamar(sesion, "create_sketch", name="Ruta", plane="YZ")
    datos = llamar(sesion, "draw_line", sketch="Ruta", start_x=0, start_y=0, end_x=0, end_y=40)
    linea = datos["entities"][0]["id"]
    llamar(sesion, "add_constraint", sketch="Ruta", type="vertical", entities=[linea])
    return linea


def preparar_circulo(sesion, nombre, plano, x, diametro):
    llamar(sesion, "create_sketch", name=nombre, plane=plano)
    datos = llamar(sesion, "draw_circle", sketch=nombre, center_x=x, center_y=0, radius=diametro / 2)
    if x:
        llamar(sesion, "add_constraint", sketch=nombre, type="fix", entities=[datos["points"][0]])
    return datos["entities"][0]["id"]


def preparar_rectangulo(sesion, ancho):
    llamar(sesion, "create_sketch", name="Base", plane="XY")
    datos = llamar(sesion, "draw_rectangle", sketch="Base", x1=50, y1=-10, x2=50 + ancho, y2=10)
    llamar(sesion, "add_constraint", sketch="Base", type="fix", entities=[datos["points"][0]])
    return [e["id"] for e in datos["entities"]]


def gemela(diametro, ancho):
    sesion = api.Sesion()
    linea = preparar_ruta(sesion)
    llamar(sesion, "add_dimension", sketch="Ruta", type="distance", entities=[linea], value="40")
    circulo = preparar_circulo(sesion, "Perfil", "XY", 0, diametro)
    llamar(sesion, "add_dimension", sketch="Perfil", type="diameter", entities=[circulo], value=str(diametro))
    llamar(sesion, "sweep", sketch="Perfil", path_sketch="Ruta", chain=True)
    lados = preparar_rectangulo(sesion, ancho)
    llamar(sesion, "add_dimension", sketch="Base", type="distance", entities=[lados[2]], value=str(ancho))
    llamar(sesion, "add_dimension", sketch="Base", type="distance", entities=[lados[1]], value="20")
    llamar(sesion, "create_construction_plane", plane="XY", offset=30, name="Plano30")
    circulo = preparar_circulo(sesion, "Seccion", "Plano30", 60, 10)
    llamar(sesion, "add_dimension", sketch="Seccion", type="diameter", entities=[circulo], value="10")
    llamar(sesion, "loft", sketches=["Base", "Seccion"], chain=True)
    return sesion


def medidas(sesion):
    cuerpos = llamar(sesion, "get_physical_properties")["bodies"]
    return sorted(cuerpos, key=lambda c: c["bounding_box"]["min"][0])


def comprobar_barrido(diametro, etiqueta):
    cuerpo = medidas(api.Sesion(v.doc))[0]
    esperado = math.pi * (diametro / 2)**2 * 40
    A.reg(AR, f"{etiqueta}: barrido π·({diametro}/2)²·40 (±0,1 %)",
          math.isclose(cuerpo["volume"], esperado, rel_tol=0.001),
          f"esperado={esperado:.6f}; obtenido={cuerpo['volume']:.6f} mm³")
    tamano = cuerpo["bounding_box"]["size"]
    A.reg(AR, f"{etiqueta}: caja del barrido {diametro}×{diametro}×40",
          all(math.isclose(a, b, abs_tol=0.001) for a, b in zip(tamano, (diametro, diametro, 40), strict=True)), tamano)


def comprobar_recalculo(diametro, ancho, etiqueta):
    actual = api.Sesion(v.doc)
    referencia = gemela(diametro, ancho)
    obtenidos, esperados = medidas(actual), medidas(referencia)
    A.reg(AR, f"{etiqueta}: dos cuerpos, cada uno UN sólido válido",
          len(v.doc.estado_final.cuerpos) == 2
          and all(len(geo.solidos(c.forma)) == 1 and geo.es_valida(c.forma)
                  for c in v.doc.estado_final.cuerpos.values()), A.cuerpos_resumen(v))
    pasos = llamar(actual, "get_timeline")["steps"]
    otros = llamar(referencia, "get_timeline")["steps"]
    malos = [(p["name"], p["status"], p["message"]) for p in pasos if p["status"] != "ok"]
    A.reg(AR, f"{etiqueta}: siete pasos sin errores, mismos nombres, tipos y orden que la gemela",
          len(pasos) == 7 and not malos
          and [(p["name"], p["type"]) for p in pasos] == [(p["name"], p["type"]) for p in otros],
          f"pasos={[(p['name'], p['type']) for p in pasos]}; errores={malos}")
    for nombre, indice in (("Barrido", 0), ("Solevación", 1)):
        obtenido = obtenidos[indice] if len(obtenidos) > indice else None
        esperado = esperados[indice]
        igual = obtenido is not None and math.isclose(obtenido["volume"], esperado["volume"], rel_tol=0.001)
        A.reg(AR, f"{etiqueta}: {nombre}, volumen igual a gemela API (±0,1 %)", igual,
              f"esperado={esperado['volume']}; obtenido={obtenido and obtenido['volume']} mm³")
        caja_igual = obtenido is not None and all(
            math.isclose(a, b, abs_tol=0.001)
            for clave in ("min", "max", "size")
            for a, b in zip(obtenido["bounding_box"][clave], esperado["bounding_box"][clave], strict=True))
        A.reg(AR, f"{etiqueta}: {nombre}, caja y posición iguales a gemela API", caja_igual,
              f"esperado={esperado['bounding_box']}; obtenido={obtenido and obtenido['bounding_box']}")
    comprobar_barrido(diametro, etiqueta)
    solevado = obtenidos[1] if len(obtenidos) == 2 else None
    A.reg(AR, f"{etiqueta}: Solevación, caja Z = 30 mm", solevado is not None
          and math.isclose(solevado["bounding_box"]["size"][2], 30, abs_tol=0.001),
          solevado and solevado["bounding_box"])
    minimo, maximo = math.pi * 5**2 * 30, ancho * 20 * 30
    A.reg(AR, f"{etiqueta}: cilindro Ø10×30 < Solevación < prisma {ancho}×20×30",
          solevado is not None and minimo < solevado["volume"] < maximo,
          f"mínimo={minimo:.6f}; obtenido={solevado and solevado['volume']}; máximo={maximo}")
    v.visor.vista("iso")
    v.visor.encuadrar()
    A.esperar(200)
    foto(etiqueta)


def cambiar_cota(nombre, ident, texto):
    lienzo = entrar_boceto(nombre)
    campo = abrir_cota(lienzo, ident)
    if campo is not None:
        teclear(campo, texto, enter=True)
        cota = lienzo.b.cotas[ident]
        A.reg(AR, f"{nombre}: acepta cota «{texto}»", cota.expresion == texto and not cota.referencia
              and math.isclose(lienzo.b.medir(cota), float(texto), abs_tol=0.001),
              f"expresión={cota.expresion}; medida={lienzo.b.medir(cota)}")
    foto(f"cota_{nombre}_{texto}")
    salir_boceto()


def valor_invalido(ident):
    antes = A.cuerpos_resumen(v)
    pasos = llamar(api.Sesion(v.doc), "get_timeline")
    lienzo = entrar_boceto("Perfil")
    cota = lienzo.b.cotas[ident]
    expresion, medida = cota.expresion, lienzo.b.medir(cota)
    campo = abrir_cota(lienzo, ident)
    if campo is not None:
        teclear(campo, "abc", enter=True)
        abierta = lienzo.entrada is not None and lienzo.entrada.isVisible()
        estilo, mensaje = campo.styleSheet(), v.timeline.estado.toolTip()
        A.reg(AR, "«abc» queda en rojo, con mensaje en el timeline y caja abierta",
              abierta and "#5c2a2d" in estilo.lower() and "abc" in mensaje.lower(),
              f"abierta={abierta}; estilo={estilo!r}; mensaje={mensaje!r}")
        foto("cota_abc")
        cota = lienzo.b.cotas[ident]
        A.reg(AR, "«abc» no cambia la cota ni su medida", cota.expresion == expresion
              and math.isclose(lienzo.b.medir(cota), medida, abs_tol=1e-6),
              f"antes={expresion!r}/{medida}; después={cota.expresion!r}/{lienzo.b.medir(cota)}")
        if abierta:
            QTest.keyClick(campo, Qt.Key_Escape)
    salir_boceto()
    A.reg(AR, "«abc» no cambia volúmenes ni parámetros del timeline", A.cuerpos_resumen(v) == antes
          and llamar(api.Sesion(v.doc), "get_timeline") == pasos,
          f"antes={antes}; después={A.cuerpos_resumen(v)}")


def paneles_chicos():
    antes = A.cuerpos_resumen(v)
    pasos = llamar(api.Sesion(v.doc), "get_timeline")
    for op in [o for o in v.doc.operaciones if o.TIPO in ("barrido", "solevacion")]:
        abrir_paso(op.id)
        panel = v.panel
        A.reg(AR, f"800×520: doble clic abre {op.nombre}", panel is not None)
        if panel is None:
            continue
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
                  v.width() == 800 and v.height() == 520 and dentro and marco.contains(rect_panel),
                  f"lienzo={marco}; panel={rect_panel}; botón={rect_boton}")
        foto(f"800_{panel.comando.CLAVE}")
        pulsar(boton(panel, "Cancelar"))
        A.reg(AR, f"800×520 · {op.nombre}: Cancelar cierra sin cambiar cuerpos ni pasos",
              v.panel is None and A.cuerpos_resumen(v) == antes
              and llamar(api.Sesion(v.doc), "get_timeline") == pasos)


def cadena():
    antes = A.cuerpos_resumen(v)
    pasos = llamar(api.Sesion(v.doc), "get_timeline")
    cuentas = []
    for clave, tecla in (("deshacer", Qt.Key_Z), ("rehacer", Qt.Key_Y)):
        cantidad, disparos = 0, []
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
    A.reg(AR, "rehacer recupera ambos cuerpos, volúmenes y timeline completos",
          A.cuerpos_resumen(v) == antes and llamar(api.Sesion(v.doc), "get_timeline") == pasos,
          f"deshacer/rehacer={cuentas}; antes={antes}; después={A.cuerpos_resumen(v)}")
    comprobar_recalculo(8, 24, "rehacer")


def guardar_reabrir():
    ruta = Path(tempfile.mkdtemp(prefix="pieza_barrido_solevacion_", dir=A.SALIDA)) / "dos_cuerpos.omnicad"
    QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: (str(ruta), ""))
    QFileDialog.getOpenFileName = staticmethod(lambda *a, **k: (str(ruta), ""))
    antes = A.cuerpos_resumen(v)
    pasos = llamar(api.Sesion(v.doc), "get_timeline")
    v.acciones["guardar"].trigger()
    A.esperar(500)
    A.reg(AR, "Guardar de la ventana crea .omnicad", ruta.exists() and ruta.stat().st_size > 0, ruta)
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
    comprobar_recalculo(8, 24, "reabierta")


def construir():
    A.reg(AR, "documento vacío en ventana 1280×720", not v.doc.operaciones
          and v.width() == 1280 and v.height() == 720, f"{v.width()}×{v.height()}")
    preparar_ruta(s)
    v.doc.recalcular()
    lienzo = entrar_boceto("Ruta")
    acotar(lienzo, (0, 20), (8, 20), "40", "distancia")
    foto("ruta_cota_40")
    salir_boceto()
    preparar_circulo(s, "Perfil", "XY", 0, 6)
    v.doc.recalcular()
    lienzo = entrar_boceto("Perfil")
    cota_diametro = acotar(lienzo, (0, 3), None, "6", "diametro")
    foto("perfil_cota_6")
    salir_boceto()
    v.visor.vista("iso")
    v.visor.encuadrar()
    A.esperar(250)
    panel = A.abrir(v, "barrido")
    elegir_punto(panel, "perfiles", (0, 0, 0), ["Perfil"])
    elegir_punto(panel, "ruta", (0, 0, 20), ["Ruta"])
    if not aceptar(panel, "barrido"):
        return
    comprobar_barrido(6, "inicial")

    preparar_rectangulo(s, 20)
    v.doc.recalcular()
    lienzo = entrar_boceto("Base")
    cota_ancho = acotar(lienzo, (60, 10), (60, 16), "20", "distancia")
    acotar(lienzo, (70, 0), (78, 0), "20", "distancia")
    foto("base_cotas_20")
    salir_boceto()
    llamar(s, "create_construction_plane", plane="XY", offset=30, name="Plano30")
    preparar_circulo(s, "Seccion", "Plano30", 60, 10)
    v.doc.recalcular()
    lienzo = entrar_boceto("Seccion")
    acotar(lienzo, (60, 5), None, "10", "diametro")
    foto("seccion_cota_10")
    salir_boceto()
    v.visor.vista("iso")
    v.visor.encuadrar()
    A.esperar(250)
    panel = A.abrir(v, "solevacion")
    elegir_punto(panel, "secciones", (60, 0, 0), ["Base"])
    # Con la vista de toda la pieza el disco mide ~20 px y su punto y su curva (tolerancia de clic) lo cubren entero:
    # se acerca la vista al disco para que el clic caiga en el perfil, lejos del centro y del borde.
    v.visor.encuadrar(A.np.array([(55, -5, 30), (65, 5, 30)], float))
    A.esperar(250)
    elegir_punto(panel, "secciones", (62.5, -1.5, 30), ["Base", "Seccion"])
    if not aceptar(panel, "solevacion"):
        return
    comprobar_recalculo(6, 20, "inicial_dos_cuerpos")
    valor_invalido(cota_diametro)
    cambiar_cota("Perfil", cota_diametro, "8")
    comprobar_recalculo(8, 20, "diametro_8")
    v.resize(800, 520)
    A.esperar(500)
    A.reg(AR, "ventana real redimensionada a 800×520", v.width() == 800 and v.height() == 520,
          f"{v.width()}×{v.height()}")
    cambiar_cota("Base", cota_ancho, "24")
    comprobar_recalculo(8, 24, "lado_24_800")
    paneles_chicos()
    guardar_reabrir()


try:
    A.correr(AR, construir)
finally:
    A.reg(AR, "ninguna excepción escapó de un slot de Qt", not A.ERRORES,
          f"{len(A.ERRORES)}: {A.ERRORES}")
    A.guardar_registro("pieza_barrido_solevacion")
    fallas = [r for r in A.REGISTRO if not r["ok"]]
    print(f"\n=== {len(A.REGISTRO)} comprobaciones, {len(fallas)} con ✗ ===", flush=True)
    v.doc.modificado = False
    v.close()
sys.exit(1 if fallas else 0)

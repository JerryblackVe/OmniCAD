# -*- coding: utf-8 -*-
"""Asistente IA como una persona: clic real en el botón de la barra, teclear en el campo (texto, vacío, enorme, pegar),
Enter, Mayús+Enter, Esc, Tab, Cancelar, cambiar de modo, biblioteca de prompts, chat nuevo y ventana chica (el campo y
Enviar tienen que entrar). IA-5: tarjeta de plan (Aplicar, Cancelar, Esc), Guiar, Cancelar con vuelta atrás,
«Deshacer este pedido» y el aviso de APP_BUSY con un comando abierto. IA-6: elegir «Claude Code (tu suscripción)» en
Preferencias (teclado y clic en Aceptar), ruta mala tecleada, y un pedido con el CLI simulado que entra por el puente en
vivo (encendido solo durante el pedido) con la tarjeta Aplicar. IA-9: clic en el clip, Ctrl+V de una imagen, arrastrar
archivos al chat, el 11.º rechazado, ✕ y las fichas en la ventana chica. IA-10: Preferencias llena «Modelo» con lo
que dice cada CLI (elegir con el teclado, escribir otro, Aceptar y reabrir). IA-11: «pinta la caja de rojo» usa
set_appearance (fuera del núcleo) en modo API con buscar_herramientas y en modo suscripción con call_tool. IA-12:
teclear las instrucciones propias (Preferencias) y las del proyecto (Chat), vacío, enorme, pegar, Tab, Esc, Aceptar,
reabrir, guardar y volver a abrir el archivo, el aviso y la ventana chica. IA-13: clic real en el visor sobre una cara,
la ficha 🎯 con su medida, «empalme de 2 mm en esto» con la ref del prompt, ✕, elegir otra cosa y la ventana chica.
IA-14: un pedido que crea una torre y gira la vista muestra Antes y Después con la misma cámara; clic y Enter la abren
grande, Esc la cierra, ventana chica, «Deshacer este pedido» y reabrir el chat. El proveedor es el falso: sin red ni
gasto."""
import asyncio
import json
import sys
import tempfile
import threading
from pathlib import Path

import arnes as A
import escena
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog, QLabel, QPushButton, QToolButton, QWidget

from omnicad import api
from omnicad.asistente import config, historial
from omnicad.asistente.proveedores.agente_local import AgenteLocal
from omnicad.asistente.proveedores.base import PedidoHerramienta, ProveedorFalso, Respuesta
from omnicad.servidor_mcp.puente_cliente import ClientePuente
from omnicad.servidor_mcp.servidor import crear_servidor

s, ids = escena.construir()
app, v = A.iniciar(s.doc)
AR = "ASISTENTE"
CAJA = PedidoHerramienta("h1", "create_box", {"length": 30, "width": 20, "height": 10})
CAJA2 = PedidoHerramienta("h2", "create_box", {"length": 10, "width": 10, "height": 40})


def esperar(p, ms=8000, aplicar=True):
    """Espera el fin del pedido; con `aplicar`, aprueba cada tarjeta de plan con un clic en Aplicar."""
    for _ in range(ms // 20):
        if not p.trabajando:
            return True
        if aplicar and p.tarjeta is not None:
            QTest.mouseClick(p.tarjeta.b_aplicar, Qt.LeftButton)
        QTest.qWait(20)
    return False


def esperar_tarjeta(p, ms=5000):
    for _ in range(ms // 20):
        if p.tarjeta is not None:
            QTest.qWait(30)                    # que se pinte antes de mirarla o hacerle clic
            return p.tarjeta
        QTest.qWait(20)
    return None


def textos(p):
    return [w.text() for w in p.lista.findChildren(QLabel)]


def botones_deshacer(p):
    return p.lista.findChildren(QPushButton, "deshacer_pedido")


def en_el_chat(w, p):
    """El widget se ve entero dentro del área visible del chat."""
    vp = p.area.viewport()
    caja = w.rect().translated(w.mapTo(vp, w.rect().topLeft()))
    return w.isVisible() and vp.rect().contains(caja)


def lineas(p):
    return [b.text() for b in p.lista.findChildren(QToolButton, "herramienta_asistente")]


def escribir(p, texto, tecla=None, mod=Qt.NoModifier):
    QTest.mouseClick(p.campo.viewport(), Qt.LeftButton)
    QTest.keyClick(p.campo, Qt.Key_A, Qt.ControlModifier)
    QTest.keyClick(p.campo, Qt.Key_Delete)
    if texto:
        QTest.keyClicks(p.campo, texto)
    if tecla is not None:
        QTest.keyClick(p.campo, tecla, mod)
    QTest.qWait(60)


def dentro(w, ventana):
    """El widget entero se ve dentro de la ventana (no quedó cortado ni afuera)."""
    caja = w.rect().translated(w.mapTo(ventana, w.rect().topLeft()))
    return w.isVisible() and ventana.rect().contains(caja)


class CliSimulado(AgenteLocal):
    """Hace lo que haría Claude Code: llama herramientas por el puente en vivo (TCP + token de puente.json). Con `meta`,
    como el CLI de verdad desde IA-11: por call_tool del `omnicad-mcp --meta-tools --modo vivo`."""

    def __init__(self, archivo, llamadas, meta=False):
        self.tipo, self.nombre, self.sesion, self.proceso = "claude_code", "Claude Code", None, None
        self.archivo, self.llamadas, self.respuestas, self.puente_visto = archivo, llamadas, [], None
        self.meta = meta

    def correr(self, texto, sistema, modo, al_evento=None, cancelado=None, adjuntos=()):
        cliente = ClientePuente(self.archivo)
        self.puente_visto = cliente.conectar()
        servidor = crear_servidor(modo="vivo", cliente=cliente, meta=True, herramientas=[]) if self.meta else None
        for nombre, args in self.llamadas:
            if servidor is None:
                r = cliente.llamar(nombre, args)
            else:
                r = json.loads(asyncio.run(servidor.call_tool("call_tool", {"name": nombre, "args": args}))
                               .content[0].text)
            self.respuestas.append(r)
            al_evento("herramienta", {"nombre": nombre, "args": args, "respuesta": r})
        if servidor is not None:
            servidor.cerrar()
        cliente.cerrar()
        al_evento("texto", "Listo: caja creada.")
        self.sesion = "sesion-simulada"
        return {"motivo": "fin", "uso": {"entrada": 0, "salida": 0, "costo_usd": None}}


def abrir_historial(p):
    """Clic en el botón Chat (el menú no bloquea en la prueba) y en «Historial de chats»: el diálogo que aparece."""
    QTest.mouseClick(p.b_chat, Qt.LeftButton)
    A.esperar(50)
    next(a for a in p.b_chat.menu().actions() if a.text() == "Historial de chats").trigger()
    A.esperar(150)
    return next((d for d in p.findChildren(QDialog, "historial_asistente") if d.isVisible()), None)


def historial_abierto(p):
    """Hay un historial a la vista (al cerrarse se borra solo: no se le pregunta al widget viejo)."""
    return any(d.isVisible() for d in p.findChildren(QDialog, "historial_asistente"))


def doble_clic(lista, fila):
    caja = lista.visualItemRect(lista.item(fila)).center()
    QTest.mouseClick(lista.viewport(), Qt.LeftButton, Qt.NoModifier, caja)
    QTest.mouseDClick(lista.viewport(), Qt.LeftButton, Qt.NoModifier, caja)
    A.esperar(100)


def historial_chats(p, guardado, n_lineas):
    """IA-7 como una persona: Chat › Historial, doble clic en el chat guardado, seguirlo tecleando, Borrar… con la
    confirmación (Supr y botón) y el diálogo en la ventana chica."""
    d = abrir_historial(p)
    A.reg(AR, "Chat › Historial de chats abre la lista con el chat guardado arriba",
          d is not None and d.lista.count() >= 1 and d.lista.item(0).data(Qt.UserRole) == guardado,
          d and [d.lista.item(i).text() for i in range(d.lista.count())])
    if d is None:
        return
    A.foto(d, "asistente_historial")
    doble_clic(d.lista, 0)
    A.reg(AR, "doble clic en el chat lo carga: se ven los mensajes y las herramientas del pedido",
          p.id_chat == guardado and not historial_abierto(p) and len(lineas(p)) == n_lineas
          and any("escribí para seguirlo" in t for t in textos(p)), f"lineas={lineas(p)}")
    falso = ProveedorFalso([Respuesta(texto="Sigo con lo de antes.")])
    p.crear_proveedor = lambda cfg: falso
    n = len(p.mensajes)
    escribir(p, "y ahora segui", Qt.Key_Return)
    esperar(p)
    A.reg(AR, "seguir el chat cargado: el modelo recibe lo anterior y se guarda en el mismo archivo",
          len(falso.recibidos[0][0]) == n + 1 and p.id_chat == guardado
          and len(historial.cargar(guardado)["mensajes"]) == n + 2, f"recibió {len(falso.recibidos[0][0])} de {n + 1}")
    p.crear_proveedor = lambda cfg: ProveedorFalso(p.guion)
    # Borrar: Supr y botón Borrar…, cada uno con la pregunta de confirmación (en la prueba contesta Aceptar).
    otro = historial.guardar([{"rol": "usuario", "contenido": [{"tipo": "texto", "texto": "chat para borrar"}]}],
                             "explicar", "anthropic", "")
    d = abrir_historial(p)
    previos = len(A.MODALES)
    d.lista.setCurrentRow(0)
    QTest.mouseClick(d.lista.viewport(), Qt.LeftButton, Qt.NoModifier, d.lista.visualItemRect(d.lista.item(0)).center())
    QTest.keyClick(d.lista, Qt.Key_Delete)
    A.esperar(50)
    A.reg(AR, "Supr en el historial pregunta y borra el chat elegido",
          len(A.MODALES) > previos and A.MODALES[previos][0] == "question"
          and all(c["id"] != otro for c in historial.listar()), A.MODALES[previos:])
    fila = next(i for i in range(d.lista.count()) if d.lista.item(i).data(Qt.UserRole) == guardado)
    QTest.mouseClick(d.lista.viewport(), Qt.LeftButton, Qt.NoModifier,
                     d.lista.visualItemRect(d.lista.item(fila)).center())
    QTest.mouseClick(d.b_borrar, Qt.LeftButton)
    A.esperar(50)
    A.reg(AR, "Borrar… pregunta y saca el chat de la lista; el chat abierto se guardará como nuevo",
          all(c["id"] != guardado for c in historial.listar()) and p.id_chat is None
          and all(d.lista.item(i).data(Qt.UserRole) != guardado for i in range(d.lista.count())))
    QTest.keyClick(d, Qt.Key_Escape)
    A.esperar(50)
    A.reg(AR, "Esc cierra el historial", not historial_abierto(p))
    # Ventana chica: el diálogo y sus botones entran en la pantalla.
    v.resize(800, 520)
    A.esperar(300)
    d = abrir_historial(p)
    pantalla = QApplication.primaryScreen().availableGeometry()
    A.reg(AR, "ventana 800x520: el historial y sus botones se ven enteros",
          d is not None and pantalla.contains(d.frameGeometry()) and dentro(d.b_abrir, d) and dentro(d.b_borrar, d),
          d and f"dialogo={d.frameGeometry()} pantalla={pantalla}")
    if d is not None:
        A.foto(d, "asistente_historial_800x520")
        d.close()
    v.resize(1900, 1000)
    A.esperar(200)
    QTest.mouseClick(p.b_nuevo, Qt.LeftButton)
    A.esperar(50)


def elegir_con_teclado(combo, dato):
    """Como la persona: foco en el combo y flechas hasta la opción (Arriba hasta la primera, después Abajo)."""
    combo.setFocus()
    for _ in range(combo.count()):
        QTest.keyClick(combo, Qt.Key_Up)
    for _ in range(combo.count()):
        if combo.currentData() == dato:
            break
        QTest.keyClick(combo, Qt.Key_Down)
    A.esperar(30)
    return combo.currentData() == dato


def modelos_en_preferencias():
    """IA-10: el campo Modelo se llena solo con lo que dice cada CLI instalado (OpenCode y Codex se preguntan de
    verdad, sin gastar: es un listado local); los proveedores por API devuelven una lista fija (sin red)."""
    from omnicad.asistente import modelos
    from omnicad.ui.preferencias import DialogoPreferencias
    real = modelos.modelos_disponibles
    modelos.modelos_disponibles = lambda proveedor, *a, **k: real(proveedor, *a, **k) if proveedor in \
        config.AGENTES_LOCALES else {"modelos": [], "fabrica": "x", "variantes": {}, "motivo": "sin red en la prueba"}
    guardado = {k: v.prefs[f"asistente/{k}"] for k in ("proveedor", "modelo", "variante")}

    def abrir():
        dlg = DialogoPreferencias(v.prefs, v, "asistente")
        dlg.aplicado.connect(v.aplicar_preferencias)
        dlg.show()
        A.esperar(200)
        return dlg

    def esperar_lista(dlg, ms=30000):
        for _ in range(ms // 50):
            if dlg.b_modelos.isEnabled():
                return True
            QTest.qWait(50)
        return False

    try:
        dlg = abrir()
        proveedor, modelo, variante = (dlg.controles[f"asistente/{k}"] for k in ("proveedor", "modelo", "variante"))
        for tipo, minimo in (("claude_code", 7), ("codex", 2), ("opencode", 2)):
            elegido = elegir_con_teclado(proveedor, tipo)
            listo = esperar_lista(dlg)
            items = [modelo.itemText(i) for i in range(modelo.count())]
            A.reg(AR, f"Preferencias: al elegir {tipo} con el teclado, «Modelo» se llena solo con lo que dice el CLI",
                  elegido and listo and len(items) > minimo and items[0].startswith("de fábrica")
                  and dlg.estado_modelos.text().endswith("modelos"),
                  f"{dlg.estado_modelos.text()} · {items[:4]}")
            A.foto(dlg, f"asistente_pref_modelos_{tipo}")
        # Codex de nuevo, para elegir modelo y esfuerzo con el teclado (la lista ya está en memoria).
        elegir_con_teclado(proveedor, "codex")
        esperar_lista(dlg)
        modelo.setFocus()
        QTest.keyClick(modelo, Qt.Key_Down)                  # del «de fábrica» al primer modelo de la lista
        A.esperar(50)
        esfuerzos = [variante.itemText(i) for i in range(variante.count())]
        A.reg(AR, "Codex: flecha abajo en Modelo elige el primero y Esfuerzo ofrece sus niveles",
              modelo.currentIndex() == 1 and "high" in esfuerzos, f"{modelo.currentText()} · {esfuerzos}")
        variante.setFocus()
        QTest.keyClick(variante.lineEdit(), Qt.Key_A, Qt.ControlModifier)
        QTest.keyClicks(variante.lineEdit(), "high")
        A.reg(AR, "Esfuerzo: escribir «high» a mano", variante.currentText() == "high", variante.currentText())
        elegido = modelo.currentText()
        QTest.mouseClick(dlg.b_aceptar, Qt.LeftButton)
        A.esperar(150)
        A.reg(AR, "Aceptar guarda Codex con el modelo elegido y el esfuerzo",
              (v.prefs["asistente/proveedor"], v.prefs["asistente/modelo"], v.prefs["asistente/variante"])
              == ("codex", elegido, "high"), (v.prefs["asistente/modelo"], v.prefs["asistente/variante"]))
        dlg = abrir()
        modelo = dlg.controles["asistente/modelo"]
        esperar_lista(dlg)
        A.reg(AR, "reabrir Preferencias: el modelo y el esfuerzo siguen ahí",
              modelo.currentText() == elegido and dlg.controles["asistente/variante"].currentText() == "high")
        QTest.mouseClick(modelo.lineEdit(), Qt.LeftButton)
        QTest.keyClick(modelo.lineEdit(), Qt.Key_A, Qt.ControlModifier)
        QTest.keyClicks(modelo.lineEdit(), "gpt-otro-escrito")
        QTest.mouseClick(dlg.b_aceptar, Qt.LeftButton)
        A.esperar(150)
        A.reg(AR, "escribir un modelo que no está en la lista y Aceptar lo guarda tal cual",
              v.prefs["asistente/modelo"] == "gpt-otro-escrito", v.prefs["asistente/modelo"])
        dlg = abrir()
        dlg.resize(800, 520)
        A.esperar(200)
        modelo = dlg.controles["asistente/modelo"]
        pantalla = QApplication.primaryScreen().availableGeometry()
        A.reg(AR, "Preferencias achicada (se pide 800x520): Modelo, ↻ y Aceptar se ven enteros y la página del "
              "Asistente no la ensancha", dentro(modelo, dlg) and dentro(dlg.b_modelos, dlg) and dentro(dlg.b_aceptar, dlg)
              and pantalla.contains(dlg.frameGeometry())
              and dlg.pila.currentWidget().minimumSizeHint().width() <= max(
                  dlg.pila.widget(i).minimumSizeHint().width() for i in range(dlg.pila.count()) if i != dlg.pila.currentIndex()),
              f"dialogo={dlg.size()} página={dlg.pila.currentWidget().minimumSizeHint()}")
        A.foto(dlg, "asistente_pref_modelos_800x520")
        QTest.mouseClick(dlg.b_cancelar, Qt.LeftButton)
    finally:
        modelos.modelos_disponibles = real
        for k, valor in guardado.items():
            v.prefs[f"asistente/{k}"] = valor
        if v.asistente is not None:
            v.asistente.actualizar_cabecera()


def suscripcion(p):
    """IA-6: Preferencias › Asistente IA con el teclado, ruta mala y un pedido con el CLI simulado por el puente."""
    from PySide6.QtCore import QTimer
    from omnicad.ui.preferencias import DialogoPreferencias
    dlg = DialogoPreferencias(v.prefs, v, "asistente")
    dlg.aplicado.connect(v.aplicar_preferencias)
    dlg.show()
    A.esperar(300)
    combo = dlg.controles["asistente/proveedor"]
    QTest.mouseClick(combo, Qt.LeftButton)
    A.esperar(150)
    QTest.keyClick(combo.view(), Qt.Key_Escape)
    for _ in range(combo.count()):
        if combo.currentData() == "claude_code":
            break
        QTest.keyClick(combo, Qt.Key_Down)
    estado = dlg.estado_clave.text()
    ruta = dlg.controles["asistente/ruta_claude_code"]
    A.reg(AR, "Preferencias: elegir «Claude Code (tu suscripción)» con el teclado explica que usa el CLI logueado",
          combo.currentData() == "claude_code" and "suscripción" in estado and "no ve ni guarda" in estado, estado[:90])
    A.reg(AR, "Preferencias: la ruta del ejecutable aparece autodetectada (o dice que no está)",
          bool(ruta.placeholderText()) and ruta.text() == "", ruta.placeholderText())
    QTest.mouseClick(ruta, Qt.LeftButton)
    QTest.keyClicks(ruta, "D:/no/existe/claude.exe")
    A.foto(dlg, "asistente_pref_suscripcion")
    QTest.mouseClick(dlg.b_aceptar, Qt.LeftButton)
    A.esperar(200)
    A.reg(AR, "Aceptar guarda proveedor y ruta, y la cabecera del panel muestra Claude Code sin modelo",
          v.prefs["asistente/proveedor"] == "claude_code" and v.prefs["asistente/ruta_claude_code"] ==
          "D:/no/existe/claude.exe" and p.etiqueta_modelo.text() == "Claude Code (tu suscripción)",
          p.etiqueta_modelo.text())
    p.crear_proveedor = config.crear_proveedor
    escribir(p, "caja", Qt.Key_Return)
    A.reg(AR, "con una ruta que no existe, el chat dice claro que no está instalado y dónde lo buscó",
          not p.trabajando and "no está instalado" in textos(p)[-1] and "D:/no/existe" in textos(p)[-1], textos(p)[-1])
    v.prefs["asistente/ruta_claude_code"] = ""

    import tempfile
    from pathlib import Path
    archivo = p.puente.archivo = Path(tempfile.mkdtemp(prefix="omnicad_puente_")) / "puente.json"  # no pisa el real
    cli = CliSimulado(archivo, [("get_scene_info", {}), ("create_box", {"length": 10, "width": 10, "height": 10})])
    p.crear_proveedor = lambda _cfg: cli
    p.modo.setCurrentIndex(p.modo.findData("hacer"))
    n = len(v.doc.operaciones)
    clics = []

    def aplicar():                           # adentro del bucle de la tarjeta, como la persona apretando Aplicar
        if p.tarjeta is not None and p.tarjeta.pendiente:
            clics.append(1)
            QTest.mouseClick(p.tarjeta.b_aplicar, Qt.LeftButton)

    reloj = QTimer(interval=150, timeout=aplicar)
    reloj.start()
    apagado_antes = not p.puente.activo and (v.puente is None or not v.puente.activo)
    escribir(p, "crea una caja de 10 mm", Qt.Key_Return)   # QTest.keyClicks con «á» tira el proceso
    esperar(p, aplicar=False)
    reloj.stop()
    A.reg(AR, "suscripción: con el puente apagado, el pedido lo enciende y el CLI llega a OmniCAD",
          apagado_antes and cli.puente_visto and [r["ok"] for r in cli.respuestas] == [True, True])
    A.reg(AR, "suscripción: el cambio pasa por la tarjeta Aplicar y la caja aparece con su línea en el chat",
          clics == [1] and len(v.doc.operaciones) == n + 1 and lineas(p)[-1].startswith("✓ create_box"),
          f"tarjetas={len(clics)} lineas={lineas(p)[-2:]}")
    A.reg(AR, "suscripción: al terminar el puente vuelve a apagarse y queda «Deshacer este pedido»",
          not p.puente.activo and not archivo.exists() and botones_deshacer(p)[-1].isEnabled())
    A.foto(v, "asistente_suscripcion")
    QTest.mouseClick(botones_deshacer(p)[-1], Qt.LeftButton)
    A.reg(AR, "suscripción: «Deshacer este pedido» saca la caja del CLI", len(v.doc.operaciones) == n)

    # IA-11: set_appearance no está en la lista corta del CLI: le llega por call_tool, con su nombre real en la tarjeta
    cli = CliSimulado(archivo, [("set_appearance", {"bodies": [primer_cuerpo()], "color": "#ff0000"})], meta=True)
    p.crear_proveedor = lambda _cfg: cli
    receta = color()
    clics.clear()
    reloj.start()
    escribir(p, "pinta la caja de rojo", Qt.Key_Return)
    esperar(p, aplicar=False)
    reloj.stop()
    A.reg(AR, "IA-11 suscripción: «pinta la caja de rojo» usa set_appearance por call_tool, con la tarjeta Aplicar",
          clics == [1] and [r["ok"] for r in cli.respuestas] == [True] and lineas(p)[-1].startswith("✓ set_appearance")
          and color() == [1.0, 0.0, 0.0], f"tarjetas={len(clics)} lineas={lineas(p)[-1:]} {cli.respuestas}")
    A.foto(v, "asistente_call_tool")
    QTest.mouseClick(botones_deshacer(p)[-1], Qt.LeftButton)
    A.reg(AR, "IA-11 suscripción: «Deshacer este pedido» saca el color", color() == receta)
    v.prefs["asistente/proveedor"] = "anthropic"
    p.actualizar_cabecera()
    p.crear_proveedor = lambda _cfg: ProveedorFalso(p.guion)


def adjuntables():
    """Un PDF, una imagen, un SVG y un DXF de prueba en una carpeta temporal."""
    import tempfile
    from pathlib import Path

    from PIL import Image

    from omnicad.io_archivos.dxf import escribir_dxf
    d = Path(tempfile.mkdtemp(prefix="omnicad_adjuntos_"))
    (d / "plano.pdf").write_bytes(b"%PDF-1.4\n%%EOF\n")
    Image.new("RGB", (300, 200), (30, 120, 200)).save(d / "foto.jpg")
    (d / "logo.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg" width="40mm" height="20mm" viewBox="0 0 40 20">'
                                '<rect x="2" y="2" width="36" height="16"/><circle cx="20" cy="10" r="6"/></svg>',
                                encoding="utf-8")
    escribir_dxf(d / "brida.dxf", [("circulo", (0, 0), 30), ("circulo", (0, 0), 10), ("circulo", (20, 0), 3)])
    return [str(d / n) for n in ("plano.pdf", "foto.jpg", "logo.svg", "brida.dxf")]


def fichas(p):
    """Las fichas en el orden en que se ven (las quitadas ya salieron de la fila aunque falte borrarlas)."""
    return [p.lay_fichas.itemAt(i).widget() for i in range(p.lay_fichas.count() - 1)]


def soltar(widget, rutas):
    """Arrastrar archivos del Explorador y soltarlos sobre `widget` (Qt pasa el evento al que acepta soltar)."""
    from PySide6.QtCore import QMimeData, QPointF, QUrl
    from PySide6.QtGui import QDragEnterEvent, QDropEvent
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(r) for r in rutas])
    centro = widget.rect().center()
    entrar = QDragEnterEvent(centro, Qt.CopyAction, mime, Qt.LeftButton, Qt.NoModifier)
    QApplication.sendEvent(widget, entrar)
    if entrar.isAccepted():
        QApplication.sendEvent(widget, QDropEvent(QPointF(centro), Qt.CopyAction, mime, Qt.LeftButton, Qt.NoModifier))
    A.esperar(80)
    return entrar.isAccepted()


def adjuntos_ui(p):
    """IA-9 como una persona: clic en el clip (el diálogo de archivos devuelve los elegidos), ✕, Ctrl+V de una imagen,
    arrastrar al chat, el 11.º rechazado y mandar el pedido con sus adjuntos."""
    from omnicad.ui import asistente as modulo
    rutas = adjuntables()
    elegidos = []
    original = modulo.QFileDialog.getOpenFileNames
    modulo.QFileDialog.getOpenFileNames = lambda *a: (elegidos.pop(0) if elegidos else [], "")
    try:
        p.adjuntos = []
        p._mostrar_fichas()
        A.reg(AR, "el clip está al lado del campo, con su ícono", p.b_clip.isVisible() and not p.b_clip.icon().isNull())
        elegidos.append(rutas)
        QTest.mouseClick(p.b_clip, Qt.LeftButton)
        A.esperar(150)
        A.reg(AR, "clic en el clip: PDF, JPG, SVG y DXF quedan como fichas arriba del campo con el contador",
              [a.clase for a in p.adjuntos] == ["pdf", "imagen", "svg", "dxf"] and len(fichas(p)) == 4
              and p.contador.text() == "4/10" and p.fila_adjuntos.isVisible(), p.contador.text())
        A.foto(v, "asistente_adjuntos_fichas")
        QTest.mouseClick(fichas(p)[0].b_quitar, Qt.LeftButton)
        A.esperar(80)
        A.reg(AR, "✕ en la ficha del PDF lo saca", [a.nombre for a in p.adjuntos] == ["foto.jpg", "logo.svg", "brida.dxf"]
              and p.contador.text() == "3/10", p.contador.text())
        from PySide6.QtGui import QColor, QImage
        imagen = QImage(120, 80, QImage.Format_RGB32)
        imagen.fill(QColor(220, 40, 40))
        QApplication.clipboard().setImage(imagen)
        escribir(p, "mira esto")
        QTest.keyClick(p.campo, Qt.Key_V, Qt.ControlModifier)
        A.esperar(80)
        A.reg(AR, "Ctrl+V con una imagen copiada la adjunta (PNG temporal) y no toca el texto",
              p.adjuntos[-1].nombre.startswith("pegada_") and p.campo.toPlainText() == "mira esto", p.campo.toPlainText())
        QApplication.clipboard().setText(" y el logo")
        QTest.keyClick(p.campo, Qt.Key_End)
        QTest.keyClick(p.campo, Qt.Key_V, Qt.ControlModifier)
        A.reg(AR, "Ctrl+V con texto sigue pegando texto", p.campo.toPlainText() == "mira esto y el logo"
              and len(p.adjuntos) == 4, p.campo.toPlainText())
        A.reg(AR, "arrastrar el PDF del Explorador y soltarlo sobre el chat lo adjunta",
              soltar(p.area.viewport(), rutas[:1]) and p.adjuntos[-1].nombre == "plano.pdf" and len(fichas(p)) == 5)
        elegidos.append(rutas * 2)
        QTest.mouseClick(p.b_clip, Qt.LeftButton)
        A.esperar(150)
        avisos = [t for t in textos(p) if "Máximo 10 adjuntos" in t]
        A.reg(AR, "más de 10: suma hasta el 10.º y del 11.º en adelante avisa claro",
              len(p.adjuntos) == 10 and p.contador.text() == "10/10" and len(avisos) == 3, avisos[:1])
        A.foto(v, "asistente_adjuntos_10")
        for _ in range(5):
            QTest.mouseClick(fichas(p)[-1].b_quitar, Qt.LeftButton)
            A.esperar(30)
        falso = ProveedorFalso([Respuesta(texto="Veo la foto, el logo y la brida.")])
        p.crear_proveedor = lambda _cfg: falso
        p.modo.setCurrentIndex(p.modo.findData("explicar"))
        QTest.keyClick(p.campo, Qt.Key_Return)
        esperar(p)
        recibido = falso.recibidos[0][0][-1]["contenido"] if falso.recibidos else []
        A.reg(AR, "Enter manda el texto con sus 5 adjuntos (imágenes, vistas previas y PDF) y las fichas se van",
              [b["tipo"] for b in recibido].count("imagen") == 4 and any(b["tipo"] == "documento" for b in recibido)
              and p.adjuntos == [] and not p.fila_adjuntos.isVisible()
              and any(t.startswith("Adjuntos: foto.jpg, logo.svg") for t in textos(p)), [b["tipo"] for b in recibido])
        guardado = historial.cargar(p.id_chat)["mensajes"][-2]["contenido"]
        A.reg(AR, "el historial guarda nombre, tipo y ruta de cada adjunto, no su contenido",
              all(b["tipo"] == "texto" for b in guardado) and any("insert_dxf(path=" in b["texto"] for b in guardado),
              [b["tipo"] for b in guardado])
        A.foto(v, "asistente_adjuntos_enviado")
    finally:
        modulo.QFileDialog.getOpenFileNames = original
        p.crear_proveedor = lambda _cfg: ProveedorFalso(p.guion)
    return rutas


def pegar(campo, texto):
    """Ctrl+V de verdad: el texto va al portapapeles y se pega con el teclado."""
    QApplication.clipboard().setText(texto)
    QTest.keyClick(campo, Qt.Key_V, Qt.ControlModifier)
    A.esperar(30)


def borrar_todo(campo):
    QTest.mouseClick(campo.viewport(), Qt.LeftButton)
    QTest.keyClick(campo, Qt.Key_A, Qt.ControlModifier)
    QTest.keyClick(campo, Qt.Key_Delete)


def instrucciones_ui(p):
    """IA-12: las propias en Preferencias › Asistente IA y las del proyecto en Chat › Instrucciones de este proyecto."""
    from omnicad.asistente import modelos
    from omnicad.io_archivos import proyecto
    from omnicad.timeline.documento import TOPE_INSTRUCCIONES, Documento
    from omnicad.ui.preferencias import DialogoPreferencias
    real = modelos.modelos_disponibles
    modelos.modelos_disponibles = lambda proveedor, *a, **k: {"modelos": [], "fabrica": "x", "variantes": {},
                                                              "motivo": "sin red en la prueba"}

    def abrir_pref():
        dlg = DialogoPreferencias(v.prefs, v, "asistente")
        dlg.show()
        A.esperar(150)
        return dlg, dlg.controles["asistente/instrucciones"]

    try:
        dlg, campo = abrir_pref()
        QTest.mouseClick(campo.viewport(), Qt.LeftButton)
        QTest.keyClicks(campo, "Explicame paso a paso")
        A.reg(AR, "Preferencias: teclear las instrucciones propias, el texto queda en el cuadro y el contador cuenta",
              campo.toPlainText() == "Explicame paso a paso"
              and campo.contador.text() == f"21 / {TOPE_INSTRUCCIONES} caracteres", campo.contador.text())
        pegar(campo, "x" * (TOPE_INSTRUCCIONES + 2000))
        A.reg(AR, "Preferencias: pegar un texto enorme lo corta al tope y el contador lo dice",
              len(campo.toPlainText()) == TOPE_INSTRUCCIONES and "se cortó" in campo.contador.text(),
              campo.contador.text())
        borrar_todo(campo)
        A.reg(AR, "Preferencias: Ctrl+A y Supr dejan el cuadro vacío (0 caracteres)",
              campo.toPlainText() == "" and campo.contador.text().startswith("0 /"), campo.contador.text())
        QTest.keyClicks(campo, "Respondeme corto")
        QTest.keyClick(campo, Qt.Key_Tab)                  # Tab sale del cuadro, no escribe un tabulador
        A.reg(AR, "Preferencias: Tab sale del cuadro sin escribir un tabulador",
              "\t" not in campo.toPlainText() and not campo.hasFocus())
        dlg.resize(800, 520)
        A.esperar(200)
        pantalla = QApplication.primaryScreen().availableGeometry()
        A.reg(AR, "Preferencias achicada (800x520): el cuadro de instrucciones, su contador y Aceptar se ven",
              dentro(campo, dlg) and dentro(campo.contador, dlg) and dentro(dlg.b_aceptar, dlg)
              and pantalla.contains(dlg.frameGeometry()), f"dialogo={dlg.size()}")
        A.foto(dlg, "asistente_pref_instrucciones_800x520")
        QTest.mouseClick(dlg.b_aceptar, Qt.LeftButton)
        A.esperar(100)
        A.reg(AR, "Aceptar guarda las instrucciones propias",
              v.prefs["asistente/instrucciones"] == "Respondeme corto", v.prefs["asistente/instrucciones"])
        dlg, campo = abrir_pref()
        A.reg(AR, "reabrir Preferencias: las instrucciones siguen ahí", campo.toPlainText() == "Respondeme corto")
        QTest.mouseClick(dlg.b_cancelar, Qt.LeftButton)
    finally:
        modelos.modelos_disponibles = real

    def abrir_proyecto():
        QTest.mouseClick(p.b_chat, Qt.LeftButton)
        A.esperar(50)
        next(a for a in p.b_chat.menu().actions() if a.text().startswith("Instrucciones de este proyecto")).trigger()
        A.esperar(150)
        return next((d for d in p.findChildren(QDialog, "instrucciones_proyecto") if d.isVisible()), None)

    d = abrir_proyecto()
    A.reg(AR, "Chat › Instrucciones de este proyecto abre su diálogo", d is not None)
    if d is None:
        return
    QTest.mouseClick(d.campo.viewport(), Qt.LeftButton)
    QTest.keyClicks(d.campo, "Pieza para PETG")
    pegar(d.campo, "y" * (TOPE_INSTRUCCIONES + 500))
    A.reg(AR, "proyecto: teclear y pegar algo enorme lo corta al tope", len(d.campo.toPlainText()) == TOPE_INSTRUCCIONES
          and "se cortó" in d.campo.contador.text(), d.campo.contador.text())
    QTest.keyClick(d, Qt.Key_Escape)
    A.esperar(100)
    A.reg(AR, "proyecto: Esc cancela y no cambia nada", v.doc.instrucciones == ""
          and not any(x.isVisible() for x in p.findChildren(QDialog, "instrucciones_proyecto")))
    d = abrir_proyecto()
    QTest.mouseClick(d.campo.viewport(), Qt.LeftButton)
    QTest.keyClicks(d.campo, "Pieza para PETG, pared de 2 mm")
    v.resize(800, 520)
    A.esperar(250)
    pantalla = QApplication.primaryScreen().availableGeometry()
    A.reg(AR, "ventana 800x520: el diálogo de instrucciones del proyecto y Aceptar se ven enteros",
          pantalla.contains(d.frameGeometry()) and dentro(d.b_aceptar, d) and dentro(d.campo.contador, d),
          f"dialogo={d.frameGeometry()}")
    A.foto(d, "asistente_instrucciones_proyecto_800x520")
    QTest.mouseClick(d.b_aceptar, Qt.LeftButton)
    A.esperar(100)
    v.resize(1900, 1000)
    A.esperar(200)
    A.reg(AR, "proyecto: Aceptar las guarda en el documento", v.doc.instrucciones == "Pieza para PETG, pared de 2 mm")
    d = abrir_proyecto()
    A.reg(AR, "proyecto: reabrir el diálogo las muestra", d.campo.toPlainText() == "Pieza para PETG, pared de 2 mm")
    QTest.keyClick(d, Qt.Key_Escape)
    # Guardar, abrir otro documento y volver a abrir el archivo: siguen, y el chat avisa que el archivo trae instrucciones.
    ruta = str(Path(tempfile.mkdtemp()) / "con_instrucciones.omnicad")
    proyecto.guardar(v.doc, ruta)
    v.set_documento(Documento())
    v.abrir_ruta(ruta, preguntar=False)
    A.esperar(300)
    avisos = [t for t in textos(p) if "trae instrucciones" in t]
    A.reg(AR, "guardar, cerrar y reabrir conserva las instrucciones del proyecto y el chat lo avisa una vez",
          v.doc.instrucciones == "Pieza para PETG, pared de 2 mm" and len(avisos) == 1, avisos[-1:] if avisos else "")
    p.modo.setCurrentIndex(p.modo.findData("explicar"))
    sistemas = []

    class ConSistema(ProveedorFalso):
        def responder(self, sistema, mensajes, herramientas):
            sistemas.append(sistema)
            return super().responder(sistema, mensajes, herramientas)

    p.crear_proveedor = lambda _cfg: ConSistema([Respuesta(texto="ok")])
    escribir(p, "hola", Qt.Key_Return)
    esperar(p)
    p.crear_proveedor = lambda _cfg: ProveedorFalso(p.guion)
    sistema = sistemas[0] if sistemas else ""
    A.reg(AR, "el pedido lleva las dos instrucciones en el prompt de sistema",
          "Respondeme corto" in sistema and "Pieza para PETG" in sistema)
    A.foto(p, "asistente_aviso_instrucciones")
    v.prefs["asistente/instrucciones"] = ""


def clic_en_cara(cx, cy, z, r):
    """Clic izquierdo REAL en el visor sobre la cara horizontal de altura z alrededor de (cx, cy): se hace en el primer
    punto de la grilla donde lo de abajo es una cara (una arista o un boceto cercanos ganan, como en Fusion)."""
    for dx in (0, r / 2, -r / 2):
        for dy in (0, r / 2, -r / 2):
            q = v.visor.proyectar((cx + dx, cy + dy, z))
            hit = v.visor.elegir_entidad(q) if q is not None else None
            if hit and hit["tipo"] == "cara":
                QTest.mouseClick(v.visor, Qt.LeftButton, Qt.NoModifier, q.toPoint())
                A.esperar(250)
                return
    A.reg(AR, f"selección: hay un punto de la cara en ({cx}, {cy}, {z}) para hacer clic", False)


def seleccion_ui(p):
    """IA-13: clic real en una cara, la ficha 🎯, «empalme de 2 mm en esto», ✕, elegir otra cosa y ventana chica."""
    import re
    v._seleccionar([])
    A.esperar(100)
    A.reg(AR, "selección: sin nada elegido no hay ficha", not p.ficha_sel.isVisible())
    clic_en_cara(-100, 0, 20, 20)    # la tapa de la caja de 30 × 30 × 20
    elegida = v.leer_seleccion()
    A.reg(AR, "selección: clic en la tapa de la caja muestra la ficha con su medida",
          p.ficha_sel.isVisible() and p.texto_sel.text().startswith("🎯 1 cara de ")
          and p.texto_sel.text().endswith("(30 × 30 mm)") and len(elegida) == 1 and elegida[0]["tipo"] == "cara",
          p.texto_sel.text())
    A.foto(p, "asistente_ficha_seleccion")
    if not (len(elegida) == 1 and elegida[0]["tipo"] == "cara"):
        return                                     # sin la cara elegida no tiene sentido seguir
    sistemas, usadas = [], []

    class Lector(ProveedorFalso):
        def responder(self, sistema, mensajes, herramientas):
            sistemas.append(sistema)
            if len(sistemas) > 1:
                return Respuesta(texto="Listo.")
            m = re.search(r"cara plana de \S+ · 30 × 30 mm · [^\"]* · ref (\S+?)\"", sistema)
            if m is None:
                return Respuesta(texto="no veo la selección")
            usadas.append(m.group(1))
            return Respuesta(herramientas=[PedidoHerramienta("e1", "fillet", {"faces_a": [m.group(1)], "radius": 2})])

    p.crear_proveedor = lambda _cfg: Lector([])
    p.modo.setCurrentIndex(p.modo.findData("hacer"))
    n = len(v.doc.operaciones)
    escribir(p, "empalme de 2 mm en esto", Qt.Key_Return)
    esperar(p)
    caja = next(c for c in v.doc.estado_final.cuerpos.values() if c.id == elegida[0]["cuerpo"])
    volumen = api.llamar(api.Sesion(v.doc), "get_physical_properties", {"bodies": [caja.id]})["result"]["total"]["volume"]
    por_mm = 4 - 3.14159265
    A.reg(AR, "selección: «empalme de 2 mm en esto» empalma la tapa elegida (ref del prompt → fillet)",
          len(v.doc.operaciones) == n + 1 and v.doc.operaciones[-1].TIPO == "empalme" and len(usadas) == 1
          and 18000 - 120 * por_mm < volumen < 18000 - 104 * por_mm, f"ref={usadas} volumen={volumen:.2f}")
    A.foto(v, "asistente_empalme_en_esto")
    A.deshacer(v)
    clic_en_cara(-100, 0, 20, 20)
    QTest.mouseClick(p.b_sin_sel, Qt.LeftButton)
    A.esperar(100)
    A.reg(AR, "selección: ✕ saca la ficha", not p.ficha_sel.isVisible() and bool(v.leer_seleccion()))
    class Guarda(ProveedorFalso):
        def responder(self, sistema, mensajes, herramientas):
            sistemas.append(sistema)
            return Respuesta(texto="ok")

    p.crear_proveedor = lambda _cfg: Guarda([])
    sistemas.clear()
    p.modo.setCurrentIndex(p.modo.findData("explicar"))
    escribir(p, "que es esto", Qt.Key_Return)
    esperar(p)
    A.reg(AR, "selección: con ✕ el prompt ya no la trae", len(sistemas) == 1 and '"seleccion"' not in sistemas[0])
    clic_en_cara(-160, 0, 30, 12)    # la tapa del cilindro de radio 10
    A.reg(AR, "selección: elegir otra cosa cambia la ficha y vuelve a aparecer",
          p.ficha_sel.isVisible() and p.texto_sel.text().endswith("(20 × 20 mm)"), p.texto_sel.text())
    p.adjuntar(adjuntables()[:2])
    for ancho, alto in ((1024, 640), (800, 520)):
        v.resize(ancho, alto)
        A.esperar(300)
        A.reg(AR, f"selección: ventana {ancho}x{alto}: la ficha, su ✕, las fichas de adjuntos, el campo y Enviar entran",
              dentro(p.ficha_sel, v) and dentro(p.b_sin_sel, v) and dentro(p.fila_adjuntos, v)
              and dentro(p.campo, v) and dentro(p.b_enviar, v) and p.campo.height() >= 20,
              f"ficha={p.ficha_sel.geometry()} campo={p.campo.height()} panel={p.width()}x{p.height()}")
        A.foto(v, f"asistente_seleccion_{ancho}x{alto}")
    p.adjuntos = []
    p._mostrar_fichas()
    v._seleccionar([])
    v.resize(1900, 1000)
    A.esperar(200)
    p.crear_proveedor = lambda _cfg: ProveedorFalso(p.guion)


def antes_despues_ui(p):
    """IA-14: Antes y Después con la misma cámara aunque la IA gire la vista; clic, Enter, Esc, ventana chica,
    «Deshacer este pedido» y el historial."""
    import numpy as np
    p.nuevo_chat()
    A.esperar(50)
    p.crear_proveedor = lambda _cfg: ProveedorFalso([
        Respuesta(herramientas=[PedidoHerramienta("b1", "buscar_herramientas", {"nombres": ["set_view"]})]),
        Respuesta(herramientas=[CAJA2, PedidoHerramienta("v1", "set_view", {"view": "top"})]),
        Respuesta(texto="Listo: torre de 10 x 10 x 40 mm.")])
    p.modo.setCurrentIndex(p.modo.findData("hacer"))
    camara = p._camara()
    n = len(v.doc.operaciones)
    escribir(p, "hace una torre y mirala desde arriba", Qt.Key_Return)
    esperar(p)
    A.esperar(200)
    pares = p.lista.findChildren(QWidget, "antes_despues")
    mini = pares[0].findChildren(QWidget, "miniatura_comparacion") if len(pares) == 1 else []
    A.reg(AR, "antes y después: el pedido que crea la torre muestra dos miniaturas rotuladas, lado a lado",
          len(v.doc.operaciones) == n + 1 and [m.titulo for m in mini] == ["Antes", "Después"]
          and mini[0].y() == mini[1].y() and mini[0].x() < mini[1].x() and min(m.width() for m in mini) > 40,
          f"pares={len(pares)} tamaños={[m.size() for m in mini]}")
    if len(mini) != 2:
        return
    for m, nombre in zip(mini, ("antes", "despues"), strict=True):
        (A.CAPTURAS / f"asistente_ia14_{nombre}.png").write_bytes(m.png)
    A.reg(AR, "antes y después: las capturas son distintas (la torre está solo en Después)", mini[0].png != mini[1].png)
    A.reg(AR, "antes y después: la vista quedó como la dejó la IA (desde arriba), no la de la captura",
          not np.allclose(v.visor.R, camara[2]) and np.allclose(v.visor.R[2], (0, 0, 1), atol=1e-6),
          f"atrás={v.visor.R[2]}")
    p.area.ensureWidgetVisible(pares[0])
    A.esperar(100)
    A.foto(p, "asistente_antes_despues")
    QTest.mouseClick(mini[1], Qt.LeftButton)
    A.esperar(200)
    grande = p.findChild(QDialog, "imagen_grande")
    A.reg(AR, "antes y después: clic en Después la abre grande", grande is not None and grande.isVisible()
          and grande.windowTitle() == "Después")
    if grande is not None:
        A.foto(grande, "asistente_despues_grande")
        QTest.keyClick(grande, Qt.Key_Escape)
        A.esperar(100)
    A.reg(AR, "antes y después: Esc cierra la grande", not p.findChildren(QDialog, "imagen_grande"))
    mini[0].setFocus()
    QTest.keyClick(mini[0], Qt.Key_Return)
    A.esperar(200)
    grande = p.findChild(QDialog, "imagen_grande")
    A.reg(AR, "antes y después: Enter sobre Antes la abre grande", grande is not None and grande.isVisible()
          and grande.windowTitle() == "Antes")
    if grande is not None:
        QTest.keyClick(grande, Qt.Key_Escape)
        A.esperar(100)
    for ancho, alto in ((1024, 640), (800, 520)):
        v.resize(ancho, alto)
        A.esperar(300)
        p.area.ensureWidgetVisible(pares[0])
        A.esperar(100)
        A.reg(AR, f"antes y después: ventana {ancho}x{alto}: las dos miniaturas entran en el chat",
              all(en_el_chat(m, p) and m.width() > 30 for m in mini) and dentro(p.b_enviar, v),
              f"tamaños={[m.size() for m in mini]} panel={p.width()}")
        A.foto(v, f"asistente_antes_despues_{ancho}x{alto}")
    v.resize(1900, 1000)
    A.esperar(200)
    QTest.mouseClick(botones_deshacer(p)[-1], Qt.LeftButton)
    A.esperar(100)
    A.reg(AR, "antes y después: «Deshacer este pedido» saca la torre y las miniaturas quedan como registro",
          len(v.doc.operaciones) == n and len(p.lista.findChildren(QWidget, "antes_despues")) == 1)
    guardado = p.id_chat
    p.nuevo_chat()
    A.esperar(50)
    p.cargar_chat(guardado)
    A.esperar(100)
    pares = p.lista.findChildren(QWidget, "antes_despues")
    mini = pares[0].findChildren(QWidget, "miniatura_comparacion") if len(pares) == 1 else []
    A.reg(AR, "antes y después: reabrir el chat las muestra achicadas (320 px de ancho)",
          len(mini) == 2 and all(m.pm.width() == 320 for m in mini), f"anchos={[m.pm.width() for m in mini]}")
    p.crear_proveedor = lambda _cfg: ProveedorFalso(p.guion)


def primer_cuerpo():
    return api.llamar(api.Sesion(v.doc), "get_scene_info", {})["result"]["bodies"][0]["id"]


def color():
    """El color propio del primer cuerpo (set_appearance lo guarda en las propiedades, no en la receta)."""
    return v.doc.propiedades.get(primer_cuerpo(), {}).get("apariencia")


def pedido():
    # ---------------------------------------------------------------- botón de la barra de la aplicación
    boton = next(b for b in v.findChildren(QToolButton) if b.defaultAction() is v.acciones["asistente"])
    QTest.mouseClick(boton, Qt.LeftButton)
    A.esperar(200)
    p = v.asistente
    A.reg(AR, "clic en el botón Asistente abre el panel", p is not None and p.isVisible() and boton.isVisible())
    A.reg(AR, "el foco queda en el campo", QApplication.focusWidget() is p.campo, f"foco={QApplication.focusWidget()}")
    A.reg(AR, "cabecera con proveedor y modelo", "·" in p.etiqueta_modelo.text(), p.etiqueta_modelo.text())
    A.foto(v, "asistente_abierto")
    p.guion = []
    p.crear_proveedor = lambda _cfg: ProveedorFalso(p.guion)

    # ---------------------------------------------------------------- vacío, espacios, Mayús+Enter, Enter
    n = len(v.doc.operaciones)
    for texto in ("", "    "):
        escribir(p, texto, Qt.Key_Return)
        A.reg(AR, f"Enter con el campo «{texto}» no manda nada", not p.trabajando and p.mensajes == [])
    QTest.mouseClick(p.b_enviar, Qt.LeftButton)
    A.reg(AR, "clic en Enviar con el campo vacío no manda nada", not p.trabajando and p.mensajes == [])
    escribir(p, "linea uno", Qt.Key_Return, Qt.ShiftModifier)
    QTest.keyClicks(p.campo, "linea dos")
    A.reg(AR, "Mayús+Enter salta de línea sin mandar", p.campo.toPlainText() == "linea uno\nlinea dos" and not p.trabajando,
          repr(p.campo.toPlainText()))
    # ---------------------------------------------------------------- modo Hacer: crea la caja
    p.modo.setCurrentIndex(p.modo.findData("hacer"))
    p.guion = [Respuesta(herramientas=[CAJA], uso={"entrada": 120, "salida": 30, "costo_usd": 0.0012}),
               Respuesta(texto="Listo: **caja** de 30 x 20 x 10 mm.")]
    QTest.keyClick(p.campo, Qt.Key_Return)
    trabajando = p.trabajando and p.b_enviar.text() == "Cancelar" and not p.modo.isEnabled()
    tarjeta = esperar_tarjeta(p)
    A.reg(AR, "modo Hacer: antes de cambiar nada muestra la tarjeta de plan con Aplicar y Cancelar",
          tarjeta is not None and len(v.doc.operaciones) == n and tarjeta.b_aplicar.isVisible()
          and "create_box(length=30" in " ".join(textos(p)))
    A.foto(v, "asistente_tarjeta_plan")
    QTest.mouseClick(tarjeta.b_aplicar, Qt.LeftButton)
    esperar(p)
    A.reg(AR, "Enter manda: mientras trabaja Enviar dice Cancelar y el modo se bloquea", trabajando)
    A.reg(AR, "modo Hacer: la caja aparece en la ventana y la línea de la herramienta",
          len(v.doc.operaciones) == n + 1 and lineas(p)[-1:] == [f"✓ create_box → {v.doc.operaciones[-1].id}"],
          f"pasos={len(v.doc.operaciones) - n} lineas={lineas(p)}")
    A.reg(AR, "pie con tokens y USD", "120 tokens de entrada" in p.pie.text() and "0,0012 USD" in p.pie.text(),
          p.pie.text())
    linea = p.lista.findChildren(QToolButton, "herramienta_asistente")[-1]
    QTest.mouseClick(linea, Qt.LeftButton)
    A.esperar(80)
    detalle = linea.parentWidget().findChildren(type(p.pie))[0]
    A.reg(AR, "clic en la línea de la herramienta despliega el detalle", detalle.isVisible() and "length" in detalle.text(),
          detalle.text()[:80])
    A.foto(v, "asistente_caja")
    A.deshacer(v)
    A.reg(AR, "deshacer de la ventana saca la caja del asistente", len(v.doc.operaciones) == n)
    boton = botones_deshacer(p)[-1]
    QTest.mouseClick(boton, Qt.LeftButton)
    A.reg(AR, "«Deshacer este pedido» tras un cambio a mano no deshace nada y se deshabilita con explicación",
          len(v.doc.operaciones) == n and not boton.isEnabled() and "se perdería ese trabajo" in textos(p)[-1],
          textos(p)[-1])

    # ---------------------------------------------------------------- IA-5: tarjeta, Cancelar, Esc, Guiar, deshacer
    for como in ("clic en Cancelar de la tarjeta", "Esc sobre la tarjeta"):
        p.modo.setCurrentIndex(p.modo.findData("hacer"))
        p.guion = [Respuesta(herramientas=[CAJA]), Respuesta(texto="no tendría que llegar")]
        receta = v.doc.a_dict()
        escribir(p, "caja", Qt.Key_Return)
        tarjeta = esperar_tarjeta(p)
        if como.startswith("Esc"):
            tarjeta.b_aplicar.setFocus()        # el foco en la tarjeta (Esc lo recibe el botón y sube a la tarjeta)
            QTest.keyClick(tarjeta.b_aplicar, Qt.Key_Escape)
        else:
            QTest.mouseClick(tarjeta.b_cancelar, Qt.LeftButton)
        esperar(p, aplicar=False)
        A.reg(AR, f"{como}: no se hace nada y el chat lo dice", v.doc.a_dict() == receta
              and lineas(p)[-1] == "✗ create_box: CANCELLED" and any("No aprobaste" in t for t in textos(p)[-3:]),
              f"{lineas(p)[-1]} | {textos(p)[-1]}")

    p.modo.setCurrentIndex(p.modo.findData("guiar"))
    p.guion = [Respuesta(herramientas=[CAJA]), Respuesta(herramientas=[CAJA2]), Respuesta(texto="Listo.")]
    escribir(p, "dos cajas", Qt.Key_Return)
    vistas = 0
    for _ in range(2):
        tarjeta = esperar_tarjeta(p)
        vistas += tarjeta is not None
        if tarjeta is not None:
            QTest.mouseClick(tarjeta.b_aplicar, Qt.LeftButton)
    esperar(p)
    A.reg(AR, "modo Guiar: una tarjeta por tanda; con Aplicar en cada una crea las dos cajas",
          vistas == 2 and len(v.doc.operaciones) == n + 2, f"tarjetas={vistas} pasos={len(v.doc.operaciones) - n}")
    A.foto(v, "asistente_guiar")
    QTest.mouseClick(botones_deshacer(p)[-1], Qt.LeftButton)
    A.reg(AR, "clic en «Deshacer este pedido» vuelve a como estaba antes del pedido (las dos cajas)",
          len(v.doc.operaciones) == n and "volvió a como estaba" in textos(p)[-1], textos(p)[-1])

    suelta = threading.Event()

    class Pausa(ProveedorFalso):
        def responder(self, *a):
            if len(self.recibidos) == 1:
                suelta.wait(5)
            return super().responder(*a)

    p.crear_proveedor = lambda _cfg: Pausa([Respuesta(herramientas=[CAJA]), Respuesta(herramientas=[CAJA2])])
    p.modo.setCurrentIndex(p.modo.findData("hacer"))
    receta = v.doc.a_dict()
    escribir(p, "dos cajas", Qt.Key_Return)
    QTest.mouseClick(esperar_tarjeta(p).b_aplicar, Qt.LeftButton)
    for _ in range(250):
        if len(v.doc.operaciones) == n + 1:
            break
        QTest.qWait(20)
    hizo_una = len(v.doc.operaciones) == n + 1
    QTest.mouseClick(p.b_enviar, Qt.LeftButton)
    suelta.set()
    esperar(p)
    A.reg(AR, "Cancelar a mitad del pedido (ya hizo una caja) vuelve a como estaba y lo dice", hizo_una
          and v.doc.a_dict() == receta and "volvió a como estaba" in " ".join(textos(p)[-2:]), textos(p)[-1])
    p.crear_proveedor = lambda _cfg: ProveedorFalso(p.guion)

    # ---------------------------------------------------------------- IA-11 (API): una fuera del núcleo en 2 llamadas
    p.modo.setCurrentIndex(p.modo.findData("hacer"))
    receta = color()
    p.guion = [Respuesta(herramientas=[PedidoHerramienta("b1", "buscar_herramientas", {"nombres": ["set_appearance"]})]),
               Respuesta(herramientas=[PedidoHerramienta("a1", "set_appearance",
                                                         {"bodies": [primer_cuerpo()], "color": "#ff0000"})]),
               Respuesta(texto="Listo: la pinté de rojo.")]
    escribir(p, "pinta la caja de rojo", Qt.Key_Return)
    tarjeta = esperar_tarjeta(p)
    en_tarjeta = tarjeta is not None and "set_appearance(" in " ".join(textos(p))
    esperar(p)
    A.reg(AR, "IA-11 API: «pinta la caja de rojo» habilita set_appearance por nombre, pide Aplicar y la usa",
          en_tarjeta and lineas(p)[-2].startswith("✓ buscar_herramientas") and lineas(p)[-1].startswith("✓ set_appearance")
          and color() == [1.0, 0.0, 0.0], f"tarjeta={en_tarjeta} lineas={lineas(p)[-2:]}")
    QTest.mouseClick(botones_deshacer(p)[-1], Qt.LeftButton)
    A.reg(AR, "IA-11 API: «Deshacer este pedido» saca el color", color() == receta, textos(p)[-1])

    # ---------------------------------------------------------------- APP_BUSY: la persona tiene un comando abierto
    abierto = A.abrir(v, "extruir")
    p.guion = [Respuesta(herramientas=[CAJA]), Respuesta(texto="No pude.")]
    escribir(p, "caja", Qt.Key_Return)
    esperar(p)
    aviso = [t for t in textos(p) if "Terminá o cancelá el comando abierto" in t]
    A.reg(AR, "con un comando abierto, el chat avisa claro que hay que terminarlo o cancelarlo",
          abierto is not None and lineas(p)[-1] == "✗ create_box: APP_BUSY" and len(aviso) == 1, aviso[-1:])
    A.foto(v, "asistente_app_busy")
    if v.panel is not None:
        v.panel.cancelar()
    A.esperar(150)

    # ---------------------------------------------------------------- modo Explicar: no cambia nada
    p.modo.setCurrentIndex(p.modo.findData("explicar"))
    p.guion = [Respuesta(herramientas=[CAJA]), Respuesta(texto="Se hace con CREAR › Caja.")]
    escribir(p, "como hago una caja", Qt.Key_Return)
    esperar(p)
    A.reg(AR, "modo Explicar no cambia el documento", len(v.doc.operaciones) == n and lineas(p)[-1] ==
          "✗ create_box: TOOL_NOT_AVAILABLE", lineas(p)[-1])
    # IA-8: la pregunta de cómo se hace va a la ayuda local y la respuesta cita la fuente.
    p.guion = [Respuesta(herramientas=[PedidoHerramienta("a1", "search_help", {"query": "empalme"})]),
               Respuesta(texto="Con fillet (fuente: herramienta fillet).")]
    escribir(p, "como hago un empalme", Qt.Key_Return)
    esperar(p)
    A.reg(AR, "IA-8: en Explicar, «cómo hago un empalme» busca en la ayuda local y cita la fuente",
          lineas(p)[-1] == "✓ search_help" and "Con fillet (fuente: herramienta fillet)." in textos(p)
          and len(v.doc.operaciones) == n, lineas(p)[-1])

    # ---------------------------------------------------------------- Cancelar (botón) y Esc
    for como in ("botón Cancelar", "Esc"):
        suelta = threading.Event()

        class Lento(ProveedorFalso):
            def responder(self, *a, suelta=suelta):
                suelta.wait(5)
                return super().responder(*a)

        p.crear_proveedor = lambda _cfg: Lento([Respuesta(herramientas=[CAJA])])
        p.modo.setCurrentIndex(p.modo.findData("hacer"))
        escribir(p, "caja lenta", Qt.Key_Return)
        if como == "Esc":
            QTest.keyClick(p.campo, Qt.Key_Escape)
        else:
            QTest.mouseClick(p.b_enviar, Qt.LeftButton)
        cancelando = p.b_enviar.text() == "Cancelando…"
        suelta.set()
        esperar(p)
        A.reg(AR, f"{como} corta el pedido: no se crea nada", cancelando and len(v.doc.operaciones) == n
              and lineas(p)[-1] == "✗ create_box: CANCELLED" and p.b_enviar.text() == "Enviar", lineas(p)[-1])
    p.crear_proveedor = lambda _cfg: ProveedorFalso(p.guion)
    QTest.keyClick(p.campo, Qt.Key_Escape)
    A.reg(AR, "Esc sin pedido en curso devuelve el foco al visor", QApplication.focusWidget() is v.visor
          and p.isVisible(), f"foco={QApplication.focusWidget()}")

    # ---------------------------------------------------------------- Tab, texto enorme, pegar
    QTest.mouseClick(p.campo.viewport(), Qt.LeftButton)
    QTest.keyClick(p.campo, Qt.Key_Tab)
    A.reg(AR, "Tab pasa del campo al siguiente control (no escribe un tabulador)",
          QApplication.focusWidget() is not p.campo and "\t" not in p.campo.toPlainText(), f"foco={QApplication.focusWidget()}")
    mensajes = len(p.mensajes)
    QApplication.clipboard().setText("x" * 25000)
    QTest.mouseClick(p.campo.viewport(), Qt.LeftButton)
    QTest.keyClick(p.campo, Qt.Key_A, Qt.ControlModifier)
    QTest.keyClick(p.campo, Qt.Key_V, Qt.ControlModifier)
    pegado = len(p.campo.toPlainText())
    QTest.keyClick(p.campo, Qt.Key_Return)
    aviso = [w.text() for w in p.lista.findChildren(type(p.pie))][-1]
    A.reg(AR, "pegar un texto enorme (25000) y Enter: no se manda y avisa", pegado == 25000 and not p.trabajando
          and len(p.mensajes) == mensajes and "muy largo" in aviso, aviso)
    QApplication.clipboard().setText("  hola desde el portapapeles  ")
    QTest.keyClick(p.campo, Qt.Key_A, Qt.ControlModifier)
    QTest.keyClick(p.campo, Qt.Key_V, Qt.ControlModifier)
    p.guion = [Respuesta(texto="Hola.")]
    QTest.keyClick(p.campo, Qt.Key_Return)
    esperar(p)
    A.reg(AR, "pegar y Enter manda el texto sin los espacios de los bordes",
          p.mensajes[-2]["contenido"][-1]["texto"] == "hola desde el portapapeles", p.mensajes[-2]["contenido"][-1])

    # ---------------------------------------------------------------- biblioteca de prompts y chat nuevo
    menu = p.b_chat.menu()
    biblioteca = next(a.menu() for a in menu.actions() if a.text() == "Biblioteca de prompts")
    item = biblioteca.actions()[0].menu().actions()[0]
    item.trigger()
    A.reg(AR, "Biblioteca de prompts deja el ejemplo en el campo sin mandarlo", bool(p.campo.toPlainText())
          and not p.trabajando, p.campo.toPlainText()[:60])
    guardado, n_lineas = p.id_chat, len(lineas(p))
    A.reg(AR, "IA-7: el chat se guardó solo al terminar el último pedido",
          bool(guardado) and historial.cargar(guardado)["mensajes"] == p.mensajes, guardado)
    QTest.mouseClick(p.b_nuevo, Qt.LeftButton)
    A.esperar(50)                              # los mensajes viejos se borran con deleteLater
    A.reg(AR, "+ empieza un chat nuevo", p.mensajes == [] and lineas(p) == [] and p.pie.text() == ""
          and p.id_chat is None)
    A.reg(AR, "la estrella avisa que es IA", "puede equivocarse" in p.b_aviso.toolTip())
    historial_chats(p, guardado, n_lineas)
    rutas = adjuntos_ui(p)

    # ---------------------------------------------------------------- ventana chica (con una tarjeta de plan esperando)
    p.modo.setCurrentIndex(p.modo.findData("hacer"))
    p.guion = [Respuesta(herramientas=[CAJA]), Respuesta(texto="no tendría que llegar")]
    escribir(p, "caja", Qt.Key_Return)
    tarjeta = esperar_tarjeta(p)
    p.adjuntar(rutas)                          # con fichas a la vista: también tienen que entrar
    for ancho, alto in ((1024, 640), (800, 520)):
        p.hide()
        A.esperar(150)
        v.resize(ancho, alto)
        A.esperar(300)
        sin_panel = v.width()                  # la ventana no baja de 821 de ancho ni sin el panel (B-105)
        p.show()
        v.resize(ancho, alto)
        A.esperar(300)
        ok = dentro(p.campo, v) and dentro(p.b_enviar, v) and dentro(p.modo, v)
        A.reg(AR, f"ventana {ancho}x{alto}: el campo, el modo y Enviar entran", ok,
              f"ventana={v.width()}x{v.height()} panel={p.width()}x{p.height()}")
        A.reg(AR, f"ventana {ancho}x{alto}: el clip, las fichas y su contador entran",
              dentro(p.b_clip, v) and dentro(p.fila_adjuntos, v) and dentro(p.contador, v)
              and dentro(fichas(p)[0].b_quitar, v), f"fila={p.fila_adjuntos.geometry()}")
        A.reg(AR, f"ventana {ancho}x{alto}: la tarjeta de plan y sus botones se ven enteros",
              tarjeta is not None and en_el_chat(tarjeta.b_aplicar, p) and en_el_chat(tarjeta.b_cancelar, p)
              and dentro(tarjeta.b_aplicar, v), f"tarjeta={tarjeta and tarjeta.size()}")
        if ancho >= sin_panel:
            A.reg(AR, f"ventana {ancho}x{alto}: el panel no agranda la ventana", v.width() == ancho,
                  f"con panel {v.width()} px")
        else:
            print(f"NOTA ventana {ancho}x{alto}: ni sin el panel baja de {sin_panel} px (B-105); con el panel mide "
                  f"{v.width()} px", flush=True)
        A.foto(v, f"asistente_{ancho}x{alto}")
    if tarjeta is not None:
        QTest.mouseClick(tarjeta.b_cancelar, Qt.LeftButton)
    esperar(p, aplicar=False)
    p.adjuntos = []
    p._mostrar_fichas()
    v.resize(1900, 1000)
    A.esperar(200)

    modelos_en_preferencias()
    suscripcion(p)
    instrucciones_ui(p)
    seleccion_ui(p)
    antes_despues_ui(p)

    # ---------------------------------------------------------------- atajo y cerrar
    QTest.keyClick(v, Qt.Key_A, Qt.ControlModifier | Qt.ShiftModifier)
    A.esperar(100)
    A.reg(AR, "Ctrl+Mayús+A cierra el panel", not p.isVisible() and not v.acciones["asistente"].isChecked())
    QTest.keyClick(v, Qt.Key_A, Qt.ControlModifier | Qt.ShiftModifier)
    A.esperar(100)
    A.reg(AR, "Ctrl+Mayús+A lo vuelve a abrir", p.isVisible())


n_err = len(A.ERRORES)
A.correr(AR, pedido)
A.reg(AR, "ninguna excepción escapada en slots de Qt", len(A.ERRORES) == n_err, "\n".join(A.ERRORES[n_err:])[-600:])
A.guardar_registro("asistente")
fallas = [r for r in A.REGISTRO if not r["ok"]]
print(f"\n=== {len(A.REGISTRO)} comprobaciones, {len(fallas)} con ✗ ===")
v.doc.modificado = False
v.close()
sys.exit(0)

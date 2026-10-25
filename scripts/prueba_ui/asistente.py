# -*- coding: utf-8 -*-
"""Asistente IA como una persona: clic real en el botón de la barra, teclear en el campo (texto, vacío, enorme, pegar),
Enter, Mayús+Enter, Esc, Tab, Cancelar, cambiar de modo, biblioteca de prompts, chat nuevo y ventana chica (el campo y
Enviar tienen que entrar). IA-5: tarjeta de plan (Aplicar, Cancelar, Esc), Guiar, Cancelar con vuelta atrás,
«Deshacer este pedido» y el aviso de APP_BUSY con un comando abierto. IA-6: elegir «Claude Code (tu suscripción)» en
Preferencias (teclado y clic en Aceptar), ruta mala tecleada, y un pedido con el CLI simulado que entra por el puente en
vivo (encendido solo durante el pedido) con la tarjeta Aplicar. El proveedor es el falso: sin red ni gasto."""
import sys
import threading

import arnes as A
import escena
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog, QLabel, QPushButton, QToolButton

from omnicad.asistente import config, historial
from omnicad.asistente.proveedores.agente_local import AgenteLocal
from omnicad.asistente.proveedores.base import PedidoHerramienta, ProveedorFalso, Respuesta
from omnicad.servidor_mcp.puente_cliente import ClientePuente

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
    """Hace lo que haría Claude Code: llama herramientas por el puente en vivo (TCP + token de puente.json)."""

    def __init__(self, archivo, llamadas):
        self.tipo, self.nombre, self.sesion, self.proceso = "claude_code", "Claude Code", None, None
        self.archivo, self.llamadas, self.respuestas, self.puente_visto = archivo, llamadas, [], None

    def correr(self, texto, sistema, modo, al_evento=None, cancelado=None):
        cliente = ClientePuente(self.archivo)
        self.puente_visto = cliente.conectar()
        for nombre, args in self.llamadas:
            r = cliente.llamar(nombre, args)
            self.respuestas.append(r)
            al_evento("herramienta", {"nombre": nombre, "args": args, "respuesta": r})
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
    v.prefs["asistente/proveedor"] = "anthropic"
    p.actualizar_cabecera()
    p.crear_proveedor = lambda _cfg: ProveedorFalso(p.guion)


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

    # ---------------------------------------------------------------- ventana chica (con una tarjeta de plan esperando)
    p.modo.setCurrentIndex(p.modo.findData("hacer"))
    p.guion = [Respuesta(herramientas=[CAJA]), Respuesta(texto="no tendría que llegar")]
    escribir(p, "caja", Qt.Key_Return)
    tarjeta = esperar_tarjeta(p)
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
    v.resize(1900, 1000)
    A.esperar(200)

    suscripcion(p)

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

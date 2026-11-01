# -*- coding: utf-8 -*-
"""Panel de comando movible y con los preajustes en la cabecera (UI-3, UI-4 y UI-7 de `docs/seguimiento/mejoras.md`), como
lo haría una persona, en la ventana real y a 1280x720, 1024x640 y 800x520:
  - el botón «⋯» de preajustes está en la cabecera (sin la fila aparte), su menú se abre con un clic y guarda, aplica,
    renombra y borra;
  - «⋯» se alcanza con Tab (después de Cancelar) y se abre con Espacio o Enter;
  - la cabecera se arrastra (press, varios movimientos, release): el panel queda donde se lo deja, jamás se sale de la
    vista y Aceptar/Cancelar siguen a la vista; la posición se recuerda en el panel siguiente y en la preferencia;
  - un clic suelto en la cabecera no borra la posición; el doble clic la devuelve a su lugar;
  - Enter acepta, Esc cancela y Tab recorre los campos con el panel movido;
  - ninguna selección vive en «Más opciones» (Nervio, Labio y Alinear: sus selecciones se ven sin abrir la sección).
    panel_movible.py   → capturas en `evidencias/ui_paneles_2026-10-31/movible/`. Eventos simulados al widget."""
import os
import tempfile

import arnes as A
import escena
from PySide6.QtCore import QEvent, QPoint, QPointF, Qt, QTimer
from PySide6.QtGui import QMouseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QInputDialog

from omnicad.ui.comando import ContextoComando, Seleccion
from omnicad.ui.comandos import CATALOGO
from omnicad.ui.superposiciones import CabeceraMovible

os.environ["OMNICAD_PREAJUSTES"] = os.path.join(tempfile.mkdtemp(prefix="omnicad_preajustes_"), "preajustes.json")   # nunca los de la persona
AR = "PANEL·movible"
CARPETA = A.SALIDA.parent / "ui_paneles_2026-10-31" / "movible"
CARPETA.mkdir(parents=True, exist_ok=True)
NOMBRE = ["Delgado"]
s, ids = escena.construir()
app, v = A.iniciar(s.doc, 1280, 720)
A.esperar(300)
QInputDialog.getText = staticmethod(lambda *a, **k: (NOMBRE[0], True))     # el nombre que la persona tecleó en el cuadro


def abrir(clave="extruir"):
    if v.panel is not None:
        v.panel.cancelar()
        A.esperar(60)
    panel = v.ejecutar_comando(CATALOGO[clave]())
    A.esperar(150)
    return panel


def evento(w, tipo, global_, boton=Qt.LeftButton):
    QApplication.sendEvent(w, QMouseEvent(tipo, QPointF(w.mapFromGlobal(global_)), QPointF(global_), boton, boton, Qt.NoModifier))


def arrastrar(panel, dx, dy, pasos=5):
    """Press en la cabecera, varios movimientos, release: como la mano."""
    cab = panel.findChild(CabeceraMovible)
    ini = cab.mapToGlobal(QPoint(30, 8))
    evento(cab, QEvent.MouseButtonPress, ini)
    for i in range(1, pasos + 1):
        evento(cab, QEvent.MouseMove, ini + QPoint(dx * i // pasos, dy * i // pasos))
    evento(cab, QEvent.MouseButtonRelease, ini + QPoint(dx, dy))
    A.esperar(60)


def botones_a_la_vista(p):
    """Aceptar y Cancelar dentro del lienzo y sin nada encima (la barra de navegación es lo que más los tapó)."""
    marco = v.area.rect()
    cancelar = next(b for b in p.findChildren(type(p.boton_ok)) if b.text() == "Cancelar")
    barra = v.area.barra.geometry() if v.area.barra is not None and v.area.barra.isVisible() else None
    return all(marco.contains(b.mapTo(v.area, b.rect().bottomRight())) and marco.contains(b.mapTo(v.area, b.rect().topLeft()))
               and (barra is None or not barra.intersects(p.geometry())) for b in (p.boton_ok, cancelar))


def entra(p):
    return v.area.rect().adjusted(0, 0, 1, 1).contains(p.geometry())


def menu_de(boton, texto=None, foto=None, tecla=None):
    """Clic real en el botón (o, con `tecla`, esa tecla con el foco en él); con el menú abierto lo mira y, si `texto`, hace clic en esa entrada (si no, Esc)."""
    visto = {}

    intentos = [0]

    def con_el_menu():
        pop = QApplication.activePopupWidget()
        if pop is None:
            intentos[0] += 1
            if intentos[0] < 8:                                 # el primer menú de la sesión tarda en armarse: se vuelve a mirar
                QTimer.singleShot(150, con_el_menu)
            else:
                visto["abierto"] = False
            return
        visto["abierto"] = True
        visto["textos"] = [a.text() for a in pop.actions() if a.text()]
        visto["marcada"] = [a.text() for a in pop.actions() if a.isChecked()]
        if foto:
            pop.grab().save(str(CARPETA / f"{foto}.png"))
        if texto:
            a = next((a for a in pop.actions() if a.text().startswith(texto)), None)
            visto["accion"] = a is not None and a.isEnabled()
            QTest.mouseClick(pop, Qt.LeftButton, Qt.NoModifier, pop.actionGeometry(a).center())
        else:
            QTest.keyClick(pop, Qt.Key_Escape)
    QTimer.singleShot(250, con_el_menu)
    if tecla is None:
        QTest.mouseClick(boton, Qt.LeftButton)
    else:
        QTest.keyClick(boton, tecla)
    for _ in range(40):                                     # el menú se abre sin bloquear: se espera a que la persona «lo vea»
        if visto:
            break
        A.esperar(50)
    A.esperar(120)
    return visto


def preajustes(tag):
    p = abrir("extruir")
    b = p.boton_preajustes
    cab = b.parentWidget()
    A.reg(AR, f"{tag} · «⋯» de preajustes en la cabecera y el cuerpo empieza justo debajo (sin fila aparte)",
          b is not None and cab.objectName() == "cabecera_comando" and cab.geometry().contains(b.geometry())
          and p.desplazador.y() <= cab.y() + cab.height() + 2, f"cabecera {cab.height()} px, cuerpo en y={p.desplazador.y()}")
    t = p.findChild(type(p.mensaje), "titulo_comando")
    A.reg(AR, f"{tag} · el título no pisa los botones de la cabecera", t.geometry().right() < b.geometry().left(), t.text())
    visto = menu_de(b, foto=f"menu_{tag}")
    A.reg(AR, f"{tag} · el clic abre el menú con fábrica, guardar, renombrar, eliminar y predeterminado",
          visto.get("abierto") and visto["marcada"] == ["Valores de fábrica"]
          and all(any(x.startswith(k) for x in visto["textos"]) for k in
                  ("Guardar los valores actuales", "Guardar", "Renombrar", "Eliminar", "Establecer como predeterminado")),
          visto.get("textos"))
    p.boton_cancelar.setFocus()
    QTest.keyClick(p.boton_cancelar, Qt.Key_Tab)
    A.reg(AR, f"{tag} · Tab desde Cancelar llega a «⋯» (se alcanza con el teclado)", QApplication.focusWidget() is b,
          type(QApplication.focusWidget()).__name__)
    abiertos = {}
    for nombre, tecla in (("Espacio", Qt.Key_Space), ("Enter", Qt.Key_Return)):
        abiertos[nombre] = menu_de(b, tecla=tecla).get("abierto")
    A.reg(AR, f"{tag} · con «⋯» enfocado, Espacio y Enter abren el menú (Enter no acepta el comando)",
          all(abiertos.values()) and v.panel is p, str(abiertos))
    p.set_valor("distancia", "33 mm")
    visto = menu_de(b, "Guardar los valores actuales como nuevo")
    A.reg(AR, f"{tag} · «Guardar como nuevo» crea el preajuste y queda elegido",
          b.actual == NOMBRE[0], f"actual={b.actual}")
    p.set_valor("distancia", "5 mm")
    menu_de(b, "Valores de fábrica")
    A.reg(AR, f"{tag} · «Valores de fábrica» restablece el valor", p.valores["distancia"] != "33 mm" and b.actual is None,
          p.valores["distancia"])
    menu_de(b, NOMBRE[0])
    A.reg(AR, f"{tag} · elegir el preajuste vuelve a poner 33 mm", p.valores["distancia"] == "33 mm" and b.actual == NOMBRE[0],
          p.valores["distancia"])
    NOMBRE[0] = "Delgado 2"
    menu_de(b, "Renombrar")
    A.reg(AR, f"{tag} · Renombrar", b.actual == "Delgado 2", f"actual={b.actual}")
    menu_de(b, "Eliminar")
    A.reg(AR, f"{tag} · Eliminar deja solo Valores de fábrica", b.actual is None and not b.panel.boton_preajustes.menu.isVisible(),
          f"actual={b.actual}")
    NOMBRE[0] = "Delgado"
    p.cancelar()


def movimiento(tag, ancho, alto):
    v.prefs["vista/posicion_panel_comando"] = ""
    v.area.posicion_panel = None
    p = abrir("extruir")
    base = p.pos()
    arrastrar(p, -300, 120)
    A.reg(AR, f"{tag} · arrastrar la cabecera mueve el panel (y no cambia su tamaño)",
          p.pos() != base and entra(p), f"{base.x()},{base.y()} → {p.x()},{p.y()}")
    A.reg(AR, f"{tag} · Aceptar y Cancelar siguen a la vista", botones_a_la_vista(p), "")
    p.grab().save(str(CARPETA / f"movido_{tag}.png"))
    v.grab().save(str(CARPETA / f"ventana_movido_{tag}.png"))
    arrastrar(p, -9000, 9000)
    A.reg(AR, f"{tag} · llevarlo mucho más allá del borde: queda dentro de la vista y con los botones", entra(p) and botones_a_la_vista(p),
          f"{p.x()},{p.y()} {p.width()}x{p.height()}")
    arrastrar(p, 9000, -9000)
    A.reg(AR, f"{tag} · y hacia el otro extremo", entra(p) and botones_a_la_vista(p), f"{p.x()},{p.y()}")
    arrastrar(p, -250, 90)
    guardada = v.prefs["vista/posicion_panel_comando"]
    A.reg(AR, f"{tag} · la posición queda en la preferencia", guardada.count(",") == 1 and guardada != "", guardada)
    esquina = (p.x() + p.width(), p.y())
    # clic suelto en la cabecera: no borra lo recordado
    cab = p.findChild(CabeceraMovible)
    QTest.mouseClick(cab, Qt.LeftButton, Qt.NoModifier, QPoint(30, 8))
    A.reg(AR, f"{tag} · un clic suelto en la cabecera no borra la posición", v.prefs["vista/posicion_panel_comando"] == guardada, "")
    # otro comando abre donde quedó (anclado al borde derecho)
    p2 = abrir("revolucion")
    A.reg(AR, f"{tag} · el panel siguiente abre donde se lo dejó", (p2.x() + p2.width(), p2.y()) == esquina and entra(p2) and botones_a_la_vista(p2),
          f"{esquina} vs {(p2.x() + p2.width(), p2.y())}")
    p2.grab().save(str(CARPETA / f"siguiente_{tag}.png"))
    # la ventana cambia de tamaño: el panel sigue entero a la vista
    v.resize(max(700, ancho - 200), max(460, alto - 120))
    A.esperar(150)
    A.reg(AR, f"{tag} · al achicar la ventana, el panel recuerda su lugar pero entra y los botones se ven",
          entra(p2) and botones_a_la_vista(p2), f"ventana {v.width()}x{v.height()}")
    v.resize(ancho, alto)
    A.esperar(150)
    # Tab, Enter y Esc con el panel movido
    clave = next(c.clave for c in p2.campos if type(c).__name__ == "Expresion")
    w = p2.widgets[clave]
    QTest.mouseClick(w, Qt.LeftButton)
    QTest.keyClick(w, Qt.Key_Tab)
    A.reg(AR, f"{tag} · Tab sigue recorriendo los campos del panel movido (no cae en la cabecera)",
          QApplication.focusWidget() is not None and p2.isAncestorOf(QApplication.focusWidget())
          and not isinstance(QApplication.focusWidget(), type(p2.boton_preajustes or p2.boton_ayuda)), type(QApplication.focusWidget()).__name__)
    QTest.keyClick(w, Qt.Key_Escape)
    A.esperar(100)
    A.reg(AR, f"{tag} · Esc cancela el panel movido", v.panel is None, "")
    # doble clic: vuelve a su lugar
    p3 = abrir("extruir")
    cab = p3.findChild(CabeceraMovible)
    evento(cab, QEvent.MouseButtonDblClick, cab.mapToGlobal(QPoint(30, 8)))
    A.esperar(80)
    A.reg(AR, f"{tag} · doble clic en la cabecera lo devuelve a su lugar de siempre (y borra la preferencia)",
          v.prefs["vista/posicion_panel_comando"] == "" and v.area.posicion_panel is None and p3.y() <= v.area.viewcube.y() + v.area.viewcube.height() + 20,
          f"{p3.x()},{p3.y()} pref=«{v.prefs['vista/posicion_panel_comando']}»")
    p3.grab().save(str(CARPETA / f"en_su_lugar_{tag}.png"))
    p3.cancelar()
    A.esperar(60)


def selecciones_a_la_vista():
    doc_ctx = ContextoComando(s.doc)
    malos = []
    for clave, clase in sorted(CATALOGO.items()):
        try:
            campos = clase().campos(doc_ctx)
        except Exception:  # noqa: BLE001 — los que piden otro contexto los cubre la apertura real de abajo
            continue
        malos += [f"{clave}.{c.clave}" for c in campos if isinstance(c, Seleccion) and c.avanzado]
    A.reg(AR, "UI-7 · ninguna selección del catálogo vive en «Más opciones»", not malos, ", ".join(malos))
    for clave, campo in (("nervio", "direccion_desmoldeo"), ("labio", "direccion"), ("alinear", "cuerpos")):
        p = abrir(clave)
        fila = p.filas_sel.get(campo)
        A.reg(AR, f"UI-7 · {clave}: «{campo}» se ve sin abrir «Más opciones»",
              fila is not None and (p.seccion is None or not p.seccion.isAncestorOf(fila)) and p._visible(p._por_clave[campo]),
              f"sección: {'sí' if p.seccion else 'no'}")
        p.grab().save(str(CARPETA / f"ui7_{clave}.png"))
        p.cancelar()


def todo():
    selecciones_a_la_vista()
    for ancho, alto in ((1280, 720), (1024, 640), (800, 520)):
        v.resize(ancho, alto)
        A.esperar(200)
        tag = f"{ancho}x{alto}"
        preajustes(tag)
        movimiento(tag, ancho, alto)


A.correr(AR, todo)
A.reg(AR, "no se escapó ninguna excepción dentro de un slot de Qt", not A.ERRORES, "; ".join(A.ERRORES)[:300])
A.guardar_registro("panel_movible")
fallas = sum(1 for r in A.REGISTRO if not r["ok"])
print(f"=== {len(A.REGISTRO)} comprobaciones, {fallas} con ✗", flush=True)

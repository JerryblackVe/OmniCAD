# -*- coding: utf-8 -*-
"""RS-X1 en la ventana real: un historial de más de 60 pasos, que calcula en el trabajador persistente, usado como lo usa
una persona. Doble clic en el timeline, teclear el valor, Enter, Esc, valor inválido, deshacer y rehacer con el teclado, y
el trabajador que se cae entre dos ediciones y a mitad de una. Eventos simulados, nunca el cursor real."""
import sys
import time

import arnes as A
import teclado as T
from omnicad import api
from omnicad.nucleo import aislado
from omnicad.nucleo import geometria as geo
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

AR = "PASOS LARGOS"
PASOS = 70
s = api.Sesion()
for i in range(PASOS):
    r = api.llamar(s, "create_box", {"length": 10, "width": 8, "height": 6, "x": (i % 10) * 14, "y": (i // 10) * 14})
    assert r["ok"], r
app, v = A.iniciar(s.doc)
tl = v.timeline


def volumen(op_id):
    return geo.volumen(v.doc.estado_final.cuerpos[f"{op_id}.c1"].forma)


def doble_clic(op_id):
    for i in range(tl.lista.count()):
        it = tl.lista.item(i)
        if it.data(Qt.UserRole) == op_id:
            tl.lista.scrollToItem(it)
            A.esperar(60)
            centro = tl.lista.visualItemRect(it).center()
            QTest.mouseClick(tl.lista.viewport(), Qt.LeftButton, Qt.NoModifier, centro)
            A.esperar(60)
            QTest.mouseDClick(tl.lista.viewport(), Qt.LeftButton, Qt.NoModifier, centro)
            A.esperar(200)
            return v.panel
    raise RuntimeError(f"el paso {op_id} no está en el timeline")


def tecla(k):
    QTest.keyClick(v, k, Qt.ControlModifier)
    A.esperar(100)


def medir(f):
    t = time.perf_counter()
    f()
    return time.perf_counter() - t


def editar(op_id, texto):
    panel = doble_clic(op_id)
    T.teclear(panel, "alto", texto)
    A.esperar(500)                      # la previa del panel corre en el trabajador
    return panel


def calentar():
    """El primer cálculo arma el documento en el trabajador; las esperas de abajo son las de siempre."""
    panel = editar("op5", "7 mm")
    QTest.keyClick(panel.widgets["alto"], Qt.Key_Return)
    A.esperar(300)
    A.reg(AR, "doble clic, teclear y Enter editan el paso", abs(volumen("op5") - 560) < 1e-6,
          f"volumen {volumen('op5')}")
    A.reg(AR, "el documento pasa el umbral: lo atiende el trabajador", aislado._trabajador is not None
          and aislado._trabajador.proceso.poll() is None)


def enter_rapido():
    op = "op40"
    panel = editar(op, "9 mm")
    dt = medir(lambda: (QTest.keyClick(panel.widgets["alto"], Qt.Key_Return), A.esperar(1)))
    A.reg(AR, "Enter aplica sin el costo de un hijo nuevo (< 0,5 s)", dt < 0.5, f"{dt:.3f} s")
    A.reg(AR, "el valor quedó en el modelo", abs(volumen(op) - 720) < 1e-6, f"{volumen(op)}")
    A.reg(AR, "el panel se cerró", v.panel is None or not v.panel.isVisible())
    panel = doble_clic(op)
    A.reg(AR, "al reabrir vuelve lo escrito", "9" in panel.widgets["alto"].text(), panel.widgets["alto"].text())
    panel.cancelar()
    A.esperar(100)


def esc_descarta():
    op = "op41"
    antes = volumen(op)
    panel = editar(op, "20 mm")
    QTest.keyClick(panel, Qt.Key_Escape)
    A.esperar(300)
    A.reg(AR, "Esc descarta: el modelo no cambió", volumen(op) == antes, f"{volumen(op)}")
    panel = editar("op42", "5 mm")
    QTest.keyClick(panel.widgets["alto"], Qt.Key_Return)
    A.esperar(300)
    A.reg(AR, "la edición siguiente no arrastra lo descartado", volumen(op) == antes and abs(volumen("op42") - 400) < 1e-6,
          f"{volumen(op)} y {volumen('op42')}")


def valor_invalido():
    op = "op43"
    antes = volumen(op)
    pid = aislado._trabajador.proceso.pid
    panel = editar(op, "-5 mm")
    QTest.keyClick(panel.widgets["alto"], Qt.Key_Return)
    A.esperar(400)
    mensaje = panel.mensaje.text() if panel.mensaje.isVisible() else ""
    A.foto(v, "pasos_largos_valor_invalido")
    A.reg(AR, "un alto negativo avisa o se aplica como en un documento chico, sin cerrar nada a la fuerza",
          bool(mensaje) or not panel.isVisible(), mensaje[:120])
    if panel.isVisible():
        panel.cancelar()
        A.esperar(100)
    A.reg(AR, "el error de la previa no mató al trabajador", aislado._trabajador.proceso.pid == pid)
    if volumen(op) != antes:
        tecla(Qt.Key_Z)


def deshacer_rehacer():
    op = "op44"
    panel = editar(op, "11 mm")
    QTest.keyClick(panel.widgets["alto"], Qt.Key_Return)
    A.esperar(300)
    despues = volumen(op)
    dt = medir(lambda: tecla(Qt.Key_Z))
    A.reg(AR, "Ctrl+Z vuelve el valor (< 0,5 s)", volumen(op) == 480 and dt < 0.5, f"{volumen(op)} en {dt:.3f} s")
    dt = medir(lambda: tecla(Qt.Key_Y))
    A.reg(AR, "Ctrl+Y lo trae (< 0,5 s)", volumen(op) == despues and dt < 0.5, f"{volumen(op)} en {dt:.3f} s")
    t = time.perf_counter()
    for _ in range(10):
        tecla(Qt.Key_Z)
    for _ in range(10):
        tecla(Qt.Key_Y)
    dt = time.perf_counter() - t
    A.reg(AR, "diez Ctrl+Z y diez Ctrl+Y en cadena dejan el mismo modelo (< 6 s)", volumen(op) == despues and dt < 6, f"{dt:.2f} s")


def caida_entre_ediciones():
    pid = aislado._trabajador.proceso.pid
    aislado._trabajador.proceso.kill()
    aislado._trabajador.proceso.wait()
    panel = editar("op45", "4 mm")
    QTest.keyClick(panel.widgets["alto"], Qt.Key_Return)
    A.esperar(800)
    A.reg(AR, "con el trabajador caído entre dos ediciones, arranca otro y la edición sale",
          aislado._trabajador.proceso.pid != pid and abs(volumen("op45") - 320) < 1e-6, f"{volumen('op45')}")


def caida_a_mitad():
    op = "op46"
    antes, pasos = volumen(op), len(v.doc.operaciones)
    A.MODALES.clear()
    panel = editar(op, "13 mm")
    original = aislado._Trabajador._avisar

    def caer(self, tarea):
        original(self, tarea)
        self.proceso.kill()

    aislado._Trabajador._avisar = caer
    v.doc._ultimo_prevuelo = None              # sin el ensayo de la previa: Enter tiene que pedirle el cálculo
    QTest.keyClick(panel.widgets["alto"], Qt.Key_Return)
    A.esperar(800)
    aislado._Trabajador._avisar = original
    A.foto(v, "pasos_largos_caida")
    texto = " ".join(str(m) for m in A.MODALES) + (panel.mensaje.text() if panel.mensaje.isVisible() else "")
    A.reg(AR, "la caída a mitad de un cálculo se informa en español y la app sigue", "sigue andando" in texto, texto[:160])
    A.reg(AR, "el documento quedó como estaba", volumen(op) == antes and len(v.doc.operaciones) == pasos, f"{volumen(op)}")
    if panel.isVisible():
        panel.cancelar()
        A.esperar(100)
    panel = editar(op, "13 mm")
    QTest.keyClick(panel.widgets["alto"], Qt.Key_Return)
    A.esperar(800)
    A.reg(AR, "la edición siguiente sale con un trabajador nuevo", abs(volumen(op) - 1040) < 1e-6, f"{volumen(op)}")
    A.foto(v, "pasos_largos_final")


for nombre, funcion in (("calentar", calentar), ("Enter", enter_rapido), ("Esc", esc_descarta),
                        ("valor inválido", valor_invalido), ("deshacer y rehacer", deshacer_rehacer),
                        ("caída entre ediciones", caida_entre_ediciones), ("caída a mitad", caida_a_mitad)):
    A.correr(f"{AR} · {nombre}", funcion)
proceso = aislado._trabajador.proceso
v.set_documento(api.Sesion().doc)
A.esperar(200)
A.reg(AR, "pasar a un documento chico cierra el trabajador y suelta su memoria",
      aislado._trabajador is None and proceso.poll() is not None and not aislado.formas_recibidas)
A.reg(AR, "sin excepciones sueltas en slots de Qt", not A.ERRORES, "; ".join(A.ERRORES)[:300])
A.guardar_registro("pasos_largos")
fallas = [r for r in A.REGISTRO if not r["ok"]]
print(f"=== {len(A.REGISTRO)} comprobaciones, {len(fallas)} con ✗", flush=True)
v.close()
sys.exit(0)

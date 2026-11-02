# -*- coding: utf-8 -*-
"""Empalme y Chaflán sobre el agujero de un cuerpo de 64 caras o más, como una persona (B-155, RS-X6): la previa va al
trabajador. Teclea valores buenos, imposibles y vacío, arrastra el asa, acepta, deshace y cancela con Esc."""
import sys
import time

import arnes as A
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from teclado import teclear

from omnicad import api
from omnicad.nucleo import aislado, geometria as geo, referencias as refs
from omnicad.nucleo.render_cpu import es_malla

AR = "PREVIA APARTE"
s = api.Sesion()
assert api.llamar(s, "create_box", {"length": 400, "width": 400, "height": 10})["ok"]
puntos = [[-180 + 40 * i, -180 + 40 * j, 10] for i in range(10) for j in range(7)]
assert api.llamar(s, "create_hole", {"face": ">Z", "points": puntos, "diameter": 20, "through_all": True})["ok"]
app, v = A.iniciar(s.doc)
cuerpo = next(iter(v.doc.estado_final.cuerpos))
caras = len(geo.caras(v.doc.estado_final.cuerpos[cuerpo].forma))
A.reg(AR, "el cuerpo pasa el umbral de la previa aparte", caras >= 64, f"{caras} caras")
VOLUMEN = geo.volumen(v.doc.estado_final.cuerpos[cuerpo].forma)


def esperar_previa(p, plazo=60):
    """Espera como la persona: mirando la ventana hasta que deja de decir que calcula. Devuelve los segundos."""
    inicio = time.monotonic()
    while time.monotonic() - inicio < plazo:
        QTest.qWait(10)
        if p._hijo_previa is None and p._pendiente_hijo is None and not p._t_previa.isActive():
            t = time.monotonic() - inicio
            A.esperar(200)                # el panel termina de acomodar su alto con el mensaje nuevo
            return t
    raise RuntimeError("la previa no terminó")


def hay_malla():
    return any(es_malla(c.forma) for c in v.visor._estado.cuerpos.values())


def mover_sim(w, pos):
    p = QPointF(pos)
    QApplication.sendEvent(w, QMouseEvent(QEvent.MouseMove, p, w.mapToGlobal(p), Qt.NoButton, Qt.NoButton, Qt.NoModifier))


def arrastrar(p, desde, hasta, pasos=8):
    g = p.manipuladores
    xy, ok = g.pantalla([desde, hasta])
    if not ok.all():
        return False
    a, b = (QPointF(*q) for q in xy)
    vis = p.visor
    mover_sim(vis, a)
    QApplication.sendEvent(vis, QMouseEvent(QEvent.MouseButtonPress, a, vis.mapToGlobal(a), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier))
    for i in range(1, pasos + 1):
        q = a + (b - a) * (i / pasos)
        QApplication.sendEvent(vis, QMouseEvent(QEvent.MouseMove, q, vis.mapToGlobal(q), Qt.NoButton, Qt.LeftButton, Qt.NoModifier))
        A.esperar(30)
    QApplication.sendEvent(vis, QMouseEvent(QEvent.MouseButtonRelease, b, vis.mapToGlobal(b), Qt.LeftButton, Qt.NoButton, Qt.NoModifier))
    return True


def borde_del_agujero():
    """Punto medio de la arista de arriba de un agujero, cerca del centro de la placa."""
    forma = v.doc.estado_final.cuerpos[cuerpo].forma
    firmas = [refs.firma_arista(a) for a in refs.subformas(forma, "arista")]
    return min((f["medio"] for f in firmas if f["geom"] != "linea" and f["medio"][2] > 9.9),
               key=lambda m: abs(m[0]) + abs(m[1]))


def abrir(clave):
    p = A.abrir(v, clave)
    A.elegir(p, "aristas", A.hit_arista(v, cuerpo, lineal=False, cerca=borde_del_agujero()))
    esperar_previa(p)
    return p


def probar(clave, campo, nombre, valores):
    """`valores`: bueno, imposible, otro bueno. La previa tiene que decir el motivo y seguir andando con el mismo trabajador."""
    bueno, imposible, otro = valores
    n0 = A.n_ops(v)
    p = abrir(clave)
    A.reg(nombre, "la previa va aparte", p._previa_pesada(p.ultima_op))

    teclear(p, campo, bueno)
    t = esperar_previa(p)
    pid = aislado._trabajador.proceso.pid
    A.reg(nombre, f"«{bueno}»: previa correcta con el sólido a la vista", p._previa_ok and hay_malla() and not p.mensaje.text(),
          f"{t:.2f} s; mensaje «{p.mensaje.text()}»")
    A.foto(v, f"previa_{clave}_bueno")

    teclear(p, campo, imposible)
    t = esperar_previa(p)
    texto = p.mensaje.text()
    A.reg(nombre, f"«{imposible}»: el panel dice el motivo real", "falló" in texto and "código" not in texto and "Error" not in texto
          and not p._previa_ok, f"{t:.2f} s; «{texto}»")
    A.reg(nombre, "el texto entra entero en el panel", p.mensaje.height() >= p.mensaje.heightForWidth(p.mensaje.width())
          and len(texto) > 100, f"{p.mensaje.height()} px de alto, {len(texto)} letras")
    A.reg(nombre, "con el valor imposible no queda una previa vieja", not hay_malla())
    A.foto(v, f"previa_{clave}_imposible")

    teclear(p, campo, otro)
    t = esperar_previa(p)
    A.reg(nombre, f"«{otro}» después del imposible: vuelve la previa, en el mismo trabajador",
          p._previa_ok and hay_malla() and not p.mensaje.text() and aislado._trabajador.proceso.pid == pid, f"{t:.2f} s")
    A.foto(v, f"previa_{clave}_otro")

    w = teclear(p, campo, "")
    t = esperar_previa(p)
    A.reg(nombre, "vacío: lo dice en el panel y no calcula", bool(w.styleSheet()) and bool(p.mensaje.text()) and not p._previa_ok,
          f"«{p.mensaje.text()}»")
    A.foto(v, f"previa_{clave}_vacio")

    QTest.keyClicks(w, otro[0])                    # tecleo rápido sobre un cálculo en curso: gana el último valor
    QTest.keyClick(w, Qt.Key_Backspace)
    QTest.keyClicks(w, bueno)
    t = esperar_previa(p)
    A.reg(nombre, "tecleo encima del cálculo: queda el último valor", p._previa_ok and aislado._trabajador.proceso.pid == pid,
          f"{t:.2f} s; valor {p.valores[campo]!r}")

    g = p.manipuladores
    m = g.manips[0]
    antes = p.ctx.evaluar(p.valores[campo])
    medio = sum(m.puntos(g)) / 2
    A.reg(nombre, "asa: se arrastra", arrastrar(p, medio, medio + m.direccion * 2 * (m.factor or 1.0)))
    t = esperar_previa(p)
    despues = p.ctx.evaluar(p.valores[campo])
    A.reg(nombre, "asa: el valor cambia y la previa lo sigue", abs(despues - antes) > 0.1 and p._previa_ok and hay_malla(),
          f"{antes:.2f} → {despues:.2f} mm, {t:.2f} s")
    A.foto(v, f"previa_{clave}_asa")

    QTest.keyClick(p, Qt.Key_Return)
    A.esperar(300)
    forma = v.doc.estado_final.cuerpos[cuerpo].forma
    A.reg(nombre, "Aceptar crea el paso con el sólido exacto", A.n_ops(v) == n0 + 1 and not es_malla(forma) and geo.es_valida(forma)
          and abs(geo.volumen(forma) - VOLUMEN) > 1, f"volumen {geo.volumen(forma):.1f}")
    A.foto(v, f"previa_{clave}_aceptado")
    A.deshacer(v)
    A.reg(nombre, "deshacer vuelve al volumen de antes", A.n_ops(v) == n0 and abs(geo.volumen(v.doc.estado_final.cuerpos[cuerpo].forma) - VOLUMEN) < 1e-6)

    p = abrir(clave)
    teclear(p, campo, otro)
    A.reg(nombre, "Enter con la previa en vuelo no espera", p._hijo_previa is not None or p._t_previa.isActive() or p._previa_ok)
    QTest.keyClick(p, Qt.Key_Return)
    A.esperar(300)
    A.reg(nombre, "...y aplica el valor tecleado", A.n_ops(v) == n0 + 1 and not es_malla(v.doc.estado_final.cuerpos[cuerpo].forma))
    A.deshacer(v)

    p = abrir(clave)
    teclear(p, campo, bueno)
    QTest.keyClick(p, Qt.Key_Escape)
    A.esperar(300)
    A.reg(nombre, "Esc con la previa en vuelo descarta y no deja malla", v.panel is None and A.n_ops(v) == n0 and not hay_malla())
    p = abrir(clave)
    teclear(p, campo, otro)
    t = esperar_previa(p)
    A.reg(nombre, "la previa siguiente al Esc anda, con el mismo trabajador", p._previa_ok and hay_malla()
          and aislado._trabajador.proceso.pid == pid, f"{t:.2f} s")
    QTest.keyClick(p, Qt.Key_Escape)
    A.esperar(200)


A.correr("empalme", lambda: probar("empalme_3d", "radio", "EMPALME", ("5", "32,329", "9,9")))
A.correr("chaflan", lambda: probar("chaflan_3d", "distancia", "CHAFLÁN", ("2", "32,329", "4,5")))
A.reg(AR, "ninguna excepción dentro de un slot de Qt", not A.ERRORES, A.ERRORES[:1])
A.guardar_registro("previa_aparte")
fallas = [r for r in A.REGISTRO if not r["ok"]]
print(f"\n=== {len(A.REGISTRO)} comprobaciones, {len(fallas)} con ✗ ===")
v.doc.modificado = False
v.close()
sys.exit(0)

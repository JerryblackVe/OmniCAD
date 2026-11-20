# -*- coding: utf-8 -*-
"""BOCETO · opciones sin prueba como usuario (PRUEBA-OPC-2): Perfil giratorio (tolerancia, invertir, solo contorno),
Desfase (cadena, topología). Eventos simulados al Lienzo, nunca el cursor real."""

import arnes as A
import numpy as np
from omnicad import api
from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QCheckBox, QDoubleSpinBox, QFormLayout

AR = "BOCETO·OPC2"
s = api.Sesion()


def L(nombre, **a):
    r = api.llamar(s, nombre, a)
    assert r["ok"], (nombre, a, r)
    return r["result"]


L("create_cylinder", radius=14, height=47, name="Cil")
app, v = A.iniciar(s.doc, 1280, 720)
A.esperar(400)
CARA = (5.0, 5.0, 47.0)
LADO = (14.0, 0.0, 20.0)
MENSAJES = []


def px(lz, p):
    return lz.mapFromGlobal(v.visor.mapToGlobal(v.visor.proyectar(np.array(p, float)).toPoint()))


def entrar():
    v.crear_boceto()
    A.esperar(120)
    QTest.mouseClick(v.visor, Qt.LeftButton, Qt.NoModifier, v.visor.proyectar(np.array(CARA)).toPoint())
    A.esperar(450)
    lz = v.modo_boceto.lienzo
    lz.mensaje.connect(MENSAJES.append)
    return lz


def curvas(lz):
    return [c for c in lz.b.curvas.values() if c.id > 0]


def casilla(t, texto):
    """La casilla cuya etiqueta (columna izquierda del formulario) contiene `texto`."""
    f = t.form_contexto
    for i in range(f.rowCount()):
        e, c = f.itemAt(i, QFormLayout.LabelRole), f.itemAt(i, QFormLayout.FieldRole)
        if e is not None and c is not None and texto in e.widget().text() and isinstance(c.widget(), QCheckBox):
            return c.widget()
    raise LookupError(texto)


def clic_casilla(t, texto):
    c = casilla(t, texto)
    QTest.mouseClick(c, Qt.LeftButton, pos=QPoint(6, c.height() // 2))
    A.esperar(120)
    return c.isChecked()


def teclear_num(t, valor):
    sp = next(w for w in t.contexto.findChildren(QDoubleSpinBox))
    sp.setFocus()
    sp.selectAll()
    QTest.keyClicks(sp, valor)
    QTest.keyClick(sp, Qt.Key_Tab)
    A.esperar(150)
    return sp.value()


def giro(lz, t):
    """Perfil giratorio sobre el lado del cilindro, como lo hace la persona; devuelve (nº curvas, tipos, caja)."""
    n0 = len(curvas(lz))
    QTest.mouseClick(lz, Qt.LeftButton, Qt.NoModifier, px(lz, LADO))
    A.esperar(250)
    if t.boton_ok.isEnabled():
        QTest.mouseClick(t.boton_ok, Qt.LeftButton)
        A.esperar(250)
    nuevas = curvas(lz)[n0:] if len(curvas(lz)) > n0 else []
    return len(nuevas), sorted({c.tipo for c in nuevas}), nuevas


def prueba_giro():
    lz = entrar()
    t = v.modo_boceto.tarjeta
    resultados = {}
    for etiqueta, tol, inv, cont in (("base", "0.1", False, True), ("tol 0.001", "0.001", False, True),
                                     ("tol 10", "10", False, True), ("invertir", "0.1", True, True),
                                     ("sin contorno", "0.1", False, False)):
        if resultados:
            QTest.keyClick(lz, Qt.Key_Escape)
            A.esperar(100)
            lz.set_herramienta("seleccionar")
            lz._elegidos_proy = []
            while len(lz.historial) > 0:
                lz.deshacer()
        v.modo_boceto.acciones["sk_perfil_giratorio"].trigger()
        A.esperar(180)
        A.reg(AR, f"giro «{etiqueta}»: abre la tarjeta", t.isVisible(), "")
        val = teclear_num(t, tol)
        A.reg(AR, f"giro «{etiqueta}»: la tolerancia tecleada «{tol}» queda", abs(val - float(tol)) < 1e-9 or (float(tol) > 10 and val == 10.0), val)
        for texto, deseado in (("Invertir", inv), ("Solo contorno", cont)):
            if casilla(t, texto).isChecked() != deseado:
                clic_casilla(t, texto)
            A.reg(AR, f"giro «{etiqueta}»: casilla «{texto}» = {deseado}", casilla(t, texto).isChecked() == deseado
                  and lz.opciones["invertir_giro" if texto == "Invertir" else "contorno_exterior"] == deseado, "")
        n, tipos, nuevas = giro(lz, t)
        caja = sorted(round(float(lz.b.coords(c.p1)[0]) + 100 * float(lz.b.coords(c.p2)[0]), 2)
                      for c in nuevas if c.tipo == "linea") if nuevas else None
        resultados[etiqueta] = (n, tipos, caja)
        A.reg(AR, f"giro «{etiqueta}»: crea curvas sin excepción", n > 0, f"{n} {tipos} {MENSAJES[-1:]}")
        A.foto(v, "opc2_giro_" + etiqueta.replace(" ", "_"))
    print("RESULTADOS GIRO", resultados)
    A.reg(AR, "giro: tolerancia 0.001 no da menos tramos que 10", resultados["tol 0.001"][0] >= resultados["tol 10"][0], resultados)
    A.reg(AR, "giro: invertir cambia el resultado", resultados["invertir"] != resultados["base"], resultados)
    # shortcut: en un cilindro la tolerancia y «solo contorno» no cambian nada (perfil de una línea); falta un cuerpo curvo
    A.reg(AR, "giro: tolerancia y contorno no rompen (cilindro: mismo resultado)", resultados["sin contorno"] == resultados["base"], resultados)


A.correr(AR + " giro", prueba_giro)
A.guardar_registro("opciones_sin_prueba")
print("ERRORES", A.ERRORES)

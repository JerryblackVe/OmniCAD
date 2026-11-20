# -*- coding: utf-8 -*-
"""BOCETO · Insertar DXF y Vectorizar imagen desde sus diálogos (PRUEBA-OPC-2): escala, desplazamiento, ángulo, volteos,
tinta clara, curvas suaves, umbral, suavizado, manchas, tolerancia; valores raros. Eventos simulados; nunca el cursor real."""
import tempfile
from pathlib import Path

import arnes as A
from omnicad import api
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QCheckBox

AR = "INSERTAR·DXF/VEC"
s = api.Sesion()
TMP = Path(tempfile.mkdtemp(prefix="opc2_"))


def L(n, **a):
    r = api.llamar(s, n, a)
    assert r["ok"], (n, a, r)
    return r["result"]


L("create_sketch", name="Fuente", plane="XY")
L("draw_rectangle", sketch="Fuente", x1=0, y1=0, x2=40, y2=20)
L("draw_circle", sketch="Fuente", center_x=60, center_y=10, radius=5)
DXF = TMP / "pieza.dxf"
L("export_sketch", path=str(DXF), sketch="Fuente")
img = QImage(200, 100, QImage.Format_RGB32)
img.fill(QColor("white"))
pt = QPainter(img)
pt.setBrush(QColor("black")); pt.setPen(Qt.NoPen)
pt.drawRect(20, 20, 80, 60)
pt.drawEllipse(130, 20, 50, 50)
pt.setBrush(QColor("#303030")); pt.drawRect(2, 2, 2, 2)          # una mancha de 4 px²
pt.end()
PNG = TMP / "logo.png"
img.save(str(PNG))
INV = TMP / "claro.png"
img.invertPixels(); img.save(str(INV))

L("create_sketch", name="Destino", plane="XY")
app, v = A.iniciar(s.doc, 1440, 900)
A.esperar(300)


def caja_boceto(op):
    b = op.boceto
    xs = [c for p in b.puntos.values() for c in (float(b.coords(p.id)[0]),)] if hasattr(b, "puntos") else []
    return xs


def teclear(w, texto):
    w.setFocus(); w.selectAll()
    if texto:
        QTest.keyClicks(w, texto)
    else:
        QTest.keyClick(w, Qt.Key_Delete)
    A.esperar(200)


def casilla(p, clave, valor):
    c = p.widgets[clave]
    if isinstance(c, QCheckBox) and c.isChecked() != valor:
        QTest.mouseClick(c, Qt.LeftButton, pos=QPoint(6, c.height() // 2)); A.esperar(250)
    return c.isChecked() == valor


def panel(clave, ruta, **campos):
    p = A.abrir(v, clave)
    A.elegir(p, "plano", A.hit_plano(v, "XY"))
    teclear(p.widgets["archivo"], str(ruta))
    for k, val in campos.items():
        w = p.widgets[k]
        if isinstance(w, QCheckBox):
            casilla(p, k, val)
        else:
            n = getattr(w, "numero", w)           # Deslizador: se teclea en su número, como la persona
            teclear(n.lineEdit() if hasattr(n, "lineEdit") else n, str(val))
            QTest.keyClick(n, Qt.Key_Tab); A.esperar(150)
    A.esperar(600)
    return p


def aceptar(p):
    n0 = A.n_ops(v)
    ok = p.boton_ok.isEnabled()
    if ok:
        QTest.mouseClick(p.boton_ok, Qt.LeftButton); A.esperar(700)
    nuevo = A.n_ops(v) - n0
    info = None
    if nuevo:
        op = v.doc.operaciones[-1]
        b = op.p.get("boceto") if hasattr(op, "p") else None
        bo = getattr(op, "boceto", None) or b
        xs = [float(bo.coords(i)[0]) for i in bo.puntos] if bo is not None else []
        ys = [float(bo.coords(i)[1]) for i in bo.puntos] if bo is not None else []
        info = (len(bo.curvas) if bo is not None else 0, round(min(xs), 2), round(max(xs), 2), round(min(ys), 2), round(max(ys), 2)) if xs else (0,)
    return ok, nuevo, info


def mensaje(p):
    try:
        return p.mensaje.text() if p.isVisible() and p.mensaje.isVisible() else ""
    except RuntimeError:
        return "(panel cerrado)"


def cerrar(p):
    try:
        if p.isVisible():
            QTest.keyClick(p, Qt.Key_Escape); A.esperar(200)
    except RuntimeError:
        pass


def deshacer():
    A.deshacer(v); A.esperar(300)


def dxf():
    for nombre, campos, chequeo in (
            ("sin cambios", {}, lambda i: i[0] == 5 and abs((i[2] - i[1]) - 60) < 0.2),
            ("escala 2", {"escala": "2"}, lambda i: abs((i[2] - i[1]) - 120) < 0.2),
            ("escala 0,5 con coma", {"escala": "0,5"}, lambda i: abs((i[2] - i[1]) - 30) < 0.2),
            ("escala 25.4 mm→", {"escala": "1/25.4"}, lambda i: abs((i[2] - i[1]) - 60 / 25.4) < 0.2),
            ("desplazamiento 10,5", {"dx": "10", "dy": "5"}, lambda i: abs(i[1] - 10) < 0.2 and abs(i[3] - 5) < 0.2),
            ("ángulo 90", {"angulo": "90"}, lambda i: abs((i[4] - i[3]) - 60) < 0.3),
            ("volteo H", {"voltear_h": True}, lambda i: abs(i[1] - 5) < 0.2 and abs(i[2] - 65) < 0.2),
            ("volteo V", {"voltear_v": True}, lambda i: abs(i[3]) < 0.2 and abs(i[4] - 20) < 0.2)):
        p = panel("insertar_dxf", DXF, **campos)
        ok, nuevo, info = aceptar(p)
        A.reg(AR, f"DXF «{nombre}»: acepta y crea 1 boceto", ok and nuevo == 1 and info is not None, f"botón={ok} nuevo={nuevo} {info}")
        if info:
            A.reg(AR, f"DXF «{nombre}»: medidas esperadas", chequeo(info), info)
            A.foto(v, "dxf_" + nombre.split()[0] + str(len(nombre)))
            deshacer()
        else:
            cerrar(p)
    # valores raros
    for nombre, campos, debe in (("escala 0", {"escala": "0"}, False), ("escala -1", {"escala": "-1"}, False),
                                 ("escala 1e9", {"escala": "1e9"}, False), ("escala abc", {"escala": "abc"}, False),
                                 ("escala vacía", {"escala": ""}, False), ("ángulo 720", {"angulo": "720"}, True)):
        p = panel("insertar_dxf", DXF, **campos)
        ok, nuevo, info = aceptar(p)
        msg = mensaje(p)
        A.reg(AR, f"DXF raro «{nombre}»: {'acepta' if debe else 'rechaza con mensaje'}", (nuevo == 1) == debe and (debe or bool(msg)), f"{ok} {nuevo} {info} «{msg}»")
        if nuevo:
            deshacer()
        else:
            cerrar(p)
    for nombre, ruta in (("archivo inexistente", TMP / "no_existe.dxf"), ("archivo vacío", TMP / "vacio.dxf"), ("basura", TMP / "basura.dxf")):
        if nombre == "archivo vacío":
            ruta.write_text("")
        if nombre == "basura":
            ruta.write_text("esto no es un dxf\n" * 5)
        p = panel("insertar_dxf", ruta)
        ok, nuevo, info = aceptar(p)
        msg = mensaje(p)
        A.reg(AR, f"DXF «{nombre}»: no crea nada y avisa", nuevo == 0 and bool(msg), f"{ok} {nuevo} «{msg}»")
        cerrar(p)


def vec():
    resultados = {}
    for nombre, ruta, campos, chequeo in (
            ("base", PNG, {}, lambda i: i[0] >= 2),
            ("tinta clara sobre imagen invertida", INV, {"invertir": True}, lambda i: i[0] >= 2),
            ("sin invertir sobre imagen clara", INV, {}, None),
            ("curvas suaves", PNG, {"curvas": True}, lambda i: i[0] >= 2),
            ("ancho 50", PNG, {"ancho": "50"}, lambda i: abs((i[2] - i[1]) - 50) < 1.5),
            ("umbral 10 (solo lo más negro)", PNG, {"umbral": 10}, None),
            ("umbral 250", PNG, {"umbral": 250}, None),
            ("tolerancia 0", PNG, {"tolerancia": 0}, None),
            ("tolerancia 10", PNG, {"tolerancia": 10}, None),
            ("curvas + tolerancia 0", PNG, {"curvas": True, "tolerancia": 0}, None),
            ("curvas + tolerancia 10", PNG, {"curvas": True, "tolerancia": 10}, None),
            ("curvas + esquina 90", PNG, {"curvas": True, "angulo_esquina": 90}, None),
            ("curvas + esquina 30", PNG, {"curvas": True, "angulo_esquina": 30}, None),
            ("curvas + esquina 180", PNG, {"curvas": True, "angulo_esquina": 180}, None),
            ("manchas 100000 (ignora todo)", PNG, {"area_minima": 100000}, None),
            ("suavizado 10", PNG, {"suavizado": 10}, None)):
        p = panel("vectorizar_imagen", ruta, **campos)
        ok, nuevo, info = aceptar(p)
        resultados[nombre] = (ok, nuevo, info)
        msg = mensaje(p)
        A.reg(AR, f"Vectorizar «{nombre}»: sin excepción", not A.ERRORES, f"botón={ok} nuevo={nuevo} {info} «{msg}»")
        if chequeo is not None:
            A.reg(AR, f"Vectorizar «{nombre}»: resultado esperado", bool(info) and chequeo(info), f"{info} «{msg}»")
        if nuevo:
            A.foto(v, "vec_" + str(len(resultados)))
            deshacer()
        else:
            cerrar(p)
    print("RESULTADOS VEC", resultados)
    n = lambda k: (resultados[k][2] or (0,))[0]
    A.reg(AR, "Vectorizar: «Curvas suaves» cambia el trazado (menos curvas o splines)", resultados["curvas suaves"] != resultados["base"], (resultados["curvas suaves"], resultados["base"]))
    A.reg(AR, "Vectorizar: manchas 100000 deja menos contornos que la base", n("manchas 100000 (ignora todo)") < n("base"), (n("manchas 100000 (ignora todo)"), n("base")))
    A.reg(AR, "Vectorizar: tolerancia 10 ≤ curvas/puntos que tolerancia 0 (simplifica)", resultados["tolerancia 10"][2] != resultados["tolerancia 0"][2], (resultados["tolerancia 10"], resultados["tolerancia 0"]))
    for nombre, ruta in (("imagen corrupta", TMP / "mala.png"), ("inexistente", TMP / "nada.png")):
        if nombre == "imagen corrupta":
            ruta.write_bytes(b"\x89PNG basura")
        p = panel("vectorizar_imagen", ruta)
        ok, nuevo, info = aceptar(p)
        msg = mensaje(p)
        A.reg(AR, f"Vectorizar «{nombre}»: no crea nada y avisa", nuevo == 0 and bool(msg), f"{ok} {nuevo} «{msg}»")
        cerrar(p)


import sys  # noqa: E402
if "solo-vec" not in sys.argv:
    A.correr(AR + " DXF", dxf)
A.correr(AR + " Vectorizar", vec)
A.guardar_registro("opciones_dxf_vectorizar")
print("ERRORES", A.ERRORES)

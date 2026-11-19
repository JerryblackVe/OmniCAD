# -*- coding: utf-8 -*-
"""BOCETO · Texto y panel CARÁCTER sin prueba como usuario (PRUEBA-TEXTO-SIM, E7): Contenido y Parámetro de texto,
Familia tipográfica (lista, búsqueda escrita, nombre inexistente) con el Filtro de fuentes, y el Pivote de giro de las 6
opciones (el punto elegido no se mueve al girar). Valores raros: texto vacío, ángulo enorme o negativo, fuente que no
existe. Contra Fusion (Sketch > Create > Text). Eventos simulados al Lienzo y a los widgets (nunca el cursor real)."""
import math
import sys
import time

import arnes as A
from omnicad import api
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

AR = "BOCETO·TEXTO"
s = api.Sesion()
api.llamar(s, "create_sketch", {"plane": "XY", "name": "T"})
app, v = A.iniciar(s.doc, 1280, 720)
A.esperar(400)
v.editar_operacion(s.paso("T").id)
A.esperar(500)
lz = v.modo_boceto.lienzo
MS = []
lz.mensaje.connect(MS.append)
lz.visor.objetivo = lz.plano.a_3d(20, 0)
lz.visor.distancia = 120 / 2 / math.sin(math.radians(lz.visor.fov) / 2) * 1.3
lz.visor.update()
A.esperar(300)
panel = v.modo_boceto.caracter


def tecla(k, mod=Qt.NoModifier):
    A.activar(v)
    QTest.keyClick(lz, k, mod)
    A.esperar(200)


def textos():
    return [c for c in lz.b.curvas.values() if type(c).__name__ == "Texto"]


def texto_con_marco(contenido="PIVOTE"):
    """Un texto con marco. En la ventana no hay cómo agregarlo (solo la API): se lo da el boceto, como add_text frame=true."""
    nuevo = nuevo_texto(contenido)
    if nuevo:
        lz.aplicar_cambio(lambda: lz.b.agregar_marco_texto(nuevo[0].id, 30, 8))
    return nuevo


def nuevo_texto(contenido="HOLA", angulo="0"):
    """Texto con marco (dos clics), contenido y ángulo tecleados en la barra, Enter."""
    n0 = len(textos())
    lz.set_herramienta("texto")
    lz.clics.append((None, (0.0, -10.0)))
    lz.clics.append((None, (40.0, 10.0)))
    lz._procesar_clics()
    A.esperar(200)
    c = lz.entrada.campos
    c[0].setText(contenido)
    c[2].setText(angulo)
    A.esperar(120)
    QTest.keyClick(c[0], Qt.Key_Return)
    A.esperar(250)
    return textos()[n0:]


def probar(nombre, f):
    try:
        f()
    except Exception as e:                                                              # noqa: BLE001
        A.reg(AR, f"{nombre}: sin excepción", False, f"{type(e).__name__}: {e} @ L{e.__traceback__.tb_next.tb_lineno if e.__traceback__.tb_next else '?'}")
    if lz.entrada is not None:
        tecla(Qt.Key_Escape)
    lz.set_herramienta("seleccionar")


# ================================================================ 1) contenido y parámetro
def contenido():
    lz.set_herramienta("texto")
    lz.clics.append((None, (0.0, -10.0)))
    lz.clics.append((None, (40.0, 10.0)))
    lz._procesar_clics()
    A.esperar(200)
    A.reg(AR, "con la herramienta Texto el panel CARÁCTER se ve", panel.isVisible(), "")
    A.reg(AR, "el texto nuevo no tiene parámetro ligado", "Sin parámetro" in panel.parametro_texto.text(), panel.parametro_texto.text())
    lz.entrada.campos[0].setText("ABC")
    A.esperar(150)
    A.reg(AR, "Contenido del panel copia lo escrito en el cuadro del visor", panel.valor_parametro_texto.text() == "ABC",
          panel.valor_parametro_texto.text())
    t0 = time.perf_counter()
    QTest.keyClick(lz.entrada.campos[0], Qt.Key_Return)
    A.esperar(250)
    dt = time.perf_counter() - t0 - 0.25
    t = textos()[-1]
    A.reg(AR, "Enter crea el texto con el contenido", t.texto == "ABC", t.texto)
    A.reg(AR, "el primer texto de la sesión se crea en menos de 1 s", dt < 1.0, f"{dt:.2f} s")
    tecla(Qt.Key_Z, Qt.ControlModifier)
    A.reg(AR, "Ctrl+Z lo saca en un paso", not [x for x in textos() if x.texto == "ABC"], len(textos()))
    # texto vacío: no crea y lo dice
    n0 = len(textos())
    nuevo_texto("", "0")
    A.reg(AR, "texto vacío: no crea nada y avisa", len(textos()) == n0 and any("vac" in m for m in MS[-3:]), f"{len(textos()) - n0}; {MS[-1:]}")
    if lz.entrada is not None:
        tecla(Qt.Key_Escape)
    # texto raro: salto de línea escapado, unicode, larguísimo
    for raro in ("A\\nB", "ñÁ€", "X" * 400):
        n0 = len(textos())
        t0 = time.perf_counter()
        nuevo = nuevo_texto(raro)
        dt = time.perf_counter() - t0
        A.reg(AR, f"texto «{raro[:12]}…»: crea sin error", len(nuevo) == 1 and lz.resultado.ok and not A.ERRORES, f"{len(nuevo)}; {dt:.2f} s")
        if len(raro) > 100:
            A.reg(AR, "un texto de 400 letras se crea en menos de 1 s (la ventana no se congela)", dt < 1.0, f"{dt:.2f} s")
        if nuevo:
            tecla(Qt.Key_Z, Qt.ControlModifier)


probar("contenido", contenido)


# ================================================================ 2) familia y filtro
def familia():
    lz.set_herramienta("texto")
    A.esperar(150)
    n = panel.fuente.count()
    A.reg(AR, "la lista de familias trae fuentes", n > 0, n)
    for i in range(panel.filtro.count()):
        panel.filtro.setCurrentIndex(i)
        A.esperar(150)
        A.reg(AR, f"Filtro «{panel.filtro.itemText(i)}»: lista válida y sin excepción", panel.fuente.count() >= 1 and not A.ERRORES,
              f"{panel.fuente.count()} familias")
    panel.filtro.setCurrentIndex(0)
    A.esperar(150)
    # elegir otra familia por la lista
    if panel.fuente.count() > 1:
        panel.fuente.setCurrentIndex(1)
        A.esperar(200)
        A.reg(AR, "elegir una familia la deja en las opciones", lz.opciones["fuente"] == panel.fuente.itemText(1), lz.opciones["fuente"])
    # búsqueda escrita: parte del nombre, inexistente, vacío
    panel.fuente.lineEdit().setFocus()
    for escrito in ("Ari", "zzzzNoExiste", ""):
        panel.fuente.lineEdit().selectAll()
        QTest.keyClicks(panel.fuente.lineEdit(), escrito)
        QTest.keyClick(panel.fuente.lineEdit(), Qt.Key_Return)
        A.esperar(200)
        A.reg(AR, f"familia escrita «{escrito}»: sin excepción", not A.ERRORES, f"{lz.opciones.get('fuente')!r}")
    # un texto con una fuente inexistente no revienta el boceto
    lz.opciones["fuente"] = "FuenteQueNoExiste"
    nuevo = nuevo_texto("HOLA")
    A.reg(AR, "fuente inexistente: crea el texto (cae a otra) o avisa; nunca excepción", (len(nuevo) == 1 or MS) and not A.ERRORES, f"{len(nuevo)}; {MS[-1:]}")
    if nuevo:
        A.reg(AR, "con fuente inexistente el texto tiene geometría", lz.resultado.ok, "")
        tecla(Qt.Key_Z, Qt.ControlModifier)
    lz.opciones["fuente"] = panel.fuente.itemText(0)


probar("familia", familia)


# ================================================================ 3) pivote de giro (6 opciones)
def pivotes():
    for i in range(panel.pivote.count()):
        dato = panel.pivote.itemData(i)
        nuevo = texto_con_marco()
        if not nuevo:
            A.reg(AR, f"pivote {dato}: se pudo crear el texto", False, MS[-1:])
            continue
        t = nuevo[0]
        lz.editar_texto(t.id, lz.a_px(20, 0))
        A.esperar(250)
        panel.pivote.setCurrentIndex(i)
        A.esperar(150)
        corner = dato.removeprefix("corner:") if dato else None
        antes = lz.b.esquina_marco(t.id, corner) if corner else lz.b.coords(t.punto)
        lz.entrada.campos[2].setText("30")
        A.esperar(120)
        QTest.keyClick(lz.entrada.campos[0], Qt.Key_Return)
        A.esperar(300)
        despues = lz.b.esquina_marco(t.id, corner) if corner else lz.b.coords(t.punto)
        giro = lz.b.angulo_texto(t.id)
        A.reg(AR, f"pivote «{panel.pivote.itemText(i)}»: el texto gira 30° y el punto elegido no se mueve",
              abs(giro - 30) < 1e-6 and math.dist(antes, despues) < 1e-6, f"ángulo {giro}; {antes} -> {despues}; {MS[-1:]}")
        A.foto(v, f"texto_pivote_{(corner or 'ancla')}")
        tecla(Qt.Key_Z, Qt.ControlModifier)
        tecla(Qt.Key_Z, Qt.ControlModifier)
    # ángulos raros con el pivote del centro
    panel.pivote.setCurrentIndex(panel.pivote.findData("corner:center"))
    for ang in ("-90", "360", "720.5", "1e6", "abc", ""):
        nuevo = nuevo_texto("GIRO", "0")
        if not nuevo:
            continue
        lz.editar_texto(nuevo[0].id, lz.a_px(20, 0))
        A.esperar(250)
        lz.entrada.campos[2].setText(ang)
        QTest.keyClick(lz.entrada.campos[0], Qt.Key_Return)
        A.esperar(250)
        A.reg(AR, f"ángulo «{ang}» con pivote centro: sin excepción y el texto sigue válido", not A.ERRORES and lz.resultado.ok,
              f"ángulo {lz.b.angulo_texto(nuevo[0].id)}; {MS[-1:]}")
        if lz.entrada is not None:
            tecla(Qt.Key_Escape)
        tecla(Qt.Key_Z, Qt.ControlModifier)
        tecla(Qt.Key_Z, Qt.ControlModifier)


probar("pivotes", pivotes)

# ================================================================ 4) el resto del panel CARÁCTER (valores normales y raros)
def teclear_spin(sp, texto):
    le = sp.lineEdit()
    le.setFocus()
    le.selectAll()
    QTest.keyClicks(le, texto)
    QTest.keyClick(le, Qt.Key_Tab)
    A.esperar(120)


def con_panel(f):
    """Abre un texto nuevo (barra abierta), deja que `f` toque el panel y acepta con Enter; devuelve el texto."""
    n0 = len(textos())
    lz.set_herramienta("texto")
    lz.clics.append((None, (0.0, -10.0)))
    lz.clics.append((None, (40.0, 10.0)))
    lz._procesar_clics()
    A.esperar(250)
    lz.entrada.campos[0].setText("Hola Mundo")
    f()
    QTest.keyClick(lz.entrada.campos[0], Qt.Key_Return)
    A.esperar(300)
    return textos()[n0:]


def ancla_combo():
    return next(c for c in panel.findChildren(type(panel.pivote)) if c.findData("medio") >= 0)


def panel_resto():
    # (nombre, clave en el texto, cómo tocarlo, valor tecleado, valor esperado)
    spins = [("Tamaño / altura", "altura", panel.altura, "12", 12.0), ("Inclinación", "inclinacion", panel.inclinacion, "20", 20.0),
             ("Línea base", "desfase_base", panel.base, "3", 3.0), ("Ancho %", "escala_h", panel.escala_h, "150", 150.0), ("Alto %", "escala_v", panel.escala_v, "80", 80.0),
             ("Grosor decoración", "grosor_decoracion", panel.grosor, "0.5", 0.5), ("Interlineado", "interlineado", panel.interlineado, "2", 2.0)]
    for nombre, clave, sp, escrito, esperado in spins:
        n = con_panel(lambda sp=sp, e=escrito: teclear_spin(sp, e))
        ok = bool(n) and abs(float(getattr(n[0], clave)) - esperado) < 1e-6
        A.reg(AR, f"{nombre} = {escrito}: el texto lo guarda", ok, f"{getattr(n[0], clave, None) if n else 'sin texto'}; {MS[-1:]}")
        if n:
            tecla(Qt.Key_Z, Qt.ControlModifier)
        # valores raros: se sujetan al rango del campo, nunca excepción ni texto roto
        for raro in ("-99999", "1e12", "abc", "0"):
            n = con_panel(lambda sp=sp, e=raro: teclear_spin(sp, e))
            A.reg(AR, f"{nombre} = «{raro}»: sin excepción y el texto sigue válido", not A.ERRORES and lz.resultado.ok,
                  f"{getattr(n[0], clave, None) if n else 'sin texto'}; campo={sp.value()}")
            if lz.entrada is not None:
                tecla(Qt.Key_Escape)
            if n:
                tecla(Qt.Key_Z, Qt.ControlModifier)
    combos = [("Subrayado", "subrayado", panel.subrayado), ("Tachado", "tachado", panel.tachado),
              ("Mayúsculas y minúsculas", "capitalizacion", panel.capitalizacion), ("Anclaje", "ancla_v", ancla_combo())]
    for nombre, clave, cb in combos:
        for i in range(cb.count()):
            dato = cb.itemData(i)
            n = con_panel(lambda cb=cb, i=i: cb.setCurrentIndex(i))
            A.reg(AR, f"{nombre} «{cb.itemText(i)}» (texto con cuadro dibujado): el texto lo guarda",
                  bool(n) and getattr(n[0], clave) == dato and lz.resultado.ok, f"{getattr(n[0], clave, None) if n else 'sin texto'}")
            if n:
                tecla(Qt.Key_Z, Qt.ControlModifier)
        cb.setCurrentIndex(0)
    # kerning de la fuente (V/A) y de un par, espaciado de caracteres
    for nombre, f in (("Kerning V/A", lambda: panel.b_kerning.setChecked(not panel.b_kerning.isChecked())),
                      ("Espaciado de caracteres 50 %", lambda: teclear_spin(panel.interletraje, "50")),
                      ("Espaciado de caracteres -100 %", lambda: teclear_spin(panel.interletraje, "-100"))):
        n = con_panel(f)
        A.reg(AR, f"{nombre}: el texto se crea sin error", bool(n) and lz.resultado.ok and not A.ERRORES, f"{MS[-1:]}")
        if n:
            tecla(Qt.Key_Z, Qt.ControlModifier)


probar("panel resto", panel_resto)

A.reg(AR, "ninguna excepción en un slot de Qt", not A.ERRORES, A.ERRORES[:1])
A.guardar_registro("boceto_texto_panel")
print(f"\n=== {len(A.REGISTRO)} comprobaciones, {len([r for r in A.REGISTRO if not r['ok']])} con ✗ ===", flush=True)
v.doc.modificado = False
v.close()
sys.exit(0)

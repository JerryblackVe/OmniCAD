# -*- coding: utf-8 -*-
"""Herramientas de SÓLIDO iguales a Fusion (CAP-1 a CAP-12), en la ventana real y como una persona: clics en la vista, botones,
tecleo en los campos, Enter, Esc, Tab, reabrir, deshacer y ventana chica. Deja una captura de cada panel para compararla con
las de Fusion."""
import sys

import numpy as np
from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLineEdit, QSpinBox

import arnes as A
import escena
from omnicad import api

s, ids = escena.construir()
app, v = A.iniciar(s.doc)
AR = "HERRAMIENTAS"
caja, cil = ids["caja"], ids["cil"]


def raton(tipo, p, boton=Qt.NoButton, botones=Qt.NoButton):
    q = QPointF(float(p[0]), float(p[1]))
    QApplication.sendEvent(v.visor, QMouseEvent(tipo, q, q, boton, botones, Qt.NoModifier))


def mover(p):
    raton(QEvent.MouseMove, p)


def clic(p):
    raton(QEvent.MouseButtonPress, p, Qt.LeftButton, Qt.LeftButton)
    raton(QEvent.MouseButtonRelease, p, Qt.LeftButton)


def teclear(w, texto, tecla=Qt.Key_Tab):
    w.setFocus()
    w.selectAll()
    QTest.keyClicks(w, texto)
    QTest.keyClick(w, tecla)
    A.esperar(120)


def foto(panel, nombre):
    panel.grab().save(str(A.CAPTURAS / f"panel_{nombre}.png"))


def volumen(cid):
    return v.doc.estado_final.cuerpos[cid].forma


def medir(cid):
    return round(A.geo.volumen(volumen(cid)), 3)


def punto_del_plano(px):
    o, r = v.visor.rayo(QPoint(*px))
    return np.asarray(o) + np.asarray(r) * (-o[2] / r[2])


# ---------------------------------------------------------------- CAP-2: Rosca con 18 tipos, Designación y Biblioteca
def rosca():
    antes = medir(cil)
    p = A.abrir(v, "rosca")
    A.elegir(p, "caras", A.hit_cara(v, cil, normal=None))
    A.esperar()
    tipo = p.widgets["tipo_rosca"]
    A.reg(AR, "Rosca ofrece los 18 tipos en una cara exterior", tipo.count() == 18, tipo.count())
    p.widgets["modelada"].click()
    foto(p, "rosca")
    p.widgets["biblioteca"].mas.click()
    A.esperar(150)
    dlg = p.biblioteca
    dlg.tipo.setCurrentIndex(dlg.tipo.findData("gb_metrica"))
    teclear(dlg.filtro, "20x")
    dlg.tabla.selectRow(0)
    elegida = dlg.elegida()
    A.reg(AR, "la biblioteca filtra y deja elegir", bool(elegida) and dlg.seleccionar.isEnabled(), elegida)
    dlg.grab().save(str(A.CAPTURAS / "panel_rosca_biblioteca.png"))
    dlg.seleccionar.click()
    A.esperar()
    A.reg(AR, "Seleccionar aplica tipo y designación", (p.valores["tipo_rosca"], p.valores["des_tipo_rosca"]) == ("gb_metrica", elegida), p.valores["des_tipo_rosca"])
    p.set_valores({"tipo_rosca": "iso_metrica", "tam_iso_metrica": "M20", "des_tipo_rosca": "M20x2.5"})
    A.esperar(300)
    p.aceptar()
    A.esperar(1500)
    A.reg(AR, "rosca modelada M20 saca material", medir(cil) < antes, (antes, medir(cil)))
    A.deshacer(v)
    A.reg(AR, "deshacer la rosca vuelve al volumen", abs(medir(cil) - antes) < 1e-3)


# ---------------------------------------------------------------- CAP-10: botones con ícono
def agujero():
    p = A.abrir(v, "agujero")
    fila = p.widgets["tipo"]
    fila.boton("avellanado").click()
    A.esperar(150)
    A.reg(AR, "Agujero: un clic en el ícono cambia el tipo", p.valores["tipo"] == "avellanado")
    foto(p, "agujero")
    QTest.keyClick(p, Qt.Key_Escape)
    A.esperar(200)


# ---------------------------------------------------------------- CAP-8: dibujar con el mouse
def dibujar(clave, campo, verificar):
    n = A.n_ops(v)
    p = A.abrir(v, clave)
    c = next(x for x in p.campos if x.clave == campo)
    p._activar(c)
    centro = (v.visor.width() // 2, v.visor.height() // 2)
    p._elegida(dict(A.hit_plano(v, "XY"), punto=punto_del_plano(centro)))
    A.esperar(100)
    A.reg(AR, f"{clave}: el clic en el plano empieza a dibujar", p.manipuladores.trazo is not None)
    otro = (centro[0] + 80, centro[1] - 40)
    mover((centro[0] + 40, centro[1] - 20))
    mover(otro)
    A.esperar(200)
    clic(otro)
    A.esperar(200)
    A.reg(AR, f"{clave}: el segundo clic fija la medida", p.manipuladores.trazo is None and verificar(p), {k: p.valores.get(k) for k in ("diametro", "ancho", "largo")})
    foto(p, clave)
    p.aceptar()
    A.esperar(500)
    A.reg(AR, f"{clave}: Aceptar deja el paso", A.n_ops(v) == n + 1)
    A.deshacer(v)


# ---------------------------------------------------------------- CAP-3, CAP-7: Solevación
def solevacion():
    p = A.abrir(v, "solevacion")
    A.elegir(p, "secciones", A.hit_perfil(v, s, "Circ"), A.hit_perfil(v, s, "Circ2"))
    A.esperar(400)
    tabla = p.filas_sel["secciones"].tabla
    A.reg(AR, "Solevación: una fila por perfil con su condición", tabla.rowCount() == 2 and tabla.cellWidget(0, 1) is not None)
    foto(p, "solevacion")
    p.filas_sel["secciones"].tabla.selectRow(0)
    tabla.cellWidget(0, 1).setCurrentIndex(1)
    A.esperar(300)
    A.reg(AR, "la condición Dirección abre sus valores", p._visible(p._por_clave["angulo_inicio"]))
    teclear(p.widgets["angulo_inicio"], "80 deg")
    tabla.cellWidget(0, 1).setCurrentIndex(0)
    p.barra_pestanas.setCurrentIndex(1)
    A.esperar(100)
    p.widgets["ana_tipo"].boton("cebra").click()
    A.esperar(500)
    A.reg(AR, "pestaña Análisis: la cebra pinta la vista previa", v.visor.funcion_colores is not None)
    foto(p, "solevacion_analisis")
    teclear(p.widgets["ana_frecuencia"].numero, "40")
    A.reg(AR, "Repetición: número y deslizador juntos", p.widgets["ana_frecuencia"].deslizador.value() == 40)
    p.widgets["ana_tipo"].boton("isocurva").click()
    A.esperar(400)
    p.widgets["ana_peines"].click()
    A.esperar(400)
    foto(p, "solevacion_isocurva")
    p.cancelar()
    A.esperar(300)
    A.reg(AR, "cerrar sin aceptar no deja análisis", v.visor.funcion_colores is None)


# ---------------------------------------------------------------- CAP-1: Editar cara
def editar_cara():
    antes = medir(caja)
    p = A.abrir(v, "editar_cara")
    A.elegir(p, "cara", A.hit_cara(v, caja, normal=(0, 0, 1)))
    A.esperar(300)
    foto(p, "editar_cara")
    n = p.widgets["n_u"]
    assert isinstance(n, QSpinBox)
    teclear(n.lineEdit(), "2")
    teclear(p.widgets["n_v"].lineEdit(), "2")
    A.esperar(300)
    g = p.manipuladores.manips[0]
    pix, ok = p.manipuladores.pantalla([g.puntos[2, 2]])
    A.reg(AR, "Editar cara: la grilla se ve", bool(ok[0]) and g.puntos.shape[:2] == (5, 5), g.puntos.shape)
    p.set_valor("filtro", "vertice")
    mover(pix[0])
    clic(pix[0])
    A.esperar(200)
    A.reg(AR, "clic en un punto lo elige", p.comando.sel == {(2, 2)}, p.comando.sel)
    A.foto(v, "editar_cara_elegido")
    p.plegables["Entradas numéricas"].boton.setChecked(True)
    A.esperar(100)
    dz = p.widgets["dz"]
    assert isinstance(dz, QLineEdit)
    teclear(dz, "abc")
    A.reg(AR, "un valor malo queda en rojo y no mueve nada", not p.valores.get("despl"))
    teclear(dz, "6 mm")
    A.esperar(500)
    A.reg(AR, "teclear Z mueve el punto", p.valores["despl"].get("2,2") == [0.0, 0.0, 6.0], p.valores.get("despl"))
    A.foto(v, "editar_cara_movido")
    A.activar(v)
    QTest.keyClick(v, Qt.Key_W, Qt.AltModifier)
    A.esperar(100)
    A.reg(AR, "Alt+W pasa a Traslación", p.valores["modo"] == "traslacion", p.valores["modo"])
    p.widgets["comprobar"].click()
    A.esperar(300)
    A.reg(AR, "Comprobación de vista preliminar oculta la grilla", not p.manipuladores.manips)
    p.widgets["comprobar"].click()
    p.aceptar()
    A.esperar(700)
    despues = medir(caja)
    A.reg(AR, "Aceptar deja el cuerpo válido con más volumen", despues > antes and A.geo.es_valida(volumen(caja)), (antes, despues))
    op = v.doc.operaciones[-1]
    v.editar_operacion(op.id)
    A.esperar(500)
    r = v.panel
    A.reg(AR, "reabrir el paso conserva la forma", r.valores["despl"] == op.p["desplazamientos"] and r.valores["n_u"] == 2)
    QTest.keyClick(r, Qt.Key_Escape)
    A.esperar(300)
    A.deshacer(v)
    A.reg(AR, "deshacer vuelve al volumen", abs(medir(caja) - antes) < 1e-3)
    v.acciones["rehacer"].trigger()
    A.esperar(300)
    A.reg(AR, "rehacer vuelve a la cara editada", abs(medir(caja) - despues) < 1e-3)
    A.deshacer(v)


# ---------------------------------------------------------------- ventana chica y capturas
def ventana_chica():
    for ancho, alto in ((1024, 640), (800, 520)):
        v.resize(ancho, alto)
        A.esperar(300)
        for clave in ("solevacion", "editar_cara", "rosca", "agujero"):
            p = A.abrir(v, clave)
            A.esperar(200)
            boton = p.btn_aceptar if hasattr(p, "btn_aceptar") else None
            ok = p.geometry().bottom() <= p.parent().height() + 1 if p.parent() else True
            A.reg(AR, f"{clave} entra con Aceptar en {ancho}×{alto}", ok and (boton is None or boton.isVisible()))
            p.cancelar()
            A.esperar(100)
    v.resize(1900, 1000)
    A.esperar(300)


def capturas():
    for clave in ("extruir", "revolucion", "barrido", "bobina", "toroide", "cilindro", "esfera", "caja", "tuberia", "red", "nervio", "vaciado",
                  "desmoldeo", "combinar", "engrosar", "escala_3d", "mover_copiar", "alinear", "division_silueta", "dividir_cara", "dividir_cuerpo",
                  "reemplazar_cara", "relleno_contorno", "patron_rectangular_3d", "simetria_3d", "cebra", "mapa_curvatura", "isocurva"):
        try:
            p = A.abrir(v, clave)
            A.esperar(120)
            foto(p, clave)
            p.cancelar()
            A.esperar(80)
        except Exception as e:  # noqa: BLE001 — una captura que falla se anota y siguen las otras
            A.reg(AR, f"captura de {clave}", False, str(e))


# ---------------------------------------------------------------- B-116 y B-117: la flecha que se mete en el cuerpo
def _api(nombre, **args):
    r = api.llamar(s, nombre, args)
    assert r["ok"], (nombre, args, r)
    return r["result"]


def _navegador():
    arbol = v.navegador.arbol

    def textos(it):
        yield it.text(0)
        for j in range(it.childCount()):
            yield from textos(it.child(j))
    return [t for i in range(arbol.topLevelItemCount()) for t in textos(arbol.topLevelItem(i))]


def _arrastrar_flecha(p, valor, captura=None):
    """La flecha de la distancia con eventos de mouse al visor: agarrar, varios movimientos, soltar en `valor` mm."""
    g = p.manipuladores
    flecha = next(m for m in g.manips if getattr(m, "clave", None) == "distancia")
    base, punta = flecha.puntos(g)
    agarre = (base + punta) / 2
    destino = agarre + flecha.direccion * (valor - float(g.valor("distancia")))
    xy, visibles = g.pantalla([agarre, destino])
    assert visibles.all()
    a, b = (QPointF(*q) for q in xy)
    vis = v.visor
    QApplication.sendEvent(vis, QMouseEvent(QEvent.MouseMove, a, a, Qt.NoButton, Qt.NoButton, Qt.NoModifier))
    QApplication.sendEvent(vis, QMouseEvent(QEvent.MouseButtonPress, a, a, Qt.LeftButton, Qt.LeftButton, Qt.NoModifier))
    for i in range(1, 11):
        q = a + (b - a) * (i / 10)
        QApplication.sendEvent(vis, QMouseEvent(QEvent.MouseMove, q, q, Qt.NoButton, Qt.LeftButton, Qt.NoModifier))
        A.esperar(40)
    if captura:
        A.esperar(300)
        A.foto(v, captura)
    QApplication.sendEvent(vis, QMouseEvent(QEvent.MouseButtonRelease, b, b, Qt.LeftButton, Qt.NoButton, Qt.NoModifier))
    A.esperar(400)


def extruir_corta():
    """Cilindro con un disco arriba y una línea que lo cruza: Extrusión delgada de 1 mm y arrastre hacia adentro."""
    barra = _api("create_cylinder", height=30, radius=10, x=400)["bodies_created"][0]["id"]
    _api("create_cylinder", height=5, radius=25, x=400, z=30, operation="join", target=barra)
    _api("create_construction_plane", plane="XY", offset=35, name="PD")
    _api("create_sketch", name="Cruce", plane="PD")
    _api("draw_line", sketch="Cruce", start_x=370, start_y=0, end_x=430, end_y=0)
    A.esperar(300)
    v.visor.encuadrar(np.array([[370.0, -30, -5], [430, 30, 50]]))
    A.esperar(200)
    otros = {k for k in v.doc.estado_final.cuerpos if k != barra}
    volumen_barra = medir(barra)
    p = A.abrir(v, "extruir")
    p.widgets["tipo"].boton("delgada").click()
    A.esperar(150)
    A.elegir(p, "perfiles", A.hit_curva(v, s, "Cruce"))
    A.esperar()
    A.reg(AR, "hacia afuera sigue Cuerpo nuevo", p.valores["operacion"] == "nuevo", p.valores["operacion"])
    teclear(p.widgets["espesor"], "1 mm")
    combo = p.widgets["ubicacion"]
    combo.setCurrentIndex(combo.findData("centro"))
    A.esperar()
    A.reg(AR, "la pared de 1 mm tampoco cambia la operación", p.valores["operacion"] == "nuevo", p.mensaje.text())
    _arrastrar_flecha(p, -45, "extruir_b117_arrastre")
    A.reg(AR, "la flecha hacia adentro pasa a Cortar", p.valores["operacion"] == "cortar", p.valores["distancia"])
    A.reg(AR, "con Cortar se ve la previa roja", "previa_comando" in v.visor._capas)
    A.reg(AR, "el combo muestra Cortar", p.widgets["operacion"].currentData() == "cortar")
    foto(p, "extruir_cortar")
    p.aceptar()
    A.esperar(800)
    op = v.doc.operaciones[-1]
    partes = {k: c for k, c in v.doc.estado_final.cuerpos.items() if k not in otros}
    A.reg(AR, "Aceptar deja el corte en el timeline", (op.TIPO, op.p["operacion"]) == ("extrusion", "cortar"), op.p["operacion"])
    A.reg(AR, "quedan 2 cuerpos, un sólido cada uno", len(partes) == 2 and all(len(A.geo.solidos(c.forma)) == 1 for c in partes.values()),
          {k: round(A.geo.volumen(c.forma), 1) for k, c in partes.items()})
    A.reg(AR, "las partes suman lo que quedó", sum(A.geo.volumen(c.forma) for c in partes.values()) < volumen_barra)
    textos = _navegador()
    A.reg(AR, "el navegador muestra los 2 cuerpos", all(any(c.nombre in t for t in textos) for c in partes.values()),
          [c.nombre for c in partes.values()])
    A.foto(v, "extruir_b116_dos_cuerpos")
    v.editar_operacion(op.id)
    A.esperar()
    reabierto = v.panel
    A.reg(AR, "reabrir el paso muestra Cortar", reabierto.valores["operacion"] == "cortar")
    teclear(reabierto.widgets["distancia"], "-5 mm")
    A.esperar()
    A.reg(AR, "reabierto no cambia de operación aunque ya no parta", reabierto.valores["operacion"] == "cortar")
    QTest.keyClick(reabierto, Qt.Key_Escape)
    A.esperar(300)
    A.reg(AR, "Esc deja los 2 cuerpos", len(v.doc.estado_final.cuerpos) == len(otros) + 2)
    A.deshacer(v)
    A.reg(AR, "deshacer vuelve a 1 cuerpo", len(v.doc.estado_final.cuerpos) == len(otros) + 1)
    v.acciones["rehacer"].trigger()
    A.esperar(300)
    A.reg(AR, "rehacer vuelve a 2 cuerpos", len(v.doc.estado_final.cuerpos) == len(otros) + 2)
    p = A.abrir(v, "extruir")
    p.widgets["tipo"].boton("delgada").click()
    A.esperar(150)
    A.elegir(p, "perfiles", A.hit_curva(v, s, "Cruce"))
    A.esperar()
    combo = p.widgets["operacion"]
    combo.setCurrentIndex(combo.findData("unir"))
    A.esperar()
    _arrastrar_flecha(p, -20)
    A.reg(AR, "con Operación elegida a mano, la flecha no la cambia", p.valores["operacion"] == "unir", p.valores["operacion"])
    QTest.keyClick(p, Qt.Key_Escape)
    A.esperar(200)


A.correr("rosca", rosca)
A.correr("agujero", agujero)
A.correr("cilindro", lambda: dibujar("cilindro", "centro", lambda p: p.valores["diametro"] != "20 mm"))
A.correr("esfera", lambda: dibujar("esfera", "centro", lambda p: p.valores["diametro"] != "20 mm"))
A.correr("toroide", lambda: dibujar("toroide", "centro", lambda p: p.valores["diametro"] != "40 mm"))
A.correr("caja", lambda: dibujar("caja", "centro", lambda p: p.valores["ancho"] != "20 mm"))
A.correr("bobina", lambda: dibujar("bobina", "plano", lambda p: p.valores["diametro"] != "20 mm"))
A.correr("solevacion", solevacion)
A.correr("editar_cara", editar_cara)
A.correr("ventana_chica", ventana_chica)
A.correr("capturas", capturas)
A.correr("extruir_corta", extruir_corta)

A.guardar_registro("herramientas_solido")
fallas = [r for r in A.REGISTRO if not r["ok"]]
for r in fallas:
    print("✗", r)
print(f"\n=== {len(A.REGISTRO)} comprobaciones, {len(fallas)} con ✗ ===")
v.close()
sys.exit(0)

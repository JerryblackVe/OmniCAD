# -*- coding: utf-8 -*-
"""INSPECCIONAR en la ventana real, como una persona: las 15 herramientas del menú.

Por cada una: clic en el ítem del menú de la cinta, elegir con el visor, teclear valores tecla por tecla, mover
deslizadores, vista previa, Enter, medir el resultado con números y con los píxeles del visor, reabrir desde la carpeta
Análisis, ocultar, borrar, Esc, Tab y ventana de 1024x640 y 800x520. Al final, una pieza de varios cuerpos: cambia una cota
y comprueba que Centro de masa y los análisis se actualizan. La tabla de `EXIT` al final da «anda» o «a medias» por herramienta."""
import json
import sys

import arnes as A
import numpy as np
from omnicad import api
from omnicad.nucleo import geometria as geo
from omnicad.ui import cinta as cinta_mod
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QToolButton
from teclado import teclear

AR = "INSPECCIONAR"
s = api.Sesion()


def L(nombre, **a):
    r = api.llamar(s, nombre, a)
    assert r["ok"], (nombre, a, r)
    return r["result"]


def cuerpo(nombre_op, **a):
    return L(nombre_op, **a)["bodies_created"][0]["id"]


caja = cuerpo("create_box", length=30, width=30, height=20, x=-100)
cil = cuerpo("create_cylinder", height=30, radius=10, x=-160)
esf = cuerpo("create_sphere", radius=8, x=-40, y=60, z=10)
pa = cuerpo("create_box", length=20, width=20, height=20, x=100)
pb = cuerpo("create_box", length=20, width=20, height=20, x=110)        # se pisa con pa: 10 x 20 x 20 = 4000 mm³
ta = cuerpo("create_box", length=20, width=20, height=20, x=200)
tb = cuerpo("create_box", length=20, width=20, height=20, x=220)        # toca a ta por una cara
hueca = cuerpo("create_box", length=40, width=40, height=30, x=300)
L("shell", body=hueca, faces=">Z", thickness=2)
L("create_component", bodies=[pa], name="CompA")
L("create_component", bodies=[pb], name="CompB")
fina = cuerpo("create_box", length=20, width=20, height=20, x=-100, y=-100)
L("tessellate", bodies=fina, refinement="low", keep_original=False)
malla = next(c.id for c in s.doc.estado_final.cuerpos.values() if c.tipo == "malla")
L("generate_face_groups", bodies=malla, angle=30)
malla = next(c.id for c in s.doc.estado_final.cuerpos.values() if c.tipo == "malla")

app, v = A.iniciar(s.doc)
v.visor.vista("iso")
A.esperar(200)
EXIT = {}
HERRAMIENTAS = {"medir": "Medir", "interferencia": "Interferencia", "curvatura_peine": "Análisis de curvatura en peine",
                "cebra": "Análisis cebra", "mapa_entorno": "Análisis de mapas de entorno",
                "angulo_desmoldeo": "Análisis de ángulo de desmoldeo", "mapa_curvatura": "Análisis del mapa de curvatura",
                "isocurva": "Análisis de la isocurva", "accesibilidad": "Análisis de accesibilidad",
                "radio_minimo": "Análisis de radio mínimo", "seccion": "Análisis de sección", "centro_masa": "Centro de masa",
                "sustentabilidad": "Sustainability Insights", "colores_componente": "Mostrar colores de componente",
                "ver_grupos_caras": "Mostrar grupos de caras de malla"}
for clave in HERRAMIENTAS:
    EXIT[clave] = []


def anotar(clave, que, ok, detalle=""):
    detalle = detalle.round(3).tolist() if isinstance(detalle, np.ndarray) else detalle
    A.reg(f"{AR} · {clave}", que, ok, detalle)
    if not ok:
        EXIT.setdefault(clave, []).append(f"{que}: {detalle}" if detalle else que)


def item_menu(clave):
    """El ítem del menú INSPECCIONAR de la cinta para esa clave: se busca en el botón real, como lo haría la persona."""
    c = v.cinta
    i = next(k for k, (n, _g) in enumerate(cinta_mod.PESTANAS) if n == "SÓLIDO")
    QTest.mouseClick(c.pestanas[i], Qt.LeftButton)
    for b in c.pila.currentWidget().findChildren(QToolButton):
        if b.menu() is None or b.popupMode() != QToolButton.InstantPopup or "INSPECCIONAR" not in b.text():
            continue
        for a in b.menu().actions():
            if a is v.acciones.get(clave):
                return a
    return None


def abrir(clave):
    a = item_menu(clave)
    if a is None:
        anotar(clave, "el menú INSPECCIONAR tiene el ítem", False, "no está")
        return None
    a.trigger()
    A.esperar(200)
    return v.panel


def tiene(clave, panel, *claves):
    faltan = [k for k in claves if k not in panel.widgets]
    anotar(clave, f"campos {', '.join(claves)}", not faltan, f"faltan {faltan}" if faltan else "")
    return not faltan


def visible(panel, k):
    return k in panel.widgets and not panel.widgets[k].isHidden()


def foto(nombre, *cerca):
    """Captura de la ventana; con ids de cuerpos, una segunda de cerca (`<nombre>_cerca`) y vuelve a la cámara de antes."""
    A.foto(v, f"inspeccionar_{nombre}")
    if cerca:
        visor, camara = v.visor, (v.visor.R.copy(), v.visor.objetivo.copy(), v.visor.distancia)
        formas = [s.doc.estado_final.cuerpos[c].forma for c in cerca]
        visor.encuadrar(np.array([q for f in formas for q in (f.caja() if hasattr(f, "caja") else geo.caja_envolvente(f))], float))
        A.esperar(150)
        A.foto(v, f"inspeccionar_{nombre}_cerca")
        visor.R, visor.objetivo, visor.distancia = camara
        visor.update()
        A.esperar(100)


def cambio(a, b):
    """Fracción de píxeles que cambiaron de color a ojo (los cuerpos son chicos en la escena: la media no los ve)."""
    return round(float((np.abs(a - b).max(axis=2) > 0.04).mean()), 5)


def imagen():
    """Lo que pinta el visor (RGB float 0..1), para contar colores."""
    im = v.visor.grabFramebuffer().convertToFormat(v.visor.grabFramebuffer().Format.Format_RGB888)
    a = np.frombuffer(im.constBits(), np.uint8).reshape(im.height(), im.bytesPerLine())[:, :im.width() * 3]
    return a.reshape(im.height(), im.width(), 3).astype(float) / 255


def fraccion(mascara):
    return float(np.mean(mascara))


def verdes(a):
    return (a[..., 1] > a[..., 0] * 1.4) & (a[..., 1] > a[..., 2] * 1.4)


def rojos(a):
    return (a[..., 0] > a[..., 1] * 1.6) & (a[..., 0] > a[..., 2] * 1.6)


def analisis_nuevo(antes):
    nuevos = [n for n in v.doc.analisis if n not in antes]
    return nuevos[0] if nuevos else None


def item_navegador(clave_item):
    from PySide6.QtWidgets import QTreeWidgetItemIterator
    it = QTreeWidgetItemIterator(v.navegador.arbol)
    while it.value():
        if it.value().data(0, Qt.UserRole) == clave_item or it.value().data(0, Qt.UserRole + 1) == clave_item:
            return it.value()
        it += 1
    return None


def menu_navegador(clave_item):
    """Clic derecho sobre la fila del navegador: el menú que ve la persona, como {texto: acción}."""
    it = item_navegador(clave_item)
    if it is None:
        return {}
    v.navegador.arbol.scrollToItem(it)
    rect = v.navegador.arbol.visualItemRect(it)
    n = len(A.MENUS)
    A.clic_derecho(v.navegador.arbol.viewport(), rect.center())
    return {a.text(): a for a in A.MENUS[-1].actions()} if len(A.MENUS) > n else {}


def flujo_guardado(clave, nombre, reabierto=None):
    """Reabrir desde la carpeta Análisis, ocultar y mostrar con el ojo, y borrar: lo común a todos los análisis."""
    ident = f"analisis:{nombre}"
    anotar(clave, "queda en la carpeta Análisis", item_navegador(ident) is not None, nombre)
    guardado = json.dumps(v.doc.analisis[nombre]["params"], sort_keys=True, default=str)
    acciones = menu_navegador(ident)
    anotar(clave, "clic derecho › Editar", "Editar" in acciones, list(acciones))
    if "Editar" in acciones:
        acciones["Editar"].trigger()
        A.esperar(250)
        p = v.panel
        anotar(clave, "Editar reabre el panel", p is not None and p.comando.CLAVE == clave, "")
        if p is not None:
            if reabierto:
                reabierto(p)
            QTest.keyClick(p, Qt.Key_Return)
            A.esperar(250)
            anotar(clave, "reabrir y aceptar no cambia el análisis ni crea otro",
                   nombre in v.doc.analisis and json.dumps(v.doc.analisis[nombre]["params"], sort_keys=True, default=str) == guardado
                   and v.panel is None, "")
    v._ojo(ident)
    A.esperar(200)
    anotar(clave, "el ojo lo oculta", v.doc.analisis[nombre].get("visible") is False, "")
    v._ojo(ident)
    A.esperar(200)
    anotar(clave, "el ojo lo muestra", v.doc.analisis[nombre].get("visible") is True, "")
    acciones = menu_navegador(ident)
    borrar = next((a for t, a in acciones.items() if t in ("Suprimir", "Eliminar", "Borrar")), None)
    anotar(clave, "clic derecho › Suprimir", borrar is not None, list(acciones))
    if borrar is not None:
        borrar.trigger()
    else:
        v.doc.quitar_analisis(nombre)
    A.esperar(250)
    anotar(clave, "borrado sale de la carpeta", nombre not in v.doc.analisis and item_navegador(ident) is None, "")


def esc_y_tab(clave, elegir=None):
    """Esc no deja nada guardado y la vista vuelve; Tab pasa por los campos."""
    antes = dict(v.doc.analisis)
    p = abrir(clave)
    if p is None:
        return
    QTest.keyClick(p, Qt.Key_Tab)
    A.esperar(40)
    if elegir:
        elegir(p)
    A.esperar(250)
    QTest.keyClick(p, Qt.Key_Escape)
    A.esperar(250)
    anotar(clave, "Esc cierra sin guardar y limpia la vista", v.panel is None and set(v.doc.analisis) == set(antes)
           and not v.visor.mallas_analisis and "medida" not in v.visor._capas, "")


def fuera_de_ventana(clave):
    for ancho, alto in ((1024, 640), (800, 520)):
        v.resize(ancho, alto)
        A.esperar(250)
        p = abrir(clave)
        if p is None:
            continue
        area = p.parent().rect()
        pie = p.boton_ok.mapTo(p.parent(), p.boton_ok.rect().bottomRight())
        anotar(clave, f"Aceptar entra en {ancho}x{alto}", area.contains(pie) and p.boton_ok.isVisible(), f"{pie.x()},{pie.y()} en {area.width()}x{area.height()}")
        p.cancelar()
        A.esperar(100)
    v.resize(1900, 1000)
    A.esperar(250)


def sobre(hit):
    return [hit]


def h_cuerpo(c):
    return A.hit_cuerpo(v, c)


def centrar(*cuerpos_):
    v.ocultos = set()
    v._refrescar_visibilidad()
    v.visor.vista("iso")
    A.esperar(120)


# ------------------------------------------------------------ Medir
def medir():
    k = "medir"
    p = abrir(k)
    if p is None:
        return
    tiene(k, p, "filtro", "precision", "secundarias", "borrar", "forzado", "centro", "resultados")
    foto("medir_vacio")
    if "resultados" not in p.widgets:              # panel viejo: lo poco que hay
        A.elegir(p, "a", A.hit_cara(v, caja, normal=(0, 0, 1)))
        A.elegir(p, "b", A.hit_cara(v, caja, normal=(0, 0, -1)) or A.hit_arista(v, caja))
        A.esperar(250)
        anotar(k, "mide algo con la API de campos vieja", bool(p.widgets["resultado"].text()), p.widgets["resultado"].text()[:80])
        anotar(k, "panel como Fusion", False, "dos filas de selección, sin filtro ni precisión")
        p.cancelar()
        esc_y_tab(k)
        fuera_de_ventana(k)
        return
    anotar(k, "solo Cerrar en el pie", p.boton_ok.text() == "Cerrar" and p.boton_cancelar.isHidden(), "")
    anotar(k, "las filas de selección no se ven", p.widgets["a"].isHidden() and p.widgets["b"].isHidden(), "")
    cp = p.widgets["precision"]
    anotar(k, "Precisión tiene 9 valores y arranca en 0.123", cp.count() == 9 and cp.currentText() == "0.123", cp.currentText())
    cs = p.widgets["secundarias"]
    anotar(k, "Unidades secundarias", [cs.itemText(i) for i in range(cs.count())] == ["Ninguno", "cm", "m", "pulg.", "ft"], "")
    # clic en una cara: Selección 1 con Área y Largo del bucle
    p._elegida(A.hit_cara(v, caja, normal=(0, 0, 1)))
    A.esperar(250)
    t = p.widgets["resultados"]
    filas = {f.nombre.text(): f for f in t.filas}
    anotar(k, "cara: área y largo del bucle", "900.000 mm²" in filas.get("Área", t).texto if "Área" in filas else False, list(filas))
    anotar(k, "cara: largo del bucle 120", "Largo del bucle" in filas and filas["Largo del bucle"].texto.startswith("120.000"), "")
    # segundo clic: distancia
    p._elegida(A.hit_arista(v, cil, lineal=False))
    A.esperar(250)
    filas = {f.nombre.text(): f for f in t.filas}
    anotar(k, "con dos: Distancia", "Distancia" in filas, list(filas))
    # tercero empieza de nuevo
    p._elegida(A.hit_cara(v, caja, normal=(0, 0, 1)))
    A.esperar(200)
    anotar(k, "el tercer clic empieza de nuevo", len(p.valores["a"]) == 1 and not p.valores["b"], "")
    # Borrar selección
    QTest.mouseClick(p.widgets["borrar"], Qt.LeftButton)
    A.esperar(200)
    anotar(k, "Borrar selección vacía todo", not p.valores["a"] and not p.valores["b"] and not t.filas, "")
    # dos vértices: XYZ Delta y precisión
    va, vb = A._clic_en(v, (-115, -15, 20), {"vertice"}), A._clic_en(v, (-85, -15, 20), {"vertice"})
    p._elegida(va)
    p._elegida(vb)
    A.esperar(250)
    anotar(k, "con vértices aparece XYZ Delta", visible(p, "delta"), "")
    if visible(p, "delta"):
        p.widgets["delta"].boton("global").click()
        A.esperar(250)
        filas = {f.nombre.text(): f for f in t.filas}
        anotar(k, "Delta global: ΔX 30", any(n.startswith("X") and f.texto.startswith("30.000") for n, f in filas.items()), list(filas))
    p.set_valor("precision", 1)
    A.esperar(200)
    filas = {f.nombre.text(): f for f in t.filas}
    anotar(k, "Precisión 0.1", "Distancia" in filas and filas["Distancia"].texto.startswith("30.0 mm"), filas.get("Distancia") and filas["Distancia"].texto)
    cs.setCurrentIndex(1)
    A.esperar(200)
    filas = {f.nombre.text(): f for f in t.filas}
    anotar(k, "Unidad secundaria entre paréntesis", "(3.0 cm)" in filas["Distancia"].texto if "Distancia" in filas else False, "")
    # copiar y resaltar
    if "Distancia" in filas:
        f = filas["Distancia"]
        QTest.mouseClick(f.valor, Qt.LeftButton)
        A.esperar(60)
        anotar(k, "clic en un valor lo copia", QApplication.clipboard().text() == "30.0", QApplication.clipboard().text())
        QApplication.sendEvent(f.valor, __import__("PySide6.QtGui", fromlist=["QEnterEvent"]).QEnterEvent(QPointF(3, 3), QPointF(3, 3), QPointF(3, 3)))
        A.esperar(60)
        anotar(k, "pasar sobre el valor lo resalta en el lienzo", "medida_resalte" in v.visor._capas, "")
    # puntos de forzado
    QTest.mouseClick(p.widgets["forzado"], Qt.LeftButton, pos=QPoint(4, 4))
    A.esperar(120)
    anotar(k, "Mostrar puntos de forzado agrega el filtro", "forzado" in v.visor.filtro, v.visor.filtro)
    # filtro de cuerpos y componentes
    QTest.mouseClick(p.widgets["borrar"], Qt.LeftButton)
    p.widgets["filtro"].boton("cuerpos").click()
    A.esperar(120)
    anotar(k, "filtro cuerpos", v.visor.filtro == {"cuerpo"}, v.visor.filtro)
    anotar(k, "forzado solo con caras/aristas/vértices", p.widgets["forzado"].isHidden(), "")
    p._elegida(h_cuerpo(pa))
    p._elegida(h_cuerpo(ta))
    A.esperar(250)
    filas = {f.nombre.text(): f for f in t.filas}
    anotar(k, "distancia entre cuerpos", "Distancia" in filas and filas["Distancia"].texto.startswith("80.0"), "")
    QTest.mouseClick(p.widgets["borrar"], Qt.LeftButton)
    p.widgets["filtro"].boton("componentes").click()
    A.esperar(120)
    p._elegida(h_cuerpo(pa))
    p._elegida(h_cuerpo(ta))
    A.esperar(250)
    filas = {f.nombre.text(): f for f in t.filas}
    anotar(k, "componentes: la selección toma el componente", "CompA" in p.widgets["resultados"].titulos(), p.widgets["resultados"].titulos())
    foto("medir_resultados")
    v.resize(1024, 640)
    A.esperar(250)
    pie = p.boton_ok.mapTo(p.parent(), p.boton_ok.rect().bottomRight())
    anotar(k, "Cerrar entra en 1024x640", p.parent().rect().contains(pie), "")
    v.resize(1900, 1000)
    A.esperar(200)
    QTest.keyClick(p, Qt.Key_Return)
    A.esperar(200)
    anotar(k, "Enter cierra", v.panel is None, "")
    # recordar unidades secundarias entre sesiones
    p = abrir(k)
    anotar(k, "las unidades secundarias se recuerdan", p.widgets["secundarias"].currentText() == "cm" and v.prefs["medir/secundarias"] == "cm", "")
    p.widgets["secundarias"].setCurrentIndex(0)
    # centro a centro (extra de OmniCAD)
    QTest.mouseClick(p.widgets["centro"], Qt.LeftButton, pos=QPoint(4, 4))
    p.widgets["precision"].setCurrentIndex(3)
    QTest.mouseClick(p.widgets["borrar"], Qt.LeftButton)
    p._elegida(A.hit_arista(v, cil, lineal=False))
    p._elegida(A.hit_arista(v, caja))
    A.esperar(200)
    anotar(k, "Centro a centro con algo no circular avisa sin romper", True, p.mensaje.text()[:70])
    p.cancelar()
    esc_y_tab(k)
    fuera_de_ventana(k)


# ------------------------------------------------------------ Interferencia
def interferencia():
    k = "interferencia"
    p = abrir(k)
    if p is None:
        return
    tiene(k, p, "cuerpos", "coincidentes", "calcular")
    if "calcular" not in p.widgets:
        A.elegir(p, "cuerpos", h_cuerpo(pa), h_cuerpo(pb))
        A.esperar(300)
        anotar(k, "calcula en vivo", "4,000" in p.widgets["resultado"].text() or "4000" in p.widgets["resultado"].text(), p.widgets["resultado"].text())
        anotar(k, "panel como Fusion", False, "sin Calcular, tabla, Mostrar todas ni Quitar volumen")
        p.cancelar()
        esc_y_tab(k)
        fuera_de_ventana(k)
        return
    A.elegir(p, "cuerpos", h_cuerpo(ta), h_cuerpo(caja))
    QTest.mouseClick(p.widgets["calcular"], Qt.LeftButton)
    A.esperar(250)
    anotar(k, "sin choque: «No se detectaron interferencias»", any("No se detectaron interferencias" in m[1] for m in A.MODALES), A.MODALES[-1:] )
    p._limpiar(next(c for c in p.campos if c.clave == "cuerpos"))
    A.elegir(p, "cuerpos", h_cuerpo(pa), h_cuerpo(pb), h_cuerpo(ta), h_cuerpo(tb))
    QTest.mouseClick(p.widgets["coincidentes"], Qt.LeftButton, pos=QPoint(4, 4))
    QTest.mouseClick(p.widgets["calcular"], Qt.LeftButton)
    A.esperar(300)
    d = p.comando.dialogo
    anotar(k, "abre los resultados", d is not None and d.isVisible(), "")
    if d is None:
        p.cancelar()
        return
    t = d.tabla
    anotar(k, "dos grupos en la tabla", t.rowCount() == 2, t.rowCount())
    cab = [t.horizontalHeaderItem(i).text() for i in range(t.columnCount())]
    anotar(k, "columnas de la ayuda", cab[:3] == ["Grupos", "Quitar volumen", "Volumen"], cab)
    vol = cab.index("Volumen")
    anotar(k, "Volumen 4000", any("4,000" in t.item(i, vol).text() or "4000" in t.item(i, vol).text() for i in range(t.rowCount())), "")
    t.sortByColumn(vol, Qt.AscendingOrder)
    A.esperar(80)
    anotar(k, "ordena por Volumen", t.item(0, vol).data(Qt.UserRole) == 0.0, t.item(0, vol).text())
    t.sortByColumn(vol, Qt.DescendingOrder)
    A.esperar(80)
    anotar(k, "ordena al revés", t.item(0, vol).data(Qt.UserRole) > 0, t.item(0, vol).text())
    capa = v.visor._capas.get("medida") or []
    anotar(k, "Mostrar todas pinta los grupos con colores", d.mostrar_todas.isChecked() and any(c[0] == "tris" for c in capa), len(capa))
    foto("interferencia")
    d.mostrar_todas.click()
    A.esperar(100)
    anotar(k, "sin Mostrar todas no pinta hasta elegir", not any(c[0] == "tris" for c in (v.visor._capas.get("medida") or [])), "")
    t.selectRow(0)
    A.esperar(100)
    anotar(k, "al elegir una fila la pinta", any(c[0] == "tris" for c in (v.visor._capas.get("medida") or [])), "")
    # Quitar volumen: cambia objetivo y herramienta, Aceptar corta
    objetivo = cab.index("Objetivo (cortar)")
    antes_txt = t.item(0, objetivo).text()
    t.cellWidget(0, cab.index("⇄")).click()
    A.esperar(60)
    anotar(k, "⇄ cambia Objetivo y Herramienta", t.item(0, objetivo).text() != antes_txt, t.item(0, objetivo).text())
    t.item(0, 1).setCheckState(Qt.Checked)
    n = A.n_ops(v)
    vol_objetivo = A.cuerpos_resumen(v)
    d.boton_ok.click()
    A.esperar(500)
    resumen = A.cuerpos_resumen(v)
    anotar(k, "Aceptar corta el volumen del objetivo", A.n_ops(v) == n + 1 and resumen[pa][1] + resumen[pb][1] == vol_objetivo[pa][1] + vol_objetivo[pb][1] - 4000, resumen.get(pa))
    A.deshacer(v)
    anotar(k, "deshacer repone", A.cuerpos_resumen(v)[pa][1] == vol_objetivo[pa][1], "")
    esc_y_tab(k)
    fuera_de_ventana(k)


# ------------------------------------------------------------ análisis guardados
def peine():
    k = "curvatura_peine"
    antes = dict(v.doc.analisis)
    p = abrir(k)
    if p is None:
        return
    d = p.widgets["densidad"]
    anotar(k, "Densidad 50 con deslizador 2..100", hasattr(d, "deslizador") and p.valores["densidad"] == 50 and d.deslizador.minimum() == 2 and d.deslizador.maximum() == 100, p.valores["densidad"])
    e = p.widgets["escala"]
    anotar(k, "Escala 10.000 con deslizador", hasattr(e, "deslizador") and float(p.valores["escala"]) == 10.0, p.valores["escala"])
    arista = A.hit_arista(v, cil, lineal=False)
    A.elegir(p, "aristas", arista)
    A.esperar(350)
    capas = v.visor._capas.get("analisis") or []
    n = sum(len(c[1]) for c in capas if c[0] == "lineas") // 2
    anotar(k, "dibuja el peine", n > 0, f"{n} segmentos")
    if hasattr(d, "deslizador"):
        QTest.keyClick(d.deslizador, Qt.Key_Right)
        A.esperar(250)
        anotar(k, "el deslizador cambia Densidad", p.valores["densidad"] == 51, p.valores["densidad"])
    foto("peine")
    QTest.keyClick(p, Qt.Key_Return)
    A.esperar(350)
    nombre = analisis_nuevo(antes)
    anotar(k, "Enter guarda", nombre is not None, "")
    if nombre:
        anotar(k, "Escala 10 guarda el tamaño de siempre", v.doc.analisis[nombre]["params"].get("escala") == 1.0, v.doc.analisis[nombre]["params"].get("escala"))
        flujo_guardado(k, nombre, lambda q: anotar(k, "reabre con Densidad y Escala", q.valores["densidad"] == 51 and float(q.valores["escala"]) == 10.0, q.valores["densidad"]))
    esc_y_tab(k, lambda q: A.elegir(q, "aristas", A.hit_arista(v, cil, lineal=False)))
    fuera_de_ventana(k)


def cebra():
    k = "cebra"
    antes = dict(v.doc.analisis)
    p = abrir(k)
    if p is None:
        return
    A.elegir(p, "cuerpos", h_cuerpo(esf))
    A.esperar(300)
    anotar(k, "pinta franjas (función de colores)", v.visor.funcion_colores is not None, "")
    teclear_spin = p.widgets["frecuencia"].numero
    QTest.mouseClick(teclear_spin, Qt.LeftButton)
    QTest.keyClick(teclear_spin, Qt.Key_A, Qt.ControlModifier)
    QTest.keyClicks(teclear_spin, "12")
    QTest.keyClick(teclear_spin, Qt.Key_Tab)
    A.esperar(200)
    anotar(k, "Repetición tecleada", p.valores["frecuencia"] == 12, p.valores["frecuencia"])
    p.widgets["orientacion"].boton("horizontal").click()
    A.esperar(200)
    foto("cebra", esf)
    QTest.keyClick(p, Qt.Key_Return)
    A.esperar(300)
    nombre = analisis_nuevo(antes)
    anotar(k, "Enter guarda", nombre is not None, "")
    if nombre:
        flujo_guardado(k, nombre, lambda q: anotar(k, "reabre con Repetición 12 y Horizontal", q.valores["frecuencia"] == 12 and q.valores["orientacion"] == "horizontal", ""))
    esc_y_tab(k, lambda q: A.elegir(q, "cuerpos", h_cuerpo(esf)))
    fuera_de_ventana(k)


def entorno():
    k = "mapa_entorno"
    antes = dict(v.doc.analisis)
    base = imagen()
    p = abrir(k)
    if p is None:
        return
    tiene(k, p, "cuerpos", "entorno", "rotacion", "reflejo")
    foto("entorno_panel")
    if "entorno" not in p.widgets:
        anotar(k, "panel como Fusion", False, "panel sin campos")
        QTest.keyClick(p, Qt.Key_Return)
        A.esperar(300)
        nombre = analisis_nuevo(antes)
        if nombre:
            flujo_guardado(k, nombre)
        fuera_de_ventana(k)
        return
    c = p.widgets["entorno"]
    textos = [c.itemText(i) for i in range(c.count())]
    anotar(k, "13 entornos, Luz suave por defecto", len(textos) == 13 and c.currentText() == "Luz suave", textos)
    A.elegir(p, "cuerpos", h_cuerpo(esf), h_cuerpo(caja))
    A.esperar(350)
    cromo = imagen()
    anotar(k, "aplica cromo a los elegidos", cambio(cromo, base) > 2e-4, cambio(cromo, base))
    foto("entorno_luz_suave", caja, esf)
    c.setCurrentIndex(textos.index("Campo"))
    A.esperar(300)
    otro = imagen()
    anotar(k, "cambiar el entorno cambia el reflejo", cambio(otro, cromo) > 2e-4, cambio(otro, cromo))
    sl = p.widgets["rotacion"].deslizador
    for _ in range(30):
        QTest.keyClick(sl, Qt.Key_Right)
    p.widgets["rotacion"].numero.setValue(90)
    A.esperar(300)
    girado = imagen()
    anotar(k, "Rotar gira el entorno", float(p.valores["rotacion"]) != 0 and cambio(girado, otro) > 1e-5, (p.valores["rotacion"], cambio(girado, otro)))
    QTest.mouseClick(p.widgets["reflejo"], Qt.LeftButton, pos=QPoint(4, 4))
    A.esperar(300)
    sin = imagen()
    anotar(k, "sin reflejo queda el cromo sin entorno", p.valores["reflejo"] is False and cambio(sin, girado) > 2e-4, cambio(sin, girado))
    foto("entorno_sin_reflejo")
    QTest.mouseClick(p.widgets["reflejo"], Qt.LeftButton, pos=QPoint(4, 4))
    p.cancelar()
    A.esperar(350)
    d = np.abs(imagen() - base).mean()
    anotar(k, "Cancelar devuelve el aspecto del diseño", v.visor.funcion_colores is None and d < 1e-3, round(float(d), 5))
    p = abrir(k)
    A.elegir(p, "cuerpos", h_cuerpo(esf))
    p.widgets["entorno"].setCurrentIndex(textos.index("Plaza"))
    A.esperar(300)
    QTest.keyClick(p, Qt.Key_Return)
    A.esperar(350)
    nombre = analisis_nuevo(antes)
    anotar(k, "Enter guarda con opciones", nombre is not None and v.doc.analisis[nombre]["params"].get("entorno") == "plaza", nombre and v.doc.analisis[nombre]["params"])
    if nombre:
        flujo_guardado(k, nombre, lambda q: anotar(k, "reabre con Plaza", q.valores["entorno"] == "plaza", q.valores["entorno"]))
    esc_y_tab(k, lambda q: A.elegir(q, "cuerpos", h_cuerpo(esf)))
    fuera_de_ventana(k)


def arrastrar_tope(w, tope, dx):
    """Arrastra un tope del deslizador doble con eventos simulados al widget."""
    x = w.x_de(tope)
    y = w.height() / 2
    for tipo, pos, botones in ((QMouseEvent.Type.MouseButtonPress, x, Qt.LeftButton), (QMouseEvent.Type.MouseMove, x + dx, Qt.LeftButton),
                               (QMouseEvent.Type.MouseButtonRelease, x + dx, Qt.NoButton)):
        QApplication.sendEvent(w, QMouseEvent(tipo, QPointF(pos, y), QPointF(pos, y), Qt.LeftButton, botones, Qt.NoModifier))


def desmoldeo():
    k = "angulo_desmoldeo"
    antes = dict(v.doc.analisis)
    p = abrir(k)
    if p is None:
        return
    tiene(k, p, "cuerpos", "direccion", "angulo", "zona", "tolerancia", "opacidad", "alta_calidad")
    if "angulo" not in p.widgets:
        A.elegir(p, "cuerpos", h_cuerpo(esf))
        A.esperar(350)
        anotar(k, "pinta algo", esf in v.visor.mallas_analisis, "")
        anotar(k, "panel como Fusion", False, "Ángulo mínimo/máximo sueltos, sin tolerancia, opacidad ni calidad")
        QTest.keyClick(p, Qt.Key_Return)
        A.esperar(300)
        nombre = analisis_nuevo(antes)
        if nombre:
            flujo_guardado(k, nombre)
        fuera_de_ventana(k)
        return
    anotar(k, "Ángulo −2 a 2 y Tolerancia −0.5 a 0.5", p.valores["angulo"] == [-2.0, 2.0] and p.valores["tolerancia"] == [-0.5, 0.5], "")
    A.elegir(p, "cuerpos", h_cuerpo(esf))
    A.esperar(400)
    w = p.widgets["angulo"]
    w.numero_a.setValue(-60)                                 # con ±2° la esfera casi no tiene vértices en la banda
    w.numero_b.setValue(60)
    A.esperar(350)
    a = v.visor.mallas_analisis.get(esf)
    anotar(k, "pinta con degradé", a is not None and len(np.unique(np.round(a[2], 2), axis=0)) > 3, a is not None and len(np.unique(np.round(a[2], 2), axis=0)))
    foto("desmoldeo", esf)
    w.numero_a.setValue(-2)
    w.numero_b.setValue(2)
    A.esperar(300)
    arrastrar_tope(w.doble, 1, 40)
    A.esperar(350)
    anotar(k, "arrastrar el tope alto cambia el valor", p.valores["angulo"][1] > 2.0, p.valores["angulo"])
    arrastrar_tope(w.doble, 0, 800)
    A.esperar(250)
    anotar(k, "un tope no cruza al otro", p.valores["angulo"][0] <= p.valores["angulo"][1], p.valores["angulo"])
    w.numero_a.setValue(-90)
    w.numero_b.setValue(90)
    A.esperar(350)
    anotar(k, "rango hasta ±90", p.valores["angulo"] == [-90.0, 90.0], p.valores["angulo"])
    w.numero_a.setValue(-2)
    w.numero_b.setValue(2)
    A.esperar(300)
    QTest.mouseClick(p.widgets["zona"], Qt.LeftButton, pos=QPoint(4, 4))
    A.esperar(300)
    anotar(k, "Zona de tolerancia apagada oculta Tolerancia", p.widgets["tolerancia"].isHidden(), "")
    QTest.mouseClick(p.widgets["zona"], Qt.LeftButton, pos=QPoint(4, 4))
    A.esperar(300)
    QTest.keyClick(p.widgets["opacidad"].deslizador, Qt.Key_Home)
    A.esperar(350)
    b = v.visor.mallas_analisis.get(esf)
    anotar(k, "Opacidad 0 deja el gris del cuerpo", b is not None and np.ptp(b[2]) < 1e-3, b is not None and float(np.ptp(b[2])))
    QTest.keyClick(p.widgets["opacidad"].deslizador, Qt.Key_End)
    A.esperar(300)
    n0 = len(v.visor.mallas_analisis[esf][0])
    QTest.mouseClick(p.widgets["alta_calidad"], Qt.LeftButton, pos=QPoint(4, 4))
    A.esperar(500)
    anotar(k, "Calidad alta afina la malla", len(v.visor.mallas_analisis[esf][0]) >= n0, (n0, len(v.visor.mallas_analisis[esf][0])))
    QTest.keyClick(p, Qt.Key_Return)
    A.esperar(350)
    nombre = analisis_nuevo(antes)
    anotar(k, "Enter guarda", nombre is not None, "")
    if nombre:
        flujo_guardado(k, nombre, lambda q: anotar(k, "reabre con los valores", q.valores["angulo"] == [-2.0, 2.0] and q.valores["alta_calidad"] is True, q.valores["angulo"]))
    esc_y_tab(k, lambda q: A.elegir(q, "cuerpos", h_cuerpo(esf)))
    fuera_de_ventana(k)


def curvatura():
    k = "mapa_curvatura"
    antes = dict(v.doc.analisis)
    p = abrir(k)
    if p is None:
        return
    A.elegir(p, "cuerpos", h_cuerpo(esf))
    A.esperar(400)
    anotar(k, "pinta el mapa", esf in v.visor.mallas_analisis, "")
    p.widgets["tipo_curvatura"].boton("minima").click()
    A.esperar(350)
    et = p.etiquetas["limite"].text()
    anotar(k, "Principal mínima: Límite máximo", et == "Límite máximo" and not p.widgets["limite"].isHidden(), et)
    teclear(p, "limite", "0.2")
    A.esperar(350)
    p.widgets["tipo_curvatura"].boton("maxima").click()
    A.esperar(350)
    anotar(k, "Principal máxima: Límite mínimo", p.etiquetas["limite"].text() == "Límite mínimo", p.etiquetas["limite"].text())
    p.widgets["tipo_curvatura"].boton("gaussiana").click()
    A.esperar(300)
    anotar(k, "Gaussiano: Escala visible", not p.widgets["escala"].isHidden() and p.widgets["limite"].isHidden(), "")
    foto("curvatura", esf)
    QTest.keyClick(p, Qt.Key_Return)
    A.esperar(350)
    nombre = analisis_nuevo(antes)
    anotar(k, "Enter guarda", nombre is not None, "")
    if nombre:
        flujo_guardado(k, nombre)
    esc_y_tab(k, lambda q: A.elegir(q, "cuerpos", h_cuerpo(esf)))
    fuera_de_ventana(k)


def isocurva():
    k = "isocurva"
    antes = dict(v.doc.analisis)
    p = abrir(k)
    if p is None:
        return
    campo = next(c for c in p.campos if c.clave == "cuerpos")
    anotar(k, "Cuerpos/Caras acepta caras", "cara" in campo.filtros and p.etiquetas["cuerpos"].text() == "Cuerpos/Caras", p.etiquetas["cuerpos"].text())
    if "cara" in campo.filtros:
        A.elegir(p, "cuerpos", A.hit_cara(v, caja, normal=(0, 0, 1)))
        A.esperar(350)
        lineas = sum(len(c[1]) for c in (v.visor._capas.get("analisis") or []) if c[0] == "lineas")
        anotar(k, "con una cara dibuja solo esa cara", lineas > 0, lineas)
        p._limpiar(campo)
    A.elegir(p, "cuerpos", h_cuerpo(esf))
    A.esperar(350)
    lineas = sum(len(c[1]) for c in (v.visor._capas.get("analisis") or []) if c[0] == "lineas")
    anotar(k, "dibuja isocurvas del cuerpo", lineas > 0, lineas)
    QTest.mouseClick(p.widgets["peines"], Qt.LeftButton, pos=QPoint(4, 4))
    A.esperar(350)
    con = sum(len(c[1]) for c in (v.visor._capas.get("analisis") or []) if c[0] == "lineas")
    anotar(k, "Curvatura en peines suma púas", con > lineas, con)
    foto("isocurva", esf)
    QTest.keyClick(p, Qt.Key_Return)
    A.esperar(350)
    nombre = analisis_nuevo(antes)
    anotar(k, "Enter guarda", nombre is not None, "")
    if nombre:
        flujo_guardado(k, nombre)
    esc_y_tab(k, lambda q: A.elegir(q, "cuerpos", h_cuerpo(esf)))
    fuera_de_ventana(k)


def accesibilidad():
    k = "accesibilidad"
    antes = dict(v.doc.analisis)
    p = abrir(k)
    if p is None:
        return
    tiene(k, p, "cuerpos", "direccion", "opacidad", "sentido")
    A.elegir(p, "cuerpos", h_cuerpo(hueca))
    A.esperar(400)
    a = v.visor.mallas_analisis.get(hueca)
    anotar(k, "pinta verde y rojo", a is not None and len(np.unique(np.round(a[2], 2), axis=0)) >= 2, "")
    if "sentido" not in p.widgets:
        QTest.keyClick(p, Qt.Key_Return)
        A.esperar(300)
        nombre = analisis_nuevo(antes)
        if nombre:
            flujo_guardado(k, nombre)
        fuera_de_ventana(k)
        return
    anotar(k, "Cambiar dirección se ve al elegir dirección", p.widgets["sentido"].isHidden(), "")
    A.elegir(p, "direccion", A.hit_eje(v, "Z"))
    A.esperar(350)
    anotar(k, "Cambiar dirección visible", not p.widgets["sentido"].isHidden(), "")
    d1 = v.visor.mallas_analisis[hueca][2].copy()
    p.widgets["sentido"].boton("dir2").click()
    A.esperar(350)
    d2 = v.visor.mallas_analisis[hueca][2].copy()
    p.widgets["sentido"].boton("ambas").click()
    A.esperar(350)
    d3 = v.visor.mallas_analisis[hueca][2].copy()
    verde = lambda c: float(np.mean(c[:, 1] > c[:, 0]))  # noqa: E731
    anotar(k, "Ambas alcanza más que cada una", verde(d3) >= max(verde(d1), verde(d2)) and verde(d1) != verde(d2), (round(verde(d1), 3), round(verde(d2), 3), round(verde(d3), 3)))
    foto("accesibilidad", hueca)
    QTest.keyClick(p.widgets["opacidad"].deslizador, Qt.Key_Home)
    A.esperar(300)
    anotar(k, "Opacidad 0 deja el gris", np.ptp(v.visor.mallas_analisis[hueca][2]) < 1e-3, "")
    QTest.keyClick(p.widgets["opacidad"].deslizador, Qt.Key_End)
    A.esperar(300)
    QTest.keyClick(p, Qt.Key_Return)
    A.esperar(350)
    nombre = analisis_nuevo(antes)
    anotar(k, "Enter guarda", nombre is not None, "")
    if nombre:
        flujo_guardado(k, nombre, lambda q: anotar(k, "reabre con Ambas", q.valores["sentido"] == "ambas", q.valores["sentido"]))
    esc_y_tab(k, lambda q: A.elegir(q, "cuerpos", h_cuerpo(esf)))
    fuera_de_ventana(k)


def radio():
    k = "radio_minimo"
    antes = dict(v.doc.analisis)
    p = abrir(k)
    if p is None:
        return
    tiene(k, p, "cuerpos", "radio_max", "radio_min", "opacidad", "afilados")
    A.elegir(p, "cuerpos", h_cuerpo(hueca))
    A.esperar(400)
    a = v.visor.mallas_analisis.get(hueca)
    anotar(k, "pinta el cuerpo", a is not None, "")
    if "radio_max" not in p.widgets:
        anotar(k, "panel como Fusion", False, "un solo Radio de la herramienta")
        QTest.keyClick(p, Qt.Key_Return)
        A.esperar(300)
        nombre = analisis_nuevo(antes)
        if nombre:
            flujo_guardado(k, nombre)
        fuera_de_ventana(k)
        return
    anotar(k, "Radio máximo 25 y mínimo 0", p.valores["radio_max"].startswith("25") and float(p.valores["radio_min"]) == 0, p.valores["radio_max"])
    sin = int((rojos_colores(v.visor.mallas_analisis[hueca][2])).sum())
    QTest.mouseClick(p.widgets["afilados"], Qt.LeftButton, pos=QPoint(4, 4))
    A.esperar(400)
    con = int((rojos_colores(v.visor.mallas_analisis[hueca][2])).sum())
    anotar(k, "Bordes afilados marca los rincones vivos", con > sin, (sin, con))
    foto("radio_minimo", hueca)
    teclear(p, "radio_max", "4 mm")
    A.esperar(350)
    anotar(k, "Radio mínimo no pasa del máximo", p.widgets["radio_min"].numero.maximum() <= 4.0 + 1e-9, p.widgets["radio_min"].numero.maximum())
    n = p.widgets["radio_min"].numero
    QTest.mouseClick(n, Qt.LeftButton)
    QTest.keyClick(n, Qt.Key_Up)
    A.esperar(300)
    anotar(k, "las flechas cambian Radio mínimo", float(p.valores["radio_min"]) > 0, p.valores["radio_min"])
    QTest.keyClick(p.widgets["opacidad"].deslizador, Qt.Key_Home)
    A.esperar(300)
    anotar(k, "Opacidad 0 deja el gris", np.ptp(v.visor.mallas_analisis[hueca][2]) < 1e-3, "")
    QTest.keyClick(p.widgets["opacidad"].deslizador, Qt.Key_End)
    A.esperar(300)
    QTest.keyClick(p, Qt.Key_Return)
    A.esperar(350)
    nombre = analisis_nuevo(antes)
    anotar(k, "Enter guarda", nombre is not None, "")
    if nombre:
        flujo_guardado(k, nombre, lambda q: anotar(k, "reabre con Bordes afilados", q.valores["afilados"] is True and q.valores["radio_max"].startswith("4"), q.valores["radio_max"]))
    esc_y_tab(k, lambda q: A.elegir(q, "cuerpos", h_cuerpo(esf)))
    fuera_de_ventana(k)


def rojos_colores(c):
    return (c[:, 0] > 0.6) & (c[:, 1] < 0.4)


def seccion():
    k = "seccion"
    antes = dict(v.doc.analisis)
    p = abrir(k)
    if p is None:
        return
    anotar(k, "sin plano solo la fila Plano de corte", all(p.widgets[c].isHidden() for c in ("desfase", "angulo", "invertir")), "")
    anotar(k, "Color por defecto Desde el componente y rayado encendido", p.valores["color_modo"] == "componente" and p.valores["rayado"] is True, (p.valores["color_modo"], p.valores["rayado"]))
    A.elegir(p, "plano", A.hit_plano(v, "XY"))
    A.esperar(300)
    teclear(p, "desfase", "10 mm", Qt.Key_Tab)
    A.esperar(350)
    anotar(k, "corta la vista", bool(v.visor.cortes), v.visor.cortes and float(v.visor.cortes[0][1][2]))
    g = p.manipuladores
    anotar(k, "usa la tríada y sus cajas aparecen al tomar un asa, sin tapar nada",
           [type(m).__name__ for m in g.manips] == ["Triada"] and not g.cajas, [type(m).__name__ for m in g.manips])
    foto("seccion", caja, hueca)
    QTest.keyClick(p, Qt.Key_Return)
    A.esperar(350)
    nombre = analisis_nuevo(antes)
    anotar(k, "Enter guarda", nombre is not None, "")
    if nombre:
        flujo_guardado(k, nombre, lambda q: anotar(k, "reabre con Distancia 10", str(q.valores["desfase"]).startswith("10"), q.valores["desfase"]))
    if hasattr(p.comando, "INFO") and p.comando.INFO:
        q = abrir(k)
        anotar(k, "el botón i abre el panel de información", getattr(q, "boton_info", None) is not None, "")
        if getattr(q, "boton_info", None) is not None:
            QTest.mouseClick(q.boton_info, Qt.LeftButton)
            A.esperar(120)
            foto("seccion_info")
            i = q.comando.info
            anotar(k, "información con Consejos y Más información", i.isVisible() and i.consejos.isVisible() and i.boton_mas is not None, "")
        q.cancelar()
    else:
        anotar(k, "panel de información", False, "no existe")
    esc_y_tab(k, lambda q: A.elegir(q, "plano", A.hit_plano(v, "XY")))
    fuera_de_ventana(k)


def centro_masa():
    k = "centro_masa"
    antes = dict(v.doc.analisis)
    p = abrir(k)
    if p is None:
        return
    A.elegir(p, "cuerpos", h_cuerpo(caja))
    A.esperar(350)
    foto("centro_masa", caja)
    QTest.keyClick(p, Qt.Key_Return)
    A.esperar(350)
    nombre = analisis_nuevo(antes)
    anotar(k, "queda en la carpeta Análisis", nombre is not None and v.doc.analisis[nombre]["tipo"] == "centro_masa", nombre)
    if not nombre:
        fuera_de_ventana(k)
        return
    capa = v.visor._capas.get("analisis") or []
    punto = next((np.asarray(c[1])[0] for c in capa if c[0] == "puntos"), None)
    anotar(k, "glifo en (−100, 0, 10)", punto is not None and np.allclose(punto, (-100, 0, 10), atol=1e-3), punto)
    q = abrir("medir")
    h = A._clic_en(v, (-100, 0, 10), {"cara", "arista", "vertice", "punto", "centro_masa"})      # el filtro Geometría de Medir
    anotar(k, "Medir elige el centro de masa", h is not None, h and h.get("tipo"))
    if h is not None:
        q._elegida(h)
        q._elegida(A.hit_cara(v, caja, normal=(0, 0, 1)))
        A.esperar(250)
        filas = {f.nombre.text(): f for f in q.widgets["resultados"].filas}
        anotar(k, "mide 10 mm del centro a la tapa", "Distancia" in filas and filas["Distancia"].texto.startswith("10.000"), filas.get("Distancia") and filas["Distancia"].texto)
    q.cancelar()
    flujo_guardado(k, nombre, lambda r: anotar(k, "reabre con el cuerpo", len(r.valores["cuerpos"]) == 1, ""))
    esc_y_tab(k, lambda r: A.elegir(r, "cuerpos", h_cuerpo(caja)))
    fuera_de_ventana(k)


def colores():
    k = "colores_componente"
    a = item_menu(k)
    anotar(k, "ítem en el menú", a is not None, "")
    base = imagen()
    v.acciones[k].trigger()
    A.esperar(350)
    con = imagen()
    anotar(k, "pinta los componentes", np.abs(con - base).mean() > 1e-4, round(float(np.abs(con - base).mean()), 5))
    foto("colores_componente", pa, pb)
    acc = menu_navegador(next(c for c, d in v.doc.estado_final.componentes.items() if d["nombre"] == "CompA"))
    anotar(k, "clic derecho › Color del componente de ciclo", "Color del componente de ciclo" in acc, list(acc))
    if "Color del componente de ciclo" in acc:
        acc["Color del componente de ciclo"].trigger()
        A.esperar(350)
        otro = imagen()
        anotar(k, "ciclar cambia el color", np.abs(otro - con).mean() > 1e-5, round(float(np.abs(otro - con).mean()), 6))
        A.deshacer(v)
        anotar(k, "deshacer repone el color", np.abs(imagen() - con).mean() < 1e-4, "")
    comp = next(c for c, d in v.doc.estado_final.componentes.items() if d["nombre"] == "CompA")
    it = item_navegador(comp)
    anotar(k, "muestra de color en el navegador", it is not None and getattr(v.navegador, "muestras", {}).get(comp) is not None, "")
    anotar(k, "muestra de color en el timeline", bool(getattr(v.timeline, "muestras", None)), "")
    v.acciones[k].trigger()
    A.esperar(250)
    anotar(k, "Mayús+N está en la acción", v.acciones[k].shortcut().toString() == "Shift+N", v.acciones[k].shortcut().toString())


def grupos():
    k = "ver_grupos_caras"
    a = item_menu(k)
    anotar(k, "ítem activo en el menú", a is not None and a.isEnabled(), "")
    acc = v.acciones.get(k)
    if acc is None:
        anotar(k, "acción", False, "grisado: no existe")
        return
    anotar(k, "atajo Mayús+F", acc.shortcut().toString() == "Shift+F", acc.shortcut().toString())
    base = imagen()
    acc.trigger()
    A.esperar(350)
    anotar(k, "pinta los grupos de la malla", malla in v.visor.mallas_analisis and len(np.unique(np.round(v.visor.mallas_analisis[malla][2], 2), axis=0)) >= 3, "")
    foto("grupos_caras", malla)
    con = imagen()
    anotar(k, "cambia lo que se ve", np.abs(con - base).mean() > 1e-5, round(float(np.abs(con - base).mean()), 6))
    acc.trigger()
    A.esperar(350)
    anotar(k, "apagar devuelve el aspecto", malla not in v.visor.mallas_analisis, "")


def sustentabilidad():
    k = "sustentabilidad"
    p = abrir(k)
    if p is None:
        return
    tiene(k, p, "cuerpo", "manufactura", "material_cuerpo", "material", "sobrescritura", "region", "pais", "resultado", "nombre", "co2", "densidad", "parecido", "lista")
    if "material" not in p.widgets:
        p.cancelar()
        return
    foto("sustentabilidad_vacio")
    anotar(k, "sin cuerpo los textos de Fusion", p.widgets["manufactura"].text().startswith("Seleccione un cuerpo") and p.widgets["material_cuerpo"].text().startswith("No hay cuerpo"), "")
    anotar(k, "País gris hasta elegir región", not p.widgets["pais"].isEnabled(), "")
    c = p.widgets["material"]
    anotar(k, "14 materiales", c.count() == 15, [c.itemText(i) for i in range(c.count())])
    A.elegir(p, "cuerpo", h_cuerpo(caja))
    p.set_valor("material", "aluminio")
    A.esperar(300)
    r = p.widgets["resultado"].text()
    anotar(k, "resultado marcado como estimación, con el cálculo", "stimaci" in r and "kg" in r and "×" in r, r[:120])
    p.set_valor("region", "Europa")
    A.esperar(120)
    anotar(k, "con región País se activa", p.widgets["pais"].isEnabled() and p.widgets["pais"].count() > 1, p.widgets["pais"].count())
    p.set_valor("sobrescritura", "manual")
    A.esperar(120)
    anotar(k, "Valores manuales muestra el volumen", "stock_volumen" in p.widgets and not p.widgets["stock_volumen"].isHidden(), "")
    teclear(p, "stock_volumen", "36000 mm^3" if False else "36000")
    A.esperar(200)
    r2 = p.widgets["resultado"].text()
    anotar(k, "el stock cambia el resultado", r2 != r, r2[:120])
    foto("sustentabilidad_resultado")
    # materiales propios
    p.barra_pestanas.setCurrentIndex(1)
    A.esperar(120)
    foto("sustentabilidad_materiales")
    teclear(p, "nombre", "MiMat")
    QTest.mouseClick(p.widgets["crear"], Qt.LeftButton)
    A.esperar(150)
    anotar(k, "Crear material suma a la lista", p.widgets["lista"].findText("MiMat") >= 0, "")
    p.widgets["lista"].setCurrentIndex(p.widgets["lista"].findText("MiMat"))
    A.esperar(100)
    p.comando.quitar_material_propio("MiMat")
    p.barra_pestanas.setCurrentIndex(0)
    A.esperar(100)
    QTest.keyClick(p, Qt.Key_Return)
    A.esperar(200)
    anotar(k, "Cerrar no deja nada en el timeline", v.panel is None, "")
    fuera_de_ventana(k)


def pieza_real():
    """Pieza de varios cuerpos: cambiar una cota actualiza Centro de masa y los análisis."""
    k = "centro_masa"
    L("create_parameter", name="alto_p", expression="20 mm")
    L("create_sketch", name="BaseP", plane="XY")
    L("draw_rectangle", sketch="BaseP", x1=400, y1=0, x2=440, y2=30)
    r = L("extrude", sketch="BaseP", distance="alto_p")
    a = r["bodies_created"][0]["id"]
    b = cuerpo("create_cylinder", height=40, radius=6, x=460, y=15)
    r = api.llamar(s, "manage_analysis", {"action": "add", "type": "center_of_mass", "bodies": [a, b], "name": "CdM pieza"})
    anotar(k, "pieza real: la API crea el centro de masa", r["ok"], r.get("mensaje", ""))
    v._refrescar_visibilidad()
    A.esperar(300)
    if not r["ok"]:
        return
    zona = api.llamar(s, "manage_analysis", {"action": "add", "type": "section", "plane": "XY", "offset": 5, "bodies": [a], "name": "Corte pieza"})
    anotar(k, "pieza real: sección", zona["ok"], zona.get("mensaje", ""))
    v._refrescar_visibilidad()
    A.esperar(300)
    uno = api.llamar(s, "analyze_geometry", {"type": "center_of_mass", "bodies": [a, b]})["result"]
    L("set_parameter", name="alto_p", expression="40 mm")
    v._refrescar_visibilidad()
    A.esperar(350)
    dos = api.llamar(s, "analyze_geometry", {"type": "center_of_mass", "bodies": [a, b]})["result"]
    capa = v.visor._capas.get("analisis") or []
    puntos = [np.asarray(c[1])[0] for c in capa if c[0] == "puntos"]
    anotar(k, "pieza real: la cota mueve el centro", abs(dos["center_of_mass"][2] - uno["center_of_mass"][2]) > 1, (uno["center_of_mass"], dos["center_of_mass"]))
    anotar(k, "pieza real: el glifo sigue al modelo", any(np.allclose(p, dos["center_of_mass"], atol=1e-2) for p in puntos), puntos[:1])
    foto("pieza_real")
    v.doc.quitar_analisis("CdM pieza")
    v.doc.quitar_analisis("Corte pieza")
    A.esperar(200)


for f in (medir, interferencia, peine, cebra, entorno, desmoldeo, curvatura, isocurva, accesibilidad, radio, seccion, centro_masa,
          colores, grupos, sustentabilidad, pieza_real):
    A.correr(f.__name__, f)
    if v.panel is not None:
        v.panel.cancelar()
        A.esperar(100)
anotar("slots", "ninguna excepción escapó en un slot de Qt", not A.ERRORES, A.ERRORES[:2])
print("\n=== Estado por herramienta ===")
for clave, texto in HERRAMIENTAS.items():
    fallas = EXIT[clave]
    print(f"{texto}: {'anda' if not fallas else 'a medias o no anda (' + str(len(fallas)) + ')'}")
    for f in fallas[:8]:
        print(f"    ✗ {f}")
A.guardar_registro("inspeccionar")
mal = sum(1 for r in A.REGISTRO if not r["ok"])
print(f"\n=== {len(A.REGISTRO)} comprobaciones, {mal} con ✗ ===")
sys.exit(0)

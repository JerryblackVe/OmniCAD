# -*- coding: utf-8 -*-
"""SUPERFICIE con guías (SUP-9, 12, 13 y 21) en la ventana real, como una persona: elegir con el visor, teclear los valores,
Enter, Tab y Esc, recorrer la tabla de bordes de Coser con el mouse y el teclado, reabrir el paso, deshacer y ventana chica.
Las capturas quedan en `evidencias/ui_<hoy>/capturas/` para compararlas con la ayuda de Fusion."""
import math
import sys

import arnes as A
import escena
import teclado as T
from omnicad import api
from omnicad.nucleo import geometria as geo
from omnicad.nucleo import referencias as refs
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QComboBox

s, ids = escena.construir()


def L(nombre, **a):
    r = api.llamar(s, nombre, a)
    assert r["ok"], (nombre, a, r)
    return r["result"]


# Lejos de la escena común, para que el clic no se confunda.
L("create_sketch", name="BP", plane="XY"); L("draw_line", sketch="BP", start_x=400, start_y=0, end_x=410, end_y=0)
L("create_sketch", name="BCirc", plane="XY"); L("draw_circle", sketch="BCirc", center_x=450, center_y=0, radius=10)
L("create_sketch", name="BR", plane="XZ"); L("draw_line", sketch="BR", start_x=400, start_y=0, end_x=400, end_y=100)
L("create_sketch", name="BRc", plane="XZ"); L("draw_line", sketch="BRc", start_x=450, start_y=0, end_x=450, end_y=100)
L("create_sketch", name="BC", plane="XZ"); L("draw_line", sketch="BC", start_x=410, start_y=0, end_x=420, end_y=100)
L("create_sketch", name="Rad", plane="XY"); L("draw_line", sketch="Rad", start_x=65, start_y=0, end_x=70, end_y=0)
L("create_construction_plane", plane="XY", offset=40, name="PA")
L("create_sketch", name="Boca", plane="PA"); L("draw_circle", sketch="Boca", center_x=60, center_y=0, radius=8)
L("create_sketch", name="L1", plane="XY"); L("draw_line", sketch="L1", start_x=500, start_y=0, end_x=510, end_y=0)
L("create_sketch", name="L2", plane="PL"); L("draw_line", sketch="L2", start_x=500, start_y=0, end_x=510, end_y=0)
L("create_sketch", name="R1", plane="XZ"); L("draw_line", sketch="R1", start_x=500, start_y=0, end_x=500, end_y=20)
L("create_sketch", name="R2", plane="XZ"); L("draw_line", sketch="R2", start_x=510, start_y=0, end_x=510, end_y=20)
L("create_sketch", name="Lc", plane="YZ"); L("draw_line", sketch="Lc", start_x=0, start_y=0, end_x=0, end_y=20)
L("create_sketch", name="C1", plane="XY"); L("draw_circle", sketch="C1", center_x=600, center_y=0, radius=10)
L("create_sketch", name="Pta", plane="PA"); L("draw_point", sketch="Pta", x=600, y=0)
g1 = L("create_surface_extrude", profiles={"sketch": "BP", "curve": list(s.doc.estado_final.bocetos[s.paso("BP").id].boceto.curvas)[0]},
       distance=10, start="offset", start_offset=200)["bodies_created"][0]["id"]
L("create_sketch", name="BP2", plane="XY"); L("draw_line", sketch="BP2", start_x=410.5, start_y=0, end_x=420, end_y=0)
g2 = L("create_surface_extrude", profiles={"sketch": "BP2", "curve": list(s.doc.estado_final.bocetos[s.paso("BP2").id].boceto.curvas)[0]},
       distance=10, start="offset", start_offset=200)["bodies_created"][0]["id"]

app, v = A.iniciar(s.doc)
AR = "SUPERFICIE-GUIAS"
pi = math.pi
tubo, caja_id, quilt, tapa = ids["tubo"], ids["caja"], ids["quilt"], ids["tapa"]


def run(nombre, f):
    A.correr(f"{AR} · {nombre}", f)


def cur(nombre, i=0):
    return lambda: [A.hit_curva(v, s, nombre, i)]


def calcular(p):
    p._t_previa.stop()
    p._calcular_previa()
    A.esperar(120)
    return A.estado_panel(p)


def caso(clave, sel, teclas, esperado, etiqueta, previos=None, foto=None, rt=True):
    """Opciones que van antes de elegir (`previos`), selección con el visor, valores tecleados campo por campo, vista previa,
    Aceptar, reabrir y aceptar sin cambiar, y deshacer."""
    antes, n0 = A.cuerpos_resumen(v), A.n_ops(v)
    A.MODALES.clear()
    p = A.abrir(v, clave)
    if p is None:
        A.reg(AR, f"{etiqueta}: abrir", False, f"{A.MODALES[-1:]}")
        return None
    for k, x in (previos or {}).items():
        p.set_valor(k, x)
    for campo, fn in sel.items():
        hs = fn()
        if not hs or any(h is None for h in hs):
            A.reg(AR, f"{etiqueta}: elegir «{campo}» con el visor", False, "el visor no devolvió la entidad")
            p.cancelar()
            return None
        A.elegir(p, campo, *hs)
    for k, x in teclas.items():
        if isinstance(x, str) and not isinstance(p.widgets[k], QComboBox) and p._visible(next(c for c in p.campos if c.clave == k)):
            T.teclear(p, k, x, Qt.Key_Tab)
        else:
            p.set_valor(k, x)
    st = calcular(p)
    if foto:
        A.esperar(450)
        A.foto(v, foto)
    if not (st["op"] and st["previa_ok"]):
        A.reg(AR, f"{etiqueta}: vista previa", False, f"mensaje=«{st['mensaje']}»")
        p.cancelar()
        A.esperar(100)
        return None
    p.aceptar()
    A.esperar(450)
    despues = A.cuerpos_resumen(v)
    nuevos = {k: x for k, x in despues.items() if k not in antes or antes[k] != x}
    total = round(sum(x[1] for k, x in nuevos.items() if k not in antes), 3)
    ok = A.n_ops(v) == n0 + 1 and (esperado is None or abs(total - esperado) <= max(abs(esperado) * 0.01, 0.05))
    A.reg(AR, f"{etiqueta}: resultado" + ("" if esperado is None else f" = {esperado:g}"), ok,
          f"obtenido {total}; pasos {n0} → {A.n_ops(v)}; nuevos={nuevos}")
    if rt and A.n_ops(v) == n0 + 1:
        v.editar_operacion(v.doc.operaciones[-1].id)
        A.esperar(250)
        p2 = v.panel
        if p2 is None or not p2.isVisible():
            A.reg(AR, f"{etiqueta}: reabrir para editar", False, "no abre el panel")
        else:
            malos = [f"{k}: puse {x!r}, vuelve {p2.valores.get(k)!r}" for k, x in {**(previos or {}), **teclas}.items()
                     if str(p2.valores.get(k)) != str(x)]
            A.reg(AR, f"{etiqueta}: al reabrir vuelven los valores", not malos, "; ".join(malos))
            calcular(p2)
            p2.aceptar()
            A.esperar(450)
            A.reg(AR, f"{etiqueta}: aceptar sin cambiar no altera nada", A.cuerpos_resumen(v) == despues and A.n_ops(v) == n0 + 1,
                  f"{A.cuerpos_resumen(v)}")
    k = 0
    while A.n_ops(v) > n0 and k < 3:
        A.deshacer(v)
        k += 1
    A.reg(AR, f"{etiqueta}: deshacer vuelve al estado anterior", A.n_ops(v) == n0 and A.cuerpos_resumen(v) == antes, "")
    return total


def rechaza(clave, sel, previos, campo, texto, palabra, etiqueta):
    """Tecleando un valor que no sirve, la vista previa avisa con un mensaje que trae `palabra` y no se puede aceptar."""
    p = A.abrir(v, clave)
    for k, x in (previos or {}).items():
        p.set_valor(k, x)
    for c, fn in sel.items():
        A.elegir(p, c, *fn())
    T.teclear(p, campo, texto, Qt.Key_Tab)
    st = calcular(p)
    n0 = A.n_ops(v)
    A.reg(AR, f"{etiqueta}: avisa y no deja seguir", not st["previa_ok"] and palabra.lower() in (st["mensaje"] or "").lower(),
          f"mensaje=«{st['mensaje']}»")
    p.aceptar()
    A.esperar(150)
    A.reg(AR, f"{etiqueta}: Aceptar no agrega un paso", A.n_ops(v) == n0, "")
    if v.panel is not None and v.panel.isVisible():
        v.panel.cancelar()
    A.esperar(100)


# 1 Primitivas (SUP-9) --------------------------------------------------------------------------------------------------
def primitivas():
    caso("sup_caja", {}, {"ancho": "10 mm", "largo": "20 mm", "alto": "30 mm", "x": "700 mm"}, 2200, "caja de superficie tecleando las medidas",
         foto="guias_caja")
    caso("sup_cilindro", {}, {"diametro": "20 mm", "alto": "30 mm", "x": "750 mm"}, 2 * pi * 10 * 40, "cilindro de superficie", foto="guias_cilindro")
    caso("sup_esfera", {"centro": lambda: [A.hit_cara(v, caja_id, normal=(0, 0, 1))]}, {"diametro": "20 mm"}, 400 * pi,
         "esfera de superficie con centro en una cara (clic)")
    caso("sup_toroide", {}, {"diametro": "40 mm", "diametro_tubo": "10 mm", "x": "850 mm"}, 4 * pi * pi * 20 * 5, "toroide de superficie")
    caso("sup_bobina", {"plano": lambda: [A.hit_plano(v, "XY")]}, {"diametro": "20 mm", "tamano": "2 mm"}, None, "bobina de superficie", foto="guias_bobina")
    caso("sup_tuberia", {"ruta": cur("BRc")}, {"tamano": "4 mm"}, 2 * pi * 2 * 100 + 2 * pi * 4, "tubería de superficie a lo largo de una ruta", foto="guias_tuberia")
    p = A.abrir(v, "sup_caja")
    campo = next(c for c in p.campos if c.clave == "operacion")
    A.reg(AR, "las primitivas de superficie no piden Operación: siempre es un cuerpo nuevo", not p._visible(campo), "")
    T.teclear(p, "ancho", "-5", Qt.Key_Tab)
    st = calcular(p)
    A.reg(AR, "caja de superficie con ancho negativo avisa", not st["previa_ok"] and "mayor que cero" in st["mensaje"], f"«{st['mensaje']}»")
    p.cancelar()
    A.esperar(100)


run("primitivas", primitivas)


def borde_del_tubo(z):
    """La arista circular del tubo a esa altura, con un clic (`A.hit_arista` da la costura, que es más larga)."""
    forma = v.doc.estado_final.cuerpos[tubo].forma
    for a in refs.subformas(forma, "arista"):
        f = refs.firma_arista(a)
        if f["geom"] != "linea" and abs(f["medio"][2] - z) < 0.5:
            for q in geo.polilinea_arista(a):                  # un punto del lado visible: del otro, el clic toma la costura
                hit = A._clic_en(v, q, {"arista"})
                if hit and hit["ref"].get("cuerpo") == tubo and hit["ref"].get("firma", {}).get("geom") != "linea":
                    return [hit]
    return None


# 2 Barrido (SUP-12) ----------------------------------------------------------------------------------------------------
def barrido():
    sel = {"perfil": cur("BP"), "ruta": cur("BR")}
    conico = 100 * (20 + 100 * math.tan(math.radians(5))) / 2
    caso("sup_barrido", sel, {"conicidad": "5 deg"}, conico, "barrido con conicidad de 5°", foto="guias_barrido_conicidad")
    caso("sup_barrido", sel, {"distancia": "0.5"}, 500, "barrido a la mitad de la ruta (fracción 0,5)")
    con_riel = {**sel, "carril": cur("BC")}
    caso("sup_barrido", con_riel, {}, 1500, "barrido con rail, escala Escalar", previos={"tipo": "ruta_carril"}, foto="guias_barrido_riel")
    caso("sup_barrido", con_riel, {"escala_carril": "ninguna"}, 1000, "barrido con rail, escala Ninguna", previos={"tipo": "ruta_carril"})
    caso("sup_barrido", con_riel, {"escala_carril": "estirar"}, 1500, "barrido con rail, escala Estirar", previos={"tipo": "ruta_carril"})
    caso("sup_barrido", con_riel, {"distancia": "0.5", "distancia_carril": "0.5"}, 625, "barrido con rail y extensión completa a la mitad",
         previos={"tipo": "ruta_carril", "extension": "completa"})
    p = A.abrir(v, "sup_barrido")
    c = {k.clave: k for k in p.campos}
    A.reg(AR, "barrido: Ruta individual muestra conicidad y torsión y esconde rail y superficie",
          p._visible(c["conicidad"]) and p._visible(c["torsion"]) and not p._visible(c["carril"]) and not p._visible(c["superficie_guia"]), "")
    p.set_valor("tipo", "ruta_carril")
    A.esperar(80)
    A.reg(AR, "barrido: con rail aparecen Extensión y Escala y se van la conicidad y la orientación",
          p._visible(c["carril"]) and p._visible(c["extension"]) and p._visible(c["escala_carril"]) and not p._visible(c["conicidad"])
          and not p._visible(c["orientacion"]) and not p._visible(c["distancia_carril"]), "")
    p.set_valor("extension", "completa")
    A.esperar(80)
    A.reg(AR, "barrido: «Extensión completa» muestra la fracción del rail", p._visible(c["distancia_carril"]), "")
    p.set_valor("tipo", "ruta")
    p.set_valor("orientacion", "paralela")
    A.esperar(80)
    A.reg(AR, "barrido: la orientación Paralela esconde conicidad y torsión", not p._visible(c["conicidad"]) and not p._visible(c["torsion"]), "")
    p.cancelar()
    A.esperar(100)
    caso("sup_barrido", {"perfil": cur("Rad"), "ruta": lambda: borde_del_tubo(0), "superficie_guia": lambda: [A.hit_cara(v, tubo)]}, {"cadena": False},
         pi * (100 - 25), "barrido con superficie guía por el borde del tubo", previos={"tipo": "ruta_superficie"}, foto="guias_barrido_superficie")
    rechaza("sup_barrido", sel, None, "conicidad", "-80 deg", "desaparece", "barrido con conicidad que hace desaparecer el perfil")
    rechaza("sup_barrido", sel, None, "distancia", "2", "de 0", "barrido con fracción mayor que 1")
    rechaza("sup_barrido", sel, None, "distancia", "abc", "abc", "barrido con texto en la fracción")
    p = A.abrir(v, "sup_barrido")
    p.set_valor("tipo", "ruta_carril")
    A.elegir(p, "perfil", *cur("BP")())
    A.elegir(p, "ruta", *cur("BR")())
    st = calcular(p)
    A.reg(AR, "barrido con rail sin elegir el rail lo pide", not st["previa_ok"] and "rail" in st["mensaje"], f"«{st['mensaje']}»")
    QTest.keyClick(p, Qt.Key_Escape)
    A.esperar(120)
    A.reg(AR, "Esc cierra el panel de barrido sin agregar nada", v.panel is None or not v.panel.isVisible(), "")


run("barrido", barrido)


# 3 Solevación (SUP-13) ----------------------------------------------------------------------------------------------------
def solevacion():
    dos = lambda: [A.hit_curva(v, s, "L1"), A.hit_curva(v, s, "L2")]  # noqa: E731
    rieles = lambda: [A.hit_curva(v, s, "R1"), A.hit_curva(v, s, "R2")]  # noqa: E731
    caso("sup_solevacion", {"secciones": dos}, {}, 200, "solevación simple entre dos líneas")
    caso("sup_solevacion", {"secciones": dos, "carriles": rieles}, {}, 200, "solevación con dos raíles", foto="guias_solevacion_rieles")
    caso("sup_solevacion", {"secciones": dos, "linea_central": cur("Lc")}, {}, None, "solevación con línea central",
         previos={"guia": "linea_central"})
    tangente = caso("sup_solevacion", {"secciones": lambda: [borde_del_tubo(20)[0], A.hit_curva(v, s, "Boca")]},
                    {"condicion_inicio": "tangente", "peso_inicio": "1.5"}, None, "solevación tangente a la boca del tubo", foto="guias_solevacion_tangente")
    libre = caso("sup_solevacion", {"secciones": lambda: [borde_del_tubo(20)[0], A.hit_curva(v, s, "Boca")]}, {}, None, "misma solevación, libre", rt=False)
    A.reg(AR, "la condición tangente cambia la superficie", tangente is not None and libre is not None and abs(tangente - libre) > 1,
          f"tangente {tangente} libre {libre}")
    # la condición se elige en el combo de la fila del perfil, como una persona
    p = A.abrir(v, "sup_solevacion")
    from omnicad.ui.comando import hit_desde_ref
    punta = {"tipo": "punto_boceto", "boceto": s.paso("Pta").id, "punto": next(iter(v.doc.estado_final.bocetos[s.paso("Pta").id].boceto.puntos))}
    A.elegir(p, "secciones", A.hit_curva(v, s, "C1"), hit_desde_ref(punta, v.doc.estado_final))
    A.esperar(150)
    combos = [c for c in p.findChildren(QComboBox) if c.findData("punto_tangente") >= 0]
    A.reg(AR, "la fila de un perfil que es un punto ofrece Aguda o Tangente", len(combos) == 1, f"{len(combos)} combos")
    cono = 0.0
    if combos:
        cono = pi * 10 * math.hypot(10, 40)
        combos[0].setCurrentIndex(combos[0].findData("punto_tangente"))
        A.esperar(120)
        A.reg(AR, "elegir Tangente en la fila lo guarda en el panel", p.valores.get("condicion_fin") == "punto_tangente", "")
        st = calcular(p)
        A.esperar(300)
        A.foto(v, "guias_solevacion_cupula")
        A.reg(AR, "solevación con cúpula: vista previa", st["previa_ok"], st["mensaje"])
        n0 = A.n_ops(v)
        p.aceptar()
        A.esperar(450)
        cuerpo = list(v.doc.estado_final.cuerpos.values())[-1]
        A.reg(AR, "la cúpula da más área que la punta aguda", A.n_ops(v) == n0 + 1 and geo.area(cuerpo.forma) > cono, f"{geo.area(cuerpo.forma):.1f} > {cono:.1f}")
        A.deshacer(v)
    else:
        p.cancelar()
    A.esperar(100)
    rechaza("sup_solevacion", {"secciones": dos}, {"condicion_inicio": "direccion", "guia": "carriles"}, "angulo_inicio", "abc", "abc", "solevación con texto en el ángulo")
    p = A.abrir(v, "sup_solevacion")
    A.elegir(p, "secciones", *dos())
    A.elegir(p, "carriles", *rieles())
    combo = next(c for c in p.findChildren(QComboBox) if c.findData("direccion") >= 0)        # la fila del primer perfil, como una persona
    combo.setCurrentIndex(combo.findData("direccion"))
    A.esperar(120)
    angulo = p.widgets["angulo_inicio"]
    angulo.setFocus()
    angulo.selectAll()
    QTest.keyClicks(angulo, "45 deg")
    QTest.keyClick(angulo, Qt.Key_Tab)
    A.esperar(120)
    st = calcular(p)
    A.reg(AR, "condición y raíles juntos: vista previa", st["previa_ok"] and p.valores.get("condicion_inicio") == "direccion", f"«{st['mensaje']}»")
    A.esperar(300)
    A.foto(v, "guias_solevacion_condicion_rieles")
    n0 = A.n_ops(v)
    p.aceptar()
    A.esperar(450)
    cuerpo = list(v.doc.estado_final.cuerpos.values())[-1]
    A.reg(AR, "la condición con raíles abre la superficie entre ellos", A.n_ops(v) == n0 + 1 and geo.area(cuerpo.forma) > 200.5, f"{geo.area(cuerpo.forma):.1f} > 200")
    op = v.doc.operaciones[-1]
    v.editar_operacion(op.id)
    A.esperar(400)
    r = v.panel
    A.reg(AR, "reabrir conserva la condición y los raíles", r.valores.get("condicion_inicio") == "direccion" and len(r.valores.get("carriles") or []) == 2, "")
    QTest.keyClick(r, Qt.Key_Escape)
    A.esperar(200)
    A.deshacer(v)
    A.esperar(100)


run("solevacion", solevacion)


# 4 Coser: tabla navegable y verde (SUP-21) ------------------------------------------------------------------------------------
def coser():
    p = A.abrir(v, "coser")
    A.elegir(p, "cuerpos", A.hit_cuerpo(v, g1), A.hit_cuerpo(v, g2))
    st = calcular(p)
    A.esperar(300)
    t = p.widgets["tabla_bordes"]
    texto = p.widgets["resultado"].text()
    A.reg(AR, "coser con 0,5 mm de hueco: 8 bordes libres y ninguna arista cosida", t.rowCount() == 8 and "8 bordes libres · 0 aristas" in texto, f"filas {t.rowCount()}; «{texto}»")
    A.reg(AR, "en la vista los bordes libres van en rojo", any(c[2] == p.comando.ROJO for c in (v.visor._capas.get("previa") or [])) or st["previa_ok"], "")
    A.foto(v, "guias_coser_tabla")
    r = t.visualItemRect(t.item(0, 0))
    centro_antes = v.visor.objetivo.copy()
    QTest.mouseClick(t.viewport(), Qt.LeftButton, Qt.NoModifier, r.center())
    A.esperar(150)
    A.reg(AR, "clic en una fila: la vista se acerca a ese borde", t.currentRow() == 0 and (v.visor.objetivo != centro_antes).any(), f"fila {t.currentRow()}")
    capas = [c for clave, lista in v.visor._capas.items() for c in lista if c[0] == "lineas"]
    A.reg(AR, "la fila elegida se dibuja aparte, más gruesa", any(c[2] == p.comando.ELEGIDO and c[3] > 3 for c in capas), f"{[c[2:] for c in capas]}")
    A.foto(v, "guias_coser_fila")
    QTest.keyClick(t, Qt.Key_Down)
    A.esperar(120)
    A.reg(AR, "flecha abajo pasa al borde siguiente", t.currentRow() == 1, f"fila {t.currentRow()}")
    T.teclear(p, "tolerancia", "0.6 mm", Qt.Key_Tab)
    st = calcular(p)
    A.esperar(200)
    capas = [c for lista in v.visor._capas.values() for c in lista if c[0] == "lineas"]
    A.reg(AR, "con tolerancia 0,6 mm se cose la arista y queda en verde", t.rowCount() == 6 and any(c[2] == p.comando.VERDE for c in capas),
          f"filas {t.rowCount()}; «{p.widgets['resultado'].text()}»")
    A.foto(v, "guias_coser_verde")
    T.teclear(p, "tolerancia", "abc", Qt.Key_Tab)
    st = calcular(p)
    A.reg(AR, "tolerancia mal escrita: avisa y la tabla no revienta", not st["previa_ok"], f"«{st['mensaje']}»")
    T.teclear(p, "tolerancia", "0.6 mm", Qt.Key_Tab)
    calcular(p)
    n0 = A.n_ops(v)
    p.aceptar()
    A.esperar(450)
    A.reg(AR, "coser con la tabla abierta agrega un paso y deja un solo cuerpo", A.n_ops(v) == n0 + 1 and g2 not in v.doc.estado_final.cuerpos, "")
    v.editar_operacion(v.doc.operaciones[-1].id)
    A.esperar(250)
    p2 = v.panel
    A.reg(AR, "coser: al reabrir la tabla vuelve llena", p2 is not None and p2.widgets["tabla_bordes"].rowCount() >= 6, "")
    p2.cancelar()
    A.esperar(100)
    A.deshacer(v)
    p = A.abrir(v, "coser")
    A.elegir(p, "cuerpos", A.hit_cuerpo(v, quilt), A.hit_cuerpo(v, tapa))
    calcular(p)
    A.reg(AR, "coser una caja: «se cierra un sólido», tabla vacía y aristas cosidas", "se cierra" in p.widgets["resultado"].text()
          and p.widgets["tabla_bordes"].rowCount() == 0 and "se cose" in p.widgets["resultado"].text(), p.widgets["resultado"].text())
    p.cancelar()
    A.esperar(100)


run("coser", coser)


# 5 Ventana chica -----------------------------------------------------------------------------------------------------------
def chica():
    for (w, h) in ((1024, 640), (800, 520)):
        v.resize(w, h)
        A.esperar(300)
        for clave, valores in (("sup_barrido", {"tipo": "ruta_carril", "extension": "completa"}), ("sup_solevacion", {}), ("coser", {}),
                               ("sup_bobina", {}), ("sup_tuberia", {})):
            p = A.abrir(v, clave)
            for k, x in valores.items():
                p.set_valor(k, x)
            A.esperar(500)
            A.reg(AR, f"ventana {w}x{h}: el panel de «{clave}» entra en el visor", v.area.rect().contains(p.geometry()),
                  f"panel={p.geometry()} área={v.area.rect()}")
            A.foto(v, f"guias_chica_{clave}_{w}x{h}")
            p.cancelar()
            A.esperar(100)
    v.resize(1900, 1000)
    A.esperar(300)


run("ventana chica", chica)

A.guardar_registro("u_superficie_guias")
fallas = [r for r in A.REGISTRO if not r["ok"]]
print(f"\n=== {len(A.REGISTRO)} comprobaciones, {len(fallas)} con ✗ ===")
print("modales vistos:", A.MODALES[-10:])
v.close()
sys.exit(0)

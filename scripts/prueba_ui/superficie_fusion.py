# -*- coding: utf-8 -*-
"""SUPERFICIE igual a Fusion (SUP-10, 11, 14 a 19, 21, 22, 26; B-113): cada opción nueva en la ventana real, como una persona:
elegir con el visor, teclear los valores, Enter/Esc/Tab, arrastrar el asa de Extender, reabrir el paso, deshacer y
ventana chica. Las capturas quedan en `evidencias/ui_<hoy>/capturas/` para compararlas con la ayuda de Fusion."""
import math
import sys

import arnes as A
import corredor as C
import escena
import teclado as T
from omnicad.nucleo import referencias as refs
from omnicad.restricciones import Boceto
from omnicad.timeline.operaciones import OpBoceto
from omnicad.ui import manipuladores as mp
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QStyle, QStyleOptionButton

s, ids = escena.construir()
texto = Boceto()
texto.agregar_texto((100, -60), "AB", 5.0, 0.0, "OmniCAD Trazo SHX")
s.doc.agregar(OpBoceto(s.doc.nuevo_id(), "Texto", plano="XY", boceto=texto))
from omnicad import api  # noqa: E402


def L(nombre, **args):
    r = api.llamar(s, nombre, args)
    assert r["ok"], (nombre, args, r)
    return r["result"]


# SUP-15: una media luna (diámetro + semicírculo: dos esquinas de 90° entre recta y arco). SUP-17: una esfera descentrada
# 6 mm del plano YZ (cortada así su borde es una circunferencia que no es iso-paramétrica: la cara no es rectangular en UV).
L("create_sketch", name="Luna", plane="XY")
L("draw_line", sketch="Luna", start_x=280, start_y=60, end_x=320, end_y=60)
L("draw_arc", sketch="Luna", start_x=320, start_y=60, mid_x=300, mid_y=80, end_x=280, end_y=60)
esfera = L("create_surface_sphere", radius=10, x=6, y=150, z=10)["bodies_created"][0]["id"]
app, v = A.iniciar(s.doc)
AR = "SUPERFICIE-FUSION"
pi = math.pi
tubo, caja, quilt, tapa = ids["tubo"], ids["caja"], ids["quilt"], ids["tapa"]


def run(nombre, f):
    A.correr(f"{AR} · {nombre}", f)


def cur(nombre, i=0):
    return lambda: [A.hit_curva(v, s, nombre, i)]


eje_z = lambda: [A.hit_eje(v, "Z")]  # noqa: E731


def caso(clave, sel, vals, esperado, etiqueta, previos=None, foto=None, rt=True):
    """Como `corredor.caso`, pero con valores que van ANTES de elegir (un campo que solo se ve en un modo): previos,
    selección con el visor, valores, vista previa, Aceptar, reabrir y aceptar sin cambiar, y deshacer."""
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
    for k, x in vals.items():
        p.set_valor(k, x)
    p._t_previa.stop()
    p._calcular_previa()
    A.esperar(120)
    st = A.estado_panel(p)
    if foto:
        A.esperar(450)                      # que el panel termine de acomodarse antes de la foto
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
    total = round(sum(x[1] for k, x in nuevos.items() if k not in antes)
                  + sum(x[1] - antes[k][1] for k, x in nuevos.items() if k in antes), 3)
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
            malos = [f"{k}: puse {x!r}, vuelve {p2.valores.get(k)!r}" for k, x in {**(previos or {}), **vals}.items()
                     if str(p2.valores.get(k)) != str(x)]
            A.reg(AR, f"{etiqueta}: al reabrir vuelven los valores", not malos, "; ".join(malos))
            p2._t_previa.stop()
            p2._calcular_previa()
            p2.aceptar()
            A.esperar(450)
            A.reg(AR, f"{etiqueta}: aceptar sin cambiar no altera nada",
                  A.cuerpos_resumen(v) == despues and A.n_ops(v) == n0 + 1, f"{A.cuerpos_resumen(v)}")
    k = 0
    while A.n_ops(v) > n0 and k < 3:
        A.deshacer(v)
        k += 1
    A.reg(AR, f"{etiqueta}: deshacer vuelve al estado anterior", A.n_ops(v) == n0 and A.cuerpos_resumen(v) == antes, "")
    return total


# 1 Extruir (SUP-10) ---------------------------------------------------------------------------------------------------
def extruir():
    lin = cur("Lin")
    caso("sup_extruir", {"curvas": lin}, {"lados": "dos_lados", "distancia": "10 mm", "distancia2": "4 mm"}, 20 * 14,
         "extruir dos lados 10 + 4", foto="fusion_extruir_dos_lados")
    caso("sup_extruir", {"curvas": lin}, {"inicio": "desfase", "desfase_inicio": "5 mm", "distancia": "10 mm"}, 200,
         "extruir con plano de desfase 5 mm")
    caso("sup_extruir", {"curvas": lin, "inicio_objeto": lambda: [A.hit_plano(v, "PM")]},
         {"distancia": "10 mm"}, 200, "extruir desde el plano PM (objeto de inicio)", previos={"inicio": "objeto"})
    caso("sup_extruir", {"curvas": lin}, {"lados": "simetrica", "medida": "mitad", "distancia": "5 mm"}, 200,
         "extruir simétrica por media longitud")
    caso("sup_extruir", {"curvas": lin}, {"lados": "simetrica", "medida": "total", "distancia": "10 mm"}, 200,
         "extruir simétrica por longitud total")
    caso("sup_extruir", {"curvas": lin, "hasta": lambda: [A.hit_plano(v, "PL")]}, {}, 20 * 20,
         "extruir A OBJETO (plano a 20 mm)", previos={"extension": "objeto"}, foto="fusion_extruir_a_objeto")
    caso("sup_extruir", {"curvas": lin, "hasta": lambda: [A.hit_plano(v, "PL")]}, {"desfase_hasta": "5 mm"}, 20 * 25,
         "extruir A OBJETO con desfase del límite 5 mm", previos={"extension": "objeto"})
    t = caso("sup_extruir", {"curvas": lin}, {}, None, "extruir TODO", previos={"extension": "todo"})
    A.reg(AR, "extruir TODO llega más allá del cuerpo más alto", t is not None and t > 20 * 30, f"área {t}")
    caso("sup_extruir", {"curvas": cur("Texto")}, {"distancia": "3 mm"}, None, "extruir un texto de una línea")
    t = caso("sup_extruir", {"curvas": cur("Texto")}, {"distancia": "3 mm"}, None, "extruir texto (otra vez, para medir)", rt=False)
    una_curva = caso("sup_extruir", {"curvas": cur("Lin")}, {"distancia": "3 mm"}, 60, "una línea suelta sigue dando su cara", rt=False)
    A.reg(AR, "el texto da más superficie que un solo trazo", t is not None and una_curva is not None and t > 3 * 3, f"{t}")


run("sup_extruir", extruir)


# 2 Revolución (SUP-11) ------------------------------------------------------------------------------------------------
def revolucion():
    giro = 2 * pi * 30 * 20
    rev = {"curvas": cur("RevL"), "eje": eje_z}
    caso("sup_revolucion", rev, {"lados": "dos_lados", "angulo": "90 deg", "angulo2": "45 deg"}, giro * 135 / 360,
         "revolución dos lados 90° + 45°", foto="fusion_revolucion_dos_lados")
    caso("sup_revolucion", rev, {"lados": "simetrica", "angulo": "90 deg"}, giro / 4, "revolución simétrica 90°")
    caso("sup_revolucion", rev, {}, giro, "revolución completa", previos={"extension": "completa"})
    caso("sup_revolucion", {**rev, "hasta": lambda: [A.hit_plano(v, "YZ")]}, {}, giro / 4,
         "revolución A OBJETO (plano YZ)", previos={"extension": "objeto"}, foto="fusion_revolucion_a_objeto")
    caso("sup_revolucion", rev, {"angulo": "90 deg", "proyectar_eje": True}, giro / 4, "revolución con «Proyectar eje»")


run("sup_revolucion", revolucion)


# 3 Parche (SUP-14) ----------------------------------------------------------------------------------------------------
def indicador(casilla):
    """Punto del cuadradito de una casilla (el clic va ahí, no al centro del widget)."""
    o = QStyleOptionButton()
    casilla.initStyleOption(o)
    r = casilla.style().subElementRect(QStyle.SE_CheckBoxIndicator, o, casilla)
    return r.center()


def parche():
    arc = lambda: [A.hit_arista(v, tubo, lineal=False)]  # noqa: E731
    caso("parche", {"contorno": arc}, {"agrupar": False, "continuidades": "G1"}, pi * 25,
         "parche con continuidad G1 por arista", foto="fusion_parche_por_arista")
    caso("parche", {"contorno": arc}, {"invertir": True}, pi * 25, "parche con la normal invertida")
    # como una persona: desmarcar «Agrupar aristas» con el mouse, teclear la continuidad, Enter
    A.MODALES.clear()
    p = A.abrir(v, "parche")
    A.elegir(p, "contorno", *arc())
    caja_agrupar = p.widgets["agrupar"]
    QTest.mouseClick(caja_agrupar, Qt.LeftButton, Qt.NoModifier, indicador(caja_agrupar))
    A.esperar(100)
    A.reg(AR, "parche: el clic en «Agrupar aristas» la desmarca y muestra «Continuidad por arista»",
          p.valores.get("agrupar") is False and p._visible(next(c for c in p.campos if c.clave == "continuidades")),
          f"agrupar={p.valores.get('agrupar')}")
    T.teclear(p, "continuidades", "G7")
    p._t_previa.stop()
    p._calcular_previa()
    A.esperar(120)
    st = A.estado_panel(p)
    A.reg(AR, "parche: una continuidad escrita mal avisa «G0, G1 o G2»", not st["previa_ok"] and "G0, G1 o G2" in st["mensaje"],
          f"mensaje=«{st['mensaje']}»")
    T.teclear(p, "continuidades", "G1, G0, G0")
    p._t_previa.stop()
    p._calcular_previa()
    st = A.estado_panel(p)
    A.reg(AR, "parche: más continuidades que aristas elegidas avisa cuántas hay", not st["previa_ok"] and "solo 1 aristas" in st["mensaje"],
          f"mensaje=«{st['mensaje']}»")
    T.teclear(p, "continuidades", "G1", Qt.Key_Tab)
    p._t_previa.stop()
    p._calcular_previa()
    A.esperar(120)
    st = A.estado_panel(p)
    A.reg(AR, "parche: con «G1» la vista previa anda", st["op"] and st["previa_ok"], st["mensaje"])
    p.cancelar()
    A.esperar(100)
    # G1 sin aristas de un cuerpo: curvas de boceto → el mensaje dice qué corregir (SUP-22)
    p = A.abrir(v, "parche")
    A.elegir(p, "contorno", *[A.hit_curva(v, s, "Circ")])
    p.set_valor("continuidad", "G1")
    p._t_previa.stop()
    p._calcular_previa()
    st = A.estado_panel(p)
    A.reg(AR, "SUP-22 · parche G1 sobre una curva suelta: el mensaje dice qué corregir",
          not st["previa_ok"] and "caras vecinas" in st["mensaje"] and "soporte" not in st["mensaje"], f"mensaje=«{st['mensaje']}»")
    p.cancelar()
    A.esperar(100)


run("parche", parche)


# 4 Reglada (SUP-15) ---------------------------------------------------------------------------------------------------
def reglada():
    lados = lambda: [A.hit_curva(v, s, "Rect", i) for i in range(4)]  # noqa: E731
    sin = caso("reglada", {"aristas": lados}, {"tipo": "tangente", "distancia": "2 mm"}, None, "reglada tangente sin ingletear", rt=False)
    con = caso("reglada", {"aristas": lados}, {"tipo": "tangente", "distancia": "2 mm", "ingletear": True}, None,
               "reglada tangente con esquinas ingleteadas", foto="fusion_reglada_ingleteada")
    afuera = (24 * 14 - 200, 200 - 16 * 6)         # hacia afuera o hacia adentro del recorrido: el marco de 2 mm con esquinas vivas
    A.reg(AR, "reglada ingleteada: el marco cierra con esquinas vivas",
          sin is not None and con is not None and any(abs(con - x) < 0.5 for x in afuera) and con != sin,
          f"sin={sin} con={con} (esperaba {afuera})")
    caso("reglada", {"aristas": lados}, {"tipo": "tangente", "distancia": "2 mm", "alternas": True}, None, "reglada con caras alternas", rt=False)
    # SUP-15: la media luna (recta + arco) con esquinas ingleteadas; sale hacia afuera o hacia adentro del recorrido
    luna = lambda: [A.hit_curva(v, s, "Luna", i) for i in range(2)]  # noqa: E731

    def luna_esperada(d):
        r, x = 20.0, math.sqrt((20.0 + d) ** 2 - d ** 2)
        ys = [abs(d) * k / 4000 for k in range(4001)]
        linea = [r + (x - r) * y / abs(d) for y in ys]
        arco = [math.sqrt(((r + d) if d > 0 else r) ** 2 - y * y) for y in ys]
        esquina = sum((arco[k] - linea[k] + arco[k + 1] - linea[k + 1]) / 2 * (ys[1] - ys[0]) for k in range(4000))
        franja = (2 * r + 2 * x) / 2 * abs(d)
        return franja + pi * abs((r + d) ** 2 - r * r) / 2 + (2 if d > 0 else -2) * esquina

    sin_luna = caso("reglada", {"aristas": luna}, {"tipo": "tangente", "distancia": "5 mm"}, None,
                    "reglada de la media luna sin ingletear", rt=False)
    con_luna = caso("reglada", {"aristas": luna}, {"tipo": "tangente", "distancia": "5 mm", "ingletear": True}, None,
                    "reglada de la media luna con esquinas ingleteadas (recta + arco)", foto="fusion_reglada_luna_ingleteada")
    esperados = (luna_esperada(5.0), luna_esperada(-5.0))
    A.reg(AR, "reglada ingleteada entre recta y arco: el área es la de la esquina viva (±0,5 %)",
          con_luna is not None and sin_luna is not None and min(abs(con_luna - e) / e for e in esperados) < 5e-3
          and con_luna != sin_luna, f"sin={sin_luna} con={con_luna} esperaba {esperados}")


run("reglada", reglada)


# 5 Escalar una superficie (SUP-19) ---------------------------------------------------------------------------------------
run("escala de superficie", lambda: caso(
    "escala_3d", {"entidades": lambda: [A.hit_cuerpo(v, tubo)]}, {"factor": "2"}, 3 * 2 * pi * 5 * 20,
    "escala ×2 de una superficie", foto="fusion_escala_superficie"))


# 6 Descoser caras sueltas (SUP-18) -----------------------------------------------------------------------------------------
def descoser_caras():
    n0, antes = len(v.doc.estado_final.cuerpos), A.cuerpos_resumen(v)
    p = A.abrir(v, "descoser")
    A.elegir(p, "caras", A.hit_cara(v, caja, normal=(0, 0, 1)))
    p._t_previa.stop()
    p._calcular_previa()
    A.esperar(120)
    st = A.estado_panel(p)
    A.foto(v, "fusion_descoser_caras")
    p.aceptar()
    A.esperar(450)
    cuerpos = v.doc.estado_final.cuerpos
    ok = len(cuerpos) == n0 + 1 and sum(1 for c in cuerpos.values() if c.tipo == "superficie") >= 2
    A.reg(AR, "descoser una cara de la caja: queda esa cara suelta y las otras cinco cosidas", st["previa_ok"] and ok,
          f"cuerpos {n0} → {len(cuerpos)}; «{st['mensaje']}»")
    A.deshacer(v)
    A.reg(AR, "descoser caras: deshacer vuelve al estado anterior", A.cuerpos_resumen(v) == antes, "")
    p = A.abrir(v, "descoser")
    p.aceptar()
    A.esperar(120)
    A.reg(AR, "descoser sin elegir nada no crea ningún paso", A.n_ops(v) == len(v.doc.operaciones) and A.cuerpos_resumen(v) == antes,
          f"«{p.mensaje.text() if p.isVisible() else ''}»")
    if v.panel is not None and v.panel.isVisible():
        v.panel.cancelar()
    A.esperar(100)


run("descoser caras", descoser_caras)


# 7 Coser: bordes libres (SUP-21) ---------------------------------------------------------------------------------------------
def coser():
    p = A.abrir(v, "coser")
    A.elegir(p, "cuerpos", A.hit_cuerpo(v, quilt), A.hit_cuerpo(v, tapa))
    p.set_valor("tolerancia", "0.01 mm")
    A.esperar(150)
    w = p.widgets.get("resultado")
    t = w.text() if hasattr(w, "text") else str(w)
    A.reg(AR, "coser: el panel adelanta «Ninguno: se cierra un sólido»", "Ninguno" in t, f"texto=«{t}»")
    A.foto(v, "fusion_coser_info")
    p.cancelar()
    A.esperar(100)
    p = A.abrir(v, "coser")
    A.elegir(p, "cuerpos", A.hit_cuerpo(v, quilt))
    p.set_valor("tolerancia", "0.01 mm")
    A.esperar(150)
    w = p.widgets.get("resultado")
    t = w.text() if hasattr(w, "text") else str(w)
    A.reg(AR, "coser una caja abierta: el panel cuenta los bordes libres", "bordes libres" in t or "borde libre" in t, f"texto=«{t}»")
    p._t_previa.stop()
    p._calcular_previa()
    p.aceptar()
    A.esperar(450)
    op = v.doc.operaciones[-1]
    res = v.doc.resultados[-1]
    A.reg(AR, "coser una caja abierta: el aviso dice cuántos bordes y dónde", res.estado == "aviso" and "bordes libres" in (res.mensaje or "")
          and "cerca de" in res.mensaje, f"{op.TIPO}: «{res.mensaje}»")
    A.deshacer(v)


run("coser", coser)


# 8 Extender: alineación y asa con tope (SUP-17 y SUP-26) --------------------------------------------------------------------------
def mover_sim(w, pos):
    q = QPointF(pos)
    QApplication.sendEvent(w, QMouseEvent(QEvent.MouseMove, q, w.mapToGlobal(q), Qt.NoButton, Qt.NoButton, Qt.NoModifier))


def arrastrar(panel, g, desde, hasta, pasos=8):
    xy, ok = g.pantalla([desde, hasta])
    if not ok.all():
        return False
    a, b = (QPointF(*q) for q in xy)
    vis = panel.visor
    mover_sim(vis, a)
    QApplication.sendEvent(vis, QMouseEvent(QEvent.MouseButtonPress, a, vis.mapToGlobal(a), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier))
    for i in range(1, pasos + 1):
        q = a + (b - a) * (i / pasos)
        QApplication.sendEvent(vis, QMouseEvent(QEvent.MouseMove, q, vis.mapToGlobal(q), Qt.NoButton, Qt.LeftButton, Qt.NoModifier))
        A.esperar(15)
    QApplication.sendEvent(vis, QMouseEvent(QEvent.MouseButtonRelease, b, vis.mapToGlobal(b), Qt.LeftButton, Qt.NoButton, Qt.NoModifier))
    A.esperar(120)
    return True


def extender():
    A.MODALES.clear()
    p = A.abrir(v, "extender_sup")
    A.elegir(p, "aristas", A.hit_arista(v, tubo, lineal=False))
    p.set_valor("distancia", "5 mm")
    p._t_previa.stop()
    p._calcular_previa()
    A.esperar(150)
    campo = next(c for c in p.campos if c.clave == "alineacion")
    A.reg(AR, "extender: «Alineación de bordes» se ve con el tipo Natural", p._visible(campo), "")
    p.set_valor("tipo", "tangente")
    A.esperar(100)
    A.reg(AR, "extender: «Alineación de bordes» se oculta con el tipo Tangente", not p._visible(campo), "")
    p.set_valor("tipo", "natural")
    A.esperar(100)
    A.foto(v, "fusion_extender")
    g = p.manipuladores
    flecha = next((m for m in (g.manips if g else []) if isinstance(m, mp.Flecha) and m.clave == "distancia"), None)
    if flecha is None:
        A.reg(AR, "SUP-26 · extender muestra la flecha de distancia", False, "sin flecha")
        p.cancelar()
        return
    a, b = flecha.puntos(g)
    medio = (a + b) / 2
    arrastrar(p, g, medio, medio - flecha.direccion * 30.0)         # más allá del cero, hacia adentro de la superficie
    final = g.valor("distancia")
    A.reg(AR, "SUP-26 · arrastrar la flecha de Extender más allá del cero frena en 0", final >= -1e-9,
          f"distancia = {final:g} mm; texto del campo «{p.valores.get('distancia')}»")
    p.set_valor("distancia", "5 mm")
    p._t_previa.stop()
    p._calcular_previa()
    A.esperar(120)
    A.reg(AR, "SUP-26 · al escribir de nuevo 5 mm la vista previa se recupera", p._previa_ok, p.mensaje.text())
    p.cancelar()
    A.esperar(100)


run("extender", extender)


# 8b Extender con bordes libres en una cara curva que no es rectangular (SUP-17) ---------------------------------------------------
def extender_curva():
    A.MODALES.clear()
    antes, n0 = A.cuerpos_resumen(v), A.n_ops(v)
    cara = lambda: [A.hit_cara(v, esfera)]  # noqa: E731
    r = C.caso(v, AR, "recortar_sup", {"herramienta": lambda: [A.hit_plano(v, "YZ")], "region": cara}, {}, deshacer=False,
               etiqueta="recortar la esfera con el plano YZ (descentrado: el borde no es iso-paramétrico)")
    if not r:
        return
    forma = v.doc.estado_final.cuerpos[esfera].forma
    borde = next((a for a in refs.subformas(forma, "arista") if refs.firma_arista(a)["geom"] == "circulo"
                  and abs(refs.firma_arista(a)["medio"][0]) < 0.5), None)
    hit = A._clic_en(v, refs.firma_arista(borde)["medio"], {"arista"}) if borde is not None else None
    if not hit or hit["ref"].get("cuerpo") != esfera:
        A.reg(AR, "SUP-17 · elegir con el visor el borde de corte de la esfera", False, f"hit={hit}")
        return
    area0 = A.cuerpos_resumen(v)[esfera][1]
    p = A.abrir(v, "extender_sup")
    A.elegir(p, "aristas", hit)
    p.set_valor("distancia", "2 mm")
    p.set_valor("alineacion", "alinear")
    p._t_previa.stop()
    p._calcular_previa()
    A.esperar(150)
    st = A.estado_panel(p)
    A.reg(AR, "SUP-17 · «Alinear bordes» en una cara curva no rectangular avisa y sugiere «alineación libre»",
          not st["previa_ok"] and "no es rectangular" in st["mensaje"] and "libre" in st["mensaje"], f"mensaje=«{st['mensaje']}»")
    p.set_valor("alineacion", "libre")
    p._t_previa.stop()
    p._calcular_previa()
    A.esperar(150)
    st = A.estado_panel(p)
    A.foto(v, "fusion_extender_libre_curva")
    A.reg(AR, "SUP-17 · «Bordes libres» extiende la cara curva (vista previa sin error)", st["previa_ok"], f"mensaje=«{st['mensaje']}»")
    p.aceptar()
    A.esperar(500)
    R, d, alfa = 10.0, 2.0, math.acos(6.0 / 10.0)           # el borde es una circunferencia de apertura alfa vista desde el centro
    chico = 2 * pi * R * R * (math.cos(alfa) - math.cos(alfa + d / R))      # se queda el casquete chico: crece
    grande = 2 * pi * R * R * (math.cos(alfa - d / R) - math.cos(alfa))     # se queda la parte grande: la franja entra en el casquete
    sumado = A.cuerpos_resumen(v)[esfera][1] - area0
    A.reg(AR, "SUP-17 · la franja es la zona esférica de 2 mm de ancho (±1 %)",
          min(abs(sumado - chico) / chico, abs(sumado - grande) / grande) < 0.01, f"sumó {sumado:.3f}; esperaba {chico:.3f} o {grande:.3f}")
    k = 0
    while A.n_ops(v) > n0 and k < 4:             # el recorte previo y la extensión
        A.deshacer(v)
        k += 1
    A.reg(AR, "SUP-17 · deshacer deja la esfera como estaba", A.n_ops(v) == n0 and A.cuerpos_resumen(v) == antes,
          f"pasos {n0} → {A.n_ops(v)}; antes={antes.get(esfera)} ahora={A.cuerpos_resumen(v).get(esfera)}")


run("extender libre en cara curva", extender_curva)


# 9 Recortar y Destrimar manual con extensión y copia (SUP-16) -------------------------------------------------------------------------
def arista_a_altura(cid, z):
    forma = v.doc.estado_final.cuerpos[cid].forma
    for a in refs.subformas(forma, "arista"):
        f = refs.firma_arista(a)
        if f["geom"] != "linea" and abs(f["medio"][2] - z) < 0.5:
            hit = A._clic_en(v, f["medio"], {"arista"})
            if hit and hit["ref"].get("cuerpo") == cid:
                return hit
    return None


def destrimar():
    cara_tubo = lambda: [A.hit_cara(v, tubo)]  # noqa: E731
    r = C.caso(v, AR, "recortar_sup", {"herramienta": lambda: [A.hit_plano(v, "PM")], "region": cara_tubo}, {}, deshacer=False,
               etiqueta="recortar el tubo con el plano PM (queda la mitad)")
    A.reg(AR, "destrimar: el recorte previo existe", bool(r), "")
    corte = lambda: [arista_a_altura(tubo, 10.0)]  # noqa: E731
    sel = {"caras": cara_tubo, "aristas": corte}
    caso("destrimar", sel, {}, 2 * pi * 5 * 10, "destrimar manual: el borde de corte vuelve al límite natural",
         previos={"contornos": "manual"}, foto="fusion_destrimar_manual")
    caso("destrimar", sel, {"mantener_copia": True}, 2 * pi * 5 * 20, "destrimar manual y mantener la copia",
         previos={"contornos": "manual"})
    caso("destrimar", sel, {"extension": "5 mm"}, 2 * pi * 5 * 30 - 2 * pi * 5 * 10, "destrimar manual extendiendo 5 mm",
         previos={"contornos": "manual"})
    # el modo manual sin aristas se rechaza con un aviso
    p = A.abrir(v, "destrimar")
    A.elegir(p, "caras", *cara_tubo())
    p.set_valor("contornos", "manual")
    p._t_previa.stop()
    p._calcular_previa()
    st = A.estado_panel(p)
    A.reg(AR, "destrimar manual sin aristas avisa que hay que elegirlas", not st["previa_ok"] and "aristas" in st["mensaje"],
          f"«{st['mensaje']}»")
    p.cancelar()
    A.esperar(100)


run("destrimar", destrimar)


# 10 Ventana chica -----------------------------------------------------------------------------------------------------------------
def chica():
    for (w, h) in ((1024, 640), (800, 520)):
        v.resize(w, h)
        A.esperar(300)
        for clave, valores, sel in (("sup_extruir", {"lados": "dos_lados", "extension": "objeto"}, {"curvas": cur("Lin")}),
                                    ("sup_revolucion", {"lados": "dos_lados", "angulo": "90 deg"}, {"curvas": cur("RevL"), "eje": eje_z}),
                                    ("parche", {"agrupar": False}, {}), ("destrimar", {"contornos": "manual"}, {}),
                                    ("reglada", {"tipo": "direccion"}, {})):
            p = A.abrir(v, clave)
            for k, x in valores.items():
                p.set_valor(k, x)
            for campo, fn in sel.items():
                A.elegir(p, campo, *fn())
            A.esperar(500)
            dentro = v.area.rect().contains(p.geometry())
            A.reg(AR, f"ventana {w}x{h}: el panel de «{clave}» entra en el visor", dentro, f"panel={p.geometry()} área={v.area.rect()}")
            A.foto(v, f"fusion_chica_{clave}_{w}x{h}")
            p.cancelar()
            A.esperar(100)
    v.resize(1900, 1000)
    A.esperar(300)


run("ventana chica", chica)

# 11 El panel crece al cambiar de modo (B-113) --------------------------------------------------------------------
def crece():
    """Con el combo real: al elegir «A objeto» o «Dos lados» aparecen campos y el cuerpo del panel tiene que crecer hasta
    mostrarlos (sin barra ni «Más opciones» cortado) mientras haya lugar; en ventana chica sigue entrando en el visor."""
    def combo(p, clave, valor):
        campo = next(c for c in p.campos if c.clave == clave)
        p.widgets[clave].setCurrentIndex(list(campo.opciones).index(valor))
        A.esperar(200)

    for (w, h) in ((1900, 1000), (1024, 640), (800, 520)):
        v.resize(w, h)
        A.esperar(300)
        for clave, sel, cambios in (("sup_extruir", {"curvas": cur("Lin")}, (("extension", "objeto"), ("lados", "dos_lados"))),
                                    ("sup_revolucion", {"curvas": cur("RevL"), "eje": eje_z}, (("lados", "dos_lados"),))):
            p = A.abrir(v, clave)
            for campo, fn in sel.items():
                A.elegir(p, campo, *fn())
            for campo, valor in cambios:
                combo(p, campo, valor)
                barra = p.desplazador.verticalScrollBar().maximum()
                dentro = v.area.rect().contains(p.geometry())
                if w == 1900:
                    A.reg(AR, f"B-113 {w}x{h}: «{clave}» con {campo}={valor} muestra todo el cuerpo sin barra", barra == 0 and dentro,
                          f"barra={barra} panel={p.geometry()}")
                else:
                    A.reg(AR, f"B-113 {w}x{h}: «{clave}» con {campo}={valor} entra en el visor", dentro, f"panel={p.geometry()} área={v.area.rect()}")
            A.foto(v, f"fusion_crece_{clave}_{w}x{h}")
            p.cancelar()
            A.esperar(100)
    v.resize(1900, 1000)
    A.esperar(300)


run("el panel crece al cambiar de modo (B-113)", crece)

A.guardar_registro("u_superficie_fusion")
fallas = [r for r in A.REGISTRO if not r["ok"]]
print(f"\n=== {len(A.REGISTRO)} comprobaciones, {len(fallas)} con ✗ ===")
print("modales vistos:", A.MODALES[-10:])
v.close()
sys.exit(0)

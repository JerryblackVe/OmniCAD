# -*- coding: utf-8 -*-
"""ENSAMBLAR igual a Fusion (ASM-6 a ASM-8 y ASM-10 a ASM-15), en la ventana real y como una persona: elegir con el visor,
teclear en los campos (con coma, unidades, «nan»), Enter, Esc, Tab, reabrir para editar, deshacer, el panel del Estudio de
movimiento (valores, reproducir, modo, velocidad) y la ventana chica."""
import sys

import arnes as A
import numpy as np
import teclado as T
from omnicad import api
from omnicad.nucleo import geometria as geo
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QDialog

AR = "ENSAMBLAR ASM"
s = api.Sesion()


def L(nombre, **a):
    r = api.llamar(s, nombre, a)
    assert r["ok"], (nombre, a, r)
    return r["result"]


base = L("create_box", length=100, width=100, height=10)["bodies_created"][0]["id"]
poste = L("create_cylinder", radius=3, height=40, x=30)["bodies_created"][0]["id"]
tapa = L("create_box", length=60, width=40, height=30, x=-200)["bodies_created"][0]["id"]
brazo = L("create_box", length=20, width=10, height=10, x=300)["bodies_created"][0]["id"]
bloque = L("create_box", length=10, width=10, height=10, x=-300, y=200)["bodies_created"][0]["id"]
L("create_component", bodies=[base, poste], name="Base", grounded=True)
L("create_component", bodies=[brazo], name="Brazo")
L("create_component", bodies=[bloque], name="Bloque")
# piezas de las restricciones de componentes (ASM-17): un bloque fijo, una caja libre, un cilindro y una esfera
rfijo = L("create_box", length=40, width=40, height=20, x=150, y=300)["bodies_created"][0]["id"]
rcaja = L("create_box", length=20, width=20, height=10, x=150, y=295, z=40)["bodies_created"][0]["id"]
rcil = L("create_cylinder", radius=8, height=30, x=150, y=-100)["bodies_created"][0]["id"]
resf = L("create_sphere", radius=8, x=250, y=0, z=40)["bodies_created"][0]["id"]
L("create_component", bodies=[rfijo], name="RFijo", grounded=True)
rtoca = L("create_box", length=40, width=20, height=10, x=160, y=-60, z=10)["bodies_created"][0]["id"]   # llega a tocar al cilindro
for _cid, _n in ((rcaja, "RCaja"), (rcil, "RCil"), (resf, "REsf"), (rtoca, "RToca")):
    L("create_component", bodies=[_cid], name=_n)
app, v = A.iniciar(s.doc)


def _mostrar_sin_foco(self):
    """El panel del estudio se abre transparente y sin foco en la prueba (como `A.mostrar`, que no se puede usar acá porque
    llama a `show()` y éste es el `show()` que se cambia)."""
    if A.modo_ventana() == "minimizada":
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setWindowFlags(self.windowFlags() | Qt.WindowTransparentForInput | Qt.WindowDoesNotAcceptFocus)
        self.setWindowOpacity(0.0)
    QDialog.show(self)


from omnicad.ui.estudio_movimiento import PanelEstudioMovimiento  # noqa: E402
PanelEstudioMovimiento.show = _mostrar_sin_foco


def caja(cid):
    return [round(float(x), 2) for p in geo.caja_envolvente(v.doc.estado_final.cuerpos[cid].forma) for x in p]


def centro(cid):
    c = caja(cid)
    return np.array([(c[i] + c[i + 3]) / 2 for i in range(3)])


def ens():
    return api.llamar(s, "get_assembly", {})["result"]


def union(nombre):
    return next(j for j in ens()["joints"] if j["name"] == nombre)


def comp(nombre):
    return next(c for c in ens()["components"] if c["name"] == nombre)


def run(nombre, f):
    A.correr(f"{AR} · {nombre}", f)


def C_vivo(p):
    try:
        return p.isVisible()
    except RuntimeError:
        return False


def cuerpo(cid):
    return [A.hit_cuerpo(v, cid)]


def circulo(cid, z):
    """La arista circular del cuerpo a la altura z, elegida con un clic del visor (la «lineal=False» del arnés daría la costura)."""
    from omnicad.nucleo import referencias as refs
    for a in refs.subformas(v.doc.estado_final.cuerpos[cid].forma, "arista"):
        f = refs.firma_arista(a)
        if f["geom"] == "circulo" and abs(f["centro"][2] - z) < 0.01:
            hit = A._clic_en(v, f["medio"], {"arista"})
            if hit and hit["ref"].get("cuerpo") == cid:
                return hit
    return None


def arriba(cid):
    return [A.hit_cara(v, cid, normal=(0, 0, 1))]


def aceptar(p):
    p.aceptar()
    A.esperar(300)


def reabrir(op_id):
    """Doble clic en el paso del timeline (como la persona) y devuelve el panel que se abrió."""
    lista = v.timeline.lista
    fila = next(lista.item(i) for i in range(lista.count()) if lista.item(i).data(Qt.UserRole) == op_id)
    lista.scrollToItem(fila)
    A.esperar(100)
    centro_fila = lista.visualItemRect(fila).center()
    QTest.mouseClick(lista.viewport(), Qt.LeftButton, Qt.NoModifier, centro_fila)
    A.esperar(60)
    QTest.mouseDClick(lista.viewport(), Qt.LeftButton, Qt.NoModifier, centro_fila)
    A.esperar(300)
    return v.panel


# 1. Origen de unión: modo «Entre dos caras» ---------------------------------------------------------------------------------
def origen_entre_caras():
    p = A.abrir(v, "origen_union")
    et = {c[0]: c[3] for c in A.etiquetas(p)}
    A.reg(AR, "origen: «Segundo ajuste» está oculto en el modo Simple", et["origen_b"] is False and et["clave"] is True, str(et))
    p.set_valor("modo", "entre_caras")
    A.esperar(100)
    et = {c[0]: c[3] for c in A.etiquetas(p)}
    A.reg(AR, "origen: en «Entre dos caras» aparece el segundo ajuste y se oculta el punto de ajuste", et["origen_b"] is True and et["clave"] is False, str(et))
    A.elegir(p, "origen", *arriba(base))
    p._t_previa.stop()
    p._calcular_previa()
    A.reg(AR, "origen: con una sola cara no hay vista previa", not p._previa_ok, p.mensaje.text() if p.mensaje.isVisible() else "")
    A.elegir(p, "origen_b", *arriba(tapa))
    p._t_previa.stop()
    p._calcular_previa()
    A.reg(AR, "origen: la vista previa anda con las dos caras", p._previa_ok, p.mensaje.text())
    aceptar(p)
    o = ens()["joint_origins"]
    # arriba de la Base (z = 10) y arriba de la Tapa (z = 30): el origen queda en z = 20, sobre el centro de la cara de la Base
    A.reg(AR, "origen entre la tapa de la Base (z=10) y la de la Tapa (z=30) queda en z=20", len(o) == 1 and abs(o[0]["origin"][2] - 20) < 0.01 and abs(o[0]["origin"][0]) < 0.01, str(o))
    # reabrir con doble clic en el timeline y ver que el segundo ajuste volvió
    p = reabrir(o[0]["id"])
    A.reg(AR, "origen: al reabrir con doble clic vuelven el modo y la segunda cara", p is not None and p.valores.get("modo") == "entre_caras" and bool(p.valores.get("origen_b")), str(None if p is None else {k: p.valores.get(k) for k in ("modo", "origen_b")}))
    if p is not None:
        QTest.keyClick(p.widgets["angulo"], Qt.Key_Escape)       # Esc en el panel lo cancela y no cambia nada
        A.esperar(150)
        A.reg(AR, "origen: Esc cierra el panel de edición", not C_vivo(p), "")
    L("undo")
    A.reg(AR, "origen: deshacer lo quita", not ens()["joint_origins"], "")


run("origen entre dos caras", origen_entre_caras)


# 2. Unión con un eje de giro propio (la arista del poste) -----------------------------------------------------------------------
def union_eje_propio():
    p = A.abrir(v, "union")
    A.elegir(p, "origen1", *arriba(brazo))
    A.elegir(p, "origen2", *arriba(base))
    p.set_valor("tipo", "revolucion")
    et = {c[0]: c[3] for c in A.etiquetas(p)}
    A.reg(AR, "unión: aparecen el eje propio de giro, sus límites y el reposo", et.get("ref_eje_giro") and et.get("minimo") and et.get("reposo_giro") and not et.get("min_desliz2"), str({k: et[k] for k in et if "eje" in k or "reposo" in k or "min" in k}))
    A.reg(AR, "unión: el eje propio de deslizamiento sigue oculto en una revolución", et.get("ref_eje_desliz") is False, "")
    circ = circulo(poste, 40)
    A.elegir(p, "ref_eje_giro", circ)
    for texto, esperado in (("nan", False), ("inf", False), ("abc", False)):
        T.teclear(p, "giro", texto, Qt.Key_Tab)
        p._t_previa.stop()
        p._calcular_previa()
        A.reg(AR, f"unión: ángulo {texto!r} no se acepta y el mensaje lo dice", p._previa_ok is esperado and ("número" in p.mensaje.text() or "desconocido" in p.mensaje.text().lower() or p.mensaje.text() != ""), p.mensaje.text())
    T.teclear(p, "giro", "0", Qt.Key_Tab)
    T.teclear(p, "reposo_giro", "25 deg", Qt.Key_Tab)
    p._t_previa.stop()
    p._calcular_previa()
    A.reg(AR, "unión: con el reposo 25° la vista previa anda", p._previa_ok, p.mensaje.text())
    aceptar(p)
    j = ens()["joints"][0]
    A.reg(AR, "unión con eje propio creada", j["custom_rotation_axis"] and j["limits_by_motion"]["rotation"]["rest"] == "25 deg", str(j))
    u0 = union(j["name"])
    c0 = centro(brazo)
    # accionar tecleando 90 deg: el brazo gira 90° alrededor del poste (x=30, y=0)
    pa = A.abrir(v, "accionar_uniones")
    pa.set_valor("union", u0["id"])
    T.teclear(pa, "giro", "90 deg", Qt.Key_Return)
    A.esperar(100)
    if C_vivo(pa):                                   # Enter ya puede haberlo aceptado
        aceptar(pa)
    c1 = centro(brazo)
    esperado = np.array([30, 0, c0[2]]) + np.array([[0, -1, 0], [1, 0, 0], [0, 0, 1]]) @ (c0 - np.array([30, 0, c0[2]]))
    A.reg(AR, "accionar 90°: el brazo gira alrededor del poste (no del centro de la unión)", np.allclose(c1, esperado, atol=0.05), f"antes={c0} ahora={c1} esperado={esperado}")
    pa = A.abrir(v, "accionar_uniones")
    pa.set_valor("union", u0["id"])
    g = pa.manipuladores
    A.esperar(150)
    pa._t_previa.stop()
    pa._calcular_previa()
    from omnicad.ui import manipuladores as mp
    arco = next((m for m in (g.manips if g else []) if isinstance(m, mp.Angulo)), None)
    A.reg(AR, "accionar: el arco de giro se dibuja en el eje propio (pasa por el poste)", arco is not None and abs(arco.centro[0] - 30) < 0.5 and abs(arco.centro[1]) < 0.5, str(None if arco is None else arco.centro))
    pa.cancelar()
    A.foto(v, "ensamblar_asm_union_eje_propio")


run("unión con eje propio", union_eje_propio)


# 3. Unión deslizante con límites por movimiento ------------------------------------------------------------------------------
def union_limites():
    p = A.abrir(v, "union")
    A.elegir(p, "origen1", *arriba(bloque))
    A.elegir(p, "origen2", *arriba(tapa))
    p.set_valor("tipo", "planar")
    et = {c[0]: c[3] for c in A.etiquetas(p)}
    A.reg(AR, "planar: límites de «Deslizamiento 2» visibles y el principal en «Límite mínimo / máximo»", et.get("min_desliz2") and et.get("max_desliz2") and et.get("minimo") and not et.get("min_giro"), str({k: v_ for k, v_ in et.items() if "min" in k or "max" in k}))
    T.teclear(p, "min_desliz2", "-5", Qt.Key_Tab)
    T.teclear(p, "max_desliz2", "8,5 mm", Qt.Key_Tab)
    T.teclear(p, "desliz2", "20", Qt.Key_Tab)
    p._t_previa.stop()
    p._calcular_previa()
    A.reg(AR, "planar: coma decimal y valor fuera de límite: la vista previa anda", p._previa_ok, p.mensaje.text())
    aceptar(p)
    j = ens()["joints"][-1]
    A.reg(AR, "planar: el límite máximo 8,5 recortó el Deslizamiento 2 de 20", abs(j["values"]["slide2"] - 8.5) < 1e-6, str(j))
    p = reabrir(j["id"])                             # reabrir con doble clic: vuelven los límites escritos
    A.reg(AR, "planar: al reabrir vuelven los límites de Deslizamiento 2", p is not None and str(p.valores.get("min_desliz2")) == "-5" and "8" in str(p.valores.get("max_desliz2")), str(None if p is None else {k: p.valores.get(k) for k in ("min_desliz2", "max_desliz2")}))
    if p is not None:
        p.cancelar()


run("unión planar con límites", union_limites)


# 4. Vínculo con grado de libertad y «Animar» ---------------------------------------------------------------------------------
def vinculo_asm():
    js = ens()["joints"]
    p = A.abrir(v, "vinculo_movimiento")
    p.set_valor("union1", js[0]["id"])
    p.set_valor("union2", js[1]["id"])
    A.esperar(100)
    opc1 = [p.widgets["mov1"].itemData(i) for i in range(p.widgets["mov1"].count())]
    opc2 = [p.widgets["mov2"].itemData(i) for i in range(p.widgets["mov2"].count())]
    A.reg(AR, "vínculo: los movimientos que se ofrecen son los de cada unión", opc1 == ["", "giro"] and "desliz2" in opc2 and "giro" in opc2, f"{opc1} / {opc2}")
    p.set_valor("mov2", "desliz")
    T.teclear(p, "factor", "0,5", Qt.Key_Tab)
    boton = p.widgets["animar"]
    QTest.mouseClick(boton, Qt.LeftButton)
    A.esperar(400)
    anda = getattr(v, "_t_vinculo", None) is not None and v._t_vinculo.isActive()
    A.reg(AR, "vínculo: «Animar» arranca la animación y mueve el dibujo", anda and bool(v.visor.transformaciones), f"transformaciones={len(v.visor.transformaciones)}")
    QTest.mouseClick(boton, Qt.LeftButton)
    A.esperar(150)
    A.reg(AR, "vínculo: un segundo clic en «Animar» la detiene y el dibujo vuelve", not v._t_vinculo.isActive() and not v.visor.transformaciones, "")
    T.teclear(p, "factor", "nan", Qt.Key_Tab)
    p._t_previa.stop()
    p._calcular_previa()
    A.reg(AR, "vínculo: relación «nan» no se acepta (dice que no es un número)", not p._previa_ok and "número" in p.mensaje.text(), p.mensaje.text())
    T.teclear(p, "factor", "0,5", Qt.Key_Tab)
    p._t_previa.stop()
    p._calcular_previa()
    aceptar(p)
    vin = ens()["motion_links"]
    A.reg(AR, "vínculo creado con el movimiento «slide» de la unión 2", len(vin) == 1 and vin[0]["motion2"] == "slide" and vin[0]["ratio"].replace(",", ".") in ("0.5", "0,5"), str(vin))


run("vínculo por grado de libertad", vinculo_asm)


# 5. Estudio de movimiento como panel ---------------------------------------------------------------------------------------
def estudio():
    v.acciones["estudio_movimiento"].trigger()
    A.esperar(300)
    pe = getattr(v, "_panel_estudio", None)
    A.reg(AR, "estudio: el botón abre el panel", pe is not None and pe.isVisible(), "")
    if pe is None:
        return
    filas = pe.filas
    A.reg(AR, "estudio: hay una fila por movimiento de cada unión", len(filas) >= 3, str([(f["union"], f["clave"], f["sigue"]) for f in filas]))
    sigue = [f for f in filas if f["sigue"]]
    A.reg(AR, "estudio: lo que sigue un vínculo queda bloqueado", all(not f["spin"].isEnabled() and not f["marca"].isEnabled() for f in sigue) and len(sigue) == 1, str([f["clave"] for f in sigue]))
    # teclear un valor en el campo de la primera fila y Enter
    f0 = filas[0]
    antes = len(v.visor.transformaciones)
    sp = f0["spin"].lineEdit()
    QTest.mouseClick(sp, Qt.LeftButton)
    QTest.keyClick(sp, Qt.Key_A, Qt.ControlModifier)
    QTest.keyClicks(sp, "45,5")
    QTest.keyClick(sp, Qt.Key_Return)
    A.esperar(150)
    A.reg(AR, "estudio: teclear «45,5» + Enter pone el valor y dibuja el mecanismo", abs(f0["spin"].value() - 45.5) < 0.01 and len(v.visor.transformaciones) > antes, f"valor={f0['spin'].value()} transformaciones={len(v.visor.transformaciones)}")
    # el documento no cambió
    A.reg(AR, "estudio: no toca el documento (el valor guardado de la unión no cambió)", union(f0["union"] and [j["name"] for j in ens()["joints"] if j["id"] == f0["union"]][0])["values"]["rotation"] != 45.5, "")
    # valores malos tecleados: el campo se queda con el último válido
    for malo in ("abc", "nan", "1e9", ""):
        antes_v = f0["spin"].value()
        QTest.mouseClick(sp, Qt.LeftButton)
        QTest.keyClick(sp, Qt.Key_A, Qt.ControlModifier)
        if malo:
            QTest.keyClicks(sp, malo)
        else:
            QTest.keyClick(sp, Qt.Key_Delete)
        QTest.keyClick(sp, Qt.Key_Tab)
        A.esperar(60)
        A.reg(AR, f"estudio: el valor malo {malo!r} deja un número válido en el campo", np.isfinite(f0["spin"].value()), f"{antes_v} → {f0['spin'].value()}")
    # deslizador
    f0["deslizador"].setValue(0)
    A.esperar(60)
    A.reg(AR, "estudio: el deslizador en 0 pone el mínimo del recorrido", abs(f0["spin"].value() - f0["rango"][0]) < 0.01, str(f0["spin"].value()))
    # reproducir
    pe.velocidad.setValue(4)                            # 4×
    pe.modo.setCurrentIndex(0)                          # en un sentido
    QTest.mouseClick(pe.b_adelante, Qt.LeftButton)
    A.esperar(250)
    A.reg(AR, "estudio: ⏩ reproduce y el valor avanza", pe.reproduciendo and f0["spin"].value() > f0["rango"][0], f"valor={f0['spin'].value()}")
    A.esperar(1400)
    A.reg(AR, "estudio: «En un sentido» termina solo y queda en el máximo", not pe.reproduciendo and abs(f0["spin"].value() - f0["rango"][1]) < 0.5, f"valor={f0['spin'].value()} reproduciendo={pe.reproduciendo}")
    pe.modo.setCurrentIndex(2)                          # bucle
    QTest.mouseClick(pe.b_atras, Qt.LeftButton)
    A.esperar(1400)
    A.reg(AR, "estudio: «Bucle» sigue andando pasado un recorrido entero", pe.reproduciendo, "")
    QTest.mouseClick(pe.b_parar, Qt.LeftButton)
    A.reg(AR, "estudio: ■ detiene", not pe.reproduciendo, "")
    v1 = f0["spin"].value()
    QTest.mouseClick(pe.b_paso, Qt.LeftButton)
    QTest.mouseClick(pe.b_paso_atras, Qt.LeftButton)
    A.reg(AR, "estudio: ▶ y ◀ avanzan y retroceden un paso (el 5 % del recorrido)", abs(f0["spin"].value() - v1) < 0.01, f"{v1} → {f0['spin'].value()}")
    pe.modo.setCurrentIndex(1)                          # ida y vuelta
    pe.velocidad.setValue(4)
    QTest.mouseClick(pe.b_adelante, Qt.LeftButton)
    A.esperar(2500)
    A.reg(AR, "estudio: «Ida y vuelta» termina solo", not pe.reproduciendo, "")
    A.foto(v, "ensamblar_asm_estudio_ventana")
    pe.grab().save(str(A.CAPTURAS / "ensamblar_asm_estudio_panel.png"))
    QTest.keyClick(pe, Qt.Key_Escape)
    A.esperar(200)
    A.reg(AR, "estudio: Esc cierra el panel y el dibujo vuelve al modelo", not pe.isVisible() and not v.visor.transformaciones, f"visible={pe.isVisible()}")


run("estudio de movimiento", estudio)


# 6. Anclar, posición inicial, capturar y revertir -------------------------------------------------------------------------
def posiciones():
    n = A.n_ops(v)
    p = A.abrir(v, "anclar_componente")
    A.elegir(p, "cuerpos", *cuerpo(bloque))
    aceptar(p)
    A.reg(AR, "anclar: el componente queda anclado (como un paso del timeline)", comp("Bloque")["pinned"] and A.n_ops(v) == n + 1, str(comp("Bloque")))
    p = A.abrir(v, "union")
    A.elegir(p, "origen1", *arriba(bloque))
    A.elegir(p, "origen2", *arriba(base))
    p._t_previa.stop()
    p._calcular_previa()
    A.reg(AR, "anclar: una unión que mueve el componente anclado se rechaza con el motivo", not p._previa_ok and "fijo" in p.mensaje.text(), p.mensaje.text())
    p.cancelar()
    p = A.abrir(v, "anclar_componente")
    A.elegir(p, "cuerpos", *cuerpo(bloque))
    p.set_valor("anclado", False)
    aceptar(p)
    A.reg(AR, "desanclar: el componente vuelve a poder moverse", not comp("Bloque")["pinned"], "")
    # posición inicial: teclear con coma, unidades, nan; Esc descarta
    c0 = caja(bloque)
    p = A.abrir(v, "posicion_inicial")
    A.elegir(p, "cuerpos", *cuerpo(bloque))
    T.teclear(p, "x", "25,5 mm", Qt.Key_Tab)
    T.teclear(p, "rz", "90 deg", Qt.Key_Tab)
    T.teclear(p, "y", "nan", Qt.Key_Tab)
    p._t_previa.stop()
    p._calcular_previa()
    A.reg(AR, "posición inicial: «nan» en una distancia se rechaza con «No es un número»", not p._previa_ok and "número" in p.mensaje.text(), p.mensaje.text())
    T.teclear(p, "y", "-10", Qt.Key_Tab)
    p._t_previa.stop()
    p._calcular_previa()
    A.reg(AR, "posición inicial: con valores buenos la vista previa anda", p._previa_ok, p.mensaje.text())
    aceptar(p)
    c1 = caja(bloque)
    # 10×10×10 girado 90° queda igual de caja; solo se corrió (25,5, −10, 0)
    A.reg(AR, "posición inicial: el bloque se corrió 25,5 en X y −10 en Y", np.allclose(np.array(c1) - np.array(c0), [25.5, -10, 0, 25.5, -10, 0], atol=0.01), f"{c0} → {c1}")
    # reabrir, cambiar y Esc
    op = next(o for o in v.doc.operaciones if o.TIPO == "posicion_inicial")
    p = reabrir(op.id)
    if p is not None:
        T.teclear(p, "x", "99", Qt.Key_Escape)
        A.esperar(200)
        A.reg(AR, "posición inicial: Esc descarta lo tecleado", abs(caja(bloque)[0] - c1[0]) < 0.01, f"{caja(bloque)}")
        if C_vivo(p):
            p.cancelar()
    # capturar (todos) y revertir (el bloque)
    p = A.abrir(v, "capturar_posicion")
    aceptar(p)
    p = A.abrir(v, "posicion_inicial")
    A.elegir(p, "cuerpos", *cuerpo(bloque))
    T.teclear(p, "z", "30", Qt.Key_Tab)
    aceptar(p)
    alto = caja(bloque)
    p = A.abrir(v, "revertir_posicion")
    A.elegir(p, "cuerpos", *cuerpo(bloque))
    aceptar(p)
    A.reg(AR, "capturar y revertir: el bloque vuelve a lo capturado (antes de subirlo 30)", abs(caja(bloque)[2] - (alto[2] - 30)) < 0.01, f"{alto} → {caja(bloque)}")
    for _ in range(5):
        A.deshacer(v)
    A.reg(AR, "deshacer en cadena: el modelo sigue sano", all(st.estado != "error" for st in v.doc.resultados), "")


run("anclar, posición inicial, capturar y revertir", posiciones)


# 6b. Restricción de componentes (ASM-17): Alinear, Ángulo, Centro y Tangente, con captura de cada una --------------------------
def curva(cid, geom):
    """Una cara curva (cilindro o esfera) del cuerpo elegida con un clic real: se prueban puntos de su superficie hasta que el visor
    devuelve esa cara (el centro de masa de una cara curva cae adentro del cuerpo)."""
    from omnicad.nucleo import consultas, referencias as refs
    forma = v.doc.estado_final.cuerpos[cid].forma
    for c in refs.subformas(forma, "cara"):
        f = refs.firma_cara(c)
        if f["geom"] != geom:
            continue
        if geom == "esfera":
            o, r = consultas.centro_esfera(c), f["radio"]
        else:
            o, r = np.array(f["centro"]), f["radio"]
        for d in ((1, -1, 0), (1, 0, 0), (0, -1, 0), (1, -1, 1), (-1, 0, 0), (0, 1, 0), (0, 0, 1)):
            hit = A._clic_en(v, o + r * np.array(d) / np.linalg.norm(d), {"cara"})
            if hit and hit["ref"].get("cuerpo") == cid and hit["ref"]["firma"]["geom"] == geom:      # no la tapa que tapa el clic
                return [hit]
    return [None]


def restriccion(etiqueta, sel, vals, foto, comprueba, rechaza=None):
    """Abre el panel, elige con el visor, pone los valores, saca la captura de la vista previa, acepta, mide y deshace."""
    p = A.abrir(v, "restriccion_componentes")
    if p is None:
        A.reg(AR, f"restricción {etiqueta}: abre el panel", False, "no abrió")
        return
    for k, val in vals.items():
        p.set_valor(k, val)
    A.esperar(80)
    for campo, hs in sel:
        if not hs or any(h is None for h in hs):
            A.reg(AR, f"restricción {etiqueta}: elegir «{campo}» con el visor", False, "el visor no devolvió la entidad")
            p.cancelar()
            return
        A.elegir(p, campo, *hs)
    p._t_previa.stop()
    p._calcular_previa()
    A.esperar(150)
    texto = p.mensaje.text() if p.mensaje.isVisible() else ""
    if rechaza:
        A.reg(AR, f"restricción {etiqueta}: se rechaza con un aviso claro", not p._previa_ok and rechaza in texto, texto)
        A.foto(v, f"restriccion_{foto}")
        p.cancelar()
        return
    A.reg(AR, f"restricción {etiqueta}: vista previa", p._previa_ok, texto)
    A.foto(v, f"restriccion_{foto}")
    if not p._previa_ok:
        p.cancelar()
        return
    aceptar(p)
    A.reg(AR, f"restricción {etiqueta}: resultado", comprueba(), f"RCaja={caja(rcaja)} REsf={caja(resf)} RCil={caja(rcil)}")
    L("undo")


def restricciones():
    cara = lambda cid, n: [A.hit_cara(v, cid, normal=n)]  # noqa: E731
    restriccion("Alinear (tapa de la caja al ras de la del bloque)",
                [("ref1", cara(rcaja, (0, 0, 1))), ("ref2", cara(rfijo, (0, 0, 1)))], {"tipo": "alinear"}, "alinear",
                lambda: abs(caja(rcaja)[5] - 20.0) < 0.01)
    restriccion("Ángulo (30° entre la tapa de la caja y la del bloque)",
                [("ref1", cara(rcaja, (0, 0, 1))), ("ref2", cara(rfijo, (0, 0, 1)))], {"tipo": "angulo", "angulo": "30 deg"}, "angulo",
                lambda: caja(rcaja)[5] - caja(rcaja)[2] > 10.5)
    p = A.abrir(v, "restriccion_componentes")
    p.set_valor("tipo", "centro")
    p.set_valor("modo2", "entre_caras")
    A.esperar(100)
    et = {c[0]: c[3] for c in A.etiquetas(p)}
    A.reg(AR, "restricción Centro: aparecen los modos y la segunda cara, no el desfase ni el ángulo",
          et["modo1"] and et["modo2"] and et["ref2b"] and not et["ref1b"] and not et["desfase"] and not et["angulo"], str(et))
    v.visor.vista("izquierda")                                   # las caras -X solo se ven desde ese lado; las +X, desde el otro
    A.esperar(200)
    A.elegir(p, "ref1", *cara(rcaja, (-1, 0, 0)))
    A.elegir(p, "ref2", *cara(rfijo, (-1, 0, 0)))
    v.visor.vista("derecha")
    A.esperar(200)
    A.elegir(p, "ref2b", *cara(rfijo, (1, 0, 0)))
    v.visor.vista("iso")
    A.esperar(200)
    p._t_previa.stop()
    p._calcular_previa()
    A.esperar(150)
    A.reg(AR, "restricción Centro: vista previa", p._previa_ok, p.mensaje.text() if p.mensaje.isVisible() else "")
    A.foto(v, "restriccion_centro")
    aceptar(p)
    A.reg(AR, "restricción Centro: la cara de la caja queda en el plano medio del bloque (x=150)", abs(caja(rcaja)[0] - 150) < 0.01, f"RCaja={caja(rcaja)}")
    L("undo")
    from PySide6.QtWidgets import QPushButton
    p = A.abrir(v, "restriccion_componentes")
    boton = next(x for x in p.findChildren(QPushButton) if x.text().startswith("+ Agregar"))
    A.elegir(p, "ref1", *cara(rcaja, (0, -1, 0)))
    A.elegir(p, "ref2", *cara(rfijo, (0, -1, 0)))
    QTest.mouseClick(boton, Qt.LeftButton)
    A.esperar(100)
    A.reg(AR, "conjunto: «+ Agregar restricción» guarda la fila y deja los campos vacíos",
          len(p.valores["filas"]) == 1 and not p.valores["ref1"] and p._lista_filas.count() == 1, p._lista_filas.item(0).text() if p._lista_filas.count() else "")
    p._lista_filas.setCurrentRow(0)                              # editar la fila guardada tecleando: nombre y desfase
    for caja_texto, texto in ((p._edit_nombre, "frente"), (p._edit_desfase, "0 mm")):
        caja_texto.setFocus()
        caja_texto.selectAll()
        QTest.keyClicks(caja_texto, texto)
        QTest.keyClick(caja_texto, Qt.Key_Tab)                   # Tab termina la edición (Enter aceptaría todo el panel)
    A.esperar(100)
    A.reg(AR, "conjunto: nombre y desfase de la fila guardada, tecleados en las cajas de la lista",
          p._lista_filas.currentRow() == 0 and p._lista_filas.item(0).text().startswith("1. frente") and p.valores["filas"][0]["desfase"] == "0 mm",
          p._lista_filas.item(0).text())
    A.elegir(p, "ref1", *cara(rcaja, (0, 0, 1)))
    A.elegir(p, "ref2", *cara(rfijo, (0, 0, 1)))
    p._t_previa.stop()
    p._calcular_previa()
    A.esperar(150)
    det = [(x["ref"]["cuerpo"], x["ref"]["firma"].get("normal")) for k in ("ref1", "ref2") for x in p.valores[k]]
    det += [(x["ref"]["cuerpo"], x["ref"]["firma"].get("normal")) for f in p.valores["filas"] for k in ("ref1", "ref2") for x in f[k]]
    A.reg(AR, "conjunto: vista previa con las dos filas", p._previa_ok, (p.mensaje.text() if p.mensaje.isVisible() else "") + f" {det} rcaja={rcaja} rfijo={rfijo}")
    A.foto(v, "restriccion_conjunto")
    aceptar(p)
    A.reg(AR, "conjunto: un solo paso deja la tapa al ras y la cara frontal alineada", caja(rcaja) == [140.0, 280.0, 10.0, 160.0, 300.0, 20.0], f"RCaja={caja(rcaja)}")
    A.reg(AR, "conjunto: el timeline tiene UN paso de restricción", len([o for o in v.doc.operaciones if o.TIPO == "restriccion"]) == 1, "")
    L("undo")
    # Preview On Hover: el cursor (simulado en el visor, nunca el real) sobre la cara del componente 2 muestra la previa sin elegirla
    from PySide6.QtCore import QEvent, QPointF
    from PySide6.QtGui import QMouseEvent
    from PySide6.QtWidgets import QApplication
    p = A.abrir(v, "restriccion_componentes")
    A.elegir(p, "ref1", *cara(rcaja, (0, 0, 1)))
    destino = cara(rfijo, (0, 0, 1))[0]
    p._activar(next(c for c in p.campos if c.clave == "ref2"))
    q = v.visor.proyectar(np.array(destino["ref"]["firma"]["centro"], float))

    def cursor(x, y):
        pos = QPointF(float(x), float(y))
        QApplication.sendEvent(v.visor, QMouseEvent(QEvent.MouseMove, pos, v.visor.mapToGlobal(pos), Qt.NoButton, Qt.NoButton, Qt.NoModifier))
        A.esperar(200)
    qx, qy = q if isinstance(q, (tuple, list, np.ndarray)) else (q.x(), q.y())
    vistos = []
    v.visor.entidad_sobre.connect(lambda h: vistos.append(None if h is None else (h["ref"].get("cuerpo"), h["ref"].get("tipo"))))
    for dx in (6, 3, 0):                                                      # como la persona: se acerca y se posa; el visor solo avisa al cambiar
        cursor(qx + dx, qy + dx)
        if p._sobre_activo:
            break
    A.reg(AR, "restricción: vista previa al pasar el cursor por la cara del componente 2 (sin elegirla)",
          p._sobre_activo and not p.valores["ref2"] and p._previa_ok and p.ultima_op is not None,
          f"{A.estado_panel(p)} sobre_activo={p._sobre_activo} filtro={v.visor.filtro} modo={v.visor.modo} vistos={vistos} destino={destino['ref'].get('cuerpo')} q=({qx:.0f},{qy:.0f}) visor={v.visor.width()}x{v.visor.height()}")
    QApplication.sendEvent(v.visor, QEvent(QEvent.Leave))                    # el cursor sale del visor (hacia el panel)
    A.esperar(200)
    A.reg(AR, "restricción: al sacar el cursor la previa vuelve a la de lo elegido (sin componente 2, no hay)",
          not p._sobre_activo and not p.valores["ref2"] and p.ultima_op is None, f"{A.estado_panel(p)} sobre_activo={p._sobre_activo} ref2={p.valores['ref2']} vistos={vistos}")
    p.cancelar()
    restriccion("Alinear con límite máximo (desfase de 8 mm recortado a 5 mm)",
                [("ref1", cara(rcaja, (0, 0, 1))), ("ref2", cara(rfijo, (0, 0, 1)))], {"desfase": "8 mm", "maximo": "5 mm"}, "alinear_limite",
                lambda: abs(abs(caja(rcaja)[5] - 20.0) - 5.0) < 0.01)
    restriccion("Alinear con límite y «Usar desfase como apoyo» fuera del rango (error)",
                [("ref1", cara(rcaja, (0, 0, 1))), ("ref2", cara(rfijo, (0, 0, 1)))],
                {"desfase": "8 mm", "maximo": "5 mm", "apoyo": True}, "alinear_apoyo_fuera", None, rechaza="apoyo")
    restriccion("Tangente (esfera sobre la tapa del bloque)",
                [("ref1", curva(resf, "esfera")), ("ref2", cara(rfijo, (0, 0, 1)))], {"tipo": "tangente"}, "tangente_esfera",
                lambda: abs(caja(resf)[2] - 20.0) < 0.01)
    restriccion("Tangente (caja contra el cilindro)",
                [("ref1", cara(rcaja, (0, -1, 0))), ("ref2", curva(rcil, "cilindro"))], {"tipo": "tangente"}, "tangente_cilindro",
                lambda: abs(caja(rcaja)[1] - (-100 + 8)) < 0.01 or abs(caja(rcaja)[1] - (-100 - 8)) < 0.01)
    restriccion("Tangente con «Todas las caras» apagado (la caja no llega a tocar el cilindro)",
                [("ref1", cara(rcaja, (0, -1, 0))), ("ref2", curva(rcil, "cilindro"))], {"tipo": "tangente", "todas_caras": False},
                "tangente_una_cara_lejos", None, rechaza="Todas las caras")
    restriccion("Tangente con «Todas las caras» apagado (la caja toca al cilindro)",
                [("ref1", cara(rtoca, (0, -1, 0))), ("ref2", curva(rcil, "cilindro"))], {"tipo": "tangente", "todas_caras": False},
                "tangente_una_cara", lambda: abs(caja(rtoca)[1] - (-100 + 8)) < 0.01 or abs(caja(rtoca)[1] - (-100 - 8)) < 0.01)


run("restricción de componentes", restricciones)


# 7. Ventana chica ---------------------------------------------------------------------------------------------------------
def chica():
    for (w, h) in ((1024, 640), (821, 520)):
        v.resize(w, h)
        A.esperar(300)
        for clave in ("union", "posicion_inicial", "vinculo_movimiento", "origen_union", "restriccion_componentes"):
            p = A.abrir(v, clave)
            if p is None:
                continue
            A.esperar(100)
            r = p.geometry()
            A.reg(AR, f"ventana {w}x{h}: el panel «{clave}» entra en el visor (Aceptar/Cancelar a la vista)", v.area.rect().contains(r), f"panel={r} área={v.area.rect()}")
            if clave == "restriccion_componentes":
                p.set_valor("tipo", "centro")
                p.set_valor("modo1", "entre_caras")
                p.set_valor("modo2", "entre_caras")
                A.esperar(100)
                A.reg(AR, f"ventana {w}x{h}: Centro con las dos segundas caras sigue entrando", v.area.rect().contains(p.geometry()), f"panel={p.geometry()}")
                A.foto(v, f"restriccion_chica_{w}x{h}")
            if clave == "union":
                p.set_valor("tipo", "planar")
                A.esperar(100)
                A.reg(AR, f"ventana {w}x{h}: la unión planar con todos sus campos sigue entrando", v.area.rect().contains(p.geometry()), f"panel={p.geometry()}")
                A.foto(v, f"ensamblar_asm_chica_{w}x{h}")
            p.cancelar()
            A.esperar(80)
        v.acciones["estudio_movimiento"].trigger()
        A.esperar(200)
        pe = getattr(v, "_panel_estudio", None)
        if pe is not None:
            A.reg(AR, f"ventana {w}x{h}: el panel del estudio cabe en la pantalla ({pe.width()}x{pe.height()})", pe.height() <= h and pe.width() <= w, "")
            pe.close()
    v.resize(1900, 1000)


run("ventana chica", chica)

A.guardar_registro("u2c_ensamblar_asm")
fallas = [r for r in A.REGISTRO if not r["ok"]]
print(f"\n=== {len(A.REGISTRO)} comprobaciones, {len(fallas)} con ✗ ===")
v.close()
sys.exit(0)

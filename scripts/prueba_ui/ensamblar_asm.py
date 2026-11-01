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


# 7. Ventana chica ---------------------------------------------------------------------------------------------------------
def chica():
    for (w, h) in ((1024, 640), (821, 520)):
        v.resize(w, h)
        A.esperar(300)
        for clave in ("union", "posicion_inicial", "vinculo_movimiento", "origen_union"):
            p = A.abrir(v, clave)
            if p is None:
                continue
            A.esperar(100)
            r = p.geometry()
            A.reg(AR, f"ventana {w}x{h}: el panel «{clave}» entra en el visor (Aceptar/Cancelar a la vista)", v.area.rect().contains(r), f"panel={r} área={v.area.rect()}")
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

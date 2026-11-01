# -*- coding: utf-8 -*-
"""Patrones de sólido (PAT-2 a PAT-5), clase de tolerancia de la rosca (CAP-14) y ENSAMBLAR bola y vínculo (ASM-11, ASM-13)
en la ventana real y como una persona: elegir con el visor, teclear en los campos, abrir «Más opciones», clic sobre las
casillas de supresión, arrastrar el disco de la ruta y las asas, elegir en los desplegables, Aceptar, reabrir, deshacer.
Mide posiciones y volúmenes. Eventos simulados al visor y a los widgets del panel (nunca el cursor real)."""
import arnes as A
import numpy as np
import teclado as T
from omnicad import api
from omnicad.nucleo import geometria as geo
from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

AR = "PATRONES·ROSCA·ENSAMBLE"
s = api.Sesion()


def L(nombre, **a):
    r = api.llamar(s, nombre, a)
    assert r["ok"], (nombre, a, r)
    return r["result"]


caja = L("create_box", length=10, width=10, height=10, x=0, y=0)["bodies_created"][0]["id"]       # x -5..5, y -5..5, z 0..10
L("create_sketch", name="Ruta", plane="XY")
L("draw_line", sketch="Ruta", start_x=0, start_y=30, end_x=40, end_y=30)
eje = L("create_cylinder", radius=6.35, height=20, x=200, y=0)["bodies_created"][0]["id"]
base = L("create_box", length=100, width=100, height=10, x=-400, y=300)["bodies_created"][0]["id"]   # cara de arriba z = 10
bola = L("create_box", length=10, width=10, height=10, x=-300, y=300)["bodies_created"][0]["id"]
perno = L("create_box", length=10, width=10, height=10, x=-300, y=500)["bodies_created"][0]["id"]
L("create_component", bodies=[base], name="Base", grounded=True)
L("create_component", bodies=[bola], name="Bola")
L("create_component", bodies=[perno], name="Perno")
app, v = A.iniciar(s.doc)
v.visor.vista("iso")
v.visor.encuadrar()
A.esperar(300)


def vols():
    return {k: x[1] for k, x in A.cuerpos_resumen(v).items()}


def minimos(prefijo):
    return sorted(tuple(round(float(x), 3) for x in geo.caja_envolvente(c.forma)[0])
                  for cid, c in v.doc.estado_final.cuerpos.items() if cid.startswith(prefijo))


def centro(cid):
    a, b = geo.caja_envolvente(v.doc.estado_final.cuerpos[cid].forma)
    return (np.array(a) + np.array(b)) / 2


def elegir_combo(combo, clave):
    i = combo.findData(clave)
    QTest.keyClick(combo, Qt.Key_Home)
    for _ in range(i):
        QTest.keyClick(combo, Qt.Key_Down)
    A.esperar(60)


def raton(tipo, xy, boton=Qt.LeftButton, botones=Qt.LeftButton):
    p = QPointF(float(xy[0]), float(xy[1]))
    QApplication.sendEvent(v.visor, QMouseEvent(tipo, p, p, boton, botones, Qt.NoModifier))


def clic_vista(xy):
    raton(QEvent.MouseButtonPress, xy)
    raton(QEvent.MouseButtonRelease, xy, boton=Qt.LeftButton, botones=Qt.NoButton)
    A.esperar(80)


def arrastrar_vista(a, b, pasos=8):
    a, b = np.asarray(a, float), np.asarray(b, float)
    raton(QEvent.MouseButtonPress, a)
    for k in range(1, pasos + 1):
        raton(QEvent.MouseMove, a + (b - a) * k / pasos, boton=Qt.NoButton)
    raton(QEvent.MouseButtonRelease, b, boton=Qt.LeftButton, botones=Qt.NoButton)
    A.esperar(120)


def manip(p, tipo, clave=None):
    return next((m for m in p.manipuladores.manips if type(m).__name__ == tipo and (clave is None or m.clave == clave)), None)


def aceptar(p):
    QTest.mouseClick(p.boton_ok, Qt.LeftButton)
    A.esperar(300)


def deshacer_todo(n0):
    while A.n_ops(v) > n0:
        A.deshacer(v)


def previa(p):
    p._t_previa.stop()
    p._calcular_previa()
    A.esperar(120)


def mas_opciones(p):
    if p.seccion is not None and not p.seccion.boton.isChecked():
        QTest.mouseClick(p.seccion.boton, Qt.LeftButton)
        A.esperar(100)


# ---------------------------------------------------------------- PAT-2 y PAT-3: trayectoria
def trayectoria():
    n0, v0 = A.n_ops(v), vols()
    p = A.abrir(v, "patron_ruta")
    A.elegir(p, "cuerpos", A.hit_cuerpo(v, caja))
    A.elegir(p, "ruta", A.hit_curva(v, s, "Ruta", 0))
    T.teclear(p, "rn", "3", Qt.Key_Tab)
    T.teclear(p, "rd", "10 mm", Qt.Key_Tab)
    mas_opciones(p)
    etiqueta = next(e[2] for e in A.etiquetas(p) if e[0] == "inicio")
    A.reg(AR + " · trayectoria", "PAT-2: el campo del inicio dice «Punto de inicio (%)» y se ve en «Más opciones»",
          etiqueta == "Punto de inicio (%)" and p.widgets["inicio"].isVisible(), etiqueta)
    T.teclear(p, "inicio", "25", Qt.Key_Tab)
    previa(p)
    disco = manip(p, "AsaRuta", "inicio")
    pos = disco.asa(p.manipuladores) if disco else None
    A.reg(AR + " · trayectoria", "PAT-2: 25 % de la ruta de 40 mm deja el disco en x = 10 y la receta guarda 0.25",
          pos is not None and np.allclose(pos, (10, 30, 0), atol=1e-3) and p.ultima_op.p["inicio"] == "0.25", str(pos))
    gm = p.manipuladores
    xy, ok = gm.pantalla([(10.0, 30.0, 0.0), (30.0, 30.0, 0.0)])
    if ok.all():
        arrastrar_vista(xy[0], xy[1])
    previa(p)
    A.reg(AR + " · trayectoria", "PAT-2: arrastrar el disco con el ratón hasta el 75 % escribe un porcentaje en el campo",
          abs(float(p.valores["inicio"]) - 75) < 5, str(p.valores["inicio"]))
    T.teclear(p, "inicio", "0", Qt.Key_Tab)
    previa(p)
    # PAT-3: casillas y silueta de la copia suprimida
    casilla = p.widgets["ver_casillas"]
    QTest.mouseClick(casilla, Qt.LeftButton, pos=QPoint(6, max(casilla.height() // 2, 6)))
    A.esperar(120)
    cas = manip(p, "CasillasCopias")
    A.reg(AR + " · trayectoria", "PAT-3: con «Elegir copias a suprimir» hay una casilla por instancia (3)",
          cas is not None and len(cas.items) == 3, str(None if cas is None else len(cas.items)))
    if cas is not None:
        punto = next(pt for ident, pt, _e in cas.items if ident == 1)
        xy, ok = gm.pantalla([punto])
        if ok.all():
            clic_vista(xy[0])
        previa(p)
        prims = p.comando.previa_vista(p.ctx, p.valores, p.ultima_op) or []
        A.reg(AR + " · trayectoria", "PAT-3: la copia suprimida se ve como una silueta roja en la vista",
              p.valores.get("suprimir") == "1" and len(prims) == 1 and prims[0][2] == (0.88, 0.18, 0.15), str(p.valores.get("suprimir")))
        A.foto(v, "patron_ruta_inicio_porcentaje")
    aceptar(p)
    nuevos = [k for k in vols() if k not in v0]
    A.reg(AR + " · trayectoria", "Aceptar crea una sola copia: la del paso 2 (x = 10, el paso 1 quedó suprimido)",
          len(nuevos) == 1 and abs(minimos(v.doc.operaciones[-1].id)[0][0] - 5.0) < 1e-3, str(minimos(v.doc.operaciones[-1].id)))
    deshacer_todo(n0)


# ---------------------------------------------------------------- PAT-5: plano de referencia de la dirección 2
def plano_dir2():
    n0 = A.n_ops(v)
    p = A.abrir(v, "patron_rectangular_3d")
    A.elegir(p, "cuerpos", A.hit_cuerpo(v, caja))
    A.elegir(p, "dir1", A.hit_eje(v, "X"))
    p.set_valor("distribucion", "espaciado")
    T.teclear(p, "n1", "2", Qt.Key_Tab)
    T.teclear(p, "d1", "30 mm", Qt.Key_Tab)
    T.teclear(p, "n2", "2", Qt.Key_Tab)
    T.teclear(p, "d2", "25 mm", Qt.Key_Tab)
    A.reg(AR + " · plano dir. 2", "PAT-5: con la cantidad 2 > 1 y sin dirección 2 aparece «Plano de referencia»",
          p.widgets["plano_dir2"].isVisible(), "")
    previa(p)
    from omnicad.ui.comandos.crear import direccion_derivada
    d = np.round(direccion_derivada(p.ctx, p.valores), 6) + 0.0
    A.reg(AR + " · plano dir. 2", "sin plano la dirección 2 derivada va por +Y", np.allclose(d, (0, 1, 0)), str(d))
    A.elegir(p, "plano_dir2", A.hit_plano(v, "XZ"))
    previa(p)
    d = np.round(direccion_derivada(p.ctx, p.valores), 6) + 0.0
    A.reg(AR + " · plano dir. 2", "elegir el plano XZ lleva la dirección 2 a Z, el panel lo dice y la flecha verde la sigue",
          "dentro del plano elegido" in p.widgets["info_dir2"].text() and np.allclose(d, (0, 0, 1))
          and np.allclose(manip(p, "Flecha", "d2").direccion, (0, 0, 1)), p.widgets["info_dir2"].text())
    A.elegir(p, "plano_dir2", A.hit_plano(v, "YZ"))
    previa(p)
    A.reg(AR + " · plano dir. 2", "un plano perpendicular a la dirección 1 se rechaza con un mensaje que lo explica",
          not p._previa_ok and "perpendicular al plano" in p.widgets["info_dir2"].text(), p.widgets["info_dir2"].text()[:80])
    A.elegir(p, "plano_dir2", A.hit_plano(v, "XZ"))
    previa(p)
    aceptar(p)
    A.reg(AR + " · plano dir. 2", "Aceptar guarda plano_dir2 en el paso y deshacer lo quita",
          v.doc.operaciones[-1].p["plano_dir2"] == {"tipo": "plano", "id": "XZ"} and A.n_ops(v) == n0 + 1, "")
    deshacer_todo(n0)


# ---------------------------------------------------------------- PAT-4: Multitransformación
def multi():
    n0, v0 = A.n_ops(v), vols()
    p = A.abrir(v, "multitransformar")
    A.elegir(p, "cuerpos", A.hit_cuerpo(v, caja))
    A.elegir(p, "t_dir1", A.hit_eje(v, "X"))
    p.set_valor("t_distribucion", "espaciado")
    T.teclear(p, "t_n1", "3", Qt.Key_Tab)
    T.teclear(p, "t_d1", "30 mm", Qt.Key_Tab)
    lista = p.widgets["lista"]
    lista.agregar.menu().actions()[4].trigger()                            # 2.ª transformación: Simetría
    A.esperar(100)
    A.elegir(p, "t_plano", A.hit_plano(v, "YZ"))
    previa(p)
    A.reg(AR + " · multi", "con la última etapa elegida no hay siluetas extra (es el resultado completo)",
          p._previa_ok and not p.comando.previa_vista(p.ctx, p.valores, p.ultima_op), p.mensaje.text()[:60])
    QTest.keyClick(lista.lista, Qt.Key_Up)                                 # elegir la 1.ª: el patrón de 3
    A.esperar(120)
    previa(p)
    prims = p.comando.previa_vista(p.ctx, p.valores, p.ultima_op) or []
    A.reg(AR + " · multi", "PAT-4: con la 1.ª etapa elegida el panel dice «quedan 3 instancias» y las siluetas azules son 2",
          "Hasta esta etapa quedan 3 instancias" in p.widgets["etapa"].text() and len(prims) == 2, p.widgets["etapa"].text()[-60:])
    asa = manip(p, "AsaCantidad", "t_n1")
    A.reg(AR + " · multi", "PAT-4: la vista muestra las asas de la transformación elegida (cantidad y distancia)",
          asa is not None and manip(p, "Flecha", "t_d1") is not None, str([m.ident for m in p.manipuladores.manips]))
    if asa is not None:
        gm = p.manipuladores
        a, _pt, t = asa._asa(gm)
        xy, ok = gm.pantalla([a, a + t * asa.paso])
        if ok.all():
            arrastrar_vista(xy[0], xy[1])
        A.reg(AR + " · multi", "tirar del asa de cantidad escribe en el campo de la etapa (t_n1 = 4)", p.valores["t_n1"] == 4,
              str(p.valores["t_n1"]))
    A.foto(v, "multitransformar_hasta_etapa")
    previa(p)
    aceptar(p)
    op = v.doc.operaciones[-1]
    A.reg(AR + " · multi", "Aceptar crea 7 copias (4 × 2 − el original) y guarda n1 = 4",
          op.p["transformaciones"][0]["n1"] == 4 and len([k for k in vols() if k not in v0]) == 7,
          str(op.p["transformaciones"][0].get("n1")))
    deshacer_todo(n0)


# ---------------------------------------------------------------- CAP-14: clase de la rosca ACME
def rosca():
    n0 = A.n_ops(v)
    resultados = {}
    for clase in ("2G", "4G"):
        p = A.abrir(v, "rosca")
        A.elegir(p, "caras", A.hit_cara(v, eje, normal=None))
        A.esperar()
        p.set_valores({"tipo_rosca": "acme", "tam_acme": "1/2", "des_tipo_rosca": "1/2-10 ACME"})
        p.widgets["modelada"].click()
        A.esperar(150)
        combo = p.widgets["clase_acme"]
        opciones = [combo.itemData(i) for i in range(combo.count())]
        if clase == "2G":
            A.reg(AR + " · rosca", "CAP-14: ACME ofrece Automática, Sin clase y 2G, 3G, 4G",
                  opciones == ["auto", "", "2G", "3G", "4G"], str(opciones))
        elegir_combo(combo, clase)
        T.teclear(p, "longitud", "8 mm", Qt.Key_Tab) if "longitud" in p.widgets and p.widgets["longitud"].isVisible() else None
        previa(p)
        aceptar(p)
        resultados[clase] = vols()[eje]
        A.reg(AR + " · rosca", f"ACME clase {clase}: el paso guarda la clase", v.doc.operaciones[-1].p["clase_rosca"] == clase,
              str(v.doc.operaciones[-1].p.get("clase_rosca")))
        A.deshacer(v)
    A.reg(AR + " · rosca", "la 4G (Ø de flancos mayor) saca menos material que la 2G",
          resultados["4G"] > resultados["2G"] + 1.0, str(resultados))
    deshacer_todo(n0)


# ---------------------------------------------------------------- ASM-11: Pitch y Yaw de la bola
def bola_pitch_yaw():
    n0 = A.n_ops(v)
    p = A.abrir(v, "union")
    A.elegir(p, "origen1", A.hit_cara(v, bola, normal=(0, 0, -1)))
    A.elegir(p, "origen2", A.hit_cara(v, base, normal=(0, 0, 1)))
    p.set_valor("tipo", "bola")
    A.esperar(120)
    A.reg(AR + " · bola", "ASM-11: con una bola aparecen «Eje de cabeceo (Pitch)» y «Eje de guiñada (Yaw)»",
          p.widgets["eje_cabeceo"].isVisible() and p.widgets["eje_guinada"].isVisible(), "")
    elegir_combo(p.widgets["eje_cabeceo"], "X")
    elegir_combo(p.widgets["eje_guinada"], "Z")
    T.teclear(p, "giro2", "90", Qt.Key_Tab)
    previa(p)
    aceptar(p)
    c = centro(bola)
    A.reg(AR + " · bola", "Pitch = X y 90°: el cubo (5 mm sobre el origen de la unión) pasa a 5 mm al costado, y = 295",
          np.allclose(c, (-400, 295, 10), atol=1e-2), str(np.round(c, 3)))
    union = next(j for j in api.llamar(s, "get_assembly", {})["result"]["joints"] if j["type"] == "ball")
    A.reg(AR + " · bola", "la unión guarda los ejes (pitch_axis X, yaw_axis Z)", (union["pitch_axis"], union["yaw_axis"]) == ("X", "Z"),
          str((union.get("pitch_axis"), union.get("yaw_axis"))))
    v.editar_operacion(union["id"])
    A.esperar(250)
    pe = v.panel
    A.reg(AR + " · bola", "reabrir la unión muestra Pitch X y Yaw Z",
          pe is not None and (pe.valores.get("eje_cabeceo"), pe.valores.get("eje_guinada")) == ("X", "Z"),
          str(None if pe is None else (pe.valores.get("eje_cabeceo"), pe.valores.get("eje_guinada"))))
    if pe is not None:
        elegir_combo(pe.widgets["eje_guinada"], "X")                       # Yaw igual que Pitch: paralelos
        previa(pe)
        A.reg(AR + " · bola", "Pitch y Yaw paralelos: la vista previa falla diciendo que son paralelos",
              not pe._previa_ok and "paralelos" in pe.mensaje.text(), pe.mensaje.text()[:80])
        pe.cancelar()
        A.esperar(150)
    deshacer_todo(n0)


# ---------------------------------------------------------------- ASM-13: vínculo entre dos movimientos de la misma unión
def vinculo_misma_union():
    n0 = A.n_ops(v)
    aux = L("create_box", length=10, width=10, height=10, x=-300, y=700)["bodies_created"][0]["id"]
    L("create_component", bodies=[aux], name="Aux")
    L("create_joint", origin1="<Z", body1=perno, origin2=">Z", body2=base, joint_type="cylindrical", name="Tornillo")
    L("create_joint", origin1="<Z", body1=aux, origin2=">Z", body2=base, joint_type="slider", name="Deslizante")     # el diálogo pide dos uniones
    j = next(x for x in api.llamar(s, "get_assembly", {})["result"]["joints"] if x["name"] == "Tornillo")
    p = A.abrir(v, "vinculo_movimiento")
    p.set_valor("union1", j["id"])
    p.set_valor("union2", j["id"])
    A.esperar(100)
    previa(p)
    A.reg(AR + " · vínculo", "ASM-13: la misma unión con los dos movimientos «Automático» se rechaza y se explica",
          not p._previa_ok and "movimientos distintos" in p.mensaje.text(), p.mensaje.text()[:90])
    p.set_valor("mov1", "giro")
    p.set_valor("mov2", "desliz")
    T.teclear(p, "factor", "0,5", Qt.Key_Tab)
    previa(p)
    A.reg(AR + " · vínculo", "con Giro → Deslizamiento de la misma unión la vista previa anda", p._previa_ok, p.mensaje.text()[:80])
    boton = p.widgets["animar"]
    QTest.mouseClick(boton, Qt.LeftButton)
    A.esperar(400)
    anda = getattr(v, "_t_vinculo", None) is not None and v._t_vinculo.isActive()
    A.reg(AR + " · vínculo", "«Animar» anda también con la misma unión (el dibujo se mueve)", anda and bool(v.visor.transformaciones),
          f"transformaciones={len(v.visor.transformaciones)}")
    QTest.mouseClick(boton, Qt.LeftButton)
    A.esperar(150)
    aceptar(p)
    vin = api.llamar(s, "get_assembly", {})["result"]["motion_links"]
    A.reg(AR + " · vínculo", "se crea el vínculo giro → deslizamiento con relación 0,5",
          len(vin) == 1 and (vin[0]["motion1"], vin[0]["motion2"]) == ("rotation", "slide"), str(vin))
    z0 = centro(perno)[2]
    L("drive_joint", joint="Tornillo", rotation=90)
    A.esperar(200)
    A.reg(AR + " · vínculo", "accionar el giro 90° sube el perno 45 mm (como un tornillo)",
          abs(centro(perno)[2] - z0 - 45) < 1e-2, f"{centro(perno)[2] - z0:.3f}")
    deshacer_todo(n0)


for nombre, f in (("trayectoria", trayectoria), ("plano dirección 2", plano_dir2), ("multitransformación", multi),
                  ("rosca con clase", rosca), ("bola", bola_pitch_yaw), ("vínculo", vinculo_misma_union)):
    A.correr(f"{AR} · {nombre}", f)

A.reg(AR, "no se escapó ninguna excepción dentro de un slot de Qt", not A.ERRORES, "; ".join(A.ERRORES)[:300])
A.guardar_registro("patrones_ensamble_rosca")
fallas = sum(1 for r in A.REGISTRO if not r["ok"])
print(f"=== {len(A.REGISTRO)} comprobaciones, {fallas} con ✗", flush=True)

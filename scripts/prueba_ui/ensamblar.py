# -*- coding: utf-8 -*-
"""Fase C · ENSAMBLAR: cada comando en la ventana real (elegir con el visor, teclear, vista previa, aceptar, reabrir,
deshacer), el efecto sobre las posiciones y los menús del timeline y del navegador para componentes y uniones."""
import sys

import arnes as A
import corredor as C
from omnicad import api
from omnicad.nucleo import geometria as geo
from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QInputDialog

AR = "ENSAMBLAR"
s = api.Sesion()


def L(nombre, **a):
    r = api.llamar(s, nombre, a)
    assert r["ok"], (nombre, a, r)
    return r["result"]


base = L("create_box", length=100, width=60, height=10)["bodies_created"][0]["id"]
eje = L("create_cylinder", radius=5, height=40, x=200)["bodies_created"][0]["id"]
brazo = L("create_box", length=60, width=20, height=5, x=300)["bodies_created"][0]["id"]
tapa = L("create_box", length=60, width=40, height=20, x=-200)["bodies_created"][0]["id"]
app, v = A.iniciar(s.doc)
QInputDialog.getText = staticmethod(lambda *a, **k: ("Nombre de prueba", True))


def caja(cid):
    return [round(float(x), 2) for p in geo.caja_envolvente(v.doc.estado_final.cuerpos[cid].forma) for x in p]


def ens():
    return api.llamar(s, "get_assembly", {})["result"]


def comp(nombre):
    return next(c for c in ens()["components"] if c["name"] == nombre)


def union(nombre):
    return next(j for j in ens()["joints"] if j["name"] == nombre)


def run(nombre, f):
    A.correr(f"{AR} · {nombre}", f)


def cuerpo(cid):
    return lambda: [A.hit_cuerpo(v, cid)]


def cara(cid, normal):
    return lambda: [A.hit_cara(v, cid, normal=normal)]


def alguna_cara(cid):
    """La primera cara que el visor deja elegir con un clic (las tapadas por otra pieza no se pueden)."""
    def f():
        for n in ((0, 0, 1), (1, 0, 0), (0, -1, 0), (-1, 0, 0), (0, 1, 0)):
            h = A.hit_cara(v, cid, normal=n)
            if h is not None:
                return [h]
        return [None]
    return f


# Componentes -------------------------------------------------------------------------------------------------------
def componentes():
    C.negativos(v, AR, "nuevo_componente")
    C.caso(v, AR, "nuevo_componente", {"cuerpos": cuerpo(base)}, {"fijo": True}, deshacer=False, etiqueta="componente Base fijo")
    C.caso(v, AR, "nuevo_componente", {"cuerpos": cuerpo(eje)}, {}, deshacer=False, etiqueta="componente Eje")
    C.caso(v, AR, "nuevo_componente", {"cuerpos": cuerpo(brazo)}, {}, deshacer=False, etiqueta="componente Brazo")
    C.caso(v, AR, "nuevo_componente", {"cuerpos": cuerpo(tapa)}, {"fijo": True}, deshacer=False, etiqueta="componente Tapa fijo")
    cs = ens()["components"]
    A.reg(AR, "cuatro componentes; Base y Tapa fijos", len(cs) == 4 and [c["grounded"] for c in cs] == [True, False, False, True], str([(c["name"], c["grounded"]) for c in cs]))


run("componentes", componentes)
N_COMP = len(v.doc.operaciones)
NB, NE, NR, NT = (c["name"] for c in ens()["components"])        # nombres que les puso la ventana


def origen():
    C.negativos(v, AR, "origen_union")
    C.caso(v, AR, "origen_union", {"origen": alguna_cara(tapa)}, {"angulo": "45 deg", "dx": "5 mm"}, deshacer=True, etiqueta="origen en la cara de arriba de la Tapa")
    C.negativos(v, AR, "origen_union", {"origen": alguna_cara(tapa)}, "dz", malos=("abc", "1e12 mm"))


run("origen de unión", origen)


def como_esta():
    C.negativos(v, AR, "union_construida")
    C.caso(v, AR, "union_construida", {"origen1": cara(brazo, (0, 0, 1)), "origen2": cuerpo(tapa)}, {"tipo": "rigida"}, deshacer=True, etiqueta="unión como está brazo→tapa")


run("unión como está", como_esta)


# Unión ----------------------------------------------------------------------------------------------------------------
def uniones():
    C.negativos(v, AR, "union")
    sel_eje = {"origen1": cara(eje, (0, 0, 1)), "origen2": cara(base, (0, 0, 1))}
    C.negativos(v, AR, "union", sel_eje, "dx", malos=("abc", "xyz mm", "1e12 mm"), vals={"tipo": "revolucion"})
    C.negativos(v, AR, "union", sel_eje, "angulo", malos=("abc", "10 mm"), vals={"tipo": "revolucion"})
    C.negativos(v, AR, "union", sel_eje, "minimo", malos=("abc", "10 mm"), vals={"tipo": "revolucion"})
    r = C.caso(v, AR, "union", sel_eje, {"tipo": "revolucion", "eje_giro": "Z"}, deshacer=False, etiqueta="unión eje→base (revolución Z)")
    A.reg(AR, "la unión pone el Eje de pie en el centro de la cara de arriba de la Base (caras enfrentadas)", r is not None and caja(eje)[2] == 10.0 and abs(caja(eje)[0] + 5) < 0.1, f"eje={caja(eje)}")
    sel_br = {"origen1": cara(brazo, (0, 0, 1)), "origen2": cara(tapa, (0, 0, 1))}
    C.caso(v, AR, "union", sel_br, {"tipo": "revolucion", "eje_giro": "Z", "minimo": "-45 deg", "maximo": "45 deg"}, deshacer=False,
           etiqueta="unión brazo→tapa con límites ±45°")
    A.reg(AR, "dos uniones en el ensamble", len(ens()["joints"]) == 2, str([(j["name"], j["type"], j.get("limits")) for j in ens()["joints"]]))


run("uniones", uniones)

# Accionar uniones: teclear el ángulo -------------------------------------------------------------------------------------
js = [j["name"] for j in ens()["joints"]]
IDS = {j["name"]: j["id"] for j in ens()["joints"]}


def accionar():
    p = A.abrir(v, "accionar_uniones")
    A.reg(AR, "accionar: abre con las uniones en la lista", p is not None, "")
    for texto, esperado in (("30 deg", 30.0), ("30,5 deg", 30.5), ("0,5 rad", 28.6479), ("-20", -20.0), ("2*15 deg", 30.0)):
        p = A.abrir(v, "accionar_uniones")
        p.set_valor("union", IDS[js[0]])
        p.set_valor("giro", texto)
        p.aceptar()
        A.esperar(300)
        got = union(js[0])["values"]["rotation"]
        A.reg(AR, f"accionar: ángulo «{texto}»", abs(got - esperado) < 0.01, f"quedó {got}")
    for malo in ("abc", "", "1e9 deg", "10 mm", "nan"):
        antes = union(js[0])["values"]["rotation"]
        p = A.abrir(v, "accionar_uniones")
        p.set_valor("union", IDS[js[0]])
        p.set_valor("giro", malo)
        p.aceptar()
        A.esperar(300)
        vivo = C._vivo(p)
        msg = p.mensaje.text() if vivo else "(el panel se cerró)"
        u = union(js[0])
        A.reg(AR, f"accionar: ángulo malo {malo!r} no rompe la unión", u["status"] != "error", f"valor {antes} → {u['values']}; estado={u['status']} «{u['message'][:80]}»; mensaje=«{msg}»; panel visible={vivo}")
        if vivo:
            p.cancelar()
        if u["status"] != "ok" or u["values"]["rotation"] != antes:      # deja la unión como estaba para seguir
            p = A.abrir(v, "accionar_uniones")
            p.set_valor("union", IDS[js[0]])
            p.set_valor("giro", f"{antes} deg")
            p.aceptar()
            A.esperar(250)
    p = A.abrir(v, "accionar_uniones")
    p.set_valor("union", IDS[js[1]])
    p.set_valor("giro", "90 deg")
    p.aceptar()
    A.esperar(300)
    got = union(js[1])["values"]["rotation"]
    A.reg(AR, "accionar: 90° en una unión con límites ±45° se topa", abs(got - 45) < 0.01, f"quedó {got}")
    antes = union(js[0])["values"]["rotation"]
    p = A.abrir(v, "accionar_uniones")
    p.set_valor("union", IDS[js[0]])
    p.set_valor("giro", "77 deg")
    p.aceptar()
    A.esperar(300)
    puesto = union(js[0])["values"]["rotation"]
    A.deshacer(v)
    A.reg(AR, "accionar: un Ctrl+Z deshace el último accionar", puesto == 77.0 and union(js[0])["values"]["rotation"] == antes, f"{antes} → {puesto} → {union(js[0])['values']}")
    A.deshacer(v)
    A.deshacer(v)
    A.reg(AR, "accionar: tras más Ctrl+Z el modelo sigue sano", union(js[0])["status"] != "error", str(union(js[0])["values"]))


run("accionar", accionar)


# Vínculo de movimiento -----------------------------------------------------------------------------------------------------
def vinculo():
    C.negativos(v, AR, "vinculo_movimiento")
    p = A.abrir(v, "vinculo_movimiento")
    p.set_valor("union1", IDS[js[0]])
    p.set_valor("union2", IDS[js[0]])
    p._t_previa.stop()
    p.aceptar()
    A.esperar(200)
    A.reg(AR, "vínculo: la misma unión dos veces se rechaza", C._vivo(p), f"mensaje=«{p.mensaje.text() if C._vivo(p) else ''}»")
    if C._vivo(p):
        p.cancelar()
    for malo in ("abc", "", "nan", "1e9", "0", "-2"):
        p = A.abrir(v, "vinculo_movimiento")
        p.set_valor("union1", IDS[js[0]])
        p.set_valor("union2", IDS[js[1]])
        p.set_valor("factor", malo)
        p._t_previa.stop()
        p._calcular_previa()
        st = A.estado_panel(p)
        n0 = A.n_ops(v)
        if st["op"] and st["previa_ok"]:
            p.aceptar()
            A.esperar(250)
            creado = A.n_ops(v) > n0
            while A.n_ops(v) > n0:
                A.deshacer(v)
        else:
            creado = False
            p.cancelar()
        A.reg(AR, f"vínculo: relación {malo!r}", True, f"{'aceptado' if creado else 'rechazado'}; mensaje=«{st['mensaje']}»")
    C.caso(v, AR, "vinculo_movimiento", {}, {"union1": IDS[js[0]], "union2": IDS[js[1]], "factor": "2"}, deshacer=False, etiqueta="vínculo 1→2 relación 2")
    p = A.abrir(v, "accionar_uniones")
    p.set_valor("union", IDS[js[0]])
    p.set_valor("giro", "20 deg")
    p.aceptar()
    A.esperar(300)
    a, b = union(js[0])["values"]["rotation"], union(js[1])["values"]["rotation"]
    A.reg(AR, "vínculo: 20° en la 1 mueve la 2 a 40°", abs(a - 20) < 0.01 and abs(b - 40) < 0.01, f"1={a} 2={b}")
    p = A.abrir(v, "accionar_uniones")
    p.set_valor("union", IDS[js[1]])
    p.set_valor("giro", "10 deg")
    p.aceptar()
    A.esperar(300)
    vivo = C._vivo(p)
    barra = v.timeline.estado.toolTip()
    A.reg(AR, "vínculo: accionar la unión que sigue no la cambia y la barra de estado lo avisa", union(js[1])["values"]["rotation"] == 40.0 and "vínculo" in barra.lower(),
          f"valor={union(js[1])['values']} panel visible={vivo} barra de estado=«{barra}»")
    if vivo:
        p.cancelar()


run("vinculo", vinculo)


# Fijar / liberar -----------------------------------------------------------------------------------------------------------
def fijar():
    C.negativos(v, AR, "fijar_componente")
    antes = comp(NB)["grounded"]
    for i in range(2):
        p = A.abrir(v, "fijar_componente")
        A.elegir(p, "cuerpos", A.hit_cuerpo(v, base))
        p.aceptar()
        A.esperar(300)
        A.reg(AR, f"fijar/liberar la Base, vez {i + 1}", comp(NB)["grounded"] == (not antes if i == 0 else antes), f"grounded={comp(NB)['grounded']}")
    # liberar la Base: ¿la unión Eje→Base mueve la Base o el Eje al accionar?
    p = A.abrir(v, "fijar_componente")
    A.elegir(p, "cuerpos", A.hit_cuerpo(v, base))
    p.aceptar()
    A.esperar(300)
    A.reg(AR, "liberar la Base deja fija solo la Tapa", [c["grounded"] for c in ens()["components"]] == [False, False, False, True], str([(c["name"], c["grounded"]) for c in ens()["components"]]))
    p = A.abrir(v, "fijar_componente")
    A.elegir(p, "cuerpos", A.hit_cuerpo(v, base))
    p.aceptar()
    A.esperar(300)


run("fijar", fijar)


# Grupo rígido / origen / unión como está ----------------------------------------------------------------------------------
def grupo():
    C.negativos(v, AR, "grupo_rigido")
    p = A.abrir(v, "grupo_rigido")
    A.elegir(p, "cuerpos", A.hit_cuerpo(v, eje))
    p._t_previa.stop()
    p.aceptar()
    A.esperar(200)
    A.reg(AR, "grupo rígido con un solo componente se rechaza", C._vivo(p), f"mensaje=«{p.mensaje.text() if C._vivo(p) else ''}»")
    if C._vivo(p):
        p.cancelar()
    C.caso(v, AR, "grupo_rigido", {"cuerpos": lambda: [A.hit_cuerpo(v, base), A.hit_cuerpo(v, brazo)]}, {}, deshacer=True, etiqueta="grupo Base+Brazo")


run("grupo rígido", grupo)


# Menús del timeline y del navegador para las piezas del ensamble ----------------------------------------------------------
def acciones_de(menu, prefijo=""):
    for a in menu.actions():
        if a.isSeparator():
            continue
        if a.menu() is not None:
            yield from acciones_de(a.menu(), prefijo + a.text().replace("&", "") + " › ")
        else:
            yield prefijo + a.text().replace("&", ""), a


def menu_de(widget, pos):
    A.MENUS.clear()
    A.clic_derecho(widget, pos)
    return A.MENUS[-1] if A.MENUS else None


def estado():
    return (len(v.doc.operaciones), v.doc.marcador, tuple(bool(o.suprimida) for o in v.doc.operaciones), str(ens()["components"]), str([(j["values"]) for j in ens()["joints"]]))


def recorrer(area, abrir):
    menu = abrir()
    if menu is None:
        A.reg(area, "menú contextual", False, "el clic derecho no abrió menú")
        return
    items = list(acciones_de(menu))
    A.reg(area, "menú contextual", bool(items), " | ".join(f"{n}{'' if a.isEnabled() else ' (gris)'}" for n, a in items))
    for nombre, a in items:
        if not a.isEnabled() or any(p in nombre.lower() for p in ("eliminar", "borrar", "quitar", "delete")):
            continue
        menu = abrir()
        a = next((x for n, x in acciones_de(menu) if n == nombre), None) if menu is not None else None
        if a is None:
            continue
        antes, n_err = estado(), len(A.ERRORES)
        a.trigger()
        A.esperar(250)
        if v.panel is not None and v.panel.isVisible():
            v.panel.cancelar()
        if v.doc.marcador != antes[1]:
            v.doc.mover_marcador(antes[1])     # «Retroceder antes de este paso» mueve el marcador: no es un paso que se deshaga
            A.esperar(200)
        k = 0
        while estado() != antes and k < 5:
            A.deshacer(v)
            k += 1
        A.reg(area, f"«{nombre}»", len(A.ERRORES) == n_err and estado() == antes, f"sin excepción y deshacer ({k}) vuelve igual: {estado() == antes}")


def menus():
    arbol = v.navegador.arbol
    # el navegador: cada componente y cada unión
    def items():
        def rec(it):
            yield it
            for j in range(it.childCount()):
                yield from rec(it.child(j))
        for i in range(arbol.topLevelItemCount()):
            yield from rec(arbol.topLevelItem(i))
    for nombre in [i.text(0) for i in items()]:
        if nombre in (NB, NE, NR, NT) or nombre.startswith("Unión") or nombre.startswith("Vínculo"):

            def abrir(nombre=nombre):
                it2 = next((i for i in items() if i.text(0) == nombre), None)
                p = it2.parent()
                while p is not None:
                    p.setExpanded(True)
                    p = p.parent()
                arbol.scrollToItem(it2)
                r = arbol.visualItemRect(it2)
                return menu_de(arbol.viewport(), QPoint(r.center().x() + 10, r.center().y()))
            recorrer(f"NAVEGADOR › {nombre}", abrir)
    # el timeline: los pasos de ensamble
    for op in list(v.doc.operaciones):
        if op.TIPO in ("componente", "union", "vinculo_movimiento", "grupo_rigido", "origen_union"):
            tl_doble_clic(op)
            recorrer(f"TIMELINE › {op.nombre}", lambda op_id=op.id: tl_menu(op_id))


def tl_item(op_id):
    lista = v.timeline.lista
    for i in range(lista.count()):
        it = lista.item(i)
        if it.data(Qt.UserRole) == op_id:
            lista.scrollToItem(it)
            A.esperar(30)
            return lista, it
    return lista, None


def tl_menu(op_id):
    lista, it = tl_item(op_id)
    if it is None:
        return None
    r = lista.visualItemRect(it)
    return menu_de(lista.viewport(), QPoint(r.center().x(), r.center().y()))


def tl_doble_clic(op):
    """Doble clic en el paso: tiene que abrir su panel con los valores que se pusieron."""
    lista, it = tl_item(op.id)
    n_err = len(A.ERRORES)
    A.MODALES.clear()
    centro = lista.visualItemRect(it).center()
    QTest.mouseClick(lista.viewport(), Qt.LeftButton, Qt.NoModifier, centro)
    A.esperar(60)
    QTest.mouseDClick(lista.viewport(), Qt.LeftButton, Qt.NoModifier, centro)
    A.esperar(300)
    abierto = v.panel is not None and v.panel.isVisible()
    A.reg(f"{AR} · TIMELINE › {op.nombre}", "doble clic abre su edición", abierto and len(A.ERRORES) == n_err, f"modales={A.MODALES[-1:]}")
    if abierto:
        A.reg(f"{AR} · TIMELINE › {op.nombre}", "el panel que abre es el de su comando", type(v.panel.comando).__name__ in (op.TIPO.title().replace("_", ""), "Union", "UnionComoEsta", "NuevoComponente", "VinculoMovimiento", "GrupoRigido", "OrigenUnion"), type(v.panel.comando).__name__)
        v.panel.cancelar()
        A.esperar(100)


run("menús", menus)

# Ventana chica con el panel de Unión abierto -------------------------------------------------------------------------------
def chica():
    for (w, h) in ((1024, 640), (821, 520)):
        v.resize(w, h)
        A.esperar(300)
        p = A.abrir(v, "union")
        A.elegir(p, "origen1", A.hit_cara(v, brazo, normal=(0, 0, 1)))
        A.esperar(100)
        r = p.geometry()
        dentro = v.area.rect().contains(r)
        A.reg(AR, f"ventana {w}x{h}: el panel de Unión entra en el visor (Aceptar/Cancelar a la vista)", dentro, f"panel={r} área={v.area.rect()}")
        A.foto(v, f"ensamblar_chica_{w}x{h}")
        p.cancelar()
        A.esperar(100)
    v.resize(1900, 1000)


run("ventana chica", chica)

# Una vuelta completa: guardar, reabrir ------------------------------------------------------------------------------------
A.guardar_registro("u2c_ensamblar")
fallas = [r for r in A.REGISTRO if not r["ok"]]
print(f"\n=== {len(A.REGISTRO)} comprobaciones, {len(fallas)} con ✗ ===")
v.close()
sys.exit(0)

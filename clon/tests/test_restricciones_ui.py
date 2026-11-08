# -*- coding: utf-8 -*-
"""Restricciones del boceto en el Lienzo (offscreen, eventos simulados): lo que sobra se rechaza con un mensaje, lo que
choca no entra, H/V sobre varias líneas es UN paso de deshacer, el menú del símbolo y el menú RESTRICCIONES de la cinta."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, Qt  # noqa: E402
from PySide6.QtGui import QMouseEvent  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from omnicad import api  # noqa: E402
from omnicad.restricciones import Boceto  # noqa: E402
from omnicad.timeline.parametros import TablaParametros  # noqa: E402
from omnicad.ui import editor_boceto, iconos  # noqa: E402
from omnicad.ui.cinta_boceto import GRUPOS_BOCETO  # noqa: E402


@pytest.fixture
def lz():
    app = QApplication.instance() or QApplication([])
    lienzo = editor_boceto.Lienzo(Boceto(), TablaParametros().evaluar)
    lienzo.resize(800, 600)
    lienzo.show()
    lienzo.mensajes = []
    lienzo.mensaje.connect(lienzo.mensajes.append)
    yield lienzo
    lienzo.close()
    lienzo.deleteLater()
    app.processEvents()


def _linea_inclinada(lz, y=30):
    a, c = lz.b.agregar_punto(40, y), lz.b.agregar_punto(70, y + 9)
    lz.resolver()
    return lz.b.agregar_linea(a, c)


def _clic(lz, x, y, mods=Qt.NoModifier):
    """Movimiento, presión y suelta al widget, sin mover el cursor real."""
    pos = lz.a_px(x, y)
    for tipo, boton, botones in ((QEvent.MouseMove, Qt.NoButton, Qt.NoButton),
                                 (QEvent.MouseButtonPress, Qt.LeftButton, Qt.LeftButton),
                                 (QEvent.MouseButtonRelease, Qt.LeftButton, Qt.NoButton)):
        QApplication.sendEvent(lz, QMouseEvent(tipo, pos, pos, boton, botones, mods))


@pytest.mark.parametrize("origen_primero", [False, True])
@pytest.mark.parametrize("materializado", [False, True])
@pytest.mark.parametrize("sobre_curva", [False, True])
def test_b223_coincidente_punto_sobre_diagonal_con_origen(lz, origen_primero, materializado, sobre_curva):
    """Recorrido del video: rectángulo, diagonal, Punto sobre la curva y dos clics Coincidente."""
    lz.centro = [-50, 0]
    lz.ajustar_grilla = False
    lz.set_herramienta("rectangulo")
    _clic(lz, -120, 0)
    _clic(lz, -55, 50)
    esquinas = list(lz.b.puntos)
    lz.set_herramienta("linea")
    lz.alternar_construccion()
    _clic(lz, -120, 0)
    _clic(lz, -55, 50)
    diagonal = lz._ultima_linea
    lz.set_herramienta("punto")
    _clic(lz, -87.5, 25, Qt.ShiftModifier if sobre_curva else Qt.NoModifier)
    punto = max(lz.b.puntos)
    assert any(r.tipo == ("coincidente" if sobre_curva else "punto_medio") and r.entidades == [punto, diagonal]
               for r in lz.b.restricciones.values())
    if materializado:
        lz.b.asegurar_referencias([Boceto.ORIGEN])
    antes = {i: lz.b.coords(i) for i in esquinas}
    lz.set_herramienta("r_coincidente")
    clics = [(0, 0), (-87.5, 25)] if origen_primero else [(-87.5, 25), (0, 0)]
    for xy in clics:
        _clic(lz, *xy)
    assert lz.b.coords(punto) == pytest.approx((0, 0), abs=1e-6)
    assert lz.resultado.ok and not lz.picks
    assert any("Restricción agregada" in m for m in lz.mensajes)
    assert any(lz.b.coords(i) != antes[i] for i in esquinas)
    # B-225 trata el reparto del movimiento; acá se conserva la forma rectangular, no se fija su tamaño.
    a, b, c, d = (lz.b.coords(i) for i in esquinas)
    assert (a[1], b[0], c[1], d[0]) == pytest.approx((b[1], c[0], d[1], a[0]), abs=1e-6)
    if not sobre_curva:
        for pid, xy in zip(esquinas, [(-32.5, -25), (32.5, -25), (32.5, 25), (-32.5, 25)], strict=True):
            assert lz.b.coords(pid) == pytest.approx(xy, abs=1e-6)


@pytest.mark.parametrize("herramienta", [*editor_boceto.RESTRICCIONES_HERRAMIENTA, "cota", "seleccionar"])
def test_b223_origen_elegible_sin_citar_en_todas_las_herramientas(lz, herramienta):
    assert Boceto.ORIGEN not in lz.b.puntos
    lz.set_herramienta(herramienta)
    assert lz.entidad_en(lz.a_px(0, 0)) == Boceto.ORIGEN
    assert lz.b.puntos[Boceto.ORIGEN].proyectado
    assert lz.b.coords(Boceto.ORIGEN) == (0, 0)
    assert len(lz.b.puntos) == 1


@pytest.mark.parametrize("origen_primero", [False, True])
def test_b223_cota_entre_punto_y_origen_con_clics(lz, origen_primero):
    lz.set_herramienta("punto")
    _clic(lz, 30, 20)
    punto = max(lz.b.puntos)
    assert Boceto.ORIGEN not in lz.b.puntos
    lz.set_herramienta("cota")
    for xy in ([(0, 0), (30, 20)] if origen_primero else [(30, 20), (0, 0)]):
        _clic(lz, *xy)
    assert set(lz.picks) == {punto, Boceto.ORIGEN}
    assert lz._esperando_ubicacion
    _clic(lz, 15, 40)
    assert lz.entrada is not None  # el tercer clic abre la cota, no vuelve a pedir entidades


def test_b223_origen_no_habilita_puntos_ocultos_ni_crea_referencias_lejanas(lz):
    oculto = lz.b.agregar_punto(0.5, 0.5, proyectado=True)
    visible = lz.b.agregar_punto(30, 20)
    lz.mostrar["proyectadas"] = False
    lz.set_herramienta("r_coincidente")
    assert lz.entidad_en(lz.a_px(20, 50)) is None
    assert Boceto.ORIGEN not in lz.b.puntos
    assert lz.entidad_en(lz.a_px(30, 20)) == visible
    assert lz.entidad_en(lz.a_px(0.5, 0.5)) == Boceto.ORIGEN
    assert lz.entidad_en(lz.a_px(0, 0)) == Boceto.ORIGEN  # origen materializado, proyecciones apagadas
    assert lz.b.coords(oculto) == (0.5, 0.5)


@pytest.mark.parametrize("materializado", [False, True])
@pytest.mark.parametrize("proyectadas", [False, True])
def test_b223_origen_compite_por_distancia_con_puntos_cercanos(lz, materializado, proyectadas):
    punto = lz.b.agregar_punto(1, 0)
    lz.mostrar["proyectadas"] = proyectadas
    if materializado:
        lz.b.asegurar_referencias([Boceto.ORIGEN])
    lz.set_herramienta("r_coincidente")
    assert lz.entidad_en(lz.a_px(1, 0)) == punto
    assert lz.entidad_en(lz.a_px(0, 0)) == Boceto.ORIGEN


def test_b223_ejes_ocultos_no_ocultan_el_origen(lz):
    lz.b.asegurar_referencias([Boceto.EJE_X, Boceto.EJE_Y])
    lz.mostrar.update(proyectadas=False, construccion=False)
    lz.set_herramienta("cota")
    assert lz.entidad_en(lz.a_px(0, 0)) == Boceto.ORIGEN
    assert lz.entidad_en(lz.a_px(1, 0)) == Boceto.ORIGEN  # no el punto auxiliar oculto del eje X


@pytest.mark.parametrize("origen_primero", [False, True])
def test_b223_herramienta_punto_medio_con_origen_centra_rectangulo(lz, origen_primero):
    """La herramienta Punto medio existente también elige el origen sin citarlo antes."""
    lz.centro = [-50, 0]
    lz.ajustar_grilla = False
    lz.set_herramienta("rectangulo")
    for xy in ((-120, 0), (-55, 50)):
        _clic(lz, *xy)
    esquinas = list(lz.b.puntos)
    lz.set_herramienta("linea")
    lz.alternar_construccion()
    for xy in ((-120, 0), (-55, 50)):
        _clic(lz, *xy)
    diagonal = lz._ultima_linea
    lz.set_herramienta("r_punto_medio")
    for xy in ([(0, 0), (-87.5, 25)] if origen_primero else [(-87.5, 25), (0, 0)]):
        _clic(lz, *xy)
    assert lz.resultado.ok
    assert any(r.tipo == "punto_medio" and r.entidades == [Boceto.ORIGEN, diagonal]
               for r in lz.b.restricciones.values())
    for pid, xy in zip(esquinas, [(-32.5, -25), (32.5, -25), (32.5, 25), (-32.5, 25)], strict=True):
        assert lz.b.coords(pid) == pytest.approx(xy, abs=1e-6)


def test_tangente_y_cambiar_por_tangente_en_el_lienzo_no_cambian_el_radio(lz):
    """BOC-83: el comando deja quieto el primer arco; «Cambiar por» llega al mismo lugar."""
    arco = lz.b.agregar_arco_centro((0, 0), (10, 0), (0, 10))
    otro = lz.b.agregar_arco_centro((24, 3), (34, 3), (24, 13))
    lz.aplicar_cambio(lambda: None)
    centro = lz.b.coords(lz.b.curvas[arco].centro)
    assert lz.aplicar_restriccion("tangente", [arco, otro])
    assert lz.b.coords(lz.b.curvas[arco].centro) == pytest.approx(centro, abs=1e-6)
    assert (lz.b.radio(arco), lz.b.radio(otro)) == pytest.approx((10, 10), abs=1e-6)
    rid = next(iter(lz.b.restricciones))
    lz.b.eliminar(rid)
    rid = lz.b.agregar_restriccion("concentrica", [arco, otro])
    lz.resolver()
    radios = lz.b.radio(arco), lz.b.radio(otro)                             # concéntricos, ya no miden 10
    assert lz.reemplazar_restriccion(rid, "tangente")
    assert (lz.b.radio(arco), lz.b.radio(otro)) == pytest.approx(radios, abs=1e-6)


def test_repetir_una_restriccion_no_la_agrega_y_lo_dice(lz):
    linea = _linea_inclinada(lz)
    assert lz.aplicar_restriccion("horizontal_vertical", [linea])
    assert lz.aplicar_restriccion("horizontal_vertical", [linea]) is False
    assert sum(r.tipo == "horizontal" for r in lz.b.restricciones.values()) == 1
    assert "sobre" in lz.mensajes[-1] and lz.resultado.ok


def test_lo_que_contradice_se_rechaza_y_el_boceto_queda_igual(lz):
    linea = _linea_inclinada(lz)
    lz.aplicar_restriccion("horizontal_vertical", [linea])
    antes = lz.b.a_dict()
    assert lz.aplicar_restriccion("vertical", [linea]) is False
    assert lz.b.a_dict() == antes and lz.resultado.ok


def test_horizontal_vertical_sobre_varias_lineas_es_un_solo_paso(lz):
    l1, l2 = _linea_inclinada(lz, 30), _linea_inclinada(lz, 80)
    pasos = len(lz.historial)
    assert lz.aplicar_restriccion("horizontal_vertical", [l1, l2])
    assert sum(r.tipo == "horizontal" for r in lz.b.restricciones.values()) == 2
    assert len(lz.historial) == pasos + 1                      # Ctrl+Z las quita a las dos
    lz.deshacer()
    assert not lz.b.restricciones


def test_horizontal_vertical_sin_nada_util_avisa(lz):
    k = lz.b.agregar_circulo((50, 50), 8)
    assert lz.aplicar_restriccion("horizontal_vertical", [k, k]) is False


def test_fijar_sobre_algo_ya_determinado_sigue_permitido(lz):
    linea = _linea_inclinada(lz)
    p = lz.b.curvas[linea].p1
    assert lz.aplicar_restriccion("fijo", [p])
    assert lz.aplicar_restriccion("fijo", [p])                 # segunda vez: anula la fijación, no es "sobra"
    assert not lz.b.restricciones


def test_menu_del_simbolo_borra_solo_esa_restriccion_y_elige_su_geometria(lz):
    l1, l2 = _linea_inclinada(lz, 30), _linea_inclinada(lz, 80)
    lz.aplicar_restriccion("horizontal_vertical", [l1])
    lz.aplicar_restriccion("paralela", [l1, l2])
    rid = next(r.id for r in lz.b.restricciones.values() if r.tipo == "paralela")
    otras = {k for k in lz.b.restricciones if k != rid}
    menu = lz._menu_restriccion(rid)
    acciones = {a.text(): a for a in menu.actions() if a.text()}
    assert any("geometría" in t for t in acciones) and any(t.startswith("Borrar") for t in acciones)
    next(a for t, a in acciones.items() if "geometría" in t).trigger()
    assert set(lz.seleccion) == {l1, l2}
    lz.seleccion = [rid]
    next(a for t, a in acciones.items() if t.startswith("Borrar")).trigger()
    assert rid not in lz.b.restricciones and set(lz.b.restricciones) == otras
    assert rid not in lz.seleccion and len(lz.b.curvas) == 2
    lz.deshacer()
    assert rid in lz.b.restricciones                           # Ctrl+Z la devuelve


def test_horizontal_y_vertical_tienen_simbolos_distintos():
    """El símbolo sobre la geometría tiene que decir cuál de las dos es (antes las dos usaban el mismo ícono)."""
    assert editor_boceto.ICONO_RESTRICCION["horizontal"] != editor_boceto.ICONO_RESTRICCION["vertical"]
    a = iconos.pixmap("r_horizontal", 32, 1).toImage()
    b = iconos.pixmap("r_vertical", 32, 1).toImage()
    assert a != b and not a.isNull()


def test_cada_tipo_de_restriccion_tiene_un_simbolo_que_se_dibuja():
    for tipo, nombre in editor_boceto.ICONO_RESTRICCION.items():
        assert nombre in iconos.DIBUJOS, (tipo, nombre)
    assert len(set(editor_boceto.ICONO_RESTRICCION[t] for t in ("horizontal", "vertical", "coincidente", "paralela",
                                                                  "perpendicular", "igual", "tangente", "concentrica",
                                                                  "punto_medio", "fijo", "colineal", "simetrica",
                                                                  "curvatura", "poligono"))) == 14       # ningún par repetido


def test_el_menu_restricciones_tiene_las_13_y_el_poligono_aparte():
    grupo = next(g for g in GRUPOS_BOCETO if g[0] == "RESTRICCIONES")
    menu = grupo[2]
    claves = [m[2] if isinstance(m, tuple) else m for m in menu]
    herramientas = [f"sk_{h}" for h in editor_boceto.RESTRICCIONES_HERRAMIENTA]
    visibles = [c for c in claves if c in herramientas]
    assert sorted(visibles) == sorted(herramientas)                # las 13, ninguna repetida
    assert claves[claves.index("sk_r_curvatura") + 1] == "-"                       # un separador entre las 12 y la propia
    assert claves[claves.index("sk_r_poligono") - 1] == "-"
    assert claves[-1] == "sk_autorestringir"
    assert editor_boceto.NOMBRES_RESTRICCION["r_poligono"] == "Polígono regular"


def test_cada_herramienta_de_restriccion_dice_que_pedir():
    assert set(editor_boceto.AYUDA_RESTRICCION) == set(editor_boceto.RESTRICCIONES_HERRAMIENTA)
    assert len(set(editor_boceto.AYUDA_RESTRICCION.values())) == 13     # cada una con su texto
    assert "r_autorestringir" in iconos.DIBUJOS                           # su ícono no es el candado de Fijar


def test_herramienta_find_redundant_constraints():
    s = api.Sesion()

    def L(nombre, **a):
        r = api.llamar(s, nombre, a)
        assert r["ok"], (nombre, a, r)
        return r["result"]
    L("create_sketch", name="S", plane="XY")
    a = L("draw_line", sketch="S", start_x=40, start_y=30, end_x=70, end_y=39)["entities"][0]["id"]
    L("add_constraint", sketch="S", type="horizontal", entities=[a])
    assert L("find_redundant_constraints", sketch="S")["redundant"] == []
    r = api.llamar(s, "add_constraint", {"sketch": "S", "type": "horizontal", "entities": [a]})
    assert not r["ok"] and r["error_kind"] == "SKETCH_OVERCONSTRAINED"         # repetida: no entra
    assert len(L("get_sketch", sketch="S")["constraints"]) == 1               # y no quedó nada a medias


def test_f5_dice_que_sobra_y_lo_deja_elegido(lz):
    linea = _linea_inclinada(lz)
    primera = lz.b.agregar_restriccion("horizontal", [linea])
    repetida = lz.b.agregar_restriccion("horizontal", [linea])            # cargada de un archivo: ya está repetida
    lz.resolver()
    assert lz.resultado.ok
    texto = lz.mostrar_conflictos()
    assert "Sobra" in texto and "horizontal" in texto
    assert lz.seleccion == [repetida]
    lz.borrar_seleccion()
    assert set(lz.b.restricciones) == {primera} and lz.resultado.ok
    assert lz.mostrar_conflictos() == "No hay restricciones ni cotas en conflicto."


def test_el_simbolo_aparece_junto_a_cada_curva_de_una_relacion_entre_dos(lz):
    l1, l2 = _linea_inclinada(lz, 30), _linea_inclinada(lz, 80)
    rid = lz.b.agregar_restriccion("paralela", [l1, l2])
    lz.resolver()
    lz.encuadrar()
    lz.grab()
    assert rid in lz._zonas_glifos and [i for i, _c in lz._zonas_glifos_extra] == [rid]
    caja2 = lz._zonas_glifos_extra[0][1]
    assert caja2 != lz._zonas_glifos[rid]
    from PySide6.QtTest import QTest
    from PySide6.QtCore import Qt
    for caja in (lz._zonas_glifos[rid], caja2):                           # un clic en cualquiera elige la restricción
        lz.seleccion = []
        QTest.mouseClick(lz, Qt.LeftButton, Qt.NoModifier, caja.center().toPoint())
        assert lz.seleccion == [rid]


def test_cambiar_una_restriccion_por_otra_conserva_el_id_y_es_un_paso(lz):
    l1, l2 = _linea_inclinada(lz, 30), _linea_inclinada(lz, 80)
    rid = lz.b.agregar_restriccion("paralela", [l1, l2])
    lz.resolver()
    assert set(lz.b.tipos_compatibles(rid)) == {"perpendicular", "igual", "colineal"}
    pasos = len(lz.historial)
    assert lz.reemplazar_restriccion(rid, "perpendicular")
    assert lz.b.restricciones[rid].tipo == "perpendicular" and len(lz.historial) == pasos + 1
    assert lz.resultado.ok
    lz.deshacer()
    assert lz.b.restricciones[rid].tipo == "paralela"


def test_cambiar_por_algo_que_choca_o_no_aplica_deja_la_original(lz):
    l1, l2 = _linea_inclinada(lz, 30), _linea_inclinada(lz, 80)
    lz.b.agregar_restriccion("paralela", [l1, l2])
    rid = lz.b.agregar_restriccion("igual", [l1, l2])
    lz.resolver()
    assert lz.reemplazar_restriccion(rid, "coincidente") is False           # dos líneas no pueden ser «coincidente»
    assert lz.b.restricciones[rid].tipo == "igual"
    assert lz.reemplazar_restriccion(rid, "perpendicular") is False         # contradice la paralela
    assert lz.b.restricciones[rid].tipo == "igual" and lz.resultado.ok


def test_herramienta_replace_constraint():
    s = api.Sesion()

    def llamar(nombre, **a):
        return api.llamar(s, nombre, a)
    assert llamar("create_sketch", name="S", plane="XY")["ok"]
    a = llamar("draw_line", sketch="S", start_x=40, start_y=30, end_x=70, end_y=39)["result"]["entities"][0]["id"]
    c = llamar("draw_line", sketch="S", start_x=40, start_y=60, end_x=80, end_y=70)["result"]["entities"][0]["id"]
    rid = llamar("add_constraint", sketch="S", type="parallel", entities=[a, c])["result"]["constraint"]["id"]
    r = llamar("replace_constraint", sketch="S", constraint=rid, type="perpendicular")
    assert r["ok"] and r["result"]["constraint"]["id"] == rid
    tipos = [x["type"] for x in llamar("get_sketch", sketch="S")["result"]["constraints"]]
    assert tipos == ["perpendicular"]
    malo = llamar("replace_constraint", sketch="S", constraint=rid, type="coincident")
    assert not malo["ok"] and malo["error_kind"] == "INVALID_CONSTRAINT"
    assert not llamar("replace_constraint", sketch="S", constraint=9999, type="parallel")["ok"]


def test_b241_borrar_un_recuadro_que_toma_el_origen_borra_el_resto(lz):
    linea = _linea_inclinada(lz)
    mensajes = []
    lz.mensaje.connect(mensajes.append)
    lz.b.asegurar_referencias([0, -1])              # el origen y el eje X existen (los cita una restricción)
    lz.seleccion = [0, -1, linea]                   # el recuadro tomó el origen, el eje y la línea
    lz.borrar_seleccion()
    assert linea not in lz.b.curvas and 0 in lz.b.puntos
    assert "referencias fijas" in mensajes[-1] and "resto" in mensajes[-1]
    lz.seleccion = [0]                               # solo el origen: avisa y no toca nada
    lz.borrar_seleccion()
    assert 0 in lz.b.puntos and "resto" not in mensajes[-1]

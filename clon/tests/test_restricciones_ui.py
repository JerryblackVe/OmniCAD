# -*- coding: utf-8 -*-
"""Restricciones del boceto en el Lienzo (offscreen, eventos simulados): lo que sobra se rechaza con un mensaje, lo que
choca no entra, H/V sobre varias líneas es UN paso de deshacer, el menú del símbolo y el menú RESTRICCIONES de la cinta."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

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

# -*- coding: utf-8 -*-
"""Interacción con el boceto como en Fusion 360, simulando ratón y teclado sobre el Lienzo:
cotas en vivo mientras se dibuja, arrastre de curvas con el solver, ventana de selección,
doble clic en una cadena, medidas de lo elegido y atajos del boceto (M) sin ambigüedad."""
import math
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPointF, QSettings, Qt  # noqa: E402
from PySide6.QtGui import QColor  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from omnicad.nucleo import geometria as g  # noqa: E402
from omnicad.restricciones import Boceto  # noqa: E402
from omnicad.timeline.parametros import TablaParametros  # noqa: E402

PLANO = g.Plano("XY")


_CREADOS = []


@pytest.fixture(scope="module")
def app_qt():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def _cerrar_lienzos():
    """Cada Lienzo se cierra y se borra con deleteLater dentro del bucle de Qt: si Python borra de golpe
    una ventana con hijos ya marcados para borrar (la caja de valor cerrada), Qt aborta."""
    yield
    while _CREADOS:
        w = _CREADOS.pop()
        w.close()
        w.deleteLater()
    if QApplication.instance() is not None:
        QTest.qWait(1)


def _lienzo(app_qt, boceto=None):
    from omnicad.ui.editor_boceto import Lienzo
    for w in _CREADOS:                           # QTest.mouseMove va a la ventana que esté debajo del cursor
        w.close()
    lz = Lienzo(boceto or Boceto(), TablaParametros().evaluar, plano=PLANO)
    lz.ajustar_grilla = False
    lz.resize(800, 600)          # 4 px/mm con el centro en (400, 300): los mm múltiplos de 0.25 caen justo
    lz.show()
    _CREADOS.append(lz)
    return lz


def _px(lz, x, y):
    return lz.a_px(x, y).toPoint()


def _mover(lz, x, y):
    QTest.mouseMove(lz, _px(lz, x, y))


def _clic(lz, x, y, mods=Qt.NoModifier):
    _mover(lz, x, y)
    QTest.mouseClick(lz, Qt.LeftButton, mods, _px(lz, x, y))


def _arrastrar(lz, desde, hasta, mods=Qt.NoModifier):
    QTest.mouseMove(lz, _px(lz, *desde))
    QTest.mousePress(lz, Qt.LeftButton, mods, _px(lz, *desde))
    medio = ((desde[0] + hasta[0]) / 2, (desde[1] + hasta[1]) / 2)
    QTest.mouseMove(lz, _px(lz, *medio))
    QTest.mouseMove(lz, _px(lz, *hasta))
    QTest.mouseRelease(lz, Qt.LeftButton, mods, _px(lz, *hasta))


def _escribir(lz, texto):
    """Teclea sobre el Lienzo: el primer carácter abre la caja activa y el resto va a su campo."""
    QTest.keyClick(lz, texto[0])
    assert lz.entrada is not None, "escribir un número abre la caja activa"
    for ch in texto[1:]:
        QTest.keyClick(lz.entrada.campos[0], ch)


def _tecla_campo(lz, tecla):
    QTest.keyClick(lz.entrada.campos[0], tecla)


def _campos(lz):
    from omnicad.ui.editor_boceto import texto_valor
    return {c.clave: texto_valor(c.valor, c.angular, c.entero) for c in lz._campos_vivos()}


def _cotas(lz):
    return sorted((c.tipo, c.expresion) for c in lz.b.cotas.values())


# ---------------------------------------------------------------- 1. cotas en vivo mientras se dibuja
def test_formato_de_las_cajas_de_valor():
    from omnicad.ui.editor_boceto import texto_valor
    assert texto_valor(74.4071) == "74.407 mm"
    assert texto_valor(45, angular=True) == "45.0 deg"
    assert texto_valor(6, entero=True) == "6"


def test_linea_muestra_largo_y_angulo_que_siguen_al_raton(app_qt):
    lz = _lienzo(app_qt)
    lz.set_herramienta("linea")
    _clic(lz, 0, 0)
    _mover(lz, 30, 40)
    assert _campos(lz) == {"largo": "50.000 mm", "angulo": "53.1 deg"}
    _mover(lz, -60, 0)
    assert _campos(lz) == {"largo": "60.000 mm", "angulo": "180.0 deg"}
    lz.grab()                                                   # se dibujan las cajas y las cotas provisionales
    assert [k for k, _ in lz._cajas_vivas] == ["largo", "angulo"]
    a, b = (r for _, r in lz._cajas_vivas)
    assert not a.intersects(b)                                  # las cajas no se pisan


def test_linea_escribir_bloquea_el_valor_tab_y_clic_crean_la_cota(app_qt):
    lz = _lienzo(app_qt)
    lz.set_herramienta("linea")
    _clic(lz, 0, 0)
    _mover(lz, 30, 40)
    assert lz._activo == 0                                      # la caja activa es el largo
    _escribir(lz, "25")
    assert lz.entrada.campos[0].text() == "25"                 # el segundo dígito no reemplaza al primero
    _tecla_campo(lz, Qt.Key_Tab)
    assert lz.entrada is None and "largo" in lz._bloqueos and lz._activo == 1   # Tab: bloquea y pasa al ángulo
    _mover(lz, 0, 40)                                           # el ratón ya no cambia el largo, sí el ángulo
    assert _campos(lz) == {"largo": "25.000 mm", "angulo": "90.0 deg"}
    lz.grab()                                                   # (se dibuja el candadito de la caja bloqueada)
    _clic(lz, 0, 40)                                            # el clic confirma
    linea = next(c for c in lz.b.curvas.values() if c.tipo == "linea")
    (x1, y1), (x2, y2) = lz.b._extremos_linea(linea.id)
    assert (x1, y1, x2) == pytest.approx((0, 0, 0)) and y2 == pytest.approx(25)
    assert _cotas(lz) == [("distancia", "25")]                  # lo escrito se vuelve cota de boceto
    assert lz.resultado.ok and not lz._bloqueos                 # la cadena sigue con cajas nuevas


def test_linea_encadenada_angulo_con_la_anterior(app_qt):
    lz = _lienzo(app_qt)
    lz.set_herramienta("linea")
    _clic(lz, 0, 0)
    _clic(lz, 20, 0)
    _mover(lz, 20, 10)
    assert _campos(lz)["angulo"] == "90.0 deg"                 # contra la línea anterior, como Fusion
    QTest.keyClick(lz, Qt.Key_Tab)                              # Tab en el Lienzo: pasa a la caja del ángulo
    assert lz._activo == 1
    _escribir(lz, "120")
    _tecla_campo(lz, Qt.Key_Tab)
    _escribir(lz, "10")
    _tecla_campo(lz, Qt.Key_Return)                             # Enter crea con los dos valores escritos
    ultima = max(lz.b.curvas)
    (x1, y1), (x2, y2) = lz.b._extremos_linea(ultima)
    assert math.dist((x1, y1), (x2, y2)) == pytest.approx(10, abs=1e-6)
    interior = math.degrees(math.atan2(y2 - y1, x2 - x1))      # 120° con la anterior → 60° con el eje X
    assert interior == pytest.approx(60, abs=1e-6)
    assert ("angulo", "60") in _cotas(lz) and ("distancia", "10") in _cotas(lz) and lz.resultado.ok


def test_rectangulo_ancho_y_alto_escritos(app_qt):
    lz = _lienzo(app_qt)
    lz.set_herramienta("rectangulo")
    _clic(lz, 0, 0)
    _mover(lz, 10, 5)
    assert _campos(lz) == {"ancho": "10.000 mm", "alto": "5.000 mm"}
    _mover(lz, 12, -7)
    assert _campos(lz) == {"ancho": "12.000 mm", "alto": "7.000 mm"}
    _escribir(lz, "40")
    _tecla_campo(lz, Qt.Key_Tab)
    _mover(lz, 15, -9)
    assert _campos(lz) == {"ancho": "40.000 mm", "alto": "9.000 mm"}   # el ancho quedó bloqueado
    _escribir(lz, "20")
    _tecla_campo(lz, Qt.Key_Return)
    xs = sorted({round(p.x, 6) for p in lz.b.puntos.values()})
    ys = sorted({round(p.y, 6) for p in lz.b.puntos.values()})
    assert xs == [0, 40] and ys == [-20, 0]                     # hacia donde estaba el ratón
    assert _cotas(lz) == [("distancia", "20"), ("distancia", "40")] and lz.resultado.ok
    assert lz.resultado.gdl == 0           # la esquina quedó pegada al origen: totalmente restringido (Fusion)


def test_enter_sin_caja_abierta_confirma_lo_bloqueado(app_qt):
    lz = _lienzo(app_qt)
    lz.set_herramienta("circulo")
    _clic(lz, 0, 0)
    _mover(lz, 5, 0)
    assert _campos(lz) == {"diametro": "10.000 mm"}
    _escribir(lz, "30")
    _tecla_campo(lz, Qt.Key_Tab)                                # bloquea (una sola caja: queda activa)
    QTest.keyClick(lz, Qt.Key_Return)
    circulo = next(c for c in lz.b.curvas.values() if c.tipo == "circulo")
    assert circulo.radio == pytest.approx(15) and _cotas(lz) == [("diametro", "30")]


def test_esc_descarta_lo_escrito(app_qt):
    lz = _lienzo(app_qt)
    lz.set_herramienta("circulo")
    _clic(lz, 0, 0)
    _mover(lz, 5, 0)
    _escribir(lz, "30")
    _tecla_campo(lz, Qt.Key_Tab)
    QTest.keyClick(lz, Qt.Key_Escape)
    assert not lz.clics and not lz._bloqueos and not lz.b.curvas


@pytest.mark.parametrize("herramienta, clics, raton, esperado", [
    ("rectangulo_centro", [(0, 0)], (10, 5), {"ancho": "20.000 mm", "alto": "10.000 mm"}),
    ("rectangulo_3p", [(0, 0)], (10, 0), {"ancho": "10.000 mm"}),
    ("rectangulo_3p", [(0, 0), (10, 0)], (5, 4), {"alto": "4.000 mm"}),
    ("arco", [(0, 0)], (20, 0), {"cuerda": "20.000 mm"}),
    ("arco", [(0, 0), (20, 0)], (10, 5), {"radio": "12.500 mm"}),
    ("arco_centro", [(0, 0)], (10, 0), {"radio": "10.000 mm"}),
    ("arco_centro", [(0, 0), (10, 0)], (0, 10), {"barrido": "90.0 deg"}),
    ("poligono_inscrito", [(0, 0)], (10, 0), {"radio": "10.000 mm", "lados": "6"}),
    ("ranura_centro", [(0, 0)], (20, 0), {"largo": "20.000 mm"}),
    ("ranura_punto", [(0, 0)], (10, 0), {"largo": "20.000 mm"}),
    ("ranura_centro", [(0, 0), (20, 0)], (10, 3), {"ancho": "6.000 mm"}),
    ("ranura_arco_centro", [(0, 0), (10, 0), (0, 10)], (0, 12), {"ancho": "4.000 mm"}),
])
def test_cajas_de_cada_herramienta(app_qt, herramienta, clics, raton, esperado):
    lz = _lienzo(app_qt)
    lz.set_herramienta(herramienta)
    for q in clics:
        _clic(lz, *q)
    _mover(lz, *raton)
    assert _campos(lz) == esperado
    lz.grab()


def test_arcos_con_valores_escritos(app_qt):
    lz = _lienzo(app_qt)
    lz.set_herramienta("arco")
    _clic(lz, 0, 0)
    _mover(lz, 16, 0)
    _escribir(lz, "20")
    _tecla_campo(lz, Qt.Key_Return)                             # Enter en el primer paso: el fin a 20 mm
    _mover(lz, 10, 5)
    _escribir(lz, "15")
    _tecla_campo(lz, Qt.Key_Return)
    arco = next(c for c in lz.b.curvas.values() if c.tipo == "arco")
    assert lz.b.radio(arco.id) == pytest.approx(15) and math.dist(lz.b.coords(arco.inicio),
                                                                  lz.b.coords(arco.fin)) == pytest.approx(20)
    assert _cotas(lz) == [("distancia", "20"), ("radio", "15")] and lz.resultado.ok
    assert lz._largo(arco.id) < 25                              # el arco menor, del lado del ratón

    lz = _lienzo(app_qt)
    lz.set_herramienta("arco_centro")
    _clic(lz, 0, 0)
    _mover(lz, 8, 0)
    _escribir(lz, "10")
    _tecla_campo(lz, Qt.Key_Return)
    _mover(lz, 0, 10)
    _escribir(lz, "270")
    _tecla_campo(lz, Qt.Key_Return)                             # barrido de más de media vuelta
    arco = next(c for c in lz.b.curvas.values() if c.tipo == "arco")
    assert lz._largo(arco.id) == pytest.approx(10 * 1.5 * math.pi, rel=1e-6)
    assert _cotas(lz) == [("radio", "10")]


def test_poligono_lados_y_radio_escritos(app_qt):
    lz = _lienzo(app_qt)
    lz.set_herramienta("poligono_inscrito")
    _clic(lz, 0, 0)
    _mover(lz, 10, 0)
    QTest.keyClick(lz, Qt.Key_Tab)
    _escribir(lz, "8")
    _tecla_campo(lz, Qt.Key_Tab)
    assert lz.lados == 8 and _campos(lz)["lados"] == "8"
    _escribir(lz, "12")
    _tecla_campo(lz, Qt.Key_Return)
    assert sum(c.tipo == "linea" for c in lz.b.curvas.values()) == 8
    circulo = next(c for c in lz.b.curvas.values() if c.tipo == "circulo")
    assert circulo.radio == pytest.approx(12) and _cotas(lz) == [("radio", "12")] and lz.resultado.ok


def test_ranuras_con_largo_y_ancho_escritos(app_qt):
    lz = _lienzo(app_qt)
    lz.set_herramienta("ranura_centro")
    _clic(lz, 0, 0)
    _mover(lz, 20, 0)
    _escribir(lz, "30")
    _tecla_campo(lz, Qt.Key_Return)
    _mover(lz, 10, 3)
    _escribir(lz, "8")
    _tecla_campo(lz, Qt.Key_Return)
    assert _cotas(lz) == [("diametro", "8"), ("distancia", "30")] and lz.resultado.ok
    tapas = [c for c in lz.b.curvas.values() if c.tipo == "arco"]
    assert [lz.b.radio(t.id) for t in tapas] == pytest.approx([4, 4])

    lz = _lienzo(app_qt)                                        # ranura total: la cota va entre centros
    lz.set_herramienta("ranura_total")
    _clic(lz, 0, 0)
    _mover(lz, 20, 0)
    _escribir(lz, "40")
    _tecla_campo(lz, Qt.Key_Return)
    _mover(lz, 10, 3)
    _escribir(lz, "10")
    _tecla_campo(lz, Qt.Key_Return)
    assert _cotas(lz) == [("diametro", "10"), ("distancia", "30")] and lz.resultado.ok


def test_valor_invalido_no_se_bloquea(app_qt):
    lz = _lienzo(app_qt)
    lz.set_herramienta("circulo")
    _clic(lz, 0, 0)
    _mover(lz, 5, 0)
    _escribir(lz, "-3")
    _tecla_campo(lz, Qt.Key_Return)
    assert lz.entrada is not None and not lz._bloqueos and not lz.b.curvas   # queda el campo para corregir


# ---------------------------------------------------------------- 2. arrastrar líneas, círculos y arcos
def test_arrastrar_una_linea_mueve_sus_dos_extremos(app_qt):
    b = Boceto()
    lid = b.agregar_linea((0, 0), (20, 0))
    lz = _lienzo(app_qt, b)
    _arrastrar(lz, (10, 0), (10, 10))
    (x1, y1), (x2, y2) = lz.b._extremos_linea(lid)
    assert (x1, y1, x2, y2) == pytest.approx((0, 10, 20, 10))
    lz.deshacer()                                               # un solo paso de deshacer
    assert lz.b._extremos_linea(lid) == ((0.0, 0.0), (20.0, 0.0))


def test_arrastrar_respeta_lo_restringido(app_qt):
    b = Boceto()
    lid = b.agregar_linea((0, 0), (20, 0))
    b.agregar_restriccion("fijo", [b.curvas[lid].p1])           # un extremo fijo: la línea gira / estira
    lz = _lienzo(app_qt, b)
    _arrastrar(lz, (10, 0), (10, 10))
    (x1, y1), (x2, y2) = lz.b._extremos_linea(lid)
    assert (x1, y1) == pytest.approx((0, 0)) and y2 == pytest.approx(10, abs=0.3)

    b = Boceto()
    ls = b.agregar_rectangulo((0, 0), (20, 10))
    b.agregar_restriccion("fijo", [b.curvas[ls[0]].p1])
    b.agregar_cota("distancia", [ls[0]], "20")
    b.agregar_cota("distancia", [ls[1]], "10")
    lz = _lienzo(app_qt, b)
    assert lz.resultado.gdl == 0
    antes = {p.id: (p.x, p.y) for p in lz.b.puntos.values()}
    avisos = []
    lz.mensaje.connect(avisos.append)
    _arrastrar(lz, (10, 0), (10, 6))                            # totalmente restringido: no se mueve
    _arrastrar(lz, (20, 10), (26, 16))                          # tampoco un vértice
    assert {p.id: (p.x, p.y) for p in lz.b.puntos.values()} == antes
    assert any("restringid" in t for t in avisos)


def test_arrastrar_circulo_y_arco(app_qt):
    b = Boceto()
    cid = b.agregar_circulo((0, 0), 10)
    lz = _lienzo(app_qt, b)
    _arrastrar(lz, (10, 0), (15, 0))                            # la curva: cambia el radio
    assert lz.b.curvas[cid].radio == pytest.approx(15)
    centro = lz.b.curvas[cid].centro
    _arrastrar(lz, (0, 0), (5, 5))                              # el centro: lo mueve
    assert lz.b.coords(centro) == pytest.approx((5, 5)) and lz.b.curvas[cid].radio == pytest.approx(15)

    b = Boceto()
    cid = b.agregar_circulo((0, 0), 10)
    b.agregar_cota("diametro", [cid], "20")
    lz = _lienzo(app_qt, b)
    _arrastrar(lz, (10, 0), (15, 5))                            # radio acotado: arrastrar la curva la mueve
    assert lz.b.curvas[cid].radio == pytest.approx(10) and lz.b.coords(lz.b.curvas[cid].centro) == pytest.approx((5, 5))

    b = Boceto()
    aid = b.agregar_arco_centro((0, 0), (10, 0), (0, 10))
    lz = _lienzo(app_qt, b)
    q = (10 * math.cos(math.pi / 4), 10 * math.sin(math.pi / 4))
    _arrastrar(lz, q, (q[0] * 1.5, q[1] * 1.5))
    assert lz.b.radio(aid) == pytest.approx(15, abs=0.2) and lz.resultado.ok
    arco = lz.b.curvas[aid]
    _arrastrar(lz, (0, 0), (-5, -5))                            # el centro arrastra el arco entero
    assert lz.b.coords(arco.centro) == pytest.approx((-5, -5))
    assert lz.b.radio(aid) == pytest.approx(15, abs=0.2) and lz.resultado.ok


# ---------------------------------------------------------------- 3. ventana de selección
def _dos_lineas():
    b = Boceto()
    adentro = b.agregar_linea((0, 0), (10, 0))
    cruza = b.agregar_linea((30, 5), (60, 5))
    return b, adentro, cruza


def test_ventana_de_izquierda_a_derecha_elige_lo_que_queda_adentro(app_qt):
    from omnicad.ui.editor_boceto import Lienzo
    b, adentro, cruza = _dos_lineas()
    lz = _lienzo(app_qt, b)
    _arrastrar(lz, (-4, -6), (40, 8))
    assert adentro in lz.seleccion and cruza not in lz.seleccion
    relleno, borde = Lienzo.colores_ventana(lz, QPointF(0, 0), QPointF(50, 50))
    assert relleno == QColor(237, 120, 0, 70) and borde == QColor(140, 150, 180)


def test_ventana_de_derecha_a_izquierda_elige_lo_que_toca(app_qt):
    b, adentro, cruza = _dos_lineas()
    lz = _lienzo(app_qt, b)
    _arrastrar(lz, (40, 8), (-4, -6))
    assert adentro in lz.seleccion and cruza in lz.seleccion
    relleno, borde = lz.colores_ventana(QPointF(50, 0), QPointF(0, 50))
    assert relleno == QColor(193, 191, 0, 70) and borde is None
    lz.seleccion = []                                           # toca sin tener ningún punto adentro
    _arrastrar(lz, (50, 8), (45, 2))
    assert lz.seleccion == [cruza]


def test_ventana_con_ctrl_o_mayus_suma(app_qt):
    b, adentro, cruza = _dos_lineas()
    lz = _lienzo(app_qt, b)
    _clic(lz, 45, 5)
    assert lz.seleccion == [cruza]
    _arrastrar(lz, (-4, -6), (14, 6), Qt.ControlModifier)
    assert cruza in lz.seleccion and adentro in lz.seleccion
    _arrastrar(lz, (-4, -6), (14, 6))                           # sin modificador reemplaza
    assert cruza not in lz.seleccion and adentro in lz.seleccion


def test_la_ventana_se_dibuja_mientras_se_arrastra(app_qt):
    lz = _lienzo(app_qt)
    QTest.mousePress(lz, Qt.LeftButton, Qt.NoModifier, _px(lz, -10, -10))
    QTest.mouseMove(lz, _px(lz, 10, 10))
    assert lz._ventana is not None
    img = lz.grab().toImage()
    medio = img.pixelColor(_px(lz, 5, 5))                      # dentro de la ventana: tinte naranja
    assert medio.red() > medio.blue() + 30
    QTest.mouseRelease(lz, Qt.LeftButton, Qt.NoModifier, _px(lz, 10, 10))


# ---------------------------------------------------------------- 4. cotas como Fusion (sin caja)
def test_cotas_sin_caja_y_sin_pisarse(app_qt):
    from omnicad.ui.editor_boceto import COTA_CLARO, COTA_OSCURO
    b = Boceto()
    ls = b.agregar_rectangulo((0, 0), (20, 10))
    b.agregar_cota("distancia", [ls[0]], "20")
    b.agregar_cota("distancia", [ls[2]], "20")
    b.agregar_cota("distancia", [ls[1]], "10")
    lz = _lienzo(app_qt, b)
    lz.grab()
    zonas = list(lz._zonas_cotas.values())
    assert len(zonas) == 3 and not any(z1.intersects(z2) for i, z1 in enumerate(zonas) for z2 in zonas[i + 1:])
    assert lz._color_cota() == COTA_CLARO and COTA_OSCURO.name() == "#a9c46c"
    cid = next(iter(lz.b.cotas))
    lz.editar_cota(cid, lz._zonas_cotas[cid].center())          # al editar aparece la caja con borde
    assert lz.entrada is not None and lz._cota_editada == cid
    lz._cerrar_entrada()
    assert lz._cota_editada is None


# ---------------------------------------------------------------- 5. doble clic: la cadena
def test_doble_clic_elige_toda_la_cadena_unida(app_qt):
    b = Boceto()
    lados = b.agregar_rectangulo((0, 0), (20, 10))
    suelta = b.agregar_linea((40, 0), (60, 0))
    l1 = b.agregar_linea((0, 30), (10, 30))
    l2 = b.agregar_linea((10, 30.5), (20, 40))
    b.agregar_restriccion("coincidente", [b.curvas[l1].p2, b.curvas[l2].p1])   # unidas por coincidencia
    lz = _lienzo(app_qt, b)
    QTest.mouseDClick(lz, Qt.LeftButton, Qt.NoModifier, _px(lz, 10, 0))
    assert sorted(lz.seleccion) == sorted(lados) and suelta not in lz.seleccion
    QTest.mouseDClick(lz, Qt.LeftButton, Qt.NoModifier, _px(lz, 5, 30))
    assert sorted(lz.seleccion) == sorted([l1, l2])
    QTest.mouseDClick(lz, Qt.LeftButton, Qt.ShiftModifier, _px(lz, 50, 0))   # Mayús suma otra cadena
    assert sorted(lz.seleccion) == sorted([l1, l2, suelta])


# ---------------------------------------------------------------- 6. medidas de lo elegido
def test_texto_de_medidas_como_fusion(app_qt):
    b = Boceto()
    lid = b.agregar_linea((0, 0), (30, 40))
    cid = b.agregar_circulo((100, 0), 25)
    aid = b.agregar_arco_centro((0, 100), (10, 100), (0, 110))
    lz = _lienzo(app_qt, b)
    textos = []
    lz.info.connect(textos.append)
    lz.seleccion = [lid]
    lz._notificar_seleccion()
    assert textos[-1] == "1 línea de boceto | Longitud: 50.000 mm"
    lz.seleccion = [cid]
    lz._notificar_seleccion()
    assert textos[-1] == "1 círculo de boceto | Radio: 25.000 mm"
    lz.seleccion = [aid]
    assert lz.describir_seleccion() == f"1 arco de boceto | Longitud: {5 * math.pi:.3f} mm"
    lz.seleccion = [lid, aid]
    assert lz.describir_seleccion() == f"2 curvas de boceto | Longitud: {50 + 5 * math.pi:.3f} mm"
    lz.seleccion = [b.curvas[lid].p1]
    assert lz.describir_seleccion() == "1 punto de boceto"
    _clic(lz, 200, 200)                                         # clic en vacío: se borra
    assert textos[-1] == ""


# ---------------------------------------------------------------- 7. aviso al perder restricciones o cotas
def test_aviso_si_una_operacion_borra_cotas(app_qt):
    b = Boceto()
    ls = b.agregar_rectangulo((0, 0), (20, 10))
    b.agregar_cota("distancia", [ls[0]], "20")
    lz = _lienzo(app_qt, b)
    avisos = []
    lz.aviso.connect(avisos.append)
    lz.set_herramienta("empalme")                               # el empalme conserva la cota: sin aviso
    _clic(lz, 15, 0)
    _clic(lz, 20, 5)
    _escribir(lz, "3")
    _tecla_campo(lz, Qt.Key_Return)
    assert any(c.tipo == "arco" for c in lz.b.curvas.values()) and avisos == []

    b = Boceto()
    linea = b.agregar_linea((0, 0), (20, 0))
    b.agregar_linea((10, -5), (10, 5))
    b.agregar_cota("distancia", [linea], "20")
    lz = _lienzo(app_qt, b)
    lz.aviso.connect(avisos.append)
    lz.set_herramienta("recortar")                              # recortar se lleva la cota de largo
    _clic(lz, 15, 0)
    assert not lz.b.cotas
    assert avisos == ["Las restricciones o las cotas se han eliminado durante la operación."]


# ---------------------------------------------------------------- 8. atajos del boceto (M) sin ambigüedad
@pytest.fixture(scope="module")
def ventana(app_qt, tmp_path_factory):
    from omnicad.ui.preferencias import Preferencias
    from omnicad.ui.ventana import VentanaPrincipal
    ruta = tmp_path_factory.mktemp("prefs") / "preferencias.ini"
    v = VentanaPrincipal(prefs=Preferencias(QSettings(str(ruta), QSettings.IniFormat)))
    v.show()
    v.activateWindow()
    QTest.qWaitForWindowActive(v, 2000)
    yield v
    v.close()
    v.deleteLater()
    QTest.qWait(1)


def _atajos_repetidos(v):
    from PySide6.QtGui import QAction
    vistos, repetidos = {}, []
    for a in v.findChildren(QAction):
        if a.isEnabled():
            for s in a.shortcuts():
                texto = s.toString()
                if texto and texto in vistos and vistos[texto] is not a:
                    repetidos.append(texto)
                vistos.setdefault(texto, a)
    return repetidos


def test_m_dentro_del_boceto_es_mover_del_boceto(ventana):
    v, mb = ventana, ventana.modo_boceto
    assert v.acciones["mover_copiar"].isEnabled() and not _atajos_repetidos(v)
    mb.iniciar(Boceto(), PLANO, {"op": None, "plano": "XY"})
    try:
        assert _atajos_repetidos(v) == []                       # antes: "M" estaba dos veces habilitada
        assert not v.acciones["mover_copiar"].isEnabled()
        mb.lienzo.setFocus()
        QTest.keyClick(mb.lienzo, Qt.Key_M)
        assert mb.lienzo.herramienta == "mover"
        mb.lienzo.b.agregar_linea((0, 0), (25, 0))
        mb.lienzo.seleccion = [max(mb.lienzo.b.curvas)]
        mb.lienzo._notificar_seleccion()
        assert v._info_sel == "1 línea de boceto | Longitud: 25.000 mm"      # abajo a la derecha
    finally:
        mb.cancelar()
    assert v.acciones["mover_copiar"].isEnabled() and not _atajos_repetidos(v)
    assert v._info_sel == ""                                     # al salir del boceto se borra

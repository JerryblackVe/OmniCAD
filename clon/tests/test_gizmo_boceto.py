"""Asas de arrastre del editor de boceto (ui/asas_boceto.py): tirar de un asa escribe en la caja de valores."""
import math
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, QPointF, Qt  # noqa: E402
from PySide6.QtGui import QMouseEvent  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from omnicad.restricciones import Boceto  # noqa: E402
from omnicad.timeline.parametros import TablaParametros  # noqa: E402
from omnicad.ui import editor_boceto  # noqa: E402


@pytest.fixture
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def lienzo(app):
    lz = editor_boceto.Lienzo(Boceto(), TablaParametros().evaluar)
    lz.resize(800, 600)
    lz.ajustar_grilla = False
    lz.show()
    yield lz
    lz.close()
    lz.deleteLater()
    app.processEvents()


def _raton(lz, tipo, xy, botones=Qt.LeftButton):
    q = lz.a_px(*xy) if not isinstance(xy, QPointF) else xy
    boton = Qt.LeftButton if tipo != QEvent.MouseMove else Qt.NoButton
    QApplication.sendEvent(lz, QMouseEvent(tipo, q, lz.mapToGlobal(q), boton,
                                           botones if tipo != QEvent.MouseButtonRelease else Qt.NoButton, Qt.NoModifier))


def arrastrar(lz, desde, hasta):
    """Press en `desde` (mm), mueve en tramos y suelta en `hasta` (mm), con eventos al widget."""
    _raton(lz, QEvent.MouseButtonPress, desde)
    for k in range(1, 7):
        punto = (desde[0] + (hasta[0] - desde[0]) * k / 6, desde[1] + (hasta[1] - desde[1]) * k / 6)
        _raton(lz, QEvent.MouseMove, punto, Qt.LeftButton)
    _raton(lz, QEvent.MouseButtonRelease, hasta)


def posicion(lz, i):
    asa = lz._asas.asas[i]
    return asa.posicion(lz._asas.valores())


def abrir(lz, herramienta, centro=None):
    c = lz.b.agregar_circulo((0, 0), 3)
    lz.set_herramienta(herramienta)
    lz.seleccion = [c]
    lz._avanzar_seleccion()
    if centro is not None:
        lz._clic_fase((None, centro))
    lz.encuadrar()
    QApplication.processEvents()
    return c


def textos(lz):
    return [c.text() for c in lz.entrada.campos]


def test_patron_rectangular_asas_de_distancia_y_cantidad(lienzo):
    lz = lienzo
    abrir(lz, "patron_rectangular")
    assert lz._asas is not None and len(lz._asas.asas) == 4
    lz.entrada.campos[0].setText("3")
    lz.entrada.campos[1].setText("20")                       # Extensión: la última copia queda a 20 mm
    assert posicion(lz, 0) == pytest.approx((20, 0), abs=1e-6)
    arrastrar(lz, posicion(lz, 0), (30, 0))
    assert float(textos(lz)[1]) == pytest.approx(30, abs=0.3)
    # cantidad: tirar hacia afuera suma copias, de a una por paso
    paso = float(textos(lz)[1]) / (int(textos(lz)[0]) - 1)
    arrastrar(lz, posicion(lz, 1), (posicion(lz, 1)[0] + 2 * paso, posicion(lz, 1)[1]))
    assert int(textos(lz)[0]) == 5
    arrastrar(lz, posicion(lz, 1), (-500, posicion(lz, 1)[1]))                 # pasa por cero y por debajo: mínimo 1
    assert int(textos(lz)[0]) == 1
    lz._cerrar_entrada()
    assert lz._asas is None


def test_patron_rectangular_eje_y_vista_previa(lienzo):
    lz = lienzo
    abrir(lz, "patron_rectangular")
    lz.entrada.campos[2].setText("2")
    lz.entrada.campos[3].setText("15")
    arrastrar(lz, posicion(lz, 2), (0, 25))
    assert float(textos(lz)[3]) == pytest.approx(25, abs=0.3)
    previa = lz._asas.previa(lz._asas.valores())
    assert len(previa) == 3 * 2 - 1                           # 3 x 2 copias menos el original
    lz._cerrar_entrada()


def test_teclear_mueve_el_asa_y_un_valor_invalido_no_la_rompe(lienzo):
    lz = lienzo
    abrir(lz, "patron_rectangular")
    antes = posicion(lz, 0)
    lz.entrada.campos[1].setText("45")
    assert posicion(lz, 0) != antes
    lz.entrada.campos[1].setText("4+")                         # a medio escribir: queda el último valor válido
    assert posicion(lz, 0) == pytest.approx((45, 0), abs=1e-6)
    QApplication.processEvents()
    lz.repaint()
    lz._cerrar_entrada()


def test_enter_aplica_lo_arrastrado_y_esc_cancela(lienzo):
    lz = lienzo
    abrir(lz, "patron_rectangular")
    lz.entrada.campos[0].setText("2")
    lz.entrada.campos[1].setText("10")
    arrastrar(lz, posicion(lz, 0), (18, 0))
    n0 = len(lz.b.curvas)
    QTest.keyClick(lz.entrada.campos[0], Qt.Key_Return)
    assert len(lz.b.curvas) == n0 + 1
    abrir(lz, "patron_rectangular")
    QTest.keyClick(lz.entrada.campos[0], Qt.Key_Escape)
    assert lz.entrada is None and lz._asas is None


def test_patron_circular_angulo_y_cantidad(lienzo):
    lz = lienzo
    c = lz.b.agregar_circulo((20, 0), 3)
    lz.set_herramienta("patron_circular")
    lz.seleccion = [c]
    lz._avanzar_seleccion()
    lz._clic_fase((None, (0.0, 0.0)))
    lz.encuadrar()
    assert len(lz._asas.asas) == 2
    lz.entrada.campos[0].setText("4")
    lz.entrada.campos[1].setText("90")
    assert posicion(lz, 0) == pytest.approx((0.0, 20.0), abs=1e-6)          # el final del arco, a 90°
    arrastrar(lz, posicion(lz, 0), (-20 * math.cos(math.radians(30)), 20 * math.sin(math.radians(30))))
    assert float(textos(lz)[1]) == pytest.approx(150, abs=1.5)
    arrastrar(lz, posicion(lz, 0), (20, 0))
    assert float(textos(lz)[1]) == pytest.approx(0, abs=1.5) or float(textos(lz)[1]) == pytest.approx(360, abs=1.5)
    lz.entrada.campos[1].setText("90")
    p = posicion(lz, 1)
    assert int(textos(lz)[0]) == 4
    a = math.atan2(p[1], p[0]) + math.radians(60)                # dos pasos de 30° más allá de la última copia
    r = math.hypot(*p)
    arrastrar(lz, p, (r * math.cos(a), r * math.sin(a)))
    assert int(textos(lz)[0]) == 6
    assert len(lz._asas.previa(lz._asas.valores())) == 5          # seis copias menos el original
    lz._cerrar_entrada()


def test_escala_factor_nunca_baja_de_cero(lienzo):
    lz = lienzo
    c = lz.b.agregar_circulo((10, 0), 3)
    lz.set_herramienta("escala")
    lz.seleccion = [c]
    lz._avanzar_seleccion()
    lz._clic_fase((None, (0.0, 0.0)))
    lz.encuadrar()
    assert len(lz._asas.asas) == 1
    lz.entrada.campos[0].setText("1")
    p = posicion(lz, 0)
    arrastrar(lz, p, (p[0] * 2, 0))
    assert float(textos(lz)[0]) == pytest.approx(2, abs=0.05)
    arrastrar(lz, posicion(lz, 0), (-30, 0))                    # del otro lado del punto base: tope positivo
    assert float(textos(lz)[0]) > 0
    lz.entrada.campos[0].setText("2")
    poli = lz._asas.previa(lz._asas.valores())[0]
    assert max(q[0] for q in poli) == pytest.approx(26, abs=0.3)    # el círculo de r 3 en x 10, ×2 desde el origen
    lz._cerrar_entrada()


def _esquina(lz, herramienta):
    a = lz.b.agregar_linea((0, 0), (30, 0))
    b = lz.b.agregar_linea((0, 0), (0, 30))
    lz.set_herramienta(herramienta)
    lz.agregar_pick(a, (15.0, 0.0), QPointF(0, 0))
    lz.agregar_pick(b, (0.0, 15.0), QPointF(0, 0))
    lz.encuadrar()
    QApplication.processEvents()
    return a, b


def test_empalme_el_asa_del_arco_cambia_el_radio_y_pasa_por_cero(lienzo):
    lz = lienzo
    _esquina(lz, "empalme")
    assert len(lz._asas.asas) == 1
    lz.entrada.campos[0].setText("5")
    m = 5 - 5 / math.sqrt(2)
    assert posicion(lz, 0) == pytest.approx((m, m), abs=0.05)
    k = 10 - 10 / math.sqrt(2)
    arrastrar(lz, posicion(lz, 0), (k, k))
    assert float(textos(lz)[0]) == pytest.approx(10, abs=0.3)
    arrastrar(lz, posicion(lz, 0), (-8.0, -8.0))                # del otro lado de la esquina: nunca cero ni negativo
    assert float(textos(lz)[0]) > 0
    lz.entrada.campos[0].setText("8")
    assert len(lz._asas.previa(lz._asas.valores())) == 1
    n0 = len(lz.b.curvas)
    QTest.keyClick(lz.entrada.campos[0], Qt.Key_Return)
    assert len(lz.b.curvas) == n0 + 1
    assert lz._asas is None


def test_empalme_con_radio_imposible_no_rompe_el_dibujo(lienzo):
    lz = lienzo
    _esquina(lz, "empalme")
    lz.entrada.campos[0].setText("500")                         # más grande que las líneas: sin vista previa, sin excepción
    lz.repaint()
    assert lz._asas.previa(lz._asas.valores()) == []
    lz._cerrar_entrada()


@pytest.mark.parametrize("herramienta,n", [("chaflan", 1), ("chaflan_dos_dist", 2), ("chaflan_dist_angulo", 2)])
def test_chaflan_asas_en_los_extremos_del_corte(lienzo, herramienta, n):
    lz = lienzo
    _esquina(lz, herramienta)
    assert len(lz._asas.asas) == n
    lz.entrada.campos[0].setText("6")
    if n == 2:
        lz.entrada.campos[1].setText("8" if herramienta == "chaflan_dos_dist" else "45")
    if herramienta == "chaflan":
        p = posicion(lz, 0)
        assert p == pytest.approx((3, 3), abs=0.05)                      # el medio de la línea de 6 y 6
        arrastrar(lz, p, (5, 5))
    else:
        p = posicion(lz, 0)
        assert p == pytest.approx((6, 0), abs=0.05)                      # el extremo sobre la primera línea
        arrastrar(lz, p, (10, 0))
    assert float(textos(lz)[0]) == pytest.approx(10, abs=0.3)
    if n == 2:
        q = posicion(lz, 1)
        if herramienta == "chaflan_dos_dist":
            assert q == pytest.approx((0, 8), abs=0.05)
            arrastrar(lz, q, (0, 12))
            assert float(textos(lz)[1]) == pytest.approx(12, abs=0.3)
        else:
            arrastrar(lz, q, (0, 10))                                    # el otro extremo cae sobre la segunda línea: 45° → atan(10/10)
            assert 0 < float(textos(lz)[1]) < 180
    lz._cerrar_entrada()


def test_texto_asa_de_giro_del_marco(lienzo):
    lz = lienzo
    lz.set_herramienta("texto")
    lz.clics.append((None, (0.0, 0.0)))
    lz.clics.append((None, (40.0, 10.0)))
    lz._procesar_clics()
    lz.encuadrar()
    assert lz._asas is not None and len(lz._asas.asas) == 1
    ancla = (0.0, 10.0)                                                  # la esquina de arriba a la izquierda del marco
    assert posicion(lz, 0) == pytest.approx((ancla[0] + 40.0, ancla[1]), abs=1e-6)
    arrastrar(lz, posicion(lz, 0), (ancla[0] + 20.0, ancla[1] + 20.0))
    assert float(textos(lz)[2]) == pytest.approx(45, abs=1.0)
    arrastrar(lz, posicion(lz, 0), (ancla[0] - 30.0, ancla[1] + 5.0))
    assert float(textos(lz)[2]) == pytest.approx(math.degrees(math.atan2(5, -30)), abs=1.0)
    lz.entrada.campos[2].setText("90")
    assert posicion(lz, 0) == pytest.approx((ancla[0], ancla[1] + 40.0), abs=1e-6)
    lz._cerrar_entrada()

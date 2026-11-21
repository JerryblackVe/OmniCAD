# -*- coding: utf-8 -*-
"""Valores raros del comando de boceto «sk_poligono_arista»: Largo, Ángulo y Lados en vacío, 0, negativo,
enorme, con unidades y con expresión. Aceptar nunca cierra la app ni deja el boceto roto, y todo aviso es de un
renglón. La ayuda de Fusion («Create polygons») define el polígono por arista con largo, ángulo y cantidad de lados.
"""
import math
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import test_boceto_interaccion as T  # noqa: E402
from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from omnicad.restricciones import resolver  # noqa: E402

app_qt = T.app_qt
_cerrar_lienzos = T._cerrar_lienzos

ORIGEN = (0, 0)
EXTREMO = (10, 0)
LADO = (5, 20)
INDICE = {"largo": 0, "angulo": 1, "lados": 2}

VALIDOS = [
    pytest.param("largo", "", 10.0, id="largo_vacio"),
    pytest.param("largo", "12 mm", 12.0, id="largo_unidad"),
    pytest.param("largo", "2*3", 6.0, id="largo_expresion"),
    pytest.param("angulo", "", 0.0, id="angulo_vacio"),
    pytest.param("angulo", "0", 0.0, id="angulo_cero"),
    pytest.param("angulo", "-30", -30.0, id="angulo_negativo"),
    pytest.param("angulo", "30 deg", 30.0, id="angulo_unidad"),
    pytest.param("angulo", "3*2", 6.0, id="angulo_expresion"),
    pytest.param("lados", "", 6, id="lados_vacio"),
]

INVALIDOS = [
    pytest.param("largo", "0", "mayor que 0", id="largo_cero"),
    pytest.param("largo", "-5", "mayor que 0", id="largo_negativo"),
    pytest.param("largo", "2000000", "máximo", id="largo_enorme"),
    pytest.param("angulo", "2000000", "ángulo", id="angulo_enorme"),
    pytest.param("lados", "0", "entre 3 y 64", id="lados_cero"),
    pytest.param("lados", "-5", "entre 3 y 64", id="lados_negativo"),
    pytest.param("lados", "1000000000", "entre 3 y 64", id="lados_enorme"),
]


def _abrir(app_qt, campo, texto):
    """Caja del campo abierta tras el primer clic; recoge avisos y excepciones al Aceptar."""
    lz = T._lienzo(app_qt)
    avisos = []
    lz.mensaje.connect(avisos.append)
    lz.grab()
    lz.set_herramienta("poligono_arista")
    T._clic(lz, *ORIGEN)
    T._mover(lz, *EXTREMO)
    assert lz._claves_vivas() == ["largo", "angulo", "lados"]
    lz._activo = INDICE[campo]
    lz._editar_campo_vivo("0")
    ed = lz.entrada
    assert ed is not None and len(ed.campos) == 1
    widget = ed.campos[0]
    QTest.keyClick(widget, Qt.Key_A, Qt.ControlModifier)
    if texto:
        QTest.keyClicks(widget, texto)
    else:
        QTest.keyClick(widget, Qt.Key_Backspace)
    avisos.clear()
    fallos = []
    try:
        QTest.keyClick(widget, Qt.Key_Return)
    except Exception as e:  # noqa: BLE001
        fallos.append(f"{type(e).__name__}: {e}")
    lz.grab()
    return lz, avisos, fallos


def _lineas(lz):
    return [c for c in lz.b.curvas.values() if c.tipo == "linea" and not c.construccion]


def _largo(lz, linea):
    return math.dist(lz.b.coords(linea.p1), lz.b.coords(linea.p2))


def _sin_rotura(lz, avisos, fallos):
    assert not fallos, fallos
    assert QApplication.instance() is not None and lz.isVisible()
    assert resolver(lz.b).ok and lz.resultado.ok, avisos
    for mensaje in avisos:
        assert "\n" not in mensaje and "\r" not in mensaje, mensaje


def _un_renglon(avisos):
    assert len(avisos) == 1, avisos
    assert "\n" not in avisos[0] and "\r" not in avisos[0], avisos[0]
    return avisos[0]


@pytest.mark.parametrize(("campo", "texto", "esperado"), VALIDOS)
def test_valores_validos_de_sk_poligono_arista_crean_el_poligono(app_qt, campo, texto, esperado):
    lz, avisos, fallos = _abrir(app_qt, campo, texto)
    assert not avisos, avisos
    assert lz.entrada is None and len(lz.clics) == 2
    a, b = lz.clics[0][1], lz.clics[1][1]
    if campo == "largo":
        assert math.dist(a, b) == pytest.approx(esperado, abs=1e-6)
    elif campo == "angulo":
        angulo = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])) % 360
        assert angulo == pytest.approx(esperado % 360, abs=1e-6)
    lados = lz.lados
    T._clic(lz, *LADO)
    _sin_rotura(lz, avisos, fallos)
    lineas = _lineas(lz)
    assert len(lineas) == lados
    for linea in lineas:
        assert _largo(lz, linea) == pytest.approx(math.dist(a, b), abs=1e-6)


@pytest.mark.parametrize(("campo", "texto", "aviso"), INVALIDOS)
def test_valores_fuera_de_rango_avisan_y_no_dibujan(app_qt, campo, texto, aviso):
    lz, avisos, fallos = _abrir(app_qt, campo, texto)
    _sin_rotura(lz, avisos, fallos)
    assert _lineas(lz) == [] and lz.entrada is not None and len(lz.clics) == 1
    assert aviso in _un_renglon(avisos).lower()
    lz.entrada.cancelado.emit()
    lz.set_herramienta("seleccionar")


@pytest.mark.parametrize("texto", ["6 mm", "2*3"])
def test_lados_con_unidad_o_expresion_avisa_en_espanol(app_qt, texto):
    """Con unidad o expresión avisa en español o acepta el valor (falta el clic de orientación); nunca error crudo."""
    lz, avisos, fallos = _abrir(app_qt, "lados", texto)
    _sin_rotura(lz, avisos, fallos)
    if _lineas(lz):
        assert lz.entrada is None and not avisos
        assert len(_lineas(lz)) == 6
    elif not avisos:
        assert lz.entrada is None
    else:
        assert lz.entrada is not None
        mensaje = _un_renglon(avisos)
        assert "could not convert" not in mensaje.lower()
        assert "lados" in mensaje.lower()

# -*- coding: utf-8 -*-
"""Valores raros de los campos «radio» y «lados» del comando de boceto «sk_poligono_inscrito».

La ayuda de Fusion (`create polygons in sketches`) fija el orden Radio → Lados (Tab) y que ambos son valores
escritos. Acá cada campo se prueba vacío, 0, negativo, enorme, con unidades y con expresión. Aceptar nunca
cierra la app ni deja el boceto roto, y todo aviso cabe en un renglón. Con unidad o expresión en «lados»
se evalúa el campo y, si no se puede, avisa en español (B-800).
"""
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

CENTRO = (0, 0)
VERTICE = (10, 0)
INDICE = {"radio": 0, "lados": 1}


def _abrir(app_qt, campo, texto):
    """Caja del campo abierta tras el clic central y el arrastre; recoge avisos y excepciones al Aceptar."""
    lz = T._lienzo(app_qt)
    avisos = []
    lz.mensaje.connect(avisos.append)
    lz.grab()
    lz.set_herramienta("poligono_inscrito")
    T._clic(lz, *CENTRO)
    T._mover(lz, *VERTICE)
    lz._activo = INDICE[campo]
    lz._editar_campo_vivo("0")
    ed = lz.entrada
    assert ed is not None and len(ed.campos) == 1
    campo_widget = ed.campos[0]
    QTest.keyClick(campo_widget, Qt.Key_A, Qt.ControlModifier)
    if texto:
        QTest.keyClicks(campo_widget, texto)
    else:
        QTest.keyClick(campo_widget, Qt.Key_Backspace)
    avisos.clear()                                  # el cartel de la herramienta no es un aviso de error
    fallos = []
    try:
        QTest.keyClick(campo_widget, Qt.Key_Return)
    except Exception as e:  # noqa: BLE001 — cualquier excepción aquí es un bug: Aceptar no puede tumbar la app
        fallos.append(f"{type(e).__name__}: {e}")
    lz.grab()                                       # redibuja: Aceptar no puede cerrar la app
    return lz, avisos, fallos


def _lineas(lz):
    return [c for c in lz.b.curvas.values() if c.tipo == "linea"]


def _radio(lz):
    circulos = [c for c in lz.b.curvas.values() if c.tipo == "circulo"]
    return circulos[0].radio if circulos else None


def _sin_rotura(lz, avisos, fallos):
    assert not fallos, fallos
    assert QApplication.instance() is not None and lz.isVisible()
    assert resolver(lz.b).ok and lz.resultado.ok, avisos   # el boceto sigue siendo resoluble
    for mensaje in avisos:
        assert "\n" not in mensaje and "\r" not in mensaje, mensaje


def _un_renglon(avisos):
    assert len(avisos) == 1, avisos
    assert "\n" not in avisos[0] and "\r" not in avisos[0], avisos[0]
    return avisos[0]


# ---------------------------------------------------------------- VACÍO
@pytest.mark.parametrize("campo", ["radio", "lados"])
def test_campo_vacio_usa_el_valor_del_raton(app_qt, campo):
    lz, avisos, fallos = _abrir(app_qt, campo, "")
    _sin_rotura(lz, avisos, fallos)
    assert not avisos, avisos
    assert len(_lineas(lz)) == 6 and _radio(lz) == pytest.approx(10)
    assert lz.entrada is None and not lz.clics


# ---------------------------------------------------------------- CERO, NEGATIVO Y ENORME
FUERA_DE_RANGO = [
    ("radio", "0", "mayor que 0"),
    ("radio", "-5", "mayor que 0"),
    ("radio", "1e9", "máximo"),
    ("lados", "0", "entre 3 y 64"),
    ("lados", "-5", "entre 3 y 64"),
    ("lados", "1e9", "entre 3 y 64"),
]


@pytest.mark.parametrize("campo,valor,aviso", FUERA_DE_RANGO)
def test_valor_fuera_de_rango_avisa_y_no_dibuja(app_qt, campo, valor, aviso):
    lz, avisos, fallos = _abrir(app_qt, campo, valor)
    _sin_rotura(lz, avisos, fallos)
    assert _lineas(lz) == [] and _radio(lz) is None
    assert lz.entrada is not None
    assert aviso in _un_renglon(avisos)


# ---------------------------------------------------------------- UNIDADES Y EXPRESIÓN
@pytest.mark.parametrize("texto", ["6 mm", "2*3"])
def test_radio_con_unidad_o_expresion_crea_la_cota(app_qt, texto):
    lz, avisos, fallos = _abrir(app_qt, "radio", texto)
    _sin_rotura(lz, avisos, fallos)
    assert not avisos, avisos
    assert len(_lineas(lz)) == 6 and _radio(lz) == pytest.approx(6)
    assert lz.entrada is None and not lz.clics


@pytest.mark.parametrize("texto", ["6 mm", "2*3"])
def test_lados_con_unidad_o_expresion_avisa_en_espanol(app_qt, texto):
    """Con unidad o expresión dibuja o avisa en español, nunca el error crudo de Python (B-800)."""
    lz, avisos, fallos = _abrir(app_qt, "lados", texto)
    _sin_rotura(lz, avisos, fallos)
    if _lineas(lz):
        assert lz.entrada is None and not avisos
        assert len(_lineas(lz)) == 6 and _radio(lz) == pytest.approx(10)
    else:
        mensaje = _un_renglon(avisos)
        assert "could not convert" not in mensaje.lower()
        assert "lados" in mensaje.lower()

# -*- coding: utf-8 -*-
"""Valores raros del comando de boceto «sk_conica»: el campo Rho de su barra en vacío, 0, negativo, enorme,
con unidades y con expresión. Aceptar nunca cierra la app ni deja el boceto roto, y todo aviso es de un renglón.
La ayuda de Fusion (`create conic curves in sketches`) fija Rho como valor de forma entre 0 y 1.
Hoy fallan las unidades y las expresiones (B-716)."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import test_boceto_interaccion as T  # noqa: E402
from omnicad.restricciones import Boceto, resolver  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

app_qt = T.app_qt
_cerrar_lienzos = T._cerrar_lienzos

PUNTOS = ((0, 0), (20, 0), (10, 10))


def _abrir(app_qt, rho):
    """Barra de Rho abierta tras los 3 clics; recoge avisos y excepciones al Aceptar."""
    lz = T._lienzo(app_qt, Boceto())
    avisos = []
    lz.mensaje.connect(avisos.append)
    lz.grab()
    lz.set_herramienta("conica")
    for xy in PUNTOS:
        T._clic(lz, *xy)
    assert len(lz.clics) == 3 and lz.entrada is not None, "los 3 clics abren la caja de Rho"
    lz.entrada.campos[0].setText(rho)
    avisos.clear()                                  # el cartel de la herramienta no es un aviso de error
    fallos = []
    try:
        lz.entrada.aceptado.emit([rho])
    except Exception as e:  # noqa: BLE001 — cualquier excepción aquí es un bug: Aceptar no puede tumbar la app
        fallos.append(f"{type(e).__name__}: {e}")
    lz.grab()                                       # redibuja: Aceptar no puede cerrar la app
    return lz, avisos, fallos


def _conicas(lz):
    return [c for c in lz.b.curvas.values() if c.tipo == "conica"]


def _sin_rotura(lz, avisos, fallos):
    assert not fallos, fallos
    assert QApplication.instance() is not None and lz.isVisible()
    resolver(lz.b)                                  # el boceto sigue siendo resoluble
    assert lz.resultado.ok, avisos
    for mensaje in avisos:
        assert "\n" not in mensaje and "\r" not in mensaje, mensaje


def _un_renglon(avisos):
    assert len(avisos) == 1, avisos
    assert "\n" not in avisos[0] and "\r" not in avisos[0], avisos[0]
    return avisos[0]


# ---------------------------------------------------------------- VACÍO
def test_campo_vacio_usa_rho_por_defecto(app_qt):
    lz, avisos, fallos = _abrir(app_qt, "")
    _sin_rotura(lz, avisos, fallos)
    assert not avisos, avisos
    (curva,) = _conicas(lz)
    assert curva.rho == pytest.approx(0.5)
    assert lz.entrada is None and not lz.clics


# ---------------------------------------------------------------- CERO, NEGATIVO Y ENORME
@pytest.mark.parametrize("rho", ["0", "-0.5", "-1", "1", "1e9", "1000000000"])
def test_rho_fuera_de_rango_avisa_y_no_dibuja(app_qt, rho):
    lz, avisos, fallos = _abrir(app_qt, rho)
    _sin_rotura(lz, avisos, fallos)
    assert _conicas(lz) == [] and lz.entrada is not None
    assert "rho" in _un_renglon(avisos).lower()


# ---------------------------------------------------------------- UNIDADES Y EXPRESIÓN
B716 = "B-716: Rho usa _numero (float) en vez de evaluar: unidades y expresiones muestran el error crudo de Python"


@pytest.mark.parametrize("rho,esperado", [("0.5 mm", 0.5), ("50 %", 0.5)])
def test_rho_con_unidad_acepta_o_rechaza_en_espanol(app_qt, rho, esperado):
    lz, avisos, fallos = _abrir(app_qt, rho)
    _sin_rotura(lz, avisos, fallos)
    curvas = _conicas(lz)
    if curvas:
        assert lz.entrada is None and not avisos
        assert curvas[0].rho == pytest.approx(esperado)
    else:
        texto = _un_renglon(avisos)
        assert "rho" in texto.lower() and "could not convert" not in texto.lower()


@pytest.mark.parametrize("rho,esperado", [("1/2", 0.5), ("0.25*2", 0.5)])
def test_rho_con_expresion_dibuja_la_conica(app_qt, rho, esperado):
    lz, avisos, fallos = _abrir(app_qt, rho)
    _sin_rotura(lz, avisos, fallos)
    assert not avisos, avisos
    (curva,) = _conicas(lz)
    assert curva.rho == pytest.approx(esperado)
    assert lz.entrada is None and not lz.clics

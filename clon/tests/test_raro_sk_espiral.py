# -*- coding: utf-8 -*-
"""Valores raros del comando de boceto «sk_espiral»: cada campo de su diálogo (Vueltas y Paso) en vacío, 0,
negativo, enorme, con unidades y con expresión. Aceptar nunca cierra la app ni deja el boceto roto, y todo aviso
es de un renglón. Hoy fallan Vueltas con expresión/unidad (B-714) y un Paso enorme (B-715)."""
import math
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import test_boceto_interaccion as T  # noqa: E402
from omnicad.restricciones.boceto import Boceto  # noqa: E402

app_qt = T.app_qt
_cerrar_lienzos = T._cerrar_lienzos


def _abrir(app_qt, vueltas, paso):
    """Caja de Vueltas/Paso abierta tras los 2 clics, con los avisos de la barra recogidos."""
    lz = T._lienzo(app_qt, Boceto())
    avisos = []
    lz.mensaje.connect(avisos.append)
    lz.grab()
    lz.set_herramienta("espiral")
    T._clic(lz, 0, 0)
    T._clic(lz, 12, 0)
    assert lz.entrada is not None, "los 2 clics abren la caja de Vueltas/Paso"
    avisos.clear()                                  # el cartel de la herramienta no es un aviso de error
    lz.entrada.aceptado.emit([vueltas, paso])
    lz.grab()                                       # redibuja: aceptar no puede cerrar la app
    return lz, avisos


def _curvas(lz):
    return [c for c in lz.b.curvas.values() if c.id > 0]


def _radio_final(lz):
    (c,) = _curvas(lz)
    return math.dist(lz.b.coords(c.pts[-1]), (0, 0))


def _un_renglon(avisos):
    assert len(avisos) == 1, avisos
    assert "\n" not in avisos[0] and "\r" not in avisos[0], avisos[0]
    return avisos[0]


# ---------------------------------------------------------------- VACÍO
@pytest.mark.parametrize("vueltas,paso", [("", "2"), ("3", "")])
def test_campo_vacio_crea_una_espiral_valida(app_qt, vueltas, paso):
    lz, avisos = _abrir(app_qt, vueltas, paso)
    assert not avisos, avisos
    assert len(_curvas(lz)) == 1 and _curvas(lz)[0].tipo == "spline"
    assert math.isfinite(_radio_final(lz)) and _radio_final(lz) > 0
    assert lz.entrada is None and lz.resultado.ok


# ---------------------------------------------------------------- CERO Y NEGATIVO
@pytest.mark.parametrize("vueltas", ["0", "-2"])
def test_vueltas_cero_o_negativas_avisan_y_no_dibujan(app_qt, vueltas):
    lz, avisos = _abrir(app_qt, vueltas, "2")
    assert _curvas(lz) == [] and lz.entrada is not None
    assert "vueltas" in _un_renglon(avisos).lower()
    assert lz.resultado.ok


@pytest.mark.parametrize("paso,radio", [("0", 12.0), ("-2", 6.0), ("-2 mm", 6.0)])
def test_paso_cero_o_negativo_dibuja_una_espiral_valida(app_qt, paso, radio):
    lz, avisos = _abrir(app_qt, "3", paso)
    assert not avisos, avisos
    assert len(_curvas(lz)) == 1
    assert _radio_final(lz) == pytest.approx(radio)
    assert lz.resultado.ok


# ---------------------------------------------------------------- ENORME
def test_vueltas_enormes_avisan_y_no_dibujan(app_qt):
    lz, avisos = _abrir(app_qt, "5000", "2")
    assert _curvas(lz) == [] and lz.entrada is not None
    assert "vueltas" in _un_renglon(avisos).lower()
    assert lz.resultado.ok


@pytest.mark.parametrize("paso", ["1e9", "1000000000"])
def test_paso_enorme_avisa_y_no_dibuja(app_qt, paso):
    lz, avisos = _abrir(app_qt, "3", paso)
    assert _curvas(lz) == [], "un Paso enorme no puede crear geometría fuera de MEDIDA_MAXIMA"
    assert lz.entrada is not None
    texto = _un_renglon(avisos)
    assert "paso" in texto.lower() or "mm" in texto.lower()
    assert lz.resultado.ok


# ---------------------------------------------------------------- UNIDADES Y EXPRESIÓN
@pytest.mark.parametrize("paso,radio", [("10 mm", 42.0), ("1 cm", 42.0), ("2*3", 30.0), ("3+1", 24.0)])
def test_paso_con_unidades_o_expresion_dibuja_una_espiral_valida(app_qt, paso, radio):
    lz, avisos = _abrir(app_qt, "3", paso)
    assert not avisos, avisos
    assert len(_curvas(lz)) == 1
    assert _radio_final(lz) == pytest.approx(radio)
    assert lz.resultado.ok


@pytest.mark.xfail(strict=True, reason="B-714: Vueltas usa float() y no evaluar(); «3+1» no se evalúa")
def test_vueltas_con_expresion_dibuja_la_espiral(app_qt):
    lz, avisos = _abrir(app_qt, "3+1", "2")
    assert not avisos, avisos
    assert len(_curvas(lz)) == 1
    assert _radio_final(lz) == pytest.approx(20.0)          # 12 + 4·2
    assert lz.resultado.ok


@pytest.mark.xfail(strict=True, reason="B-714: «3 mm» filtra el ValueError de Python en vez de avisar en español")
def test_vueltas_con_unidad_avisa_en_un_renglon_en_espanol(app_qt):
    lz, avisos = _abrir(app_qt, "3 mm", "2")
    assert _curvas(lz) == []
    texto = _un_renglon(avisos)
    assert "vueltas" in texto.lower()
    assert "could not convert" not in texto.lower()

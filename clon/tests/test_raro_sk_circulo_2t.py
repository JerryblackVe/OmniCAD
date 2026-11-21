# -*- coding: utf-8 -*-
"""Valores raros del comando de boceto «sk_circulo_2t»: el campo R de su barra (radio del círculo tangente
a 2 líneas) en vacío, cero, negativo, enorme, con unidades y con expresión. Aceptar nunca cierra la app ni deja
el boceto roto, y todo aviso es de un solo renglón."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import test_boceto_interaccion as T  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402
from omnicad.restricciones import Boceto, resolver  # noqa: E402

app_qt = T.app_qt
_cerrar_lienzos = T._cerrar_lienzos


def _abrir(app_qt, valor):
    """Barra de R abierta tras elegir 2 líneas y escribir un número; recoge avisos y excepciones al Aceptar."""
    lz = T._lienzo(app_qt, Boceto())
    l1 = lz.b.agregar_linea((0.0, 0.0), (20.0, 0.0))
    l2 = lz.b.agregar_linea((0.0, 0.0), (0.0, 20.0))
    avisos = []
    lz.mensaje.connect(avisos.append)
    lz.grab()
    lz.set_herramienta("circulo_2t")
    lz.agregar_pick(l1, (10.0, 0.0))
    lz.agregar_pick(l2, (0.0, 10.0))
    T._mover(lz, 4.0, 4.0)
    QTest.keyClick(lz, "1")
    QApplication.instance().processEvents()
    assert lz.entrada is not None, "escribir un número abre la barra de R"
    lz.entrada.campos[0].setText(valor)
    avisos.clear()  # el cartel de la herramienta no es un aviso de error
    fallos = []
    try:
        lz.entrada.aceptado.emit([valor])
    except Exception as e:  # noqa: BLE001 — cualquier excepción aquí es un bug
        fallos.append(f"{type(e).__name__}: {e}")
    lz.grab()
    return lz, avisos, fallos


def _circulos(lz):
    return [c for c in lz.b.curvas.values() if c.tipo == "circulo"]


def _sin_rotura(lz, avisos, fallos):
    assert not fallos, fallos
    assert QApplication.instance() is not None and lz.isVisible()
    resolver(lz.b)
    assert lz.resultado.ok, avisos
    for mensaje in avisos:
        assert "\n" not in mensaje and "\r" not in mensaje, mensaje


CASOS = [
    ("", False),
    ("0", False),
    ("-5", False),
    ("1e9", False),
    ("5 mm", True),
    ("5*2", True),
]


@pytest.mark.parametrize(("valor", "valido"), CASOS, ids=lambda v: str(v))
def test_valores_raros_de_sk_circulo_2t_no_rompen_el_boceto(app_qt, valor, valido):
    lz, avisos, fallos = _abrir(app_qt, valor)
    _sin_rotura(lz, avisos, fallos)

    if not valido:
        assert lz.entrada is not None, (valor, lz.entrada is not None)
        assert _circulos(lz) == [], (valor, len(_circulos(lz)))
        assert avisos, (valor, avisos)
        mensaje = avisos[-1]
        assert "\n" not in mensaje and "\r" not in mensaje, mensaje
        if lz.entrada is not None:
            lz.entrada.cancelado.emit()
            QApplication.instance().processEvents()
    else:
        assert lz.entrada is None, (valor, lz.entrada is not None)
        assert not avisos, (valor, avisos)
        assert len(_circulos(lz)) == 1, (valor, len(_circulos(lz)))

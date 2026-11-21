# -*- coding: utf-8 -*-
"""Valores raros del comando de boceto «sk_ranura_total»: los campos Largo, Ángulo y Ancho de su barra en
vacío, 0, negativo, enorme, con unidades y con expresión. Aceptar nunca cierra la app ni deja el boceto roto,
y todo aviso es de un renglón."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

import test_boceto_interaccion as T  # noqa: E402
from omnicad.restricciones import Boceto, resolver  # noqa: E402

app_qt = T.app_qt
_cerrar_lienzos = T._cerrar_lienzos


def _escribir_return(widget, texto):
    QTest.keyClick(widget, Qt.Key_A, Qt.ControlModifier)
    if texto:
        QTest.keyClicks(widget, texto)
    else:
        QTest.keyClick(widget, Qt.Key_Backspace)
    QTest.keyClick(widget, Qt.Key_Return)


def _abrir_campo(lz, campo):
    if campo == "angulo":
        lz._activo = 1
    lz._editar_campo_vivo("0")
    assert lz.entrada is not None
    return lz.entrada.campos[0]


def _completar_ancho(lz):
    T._mover(lz, 10, 3)
    lz._editar_campo_vivo("0")
    assert lz.entrada is not None
    _escribir_return(lz.entrada.campos[0], "4")
    QApplication.instance().processEvents()


CASOS = [
    # (campo, texto, valido)
    ("largo", "", True),
    ("largo", "0", False),
    ("largo", "-5", False),
    ("largo", "2000000", False),
    ("largo", "20 mm", True),
    ("largo", "30 deg", False),
    ("largo", "5*2", True),
    ("angulo", "", True),
    ("angulo", "0", True),
    ("angulo", "-5", True),
    ("angulo", "2000000", False),
    ("angulo", "30 deg", True),
    ("angulo", "5 mm", False),
    ("angulo", "5*2", True),
    ("ancho", "", True),
    ("ancho", "0", False),
    ("ancho", "-5", False),
    ("ancho", "2000000", False),
    ("ancho", "10 mm", True),
    ("ancho", "30 deg", False),
    ("ancho", "5*2", True),
]


@pytest.mark.parametrize(("campo", "texto", "valido"), CASOS,
                         ids=[f"{c}_{t or 'vacio'}" for c, t, _ in CASOS])
def test_valores_raros_de_sk_ranura_total_no_rompen_el_boceto(app_qt, campo, texto, valido):
    lz = T._lienzo(app_qt, Boceto())
    mensajes = []
    lz.mensaje.connect(mensajes.append)
    lz.set_herramienta("ranura_total")
    T._clic(lz, 0, 0)
    T._mover(lz, 20, 0)
    antes_curvas = len(lz.b.curvas)

    if campo in ("largo", "angulo"):
        widget = _abrir_campo(lz, campo)
        entrada = lz.entrada
        _escribir_return(widget, texto)
        QApplication.instance().processEvents()

        assert QApplication.instance() is not None
        assert lz.isVisible()
        try:
            resolver(lz.b)
        except Exception as e:  # noqa: BLE001
            pytest.fail(f"resolver crashed after {campo}={texto!r}: {e}")

        if not valido:
            assert lz.entrada is entrada, (campo, texto)
            assert len(lz.b.curvas) == antes_curvas, (campo, texto)
            assert lz.resultado.ok, (campo, texto)
            assert mensajes, (campo, texto)
            msg = mensajes[-1]
            assert "\n" not in msg and "\r" not in msg, msg
            # recuperar con un valor válido para avanzar al siguiente paso
            _escribir_return(widget, "20" if campo == "largo" else "30")
            QApplication.instance().processEvents()
        else:
            assert lz.entrada is None, (campo, texto)
            assert lz.resultado.ok, (campo, texto)
        # completar el segundo paso (ancho) para dejar el boceto con geometría
        _completar_ancho(lz)
    else:  # ancho
        # avanzar el primer paso con un valor válido
        w1 = _abrir_campo(lz, "largo")
        _escribir_return(w1, "40")
        QApplication.instance().processEvents()
        assert lz.entrada is None
        T._mover(lz, 10, 3)
        antes_curvas = len(lz.b.curvas)
        lz._editar_campo_vivo("0")
        assert lz.entrada is not None
        widget = lz.entrada.campos[0]
        entrada = lz.entrada
        _escribir_return(widget, texto)
        QApplication.instance().processEvents()

        assert QApplication.instance() is not None
        assert lz.isVisible()
        try:
            resolver(lz.b)
        except Exception as e:  # noqa: BLE001
            pytest.fail(f"resolver crashed after ancho={texto!r}: {e}")

        if not valido:
            assert lz.entrada is entrada, ("ancho", texto)
            assert len(lz.b.curvas) == antes_curvas, ("ancho", texto)
            assert lz.resultado.ok, ("ancho", texto)
            assert mensajes, ("ancho", texto)
            msg = mensajes[-1]
            assert "\n" not in msg and "\r" not in msg, msg
            _escribir_return(widget, "10")
            QApplication.instance().processEvents()
        else:
            assert lz.entrada is None, ("ancho", texto)
            assert lz.resultado.ok, ("ancho", texto)

    QApplication.instance().processEvents()
    assert lz.resultado.ok
    assert len(lz.b.curvas) > 0
    try:
        resolver(lz.b)
    except Exception as e:  # noqa: BLE001
        pytest.fail(f"resolver crashed at end: {e}")

# -*- coding: utf-8 -*-
"""Valores raros del comando de boceto «sk_ranura_punto»: los campos Largo, Ángulo y Ancho de su barra de
valores en vacío, 0, negativo, enorme, con unidades y con expresión. Aceptar nunca cierra la app ni deja el
boceto roto, y todo aviso es de un renglón. La ayuda de Fusion (create-slots-in-a-sketch-*.md) pide distancia,
ángulo y ancho; en OmniCAD son los campos vivos `largo`, `angulo` y `ancho` de `editor_boceto_cotas.py`."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import test_boceto_interaccion as T  # noqa: E402
from omnicad.restricciones import Boceto, resolver  # noqa: E402
from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

app_qt = T.app_qt
_cerrar_lienzos = T._cerrar_lienzos

# (campo, valor tecleado, ¿se acepta y cierra la caja?)
CASOS = [
    ("largo", "", True),
    ("largo", "0", False),
    ("largo", "-5", False),
    ("largo", "2000000", False),
    ("largo", "20 mm", True),
    ("largo", "30 deg", False),                 # unidad de ángulo en un campo de longitud
    ("largo", "5*2", True),
    ("angulo", "", True),
    ("angulo", "0", True),
    ("angulo", "-5", True),
    ("angulo", "2000000", False),
    ("angulo", "30 deg", True),
    ("angulo", "20 mm", False),
    ("angulo", "5*2", True),
    ("ancho", "", True),
    ("ancho", "0", False),
    ("ancho", "-5", False),
    ("ancho", "2000000", False),
    ("ancho", "20 mm", True),
    ("ancho", "30 deg", False),
    ("ancho", "5*2", True),
]


def _abrir(lz, campo):
    """Deja abierta la caja del campo pedido del ranura_punto (centro, extremo y ancho)."""
    lz.set_herramienta("ranura_punto")
    T._clic(lz, 0, 0)
    T._mover(lz, 20, 0)
    if campo == "ancho":
        T._clic(lz, 20, 0)
        T._mover(lz, 20, 6)
    claves = lz._claves_vivas()
    assert campo in claves, (campo, claves)
    lz._activo = claves.index(campo)
    lz._editar_campo_vivo("")
    assert lz.entrada is not None


@pytest.mark.parametrize(("campo", "texto", "valido"), CASOS, ids=[f"{c}_{t or 'vacio'}" for c, t, _ in CASOS])
def test_raro_sk_ranura_punto(app_qt, campo, texto, valido):
    lz = T._lienzo(app_qt, Boceto())
    avisos = []
    lz.mensaje.connect(avisos.append)
    antes = lz.b.a_dict()
    _abrir(lz, campo)
    avisos.clear()
    caja = lz.entrada.campos[0]
    caja.setText(texto)
    QTest.keyClick(caja, Qt.Key_Return)
    QApplication.instance().processEvents()

    assert QApplication.instance() is not None and lz.isVisible()
    assert all("\n" not in m and "\r" not in m for m in avisos), (campo, texto, avisos)
    try:
        resultado = resolver(lz.b)
    except Exception as e:  # noqa: BLE001 — un valor raro no puede tumbar el solver
        pytest.fail(f"resolver crashed after {campo}={texto!r}: {e}")
    assert resultado.ok, (campo, texto, "el boceto quedó roto")

    if valido:
        assert lz.entrada is None, (campo, texto)
        assert not avisos, (campo, texto, avisos)
        if campo == "ancho":
            curvas = [c for c in lz.b.curvas.values() if c.id > 0]
            assert sorted(c.tipo for c in curvas) == ["arco", "arco", "linea", "linea", "linea"], (campo, texto)
            if texto:
                assert len(lz.b.cotas) == 1, (campo, texto)
        elif texto:
            assert lz._bloqueos[campo][0] == texto, (campo, texto, lz._bloqueos)
    else:
        assert lz.entrada is not None, (campo, texto)
        assert lz.b.a_dict() == antes, (campo, texto, "el valor rechazado cambió el boceto")
        assert len(avisos) == 1, (campo, texto, avisos)
        esperado = "ángulo" if campo == "angulo" else ("longitud" if "unidad" in avisos[0] else "distancia")
        assert esperado in avisos[0].lower(), (campo, texto, avisos)
        lz.entrada.cancelado.emit()
        QApplication.instance().processEvents()

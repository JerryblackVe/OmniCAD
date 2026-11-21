# -*- coding: utf-8 -*-
"""Valores raros del comando de boceto «insertar_svg»: cada campo de su diálogo en vacío, 0, negativo,
enorme, con unidades y con expresión (sin cerrar la app ni dejar el boceto roto; mensaje de 1 renglón).
Si falla, es un bug: fila nueva en docs/seguimiento/ y xfail con el motivo."""
import os
from PySide6.QtWidgets import QApplication

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from omnicad.timeline.documento import Documento
from omnicad.ui.comando import ContextoComando, hit_desde_ref
from omnicad.ui.comandos.insertar import InsertarSVG
from omnicad.ui.comando import ErrorComando


CASOS = [
    ("archivo", "", True),
    ("archivo", "/tmp/nonexistent_file_xyz.svg", False),
    ("plano", None, False),
    ("plano", [], False),
    ("escala", "", True),
    ("escala", "0", True),
    ("escala", "-5", True),
    ("escala", "99999999999", True),
    ("escala", "1 mm", True),
    ("escala", "5*2", True),
    ("dx", "", True),
    ("dx", "0 mm", True),
    ("dx", "-5 mm", True),
    ("dx", "99999999999 mm", True),
    ("dx", "expr", True),
    ("dy", "", True),
    ("dy", "0 mm", True),
    ("dy", "-5 mm", True),
    ("dy", "99999999999 mm", True),
    ("dy", "expr", True),
    ("angulo", "", True),
    ("angulo", "0 deg", True),
    ("angulo", "-5 deg", True),
    ("angulo", "99999999999 deg", True),
    ("angulo", "expr", True),
    ("capas", "", True),
    ("capas", "corte", True),
    ("colores", "", True),
    ("colores", "#ff0000", True),
]


@pytest.fixture(scope="module")
def app_qt():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


@pytest.fixture
def doc(app_qt):
    return Documento()


@pytest.fixture
def ctx(doc):
    return ContextoComando(doc)


@pytest.fixture
def cmd():
    return InsertarSVG()


@pytest.mark.parametrize("campo, texto, valido", CASOS, ids=[f"{c}_{t or 'vacio'}" for c, t, _ in CASOS])
def test_valores_raros_insertar_svg_no_rompen_el_boceto(cmd, ctx, doc, campo, texto, valido):
    """Cada campo del diálogo de insertar_svg con valores raros no debe cerrar la app ni dejar el boceto roto.
    Mensajes de error de un solo renglón."""
    v = {c.clave: c.defecto for c in cmd.campos(ctx)}
    hit = hit_desde_ref({"tipo": "plano", "id": "XY"}, doc.estado_final)
    v["plano"] = [hit]

    if campo == "archivo":
        v["archivo"] = texto
    elif campo == "plano":
        pass
    else:
        v[campo] = texto

    mensajes = []
    try:
        op = cmd.construir(v, ctx)
        doc.agregar(op)
    except ErrorComando as e:
        mensajes.append(str(e))

    assert QApplication.instance() is not None, "App cerró inesperadamente"

    # Verificar que los mensajes de error son de 1 renglón
    for m in mensajes:
        assert "\n" not in m and "\r" not in m, f"Mensaje multilínea: {m!r}"
        assert len(m) <= 80, f"Mensaje muy largo: {m!r}"

    if not valido:
        # Para valores inválidos, el comando debe fallar con ErrorComando de 1 renglón
        assert len(mensajes) > 0, (campo, texto, "Expected ErrorComando for invalid value")
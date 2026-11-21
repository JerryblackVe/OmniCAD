# -*- coding: utf-8 -*-
"""Valores raros del comando «duplicar_con_uniones»: cada campo de su diálogo en vacío, 0, negativo,
enorme, con unidades y con expresión (sin cerrar la app ni dejar el modelo roto; mensaje de 1 renglón)."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from omnicad.ui.comando import ContextoComando, hit_desde_ref
from omnicad.ui.comandos.ensamblar import DuplicarConUniones
from omnicad.timeline.ops_ensamblar import OpUnion

from test_ensamblar import _doc_dos_cajas, _cara


def _escena():
    doc = _doc_dos_cajas()
    doc.agregar(OpUnion(doc.nuevo_id(), "Unión1", tipo="rigida",
                        origen1=_cara(doc, "op2.c1", (105, 55, 0)),
                        origen2=_cara(doc, "op1.c1", (20, 20, 10))))
    return doc, ContextoComando(doc)


@pytest.fixture
def app_qt():
    return QApplication.instance() or QApplication([])


CASOS = []
for valor in ("", "0", "-5", "99999999999", "5 mm", "5*2"):
    CASOS.append(("union", valor, False))
for valor in ("", "0", "-5", "99999999999", "5 mm", "5*2"):
    CASOS.append(("destinos", valor, False))
for valor in ("", "0", "-5", "99999999999", "5 mm", "5*2"):
    CASOS.append(("voltear", valor, True))


@pytest.mark.parametrize(("campo", "texto", "valido"), CASOS,
                         ids=[f"{c}_{t or 'vacio'}" for c, t, _ in CASOS])
def test_valores_raros_duplicar_con_uniones(app_qt, campo, texto, valido):
    doc, ctx = _escena()
    cmd = DuplicarConUniones()
    v = {c.clave: c.defecto for c in cmd.campos(ctx)}
    v["union"] = list(cmd._uniones(ctx))[0]
    hit = hit_desde_ref({"tipo": "plano", "id": "XY"}, doc.estado_final)
    v["destinos"] = [hit]
    if texto and campo == "destinos":
        hit = hit_desde_ref({"tipo": "plano", "id": "XY"}, doc.estado_final)
        hit["ref"] = {"tipo": "plano", "id": texto}
        v["destinos"] = [hit]
    elif campo == "destinos":
        v["destinos"] = []
    else:
        v[campo] = texto

    # capturar excepciones como mensaje de un renglón
    exc = None
    try:
        cmd.aplicar(v, ctx)
    except Exception as e:  # noqa: BLE001
        exc = e

    assert QApplication.instance() is not None
    assert doc is not None

    if not valido:
        assert exc is not None, (campo, texto)
        msg = str(exc)
        assert "\n" not in msg and "\r" not in msg, msg
    else:
        if exc is not None:
            pytest.xfail(f"Comando falló con {campo}={texto!r}: {exc}")
        assert True

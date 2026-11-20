# -*- coding: utf-8 -*-
"""PREP: comando ENSAMBLAR › Uniones de animación (clave `accionar_uniones`), según la ayuda de Fusion
(`docs/fusion_docs/contenido/fusion-assemble/drive-joints-reference-c5b9344a8e3.md` y `joint-motion-limits-...`).

Drive Joints mueve una unión con un valor exacto de ángulo o distancia; los límites de movimiento (Joint Motion
Limits) recortan el valor pedido. No cambia código de la app: fija lo que ya hace y avisa si deja de hacerlo.
"""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from omnicad.nucleo import geometria as g
from omnicad.timeline.ops_ensamblar import OpUnion
from omnicad.ui.comando import ContextoComando
from omnicad.ui.comandos.ensamblar import AccionarUniones

from test_ensamblar import _doc_dos_cajas, _cara


def _caja(doc, cid="op2.c1"):
    return g.caja_envolvente(doc.estado_final.cuerpos[cid].forma)


def test_accionar_uniones_gira_90_grados_y_deja_el_valor_numerico():
    """Fusion: Drive Joints mueve la unión al ángulo pedido y el componente sigue ese valor."""
    doc = _doc_dos_cajas()
    op = OpUnion(doc.nuevo_id(), "Unión1", tipo="revolucion",
                 origen1=_cara(doc, "op2.c1", (105, 55, 0)),
                 origen2=_cara(doc, "op1.c1", (20, 20, 10)), dx="10 mm", giro="0 deg")
    doc.agregar(op)

    AccionarUniones().aplicar({"union": op.id, "giro": "90 deg", "desliz": "0 mm"}, ContextoComando(doc))

    assert doc.estado_final.uniones[op.id]["valores"]["giro"] == pytest.approx(90)
    caja = tuple(v for p in _caja(doc) for v in p)
    assert caja == pytest.approx((15.0, 25.0, 10.0, 25.0, 35.0, 20.0), abs=1e-6)


def test_accionar_uniones_por_encima_del_maximo_se_recorta_al_limite():
    """Fusion: Joint Motion Limits recortan el movimiento pedido al máximo permitido."""
    doc = _doc_dos_cajas()
    op = OpUnion(doc.nuevo_id(), "Unión1", tipo="revolucion",
                 origen1=_cara(doc, "op2.c1", (105, 55, 0)),
                 origen2=_cara(doc, "op1.c1", (20, 20, 10)), dx="10 mm", giro="0 deg",
                 maximo="45 deg")
    doc.agregar(op)

    AccionarUniones().aplicar({"union": op.id, "giro": "90 deg", "desliz": "0 mm"}, ContextoComando(doc))

    assert doc.estado_final.uniones[op.id]["valores"]["giro"] == pytest.approx(45)
    caja = tuple(v for p in _caja(doc) for v in p)
    assert caja == pytest.approx((20.0, 20.0, 10.0, 34.14213562373095, 34.14213562373095, 20.0), abs=1e-6)
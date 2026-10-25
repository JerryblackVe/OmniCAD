# -*- coding: utf-8 -*-
"""SOL-8 en el diálogo de Barrido: tipo «Cuerpo sólido» y selección de cadena."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from omnicad import api  # noqa: E402
from omnicad.nucleo import geometria as geo  # noqa: E402
from omnicad.ui.comando import ContextoComando, ErrorComando, hit_desde_ref  # noqa: E402
from omnicad.ui.comandos.crear import Barrido  # noqa: E402


def test_barrido_de_cuerpo_en_el_dialogo():
    QApplication.instance() or QApplication([])
    s = api.Sesion()
    for nombre, args in (("create_box", dict(length=10, width=10, height=10, name="Caja")),
                         ("create_sketch", dict(plane="XY", name="Ruta")),
                         ("draw_line", dict(start_x=0, start_y=0, end_x=40, end_y=0, sketch="Ruta"))):
        assert api.llamar(s, nombre, args)["ok"]
    doc = s.doc
    estado = doc.estado_final
    curva = api.llamar(s, "get_sketch", {"sketch": "Ruta"})["result"]["entities"][0]["id"]
    ruta = hit_desde_ref({"tipo": "curva_boceto", "boceto": "op2", "curva": curva}, estado)
    caja = hit_desde_ref({"tipo": "cuerpo", "cuerpo": "op1.c1"}, estado)
    cmd, ctx = Barrido(), ContextoComando(doc)
    v = {c.clave: c.defecto for c in cmd.campos(ctx)}
    assert {"cuerpos", "cadena"} <= set(v)
    v.update(tipo="cuerpo", ruta=[ruta], orientacion="paralela", operacion="nuevo")
    with pytest.raises(ErrorComando, match="cuerpo"):
        cmd.construir(v, ctx)                                                   # sin el cuerpo elegido
    v.update(cuerpos=[caja])
    op = cmd.construir(v, ctx)
    doc.agregar(op)
    nuevo = [c for c in doc.estado_final.cuerpos.values() if c.id != "op1.c1"][0]
    assert geo.volumen(nuevo.forma) == pytest.approx(10 * 10 * 50, rel=1e-3)
    reabierto = cmd.desde_op(op, ContextoComando(doc, op=op))
    assert reabierto["tipo"] == "cuerpo" and len(reabierto["cuerpos"]) == 1
    # torsión oculta: con «Cuerpo sólido» el campo no se ve, así que no puede hacer fallar el paso
    v.update(torsion="10 deg", conicidad="5 deg")
    assert cmd.construir(v, ctx).p["torsion"] == "0 deg"

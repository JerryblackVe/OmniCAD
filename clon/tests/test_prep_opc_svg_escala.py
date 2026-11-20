# -*- coding: utf-8 -*-
"""PREP: opción «Escala (Expresion)» del comando «Insertar SVG en boceto».

La ayuda de Fusion (Add an SVG image) describe «Scale» como un factor numérico que cambia el tamaño del
dibujo; el valor se teclea como expresión (`escala`). Se prueba un valor numérico y los bordes del
rango (escala no positiva y desborde del boceto de 1 km), sobre el código del comando en
`ui/comandos/insertar.py` y `ui/comandos/insertar_en_boceto.py`. No cambia código de la app.
"""
import os
from types import SimpleNamespace

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from omnicad.nucleo import geometria as geo
from omnicad.timeline.documento import Documento
from omnicad.ui.comando import ContextoComando, ErrorComando
from omnicad.ui.comandos.insertar import InsertarSVG
from omnicad.ui.comandos.insertar_en_boceto import InsertarEnBoceto

SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="10mm" height="10mm" viewBox="0 0 10 10">
  <line x1="0" y1="0" x2="10" y2="4"/>
</svg>"""


@pytest.fixture
def comando(tmp_path):
    ruta = tmp_path / "escala.svg"
    ruta.write_text(SVG, encoding="utf-8")
    lienzo = SimpleNamespace(plano=geo.Plano("XY"))
    return InsertarEnBoceto(InsertarSVG(), lienzo), ContextoComando(Documento()), str(ruta)


def _valores(ruta, escala):
    return {"archivo": ruta, "escala": escala, "dx": "0 mm", "dy": "0 mm", "angulo": "0 deg",
            "voltear_h": False, "voltear_v": False}


def _linea(boceto):
    lid = next(k for k, curva in boceto.curvas.items() if curva.tipo == "linea")
    return boceto._extremos_linea(lid)


def test_escala_expresion_numerica_escala_la_geometria(comando):
    cmd, ctx, ruta = comando
    base = cmd.boceto_previo(_valores(ruta, "1"), ctx)
    escalado = cmd.boceto_previo(_valores(ruta, "2"), ctx)
    (xa0, ya0), (xb0, yb0) = _linea(base)
    (xa1, ya1), (xb1, yb1) = _linea(escalado)
    assert (xa1, ya1) == pytest.approx((2 * xa0, 2 * ya0))
    assert (xb1, yb1) == pytest.approx((2 * xb0, 2 * yb0))
    assert cmd.base.transformacion(_valores(ruta, "2"), ctx)["escala"] == pytest.approx(2.0)


def test_escala_no_positiva_se_rechaza(comando):
    cmd, ctx, ruta = comando
    with pytest.raises(ErrorComando, match="positiva"):
        cmd.boceto_previo(_valores(ruta, "0"), ctx)


def test_escala_que_desborda_el_boceto_se_rechaza(comando):
    cmd, ctx, ruta = comando
    with pytest.raises(ErrorComando, match=r"1\.000\.000"):
        cmd.boceto_previo(_valores(ruta, "200000"), ctx)

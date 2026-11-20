# -*- coding: utf-8 -*-
"""PREP: opción «Desplazamiento Y (Expresion)» de «Insertar SVG en boceto».

La ayuda de Fusion (Add an SVG image) describe «Y Distance» como una distancia en milímetros que corre la
geometría respecto del origen del boceto; el valor se teclea como expresión (`dy`). Se prueba un valor
numérico y el borde del rango del boceto (1 km), sobre el código del comando en `ui/comandos/insertar.py`
y `ui/comandos/insertar_en_boceto.py`. No cambia código de la app.
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
    ruta = tmp_path / "desplazamiento_y.svg"
    ruta.write_text(SVG, encoding="utf-8")
    lienzo = SimpleNamespace(plano=geo.Plano("XY"))
    return InsertarEnBoceto(InsertarSVG(), lienzo), ContextoComando(Documento()), str(ruta)


def _valores(ruta, dy):
    return {"archivo": ruta, "escala": "1", "dx": "0 mm", "dy": dy, "angulo": "0 deg",
            "voltear_h": False, "voltear_v": False}


def _linea(boceto):
    lid = next(k for k, curva in boceto.curvas.items() if curva.tipo == "linea")
    return boceto._extremos_linea(lid)


def test_dy_expresion_numerica_corre_la_geometria_en_y(comando):
    cmd, ctx, ruta = comando
    sin_corre = cmd.boceto_previo(_valores(ruta, "0 mm"), ctx)
    corregido = cmd.boceto_previo(_valores(ruta, "25 mm"), ctx)
    (x0a, y0a), (x0b, y0b) = _linea(sin_corre)
    (x1a, y1a), (x1b, y1b) = _linea(corregido)
    assert (x1a, x1b) == pytest.approx((x0a, x0b))
    assert (y1a - y0a, y1b - y0b) == pytest.approx((25.0, 25.0))
    assert cmd.base.transformacion(_valores(ruta, "25 mm"), ctx)["desplazamiento"][1] == pytest.approx(25.0)


def test_dy_en_el_borde_del_rango_del_boceto_se_rechaza(comando):
    cmd, ctx, ruta = comando
    with pytest.raises(ErrorComando, match=r"1\.000\.000"):
        cmd.boceto_previo(_valores(ruta, "1000000 mm"), ctx)

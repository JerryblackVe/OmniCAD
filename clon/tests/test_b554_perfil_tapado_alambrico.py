# -*- coding: utf-8 -*-
"""B-554: un perfil de boceto dentro de un cuerpo. Como en Fusion, en vista sombreada lo tapa el cuerpo (se elige con
«Seleccionar otro»); en «Estructura alámbrica» el cuerpo no tapa nada y el clic elige el perfil."""
import os

import numpy as np
import pytest

from omnicad.nucleo import geometria as g
from omnicad.restricciones import Boceto
from omnicad.timeline.documento import Documento
from omnicad.timeline.operaciones import OpBoceto


@pytest.fixture(scope="module")
def visor():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    from omnicad.ui.comando import ContextoComando
    from omnicad.ui.visor3d import Visor3D
    QApplication.instance() or QApplication([])
    doc = Documento()
    b = Boceto()
    b.agregar_circulo((0, 0), 4)                       # en el plano XY, a z=0
    doc.agregar(OpBoceto(doc.nuevo_id(), "Boceto1", boceto=b))
    ctx = ContextoComando(doc)
    ctx.estado.nuevo_cuerpo("caja", g.caja(30, 30, 20, origen=(-15, -15, -10)))   # el círculo queda adentro
    v = Visor3D()
    v.resize(800, 600)
    v.set_modelo(ctx.estado)
    v.vista("arriba")
    v.encuadrar()
    yield v
    v.close()


def test_sombreado_el_cuerpo_tapa_el_perfil_y_con_otro_se_elige(visor):
    visor.config.estilo_visual = "sombreado_aristas"
    pos = visor.proyectar(np.array([0.0, 0.0, 0.0]))
    hit = visor.elegir_entidad(pos, {"perfil"})
    assert hit is None or hit["tipo"] != "perfil"
    assert visor.elegir_entidad(pos, {"perfil"}, a_traves=True)["tipo"] == "perfil"


def test_alambrico_elige_el_perfil_tapado(visor):
    visor.config.estilo_visual = "alambrico"
    hit = visor.elegir_entidad(visor.proyectar(np.array([0.0, 0.0, 0.0])), {"perfil"})
    assert hit is not None and hit["tipo"] == "perfil"

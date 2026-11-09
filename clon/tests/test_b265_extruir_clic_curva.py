# -*- coding: utf-8 -*-
"""B-265: en Extruir sólida, un clic sobre el borde de un perfil elige el perfil, nunca la curva suelta.

Antes, el clic en el ala de la mariposa entraba como «curva de boceto», el campo pasaba de «10 perfiles» a «11 objetos»
y la vista previa se perdía con «Las curvas abiertas solo se extruyen con Extrusión delgada». Fusion (Extrude reference):
la extrusión sólida toma perfiles cerrados; las curvas abiertas, solo la delgada."""
import os

import numpy as np
import pytest

from omnicad.nucleo import geometria as g
from omnicad.restricciones import Boceto
from omnicad.timeline.documento import Documento
from omnicad.timeline.operaciones import OpBoceto


@pytest.fixture(scope="module")
def app_qt():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def test_b265_clic_en_el_borde_elige_el_perfil_en_la_solida(app_qt):
    from omnicad.ui.comando import ContextoComando, PanelComando
    from omnicad.ui.comandos.solido import Extruir
    from omnicad.ui.visor3d import Visor3D
    doc = Documento()
    b = Boceto()
    b.agregar_rectangulo((0, 0), (20, 10))
    b.agregar_circulo((40, 5), 4)
    doc.agregar(OpBoceto(doc.nuevo_id(), "Boceto1", boceto=b))
    ctx, visor = ContextoComando(doc), Visor3D()
    visor.resize(800, 600)
    visor.set_modelo(ctx.estado)
    visor.encuadrar()
    panel = PanelComando(Extruir(), ctx, visor)
    panel._t_previa.stop()
    panel.show()                                                # el panel solo recibe clics mientras se ve
    assert panel.activa.clave == "perfiles"
    borde = visor.proyectar(np.array([10.0, 0.0, 0.0]))       # sobre la recta de abajo del rectángulo
    assert borde is not None

    assert "curva_boceto" not in visor.filtro
    hit = visor.elegir_entidad(borde, visor.filtro)
    assert hit is not None and hit["ref"]["tipo"] == "perfil"
    panel._elegida(hit)
    panel._elegida(visor.elegir_entidad(visor.proyectar(np.array([40.0, 1.0, 0.0])), visor.filtro))    # el anillo
    assert [h["ref"]["tipo"] for h in panel.valores["perfiles"]] == ["perfil", "perfil"]
    assert cmd_ok(panel, ctx)
    # B-266: con lo elegido a clics sobre los bordes, cambiar la distancia rehace la vista previa
    previas = []
    panel.previa.connect(previas.append)
    panel._previa_aislada = True
    for d in ("7 mm", "12 mm"):
        panel.set_valor("distancia", d)
        panel._t_previa.stop()
        panel._calcular_previa()
        assert panel._previa_ok, panel.mensaje.text()
        alturas = {round(float(g.caja_envolvente(c.forma)[1][2]), 6) for c in previas[-1].cuerpos.values()}
        assert alturas == {float(d.split()[0])}

    panel.set_valor("tipo", "delgada")                          # la delgada sí toma curvas (abiertas o cerradas)
    assert "curva_boceto" in visor.filtro
    assert visor.elegir_entidad(borde, visor.filtro)["ref"]["tipo"] == "curva_boceto"
    panel.set_valor("tipo", "solida")
    assert "curva_boceto" not in visor.filtro
    # una curva elegida antes de apretar E tampoco entra a la sólida (sí el perfil)
    from omnicad.ui.comando import preseleccion
    curva = visor.elegir_entidad(borde, {"curva_boceto"})
    assert curva["ref"]["tipo"] == "curva_boceto"
    previa = preseleccion(Extruir().campos(ctx), [curva, hit])
    assert [h["ref"]["tipo"] for h in previa["perfiles"]] == ["perfil"]
    panel.deleteLater()
    visor.deleteLater()


def cmd_ok(panel, ctx):
    op = panel.comando.construir(panel.valores, ctx)
    return op.p["curvas"] == [] and len(op.p["perfiles"]) == 2

"""B-635: las diagonales de construcción no son perfiles de extrusión."""
import numpy as np
import pytest
from PySide6.QtWidgets import QApplication

from omnicad.nucleo import geometria as geo
from omnicad.restricciones import Boceto
from omnicad.restricciones.boceto import agregar_rectangulo_centro
from omnicad.timeline.documento import Documento
from omnicad.timeline.operaciones import OpBoceto, OpExtrusion
from omnicad.ui.comando import ContextoComando, PanelComando
from omnicad.ui.comandos.solido import Extruir
from omnicad.ui.comandos.superficie import SupExtruir
from omnicad.ui.visor3d import Visor3D


@pytest.fixture
def escenario():
    app = QApplication.instance() or QApplication([])
    doc = Documento()
    boceto = Boceto()
    agregar_rectangulo_centro(boceto, (0, 0), (10, 5))
    doc.agregar(OpBoceto(doc.nuevo_id(), "Boceto1", boceto=boceto))
    visor = Visor3D()
    visor.resize(800, 600)
    visor.set_modelo(doc.estado_final)
    visor.encuadrar()
    yield doc, visor
    visor.deleteLater()
    app.processEvents()


def test_perfil_y_extrusion_solida_ignoran_las_diagonales(escenario):
    doc, _ = escenario
    br = next(iter(doc.estado_final.bocetos.values()))
    assert len([c for c in br.boceto.curvas.values() if c.construccion]) == 2
    assert len(br.perfiles) == 1
    assert br.perfiles[0].area == pytest.approx(200)
    ref = OpExtrusion.referencia_perfil(br.perfiles[0])
    resultado = doc.agregar(OpExtrusion(doc.nuevo_id(), boceto=br.op_id, perfiles=[ref], distancia="10 mm"))
    assert resultado.estado in ("ok", "aviso"), resultado.mensaje
    cuerpos = doc.estado_final.cuerpos
    assert len(cuerpos) == 1
    forma = next(iter(cuerpos.values())).forma
    assert geo.volumen(forma) == pytest.approx(2000)
    assert geo.es_valida(forma)


@pytest.mark.xfail(strict=True, reason="B-635", raises=AssertionError)
@pytest.mark.parametrize("modo", ["delgada", "superficie"])
def test_las_diagonales_no_se_seleccionan_para_extruir(escenario, modo):
    doc, visor = escenario
    ctx = ContextoComando(doc)
    panel = PanelComando(Extruir() if modo == "delgada" else SupExtruir(), ctx, visor)
    panel._t_previa.stop()
    panel.show()
    if modo == "delgada":
        panel.set_valor("tipo", "delgada")
    try:
        elegidas = []
        for y in (2.5, -2.5):
            punto = visor.proyectar(np.array([5.0, y, 0.0]))
            if punto is None:
                raise RuntimeError("No se pudo proyectar la diagonal")
            hit = visor.elegir_entidad(punto, visor.filtro)
            if hit and hit["ref"]["tipo"] == "curva_boceto":
                elegidas.append(hit)
                panel._elegida(hit)
        if len(elegidas) == 2:
            panel.set_valor("distancia", "10 mm")
            op = panel.comando.construir(panel.valores, ctx)
            resultado = doc.agregar(op)
            if resultado.estado not in ("ok", "aviso") or len(doc.estado_final.cuerpos) == 0:
                raise RuntimeError(f"No se reprodujo la extrusión: {resultado.mensaje}")
        assert not elegidas, f"Se eligieron {len(elegidas)} diagonales de construcción"
    finally:
        panel._t_previa.stop()
        panel.deleteLater()

# -*- coding: utf-8 -*-
"""B-759: la previa de un plano, eje o punto de construcción (cuentas de geometría, sin mallas) se calcula en la ventana:
el proceso aparte rehacía el documento entero (con texto extruido, mucho) y dejaba «Calculando vista previa…» fijo."""
import os

import pytest
from PySide6.QtCore import QCoreApplication

from omnicad.timeline.documento import Documento
from omnicad.timeline.operaciones import OpPlano, OpPrimitiva
from omnicad.ui import comando


@pytest.fixture(scope="module")
def app_qt():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def test_previa_de_plano_desfase_no_pasa_por_el_proceso_aparte(app_qt, monkeypatch):
    from omnicad.ui.comando import ContextoComando, PanelComando, hit_desde_ref
    from omnicad.ui.comandos.construir import CATALOGO_LOCAL
    from omnicad.ui.visor3d import Visor3D
    monkeypatch.setattr(comando, "PREVIA_APARTE", True)
    doc = Documento()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="20", largo="20", alto="20"))
    monkeypatch.setattr(PanelComando, "_iniciar_previa", lambda *a: pytest.fail("abrió el proceso aparte"))
    monkeypatch.setattr(Documento, "_prevuelo_cambio", lambda *a, **k: pytest.fail("ensayó el documento aparte"))
    visor = Visor3D()
    visor.set_modelo(doc.estado_final)
    plano = hit_desde_ref({"tipo": "plano", "id": "XY"}, doc.estado_final)
    panel = PanelComando(CATALOGO_LOCAL["plano_desfase"](), ContextoComando(doc, None), visor, {"r0": [plano]})
    panel.show()
    panel._t_previa.stop()
    panel.set_valor("distancia", "10 mm")
    panel._t_previa.stop()
    panel._calcular_previa()
    QCoreApplication.processEvents()
    assert panel._previa_ok and not panel._previa_aparte and panel._hijo_previa is None
    assert "Calculando" not in panel.mensaje.text()
    panel.cancelar()
    visor.close()


@pytest.mark.parametrize("tipo", ["plano", "eje", "punto"])
def test_las_construcciones_nunca_son_previa_pesada(tipo):
    class _Op:                       # `_previa_pesada` solo mira el tipo antes de decidir
        TIPO = tipo
    panel = comando.PanelComando.__new__(comando.PanelComando)
    panel.ctx = type("C", (), {"doc": type("D", (), {"motor": "opencascade"})()})()
    assert not panel._previa_pesada(_Op())
    assert OpPlano.TIPO in comando.TIPOS_LIVIANOS

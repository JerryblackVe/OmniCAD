# -*- coding: utf-8 -*-
"""B-623: «Dividir cuerpo» pierde el campo «Cuerpo para dividir» cuando la herramienta se elige primero.

Preparación para Opus: reproduce los clics del visor con señales (sin mover el cursor real).
"""
from PySide6.QtCore import QCoreApplication, QPointF
from test_manipuladores import _doc_caja, _panel, app_qt  # noqa: F401 (fixture)

from omnicad.ui.comando import hit_desde_ref
from omnicad.ui.comandos.modificar import DividirCuerpo


def test_un_clic_en_el_cuerpo_no_cae_en_la_herramienta(app_qt):  # noqa: F811 (fixture importado)
    doc = _doc_caja()
    cuerpo = hit_desde_ref({"tipo": "cuerpo", "cuerpo": "op1.c1"}, doc.estado_final)
    plano = hit_desde_ref({"tipo": "plano", "id": "XY"}, doc.estado_final)
    panel, visor, _ = _panel(DividirCuerpo(), doc, {})
    panel.show()
    visor.show()
    QCoreApplication.processEvents()

    try:
        # Con «Cuerpo para dividir» activo, el visor no elige el plano: `clic_vacio` salta a «Herramientas de
        # división» (ui/comando.py:1814), que también acepta cuerpos.
        visor.elegir_entidad = lambda pos, filtros: plano if "plano" in filtros else None
        panel._pos_clic = QPointF(400, 300)
        visor.clic_vacio.emit()

        # El clic siguiente al cuerpo, que debía llenar «Cuerpo para dividir», entra en la herramienta y
        # `construir` acaba pidiendo «Seleccioná el cuerpo.» (ui/comandos/modificar.py:844).
        visor.entidad_elegida.emit(cuerpo)
        refs = [h["ref"] for h in panel.valores.get("herramienta") or []]
        assert len(panel.valores.get("cuerpo") or []) == 1
        assert not any(r.get("tipo") == "cuerpo" for r in refs)
    finally:
        panel.cancelar()

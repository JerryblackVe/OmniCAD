"""Extruir → Cortar: recibir la previa exacta no debería recalcular la herramienta en la ventana."""
import math
import time

import pytest
from PySide6.QtCore import QSettings, QThread
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from omnicad import api
from omnicad.nucleo import geometria as geo
from omnicad.timeline.operaciones import OpExtrusion
from omnicad.ui import comando
from omnicad.ui.comandos.solido import Extruir
from omnicad.ui.preferencias import Preferencias
from omnicad.ui.ventana import VentanaPrincipal


@pytest.mark.xfail(strict=True, reason="B-622", raises=pytest.fail.Exception)
def test_recibir_el_corte_aparte_no_recalcula_la_herramienta_en_la_ventana(tmp_path, monkeypatch):
    monkeypatch.setattr(comando, "PREVIA_APARTE", True)
    app = QApplication.instance() or QApplication([])
    sesion = api.Sesion()
    circulos = [{"type": "circle", "center": [5 + 5 * x, 5 + 5 * y], "radius": 1}
                for x in range(8) for y in range(6)]
    for herramienta, args in (
        ("create_box", {"length": 50, "width": 40, "height": 10, "anchor": "corner"}),
        ("create_construction_plane", {"plane": "XY", "offset": 10, "name": "Arriba"}),
        ("sketch_from_spec", {"plane": "Arriba", "entities": circulos}),
    ):
        respuesta = api.llamar(sesion, herramienta, args)
        assert respuesta["ok"], respuesta
    boceto = sesion.doc.operaciones[-1].id
    ventana = VentanaPrincipal(sesion.doc, prefs=Preferencias(QSettings(str(tmp_path / "prefs.ini"), QSettings.IniFormat)))
    ventana.show()
    try:
        panel = ventana.ejecutar_comando(Extruir())
        perfiles = sesion.doc.estado_final.bocetos[boceto].perfiles
        assert len(perfiles) == len(circulos)
        panel.set_valor("perfiles", [comando.hit_desde_ref(
            {"tipo": "perfil", "boceto": boceto, **OpExtrusion.referencia_perfil(perfil)}, panel.ctx.estado)
            for perfil in perfiles])
        panel.set_valor("operacion", "cortar")
        panel.set_valor("distancia", "-4 mm")
        panel._t_previa.stop()
        panel._calcular_previa()
        assert panel._previa_aparte and panel._hijo_previa is not None, panel.mensaje.text()

        # Mide trabajo real sin fijar un umbral de tiempo que dependa de la máquina.
        tiempos = []
        previsualizar = sesion.doc.previsualizar

        def medir(op, *args, **kwargs):
            inicio = time.perf_counter()
            resultado = previsualizar(op, *args, **kwargs)
            if QThread.currentThread() == app.thread() and op.TIPO == "extrusion" and op.p["operacion"] == "nuevo":
                tiempos.append((time.perf_counter() - inicio) * 1000)
            return resultado

        monkeypatch.setattr(sesion.doc, "previsualizar", medir)
        limite = time.monotonic() + 35
        while panel._hijo_previa is not None and time.monotonic() < limite:
            QTest.qWait(20)
        assert panel._hijo_previa is None and panel._previa_ok, panel.mensaje.text()
        estado = ventana.visor._estado
        volumen = sum(geo.volumen_exacto(c.forma) for c in estado.cuerpos.values())
        assert volumen == pytest.approx(50 * 40 * 10 - len(circulos) * math.pi * 4)
        if tiempos:
            pytest.fail(f"La ventana volvió a extruir la herramienta al recibir la previa: {sum(tiempos):.0f} ms")
    finally:
        if ventana.panel is not None:
            ventana.panel.cancelar()
        ventana.doc.modificado = False
        ventana.close()
        ventana.deleteLater()
        app.processEvents()

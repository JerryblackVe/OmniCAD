# -*- coding: utf-8 -*-
"""B-418 (E11, tanda 12): en Windows el trabajador toma el pedido y nunca devuelve la respuesta. Ahí la previa va en la
ventana y todo cálculo aparte (la previa pesada, el Aceptar de un documento grande) va a un hijo de una sola tarea, salvo
OMNICAD_PREVIA_EN_VENTANA=0."""
import os
import subprocess
import sys
from pathlib import Path

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from omnicad.nucleo import aislado
from omnicad.timeline.documento import Documento
from omnicad.ui import comando
from omnicad.ui.preferencias import Preferencias
from omnicad.ui.ventana import VentanaPrincipal

CLON = Path(__file__).resolve().parents[1]
# OCP y Qt cargan sus DLL según la plataforma: se importan antes de fingir Windows; los módulos de OmniCAD, después.
FINGIR_WINDOWS = """
import subprocess, sys, PySide6.QtWidgets, PySide6.QtOpenGLWidgets, OCP, numpy
import omnicad.nucleo.geometria
sys.platform = "win32"
from omnicad.nucleo import aislado
from omnicad.ui import comando
print(comando.PREVIA_APARTE, aislado.TRABAJADOR)
"""


@pytest.mark.parametrize("valor, esperado", [(None, "False False"), ("1", "False False"), ("0", "True True")])
def test_en_windows_la_previa_va_en_la_ventana_y_sin_trabajador_salvo_que_se_pida(valor, esperado):
    entorno = {k: v for k, v in os.environ.items() if k != "OMNICAD_PREVIA_EN_VENTANA"}
    if valor is not None:
        entorno["OMNICAD_PREVIA_EN_VENTANA"] = valor
    salida = subprocess.run([sys.executable, "-c", FINGIR_WINDOWS], cwd=CLON, capture_output=True, text=True,
                            env=dict(entorno, PYTHONPATH=str(CLON), QT_QPA_PLATFORM="offscreen"), timeout=120)
    assert salida.stdout.strip().splitlines()[-1:] == [esperado], salida.stderr[-2000:]


def test_sin_trabajador_aceptar_crea_el_paso_con_un_hijo_de_una_sola_tarea(tmp_path, monkeypatch):
    from omnicad.ui.comandos import CATALOGO
    monkeypatch.setattr(aislado, "TRABAJADOR", False)
    monkeypatch.setattr(comando, "PREVIA_APARTE", False)
    monkeypatch.setattr(aislado, "UMBRAL_PREVUELO_PARAMETROS", 1)      # Aceptar va aparte, como en un documento grande
    aislado.cerrar_trabajador()
    nuevos = []
    monkeypatch.setattr(aislado._Trabajador, "__init__", lambda self: nuevos.append(self) or 1 / 0)
    app = QApplication.instance() or QApplication([])
    v = VentanaPrincipal(Documento(), prefs=Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat)))
    v.show()
    try:
        for clave in ("caja", "cilindro"):
            p = v.ejecutar_comando(CATALOGO[clave]())
            p.set_valor("alto", "15 mm")
            p.aceptar()
            assert v.panel is None, p.mensaje.text()
        assert len(v.doc.estado_final.cuerpos) == 2 and not nuevos
        calculo = aislado.CalculoPendiente("recalcular_documento", {"receta": v.doc.a_dict()})   # la previa pesada
        assert calculo.trabajador is None and calculo.proceso is not None
        calculo.cancelar()
    finally:
        v.doc.modificado = False
        v.close()
        v.deleteLater()
        app.processEvents()

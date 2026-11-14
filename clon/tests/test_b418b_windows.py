# -*- coding: utf-8 -*-
"""B-418: en Windows el trabajador tomaba el pedido y no contestaba (se trababa cargando la DLL de OpenBLAS con un ReadFile
de la entrada estándar pendiente en otro hilo). Ya lee sin bloquear (`aislado._lineas_sin_bloquear`); hasta confirmarlo en
la PC (10 de 10 con `diagnostico_b418.py --qt`), vuelve a estar prendido en Windows; OMNICAD_PREVIA_EN_VENTANA=1 es la
salida de escape: previa en la ventana y lo demás en hijos de una sola tarea."""
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


@pytest.mark.parametrize("valor, esperado", [(None, "True True"), ("0", "True True"), ("1", "False False")])
def test_en_windows_el_trabajador_esta_prendido_salvo_con_el_escape(valor, esperado):
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


def test_el_lector_sin_bloquear_arma_las_lineas_y_sale_cuando_el_padre_cierra():
    """Con trozos que cortan las líneas en cualquier lado, momentos sin nada y la tubería rota al final (el padre murió)."""
    llegadas = [0, 3, 0, 9, 4]
    datos = iter([b"pre", b"via\ncalen", b"tar\nfi"])

    def mirar():
        if not llegadas:
            raise BrokenPipeError
        return llegadas.pop(0)

    lineas = list(aislado._lineas_sin_bloquear(mirar, lambda n: next(datos), esperar=0))
    assert lineas == [b"previa\n", b"calentar\n", b"fi"]

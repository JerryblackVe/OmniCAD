# -*- coding: utf-8 -*-
"""B-48: las caídas nativas reproducidas (AG-8: `BRepAlgoAPI_Fuse.Build` en paralelo dentro de `unir_todos`; B-293: la
previa de Extruir) fueron booleanas en paralelo de OpenCascade en el proceso de la ventana. La app las corre en serie;
los procesos aparte (`--tarea-aislada`, prevuelo, trabajador) siguen en paralelo."""
import os
import subprocess
import sys
from pathlib import Path

import pytest

CLON = Path(__file__).resolve().parents[1]

# Corta `main()` donde ya se creó la aplicación: imprime el modo de las booleanas y sale.
_HUMO = """
import OmniCAD
from omnicad import prueba_humo
from omnicad.nucleo import geometria as geo
prueba_humo.ejecutar = lambda: print("PARALELO", geo.PARALELO) or 0
OmniCAD.main(["--prueba-humo"])
"""
_APP = """
import sys
import OmniCAD
from omnicad.nucleo import aislado, geometria as geo
from omnicad.ui import arranque, ventana
arranque.mostrar_portada = lambda app: None
aislado.precalentar = lambda: None
def cortar():
    print("PARALELO", geo.PARALELO)
    sys.exit(0)
ventana.VentanaPrincipal = cortar
OmniCAD.main([])
"""
_HIJO = "from omnicad.nucleo import geometria as geo; print('PARALELO', geo.PARALELO)"


@pytest.mark.parametrize(("codigo", "esperado"), [(_HUMO, "False"), (_APP, "False"), (_HIJO, "True")],
                         ids=["humo", "app", "proceso_aparte"])
def test_la_ventana_corre_las_booleanas_en_serie_y_los_hijos_en_paralelo(codigo, esperado, tmp_path):
    entorno = {**os.environ, "QT_QPA_PLATFORM": "offscreen", "LOCALAPPDATA": str(tmp_path)}
    entorno.pop("OMNICAD_SIN_PARALELO", None)
    salida = subprocess.run([sys.executable, "-c", codigo], cwd=CLON, env=entorno, capture_output=True, text=True,
                            timeout=180)
    assert salida.returncode == 0, salida.stderr[-2000:]
    assert f"PARALELO {esperado}" in salida.stdout.splitlines()

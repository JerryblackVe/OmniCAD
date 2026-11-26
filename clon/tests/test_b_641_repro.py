"""B-641: el escenario de rosca modelada debe completar las mediciones."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.mark.lento
@pytest.mark.skipif(
    sys.platform.startswith("linux") and (os.environ.get("QT_QPA_PLATFORM") != "xcb" or not os.environ.get("DISPLAY")),
    reason="El banco necesita un visor OpenGL: QT_QPA_PLATFORM=xcb y xvfb-run -a",
)
def test_banco_de_rosca_modelada_completa_las_mediciones(tmp_path):
    clon = Path(__file__).resolve().parents[1]
    banco = clon.parent / "scripts" / "bench_fluidez.py"
    # El hijo del banco usa eventos Qt reales sobre el visor, aislado del Qt de pytest.
    # conftest deja offscreen y en Windows no da OpenGL: el hijo elige su plataforma (arnes.py).
    entorno = {k: v for k, v in os.environ.items() if not (k == "QT_QPA_PLATFORM" and v == "offscreen")}
    proceso = subprocess.run(
        [sys.executable, str(banco), "--hijo", "b"], cwd=clon, capture_output=True, text=True, timeout=300,
        env=dict(entorno, OMNICAD_PRUEBA_VENTANA="minimizada", OMNICAD_CODIGO=str(clon), OMNICAD_FLUIDEZ="aviso",
                 OMNICAD_ASISTENTE_DIR=str(tmp_path), OMNICAD_PREAJUSTES=str(tmp_path / "preajustes.json")),
    )
    assert proceso.returncode == 0, (proceso.stdout, proceso.stderr)
    prefijo = "FLUIDEZ_JSON="
    linea = next((s for s in reversed(proceso.stdout.splitlines()) if s.startswith(prefijo)), None)
    assert linea is not None, (proceso.stdout, proceso.stderr)
    resultado = json.loads(linea.removeprefix(prefijo))
    assert "error" not in resultado, resultado["error"]
    assert resultado["primera_previa_ms"] is not None and resultado["aceptar_ms"] is not None, resultado

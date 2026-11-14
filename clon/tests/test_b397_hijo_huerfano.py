# -*- coding: utf-8 -*-
"""B-397: el hijo de una sola tarea termina si muere el padre mientras calcula."""
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

CLON = Path(__file__).resolve().parents[1]

# Como en B-396, sitecustomize instala una tarea sintética larga, sin geometría. Se sustituye el lector
# de STEP para alcanzar también el principal lanzado con «-m» (tiene su propio registro de tareas).
GIRAR = """
import os
import time
from pathlib import Path
from omnicad.nucleo import intercambio

def _girar(ruta):
    Path(ruta).write_text(str(os.getpid()), encoding="ascii")
    fin = time.monotonic() + 120
    while time.monotonic() < fin:
        pass

intercambio.leer_step = _girar
"""
PADRE = """
import sys
import time
from omnicad.nucleo import aislado

modo, ruta = sys.argv[1:]
datos = {"ruta": ruta, "formato": "STEP"}
with aislado._ocupado:
    if modo == "previa":
        calculo = aislado.CalculoPendiente("ensayar_lectura", datos)
        assert calculo.trabajador is None
        time.sleep(600)
    else:
        esperar = (lambda segundos: None) if modo == "con_espera" else None
        aislado.correr_json("ensayar_lectura", datos, 600, esperar)
"""


def _vivo(pid):
    try:
        with open(f"/proc/{pid}/stat") as f:
            return f.read().split(")")[-1].split()[0] != "Z"  # un zombi ya terminó
    except OSError:
        return False


@pytest.mark.skipif(not Path("/proc").is_dir(), reason="mira los procesos en /proc (Linux)")
@pytest.mark.parametrize("modo", ["previa", "sin_espera", "con_espera"])
def test_muerto_el_padre_el_hijo_termina_en_plena_tarea(tmp_path, modo):
    (tmp_path / "sitecustomize.py").write_text(GIRAR, encoding="utf-8")
    ruta = tmp_path / "hijo.pid"
    hijo = None
    with subprocess.Popen([sys.executable, "-c", PADRE, modo, str(ruta)], cwd=CLON,
                          env=dict(os.environ, PYTHONPATH=os.pathsep.join((str(tmp_path), str(CLON))))) as padre:
        try:
            limite = time.monotonic() + 30
            while not ruta.is_file() and padre.poll() is None and time.monotonic() < limite:
                time.sleep(0.1)
            assert ruta.is_file(), "el hijo no llegó a la tarea sintética"
            hijo = int(ruta.read_text(encoding="ascii"))
            time.sleep(0.2)  # sigue calculando con el padre vivo; no se cerró la tubería al enviar
            assert _vivo(hijo)
            padre.kill()
            padre.wait()
            limite = time.monotonic() + 10
            while _vivo(hijo) and time.monotonic() < limite:
                time.sleep(0.1)
            assert not _vivo(hijo), "el hijo de una sola tarea quedó huérfano calculando"
        finally:
            if padre.poll() is None:
                padre.kill()
                padre.wait()
            if hijo is not None and _vivo(hijo):
                os.kill(hijo, signal.SIGKILL)  # también limpiar al demostrar el fallo sin el arreglo

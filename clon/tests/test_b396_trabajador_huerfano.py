# -*- coding: utf-8 -*-
"""B-396: si muere el padre, el trabajador del proceso aparte termina aunque esté en medio de un cálculo."""
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

CLON = Path(__file__).resolve().parents[1]

# Una tarea de prueba que gira dos minutos al 100 % de CPU, como los huérfanos de la VPS. El `sitecustomize` la
# registra en el padre y en el trabajador (lo hereda por PYTHONPATH), sin depender de cuánto tarde la geometría.
GIRAR = """
import time
from omnicad.nucleo import aislado

def _girar(segundos):
    fin = time.monotonic() + segundos
    while time.monotonic() < fin:
        pass
    return {}

aislado._TAREAS_JSON["girar"] = _girar
"""
# El padre la pide, avisa el pid del trabajador y espera: el test lo mata a mitad, como turno.py al cortar un pytest.
PADRE = """
import time
from omnicad.nucleo import aislado
calculo = aislado.CalculoPendiente("girar", {"segundos": 120})
print(calculo.proceso.pid, flush=True)
time.sleep(600)
"""


def _vivo(pid):
    try:
        with open(f"/proc/{pid}/stat") as f:
            return f.read().split(")")[-1].split()[0] != "Z"      # un zombi ya terminó: solo falta que lo recojan
    except OSError:
        return False


@pytest.mark.skipif(not Path("/proc").is_dir(), reason="mira los procesos en /proc (Linux)")
def test_muerto_el_padre_el_trabajador_termina_en_plena_tarea(tmp_path):
    (tmp_path / "sitecustomize.py").write_text(GIRAR, encoding="utf-8")
    with subprocess.Popen([sys.executable, "-c", PADRE], cwd=CLON, stdout=subprocess.PIPE, text=True,
                          env=dict(os.environ, PYTHONPATH=os.pathsep.join((str(tmp_path), str(CLON))))) as padre:
        try:
            hijo = int(padre.stdout.readline())
            time.sleep(2)                     # ya está girando
            assert _vivo(hijo)
        finally:
            padre.kill()                      # pase lo que pase: el padre duerme 10 min
        padre.wait()
        limite = time.monotonic() + 10
        while _vivo(hijo) and time.monotonic() < limite:
            time.sleep(0.1)
        assert not _vivo(hijo), "el trabajador quedó huérfano calculando"

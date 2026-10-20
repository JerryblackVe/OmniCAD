# -*- coding: utf-8 -*-
"""Bug B-48 (crítico): caída nativa de OCCT (0xC0000005 en TKernel, OCCT 8.0.1) durante la tortura de
parámetros del motor RL-1 (148 pasos; el puente en vivo murió con BRIDGE_ERROR 10054).

No se reprodujo en subproceso: se abrió `motor-rl-tortura.omnicad` sin ventana y se aplicó la secuencia
exacta del craso (r_camara=32,5 y largo_camara=65 por los reverts perdidos, después d_eje 6→7,8→6),
18 min de recálculo, salida 0. Visto 1 vez en la sesión original, así que la protección es el
aislamiento: una caída nativa del kernel dentro de una tarea aislada (`nucleo/aislado.py`) tiene que
volver como error en español y no puede matar al proceso padre."""
import sys

import pytest

from omnicad.nucleo import aislado
from omnicad.nucleo import geometria as geo


def test_b48_un_crash_nativo_del_kernel_vuelve_como_error_y_no_mata_al_padre(monkeypatch):
    """El hijo muere de verdad con 0xC0000005 (lo mismo que firmó Windows para TKernel): el padre recibe
    `TareaAislada` con un mensaje claro y sigue corriendo."""
    monkeypatch.setattr(aislado._motor, "motor_activo", lambda: "opencascade")          # con omnikernel corre en proceso
    monkeypatch.setattr(aislado, "_comando", lambda tarea, carpeta: [sys.executable, "-c",
                                                                      "import os; os._exit(-1073741819)"])
    forma = geo.caja(10, 20, 30)
    with pytest.raises(aislado.TareaAislada) as fallo:
        aislado.correr("autointersecciones", forma, 60)
    mensaje = str(fallo.value)
    assert "error nativo" in mensaje and "0xc0000005" in mensaje and "sigue andando" in mensaje
    assert geo.es_valida(forma)   # el proceso padre sigue vivo y trabajando

# -*- coding: utf-8 -*-
"""B-292: todos los hijos limitan BLAS antes de arrancar y respetan el entorno del usuario."""
import os
from unittest.mock import patch

import pytest

from omnicad.nucleo import aislado


@pytest.mark.parametrize("lanzamiento", ["trabajador", "previa", "ejecutar"])
@pytest.mark.parametrize("congelada", [False, True], ids=["python", "frozen"])
@pytest.mark.parametrize("definidas", [
    {},
    {"OPENBLAS_NUM_THREADS": "4"},
    {"OMP_NUM_THREADS": "3"},
    {"OPENBLAS_NUM_THREADS": "4", "OMP_NUM_THREADS": "3"},
], ids=["por_defecto", "openblas_del_usuario", "omp_del_usuario", "ambas_del_usuario"])
def test_todos_los_lanzamientos_pasan_el_entorno(monkeypatch, tmp_path, lanzamiento, congelada, definidas):
    for nombre in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS"):
        monkeypatch.delenv(nombre, raising=False)
    for nombre, valor in definidas.items():
        monkeypatch.setenv(nombre, valor)
    monkeypatch.setattr(aislado.sys, "frozen", congelada, raising=False)
    entorno_padre = os.environ.copy()

    with patch("omnicad.nucleo.aislado.subprocess.Popen") as abrir, \
            patch("omnicad.nucleo.aislado.subprocess.run") as ejecutar:
        if lanzamiento == "trabajador":
            hijo = aislado._Trabajador()
            hijo.cerrar()
            llamada = abrir
        elif lanzamiento == "previa":
            with patch.object(aislado.CalculoPendiente, "_al_trabajador", return_value=False):
                hijo = aislado.CalculoPendiente("ensayar_lectura", {})
            hijo.cancelar()
            llamada = abrir
        else:
            aislado._ejecutar(aislado._comando("ensayar_lectura", tmp_path), 10, None)
            llamada = ejecutar

        llamada.assert_called_once()
        entorno = llamada.call_args.kwargs["env"]
        assert entorno == {**entorno_padre, "OPENBLAS_NUM_THREADS": definidas.get("OPENBLAS_NUM_THREADS", "1"),
                           "OMP_NUM_THREADS": definidas.get("OMP_NUM_THREADS", "1")}
        assert os.environ == entorno_padre
        assert llamada.call_args.args[0][1] == ("--tarea-aislada" if congelada else "-m")

# -*- coding: utf-8 -*-
"""Portón de paridad: cada kernel corre en un intérprete separado, por las mismas funciones de `nucleo/`.

CONECTADOS: dan el mismo resultado con los dos motores (volumen ≤ 1e-6, área ≤ 1e-5, mismas caras y aristas,
válidos y cada cara de OpenCascade encuentra exactamente una cara igual en OmniKernel).
SIN_SOPORTE: OmniKernel no da paridad todavía; el motor nuevo informa MOTOR_SIN_SOPORTE (faltantes FK-003…).
"""
import json
import os
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest


pytestmark = pytest.mark.lento

CONECTADOS = ["caja", "cilindro", "toroide", "trasladar", "rotar", "unir", "cortar", "intersecar", "unir_l",
              "extruir_rectangulo", "extruir_simetrica", "extruir_xz", "extruir_dos", "extruir_sobre_cara", "empalme", "empalme_dos",
              "chaflan", "vaciado", "cara_l", "perfil_rectangulo", "perfil_elipse_vertical", "perfil_con_curva_rota", "vaciado_dos_caras", "desfasar_caras", "desmoldeo", "quitar_caras",
              "caja@step", "cilindro@step", "caja@iges", "cilindro@iges", "unir_l@step"]
SIN_SOPORTE = ["esfera", "extruir_circulo", "revolver_rectangulo", "cortar_cilindro", "agujero_pasante",
               "unir_cilindro", "intersecar_cilindro", "empalme_esquina", "chaflan_esquina", "extruir_con_agujero", "empalme_cilindro"]


def _medir(caso, motor):
    entorno = dict(os.environ, OMNICAD_MOTOR=motor, PYTHONIOENCODING="utf-8")
    entorno.pop("OMNICAD_BLOQUEAR_OCP", None)
    if motor == "omnikernel":
        entorno["OMNICAD_BLOQUEAR_OCP"] = "1"
    raiz = Path(__file__).resolve().parents[1]
    entorno["PYTHONPATH"] = str(raiz)
    p = subprocess.run([sys.executable, str(Path(__file__).with_name("caso_paridad_motor.py")), caso],
                       cwd=raiz, env=entorno, capture_output=True, text=True, encoding="utf-8", timeout=120)
    assert p.returncode == 0, p.stdout + p.stderr
    lineas = [l.removeprefix("RESULTADO_PARIDAD=") for l in p.stdout.splitlines() if l.startswith("RESULTADO_PARIDAD=")]
    assert len(lineas) == 1, p.stdout
    return json.loads(lineas[0])


@pytest.mark.parametrize("caso", CONECTADOS)
def test_paridad_en_procesos_aislados(caso):
    occ, omni = _medir(caso, "opencascade"), _medir(caso, "omnikernel")
    assert "error_kind" not in omni, omni
    a, b = occ["propiedades"], omni["propiedades"]
    assert a["valida"] and b["valida"]
    assert np.isclose(a["volumen"], b["volumen"], rtol=1e-6, atol=0)
    assert np.isclose(a["area"], b["area"], rtol=1e-5, atol=0)
    assert (a["caras"], a["aristas"]) == (b["caras"], b["aristas"])
    # Visor: la malla cubre la superficie (cuerdas: un poco menos que el área exacta) y cada triángulo es de una cara.
    for d in (a, b):
        assert 0.97 * d["area"] <= d["area_malla"] <= d["area"] * (1 + 1e-6) and d["triangulos_por_cara"]
    # Caja envolvente: OmniKernel la agranda con la cota real de su malla, hasta ~2e-4 del tamaño (faltante FK-011).
    if b["caja"] is not None:
        margen = max(2e-3, 3e-4 * float(np.linalg.norm(np.subtract(*a["caja"]))))
        assert np.allclose(a["caja"], b["caja"], rtol=0, atol=margen)
    # Cada firma debe encontrar exactamente la misma cara física, aunque el orden del kernel difiera.
    for firma in occ["firmas"]:
        candidatas = [f for f in omni["firmas"] if f["geom"] == firma["geom"] and
                      np.allclose(f["centro"], firma["centro"], rtol=0, atol=1e-6) and
                      np.isclose(f["area"], firma["area"], rtol=1e-5, atol=0)]
        assert len(candidatas) == 1
        for clave in ("normal", "radio"):
            if clave in firma:
                assert np.allclose(firma[clave], candidatas[0][clave], rtol=1e-6, atol=1e-8)
        if "eje" in firma:      # un eje es una recta: `referencias._distancia` lo compara sin signo
            assert np.isclose(abs(np.dot(firma["eje"], candidatas[0]["eje"])), 1, rtol=0, atol=1e-8)


@pytest.mark.parametrize("caso", SIN_SOPORTE)
def test_sin_paridad_informa_motor_sin_soporte(caso):
    assert "propiedades" in _medir(caso, "opencascade")
    assert _medir(caso, "omnikernel").get("error_kind") == "MOTOR_SIN_SOPORTE"

# -*- coding: utf-8 -*-
"""Portón de paridad: cada kernel corre en un intérprete separado, por las mismas funciones de `nucleo/`.

CONECTADOS: dan el mismo resultado con los dos motores (volumen ≤ 1e-6, área ≤ 1e-5, mismas caras y aristas,
válidos y cada cara de OpenCascade encuentra exactamente una cara igual en OmniKernel).
SIN_SOPORTE: OmniKernel no da paridad todavía; el motor nuevo informa MOTOR_SIN_SOPORTE (faltantes FK-…).
CONSULTAS: funciones que devuelven números (distancias, clasificación, centros): los mismos valores.
Las aristas de OpenCascade se cuentan sin las degeneradas de polos y ápices (regla de FK-006).
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
              "caja@step", "cilindro@step", "caja@iges", "cilindro@iges", "unir_l@step",
              "esfera", "extruir_circulo", "revolver_rectangulo", "revolver_arco", "cortar_cilindro", "agujero_pasante",
              "unir_cilindro", "intersecar_cilindro", "empalme_esquina", "chaflan_esquina", "extruir_con_agujero",
              "unir_dos_cuerpos", "revolver_negativo", "cremallera",
              "simetria", "patron_rectangular", "patron_circular", "patron_puntos", "multitransformacion",
              "agujero_punta", "agujero_plano", "agujero_abocardado", "agujero_avellanado", "agujero_en_caja"]
SIN_SOPORTE = ["empalme_cilindro", "chaflan_cilindro", "vaciado_cilindro", "desfasar_cilindro", "desfasar_lateral",
               "desmoldeo_cilindro"]
CONSULTAS = ["distancias", "se_tocan", "dentro_solidos", "centro_arco", "es_estanca", "cadena_tangente", "caras_tangentes"]


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
    # Visor: la malla cubre la superficie y cada triángulo es de una cara. Las cuerdas achican las caras curvas y
    # agrandan apenas las planas con agujeros (el hueco poligonal es más chico): también en OpenCascade.
    for d in (a, b):
        assert 0.97 <= d["area_malla"] / d["area"] <= 1.002 and d["triangulos_por_cara"]
    # Caja envolvente exacta en los dos (AddOptimal y body_bbox_exact, FK-011).
    if b["caja"] is not None:
        assert np.allclose(a["caja"], b["caja"], rtol=0, atol=1e-6)
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


@pytest.mark.parametrize("caso", CONSULTAS)
def test_consultas_dan_lo_mismo(caso):
    occ, omni = _medir(caso, "opencascade"), _medir(caso, "omnikernel")
    assert "error_kind" not in omni, omni
    for a, b in zip(occ["valores"], omni["valores"], strict=True):
        assert a == b if isinstance(a, bool) else np.allclose(a, b, rtol=1e-9, atol=1e-9), (a, b)

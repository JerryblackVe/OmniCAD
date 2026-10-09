# -*- coding: utf-8 -*-
"""Los ejemplos de `ejemplos/agentes/` corren de verdad: receta, script de Python y batch arman el mismo soporte
en L y dan el volumen analítico. Si una herramienta cambia y un ejemplo deja de andar, este test lo avisa."""
import importlib.util
import json
import math
from pathlib import Path

import pytest

from omnicad.cli import main

EJEMPLOS = Path(__file__).resolve().parents[2] / "ejemplos" / "agentes"
K = 1 - math.pi / 4          # área que le falta a un cuarto de cuadrado frente a un cuarto de círculo, por mm de radio²


def volumen_soporte(espesor):
    """Volumen exacto: dos placas de 80x40 que se solapan, menos 2 agujeros de Ø8, más el empalme interior de
    R6 (largo 80) y menos las dos esquinas redondeadas de R5 (alto = espesor)."""
    return (2 * 80 * 40 * espesor - 80 * espesor * espesor - 2 * math.pi * 4 ** 2 * espesor
            + 80 * 6 ** 2 * K - 2 * 5 ** 2 * K * espesor)


def correr(capsys, *argv):
    capsys.readouterr()
    codigo = main([str(a) for a in argv])
    salida = capsys.readouterr()
    return codigo, salida.out, salida.err


def volumen_de(capsys, archivo):
    codigo, out, _ = correr(capsys, "info", archivo, "--json")
    assert codigo == 0
    cuerpos = json.loads(out)["result"]["bodies"]
    assert len(cuerpos) == 1
    return cuerpos[0]["volume"], cuerpos[0]["bounding_box"]["size"]


@pytest.fixture
def pieza(tmp_path, capsys):
    """Proyecto vacío, creado con la propia CLI."""
    ruta = tmp_path / "pieza.omnicad"
    assert correr(capsys, "new", ruta)[0] == 0
    return ruta


def test_el_volumen_analitico_es_el_esperado():
    assert volumen_soporte(8) == pytest.approx(45807.965, abs=1e-3)


def test_script_de_python(tmp_path, capsys):
    spec = importlib.util.spec_from_file_location("soporte_l", EJEMPLOS / "soporte_l.py")
    ejemplo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ejemplo)
    capsys.readouterr()
    assert ejemplo.main([str(tmp_path / "salida")]) == 0
    resumen = json.loads(capsys.readouterr().out)
    assert resumen["volumen_mm3"] == pytest.approx(volumen_soporte(8), rel=1e-3)
    assert resumen["caja_mm"] == pytest.approx([80, 40, 40], abs=1e-3)
    for ruta in resumen["archivos"]:
        assert Path(ruta).stat().st_size > 0
    assert Path(resumen["archivos"][2]).read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    assert volumen_de(capsys, resumen["archivos"][0])[0] == pytest.approx(volumen_soporte(8), rel=1e-3)


def test_script_sin_carpeta_es_error_de_uso(capsys):
    spec = importlib.util.spec_from_file_location("soporte_l", EJEMPLOS / "soporte_l.py")
    ejemplo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ejemplo)
    assert ejemplo.main([]) == 2


def test_batch(pieza, tmp_path, capsys):
    codigo, out, err = correr(capsys, "batch", EJEMPLOS / "soporte_l.jsonl", "--doc", pieza)
    assert codigo == 0, err
    assert "10 ok, 0 con error, de 10 paso(s)" in out
    volumen, caja = volumen_de(capsys, pieza)
    assert volumen == pytest.approx(volumen_soporte(8), rel=1e-3)
    assert caja == pytest.approx([80, 40, 40], abs=1e-3)
    stl, png = tmp_path / "soporte.stl", tmp_path / "soporte.png"
    assert correr(capsys, "export", pieza, stl)[0] == 0 and stl.stat().st_size > 0
    assert correr(capsys, "render", pieza, png, "--size", "320x240")[0] == 0
    assert png.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


def test_receta(pieza, capsys):
    codigo, _, err = correr(capsys, "call", "apply_recipe", "--doc", pieza, "--args-file", EJEMPLOS / "soporte_l.receta.json")
    assert codigo == 0, err
    volumen, caja = volumen_de(capsys, pieza)
    assert volumen == pytest.approx(volumen_soporte(8), rel=1e-3)
    assert caja == pytest.approx([80, 40, 40], abs=1e-3)


def test_el_empalme_sigue_al_cambiar_un_parametro(pieza, capsys):
    """Lo que promete el README de los ejemplos: con espesor = 10 mm los empalmes se recalculan solos."""
    assert correr(capsys, "batch", EJEMPLOS / "soporte_l.jsonl", "--doc", pieza)[0] == 0
    assert correr(capsys, "call", "set_parameter", "--doc", pieza, "name=espesor", "expression=10 mm")[0] == 0
    assert volumen_de(capsys, pieza)[0] == pytest.approx(volumen_soporte(10), rel=1e-3)


def test_los_tres_ejemplos_estan_documentados():
    texto = (EJEMPLOS / "README.md").read_text(encoding="utf-8")
    for archivo in ("soporte_l.receta.json", "soporte_l.py", "soporte_l.jsonl"):
        assert (EJEMPLOS / archivo).is_file()
        assert archivo in texto

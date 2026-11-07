# -*- coding: utf-8 -*-
"""`todo.py --paralelo N`: hasta N piezas a la vez, sin abrir ninguna ventana.

Corre `scripts/prueba_ui/todo.py` como subproceso con piezas falsas (scripts chicos que duermen e imprimen la línea
de resumen) en una carpeta propia (OMNICAD_PRUEBA_PIEZAS) y con salida propia (OMNICAD_PRUEBA_SALIDA). TMP/TEMP
apuntan a una carpeta del test: los candados de `turno.py` quedan aislados del resto de la PC (otra sesión puede
estar corriendo pruebas pesadas con su propio turno).
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

TODO = Path(__file__).resolve().parents[2] / "scripts" / "prueba_ui" / "todo.py"
NOMBRES = ("corta", "lenta", "media")          # orden alfabético = orden de PIEZAS; lenta es la más larga
DUERMEN = {"corta": 0.6, "lenta": 3.0, "media": 1.0}
COMPROBACIONES = {"corta": 2, "lenta": 5, "media": 3}

PIEZA = """\
import os
import time
from pathlib import Path

salida = Path(os.environ["OMNICAD_PRUEBA_SALIDA"])
(salida / "{nombre}.inicio").write_text(str(time.time()), encoding="utf-8")
time.sleep({segundos})
(salida / "{nombre}.fin").write_text(str(time.time()), encoding="utf-8")
print("=== {comprobaciones} comprobaciones, 0 con")
"""


def _piezas_falsas(tmp_path):
    # Copia mínima: el histórico y los candados tampoco leen las corridas reales de la PC.
    scripts = tmp_path / "scripts" / "prueba_ui"
    scripts.mkdir(parents=True)
    shutil.copy2(TODO, scripts / "todo.py")
    shutil.copy2(TODO.parents[1] / "turno.py", scripts.parent / "turno.py")
    (tmp_path / "clon").mkdir()
    piezas = tmp_path / "piezas"
    piezas.mkdir()
    for nombre in NOMBRES:
        (piezas / f"{nombre}.py").write_text(
            PIEZA.format(nombre=nombre, segundos=DUERMEN[nombre], comprobaciones=COMPROBACIONES[nombre]),
            encoding="utf-8")
    return piezas


def _correr(tmp_path, *argumentos):
    (tmp_path / "tmp").mkdir(exist_ok=True)     # TMP propio: candados de turno.py aislados de la PC
    env = dict(os.environ, OMNICAD_PRUEBA_PIEZAS=str(tmp_path / "piezas"),
               OMNICAD_PRUEBA_SALIDA=str(tmp_path / "salida"), OMNICAD_TURNO_MB="0",
               TMP=str(tmp_path / "tmp"), TEMP=str(tmp_path / "tmp"), TMPDIR=str(tmp_path / "tmp"))
    env.pop("OMNICAD_TURNOS", None)
    r = subprocess.run([sys.executable, str(tmp_path / "scripts" / "prueba_ui" / "todo.py"), *argumentos],
                       capture_output=True, text=True, encoding="utf-8", env=env, timeout=300,
                       cwd=str(tmp_path / "clon"))
    return r.returncode, r.stdout


def _marcas(salida, nombre):
    """(instante de arranque, instante de fin) de una pieza, según lo que anotó ella misma."""
    return (float((salida / f"{nombre}.inicio").read_text(encoding="utf-8")),
            float((salida / f"{nombre}.fin").read_text(encoding="utf-8")))


def _en_orden(texto, nombres):
    """Los nombres aparecen en `texto` en el orden dado (el resumen no sigue el orden de llegada)."""
    return [texto.index(n) for n in nombres] == sorted(texto.index(n) for n in nombres)


def test_sin_paralelo_corre_de_a_una_y_guarda_los_tiempos(tmp_path):
    _piezas_falsas(tmp_path)
    codigo, texto = _correr(tmp_path)
    assert codigo == 0, texto
    assert _en_orden(texto, NOMBRES)
    salida = tmp_path / "salida"
    ini_corta, fin_corta = _marcas(salida, "corta")
    ini_lenta, fin_lenta = _marcas(salida, "lenta")
    ini_media, _ = _marcas(salida, "media")
    assert fin_corta < ini_lenta < fin_lenta < ini_media      # de a una, en orden de PIEZAS
    tiempos = json.loads((salida / "tiempos_piezas.json").read_text(encoding="utf-8"))
    assert set(tiempos) == set(NOMBRES)
    assert all(tiempos[n] >= DUERMEN[n] for n in NOMBRES)


@pytest.mark.parametrize("argumentos", [(), ("--paralelo", "2")])
@pytest.mark.parametrize("origen", ["salida", "evidencias/ui_previa"])
def test_corrida_parcial_combina_tiempos_previos_y_nuevos(tmp_path, argumentos, origen):
    _piezas_falsas(tmp_path)
    anterior = tmp_path / origen / "tiempos_piezas.json"
    anterior.parent.mkdir(parents=True, exist_ok=True)
    previos = {"corta": 999.0, "lenta": 27.0, "otra": 51.0}
    anterior.write_text(json.dumps(previos), encoding="utf-8")

    codigo, texto = _correr(tmp_path, *argumentos, "corta")
    assert codigo == 0, texto
    tiempos = json.loads((tmp_path / "salida" / "tiempos_piezas.json").read_text(encoding="utf-8"))
    assert set(tiempos) == set(previos)
    assert tiempos["lenta"] == previos["lenta"] and tiempos["otra"] == previos["otra"]
    assert DUERMEN["corta"] <= tiempos["corta"] < previos["corta"]
    assert not (tmp_path / "salida" / "lenta.inicio").exists()
    if origen != "salida":
        assert json.loads(anterior.read_text(encoding="utf-8")) == previos


def test_paralelo_corre_dos_a_la_vez_y_arranca_por_la_mas_larga(tmp_path):
    _piezas_falsas(tmp_path)
    salida = tmp_path / "salida"

    codigo, texto = _correr(tmp_path, "--paralelo", "2")
    assert codigo == 0, texto
    assert _en_orden(texto, NOMBRES)                          # el resumen, en el orden de PIEZAS
    for nombre, total in COMPROBACIONES.items():              # las mismas líneas de siempre
        assert texto.index(nombre) < texto.index(f"{total} comprobaciones")
    ini = {n: _marcas(salida, n)[0] for n in NOMBRES}
    fin = {n: _marcas(salida, n)[1] for n in NOMBRES}
    assert ini["lenta"] < fin["corta"]                        # corta y lenta corrieron a la vez…
    assert ini["media"] < fin["lenta"] - 1.0                  # …media también se solapó con lenta…
    assert ini["media"] > fin["corta"] - 0.05                 # …pero nunca tres: media esperó un lugar
    tiempos = json.loads((salida / "tiempos_piezas.json").read_text(encoding="utf-8"))
    assert set(tiempos) == set(NOMBRES) and tiempos["lenta"] > tiempos["media"] > tiempos["corta"]

    codigo, texto = _correr(tmp_path, "--paralelo", "2")      # segunda corrida: usa los tiempos de la primera
    assert codigo == 0, texto
    assert _en_orden(texto, NOMBRES)
    ini = {n: _marcas(salida, n)[0] for n in NOMBRES}
    assert ini["lenta"] < ini["corta"] - 0.5                  # arrancó por la más larga…
    assert ini["media"] < ini["corta"] - 0.5                  # …las dos más largas primero, corta al final

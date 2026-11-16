# -*- coding: utf-8 -*-
"""B-590: cada módulo de operaciones se importa solo, en un intérprete limpio (sin ciclo con operaciones.py)."""
import subprocess
import sys
from pathlib import Path

import pytest

CARPETA = Path(__file__).resolve().parents[1] / "omnicad" / "timeline"
MODULOS = sorted(p.stem for p in CARPETA.glob("ops_*.py"))


@pytest.mark.parametrize("modulo", MODULOS)
def test_el_modulo_se_importa_solo(modulo):
    r = subprocess.run([sys.executable, "-c", f"import omnicad.timeline.{modulo}"], cwd=CARPETA.parents[1],    # sin -I: el cwd (este clon) va primero en sys.path
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr[-600:]

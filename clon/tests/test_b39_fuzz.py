# -*- coding: utf-8 -*-
"""B-39: regresión liviana del fuzzer de uniones (`scripts/fuzz_b39.py`, semilla b39).

Cada caso arma una base (pared, caja hueca, tubo, placa con agujero) y de 1 a 4 herramientas (cilindro, caja, esfera,
toro, prisma, cuña) contra sus caras y aristas con tangencia ± 0…1e-3 mm, y las une una por una. Estos casos fallaban
antes de la defensa de `geo.booleano` (resultado imposible, vacío, dos sólidos por un toro que «no tocaba»…). El fuzzer
completo corre aparte: `python scripts/fuzz_b39.py --casos 1000` (con `--ligero` solo los chequeos de este test)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import fuzz_b39 as fuzz  # noqa: E402


@pytest.mark.parametrize("indice", [185, 112, 283, 960, 383, 9, 24, 92, 204, 11, 23])
def test_b39_fuzzer_caso_fijado_sin_resultado_imposible(indice):
    nombre, herramientas, fallos = fuzz.correr_caso("b39", indice, ligero=True)
    assert not fuzz.graves(fallos), fuzz.descripcion(nombre, herramientas)

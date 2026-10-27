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


# Casos GRAVES de la línea base (fuzz completo del 2026-10-27, 4 000 casos, 23 graves): hoy o se curan o se rechazan
# con error claro (E), nunca salen como geometría silenciosa mala. El 1414 queda fuera a propósito: su resto es una
# arista no manifold nueva en un contacto casi tangente con volumen correcto y cuerpo estanco (la misma clase que la
# unión documentada de dos cajas por una arista, ver test_revision).
@pytest.mark.parametrize("semilla,indice", [
    ("b39", 217), ("b39", 765), ("b39", 791), ("b39", 1057), ("b39", 1101), ("b39", 1342), ("b39", 1438),
    ("b39", 1690), ("b39", 1721), ("b39", 1801), ("b39", 1857), ("b39", 1870), ("b39", 1900),
    ("otra", 547), ("otra", 782), ("otra", 869), ("otra", 1135), ("otra", 1258), ("otra", 1573), ("otra", 1589),
    ("otra", 1864), ("otra", 1935),
])
def test_b39_fuzzer_caso_grave_de_la_linea_base_sin_geometria_silenciosa_mala(semilla, indice):
    nombre, herramientas, fallos = fuzz.correr_caso(semilla, indice, ligero=True)
    assert not fuzz.graves(fallos), fuzz.descripcion(nombre, herramientas)

# -*- coding: utf-8 -*-
"""Mide el solver de bocetos con contornos cerrados de splines encadenadas con tangentes (B-111).

Uso, desde `clon/` (con turno: es una medición pesada):
    .venv/Scripts/python.exe ../scripts/turno.py -- .venv/Scripts/python.exe ../scripts/medir_solver_boceto.py [etiqueta]
        [--sin-cache] [--resolver=10,60,120] [--conflictos=6,12,20] [--corridas=3]
Mide, con la mediana de las corridas: `resolver` con 10/60/120 splines y `restricciones_en_conflicto` con 6/12/20
(boceto en conflicto). `--sin-cache` apaga la caché de splines del solver: así se reproduce el «antes». Escribe evidencias/solver_boceto_<etiqueta>.json (fuera de git) y un resumen por pantalla."""
import json
import statistics
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "clon"))
sys.path.insert(0, str(RAIZ / "clon" / "tests"))

from _contornos import contorno_splines  # noqa: E402

from omnicad.restricciones import solver as S  # noqa: E402

OPCIONES = dict(a[2:].split("=", 1) for a in sys.argv[1:] if a.startswith("--") and "=" in a)
CORRIDAS = int(OPCIONES.get("corridas", 3))
LISTA = lambda clave, por_defecto: [int(n) for n in OPCIONES.get(clave, por_defecto).split(",") if n]  # noqa: E731


def mediana_ms(f):
    t = []
    for _ in range(CORRIDAS):
        t0 = time.perf_counter()
        f()
        t.append((time.perf_counter() - t0) * 1000)
    return round(statistics.median(t), 1)


def main():
    etiqueta = next((a for a in sys.argv[1:] if not a.startswith("--")), "medida")
    S.CACHE_SPLINES = "--sin-cache" not in sys.argv
    res = {"resolver_ms": {}, "conflictos_ms": {}}
    for n in LISTA("resolver", "10,60,120"):
        res["resolver_ms"][n] = mediana_ms(lambda n=n: S.resolver(*contorno_splines(n)))
        print(f"resolver {n:>3} splines: {res['resolver_ms'][n]:>9} ms", flush=True)
    r = res["resolver_ms"]
    if 60 in r and 120 in r:
        res["pendiente_120_60"] = round(r[120] / r[60], 2)
        print(f"t120/t60 = {res['pendiente_120_60']}")
    for n in LISTA("conflictos", "6,12,20"):
        res["conflictos_ms"][n] = mediana_ms(lambda n=n: S.restricciones_en_conflicto(*contorno_splines(n, conflicto=True)))
        print(f"conflictos {n:>3} splines: {res['conflictos_ms'][n]:>9} ms", flush=True)
    salida = RAIZ / "evidencias" / f"solver_boceto_{etiqueta}.json"
    salida.parent.mkdir(exist_ok=True)
    salida.write_text(json.dumps(res, indent=1), encoding="utf-8")
    print("->", salida)


if __name__ == "__main__":
    main()

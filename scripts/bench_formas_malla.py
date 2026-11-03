# -*- coding: utf-8 -*-
"""Banco de la medición de formas de malla (H-57): cuánto tarda `formas_malla.medir` en una pieza con
muchas caras chicas. La malla se arma acá (placa con retícula de cajeras y agujeros, refinada), sin
archivos de afuera, y es determinista: las 3 corridas dan la misma ficha.

Uso (desde `clon/`, con turno):
    .venv/Scripts/python.exe ../scripts/turno.py -- .venv/Scripts/python.exe ../scripts/bench_formas_malla.py
Imprime el tiempo de cada corrida, la mediana y la cantidad y tipos de formas halladas.
"""
import statistics
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "clon"))

from omnicad.nucleo import geometria as geo  # noqa: E402
from omnicad.nucleo import malla as ml  # noqa: E402
from omnicad.nucleo import formas_malla as fm  # noqa: E402

CORRIDAS = 3
TOL = 0.05          # desviación de la teselación (mm): deja caras chicas
REFINO = 7.5        # longitud máxima del refino (mm): sube a ~19.000 triángulos


def _pieza():
    """Placa 180×130×8 con 6×5 cajeras cuadradas y 6 agujeros cilíndricos, mallada fina."""
    placa = geo.caja(180, 130, 8, (0, 0, 0))
    for i in range(6):
        for j in range(5):
            cajera = geo.caja(16, 12, 3, (10 + i * 28, 15 + j * 22, 5))
            placa = geo.booleano(placa, cajera, "cortar")
    for i in range(6):
        placa = geo.booleano(placa, geo.cilindro(5, 12, (15 + i * 30, 118, -2)), "cortar")
    m = ml.desde_brep(placa, refinamiento="personalizado", desviacion=TOL, angulo=40)
    if m.caras.shape[0] < 10000:
        m = ml.refinar_triangulos(m, longitud_maxima=REFINO)
    return m


def main():
    m = _pieza()
    print(f"malla: {len(m.caras)} triángulos")
    tiempos, ficha = [], None
    for k in range(CORRIDAS):
        t0 = time.perf_counter()
        ficha = fm.analizar(m)
        tiempos.append(time.perf_counter() - t0)
        print(f"corrida {k + 1}: {tiempos[-1]:.2f} s")
    print(f"mediana de {CORRIDAS}: {statistics.median(tiempos):.2f} s")
    print(f"formas: {len(ficha['shapes'])}  resumen: {ficha['summary']}")
    print(f"sin clasificar: {ficha['unclassified_percent']} %")


if __name__ == "__main__":
    main()

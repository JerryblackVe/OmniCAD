# -*- coding: utf-8 -*-
"""Medidas del sistema de restricciones del boceto (mediana de 3 corridas) con 10, 100 y 400 piezas:
resolver completo, agregar una restricción, un paso de arrastre, GDL, diagnóstico de redundancia y pintar los símbolos.
Uso (desde clon/, con turno):  .venv/Scripts/python.exe ../scripts/turno.py -- .venv/Scripts/python.exe ../scripts/bench_restricciones.py [salida.json]
Cada línea del resultado: tamaño, operación, mediana en ms (y mínimo / máximo)."""
import json
import os
import statistics
import sys
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "clon"))

from omnicad.restricciones import Boceto, grados_de_libertad, resolver, restricciones_redundantes  # noqa: E402
from omnicad.timeline.parametros import TablaParametros  # noqa: E402


def cadena(n):
    """n piezas: una escalera de líneas unidas por sus extremos, con horizontal/vertical y una igual cada tres."""
    b = Boceto()
    pts = [b.agregar_punto(40 + 12 * (i // 2), 30 + (25 if i % 2 else 0) + 3 * (i % 5)) for i in range(n + 1)]
    ls = [b.agregar_linea(pts[i], pts[i + 1]) for i in range(n)]
    for i, l in enumerate(ls):
        if i % 2 == 0:
            b.agregar_restriccion("vertical", [l])
        if i % 3 == 0 and i + 2 < n:
            b.agregar_restriccion("igual", [l, ls[i + 2]])
    return b, pts, ls


def medir(f, veces=3):
    t = []
    for _ in range(veces):
        t0 = time.perf_counter()
        f()
        t.append((time.perf_counter() - t0) * 1000)
    return {"mediana_ms": round(statistics.median(t), 2), "min_ms": round(min(t), 2), "max_ms": round(max(t), 2)}


def pintar(b):
    from PySide6.QtWidgets import QApplication

    from omnicad.ui import editor_boceto
    app = QApplication.instance() or QApplication([])      # noqa: F841
    lz = editor_boceto.Lienzo(b.copia(), TablaParametros().evaluar)
    lz.resize(1400, 900)
    lz.show()
    lz.resolver()
    lz.encuadrar()
    lz.grab()
    r = medir(lz.grab)                                       # pintar de verdad (repaint no pinta si la ventana no está a la vista)
    lz.close()
    return r


def main():
    salida = {}
    for n in (10, 100, 400):
        b, pts, ls = cadena(n)
        res = {}
        res["resolver_completo"] = medir(lambda: resolver(b.copia(), {}))
        res["grados_de_libertad"] = medir(lambda: grados_de_libertad(b))
        b2 = b.copia()
        previo = resolver(b2, {})
        medio = pts[len(pts) // 2]

        def paso():
            b2.puntos[medio].x += 0.5
            resolver(b2, {}, arrastrado=medio, previo=previo)
        res["paso_de_arrastre"] = medir(paso, 5)

        def agregar():
            c = b.copia()
            c.agregar_restriccion("paralela", [ls[1], ls[3]])
            resolver(c, {})
        res["agregar_restriccion_y_resolver"] = medir(agregar)
        res["redundantes"] = medir(lambda: restricciones_redundantes(b, {}), 1)
        res["pintar_con_simbolos"] = pintar(b)
        res["restricciones"] = len(b.restricciones)
        salida[str(n)] = res
        print(n, json.dumps(res, ensure_ascii=False), flush=True)
    if len(sys.argv) > 1:
        Path(sys.argv[1]).write_text(json.dumps(salida, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()

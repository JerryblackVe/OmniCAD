# -*- coding: utf-8 -*-
"""B-111: la ventana local del arrastre frente al arrastre completo, en bocetos de splines encadenadas con tangentes.

Uso, desde `clon/` (con turno): .venv/Scripts/python.exe ../scripts/turno.py --plazo 280 -- .venv/Scripts/python.exe
    ../scripts/medir_ventana_arrastre.py [--splines=20,60] [--arrastres=25] [--radio=2]
Por cada arrastre (6 movimientos de 0,4 mm en una dirección distinta, y soltar = `resolver` completo) y desde el MISMO
boceto resuelto, resuelve con la ventana y con el arrastre completo y compara. Escribe evidencias/ventana_arrastre.json."""
import copy
import json
import math
import statistics
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "clon"))
sys.path.insert(0, str(RAIZ / "clon" / "tests"))

from _contornos import contorno_splines  # noqa: E402

from omnicad.restricciones import solver as S  # noqa: E402

OPC = dict(a[2:].split("=", 1) for a in sys.argv[1:] if a.startswith("--") and "=" in a)
LISTA = [int(n) for n in OPC.get("splines", "20,60").split(",")]
ARRASTRES, PASOS, PASO_MM = int(OPC.get("arrastres", 25)), 6, 0.4
if "radio" in OPC:
    S.RADIO_VENTANA = int(OPC["radio"])


def arrastrar(base, previo, v, pid, k, ventana):
    """Un arrastre completo sobre una copia de `base`; devuelve (boceto soltado, resultado al soltar, tiempos por movimiento)."""
    S.UMBRAL_VENTANA = 40 if ventana else 10**9
    b, t = base.copia(), []
    x0, y0 = b.coords(pid)
    ang = 2 * math.pi * k / ARRASTRES
    for i in range(1, PASOS + 1):
        b.puntos[pid].x, b.puntos[pid].y = x0 + PASO_MM * i * math.cos(ang), y0 + PASO_MM * i * math.sin(ang)
        t0 = time.perf_counter()
        S.resolver(b, v, pid, previo)
        t.append(time.perf_counter() - t0)
    t0 = time.perf_counter()
    r = S.resolver(b, v)                       # soltar: resuelve todo
    return b, r, t, time.perf_counter() - t0, (x0 + PASO_MM * PASOS * math.cos(ang), y0 + PASO_MM * PASOS * math.sin(ang))


def main():
    salida = {}
    for n in LISTA:
        base, v = contorno_splines(n)
        previo = S.resolver(base, v)
        libres = [p for p in base.puntos if p not in base.puntos_fijos()]
        filas, mov = [], {True: [], False: []}
        for k in range(ARRASTRES):
            pid = libres[(7 * k + 5) % len(libres)]
            comp = arrastrar(base, previo, v, pid, k, False)
            vent = arrastrar(base, previo, v, pid, k, True)
            mov[False] += comp[2]
            mov[True] += vent[2]
            desp = {p: math.dist(comp[0].coords(p), vent[0].coords(p)) for p in base.puntos}
            fuera = [d for p, d in desp.items() if math.dist(base.coords(p), comp[0].coords(p)) < 1e-6]
            filas.append({"punto": pid, "desplazamiento_max_mm": max(desp.values()),
                          "desplazamiento_de_lo_que_el_completo_no_movio_mm": max(fuera, default=0.0),
                          "ok": vent[1].ok, "gdl": (vent[1].gdl, comp[1].gdl), "determinadas_iguales": vent[1].determinadas == comp[1].determinadas,
                          "residuo": vent[1].residuo_max, "punto_soltado_error_mm": math.dist(vent[0].coords(pid), vent[4]),
                          "soltar_s": (round(vent[3], 3), round(comp[3], 3))})
        p95 = lambda xs: sorted(xs)[int(0.95 * (len(xs) - 1))]  # noqa: E731
        salida[n] = {"mover_completo_ms": {"mediana": round(1000 * statistics.median(mov[False]), 1), "p95": round(1000 * p95(mov[False]), 1), "max": round(1000 * max(mov[False]), 1)},
                     "mover_ventana_ms": {"mediana": round(1000 * statistics.median(mov[True]), 1), "p95": round(1000 * p95(mov[True]), 1), "max": round(1000 * max(mov[True]), 1)},
                     "desplazamiento_max_mm": max(f["desplazamiento_max_mm"] for f in filas),
                     "todos_ok": all(f["ok"] for f in filas), "gdl_iguales": all(f["gdl"][0] == f["gdl"][1] for f in filas),
                     "determinadas_iguales": all(f["determinadas_iguales"] for f in filas),
                     "residuo_max": max(f["residuo"] for f in filas), "punto_soltado_error_max_mm": max(f["punto_soltado_error_mm"] for f in filas),
                     "arrastres": filas}
        r = copy.copy(salida[n])
        r.pop("arrastres")
        print(n, json.dumps(r, ensure_ascii=False), flush=True)
    destino = RAIZ / "evidencias" / "ventana_arrastre.json"
    destino.parent.mkdir(exist_ok=True)
    destino.write_text(json.dumps(salida, indent=1, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()

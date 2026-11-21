# -*- coding: utf-8 -*-
"""Banco de velocidad de las operaciones del boceto (plan_fluidez §3): cada operación sobre un boceto de ~N piezas.
Uso (desde clon/): xvfb-run -a .venv/bin/python ../scripts/turno.py -- .venv/bin/python ../scripts/bench_boceto_ops.py [N]
Imprime operación y ms; marca con ⚠ lo que pasa de 500 ms (cada una es una fila P-)."""
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "clon"))
from omnicad.restricciones import Boceto  # noqa: E402


def base(n):
    """Grilla de n/2 rectángulos y círculos, todos cortados por dos líneas largas."""
    b = Boceto()
    cols = max(2, int(n ** 0.5))
    rects, circs = [], []
    for i in range(n // 2):
        x, y = 30 * (i % cols), 30 * (i // cols)
        rects.append(b.agregar_rectangulo((x, y), (x + 20, y + 15)))
        circs.append(b.agregar_circulo(b.agregar_punto(x + 10, y + 7), 4))
    h = b.agregar_linea(b.agregar_punto(-5, 7), b.agregar_punto(30 * cols, 7))
    return b, rects, circs, h


def ids_de(b):
    return list(b.curvas)


def medir(nombre, f, preparar):
    t = []
    for _ in range(3):
        ctx = preparar()
        t0 = time.perf_counter()
        try:
            f(*ctx)
            ok = ""
        except Exception as e:  # una operación que no aplica no frena el banco
            ok = f" (error: {str(e)[:50]})"
        t.append((time.perf_counter() - t0) * 1000)
    m = statistics.median(t)
    print(f"{'⚠ ' if m > 500 else '  '}{nombre:28s} {m:9.1f} ms{ok}", flush=True)


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    P = lambda: (lambda b, r, c, h: (b, r, c, h))(*base(n))  # noqa: E731
    todos = lambda b: list(b.curvas)  # noqa: E731
    medir("recortar (línea cruza todo)", lambda b, r, c, h: b.recortar(h, (3, 7)), P)
    medir("partir", lambda b, r, c, h: b.partir(h, (50, 7)), P)
    medir("alargar", lambda b, r, c, h: b.alargar(h, (-5, 7)), P)
    medir("desfase círculo", lambda b, r, c, h: b.desfase(c[0], 1.0, punto_lado=(100, 100)), P)
    medir("patron_rectangular 10x10", lambda b, r, c, h: b.patron_rectangular([c[0]], 10, 5, 10, 5), P)
    medir("patron_circular 50", lambda b, r, c, h: b.patron_circular([c[0]], (500, 500), 50), P)
    medir("simetria todo", lambda b, r, c, h: b.simetria(todos(b), h), P)
    medir("transformar copiar todo", lambda b, r, c, h: b.transformar(todos(b), dx=3, copiar=True), P)
    medir("escalar todo", lambda b, r, c, h: b.escalar(todos(b), (0, 0), 1.5), P)
    medir("limpiar", lambda b, r, c, h: b.limpiar(), P)
    medir("copia del boceto", lambda b, r, c, h: b.copia(), P)


if __name__ == "__main__":
    main()

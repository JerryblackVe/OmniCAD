"""RS-X3: hover y repintado del Lienzo de boceto 2D con muchas curvas (líneas, círculos, arcos y splines al azar).

Uso, desde `clon/` (con turno; no abre ventana: plataforma offscreen):
    .venv/Scripts/python.exe ../scripts/turno.py -- .venv/Scripts/python.exe ../scripts/medir_paint_boceto.py [100,400,2000]
Mide, con la mediana de varias corridas:
  - hover: `_curva_cercana` en 60 lugares al azar;
  - paintEvent sin cambios en pantalla (el cursor se mueve: se pega la imagen guardada de las curvas);
  - paintEvent rearmando esa imagen (cambió el hover, la selección…).
Meta de RS-X3 (en una máquina sin carga): 400 curvas con hover de 1 ms o menos y repintado de 8 ms o menos."""
import os
import random
import statistics
import sys
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "clon"))

from PySide6.QtCore import QPointF  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from omnicad.nucleo import geometria as g  # noqa: E402
from omnicad.restricciones import Boceto  # noqa: E402
from omnicad.timeline.parametros import TablaParametros  # noqa: E402
from omnicad.ui.editor_boceto import Lienzo  # noqa: E402


def boceto(n):
    b, rnd = Boceto(), random.Random(1)
    for i in range(n):
        x, y = rnd.uniform(-200, 200), rnd.uniform(-120, 120)
        if i % 4 == 0:
            b.agregar_linea(b.agregar_punto(x, y), b.agregar_punto(x + rnd.uniform(-20, 20), y + rnd.uniform(-20, 20)))
        elif i % 4 == 1:
            b.agregar_circulo(b.agregar_punto(x, y), rnd.uniform(1, 8))
        elif i % 4 == 2:
            r = rnd.uniform(2, 10)
            b.agregar_arco_centro(b.agregar_punto(x, y), b.agregar_punto(x + r, y), b.agregar_punto(x, y + r))
        else:
            b.agregar_spline([b.agregar_punto(x + 5 * j, y + rnd.uniform(-5, 5)) for j in range(4)])
    return b


TIEMPOS = []


class Medido(Lienzo):
    def paintEvent(self, e):
        t0 = time.perf_counter()
        super().paintEvent(e)
        TIEMPOS.append(time.perf_counter() - t0)


def main():
    QApplication.instance() or QApplication([])
    for n in [int(a) for a in (sys.argv[1] if len(sys.argv) > 1 else "100,400,2000").split(",")]:
        lz = Medido(boceto(n), TablaParametros().evaluar, plano=g.Plano("XY"))
        lz.resize(1200, 800)
        lz.encuadrar()
        lz.set_herramienta("seleccionar")
        lz.grab()
        rnd = random.Random(2)
        hover = []
        for _ in range(60):
            p = QPointF(rnd.uniform(0, 1200), rnd.uniform(0, 800))
            t0 = time.perf_counter()
            lz._curva_cercana(p, interior=True)
            hover.append(time.perf_counter() - t0)
        TIEMPOS.clear()
        for _ in range(15):
            lz.grab()
        quieto = statistics.median(TIEMPOS)
        TIEMPOS.clear()
        for _ in range(5):
            lz._capa_clave = None
            lz.grab()
        print(f"{n:5d} curvas: hover {1000 * statistics.median(hover):6.2f} ms | repintado sin cambios "
              f"{1000 * quieto:6.1f} ms | rearmando la imagen {1000 * statistics.median(TIEMPOS):6.1f} ms", flush=True)
        lz.close()


if __name__ == "__main__":
    main()

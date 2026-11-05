# -*- coding: utf-8 -*-
"""Latencias con panel real, imanes activos y eventos Qt. Ejecutar antes y después con el mismo comando.

Desde clon/: .venv/Scripts/python.exe ../scripts/medir_manipulacion_vectorial.py --salida ../evidencias/vectores_antes.json
La frecuencia informada es capacidad de actualización del widget; no es FPS de presentación del monitor.
"""
import argparse
import json
import os
from pathlib import Path
import platform
import statistics
import sys
import tempfile
import time

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "clon"))
os.environ.setdefault("OMNICAD_SIN_ANIMACION", "1")

from PySide6.QtCore import QEvent, Qt  # noqa: E402
from PySide6.QtGui import QMouseEvent  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from bench_objetos_vectoriales import logo  # noqa: E402
from omnicad.io_archivos.boceto_archivos import boceto_desde_primitivas  # noqa: E402
from omnicad.io_archivos.svg import leer_svg  # noqa: E402
from omnicad.restricciones import objetos as ob  # noqa: E402
from omnicad.timeline.documento import Documento  # noqa: E402
from omnicad.timeline.operaciones import OpBoceto  # noqa: E402
from omnicad.timeline.parametros import TablaParametros  # noqa: E402
from omnicad.ui.editor_boceto import Lienzo  # noqa: E402
from omnicad.ui.objetos_vectoriales import PanelObjetos  # noqa: E402


def tiempo(f):
    t = time.perf_counter()
    r = f()
    return 1000 * (time.perf_counter() - t), r


def raton(lz, tipo, xy):
    pos = lz.a_px(*xy)
    QApplication.sendEvent(lz, QMouseEvent(tipo, pos, lz.mapToGlobal(pos),
        Qt.NoButton if tipo == QEvent.MouseMove else Qt.LeftButton,
        Qt.NoButton if tipo == QEvent.MouseButtonRelease else Qt.LeftButton, Qt.NoModifier))


def medir(ruta):
    b = boceto_desde_primitivas(leer_svg(ruta))
    lz = Lienzo(b, TablaParametros().evaluar)
    lz.resize(1200, 800)
    lz.centro, lz.escala = [50, 50], 5
    panel = PanelObjetos(lz.objetos, lz)
    panel.move(900, 0)
    lz.grab()
    punto = (4, 96)
    seleccion, _ = tiempo(lambda: raton(lz, QEvent.MouseButtonPress, punto))
    raton(lz, QEvent.MouseButtonRelease, punto)
    oid = ob.raices(b)[0]
    assert lz.objetos.seleccion() == [oid]
    panel.sincronizar()
    panel.show()
    lz.grab()
    antes = b.a_dict()
    inicio, _ = tiempo(lambda: raton(lz, QEvent.MouseButtonPress, punto))
    eventos, cuadros = [], []
    for k in range(1, 61):
        destino = (punto[0] + k / 2, punto[1] - k / 4)
        t, _ = tiempo(lambda destino=destino: raton(lz, QEvent.MouseMove, destino))
        eventos.append(t)
        t, _ = tiempo(lz.grab)
        cuadros.append(t)
    assert b.a_dict() == antes
    confirmar, _ = tiempo(lambda: raton(lz, QEvent.MouseButtonRelease, destino))
    doc = Documento()
    recalculo, _ = tiempo(lambda: doc.agregar(OpBoceto("logo", boceto=b.copia())))
    lz.close()
    lz.deleteLater()
    QApplication.processEvents()
    total = [a + b for a, b in zip(eventos, cuadros, strict=True)]
    return {"curvas": len(b.curvas), "seleccion_ms": seleccion, "inicio_ms": inicio,
            "evento_p50_ms": statistics.median(eventos), "pintado_p50_ms": statistics.median(cuadros),
            "cuadro_p50_ms": statistics.median(total), "cuadro_p95_ms": sorted(total)[56],
            "capacidad_actualizaciones_hz": 1000 / statistics.median(total),
            "liberacion_y_confirmacion_ms": confirmar, "timeline_ms": recalculo,
            "muestras_evento_ms": eventos, "muestras_pintado_ms": cuadros}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--salida", type=Path, required=True)
    args = parser.parse_args()
    app = QApplication.instance() or QApplication([])
    resultados = {}
    with tempfile.TemporaryDirectory(dir=RAIZ / "evidencias", prefix="vector_medicion_") as carpeta:
        for nombre, contenido in (("sencillo", '<svg width="100mm" height="100mm" viewBox="0 0 100 100"><rect x="2" y="2" width="20" height="10"/></svg>'), ("complejo", logo())):
            ruta = Path(carpeta) / f"{nombre}.svg"
            ruta.write_text(contenido, encoding="utf-8")
            resultados[nombre] = [medir(ruta) for _ in range(3)]
    datos = {"entorno": {"python": platform.python_version(), "plataforma": platform.platform(),
                          "qt": app.platformName(), "tamano_widget": [1200, 800], "panel": True, "imanes": True},
             "corridas": resultados,
             "medianas": {n: {k: statistics.median(r[k] for r in filas) for k in filas[0]
                               if not k.startswith("muestras_")} for n, filas in resultados.items()}}
    args.salida.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(datos["medianas"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""P-45: fluidez de las vistas animadas (ViewCube / Ajustar / mirar al boceto) en la ventana real.

Cambia 24 veces entre las vistas frente, derecha, arriba e isométrica con `Visor3D.animar_vista` y mide los
intervalos entre cuadros presentados (`frameSwapped`) durante cada transición de ~250 ms. Escena: la placa de 200
agujeros de `medir_previa_comandos.py`. Criterio: ≥ 99 % de los cuadros ≤ 20 ms.

Uso, desde `clon/`:
    .venv/Scripts/python.exe ../scripts/turno.py -- .venv/Scripts/python.exe ../scripts/medir_vistas.py [etiqueta]
No mover el mouse ni usar el teclado mientras corre. Deja `evidencias/vistas_<etiqueta>.json`.
"""
import json
import os
import runpy
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "prueba_ui"))

import arnes as A  # noqa: E402
import numpy as np  # noqa: E402
from omnicad.timeline.documento import Documento  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402

os.environ.pop("OMNICAD_SIN_ANIMACION", None)          # el arnés lo fija para las pruebas; acá se mide la animación


def main():
    etiqueta = sys.argv[1] if len(sys.argv) > 1 else "medida"
    receta, _ = runpy.run_path(str(Path(__file__).resolve().parent / "medir_previa_comandos.py"))["_modelo"]("placa200")
    doc = Documento.desde_dict(receta)
    doc.recalcular(0)
    app, v = A.iniciar(doc)
    vi = v.visor
    vi.config.animar_vistas = True
    A.esperar(600)
    swaps = []
    vi.frameSwapped.connect(lambda: swaps.append(time.perf_counter()))
    vi.animar_vista(lambda: vi.vista("iso"))
    A.esperar(500)
    intervalos, duraciones, cortes, por_transicion, paso_ms = [], [], 0, [], []
    original = vi._paso_animacion

    def medir_paso():
        t = time.perf_counter()
        original()
        paso_ms.append((time.perf_counter() - t) * 1000)

    vi._t_animacion.timeout.disconnect()
    vi._t_animacion.timeout.connect(medir_paso)
    secuencia = ["frente", "derecha", "arriba", "iso"] * 6
    for nombre in secuencia:
        inicio = time.perf_counter()
        swaps.clear()
        vi.animar_vista(lambda n=nombre: vi.vista(n))
        if vi._animacion is None:
            continue
        while vi._animacion is not None and time.perf_counter() - inicio < 2:
            QTest.qWait(4)
        duraciones.append(round((time.perf_counter() - inicio) * 1000, 1))
        QTest.qWait(60)
        activos = [t for t in swaps if t >= inicio]
        intervalos += list(np.diff(activos) * 1000)
        por_transicion.append([round(x, 1) for x in np.diff(activos) * 1000])
        cortes += vi._animacion is not None
        A.esperar(120)
    iv = np.array(intervalos)
    r = {"etiqueta": etiqueta, "transiciones": len(duraciones), "duracion_ms": {"min": min(duraciones), "max": max(duraciones)},
         "cuadros": len(iv), "p50": round(float(np.percentile(iv, 50)), 2), "p95": round(float(np.percentile(iv, 95)), 2),
         "p99": round(float(np.percentile(iv, 99)), 2), "max": round(float(iv.max()), 2),
         "pct_cuadros_<=20ms": round(float((iv <= 20).mean() * 100), 2), "mayores_20ms": int((iv > 20).sum()),
         "mayores_33ms": int((iv > 33.4).sum()), "sin_terminar": int(cortes), "gl": vi.info_gl,
         "paso_animacion_ms": {"p50": round(float(np.percentile(paso_ms, 50)), 2), "p95": round(float(np.percentile(paso_ms, 95)), 2), "max": round(max(paso_ms), 2), "n": len(paso_ms)},
         "intervalos_por_transicion": por_transicion, "excepciones_en_slots": list(A.ERRORES)}
    ruta = Path(__file__).resolve().parents[1] / "evidencias" / f"vistas_{etiqueta}.json"
    ruta.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(r, ensure_ascii=False, indent=1))
    v.doc.modificado = False
    v.close()


main()

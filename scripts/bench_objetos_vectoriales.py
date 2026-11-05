# -*- coding: utf-8 -*-
"""Banco pareado reproducible: el MISMO SVG como curvas sueltas y como objeto lógico.

Desde clon/: .venv/Scripts/python.exe ../scripts/bench_objetos_vectoriales.py
No abre documentos del usuario ni mueve el cursor. Las medidas son medianas de tres corridas.
"""
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
os.environ.setdefault("QT_QPA_PLATFORM", "windows" if sys.platform == "win32" else "offscreen")
os.environ.setdefault("OMNICAD_SIN_ANIMACION", "1")

from PySide6.QtCore import QEvent, Qt  # noqa: E402
from PySide6.QtGui import QMouseEvent  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from omnicad import api  # noqa: E402
from omnicad.io_archivos.boceto_archivos import boceto_desde_primitivas  # noqa: E402
from omnicad.io_archivos.svg import leer_svg  # noqa: E402
from omnicad.nucleo import geometria as geo  # noqa: E402
from omnicad.nucleo.perfiles import detectar_boceto  # noqa: E402
from omnicad.restricciones import resolver  # noqa: E402
from omnicad.timeline.documento import Documento  # noqa: E402
from omnicad.timeline.operaciones import OpBoceto  # noqa: E402
from omnicad.timeline.parametros import TablaParametros  # noqa: E402
from omnicad.ui.editor_boceto import Lienzo  # noqa: E402


def logo():
    paths = []
    for i in range(151):
        x, y = 2 + (i % 13) * 7, 2 + (i // 13) * 7
        paths.append(f'<path d="M{x} {y} C{x+1} {y-1} {x+3} {y-1} {x+4} {y} '
                     f'L{x+4} {y+3} C{x+3} {y+4} {x+1} {y+4} {x} {y+3} Z"/>')
    paths.extend(('<circle cx="96" cy="30" r="2"/>', '<circle cx="96" cy="50" r="2"/>'))
    return '<svg width="100mm" height="100mm" viewBox="0 0 100 100">' + ''.join(paths) + '</svg>'


def raton(lz, tipo, xy):
    pos = lz.a_px(*xy)
    QApplication.sendEvent(lz, QMouseEvent(tipo, pos, lz.mapToGlobal(pos),
                                          Qt.NoButton if tipo == QEvent.MouseMove else Qt.LeftButton,
                                          Qt.NoButton if tipo == QEvent.MouseButtonRelease else Qt.LeftButton,
                                          Qt.NoModifier))


def tiempo(funcion):
    inicio = time.perf_counter()
    resultado = funcion()
    return (time.perf_counter() - inicio) * 1000, resultado


def medir(ruta, agrupado):
    prims = leer_svg(ruta)
    prims.como_objeto = agrupado
    t_importar, b = tiempo(lambda: boceto_desde_primitivas(prims))
    t_solver, resultado = tiempo(lambda: resolver(b))
    t_perfiles, perfiles = tiempo(lambda: detectar_boceto(b, geo.Plano("XY")))
    lz = Lienzo(b, TablaParametros().evaluar)
    lz.resize(1000, 800)
    lz.centro = [50, 50]
    lz.escala = 6
    lz.ajustar_grilla = False
    lz.objetos.snap = False
    lz.grab()  # precalienta las muestras y la representación, igual en las dos variantes
    punto = (4, 96)
    t_clic, elegido = tiempo(lambda: lz.entidad_en(lz.a_px(*punto)))
    if agrupado:
        lz.seleccion = [elegido]
    else:
        lz._seleccionar_ventana(lz.a_px(0, 100), lz.a_px(100, 0))
    cantidad = len(lz.seleccion)
    lz.grab()
    if agrupado:
        t_inicio, _ = tiempo(lambda: raton(lz, QEvent.MouseButtonPress, punto))
    else:
        centro = (50, 50)
        t_inicio, _ = tiempo(lambda: lz._presionar_marco(lz.a_px(*centro)))
        if lz._marco is None:
            lz._marco = {"tipo": "mover", "caja": lz._caja_marco(), "inicio": centro, "actual": centro,
                         "px_inicio": lz.a_px(*centro), "px_actual": lz.a_px(*centro), "shift": False}
    cuadros = []
    for k in range(1, 13):
        destino = (punto[0] + k, punto[1] - 3) if agrupado else (50 + k, 47)
        t, _ = tiempo(lambda destino=destino: (raton(lz, QEvent.MouseMove, destino), lz.grab()))
        cuadros.append(t)
    t_confirmar, _ = tiempo(lambda: raton(lz, QEvent.MouseButtonRelease, destino))
    doc = Documento()
    t_recalculo, _ = tiempo(lambda: doc.agregar(OpBoceto("logo", boceto=b.copia())))
    s = api.Sesion(doc)
    t_extruir, extrusion = tiempo(lambda: api.llamar(s, "extrude", {"sketch": "logo", "profile": "sketch", "distance": 2}))
    if not extrusion["ok"]:
        raise RuntimeError(extrusion)
    volumen = sum(geo.volumen(c.forma) for c in doc.estado_final.cuerpos.values())
    assert all(geo.es_valida(c.forma) for c in doc.estado_final.cuerpos.values())
    lz.close()
    lz.deleteLater()
    QApplication.processEvents()
    return {"curvas": len(b.curvas), "puntos_originales": len(b.puntos), "gdl_internos": resultado.gdl,
            "elementos_seleccionados": cantidad, "perfiles": len(perfiles), "volumen_mm3": volumen,
            "importacion_ms": t_importar, "solver_ms": t_solver, "perfiles_ms": t_perfiles,
            "clic_ms": t_clic, "inicio_arrastre_ms": t_inicio, "cuadro_previa_mediana_ms": statistics.median(cuadros),
            "cuadro_previa_p95_ms": sorted(cuadros)[-1], "confirmacion_ms": t_confirmar,
            "recalculo_ms": t_recalculo, "extrusion_ms": t_extruir}


def main():
    app = QApplication.instance() or QApplication([])
    resultados = {"curvas_sueltas": [], "objeto": []}
    with tempfile.TemporaryDirectory(prefix="bench_vectores_", dir=RAIZ / "evidencias") as carpeta:
        ruta = Path(carpeta) / "logo_606.svg"
        ruta.write_text(logo(), encoding="utf-8")
        if "--perfil" in sys.argv:
            import cProfile
            import pstats
            perfil = cProfile.Profile()
            perfil.runcall(medir, ruta, True)
            pstats.Stats(perfil).strip_dirs().sort_stats("cumtime").print_stats(35)
            pstats.Stats(perfil).strip_dirs().sort_stats("cumtime").print_stats("objetos_vectoriales|drawPath|map|primitivas")
            return
        for _ in range(3):
            for modo, agrupado in (("curvas_sueltas", False), ("objeto", True)):
                resultados[modo].append(medir(ruta, agrupado))
    resumen = {m: {k: statistics.median(r[k] for r in filas) for k in filas[0]} for m, filas in resultados.items()}
    print(json.dumps({"entorno": {"sistema": platform.platform(), "cpu": platform.processor(),
                                   "procesadores_logicos": os.cpu_count(), "python": platform.python_version(),
                                   "qt": app.platformName(), "tamano_widget": [1000, 800]},
                      "svg_bytes": len(logo().encode()), "corridas": resultados, "medianas": resumen}, indent=2))


if __name__ == "__main__":
    main()

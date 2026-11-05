# -*- coding: utf-8 -*-
"""Medición de eventos, repintados y presentación OpenGL en la ventana real, sin mover el cursor físico."""
import argparse
import json
from pathlib import Path
import statistics
import sys
import tempfile
import time

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts" / "prueba_ui"))
import arnes as A  # noqa: E402
from bench_objetos_vectoriales import logo  # noqa: E402
from PySide6.QtCore import QEvent, QEventLoop, QObject, QPointF, Qt, QTimer  # noqa: E402
from PySide6.QtGui import QMouseEvent  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402
from omnicad import api  # noqa: E402


class Pintados(QObject):
    def __init__(self, widget):
        super().__init__(widget)
        self.cuadros, self.retrasos = [], []
        self.evento = None
        widget.installEventFilter(self)

    def eventFilter(self, _objeto, e):
        if e.type() == QEvent.Paint and self.evento is not None:
            t = time.perf_counter()
            self.cuadros.append(t)
            self.retrasos.append(1000 * (t - self.evento))
        return False


def raton(visor, tipo, pos):
    pos = QPointF(pos)
    QApplication.sendEvent(visor, QMouseEvent(tipo, pos, visor.mapToGlobal(pos),
        Qt.NoButton if tipo == QEvent.MouseMove else Qt.LeftButton,
        Qt.NoButton if tipo == QEvent.MouseButtonRelease else Qt.LeftButton, Qt.NoModifier))


def resumen(valores):
    return {"p50_ms": statistics.median(valores), "p95_ms": sorted(valores)[int(.95 * (len(valores) - 1))],
            "maximo_ms": max(valores)}


def medir(v, doc, punto, perfilar=False):
    v.set_documento(doc)
    v.visor.vista("arriba")
    A.esperar(100)
    v.visor.encuadrar()
    A.esperar(150)
    q = v.visor.proyectar([*punto, 0])
    t = time.perf_counter()
    raton(v.visor, QEvent.MouseButtonPress, q)
    raton(v.visor, QEvent.MouseButtonRelease, q)
    seleccion = 1000 * (time.perf_counter() - t)
    lz = v.vectores.activo
    assert lz is not None and len(lz.objetos.seleccion()) == 1
    lz.objetos.snap = False
    A.esperar(100)
    pintados = Pintados(lz)
    presentados = []
    presentar = lambda: presentados.append(time.perf_counter())
    v.visor.frameSwapped.connect(presentar)
    t = time.perf_counter()
    raton(v.visor, QEvent.MouseButtonPress, q)
    inicio = 1000 * (time.perf_counter() - t)
    receta = doc.a_dict()
    eventos = []
    resolver = lz.resolver
    llamadas_solver = []
    def resolver_medido(*args, **kwargs):
        llamadas_solver.append(True)
        return resolver(*args, **kwargs)
    lz.resolver = resolver_medido
    bucle, temporizador = QEventLoop(), QTimer()
    temporizador.setTimerType(Qt.PreciseTimer)
    temporizador.setInterval(16)
    paso = [0]
    def mover():
        paso[0] += 1
        k = paso[0]
        pos = q + QPointF(k, k / 3)
        pintados.evento = time.perf_counter()
        raton(v.visor, QEvent.MouseMove, pos)
        eventos.append(1000 * (time.perf_counter() - pintados.evento))
        if k == 90:
            temporizador.stop()
            QTimer.singleShot(40, lz, bucle.quit)
    temporizador.timeout.connect(mover)
    temporizador.start()
    bucle.exec()
    pos = q + QPointF(90, 30)
    assert doc.a_dict() == receta and not llamadas_solver
    pintados.evento = None
    v.visor.frameSwapped.disconnect(presentar)
    lz.resolver = resolver
    tiempos_timeline = []
    recalcular = doc.recalcular
    def recalculo(*args, **kwargs):
        t = time.perf_counter()
        r = recalcular(*args, **kwargs)
        tiempos_timeline.append(1000 * (time.perf_counter() - t))
        return r
    doc.recalcular = recalculo
    t = time.perf_counter()
    if perfilar:
        import cProfile
        import pstats
        perfil = cProfile.Profile()
        perfil.runcall(raton, v.visor, QEvent.MouseButtonRelease, pos)
        pstats.Stats(perfil).strip_dirs().sort_stats("cumtime").print_stats(35)
    else:
        raton(v.visor, QEvent.MouseButtonRelease, pos)
    confirmacion = 1000 * (time.perf_counter() - t)
    doc.recalcular = recalcular
    assert len(pintados.cuadros) >= 45 and len(presentados) >= 45
    intervalos = [(b - a) * 1000 for a, b in zip(presentados, presentados[1:], strict=False)]
    return {"curvas": len(lz.b.curvas), "seleccion_fria_ms": seleccion, "inicio_ms": inicio,
            "evento": resumen(eventos), "retraso_hasta_pintar": resumen(pintados.retrasos),
            "intervalo_presentado": resumen(intervalos), "cuadros_overlay": len(pintados.cuadros),
            "cuadros_presentados": len(presentados),
            "fps_presentados": (len(presentados) - 1) / (presentados[-1] - presentados[0]),
            "soltar_y_confirmar_ms": confirmacion, "timeline_ms": sum(tiempos_timeline),
            "solver_durante_gesto": len(llamadas_solver), "receta_intacta_durante_gesto": True}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--salida", type=Path, required=True)
    p.add_argument("--perfil", action="store_true", help="Perfila una confirmación del SVG complejo")
    args = p.parse_args()
    app, v = A.iniciar(api.Sesion().doc, 1440, 900)
    datos = {}
    try:
        with tempfile.TemporaryDirectory(dir=RAIZ / "evidencias", prefix="medir_vectores_") as carpeta:
            for nombre, contenido, punto in (("sencillo", '<svg width="100mm" height="100mm" viewBox="0 0 100 100"><rect x="2" y="2" width="20" height="10"/></svg>', (4, 96)),
                                            ("complejo", logo(), (4, 96))):
                ruta = Path(carpeta) / f"{nombre}.svg"
                ruta.write_text(contenido, encoding="utf-8")
                filas = []
                for repeticion in range(3):
                    s = api.Sesion()
                    r = api.llamar(s, "insert_svg", {"path": str(ruta), "plane": "XY"})
                    assert r["ok"], r
                    filas.append(medir(v, s.doc, punto, args.perfil and nombre == "complejo" and repeticion == 0))
                datos[nombre] = filas
    finally:
        v.doc.modificado = False
        v.close()
        app.processEvents()
    assert not A.ERRORES, A.ERRORES
    args.salida.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(datos, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

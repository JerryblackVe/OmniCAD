# -*- coding: utf-8 -*-
"""Medición de fluidez de OmniCAD con la ventana REAL (informe: docs/auditorias/fluidez-2026-10-28.md).

NO toca el código del programa: solo envuelve funciones con cronómetros en ESTE proceso y manda eventos de mouse
simulados al visor (nunca mueve el cursor real; no usar el mouse mientras corre, y la ventana tiene que quedar a la
vista: ocluida, Windows no entrega `frameSwapped` y los FPS salen falsos).

Uso, desde `clon/`:
    .venv/Scripts/python.exe ../scripts/turno.py -- .venv/Scripts/python.exe ../scripts/medir_fluidez.py chico|grande|placa200|orbita|hover|todo
Contrafactuales (en memoria, sin cambiar el programa):
    OMNI_INTERVALO=0  → la vista previa se recalcula sin la espera de 220 ms (`PanelComando._t_previa`)
    OMNI_SIN_HIJO=1   → la vista previa nunca va a un proceso aparte (`aislado.EN_HIJO = True`)
Escenarios:
    chico   arrastre de la flecha de Extruir con un rectángulo (el del video), 2 repeticiones de 3 s
    grande  lo mismo con un modelo de 71 pasos (70 cajas; pasa el umbral de proceso aparte), 6 s
    orbita  órbita lenta y rápida, modelo chico y modelo grande (73 pasos, 16,8 k triángulos) + ms por cuadro con glFinish
    hover   costo de elegir_entidad (resaltado bajo el cursor) en ambos modelos
Salida: JSON en evidencias/ui_<hoy>/fluidez_<escenario>.json (fuera de git) y un resumen por pantalla."""
import cProfile
import io
import json
import os
import pstats
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "prueba_ui"))

import arnes as A  # noqa: E402
import numpy as np  # noqa: E402
from omnicad import api  # noqa: E402
from omnicad.timeline.documento import Documento  # noqa: E402
from omnicad.ui import comando as com  # noqa: E402
from omnicad.ui import manipuladores as mp  # noqa: E402
from omnicad.ui import ventana as vent  # noqa: E402
from omnicad.ui import visor3d as vis  # noqa: E402
from PySide6.QtCore import QEvent, QPointF, Qt  # noqa: E402
from PySide6.QtGui import QMouseEvent  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

LOG = {k: [] for k in ("previa", "previsualizar", "prevuelo", "set_modelo", "teselar", "aristas", "paint", "refresco",
                       "arrastrar")}


def envolver(obj, nombre, tag, extra=None):
    orig = getattr(obj, nombre)

    def f(*a, **k):
        t = time.perf_counter()
        pre = extra(*a, **k) if extra else None
        try:
            return orig(*a, **k)
        finally:
            LOG[tag].append((t, time.perf_counter(), pre))
    setattr(obj, nombre, f)


def _valor_previa(panel, *a, **k):
    g = panel.manipuladores
    try:
        return g.valor("distancia") if g else None
    except Exception:  # noqa: BLE001
        return None


envolver(com.PanelComando, "_calcular_previa", "previa", _valor_previa)
envolver(Documento, "previsualizar", "previsualizar")
envolver(Documento, "_prevuelo_cambio", "prevuelo")          # llamadas; la mayoría vuelve en 0,1 ms si no hay hijo
envolver(vis.Visor3D, "set_modelo", "set_modelo")
envolver(vis.Visor3D, "paintGL", "paint")
envolver(vent.VentanaPrincipal, "_refrescar_visibilidad", "refresco")
envolver(mp.GestorManipuladores, "arrastrar", "arrastrar")
for _n, _t in (("teselar_cuerpo", "teselar"), ("aristas_cuerpo", "aristas")):
    envolver(vis, _n, _t)


def pct(xs, q):
    return float(np.percentile(xs, q)) if len(xs) else float("nan")


def resumen(xs):
    if not len(xs):
        return {"n": 0}
    return {"n": len(xs), "p50": round(pct(xs, 50), 2), "p95": round(pct(xs, 95), 2), "p99": round(pct(xs, 99), 2),
            "max": round(max(xs), 2), "media": round(float(np.mean(xs)), 2)}


def L(s, nombre, **a):
    r = api.llamar(s, nombre, a)
    assert r["ok"], (nombre, a, r)
    return r["result"]


def escena(n_cajas=0, n_agujeros=0):
    s = api.Sesion()
    for i in range(n_cajas):
        L(s, "create_box", length=10, width=10, height=10, x=(i % 10) * 15, y=-40 - (i // 10) * 15)
    L(s, "create_sketch", name="Rect", plane="XY")
    L(s, "draw_rectangle", sketch="Rect", x1=0, y1=0, x2=400 if n_agujeros else 100, y2=400 if n_agujeros else 60)
    for i in range(n_agujeros):
        L(s, "draw_circle", sketch="Rect", center_x=10 + i % 25 * 15.5, center_y=10 + i // 25 * 15.5, radius=3)
    return s


def _ev(w, tipo, q, boton, botones):
    QApplication.sendEvent(w, QMouseEvent(tipo, q, w.mapToGlobal(q), boton, botones, Qt.NoModifier))


def arrastre_extruir(v, s, dur, perfil=0):
    """Arrastra la flecha de Extruir `dur` s con cambios de sentido rápidos (movimiento por tiempo, ~125 Hz pedidos)."""
    for k in LOG.values():
        k.clear()
    swaps = []
    gancho = lambda: swaps.append(time.perf_counter())  # noqa: E731
    vi = v.visor
    vi.frameSwapped.connect(gancho)
    p = A.abrir(v, "extruir")
    A.elegir(p, "perfiles", A.hit_perfil(v, s, "Rect", perfil))
    if os.environ.get("OMNI_INTERVALO"):
        p._t_previa.setInterval(int(os.environ["OMNI_INTERVALO"]))
    p.set_valor("distancia", "45 mm")
    p._t_previa.stop()
    p._calcular_previa()
    assert p._previa_ok, p.mensaje.text()
    if perfil == "largest":
        assert np.allclose(np.ptp(vi._mallas[-1]["v"], axis=0)[:2], [400, 400]), "No se eligió la placa completa"
    A.esperar(400)
    g = p.manipuladores
    m = next(x for x in g.manips if isinstance(x, mp.Flecha))
    a, b = m.puntos(g)
    medio = (a + b) / 2
    d = np.asarray(m.direccion, float)
    for k in LOG.values():
        k.clear()
    swaps.clear()
    xy, ok = g.pantalla([medio])
    a0 = QPointF(*xy[0])
    _ev(vi, QEvent.MouseMove, a0, Qt.NoButton, Qt.NoButton)
    _ev(vi, QEvent.MouseButtonPress, a0, Qt.LeftButton, Qt.LeftButton)
    movs = []                      # (t, valor del campo tras el evento)
    t0 = time.perf_counter()
    while (t := time.perf_counter() - t0) < dur:
        sdesp = 20 * np.sin(2 * np.pi * t / 1.0) + 10 * np.sin(2 * np.pi * t / 0.37)
        xy, ok = g.pantalla([medio + d * sdesp])
        _ev(vi, QEvent.MouseMove, QPointF(*xy[0]), Qt.NoButton, Qt.LeftButton)
        movs.append((time.perf_counter(), g.valor("distancia")))
        QTest.qWait(8)
    fin_movimiento = time.perf_counter()
    _ev(vi, QEvent.MouseButtonRelease, QPointF(*xy[0]), Qt.LeftButton, Qt.NoButton)
    A.esperar(300)
    vi.frameSwapped.disconnect(gancho)
    r = analizar(movs, swaps, t0, dur)
    r["previa_arrastre_ms"] = resumen([(b - a) * 1000 for a, b, _ in LOG["previa"] if t0 <= a <= fin_movimiento])
    r["previa_al_soltar_ms"] = resumen([(b - a) * 1000 for a, b, _ in LOG["previa"] if a > fin_movimiento])
    p.cancelar()
    A.esperar(200)
    return r


def analizar(movs, swaps, t0, dur):
    fin = t0 + dur
    r = {"mouse_hz_efectivo": round(len(movs) / dur, 1)}
    previas = [(a, b, val) for a, b, val in LOG["previa"] if a <= fin + 0.5]
    r["previas_por_s"] = round(len(previas) / dur, 2)
    r["previa_ms"] = resumen([(b - a) * 1000 for a, b, _ in previas])
    r["previsualizar_ms"] = resumen([(b - a) * 1000 for a, b, _ in LOG["previsualizar"]])
    r["prevuelo_llamadas"] = len(LOG["prevuelo"])
    r["prevuelo_ms"] = resumen([(b - a) * 1000 for a, b, _ in LOG["prevuelo"]])
    r["set_modelo_ms"] = resumen([(b - a) * 1000 for a, b, _ in LOG["set_modelo"]])
    r["teselar_llamadas"] = len(LOG["teselar"])
    r["teselar_ms"] = resumen([(b - a) * 1000 for a, b, _ in LOG["teselar"]])
    r["aristas_ms"] = resumen([(b - a) * 1000 for a, b, _ in LOG["aristas"]])
    r["manejador_asa_por_evento_ms"] = resumen([(b - a) * 1000 for a, b, _ in LOG["arrastrar"]])
    r["paintGL_ms"] = resumen([(b - a) * 1000 for a, b, _ in LOG["paint"]])
    activos = [x for x in swaps if t0 <= x <= fin]       # solo mientras se arrastra (sin la pausa ociosa de antes/después)
    iv = np.diff(np.array(activos)) * 1000 if len(activos) > 1 else np.array([])
    r["fps_presentados"] = round(len(activos) / dur, 1)
    r["intervalo_cuadros_ms"] = resumen(list(iv))
    r["cuadros_lentos_>33ms"] = int((iv > 33.4).sum())
    r["cuadros_lentos_>100ms"] = int((iv > 100).sum())
    r["cuadros_lentos_>50ms"] = int((iv > 50).sum())
    r["pct_cuadros_<=33.4ms"] = round(float((iv <= 33.4).mean() * 100), 2) if len(iv) else None
    # retraso del sólido respecto de la asa en cada cuadro presentado (ms y mm de valor)
    tiempos_mov = np.array([m[0] for m in movs])
    vals_mov = np.array([m[1] for m in movs])
    ret_ms, ret_mm = [], []
    finales = sorted([(b, val) for a, b, val in previas if val is not None])
    for s in activos:
        hechas = [x for x in finales if x[0] <= s]
        i_asa = np.searchsorted(tiempos_mov, s, side="right") - 1
        if i_asa < 0 or not hechas:
            continue
        mostrado = hechas[-1][1]
        ret_mm.append(abs(vals_mov[i_asa] - mostrado))
        coinc = np.where(np.abs(vals_mov[:i_asa + 1] - mostrado) < 0.06)[0]
        ref = tiempos_mov[coinc[-1]] if len(coinc) else tiempos_mov[0]
        ret_ms.append(max(0.0, (tiempos_mov[i_asa] - ref) * 1000))
    r["retraso_solido_vs_asa_ms"] = resumen(ret_ms)
    r["retraso_solido_vs_asa_mm"] = resumen(ret_mm)
    return r


def orbita(v, dur, amplitud, periodo):
    for k in LOG.values():
        k.clear()
    swaps = []
    gancho = lambda: swaps.append(time.perf_counter())  # noqa: E731
    vi = v.visor
    vi.frameSwapped.connect(gancho)
    vi.set_modo("orbita")
    c = QPointF(vi.width() / 2, vi.height() / 2)
    _ev(vi, QEvent.MouseMove, c, Qt.NoButton, Qt.NoButton)
    _ev(vi, QEvent.MouseButtonPress, c, Qt.LeftButton, Qt.LeftButton)
    t0 = time.perf_counter()
    swaps.clear()
    LOG["paint"].clear()
    n = 0
    while (t := time.perf_counter() - t0) < dur:
        q = QPointF(c.x() + amplitud * np.sin(2 * np.pi * t / periodo), c.y() + 0.3 * amplitud * np.sin(2 * np.pi * t / (periodo * 0.7)))
        _ev(vi, QEvent.MouseMove, q, Qt.NoButton, Qt.LeftButton)
        n += 1
        QTest.qWait(8)
    _ev(vi, QEvent.MouseButtonRelease, q, Qt.LeftButton, Qt.NoButton)
    A.esperar(300)
    vi.frameSwapped.disconnect(gancho)
    vi.set_modo(None)
    activos = [x for x in swaps if x >= t0]
    iv = np.diff(np.array(activos)) * 1000 if len(activos) > 1 else np.array([])
    return {"eventos_por_s": round(n / dur, 1), "px_por_s_pico": round(2 * np.pi * amplitud / periodo),
            "paintGL_ms": resumen([(b - a) * 1000 for a, b, _ in LOG["paint"]]), "fps_presentados": round(len(activos) / dur, 1),
            "intervalo_cuadros_ms": resumen(list(iv)), "cuadros_lentos_>33ms": int((iv > 33.4).sum()),
            "cuadros_lentos_>50ms": int((iv > 50).sum())}


def gpu_orbita(v, cuadros=150):
    """ms por cuadro de dibujo puro (paintGL + glFinish): CPU + GPU, sin sincronía vertical."""
    from OpenGL import GL
    vi = v.visor
    ts = []
    for _ in range(cuadros):
        t = time.perf_counter()
        vi.orbitar(4, 0)
        vi.makeCurrent()
        vi.paintGL()
        GL.glFinish()
        vi.doneCurrent()
        ts.append((time.perf_counter() - t) * 1000)
    return resumen(ts)


def hover(v, n=80):
    vi = v.visor
    rng = np.random.default_rng(1)
    ts = []
    for _ in range(n):
        q = QPointF(float(rng.uniform(0.2, 0.8) * vi.width()), float(rng.uniform(0.2, 0.8) * vi.height()))
        t = time.perf_counter()
        vi.elegir_entidad(q, {"cara", "arista", "cuerpo", "perfil", "vertice"})
        ts.append((time.perf_counter() - t) * 1000)
    return resumen(ts)


def perfil_previa(v, s):
    p = A.abrir(v, "extruir")
    A.elegir(p, "perfiles", A.hit_perfil(v, s, "Rect"))
    p.set_valor("distancia", "20 mm")
    p._t_previa.stop()
    p._calcular_previa()
    p.set_valor("distancia", "21.37 mm")
    p._t_previa.stop()
    pr = cProfile.Profile()
    pr.enable()
    p._calcular_previa()
    pr.disable()
    o = io.StringIO()
    pstats.Stats(pr, stream=o).sort_stats("cumulative").print_stats(12)
    p.cancelar()
    return o.getvalue()


def main():
    que = sys.argv[1] if len(sys.argv) > 1 else "todo"
    out = {}
    if os.environ.get("OMNI_SIN_HIJO"):
        from omnicad.nucleo import aislado
        aislado.EN_HIJO = True
    out["config"] = {"intervalo": os.environ.get("OMNI_INTERVALO", "220 (el del programa)"),
                     "sin_hijo": bool(os.environ.get("OMNI_SIN_HIJO"))}
    if que in ("chico", "todo", "orbita", "hover"):
        s = escena(0)
        app, v = A.iniciar(s.doc)
        out["gl"] = v.visor.info_gl
        if que in ("chico", "todo"):
            out["extruir_chico_rep1"] = arrastre_extruir(v, s, 3.0)
            out["extruir_chico_rep2"] = arrastre_extruir(v, s, 3.0)
            out["perfil_previa_chico"] = perfil_previa(v, s)
        if que in ("orbita", "todo"):
            out["orbita_chico_lenta"] = orbita(v, 3.0, 150, 1.5)
            out["orbita_chico_rapida"] = orbita(v, 3.0, 500, 0.8)
            out["gpu_orbita_chico"] = gpu_orbita(v)
        if que in ("hover", "todo"):
            v.visor.set_filtro({"cara", "arista", "cuerpo", "perfil", "vertice"})
            out["hover_chico_ms"] = hover(v)
        v.doc.modificado = False
        v.close()
    if que in ("grande", "todo"):
        s = escena(70)
        app, v = A.iniciar(s.doc)
        out["grande_pasos"] = len(s.doc.operaciones)
        out["extruir_grande"] = arrastre_extruir(v, s, 6.0)
        v.doc.modificado = False
        v.close()
    if que == "placa200":
        s = escena(n_agujeros=200)
        app, v = A.iniciar(s.doc)
        out["gl"] = v.visor.info_gl
        for i in range(3):
            out[f"extruir_placa200_rep{i+1}"] = arrastre_extruir(v, s, 3.0, "largest")
        v.doc.modificado = False
        v.close()
    if que in ("orbita", "todo", "hover"):
        from omnicad.ui.bench import documento_grande
        doc = documento_grande(8)
        doc.recalcular(0)
        app, v = A.iniciar(doc)
        out["modelo_grande_triangulos"] = sum(len(m["v"]) for m in v.visor._mallas) // 3
        if que in ("orbita", "todo"):
            out["orbita_modelo_grande_lenta"] = orbita(v, 3.0, 150, 1.5)
            out["orbita_modelo_grande_rapida"] = orbita(v, 3.0, 500, 0.8)
            out["gpu_orbita_modelo_grande"] = gpu_orbita(v)
        if que in ("hover", "todo"):
            v.visor.set_filtro({"cara", "arista", "cuerpo", "perfil", "vertice"})
            out["hover_modelo_grande_ms"] = hover(v)
        v.doc.modificado = False
        v.close()
    out["excepciones_en_slots"] = list(A.ERRORES)
    ruta = A.SALIDA / f"fluidez_{que}.json"
    ruta.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: x for k, x in out.items() if k != "perfil_previa_chico"}, ensure_ascii=False, indent=1))
    print(f"\nGuardado en {ruta}")


main()

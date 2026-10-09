# -*- coding: utf-8 -*-
"""
Medición de rendimiento de OmniCAD con la ventana REAL (pendiente 10 de PROJECT_LOG.md: nada se optimiza sin
números de antes y después).

    python -m omnicad.ui.bench [--lado N] [--cuadros N] [--t0 SEGUNDOS_EPOCH]

Abre la ventana como `OmniCAD.py` (preferencias en un .ini temporal), espera el primer cuadro del visor y mide:
  - arranque: desde `--t0` (la hora en que el proceso padre lanzó este) hasta el primer cuadro; sin `--t0`, desde
    que empezó este módulo. `importar_s`: lo que tarda en importar la ventana (PySide6, OpenGL, OCP…).
  - memoria (MB) al arrancar, con el modelo grande cargado, y el pico.
  - recálculo del MODELO GRANDE (placa con N×N agujeros cortados y N esferas unidas, un paso por agujero):
    todo el timeline, solo el último paso (lo que hace editar un paso) y cambiar un parámetro.
  - cuadros por segundo al girar la vista con el modelo grande (órbita de `--cuadros` cuadros, cada uno dibujado
    y terminado en la placa de video con glFinish).
Imprime UNA línea JSON en la salida estándar. Códigos de salida como `captura.py`: 0 ok · 1 falla · 3 sin
pantalla u OpenGL. La herramienta `run_bench` (api/herramientas_dev.py) la llama en un subproceso.
"""
import argparse
import copy
import json
import statistics
import sys
import tempfile
import time
from pathlib import Path

_INICIO = time.time()
OK, FALLA, SIN_PANTALLA = 0, 1, 3


def memoria_mb():
    """(actual, pico) de memoria residente del proceso, en MB. Sin dependencias: API de Windows o /proc en Linux."""
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes

        class _Contadores(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                        ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                        ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]
        k32 = ctypes.WinDLL("kernel32")
        k32.GetCurrentProcess.restype = wintypes.HANDLE
        k32.K32GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(_Contadores), wintypes.DWORD]
        c = _Contadores()
        c.cb = ctypes.sizeof(c)
        k32.K32GetProcessMemoryInfo(k32.GetCurrentProcess(), ctypes.byref(c), c.cb)
        return c.WorkingSetSize / 2 ** 20, c.PeakWorkingSetSize / 2 ** 20
    actual = pico = 0.0
    with open("/proc/self/status", encoding="ascii") as f:
        for linea in f:
            if linea.startswith("VmRSS:"):
                actual = int(linea.split()[1]) / 1024
            elif linea.startswith("VmHWM:"):
                pico = int(linea.split()[1]) / 1024
    return actual, pico


def documento_grande(lado=8):
    """Placa de 20·lado mm con lado×lado agujeros (un paso «cortar» por agujero, diámetro = parámetro «diam») y
    `lado` esferas unidas arriba. Las operaciones se cargan sin calcular: el que llama mide `recalcular(0)`."""
    from ..timeline.documento import Documento
    from ..timeline.operaciones import OpPrimitiva
    doc = Documento()
    doc.nombre = f"Banco {lado}x{lado}"
    doc.parametros.agregar("diam", "8 mm")
    paso = 20.0
    ops = [OpPrimitiva(doc.nuevo_id(), "Placa", forma="caja", ancho=f"{paso * lado} mm", largo=f"{paso * lado} mm",
                       alto="10 mm", x="0", y="0", z="0", operacion="nuevo")]
    for i in range(lado):
        for j in range(lado):
            ops.append(OpPrimitiva(doc.nuevo_id(), f"Agujero {i}-{j}", forma="cilindro", radio="diam / 2",
                                   alto="30 mm", x=f"{paso * (i + 0.5)} mm", y=f"{paso * (j + 0.5)} mm", z="-10 mm",
                                   operacion="cortar"))
    for i in range(lado):
        ops.append(OpPrimitiva(doc.nuevo_id(), f"Esfera {i}", forma="esfera", radio="6 mm",
                               x=f"{paso * (i + 0.5)} mm", y="0", z="10 mm", operacion="unir"))
    doc.operaciones = ops
    doc.marcador = len(ops)
    return doc


def _cronometro(funcion):
    t = time.perf_counter()
    funcion()
    return round(time.perf_counter() - t, 3)


def medir(lado, cuadros, t0, preset=None):
    from PySide6.QtCore import QSettings
    from PySide6.QtGui import QSurfaceFormat
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication

    formato = QSurfaceFormat()          # el mismo formato que OmniCAD.py
    formato.setDepthBufferSize(24)
    formato.setStencilBufferSize(8)
    formato.setSamples(4)
    QSurfaceFormat.setDefaultFormat(formato)
    app = QApplication(sys.argv[:1])
    app.setApplicationName("OmniCAD")
    if app.primaryScreen() is None:
        return SIN_PANTALLA, None

    t_imp = time.perf_counter()
    from .preferencias import Preferencias
    from .ventana import VentanaPrincipal
    importar_s = round(time.perf_counter() - t_imp, 3)

    r = {"importar_s": importar_s}
    with tempfile.TemporaryDirectory(prefix="omnicad_bench_") as tmp:
        prefs = Preferencias(QSettings(str(Path(tmp) / "prefs.ini"), QSettings.IniFormat))
        if preset:                          # Preferencias › Gráficos › Valor predefinido (fija todo junto)
            from .preferencias import PRESETS
            prefs["graficos/preset"] = preset
            for clave, valor in PRESETS.get(preset, {}).items():
                prefs[clave] = valor
        r["preset"] = prefs["graficos/preset"]
        try:
            v = VentanaPrincipal(prefs=prefs)
        except Exception as e:  # noqa: BLE001 — sin contexto OpenGL la app no puede dibujar
            print(f"bench: no se pudo crear la ventana con OpenGL ({e})", file=sys.stderr)
            return SIN_PANTALLA, None
        dibujados = []
        v.visor.frameSwapped.connect(lambda: dibujados.append(time.time()))
        v.resize(1600, 900)
        v.show()
        limite = time.time() + 30
        while not dibujados and time.time() < limite:
            QTest.qWait(5)
        if not dibujados:
            print("bench: el visor no dibujó en 30 s", file=sys.stderr)
            return FALLA, None
        r["arranque_s"] = round(dibujados[0] - (t0 or _INICIO), 3)
        r["memoria_inicio_mb"] = round(memoria_mb()[0], 1)

        doc = documento_grande(lado)
        r["modelo"] = {"pasos": len(doc.operaciones), "agujeros": lado * lado}
        r["recalculo_completo_s"] = _cronometro(lambda: doc.recalcular(0))
        errores = [x.mensaje for x in doc.resultados if x.estado == "error"]
        if errores:
            print(f"bench: el modelo grande tiene errores: {errores[:3]}", file=sys.stderr)
            return FALLA, None
        r["recalculo_ultimo_paso_s"] = _cronometro(lambda: doc.recalcular(len(doc.operaciones) - 1))
        tabla = copy.deepcopy(doc.parametros)        # lo que hace «Cambiar parámetros» al aceptar
        tabla.modificar("diam", "9 mm")
        r["recalculo_parametro_s"] = _cronometro(lambda: doc.aplicar_parametros(tabla))

        r["mostrar_modelo_s"] = _cronometro(lambda: (v.set_documento(doc), QTest.qWait(0)))
        dibujados.clear()
        limite = time.time() + 60
        while not dibujados and time.time() < limite:
            QTest.qWait(5)
        v.visor.encuadrar()
        QTest.qWait(50)
        r["triangulos"] = sum(len(m["v"]) for m in v.visor._mallas) // 3
        r["memoria_modelo_mb"] = round(memoria_mb()[0], 1)

        from OpenGL import GL
        visor = v.visor
        tiempos = []                        # dibujo puro: paintGL + glFinish (lo que cuesta cada cuadro)
        for _ in range(cuadros):
            t = time.perf_counter()
            visor.orbitar(4, 0)
            visor.makeCurrent()
            visor.paintGL()
            GL.glFinish()
            visor.doneCurrent()
            tiempos.append(time.perf_counter() - t)
        ms = sorted(x * 1000 for x in tiempos)
        dibujados.clear()                   # en pantalla: pedir cuadro y esperar que se muestre (con sincronía vertical)
        t = time.perf_counter()
        limite = t + 30
        while len(dibujados) < cuadros and time.perf_counter() < limite:
            antes = len(dibujados)
            visor.orbitar(4, 0)
            while len(dibujados) == antes and time.perf_counter() < limite:
                app.processEvents()
        en_pantalla = len(dibujados) / (time.perf_counter() - t)
        r["giro"] = {"cuadros": cuadros, "fps_dibujo": round(1000 / statistics.mean(ms), 1),
                     "ms_medio": round(statistics.mean(ms), 2), "ms_p95": round(ms[int(len(ms) * 0.95) - 1], 2),
                     "fps_pantalla": round(en_pantalla, 1)}
        r["memoria_pico_mb"] = round(memoria_mb()[1], 1)
        v.doc.modificado = False
        v.close()
    return OK, r


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m omnicad.ui.bench", description="Mide el rendimiento de OmniCAD.")
    ap.add_argument("--lado", type=int, default=8, help="agujeros por lado del modelo grande (defecto 8 → 64)")
    ap.add_argument("--cuadros", type=int, default=120, help="cuadros de la órbita para medir los FPS")
    ap.add_argument("--t0", type=float, default=None, help="hora (time.time) en que se lanzó el proceso")
    ap.add_argument("--preset", choices=("rendimiento", "equilibrado", "calidad", "personalizar"),
                    help="valor predefinido de gráficos (defecto: el de fábrica, personalizar)")
    args = ap.parse_args(argv)
    try:
        codigo, r = medir(max(1, args.lado), max(10, args.cuadros), args.t0, args.preset)
    except Exception as e:  # noqa: BLE001 — la falla sale como mensaje claro
        print(f"bench: {type(e).__name__}: {e}", file=sys.stderr)
        return FALLA
    if r is not None:
        print(json.dumps(r, ensure_ascii=False))
    return codigo


if __name__ == "__main__":
    sys.exit(main())

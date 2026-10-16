# -*- coding: utf-8 -*-
"""
Mide las instancias (PL8 + F17 + RH17): memoria y tiempo con N copias de una pieza, como copias de verdad y como
instancias (la misma geometría con otra ubicación). La pieza es un engranaje de 40 dientes, que trae muchas caras.

Mide: tiempo de construir el patrón, tiempo de recalcular tras cambiar el ancho del engranaje, tiempo de teselar los N
cuerpos (lo que tarda el visor la primera vez), memoria del proceso que cuesta tener el documento con los N cuerpos
teselados y cuántas geometrías distintas hay (formas que no comparten su TShape).

Uso, desde la raíz del repo:  clon/.venv/Scripts/python.exe scripts/medir_instancias.py [N] [salida.md]
"""
import ctypes
import gc
import sys
import time
from ctypes import wintypes
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "clon"))

from omnicad import api  # noqa: E402
from omnicad.nucleo import geometria as geo  # noqa: E402


class _Contadores(ctypes.Structure):
    _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD), ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t), ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t), ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t), ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t)]


def memoria_mb():
    """Memoria privada del proceso en MB (Windows: PagefileUsage = lo que el proceso tiene comprometido)."""
    gc.collect()
    c = _Contadores()
    c.cb = ctypes.sizeof(c)
    if sys.platform != "win32":
        raise OSError("La medición de memoria usa la API de Windows: en otro sistema este script no da ese número.")
    kernel, psapi = ctypes.WinDLL("kernel32"), ctypes.WinDLL("psapi")
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(_Contadores), wintypes.DWORD]
    if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(c), c.cb):
        raise OSError("GetProcessMemoryInfo falló: no se pudo medir la memoria")
    return c.PagefileUsage / 1e6


def _ok(sesion, nombre, **args):
    r = api.llamar(sesion, nombre, args)
    assert r["ok"], r
    return r["result"]


def medir(n, instancias):
    gc.collect()
    base = memoria_mb()
    s = api.Sesion()
    _ok(s, "create_gear", module=2, teeth=40, width=8)
    cuerpo = next(iter(s.doc.estado_final.cuerpos))
    lado = int(n ** 0.5) + 1
    t0 = time.perf_counter()
    args = dict(bodies=[cuerpo], x_count=lado, x_spacing=100, y_count=lado, y_spacing=100)
    if instancias:
        args["lightweight"] = True
    _ok(s, "rectangular_pattern", **args)
    t_patron = time.perf_counter() - t0
    cuerpos = list(s.doc.estado_final.cuerpos.values())[:n]
    t0 = time.perf_counter()
    triangulos = sum(len(geo.teselar(c.forma, 0.05, 0.3)[0]) // 3 for c in cuerpos)
    t_tesela = time.perf_counter() - t0
    t0 = time.perf_counter()
    _ok(s, "edit_feature", feature=s.doc.operaciones[0].id, params={"ancho": "9 mm"})   # la original cambia: siguen las copias
    t_edicion = time.perf_counter() - t0
    t0 = time.perf_counter()
    s.doc.recalcular()                                              # el timeline entero, sin el informe de la API
    t_recalculo = time.perf_counter() - t0
    distintas = geometrias_distintas([c.forma for c in s.doc.estado_final.cuerpos.values()])
    volumen = sum(geo.volumen(c.forma) for c in s.doc.estado_final.cuerpos.values())
    memoria = memoria_mb() - base
    return {"copias": len(s.doc.estado_final.cuerpos), "patron_s": t_patron, "tesela_s": t_tesela,
            "edicion_s": t_edicion, "recalculo_s": t_recalculo, "memoria_mb": memoria, "geometrias_distintas": distintas,
            "triangulos": triangulos, "volumen": volumen}


def geometrias_distintas(formas):
    """Cuántas geometrías hay: las formas que comparten su TShape (copias con otra ubicación) cuentan una sola vez."""
    representantes = []
    for f in formas:
        if not any(f.IsPartner(r) for r in representantes):
            representantes.append(f)
    return len(representantes)


def main(n=50, salida=None):
    filas = []
    for etiqueta, inst in (("copias de verdad", False), ("instancias", True)):
        filas.append((etiqueta, medir(n, inst)))
    texto = [f"Medición de instancias con {n} copias de un engranaje de 40 dientes (clon/.venv, Windows).", "",
             "| Modo | Cuerpos | Patrón por API (s) | Teselado (s) | Editar el ancho por API (s) | Recalcular el timeline (s) "
             "| Memoria (MB) | Geometrías distintas |",
             "|---|---|---|---|---|---|---|---|"]
    for etiqueta, r in filas:
        texto.append(f"| {etiqueta} | {r['copias']} | {r['patron_s']:.2f} | {r['tesela_s']:.2f} | {r['edicion_s']:.2f} | "
                     f"{r['recalculo_s']:.2f} | "
                     f"{r['memoria_mb']:.0f} | {r['geometrias_distintas']} |")
    verdad, inst = filas[0][1], filas[1][1]
    texto += ["", f"Mismo volumen total: {verdad['volumen']:.1f} mm³ contra {inst['volumen']:.1f} mm³."]
    texto = "\n".join(texto)
    print(texto)
    if salida:
        Path(salida).write_text(texto + "\n", encoding="utf-8")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 50, sys.argv[2] if len(sys.argv) > 2 else None)

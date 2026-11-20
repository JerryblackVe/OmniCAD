"""P-201: un solo hilo de OpenBLAS para las cuentas chicas del solver (SVD, QR, rango de matrices de cientos de
columnas). Con la máquina cargada, los hilos de OpenBLAS se esperan entre ellos: el cambio de cota del desfase largo
pasaba de 0,46 a 0,94 s. Se toca el OpenBLAS que traen numpy y scipy (`numpy.libs`, `scipy.libs`, Linux y Windows);
si no se encuentra o falla, no hace nada (el camino normal)."""
import contextlib
import ctypes
import glob
import os
import threading

_candado = threading.Lock()
_estado = {"libs": None, "profundidad": 0, "antes": []}


def _bibliotecas():
    """[(set, get)] de cada OpenBLAS cargado por numpy y scipy (la primera vez los busca)."""
    if _estado["libs"] is None:
        libs = []
        try:
            import numpy
            import scipy
            for paquete in (numpy, scipy):
                carpeta = os.path.join(os.path.dirname(os.path.dirname(paquete.__file__)), paquete.__name__ + ".libs")
                for ruta in glob.glob(os.path.join(carpeta, "*openblas*")):
                    lib = ctypes.CDLL(ruta)
                    for sufijo in ("64_", "_64_", ""):
                        poner = getattr(lib, "scipy_openblas_set_num_threads" + sufijo, None)
                        leer = getattr(lib, "scipy_openblas_get_num_threads" + sufijo, None)
                        if poner is not None and leer is not None:
                            libs.append((poner, leer))
                            break
        except Exception:   # vía rápida: sin OpenBLAS a mano, los hilos quedan como están
            libs = []
        _estado["libs"] = libs
    return _estado["libs"]


@contextlib.contextmanager
def un_hilo():
    """Un hilo de OpenBLAS mientras dura el bloque; al salir, los que había (anidable y entre hilos de Python)."""
    with _candado:
        if _estado["profundidad"] == 0:
            _estado["antes"] = []
            try:
                for poner, leer in _bibliotecas():
                    _estado["antes"].append((poner, leer()))     # se anota antes de tocarla: se devuelve al salir
                    poner(1)
            except Exception:   # vía rápida: si falla, se sigue con los hilos que haya
                pass
        _estado["profundidad"] += 1
    try:
        yield
    finally:
        with _candado:
            _estado["profundidad"] -= 1
            if _estado["profundidad"] == 0:
                for poner, n in _estado["antes"]:
                    try:
                        poner(n)
                    except Exception:   # no se pudo devolver: quedan en uno (más lento, nunca un error)
                        pass

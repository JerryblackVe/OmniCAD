# -*- coding: utf-8 -*-
"""B-562: en Windows, un archivo abierto por otro proceso (el trabajador, el antivirus, el Explorador leyendo la
miniatura) da PermissionError (WinError 32) por un instante. Lo que va y viene por archivos se reintenta antes de
darlo por perdido. Sin Qt."""
import time

PAUSAS = (0.05, 0.1, 0.2)       # 3 reintentos cortos: 0,35 s como mucho


def reintentar(funcion, *args, **kwargs):
    """`funcion(*args, **kwargs)`, repetida tras cada pausa de `PAUSAS` si da PermissionError. Otro OSError (archivo
    que no está, disco lleno) sale enseguida: repetirlo da lo mismo."""
    for pausa in PAUSAS:
        try:
            return funcion(*args, **kwargs)
        except PermissionError:
            time.sleep(pausa)
    return funcion(*args, **kwargs)

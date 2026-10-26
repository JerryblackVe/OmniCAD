"""Medidas del sistema sin dependencias adicionales ni Qt."""
import os
import sys


def ram_total():
    """Bytes físicos totales, o None si el SO no los informa."""
    try:
        if sys.platform == "win32":
            import ctypes

            class Memoria(ctypes.Structure):
                _fields_ = [("largo", ctypes.c_ulong), ("carga", ctypes.c_ulong),
                            *[(k, ctypes.c_ulonglong) for k in ("total", "libre", "pagina", "pagina_libre",
                                                               "virtual", "virtual_libre", "extendida")]]
            m = Memoria()
            m.largo = ctypes.sizeof(m)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m)):
                return m.total
        else:
            return os.sysconf("SC_PHYS_PAGES") * os.sysconf("SC_PAGE_SIZE")
    except (OSError, ValueError, AttributeError):
        pass
    return None

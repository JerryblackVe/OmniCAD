"""Corre un comando pesado (pytest, prueba de humo, bench) esperando su turno: uno a la vez en toda la PC.

Pensado para varios agentes trabajando en paralelo en una PC con poca memoria: cada corrida de pytest reserva
cerca de 1 GB y cuatro a la vez colgaron una PC de 13 GB. Los agentes editan en paralelo y solo el comando
pesado hace fila.

Uso (desde `clon/`):
    .venv/Scripts/python.exe ../scripts/turno.py -- .venv/Scripts/python.exe -m pytest tests/test_x.py -q

Opciones (antes de `--`):
    --plazo SEG     tiempo máximo del comando; al vencer se mata con todos sus hijos (por defecto 900).
    --lugares N     cuántos comandos a la vez (por defecto 1, o la variable OMNICAD_TURNOS).

El candado vive en la carpeta temporal del sistema, así lo comparten todas las copias del repo. Con el turno
tomado, además espera a que queden 1200 MB para reservar (variable OMNICAD_TURNO_MB; RAM + paginación). En
Windows el comando corre con un tope de memoria de 3000 MB entre todos sus procesos (OMNICAD_TURNO_TOPE_MB; 0 = sin
tope): pasado el tope, sus reservas fallan (MemoryError) en vez de llenar la PC.
Sale con el código del comando; 124 si venció el plazo.
"""

import os
import subprocess
import sys
import tempfile
import time

if os.name == "nt":
    import msvcrt

    def _tomar(f):
        try:
            f.seek(0)
            msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
            return True
        except OSError:
            return False

    def _soltar(f):
        f.seek(0)
        msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)

    def _matar(proc):
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True)

    def _lanzar_con_tope(comando, tope_mb):
        """Arranca el comando suspendido dentro de un objeto de trabajo de Windows con tope de memoria (lo hereda
        el python real que lanza el python.exe del venv) y lo suelta. Pasado el tope, las reservas fallan."""
        import ctypes
        from ctypes import wintypes

        class _Basica(ctypes.Structure):
            _fields_ = [("PerProcessUserTimeLimit", ctypes.c_longlong), ("PerJobUserTimeLimit", ctypes.c_longlong),
                        ("LimitFlags", wintypes.DWORD), ("MinimumWorkingSetSize", ctypes.c_size_t),
                        ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", wintypes.DWORD),
                        ("Affinity", ctypes.c_size_t), ("PriorityClass", wintypes.DWORD),
                        ("SchedulingClass", wintypes.DWORD)]

        class _Extendida(ctypes.Structure):
            _fields_ = [("BasicLimitInformation", _Basica), ("IoInfo", ctypes.c_ulonglong * 6),
                        ("ProcessMemoryLimit", ctypes.c_size_t), ("JobMemoryLimit", ctypes.c_size_t),
                        ("PeakProcessMemoryUsed", ctypes.c_size_t), ("PeakJobMemoryUsed", ctypes.c_size_t)]

        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        k32.CreateJobObjectW.restype = wintypes.HANDLE
        trabajo = k32.CreateJobObjectW(None, None)
        info = _Extendida()
        info.BasicLimitInformation.LimitFlags = 0x200 | 0x2000   # JOB_MEMORY | KILL_ON_JOB_CLOSE
        info.JobMemoryLimit = int(tope_mb) * 2**20
        k32.SetInformationJobObject(wintypes.HANDLE(trabajo), 9, ctypes.byref(info), ctypes.sizeof(info))
        proc = subprocess.Popen(comando, creationflags=0x4)      # CREATE_SUSPENDED
        k32.AssignProcessToJobObject(wintypes.HANDLE(trabajo), wintypes.HANDLE(int(proc._handle)))
        ctypes.WinDLL("ntdll").NtResumeProcess(wintypes.HANDLE(int(proc._handle)))
        proc._trabajo_omnicad = trabajo                           # vive lo que vive el proceso
        return proc
else:
    import fcntl
    import signal

    def _tomar(f):
        try:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except OSError:
            return False

    def _soltar(f):
        fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    def _matar(proc):
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except OSError:
            proc.kill()


def _leer_opciones(args):
    plazo, lugares = 900.0, int(os.environ.get("OMNICAD_TURNOS", "1"))
    if "--" not in args:
        sys.exit("uso: turno.py [--plazo SEG] [--lugares N] -- comando ...")
    i = args.index("--")
    previas, comando = args[:i], args[i + 1:]
    while previas:
        clave = previas.pop(0)
        if clave == "--plazo":
            plazo = float(previas.pop(0))
        elif clave == "--lugares":
            lugares = int(previas.pop(0))
        else:
            sys.exit(f"opción desconocida: {clave}")
    if not comando:
        sys.exit("falta el comando después de --")
    if os.path.isfile(comando[0]):              # Windows no encuentra rutas relativas con «/» (.venv/Scripts/…)
        comando[0] = os.path.abspath(comando[0])
    return plazo, max(1, lugares), comando


def _memoria_libre_mb():
    """Memoria que todavía se puede reservar (RAM + archivo de paginación), en MB; None si no se sabe."""
    if os.name == "nt":
        import ctypes

        class _Estado(ctypes.Structure):
            _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
        estado = _Estado()
        estado.dwLength = ctypes.sizeof(_Estado)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(estado)):
            return estado.ullAvailPageFile / 2**20
        return None
    try:
        with open("/proc/meminfo") as f:
            datos = {linea.split(":")[0]: int(linea.split()[1]) for linea in f}
        return (datos["MemAvailable"] + datos.get("SwapFree", 0)) / 1024
    except (OSError, KeyError, ValueError):
        return None


def _esperar_memoria(minimo_mb, plazo_s=900):
    """Espera a que haya `minimo_mb` libres para reservar (lo que tarda otra cosa en soltarla), hasta `plazo_s`."""
    inicio, avisado = time.monotonic(), False
    while time.monotonic() - inicio < plazo_s:
        libre = _memoria_libre_mb()
        if libre is None or libre >= minimo_mb:
            return
        if not avisado:
            print(f"[turno] poca memoria ({libre:.0f} MB libres, pido {minimo_mb}): espero…", file=sys.stderr, flush=True)
            avisado = True
        time.sleep(3)
    print("[turno] sigue faltando memoria: arranco igual", file=sys.stderr)


def _esperar_lugar(lugares):
    carpeta = tempfile.gettempdir()
    archivos = [open(os.path.join(carpeta, f"omnicad_turno_{i}.lock"), "a+") for i in range(lugares)]
    avisado, inicio = False, time.monotonic()
    while True:
        for f in archivos:
            if _tomar(f):
                for otro in archivos:
                    if otro is not f:
                        otro.close()
                if avisado:
                    print(f"[turno] arranca tras {time.monotonic() - inicio:.0f} s de espera", file=sys.stderr)
                return f
        if not avisado:
            print("[turno] hay otro comando pesado corriendo: espero mi turno…", file=sys.stderr, flush=True)
            avisado = True
        time.sleep(1.5)


def main(args):
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    plazo, lugares, comando = _leer_opciones(args)
    candado = _esperar_lugar(lugares)
    _esperar_memoria(int(os.environ.get("OMNICAD_TURNO_MB", "1200")))
    try:
        tope = int(os.environ.get("OMNICAD_TURNO_TOPE_MB", "3000"))
        if os.name == "nt" and tope > 0:
            proc = _lanzar_con_tope(comando, tope)
        else:
            proc = subprocess.Popen(comando, **({} if os.name == "nt" else {"start_new_session": True}))
        try:
            return proc.wait(timeout=plazo)
        except subprocess.TimeoutExpired:
            _matar(proc)
            proc.wait()
            print(f"[turno] el comando pasó el plazo de {plazo:.0f} s y se cortó", file=sys.stderr)
            return 124
    finally:
        _soltar(candado)
        candado.close()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

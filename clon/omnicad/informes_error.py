# -*- coding: utf-8 -*-
"""Informes de error de cada sesión (P-20 de docs/seguimiento/faltantes.md).

Como el «Reportar problema» de otros programas: cada error NO capturado (excepción del hilo principal,
de los hilos de Python o caída dura de C vía ``faulthandler``) queda escrito en UN archivo por sesión
dentro de ``informes/`` de la carpeta de datos, con fecha, versión y traza completa. El archivo de la
sesión anterior nunca se pisa (el nombre lleva fecha y pid) y solo se conservan los últimos
``CONSERVAR`` informes.

El módulo no conoce Qt: el cartel con el botón «Abrir carpeta de errores» lo arma quien instala el
capturador pasando un ``avisar`` (la app con un QMessageBox; la prueba de humo no pasa ninguno).
"""
import faulthandler
import os
import platform
import sys
import threading
import time
import traceback
from pathlib import Path

CONSERVAR = 20          # informes que sobreviven a la poda
MAX_PASOS = 8            # pasos del timeline que se anotan al fallar


def carpeta_informes():
    """Carpeta donde viven los informes: <carpeta de datos>/informes."""
    from . import carpeta_datos
    carpeta = carpeta_datos() / "informes"
    carpeta.mkdir(parents=True, exist_ok=True)
    return carpeta


class _Estado:
    """Lo que instala ``instalar``: el archivo de la sesión y el contexto de la app."""

    def __init__(self):
        self.archivo = None            # Path del informe de esta sesión (None hasta instalar)
        self.manejador = None          # archivo abierto que usa faulthandler
        self.contexto = None           # callable() -> list[str] con el estado de la app
        self.avisar = None             # callable(ruta) que muestra el cartel


_E = _Estado()


def poner_contexto(funcion):
    """Registra quién sabe decir el estado de la app (p. ej. los últimos pasos del timeline):
    ``funcion()`` devuelve una lista de líneas de texto. Puede cambiarse en caliente."""
    _E.contexto = funcion


def abrir_sesion(carpeta=None):
    """Crea el archivo de informe de ESTA sesión (sin pisar el de ninguna anterior) y habilita
    ``faulthandler`` hacia él para que las caídas duras de C (access violation) también queden.
    Devuelve la ruta del informe."""
    if _E.archivo is not None:
        return _E.archivo
    carpeta = Path(carpeta) if carpeta else carpeta_informes()
    carpeta.mkdir(parents=True, exist_ok=True)
    _E.archivo = carpeta / f"sesion-{time.strftime('%Y%m%d-%H%M%S')}-{os.getpid()}.txt"
    try:
        from . import VERSION
        version = VERSION
    except ImportError:               # pruebas sin el paquete completo
        version = "?"
    _E.manejador = open(_E.archivo, "a", encoding="utf-8")
    _E.manejador.write(f"=== OmniCAD {version} — sesión {time.strftime('%Y-%m-%d %H:%M:%S')} "
                       f"(pid {os.getpid()}) ===\nSistema: {platform.platform()}\n"
                       f"Python: {platform.python_version()}\n\n")
    _E.manejador.flush()
    try:
        faulthandler.enable(_E.manejador)
    except Exception:                # noqa: BLE001 — faulthandler ya habilitado hacia otra parte: no es fatal
        pass
    podar(carpeta)
    return _E.archivo


def _lineas_contexto():
    if _E.contexto is None:
        return []
    try:
        lineas = list(_E.contexto())
        return [str(x) for x in lineas][:MAX_PASOS]
    except Exception:                # noqa: BLE001 — el contexto JAMÁS puede romper el informe
        return ["(el contexto de la app falló al pedirlo)"]


def escribir_error(tipo, valor, traza, titulo="Error"):
    """Anota un error al informe de la sesión. Si no hay sesión abierta la abre. Devuelve la ruta del
    informe (para el cartel con «Abrir carpeta de errores»)."""
    ruta = _E.archivo if _E.archivo is not None else abrir_sesion()
    try:
        with open(ruta, "a", encoding="utf-8") as f:
            f.write(f"--- {titulo} {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")
            f.write(f"{tipo.__name__}: {valor}\n")       # primera línea legible (la usa el título del issue)
            f.write("".join(traceback.format_exception(tipo, valor, traza)))
            pasos = _lineas_contexto()
            if pasos:
                f.write("Últimos pasos del timeline:\n  " + "\n  ".join(pasos) + "\n")
            f.write("\n")
        return ruta
    except OSError:
        return ruta                    # disco lleno o carpeta borrada: el informe se pierde, la app no


def _gancho_principal(avisar):
    def gancho(tipo, valor, traza):
        ruta = escribir_error(tipo, valor, traza)
        if avisar is not None:
            try:
                avisar(ruta)
            except Exception:          # noqa: BLE001 — el aviso nunca tapa al error original
                pass
        sys.__excepthook__(tipo, valor, traza)
    return gancho


def instalar(avisar=None, carpeta=None):
    """Arranca la sesión de informes y deja el ganchos puestos: ``sys.excepthook`` (hilo principal),
    ``threading.excepthook`` (hilos de Python) y ``faulthandler`` (caídas de C). ``avisar(ruta)`` se
    llama con la ruta del informe después de cada error del hilo principal (el cartel con el botón
    «Abrir carpeta de errores»); puede ser None para no avisar (prueba de humo, tests)."""
    abrir_sesion(carpeta)
    _E.avisar = avisar
    sys.excepthook = _gancho_principal(avisar)
    anterior = threading.excepthook

    def gancho_hilos(args):
        escribir_error(args.exc_type, args.exc_value, args.exc_traceback, f"Error en el hilo «{args.name}»")
        anterior(args)

    threading.excepthook = gancho_hilos
    return _E.archivo


# ---------------------------------------------------------------- consulta (API/MCP, menú Ayuda)
def listar(carpeta=None):
    """Informes que hay guardados, del más nuevo al más viejo: [{name, date, size}]."""
    carpeta = Path(carpeta) if carpeta else carpeta_informes()
    if not carpeta.is_dir():
        return []
    archivos = [a for a in carpeta.iterdir() if a.is_file() and a.suffix == ".txt"]
    return [{"name": a.name, "date": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(a.stat().st_mtime)),
             "size": a.stat().st_size} for a in sorted(archivos, key=lambda a: a.stat().st_mtime, reverse=True)]


def leer(nombre, carpeta=None):
    """Contenido de un informe por su nombre de archivo. Falla con FileNotFoundError si no existe
    (nunca acepta rutas: solo el nombre dentro de la carpeta de informes)."""
    if Path(nombre).name != nombre:
        raise FileNotFoundError(nombre)
    archivo = (Path(carpeta) if carpeta else carpeta_informes()) / nombre
    return archivo.read_text(encoding="utf-8")


def ultimo(carpeta=None):
    """El informe más reciente (Path) o None si no hay ninguno."""
    informes = listar(carpeta)
    return (Path(carpeta) if carpeta else carpeta_informes()) / informes[0]["name"] if informes else None


def podar(carpeta=None, quedan=CONSERVAR):
    """Borra los informes más viejos dejando los últimos ``quedan``. El de la sesión abierta nunca se
    borra. Devuelve cuántos borró."""
    carpeta = Path(carpeta) if carpeta else carpeta_informes()
    actual = _E.archivo.resolve() if _E.archivo is not None else None
    archivos = [a for a in carpeta.glob("*.txt") if a.is_file() and a.resolve() != actual]
    archivos.sort(key=lambda a: a.stat().st_mtime, reverse=True)
    borrados = 0
    for viejo in archivos[quedan:]:
        try:
            viejo.unlink()
            borrados += 1
        except OSError:
            pass
    return borrados


def ultimo_error(texto):
    """(tipo, mensaje) del último error anotado en un informe: la primera línea con contenido que
    sigue al último encabezado «--- …». Sin errores devuelve ("Error", "sin detalle")."""
    lineas = texto.splitlines()
    for i in range(len(lineas) - 1, -1, -1):
        if lineas[i].startswith("--- "):
            primera = next((x for x in lineas[i + 1:] if x.strip()), "")
            tipo, _, mensaje = primera.partition(": ")
            return (tipo.strip() or "Error", (mensaje or primera).strip())
    return ("Error", "sin detalle")


def url_issue(nombre=None, carpeta=None):
    """URL de «nuevo issue» de GitHub con el informe ya cargado (título y cuerpo sin rutas de la casa ni
    datos personales). ``nombre`` vacío usa el informe más reciente; si tampoco hay, el issue sale con
    la versión y el sistema. Nada se manda solo: quien abre la URL revisa y envía."""
    from urllib.parse import quote

    if nombre:
        cuerpo = resumen_issue(nombre, carpeta)
    else:
        informe = ultimo(carpeta)
        cuerpo = informe.read_text(encoding="utf-8") if informe is not None else ""
    if not cuerpo:
        from . import VERSION
        cuerpo = f"OmniCAD {VERSION} en {platform.platform()}.\n\n(nada más para contar: no hay informe de error)"
    tipo, mensaje = ultimo_error(cuerpo)
    return ("https://github.com/JerryblackVe/OmniCAD/issues/new?title="
            + quote(f"Error: {tipo}: {mensaje}"[:100]) + "&body=" + quote(cuerpo[:4000]))


def resumen_issue(nombre, carpeta=None):
    """Cuerpo listo para pegar en un issue de GitHub a partir de un informe, SIN rutas del usuario ni
    datos personales: versión, sistema, y las líneas del error con las rutas de la casa recortadas a
    ``~``. Nada se manda solo: la app solo arma el texto y la persona lo revisa."""
    try:
        texto = leer(nombre, carpeta)
    except (FileNotFoundError, OSError):
        return "No se encontró el informe de error."
    casa = str(Path.home())
    return texto.replace(casa, "~")

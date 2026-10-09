# -*- coding: utf-8 -*-
"""Herramientas del grupo "dev": que un agente verifique sus cambios al programa sin usar la terminal.

  - `run_checks`: corre la verificación oficial de AGENTS.md (ruff, pytest y, si se pide, la prueba de humo)
    y resume cada paso. Cada paso va en un subproceso con su propio tiempo máximo.
  - `app_screenshot`: abre la ventana REAL de OmniCAD en otro proceso (`omnicad.ui.captura`), la captura
    entera y la cierra. Sirve para ver la interfaz tal como la ve una persona.

Son herramientas de desarrollo: el servidor MCP las muestra solo con `--dev` y la CLI las expone en
`omnicad dev`. Los parseadores (`parsear_*`) son funciones puras: se prueban sin correr nada.
"""
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from ..ui.captura import SIN_PANTALLA
from .errores import ErrorAPI, error
from .registro import Imagen, herramienta

RAIZ = Path(__file__).resolve().parents[2]   # carpeta clon/: pyproject, tests/ y OmniCAD.py
TOPE_LINEAS = 20                              # líneas de falla que se devuelven por paso
TIMEOUT_RUFF = 120                            # segundos máximos por paso
TIMEOUT_PYTEST = 900
TIMEOUT_HUMO = 600
TIMEOUT_CAPTURA = 180
_ARGS_RUFF = ["--select", "F,B023,B905", "."]   # el criterio de AGENTS.md (sin --select hay cientos de avisos viejos)
_FIRMA_PNG = b"\x89PNG\r\n\x1a\n"
# Marca que run_checks pone en sus subprocesos. Si la suite que lanzó vuelve a llamar a run_checks sin simular los
# subprocesos, cada nivel correría toda la suite otra vez: una cadena de pytest anidados llenó la memoria de la PC
# (2026-10-09). Con la marca presente, run_checks se niega (NESTED_CHECKS).
VAR_ANIDADO = "OMNICAD_RUN_CHECKS"


def _correr(argv, timeout):
    """Corre `argv` en la carpeta clon/. Devuelve (código, salida) con stdout y stderr juntos. Código None si
    pasó el tiempo máximo. No lanza: un programa que no arranca vuelve como código -1 con su mensaje."""
    try:
        r = subprocess.run(argv, cwd=RAIZ, capture_output=True, timeout=timeout,
                           env={**os.environ, "PYTHONIOENCODING": "utf-8", VAR_ANIDADO: "1"})
    except subprocess.TimeoutExpired:
        return None, ""
    except OSError as e:
        return -1, str(e)
    return r.returncode, (r.stdout + r.stderr).decode("utf-8", errors="replace")


def _ultima_linea(texto):
    lineas = [linea.strip() for linea in texto.splitlines() if linea.strip()]
    return lineas[-1] if lineas else ""


# ---------------------------------------------------------------- parseo (puro)
def parsear_ruff(texto, codigo):
    """Salida de `ruff check` → {"ok", "summary"}: limpio si el código es 0; el resumen es la última línea."""
    return {"ok": codigo == 0, "summary": _ultima_linea(texto)}


def parsear_pytest(texto, codigo):
    """Salida de `pytest -q` → {"ok", "summary", "failed"}: el resumen («972 passed in 74.11s») y las primeras
    líneas «FAILED …» de la sección «short test summary info»."""
    fallas = [linea.strip() for linea in texto.splitlines() if linea.strip().startswith("FAILED ")]
    return {"ok": codigo == 0, "summary": _ultima_linea(texto), "failed": fallas[:TOPE_LINEAS]}


def parsear_humo(texto, codigo):
    """Salida de `OmniCAD.py --prueba-humo` → {"ok", "summary", "failures"}. El resumen es la línea «Resultado: …».
    Las fallas son las líneas «FALLA …»; si el código no es 0 y no hay ninguna, las líneas que no son «OK» (incluidos
    los registros del log)."""
    lineas = [linea.strip() for linea in texto.splitlines() if linea.strip()]
    resultado = next((x for x in reversed(lineas) if x.startswith("Resultado:")), _ultima_linea(texto))
    fallas = [x for x in lineas if x.startswith("FALLA")]
    if codigo != 0 and not fallas:
        fallas = [x for x in lineas if not x.startswith(("OK", "Resultado:"))]
    return {"ok": codigo == 0, "summary": resultado, "failures": fallas[:TOPE_LINEAS]}


# ---------------------------------------------------------------- pasos de la verificación
def _paso_ruff():
    codigo, salida = _correr([sys.executable, "-m", "ruff", "check", *_ARGS_RUFF], TIMEOUT_RUFF)
    if codigo is None:
        return {"ok": False, "summary": f"timeout: ruff pasó de {TIMEOUT_RUFF} s y se cortó"}
    return parsear_ruff(salida, codigo)


def _paso_pytest(pytest_args):
    codigo, salida = _correr([sys.executable, "-m", "pytest", "-q", *pytest_args.split()], TIMEOUT_PYTEST)
    if codigo is None:
        return {"ok": False, "summary": f"timeout: pytest pasó de {TIMEOUT_PYTEST} s y se cortó", "failed": []}
    return parsear_pytest(salida, codigo)


def _paso_humo():
    codigo, salida = _correr([sys.executable, "OmniCAD.py", "--prueba-humo"], TIMEOUT_HUMO)
    if codigo is None:
        return {"ok": False, "summary": f"timeout: la prueba de humo pasó de {TIMEOUT_HUMO} s y se cortó",
                "failures": []}
    return parsear_humo(salida, codigo)


@herramienta("run_checks", "dev", "Corre la verificación del proyecto (ruff, pytest y, si se pide, la prueba de humo "
             "de la interfaz) y devuelve un resumen por paso. Es lo que hay que correr antes de dar un cambio por bueno.")
def run_checks(sesion, include_smoke: bool = True, pytest_args: str = ""):
    """
    include_smoke: true corre también la prueba de humo (abre la ventana real; tarda 1 a 2 minutos).
    pytest_args: argumentos de pytest separados por espacios, p. ej. "tests/test_parametros.py -k ancho"; vacío = toda la suite.
    """
    if os.environ.get(VAR_ANIDADO):
        raise error("NESTED_CHECKS", "run_checks no se puede llamar desde la verificación que él mismo lanzó.")
    inicio = time.perf_counter()
    ruff = _paso_ruff()
    pyt = _paso_pytest(pytest_args)
    humo = _paso_humo() if include_smoke else None
    pasos = [ruff, pyt] + ([humo] if humo is not None else [])
    return {"ok": all(p["ok"] for p in pasos), "seconds": round(time.perf_counter() - inicio, 1),
            "ruff": ruff, "pytest": pyt, "smoke": humo}


# ---------------------------------------------------------------- captura de la ventana real
def _dimensiones_png(datos):
    if datos[:8] != _FIRMA_PNG or datos[12:16] != b"IHDR":
        raise ErrorAPI("OPERATION_FAILED", "La captura no es un PNG válido.")
    return struct.unpack(">II", datos[16:24])


@herramienta("app_screenshot", "dev", "Abre la ventana REAL de OmniCAD en otro proceso, espera a que dibuje, captura "
             "la ventana entera y la cierra. Es la forma de ver la interfaz tal como la ve una persona.", modifica=False)
def app_screenshot(sesion, path: str | None = None, example: bool = False, project: str | None = None,
                   width: int = 1600, height: int = 900):
    """
    path: ruta del PNG donde guardar la captura además de devolverla; vacío = no se guarda en disco.
    example: true abre el modelo de ejemplo.
    project: ruta de un proyecto .omnicad a abrir; no se combina con example.
    width: ancho de la captura en píxeles (320 a 4000).
    height: alto de la captura en píxeles (240 a 3000).
    """
    if example and project:
        raise error("INVALID_ARGUMENTS", "Usá example o project, no los dos.")
    if not (320 <= width <= 4000 and 240 <= height <= 3000):
        raise error("INVALID_ARGUMENTS", "El tamaño tiene que ser de 320 a 4000 px de ancho y de 240 a 3000 px de alto.")
    if project is not None and not Path(project).is_file():
        raise error("FILE_NOT_FOUND", f"No existe el proyecto: {project}")
    temporal = None
    if path:
        destino = Path(path).resolve()
    else:
        temporal = Path(tempfile.mkdtemp(prefix="omnicad_app_"))
        destino = temporal / "captura.png"
    try:
        destino.parent.mkdir(parents=True, exist_ok=True)
        argv = [sys.executable, "-m", "omnicad.ui.captura", str(destino), "--tamano", f"{width}x{height}"]
        if example:
            argv.append("--ejemplo")
        elif project is not None:
            argv += ["--proyecto", str(Path(project).resolve())]
        codigo, salida = _correr(argv, TIMEOUT_CAPTURA)
        if codigo is None:
            raise ErrorAPI("OPERATION_FAILED", f"La captura pasó de {TIMEOUT_CAPTURA} s y se cortó.",
                           ["Probá con example=true para descartar un problema del proyecto."])
        if codigo == SIN_PANTALLA:
            raise ErrorAPI("OPERATION_FAILED", "No hay pantalla u OpenGL disponible para abrir la ventana.",
                           ["Corré esto en la sesión de escritorio, no en un proceso sin pantalla."])
        if codigo != 0 or not destino.is_file():
            raise ErrorAPI("OPERATION_FAILED",
                           f"No se pudo capturar la ventana: {_ultima_linea(salida) or 'sin detalle'}",
                           ["Corré `python -m omnicad.ui.captura salida.png --ejemplo` para ver el error completo."])
        datos = destino.read_bytes()
        ancho, alto = _dimensiones_png(datos)
        return {"image": Imagen(datos, ancho, alto), "path": str(destino) if path else None}
    finally:
        if temporal is not None:
            shutil.rmtree(temporal, ignore_errors=True)

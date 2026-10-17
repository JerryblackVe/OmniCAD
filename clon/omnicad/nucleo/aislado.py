# -*- coding: utf-8 -*-
"""
Tareas del kernel que pueden no terminar nunca, corridas en un PROCESO APARTE con tope de tiempo.

OpenCascade no se corta desde Python: el análisis de autointersecciones (BOPAlgo_ArgumentAnalyzer) o la
eliminación exacta de líneas ocultas (HLRBRep_Algo) sobre una rosca modelada (caras B-spline helicoidales) pueden
tardar horas, y en la app congelan la ventana (prueba de tortura del 2026-10-17, T-01 y T-02). Acá la forma viaja
como BREP a un hijo que hace la cuenta; si pasa el tope se lo mata y la app sigue viva.

`correr(tarea, forma, tope, **args)` devuelve el resultado (JSON) o lanza `TareaAislada` (`TiempoAgotado` si pasó
el tope). Módulo puro: sin Qt ni timeline. En la app instalada el hijo es la misma `OmniCAD.exe --tarea-aislada`.
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from . import intercambio

_RAIZ = Path(__file__).resolve().parents[2]      # la carpeta que contiene el paquete `omnicad`
_SIN_VENTANA = getattr(subprocess, "CREATE_NO_WINDOW", 0)


class TareaAislada(Exception):
    """El hijo no pudo hacer la tarea (no arrancó, falló o devolvió basura)."""


class TiempoAgotado(TareaAislada):
    """El hijo pasó el tope y se lo mató."""


# ---------------------------------------------------------------- lo que corre el hijo
def _autointersecciones(forma, limite):
    from . import revision
    return revision._autointersecciones(forma, limite)


def _proyeccion_exacta(forma, e, x, deflexion):
    from . import dibujo
    return dibujo._hlr(forma, dibujo.Marco(e, x), "exacto", deflexion)


_TAREAS = {"autointersecciones": _autointersecciones, "proyeccion_exacta": _proyeccion_exacta}


def _a_json(o):
    if hasattr(o, "tolist"):
        return o.tolist()
    raise TypeError(f"{type(o).__name__} no se guarda como JSON")


def principal(argv):
    """Punto de entrada del hijo: `tarea carpeta`. Lee forma.brep y args.json, escribe salida.json."""
    tarea, carpeta = argv[0], Path(argv[1])
    forma = intercambio.leer_brep(carpeta / "forma.brep")
    args = json.loads((carpeta / "args.json").read_text(encoding="utf-8"))
    salida = _TAREAS[tarea](forma, **args)
    (carpeta / "salida.json").write_text(json.dumps(salida, default=_a_json), encoding="utf-8")
    return 0


# ---------------------------------------------------------------- lo que llama la app
def _comando(tarea, carpeta):
    if getattr(sys, "frozen", False):            # app instalada: no hay «python -m»; OmniCAD.py atiende el flag
        # También se llama desde omnicad-cli / omnicad-mcp, que no atienden ese flag.
        app = Path(sys.executable).with_name("OmniCAD.exe" if sys.platform == "win32" else "OmniCAD")
        return [str(app), "--tarea-aislada", tarea, str(carpeta)]
    return [sys.executable, "-m", "omnicad.nucleo.aislado", tarea, str(carpeta)]


def correr(tarea, forma, tope, **args):
    """Hace `tarea` sobre `forma` en un proceso aparte y devuelve su resultado. `tope`: segundos como máximo."""
    if tarea not in _TAREAS:
        raise ValueError(f"Tarea aislada desconocida: {tarea}")
    if tope <= 0:
        raise TiempoAgotado("no quedó tiempo para correrla")
    with tempfile.TemporaryDirectory(prefix="omnicad_tarea_", ignore_cleanup_errors=True) as tmp:   # en Windows el hijo
        # recién muerto puede tardar en soltar el archivo: borrar la carpeta no tiene que tumbar la revisión
        carpeta = Path(tmp)
        try:
            intercambio.escribir_brep(forma, carpeta / "forma.brep")
            (carpeta / "args.json").write_text(json.dumps(args, default=_a_json), encoding="utf-8")
            hijo = subprocess.run(_comando(tarea, carpeta), cwd=_RAIZ, capture_output=True, timeout=tope,
                                  creationflags=_SIN_VENTANA, check=False)
        except subprocess.TimeoutExpired:         # run() ya mató al hijo
            raise TiempoAgotado(f"pasó de {tope:.3g} s y se cortó".replace(".", ",")) from None
        except (OSError, ValueError, intercambio.ErrorGeometria) as e:
            raise TareaAislada(f"no pudo arrancar el proceso aparte ({e})") from e
        salida = carpeta / "salida.json"
        if hijo.returncode != 0 or not salida.is_file():
            ultima = (hijo.stderr or b"").decode("utf-8", "replace").strip().splitlines()[-1:] or ["sin detalle"]
            raise TareaAislada(f"el proceso aparte falló ({ultima[0][:200]})")
        try:
            return json.loads(salida.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            raise TareaAislada(f"el proceso aparte dejó un resultado ilegible ({e})") from e


if __name__ == "__main__":
    sys.exit(principal(sys.argv[1:]))

# -*- coding: utf-8 -*-
"""
Tareas del kernel que pueden no terminar nunca, corridas en un PROCESO APARTE con tope de tiempo.

OpenCascade no se corta desde Python: el análisis de autointersecciones (BOPAlgo_ArgumentAnalyzer) o la
eliminación exacta de líneas ocultas (HLRBRep_Algo) sobre una rosca modelada (caras B-spline helicoidales) pueden
tardar horas, y en la app congelan la ventana (prueba de tortura del 2026-10-17, T-01 y T-02). Acá la forma viaja
como BREP a un hijo que hace la cuenta; si pasa el tope se lo mata y la app sigue viva.

`correr(tarea, forma, tope, **args)` y `correr_json(tarea, datos, tope)` devuelven JSON o lanzan `TareaAislada`
(`TiempoAgotado` si pasó el tope). Sin Qt; solo el hijo de prevuelo importa timeline para reconstruir la receta.
En la app instalada el hijo es la misma `OmniCAD.exe --tarea-aislada`.
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from . import intercambio
from . import motor as _motor

_RAIZ = Path(__file__).resolve().parents[2]      # la carpeta que contiene el paquete `omnicad`
_SIN_VENTANA = getattr(subprocess, "CREATE_NO_WINDOW", 0)
UMBRAL_PREVUELO_PARAMETROS = 60       # pasos no suprimidos anteriores al marcador
TOPE_PREVUELO_PARAMETROS = 900        # segundos, incluida la reconstrucción del documento
TOPE_PREVUELO_ABRIR = 900             # segundos para el ensayo de apertura de un archivo grande (B-48)
EN_HIJO = False


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


def _prevuelo_parametros(receta, parametros, desde):
    from ..timeline.documento import Documento
    from ..timeline.parametros import TablaParametros

    with _motor.fijar_motor("opencascade"):
        doc = Documento.desde_dict(receta)
        doc.parametros = TablaParametros.desde_lista(parametros)
        doc.recalcular(desde)
    return {"errores": sum(r.estado == "error" for r in doc.resultados), "pasos": len(doc.operaciones)}


def _prevuelo_cambio(receta, cambio, desde):
    """Ensaya editar, suprimir o eliminar un paso (B-48): un cambio del historial también recalcula y podía
    tumbar el proceso con una caída nativa del kernel."""
    from ..timeline.documento import Documento
    from ..timeline.operaciones import operacion_desde_dict

    with _motor.fijar_motor("opencascade"):
        doc = Documento.desde_dict(receta)
        i = int(cambio["indice"])
        if cambio["tipo"] == "reemplazar":
            nueva = operacion_desde_dict(cambio["operacion"])
            nueva.id = doc.operaciones[i].id
            doc.operaciones[i] = nueva
        elif cambio["tipo"] == "suprimir":
            doc.operaciones[i].suprimida = bool(cambio["suprimida"])
        elif cambio["tipo"] == "eliminar":
            del doc.operaciones[i]
            if i < doc.marcador:
                doc.marcador -= 1
        else:
            raise ValueError(f"Cambio desconocido: {cambio['tipo']}")
        doc.recalcular(int(desde))
    return {"errores": sum(r.estado == "error" for r in doc.resultados), "pasos": len(doc.operaciones)}


def _prevuelo_abrir(ruta):
    """Ensaya abrir un proyecto grande (B-48): si el kernel cae al reconstruirlo, la app no lo abre y sigue viva."""
    from ..io_archivos import proyecto

    with _motor.fijar_motor("opencascade"):
        doc = proyecto.abrir(ruta)
    return {"errores": sum(r.estado == "error" for r in doc.resultados), "pasos": len(doc.operaciones),
            "cuerpos": len(doc.estado_final.cuerpos)}


_TAREAS_JSON = {"prevuelo_parametros": _prevuelo_parametros, "prevuelo_cambio": _prevuelo_cambio,
                "prevuelo_abrir": _prevuelo_abrir}


def _a_json(o):
    if hasattr(o, "tolist"):
        return o.tolist()
    raise TypeError(f"{type(o).__name__} no se guarda como JSON")


def principal(argv):
    """Punto de entrada del hijo: `tarea carpeta`. Lee args.json y, si corresponde, forma.brep; escribe salida.json."""
    # Con «-m» este módulo es __main__; timeline importa la instancia con su nombre de paquete.
    from . import aislado
    aislado.EN_HIJO = True
    tarea, carpeta = argv[0], Path(argv[1])
    args = json.loads((carpeta / "args.json").read_text(encoding="utf-8"))
    if tarea in _TAREAS_JSON:
        salida = _TAREAS_JSON[tarea](**args)
    else:
        forma = intercambio.leer_brep(carpeta / "forma.brep")
        salida = _TAREAS[tarea](forma, **args)
    (carpeta / "salida.json").write_text(json.dumps(salida, default=_a_json), encoding="utf-8", newline="\n")
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
    return _correr(tarea, tope, args, forma)


def correr_json(tarea, datos, tope):
    """Hace `tarea` en un hijo con argumentos JSON (`datos`), sin BREP. `tope`: segundos como máximo."""
    if tarea not in _TAREAS_JSON:
        raise ValueError(f"Tarea aislada desconocida: {tarea}")
    return _correr(tarea, tope, datos)


def _correr(tarea, tope, args, forma=None):
    if tope <= 0:
        raise TiempoAgotado("no quedó tiempo para correrla")
    if forma is not None and _motor.motor_activo() == "omnikernel":
        # Sin subproceso ni BREP: cada llamada al kernel nativo lleva su CancelToken con plazo (binding omnikernel_py).
        # Las tareas de hoy son de OpenCascade: su despacho informa MOTOR_SIN_SOPORTE en vez de tapar el error.
        return json.loads(json.dumps(_TAREAS[tarea](forma, **args), default=_a_json))
    with tempfile.TemporaryDirectory(prefix="omnicad_tarea_", ignore_cleanup_errors=True) as tmp:   # en Windows el hijo
        # recién muerto puede tardar en soltar el archivo: borrar la carpeta no tiene que tumbar la revisión
        carpeta = Path(tmp)
        try:
            if forma is not None:
                intercambio.escribir_brep(forma, carpeta / "forma.brep")
            (carpeta / "args.json").write_text(json.dumps(args, default=_a_json), encoding="utf-8", newline="\n")
            hijo = subprocess.run(_comando(tarea, carpeta), cwd=_RAIZ, capture_output=True, timeout=tope,
                                  creationflags=_SIN_VENTANA, check=False)
        except subprocess.TimeoutExpired:         # run() ya mató al hijo
            raise TiempoAgotado(f"pasó de {tope:.3g} s y se cortó".replace(".", ",")) from None
        except (OSError, TypeError, ValueError, intercambio.ErrorGeometria) as e:
            raise TareaAislada(f"no pudo arrancar el proceso aparte ({e})") from e
        salida = carpeta / "salida.json"
        if hijo.returncode != 0 or not salida.is_file():
            if hijo.returncode < 0 or hijo.returncode >= 0x80000000:
                # B-48: caída nativa del kernel (p. ej. 0xC0000005 en TKernel). Acá llega como error en español
                # y la app sigue viva; sin el proceso aparte mataba a todo el programa.
                raise TareaAislada(f"el kernel cayó por un error nativo (código {hijo.returncode:#x}) dentro "
                                   "del proceso aparte; OmniCAD sigue andando")
            ultima = (hijo.stderr or b"").decode("utf-8", "replace").strip().splitlines()[-1:] or ["sin detalle"]
            raise TareaAislada(f"el proceso aparte falló ({ultima[0][:200]})")
        try:
            return json.loads(salida.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            raise TareaAislada(f"el proceso aparte dejó un resultado ilegible ({e})") from e


if __name__ == "__main__":
    sys.exit(principal(sys.argv[1:]))

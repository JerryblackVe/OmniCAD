# -*- coding: utf-8 -*-
"""Estado de cada función pública de `nucleo/` con OmniKernel: conectada, común o sin soporte.

    clon/.venv/Scripts/python.exe scripts/estado_motor.py      reescribe la sección «Estado por función» de
                                                                docs/inventario_motor.md
- conectada: `nucleo/omnikernel/<modulo>.py` trae su implementación (con paridad en tests/test_paridad_motor.py);
- común: no nombra nada de OCP, corre igual en los dos motores (validaciones, búsquedas, política de la app);
- sin soporte: usa OpenCascade y OmniKernel no la tiene todavía: da MOTOR_SIN_SOPORTE.
"""
from importlib import import_module
from pathlib import Path
import sys

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "clon"))
TITULO = "## Estado por función (paso 9)"


def estado():
    from omnicad.nucleo import motor
    filas = {"conectada": [], "común": [], "sin soporte": []}
    for archivo in sorted((RAIZ / "clon/omnicad/nucleo").glob("*.py")):
        modulo = import_module(f"omnicad.nucleo.{archivo.stem}")
        iniciar = getattr(modulo, "_iniciar_opencascade", None)
        if iniciar is None:
            continue
        nombres_occ = set(iniciar.__code__.co_names)
        alternativa = RAIZ / "clon/omnicad/nucleo/omnikernel" / archivo.name
        alt = import_module(f"omnicad.nucleo.omnikernel.{archivo.stem}") if alternativa.exists() else None
        for nombre, f in sorted(vars(modulo).items()):
            original = getattr(f, "__wrapped__", None)
            if original is None or getattr(f, "__module__", "") != modulo.__name__ or nombre.startswith("_"):
                continue
            if alt is not None and hasattr(alt, nombre):
                clase = "conectada"
            elif not motor._usa_opencascade(original.__code__, nombres_occ):
                clase = "común"
            else:
                clase = "sin soporte"
            filas[clase].append(f"{archivo.stem}.{nombre}")
    return filas


def main():
    filas = estado()
    texto = [TITULO, "",
             "Generado por `scripts/estado_motor.py`. Funciones públicas de `nucleo/` (sin las de guion bajo): "
             f"**{len(filas['conectada'])} conectadas** a OmniKernel, **{len(filas['común'])} comunes** a los dos "
             f"motores y **{len(filas['sin soporte'])} sin soporte** (dan MOTOR_SIN_SOPORTE; familias y casos "
             "mínimos en `rust-kernel/docs/faltantes_omnicad.md`).", ""]
    for clase, nombres in filas.items():
        texto += [f"### {clase.capitalize()} ({len(nombres)})", "", ", ".join(f"`{n}`" for n in nombres), ""]
    ruta = RAIZ / "docs/inventario_motor.md"
    actual = ruta.read_text(encoding="utf-8")
    actual = actual.split(TITULO)[0].rstrip() + "\n\n"
    ruta.write_text(actual + "\n".join(texto), encoding="utf-8")
    print({k: len(v) for k, v in filas.items()})


if __name__ == "__main__":
    main()

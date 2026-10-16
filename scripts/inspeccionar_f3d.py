# -*- coding: utf-8 -*-
"""
Mide cómo abre OmniCAD cada ejemplo de Fusion (P11.a): cuerpos y volumen guardados tal cual contra los de cada
componente en su lugar (con sus copias). Usa la herramienta `inspect_f3d` de la API.

Uso, desde la raíz del repo:  clon/.venv/Scripts/python.exe scripts/inspeccionar_f3d.py <carpeta con .f3d/.f3z> [salida.md]
"""
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "clon"))

from omnicad import api  # noqa: E402


def main(carpeta, salida=None):
    filas = ["| Archivo | Cuerpos antes | Cuerpos después | Volumen antes (mm³) | Volumen después (mm³) | "
             "Componentes movidos | Con copias | Sin ubicar | Segundos |", "|---|---|---|---|---|---|---|---|---|"]
    sesion = api.Sesion()
    for ruta in sorted(Path(carpeta).glob("*.f3[dz]")):
        t0 = time.perf_counter()
        r = api.llamar(sesion, "inspect_f3d", {"path": str(ruta)})
        if not r["ok"]:
            filas.append(f"| {ruta.name} | error: {r.get('mensaje') or r.get('error_kind')} |")
            continue
        d = r["result"]
        filas.append(f"| {ruta.name} | {d['bodies_stored']} | {d['bodies_placed']} | {d['volume_stored_mm3']:.1f} | "
                     f"{d['volume_placed_mm3']:.1f} | {d['components_moved']} | {d['components_with_copies']} | "
                     f"{d['unplaced_bodies']} | {time.perf_counter() - t0:.0f} |")
        print(filas[-1], flush=True)
    texto = "\n".join(filas)
    if salida:
        Path(salida).write_text(texto + "\n", encoding="utf-8")
    return texto


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)

# -*- coding: utf-8 -*-
"""
Soporte en L con dos agujeros y empalmes, armado con la API de Python de OmniCAD (`omnicad.api`).

La pieza (mm):
  - base de 80 x 40 x 8 y pared de 80 x 8 x 40, en L;
  - dos agujeros pasantes de diámetro 8 en la base (el espesor y el diámetro son parámetros);
  - empalme de radio 6 en el rincón interior y de radio 5 en las dos esquinas del frente de la base.

Uso (con el Python del venv, desde cualquier carpeta):

    clon/.venv/Scripts/python.exe ejemplos/agentes/soporte_l.py CARPETA_DE_SALIDA

Guarda `soporte_l.omnicad`, `soporte_l.stl` y `soporte_l.png` en esa carpeta e imprime un JSON con el volumen
y la caja envolvente. Sale con 0 si todo anduvo y con 1 si alguna herramienta devolvió un error.
Las mismas herramientas, una por línea, están en `soporte_l.jsonl` (para `omnicad batch`).
"""
import json
import sys
from pathlib import Path

from omnicad import api

PASOS = [
    ("create_parameter", {"name": "espesor", "expression": "8 mm"}),
    ("create_parameter", {"name": "diametro", "expression": "8 mm"}),
    # la base: un rectángulo en el plano XY, extruido hacia arriba
    ("sketch_from_spec", {"name": "Base", "plane": "XY",
                          "entities": [{"type": "rectangle", "corner1": [0, 0], "corner2": [80, 40]}]}),
    ("extrude", {"sketch": "Base", "distance": "espesor"}),
    # la pared: un rectángulo en el plano XZ, extruido hacia +Y y unido a la base
    ("sketch_from_spec", {"name": "Pared", "plane": "XZ",
                          "entities": [{"type": "rectangle", "corner1": [0, 0], "corner2": [80, 40]}]}),
    ("extrude", {"sketch": "Pared", "distance": "espesor", "operation": "join", "reverse": True}),
    # dos agujeros: dos círculos con cota de diámetro = parámetro, cortados a través de la base
    ("sketch_from_spec", {"name": "Agujeros", "plane": "XY",
                          "entities": [{"type": "circle", "id": "a", "center": [15, 25], "radius": 4},
                                       {"type": "circle", "id": "b", "center": [65, 25], "radius": 4}],
                          "dimensions": [{"type": "diameter", "entities": ["a"], "value": "diametro"},
                                         {"type": "diameter", "entities": ["b"], "value": "diametro"}]}),
    ("extrude", {"sketch": "Agujeros", "profile": "all", "distance": "espesor", "operation": "cut"}),
    # empalmes con selectores: la arista interior más cercana al punto, y las verticales del frente (y máxima)
    ("fillet", {"edges": "nearest:[40,8,8]", "radius": 6}),
    ("fillet", {"edges": "|Z and >Y", "radius": 5}),
]


def llamar(sesion, nombre, **args):
    """Llama una herramienta y devuelve su `result`. Si falla, lanza RuntimeError con el mensaje y las pistas."""
    r = api.llamar(sesion, nombre, args)
    if not r["ok"]:
        raise RuntimeError(f"{nombre} falló [{r['error_kind']}]: {r['mensaje']} {' '.join(r.get('pistas', []))}")
    return r["result"]


def construir(sesion):
    """Arma el soporte en la sesión (cada herramienta que modifica es un paso de deshacer)."""
    for nombre, args in PASOS:
        llamar(sesion, nombre, **args)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print("uso: soporte_l.py CARPETA_DE_SALIDA", file=sys.stderr)
        return 2
    carpeta = Path(argv[0])
    carpeta.mkdir(parents=True, exist_ok=True)
    sesion = api.Sesion()
    try:
        construir(sesion)
        cuerpo = llamar(sesion, "get_physical_properties")["bodies"][0]
        guardado = llamar(sesion, "save_document", path=str(carpeta / "soporte_l.omnicad"), overwrite=True)
        stl = llamar(sesion, "export", path=str(carpeta / "soporte_l.stl"), overwrite=True)
        imagen = llamar(sesion, "get_viewport_image", direction=[1, 1.5, 1], width=640, height=480)["image"]
    except RuntimeError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    png = carpeta / "soporte_l.png"
    png.write_bytes(imagen.png)               # `Imagen` trae los bytes del PNG en `.png`
    print(json.dumps({"volumen_mm3": round(cuerpo["volume"], 3), "caja_mm": cuerpo["bounding_box"]["size"],
                      "archivos": [guardado["path"], stl["path"], str(png.resolve())]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

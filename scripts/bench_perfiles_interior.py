# -*- coding: utf-8 -*-
"""Antes/después del punto interior: SVG y texto con cientos de regiones, con y sin malla.

Desde clon/: .venv/Scripts/python.exe ../scripts/turno.py -- .venv/Scripts/python.exe ../scripts/bench_perfiles_interior.py
Compara solo esta corrección, sobre las mismas caras y cachés calientes. No abre la ventana ni archivos del usuario.
"""
from contextlib import contextmanager
from datetime import date
import json
from pathlib import Path
import statistics
import sys
import tempfile
import time

import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "clon"))

from OCP.BRepClass import BRepClass_FaceClassifier  # noqa: E402
from OCP.TopAbs import TopAbs_IN  # noqa: E402
from OCP.gp import gp_Pnt  # noqa: E402
from omnicad.io_archivos.boceto_archivos import boceto_desde_primitivas  # noqa: E402
from omnicad.io_archivos.svg import leer_svg  # noqa: E402
from omnicad.nucleo import geometria as geo, perfiles as pf  # noqa: E402
from omnicad.restricciones import Boceto  # noqa: E402


def anterior(cara):
    """Implementación previa de perfiles._punto_adentro, conservada solo como control del banco."""
    tris = np.asarray(geo.teselar(cara)[0], float).reshape(-1, 3, 3)
    areas = np.linalg.norm(np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0]), axis=1)
    return tris[int(np.argmax(areas))].mean(axis=0)


@contextmanager
def cambiar(modulo, nombre, valor):
    original = getattr(modulo, nombre)
    setattr(modulo, nombre, valor)
    try:
        yield
    finally:
        setattr(modulo, nombre, original)


def medir(b, perfiles):
    nuevo = pf._punto_adentro
    receta = b.a_dict()
    with cambiar(pf, "_punto_adentro", anterior):
        esperado = pf.sin_huecos(perfiles, b)
    pf.sin_huecos(perfiles, b)  # calentamiento de ambos caminos antes del cronómetro
    tiempos = {"antes_ms": [], "despues_ms": [], "sin_malla_ms": []}
    for vuelta in range(3):
        orden = (("antes_ms", anterior), ("despues_ms", nuevo))
        for clave, funcion in orden if vuelta % 2 == 0 else reversed(orden):
            with cambiar(pf, "_punto_adentro", funcion):
                inicio = time.perf_counter()
                utiles = pf.sin_huecos(perfiles, b)
                tiempos[clave].append(1000 * (time.perf_counter() - inicio))
            assert utiles == esperado
    vacia = np.empty((0, 3), np.float32)
    with cambiar(geo, "teselar", lambda *a, **k: (vacia, vacia)):
        try:
            with cambiar(pf, "_punto_adentro", anterior):
                pf.sin_huecos(perfiles, b)
        except ValueError as e:
            fallo_anterior = str(e)
        else:
            raise AssertionError("El control anterior no reprodujo la malla vacía")
        for _ in range(3):
            inicio = time.perf_counter()
            utiles = pf.sin_huecos(perfiles, b)
            tiempos["sin_malla_ms"].append(1000 * (time.perf_counter() - inicio))
            assert utiles == esperado
        # Árbitro separado del filtro de perfiles: cada punto pertenece al material, no a la contraforma.
        for perfil in perfiles:
            q = geo.punto_dentro(perfil.cara)
            assert BRepClass_FaceClassifier(perfil.cara, gp_Pnt(*map(float, q)), 1e-7).State() == TopAbs_IN
    assert b.a_dict() == receta and all(geo.es_valida(p.cara) for p in perfiles)
    medianas = {clave: statistics.median(valores) for clave, valores in tiempos.items()}
    return {"perfiles": len(perfiles), "regiones_utiles": len(esperado),
            "area_mm2": sum(p.area for p in esperado), "receta_intacta": True,
            "diferencias_clasificacion": 0, "puntos_verificados": len(perfiles),
            "fallo_anterior_sin_malla": fallo_anterior, "corridas": tiempos, "medianas": medianas,
            "variacion_normal_pct": 100 * (medianas["despues_ms"] / medianas["antes_ms"] - 1)}


def main():
    salida = RAIZ / "evidencias"
    if not salida.is_dir():
        raise RuntimeError("Falta la carpeta de evidencias del repositorio.")
    texto = Boceto()
    texto.agregar_texto((0, 0), "ABOPR8 " * 72, altura=10)
    formas = []
    for k in range(500):
        x, y = (k % 25) * 8 + 1, (k // 25) * 8 + 1
        formas.append(f'<path fill-rule="evenodd" d="M{x} {y}h6v6h-6z M{x+2} {y+2}h2v2h-2z"/>')
    with tempfile.TemporaryDirectory(prefix="perfiles_interior_", dir=salida) as carpeta:
        ruta = Path(carpeta) / "anillos.svg"
        ruta.write_text('<svg width="200mm" height="160mm" viewBox="0 0 200 160">'
                        + ''.join(formas) + '</svg>', encoding="utf-8")
        dibujo = boceto_desde_primitivas(leer_svg(ruta))
        resultados = {}
        for nombre, b in (("texto", texto), ("svg", dibujo)):
            perfiles = pf.detectar_boceto(b, geo.Plano("XY", 177))
            assert len(perfiles) >= 500
            resultados[nombre] = medir(b, perfiles)
    resultados["entorno"] = {"python": sys.version.split()[0], "repeticiones": 3,
                             "tipo": "clasificacion completa, mismas caras, caches calientes"}
    destino = salida / f"perfiles_interior_{date.today().isoformat()}.json"
    contenido = json.dumps(resultados, ensure_ascii=False, indent=2)
    destino.write_text(contenido, encoding="utf-8")
    print(contenido)
    print(f"Evidencia: {destino}")


if __name__ == "__main__":
    main()

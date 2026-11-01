"""Banco antes/después del módulo Rust: Zstandard del .f3d y BVH de rayos (RS-R1, RS-R3).

Se corre con turno (una corrida pesada a la vez), desde clon/, y "antes" es la misma orden con OMNICAD_SIN_RUST=1:

    .venv/Scripts/python.exe ../scripts/turno.py -- .venv/Scripts/python.exe ../scripts/bench_nativo.py f3d RUTA.f3d
    .venv/Scripts/python.exe ../scripts/turno.py -- .venv/Scripts/python.exe ../scripts/bench_nativo.py rayos [triángulos...]

`f3d`: abrir el .f3d entero (`leer_componentes`) y descomprimir sus miembros Zstandard por separado.
`rayos`: `primer_choque` con 2000 rayos hacia adentro (como `espesores`), construir el BVH y un rayo de hover
(`primer_rayo_triangulos`) contra una esfera de N triángulos (por defecto 50 000 y 251 000).
"""
import io
import math
import os
import sys
import time
import zipfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "clon"))


def _cronometro(etiqueta, f):
    t = time.perf_counter()
    r = f()
    print(f"{etiqueta:58s} {(time.perf_counter() - t) * 1000:10.1f} ms", flush=True)
    return r


def f3d(ruta):
    from omnicad.io_archivos import f3d_nativo
    datos = Path(ruta).read_bytes()
    with zipfile.ZipFile(io.BytesIO(datos)) as z:
        miembros = [i for i in z.infolist() if f3d_nativo.CARPETA_BREPS in i.filename and i.filename.lower().endswith(".smbh")]
        salida = _cronometro(f"Zstandard de {len(miembros)} miembros", lambda: [f3d_nativo.miembro(datos, i) for i in miembros])
    print(f"   {sum(len(s) for s in salida) / 1e6:.1f} MB descomprimidos")
    _cronometro(f"leer_componentes de {Path(ruta).name}", lambda: f3d_nativo.leer_componentes(ruta))


def _esfera(n_triangulos):
    k = max(4, round(math.sqrt(n_triangulos / 2)))
    u = np.linspace(0, 2 * math.pi, k + 1)
    v = np.linspace(0.02, math.pi - 0.02, k + 1)
    p = np.stack([np.outer(np.sin(v), np.cos(u)), np.outer(np.sin(v), np.sin(u)),
                  np.outer(np.cos(v), np.ones_like(u))], axis=-1) * 10.0
    a, b, c, d = p[:-1, :-1], p[:-1, 1:], p[1:, 1:], p[1:, :-1]
    return np.concatenate([np.stack([a, b, c], 2).reshape(-1, 3, 3), np.stack([a, c, d], 2).reshape(-1, 3, 3)])


def rayos(tamanos):
    from omnicad import nativo
    from omnicad.nucleo import revision
    from omnicad.ui.visor3d import primer_rayo_triangulos
    print("módulo Rust:", "sí" if hasattr(nativo.disponible(), "Bvh") else "no (numpy)")
    azar = np.random.default_rng(5)
    for n in tamanos:
        tris = _esfera(n)
        print(f"-- {len(tris)} triángulos")
        u = azar.normal(size=(2000, 3))
        u /= np.linalg.norm(u, axis=1, keepdims=True)
        o, d = u * 10.0 * (1 - 1e-6), -u + azar.normal(size=(2000, 3)) * 0.05
        d /= np.linalg.norm(d, axis=1, keepdims=True)
        t, i = _cronometro("primer_choque, 2000 rayos (construye el BVH)", lambda: revision.primer_choque(o, d, tris, 1e-6))
        print(f"   {np.isfinite(t).sum()} rayos chocan; suma de distancias {t[np.isfinite(t)].sum():.6f}")
        cache = {}
        _cronometro("hover: 1.er rayo (construye el BVH)", lambda: primer_rayo_triangulos(o[0], d[0], tris, cache, "k"))
        _cronometro("hover: 100 rayos más", lambda: [primer_rayo_triangulos(o[j], d[j], tris, cache, "k") for j in range(1, 101)])


if __name__ == "__main__":
    modo = sys.argv[1] if len(sys.argv) > 1 else ""
    if modo == "f3d" and len(sys.argv) > 2:
        f3d(sys.argv[2])
    elif modo == "rayos":
        rayos([int(x) for x in sys.argv[2:]] or [50_000, 251_000])
    else:
        sys.exit(__doc__)
    print("SIN_RUST =", os.environ.get("OMNICAD_SIN_RUST", ""))

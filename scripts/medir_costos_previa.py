# -*- coding: utf-8 -*-
"""Costos de la vista previa de Extruir SIN ventana (informe: docs/auditorias/fluidez-2026-10-28.md). Solo lectura.

Uso, desde `clon/` (con turno: abre OpenCascade y arma mallas grandes):
    .venv/Scripts/python.exe ../scripts/turno.py -- .venv/Scripts/python.exe ../scripts/medir_costos_previa.py escala|reparto|hijo
  escala   extrusión de una placa con N agujeros: núcleo (herramienta `extrude`), teselado del visor y aristas
  reparto  teselado de la placa de 200 agujeros partido en: mallador de OpenCascade (C++), normales por nodo y copia a numpy
  hijo     de qué se compone el proceso aparte de la vista previa con >= 60 pasos (receta, arranque del hijo, recálculo)"""
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "clon"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from omnicad import api  # noqa: E402
from omnicad.nucleo import analisis  # noqa: E402
from omnicad.nucleo import geometria as geo  # noqa: E402
from omnicad.ui import visor3d as vis  # noqa: E402


def L(s, n, **a):
    r = api.llamar(s, n, a)
    assert r["ok"], (n, a, r)
    return r["result"]


def placa(n_agujeros):
    s = api.Sesion()
    L(s, "create_sketch", name="R", plane="XY")
    L(s, "draw_rectangle", sketch="R", x1=0, y1=0, x2=400, y2=400)
    for i in range(n_agujeros):
        L(s, "draw_circle", sketch="R", center_x=10 + (i % 25) * 15.5, center_y=10 + (i // 25) * 15.5, radius=3)
    return s


def cuerpo_unico(s):
    return next(iter(s.doc.estado_final.cuerpos.values())).forma


def mejor(f, rep=3):
    ts = []
    for _ in range(rep):
        t = time.perf_counter()
        x = f()
        ts.append((time.perf_counter() - t) * 1000)
    return round(min(ts), 1), x


def escala():
    print("N_agujeros  extrude_ms  teselar_ms  aristas_ms  triangulos")
    for n in (0, 50, 200, 500):
        s = placa(n)
        t = time.perf_counter()
        L(s, "extrude", sketch="R", profile="largest", distance=20)
        t_ext = (time.perf_counter() - t) * 1000
        forma = cuerpo_unico(s)
        defl = vis.deflexion_automatica(forma)
        t_tes, (v, _n) = mejor(lambda forma=forma, defl=defl: vis.teselar_cuerpo(forma, defl, 0.3, True))
        t_ari, _ = mejor(lambda forma=forma: vis.aristas_cuerpo(forma))
        print(f"{n:10d} {t_ext:11.1f} {t_tes:11.1f} {t_ari:11.1f} {len(v) // 3:11d}")


def reparto():
    s = placa(200)
    L(s, "extrude", sketch="R", profile="largest", distance=20)
    forma = cuerpo_unico(s)
    defl = vis.deflexion_automatica(forma)
    vis.teselar_cuerpo(forma, defl, 0.3, True)               # inicializa los globals del motor
    acum = {"malla": 0.0, "props": 0.0}
    orig_malla, orig_props = geo.BRepMesh_IncrementalMesh, analisis._props_nodos

    def malla(*a, **k):
        t = time.perf_counter()
        try:
            return orig_malla(*a, **k)
        finally:
            acum["malla"] += time.perf_counter() - t

    def props(*a, **k):
        t = time.perf_counter()
        try:
            return orig_props(*a, **k)
        finally:
            acum["props"] += time.perf_counter() - t

    geo.BRepMesh_IncrementalMesh, analisis._props_nodos = malla, props
    for _ in range(3):
        acum["malla"] = acum["props"] = 0.0
        t = time.perf_counter()
        vis.teselar_cuerpo(forma, defl, 0.3, True)
        total = time.perf_counter() - t
        print(f"total {total * 1000:6.0f} ms | mallador OpenCascade {acum['malla'] * 1000:5.0f} | normales por nodo "
              f"{acum['props'] * 1000:5.0f} | copia a numpy y resto {(total - acum['malla'] - acum['props']) * 1000:5.0f}")


def hijo():
    s = api.Sesion()
    for i in range(70):
        L(s, "create_box", length=10, width=10, height=10, x=(i % 10) * 15, y=-40 - (i // 10) * 15)
    L(s, "create_sketch", name="Rect", plane="XY")
    L(s, "draw_rectangle", sketch="Rect", x1=0, y1=0, x2=100, y2=60)
    doc = s.doc
    t = time.perf_counter()
    receta = doc.a_dict()
    texto = json.dumps({"receta": receta}, sort_keys=True)
    hashlib.sha256(texto.encode("utf-8")).digest()
    print(f"{len(doc.operaciones)} pasos; receta + json + sha256 por cada previa: {(time.perf_counter() - t) * 1000:.1f} ms "
          f"({len(texto) / 1024:.0f} KB)")
    cmd = [sys.executable, "-c", "import omnicad.timeline.documento, omnicad.nucleo.aislado"]
    ts = []
    for _ in range(3):
        t = time.perf_counter()
        subprocess.run(cmd, cwd=str(RAIZ / "clon"), check=True, creationflags=0x08000000 if sys.platform == "win32" else 0)
        ts.append((time.perf_counter() - t) * 1000)
    print(f"arranque del hijo + imports (mínimo de 3): {min(ts):.0f} ms")
    t = time.perf_counter()
    doc.recalcular(0)
    print(f"recalcular los {len(doc.operaciones)} pasos en este proceso: {(time.perf_counter() - t) * 1000:.0f} ms")


{"escala": escala, "reparto": reparto, "hijo": hijo}[sys.argv[1] if len(sys.argv) > 1 else "escala"]()

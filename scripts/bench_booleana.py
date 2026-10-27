# -*- coding: utf-8 -*-
"""Banco de la booleana de la extrusión: «Cuerpo nuevo» contra «Unir / Cortar / Intersecar» al EDITAR el paso.

Cada caso corre en un proceso aparte (con tope de tiempo), arma un cuerpo base (placa con N rasgos, importada como
BREP para que sea un paso base), dibuja un rectángulo sobre su cara de arriba, extruye como «Cuerpo nuevo» y después
edita la operación a cada una de las otras, midiendo por etapa: `booleano`, `_booleana`, `_problema_booleana`
(chequeos de B-39), `unificar_caras`, `_quitar_cables_colgados`, `volumen`, `se_tocan` y `es_estanca`.

Uso (desde `clon/`, con turno):
    .venv/Scripts/python.exe ../scripts/turno.py -- .venv/Scripts/python.exe ../scripts/bench_booleana.py todo
    .venv/Scripts/python.exe ../scripts/bench_booleana.py caso placa500 [--perfil]
Escribe `evidencias/booleanas_<fecha>/tabla.md` (mediana de 3 corridas) con `todo`.
"""
import argparse
import cProfile
import json
import math
import os
import pstats
import statistics
import subprocess
import sys
import time
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "clon"))
CARPETA = RAIZ / "evidencias" / f"booleanas_{date.today().isoformat()}"
BINCHA = Path(r"C:\Users\mosos\Desktop\f3z\BINCHA.f3d")

# nombre → (rasgos, tipo de rasgo, lado de la extrusión respecto de la placa)
CASOS = {
    "caja": (0, "ninguno", "centro"),
    "placa50": (50, "agujeros", "centro"), "placa500": (500, "agujeros", "centro"),
    "placa3000": (3000, "agujeros", "centro"),
    "hoyuelos500": (500, "esferas", "centro"),
    "bspline50": (50, "bspline", "centro"), "bspline500": (500, "bspline", "centro"),
    "coplanar50": (50, "agujeros", "borde"), "coplanar500": (500, "agujeros", "borde"),
    "bincha": (0, "f3d", "centro"),
}
ESPANOL = {"join": "unir", "cut": "cortar", "intersect": "intersecar"}
ETAPAS = (("booleano", "geo", "booleano"), ("_booleana", "geo", "_booleana"),
          ("_problema", "geo", "_problema_booleana"), ("unificar_caras", "geo", "_unificar_caras"),
          ("_quitar_cables", "geo", "_quitar_cables_colgados"), ("volumen", "geo", "volumen"), ("vol_exacto", "geo", "volumen_exacto"),
          ("_caja_occ", "geo", "_caja_occ"), ("_adentro", "geo", "_adentro"),
          ("se_tocan", "geo", "se_tocan"), ("es_estanca", "rv", "es_estanca"),
          ("_vol_entrada", "geo", "_volumenes_entrada"), ("aristas_def", "geo", "_aristas_defectuosas"),
          ("es_valida", "geo", "es_valida"))


def _forma_base(n, rasgo):
    """Placa 400×200×20 con `n` rasgos en la mitad x < 0 (la mitad x > 0 queda libre para la extrusión)."""
    from OCP.BRepBuilderAPI import BRepBuilderAPI_NurbsConvert

    from omnicad.nucleo import geometria as geo
    placa = geo.caja(400, 200, 20, (-200, -100, 0))
    if n == 0:
        return placa
    columnas = max(1, int(math.sqrt(n * 185 / 190)))
    filas = math.ceil(n / columnas)
    paso_x, paso_y = 185.0 / columnas, 190.0 / filas
    cortes = []
    for k in range(n):
        x = -195 + paso_x * (k % columnas + 0.5)
        y = -95 + paso_y * (k // columnas + 0.5)
        r = min(paso_x, paso_y) * 0.3
        c = geo.esfera(r, (x, y, 20)) if rasgo == "esferas" else geo.cilindro(r, 30, (x, y, -5))
        cortes.append(BRepBuilderAPI_NurbsConvert(c, True).Shape() if rasgo == "bspline" else c)   # caras B-spline
    forma = geo.booleano(placa, geo.unir_todos(cortes), "cortar")
    return forma


def _brep(nombre):
    from OCP.BRepTools import BRepTools
    n, rasgo, _ = CASOS[nombre]
    CARPETA.mkdir(parents=True, exist_ok=True)
    ruta = CARPETA / f"base_{nombre}.brep"
    if not ruta.exists():
        BRepTools.Write_s(_forma_base(n, rasgo), str(ruta))
    return ruta


def _instrumentar():
    """Envuelve cada etapa con un cronómetro; devuelve el dict {nombre: [segundos, llamadas]}."""
    from omnicad.nucleo import geometria as geo
    from omnicad.nucleo import revision as rv
    mods = {"geo": geo, "rv": rv}
    tiempos = {}
    for nombre, mod, attr in ETAPAS:
        original = getattr(mods[mod], attr)
        tiempos[nombre] = [0.0, 0]

        def envuelta(*a, _o=original, _t=tiempos[nombre], **k):
            t = time.perf_counter()
            try:
                return _o(*a, **k)
            finally:
                _t[0] += time.perf_counter() - t
                _t[1] += 1
        setattr(mods[mod], attr, envuelta)
    return tiempos


def correr_caso(nombre, perfil=False):
    from omnicad import api
    tiempos = _instrumentar()
    n, rasgo, lado = CASOS[nombre]
    s = api.Sesion()

    def llamar(herr, **a):
        r = api.llamar(s, herr, a)
        assert r["ok"], (herr, r)
        return r["result"]
    t0 = time.perf_counter()
    if rasgo == "f3d":
        llamar("open_document", path=str(BINCHA))
        cara = "XY"           # la cara de arriba del único sólido (z = 0)
        x1, x2, y1, y2 = -40.0, -36.0, -60.0, -56.0
    else:
        if nombre == "caja":
            llamar("create_box", length=400, width=200, height=20, name="Base")
        else:
            llamar("open_document", path=str(_brep(nombre)))
        cara, (x1, x2), (y1, y2) = ">Z", ((180, 200) if lado == "borde" else (100, 120)), (-10, 10)
    armado = time.perf_counter() - t0
    boceto = llamar("create_sketch", plane=cara)["sketch"]
    llamar("draw_rectangle", x1=x1, y1=y1, x2=x2, y2=y2)
    t = time.perf_counter()
    r = llamar("extrude", sketch=boceto["id"], profile=0, distance=5, operation="new_body")
    resultado = {"caso": nombre, "armado": armado, "nuevo": time.perf_counter() - t}
    paso = r["feature"]["id"]
    for op in ("join", "cut", "intersect"):
        for v in tiempos.values():
            v[0], v[1] = 0.0, 0
        t = time.perf_counter()
        pr = cProfile.Profile() if perfil and op == "join" else None
        if pr:
            pr.enable()
        r = api.llamar(s, "edit_feature", {"feature": paso, "params": {"operacion": ESPANOL[op], "invertir": op != "join"}})
        if pr:
            pr.disable()
            pstats.Stats(pr).sort_stats("cumulative").print_stats(25)
        resultado[op] = time.perf_counter() - t
        resultado[op + "_ok"] = r.get("ok")
        resultado[op + "_etapas"] = {k: [round(v[0], 3), v[1]] for k, v in tiempos.items() if v[1]}
        resultado[op + "_avisos"] = (r.get("warnings") or r.get("avisos") or [])[:2]
        if not r.get("ok"):
            resultado[op + "_error"] = str(r)[:200]
        if r.get("ok"):
            vol = sum(c.get("volume") or 0 for c in llamar("get_scene_info").get("bodies", []))
            resultado[op + "_vol"] = round(vol, 3)
    return resultado


def todo(repeticiones, plazo, casos):
    CARPETA.mkdir(parents=True, exist_ok=True)
    filas = []
    for nombre in casos:
        corridas = []
        for _ in range(repeticiones):
            try:
                p = subprocess.run([sys.executable, str(Path(__file__)), "caso", nombre], capture_output=True,
                                   text=True, timeout=plazo, cwd=str(RAIZ / "clon"),
                                   env={**os.environ, "PYTHONIOENCODING": "utf-8"})
                linea = [ln for ln in p.stdout.splitlines() if ln.startswith("{")]
                corridas.append(json.loads(linea[-1]) if linea else {"caso": nombre, "error": p.stderr[-300:]})
            except subprocess.TimeoutExpired:
                corridas.append({"caso": nombre, "error": f"más de {plazo} s"})
        filas.append(corridas)
        (CARPETA / f"corridas_{nombre}.json").write_text(json.dumps(corridas, indent=1), encoding="utf-8")
        print(nombre, [round(c.get(k, -1), 2) for c in corridas[:1] for k in ("nuevo", "join", "cut", "intersect")],
              flush=True)
    lineas = ["| caso | nuevo | unir | cortar | intersecar | unir / nuevo |", "|---|---|---|---|---|---|"]
    for corridas in filas:
        buenas = [c for c in corridas if "error" not in c]
        if not buenas:
            lineas.append(f"| {corridas[0]['caso']} | ERROR {corridas[0].get('error', '')[:60]} | | | | |")
            continue
        med = {k: statistics.median(c[k] for c in buenas) for k in ("nuevo", "join", "cut", "intersect")}
        lineas.append(f"| {buenas[0]['caso']} | {med['nuevo']:.2f} | {med['join']:.2f} | {med['cut']:.2f} | "
                      f"{med['intersect']:.2f} | {med['join'] / max(med['nuevo'], 1e-3):.1f}× |")
    texto = "\n".join(lineas)
    (CARPETA / "tabla.md").write_text(texto + "\n", encoding="utf-8")
    print(texto)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("modo", choices=("caso", "todo"))
    ap.add_argument("nombre", nargs="?")
    ap.add_argument("--perfil", action="store_true")
    ap.add_argument("--repeticiones", type=int, default=3)
    ap.add_argument("--plazo", type=int, default=600)
    a = ap.parse_args()
    if a.modo == "caso":
        print(json.dumps(correr_caso(a.nombre, a.perfil), default=str))
    else:
        todo(a.repeticiones, a.plazo, [a.nombre] if a.nombre else list(CASOS))

# -*- coding: utf-8 -*-
"""B-517: el desfase hacia adentro de los perfiles de un texto («@tienda», −0,5) cerraba el programa (segfault de
OpenCascade). Corre en un proceso aparte: si vuelve el segfault, falla el test y no pytest."""
import subprocess
import sys
from pathlib import Path

_SCRIPT = r'''
from omnicad import api
S = api.Sesion()
L = lambda n, a=None: api.llamar(S, n, a or {})
L("create_box", {"length": 100, "width": 100, "height": 3})
L("create_sketch", {"plane": ">Z", "name": "texto"})
L("add_text", {"text": "@tienda", "x": -30, "y": -42, "height": 8, "sketch": "texto"})
r = L("offset_profiles", {"profiles": "all", "distance": -0.5, "keep_original": False, "sketch": "texto"})
assert not r["ok"] and "desaparece" in r["mensaje"], r          # el trazo mide menos de 1 mm: se lo come
objetos = [o["id"] for o in L("get_vector_objects", {"sketch": "texto"})["result"]["objects"]]
r = L("offset_vector_objects", {"objects": objetos, "distance": -0.5, "sketch": "texto"})
assert not r["ok"] and "desaparece" in r["mensaje"], r
r = L("offset_profiles", {"profiles": "all", "distance": -0.2, "sketch": "texto"})
assert r["ok"], r                                                # lo que entra, anda
L("create_sketch", {"plane": "XY", "name": "s"})
L("draw_spline", {"points": [[0, 0], [20, -5], [30, 10], [15, 25], [-5, 15]], "closed": True, "sketch": "s"})
L("draw_ellipse", {"center_x": 60, "center_y": 0, "major_radius": 20, "minor_radius": 10, "sketch": "s"})
r = L("offset_profiles", {"profiles": "all", "distance": -2, "sketch": "s"})
assert r["ok"] and r["result"]["entities_added"] < 20, r         # una spline o una elipse sola queda exacta
print("OK")
'''


def test_desfase_hacia_adentro_de_un_texto_no_cierra_el_programa():
    clon = Path(__file__).resolve().parents[1]
    r = subprocess.run([sys.executable, "-c", _SCRIPT], cwd=clon, capture_output=True, text=True, timeout=300)
    assert r.returncode == 0 and r.stdout.strip().endswith("OK"), (r.returncode, r.stdout[-500:], r.stderr[-2000:])

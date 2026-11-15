# -*- coding: utf-8 -*-
"""B-493: Engrosar o desfasar una superficie de revolución que termina en punta sobre el eje cerraba el programa
(access violation de OpenCascade). Corre en un proceso aparte: si vuelve el segfault, falla el test y no pytest."""
import subprocess
import sys
from pathlib import Path

_SCRIPT = r'''
import math
from omnicad import api
from omnicad.nucleo import geometria as geo, solidos_crear as sc, superficies as su
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge
from OCP.BRepPrimAPI import BRepPrimAPI_MakeRevol
from OCP.GC import GC_MakeArcOfCircle
from OCP.gp import gp_Ax1, gp_Dir, gp_Pnt

S = api.Sesion()
L = lambda n, a=None: api.llamar(S, n, a or {})
L("create_sketch", {"plane": "XY", "name": "b"})
L("draw_arc", {"start_x": 0, "start_y": 0, "mid_x": 18, "mid_y": 10, "end_x": 0, "end_y": 25, "sketch": "b"})
eje = L("draw_line", {"start_x": 0, "start_y": -5, "end_x": 0, "end_y": 30, "sketch": "b",
                      "construction": True})["result"]["entities"][0]["id"]
arco = [e["id"] for e in L("get_sketch", {"sketch": "b"})["result"]["entities"] if e["type"] == "arc"][0]
assert L("create_surface_revolve", {"profiles": [{"sketch": "b", "curve": arco}], "axis": {"sketch": "b", "curve": eje},
                                    "angle": 360})["ok"]
r = L("thicken", {"faces": [L("find_faces")["result"]["faces"][0]["id"]], "thickness": 2})
assert not r["ok"] and "termina en punta" in r["mensaje"], r

def cupula(*pts):
    arco = GC_MakeArcOfCircle(*[gp_Pnt(x, y, 0) for x, y in pts]).Value()
    return BRepPrimAPI_MakeRevol(BRepBuilderAPI_MakeEdge(arco).Edge(), gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(0, 1, 0)),
                                 2 * math.pi).Shape()

abierta = cupula((0, 25), (12, 22), (18, 8))          # un solo polo, en punta
for llamada in (lambda: su.engrosar_superficie(abierta, -2), lambda: su.desfasar_superficie(abierta, 2),
                lambda: sc._engrosar_lamina(abierta, 2), lambda: sc.engrosar(abierta, 2, direccion="simetrica")):
    try:
        llamada()
        raise AssertionError("tenía que fallar")
    except geo.ErrorGeometria as e:
        assert "termina en punta" in str(e), e
lisa = cupula((0, 25), (25 / 2 ** .5, 25 / 2 ** .5), (25, 0))   # media esfera: polo liso, sigue andando
r = su.engrosar_superficie(lisa, -2)
assert geo.es_valida(r) and abs(geo.volumen(r) - 2 / 3 * math.pi * (27 ** 3 - 25 ** 3)) < 1, geo.volumen(r)
from OCP.GC import GC_MakeArcOfEllipse
from OCP.gp import gp_Ax2, gp_Elips
elipse = gp_Elips(gp_Ax2(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1), gp_Dir(0, 1, 0)), 1000, 40)
largo = BRepPrimAPI_MakeRevol(BRepBuilderAPI_MakeEdge(GC_MakeArcOfEllipse(elipse, 0.0, math.pi / 2, True).Value()).Edge(),
                              gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(0, 1, 0)), 2 * math.pi).Shape()
assert geo.es_valida(su.engrosar_superficie(largo, 0.5))   # polo liso de radio 1,6 mm en un perfil de 1 m: no es punta
print("OK")
'''


_DESFASE = r'''
from omnicad import api
S = api.Sesion()
L = lambda n, a=None: api.llamar(S, n, a or {})
L("create_sketch", {"plane": "XY", "name": "b"})
L("draw_arc", {"start_x": 0, "start_y": 0, "mid_x": 18, "mid_y": 10, "end_x": 0, "end_y": 25, "sketch": "b"})
eje = L("draw_line", {"start_x": 0, "start_y": -5, "end_x": 0, "end_y": 30, "sketch": "b",
                      "construction": True})["result"]["entities"][0]["id"]
arco = [e["id"] for e in L("get_sketch", {"sketch": "b"})["result"]["entities"] if e["type"] == "arc"][0]
assert L("create_surface_revolve", {"profiles": [{"sketch": "b", "curve": arco}], "axis": {"sketch": "b", "curve": eje},
                                    "angle": 300})["ok"]
r = L("offset_surface", {"faces": [L("find_faces")["result"]["faces"][0]["id"]], "distance": -2})
assert not r["ok"] and "termina en punta" in r["mensaje"], r
print("OK")
'''


def _correr(script):
    clon = Path(__file__).resolve().parents[1]
    r = subprocess.run([sys.executable, "-c", script], cwd=clon, capture_output=True, text=True, timeout=300)
    assert r.returncode == 0 and r.stdout.strip().endswith("OK"), (r.returncode, r.stdout[-500:], r.stderr[-2000:])


def test_engrosar_cupula_en_punta_da_error_claro_sin_cerrar_el_programa():
    _correr(_SCRIPT)


def test_desfasar_revolucion_de_300_en_punta_da_error_claro_sin_cerrar_el_programa():
    _correr(_DESFASE)

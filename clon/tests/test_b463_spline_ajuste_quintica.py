"""B-463: la spline de ajuste nueva es la quíntica natural centrípeta (grado 5), la más cercana a la de Fusion; las
guardadas con grado 3 siguen siendo la cúbica vieja. Muestras: 5 splines medidas en Fusion (E11, 19/11)."""
import json
from pathlib import Path

import numpy as np
import pytest

from omnicad.restricciones.boceto import Boceto
from omnicad.restricciones.boceto_geometria import evaluar_primitiva, mas_cercano

CASOS = json.loads((Path(__file__).parent / "datos" / "b463_splines_fusion.json").read_text())


def _curva(b, sid, n=4001):
    prim = b.primitivas(sid)[0]
    return prim, np.array([evaluar_primitiva(prim, t)[0] for t in np.linspace(0, 1, n)])


def _desvio(C, muestras):
    return max(np.min(np.hypot(*(C - m).T)) for m in np.array(muestras))


def _pasa_por(prim, puntos):
    return max(np.hypot(*(np.array(mas_cercano(prim, q)[2]) - q)) for q in puntos) < 1e-6


@pytest.mark.parametrize("caso", sorted(CASOS))
def test_parecida_a_fusion(caso):
    c = CASOS[caso]
    b = Boceto()
    sid = b.agregar_spline([tuple(p) for p in c["puntos"]], "ajuste", 3, c["cerrada"])
    prim, C = _curva(b, sid)
    assert prim[4] == 5
    assert _desvio(C, c["muestras"]) <= (0.05 if c["cerrada"] else 0.5)
    assert _pasa_por(prim, c["puntos"])


def test_spline_modificada_sigue_quintica():
    b = Boceto()
    sid = b.agregar_spline([(0, 0), (30, 0), (31, 2), (60, 30), (61, 0)], "ajuste")
    pid = b.curvas[sid].pts[2]
    b.puntos[pid].x, b.puntos[pid].y = 35.0, 8.0                     # arrastrar un punto
    nuevo = b.insertar_punto_spline(sid, evaluar_primitiva(b.primitivas(sid)[0], 0.8)[0])
    _prim, antes = _curva(b, sid)
    b.activar_manija(sid, nuevo)                                     # la manija por defecto no cambia la forma
    b.activar_manija(sid, b.curvas[sid].pts[0])
    prim, C = _curva(b, sid)
    assert prim[4] == 5 and np.max(np.hypot(*(C - antes).T)) < 1e-6
    assert _pasa_por(prim, [b.coords(p) for p in b.curvas[sid].pts])
    copia = Boceto.desde_dict(json.loads(json.dumps(b.a_dict())))   # guardar y abrir: misma curva
    assert np.max(np.hypot(*(_curva(copia, sid)[1] - C).T)) < 1e-9


def test_archivo_viejo_sigue_cubica():
    viejo = {"siguiente_id": 7, "puntos": [{"id": i + 1, "x": x, "y": y} for i, (x, y) in
                                           enumerate([(0, 0), (30, 0), (31, 2), (60, 30), (61, 0)])],
             "curvas": [{"tipo": "spline", "id": 6, "modo": "ajuste", "grado": 3, "cerrada": False, "pesos": None,
                         "nudos": None, "construccion": False, "puntos": [1, 2, 3, 4, 5]}]}
    b = Boceto.desde_dict(viejo)
    prim = b.primitivas(6)[0]
    assert prim[4] == 3 and b.a_dict()["curvas"][0]["grado"] == 3
    assert np.allclose(evaluar_primitiva(prim, 0.5)[0], (41.9727602573098, 20.111313949348446))   # la de antes de B-463

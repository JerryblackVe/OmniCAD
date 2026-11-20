"""B-463: la spline de ajuste es la quíntica de Fusion (energía mínima, método de BauhausCM10.dll); las guardadas con
grado 3 siguen siendo la cúbica vieja. Datos: splines medidas en Fusion (E11, 19/11); `_hp`: 17 cifras, con nudos y polos."""
import json
import math
from pathlib import Path

import numpy as np
import pytest

from omnicad.restricciones.boceto import Boceto
from omnicad.restricciones.boceto_geometria import (
    _base_derivada, _tramo, evaluar_primitiva, interpolar_spline, mas_cercano, parametros_cuerda)

CASOS = json.loads((Path(__file__).parent / "datos" / "b463_splines_fusion.json").read_text())
CASOS_HP = json.loads((Path(__file__).parent / "datos" / "b463_splines_fusion_hp.json").read_text())


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
    assert _desvio(C, c["muestras"]) <= 0.05   # al punto de muestra más cercano; lo exacto: test_igual_a_fusion
    assert _pasa_por(prim, c["puntos"])


@pytest.mark.parametrize("caso", sorted(CASOS_HP))
def test_igual_a_fusion(caso):
    """Mismo parámetro por punto, mismos nudos y mismos polos que Fusion (a 1e-4 mm; da ~3e-8). La cerrada (caso 6)
    Fusion la da «periódica» con 25 nudos: son los nuestros sin el primero ni los 5 últimos (mismos polos)."""
    c = CASOS_HP[caso]
    polos, nudos, grado = interpolar_spline(c["puntos"], 5, c["cerrada"])
    assert grado == 5 and np.allclose(nudos[1:-5] if c["cerrada"] else nudos, c["nudos"], atol=1e-12)
    vuelta = c["puntos"] + c["puntos"][:1] if c["cerrada"] else c["puntos"]
    assert np.allclose(parametros_cuerda(vuelta, 5)[:len(c["puntos"])], c["parametros"], atol=1e-12)
    assert np.max(np.abs(np.array(polos) - c["polos"])) < 1e-4


def test_cerrada_c4_en_la_costura():
    polos, nudos, p = interpolar_spline([(0, 0), (20, 0), (20, 20), (0, 20)], 5, True)
    prim = ("spline", None, polos, nudos, p, None)
    assert np.allclose(evaluar_primitiva(prim, 0)[0], (0, 0)) and np.allclose(evaluar_primitiva(prim, 1)[0], (0, 0))
    for orden in range(1, 5):
        assert np.allclose(_base_derivada_curva(polos, nudos, p, 0.0, orden), _base_derivada_curva(polos, nudos, p, 1.0, orden))


def _base_derivada_curva(polos, nudos, p, t, orden):
    n = len(polos) - 1
    k = _tramo(nudos, p, n, t)
    return np.array(_base_derivada(nudos, p, t, k, orden)) @ np.array(polos[k - p:k + 1])


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


def test_muchos_puntos_pasa_exacto():
    """Con 41 puntos la energía (h^-5) tapaba las restricciones y la punta quedaba a 1,7e-4 mm (perfil sin cerrar)."""
    puntos = [(x, 2 * math.sin(x * math.pi / 5)) for x in range(41)]
    polos, nudos, p = interpolar_spline(puntos, 5)
    prim = ("spline", None, polos, nudos, p, None)
    assert np.allclose(polos[-1], puntos[-1], atol=1e-9) and _pasa_por(prim, puntos)


MANIJAS = json.loads((Path(__file__).parent / "datos" / "b463_manijas_fusion.json").read_text())


@pytest.mark.parametrize("caso", sorted(MANIJAS))
def test_manija_igual_a_fusion(caso):
    """B-463: la manija movida en Fusion (E11, casos 7–15: punto 0 e interior, 6 direcciones, ×2 y 5 puntos) da la
    misma C' en el punto (≤0,5 %; da ≤0,3 %) y los mismos polos."""
    c = MANIJAS[caso]
    b = Boceto()
    sid = b.agregar_spline([tuple(p) for p in c["puntos"]], "ajuste")
    hx, hy = c["manija"]
    b.activar_manija(sid, b.curvas[sid].pts[c["punto"]], math.degrees(math.atan2(hy, hx)), math.hypot(hx, hy))
    polos, nudos, p = b.primitivas(sid)[0][2:5]
    t = parametros_cuerda([tuple(q) for q in c["puntos"]], 5)[c["punto"]]
    d1 = _base_derivada_curva(polos, nudos, p, t, 1)
    assert np.linalg.norm(d1 - c["c_prima"]) <= 0.005 * np.linalg.norm(c["c_prima"])
    assert np.max(np.abs(np.array(polos) - c["polos"])) < 0.1

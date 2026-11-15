# -*- coding: utf-8 -*-
"""FL-13: los perfiles de un boceto grande se detectan por islas (grupos de curvas que no se tocan), con caché por
isla, y salen idénticos al camino de siempre; también con una isla adentro del contorno de otra."""
from omnicad.nucleo import geometria as geo
from omnicad.nucleo import perfiles as pf


def _rect(x, y, w, h, n):
    p = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
    return [("linea", f"{n}{i}", p[i], p[(i + 1) % 4]) for i in range(4)]


def _firma(ps):
    return sorted((round(p.area, 4), round(p.centroide_uv[0], 3), round(p.centroide_uv[1], 3), tuple(sorted(p.firma)))
                  for p in ps)


def _sin_islas(g, monkeypatch):
    monkeypatch.setattr(pf, "_MIN_ISLAS", 10 ** 9)
    pf._CACHE_PERFILES.clear()
    r = _firma(pf.detectar(g, geo.Plano("XY")))
    monkeypatch.undo()
    pf._CACHE_PERFILES.clear()
    return r


def test_fl13_islas_iguales_al_camino_normal_y_solo_rehace_la_isla_tocada(monkeypatch):
    g = [c for k in range(20) for c in _rect(15 * k, 0, 10, 10, f"r{k}_")]
    g += _rect(-40, -40, 400, 100, "marco") + [("circulo", "adentro", (100.0, 30.0), 5.0)]   # isla dentro de un contorno
    assert len(pf._islas(g, 1e-4)) == 1                   # el marco envuelve todo: una sola isla
    g = g[:-5] + [("circulo", "suelto", (500.0, 500.0), 5.0)]
    assert len(pf._islas(g, 1e-4)) == 21
    esperado = _sin_islas(g, monkeypatch)
    assert _firma(pf.detectar(g, geo.Plano("XY"))) == esperado and len(esperado) == 21
    partidas, detectar = [], pf._detectar
    monkeypatch.setattr(pf, "_detectar", lambda geom, *a: partidas.append(len(geom)) or detectar(geom, *a))
    g2 = g[:4] + [("linea", "puente", (10.0, 5.0), (15.0, 5.0))] + g[4:]      # boceto ya modificado: une r0 con r1
    assert _firma(pf.detectar(g2, geo.Plano("XY"))) == _sin_islas(g2, monkeypatch)
    assert partidas[0] == 9                               # solo la isla nueva (r0 + puente + r1) se volvió a partir

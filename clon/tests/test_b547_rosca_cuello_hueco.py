# -*- coding: utf-8 -*-
"""B-547: la rosca en el cuello vaciado de una botella (un tubo) caía al corte helicoidal lento porque la varilla
directa de B-461 rellenaba el hueco; ahora la varilla sale hueca y da lo mismo que el corte."""
import pytest

from omnicad import api
from omnicad.nucleo import geometria as geo
from omnicad.nucleo import solidos_crear as sc


def _llamar(s, nombre, **argumentos):
    r = api.llamar(s, nombre, argumentos)
    assert r["ok"], r
    return r["result"]


def _botella_roscada():
    s = api.Sesion()
    _llamar(s, "create_cylinder", radius=30, height=80)
    _llamar(s, "create_cylinder", radius=10, height=15, z=80, operation="join")
    tapa = max((f for f in _llamar(s, "find_faces")["faces"] if f["type"] == "plane"), key=lambda f: f["center"][2])["id"]
    _llamar(s, "shell", body="Cuerpo1", faces=[tapa], thickness=1.5)            # el cuerpo ya modificado
    cuello = [f["id"] for f in _llamar(s, "find_faces")["faces"]
              if f["type"] == "cylinder" and f.get("radius") == 10 and f["center"][2] > 80][0]
    _llamar(s, "create_thread", faces=[cuello], thread="M20x2.5", modeled=True)
    return next(iter(s.doc.estado_final.cuerpos.values())).forma


def test_b547_rosca_en_cuello_hueco_va_directa_y_da_lo_mismo_que_el_corte(monkeypatch):
    directas, original = [], sc._rosca_directa
    monkeypatch.setattr(sc, "_rosca_directa", lambda *a, **k: directas.append(original(*a, **k)) or directas[-1])
    rapida = _botella_roscada()
    assert directas and directas[-1] is not None and geo.es_valida(rapida)        # sin caer al corte lento
    monkeypatch.setattr(sc, "_rosca_directa", lambda *a, **k: None)              # el corte de siempre
    lenta = _botella_roscada()
    assert geo.volumen(rapida) == pytest.approx(geo.volumen(lenta), rel=1e-5)
    assert len(geo.solidos(rapida)) == len(geo.solidos(lenta)) == 1


def test_b547_un_hueco_descentrado_no_es_un_tubo():
    largo = 15.0
    descentrado = geo.cilindro(3, largo, base=(4.0, 0.0, 0.0))
    assert sc._radio_hueco(descentrado, (0.0, 0.0, 0.0), (0.0, 0.0, 1.0), largo, 8.0) == 0.0
    centrado = geo.cilindro(5, largo)
    assert sc._radio_hueco(centrado, (0.0, 0.0, 0.0), (0.0, 0.0, 1.0), largo, 8.0) == pytest.approx(5.0)

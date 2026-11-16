# -*- coding: utf-8 -*-
"""B-567: cuando el kernel insiste en fallar, los reintentos de una booleana tardaban 34-45 s antes del error. Ahora
paran en `_TOPE_REINTENTOS_S` (o el doble de la primera pasada); el reintento que más rescata va primero."""
import time

import pytest

from omnicad.nucleo import geometria as geo


def test_b567_el_error_llega_en_segundos_y_no_tras_todos_los_reintentos(monkeypatch):
    monkeypatch.setattr(geo, "_TOPE_REINTENTOS_S", 1.0)
    pasadas, original = [], geo._booleana

    def lenta(*a, **k):
        pasadas.append(k)
        time.sleep(0.3)                                    # una pasada lenta, como con caras libres
        return original(*a, **k)
    monkeypatch.setattr(geo, "_booleana", lenta)
    monkeypatch.setattr(geo, "_problema_booleana", lambda *a, **k: (2, "el resultado quedó vacío", 1.0, 0.0))
    t = time.monotonic()
    with pytest.raises(geo.ErrorGeometria, match="no logró corregirlo"):
        geo.booleano(geo.caja(10, 10, 10), geo.caja(10, 10, 10, origen=(5, 5, 5)), "unir")
    assert time.monotonic() - t < 2.5
    assert 2 < len(pasadas) < 1 + len(geo._REINTENTOS_BOOLEANA)      # reintenta, pero no todos
    assert pasadas[1].get("paralelo") is False                        # primero el que más rescata


def test_b567_una_primera_pasada_lenta_deja_el_doble_para_reintentar(monkeypatch):
    monkeypatch.setattr(geo, "_TOPE_REINTENTOS_S", 1.0)
    pasadas, original = [], geo._booleana

    def lenta(*a, **k):
        pasadas.append(k)
        time.sleep(2.0 if len(pasadas) == 1 else 0.1)      # una pieza pesada: la primera pasada tarda más que el tope
        return original(*a, **k)
    monkeypatch.setattr(geo, "_booleana", lenta)
    rescate = {"n": 0}

    def problema(*a, **k):
        rescate["n"] += 1
        return None if rescate["n"] == 5 else (2, "el resultado quedó vacío", 1.0, 0.0)
    monkeypatch.setattr(geo, "_problema_booleana", problema)
    geo.booleano(geo.caja(10, 10, 10), geo.caja(10, 10, 10, origen=(5, 5, 5)), "unir")    # el 4.º reintento rescata
    assert len(pasadas) == 5

# -*- coding: utf-8 -*-
"""Pieza de calibración de holguras (P-29-6): núcleo puro y herramienta create_clearance_test."""
import math

import pytest

from omnicad import api
from omnicad.nucleo import calibracion as cal
from omnicad.nucleo import geometria as geo


def llamar(sesion, nombre, **args):
    r = api.llamar(sesion, nombre, args)
    assert r["ok"], r
    return r["result"]


def volumen_esperado(r, diametro, espesor):
    """Placa de largo × ancho × espesor menos un cilindro de Ø diametro + 2·holgura por agujero."""
    return r["largo"] * r["ancho_placa"] * espesor - sum(math.pi * (diametro / 2 + h) ** 2 * espesor
                                                         for h in r["holguras"])


def test_nucleo_sin_etiquetas_volumen_exacto_y_holguras():
    r = cal.pieza_calibracion_holguras(5, 0.1, 0.1, 5, 3, etiquetas=False)
    assert r["holguras"] == [0.1, 0.2, 0.3, 0.4, 0.5]
    assert r["diametros_agujero"] == [5.2, 5.4, 5.6, 5.8, 6.0]
    assert geo.es_valida(r["placa"]) and geo.es_valida(r["peine"])
    assert geo.volumen(r["placa"]) == pytest.approx(volumen_esperado(r, 5, 3), rel=1e-6)
    (x0, y0, z0), (x1, y1, z1) = geo.caja_envolvente(r["placa"])
    assert (x1 - x0, y1 - y0, z1 - z0) == pytest.approx((r["largo"], r["ancho_placa"], 3.0), abs=1e-6)
    (px0, py0, pz0), (px1, py1, pz1) = geo.caja_envolvente(r["peine"])
    assert py0 > y1 and pz0 == pytest.approx(0, abs=1e-6)            # el peine queda al lado de la placa, en la cama
    assert px1 - px0 == pytest.approx(r["largo"], abs=1e-6) and pz1 == pytest.approx(2 + 3 + 1, abs=1e-6)
    assert len(geo.solidos(r["placa"])) == len(geo.solidos(r["peine"])) == 1


def test_nucleo_etiquetas_graban_sin_romper_los_agujeros():
    r = cal.pieza_calibracion_holguras(5, 0.1, 0.1, 5, 3)
    assert geo.es_valida(r["placa"])
    quitado = volumen_esperado(r, 5, 3) - geo.volumen(r["placa"])
    assert 0 < quitado < 5 * 0.4 * 20                  # 5 etiquetas de 0,4 mm de profundidad y menos de 20 mm² cada una
    assert geo.caja_envolvente(r["placa"])[1][2] == pytest.approx(3.0, abs=1e-4)      # el grabado no sube la placa


@pytest.mark.parametrize("args,texto", [
    ({"diametro": 0}, "diámetro"), ({"diametro": 5, "paso": 0}, "paso"), ({"diametro": 5, "espesor": -1}, "espesor"),
    ({"diametro": 5, "holgura_inicial": -0.1}, "holgura inicial"), ({"diametro": 5, "cantidad": 0}, "cantidad"),
    ({"diametro": 5, "cantidad": cal.CANTIDAD_MAXIMA + 1}, "cantidad"), ({"diametro": 5, "cantidad": 2.5}, "cantidad")])
def test_nucleo_medidas_invalidas(args, texto):
    with pytest.raises(geo.ErrorGeometria, match=texto):
        cal.pieza_calibracion_holguras(etiquetas=False, **args)


def test_herramienta_crea_placa_y_peine_en_un_paso_y_deshacer_lo_quita():
    s = api.Sesion()
    r = llamar(s, "create_clearance_test", diameter=4, start_clearance=0.15, step=0.05, count=4, thickness=2.5,
               labels=False)
    assert r["clearances"] == [0.15, 0.2, 0.25, 0.3]
    assert r["feature"]["type"] == "calibracion_holguras" and len(s.doc.operaciones) == 1
    cuerpos = {c["name"]: c for c in r["bodies_created"]}
    assert set(cuerpos) == {"Placa de calibración", "Peine de calibración"}
    nucleo = cal.pieza_calibracion_holguras(4, 0.15, 0.05, 4, 2.5, etiquetas=False)
    assert cuerpos["Placa de calibración"]["volume"] == pytest.approx(geo.volumen(nucleo["placa"]), rel=1e-4)
    assert cuerpos["Peine de calibración"]["volume"] == pytest.approx(geo.volumen(nucleo["peine"]), rel=1e-4)
    llamar(s, "undo")
    assert llamar(s, "get_scene_info")["bodies"] == []


def test_herramienta_con_parametro_y_etiquetas():
    s = api.Sesion()
    llamar(s, "create_parameter", name="perno", expression="6 mm")
    r = llamar(s, "create_clearance_test", diameter="perno", count=3)           # etiquetas por defecto
    placa = next(c for c in r["bodies_created"] if c["name"].startswith("Placa"))
    nucleo = cal.pieza_calibracion_holguras(6, 0.1, 0.1, 3, 3)
    assert placa["volume"] == pytest.approx(geo.volumen(nucleo["placa"]), rel=1e-4)
    assert 0 < volumen_esperado(nucleo, 6, 3) - placa["volume"] < 3 * 0.4 * 20          # lo grabado
    llamar(s, "set_parameter", name="perno", expression="8 mm")                 # el paso sigue al parámetro
    placa = next(c for c in llamar(s, "get_scene_info")["bodies"] if c["name"].startswith("Placa"))
    assert placa["volume"] > geo.volumen(nucleo["placa"])


@pytest.mark.parametrize("args", [{"count": 0}, {"count": 21}, {"count": True}, {"diameter": -1}, {"step": 0},
                                  {"thickness": 0}, {"start_clearance": -0.1}])
def test_herramienta_rechaza_medidas_invalidas_sin_tocar_el_documento(args):
    s = api.Sesion()
    r = api.llamar(s, "create_clearance_test", {"diameter": 5, **args})
    assert not r["ok"] and r["error_kind"] == "INVALID_ARGUMENTS"
    assert s.doc.operaciones == []


def test_herramienta_pide_el_diametro():
    s = api.Sesion()
    r = api.llamar(s, "create_clearance_test", {})
    assert not r["ok"] and r["error_kind"] == "INVALID_ARGUMENTS" and s.doc.operaciones == []

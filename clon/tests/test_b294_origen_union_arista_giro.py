# -*- coding: utf-8 -*-
"""B-294: el origen de unión sigue el sentido de la arista guardado por B-283."""
import math

import numpy as np
import pytest

from omnicad import api


def _llamar(sesion, nombre, **argumentos):
    resultado = api.llamar(sesion, nombre, argumentos)
    assert resultado["ok"], resultado
    return resultado["result"]


def _crear_origen(punto):
    sesion = api.Sesion()
    _llamar(sesion, "create_box", length=20, width=30, height=40, anchor="corner")
    _llamar(sesion, "create_parameter", name="a", expression="1")
    _llamar(sesion, "move_body", body="Cuerpo1", rotate=["0", "a", "0"], pivot="origin")
    aristas = _llamar(sesion, "find_edges", body="Cuerpo1")["edges"]
    arista = max((e for e in aristas if e.get("type") == "line"), key=lambda e: e["length"])["id"]
    identificador = _llamar(sesion, "create_joint_origin", geometry=arista, body="Cuerpo1", snap=punto)["joint_origin"]["id"]
    return sesion, identificador


@pytest.mark.parametrize("punto", ["start", "end", "center"])
def test_el_origen_y_z_siguen_la_arista_al_girar_el_cuerpo(punto):
    sesion, identificador = _crear_origen(punto)
    plano = sesion.doc.estado_final.planos[identificador]
    origen, z = np.array(plano.origen), np.array(plano.normal)
    for grados in (-1, 1):
        _llamar(sesion, "set_parameter", name="a", expression=str(grados))
        angulo = math.radians(grados - 1)
        c, s = math.cos(angulo), math.sin(angulo)
        giro = np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
        plano = sesion.doc.estado_final.planos[identificador]
        assert np.allclose(plano.origen, giro @ origen, atol=1e-8)
        assert np.allclose(plano.normal, giro @ z, atol=1e-8)
        assert np.asarray(plano.normal) @ z > 0.99


@pytest.mark.parametrize("punto", ["start", "end", "center"])
def test_una_receta_sin_sentido_conserva_los_extremos_ordenados(punto):
    sesion, identificador = _crear_origen(punto)
    receta = _llamar(sesion, "get_recipe")["recipe"]
    paso = next(p for p in receta["operaciones"] if p["id"] == identificador)
    assert paso["params"]["origen"].pop("sentido") in (-1, 1)
    vieja = api.Sesion()
    _llamar(vieja, "apply_recipe", recipe=receta)
    for grados in (1, -1):
        _llamar(vieja, "set_parameter", name="a", expression=str(grados))
        angulo = math.radians(grados)
        extremo = np.array([40 * math.sin(angulo), 0, 40 * math.cos(angulo)])
        inicio, fin = (np.zeros(3), extremo) if grados > 0 else (extremo, np.zeros(3))
        esperado = {"start": inicio, "end": fin, "center": extremo / 2}[punto]
        plano = vieja.doc.estado_final.planos[identificador]
        assert np.allclose(plano.origen, esperado, atol=1e-8)
        assert np.allclose(plano.normal, (fin - inicio) / 40, atol=1e-8)

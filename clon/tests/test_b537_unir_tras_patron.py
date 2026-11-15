# -*- coding: utf-8 -*-
"""B-537: Extruir › Unir una brida sobre un colector con Patrón de operaciones daba «sólido inválido» (a 112,5) o
aceptaba un cuerpo inválido (a 10,1: los dos sólidos sin fundir). El kernel la hacía bien; juntar las caras coplanares
la rompía. Receta del ejercicio de E11 (`evidencias/reportes_pc/2026-11-15_ejercicio_video/`)."""
import json
from pathlib import Path

import pytest

from omnicad import api
from omnicad.nucleo import geometria as geo

RECETA = Path(__file__).parent / "datos" / "b537_colector_hasta_patron.json"


@pytest.mark.parametrize("desfase", ["112.5", "10.1"])
def test_la_brida_se_une_valida_al_colector_con_patron(desfase):
    s = api.Sesion()
    assert api.llamar(s, "apply_recipe", {"recipe": json.loads(RECETA.read_text(encoding="utf-8"))["recipe"],
                                          "mode": "replace"})["ok"]
    antes = api.llamar(s, "check_geometry", {})["result"]["bodies"][0]["volume"]
    r = api.llamar(s, "extrude", {"sketch": "Brida", "profile": [3], "distance": 10, "start": "offset",
                                  "start_offset": desfase, "operation": "join"})
    assert r["ok"], r
    cuerpo = api.llamar(s, "check_geometry", {})["result"]["bodies"][0]
    assert cuerpo["valid"] and cuerpo["solids"] == 1 and cuerpo["self_intersections"] == 0
    assert antes < cuerpo["volume"] < antes + 32586.2 - 1000          # suma la brida menos lo que se solapa


def test_una_union_que_no_funde_el_solape_no_es_creible():
    """Lo que dejaba pasar el rango de volumen: los dos sólidos sin fundir pesan justo la suma."""
    a, b = geo.caja(10, 10, 10), geo.caja(10, 10, 10, origen=(5, 0, 0))
    sin_fundir = geo.compuesto([a, b])
    problema = geo._problema_booleana(a, b, "unir", sin_fundir, geo._volumenes_entrada(a, b))
    assert problema is not None and "no fundió" in problema[1]
    assert geo._problema_booleana(a, b, "unir", geo.booleano(a, b, "unir"), geo._volumenes_entrada(a, b)) is None

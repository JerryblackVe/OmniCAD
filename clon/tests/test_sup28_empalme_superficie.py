# -*- coding: utf-8 -*-
"""SUP-28: Empalme y Chaflán de superficie con las opciones del sólido (Fusion usa el mismo diálogo: SFC-FILLET-CHAMFER).
Caja de superficie de 20 mm con la esquina en el origen; las áreas esperadas salen a mano."""
import math

import pytest

from omnicad import api
from omnicad.nucleo import geometria as geo
from omnicad.timeline.ops_superficie import OpSupEmpalme

VERTICAL = "nearest:[0,0,10]"          # la arista vertical que pasa por el origen


def _caja():
    s = api.Sesion()
    assert api.llamar(s, "create_surface_box", {"length": 20, "width": 20, "height": 20, "anchor": "corner"})["ok"]
    return s


def _area(s, **args):
    r = api.llamar(s, "fillet_surface", {"body": "op1.c1", **args})
    assert r["ok"], r
    forma = s.doc.estado_final.cuerpo("op1.c1").forma
    assert geo.es_valida(forma)
    return geo.area(forma)


def _empalme(r):        # una arista de 20 mm entre caras a 90°: tira 2·r·20, suma un cuarto de cilindro, recorta 2 esquinas
    return 2400 - 2 * r * 20 + math.pi * r / 2 * 20 - 2 * (r * r - math.pi * r * r / 4)


@pytest.mark.parametrize("args,esperada", [
    ({"size": 2}, _empalme(2)),
    ({"size": 2, "radius_type": "chord"}, _empalme(math.sqrt(2))),          # cuerda 2 a 90°: r = 2 / (2·sen 45°)
    ({"size": 2, "fillet_type": "chamfer", "chamfer_type": "two_distances", "distance2": 3},
     2400 - 100 + math.sqrt(13) * 20 - 2 * 3),
    ({"size": 2, "fillet_type": "chamfer", "chamfer_type": "distance_angle", "angle": 30},
     2400 - (2 + 2 * math.tan(math.radians(30))) * 20 + 2 / math.cos(math.radians(30)) * 20
     - 2 * 2 * 2 * math.tan(math.radians(30)) / 2),
])
def test_tipos_de_radio_y_de_chaflan_dan_el_area_exacta(args, esperada):
    assert _area(_caja(), edges=VERTICAL, **args) == pytest.approx(esperada, abs=1e-3)


def test_radio_variable_queda_entre_los_dos_constantes():
    variable = _area(_caja(), edges=VERTICAL, size=2, radius_type="variable", end_radius=4)
    assert _empalme(4) < variable < _empalme(2)


def test_esquinas_de_tres_aristas_cambian_el_resultado():
    tres = ["nearest:[0,0,10]", "nearest:[10,0,0]", "nearest:[0,10,0]"]
    bola = _area(_caja(), edges=tres, size=2)
    assert _area(_caja(), edges=tres, size=2, corner_type="setback", setback=4) != pytest.approx(bola, abs=1e-3)
    chaflan = _area(_caja(), edges=tres, size=2, fillet_type="chamfer")
    assert _area(_caja(), edges=tres, size=2, fillet_type="chamfer", corner_type="blend") != pytest.approx(chaflan, abs=1e-3)


def test_cadena_tangente_redondea_todo_el_borde_de_arriba():
    s, todas = _caja(), _caja()
    for caso in (s, todas):
        _area(caso, edges="|Z", size=3)                                # las 4 verticales: el borde de arriba es una cadena
    una = _area(s, edges="nearest:[10,0,20]", size=1)
    # OpenCascade propaga siempre por la cadena tangente (también en el sólido: solidos_modificar, «Límites del kernel»)
    assert una == pytest.approx(_area(todas, edges=">Z", size=1, tangent_chain=False), abs=1e-3)


def test_esquina_de_chaflan_con_empalme_da_error_y_receta_vieja_sin_cadena():
    r = api.llamar(_caja(), "fillet_surface", {"edges": VERTICAL, "size": 2, "corner_type": "miter"})
    assert not r["ok"] and "corner_type=miter" in r["mensaje"], r
    assert OpSupEmpalme.migrar_receta({"params": {"tipo": "empalme"}})["params"]["cadena_tangente"] is False

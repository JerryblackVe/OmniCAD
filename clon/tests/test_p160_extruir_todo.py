"""P-160 (Gerardo): Extruir con «Todo» y «Un lado» va hacia donde hay cuerpos; con cuerpos a los dos lados, el de la
flecha; sin cuerpos, aviso de 1 renglón y la flecha en rojo."""
import numpy as np
import pytest

from omnicad import api
from omnicad.nucleo import geometria as geo
from omnicad.nucleo import solidos_crear as sc
from omnicad.ui import manipuladores as mp
from omnicad.ui.comando import ContextoComando
from omnicad.ui.comandos import solido


def _extruir(cara, z0=0, operacion="cut", invertir=False, otra=False):
    s = api.Sesion()
    api.llamar(s, "create_box", {"length": 20, "width": 20, "height": 10, "z": z0})
    if otra:
        api.llamar(s, "create_box", {"length": 20, "width": 20, "height": 10, "z": z0 - 30})
    assert api.llamar(s, "create_sketch", {"plane": cara, "name": "e", "body": "Cuerpo1"})["ok"]
    api.llamar(s, "draw_rectangle", {"sketch": "e", "x1": -3, "y1": -3, "x2": 3, "y2": 3})
    r = api.llamar(s, "extrude", {"sketch": "e", "profile": 0, "extent": "all", "operation": operacion,
                                  "reverse": invertir})
    assert r["ok"], r
    return sorted(round(c["volume"], 3) for c in api.llamar(s, "get_scene_info", {})["result"]["bodies"])


@pytest.mark.parametrize("cara", [">Z", "<Z"])
def test_p160_desde_una_cara_corta_hacia_el_material(cara):
    assert _extruir(cara) == [4000 - 360]               # caja 20×20×10 menos el prisma de 6×6×10


def test_p160_intersecar_va_hacia_el_material():
    assert _extruir(">Z", operacion="intersect") == [360]


@pytest.mark.parametrize("invertir", [False, True])
def test_p160_con_cuerpo_a_los_dos_lados_gana_la_flecha(invertir):
    assert _extruir("XY", z0=-5, invertir=invertir) == [4000 - 180]     # corta solo la mitad del lado de la flecha
    assert _extruir("XY", z0=5, otra=True, invertir=invertir) == [4000 - 360, 4000]


def test_p160_sin_cuerpos_a_ningun_lado_el_aviso_es_de_un_renglon():
    with pytest.raises(geo.ErrorGeometria, match="^No hay ningún cuerpo para atravesar con «Todo».$"):
        sc.lado_todo(0.0, 0.0, 1.0)
    assert sc.lado_todo(-10.0, 0.0, 1.0) == -1.0 and sc.lado_todo(0.0, 10.0, -1.0) == 1.0
    assert sc.lado_todo(-5.0, 5.0, -1.0) == -1.0


def test_p160_la_superficie_tambien_va_hacia_el_cuerpo():
    s = api.Sesion()
    api.llamar(s, "create_box", {"length": 20, "width": 20, "height": 10})
    api.llamar(s, "create_sketch", {"plane": ">Z", "name": "e", "body": "Cuerpo1"})
    api.llamar(s, "draw_rectangle", {"sketch": "e", "x1": -3, "y1": -3, "x2": 3, "y2": 3})
    r = api.llamar(s, "create_surface_extrude", {"profiles": [{"sketch": "e", "profile": 0}], "extent": "all"})
    assert r["ok"], r
    sup = next(c for c in api.llamar(s, "get_scene_info", {})["result"]["bodies"] if c["type"] == "surface")
    assert sup["bounding_box"]["max"][2] <= 10 + 1e-6 and sup["bounding_box"]["min"][2] < 0     # bajó por la caja


def test_p160_la_flecha_apunta_al_cuerpo_y_sin_cuerpos_va_en_rojo():
    s = api.Sesion()
    vacio = solido._flecha_todo(ContextoComando(s.doc), np.zeros(3), np.array([0.0, 0.0, 1.0]))
    assert isinstance(vacio, mp.FlechaSentido) and vacio.color == mp.COLORES_EJE[0]
    api.llamar(s, "create_box", {"length": 20, "width": 20, "height": 10})
    flecha = solido._flecha_todo(ContextoComando(s.doc), np.array([0.0, 0.0, 10.0]), np.array([0.0, 0.0, 1.0]))
    assert flecha.color == mp.AMARILLO and np.allclose(flecha.direccion, (0, 0, -1))
    assert flecha.empezar(None, None, None) is None          # no se arrastra: solo muestra el sentido

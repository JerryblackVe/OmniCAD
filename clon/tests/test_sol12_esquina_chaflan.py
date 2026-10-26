"""SOL-12: tipo de esquina del chaflán (Chaflán, Inglete o Mezcla)."""
import pytest

from omnicad import api
from omnicad.nucleo import geometria as geo


def llamar(sesion, nombre, **args):
    r = api.llamar(sesion, nombre, args)
    assert r["ok"], r
    return r["result"]



def _aristas_de_la_esquina(s):
    ids = []
    for punto in ("[5,5,5]", "[5,0,10]", "[0,5,10]"):
        ids.append(llamar(s, "find_edges", body="Cubo", selector=f"nearest:{punto}")["edges"][0]["id"])
    return ids


def test_inglete_une_los_chaflanes_en_un_punto():
    s = api.Sesion()
    llamar(s, "create_box", length=10, width=10, height=10, name="Cubo")
    aristas = _aristas_de_la_esquina(s)
    llamar(s, "chamfer", edges=aristas, distance=2, tangent_chain=False, corner_type="miter")
    forma = s.cuerpo("Cubo").forma
    assert geo.es_valida(forma)
    assert geo.volumen(forma) == pytest.approx(946.0, abs=1e-6)       # 1000 − 54 (inclusión–exclusión de las 3 cuñas)
    assert len(geo.caras(forma)) == 9                                 # sin la cara chica de unión
    llamar(s, "undo")
    llamar(s, "chamfer", edges=_aristas_de_la_esquina(s), distance=2, tangent_chain=False)    # esquina «Chaflán»
    por_defecto = s.cuerpo("Cubo").forma
    assert geo.volumen(por_defecto) == pytest.approx(945.3333333, abs=1e-5)
    assert len(geo.caras(por_defecto)) == 10


def test_inglete_sin_esquina_no_hace_nada_y_avisa():
    s = api.Sesion()
    llamar(s, "create_box", length=10, width=10, height=10, name="Cubo")
    arista = llamar(s, "find_edges", body="Cubo", selector="nearest:[5,0,10]")["edges"][0]["id"]
    r = api.llamar(s, "chamfer", dict(edges=arista, distance=2, tangent_chain=False, corner_type="miter"))
    assert not r["ok"] and "esquinas" in r["mensaje"]


def test_inglete_lejos_del_origen_sigue_ingleteando():
    """La losa de corte se centra en el origen del plano: con el cubo en x=500 la esquina quedaba afuera (sin error)."""
    s = api.Sesion()
    llamar(s, "create_box", length=10, width=10, height=10, name="Cubo")
    llamar(s, "move_body", body="Cubo", translate=[500, 0, 0])
    ids = []
    for punto in ("[505,5,5]", "[505,0,10]", "[500,5,10]"):
        ids.append(llamar(s, "find_edges", body="Cubo", selector=f"nearest:{punto}")["edges"][0]["id"])
    llamar(s, "chamfer", edges=ids, distance=2, tangent_chain=False, corner_type="miter")
    forma = s.cuerpo("Cubo").forma
    assert geo.es_valida(forma)
    assert geo.volumen(forma) == pytest.approx(946.0, abs=1e-6)
    assert len(geo.caras(forma)) == 9


def test_mezcla_redondea_la_union_de_los_chaflanes_y_sigue_valida():
    s = api.Sesion()
    llamar(s, "create_box", length=10, width=10, height=10, name="Cubo")
    llamar(s, "chamfer", edges=_aristas_de_la_esquina(s), distance=2, tangent_chain=False, corner_type="blend")
    forma = s.cuerpo("Cubo").forma
    assert geo.es_valida(forma)
    assert len(geo.caras(forma)) == 13                                # inglete (9 caras) + 3 redondeos de la unión + el vértice
    assert 945.0 < geo.volumen(forma) < 946.0                         # el inglete deja 946: el redondeo saca un poco más
    r = api.llamar(s, "chamfer", dict(edges="|Z and <X and <Y", distance=2, tangent_chain=False, corner_type="blend"))
    assert not r["ok"] and "esquina" in r["mensaje"]                  # sin tres chaflanes que se junten no hay mezcla

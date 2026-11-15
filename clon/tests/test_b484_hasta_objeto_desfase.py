"""B-484: Extruir › «Hasta objeto» con desfase NEGATIVO acerca el final al perfil, como Fusion («Offset: distance to
offset extrusion from selected object»; Fusion con la cara a z=20 y −5 llega a z=15). Antes sumaba: cara a z=27 y −10
llegaba a z=37."""
import pytest

from omnicad import api


def _ok(s, nombre, **args):
    r = api.llamar(s, nombre, args)
    assert r["ok"], r
    return r["result"]


def _z(s):
    """(z mínima, z máxima) del último cuerpo creado."""
    caja = _ok(s, "get_scene_info")["bodies"][-1]["bounding_box"]
    return caja["min"][2], caja["max"][2]


def _circulo(s):
    _ok(s, "create_sketch", plane="XY", name="B")
    _ok(s, "draw_circle", radius=3, center_x=50, sketch="B")


@pytest.mark.parametrize("desfase, alto", [(-10, 17), (-5, 22), (0, 27), (5, 32)])
def test_cara_paralela_a_z27(desfase, alto):
    s = api.Sesion()
    _circulo(s)
    _ok(s, "create_construction_plane", plane="XY", offset=27, name="Tope")
    _ok(s, "extrude", sketch="B", extent="to_object", to="Tope", to_offset=desfase)
    assert _z(s) == pytest.approx((0, alto))


@pytest.mark.parametrize("z_caja, desfase, esperado", [(40, -10, (0, 30)), (-40, -10, (-4, 0)), (-40, 5, (-19, 0))])
def test_cuerpo_delante_o_detras_del_perfil(z_caja, desfase, esperado):
    """Hasta un cuerpo (el otro camino: el objeto se corre y se recorta): el desfase negativo acerca también cuando el
    cuerpo queda detrás del perfil (la extrusión va hacia −Z)."""
    s = api.Sesion()
    _ok(s, "create_box", length=200, width=200, height=26, z=z_caja, name="Caja")   # z 40..66 o −40..−14
    _circulo(s)
    _ok(s, "extrude", sketch="B", extent="to_object", to="Caja", to_mode="body", to_offset=desfase,
        operation="new_body")
    assert _z(s) == pytest.approx(esperado)


def test_un_desfase_que_cruza_el_perfil_es_un_error():
    s = api.Sesion()
    _circulo(s)
    _ok(s, "create_construction_plane", plane="XY", offset=27, name="Tope")
    r = api.llamar(s, "extrude", {"sketch": "B", "extent": "to_object", "to": "Tope", "to_offset": -30})
    assert not r["ok"] and "desfase" in r["mensaje"], r

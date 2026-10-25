"""SOL-16: Dividir cara con «Según vector» y «Punto más cercano»."""
import pytest

from omnicad import api
from omnicad.nucleo import geometria as geo


def llamar(sesion, nombre, **args):
    r = api.llamar(sesion, nombre, args)
    assert r["ok"], r
    return r["result"]


def _escena(altura_boceto):
    """Caja 10x10x10 y una línea de boceto x = 3 sobre un plano a `altura_boceto`."""
    s = api.Sesion()
    llamar(s, "create_box", length=10, width=10, height=10, name="Caja")
    llamar(s, "create_construction_plane", plane="XY", offset=altura_boceto, name="Alto")
    llamar(s, "create_sketch", plane="Alto", name="Guia")
    llamar(s, "draw_line", start_x=3, start_y=-5, end_x=3, end_y=15)
    return s


def _tapa(s):
    return llamar(s, "find_faces", body="Caja", selector=">Z")["faces"][0]["id"]


@pytest.mark.parametrize("tipo,altura", [("vector", 25), ("closest_point", 25)])
def test_la_curva_se_proyecta_sobre_la_tapa_y_la_parte(tipo, altura):
    s = _escena(altura)
    extra = {"direction": "Z"} if tipo == "vector" else {}
    llamar(s, "split_face", faces=_tapa(s), tool={"sketch": "Guia", "curve": 3}, split_type=tipo, **extra)
    forma = s.cuerpo("Caja").forma
    assert geo.es_valida(forma) and geo.volumen(forma) == pytest.approx(1000)
    assert len(geo.caras(forma)) == 7
    assert sorted(geo.area(c) for c in geo.caras(forma))[:2] == pytest.approx([20, 80])


def test_vector_pide_direccion_y_closest_la_rechaza():
    s = _escena(25)
    tapa = _tapa(s)
    curva = {"sketch": "Guia", "curve": 3}
    for args in ({"split_type": "vector"}, {"split_type": "closest_point", "direction": "Z"}):
        r = api.llamar(s, "split_face", dict(faces=tapa, tool=curva, **args))
        assert not r["ok"] and r["error_kind"] == "INVALID_ARGUMENTS"
    r = api.llamar(s, "split_face", dict(faces=tapa, tool="YZ", split_type="vector", direction="Z"))
    assert not r["ok"]          # un plano no se puede proyectar


def test_vector_horizontal_no_cruza_la_tapa():
    s = _escena(25)
    r = api.llamar(s, "split_face", dict(faces=_tapa(s), tool={"sketch": "Guia", "curve": 3}, split_type="vector",
                                         direction="X"))
    assert not r["ok"] or len(geo.caras(s.cuerpo("Caja").forma)) == 6

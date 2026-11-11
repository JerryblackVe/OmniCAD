"""B-159: un empalme cuyo radio iguala el ancho de una cara vecina (1 mm en el borde de una pared vaciada de 1 mm)
cerraba la app (access violation en BRepFilletAPI_MakeFillet.Build). El caso del cazador vive en
tests/corpus_caza/b159_empalme_cierre.json y corre aislado en tests/test_caza_regresion.py."""
import pytest

from omnicad import api
from omnicad.nucleo import geometria as geo
from omnicad.nucleo import solidos_modificar, superficies


def _caja_vaciada():
    """Caja 60 × 50 × 40 vaciada a 1 mm sin la base: `Cuerpo1/E10` es el borde exterior del canto de 1 mm."""
    s = api.Sesion()
    for nombre, args in (("create_box", {"length": 60, "width": 50, "height": 40}),
                         ("shell", {"body": "Cuerpo1", "thickness": 1, "faces": "<Z"})):
        assert api.llamar(s, nombre, args)["ok"]
    return s


def _borde(forma):
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    for e in geo._aristas_unicas(forma):
        c = BRepAdaptor_Curve(e)
        p = c.Value((c.FirstParameter() + c.LastParameter()) / 2)
        if abs(p.X() + 30) < 1e-6 and abs(p.Y()) < 1e-6 and abs(p.Z()) < 1e-6:
            return e
    raise AssertionError("no está el borde x = −30 del canto")


def test_radio_igual_al_canto_da_error_claro():
    s = _caja_vaciada()

    r = api.llamar(s, "fillet", {"body": "op1.c1", "edges": ["Cuerpo1/E10"], "radius": 1.0})   # antes: moría acá

    assert not r["ok"] and "se come justo una cara vecina" in r["mensaje"]


def test_un_poco_menos_que_el_canto_sigue_andando():
    s = _caja_vaciada()

    r = api.llamar(s, "fillet", {"body": "op1.c1", "edges": ["Cuerpo1/E10"], "radius": 0.99})

    assert r["ok"], r
    assert r["result"]["bodies_modified"][0]["volume"] == pytest.approx(11413.4834, abs=1e-3)


def test_radio_variable_y_empalme_de_superficie_tambien():
    forma = _caja_vaciada().cuerpo("Cuerpo1").forma
    borde = _borde(forma)

    with pytest.raises(geo.ErrorGeometria, match="se come justo"):
        solidos_modificar.empalme(forma, [{"aristas": [borde], "tipo": "variable", "radios": [(0, 1), (1, 1)]}])
    with pytest.raises(geo.ErrorGeometria, match="se come justo"):
        superficies.empalme_superficie(forma, [borde], 1.0)

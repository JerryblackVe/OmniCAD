"""B-290: empalmar un arco abierto con su mismo radio cerraba la app (access violation en BRepFilletAPI_MakeFillet.Build)."""
import pytest

from omnicad import api
from omnicad.nucleo import geometria as geo
from omnicad.nucleo import solidos_modificar, superficies


def _llamar(s, nombre, **args):
    r = api.llamar(s, nombre, args)
    assert r["ok"], (nombre, r)
    return r


def _caja_con_tubo():
    """Caja + barrido unido de un círculo de radio 3 que asoma por arriba: su arista `Cuerpo1/E1` es un arco abierto de r 3."""
    s = api.Sesion()
    _llamar(s, "create_box", length=100, width=60, height=20, anchor="corner")
    _llamar(s, "create_sketch", plane="XZ")
    _llamar(s, "draw_circle", radius=3, center_x=10, center_y=21)
    perfil = s.doc.operaciones[-1].id
    _llamar(s, "create_sketch", plane="XY")
    _llamar(s, "draw_line", start_x=10, start_y=0, end_x=10, end_y=50)
    _llamar(s, "draw_line", start_x=10, start_y=50, end_x=90, end_y=50)
    _llamar(s, "sweep", sketch=perfil, path_sketch=s.doc.operaciones[-1].id, operation="join")
    arco = _llamar(s, "find_edges", selector="|Z")["result"]["edges"][0]
    assert arco["type"] == "circle" and arco["radius"] == 3.0
    return s, arco["id"]


def test_arco_abierto_con_su_mismo_radio_da_error_claro():
    s, arco = _caja_con_tubo()

    r = api.llamar(s, "fillet", {"edges": [arco], "radius": "3 mm"})     # antes: el proceso moría acá

    assert not r["ok"] and "igual al del arco" in r["mensaje"]


def _forma_y_arco():
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    from OCP.GeomAbs import GeomAbs_Circle
    s, _ = _caja_con_tubo()
    forma = s.cuerpo("Cuerpo1").forma
    return forma, next(e for e in geo._aristas_unicas(forma)
                       if BRepAdaptor_Curve(e).GetType() == GeomAbs_Circle and not BRepAdaptor_Curve(e).IsClosed())


def test_empalme_de_superficie_sobre_el_mismo_arco_da_error_claro():
    forma, arco = _forma_y_arco()

    with pytest.raises(geo.ErrorGeometria, match="igual al del arco"):
        superficies.empalme_superficie(forma, [arco], 3.0)


def test_radio_variable_que_toca_el_radio_del_arco_da_error_claro():
    forma, arco = _forma_y_arco()

    with pytest.raises(geo.ErrorGeometria, match="igual al del arco"):
        solidos_modificar.empalme(forma, [{"aristas": [arco], "tipo": "variable", "radios": [(0, 3), (1, 3)]}])


def test_tapa_de_cilindro_con_su_mismo_radio_sigue_andando():
    s = api.Sesion()
    _llamar(s, "create_cylinder", radius=3, height=10)
    tapa = _llamar(s, "find_edges", selector="%CIRCLE")["result"]["edges"][0]

    _llamar(s, "fillet", edges=[tapa["id"]], radius="3 mm")     # círculo cerrado: queda una cúpula

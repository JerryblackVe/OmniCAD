"""Curva isoparamétrica (BOC-36, Fusion: Project/Include › Isoparametric Curve): U, V o ambas, Single o Distributed (por
distancia o por cantidad), recortadas a la cara, con vínculo (siguen a la cara) o sin él. Núcleo puro y herramienta de
la API (`isoparametric_curve`); la ventana usa las mismas funciones."""
import math

import pytest
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
from OCP.GeomAbs import GeomAbs_Cylinder, GeomAbs_Plane

from omnicad import api
from omnicad.nucleo import curvas3d as c3
from omnicad.nucleo import geometria as geo


def cara_de(forma, tipo, z=None):
    for c in geo.caras(forma):
        if BRepAdaptor_Surface(c).GetType() == tipo and (z is None or abs(geo.caja_envolvente(c)[0][2] - z) < 1e-6
                                                         and abs(geo.caja_envolvente(c)[1][2] - z) < 1e-6):
            return c
    raise AssertionError("no hay esa cara")


def test_u_single_en_un_cilindro_es_el_circulo_de_esa_altura_y_v_la_generatriz():
    lat = cara_de(geo.cilindro(10, 40), GeomAbs_Cylinder)
    (u,) = c3.isoparametricas(lat, (10, 0, 15), "u")
    assert u["tipo"] == "circulo" and u["radio"] == pytest.approx(10) and u["centro"] == pytest.approx([0, 0, 15])
    (v,) = c3.isoparametricas(lat, (0, 10, 15), "v")
    assert v["tipo"] == "linea" and v["puntos"][0] == pytest.approx([0, 10, 0]) and v["puntos"][1] == pytest.approx([0, 10, 40])


def test_both_da_las_dos_curvas_por_el_punto():
    lat = cara_de(geo.cilindro(10, 40), GeomAbs_Cylinder)
    r = c3.isoparametricas(lat, (10, 0, 15), "both")
    assert [d["tipo"] for d in r] == ["circulo", "linea"]


def test_distribuidas_por_cantidad_caen_en_k_sobre_n_mas_uno_y_no_tocan_el_borde():
    lat = cara_de(geo.cilindro(10, 40), GeomAbs_Cylinder)
    r = c3.isoparametricas(lat, (10, 0, 15), "u", "distributed", cantidad=4)
    assert sorted(d["centro"][2] for d in r) == pytest.approx([8, 16, 24, 32])
    r = c3.isoparametricas(lat, (10, 0, 15), "v", "distributed", cantidad=4)
    angulos = sorted(round(math.degrees(math.atan2(d["puntos"][0][1], d["puntos"][0][0])) % 360, 6) for d in r)
    assert angulos == pytest.approx([72, 144, 216, 288])


@pytest.mark.parametrize("cantidad, fracciones", [(1, [1 / 2]), (2, [1 / 3, 2 / 3]), (3, [1 / 4, 2 / 4, 3 / 4]),
                                                  (4, [0.2, 0.4, 0.6, 0.8])])
def test_distribuidas_en_una_cara_de_20_por_30_dan_lo_medido_en_fusion(cantidad, fracciones):
    tapa = cara_de(geo.caja(20, 30, 10), GeomAbs_Plane, z=10)
    r = c3.isoparametricas(tapa, (5, 7, 10), "u", "distributed", cantidad=cantidad)
    assert sorted(d["puntos"][0][1] for d in r) == pytest.approx([30 * f for f in fracciones])
    r = c3.isoparametricas(tapa, (5, 7, 10), "v", "distributed", cantidad=cantidad)
    assert sorted(d["puntos"][0][0] for d in r) == pytest.approx([20 * f for f in fracciones])


def test_distribuidas_por_distancia_pasan_por_el_punto_y_no_tocan_el_borde():
    lat = cara_de(geo.cilindro(10, 40), GeomAbs_Cylinder)
    r = c3.isoparametricas(lat, (10, 0, 15), "u", "distributed", distancia=10)
    assert sorted(d["centro"][2] for d in r) == pytest.approx([5, 15, 25, 35])        # 15 es el del punto
    r = c3.isoparametricas(lat, (10, 0, 20), "u", "distributed", distancia=10)
    assert sorted(d["centro"][2] for d in r) == pytest.approx([10, 20, 30])           # 0 y 40 son el borde: no cuentan


def test_en_una_cara_plana_las_curvas_son_lineas_y_el_punto_tiene_que_estar_en_la_cara():
    caja = geo.caja(20, 30, 10)
    arriba = cara_de(caja, GeomAbs_Plane, z=10)
    (u,) = c3.isoparametricas(arriba, (5, 7, 10), "u")
    assert u["tipo"] == "linea" and sorted(map(tuple, u["puntos"])) == pytest.approx([(0, 7, 10), (20, 7, 10)])
    with pytest.raises(geo.ErrorGeometria, match="no cae sobre la cara"):
        c3.isoparametricas(arriba, (50, 7, 10), "u")


def test_una_cara_con_agujero_recorta_la_curva_en_dos_tramos():
    forma = BRepAlgoAPI_Cut(geo.caja(40, 40, 10), geo.cilindro(5, 30, base=(20, 20, -5))).Shape()
    arriba = cara_de(forma, GeomAbs_Plane, z=10)
    r = c3.isoparametricas(arriba, (5, 20, 10), "u")                                  # la línea y = 20 cruza el agujero
    tramos = sorted(x for d in r for x in sorted(p[0] for p in d["puntos"]))
    assert len(r) == 2 and tramos == pytest.approx([0, 15, 25, 40])


@pytest.mark.parametrize("args", [{"direccion": "w"}, {"tipo": "mas"}, {"tipo": "distributed"},
                                  {"tipo": "distributed", "distancia": 5, "cantidad": 3},
                                  {"tipo": "distributed", "distancia": 0}, {"tipo": "distributed", "cantidad": 0},
                                  {"tipo": "distributed", "distancia": 0.01}])
def test_pedidos_que_no_sirven_se_rechazan_con_un_mensaje(args):
    lat = cara_de(geo.cilindro(10, 40), GeomAbs_Cylinder)
    with pytest.raises(geo.ErrorGeometria):
        c3.isoparametricas(lat, (10, 0, 15), **args)


# ---------------------------------------------------------------- la herramienta del MCP y la CLI
def llamar(s, nombre, **args):
    r = api.llamar(s, nombre, args)
    assert r["ok"], r
    return r["result"]


def falla(s, nombre, **args):
    r = api.llamar(s, nombre, args)
    assert not r["ok"], r
    return r


def _entidades(s, sketch):
    return {e["id"]: e for e in llamar(s, "get_sketch", sketch=sketch)["entities_3d"]}


@pytest.fixture
def cilindro():
    s = api.Sesion()
    llamar(s, "create_parameter", name="r", expression="10 mm")
    llamar(s, "create_cylinder", radius="r", height=40)
    llamar(s, "create_sketch", plane="XY", name="Iso")
    return s


def test_isoparametric_curve_crea_las_curvas_3d_con_su_origen(cilindro):
    s = cilindro
    r = llamar(s, "isoparametric_curve", face="Cuerpo1/F1", point=[10, 0, 15], direction="both")
    assert r["linked"] is True and len(r["entities"]) == 2
    e = _entidades(s, "Iso")
    circulo, linea = (e[i] for i in r["entities"])
    assert circulo["type"] == "circle" and circulo["radius"] == pytest.approx(10) and circulo["center"] == [0, 0, 15]
    assert linea["type"] == "line" and linea["length"] == pytest.approx(40)
    assert circulo["source"]["tool"] == "isoparametric_curve" and circulo["source"]["type"] == "single"


def test_con_vinculo_las_curvas_siguen_a_la_cara_y_sin_el_quedan_congeladas(cilindro):
    s = cilindro
    (con,) = llamar(s, "isoparametric_curve", face="Cuerpo1/F1", point=[10, 0, 15], direction="u")["entities"]
    (sin,) = llamar(s, "isoparametric_curve", face="Cuerpo1/F1", point=[10, 0, 25], direction="u", link=False)["entities"]
    assert "source" not in _entidades(s, "Iso")[sin]
    llamar(s, "set_parameter", name="r", expression="15 mm")
    e = _entidades(s, "Iso")
    assert e[con]["radius"] == pytest.approx(15)                               # la que tiene vínculo, recalculada
    assert e[sin]["radius"] == pytest.approx(10)                               # la libre, como estaba


def test_distribuidas_por_distancia_y_por_cantidad_con_la_api(cilindro):
    s = cilindro
    ids = llamar(s, "isoparametric_curve", face="Cuerpo1/F1", point=[10, 0, 20], direction="u", type="distributed",
                 distance=10)["entities"]
    e = _entidades(s, "Iso")
    assert sorted(e[i]["center"][2] for i in ids) == pytest.approx([10, 20, 30])
    ids = llamar(s, "isoparametric_curve", face="Cuerpo1/F1", point=[10, 0, 20], direction="v", type="distributed",
                 quantity=6)["entities"]
    assert len(ids) == 6 and all(_entidades(s, "Iso")[i]["type"] == "line" for i in ids)


def test_isoparametric_curve_rechaza_lo_que_no_sirve_y_no_cambia_el_boceto(cilindro):
    s = cilindro
    antes = llamar(s, "get_sketch", sketch="Iso")
    for args, tipo in (({"point": [10, 0]}, "INVALID_ARGUMENTS"), ({"point": [10, 0, 15], "distance": 5}, "INVALID_ARGUMENTS"),
                       ({"point": [10, 0, 15], "type": "distributed"}, "INVALID_ARGUMENTS"),
                       ({"point": [10, 0, 15], "type": "distributed", "distance": -1}, "INVALID_ARGUMENTS"),
                       ({"point": [10, 0, 15], "type": "distributed", "quantity": 1.5}, "INVALID_ARGUMENTS"),
                       ({"point": [10, 0, 15], "type": "distributed", "quantity": 0}, "INVALID_ARGUMENTS"),
                       ({"point": [10, 0, 99]}, "INVALID_GEOMETRY"),
                       ({"point": [10, 0, 15], "type": "distributed", "distance": 0.01}, "INVALID_GEOMETRY")):
        e = falla(s, "isoparametric_curve", face="Cuerpo1/F1", **args)
        assert e["error_kind"] == tipo, (args, e)
    assert falla(s, "isoparametric_curve", face="%PLANE", point=[10, 0, 15])["error_kind"] == "INVALID_ARGUMENTS"   # dos caras
    assert llamar(s, "get_sketch", sketch="Iso") == antes

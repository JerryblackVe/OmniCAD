# -*- coding: utf-8 -*-
"""PL7 (brechas_plasticity.md): desfase de aristas y de curvas de boceto («Offset Edge» / «Offset Face Loop»)."""
import math

import numpy as np
import pytest
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge
from OCP.gp import gp_Pnt

from omnicad import api
from omnicad.nucleo import desfase_aristas as da
from omnicad.nucleo import geometria as geo
from omnicad.nucleo.perfiles import proyectar_forma


def _arista(a, b):
    return BRepBuilderAPI_MakeEdge(gp_Pnt(*a), gp_Pnt(*b)).Edge()


def _lineas(forma, plano):
    """Segmentos [(x1, y1), (x2, y2)] de las líneas de `forma` proyectadas al plano."""
    return [(tuple(round(c, 4) for c in p[2]), tuple(round(c, 4) for c in p[3]))
            for p in proyectar_forma(forma, plano)[0] if p[0] == "linea"]


def _cuadrado(lado=10.0):
    return [_arista((0, 0, 0), (lado, 0, 0)), _arista((lado, 0, 0), (lado, lado, 0)),
            _arista((lado, lado, 0), (0, lado, 0)), _arista((0, lado, 0), (0, 0, 0))]


XY = geo.Plano("XY")


def test_una_recta_se_traslada_a_la_derecha_de_su_recorrido():
    (a,) = da.desfasar_aristas([_arista((0, 0, 0), (10, 0, 0))], XY, 2)
    assert _lineas(a, XY) == [((0.0, -2.0), (10.0, -2.0))]
    (b,) = da.desfasar_aristas([_arista((0, 0, 0), (10, 0, 0))], XY, -2)
    assert _lineas(b, XY) == [((0.0, 2.0), (10.0, 2.0))]


def test_simetrico_hace_los_dos_lados_con_el_valor_absoluto():
    lados = da.desfasar_aristas([_arista((0, 0, 0), (10, 0, 0))], XY, -2, simetrico=True)
    assert sorted(y for f in lados for (_, (_, y)) in _lineas(f, XY)) == [-2.0, 2.0]


def test_dos_aristas_en_linea_son_una_sola_cadena():
    resultado = da.desfasar_aristas([_arista((5, 0, 0), (10, 0, 0)), _arista((0, 0, 0), (5, 0, 0))], XY, 2)
    assert len(resultado) == 1 and len(_lineas(resultado[0], XY)) == 2


def test_un_lazo_cerrado_crece_hacia_afuera_sin_importar_su_sentido():
    invertido = [_arista((0, 0, 0), (0, 10, 0)), _arista((0, 10, 0), (10, 10, 0)), _arista((10, 10, 0), (10, 0, 0)),
                 _arista((10, 0, 0), (0, 0, 0))]
    for aristas in (_cuadrado(), invertido):
        (lazo,) = da.desfasar_aristas(aristas, XY, 2)
        puntos = [q for p in proyectar_forma(lazo, XY)[0] if p[0] == "linea" for q in (p[2], p[3])]
        assert min(q[0] for q in puntos) == pytest.approx(-2) and max(q[0] for q in puntos) == pytest.approx(12)
    (hacia_adentro,) = da.desfasar_aristas(_cuadrado(), XY, -2)
    esquinas = {q for seg in _lineas(hacia_adentro, XY) for q in seg}
    assert esquinas == {(2.0, 2.0), (8.0, 2.0), (8.0, 8.0), (2.0, 8.0)}


def test_esquinas_vivas_o_redondas():
    (redondo,) = da.desfasar_aristas(_cuadrado(), XY, 2, esquinas="redondas")
    (vivo,) = da.desfasar_aristas(_cuadrado(), XY, 2, esquinas="vivas")
    assert sum(p[0] == "arco" for p in proyectar_forma(redondo, XY)[0]) == 4
    assert all(p[0] == "linea" for p in proyectar_forma(vivo, XY)[0])


def test_distancia_cero_y_esquinas_desconocidas_fallan_claro():
    with pytest.raises(geo.ErrorGeometria, match="cero"):
        da.desfasar_aristas(_cuadrado(), XY, 0)
    with pytest.raises(geo.ErrorGeometria, match="Esquinas"):
        da.desfasar_aristas(_cuadrado(), XY, 1, esquinas="raras")


def test_plano_de_las_aristas_ajustado_orientado_y_con_errores():
    inclinado = [_arista((0, 0, 0), (10, 0, 0)), _arista((10, 0, 0), (10, 10, 10))]
    plano = da.plano_de_aristas(inclinado)
    assert abs(float(plano.normal @ np.array([1, 0, 0]))) < 1e-9 and plano.normal[np.argmax(abs(plano.normal))] > 0
    assert da.plano_de_aristas(_cuadrado()).normal == pytest.approx([0, 0, 1])
    with pytest.raises(geo.ErrorGeometria, match="línea recta"):
        da.plano_de_aristas([_arista((0, 0, 0), (10, 0, 0))])
    with pytest.raises(geo.ErrorGeometria, match="mismo plano"):
        da.plano_de_aristas([_arista((0, 0, 0), (10, 0, 0)), _arista((10, 0, 0), (10, 10, 0)),
                             _arista((10, 10, 0), (0, 10, 5)), _arista((0, 10, 5), (0, 0, 0))])


# ---------------------------------------------------------------- operación y API
def _ok(r):
    assert r["ok"], r
    return r["result"]


@pytest.fixture
def caja():
    s = api.Sesion()
    _ok(api.llamar(s, "create_box", {"length": 40, "width": 30, "height": 20}))
    return s


def test_desfase_de_la_cara_de_arriba_da_un_boceto_con_un_perfil_del_area_esperada(caja):
    r = _ok(api.llamar(caja, "offset_edges", {"edges": ">Z", "distance": 3}))
    assert r["sketch"]["type"] == "desfase_aristas" and r["profiles"] == 1 and r["curves"] == 8     # 4 rectas + 4 arcos
    info = _ok(api.llamar(caja, "get_sketch", {"sketch": r["sketch"]["id"]}))
    assert info["profiles"][0]["area"] == pytest.approx(40 * 30 + 2 * 3 * (40 + 30) + math.pi * 9, rel=1e-3)
    assert info["plane_frame"]["origin"][2] == pytest.approx(20)


def test_el_desfase_hacia_adentro_y_simetrico(caja):
    adentro = _ok(api.llamar(caja, "offset_edges", {"edges": ">Z", "distance": -3}))
    area = _ok(api.llamar(caja, "get_sketch", {"sketch": adentro["sketch"]["id"]}))["profiles"][0]["area"]
    assert area == pytest.approx((40 - 6) * (30 - 6), rel=1e-3)
    sim = _ok(api.llamar(caja, "offset_edges", {"edges": ">Z", "distance": 3, "symmetric": True, "corners": "sharp"}))
    assert sim["profiles"] == 2


def test_el_boceto_derivado_se_puede_extruir_y_sigue_al_modelo(caja):
    r = _ok(api.llamar(caja, "offset_edges", {"edges": ">Z", "distance": 3, "corners": "sharp"}))
    ext = _ok(api.llamar(caja, "extrude", {"sketch": r["sketch"]["id"], "distance": 5}))
    cuerpo = ext["bodies_created"][0]
    assert cuerpo["volume"] == pytest.approx(46 * 36 * 5, rel=1e-6)
    _ok(api.llamar(caja, "create_parameter", {"name": "ancho", "expression": "3 mm"}))
    _ok(api.llamar(caja, "edit_feature", {"feature": r["sketch"]["id"], "params": {"distancia": "ancho * 2"}}))
    info = _ok(api.llamar(caja, "get_physical_properties", {"bodies": [cuerpo["id"]]}))
    assert info["total"]["volume"] == pytest.approx(52 * 42 * 5, rel=1e-6)


def test_una_arista_sola_pide_el_plano_y_el_paso_fallido_no_queda(caja):
    sin_plano = api.llamar(caja, "offset_edges", {"edges": ["Cuerpo1/E1"], "distance": 2})
    assert sin_plano["ok"] is False and "plano" in sin_plano["mensaje"].lower()
    assert len(_ok(api.llamar(caja, "get_timeline", {}))["steps"]) == 1


def test_desfase_de_curvas_de_un_boceto():
    s = api.Sesion()
    _ok(api.llamar(s, "create_sketch", {"plane": "XY"}))
    linea = _ok(api.llamar(s, "draw_line", {"start_x": 0, "start_y": 0, "end_x": 10, "end_y": 0}))["entities"][0]["id"]
    r = _ok(api.llamar(s, "offset_edges", {"curves": [linea], "distance": 2, "plane": "XY"}))
    assert r["curves"] == 1
    assert api.llamar(s, "offset_edges", {"curves": [999], "distance": 2})["error_kind"] == "ENTITY_NOT_FOUND"
    assert api.llamar(s, "offset_edges", {"distance": 2})["error_kind"] == "INVALID_ARGUMENTS"


def test_el_proyecto_guarda_y_reabre_el_desfase(caja, tmp_path):
    from omnicad.io_archivos import proyecto
    r = _ok(api.llamar(caja, "offset_edges", {"edges": ">Z", "distance": 3}))
    ruta = tmp_path / "pieza.omnicad"
    proyecto.guardar(caja.doc, ruta)
    abierto = proyecto.abrir(ruta)
    assert abierto.estado_final.bocetos[r["sketch"]["id"]].perfiles


# ---------------------------------------------------------------- revisión ponytail (upgrades3)
def _arco(p1, medio, p2):
    from OCP.GC import GC_MakeArcOfCircle
    return BRepBuilderAPI_MakeEdge(GC_MakeArcOfCircle(gp_Pnt(*p1), gp_Pnt(*medio), gp_Pnt(*p2)).Value()).Edge()


def _distancia_al_origen(forma):
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeVertex
    from OCP.BRepExtrema import BRepExtrema_DistShapeShape
    return BRepExtrema_DistShapeShape(BRepBuilderAPI_MakeVertex(gp_Pnt(0, 0, 0)).Vertex(), forma).Value()


def test_dos_cadenas_que_no_se_tocan_dan_dos_desfases():
    """Antes el último Add fallido dejaba el MakeWire «no hecho» y Wire() lanzaba StdFail_NotDone."""
    resultado = da.desfasar_aristas([_arista((0, 0, 0), (10, 0, 0)), _arista((0, 20, 0), (10, 20, 0))], XY, 2)
    assert len(resultado) == 2


def test_un_desfase_que_hace_desaparecer_el_lazo_falla_con_mensaje():
    with pytest.raises(geo.ErrorGeometria, match="desaparecer"):
        da.desfasar_aristas(_cuadrado(), XY, -6)


def test_un_arco_abierto_va_a_la_derecha_de_su_recorrido():
    r = 5 / math.sqrt(2)
    antihorario = _arco((5, 0, 0), (r, r, 0), (0, 5, 0))           # yendo antihorario, la derecha es hacia afuera
    horario = _arco((0, 5, 0), (r, r, 0), (5, 0, 0))
    (afuera,) = da.desfasar_aristas([antihorario], XY, 2)
    (adentro,) = da.desfasar_aristas([horario], XY, 2)
    assert _distancia_al_origen(afuera) == pytest.approx(7, abs=1e-6)
    assert _distancia_al_origen(adentro) == pytest.approx(3, abs=1e-6)


def test_aristas_que_no_son_paralelas_al_plano_fallan_claro(caja):
    with pytest.raises(geo.ErrorGeometria, match="paralelas"):
        da.desfasar_aristas([_arista((0, 0, 0), (0, 0, 10))], XY, 2)        # antes: NaN y un alambre vacío
    r = api.llamar(caja, "offset_edges", {"edges": ">Z", "distance": 2, "plane": "XZ"})   # antes: ok con 0 perfiles
    assert r["ok"] is False and "paralelas" in r["mensaje"]


def test_plane_que_elige_varias_caras_y_curvas_repetidas(caja):
    r = api.llamar(caja, "offset_edges", {"edges": ">Z", "distance": 2, "plane": "|Z"})
    assert r["ok"] is False and r["error_kind"] == "INVALID_ARGUMENTS" and "2 caras" in r["mensaje"]      # arriba y abajo
    s = api.Sesion()
    _ok(api.llamar(s, "create_sketch", {"plane": "XY"}))
    linea = _ok(api.llamar(s, "draw_line", {"start_x": 0, "start_y": 0, "end_x": 10, "end_y": 0}))["entities"][0]["id"]
    assert _ok(api.llamar(s, "offset_edges", {"curves": [linea, linea], "distance": 2, "plane": "XY"}))["curves"] == 1


def test_las_herramientas_que_escriben_no_toman_el_boceto_derivado(caja):
    from omnicad.timeline.ops_modificar import OpDesfaseAristas
    boceto = _ok(api.llamar(caja, "create_sketch", {"plane": "XY"}))["sketch"]["id"]
    _ok(api.llamar(caja, "draw_line", {"start_x": 0, "start_y": 0, "end_x": 10, "end_y": 0}))
    derivado = _ok(api.llamar(caja, "offset_edges", {"edges": ">Z", "distance": 3}))["sketch"]["id"]
    assert _ok(api.llamar(caja, "auto_constrain", {}))["sketch"]["id"] == boceto     # antes: SKETCH_NOT_FOUND
    r = api.llamar(caja, "combine_profiles", {"profiles": "all", "sketch": derivado})
    assert r["ok"] is False and r["error_kind"] == "SKETCH_NOT_FOUND"              # antes: ok sin cambiar nada
    assert not OpDesfaseAristas.boceto.curvas                                     # y ensuciaba el atributo de clase


def test_run_operation_acepta_los_perfiles_del_boceto_derivado(caja):
    derivado = _ok(api.llamar(caja, "offset_edges", {"edges": ">Z", "distance": 3, "corners": "sharp"}))["sketch"]["id"]
    r = _ok(api.llamar(caja, "run_operation", {"type": "extrusion", "params": {
        "perfiles": [{"sketch": derivado, "profile": 0}], "distancia": "5 mm"}}))
    assert r["status"] == "ok"

# -*- coding: utf-8 -*-
"""F10 y SC13: comparar dos cuerpos, con resultados contra cuentas a mano."""
import numpy as np
import pytest

from omnicad import api
from omnicad.nucleo import comparar_malla as cm
from omnicad.nucleo import geometria as geo
from omnicad.nucleo import malla as ml
from omnicad.nucleo import malla_seccion as ms


def _placa(dx=0.0):
    base = geo.caja(80, 50, 8, (-40, -25, 0))
    return geo.booleano(base, geo.cilindro(5, 20, (10 + dx, 0, -5)), "cortar")


def _malla(forma, desviacion=0.02):
    return ml.desde_brep(forma, refinamiento="personalizado", desviacion=desviacion, angulo=15)


def _caja(x=0.0, lado=10.0):
    return ml.desde_brep(geo.caja(lado, lado, lado, (x, 0, 0)), refinamiento="bajo")


def test_una_pieza_contra_su_propia_malla_da_casi_cero():
    forma = _placa()
    assert geo.es_valida(forma)
    r = cm.comparar(forma, _malla(forma), tolerancia=0.1)
    assert r["max_deviation"] < 0.02                                      # la cuerda del teselado, nada más
    assert r["within_tolerance_percent"] == 100.0
    assert r["zones"] == [] and r["zones_total"] == 0
    assert r["iou"] > 0.999
    assert r["volume_a"] == pytest.approx(80 * 50 * 8 - np.pi * 25 * 8, rel=1e-6)


def test_un_agujero_corrido_1_mm_marca_esa_zona_y_nada_mas():
    r = cm.comparar(_placa(1.0), _malla(_placa()), tolerancia=0.1)
    assert r["max_deviation"] == pytest.approx(1.0, abs=0.03)
    assert r["zones_total"] == 1
    z = r["zones"][0]
    assert np.array(z["bbox_min"])[:2] == pytest.approx([5.0, -5.0], abs=0.05)
    assert np.array(z["bbox_max"])[:2] == pytest.approx([16.0, 5.0], abs=0.05)
    assert z["excess_mm"] == pytest.approx(1.0, abs=0.03) and z["missing_mm"] == pytest.approx(1.0, abs=0.03)
    assert r["within_tolerance_percent"] < 100


def test_el_signo_dice_si_sobra_o_falta_material():
    chica, grande = _caja(lado=10.0), _caja(lado=12.0)
    assert cm.comparar(grande, chica, tolerancia=0.1)["zones"][0]["excess_mm"] == pytest.approx(2 * 3 ** 0.5, abs=0.01)  # esquina contra esquina
    assert cm.comparar(chica, grande, tolerancia=0.1)["zones"][0]["missing_mm"] == pytest.approx(2 * 3 ** 0.5, abs=0.01)


def test_solapamiento_contra_la_cuenta_a_mano():
    assert cm.solapamiento(_caja(), _caja(5.0)) == pytest.approx(1 / 3, abs=1e-6)
    invertida = ml.Malla(_caja().vertices, _caja().caras[:, ::-1])
    assert cm.solapamiento(invertida, _caja(5.0)) == pytest.approx(1 / 3, abs=1e-6)
    assert cm.solapamiento(_caja(), _caja()) == pytest.approx(1.0)
    assert cm.solapamiento(_caja(), _caja(50.0)) == 0.0


def test_dos_corridas_dan_lo_mismo():
    a, b = _placa(0.5), _malla(_placa())
    assert cm.comparar(a, b) == cm.comparar(a, b)


def test_mapa_pinta_con_signo_y_con_la_escala():
    v, n, valores = cm.mapa(_malla(_placa(1.0)), _malla(_placa()), tolerancia=0.1)
    assert len(v) == len(n) == len(valores) and len(v) % 3 == 0
    assert valores.max() == pytest.approx(1.0, abs=0.05) and valores.min() == pytest.approx(-1.0, abs=0.05)
    c = cm.colores(np.array([0.0, 0.1, 0.5, -0.5]), 0.1)
    assert c[0] == pytest.approx(cm.ESCALA[1]) and c[1] == pytest.approx(cm.ESCALA[2])
    assert c[2] == pytest.approx(cm.ESCALA[3]) and c[3] == pytest.approx(cm.ESCALA[0])


@pytest.mark.parametrize("malla, mensaje", [(ml.Malla(np.zeros((0, 3)), np.zeros((0, 3), int)), "vacía"),
                                            (ml.Malla(np.zeros((3, 3)), [[0, 1, 2]]), "degenerados")])
def test_mallas_sin_superficie_dan_un_mensaje_claro(malla, mensaje):
    with pytest.raises(geo.ErrorGeometria, match=mensaje):
        cm.comparar(malla, _caja())


def test_una_malla_enorme_se_rechaza_con_un_mensaje_claro(monkeypatch):
    monkeypatch.setattr(cm, "TOPE_TRIANGULOS", 5)
    with pytest.raises(geo.ErrorGeometria, match="reducila"):
        cm.comparar(_caja(), _caja())


def test_una_malla_abierta_se_compara_sin_solapamiento():
    abierta = ml.Malla(_caja().vertices, _caja().caras[2:])
    r = cm.comparar(abierta, _caja())
    assert r["closed"] is False and r["iou"] is None
    assert r["a_to_b"]["max"] < 1e-9 and r["b_to_a"]["max"] == pytest.approx(5.0, abs=0.2)   # el centro de la tapa que falta


@pytest.mark.parametrize("args", [{"tolerancia": 0}, {"tolerancia": float("nan")}, {"muestras": 10}])
def test_parametros_invalidos(args):
    with pytest.raises(geo.ErrorGeometria):
        cm.comparar(_caja(), _caja(), **args)


def test_un_corte_con_pocos_puntos_no_se_vuelve_circulo_ni_arco():
    cuadrado = np.array([[0.0, 0.0], [10.0, 0.0], [10.0, 10.0], [0.0, 10.0]])
    curvas = ms.ajustar(cuadrado, True, "lineas_arcos", desviacion=0.1)
    assert [c["tipo"] for c in curvas] == ["linea"] * 4
    circulo = np.c_[10 * np.cos(np.linspace(0, 2 * np.pi, 72, endpoint=False)), 10 * np.sin(np.linspace(0, 2 * np.pi, 72, endpoint=False))]
    assert [c["tipo"] for c in ms.ajustar(circulo, True, "lineas_arcos", desviacion=0.1)] == ["circulo"]


def _sesion():
    s = api.Sesion()
    for n, a in (("create_box", dict(length=20, width=20, height=20)), ("tessellate", dict(bodies=["op1.c1"], keep_original=True))):
        r = api.llamar(s, n, a)
        assert r["ok"], r
    return s


def test_compare_to_mesh_devuelve_el_mismo_juez_por_la_api():
    s = _sesion()
    cuerpos = list(s.doc.estado_final.cuerpos)
    r = api.llamar(s, "compare_to_mesh", {"body": cuerpos[0], "reference": cuerpos[1]})
    assert r["ok"], r
    x = r["result"]
    assert x["max_deviation"] < 0.01 and x["within_tolerance_percent"] == 100.0 and x["overlap_iou"] > 0.999
    assert x["volume_body"] == pytest.approx(8000.0)


def test_compare_to_mesh_rechaza_el_mismo_cuerpo_y_una_tolerancia_mala():
    s = _sesion()
    c = list(s.doc.estado_final.cuerpos)
    assert api.llamar(s, "compare_to_mesh", {"body": c[0], "reference": c[0]})["error_kind"] == "INVALID_ARGUMENTS"
    assert api.llamar(s, "compare_to_mesh", {"body": c[0], "reference": c[1], "tolerance": 0})["error_kind"] == "INVALID_ARGUMENTS"


def test_show_deviation_map_lo_dibuja_y_se_deshace():
    s = _sesion()
    c = list(s.doc.estado_final.cuerpos)
    r = api.llamar(s, "show_deviation_map", {"body": c[0], "reference": c[1]})
    assert r["ok"], r
    assert r["result"]["analysis"] == "Desviación1" and "Desviación1" in s.doc.analisis
    assert api.llamar(s, "get_viewport_image", {"width": 200, "height": 150})["ok"]
    assert api.llamar(s, "undo", {})["ok"]
    assert "Desviación1" not in s.doc.analisis


def test_las_tandas_de_candidatos_cubren_cada_punto_una_vez(monkeypatch):
    """Lejos de la superficie cada punto toca miles de triángulos: 13 millones juntos agotaron la memoria."""
    from scipy.spatial import cKDTree
    P = np.random.default_rng(1).random((3000, 3))
    arbol = cKDTree(P)
    monkeypatch.setattr(cm, "_CANDIDATOS_TANDA", 2000)
    vistos = np.zeros(len(P), int)
    for tanda in cm._tramos(arbol, P, np.full(len(P), 0.15)):
        assert len(tanda["candidatos"]) < 2400 and len(tanda["fila"]) == len(tanda["candidatos"])
        vistos[tanda["indices"]] += 1
        k = len(tanda["indices"]) // 2
        assert sorted(tanda["candidatos"][tanda["fila"] == k]) == sorted(arbol.query_ball_point(P[tanda["indices"][k]], 0.15))
    assert (vistos == 1).all()


def test_zonas_con_puntos_amontonados_no_explotan():
    """Los vértices se juntan en los detalles finos: los pares de puntos vecinos llegaron a 32 millones."""
    P = np.r_[np.random.default_rng(1).random((200000, 3)), np.array([[50.0, 0, 0], [50.5, 0, 0]])]
    z = cm.zonas(P, np.ones(len(P)), 0.1, 1.0)
    assert len(z) == 2 and z[1]["area"] == pytest.approx(2.0) and z[0]["area"] == pytest.approx(200000.0)

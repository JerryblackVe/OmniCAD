# -*- coding: utf-8 -*-
"""F11: medir formas sobre una malla, con medidas conocidas de antemano."""
import math

import numpy as np
import pytest

from omnicad import api
from omnicad.nucleo import formas_malla as fm
from omnicad.nucleo import geometria as geo
from omnicad.nucleo import malla as ml


def _m(forma, desviacion=0.02):
    return ml.desde_brep(forma, refinamiento="personalizado", desviacion=desviacion, angulo=15)


def _resumen(ficha):
    return {k: v for k, v in ficha["summary"].items() if v}


def test_caja_seis_planos_y_tres_simetrias():
    f = fm.analizar(_m(geo.caja(60, 40, 20, (0, 0, 0))))
    assert _resumen(f) == {"plane": 6} and f["unclassified_percent"] == 0
    assert sorted(x["area"] for x in f["shapes"]) == pytest.approx([800, 800, 1200, 1200, 2400, 2400])
    assert len(f["symmetries"]) == 3
    assert all(len(x["neighbors"]) == 4 for x in f["shapes"])


def test_cilindro_con_su_radio_y_su_eje():
    f = fm.analizar(_m(geo.cilindro(15, 50, (3, 4, 5))))
    assert _resumen(f) == {"plane": 2, "cylinder": 1}
    c = next(x for x in f["shapes"] if x["type"] == "cylinder")
    assert c["radius"] == pytest.approx(15, abs=1e-3) and c["height"] == pytest.approx(50, abs=1e-3)
    assert c["arc_degrees"] == 360 and c["concave"] is False
    assert abs(c["axis"][2]) == pytest.approx(1, abs=1e-6)
    assert np.array(c["axis_point"])[:2] == pytest.approx([3, 4], abs=1e-3)
    assert f["revolution_axis"]["share"] == pytest.approx(1)


def test_esfera_y_toro():
    f = fm.analizar(_m(geo.esfera(12, (1, 2, 3))))
    assert _resumen(f) == {"sphere": 1}
    assert f["shapes"][0]["radius"] == pytest.approx(12, abs=1e-3)
    assert np.array(f["shapes"][0]["center"]) == pytest.approx([1, 2, 3], abs=1e-3)


def test_el_porton_del_toro_no_descarta_un_toro_real():
    """El toro se afina recién cuando el ajuste algebraico ya está cerca (igual que el cono); un toro de verdad
    entra en esa ventana y queda reconocido con sus radios."""
    f = fm.analizar(_m(geo.toroide(12, 4)))
    assert _resumen(f) == {"torus": 1}
    assert f["shapes"][0]["major_radius"] == pytest.approx(12, abs=1e-3)
    assert f["shapes"][0]["minor_radius"] == pytest.approx(4, abs=1e-3)


def test_agujero_ciego_pasante_y_patron():
    base = geo.caja(90, 70, 10, (-45, -35, 0))
    for x in (-30, -10, 10, 30):
        base = geo.booleano(base, geo.cilindro(3, 20, (x, 0, -5)), "cortar")
    base = geo.booleano(base, geo.cilindro(5, 8, (0, 25, 5)), "cortar")
    f = fm.analizar(_m(base))
    pasantes = [h for h in f["holes"] if h["through"]]
    ciegos = [h for h in f["holes"] if not h["through"]]
    assert len(pasantes) == 4 and all(h["diameter"] == pytest.approx(6, abs=1e-3) for h in pasantes)
    assert len(ciegos) == 1 and ciegos[0]["diameter"] == pytest.approx(10, abs=1e-3)
    assert ciegos[0]["depth"] == pytest.approx(5, abs=1e-3)
    p = next(x for x in f["patterns"] if x["type"] == "rectangular_pattern")
    assert p["count"] == 4 and p["directions"][0]["step"] == pytest.approx(20, abs=1e-3)


def test_cuatro_puntos_de_un_rectangulo_no_son_un_cilindro():
    """Dos bordes de un cilindro caben en una esfera y dos cuerdas caben en un círculo: se comprobó en el banco."""
    f = fm.analizar(_m(geo.cilindro(15, 50, (0, 0, 0)), 0.5))
    assert f["summary"]["sphere"] == 0 and f["summary"]["cylinder"] == 1


def test_dos_corridas_dan_la_misma_ficha():
    m = _m(geo.booleano(geo.caja(40, 40, 10, (0, 0, 0)), geo.cilindro(5, 20, (20, 20, -5)), "cortar"))
    a, b = fm.analizar(m), fm.analizar(m)
    assert a == b


def test_mallas_ajenas_dan_mensajes_claros():
    with pytest.raises(geo.ErrorGeometria, match="vacía"):
        fm.analizar(ml.Malla(np.zeros((0, 3)), np.zeros((0, 3), int)))


def test_una_malla_abierta_tambien_se_mide():
    m = _m(geo.caja(20, 20, 20, (0, 0, 0)))
    abierta = ml.Malla(m.vertices, m.caras[2:])
    f = fm.analizar(abierta)
    assert f["quality"]["closed"] is False and f["summary"]["plane"] == 5      # los dos triángulos sacados eran una tapa


def test_ruido_de_escaneo_con_tolerancia_recupera_el_radio():
    m = ml.refinar_triangulos(_m(geo.cilindro(20, 40, (0, 0, 0)), 0.05), longitud_maxima=4.0)
    rng = np.random.default_rng(1)
    f = fm.analizar(ml.Malla(m.vertices + rng.normal(0, 0.01, m.vertices.shape), m.caras), tolerancia=0.05)
    assert _resumen(f) == {"plane": 2, "cylinder": 1} and f["quality"]["origin"] == "scan"
    assert next(x for x in f["shapes"] if x["type"] == "cylinder")["radius"] == pytest.approx(20, abs=0.02)


def _afinar_numerica(tipo, p0, a0, b, c, P):
    """La ruta vieja de _afinar: el mismo ajuste con la derivada numérica de scipy."""
    from scipy.optimize import least_squares
    u, v = fm._base(a0)

    def forma(x):
        return fm._Forma(tipo, p0 + x[2] * u + x[3] * v, fm._unit(a0 + x[0] * u + x[1] * v), x[4], x[5])

    x = least_squares(lambda x: forma(x).distancia(P), [0.0, 0.0, 0.0, 0.0, b, c], max_nfev=30).x
    return forma(x)


def test_afinar_con_derivada_exacta_coincide_con_la_numerica():
    """El ajuste fino de _afinar con la jacobiana exacta cae en la misma forma que con diferencias finitas."""
    rng = np.random.default_rng(7)
    casos = [("torus", (20.0, 5.0)), ("cone", (10.0, 0.3))]
    for tipo, (b, c) in casos:
        if tipo == "torus":
            th, ph = rng.uniform(0, 2 * np.pi, (2, 400))
            P = np.c_[(b + c * np.cos(ph)) * np.cos(th), (b + c * np.cos(ph)) * np.sin(th), c * np.sin(ph)]
        else:
            th, z = rng.uniform(0, 2 * np.pi, 400), rng.uniform(0, 30, 400)
            r = b + c * z
            P = np.c_[r * np.cos(th), r * np.sin(th), z]
        P += rng.normal(0, 0.01, P.shape)
        p0, a0 = np.array([0.3, -0.2, 0.1]), fm._unit(np.array([0.05, -0.04, 1.0]))
        exacta = fm._afinar(tipo, p0, a0, b, c, P)
        numerica = _afinar_numerica(tipo, p0, a0, b, c, P)
        assert np.abs(exacta.distancia(P) - numerica.distancia(P)).max() < 0.1


def test_superficie_libre_queda_sin_clasificar_y_no_inventa_formas():
    u, v = np.meshgrid(np.linspace(0, 40, 41), np.linspace(0, 40, 41))
    z = 3 * np.sin(u / 5) * np.cos(v / 7) + 0.5 * np.sin(u * v / 60)
    V = np.c_[u.ravel(), v.ravel(), z.ravel()]
    i = np.arange(40 * 41).reshape(40, 41)[:, :40].ravel()
    C = np.r_[np.c_[i, i + 1, i + 41], np.c_[i + 1, i + 42, i + 41]]
    f = fm.analizar(ml.Malla(V, C), tolerancia=0.01)
    assert f["unclassified_percent"] > 50


def test_analyze_mesh_features_por_la_api():
    s = api.Sesion()
    assert api.llamar(s, "create_cylinder", {"diameter": 30, "height": 40})["ok"]
    assert api.llamar(s, "tessellate", {"bodies": ["op1.c1"]})["ok"]
    malla = list(s.doc.estado_final.cuerpos)[-1]
    r = api.llamar(s, "analyze_mesh_features", {"body": malla})
    assert r["ok"], r
    x = r["result"]
    assert x["summary"]["cylinder"] == 1 and x["shapes"][0]["fit_error"] >= 0
    import json
    assert json.dumps(x)                                          # ficha JSON estable: sin arrays de numpy
    assert api.llamar(s, "analyze_mesh_features", {"body": malla, "tolerance": -1})["error_kind"] == "INVALID_ARGUMENTS"


def test_rectangular_arco_completo_de_un_cilindro_hueco():
    tubo = geo.booleano(geo.cilindro(20, 30, (0, 0, 0)), geo.cilindro(12, 40, (0, 0, -5)), "cortar")
    f = fm.analizar(_m(tubo))
    radios = sorted(x["radius"] for x in f["shapes"] if x["type"] == "cylinder")
    assert radios == pytest.approx([12, 20], abs=1e-3)
    hueco = next(x for x in f["shapes"] if x["type"] == "cylinder" and x["radius"] < 15)
    assert hueco["concave"] is True and hueco["arc_degrees"] == 360
    assert math.isclose(f["holes"][0]["diameter"], 24, abs_tol=1e-3)


def test_ruido_se_detecta_sin_medir_todo():
    m = ml.refinar_triangulos(_m(geo.caja(40, 30, 20, (0, 0, 0))), longitud_maxima=4.0)
    assert fm.con_ruido(m) is False
    rng = np.random.default_rng(1)
    assert fm.con_ruido(ml.Malla(m.vertices + rng.normal(0, 0.01, m.vertices.shape), m.caras)) is True

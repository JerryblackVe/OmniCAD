"""H-56: en perspectiva, el mapa de entorno calcula la dirección de vista por vértice (de cada punto a la cámara), así
una cara plana refleja más de un color, como el cromo de Fusion. En ortográfica la dirección es una sola, como antes."""
import numpy as np
from _tiempo import mejor_tiempo

from omnicad.nucleo import analisis as an


def _cara_plana(lado=100.0, n=21):
    u = np.linspace(-lado / 2, lado / 2, n)
    puntos = np.array([(x, y, 0.0) for x in u for y in u])
    return puntos, np.tile((0.0, 0.0, 1.0), (len(puntos), 1))


def _distintos(colores):
    return len(np.unique(np.round(colores, 4), axis=0))


def test_cara_plana_en_perspectiva_refleja_varios_colores():
    puntos, normales = _cara_plana()
    vista = np.array([0.0, -0.6, 0.8])
    for entorno in (None, "plaza"):
        colores = an.colores_mapa_entorno(normales, vista, entorno=entorno, puntos=puntos, ojo=200 * vista)
        assert colores.shape == normales.shape and colores.dtype == np.float32
        assert _distintos(colores) > 1, entorno
        # En ortográfica (sin ojo) la cara plana sigue siendo de un solo color.
        assert _distintos(an.colores_mapa_entorno(normales, vista, entorno=entorno)) == 1


def test_esfera_con_la_camara_muy_lejos_da_lo_mismo_que_la_ortografica():
    rng = np.random.default_rng(1)
    normales = an._normalizar_filas(rng.normal(size=(5000, 3)))
    puntos = 10 * normales
    vista = np.array([0.3, -0.9, 0.3]) / np.linalg.norm([0.3, -0.9, 0.3])
    lejos = an.colores_mapa_entorno(normales, vista, puntos=puntos, ojo=1e9 * vista)
    assert np.allclose(lejos, an.colores_mapa_entorno(normales, vista), atol=1e-4)
    sin_reflejo = an.colores_mapa_entorno(normales, vista, puntos=puntos, ojo=1e9 * vista, reflejo=False)
    assert np.allclose(sin_reflejo, an.colores_mapa_entorno(normales, vista, reflejo=False), atol=1e-6)


def test_el_render_de_la_api_le_pasa_la_camara():
    from omnicad import api
    from omnicad.api import herramientas_inspeccion as hi
    from omnicad.nucleo import render_cpu as rc
    s = api.Sesion()
    assert api.llamar(s, "create_box", {"length": 100, "width": 100, "height": 1})["ok"]
    assert api.llamar(s, "manage_analysis", {"action": "add", "type": "environment_map"})["ok"]
    for orto, esperados in ((False, lambda k: k > 1), (True, lambda k: k == 1)):
        cam = rc.camara(np.eye(3), (30.0, 10.0, 0.0), 200.0, ortografica=orto)      # de arriba, a 200 mm, corrida
        objetos, _, _ = hi._con_analisis(s, hi._objetos_render(s, hi._cuerpos(s, None), cam), cam, 600, None)
        o = objetos[0]
        arriba = o["n"][:, 2] > 0.99                                                  # la cara plana de arriba
        assert esperados(_distintos(o["colores"][arriba])), orto


def test_cien_mil_vertices_en_menos_de_dos_decimas():
    rng = np.random.default_rng(2)
    normales = rng.normal(size=(100_000, 3))
    puntos = rng.uniform(-50, 50, size=(100_000, 3))
    vista = np.array([0.0, -1.0, 0.0])
    segundos, _ = mejor_tiempo(lambda: an.colores_mapa_entorno(normales, vista, puntos=puntos, ojo=200 * vista), 0.2)
    print(f"100 000 vértices: {segundos:.3f} s")
    assert segundos < 0.2

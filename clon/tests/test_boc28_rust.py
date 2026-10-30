"""BOC-28: la detección de perfiles con el módulo Rust (`_rs.arreglo_planar`) da lo mismo que el Splitter de OpenCascade.

Equivalencia: mismo número de perfiles, mismas áreas y centroides (≤ 1e-6), misma firma, y la cara exacta (que se arma
al pedirla) es válida y tiene la misma área. Sin el módulo compilado la referencia sigue andando (respaldo)."""
import math
import time

import numpy as np
import pytest
from scipy.spatial import cKDTree

from omnicad import api, nativo
from omnicad.nucleo import fuentes, perfiles
from omnicad.nucleo import geometria as geo

pytestmark = pytest.mark.skipif(nativo.disponible() is None, reason="Extensión Rust opcional no compilada en este entorno.")
PLANO = geo.Plano("XY")


def _linea(i, a, b):
    return ("linea", i, a, b)


def _rect(i, x0, y0, x1, y1):
    return [_linea(i, (x0, y0), (x1, y0)), _linea(i, (x1, y0), (x1, y1)), _linea(i, (x1, y1), (x0, y1)), _linea(i, (x0, y1), (x0, y0))]


def _bezier(i, p0, p1, p2):
    return ("spline", i, (p0, p1, p2), (0.0, 0.0, 0.0, 1.0, 1.0, 1.0), 2, None)


def _comparar(g, esperados=None, tol=1e-6):
    ref = perfiles._detectar_occ(g, PLANO)
    rs = perfiles._detectar_rust(g, PLANO)
    assert rs is not None, "Rust no resolvió un caso común"
    assert len(rs) == len(ref)
    if esperados is not None:
        assert len(rs) == esperados
    if not ref:
        return rs
    clave = lambda ps: np.array([[p.centroide_uv[0], p.centroide_uv[1], p.area] for p in ps])  # noqa: E731
    dist, idx = cKDTree(clave(ref)).query(clave(rs))
    assert dist.max() < tol, dist.max()
    assert len(set(idx.tolist())) == len(ref)                                      # emparejados uno a uno
    for k, p in zip(idx, rs, strict=True):
        assert p.firma == ref[k].firma
        (x0, y0, _z0), (x1, y1, _z1) = geo.caja_envolvente(ref[k].cara)               # caja envolvente sin armar la cara
        assert p.caja_uv == pytest.approx((x0, y0, x1, y1), abs=max(tol, 1e-6))
    for p in rs[:50]:                                                              # la cara exacta, armada a pedido
        assert geo.es_valida(p.cara)
        assert geo.area(p.cara) == pytest.approx(p.area, abs=1e-6)
    return rs


def test_rectangulo_con_circulo_adentro_da_anillo_y_disco():
    rs = _comparar(_rect(1, -10, -10, 10, 10) + [("circulo", 2, (0.0, 0.0), 4.0)], 2)
    assert sorted(p.area for p in rs) == pytest.approx(sorted([math.pi * 16, 400 - math.pi * 16]), abs=1e-6)
    assert {p.firma for p in rs} == {frozenset({2}), frozenset({1, 2})}


def test_circulo_cortado_por_una_recta():
    _comparar([("circulo", 1, (0.0, 0.0), 10.0), _linea(2, (-20, 4), (20, 4))], 2)


def test_rectangulo_con_diagonales_y_circulo():
    g = _rect(1, 0, 0, 10, 10) + [_linea(2, (0, 0), (10, 10)), _linea(3, (0, 10), (10, 0)), ("circulo", 4, (5.0, 5.0), 3.0)]
    _comparar(g)


def test_rectangulos_anidados_con_colgante_y_componentes_sueltas():
    g = (_rect(1, -20, -20, 20, 20) + _rect(2, -10, -10, 10, 10) + _rect(3, -3, -3, 3, 3) + [_linea(4, (0, 10), (0, 5))]
         + _rect(5, 30, 0, 40, 10) + [_linea(6, (35, 3), (35, 8))] + [("circulo", 7, (35.0, 5.0), 1.0)] + [_linea(8, (31, 1), (33, 1))])
    rs = _comparar(g)
    assert any(p.firma >= {6} for p in rs)             # el colgante suelto dentro de una región entra en su firma
    assert any(p.firma >= {8} for p in rs)             # y también un segmento aislado (componente sin ciclos)


def test_dos_circulos_que_se_cruzan_y_un_arco():
    g = [("circulo", 1, (0.0, 0.0), 5.0), ("circulo", 2, (6.0, 1.0), 4.0), ("arco", 3, (3.0, 0.0), 8.0, 0.2, 2.9)]
    _comparar(g)


def test_arco_tangente_en_el_extremo_y_t_en_borde():
    """Un empalme (arco tangente a dos rectas en sus extremos) y una recta que termina sobre el borde de un círculo."""
    g = [_linea(1, (0, 0), (8, 0)), ("arco", 2, (8.0, 2.0), 2.0, -math.pi / 2, 0.0), _linea(3, (10, 2), (10, 10)),
         _linea(4, (10, 10), (0, 10)), _linea(5, (0, 10), (0, 0)), ("circulo", 6, (4.0, 5.0), 2.0), _linea(7, (4, 7), (4, 10)),
         _linea(8, (4, 3), (4, 0.0))]
    _comparar(g)


def test_spline_que_cruza_recta_y_circulo():
    g = [_bezier(1, (0, 0), (5, 12), (10, 0)), _linea(2, (-2, 3), (12, 3)), ("circulo", 3, (5.0, 2.0), 2.5),
         _bezier(4, (0, 8), (5, -4), (10, 8))]
    _comparar(g)


def test_extremos_casi_unidos_se_delegan_al_splitter():
    """Esquinas separadas 5e-6 mm (menos que la tolerancia 1e-4): el Splitter las cierra. Rust funde solo a 1e-8, así que
    ante un extremo libre a menos de 1e-4 de otra curva declina y rige la referencia (que da el perfil)."""
    g = [_linea(1, (0, 0), (10, 0)), _linea(2, (10, 5e-6), (10, 10)), _linea(3, (10 + 5e-6, 10), (0, 10)), _linea(4, (0, 10 - 5e-6), (0, 0))]
    assert perfiles._detectar_rust(g, PLANO) is None
    assert len(perfiles.detectar(g, PLANO)) == 1


def test_extremos_unidos_a_1e_9_se_resuelven_en_rust():
    """Esquinas separadas 1e-9 (residuo típico del solver): se funden y el perfil sale del arreglo."""
    g = [_linea(1, (0, 0), (10, 0)), _linea(2, (10, 1e-9), (10, 10)), _linea(3, (10 + 1e-9, 10), (0, 10)), _linea(4, (0, 10 - 1e-9), (0, 0))]
    _comparar(g, 1)


def test_polilinea_abierta_no_da_perfiles():
    assert _comparar([_linea(1, (0, 0), (10, 0)), _linea(1, (10, 0), (10, 10))], 0) == []


def test_curvas_tangentes_se_resuelven_o_se_delegan():
    """Una recta tangente a un círculo: Rust puede resolverla o declinar (None); nunca dar un resultado distinto."""
    g = [("circulo", 1, (0.0, 0.0), 5.0), _linea(2, (-10, 5), (10, 5)), _linea(3, (-10, 0), (10, 0))]
    rs = perfiles._detectar_rust(g, PLANO)
    if rs is not None:
        assert len(rs) == len(perfiles._detectar_occ(g, PLANO))


def test_curvas_superpuestas_se_delegan_al_respaldo():
    assert perfiles._detectar_rust([_linea(1, (0, 0), (10, 0)), _linea(2, (5, 0), (15, 0)), _linea(3, (0, 0), (0, 5))], PLANO) is None
    assert perfiles._detectar_rust([("circulo", 1, (0.0, 0.0), 3.0), ("circulo", 2, (0.0, 0.0), 3.0)], PLANO) is None


def test_elipse_y_sin_rust_usan_la_referencia(monkeypatch):
    g = _rect(1, -5, -5, 5, 5) + [("elipse", 2, (0.0, 0.0), 3.0, 2.0, 0.3)]
    assert perfiles._detectar_rust(g, PLANO) is None
    assert len(perfiles.detectar(g, PLANO)) == 2
    monkeypatch.setenv("OMNICAD_SIN_RUST", "1")
    h = _rect(1, -5, -5, 5, 5) + [("circulo", 2, (0.0, 0.0), 3.0)]
    assert perfiles._detectar_rust(h, PLANO) is None
    assert [round(p.area, 6) for p in perfiles.detectar(h, PLANO)] == sorted(round(p.area, 6) for p in perfiles._detectar_occ(h, PLANO))


def test_texto_con_huecos_y_letras_que_se_tocan():
    familias = {f.lower() for f in fuentes.familias()}
    fuente = "Arial" if "arial" in familias else "OmniCAD Trazo SHX"
    prims = fuentes.contornos_texto("BOAg8&", fuente, 10)
    g = [(p[0], 1, *p[2:]) for p in prims]
    rs = _comparar(g)
    assert len(rs) >= 8                                  # letras y huecos
    g2 = [(p[0], 1, *p[2:]) for p in fuentes.contornos_texto("WWWW", fuente, 10, espaciado=-3)]
    _comparar(g2)                                        # letras superpuestas


def test_rectas_al_azar():
    rng = np.random.default_rng(28)
    pts = rng.uniform(-10, 10, (40, 4))
    _comparar([_linea(i + 1, (a, b), (c, d)) for i, (a, b, c, d) in enumerate(pts)] + _rect(99, -12, -12, 12, 12))


def _texto_largo_sobre_circulo():
    s = api.Sesion()
    api.llamar(s, "create_sketch", {"plane": "XY", "name": "B"})
    c = api.llamar(s, "draw_circle", {"radius": 20})["result"]["entities"][0]["id"]
    return s, c


def test_200_W_sobre_un_circulo_equivale_a_la_referencia_y_es_rapido(monkeypatch):
    """El caso de la fila BOC-28: 14,8 mil perfiles. Antes ~3,95 s (Splitter); con Rust la meta es < 1,5 s y el tope de
    la prueba es holgado (3 s) para no fallar por carga de la PC."""
    capturado = {}
    original = perfiles._detectar

    def medir(g, plano, tol=1e-4):
        t = time.perf_counter()
        r = original(g, plano, tol)
        capturado.update(g=list(g), t=time.perf_counter() - t, r=r)
        return r

    monkeypatch.setattr(perfiles, "_detectar", medir)
    monkeypatch.setattr(perfiles, "_CACHE_PERFILES", {})    # otro test con las mismas 200 «W» la dejó llena: no mediríamos nada
    s, c = _texto_largo_sobre_circulo()
    r = api.llamar(s, "add_text", {"text": "W" * 200, "height": 5, "path_entity": c, "fit_path": True})["result"]
    assert 14000 < r["profiles"] < 15500
    assert capturado["t"] < 3.0, capturado["t"]
    ref = perfiles._detectar_occ(capturado["g"], PLANO)
    clave = lambda ps: np.array([[p.centroide_uv[0], p.centroide_uv[1], p.area] for p in ps])  # noqa: E731
    rs = capturado["r"]
    dist, _ = cKDTree(clave(ref)).query(clave(rs))
    # Las letras se pisan y hay triples puntos casi concurrentes (< 1e-4 mm): ahí el Splitter funde con su tolerancia y
    # el arreglo no (7 regiones de ≲ 6e-4 mm² de 14 768). Todo lo demás coincide a ≤ 1e-6.
    assert abs(len(rs) - len(ref)) <= 5 and (dist > 1e-6).sum() <= 60 and dist.max() < 0.1
    assert abs(sum(p.area for p in rs) - sum(p.area for p in ref)) < 1e-3
    assert {p.firma for p in rs} == {p.firma for p in ref}

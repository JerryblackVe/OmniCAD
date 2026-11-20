# -*- coding: utf-8 -*-
"""P-183: el relleno de un texto cursivo largo (`detectar_boceto` + `sin_huecos`) era lento: las horquillas de la fuente
mandaban letras enteras al Splitter, cada pieza se armaba y se mallaba para hallar un punto adentro, y al tipear se
volvían a unir y clasificar todas las letras. Cada vía rápida da lo mismo que el camino de siempre."""
import pytest
from OCP.BRepClass import BRepClass_FaceClassifier
from OCP.TopAbs import TopAbs_IN
from OCP.gp import gp_Pnt

from omnicad import api, nativo
from omnicad.nucleo import fuentes, geometria as geo, perfiles as pf
from omnicad.restricciones.boceto import Boceto

PLANO = geo.Plano("XY")
hay_dejavu = pytest.mark.skipif(fuentes.buscar_fuente("DejaVu Sans") is None, reason="No hay DejaVu Sans instalada")


def _rs_nuevo():
    """El módulo Rust con el punto interior (P-183); uno viejo sigue andando por el camino de siempre."""
    rs = nativo.disponible()
    return rs is not None and len(rs.arreglo_planar(*pf._datos_rust([("linea", 1, (0, 0), (1, 0))])[1], 1e-4)) > 11


rust_nuevo = pytest.mark.skipif(not _rs_nuevo(), reason="Módulo Rust ausente o viejo: recompilar clon/rust (maturin).")


def _horquilla(fin):
    """Una cuadrática que vuelve sobre sí (de una «a» cursiva de Ananda Black) cerrada con dos rectas."""
    a, b = (21.39112175, 4.57527999), (21.28206286, 4.34158237)
    return [("spline", 1, (a, (21.39631503, 4.59085983), b), (0.0, 0.0, 0.0, 1.0, 1.0, 1.0), 2, None),
            ("linea", 1, b, fin), ("linea", 1, fin, a)]


def _limpiar_caches():
    for c in (pf._CACHE_PERFILES, pf._CACHE_ISLAS, pf._CACHE_TEXTO, pf._CACHE_CAPAS, pf._CACHE_UNION):
        c.clear()


@rust_nuevo
@pytest.mark.parametrize("fin", [(23.0, 3.0), (20.0, 3.0), (21.3, 4.0)])
def test_una_horquilla_de_conica_no_es_un_autocruce(fin):
    g = _horquilla(fin)
    rs, ref = pf._detectar_rust(g, PLANO), pf._detectar_occ(g, PLANO)
    assert rs is not None                                  # antes: «curva que se corta a sí misma» y Splitter
    assert sorted(p.area for p in rs) == pytest.approx(sorted(p.area for p in ref), abs=1e-6)


def test_un_bucle_cubico_de_verdad_sigue_yendo_al_splitter():
    bucle = [("spline", 1, ((0.0, 0.0), (10.0, 6.0), (-4.0, 6.0), (6.0, 0.0)), (0.0,) * 4 + (1.0,) * 4, 3, None),
             ("linea", 1, (6.0, 0.0), (0.0, 0.0))]
    assert pf._detectar_rust(bucle, PLANO) is None         # un cúbico sí puede cortarse: no se certifica


@rust_nuevo
@hay_dejavu
def test_el_punto_interior_de_rust_cae_adentro_de_la_cara():
    b = Boceto()
    b.agregar_texto((0, 0), "OO&@8B", altura=10, fuente="DejaVu Sans", espaciado=-4)
    perfiles = pf._detectar_rust(b.geometria(), PLANO)
    assert perfiles and all(getattr(p, "_punto", None) is not None for p in perfiles)
    for p in perfiles:
        assert BRepClass_FaceClassifier(p.cara, gp_Pnt(*map(float, p._punto)), 1e-7).State() == TopAbs_IN


@rust_nuevo
def test_sin_punto_seguro_se_malla_como_siempre():
    # una recta suelta adentro del círculo: el punto podría caer sobre ella, Rust no lo da y `sin_huecos` sigue igual
    b = Boceto()
    b.agregar_circulo((0, 0), 10)
    b.agregar_linea((-3, 0), (3, 0))
    (disco,) = pf._detectar_rust(b.geometria(), PLANO)
    assert getattr(disco, "_punto", None) is None
    assert len(pf.sin_huecos(pf.detectar_boceto(b, PLANO), b)) == 1


@hay_dejavu
def test_al_tipear_las_caches_dan_lo_mismo_que_sin_caches():
    def partes(texto):
        b = Boceto()
        tid = b.agregar_texto((0, 0), texto, altura=10, fuente="DejaVu Sans", espaciado=-2)
        perfiles = pf.detectar_boceto(b, PLANO)
        return [sorted(round(p.area, 6) for p in lista) for lista in pf.partes_de_texto(perfiles, [tid])]
    partes("OO      OO")
    con_cache = partes("OO      OOO")                      # solo cambia la última palabra
    _limpiar_caches()
    assert con_cache == partes("OO      OOO")
    assert len(con_cache[0]) == 2 and len(con_cache[1]) == 5   # cada palabra unida; 2 + 3 huecos


@hay_dejavu
def test_extruir_texto_encimado_sobre_un_cuerpo_ya_modificado_da_lo_mismo_sin_rust(monkeypatch):
    def volumen():
        _limpiar_caches()
        s = api.Sesion()
        for herramienta, argumentos in (("create_box", {"length": 60, "width": 20, "height": 5}),
                                        ("fillet", {"edges": "|Z", "radius": 2}),
                                        ("create_sketch", {"plane": ">Z"}),
                                        ("add_text", {"text": "OOO OO", "x": 2, "y": 4, "height": 10,
                                                      "font": "DejaVu Sans", "letter_spacing": -4})):
            assert api.llamar(s, herramienta, argumentos)["ok"]
        r = api.llamar(s, "extrude", {"sketch": "Boceto1", "profile": "sketch", "distance": 2, "operation": "join"})
        assert r["ok"], r
        (cuerpo,) = s.doc.estado_final.cuerpos.values()
        assert geo.es_valida(cuerpo.forma)
        return geo.volumen_exacto(cuerpo.forma)
    rapido = volumen()
    monkeypatch.setenv("OMNICAD_SIN_RUST", "1")
    assert rapido == pytest.approx(volumen(), rel=1e-7)

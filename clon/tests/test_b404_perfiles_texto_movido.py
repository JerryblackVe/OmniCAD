# -*- coding: utf-8 -*-
"""B-404: mover un texto del boceto no le saca letras a su extrusión. Todas las letras tienen la firma del texto; antes
cada perfil iba a la región más cercana a su centroide viejo y, con el texto movido, varias caían en la misma letra
(«Emilia» quedaba «Emi i») sin aviso. Si quedan menos regiones que perfiles elegidos, el paso avisa."""
import pytest

from omnicad import api
from omnicad.nucleo import geometria as geo


def llamar(s, nombre, **args):
    r = api.llamar(s, nombre, args)
    assert r["ok"], r
    return r["result"]


def volumen(s):
    return sum(geo.volumen(c.forma) for c in s.doc.estado_final.cuerpos.values())


def resultado_extrusion(s):
    i = next(k for k, o in enumerate(s.doc.operaciones) if o.TIPO == "extrusion")
    return s.doc.resultados[i]


@pytest.fixture
def emilia():
    s = api.Sesion()
    llamar(s, "create_sketch", name="B", plane="XY")
    texto = llamar(s, "add_text", text="Emilia", height=10)["entities"][0]["id"]
    return s, texto


@pytest.mark.parametrize("mover", [{"x": 3}, {"x": 80, "y": -20}])
def test_todas_las_letras_siguen_al_texto_movido(emilia, mover):
    s, texto = emilia
    llamar(s, "extrude", sketch="B", profile="text", distance=2)
    antes = volumen(s)
    assert len(s.doc.operaciones[-1].p["perfiles"]) == 8                 # E, m, i y su punto, l, i y su punto, a
    llamar(s, "edit_text", entity=texto, sketch="B", **mover)
    assert volumen(s) == pytest.approx(antes, rel=1e-9)
    assert resultado_extrusion(s).estado == "ok"


def test_texto_girado_conserva_todas_las_letras(emilia):
    s, _texto = emilia
    llamar(s, "extrude", sketch="B", profile="text", distance=2)
    antes = volumen(s)
    llamar(s, "transform_sketch", sketch="B", dx=15, dy=40, angle=90)
    assert volumen(s) == pytest.approx(antes, rel=1e-6)


def test_dos_letras_elegidas_siguen_siendo_las_mismas_al_mover(emilia):
    s, texto = emilia
    llamar(s, "extrude", sketch="B", profile=[0, 8], distance=2)          # la E y la a (el 7 es el hueco de la a)
    antes = volumen(s)
    llamar(s, "edit_text", entity=texto, sketch="B", x=30)
    assert volumen(s) == pytest.approx(antes, rel=1e-9)


def test_menos_regiones_que_perfiles_avisa_en_vez_de_callar(emilia):
    s, texto = emilia
    llamar(s, "extrude", sketch="B", profile="text", distance=2)
    llamar(s, "edit_text", entity=texto, sketch="B", text="Emil")        # quedan 5 regiones para 8 perfiles
    r = resultado_extrusion(s)
    assert r.estado == "aviso" and "ya no tiene región" in r.mensaje
    assert volumen(s) > 0


def test_resolver_todas_reparte_las_letras_del_texto_movido(emilia):
    """El gemelo de la extrusión: los pasos que resuelven perfiles con `entidades.resolver_todas` (repujado, nervio…)."""
    from omnicad.timeline import entidades as ent
    s, texto = emilia
    bid = s.paso("B").id
    br = s.doc.estado_final.bocetos[bid]
    letras = [p for p in br.perfiles if geo.area(p.cara) > 0][:8]
    refs = [{"tipo": "perfil", "boceto": bid, "firma": sorted(p.firma), "centroide": list(p.centroide_uv)} for p in letras]
    area = sum(geo.area(p.cara) for p in letras)
    llamar(s, "edit_text", entity=texto, sketch="B", x=3)
    caras = [e.forma for e in ent.resolver_todas(refs, s.doc.estado_final)]
    assert len({id(c) for c in caras}) == 8 and sum(geo.area(c) for c in caras) == pytest.approx(area, rel=1e-9)


def test_dos_perfiles_que_quedan_en_la_misma_region_avisan_y_no_se_extruyen_dos_veces():
    s = api.Sesion()
    llamar(s, "create_sketch", name="C", plane="XY")
    llamar(s, "draw_circle", sketch="C", center_x=0, center_y=0, radius=10)
    linea = llamar(s, "draw_line", sketch="C", start_x=-10, start_y=0, end_x=10, end_y=0)["entities"][0]["id"]
    llamar(s, "extrude", sketch="C", profile=[0, 1], distance=2)                 # las dos mitades
    llamar(s, "delete_sketch_entities", sketch="C", entities=[linea])         # vuelve a ser un solo disco
    r = resultado_extrusion(s)
    assert r.estado == "aviso" and "misma región" in r.mensaje
    assert volumen(s) == pytest.approx(3.141592653589793 * 100 * 2, rel=1e-6)

# -*- coding: utf-8 -*-
"""B-503: Cara de desfase −0,5 sobre las paredes de letras curvas. El desfase 2D de OpenCascade no achica un lazo cuyo
trazo se parte (la «e», la «@»): ahora se le restan las franjas de sus aristas, y el palo de la «i», que se va entero,
se reconoce. La unión o el corte de la banda va pegado (GlueShift), y si no sale creíble, por la booleana de siempre."""
import pytest
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace
from OCP.TopAbs import TopAbs_WIRE
from OCP.TopoDS import TopoDS

from omnicad import api
from omnicad.nucleo import geometria as geo
from omnicad.nucleo import solidos_modificar as sm
from omnicad.nucleo import vectores


def _texto(texto):
    s = api.Sesion()
    for nombre, args in (("create_box", {"length": 40, "width": 40, "height": 3}),
                         ("create_sketch", {"plane": ">Z", "name": "T"}),
                         ("add_text", {"text": texto, "x": -10, "y": -5, "height": 8}),
                         ("extrude", {"sketch": "T", "profile": "text", "distance": 3, "operation": "join"})):
        assert api.llamar(s, nombre, args)["ok"]
    return next(iter(s.doc.estado_final.cuerpos.values())).forma


def _paredes(forma):
    return [c for c in geo.caras(forma) if 3.1 < geo.centro_masa(c, True)[2] < 5.9]


def _tapas(forma):
    return [c for c in geo.caras(forma) if geo.centro_masa(c, True)[2] > 5.9]


def test_las_franjas_achican_como_el_desfase_de_opencascade_donde_este_anda():
    tapa = max(_tapas(_texto("a")), key=geo.area)
    lazo = BRepBuilderAPI_MakeFace(TopoDS.Wire(sm._unicos(tapa, TopAbs_WIRE)[0]), True).Face()
    exacto = vectores.desfase_caras([lazo], -0.3, "redondas")           # acá OpenCascade sí puede
    area = sum(geo.area(BRepBuilderAPI_MakeFace(TopoDS.Wire(w), True).Face())
               for f in exacto for w in sm._unicos(f, TopAbs_WIRE))
    por_franjas = vectores.booleana_caras([lazo], vectores._franjas(lazo, 0.3), "resta")
    assert geo.area(por_franjas) == pytest.approx(area, rel=1e-3)
    assert not vectores.se_borra_al_achicar(lazo, 0.3)


def test_e_e_i_se_achican_medio_milimetro_y_el_palo_de_la_i_se_va():
    """En main el atajo devolvía None (la «e» no se achicaba y el palo de la «i» no se daba por ido) y el kernel 3D
    fallaba: «No se pudo desfasar estas caras»."""
    forma = _texto("ei")
    r = sm._desfase_por_contorno(forma, _paredes(forma), -0.5)
    assert r is not None and geo.es_valida(r)
    assert len(_tapas(r)) == len(_tapas(forma)) - 1                    # el palo de la «i» (0,85 mm) desaparece
    perdida = sum(map(geo.area, _tapas(forma))) - sum(map(geo.area, _tapas(r)))
    assert geo.volumen_exacto(forma) - geo.volumen_exacto(r) == pytest.approx(perdida * 3, rel=1e-3)


def test_la_banda_pegada_da_lo_mismo_que_la_booleana_de_siempre_sobre_un_cuerpo_ya_desfasado(monkeypatch):
    forma = _texto("ei")
    una = sm.desfasar_caras(forma, _paredes(forma), 0.3)                  # el cuerpo ya viene de un paso anterior
    booleano = geo.booleano
    monkeypatch.setattr(geo, "booleano", lambda *a, **k: pytest.fail("no salió por la vía pegada"))
    pegada = sm.desfasar_caras(una, _paredes(una), -0.5)

    original = geo._booleana

    def sin_pegar(*a, **modo):                  # la pasada pegada falla: cae sola a la booleana de siempre
        if modo.get("pegar"):
            raise geo.ErrorGeometria("simulado")
        return original(*a, **modo)
    monkeypatch.setattr(geo, "booleano", booleano)
    monkeypatch.setattr(geo, "_booleana", sin_pegar)
    normal = sm.desfasar_caras(una, _paredes(una), -0.5)
    assert geo.es_valida(pegada)
    assert geo.volumen_exacto(pegada) == pytest.approx(geo.volumen_exacto(normal), rel=1e-6)

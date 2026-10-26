"""SOL-11: Empalme con puntos de radio intermedios, varios conjuntos y redondeo completo."""
import math

import pytest

from omnicad import api
from omnicad.nucleo import geometria as geo


def llamar(sesion, nombre, **args):
    r = api.llamar(sesion, nombre, args)
    assert r["ok"], r
    return r["result"]


def _caja():
    s = api.Sesion()
    llamar(s, "create_box", length=20, width=10, height=10, name="Bloque")        # x de -10 a 10, y de -5 a 5, z de 0 a 10
    return s


def _vol(s):
    f = s.cuerpo("Bloque").forma
    assert geo.es_valida(f)
    return geo.volumen(f)


def test_redondeo_completo_deja_media_cana():
    s = _caja()
    llamar(s, "fillet", type="full_round", center_face=">Z", side_faces=["<Y", ">Y"])
    # se quita lo que hay sobre el semicírculo de radio 5: (10 * 5 - π·25/2) por 20 de largo
    assert 2000 - _vol(s) == pytest.approx((50 - math.pi * 25 / 2) * 20, rel=1e-6)
    assert len(geo.caras(s.cuerpo("Bloque").forma)) == 6                          # la cara central se volvió la media caña


def test_redondeo_completo_valida_las_caras():
    s = _caja()
    for args in ({"type": "full_round", "center_face": ">Z", "side_faces": ["<Y"]},                   # falta una lateral
                 {"type": "full_round", "center_face": ">Z", "side_faces": ["<X", ">Y"]},             # no son paralelas
                 {"type": "full_round", "center_face": "<Y", "side_faces": ["<Z", ">Z"]},             # arista sin ser paralela
                 {"type": "full_round", "side_faces": ["<Y", ">Y"]}):
        r = api.llamar(s, "fillet", args)
        assert not r["ok"] or r["result"], args
    assert not api.llamar(s, "fillet", {"type": "full_round", "center_face": ">Z", "side_faces": ["<Y"]})["ok"]
    assert not api.llamar(s, "fillet", {"type": "full_round", "center_face": ">Z", "side_faces": ["<X", ">Y"]})["ok"]


def test_radio_variable_con_punto_intermedio():
    a, b = _caja(), _caja()
    llamar(a, "fillet", edges=">Z and |X", radius=1, radius_type="variable", end_radius=1, body="Bloque")
    llamar(b, "fillet", edges=">Z and |X", radius=1, radius_type="variable", end_radius=1, body="Bloque",
           radius_points=[{"position": 0.5, "radius": 3}])
    assert _vol(b) < _vol(a)                                                       # el punto intermedio agranda el radio
    assert not api.llamar(a, "fillet", {"edges": ">Z and |X", "radius": 1, "radius_type": "variable", "end_radius": 1,
                                        "radius_points": [{"position": 1.5, "radius": 3}]})["ok"]
    assert not api.llamar(a, "fillet", {"edges": ">Z and |X", "radius": 1, "radius_points": [{"position": 0.5, "radius": 3}]})["ok"]


def test_varios_conjuntos_en_un_solo_paso():
    s = _caja()
    llamar(s, "fillet", edges=">Z and |X", radius=1, sets=[{"edges": "<Z and |X", "radius": 2}])
    una = _caja()
    llamar(una, "fillet", edges=">Z and |X", radius=1)
    llamar(una, "fillet", edges="<Z and |X", radius=2)
    assert _vol(s) == pytest.approx(_vol(una), rel=1e-6)
    assert len(s.doc.operaciones) == 2                                             # la caja y UN empalme
    assert not api.llamar(s, "fillet", {"edges": ">Z and |X", "radius": 1, "sets": [{"edges": "<Z"}]})["ok"]


def _hit(doc, selector):
    from omnicad.api import selectores as sl
    from omnicad.ui.comando import hit_desde_ref
    c, e = sl.elegir_uno(api.Sesion(doc), selector, "cara")
    return hit_desde_ref(sl.referencia(c, e), doc.estado_final)


def test_dialogo_redondeo_completo_y_puntos_de_radio():
    from PySide6.QtWidgets import QApplication
    from omnicad.timeline.documento import Documento
    from omnicad.timeline.operaciones import OpPrimitiva
    from omnicad.ui.comando import ContextoComando, ErrorComando
    from omnicad.ui.comandos.modificar import Empalme
    QApplication.instance() or QApplication([])
    doc = Documento()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="20", largo="10", alto="10"))
    cmd, ctx = Empalme(), ContextoComando(doc)
    v = {c.clave: (list(c.defecto) if isinstance(c.defecto, list) else c.defecto) for c in cmd.campos(ctx)}
    v.update(tipo="completo", central=[_hit(doc, ">Z")], laterales=[_hit(doc, "<Y")])
    with pytest.raises(ErrorComando):
        cmd.construir(v, ctx)                                                      # falta una lateral
    v["laterales"] = [_hit(doc, "<Y"), _hit(doc, ">Y")]
    op = cmd.construir(v, ctx)
    doc.agregar(op)
    assert doc.resultados[-1].estado == "ok", doc.resultados[-1].mensaje
    assert cmd.desde_op(op, ContextoComando(doc, op=op))["laterales"]
    # puntos intermedios: texto mal formado o fuera de rango se rechaza antes de crear el paso
    assert Empalme._puntos_radio("0.5: 3 mm; 0.8:2 mm", ctx) == [{"posicion": "0.5", "radio": "3 mm"},
                                                                 {"posicion": "0.8", "radio": "2 mm"}]
    for malo in ("0.5", "1.5: 3 mm", "0.5: mucho"):
        with pytest.raises(Exception):
            Empalme._puntos_radio(malo, ctx)


def test_radio_asimetrico_y_g2_en_una_arista_recta():
    s = api.Sesion()
    llamar(s, "create_box", length=20, width=20, height=20, name="Caja")
    base = geo.volumen(s.cuerpo("Caja").forma)
    llamar(s, "fillet", edges="nearest:[10,10,10]", radius=2, tangent_chain=False, radius_type="asymmetric", radius2=2)
    assert base - geo.volumen(s.cuerpo("Caja").forma) == pytest.approx((4 - math.pi) * 20, rel=1e-6)   # r1 = r2: el círculo
    llamar(s, "undo")
    llamar(s, "fillet", edges="nearest:[10,10,10]", radius=2, tangent_chain=False, radius_type="asymmetric", radius2=4)
    forma = s.cuerpo("Caja").forma
    assert geo.es_valida(forma)
    assert base - geo.volumen(forma) == pytest.approx((1 - math.pi / 4) * 2 * 4 * 20, rel=1e-6)           # cónica de 2 × 4
    llamar(s, "undo")
    llamar(s, "fillet", edges="nearest:[10,10,10]", radius=2, tangent_chain=False, continuity="g2")
    g2 = s.cuerpo("Caja").forma
    assert geo.es_valida(g2) and 0.85 * (4 - math.pi) * 20 < base - geo.volumen(g2) < 4 * 20 / 2        # entre el círculo y el chaflán
    r = api.llamar(s, "fillet", dict(edges="|Z", radius=1, radius_type="chord", chord_length=1, continuity="g2"))
    assert not r["ok"] and "g2" in r["mensaje"]
    r = api.llamar(s, "fillet", dict(edges="nearest:[10,10,10]", radius=2, radius_type="asymmetric"))
    assert not r["ok"] and "radius2" in r["mensaje"]


def test_radio_asimetrico_en_arista_concava_se_rellena():
    s = api.Sesion()
    llamar(s, "create_box", length=20, width=20, height=10, name="Base")
    llamar(s, "create_box", length=10, width=20, height=10, z=10, name="Pared")
    llamar(s, "boolean_operation", target="Base", tools=["Pared"], operation="join")
    antes = geo.volumen(s.cuerpo("Base").forma)
    llamar(s, "fillet", edges="nearest:[5,0,10]", radius=1, radius2=2, radius_type="asymmetric", tangent_chain=False)
    forma = s.cuerpo("Base").forma
    assert geo.es_valida(forma)
    assert geo.volumen(forma) - antes == pytest.approx((1 - math.pi / 4) * 1 * 2 * 20, rel=1e-6)        # rellena la esquina


def test_esquina_setback_crece_el_radio_hacia_la_esquina():
    s = api.Sesion()
    llamar(s, "create_box", length=20, width=20, height=20, name="Caja")
    base = geo.volumen(s.cuerpo("Caja").forma)
    aristas = ["nearest:[10,10,10]", "nearest:[10,0,20]", "nearest:[0,10,20]"]       # las tres aristas del vértice (10, 10, 20)
    llamar(s, "fillet", edges=aristas, radius=2, tangent_chain=False)
    bola = base - geo.volumen(s.cuerpo("Caja").forma)
    llamar(s, "undo")
    llamar(s, "fillet", edges=aristas, radius=2, tangent_chain=False, corner_type="setback", setback=3)
    forma = s.cuerpo("Caja").forma
    assert geo.es_valida(forma)
    corto = base - geo.volumen(forma)
    llamar(s, "undo")
    llamar(s, "fillet", edges=aristas, radius=2, tangent_chain=False, corner_type="setback", setback=6)
    largo = base - geo.volumen(s.cuerpo("Caja").forma)
    assert bola < corto < largo                                       # más setback, más material quitado en la esquina
    r = api.llamar(s, "fillet", dict(edges=aristas, radius=2, corner_type="setback"))
    assert not r["ok"] and "setback" in r["mensaje"]


def test_g2_y_asimetrico_rechazan_radio_que_no_entra_y_extremos_oblicuos():
    s = api.Sesion()
    llamar(s, "create_box", length=20, width=20, height=2, name="Placa")
    r = api.llamar(s, "fillet", dict(edges="nearest:[0,-10,2]", radius=3, tangent_chain=False, continuity="g2"))
    assert not r["ok"] and "no entra" in r["mensaje"]
    t = api.Sesion()
    llamar(t, "create_box", length=20, width=20, height=20, name="Caja")
    llamar(t, "chamfer", edges="|Z", distance=3, tangent_chain=False)
    r = api.llamar(t, "fillet", dict(edges="nearest:[0,-10,20]", radius=2, radius_type="asymmetric", radius2=3, tangent_chain=False))
    assert not r["ok"] and "perpendiculares" in r["mensaje"]

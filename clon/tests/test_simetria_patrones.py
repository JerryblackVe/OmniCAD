# -*- coding: utf-8 -*-
"""Simetría, patrones y copias: heredan aspecto y material; distancias del patrón explicadas (P12)."""
import math

import pytest

from omnicad import api
from omnicad.nucleo import geometria as geo
from omnicad.nucleo.render_cpu import color_y_acabado
from omnicad.timeline.documento import Documento
from omnicad.timeline.operaciones import propiedades_cuerpo

ROJO = [1.0, 0.0, 0.0]


def ok(r):
    assert r["ok"], r
    return r["result"]


@pytest.fixture
def s():
    sesion = api.Sesion(Documento())
    ok(api.llamar(sesion, "create_box", {"length": 10, "width": 10, "height": 10}))
    sesion.doc.set_propiedad(["op1.c1"], "apariencia", ROJO)
    sesion.doc.set_propiedad(["op1.c1"], "material", "Aluminio 6061")
    return sesion


def _nuevo(s, herramienta, args):
    antes = set(s.doc.estado_final.cuerpos)
    ok(api.llamar(s, herramienta, args))
    nuevos = [c for c in s.doc.estado_final.cuerpos if c not in antes]
    assert nuevos
    return nuevos[-1]


def _hereda(s, cid):
    doc = s.doc
    c = doc.estado_final.cuerpos[cid]
    assert geo.es_valida(c.forma)
    assert geo.volumen(c.forma) == pytest.approx(1000, rel=1e-6)
    assert doc.propiedad(cid, "material") == "Aluminio 6061"
    assert doc.propiedad(cid, "apariencia") == ROJO
    color, _ = color_y_acabado(c, propiedades_cuerpo(doc.propiedades, c))
    assert tuple(color)[:3] == pytest.approx((1.0, 0.0, 0.0))


def test_simetria_hereda_aspecto_y_material(s):
    cid = _nuevo(s, "mirror", {"bodies": "op1.c1", "plane": "YZ"})
    _hereda(s, cid)


def test_patron_y_mover_copiar_heredan(s):
    cid = _nuevo(s, "rectangular_pattern", {"bodies": "op1.c1", "x_count": 2, "x_spacing": 20})
    _hereda(s, cid)
    copia = _nuevo(s, "move_body", {"body": "op1.c1", "translate": [0, 30, 0], "copy": True})
    _hereda(s, copia)
    # copia de copia
    otra = _nuevo(s, "mirror", {"bodies": copia, "plane": "XZ"})
    _hereda(s, otra)


def test_lo_propio_gana_y_el_nombre_no_se_hereda(s):
    s.doc.set_propiedad(["op1.c1"], "nombre", "LED")
    cid = _nuevo(s, "mirror", {"bodies": "op1.c1", "plane": "YZ"})
    assert s.doc.propiedad(cid, "nombre") is None
    s.doc.set_propiedad([cid], "apariencia", [0.0, 1.0, 0.0])
    assert s.doc.propiedad(cid, "apariencia") == [0.0, 1.0, 0.0]
    assert s.doc.propiedad("op1.c1", "apariencia") == ROJO


def test_masa_de_la_copia_usa_el_material_heredado(s):
    cid = _nuevo(s, "mirror", {"bodies": "op1.c1", "plane": "YZ"})
    r = ok(api.llamar(s, "get_physical_properties", {"bodies": [cid]}))
    texto = str(r)
    assert "Aluminio 6061" in texto
    assert "2.7" in texto


def _xs(s):
    return sorted(round(geo.caja_envolvente(c.forma)[0][0], 3) for c in s.doc.estado_final.cuerpos.values())


def test_patron_sin_distribucion_avisa_que_d1_es_total(s):
    r = api.llamar(s, "run_operation", {"type": "patron", "params": {
        "cuerpos": ["op1.c1"], "dir1": {"tipo": "eje", "id": "X"}, "n1": 3, "d1": "50 mm"}})
    ok(r)
    assert any("TOTAL" in a and "espaciado" in a for a in r["avisos"]), r["avisos"]
    assert _xs(s) == [-5.0, 20.0, 45.0]


def test_patron_espaciado_no_avisa(s):
    r = api.llamar(s, "run_operation", {"type": "patron", "params": {
        "cuerpos": ["op1.c1"], "dir1": {"tipo": "eje", "id": "X"}, "n1": 3, "d1": "50 mm", "distribucion": "espaciado"}})
    ok(r)
    assert not any("TOTAL" in a for a in r["avisos"]), r["avisos"]
    assert _xs(s) == [-5.0, 45.0, 95.0]


def test_edit_feature_de_rectangular_pattern_aclara_separacion(s):
    ok(api.llamar(s, "rectangular_pattern", {"bodies": "op1.c1", "x_count": 3, "x_spacing": 20}))
    paso = s.doc.operaciones[-1].id
    r = api.llamar(s, "edit_feature", {"feature": paso, "params": {"d1": "30 mm"}})
    ok(r)
    assert any("separación" in a for a in r["avisos"]), r["avisos"]
    assert _xs(s) == [-5.0, 25.0, 55.0]


def test_describe_operation_patron_explica_distribucion():
    doc = ok(api.llamar(api.Sesion(Documento()), "describe_operation", {"type": "patron"}))["doc"]
    assert "distribucion" in doc and "TOTAL" in doc


def _ruta(s):
    ok(api.llamar(s, "create_sketch", {"plane": "XY", "name": "Ruta"}))
    ok(api.llamar(s, "draw_line", {"start_x": 0, "start_y": -40, "end_x": 100, "end_y": -40}))
    return "Ruta"


def test_patron_en_puntos_en_ruta_y_multitransformacion_heredan(s):
    cid = _nuevo(s, "point_pattern", {"bodies": "op1.c1", "points": [[40, 0, 0]]})
    _hereda(s, cid)
    cid = _nuevo(s, "multi_transform", {"bodies": "op1.c1", "transforms": [
        {"type": "rectangular", "axis": "y", "count": 2, "spacing": 30}, {"type": "mirror", "plane": "XY"}]})
    _hereda(s, cid)
    cid = _nuevo(s, "path_pattern", {"bodies": "op1.c1", "path_sketch": _ruta(s), "count": 2, "distance": 50,
                                     "twist": 45})
    _hereda(s, cid)


def test_run_operation_patron_de_operaciones_y_multitransformar(s):
    """run_operation guarda tal cual los campos nuevos (pasos, coordenadas y transformaciones no son referencias) y el
    patrón y la multitransformación de operaciones repiten el corte del cilindro."""
    ok(api.llamar(s, "create_cylinder", {"radius": 1, "height": 30, "z": -10, "operation": "cut"}))
    agujero = s.doc.operaciones[-1].id
    un_agujero = math.pi * 1 ** 2 * 10
    ok(api.llamar(s, "run_operation", {"type": "patron", "params": {
        "objeto": "operaciones", "pasos": [agujero], "forma_patron": "puntos", "coordenadas": [[3, 3, 0]]}}))
    patron = s.doc.operaciones[-1]
    assert s.doc.resultados[-1].estado == "ok" and patron.p["pasos"] == [agujero]
    assert geo.volumen(s.doc.estado_final.cuerpos["op1.c1"].forma) == pytest.approx(1000 - 2 * un_agujero, rel=1e-9)
    ok(api.llamar(s, "run_operation", {"type": "multitransformar", "params": {
        "objeto": "operaciones", "pasos": [patron.id],
        "transformaciones": [{"tipo": "simetria", "plano": {"tipo": "plano", "id": "YZ"}}]}}))
    assert s.doc.resultados[-1].estado == "ok"
    forma = s.doc.estado_final.cuerpos["op1.c1"].forma
    assert geo.es_valida(forma) and geo.volumen(forma) == pytest.approx(1000 - 3 * un_agujero, rel=1e-9)


def test_describe_operation_patron_y_multitransformar_explican_lo_nuevo():
    sesion = api.Sesion(Documento())
    doc = ok(api.llamar(sesion, "describe_operation", {"type": "patron"}))["doc"]
    assert all(clave in doc for clave in ("objeto", "pasos", "giro", "coordenadas", "referencia_xyz", "puntos"))
    campos = {p["name"]: p for p in ok(api.llamar(sesion, "describe_operation", {"type": "patron"}))["params"]}
    assert all("format" not in campos[k] for k in ("pasos", "coordenadas", "referencia_xyz"))     # no son referencias
    assert "punto" in campos["referencia"]["format"] and "boceto" in campos["puntos"]["format"]
    doc = ok(api.llamar(sesion, "describe_operation", {"type": "multitransformar"}))["doc"]
    assert "transformaciones" in doc and "simetria" in doc

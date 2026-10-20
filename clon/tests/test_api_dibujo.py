# -*- coding: utf-8 -*-
"""Herramientas del grupo "dibujo" (espacio DIBUJO, bug B-80 / MCP-11 a MCP-14 y MCP-85): crear y consultar el
plano, hoja y cajetín, vistas (base, proyectada, sección, detalle) y su edición. Todo sin abrir la ventana."""
import pytest

from omnicad import api


@pytest.fixture(scope="module")
def sesion():
    s = api.Sesion()
    r = api.llamar(s, "create_box", {"length": 40, "width": 20, "height": 10, "name": "Caja"})
    assert r["ok"], r
    return s


def _ok(s, nombre, args=None):
    r = api.llamar(s, nombre, args or {})
    assert r["ok"], r
    return r["result"]


def test_sin_dibujo_las_herramientas_lo_dicen(sesion):
    r = api.llamar(sesion, "get_drawing", {})
    assert not r["ok"] and r["error_kind"] == "DRAWING_NOT_FOUND"
    r = api.llamar(sesion, "set_drawing_sheet", {"size": "A4"})
    assert not r["ok"] and r["error_kind"] == "DRAWING_NOT_FOUND"


def test_crear_dibujo_con_vista_base_y_consultarlo(sesion):
    res = _ok(sesion, "create_drawing", {"size": "A3", "title": "Soporte", "bodies": ["Caja"]})
    assert res["sheet"]["size"] == "A3" and res["sheet"]["width"] == 420.0 and res["sheet"]["height"] == 297.0
    assert res["sheet"]["standard"] == "ISO" and res["sheet"]["projection"] == "first_angle"
    assert res["title_block"]["title"] == "Soporte"
    (v,) = res["views"]
    assert v["id"] == "v1" and v["type"] == "base" and v["orientation"] == "front" and v["error"] is None
    assert v["style"] == "visible_hidden" and v["center_marks"] is True
    assert 0 < v["scale"] <= 1 or v["scale"] >= 1
    x0, y0, x1, y1 = v["bbox"]
    # la vista frontal de una caja de 40 × 10 mide 40·escala × 10·escala en la hoja
    assert x1 - x0 == pytest.approx(40 * v["scale"], abs=0.01) and y1 - y0 == pytest.approx(10 * v["scale"], abs=0.01)
    # lo guarda en doc.espacios con el formato de la ventana y get_drawing lo devuelve igual
    assert sesion.doc.espacios["dibujo"]["vistas"][0]["id"] == "v1"
    assert _ok(sesion, "get_drawing")["views"] == res["views"]
    assert _ok(sesion, "get_drawing")["parts_list"][1][2] == "Caja"
    r = api.llamar(sesion, "create_drawing", {})
    assert not r["ok"] and r["error_kind"] == "DRAWING_EXISTS"


def test_hoja_y_cajetin(sesion):
    res = _ok(sesion, "set_drawing_sheet", {"standard": "ASME", "size": "ANSI B", "orientation": "vertical",
                                            "method": "fast", "title": "Brida", "part_number": "BR-01",
                                            "author": "Gerardo", "material": "Acero", "scale": "1:2"})
    assert res["sheet"]["standard"] == "ASME" and res["sheet"]["projection"] == "third_angle"
    assert res["sheet"]["size"] == "ANSI B" and res["sheet"]["orientation"] == "vertical"
    assert (res["sheet"]["width"], res["sheet"]["height"]) == (279.4, 431.8) and res["sheet"]["method"] == "fast"
    assert res["title_block"]["title"] == "Brida" and res["title_block"]["part_number"] == "BR-01"
    assert res["title_block"]["material"] == "Acero" and res["title_block"]["scale"] == "1:2"
    assert sesion.doc.espacios["dibujo"]["hoja"]["diedro"] == "tercero"
    for malo in ({}, {"size": "A9"}):
        r = api.llamar(sesion, "set_drawing_sheet", malo)
        assert not r["ok"] and r["error_kind"] == "INVALID_ARGUMENTS", r
    _ok(sesion, "set_drawing_sheet", {"standard": "ISO", "size": "A3", "orientation": "horizontal", "method": "exact"})


def test_vista_proyectada_y_de_seccion_y_de_detalle(sesion):
    base = _ok(sesion, "get_drawing")["views"][0]
    cx, cy = (base["bbox"][0] + base["bbox"][2]) / 2, (base["bbox"][1] + base["bbox"][3]) / 2
    ancho = base["bbox"][2] - base["bbox"][0]
    der = _ok(sesion, "add_drawing_view", {"type": "projected", "parent": "v1", "position": [cx + ancho + 30, cy]})
    assert der["type"] == "projected" and der["parent"] == "v1" and der["direction"] == [1, 0]
    assert der["position"][1] == pytest.approx(base["position"][1], abs=1e-6)       # alineada con la padre
    assert der["scale"] == base["scale"] and der["error"] is None
    arriba = _ok(sesion, "add_drawing_view", {"type": "projected", "parent": "v1", "position": [cx, cy + 60]})
    assert arriba["direction"] == [0, 1]
    corte = _ok(sesion, "add_drawing_view", {
        "type": "section", "parent": "v1", "section_line": [[cx, cy - 20], [cx, cy + 20]],
        "position": [cx - ancho - 30, cy]})
    assert corte["type"] == "section" and corte["label"] and corte["error"] is None
    detalle = _ok(sesion, "add_drawing_view", {"type": "detail", "parent": "v1", "detail_center": [cx, cy],
                                               "detail_radius": 5, "position": [cx + 90, cy - 60]})
    assert detalle["type"] == "detail" and detalle["scale"] == pytest.approx(2 * base["scale"], rel=1e-6)
    ids = [v["id"] for v in _ok(sesion, "get_drawing")["views"]]
    assert ids == ["v1", "v2", "v3", "v4", "v5"]


def test_errores_de_vistas(sesion):
    casos = [({"type": "projected", "position": [10, 10]}, "INVALID_ARGUMENTS"),
             ({"type": "projected", "parent": "v1"}, "INVALID_ARGUMENTS"),
             ({"type": "projected", "parent": "v99", "position": [10, 10]}, "DRAWING_ELEMENT_NOT_FOUND"),
             ({"type": "section", "parent": "v1", "position": [10, 10]}, "INVALID_ARGUMENTS"),
             ({"type": "detail", "parent": "v1", "position": [10, 10]}, "INVALID_ARGUMENTS"),
             ({"type": "base", "scale": "x"}, "INVALID_ARGUMENTS"),
             ({"type": "base", "bodies": ["NoExiste"]}, "BODY_NOT_FOUND")]
    for args, kind in casos:
        r = api.llamar(sesion, "add_drawing_view", args)
        assert not r["ok"] and r["error_kind"] == kind, (args, r)
    assert len(_ok(sesion, "get_drawing")["views"]) == 5          # ninguna falla dejó nada a medias


def test_editar_vista_escala_estilo_marcas_etiqueta_y_giro(sesion):
    antes = {v["id"]: v for v in _ok(sesion, "get_drawing")["views"]}
    r = _ok(sesion, "edit_drawing_view", {"view": "v1", "scale": "1:2", "style": "visible", "tangents": "off",
                                          "center_marks": False, "label": "P"})
    assert r["scale"] == 0.5 and r["scale_text"] == "1:2" and r["style"] == "visible" and r["tangents"] == "off"
    assert r["center_marks"] is False and r["label"] == "P"
    despues = {v["id"]: v for v in _ok(sesion, "get_drawing")["views"]}
    assert despues["v2"]["scale"] == 0.5 and despues["v3"]["scale"] == 0.5          # las proyectadas la heredan
    assert despues["v5"]["scale"] == antes["v5"]["scale"]                            # la de detalle conserva la suya
    giro = _ok(sesion, "edit_drawing_view", {"view": "v1", "rotate": 90})
    assert giro["rotation"] == 90.0
    assert _ok(sesion, "edit_drawing_view", {"view": "v1", "rotate": 300})["rotation"] == 30.0
    for malo in ({"view": "v1"}, {"view": "v77", "scale": 1}, {"view": "v1", "scale": "0"}):
        r = api.llamar(sesion, "edit_drawing_view", malo)
        assert not r["ok"] and r["error_kind"] in ("INVALID_ARGUMENTS", "DRAWING_ELEMENT_NOT_FOUND"), r


def test_es_un_paso_de_deshacer_y_la_falla_no_cambia_nada(sesion):
    antes = sesion.doc.espacios["dibujo"]["vistas"][0]["escala"]
    _ok(sesion, "edit_drawing_view", {"view": "v1", "scale": 2})
    assert sesion.doc.espacios["dibujo"]["vistas"][0]["escala"] == 2.0
    _ok(sesion, "undo")
    assert sesion.doc.espacios["dibujo"]["vistas"][0]["escala"] == antes
    n = len(sesion.doc.espacios["dibujo"]["vistas"])
    r = api.llamar(sesion, "add_drawing_view", {"type": "projected", "parent": "v1", "position": [1, 1], "scale": "x"})
    assert not r["ok"]
    assert len(sesion.doc.espacios["dibujo"]["vistas"]) == n


def test_reemplazar_el_dibujo_y_agregar_la_primera_vista_crea_el_dibujo():
    s = api.Sesion()
    assert api.llamar(s, "create_box", {"length": 10, "width": 10, "height": 10})["ok"]
    v = _ok(s, "add_drawing_view", {"orientation": "iso_se"})          # sin create_drawing
    assert v["id"] == "v1" and v["orientation"] == "iso_se"
    res = _ok(s, "create_drawing", {"replace": True, "size": "A4"})
    assert res["views"] == [] and res["sheet"]["size"] == "A4"


def test_marcas_de_centro_automaticas_se_prenden_y_apagan():
    """MCP-85: center_marks agrega o saca las marcas y los ejes de centro de los círculos de la vista."""
    from omnicad.api.herramientas_dibujo import cargar_dibujo
    s = api.Sesion()
    assert api.llamar(s, "create_cylinder", {"radius": 5, "height": 20})["ok"]
    _ok(s, "add_drawing_view", {"orientation": "top"})

    def centro():                       # la hoja (marco) también usa la capa CENTRO: se cuenta solo la vista
        d = cargar_dibujo(s)
        return sum(1 for capa, _p in d.primitivas_vista(d.vista("v1")) if capa == "CENTRO")
    con = centro()
    assert con > 0
    _ok(s, "edit_drawing_view", {"view": "v1", "center_marks": False})
    assert centro() == 0
    _ok(s, "edit_drawing_view", {"view": "v1", "center_marks": True})
    assert centro() == con
    assert _ok(s, "add_drawing_view", {"orientation": "top", "center_marks": False, "position": [300, 100]})["center_marks"] is False

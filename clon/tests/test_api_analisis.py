# -*- coding: utf-8 -*-
"""Análisis de INSPECCIONAR y estilo visual por API (B-80, MCP-26, MCP-44 y MCP-45): manage_analysis, analyze_geometry,
section_view, set_visual_style y lo que dibuja get_viewport_image (estilos, análisis, cortes). Números exactos y píxeles."""
import io
import math

import numpy as np
import pytest
from PIL import Image

from omnicad import api


def ok(s, nombre, **args):
    r = api.llamar(s, nombre, args)
    assert r["ok"], r
    return r["result"]


def falla(s, nombre, esperado="INVALID_ARGUMENTS", **args):
    r = api.llamar(s, nombre, args)
    assert not r["ok"] and r["error_kind"] == esperado, r
    return r


def caja(s=None, lado=20):
    s = s or api.Sesion()
    ok(s, "create_box", length=lado, width=lado, height=lado)
    return s


def imagen(s, **args):
    r = ok(s, "get_viewport_image", width=96, height=72, view="iso", **args)
    return np.asarray(Image.open(io.BytesIO(r["image"].png)).convert("RGB")).astype(int), r


def distintas(a, b):
    return int((np.abs(a - b).sum(axis=2) > 12).sum())


# ---------------------------------------------------------------- manage_analysis
def test_manage_analysis_agrega_lista_oculta_muestra_y_quita_con_deshacer():
    s = caja()
    assert ok(s, "manage_analysis")["count"] == 0
    a = ok(s, "manage_analysis", action="add", type="section", plane="XY", offset=5)["analysis"]
    assert a == {"name": "Sección1", "type": "section", "visible": True}
    assert s.doc.analisis["Sección1"]["params"]["desfase_mm"] == 5.0
    ok(s, "manage_analysis", action="add", type="zebra", frequency=12, orientation="vertical", name="Mi cebra")
    assert s.doc.analisis["Mi cebra"]["params"] == {"frecuencia": 12, "orientacion": "vertical"}
    ok(s, "manage_analysis", action="add", type="draft", direction="z", min_angle=1, max_angle=5, flip=True)
    ok(s, "manage_analysis", action="add", type="curvature", curvature_type="mean")
    ok(s, "manage_analysis", action="add", type="isocurve", density=4)
    ok(s, "manage_analysis", action="add", type="accessibility", direction="x")
    ok(s, "manage_analysis", action="add", type="min_radius", radius=2.5)
    ok(s, "manage_analysis", action="add", type="environment_map")
    lista = ok(s, "manage_analysis")["analyses"]
    assert [x["type"] for x in lista] == ["section", "zebra", "draft", "curvature", "isocurve", "accessibility",
                                          "min_radius", "environment_map"]
    ok(s, "manage_analysis", action="hide", name="Mi cebra")
    assert not s.doc.analisis["Mi cebra"]["visible"]
    ok(s, "manage_analysis", action="hide", name="Mi cebra")                 # ocultar dos veces no lo vuelve a mostrar
    assert not s.doc.analisis["Mi cebra"]["visible"]
    ok(s, "manage_analysis", action="show", name="Mi cebra")
    assert s.doc.analisis["Mi cebra"]["visible"]
    assert ok(s, "manage_analysis", action="remove", name="Mi cebra")["count"] == 7
    ok(s, "undo")
    assert "Mi cebra" in s.doc.analisis                                        # un solo paso de deshacer por llamada


def test_manage_analysis_rechaza_lo_que_no_corresponde():
    s = caja()
    falla(s, "manage_analysis", action="add")                                  # sin type
    falla(s, "manage_analysis", action="add", type="section")                  # sin plano
    falla(s, "manage_analysis", action="add", type="zebra", radius=3)          # opción de otro tipo
    falla(s, "manage_analysis", action="add", type="zebra", frequency=0)
    falla(s, "manage_analysis", action="add", type="zebra", orientation="diagonal", esperado="INVALID_ARGUMENTS")
    falla(s, "manage_analysis", action="add", type="draft", min_angle=5, max_angle=1)
    falla(s, "manage_analysis", action="add", type="comb")                     # sin aristas
    falla(s, "manage_analysis", action="remove")                               # sin name
    falla(s, "manage_analysis", action="remove", name="no existe")
    ok(s, "manage_analysis", action="add", type="zebra", name="A")
    falla(s, "manage_analysis", action="add", type="zebra", name="A")          # nombre repetido
    falla(s, "manage_analysis", action="add", type="section", plane="no_existe")
    assert len(s.doc.analisis) == 1                                            # lo que falló no dejó nada


def test_peine_de_curvatura_toma_aristas_por_selector():
    s = api.Sesion()
    ok(s, "create_cylinder", radius=10, height=5)
    a = ok(s, "manage_analysis", action="add", type="comb", edges="edges:%CIRCLE and >Z", density=12, scale=2)
    assert s.doc.analisis[a["analysis"]["name"]]["params"]["densidad"] == 12
    assert len(s.doc.analisis[a["analysis"]["name"]]["params"]["aristas"]) == 1


# ---------------------------------------------------------------- analyze_geometry
def test_medidas_de_seccion_desmoldeo_y_accesibilidad_de_una_caja():
    s = caja()
    sec = ok(s, "analyze_geometry", type="section", plane="XY", offset=10)["bodies"][0]
    assert sec["area_mm2"] == pytest.approx(400) and sec["contour_length_mm"] == pytest.approx(80)
    assert sec["contour_box"] == {"min": [-10, -10, 10], "max": [10, 10, 10]}
    assert ok(s, "analyze_geometry", type="section", plane="XY", offset=50)["bodies"][0]["intersects"] is False
    dr = ok(s, "analyze_geometry", type="draft", direction="z")["bodies"][0]
    assert dr["angle_deg"]["min"] == pytest.approx(-90) and dr["angle_deg"]["max"] == pytest.approx(90)
    assert dr["sufficient_percent"] == pytest.approx(100 / 6, abs=0.01)        # la tapa de arriba: 1 de 6 caras
    assert dr["insufficient_percent"] == pytest.approx(500 / 6, abs=0.01)
    inv = ok(s, "analyze_geometry", type="draft", direction="z", flip=True)["bodies"][0]
    assert inv["sufficient_percent"] == pytest.approx(100 / 6, abs=0.01) and inv["direction"] == [0, 0, -1]
    assert ok(s, "analyze_geometry", type="draft", flip=True)["bodies"][0]["direction"] == [0, 0, -1]   # flip sin dirección
    assert ok(s, "analyze_geometry", type="accessibility", direction="z")["bodies"][0]["accessible_percent"] == \
        pytest.approx(500 / 6, abs=0.01)                                         # todo menos la base
    assert ok(s, "analyze_geometry", type="isocurve", density=4)["bodies"][0]["u_curves"] > 0


def test_curvatura_de_una_esfera_y_radio_minimo_de_un_agujero():
    s = api.Sesion()
    ok(s, "create_sphere", radius=10)
    g = ok(s, "analyze_geometry", type="curvature")["bodies"][0]                  # gaussiana = 1/r²
    assert g["mean"] == pytest.approx(0.01, rel=1e-3) and g["convex_percent"] == 100
    m = ok(s, "analyze_geometry", type="curvature", curvature_type="mean")["bodies"][0]
    assert m["mean"] == pytest.approx(0.1, rel=1e-3) and m["unit"] == "1/mm"
    s = caja(lado=20)
    ok(s, "create_cylinder", radius=3, height=40, z=-10, name="Aguja")
    ok(s, "boolean_operation", operation="cut", target="Cuerpo1", tools=["Aguja"])
    grande = ok(s, "analyze_geometry", type="min_radius", radius=5)["bodies"][0]
    chica = ok(s, "analyze_geometry", type="min_radius", radius=1)["bodies"][0]
    assert grande["blocked_percent"] > 0 and chica["blocked_percent"] == 0


def test_analyze_geometry_rechaza_lo_visual_y_lo_mal_pedido():
    s = caja()
    falla(s, "analyze_geometry", type="zebra")                                  # no es un valor del esquema
    falla(s, "analyze_geometry", type="section")                                # sin plano
    falla(s, "analyze_geometry", type="draft", frequency=3)
    falla(s, "analyze_geometry", type="section", plane="XY", bodies=["no_hay"], esperado="BODY_NOT_FOUND")
    falla(api.Sesion(), "analyze_geometry", type="curvature", esperado="NOTHING_TO_MEASURE")


# ---------------------------------------------------------------- section_view
def test_section_view_guarda_el_analisis_y_devuelve_el_corte():
    s = caja()
    r = ok(s, "section_view", plane="XZ", offset=4, name="Corte")
    assert r["analysis"] == {"name": "Corte", "type": "section", "visible": True}
    assert r["bodies"][0]["area_mm2"] == pytest.approx(400) and "Corte" in s.doc.analisis
    oculto = ok(s, "section_view", plane="YZ", show=False)
    assert oculto["analysis"]["visible"] is False
    falla(s, "section_view", plane="XY", name="Corte")
    falla(s, "section_view", plane="XY", bodies=["no_hay"], esperado="BODY_NOT_FOUND")
    ok(s, "undo")
    assert len(s.doc.analisis) == 1


def test_section_view_con_angulo_gira_el_plano_sobre_su_eje():
    s = caja()                                                                  # cubo de 20 de z=0 a z=20, centrado en x e y
    r = ok(s, "section_view", plane="XY", angle=45)
    assert r["bodies"][0]["area_mm2"] == pytest.approx(20 * 10 * 2 ** 0.5)       # corte a 45° por el origen: 20 × 10√2
    assert s.doc.analisis[r["analysis"]["name"]]["params"]["angulo"] == 45
    falla(s, "section_view", plane="XY", angle=400)


# ---------------------------------------------------------------- set_visual_style
def test_set_visual_style_guarda_estilo_entorno_y_efectos():
    s = caja()
    base = ok(s, "set_visual_style")
    assert base == {"style": "shaded", "environment": None,
                    "effects": {"shadows": None, "reflections": None, "ambient_occlusion": None, "ground_plane": None}}
    r = ok(s, "set_visual_style", style="wireframe_hidden_edges", environment="fotomaton", shadows=False, ground_plane=True)
    assert r["style"] == "wireframe_hidden_edges" and r["effects"]["shadows"] is False and r["effects"]["ground_plane"]
    ok(s, "set_visual_style", reflections=False)                                 # suma, no pisa lo anterior
    assert ok(s, "set_visual_style")["effects"] == {"shadows": False, "reflections": False, "ambient_occlusion": None,
                                                   "ground_plane": True}
    falla(s, "set_visual_style", style="pintura")
    falla(s, "set_visual_style", environment="marte")
    assert ok(s, "set_visual_style", clear=True)["style"] == "shaded"
    ok(s, "undo")
    assert ok(s, "set_visual_style")["style"] == "wireframe_hidden_edges"


# ---------------------------------------------------------------- lo que se ve en la imagen
def test_los_estilos_cambian_la_imagen_y_el_guardado_se_usa_por_defecto():
    s = caja()
    sombreado, r0 = imagen(s)
    assert r0["style"] == "shaded" and r0["analyses"] == []
    alambre, r1 = imagen(s, style="wireframe")
    assert r1["style"] == "wireframe" and distintas(sombreado, alambre) > 300
    fondo = int((np.abs(alambre - alambre[0, 0]).sum(axis=2) < 40).sum())
    assert fondo > 0.8 * alambre.shape[0] * alambre.shape[1]                       # casi todo fondo: solo las aristas
    ok(s, "set_visual_style", style="wireframe")
    guardado, r2 = imagen(s)
    assert r2["style"] == "wireframe" and distintas(guardado, alambre) == 0         # lo guardado es el de por defecto
    otro, _ = imagen(s, style="shaded")
    assert distintas(otro, sombreado) == 0                                           # lo pedido gana
    falla(s, "get_viewport_image", style="raro")


def test_el_entorno_y_los_efectos_guardados_se_ven():
    s = caja()
    normal, _ = imagen(s)
    ok(s, "set_visual_style", shadows=False, reflections=False, ambient_occlusion=False, ground_plane=False)
    liso, _ = imagen(s)
    assert distintas(normal, liso) > 100
    ok(s, "set_visual_style", environment="tema")
    assert distintas(liso, imagen(s)[0]) > 100                                       # otro entorno, otro fondo


def test_los_analisis_visibles_se_dibujan_y_se_pueden_elegir():
    s = caja()
    limpio, _ = imagen(s)
    ok(s, "manage_analysis", action="add", type="draft", direction="z", name="Desmoldeo")
    pintado, r = imagen(s)
    assert r["analyses"] == ["Desmoldeo"] and distintas(limpio, pintado) > 200
    verdes = ((pintado[..., 1] > pintado[..., 0] + 40) & (pintado[..., 1] > pintado[..., 2] + 40)).sum()
    rojos = ((pintado[..., 0] > pintado[..., 1] + 60) & (pintado[..., 0] > pintado[..., 2] + 60)).sum()
    assert verdes > 100 and rojos > 100                                              # la tapa verde, los lados rojos
    ninguno, r0 = imagen(s, analysis=[])
    assert r0["analyses"] == [] and distintas(ninguno, limpio) == 0
    ok(s, "manage_analysis", action="hide", name="Desmoldeo")
    assert distintas(imagen(s)[0], limpio) == 0                                      # oculto: no se dibuja
    elegido, r1 = imagen(s, analysis=["Desmoldeo"])
    assert r1["analyses"] == ["Desmoldeo"] and distintas(elegido, pintado) == 0     # pedido por nombre
    falla(s, "get_viewport_image", analysis=["no existe"])


def test_cebra_y_curvatura_pintan_por_vertice_sin_romper_el_color_de_siempre():
    s = api.Sesion()
    ok(s, "create_sphere", radius=10)
    limpia, _ = imagen(s)
    ok(s, "manage_analysis", action="add", type="zebra", frequency=6)
    cebra, _ = imagen(s)
    negros = int((cebra.sum(axis=2) < 3 * 60).sum())
    assert negros > 150 and distintas(cebra, limpia) > 300                           # franjas blancas y negras
    ok(s, "manage_analysis", action="remove", name="Cebra1")
    ok(s, "manage_analysis", action="add", type="curvature", curvature_type="gaussian")
    curva, _ = imagen(s)
    assert distintas(curva, limpia) > 300


def test_la_seccion_corta_la_pieza_y_muestra_su_tapa():
    s = caja()
    entera, _ = imagen(s, style="shaded", analysis=[])
    ok(s, "section_view", plane="XY", offset=10, name="Corte")      # la caja va de z = 0 a 20: corta por la mitad
    cortada, r = imagen(s)
    assert r["analyses"] == ["Corte"] and distintas(entera, cortada) > 200
    tapa = ((cortada[..., 0] > cortada[..., 1] + 60) & (cortada[..., 0] > cortada[..., 2] + 60)).sum()
    assert tapa > 100                                                                  # la tapa de color de la sección
    arista, _ = imagen(s, style="shaded_visible_edges")                                # los estilos también respetan el corte
    assert distintas(arista, cortada) > 20
    ok(s, "manage_analysis", action="hide", name="Corte")
    assert distintas(imagen(s)[0], entera) == 0


def test_la_imagen_sin_analisis_sigue_igual_que_antes():
    s = caja()
    a, _ = imagen(s)
    ok(s, "manage_analysis", action="add", type="zebra")
    ok(s, "manage_analysis", action="remove", name="Cebra1")
    b, _ = imagen(s)
    assert distintas(a, b) == 0
    assert math.isfinite(float(b.mean()))


def test_los_cuerpos_pedidos_se_dibujan_aunque_esten_ocultos_y_deshacer_vuelve_el_analisis():
    s = api.Sesion()
    ok(s, "create_box", length=5, width=5, height=5, name="A")
    ok(s, "create_box", length=5, width=5, height=5, x=20, name="B")
    ok(s, "isolate_bodies", bodies=["A"])                                        # B queda oculto
    assert ok(s, "get_viewport_image", width=64, height=48)["bodies"] == ["op1.c1"]
    assert ok(s, "get_viewport_image", width=64, height=48, bodies=["B"])["bodies"] == ["op2.c1"]
    ok(s, "manage_analysis", action="add", type="zebra", name="Z")
    ok(s, "manage_analysis", action="hide", name="Z")
    assert s.doc.analisis["Z"]["visible"] is False
    ok(s, "undo")                                                                # ocultar admite deshacer
    assert s.doc.analisis["Z"]["visible"] is True


# ---------------------------------------------------------------- SOL-38: color de la sección y rayado
def _capas_corte(s, nombre):
    from omnicad.timeline import analisis_vista
    a = s.doc.analisis[nombre]
    return analisis_vista.calcular(a["tipo"], a["params"], s.doc.estado_final, s.doc.propiedades)["capas"]


def test_seccion_sin_opciones_nuevas_se_dibuja_como_siempre():
    s = caja()
    nombre = ok(s, "section_view", plane="XY", offset=10)["analysis"]["name"]
    assert s.doc.analisis[nombre]["params"].get("rayado") is None and "color" not in s.doc.analisis[nombre]["params"]
    capas = _capas_corte(s, nombre)
    assert [c[0] for c in capas] == ["tris", "lineas"] and capas[0][2] == (0.85, 0.30, 0.25)


def test_seccion_color_personalizado_y_del_componente_y_rayado_sobreviven_a_guardar(tmp_path):
    s = caja()
    nombre = ok(s, "section_view", plane="XY", offset=10, section_color="custom", custom_color="#00FF80",
                hatch=True)["analysis"]["name"]
    capas = _capas_corte(s, nombre)
    assert capas[0][2] == (0.0, 1.0, pytest.approx(0.502, abs=1e-3)) and [c[0] for c in capas] == ["tris", "lineas", "lineas"]
    otro = ok(s, "section_view", plane="XY", offset=5, section_color="component")["analysis"]["name"]
    assert _capas_corte(s, otro)[0][2] == pytest.approx((0.72, 0.72, 0.73))          # acero: el aspecto de la caja sin pintar
    ruta = str(tmp_path / "s.omnicad")
    ok(s, "save_document", path=ruta)
    s2 = api.Sesion()
    ok(s2, "open_document", path=ruta)
    assert s2.doc.analisis[nombre]["params"]["rayado"] is True and s2.doc.analisis[otro]["params"]["color_modo"] == "componente"


def test_rayado_diagonal_son_rayas_a_45_grados_dentro_de_la_cara():
    from omnicad.nucleo import geometria as geo
    from omnicad.timeline.analisis_vista import rayado_diagonal
    tris = np.array([[[0, 0, 0], [10, 0, 0], [10, 10, 0]], [[0, 0, 0], [10, 10, 0], [0, 10, 0]]], float)   # cuadrado 10x10
    seg = rayado_diagonal(tris, geo.Plano("XY")).reshape(-1, 2, 3)
    assert len(seg) > 20
    d = seg[:, 1] - seg[:, 0]
    assert np.allclose(np.abs(d[:, 0]), np.abs(d[:, 1]), atol=1e-6) and np.all(d[:, 0] * d[:, 1] < 0)   # todas a 135° (u − v)
    assert seg.min() >= -1e-6 and seg.max() <= 10 + 1e-6 and np.allclose(seg[..., 2], 0)
    assert np.linalg.norm(d, axis=1).sum() == pytest.approx(100 / (10 * 2 ** 0.5 / 40), rel=0.05)    # largo total = área / separación


def test_section_view_rechaza_color_invalido():
    s = caja()
    falla(s, "section_view", plane="XY", custom_color="rojo")
    falla(s, "section_view", plane="XY", section_color="component", custom_color="#FF0000")
    falla(s, "manage_analysis", action="add", type="zebra", hatch=True)

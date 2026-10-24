"""Fase 6 del boceto: desfase de dos lados, patrones editables, vínculo de proyección, pegar entre bocetos."""
import json
import math

import pytest

from omnicad import api


@pytest.fixture
def s():
    sesion = api.Sesion()
    api.llamar(sesion, "create_sketch", {"plane": "XY", "name": "B"})
    return sesion


def ok(r):
    assert r["ok"], r
    return r["result"]


def llamar(sesion, nombre, **args):
    return ok(api.llamar(sesion, nombre, args))


def falla(sesion, nombre, **args):
    r = api.llamar(sesion, nombre, args)
    assert not r["ok"], r
    return r


def foto(sesion):
    return json.dumps(sesion.doc.a_dict(), sort_keys=True), len(sesion.doc._deshacer)


def boceto(sesion, sketch=None):
    return llamar(sesion, "get_sketch", sketch=sketch)


def areas(sesion, sketch=None):
    return sorted(p["area"] for p in boceto(sesion, sketch)["profiles"])


def rectangulo(sesion, x1=0, y1=0, x2=10, y2=10):
    """Ids de las 4 líneas: abajo, derecha, arriba, izquierda."""
    return [e["id"] for e in llamar(sesion, "draw_rectangle", x1=x1, y1=y1, x2=x2, y2=y2)["entities"]]


# ---------------------------------------------------------------- BOC-14: desfase
def test_boc14_simetrico_da_un_cuadrado_afuera_y_otro_adentro(s):
    abajo = rectangulo(s)[0]
    llamar(s, "offset_sketch_curves", entity=abajo, distance=2, direction="symmetric")
    assert areas(s) == pytest.approx(sorted([36, 100 - 36, 196 - 100]), abs=1e-3)


def test_boc14_dos_lados_con_distancias_distintas(s):
    abajo = rectangulo(s)[0]
    llamar(s, "offset_sketch_curves", entity=abajo, distance=1, distance2=3, direction="two")
    assert areas(s) == pytest.approx(sorted([16, 100 - 16, 144 - 100]), abs=1e-3)
    assert falla(s, "offset_sketch_curves", entity=abajo, distance=1, direction="two")["error_kind"] == "INVALID_ARGUMENTS"


def test_boc14_dos_lados_es_un_solo_paso_de_deshacer(s):
    c = llamar(s, "draw_circle", radius=5)["entities"][0]["id"]
    antes = foto(s)
    llamar(s, "offset_sketch_curves", entity=c, distance=1, direction="symmetric")
    radios = sorted(e["radius"] for e in boceto(s)["entities"] if e["type"] == "circle")
    assert radios == pytest.approx([4, 5, 6])
    llamar(s, "undo")
    assert foto(s) == antes


def _curva(s, tipo, excepto=()):
    return next(e for e in boceto(s)["entities"] if e["type"] == tipo and e["id"] not in excepto)


def test_boc14_spline_desfasada_queda_a_la_distancia(s):
    llamar(s, "draw_spline", points=[[0, 0], [5, 5], [10, 0]])
    sp = _curva(s, "spline")
    llamar(s, "offset_sketch_curves", entity=sp["id"], distance=1)
    nueva = _curva(s, "spline", excepto=(sp["id"],))
    # la original pasa por (5, 5) y su tangente ahí es horizontal: el punto medio desfasado queda a 1 mm
    cerca = min(nueva["vertices"], key=lambda q: abs(q[0] - 5))
    assert abs(cerca[1] - 5) == pytest.approx(1, abs=0.1)


def test_boc14_elipse_desfasada_es_una_spline_cerrada(s):
    llamar(s, "draw_ellipse", major_radius=10, minor_radius=6)
    el = _curva(s, "ellipse")
    llamar(s, "offset_sketch_curves", entity=el["id"], distance=1)
    nueva = _curva(s, "spline")
    xs = [p[0] for p in nueva["vertices"]]
    ys = [p[1] for p in nueva["vertices"]]
    assert max(xs) - min(xs) == pytest.approx(22, abs=0.2)
    assert max(ys) - min(ys) == pytest.approx(14, abs=0.2)
    assert nueva["closed"] is True


def test_boc14_soltar_el_desfase_deja_las_curvas_sin_asociacion(s):
    abajo = rectangulo(s)[0]
    r = llamar(s, "offset_sketch_curves", entity=abajo, distance=2)
    copia = r["entities"][0]["id"]
    assert any(c["type"] == "offset" for c in boceto(s)["constraints"])
    llamar(s, "release_offset", entity=copia)
    info = boceto(s)
    assert not any(c["type"] == "offset" for c in info["constraints"] + info["dimensions"])
    assert falla(s, "release_offset", entity=abajo)["error_kind"] == "INVALID_GEOMETRY"


# ---------------------------------------------------------------- BOC-16: patrones editables
def _centros(s):
    """Centros de los círculos del boceto, ordenados."""
    return sorted(tuple(round(v, 6) for v in e["center"]) for e in boceto(s)["entities"] if e["type"] == "circle")


def _plano(centros):
    return [v for c in centros for v in c]


def _circulo(s, x=0, y=0, r=1):
    return llamar(s, "draw_circle", radius=r, center_x=x, center_y=y)["entities"][0]["id"]


def test_boc16_suprimir_copias_al_crear_y_al_editar(s):
    c = _circulo(s)
    r = llamar(s, "sketch_rectangular_pattern", entities=[c], count1=4, distance1=30, suppress=[1])
    assert _centros(s) == [(0, 0), (10, 0), (30, 0)]
    assert sorted(r["instances"]) == ["0", "2"] and boceto(s)["patterns"][0]["suppressed"] == [1]
    llamar(s, "edit_sketch_pattern", pattern=r["pattern"], suppress=[])
    assert _centros(s) == [(0, 0), (10, 0), (20, 0), (30, 0)]


def test_boc16_editar_cantidad_y_distancia(s):
    c = _circulo(s)
    r = llamar(s, "sketch_rectangular_pattern", entities=[c], count1=3, distance1=20)
    llamar(s, "edit_sketch_pattern", pattern=r["pattern"], count1=5, distance1=40)
    assert _centros(s) == [(0, 0), (10, 0), (20, 0), (30, 0), (40, 0)]
    assert len(boceto(s)["patterns"]) == 1
    llamar(s, "undo")
    assert _centros(s) == [(0, 0), (10, 0), (20, 0)]


def test_boc16_direccion_2_libre_y_por_linea(s):
    c = _circulo(s)
    llamar(s, "sketch_rectangular_pattern", entities=[c], count1=2, distance1=10, count2=2, distance2=10, angle2=60)
    esperado = [(0, 0), (10, 0), (5, 8.660254), (15, 8.660254)]
    assert _plano(_centros(s)) == pytest.approx(_plano(sorted(esperado)), abs=1e-3)
    s2 = api.Sesion()
    llamar(s2, "create_sketch", plane="XY")
    c2 = _circulo(s2)
    linea = llamar(s2, "draw_line", start_x=0, start_y=-50, end_x=30, end_y=-50 + 30 * math.tan(math.radians(30)),
                   construction=True)["entities"][0]["id"]
    llamar(s2, "sketch_rectangular_pattern", entities=[c2], count1=3, distance1=20, direction1_line=linea)
    centros = _centros(s2)
    assert math.dist(centros[0], centros[2]) == pytest.approx(20, abs=1e-4)
    assert math.degrees(math.atan2(centros[2][1] - centros[0][1], centros[2][0] - centros[0][0])) == pytest.approx(30, abs=1e-3)


def test_boc16_patron_circular_editado(s):
    c = _circulo(s, 10, 0)
    r = llamar(s, "sketch_circular_pattern", entities=[c], count=4)
    assert len(_centros(s)) == 4
    llamar(s, "edit_sketch_pattern", pattern=r["pattern"], count=6)
    assert len(_centros(s)) == 6 and (-10.0, 0.0) in _centros(s)
    llamar(s, "edit_sketch_pattern", pattern=r["pattern"], count=3, total_angle=180)
    assert _plano(_centros(s)) == pytest.approx(_plano(sorted([(10, 0), (0, 10), (-10, 0)])), abs=1e-3)


def test_boc16_original_movido_arrastra_copias_tras_editar(s):
    c = _circulo(s)
    r = llamar(s, "sketch_rectangular_pattern", entities=[c], count1=2, distance1=10)
    llamar(s, "edit_sketch_pattern", pattern=r["pattern"], distance1=15)
    llamar(s, "transform_sketch", entities=[c], dx=5, dy=0)
    a, b = _centros(s)      # el solver reparte el corrimiento: lo que se conserva es el paso del patrón
    assert b[0] - a[0] == pytest.approx(15, abs=1e-6) and a[1] == b[1] == 0


def test_boc16_roundtrip_conserva_los_patrones(s):
    c = _circulo(s)
    llamar(s, "sketch_rectangular_pattern", entities=[c], count1=3, distance1=20, suppress=[0])
    op = s.doc.operaciones[0]
    from omnicad.restricciones import Boceto
    b = Boceto.desde_dict(json.loads(json.dumps(op.boceto.a_dict())))
    assert b.patrones[0]["suprimidos"] == [0] and len(b.patrones[0]["copias"]) == 1


def test_boc16_errores(s):
    c = _circulo(s)
    r = llamar(s, "sketch_rectangular_pattern", entities=[c], count1=2, distance1=10)
    assert falla(s, "edit_sketch_pattern", pattern=999, count1=3)["error_kind"] == "ENTITY_NOT_FOUND"
    assert falla(s, "edit_sketch_pattern", pattern=r["pattern"], count=3)["error_kind"] == "INVALID_ARGUMENTS"
    assert falla(s, "edit_sketch_pattern", pattern=r["pattern"], count1=500)["error_kind"] == "INVALID_ARGUMENTS"
    assert falla(s, "sketch_rectangular_pattern", entities=[c], count1=2, distance1=10,
                 suppress=[-1])["error_kind"] == "INVALID_ARGUMENTS"
    assert falla(s, "sketch_rectangular_pattern", entities=[c], count1=2, distance1=10,
                 direction1_line=c)["error_kind"] == "INVALID_GEOMETRY"


# ---------------------------------------------------------------- BOC-17: vínculo de proyección
@pytest.fixture
def caja():
    """Caja de ancho paramétrico (centrada en el origen) y un boceto en XY."""
    sesion = api.Sesion()
    llamar(sesion, "create_parameter", name="ancho", expression="20 mm")
    llamar(sesion, "create_box", length="ancho", width=10, height=10)
    llamar(sesion, "create_sketch", plane="XY")
    return sesion


def _ancho_x(sesion):
    xs = [p["x"] for p in boceto(sesion)["points"]]
    return max(xs) - min(xs)


def test_boc17_con_link_sigue_al_modelo_y_sin_link_queda_congelada(caja):
    r = llamar(caja, "project_to_sketch", bodies=["Cuerpo1"])
    assert r["projection"] == 1 and boceto(caja)["projections"] == [
        {"id": 1, "mode": "project", "lost": False, "entities": boceto(caja)["projections"][0]["entities"]}]
    llamar(caja, "set_parameter", name="ancho", expression="30 mm")
    assert _ancho_x(caja) == pytest.approx(30)
    s = api.Sesion()
    llamar(s, "create_parameter", name="ancho", expression="20 mm")
    llamar(s, "create_box", length="ancho", width=10, height=10)
    llamar(s, "create_sketch", plane="XY")
    assert llamar(s, "project_to_sketch", bodies=["Cuerpo1"], link=False)["projection"] is None
    llamar(s, "set_parameter", name="ancho", expression="30 mm")
    assert _ancho_x(s) == pytest.approx(20) and "projections" not in boceto(s)


def test_boc17_romper_vinculo_deja_geometria_normal_en_su_lugar(caja):
    llamar(caja, "project_to_sketch", bodies=["Cuerpo1"])
    assert all(e["state"] == "fixed" for e in boceto(caja)["entities"])
    llamar(caja, "break_projection_link", projection=1)
    info = boceto(caja)
    assert "projections" not in info and all(e["state"] != "fixed" for e in info["entities"])
    llamar(caja, "set_parameter", name="ancho", expression="30 mm")
    assert _ancho_x(caja) == pytest.approx(20)
    assert falla(caja, "break_projection_link", projection=1)["error_kind"] == "ENTITY_NOT_FOUND"


def test_boc17_proyeccion_perdida_se_lista_y_se_rompe_o_se_borra(caja):
    llamar(caja, "project_to_sketch", bodies=["Cuerpo1"])
    caja.doc.suprimir("op1")                    # la caja deja de existir: la proyección se pierde
    assert boceto(caja)["projections"][0]["lost"] is True
    antes = len(boceto(caja)["entities"])
    llamar(caja, "manage_lost_projections", action="break")
    info = boceto(caja)
    assert "projections" not in info and len(info["entities"]) == antes
    llamar(caja, "undo")
    llamar(caja, "manage_lost_projections", action="delete", projection=1)
    assert boceto(caja)["entities"] == [] and "projections" not in boceto(caja)
    assert falla(caja, "manage_lost_projections", action="break")["error_kind"] == "INVALID_ARGUMENTS"


def test_boc17_relink_a_otro_cuerpo_de_la_misma_forma():
    s = api.Sesion()
    llamar(s, "create_box", length=20, width=10, height=10)
    llamar(s, "create_box", length=50, width=10, height=10)
    llamar(s, "create_sketch", plane="XY")
    llamar(s, "project_to_sketch", bodies=["op1.c1"])
    s.doc.suprimir("op1")
    assert boceto(s)["projections"][0]["lost"] is True
    llamar(s, "manage_lost_projections", action="relink", projection=1, bodies=["op2.c1"])
    assert _ancho_x(s) == pytest.approx(50) and boceto(s)["projections"][0]["lost"] is False
    assert falla(s, "manage_lost_projections", action="relink", projection=1)["error_kind"] == "INVALID_ARGUMENTS"


def test_boc17_proyecta_planos_ejes_puntos_y_curvas_de_otro_boceto():
    s = api.Sesion()
    a = llamar(s, "create_sketch", plane="XZ")["sketch"]["id"]
    ln = llamar(s, "draw_line", start_x=2, start_y=0, end_x=10, end_y=5)["entities"][0]["id"]
    llamar(s, "create_sketch", plane="XY")
    r = llamar(s, "project_to_sketch", references=[{"sketch": a, "curve": ln}])
    linea = next(e for e in boceto(s)["entities"] if e["type"] == "line")
    assert linea["length"] == pytest.approx(8)
    llamar(s, "project_to_sketch", references=["XZ"])                  # traza del plano XZ: el eje x, ±100 mm
    largos = sorted(e["length"] for e in boceto(s)["entities"] if e["type"] == "line")
    assert largos == pytest.approx([8, 200])
    llamar(s, "project_to_sketch", references=["Z", "O"])             # eje perpendicular: un punto; origen: un punto
    assert sum(1 for p in boceto(s)["points"] if abs(p["x"]) < 1e-9 and abs(p["y"]) < 1e-9) >= 1
    assert falla(s, "project_to_sketch", references=["Fantasma"])["error_kind"] == "INVALID_ARGUMENTS"
    assert r["projection"] == 1


# ---------------------------------------------------------------- BOC-10: copiar y pegar entre bocetos
def test_boc10_copia_a_otro_boceto_con_cotas_y_restricciones():
    s = api.Sesion()
    a = llamar(s, "create_sketch", plane="XY", name="A")["sketch"]["id"]
    lados = rectangulo(s, 0, 0, 40, 20)
    llamar(s, "add_dimension", sketch=a, type="horizontal", entities=[lados[0]], value=40)
    llamar(s, "create_sketch", plane="XZ", name="B")
    r = llamar(s, "copy_sketch_entities", entities=lados, source_sketch=a, dx=100, dy=5)
    info = boceto(s)
    assert r["profiles"] == 1 and info["profiles"][0]["area"] == pytest.approx(800)
    assert info["profiles"][0]["centroid"] == pytest.approx([120, 15])
    assert [k["expression"] for k in info["dimensions"]] == ["40.0"]
    assert {c["type"] for c in info["constraints"]} >= {"horizontal", "vertical"}
    assert areas(s, a) == pytest.approx([800])                    # el original queda como estaba


def test_boc10_pegar_en_el_mismo_boceto_y_errores():
    s = api.Sesion()
    llamar(s, "create_sketch", plane="XY", name="A")
    c = llamar(s, "draw_circle", radius=3)["entities"][0]["id"]
    llamar(s, "copy_sketch_entities", entities=[c], source_sketch="A", dx=10)
    centros = sorted(e["center"][0] for e in boceto(s)["entities"] if e["type"] == "circle")
    assert centros == pytest.approx([0, 10])
    assert falla(s, "copy_sketch_entities", entities=[0], source_sketch="A")["error_kind"] == "ENTITY_NOT_FOUND"
    assert falla(s, "copy_sketch_entities", entities=[c], source_sketch="Fantasma")["error_kind"] == "SKETCH_NOT_FOUND"
    assert falla(s, "copy_sketch_entities", entities=[999], source_sketch="A")["error_kind"] == "ENTITY_NOT_FOUND"


# ---------------------------------------------------------------- BOC-8: aristas de la cara al crear el boceto
def _caja_con_tapa():
    s = api.Sesion()
    llamar(s, "create_parameter", name="ancho", expression="20 mm")
    llamar(s, "create_box", length="ancho", width=10, height=10)
    return s


def test_boc8_create_sketch_sobre_cara_proyecta_el_contorno_y_lo_sigue():
    s = _caja_con_tapa()
    r = llamar(s, "create_sketch", plane=">Z", project_edges=True)
    assert r["projected"] == 4 and r["profiles"] == 1
    assert areas(s) == pytest.approx([200])
    llamar(s, "set_parameter", name="ancho", expression="30 mm")
    assert areas(s) == pytest.approx([300])                          # asociativo: la cara cambió y el contorno la siguió
    vacio = llamar(s, "create_sketch", plane=">Z")
    assert vacio["profiles"] == 0 and "projected" not in vacio        # sin project_edges, vacío como antes


def test_boc8_sketch_from_spec_suma_el_contorno_y_un_plano_avisa():
    s = _caja_con_tapa()
    r = api.llamar(s, "sketch_from_spec", {"plane": ">Z", "project_edges": True, "entities": [
        {"type": "circle", "center": [0, 0], "radius": 2}]})
    assert r["ok"], r
    assert r["result"]["projected"] == 4 and r["result"]["entities"] == 5
    assert areas(s) == pytest.approx(sorted([200 - 4 * math.pi, 4 * math.pi]), abs=1e-3)
    r = api.llamar(s, "create_sketch", {"plane": "XY", "project_edges": True})
    assert r["ok"] and r["avisos"] and "cara" in r["avisos"][0]


# ---------------------------------------------------------------- BOC-18: perfil giratorio proyectado
def test_boc18_perfil_giratorio_de_un_cilindro_y_sigue_al_modelo():
    s = api.Sesion()
    llamar(s, "create_parameter", name="largo", expression="30 mm")
    llamar(s, "create_cylinder", radius=5, height="largo")
    llamar(s, "create_sketch", plane="XZ")
    r = llamar(s, "project_spun_profile", axis="Z", bodies=["Cuerpo1"], tolerance=0.05)
    assert r["projection"] == 1
    xs = [p["x"] for p in boceto(s)["points"]]
    ys = [p["y"] for p in boceto(s)["points"]]
    # el eje Z está en el plano XZ: h = altura (v del boceto) y r = radio (u), 5 mm
    assert max(xs) == pytest.approx(5, abs=0.06) and max(ys) - min(ys) == pytest.approx(30, abs=0.06)
    llamar(s, "set_parameter", name="largo", expression="40 mm")
    ys = [p["y"] for p in boceto(s)["points"]]
    assert max(ys) - min(ys) == pytest.approx(40, abs=0.06)
    llamar(s, "undo")
    flip = llamar(s, "project_spun_profile", axis="Z", bodies=["Cuerpo1"], flip=True, link=False)
    assert flip["projection"] is None and min(p["x"] for p in boceto(s)["points"]) == pytest.approx(-5, abs=0.06)


def test_boc18_errores():
    s = api.Sesion()
    llamar(s, "create_cylinder", radius=5, height=30)
    llamar(s, "create_sketch", plane="XY")
    assert falla(s, "project_spun_profile", axis="Z", bodies=["Cuerpo1"])["error_kind"] == "INVALID_GEOMETRY"
    assert falla(s, "project_spun_profile", axis="X")["error_kind"] == "INVALID_ARGUMENTS"
    assert falla(s, "project_spun_profile", axis="X", bodies=["Cuerpo1"], tolerance=0)["error_kind"] == "INVALID_ARGUMENTS"


# ---------------------------------------------------------------- BOC-30: escala con expresión y con punto fijo
def test_boc30_factor_como_expresion_y_base_en_punto_fijo(s):
    llamar(s, "create_parameter", name="ancho", expression="40 mm")
    lados = rectangulo(s, 0, 0, 10, 10)
    punto = next(p for p in boceto(s)["points"] if p["x"] == 0 and p["y"] == 0)
    llamar(s, "add_constraint", sketch="B", type="fix", entities=[punto["id"]])
    llamar(s, "transform_sketch", entities=lados, scale="ancho / 20", center_x=0, center_y=0)   # ×2 desde el punto fijo
    assert areas(s) == pytest.approx([400])
    assert falla(s, "transform_sketch", entities=lados, scale=2, center_x=5, center_y=5)["error_kind"] == "INVALID_GEOMETRY"
    assert falla(s, "transform_sketch", entities=lados, scale="nada")["error_kind"] == "INVALID_ARGUMENTS"

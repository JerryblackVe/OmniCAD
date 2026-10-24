"""Fase 0 del plan del boceto: validación de entradas y API (B-88 a B-93 y NOV-b80-2)."""
import pytest

from omnicad import api


def ok(sesion, nombre, **args):
    r = api.llamar(sesion, nombre, args)
    assert r["ok"], r
    return r


def falla(sesion, nombre, esperado, **args):
    r = api.llamar(sesion, nombre, args)
    assert not r["ok"] and r["error_kind"] == esperado, r
    return r


@pytest.fixture
def s():
    sesion = api.Sesion()
    ok(sesion, "create_sketch", name="B")
    return sesion


def estado(s):
    return s.doc.a_dict()


def sin_cambio(s, nombre, esperado, **args):
    """La herramienta falla con `esperado` y el documento queda igual."""
    antes = estado(s)
    r = falla(s, nombre, esperado, **args)
    assert estado(s) == antes
    return r


# ---------------------------------------------------------------- B-88
def test_b88_draw_line_encadena_los_extremos_que_coinciden(s):
    ok(s, "draw_line", start_x=0, start_y=0, end_x=10, end_y=0)
    ok(s, "draw_line", start_x=10, start_y=0, end_x=5, end_y=8)
    ok(s, "draw_line", start_x=5, start_y=8, end_x=0, end_y=0)
    sk = ok(s, "get_sketch")["result"]
    assert len(sk["points"]) == 3          # un triángulo comparte sus vértices (antes: 6 puntos sueltos)
    assert sk["profiles"] and len(sk["profiles"]) == 1


def test_b88_una_linea_suelta_sigue_funcionando(s):
    ok(s, "draw_line", start_x=0, start_y=0, end_x=10, end_y=0)
    ok(s, "draw_line", start_x=20, start_y=5, end_x=30, end_y=5)
    sk = ok(s, "get_sketch")["result"]
    assert len(sk["points"]) == 4 and len(sk["entities"]) == 2


# ---------------------------------------------------------------- B-89
@pytest.mark.parametrize("puntos", [[[0, 0], [5, 0], [10, 0]],      # barrido 0: el 3.º punto sigue la misma dirección
                                    [[0, 0], [5, 0], [0, 0]]])      # el 3.º punto cae en el centro
def test_b89_ranura_de_arco_con_barrido_nulo_o_tercer_punto_en_el_centro(s, puntos):
    sin_cambio(s, "draw_slot", "INVALID_GEOMETRY", points=puntos, width=1, kind="arc_center")


def test_b89_conica_con_extremos_iguales(s):
    sin_cambio(s, "draw_conic", "INVALID_GEOMETRY", start_x=0, start_y=0, end_x=0, end_y=0, vertex_x=5, vertex_y=5)


def test_b89_spline_de_control_cerrada_avisa_que_se_ignora(s):
    r = ok(s, "draw_spline", points=[[0, 0], [1, 1], [2, 0], [3, 1]], spline_type="control_points", closed=True)
    assert any("closed" in a for a in r["avisos"]), r["avisos"]
    r = ok(s, "draw_spline", points=[[0, 0], [1, 1], [2, 0], [3, 1]], spline_type="control_points")
    assert r["avisos"] == []
    r = ok(s, "sketch_from_spec", entities=[{"type": "spline", "points": [[0, 0], [1, 1], [2, 0], [3, 1]],
                                             "spline_type": "control_points", "closed": True}])
    assert any("closed" in a for a in r["avisos"]), r["avisos"]


# ---------------------------------------------------------------- B-90
def curvas(s):
    ok(s, "draw_line", start_x=0, start_y=0, end_x=10, end_y=0)
    ok(s, "draw_line", start_x=0, start_y=5, end_x=10, end_y=9)
    ok(s, "draw_spline", points=[[0, 20], [5, 25], [10, 20]])
    ok(s, "draw_conic", start_x=0, start_y=30, end_x=10, end_y=30, vertex_x=5, vertex_y=40)
    ok(s, "add_text", sketch="B", text="Hola", height=5)
    return {e["type"]: e["id"] for e in ok(s, "get_sketch")["result"]["entities"]}, \
        [e["id"] for e in ok(s, "get_sketch")["result"]["entities"] if e["type"] == "line"]


@pytest.mark.parametrize("tipo", ["spline", "conic", "text"])
@pytest.mark.parametrize("cota", ["distance", "horizontal", "vertical", "radius", "diameter", "angle", "offset"])
def test_b90_cota_sobre_entidad_que_no_corresponde(s, tipo, cota):
    por_tipo, _ = curvas(s)
    sin_cambio(s, "add_dimension", "INVALID_DIMENSION", sketch="B", type=cota, entities=[por_tipo[tipo]])


def test_b90_diametro_y_radio_sobre_una_linea(s):
    _, lineas = curvas(s)
    for cota in ("diameter", "radius"):
        sin_cambio(s, "add_dimension", "INVALID_DIMENSION", sketch="B", type=cota, entities=[lineas[0]])


@pytest.mark.parametrize("valor", [0, 180, 200, -30, 360])
def test_b90_angulo_fuera_de_rango(s, valor):
    _, lineas = curvas(s)
    r = sin_cambio(s, "add_dimension", "INVALID_DIMENSION", sketch="B", type="angle", entities=lineas, value=valor)
    assert "0 y 180" in r["mensaje"]


def test_b90_angulo_con_la_misma_linea_dos_veces(s):
    _, lineas = curvas(s)
    sin_cambio(s, "add_dimension", "INVALID_DIMENSION", sketch="B", type="angle", entities=[lineas[0], lineas[0]])
    sin_cambio(s, "add_dimension", "INVALID_DIMENSION", sketch="B", type="angle", entities=[lineas[0], lineas[0]],
               value=30)


def test_b90_angulo_valido_sigue_andando(s):
    _, lineas = curvas(s)
    d = ok(s, "add_dimension", sketch="B", type="angle", entities=lineas)["result"]["dimension"]
    assert 0 < d["value"] < 180
    ok(s, "edit_dimension", dimension=d["id"], value=45)
    falla(s, "edit_dimension", "INVALID_DIMENSION", dimension=d["id"], value=180)


# ---------------------------------------------------------------- B-91
@pytest.mark.parametrize("kind", ["edge", "circunscrito", "foo"])
def test_b91_poligono_de_spec_con_kind_desconocido(kind):
    s = api.Sesion()
    sin_cambio(s, "sketch_from_spec", "INVALID_SPEC",
               entities=[{"type": "polygon", "sides": 6, "radius": 10, "kind": kind}])


def test_b91_poligono_de_spec_circunscrito_sigue_andando():
    s = api.Sesion()
    r = ok(s, "sketch_from_spec", entities=[{"type": "polygon", "sides": 6, "radius": 10, "kind": "circumscribed"}])
    assert r["result"]["profiles"] == 1


def test_b91_spec_con_construction_no_booleano():
    s = api.Sesion()
    sin_cambio(s, "sketch_from_spec", "INVALID_SPEC",
               entities=[{"type": "circle", "center": [0, 0], "radius": 5, "construction": "no"}])


def test_b91_rectangulo_con_esquinas_y_tamano(s):
    sin_cambio(s, "draw_rectangle", "INVALID_ARGUMENTS", x1=0, y1=0, x2=10, y2=10, width=5, height=5)
    sin_cambio(s, "draw_rectangle", "INVALID_ARGUMENTS", x1=0, y1=0, x2=10, y2=10, center_x=1, center_y=1)


def test_b91_arco_con_centro_y_tres_puntos(s):
    sin_cambio(s, "draw_arc", "INVALID_ARGUMENTS", start_x=5, start_y=0, center_x=0, center_y=0, sweep_angle=90,
               mid_x=3, mid_y=3, end_x=0, end_y=5)
    sin_cambio(s, "draw_arc", "INVALID_ARGUMENTS", start_x=5, start_y=0, center_x=0, center_y=0, mid_x=3, mid_y=3,
               end_x=0, end_y=5)


def test_b91_circulo_con_argumentos_de_otra_forma(s):
    sin_cambio(s, "draw_circle", "INVALID_ARGUMENTS", kind="two_points", points=[[0, 0], [10, 0]], radius=3)
    sin_cambio(s, "draw_circle", "INVALID_ARGUMENTS", kind="three_points", points=[[0, 0], [10, 0], [5, 5]], radius=3)
    sin_cambio(s, "draw_circle", "INVALID_ARGUMENTS", radius=3, points=[[0, 0], [10, 0]])


def test_b91_formas_validas_siguen_andando(s):
    ok(s, "draw_rectangle", x1=0, y1=0, x2=10, y2=10)
    ok(s, "draw_arc", start_x=5, start_y=20, center_x=0, center_y=20, sweep_angle=90)
    ok(s, "draw_arc", start_x=0, start_y=40, mid_x=3, mid_y=43, end_x=6, end_y=40)
    ok(s, "draw_circle", kind="two_points", points=[[0, 60], [10, 60]])


# ---------------------------------------------------------------- B-92 y NOV-b80-2
@pytest.mark.parametrize("escala", [1e-9, 1e9])
def test_b92_transform_sketch_escala_extrema(s, escala):
    ok(s, "draw_rectangle", x1=0, y1=0, x2=10, y2=10)
    sin_cambio(s, "transform_sketch", "INVALID_ARGUMENTS", scale=escala)


def test_b92_transform_sketch_que_se_sale_de_rango(s):
    ok(s, "draw_rectangle", x1=0, y1=0, x2=1000, y2=1000)
    sin_cambio(s, "transform_sketch", "INVALID_GEOMETRY", scale=5000)


def test_b92_transform_sketch_valido_sigue_andando(s):
    ok(s, "draw_rectangle", x1=5, y1=5, x2=15, y2=15)     # lejos del origen: no queda anclado
    ok(s, "transform_sketch", scale=2)


@pytest.mark.parametrize("nombre, args", [
    ("draw_ellipse", dict(major_radius=10, minor_radius=1e-8)),
    ("draw_ellipse", dict(major_radius=1e12, minor_radius=5)),
    ("create_polygon", dict(sides=6, radius=1e12)),
    ("draw_line", dict(start_x=0, start_y=0, end_x=1e300, end_y=0)),
    ("draw_rectangle", dict(x1=0, y1=0, x2=1e12, y2=1e12)),
    ("draw_circle", dict(radius=1e12)),
    ("draw_circle", dict(radius=1e-8)),
])
def test_b92_tamano_fuera_de_rango_da_error_claro(s, nombre, args):
    r = sin_cambio(s, nombre, "INVALID_GEOMETRY", **args)
    assert "mm" in r["mensaje"]


def test_b92_set_circle_radius_fuera_de_rango(s):
    cid = ok(s, "draw_circle", radius=5)["result"]["entities"][0]["id"]
    sin_cambio(s, "set_circle_radius", "INVALID_GEOMETRY", sketch="B", curve=cid, radius=1e12)
    sin_cambio(s, "set_circle_radius", "INVALID_GEOMETRY", sketch="B", curve=cid, radius=1e-8)
    ok(s, "set_circle_radius", sketch="B", curve=cid, radius=7)


def test_b92_tamanos_grandes_pero_validos_siguen_andando(s):
    ok(s, "draw_line", start_x=0, start_y=0, end_x=900000, end_y=0)
    ok(s, "draw_circle", center_x=100, center_y=100, radius=500000)


# ---------------------------------------------------------------- B-93
def test_b93_redefinir_el_plano_con_el_id_de_find_faces():
    s = api.Sesion()
    ok(s, "create_sketch", name="Base")
    ok(s, "draw_rectangle", x1=0, y1=0, x2=20, y2=10)
    ok(s, "extrude", sketch="Base", distance=5)
    ok(s, "create_sketch", name="Otro")
    ok(s, "draw_circle", radius=2)
    cara = ok(s, "find_faces", selector=">Z")["result"]["faces"][0]["id"]
    r = ok(s, "redefine_sketch_plane", sketch="Otro", plane=cara)["result"]
    assert r["sketch"]["plane_frame"]["origin"][2] == pytest.approx(5)

"""Fase 9 del boceto (núcleo y API): Match Topology, cotas sobre copias de patrón, ejes proyectados a medida,
contorno exterior del perfil giratorio, Project Axis, pivote en la esquina del marco y topes de polígono/patrón."""
import math

import pytest

from omnicad import api
from omnicad.nucleo.contorno_giro import contorno_exterior
from omnicad.restricciones import Boceto


@pytest.fixture
def s():
    sesion = api.Sesion()
    api.llamar(sesion, "create_sketch", {"plane": "XY", "name": "B"})
    return sesion


def ok(r):
    assert r["ok"], r
    return r


def llamar(sesion, nombre, **args):
    return ok(api.llamar(sesion, nombre, args))["result"]


def falla(sesion, nombre, **args):
    r = api.llamar(sesion, nombre, args)
    assert not r["ok"], r
    return r


def boceto(sesion, sketch=None):
    return llamar(sesion, "get_sketch", sketch=sketch)


def largos(sesion):
    return sorted(e["length"] for e in boceto(sesion)["entities"] if e["type"] == "line")


# ---------------------------------------------------------------- BOC-14: Match Topology
def test_boc14_match_topology_limita_la_distancia_al_tope_sin_perder_segmentos(s):
    abajo = llamar(s, "draw_rectangle", x1=0, y1=0, x2=10, y2=4)["entities"][0]["id"]
    # hacia adentro, 3 mm colapsan los lados verticales (el alto es 4): sin Match Topology falla
    assert falla(s, "offset_sketch_curves", entity=abajo, distance=3, side_x=5, side_y=2)["error_kind"] == "INVALID_GEOMETRY"
    r = ok(api.llamar(s, "offset_sketch_curves", {"entity": abajo, "distance": 3, "side_x": 5, "side_y": 2,
                                                 "match_topology": True}))
    cota = next(k for k in boceto(s)["dimensions"] if k["type"] == "offset")
    assert cota["value"] == pytest.approx(2, abs=0.01)                  # se frena justo antes de perder un segmento
    assert len(r["result"]["entities"]) == 4 and any("Match Topology" in a for a in r["avisos"])


def test_boc14_match_topology_no_toca_un_desfase_que_ya_conserva_la_topologia(s):
    abajo = llamar(s, "draw_rectangle", x1=0, y1=0, x2=10, y2=4)["entities"][0]["id"]
    r = ok(api.llamar(s, "offset_sketch_curves", {"entity": abajo, "distance": 1, "side_x": 5, "side_y": 2,
                                                 "match_topology": True}))
    cota = next(k for k in boceto(s)["dimensions"] if k["type"] == "offset")
    assert cota["value"] == pytest.approx(1) and cota["expression"] in ("1", "1.0") and not r["avisos"]


def test_boc14_match_topology_en_un_circulo_hacia_adentro(s):
    c = llamar(s, "draw_circle", radius=5)["entities"][0]["id"]
    llamar(s, "offset_sketch_curves", entity=c, distance=8, side_x=0, side_y=0, match_topology=True)
    radios = sorted(e["radius"] for e in boceto(s)["entities"] if e["type"] == "circle")
    assert radios[0] == pytest.approx(0, abs=0.02) and radios[0] > 0 and radios[1] == pytest.approx(5)


# ---------------------------------------------------------------- BOC-16: cotas sobre copias de patrón
def test_boc16_editar_el_patron_conserva_la_cota_sobre_una_copia_y_avisa_la_que_se_pierde(s):
    c = llamar(s, "draw_circle", radius=1)["entities"][0]["id"]
    r = llamar(s, "sketch_rectangular_pattern", entities=[c], count1=3, distance1=20)
    centro = r["instances"]["1"][1]                                     # centro de la copia en x = 20
    p = llamar(s, "draw_point", x=20, y=10)["points"][0]
    llamar(s, "add_dimension", sketch="B", type="distance", entities=[p, centro], value=10)
    llamar(s, "add_constraint", sketch="B", type="vertical", entities=[p, centro])
    r2 = ok(api.llamar(s, "edit_sketch_pattern", {"pattern": r["pattern"], "count1": 4, "distance1": 30}))
    nuevo = r2["result"]["instances"]["1"][1]
    info = boceto(s)
    cota = next(k for k in info["dimensions"] if k["type"] == "distance")
    assert set(cota["entities"]) == {p, nuevo} and cota["value"] == pytest.approx(10)
    assert any(k["type"] == "vertical" and set(k["entities"]) == {p, nuevo} for k in info["constraints"])
    xy = {q["id"]: (q["x"], q["y"]) for q in info["points"]}
    assert xy[nuevo] == pytest.approx((20, 0)) and xy[p] == pytest.approx((20, 10))
    assert r2["result"]["lost_references"] == []
    r3 = ok(api.llamar(s, "edit_sketch_pattern", {"pattern": r["pattern"], "count1": 2}))   # la copia 1 deja de existir
    info = boceto(s)
    assert not any(k["type"] == "distance" for k in info["dimensions"])
    assert len(r3["result"]["lost_references"]) == 2 and r3["avisos"]


# ---------------------------------------------------------------- BOC-17: eje y traza a la medida del boceto
def test_boc17_eje_proyectado_a_la_medida_de_la_geometria_del_boceto(s):
    llamar(s, "draw_rectangle", x1=0, y1=0, x2=300, y2=50)
    llamar(s, "project_to_sketch", references=["X"])
    eje = max(largos(s))
    assert eje == pytest.approx(2 * 1.1 * math.hypot(300, 50), abs=1e-3)        # centrado en el origen, 10 % de margen


def test_boc17_eje_proyectado_a_la_medida_del_modelo_y_sin_nada_100_mm():
    s = api.Sesion()
    llamar(s, "create_box", length=500, width=10, height=10)
    llamar(s, "create_sketch", plane="XY")
    llamar(s, "project_to_sketch", references=["X"])
    assert largos(s) == pytest.approx([2 * 1.1 * math.hypot(250, 5)], abs=1e-3)
    vacio = api.Sesion()
    llamar(vacio, "create_sketch", plane="XY")
    llamar(vacio, "project_to_sketch", references=["XZ"])
    assert largos(vacio) == pytest.approx([200])


def test_boc17_el_eje_crece_con_el_boceto_al_recalcular(s):
    llamar(s, "project_to_sketch", references=["Y"])
    assert largos(s) == pytest.approx([200])
    llamar(s, "draw_line", start_x=0, start_y=0, end_x=0, end_y=400)
    assert max(largos(s)) == pytest.approx(2 * 1.1 * 400, abs=1e-3)


# ---------------------------------------------------------------- BOC-18: contorno exterior, Project Axis, re-vincular
def test_boc18_contorno_exterior_descarta_las_aristas_internas():
    # (h, r) sobre el eje x: rectángulo h 0..10, r 2..6 más una línea interna en r = 4 que no debe quedar
    eje = ((0.0, 0.0), (1.0, 0.0))
    segs = [((0, 6), (10, 6)), ((0, 2), (10, 2)), ((0, 2), (0, 6)), ((10, 2), (10, 6)), ((0, 4), (10, 4))]
    lineas = contorno_exterior([("linea", None, a, b) for a, b in segs], eje)
    pts = {tuple(round(v, 9) for v in q) for prim in lineas for q in prim[2:4]}
    assert pts == {(0, 2), (0, 6), (10, 6), (10, 2)}
    assert sum(math.dist(p[2], p[3]) for p in lineas) == pytest.approx(4 + 10 + 4)


def test_boc18_contorno_exterior_con_escalon_y_cruce():
    eje = ((0.0, 0.0), (1.0, 0.0))
    # escalón: r 5 en h 0..4 y r 3 en h 4..10 (frente vertical en h 4); dos segmentos que se cruzan en h 15
    segs = [((0, 5), (4, 5)), ((4, 3), (4, 5)), ((4, 3), (10, 3)), ((10, 1), (20, 5)), ((10, 5), (20, 1))]
    lineas = contorno_exterior([("linea", None, a, b) for a, b in segs], eje)
    pts = {tuple(round(v, 6) for v in q) for prim in lineas for q in prim[2:4]}
    assert {(0, 5), (4, 5), (4, 3), (10, 3), (15, 3), (20, 5)} <= pts and (10, 1) not in pts and (20, 1) not in pts


def test_boc18_perfil_giratorio_de_una_caja_solo_el_contorno():
    s = api.Sesion()
    llamar(s, "create_box", length=20, width=20, height=10)
    llamar(s, "create_cylinder", radius=3, height=10)
    llamar(s, "boolean_operation", target="op1.c1", tools=["op2.c1"], operation="cut")
    llamar(s, "create_sketch", plane="XZ")
    llamar(s, "project_spun_profile", axis="Z", bodies=["op1.c1"], tolerance=0.01)
    xs = sorted({round(abs(p["x"]), 3) for p in boceto(s)["points"]})
    # la silueta va hasta la esquina (10·√2) y el frente de las tapas arranca en r = 10; el agujero (r = 3) no queda
    assert xs == pytest.approx([10, round(10 * math.sqrt(2), 3)], abs=0.02)
    todas = api.Sesion()
    llamar(todas, "create_box", length=20, width=20, height=10)
    llamar(todas, "create_cylinder", radius=3, height=10)
    llamar(todas, "boolean_operation", target="op1.c1", tools=["op2.c1"], operation="cut")
    llamar(todas, "create_sketch", plane="XZ")
    llamar(todas, "project_spun_profile", axis="Z", bodies=["op1.c1"], tolerance=0.01, outer_contour=False)
    assert min(abs(p["x"]) for p in boceto(todas)["points"]) == pytest.approx(3, abs=0.02)


def test_boc18_project_axis_proyecta_el_eje_con_vinculo():
    s = api.Sesion()
    llamar(s, "create_cylinder", radius=5, height=30)
    llamar(s, "create_sketch", plane="XZ")
    r = llamar(s, "project_spun_profile", axis="Z", bodies=["Cuerpo1"], project_axis=True)
    assert r["projection"] == 1 and r["axis_projection"] == 2
    info = boceto(s)
    eje = next(e for e in info["entities"] if e["type"] == "line" and abs(e["start"][0]) < 1e-9 and abs(e["end"][0]) < 1e-9)
    assert eje["length"] > 30 and [p["id"] for p in info["projections"]] == [1, 2]


def test_boc18_relink_de_un_perfil_giratorio_perdido():
    s = api.Sesion()
    llamar(s, "create_cylinder", radius=5, height=30)
    llamar(s, "create_cylinder", radius=8, height=30)
    llamar(s, "create_sketch", plane="XZ")
    llamar(s, "project_spun_profile", axis="Z", bodies=["op1.c1"])
    s.doc.suprimir("op1")
    assert boceto(s)["projections"][0]["lost"] is True
    llamar(s, "manage_lost_projections", action="relink", projection=1, bodies=["op2.c1"])
    assert max(p["x"] for p in boceto(s)["points"]) == pytest.approx(8, abs=0.1)


# ---------------------------------------------------------------- BOC-20: pivote en la esquina del marco
def test_boc20_esquinas_del_marco_del_texto_para_el_pivote():
    b = Boceto()
    t = b.agregar_texto((10, 20), "Hola", altura=5)
    b.agregar_marco_texto(t, 30, 8)
    assert b.esquina_marco(t, "bl") == pytest.approx((10, 20))
    assert b.esquina_marco(t, "tr") == pytest.approx((40, 28))
    assert b.esquina_marco(t, "center") == pytest.approx((25, 24))
    b.girar_texto(t, 90, pivote=b.esquina_marco(t, "tr"))
    assert b.esquina_marco(t, "tr") == pytest.approx((40, 28))                   # gira alrededor de esa esquina
    sin_marco = b.agregar_texto((0, 0), "X", altura=5)
    with pytest.raises(ValueError):
        b.esquina_marco(sin_marco, "tl")


# ---------------------------------------------------------------- BOC-29: topes propios documentados
def test_boc29_topes_de_poligono_y_patron(s):
    assert len(llamar(s, "create_polygon", sides=64, radius=50)["entities"]) == 65      # 64 lados + círculo guía
    assert falla(s, "create_polygon", sides=65, radius=50)["error_kind"] == "INVALID_GEOMETRY"
    p = llamar(s, "draw_point", x=0, y=0)["points"][0]
    assert falla(s, "sketch_rectangular_pattern", entities=[p], count1=202, distance1=10)["error_kind"] == "INVALID_ARGUMENTS"
    assert falla(s, "sketch_circular_pattern", entities=[p], count=202)["error_kind"] == "INVALID_ARGUMENTS"
    assert len(llamar(s, "sketch_rectangular_pattern", entities=[p], count1=201, distance1=10)["instances"]) == 200

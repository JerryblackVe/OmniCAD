# -*- coding: utf-8 -*-
"""Herramientas de boceto que tenía el editor de la interfaz y le faltaban al MCP (hallazgo de la prueba 2 del
2026-10-09): elipse, ranura, polígono totalmente acotado, empalme y chaflán de boceto, recortar / alargar / partir,
desfase paramétrico, simetría, patrones, proyectar, tipo de línea, editar cotas y restringir automáticamente."""
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
    doc = sesion.doc
    return json.dumps(doc.a_dict(), sort_keys=True), len(doc._deshacer)


def boceto(sesion, sketch=None):
    return llamar(sesion, "get_sketch", sketch=sketch)


def areas(sesion, sketch=None):
    return sorted(p["area"] for p in boceto(sesion, sketch)["profiles"])


def por_id(sesion, sketch=None):
    return {e["id"]: e for e in boceto(sesion, sketch)["entities"]}


def rectangulo(sesion, x1=0, y1=0, x2=40, y2=20):
    """Ids de las 4 líneas: abajo, derecha, arriba, izquierda."""
    return [e["id"] for e in llamar(sesion, "draw_rectangle", x1=x1, y1=y1, x2=x2, y2=y2)["entities"]]


def rectangulo_acotado(sesion):
    """Rectángulo 40 × 20 totalmente restringido (esquina fija + dos cotas): sin eso, un cambio de cota puede
    estirarlo y el área no queda determinada."""
    lados = rectangulo(sesion)
    p0 = next(e for e in boceto(sesion)["entities"] if e["id"] == lados[0])["points"][0]
    llamar(sesion, "add_constraint", sketch="B", type="fix", entities=[p0])
    llamar(sesion, "add_dimension", sketch="B", type="distance", entities=[lados[0]], value=40)
    r = llamar(sesion, "add_dimension", sketch="B", type="distance", entities=[lados[1]], value=20)
    assert r["status"] == "fully_constrained"
    return lados


# ---------------------------------------------------------------- polígono totalmente acotado
def _area_poligono(n, r, circunscrito):
    return n * r * r * math.tan(math.pi / n) if circunscrito else n * r * r * math.sin(2 * math.pi / n) / 2


@pytest.mark.parametrize("lados, kind, giro, cx, cy", [
    (6, "inscribed", 0, 0, 0), (6, "circumscribed", 17, 30, 5), (5, "circumscribed", 90, -30, 0),
    (4, "inscribed", 200, 0, -30), (3, "inscribed", 270, 12, 0)])
def test_poligono_totalmente_acotado(s, lados, kind, giro, cx, cy):
    r = llamar(s, "create_polygon", sides=lados, radius=10, center_x=cx, center_y=cy, rotation=giro, kind=kind,
               fully_constrained=True)
    assert (r["status"], r["dof"], r["profiles"]) == ("fully_constrained", 0, 1)
    assert r["dimensions"][0]["type"] == "radius" and r["dimensions"][0]["expression"] == "10.0"
    assert areas(s) == [pytest.approx(_area_poligono(lados, 10, kind == "circumscribed"), abs=1e-3)]
    centro = boceto(s)["profiles"][0]["centroid"]
    assert centro == pytest.approx([cx, cy], abs=1e-6)


@pytest.mark.parametrize("lados, kind", [(6, "inscribed"), (6, "circumscribed"), (5, "circumscribed"),
                                         (8, "circumscribed")])
def test_poligono_sin_acotar_sigue_con_4_grados(s, lados, kind):
    """Centro, tamaño y giro. Circunscrito con lados pares daba 5: lados iguales y tangentes no lo hacían regular."""
    r = llamar(s, "create_polygon", sides=lados, radius=10, kind=kind)
    assert (r["status"], r["dof"]) == ("under_constrained", 4) and "dimensions" not in r


def test_poligono_acotado_sigue_a_un_parametro(s):
    """Tuerca hexagonal: radius = entrecaras / 2 en un hexágono circunscrito; al cambiar el parámetro, cambia."""
    llamar(s, "create_parameter", name="entrecaras", expression="10 mm")
    r = llamar(s, "create_polygon", sides=6, radius="entrecaras / 2", kind="circumscribed", rotation=30,
               fully_constrained=True)
    assert r["dof"] == 0 and r["dimensions"][0]["expression"] == "entrecaras / 2"
    assert areas(s) == [pytest.approx(6 * 25 * math.tan(math.pi / 6), abs=1e-3)]
    llamar(s, "set_parameter", name="entrecaras", expression="13 mm")
    assert areas(s) == [pytest.approx(6 * 6.5 ** 2 * math.tan(math.pi / 6), abs=1e-3)]
    assert boceto(s)["status"] == "fully_constrained"


def test_dos_poligonos_acotados_comparten_el_origen(s):
    llamar(s, "create_polygon", sides=6, radius=5, center_x=20, fully_constrained=True)
    r = llamar(s, "create_polygon", sides=4, radius=5, center_x=-20, rotation=45, fully_constrained=True)
    assert r["dof"] == 0
    fijos = [p for p in boceto(s)["points"] if p["fixed"]]
    assert len(fijos) == 1 and (fijos[0]["x"], fijos[0]["y"]) == (0, 0)


def test_poligono_acotado_en_spec(s):
    r = llamar(s, "sketch_from_spec", plane="XY", entities=[
        {"type": "polygon", "id": "hex", "sides": 6, "radius": 8, "center": [10, 10], "rotation": 15,
         "fully_constrained": True}])
    assert (r["status"], r["dof"], r["profiles"]) == ("fully_constrained", 0, 1)


# ---------------------------------------------------------------- elipse y ranura
def test_elipse(s):
    r = llamar(s, "draw_ellipse", major_radius=20, minor_radius=10, center_x=5, center_y=-3, angle=30)
    assert [e["type"] for e in r["entities"]] == ["ellipse", "line", "line"] and r["profiles"] == 1
    assert areas(s) == [pytest.approx(math.pi * 200, abs=1e-3)]
    e = por_id(s)[r["entities"][0]["id"]]
    assert (e["center"], e["major_radius"], e["minor_radius"], e["angle"]) == ([5, -3], 20, 10, 30)
    assert e["major_point"] == pytest.approx([5 + 20 * math.cos(math.radians(30)), -3 + 10], abs=1e-4)
    ejes = [por_id(s)[x["id"]] for x in r["entities"][1:]]
    assert all(x["construction"] for x in ejes) and sorted(x["length"] for x in ejes) == [20, 40]
    assert falla(s, "draw_ellipse", major_radius=20, minor_radius=0)["error_kind"] == "INVALID_GEOMETRY"
    assert falla(s, "draw_ellipse", major_radius=math.nan, minor_radius=3)["error_kind"] == "INVALID_ARGUMENTS"


@pytest.mark.parametrize("kind, puntos, ancho, area", [
    ("center_to_center", [[0, 0], [30, 0]], 10, 300 + 25 * math.pi),
    ("overall", [[0, 0], [40, 0]], 10, 300 + 25 * math.pi),
    ("center_point", [[0, 0], [15, 0]], 10, 300 + 25 * math.pi),
    ("arc_center", [[0, 0], [20, 0], [0, 20]], 4, 10 * math.pi * 4 + 4 * math.pi),     # cuarto de vuelta, R = 20
    ("arc_three_points", [[20, 0], [-20, 0], [0, 20]], 4, 20 * math.pi * 4 + 4 * math.pi)])  # media vuelta
def test_ranuras(s, kind, puntos, ancho, area):
    r = llamar(s, "draw_slot", points=puntos, width=ancho, kind=kind)
    assert [e["type"] for e in r["entities"]][4] in ("line", "arc") and r["profiles"] == 1
    assert areas(s) == [pytest.approx(area, abs=1e-3)]
    eje = por_id(s)[r["entities"][4]["id"]]
    assert eje["construction"] is True


def test_ranura_invalida(s):
    antes = foto(s)
    assert falla(s, "draw_slot", points=[[0, 0], [30, 0]], width=0)["error_kind"] == "INVALID_GEOMETRY"
    assert falla(s, "draw_slot", points=[[0, 0]], width=4)["error_kind"] == "INVALID_GEOMETRY"
    assert falla(s, "draw_slot", points=[[0, 0], [10, 0]], width=12, kind="overall")["error_kind"] == "INVALID_GEOMETRY"
    assert falla(s, "draw_slot", points=[[0, 0], [5, 0], [0, 5]], width=12,
                 kind="arc_center")["error_kind"] == "INVALID_GEOMETRY"
    assert foto(s) == antes


def test_ranura_y_elipse_en_spec_se_citan(s):
    r = llamar(s, "sketch_from_spec", plane="XY", entities=[
        {"type": "slot", "id": "r", "points": [[0, 0], [30, 0]], "width": 10},
        {"type": "ellipse", "id": "e", "center": [0, 40], "major_radius": 12, "minor_radius": 6}],
        dimensions=[{"type": "radius", "entities": ["r.end1"], "value": 4},
                    {"type": "distance", "entities": ["r.axis"], "value": 30}])
    assert r["profiles"] == 2 and {"r.side1", "r.end2", "r.axis", "r.center1", "e", "e.major"} <= set(r["handles"])
    assert areas(s, r["sketch"]["id"]) == pytest.approx(sorted([300 * 0.8 + 16 * math.pi, 72 * math.pi]), abs=1e-3)


# ---------------------------------------------------------------- empalme y chaflán
def test_empalme_y_chaflan_de_boceto(s):
    abajo, derecha, arriba, izquierda = rectangulo_acotado(s)
    r = llamar(s, "sketch_fillet", entity1=abajo, entity2=derecha, radius=5)
    assert [e["type"] for e in r["entities"]] == ["arc"] and r["dimensions"][0]["type"] == "radius"
    assert r["status"] == "fully_constrained"                # las cotas de largo pasan al vértice virtual
    assert areas(s) == [pytest.approx(800 - (25 - 25 * math.pi / 4), abs=1e-3)]
    r = llamar(s, "sketch_chamfer", line1=arriba, line2=izquierda, distance=4, distance2=6)
    assert [d["expression"] for d in r["dimensions"]] == ["4.0", "6.0"] and r["status"] == "fully_constrained"
    assert areas(s) == [pytest.approx(800 - (25 - 25 * math.pi / 4) - 12, abs=1e-3)]


def test_empalme_con_parametro_y_chaflan_de_angulo(s):
    llamar(s, "create_parameter", name="r_esquina", expression="3 mm")
    abajo, derecha, arriba, izquierda = rectangulo_acotado(s)
    llamar(s, "sketch_fillet", entity1=abajo, entity2=derecha, radius="r_esquina")
    llamar(s, "sketch_chamfer", line1=arriba, line2=izquierda, distance=4, angle=45)
    assert areas(s) == [pytest.approx(800 - 9 * (1 - math.pi / 4) - 8, abs=1e-3)]
    llamar(s, "set_parameter", name="r_esquina", expression="6 mm")
    assert areas(s) == [pytest.approx(800 - 36 * (1 - math.pi / 4) - 8, abs=1e-3)]


def test_empalme_y_chaflan_invalidos_no_cambian_nada(s):
    abajo, derecha, _arriba, _izq = rectangulo(s)
    c = llamar(s, "draw_circle", radius=3, center_x=100)["entities"][0]["id"]
    antes = foto(s)
    assert falla(s, "sketch_fillet", entity1=abajo, entity2=derecha, radius=50)["error_kind"] == "INVALID_GEOMETRY"
    assert falla(s, "sketch_fillet", entity1=abajo, entity2=derecha, radius=0)["error_kind"] == "INVALID_DIMENSION"
    assert falla(s, "sketch_fillet", entity1=abajo, entity2=999, radius=1)["error_kind"] == "ENTITY_NOT_FOUND"
    assert falla(s, "sketch_fillet", entity1=abajo, entity2=abajo, radius=1)["error_kind"] == "INVALID_GEOMETRY"
    assert falla(s, "sketch_chamfer", line1=abajo, line2=c, distance=1)["error_kind"] == "INVALID_GEOMETRY"
    assert falla(s, "sketch_chamfer", line1=abajo, line2=derecha, distance=1, distance2=2,
                 angle=30)["error_kind"] == "INVALID_ARGUMENTS"
    assert falla(s, "sketch_chamfer", line1=abajo, line2=derecha, distance=1, angle=190)["error_kind"] == \
        "INVALID_DIMENSION"
    assert foto(s) == antes


def test_empalme_usa_la_geometria_resuelta(s):
    """El boceto guardado tiene 40 de ancho, pero una cota lo lleva a 60: el empalme se calcula sobre 60."""
    abajo, derecha, _arriba, _izq = rectangulo(s)
    llamar(s, "add_dimension", sketch="B", type="distance", entities=[abajo], value=60)
    llamar(s, "sketch_fillet", entity1=abajo, entity2=derecha, radius=5)
    assert areas(s) == [pytest.approx(1200 - (25 - 25 * math.pi / 4), abs=1e-3)]


# ---------------------------------------------------------------- recortar, alargar, partir
def test_recortar_alargar_y_partir(s):
    h = llamar(s, "draw_line", start_x=0, start_y=0, end_x=20, end_y=0)["entities"][0]["id"]
    v = llamar(s, "draw_line", start_x=10, start_y=-5, end_x=10, end_y=5)["entities"][0]["id"]
    r = llamar(s, "trim_sketch_curve", entity=v, x=10, y=-3)
    assert r["mode"] == "trim" and r["deleted"] is False
    assert sorted([por_id(s)[v]["start"], por_id(s)[v]["end"]]) == [[10, 0], [10, 5]]
    # alargar: una línea que no llega a h
    w = llamar(s, "draw_line", start_x=15, start_y=8, end_x=15, end_y=3)["entities"][0]["id"]
    llamar(s, "trim_sketch_curve", entity=w, x=15, y=3, mode="extend")
    assert por_id(s)[w]["end"] == [15, 0] and por_id(s)[w]["length"] == 8
    # partir h en el cruce más cercano al clic (x = 10 y x = 15 la cortan)
    r = llamar(s, "trim_sketch_curve", entity=h, x=5, y=0, mode="break")
    assert len(r["pieces"]) == 2
    largos = sorted(por_id(s)[i]["length"] for i in r["pieces"])
    assert largos == [10, 10]
    # una línea suelta que no cruza nada se borra entera
    z = llamar(s, "draw_line", start_x=50, start_y=50, end_x=60, end_y=50)["entities"][0]["id"]
    r = llamar(s, "trim_sketch_curve", entity=z, x=55, y=50)
    assert r["deleted"] is True and r["entities_deleted"] == [z] and z not in por_id(s)


def test_recortar_usa_la_geometria_resuelta(s):
    """La línea guardada mide 20, pero su cota la lleva a 40 y la vertical en x = 30 la cruza solo así: partiendo
    del boceto guardado no había cruce y recortar borraba la línea entera."""
    r = llamar(s, "draw_line", start_x=0, start_y=50, end_x=20, end_y=50)
    h, p1 = r["entities"][0]["id"], r["points"][0]
    llamar(s, "add_constraint", sketch="B", type="fix", entities=[p1])
    llamar(s, "add_constraint", sketch="B", type="horizontal", entities=[h])
    llamar(s, "add_dimension", sketch="B", type="distance", entities=[h], value=40)
    llamar(s, "draw_line", start_x=30, start_y=45, end_x=30, end_y=55)
    r = llamar(s, "trim_sketch_curve", entity=h, x=35, y=50)
    assert r["deleted"] is False and (por_id(s)[h]["start"], por_id(s)[h]["end"]) == ([0, 50], [30, 50])


def test_recortar_errores(s):
    p = llamar(s, "draw_point", x=1, y=1)["points"][0]
    llamar(s, "draw_line", start_x=0, start_y=0, end_x=20, end_y=0)
    antes = foto(s)
    assert falla(s, "trim_sketch_curve", entity=999, x=0, y=0)["error_kind"] == "ENTITY_NOT_FOUND"
    assert falla(s, "trim_sketch_curve", entity=p, x=0, y=0)["error_kind"] == "INVALID_GEOMETRY"
    assert falla(s, "trim_sketch_curve", entity=p + 1, x=math.inf, y=0)["error_kind"] == "INVALID_ARGUMENTS"
    assert foto(s) == antes


# ---------------------------------------------------------------- desfase paramétrico
def test_desfase_de_cadena_afuera_adentro_y_con_parametro(s):
    abajo = rectangulo_acotado(s)[0]
    r = llamar(s, "offset_sketch_curves", entity=abajo, distance=2)
    assert len(r["entities"]) == 4 and r["dimensions"][0]["type"] == "offset"
    assert areas(s) == pytest.approx([44 * 24 - 800, 800], abs=1e-3)
    llamar(s, "undo")
    llamar(s, "offset_sketch_curves", entity=abajo, distance=-2)
    assert areas(s) == pytest.approx([800 - 36 * 16, 36 * 16], abs=1e-3)
    llamar(s, "undo")
    llamar(s, "create_parameter", name="pared", expression="3 mm")
    r = llamar(s, "offset_sketch_curves", entity=abajo, distance="pared")
    assert r["dimensions"][0]["expression"] == "pared"
    llamar(s, "set_parameter", name="pared", expression="1 mm")
    assert areas(s) == pytest.approx([42 * 22 - 800, 800], abs=1e-3) and boceto(s)["status"] == "fully_constrained"


def test_desfase_de_circulo_con_lado(s):
    c = llamar(s, "draw_circle", radius=5)["entities"][0]["id"]
    llamar(s, "offset_sketch_curves", entity=c, distance=2)
    assert areas(s) == pytest.approx([24 * math.pi, 25 * math.pi], abs=1e-3)
    llamar(s, "offset_sketch_curves", entity=c, distance=2, side_x=0, side_y=1)     # punto adentro
    assert areas(s)[0] == pytest.approx(9 * math.pi, abs=1e-3)
    antes = foto(s)
    assert falla(s, "offset_sketch_curves", entity=c, distance=0)["error_kind"] == "INVALID_DIMENSION"
    assert falla(s, "offset_sketch_curves", entity=c, distance=2, side_x=1)["error_kind"] == "INVALID_ARGUMENTS"
    assert falla(s, "offset_sketch_curves", entity=c, distance=6, side_x=0, side_y=0)["error_kind"] == \
        "INVALID_GEOMETRY"
    assert foto(s) == antes


# ---------------------------------------------------------------- simetría y patrones
def test_simetria_sigue_al_original(s):
    eje = llamar(s, "draw_line", start_x=0, start_y=-10, end_x=0, end_y=10, construction=True)["entities"][0]["id"]
    llamar(s, "add_constraint", sketch="B", type="fix", entities=[eje])
    c = llamar(s, "draw_circle", radius=2, center_x=5, center_y=3)
    cid, centro = c["entities"][0]["id"], c["points"][0]
    r = llamar(s, "mirror_sketch", entities=[cid], axis=eje)
    copia = r["entities"][0]["id"]
    assert por_id(s)[copia]["center"] == [-5, 3] and r["profiles"] == 2
    d = llamar(s, "add_dimension", sketch="B", type="radius", entities=[cid], value=2)["dimension"]["id"]
    llamar(s, "edit_dimension", dimension=d, value=3)
    r = llamar(s, "move_sketch_point", point=centro, x=8, y=4)
    assert r["reached"] is True and r["point"] == {"id": centro, "x": 8, "y": 4}
    assert por_id(s)[copia]["center"] == [-8, 4] and por_id(s)[copia]["radius"] == 3
    antes = foto(s)
    assert falla(s, "mirror_sketch", entities=[cid], axis=cid)["error_kind"] == "INVALID_GEOMETRY"
    assert falla(s, "mirror_sketch", entities=[], axis=eje)["error_kind"] == "INVALID_ARGUMENTS"
    assert foto(s) == antes


def test_patron_rectangular_y_circular(s):
    c = llamar(s, "draw_circle", radius=1, center_x=10, center_y=0)["entities"][0]["id"]
    r = llamar(s, "sketch_rectangular_pattern", entities=[c], count1=3, distance1=20, count2=2, distance2=5)
    assert len(r["entities"]) == 5 and r["profiles"] == 6
    centros = sorted(tuple(e["center"]) for e in boceto(s)["entities"])
    assert centros == [(10, 0), (10, 5), (20, 0), (20, 5), (30, 0), (30, 5)]
    llamar(s, "undo")
    r = llamar(s, "sketch_rectangular_pattern", entities=[c], count1=3, distance1=4, spacing="spacing", angle=90,
               symmetric=True)
    assert sorted(tuple(e["center"]) for e in boceto(s)["entities"]) == [(10, -4), (10, 0), (10, 4)]
    llamar(s, "undo")
    r = llamar(s, "sketch_circular_pattern", entities=[c], count=6)
    assert r["profiles"] == 6
    radios = {round(math.hypot(*e["center"]), 3) for e in boceto(s)["entities"]}
    angulos = sorted(round(math.degrees(math.atan2(e["center"][1], e["center"][0])) % 360, 2)
                     for e in boceto(s)["entities"])
    assert radios == {10} and angulos == [0, 60, 120, 180, 240, 300]
    # las copias siguen al radio del original (restricción «igual»)
    d = llamar(s, "add_dimension", sketch="B", type="radius", entities=[c], value=1)["dimension"]["id"]
    llamar(s, "edit_dimension", dimension=d, value=2)
    assert {e["radius"] for e in boceto(s)["entities"]} == {2}


def test_patron_con_centro_en_un_punto_y_topes(s):
    p = llamar(s, "draw_point", x=50, y=50)["points"][0]
    c = llamar(s, "draw_circle", radius=1, center_x=60, center_y=50)["entities"][0]["id"]
    llamar(s, "sketch_circular_pattern", entities=[c], count=3, center_point=p, total_angle=180)
    assert sorted(tuple(e["center"]) for e in boceto(s)["entities"]) == [(40, 50), (50, 60), (60, 50)]
    lineas = rectangulo(s, 100, 100, 102, 101)
    antes = foto(s)
    assert falla(s, "sketch_circular_pattern", entities=[c], count=300)["error_kind"] == "INVALID_ARGUMENTS"
    r = falla(s, "sketch_rectangular_pattern", entities=lineas, count1=60, distance1=100)   # 59 × 4 puntos
    assert r["error_kind"] == "INVALID_ARGUMENTS" and "200" in r["mensaje"]
    assert falla(s, "sketch_rectangular_pattern", entities=[c], count1=1, distance1=5)["error_kind"] == \
        "INVALID_ARGUMENTS"
    assert falla(s, "sketch_circular_pattern", entities=[c], count=4, center_point=c)["error_kind"] == \
        "ENTITY_NOT_FOUND"
    assert falla(s, "sketch_circular_pattern", entities=[999], count=4)["error_kind"] == "ENTITY_NOT_FOUND"
    assert foto(s) == antes


# ---------------------------------------------------------------- editar cotas y restringir automáticamente
def test_editar_cota(s):
    abajo, derecha, _arriba, _izq = rectangulo(s)
    p0 = boceto(s)["entities"][0]["points"][0]
    llamar(s, "add_constraint", sketch="B", type="fix", entities=[p0])
    d = llamar(s, "add_dimension", sketch="B", type="distance", entities=[abajo], value=40)["dimension"]["id"]
    llamar(s, "add_dimension", sketch="B", type="distance", entities=[derecha], value=20)
    n = len(s.doc._deshacer)
    r = llamar(s, "edit_dimension", dimension=d, value=55)
    assert r["dimension"]["previous_expression"] == "40.0" and r["dimension"]["value"] == 55
    assert r["status"] == "fully_constrained" and len(s.doc._deshacer) == n + 1
    assert areas(s) == [pytest.approx(55 * 20, abs=1e-3)]
    llamar(s, "create_parameter", name="largo", expression="70 mm")
    llamar(s, "edit_dimension", dimension=d, value="largo")
    llamar(s, "set_parameter", name="largo", expression="80 mm")
    assert areas(s) == [pytest.approx(80 * 20, abs=1e-3)]
    llamar(s, "undo")
    llamar(s, "undo")
    assert areas(s) == [pytest.approx(55 * 20, abs=1e-3)]


def test_editar_cota_invalida_no_cambia_nada(s):
    abajo, derecha, arriba, izquierda = rectangulo(s)
    d = llamar(s, "add_dimension", sketch="B", type="distance", entities=[abajo], value=40)["dimension"]["id"]
    a = llamar(s, "add_dimension", sketch="B", type="angle", entities=[abajo, derecha])["dimension"]["id"]
    antes = foto(s)
    assert falla(s, "edit_dimension", dimension=d, value=-1)["error_kind"] == "INVALID_DIMENSION"
    assert falla(s, "edit_dimension", dimension=d, value=1e9)["error_kind"] == "INVALID_DIMENSION"
    assert falla(s, "edit_dimension", dimension=a, value=200)["error_kind"] == "INVALID_DIMENSION"
    assert falla(s, "edit_dimension", dimension=a, value=60)["error_kind"] == "SKETCH_OVERCONSTRAINED"
    assert falla(s, "edit_dimension", dimension=abajo, value=3)["error_kind"] == "ENTITY_NOT_FOUND"
    assert falla(s, "edit_dimension", dimension=d, value="nada * 2")["error_kind"] == "INVALID_EXPRESSION"
    assert foto(s) == antes


def test_mover_punto_como_arrastrar(s):
    """move_sketch_point lleva el punto a (x, y) aunque esté atado a otra geometría libre; si una cota no lo deja,
    queda lo más cerca posible y lo dice (reached = false)."""
    r = llamar(s, "draw_line", start_x=0, start_y=0, end_x=10, end_y=0)
    linea, (p1, p2) = r["entities"][0]["id"], r["points"]
    r = llamar(s, "move_sketch_point", point=p2, x=0, y=7)
    assert r["reached"] is True and por_id(s)[linea]["end"] == [0, 7]
    llamar(s, "add_constraint", sketch="B", type="fix", entities=[p1])
    llamar(s, "add_dimension", sketch="B", type="distance", entities=[linea], value=10)
    r = llamar(s, "move_sketch_point", point=p2, x=30, y=0)
    assert r["reached"] is False and r["point"]["x"] == pytest.approx(10, abs=1e-4)
    assert por_id(s)[linea]["length"] == pytest.approx(10, abs=1e-4) and r["dof"] == 1      # todavía puede girar
    assert falla(s, "move_sketch_point", point=p1, x=1, y=1)["error_kind"] == "INVALID_GEOMETRY"   # fijo


def test_borrar_cota_y_restriccion_existentes(s):
    """Hallazgo de la prueba 2: add_constraint / add_dimension solo agregaban; ahora se editan y se borran."""
    abajo = rectangulo(s)[0]
    d = llamar(s, "add_dimension", sketch="B", type="distance", entities=[abajo], value=40)["dimension"]["id"]
    rid = boceto(s)["constraints"][0]["id"]
    r = llamar(s, "delete_sketch_entities", entities=[d, rid])
    assert r["deleted"] == [d, rid]
    assert boceto(s)["dimensions"] == [] and rid not in {c["id"] for c in boceto(s)["constraints"]}


def test_restringir_automaticamente(s):
    rectangulo(s, 10, 10, 40, 30)
    r = llamar(s, "auto_constrain")
    assert (r["status"], r["dof"]) == ("fully_constrained", 0) and r["added"]
    assert areas(s) == [pytest.approx(600, abs=1e-6)]
    largo = next(k for k in boceto(s)["dimensions"] if k["type"] == "distance" and k["value"] == 30)
    llamar(s, "edit_dimension", dimension=largo["id"], value=50)
    assert areas(s) == [pytest.approx(1000, abs=1e-6)] and boceto(s)["status"] == "fully_constrained"


# ---------------------------------------------------------------- punto, cónica, tangente, fusión, tipo de línea
def test_circulo_tangente(s):
    a = llamar(s, "draw_line", start_x=0, start_y=0, end_x=20, end_y=0)["entities"][0]["id"]
    b = llamar(s, "draw_line", start_x=0, start_y=0, end_x=0, end_y=20)["entities"][0]["id"]
    r = llamar(s, "draw_tangent_circle", lines=[a, b], radius=3)
    c = por_id(s)[r["entities"][0]["id"]]
    assert (c["center"], c["radius"]) == ([3, 3], 3)
    assert [x["type"] for x in r["constraints"]] == ["tangent", "tangent"]
    # triángulo 30-40-50: el inscrito tiene radio (30 + 40 − 50) / 2 = 10
    llamar(s, "create_sketch", plane="XY", name="T")
    ids = [llamar(s, "draw_line", start_x=x1, start_y=y1, end_x=x2, end_y=y2)["entities"][0]["id"]
           for x1, y1, x2, y2 in ((0, 0, 30, 0), (30, 0, 0, 40), (0, 40, 0, 0))]
    r = llamar(s, "draw_tangent_circle", lines=ids)
    c = por_id(s)[r["entities"][0]["id"]]
    assert c["radius"] == pytest.approx(10) and c["center"] == pytest.approx([10, 10])
    antes = foto(s)
    assert falla(s, "draw_tangent_circle", lines=ids[:1])["error_kind"] == "INVALID_ARGUMENTS"
    assert falla(s, "draw_tangent_circle", lines=ids, radius=3)["error_kind"] == "INVALID_ARGUMENTS"
    assert falla(s, "draw_tangent_circle", lines=[ids[0], r["entities"][0]["id"]])["error_kind"] == "INVALID_GEOMETRY"
    assert foto(s) == antes


def test_conica_fusion_punto_y_tipo_de_linea(s):
    r = llamar(s, "draw_point", x=3, y=4)
    assert boceto(s)["points"][0] == {"id": r["points"][0], "x": 3, "y": 4, "fixed": False}
    a = llamar(s, "draw_line", start_x=0, start_y=0, end_x=20, end_y=0)["entities"][0]["id"]
    k = llamar(s, "draw_conic", start_x=30, start_y=10, end_x=50, end_y=10, vertex_x=40, vertex_y=20)
    con = por_id(s)[k["entities"][0]["id"]]
    assert (con["type"], con["vertex"], con["rho"]) == ("conic", [40, 20], 0.5)
    r = llamar(s, "draw_blend_curve", entity1=a, entity2=con["id"])
    f = por_id(s)[r["entities"][0]["id"]]
    assert f["type"] == "spline" and f["degree"] == 3 and f["vertices"][0] == [20, 0] and f["vertices"][-1] == [30, 10]
    assert [x["type"] for x in r["constraints"]] == ["tangent", "tangent"]
    b = llamar(s, "draw_line", start_x=0, start_y=-10, end_x=20, end_y=-10)["entities"][0]["id"]
    r = llamar(s, "draw_blend_curve", entity1=a, entity2=b, point1=[0, 0], point2=[0, -10], continuity="G2")
    f = por_id(s)[r["entities"][0]["id"]]
    assert f["degree"] == 5 and f["vertices"][0] == [0, 0] and f["vertices"][-1] == [0, -10]
    assert [x["type"] for x in r["constraints"]] == ["curvature", "curvature"]
    assert falla(s, "draw_blend_curve", entity1=a, entity2=a)["error_kind"] == "INVALID_GEOMETRY"
    assert falla(s, "draw_conic", start_x=0, start_y=0, end_x=10, end_y=0, vertex_x=5, vertex_y=0)["error_kind"] == \
        "INVALID_GEOMETRY"
    # tipo de línea: un rectángulo de construcción no forma perfil
    llamar(s, "create_sketch", plane="XY", name="L")
    lados = rectangulo(s)
    assert llamar(s, "set_line_type", entities=lados, line_type="construction")["profiles"] == 0
    assert llamar(s, "set_line_type", entities=lados, line_type="centerline")["profiles"] == 1
    assert all(e.get("centerline") for e in boceto(s)["entities"])
    assert llamar(s, "set_line_type", entities=lados, line_type="normal")["profiles"] == 1
    assert falla(s, "set_line_type", entities=[999], line_type="normal")["error_kind"] == "ENTITY_NOT_FOUND"


# ---------------------------------------------------------------- proyectar el modelo
def test_proyectar_e_intersecar():
    s = api.Sesion()
    llamar(s, "create_box", length=20, width=10, height=5)
    llamar(s, "create_construction_plane", plane="XY", offset=10, name="Arriba")
    llamar(s, "create_construction_plane", plane="XY", offset=2.5, name="Medio")
    llamar(s, "create_sketch", plane="Arriba", name="P")
    r = llamar(s, "project_to_sketch", bodies=["Cuerpo1"])
    assert len(r["entities"]) == 4 and areas(s) == [pytest.approx(200)]
    assert all(por_id(s)[e["id"]].get("projected") for e in r["entities"])
    llamar(s, "create_sketch", plane="XY", name="Q")
    assert llamar(s, "project_to_sketch", edges=">Z")["profiles"] == 1
    llamar(s, "create_sketch", plane="Medio", name="I")
    r = llamar(s, "project_to_sketch", bodies=["Cuerpo1"], mode="intersect")
    assert areas(s) == [pytest.approx(200)]
    fijos = [p for p in boceto(s)["points"] if p["fixed"]]
    assert len(fijos) == 4                                   # lo proyectado es fijo para el solver
    llamar(s, "create_sketch", plane="Arriba", name="N")
    antes = foto(s)
    assert falla(s, "project_to_sketch", bodies=["Cuerpo1"], mode="intersect")["error_kind"] == "INVALID_GEOMETRY"
    assert falla(s, "project_to_sketch")["error_kind"] == "INVALID_ARGUMENTS"
    assert falla(s, "project_to_sketch", bodies=["Fantasma"])["error_kind"] == "BODY_NOT_FOUND"
    assert foto(s) == antes


# ---------------------------------------------------------------- un paso de deshacer cada una
def test_cada_herramienta_es_un_paso_de_deshacer(s):
    abajo, derecha, _arriba, _izq = rectangulo(s)
    for nombre, args in (("draw_ellipse", {"major_radius": 5, "minor_radius": 2, "center_x": 100}),
                         ("draw_slot", {"points": [[100, 50], [120, 50]], "width": 4}),
                         ("sketch_fillet", {"entity1": abajo, "entity2": derecha, "radius": 2}),
                         ("auto_constrain", {})):
        n, texto = len(s.doc._deshacer), json.dumps(s.doc.a_dict(), sort_keys=True)
        llamar(s, nombre, **args)
        assert len(s.doc._deshacer) == n + 1, nombre
        llamar(s, "undo")
        assert json.dumps(s.doc.a_dict(), sort_keys=True) == texto, nombre
        llamar(s, "redo")

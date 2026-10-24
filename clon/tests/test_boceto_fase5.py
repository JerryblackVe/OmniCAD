"""BOC-13 y BOC-19: especificaciones completas y creación de geometría central."""
import math

import pytest

from omnicad import api
from omnicad.nucleo import geometria as geo
from omnicad.restricciones import Boceto


def llamar_fase5(sesion, nombre, **argumentos):
    respuesta = api.llamar(sesion, nombre, argumentos)
    assert respuesta["ok"], respuesta
    return respuesta["result"]


@pytest.mark.parametrize("entidades", [None, []])
def test_boc13_spec_vacio_crea_boceto_y_devuelve_aviso(entidades):
    s = api.Sesion()
    r = api.llamar(s, "sketch_from_spec", {"entities": entidades})
    assert r["ok"], r
    assert r["avisos"] and "vacío" in " ".join(r["avisos"])
    assert len(s.doc.operaciones) == 1
    assert r["result"]["profiles"] == 0


def test_boc13_conica_y_linea_de_punto_medio_con_alias():
    s = api.Sesion()
    r = llamar_fase5(s, "sketch_from_spec", entities=[
        {"type": "conic", "id": "c", "start": [0, 0], "end": [10, 0], "vertex": [5, 10], "rho": 0.5},
        {"type": "midpoint_line", "id": "m", "center": [20, 10], "end": [23, 14]},
    ])
    info = llamar_fase5(s, "get_sketch")
    curvas = {c["id"]: c for c in info["entities"]}
    assert curvas[r["handles"]["c"]]["rho"] == pytest.approx(0.5)
    assert curvas[r["handles"]["c"]]["vertex"] == [5, 10]
    assert curvas[r["handles"]["m"]]["length"] == pytest.approx(10)
    centro = next(p for p in info["points"] if p["id"] == r["handles"]["m.center"])
    assert (centro["x"], centro["y"]) == (20, 10)
    assert any(c["type"] == "midpoint" for c in info["constraints"])


@pytest.mark.parametrize("lado,centro_y", [(None, 5), ([5, -1], -5)])
def test_boc13_poligono_por_arista_area_y_orientacion(lado, centro_y):
    s = api.Sesion()
    entidad = {"type": "polygon", "kind": "edge", "id": "p", "start": [0, 0], "end": [10, 0], "sides": 4}
    if lado is not None:
        entidad["edge_points"] = [[0, 0], [10, 0], lado]
    r = llamar_fase5(s, "sketch_from_spec", entities=[entidad])
    info = llamar_fase5(s, "get_sketch")
    assert info["profiles"][0]["area"] == pytest.approx(100)
    assert info["profiles"][0]["centroid"] == pytest.approx([5, centro_y])
    assert all(f"p.side{i}" in r["handles"] for i in range(1, 5))


@pytest.mark.parametrize("cantidad,radio", [(2, 2), (3, 10 - 5 * math.sqrt(2))])
def test_boc13_circulos_tangentes_por_citas(cantidad, radio):
    s = api.Sesion()
    entidades = [
        {"type": "line", "id": "a", "start": [0, 0], "end": [10, 0], "construction": True},
        {"type": "line", "id": "b", "start": [0, 0], "end": [0, 10], "construction": True},
    ]
    circulo = {"type": "tangent_circle", "id": "c", "lines": ["a", "b"]}
    if cantidad == 3:
        entidades.append({"type": "line", "id": "h", "start": [10, 0], "end": [0, 10], "construction": True})
        circulo["lines"].append("h")
    else:
        circulo.update(radius=2, x=2, y=2)
    r = llamar_fase5(s, "sketch_from_spec", entities=entidades + [circulo])
    info = llamar_fase5(s, "get_sketch")
    curva = next(c for c in info["entities"] if c["id"] == r["handles"]["c"])
    assert curva["radius"] == pytest.approx(radio, abs=1e-4)
    assert curva["center"] == pytest.approx([radio, radio], abs=1e-4)
    assert info["profiles"][0]["area"] == pytest.approx(math.pi * radio ** 2, abs=1e-3)
    assert sum(c["type"] == "tangent" for c in info["constraints"]) == cantidad


@pytest.mark.parametrize("extremo,fin", [("end", [15, 5]), ("start", [-5, 5])])
def test_boc13_arco_tangente_comparte_extremo_y_radio(extremo, fin):
    s = api.Sesion()
    r = llamar_fase5(s, "sketch_from_spec", entities=[
        {"type": "line", "id": "l", "start": [0, 0], "end": [10, 0]},
        {"type": "tangent_arc", "id": "a", "from": f"l.{extremo}", "end": fin},
    ])
    info = llamar_fase5(s, "get_sketch")
    arco = next(c for c in info["entities"] if c["id"] == r["handles"]["a"])
    assert arco["radius"] == pytest.approx(5)
    assert r["handles"][f"l.{extremo}"] in arco["points"]
    assert any(c["type"] == "tangent" for c in info["constraints"])


def test_boc13_texto_reutiliza_opciones_y_camino_de_add_text():
    opciones = {"text": "AB", "x": 3, "y": 4, "height": 6, "angle": 12, "font": "Arial",
                "bold": True, "italic": True, "letter_spacing": 0.2, "line_spacing": 1.5,
                "align": "right", "anchor": "middle", "box_width": 20, "flip_h": True, "flip_v": True,
                "kerning": False, "skew": 10, "scale_x": 120, "scale_y": 80, "baseline_shift": 1,
                "case": "lower", "underline": "double", "strikethrough": "single",
                "decoration_thickness": 0.3, "no_wrap": True, "kerning_pairs": [[1, 0.4]]}
    s = api.Sesion()
    llamar_fase5(s, "sketch_from_spec", entities=[{"type": "text", **opciones}])
    texto_spec = llamar_fase5(s, "get_sketch")["entities"][0]
    otra = api.Sesion()
    llamar_fase5(otra, "create_sketch")
    llamar_fase5(otra, "add_text", **opciones)
    assert texto_spec == llamar_fase5(otra, "get_sketch")["entities"][0]
    assert texto_spec["height"] == 6
    assert texto_spec["position"] == [3, 4]
    s = api.Sesion()
    r = llamar_fase5(s, "sketch_from_spec", entities=[
        {"type": "circle", "id": "c", "center": [0, 0], "radius": 20, "construction": True},
        {"type": "text", "id": "t", "text": "A", "height": 3, "path_entity": "c", "path_side": "right",
         "path_position": 0.25, "path_offset": 2, "fit_path": True},
    ])
    texto = next(c for c in llamar_fase5(s, "get_sketch")["entities"] if c["type"] == "text")
    assert texto["path_entity"] == r["handles"]["c"]
    assert texto["path_position"] == 0.25 and texto["path_offset"] == 2 and texto["fit_path"]


def test_boc13_cota_de_referencia_mide_sin_mover_y_sin_quitar_gdl():
    s = api.Sesion()
    llamar_fase5(s, "sketch_from_spec", entities=[{"type": "line", "id": "l", "start": [3, 4], "end": [13, 4]}],
                 dimensions=[{"type": "distance", "entities": ["l"], "value": 99, "reference": True}])
    info = llamar_fase5(s, "get_sketch")
    assert info["dof"] == 4
    assert info["dimensions"][0]["reference"] is True
    assert info["dimensions"][0]["value"] == pytest.approx(10)
    assert info["entities"][0]["length"] == pytest.approx(10)


DIBUJOS_CENTRALES = [
    ("draw_line", {"start_x": 3, "start_y": 4, "end_x": 13, "end_y": 4}),
    ("draw_rectangle", {"width": 10, "height": 5}),
    ("draw_circle", {"radius": 5}),
    ("draw_arc", {"start_x": 5, "start_y": 0, "center_x": 0, "center_y": 0, "sweep_angle": 90}),
    ("draw_ellipse", {"major_radius": 10, "minor_radius": 5}),
    ("draw_spline", {"points": [[0, 0], [5, 3], [10, 0]]}),
    ("draw_slot", {"points": [[0, 0], [10, 0]], "width": 4}),
    ("create_polygon", {"sides": 4, "radius": 5}),
    ("draw_conic", {"start_x": 0, "start_y": 0, "end_x": 10, "end_y": 0, "vertex_x": 5, "vertex_y": 10}),
]


@pytest.mark.parametrize("nombre,argumentos", DIBUJOS_CENTRALES)
def test_boc19_dibujo_central_conserva_perfiles_y_auxiliares(nombre, argumentos):
    s = api.Sesion()
    llamar_fase5(s, "create_sketch")
    llamar_fase5(s, nombre, **argumentos, centerline=True)
    info = llamar_fase5(s, "get_sketch")
    normales = [c for c in info["entities"] if not c["construction"]]
    assert normales and all(c["centerline"] is True for c in normales)
    assert all(not c.get("centerline", False) for c in info["entities"] if c["construction"])
    b = s.doc.operaciones[0].boceto
    assert Boceto.desde_dict(b.a_dict()).a_dict() == b.a_dict()
    if nombre == "draw_circle":
        assert info["profiles"][0]["area"] == pytest.approx(math.pi * 25, abs=1e-4)


@pytest.mark.parametrize("nombre,argumentos", DIBUJOS_CENTRALES)
def test_boc19_construccion_y_central_juntas_fallan_atomicamente(nombre, argumentos):
    s = api.Sesion()
    llamar_fase5(s, "create_sketch")
    antes = s.doc.a_dict()
    r = api.llamar(s, nombre, {**argumentos, "centerline": True, "construction": True})
    assert not r["ok"] and r["error_kind"] == "INVALID_ARGUMENTS", r
    assert "centerline" in r["mensaje"] and "construction" in r["mensaje"]
    assert s.doc.a_dict() == antes


def test_boc13_central_en_spec_sigue_siendo_perfil_revolucionable():
    s = api.Sesion()
    r = llamar_fase5(s, "sketch_from_spec", plane="XZ", entities=[
        {"type": "rectangle", "corner1": [2, 0], "corner2": [7, 10]},
        {"type": "line", "id": "eje", "start": [2, 0], "end": [2, 10], "centerline": True},
    ])
    info = llamar_fase5(s, "get_sketch")
    assert next(c for c in info["entities"] if c["id"] == r["handles"]["eje"])["centerline"] is True
    llamar_fase5(s, "revolve", sketch=r["sketch"]["id"], axis=r["handles"]["eje"])
    forma = next(iter(s.doc.estado_final.cuerpos.values())).forma
    assert geo.es_valida(forma)
    assert geo.volumen(forma) == pytest.approx(math.pi * 25 * 10)


@pytest.mark.parametrize("entidad", [
    {"type": "line", "start": [0, 0], "end": [10, 0], "centerline": "true"},
    {"type": "line", "start": [0, 0], "end": [10, 0], "centerline": True, "construction": True},
    {"type": "text", "text": "A", "centerline": True},
    {"type": "tangent_arc", "from": "inexistente.end", "end": [5, 5]},
])
def test_boc13_spec_invalido_no_deja_boceto(entidad):
    s = api.Sesion()
    antes = s.doc.a_dict()
    r = api.llamar(s, "sketch_from_spec", {"entities": [entidad]})
    assert not r["ok"] and r["error_kind"] != "INTERNAL_ERROR", r
    assert s.doc.a_dict() == antes


def test_boc13_arco_desde_cita_identifica_linea_aun_con_esquina_compartida():
    s = api.Sesion()
    r = llamar_fase5(s, "sketch_from_spec", entities=[
        {"type": "line", "id": "l", "start": [0, 0], "end": [10, 0]},
        {"type": "line", "id": "otra", "start": [10, 0], "end": [10, -5]},
        {"type": "tangent_arc", "id": "a", "from": "l.end", "end": [15, 5], "centerline": True},
    ])
    info = llamar_fase5(s, "get_sketch")
    arco = next(c for c in info["entities"] if c["id"] == r["handles"]["a"])
    assert arco["radius"] == 5 and arco["centerline"]
    tangencia = next(c for c in info["constraints"] if c["type"] == "tangent")
    assert tangencia["entities"] == [r["handles"]["l"], r["handles"]["a"]]
    assert not next(c for c in info["entities"] if c["id"] == r["handles"]["l"]).get("centerline")


@pytest.mark.parametrize("opciones", [{"align": ""}, {"bold": "true"}, {"height": float("nan")},
                                      {"path_entity": []}, {"scale_x": 0}])
def test_boc13_texto_invalido_rechazado_atomicamente(opciones):
    s = api.Sesion()
    antes = s.doc.a_dict()
    r = api.llamar(s, "sketch_from_spec", {"entities": [{"type": "text", "text": "A", **opciones}]})
    assert not r["ok"] and r["error_kind"] != "INTERNAL_ERROR", r
    assert s.doc.a_dict() == antes


@pytest.mark.parametrize("valor", [None, 0, "no_es_un_parametro"])
def test_boc13_referencia_no_exige_valor_ni_evalua_expresion(valor):
    s = api.Sesion()
    llamar_fase5(s, "sketch_from_spec", entities=[{"type": "circle", "id": "c", "center": [0, 0], "radius": 5}],
                 dimensions=[{"type": "radius", "entities": ["c"], "reference": True, "value": valor}])
    info = llamar_fase5(s, "get_sketch")
    assert info["dof"] == 3
    assert info["dimensions"][0]["value"] == 5 and info["dimensions"][0]["reference"]


@pytest.mark.parametrize("nombre,argumentos", [
    ("draw_line", {"start_x": 0, "start_y": 0, "end_x": 5, "end_y": 0, "midpoint": True}),
    ("draw_rectangle", {"three_points": [[0, 0], [10, 0], [3, 5]]}),
    ("draw_rectangle", {"center_x": 0, "center_y": 0, "width": 10, "height": 5, "center_diagonals": True}),
    ("draw_circle", {"kind": "two_points", "points": [[-5, 0], [5, 0]]}),
    ("draw_circle", {"kind": "three_points", "points": [[-5, 0], [0, 5], [5, 0]]}),
    ("draw_arc", {"start_x": 5, "start_y": 0, "mid_x": 0, "mid_y": 5, "end_x": -5, "end_y": 0}),
    ("create_polygon", {"sides": 4, "kind": "edge", "edge_points": [[0, 0], [10, 0], [0, 5]],
                        "fully_constrained": True}),
])
def test_boc19_central_en_variantes_de_las_herramientas(nombre, argumentos):
    s = api.Sesion()
    llamar_fase5(s, "create_sketch")
    antes = s.doc.a_dict()
    llamar_fase5(s, nombre, **argumentos, centerline=True)
    info = llamar_fase5(s, "get_sketch")
    assert all(c.get("centerline") for c in info["entities"] if not c["construction"])
    assert all(not c.get("centerline") for c in info["entities"] if c["construction"])
    s.doc.deshacer()
    assert s.doc.a_dict() == antes


def test_boc19_arco_tangente_central_no_marca_linea_previa():
    s = api.Sesion()
    llamar_fase5(s, "create_sketch")
    l = llamar_fase5(s, "draw_line", start_x=0, start_y=0, end_x=10, end_y=0)["entities"][0]["id"]
    llamar_fase5(s, "draw_arc", tangent_to=l, start_x=10, start_y=0, end_x=15, end_y=5, centerline=True)
    info = llamar_fase5(s, "get_sketch")
    assert not next(c for c in info["entities"] if c["id"] == l).get("centerline")
    arco = next(c for c in info["entities"] if c["type"] == "arc")
    assert arco["centerline"] and arco["radius"] == 5


def test_boc19_revolve_toma_sola_la_linea_central():
    s = api.Sesion()
    r = llamar_fase5(s, "sketch_from_spec", entities=[
        {"type": "rectangle", "corner1": [0, 0], "corner2": [5, 10]},
        {"type": "line", "id": "eje", "start": [0, -1], "end": [0, 11], "centerline": True}])
    llamar_fase5(s, "revolve", sketch=r["sketch"]["id"], profile=0)
    forma = next(iter(s.doc.estado_final.cuerpos.values())).forma
    assert geo.volumen(forma) == pytest.approx(math.pi * 25 * 10, rel=1e-3)


def test_boc19_revolve_sin_eje_ni_central_o_con_dos_centrales_falla():
    s = api.Sesion()
    r = llamar_fase5(s, "sketch_from_spec", entities=[{"type": "rectangle", "corner1": [1, 0], "corner2": [5, 10]}])
    assert not api.llamar(s, "revolve", {"sketch": r["sketch"]["id"]})["ok"]
    r2 = llamar_fase5(s, "sketch_from_spec", entities=[
        {"type": "rectangle", "corner1": [1, 0], "corner2": [5, 10]},
        {"type": "line", "start": [0, 0], "end": [0, 10], "centerline": True},
        {"type": "line", "start": [-1, 0], "end": [-1, 10], "centerline": True}])
    resp = api.llamar(s, "revolve", {"sketch": r2["sketch"]["id"]})
    assert not resp["ok"] and resp["error_kind"] == "INVALID_AXIS"


def test_boc19_cota_diametro_con_linea_central_mide_el_doble():
    s = api.Sesion()
    r = llamar_fase5(s, "sketch_from_spec", entities=[
        {"type": "line", "id": "eje", "start": [0, 0], "end": [0, 20], "centerline": True},
        {"type": "line", "id": "borde", "start": [7, 0], "end": [7, 20]}],
        constraints=[{"type": "fix", "entities": ["eje"]}, {"type": "vertical", "entities": ["borde"]}])
    eje, borde = r["handles"]["eje"], r["handles"]["borde"]
    k = llamar_fase5(s, "add_dimension", sketch=r["sketch"]["id"], type="diameter", entities=[borde, eje], value=20)
    assert k["dimension"]["value"] == pytest.approx(20)
    info = llamar_fase5(s, "get_sketch")
    xs = [p["x"] for p in info["points"] if p["id"] in api_puntos(info, borde)]
    assert xs == [pytest.approx(10.0, abs=1e-4)] * 2


def api_puntos(info, cid):
    return next(c for c in info["entities"] if c["id"] == cid)["points"]


@pytest.mark.parametrize("giro,invertida,lado", [(0, False, 1), (0, True, -1), (37, True, 1)])
def test_boc15_empalme_paralelas_semicirculo_tangente(giro, invertida, lado):
    from omnicad.restricciones.boceto import dominio, evaluar_primitiva

    ang = math.radians(giro)

    def transformar(x, y):
        return [x * math.cos(ang) - y * math.sin(ang), x * math.sin(ang) + y * math.cos(ang)]

    s = api.Sesion()
    a2, b2 = (20, 0) if invertida else (0, 20)
    r = llamar_fase5(s, "sketch_from_spec", entities=[
        {"type": "line", "id": "a", "start": transformar(0, 0), "end": transformar(20, 0)},
        {"type": "line", "id": "b", "start": transformar(a2, 10), "end": transformar(b2, 10)},
    ])
    a, b = r["handles"]["a"], r["handles"]["b"]
    x_conservado = 2 if lado == 1 else 18
    respuesta = api.llamar(s, "sketch_fillet", {"entity1": a, "entity2": b, "radius": 2,
        "point1": transformar(x_conservado, 0), "point2": transformar(x_conservado, 10)})
    assert respuesta["ok"], respuesta
    assert any("radio" in aviso.lower() and "5" in aviso for aviso in respuesta["avisos"])
    info = llamar_fase5(s, "get_sketch")
    arco = next(c for c in info["entities"] if c["type"] == "arc")
    br = s.doc.estado_final.bocetos[r["sketch"]["id"]]
    centro = br.boceto.coords(br.boceto.curvas[arco["id"]].centro)
    x_centro = 20 if lado == 1 else 0
    assert arco["radius"] == pytest.approx(5, abs=1e-6)
    assert centro == pytest.approx(transformar(x_centro, 5), abs=1e-6)
    assert info["dimensions"][0]["value"] == pytest.approx(5, abs=1e-6)
    assert br.solver.ok
    prim = br.boceto.primitivas(arco["id"])[0]
    assert dominio(prim)[1] == pytest.approx(math.pi)
    medio = evaluar_primitiva(prim, math.pi / 2)[0]
    assert medio == pytest.approx(transformar(x_centro + lado * 5, 5), abs=1e-6)
    for lid in (a, b):
        linea = br.boceto.curvas[lid]
        compartidos = set(linea.extremos()) & set(br.boceto.curvas[arco["id"]].extremos())
        assert len(compartidos) == 1
        q = br.boceto.coords(compartidos.pop())
        v = br.boceto._direccion(lid)
        assert abs((q[0] - centro[0]) * v[0] + (q[1] - centro[1]) * v[1]) < 1e-6
        assert any(c["type"] == "tangent" and set(c["entities"]) == {lid, arco["id"]}
                   for c in info["constraints"])


@pytest.mark.parametrize("tipo,lado", [("fit_points", 0), ("fit_points", 1), ("control_points", 1)])
def test_boc15_extender_spline_tangente_conserva_tramo_y_coincide(tipo, lado):
    from omnicad.restricciones.boceto import dominio, evaluar_primitiva

    s = api.Sesion()
    r = llamar_fase5(s, "create_sketch")
    ref = r["sketch"]["id"]
    puntos = [[20, 20], [25, 23], [30, 20]] if tipo == "fit_points" else [[20, 20], [23, 23], [27, 23], [30, 20]]
    curva = llamar_fase5(s, "draw_spline", points=puntos, spline_type=tipo)["entities"][0]["id"]
    original = s.doc.estado_final.bocetos[ref].boceto.primitivas(curva)[0]
    t0, t1, _ = dominio(original)
    extremo, derivada = evaluar_primitiva(original, (t0, t1)[lado], 1)
    destino_x = extremo[0] + (4 if lado else -4)
    destino_y = extremo[1] + (destino_x - extremo[0]) * derivada[1] / derivada[0]
    for x in (destino_x, destino_x + (3 if lado else -3)):
        llamar_fase5(s, "draw_line", start_x=x, start_y=-100, end_x=x, end_y=100)
    linea = next(c["id"] for c in llamar_fase5(s, "get_sketch")["entities"] if c["type"] == "line")
    antes = s.doc.a_dict()
    llamar_fase5(s, "trim_sketch_curve", entity=curva, x=extremo[0], y=extremo[1], mode="extend")
    br = s.doc.estado_final.bocetos[ref]
    b = br.boceto
    nueva = b.primitivas(curva)[0]
    pid = b.curvas[curva].extremos()[lado]
    assert br.solver.ok and b.coords(pid) == pytest.approx((destino_x, destino_y), abs=1e-6)
    assert any(c.tipo == "coincidente" and c.entidades == [pid, linea] for c in b.restricciones.values())
    for i in range(21):
        t = t0 + (t1 - t0) * i / 20
        assert evaluar_primitiva(nueva, t)[0] == pytest.approx(evaluar_primitiva(original, t)[0], abs=1e-6)
    assert Boceto.desde_dict(b.a_dict()).a_dict() == b.a_dict()
    s.doc.deshacer()
    assert s.doc.a_dict() == antes


@pytest.mark.parametrize("lado", [0, 1])
def test_boc15_extender_arco_elipse_continua_hasta_proxima_interseccion(lado):
    s = api.Sesion()
    r = llamar_fase5(s, "sketch_from_spec", entities=[
        {"type": "ellipse", "id": "e", "center": [20, 20], "major_radius": 10, "minor_radius": 5},
        {"type": "line", "id": "corte", "start": [5, 20], "end": [35, 20]},
    ])
    ref, curva = r["sketch"]["id"], r["handles"]["e"]
    llamar_fase5(s, "trim_sketch_curve", entity=curva, x=20, y=15)
    destino_x = 28 if lado == 0 else 12
    linea = llamar_fase5(s, "draw_line", start_x=destino_x, start_y=10,
                        end_x=destino_x, end_y=19)["entities"][0]["id"]
    b = s.doc.estado_final.bocetos[ref].boceto
    extremo = b.coords(b.curvas[curva].extremos()[lado])
    llamar_fase5(s, "trim_sketch_curve", entity=curva, x=extremo[0], y=extremo[1], mode="extend")
    br = s.doc.estado_final.bocetos[ref]
    b = br.boceto
    c = b.curvas[curva]
    assert br.solver.ok
    assert b.coords(c.extremos()[lado]) == pytest.approx((destino_x, 17), abs=1e-6)
    assert b.coords(c.centro) == pytest.approx((20, 20), abs=1e-6)
    assert math.dist(b.coords(c.centro), b.coords(c.mayor)) == pytest.approx(10, abs=1e-6)
    assert c.radio_menor == pytest.approx(5, abs=1e-6)
    assert any(k.tipo == "coincidente" and k.entidades == [c.extremos()[lado], linea]
               for k in b.restricciones.values())


def test_boc15_extender_spline_sin_interseccion_falla_sin_cambios():
    s = api.Sesion()
    llamar_fase5(s, "create_sketch")
    curva = llamar_fase5(s, "draw_spline", points=[[20, 20], [25, 23], [30, 20]])["entities"][0]["id"]
    antes = s.doc.a_dict()
    respuesta = api.llamar(s, "trim_sketch_curve", {"entity": curva, "x": 30, "y": 20, "mode": "extend"})
    assert not respuesta["ok"] and respuesta["error_kind"] == "INVALID_GEOMETRY"
    assert "alcanzar" in respuesta["mensaje"]
    assert s.doc.a_dict() == antes


def test_boc15_empalme_paralelas_sin_picks_alarga_la_linea_mas_corta():
    s = api.Sesion()
    r = llamar_fase5(s, "sketch_from_spec", entities=[
        {"type": "line", "id": "a", "start": [0, 0], "end": [20, 0]},
        {"type": "line", "id": "b", "start": [0, 10], "end": [12, 10]},
    ])
    llamar_fase5(s, "sketch_fillet", entity1=r["handles"]["a"], entity2=r["handles"]["b"], radius=5)
    info = llamar_fase5(s, "get_sketch")
    arco = next(c for c in info["entities"] if c["type"] == "arc")
    assert arco["center"] == [20, 5] and arco["radius"] == 5
    linea = next(c for c in info["entities"] if c["id"] == r["handles"]["b"])
    assert linea["end"] == [20, 10] and linea["length"] == 20


@pytest.mark.parametrize("separacion,pick2,mensaje", [(0, [2, 0], "colineales"), (10, [18, 10], "mismo lado")])
def test_boc15_empalme_paralelas_invalido_no_cambia_documento(separacion, pick2, mensaje):
    s = api.Sesion()
    r = llamar_fase5(s, "sketch_from_spec", entities=[
        {"type": "line", "id": "a", "start": [0, 0], "end": [20, 0]},
        {"type": "line", "id": "b", "start": [0, separacion], "end": [20, separacion]},
    ])
    antes = s.doc.a_dict()
    respuesta = api.llamar(s, "sketch_fillet", {"entity1": r["handles"]["a"], "entity2": r["handles"]["b"],
        "radius": 5, "point1": [2, 0], "point2": pick2})
    assert not respuesta["ok"] and respuesta["error_kind"] == "INVALID_GEOMETRY"
    assert mensaje in respuesta["mensaje"]
    assert s.doc.a_dict() == antes


@pytest.mark.parametrize("lado", [0, 1])
def test_boc15_extender_spline_racional_conserva_geometria_y_tangente(lado):
    from omnicad.restricciones.boceto import dominio, evaluar_primitiva

    b = Boceto()
    curva = b.agregar_spline([(20, 20), (25, 25), (30, 20)], "control", 2, pesos=[1, 0.5, 1])
    prim = b.primitivas(curva)[0]
    t0, t1, _ = dominio(prim)
    t = (t0, t1)[lado]
    extremo, tangente = evaluar_primitiva(prim, t, 1)
    x = extremo[0] + (4 if lado else -4)
    b.agregar_linea((x, 0), (x, 40))
    b.alargar(curva, extremo)
    nueva = b.primitivas(curva)[0]
    assert b.coords(b.curvas[curva].extremos()[lado]) == pytest.approx((x, 16), abs=1e-6)
    for i in range(21):
        u = t0 + (t1 - t0) * i / 20
        assert evaluar_primitiva(nueva, u)[0] == pytest.approx(evaluar_primitiva(prim, u)[0], abs=1e-8)
    assert evaluar_primitiva(nueva, t + (1e-9 if lado else -1e-9), 1)[1] == pytest.approx(tangente, abs=1e-6)


def test_boc15_extender_elipse_no_toma_sus_ejes_auxiliares_como_cortes():
    s = api.Sesion()
    r = llamar_fase5(s, "sketch_from_spec", entities=[
        {"type": "ellipse", "id": "e", "center": [20, 20], "major_radius": 10, "minor_radius": 5},
        {"type": "line", "start": [5, 20], "end": [35, 20]},
    ])
    curva = r["handles"]["e"]
    llamar_fase5(s, "trim_sketch_curve", entity=curva, x=20, y=15)
    antes = s.doc.a_dict()
    respuesta = api.llamar(s, "trim_sketch_curve", {"entity": curva, "x": 10, "y": 20, "mode": "extend"})
    assert not respuesta["ok"] and respuesta["error_kind"] == "INVALID_GEOMETRY"
    assert "alcanzar" in respuesta["mensaje"]
    assert s.doc.a_dict() == antes


def _boc12_fuente(s, tipo):
    ref = llamar_fase5(s, "create_sketch")["sketch"]["id"]
    if tipo == "linea":
        r = llamar_fase5(s, "draw_line", start_x=20, start_y=20, end_x=30, end_y=24)
    elif tipo == "arco":
        r = llamar_fase5(s, "draw_arc", center_x=20, center_y=20, start_x=30, start_y=20, sweep_angle=110)
    elif tipo in ("ajuste", "control"):
        r = llamar_fase5(s, "draw_spline", points=[[20, 20], [23, 25], [27, 24], [30, 20]],
                         spline_type="fit_points" if tipo == "ajuste" else "control_points")
    elif tipo == "conica":
        r = llamar_fase5(s, "draw_conic", start_x=20, start_y=20, end_x=30, end_y=20,
                         vertex_x=25, vertex_y=30, rho=0.7)
    else:
        r = llamar_fase5(s, "draw_ellipse", center_x=20, center_y=20, major_radius=10, minor_radius=5)
    cid = r["entities"][0]["id"]
    if tipo == "arco_elipse":
        llamar_fase5(s, "draw_line", start_x=5, start_y=20, end_x=35, end_y=20)
        llamar_fase5(s, "trim_sketch_curve", entity=cid, x=20, y=15)
    llamar_fase5(s, "add_constraint", sketch=ref, type="fix", entities=[cid])
    return ref, cid


@pytest.mark.parametrize("tipo", ["arco", "ajuste", "control", "conica", "elipse", "arco_elipse", "linea"])
@pytest.mark.parametrize("lado", [0, 1])
def test_boc12_arco_tangente_desde_curvas_comparte_punto_y_derivada(tipo, lado):
    from omnicad.restricciones.boceto import dominio, evaluar_primitiva, mas_cercano

    s = api.Sesion()
    ref, cid = _boc12_fuente(s, tipo)
    b = s.doc.estado_final.bocetos[ref].boceto
    original = b.primitivas(cid)[0]
    t = (0.3 + lado) if tipo == "elipse" else dominio(original)[lado]
    p, d = evaluar_primitiva(original, t, 1)
    n = math.hypot(*d)
    signo = -1 if lado == 0 else 1
    u = (signo * d[0] / n, signo * d[1] / n)
    fin = (p[0] + 4 * u[0] - 3 * u[1], p[1] + 4 * u[1] + 3 * u[0])
    antes = s.doc.a_dict()
    nuevo = llamar_fase5(s, "draw_arc", tangent_to=cid, start_x=p[0], start_y=p[1], end_x=fin[0], end_y=fin[1])
    aid = nuevo["entities"][0]["id"]
    b = s.doc.estado_final.bocetos[ref].boceto
    arco = b.curvas[aid]
    centro = b.coords(arco.centro)
    if tipo == "elipse":
        # En una curva cerrada el contacto puede deslizarse: se verifica la unión resuelta.
        p = b.coords(min(arco.extremos(), key=lambda pid: math.dist(b.coords(pid), p)))
        t, distancia, _q = mas_cercano(b.primitivas(cid)[0], p)
        assert distancia < 1e-6
        d = evaluar_primitiva(b.primitivas(cid)[0], t, 1)[1]
        n = math.hypot(*d)
        u = (d[0] / n, d[1] / n)
    else:
        assert b.radio(aid) == pytest.approx(25 / 6, abs=1e-6)
        assert min(math.dist(b.coords(pid), p) for pid in arco.extremos()) < 1e-7
        assert min(math.dist(b.coords(pid), fin) for pid in arco.extremos()) < 1e-7
    prim = b.primitivas(aid)[0]
    da = evaluar_primitiva(prim, mas_cercano(prim, p)[0], 1)[1]
    seno = (da[0] * d[1] - da[1] * d[0]) / (math.hypot(*da) * n)
    assert abs(math.asin(max(-1, min(1, seno)))) < 1e-6
    assert abs((p[0] - centro[0]) * u[0] + (p[1] - centro[1]) * u[1]) / b.radio(aid) < 1e-6
    assert b.primitivas(cid)[0] == original
    if tipo != "elipse":
        assert set(b.curvas[cid].extremos()) & set(arco.extremos())
    info = llamar_fase5(s, "get_sketch")
    assert any(c["type"] == "tangent" and c["entities"] == [cid, aid] for c in info["constraints"])
    assert s.doc.estado_final.bocetos[ref].solver.ok
    assert Boceto.desde_dict(b.a_dict()).a_dict() == b.a_dict()
    s.doc.deshacer()
    assert s.doc.a_dict() == antes


@pytest.mark.parametrize("tipo", ["linea", "arco", "ajuste", "conica", "elipse", "arco_elipse"])
@pytest.mark.parametrize("extremo,lado", [("start", 0), ("end", 1)])
def test_boc12_spline_de_ajuste_arranca_tangente(tipo, extremo, lado):
    from omnicad.restricciones.boceto import dominio, evaluar_primitiva, mas_cercano

    s = api.Sesion()
    ref, cid = _boc12_fuente(s, tipo)
    b = s.doc.estado_final.bocetos[ref].boceto
    prim = b.primitivas(cid)[0]
    p, d = evaluar_primitiva(prim, 0.7 if tipo == "elipse" else dominio(prim)[lado], 1)
    signo = -1 if lado == 0 else 1
    u = [signo * v / math.hypot(*d) for v in d]
    puntos = [list(p), [p[0] + 4 * u[0] - u[1], p[1] + 4 * u[1] + u[0]],
              [p[0] + 8 * u[0] - 3 * u[1], p[1] + 8 * u[1] + 3 * u[0]]]
    antes = s.doc.a_dict()
    r = llamar_fase5(s, "draw_spline", points=puntos, tangent_to=cid, tangent_end=extremo)
    sid = r["entities"][0]["id"]
    br = s.doc.estado_final.bocetos[ref]
    b = br.boceto
    spline = b.curvas[sid]
    assert spline.modo == "ajuste" and not spline.cerrada
    if tipo == "elipse":
        t, distancia, _q = mas_cercano(b.primitivas(cid)[0], b.coords(spline.pts[0]))
        assert distancia < 1e-6
        d = evaluar_primitiva(b.primitivas(cid)[0], t, 1)[1]
    else:
        assert b.coords(spline.pts[0]) == pytest.approx(p, abs=1e-6)
    nueva = b.primitivas(sid)[0]
    ds = evaluar_primitiva(nueva, dominio(nueva)[0], 1)[1]
    assert abs(ds[0] * d[1] - ds[1] * d[0]) / (math.hypot(*ds) * math.hypot(*d)) < 1e-6
    if tipo != "elipse":
        assert spline.pts[0] == b.curvas[cid].extremos()[lado]
    else:
        assert mas_cercano(b.primitivas(cid)[0], b.coords(spline.pts[0]))[1] < 1e-6
    assert br.solver.ok
    assert any(c["type"] == "tangent" and c["entities"] == [cid, sid]
               for c in llamar_fase5(s, "get_sketch")["constraints"])
    assert Boceto.desde_dict(b.a_dict()).a_dict() == b.a_dict()
    s.doc.deshacer()
    assert s.doc.a_dict() == antes


@pytest.mark.parametrize("herramienta,opciones", [
    ("draw_arc", {"start_x": 25, "start_y": 22, "end_x": 35, "end_y": 30}),
    ("draw_spline", {"points": [[20, 20], [35, 30]], "tangent_end": "end"}),
    ("draw_spline", {"points": [[30, 24], [35, 30]], "closed": True}),
    ("draw_spline", {"points": [[30, 24], [32, 25], [34, 26], [36, 25]], "spline_type": "control_points"}),
])
def test_boc12_tangencia_invalida_es_atomica(herramienta, opciones):
    s = api.Sesion()
    _ref, cid = _boc12_fuente(s, "linea")
    antes = s.doc.a_dict()
    r = api.llamar(s, herramienta, {"tangent_to": cid, **opciones})
    assert not r["ok"] and r["error_kind"] in ("INVALID_GEOMETRY", "INVALID_ARGUMENTS"), r
    assert s.doc.a_dict() == antes


@pytest.mark.parametrize("nombre", ["draw_arc", "draw_spline"])
@pytest.mark.parametrize("tipo", ["cerrada", "elipse", "sin_tangente"])
def test_boc12_fuente_sin_extremo_o_sin_tangente_rechaza_sin_modificar(nombre, tipo):
    s = api.Sesion()
    llamar_fase5(s, "create_sketch")
    if tipo == "elipse":
        r = llamar_fase5(s, "draw_ellipse", center_x=20, center_y=20, major_radius=10, minor_radius=5)
        inicio = [20, 20]  # el centro no está sobre la elipse
    else:
        puntos = [[20, 20], [25, 25], [30, 20]] if tipo == "cerrada" else [[20, 20], [20, 20], [25, 25], [30, 20]]
        r = llamar_fase5(s, "draw_spline", points=puntos, closed=tipo == "cerrada",
                         spline_type="fit_points" if tipo == "cerrada" else "control_points")
        inicio = [20, 20]
    cid = r["entities"][0]["id"]
    opciones = {"start_x": inicio[0], "start_y": inicio[1], "end_x": 16, "end_y": 24} if nombre == "draw_arc" else {
        "points": [inicio, [16, 24], [12, 25]], "tangent_end": "start"}
    antes = s.doc.a_dict()
    r = api.llamar(s, nombre, {"tangent_to": cid, **opciones})
    assert not r["ok"] and r["error_kind"] == "INVALID_GEOMETRY", r
    assert s.doc.a_dict() == antes


def test_boc12_spline_usa_fin_por_defecto_y_geometria_ya_resuelta():
    from omnicad.restricciones.boceto import dominio, evaluar_primitiva

    s = api.Sesion()
    ref = llamar_fase5(s, "create_sketch")["sketch"]["id"]
    cid = llamar_fase5(s, "draw_line", start_x=10, start_y=10, end_x=20, end_y=10)["entities"][0]["id"]
    llamar_fase5(s, "add_dimension", sketch=ref, type="distance", entities=[cid], value=20)
    b = s.doc.estado_final.bocetos[ref].boceto
    fin = b.coords(b.curvas[cid].p2)
    assert fin != (20, 10)
    r = llamar_fase5(s, "draw_spline", tangent_to=cid, construction=True,
                     points=[list(fin), [fin[0] + 5, fin[1]], [fin[0] + 10, fin[1]]])
    sid = r["entities"][0]["id"]
    b = s.doc.estado_final.bocetos[ref].boceto
    assert b.curvas[sid].construccion and b.curvas[sid].pts[0] == b.curvas[cid].p2
    assert b.coords(b.curvas[sid].pts[0]) == pytest.approx(fin, abs=1e-7)
    prim = b.primitivas(sid)[0]
    d = evaluar_primitiva(prim, dominio(prim)[0], 1)[1]
    assert abs(d[1]) < 1e-7 and d[0] > 0


@pytest.mark.parametrize("rho,signo", [(0.25, -1), (0.5, 0), (0.75, 1)])
def test_boc26_rho_elipse_parabola_hiperbola_y_punto_conocido(rho, signo):
    from omnicad.restricciones.boceto import evaluar_primitiva

    s = api.Sesion()
    llamar_fase5(s, "create_sketch")
    cid = llamar_fase5(s, "draw_conic", start_x=20, start_y=20, end_x=40, end_y=20,
                      vertex_x=30, vertex_y=40, rho=rho)["entities"][0]["id"]
    b = next(iter(s.doc.estado_final.bocetos.values())).boceto
    prim = b.primitivas(cid)[0]
    assert evaluar_primitiva(prim, 0.5)[0] == pytest.approx((30, 20 + 20 * rho), abs=1e-6)
    # Ecuación implícita normalizada: X² + A·Y² + 2Y − 1 = 0; discriminante −4A.
    coeficiente = ((1 - rho) / rho) ** 2 - 1
    discriminante = -4 * coeficiente
    assert (discriminante > 0) - (discriminante < 0) == signo
    for t in (0, 0.25, 0.5, 0.75, 1):
        x, y = evaluar_primitiva(prim, t)[0]
        x, y = (x - 30) / 10, (y - 20) / 20
        assert x * x + coeficiente * y * y + 2 * y - 1 == pytest.approx(0, abs=1e-6)
    if rho == 0.5:
        assert evaluar_primitiva(prim, 0.25)[0] == pytest.approx((25, 27.5), abs=1e-6)

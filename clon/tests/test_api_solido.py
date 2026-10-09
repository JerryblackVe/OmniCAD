# -*- coding: utf-8 -*-
import json
import math

import pytest

from omnicad import api


@pytest.fixture
def s():
    return api.Sesion()


def ok(r):
    assert r["ok"], r
    return r["result"]


def llamar(sesion, nombre, **args):
    return ok(api.llamar(sesion, nombre, args))


def foto(sesion):
    doc = sesion.doc
    return (json.dumps(doc.a_dict(), sort_keys=True), [(r.estado, r.mensaje) for r in doc.resultados],
            len(doc._deshacer), len(doc._rehacer), doc.modificado)


def cuerpos(sesion):
    return {c["id"]: c for c in llamar(sesion, "get_scene_info")["bodies"]}


def volumen(sesion, cuerpo=None):
    c = cuerpos(sesion)
    return (c[cuerpo] if cuerpo else next(iter(c.values())))["volume"]


def caja(sesion, cuerpo):
    bb = cuerpos(sesion)[cuerpo]["bounding_box"]
    return bb["min"], bb["max"]


def test_herramientas_del_grupo_solido():
    assert [h["nombre"] for h in api.catalogo("solido")] == [
        "extrude", "revolve", "sweep", "loft", "create_box", "create_cylinder", "create_sphere", "create_torus",
        "boolean_operation", "mirror", "rectangular_pattern", "circular_pattern", "move_body",
        "fillet", "chamfer", "shell", "create_hole", "draft"]   # las 5 últimas: herramientas_modificar.py (Paquete D)
    assert all(h["modifica"] for h in api.catalogo("solido"))


# ---------------------------------------------------------------- el soporte en L, solo con la API
# Dos placas de 80 × 40 × 8 mm en L (la base en XY y la pared parada sobre su borde y = 0..8), con dos
# agujeros pasantes de Ø8 en la base. Se solapan en un cubo de 80 × 8 × 8.
SOPORTE_EN_L = [
    ("create_sketch", {"plane": "XY", "name": "Base"}),
    ("draw_rectangle", {"x1": 0, "y1": 0, "x2": 80, "y2": 40}),
    ("extrude", {"sketch": "Base", "profile": 0, "distance": 8}),
    ("create_sketch", {"plane": "XZ", "name": "Pared"}),
    ("draw_rectangle", {"x1": 0, "y1": 0, "x2": 80, "y2": 40}),
    ("extrude", {"sketch": "Pared", "profile": 0, "distance": 8, "operation": "join", "reverse": True}),
    ("create_sketch", {"plane": "XY", "name": "Agujeros"}),
    ("draw_circle", {"radius": 4, "center_x": 15, "center_y": 25}),
    ("draw_circle", {"radius": 4, "center_x": 65, "center_y": 25}),
    ("extrude", {"sketch": "Agujeros", "profile": "all", "distance": 8, "operation": "cut"}),
]
VOLUMEN_L = 2 * 80 * 40 * 8 - 80 * 8 * 8 - 2 * math.pi * 4 ** 2 * 8


def test_soporte_en_l_solo_con_la_api(s):
    for nombre, args in SOPORTE_EN_L:
        ok(api.llamar(s, nombre, args))
    info = llamar(s, "get_scene_info")
    assert len(info["bodies"]) == 1 and [b["profiles"] for b in info["sketches"]] == [1, 1, 2]
    cuerpo = info["bodies"][0]
    assert cuerpo["volume"] == pytest.approx(VOLUMEN_L, rel=1e-3)
    assert cuerpo["bounding_box"]["size"] == pytest.approx([80, 40, 40], abs=1e-3)
    pasos = llamar(s, "get_timeline", include_params=False)["steps"]       # 3 bocetos + 3 extrusiones
    assert [p["type"] for p in pasos] == ["boceto", "extrusion"] * 3 and {p["status"] for p in pasos} == {"ok"}


def test_soporte_en_l_parametrico_con_spec(s):
    llamar(s, "create_parameter", name="espesor", expression="8 mm")
    llamar(s, "create_parameter", name="diametro", expression="8 mm")
    llamar(s, "sketch_from_spec", name="Base", entities=[{"type": "rectangle", "corner1": [0, 0], "corner2": [80, 40]}])
    llamar(s, "extrude", sketch="Base", distance="espesor")
    llamar(s, "sketch_from_spec", plane="XZ", name="Pared", entities=[{"type": "rectangle", "corner1": [0, 0], "corner2": [80, 40]}])
    llamar(s, "extrude", sketch="Pared", distance="espesor", operation="join", reverse=True)
    llamar(s, "sketch_from_spec", name="Agujeros",
           entities=[{"type": "circle", "id": "a", "center": [15, 25], "radius": 4},
                     {"type": "circle", "id": "b", "center": [65, 25], "radius": 4}],
           dimensions=[{"type": "diameter", "entities": ["a"], "value": "diametro"},
                       {"type": "diameter", "entities": ["b"], "value": "diametro"}])
    llamar(s, "extrude", sketch="Agujeros", profile="all", distance="espesor", operation="cut")
    assert volumen(s) == pytest.approx(VOLUMEN_L, rel=1e-3)
    llamar(s, "set_parameter", name="diametro", expression="10 mm")
    # los perfiles se referencian por firma: la extrusión sigue su agujero cuando cambia la cota
    assert volumen(s) == pytest.approx(2 * 80 * 40 * 8 - 80 * 8 * 8 - 2 * math.pi * 25 * 8, rel=1e-3)


def test_un_parametro_en_distance_cambia_el_volumen(s):
    llamar(s, "create_parameter", name="espesor", expression="8 mm")
    llamar(s, "create_sketch")
    llamar(s, "draw_rectangle", x1=0, y1=0, x2=20, y2=10)
    r = llamar(s, "extrude", sketch="Boceto1", distance="espesor")
    assert r["bodies_created"][0]["volume"] == pytest.approx(1600, rel=1e-6)
    llamar(s, "extrude", sketch="Boceto1", distance="espesor * 2", operation="join")
    assert volumen(s) == pytest.approx(20 * 10 * 16, rel=1e-6)                 # el segundo solapa al primero
    assert llamar(s, "get_parameters")["parameters"][0]["used_by"] == ["Extrusión1", "Extrusión2"]
    res = llamar(s, "set_parameter", name="espesor", expression="15 mm")
    assert res["value"] == 15
    assert volumen(s) == pytest.approx(20 * 10 * 30, rel=1e-6)
    ok(api.llamar(s, "undo"))
    assert volumen(s) == pytest.approx(20 * 10 * 16, rel=1e-6)
    r = api.llamar(s, "set_parameter", {"name": "espesor", "expression": "0 mm"})
    assert r["ok"] is False and r["error_kind"] == "OPERATION_FAILED"
    assert volumen(s) == pytest.approx(20 * 10 * 16, rel=1e-6)                 # falló: no cambió nada


# ---------------------------------------------------------------- errores estructurados
def test_perfil_inexistente_es_un_error_estructurado(s):
    llamar(s, "create_sketch")
    llamar(s, "draw_rectangle", x1=0, y1=0, x2=10, y2=10)
    antes = foto(s)
    r = api.llamar(s, "extrude", {"sketch": "Boceto1", "profile": 5, "distance": 3})
    assert r["ok"] is False and r["error_kind"] == "PROFILE_NOT_FOUND"
    assert "5" in r["mensaje"] and "1 (índices 0 a 0)" in r["mensaje"]
    assert 1 <= len(r["pistas"]) <= 3 and any("get_sketch" in p or "largest" in p for p in r["pistas"])
    assert foto(s) == antes
    for perfil in ([0, 7], -1, "casi", []):
        assert api.llamar(s, "extrude", {"sketch": "Boceto1", "profile": perfil})["error_kind"] == "PROFILE_NOT_FOUND"
    assert foto(s) == antes


def test_errores_de_extrusion(s):
    assert api.llamar(s, "extrude", {"sketch": "nada"})["error_kind"] == "SKETCH_NOT_FOUND"
    llamar(s, "create_sketch")
    assert api.llamar(s, "extrude", {"sketch": "Boceto1"})["error_kind"] == "PROFILE_NOT_FOUND"       # vacío
    llamar(s, "draw_line", start_x=0, start_y=0, end_x=10, end_y=0)
    llamar(s, "draw_line", start_x=10, start_y=0, end_x=10, end_y=10)
    assert api.llamar(s, "extrude", {"sketch": "Boceto1"})["error_kind"] == "PROFILE_NOT_CLOSED"   # no se cierra
    llamar(s, "draw_rectangle", x1=0, y1=0, x2=5, y2=5)
    antes = foto(s)
    casos = [({"sketch": "Boceto1", "target": "Cuerpo9", "operation": "cut"}, "BODY_NOT_FOUND"),
             ({"sketch": "Boceto1", "operation": "cut"}, "NO_TARGET_BODY"),              # no hay qué cortar
             ({"sketch": "Boceto1", "distance": 0}, "OPERATION_FAILED"),
             ({"sketch": "Boceto1", "distance": "sin_param"}, "INVALID_EXPRESSION"),
             ({"sketch": "Boceto1", "operation": "pegar"}, "INVALID_ARGUMENTS"),
             ({"sketch": "Boceto1", "direction": "dos"}, "INVALID_ARGUMENTS")]
    for args, kind in casos:
        r = api.llamar(s, "extrude", args)
        assert r["error_kind"] == kind, (args, r)
        assert foto(s) == antes


# ---------------------------------------------------------------- extrusión: opciones
def _cuadrado(s, plano="XY", lado=10, **kw):
    llamar(s, "create_sketch", plane=plano, **kw)
    llamar(s, "draw_rectangle", x1=10, y1=5, x2=10 + lado, y2=5 + lado)


@pytest.mark.parametrize("plano, esperado", [
    ("XY", ([10, 5, 0], [20, 15, 3])),
    ("XZ", ([10, -3, 5], [20, 0, 15])),            # x→X, y→Z, la normal es −Y
    ("YZ", ([0, 10, 5], [3, 20, 15])),             # x→Y, y→Z, la normal es +X
])
def test_orientacion_de_las_coordenadas_en_cada_plano(s, plano, esperado):
    _cuadrado(s, plano)
    r = llamar(s, "extrude", sketch="Boceto1", distance=3)
    assert caja(s, r["bodies_created"][0]["id"]) == pytest.approx(esperado, abs=1e-6)


def test_direcciones_inversa_simetrica_y_dos_lados(s):
    _cuadrado(s)
    a = llamar(s, "extrude", sketch="Boceto1", distance=6, reverse=True)["bodies_created"][0]["id"]
    b = llamar(s, "extrude", sketch="Boceto1", distance=6, direction="symmetric")["bodies_created"][0]["id"]
    c = llamar(s, "extrude", sketch="Boceto1", distance=6, distance2=2, direction="two_sides")["bodies_created"][0]["id"]
    d = llamar(s, "extrude", sketch="Boceto1", distance=4, direction="two_sides")["bodies_created"][0]["id"]
    assert caja(s, a)[0][2] == -6 and caja(s, a)[1][2] == 0
    assert (caja(s, b)[0][2], caja(s, b)[1][2]) == (-3, 3)                      # distance = largo total
    assert (caja(s, c)[0][2], caja(s, c)[1][2]) == (-2, 6)
    assert (caja(s, d)[0][2], caja(s, d)[1][2]) == (-4, 4)
    assert volumen(s, c) == pytest.approx(100 * 8)


def test_conicidad(s):
    _cuadrado(s)
    for grados, signo in ((5, 1), (-5, -1)):                                   # positivo ensancha, negativo estrecha
        r = llamar(s, "extrude", sketch="Boceto1", distance=10, taper_angle=grados)["bodies_created"][0]
        lado = 10 + signo * 2 * 10 * math.tan(math.radians(5))
        assert r["volume"] == pytest.approx(10 / 3 * (100 + lado * lado + 10 * lado), rel=2e-3)


def test_seleccion_de_perfiles(s):
    llamar(s, "create_sketch")
    llamar(s, "draw_rectangle", x1=0, y1=0, x2=40, y2=20)
    llamar(s, "draw_circle", radius=5, center_x=10, center_y=10)
    llamar(s, "draw_circle", radius=3, center_x=30, center_y=10)
    perfiles = llamar(s, "get_sketch")["profiles"]
    assert len(perfiles) == 3                                                  # la placa con dos agujeros y los dos discos
    mayor = llamar(s, "extrude", sketch="Boceto1", profile="largest", distance=2)
    assert mayor["profiles_used"] == [max(perfiles, key=lambda p: p["area"])["index"]]
    assert mayor["bodies_created"][0]["volume"] == pytest.approx((800 - math.pi * 34) * 2, rel=1e-3)
    discos = [p["index"] for p in perfiles if p["area"] < 100]
    dos = llamar(s, "extrude", sketch="Boceto1", profile=discos, distance=2)
    assert sum(b["volume"] for b in dos["bodies_created"]) == pytest.approx(math.pi * 34 * 2, rel=1e-3)
    todo = llamar(s, "extrude", sketch="Boceto1", profile="all", distance=2)
    assert sum(b["volume"] for b in todo["bodies_created"]) == pytest.approx(800 * 2, rel=1e-3)
    assert llamar(s, "extrude", sketch="Boceto1", profile=discos[0], distance=1)["profiles_used"] == [discos[0]]


def test_operaciones_y_target(s):
    llamar(s, "create_box", length=40, width=40, height=10, x=20, y=20)
    llamar(s, "create_box", length=10, width=10, height=10, x=100, y=20)
    llamar(s, "create_sketch")
    llamar(s, "draw_circle", radius=5, center_x=20, center_y=20)
    # cortar solo el segundo cuerpo (que no toca): no cambia nada y avisa
    r = api.llamar(s, "extrude", {"sketch": "Boceto1", "distance": 10, "operation": "cut", "target": "Cuerpo2"})
    assert r["ok"] and all(m["volume"] == m["previous_volume"] for m in r["result"]["bodies_modified"])
    assert any("no cambió el volumen" in a for a in r["avisos"])
    # sin target corta el que toca
    r = llamar(s, "extrude", sketch="Boceto1", distance=10, operation="cut")
    assert [b["id"] for b in r["bodies_modified"]] == ["op1.c1"]
    assert r["bodies_modified"][0]["volume"] == pytest.approx(16000 - math.pi * 25 * 10, rel=1e-6)
    r = api.llamar(s, "extrude", {"sketch": "Boceto1", "distance": 20, "operation": "intersect", "target": "Cuerpo1"})
    assert r["ok"] and r["result"]["bodies_removed"] == ["op1.c1"] and any("vacío" in a for a in r["avisos"])
    # target con new_body se ignora con aviso
    ok_ = api.llamar(s, "extrude", {"sketch": "Boceto1", "distance": 1, "target": "Cuerpo2"})
    assert ok_["ok"] and any("ignora" in a for a in ok_["avisos"])


# ---------------------------------------------------------------- revolución, barrido y solevación
def test_revolucion(s):
    llamar(s, "create_sketch", plane="XZ")
    llamar(s, "draw_rectangle", x1=80, y1=0, x2=86, y2=12)
    aro = llamar(s, "revolve", sketch="Boceto1", profile=0, axis="sketch_y")["bodies_created"][0]
    assert aro["volume"] == pytest.approx(math.pi * (86 ** 2 - 80 ** 2) * 12, rel=1e-6)
    mitad = llamar(s, "revolve", sketch="Boceto1", profile=0, axis="z", angle=180)["bodies_created"][0]
    assert mitad["volume"] == pytest.approx(aro["volume"] / 2, rel=1e-6)
    sim = llamar(s, "revolve", sketch="Boceto1", profile=0, axis="Z", angle="90 deg", direction="symmetric")
    assert sim["bodies_created"][0]["volume"] == pytest.approx(aro["volume"] / 4, rel=1e-6)
    dos = llamar(s, "revolve", sketch="Boceto1", profile=0, axis="z", angle=90, angle2=45, direction="two_sides")
    assert dos["bodies_created"][0]["volume"] == pytest.approx(aro["volume"] * 135 / 360, rel=1e-6)
    linea = llamar(s, "draw_line", start_x=0, start_y=0, end_x=0, end_y=20, construction=True)["entities"][0]["id"]
    eje = llamar(s, "revolve", sketch="Boceto1", profile=0, axis=linea)
    assert eje["bodies_created"][0]["volume"] == pytest.approx(aro["volume"], rel=1e-6)
    llamar(s, "create_parameter", name="giro", expression="90 deg")
    r = llamar(s, "revolve", sketch="Boceto1", profile=0, axis="z", angle="giro")
    assert r["bodies_created"][0]["volume"] == pytest.approx(aro["volume"] / 4, rel=1e-6)
    llamar(s, "set_parameter", name="giro", expression="180 deg")
    assert cuerpos(s)[r["bodies_created"][0]["id"]]["volume"] == pytest.approx(aro["volume"] / 2, rel=1e-6)
    for axis in ("w", 99, "5x"):
        assert api.llamar(s, "revolve", {"sketch": "Boceto1", "profile": 0, "axis": axis})["error_kind"] == "INVALID_AXIS"
    assert api.llamar(s, "revolve", {"sketch": "Boceto1", "profile": 0, "axis": "1"})["error_kind"] == "INVALID_AXIS"   # un punto


def test_barrido_y_solevacion(s):
    llamar(s, "sketch_from_spec", name="Perfil", entities=[{"type": "circle", "center": [0, 0], "radius": 3}])
    llamar(s, "sketch_from_spec", plane="XZ", name="Ruta", entities=[{"type": "line", "start": [0, 0], "end": [0, 30]}])
    r = llamar(s, "sweep", sketch="Perfil", profile=0, path_sketch="Ruta")
    assert r["bodies_created"][0]["volume"] == pytest.approx(math.pi * 9 * 30, rel=1e-4)
    assert api.llamar(s, "sweep", {"sketch": "Perfil", "profile": 0, "path_sketch": "Ruta", "path_curves": [99]})["error_kind"] \
        == "ENTITY_NOT_FOUND"
    llamar(s, "create_construction_plane", plane="XY", offset=20, name="Alto")
    llamar(s, "sketch_from_spec", name="Base", entities=[{"type": "rectangle", "center": [0, 0], "width": 10, "height": 10}])
    llamar(s, "sketch_from_spec", plane="Alto", name="Tope", entities=[{"type": "rectangle", "center": [0, 0], "width": 4, "height": 4}])
    tronco = llamar(s, "loft", sketches=["Base", "Tope"])["bodies_created"][0]
    assert tronco["volume"] == pytest.approx(20 / 3 * (100 + 16 + math.sqrt(1600)), rel=1e-4)
    assert api.llamar(s, "loft", {"sketches": ["Base"]})["error_kind"] == "INVALID_ARGUMENTS"
    assert api.llamar(s, "loft", {"sketches": ["Base", "Tope"], "profiles": [0]})["error_kind"] == "INVALID_ARGUMENTS"
    assert api.llamar(s, "loft", {"sketches": ["Base", "Nada"]})["error_kind"] == "SKETCH_NOT_FOUND"


# ---------------------------------------------------------------- primitivas
def test_primitivas_y_su_posicion(s):
    llamar(s, "create_parameter", name="largo", expression="20 mm")
    caja_ = llamar(s, "create_box", length="largo", width=10, height=5, x=100, y=50, z=7)["bodies_created"][0]
    assert caja_["volume"] == pytest.approx(1000) and caja(s, caja_["id"]) == pytest.approx(([90, 45, 7], [110, 55, 12]))
    cil = llamar(s, "create_cylinder", radius=2, height=10, x=1, y=2, z=3)["bodies_created"][0]
    assert cil["volume"] == pytest.approx(math.pi * 40) and caja(s, cil["id"]) == pytest.approx(([-1, 0, 3], [3, 4, 13]))
    esf = llamar(s, "create_sphere", radius=3, x=-10, y=0, z=0)["bodies_created"][0]
    assert esf["volume"] == pytest.approx(4 / 3 * math.pi * 27)
    tor = llamar(s, "create_torus", major_radius=12, minor_radius=3, x=0, y=0, z=40)["bodies_created"][0]
    assert tor["volume"] == pytest.approx(2 * math.pi ** 2 * 12 * 9) and caja(s, tor["id"])[0][2] == pytest.approx(37)
    llamar(s, "set_parameter", name="largo", expression="40 mm")
    assert volumen(s, caja_["id"]) == pytest.approx(2000) and caja(s, caja_["id"])[0][0] == pytest.approx(80)
    assert [b["name"] for b in llamar(s, "get_scene_info")["bodies"]] == ["Cuerpo1", "Cuerpo2", "Cuerpo3", "Cuerpo4"]
    assert [p["name"] for p in llamar(s, "get_timeline", include_params=False)["steps"]] == \
        ["Caja1", "Cilindro1", "Esfera1", "Toroide1"]


def test_primitivas_con_operacion_y_errores(s):
    base = llamar(s, "create_box", length=20, width=20, height=10)["bodies_created"][0]
    r = llamar(s, "create_cylinder", radius=3, height=10, operation="cut", target=base["id"])
    assert r["bodies_modified"][0]["volume"] == pytest.approx(4000 - math.pi * 90, rel=1e-6) and not r["bodies_created"]
    r = llamar(s, "create_sphere", radius=4, z=10, operation="join")
    assert r["bodies_modified"][0]["volume"] > 4000 - math.pi * 90
    antes = foto(s)
    for nombre, args, kind in (("create_box", {"length": 0, "width": 1, "height": 1}, "INVALID_ARGUMENTS"),
                               ("create_cylinder", {"radius": 1, "height": -2}, "INVALID_ARGUMENTS"),
                               ("create_sphere", {"radius": "r_inexistente"}, "INVALID_EXPRESSION"),
                               ("create_torus", {"major_radius": 2, "minor_radius": 3}, "OPERATION_FAILED"),
                               ("create_box", {"length": 1, "width": 1, "height": 1, "operation": "cut", "target": "x"},
                                "BODY_NOT_FOUND")):
        assert api.llamar(s, nombre, args)["error_kind"] == kind, (nombre, args)
        assert foto(s) == antes


# ---------------------------------------------------------------- booleanas, simetría, patrones y movimiento
def test_operaciones_booleanas(s):
    a = llamar(s, "create_box", length=20, width=20, height=20)["bodies_created"][0]["id"]
    b = llamar(s, "create_box", length=20, width=20, height=20, x=10)["bodies_created"][0]["id"]
    r = llamar(s, "boolean_operation", target=a, tools=[b], operation="intersect", keep_tools=True)
    assert r["bodies_modified"][0]["volume"] == pytest.approx(10 * 20 * 20) and r["bodies_removed"] == []
    ok(api.llamar(s, "undo"))
    r = llamar(s, "boolean_operation", target=a, tools=[b])
    assert r["bodies_modified"][0]["volume"] == pytest.approx(30 * 20 * 20) and r["bodies_removed"] == [b]
    assert api.llamar(s, "boolean_operation", {"target": a, "tools": [a]})["error_kind"] == "OPERATION_FAILED"
    assert api.llamar(s, "boolean_operation", {"target": "zz", "tools": [a]})["error_kind"] == "BODY_NOT_FOUND"


def test_simetria(s):
    cubo = llamar(s, "create_box", length=10, width=10, height=10, x=25, y=10)["bodies_created"][0]["id"]
    esp = llamar(s, "mirror", bodies=cubo, plane="YZ")["bodies_created"][0]
    assert caja(s, esp["id"]) == pytest.approx(([-30, 5, 0], [-20, 15, 10]))
    unido = llamar(s, "mirror", bodies=[cubo], plane="XZ", combine=True)
    assert unido["bodies_modified"][0]["volume"] == pytest.approx(2000) and unido["bodies_created"] == []
    assert caja(s, cubo) == pytest.approx(([20, -15, 0], [30, 15, 10]))
    llamar(s, "create_construction_plane", plane="YZ", offset=40, name="Espejo")
    otro = llamar(s, "mirror", bodies=esp["id"], plane="Espejo")["bodies_created"][0]
    assert caja(s, otro["id"]) == pytest.approx(([100, 5, 0], [110, 15, 10]))


def test_patron_rectangular(s):
    cubo = llamar(s, "create_box", length=10, width=10, height=10, x=-25)["bodies_created"][0]["id"]
    r = llamar(s, "rectangular_pattern", bodies=cubo, x_count=3, x_spacing=20, y_count=2, y_spacing=30, axis2="z")
    minimos = sorted(tuple(caja(s, b["id"])[0]) for b in r["bodies_created"])
    assert minimos == [(-30, -5, 30), (-10, -5, 0), (-10, -5, 30), (10, -5, 0), (10, -5, 30)]
    assert all(b["volume"] == pytest.approx(1000) for b in r["bodies_created"])
    junto = llamar(s, "rectangular_pattern", bodies=cubo, x_count=2, x_spacing=15, combine=True)
    assert junto["bodies_created"] == [] and junto["bodies_modified"][0]["volume"] == pytest.approx(2000)


def test_patron_circular(s):
    cubo = llamar(s, "create_box", length=10, width=10, height=10, x=25)["bodies_created"][0]["id"]
    circ = llamar(s, "circular_pattern", bodies=cubo, count=4, axis="z")
    assert len(circ["bodies_created"]) == 3
    assert caja(s, circ["bodies_created"][0]["id"]) == pytest.approx(([-5, 20, 0], [5, 30, 10]), abs=1e-6)   # 90°
    assert caja(s, circ["bodies_created"][1]["id"]) == pytest.approx(([-30, -5, 0], [-20, 5, 10]), abs=1e-6)  # 180°
    medio = llamar(s, "circular_pattern", bodies=cubo, count=3, axis="z", total_angle=180)
    assert caja(s, medio["bodies_created"][1]["id"]) == pytest.approx(([-30, -5, 0], [-20, 5, 10]), abs=1e-6)
    ejex = llamar(s, "circular_pattern", bodies=cubo, count=2, axis="x")
    assert caja(s, ejex["bodies_created"][0]["id"]) == pytest.approx(([20, -5, -10], [30, 5, 0]), abs=1e-6)


@pytest.mark.parametrize("nombre, args, kind", [
    ("rectangular_pattern", {"bodies": "Cuerpo1"}, "INVALID_ARGUMENTS"),
    ("rectangular_pattern", {"bodies": "Cuerpo1", "x_count": 0}, "INVALID_ARGUMENTS"),
    ("rectangular_pattern", {"bodies": "Cuerpo1", "y_count": 2, "axis1": "x", "axis2": "x"}, "INVALID_ARGUMENTS"),
    ("circular_pattern", {"bodies": "Cuerpo1", "count": 1}, "INVALID_ARGUMENTS"),
    ("circular_pattern", {"bodies": "Cuerpo9", "count": 3}, "BODY_NOT_FOUND"),
    ("mirror", {"bodies": []}, "INVALID_ARGUMENTS"),
    ("mirror", {"bodies": "Cuerpo1", "plane": "Q"}, "PLANE_NOT_FOUND"),
])
def test_errores_de_patrones_y_simetria(s, nombre, args, kind):
    llamar(s, "create_box", length=10, width=10, height=10)
    antes = foto(s)
    assert api.llamar(s, nombre, args)["error_kind"] == kind
    assert foto(s) == antes


def test_mover_cuerpos(s):
    llamar(s, "create_parameter", name="sube", expression="50 mm")
    cubo = llamar(s, "create_box", length=10, width=10, height=10)["bodies_created"][0]["id"]
    r = llamar(s, "move_body", body=cubo, translate=[5, 0, "sube"])
    assert caja(s, cubo) == pytest.approx(([0, -5, 50], [10, 5, 60])) and r["bodies_modified"][0]["id"] == cubo
    llamar(s, "move_body", body=cubo, rotate=[0, 0, 90])                         # gira sobre su propio centro
    assert caja(s, cubo) == pytest.approx(([0, -5, 50], [10, 5, 60]), abs=1e-6)
    llamar(s, "move_body", body=cubo, rotate=[0, 0, 90], pivot="origin")         # alrededor del origen del diseño
    assert caja(s, cubo) == pytest.approx(([-5, 0, 50], [5, 10, 60]), abs=1e-6)
    copia = llamar(s, "move_body", body=cubo, translate=[100, 0, 0], copy=True)
    assert len(copia["bodies_created"]) == 1 and caja(s, copia["bodies_created"][0]["id"])[0][0] == pytest.approx(95)
    llamar(s, "set_parameter", name="sube", expression="10 mm")
    assert caja(s, cubo)[0][2] == pytest.approx(10)
    assert api.llamar(s, "move_body", {"body": cubo, "translate": [1, 2]})["error_kind"] == "INVALID_ARGUMENTS"
    assert api.llamar(s, "move_body", {"body": "nada"})["error_kind"] == "BODY_NOT_FOUND"


# ---------------------------------------------------------------- un paso de deshacer por herramienta
@pytest.mark.parametrize("nombre, args", [
    ("create_box", {"length": 5, "width": 5, "height": 5}),
    ("create_cylinder", {"radius": 2, "height": 5}),
    ("move_body", {"body": "Cuerpo1", "translate": [1, 1, 1]}),
    ("mirror", {"bodies": "Cuerpo1", "plane": "XY"}),
    ("circular_pattern", {"bodies": "Cuerpo1", "count": 3}),
    ("extrude", {"sketch": "Boceto1", "distance": 3}),
])
def test_cada_herramienta_es_un_paso_de_deshacer(s, nombre, args):
    llamar(s, "create_box", length=10, width=10, height=10, x=30)
    llamar(s, "create_sketch")
    llamar(s, "draw_rectangle", x1=0, y1=0, x2=5, y2=5)
    pila, antes = len(s.doc._deshacer), foto(s)[0]
    ok(api.llamar(s, nombre, args))
    assert len(s.doc._deshacer) == pila + 1
    ok(api.llamar(s, "undo"))
    assert foto(s)[0] == antes


def test_guardar_y_abrir_conserva_el_modelo(s, tmp_path):
    for nombre, args in SOPORTE_EN_L:
        ok(api.llamar(s, nombre, args))
    ruta = llamar(s, "save_document", path=str(tmp_path / "soporte"))["path"]
    otra = api.Sesion()
    llamar(otra, "open_document", path=ruta)
    assert volumen(otra) == pytest.approx(VOLUMEN_L, rel=1e-3)
    llamar(otra, "extrude", sketch="Pared", distance=2, operation="join", reverse=True)     # los ids estables siguen valiendo

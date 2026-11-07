"""Matriz de la auditoría de CREAR y MODIFICAR del boceto (fase 1), sin ventana, por la API (la misma del MCP y la CLI).

Un caso por comando o variante de la cinta: lo arma por la API y comprueba con números (largos, radios, centros, áreas
de perfiles) que el resultado es el que dicen las entradas; después, que la receta guardada y vuelta a abrir
(`get_recipe` → `apply_recipe`) da el mismo boceto. Inventario: docs/auditorias/boceto_crear_modificar_inventario.md.
"""
import math

import pytest

from omnicad import api


def _ok(r):
    assert r["ok"], r
    return r["result"]


def L(s, nombre, **args):
    return _ok(api.llamar(s, nombre, {"sketch": "B", **args} if nombre not in _SIN_BOCETO else args))


_SIN_BOCETO = {"create_parameter", "set_parameter"}


def _ids(r):
    return [e["id"] for e in r["entities"]]


def _ents(s):
    return L(s, "get_sketch")["entities"]


def _de(s, tipo, construccion=False):
    return [e for e in _ents(s) if e["type"] == tipo and e["construction"] == construccion]


def _areas(s):
    return sorted(p["area"] for p in L(s, "get_sketch")["profiles"])


def _dist_recta(xy, linea):
    (x1, y1), (x2, y2) = linea["start"], linea["end"]
    return abs((x2 - x1) * (y1 - xy[1]) - (x1 - xy[0]) * (y2 - y1)) / math.hypot(x2 - x1, y2 - y1)


def _rect(s, x1=0, y1=0, x2=60, y2=40):
    """Ids de las 4 líneas: abajo, derecha, arriba, izquierda."""
    return _ids(L(s, "draw_rectangle", x1=x1, y1=y1, x2=x2, y2=y2))


def _ap(v, abs=2e-4):             # get_sketch redondea a 4 decimales
    return pytest.approx(v, abs=abs)


# ---------------------------------------------------------------- CREAR
def linea(s):
    L(s, "draw_line", start_x=0, start_y=0, end_x=30, end_y=40)
    assert _de(s, "line")[0]["length"] == _ap(50)


def linea_medio(s):
    L(s, "draw_line", start_x=0, start_y=0, end_x=10, end_y=0, midpoint=True)
    (e,) = _de(s, "line")
    assert sorted([tuple(e["start"]), tuple(e["end"])]) == [(-10, 0), (10, 0)]


def rectangulo(s):
    _rect(s)
    assert _areas(s) == [_ap(2400)]


def rectangulo_3p(s):
    L(s, "draw_rectangle", three_points=[[0, 0], [30, 30], [20, 40]])
    lados = sorted(round(e["length"], 6) for e in _de(s, "line"))
    assert lados == _ap([math.hypot(10, 10)] * 2 + [math.hypot(30, 30)] * 2)
    assert _areas(s) == [_ap(math.hypot(30, 30) * math.hypot(10, 10))]


def rectangulo_centro(s):
    L(s, "draw_rectangle", center_x=5, center_y=-5, width=20, height=10, center_diagonals=True)   # como el editor
    assert len(_de(s, "line", construccion=True)) == 2
    p = L(s, "get_sketch")["profiles"][0]
    assert p["bounding_box"] == {"min": _ap([-5, -10]), "max": _ap([15, 0])}


def circulo(s):
    L(s, "draw_circle", radius=5, center_x=2, center_y=3)
    (c,) = _de(s, "circle")
    assert (c["center"], c["radius"]) == (_ap([2, 3]), _ap(5))


def circulo_2p(s):
    L(s, "draw_circle", kind="two_points", points=[[0, 0], [10, 0]])
    (c,) = _de(s, "circle")
    assert (c["center"], c["radius"]) == (_ap([5, 0]), _ap(5))


def circulo_3p(s):
    L(s, "draw_circle", kind="three_points", points=[[5, 0], [0, 5], [-5, 0]])
    (c,) = _de(s, "circle")
    assert (c["center"], c["radius"]) == (_ap([0, 0]), _ap(5))


def circulo_2t(s):
    a = _ids(L(s, "draw_line", start_x=0, start_y=0, end_x=40, end_y=0))[0]
    b = _ids(L(s, "draw_line", start_x=0, start_y=0, end_x=0, end_y=40))[0]
    L(s, "draw_tangent_circle", lines=[a, b], radius=5, x=6, y=6)
    (c,) = _de(s, "circle")
    assert (c["center"], c["radius"]) == (_ap([5, 5]), _ap(5))


def circulo_3t(s):
    lados = [_ids(L(s, "draw_line", start_x=x1, start_y=y1, end_x=x2, end_y=y2))[0]
             for x1, y1, x2, y2 in ((0, 0, 30, 0), (30, 0, 0, 40), (0, 40, 0, 0))]
    L(s, "draw_tangent_circle", lines=lados, x=8, y=8)
    (c,) = _de(s, "circle")
    assert (c["center"], c["radius"]) == (_ap([10, 10]), _ap(10))           # triángulo 30-40-50: r = 10


def arco_3p(s):
    L(s, "draw_arc", start_x=10, start_y=0, mid_x=0, mid_y=10, end_x=-10, end_y=0)
    (a,) = _de(s, "arc")
    assert (a["center"], a["radius"]) == (_ap([0, 0]), _ap(10))


def arco_centro(s):
    L(s, "draw_arc", start_x=10, start_y=0, center_x=0, center_y=0, sweep_angle=90)
    (a,) = _de(s, "arc")
    assert (a["radius"], a["end"]) == (_ap(10), _ap([0, 10]))


def arco_tangente(s):
    ln = _ids(L(s, "draw_line", start_x=0, start_y=0, end_x=20, end_y=0))[0]
    L(s, "draw_arc", start_x=20, start_y=0, end_x=20, end_y=10, tangent_to=ln)
    (a,) = _de(s, "arc")
    (linea_e,) = _de(s, "line")
    assert _dist_recta(a["center"], linea_e) == _ap(a["radius"])
    assert a["radius"] == _ap(5)


def _poligono(kind, radio_vertice):
    def caso(s):
        L(s, "create_polygon", sides=6, radius=10, center_x=0, center_y=0, kind=kind)
        lados = _de(s, "line")
        assert len(lados) == 6
        assert [math.hypot(*e["start"]) for e in lados] == _ap([radio_vertice] * 6)
    return caso


def poligono_arista(s):
    L(s, "create_polygon", sides=4, kind="edge", edge_points=[[0, 0], [10, 0], [5, 5]], radius=1)
    lados = _de(s, "line")
    assert len(lados) == 4 and {round(e["length"], 6) for e in lados} == {10}
    assert _areas(s) == [_ap(100)]


def elipse(s):
    L(s, "draw_ellipse", major_radius=8, minor_radius=3, center_x=1, center_y=2, angle=30)
    (e,) = _de(s, "ellipse")
    assert (e["center"], e["major_radius"], e["minor_radius"], e["angle"]) == (_ap([1, 2]), _ap(8), _ap(3), _ap(30))
    assert _areas(s) == [_ap(math.pi * 8 * 3, abs=1e-3)]


_AREA_RANURA = 30 * 10 + math.pi * 25
_AREA_ARCO = math.pi * (15 ** 2 - 5 ** 2) / 2 + math.pi * 25     # media corona + los dos extremos


def _ranura(kind, puntos, area):
    def caso(s):
        L(s, "draw_slot", kind=kind, points=puntos, width=10)
        assert _areas(s) == [_ap(area, abs=1e-3)]
    return caso


def spline(tipo):
    def caso(s):
        L(s, "draw_spline", points=[[0, 0], [10, 8], [20, 0], [30, 5]], spline_type=tipo)
        (e,) = _de(s, "spline")
        assert e["spline_type"] == tipo and sum(e["vertices"], []) == _ap([0, 0, 10, 8, 20, 0, 30, 5])
    return caso


def conica(s):
    L(s, "draw_conic", start_x=0, start_y=0, end_x=20, end_y=0, vertex_x=10, vertex_y=10, rho=0.3)
    (e,) = _de(s, "conic")
    assert (e["start"], e["vertex"], e["end"], e["rho"]) == (_ap([0, 0]), _ap([10, 10]), _ap([20, 0]), _ap(0.3))


def punto(s):
    p = L(s, "draw_point", x=3, y=4)["points"][0]
    assert {q["id"]: (q["x"], q["y"]) for q in L(s, "get_sketch")["points"]}[p] == _ap((3, 4))


def texto(s):
    L(s, "add_text", text="OH", x=0, y=0, height=10)
    (t,) = _de(s, "text")
    assert t["text"] == "OH"
    assert len(_areas(s)) >= 2                                   # la O tiene agujero; la H, un contorno


def desglosar_texto(s):
    t = _ids(L(s, "add_text", text="L", x=0, y=0, height=10))[0]
    L(s, "explode_text", entity=t)
    assert not _de(s, "text") and len(_ents(s)) >= 6              # la L queda como sus segmentos
    assert len(_areas(s)) == 1


def simetria(s):
    eje = _ids(L(s, "draw_line", start_x=0, start_y=-10, end_x=0, end_y=10, construction=True))[0]
    c = _ids(L(s, "draw_circle", radius=2, center_x=5, center_y=3))[0]
    L(s, "mirror_sketch", entities=[c], axis=eje)
    assert sorted(tuple(e["center"]) for e in _de(s, "circle")) == [_ap((-5, 3)), _ap((5, 3))]


def patron_circular(s):
    c = _ids(L(s, "draw_circle", radius=1, center_x=10, center_y=0))[0]
    L(s, "sketch_circular_pattern", entities=[c], count=4)
    assert sorted(tuple(round(v, 6) for v in e["center"]) for e in _de(s, "circle")) == \
        [(-10, 0), (0, -10), (0, 10), (10, 0)]


def patron_rectangular(s):
    c = _ids(L(s, "draw_circle", radius=1, center_x=0, center_y=0))[0]
    L(s, "sketch_rectangular_pattern", entities=[c], count1=3, distance1=20, count2=2, distance2=5)
    assert sorted(tuple(round(v, 6) for v in e["center"]) for e in _de(s, "circle")) == \
        [(0, 0), (0, 5), (10, 0), (10, 5), (20, 0), (20, 5)]


def editar_patron(s):
    c = _ids(L(s, "draw_circle", radius=1, center_x=10, center_y=0))[0]
    r = L(s, "sketch_circular_pattern", entities=[c], count=4)
    L(s, "edit_sketch_pattern", pattern=r["pattern"], count=6)
    assert len(_de(s, "circle")) == 6


def cota(s):
    abajo = _rect(s)[0]
    L(s, "add_dimension", type="distance", entities=[abajo], value=80)
    assert _areas(s) == [_ap(80 * 40, abs=1e-3)]


def espiral(s):
    L(s, "draw_spiral", center=[0, 0], start=[5, 0], turns=3, pitch=2)
    (e,) = _de(s, "spline")
    assert len(e["vertices"]) == 25 and e["vertices"][0] == _ap([5, 0]) and e["vertices"][-1] == _ap([11, 0])


# ---------------------------------------------------------------- MODIFICAR
def empalme(s):
    abajo, derecha, *_ = _rect(s)
    L(s, "sketch_fillet", entity1=abajo, entity2=derecha, radius=5)
    (a,) = _de(s, "arc")
    assert a["radius"] == _ap(5) and a["center"] == _ap([55, 5])
    assert _areas(s) == [_ap(2400 - 25 * (1 - math.pi / 4), abs=1e-3)]


def _chaflan(**opciones):
    def caso(s):
        abajo, derecha, *_ = _rect(s)
        L(s, "sketch_chamfer", line1=abajo, line2=derecha, **opciones)
        d1 = opciones["distance"]
        d2 = opciones.get("distance2") or (d1 * math.tan(math.radians(opciones["angle"])) if "angle" in opciones else d1)
        assert len(_de(s, "line")) == 5
        assert _areas(s) == [_ap(2400 - d1 * d2 / 2, abs=1e-3)]
    return caso


def curva_fusion(s):
    a = _ids(L(s, "draw_line", start_x=0, start_y=0, end_x=10, end_y=0))[0]
    b = _ids(L(s, "draw_line", start_x=20, start_y=5, end_x=30, end_y=5))[0]
    L(s, "draw_blend_curve", entity1=a, entity2=b, point1=[10, 0], point2=[20, 5])
    (sp,) = _de(s, "spline")
    assert (sp["vertices"][0], sp["vertices"][-1]) == (_ap([10, 0]), _ap([20, 5]))


def desfase(s):
    abajo = _rect(s)[0]
    L(s, "offset_sketch_curves", entity=abajo, distance=2, side_x=-50, side_y=-50)
    assert _areas(s) == [_ap(64 * 44 - 2400, abs=1e-3), _ap(2400)]            # el anillo y el original


def soltar_desfase(s):
    abajo = _rect(s)[0]
    nuevos = _ids(L(s, "offset_sketch_curves", entity=abajo, distance=2, side_x=-50, side_y=-50))
    L(s, "release_offset", entity=nuevos[0])
    tipos = {c["type"] for c in L(s, "get_sketch")["constraints"]}
    assert "offset" not in tipos and _areas(s) == [_ap(64 * 44 - 2400, abs=1e-3), _ap(2400)]


def recortar(s):
    _ids(L(s, "draw_line", start_x=0, start_y=0, end_x=20, end_y=0))
    _ids(L(s, "draw_line", start_x=10, start_y=-10, end_x=10, end_y=10))
    L(s, "trim_sketch_curve", entity=_de(s, "line")[0]["id"], x=15, y=0)
    largos = sorted(round(e["length"], 6) for e in _de(s, "line"))
    assert largos == [10, 20]


def alargar(s):
    a = _ids(L(s, "draw_line", start_x=0, start_y=0, end_x=5, end_y=0))[0]
    L(s, "draw_line", start_x=10, start_y=-10, end_x=10, end_y=10)
    L(s, "extend_sketch_curve", curve=a, point=[5, 0])
    assert next(e for e in _de(s, "line") if e["id"] == a)["length"] == _ap(10)


def partir(s):
    a = _ids(L(s, "draw_line", start_x=0, start_y=0, end_x=20, end_y=0))[0]
    L(s, "draw_line", start_x=8, start_y=-10, end_x=8, end_y=10)
    L(s, "split_sketch_curve", curve=a, point=[4, 0])
    largos = sorted(round(e["length"], 6) for e in _de(s, "line"))
    assert largos == [8, 12, 20]


def escala(s):
    lados = _rect(s, 0, 0, 10, 5)
    L(s, "transform_sketch", entities=lados, scale=2, center_x=0, center_y=0)
    assert _areas(s) == [_ap(200, abs=1e-3)]


def mover(s):
    lados = _rect(s, 1, 1, 11, 6)                  # fuera del origen: lo anclado al origen no se mueve
    L(s, "transform_sketch", entities=lados, dx=7, dy=-3)
    p = L(s, "get_sketch")["profiles"][0]
    assert p["bounding_box"] == {"min": _ap([8, -2]), "max": _ap([18, 3])}


def copiar(s):
    lados = _rect(s, 0, 0, 10, 5)
    L(s, "transform_sketch", entities=lados, dx=20, copy=True)
    assert _areas(s) == [_ap(50), _ap(50)]


def cambiar_parametros(s):
    abajo = _rect(s)[0]
    L(s, "create_parameter", name="ancho", expression="70 mm")
    L(s, "add_dimension", type="distance", entities=[abajo], value="ancho")
    L(s, "set_parameter", name="ancho", expression="90 mm")
    assert _areas(s) == [_ap(90 * 40, abs=1e-3)]


CASOS = {
    "sk_linea": linea, "sk_linea_medio": linea_medio,
    "sk_rectangulo": rectangulo, "sk_rectangulo_3p": rectangulo_3p, "sk_rectangulo_centro": rectangulo_centro,
    "sk_circulo": circulo, "sk_circulo_2p": circulo_2p, "sk_circulo_3p": circulo_3p,
    "sk_circulo_2t": circulo_2t, "sk_circulo_3t": circulo_3t,
    "sk_arco": arco_3p, "sk_arco_centro": arco_centro, "sk_arco_tangente": arco_tangente,
    "sk_poligono_inscrito": _poligono("inscribed", 10),
    "sk_poligono_circunscrito": _poligono("circumscribed", 10 / math.cos(math.radians(30))),
    "sk_poligono_arista": poligono_arista,
    "sk_elipse": elipse,
    "sk_ranura_centro": _ranura("center_to_center", [[0, 0], [30, 0]], _AREA_RANURA),
    "sk_ranura_total": _ranura("overall", [[-5, 0], [35, 0]], _AREA_RANURA),
    "sk_ranura_punto": _ranura("center_point", [[15, 0], [30, 0]], _AREA_RANURA),
    "sk_ranura_arco_3p": _ranura("arc_three_points", [[10, 0], [-10, 0], [0, 10]], _AREA_ARCO),
    "sk_ranura_arco_centro": _ranura("arc_center", [[0, 0], [10, 0], [-10, 0]], _AREA_ARCO),
    "sk_spline_ajuste": spline("fit_points"), "sk_spline_control": spline("control_points"),
    "sk_conica": conica, "sk_punto": punto, "sk_texto": texto, "sk_desglosar_texto": desglosar_texto,
    "sk_simetria": simetria, "sk_patron_circular": patron_circular, "sk_patron_rectangular": patron_rectangular,
    "sk_editar_patron": editar_patron, "sk_cota": cota, "sk_espiral": espiral,
    "sk_empalme": empalme,
    "sk_chaflan": _chaflan(distance=5), "sk_chaflan_dist_angulo": _chaflan(distance=5, angle=30),
    "sk_chaflan_dos_dist": _chaflan(distance=5, distance2=8),
    "sk_curva_fusion": curva_fusion, "sk_desfase": desfase, "sk_soltar_desfase": soltar_desfase,
    "sk_recortar": recortar, "sk_alargar": alargar, "sk_partir": partir, "sk_escala": escala,
    "sk_mover": mover, "sk_mover_copiar": copiar, "parametros": cambiar_parametros,
}


@pytest.mark.parametrize("clave", list(CASOS))
def test_comando_da_la_geometria_pedida_y_sobrevive_a_guardar(clave):
    s = api.Sesion()
    _ok(api.llamar(s, "create_sketch", {"name": "B"}))
    CASOS[clave](s)
    assert L(s, "get_sketch")["status"] != "over_constrained"
    receta = _ok(api.llamar(s, "get_recipe", {}))
    otra = api.Sesion()
    _ok(api.llamar(otra, "apply_recipe", {"recipe": receta}))
    assert _ents(otra) == _ents(s)


# ---------------------------------------------------------------- hallazgos de la fase 1 (se arreglan de a uno)
def _rect_con_esquina(s, comando):
    """Rectángulo de 40 × 20 con un chaflán de 2 o un empalme de 3 en una esquina; devuelve su área."""
    lados = _rect(s, 1, 1, 41, 21)
    if comando == "chaflan":
        L(s, "sketch_chamfer", line1=lados[0], line2=lados[1], distance=2)
        return 40 * 20 - 2 * 2 / 2
    L(s, "sketch_fillet", entity1=lados[0], entity2=lados[1], radius=3)
    return 40 * 20 - 9 * (1 - math.pi / 4)


@pytest.mark.parametrize("comando", ["chaflan", "empalme"])
@pytest.mark.parametrize(("args", "factor", "caja"), [
    ({"scale": 2, "center_x": 1, "center_y": 1}, 4, {"min": [1, 1], "max": [81, 41]}),
    ({"dx": 100}, 1, {"min": [101, 1], "max": [141, 21]}),
], ids=["escalar", "mover"])
def test_b232_escalar_o_mover_un_perfil_con_chaflan_no_lo_deforma(args, factor, caja, comando):
    s = api.Sesion()
    _ok(api.llamar(s, "create_sketch", {"name": "B"}))
    area = _rect_con_esquina(s, comando)
    L(s, "transform_sketch", **args)
    (p,) = L(s, "get_sketch")["profiles"]
    assert p["area"] == _ap(area * factor, abs=1e-3)
    assert p["bounding_box"] == {"min": _ap(caja["min"]), "max": _ap(caja["max"])}


def test_b236_copiar_un_perfil_con_chaflan_lleva_sus_cotas():
    s = api.Sesion()
    _ok(api.llamar(s, "create_sketch", {"name": "B"}))
    area = _rect_con_esquina(s, "chaflan")
    antes = {k["id"] for k in L(s, "get_sketch")["dimensions"]}
    L(s, "transform_sketch", dx=100, copy=True)
    nuevas = [k for k in L(s, "get_sketch")["dimensions"] if k["id"] not in antes]
    assert len(nuevas) == len(antes) == 2
    L(s, "edit_dimension", dimension=nuevas[0]["id"], value=4)
    valores = {k["id"]: k["value"] for k in L(s, "get_sketch")["dimensions"]}
    assert [valores[k["id"]] for k in nuevas] == [4, 4]         # la gemela sigue a su par copiado...
    assert [valores[k] for k in sorted(antes)] == [2, 2]         # ...y no al original
    assert _ap(area) in _areas(s)                                # el original no se movió


def test_b236_pegar_en_otro_boceto_un_perfil_con_chaflan_lleva_sus_cotas():
    s = api.Sesion()
    _ok(api.llamar(s, "create_sketch", {"name": "B"}))
    _rect_con_esquina(s, "chaflan")
    lineas = [e["id"] for e in _de(s, "line")]
    _ok(api.llamar(s, "create_sketch", {"name": "C"}))
    _ok(api.llamar(s, "copy_sketch_entities", {"sketch": "C", "entities": lineas, "source_sketch": "B", "dx": 100}))
    pegadas = _ok(api.llamar(s, "get_sketch", {"sketch": "C"}))["dimensions"]
    assert len(pegadas) == 2
    _ok(api.llamar(s, "edit_dimension", {"sketch": "C", "dimension": pegadas[0]["id"], "value": 4}))
    assert [k["value"] for k in _ok(api.llamar(s, "get_sketch", {"sketch": "C"}))["dimensions"]] == [4, 4]
    assert [k["value"] for k in L(s, "get_sketch")["dimensions"]] == [2, 2]


def test_b233_recortar_no_deja_restricciones_en_un_punto_suelto():
    s = api.Sesion()
    _ok(api.llamar(s, "create_sketch", {"name": "B"}))
    r = L(s, "draw_line", start_x=0, start_y=0, end_x=20, end_y=0)
    linea_id, extremo = r["entities"][0]["id"], r["points"][1]
    L(s, "draw_line", start_x=10, start_y=-10, end_x=10, end_y=10)
    L(s, "add_constraint", type="fix", entities=[extremo])
    L(s, "trim_sketch_curve", entity=linea_id, x=15, y=0)
    g = L(s, "get_sketch")
    usados = {p for e in g["entities"] for p in e["points"]}
    assert all(set(c["entities"]) <= usados | {e["id"] for e in g["entities"]} for c in g["constraints"])


@pytest.mark.parametrize("herramienta", ["extend_sketch_curve", "trim_sketch_curve"])
def test_b237_alargar_un_extremo_fijo_falla_sin_tocar_nada(herramienta):
    s = api.Sesion()
    _ok(api.llamar(s, "create_sketch", {"name": "B"}))
    r = L(s, "draw_line", start_x=0, start_y=0, end_x=5, end_y=0)
    linea, fijo = r["entities"][0]["id"], r["points"][1]
    L(s, "draw_line", start_x=10, start_y=-5, end_x=10, end_y=5)
    L(s, "draw_line", start_x=-10, start_y=-5, end_x=-10, end_y=5)
    L(s, "add_constraint", type="fix", entities=[fijo])

    def alargar(x):
        args = ({"curve": linea, "point": [x, 0]} if herramienta == "extend_sketch_curve"
                else {"entity": linea, "x": x, "y": 0, "mode": "extend"})
        return api.llamar(s, herramienta, {"sketch": "B", **args})
    antes = L(s, "get_sketch")
    r = alargar(4.5)
    assert not r["ok"] and "fijo" in r["mensaje"].lower()
    assert L(s, "get_sketch") == antes
    _ok(alargar(0.5))                                   # el extremo libre sí se alarga
    (ln,) = [e for e in _ents(s) if e["id"] == linea]
    assert sorted([ln["start"][0], ln["end"][0]]) == [_ap(-10), _ap(5)]


def test_b237_alargar_no_deja_una_cota_en_un_punto_suelto():
    s = api.Sesion()
    _ok(api.llamar(s, "create_sketch", {"name": "B"}))
    r = L(s, "draw_line", start_x=1, start_y=0, end_x=5, end_y=0)
    L(s, "draw_line", start_x=10, start_y=-5, end_x=10, end_y=5)
    L(s, "add_dimension", type="distance", entities=r["points"], value=4)
    L(s, "extend_sketch_curve", curve=r["entities"][0]["id"], point=[4.5, 0])
    g = L(s, "get_sketch")
    usados = {p for e in g["entities"] for p in e["points"]} | {e["id"] for e in g["entities"]}
    assert all(set(k["entities"]) <= usados for k in g["dimensions"] + g["constraints"])


def test_b234_el_nucleo_pone_tope_a_las_vueltas_de_la_espiral():
    from omnicad.restricciones.boceto import ErrorBoceto, puntos_espiral
    with pytest.raises(ErrorBoceto):
        puntos_espiral((0, 0), (5, 0), 5000, 1)


def test_b235_el_angulo_del_chaflan_conserva_su_expresion():
    s = api.Sesion()
    _ok(api.llamar(s, "create_sketch", {"name": "B"}))
    lados = _rect(s, 1, 1, 41, 21)
    L(s, "create_parameter", name="ang", expression="30 deg")
    L(s, "sketch_chamfer", line1=lados[0], line2=lados[1], distance=5, angle="ang")
    (angulo,) = [d for d in L(s, "get_sketch")["dimensions"] if d["type"] == "angle"]
    assert angulo["expression"] == "ang"


def test_b233_el_empalme_no_deja_restricciones_en_un_punto_suelto():
    """Gemelo de B-233: el empalme recorta el tramo de más allá de la esquina, y su «fijo» se va con él."""
    s = api.Sesion()
    _ok(api.llamar(s, "create_sketch", {"name": "B"}))
    r = L(s, "draw_line", start_x=0, start_y=0, end_x=20, end_y=0)
    a, extremo = r["entities"][0]["id"], r["points"][1]
    b = L(s, "draw_line", start_x=10, start_y=-10, end_x=10, end_y=10)["entities"][0]["id"]
    L(s, "add_constraint", type="fix", entities=[extremo])
    L(s, "sketch_fillet", entity1=a, entity2=b, radius=2, point1=[3, 0], point2=[10, 8])
    g = L(s, "get_sketch")
    assert extremo not in {p["id"] for p in g["points"]}
    assert not [c for c in g["constraints"] if extremo in c["entities"]]


def test_p69_trim_extend_y_break_validan_como_las_otras_herramientas():
    """P-69: trim_sketch_curve en extend y break tiene que validar como extend_sketch_curve y split_sketch_curve:
    en break el punto cae sobre la curva (tolerancia 1e-7) y la edición no deja el boceto en conflicto."""
    def partir(herramienta, punto):
        s = api.Sesion()
        _ok(api.llamar(s, "create_sketch", {"name": "B"}))
        L(s, "draw_line", start_x=0, start_y=0, end_x=20, end_y=0)
        a = _de(s, "line")[0]["id"]
        L(s, "draw_line", start_x=8, start_y=-10, end_x=8, end_y=10)
        args = ({"entity": a, "x": punto[0], "y": punto[1], "mode": "break"} if herramienta == "trim_sketch_curve"
                else {"curve": a, "point": list(punto)})
        return api.llamar(s, herramienta, {"sketch": "B", **args}), s

    def alargar(herramienta):
        s = api.Sesion()
        _ok(api.llamar(s, "create_sketch", {"name": "B"}))
        L(s, "draw_line", start_x=0, start_y=0, end_x=5, end_y=0)
        a = _de(s, "line")[0]["id"]
        L(s, "draw_line", start_x=10, start_y=-10, end_x=10, end_y=10)
        args = ({"entity": a, "x": 5, "y": 0, "mode": "extend"} if herramienta == "trim_sketch_curve"
                else {"curve": a, "point": [5, 0]})
        return api.llamar(s, herramienta, {"sketch": "B", **args}), s

    # un punto lejos de la curva: los dos caminos la rechazan igual
    trim, _ = partir("trim_sketch_curve", (50, 50))
    split, _ = partir("split_sketch_curve", (50, 50))
    assert not trim["ok"] and trim["error_kind"] == split["error_kind"] == "INVALID_GEOMETRY"
    assert trim["mensaje"] == split["mensaje"]
    # un punto sobre la curva: los dos caminos la parten en el mismo lugar y devuelven las piezas
    r_trim, s_trim = partir("trim_sketch_curve", (4, 0))
    r_split, s_split = partir("split_sketch_curve", (4, 0))
    assert r_trim["ok"] and r_split["ok"]
    assert r_trim["result"]["mode"] == "break" and r_trim["result"]["pieces"] == r_split["result"]["pieces"]
    assert _ents(s_trim) == _ents(s_split)
    # alargar que sí llega: los dos caminos dejan el mismo boceto
    r_trim, s_trim = alargar("trim_sketch_curve")
    r_ext, s_ext = alargar("extend_sketch_curve")
    assert r_trim["ok"] and r_ext["ok"]
    assert r_trim["result"]["mode"] == "extend"
    assert _ents(s_trim) == _ents(s_ext)


@pytest.mark.parametrize("herramienta", ["trim_sketch_curve", "sketch_fillet"])
def test_p68_modificar_informa_lo_borrado(herramienta):
    s = api.Sesion()
    _ok(api.llamar(s, "create_sketch", {"name": "B"}))
    r = L(s, "draw_line", start_x=1, start_y=0, end_x=21, end_y=0)
    assert not {"entities_deleted", "constraints_deleted", "dimensions_deleted"} & r.keys()
    linea_id, extremo = r["entities"][0]["id"], r["points"][1]
    otra = _ids(L(s, "draw_line", start_x=11, start_y=-10, end_x=11, end_y=10))[0]
    L(s, "add_constraint", type="fix", entities=[extremo])
    L(s, "add_dimension", type="distance", entities=r["points"], value=20)
    antes = L(s, "get_sketch")
    if herramienta == "trim_sketch_curve":
        r = L(s, herramienta, entity=linea_id, x=16, y=0)
    else:
        r = L(s, herramienta, entity1=linea_id, entity2=otra, radius=2, point1=[3, 0], point2=[11, 8])
    despues = L(s, "get_sketch")
    for clave in ("constraints", "dimensions"):
        borradas = sorted({e["id"] for e in antes[clave]} - {e["id"] for e in despues[clave]})
        assert borradas, (clave, antes, despues)
        assert r[f"{clave}_deleted"] == borradas
    assert "entities_deleted" not in r


def test_p68_modificar_revierte_si_deja_el_boceto_en_conflicto():
    s = api.Sesion()
    _ok(api.llamar(s, "create_sketch", {"name": "B"}))
    lados = [_ids(L(s, "draw_line", start_x=x1, start_y=y1, end_x=x2, end_y=y2))[0]
             for x1, y1, x2, y2 in ((1, 1, 4, 1), (4, 1, 4, 5), (4, 5, 1, 1))]
    for lado, largo in zip(lados, (3, 4, 5), strict=True):
        cota = L(s, "add_dimension", type="distance", entities=[lado], value=largo)
        assert not cota["dimension"]["reference"]
    antes = L(s, "get_sketch")
    assert antes["status"] != "over_constrained"
    receta = _ok(api.llamar(s, "get_recipe", {}))
    r = api.llamar(s, "transform_sketch", {"sketch": "B", "entities": [lados[0]], "scale": 4,
                                           "center_x": 1, "center_y": 1})
    assert not r["ok"], r
    assert r["error_kind"] == "SKETCH_OVERCONSTRAINED", r
    assert L(s, "get_sketch") == antes
    assert _ok(api.llamar(s, "get_recipe", {})) == receta


@pytest.mark.parametrize("lados", [3, 6, 64])
@pytest.mark.parametrize("circunscrito", [False, True])
@pytest.mark.parametrize("construccion", [False, True])
def test_p70_poligono_ventana_y_api_dan_la_misma_geometria(lados, circunscrito, construccion):
    from types import SimpleNamespace

    from omnicad.restricciones.boceto import Boceto, ErrorBoceto, agregar_poligono
    from omnicad.api import herramientas_boceto as herramientas
    from omnicad.ui import editor_boceto as editor

    assert herramientas.agregar_poligono is editor.agregar_poligono is agregar_poligono
    centro, radio, giro = (2, -3), 10, math.radians(30)
    tipo = "circunscrito" if circunscrito else "inscrito"
    cursor = giro + math.pi / lados if circunscrito else giro
    vertice = (centro[0] + radio * math.cos(cursor), centro[1] + radio * math.sin(cursor))
    ventana, por_api, nucleo = Boceto(), Boceto(), Boceto()
    lienzo = SimpleNamespace(b=ventana, construccion=construccion)
    ls, cid = editor.Lienzo._poligono(lienzo, centro, vertice, lados, tipo)
    alias = herramientas._poligono(por_api, lados, radio, *centro, math.degrees(giro), circunscrito, construccion)
    assert agregar_poligono(nucleo, centro, radio, lados, giro, circunscrito, construccion) == (ls, cid)
    assert alias["circle"] == cid and alias["center"] == ventana.curvas[cid].centro
    for k, lid in enumerate(ls, 1):
        assert alias[f"side{k}"] == lid and alias[f"v{k}"] == ventana.curvas[lid].p1
    radio_vertices = radio / math.cos(math.pi / lados) if circunscrito else radio
    assert ventana.coords(alias["v1"]) == pytest.approx((centro[0] + radio_vertices * math.cos(giro),
                                                        centro[1] + radio_vertices * math.sin(giro)))
    r_previa, esquinas = editor._vertices_poligono(centro, vertice, lados, tipo)
    assert r_previa == pytest.approx(radio)
    for lid, esquina in zip(ls, esquinas, strict=True):
        assert ventana.coords(ventana.curvas[lid].p1) == pytest.approx(esquina)
    for b in (por_api, nucleo):
        for k in b.curvas:
            assert b.curvas[k].a_dict() == pytest.approx(ventana.curvas[k].a_dict())
        assert b.a_dict()["restricciones"] == ventana.a_dict()["restricciones"]
        assert len(b.restricciones) == 2 * lados - 1 + circunscrito
        for pid in b.puntos:
            assert b.coords(pid) == pytest.approx(ventana.coords(pid), abs=1e-12)
        assert b.curvas[cid].radio == pytest.approx(radio)
    # El centro enganchado de la ventana sigue siendo el mismo punto.
    enganchado = Boceto()
    pc = enganchado.agregar_punto(centro[0] + 1e-10, centro[1])
    _, guia = editor.Lienzo._poligono(SimpleNamespace(b=enganchado, construccion=construccion),
                                     centro, vertice, lados, tipo, pc)
    assert enganchado.curvas[guia].centro == pc
    for original, nuevo in zip(ls, list(enganchado.curvas)[1:], strict=True):
        assert enganchado.coords(enganchado.curvas[nuevo].p1) == ventana.coords(ventana.curvas[original].p1)
    for n in (2, 65):
        antes = ventana.a_dict()
        with pytest.raises(ErrorBoceto) as del_nucleo:
            agregar_poligono(ventana, centro, radio, n, giro, circunscrito)
        with pytest.raises(ErrorBoceto, match=str(del_nucleo.value)):
            editor.Lienzo._poligono(lienzo, centro, vertice, n, tipo)
        with pytest.raises(ErrorBoceto, match=str(del_nucleo.value)):
            herramientas._poligono(ventana, n, radio, *centro, 30, circunscrito)
        with pytest.raises(ErrorBoceto, match=str(del_nucleo.value)):
            editor.Lienzo._evaluar_campo(lienzo, "lados", str(n))
        assert ventana.a_dict() == antes

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
    r = L(s, "draw_line", start_x=1, start_y=0, end_x=5, end_y=0)  # fuera del origen: ahí quedaría anclado (P-94)
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


@pytest.mark.parametrize(("herramienta", "opciones", "claves"), [
    ("sketch_fillet", {"radius": 5}, ("entity1", "entity2")),
    ("sketch_chamfer", {"distance": 5}, ("line1", "line2")),
    ("sketch_chamfer", {"distance": 5, "distance2": 3}, ("line1", "line2")),
    ("sketch_chamfer", {"distance": 5, "angle": 30}, ("line1", "line2")),
])
def test_h107_empalme_y_chaflan_por_vertice(herramienta, opciones, claves):
    sesiones = [api.Sesion(), api.Sesion()]
    for s in sesiones:
        _ok(api.llamar(s, "create_sketch", {"name": "B"}))
        lados = _rect(s, 1, 1, 61, 41)
    vertice = next(p["id"] for p in L(sesiones[0], "get_sketch")["points"] if (p["x"], p["y"]) == (61, 1))
    por_vertice, por_curvas = sesiones
    L(por_vertice, herramienta, vertex=vertice, **opciones)
    L(por_curvas, herramienta, **dict(zip(claves, lados[:2], strict=True)),
      point1=[60, 1], point2=[61, 2], **opciones)
    assert por_vertice.doc.operaciones[0].boceto.a_dict() == por_curvas.doc.operaciones[0].boceto.a_dict()
    assert _areas(por_vertice) == _areas(por_curvas)
    # Cada edición es un solo paso y las selecciones inválidas no cambian la receta.
    _ok(api.llamar(por_vertice, "undo", {}))
    antes = _ok(api.llamar(por_vertice, "get_recipe", {}))
    for seleccion in ({}, {claves[0]: lados[0]}, {claves[1]: lados[1]},
                      {"vertex": vertice, claves[0]: lados[0]},
                      {"vertex": vertice, **dict(zip(claves, lados[:2], strict=True))}):
        r = api.llamar(por_vertice, herramienta, {"sketch": "B", **opciones, **seleccion})
        assert not r["ok"] and r["error_kind"] == "INVALID_ARGUMENTS", r
        assert _ok(api.llamar(por_vertice, "get_recipe", {})) == antes
    suelto = L(por_vertice, "draw_point", x=100, y=100)["points"][0]
    L(por_vertice, "draw_line", start_x=61, start_y=1, end_x=80, end_y=-10)
    for pid in (suelto, vertice):
        antes = _ok(api.llamar(por_vertice, "get_recipe", {}))
        r = api.llamar(por_vertice, herramienta, {"sketch": "B", "vertex": pid, **opciones})
        assert not r["ok"] and r["error_kind"] == "INVALID_GEOMETRY", r
        assert "vértice" in r["mensaje"] and "exactamente dos" in r["mensaje"], r
        assert _ok(api.llamar(por_vertice, "get_recipe", {})) == antes


@pytest.mark.parametrize(("herramienta", "con_arco"), [("empalme", False), ("chaflan", False),
    ("chaflan_dos_dist", False), ("chaflan_dist_angulo", False), ("empalme", True)])
def test_h107_ventana_un_clic_en_el_vertice_crea_la_esquina(herramienta, con_arco, monkeypatch):
    from PySide6.QtCore import QEvent, Qt
    from PySide6.QtGui import QMouseEvent, QPainter, QPixmap
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication

    from omnicad.restricciones import Boceto
    from omnicad.timeline.parametros import TablaParametros
    from omnicad.ui.editor_boceto import Lienzo

    app = QApplication.instance() or QApplication([])
    lz = Lienzo(Boceto(), TablaParametros().evaluar)
    lz.resize(800, 600)
    lz.setAttribute(Qt.WA_ShowWithoutActivating)
    lz.setWindowFlag(Qt.WindowDoesNotAcceptFocus)
    lz.setWindowOpacity(0)
    lz.ajustar_grilla = False
    if con_arco:
        arco = lz.b.agregar_arco_centro((41, 1), (61, 1), (21, 1))
        pid = lz.b.curvas[arco].inicio
        lados = [arco, lz.b.agregar_linea(pid, (1, 11))]
    else:
        lados = lz.b.agregar_rectangulo((1, 1), (61, 41))
        pid = lz.b.curvas[lados[0]].p2
    antes = lz.b.a_dict()
    lz.set_herramienta(herramienta)
    lz.encuadrar()
    lz.show()
    app.processEvents()
    pos = lz.a_px(61, 1)
    try:
        QApplication.sendEvent(lz, QMouseEvent(QEvent.MouseMove, pos, lz.mapToGlobal(pos), Qt.NoButton,
                                               Qt.NoButton, Qt.NoModifier))
        # La previa se dibuja ya al pasar sobre el vértice, antes de elegirlo.
        imagen = QPixmap(lz.size())
        with monkeypatch.context() as m:
            polis = []
            m.setattr(lz, "_dibujar_polilinea", lambda p, poli: polis.append(poli))
            pintor = QPainter(imagen)
            try:
                lz._dibujar_previa(pintor)
                assert polis and lz.entrada is None and lz.b.a_dict() == antes
                polis.clear()
                lejos = lz.a_px(100, 100)
                QApplication.sendEvent(lz, QMouseEvent(QEvent.MouseMove, lejos, lz.mapToGlobal(lejos), Qt.NoButton,
                                                       Qt.NoButton, Qt.NoModifier))
                lz._dibujar_previa(pintor)
                assert not polis
            finally:
                pintor.end()
        for tipo, boton, botones in ((QEvent.MouseButtonPress, Qt.LeftButton, Qt.LeftButton),
                                     (QEvent.MouseButtonRelease, Qt.LeftButton, Qt.NoButton)):
            QApplication.sendEvent(lz, QMouseEvent(tipo, pos, lz.mapToGlobal(pos), boton, botones, Qt.NoModifier))
        assert lz.entrada is not None, "Un clic en el vértice debe resolver las dos curvas y abrir los valores."
        assert lz.b.a_dict() == antes                 # la previa no toca el boceto
        assert lz._asas.previa(lz._asas.valores())
        campo = lz.entrada.campos[0]
        QTest.keyClick(campo, Qt.Key_A, Qt.ControlModifier)
        QTest.keyClicks(campo, "5 mm")
        if len(lz.entrada.campos) == 2:
            QTest.keyClick(campo, Qt.Key_Tab)
            segundo = lz.entrada.campos[1]
            QTest.keyClick(segundo, Qt.Key_A, Qt.ControlModifier)
            QTest.keyClicks(segundo, "3 mm" if herramienta == "chaflan_dos_dist" else "30 deg")
        previa = lz._asas.previa(lz._asas.valores())
        assert previa and lz.b.a_dict() == antes
        if con_arco:
            assert min(x for poli in previa for x, y in poli) > 41       # el cruce del vértice, no el de la izquierda
        QTest.keyClick(lz.entrada.campos[-1], Qt.Key_Return)
        assert lz.entrada is None and len(lz.b.curvas) == len(lados) + 1
        nuevo = next(c for k, c in lz.b.curvas.items() if k not in lados)
        assert nuevo.tipo == ("arco" if herramienta == "empalme" else "linea")
        if herramienta == "empalme":
            assert lz.b.radio(nuevo.id) == pytest.approx(5)
        else:
            assert math.dist((61, 1), lz.b.coords(nuevo.p1)) == pytest.approx(5)
        lz.deshacer()
        assert lz.b.a_dict() == antes
        # Un vértice ambiguo no elige dos curvas al azar ni deja una elección parcial.
        lz.b.agregar_linea(pid, (80, -10))
        ambiguo = lz.b.a_dict()
        mensajes = []
        lz.mensaje.connect(mensajes.append)
        QApplication.sendEvent(lz, QMouseEvent(QEvent.MouseButtonPress, pos, lz.mapToGlobal(pos), Qt.LeftButton,
                                               Qt.LeftButton, Qt.NoModifier))
        assert lz.entrada is None and not lz.picks and lz.b.a_dict() == ambiguo
        assert "exactamente dos" in mensajes[-1]
        # Una punta libre no es esquina: el clic cerca de ella elige la curva, como antes.
        suelta = lz.b.agregar_linea((1, 60), (30, 60))
        punta = lz.a_px(30, 60)
        QApplication.sendEvent(lz, QMouseEvent(QEvent.MouseButtonPress, punta, lz.mapToGlobal(punta), Qt.LeftButton,
                                               Qt.LeftButton, Qt.NoModifier))
        assert lz.picks == [suelta], lz.picks
    finally:
        lz._cerrar_entrada()
        lz.close()
        lz.deleteLater()
        app.processEvents()


@pytest.mark.parametrize("tipo", ["arco", "spline"])
def test_h107_vertice_valida_el_tipo_de_las_dos_curvas(tipo):
    s = api.Sesion()
    _ok(api.llamar(s, "create_sketch", {"name": "B"}))
    if tipo == "arco":
        L(s, "draw_arc", start_x=20, start_y=0, center_x=0, center_y=0, sweep_angle=180)
    else:
        L(s, "draw_spline", points=[[20, 0], [10, 10], [0, 20]])
    # Las draw_* de curvas distintas no comparten puntos por sus coordenadas: modelamos una unión real.
    op = s.doc.operaciones[0].copia()
    curva = next(iter(op.boceto.curvas.values()))
    pid = curva.extremos()[0]
    op.boceto.agregar_linea(pid, (-40, 10))       # vuelve a cruzar el arco: el vértice elige la esquina, no ese cruce
    s.doc.reemplazar(op.id, op)
    antes = _ok(api.llamar(s, "get_recipe", {}))
    r = api.llamar(s, "sketch_chamfer", {"vertex": pid, "distance": 3})
    assert not r["ok"] and r["error_kind"] == "INVALID_GEOMETRY", r
    assert "dos líneas" in r["mensaje"]
    assert _ok(api.llamar(s, "get_recipe", {})) == antes
    r = api.llamar(s, "sketch_fillet", {"vertex": pid, "radius": 3})
    if tipo == "arco":
        assert r["ok"], r
        assert len(_de(s, "arc")) == 2
        assert _de(s, "arc")[-1]["radius"] == pytest.approx(3)
        assert _de(s, "arc")[-1]["center"][0] > 15
    else:
        assert not r["ok"] and r["error_kind"] == "INVALID_GEOMETRY", r
        assert "línea o arco" in r["mensaje"]
        assert _ok(api.llamar(s, "get_recipe", {})) == antes


@pytest.mark.parametrize("cantidad", [2, 3, 4, 5, 6, 7])
@pytest.mark.parametrize("herramienta", ["draw_spline", "sketch_from_spec"])
def test_p67_spline_de_control_guarda_el_grado_efectivo_y_sobrevive_a_la_receta(cantidad, herramienta):
    from omnicad.restricciones.boceto import dominio, evaluar_primitiva

    s = api.Sesion()
    puntos = [[0, 0], [5, 8], [12, -3], [18, 6], [25, 0], [30, 4], [35, -2]][:cantidad]
    args = {"points": puntos, "spline_type": "control_points"}
    if herramienta == "draw_spline":
        _ok(api.llamar(s, "create_sketch", {"name": "B"}))
        L(s, herramienta, **args)
    else:
        _ok(api.llamar(s, herramienta, {"name": "B", "entities": [{"type": "spline", **args}]}))
    (e,) = _de(s, "spline")
    grado = min(5, cantidad - 1)
    assert e["degree"] == grado
    b = s.doc.operaciones[0].boceto
    assert b.curvas[e["id"]].grado == grado
    p = b.primitivas(e["id"])[0]
    inicio, fin, _ = dominio(p)
    assert evaluar_primitiva(p, inicio)[0] == pytest.approx(puntos[0])
    assert evaluar_primitiva(p, fin)[0] == pytest.approx(puntos[-1])
    receta = _ok(api.llamar(s, "get_recipe", {}))
    otra = api.Sesion()
    _ok(api.llamar(otra, "apply_recipe", {"recipe": receta}))
    assert _ents(otra) == _ents(s)
    assert otra.doc.operaciones[0].boceto.curvas[e["id"]].grado == grado


@pytest.mark.parametrize("cantidad", [2, 3, 5])
@pytest.mark.parametrize("grado", [3, 5])
def test_p67_cambiar_grado_desde_un_grado_reducido(cantidad, grado):
    from omnicad.restricciones.boceto import dominio, evaluar_primitiva

    s = api.Sesion()
    _ok(api.llamar(s, "create_sketch", {"name": "B"}))
    L(s, "draw_spline", points=[[0, 0], [5, 8], [12, -3], [18, 6], [25, 0]][:cantidad],
      spline_type="control_points")
    (e,) = _de(s, "spline")
    assert e["degree"] == cantidad - 1
    p = s.doc.operaciones[0].boceto.primitivas(e["id"])[0]
    inicio, fin, _ = dominio(p)
    ts = [inicio + (fin - inicio) * i / 20 for i in range(21)]
    antes = [evaluar_primitiva(p, t)[0] for t in ts]
    L(s, "edit_sketch_spline", entity=e["id"], action="set_degree", degree=grado)
    assert _de(s, "spline")[0]["degree"] == grado
    nueva = s.doc.operaciones[0].boceto.primitivas(e["id"])[0]
    despues = [evaluar_primitiva(nueva, t)[0] for t in ts]
    assert despues[0] == pytest.approx(antes[0])
    assert despues[-1] == pytest.approx(antes[-1])
    if grado > e["degree"]:
        assert max(math.dist(a, b) for a, b in zip(antes, despues, strict=True)) < 1e-6


def test_p67_editor_arranca_con_grado_cinco_sin_mostrar_ventana():
    from PySide6.QtWidgets import QApplication

    from omnicad.restricciones import Boceto
    from omnicad.timeline.parametros import TablaParametros
    from omnicad.ui.editor_boceto import Lienzo

    app = QApplication.instance() or QApplication([])
    lienzo = Lienzo(Boceto(), TablaParametros().evaluar)
    try:
        assert not lienzo.isVisible()
        assert lienzo.opciones["grado_spline"] == 5
    finally:
        lienzo.close()
        lienzo.deleteLater()
        app.processEvents()


@pytest.mark.parametrize("barrido", [90, -90, 270, -270])
def test_p72_arco_tangente_con_radio_y_barrido_se_guarda(barrido, tmp_path):
    from omnicad.restricciones.boceto import dominio

    s = api.Sesion()
    _ok(api.llamar(s, "create_sketch", {"name": "B"}))
    linea = _ids(L(s, "draw_line", start_x=0, start_y=0, end_x=20, end_y=0))[0]
    L(s, "draw_arc", start_x=20, start_y=0, tangent_to=linea, radius=10, sweep_angle=barrido)
    (arco,) = _de(s, "arc")
    lado = 1 if barrido > 0 else -1
    assert arco["radius"] == _ap(10)
    assert arco["center"] == _ap([20, 10 * lado])
    extremo = [30 if abs(barrido) == 90 else 10, 10 * lado]
    b = s.doc.operaciones[0].boceto
    curva = b.curvas[arco["id"]]
    inicio, fin = (curva.inicio, curva.fin) if barrido > 0 else (curva.fin, curva.inicio)
    assert b.coords(fin) == pytest.approx(extremo)
    assert b.coords(inicio) == pytest.approx([20, 0])
    assert inicio == b.curvas[linea].p2
    t0, t1, _ = dominio(b.primitivas(arco["id"])[0])
    assert math.degrees(t1 - t0) == pytest.approx(abs(barrido))
    assert any(r.tipo == "tangente" and set(r.entidades) == {linea, arco["id"]}
               for r in b.restricciones.values())
    assert _dist_recta(arco["center"], _de(s, "line")[0]) == _ap(10)
    assert s.doc.estado_final.bocetos[s.doc.operaciones[0].id].solver.ok
    ruta = str(tmp_path / "arco_tangente.omnicad")
    _ok(api.llamar(s, "save_document", {"path": ruta}))
    otra = api.Sesion()
    _ok(api.llamar(otra, "open_document", {"path": ruta}))
    assert _ents(otra) == _ents(s)
    assert otra.doc.operaciones[0].boceto.a_dict() == b.a_dict()


@pytest.mark.parametrize("argumentos", [
    {"radius": 10, "sweep_angle": 90, "end_x": 30},
    {"radius": 10, "sweep_angle": 90, "end_y": 10},
    {"radius": 10, "sweep_angle": 90, "end_x": 30, "end_y": 10},
    {}, {"end_x": 30}, {"radius": 10},
    {"radius": 10, "sweep_angle": 90, "center_x": 20},
    {"radius": 10, "sweep_angle": 90, "mid_y": 5},
    {"end_x": 30, "end_y": 10, "sweep_angle": 90},
    {"radius": 0, "sweep_angle": 90}, {"radius": -10, "sweep_angle": 90},
    {"radius": 10, "sweep_angle": 0}, {"radius": 10, "sweep_angle": 360},
])
def test_p72_arco_tangente_rechaza_entradas_sin_mutar(argumentos):
    s = api.Sesion()
    _ok(api.llamar(s, "create_sketch", {"name": "B"}))
    linea = _ids(L(s, "draw_line", start_x=0, start_y=0, end_x=20, end_y=0))[0]
    antes = _ok(api.llamar(s, "get_recipe", {}))
    resultado = api.llamar(s, "draw_arc", {"sketch": "B", "start_x": 20, "start_y": 0,
                                          "tangent_to": linea, **argumentos})
    assert not resultado["ok"], resultado
    assert resultado["error_kind"] == ("INVALID_GEOMETRY" if argumentos.get("radius", 1) <= 0
                                        or argumentos.get("sweep_angle", 1) in (0, 360) else "INVALID_ARGUMENTS")
    assert _ok(api.llamar(s, "get_recipe", {})) == antes


@pytest.mark.parametrize("barrido", [90, -90, 270, -270])
def test_p72_ventana_y_api_crean_el_mismo_arco_con_radio(barrido):
    from PySide6.QtWidgets import QApplication

    from omnicad.timeline.parametros import TablaParametros
    from omnicad.ui.editor_boceto import Lienzo

    s = api.Sesion()
    _ok(api.llamar(s, "create_sketch", {"name": "B"}))
    linea = _ids(L(s, "draw_line", start_x=0, start_y=0, end_x=20, end_y=0))[0]
    app = QApplication.instance() or QApplication([])
    lienzo = Lienzo(s.doc.operaciones[0].boceto.copia(), TablaParametros().evaluar)
    try:
        pid = lienzo.b.curvas[linea].p2
        lienzo.set_herramienta("arco_tangente")
        lienzo.clics = [(pid, (20, 0))]
        lienzo._bloqueos = {"radio": ("10 mm", 10)}
        cursor = (30 if abs(barrido) == 90 else 10, 10 if barrido > 0 else -10)
        fin = lienzo._aplicar_bloqueos(cursor)
        aid, destino = lienzo._crear_arco_tangente(pid, linea, (None, fin))
        L(s, "draw_arc", start_x=20, start_y=0, tangent_to=linea, radius=10, sweep_angle=barrido)
        b = s.doc.operaciones[0].boceto
        actual, ventana = b.primitivas(aid)[0], lienzo.b.primitivas(aid)[0]
        assert actual[0] == ventana[0] == "arco"
        assert actual[1] == ventana[1]
        assert actual[2] == pytest.approx(ventana[2])
        assert actual[3] == pytest.approx(ventana[3])
        for angulo, esperado in zip(actual[4:], ventana[4:], strict=True):
            assert math.remainder(angulo - esperado, 2 * math.pi) == pytest.approx(0, abs=1e-9)
        assert b.coords(destino) == pytest.approx(cursor)
        assert not lienzo.isVisible()
    finally:
        lienzo.close()
        lienzo.deleteLater()
        app.processEvents()

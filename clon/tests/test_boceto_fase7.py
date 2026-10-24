"""Fase 7 del boceto: editar splines (manijas, peine, abrir/cerrar, insertar punto, grado) y texto (altura con
parámetro, 'abc' + parámetro, marco acotable, giro con pivote, fuente de un trazo, glifos faltantes)."""
import json
import math

import pytest

from omnicad import api
from omnicad.api.herramientas_boceto import op_boceto
from omnicad.restricciones.boceto import dominio, evaluar_primitiva, mas_cercano


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


def entidad(sesion, eid):
    return next(e for e in llamar(sesion, "get_sketch")["entities"] if e["id"] == eid)


def prim(sesion, eid):
    """Primitiva resuelta de la curva (como la ve el núcleo)."""
    from omnicad.api.herramientas_boceto import boceto_resuelto
    br = boceto_resuelto(sesion, op_boceto(sesion, None))
    return br.boceto.primitivas(eid)[0]


def muestras(p, n=200):
    t0, t1, _ = dominio(p)
    return [evaluar_primitiva(p, t0 + (t1 - t0) * i / n)[0] for i in range(n + 1)]


def spline(sesion, puntos, **kw):
    return llamar(sesion, "draw_spline", points=puntos, **kw)["entities"][0]["id"]


ARCO = [[10 * math.cos(0.3 * i), 10 * math.sin(0.3 * i)] for i in range(9)]


# ---------------------------------------------------------------- BOC-11: manijas
def test_boc11_manija_de_tangente_fija_el_angulo_y_sigue_pasando_por_los_puntos(s):
    sid = spline(s, [[0, 0], [10, 5], [20, 0]])
    medio = entidad(s, sid)["points"][1]
    r = llamar(s, "edit_sketch_spline", entity=sid, action="activate_handle", point=medio, angle=30, length=8)
    assert [e["type"] for e in r["entities"]] == ["line"]
    p = prim(s, sid)
    t = min((abs(math.dist(evaluar_primitiva(p, u / 1000)[0], (10, 5))), u / 1000) for u in range(1001))[1]
    c, d1 = evaluar_primitiva(p, t, 1)
    assert math.dist(c, (10, 5)) < 1e-6
    assert math.degrees(math.atan2(d1[1], d1[0])) == pytest.approx(30, abs=0.5)
    info = entidad(s, sid)
    assert info["handles"][0]["angle"] == pytest.approx(30) and info["handles"][0]["length"] == pytest.approx(8)
    for q in ([0, 0], [20, 0]):
        assert min(math.dist(q, m) for m in muestras(p)) < 1e-6


def test_boc11_curvatura_de_la_manija(s):
    sid = spline(s, [[0, 0], [10, 0], [20, 0]])
    medio = entidad(s, sid)["points"][1]
    llamar(s, "edit_sketch_spline", entity=sid, action="activate_handle", point=medio, angle=0, curvature=0.05)
    p = prim(s, sid)
    t = min((math.dist(evaluar_primitiva(p, u / 2000)[0], (10, 0)), u / 2000) for u in range(2001))[1]
    _c, d1, d2 = evaluar_primitiva(p, t, 2)
    k = (d1[0] * d2[1] - d1[1] * d2[0]) / math.hypot(*d1) ** 3
    assert k == pytest.approx(0.05, rel=0.05)


def test_boc11_borrar_la_linea_de_la_manija_la_desactiva_y_un_paso_de_deshacer(s):
    sid = spline(s, [[0, 0], [10, 5], [20, 0]])
    antes = foto(s)
    medio = entidad(s, sid)["points"][1]
    linea = llamar(s, "edit_sketch_spline", entity=sid, action="activate_handle", point=medio,
                   angle=-40)["entities"][0]["id"]
    assert entidad(s, linea)["construction"] is True
    llamar(s, "undo")
    assert foto(s) == antes
    llamar(s, "edit_sketch_spline", entity=sid, action="activate_handle", point=medio, angle=-40)
    llamar(s, "edit_sketch_spline", entity=sid, action="deactivate_handle", point=medio)
    assert entidad(s, sid).get("handles", []) == []
    assert len(llamar(s, "get_sketch")["entities"]) == 1


def test_boc11_manija_errores(s):
    control = spline(s, [[0, 0], [5, 5], [10, 0], [15, 5]], spline_type="control_points", degree=3)
    pid = entidad(s, control)["points"][1]
    assert falla(s, "edit_sketch_spline", entity=control, action="activate_handle",
                 point=pid)["error_kind"] == "INVALID_GEOMETRY"
    sid = spline(s, [[0, 10], [10, 15], [20, 10]])
    assert falla(s, "edit_sketch_spline", entity=sid, action="activate_handle", point=pid)["error_kind"] \
        == "INVALID_GEOMETRY"


# ---------------------------------------------------------------- BOC-11: peine de curvatura
def test_boc11_peine_de_curvatura_de_un_arco(s):
    sid = spline(s, ARCO)
    r = llamar(s, "get_spline_curvature", entity=sid, density=21)
    assert len(r["samples"]) == 21
    medio = r["samples"][10]
    assert medio["curvature"] == pytest.approx(0.1, rel=0.03)
    assert math.hypot(*medio["point"]) == pytest.approx(10, abs=0.05)
    assert math.hypot(*medio["tip"]) > 10            # la púa sale del lado opuesto al centro
    assert r["max_curvature"] == pytest.approx(max(abs(m["curvature"]) for m in r["samples"]))


# ---------------------------------------------------------------- BOC-11: abrir y cerrar
def test_boc11_cerrar_y_abrir_una_spline_de_ajuste(s):
    sid = spline(s, [[0, 0], [10, 0], [10, 10], [0, 10]])
    assert llamar(s, "get_sketch")["profiles"] == []
    llamar(s, "edit_sketch_spline", entity=sid, action="close")
    info = entidad(s, sid)
    assert info["closed"] is True
    assert len(llamar(s, "get_sketch")["profiles"]) == 1
    llamar(s, "edit_sketch_spline", entity=sid, action="open")
    info = entidad(s, sid)
    assert info["closed"] is False and len(info["vertices"]) == 5
    assert info["vertices"][0] == info["vertices"][-1]


# ---------------------------------------------------------------- BOC-11: insertar punto
def test_boc11_insertar_punto_de_ajuste_queda_sobre_la_curva(s):
    sid = spline(s, ARCO)
    curva = prim(s, sid)
    antes = muestras(curva)
    r = llamar(s, "edit_sketch_spline", entity=sid, action="insert_point", x=10 * math.cos(0.15),
               y=10 * math.sin(0.15))
    assert len(r["points"]) == 1
    info = entidad(s, sid)
    assert len(info["vertices"]) == 10
    nuevo = info["vertices"][1]
    assert mas_cercano(curva, nuevo)[1] < 1e-3          # get_sketch redondea
    assert max(min(math.dist(q, a) for a in antes) for q in muestras(prim(s, sid))) < 0.02


def test_boc11_insertar_punto_de_control_no_cambia_la_forma(s):
    sid = spline(s, [[0, 0], [5, 8], [12, -3], [18, 6], [25, 0]], spline_type="control_points", degree=3)
    antes = muestras(prim(s, sid))
    llamar(s, "edit_sketch_spline", entity=sid, action="insert_point", x=12, y=2)
    assert len(entidad(s, sid)["vertices"]) == 6
    despues = muestras(prim(s, sid))
    assert max(math.dist(a, b) for a, b in zip(antes, despues, strict=True)) < 1e-6


# ---------------------------------------------------------------- BOC-11: grado
def test_boc11_subir_el_grado_conserva_la_forma_y_bajarlo_conserva_los_extremos(s):
    sid = spline(s, [[0, 0], [5, 8], [12, -3], [18, 6], [25, 0]], spline_type="control_points", degree=3)
    antes = muestras(prim(s, sid))
    llamar(s, "edit_sketch_spline", entity=sid, action="set_degree", degree=5)
    info = entidad(s, sid)
    assert info["degree"] == 5 and len(info["vertices"]) > 5
    despues = muestras(prim(s, sid))
    assert max(math.dist(a, b) for a, b in zip(antes, despues, strict=True)) < 1e-4
    llamar(s, "edit_sketch_spline", entity=sid, action="set_degree", degree=3)
    info = entidad(s, sid)
    assert info["degree"] == 3
    assert info["vertices"][0] == [0, 0] and info["vertices"][-1] == [25, 0]
    assert falla(s, "edit_sketch_spline", entity=spline(s, ARCO), action="set_degree",
                 degree=5)["error_kind"] == "INVALID_GEOMETRY"


# ---------------------------------------------------------------- BOC-20: texto
def _alto_texto(sesion, tid):
    ys = [q[1] for p in prim_todas(sesion, tid) for q in ((p[2], p[3]) if p[0] == "linea" else p[2])]
    return max(ys) - min(ys)


def prim_todas(sesion, eid):
    from omnicad.api.herramientas_boceto import boceto_resuelto
    return boceto_resuelto(sesion, op_boceto(sesion, None)).boceto.primitivas(eid)


def test_boc20_altura_del_texto_con_parametro(s):
    llamar(s, "create_parameter", name="h_texto", expression="5 mm")
    tid = llamar(s, "add_text", text="H", height="h_texto")["entities"][0]["id"]
    assert entidad(s, tid)["height_expression"] == "h_texto"
    alto = _alto_texto(s, tid)
    llamar(s, "set_parameter", name="h_texto", expression="10 mm")
    assert _alto_texto(s, tid) == pytest.approx(2 * alto, rel=1e-6)
    assert entidad(s, tid)["height"] == pytest.approx(10)


def test_boc20_texto_con_comillas_y_parametro():
    from omnicad.timeline.operaciones import texto_con_valores
    assert texto_con_valores("Rev {'R-' + rev}", {"rev": 3.0}) == "Rev R-3"
    assert texto_con_valores("{'a' + 'b'}", {}) == "ab"


def test_boc20_expresion_invalida_avisa(s):
    r = api.llamar(s, "add_text", {"text": "Ancho {no_existe}"})
    assert r["ok"] and any("no_existe" in a for a in r["avisos"])


def test_boc20_marco_acotable_mueve_el_texto(s):
    r = llamar(s, "add_text", text="AB", height=5, box_width=40, frame=True, frame_height=10, align="center",
               anchor="middle")
    lineas = [e["id"] for e in r["entities"] if e["type"] == "line"]
    tid = next(e["id"] for e in r["entities"] if e["type"] == "text")
    assert len(lineas) == 4 and all(entidad(s, i)["construction"] for i in lineas)
    assert entidad(s, tid)["frame"]["width"] == pytest.approx(40)
    xs = [q[0] for p in prim_todas(s, tid) for q in ((p[2], p[3]) if p[0] == "linea" else p[2])]
    assert (min(xs) + max(xs)) / 2 == pytest.approx(20, abs=0.5)
    abajo = min(lineas, key=lambda i: entidad(s, i)["start"][1] + entidad(s, i)["end"][1])
    llamar(s, "add_dimension", sketch="B", type="distance", entities=[abajo], value=60)
    assert entidad(s, tid)["frame"]["width"] == pytest.approx(60)
    linea = entidad(s, abajo)
    xs = [q[0] for p in prim_todas(s, tid) for q in ((p[2], p[3]) if p[0] == "linea" else p[2])]
    assert (min(xs) + max(xs)) / 2 == pytest.approx((linea["start"][0] + linea["end"][0]) / 2, abs=0.5)


def test_boc20_giro_con_pivote(s):
    tid = llamar(s, "add_text", text="A", x=10, y=0)["entities"][0]["id"]
    llamar(s, "edit_text", entity=tid, angle=90, pivot=[0, 0])
    info = entidad(s, tid)
    assert info["position"] == pytest.approx([0, 10], abs=1e-9) and info["angle"] == pytest.approx(90)


# ---------------------------------------------------------------- BOC-21: fuente de un trazo
def test_boc21_fuente_de_un_trazo_en_la_lista_y_dibuja_solo_lineas(s):
    r = llamar(s, "list_fonts", query="SHX")
    assert r["families"] and all(f["single_line"] for f in r["families"])
    familia = r["families"][0]["name"]
    tid = llamar(s, "add_text", text="L1", font=familia, height=10)["entities"][0]["id"]
    prims = prim_todas(s, tid)
    assert prims and all(p[0] == "linea" for p in prims)
    assert _alto_texto(s, tid) == pytest.approx(10 * 0.7, rel=0.05)   # altura de las mayúsculas


# ---------------------------------------------------------------- BOC-28: glifos faltantes y texto largo
def test_boc28_glifo_faltante_avisa(s):
    r = api.llamar(s, "add_text", {"text": "Hola \U0001F600"})
    assert r["ok"] and any("glifo" in a for a in r["avisos"])


def test_boc28_texto_largo_en_un_circulo_en_tiempo_razonable(s):
    import time
    c = llamar(s, "draw_circle", radius=100)["entities"][0]["id"]
    t = time.perf_counter()
    r = llamar(s, "add_text", text="W" * 200, height=5, path_entity=c, fit_path=True)
    assert r["profiles"] > 1000
    assert time.perf_counter() - t < 10.0     # ~2-3 s; antes de BOC-28, el doble


def test_relink_de_perfil_giratorio_conserva_eje_y_sentido():
    s = api.Sesion()
    llamar(s, "create_cylinder", radius=5, height=30)
    llamar(s, "create_sketch", plane="XZ")
    llamar(s, "project_spun_profile", axis="Z", bodies=["Cuerpo1"], flip=True, tolerance=0.05)
    llamar(s, "manage_lost_projections", action="relink", projection=1, bodies=["Cuerpo1"])
    xs = [p["x"] for p in llamar(s, "get_sketch", sketch=None)["points"]]
    assert min(xs) == pytest.approx(-5, abs=0.06) and max(xs) <= 1e-6

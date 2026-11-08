"""Auditoría cm-3a: combinaciones 1–4 de CREAR y MODIFICAR, sin ventana."""
import math

import pytest

from omnicad import api
from tests.test_boceto_crear_modificar_matriz import _ok, _ids, _ents, _de, _areas, _rect


def _llamar(s, nombre, **argumentos):
    return _ok(api.llamar(s, nombre, argumentos))


def _boceto(s):
    informe = _llamar(s, "get_sketch", sketch="B")
    assert informe["status"] in {"fully_constrained", "under_constrained"}
    assert informe["conflicts"] == []
    return informe


def _reabrir(s):
    receta = _llamar(s, "get_recipe")
    otra = api.Sesion()
    _llamar(otra, "apply_recipe", recipe=receta)
    assert _ents(otra) == _ents(s)
    assert _boceto(otra) == _boceto(s)
    return otra


def _solido(s, volumen, minimo, maximo):
    propiedades = _llamar(s, "get_physical_properties")
    assert len(propiedades["bodies"]) == 1
    assert propiedades["total"]["volume"] == pytest.approx(volumen, abs=1e-3)
    assert propiedades["total"]["bounding_box"]["min"] == pytest.approx(minimo, abs=2e-4)
    assert propiedades["total"]["bounding_box"]["max"] == pytest.approx(maximo, abs=2e-4)
    geometria = _llamar(s, "check_geometry")
    assert geometria["all_valid"] and geometria["all_closed"]
    assert geometria["bodies"][0]["solids"] == 1
    assert geometria["bodies"][0]["errors"] == 0


def test_combinacion_1_rectangulo_empalme_desfase_recorte_extrusion():
    s = api.Sesion()
    _llamar(s, "create_sketch", name="B")
    lados = _rect(s, 1, 1, 41, 21)
    assert sorted(e["length"] for e in _de(s, "line")) == [20, 20, 40, 40]
    assert _areas(s) == pytest.approx([800])
    _boceto(s)
    _llamar(s, "sketch_fillet", sketch="B", entity1=lados[0], entity2=lados[1], radius=3)
    # Se quita un cuadrado de 3² y se repone un cuarto de círculo de radio 3.
    area = 800 - 9 * (1 - math.pi / 4)
    assert _areas(s) == pytest.approx([area], abs=2e-4)
    arco, = _de(s, "arc")
    assert arco["radius"] == pytest.approx(3, abs=2e-4)
    assert arco["center"] == pytest.approx([38, 4], abs=2e-4)
    assert sorted(e["length"] for e in _de(s, "line")) == pytest.approx([17, 20, 37, 40])
    assert len(_ents(s)) == 5
    _boceto(s)
    originales = {e["id"] for e in _ents(s)}
    _llamar(s, "offset_sketch_curves", sketch="B", entity=lados[2], distance=2)
    assert len(_ents(s)) == 10
    copias = [e for e in _ents(s) if e["id"] not in originales]
    arco_copia, = [e for e in copias if e["type"] == "arc"]
    assert arco_copia["radius"] == pytest.approx(5, abs=2e-4)
    assert arco_copia["center"] == pytest.approx([38, 4], abs=2e-4)
    assert sorted(e["length"] for e in copias if e["type"] == "line") == pytest.approx([19, 24, 39, 44])
    # Contorno exterior: caja 44×24 menos la esquina cuadrada de 5² fuera del arco.
    assert sum(_areas(s)) == pytest.approx(44 * 24 - 25 * (1 - math.pi / 4), abs=1e-3)
    _boceto(s)
    inferior, = [e for e in copias if e["type"] == "line" and abs(e["start"][1] + 1) < 2e-4
                 and abs(e["end"][1] + 1) < 2e-4]
    _llamar(s, "trim_sketch_curve", sketch="B", entity=inferior["id"], x=20, y=-1)
    assert len(_ents(s)) == 9
    assert inferior["id"] not in {e["id"] for e in _ents(s)}
    assert _areas(s) == pytest.approx([area], abs=2e-4)
    _boceto(s)
    _llamar(s, "extrude", sketch="B", profile=0, distance=5)
    # El desfase abierto no aporta perfil: V = (800 - 9 + 9π/4) × 5.
    _solido(s, area * 5, [1, 1, 0], [41, 21, 5])
    otra = _reabrir(s)
    _solido(otra, area * 5, [1, 1, 0], [41, 21, 5])


def test_combinacion_2_circulo_patron_partir_y_editar():
    s = api.Sesion()
    _llamar(s, "create_sketch", name="B")
    circulo, = _ids(_llamar(s, "draw_circle", sketch="B", center_x=30, center_y=0, radius=10))
    assert _de(s, "circle")[0]["radius"] == pytest.approx(10)
    assert _de(s, "circle")[0]["center"] == pytest.approx([30, 0])
    assert _areas(s) == pytest.approx([100 * math.pi], abs=2e-4)
    _boceto(s)
    _llamar(s, "sketch_circular_pattern", sketch="B", entities=[circulo], count=6,
            center_x=0, center_y=0)
    assert len(_ents(s)) == len(_de(s, "circle")) == 6
    for i in range(6):
        centro = [30 * math.cos(i * math.pi / 3), 30 * math.sin(i * math.pi / 3)]
        assert any(e["center"] == pytest.approx(centro, abs=2e-4) for e in _de(s, "circle"))
    assert [e["radius"] for e in _de(s, "circle")] == pytest.approx([10] * 6)
    # Seis discos disjuntos: A = 6πr² = 600π.
    assert sum(_areas(s)) == pytest.approx(600 * math.pi, abs=1e-3)
    patron, = _boceto(s)["patterns"]
    assert patron["parameters"]["count"] == 6
    copia, = [e for e in _de(s, "circle") if e["center"] == pytest.approx([-30, 0], abs=2e-4)]
    _llamar(s, "draw_line", sketch="B", start_x=-30, start_y=-15, end_x=-30, end_y=15)
    assert len(_ents(s)) == 7
    assert _de(s, "line")[0]["length"] == pytest.approx(30)
    _boceto(s)
    partes = _llamar(s, "split_sketch_curve", sketch="B", curve=copia["id"], point=[-40, 0])
    assert len(partes["pieces"]) == 2
    assert len(_ents(s)) == 8
    assert len(_de(s, "circle")) == 5
    assert len(_de(s, "arc")) == 2
    for arco in _de(s, "arc"):
        assert arco["radius"] == pytest.approx(10)
        assert arco["center"] == pytest.approx([-30, 0], abs=2e-4)
        assert math.dist(arco["start"], arco["end"]) == pytest.approx(20, abs=2e-4)
    assert sum(_areas(s)) == pytest.approx(600 * math.pi, abs=1e-3)
    _boceto(s)
    s = _reabrir(s)
    _llamar(s, "edit_sketch_pattern", sketch="B", pattern=patron["id"], count=7)
    # La API documenta que editar regenera las copias: siete círculos y la línea de corte.
    assert len(_ents(s)) == 8
    assert len(_de(s, "circle")) == 7
    assert _de(s, "arc") == []
    for i in range(7):
        centro = [30 * math.cos(2 * i * math.pi / 7), 30 * math.sin(2 * i * math.pi / 7)]
        assert any(e["center"] == pytest.approx(centro, abs=2e-4) for e in _de(s, "circle"))
    assert [e["radius"] for e in _de(s, "circle")] == pytest.approx([10] * 7)
    assert sum(_areas(s)) == pytest.approx(700 * math.pi, abs=1e-3)
    patron_editado, = _boceto(s)["patterns"]
    assert patron_editado["id"] == patron["id"]
    assert patron_editado["parameters"]["count"] == 7
    _reabrir(s)


def test_combinacion_4_hexagono_escalar_mover_extruir():
    s = api.Sesion()
    _llamar(s, "create_sketch", name="B")
    _llamar(s, "create_polygon", sketch="B", sides=6, radius=10, kind="inscribed",
            center_x=0, center_y=0)
    # Seis triángulos equiláteros de lado R: A = 6 × sqrt(3)R²/4.
    for radio, centro in ((10, [0, 0]), (15, [0, 0]), (15, [20, -5])):
        if radio == 15 and centro == [0, 0]:
            _llamar(s, "transform_sketch", sketch="B", scale=1.5, center_x=0, center_y=0)
        elif centro == [20, -5]:
            _llamar(s, "transform_sketch", sketch="B", dx=20, dy=-5)
        assert len(_de(s, "line")) == 6
        assert [e["length"] for e in _de(s, "line")] == pytest.approx([radio] * 6, abs=2e-4)
        guia, = _de(s, "circle", construccion=True)
        assert guia["radius"] == pytest.approx(radio)
        assert guia["center"] == pytest.approx(centro)
        for linea in _de(s, "line"):
            for extremo in (linea["start"], linea["end"]):
                assert math.dist(extremo, centro) == pytest.approx(radio, abs=2e-4)
        assert _areas(s) == pytest.approx([3 * math.sqrt(3) * radio**2 / 2], abs=2e-4)
        perfil, = _boceto(s)["profiles"]
        assert perfil["bounding_box"]["min"] == pytest.approx(
            [centro[0] - radio, centro[1] - math.sqrt(3) * radio / 2], abs=2e-4)
        assert perfil["bounding_box"]["max"] == pytest.approx(
            [centro[0] + radio, centro[1] + math.sqrt(3) * radio / 2], abs=2e-4)
    _llamar(s, "extrude", sketch="B", profile=0, distance=5)
    # V = (3sqrt(3)/2) × 15² × 5 = 2922.83573777 mm³.
    volumen = 3 * math.sqrt(3) * 15**2 / 2 * 5
    minimo = [5, -5 - 15 * math.sqrt(3) / 2, 0]
    maximo = [35, -5 + 15 * math.sqrt(3) / 2, 5]
    _solido(s, volumen, minimo, maximo)
    otra = _reabrir(s)
    _solido(otra, volumen, minimo, maximo)


def test_combinacion_3_linea_arco_tangente_y_alargar():
    s = api.Sesion()
    _llamar(s, "create_sketch", name="B")
    linea, = _ids(_llamar(s, "draw_line", sketch="B", start_x=0, start_y=0, end_x=20, end_y=0))
    assert _de(s, "line")[0]["length"] == pytest.approx(20)
    _boceto(s)
    _llamar(s, "draw_arc", sketch="B", tangent_to=linea, start_x=20, start_y=0, end_x=30, end_y=10)
    assert len(_ents(s)) == 2
    arco, = _de(s, "arc")
    assert arco["radius"] == pytest.approx(10)
    assert arco["center"] == pytest.approx([20, 10])
    assert arco["start"] == pytest.approx([20, 0])
    assert arco["end"] == pytest.approx([30, 10])
    _boceto(s)
    _llamar(s, "draw_line", sketch="B", start_x=-10, start_y=-10, end_x=-10, end_y=10)
    assert sorted(e["length"] for e in _de(s, "line")) == pytest.approx([20, 20])
    _boceto(s)
    # Se alarga el extremo libre: x=0 → -10, hasta la línea vertical x=-10.
    for alargada in (False, True):
        if alargada:
            _llamar(s, "extend_sketch_curve", sketch="B", curve=linea, point=[0, 0])
        recta, = [e for e in _de(s, "line") if e["id"] == linea]
        arco, = _de(s, "arc")
        assert recta["length"] == pytest.approx(30 if alargada else 20)
        assert recta["start"] == pytest.approx([-10 if alargada else 0, 0])
        assert recta["end"] == pytest.approx(arco["start"])
        assert arco["radius"] == pytest.approx(10)
        assert arco["center"] == pytest.approx([20, 10])
        vx, vy = (b - a for a, b in zip(recta["start"], recta["end"], strict=True))
        rx, ry = (a - b for a, b in zip(arco["start"], arco["center"], strict=True))
        # La tangente circular es (-ry, rx); atan2 da el ángulo sin perder precisión cerca de cero.
        tx, ty = -ry, rx
        angulo = abs(math.atan2(vx * ty - vy * tx, vx * tx + vy * ty))
        assert angulo < 1e-6
        assert len(_ents(s)) == 3
        assert _boceto(s)["tangents_off_arc"] == []
    _reabrir(s)


def test_combinacion_5_texto_copiar_escalar_y_extruir():
    s = api.Sesion()
    _llamar(s, "create_sketch", name="B")
    _llamar(s, "add_text", sketch="B", text="I", height=10, x=0, y=0)
    original, = _ents(s)
    assert original["type"] == "text"
    assert original["position"] == [0, 0]
    assert original["height"] == 10
    area, = _areas(s)
    assert area > 0
    _boceto(s)
    _llamar(s, "transform_sketch", sketch="B", entities=[original["id"]], dx=40, copy=True)
    assert len(_ents(s)) == 2
    assert _areas(s) == pytest.approx([area, area], abs=2e-4)
    copia, = [e for e in _ents(s) if e["id"] != original["id"]]
    assert copia["type"] == "text"
    assert copia["position"] == [40, 0]
    assert copia["height"] == 10
    _boceto(s)
    _llamar(s, "transform_sketch", sketch="B", entities=[original["id"]],
            scale=2, center_x=0, center_y=0)
    # Se difiere la aserción del hallazgo para comprobar también extrusión y reapertura.
    areas_escaladas = _areas(s)
    assert len(_ents(s)) == len(_de(s, "text")) == 2
    copia_escalada = next(e for e in _ents(s) if e["id"] == copia["id"])
    assert next(e for e in _ents(s) if e["id"] == original["id"])["height"] == 20
    _boceto(s)
    _llamar(s, "transform_sketch", sketch="B", entities=[original["id"]], dx=-20, dy=5)
    copia_movida = next(e for e in _ents(s) if e["id"] == copia["id"])
    assert copia_movida["position"] == copia["position"]
    assert next(e for e in _ents(s) if e["id"] == original["id"])["position"] == [-20, 5]
    areas_movidas = _areas(s)
    _boceto(s)
    _llamar(s, "extrude", sketch="B", profile=f"text:{original['id']}", distance=3)
    # V = 4A × 3 = 12A; A depende de la fuente instalada, se mide antes de transformar.
    for documento in (s, _reabrir(s)):
        propiedades = _llamar(documento, "get_physical_properties")
        assert len(propiedades["bodies"]) == 1
        assert propiedades["total"]["volume"] == pytest.approx(12 * area, abs=2e-3)
        geometria = _llamar(documento, "check_geometry")
        assert geometria["all_valid"] and geometria["all_closed"]
    # Una homotecia ×2 multiplica el área por 2²; la copia conserva A y sus atributos.
    assert areas_escaladas == pytest.approx([area, 4 * area], abs=1e-3)
    assert areas_movidas == pytest.approx([area, 4 * area], abs=1e-3)
    assert copia_escalada == copia_movida == copia


def test_combinacion_6_spline_desfase_recortar_cerrar_extruir():
    s = api.Sesion()
    _llamar(s, "create_sketch", name="B")
    # Cinco puntos colineales: spline de ajuste exacta y distancia/área calculables sin aproximación.
    puntos = [[x, 0] for x in (0, 10, 20, 30, 40)]
    original, = _ids(_llamar(s, "draw_spline", sketch="B", points=puntos, spline_type="fit_points"))
    assert len(_ents(s)) == 1
    assert _de(s, "spline")[0]["vertices"] == puntos
    _boceto(s)
    _llamar(s, "offset_sketch_curves", sketch="B", entity=original, distance=2)
    assert len(_ents(s)) == 2
    desfase, = [e for e in _ents(s) if e["id"] != original]
    assert desfase["type"] == "spline"
    assert desfase["vertices"][0] == [0, 2]
    assert desfase["vertices"][-1] == [40, 2]
    # La spline madre es y=0 entre x=0 y 40: la distancia mínima es |y|.
    for i in range(20):
        x, y = desfase["vertices"][round(i * (len(desfase["vertices"]) - 1) / 19)]
        assert 0 <= x <= 40
        assert abs(y) == pytest.approx(2, abs=1e-3)
    _boceto(s)
    _llamar(s, "draw_line", sketch="B", start_x=10, start_y=-1, end_x=10, end_y=3,
            construction=True)
    _llamar(s, "trim_sketch_curve", sketch="B", entity=desfase["id"], x=5, y=2)
    assert len(_ents(s)) == 3
    recortada, = [e for e in _de(s, "spline") if e["id"] != original]
    assert recortada["vertices"][0] == pytest.approx([10, 2], abs=2e-4)
    assert recortada["vertices"][-1] == pytest.approx([40, 2], abs=2e-4)
    _boceto(s)
    for inicio, fin in (([10, 2], [10, 0]), ([40, 0], [40, 2])):
        _llamar(s, "draw_line", sketch="B", start_x=inicio[0], start_y=inicio[1],
                end_x=fin[0], end_y=fin[1])
        _boceto(s)
    # Franja de ancho 40−10 y alto 2: A=60 mm²; V=60×3=180 mm³.
    assert len(_ents(s)) == 5
    assert [e["length"] for e in _de(s, "line")] == [2, 2]
    assert _areas(s) == pytest.approx([60], abs=1e-3)
    _llamar(s, "extrude", sketch="B", profile=0, distance=3)
    _solido(s, 180, [10, 0, 0], [40, 2, 3])
    _solido(_reabrir(s), 180, [10, 0, 0], [40, 2, 3])


def test_combinacion_7_proyeccion_de_caja_sigue_el_parametro():
    s = api.Sesion()
    _llamar(s, "create_parameter", name="largo_caja", expression="40 mm")
    _llamar(s, "create_box", length="largo_caja", width=20, height=10, anchor="corner")
    _solido(s, 8000, [0, 0, 0], [40, 20, 10])
    _llamar(s, "create_sketch", name="B", plane=">Z")
    assert len(_ents(s)) == 0
    assert _boceto(s)["plane_frame"]["origin"] == pytest.approx([0, 0, 10])
    _llamar(s, "project_to_sketch", sketch="B", faces=">Z", link=True)
    assert len(_ents(s)) == 4
    assert sorted(e["length"] for e in _de(s, "line")) == [20, 20, 40, 40]
    assert _areas(s) == pytest.approx([800])
    antes = _boceto(s)
    primera = _de(s, "line")[0]
    segunda = next(e for e in _de(s, "line") if e["id"] != primera["id"]
                   and any(math.dist(a, b) < 1e-6 for a in (e["start"], e["end"])
                           for b in (primera["start"], primera["end"])))
    resultado = api.llamar(s, "sketch_fillet", {
        "sketch": "B", "entity1": primera["id"], "entity2": segunda["id"], "radius": 3})
    if not resultado["ok"]:
        assert resultado["error_kind"]
        assert "proyect" in resultado["mensaje"].lower(), resultado
        assert _boceto(s) == antes
        area_quitada = 0
    else:
        arco, = _de(s, "arc")
        assert arco["radius"] == pytest.approx(3, abs=2e-4)
        # A = LW − (3² − π3²/4) si permite modificar las proyectadas.
        area_quitada = 9 * (1 - math.pi / 4)
        assert _areas(s) == pytest.approx([800 - area_quitada], abs=1e-3)
        _boceto(s)
    _llamar(s, "set_parameter", name="largo_caja", expression="60 mm")
    for documento in (s, _reabrir(s)):
        informe = _boceto(documento)
        assert len(informe["entities"]) == (5 if area_quitada else 4)
        assert _areas(documento) == pytest.approx([1200 - area_quitada], abs=1e-3)
        perfil, = informe["profiles"]
        assert perfil["bounding_box"]["min"] == pytest.approx([0, 0], abs=2e-4)
        assert perfil["bounding_box"]["max"] == pytest.approx([60, 20], abs=2e-4)
        _solido(documento, 12000, [0, 0, 0], [60, 20, 10])


def test_combinacion_8_patron_rectangular_editable_con_separacion_parametrica():
    s = api.Sesion()
    _llamar(s, "create_parameter", name="paso", expression="10 mm")
    _llamar(s, "create_sketch", name="B")
    linea, = _ids(_llamar(s, "draw_line", sketch="B", start_x=1, start_y=1, end_x=3, end_y=1))
    assert _de(s, "line")[0]["length"] == pytest.approx(2)
    _boceto(s)
    _llamar(s, "sketch_rectangular_pattern", sketch="B", entities=[linea], count1=3, count2=2,
            distance1="paso", distance2=20, spacing="spacing")
    for columnas, paso in ((3, 10), (4, 10), (4, 15)):
        if columnas == 4 and paso == 10:
            patron, = _boceto(s)["patterns"]
            _llamar(s, "edit_sketch_pattern", sketch="B", pattern=patron["id"], count1=4)
        elif paso == 15:
            _llamar(s, "set_parameter", name="paso", expression="15 mm")
        # En modo spacing, (i,j) se traslada (i×paso,j×20): 6 → 8 → 8 líneas de largo 2.
        lineas = _de(s, "line")
        assert len(_ents(s)) == len(lineas) == columnas * 2
        assert [e["length"] for e in lineas] == pytest.approx([2] * (columnas * 2))
        for i in range(columnas):
            for j in range(2):
                copia, = [e for e in lineas if e["start"] == pytest.approx([1 + i * paso, 1 + j * 20])]
                assert copia["end"] == pytest.approx([3 + i * paso, 1 + j * 20])
        patron, = _boceto(s)["patterns"]
        assert patron["parameters"]["count1"] == columnas
        assert patron["parameters"]["count2"] == 2
        s = _reabrir(s)




# ---------------------------------------------------------------- cm-3c: casos límite por herramienta
def _limite_sesion():
    s = api.Sesion()
    _llamar(s, "create_parameter", name="d", expression="1.5", kind="scalar")
    _llamar(s, "create_sketch", name="B")
    return s


def _limite_llamar(s, herramienta, esperado, **argumentos):
    antes = _boceto(s)
    resultado = api.llamar(s, herramienta, {"sketch": "B", **argumentos})
    if not resultado["ok"]:
        assert resultado["error_kind"] and resultado["error_kind"] not in {
            "INTERNAL_ERROR", "PYTHON_ERROR", "INTERNAL", "UNEXPECTED_ERROR",
        }, resultado
        mensaje = resultado["mensaje"].lower()
        # Se comprueban giros españoles, no palabras como «factor», comunes al inglés.
        assert any(palabra in mensaje for palabra in (
            "el ", "la ", "los ", "las ", "debe", "no ", "tiene que", "admite", "necesita", "expresión vacía",
        )), resultado
        assert _boceto(s) == antes, resultado
        _reabrir(s)
        assert esperado in {"error", "valido_o_error"}, resultado
        return False
    assert esperado != "error", resultado
    _boceto(s)
    return True


@pytest.mark.parametrize(("radio", "esperado"), [
    pytest.param(0, "error", id="cero"),
    pytest.param(-3, "error", id="negativo"),
    pytest.param(1e7, "error", id="enorme"),
    pytest.param(1e-7, "error", id="diminuto"),
    pytest.param("d * 2", "valido", id="expresion"),
    pytest.param("", "error", id="texto_vacio"),
    pytest.param(21, "error", id="radio_mayor_que_tramo_20"),
])
def test_limite_empalme(radio, esperado):
    s = _limite_sesion()
    lados = _rect(s, 1, 1, 41, 21)
    if not _limite_llamar(s, "sketch_fillet", esperado,
                         entity1=lados[0], entity2=lados[1], radius=radio):
        return
    r = 3 if isinstance(radio, str) else radio
    for documento in (s, _reabrir(s)):
        assert len(_ents(documento)) == 5
        arco, = _de(documento, "arc")
        assert arco["radius"] == pytest.approx(r, abs=5e-5)
        assert arco["center"] == pytest.approx([41 - r, 1 + r], abs=2e-4)
        assert sorted(e["length"] for e in _de(documento, "line")) == pytest.approx(
            sorted([40 - r, 20 - r, 40, 20]), abs=2e-4)
        # A = 40×20 − r² + πr²/4: se reemplaza una esquina por un cuarto de círculo.
        assert _areas(documento) == pytest.approx([800 - r * r * (1 - math.pi / 4)], abs=2e-4)


@pytest.mark.parametrize(("distancia", "esperado"), [
    pytest.param(0, "error", id="cero"),
    pytest.param(-3, "error", id="negativo"),
    pytest.param(1e7, "error", id="enorme"),
    pytest.param(1e-7, "error", id="diminuto"),
    pytest.param("d * 2", "valido", id="expresion"),
    pytest.param("", "error", id="texto_vacio"),
    pytest.param(21, "error", id="distancia_mayor_que_tramo_20"),
])
def test_limite_chaflan(distancia, esperado):
    s = _limite_sesion()
    lados = _rect(s, 1, 1, 41, 21)
    if not _limite_llamar(s, "sketch_chamfer", esperado,
                         line1=lados[0], line2=lados[1], distance=distancia):
        return
    d = 3 if isinstance(distancia, str) else distancia
    for documento in (s, _reabrir(s)):
        assert len(_ents(documento)) == len(_de(documento, "line")) == 5
        assert sorted(e["length"] for e in _de(documento, "line")) == pytest.approx(
            sorted([40 - d, 20 - d, 40, 20, d * math.sqrt(2)]), abs=2e-4)
        # A = 40×20 − d²/2: se quita un triángulo rectángulo de catetos d.
        assert _areas(documento) == pytest.approx([800 - d * d / 2], abs=2e-4)


@pytest.mark.parametrize(("distancia", "radio", "esperado"), [
    pytest.param(0, 10, "error", id="cero"),
    pytest.param(-3, 10, "valido", id="negativo"),
    pytest.param(1e7, 10, "error", id="enorme"),
    pytest.param(1e-7, 10, "valido", id="diminuto"),
    pytest.param("d * 2", 10, "valido", id="expresion"),
    pytest.param("", 10, "error", id="texto_vacio"),
    pytest.param(3, 2, "error", id="arco_radio_2_desfase_interior_3"),
    pytest.param(2, 2, "error", id="arco_radio_2_desfase_interior_2"),
])
def test_limite_desfase(distancia, radio, esperado):
    s = _limite_sesion()
    arco, = _ids(_llamar(s, "draw_arc", sketch="B", center_x=10, center_y=10,
                        start_x=10 + radio, start_y=10, sweep_angle=90))
    original = _ents(s)
    if not _limite_llamar(s, "offset_sketch_curves", esperado, entity=arco, distance=distancia):
        return
    d = 3 if isinstance(distancia, str) else distancia
    for documento in (s, _reabrir(s)):
        assert len(_ents(documento)) == len(_de(documento, "arc")) == 2
        assert [e for e in _ents(documento) if e["id"] == arco] == original
        copia, = [e for e in _de(documento, "arc") if e["id"] != arco]
        # Normal izquierda del arco antihorario: R' = R − distancia.
        assert copia["radius"] == pytest.approx(radio - d, abs=5e-5)
        assert copia["center"] == pytest.approx([10, 10], abs=2e-4)
        assert copia["start"] == pytest.approx([10 + radio - d, 10], abs=2e-4)
        assert copia["end"] == pytest.approx([10, 10 + radio - d], abs=2e-4)


@pytest.mark.parametrize(("x", "esperado"), [
    pytest.param(0, "valido_o_error", id="cero_coincidentes"),
    pytest.param(-3, "valido_o_error", id="negativo_coincidentes"),
    pytest.param(1e7, "valido_o_error", id="enorme_coincidentes"),
    pytest.param(1e-7, "valido_o_error", id="diminuto_coincidentes"),
    pytest.param("d * 2", "error", id="expresion_no_admitida_en_coordenada"),
    pytest.param("", "error", id="texto_vacio"),
])
def test_limite_recortar(x, esperado):
    s = _limite_sesion()
    argumentos = dict(sketch="B", start_x=-10, start_y=1, end_x=10, end_y=1)
    linea, = _ids(_llamar(s, "draw_line", **argumentos))
    otra, = _ids(_llamar(s, "draw_line", **argumentos))
    assert linea != otra and len(_ents(s)) == 2
    conservada, = [e for e in _ents(s) if e["id"] == otra]
    if not _limite_llamar(s, "trim_sketch_curve", esperado, entity=linea, x=x, y=1):
        return
    for documento in (s, _reabrir(s)):
        # Sin cruces interiores aislados, se borra solo la curva seleccionada: queda 20 mm.
        assert _ents(documento) == [conservada]
        assert _de(documento, "line")[0]["length"] == pytest.approx(20)
        assert _areas(documento) == []


@pytest.mark.parametrize(("radio", "lados", "esperado"), [
    pytest.param(0, 6, "error", id="cero"),
    pytest.param(-3, 6, "error", id="negativo"),
    pytest.param(1e7, 6, "error", id="enorme"),
    pytest.param(1e-7, 6, "error", id="diminuto"),
    pytest.param("d * 2", 6, "valido", id="expresion"),
    pytest.param("", 6, "error", id="texto_vacio"),
    pytest.param(10, 2, "error", id="dos_lados"),
    pytest.param(10, 1000, "error", id="mil_lados_tope_documentado_64"),
])
def test_limite_poligono(radio, lados, esperado):
    s = _limite_sesion()
    if not _limite_llamar(s, "create_polygon", esperado, sides=lados, radius=radio,
                         center_x=10, center_y=10):
        return
    r = 3 if isinstance(radio, str) else radio
    for documento in (s, _reabrir(s)):
        assert len(_ents(documento)) == 7
        lineas = _de(documento, "line")
        assert len(lineas) == 6
        # Hexágono inscrito: lado=2R·sen(π/6)=R; A=6R²·sen(π/3)/2.
        assert [e["length"] for e in lineas] == pytest.approx([r] * 6, abs=5e-5)
        assert _areas(documento) == pytest.approx([3 * math.sqrt(3) * r * r / 2], abs=2e-4)
        guia, = _de(documento, "circle", construccion=True)
        assert guia["center"] == pytest.approx([10, 10], abs=2e-4)
        assert guia["radius"] == pytest.approx(r, abs=5e-5)


@pytest.mark.parametrize(("vueltas", "esperado"), [
    pytest.param(0, "error", id="cero_vueltas"),
    pytest.param(-3, "error", id="negativo"),
    pytest.param(1e7, "error", id="enorme_supera_200_puntos"),
    pytest.param(1e-7, "valido", id="diminuto"),
    pytest.param("d * 2", "error", id="expresion_no_admitida_en_vueltas"),
    pytest.param("", "error", id="texto_vacio"),
    pytest.param(1, "valido", id="una_vuelta_control"),
])
def test_limite_espiral(vueltas, esperado):
    s = _limite_sesion()
    # R=10.000 hace visible hasta 1e-7 vueltas con el redondeo de get_sketch a 4 decimales.
    if not _limite_llamar(s, "draw_spiral", esperado, center=[10, 10], start=[10010, 10],
                         turns=vueltas, pitch=2):
        return
    for documento in (s, _reabrir(s)):
        assert len(_ents(documento)) == 1
        espiral, = _de(documento, "spline")
        assert espiral["degree"] == 3 and not espiral["closed"]
        vertices = espiral["vertices"]
        assert 4 <= len(vertices) <= 200
        assert all(math.dist(a, b) > 0 for a, b in zip(vertices, vertices[1:], strict=False))
        for i, punto in enumerate(vertices):
            # Espiral de Arquímedes: R(t)=10.000+2t, ángulo=2πt, 0≤t≤vueltas.
            t = vueltas * i / (len(vertices) - 1)
            r = 10000 + 2 * t
            assert punto == pytest.approx(
                [10 + r * math.cos(2 * math.pi * t), 10 + r * math.sin(2 * math.pi * t)], abs=5e-5)
        assert _areas(documento) == []


@pytest.mark.parametrize("x", [
    pytest.param(0, id="cero"), pytest.param(-3, id="negativo"),
    pytest.param(1e7, id="enorme"), pytest.param(1e-7, id="diminuto"),
    pytest.param("d * 2", id="expresion_no_admitida_en_coordenada"),
    pytest.param("", id="texto_vacio"),
])
def test_limite_alargar(x):
    s = _limite_sesion()
    linea, = _ids(_llamar(s, "draw_line", sketch="B", start_x=1, start_y=1, end_x=21, end_y=1))
    assert _de(s, "line")[0]["length"] == 20
    # Una sola línea: no existe otra curva que alcanzar, cualquiera sea el extremo elegido.
    _limite_llamar(s, "extend_sketch_curve", "error", curve=linea, point=[x, 1])


@pytest.mark.parametrize(("x", "esperado"), [
    pytest.param(0, "valido_o_error", id="extremo_inicial_cero"),
    pytest.param(-3, "error", id="negativo_fuera_de_curva"),
    pytest.param(1e7, "error", id="enorme_fuera_de_curva"),
    pytest.param(1e-7, "valido_o_error", id="diminuto_junto_al_extremo"),
    pytest.param("d * 2", "error", id="expresion_no_admitida_en_coordenada"),
    pytest.param("", "error", id="texto_vacio"),
    pytest.param(20, "valido_o_error", id="extremo_final_20"),
])
def test_limite_partir(x, esperado):
    s = _limite_sesion()
    linea, = _ids(_llamar(s, "draw_line", sketch="B", start_x=0, start_y=1, end_x=20, end_y=1))
    antes = _ents(s)
    if not _limite_llamar(s, "split_sketch_curve", esperado, curve=linea, point=[x, 1]):
        return
    for documento in (s, _reabrir(s)):
        # Partir en un extremo no debe agregar una curva de largo cero ni perder los 20 mm.
        assert _ents(documento) == antes
        assert _de(documento, "line")[0]["length"] == 20
        assert _areas(documento) == []


@pytest.mark.parametrize(("factor", "esperado"), [
    pytest.param(0, "error", id="cero"),
    pytest.param(-3, "error", id="negativo"),
    pytest.param(1e7, "error", id="enorme"),
    pytest.param(1e-7, "error", id="diminuto_menor_que_minimo_1e_6"),
    pytest.param("d * 2", "valido", id="expresion"),
    pytest.param("", "error", id="texto_vacio"),
])
def test_limite_escalar(factor, esperado):
    s = _limite_sesion()
    _rect(s, 1, 1, 41, 21)
    if not _limite_llamar(s, "transform_sketch", esperado, scale=factor, center_x=1, center_y=1):
        return
    for documento in (s, _reabrir(s)):
        assert len(_ents(documento)) == 4
        assert sorted(e["length"] for e in _de(documento, "line")) == [60, 60, 120, 120]
        # d=1,5; factor=d×2=3: largos ×3, área ×3².
        assert _areas(documento) == pytest.approx([800 * 9])
        perfil, = _boceto(documento)["profiles"]
        assert perfil["bounding_box"]["min"] == pytest.approx([1, 1])
        assert perfil["bounding_box"]["max"] == pytest.approx([121, 61])


@pytest.mark.parametrize(("cantidad", "esperado"), [
    pytest.param(0, "error", id="cero_instancias"),
    pytest.param(-3, "error", id="negativo"),
    pytest.param(10_000_000, "error", id="enorme"),
    pytest.param(1e-7, "error", id="diminuto_no_entero"),
    pytest.param("d * 2", "error", id="expresion_no_admitida_en_cantidad"),
    pytest.param("", "error", id="texto_vacio"),
    pytest.param(1, "error", id="una_instancia"),
    pytest.param(3, "valido", id="tres_instancias_control"),
])
def test_limite_patron(cantidad, esperado):
    s = _limite_sesion()
    linea, = _ids(_llamar(s, "draw_line", sketch="B", start_x=1, start_y=1, end_x=3, end_y=1))
    if not _limite_llamar(s, "sketch_rectangular_pattern", esperado, entities=[linea],
                         count1=cantidad, distance1=10, spacing="spacing"):
        return
    for documento in (s, _reabrir(s)):
        lineas = _de(documento, "line")
        assert len(_ents(documento)) == len(lineas) == cantidad
        # Copia i: (1+10i,1) → (3+10i,1), largo 2 mm, sin perfiles cerrados.
        assert [e["length"] for e in lineas] == [2] * cantidad
        for i in range(cantidad):
            copia, = [e for e in lineas if e["start"] == pytest.approx([1 + 10 * i, 1])]
            assert copia["end"] == pytest.approx([3 + 10 * i, 1])
        assert _areas(documento) == []


@pytest.mark.parametrize("camino", ["patron", "pegar"])
@pytest.mark.parametrize("altura", [10, 15])
def test_b239_copias_de_texto_conservan_altura_al_escalar_original_y_reabrir(camino, altura):
    s = api.Sesion()
    _llamar(s, "create_sketch", name="B")
    _llamar(s, "add_text", sketch="B", text="I", height=10)
    if altura != 10:
        _llamar(s, "set_parameter", name="Text_height", expression=f"{altura} mm")
    original, = _de(s, "text")
    assert original["height"] == altura
    if camino == "patron":
        _llamar(s, "sketch_rectangular_pattern", sketch="B", entities=[original["id"]],
                count1=3, distance1=40, spacing="spacing")
        destino = "B"
    else:
        _llamar(s, "create_sketch", name="C")
        _llamar(s, "copy_sketch_entities", source_sketch="B", sketch="C",
                entities=[original["id"]], dx=40)
        destino = "C"
    copias = [e for e in _llamar(s, "get_sketch", sketch=destino)["entities"]
              if destino != "B" or e["id"] != original["id"]]
    assert len(copias) == (2 if camino == "patron" else 1)
    assert all(e["height"] == altura for e in copias)
    _llamar(s, "transform_sketch", sketch="B", entities=[original["id"]],
            scale=2, center_x=0, center_y=0)
    for documento in (s, _reabrir(s)):
        assert next(e for e in _de(documento, "text") if e["id"] == original["id"])["height"] == 2 * altura
        actuales = _llamar(documento, "get_sketch", sketch=destino)["entities"]
        assert [e for e in actuales if destino != "B" or e["id"] != original["id"]] == copias
def test_h111_circular_sigue_el_angulo_y_conserva_expresion_en_la_receta():
    s = api.Sesion()
    _llamar(s, "create_parameter", name="ang", expression="90 deg", kind="angle")
    _llamar(s, "create_sketch", name="B")
    circulo, = _ids(_llamar(s, "draw_circle", sketch="B", center_x=30, center_y=0, radius=2))
    resultado = _llamar(s, "sketch_circular_pattern", sketch="B", entities=[circulo], count=3, total_angle="ang")
    patron = resultado["pattern"]
    ids = {e["id"] for e in _ents(s)}
    for angulo in (90, 180, 360, -90):
        _llamar(s, "set_parameter", name="ang", expression=f"{angulo} deg")
        for documento in (s, _reabrir(s)):
            assert {e["id"] for e in _ents(documento)} == ids
            paso = angulo / (3 if abs(angulo) == 360 else 2)
            for i in range(3):
                a = math.radians(i * paso)
                assert any(e["center"] == pytest.approx([30 * math.cos(a), 30 * math.sin(a)], abs=2e-4)
                           for e in _de(documento, "circle"))
            receta = _llamar(documento, "get_recipe")["recipe"]
            paso_boceto, = [op for op in receta["operaciones"] if "boceto" in op]
            assert paso_boceto["boceto"]["patrones"][0]["params"]["expresiones"]["angulo_total"] == "ang"
    _llamar(s, "edit_sketch_pattern", sketch="B", pattern=patron, total_angle="ang / 2")
    _llamar(s, "set_parameter", name="ang", expression="180 deg")
    copia = next(e for e in _de(s, "circle") if e["id"] != circulo)
    assert math.degrees(math.atan2(*reversed(copia["center"]))) == pytest.approx(45, abs=2e-4)
    _reabrir(s)


@pytest.mark.parametrize("circular", [False, True])
@pytest.mark.parametrize("editar", [False, True])
def test_h111_expresion_invalida_rechazada_sin_cambiar_el_boceto(circular, editar):
    s = api.Sesion()
    _llamar(s, "create_sketch", name="B")
    linea, = _ids(_llamar(s, "draw_line", sketch="B", start_x=10, start_y=0, end_x=12, end_y=0))
    nombre = "sketch_circular_pattern" if circular else "sketch_rectangular_pattern"
    args = {"entities": [linea], **({"count": 3} if circular else {"count1": 3, "distance1": 10})}
    if editar:
        patron = _llamar(s, nombre, sketch="B", **args)["pattern"]
        nombre, args = "edit_sketch_pattern", {"pattern": patron}
    args["total_angle" if circular else "distance1"] = "nada * 2"
    antes, receta = _boceto(s), _llamar(s, "get_recipe")
    resultado = api.llamar(s, nombre, {"sketch": "B", **args})
    assert not resultado["ok"]
    assert "nada" in resultado["mensaje"] and "no" in resultado["mensaje"].lower()
    assert _boceto(s) == antes
    assert _llamar(s, "get_recipe") == receta


@pytest.mark.parametrize("editar", [False, True])
@pytest.mark.parametrize("segunda_direccion", [False, True])
def test_h111_rectangular_distancias_y_direcciones_parametricas(editar, segunda_direccion):
    s = api.Sesion()
    _llamar(s, "create_parameter", name="paso", expression="10 mm")
    _llamar(s, "create_parameter", name="ang", expression="0 deg", kind="angle")
    _llamar(s, "create_sketch", name="B")
    linea, = _ids(_llamar(s, "draw_line", sketch="B", start_x=1, start_y=1, end_x=3, end_y=1))
    campos = {"distance1": "paso", "distance2": "paso * 2", "angle": "ang"}
    if segunda_direccion:
        campos["angle2"] = "ang + 90 deg"
    patron = _llamar(s, "sketch_rectangular_pattern", sketch="B", entities=[linea], count1=2, count2=2,
                    **({"distance1": 10, "distance2": 20} if editar else campos))["pattern"]
    if editar:
        _llamar(s, "edit_sketch_pattern", sketch="B", pattern=patron, **campos)
    ids = {e["id"] for e in _ents(s)}
    _llamar(s, "set_parameter", name="paso", expression="15 mm")
    _llamar(s, "set_parameter", name="ang", expression="90 deg")
    for documento in (s, _reabrir(s)):
        assert {e["id"] for e in _ents(documento)} == ids
        for punto in ([1, 1], [1, 16], [-29, 1], [-29, 16]):
            assert any(e["start"] == pytest.approx(punto, abs=2e-4) for e in _de(documento, "line"))
    # Editar solo la cantidad conserva las expresiones y usa los valores actuales.
    _llamar(s, "edit_sketch_pattern", sketch="B", pattern=patron, count1=3)
    assert len(_de(s, "line")) == 6
    receta = _llamar(s, "get_recipe")["recipe"]
    paso_boceto, = [op for op in receta["operaciones"] if "boceto" in op]
    assert paso_boceto["boceto"]["patrones"][0]["params"]["expresiones"]["distancia1"] == "paso"
    _llamar(s, "set_parameter", name="paso", new_name="separacion")
    _llamar(s, "set_parameter", name="separacion", expression="20 mm")
    for punto in ([1, 21], [-39, 21]):
        assert any(e["start"] == pytest.approx(punto, abs=2e-4) for e in _de(s, "line"))
    _reabrir(s)


@pytest.mark.parametrize("circular", [False, True])
def test_h111_panel_conserva_el_texto_al_crear_y_editar(circular):
    from PySide6.QtWidgets import QApplication
    from omnicad.restricciones import Boceto
    from omnicad.timeline.parametros import TablaParametros
    from omnicad.ui.editor_boceto import Lienzo

    app = QApplication.instance() or QApplication([])
    tabla = TablaParametros()
    tabla.agregar("paso", "10 mm")
    tabla.agregar("ang", "90 deg", "angulo")
    lienzo = Lienzo(Boceto(), tabla.evaluar)
    try:
        linea = lienzo.b.agregar_linea((10, 0), (12, 0))
        lienzo.seleccion = [linea]
        lienzo.set_herramienta("patron_circular" if circular else "patron_rectangular")
        control = lienzo.patron
        if circular:
            control.centro = (0, 0)
            control.recibir({**control.textos, "distribucion": "parcial", "angulo_total": "ang", "cantidad": "3"})
        else:
            control.recibir({**control.textos, "distancia1": "paso", "angulo1": "ang"})
        assert control.aceptar()
        registro, = lienzo.b.patrones
        clave, texto = ("angulo_total", "ang") if circular else ("distancia1", "paso")
        assert registro["params"]["expresiones"][clave] == texto
        assert lienzo.editar_patron(registro["id"])
        assert lienzo.patron.textos[clave] == texto
        assert lienzo.patron.aceptar()
        tabla.modificar("ang" if circular else "paso", "180 deg" if circular else "20 mm")
        assert lienzo.resolver().ok
        assert lienzo.b.patrones[0]["params"][clave] == (180 if circular else 20)
        puntos = [lienzo.b.coords(c.p1) for c in lienzo.b.curvas.values()]
        esperados = ((10, 0), (0, 10), (-10, 0)) if circular else ((10, 0), (10, 10), (10, 20))
        for punto in esperados:
            assert any(q == pytest.approx(punto, abs=2e-4) for q in puntos)
    finally:
        lienzo.close()
        lienzo.deleteLater()
        app.processEvents()


@pytest.mark.parametrize("diagonales", [False, True])
@pytest.mark.parametrize("igualdad", [False, True])
def test_b242_empalmar_cuatro_esquinas_conserva_el_rectangulo_restringido(tmp_path, diagonales, igualdad):
    s = api.Sesion()
    _llamar(s, "create_sketch", name="B")
    _llamar(s, "draw_rectangle", sketch="B", center_x=0, center_y=0,
            width=100, height=100, center_diagonals=diagonales)
    lados = [e["id"] for e in _de(s, "line")]
    if not diagonales:
        for lado, (x, y), eje in ((lados[0], (0, -50), -2), (lados[1], (50, 0), -1)):
            punto, = _llamar(s, "draw_point", sketch="B", x=x, y=y)["points"]
            _llamar(s, "add_constraint", sketch="B", type="midpoint", entities=[punto, lado])
            _llamar(s, "add_constraint", sketch="B", type="coincident", entities=[punto, eje])
    if igualdad:
        _llamar(s, "add_constraint", sketch="B", type="equal", entities=lados[:2])
    for lado in lados[:1 if igualdad else 2]:
        _llamar(s, "add_dimension", sketch="B", type="distance", entities=[lado], value=100)
    assert _boceto(s)["dof"] == 0
    for i in range(4):
        antes = _boceto(s)
        resultado = _llamar(s, "sketch_fillet", sketch="B", entity1=lados[i],
                            entity2=lados[(i + 1) % 4], radius=10)
        despues = _boceto(s)
        assert resultado["dof"] == despues["dof"] == 0, (i, resultado, despues)
        borradas = {r["id"] for r in antes["constraints"]} - {r["id"] for r in despues["constraints"]}
        assert borradas == set(resultado.get("constraints_deleted", []))
        assert all(r["type"] == "coincident" for r in antes["constraints"] if r["id"] in borradas)
        assert not resultado.get("dimensions_deleted")
        assert {c["id"] for c in antes["dimensions"]} <= {c["id"] for c in despues["dimensions"]}
        assert all(not c["reference"] for c in despues["dimensions"])
        assert despues["profiles"][0]["bounding_box"] == {"min": [-50, -50], "max": [50, 50]}
        assert _areas(s) == pytest.approx([10000 - (i + 1) * 100 * (1 - math.pi / 4)], abs=1e-3)
    cota = _boceto(s)["dimensions"][0]["id"]
    _llamar(s, "edit_dimension", sketch="B", dimension=cota, value=120)
    alto = 120 if igualdad else 100
    assert _boceto(s)["dof"] == 0
    assert _boceto(s)["profiles"][0]["bounding_box"] == {
        "min": [-60, -alto / 2], "max": [60, alto / 2]}
    assert _areas(s) == pytest.approx([120 * alto - 400 * (1 - math.pi / 4)], abs=1e-3)
    assert [e["radius"] for e in _de(s, "arc")] == pytest.approx([10] * 4)
    ruta = str(tmp_path / "rectangulo_empalmado.omnicad")
    _llamar(s, "save_document", path=ruta)
    otra = api.Sesion()
    _llamar(otra, "open_document", path=ruta)
    assert _boceto(otra) == _boceto(s)
    assert _boceto(otra)["dof"] == 0


def test_b242_empalme_con_extremos_distintos_unidos_por_coincidencias():
    from omnicad.restricciones import Boceto, resolver

    b = Boceto()
    b.asegurar_referencias([-1, -2])
    lados = b.agregar_rectangulo((-50, -50), (50, 50))
    coincidencias = []
    for lado in lados:
        linea = b.curvas[lado]
        anterior = linea.p1
        linea.p1 = b.agregar_punto(*b.coords(anterior))
        coincidencias.append(b.agregar_restriccion("coincidente", [anterior, linea.p1]))
    for lado, xy, eje in ((lados[0], (0, -50), -2), (lados[1], (50, 0), -1)):
        punto = b.agregar_punto(*xy)
        b.agregar_restriccion("punto_medio", [punto, lado])
        b.agregar_restriccion("coincidente", [punto, eje])
    for lado in lados[:2]:
        b.agregar_cota("distancia", [lado], "100")
    for i in range(5):
        if i:
            antes = set(b.restricciones)
            b.empalme(lados[i - 1], lados[i % 4], 10)
            assert antes - set(b.restricciones) == {coincidencias[i % 4]}
        resultado = resolver(b, {k.id: float(k.expresion) for k in b.cotas.values()})
        assert resultado.ok and resultado.gdl == 0, (i, resultado)

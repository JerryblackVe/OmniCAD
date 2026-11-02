# -*- coding: utf-8 -*-
"""Parámetros igual a Fusion: cada valor esperado de `CASOS` salió de Fusion real (docs/brechas_parametros.md, sección
«Comparado en Fusion real»), pasado de cm a mm. None = Fusion lo rechaza."""
import json
import math
import time

import pytest

from omnicad import api
from omnicad.timeline.documento import Documento
from omnicad.timeline.operaciones import OpPrimitiva, operacion_desde_dict
from omnicad.timeline.parametros import (ANGULO, ESCALAR, LONGITUD, TEXTO, ErrorExpresion, ErrorMagnitud,
                                         TablaParametros, _comas, evaluar, nombres_usados, renombrar_en, separar_nombre,
                                         tipo_de_unidad, validar_nombre)
from omnicad.timeline.unidades import FAMILIAS, TABLA, leer_unidad


def tabla_base():
    t = TablaParametros()
    for nombre, expresion in (("w", "10 mm"), ("h", "20 mm"), ("BookShelfHeight", "700 mm"), ("Height", "500 mm"),
                              ("Width", "300 mm")):
        t.agregar(nombre, expresion)
    return t


CASOS = [
    ("5 % 3", "mm", 2), ("5 mm % 3 mm", "mm", 2), ("7.5 % 2", "mm", 1.5), ("2 ^ 3", "", 8), ("2 mm ^ 2", "mm", None),
    ("(2 mm) ^ 2", "", None), ("max(1;2)", "", 2), ("max(1 mm; 2 mm)", "mm", 2), ("max(1,5 mm; 2 mm)", "mm", 2),
    ("min(1 mm; 2 mm)", "mm", 1), ("E", "", math.e), ("PI", "", math.pi), ("pi", "", math.pi),
    ("Gravity", "mm", None), ("Gravity", "", None), ("SpeedOfLight", "mm", None), ("Gravity", "cm/s^2", 9806.65),
    ("Gravity", "m/s^2", 9806.65), ("Gravity", "mm/s/s", 9806.65), ("SpeedOfLight", "cm/s", 299792458000.0),
    ("1 > 2", "", 0), ("1 < 2", "", 1), ("1 >= 1", "", 1), ("1 <= 1", "", 1), ("1 == 1", "", 1), ("1 <> 1", "", 0),
    ("1 != 1", "", None), ("if(1 > 2; 3; 4)", "", 4), ("if(w > h; w; h)", "mm", 20), ("if(1>2;3;if(2>1;5;6))", "", 5),
    ("if(1; 3; 4)", "", 3), ("if(0; 3; 4)", "", 4), ("if(1 > 2, 3, 4)", "", None), ("and(1;0)", "", None),
    ("(1>0) and (2>1)", "", 1), ("(1>0) and (2<1)", "", 0), ("1 and 0", "", 0), ("or(1;0)", "", None),
    ("(1>0) or (2<1)", "", 1), ("not(1>0)", "", 0), ("not (1>0)", "", 0), ("not 1", "", None),
    ("sign(-3)", "", 0), ("sign(-3 mm)", "mm", 0), ("sign(0)", "", 0), ("sign(3)", "", 1), ("sign(3 mm)", "mm", 1),
    ("sign(-0.5)", "", 0), ("log(100)", "", 2), ("log(E)", "", 0.434294482), ("ln(E)", "", 1),
    ("exp(1)", "", 2.718281828), ("pow(2;3)", "", 8), ("pow(2 mm;2)", "mm", None), ("random", "", None),
    ("sqrt(4)", "", 2), ("sqrt(4 mm * 4 mm)", "mm", 4), ("abs(-2 mm)", "mm", 2), ("ceil(1.2)", "", 2),
    ("ceil(1.2 mm)", "mm", 2), ("floor(1.2)", "", 1), ("round(2.5)", "", 3), ("round(3.5)", "", 4),
    ("round(-2.5)", "", -3), ("round(2.5 mm)", "mm", 3), ("sin(PI/4)", "", 0.013707355), ("sin(PI/4 rad)", "", None),
    ("sin(45 deg)", "", 0.707106781), ("sin(45)", "", 0.707106781), ("cos(0)", "", 1), ("tan(45)", "", 1),
    ("tan(45 deg)", "", 1), ("sin(PI/4 * 1 rad)", "", 0.707106781), ("sin((PI/4) rad)", "", None),
    ("sin(1 rad)", "", 0.841470985), ("sin(0.5 rad)", "", 0.479425539), ("sin(PI rad / 4)", "", 0.707106781),
    ("PI rad", "deg", 180), ("2 rad", "deg", 114.591559026), ("(PI/4) * 1 rad", "deg", 45), ("asin(1)", "mm", None),
    ("asin(1)", "", None), ("asin(1)", "deg", 90), ("acos(1)", "deg", 0), ("atan(1)", "deg", 45), ("acosh(1)", "deg", 0),
    ("asinh(0)", "deg", 0), ("atanh(0)", "deg", 0), ("cosh(0)", "", 1), ("sinh(0)", "", 0), ("tanh(0)", "", 0),
    ("2 w", "mm", None), ("2w", "mm", None), ("w h", "mm", None), ("w*h", "mm", None), ("w * h", "mm^2", 200),
    ("w * h / 1 mm", "mm", 200), ("w / h", "", 0.5), ("w / h", "mm", 0.5), ("w / 2", "mm", 5), ("1,5 mm", "mm", 1.5),
    ("1.5 mm", "mm", 1.5), ("10 mm * 2", "mm", 20), ("10 mm + 2", "mm", 12), ("w + 1 deg", "mm", None),
    ("1 mm + 1 cm", "mm", 11), ("1 cm + 1 mm", "mm", 11), ("1 in", "mm", 25.4), ('1 "', "mm", 25.4), ("1 ft", "mm", 304.8),
    ("1 '", "mm", 304.8), ("1 yd", "mm", 914.4), ("1 mi", "mm", 1609344), ("1 mil", "mm", 0.0254),
    ("1 micron", "mm", 0.001), ("1 um", "mm", None), ("1 hm", "mm", 1e5), ("1 km", "mm", 1e6), ("1 dm", "mm", 100),
    ("1 nauticalMile", "mm", 1852000), ("90 deg + 1 rad", "deg", 147.295779513), ("100 grad", "deg", 90), ("1deg", "deg", 1),
    ("2 mm 3", "mm", None), ("--1", "", 1), ("1 +", "", None), ("(1", "", None), ("", "", None), ("   ", "", None),
    ("5 mm", "deg", None), ("5", "mm", 5), ("sin(w)", "", None), ("sin(30 deg) * w", "mm", 5),
    ("sqrt(w*h)", "mm", 14.142135624), ("w^2", "", None), ("w ^ 2", "mm", None), ("w^2 / w", "mm", 10),
    ("1 mm ^ 2 / 1 mm", "mm", 1),
    # Los ejemplos de la ayuda
    ("if(BookShelfHeight < 500 mm; 2; if(BookShelfHeight < 1200 mm; 3; 4))", "", 3),
    ("if(BookShelfHeight <= 500 mm; 2; (if(BookShelfHeight >= 1200 mm; 4; 3)))", "", 3),
    ("if(( Height < 400 mm ) and ( Width < 400 mm ); 12 mm; 18 mm)", "mm", 18),
    ("if(( Height < 400 mm ) or ( Width < 400 mm ); 12 mm; 18 mm)", "mm", 12),
]


@pytest.mark.parametrize("expr,unidad,esperado", CASOS)
def test_igual_que_fusion(expr, unidad, esperado):
    valores = tabla_base().valores()
    if esperado is None:
        with pytest.raises(ErrorExpresion):
            evaluar(expr, tipo_de_unidad(unidad), valores, estricto=True, unidad=unidad)
    else:
        assert evaluar(expr, tipo_de_unidad(unidad), valores, estricto=True, unidad=unidad) == pytest.approx(esperado, rel=1e-6)


def test_random_cambia_en_cada_lectura():
    leidos = {evaluar("random()", ESCALAR) for _ in range(20)}
    assert len(leidos) > 1 and all(0 <= v <= 1 for v in leidos)


@pytest.mark.parametrize("expr,tipo,esperado", [
    ("max(w, h)", LONGITUD, 20), ("min(1,5)", ESCALAR, 1), ("max(1, 2, 3)", ESCALAR, 3), ("round(3.14159, 2)", ESCALAR, 3.14),
    ("1,5 mm", LONGITUD, 1.5), ("w * h", LONGITUD, 200), ("w * h / 10", LONGITUD, 20), ("2 ** 3", ESCALAR, 8),
    ("w ** 2", LONGITUD, 100), ("-2 ** 2", ESCALAR, -4), ("2 ** -1", ESCALAR, 0.5), ("sin(PI/4 rad)", ESCALAR, 0.000238, ),
    ("10 mm * 2 mm", LONGITUD, 20), ("10 mm + 2 deg", ESCALAR, 12), ("pi * 2", ESCALAR, 2 * math.pi),
])
def test_recetas_viejas_dan_lo_mismo(expr, tipo, esperado):
    """Sin `estricto` no se miran magnitudes: una receta guardada abre igual, aunque Fusion rechazaría la fórmula."""
    assert evaluar(expr, tipo, {"w": 10.0, "h": 20.0}) == pytest.approx(esperado, rel=1e-2)


def test_parametros_viejos_con_nombre_de_constante_ganan():
    t = TablaParametros.desde_lista([{"nombre": "E", "expresion": "7 mm", "tipo": LONGITUD},
                                     {"nombre": "Gravity", "expresion": "3", "tipo": ESCALAR},
                                     {"nombre": "log", "expresion": "2", "tipo": ESCALAR},
                                     {"nombre": "x", "expresion": "E * Gravity * log"}])
    assert t.valores()["x"] == 42
    assert nombres_usados("E + log") == {"E", "log"}


def test_nombre_de_constante_ya_no_se_acepta_nuevo():
    for nombre in ("E", "PI", "mm", "sin", "max", "if", "Gravity", "yd", "grad", "a b", "1a", "a.b", "a-b", "a'b"):
        with pytest.raises(ErrorExpresion):
            validar_nombre(nombre)
    for nombre in ("_a", "a_1", "a$b", 'a"b', "d1", "µm_x", "a°b", "ñandú"):
        validar_nombre(nombre)


def test_nombre_con_simbolos_se_puede_citar():
    t = TablaParametros()
    t.agregar("µm_x", "2 mm")
    t.agregar('a"b', "µm_x * 2")
    t.agregar("c$", 'a"b + 1 mm')
    assert t.valores()["c$"] == 5


def test_w_y_W_chocan():
    t = tabla_base()
    with pytest.raises(ErrorExpresion, match="Ya existe"):
        t.agregar("W", "1 mm")


def test_tope_de_anidado():
    with pytest.raises(ErrorExpresion, match="niveles"):
        evaluar("(" * 200 + "1" + ")" * 200, ESCALAR)
    assert evaluar("(" * 30 + "1" + ")" * 30, ESCALAR) == 1
    with pytest.raises(ErrorExpresion, match="larga"):
        evaluar("+".join(["1"] * 5000), ESCALAR)


def test_mensajes_en_espanol_y_magnitud_clara():
    t = tabla_base()
    with pytest.raises(ErrorMagnitud, match=r"mm\^2.*área.*longitud"):
        t.agregar("a", "w * h")
    with pytest.raises(ErrorExpresion, match="ángulo"):
        t.agregar("a", "w + 1 deg")
    with pytest.raises(ErrorExpresion, match="sqrt"):
        evaluar("sqrt(-1)", ESCALAR)
    with pytest.raises(ErrorExpresion, match="División por cero"):
        evaluar("5 % 0", ESCALAR)
    with pytest.raises(ErrorExpresion, match="3 argumentos"):
        evaluar("if(1; 2)", ESCALAR)


def test_35_familias_y_conversiones():
    assert len(FAMILIAS) + 2 == 35                    # No unit y Text no llevan abreviaturas
    assert leer_unidad("yd").factor == 914.4 and leer_unidad("mil").factor == pytest.approx(0.0254)
    assert evaluar("1 hr", "magnitud", unidad="min") == 3600
    assert leer_unidad("min").desde_interno(evaluar("1 hr", "magnitud", unidad="min")) == 60
    assert evaluar("1 kg", "magnitud", unidad="lbmass") == 1000
    assert evaluar("10 N", "magnitud", unidad="kg*m/s^2", estricto=True) == pytest.approx(1e7)
    assert leer_unidad("C").desde_interno(evaluar("68 F", "magnitud", unidad="C")) == pytest.approx(20)
    assert evaluar("100000 Pa", "magnitud", unidad="bar", estricto=True) == pytest.approx(1e5)
    assert evaluar("1 l", "magnitud", unidad="mm^3", estricto=True) == 1e6
    assert evaluar("90 rpm", "magnitud", unidad="deg/s", estricto=True) == 540
    assert evaluar("100 mm/s * 2 s", LONGITUD, estricto=True) == 200
    with pytest.raises(ValueError):
        leer_unidad("foo")
    assert all(u in TABLA for _, unidades in FAMILIAS.values() for u in unidades)


def test_el_numero_suelto_toma_la_unidad_del_parametro():
    t = TablaParametros()
    t.agregar("a", "2", LONGITUD, unidad="in")
    t.agregar("b", "a + 1", LONGITUD, unidad="in")
    t.agregar("c", "a * 2", LONGITUD, unidad="cm")
    assert t.valores()["a"] == pytest.approx(50.8) and t.valores()["b"] == pytest.approx(76.2)
    assert t.valores()["c"] == pytest.approx(101.6)
    copia = TablaParametros.desde_lista(t.a_lista())
    assert copia.obtener("a").texto_unidad == "in" and copia.valores()["a"] == pytest.approx(50.8)


def test_receta_sin_extras_queda_identica():
    t = TablaParametros()
    t.agregar("a", "2 mm", comentario="x")
    assert t.a_lista() == [{"nombre": "a", "expresion": "2 mm", "tipo": LONGITUD, "comentario": "x"}]


@pytest.fixture
def s():
    s = api.Sesion()
    llamar(s, "create_parameter", name="w", expression="10 mm")
    llamar(s, "create_parameter", name="h", expression="w * 2")
    llamar(s, "create_box", length="w", width="h", height=5, name="Caja")
    return s


def llamar(s, nombre, **args):
    r = api.llamar(s, nombre, args)
    assert r["ok"], r
    return r["result"]


def volumen(s):
    return llamar(s, "get_scene_info")["bodies"][0]["volume"]


def parametro(s, nombre):
    return next(p for p in llamar(s, "get_parameters")["parameters"] if p["name"] == nombre)


def test_renombrar_actualiza_todo_y_el_modelo_da_igual(s):
    llamar(s, "create_sketch", plane="XY", name="B")
    llamar(s, "draw_line", sketch="B", start_x=0, start_y=0, end_x=30, end_y=0)
    linea = next(iter(s.paso("B").boceto.curvas))
    llamar(s, "add_dimension", sketch="B", type="distance", entities=[linea], value="w * 3")
    antes, n = volumen(s), len(s.doc._deshacer)
    llamar(s, "set_parameter", name="w", new_name="ancho")
    assert volumen(s) == antes and len(s.doc._deshacer) == n + 1
    assert parametro(s, "h")["expression"] == "ancho * 2"
    assert s.doc.operacion("op1").p["ancho"] == "ancho"
    cota = next(iter(s.paso("B").boceto.cotas.values()))
    assert cota.expresion == "ancho * 3"
    llamar(s, "set_parameter", name="ancho", expression="20 mm")
    assert volumen(s) == pytest.approx(20 * 40 * 5)
    llamar(s, "undo")
    llamar(s, "undo")
    assert parametro(s, "w")["expression"] == "10 mm" and parametro(s, "h")["expression"] == "w * 2"
    assert s.doc.operacion("op1").p["ancho"] == "w"


def test_renombrar_no_toca_lo_que_se_le_parece():
    assert renombrar_en("w + w2 + a_w + max(w; 5 s) + 2 * s", "w", "x") == "x + w2 + a_w + max(x; 5 s) + 2 * s"
    assert renombrar_en("5 s + s", "s", "t") == "5 s + t"
    assert renombrar_en("min(1; min)", "min", "m2") == "min(1; m2)"


def test_renombrar_una_cota_y_un_valor_de_paso(s):
    llamar(s, "create_parameter", name="doble", expression="d1 * 2")
    llamar(s, "set_parameter", name="d1", new_name="largo_caja")
    assert parametro(s, "doble")["expression"] == "largo_caja * 2"
    assert parametro(s, "largo_caja")["feature"] == "op1"
    assert api.llamar(s, "set_parameter", {"name": "largo_caja", "new_name": "h"})["error_kind"] == "PARAMETER_EXISTS"


def test_extrusion_en_parametros_del_modelo():
    s = api.Sesion()
    llamar(s, "create_sketch", plane="XY", name="B")
    llamar(s, "draw_rectangle", sketch="B", x1=0, y1=0, x2=10, y2=10)
    llamar(s, "extrude", sketch="B", distance="15 mm")
    filas = [p for p in llamar(s, "get_parameters")["parameters"] if p.get("source") == "feature"]
    assert [(p["role"], p["expression"], p["value"], p["unit"]) for p in filas] == [
        ("distancia", "15 mm", 15, "mm"), ("conicidad", "0.0", 0, "deg")]
    d = filas[0]["name"]
    llamar(s, "create_parameter", name="doble", expression=f"{d} * 2")
    assert parametro(s, "doble")["value"] == 30
    llamar(s, "set_parameter", name=d, expression="20 mm")
    assert volumen(s) == pytest.approx(2000) and parametro(s, "doble")["value"] == 40
    extrusion = s.doc.operaciones[-1]
    assert s.doc.operacion(extrusion.id).p["distancia"] == "20 mm"
    llamar(s, "undo")
    assert volumen(s) == pytest.approx(1500) and parametro(s, d)["expression"] == "15 mm"
    llamar(s, "edit_feature", feature=extrusion.id, params={"distancia": "30 mm"})
    assert parametro(s, d)["expression"] == "30 mm" and parametro(s, "doble")["value"] == 60
    r = api.llamar(s, "delete_parameter", {"name": d})
    assert r["error_kind"] == "PARAMETER_IN_USE"


def test_numeracion_unica_entre_cotas_y_pasos():
    s = api.Sesion()
    llamar(s, "create_box", length=1, width=2, height=3)
    llamar(s, "create_box", length=4, width=5, height=6)
    assert [p["name"] for p in llamar(s, "get_parameters")["parameters"]] == [f"d{i}" for i in range(1, 7)]


def test_receta_vieja_abre_igual_y_recibe_nombres():
    """Una receta de antes de PAR-4: no tiene los parámetros de los pasos. Abre con los mismos valores."""
    s = api.Sesion()
    llamar(s, "create_parameter", name="a", expression="5 mm")
    llamar(s, "create_box", length="a * a", width=2, height=3)      # una magnitud que Fusion rechazaría
    receta = s.doc.a_dict()
    receta["parametros"] = [p for p in receta["parametros"] if not p.get("op")]
    receta.pop("contador_cotas", None)
    doc = Documento.desde_dict(json.loads(json.dumps(receta)))
    assert api.llamar(api.Sesion(doc), "get_scene_info")["result"]["bodies"][0]["volume"] == pytest.approx(25 * 2 * 3)
    assert [p.nombre for p in doc.parametros] == ["a", "d1", "d2", "d3"]
    assert doc.parametros.valores()["d1"] == 25
    otra = Documento.desde_dict(json.loads(json.dumps(doc.a_dict())))
    assert otra.parametros.a_lista() == doc.parametros.a_lista()


def test_paso_con_magnitud_rara_avisa_sin_romper():
    s = api.Sesion()
    llamar(s, "create_parameter", name="a", expression="5 mm")
    r = api.llamar(s, "create_box", {"length": "a * a", "width": 2, "height": 3})
    assert r["ok"] and any("mm^2" in x for x in r["avisos"])


def test_un_paso_con_expresion_mala_no_rompe_la_tabla():
    doc = Documento()
    doc.parametros.agregar("a", "5 mm")
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="a", largo="no_existe", alto="1"))
    assert doc.resultados[-1].estado == "error" and doc.parametros.valores()["a"] == 5


def test_nombre_igual_valor_en_un_campo_crea_favorito():
    s = api.Sesion()
    llamar(s, "create_sketch", plane="XY", name="B")
    llamar(s, "draw_rectangle", sketch="B", x1=0, y1=0, x2=10, y2=10)
    llamar(s, "extrude", sketch="B", distance="alto=15 mm")
    assert volumen(s) == pytest.approx(1500)
    p = parametro(s, "alto")
    extrusion = s.doc.operaciones[-1]
    assert p["favorite"] and p["expression"] == "15 mm" and p["feature"] == extrusion.id
    assert extrusion.p["distancia"] == "15 mm"
    llamar(s, "extrude", sketch="B", distance="alto2=alto*2")
    assert parametro(s, "alto2")["value"] == 30 and parametro(s, "alto2")["expression"] == "alto*2"
    r = api.llamar(s, "extrude", {"sketch": "B", "distance": "alto=1 mm"})
    assert r["error_kind"] == "PARAMETER_EXISTS"


def test_separar_nombre_no_confunde_comparaciones():
    assert separar_nombre("a==b") == (None, "a==b")
    assert separar_nombre("a<=b") == (None, "a<=b")
    assert separar_nombre("Largo=Ancho*2") == ("Largo", "Ancho*2")
    assert evaluar("x=3 mm", LONGITUD) == 3


def test_favoritos_filtros_orden_y_busqueda(s):
    llamar(s, "set_parameter", name="h", favorite=True, comment="Alto 10")
    llamar(s, "create_parameter", name="zeta", expression="3", kind="scalar", comment="Alto 9")
    assert [p["name"] for p in llamar(s, "get_parameters", favorites_only=True)["parameters"]] == ["h"]
    assert [p["name"] for p in llamar(s, "get_parameters", user_only=True)["parameters"]] == ["w", "h", "zeta"]
    assert [p["name"] for p in llamar(s, "get_parameters", search="ZET")["parameters"]] == ["zeta"]
    orden = lambda **k: [p["name"] for p in llamar(s, "get_parameters", user_only=True, **k)["parameters"]]     # noqa: E731
    assert orden(sort_by="name", descending=True) == ["zeta", "w", "h"]
    assert orden(sort_by="value") == ["zeta", "w", "h"]
    assert orden(sort_by="comment") == ["w", "zeta", "h"]            # «Alto 9» antes que «Alto 10»
    r = s.doc.a_dict()
    assert Documento.desde_dict(r).parametros.obtener("h").favorito


def test_unidades_en_la_api(s):
    r = llamar(s, "create_parameter", name="largo", expression="2", unit="in", favorite=True)
    assert (r["unit"], r["value"], r["kind"], r["favorite"]) == ("in", 2, "length", True)
    llamar(s, "create_box", length="largo", width=1, height=1)
    assert s.doc.parametros.valores()["largo"] == pytest.approx(50.8)
    assert llamar(s, "create_parameter", name="peso", expression="3 kg", unit="kg")["kind"] == "other"
    assert llamar(s, "create_parameter", name="sup", expression="w * h", unit="mm^2")["value"] == 200
    assert llamar(s, "set_parameter", name="sup", unit="cm^2")["value"] == 2
    assert api.llamar(s, "create_parameter", {"name": "x", "expression": "w * h"})["error_kind"] == "UNIT_MISMATCH"
    assert api.llamar(s, "create_parameter", {"name": "x", "expression": "5", "unit": "foo"})["error_kind"] == "INVALID_EXPRESSION"
    assert "Longitud" in llamar(s, "get_parameter_units")["families"]
    assert api.llamar(s, "set_parameter", {"name": "d1", "unit": "in"})["error_kind"] == "INVALID_ARGUMENTS"


def test_renombrar_no_toca_las_opciones_del_paso():
    s = api.Sesion()
    llamar(s, "create_parameter", name="total", expression="20 mm")
    llamar(s, "create_sketch", plane="XY", name="B")
    llamar(s, "draw_rectangle", sketch="B", x1=0, y1=0, x2=10, y2=10)
    llamar(s, "extrude", sketch="B", distance="total")
    s.doc.operaciones[-1].p["medida"] = "total"
    llamar(s, "set_parameter", name="total", new_name="largo")
    assert s.doc.operaciones[-1].p["distancia"] == "largo" and s.doc.operaciones[-1].p["medida"] == "total"


def test_entradas_enormes_dan_un_error_y_no_cuelgan():
    assert nombres_usados("1" + "+1" * 6000) == set()
    t = time.perf_counter()
    assert "." in _comas("(," * 40000)
    assert time.perf_counter() - t < 2
    for unidad in ("km^9999", "um^9999", "mm/um^9999"):
        r = api.llamar(api.Sesion(), "create_parameter", {"name": "a", "expression": "1", "unit": unidad})
        assert r["error_kind"] != "INTERNAL_ERROR" and "Unidad" in r["mensaje"], r


def test_texto_con_llaves():
    s = api.Sesion()
    llamar(s, "create_parameter", name="PartNumber", expression="A-7", kind="text")
    llamar(s, "create_parameter", name="Length", expression="10 mm")
    llamar(s, "create_parameter", name="Width", expression="4 mm")
    r = llamar(s, "create_parameter", name="etiqueta", expression="Pieza {PartNumber}", kind="text")
    assert r["value"] == "Pieza A-7" and r["expression"] == "Pieza {PartNumber}"
    r = llamar(s, "create_parameter", name="caja", expression="Es {Length} x {Width} y {Length*Width/1 mm}", kind="text")
    assert r["value"] == "Es 10 x 4 y 40"
    llamar(s, "set_parameter", name="PartNumber", expression="B-8")
    assert parametro(s, "etiqueta")["value"] == "Pieza B-8"
    llamar(s, "set_parameter", name="PartNumber", new_name="Codigo")
    assert parametro(s, "etiqueta")["expression"] == "Pieza {Codigo}"
    assert api.llamar(s, "delete_parameter", {"name": "Codigo"})["error_kind"] == "PARAMETER_IN_USE"
    assert llamar(s, "create_parameter", name="suelto", expression="{no_existe}", kind="text")["value"] == "{no_existe}"


def test_texto_viejo_con_llaves_sin_resolver_queda_igual():
    t = TablaParametros.desde_lista([{"nombre": "t", "expresion": "Hola {nada}", "tipo": TEXTO}])
    assert t.valores()["t"] == "Hola {nada}"


def test_csv_con_unidades_favoritos_y_seleccion(s, tmp_path):
    ruta = tmp_path / "p.csv"
    ruta.write_text("Name,Unit,Expression,Value,Comments,Favorite\n"
                    'grosor,in,.75,.75 in,Terciado,true\n'
                    "ancho2,in,grosor*2,1.5 in,,false\n"
                    "masa,kg,3,,,false\n"
                    "rotulo,Text,'Hola',,,false\n", encoding="utf-8")
    vista = llamar(s, "import_parameters", path=str(ruta), preview=True)
    assert vista["count"] == 4 and vista["rows"][0] == {"name": "grosor", "unit": "in", "expression": ".75", "comment": "Terciado"}
    assert "grosor" not in s.doc.parametros
    llamar(s, "import_parameters", path=str(ruta), names=["grosor", "masa", "rotulo"])
    assert parametro(s, "grosor")["value"] == 0.75 and parametro(s, "grosor")["favorite"]
    assert s.doc.parametros.valores()["grosor"] == pytest.approx(19.05)
    assert parametro(s, "rotulo")["value"] == "Hola" and "ancho2" not in s.doc.parametros
    r = api.llamar(s, "import_parameters", {"path": str(ruta), "names": ["nada"]})
    assert r["error_kind"] == "INVALID_ARGUMENTS"
    salida = tmp_path / "s.csv"
    llamar(s, "export_parameters", path=str(salida))
    texto = salida.read_text(encoding="utf-8")
    assert texto.splitlines()[0] == "Name,Unit,Expression,Value,Comments,Favorite"
    assert "grosor,in,.75,0.75,Terciado,true" in texto and "d1" not in texto


def test_csv_rechaza_magnitud_que_no_coincide(s, tmp_path):
    ruta = tmp_path / "p.csv"
    ruta.write_text("Name,Unit,Expression\nmal,mm,w * h\n", encoding="utf-8")
    assert api.llamar(s, "import_parameters", {"path": str(ruta)})["error_kind"] == "UNIT_MISMATCH"
    assert "mal" not in s.doc.parametros


def test_lector_rapido():
    inicio = time.perf_counter()
    for i in range(2000):
        evaluar(f"ancho / {i + 1} + 10 mm", LONGITUD, {"ancho": 60.0})
    assert time.perf_counter() - inicio < 1


def test_operacion_ida_y_vuelta_conserva_lo_renombrado():
    op = OpPrimitiva("op1", forma="caja", ancho="w * 2", largo="w", alto="3")
    assert op.renombrar_parametro("w", "x") and op.p["ancho"] == "x * 2" and op.p["largo"] == "x"
    assert operacion_desde_dict(op.a_dict()).p["largo"] == "x"
    assert not op.renombrar_parametro("nada", "y")
    assert ANGULO == "angulo"

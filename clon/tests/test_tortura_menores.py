# -*- coding: utf-8 -*-
"""Hallazgos menores de la prueba de tortura del 2026-11-01: B-127, T-19, T-21, T-22 y T-23."""
import json
import math
import time

import pytest
from OCP.BRepBuilderAPI import BRepBuilderAPI_GTransform
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.BRepGProp import BRepGProp
from OCP.GeomAbs import GeomAbs_BSplineSurface
from OCP.TopoDS import TopoDS_Shape
from OCP.gp import gp_GTrsf, gp_Mat

from omnicad import api
from omnicad.nucleo import aislado, chapa
from omnicad.nucleo import geometria as geo
from omnicad.nucleo import revision as rv
from omnicad.timeline.operaciones import OpCombinar


def llamar(s, nombre, **args):
    r = api.llamar(s, nombre, args)
    assert r["ok"], r
    return r["result"]


def falla(s, nombre, kind=None, **args):
    receta = json.dumps(s.doc.a_dict(), sort_keys=True)
    r = api.llamar(s, nombre, args)
    assert not r["ok"] and (kind is None or r["error_kind"] == kind), r
    assert json.dumps(s.doc.a_dict(), sort_keys=True) == receta          # atómica: el documento no cambió
    return r


def _a_y_b(x=20):
    s = api.Sesion()
    llamar(s, "create_box", length=40, width=40, height=40, name="A")
    llamar(s, "create_box", length=10, width=10, height=10, x=x, name="B")
    return s


def _volumen(s):
    return llamar(s, "get_physical_properties")["total"]["volume"]


# ---------------------------------------------------------------- B-127 · herramienta repetida
@pytest.mark.parametrize("herramientas", [["B", "B"], ["B", "b"]])
def test_b127_una_herramienta_repetida_cuenta_una_vez(herramientas):
    s = _a_y_b()
    llamar(s, "boolean_operation", target="A", tools=herramientas, operation="cut")
    referencia = _a_y_b()
    llamar(referencia, "boolean_operation", target="A", tools=["B"], operation="cut")
    assert _volumen(s) == _volumen(referencia) == pytest.approx(40**3 - 5 * 10 * 10)      # B asoma 5 mm dentro de A
    assert [c["name"] for c in llamar(s, "get_scene_info")["bodies"]] == ["A"]


def test_b127_el_paso_combinar_de_una_receta_tolera_herramientas_repetidas():
    s = _a_y_b()
    cuerpos = [c["id"] for c in llamar(s, "get_scene_info")["bodies"]]
    op = OpCombinar(s.doc.nuevo_id(), "Combinar", objetivo=cuerpos[0], herramientas=[cuerpos[1], cuerpos[1]],
                    operacion="cortar")
    s.doc.agregar(op)
    assert s.doc.resultados[-1].estado == "ok", s.doc.resultados[-1].mensaje
    assert _volumen(s) == pytest.approx(40**3 - 5 * 10 * 10)


# ---------------------------------------------------------------- T-19 · volúmenes diminutos
def test_t19_un_cuerpo_de_1e_10_mm3_no_aparece_con_volumen_cero():
    s = api.Sesion()
    creado = llamar(s, "create_box", length=1e-4, width=1e-3, height=1e-3, name="A")
    assert creado["bodies_created"][0]["volume"] == pytest.approx(1e-10, rel=1e-3)
    assert llamar(s, "get_scene_info")["bodies"][0]["volume"] == pytest.approx(1e-10, rel=1e-3)
    total = llamar(s, "get_physical_properties", density=7.85)["total"]
    assert total["volume"] == pytest.approx(1e-10, rel=1e-3) and total["mass_g"] == pytest.approx(7.85e-13, rel=1e-3)


def test_t19_los_volumenes_normales_siguen_con_4_decimales():
    s = api.Sesion()
    llamar(s, "create_box", length=10, width=10, height=10, name="A")
    llamar(s, "create_sphere", radius=1, x=100)
    volumenes = [c["volume"] for c in llamar(s, "get_scene_info")["bodies"]]
    assert volumenes == [1000.0, round(4 / 3 * math.pi, 4)]


# ---------------------------------------------------------------- T-22 · intersecar sin contacto
def _extruir_lejos(s):
    sketch = llamar(s, "create_sketch", plane="XY")["sketch"]["id"]
    llamar(s, "draw_rectangle", x1=100, y1=100, x2=110, y2=110)
    return falla(s, "extrude", "OPERATION_FAILED", sketch=sketch, profile=0, distance=10, operation="intersect",
                 target="A")


def _caja_lejos(s):
    return falla(s, "create_box", "OPERATION_FAILED", length=10, width=10, height=10, x=200, operation="intersect",
                 target="A")


def _combinar_lejos(s):
    llamar(s, "create_box", length=10, width=10, height=10, x=200, name="B")
    return falla(s, "boolean_operation", "OPERATION_FAILED", target="A", tools=["B"], operation="intersect")


@pytest.mark.parametrize("via", [_extruir_lejos, _caja_lejos, _combinar_lejos])
def test_t22_intersecar_sin_contacto_falla_y_no_borra_el_cuerpo(via):
    s = api.Sesion()
    llamar(s, "create_box", length=40, width=40, height=40, name="A")
    r = via(s)
    assert "vacío" in r["mensaje"]
    assert "A" in [c["name"] for c in llamar(s, "get_scene_info")["bodies"]]


def test_t22_intersecar_con_solape_sigue_dejando_lo_comun():
    s = api.Sesion()
    llamar(s, "create_box", length=40, width=40, height=40, name="A")                     # x de −20 a 20
    llamar(s, "create_box", length=10, width=10, height=10, x=18, operation="intersect", target="A")
    assert _volumen(s) == pytest.approx(7 * 10 * 10)                                      # solo la parte en x de 13 a 20


# ---------------------------------------------------------------- T-23 · nan e inf
@pytest.mark.parametrize("valor", [math.nan, math.inf, -math.inf])
@pytest.mark.parametrize("campo", ["x", "y", "z"])
def test_t23_una_posicion_no_finita_dice_que_no_es_un_numero_valido(campo, valor):
    r = falla(api.Sesion(), "create_box", "INVALID_ARGUMENTS", length=10, width=10, height=10, **{campo: valor})
    assert f"'{campo}'" in r["mensaje"] and "número válido" in r["mensaje"] and "Nombre desconocido" not in r["mensaje"]


@pytest.mark.parametrize("valor", [math.nan, math.inf])
def test_t23_una_distancia_no_finita_dice_que_no_es_un_numero_valido(valor):
    s = api.Sesion()
    llamar(s, "create_sketch", plane="XY")
    llamar(s, "draw_circle", radius=3)
    r = falla(s, "extrude", "INVALID_ARGUMENTS", distance=valor)
    assert "'distance'" in r["mensaje"] and "número válido" in r["mensaje"]


# ---------------------------------------------------------------- T-21 · autointersecciones que ya pasaron su tope
def _solevado():
    s = api.Sesion()
    llamar(s, "sketch_from_spec", name="A", plane="XY",
           entities=[{"type": "rectangle", "id": "R", "center": [0, 0], "width": 24, "height": 24}])
    llamar(s, "create_construction_plane", plane="XY", offset=30, name="P2")
    llamar(s, "sketch_from_spec", name="B", plane="P2",
           entities=[{"type": "circle", "id": "C", "center": [0, 0], "radius": 7}])
    llamar(s, "loft", sketches=["A", "B"])
    return next(iter(s.doc.estado_final.cuerpos.values())).forma


@pytest.fixture
def tope_agotado(monkeypatch):
    llamadas = []

    def correr(tarea, forma, tope, **args):
        llamadas.append(tope)
        raise aislado.TiempoAgotado(f"pasó de {tope:g} s y se cortó")

    monkeypatch.setattr(aislado, "correr", correr)
    monkeypatch.setattr(rv, "_AGOTADAS", {})
    return llamadas


def test_t21_la_misma_forma_no_se_vuelve_a_esperar_con_el_mismo_tope(tope_agotado):
    forma = _solevado()
    primera = rv.revisar(forma)
    segunda = rv.revisar(forma)
    assert tope_agotado == [rv.PLAZO_AUTOINTERSECCION]                        # el hijo corrió una sola vez
    for informe in (primera, segunda):
        assert informe["autointersecciones"] is None and informe["avisos"] == 1
        assert [p["tipo"] for p in informe["problemas"]] == ["autointerseccion_omitida"]
    assert "ya pasó" in segunda["problemas"][0]["mensaje"]


def test_t21_otra_forma_o_un_tope_mayor_vuelven_a_intentarse(tope_agotado, monkeypatch):
    forma = _solevado()
    rv.revisar(forma)
    rv.revisar(_solevado())                                                     # otra forma: otro intento
    monkeypatch.setattr(rv, "PLAZO_AUTOINTERSECCION", 2 * rv.PLAZO_AUTOINTERSECCION)
    rv.revisar(forma)                                                           # más tope que el que ya agotó: se intenta
    rv.revisar(forma)                                                           # y de ahí en más, no
    assert tope_agotado == [10.0, 10.0, 20.0]


# ---------------------------------------------------------------- T-19 · el mismo redondeo en los demás informes de volumen
def test_t19_los_demas_informes_de_volumen_tampoco_dan_cero_en_cuerpos_diminutos():
    s = api.Sesion()
    llamar(s, "create_box", length=1e-2, width=1e-2, height=1e-2, name="A")                       # 1e-6 mm³
    llamar(s, "create_box", length=1e-2, width=1e-2, height=1e-2, x=5e-3, name="B")
    assert llamar(s, "check_geometry")["bodies"][0]["volume"] == pytest.approx(1e-6, rel=1e-3)
    assert llamar(s, "get_bill_of_materials")["rows"][0]["volume"] == pytest.approx(1e-6, rel=1e-3)
    par = llamar(s, "check_interference")["pairs"][0]
    assert par["volume"] == pytest.approx(5e-7, rel=1e-3)
    malla = llamar(s, "tessellate", bodies="A", keep_original=False)["bodies_created"][0]["id"]
    assert llamar(s, "get_mesh_info", body=malla)["bodies"][0]["volume"] == pytest.approx(1e-6, rel=1e-2)


# ---------------------------------------------------------------- T-21 · la memoria de formas agotadas vence
def test_t21_la_forma_agotada_se_vuelve_a_intentar_pasados_los_minutos(tope_agotado):
    forma = _solevado()
    rv.revisar(forma)
    rv.revisar(forma)
    assert len(tope_agotado) == 1                                                  # dentro de los minutos, no se espera
    clave = next(iter(rv._AGOTADAS))
    f, tope, _ = rv._AGOTADAS[clave]
    rv._AGOTADAS[clave] = (f, tope, time.monotonic() - rv.VENCE_AGOTADA - 1)       # pasó el vencimiento
    rv.revisar(forma)
    assert len(tope_agotado) == 2
    rv.revisar(forma)
    assert len(tope_agotado) == 2                                                  # y vuelve a recordarse


# ---------------------------------------------------------------- T-19 · los tres informes que faltaban
def test_t19_el_eje_la_chapa_y_el_estudio_de_movimiento_tampoco_dan_cero_en_cuerpos_diminutos(tmp_path, monkeypatch):
    monkeypatch.setenv(chapa.VAR_REGLAS, str(tmp_path / "reglas_chapa.json"))        # la regla propia no toca la del usuario
    monkeypatch.setattr(chapa, "REGLAS_USUARIO", {})
    s = api.Sesion()
    eje = llamar(s, "create_shaft", segments=[{"diameter": 0.01, "length": 0.1}])["shaft"]       # 7,85e-6 mm³
    assert eje["volume"] == pytest.approx(math.pi * 0.005**2 * 0.1, rel=1e-3)

    s = api.Sesion()                                                                           # chapa de 1e-5 mm³
    sketch = llamar(s, "create_sketch", plane="XY")["sketch"]["id"]
    llamar(s, "draw_rectangle", x1=0, y1=0, x2=0.1, y2=0.05, sketch=sketch)
    llamar(s, "create_sheet_metal_rule", name="Fina", thickness=0.002, bend_radius=0.002)
    cuerpo = llamar(s, "create_base_flange", sketch=sketch, rule="Fina")["bodies_created"][0]["id"]
    assert llamar(s, "get_sheet_metal_info", body=cuerpo)["bodies"][0]["volume"] == pytest.approx(1e-5, rel=1e-3)

    k = 1e-3                                                                                   # el estudio de movimiento de ASM, a 1/1000
    s = api.Sesion()
    base = llamar(s, "create_box", length=40 * k, width=40 * k, height=10 * k)["bodies_created"][0]["id"]
    bloque = llamar(s, "create_box", length=10 * k, width=10 * k, height=10 * k, x=100 * k, y=50 * k)["bodies_created"][0]["id"]
    llamar(s, "create_component", bodies=[base], name="Base", grounded=True)
    llamar(s, "create_component", bodies=[bloque], name="Bloque")
    llamar(s, "create_joint", origin1="<Z", body1=bloque, origin2=">Z", body2=base, joint_type="revolute",
           offset=[15 * k, 0, 0])
    llamar(s, "create_box", length=6 * k, width=6 * k, height=6 * k, x=0, y=15 * k, z=10 * k)
    r = llamar(s, "motion_study", joint="Unión1", values=[0, 90, 180], check_interference=True)
    assert r["collision_values"] == [90.0]
    assert r["steps"][1]["interference"][0]["volume"] == pytest.approx(216 * k**3, rel=1e-3)


# ---------------------------------------------------------------- B-129 · volumen de una lente
@pytest.mark.parametrize("a, b", [((0, 0, 10), (20, 0, 15)), ((0, 0, 0), (10, 0, 0)), ((0, 0, 0), (7.07, 7.07, 0))])
def test_b129_el_volumen_de_una_lente_de_dos_esferas_cierra_con_la_formula(a, b):
    s = api.Sesion()
    llamar(s, "create_sphere", radius=20, x=a[0], y=a[1], z=a[2], name="A")
    llamar(s, "create_sphere", radius=20, x=b[0], y=b[1], z=b[2], name="B")
    llamar(s, "boolean_operation", target="A", tools=["B"], operation="intersect")
    d = math.dist(a, b)
    formula = math.pi * (4 * 20 + d) * (2 * 20 - d) ** 2 / 12                 # lente de dos casquetes de radio 20
    assert llamar(s, "get_physical_properties")["total"]["volume"] == pytest.approx(formula, rel=1e-6)


# ---------------------------------------------------------------- B-129 · la integración fina no puede tumbar al volumen
def _lente():
    return geo.booleano(geo.esfera(20, (0, 0, 0)), geo.esfera(20, (10, 0, 0)), "intersecar")


def test_b129_si_la_integracion_fina_falla_el_volumen_cae_a_la_de_siempre(monkeypatch):
    lente = _lente()
    por_defecto = geo.volumen_exacto(lente)
    fina = geo.volumen(lente)
    assert fina != pytest.approx(por_defecto, abs=1e-6)                       # la fina corrió y corrige la de siempre

    class KernelQueFallaConEps:
        SurfaceProperties_s = staticmethod(BRepGProp.SurfaceProperties_s)

        @staticmethod
        def VolumeProperties_s(forma, props, *resto):
            if resto and isinstance(resto[0], float):                         # la variante adaptativa (con Eps)
                raise RuntimeError("Standard_Failure")
            return BRepGProp.VolumeProperties_s(forma, props, *resto)

    monkeypatch.setattr(geo, "BRepGProp", KernelQueFallaConEps)
    assert geo.volumen(lente) == pytest.approx(por_defecto, abs=1e-9)


def test_b129_una_lente_aplastada_o_una_forma_vacia_siguen_dando_un_volumen():
    gt = gp_GTrsf()
    gt.SetVectorialPart(gp_Mat(1, 0, 0, 0, 1, 0, 0, 0, 1e-12))                # lente de 1e-12 de espesor
    plana = BRepBuilderAPI_GTransform(_lente(), gt, True).Shape()
    assert geo.es_forma_libre(plana) and 0 <= geo.volumen(plana) < 1e-6
    assert geo.volumen(TopoDS_Shape()) == 0.0


# ---------------------------------------------------------------- B-129 · cuerpos de más de 64 caras libres
def _lentes(n):
    """n lentes oblicuas (una cara B-spline y una esférica cada una) en una grilla, como UN cuerpo, y su volumen exacto."""
    formas = []
    for i in range(n):
        o = ((i % 10) * 60.0, (i // 10) * 60.0, 10.0)
        formas.append(geo.booleano(geo.esfera(20, o), geo.esfera(20, (o[0] + 20, o[1], o[2] + 5)), "intersecar"))
    d = math.hypot(20, 5)
    return geo.compuesto(formas), n * math.pi * (4 * 20 + d) * (2 * 20 - d) ** 2 / 12


def test_b129_un_cuerpo_de_mas_de_64_caras_libres_cierra_con_la_formula():
    cuerpo, exacto = _lentes(70)
    assert len(geo.caras(cuerpo)) == 140 and geo.es_forma_libre(cuerpo)
    assert abs(geo.volumen_exacto(cuerpo) - exacto) > 1e-5 * exacto             # la integración de siempre erra 5e-5
    assert geo.volumen(cuerpo) == pytest.approx(exacto, rel=1e-6)


def test_b129_las_caras_libres_grandes_siguen_con_la_integracion_de_siempre():
    s = api.Sesion()                                                          # una rosca modelada: B-spline de más de 170 polos
    llamar(s, "create_cylinder", radius=5, height=20)
    llamar(s, "create_thread", faces="not (>Z or <Z)", thread="M10", modeled=True, length=15)
    rosca = next(iter(s.doc.estado_final.cuerpos.values())).forma
    assert geo.es_forma_libre(rosca) and not geo._apta_para_integral_fina(rosca)
    assert geo._apta_para_integral_fina(_lentes(1)[0])                          # y la lente chica sí


def test_b129_los_bordes_de_la_regla_son_300_caras_y_170_polos(monkeypatch):
    lente = _lentes(1)[0]
    polos = max(b.NbUPoles() * b.NbVPoles() for b in (BRepAdaptor_Surface(c).BSpline() for c in geo.caras(lente)
                                                       if BRepAdaptor_Surface(c).GetType() == GeomAbs_BSplineSurface))
    assert polos <= geo._POLOS_FINOS == 170
    monkeypatch.setattr(geo, "_POLOS_FINOS", polos)
    assert geo._apta_para_integral_fina(lente)                                  # justo en el borde
    monkeypatch.setattr(geo, "_POLOS_FINOS", polos - 1)
    assert not geo._apta_para_integral_fina(lente)                              # un polo de más
    monkeypatch.undo()

    cajas = [geo.caja(1, 1, 1, (3.0 * i, 0, 0)) for i in range(49)]            # 49 cajas = 294 caras; la lente suma 2
    for esferas, caras, apta in ((4, 300, True), (5, 301, False)):
        cuerpo = geo.compuesto(cajas + [geo.esfera(1, (0, 10.0 * k, 5)) for k in range(esferas)] + [_lentes(1)[0]])
        assert len(geo.caras(cuerpo)) == caras
        assert geo._apta_para_integral_fina(cuerpo) is apta

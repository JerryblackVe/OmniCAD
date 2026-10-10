# -*- coding: utf-8 -*-
"""Topes al tamaño del trabajo (Hallazgos de pruebas de uso, «SIN TOPES»): torsión del barrido, instancias de un
patrón, lados de un polígono y triángulos de un remallado. Se validan ANTES de calcular y el mensaje dice el máximo.

Los valores pedidos quedan apenas por encima de cada tope (nunca 1e9): si el tope faltara, la prueba no debe
comerse la memoria de la PC."""
import json
import math

import numpy as np
import pytest
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakePolygon
from OCP.GC import GC_MakeArcOfCircle, GC_MakeCircle
from OCP.gp import gp_Ax2, gp_Dir, gp_Pnt

from omnicad import api
from omnicad.nucleo import geometria as geo
from omnicad.nucleo import malla as ml
from omnicad.nucleo import solidos_crear as sc
from omnicad.nucleo import superficies as sf


@pytest.fixture
def s():
    return api.Sesion()


def foto(sesion):
    """Todo lo que una falla atómica no debe cambiar (también el contador de ids)."""
    doc = sesion.doc
    return (json.dumps(doc.a_dict(), sort_keys=True), [(r.estado, r.mensaje) for r in doc.resultados],
            len(doc._deshacer), len(doc._rehacer), doc.modificado)


def falla(sesion, nombre, **args):
    r = api.llamar(sesion, nombre, args)
    assert r["ok"] is False, r
    return r


def linea(a, b):
    return BRepBuilderAPI_MakeEdge(gp_Pnt(*map(float, a)), gp_Pnt(*map(float, b))).Edge()


def rectangulo():
    """Alambre de 4 × 2 en XY, perpendicular a la ruta Z."""
    mk = BRepBuilderAPI_MakePolygon()
    for p in ((-2, -1, 0), (2, -1, 0), (2, 1, 0), (-2, 1, 0)):
        mk.Add(gp_Pnt(*map(float, p)))
    mk.Close()
    return mk.Wire()


RUTA = [linea((0, 0, 0), (0, 0, 10))]


# ---------------------------------------------------------------- patrones (núcleo)
def test_patron_circular_admite_10000_instancias_y_no_una_mas():
    assert len(sc.transformaciones_circulares((0, 0, 0), (0, 0, 1), 10_000)) == 10_000
    with pytest.raises(geo.ErrorGeometria, match=r"10\.000"):
        sc.transformaciones_circulares((0, 0, 0), (0, 0, 1), 10_001)
    with pytest.raises(geo.ErrorGeometria, match=r"10\.000"):     # simétrico: 2·5001 − 1 = 10.001
        sc.transformaciones_circulares((0, 0, 0), (0, 0, 1), 5_001, simetrico=True)
    with pytest.raises(geo.ErrorGeometria, match="al menos 1"):   # antes: ZeroDivisionError
        sc.transformaciones_circulares((0, 0, 0), (0, 0, 1), 0)


def test_patron_rectangular_cuenta_las_dos_direcciones():
    assert len(sc.transformaciones_rectangulares((1, 0, 0), 100, 10.0, (0, 1, 0), 100, 10.0)) == 10_000
    with pytest.raises(geo.ErrorGeometria, match=r"10\.100"):
        sc.transformaciones_rectangulares((1, 0, 0), 101, 10.0, (0, 1, 0), 100, 10.0)
    with pytest.raises(geo.ErrorGeometria, match=r"10\.000"):
        sc.transformaciones_rectangulares((1, 0, 0), 5_001, 10.0, simetrico1=True)
    # sin dirección 2, n2 no cuenta
    assert len(sc.transformaciones_rectangulares((1, 0, 0), 10_000, 10.0, None, 10_000)) == 10_000


def test_patron_en_ruta_tiene_el_mismo_tope():
    with pytest.raises(geo.ErrorGeometria, match=r"10\.000"):
        sc.transformaciones_en_ruta(linea((0, 0, 0), (100, 0, 0)), 10_001, 100.0)


def test_unir_instancias_en_una_sola_booleana():
    """Revisión: «Combinar» unía las copias de a una (geo.unir_todos) y crece con el cuadrado: 20 × 20 cubos tardaba
    51 s y 32 × 32, más de 200 s. En una sola booleana, 0,3 s; el resultado es el mismo."""
    import time
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
    from OCP.TopAbs import TopAbs_SOLID
    cubo = BRepPrimAPI_MakeBox(10.0, 10.0, 10.0).Shape()
    formas = [sc.aplicar(cubo, t) for t in sc.transformaciones_rectangulares(
        (1, 0, 0), 20, 20.0, (0, 1, 0), 20, 20.0, distribucion="espaciado")]
    t = time.perf_counter()
    r = sc.unir_instancias(formas)
    assert time.perf_counter() - t < 5
    assert geo.es_valida(r) and geo.volumen(r) == pytest.approx(400_000.0)
    assert len(list(geo._explorar(r, TopAbs_SOLID))) == 400
    solapados = [sc.aplicar(cubo, t) for t in sc.transformaciones_rectangulares((1, 0, 0), 3, 5.0, (0, 1, 0), 3, 5.0,
                                                                                 distribucion="espaciado")]
    una, de_a_una = sc.unir_instancias(solapados), geo.unir_todos(solapados)
    assert geo.volumen(una) == pytest.approx(geo.volumen(de_a_una)) == pytest.approx(20 * 20 * 10)
    assert len(geo.caras(una)) == len(geo.caras(de_a_una)) == 6


# ---------------------------------------------------------------- barrido con torsión (núcleo)
def test_barrido_rechaza_torsion_de_mas_de_10_vueltas():
    sc.validar_torsion(3600.0)
    sc.validar_torsion(-3600.0)
    for grados in (3601.0, -3601.0, math.nan, math.inf):
        with pytest.raises(geo.ErrorGeometria, match=r"3600° \(10 vueltas\)"):
            sc.barrer([rectangulo()], RUTA, torsion=grados)


def test_barrido_de_superficie_rechaza_torsion_de_mas_de_50_vueltas():
    """Su tope es otro (una sección cada 10°: 18.000° tarda 49 s y andaba; 36.000°, 115 s y falla)."""
    for grados in (18_001.0, -18_001.0, math.nan, math.inf):
        with pytest.raises(geo.ErrorGeometria, match=r"18000° \(50 vueltas\)"):
            sf.barrer_superficie(linea((-5, 0, 0), (5, 0, 0)), RUTA, torsion=grados)
    # más de 10 vueltas (el tope del barrido sólido) sigue andando: 3601° → 362 secciones; helicoide de 10 × 200
    f = sf.barrer_superficie(linea((-5, 0, 0), (5, 0, 0)), [linea((0, 0, 0), (0, 0, 200))], torsion=3601.0)
    assert geo.es_valida(f) and geo.area(f) == pytest.approx(2647.3, rel=2e-3)


def test_barrido_con_torsion_exacto_en_rutas_largas_y_curvas():
    """Guía de torsión en modo plano: antes (modo curvilíneo) 90° en 50 mm perdía 2,1 % de volumen, las rutas de
    100 mm o más fallaban con cualquier ángulo y 3600° tardaba 9 s y fallaba. La sección es constante: volumen =
    8 mm² × largo de la ruta."""
    for largo, grados in ((50, 90.0), (100, 10.0), (300, 720.0), (50, 3600.0)):
        s = sc.barrer([rectangulo()], [linea((0, 0, 0), (0, 0, largo))], torsion=grados)
        assert geo.es_valida(s) and geo.volumen(s) == pytest.approx(8 * largo, rel=1e-4), (largo, grados)
    r = math.sqrt(0.5)
    recta_arco = [linea((0, 0, 0), (0, 0, 40)),          # recta + arco tangente de R30 y 90° (sin quiebre)
                  BRepBuilderAPI_MakeEdge(GC_MakeArcOfCircle(gp_Pnt(0, 0, 40), gp_Pnt(30 - 30 * r, 0, 40 + 30 * r),
                                                             gp_Pnt(30, 0, 70)).Value()).Edge()]
    s = sc.barrer([rectangulo()], recta_arco, torsion=720.0)
    assert geo.es_valida(s) and geo.volumen(s) == pytest.approx(8 * (40 + 15 * math.pi), rel=1e-4)


def test_guia_plana_solo_en_rutas_abiertas_sin_quiebres():
    """En un quiebre el modo plano tira abajo el kernel (codo de 90° con 3600°: violación de acceso) y en las rutas
    cerradas no resuelve: ahí queda el modo curvilíneo de antes."""
    codo = sc._alambre([linea((0, 0, 0), (0, 0, 50)), linea((0, 0, 50), (50, 0, 50))])
    circulo = sc._alambre([BRepBuilderAPI_MakeEdge(GC_MakeCircle(gp_Ax2(gp_Pnt(30, 0, 0), gp_Dir(0, 1, 0)),
                                                                 30.0).Value()).Edge()])
    seguidas = sc._alambre([linea((0, 0, 0), (0, 0, 50)), linea((0, 0, 50), (0, 0, 80))])
    assert not sc._guia_plana_posible(codo) and not sc._guia_plana_posible(circulo)
    assert sc._guia_plana_posible(seguidas) and sc._guia_plana_posible(sc._alambre(RUTA))


def _quiebre(grados, largo=50.0):
    """Dos rectas de `largo` con un quiebre de `grados` entre ellas."""
    g = math.radians(grados)
    return [linea((0, 0, 0), (0, 0, largo)), linea((0, 0, largo), (largo * math.sin(g), 0, largo + largo * math.cos(g)))]


def _sin_barrer(monkeypatch, plano_falla=False):
    """Reemplaza el cálculo (_barrer) por uno falso: anota cada modo pedido (True = plano). Así las pruebas no corren
    el curvilíneo, que en estos casos tarda minutos o tira abajo el proceso."""
    modos = []

    def falso(*_a, guia_plana):
        modos.append(guia_plana)
        if guia_plana and plano_falla:
            raise geo.ErrorGeometria("El kernel no pudo barrer el perfil por la ruta.")
        return "barrido"
    monkeypatch.setattr(sc, "_barrer", falso)
    return modos


def test_barrido_con_torsion_rechaza_rutas_con_esquinas_antes_de_calcular(monkeypatch):
    """Revisión: con un quiebre el curvilíneo tardaba de 15 s a minutos y daba un sólido inválido (90° en un codo de
    90° o de 10°), o tiraba abajo el proceso (3600°); con 0,5° el plano anda."""
    modos = _sin_barrer(monkeypatch)
    for grados in (90.0, 10.0, 1.0):
        with pytest.raises(geo.ErrorGeometria, match=r"sin esquinas: la ruta quiebra .* \(admite hasta 0,5°\)"):
            sc.barrer([rectangulo()], _quiebre(grados), torsion=90.0)
    assert modos == []                                  # no calculó nada
    assert sc.barrer([rectangulo()], _quiebre(1.0), torsion=0.0) == "barrido"     # sin torsión las esquinas valen
    assert sc.barrer([rectangulo()], _quiebre(0.4), torsion=3600.0) == "barrido" and modos[-1] is True


def test_barrido_con_torsion_en_quiebre_chico_es_exacto():
    s = sc.barrer([rectangulo()], _quiebre(0.5), torsion=3600.0)
    assert geo.es_valida(s) and geo.volumen(s) == pytest.approx(800.0, rel=1e-3)


def test_barrido_con_torsion_en_ruta_cerrada_admite_1800(monkeypatch):
    """Una ruta cerrada va en modo curvilíneo: su tope es TORSION_MAXIMA_CURVILINEA, antes de calcular."""
    modos = _sin_barrer(monkeypatch)
    r = math.sqrt(0.5)
    circulo = [BRepBuilderAPI_MakeEdge(GC_MakeArcOfCircle(gp_Pnt(0, 0, 0), gp_Pnt(30, 0, 30),
                                                          gp_Pnt(60, 0, 0)).Value()).Edge(),
               BRepBuilderAPI_MakeEdge(GC_MakeArcOfCircle(gp_Pnt(60, 0, 0), gp_Pnt(30 + 30 * r, 0, -30 * r),
                                                          gp_Pnt(0, 0, 0)).Value()).Edge()]
    with pytest.raises(geo.ErrorGeometria, match=r"ruta cerrada .* como máximo ±1800° \(5 vueltas\)"):
        sc.barrer([rectangulo()], circulo, torsion=1801.0)
    assert modos == []
    assert sc.barrer([rectangulo()], circulo, torsion=1800.0) == "barrido" and modos == [False]


def test_barrido_no_cae_al_curvilineo_de_mas_de_1800(monkeypatch):
    """Revisión: recta + arco de R2 con 3600°: el plano falla y el curvilíneo tiraba abajo el proceso (0xC0000005)."""
    modos = _sin_barrer(monkeypatch, plano_falla=True)
    with pytest.raises(geo.ErrorGeometria, match=r"no se pudo resolver en esta ruta.*±1800° \(5 vueltas\)"):
        sc.barrer([rectangulo()], RUTA, torsion=3600.0)
    assert modos == [True]
    assert sc.barrer([rectangulo()], RUTA, torsion=1800.0) == "barrido" and modos[1:] == [True, False]
    # con un quiebre chico (0,3°) el curvilíneo tardaría minutos: el error del plano queda
    del modos[:]
    with pytest.raises(geo.ErrorGeometria, match="no pudo barrer"):
        sc.barrer([rectangulo()], _quiebre(0.3), torsion=90.0)
    assert modos == [True]


# ---------------------------------------------------------------- herramientas de la API
def _boceto_barrido(s):
    assert api.llamar(s, "sketch_from_spec", {"name": "Perfil", "entities": [
        {"type": "rectangle", "center": [0, 0], "width": 4, "height": 2}]})["ok"]
    assert api.llamar(s, "sketch_from_spec", {"plane": "XZ", "name": "Ruta", "entities": [
        {"type": "line", "start": [0, 0], "end": [0, 10]}]})["ok"]


def test_sweep_rechaza_twist_angle_de_mas_sin_gastar_un_id(s):
    _boceto_barrido(s)
    antes = foto(s)
    r = falla(s, "sweep", sketch="Perfil", profile=0, path_sketch="Ruta", twist_angle=3601)
    assert r["error_kind"] == "INVALID_ARGUMENTS" and "3600° (10 vueltas)" in r["mensaje"]
    assert foto(s) == antes
    # con una expresión la frena el núcleo, antes de calcular
    r = falla(s, "sweep", sketch="Perfil", profile=0, path_sketch="Ruta", twist_angle="3601 deg")
    assert r["error_kind"] == "OPERATION_FAILED" and "3600" in r["mensaje"]


def test_create_polygon_admite_hasta_64_lados_como_la_interfaz(s):
    assert api.llamar(s, "create_sketch", {})["ok"]
    antes = foto(s)
    r = falla(s, "create_polygon", sides=65, radius=10)
    assert r["error_kind"] == "INVALID_GEOMETRY" and "64" in r["mensaje"]
    assert foto(s) == antes
    r = falla(s, "sketch_from_spec", entities=[{"type": "polygon", "sides": 65, "radius": 10}])
    assert "64" in r["mensaje"]
    assert api.llamar(s, "create_polygon", {"sides": 64, "radius": 10})["ok"]


def test_patrones_por_api_rechazan_antes_de_crear_nada(s):
    cubo = api.llamar(s, "create_box", {"length": 10, "width": 10, "height": 10})["result"]["bodies_created"][0]["id"]
    antes = foto(s)
    r = falla(s, "circular_pattern", bodies=cubo, count=10_001)
    assert r["error_kind"] == "INVALID_ARGUMENTS" and "10.000" in r["mensaje"]
    r = falla(s, "rectangular_pattern", bodies=cubo, x_count=101, x_spacing=20, y_count=100, y_spacing=20)
    assert r["error_kind"] == "INVALID_ARGUMENTS" and "10.000" in r["mensaje"]
    assert foto(s) == antes
    # run_operation no pasa por la herramienta: lo frena el núcleo
    r = falla(s, "run_operation", type="patron", params={"forma_patron": "circular", "cuerpos": [cubo],
                                                          "eje": {"tipo": "eje", "id": "Z"}, "n": 10_001})
    assert r["error_kind"] == "OPERATION_FAILED" and "10.000" in r["mensaje"]


# ---------------------------------------------------------------- remallado
def _cuadrado(lado=1000.0):
    """Malla plana de 2 triángulos: área lado², aristas de lado y lado·√2 (media = 1,0828·lado)."""
    v = np.array([[0, 0, 0], [lado, 0, 0], [lado, lado, 0], [0, lado, 0]], float)
    return ml.Malla(v, np.array([[0, 1, 2], [0, 2, 3]]))


def test_remallar_rechaza_mas_de_100000_triangulos_antes_de_calcular():
    m = _cuadrado()
    # longitud 4,5 mm → 1.000.000 / (√3/4 · 4,5²) ≈ 114.044 triángulos; con 4,81 mm se llega a 100.000
    with pytest.raises(geo.ErrorGeometria, match=r"unos 114\.044 triángulos y el máximo es 100\.000: "
                                                 r"subí la longitud a 4,81 mm"):
        ml.remallar(m, longitud=4.5, preservar_bordes=False)
    # densidad 60.000 → largo = 1082,8 / √60000 ≈ 4,42 mm → ≈ 118.173 triángulos; tope con densidad 50.700
    with pytest.raises(geo.ErrorGeometria, match=r"unos 118\.173 triángulos y el máximo es 100\.000: "
                                                 r"bajá la densidad a 50\.700 o menos"):
        ml.remallar(m, densidad=60_000, preservar_bordes=False)
    # la misma malla con un largo razonable sigue andando (estimado 231 triángulos)
    r = ml.remallar(m, longitud=100.0, iteraciones=1, preservar_bordes=False)
    assert len(r.caras) == 256 and r.area() == pytest.approx(1e6)


def _grilla(nx, ny):
    """Malla plana de nx × ny cuadrados de 1 mm (2 triángulos cada uno): sus bordes abiertos son aristas de 1 mm."""
    xs, ys = np.meshgrid(np.arange(nx + 1.0), np.arange(ny + 1.0), indexing="ij")
    k = lambda i, j: i * (ny + 1) + j  # noqa: E731
    caras = [c for i in range(nx) for j in range(ny)
             for c in ([k(i, j), k(i + 1, j), k(i + 1, j + 1)], [k(i, j), k(i + 1, j + 1), k(i, j + 1)])]
    return ml.Malla(np.c_[xs.ravel(), ys.ravel(), np.zeros(xs.size)], np.array(caras))


def _sin_calcular(monkeypatch):
    def no(*_a, **_k):
        raise AssertionError("calculó el remallado")
    monkeypatch.setattr(ml, "_remallar_nucleo", no)


def test_remallar_cuenta_los_bordes_fijos_de_menos_de_3_aristas_maximas(monkeypatch):
    """Revisión: con longitud 0,252 una tira de 1200 × 1 mm tiene bordes de n = 1 / (4/3 · 0,252) = 2,98 aristas
    máximas. Por área daba 43.639 (entraba) y el remallado corría 105 s hasta 156.132 triángulos. Ahora el estimado
    suma lo que crecen esos bordes fijos y frena antes de calcular; el consejo da una longitud que sí entra."""
    _sin_calcular(monkeypatch)
    tira = _grilla(1200, 1)
    with pytest.raises(geo.ErrorGeometria, match=r"unos [\d.]+ triángulos y el máximo es 100\.000: con «Preservar "
                                                 r"bordes» .*: desactivalo o subí la longitud a ([\d,]+) mm") as e:
        ml.remallar(tira, longitud=0.252)
    assert e.value.triangulos > 156_132
    sugerida = float(e.value.args[0].split("longitud a ")[1].split(" mm")[0].replace(",", "."))
    bordes = np.ones(2 * 1200 + 2)          # los bordes abiertos de la tira: aristas de 1 mm
    ml._exigir_tamano_remallado(tira.area(), bordes, sugerida, 60, 1.0, sugerida)       # con esa sí entra


def test_remallar_el_estimado_cubre_los_bordes_fijos():
    """Tira de 20 × 1 mm con bordes de n = 2,98: el resultado pasa de largo el estimado por área (1,5 veces o más),
    pero no el estimado con los bordes fijos."""
    tira, largo = _grilla(20, 1), 1 / (4 / 3 * 2.98)
    r = ml.remallar(tira, longitud=largo)
    assert len(r.caras) > 1.5 * ml._estimado_remallado(tira.area(), (), largo, 60)
    assert len(r.caras) <= ml._estimado_remallado(tira.area(), np.ones(42), largo, 60)
    assert r.area() == pytest.approx(20.0, rel=1e-4)     # los abanicos dejan algún triángulo volteado (de antes)


def test_remallar_se_corta_en_el_techo_si_el_estimado_se_queda_corto(monkeypatch):
    """Lo que el estimado no vea lo cortan los techos: el resultado nunca tiene más de TECHO_REMALLADO triángulos y,
    si la cuenta crece a un ritmo que lo pasaría, se corta antes de la última vuelta. Acá el estimado se hace ciego a
    los bordes y los techos se bajan para que la prueba sea rápida."""
    tira, largo = _grilla(20, 1), 1 / (4 / 3 * 2.98)
    solo_area = ml._estimado_remallado(tira.area(), (), largo, 60)
    monkeypatch.setattr(ml, "_excedente_bordes", lambda *_: 0.0)
    monkeypatch.setattr(ml, "TECHO_REMALLADO", int(1.2 * solo_area))
    vueltas = []
    nucleo = ml._remallar_nucleo
    monkeypatch.setattr(ml, "_remallar_nucleo", lambda *a, **k: (vueltas.append(1), nucleo(*a, **k)))
    with pytest.raises(geo.ErrorGeometria, match=r"se cortó en la vuelta [2-4] de 5 con [\d.]+ triángulos: crece más "
                                                 r"de lo estimado .*Preservar bordes"):
        ml.remallar(tira, longitud=largo)
    assert len(vueltas) < 5                 # no terminó las 5 vueltas para descubrirlo
    # sin preservar bordes el borde se divide como cualquier arista: el estimado por área vale y entra en el techo
    r = ml.remallar(tira, longitud=largo, preservar_bordes=False)
    assert len(r.caras) <= ml.TECHO_REMALLADO and r.area() == pytest.approx(20.0)
    # y en medio de una vuelta la división no pasa de TECHO_TRANSITORIO (la memoria): se mira en cada ronda
    monkeypatch.setattr(ml, "TECHO_TRANSITORIO", 300)
    with pytest.raises(geo.ErrorGeometria, match=r"se cortó en la vuelta 1 de 5 con [\d.]+ triángulos"):
        ml.remallar(tira, longitud=largo, preservar_bordes=False)


def test_remallar_proyecta_bien_sobre_las_astillas_de_un_teselado():
    """Un cilindro teselado tiene triángulos de 100 mm de largo y 2 de ancho: proyectando sobre el triángulo de centro
    más cercano (no sobre el más cercano) el remallado terminaba con 1,9 a 2,2 veces lo estimado (longitud 4 a 2,5;
    con longitud 1, 5,3 veces en 195 s)."""
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeCylinder
    cil = ml.desde_brep(BRepPrimAPI_MakeCylinder(20.0, 100.0).Shape())
    r = ml.remallar(cil, longitud=5.0)
    assert len(r.caras) <= 1.2 * ml._estimado_remallado(cil.area(), (), 5.0, 60)
    assert r.es_cerrada() and r.volumen() == pytest.approx(cil.volumen(), rel=1e-2)


def _esfera(nlat=20, nlon=30, radio=50.0):
    """Malla cerrada de 2·nlon·(nlat − 1) triángulos (latitud y longitud)."""
    th = np.linspace(0, np.pi, nlat + 1)[1:-1]
    ph = np.linspace(0, 2 * np.pi, nlon, endpoint=False)
    T, P = np.meshgrid(th, ph, indexing="ij")
    v = np.c_[np.sin(T).ravel() * np.cos(P).ravel(), np.sin(T).ravel() * np.sin(P).ravel(), np.cos(T).ravel()]
    v = np.vstack([[0, 0, 1], v, [0, 0, -1]]) * radio
    sur = len(v) - 1
    k = lambda i, j: 1 + i * nlon + j % nlon  # noqa: E731
    caras = [[0, k(0, j), k(0, j + 1)] for j in range(nlon)] + [[sur, k(nlat - 2, j + 1), k(nlat - 2, j)]
                                                                for j in range(nlon)]
    for i in range(nlat - 2):
        for j in range(nlon):
            caras += [[k(i, j), k(i + 1, j), k(i, j + 1)], [k(i, j + 1), k(i + 1, j), k(i + 1, j + 1)]]
    return ml.Malla(v, np.array(caras))


def test_reparar_reconstruir_pide_reducir_y_no_una_densidad_que_no_tiene(monkeypatch):
    """Reparar › Reconstruir remalla con densidad 1 fija (el paso no tiene densidad): el consejo es reducir."""
    m = _esfera()
    assert m.es_cerrada() and len(m.caras) == 1140
    monkeypatch.setattr(ml, "TRIANGULOS_MAXIMOS_REMALLADO", 300)
    with pytest.raises(geo.ErrorGeometria, match=r"Reconstruir daría unos [\d.]+ triángulos y el máximo es 300: "
                                                 r"reducí antes la malla \(Modificar › Reducir\) a unos [\d.,]+ "
                                                 r"triángulos o menos\.") as e:
        ml.reparar(m, tipo="reconstruir")
    assert "densidad" not in str(e.value)
    with pytest.raises(geo.ErrorGeometria, match="bajá la densidad"):      # Remallar sí la tiene
        ml.remallar(m)


@pytest.mark.parametrize("args", [{"densidad": math.nan}, {"densidad": math.inf}, {"longitud": math.nan},
                                  {"longitud": math.inf}, {"densidad": 0}, {"longitud": -1}])
def test_remallar_rechaza_densidad_o_longitud_no_finitas(args):
    with pytest.raises(geo.ErrorGeometria, match="finitas"):
        ml.remallar(_cuadrado(), **args)


# ---------------------------------------------------------------- pico de la división (astillas de un teselado)
def _cilindro(radio, alto):
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeCylinder
    return ml.desde_brep(BRepPrimAPI_MakeCylinder(float(radio), float(alto)).Shape())


@pytest.mark.parametrize("caso", ["cilindro", "tira"])
def test_remallar_simula_la_division_de_la_primera_vuelta(monkeypatch, caso):
    """_pico_division da las caras que deja la división de la 1.ª vuelta igual que el editor (con y sin bordes
    fijos), sin calcular el remallado."""
    if caso == "cilindro":
        m, largo = _cilindro(20, 100), 5.0
        fijas = np.zeros((len(m.caras), 3), bool)
    else:
        m, largo = _grilla(20, 1), 1 / (4 / 3 * 2.98)
        topo = ml._Topo(m.caras, len(m.vertices))
        fijas = (topo.cuenta[topo.inv] == 1).reshape(-1, 3)
    assert len(fijas) == len(m.caras)
    picos = [0]
    aristas = ml._Editor.aristas

    def espia(ed):
        picos[0] = max(picos[0], len(ed.c) - ed.viva.count(False))
        return aristas(ed)
    monkeypatch.setattr(ml._Editor, "aristas", espia)
    ml.remallar(m, longitud=largo, iteraciones=1)
    simulado = ml._pico_division(m.vertices[m.caras], fijas, 4 / 3 * largo, ml._RONDAS_DIVISION, 10**7)
    assert simulado == picos[0] and simulado > 2 * len(m.caras)


def test_remallar_frena_las_astillas_de_un_teselado_antes_de_calcular(monkeypatch):
    """Revisión: en un teselado CAD (triángulos de 300 × 0,3 mm) la 1.ª vuelta divide mucho más que el resultado
    y es lo que tarda: barra R5 × 300 con densidad 1000, 393.928 caras al dividir y 49,8 s; cilindro R20 × 100 con
    densidad 4000, 494.560 y 106 s. El estimado del resultado entraba (2.129 y 94.978). Ahora frena antes."""
    _sin_calcular(monkeypatch)
    barra = _cilindro(5, 300)
    assert ml._estimado_remallado(barra.area(), (), 2.0, 60) < 10_000         # el resultado entraría de sobra
    with pytest.raises(geo.ErrorGeometria, match=r"pasaría de 150\.000 triángulos \(el máximo\) al dividir las "
                                                 r"aristas largas .*: subí la longitud a ([\d,]+) mm o más") as e:
        ml.remallar(barra, longitud=2.0)
    sugerida = float(e.value.args[0].split("longitud a ")[1].split(" mm")[0].replace(",", "."))
    tris, fijas = barra.vertices[barra.caras], np.zeros((len(barra.caras), 3), bool)
    assert ml._pico_division(tris, fijas, 4 / 3 * sugerida, 12, 10**7) <= ml.PICO_MAXIMO_REMALLADO
    with pytest.raises(geo.ErrorGeometria, match=r"pasaría de 150\.000 .*: bajá la densidad a [\d.,]+ o menos"):
        ml.remallar(barra, densidad=1000)
    # una malla grande que no crece no se frena por el pico (cuenta como máximo su propia cantidad de caras)
    monkeypatch.setattr(ml, "PICO_MAXIMO_REMALLADO", 10)
    with pytest.raises(AssertionError, match="calculó"):
        ml.remallar(barra, longitud=400.0)


def test_reparar_reconstruir_con_astillas_pide_reducir(monkeypatch):
    m = _esfera()
    monkeypatch.setattr(ml, "PICO_MAXIMO_REMALLADO", 0)          # el tope queda en las caras de la malla: 1140
    _sin_calcular(monkeypatch)
    with pytest.raises(geo.ErrorGeometria, match=r"Reconstruir pasaría de 1\.140 triángulos \(el máximo\) al dividir "
                                                 r"las aristas largas .*: reducí antes la malla") as e:
        ml.reparar(m, tipo="reconstruir")
    assert "densidad" not in str(e.value)

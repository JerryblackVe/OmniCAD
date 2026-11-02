# -*- coding: utf-8 -*-
"""RI-2: de una malla a una pieza con timeline, con el juez como árbitro. Cada pieza se arma con la API, se tesela, se
reconstruye y se mide contra la respuesta conocida."""
import math

import numpy as np
import pytest

from omnicad import api
from omnicad.nucleo import comparar_malla as cm
from omnicad.nucleo import geometria as geo
from omnicad.nucleo import malla as ml
from omnicad.nucleo import reconstruir_malla as rm


def _ok(s, nombre, **a):
    r = api.llamar(s, nombre, a)
    assert r["ok"], (nombre, r)
    return r["result"]


def _malla(*pasos):
    """Sesión nueva con solo la malla de la pieza que arman `pasos`, para partir como de un STL."""
    origen = api.Sesion()
    for nombre, args in pasos:
        _ok(origen, nombre, **args)
    forma = next(iter(origen.doc.estado_final.cuerpos.values())).forma
    return forma, ml.desde_brep(forma, refinamiento="personalizado", desviacion=0.02, angulo=15)


def _insertar(tmp_path, m):
    ruta = tmp_path / "pieza.stl"
    ml.escribir(m, str(ruta))
    s = api.Sesion()
    return s, _ok(s, "insert_file", path=str(ruta))["new_bodies"][0]


def _reconstruir(tmp_path, *pasos, tolerancia=0.1):
    forma, m = _malla(*pasos)
    s, malla = _insertar(tmp_path, m)
    r = _ok(s, "reconstruct_from_mesh", body=malla, tolerance=tolerancia)
    nuevo = s.doc.estado_final.cuerpos[r["body"]].forma
    assert geo.es_valida(nuevo) and r["valid"]
    assert not [o.id for o, x in zip(s.doc.operaciones, s.doc.resultados, strict=True) if x.estado == "error"]
    return s, r, forma, nuevo


def _sin_errores(s, tmp_path):
    ruta = tmp_path / "pieza.omnicad"
    s.guardar(str(ruta), sobrescribir=True)
    otra = api.Sesion()
    otra.abrir(str(ruta))
    _ok(otra, "recompute_all")
    assert not [x for x in otra.doc.resultados if x.estado == "error"]
    return otra


CAJA = ("create_box", dict(length=60, width=40, height=20))
PERFIL_L = ("sketch_from_spec", dict(plane="XY", entities=[
    {"type": "line", "start": a, "end": b} for a, b in
    (([0, 0], [50, 0]), ([50, 0], [50, 12]), ([50, 12], [15, 12]), ([15, 12], [15, 35]), ([15, 35], [0, 35]), ([0, 35], [0, 0]))]))


def test_un_bloque_vuelve_como_boceto_y_extrusion(tmp_path):
    s, r, forma, nuevo = _reconstruir(tmp_path, CAJA)
    assert r["tolerance_met"] is True and r["max_deviation"] <= 0.1 / 20      # el juez deja de buscar a tol / 20
    assert r["faces"] == 6 and geo.volumen(nuevo) == pytest.approx(geo.volumen(forma), rel=1e-6)
    assert [o.TIPO for o in s.doc.operaciones[1:]] == ["boceto", "extrusion"]


def test_perfil_en_L(tmp_path):
    _s, r, forma, nuevo = _reconstruir(tmp_path, PERFIL_L, ("extrude", dict(sketch="op1", profile=0, distance=30)))
    assert r["faces"] == 8 and geo.volumen(nuevo) == pytest.approx(geo.volumen(forma), rel=1e-5)


def test_agujeros_con_su_paso_y_su_patron(tmp_path):
    s, r, forma, nuevo = _reconstruir(
        tmp_path, ("create_box", dict(length=90, width=70, height=6)),
        ("create_hole", dict(face=">Z", diameter=5, through_all=True, points=[[x, y, 6] for x in (-30, -10, 10, 30) for y in (-20, 0, 20)])))
    tipos = [o.TIPO for o in s.doc.operaciones]
    assert tipos.count("agujero") == 1 and any("patron" in t for t in tipos)
    assert r["faces"] == 18 and r["max_deviation"] <= 0.1
    assert geo.volumen(nuevo) == pytest.approx(geo.volumen(forma), rel=1e-3)


def test_eje_escalonado_sale_de_una_revolucion(tmp_path):
    puntos = [[0, 0], [20, 0], [20, 15], [12, 15], [12, 45], [8, 45], [8, 70], [0, 70]]
    ents = [{"type": "line", "start": a, "end": b} for a, b in zip(puntos, puntos[1:] + puntos[:1], strict=True)]
    s, r, forma, nuevo = _reconstruir(tmp_path, ("sketch_from_spec", dict(plane="XZ", entities=ents)),
                                      ("revolve", dict(sketch="op1", profile=0, axis="z", angle=360)))
    assert r["strategy"] == "revolve" and r["faces"] == 7
    assert sum(o.TIPO == "revolucion" for o in s.doc.operaciones) == 1
    assert geo.volumen(nuevo) == pytest.approx(geo.volumen(forma), rel=2e-3)


def test_empalme_y_chaflan_con_su_paso(tmp_path):
    s, r, _forma, _nuevo = _reconstruir(tmp_path, CAJA, ("fillet", dict(edges=">Z", radius=3)))
    assert any(o.TIPO in ("empalme",) for o in s.doc.operaciones) and r["faces"] <= 15 and r["max_deviation"] <= 0.1
    s, r, _forma, _nuevo = _reconstruir(tmp_path, CAJA, ("chamfer", dict(edges=">Z", distance=2)))
    assert any("chafl" in o.TIPO for o in s.doc.operaciones) and r["max_deviation"] <= 0.1


def test_esquinas_redondeadas_salen_en_el_perfil_con_pocas_caras(tmp_path):
    """El corte pasa por las diagonales de las facetas: sin limpiar, cada empalme eran muchos tramos rectos."""
    s, r, forma, nuevo = _reconstruir(tmp_path, CAJA, ("fillet", dict(edges="|Z", radius=6)))
    assert r["faces"] == 10 and [o.TIPO for o in s.doc.operaciones[1:]] == ["boceto", "extrusion"]
    assert geo.volumen(nuevo) == pytest.approx(geo.volumen(forma), rel=1e-3)


def test_patron_circular_con_su_eje(tmp_path):
    s, r, _forma, _nuevo = _reconstruir(
        tmp_path, ("create_cylinder", dict(diameter=80, height=10)),
        ("create_hole", dict(face=">Z", diameter=8, through_all=True, points=[[28, 0, 10]])),
        ("circular_pattern", dict(features=["op2"], count=6, axis="z", total_angle=360)))
    assert r["unrecovered"] == [] and r["faces"] == 9 and r["max_deviation"] <= 0.1
    assert any("patron" in o.TIPO for o in s.doc.operaciones)


def test_regiones_de_igual_area_en_una_capa(tmp_path):
    """Cuatro topes iguales sobre una placa: dos regiones iguales no pueden tomar el mismo perfil del boceto."""
    pasos = [("create_box", dict(length=100, width=60, height=6))]
    for x, y in ((-30, -15), (30, -15), (-30, 15), (30, 15)):
        pasos.append(("create_box", dict(length=15, width=12, height=10, x=x, y=y, z=6, operation="join")))
    s, r, forma, nuevo = _reconstruir(tmp_path, *pasos)
    assert sum(o.TIPO == "extrusion" for o in s.doc.operaciones) == 2 and r["faces"] == 26
    assert geo.volumen(nuevo) == pytest.approx(geo.volumen(forma), rel=1e-3)


def test_dos_agujeros_que_se_cruzan(tmp_path):
    """El del costado queda partido en dos cilindros del mismo diámetro: sigue siendo un solo agujero."""
    s, r, _forma, _nuevo = _reconstruir(tmp_path, ("create_box", dict(length=50, width=40, height=30)),
                                        ("create_hole", dict(face=">Z", diameter=10, through_all=True, points=[[0, 0, 30]])),
                                        ("create_hole", dict(face=">X", diameter=8, through_all=True, points=[[25, 0, 15]])))
    assert sum(o.TIPO == "agujero" for o in s.doc.operaciones) == 2 and r["unrecovered"] == [] and r["faces"] == 9


def test_el_ajuste_a_un_circulo_no_confunde_las_esquinas_de_un_rectangulo():
    P = np.array([[10.0, 0], [0, 10], [-10, 0], [0, -10]])
    assert [c["tipo"] for c in rm._crudas(P, True, 0.05, [(np.zeros(2), 10.0)])] == ["linea"] * 4


def test_puntos_que_no_doblan_se_van():
    P = np.array([[0, 0], [5, 0], [10, 0], [10, 10], [0, 10.0]])
    assert len(rm._sin_colineales(P, True)) == 4


def test_pieza_girada_termina_con_un_paso_mover(tmp_path):
    s, r, forma, nuevo = _reconstruir(tmp_path, PERFIL_L, ("extrude", dict(sketch="op1", profile=0, distance=30)),
                                      ("move_body", dict(body="op2.c1", rotate=[20, 0, 30], pivot="origin")))
    assert r["tolerance_met"] is True and s.doc.operaciones[-1].TIPO in ("mover",)
    caja, esperada = geo.caja_envolvente(nuevo), geo.caja_envolvente(forma)
    assert np.array(caja[0]) == pytest.approx(np.array(esperada[0]), abs=0.05)


def test_es_un_solo_deshacer_y_la_malla_queda_oculta(tmp_path):
    forma, m = _malla(CAJA)
    s, malla = _insertar(tmp_path, m)
    antes = len(s.doc.operaciones)
    r = _ok(s, "reconstruct_from_mesh", body=malla)
    assert malla in s.doc.propiedad("__navegador__", "ocultos", []) and r["mesh_hidden"] == malla
    _ok(s, "undo")
    assert len(s.doc.operaciones) == antes and malla not in s.doc.propiedad("__navegador__", "ocultos", [])
    _ok(s, "redo")
    assert len(s.doc.operaciones) > antes


def test_lo_reconstruido_se_guarda_se_abre_se_edita_y_recalcula(tmp_path):
    s, _r, _forma, nuevo = _reconstruir(tmp_path, CAJA)
    otra = _sin_errores(s, tmp_path)
    extrusion = next(o for o in otra.doc.operaciones if o.TIPO == "extrusion")
    _ok(otra, "edit_feature", feature=extrusion.id, params={"distancia": "30 mm"})
    cuerpo = next(c for c in otra.doc.estado_final.cuerpos.values() if getattr(c, "tipo", "") != "malla")
    assert geo.volumen(cuerpo.forma) == pytest.approx(geo.volumen(nuevo) * 1.5, rel=1e-6)


def test_la_vuelta_de_correccion_se_corta_sola_si_no_mejora(tmp_path):
    """Un agujero oblicuo no entra en la pila de capas: la vuelta prueba, no mejora y se detiene sin colgarse."""
    s, r, _forma, _nuevo = _reconstruir(tmp_path, ("create_sphere", dict(radius=20)),
                                        ("create_box", dict(length=4, width=4, height=60, z=-30, operation="cut")))
    assert len(r["iterations"]) <= 3
    if r["iterations"]:
        assert r["iterations"][-1]["applied"] == 0 or r["tolerance_met"]


def test_informa_lo_que_no_recupera_sin_fingir(tmp_path):
    u, v = np.meshgrid(np.linspace(0, 2 * math.pi, 40), np.linspace(0.3, math.pi - 0.3, 20))
    rr = 20 + 2 * np.sin(4 * u) * np.sin(3 * v)
    V = np.c_[(rr * np.sin(v) * np.cos(u)).ravel(), (rr * np.sin(v) * np.sin(u)).ravel(), (rr * np.cos(v)).ravel()]
    i = np.arange(19 * 40).reshape(19, 40)[:, :39].ravel()
    m = ml.Malla(V, np.r_[np.c_[i, i + 1, i + 40], np.c_[i + 1, i + 41, i + 40]])
    s, malla = _insertar(tmp_path, m)
    r = api.llamar(s, "reconstruct_from_mesh", {"body": malla})
    if r["ok"]:
        assert r["result"]["tolerance_met"] is False and r["result"]["unrecovered"]
    else:
        assert r["error_kind"] == "OPERATION_FAILED" and len(s.doc.operaciones) == 1


@pytest.mark.parametrize("args", [{"tolerance": 0}, {"tolerance": -1}, {"max_iterations": 11}])
def test_parametros_invalidos(tmp_path, args):
    _forma, m = _malla(CAJA)
    s, malla = _insertar(tmp_path, m)
    assert api.llamar(s, "reconstruct_from_mesh", {"body": malla, **args})["error_kind"] == "INVALID_ARGUMENTS"
    assert len(s.doc.operaciones) == 1


def test_un_solido_no_es_una_malla():
    s = api.Sesion()
    _ok(s, *CAJA[:1], **CAJA[1])
    assert api.llamar(s, "reconstruct_from_mesh", {"body": "op1.c1"})["error_kind"] == "UNSUPPORTED_BODY_TYPE"


def test_malla_con_unidades_raras(tmp_path):
    """Un STL en pulgadas: mesh_units lo pasa a mm antes de medir."""
    _forma, m = _malla(CAJA)
    ruta = tmp_path / "pulgadas.stl"
    ml.escribir(ml.Malla(m.vertices / 25.4, m.caras), str(ruta))
    s = api.Sesion()
    malla = _ok(s, "insert_file", path=str(ruta), mesh_units="in")["new_bodies"][0]
    r = _ok(s, "reconstruct_from_mesh", body=malla)
    assert r["tolerance_met"] is True and r["faces"] == 6


def test_una_malla_con_ruido_vuelve_a_ser_la_pieza(tmp_path):
    forma, m = _malla(CAJA, ("create_hole", dict(face=">Z", diameter=12, through_all=True, points=[[0, 0, 20]])))
    m = ml.refinar_triangulos(m, longitud_maxima=4.0)
    rng = np.random.default_rng(1)
    s, malla = _insertar(tmp_path, ml.Malla(m.vertices + rng.normal(0, 0.01, m.vertices.shape), m.caras))
    r = _ok(s, "reconstruct_from_mesh", body=malla, tolerance=0.1)
    nuevo = s.doc.estado_final.cuerpos[r["body"]].forma
    assert r["quality"] == "scan" and r["faces"] == 7 and r["max_deviation"] <= 0.1
    assert geo.volumen(nuevo) == pytest.approx(geo.volumen(forma), rel=5e-3)


def test_malla_abierta_se_repara_para_medir_y_avisa(tmp_path):
    _forma, m = _malla(CAJA)
    s, malla = _insertar(tmp_path, ml.Malla(m.vertices, m.caras[2:]))
    r = _ok(s, "reconstruct_from_mesh", body=malla)
    assert r["valid"] is True and any("cerrada" in x for x in r["unrecovered"])


def test_malla_sucia_con_caras_repetidas_y_degeneradas(tmp_path):
    _forma, m = _malla(CAJA)
    i = m.caras[0, 0]
    s, malla = _insertar(tmp_path, ml.Malla(m.vertices, np.r_[m.caras, m.caras[:4], [[i, i, m.caras[0, 1]]]]))
    r = _ok(s, "reconstruct_from_mesh", body=malla)
    assert r["valid"] is True and r["max_deviation"] <= 0.1 and r["faces"] == 6


def test_malla_vacia_y_enorme_dan_mensaje_claro(tmp_path, monkeypatch):
    _forma, m = _malla(CAJA)
    s, malla = _insertar(tmp_path, m)
    monkeypatch.setattr(cm, "TOPE_TRIANGULOS", 3)
    r = api.llamar(s, "reconstruct_from_mesh", {"body": malla})
    assert r["ok"] is False and "reduce_mesh" in r["mensaje"] and len(s.doc.operaciones) == 1
    monkeypatch.undo()
    s.doc.estado_final.cuerpos[malla].forma = ml.Malla(np.zeros((0, 3)), np.zeros((0, 3), int))
    r = api.llamar(s, "reconstruct_from_mesh", {"body": malla})
    assert r["ok"] is False and "vacía" in r["mensaje"]


def test_giros_de_mover_al_derecho_y_en_el_polo():
    for rx, ry, rz in ((20, 0, 30), (0, 90, 0), (10, -90, 0), (-35, 50, 120)):
        c, s = np.cos(np.radians([rx, ry, rz])), np.sin(np.radians([rx, ry, rz]))
        R = (np.array([[c[2], -s[2], 0], [s[2], c[2], 0], [0, 0, 1]]) @ np.array([[c[1], 0, s[1]], [0, 1, 0], [-s[1], 0, c[1]]])
             @ np.array([[1, 0, 0], [0, c[0], -s[0]], [0, s[0], c[0]]]))
        a, b, g = np.radians(rm.angulos(R))
        ca, sa, cb, sb, cg, sg = np.cos(a), np.sin(a), np.cos(b), np.sin(b), np.cos(g), np.sin(g)
        Q = (np.array([[cg, -sg, 0], [sg, cg, 0], [0, 0, 1]]) @ np.array([[cb, 0, sb], [0, 1, 0], [-sb, 0, cb]])
             @ np.array([[1, 0, 0], [0, ca, -sa], [0, sa, ca]]))
        assert Q == pytest.approx(R, abs=1e-6)


def test_estrategia_y_regiones_puras():
    cuadrado = lambda lado, x=0.0: (np.array([[x, x], [x + lado, x], [x + lado, x + lado], [x, x + lado]]), lado ** 2)  # noqa: E731
    regs = rm.regiones([cuadrado(10.0), cuadrado(6.0, 2.0), cuadrado(2.0, 4.0), cuadrado(3.0, 20.0)])
    assert len(regs) == 3
    externa = regs[0]
    assert len(externa["holes"]) == 1 and externa["area"] == pytest.approx(64.0)
    assert sorted(r["area"] for r in regs) == pytest.approx([4.0, 9.0, 64.0])

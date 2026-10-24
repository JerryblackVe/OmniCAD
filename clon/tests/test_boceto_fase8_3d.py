# -*- coding: utf-8 -*-
"""Boceto 3D (FU-1, «3D Sketch» de Fusion): línea, spline y punto fuera del plano del boceto, bloqueo de eje y de
plano (la tríada), restricciones y cotas 3D con su solver, ruta de barrido, API (MCP/CLI) y guardar/abrir."""
import math

import numpy as np
import pytest

from omnicad import api
from omnicad.nucleo import geometria as geo
from omnicad.restricciones import Boceto
from omnicad.restricciones import boceto3d as b3
from omnicad.restricciones.boceto import ErrorBoceto
from omnicad.timeline import entidades as ent
from omnicad.timeline.documento import Documento
from omnicad.timeline.operaciones import OpBoceto


def _coords(b, pid):
    return np.array(b.geo3d["puntos"][pid], float)


def _pts(b, cid):
    return b.geo3d["curvas"][cid]["puntos"]


# ---------------------------------------------------------------- núcleo: geometría y serialización
def test_linea_y_spline_encadenadas_comparten_el_extremo():
    b = Boceto()
    linea = b3.agregar_linea(b, (0, 0, 0), (0, 0, 20))
    spline = b3.agregar_spline(b, [(0, 0, 20), (10, 5, 35), (20, 20, 40)])
    assert _pts(b, linea)[1] == _pts(b, spline)[0]
    assert len(b.geo3d["puntos"]) == 4
    assert b.curvas == {} and b.puntos == {}          # la parte 2D del boceto no se toca


def test_ids_compartidos_con_el_boceto_2d_y_round_trip():
    b = Boceto()
    b.agregar_linea((0, 0), (10, 0))
    linea = b3.agregar_linea(b, (0, 0, 0), (5, 5, 5))
    k = b3.agregar_cota(b, [linea], "12 mm")
    assert linea not in b.curvas and linea not in b.puntos         # un solo espacio de ids
    d = Boceto.desde_dict(b.a_dict())
    assert d.a_dict() == b.a_dict()
    assert d.geo3d["cotas"][k]["expresion"] == "12 mm"
    nuevo = d.agregar_linea((0, 5), (10, 5))
    assert nuevo > max(b.geo3d["puntos"]) and nuevo > k             # los ids 3D no se reusan al abrir


def test_copia_independiente():
    b = Boceto()
    linea = b3.agregar_linea(b, (0, 0, 0), (5, 5, 5))
    c = b.copia()
    c.geo3d["puntos"][_pts(c, linea)[1]][2] = 99.0
    assert _coords(b, _pts(b, linea)[1])[2] == 5.0


def test_entradas_invalidas_del_nucleo():
    b = Boceto()
    with pytest.raises(ErrorBoceto):
        b3.agregar_linea(b, (0, 0, 0), (0, 0, 0))
    with pytest.raises(ErrorBoceto):
        b3.agregar_spline(b, [(0, 0, 0)])
    with pytest.raises(ErrorBoceto):
        b3.agregar_linea(b, (0, 0, float("nan")), (1, 1, 1))
    linea = b3.agregar_linea(b, (0, 0, 0), (5, 0, 0))
    punto = b3.agregar_punto(b, (3, 3, 3))
    with pytest.raises(ErrorBoceto):
        b3.agregar_restriccion(b, "paralela", [linea, punto])
    with pytest.raises(ErrorBoceto):
        b3.agregar_restriccion(b, "eje", [linea], eje="w")
    with pytest.raises(ErrorBoceto):
        b3.agregar_restriccion(b, "coincidente", [linea, 999])
    suelta = b3.agregar_spline(b, [(10, 10, 10), (12, 11, 15), (14, 15, 16)])
    with pytest.raises(ErrorBoceto, match="extremo"):
        b3.agregar_restriccion(b, "tangente", [linea, suelta])
    with pytest.raises(ErrorBoceto):
        b3.agregar_cota(b, [punto], "5")


# ---------------------------------------------------------------- solver 3D
def test_eje_y_cota_de_distancia_3d():
    b = Boceto()
    linea = b3.agregar_linea(b, (0, 0, 0), (1, 2, 18))
    p1, p2 = _pts(b, linea)
    b3.agregar_restriccion(b, "fijo", [p1])
    b3.agregar_restriccion(b, "eje", [linea], eje="z")
    k = b3.agregar_cota(b, [linea], "20")
    r = b3.resolver(b, {k: 20.0})
    assert r.ok and r.gdl == 0
    assert np.allclose(_coords(b, p2), (0, 0, 20), atol=1e-6)


def test_paralela_perpendicular_coincidente_igual_y_punto_medio():
    b = Boceto()
    l1 = b3.agregar_linea(b, (0, 0, 0), (10, 0, 0))
    b3.agregar_restriccion(b, "fijo", [l1])
    l2 = b3.agregar_linea(b, (3, 4, 5), (9, 1, 7))
    b3.agregar_restriccion(b, "paralela", [l1, l2])
    b3.agregar_restriccion(b, "igual", [l1, l2])
    l3 = b3.agregar_linea(b, (11, 1, 1), (12, 3, 6))
    b3.agregar_restriccion(b, "coincidente", [_pts(b, l3)[0], _pts(b, l1)[1]])
    b3.agregar_restriccion(b, "perpendicular", [l1, l3])
    medio = b3.agregar_punto(b, (4, 1, 1))
    b3.agregar_restriccion(b, "punto_medio", [medio, l1])
    sobre = b3.agregar_punto(b, (7, 2, -1))
    b3.agregar_restriccion(b, "coincidente", [sobre, l1])
    r = b3.resolver(b, {})
    assert r.ok, r.mensaje
    a, c = _coords(b, _pts(b, l2)[0]), _coords(b, _pts(b, l2)[1])
    assert np.allclose(np.cross(c - a, (1, 0, 0)), 0, atol=1e-6)
    assert math.isclose(np.linalg.norm(c - a), 10, abs_tol=1e-6)
    s, e = _coords(b, _pts(b, l3)[0]), _coords(b, _pts(b, l3)[1])
    assert np.allclose(s, (10, 0, 0), atol=1e-6) and abs(float(np.dot(e - s, (1, 0, 0)))) < 1e-6
    assert np.allclose(_coords(b, medio), (5, 0, 0), atol=1e-6)
    assert abs(_coords(b, sobre)[1]) < 1e-6 and abs(_coords(b, sobre)[2]) < 1e-6
    assert np.allclose(_coords(b, _pts(b, l1)[1]), (10, 0, 0))        # lo fijo no se mueve


def test_cotas_en_conflicto_no_mueven_nada():
    b = Boceto()
    linea = b3.agregar_linea(b, (0, 0, 0), (3, 4, 0))
    k1, k2 = b3.agregar_cota(b, [linea], "10"), b3.agregar_cota(b, [linea], "20")
    antes = {k: list(v) for k, v in b.geo3d["puntos"].items()}
    r = b3.resolver(b, {k1: 10.0, k2: 20.0})
    assert not r.ok and "conflicto" in r.mensaje
    assert b.geo3d["puntos"] == antes


def test_spline_tangente_a_la_linea():
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    from OCP.gp import gp_Pnt, gp_Vec
    b = Boceto()
    linea = b3.agregar_linea(b, (0, 0, 0), (0, 0, 20))
    spline = b3.agregar_spline(b, [(0, 0, 20), (10, 5, 35), (20, 20, 40)])

    def tangente_inicio():
        c = BRepAdaptor_Curve(b3.arista(b, spline, geo.Plano("XY")))
        p, v = gp_Pnt(), gp_Vec()
        c.D1(c.FirstParameter(), p, v)
        return np.array([v.X(), v.Y(), v.Z()]) / v.Magnitude()

    assert tangente_inicio()[2] < 0.99                                # sin la restricción no sale derecha
    b3.agregar_restriccion(b, "tangente", [linea, spline])
    assert np.allclose(tangente_inicio(), (0, 0, 1), atol=1e-6)


# ---------------------------------------------------------------- timeline: el paso de boceto y su referencia
def test_paso_boceto_resuelve_3d_y_la_curva_sirve_de_referencia():
    doc = Documento()
    b = Boceto()
    linea = b3.agregar_linea(b, (1, 2, 0), (1, 2, 1))
    b3.agregar_restriccion(b, "fijo", [_pts(b, linea)[0]])
    b3.agregar_restriccion(b, "eje", [linea], eje="z")
    b3.agregar_cota(b, [linea], "largo")
    doc.parametros.agregar("largo", "25 mm")
    doc.agregar(OpBoceto(doc.nuevo_id(), "Ruta", plano="XZ", boceto=b))
    br = doc.estado_final.bocetos["op1"]
    assert br.solver3d.ok
    e = ent.resolver({"tipo": "curva_boceto", "boceto": "op1", "curva": linea}, doc.estado_final)
    assert math.isclose(geo.longitud(e.forma), 25, rel_tol=1e-9)
    plano = geo.Plano("XZ")
    esperado = plano.a_3d(1, 2) + 0 * plano.normal                   # z local = a lo largo de la normal del plano
    assert np.allclose(e.eje[0], esperado) and np.allclose(abs(e.eje[1]), abs(plano.normal))
    doc.parametros.modificar("largo", "40 mm")
    doc.recalcular()
    e = ent.resolver({"tipo": "curva_boceto", "boceto": "op1", "curva": linea}, doc.estado_final)
    assert math.isclose(geo.longitud(e.forma), 40, rel_tol=1e-9)    # la cota sigue al parámetro


# ---------------------------------------------------------------- API (MCP / CLI)
@pytest.fixture
def s():
    return api.Sesion()


def ok(r):
    assert r["ok"], r
    return r["result"]


def llamar(sesion, nombre, **args):
    return ok(api.llamar(sesion, nombre, args))


def falla(sesion, nombre, kind, **args):
    r = api.llamar(sesion, nombre, args)
    assert not r["ok"] and r["error_kind"] == kind, r
    return r


def _tubo(s):
    """Ruta 3D: línea a lo largo de Z y spline tangente; perfil: círculo de radio 2 en XY. Devuelve (ids, volumen)."""
    llamar(s, "create_sketch", plane="XY", name="Ruta")
    linea = llamar(s, "draw_line_3d", start=[0, 0, 0], axis="z", length=20)["entity"]
    spline = llamar(s, "draw_spline_3d", points=[[0, 0, 20], [10, 5, 35], [20, 20, 40]])["entity"]
    llamar(s, "add_constraint_3d", type="tangent", entities=[linea, spline])
    llamar(s, "create_sketch", plane="XY", name="Perfil")
    llamar(s, "draw_circle", center_x=0, center_y=0, radius=2)
    llamar(s, "sweep", sketch="Perfil", profile=0, path_sketch="Ruta")
    cuerpos = list(s.doc.estado_final.cuerpos.values())
    assert len(cuerpos) == 1
    return linea, spline, geo.volumen(cuerpos[0].forma)


def test_barrido_por_ruta_3d_da_el_volumen_del_tubo(s):
    linea, spline, volumen = _tubo(s)
    info = llamar(s, "get_sketch", sketch="Ruta")
    largos = {e["id"]: e["length"] for e in info["entities_3d"]}
    assert largos[linea] == 20
    esperado = math.pi * 2 ** 2 * (largos[linea] + largos[spline])  # Pappus: área × largo de la ruta
    assert volumen == pytest.approx(esperado, rel=1e-2)


def test_barrido_recto_fuera_del_plano_es_exacto(s):
    llamar(s, "create_sketch", plane="XY", name="Ruta")
    r = llamar(s, "draw_line_3d", start=[0, 0, 0], end=[0, 0, 30])
    llamar(s, "create_sketch", plane="XY", name="Perfil")
    llamar(s, "draw_circle", center_x=0, center_y=0, radius=2)
    llamar(s, "sweep", sketch="Perfil", profile=0, path_sketch="Ruta", path_curves=[r["entity"]])
    (c,) = s.doc.estado_final.cuerpos.values()
    assert geo.volumen(c.forma) == pytest.approx(math.pi * 4 * 30, rel=1e-6)


def test_get_sketch_devuelve_el_boceto_3d(s):
    llamar(s, "create_sketch", plane="XY")
    r = llamar(s, "draw_line_3d", start=[1, 2, 3], axis="x", length=-4)
    assert r["constraints"] and r["status_3d"] == "under_constrained"
    p = llamar(s, "draw_point_3d", x=7, y=8, z=9)["point"]
    info = llamar(s, "get_sketch")
    (linea,) = info["entities_3d"]
    assert linea["type"] == "line" and linea["start"] == [1, 2, 3] and linea["end"] == [-3, 2, 3]
    assert linea["length"] == 4
    assert {q["id"]: [q["x"], q["y"], q["z"]] for q in info["points_3d"]}[p] == [7, 8, 9]
    assert info["constraints_3d"] == [{"id": r["constraints"][0], "type": "axis", "entities": [r["entity"]],
                                       "axis": "x"}]
    assert info["status_3d"] == "under_constrained" and info["dof_3d"] == 7   # 6 de la línea − 2 del eje + 3 del punto


def test_bloqueo_de_plano_y_encadenado(s):
    llamar(s, "create_sketch", plane="XY")
    a = llamar(s, "draw_line_3d", start=[1, 2, 3], end=[5, 6, 9], plane="xy")
    b = llamar(s, "draw_line_3d", start=[5, 6, 3], end=[5, 6, 10])
    info = llamar(s, "get_sketch")
    lineas = {e["id"]: e for e in info["entities_3d"]}
    assert lineas[a["entity"]]["end"] == [5, 6, 3]                  # z del final = z del inicio (plano XY)
    assert lineas[b["entity"]]["points"][0] == lineas[a["entity"]]["points"][1]


def test_cota_3d_y_conflicto(s):
    llamar(s, "create_sketch", plane="XY")
    linea = llamar(s, "draw_line_3d", start=[0, 0, 0], end=[3, 4, 12])["entity"]
    llamar(s, "add_dimension_3d", entities=[linea], value=26)
    (e,) = llamar(s, "get_sketch")["entities_3d"]
    assert e["length"] == 26
    antes = s.doc.a_dict()
    falla(s, "add_dimension_3d", "SKETCH_OVERCONSTRAINED", entities=[linea], value=10)
    assert s.doc.a_dict() == antes                                   # atómico: no quedó nada


def test_borrar_entidades_3d(s):
    llamar(s, "create_sketch", plane="XY")
    l1 = llamar(s, "draw_line_3d", start=[0, 0, 0], end=[0, 0, 10])["entity"]
    l2 = llamar(s, "draw_line_3d", start=[0, 0, 10], end=[5, 0, 10])["entity"]
    k = llamar(s, "add_constraint_3d", type="perpendicular", entities=[l1, l2])["constraint"]
    llamar(s, "delete_sketch_entities_3d", entities=[l1])
    info = llamar(s, "get_sketch")
    assert [e["id"] for e in info["entities_3d"]] == [l2]
    assert all(r["id"] != k for r in info["constraints_3d"])          # la restricción de la línea borrada se va
    assert len(info["points_3d"]) == 2                               # el extremo compartido queda


def test_errores_de_la_api_nunca_internos(s):
    falla(s, "draw_line_3d", "SKETCH_NOT_FOUND", start=[0, 0, 0], end=[1, 1, 1])
    llamar(s, "create_sketch", plane="XY")
    falla(s, "draw_line_3d", "INVALID_ARGUMENTS", start=[0, 0], end=[1, 1, 1])
    falla(s, "draw_line_3d", "INVALID_ARGUMENTS", start=[0, 0, 0], axis="z")
    falla(s, "draw_line_3d", "INVALID_ARGUMENTS", start=[0, 0, 0], end=[1, 1, 1], axis="z", length=3)
    falla(s, "draw_line_3d", "INVALID_ARGUMENTS", start=[0, 0, float("nan")], end=[1, 1, 1])
    falla(s, "draw_line_3d", "INVALID_GEOMETRY", start=[1, 1, 1], end=[1, 1, 1])
    falla(s, "draw_spline_3d", "INVALID_GEOMETRY", points=[[0, 0, 0]])
    linea = llamar(s, "draw_line_3d", start=[0, 0, 0], end=[1, 1, 1])["entity"]
    falla(s, "add_constraint_3d", "ENTITY_NOT_FOUND", type="parallel", entities=[linea, 999])
    falla(s, "add_constraint_3d", "INVALID_CONSTRAINT", type="axis", entities=[linea])
    falla(s, "add_dimension_3d", "INVALID_EXPRESSION", entities=[linea], value="no_existe * 2")
    falla(s, "delete_sketch_entities_3d", "ENTITY_NOT_FOUND", entities=[12345])


def test_guardar_y_abrir_conserva_el_boceto_3d(s, tmp_path):
    _, _, volumen = _tubo(s)
    antes = llamar(s, "get_sketch", sketch="Ruta")
    ruta = str(tmp_path / "tubo.omnicad")
    llamar(s, "save_document", path=ruta)
    otra = api.Sesion()
    llamar(otra, "open_document", path=ruta)
    despues = llamar(otra, "get_sketch", sketch="Ruta")
    for clave in ("entities_3d", "points_3d", "constraints_3d", "dimensions_3d", "status_3d", "dof_3d"):
        assert despues[clave] == antes[clave], clave
    (c,) = otra.doc.estado_final.cuerpos.values()
    assert geo.volumen(c.forma) == pytest.approx(volumen, rel=1e-9)


# ---------------------------------------------------------------- interfaz: la casilla «Boceto 3D» de la paleta
from test_p23_navegador import v as v, ventana as ventana  # noqa: E402, F401  (fixtures de la ventana en vivo)


def test_paleta_boceto_3d_dibuja_con_la_triada_y_guarda_en_el_timeline(v, tmp_path):
    from omnicad.ui.puente import PuenteAgentes
    from omnicad.ui.visor3d import polilineas_boceto
    ident = v.doc.nuevo_id()
    v.doc.agregar(OpBoceto(ident, "Ruta 3D", plano="XY", boceto=Boceto()))
    puente = PuenteAgentes(v, archivo=tmp_path / "puente.json")
    assert puente.ejecutar("sketch_view", {"sketch": ident, "action": "edit"})["ok"]
    paleta = v.modo_boceto.paleta
    casilla = paleta.checks["boceto3d"]
    assert casilla.isEnabled() and not casilla.isChecked() and paleta.panel3d.isHidden()
    casilla.setChecked(True)
    assert not paleta.panel3d.isHidden()
    paleta.bloqueo3d.setCurrentIndex(paleta.bloqueo3d.findData("z"))
    paleta.puntos3d.setText("1, 2, 0")
    paleta.largo3d.setText("15")
    paleta.dibujar3d.emit("linea", "z", paleta.puntos3d.text(), paleta.largo3d.text())
    lz = v.modo_boceto.lienzo
    pasos = len(lz.historial)
    paleta.dibujar3d.emit("linea", "z", "1, 2", "15")                # mal escrito: avisa y no agrega nada
    assert len(lz.historial) == pasos and len(lz.b.geo3d["curvas"]) == 1
    lz.deshacer()                                                    # Ctrl+Z del boceto deshace lo 3D
    assert not lz.b.geo3d.get("curvas")
    lz.rehacer()
    v.modo_boceto.terminar()
    br = v.doc.estado_final.bocetos[ident]
    g = br.boceto.geo3d
    (curva,) = g["curvas"].values()
    assert [g["puntos"][p] for p in curva["puntos"]] == [[1, 2, 0], [1, 2, 15]]
    assert [r["tipo"] for r in g["restricciones"].values()] == ["eje"]
    assert any(len(p) == 2 and np.allclose(p[1], (1, 2, 15)) for p in polilineas_boceto(br))


def test_curvas3d_nucleo_arista_recta_y_spline():
    from omnicad.nucleo import curvas3d
    r = curvas3d.muestrear(curvas3d.arista_recta((0, 0, 0), (0, 0, 10)), 4)
    assert r.shape == (5, 3) and abs(r[-1][2] - 10) < 1e-5
    s = curvas3d.muestrear(curvas3d.arista_spline([(0, 0, 0), (5, 5, 5), (10, 0, 10)], {0: (1, 0, 0)}), 8)
    assert np.allclose(s[0], (0, 0, 0), atol=1e-5) and np.allclose(s[-1], (10, 0, 10), atol=1e-5)
    assert s[1][0] > s[0][0] and abs(s[1][1]) < abs(s[1][0])

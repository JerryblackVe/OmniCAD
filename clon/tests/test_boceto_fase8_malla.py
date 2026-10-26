# -*- coding: utf-8 -*-
"""BOC-22: Crear boceto de sección de malla y Ajustar curvas a sección de malla (Fusion: MESH-CREATE-MESH-SECTION-
SKETCH y SKT-FIT-CURVE-TO-MESH-SECTION). Núcleo (`nucleo/malla_seccion.py`), herramientas MCP/CLI, guardar/abrir y el
comando de la cinta MALLA."""
import math
import os

import numpy as np
import pytest

from omnicad import api
from omnicad.nucleo import geometria as geo
from omnicad.nucleo import malla as ml
from omnicad.nucleo import malla_seccion as ms

V_CUBO = np.array([[0, 0, 0], [10, 0, 0], [10, 10, 0], [0, 10, 0],
                   [0, 0, 10], [10, 0, 10], [10, 10, 10], [0, 10, 10]], float)
F_CUBO = np.array([[0, 2, 1], [0, 3, 2], [4, 5, 6], [4, 6, 7], [0, 1, 5], [0, 5, 4],
                   [1, 2, 6], [1, 6, 5], [2, 3, 7], [2, 7, 6], [3, 0, 4], [3, 4, 7]])


def ok(s, nombre, **args):
    r = api.llamar(s, nombre, args)
    assert r["ok"], r
    return r["result"]


def fallo(s, nombre, kind, **args):
    r = api.llamar(s, nombre, args)
    assert not r["ok"] and r["error_kind"] == kind, r
    return r


def malla(s, primitiva, **medidas):
    cid = ok(s, primitiva, **medidas)["bodies_created"][0]["id"]
    return ok(s, "tessellate", bodies=cid, keep_original=False)["bodies_created"][0]["id"]


def medio_z(s, cuerpo):
    caja = ok(s, "get_mesh_info", body=cuerpo)["bodies"][0]["bounding_box"]
    return (caja["min"][2] + caja["max"][2]) / 2


def curvas(s, boceto, tipo):
    return [e for e in ok(s, "get_sketch", sketch=boceto)["entities"] if e["type"] == tipo and not e.get("projected")]


@pytest.fixture
def s():
    return api.Sesion()


# ---------------------------------------------------------------- núcleo
def test_seccion_de_un_cubo_es_un_cuadrado_cerrado():
    (P, cerrada), = ms.seccion(ml.Malla(V_CUBO, F_CUBO), geo.Plano("XY", 5))
    assert cerrada
    assert np.allclose(P.min(0), [0, 0]) and np.allclose(P.max(0), [10, 10])
    curvas_ = ms.ajustar(P, cerrada, "lineas_arcos", desviacion=0.01)
    assert [c["tipo"] for c in curvas_] == ["linea"] * 4
    largos = [math.dist(*c["puntos"]) for c in curvas_]
    assert np.allclose(largos, 10)


def test_plano_que_no_corta_y_malla_vacia_dan_error_claro():
    with pytest.raises(geo.ErrorGeometria, match="no corta"):
        ms.seccion(ml.Malla(V_CUBO, F_CUBO), geo.Plano("XY", 50))
    with pytest.raises(geo.ErrorGeometria, match="vacía"):
        ms.seccion(ml.Malla(np.zeros((0, 3)), np.zeros((0, 3), int)), geo.Plano("XY"))


def test_tramo_corto_y_largo_entre_dos_puntos_de_la_seccion():
    (P, cerrada), = ms.seccion(ml.Malla(V_CUBO, F_CUBO), geo.Plano("XY", 5))
    corto = ms.tramo(P, cerrada, (0, 2), (2, 0), "corto")
    largo = ms.tramo(P, cerrada, (0, 2), (2, 0), "largo")
    assert ms.largo(corto) == pytest.approx(4) and ms.largo(largo) == pytest.approx(36)
    assert np.allclose(corto[0], (0, 2)) and np.allclose(corto[-1], (2, 0))


# ---------------------------------------------------------------- herramientas
def test_las_herramientas_estan_en_el_catalogo():
    nombres = {h["nombre"] for h in api.catalogo("malla")}
    assert {"create_mesh_section_sketch", "fit_curves_to_mesh_section"} <= nombres


def test_caja_da_cuatro_lineas_y_un_perfil_de_100(s):
    m = malla(s, "create_box", length=10, width=10, height=10)
    r = ok(s, "create_mesh_section_sketch", body=m, plane="XY", offset=medio_z(s, m))
    (sec,) = r["sections"]
    assert sec["closed"] and sec["length"] == pytest.approx(40, abs=1e-6)
    boceto = r["sketch"]["id"]
    f = ok(s, "fit_curves_to_mesh_section", sketch=boceto, curve_type="lines_and_arcs", max_deviation=0.01)
    assert [c["type"] for c in f["curves"]] == ["line"] * 4
    assert all(c["max_deviation"] < 1e-6 for c in f["curves"])
    assert sorted(round(e["length"], 6) for e in curvas(s, boceto, "line")) == [10] * 4
    (perfil,) = ok(s, "get_sketch", sketch=boceto)["profiles"]
    assert perfil["area"] == pytest.approx(100, abs=1e-6)


def test_el_boceto_de_seccion_puede_ir_en_un_plano_girado(s):
    m = malla(s, "create_box", length=10, width=10, height=10)
    r = ok(s, "create_mesh_section_sketch", body=m, plane="XY", offset=medio_z(s, m), angle=30)
    frame = r["plane_frame"]
    assert frame["normal"] == pytest.approx([0, -0.5, 3 ** 0.5 / 2], abs=1e-3)       # la normal de XY girada 30° sobre X
    assert frame["u_axis"] == pytest.approx([1, 0, 0]) and r["sections"]
    op = s.doc.operacion(r["sketch"]["id"])
    assert op.p["angulo_plano"] == "30.0"


def test_cilindro_da_un_circulo_de_radio_correcto(s):
    m = malla(s, "create_cylinder", radius=10, height=20)
    boceto = ok(s, "create_mesh_section_sketch", body=m, plane="XY", offset=medio_z(s, m))["sketch"]["id"]
    f = ok(s, "fit_curves_to_mesh_section", sketch=boceto, curve_type="circle", max_deviation=0.2)
    (c,) = f["curves"]
    assert c["type"] == "circle" and c["max_deviation"] < 0.2
    (circ,) = curvas(s, boceto, "circle")
    assert circ["radius"] == pytest.approx(10, abs=0.1)
    # lines_and_arcs sobre un círculo también da UN círculo (el más simple que entra en la desviación)
    f = ok(s, "fit_curves_to_mesh_section", sketch=boceto, curve_type="lines_and_arcs", max_deviation=0.2)
    assert [c["type"] for c in f["curves"]] == ["circle"]


def test_esfera_en_xz_y_elipse_de_un_cilindro_estirado(s):
    m = malla(s, "create_sphere", radius=10)
    boceto = ok(s, "create_mesh_section_sketch", body=m, plane="XZ")["sketch"]["id"]
    ok(s, "fit_curves_to_mesh_section", sketch=boceto, curve_type="circle", max_deviation=0.3)
    assert curvas(s, boceto, "circle")[0]["radius"] == pytest.approx(10, abs=0.15)
    c = malla(s, "create_cylinder", radius=10, height=20)
    ok(s, "scale_mesh", bodies=c, factor_x=2, factor_y=1, factor_z=1)
    boceto = ok(s, "create_mesh_section_sketch", body=c, plane="XY", offset=medio_z(s, c))["sketch"]["id"]
    ok(s, "fit_curves_to_mesh_section", sketch=boceto, curve_type="ellipse", max_deviation=0.5)
    (e,) = curvas(s, boceto, "ellipse")
    assert e["major_radius"] == pytest.approx(20, abs=0.3) and e["minor_radius"] == pytest.approx(10, abs=0.15)


def test_curvas_abiertas_line_arc_spline_y_spline_cerrada(s):
    m = malla(s, "create_box", length=10, width=10, height=10, anchor="corner")
    boceto = ok(s, "create_mesh_section_sketch", body=m, plane="XY", offset=5)["sketch"]["id"]
    f = ok(s, "fit_curves_to_mesh_section", sketch=boceto, curve_type="line", start=[0, 0], end=[10, 0])
    assert f["curves"][0]["max_deviation"] < 1e-6
    # el camino largo de (10,0) a (0,0) da la vuelta por los otros tres lados: una línea se desvía 10 mm
    r = api.llamar(s, "fit_curves_to_mesh_section", {"sketch": boceto, "curve_type": "line", "start": [10, 0],
                                                     "end": [0, 0], "path": "long", "max_deviation": 0.1})
    assert r["result"]["curves"][0]["max_deviation"] == pytest.approx(10, abs=1e-6) and r["avisos"]
    # la segunda línea arranca donde terminó la primera: comparten el punto
    lineas = curvas(s, boceto, "line")
    assert set(lineas[0]["points"]) & set(lineas[1]["points"])
    c = malla(s, "create_cylinder", radius=10, height=20, x=100)
    boceto = ok(s, "create_mesh_section_sketch", body=c, plane="XY", offset=medio_z(s, c))["sketch"]["id"]
    f = ok(s, "fit_curves_to_mesh_section", sketch=boceto, curve_type="arc", start=[110, 0], end=[100, 10],
           max_deviation=0.2)
    (arco,) = curvas(s, boceto, "arc")
    assert arco["radius"] == pytest.approx(10, abs=0.1) and f["curves"][0]["max_deviation"] < 0.2
    f = ok(s, "fit_curves_to_mesh_section", sketch=boceto, curve_type="spline", start=[100, 10], end=[90, 0],
           tolerance=0.05)
    assert f["curves"][0]["type"] == "spline"
    f = ok(s, "fit_curves_to_mesh_section", sketch=boceto, curve_type="closed_spline", tolerance=0.05,
           max_deviation=0.2)
    assert f["curves"][0]["max_deviation"] < 0.2


def test_entradas_invalidas(s):
    solido = ok(s, "create_box", length=10, width=10, height=10)["bodies_created"][0]["id"]
    fallo(s, "create_mesh_section_sketch", "UNSUPPORTED_BODY_TYPE", body=solido, plane="XY")
    m = malla(s, "create_box", length=10, width=10, height=10, x=50)
    fallo(s, "create_mesh_section_sketch", "OPERATION_FAILED", body=m, plane="XY", offset=500)
    fallo(s, "create_mesh_section_sketch", "PLANE_NOT_FOUND", body=m, plane="ZZ")
    vacio = ok(s, "create_sketch", plane="XY")["sketch"]["id"]
    fallo(s, "fit_curves_to_mesh_section", "INVALID_ARGUMENTS", sketch=vacio, curve_type="circle")
    boceto = ok(s, "create_mesh_section_sketch", body=m, plane="XY", offset=medio_z(s, m))["sketch"]["id"]
    fallo(s, "fit_curves_to_mesh_section", "INVALID_ARGUMENTS", sketch=boceto, curve_type="line")
    fallo(s, "fit_curves_to_mesh_section", "INVALID_ARGUMENTS", sketch=boceto, curve_type="arc",
          start=[50, 0], end=[50, 0])
    fallo(s, "fit_curves_to_mesh_section", "INVALID_ARGUMENTS", sketch=boceto, curve_type="line", start=[50, 0],
          end=[55, 5], max_deviation=0)
    fallo(s, "fit_curves_to_mesh_section", "ENTITY_NOT_FOUND", sketch=boceto, curve_type="circle", section=999)
    assert len(ok(s, "get_timeline")["steps"]) == 5      # nada de lo que falló dejó un paso


def test_un_paso_de_deshacer_y_guardar_abrir(s, tmp_path):
    m = malla(s, "create_cylinder", radius=10, height=20)
    boceto = ok(s, "create_mesh_section_sketch", body=m, plane="XY", offset=medio_z(s, m))["sketch"]["id"]
    ok(s, "fit_curves_to_mesh_section", sketch=boceto, curve_type="circle", max_deviation=0.2)
    ok(s, "undo")
    assert curvas(s, boceto, "circle") == []
    ok(s, "redo")
    ruta = str(tmp_path / "seccion.omnicad")
    ok(s, "save_document", path=ruta)
    otra = api.Sesion()
    ok(otra, "open_document", path=ruta)
    info = ok(otra, "get_sketch", sketch=boceto)
    seccion = [e for e in info["entities"] if e.get("projected")]
    assert len(seccion) == 1 and seccion[0]["construction"]
    assert curvas(otra, boceto, "circle")[0]["radius"] == pytest.approx(10, abs=0.1)
    assert len(info["profiles"]) == 1


# ---------------------------------------------------------------- interfaz
@pytest.fixture
def app_qt():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def test_comando_y_boton_de_la_cinta(s, app_qt):
    from omnicad.ui import cinta
    from omnicad.ui.comando import ContextoComando, hit_desde_ref
    from omnicad.ui.comandos import CATALOGO
    claves = {it[2] for _g, _f, items in cinta.MALLA for it in items if it[0] == "item"}
    assert "seccion_malla" in claves and "seccion_malla" in CATALOGO
    m = malla(s, "create_cylinder", radius=10, height=20)
    doc = s.doc
    cmd, ctx = CATALOGO["seccion_malla"](), ContextoComando(doc)
    v = {c.clave: c.defecto for c in cmd.campos(ctx)}
    v.update(cuerpo=[hit_desde_ref({"tipo": "cuerpo", "cuerpo": m}, doc.estado_final)],
             plano=[hit_desde_ref({"tipo": "plano", "id": "XY"}, doc.estado_final)],
             distancia=f"{medio_z(s, m)} mm", ajuste="circulo", tolerancia="0.2 mm")
    op = cmd.construir(v, ctx)
    assert doc.agregar(op).estado in ("ok", "aviso")
    assert curvas(s, op.id, "circle")[0]["radius"] == pytest.approx(10, abs=0.1)
    v.update(plano=[hit_desde_ref({"tipo": "plano", "id": "XY"}, doc.estado_final)], distancia="500 mm")
    from omnicad.ui.comando import ErrorComando
    with pytest.raises(ErrorComando, match="no corta"):
        cmd.construir(v, ctx)

# -*- coding: utf-8 -*-
"""Bocetos sobre caras y planos de construcción, herramientas del boceto en la vista 3D y cámara."""
import math

import numpy as np
import pytest

from omnicad.nucleo import geometria as g
from omnicad.restricciones import Boceto, resolver
from omnicad.timeline.documento import Documento, ErrorDocumento
from omnicad.timeline.operaciones import OpBoceto, OpExtrusion, OpPlano, OpPrimitiva
from omnicad.timeline.parametros import TablaParametros


def _caras_planas(forma):
    return [p for p in (g.plano_de_cara(c) for c in g.caras(forma)) if p is not None]


# ---------------------------------------------------------------- planos de caras
def test_plano_de_la_cara_superior_y_de_una_lateral():
    planos = _caras_planas(g.caja(10, 10, 10))
    arriba = next(p for p in planos if p.normal[2] > 0.99)
    assert np.allclose(arriba.origen, (0, 0, 10)) and np.allclose(arriba.u, (1, 0, 0))
    lateral = next(p for p in planos if p.normal[0] > 0.99)
    assert np.allclose(lateral.v, (0, 0, 1))                      # el boceto queda "derecho"
    assert np.allclose(np.cross(lateral.u, lateral.v), lateral.normal)
    assert g.plano_de_cara(g.caras(g.cilindro(5, 10))[0]) is None or len(_caras_planas(g.cilindro(5, 10))) == 2


def test_a_uv_es_la_inversa_de_a_3d():
    p = g.Plano.desde_marco((1, 2, 3), (1, 1, 0), (0, 0, 1))
    assert np.allclose(p.a_uv(p.a_3d(4.5, -2.0)), (4.5, -2.0))


def test_boceto_sobre_una_cara_extruye_desde_la_cara():
    doc = Documento()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="40", largo="40", alto="10"))
    arriba = next(p for p in _caras_planas(doc.estado_final.cuerpos["op1.c1"].forma) if p.normal[2] > 0.99)
    b = Boceto()
    b.agregar_circulo((20, 20), 5)
    doc.agregar(OpBoceto(doc.nuevo_id(), plano="cara", marco=arriba.marco(), boceto=b))
    perfil = doc.estado_final.bocetos["op2"].perfiles[0]
    doc.agregar(OpExtrusion(doc.nuevo_id(), boceto="op2", perfiles=[OpExtrusion.referencia_perfil(perfil)],
                            distancia="6", operacion="nuevo"))
    (_, _, z0), (_, _, z1) = g.caja_envolvente(doc.estado_final.cuerpos["op3.c1"].forma)
    assert (z0, z1) == pytest.approx((10, 16))


# ---------------------------------------------------------------- planos de construcción
def _doc_con_plano():
    doc = Documento()
    doc.parametros.agregar("alto_plano", "25 mm")
    doc.agregar(OpPlano(doc.nuevo_id(), base="XY", distancia="alto_plano"))
    b = Boceto()
    b.agregar_rectangulo((0, 0), (10, 10))
    doc.agregar(OpBoceto(doc.nuevo_id(), plano="op1", boceto=b))
    return doc


def test_boceto_en_un_plano_de_desfase_sigue_al_parametro():
    doc = _doc_con_plano()
    assert doc.estado_final.bocetos["op2"].plano.origen[2] == pytest.approx(25)
    t = TablaParametros.desde_lista(doc.parametros.a_lista())
    t.modificar("alto_plano", "40 mm")
    doc.aplicar_parametros(t)
    assert doc.estado_final.bocetos["op2"].plano.origen[2] == pytest.approx(40)


def test_no_se_borra_un_plano_que_usa_un_boceto():
    doc = _doc_con_plano()
    assert "op1" in doc.operacion("op2").dependencias()
    with pytest.raises(ErrorDocumento):
        doc.eliminar("op1")


def test_plano_desfasado_de_otro_plano():
    doc = _doc_con_plano()
    doc.agregar(OpPlano(doc.nuevo_id(), base="op1", distancia="5"))
    assert doc.estado_final.planos["op3"].origen[2] == pytest.approx(30)


# ---------------------------------------------------------------- boceto asociado a la cara (L143)
def _cara_mas_x(forma):
    return next(c for c in g.caras(forma) if (p := g.plano_de_cara(c)) is not None and p.normal[0] > 0.99)


def _doc_corte_en_cara(asociado=True):
    """Caja de ancho paramétrico 70 con una abertura 10x4x3 cortada desde un boceto en la cara +X."""
    from omnicad.nucleo import referencias as refs
    doc = Documento()
    doc.parametros.agregar("ancho", "70 mm")
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="ancho", largo="40", alto="20"))
    forma = doc.estado_final.cuerpos["op1.c1"].forma
    cara = _cara_mas_x(forma)
    b = Boceto()
    b.agregar_rectangulo((15, 8), (25, 12))
    extra = {"cara": refs.referencia("op1.c1", cara, forma)} if asociado else {}
    doc.agregar(OpBoceto(doc.nuevo_id(), plano="cara", marco=g.plano_de_cara(cara).marco(), boceto=b, **extra))
    perfil = doc.estado_final.bocetos["op2"].perfiles[0]
    doc.agregar(OpExtrusion(doc.nuevo_id(), boceto="op2", perfiles=[OpExtrusion.referencia_perfil(perfil)],
                            distancia="3", invertir=True, operacion="cortar"))
    return doc


def _ancho(doc, valor):
    t = TablaParametros.desde_lista(doc.parametros.a_lista())
    t.modificar("ancho", valor)
    doc.aplicar_parametros(t)


@pytest.mark.parametrize("ancho", [76, 64])
def test_boceto_sobre_cara_sigue_a_la_cara(ancho):
    doc = _doc_corte_en_cara()
    _ancho(doc, f"{ancho} mm")
    assert all(r.estado == "ok" for r in doc.resultados), [(r.estado, r.mensaje) for r in doc.resultados]
    assert doc.estado_final.bocetos["op2"].plano.origen[0] == pytest.approx(ancho)
    forma = doc.estado_final.cuerpos["op1.c1"].forma
    assert g.es_valida(forma)
    assert g.volumen(forma) == pytest.approx(ancho * 40 * 20 - 10 * 4 * 3, rel=1e-6)
    assert g.area(_cara_mas_x(forma)) == pytest.approx(40 * 20 - 10 * 4, rel=1e-6)   # la abertura está en la cara


def test_boceto_viejo_sin_cara_conserva_el_marco():
    doc = _doc_corte_en_cara(asociado=False)
    _ancho(doc, "76 mm")
    assert doc.estado_final.bocetos["op2"].plano.origen[0] == pytest.approx(70)
    datos = doc.a_dict()
    for op in datos["operaciones"]:
        op["params"].pop("cara", None)
    otro = Documento.desde_dict(datos)
    assert otro.operacion("op2").p["cara"] is None


def test_boceto_sobre_cara_perdida_da_error_y_depende_del_cuerpo():
    doc = _doc_corte_en_cara()
    assert "op1" in doc.operacion("op2").dependencias()
    with pytest.raises(ErrorDocumento):
        doc.eliminar("op1")
    doc.suprimir("op1")
    r = doc.resultados[1]                                                    # el boceto, op2
    assert r.estado == "error" and "cara" in r.mensaje


def test_boceto_sobre_cara_sigue_a_la_cara_tras_guardar_y_abrir():
    otro = Documento.desde_dict(_doc_corte_en_cara().a_dict())
    _ancho(otro, "80 mm")
    assert otro.estado_final.bocetos["op2"].plano.origen[0] == pytest.approx(80)
    assert g.volumen(otro.estado_final.cuerpos["op1.c1"].forma) == pytest.approx(80 * 40 * 20 - 120, rel=1e-6)


def test_api_create_sketch_en_cara_queda_asociado():
    from omnicad import api
    s = api.Sesion()
    for nombre, args in (("create_parameter", {"name": "ancho", "expression": "70 mm"}),
                         ("create_box", {"length": "ancho", "width": 40, "height": 20}),
                         ("create_sketch", {"plane": ">X"})):
        r = api.llamar(s, nombre, args)
        assert r["ok"], r
    op = s.doc.operaciones[-1]
    assert op.p["cara"]["tipo"] == "cara"
    assert r["result"]["plane_frame"]["origin"][0] == pytest.approx(35)
    assert api.llamar(s, "set_parameter", {"name": "ancho", "expression": "76 mm"})["ok"]
    assert s.doc.estado_final.bocetos[op.id].plano.origen[0] == pytest.approx(38)


def _caja_con_agujero_a_8_mm_del_borde():
    """B-09: caja de `ancho` x 40 x 20; boceto en la cara de arriba con el contorno PROYECTADO y un círculo r3
    acotado a 8 mm de su borde derecho; corte de 5 mm hacia adentro."""
    from omnicad import api
    s = api.Sesion()

    def llamar(nombre, **args):
        r = api.llamar(s, nombre, args)
        assert r["ok"], r
        return r["result"]
    llamar("create_parameter", name="ancho", expression="70 mm")
    llamar("create_box", length="ancho", width=40, height=20)
    llamar("create_sketch", plane=">Z")
    llamar("project_to_sketch", faces=">Z")
    derecha = next(e["id"] for e in llamar("get_sketch")["entities"]
                   if e["type"] == "line" and e["start"][0] == e["end"][0] == 35)
    centro = llamar("draw_circle", center_x=27, center_y=0, radius=3)["points"][0]
    llamar("add_dimension", sketch="Boceto1", type="distance", entities=[centro, derecha], value=8)
    llamar("extrude", sketch="Boceto1", profile=1, distance=5, operation="cut")
    return s, llamar


def _volumen(llamar):
    return llamar("get_physical_properties")["total"]["volume"]


def test_proyeccion_del_boceto_sigue_al_modelo_cuando_cambia_un_parametro():
    s, llamar = _caja_con_agujero_a_8_mm_del_borde()
    agujero = math.pi * 3 ** 2 * 5
    assert _volumen(llamar) == pytest.approx(70 * 40 * 20 - agujero, rel=1e-4)
    for ancho in (50, 30, 90, 70):                                # a 30 mm el agujero antes quedaba en el aire
        llamar("set_parameter", name="ancho", expression=f"{ancho} mm")
        assert _volumen(llamar) == pytest.approx(ancho * 40 * 20 - agujero, rel=1e-4), ancho
        assert not [p for p in llamar("get_timeline", include_params=False)["steps"] if p["status"] != "ok"], ancho


def test_proyeccion_asociativa_sobrevive_a_guardar_y_abrir():
    s, llamar = _caja_con_agujero_a_8_mm_del_borde()
    from omnicad import api
    s2 = api.Sesion(Documento.desde_dict(s.doc.a_dict()))
    assert api.llamar(s2, "set_parameter", {"name": "ancho", "expression": "30 mm"})["ok"]
    agujero = math.pi * 3 ** 2 * 5
    assert api.llamar(s2, "get_physical_properties", {})["result"]["total"]["volume"] == pytest.approx(
        30 * 40 * 20 - agujero, rel=1e-4)


def test_vistas_guardadas_se_guardan_con_el_documento():
    doc = Documento()
    doc.vistas["Frente"] = {"objetivo": [0, 0, 0], "distancia": 100.0, "R": np.identity(3).tolist(), "camara": "ortografica"}
    otro = Documento.desde_dict(doc.a_dict())
    assert otro.vistas == doc.vistas


# ---------------------------------------------------------------- solver: restringido por entidad
def test_rectangulo_totalmente_restringido_queda_determinado():
    b = Boceto()
    ls = b.agregar_rectangulo((0, 0), (20, 10))
    b.agregar_restriccion("fijo", [b.curvas[ls[0]].p1])
    c1, c2 = b.agregar_cota("distancia", [ls[0]], "20"), b.agregar_cota("distancia", [ls[1]], "10")
    r = resolver(b, {c1: 20, c2: 10})
    assert r.gdl == 0 and r.determinadas == set(b.puntos) | set(b.curvas)
    b2 = Boceto()
    b2.agregar_rectangulo((0, 0), (20, 10))
    assert not resolver(b2).determinadas


def test_simetria_y_colineal():
    b = Boceto()
    eje = b.agregar_linea((0, -10), (0, 10), True)
    b.agregar_restriccion("fijo", [eje])
    p1, p2 = b.agregar_punto(-5, 2), b.agregar_punto(7, 4)
    b.agregar_restriccion("simetrica", [p1, p2, eje])
    l1 = b.agregar_linea((20, 0), (30, 0))
    b.agregar_restriccion("fijo", [l1])
    l2 = b.agregar_linea((32, 1), (40, 2))
    b.agregar_restriccion("colineal", [l1, l2])
    assert resolver(b).ok
    (x1, y1), (x2, y2) = b.coords(p1), b.coords(p2)
    assert x1 == pytest.approx(-x2) and y1 == pytest.approx(y2)
    assert all(abs(b.coords(p)[1]) < 1e-6 for p in b.curvas[l2].puntos())


# ---------------------------------------------------------------- herramientas del boceto (Lienzo 2D)
@pytest.fixture(scope="module")
def app_qt():
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _lienzo(app_qt):
    from omnicad.ui.editor_boceto import Lienzo
    lz = Lienzo(Boceto(), TablaParametros().evaluar)
    lz.ajustar_grilla = False
    return lz


def _crear(lz, herramienta, *puntos):
    lz.set_herramienta(herramienta)
    for p in puntos:
        lz.clics.append((None, p))
        lz._procesar_clics()


@pytest.mark.parametrize("herramienta, puntos, lineas, circulos", [
    ("rectangulo_3p", [(0, 0), (10, 5), (8, 12)], 4, 0),
    ("rectangulo_centro", [(0, 0), (10, 6)], 6, 0),          # 4 lados + 2 diagonales de construcción
    ("circulo_2p", [(0, 0), (10, 0)], 0, 1),
    ("circulo_3p", [(0, 0), (10, 0), (5, 5)], 0, 1),
    ("poligono_inscrito", [(0, 0), (10, 0)], 6, 1),
    ("poligono_circunscrito", [(0, 0), (10, 0)], 6, 1),
    ("poligono_arista", [(0, 0), (10, 0), (5, 5)], 6, 1),
])
def test_herramientas_de_creacion(app_qt, herramienta, puntos, lineas, circulos):
    lz = _lienzo(app_qt)
    _crear(lz, herramienta, *puntos)
    tipos = [c.tipo for c in lz.b.curvas.values()]
    assert tipos.count("linea") == lineas and tipos.count("circulo") == circulos
    assert lz.resultado.ok


def test_poligono_regular_y_rectangulo_3p_son_correctos(app_qt):
    lz = _lienzo(app_qt)
    _crear(lz, "poligono_inscrito", (0, 0), (10, 0))
    largos = [math.dist(*lz.b._extremos_linea(c.id)) for c in lz.b.curvas.values() if c.tipo == "linea"]
    assert largos == pytest.approx([10.0] * 6)                 # hexágono inscrito en R = 10
    lz = _lienzo(app_qt)
    _crear(lz, "rectangulo_3p", (0, 0), (10, 5), (8, 12))
    ls = [c.id for c in lz.b.curvas.values()]
    d0, d1 = lz.b._direccion(ls[0]), lz.b._direccion(ls[1])
    assert abs(d0[0] * d1[0] + d0[1] * d1[1]) < 1e-9          # lados perpendiculares


def test_arco_tangente_y_linea_de_punto_medio(app_qt):
    lz = _lienzo(app_qt)
    _crear(lz, "linea", (0, 0), (10, 0))
    linea = next(iter(lz.b.curvas))
    fin = lz.b.curvas[linea].p2
    aid, _ = lz._crear_arco_tangente(fin, linea, (None, (15, 5)))
    assert lz.b.tipo_de(aid) == "arco" and lz.resultado.ok
    cx, cy = lz.b.coords(lz.b.curvas[aid].centro)
    assert cx == pytest.approx(10) and cy == pytest.approx(5)  # centro sobre la normal: tangente a la línea
    lz = _lienzo(app_qt)
    _crear(lz, "linea_medio", (0, 0), (5, 0))
    ln = next(c for c in lz.b.curvas.values())
    assert lz.b._extremos_linea(ln.id) == ((-5.0, 0.0), (5.0, 0.0))
    assert any(r.tipo == "punto_medio" for r in lz.b.restricciones.values())


def test_linea_casi_horizontal_infiere_la_restriccion(app_qt):
    from PySide6.QtCore import QPointF
    lz = _lienzo(app_qt)
    lz.resize(600, 400)
    lz.set_herramienta("linea")
    lz.clics = [(None, (0.0, 0.0))]
    pos = lz.a_px(20, 0.3)                                      # menos de 3°: se infiere horizontal
    _pid, xy = lz._ajustar(QPointF(pos), base=(0.0, 0.0))
    assert lz.inferencia == "horizontal" and xy[1] == 0.0
    lz.clics.append((None, xy))
    lz._procesar_clics()
    assert any(r.tipo == "horizontal" for r in lz.b.restricciones.values())


def test_restriccion_con_herramienta_y_fijar_anular(app_qt):
    lz = _lienzo(app_qt)
    _crear(lz, "linea", (5, 5), (15, 6))                         # lejos del origen (que engancha y fija)
    linea = next(iter(lz.b.curvas))
    assert lz.aplicar_restriccion("horizontal_vertical", [linea])
    assert any(r.tipo == "horizontal" for r in lz.b.restricciones.values())
    assert lz.aplicar_restriccion("fijo", [linea])
    assert any(r.tipo == "fijo" for r in lz.b.restricciones.values())
    assert lz.aplicar_restriccion("fijo", [linea])               # segunda vez: anula la fijación
    assert not any(r.tipo == "fijo" for r in lz.b.restricciones.values())


# ---------------------------------------------------------------- picking del visor
def test_rayo_triangulos():
    from omnicad.ui.visor3d import paso_lindo, rayo_triangulos
    tris = np.array([[[0, 0, 0], [1, 0, 0], [0, 1, 0]], [[0, 0, 5], [1, 0, 5], [0, 1, 5]]], float)
    t = rayo_triangulos(np.array([0.2, 0.2, 10.0]), np.array([0.0, 0.0, -1.0]), tris)
    assert t[1] == pytest.approx(5) and t[0] == pytest.approx(10)
    assert math.isinf(rayo_triangulos(np.array([5.0, 5.0, 10.0]), np.array([0.0, 0.0, -1.0]), tris)[0])
    assert [paso_lindo(x) for x in (0.7, 3, 12, 0.031)] == pytest.approx([1, 5, 20, 0.05])


def test_reproyectar_rechaza_cambio_de_cantidad_y_conserva_el_registro():
    b = Boceto()
    primitivas = [("linea", None, (0, 0), (10, 0)), ("linea", None, (10, 0), (10, 5))]
    origen = {"modo": "project", "refs": [{"tipo": "cuerpo", "cuerpo": "op1.c1"}]}
    ids = b.agregar_proyeccion(primitivas, origen=origen)
    datos = b.a_dict()
    registro = b.proyecciones[0]
    assert registro == {**origen, "construccion": False, "ids": ids}
    assert not b.reproyectar(registro, [("linea", None, (20, 0), (30, 0))], [])
    assert b.a_dict() == datos
    assert Boceto.desde_dict(datos).a_dict() == datos
    copia = b.copia()
    copia.proyecciones[0]["refs"][0]["cuerpo"] = "op2.c1"
    copia.proyecciones[0]["ids"].clear()
    assert b.a_dict() == datos
    assert "proyecciones" not in Boceto().a_dict()
    assert Boceto.desde_dict({}).proyecciones == []


def test_reproyectar_mueve_puntos_y_radios_sin_cambiar_ids():
    b = Boceto()
    b.agregar_punto(-10, -10)  # ids originales distintos de los del boceto de descarte
    origen = {"modo": "project", "refs": [{"tipo": "cuerpo", "cuerpo": "op1.c1"}]}
    ids = b.agregar_proyeccion([("linea", None, (0, 0), (10, 0)),
                               ("circulo", None, (10, 0), 2)], [(20, 0)], True, origen)
    puntos = set(b.puntos)
    assert b.curvas[ids[0]].p2 == b.curvas[ids[1]].centro
    assert b.reproyectar(b.proyecciones[0], [("linea", None, (5, 3), (15, 3)),
                                           ("circulo", None, (15, 3), 4)], [(25, 3)])
    assert set(b.puntos) == puntos and list(b.curvas) == ids[:2]
    assert b._extremos_linea(ids[0]) == ((5, 3), (15, 3))
    assert b.curvas[ids[1]].radio == 4 and b.coords(ids[2]) == (25, 3)
    assert all(c.construccion and c.proyectada for c in b.curvas.values())
    datos = b.a_dict()
    assert not b.reproyectar(b.proyecciones[0], [("linea", None, (0, 0), (1, 0)),
                                               ("linea", None, (1, 0), (2, 0))], [(3, 0)])
    assert b.a_dict() == datos
    b.eliminar(ids[1])
    datos = b.a_dict()
    assert not b.reproyectar(b.proyecciones[0], [("linea", None, (0, 0), (1, 0)),
                                               ("circulo", None, (1, 0), 2)], [(3, 0)])
    assert b.a_dict() == datos


@pytest.mark.parametrize("modo", ["project", "intersect"])
def test_proyeccion_de_cuerpo_depende_del_modelo_y_avisa_si_se_pierde(modo):
    from omnicad import api
    s = api.Sesion()
    for nombre, args in (("create_parameter", {"name": "ancho", "expression": "20 mm"}),
                         ("create_box", {"length": "ancho", "width": 10, "height": 10}),
                         ("create_sketch", {"plane": "XY"}),
                         ("project_to_sketch", {"bodies": ["op1.c1"], "mode": modo}),
                         ("set_parameter", {"name": "ancho", "expression": "30 mm"})):
        r = api.llamar(s, nombre, args)
        assert r["ok"], r
    op = s.doc.operacion("op2")
    assert op.dependencias() == {"op1"}
    assert max(p.x for p in s.doc.estado_final.bocetos[op.id].boceto.puntos.values()) == pytest.approx(15)
    guardado = op.boceto.a_dict()
    s.doc.suprimir("op1")
    assert s.doc.resultados[1].estado == "aviso"
    assert s.doc.resultados[1].mensaje == f"{op.nombre}: la proyección ya no coincide con el modelo; queda como estaba."
    assert s.doc.estado_final.bocetos[op.id].boceto.a_dict() == guardado

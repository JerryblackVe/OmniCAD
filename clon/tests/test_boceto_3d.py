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

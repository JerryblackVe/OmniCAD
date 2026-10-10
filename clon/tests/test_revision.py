# -*- coding: utf-8 -*-
"""Revisar geometría e impresión 3D y Reparar (nucleo/revision.py, timeline/ops_revision.py): F2 + B2 + RH13."""
import math

import numpy as np
import pytest
from OCP.BRep import BRep_Builder
from OCP.BRepBuilderAPI import BRepBuilderAPI_Copy, BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakePolygon
from OCP.ShapeFix import ShapeFix_ShapeTolerance
from OCP.TopoDS import TopoDS_Shell, TopoDS_Solid
from OCP.gp import gp_Pnt

from omnicad.nucleo import geometria as geo
from omnicad.nucleo import intercambio
from omnicad.nucleo import malla as ml
from omnicad.nucleo import revision as rv
from omnicad.timeline.documento import Documento
from omnicad.timeline.operaciones import OpOperacionBase
from omnicad.timeline.ops_revision import OpReparar


# ---------------------------------------------------------------- formas de prueba
def caja():
    return geo.caja(10, 20, 30)


def cascara(caras, invertir=None):
    sh = TopoDS_Shell()
    b = BRep_Builder()
    b.MakeShell(sh)
    for i, f in enumerate(caras):
        b.Add(sh, f.Reversed() if i == invertir else f)
    return sh


def caja_sin_tapa():
    return cascara(geo.caras(caja())[:-1])


def caja_rota():
    """Caja 10×20×30 armada a mano con una cara al revés (BRepCheck: orientación) y tolerancias de 0,5 mm."""
    so = TopoDS_Solid()
    b = BRep_Builder()
    b.MakeSolid(so)
    b.Add(so, cascara(geo.caras(caja()), invertir=0))
    ShapeFix_ShapeTolerance().SetTolerance(so, 0.5)
    return so


def cuna(apice=10.0, largo=20.0, alto=10.0):
    """Prisma triangular con un filo de `apice` grados en el origen, a lo largo de Z."""
    h = largo * math.tan(math.radians(apice))
    pol = BRepBuilderAPI_MakePolygon(gp_Pnt(0, 0, 0), gp_Pnt(largo, 0, 0), gp_Pnt(largo, h, 0), True).Wire()
    return geo.extruir([BRepBuilderAPI_MakeFace(pol, True).Face()], (0, 0, 1), alto)


def tipos(informe):
    return [p["tipo"] for p in informe["problemas"]]


# ---------------------------------------------------------------- revisar (B-rep)
def test_caja_valida_sin_problemas():
    forma = caja()
    r = rv.revisar(forma)
    assert geo.es_valida(forma) and r["valido"] and r["cerrado"] and rv.es_estanca(forma)
    assert r["problemas"] == [] and r["errores"] == r["avisos"] == 0 and not r["truncado"]
    assert (r["solidos"], r["cascaras"], r["caras"], r["aristas"], r["vertices"]) == (1, 1, 6, 12, 8)
    assert r["aristas_libres"] == r["aristas_no_manifold"] == r["autointersecciones"] == 0
    assert r["volumen"] == pytest.approx(6000) and r["area"] == pytest.approx(2200)
    assert r["caja"] == ((0, 0, 0), (10, 20, 30))
    assert max(r["tolerancias"].values()) <= 1e-6
    assert "Válido: sí" in rv.resumen(r) and "Estanco: sí" in rv.resumen(r)


def test_caja_sin_una_cara_da_4_aristas_libres_con_posicion():
    forma = caja_sin_tapa()
    r = rv.revisar(forma)
    assert geo.es_valida(forma) and r["valido"]              # una cáscara abierta es válida para el kernel
    assert not r["cerrado"] and not rv.es_estanca(forma) and r["aristas_libres"] == 4 and r["solidos"] == 0
    libres = [p for p in r["problemas"] if p["tipo"] == "arista_libre"]
    assert len(libres) == 4 and all(len(p["segmentos"]) >= 2 for p in libres)
    puntos = sorted(tuple(round(c, 6) for c in p["punto"]) for p in libres)
    assert puntos == sorted([(0, 10, 30), (10, 10, 30), (5, 0, 30), (5, 20, 30)])   # el borde de la tapa que falta


def test_dos_cajas_por_una_arista_dan_una_no_manifold():
    union = geo.booleano(caja(), geo.caja(10, 20, 30, (10, 20, 0)), "unir")
    r = rv.revisar(union)
    assert geo.es_valida(union) and r["aristas_no_manifold"] == 1 and r["solidos"] == 2
    (p,) = [p for p in r["problemas"] if p["tipo"] == "arista_no_manifold"]
    assert p["punto"] == pytest.approx((10, 20, 15)) and p["valor"] == 4 and p["gravedad"] == "error"


def test_autointerseccion_de_dos_solidos_superpuestos():
    forma = geo.compuesto([caja(), geo.trasladar(caja(), (5, 5, 5))])
    r = rv.revisar(forma)
    assert r["autointersecciones"] > 0 and "autointerseccion" in tipos(r)
    assert all(p["punto"] is not None for p in r["problemas"] if p["tipo"] == "autointerseccion")
    assert rv.revisar(forma, autointersecciones=False)["autointersecciones"] is None


def test_cara_que_se_cruza_explica_por_que_es_invalida():
    pol = BRepBuilderAPI_MakePolygon(gp_Pnt(0, 0, 0), gp_Pnt(10, 10, 0), gp_Pnt(10, 0, 0), gp_Pnt(0, 10, 0), True).Wire()
    cara = BRepBuilderAPI_MakeFace(pol, True).Face()
    r = rv.revisar(cara)
    assert not geo.es_valida(cara) and not r["valido"]
    (p,) = [p for p in r["problemas"] if p["tipo"] == "cara_invalida"]
    assert "se cruza a sí mismo" in p["mensaje"] and p["punto"][2] == pytest.approx(0)


def test_cara_invertida_y_tolerancias_altas_se_informan():
    r = rv.revisar(caja_rota())
    assert not r["valido"] and "cascara_invalida" in tipos(r)
    assert any("orientación invertida" in p["mensaje"] for p in r["problemas"])
    assert r["tolerancias"] == pytest.approx({"vertice": 0.5, "arista": 0.5, "cara": 0.5})
    assert r["tolerancias_altas"] == 8 + 12 + 6 and r["problemas"][0]["gravedad"] == "error"   # errores primero
    assert rv.revisar(caja_rota(), tolerancia_maxima=None)["tolerancias_altas"] == 0


def test_max_problemas_trunca_pero_cuenta_todo():
    r = rv.revisar(caja_rota(), max_problemas=3)
    assert len(r["problemas"]) == 3 and r["truncado"] and r["avisos"] == 26 and r["errores"] == 1
    assert r["problemas"][0]["tipo"] == "cascara_invalida"
    r = rv.revisar(caja_sin_tapa(), max_problemas=1)
    assert r["aristas_libres"] == 4 and r["avisos"] == 4 and len(r["problemas"]) == 1 and r["truncado"]
    r = rv.revisar(caja_sin_tapa(), max_problemas=0)
    assert r["problemas"] == [] and r["avisos"] == 4 and r["truncado"]
    assert not rv.revisar(caja())["truncado"]


# ---------------------------------------------------------------- impresión 3D
def test_placa_de_0_3_mm_da_espesor_minimo_0_3():
    placa = geo.caja(20, 20, 0.3)
    r = rv.revisar_impresion(placa, espesor_minimo=0.8)
    assert geo.es_valida(placa) and r["cerrado"]
    assert r["espesor_minimo"] == pytest.approx(0.3, abs=1e-9) and r["zonas_finas"] == 1 and not r["imprimible"]
    (p,) = [p for p in r["problemas"] if p["tipo"] == "espesor_fino"]
    assert p["valor"] == pytest.approx(0.3) and p["punto"][2] == pytest.approx(0.15)     # en el medio de la pared
    assert rv.revisar_impresion(placa, espesor_minimo=0.2)["imprimible"]
    assert r["volumen"] == pytest.approx(120) and r["muestras"] == rv.MUESTRAS_ESPESOR


def test_caja_inclinada_30_grados_tiene_100_mm2_de_voladizo():
    inclinada = geo.rotar(geo.caja(10, 10, 10), (0, 0, 0), (1, 0, 0), 30)
    r = rv.revisar_impresion(inclinada)
    assert geo.es_valida(inclinada)
    assert r["area_voladizo"] == pytest.approx(100, rel=1e-6) and r["zonas_voladizo"] == 1   # la base, a 30° de −Z
    (p,) = [p for p in r["problemas"] if p["tipo"] == "voladizo"]
    assert p["gravedad"] == "aviso" and len(p["segmentos"]) >= 8
    assert rv.revisar_impresion(inclinada, angulo_voladizo=70)["area_voladizo"] == pytest.approx(0)
    derecha = rv.revisar_impresion(geo.caja(10, 10, 10, (0, 0, 5)))            # la base apoya en la cama
    assert derecha["area_voladizo"] == 0 and derecha["espesor_minimo"] == pytest.approx(10) and derecha["imprimible"]


def test_filo_de_10_grados_es_arista_filosa():
    forma = cuna(10.0)
    r = rv.revisar_impresion(forma, espesor_minimo=0)
    assert geo.es_valida(forma) and r["aristas_filosas"] == 1
    (p,) = [p for p in r["problemas"] if p["tipo"] == "arista_filosa"]
    assert p["valor"] == pytest.approx(10.0) and p["punto"] == pytest.approx((0, 0, 5))
    assert rv.revisar_impresion(cuna(30.0), espesor_minimo=0)["aristas_filosas"] == 0
    assert rv.revisar_impresion(ml.desde_brep(forma), espesor_minimo=0)["aristas_filosas"] == 1


def test_cuerpo_abierto_no_es_imprimible():
    r = rv.revisar_impresion(caja_sin_tapa())
    assert not r["cerrado"] and not r["imprimible"] and "abierto" in tipos(r) and r["volumen"] is None


def test_primer_choque_mide_la_distancia_y_el_triangulo():
    m = ml.desde_brep(caja())
    t, j = rv.primer_choque([(5, 5, -10), (50, 50, 50)], [(0, 0, 1), (0, 0, 1)], m.triangulos(), 1e-9)
    assert t[0] == pytest.approx(10) and np.isinf(t[1]) and j[1] == -1
    assert m.triangulos()[j[0]][:, 2] == pytest.approx([0, 0, 0])


def test_espesores_de_una_placa_repartidos_por_area():
    m = ml.desde_brep(geo.caja(20, 20, 0.3))
    puntos, espesor, origen, opuesto = rv.espesores(m, muestras=500)
    assert len(puntos) == len(espesor) == len(origen) == len(opuesto) == 500 and np.isfinite(espesor).all()
    assert espesor.min() == pytest.approx(0.3) and espesor.max() <= 20 + 1e-9 and (opuesto >= 0).all()
    caras = (np.abs(puntos[:, 2]) < 1e-9) | (np.abs(puntos[:, 2] - 0.3) < 1e-9)
    assert np.allclose(espesor[caras], 0.3) and caras.sum() > 450          # 97 % del área está arriba y abajo
    again = rv.espesores(m, muestras=500)
    assert np.array_equal(again[1], espesor)                                # semilla fija: se repite


@pytest.mark.parametrize("kw", [{"angulo_voladizo": 0}, {"angulo_voladizo": 90}, {"espesor_minimo": -1},
                                {"angulo_filoso": 180}, {"muestras": 0}])
def test_parametros_de_impresion_invalidos(kw):
    with pytest.raises(geo.ErrorGeometria):
        rv.revisar_impresion(caja(), **kw)


def test_forma_vacia_da_error_claro():
    with pytest.raises(geo.ErrorGeometria, match="vací"):
        rv.revisar(None)
    with pytest.raises(geo.ErrorGeometria, match="vacía"):
        rv.revisar(ml.Malla(np.zeros((0, 3)), np.zeros((0, 3), int)))


# ---------------------------------------------------------------- mallas
def test_malla_cerrada_sin_problemas_y_abierta_con_un_borde():
    m = ml.desde_brep(caja())
    r = rv.revisar(m)
    assert r["tipo_cuerpo"] == "malla" and r["valido"] and r["cerrado"] and r["problemas"] == []
    assert r["volumen"] == pytest.approx(6000) and r["autointersecciones"] is None and r["tolerancias"] is None
    abierta = rv.revisar(ml.Malla(m.vertices, m.caras[:-2]))              # sin dos triángulos: un agujero
    assert abierta["aristas_libres"] == 4 and not abierta["cerrado"]
    (p,) = abierta["problemas"]
    assert p["tipo"] == "arista_libre" and p["valor"] == 4 and len(p["segmentos"]) == 8


def test_malla_con_normales_invertidas_y_al_reves():
    m = ml.desde_brep(caja())
    caras = m.caras.copy()
    caras[0] = caras[0][[0, 2, 1]]
    r = rv.revisar(ml.Malla(m.vertices, caras))
    assert r["normales_invertidas"] == 3 and not r["valido"] and "normales_invertidas" in tipos(r)
    al_reves = rv.revisar(ml.Malla(m.vertices, m.caras[:, [0, 2, 1]]))
    assert al_reves["volumen_negativo"] and "volumen_negativo" in tipos(al_reves) and not al_reves["valido"]


def test_malla_no_manifold_y_degenerada():
    v = [(0, 0, 0), (1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (2, 0, 0)]
    c = [(0, 1, 2), (1, 0, 3), (0, 1, 4), (0, 1, 5)]                       # la arista 0-1 en cuatro triángulos
    r = rv.revisar(ml.Malla(v, c))
    assert r["aristas_no_manifold"] == 1 and r["caras_degeneradas"] == 1 and not r["valido"]


def test_espesor_y_voladizo_en_malla():
    r = rv.revisar_impresion(ml.desde_brep(geo.caja(20, 20, 0.3)))
    assert r["tipo_cuerpo"] == "malla" and r["espesor_minimo"] == pytest.approx(0.3, abs=1e-9)
    inclinada = ml.desde_brep(geo.rotar(geo.caja(10, 10, 10), (0, 0, 0), (1, 0, 0), 30))
    assert rv.revisar_impresion(inclinada)["area_voladizo"] == pytest.approx(100, rel=1e-6)


# ---------------------------------------------------------------- reparar
def test_reparar_tolerancias_infladas_y_cara_invertida_queda_valida():
    rota = caja_rota()
    assert not geo.es_valida(rota)
    arreglada = rv.reparar(rota, tolerancia=1e-3)
    r = rv.revisar(arreglada)
    assert geo.es_valida(arreglada) and r["valido"] and r["cerrado"] and r["errores"] == 0
    assert max(r["tolerancias"].values()) <= 1e-3 + 1e-12 and r["tolerancias_altas"] == 0
    assert geo.volumen(arreglada) == pytest.approx(6000)
    assert not geo.es_valida(rota)                                     # la de entrada no se toca


def test_reparar_cose_caras_sueltas_en_un_solido():
    sueltas = geo.compuesto([BRepBuilderAPI_Copy(f).Shape() for f in geo.caras(caja())])
    assert rv.revisar(sueltas)["aristas_libres"] == 24
    cosida = rv.reparar(sueltas)
    assert geo.es_valida(cosida) and rv.es_estanca(cosida) and len(geo.solidos(cosida)) == 1
    assert geo.volumen(cosida) == pytest.approx(6000)
    assert rv.revisar(rv.reparar(sueltas, coser=False))["aristas_libres"] == 24


def test_reparar_refina_caras_coplanares():
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Fuse
    cruda = BRepAlgoAPI_Fuse(geo.caja(10, 10, 10), geo.caja(10, 10, 10, (10, 0, 0))).Shape()   # sin UnifySameDomain
    refinada = rv.reparar(cruda)
    assert len(geo.caras(cruda)) == 10 and len(geo.caras(refinada)) == 6 and geo.es_valida(refinada)
    assert geo.volumen(refinada) == pytest.approx(2000)
    assert len(geo.caras(rv.reparar(cruda, refinar=False))) == 10


def test_reparar_malla_cierra_el_agujero():
    m = ml.desde_brep(caja())
    reparada = rv.reparar(ml.Malla(m.vertices, m.caras[:-2]))
    assert isinstance(reparada, ml.Malla) and rv.es_estanca(reparada) and reparada.volumen() == pytest.approx(6000)


def test_reparar_tolerancia_negativa():
    with pytest.raises(geo.ErrorGeometria, match="negativa"):
        rv.reparar(caja(), tolerancia=-1)


# ---------------------------------------------------------------- paso del timeline
def _doc_con(forma, tipo="solido"):
    doc = Documento()
    doc.agregar(OpOperacionBase(doc.nuevo_id(), cuerpos=[{"id": "x.c1", "nombre": "Roto", "tipo": tipo,
                                                          "brep": intercambio.brep_a_texto(forma)}]))
    return doc, next(iter(doc.estado_final.cuerpos))


def test_paso_reparar_deja_el_cuerpo_valido_y_se_guarda():
    doc, cid = _doc_con(caja_rota())
    assert not geo.es_valida(doc.estado_final.cuerpos[cid].forma)
    res = doc.agregar(OpReparar(doc.nuevo_id(), cuerpos=[cid], tolerancia="0.001 mm"))
    assert res.estado == "ok", res.mensaje
    forma = doc.estado_final.cuerpos[cid].forma
    assert geo.es_valida(forma) and geo.volumen(forma) == pytest.approx(6000)
    op = doc.operaciones[-1]
    assert op.dependencias() == {doc.operaciones[0].id}
    copia = Documento()
    copia._cargar(doc.a_dict())
    assert geo.es_valida(copia.estado_final.cuerpos[cid].forma)


def test_paso_reparar_superficie_que_se_cierra_pasa_a_solido():
    sueltas = geo.compuesto([BRepBuilderAPI_Copy(f).Shape() for f in geo.caras(caja())])
    doc, cid = _doc_con(sueltas, "superficie")
    doc.agregar(OpReparar(doc.nuevo_id(), cuerpos=[cid]))
    c = doc.estado_final.cuerpos[cid]
    assert c.tipo == "solido" and geo.volumen(c.forma) == pytest.approx(6000)


def test_paso_reparar_avisa_si_sigue_abierto_y_falla_sin_cuerpos():
    doc, cid = _doc_con(caja_sin_tapa(), "superficie")
    res = doc.agregar(OpReparar(doc.nuevo_id(), cuerpos=[cid]))
    assert res.estado == "ok" and not rv.es_estanca(doc.estado_final.cuerpos[cid].forma)
    res = doc.agregar(OpReparar(doc.nuevo_id(), cuerpos=[]))
    assert res.estado == "error" and "Elegí los cuerpos" in res.mensaje
    res = doc.agregar(OpReparar(doc.nuevo_id(), cuerpos=[cid], tolerancia="-1 mm"))
    assert res.estado == "error" and "negativa" in res.mensaje

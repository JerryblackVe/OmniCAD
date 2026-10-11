# -*- coding: utf-8 -*-
"""Patrones avanzados (F3 y F18 de docs/brechas_freecad.md y el hallazgo «los patrones solo repiten cuerpos»):
patrón en puntos, giro progresivo en el patrón en ruta, patrón de OPERACIONES (repite la herramienta de un agujero
o de una extrusión que corta) y multitransformación (patrón + simetría + patrón en un solo paso)."""
import json
import math
import zipfile

import numpy as np
import pytest
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge
from OCP.gp import gp_Pnt, gp_Trsf

from omnicad.io_archivos import proyecto
from omnicad.nucleo import geometria as g
from omnicad.nucleo import solidos_crear as sc
from omnicad.restricciones import Boceto
from omnicad.timeline import documento
from omnicad.timeline.documento import Documento
from omnicad.timeline.operaciones import OpBoceto, OpExtrusion, OpPlano, OpPrimitiva, operacion_desde_dict
from omnicad.timeline.ops_solido import TIPOS_REPETIBLES, OpAgujero, OpMultitransformar, OpPatron

R, H = 3.0, 10.0                                   # agujero Ø6 pasante en una placa de 10 mm
CAJA = 100 * 60 * 10
AGUJERO = math.pi * R ** 2 * H
EJE_X, EJE_Y, EJE_Z = ({"tipo": "eje", "id": e} for e in "XYZ")


def _xyz(t, p):
    q = gp_Pnt(*map(float, p)).Transformed(t)
    return np.array([q.X(), q.Y(), q.Z()])


def _vol(doc, cid="op1.c1"):
    return g.volumen(doc.estado_final.cuerpos[cid].forma)


def _ok(doc, op):
    r = doc.agregar(op)
    assert r.estado in ("ok", "aviso"), r.mensaje
    return r


def _placa_con_agujero():
    """Placa 100 × 60 × 10 (op1.c1, de (0, 0, 0) a (100, 60, 10)), boceto con un punto en (10, 10) (op2) y agujero
    Ø6 pasante hacia +Z en ese punto (op3)."""
    doc = Documento()
    _ok(doc, OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="100", largo="60", alto="10"))
    b = Boceto()
    pid = b.agregar_punto(10, 10)
    sk = OpBoceto(doc.nuevo_id(), plano="XY", boceto=b)
    _ok(doc, sk)
    _ok(doc, OpAgujero(doc.nuevo_id(), posiciones=[{"tipo": "punto_boceto", "boceto": sk.id, "punto": pid}],
                       diametro="6 mm", extension="todo", invertir=True))
    assert _vol(doc) == pytest.approx(CAJA - AGUJERO, rel=1e-9)
    return doc


# ---------------------------------------------------------------- núcleo
def test_transformaciones_en_puntos():
    ts = sc.transformaciones_en_puntos([(10, 0, 0), (0, 0, 0), (5, 5, 5), (10, 0, 0)], (0, 0, 0))
    assert len(ts) == 3                          # el original, (10, 0, 0) y (5, 5, 5): el origen y el repetido no
    assert _xyz(ts[1], (1, 2, 3)) == pytest.approx([11, 2, 3])
    assert _xyz(ts[2], (1, 2, 3)) == pytest.approx([6, 7, 8])
    ts = sc.transformaciones_en_puntos([(10, 0, 0), (20, 0, 0)], (5, 0, 0), suprimir=[1])
    assert len(ts) == 2 and _xyz(ts[1], (5, 0, 0)) == pytest.approx([20, 0, 0])
    caja = g.caja(4, 4, 4)
    copia = sc.aplicar(caja, sc.transformaciones_en_puntos([(30, 40, 50)], (2, 2, 0))[1])
    assert g.es_valida(copia) and g.volumen(copia) == pytest.approx(64)
    assert g.caja_envolvente(copia)[0] == pytest.approx((28, 38, 50))
    with pytest.raises(g.ErrorGeometria):
        sc.transformaciones_en_puntos([], (0, 0, 0))
    with pytest.raises(g.ErrorGeometria):
        sc.transformaciones_en_puntos([(1, 2)], (0, 0, 0))


def test_ruta_con_giro_progresivo():
    ruta = BRepBuilderAPI_MakeEdge(gp_Pnt(0, 0, 0), gp_Pnt(100, 0, 0)).Edge()
    sin = sc.transformaciones_en_ruta(ruta, 3, 100.0)
    con = sc.transformaciones_en_ruta(ruta, 3, 100.0, giro=90.0)
    assert len(sin) == len(con) == 3
    p = (0, 0, 10)                                # un punto 10 mm arriba de la ruta
    assert _xyz(sin[2], p) == pytest.approx([100, 0, 10], abs=1e-9)
    assert _xyz(con[0], p) == pytest.approx([0, 0, 10], abs=1e-9)                     # el original no gira
    assert _xyz(con[1], p) == pytest.approx([50, -10 * math.sin(math.radians(45)), 10 * math.cos(math.radians(45))],
                                            abs=1e-9)                                  # mitad del giro
    assert _xyz(con[2], p) == pytest.approx([100, -10, 0], abs=1e-9)                   # giro total: 90° sobre +X
    caja = sc.aplicar(g.caja(2, 2, 20), con[2])
    assert g.es_valida(caja) and g.volumen(caja) == pytest.approx(80)
    (x0, y0, z0), (x1, y1, z1) = g.caja_envolvente(caja)
    assert (x1 - x0, y1 - y0, z1 - z0) == pytest.approx((2, 20, 2))                    # la columna quedó acostada
    with pytest.raises(g.ErrorGeometria):
        sc.transformaciones_en_ruta(ruta, 3, 100.0, giro=float("nan"))


def test_componer_transformaciones():
    rect = sc.transformaciones_rectangulares((1, 0, 0), 3, 10.0, distribucion="espaciado")
    espejo = [gp_Trsf(), sc.transformacion_simetria(g.Plano("XZ"))]
    ts = sc.componer_transformaciones([rect, espejo])
    assert len(ts) == 6
    puntos = sorted(tuple(np.round(_xyz(t, (1, 2, 3)), 6)) for t in ts)
    assert puntos == [(1, -2, 3), (1, 2, 3), (11, -2, 3), (11, 2, 3), (21, -2, 3), (21, 2, 3)]
    # el orden importa: primero gira 90° y después traslada
    giro = sc.transformaciones_circulares((0, 0, 0), (0, 0, 1), 4)[:2]
    ts = sc.componer_transformaciones([giro, rect[:2]])
    assert sorted(tuple(np.round(_xyz(t, (1, 0, 0)), 6)) for t in ts) == [(0, 1, 0), (1, 0, 0), (10, 1, 0), (11, 0, 0)]
    # dos simetrías iguales no repiten instancias (la segunda devuelve al original)
    assert len(sc.componer_transformaciones([espejo, espejo])) == 2
    copia = sc.aplicar(g.caja(5, 5, 5), ts[-1])
    assert g.es_valida(copia) and g.volumen(copia) == pytest.approx(125)
    reflejo = sc.aplicar(g.caja(5, 5, 5), sc.componer_transformaciones([rect, espejo])[-1])
    assert g.es_valida(reflejo) and g.volumen(reflejo) == pytest.approx(125)
    with pytest.raises(g.ErrorGeometria, match="como máximo"):
        sc.componer_transformaciones([[gp_Trsf()] * 200, [gp_Trsf()] * 200])
    with pytest.raises(g.ErrorGeometria):
        sc.componer_transformaciones([])


# ---------------------------------------------------------------- patrón de operaciones
def test_patron_rectangular_de_un_agujero_resta_seis_agujeros_exactos():
    """El hallazgo: un patrón 3 × 2 de un agujero pasante hace 6 agujeros (el original cuenta) sobre la placa."""
    doc = _placa_con_agujero()
    pat = OpPatron(doc.nuevo_id(), objeto="operaciones", pasos=["op3"], forma_patron="rectangular", dir1=EJE_X, n1=3,
                   d1="20 mm", dir2=EJE_Y, n2=2, d2="25 mm", distribucion="espaciado")
    _ok(doc, pat)
    forma = doc.estado_final.cuerpos["op1.c1"].forma
    assert g.es_valida(forma)
    assert g.volumen(forma) == pytest.approx(CAJA - 6 * AGUJERO, rel=1e-9)
    assert list(doc.estado_final.cuerpos) == ["op1.c1"]            # no crea cuerpos: corta la placa
    assert "op3" in pat.dependencias() and pat.pasos_repetidos() == ["op3"]
    # paramétrico: el agujero original cambia de diámetro y el patrón lo sigue
    nuevo = doc.operacion("op3").copia()
    nuevo.p["diametro"] = "8 mm"
    doc.reemplazar("op3", nuevo)
    assert _vol(doc) == pytest.approx(CAJA - 6 * math.pi * 16 * H, rel=1e-9)


def test_patron_de_extrusion_que_corta_y_de_una_que_une():
    doc = Documento()
    _ok(doc, OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="100", largo="60", alto="10"))
    b = Boceto()
    b.agregar_rectangulo((10, 20), (14, 40))                         # ranura de ventilación 4 × 20
    sk = OpBoceto(doc.nuevo_id(), plano="XY", boceto=b)
    _ok(doc, sk)
    perfil = doc.estado_final.bocetos[sk.id].perfiles[0]
    corte = OpExtrusion(doc.nuevo_id(), boceto=sk.id, perfiles=[OpExtrusion.referencia_perfil(perfil)],
                        distancia="10 mm", operacion="cortar")
    _ok(doc, corte)
    _ok(doc, OpPatron(doc.nuevo_id(), objeto="operaciones", pasos=[corte.id], forma_patron="rectangular", dir1=EJE_X,
                      n1=8, d1="10 mm", distribucion="espaciado"))
    assert g.es_valida(doc.estado_final.cuerpos["op1.c1"].forma)
    assert _vol(doc) == pytest.approx(CAJA - 8 * 4 * 20 * 10, rel=1e-9)
    # un taco unido arriba, reflejado en el plano medio de la placa (x = 50): se une a la placa
    taco = OpPrimitiva(doc.nuevo_id(), forma="cilindro", radio="2", alto="5", x="80", y="30", z="10", operacion="unir")
    _ok(doc, taco)
    medio = OpPlano(doc.nuevo_id(), "Medio", base="YZ", distancia="50 mm")
    _ok(doc, medio)
    antes = _vol(doc)
    _ok(doc, OpMultitransformar(doc.nuevo_id(), objeto="operaciones", pasos=[taco.id], transformaciones=[
        {"tipo": "simetria", "plano": {"tipo": "plano", "id": medio.id}}]))
    assert list(doc.estado_final.cuerpos) == ["op1.c1"]
    assert _vol(doc) == pytest.approx(antes + math.pi * 4 * 5, rel=1e-9)
    assert g.es_valida(doc.estado_final.cuerpos["op1.c1"].forma)
    (x0, _, _), (x1, _, z1) = g.caja_envolvente(doc.estado_final.cuerpos["op1.c1"].forma)
    assert (x0, x1, z1) == pytest.approx((0, 100, 15))


def test_patron_de_un_cuerpo_nuevo_crea_cuerpos():
    doc = Documento()
    _ok(doc, OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="5", largo="5", alto="5"))
    pat = OpPatron(doc.nuevo_id(), objeto="operaciones", pasos=["op1"], forma_patron="circular", eje=EJE_Z, n=4)
    _ok(doc, pat)
    nuevos = [c for c in doc.estado_final.cuerpos if c.startswith(pat.id)]
    assert len(nuevos) == 3
    assert all(g.volumen(doc.estado_final.cuerpos[c].forma) == pytest.approx(125) for c in nuevos)


def test_patron_de_un_patron_de_operaciones():
    doc = _placa_con_agujero()
    fila = OpPatron(doc.nuevo_id(), objeto="operaciones", pasos=["op3"], forma_patron="rectangular", dir1=EJE_X, n1=4,
                    d1="20 mm", distribucion="espaciado")
    _ok(doc, fila)
    _ok(doc, OpPatron(doc.nuevo_id(), objeto="operaciones", pasos=[fila.id, "op3"], forma_patron="rectangular",
                      dir1=EJE_Y, n1=3, d1="20 mm", distribucion="espaciado"))
    assert _vol(doc) == pytest.approx(CAJA - 12 * AGUJERO, rel=1e-9)


def test_errores_claros_del_patron_de_operaciones():
    doc = _placa_con_agujero()
    r = doc.agregar(OpPatron(doc.nuevo_id(), objeto="operaciones", pasos=["op2"], dir1=EJE_X))     # un boceto
    assert r.estado == "error" and "no dejó una herramienta" in r.mensaje
    assert all(t in r.mensaje for t in TIPOS_REPETIBLES)
    doc.deshacer()
    r = doc.agregar(OpPatron(doc.nuevo_id(), objeto="operaciones", pasos=[], dir1=EJE_X))
    assert r.estado == "error" and "Elegí las operaciones" in r.mensaje
    doc.deshacer()
    corte = OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="50", largo="50", alto="50", operacion="intersecar")
    _ok(doc, corte)
    r = doc.agregar(OpPatron(doc.nuevo_id(), objeto="operaciones", pasos=[corte.id], dir1=EJE_X))
    assert r.estado == "error" and "interseca" in r.mensaje


def test_la_cache_del_proyecto_no_pierde_la_herramienta(tmp_path, monkeypatch):
    """Al abrir, los pasos lentos salen de la caché (sin ejecutarse): el paso que repite el patrón se calcula igual,
    porque la caché guarda los cuerpos y no la herramienta."""
    monkeypatch.setattr(documento, "_SEGUNDOS_CACHE", 0)
    doc = _placa_con_agujero()
    _ok(doc, OpPatron(doc.nuevo_id(), objeto="operaciones", pasos=["op3"], forma_patron="rectangular", dir1=EJE_X,
                      n1=3, d1="20 mm", distribucion="espaciado"))
    ruta = proyecto.guardar(doc, tmp_path / "placa")
    with zipfile.ZipFile(ruta) as z:                 # el agujero y el patrón van a la caché
        assert [p["op"] for p in json.loads(z.read("cache/pasos.json"))["pasos"]] == ["op1", "op3", "op4"]
    abierto = proyecto.abrir(ruta)
    assert [r.estado for r in abierto.resultados] == ["ok"] * 4
    assert _vol(abierto) == pytest.approx(CAJA - 3 * AGUJERO, rel=1e-9)
    r = abierto.reemplazar("op4", abierto.operacion("op4").copia())        # recalcular el patrón después de abrir
    assert r.estado == "ok" and _vol(abierto) == pytest.approx(CAJA - 3 * AGUJERO, rel=1e-9)


# ---------------------------------------------------------------- patrón en puntos y en ruta (timeline)
def test_patron_en_puntos_de_un_boceto_y_con_referencia():
    doc = Documento()
    _ok(doc, OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="4", largo="4", alto="4"))      # de (0,0,0) a (4,4,4)
    b = Boceto()
    for x, y in ((50, 0), (0, 50), (50, 50)):
        b.agregar_punto(x, y)
    b.agregar_linea((100, 100), (120, 100))          # sus extremos no son puntos sueltos
    sk = OpBoceto(doc.nuevo_id(), plano="XY", boceto=b)
    _ok(doc, sk)
    pat = OpPatron(doc.nuevo_id(), forma_patron="puntos", cuerpos=["op1.c1"],
                   puntos=[{"tipo": "boceto", "boceto": sk.id}], referencia={"tipo": "punto", "id": "O"},
                   coordenadas=[[0, 0, "20 mm"]])
    _ok(doc, pat)
    nuevos = sorted(g.caja_envolvente(doc.estado_final.cuerpos[c].forma)[0] for c in doc.estado_final.cuerpos
                    if c.startswith(pat.id))
    assert nuevos == pytest.approx([(0, 0, 20), (0, 50, 0), (50, 0, 0), (50, 50, 0)])
    assert all(g.es_valida(doc.estado_final.cuerpos[c].forma) for c in doc.estado_final.cuerpos)
    assert sk.id in pat.dependencias()
    # referencia [x, y, z]: el centro de la base de la caja va a cada punto
    pat2 = OpPatron(doc.nuevo_id(), forma_patron="puntos", cuerpos=["op1.c1"], coordenadas=[[100, 0, 0]],
                    referencia_xyz=[2, 2, 0], combinar=True)
    _ok(doc, pat2)
    assert _vol(doc) == pytest.approx(128) and g.caja_envolvente(doc.estado_final.cuerpos["op1.c1"].forma)[1] == \
        pytest.approx((102, 4, 4))
    r = doc.agregar(OpPatron(doc.nuevo_id(), forma_patron="puntos", cuerpos=["op1.c1"]))
    assert r.estado == "error" and "Elegí los puntos" in r.mensaje


def test_patron_en_ruta_con_giro():
    doc = Documento()
    _ok(doc, OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="2", largo="2", alto="20", x="-1", y="-1"))
    b = Boceto()
    b.agregar_linea((0, 0), (100, 0))
    sk = OpBoceto(doc.nuevo_id(), plano="XY", boceto=b)
    _ok(doc, sk)
    curva = next(iter(b.curvas))
    pat = OpPatron(doc.nuevo_id(), forma_patron="ruta", cuerpos=["op1.c1"], n1=3, d1="100 mm",
                   ruta=[{"tipo": "curva_boceto", "boceto": sk.id, "curva": curva}], giro="90 deg")
    _ok(doc, pat)
    ultimo = doc.estado_final.cuerpos[f"{pat.id}.c2"].forma
    (x0, y0, z0), (x1, y1, z1) = g.caja_envolvente(ultimo)
    assert (x1 - x0, y1 - y0, z1 - z0) == pytest.approx((2, 20, 2))         # la columna gira 90° hasta acostarse
    assert g.es_valida(ultimo) and g.volumen(ultimo) == pytest.approx(80)


def test_recetas_viejas_del_patron_siguen_igual():
    """Un patrón guardado antes de los tipos nuevos (sin objeto, giro, puntos…) abre y calcula igual."""
    viejo = {"tipo": "patron", "id": "op2", "nombre": "Patrón1", "params": {
        "forma_patron": "rectangular", "cuerpos": ["op1.c1"], "dir1": EJE_X, "n1": 3, "d1": "40 mm", "dir2": None,
        "n2": 1, "d2": "30 mm", "distribucion": "extension", "simetrico": False, "eje": None, "n": 6,
        "angulo": "360 deg", "ruta": [], "orientacion": "identica", "inicio": "0", "suprimir": [], "combinar": False}}
    op = operacion_desde_dict(viejo)
    assert op.p["objeto"] == "cuerpos" and op.p["giro"] == "0 deg"
    doc = Documento()
    _ok(doc, OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="5", largo="5", alto="5"))
    _ok(doc, op)
    assert sorted(g.caja_envolvente(c.forma)[0][0] for c in doc.estado_final.cuerpos.values()) == \
        pytest.approx([0, 20, 40])


# ---------------------------------------------------------------- multitransformación
def test_multitransformar_cuerpos_patron_y_simetria():
    doc = Documento()
    _ok(doc, OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="5", largo="5", alto="5", x="10"))
    mt = OpMultitransformar(doc.nuevo_id(), cuerpos=["op1.c1"], transformaciones=[
        {"tipo": "rectangular", "dir1": EJE_Y, "n1": 3, "d1": "20 mm", "distribucion": "espaciado"},
        {"tipo": "simetria", "plano": {"tipo": "plano", "id": "YZ"}}])
    _ok(doc, mt)
    minimos = sorted(tuple(np.round(g.caja_envolvente(c.forma)[0], 6)) for c in doc.estado_final.cuerpos.values())
    assert minimos == [(-15, 0, 0), (-15, 20, 0), (-15, 40, 0), (10, 0, 0), (10, 20, 0), (10, 40, 0)]
    assert all(g.es_valida(c.forma) and g.volumen(c.forma) == pytest.approx(125)
               for c in doc.estado_final.cuerpos.values())
    assert mt.dependencias() == {"op1"}


def test_multitransformar_operaciones_y_errores():
    doc = _placa_con_agujero()
    _ok(doc, OpMultitransformar(doc.nuevo_id(), objeto="operaciones", pasos=["op3"], transformaciones=[
        {"tipo": "rectangular", "dir1": EJE_X, "n1": 2, "d1": "80 mm", "distribucion": "espaciado"},
        {"tipo": "rectangular", "dir1": EJE_Y, "n1": 2, "d1": "40 mm", "distribucion": "espaciado"}]))
    assert _vol(doc) == pytest.approx(CAJA - 4 * AGUJERO, rel=1e-9)
    assert g.es_valida(doc.estado_final.cuerpos["op1.c1"].forma)
    r = doc.agregar(OpMultitransformar(doc.nuevo_id(), cuerpos=["op1.c1"], transformaciones=[{"tipo": "espiral"}]))
    assert r.estado == "error" and "Transformación 1" in r.mensaje and "simetria" in r.mensaje
    doc.deshacer()
    r = doc.agregar(OpMultitransformar(doc.nuevo_id(), cuerpos=["op1.c1"], transformaciones=[]))
    assert r.estado == "error" and "al menos una transformación" in r.mensaje
    doc.deshacer()
    r = doc.agregar(OpMultitransformar(doc.nuevo_id(), cuerpos=["op1.c1"], transformaciones=[
        {"tipo": "circular", "n": 3}]))
    assert r.estado == "error" and "Transformación 1 (circular)" in r.mensaje and "eje" in r.mensaje

# -*- coding: utf-8 -*-
"""Arreglos de rendimiento en Python (fases 0 y 5 de docs/plan_rust.md, P1–P13): cada uno da lo mismo que antes, más
rápido. Sin ventanas OpenGL."""
import math
import struct

import numpy as np
import pytest

from omnicad.nucleo import geometria as geo
from omnicad.restricciones import Boceto, resolver
from omnicad.restricciones import solver as S
from omnicad.timeline.documento import Documento
from omnicad.timeline.operaciones import OpPrimitiva
from omnicad.timeline.parametros import TablaParametros


# ---------------------------------------------------------------- P1: parámetros
def test_valores_con_cache_se_entera_de_una_expresion_cambiada_en_el_lugar():
    t = TablaParametros()
    t.agregar("a", "10 mm")
    t.agregar("b", "a * 2")
    assert t.valores() == {"a": 10.0, "b": 20.0}
    t.obtener("a").expresion = "7 mm"            # sin pasar por `modificar`: la clave de la caché es el contenido
    assert t.valores()["b"] == 14.0
    v = t.valores()
    v["a"] = 999                                 # lo devuelto es una copia: no ensucia la caché
    assert t.valores()["a"] == 7.0


# ---------------------------------------------------------------- P2: solver
def _poligono(n):
    b, vals = Boceto(), {}
    pts = [(math.cos(2 * math.pi * i / n) * 50, math.sin(2 * math.pi * i / n) * 50) for i in range(n)]
    ls = [b.agregar_linea(pts[i], pts[(i + 1) % n]) for i in range(n)]
    for i in range(n):
        b.agregar_restriccion("coincidente", [b.curvas[ls[i]].p2, b.curvas[ls[(i + 1) % n]].p1])
    b.agregar_restriccion("fijo", [b.curvas[ls[0]].p1])
    for i in range(n):
        vals[b.agregar_cota("distancia", [ls[i]], "20")] = 20
    return b, vals


def test_jacobiano_por_colores_es_igual_al_de_a_una_columna():
    b, v = _poligono(8)
    sis = S._Sistema(b, v, S._grupos(b)[0])
    x = sis.x0 + 0.01
    denso = np.zeros((len(sis.residuos(x)), len(x)))
    for j in range(len(x)):
        xp = x.copy()
        xp[j] += 1e-7
        denso[:, j] = (sis.residuos(xp) - sis.residuos(x)) / 1e-7
    assert np.array_equal(S._jacobiano(sis, x), denso)
    assert len(S._colorear(S._patron(sis, x))) < len(x) / 3      # muchas menos evaluaciones


def test_arrastre_con_previo_mueve_solo_su_parte_y_conserva_los_grados_de_libertad():
    b, v = _poligono(6)
    otro = b.agregar_linea((200, 0), (230, 0))
    b.agregar_restriccion("horizontal", [otro])
    previo = resolver(b, v)
    quieto = b.coords(b.curvas[otro].p2)
    pid = next(p for p in b.puntos if p not in (b.curvas[otro].p1, b.curvas[otro].p2) and p not in b.puntos_fijos())
    b.puntos[pid].x += 1.0
    r = resolver(b, v, arrastrado=pid, previo=previo)
    assert r.ok and r.gdl == previo.gdl and r.determinadas == previo.determinadas
    assert b.coords(b.curvas[otro].p2) == quieto
    completo = resolver(b, v)
    assert completo.ok and completo.gdl == previo.gdl


# ---------------------------------------------------------------- P7 y P6: memoria por paso en el documento
@pytest.fixture
def ejecutados(monkeypatch):
    lista = []
    real = OpPrimitiva.ejecutar

    def espia(self, estado, ctx):
        lista.append(self.id)
        return real(self, estado, ctx)

    monkeypatch.setattr(OpPrimitiva, "ejecutar", espia)
    return lista


def _doc():
    d = Documento()
    d.agregar(OpPrimitiva("op1", forma="caja", ancho="20", largo="20", alto="20"))
    d.agregar(OpPrimitiva("op2", forma="caja", ancho="20", largo="20", alto="20", x="100"))
    d.agregar(OpPrimitiva("op3", forma="cilindro", radio="3", alto="40", x="110", y="10", z="-5",
                          operacion="cortar", objetivo="op2.c1"))
    d.agregar(OpPrimitiva("op4", forma="caja", ancho="5", largo="5", alto="5", x="300", operacion="cortar"))
    return d


def _volumenes(d):
    return {cid: round(geo.volumen(c.forma), 6) for cid, c in d.estado_final.cuerpos.items()}


def test_editar_un_paso_no_recalcula_los_posteriores_que_no_dependen_de_el(ejecutados):
    d = _doc()
    ejecutados.clear()
    d.reemplazar("op1", OpPrimitiva("op1", forma="caja", ancho="25", largo="20", alto="20"))
    # op3 corta solo a op2.c1 (no lo tocó la edición): se reusa. op4 corta «automático»: mira todos los cuerpos.
    assert ejecutados == ["op1", "op4"]
    fresco = Documento.desde_dict(d.a_dict())
    assert _volumenes(d) == _volumenes(fresco)
    assert [r.estado for r in d.resultados] == [r.estado for r in fresco.resultados]


def test_editar_un_paso_recalcula_lo_que_depende_de_el(ejecutados):
    d = _doc()
    ejecutados.clear()
    d.reemplazar("op2", OpPrimitiva("op2", forma="caja", ancho="30", largo="20", alto="20", x="100"))
    assert ejecutados == ["op2", "op3", "op4"]
    assert _volumenes(d) == _volumenes(Documento.desde_dict(d.a_dict()))


def test_calcular_todo_olvida_la_memoria(ejecutados):
    d = _doc()
    ejecutados.clear()
    d.recalcular(0)
    assert ejecutados == []                     # nada cambió: todo de la memoria
    d.olvidar_memoria()
    d.recalcular(0)
    assert ejecutados == ["op1", "op2", "op3", "op4"]


def test_un_paso_no_memorizable_se_ejecuta_siempre(ejecutados, monkeypatch):
    d = _doc()
    monkeypatch.setattr(OpPrimitiva, "MEMORIZABLE", False)     # p. ej. la derivación, que lee un archivo externo
    ejecutados.clear()
    d.recalcular(0)
    assert ejecutados == ["op1", "op2", "op3", "op4"]


def test_recompute_all_ejecuta_todos_los_pasos(ejecutados):
    from omnicad import api
    sesion = api.Sesion(_doc())
    ejecutados.clear()
    r = api.llamar(sesion, "recompute_all", {})
    assert r["ok"], r
    assert r["result"]["steps"] == 4 and r["result"]["failed_steps"] == []
    assert ejecutados == ["op1", "op2", "op3", "op4"]


def test_aceptar_un_comando_reusa_su_vista_previa(ejecutados):
    d = _doc()
    ejecutados.clear()
    op = OpPrimitiva("op5", forma="esfera", radio="4", x="50")
    estado, _ = d.previsualizar(op)
    d.previsualizar(OpPrimitiva("op5", forma="esfera", radio="4", x="50"))     # la misma previa: no se recalcula
    assert ejecutados == ["op5"]
    d.agregar(op)
    assert ejecutados == ["op5"] and d.estado_final is estado
    assert d.resultados[-1].estado == "ok"


def test_deshacer_reusa_los_pasos_que_no_cambiaron(ejecutados):
    d = _doc()
    d.reemplazar("op1", OpPrimitiva("op1", forma="caja", ancho="25", largo="20", alto="20"))
    ejecutados.clear()
    d.deshacer()
    assert ejecutados == ["op1", "op4"]


# ---------------------------------------------------------------- P5: rayo contra la caja de un cuerpo
def test_rayo_caja():
    from omnicad.ui.visor3d import rayo_caja
    mn, mx = np.zeros(3), np.ones(3)
    assert rayo_caja(np.array([0.5, 0.5, -2.0]), np.array([0.0, 0.0, 1.0]), mn, mx) == pytest.approx(2.0, abs=1e-5)
    assert rayo_caja(np.array([2.0, 0.5, -2.0]), np.array([0.0, 0.0, 1.0]), mn, mx) == math.inf
    assert rayo_caja(np.array([0.5, 0.5, 0.5]), np.array([1.0, 0.0, 0.0]), mn, mx) == 0.0       # desde adentro
    assert rayo_caja(np.array([0.5, 0.5, 3.0]), np.array([0.0, 0.0, 1.0]), mn, mx) == math.inf  # queda atrás


# ---------------------------------------------------------------- P11 y P12: mallas
def test_exportar_stl_binario_da_los_mismos_bytes(tmp_path):
    from omnicad.io_archivos.exportar import exportar_stl
    from omnicad.timeline.operaciones import Cuerpo
    cuerpo = Cuerpo("c1", "Caja", geo.caja(10, 20, 30), "op1")
    n = exportar_stl([cuerpo], tmp_path / "a.stl")
    datos = (tmp_path / "a.stl").read_bytes()
    assert len(datos) == 84 + 50 * n and struct.unpack("<I", datos[80:84])[0] == n
    v, i = geo.triangulos_indexados(cuerpo.forma, 0.02)
    tri = np.asarray(v, float)[np.asarray(i, int)]
    nor = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    nor /= np.linalg.norm(nor, axis=1, keepdims=True)
    viejo = b"".join(struct.pack("<12fH", *a, *t[0], *t[1], *t[2], 0) for a, t in zip(nor, tri, strict=True))
    assert datos[84:] == viejo


def test_es_cerrada_y_corregir_degenerados():
    from omnicad.nucleo import malla as M
    caja = M.desde_brep(geo.caja(10, 10, 10))
    assert caja.es_cerrada()
    assert not M.Malla(caja.vertices, caja.caras[1:]).es_cerrada()                     # con un agujero
    dada_vuelta = np.vstack([caja.caras[:1, ::-1], caja.caras[1:]])
    assert not M.Malla(caja.vertices, dada_vuelta).es_cerrada()
    v = np.array([[0, 0, 0], [2, 0, 0], [1, 0, 0], [1, 1, 0], [1, -1, 0]], float)
    plana = M.Malla(v, np.array([[0, 1, 2], [1, 0, 3], [0, 4, 1]]))   # la 1.ª es degenerada (alineada)
    corregida = M._corregir_degenerados(plana)
    assert len(corregida.caras) == 3 and np.all(corregida.areas_caras() > 0)
